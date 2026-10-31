# Memory review and browser media consent — 2026.10.31.4

## Permission implementation

A browser result detecting images or video can offer a session-local permission
request. Authenticated Chat and Coding windows poll the pending list and display
Allow once / Deny. Browser tools cannot approve their own requests; a caller's
approved flag is ignored. Requests expire after ten minutes and cannot be reused,
transferred across backend sessions or expanded to another tool. Broker and Guard
still authorize the actual operation. URL exclusions are rechecked, including
subrequests; consent never overrides them.

After approval the media tool revisits the source in a fresh isolated browser,
then delegates a viewport screenshot, or video screenshots at 0/5/10 seconds,
to the existing document/image reader through a bound Broker. It does not replay
previous browser interactions or preserve the exact earlier page state. Video
seeking may fail on short, live, protected or unsupported players; failures are
reported rather than treated as understanding the whole video. Screenshot OCR
is not a complete visual/video understanding engine. Audio is explicitly marked
unavailable: no registered listening/transcription adapter exists. No claims of
WhisperKit integration or full video watching are made.

Results are shown in the permission panel, marked unverified, and do not write
knowledge or automatically resume a paused domain task. A full automatic
media-result-to-reasoning/learning continuation is still needed. The generic
Mind stores permission state without website-specific logic; the server only
handles authenticated decisions. Binary media payloads are omitted from Broker
history/log messages. Results may still appear in normal UI/output diagnostics;
this is not a guarantee of zero diagnostic data retention.

## Confirmed memory problems and repairs

1. Exact request-substring search misses naturally worded questions. Bridge recall
   now falls back to ranked lexical token overlap when exact search is empty.
   Exact phrase search remains first. This is explainable lexical retrieval,
   not semantic embeddings or a proof of relevance/truth.
2. Recall silently reduced every record to its first 500 characters. The evidence
   window is now 12,000 characters per result, with full length, explicit
   truncation, source and trust/class metadata. Mind additionally shares a 24,000-character source-text budget across its
   selected recall records, marking further truncation explicitly. Full source remains retrievable
   by ID through authorized clients. Very long sources still need chunking.
3. A cached in-process index missed another session's appended records. Each
   search now builds its filtered index from current storage. This scans memory;
   a revision-aware persistent index is needed for scale.
4. Raw entries could consume a domain's result limit before access filtering,
   hiding accessible Tested/Derived records. Domain filtering now happens before
   the limit; domains still cannot directly read Raw.

## What already works, with limits

Raw originals are retained; post-intake queue/history survive restart; Coding
can propose syntax/structure observations; Mind decides commits; Memory Service
serializes writers. Tested observations include a verification scope. Duplicate
and conservative conflict checks avoid automatic overwrites. These are useful
foundations, not a complete learning system.

## Remaining causes of limited growth

- Languages and general prose have no automatic post-intake evaluator. They are
  deferred rather than falsely accepted. Generic intake does not teach every
  domain automatically.
- Runtime learning requires an explicit reusable candidate and a passing domain
  evaluation. Turns that do not produce a candidate create no permanent learning.
  Operational failures are not equivalent to verified reusable failure lessons.
- Raw-first retrieval still does not resolve arbitrary tasks without semantic LLM
  understanding. Raw records can crowd Mind's bounded recall; trust-aware budgets
  and further chunked retrieval are needed.
- Shared metadata exists, but domain payload schemas are not uniformly versioned.
  Coding's intake envelope is not yet a universal domain contract.
- Embedding/semantic search, relationship indexing, domain-specific contradiction
  review, trainer feedback calibration, migrations and the trusted memory-review
  UI remain incomplete.

## Next memory design steps

1. Inventory actual Raw, Tested, Derived and pending proposal counts by domain;
   expose reasons for deferral/rejection and missing candidates to the Trainer.
2. Standardize one versioned envelope (identity, domain, kind, immutable source
   references/hashes, payload schema/version, verification scope/results,
   applicability, decision and lineage). Domains own their specialized payloads.
