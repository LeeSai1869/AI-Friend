# Coding dispatch correction — 2026-10-31

Laptop evidence at commit 251b4b8 shows the correct branch_test project and a
Mind plan delegating coder/write_code with main(), --source and output
requirements intact. Coding classification instead returned kind=plan, and the
read-only implementation planner ran. No write model call was observed. This
failure precedes functional execution; Docker availability is not its diagnosis.

The classifier prompt now distinguishes named-file creation from plan-only
requests, including empty projects. A delegated write_code operation that is
classified as plan/test/inspect/other gets one bounded classification correction
with the original task intact. A repeated mismatch returns an explicit error
with no artifacts. It cannot silently succeed by returning a plan. Legitimate
clarification and error responses remain permitted; no write is forced and Guard
or acceptance requirements are unchanged. Model selection remains capability based.

Regression tests cover repeated mismatch, clarification after correction, and
preservation of an initial clarification. The supplied laptop evidence also
shows repeated clarification and malformed/contradictory audit verdicts. Those
remain unresolved by this narrow patch; this is not a claim that the complete
live-model loop is repaired. Inspection file selection is also unchanged.

Build identity: 2026.10.31.1. This source patch does not automatically update an
installed Mac application. The existing development worktree can pull it without
creating another worktree. Do not rebuild the installed app before source testing.
