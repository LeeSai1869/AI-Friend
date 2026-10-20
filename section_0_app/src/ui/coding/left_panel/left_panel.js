import {
  getAccount,
  onAuthStateChange,
} from "../../shared/auth_session/session.js";

import {
  openIntake,
} from "../../chat/memory_intake/memory_intake.js";

import {
  onProjectChange,
} from "../project/project.js";

export function createCodingLeftPanel() {
  const name = document.getElementById("coding-project-name");
  const root = document.getElementById("coding-project-root");
  const username = document.getElementById("coding-username");

  function renderProject(project) {
    if (name) {
      name.textContent = project.name || "No project";
    }

    if (root) {
      root.textContent = project.root || "";
      root.title = project.root || "";
    }
  }

  function renderAccount(account) {
    if (!username) return;

    const value =
      account?.username ||
      account?.name ||
      "Signed in";

    username.textContent = `👤 ${value}`;
  }

  onProjectChange(renderProject);

  onAuthStateChange((state) => {
    if (state.authenticated) {
      renderAccount(state.account || getAccount());
    } else if (username) {
      username.textContent = "👤 Not signed in";
    }
  });

  document
    .getElementById("btn-intake")
    ?.addEventListener("click", openIntake);

  return {
    renderProject,
    renderAccount,
  };
}
