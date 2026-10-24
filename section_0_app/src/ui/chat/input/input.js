export function createChatInput({ getIntent, onSend }) {
  const input = document.getElementById("input");
  const sendButton = document.getElementById("send");
  const attachButton = document.getElementById("chat-attach");
  const filePicker = document.getElementById("chat-file-picker");
  const micButton = document.getElementById("chat-mic");
  const attachmentsView = document.getElementById("input-attachments");
  const statusView = document.getElementById("input-status");

  let busy = false;
  let selectedFiles = [];
  let speechActive = false;
  let speechStarting = false;

  function setStatus(text) {
    if (statusView) statusView.textContent = text;
  }

  function renderAttachments() {
    if (!attachmentsView) return;
    attachmentsView.replaceChildren();
    selectedFiles.forEach((file, index) => {
      const chip = document.createElement("span");
      chip.className = "input-attachment";
      const label = document.createElement("span");
      label.textContent = file.name;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "×";
      remove.setAttribute("aria-label", `Remove ${file.name}`);
      remove.addEventListener("click", () => {
        selectedFiles.splice(index, 1);
        renderAttachments();
      });
      chip.append(label, remove);
      attachmentsView.append(chip);
    });
    attachmentsView.hidden = selectedFiles.length === 0;
  }

  function addFiles(files) {
    const incoming = Array.from(files || []);
    if (!incoming.length) return;
    selectedFiles.push(...incoming);
    renderAttachments();
    setStatus(`${selectedFiles.length} file${selectedFiles.length === 1 ? "" : "s"} attached`);
  }

  async function encodeFile(file) {
    const name = file.name || "pasted-file";
    const extension = name.split(".").pop().toLowerCase();
    const textExtensions = new Set([
      "c", "cc", "cpp", "css", "csv", "go", "h", "html", "htm", "ini",
      "java", "js", "jsx", "json", "log", "md", "mdx", "py", "r", "rs",
      "sh", "sql", "toml", "ts", "tsx", "txt", "xml", "yaml", "yml",
    ]);
    const isText = file.type.startsWith("text/")
      || ["application/json", "application/xml"].includes(file.type)
      || textExtensions.has(extension);
    if (isText) {
      const content = await file.text();
      if (content.includes("\0")) {
        throw new Error(`"${name}" contains binary data and cannot be read as text.`);
      }
      return { name, content };
    }

    const bytes = new Uint8Array(await file.arrayBuffer());
    let binary = "";
    const chunkSize = 0x8000;
    for (let offset = 0; offset < bytes.length; offset += chunkSize) {
      binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
    }
    return { name, data_base64: btoa(binary) };
  }

  function setBusy(next) {
    busy = Boolean(next);
    if (sendButton) sendButton.disabled = busy;
    if (input) input.setAttribute("aria-busy", String(busy));
    if (attachButton) attachButton.disabled = busy;
    if (micButton) micButton.disabled = busy;
  }

  async function submit() {
    if (!input || busy) {
      return false;
    }

    const text = input.value.trim();

    if (!text && !selectedFiles.length) {
      return false;
    }

    setBusy(true);
    setStatus("Preparing attachments…");
    try {
      const attachments = await Promise.all(selectedFiles.map(encodeFile));
      const intent = getIntent();
      onSend({
        text,
        intent,
        attachments,
        attachmentNames: attachments.map((attachment) => attachment.name),
      });
      selectedFiles = [];
      renderAttachments();
      input.value = "";
      input.style.height = "auto";
      setStatus("");
      return true;
    } catch (error) {
      setStatus(error.message || "Could not read the selected attachment.");
      setBusy(false);
      return false;
    }
  }

  if (sendButton) {
    sendButton.addEventListener("click", () => { void submit(); });
  }

  if (attachButton && filePicker) {
    attachButton.addEventListener("click", () => filePicker.click());
    filePicker.addEventListener("change", () => {
      addFiles(filePicker.files);
      filePicker.value = "";
    });
  }

  if (input) {
    input.addEventListener("paste", (event) => {
      const files = Array.from(event.clipboardData?.items || [])
        .filter((item) => item.kind === "file")
        .map((item) => item.getAsFile())
        .filter(Boolean);
      if (files.length) {
        event.preventDefault();
        addFiles(files);
      }
    });
  }

  if (micButton) {
    const tauri = window.__TAURI__;
    if (!tauri?.core?.invoke || !tauri?.event?.listen) {
      micButton.disabled = true;
      micButton.title = "Native speech-to-text is available in the AI Friend macOS app.";
      micButton.setAttribute("aria-label", micButton.title);
    } else {
      tauri.event.listen("speech-recognition", ({ payload }) => {
        if (payload.kind === "started") {
          speechActive = true;
          speechStarting = false;
          micButton.classList.add("recording");
          micButton.setAttribute("aria-label", "Stop speech-to-text");
          micButton.title = "Stop speech-to-text";
          setStatus("Listening… Speak, then press the microphone again to stop.");
          return;
        }
        if (payload.kind === "transcript") {
          if (payload.final && input) {
            const separator = input.value && !/\s$/.test(input.value) ? " " : "";
            input.value += `${separator}${String(payload.text || "").trim()}`;
            input.dispatchEvent(new Event("input", { bubbles: true }));
            setStatus(speechActive ? "Listening…" : "");
          } else if (payload.text) {
            setStatus(`Listening: ${payload.text}`);
          }
          return;
        }
        if (payload.kind === "error") {
          speechActive = false;
          speechStarting = false;
          setStatus(payload.message || "Speech recognition failed.");
        }
        if (payload.kind === "stopped") {
          speechActive = false;
          speechStarting = false;
          setStatus("");
        }
        micButton.classList.remove("recording");
        micButton.setAttribute("aria-label", "Start speech-to-text");
        micButton.title = "Start speech-to-text";
      });
      micButton.addEventListener("click", () => {
        if (speechStarting) return;
        if (speechActive) {
          tauri.core.invoke("stop_speech_to_text").catch((error) => {
            setStatus(`Could not stop speech recognition: ${error}`);
          });
          speechActive = false;
          micButton.classList.remove("recording");
          micButton.setAttribute("aria-label", "Start speech-to-text");
          micButton.title = "Start speech-to-text";
          setStatus("Finishing transcription…");
          return;
        }
        speechStarting = true;
        setStatus("Requesting microphone and speech recognition access…");
        tauri.core.invoke("start_speech_to_text", {
          locale: navigator.language || "en-US",
        }).catch((error) => {
          speechStarting = false;
          setStatus(String(error));
        });
      });
    }
  }

  if (input) {
    input.addEventListener("keydown", (event) => {
      if (
        event.key === "Enter" &&
        (event.metaKey || event.ctrlKey)
      ) {
        event.preventDefault();
        void submit();
      }
    });

    input.addEventListener("input", () => {
      input.style.height = "auto";
      input.style.height =
        Math.min(input.scrollHeight, 160) + "px";
    });
  }

  return {
    submit: () => submit(),
    setBusy,
    isBusy: () => busy,
  };
}
