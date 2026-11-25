# Status
Stage: 2
Task: LITE-S2-VERIFY-TESTS-01-R1
Owner: Verifier
State: S2_TEST_CONTRACT_REVIEW_REPAIR1_REQUESTED
Base SHA: 977787ea97068ff942efec8575514c81930b31a7
PR: https://github.com/pramodh-bn/sahai-lite/pull/14
Evidence: Verifier Stage 2 test contract (head 88157d40faf979a2a6c1e58b8bff30a6b2ab1987, PR #14) reviewed by Lead 2. Verified: 977787e is an ancestor; the diff is test-only (CONTRACT.md, evidence, s2_helpers.py, 7 new test_s2_req*.py; no app/ change and no Stage 1 test file touched); Lead 2 independently reproduced the red run on the exact SHA: Ran 48 tests, 22 failures + 1 error, exit 1, with the Stage 1 25 green. Stage 2 conventions accepted and frozen: the /api/rehearsal/* wire format (contract risk 2), same-process UI served at / on the Stage 1 Flask app (risk 4), and the Playwright dev dependency documented with a visible SkipTest when absent (risk 1). Gap: stage-2.md names "hidden budget constraint and sign-on flexibility", but only the budget dimension is tested; sign-on flexibility is uncovered (risk 3).
Next: Lead 2 requested one bounded contract repair (R1) from Verifier on the same branch/PR #14: keep the single hidden_need_revealed boolean, define the hidden need as budget constraint + sign-on flexibility, extend the reveal trigger set to explicit sign-on probes, and add a black-box test where a sign-on-only probe (no budget keyword) reveals the hidden need while a neutral probe does not; update CONTRACT.md accordingly. The contract must stay red on base 977787e with cumulative Stage 1 green. On return, Lead 2 re-reviews, integrates the test-only PR, then assigns Builder against that exact merged SHA. Stage 3 needs real live Napster evidence or an explicit blocked/partial report; no certification without evidence.
