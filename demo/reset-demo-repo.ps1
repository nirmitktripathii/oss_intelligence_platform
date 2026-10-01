# Put the shared demo repo back to its starting state after visitors have tried the demo:
# close every open pull request and delete every branch except main. main itself is never
# written to by the agent (pull requests are drafts from feature branches), so it needs no reset.
# Needs the GitHub CLI signed in as the repo owner: gh auth login
param([string]$Repo = "nirmitktripathii/gitscout-demo-sandbox")
$ErrorActionPreference = "Stop"

foreach ($pr in (gh pr list --repo $Repo --state open --json number --jq ".[].number")) {
  gh pr close $pr --repo $Repo --delete-branch
}
foreach ($branch in (gh api "repos/$Repo/branches" --paginate --jq ".[].name")) {
  if ($branch -ne "main") { gh api -X DELETE "repos/$Repo/git/refs/heads/$branch" | Out-Null; Write-Host "deleted $branch" }
}
Write-Host "Reset $Repo."
