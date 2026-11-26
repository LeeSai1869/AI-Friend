import {
  sendRaw,
  onMessage,
  onAuthStateChange,
} from "../../shared/auth_session/session.js";

const DOMAIN_ICONS = {
  coding: "⌨",
  coder: "⌨",
  trading: "📈",
  image: "◈",
  video: "▶",
  languages: "文",
  general: "💬",
};

export function createChatLeftPanel({
  conversation,
  topBar,
  onOpenIntake,
}) {
  const pendingDeletes = new Set();

  function requestInventory() {
    sendRaw({ op: "inventory" });
  }

  function requestChats() {
    sendRaw({ op: "list_chats" });
  }

  function renderDomains(domains) {
    const list = document.getElementById("domain-list");

    if (!list) {
      return;
    }

    list.innerHTML = "";

    const visible = domains.filter((domain) => domain.name !== "general");

    if (!visible.length) {
      return;
    }

    const header = document.createElement("div");
    header.className = "sidebar-group-title";
    header.textContent = "Domains";
    list.appendChild(header);

    for (const domain of visible) {
      const button = document.createElement("button");
      button.className = "sidebar-new";

      const icon =
        domain.icon ||
        DOMAIN_ICONS[domain.name] ||
        "🔷";

      button.textContent =
        `${icon} ${domain.display_name || domain.name}`;

      button.addEventListener("click", () => {
        openDomain(domain);
      });

      list.appendChild(button);
    }
  }

  async function openDomain(domain) {
    if (domain.window === "code" || domain.name === "coder" || domain.name === "coding") {
      try {
        if (window.__TAURI__?.core?.invoke) {
          await window.__TAURI__.core.invoke("open_code_window");
          return;
        }
      } catch (error) {
        console.error("[chat/left_panel] code invoke failed:", error);
      }
    }

    if (domain.window === "trading" || domain.name === "trading") {
      try {
        if (window.__TAURI__?.core?.invoke) {
          await window.__TAURI__.core.invoke("open_trading_window");
          return;
        }
      } catch (error) {
        console.error("[chat/left_panel] trading invoke failed:", error);
      }
    }

    topBar.setTopic(
      domain.display_name || domain.name || "New chat",
      domain.name || "general",
    );
  }

  function renderChats(chats) {
    const list = document.getElementById("chat-list");

    if (!list) {
      return;
    }

    list.innerHTML = "";

    for (const chat of chats || []) {
      const item = document.createElement("button");
      item.className = "sidebar-chat";
      item.dataset.chatId = chat.chat_id;

      const title = document.createElement("div");
      title.className = "sidebar-chat-title";
      title.textContent = chat.topic || "(untitled)";

      const meta = document.createElement("div");
      meta.className = "sidebar-chat-meta";
      meta.textContent = chat.domain || "general";

      item.appendChild(title);
      item.appendChild(meta);

      if (conversation.getChatId() === chat.chat_id) {
        item.classList.add("active");
      }

      item.addEventListener("click", () => {
        sendRaw({
          op: "load_chat",
          chat_id: chat.chat_id,
        });
      });

      const row = document.createElement("div");
      row.className = "chat-list-row";

      const actions = document.createElement("details");
      actions.className = "chat-list-actions";

      const toggle = document.createElement("summary");
      toggle.textContent = "⋯";
      toggle.setAttribute("aria-label", `Actions for ${title.textContent}`);

      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "Delete chat";
      remove.disabled = pendingDeletes.has(chat.chat_id);
      remove.addEventListener("click", () => {
        actions.open = false;
        toggle.focus();
        if (!window.confirm(`Permanently delete “${title.textContent}”?`)) {
          return;
        }
        if (!sendRaw({ op: "delete_chat", chat_id: chat.chat_id }, { queue: false })) {
          window.alert("Could not send the delete request. Reconnect and try again.");
          return;
        }
        pendingDeletes.add(chat.chat_id);
        remove.disabled = true;
      });
      actions.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && actions.open) {
          actions.open = false;
          toggle.focus();
        }
      });

      actions.append(toggle, remove);
      row.append(item, actions);
      list.appendChild(row);
    }
  }

  onAuthStateChange(({ authenticated }) => {
    if (!authenticated) pendingDeletes.clear();
  });

  onMessage((msg) => {
    if (msg.op === "inventory_result" && Array.isArray(msg.domains)) {
      renderDomains(msg.domains);
      return;
    }

    if (msg.op === "chat_deleted" && pendingDeletes.delete(msg.chat_id)) {
      if (!msg.ok) {
        window.alert(msg.error || "Could not delete the chat.");
      } else if (conversation.getChatId() === msg.chat_id) {
        startNewChat();
      }
      requestChats();
      return;
    }

    if (msg.op === "chat_loaded") {
      if (!msg.ok) {
        return;
      }

      conversation.restoreChat(msg);
      topBar.setTopic(
        msg.topic || "New chat",
        msg.domain || "general",
      );

      requestChats();
      return;
    }

    if (msg.op === "chats_result" && Array.isArray(msg.chats)) {
      renderChats(msg.chats);
    }
  });

  function startNewChat() {
    conversation.newChat();
    topBar.setTopic("New chat", "general");
  }

  document
    .getElementById("btn-new-chat")
    ?.addEventListener("click", startNewChat);

  document
    .getElementById("btn-search")
    ?.addEventListener("click", () => {
      const box = document.getElementById("search-box");

      if (!box) {
        return;
      }

      box.style.display =
        box.style.display === "none"
          ? "block"
          : "none";

      if (box.style.display === "block") {
        document.getElementById("search-input")?.focus();
      }
    });

  document
    .getElementById("btn-intake")
    ?.addEventListener("click", onOpenIntake);

  return {
    requestInventory,
    requestChats,
    renderDomains,
    renderChats,
  };
}
