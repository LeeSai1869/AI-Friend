import {
  getAccount,
  isAuthenticated,
  logout,
  onAuthStateChange,
} from "../auth_session/session.js";

export function createAccountControls({ onOpenIntake }) {
  const settingsButton = document.getElementById("btn-settings");
  const trainerButton = document.getElementById("btn-trainer");
  let overlay = null;
  let title = null;
  let content = null;
  let mode = "settings";
  let signingOut = false;
  let authState = {
    authenticated: isAuthenticated(),
    account: getAccount(),
  };

  function createButton(label, className, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.textContent = label;
    button.addEventListener("click", onClick);
    return button;
  }

  function ensureOverlay() {
    if (overlay) return;

    overlay = document.createElement("div");
    overlay.className = "account-controls-overlay";
    overlay.hidden = true;

    const dialog = document.createElement("section");
    dialog.className = "account-controls-dialog";
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");

    const header = document.createElement("header");
    header.className = "account-controls-header";
    title = document.createElement("h2");
    const close = createButton("Close", "account-controls-close", closePanel);
    close.setAttribute("aria-label", "Close panel");
    header.append(title, close);

    content = document.createElement("div");
    content.className = "account-controls-content";
    dialog.append(header, content);
    overlay.append(dialog);
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) closePanel();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !overlay.hidden) closePanel();
    });
    document.body.append(overlay);
  }

  function addText(className, value) {
    const element = document.createElement("p");
    element.className = className;
    element.textContent = value;
    content.append(element);
  }

  function signOut() {
    if (signingOut || !authState.authenticated) return;
    signingOut = true;
    render();
    logout();
  }

  function render() {
    if (!overlay || overlay.hidden) return;

    title.textContent = mode === "settings" ? "Settings" : "Trainer mode";
    content.replaceChildren();

    const account = authState.account;
    if (!authState.authenticated || !account) {
      addText("account-controls-message", "Sign in to use account controls.");
      return;
    }

    const role = String(account.role || "user").toLowerCase();
    const username = account.username || account.name || "Signed in";

    if (mode === "settings") {
      addText("account-controls-account", `Signed in as ${username}`);
      addText("account-controls-role", `Role: ${role}`);
      content.append(
        createButton(
          signingOut ? "Signing out…" : "Sign out",
          "account-controls-primary",
          signOut,
        ),
      );
      return;
    }

    if (role === "trainer") {
      addText(
        "account-controls-message",
        "Trainer mode is active for this authenticated account.",
      );
      content.append(
        createButton(
          "Open Memory Intake",
          "account-controls-primary",
          () => {
            closePanel();
            onOpenIntake();
          },
        ),
      );
      return;
    }

    addText(
      "account-controls-message",
      `This account has the ${role} role. Memory Intake requires the designated Trainer account.`,
    );
    content.append(
      createButton(
        signingOut ? "Signing out…" : "Sign out to switch account",
        "account-controls-primary",
        signOut,
      ),
    );
  }

  function openPanel(nextMode) {
    ensureOverlay();
    mode = nextMode;
    signingOut = false;
    overlay.hidden = false;
    render();
    overlay.querySelector(".account-controls-close")?.focus();
  }

  function closePanel() {
    if (overlay) overlay.hidden = true;
  }

  settingsButton?.addEventListener("click", () => openPanel("settings"));
  trainerButton?.addEventListener("click", () => openPanel("trainer"));

  onAuthStateChange((state) => {
    authState = state;
    if (!state.authenticated) signingOut = false;
    render();
  });

  return {
    openSettings: () => openPanel("settings"),
    openTrainerMode: () => openPanel("trainer"),
    close: closePanel,
  };
}
