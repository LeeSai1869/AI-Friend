// Memory Intake panel — a separate operation from chat.
// Three screens: source picker, proposal review, confirmation.

import { sendRaw, onMessage } from "../../shared/auth_session/session.js";

let currentProposal = null;

// ---- panel open / close ----------------------------------------

export function openIntake() {
  const overlay = document.getElementById("intake-overlay");
  if (!overlay) return;
  overlay.style.display = "flex";
  showSourceScreen();
}

export function closeIntake() {
  const overlay = document.getElementById("intake-overlay");
  if (!overlay) return;
  overlay.style.display = "none";
  currentProposal = null;
}

// The header close button is permanent HTML shared by Chat and Coding.
// Bind it once when this module loads.
const headerCloseButton = document.getElementById("intake-close");
if (headerCloseButton) {
  headerCloseButton.onclick = closeIntake;
}

// ---- screen 1: pick a source ----------------------------------

function showSourceScreen() {
  const body = document.getElementById("intake-body");
  body.innerHTML = `
    <div class="intake-section">
      <div class="intake-label">Where does the source come from?</div>
      <div class="intake-hint">Use your Trainer account to submit learning material.</div>
      <div class="intake-buttons">
        <button data-action="existing" class="intake-btn">
          🗂  A file in the workspace
        </button>
        <button data-action="file" class="intake-btn">
          📄 A file on disk
        </button>
        <button data-action="folder" class="intake-btn">
          📁 A folder
        </button>
        <button data-action="url" class="intake-btn">
          🌐 A URL
        </button>
        <button data-action="text" class="intake-btn">
          ✏  Paste text
        </button>
      </div>
    </div>
    <div class="intake-footer">
      <button id="intake-cancel-1" class="intake-btn">Cancel</button>
    </div>
  `;

  document.getElementById("intake-cancel-1").onclick = closeIntake;

  body.querySelectorAll(".intake-btn[data-action]").forEach((b) => {
    b.onclick = () => {
      const action = b.getAttribute("data-action");
      if (action === "existing") showExistingPicker();
      else if (action === "file" || action === "folder") showUploadPicker(action);
      else showTextPicker(action);
    };
  });
}

// ---- screen 1b: pick an existing file --------------------------

function showExistingPicker() {
  const body = document.getElementById("intake-body");
  body.innerHTML = `
    <div class="intake-section">
      <div class="intake-label">Enter a path relative to the project root:</div>
      <input id="intake-path" type="text" placeholder="e.g. Readme.md or section_5_domains/coding/requirements.md" />
      <div class="intake-hint">
        Examples: <code>Readme.md</code>, <code>section_5_domains/coding/__manifest__.py</code>
      </div>
    </div>
    <div class="intake-footer">
      <button id="intake-back-1" class="intake-btn">Back</button>
      <button id="intake-propose" class="intake-btn primary">Read and propose</button>
    </div>
  `;

  document.getElementById("intake-back-1").onclick = showSourceScreen;
  document.getElementById("intake-propose").onclick = () => {
    const path = document.getElementById("intake-path").value.trim();
    if (!path) return;
    propose(path);
  };
}

function showError(message) {
  const body = document.getElementById("intake-body");
  body.innerHTML = `<div class="intake-section"><div class="intake-label">Could not import source</div><div class="intake-hint">${escapeHtml(message)}</div></div><button id="intake-retry" class="intake-btn">Back to sources</button>`;
  document.getElementById("intake-retry").onclick = showSourceScreen;
}

