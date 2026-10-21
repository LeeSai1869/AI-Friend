import { sendRaw } from "../auth_session/session.js";

export function renderChatRows({ list, chats, conversation, isBusy = () => false, itemClass }) {
  list.replaceChildren();
  for (const chat of chats || []) {
    const row = document.createElement("div");
    row.style.cssText = "position:relative;display:flex;align-items:center;gap:4px";
    row.dataset.chatId = chat.chat_id;
    const item = document.createElement("button");
    item.className = itemClass;
    item.style.cssText = "flex:1;min-width:0;text-align:left";
    item.textContent = chat.topic || "(untitled)";
    if (conversation.getChatId() === chat.chat_id) item.classList.add("active");
    item.onclick = () => {
      if (!isBusy()) sendRaw({ op: "load_chat", chat_id: chat.chat_id });
    };
    const actions = document.createElement("button");
    actions.textContent = "⋯";
    actions.title = "Chat actions";
    actions.setAttribute("aria-label", `Chat actions: ${chat.topic || "Untitled"}`);
    actions.setAttribute("aria-haspopup", "menu");
    actions.setAttribute("aria-expanded", "false");
    const menu = document.createElement("div");
    menu.hidden = true;
    menu.setAttribute("role", "menu");
    menu.style.cssText = "position:absolute;right:0;top:100%;z-index:20;padding:6px;background:var(--bg-panel,#20232b);border:1px solid #666;border-radius:6px";
    const remove = document.createElement("button");
    remove.textContent = "Delete chat";
    remove.setAttribute("role", "menuitem");
    remove.style.cssText = "white-space:nowrap;color:#ef8f8f";
    remove.onclick = () => {
      if (isBusy()) return;
      remove.disabled = true;
      sendRaw({ op: "delete_chat", chat_id: chat.chat_id });
      menu.hidden = true;
    };
    menu.append(remove);
    actions.onclick = () => {
      if (isBusy()) return;
      const open = menu.hidden;
      list.querySelectorAll('[role="menu"]').forEach(node => { node.hidden = true; });
      list.querySelectorAll('[aria-expanded]').forEach(node => node.setAttribute("aria-expanded", "false"));
      menu.hidden = !open;
      actions.setAttribute("aria-expanded", String(open));
      if (open) remove.focus();
    };
    row.onkeydown = event => {
      if (event.key === "Escape") {
        menu.hidden = true;
        actions.setAttribute("aria-expanded", "false");
        actions.focus();
      }
    };
    row.onfocusout = event => {
      if (!row.contains(event.relatedTarget)) {
        menu.hidden = true;
        actions.setAttribute("aria-expanded", "false");
      }
    };
    row.append(item, actions, menu);
    list.append(row);
  }
}
