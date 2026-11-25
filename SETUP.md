# Windows setup
Stop old Sah agents in Desktop (not unrelated agents). Preserve any uncommitted changes separately; do not reset or clean. Run in PowerShell:
```powershell
cd D:\Workspace\sahai
git status --short
git fetch origin
git log --all --graph --oneline --decorate -40
```
If dirty, stop and preserve work. Inspect history and choose the exact commit before v2; do not guess. Then run (replace BASE_SHA):
```powershell
$base = 'BASE_SHA'
git show --stat $base
if ($LASTEXITCODE -ne 0) { throw 'Invalid baseline' }
git branch archive/factory-v2 origin/dev
if ($LASTEXITCODE -ne 0) { throw 'Archive branch failed; inspect existing branch' }
git push origin archive/factory-v2
if ($LASTEXITCODE -ne 0) { throw 'Archive push failed' }
git worktree add -b dev-v3 D:\Workspace\sahai-lite $base
if ($LASTEXITCODE -ne 0) { throw 'Worktree creation failed' }
```
If baseline contains v2 files, inspect and remove only obsolete factory files in the NEW branch, commit the removal; do not remove original history. Extract ZIP contents into D:\Workspace\sahai-lite. Inspect files and commit only intended kit files, then push `git push -u origin dev-v3`. Do not force push. Use this checkout for Lead; create separate Builder and Verifier worktrees from origin/dev-v3, e.g. D:\Workspace\sahai-lite-builder and D:\Workspace\sahai-lite-verifier. Never share writable worktrees. Configure fresh agents in Desktop, one room, no old mandates or agents. Use model selectors to confirm actual availability; candidate model labels in mandates are not guaranteed. Disable room membership/agent creation grants where possible. Give only necessary filesystem and Git permissions. Do not grant blanket permission to spend money. Branch protection if available; otherwise acknowledge that prompt restrictions are not enforcement. Set actual OpenRouter key cap separately before paid use. Paste MASTER_PROMPT.md mentioning only Lead. No need to send it to Builder or Verifier. Stop old room before launch; stop the new room if recursive messages recur.
