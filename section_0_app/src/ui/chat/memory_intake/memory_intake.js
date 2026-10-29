// Memory Intake panel — a separate operation from chat.
// Three screens: source picker, proposal review, confirmation.

import { sendRaw, onMessage, onAuthenticated } from "../../shared/auth_session/session.js";

let currentProposal = null;
let queueView = false;

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
  queueView = false;
}

// The header close button is permanent HTML shared by Chat and Coding.
// Bind it once when this module loads.
const headerCloseButton = document.getElementById("intake-close");
if (headerCloseButton) {
  headerCloseButton.onclick = closeIntake;
}

// ---- screen 1: pick a source ----------------------------------

function showSourceScreen() {
  queueView = false;
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
      <button id="intake-queue" class="intake-btn">Review processing queue</button>
      <button id="intake-cancel-1" class="intake-btn">Cancel</button>
    </div>
  `;

  document.getElementById("intake-cancel-1").onclick = closeIntake;
  document.getElementById("intake-queue").onclick = () => {
    queueView = true;
    sendRaw({ op: "intake_processing_list" });
  };

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
    if (url && !/^https?:\/\//i.test(value)) return showError("Enter a complete HTTP or HTTPS URL.");
    const name = url ? value : (document.getElementById("intake-source-name").value.trim() || "Pasted text");
    proposeSource({ source: { kind, name, ...(url ? {} : { content: value }) } });
  };
}

function showUploadPicker(kind) {
  const body = document.getElementById("intake-body");
  body.innerHTML = `<div class="intake-section"><label class="intake-label" for="intake-upload">${kind === "folder" ? "Choose a folder" : "Choose a file on disk"}</label>
    <input id="intake-upload" type="file" ${kind === "folder" ? "webkitdirectory multiple" : ""} />
    <div class="intake-hint">Text, PDF (including scanned pages), DOCX, PPTX, XLSX, images and screenshots, and videos are read locally before Central Mind reviews them.</div>
    </div><div class="intake-footer"><button id="intake-upload-back" class="intake-btn">Back</button><button id="intake-upload-submit" class="intake-btn primary">Read and propose</button></div>`;
  document.getElementById("intake-upload-back").onclick = showSourceScreen;
  document.getElementById("intake-upload-submit").onclick = async () => {
    const files = Array.from(document.getElementById("intake-upload").files || []);
    if (!files.length) return;
    const submit = document.getElementById("intake-upload-submit");
    submit.disabled = true;
    try {
      const entries = [];
      for (const file of files) {
        const name = file.webkitRelativePath || file.name;
        entries.push(await readUpload(file, name));
      }
      const name = kind === "folder" ? entries[0].name.split("/")[0] : files[0].name;
      proposeSource({
        source: {
          kind,
          name,
          ...(kind === "folder" ? { files: entries } : entries[0]),
        },
      });
    } catch (error) {
      showError(error.message || "Could not read source files.");
    }
  };
}

async function readUpload(file, name) {
  const extension = name.split(".").pop().toLowerCase();
  const textExtensions = new Set([
    "c", "cc", "cpp", "css", "csv", "go", "h", "html", "htm", "ini",
    "java", "js", "jsx", "json", "log", "md", "mdx", "py", "r", "rs",
    "sh", "sql", "svg", "toml", "ts", "tsx", "txt", "xml", "yaml", "yml",
  ]);
  const isText = file.type.startsWith("text/")
    || ["application/json", "application/xml"].includes(file.type)
    || textExtensions.has(extension);

  if (isText) {
    try {
      const content = await file.text();
      if (content.includes("\0")) {
        throw new Error("contains binary data.");
      }
      return { name, content };
    } catch (error) {
      throw new Error(`Could not read "${name}": ${error.message || "file access failed."}`);
    }
  }

  try {
    const bytes = new Uint8Array(await file.arrayBuffer());
    let binary = "";
    const chunkSize = 0x8000;
    for (let offset = 0; offset < bytes.length; offset += chunkSize) {
      binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
    }
    return { name, data_base64: btoa(binary) };
  } catch (error) {
    throw new Error(`Could not read "${name}": ${error.message || "file access failed."}`);
  }
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
  const questions = Array.isArray(p.intake_questions) && p.intake_questions.length
    ? p.intake_questions.slice(0, 4)
    : ["What is the nature of this material, and what should Central Mind understand it to be?"];

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
        <span class="intake-value">Raw — unverified material for Central Mind analysis</span>
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

    <div class="intake-section">
      <div class="intake-label">Central Mind needs context</div>
      <div class="intake-hint">Your answers help Central Mind interpret this material and decide what analysis or testing is relevant. They are stored with it as Trainer-provided context, not as verified facts. The first answer is required.</div>
      ${questions.map((question, index) => `
        <div class="intake-field">
          <label class="intake-key" for="intake-context-${index}">${escapeHtml(question)}</label>
          <textarea id="intake-context-${index}" rows="2" ${index === 0 ? "required" : ""} placeholder="Your context${index === 0 ? " (required)" : " (optional)"}"></textarea>
        </div>
      `).join("")}
    </div>

    <div class="intake-footer">
      <button id="intake-back-2" class="intake-btn">Back</button>
      <button id="intake-cancel-2" class="intake-btn">Cancel</button>
      <button id="intake-store" class="intake-btn primary">Store as Raw Memory</button>
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
  const questions = Array.isArray(original.intake_questions)
    ? original.intake_questions.slice(0, 4)
    : ["What is the nature of this material, and what should Central Mind understand it to be?"];
  const intakeContext = questions.map((question, index) => ({
    question,
    answer: document.getElementById(`intake-context-${index}`).value.trim(),
  })).filter(item => item.answer);
  if (!intakeContext.length || !intakeContext[0].answer) {
    document.getElementById("intake-context-0").focus();
    return;
  }

  const proposal = {
    memory_class: "raw",
    domain,
    kind,
    title,
    tags,
    content: original.content || original.preview || "",
    source_path: original.source_path,
    intake_context: intakeContext,
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
      <div class="intake-label">Intake stored</div>
      <div id="intake-processing-summary" class="intake-hint">${escapeHtml(s.processing ? `Processing: ${s.processing.processing} · Verification: ${s.processing.verification} · Mind decision: ${s.processing.decision}. ${s.processing.reason || ""}` : "Source is stored; processing status is unavailable.")}</div>
      <div class="intake-hint">${escapeHtml(s.memory_id ? "Stored as Raw Memory. Central Mind can recall it for analysis and testing; it remains unverified until evaluated." : "No memory entry was created.")}</div>
      <div class="intake-field">
        <span class="intake-key">Memory ID</span>
        <span class="intake-value">${escapeHtml(s.memory_id || "?")}</span>
      </div>
      <div class="intake-field">
        <span class="intake-key">Status</span>
        <span class="intake-value">${escapeHtml(s.status || "unknown")}</span>
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
      <button id="intake-processing-retry" class="intake-btn">Re-examine source</button>
      <button id="intake-processing-resume" class="intake-btn">Process queued sources</button>
      <button id="intake-another" class="intake-btn">Intake another</button>
      <button id="intake-close-3" class="intake-btn primary">Close</button>
    </div>
  `;

  document.getElementById("intake-processing-retry").onclick = () => {
    sendRaw({ op: "intake_processing_retry", memory_id: s.memory_id });
  };
  document.getElementById("intake-processing-resume").onclick = () => sendRaw({ op: "intake_processing_resume" });
  document.getElementById("intake-another").onclick = showSourceScreen;
  document.getElementById("intake-close-3").onclick = closeIntake;
}

