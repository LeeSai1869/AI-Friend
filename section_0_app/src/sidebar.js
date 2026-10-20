import { sendRaw, onMessage } from "./ui/shared/auth_session/session.js";

const DOMAIN_ICONS = {
  general: "💬",
  coder: "💻",
  coding: "💻",
  image: "🎨",
  video: "🎬",
  trading: "📈",
};

// ---- Inventory (domains) --------------------------------------

export function requestInventory() {
  sendRaw({ op: "inventory" });
}

// ---- Chats ----------------------------------------------------

export function requestChats() {
  sendRaw({ op: "list_chats" });
}

// ---- Message handler ------------------------------------------

onMessage((msg) => {
  if (msg.op === "inventory_result" && Array.isArray(msg.domains)) {
    renderDomains(msg.domains);
    return;
  }
  if (msg.op === "chats_result" && Array.isArray(msg.chats)) {
    renderChats(msg.chats);
    return;
  }
});

// ---- Domains --------------------------------------------------

function renderDomains(domains) {
  const list = document.getElementById("domain-list");
  if (!list) return;
  list.innerHTML = "";

  // Section header
  const header = document.createElement("div");
  header.className = "sidebar-group-title";
  header.textContent = "Domains";
  header.style.paddingTop = "12px";
  list.appendChild(header);

  for (const d of domains) {
    // Skip the general domain — it is the default context, not a button.
    if (d.name === "general") continue;

    const btn = document.createElement("button");
    btn.className = "sidebar-new";
    btn.innerHTML = `<span style="font-size:16px">${d.icon}</span> ${d.display_name}`;
    btn.addEventListener("click", () => openDomain(d));
    list.appendChild(btn);
  }
}

async function openDomain(d) {
  if (d.window === "code") {
    try {
      if (window.__TAURI__ && window.__TAURI__.core) {
        await window.__TAURI__.core.invoke("open_code_window");
      } else {
        console.warn("[sidebar] __TAURI__ not available, falling back");
        window.open("window-code.html", "_blank");
      }
    } catch (e) {
      console.error("[sidebar] invoke failed:", e);
      window.open("window-code.html", "_blank");
    }
    return;
  }

  if (d.window === "trading") {
    try {
      if (window.__TAURI__ && window.__TAURI__.core) {
        await window.__TAURI__.core.invoke("open_trading_window");
      } else {
        window.open("window-trading.html", "_blank");
      }
    } catch (e) {
      console.error("[sidebar] trading invoke failed:", e);
      window.open("window-trading.html", "_blank");
    }
    return;
  }

  if (d.window === "chat") {
    const topic = document.querySelector(".chat-topic");
    if (topic) topic.innerHTML = `${d.display_name} <span class="dim">· ${d.name}</span>`;
    const thread = document.getElementById("chat-thread");
    if (thread) {
      thread.innerHTML = "";
      const msg = document.createElement("div");
      msg.className = "msg msg-mind";
      msg.innerHTML = `<div class="msg-role">Central Mind</div><div class="msg-body">${d.display_name} ready.</div>`;
      thread.appendChild(msg);
    }
    return;
  }

  alert(`Custom window for ${d.name} not yet implemented.`);
}

// ---- Chats ----------------------------------------------------

function renderChats(chats) {
  const list = document.getElementById("chat-list");
  if (!list) return;
  list.innerHTML = "";

  if (!chats.length) {
    const empty = document.createElement("div");
    empty.className = "sidebar-group-title";
    empty.textContent = "No chats yet";
    list.appendChild(empty);
    return;
  }

  const groups = {
    "Today": [],
    "Yesterday": [],
    "Last 7 days": [],
    "Last 30 days": [],
    "Older": [],
  };

  const now = Date.now() / 1000;
  const day = 86400;

  for (const c of chats) {
    const age = now - (c.updated_at || c.created_at || 0);
    if (age < day) groups["Today"].push(c);
    else if (age < 2 * day) groups["Yesterday"].push(c);
    else if (age < 7 * day) groups["Last 7 days"].push(c);
    else if (age < 30 * day) groups["Last 30 days"].push(c);
    else groups["Older"].push(c);
  }

  for (const [title, items] of Object.entries(groups)) {
    if (!items.length) continue;
    const header = document.createElement("div");
    header.className = "sidebar-group-title";
    header.textContent = title;
    list.appendChild(header);

    for (const c of items) {
      const icon = DOMAIN_ICONS[c.domain] || "💬";
      const item = document.createElement("div");
      item.className = "sidebar-chat";
      item.dataset.chatId = c.chat_id;
      const short = (c.topic || "(untitled)").slice(0, 42);
      item.innerHTML = `<span>${icon}</span> <span>${short}</span>`;
      item.addEventListener("click", () => openChat(c));
      list.appendChild(item);
    }
  }
}

function openChat(c) {
  // Highlight active.
  document.querySelectorAll(".sidebar-chat").forEach((el) => {
    el.classList.toggle("active", el.dataset.chatId === c.chat_id);
  });
  // Show the chat in the main area (Phase 3 will load the actual messages).
  const topic = document.querySelector(".chat-topic");
  if (topic) {
    topic.innerHTML = `${(c.topic || "Chat").slice(0, 60)} <span class="dim">· ${c.domain}</span>`;
  }
  const thread = document.getElementById("chat-thread");
  if (thread) {
    thread.innerHTML = "";
    const msg = document.createElement("div");
    msg.className = "msg msg-mind";
    msg.innerHTML = `<div class="msg-role">Central Mind</div><div class="msg-body">Loaded chat: ${c.chat_id}</div>`;
    thread.appendChild(msg);
  }
}