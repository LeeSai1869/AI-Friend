# Coding response protocol and step scope — 2026.10.31.8

The live Mac log confirms correct add_values.py/test_add_values.py content.
It also shows two distinct delays/failures:

- Semantic understanding took 156.52 seconds across provider HTTP 500, HTTP 400
  and a successful third provider. This patch does not diagnose those provider
  errors or claim to eliminate that initial latency.
- The first delegated write step emitted both implementation and test file.
  Mind then ran its separately planned test-file step. Its write returned invalid
  JSON string escaping; repair resources returned bare Python and then a tutorial.
  That is a machine-response contract failure, not evidence the source code or
  actual unittest assertions failed. Empty docker ps output is inconclusive:
  the runner cleans up completed containers.

## Repair

Coding classification, candidate generation and repair now request structured
JSON through Caller and Section 7. The existing provider adapter receives the
JSON mode; routing rejects malformed JSON before accepting a provider response.
The Coding parser still requires an object and validates writes, allowed paths
and Python syntax. There is no permissive eval, bare-code execution or dropped
verification. Repair instructions repeat the actual writes-object schema.
Model selection remains capability-based in the YAML registry; no identities
are added or fixed by this patch.

Coding now distinguishes explicitly named paths in the delegated step objective
from whole-task context. It retains original requirements, but prompts and checks
against the current named-target scope. A scope violation gets one correction;
a repeated violation fails before file access. Conventional test paths can be
included when the current step explicitly asks to create/write/add tests; global
requirements alone cannot widen that step. When no paths are explicitly named,
this additional scope inference makes no claim to identify all allowed targets.

We do not automatically mark later semantic requirements complete because a file
exists. A verified completion contract is needed before skipping such steps.
The current repair avoids early expansion rather than guessing step completion.
Provider status messages on Caller-routed operations now include domain/capability.
This is additional context, not a guarantee of uninterrupted UI progress reporting.

The completed Mac turn's actual Docker test result, final communication and
memory acceptance remain unconfirmed by the supplied model-call log. Preserve
existing generated files and collect the final app response before resubmitting.
Live inference remains a laptop check; cloud model responses are fixtures.

## Additional live-turn findings

New test modules were not automatically included in candidate/persisted behavioral
checks: discovery used only pre-existing inventory unless the classifier named
tests separately. Candidate execution now includes conventional test modules in
the allowed write targets as well as the existing regression suite. This is
verified before any writes by a domain/executor integration regression.

The media-permission UI previously polled every five seconds without tracking an
outstanding reply. Since a long turn serializes session operations, this could
queue redundant messages and contribute to WebSocket backpressure. It now permits
only one outstanding list request, resuming after response or reauthentication.
A Node-executed UI regression confirms 100 unanswered timer ticks send only one
request. This is a fixed transport risk, not proof that the user's particular
stall was a keepalive failure; backend connection/error lines are still needed.

## Recovery and launching

Both Chat and Coding now clear transient thinking/busy state on transport loss
and show an outcome-unknown warning instead of leaving the last model status
visible indefinitely. They do not claim cancellation or replay the task. Browser
integration covers a deliberately dropped turn and reconnection without replay.

The Mac process listing confirmed the worktree backend was already running when
another npm launcher was started. A later command directly invoked the raw
`target/debug/central-mind-app` from HOME; that executable is not the packaged
Applications bundle. Its current startup path selection depends on launch working
directory. No native Mac white-window cause is proven or claimed fixed here.

Use `bash scripts/start_dev.sh` from the updated checkout (or its absolute path).
It validates the checkout, checks port 8765 using lsof, refuses a concurrent
backend, and runs npm from section_0_app. It never kills processes or changes the
installed app. A launcher regression covers paths with spaces, an occupied port,
and the exact working directory. Quit the existing app before using it. Startup
errors/white windows still require native Mac logs; cloud browser fixtures do
not validate native packaging or direct raw-binary launches.

## Validation

Final default suite: 603 tests and 15 subtests passed, 4 optional integrations
skipped. Focused real Chromium/Docker runs passed the coding/repair/memory path,
JSON routing and scope checks, followed by a reconnect/no-replay browser check.
The final browser reconnect run passed 2 tests; the preceding structured/scope
and polling integration runs passed 21 and 16 tests respectively. Models are
controlled fixtures; native Mac launch and live provider behavior remain unverified.
One intervening browser run failed when a container operation took over 30 seconds;
the rerun passed the same assertions without weakening timeouts. Python/JS/shell
syntax and Git whitespace checks passed.
