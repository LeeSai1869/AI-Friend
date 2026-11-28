export function createCodingTerminal({ requestTests }) {
  const panel = document.getElementById("coding-terminal");
  const toggle = document.getElementById("terminal-toggle");
  const output = document.getElementById("terminal");
  const runButton = document.getElementById("terminal-run-tests");
  const status = document.getElementById("terminal-status");
  let connected = false;
  let projectRoot = "";
  let projectName = "";
  let pendingRequest = null;
  let pendingTimer = null;

  function updateControls() {
    runButton.disabled = !connected || !projectRoot || pendingRequest !== null;
    status.textContent = !connected
      ? "Sign in to connect the terminal."
      : projectRoot
        ? projectName
        : "Open a Coding project to run tests.";
  }

  function finish(text) {
    clearTimeout(pendingTimer);
    pendingRequest = null;
    output.textContent = text;
    updateControls();
  }

  runButton.addEventListener("click", () => {
    if (runButton.disabled) return;
    output.textContent = `Running Python tests in ${projectName}…`;
    try {
      pendingRequest = requestTests();
    } catch (error) {
      finish(error.message || "Could not send the test request.");
      return;
    }
    updateControls();
    pendingTimer = setTimeout(() => {
      finish("No result received. The tests may still be running.");
    }, 75000);
  });

  function receiveTestResult(message) {
    if (pendingRequest === null || message.request_id !== pendingRequest) return;
    const result = message.result;
    finish(message.ok
      ? (result?.output || result?.resource_request?.reason || result?.error || "No test output was returned.")
      : (message.error || "The test request failed."));
  }

  function setConnected(next) {
    if (connected && !next) {
      const interrupted = pendingRequest !== null;
      connected = false;
      finish(interrupted ? "Connection lost before results arrived. The tests may still be running." : "");
      return;
    }
    connected = next;
    updateControls();
  }

  function setProject({ name, root }) {
    if (connected && root !== projectRoot) {
      finish("");
    }
    projectRoot = root;
    projectName = name;
    updateControls();
  }

  function showProjectError(message) {
    setCollapsed(false);
    output.textContent = message;
  }

  function setCollapsed(collapsed) {
    panel.classList.toggle("coding-terminal-collapsed", collapsed);
    toggle.setAttribute("aria-expanded", String(!collapsed));
    toggle.textContent = collapsed ? "Terminal ▸" : "Terminal ▾";
  }

  toggle.addEventListener("click", () => {
    setCollapsed(toggle.getAttribute("aria-expanded") === "true");
  });

  updateControls();
  return { receiveTestResult, setConnected, setProject, showProjectError };
}
