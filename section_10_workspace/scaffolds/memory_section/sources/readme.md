# Section 3 - Memory

Three memory classes: raw, tested, derived.

Every entry has the same schema. It carries:
  - a domain-prefixed ID
  - a memory_class: raw | tested | derived
  - originator list
  - tags (free-form)
  - success_count and failure_count
  - a failure ledger
  - cross-references
  - a score

State is COMPUTED from the counts. Never stored as a tag.

The computed states are:
  - untested        (0 successes, 0 failures)
  - rejected        (0 successes, more than 0 failures)
  - provisional     (some successes, no failures, below threshold)
  - verified        (enough successes, no failures)
  - unstable        (successes and failures both > 0)

VERIFIED_THRESHOLD is a config value (default 3).

Score formula:
  score = (success - 2 * failure) / (success + failure + 1)

Derived entries additionally carry:
  - source_refs (the tested entries they were built from)
  - derivation_note (how they were built)
  - derived_status: active | contested | obsolete

derived_status reflects the state of the sources, not the entry's
own counts. Scoring is identical for tested and derived entries.
