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
