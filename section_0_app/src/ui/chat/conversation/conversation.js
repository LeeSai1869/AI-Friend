// Chat conversation surface.
//
// Owns only the current UI Chat State:
// - active chat ID
// - rendering/restoring turns
// - per-response resource footer
//
// Durable Chat State remains backend-owned by ChatStore.
// Permanent Memory remains Section 3 and is not managed here.

export function createConversation() {
  const thread = document.getElementById("chat-thread");

  let activeChatId = null;
  let activeToolStatus = null;

  function getChatId() {
    return activeChatId;
  }

  function setChatId(chatId) {
    activeChatId = chatId || null;
  }

  function clearThread() {
    if (!thread) {
      return;
    }

    thread.innerHTML = "";
    activeToolStatus = null;
  }

  function appendMessage(role, text, metadata = null) {
    if (!thread) {
      return;
    }

    const msg = document.createElement("div");
    msg.className =
      role === "user"
        ? "msg msg-user"
        : "msg msg-mind";

    const roleEl = document.createElement("div");
    roleEl.className = "msg-role";
    roleEl.textContent =
      role === "user"
        ? "You"
        : "Central Mind";

    const body = document.createElement("div");
    body.className = "msg-body";
    body.textContent = String(text ?? "");

    msg.appendChild(roleEl);
    msg.appendChild(body);

    if (role !== "user" && Array.isArray(metadata?.artifacts) && metadata.artifacts.length) {
      const artifacts = document.createElement("div");
      artifacts.className = "msg-artifacts";
      artifacts.textContent = "Files: " + metadata.artifacts.join(", ");
      msg.appendChild(artifacts);
    }
    if (role !== "user" && metadata) {
      const footer = resourceFooter(metadata);

      if (footer) {
        msg.appendChild(footer);
      }
    }

    thread.appendChild(msg);
    thread.scrollTop = thread.scrollHeight;
  }

  function resourceFooter(metadata) {
    const executionModel =
      metadata.execution_model ||
      metadata.source_model ||
      metadata.source_llm ||
      "";

    const provider = metadata.provider || "";
    const domain = metadata.domain || "";
    const capability = metadata.capability || "";

    const parts = [];

    if (executionModel) {
      parts.push(`Resource: ${executionModel}`);
    }

    if (provider) {
      parts.push(provider);
    }

    if (domain || capability) {
      const route = [domain, capability]
        .filter(Boolean)
        .join(" / ");

      if (route) {
        parts.push(route);
      }
    }

    if (!parts.length) {
      return null;
    }

    const footer = document.createElement("div");
    footer.className = "msg-resource";
    footer.textContent = parts.join(" · ");

    return footer;
  }

  function clearToolStatus() {
    if (activeToolStatus && activeToolStatus.parentNode) {
      activeToolStatus.parentNode.removeChild(activeToolStatus);
    }

    activeToolStatus = null;
  }

  function appendToolStatus(text) {
    if (!thread) {
      return;
    }

    clearToolStatus();

    const msg = document.createElement("div");
    msg.className = "msg msg-tool";

    const body = document.createElement("div");
    body.className = "msg-body";
    body.textContent = String(text ?? "");

    msg.appendChild(body);
    thread.appendChild(msg);
    activeToolStatus = msg;
    thread.scrollTop = thread.scrollHeight;
  }

  function restoreChat(payload) {
    clearThread();
    setChatId(payload.chat_id);

    const turns = Array.isArray(payload.turns)
      ? payload.turns
      : [];

    for (const turn of turns) {
      const role =
        turn.role === "user"
          ? "user"
          : "mind";

      appendMessage(role, turn.text ?? "");
    }

    if (!turns.length) {
      appendMessage(
        "mind",
        "Ready. What would you like to do?",
      );
    }
  }

  function newChat() {
    activeChatId = null;
    clearThread();

    appendMessage(
      "mind",
      "Ready. What would you like to do?",
    );
  }

  return {
    getChatId,
    setChatId,
    appendMessage,
    appendToolStatus,
    clearToolStatus,
    restoreChat,
    newChat,
  };
}
