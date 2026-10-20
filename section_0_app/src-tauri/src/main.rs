#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process;
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};
use tauri::{Manager, WebviewWindowBuilder, WebviewUrl, WindowEvent};
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};

struct BackendProcess(Mutex<Option<CommandChild>>);

/// Application-scoped authenticated session credential.
///
/// This is deliberately process memory only:
/// - never persisted to disk
/// - never stored in browser local/session storage
/// - never treated as authority by Tauri
///
/// The Python backend remains the authority boundary and must validate this
/// opaque credential through AuthService before constructing a GuardPrincipal.
struct ApplicationSession(Mutex<Option<String>>);

#[tauri::command]
fn set_application_session(
    state: tauri::State<'_, ApplicationSession>,
    token: String,
) -> Result<(), String> {
    if token.trim().is_empty() {
        return Err("session token is required".to_string());
    }

    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    *guard = Some(token);
    Ok(())
}

#[tauri::command]
fn get_application_session(
    state: tauri::State<'_, ApplicationSession>,
) -> Result<Option<String>, String> {
    let guard = state.0.lock().map_err(|e| e.to_string())?;
    Ok(guard.clone())
}

#[tauri::command]
fn clear_application_session(
    state: tauri::State<'_, ApplicationSession>,
) -> Result<(), String> {
    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    *guard = None;
    Ok(())
}

fn start_backend(app: &tauri::AppHandle) -> Result<(), String> {
    let state = app.state::<BackendProcess>();

    {
        let guard = state.0.lock().map_err(|e| e.to_string())?;
        if guard.is_some() {
            return Ok(());
        }
    }

    let resource_dir = app
        .path()
        .resource_dir()
        .map_err(|e| format!("resource directory unavailable: {e}"))?;

    // During development the project root is three levels above
    // section_0_app/src-tauri.  In a bundled build we fall back to
    // the packaged resource directory.
    let dev_root = std::env::current_dir()
        .ok()
        .and_then(|p| {
            if p.ends_with("section_0_app/src-tauri") {
                p.parent()?.parent().map(|x| x.to_path_buf())
            } else if p.ends_with("section_0_app") {
                p.parent().map(|x| x.to_path_buf())
            } else {
                None
            }
        });

    // Tauri preserves parent-directory resource declarations such as
    // "../../section_1_central_mind/**/*" beneath Resources/_up_/_up_.
    // Resolve the packaged project root from the actual bundled layout
    // rather than assuming resource_dir itself is the project root.
    let project_root = if let Some(dev_root) = dev_root {
        dev_root
    } else {
        let packaged_root = resource_dir
            .join("_up_")
            .join("_up_");

        let packaged_main = packaged_root
            .join("section_1_central_mind")
            .join("main.py");

        if packaged_main.exists() {
            packaged_root
        } else {
            return Err(format!(
                "Central Mind packaged project root not found. Expected backend entry point at: {}",
                packaged_main.display()
            ));
        }
    };

    let main_py = project_root
        .join("section_1_central_mind")
        .join("main.py");

    if !main_py.exists() {
        return Err(format!(
            "Central Mind backend entry point not found: {}",
            main_py.display()
        ));
    }

    let command = app
        .shell()
        .command("python3")
        .args([
            main_py.to_string_lossy().to_string(),
            "--serve".to_string(),
            "--app-owner-pid".to_string(),
            process::id().to_string(),
            "--app-runtime-token".to_string(),
            format!(
                "{}-{}",
                process::id(),
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .map_err(|e| format!("system clock error: {e}"))?
                    .as_nanos()
            ),
        ])
        .current_dir(project_root)
        .set_process_group(true);

    let (mut rx, child) = command
        .spawn()
        .map_err(|e| format!("failed to start Central Mind backend: {e}"))?;

    {
        let mut guard = state.0.lock().map_err(|e| e.to_string())?;
        *guard = Some(child);
    }

    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    print!("{}", String::from_utf8_lossy(&bytes));
                }
                CommandEvent::Stderr(bytes) => {
                    eprint!("{}", String::from_utf8_lossy(&bytes));
                }
                CommandEvent::Terminated(payload) => {
                    println!("[app] Central Mind backend terminated: {:?}", payload.code);
                    break;
                }
                _ => {}
            }
        }
    });

    Ok(())
}

fn stop_backend(app: &tauri::AppHandle) {
    let state = app.state::<BackendProcess>();

    let child = match state.0.lock() {
        Ok(mut guard) => guard.take(),
        Err(_) => None,
    };

    if let Some(child) = child {
        let _ = child.kill();
    }
}

#[tauri::command]
fn open_code_window(app: tauri::AppHandle) -> Result<(), String> {
    if let Some(w) = app.get_webview_window("code") {
        w.set_focus().map_err(|e| e.to_string())?;
        return Ok(());
    }

    WebviewWindowBuilder::new(
        &app,
        "code",
        WebviewUrl::App("window-code.html".into()),
    )
    .title("AI Friend — Coding")
    .inner_size(1400.0, 900.0)
    .min_inner_size(900.0, 600.0)
    .build()
    .map_err(|e| e.to_string())?;

    Ok(())
}

#[tauri::command]
fn open_trading_window(app: tauri::AppHandle) -> Result<(), String> {
    if let Some(w) = app.get_webview_window("trading") {
        w.set_focus().map_err(|e| e.to_string())?;
        return Ok(());
    }

    WebviewWindowBuilder::new(
        &app,
        "trading",
        WebviewUrl::App("window-trading.html".into()),
    )
    .title("AI Friend — Trading")
    .inner_size(1400.0, 900.0)
    .min_inner_size(900.0, 600.0)
    .build()
    .map_err(|e| e.to_string())?;

    Ok(())
}

#[tauri::command]
fn open_chat_window(app: tauri::AppHandle) -> Result<(), String> {
    if let Some(w) = app.get_webview_window("chat") {
        w.set_focus().map_err(|e| e.to_string())?;
        return Ok(());
    }

    WebviewWindowBuilder::new(
        &app,
        "chat",
        WebviewUrl::App("window-chat.html".into()),
    )
    .title("AI Friend — Chat")
    .inner_size(1200.0, 800.0)
    .min_inner_size(800.0, 600.0)
    .build()
    .map_err(|e| e.to_string())?;

    Ok(())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(BackendProcess(Mutex::new(None)))
        .manage(ApplicationSession(Mutex::new(None)))
        .setup(|app| {
            start_backend(&app.handle())?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            open_code_window,
            open_trading_window,
            open_chat_window,
            set_application_session,
            get_application_session,
            clear_application_session
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            match event {
                tauri::RunEvent::WindowEvent {
                    label,
                    event: WindowEvent::CloseRequested { .. },
                    ..
                } => {
                    // AI Friend owns one runtime shared by all of its windows.
                    //
                    // Closing a specialist window must not destroy that runtime
                    // while another AI Friend window remains open.
                    //
                    // Closing the final AI Friend window is a hard application
                    // close: terminate the app-owned backend first, then exit.
                    let open_windows = app.webview_windows();

                    let other_window_exists = open_windows
                        .keys()
                        .any(|open_label| open_label != &label);

                    if !other_window_exists {
                        println!(
                            "[app] final window closing — terminating fresh runtime"
                        );

                        stop_backend(app);
                        app.exit(0);
                    }
                }

                tauri::RunEvent::Exit => {
                    // Defense in depth for menu exits, OS termination paths,
                    // programmatic exits, and any future exit mechanism.
                    stop_backend(app);
                }

                _ => {}
            }
        });
}
