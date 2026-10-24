export function createChatTopBar() {
  const topic = document.querySelector(".chat-topic");
  const projectContext = document.getElementById("active-project-context");

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

  function setActiveProject(project) {
    if (!projectContext) {
      return;
    }

    projectContext.textContent = project?.name
      ? `Project: ${project.name}`
      : "No active project";
    projectContext.title = project?.root || "";
  }

  return {
    setTopic,
    setActiveProject,
  };
}
