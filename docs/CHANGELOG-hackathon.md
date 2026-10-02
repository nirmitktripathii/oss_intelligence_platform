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
  - **Ownership.** Starting a conversation returns a secret `session_token` exactly once (only
    its hash is stored); reading a mission or answering its approval gate requires it as
    `X-Session-Token`. A mission id alone grants nothing, a foreign mission answers 404, and a
    session id nobody created cannot be claimed.
  - **Progress streaming.** `POST /agent/missions/stream` and
    `POST /agent/missions/{id}/approval/stream` answer with Server-Sent Events
    (`mission_started`, `thinking`, `step`, `tool_start`, `tool_done`, then the final
    `mission`), so a client can show progress instead of a minute of silence.
  - **Deployable.** `deploy/render.yaml` gains a `gitscout-mcp` service (the MCP server, bound
    to `0.0.0.0` so the SDK's localhost-only Host allowlist does not reject the public
    hostname: a loopback bind answers `421`, verified) and the backend's `AGENT_MCP_SERVERS`;
    the keep-alive workflow warms it too.
  - **Untrusted tool output.** Results are JSON-encoded and fenced as data in the prompt; the
    approval gate, not the prompt, is what stops injected text from causing a side effect.
  - Bounded: `AGENT_MAX_STEPS` tool calls per mission (default 6), recovery from up to two
    unusable model replies, no identical repeat calls, and a per-client rate limit
    (`AGENT_RATE_LIMIT`, default 10/minute) on starting and approving missions.
  - **Dormant unless configured**: with `AGENT_MCP_SERVERS` unset the endpoints answer 503 and
    nothing else changes.
- `mcp>=2.2.0,<3` dependency in the backend (MCP client).
- Tests: `backend/tests/test_agent_planner.py` (29) covering the decision loop, approval and
  rejection, replay protection, memory isolation between sessions, session-token ownership,
  fence escaping, server-config validation, the HTTP and streaming API, and the MCP client
  against an in-process MCP server.

### Verified
- Backend suite: **113 passed**.
- Live, end to end, on a developer machine: planner → local GitScout MCP server (Streamable
  HTTP) → hosted GitScout API, reasoning on `gemini:gemini-3.5-flash-lite`.
  - "Find me a beginner-friendly Python issue and explain what's wrong in it" → `search_issues`
    then `analyze_issue`, spoken answer plus a markdown card.
  - Follow-up "how would I fix the first one?" → answered from session memory, no tool calls.
  - With `analyze_issue` left out of `auto_approve`: the mission paused, ran the tool only after
    approval, then completed.

  - Streaming, live: the first event arrives about 2 s after the request and each step shows
    as it happens, instead of one answer after a minute.

### Not yet verified / known limits
- **Not deployed yet.** The Render config is written and the MCP server's public-host behaviour
  is verified, but the `gitscout-mcp` service has not been created on Render, so the hosted
  backend does not run the planner. The hosted backend also needs Redis (Upstash) configured:
  with two workers, missions must be shared through it.
- **Not yet run on Amazon Nova** (Bedrock quota restriction above). The planner is unchanged
  either way; only the provenance label will differ.
- **Session tokens are bearer secrets.** Anyone who has one can act as that conversation, so a
  client must keep it out of URLs and logs. There is no user login yet; add real per-user
  authentication before a side-effecting tool (Git/CI, email) is connected to a public
  deployment.
- **Latency is hidden, not removed.** A full mission still takes about a minute when it runs the
  hosted triage tool; streaming makes that visible progress rather than silence.

---

## 2026-10-01 (simulated Alexa+ web client)

