# Status
Stage: 4
Cycle: 1
Task: LITE-S4-SCOPE-01
Owner: Lead
Coordinator: Lead
State: S4_SCOPE_CORRECTION
Base SHA: 216475f70ce2b1ba013c81484567ec3488aa926e
PR: pending
Evidence: Stage 3 is certified at 82e9406ff65d932a8bf19e8254fc6156536ccf2a (tag lite-stage-3-passed). The three Stage 4 specialist reports are merged as PRs #69-#71. The owner selected the privacy-first made-up-avatar direction and does not want to provide biometric video. The contest build is therefore synthetic-only: no Digital Twin, real-person likeness, cloned voice, or biometric upload.
Review: PR #73 (`LITE-S4-VERIFY-TESTS-01`, head 098412e3576272a3fb41c2cca67ebf6937eba23f) correctly tests the former packaging specification but does not cover the approved persona profile, two-role hidden-state isolation, server-authoritative orchestration, bounded authority, transcript evidence, or fidelity/adversarial gates. It must not merge unchanged or be dispatched to Builder.
Next: merge this scope correction, then assign Verifier 2 a repair of PR #73 against the amended Stage 4 specification and all three specialist reports. Preserve its valid accessibility, lifecycle, consent, deletion, responsive, and submission tests; add executable persona/orchestration requirements and a fresh red run before any Builder assignment.
