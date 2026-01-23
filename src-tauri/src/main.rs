#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::Write;
use std::net::TcpStream;
use std::path::PathBuf;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Mutex,
};
use std::time::{Duration, Instant};

use tauri::menu::MenuBuilder;
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{Manager, RunEvent, WindowEvent};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

const TRAY_MENU_SHOW: &str = "tray-show";
const TRAY_MENU_QUIT: &str = "tray-quit";
const TRAY_ID: &str = "main";

struct BackendState(Mutex<Option<CommandChild>>);
struct ExitState(AtomicBool);

impl ExitState {
    fn request_exit(&self) {
        self.0.store(true, Ordering::SeqCst);
    }

    fn is_exit_requested(&self) -> bool {
        self.0.load(Ordering::SeqCst)
    }
}

fn is_port_open(host: &str, port: u16) -> bool {
    TcpStream::connect_timeout(
        &format!("{host}:{port}").parse().unwrap(),
        Duration::from_millis(300),
    )
    .is_ok()
}

fn wait_for_port(host: &str, port: u16, timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if is_port_open(host, port) {
            return true;
        }
        std::thread::sleep(Duration::from_millis(200));
    }
    false
}

fn backend_host_port() -> (String, u16) {
    let host = std::env::var("IDLE_NPU_HOST").unwrap_or_else(|_| "127.0.0.1".to_string());
    let port: u16 = std::env::var("IDLE_NPU_PORT")
        .ok()
        .and_then(|value| value.parse().ok())
        .unwrap_or(8000);
    let ui_host = if host == "0.0.0.0" {
        "127.0.0.1".to_string()
    } else {
        host
    };
    (ui_host, port)
}

fn request_backend_exit(host: &str, port: u16) {
    let addr: std::net::SocketAddr = match format!("{host}:{port}").parse() {
        Ok(addr) => addr,
        Err(_) => return,
    };
    if let Ok(mut stream) = TcpStream::connect_timeout(&addr, Duration::from_millis(300)) {
        let req = format!(
            "POST /api/app/exit HTTP/1.1\r\nHost: {host}:{port}\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
        );
        let _ = stream.write_all(req.as_bytes());
    }
}

fn spawn_backend<R: tauri::Runtime>(
    app: &tauri::AppHandle<R>,
    host: &str,
    port: u16,
) -> Result<CommandChild, Box<dyn std::error::Error>> {
    let command = if cfg!(debug_assertions) {
        let python = std::env::var("IDLE_NPU_PYTHON").unwrap_or_else(|_| "python".to_string());
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .unwrap()
            .to_path_buf();
        app.shell()
            .command(python)
            .current_dir(root)
            .args(["main.py"])
    } else {
        app.shell().sidecar("IdleNPUWaker")?
    };

    let command = command
        .env("IDLE_NPU_HOST", host)
        .env("IDLE_NPU_PORT", port.to_string());

    let (_rx, child) = command.spawn()?;
    Ok(child)
}

fn show_main_window<R: tauri::Runtime>(app: &tauri::AppHandle<R>) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

fn shutdown_backend<R: tauri::Runtime>(app: &tauri::AppHandle<R>) {
    let (host, port) = backend_host_port();
    request_backend_exit(&host, port);
    let child = {
        let state = app.state::<BackendState>();
        let mut guard = match state.0.lock() {
            Ok(guard) => guard,
            Err(_) => return,
        };
        guard.take()
    };
    if let Some(child) = child {
        let _ = child.kill();
    }
}

fn init_tray<R: tauri::Runtime>(app: &tauri::AppHandle<R>) -> Result<(), Box<dyn std::error::Error>> {
    let menu = build_tray_menu(app, "Show", "Quit")?;

    let mut tray = TrayIconBuilder::with_id(TRAY_ID)
        .menu(&menu)
        .tooltip("Idle NPU Waker")
        .show_menu_on_left_click(false);

    if let Some(icon) = app.default_window_icon().cloned() {
        tray = tray.icon(icon);
    }

    tray
        .on_menu_event(|app, event| match event.id().as_ref() {
            TRAY_MENU_SHOW => {
                show_main_window(app);
            }
            TRAY_MENU_QUIT => {
                let exit_state = app.state::<ExitState>();
                exit_state.request_exit();
                shutdown_backend(app);
                app.exit(0);
            }
            _ => {}
        })
        .on_tray_icon_event(|tray, event| match event {
            TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } => {
                show_main_window(tray.app_handle());
            }
            TrayIconEvent::DoubleClick {
                button: MouseButton::Left,
                ..
            } => {
                show_main_window(tray.app_handle());
            }
            _ => {}
        })
        .build(app)?;

    Ok(())
}

fn build_tray_menu<R: tauri::Runtime>(
    app: &tauri::AppHandle<R>,
    show_label: &str,
    quit_label: &str,
) -> tauri::Result<tauri::menu::Menu<R>> {
    MenuBuilder::new(app)
        .text(TRAY_MENU_SHOW, show_label)
        .separator()
        .text(TRAY_MENU_QUIT, quit_label)
        .build()
}

fn update_tray_menu<R: tauri::Runtime>(
    app: &tauri::AppHandle<R>,
    show_label: &str,
    quit_label: &str,
) -> tauri::Result<()> {
    let menu = build_tray_menu(app, show_label, quit_label)?;
    if let Some(tray) = app.tray_by_id(TRAY_ID) {
        tray.set_menu(Some(menu))?;
    }
    Ok(())
}

#[tauri::command]
fn update_tray_labels(
    app: tauri::AppHandle,
    show_label: String,
    quit_label: String,
) -> Result<(), String> {
    update_tray_menu(&app, &show_label, &quit_label).map_err(|err| err.to_string())
}

fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendState(Mutex::new(None)))
        .manage(ExitState(AtomicBool::new(false)))
        .invoke_handler(tauri::generate_handler![update_tray_labels])
        .setup(|app| {
            let host = std::env::var("IDLE_NPU_HOST").unwrap_or_else(|_| "127.0.0.1".to_string());
            let port: u16 = std::env::var("IDLE_NPU_PORT")
                .ok()
                .and_then(|value| value.parse().ok())
                .unwrap_or(8000);
            let ui_host = if host == "0.0.0.0" {
                "127.0.0.1".to_string()
            } else {
                host.clone()
            };
            let url = format!("http://{ui_host}:{port}");

            let use_external_backend = cfg!(debug_assertions);
            let child = if use_external_backend {
                None
            } else if is_port_open(&ui_host, port) {
                None
            } else {
                Some(spawn_backend(&app.handle(), &host, port)?)
            };
            let state = app.state::<BackendState>();
            let mut guard = state.0.lock().unwrap();
            *guard = child;

            let window = app
                .get_webview_window("main")
                .expect("main window missing");
            let url_clone = url.clone();
            let wait_host = ui_host.clone();
            std::thread::spawn(move || {
                wait_for_port(&wait_host, port, Duration::from_secs(20));
                let _ = window.eval(&format!("window.location.replace('{url_clone}')"));
                show_main_window(window.app_handle());
            });

            init_tray(&app.handle())?;

            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                let exit_state = window.app_handle().state::<ExitState>();
                if exit_state.is_exit_requested() {
                    shutdown_backend(window.app_handle());
                    return;
                }
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|app_handle, event| {
        match event {
            RunEvent::ExitRequested { .. } | RunEvent::Exit { .. } => {
                shutdown_backend(app_handle);
            }
            _ => {}
        }
    });
}
