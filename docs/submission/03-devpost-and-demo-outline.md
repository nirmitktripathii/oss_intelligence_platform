# Devpost pitch and demo outline (working draft)

## Devpost: tagline

An agent that works for the contributor and defers to the maintainer.

## Devpost: inspiration

Maintainers are being buried in AI-generated pull requests nobody asked for. We wanted an agent that
behaves the way a good contributor does: reads the project's rules first, asks before acting, shows
its work, and leaves the decision to a person.

## Devpost: what it does

Say one sentence to an Alexa+-style client. The agent reads the repository's contribution and AI
policy, then works in a throwaway sandbox: it reads the code, runs the tests, proposes a small change,
and shows you the exact diff. Each write (clone, edit, test run, commit, draft PR, email) waits for
your approval. If the project does not accept AI-assisted work, the agent refuses and quotes the rule.
If tests fail, it opens nothing. Want to learn instead of delegate? Ask for a terminal: you do the
work and the assistant explains and hints.

## Devpost: how we built it

- Alexa+-style web client (Next.js on Vercel) with voice, pause and review, and an on-screen history.
- Agent planner (FastAPI on Render) with default-deny tool access, session tokens and live progress.
- Three MCP servers over Streamable HTTP, spec 2025-11-25: GitScout (issue intelligence), Git/CI
  (sandboxed execution) and Email (demo mailbox).
- Per-user GitHub sign-in; only the conversation's owner can approve a change.
- AWS: say exactly what is used on the day. Bedrock is blocked on this account
  the account restriction), so describe the integration and the evidence honestly. If the Fargate sandbox
  terminal is proven by then, include it.

## Devpost: challenges

Keep the real ones: a model ending a mission half-way (fixed by sending a premature "final" back
once), a sleeping free-tier server dropping out of the tool list (retried and named), Render blocking
SMTP ports (Brevo on 2525), and the Bedrock restriction.

## Devpost: what we are proud of

An approval gate that held up on a live hosted run, and an agent that can say no.

## Devpost: what's next

Duplicate-work pre-flight (is it claimed, is a PR already open), a browser terminal, a fork-and-PR flow
for other people's repositories, tests in an isolated no-secrets sandbox. State these as next, not done.

---

## Demo video outline (target 2:40, hard limit 3:00)

The hook is a refusal, not a fix.

| Time | Beat | On screen | Line |
|---|---|---|---|
| 0:00 | Problem | Maintainer-style pull-request pile, text only | "Maintainers are drowning in AI-generated pull requests." |
| 0:12 | Thesis | Title card | "This agent works for the contributor and defers to the maintainer." |
| 0:20 | **The refusal** | `/alexa`: ask it to fix an issue in a repo whose CONTRIBUTING bans AI work | The agent declines, quotes the rule, and leaves the choice to the user. |
| 0:50 | Consent | Same page: a repo that welcomes AI work with disclosure | "Here the project asks for disclosure, so the agent will say so in the PR." |
| 1:05 | Mission | One sentence: check inbox for a bug report, fix it, open a draft PR, email me a summary | Approval cards appear one at a time. |
| 1:20 | Human gate | Approval card with the diff panel | "Nothing writes until I approve. I can see the exact change." Approve step by step. |
| 1:50 | Proof | Tests fail, then pass; draft PR on GitHub with the disclosure line and green CI | "It opens a draft only because the tests pass." |
| 2:15 | Email | The summary in the inbox | "The summary goes to my confirmed address, never one the model picks." |
| 2:30 | Close | Architecture frame, MCP, AWS | "Consent first. Proof, not volume. A person decides." |

### Before recording (checklist)

- [ ] AI-policy check committed, deployed to `gitscout-api`, and tested live on both repos.
- [x] Throwaway repo whose CONTRIBUTING bans AI-assisted PRs, for the refusal beat: nirmitktripathii/gitscout-demo-no-ai (detector verdict: prohibited).
- [ ] Demo state clean: no open draft PRs, no saved branch `fix-slugify-bug`, all Render services awake.
- [ ] Signed in with GitHub on `/alexa`; email address confirmed.
- [ ] Claims ledger in `01-positioning.md` checked line by line.
- [ ] Video under 3:00, public, in English, with a text description of the features.

### Cut if time is short

The terminal and the duplicate-work pre-flight. The refusal beat, the gated mission and the proof are
the story; everything else is extra.
