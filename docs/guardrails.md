# Autonomy and escalation gates

## Proceed autonomously
Branch creation, small commits and pushes to task branches, non-destructive refactors, test execution, mock calls, CI fix proposals and PR drafts within budgets and scopes.

## Stop for approval
- Entering or purchasing paid tiers; using new third-party credentials; generating/cloning a real person's face or voice; publishing personal media; changing privacy policy; exposing real users to an unvalidated AI assessment.
- Destructive operations (`git reset --hard` on shared work, deleting important branches, force-push, mass deletion), public production deployments, changing production secrets, irreversible database migrations.
- Vendor API behavior contradicts spec (NO-GO); API key not provided; repeated HTTP 409/429 beyond bounded retry; monthly budget exhausted.

## Automatic stops
3 failed attempts at the same fault, 2 consecutive stage-gate failures with no new evidence, stale PR over budget/time cap, unattended scheduler losing lease, tests modified only to pass failing code.

## Default proposed budgets
Daily token/API cap: **$10** total (proposed, must be explicitly set and monitored in real billing systems); stage live Napster credit cap: **$2** for capability probes; limit concurrency to two paid model sessions until measured. These are planning caps, not enforced by this scaffold.

## Operation limits
No system can promise uninterrupted days of autonomous progress solely from a chat message. BAND/Desktop and host must remain running; session expiry, credential refresh, vendor outages, budget and OS sleep will stop progress. Persist queue state and checkpoint after every PR. A supervising daemon is separate engineering work, not provided here.
