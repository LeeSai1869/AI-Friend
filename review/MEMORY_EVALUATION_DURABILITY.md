# Recorded memory findings and evaluation durability — 2026.10.31.7

## Laptop findings

Installed state has four legacy Coding success records and three Languages
facts. The report finds no structured approval/test evidence or source references
in those seven records. Their text may still be useful; metadata alone cannot
prove correctness, uselessness or the original validation method.

Development contains the same seven records plus six approved Coding
observations, linked to proposals 7–12. Their journal decisions report passing
review but domain evaluations were not persisted. File source references are
not necessarily links to memory IDs, so zero linked-memory-reference counts do
not automatically mean broken provenance. Zero success/failure counters do not
establish whether source validation occurred or prove the records were never
used; they do not document successful reuse.

All six pending proposals (1–6) are Languages proposals requesting Raw, not
pending Coding examples. They have no saved evaluation or decision reason.
They must not be automatically approved as Raw: system learning and authenticated
Trainer Raw intake have separate authority. No old proposal or stored memory is
automatically rejected, deleted or reclassified by this change.

## Concrete repair

Previously, Mind's proposal handler returned an evaluation to its caller, while
the journal retained only the original submission and eventual decision. Future
assessment history is now saved by Memory Service through a trusted Mind hook,
including explicit ok/testable flags, evaluator, timestamp, evidence and proposal
status at assessment. The hook is not exposed on MemoryClient. Saving an
assessment grants no approval and creates no knowledge entry. Invalid evaluator
flags fail closed into an explicit non-testable result.

Approved entries retain the evaluation used for their approval in their source
provenance. Later revalidation appends another journal assessment; it does not
rewrite the original entry, erase its original approval evidence or silently
reverse the approval. A separate reviewed action would be needed for such a
change. Journal writes are serialized and atomic, with in-memory rollback on
failure. Old missing evaluations are not fabricated or backfilled from counters.

## Next live acceptance test

1. Confirm functional runtime is available (`docker info --format '{{.ServerVersion}}'`).
2. Quit old app/backend and run this source build in development. Open a disposable
   Coding project, confirming its exact path.
3. Ask for add_values.py with add(a: int, b: int) -> int and test_add_values.py
   using unittest to check add(2,3)==5 and add(-2,2)==0. Request execution of tests
   and a report of actual writes/checks/limits.
4. Check code/real tests, received UI result, then a new versioned Coding example
   and durable passing evaluation. No interpreter-only/syntax-only result counts
   as passing this acceptance test. Existing legacy records need no changes.
5. Only after that succeeds, test bounded reuse and measure model calls. A
   repeat task that still calls a model is not yet independent memory execution.

## Runtime prerequisite confirmed on laptop

The user's shell reports `docker: command not found`. That establishes the CLI
is unavailable in that shell, not whether Docker Desktop is absent versus missing
from PATH. This build's functional runner requires Docker. Missing runtime is a
separate blocker from model interpretation or memory persistence.

If Docker Desktop is already installed, open it and check its CLI. Otherwise
install Docker Desktop for Apple Silicon from the official Docker site and open
it. Then run `bash scripts/setup_coding_runtime.sh` from the updated source.
The administrator-run script pulls the official Python base (or an explicit
base argument), resolves its immutable ID, invokes the existing isolated image
builder, checks pytest in an unprivileged network-disabled container, and only
then saves the image ID under Application Support/AI Friend V1/runtime/test-image-id.
It never mounts a user project into the container or disables the app's Guard.
Package/base downloads occur during setup, not during generated-code execution.

Updated backends use the saved ID when AI_FRIEND_TEST_IMAGE is unset. An explicit
environment setting retains precedence. The runner can also locate Docker
Desktop's bundled CLI when GUI launches lack the shell PATH. Docker Desktop must
remain running. This setup helper is not an app/model tool and does not install
Docker Desktop or approve arbitrary image changes automatically. Its shell
syntax and config behavior are tested; native Docker Desktop setup is a laptop
step. No claims that the Mac functional runtime is ready until this succeeds.

## Validation

Final default suite: 594 passed, 4 optional integrations skipped, 15 subtests
passed. A separate focused run passed 12 tests with actual Chromium and Docker,
including the UI/Coding/tested-memory path, media delegation, restart/revalidation
persistence and runtime-config behavior. Model/WhisperKit responses are controlled
fixtures. Setup tests verify no config is saved before readiness. Shell syntax
and Git whitespace checks passed. Docker Desktop installation and live-model
behavior on the user's laptop remain unverified.
