# Raw Memory processing milestone — 2026.10.29.2

This branch includes the execution milestone described in
[EXECUTION_CHANGELOG.md](EXECUTION_CHANGELOG.md), plus the first working
post-intake examination pipeline. It does not replace the three Mind loops.

## Flow and ownership

1. Trainer submits material through existing intake methods. Memory Service
   preserves it as unverified Raw, including source and Trainer context.
2. A durable SQLite queue records the source fingerprint and append-only attempt
   history separately from the original memory. Interrupted queued work survives
   service restart. Trainer/Administrator login resumes a bounded batch of four;
   the UI can process further batches or explicitly re-examine a source.
3. Mind reads the full Raw record and discovers its domain owner from manifests.
   The generic resource socket requests examination; no model name or Python rule
   is embedded in Mind's coordinator.
4. The domain returns analysis, scoped candidates and provenance. It cannot commit
   memory. Existing context is bounded and explicitly marked when truncated;
   final duplicate/conflict reconciliation checks complete stored entries.
5. Mind compares candidates with existing knowledge. Exact duplicates reuse IDs;
   conflicting semantic keys are deferred rather than overwriting prior records.
   New proposals pass the domain evaluator, then Mind approves or rejects them.
   Only Memory Service performs the resulting writes.
6. UI separately reports storage, processing, verification and Mind decision.
   The processing queue provides status and explicit retries.

## What is verified now

Coding's deterministic examiner recognizes Python files, folder-source blocks
and Python fenced blocks. It parses and compiles without executing the supplied
code, recording functions, signatures and classes in a versioned common envelope.
A Tested record establishes syntax/structure only; its verification scope states
that behavior is unverified. Invalid syntax remains a stored Raw source with a
failed check. Unknown material is deferred, not silently accepted.

Source fingerprints detect changed contents and compare declared hashes. They do
not authenticate the author or establish the truth of prose. Languages declares
intake processing deferred: its gradual interaction/Trainer-feedback learning is
not replaced by bulk phrase ingestion. Other domains need their own declared
examiner and evaluator before automatic acceptance.

## Reliability and limits

- Separate entry and proposal writer locks prevent stale sequence caches and
  simultaneous sessions from overwriting entries or proposal journals.
- A cross-session lease serializes examination. The current lease lasts fifteen
  minutes; future long-running examiners will need renewal. Attempts can recover
  after expiry, and duplicate reconciliation handles interrupted commits.
- Candidate batches are capped at 64. Coding blocks above 1 MiB are explicitly
  rejected for examination; Raw remains stored. No hidden truncation is accepted
  as a verified complete source.
- Duplicate detection is exact-content based. Conflict keys are conservative
  (currently Python source labels); unrelated same-named sources can require
  review. This is not semantic truth detection or an automatic merge system.
- Queue listing shows the latest 50 sources. Examination currently runs inline
  off the websocket event loop; this is not an autonomous background worker.
- Existing 500-character recall previews and mandatory LLM semantic understanding
  are unchanged. Full Raw reading works for examination, but memory-first task
  resolution and richer retrieval are the next milestone.
- Native Mac packaging and live local model quality require laptop verification.
  Browser tests simulate the native bridge and model responses.

## Files to review

- `section_1_central_mind/mind/intake_processing.py`: generic coordinator/decisions.
- `section_3_memory/processing.py`: durable queue/history/lease.
- `section_3_memory/locking.py`, `api.py`, `service.py`: serialized writes,
  reconciliation, restart recovery.
- `section_5_domains/coding/intake_examiner.py`: non-executing scoped examiner.
- Domain manifests, Coding engine and regular operation's public socket dispatch.
- `section_1_central_mind/server.py`: authenticated processing operations.
- `section_0_app/src/ui/chat/memory_intake/memory_intake.js`: status/queue/retry UI.
- `tests/test_raw_intake_processing.py`, `tests/test_ui_round_trip.py`: lifecycle,
  authority, duplicates, conflicts, interruption, concurrency and browser coverage.

No runtime memories, processing databases, model weights, credentials or local
workspace samples are included in this change. Build identity is 2026.10.29.2.

## Laptop checkout

Quit the installed application with Cmd+Q. In your original project folder:

```sh
git fetch origin implementation/raw-memory-processing
git worktree add -b laptop/raw-memory-processing ../AI-Friend-raw-memory-processing FETCH_HEAD
cd ../AI-Friend-raw-memory-processing
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-runtime.txt -r requirements-dev.txt
npm ci --prefix section_0_app
npm run dev --prefix section_0_app
```

This fresh worktree avoids modifying the root-owned Central Mind in your old
folder. It includes both milestones. Export your existing reviewed
`AI_FRIEND_TEST_IMAGE` before starting if you want functional Coding execution.
Pulling source does not update the installed `.app`; after source testing, quit
the development app and run `bash scripts/update_macos_app.sh` from this worktree
to rebuild/install. Confirm Build 2026.10.29.2 in the app.

## Validation

546 tests and 15 subtests passed with real Docker and browser integration enabled.
The browser path stores a full source, observes Coding examination and Mind
acceptance, re-examines it as a duplicate, and opens the processing queue.
The execution milestone's coding/communication-retry checks also remain passing.
JavaScript syntax and Git whitespace checks passed. An initial default run hit
an existing scheduler timing assertion; its focused rerun and the final complete
suite passed without changing that scheduler or weakening its assertions.