### Added
- **`/alexa` page in `frontend/`** — the simulated Alexa+ client for Developer Mission Control.
  It talks to the agent planner's streaming endpoints and shows what an Alexa+ device would:
  - **Voice in and out.** Browser speech recognition (mic button) and speech synthesis read the
    assistant's `speech` aloud. Both are feature-detected; typing works in every browser, and
    the page says so when voice is unavailable.
  - **Live step timeline.** Each tool the planner picks appears as it happens (queued, running,
    done, failed, needs your OK, declined), with its reasoning and arguments.
  - **Approval card.** A gated tool shows its exact arguments with Approve / Decline buttons; with
    the mic on, saying "yes" or "no" answers it. The approved call runs with those arguments.
  - **"On screen" panel.** The longer `display` answer (links, code) is rendered by a small
    markdown renderer that builds React elements only (no HTML injection from model output;
    links limited to http/https).
  - **Conversation memory.** Follow-ups reuse the session; the session token is a bearer secret
    and is kept in memory only (never storage or a URL), so a reload starts a new conversation.
  - Honest failure states: agent not enabled (503), rate limited (429), network loss, stop button.
- **Nav link** "Alexa+" in the header.

### Fixed
- A Gemini reply with HTTP 200 but no text (blocked or truncated candidate) crashed the provider
  with `KeyError('parts')` and failed the mission. It is now a provider miss, so the chain
  falls through. Regression test added (4 response shapes).

- **Provider cooldown** (`LLM_PROVIDER_COOLDOWN_SECONDS`, default 120): a provider that raises is
  skipped for that long while another can answer, so a broken Bedrock key or a zero quota costs
  one slow call per window instead of ~5 s on every request. The last provider in the chain is
  never skipped.

### Verified
- `tsc`, `next lint` (no new warnings) and `next build` pass; `/alexa` is 117 kB first load.
- Live in the browser against a local stack (GitScout MCP server + backend + Gemini): a spoken-style
  request ran `search_issues` and `get_issue` unattended, paused on `analyze_issue` for approval,
  and after Approve finished with a spoken answer and a markdown card on screen. The layout holds
  at phone width. Backend triage and agent tests: 51 passed (full suite 117 before the cooldown change).

### Not verified
- **Microphone input and spoken replies were not exercised** (the test browser has no speech
  recognition); the typed path is what was run.
- Not deployed: Vercel needs the backend to have the agent enabled (see the known limits above).

---

## Planned (tracked on the battle-plan board)
- Enable the Bedrock provider on the hosted backend (set `AWS_BEARER_TOKEN_BEDROCK` on Render)
  once the account quota restriction is lifted, and record the first live Nova triage here.
- Create the `gitscout-mcp` service on Render, set `UPSTASH_REDIS_*` on the backend, and run
  one mission against the hosted stack.
- **Git/CI MCP** (branch · patch · run tests · CI status · draft PR) against one ephemeral
  demo sandbox.
- Wire the **Email Orchestrator MCP** (upgrade to protocol 2025-11-25 / Streamable HTTP) as an
  agent action for report delivery.
- Terminal/diff panel in the Alexa+ client (arrives with the Git/CI MCP).

## 2026-10-01 (Git/CI MCP)

- New `git_ci_mcp/` server (Streamable HTTP, port 9100): `sandbox_clone`, `create_branch`, `apply_patch`, `show_diff`, `run_tests`, `commit_changes`, `ci_status`, `draft_pr`, `sandbox_status`, `destroy_sandbox`.
- Guardrails: GitHub https URLs only, owner allow-list (default-deny), sandbox count and TTL limits, patch path validation (no absolute, `..` or `.git` paths), exact-match test-command allow-list with no shell and a scrubbed environment, hooks disabled, token passed as an HTTP header and never stored, base branch never pushed, PRs always drafts.
- Verified: 14 offline tests including a full local clone, branch, patch, commit flow. Not verified: a real push and draft PR (needs `GITHUB_TOKEN`).
- Deliberately not in `deploy/render.yaml`: it executes a repo's tests, so it runs locally for the demo.

## 2026-10-01 (Git/CI approval-gate demo, verified end to end)

