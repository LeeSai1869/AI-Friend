# File-specific recall and action diagnostics — 2026.11.02.1

The live read-only test request returned execution:not_started and no test
results. The supplied old debug plan was cut off at 9,000 characters inside
recalled Raw content and its source-file inventory, before the action steps.
This does not establish that Coding received the request and lost its report.
The missing steps cannot be reconstructed from the truncated plan itself.

## Changes

- Natural-query lexical fallback now requires an explicit file/URL identifier
  to occur in a candidate when the query names one. A long generic guide no
  longer wins simply by containing common words such as tests/report/files.
  This is deliberately conservative lexical matching, not a semantic relevance
  guarantee or a general-purpose knowledge resolver. Exact phrase matches remain
  first; generic queries without explicit identifiers keep their existing fallback.
- Matching file excerpts can start near the identifier instead of always using
  the first 12,000 characters. Offsets refer to the original Unicode source.
- Recall source metadata is compact: identity/provenance scalars, approval IDs,
  source-file/reference counts and bounded lists replace unbounded inventories.
  Raw content, metadata and all source files remain unchanged and accessible by
  ID through the authorized full-record path. Compact recall does not upgrade
  Raw material to trusted execution evidence.
- New Chat diagnostics store action steps independently and a compact valid JSON
  plan, omitting source content/inventories from recalled-memory diagnostics.
  Execution receipts expose operation/test-count summaries separately. These are
  bounded diagnostic views, not complete archives; limits are recorded.
- `scripts/turn_trace.py` reads old/new logs without initializing memory or
  printing recalled text/model prose/code. When an untruncated old semantic
  provider output exists, it can expose its candidate capability list even when
  the old final-plan diagnostic was cut off. Recent proposals may belong to
  different turns: compare timestamps. Missing/truncated outputs are not guessed.
- The generic understanding instructions now explicitly distinguish performing
  an operation from reporting historical results, and distinguish a no-mutation
  constraint from a ban on read-only execution. Coding's manifest clarifies that
  test_code executes suites and reports actual counts. No test-keyword routing
  is embedded in Central Mind. These prompts are guidance, not an independently
  verified guarantee of correct live-model interpretation.

## Verification scope

The browser/Docker regression includes the user's read-only run shape, real
container tests, returned counts/receipts, unchanged source bytes and mtimes,
and no writer-model calls. A large unrelated Raw guide is present. Semantic
interpretation is a controlled fixture: this tests execution/report transport,
not whether a live provider reliably decides to run tests. Additional regressions
cover file-specific filtering, bounded metadata, original Unicode offsets,
parseable compact diagnostics and privacy-preserving legacy trace recovery.

## Laptop inspection (no restart needed for this script)

```sh
python3 "$HOME/Desktop/AI-Friend-raw-memory-processing/scripts/turn_trace.py"
```

It defaults to the development state. For installed state add:
`--state-root "$HOME/Library/Application Support/AI Friend V1/state"`.
Capture this before replaying the task so the last completed turn stays clear.
No old memory, approval or pending proposal is changed by this patch.

Understanding guidance also explicitly treats Raw source instructions as data,
and distinguishes historical knowledge from live execution evidence. The supplied
Raw excerpt contains navigation/redirect text and encoding artifacts, but this
patch does not infer that the entire source is worthless or that instruction
confusion caused the failed turn. Originals are retained for examination.

Validation: 608 default tests and 15 subtests passed; 4 optional integration tests
skipped. A separate run passed 3 tests including the real browser/Docker read-only
execution/report scenario with unchanged source bytes/mtimes. Targeted recall,
Unicode-offset, compact diagnostic and safe trace tests passed. Final generic
prompt clarification is guidance and still needs live-provider verification.
Native Mac startup is not validated by cloud browser fixtures.
