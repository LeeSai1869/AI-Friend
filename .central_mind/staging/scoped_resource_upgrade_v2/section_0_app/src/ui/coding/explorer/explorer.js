import {
  listCodingFiles,
  readCodingFile,
  onMessage,
} from "../../shared/auth_session/session.js";

export function createCodingExplorer({ onFileOpen }) {
  const tree = document.getElementById("files-tree");
  let currentPath = "";

  function load(path = "") {
    currentPath = path || "";
    listCodingFiles(currentPath);
  }

  function render(files, parentPath) {
    if (!tree) return;

    tree.innerHTML = "";

    if (parentPath) {
      const up = document.createElement("div");
      up.className = "file";
      up.textContent = "⬆ ..";

      up.addEventListener("click", () => {
        const parts = parentPath.split("/").filter(Boolean);
        parts.pop();
        load(parts.join("/"));
      });

      tree.appendChild(up);
    }

    for (const file of files || []) {
      const item = document.createElement("div");
      item.className = "file";

      const isDirectory = file.type === "dir";
      const extension =
        file.name.split(".").pop()?.toLowerCase() || "";

      let icon = "📄";

      if (isDirectory) icon = "📁";
      else if (extension === "py") icon = "🐍";
      else if (extension === "md") icon = "📝";
      else if (extension === "json") icon = "🔧";
      else if (extension === "html") icon = "🌐";
      else if (extension === "css") icon = "🎨";
      else if (extension === "js" || extension === "mjs") icon = "📜";
      else if (extension === "rs") icon = "🦀";

      item.textContent = `${icon} ${file.name}`;
      item.title = file.path || file.name;

      if (isDirectory) {
        item.addEventListener("click", () => load(file.path));
      } else {
        item.addEventListener("click", () => {
          tree
            .querySelectorAll(".file")
            .forEach((node) => node.classList.remove("active-file"));

          item.classList.add("active-file");
          readCodingFile(file.path);
        });
      }

      tree.appendChild(item);
    }
  }

  onMessage((msg) => {
    if (msg.op === "coding_files_result") {
      render(msg.files || [], msg.path || "");
      return;
    }

    if (msg.op === "coding_file_content") {
      onFileOpen?.({
        path: msg.path,
        content: msg.content || "",
      });
    }
  });

  return {
    load,
    getCurrentPath: () => currentPath,
  };
}
