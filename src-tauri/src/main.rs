#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::Write;
use std::net::TcpStream;
use std::path::PathBuf;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Mutex,
};
use std::time::{Duration, Instant};

use base64::Engine as _;
use serde::Serialize;
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{
    Emitter, Manager, PhysicalPosition, RunEvent, Url, WebviewUrl, WebviewWindowBuilder,
    WindowEvent,
};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

const TRAY_ID: &str = "main";
const TRAY_WINDOW_LABEL: &str = "tray-menu";
const TRAY_MENU_WIDTH: f64 = 210.0;
const TRAY_MENU_HEIGHT: f64 = 100.0;

struct BackendState(Mutex<Option<CommandChild>>);
struct ExitState(AtomicBool);
struct TrayLabels(Mutex<(String, String)>);
struct TrayShowState(Mutex<Option<Instant>>);

#[derive(Serialize, Clone)]
struct TrayLabelsPayload {
    show_label: String,
    quit_label: String,
}


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

fn configure_webview_logging() {
    if std::env::var_os("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS").is_none() {
        std::env::set_var("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "--disable-logging --log-level=3");
    }
}

fn show_main_window<R: tauri::Runtime>(app: &tauri::AppHandle<R>) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.unminimize();
        let _ = window.show();
        let _ = window.set_focus();
    }
}

fn tray_menu_url() -> WebviewUrl {
    let (host, port) = backend_host_port();
    let url = format!("http://{host}:{port}/tray.html");
    match Url::parse(&url) {
        Ok(parsed) => WebviewUrl::External(parsed),
        Err(_) => WebviewUrl::App("tray.html".into()),
    }
}

fn emit_tray_labels<R: tauri::Runtime>(
    app: &tauri::AppHandle<R>,
    show_label: &str,
    quit_label: &str,
) {
    if let Ok(mut guard) = app.state::<TrayLabels>().0.lock() {
        *guard = (show_label.to_string(), quit_label.to_string());
    }
    if let Some(window) = app.get_webview_window(TRAY_WINDOW_LABEL) {
        let payload = TrayLabelsPayload {
            show_label: show_label.to_string(),
            quit_label: quit_label.to_string(),
        };
        let _ = window.emit("tray-labels-updated", payload);
    }
}

fn ensure_tray_window<R: tauri::Runtime>(
    app: &tauri::AppHandle<R>,
) -> Result<tauri::WebviewWindow<R>, Box<dyn std::error::Error>> {
    if let Some(window) = app.get_webview_window(TRAY_WINDOW_LABEL) {
        return Ok(window);
    }
    let url = tray_menu_url();
    let window = WebviewWindowBuilder::new(app, TRAY_WINDOW_LABEL, url)
        .title("Tray Menu")
        .inner_size(TRAY_MENU_WIDTH, TRAY_MENU_HEIGHT)
        .resizable(false)
        .fullscreen(false)
        .visible(false)
        .decorations(false)
        .transparent(true)
        .shadow(false)
        .always_on_top(true)
        .skip_taskbar(true)
        .build()?;
    Ok(window)
}

fn show_tray_menu<R: tauri::Runtime>(
    app: &tauri::AppHandle<R>,
    position: PhysicalPosition<f64>,
) {
    if let Ok(mut guard) = app.state::<TrayShowState>().0.lock() {
        *guard = Some(Instant::now());
    }
    let window = match ensure_tray_window(app) {
        Ok(window) => window,
        Err(_) => return,
    };
    if let Ok(guard) = app.state::<TrayLabels>().0.lock() {
        let payload = TrayLabelsPayload {
            show_label: guard.0.clone(),
            quit_label: guard.1.clone(),
        };
        let _ = window.emit("tray-labels-updated", payload);
    }
    let width = TRAY_MENU_WIDTH as i32;
    let height = TRAY_MENU_HEIGHT as i32;
    let mut x = position.x as i32 - width / 2;
    let mut y = position.y as i32 - height - 8;
    if x < 0 {
        x = 0;
    }
    if y < 0 {
        y = 0;
    }
    let _ = window.set_position(PhysicalPosition::new(x, y));
    let _ = window.show();
    let _ = window.set_focus();
}

fn hide_tray_menu_window<R: tauri::Runtime>(app: &tauri::AppHandle<R>) {
    if let Ok(mut guard) = app.state::<TrayShowState>().0.lock() {
        *guard = None;
    }
    if let Some(window) = app.get_webview_window(TRAY_WINDOW_LABEL) {
        let _ = window.hide();
    }
}

fn emit_close_prompt<R: tauri::Runtime>(app: &tauri::AppHandle<R>) -> bool {
    if let Some(webview) = app.get_webview_window("main") {
        return webview
            .eval(
                "if (!window.__idleNpuCloseRequested) { throw new Error('close handler missing'); } window.__idleNpuCloseRequested();",
            )
            .is_ok();
    }
    false
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
    emit_tray_labels(app, "Show", "Quit");

    let mut tray = TrayIconBuilder::with_id(TRAY_ID)
        .tooltip("Idle NPU Waker")
        .show_menu_on_left_click(false);

    if let Some(icon) = app.default_window_icon().cloned() {
        tray = tray.icon(icon);
    }

    tray
        .on_tray_icon_event(|tray, event| match event {
            TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } => {
                hide_tray_menu_window(tray.app_handle());
                show_main_window(tray.app_handle());
            }
            TrayIconEvent::DoubleClick {
                button: MouseButton::Left,
                ..
            } => {
                hide_tray_menu_window(tray.app_handle());
                show_main_window(tray.app_handle());
            }
            TrayIconEvent::Click {
                button: MouseButton::Right,
                button_state: MouseButtonState::Up,
                position,
                ..
            } => {
                show_tray_menu(tray.app_handle(), position);
            }
            _ => {}
        })
        .build(app)?;

    Ok(())
}

