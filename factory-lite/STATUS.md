# Status
Stage: 1
Task: LITE-S1-BUILD-01
Owner: Builder
State: REPAIR_REQUESTED_2_FINAL
Base SHA: a73d168b5bafd900a4e834ba9d00ae10d1f8fb5a
PR: none
Evidence: Builder repair 1 pushed 454b29d02f0b2c3a4dde8d2e401a46a5232a3eb7 on lite/builder/LITE-S1-BUILD-01 from unrelated history rather than base a73d168b. Its diff deletes factory-lite/PROTOCOL.md, STATUS.md, all four specs, and the approved 25-test contract; adds legacy factory/stage material; changes 131 files; immutable-test diff exits 1; and no PR exists. This SHA is rejected and must never be merged.
Next: Final repair 2 must use a fresh worktree and branch lite/builder/LITE-S1-BUILD-01-R2 created directly from a73d168b5bafd900a4e834ba9d00ae10d1f8fb5a, change only app/** and factory-lite/docs/napster-feasibility.md, preserve the approved tests byte-for-byte, achieve exactly 25/25 exit 0, and open a real PR targeting dev-v3. Any further failure blocks Stage 1.
