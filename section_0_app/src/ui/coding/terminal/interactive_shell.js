export function createInteractiveShell() {
  const shellTab = document.getElementById("terminal-shell-tab");
  const testsTab = document.getElementById("terminal-tests-tab");
  const shellView = document.getElementById("terminal-shell-view");
  const testsView = document.getElementById("terminal-tests-view");
  const start = document.getElementById("terminal-open-shell");
  const stop = document.getElementById("terminal-close-shell");
  const status = document.getElementById("terminal-shell-status");
  const screen = document.getElementById("terminal-shell-screen");
  const core = window.__TAURI__?.core;

  let connected = false;
  let project = { name: "", root: "" };
  let session = null;
  let opening = false;
  let closing = false;
  let sequence = 0;
  let message = "";

  function render() {
    start.disabled = Boolean(session) || opening || closing || !connected || !project.root || !core?.Channel;
    stop.disabled = !session;
    status.textContent = message || (!core?.Channel
      ? "Open the Coding window in the desktop app to use the shell."
      : !connected
        ? "Sign in to use the shell."
        : project.root
          ? project.name
          : "Open a Coding project to start a shell.");
  }

  function fit() {
    if (screen.clientWidth && screen.clientHeight) {
      session?.fit.fit();
    }
  }

  function showShell(visible) {
    shellTab.setAttribute("aria-pressed", String(visible));
    testsTab.setAttribute("aria-pressed", String(!visible));
    shellView.hidden = !visible;
    testsView.hidden = visible;
    if (visible) {
      fit();
      session?.terminal.focus();
    }
  }

  async function close() {
    const active = session;
    if (!active) return;
    session = null;
    closing = true;
    active.terminal.dispose();
    message = "";
    render();
    try {
      await active.started;
      await core.invoke("coding_terminal_stop", { id: active.id });
    } catch (error) {
      message = String(error);
    } finally {
      closing = false;
      render();
    }
  }

  async function open() {
    if (start.disabled) return;
    const { root, name } = project;
    opening = true;
    message = "Starting shell…";
    render();
    let active;
    try {
      const [{ Terminal }, { FitAddon }] = await Promise.all([
        import("../../../vendor/xterm/xterm.mjs"),
        import("../../../vendor/xterm/addon-fit.mjs"),
      ]);
      if (!connected || root !== project.root) return;

      const terminal = new Terminal({
        cursorBlink: true,
        theme: { background: "#181818", foreground: "#f2f2f2" },
      });
      const addon = new FitAddon();
      terminal.loadAddon(addon);
      terminal.open(screen);
      const id = `coding-shell-${Date.now()}-${++sequence}`;
      const events = new core.Channel();
      active = { id, terminal, fit: addon, started: null };
      session = active;
      fit();

      events.onmessage = (event) => {
        if (session !== active) return;
        if (event.kind === "output") {
          terminal.write(Uint8Array.from(event.bytes));
        } else if (event.kind === "closed") {
          terminal.write("\r\n[Shell exited]\r\n");
          terminal.options.disableStdin = true;
          message = "Shell exited. Close it to start another.";
          render();
        }
      };

      active.started = core.invoke("coding_terminal_start", {
        id, cwd: root, rows: terminal.rows, cols: terminal.cols, events,
      });
      await active.started;
      if (session !== active) return;

      let input = Promise.resolve();
      terminal.onData((text) => {
        input = input.then(async () => {
          if (session === active) {
            await core.invoke("coding_terminal_write", { id, text });
          }
        }).catch((error) => {
          if (session === active) {
            message = String(error);
            render();
          }
        });
      });
      terminal.onResize(({ rows, cols }) => {
        core.invoke("coding_terminal_resize", { id, rows, cols }).catch((error) => {
          if (session === active) {
            message = String(error);
            render();
          }
        });
      });
      if (!terminal.options.disableStdin) {
        message = name;
        terminal.focus();
      }
    } catch (error) {
      if (active && session === active) {
        active.terminal.dispose();
        session = null;
      }
      message = String(error);
    } finally {
      opening = false;
      if (!session && message === "Starting shell…") message = "";
      render();
    }
  }

  new ResizeObserver(fit).observe(screen);
  shellTab.addEventListener("click", () => showShell(true));
  testsTab.addEventListener("click", () => showShell(false));
  start.addEventListener("click", open);
  stop.addEventListener("click", close);
  render();

  return {
    setProject(next) {
      if (next.root !== project.root) {
        message = "";
        close();
      }
      project = next;
      render();
    },
    setConnected(next) {
      if (connected !== next) message = "";
      connected = next;
      if (!connected) close();
      render();
    },
  };
}
