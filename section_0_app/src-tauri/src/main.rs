#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process;
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};
use tauri::{Emitter, Manager, WebviewWindowBuilder, WebviewUrl, WindowEvent};
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};

struct BackendProcess(Mutex<Option<CommandChild>>);

type SpeechChild = Arc<Mutex<Child>>;

struct SpeechProcess(Arc<Mutex<Option<SpeechChild>>>);

/// Application-scoped authenticated session credential.
///
/// By default this lives in process memory only. Explicit Remember Me stores
/// the opaque revocable session credential in macOS Keychain, never a password.
/// The backend validates it again before granting any authority.
struct ApplicationSession(Mutex<Option<String>>);

#[tauri::command]
fn set_application_session(
    state: tauri::State<'_, ApplicationSession>,
    token: String,
    remember: Option<bool>,
) -> Result<(), String> {
    if token.trim().is_empty() {
        return Err("session token is required".to_string());
    }

    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    *guard = Some(token.clone());
    #[cfg(target_os = "macos")]
    {
        let entry = keyring::Entry::new("com.centralmind.app", "application-session")
            .map_err(|_| "Could not access macOS Keychain".to_string())?;
        if remember.unwrap_or(false) {
            entry.set_password(&token).map_err(|_| "Could not save Remember Me in macOS Keychain".to_string())?;
        } else {
            match entry.delete_credential() {
                Ok(()) | Err(keyring::Error::NoEntry) => (),
                Err(_) => return Err("Could not remove saved session from macOS Keychain".to_string()),
            }
        }
    }
    #[cfg(not(target_os = "macos"))]
    if remember.unwrap_or(false) {
        return Err("Remember Me requires the macOS Keychain on this build".to_string());
    }
    Ok(())
}

#[tauri::command]
fn get_application_session(
    state: tauri::State<'_, ApplicationSession>,
) -> Result<Option<String>, String> {
    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    #[cfg(target_os = "macos")]
    if guard.is_none() {
        let entry = keyring::Entry::new("com.centralmind.app", "application-session")
            .map_err(|_| "Could not access macOS Keychain".to_string())?;
        match entry.get_password() {
            Ok(token) => *guard = Some(token),
            Err(keyring::Error::NoEntry) => (),
            Err(_) => return Err("Could not read Remember Me from macOS Keychain".to_string()),
        }
    }
    Ok(guard.clone())
}

#[tauri::command]
fn clear_application_session(
    state: tauri::State<'_, ApplicationSession>,
) -> Result<(), String> {
    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    *guard = None;
    #[cfg(target_os = "macos")]
    {
        let entry = keyring::Entry::new("com.centralmind.app", "application-session")
            .map_err(|_| "Could not access macOS Keychain".to_string())?;
        match entry.delete_credential() {
            Ok(()) | Err(keyring::Error::NoEntry) => (),
            Err(_) => return Err("Could not remove saved session from macOS Keychain".to_string()),
        }
    }
    Ok(())
}

