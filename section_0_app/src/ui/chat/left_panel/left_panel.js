import {
  sendRaw,
  onMessage,
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

      list.appendChild(item);
    }
  }

  onMessage((msg) => {
    if (msg.op === "inventory_result" && Array.isArray(msg.domains)) {
      renderDomains(msg.domains);
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

  document
    .getElementById("btn-new-chat")
    ?.addEventListener("click", () => {
      conversation.newChat();
      topBar.setTopic("New chat", "general");
    });

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
