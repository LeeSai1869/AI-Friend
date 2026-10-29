# Execution milestone: steps 1–5

Base: laptop snapshot `cb5cdf7`. This branch preserves the existing three-loop
architecture. Mind describes generic requirements and outcomes; Coding owns
Python acceptance checks. Guard remains responsible for tool authority. Model
identities and selection remain in Section 7.

## Baseline and evidence

The initial run reproduced 523 passing tests, two failures, two optional skips,
and 15 passing subtests. One failure was a test reading the retired loop file;
the other HTTP fixture matched a retired renderer prompt and supplied code JSON
instead of a final response. Both fixtures now exercise the current interfaces
without weakening their execution/security assertions.

The supplied P1 trace establishes that `build_index.py` was written and compiled,
accepted a positional argument, rejected `--source` with exit 2, and was followed
by an invented Chat implementation and failed audit. It does not include the
complete original user request, fixture data, or whole generated file. The
existing untracked laptop script has not been modified here. Exact counting
semantics and a real-file P1 reproduction remain pending.

## Checklist

| Step | Result |
|---|---|
| 1. Baseline | Recorded source/test baseline and supplied P1 evidence. Exact P1 fixture/request still needed. |
| 2. Preserve results | Execution receipts survive reply rejection; confirmed artifacts refresh both windows. Chat retains outcomes. Explanation-only retry invokes model resources, never a domain. |
| 3. Task contract | Version 1 carries task ID, original objective, requirement IDs, constraints and planned acceptance checks. Coding rejects unsupported/malformed incoming contracts. Legacy domain calls remain compatible. |
| 4. Plan fidelity | Global requirements and constraints reach delegated steps. Invalid material steps trigger bounded re-planning even if a communication step survives. Failed repair is explicit. Generic evidence is not relabeled as an unknown user choice. |
| 5. Behavior checks | Coding supports immutable container-only function examples, exact signatures and CLI checks, declared by its manifest. Missing runtime blocks application when acceptance checks are planned. Syntax-only work remains explicitly unverified. |

## Results and retry semantics

`outcome` separates execution, verification and communication. A reply failure
can coexist with completed file writes and passing selected tests. Canonical
fallback text reports paths and actual checks without approving the rejected
model draft. Partial writes are reported as partial work. Requirements with no
passed linked acceptance checks stay unverified; passing examples is not proof
of all program behavior.

Chat persists these receipts separately from Section 3 permanent knowledge.
The UI displays the three outcome states and offers **Retry explanation only**
when the current session has retained its rendering context. That context is
bounded to 32 tasks. A backend restart can expire the retry context; attempting
an expired retry reports the limitation and never repeats file operations.
Crash recovery and cross-restart explanation reconstruction are follow-ups.

The regular operation, self-assessment and feature-expansion packages are kept.
No model is hardcoded. Domain-specific acceptance payloads are described in the
Coding manifest rather than encoded in Mind's semantic prompt.

## Acceptance execution

A planned check has `id`, optional `requirement_ids`, optional `step_id`, `kind`
and `payload`. Supported Coding kinds:

- `python_call`: module, function, args, kwargs, expected JSON result.
- `python_signature`: module, function, exact parameter/return signature.
- `python_cli`: relative Python script, string arguments, expected exit code,
  optional exact standard output.

Checks are materialized only in the disposable test snapshot. Generated code
cannot change their expected results because the harness is excluded from the
allowed write paths. Candidates must pass before application and persisted
source is tested again afterward. An unavailable runtime produces a resource
request before host writes when planned acceptance checks exist.

A check derived by a model still needs review against the user's real intent.
The implementation does not claim it can infer every ambiguous requirement.

## Validation

Regression cases cover rejected replies after successful writes, explanation-only
retry, durable outcomes and account isolation, partial writes, global requirement
preservation, invalid action plus surviving communication, unrelated project
facts versus unknown user choices, malformed contracts, wrong duplicate-counting
behavior, wrong CLI arguments, and unavailable test execution.

The browser test uses real auth, HTTP/WebSockets, production UI and Guard,
filesystem writes and Docker. It injects a communication rejection after two
passing behavioral checks, verifies both-window artifact refresh, then verifies
that explanation retry changes neither the writer-call count nor file mtime.
Model output and the native window bridge are controlled fixtures. Actual Mac
inference and native desktop execution still require laptop validation.

## Next milestone

Steps 6–9 (post-intake processing, reconciliation, retrieval and memory-first
resolution) are not implemented by this branch. Steps 10–12 remain subsequent
reliability/learning work. No memory migration, model download, domain expansion
or administrator approval bypass is introduced here.

Final cloud validation: **537 passed and 15 subtests passed**, with both browser
and native Docker integration checks enabled. JavaScript syntax and Git
whitespace checks passed. Release identity: **2026.10.29.1**. No native Mac build
or inference against the laptop's models is claimed by these fixture-based tests.

To try this milestone, fetch `implementation/execution-milestone` into a separate
checkout/worktree and run `bash scripts/dev.sh` there. Quit an existing app/backend
first. Pulling source does not replace an installed `.app`; rebuild it with
`scripts/update_macos_app.sh` only when ready to install the milestone. Preserve
any local source edits before switching branches.