#[tauri::command]
fn start_speech_to_text(
    app: tauri::AppHandle,
    window: tauri::WebviewWindow,
    state: tauri::State<'_, SpeechProcess>,
    locale: String,
) -> Result<(), String> {
    let locale = locale.trim();
    if locale.is_empty() || locale.len() > 64 {
        return Err("A valid speech recognition locale is required.".to_string());
    }

    let mut active = state.0.lock().map_err(|error| error.to_string())?;
    if let Some(process) = active.clone() {
        let is_running = {
            let mut child = process.lock().map_err(|error| error.to_string())?;
            child.try_wait().map_err(|error| error.to_string())?.is_none()
        };
        if is_running {
            return Err("Speech recognition is already running.".to_string());
        }
        *active = None;
    }

    #[cfg(target_os = "macos")]
    let helper = {
        let executable = std::env::current_exe().map_err(|error| error.to_string())?;
        let contents = executable
            .parent()
            .and_then(std::path::Path::parent)
            .ok_or_else(|| "Could not locate the application bundle.".to_string())?;
        contents.join("Helpers/AI Friend Speech.app/Contents/MacOS/AI Friend Speech")
    };
    #[cfg(not(target_os = "macos"))]
    return Err("Native speech-to-text is currently supported on macOS.".to_string());

    #[cfg(target_os = "macos")]
    {
        if !helper.is_file() {
            return Err(
                "The native speech helper is missing. Reinstall AI Friend to enable dictation."
                    .to_string(),
            );
        }
        let mut child = Command::new(&helper)
            .arg(locale)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|error| format!("Could not launch native speech recognition: {error}"))?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| "Speech helper did not provide an output stream.".to_string())?;
        let stderr = child
            .stderr
            .take()
            .ok_or_else(|| "Speech helper did not provide an error stream.".to_string())?;
        let child = Arc::new(Mutex::new(child));
        *active = Some(Arc::clone(&child));

        let app_for_output = app.clone();
        let window_label = window.label().to_string();
        let process_for_output = Arc::clone(&child);
        let speech_state = Arc::clone(&state.0);
        std::thread::spawn(move || {
            for line in BufReader::new(stdout).lines() {
                match line {
                    Ok(line) => match serde_json::from_str::<serde_json::Value>(&line) {
                        Ok(payload) => {
                            let _ = app_for_output.emit_to(
                                window_label.as_str(),
                                "speech-recognition",
                                payload,
                            );
                        }
                        Err(error) => eprintln!("[speech] invalid helper response: {error}"),
                    },
                    Err(error) => {
                        eprintln!("[speech] failed reading helper output: {error}");
                        break;
                    }
                }
            }

            let process_id = process_for_output
                .lock()
                .ok()
                .map(|process| process.id());
            if let Ok(mut active) = speech_state.lock() {
                let is_same_process = active
                    .as_ref()
                    .and_then(|current| current.lock().ok().map(|process| process.id()))
                    == process_id;
                if is_same_process {
                    *active = None;
                }
            }
        });

        std::thread::spawn(move || {
            for line in BufReader::new(stderr).lines() {
                match line {
                    Ok(line) if !line.is_empty() => eprintln!("[speech] {line}"),
                    Ok(_) => (),
                    Err(error) => {
                        eprintln!("[speech] failed reading helper diagnostics: {error}");
                        break;
                    }
                }
            }
        });
    }
    Ok(())
}

#[tauri::command]
fn stop_speech_to_text(state: tauri::State<'_, SpeechProcess>) -> Result<(), String> {
    let active = state.0.lock().map_err(|error| error.to_string())?;
    let Some(process) = active.as_ref() else {
        return Ok(());
    };
    let mut child = process.lock().map_err(|error| error.to_string())?;
    if let Some(stdin) = child.stdin.as_mut() {
        stdin
            .write_all(b"stop\n")
            .and_then(|()| stdin.flush())
            .map_err(|error| format!("Could not stop speech recognition: {error}"))?;
    }
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
    let is_dev = dev_root.is_some();
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

    if std::net::TcpStream::connect_timeout(
        &"127.0.0.1:8765".parse().unwrap(), std::time::Duration::from_millis(300)
    ).is_ok() {
        return Err("Another AI Friend backend is using port 8765. Quit the other installed/development app before launching this build.".to_string());
    }
    let support = app.path().home_dir().map_err(|e| e.to_string())?
        .join("Library").join("Application Support").join("AI Friend V1");
    let state_dir = if is_dev {
        support.with_file_name("AI Friend V1 Dev").join("state")
    } else {
        support.join("state")
    };
    let installed_python = support.join("runtime").join("venv").join("bin").join("python3");
    let local_python = project_root.join(".venv").join("bin").join("python3");
    let python = if local_python.is_file() {
        local_python.to_string_lossy().to_string()
    } else if installed_python.is_file() {
        installed_python.to_string_lossy().to_string()
    } else {
        "python3".to_string()
    };

    let command = app
        .shell()
        .command(python)
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
        .env("AI_FRIEND_STATE_DIR", state_dir)
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

fn stop_speech(app: &tauri::AppHandle) {
    let state = app.state::<SpeechProcess>();
    let process = match state.0.lock() {
        Ok(mut active) => active.take(),
        Err(_) => None,
    };

    if let Some(process) = process {
        if let Ok(mut child) = process.lock() {
            if let Some(stdin) = child.stdin.as_mut() {
                let _ = stdin.write_all(b"stop\n");
                let _ = stdin.flush();
            }
            let _ = child.kill();
        }
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
        // Register first: a second launch must focus the existing application
        // before setup can spawn another Python backend.
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            let window = app.get_webview_window("chat")
                .or_else(|| app.webview_windows().into_values().next());
            if let Some(window) = window {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(BackendProcess(Mutex::new(None)))
        .manage(SpeechProcess(Arc::new(Mutex::new(None))))
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
            clear_application_session,
            start_speech_to_text,
            stop_speech_to_text
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

                        stop_speech(app);
                        stop_backend(app);
                        app.exit(0);
                    }
                }

                tauri::RunEvent::Exit => {
                    // Defense in depth for menu exits, OS termination paths,
                    // programmatic exits, and any future exit mechanism.
                    stop_speech(app);
                    stop_backend(app);
                }

                _ => {}
            }
        });
}
