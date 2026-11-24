# Git protocol and traceability

## Required Git workflow
1. Integration agent verifies local/remote repository, creates branch, and protects main from direct pushes if GitHub permissions allow.
2. Coordinator creates one issue per task; assign a real accountable seat in the BAND room, even if GitHub account is shared.
3. Worktree per issue, e.g. `git worktree add D:/Workspace/sahai-worktrees/backend-42 -b agent/backend/s03-42-ledger origin/main`.
4. Agent writes changes, runs local checks, commits small units **at milestones**, pushes branch and opens PR. Never make one giant final commit.
5. Reviewer requests changes; agent fixes in own branch; CI and harness run again.
6. Integrator merges gated PR; pushes stage tag; Reporter records lineage.

## Git identity
Use `git -C <worktree> config user.name "Sah Agent: backend"` and a configured attribution email you control. These local names are advisory. If all pushes authenticate as one GitHub user, PR metadata and room transcript are the independent proof. Never fabricate GitHub identities. Do not spoof other people's email addresses.

## Commit template
```
feat(s03): persist ordered rehearsal events

Spec: challenges/sah/spec/stage-03.md
Evidence: artifacts/stages/stage-03/ledger-tests.json

Agent-Seat: backend
Agent-Harness: OpenCode
Agent-Model: qwen/qwen3-coder
Spec-Stage: 03
Issue: #42
```

## Minimum PR template
```
Resolves #42
Spec: challenges/sah/spec/stage-03.md
Agent seat/runtime/model:
Change summary:
Decisions / tradeoffs:
Test commands and results:
UI trace/screenshot (where applicable):
Live API verified? YES / NO / BLOCKED (proof):
Risk and rollback:
Spent / budget:
Band room message IDs:
```

## Permission and safety
- `git push` requires a valid remote and authenticated credential. Test using an expendable task branch; never assume capability from `git status`.
- Keep one shared integration checkout and separate agent worktrees to avoid races and files overwritten by other agents.
- Require branch protection + required checks when available. A GitHub account with admin ability can bypass these checks unless rulesets forbid bypass; prefer safe behavior over trust in prompts.
- Model attribution across agents is probabilistic unless separately authenticated + cryptographically signed; keep reproducible test artifact references and room logs.
