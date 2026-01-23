#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpStream;
use std::path::PathBuf;
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::{Manager, WindowEvent};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

struct BackendState(Mutex<Option<CommandChild>>);

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
        let bootstrap = "import os,runpy,sys; \
sys.stdout = sys.__stdout__ or open(os.devnull, 'w', encoding='utf-8'); \
sys.stderr = sys.__stderr__ or open(os.devnull, 'w', encoding='utf-8'); \
runpy.run_path('main.py', run_name='__main__')";
        app.shell()
            .command(python)
            .current_dir(root)
            .args(["-c", bootstrap])
    } else {
        app.shell().sidecar("IdleNPUWaker")?
    };

    let command = command
        .env("IDLE_NPU_HOST", host)
        .env("IDLE_NPU_PORT", port.to_string());

    let (_rx, child) = command.spawn()?;
    Ok(child)
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendState(Mutex::new(None)))
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

            let child = spawn_backend(&app.handle(), &host, port)?;
            let state = app.state::<BackendState>();
            let mut guard = state.0.lock().unwrap();
            *guard = Some(child);

            let window = app
                .get_webview_window("main")
                .expect("main window missing");
            let url_clone = url.clone();
            let wait_host = ui_host.clone();
            std::thread::spawn(move || {
                wait_for_port(&wait_host, port, Duration::from_secs(20));
                let _ = window.eval(&format!("window.location.replace('{url_clone}')"));
                let _ = window.show();
                let _ = window.set_focus();
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { .. } = event {
                let state = window.app_handle().state::<BackendState>();
                let guard_result = state.0.lock();
                if let Ok(mut guard) = guard_result {
                    if let Some(child) = guard.take() {
                        let _ = child.kill();
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
