import { getIntent } from "./intents.js";
import { send, onMessage, onAuthenticated } from "./ui/shared/auth_session/session.js";
import { requestInventory, requestChats } from "./sidebar.js";
import { openIntake } from "./intake.js";
import "./ui/chat/auth/login_overlay.js";
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const thread = document.getElementById("chat-thread");

function appendMessage(role, text) {
  const msg = document.createElement("div");
  msg.className = `msg msg-${role}`;
  msg.innerHTML = `<div class="msg-role">${role === "user" ? "You" : "Central Mind"}</div><div class="msg-body"></div>`;
  msg.querySelector(".msg-body").textContent = text;
  thread.appendChild(msg);
  thread.parentElement.scrollTop = thread.parentElement.scrollHeight;
}
function onSubmit() {
  if (!input) return;

  const text = input.value.trim();

  if (!text) return;

  const intent = getIntent();

  appendMessage("user", text);

  input.value = "";
  input.style.height = "auto";

  send(text, intent);
}
if (sendBtn) {
  sendBtn.addEventListener("click", onSubmit);
}
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); onSubmit(); }
});
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 160) + "px";
});
onMessage((msg) => {
  if (msg.op) return;

  if (msg.role === "tool") {
    // Show tool activity as a subtle italic line.
    const el = document.createElement("div");
    el.className = "msg msg-tool";
    el.style.color = "var(--text-dim)";
    el.style.fontStyle = "italic";
    el.style.fontSize = "12px";
    el.style.padding = "2px 0 2px 24px";
    el.textContent = msg.text;
    thread.appendChild(el);
    thread.parentElement.scrollTop = thread.parentElement.scrollHeight;
    return;
  }

  if (msg.role !== "mind" && msg.role !== "user" && msg.role !== "system") return;
  appendMessage(msg.role === "user" ? "user" : "mind", msg.text ?? "");
});
document.getElementById("btn-new-chat")?.addEventListener("click", () => {
  thread.innerHTML = ""; appendMessage("mind", "New chat. What would you like to do?");
});
document.getElementById("btn-search")?.addEventListener("click", () => {
  const box = document.getElementById("search-box");
  box.style.display = box.style.display === "none" ? "block" : "none";
  if (box.style.display === "block") document.getElementById("search-input").focus();
});
document.getElementById("btn-intake")?.addEventListener("click", openIntake);
onAuthenticated(() => {
  requestInventory();
  requestChats();
});
