# Positioning (applied to the README on Oct 7; Devpost entry still to write)

## Why this exists

Feedback: AI-assisted open-source work is getting pushback because maintainers are flooded with
unreviewed, AI-generated PRs and bounty-farming ("AI slop"). Open source needs the opposite. Our
front door (README, pitch) described the project as the thing maintainers fear.

## One sentence

**Developer Mission Control is a contributor's agent that defers to the maintainer: it checks whether a
project welcomes AI-assisted work before touching it, helps a person understand an issue, and never
changes anything without that person's approval.**

Short form for a title line: *An agent that works for the contributor and defers to the maintainer.*

## The thesis: the opposite of slop is consent, proof and human authorship

| Slop looks like | We do the opposite |
|---|---|
| Fixes whatever is easy, no matter the project's rules | Reads CONTRIBUTING and the PR template first; if the project bans or restricts AI work, the agent refuses to clone and quotes the rule |
| Opens PRs in bulk | One draft PR per issue; drafts only, never a ready-for-review PR |
| Unreviewed output | Every write waits for a signed-in human; the human sees the exact diff first |
| Unverified changes | Tests run before and after; a PR is opened only if they pass |
| Hides that AI was involved | Adds a disclosure line to the PR body when the project asks for one, or has no stated policy |
| Optimises for payout per hour | No bounty ranking, no payout estimates |
| Pushes to someone else's repo | Works in a throwaway sandbox; the base branch is never pushed |

## What the agent will not do (say this out loud in the pitch)

- Work on a project that says it does not accept AI-assisted contributions.
- Open a PR whose tests fail.
- Act without the signed-in person's approval, step by step (no batch approval).
- Email or message anyone except the signed-in user's own confirmed address or chat.

## Language to retire

Remove these from the README, Devpost and any slide:

- "The Bloomberg Terminal for Open-Source Developers" (reads as a trading desk for issues).
- "Bounty & Hourly ROI Engine", "`$/hr`", anything ranking issues by payout.
- "Sub-second multi-channel alerts" (and any claim of live alerts: they are not live).
- "Zero-Mock: Verified" and "100% Passing" badges as headline claims (show real test counts instead).

## Claims ledger: only say what is true today

Check each line against the live system on the day of recording.

| Claim | Status as of Oct 7 |
|---|---|
| Approval gate on every write, signed-in owner only | Live |
| Draft PRs only, base branch never pushed | Live |
| Diff shown before approval | Live |
| Tests run first; PR only if they pass | Live |
| Per-user saved work per branch | Live |
| Email summary to the user's confirmed address | Live (Brevo, port 2525) |
| Repeated on-screen summary fixed (#31) | Deployed Oct 7 |
| AI-policy check (refuses banned projects, adds disclosure line) | Built in the working tree; **not committed, not deployed** |
| Sandbox terminal where the human does the work | Stack deployed to AWS; **no launch proven, no browser terminal** |
| Duplicate-work / competing-PR pre-flight | **Not built** |
| Amazon Bedrock (Nova) reasoning | **Blocked** by account restriction; Gemini fallback in use |
| Alerts | **Not live. Do not claim.** |

Anything marked not live or not built is either finished before recording or left out of the pitch.
