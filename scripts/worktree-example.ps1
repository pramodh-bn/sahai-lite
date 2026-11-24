param(
 [Parameter(Mandatory=$true)][string]$Seat,
 [Parameter(Mandatory=$true)][string]$Issue,
 [Parameter(Mandatory=$true)][string]$Slug,
 [Parameter(Mandatory=$true)][string]$Stage
)
$ErrorActionPreference = 'Stop'
$integration = 'D:\Workspace\sahai-base'
$dir = "D:\Workspace\sahai-worktrees\$Seat-$Issue"
$branch = "agent/$Seat/s$Stage-$Issue-$Slug"
if (-not (Test-Path "$integration\.git")) { throw "Integration checkout missing: $integration" }
& git -C $integration fetch origin main
if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
& git -C $integration worktree add $dir -b $branch origin/main
if ($LASTEXITCODE -ne 0) { throw 'Worktree creation failed' }
Write-Host "Worktree $dir, branch $branch"
Write-Host 'Agent must configure a non-spoofing Git author, commit, push branch and open PR.'
