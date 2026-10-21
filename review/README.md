# Chat → Mind → Coding → Mind → Chat

Central Mind changes are applied following administrator authorization. The application now carries authenticated Chat turns through generic Mind planning, capability-selected resources, guarded Coding, verified results, final communication, and UI delivery. Coding and Chat windows share one serialized Mind per validated session. Clarification retains the original task and resumes on the next answer; long model/tool calls run off the WebSocket event loop.

Mind remains generic: domains come from manifests and models are chosen from Section 7 YAML capabilities, availability, and contextual tested-use evidence. No concrete LLM is selected in Coding or Mind configuration. Ollama and OpenAI-compatible text-generation providers are supported. Other model runtimes need adapters; installed software alone is not an active resource.

Tested successful observations can pass domain evaluation into the canonical Memory Service. Coding does not rewrite durable memory or core documents. This is evidence-based recall and source scoring, not model-weight training or a guarantee of correct reasoning.

## Validation

The complete suite passed: **455 tests and 15 subtests**, including browser and native-container integration. The browser test exercised login, two connected windows, clarification, a failed candidate, repair, guarded application, persisted-file tests, final Mind communication, Chat rendering, and live editor refresh. Models and the native Tauri window/dialog bridge were deterministic fixtures; auth, HTTP/WebSockets, production UI modules, Guard, filesystem, memory, and Docker execution were real. Screenshot: `test_results/ui-round-trip.png`.

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
