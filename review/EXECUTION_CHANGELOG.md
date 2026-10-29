# Execution milestone change summary

Release: **2026.10.29.1**. Implementation commit: **009e2e2**, based on the
laptop source snapshot **cb5cdf7**. Branch: `implementation/execution-milestone`.
The original regular-operation, self-assessment and feature-expansion packages
remain separate. This release changes the regular operation path, its Coding
plug, Chat delivery and UI; it does not implement the Raw intake workflow.

## What changed

1. **Execution receipts:** Mind retains structured records of domain results,
   confirmed file writes, syntax checks, selected functional tests, timestamps
   and acceptance evidence. These survive reply generation or audit failure.
   A partial write reports only confirmed artifacts and does not claim that
   every requested operation completed.
2. **Separate outcomes:** Results distinguish execution, verification and
   communication. A failed explanation can accompany completed writes. Passing
   selected tests does not establish arbitrary correctness or every requirement.
3. **Deterministic fallback:** When a reply is rejected after writes, the user
   receives a fixed factual report from the receipts rather than losing the
   completed work. The rejected draft is not silently approved.
4. **UI delivery:** Chat and Coding receive confirmed artifact notifications
   even when the final reply fails. The editor refreshes. Each reply shows the
   three outcome states and expandable requirement-check coverage.
5. **Explanation-only retry:** A button requests only rendering and review of
   retained results. It never invokes a domain or repeats writes. The retained
   context is scoped to the validated session and bounded to 32 tasks. Expired
   context fails explicitly; cross-restart reconstruction is not implemented.
6. **Durable chat evidence:** Chat State stores the outcome with the turn and
   restores it on reload. This is conversation history, not a direct domain
   write into Section 3 permanent memory.
7. **Task contract v1:** Tasks carry an identity, original objective, numbered
   requirements, constraints and optional acceptance checks. Coding validates
   incoming contracts. Global requirements/constraints survive step delegation;
   long requirements are no longer silently cut to 300 characters. Follow-up
   answers such as "42" or "JSON" do not replace the original objective.
8. **Plan repair:** Invalid action steps cannot hide behind surviving
   communication steps. One bounded re-plan is allowed; failed repair produces
   an explicit failure before execution. Already supplied read-only evidence is
   distinguished from work that still needs execution.
9. **Clarification correctness:** Automatic evidence gathering no longer labels
   generic workspace facts as an answer to an unrelated user choice, or repeats
   facts already gathered automatically this turn.
10. **Behavioral acceptance:** Coding declares function-example, exact-signature
    and CLI acceptance checks in its manifest. Mind treats these as generic
    contracts. Their immutable test harness runs only in the guarded disposable
    container, before applying a candidate and again against persisted source.
    Generated code cannot edit that harness. If checks are planned but execution
    is unavailable, no candidate is applied. Without functional checks,
    syntax-only output stays explicitly unverified.
11. **Renderer boundaries:** Chat is instructed to report completed operations,
    not offer to provide files already written or invent replacement source
    when the actual source was not supplied as evidence.
12. **Tests and build identity:** Stale tests now reference the three-loop
    implementation and current renderer prompt. UI/backend identity and the
    installer message were advanced to 2026.10.29.1.

## Verification

**537 tests and 15 subtests passed**, with real Docker and browser integration
enabled. The browser test injects a failed communication audit after successful
coding, checks both-window artifact refresh, and proves that explanation retry
neither calls the writer again nor changes the file modification timestamp.
Additional regressions cover partial writes, account isolation, requirements
across delegation/clarification, invalid action plans, unknown user choices,
malformed contracts, a wrong duplicate-counting implementation, the confirmed
`--source` CLI mismatch, and missing functional execution.

Models and the native window bridge are controlled fixtures. The original P1
script and dictionary fixture were not uploaded and were not modified. Its exact
counting definition remains unconfirmed. Mac native builds and the local models'
inference quality require laptop testing.

## Testing on the laptop

Quit AI Friend with Cmd+Q. From the original repository, create an independent
worktree so its locked Central Mind and existing workspace are not overwritten:

```sh
git fetch origin implementation/execution-milestone
git worktree add -b laptop/execution-milestone ../AI-Friend-execution-milestone FETCH_HEAD
cd ../AI-Friend-execution-milestone
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-runtime.txt -r requirements-dev.txt
npm ci --prefix section_0_app
npm run dev --prefix section_0_app
```

Use a disposable Coding project and your Trainer account. Export your existing
reviewed `AI_FRIEND_TEST_IMAGE` in that shell for functional execution. Pulling
source does not replace an installed application. Use `scripts/update_macos_app.sh`
only when ready to rebuild/install; it backs up the prior installed bundle.

## Deferred work

Post-intake examination/reconciliation, improved memory retrieval and memory-first
resolution are the next milestones. Reviewer model switching, full provider
quality grading and broader self-assessment coverage remain later work. No model
is downloaded, no model identity is hardcoded, and no Guard permission is added
by the execution milestone.
