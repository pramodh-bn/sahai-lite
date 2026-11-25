# Status
Stage: 1
Task: LITE-S1-BUILD-01
Owner: Builder
State: REPAIR_REQUESTED_1
Base SHA: a73d168b5bafd900a4e834ba9d00ae10d1f8fb5a
PR: none
Evidence: Builder reported SHA a02ef4ab8370524fb3e46edb1a88708663afe651, but that object does not exist in sahai-lite after fetching origin. No origin branch or PR named lite/builder/LITE-S1-BUILD-01 exists, no Builder worktree is registered in sahai-lite, and the report supplied no executable command output or exit codes. The implementation cannot be reviewed.
Next: Builder repair 1 must work only in pramodh-bn/sahai-lite from exact base a73d168b5bafd900a4e834ba9d00ae10d1f8fb5a, leave factory-lite/tests unchanged, run the exact 25-test command, push the required branch, open a PR targeting dev-v3, and return verifiable SHA/PR/commands/exits/evidence.
