import "../../shared/media_permissions.js";
import {
  send,
  retryCommunication,
  onMessage,
  onAuthenticated,
  onAuthStateChange,
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
import {
  createAccountControls,
} from "../../shared/account_controls/account_controls.js";

const conversation = createConversation();
const intent = createChatIntent();
const topBar = createChatTopBar();
createAccountControls({ onOpenIntake: openIntake });

const leftPanel = createChatLeftPanel({
  conversation,
  topBar,
  onOpenIntake: openIntake,
  isBusy: () => Boolean(pendingTurn),
});

let pendingTurn = null;
const chatInput = createChatInput({
  getIntent: intent.getIntent,

  onSend({ text, intent: selectedIntent, attachments, attachmentNames }) {
    conversation.appendMessage("user", text, { attachmentNames });

    pendingTurn = send(
      text,
      selectedIntent,
      {
        attachments,
        chat_id: conversation.getChatId(),
        context: {
          active_window: {
            kind: "regular",
            surface: "chat",
          },
        },
      },
    );
    chatInput.setBusy(true);
    conversation.appendToolStatus("Thinking…");
  },
});

onAuthStateChange((state) => {
  if (!state.authenticated) {
    pendingTurn = null;
    chatInput.setBusy(false);
  }
});

onMessage((msg) => {
  if (msg.op === "shared_context") {
    topBar.setActiveProject(msg.active_project || null);
    return;
  }
  if (msg.op === "turn_started" && msg.request_id === pendingTurn) {
    conversation.setChatId(msg.chat_id);
    return;
  }
  if (msg.role === "mind" && msg.request_id) {
    if (pendingTurn && msg.request_id !== pendingTurn) return;
    pendingTurn = null;
    chatInput.setBusy(false);
  }
  if (msg.op) {
    return;
  }

  if (msg.role === "tool") {
    if (!pendingTurn || (msg.request_id && msg.request_id !== pendingTurn)) return;
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
          artifacts: msg.artifacts,
          outcome: msg.outcome,
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

window.addEventListener("retry-communication", event => {
  if (pendingTurn) return;
  pendingTurn = retryCommunication(event.detail.taskId, event.detail.chatId);
  chatInput.setBusy(true);
  conversation.appendToolStatus("Retrying explanation; file operations will not repeat…");
});
