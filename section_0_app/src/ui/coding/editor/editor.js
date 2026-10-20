export function createCodingEditor() {
  const host = document.getElementById("editor");

  const openFiles = new Map();
  let activePath = null;

  function openFile(path, content) {
    if (!path || !host) return;

    openFiles.set(path, String(content ?? ""));
    activePath = path;
    render();
  }

  function closeFile(path) {
    if (!openFiles.has(path)) return;

    openFiles.delete(path);

    if (activePath === path) {
      activePath =
        Array.from(openFiles.keys()).at(-1) || null;
    }

    render();
  }

  function activateFile(path) {
    if (!openFiles.has(path)) return;
    activePath = path;
    render();
  }

  function render() {
    if (!host) return;

    host.innerHTML = "";

    const tabs = document.createElement("div");
    tabs.className = "coding-tabs";

    for (const path of openFiles.keys()) {
      const tab = document.createElement("button");
      tab.className =
        "coding-tab" +
        (path === activePath ? " active" : "");

      const name = document.createElement("span");
      name.textContent = path.split("/").pop() || path;

      const close = document.createElement("span");
      close.className = "coding-tab-close";
      close.textContent = "×";

      close.addEventListener("click", (event) => {
        event.stopPropagation();
        closeFile(path);
      });

      tab.addEventListener("click", () => activateFile(path));

      tab.appendChild(name);
      tab.appendChild(close);
      tabs.appendChild(tab);
    }

    host.appendChild(tabs);

    const body = document.createElement("div");
    body.className = "coding-editor-body";

    if (!activePath) {
      body.classList.add("coding-editor-empty");
      body.textContent = "Editor · no file open";
      host.appendChild(body);
      return;
    }

    const pre = document.createElement("pre");
    pre.className = "coding-code";
    pre.textContent = openFiles.get(activePath) || "";

    body.appendChild(pre);
    host.appendChild(body);
  }

  render();

  return {
    openFile,
    closeFile,
    activateFile,
    getActivePath: () => activePath,
    getOpenFiles: () => Array.from(openFiles.keys()),
  };
}
