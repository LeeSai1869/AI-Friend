# Browser tool foundation — 2026.10.31.2

Internet access is not Trainer-only. The desired resolution order is relevant
memory, model reasoning, then internet evidence where information remains
insufficient. This patch provides tools for that policy, not a complete
model-independent fallback orchestrator. An unavailable semantic model still
cannot produce a plan; adding a browser does not fix that existing failure.

## Implemented

- `browser_interact` is dynamically registered beside web_search/web_fetch. Broker
  and Guard inspect declared network origins before execution. HTTP traffic to
  other origins and all WebSockets are blocked; service workers are disabled.
- A fresh isolated Chromium session can open a URL, fill named controls, click,
  read selectors, and wait for a response selector. It returns rendered text,
  links, timestamp, completed steps, blocked requests and explicit truncation.
- No downloads, arbitrary JavaScript actions, stored login profile or memory
  writes are exposed. Page text is unverified external evidence. Clicks can have
  remote effects even when a subsequent operation fails; errors disclose that.
- Coding's existing memory/model/research cycle can request read-only browser
  evidence for rendered sites. Its research channel cannot fill/click. Ordinary
  interaction callers need an authorized domain workflow through the Broker.
- Runtime requirements now include the previously omitted search dependency and
  Playwright. The Mac installer installs Chromium. Development needs
  `python -m pip install -r requirements-runtime.txt` and
  `python -m playwright install chromium` in its venv.
- Coding ambient project evidence includes recursive visible file count and its
  exclusion scope. This supplies a missing fact without asking an LLM to count.
- Built bundles receive read/traverse permissions so administrator ownership does
  not reproduce the earlier mode-700 launch failure. Existing root-owned app
  replacement still needs administrator installation handling; never sudo the
  entire build or package manager.

## Not yet implemented or verified

No universal browser planner, persistent conversation session, logged-in ChatGPT
integration, automated tests on external sites, or browser-to-memory teaching UI
is claimed. A live ChatGPT service may need login, additional approved origins,
streaming transport and site-specific response detection. Ollama remains an API
provider, not a website. There are no hardcoded model identities in this patch.
The existing URL intake still uses web_fetch; browser findings need an explicit
intake/verification workflow before becoming knowledge. Source truth is not
established by browsing. The memory-first solver and offline-model recovery
remain separate unfinished work. File-count evidence does not prove the live
planner/reviewer will now use it correctly.

## Validation

Real Chromium integration against a local practice website fills a question,
clicks Ask, reads its rendered response, and blocks an undeclared external image.
Other tests cover effect declarations, invalid schemes/credentials/actions,
bounds, and nested project file counting. External authenticated services and
Mac packaging are not tested in the cloud.

Default regression suite: 555 passed, 3 optional tests skipped, 15 subtests
passed. The focused real-browser run separately passed all 8 browser tests
before adding the independent nested-file-count regression. Shell syntax and
Git whitespace checks passed.