function showProcessingQueue(rows) {
  const body = document.getElementById("intake-body");
  body.innerHTML = '<div class="intake-section"><div class="intake-label">Raw Memory processing</div><div id="processing-rows"></div></div><div class="intake-footer"><button id="queue-back" class="intake-btn">Back</button><button id="queue-resume" class="intake-btn primary">Process next queued sources</button></div>';
  const list = document.getElementById("processing-rows");
  if (!rows.length) list.textContent = "No Raw sources are queued.";
  for (const row of rows) {
    const record = document.createElement("div");
    record.style.cssText = "padding:10px 0;border-bottom:1px solid var(--border)";
    const text = document.createElement("div");
    text.textContent = `${row.raw_id} · ${row.domain} — Storage: ${row.storage}; Processing: ${row.processing}; Verification: ${row.verification}; Decision: ${row.decision}. ${row.reason || ""}`;
    record.append(text);
    const retry = document.createElement("button");
    retry.className = "intake-btn";
    retry.textContent = "Re-examine";
    retry.onclick = () => { retry.disabled = true; sendRaw({ op: "intake_processing_retry", memory_id: row.raw_id }); };
    record.append(retry);
    list.append(record);
  }
  document.getElementById("queue-back").onclick = showSourceScreen;
  document.getElementById("queue-resume").onclick = () => sendRaw({ op: "intake_processing_resume" });
}

// ---- WebSocket message handling -------------------------------

onAuthenticated(account => {
  if (["trainer", "administrator"].includes(account?.role)) sendRaw({ op: "intake_processing_resume" });
});

onMessage((msg) => {
  if (msg.op === "intake_processing_result") {
    if (queueView) {
      if (!msg.ok) { showError(msg.error || "Could not read processing status."); queueView = false; }
      else if (msg.operation !== "intake_processing_list") sendRaw({ op: "intake_processing_list" });
      else showProcessingQueue(msg.sources || []);
      return;
    }
    const summary = document.getElementById("intake-processing-summary");
    if (summary) {
      summary.textContent = msg.ok ? (msg.sources.length ? msg.sources.map(row => `${row.raw_id}: ${row.processing} · ${row.verification} · ${row.decision}. ${row.reason || ""}`).join("\n") : "No queued sources need processing.") : msg.error;
    }
    return;
  }
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