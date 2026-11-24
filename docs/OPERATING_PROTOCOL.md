# Operating protocol v2
Coordinator owns durable queue: issue ID, stage, dependencies, seat, status, lease expiry, attempts, base SHA, branch, PR, evidence, spend and next action. Persist after every handoff. States READY, ACTIVE, REVIEW, ACCEPTED, BLOCKED. On restart reconcile remote PRs and worktrees before redispatch; never duplicate active work. Initial WIP 3, paid model concurrency 2, live vendor concurrency 1. Use bounded retries (3 attempts), then block or replan with evidence. No unattended spending until owner-approved caps and actual billing controls exist.

## Authority matrix
Coordinator dispatches and reprioritizes; Product/Architect propose spec changes; Harness Engineer owns acceptance suites; specialists own assigned implementation files; Reviewer approves exact SHA independently; UI Tester signs off browser evidence; Security blocks privacy/security failures; Integrator alone merges and tags; Judge scores but cannot waive gates; Reporter records evidence. Spec/test changes require separate review. No agent approves its own work. If GitHub identities are shared, record independent room review and do not pretend GitHub approval is independent; if branch protection requires separate accounts, stop for owner setup.

## Model economics
Roster IDs are candidates, not validated availability or prices. Check actual runtime model list and provider rates. Run a small comparable task with tests, record cost, elapsed time and pass rate. Use cheapest passing model for routine work; escalate to stronger available model only after two evidenced failures or for consequential architecture/security decisions within approved cap. Record actual model and effort per task. No automatic paid upgrades. Unknown cost is unknown, not zero.

## Dispatch template
@seat | issue | stage | spec IDs | base SHA | allowed paths | dependencies | acceptance commands | budget | timebox | expected artifacts | reviewer. Include full mandate for runtimes without persistent instructions. Seat replies ACK or BLOCKED. Completion includes PR URL, SHA, tests, evidence, spend, remaining risks. Coordinator acknowledges and records next owner.

## Recovery
Do not reset shared checkouts, kill unrelated containers or overwrite work. Resume from last verified SHA. Use unique ports and Docker project names. Persist redacted logs. Keep raw room export outside Git until privacy review. Stop on missing credentials, exhausted budget, consent or permission failures; continue independent offline work where safe. Never claim a supervisor exists until tested.
