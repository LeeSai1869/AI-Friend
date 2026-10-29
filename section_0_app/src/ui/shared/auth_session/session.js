import { BUILD_ID } from "../build.js";
import {
  connect,
  onMessage as onTransportMessage,
  onConnectionChange,
  sendPublic,
  sendProtected,
} from "../transport/backend.js";

let authenticated = false;
let account = null;
let connectionState = "connecting";

const authListeners = new Set();
const readyListeners = new Set();
const messageListeners = new Set();
const protectedQueue = [];

function tauriInvokeAvailable() {
  return Boolean(
    window.__TAURI__ &&
    window.__TAURI__.core &&
    typeof window.__TAURI__.core.invoke === "function"
  );
}

async function setApplicationSession(token, remember = false) {
  if (!token || !tauriInvokeAvailable()) {
    return false;
  }

  try {
    await window.__TAURI__.core.invoke(
      "set_application_session",
      { token, remember },
    );

    return true;
  } catch (error) {
    console.warn(
      "[session] could not store application session",
      error,
    );

    return false;
  }
}

async function getApplicationSession() {
  if (!tauriInvokeAvailable()) {
    return null;
  }

  try {
    return await window.__TAURI__.core.invoke(
      "get_application_session",
    );
  } catch (error) {
    console.warn(
      "[session] could not read application session",
      error,
    );

    return null;
  }
}

async function clearApplicationSession() {
  if (!tauriInvokeAvailable()) {
    return;
  }

  try {
    await window.__TAURI__.core.invoke(
      "clear_application_session",
    );
  } catch (error) {
    console.warn(
      "[session] could not clear application session",
      error,
    );
  }
}

export function isAuthenticated() {
  return authenticated;
}

export function getAccount() {
  return account;
}

export function getConnectionState() {
  return connectionState;
}

export function onAuthStateChange(fn) {
  authListeners.add(fn);

  try {
    fn({
      authenticated,
      account,
      connectionState,
    });
  } catch (_) {}

  return () => authListeners.delete(fn);
}

export function onAuthenticated(fn) {
  readyListeners.add(fn);

  if (authenticated) {
    try {
      fn(account);
    } catch (_) {}
  }

  return () => readyListeners.delete(fn);
}

export function onMessage(fn) {
  messageListeners.add(fn);
  return () => messageListeners.delete(fn);
}

function publishMessage(msg) {
  messageListeners.forEach((fn) => {
    try {
      fn(msg);
    } catch (_) {}
  });
}

function publishAuthState(extra = {}) {
  const state = {
    authenticated,
    account,
    connectionState,
    ...extra,
  };

  authListeners.forEach((fn) => {
    try {
      fn(state);
    } catch (_) {}
  });
}

function publishAuthenticated() {
  readyListeners.forEach((fn) => {
    try {
      fn(account);
    } catch (_) {}
  });
}

function flushProtectedQueue() {
  if (!authenticated) {
    return;
  }

  while (protectedQueue.length) {
    const obj = protectedQueue[0];

    if (!sendProtected(obj)) {
      return;
    }

    protectedQueue.shift();
  }
}

function establishAuthenticatedState(nextAccount) {
  const wasAuthenticated = authenticated;

  authenticated = true;
  account = nextAccount || null;

  publishAuthState();
  flushProtectedQueue();

  if (!wasAuthenticated) {
    publishAuthenticated();
  }
}

function clearAuthenticatedState(extra = {}) {
  authenticated = false;
  account = null;
  publishAuthState(extra);
}

export function requestAuthStatus() {
  sendPublic({ op: "auth_status" });
}

async function attachApplicationSession() {
  const token = await getApplicationSession();

  if (!token) {
    requestAuthStatus();
    return;
  }

  sendPublic({
    op: "attach_session",
    token,
  });
}

export function login(username, password, rememberMe = false) {
  sendPublic({
    op: "login",
    username,
    password,
    remember_me: rememberMe === true,
  });
}

export function logout() {
  sendPublic({ op: "logout" });
}

export function sendRaw(obj) {
  if (authenticated && sendProtected(obj)) {
    return;
  }

  protectedQueue.push(obj);
  connect();
}

let turnSequence = 0;

export function send(text, intent, options = {}) {
  const requestId = `turn-${Date.now()}-${++turnSequence}`;
  const payload = {
    request_id: requestId,
    text,
    intent,
    ts: Date.now(),
  };

  if (options.chat_id) {
    payload.chat_id = options.chat_id;
  }

  if (
    Array.isArray(options.attachments) &&
    options.attachments.length
  ) {
    payload.attachments = options.attachments;
  }

  // Application surfaces may attach arbitrary observational context.
  // Transport carries it unchanged and assigns no semantic authority.
  if (
    options.context &&
    typeof options.context === "object" &&
    !Array.isArray(options.context)
  ) {
    payload.context = options.context;
  }

  sendRaw(payload);
  return requestId;
}