- Git/CI MCP gained `list_files` and `read_file` (read-only, path-confined, size-capped) and `edit_file` (replace one exact piece of text; more reliable for a model than a hand-written diff). `apply_patch` now uses `git apply --recount` and returns a hint on failure.
- Fixed: git subprocesses ran in text mode, which turned a patch's newlines into CRLF on Windows so patches never applied. They now run on bytes. Clones use `core.autocrlf=false`.
- New `demo/`: `sandbox-repo/` (a small package with a real bug, failing tests and a CI workflow, published as `nirmitktripathii/gitscout-demo-sandbox`) and `start-demo.ps1` (starts both MCP servers, the backend with a 14-step budget, and the frontend). Walkthrough in `docs/DEMO-approval-gate.md`.
- Verified live: one request through the real planner, GitScout MCP and Git/CI MCP produced clone, read, branch, edit, test, commit and draft PR #1 in the demo repo, with GitHub Actions green. Seven writes paused for approval; the test harness answered them. The model was Gemini (Nova quota is still 0).
- Tests: 16 Git/CI tests pass (new: exact-text edit, wrong-count patch, path confinement on the read tools).
- Still not deployed: the Git/CI server runs locally until per-user sign-in exists.

## 2026-10-01 (Per-user sign-in for the agent)

- GitHub OAuth sign-in (`/auth/github/login`, `/auth/github/callback`, `/auth/me`). Identity only: no scopes requested. The API returns a short-lived HMAC-signed token in the URL fragment; the frontend keeps it in sessionStorage and sends `Authorization: Bearer`. There is no user table.
- Agent endpoints: read-only tools stay open to everyone. Tools that change things are hidden from the model and refused unless the caller is signed in and on `AUTH_ALLOWED_LOGINS` (empty = nobody), and only the conversation's owner can approve; declining is always allowed. `AGENT_ALLOW_ANONYMOUS_WRITES` re-opens writes for the local demo only (default off).
- The OAuth `state` is signed, expires in 10 minutes and is bound to the browser by an httponly cookie, so a forged callback cannot sign anyone in.
- `/alexa` shows sign-in, sign-out and a read-only notice. Tests: 25 new in `backend/tests/test_auth.py` (tokens, OAuth round trip with GitHub mocked, 401/403 paths, owner-only approval, planner read-only paths).
- Needs from the operator before it works on the hosted stack: a GitHub OAuth App and the `AUTH_*` values on Render. Until then the hosted agent is read-only.

## 2026-10-02 (Git/CI MCP on Render)

- The Git/CI server now requires `Authorization: Bearer <GITCI_MCP_TOKEN>` on every request and refuses to start on a non-loopback address without a 32+ character token. Before this it had no authentication, so deploying it would have let anyone call its tools directly and skip the approval gate.
- The agent's MCP client can send a bearer token (`bearer_env` in `AGENT_MCP_SERVERS` names the environment variable, so the secret is not in the JSON).
- `deploy/render.yaml`: new `gitci-mcp` service; `gitscout-api` registers it, with only its read-only tools auto-approved, and a 14-step budget.
- Tests: real-server checks for 401 without or with a wrong token, and the client sending the token. Git/CI suite 18 pass; planner suite 33 pass.
- Shared demo: `AUTH_ALLOWED_LOGINS=*` admits any signed-in GitHub user (sign-in and conversation ownership still required). New `GITCI_ALLOWED_REPOS` pins the Git/CI server to `nirmitktripathii/gitscout-demo-sandbox`, which is what makes that safe; `ci_status` is checked against it too. `demo/reset-demo-repo.ps1` clears visitors' draft PRs and branches. Tests: 2 new Git/CI, 2 new auth.
- Not built (roadmap): acting on a visitor's own repos needs their GitHub token, a fork-and-PR flow and test runs in an isolated sandbox with no secrets.
- Hosted run proven: the live app cloned `gitscout-demo-sandbox`, fixed the bug, ran the tests, committed and opened a draft PR from Render. Two things found: a bare repo name gave the model no owner, so it asked for a URL; and the GitHub token needed Contents write. New `AGENT_DEFAULT_REPO` names the working repo in the planner prompt so "the demo sandbox" resolves without a URL. 1 new planner test.

