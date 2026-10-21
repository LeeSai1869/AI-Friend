export function createChatInput({ getIntent, onSend }) {
  const input = document.getElementById("input");
  const sendButton = document.getElementById("send");

  let busy = false;
  function setBusy(next) {
    busy = Boolean(next);
    if (sendButton) sendButton.disabled = busy;
    if (input) input.setAttribute("aria-busy", String(busy));
  }

  function submit() {
    if (!input || busy) {
      return false;
    }

    const text = input.value.trim();

    if (!text) {
      return false;
    }

    const intent = getIntent();

    onSend({
      text,
      intent,
    });

    input.value = "";
    input.style.height = "auto";

    return true;
  }

  if (sendButton) {
    sendButton.addEventListener("click", submit);
  }

  if (input) {
    input.addEventListener("keydown", (event) => {
      if (
        event.key === "Enter" &&
        (event.metaKey || event.ctrlKey)
      ) {
        event.preventDefault();
        submit();
      }
    });

    input.addEventListener("input", () => {
      input.style.height = "auto";
      input.style.height =
        Math.min(input.scrollHeight, 160) + "px";
    });
  }

  return {
    submit,
    setBusy,
    isBusy: () => busy,
  };
}
