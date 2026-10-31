# Coding-loop memory quality and audio connection — 2026.10.31.5

The delivery target remains UI -> Chat -> generic Mind -> Coding -> guarded
execution -> verified memory -> Mind -> Chat/UI. These repairs do not establish
that every live-model request completes this path.

## Memory quality

- Trainer intake serializes source comparison and writing across sessions.
  Exact source content within one domain/kind reuses one active Raw ID. New
  source/provenance, title, tags, actor and Trainer notes are preserved in an
  append-only intake receipt. The original source is not rewritten.
- A known Trainer-context suffix is separated only when it exactly matches its
  declared metadata. Different notes on identical source material no longer
  require another Raw copy. Different domains/kinds or changed source bytes
  remain separate. This is not semantic/fuzzy deduplication.
- Existing duplicates are not automatically deleted or merged. The read-only
  audit script reports duplicate groups, class/domain counts, Tested record
  types and proposal statuses without printing lesson contents. Historical
  legacy copies can contain inconsistencies; those are reported for review.
- Syntax-only Coding results are operational evidence, not permanent reusable
  learning candidates. A candidate now requires successful behavioral tests.
  It contains a versioned JSON example: task contract, source snapshot, hashes,
  test evidence, verification scope, applicability restrictions and limitations.
  Examples above 64 KiB are not silently truncated and called learned.
- Equivalent checked output snapshots/tasks can reuse an existing Tested example
  through a new proposal decision, keeping its original record unchanged.
  Stored examples are reference evidence, never automatically executable code.
- Raw Coding intake may still create Tested *structural observations* after
  syntax examination. These do not claim behavioral correctness and are not
  relabeled as successful solutions by the Coding recaller.
- Runtime failures are still operational evidence unless a domain proposes a
  separately verified reusable failure lesson. Automatic zero-LLM procedure
  execution is not implemented by this patch.

The earlier authenticated syntax-only regression deliberately expected a
permanent Tested observation. It now asserts no permanent candidate is created.
The real Docker/UI regression instead asserts a behaviorally checked example,
including actual source and passed checks, reaches permanent memory.

## Audit the laptop, without changing memory

From the updated source checkout:

```sh
python3 scripts/memory_audit.py "$HOME/Library/Application Support/AI Friend V1/state/memory"
python3 scripts/memory_audit.py "$HOME/Library/Application Support/AI Friend V1 Dev/state/memory"
```

These inspect installed and development stores separately. They do not initialize
Store, migrate files, delete duplicates or write data. Share counts/types and
IDs if desired; do not paste private memory contents. Missing directories are
reported as errors, never created.

## Audio/video

The new audio_transcribe tool uses the existing trainer-maintained
runtime_inventory.whisperkit entry in Section 7 YAML. Its CLI syntax follows the
Mac help supplied by the user. Configure model_path to the existing local model
directory (no model identity is embedded in Python). Missing configuration fails
explicitly; no --model download request is made. Offline environment hints are
set, but are not an OS network sandbox for the native CLI.

After scoped approval, browser video analysis can fetch a directly accessible
media URL, transcribe up to its first 60 seconds and inspect frames at 0/5/10
seconds. Audio-only elements can also request transcription. Timestamped segments
and frames are returned together with the source URL. All destinations and
redirects obey the existing origin approvals and denylist. Fetches are bounded
at 32 MiB; blob/MSE/DRM/authenticated streaming is not implemented. A page can
require additional approved CDN origins. Audio failure is reported separately
from available visual evidence, and incomplete sampling is marked incomplete.

ffmpeg converts approved input bytes to a temporary WAV through stdin/stdout,
with only the pipe protocol allowed. Untrusted playlists cannot use this step
to fetch additional URLs or local files. Temporary WAV/reports are cleaned up;
transcripts are not automatically accepted into memory. Guard still authorizes
CLI execution and local model-directory access. There is no silent microphone
recording, native screen recording, or whole-video-understanding claim.

WhisperKit JSON reports must contain recognized timestamped segments. Silence,
unknown report formats, missing models, Guard denial and missing ffmpeg are
explicit errors. Actual Mac WhisperKit report behavior and recognition quality
need laptop verification; cloud tests use a controlled CLI report fixture.

## Remaining proof

We need a live laptop coding turn with a fixed behavioral contract, actual
functional runtime, accepted checked example and correct UI report. Then prove
bounded reuse of that example on a repeat task without another LLM call.
A stronger provider can be added to the YAML registry, but replacing a model
alone does not repair missing contracts, execution or learning validation.

## Validation

The browser/container run passed 588 tests and 15 subtests, including real media
fetch/ffmpeg/frame sampling with controlled WhisperKit/image fixtures and the
Coding -> tested example memory -> UI assertion. After the final generic
example-fingerprint regression, the default suite passed 585 tests and 15
subtests, with 4 optional integration tests skipped. Focused duplicate intake,
concurrent writer, source-note preservation, example deduplication, transcript
and read-only audit tests passed. Git whitespace, Python compilation and shell
syntax checks passed. Native WhisperKit recognition and the live Mac loop still
require laptop validation; these tests do not establish general reliability.

If the behavioral runner is unavailable, no verified Coding example is saved.
That is intentional: do not fill Tested Memory with syntax-only success claims.
This may leave Tested examples empty until a functional runtime is available.
The existing legacy vision-reader model selection issue remains a separate
known gap; this patch adds no new pinned model identity.