## 2026-10-02 (what the person approves, shown as a diff)

- `/alexa` no longer shows raw JSON when it asks for approval. Each write tool gets a plain card: `sandbox_clone` names the repo, `create_branch` the branch, `edit_file` and `apply_patch` the exact change as a red and green diff, `commit_changes` the message and everything it would commit, and `draft_pr` the repo, branch, title, text and the combined diff, with a note that it is a draft and the main branch is not changed. The exact arguments stay one click away.
- Finished steps show what they produced: `run_tests` as a terminal block (command, passed or failed, output tail, exit code and time), `show_diff` as a diff, `edit_file` as a collapsible diff, and `draft_pr` as a link to the pull request.
- This is the control that makes the approval gate meaningful: the person can see the change before agreeing to it. The same panel is a prerequisite for letting strangers' repos in (see `docs/design/per-user-access.md` on `feature/per-user-access`).
- Also fixed: below the `lg` breakpoint the conversation grid had no shrinkable column, so a long argument line widened the whole page sideways on a phone. Checked at 390px: no horizontal scroll, panels scroll inside themselves.
- Frontend only: new `lib/diff.ts` (no dependency), `change-panels.tsx`, `approval-preview.tsx`. Verified with the typecheck, lint and a stand-in API for a visual check (no JS test framework in this project).

## 2026-10-02 (finish the loop: fix, verify, report)

