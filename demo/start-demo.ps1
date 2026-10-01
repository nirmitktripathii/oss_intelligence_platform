# Starts the four local processes for the approval-gate demo, each in its own window.
# Run from the repo root in PowerShell, with GITHUB_TOKEN already set in THIS shell:
#   $env:GITHUB_TOKEN = "<fine-grained token for the demo repo only>"
#   .\demo\start-demo.ps1
param(
  [string]$Owner = "nirmitktripathii",
  [string]$Repo  = "gitscout-demo-sandbox"
)
$ErrorActionPreference = "Stop"
if (-not $env:GITHUB_TOKEN) { throw "Set `$env:GITHUB_TOKEN first (see docs/DEMO-approval-gate.md)." }
$root = (Get-Location).Path

# One JSON line: GitScout is read-only and auto-approved; Git/CI only auto-approves reading.
$servers = '[{"name":"gitscout","url":"http://127.0.0.1:9000/mcp","auto_approve":["search_issues","get_issue","analyze_issue","analyze_issue_text","gitscout_health"]},{"name":"gitci","url":"http://127.0.0.1:9100/mcp","auto_approve":["sandbox_status","list_files","read_file","show_diff","ci_status"]}]'

function Start-Window($title, $dir, $cmd) {
  Start-Process powershell -ArgumentList "-NoExit","-Command","`$Host.UI.RawUI.WindowTitle='$title'; Set-Location '$dir'; $cmd"
}

Start-Window "gitscout-mcp :9000" "$root\mcp_server" "`$env:MCP_PORT='9000'; `$env:GITSCOUT_API_BASE='https://gitscout-api.onrender.com/api/v1'; python -m gitscout_mcp.server"
Start-Window "gitci-mcp :9100"    "$root\git_ci_mcp"  "`$env:MCP_PORT='9100'; `$env:GITCI_ALLOWED_OWNERS='$Owner'; python -m gitci_mcp.server"
Start-Window "backend :8000"      "$root\backend"     "`$env:AGENT_MAX_STEPS='14'; `$env:AGENT_ALLOW_ANONYMOUS_WRITES='true'; `$env:AGENT_MCP_SERVERS='$servers'; python -m uvicorn app.main:app --port 8000"
Start-Window "frontend :3000"     "$root\frontend"    "`$env:NEXT_PUBLIC_API_URL='http://localhost:8000/api/v1'; npm run dev"

Write-Host "Open http://localhost:3000/alexa in about 20 seconds."
Write-Host "Say: Fix the bug in https://github.com/$Owner/$Repo (the issue is in ISSUE.md)."
