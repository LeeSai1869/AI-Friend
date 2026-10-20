export function createChatTopBar() {
  const topic = document.querySelector(".chat-topic");

  function setTopic(title, domain = "general") {
    if (!topic) {
      return;
    }

    topic.innerHTML = "";
    topic.append(document.createTextNode(title || "New chat"));

    const dim = document.createElement("span");
    dim.className = "dim";
    dim.textContent = `· ${domain || "general"}`;

    topic.appendChild(dim);
  }

  return {
    setTopic,
  };
}
