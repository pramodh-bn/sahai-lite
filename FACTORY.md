# Factory Design — Sah

## Operating principle
A *software factory*, not a large group chat: specialized agents receive a contract, work on isolated branches, produce reproducible evidence, request independent review, then merge through gated checks. Requirements and tests are versioned with code, but **only specification owners change acceptance tests**; implementers cannot loosen them to obtain a pass.

## Geometry
- Canonical repository: `https://github.com/pramodh-bn/sahai` (verify access; repository was not accessible to the kit author on 2026-11-24).
- Local canonical checkout: `D:\Workspace\sahai` (do not alter unless instructed).
- BAND primary/integration checkout: `D:\Workspace\sahai-base`.
- Independent implementation worktrees: `D:\Workspace\sahai-worktrees\<agent>-<ticket>`.
- There is only one Git repository and one product app. Unlike the organizer's submissions, each stage is a versioned snapshot (tag `stage-NN-passed`) of the shared app tree, not twelve copied full apps. `stage-NN/RUN.md` describes the build/test contract. `git archive` from stage tags reproduces each exact snapshot.
- `challenges/sah/spec` is the customer-facing contract; `harness` is independent verification; `app`/`src`/`web` are product implementation.

## Stage protocol
1. Requirements: Architect and Product Agent jointly freeze stage spec. Harness Agent writes black-box checks independently from the implementer.
2. Capability gate: API Scout executes the smallest possible live experiment for vendor functionality, attaches sanitized request IDs and artifacts. Missing keys -> BLOCKED, never SIMULATED=PASS.
3. Work: Coordinator splits non-overlapping issue/branch tasks; agents run in worktrees. A feature agent may push *its branch only*.
4. Review: Reviewer or Security owns review and sends change requests. UI Tester conducts genuine Playwright journeys after staging environment starts.
5. Gate: CI green, harness cumulative stages green, evidence archived, budget under cap, human-facing scope accurate. Integration Agent merges approved PRs and tags stage.
6. Report: Reporter writes timeline, provenance (agent, runtime/model, issue, PR, commits, tests, cost, evidence, residual risks), and a summary for the owner.

## Responsibility and independence
- The coordinator owns dispatch, dependency scheduling and retries, but not production code.
- Specification owner defines behavior; harness owner defines independent tests; implementers do not modify these paths to make tests pass.
- Reviewer cannot approve own changes. UI Tester must record actual screenshots/trace, not infer visual correctness from DOM assertions.
- CI is objective guardrail but insufficient: the vendor side must be verified separately.

## Git and attribution
- Use one feature branch per task: `agent/<seat>/sNN-<ticket>-<slug>`.
- Conventional commits: `feat(sNN): ...`, `test(sNN): ...`, `fix(sNN): ...`.
- Commit trailer: `Agent-Seat: ...`, `Agent-Harness: ...`, `Agent-Model: ...`, `Spec-Stage: NN`, `Issue: #NNN`, `Evidence: artifacts/...`.
- If several agents share one GitHub account, git author names are *declarations*, not cryptographic proof. Prefer authenticated individual bot identities or GitHub Apps where possible. Preserve Band room export and PR metadata independently.
- Never push directly to main; never force push after review; never alter another agent's branch; never commit credentials, raw personal video, private voice or huge recordings.
- Preserve commits (merge commits or rebase merge), avoid squash merges if individual change attribution is an objective.
- Every PR body references a single issue and spec, scope, test commands, evidence, deployment risks and rollback.

## Long-running control
- A coordinator session in BAND Desktop alone is not a reliable day-long scheduler. Machine must remain awake; process supervisor/queue must persist jobs; retries/backoff bounded; worktrees locked; resumable state in `factory/state.json` or issue board; periodic CI and API credential refresh.
- Budget: set explicit monthly/day caps and per-stage budget. Check costs every N jobs. No unbounded recursive 'fix and retry' loops.
- Max 2 expensive model invocations at once, max 2 live Napster sessions until real limits are measured; default 1 connection creation per second across the API key per Napster docs. Serialization queue for vendor requests.
- Escalate to owner on credential purchase, ToS concerns, consent/biometric use, production deploy, repeated third-party failure, or stage budget cap.

## Non-negotiable safeguards
- No real self likeness without affirmative consent and secure storage. No user voice cloned from unrelated data. Do not send recordings to other providers without disclosure.
- Session dialogue and scorecard are attributable to recorded turns; deterministic state transitions must be testable offline. No unsupported claims about improved confidence or performance.
- A mock is always labeled MOCK. A prerecorded video is labeled PRERECORDED. Live is marked LIVE only on verified end-to-end execution.
- The double *never* joins real calls. No biometric authentication claims. The application supports deleting uploaded likeness and sessions.

V2: independent Hackathon Judge evaluates product at stages 6, 9 and 12. See docs/OPERATING_PROTOCOL.md for authority, recovery and cost controls.
