# Status
Stage: 1
Task: LITE-S1-VERIFY-TESTS-01
Owner: Verifier
State: ASSIGNED
Base SHA: 32e8c6f07933737393ea22e729f1a134dae7039d
PR: pending
Evidence: origin/dev-v3 exists; Lead integration checkout is clean and GitHub, Docker, Node, npm, and Python are available. Stage 1 acceptance command: py -3.12 -m unittest discover -s factory-lite/tests -p "test_*.py" -v.
Next: Verifier creates a test-only PR targeting dev-v3, proves the contract red on the exact base (including a deliberate broken-service failure), documents Napster feasibility without paid/live calls, and reports exact SHA/PR/command exits/evidence plus runtime model and clean separate-worktree confirmation.
