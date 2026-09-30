# Hackathon Change Log — Build, Ship, Shape (Amazon Developer Hackathon 2026)

This file documents the **significant updates made after the submission window opened
(Aug 31, 2026, 10:15 AM PT)**, as required by the hackathon rules for a project that
existed prior to the window.

**Baseline:** The `oss_intelligence_platform` (GitScout) repository was created
**Aug 30, 2026** — roughly one day before the window opened. Under the rules it therefore
counts as a *pre-existing* project, so every entry below is work done **during** the
Submission Period and is what the submission is judged as "new".

**Submission target:** Alexa+ primary track + AWS Builder mini-challenge + Open Source
mini-challenge. Flagship: *Developer Mission Control* — an Alexa+-accessible agent that
discovers → understands → fixes → communicates open-source work, with GitScout as the
intelligence engine exposed over MCP.

---

## 2026-09-22

### Added
- **`LICENSE`** — MIT license file at repo root, so GitHub detects and displays the license
  in the About panel (the README already declared MIT and linked `LICENSE`). Required for the
  public-repo submission path and the Open Source mini-challenge.
- **`mcp_server/`** — new **GitScout MCP server** (Python, official `mcp` SDK, Streamable HTTP
  transport, MCP protocol ≥ 2025-11-25). A thin, spec-compliant MCP layer over the existing
  GitScout FastAPI intelligence engine. Spike tools:
  - `search_issues` — live, open, unassigned GitHub issues + funded bounties (wraps `GET /issues`).
  - `get_issue` — full issue detail (wraps `GET /issues/{id}`).
  - `analyze_issue` — AST-localized, source-grounded AI triage: root cause, reproduction, fix
    plan, contributing rules, confidence (wraps `GET /triage/{id}`).
  - `analyze_issue_text` — on-demand triage for arbitrary issue text (wraps `POST /triage/generate`).
  - `gitscout_health` — connectivity/telemetry check (wraps `GET /health`).
- **`docs/CHANGELOG-hackathon.md`** — this file.

### Verified
- Built the MCP server against the **official `mcp` SDK v2.2.0** (the 2.x line renamed
  `FastMCP` → `MCPServer`; the code uses the 2.x API).
- End-to-end handshake with a real MCP client over Streamable HTTP **negotiated protocol
  version `2025-11-25`** and enumerated all five tools with the tools capability advertised.
  This confirms the Alexa+ track's hard transport/protocol requirement is met. (Offline
  smoke tests in `mcp_server/tests/` assert the tool surface without needing the backend.)
- **Live integration proven** against the hosted GitScout backend
  (`https://gitscout-api.onrender.com/api/v1` — Neon Postgres + Upstash Redis, 2,339 issues):
  through MCP, `gitscout_health`, `search_issues` (315 bounty matches), and `analyze_issue`
  (real AST localization → `rustchain_bounties/core.py`, reproduction + 4-step fix plan) all
  returned correctly-shaped live data. Note: when this entry was written the hosted backend ran
  **AST-only** triage (`llm_enhanced:false`). As of **2026-09-23** it runs **LLM-enhanced** triage
  via a Gemini provider (`llm_enhanced:true`, confidence `0.95` on the same issue; 2,354 issues
  indexed). Adding an **Amazon Bedrock** provider therefore gives an AWS-native, source-grounded
  reasoning path *alongside* Gemini — not the step that "unlocks" triage (AWS Builder mini-challenge).

### Why it matters
This turns GitScout from a web dashboard into an **agent-accessible intelligence engine**: the
same tools can be driven by Alexa+, by an MCP client such as Claude Code / Cursor, or by the
project's own web UI. It is the core "significant update" for the hackathon and the deliverable
for the Open Source mini-challenge.

---

## Planned (tracked on the battle-plan board)
- Add an **Amazon Bedrock** provider *alongside* the current Gemini provider for
  triage/fix-plan/mission reasoning in `backend/app/triage/llm_engine.py` — an AWS-native,
  source-grounded path (AWS Builder mini-challenge hook).
- **Git/CI MCP** (branch · patch · run tests · CI status · draft PR) against one ephemeral
  demo sandbox.
- Wire the **Email Orchestrator MCP** (upgrade to protocol 2025-11-25 / Streamable HTTP) as an
  agent action for report delivery.
- **Simulated Alexa+ web client** (in `frontend/`) — conversational orchestrator + terminal/diff panel.
