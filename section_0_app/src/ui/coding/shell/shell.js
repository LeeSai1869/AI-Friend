import {
  onAuthenticated,
  onMessage,
  send,
  sendRaw,
  sendDomainRequest,
} from "../../shared/auth_session/session.js";

import "../../chat/auth/login_overlay.js";

import { createCodingConversation } from "../conversation/conversation.js";
import { createCodingExplorer } from "../explorer/explorer.js";
import { createCodingEditor } from "../editor/editor.js";
import { createCodingInput } from "../input/input.js";
import { createCodingTerminal } from "../terminal/terminal.js";
import { createCodingLeftPanel } from "../left_panel/left_panel.js";
import { selectProject, setProject } from "../project/project.js";
import { createChatIntent } from "../../chat/intent/intent.js";
import { openIntake } from "../../chat/memory_intake/memory_intake.js";
import { createAccountControls } from "../../shared/account_controls/account_controls.js";
import { renderChatRows } from "../../shared/chat_history/chat_history.js";

let pendingTurn = null;
const conversation = createCodingConversation();
const intent = createChatIntent();
const chatHistory = document.getElementById("coding-chat-history");
const chatTopic = document.querySelector(".coding-chat-topbar .chat-topic");

function setChatTopic(title, domain = "general") {
  if (!chatTopic) return;

  chatTopic.replaceChildren(document.createTextNode(title || "Current chat"));
  const suffix = document.createElement("span");
  suffix.className = "dim";
  suffix.textContent = `· ${domain || "general"}`;
  chatTopic.append(suffix);
}

function requestChats() {
  sendRaw({ op: "list_chats" });
}

const editor = createCodingEditor();
const terminal = createCodingTerminal({
  requestTests: () => sendDomainRequest("coder", "run_tests", {}),
});

createCodingLeftPanel();
createAccountControls({ onOpenIntake: openIntake });
const chatInput = createCodingInput({
  getIntent: intent.getIntent,
  onSend({ text, intent: selectedIntent, attachments, attachmentNames }) {
    conversation.appendMessage("user", text, { attachmentNames });
    pendingTurn = send(text, selectedIntent, {
      attachments,
      chat_id: conversation.getChatId(),
      context: {
        active_window: {
          kind: "specialised",
          surface: "coding",
        },
      },
    });
    chatInput.setBusy(true);
    conversation.appendToolStatus("Thinking…");
  },
});

document
  .getElementById("coding-new-chat")
  ?.addEventListener("click", () => {
    if (pendingTurn) return;
    conversation.newChat();
    setChatTopic("Current chat", "general");
  });

const explorer = createCodingExplorer({
  onFileOpen({ path, content }) {
    editor.openFile(path, content);
  },
});

onMessage((msg) => {
  if (msg.op === "chats_changed") {
    requestChats();
    return;
  }

  if (msg.op === "chats_result" && Array.isArray(msg.chats)) {
    if (chatHistory) {
      renderChatRows({
        list: chatHistory,
        chats: msg.chats,
        conversation,
        isBusy: () => Boolean(pendingTurn),
        itemClass: "sidebar-chat",
      });
    }
    return;
  }

  if (msg.op === "chat_loaded") {
    if (!msg.ok || pendingTurn) return;
    conversation.restoreChat(msg);
    setChatTopic(msg.topic || "Current chat", msg.domain || "general");
    requestChats();
    return;
  }

  if (msg.op === "chat_deleted") {
    if (!msg.ok) {
      conversation.appendMessage(
        "system",
        msg.error || "Could not delete chat.",
      );
    } else if (conversation.getChatId() === msg.chat_id) {
      conversation.newChat();
      setChatTopic("Current chat", "general");
    }
    requestChats();
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

  if (msg.op === "artifacts_changed") {
    explorer.load(explorer.getCurrentPath());
    const path = editor.getActivePath();
    if (path && msg.artifacts?.includes(path)) {
      sendDomainRequest("coder", "read_file", { path });
    }
    return;
  }

  if (msg.op === "domain_result" && msg.component === "coder") {
    if (msg.operation === "run_tests") {
      terminal.receiveTestResult(msg);
      return;
    }

    if (
      msg.operation !== "open_project" &&
      msg.operation !== "project_status"
    ) {
      return;
    }

    if (!msg.ok) {
      console.error(
        "[coding/project] domain request failed:",
        msg.error || "unknown error",
      );
      return;
    }

    const project = msg.result?.project;
    if (project?.root) {
      setProject(project);
      explorer.load("");
    } else if (
      msg.operation === "project_status" &&
      msg.result?.open === false
    ) {
      setProject({ name: "No project", root: "" });
    }
    return;
  }

  if (msg.op) return;

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
        }
      : null,
  );

  if (msg.role === "mind") {
    setChatTopic(msg.topic || "Current chat", msg.domain || "general");
    requestChats();
  }
});

document
  .getElementById("btn-open-folder")
  ?.addEventListener("click", async () => {
    try {
      const project = await selectProject();
      if (!project) return;

      sendDomainRequest("coder", "open_project", { root: project.root });
    } catch (error) {
      console.error("[coding/project] project selection failed:", error);
    }
  });

onAuthenticated(() => {
  sendDomainRequest("coder", "project_status", {});
  requestChats();
});
