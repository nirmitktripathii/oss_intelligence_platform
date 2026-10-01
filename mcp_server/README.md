# GitScout MCP Server

A spec-compliant **Model Context Protocol** server that exposes the GitScout
open-source issue-intelligence engine to any MCP client — Alexa+, Claude Code,
Cursor, or the GitScout web app — over the **Streamable HTTP** transport
(MCP protocol ≥ `2025-11-25`).

GitScout finds the work and understands the code; this server makes that
intelligence callable by an agent.

## Tools

| Tool | Wraps | What it does |
|------|-------|--------------|
| `search_issues` | `GET /issues` | Live, open, unassigned GitHub issues + funded bounties, filterable by domain, difficulty, tech stack, bounty, effort, ROI. |
| `get_issue` | `GET /issues/{id}` | Full detail for one indexed issue. |
| `analyze_issue` | `GET /triage/{id}` | AST-localized, source-grounded triage: root cause, minimal reproduction, fix plan, contributing rules, confidence. |
| `analyze_issue_text` | `POST /triage/generate` | Same triage for arbitrary (non-indexed) issue text. |
| `gitscout_health` | `GET /health` | Connectivity / telemetry check. |

## Prerequisites

The GitScout FastAPI backend must be running and reachable. From the repo root:

```bash
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

(Optional) seed live issues so search returns data:

```bash
python -m app.scrapers.orchestrator --seed-live --limit-per-repo 4
```

## Install & run

```bash
cd mcp_server
python -m venv .venv && . .venv/Scripts/activate   # Windows; use bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env          # then edit GITSCOUT_API_BASE if needed
python -m gitscout_mcp.server
```

The MCP endpoint is then live at **`http://127.0.0.1:9000/mcp`**.

For production hosting, serve the ASGI app instead:

```bash
uvicorn "gitscout_mcp.server:create_app" --factory --host 0.0.0.0 --port 9000
```

Set `MCP_HOST=0.0.0.0` when serving under a public hostname. The SDK only enforces its
localhost-only `Host` header allowlist when bound to loopback, so a loopback bind answers a
real hostname with `421 Misdirected Request`. The Render blueprint (`deploy/render.yaml`,
service `gitscout-mcp`) already does this, and the backend's agent planner connects to it via
`AGENT_MCP_SERVERS`.

## Connect a client

**Claude Code:**

```bash
claude mcp add --transport http gitscout http://127.0.0.1:9000/mcp
```

**Cursor / generic MCP config (`mcp.json`):**

```json
{
  "mcpServers": {
    "gitscout": {
      "type": "streamable-http",
      "url": "http://127.0.0.1:9000/mcp"
    }
  }
}
```

## Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `GITSCOUT_API_BASE` | `http://localhost:8000/api/v1` | GitScout backend base URL (include `/api/v1`). |
| `MCP_HOST` | `127.0.0.1` | Listener host. |
| `MCP_PORT` | `9000` | Listener port (endpoint is `/mcp`). |
| `GITSCOUT_TIMEOUT` | `60` | Per-request timeout (seconds). |

## Test (offline)

```bash
pip install pytest
pytest tests
```

---

Part of **Developer Mission Control** for the Amazon *Build, Ship, Shape* hackathon
(Alexa+ track + AWS Builder + Open Source mini-challenges). MIT-licensed with the
parent repository.
