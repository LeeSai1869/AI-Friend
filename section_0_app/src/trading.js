import { getIntent } from "./intents.js";
import { send, onMessage } from "./ui/shared/auth_session/session.js";
import "./ui/chat/auth/login_overlay.js";

const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const thread = document.getElementById("chat-thread");

function appendMessage(role, text) {
  const msg = document.createElement("div");
  msg.className = `msg msg-${role}`;

  msg.innerHTML = `
    <div class="msg-role">
      ${role === "user" ? "You" : "Central Mind"}
    </div>
    <div class="msg-body"></div>
  `;

  msg.querySelector(".msg-body").textContent = text;

  thread.appendChild(msg);
  thread.parentElement.scrollTop =
    thread.parentElement.scrollHeight;
}

function onSubmit() {
  const text = input.value.trim();

  if (!text) return;

  appendMessage("user", text);

  input.value = "";
  input.style.height = "auto";

  send(text, getIntent());
}

sendBtn.addEventListener("click", onSubmit);

input.addEventListener("keydown", (event) => {
  if (
    event.key === "Enter" &&
    (event.metaKey || event.ctrlKey)
  ) {
    event.preventDefault();
    onSubmit();
  }
});

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height =
    Math.min(input.scrollHeight, 160) + "px";
});

onMessage((msg) => {
  if (msg.op) return;

  if (
    msg.role !== "mind" &&
    msg.role !== "user" &&
    msg.role !== "system"
  ) return;

  appendMessage(
    msg.role === "user" ? "user" : "mind",
    msg.text ?? "",
  );
});

document
  .getElementById("btn-back-chat")
  ?.addEventListener("click", async () => {
    try {
      if (
        window.__TAURI__ &&
        window.__TAURI__.core
      ) {
        await window.__TAURI__.core.invoke(
          "open_chat_window"
        );
      } else {
        window.location.href = "window-chat.html";
      }
    } catch (_) {
      window.location.href = "window-chat.html";
    }
  });
