# Demo: the approval gate on a real action

The assistant triages a bug, then changes a throwaway sandbox of a real repo. Every step that
writes pauses for the user's yes. Only reading is automatic.

## One-time setup (about 10 minutes)

1. **Create the demo repo.** On GitHub create an empty public repo `gitscout-demo-sandbox` under the
   account listed in `GITCI_ALLOWED_OWNERS` (default `nirmitktripathii`). Push the contents of
   `demo/sandbox-repo/` to it:

       cd demo/sandbox-repo
       git init -b main
       git add .
       git commit -m "Initial commit with a known slugify bug"
       git remote add origin https://github.com/nirmitktripathii/gitscout-demo-sandbox.git
       git push -u origin main

   Two of its three tests fail on purpose. `ISSUE.md` describes the bug.
2. **Create a fine-grained token** (GitHub > Settings > Developer settings > Fine-grained tokens):
   repository access: only `gitscout-demo-sandbox`; permissions: Contents read/write, Pull requests
   read/write, Metadata read. Short expiry (7 days). Never paste it into chat or commit it.
3. **Install the test runner** for the Python that will run the Git/CI server: `pip install pytest`.
   Install server dependencies once: `pip install -r git_ci_mcp/requirements.txt -r mcp_server/requirements.txt`
   and the backend's `pip install -r backend/requirements.txt`; in `frontend/` run `npm install`.

## Run it

    $env:GITHUB_TOKEN = "<your token>"
    .\demo\start-demo.ps1

`start-demo.ps1` sets `AGENT_ALLOW_ANONYMOUS_WRITES=true` for the local backend, so the demo needs no
sign-in. That switch exists only for this local demo: a deployed backend leaves it off, and then only a
signed-in, allow-listed GitHub user can approve a change (see "Sign-in" below).

Open http://localhost:3000/alexa and say or type:

> Fix the bug in https://github.com/nirmitktripathii/gitscout-demo-sandbox. The issue is that
> slugify keeps punctuation and does not collapse separators.

Expected sequence (each "needs approval" is a pause you answer with Approve, or say yes, then Send):

| Step | Tool | Gate |
|---|---|---|
| Triage the issue text | `analyze_issue_text` | automatic (read-only) |
| Clone the repo into a sandbox | `sandbox_clone` | **approval** |
| Read the code | `list_files`, `read_file` | automatic |
| Branch | `create_branch` | **approval** |
| Apply the diff it wrote | `apply_patch` | **approval**, shows the exact diff |
| Run the tests | `run_tests` | **approval** |
| Commit | `commit_changes` | **approval** |
| Open a draft PR | `draft_pr` | **approval** |
| Check CI | `ci_status` | automatic |

Decline any step and the mission stops there; nothing after it runs.

## What is safe about it

- Only repos owned by `GITCI_ALLOWED_OWNERS` can be cloned; the base branch is never pushed;
  PRs are drafts; the token is sent as an HTTP header and never stored or logged.
- Patches that touch `.git` or paths outside the repo are rejected before `git apply`.
- `run_tests` runs only an allow-listed command, without a shell, with a time limit and a
  scrubbed environment. It still executes the repo's code, which is why this runs locally on a
  repo you own and is not deployed.

## Sign-in (deployed backend)

Anyone can use the read-only tools. A tool that changes things is hidden from the model, and refused,
unless the caller is signed in with GitHub **and** their login is on `AUTH_ALLOWED_LOGINS`. Only the
user who started a conversation can approve its changes; declining is always allowed.

One-time setup:

1. GitHub > Settings > Developer settings > OAuth Apps > New OAuth App.
   Homepage URL: `https://oss-intelligence-platform.vercel.app`.
   Authorization callback URL: `https://gitscout-api.onrender.com/api/v1/auth/github/callback`.
2. Generate a client secret. On Render (service `gitscout-api`) set:
   - `AUTH_GITHUB_CLIENT_ID`, `AUTH_GITHUB_CLIENT_SECRET` from the OAuth App
   - `AUTH_GITHUB_CALLBACK_URL` = the callback URL above, exactly
   - `AUTH_SECRET` = a random string of 32 or more characters (`python -c "import secrets; print(secrets.token_urlsafe(48))"`). Changing it signs everyone out.
   - `AUTH_ALLOWED_LOGINS` = comma-separated GitHub logins, e.g. `nirmitktripathii`. Empty means nobody may change anything.
   - `FRONTEND_URL` must be the Vercel URL (already set in `deploy/render.yaml`).
3. Open `/alexa`, click "Sign in with GitHub".

The OAuth app asks for no scopes (public profile only): it proves who you are and nothing more.

## Hosted Git/CI server (Render)

The hosted agent can only change things if the Git/CI MCP server is deployed and registered.

