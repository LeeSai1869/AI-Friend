function getDialogOpen() {
  const dialog = window.__TAURI__?.dialog;
  if (!dialog || typeof dialog.open !== "function") {
    throw new Error("Tauri dialog API is unavailable in the Coding window");
  }
  return dialog.open.bind(dialog);
}

let projectName = "No project";
let projectRoot = "";

const listeners = new Set();

export function getProject() {
  return {
    name: projectName,
    root: projectRoot,
  };
}

export function setProject({ name, root }) {
  projectName = name || "Project";
  projectRoot = root || "";

  const state = getProject();

  for (const listener of listeners) {
    try {
      listener(state);
    } catch (_) {}
  }

  return state;
}

export function onProjectChange(listener) {
  listeners.add(listener);

  try {
    listener(getProject());
  } catch (_) {}

  return () => listeners.delete(listener);
}

export async function selectProject() {
  const open = getDialogOpen();

  const selected = await open({
    directory: true,
    multiple: false,
    title: "Open Coding Project",
  });

  if (!selected || typeof selected !== "string") {
    return null;
  }

  const normalized = selected.replace(/[\\/]+$/, "");
  const parts = normalized.split(/[\\/]/).filter(Boolean);

  return {
    name: parts.at(-1) || normalized,
    root: normalized,
  };
}
