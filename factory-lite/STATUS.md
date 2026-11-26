# Status
Stage: 4
Cycle: 1
Task: LITE-S4-VERIFY-TESTS-01
Owner: Verifier
Coordinator: Lead 3
State: S4_TEST_CONTRACT_ASSIGNED
Base SHA: 79747d9d0f092e7304315a5e32a10c837ed0ff9a
PR: pending (tracked as issue #66)
Evidence: Stage 3 is certified at 82e9406ff65d932a8bf19e8254fc6156536ccf2a (tag lite-stage-3-passed, PR #61); the Stage 4 gate is open. No Stage 4 implementation exists. Cumulative Stage 1-3 baseline on 79747d9: 96 tests, exit 0, 1 intentional skip, 370 s (`factory-lite/tests/evidence/lead-s4-baseline-79747d9-run2.txt`); one earlier run of the same SHA errored in `test_s2_req2` setUpClass on a port-8000 startup race and passed on isolated rerun, so any red must be reproduced before it is called a regression. Three docs-only merges landed after the baseline (#69, #70, #71) with no application or test changes.
Parallel track: body-double research and design, docs only, base 79747d9, merged 2026-11-26 -- `factory-lite/docs/napster-digital-twin-research.md` (#69), `factory-lite/docs/body-double-orchestration.md` (#70), `factory-lite/docs/body-double-persona-and-consent.md` (#71). No implementation has been dispatched from them.
Coordination: the Band agent CLI is unavailable to Lead 3 (every agent-scoped command is refused). Assignments, state and results are mirrored as GitHub issues labeled `assignment`; that issue list is the board of record while the room work board and plan cannot be read or written. Room messages remain the wake channel.
Next: Verifier authors the executable Stage 4 acceptance contract from factory-lite/spec/stage-4.md: Playwright desktop and mobile journey scenario -> stand-in demo -> handoff -> practice -> evidence feedback -> retry from pivot; keyboard operation, mic denial, slow network, exactly-once session cleanup; avatar/voice consent, no real meeting participation, deletion and no sensitive logs; clean-checkout cumulative runs; README, under-3-minute demo script, under-500-word writeup, real/mock matrix and judging-rubric self-check. Include at least one deliberately failing case and a red-run evidence file. Branch lite/verifier/LITE-S4-VERIFY-TESTS-01, PR to dev-v3.
