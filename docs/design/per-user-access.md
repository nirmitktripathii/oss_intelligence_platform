# Real per-user access: design and plan

Status: draft, branch `feature/per-user-access`. Nothing here is merged into `main`, deployed, or on the
hackathon submission path. `main` keeps the shared demo (one throwaway repo, `AUTH_ALLOWED_LOGINS=*`).

## Goal

A signed-in GitHub user points the agent at **their own repo**, or at **someone else's open-source repo**, and the
agent fixes it and opens a draft pull request, with the same approval gate as today.

- Own repo: push a branch to it, open the PR in the same repo.
- Someone else's repo: fork it to the user's account, push to the fork, open the PR from the fork. This is the normal
  open-source workflow.

## What is unsafe today (and why the demo is pinned to one repo)

| # | Problem | Today's mitigation | Why it is not enough for other repos |
|---|---------|--------------------|--------------------------------------|
| 1 | `run_tests` runs the repo's own code on the Git/CI server | exact-match test commands, scrubbed child env, timeout, 3 sandboxes | The child is the same OS user as the server. On Linux a test can read `/proc/<parent>/environ` and take `GITHUB_TOKEN` and `GITCI_MCP_TOKEN`. Safe only because we own the one repo. |
| 2 | One shared `GITHUB_TOKEN` | fine-grained, demo repo only | It cannot act on anyone else's repo, and widening it would let every visitor act as the owner. |
| 3 | Repo content and test output go back to the model | approval gate shows each write | A hostile repo can contain text aimed at the model ("prompt injection"). The gate is the defence, so the user must see what they approve (diff panel). |

Problems 1 and 2 are what this branch fixes. Problem 3 is reduced, not removed (see Threat model).

## Design

```
 Browser (/alexa)  --sign in-->  GitHub (grants access to the user's own account)
        |                              |
        |  Bearer session token        |  user access token
        v                              v
 Agent backend (gitscout-api)  ---- stores token server-side, encrypted ----
        |   per tool call: Authorization (shared secret) + X-GitHub-User-Token
        v
 Git/CI MCP server  -- clone / fork / push / open PR with THE USER'S token (memory only)
        |
        |  run_tests: source tarball only, no credentials
        v
 Isolated test runner (ephemeral, no secrets, no inbound network, time and size limits)
```

### A. Isolated test runner (the part that makes strangers' repos safe)

`run_tests` stops running a subprocess on the server. It hands the working tree to a **runner** and gets back
`{exit_code, output_tail, timed_out}`. The runner has to guarantee:

- **No secrets in reach.** The runner's role has no permissions beyond writing its own logs. No tokens are passed in.
- **Ephemeral.** One fresh environment per run, destroyed afterwards. Nothing survives between runs or between users.
- **Bounded.** CPU, memory, disk and wall-clock limits; output size cap.
- **No inbound network.** Outbound is allowed only if needed to install dependencies, and logged.
- **The caller holds the keys.** The server (not the test code) holds the cloud credentials that start the runner.

