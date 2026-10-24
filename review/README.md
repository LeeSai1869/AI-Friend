# Chat → Mind → Coding → Mind → Chat

Central Mind changes are applied following administrator authorization. The application now carries authenticated Chat turns through generic Mind planning, capability-selected resources, guarded Coding, verified results, final communication, and UI delivery. Coding and Chat windows share one serialized Mind per validated session. Clarification retains the original task and resumes on the next answer; long model/tool calls run off the WebSocket event loop.

Mind remains generic: domains come from manifests and models are chosen from Section 7 YAML capabilities, availability, and contextual tested-use evidence. No concrete LLM is selected in Coding or Mind configuration. Ollama and OpenAI-compatible text-generation providers are supported. Other model runtimes need adapters; installed software alone is not an active resource.

Tested successful observations can pass domain evaluation into the canonical Memory Service. Coding does not rewrite durable memory or core documents. This is evidence-based recall and source scoring, not model-weight training or a guarantee of correct reasoning.

## Validation

The complete suite passed: **476 tests and 15 subtests**, including browser and native-container integration. The browser test exercised login, two connected windows, clarification, a failed candidate, repair, guarded application, persisted-file tests, final Mind communication, Chat rendering, and live editor refresh. Models and the native Tauri window/dialog bridge were deterministic fixtures; auth, HTTP/WebSockets, production UI modules, Guard, filesystem, memory, and Docker execution were real. Screenshot: `test_results/ui-round-trip.png`.

Native macOS packaging, duplicate-launch behavior, and inference against the models installed on your Mac still require a Mac check. Linux native compilation is blocked by missing GLib development libraries. Tauri now registers its single-instance plugin and prefers the repository virtual environment for its Python backend. Normal startup no longer launches the documentation-rewriting Designer watcher.

## Setup and run

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
npm ci --prefix section_0_app
. .venv/bin/activate
npm run dev --prefix section_0_app
```

Declare resources and capabilities in Section 7 YAML. Check Ollama availability with `curl --fail http://127.0.0.1:11434/api/tags`; use `OLLAMA_HOST` or per-resource `api_url` for another host. The cloud environment cannot access models bound to your Mac's localhost.

For behavioral Coding execution, configure the reviewed Docker image described in [CODING.md](CODING.md), export `AI_FRIEND_TEST_IMAGE`, and use an authenticated Trainer. Execution is denied to other roles under the existing policy. Missing runtimes produce a resource request rather than applying an untested candidate.

```sh
.venv/bin/python -m pytest tests -q
# Optional full browser/container integration:
.venv/bin/python -m pip install -r requirements-e2e.txt
.venv/bin/python -m playwright install chromium
AI_FRIEND_RUN_BROWSER_TESTS=1 AI_FRIEND_RUN_CONTAINER_TESTS=1 \
  .venv/bin/python -m pytest tests -q
```

The optional checks require Docker and an exported immutable `AI_FRIEND_TEST_IMAGE`. Default runs skip them. See [CODING.md](CODING.md) for execution limits and operational details.

## Laptop feedback fixes

The model HTTP connectors now carry the structured-output requirement to Ollama
(`format: json`) and OpenAI-compatible endpoints (`response_format`). YAML's
`routing.structured_generation` configures the structured-task output/context
budget and thinking option; a resource's `generation` settings can override it.
Ollama context is capped to the resource's declared context window. Empty,
reasoning-only and truncated answers are distinguished from unavailable models,
unreachable services, timeouts and invalid JSON. Mind includes sanitized per-model
attempts in a failure response, and live status names the selected resource.
The trainer-reported `qwen3.5:27b` resource is registered without an invented
quality score. Installed runtime capability flags do not constitute quality
measurements or change Guard permissions.

After updating the branch, test the actual Mac service without running tools or
writing memory:

```sh
source .venv/bin/activate
python scripts/check_models.py
python scripts/check_models.py --semantic
```

The second command uses the production semantic prompt and trusted manifest
catalog, with models selected from YAML. It can take several minutes. A passing
cloud fixture does not establish successful inference on the separate Mac.

Memory intake now accepts explicitly selected disk text files, folders of text
files, HTTP(S) URLs and pasted text, in addition to workspace files. Previewing
uses capability routing; when automatic classification fails, manual review
remains available with an explicit warning. The server retains the complete
source per authenticated session and submits that source rather than its preview.
Memory Intake has no application-imposed file-count or content-size cap.
Binary documents, images and video need extraction adapters; they are not treated
as readable text. URL fetching uses Guard and HTTP text/HTML extraction, without
requiring html2text.
Imported proposals retain source provenance and hashes. Submission is not a claim
of verified knowledge: the result displays the actual learning decision and reason.

Chat and Coding have a three-dot menu with Delete chat. Authenticated history is
scoped to the signed-in account, and deletion is an explicit human application
operation. It does not grant Mind a deletion capability or delete project files or
permanent memory. History updates and deletion synchronize between windows in the
same validated session. Legacy unowned chat files are retained rather than silently
assigned to an arbitrary account. Only the Administrator sees these older
histories, labeled **Older, unassigned**, and can remove them using the same menu.

## Updating an installed Mac application

An installed `.app` contains its own frontend and Python source. Pulling Git
changes in the checkout does **not** update that installed bundle. Quit AI Friend
and run the following from the checkout:

```sh
git pull --ff-only origin integration/full-coding-loop
bash scripts/update_macos_app.sh
```

The updater requires Python 3, Node/npm, Rust/Cargo and the normal Tauri/Xcode
build prerequisites on the Mac. It builds the app bundle, installs a private
Python runtime for Finder launches, backs up the existing `/Applications/AI
Friend.app`, and installs the freshly built app. Pass a different applications
directory as its first argument if needed. It refuses to proceed while port
8765 has a listener, and never kills processes. Existing unowned histories stay
visible only to Administrator after migration.

Build **2026.10.21.3** displays a UI/backend identity badge in the lower left.
A mismatch means a different/older backend is serving the window. The desktop
also refuses to start over an occupied backend port. The installed backend uses
`~/Library/Application Support/AI Friend V1/state` for durable Chat and Memory
state; the updater copies old bundle data there only if no destination data
exists. A complete backup of the old application is retained under the same
application-support directory before replacement. Authentication continues to
use the existing private account database.

**Remember Me** is opt-in for 30 days. It stores only the backend-issued revocable
session token in macOS Keychain. Passwords and session tokens are not stored in
web storage. A normal login remains limited to the configured session lifetime;
logout or a newer login revokes the previous token. The backend validates the
remembered token again whenever a window attaches. Native Keychain access and
native app installation must be checked on macOS; cloud browser tests use a
controlled native bridge, with real authentication and expiry/revocation checks.

The explorer now expands nested directories in place and displays asset and
lockfiles as well as text files. Binary assets are visible without being fed to
text-based reasoning. Late progress messages from an already completed Chat turn
are ignored.
