const BACKEND_URL = "ws://127.0.0.1:8765";

let socket = null;
let reconnectTimer = null;
let connectionState = "disconnected";

const messageListeners = new Set();
const connectionListeners = new Set();

export function onMessage(fn) {
  messageListeners.add(fn);
  return () => messageListeners.delete(fn);
}

export function getConnectionState() {
  return connectionState;
}

export function onConnectionChange(fn) {
  connectionListeners.add(fn);

  // Connection state is durable state, not a transient event.
  // A component subscribing after transport startup must still learn
  // whether the backend is already connected.
  try {
    fn(connectionState);
  } catch (_) {}

  return () => connectionListeners.delete(fn);
}

function publishConnection(state) {
  connectionState = state;

  connectionListeners.forEach((fn) => {
    try {
      fn(state);
    } catch (_) {}
  });
}

function publishMessage(msg) {
  messageListeners.forEach((fn) => {
    try {
      fn(msg);
    } catch (_) {}
  });
}

export function isConnected() {
  return Boolean(
    socket &&
    socket.readyState === WebSocket.OPEN
  );
}

export function connect() {
  if (
    socket &&
    (
      socket.readyState === WebSocket.OPEN ||
      socket.readyState === WebSocket.CONNECTING
    )
  ) {
    return;
  }

  publishConnection("connecting");

  try {
    socket = new WebSocket(BACKEND_URL);

    socket.onopen = () => {
      console.log("[transport] connected");
      publishConnection("connected");
    };

    socket.onmessage = (event) => {
      let msg;

      try {
        msg = JSON.parse(event.data);
      } catch (_) {
        msg = { text: event.data };
      }

      publishMessage(msg);
    };

    socket.onclose = () => {
      console.log("[transport] disconnected");

      socket = null;
      publishConnection("disconnected");

      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }

      reconnectTimer = setTimeout(connect, 2000);
    };

    socket.onerror = () => {};
  } catch (error) {
    console.warn("[transport] connection failed", error);
    publishConnection("disconnected");

    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
    }

    reconnectTimer = setTimeout(connect, 2000);
  }
}

export function sendPublic(obj) {
  if (isConnected()) {
    socket.send(JSON.stringify(obj));
    return;
  }

  connect();

  const attempt = () => {
    if (isConnected()) {
      socket.send(JSON.stringify(obj));
      return;
    }

    setTimeout(attempt, 100);
  };

  attempt();
}

export function sendProtected(obj) {
  if (!isConnected()) {
    return false;
  }

  socket.send(JSON.stringify(obj));
  return true;
}

connect();
