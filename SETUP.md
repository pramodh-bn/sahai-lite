# Fresh repository setup (Windows PowerShell)
Stop the old Sah agents. Leave their repository and workspaces untouched. If the new repository is already cloned, skip clone. If the destination already exists, inspect it; do not overwrite it.
```powershell
cd D:\Workspace
git clone https://github.com/pramodh-bn/sahai-lite.git
cd sahai-lite
git remote -v
git status
```
Extract this ZIP into the new checkout, review the files, then run the following on the initial branch (normally main). If main already has unrelated changes, stop and inspect.
```powershell
git add MASTER_PROMPT.md README.md SETUP.md mandates factory-lite
git diff --cached --stat
git commit -m "chore: initialize Sah v3 Lite factory"
git push -u origin HEAD:main
git branch dev-v3
git push -u origin dev-v3
git tag factory-v3-lite-start
git push origin factory-v3-lite-start
git worktree add D:\Workspace\sahai-lite-lead dev-v3
git worktree add -b lite/builder/bootstrap D:\Workspace\sahai-lite-builder dev-v3
git worktree add -b lite/verifier/bootstrap D:\Workspace\sahai-lite-verifier dev-v3
git worktree list
```
Stop if any command fails; do not force push. The initial owner bootstrap push to main is the only direct main write authorized here. Agents use PRs targeting dev-v3 only. Lead uses sahai-lite-lead; Builder and Verifier use their respective worktrees and create task branches from the assigned exact base SHA. Configure fresh agents with mandates in BAND Desktop and select actual available models. Restrict permissions and set external paid-provider caps. Add only the three agents to Sah-Factory-v3-Lite; send MASTER_PROMPT.md only to Lead. Monitor the first 30 minutes or Stage 1, whichever comes first. Stop on recursive messaging. No paid live API calls without owner authorization.
