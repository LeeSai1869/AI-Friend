export function createCodingTerminal({ requestTests } = {}) {
  const panel = document.getElementById("coding-terminal");
  const toggle = document.getElementById("terminal-toggle");
  const output = document.getElementById("terminal");
  let pendingRequest = null;
  let pendingTimer = null;
  const runButton = document.createElement("button");
  runButton.type = "button";
  runButton.className = "terminal-run-tests";
  runButton.textContent = "Run Python tests";
  runButton.addEventListener("click", () => {
    if (!requestTests || pendingRequest) return;
    setCollapsed(false);
    if (output) output.textContent = "Running project tests…";
    runButton.disabled = true;
    pendingRequest = requestTests();
    pendingTimer = setTimeout(() => {
      pendingRequest = null;
      runButton.disabled = false;
      if (output) output.textContent = "The test request did not finish. Check the connection and test runtime.";
    }, 75000);
  });
  if (requestTests && panel) panel.insertBefore(runButton, output);

  function receiveTestResult(message) {
    if (!pendingRequest || message.request_id !== pendingRequest) return;
    clearTimeout(pendingTimer);
    pendingRequest = null;
    runButton.disabled = false;
    const result = message.result;
    if (output) {
      output.textContent = message.ok
        ? (result?.output || result?.error || "No test output was returned.")
        : (message.error || "The test request failed.");
    }
  }

  let collapsed = false;

  function setCollapsed(next) {
    collapsed = Boolean(next);

    if (panel) {
      panel.classList.toggle(
        "coding-terminal-collapsed",
        collapsed,
      );
    }

    if (toggle) {
      toggle.textContent =
        collapsed ? "Terminal ▲" : "Terminal ▼";
    }
  }

  toggle?.addEventListener("click", () => {
    setCollapsed(!collapsed);
  });

  return {
    setCollapsed,
    isCollapsed: () => collapsed,
    receiveTestResult,
  };
}
