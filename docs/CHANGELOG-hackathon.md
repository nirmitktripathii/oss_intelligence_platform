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

## 2026-09-30

### Added
- **Amazon Bedrock provider** in `backend/app/triage/llm_engine.py` — a fifth LLM provider
  *alongside* Gemini / Groq / OpenAI-compatible / Ollama, using the Bedrock **Converse API**
  through `boto3` (run off the event loop, bounded by the same timeout budget as the other
  providers). Default model: **Amazon Nova 2 Lite** via the US cross-region inference profile
  `us.amazon.nova-2-lite-v1:0`.
  - **Dormant unless configured.** Enabled only by an explicit credential: a Bedrock API key in
    `AWS_BEARER_TOKEN_BEDROCK` (deploys) or a named CLI profile in `BEDROCK_AWS_PROFILE` (local
    dev). Ambient AWS credentials never route traffic here by accident.
  - **Leads the auto chain, degrades gracefully.** Order is Bedrock → Gemini → Groq → OpenAI →
    Ollama; any Bedrock error falls through to the next provider, then to AST-only triage.
  - **Own model override** (`BEDROCK_MODEL_ID`): the shared `LLM_MODEL` is not applied to
    Bedrock, since a Gemini/Groq model id is invalid there.
  - `maxTokens` is always sent (`BEDROCK_MAX_TOKENS`, default 4096) and non-text content blocks
    (e.g. reasoning) are dropped from the returned text.
- `boto3[crt]>=1.39.0` dependency (1.39 is the first line that reads Bedrock API keys; `crt` is
  needed for `aws login` credentials in local dev).
- Tests: provider-chain ordering, API-key-only enablement, Converse request shape, and
  Bedrock-failure fallback. A suite-wide fixture keeps tests off real Bedrock even when a
  developer `.env` enables it.

### Verified
- Backend suite: **84 passed**.
- Request path exercised against the real Bedrock endpoint in `us-east-1`: authentication and
  request signing succeed and the call reaches the Converse operation.

### Not yet verified
- **No live model response yet.** The AWS account's Bedrock inference quotas are currently
  applied at `0` (new-account restriction), so Converse returns
  `ValidationException: Operation not allowed` and the engine falls back as designed. An AWS
  Support case is open. The hosted backend therefore still answers with Gemini, and the
  **AWS Builder mini-challenge is not claimed** until a triage response carries
  `bedrock:us.amazon.nova-2-lite-v1:0` provenance.

---

## 2026-09-30 (agent planner)

### Added
- **Agent planner** in `backend/app/agent/` — turns one spoken request into a sequence of MCP
  tool calls and a short spoken answer. Endpoints under `/api/v1/agent`: `GET /tools`,
  `POST /missions`, `GET /missions/{id}`, `POST /missions/{id}/approval`.
  - **Provider-neutral.** Every decision goes through the existing LLM chain (Bedrock → Gemini →
    Groq → OpenAI → Ollama), one JSON decision per turn, with no provider-specific tool-calling
    API. Switching providers needs no planner change.
  - **Tools come only from MCP servers** over Streamable HTTP (`AGENT_MCP_SERVERS`), the same
    surface Alexa+ uses. Adding a server is configuration, not code.
  - **Approval gates, default-deny.** A tool runs unattended only if the operator listed it in
    that server's `auto_approve`; anything else pauses the mission (`awaiting_approval`) and,
    once approved, runs with exactly the arguments the user was shown. A server's own
    annotations are not trusted for this decision.
  - **Session memory.** Missions sharing a `session_id` see the last three turns, so "how would
    I fix the first one?" resolves without another search.
  - **Untrusted tool output.** Results are JSON-encoded and fenced as data in the prompt; the
    approval gate, not the prompt, is what stops injected text from causing a side effect.
  - Bounded: `AGENT_MAX_STEPS` tool calls per mission (default 6), recovery from up to two
    unusable model replies, no identical repeat calls, and a per-client rate limit
    (`AGENT_RATE_LIMIT`, default 10/minute) on starting and approving missions.
  - **Dormant unless configured**: with `AGENT_MCP_SERVERS` unset the endpoints answer 503 and
    nothing else changes.
- `mcp>=2.2.0,<3` dependency in the backend (MCP client).
- Tests: `backend/tests/test_agent_planner.py` (24) covering the decision loop, approval and
  rejection, replay protection, memory isolation between sessions, fence escaping, server-config
  validation, the HTTP API, and the MCP client against an in-process MCP server.

### Verified
- Backend suite: **108 passed**.
- Live, end to end, on a developer machine: planner → local GitScout MCP server (Streamable
  HTTP) → hosted GitScout API, reasoning on `gemini:gemini-3.5-flash-lite`.
  - "Find me a beginner-friendly Python issue and explain what's wrong in it" → `search_issues`
    then `analyze_issue`, spoken answer plus a markdown card.
  - Follow-up "how would I fix the first one?" → answered from session memory, no tool calls.
  - With `analyze_issue` left out of `auto_approve`: the mission paused, ran the tool only after
    approval, then completed.

### Not yet verified / known limits
- **Not deployed.** The hosted backend does not run the planner yet; it needs the GitScout MCP
  server hosted alongside it.
- **Not yet run on Amazon Nova** (Bedrock quota restriction above). The planner is unchanged
  either way; only the provenance label will differ.
- **No caller authentication** on the mission and approval endpoints: a mission id is an
  unguessable token, but anyone holding it can approve. This must be closed before a
  side-effecting tool (Git/CI, email) is connected.
- **Latency.** Missions run synchronously; the first live mission took about a minute (mostly
  the hosted triage call), which is too slow for voice without progress updates.

---

## Planned (tracked on the battle-plan board)
- Enable the Bedrock provider on the hosted backend (set `AWS_BEARER_TOKEN_BEDROCK` on Render)
  once the account quota restriction is lifted, and record the first live Nova triage here.
- Deploy the agent planner: host the GitScout MCP server next to the backend, add caller
  authentication to the mission endpoints, and stream mission progress.
- **Git/CI MCP** (branch · patch · run tests · CI status · draft PR) against one ephemeral
  demo sandbox.
- Wire the **Email Orchestrator MCP** (upgrade to protocol 2025-11-25 / Streamable HTTP) as an
  agent action for report delivery.
- **Simulated Alexa+ web client** (in `frontend/`) — conversational orchestrator + terminal/diff panel.