- **Planner order.** The system prompt now gives the end-to-end order: clone, find the issue (the user's text or the repo's `ISSUE.md`, optionally through `analyze_issue_text`), branch, read, run the tests to see them fail, make the smallest edit, run them again, show the diff, and only if they pass commit and open a draft PR. If they still fail it does not commit; it says what failed.
- **Repeat guard fixed.** The planner refused any identical tool call, so the second `pytest -q` after an edit was blocked. A call now counts as a repeat only when no approved step by a different tool came between. Same check twice in a row is still refused.
- **`send_report` (Git/CI MCP).** Telegram message to one fixed chat (`TELEGRAM_CHAT_ID`; the tool takes no address). Fixed template, title 120 and summary 1200 characters, plain text, the link must be a pull request in an allowed repo, hourly cap. Errors never include the bot token. It lives on the bearer-protected Git/CI server, not on the public GitScout MCP server, because a send tool on an unauthenticated server could be called directly and skip the approval gate. Tests run without the Telegram variables.
- **Approval stays per step.** The report is its own approval card showing the exact message and the fixed recipient; there is no batch approve.
- `/alexa`: a fifth suggestion runs the whole fix-and-report mission; finished reports show "Report sent to Telegram".
- `render.yaml`: `AGENT_MAX_STEPS` 20; the service and URL are `git-ci-mcp` (the blueprint still said `gitci-mcp`, which does not match the live service); Telegram variables added as `sync: false`.
- **Notification endpoints locked down.** Found while checking what the platform already had: `POST /notifications/test` sent real email, Telegram, Discord and WhatsApp messages to any destination for any caller (a mail relay, and a blind request forger through Discord URLs), and listing or deleting subscriptions was open. Now test, list and delete need a signed-in allowed user (also when anonymous agent writes are on); subscribe stays open with a rate limit; destinations must fit their channel (Discord only on Discord's webhook hosts); test text is capped and escaped; Discord mentions are off. Unconfigured channels answer `not_configured`, not delivered, and the broadcast skips them. The frontend now sends the auth header and reads the fields the server really returns.
- **Not wired:** nothing calls `broadcast_issue_alert` when a new issue is indexed, so there is no automatic alert broadcast. The submission should not claim one.
- Tests: Git/CI 31 pass (7 new send_report tests). Backend 177 pass: 156 before the lock-down (3 of them new planner tests for the order and the repeat guard), plus 21 notification tests.


## 2026-10-02 (per-user Telegram reports)

- **Why.** `send_report` went to one fixed chat, the owner's. A visitor who ran the mission would never see their own report, and the demo looked like a feature only the author could use.
- **Linking.** A signed-in user presses Link Telegram on /alexa. The backend makes a one-time code tied to their GitHub login (10 minute life, stored only as a hash, single use, a new code replaces the old one) and returns a `t.me/<bot>?start=<code>` link. Pressing Start sends the code to a webhook that stores the chat against that login. The webhook rejects any request without the secret header, only answers private chats, and `/stop` in the chat unlinks it. The page has Link, Cancel and Unlink and updates by itself.
- **The model never picks the recipient.** The `chat_id` argument of `send_report` is removed from the schema the model sees (and from `/agent/tools`), dropped from anything the model supplies, and added only by the backend from the signed-in owner's link. The mission does not store it. Approving a report sends it to the chat of the person who owns the conversation, even if the model names someone else's.
- **Not linked.** The report tool is not offered, and the planner tells the user to press Link Telegram instead of asking for a chat id. Unlinking between proposal and approval makes the step fail with that message instead of sending.
- **Limits.** Chat ids must be digits. Per-chat hourly cap and a global hourly cap (`GITCI_REPORTS_GLOBAL_PER_HOUR`, default 60) on the Git/CI server. Link creation uses the existing notification rate limit. `TELEGRAM_CHAT_ID` stays only as a fallback for callers that name no chat.
- **Token leak fixed.** httpx logs every request URL at INFO and Telegram URLs contain the bot token, so the token was reaching the logs. The httpx logger is now at WARNING in the backend and the Git/CI server, the bot client never logs URLs or bodies, and a test asserts the token never appears in logs.
- **Operator steps.** Set `TELEGRAM_WEBHOOK_SECRET` on gitscout-api (letters, digits, `_`, `-`), use the same `TELEGRAM_BOT_TOKEN` on both services, redeploy. The webhook registers at startup. A bot has one webhook, so this stops any other program polling `getUpdates` with the same bot.
- Tests: Git/CI 43 pass. Backend 205 pass (28 new in `test_telegram_link.py`). Frontend: `tsc`, lint (only older hook warnings) and `next build` clean; panel checked visually in the unlinked, waiting and linked states at desktop and phone width against a stand-in API.

## 2026-10-02 (email: demo inbox, confirmed address, approved send)

- **Why.** The mission could find, fix, verify and report, but the "tell me" step was Telegram only, and the project's second server (the Email Orchestrator) was not part of the flow. Now the agent can read an inbox, act on a bug report in it, and email the person a summary.
- **Email Orchestrator (separate repo, PR `nirmitktripathii/email-orchestrator#1`).** A hosted Streamable HTTP entry (`dist/http.js`) that fails closed: bearer token of 32+ characters, a required tool allow-list, `/healthz` the only open path. It serves a **demo mailbox** of 12 invented emails (reserved `.example` addresses; one is a bug report pointing at the demo sandbox, one is a prompt-injection attempt) and refuses real accounts unless explicitly told otherwise, so no private mail and no OAuth secrets are on the host. A new `send_email` tool exists only when `EMAIL_SEND_ENABLED=true` and SMTP is fully configured; otherwise it is not registered. One plain address, plain text, length caps, a footer saying an AI wrote it, hourly caps per recipient and overall. The README's "never sends email" claim was rewritten to match.
- **Confirmed address.** A signed-in user types an address on /alexa; the backend mails a six-digit code, and typing it back links the address to their GitHub login. Codes live 10 minutes, are stored as a hash, allow five wrong guesses, and are capped at 3 per hour per address and per login so the form cannot be used to mail a stranger repeatedly. The code mail names the account that asked and says to ignore it. Without SMTP configured the endpoints answer 503 and the panel hides, instead of pretending a mail was sent.
- **The model never picks the recipient.** `to` is removed from the `send_email` schema the model sees, dropped from anything it supplies, and added only by the backend from the signed-in owner's confirmed address (the same mechanism as `send_report`'s `chat_id`). A user with no confirmed address is not offered the tool and is told to link one. Unlinking between proposal and approval makes the step fail instead of sending. The mission does not store the address.
- **Approval.** `send_email` is not auto-approved: each send is its own card showing the subject and the exact text, and the note that the recipient is the confirmed address.
- **Why the structure matters.** Anything the assistant reads in an email is untrusted. The planner prompt says so, and the structure backs it: the recipient is fixed, the text is capped and footed, and a human approves each send. The demo inbox includes an email that tries to redirect the assistant, to show that.
- **Not claimed.** This is not a general mail client: the hosted server reads made-up mail only. Alerts are still not wired (see the previous entries).
- Tests: Email Orchestrator 127 pass (80 before the branch). Backend 243 pass (38 new in `test_email_link.py`: the code flow and its limits, per-user routing, the recipient being dropped and re-added, unlinking before approval). Frontend `tsc`, lint (only older hook warnings) and `next build` clean.

