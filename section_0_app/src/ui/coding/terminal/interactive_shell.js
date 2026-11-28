export function createInteractiveShell() {
  const shellTab = document.getElementById("terminal-shell-tab");
  const testsTab = document.getElementById("terminal-tests-tab");
  const shellView = document.getElementById("terminal-shell-view");
  const testsView = document.getElementById("terminal-tests-view");
  const start = document.getElementById("terminal-open-shell");
  const stop = document.getElementById("terminal-close-shell");
  const status = document.getElementById("terminal-shell-status");
  const tabs = document.getElementById("terminal-session-tabs");
  const screen = document.getElementById("terminal-shell-screen");
  const core = window.__TAURI__?.core;

  let connected = false;
  let project = { name: "", root: "" };
  const sessions = new Map();
  let session = null;
  let opening = false;
  let closing = false;
  let sequence = 0;
  let generation = 0;
  let message = "";

  function render() {
    start.disabled = sessions.size >= 8 || opening || closing || !connected || !project.root || !core?.Channel;
    stop.disabled = !session;
    status.textContent = message || session?.message || (!core?.Channel
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

  function select(active) {
    session = active;
    for (const item of sessions.values()) {
      item.host.hidden = item !== active;
      item.tab.setAttribute("aria-pressed", String(item === active));
    }
    message = "";
    render();
    fit();
    active?.terminal.focus();
  }

  async function close(active = session) {
    if (!active) return;
    sessions.delete(active.id);
    active.terminal.dispose();
    active.host.remove();
    active.tab.remove();
    if (session === active) select([...sessions.values()].at(-1) || null);
    try {
      await active.started;
      await core.invoke("coding_terminal_stop", { id: active.id });
    } catch (error) {
      message = String(error);
    }
    render();
  }

  async function closeAll() {
    const epoch = ++generation;
    closing = true;
    await Promise.all([...sessions.values()].map(close));
    if (epoch === generation) closing = false;
    render();
  }

  async function open() {
    if (start.disabled) return;
    const { root, name } = project;
    const epoch = generation;
    opening = true;
    message = "Starting shell…";
    render();
    let active;
    try {
      const [{ Terminal }, { FitAddon }] = await Promise.all([
        import("../../../vendor/xterm/xterm.mjs"),
        import("../../../vendor/xterm/addon-fit.mjs"),
      ]);
      if (epoch !== generation) return;

      const terminal = new Terminal({
        cursorBlink: true,
        theme: { background: "#181818", foreground: "#f2f2f2" },
      });
      const addon = new FitAddon();
      terminal.loadAddon(addon);
      const host = document.createElement("div");
      host.className = "terminal-session-screen";
      screen.append(host);
      terminal.open(host);
      const id = `coding-shell-${Date.now()}-${++sequence}`;
      const tab = document.createElement("button");
      tab.type = "button";
      tab.textContent = `Shell ${sequence}`;
      tabs.append(tab);
      const events = new core.Channel();
      active = { id, terminal, fit: addon, host, tab, started: null, message: name };
      sessions.set(id, active);
      tab.addEventListener("click", () => select(active));
      select(active);

      events.onmessage = (event) => {
        if (!sessions.has(id)) return;
        if (event.kind === "output") {
          terminal.write(Uint8Array.from(event.bytes));
        } else if (event.kind === "closed") {
          terminal.write("\r\n[Shell exited]\r\n");
          terminal.options.disableStdin = true;
          active.message = "Shell exited.";
          render();
        }
      };

      active.started = core.invoke("coding_terminal_start", {
        id, cwd: root, rows: terminal.rows, cols: terminal.cols, events,
      });
      await active.started;
      if (!sessions.has(id)) return;

      let input = Promise.resolve();
      terminal.onData((text) => {
        input = input.then(async () => {
          if (sessions.has(id)) {
            await core.invoke("coding_terminal_write", { id, text });
          }
        }).catch((error) => {
          if (session === active) {
            active.message = String(error);
            render();
          }
        });
      });
      terminal.onResize(({ rows, cols }) => {
        core.invoke("coding_terminal_resize", { id, rows, cols }).catch((error) => {
          if (session === active) {
            active.message = String(error);
            render();
          }
        });
      });
      if (session === active && !terminal.options.disableStdin) terminal.focus();
    } catch (error) {
      if (active && sessions.has(active.id)) await close(active);
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
  stop.addEventListener("click", () => close());
  render();

  return {
    setProject(next) {
      if (next.root !== project.root) {
        message = "";
        closeAll();
      }
      project = next;
      render();
    },
    setConnected(next) {
      if (connected !== next) message = "";
      connected = next;
      if (!connected) closeAll();
      render();
    },
  };
}
