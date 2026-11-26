import { sendRaw } from "../auth_session/session.js";

export function renderChatRows({ list, chats, conversation, isBusy = () => false, itemClass }) {
  list.replaceChildren();
  for (const chat of chats || []) {
    const row = document.createElement("div");
    row.className = "chat-history-row";
    row.dataset.chatId = chat.chat_id;
    const item = document.createElement("button");
    item.className = itemClass;
    item.type = "button";
    item.textContent = chat.topic || "(untitled)";
    if (conversation.getChatId() === chat.chat_id) item.classList.add("active");
    item.onclick = () => {
      if (!isBusy()) sendRaw({ op: "load_chat", chat_id: chat.chat_id });
    };
    const actions = document.createElement("button");
    actions.type = "button";
    actions.className = "icon-btn";
    actions.textContent = "⋯";
    actions.title = "Chat actions";
    actions.setAttribute("aria-label", `Chat actions: ${chat.topic || "Untitled"}`);
    actions.setAttribute("aria-haspopup", "menu");
    actions.setAttribute("aria-expanded", "false");
    const menu = document.createElement("div");
    menu.hidden = true;
    menu.setAttribute("role", "menu");
    menu.className = "chat-history-menu";
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Delete chat";
    remove.setAttribute("role", "menuitem");
    // On macOS, clicking a button can blur the focused menu item before
    // click fires. Preserve focus through the pointer interaction.
    menu.onmousedown = (event) => event.preventDefault();
    actions.onmousedown = (event) => event.preventDefault();
    remove.onclick = () => {
      if (isBusy()) {
        window.alert("Wait for the current reply before deleting a chat.");
        return;
      }
      const sent = sendRaw({ op: "delete_chat", chat_id: chat.chat_id }, { queue: false });
      if (!sent) {
        window.alert("Could not send the delete request. Reconnect and try again.");
        return;
      }
      actions.focus();
      actions.setAttribute("aria-expanded", "false");
      menu.hidden = true;
      remove.disabled = true;
    };
    menu.append(remove);
    actions.onclick = () => {
      const open = menu.hidden;
      list.querySelectorAll('[role="menu"]').forEach(node => { node.hidden = true; });
      list.querySelectorAll('[aria-expanded]').forEach(node => node.setAttribute("aria-expanded", "false"));
      menu.hidden = !open;
      actions.setAttribute("aria-expanded", String(open));
      if (open) remove.focus();
      else actions.focus();
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
