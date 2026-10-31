# Memory identity and audit correction — 2026.10.31.6

Laptop output identified installed/development stores with different counts.
The first audit mistakenly scanned _sequences.json as a record and counted
retained legacy migration copies as distinct Raw knowledge. Its same-ID byte
comparison also confused historical copies with active conflicts. Do not use
those initial duplicate counts as a deletion plan. A plain-text Tested record
is classified legacy_or_unstructured; that label is not a quality verdict.

The corrected audit skips internal metadata, distinguishes canonical class
folders from entries/ history, follows source.legacy_id migration links, reports
retained copies/differing fields separately, and reports reused legacy IDs.
True duplicate-source groups are computed over logical records. It remains
read-only and does not initialize Store or change any files.

A separate concrete Store bug was found: historical Raw aliases could shadow
canonical Tested/Derived IDs. Sequence allocation excluded migrated Raw numbers,
so a later Tested record could reuse one. Canonical records now take precedence
in lookup; Raw stays available through its migrated raw_* ID. Raw IDs never become Tested IDs: new Raw records retain raw_* identifiers and
new Tested/Derived records have their own mem_* numbers plus source_refs.
Historical alias numbers do not advance the mainstream sequence. The allocator
skips only a proposed number that collides with a retained compatibility alias;
it does not import the largest old Raw number as a counter. Migration no longer guesses how to rewrite an
ambiguous reference when a canonical non-Raw record owns the same old number.

No old record is deleted, renumbered, merged, or automatically reclassified by
this patch. Existing references that were already rewritten under the older
behavior may need manual provenance review; their original intent cannot be
inferred safely. Initialization still retains the existing legacy-migration
behavior for unambiguous references. Canonical records with duplicate IDs across
multiple class folders remain an audit error requiring review.

Tests cover canonical lookup alongside a colliding Raw alias, prevention of new
number reuse, logical counts, retained copies, internal metadata exclusion and
preservation of input bytes. Native laptop data must be re-audited after pulling.

Validation: 589 tests and 15 subtests passed; 4 optional integration tests skipped.
This includes the separate-Raw/mainstream-counter regressions and audit tests.
Git whitespace checks passed. No laptop data was accessed or changed remotely.
