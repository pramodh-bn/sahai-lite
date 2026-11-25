# Status
Stage: 3
Task: LITE-S3-VERIFY-TESTS-01
Owner: Verifier
Coordinator: sah-lead
State: S3_TEST_CONTRACT_ASSIGNED_LIVE_UNAUTHORIZED
Base SHA: b0e276d52db7cdac643206b65c137b75f2ff251a
PR: pending
Evidence: Stage 2 Builder SHA 8778448b43b7d704109c575d6ebfa4743df3a111 passed independent Verifier review unchanged and merged through PR #19 as b0e276d52db7cdac643206b65c137b75f2ff251a. Lead ran the cumulative suite on the merged SHA: Ran 49 tests in 215.737s, OK, exit 0; Playwright full demo-to-retry journey executed. Origin tag lite-stage-2-passed points to b0e276d52db7cdac643206b65c137b75f2ff251a. Highest contiguous certified stage: 2. Stage 2 is a deterministic offline stand-in; no live or paid calls. Stage 3 live Napster calls, credentials, and spending remain unauthorized; only test-contract and official-document research may proceed.
Next: Verifier authors a test-only Stage 3 black-box contract from exact base b0e276d52db7cdac643206b65c137b75f2ff251a. It must keep cumulative 49 tests, separate mock/static evidence from an explicitly gated authorized live probe, require redacted real evidence for companion/avatar, audio and handoff, prevent duplicate sessions, require cleanup on error, bounded 409/429 retry, mic-denial fallback, and forbid invented voice cloning or meeting relay control. No live/paid calls. Return a real PR, red offline evidence, and an explicit statement that Stage 3 cannot certify without owner authorization, credentials and successful live evidence.
