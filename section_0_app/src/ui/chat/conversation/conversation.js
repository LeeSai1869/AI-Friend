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
  let persistedTurnCount = 0;
  let feedbackHandler = null;

  function getChatId() {
    return activeChatId;
  }

  function setChatId(chatId) {
    activeChatId = chatId || null;
  }

  function clearThread() {
    persistedTurnCount = 0;
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
    body.textContent = String(text ?? "") || (
      role === "user" && metadata?.attachmentNames?.length
        ? "Please review the attached file(s)."
        : ""
    );

    msg.appendChild(roleEl);
    msg.appendChild(body);

    const transient = metadata?.transient === true;
    const turnIndex = Number.isInteger(metadata?.turnIndex)
      ? metadata.turnIndex
      : persistedTurnCount;
    if (!transient) {
      persistedTurnCount = Math.max(persistedTurnCount, turnIndex + 1);
    }

    if (role === "user" && Array.isArray(metadata?.attachmentNames) && metadata.attachmentNames.length) {
      const attachments = document.createElement("div");
      attachments.className = "msg-attachments";
      attachments.textContent = `Attachments: ${metadata.attachmentNames.join(", ")}`;
      msg.appendChild(attachments);
    }

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
    if (role === "mind" && activeChatId && !transient) {
      const feedback = document.createElement("div");
      feedback.className = "msg-feedback";
      feedback.dataset.turnIndex = String(turnIndex);
      feedback.dataset.chatId = activeChatId;
      feedback.style.cssText = "display:flex;align-items:center;gap:6px;margin-top:8px;flex-wrap:wrap";

      const question = document.createElement("div");
      question.className = "msg-feedback-question";
      question.textContent = "Was this result acceptable? If not, what went wrong or needs changing?";
      question.style.cssText = "flex-basis:100%";

      const comment = document.createElement("input");
      comment.type = "text";
      comment.maxLength = 2000;
      comment.placeholder = "What should be fixed? (optional)";
      comment.setAttribute("aria-label", "What went wrong or should be changed?");
      comment.value = metadata?.feedback?.comment || "";
      comment.style.cssText = "max-width:260px";

      const status = document.createElement("span");
      status.className = "msg-feedback-status";
      status.setAttribute("aria-live", "polite");
      if (metadata?.feedback?.rating) {
        status.textContent = `Feedback recorded: ${metadata.feedback.rating.replace("_", " ")}`;
      }

      for (const [rating, label] of [["helpful", "Helpful"], ["not_helpful", "Not helpful"]]) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = label;
        button.setAttribute("aria-pressed", String(metadata?.feedback?.rating === rating));
        button.onclick = () => {
          if (typeof feedbackHandler !== "function") return;
          button.disabled = true;
          status.textContent = "Saving feedback…";
          feedbackHandler({
            chatId: activeChatId,
            turnIndex,
            rating,
            comment: comment.value,
          });
        };
        feedback.appendChild(button);
      }

      feedback.prepend(question);
      feedback.append(comment, status);
      msg.appendChild(feedback);
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

    turns.forEach((turn, turnIndex) => {
      const role =
        turn.role === "user"
          ? "user"
          : "mind";

      appendMessage(role, turn.text ?? "", {
        turnIndex,
        feedback: turn.feedback,
      });
    });

    if (!turns.length) {
      appendMessage(
        "mind",
        "Ready. What would you like to do?",
        { transient: true },
      );
    }
  }

  function newChat() {
    activeChatId = null;
    clearThread();

    appendMessage(
      "mind",
      "Ready. What would you like to do?",
      { transient: true },
    );
  }

  function setFeedbackHandler(handler) {
    feedbackHandler = typeof handler === "function" ? handler : null;
  }

  function applyFeedbackResult(result) {
    if (!thread || result?.chat_id !== activeChatId) return;
    const feedback = thread.querySelector(
      `.msg-feedback[data-turn-index="${result.turn_index}"][data-chat-id="${result.chat_id}"]`,
    );
    if (!feedback) return;

    const status = feedback.querySelector(".msg-feedback-status");
    const buttons = feedback.querySelectorAll("button");
    buttons.forEach(button => { button.disabled = false; });
    if (!result.ok) {
      if (status) status.textContent = result.error || "Could not save feedback.";
      return;
    }

    const rating = result.feedback?.rating;
    buttons.forEach(button => {
      button.setAttribute(
        "aria-pressed",
        String((rating === "helpful" && button.textContent === "Helpful") ||
          (rating === "not_helpful" && button.textContent === "Not helpful")),
      );
    });
    if (status) {
      status.textContent = `Feedback recorded: ${String(rating || "").replace("_", " ")}`;
    }
  }

  return {
    getChatId,
    setChatId,
    appendMessage,
    appendToolStatus,
    clearToolStatus,
    restoreChat,
    newChat,
    setFeedbackHandler,
    applyFeedbackResult,
  };
}
