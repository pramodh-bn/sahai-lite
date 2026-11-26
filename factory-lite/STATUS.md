# Status
Stage: 3
Cycle: 4 (owner-authorized fresh verification cycle; two-repair budget)
Task: LITE-S3-VERIFY-TESTS-04
Owner: Verifier 2
Coordinator: sah-lead
State: S3_CYCLE4_AUTHORIZED
Base SHA: 1bde34e3a1b615b1d37c4f4f44fe9d133f1edf22
PR: none yet
Evidence: Owner explicitly approved a fresh Stage 3 Cycle 4 after Cycle 3 closed. PR #38 remains closed and forbidden from merge. Verifier 2 may use its validated concepts only as reference and must recreate the test/docs-only contract on the current clean dev-v3 base. Cycle 4 adds a mandatory focused self-check before the full cumulative run: helper signatures must match every caller, all new Stage 3 modules must import and collect without Verifier-authored exceptions, and the live gate must skip non-certifying with zero calls. Highest certified stage remains 2; Stage 3 remains uncertified.
Next: Assign one fresh Verifier 2 contract task from the exact merged Cycle 4 ledger SHA. Gate 1 is focused helper/import/collection validation. Gate 2 is the full cumulative suite with all original 49 tests green and red only on missing Stage 3 application behavior. Builder and Stage 4 remain gated until Lead independently validates and merges the test-only contract.