#[tauri::command]
fn update_tray_labels(
    app: tauri::AppHandle,
    show_label: String,
    quit_label: String,
) -> Result<(), String> {
    emit_tray_labels(&app, &show_label, &quit_label);
    Ok(())
}

#[tauri::command]
fn show_main_window_cmd(app: tauri::AppHandle) -> Result<(), String> {
    show_main_window(&app);
    Ok(())
}

#[tauri::command]
fn hide_main_window(app: tauri::AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        window.hide().map_err(|err| err.to_string())?;
    }
    Ok(())
}

#[tauri::command]
fn hide_tray_menu(app: tauri::AppHandle) -> Result<(), String> {
    hide_tray_menu_window(&app);
    Ok(())
}

#[tauri::command]
fn exit_app(app: tauri::AppHandle) -> Result<(), String> {
    let exit_state = app.state::<ExitState>();
    exit_state.request_exit();
    shutdown_backend(&app);
    app.exit(0);
    Ok(())
}

fn sanitize_filename(name: &str) -> String {
    let mut safe = name.trim().to_string();
    if safe.is_empty() {
        return "attachment".to_string();
    }
    let invalid = ['\\', '/', ':', '*', '?', '"', '<', '>', '|'];
    for ch in invalid {
        safe = safe.replace(ch, "_");
    }
    safe
}

fn unique_path(path: PathBuf) -> PathBuf {
    if !path.exists() {
        return path;
    }
    let stem = path.file_stem().and_then(|s| s.to_str()).unwrap_or("attachment");
    let ext = path.extension().and_then(|s| s.to_str()).unwrap_or("");
    let parent = path.parent().map(|p| p.to_path_buf()).unwrap_or_else(|| PathBuf::from("."));
    for idx in 1..1000 {
        let file_name = if ext.is_empty() {
            format!("{stem}-{idx}")
        } else {
            format!("{stem}-{idx}.{ext}")
        };
        let candidate = parent.join(file_name);
        if !candidate.exists() {
            return candidate;
        }
    }
    path
}

#[tauri::command]
fn save_attachment_to_downloads(
    name: String,
    data_base64: String,
    target_dir: Option<String>,
) -> Result<String, String> {
    let downloads = if let Some(dir) = target_dir {
        let trimmed = dir.trim();
        if !trimmed.is_empty() {
            PathBuf::from(trimmed)
        } else {
            dirs::download_dir().ok_or("No download directory")?
        }
    } else {
        dirs::download_dir().ok_or("No download directory")?
    };
    if !downloads.exists() {
        std::fs::create_dir_all(&downloads).map_err(|err| err.to_string())?;
    }
    let safe_name = sanitize_filename(&name);
    let mut target = downloads.join(safe_name);
    target = unique_path(target);

    let bytes = base64::engine::general_purpose::STANDARD
        .decode(data_base64.trim())
        .map_err(|err| err.to_string())?;

    std::fs::write(&target, bytes).map_err(|err| err.to_string())?;
    Ok(target.to_string_lossy().to_string())
}

fn main() {
    configure_webview_logging();
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendState(Mutex::new(None)))
        .manage(ExitState(AtomicBool::new(false)))
        .manage(TrayLabels(Mutex::new((
            "Show".to_string(),
            "Quit".to_string(),
        ))))
        .manage(TrayShowState(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![
            update_tray_labels,
            show_main_window_cmd,
            hide_main_window,
            hide_tray_menu,
            exit_app,
            save_attachment_to_downloads
        ])
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

            let url_clone = url.clone();
            let wait_host = ui_host.clone();
            let app_handle = app.handle().clone();
            let tray_handle = app_handle.clone();
            std::thread::spawn(move || {
                wait_for_port(&wait_host, port, Duration::from_secs(20));
                let tray_handle_for_window = tray_handle.clone();
                let _ = tray_handle.run_on_main_thread(move || {
                    let _ = ensure_tray_window(&tray_handle_for_window);
                });
                let app_handle_for_window = app_handle.clone();
                let _ = app_handle.run_on_main_thread(move || {
                    if let Some(window) = app_handle_for_window.get_webview_window("main") {
                        let _ = window.eval(&format!("window.location.replace('{url_clone}')"));
                    }
                    show_main_window(&app_handle_for_window);
                });
            });

            init_tray(&app.handle())?;

            Ok(())
        })
        .on_window_event(|window, event| {
            match event {
                WindowEvent::Focused(false) => {
                    if window.label() != TRAY_WINDOW_LABEL {
                        return;
                    }
                    let app_handle = window.app_handle();
                    let should_hide = match app_handle.state::<TrayShowState>().0.lock() {
                        Ok(guard) => guard
                            .as_ref()
                            .map(|instant| instant.elapsed() >= Duration::from_millis(200))
                            .unwrap_or(true),
                        Err(_) => true,
                    };
                    if should_hide {
                        hide_tray_menu_window(app_handle);
                    }
                }
                WindowEvent::CloseRequested { api, .. } => {
                    if window.label() != "main" {
                        return;
                    }
                    let app_handle = window.app_handle();
                    let exit_state = app_handle.state::<ExitState>();
                    if exit_state.is_exit_requested() {
                        shutdown_backend(app_handle);
                        return;
                    }
                    api.prevent_close();
                    if !emit_close_prompt(app_handle) {
                        exit_state.request_exit();
                        shutdown_backend(app_handle);
                        app_handle.exit(0);
                    }
                }
                _ => {}
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