## 2026-10-03 (sandbox pool stuck full for everyone)

- **What a visitor saw.** The mission said it hit a sandbox limit, tried to destroy sandboxes with made-up ids (`sandbox-1`, `sandbox`), got "unknown sandbox id", and gave up. Reported by a third-party tester on the live app, and the owner saw the same errors.
- **Cause.** The Git/CI server has one pool of sandboxes shared by every visitor, capped at 3. Nothing ever freed one: a finished mission never destroyed its sandbox, and a sandbox only expired two hours after it was made. Three missions locked everyone out for up to two hours. The model could not list sandboxes, and no one can free another person's sandbox anyway, so its guessed ids could never work. A restart wipes the disk, which is why it worked again after a redeploy.
- **Fix (server).** The pool now frees itself. Every use of a sandbox counts as activity. When it is full, the sandbox idle longest is deleted if it has been idle at least `GITCI_SANDBOX_RECLAIM_SECONDS` (default 600); if all are busier than that, the caller is told that every sandbox is in use and to try again in about N minutes. Sandboxes idle past `GITCI_SANDBOX_TTL_SECONDS` (now 1800, was 7200) are deleted on the next clone. The cap is 15 (`GITCI_MAX_SANDBOXES`, was 3). Error messages now say where ids come from and not to guess or destroy anyone else's.
- **Fix (planner).** The prompt tells the model to call `destroy_sandbox` with the id `sandbox_clone` gave it when the task is done, never to guess an id, and, if every sandbox is in use, to tell the user to try again in a few minutes instead of trying to destroy any.
- **Why there is still a cap.** It is a ceiling for the machine's disk, not a per-user quota. Every sandbox is a full clone plus whatever its tests install, on a small shared disk; with no cap, one account could clone in a loop until the disk fills and the server falls over for everyone. So there are two numbers: 15 sandboxes on the machine in total, and at most 5 of them per user (`GITCI_MAX_SANDBOXES_PER_USER`). A user opening a sixth gets their own longest-idle one saved and closed, so one person cannot take the whole pool.
- **Saved progress (nobody loses work).** Deleting a sandbox was never the only way to lose work: Render's free plan wipes the whole disk when the service sleeps (15 minutes without traffic) or redeploys, cap or no cap. So a signed-in user's unfinished work is saved off the machine after every change (branch, commit, edit, push): commits as patches, uncommitted edits (new files included) as a diff, in Postgres (`GITCI_SAVE_DATABASE_URL`, table `gitci_saved_work`). Nothing is deleted (idle cleanup, reclaim, `destroy_sandbox`) until that save succeeds. A sandbox whose work cannot be saved is kept, but only for a day (`GITCI_SAVE_GRACE_SECONDS`), so a broken database cannot leave the pool stuck forever; every change that is not saved says so in its tool result (`"saved": false` and a `save_warning`), and the planner tells the user.
- **One record per branch.** The first version kept one record per user and repo, so starting a second issue on the same repo (in another conversation, or after a clean start) overwrote the first issue's saved work on its first change. Now each record is keyed by user, repo and branch. A sandbox writes only the branch it is on, and only a record it created or restored, so two conversations never overwrite each other: if a second sandbox makes changes on a branch that already has saved work, they are not saved and it is told to resume that branch or use another name, and `create_branch` refuses a name that already has saved work. `sandbox_clone` without a branch starts clean and lists the saved branches of that repo (`saved_work`); `sandbox_clone(branch=...)` puts one back (`resumed`), first saving and closing any open sandbox on that branch so the newest copy comes back. `fresh` is gone: a clean clone is the default.
- **Several commits, and stacked branches.** Any number of commits and edits on one branch were already kept (a patch series plus a diff). A branch created while on another feature branch is now recorded as stacked on it: its saved record carries the parent, it comes back with all its commits, and `draft_pr` targets the parent once the parent is on GitHub (so the pull request shows only its own commits). If the parent is not pushed yet, it targets the base branch and says why.
- **Space per user.** Up to 15 saved branches and 100 MB per user (`GITCI_MAX_SAVED_BRANCHES`, `GITCI_MAX_SAVED_BYTES_PER_USER`; 10 MB per branch, `GITCI_MAX_SAVE_BYTES`). A record is deleted 90 days after its last change (`GITCI_SAVE_KEEP_DAYS`), and as soon as its pull request is merged or closed. When a user is full, finished pull requests are cleared first; if that is not enough, the save is refused with the counts, and the user deletes what they choose: `list_saved_work` (read-only, auto-approved) shows branch, commits, files, pull request, date and space used, and `delete_saved_work` (needs approval) deletes one branch and closes its open sandbox. `destroy_sandbox(discard=true)` deletes a sandbox without saving when the user says to throw the work away.
- **Merged or not.** If the saved work has a pull request, the clone asks GitHub first. Merged or closed: the saved work is dropped and the sandbox starts clean. Open: work resumes on the same commits GitHub has, so pushing again is a fast-forward that updates the pull request, and `draft_pr` returns the existing pull request instead of failing.
- **Who owns the work.** The owner is the signed-in GitHub login, injected by gitscout-api like the Telegram chat and the email address, for `sandbox_clone`, `list_saved_work` and `delete_saved_work`: hidden from the model's schema, and anything the model passes is dropped. Without a signed-in user, the list and delete tools are not offered and nothing is saved. Saved work stays private (it is not pushed to GitHub, which would bypass the approval gate for pushes).
- **Test runs.** These are what use CPU and memory, so at most `GITCI_MAX_CONCURRENT_TESTS` (3) run at once; another waits up to 20 seconds for a slot, then is told to run the tests again in a minute.
- **Database size.** At the full 100 MB, ten users would fill a 1 GB free Postgres. Real records are far smaller (a typical fix is a few KB), but the per-user limit is one setting if it needs lowering.
- Tests: Git/CI 95 pass (42 for saved work: work survives a wiped disk and comes back by branch; a second issue in another conversation never touches the first; two sandboxes on one branch never overwrite each other; a saved branch name is not reused; resuming an open branch continues from its latest work; destroy saves first and discard does not; stacked branches target their parent and come back whole; the branch and space limits refuse and then accept after a delete; finished pull requests free their own space; the per-user sandbox share; unsaved changes warn and their sandbox is kept, until the grace period; merged and closed pull requests are not restored; an open one resumes on the pushed commits and pushes again as a fast-forward; work that no longer applies is kept; the file store and a real Postgres store, run locally with `pgserver` and skipped where it is not installed; pull request state and the existing-PR fallback). Backend 251 pass (8 for the owner: hidden from the model, dropped when the model sets it, injected from the signed-in login through the API for clone, list and delete; list and delete not offered when anonymous; the planner rules for resuming and freeing space).