function showTextPicker(kind) {
  const body = document.getElementById("intake-body");
  const url = kind === "url";
  body.innerHTML = `<div class="intake-section">
    <label class="intake-label" for="intake-source">${url ? "Source URL" : "Training text"}</label>
    ${url ? '<input id="intake-source" type="url" placeholder="https://example.com/article" />' : '<textarea id="intake-source" rows="12" placeholder="Paste material to learn from"></textarea>'}
    <label for="intake-source-name">${url ? "" : "Source title"}</label>
    ${url ? "" : '<input id="intake-source-name" placeholder="Lesson or reference title" />'}
    <div class="intake-hint">Source material is submitted for evaluation, not accepted as verified knowledge.</div>
    </div><div class="intake-footer"><button id="intake-source-back" class="intake-btn">Back</button><button id="intake-source-submit" class="intake-btn primary">Read and propose</button></div>`;
  document.getElementById("intake-source-back").onclick = showSourceScreen;
  document.getElementById("intake-source-submit").onclick = () => {
    const value = document.getElementById("intake-source").value.trim();
    if (!value) return;
    if (new TextEncoder().encode(value).length > 512 * 1024) return showError("Text exceeds 512 KiB.");
    if (url && !/^https?:\/\//i.test(value)) return showError("Enter a complete HTTP or HTTPS URL.");
    const name = url ? value : (document.getElementById("intake-source-name").value.trim() || "Pasted text");
    proposeSource({ source: { kind, name, ...(url ? {} : { content: value }) } });
  };
}

function showUploadPicker(kind) {
  const body = document.getElementById("intake-body");
  body.innerHTML = `<div class="intake-section"><label class="intake-label" for="intake-upload">${kind === "folder" ? "Choose a folder" : "Choose a file on disk"}</label>
    <input id="intake-upload" type="file" ${kind === "folder" ? "webkitdirectory multiple" : ""} />
    <div class="intake-hint">UTF-8 text, code, Markdown, JSON, CSV or similar text sources. Up to 50 files and 512 KiB total. Images, videos and binary documents require extraction adapters.</div>
    </div><div class="intake-footer"><button id="intake-upload-back" class="intake-btn">Back</button><button id="intake-upload-submit" class="intake-btn primary">Read and propose</button></div>`;
  document.getElementById("intake-upload-back").onclick = showSourceScreen;
  document.getElementById("intake-upload-submit").onclick = async () => {
    const files = Array.from(document.getElementById("intake-upload").files || []);
    if (!files.length) return;
    if (files.length > 50 || files.reduce((total, file) => total + file.size, 0) > 512 * 1024) return showError("Choose at most 50 files with a combined size of 512 KiB.");
    const submit = document.getElementById("intake-upload-submit");
    submit.disabled = true;
    try {
      const entries = [];
      for (const file of files) {
        const content = new TextDecoder("utf-8", { fatal: true }).decode(await file.arrayBuffer());
        if (content.includes("\0")) throw new Error("Binary files are not supported. Select UTF-8 text sources.");
        entries.push({ name: file.webkitRelativePath || file.name, content });
      }
      const name = kind === "folder" ? entries[0].name.split("/")[0] : files[0].name;
      proposeSource({ source: { kind, name, ...(kind === "folder" ? { files: entries } : { content: entries[0].content }) } });
    } catch (error) {
      showError(error.message || "Could not read source files.");
    }
  };
}

function propose(path) { proposeSource({ path }); }

function proposeSource(payload) {
  const body = document.getElementById("intake-body");
  body.innerHTML = '<div class="intake-section"><div class="intake-label">Reading and classifying…</div></div>';
  sendRaw({ op: "intake_propose", ...payload });
}

// ---- screen 2: review proposal --------------------------------

function showProposalScreen(p) {
  currentProposal = p;
  const body = document.getElementById("intake-body");

  const domains = ["Cod", "Img", "Vid", "Trd", "Gen", "Mind", "Chr", "Cap"];
  const kinds = ["fact", "language", "formula", "pattern", "observation", "theory"];

  body.innerHTML = `
    <div class="intake-section">
      <div class="intake-label">Source</div>
      <div class="intake-hint">${escapeHtml(p.source_path)} · ${p.content_bytes} bytes · ${escapeHtml(p.source_kind || "file")}</div>
      <div class="intake-hint">${escapeHtml(p.warning || "")}</div>
      <pre class="intake-preview">${escapeHtml(p.preview || "")}</pre>
    </div>

    <div class="intake-section">
      <div class="intake-label">Classification</div>

      <div class="intake-field">
        <span class="intake-key">Memory class</span>
        <span class="intake-value">${p.memory_class}</span>
      </div>

      <div class="intake-field">
        <span class="intake-key">Domain</span>
        <select id="intake-domain">
          ${domains.map(d => `<option value="${d}" ${d === p.domain ? "selected" : ""}>${d}</option>`).join("")}
        </select>
      </div>

      <div class="intake-field">
        <span class="intake-key">Kind</span>
        <select id="intake-kind">
          ${kinds.map(k => `<option value="${k}" ${k === p.kind ? "selected" : ""}>${k}</option>`).join("")}
        </select>
      </div>

      <div class="intake-field">
        <span class="intake-key">Title</span>
        <input id="intake-title-input" type="text" value="${escapeAttr(p.title)}" />
      </div>

      <div class="intake-field">
        <span class="intake-key">Tags</span>
        <input id="intake-tags-input" type="text" value="${escapeAttr((p.tags || []).join(", "))}" />
      </div>
    </div>

    <div class="intake-footer">
      <button id="intake-back-2" class="intake-btn">Back</button>
      <button id="intake-cancel-2" class="intake-btn">Cancel</button>
      <button id="intake-store" class="intake-btn primary">Submit for review</button>
    </div>
  `;

  document.getElementById("intake-back-2").onclick = showSourceScreen;
  document.getElementById("intake-cancel-2").onclick = closeIntake;
  document.getElementById("intake-store").onclick = () => storeProposal(p);
}

function storeProposal(original) {
  const domain = document.getElementById("intake-domain").value;
  const kind = document.getElementById("intake-kind").value;
  const title = document.getElementById("intake-title-input").value.trim();
  const tagsRaw = document.getElementById("intake-tags-input").value;
  const tags = tagsRaw.split(",").map(t => t.trim()).filter(Boolean);

  const proposal = {
    memory_class: "raw",
    domain,
    kind,
    title,
    tags,
    content: original.content || original.preview || "",
    source_path: original.source_path,
    originator: [{ type: "trainer", name: "user" }],
  };

  const body = document.getElementById("intake-body");
  body.innerHTML = `
    <div class="intake-section">
      <div class="intake-label">Submitting proposal...</div>
    </div>
  `;

  sendRaw({ op: "intake_commit", draft_id: original.draft_id, proposal });
}

// ---- screen 3: confirmation -----------------------------------

function showSubmittedScreen(s) {
  const body = document.getElementById("intake-body");
  body.innerHTML = `
    <div class="intake-section">
      <div class="intake-label">Intake evaluation result</div>
      <div class="intake-hint">${escapeHtml(s.memory_id ? "The evaluated source produced a memory entry." : "No permanent memory entry was created. " + (s.decision_reason || "The proposal remains subject to evaluation."))}</div>
      <div class="intake-field">
        <span class="intake-key">Proposal ID</span>
        <span class="intake-value">${escapeHtml(s.proposal_id || "?")}</span>
      </div>
      <div class="intake-field">
        <span class="intake-key">Status</span>
        <span class="intake-value">${escapeHtml(s.status || "pending")}</span>
      </div>
      <div class="intake-field">
        <span class="intake-key">Domain</span>
        <span class="intake-value">${escapeHtml(s.domain || "?")}</span>
      </div>
      <div class="intake-field">
        <span class="intake-key">Title</span>
        <span class="intake-value">${escapeHtml(s.title || "")}</span>
      </div>
      <div class="intake-field">
        <span class="intake-key">Tags</span>
        <span class="intake-value">${escapeHtml((s.tags || []).join(", "))}</span>
      </div>
    </div>
    <div class="intake-footer">
      <button id="intake-another" class="intake-btn">Intake another</button>
      <button id="intake-close-3" class="intake-btn primary">Close</button>
    </div>
  `;

  document.getElementById("intake-another").onclick = showSourceScreen;
  document.getElementById("intake-close-3").onclick = closeIntake;
}

// ---- WebSocket message handling -------------------------------

onMessage((msg) => {
  if (msg.op === "intake_proposal") {
    if (msg.error) {
      const body = document.getElementById("intake-body");
      body.innerHTML = `
        <div class="intake-section">
          <div class="intake-label">Error</div>
          <div class="intake-hint">${escapeHtml(msg.error)}</div>
        </div>
        <div class="intake-footer">
          <button id="intake-close-err" class="intake-btn">Close</button>
        </div>
      `;
      document.getElementById("intake-close-err").onclick = closeIntake;
      return;
    }
    showProposalScreen(msg.proposal || {});
    return;
  }

  if (msg.op === "intake_proposal_submitted") {
    if (msg.error) {
      const body = document.getElementById("intake-body");
      body.innerHTML = `
        <div class="intake-section">
          <div class="intake-label">Error</div>
          <div class="intake-hint">${escapeHtml(msg.error)}</div>
        </div>
        <div class="intake-footer">
          <button id="intake-close-err2" class="intake-btn">Close</button>
        </div>
      `;
      document.getElementById("intake-close-err2").onclick = closeIntake;
      return;
    }
    showSubmittedScreen(msg);
    return;
  }
});

// ---- helpers --------------------------------------------------

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function escapeAttr(s) {
  return escapeHtml(s).replaceAll('"', "&quot;");
}