1. **Token for the server.** Make a random access token, as for `AUTH_SECRET`:
   `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Set the same value as
   `GITCI_MCP_TOKEN` on the `git-ci-mcp` service and on `gitscout-api`. Without it the server refuses
   to start, and every request without it gets a 401, so nobody can reach the tools except the agent
   backend (which sits behind sign-in and the approval gate).
2. **GitHub token for the server.** A fine-grained token limited to `gitscout-demo-sandbox` (Contents
   and Pull requests read/write, Metadata read), short expiry. Set it as `GITHUB_TOKEN` on `git-ci-mcp`.
3. **Allow-list.** `GITCI_ALLOWED_OWNERS` names the only accounts whose repos can be cloned or tested
   (it runs their tests on the server). Keep it to accounts you control.
4. `gitscout-api` lists the server in `AGENT_MCP_SERVERS` with `"bearer_env": "GITCI_MCP_TOKEN"`:
   the token is read from the environment, never from that JSON.
5. **Telegram report (optional), one chat per signed-in user.** The `send_report` tool messages the
   person who ran the mission. Create a bot with `@BotFather` and set `TELEGRAM_BOT_TOKEN` on both
   `gitscout-api` and `git-ci-mcp`. On `gitscout-api` also set `TELEGRAM_WEBHOOK_SECRET` (make up a
   string of letters, digits, `_` and `-`) and `TELEGRAM_WEBHOOK_URL`
   (`https://<api host>/api/v1/telegram/webhook`); the API registers the webhook with Telegram on
   startup. All of these are set in the Render dashboard only (`sync: false`).

   How a visitor gets reports: on `/alexa`, signed in, they press **Link Telegram**. The page opens a
   one-time `t.me/<bot>?start=<code>` link (it expires in 10 minutes, works once, and only its hash is
   stored); pressing Start in Telegram sends the code to the webhook, which stores that chat against
   their GitHub login. The bot replies naming the account and offering `/stop`. **Unlink** on the page
   or `/stop` in the chat removes it. Only private chats can be linked.

   Who can be messaged: only the chat the signed-in owner of the conversation linked. The model never
   sees or sets the recipient: the backend looks it up and adds it to the call, and drops any `chat_id`
   the model supplies. A user who has not linked is not offered the tool and the assistant tells them
   to press Link Telegram. The Git/CI server accepts the chat id only from the backend (it holds the
   bearer token), validates it as digits, and caps reports per chat (`GITCI_REPORTS_PER_HOUR`, default
   10) and overall (`GITCI_REPORTS_GLOBAL_PER_HOUR`, default 60). The text is a fixed template with
   capped fields sent as plain text, and the link must be a pull request in an allowed repo. Like every
   write, it asks for approval, and the approval card shows the exact message. Test commands run
   without these variables, so a repository's tests cannot read them.

   Note: a bot has one webhook. If the same bot was ever polled with `getUpdates` by another program
   (an earlier alert bot), registering the webhook stops that.
6. **Email (optional), demo mailbox, one address per signed-in user.** The agent reads a made-up inbox and
   can email the signed-in user a summary. The inbox lives in the separate Email Orchestrator
   (`github.com/nirmitktripathii/email-orchestrator`, `render.yaml` there, service `email-orchestrator-mcp`):
   it serves 12 invented emails, one of which is a bug report pointing at the demo sandbox and one of which
   tries to prompt-inject the assistant. It never opens a real mailbox. On that service set `MCP_HTTP_TOKEN`
   (32+ characters), `LLM_API_KEY`, and, to allow sending, `EMAIL_SEND_ENABLED=true`, `SMTP_HOST`, `SMTP_USER`,
   `SMTP_PASSWORD`, and add `send_email` to `EMAIL_HTTP_TOOLS`. On `gitscout-api` set `EMAIL_MCP_TOKEN` to the same
   token and `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` (used for the confirmation code).
   All are dashboard-only values.

   How a visitor gets emails: on `/alexa`, signed in, they type an address in **Email me** and press Send code.
   The backend mails a six-digit code to that address (10 minute life, five wrong guesses and it is spent, only
   its hash stored). Typing the code back links the address to their GitHub login; the page shows it masked.
   Typing someone else's address only makes the platform send them one code mail that names the account and says
   to ignore it; nothing else is sent to an address that has not entered its code. Codes are capped at 3 per hour
   per address and per login.

   Who can be emailed: only that confirmed address. As with Telegram, the `to` argument of `send_email` is removed
   from the schema the model sees, dropped from anything it supplies, and added by the backend from the signed-in
   owner's link, so text in an email cannot redirect a message. A user with no confirmed address is not offered the
   tool. Every send is its own approval card showing the subject and the exact text. The Email server also fixes
   the shape: one plain address, plain text, 150-character subject, 4000-character body, a footer saying an AI wrote
   it, and hourly caps per recipient (5) and overall (30).
7. A full mission (clone, find, branch, read, test, edit, test, diff, commit, draft PR, report) is about
   thirteen tool calls, so set `AGENT_MAX_STEPS` to at least 20 on `gitscout-api`. Changing
   `render.yaml` only takes effect on a blueprint sync; the dashboard value is what runs.

### Who may use it (shared demo)

`AUTH_ALLOWED_LOGINS=*` lets any signed-in GitHub user approve changes, so judges can try the whole flow
without being added by hand. That is safe only because the hosted Git/CI server is pinned to one
throwaway repo: `GITCI_ALLOWED_REPOS=nirmitktripathii/gitscout-demo-sandbox` rejects every other repo,
`GITHUB_TOKEN` can only write to that repo, and pull requests are always drafts. Visitors still sign in,
and only the person who started a conversation can approve its changes.

Do **not** keep `*` if you add a tool that can reach anything personal (a real mailbox, another repo).
Switch to a comma-separated list of logins first. The demo mailbox is made up and an email can only go to an
address its owner confirmed, so `*` stays acceptable with it, but it does let any signed-in user trigger a few
confirmation mails and emails to their own address through your SMTP account, bounded by the caps above.

Visitors leave draft PRs and branches behind. Reset with `demo/reset-demo-repo.ps1` (needs `gh`
signed in as the repo owner). The server runs at most 3 sandboxes at once (they expire after 2 hours),
so if several people try it together a fourth may be told to wait.

### Not built: per-user access to their own repos

Acting on a visitor's own repos needs their own GitHub token (a `public_repo` sign-in scope) and a
fork-and-PR flow, and the server runs a repo's tests, so those would have to move into an isolated
sandbox with no secrets (for example AWS CodeBuild or Fargate). That is the roadmap item, not part of this submission.