3. Add bounded source chunks with stable offsets and source IDs, then evaluate
   retrieval on paraphrases and answers beyond the first chunk. Preserve originals.
4. Reserve retrieval budgets for Raw versus approved knowledge; add a governed
   memory-resolution path before model/internet fallback, without trusting Raw.
5. Complete domain examination and proposal-review workflows. Add explicit
   failure-to-lesson and user-correction proposals; never overwrite old memories.
6. Evaluate learning with repeat tasks and held-out tests: source completeness,
   retrieval relevance, verified acceptance rate, conflict behavior and reduced
   repeated failures. Saving more records alone is not evidence of growth.

## Comparison with the suggested five-layer architecture

The suggested plan is sound for BOTH knowledge and capability accumulation.
Memory is not model training; a tested procedure with applicability conditions,
limitations and executable verification is more valuable than a transcript.
Its stages are useful milestones, not a promise of general intelligence.

| Proposed layer | Current evidence | Remaining gap |
| --- | --- | --- |
| Memory | Raw/Tested/Derived storage, provenance, proposals, append-only intake history | Uniform payload contracts, chunking, trusted review UI |
| Retrieval/knowledge | Exact and now lexical recall, source IDs, domain filtering | Semantic/relational retrieval, relevance evaluations, trust-aware budgeting |
| Decision/execution | Guarded Coding, task contracts, acceptance checks, execution receipts | Registry of validated procedures with executable applicability checks and governed reuse |
| LLM providers | YAML-driven general model ranking and provider routing | Reliable semantic interpretation/recovery; the legacy vision reader still has a pinned model and must be migrated |
| Learning/validation | Candidate proposals, domain evaluation, Mind decisions | Systematic reusable failure lessons, corrections, evidence calibration and end-to-end growth evaluation |

The application remains predominantly Stage 1 (LLM dependent), with partial
Stage 2 (memory assisted). It has some execution/validation machinery needed
for Stage 3, but no demonstrated general knowledge-driven resolver. It is not
Stage 4/5. Stronger Guard/authority boundaries and explicit processing history
are implementation details the conceptual plan does not spell out; they do not
mean the app is ahead on reliable independent task solving.

The decisive next milestone is one bounded capability completed from memory:
store a verified procedure + applicability conditions + parameters + limitations
+ acceptance checks; retrieve on a paraphrase; validate applicability; execute
through Guard; recheck the result; append outcome evidence; record zero LLM calls.
A miss, contradiction or failed check must fall back to capability-selected LLM
reasoning, then relevant internet evidence where needed. Learned procedures must
never become unrestricted stored code executed directly from memory or overwrite
Central Mind. Expansion/installation follows the administrator approval boundary.

Do not add relational, vector and graph databases simultaneously merely because
the plan lists them. Start with the current store and measured retrieval tests;
add indexes based on observed misses and scale. No model distillation/training
is implemented or required for this first verified reuse milestone. A hardware
upgrade is not justified by the demonstrated software failures alone.

No defensible percentage or calendar estimate of the gap exists without a task
benchmark. Track completed task correctness, repeat-failure rate, relevant memory
recall, verified procedure coverage, provenance completeness and LLM calls per
successful repeat task. The original coding task and a bounded phrase task are
candidate benchmarks; their exact contracts must be fixed before scoring.

## Validation

Real browser/container integration suite: 578 tests and 15 subtests passed,
including the UI Deny action, authenticated approval dispatch, real screenshot
capture/delegation with a controlled reader, and the existing Docker coding loop.
After adding the explicit combined recall-text-budget regression, the final
default suite passed 576 tests and 15 subtests with 3 optional integration tests
skipped; the focused budget/consent tests also passed. Native Mac packaging,
actual live-model video interpretation and audio transcription are not verified.
JavaScript syntax and Git whitespace checks passed.
