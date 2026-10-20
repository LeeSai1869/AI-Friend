export const INTENTS = [
  { id: "ask",     label: "Ask",     shortcut: "1", hint: "Get an answer. No changes." },
  { id: "plan",    label: "Plan",    shortcut: "2", hint: "Think through something. No changes." },
  { id: "edit",    label: "Edit",    shortcut: "3", hint: "Change what exists." },
  { id: "create",  label: "Create",  shortcut: "4", hint: "Bring something new into existence." },
  { id: "analyze", label: "Analyze", shortcut: "5", hint: "Examine and report." },
  { id: "execute", label: "Execute", shortcut: "6", hint: "Run a process." },
];
export const DEFAULT_INTENT = "ask";
let currentIntent = DEFAULT_INTENT;
const listeners = new Set();
export function getIntent() { return currentIntent; }
export function setIntent(id) {
  if (!INTENTS.find(i => i.id === id)) return;
  currentIntent = id;
  listeners.forEach(fn => fn(id));
  render();
}
export function onIntentChange(fn) { listeners.add(fn); }
export function render() {
  const bar = document.getElementById("intent-bar");
  if (!bar) return;
  bar.innerHTML = "";
  for (const it of INTENTS) {
    const btn = document.createElement("button");
    btn.className = "intent-btn" + (it.id === currentIntent ? " active" : "");
    btn.textContent = it.label;
    btn.title = it.hint;
    btn.addEventListener("click", () => setIntent(it.id));
    bar.appendChild(btn);
  }
}
document.addEventListener("keydown", (e) => {
  if (!(e.metaKey || e.ctrlKey)) return;
  const match = INTENTS.find(i => i.shortcut === e.key);
  if (match) { e.preventDefault(); setIntent(match.id); }
});
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", render);
} else { render(); }
