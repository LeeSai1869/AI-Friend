export function createCodingTerminal() {
  const panel = document.getElementById("coding-terminal");
  const toggle = document.getElementById("terminal-toggle");

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
  };
}
