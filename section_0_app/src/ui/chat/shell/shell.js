import {
  send,
  onMessage,
  onAuthenticated,
} from "../../shared/auth_session/session.js";

import "../auth/login_overlay.js";

import {
  createConversation,
} from "../conversation/conversation.js";

import {
  createChatInput,
} from "../input/input.js";

import {
  createChatIntent,
} from "../intent/intent.js";

import {
  createChatTopBar,
} from "../top_bar/top_bar.js";

import {
  createChatLeftPanel,
} from "../left_panel/left_panel.js";

import {
  openIntake,
} from "../memory_intake/memory_intake.js";

const conversation = createConversation();
const intent = createChatIntent();
const topBar = createChatTopBar();

const leftPanel = createChatLeftPanel({
  conversation,
  topBar,
  onOpenIntake: openIntake,
});

createChatInput({
  getIntent: intent.getIntent,

  onSend({ text, intent: selectedIntent }) {
    conversation.appendMessage("user", text);

    send(
      text,
      selectedIntent,
      {
        chat_id: conversation.getChatId(),
      },
    );
  },
});

onMessage((msg) => {
  if (msg.op) {
    return;
  }

  if (msg.role === "tool") {
    conversation.appendToolStatus(msg.text ?? "");
    return;
  }

  if (
    msg.role !== "mind" &&
    msg.role !== "user" &&
    msg.role !== "system"
  ) {
    return;
  }

  if (msg.chat_id) {
    conversation.setChatId(msg.chat_id);
  }

  // Tool/thinking messages describe an in-progress turn.  Any final
  // conversational response closes that transient status.
  conversation.clearToolStatus();

  conversation.appendMessage(
    msg.role === "user" ? "user" : "mind",
    msg.text ?? "",
    msg.role === "mind"
      ? {
          provider: msg.provider,
          execution_model: msg.execution_model,
          source_model: msg.source_model,
          source_llm: msg.source_llm,
          domain: msg.domain,
          capability: msg.capability,
        }
      : null,
  );

  if (msg.role === "mind") {
    topBar.setTopic(
      msg.topic || "Current chat",
      msg.domain || "general",
    );

    leftPanel.requestChats();
  }
});

onAuthenticated(() => {
  leftPanel.requestInventory();
  leftPanel.requestChats();
});
