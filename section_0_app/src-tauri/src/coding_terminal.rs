use portable_pty::{native_pty_system, Child, CommandBuilder, MasterPty, PtySize};
use serde::Serialize;
use std::io::{Read, Write};
use std::path::Path;
use std::sync::{mpsc, Mutex};
use tauri::{ipc::Channel, State, WebviewWindow};

#[derive(Default)]
pub struct CodingTerminal(Mutex<Option<Session>>);

struct Session {
    id: String,
    master: Box<dyn MasterPty + Send>,
    input: mpsc::SyncSender<String>,
    child: Box<dyn Child + Send + Sync>,
}

impl Drop for Session {
    fn drop(&mut self) {
        if matches!(self.child.try_wait(), Ok(None)) {
            #[cfg(unix)]
            if let Some(group) = self.master.process_group_leader() {
                // A foreground job can have a process group distinct from the shell.
                unsafe { libc::kill(-group, libc::SIGHUP) };
            }
            if self.child.kill().is_ok() {
                let _ = self.child.wait();
            }
        }
    }
}

#[derive(Clone, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum TerminalEvent {
    Output { bytes: Vec<u8> },
    Closed,
}

fn require_coding_window(window: &WebviewWindow) -> Result<(), String> {
    if window.label() == "code" {
        Ok(())
    } else {
        Err("The terminal is available only in the Coding window.".into())
    }
}

fn size(rows: u16, cols: u16) -> PtySize {
    PtySize {
        rows: rows.max(1),
        cols: cols.max(2),
        pixel_width: 0,
        pixel_height: 0,
    }
}

impl CodingTerminal {
    fn with_session<T>(
        &self,
        id: &str,
        action: impl FnOnce(&Session) -> Result<T, String>,
    ) -> Result<T, String> {
        let current = self.0.lock().map_err(|error| error.to_string())?;
        let session = current
            .as_ref()
            .filter(|session| session.id == id)
            .ok_or("The terminal session has closed.")?;
        action(session)
    }

    pub fn close(&self, id: Option<&str>) {
        let session = {
            let Ok(mut current) = self.0.lock() else {
                return;
            };
            if id.is_some_and(|id| current.as_ref().is_none_or(|session| session.id != id)) {
                return;
            }
            current.take()
        };
        drop(session);
    }
}

#[tauri::command]
pub fn coding_terminal_start(
    window: WebviewWindow,
    terminal: State<'_, CodingTerminal>,
    id: String,
    cwd: String,
    rows: u16,
    cols: u16,
    events: Channel<TerminalEvent>,
) -> Result<(), String> {
    require_coding_window(&window)?;
    let directory = Path::new(&cwd);
    if !directory.is_absolute() || !directory.is_dir() {
        return Err("Open a valid Coding project before starting the terminal.".into());
    }

    let mut current = terminal.0.lock().map_err(|error| error.to_string())?;
    if current.is_some() {
        return Err("A Coding terminal session is already open.".into());
    }

    let pty = native_pty_system()
        .openpty(size(rows, cols))
        .map_err(|error| error.to_string())?;
    let mut reader = pty
        .master
        .try_clone_reader()
        .map_err(|error| error.to_string())?;
    let mut writer = pty
        .master
        .take_writer()
        .map_err(|error| error.to_string())?;
    let mut command = CommandBuilder::new_default_prog();
    command.cwd(directory);
    command.env("TERM", "xterm-256color");
    let child = pty
        .slave
        .spawn_command(command)
        .map_err(|error| error.to_string())?;
    drop(pty.slave);

    let (input, incoming) = mpsc::sync_channel::<String>(64);
    std::thread::spawn(move || {
        for text in incoming {
            if writer
                .write_all(text.as_bytes())
                .and_then(|_| writer.flush())
                .is_err()
            {
                break;
            }
        }
    });
    std::thread::spawn(move || {
        let mut buffer = [0; 8192];
        loop {
            match reader.read(&mut buffer) {
                Ok(0) => break,
                Ok(count) => {
                    if events
                        .send(TerminalEvent::Output {
                            bytes: buffer[..count].to_vec(),
                        })
                        .is_err()
                    {
                        break;
                    }
                }
                Err(error) if error.kind() == std::io::ErrorKind::Interrupted => continue,
                Err(_) => break,
            }
        }
        let _ = events.send(TerminalEvent::Closed);
    });

    *current = Some(Session {
        id,
        master: pty.master,
        input,
        child,
    });
    Ok(())
}

#[tauri::command]
pub fn coding_terminal_write(
    window: WebviewWindow,
    terminal: State<'_, CodingTerminal>,
    id: String,
    text: String,
) -> Result<(), String> {
    require_coding_window(&window)?;
    if text.len() > 1024 * 1024 {
        return Err("Terminal input is too large.".into());
    }
    terminal.with_session(&id, |session| {
        session.input.try_send(text).map_err(|error| match error {
            mpsc::TrySendError::Full(_) => "The terminal is busy. Try again.".into(),
            mpsc::TrySendError::Disconnected(_) => "The terminal session has closed.".into(),
        })
    })
}

#[tauri::command]
pub fn coding_terminal_resize(
    window: WebviewWindow,
    terminal: State<'_, CodingTerminal>,
    id: String,
    rows: u16,
    cols: u16,
) -> Result<(), String> {
    require_coding_window(&window)?;
    terminal.with_session(&id, |session| {
        session
            .master
            .resize(size(rows, cols))
            .map_err(|error| error.to_string())
    })
}

#[tauri::command]
pub fn coding_terminal_stop(
    window: WebviewWindow,
    terminal: State<'_, CodingTerminal>,
    id: String,
) -> Result<(), String> {
    require_coding_window(&window)?;
    terminal.close(Some(&id));
    Ok(())
}