let domainRequestSequence = 0;

export function sendDomainRequest(
  component,
  operation,
  payload = {},
  capability = "application",
) {
  domainRequestSequence += 1;

  const requestId =
    `domain-${Date.now()}-${domainRequestSequence}`;

  sendRaw({
    op: "domain_request",
    request_id: requestId,
    component,
    capability,
    operation,
    payload,
  });

  return requestId;
}

export function listFiles(path) {
  sendRaw({
    op: "list_files",
    path: path || "",
  });
}

export function readFile(path) {
  sendRaw({
    op: "read_file",
    path,
  });
}

onConnectionChange((state) => {
  connectionState = state;

  if (state === "connected") {
    // Every WebSocket is a fresh transport connection. Attempt to bind it
    // to the Tauri application's already authenticated session. The backend
    // still validates the credential independently through AuthService.
    attachApplicationSession();
  }

  if (state === "disconnected") {
    // Transport loss removes authority from this JS context. The opaque
    // credential may remain in Tauri process memory so a reconnect can ask
    // the backend to validate and reattach it.
    authenticated = false;
    account = null;
  }

  publishAuthState();
});

onTransportMessage(async (msg) => {
  if (msg.op === "auth_status_result" || (["login_result", "attach_session_result"].includes(msg.op) && msg.ok)) {
    let badge = document.getElementById("runtime-build");
    if (!badge) {
      badge = document.createElement("div");
      badge.id = "runtime-build";
      badge.style.cssText = "position:fixed;bottom:4px;left:8px;z-index:9999;font-size:11px;max-width:90vw;padding:3px 6px;background:#20232b;color:#aaa;border-radius:4px";
      document.body.append(badge);
    }
    const matches = msg.build_id === BUILD_ID;
    badge.textContent = matches ? `Build ${BUILD_ID} · UI / Mind connected` : `Build mismatch: UI ${BUILD_ID}, Mind ${msg.build_id || "older/unknown"}. Close AI Friend and restart from this checkout.`;
    badge.style.color = matches ? "#aaa" : "#ffb36b";
  }

  if (msg.op === "auth_status_result") {
    const wasAuthenticated = authenticated;

    authenticated = Boolean(msg.authenticated);
    account = msg.account || null;

    publishAuthState({
      authAvailable: msg.auth_available,
      registrationEnabled: msg.registration_enabled,
    });

    if (authenticated) {
      flushProtectedQueue();

      if (!wasAuthenticated) {
        publishAuthenticated();
      }
    }

    return;
  }

  if (msg.op === "login_result") {
    if (msg.ok) {
      // The credential crosses JS only as part of this backend response.
      // Move it immediately into Tauri process memory; do not keep a JS
      // module-level copy and do not persist it in browser storage.
      // The Python backend is the authentication authority and this
      // WebSocket is already authenticated when login_result.ok is true.
      // Tauri process memory is only a convenience credential for attaching
      // additional windows or reconnecting this application runtime. Failure
      // to copy the credential there must not invalidate the authenticated
      // backend connection that already exists.
      const saved = await setApplicationSession(msg.token, msg.remember_me === true);
      if (msg.remember_me && !saved) {
        publishMessage({ role: "system", text: "Signed in, but Remember Me could not be saved in macOS Keychain." });
      }
      establishAuthenticatedState(msg.account);
    } else {
      clearAuthenticatedState({
        loginError: msg.error || "Login failed.",
      });
    }

    return;
  }

  if (msg.op === "attach_session_result") {
    if (msg.ok) {
      establishAuthenticatedState(msg.account);
    } else {
      // The Tauri process held an expired/revoked credential. Remove it so
      // subsequent windows do not repeatedly present stale authentication.
      await clearApplicationSession();

      clearAuthenticatedState({
        loginError: "Session expired. Sign in again.",
      });
    }

    return;
  }

  if (msg.op === "logout_result") {
    await clearApplicationSession();

    clearAuthenticatedState({
      loggedOut: true,
    });

    return;
  }

  if (msg.op === "auth_required") {
    // Backend revalidation is authoritative. Clear any app-scoped credential
    // that no longer validates.
    await clearApplicationSession();

    clearAuthenticatedState({
      loginError:
        msg.error ||
        "Authentication required.",
    });

    return;
  }

  publishMessage(msg);
});

connect();

export function retryCommunication(taskId, chatId) {
  const requestId = `reply-${Date.now()}-${++turnSequence}`;
  sendRaw({ op: "retry_communication", request_id: requestId, task_id: taskId, chat_id: chatId });
  return requestId;
}
