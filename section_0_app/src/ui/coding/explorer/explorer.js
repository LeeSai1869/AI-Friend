import { sendDomainRequest, onMessage } from "../../shared/auth_session/session.js";
import { onProjectChange } from "../project/project.js";

export function createCodingExplorer({ onFileOpen }) {
  const tree = document.getElementById("files-tree");
  const cache = new Map();
  const expanded = new Set([""]);
  const requests = new Map();
  let selected = "";
  let projectRoot = "";
  onProjectChange(project => {
    if (project.root === projectRoot) return;
    projectRoot = project.root;
    cache.clear(); requests.clear(); expanded.clear(); expanded.add(""); selected = "";
  });
  function request(path) {
    cache.set(path, { loading: true });
    const id = sendDomainRequest("coder", "list_files", { path });
    requests.set(id, path);
  }
  function load(path = "") {
    expanded.add(path);
    for (const open of expanded) request(open);
    render();
  }
  function renderBranch(path, parent, depth) {
    const state = cache.get(path);
    if (!state || state.loading || state.error) {
      const note = document.createElement("div");
      note.style.paddingLeft = `${depth * 16 + 8}px`;
      note.textContent = state?.error || "Loading…";
      parent.append(note);
      return;
    }
    if (!state.files.length) {
      const empty = document.createElement("div");
      empty.textContent = "Empty folder";
      empty.style.paddingLeft = `${depth * 16 + 8}px`;
      parent.append(empty);
    }
    for (const file of state.files) {
      const directory = file.type === "dir";
      const row = document.createElement("div");
      row.className = "file" + (selected === file.path ? " active-file" : "");
      row.style.paddingLeft = `${depth * 16 + 8}px`;
      row.setAttribute("role", "treeitem");
      row.tabIndex = 0;
      if (directory) row.setAttribute("aria-expanded", String(expanded.has(file.path)));
      const ext = file.name.split('.').pop()?.toLowerCase();
      const icon = directory ? (expanded.has(file.path) ? "▾ 📂" : "▸ 📁") : ({py:"🐍", md:"📝", js:"📜", json:"🔧"}[ext] || "📄");
      row.textContent = `${icon} ${file.name}`;
      row.title = file.path;
      const activate = () => {
        if (directory) {
          if (expanded.has(file.path)) expanded.delete(file.path);
          else { expanded.add(file.path); if (!cache.has(file.path)) request(file.path); }
          render();
        } else {
          selected = file.path; render();
          if (file.text_preview === false) {
            onFileOpen?.({ path: file.path, content: "This file is visible in the project tree, but a text preview is unavailable for this file type." });
          } else sendDomainRequest("coder", "read_file", { path: file.path });
        }
      };
      row.onclick = activate;
      row.onkeydown = event => {
        if (["Enter", " "].includes(event.key)) { event.preventDefault(); activate(); }
      };
      parent.append(row);
      if (directory && expanded.has(file.path)) renderBranch(file.path, parent, depth + 1);
    }
  }
  function render() {
    if (!tree) return;
    tree.replaceChildren();
    tree.setAttribute("role", "tree");
    tree.setAttribute("aria-label", "Project files");
    renderBranch("", tree, 0);
  }
  onMessage(msg => {
    if (msg.op !== "domain_result" || msg.component !== "coder") return;
    if (msg.operation === "list_files" && requests.has(msg.request_id)) {
      const path = requests.get(msg.request_id); requests.delete(msg.request_id);
      cache.set(path, msg.ok ? { files: msg.result?.files || [] } : { error: msg.error || "Could not list folder." });
      render();
    }
    if (msg.operation === "read_file") {
      if (msg.ok) onFileOpen?.({ path: msg.result?.path || "", content: msg.result?.content || "" });
      else onFileOpen?.({ path: selected, content: `Could not read this file: ${msg.error || "unknown error"}` });
    }
  });
  return { load, getCurrentPath: () => "" };
}
