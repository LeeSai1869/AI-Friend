import {
  login,
  onAuthStateChange,
} from "../../shared/auth_session/session.js";

function ensureOverlay() {
  let overlay = document.getElementById("auth-overlay");

  if (overlay) {
    return overlay;
  }

  overlay = document.createElement("div");
  overlay.id = "auth-overlay";
  overlay.className = "auth-overlay";

  overlay.innerHTML = `
    <div class="auth-card">
      <div class="auth-title">AI Friend</div>

      <div class="auth-subtitle" id="auth-status">
        Connecting to Central Mind…
      </div>

      <form id="auth-form">
        <input
          id="auth-username"
          autocomplete="username"
          placeholder="Username"
        />

        <input
          id="auth-password"
          type="password"
          autocomplete="current-password"
          placeholder="Password"
        />

        <label class="auth-remember" style="display:flex;align-items:center;gap:8px;margin:12px 0">
          <input id="auth-remember" type="checkbox" style="width:auto" />
          Remember me for 30 days
        </label>
        <button type="submit" class="send-btn">
          Sign in
        </button>
      </form>

      <div class="auth-error" id="auth-error"></div>
    </div>
  `;

  document.body.appendChild(overlay);

  const form = overlay.querySelector("#auth-form");

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    const username = overlay
      .querySelector("#auth-username")
      .value
      .trim();

    const password = overlay
      .querySelector("#auth-password")
      .value;

    const error = overlay.querySelector("#auth-error");

    error.textContent = "";

    if (!username || !password) {
      error.textContent = "Enter username and password.";
      return;
    }

    overlay.querySelector("#auth-status").textContent =
      "Signing in…";

    login(username, password, overlay.querySelector("#auth-remember").checked);
  });

  return overlay;
}

function showOverlay(message, errorMessage = "") {
  const overlay = ensureOverlay();

  overlay.style.display = "flex";
  overlay.querySelector("#auth-status").textContent = message;
  overlay.querySelector("#auth-error").textContent = errorMessage;
}

function hideOverlay() {
  const overlay = ensureOverlay();
  overlay.style.display = "none";
}

onAuthStateChange((state) => {
  if (state.authenticated) {
    hideOverlay();
    return;
  }

  if (state.loginError) {
    showOverlay(
      "Sign in to continue.",
      state.loginError,
    );
    return;
  }

  if (state.authAvailable === false) {
    showOverlay("Authentication service unavailable.");
    return;
  }

  if (state.loggedOut) {
    showOverlay("Signed out.");
    return;
  }

  if (
    state.connectionState === "connecting" ||
    state.connectionState === "disconnected"
  ) {
    showOverlay("Central Mind is starting…");
    return;
  }

  showOverlay("Sign in to continue.");
});

ensureOverlay();
