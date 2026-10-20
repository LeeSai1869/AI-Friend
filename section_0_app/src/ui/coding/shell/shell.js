import {
  send,
  sendRaw,
  onMessage,
  onAuthenticated,
  sendDomainRequest,
} from "../../shared/auth_session/session.js";

import "../../chat/auth/login_overlay.js";

import {
  createChatIntent,
} from "../../chat/intent/intent.js";

import {
  createChatTopBar,
} from "../../chat/top_bar/top_bar.js";

import {
  openIntake,
} from "../../chat/memory_intake/memory_intake.js";

import {
  createCodingConversation,
} from "../conversation/conversation.js";

import {
  createCodingInput,
} from "../input/input.js";

import {
  createCodingExplorer,
} from "../explorer/explorer.js";

import {
  createCodingEditor,
} from "../editor/editor.js";

import {
  createCodingTerminal,
} from "../terminal/terminal.js";

import {
  createCodingLeftPanel,
} from "../left_panel/left_panel.js";

import {
  createCodingSettings,
} from "../settings/settings.js";

import {
  selectProject,
} from "../project/project.js";

const intent = createChatIntent();
const conversation = createCodingConversation();
const topBar = createChatTopBar();
const editor = createCodingEditor();

createCodingTerminal();
createCodingLeftPanel();
createCodingSettings();

const explorer = createCodingExplorer({
  onFileOpen({ path, content }) {
    editor.openFile(path, content);
  },
});

createCodingInput({
  getIntent: intent.getIntent,

  onSend({ text, intent: selectedIntent }) {
    conversation.appendMessage("user", text);

    send(
      text,
      selectedIntent,
      {
        chat_id: conversation.getChatId(),
        context: {
          surface: "coding",
          active_file: editor.getActivePath(),
          open_files: editor.getOpenFiles(),
        },
      },
    );
  },
});

function requestChats() {
  sendRaw({ op: "list_chats" });
}

function renderChatHistory(chats) {
  const list = document.getElementById("coding-chat-history");
  if (!list) return;

  list.innerHTML = "";

  for (const chat of chats || []) {
    const button = document.createElement("button");
    button.className = "coding-history-item";
    button.textContent = chat.topic || "(untitled)";

    if (conversation.getChatId() === chat.chat_id) {
      button.classList.add("active");
    }

    button.addEventListener("click", () => {
      sendRaw({
        op: "load_chat",
        chat_id: chat.chat_id,
      });
    });

    list.appendChild(button);
  }
}

document
  .getElementById("coding-new-chat")
  ?.addEventListener("click", () => {
    conversation.newChat();
    topBar.setTopic("New chat", "general");
  });

onMessage((msg) => {
  if (
    msg.op === "domain_result" &&
    msg.component === "coder"
  ) {
    if (
      msg.operation === "open_project" ||
      msg.operation === "project_status"
    ) {
      if (!msg.ok) {
        console.error(
          "[coding/project] domain request failed:",
          msg.error || "unknown error",
        );
        return;
      }

      if (
        msg.operation === "open_project" ||
        msg.result?.open ||
        msg.result?.project
      ) {
        explorer.load("");
      }
      return;
    }
  }

  if (msg.op === "chat_loaded") {
    if (!msg.ok) return;

    conversation.restoreChat(msg);

    topBar.setTopic(
      msg.topic || "New chat",
      msg.domain || "general",
    );

    requestChats();
    return;
  }

  if (msg.op === "chats_result") {
    renderChatHistory(msg.chats || []);
    return;
  }

  if (msg.op) return;

  if (msg.role === "tool") {
    conversation.appendToolStatus(msg.text || "");
    return;
  }

  if (
    msg.role !== "mind" &&
    msg.role !== "user" &&
    msg.role !== "system"
  ) {
    return;
  }

  conversation.clearToolStatus();

  conversation.appendMessage(
    msg.role === "user" ? "user" : "mind",
    msg.text ?? "",
    msg.metadata || null,
  );

  if (msg.chat_id) {
    conversation.setChatId(msg.chat_id);
  }

  if (msg.role === "mind") {
    topBar.setTopic(
      msg.topic || "Current chat",
      msg.domain || "general",
    );

    requestChats();
  }
});

document
  .getElementById("btn-open-folder")
  ?.addEventListener("click", async () => {
    try {
      const project = await selectProject();

      if (!project) {
        return;
      }

      console.log(
        "[coding/project] selected:",
        project.root,
      );

      // Opening a project is a Coding Domain operation.  It does not
      // invoke Central Mind cognition.
      sendDomainRequest(
        "coder",
        "open_project",
        { root: project.root },
      );
    } catch (error) {
      console.error(
        "[coding/project] project selection failed:",
        error,
      );
    }
  });

onAuthenticated(() => {
  requestChats();
  sendDomainRequest(
    "coder",
    "project_status",
    {},
  );
});

// Keep the canonical intake module alive in this shell explicitly.
// The left panel owns the visible button.
void openIntake;