Runner interface (new, in `git_ci_mcp`): `TestRunner.run(tarball, command, timeout) -> RunResult`, with
`LocalRunner` (today's behaviour, kept for the demo repo and local development) and a remote runner chosen by
`GITCI_RUNNER=local|codebuild|lambda`. The default stays `local`, so merging the interface changes nothing live.

Options considered:

| Option | Fit | Cost / effort | Notes |
|--------|-----|---------------|-------|
| **AWS CodeBuild** | Best general fit. Fresh container per build, any language image, IAM role with only log access, source from an S3 object so no Git credentials are needed. | About $0.005 per build minute. Provisioning adds roughly 20 to 60 s. Needs a small CDK stack. | Strong AWS story for the AWS Builder mini. Recommended. |
| AWS Lambda (container image) | Simplest spike: seconds to start, near-zero cost, no-permission role. | 15 minute cap, one runtime image per language. | Good for a first working slice with Python repos. |
| ECS Fargate task | Most control (network rules, bigger machines). | Most setup: cluster, VPC, task definition. | Overkill for now. |
| Daytona / E2B | Fastest to integrate, built for untrusted code. | Third-party service and key. | Not AWS; consider for the SaaS later. |

Recommendation: build the interface, then a CodeBuild runner. If time is short, a Lambda runner for Python repos is a
legitimate first slice behind the same interface.

Open check: this account is on the AWS **free plan**. Confirm CodeBuild (or Lambda) can be created before committing
to either. The CLI session has expired, so this needs `aws login` first.

### B. Per-user token plumbing

1. **Ask for access at sign-in.** Today sign-in requests no scopes. Two ways to ask for repo access:
   - OAuth App with `public_repo` (the quick option): read and write on **all** of the user's public repos. Coarse.
   - GitHub App with user-to-server tokens (the proper option): the user installs it on **chosen repos only**,
     permissions are Contents and Pull requests, tokens expire after 8 hours. More setup, much smaller blast radius.
   The first slice can use `public_repo` behind a flag; the GitHub App is the target.
2. **Keep the token server-side.** The browser never receives it. The backend stores it encrypted (AES-GCM, a key
   separate from `AUTH_SECRET`) in Redis with a TTL no longer than the session. Sign-out deletes it.
3. **Pass it per call, not through the model.** For Git/CI tool calls the planner adds the user's token as a request
   header. It is never in tool arguments, prompts, mission steps, logs, or results. The existing output scrubbing
   (`secret=` in `_git`) stays.
4. **The server verifies it.** For each request the Git/CI server calls GitHub `GET /user` with the token and
   checks the login matches what the backend claimed (cached briefly). A stolen backend secret alone is not enough
   to act as a user.

### C. Repo policy (replaces the single-repo pin)

- Own repo (`owner == verified login`): branch and PR in place.
- Other public repo: fork to the user's account (`POST /repos/{o}/{r}/forks`), wait until it exists, push the
  feature branch to the **fork**, open the PR as `login:branch` against upstream, always as a draft.
- Never push to a repo the user cannot write to, never push the base branch, never force-push.
- Limits per user: sandboxes at once, runs per hour, repo size, clone depth, test time. Public repos only (no
  private repo access is requested).
- `GITCI_ALLOWED_REPOS` and `GITCI_ALLOWED_OWNERS` still apply when set, so the demo deployment can stay pinned.

### D. Making the approval useful

Approving a write blind is the weak point (problem 3). Before this ships to strangers, `/alexa` should show the exact
diff for `edit_file`, `apply_patch` and `commit_changes`, and the target (`fork of X`, branch name). This overlaps the
planned diff panel and should be built once, for both.

## Threat model

| Threat | Control |
|--------|---------|
| Test code steals server secrets | Tests never run on the server (runner A). |
| Test code uses the network to exfiltrate the repo or abuse a host | Runner has no secrets to leak; outbound limited and logged; short life. |
| Fork bomb, huge output, endless run | Runner CPU/memory/time limits; output cap; per-user rate limits. |
| User A uses user B's token | Tokens are keyed by verified login; the Git/CI server re-verifies with `GET /user`. |
| Backend bearer secret leaks | Attacker still needs a user token, which exists only in the backend's encrypted store and in memory during a call. |
| Prompt injection in a hostile repo makes the agent do harm | Writes are gated, the user sees the diff and target, the token only reaches the user's own account and forks, PRs are drafts. Residual risk: the user approves something harmful. |
| Token left on disk or in logs | Header only, never in URLs or git config, scrubbed from output, encrypted at rest, TTL, deleted on sign-out. |
| Abuse of the shared platform (spam PRs to others) | Rate limits, draft PRs only, per-user caps, ability to switch the feature off with one flag. |

## Phases and acceptance

| Phase | Deliverable | Done when |
|-------|-------------|-----------|
| 0 | This document reviewed; runner choice made; AWS account checked | Decisions below answered |
| 1 | `TestRunner` interface + `LocalRunner`, no behaviour change | Existing Git/CI tests pass unchanged |
| 2 | Remote runner (CodeBuild or Lambda) + IaC in `infra/per-user-runner/` | A test that tries to read the parent environment and the metadata endpoint finds nothing; timeouts and output cap enforced; a Python repo's tests run end to end |
| 3 | Per-user token store and per-call passthrough (flagged off) | Token never appears in logs, steps or model prompts (tested); wrong-user attempts rejected |
| 4 | Own-repo flow, then fork-and-PR flow | Draft PR opened in a test account's own repo and from a fork of a third-party repo |
| 5 | Diff and target shown before each write | Approval card shows the real diff |
| 6 | Hardening: rate limits, logging, kill switch, GitHub App | Reviewed against the threat model |

## Isolation from the submission code

- Work lives on `feature/per-user-access`, in its own git worktree. `main` is not touched.
- Render deploys from `main` only, so nothing on this branch reaches the live app until it is merged.
- Every behaviour change is behind a flag that defaults to today's behaviour (`GITCI_RUNNER=local`, per-user mode off).
- Cloud resources for the runner live in their own AWS stack, separate from anything the live app uses, so they can be
  deleted without affecting it.
- The merge decision is made after Phase 2, once the cost and the schedule are known. Phase 1 and 2 alone are already
  a complete, defensible AWS-flavoured addition if the rest has to wait.

## Decisions needed

1. **Runner:** CodeBuild (recommended), Lambda for a faster first slice, or a third-party sandbox.
2. **GitHub access:** `public_repo` OAuth first (quick, coarse) or go straight to a GitHub App (more setup, safer).
3. **Scope for the submission:** keep this entirely post-hackathon, or pull Phases 1 and 2 into the submission for the
   AWS story if the main path is on schedule.
4. **AWS:** run `aws login` for profile `hackathon` so the free-plan check can be done.
