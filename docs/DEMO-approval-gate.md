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
   `GITCI_MCP_TOKEN` on the `gitci-mcp` service and on `gitscout-api`. Without it the server refuses
   to start, and every request without it gets a 401, so nobody can reach the tools except the agent
   backend (which sits behind sign-in and the approval gate).
2. **GitHub token for the server.** A fine-grained token limited to `gitscout-demo-sandbox` (Contents
   and Pull requests read/write, Metadata read), short expiry. Set it as `GITHUB_TOKEN` on `gitci-mcp`.
3. **Allow-list.** `GITCI_ALLOWED_OWNERS` names the only accounts whose repos can be cloned or tested
   (it runs their tests on the server). Keep it to accounts you control.
4. `gitscout-api` lists the server in `AGENT_MCP_SERVERS` with `"bearer_env": "GITCI_MCP_TOKEN"`:
   the token is read from the environment, never from that JSON.

### Who may use it (shared demo)

`AUTH_ALLOWED_LOGINS=*` lets any signed-in GitHub user approve changes, so judges can try the whole flow
without being added by hand. That is safe only because the hosted Git/CI server is pinned to one
throwaway repo: `GITCI_ALLOWED_REPOS=nirmitktripathii/gitscout-demo-sandbox` rejects every other repo,
`GITHUB_TOKEN` can only write to that repo, and pull requests are always drafts. Visitors still sign in,
and only the person who started a conversation can approve its changes.

Do **not** keep `*` if you add a tool that can reach anything personal (email send, another repo).
Switch to a comma-separated list of logins first.

Visitors leave draft PRs and branches behind. Reset with `demoeset-demo-repo.ps1` (needs `gh`
signed in as the repo owner). The server runs at most 3 sandboxes at once (they expire after 2 hours),
so if several people try it together a fourth may be told to wait.

### Not built: per-user access to their own repos

Acting on a visitor's own repos needs their own GitHub token (a `public_repo` sign-in scope) and a
fork-and-PR flow, and the server runs a repo's tests, so those would have to move into an isolated
sandbox with no secrets (for example AWS CodeBuild or Fargate). That is the roadmap item, not part of this submission.

