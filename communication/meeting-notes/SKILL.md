---
name: communication-meeting-notes
description: Use when the user needs a meeting written up as decisions and action items — refinement sessions, steercos, workshops, postmortem reviews — from rough notes, a transcript, or a recap dictated after the fact. Triggers: "write up the minutes", "capture the decisions from this refinement", "turn this transcript into action items", "start a decision log for the project". Do NOT use for status updates to stakeholders (use communication/stakeholder-updates), scoping an initiative raised in the meeting (use business-analysis/skills/ba-initiative-scoping), or the postmortem document itself (use communication/incident-postmortem — this skill only captures its review meeting).
---

# Meeting Notes & Decision Log

Turns a meeting — rough notes, a transcript, or a dictated recap — into the two artifacts that matter afterwards: **decisions** (each with a decider and a status) and **action items** (each with one owner and a due date). Everything else is supporting context, kept to a minimum. Maintains a running per-project **decision log** so decisions are never re-litigated invisibly.

`stakeholder-updates` deliberately excludes meeting minutes; this skill owns them. The two compose: minutes capture what was decided, the update communicates it outward.

## When to use

- A refinement / planning / steerco / workshop session needs writing up
- A transcript or messy notes need distilling into decisions + actions
- A project needs a running decision log (or an existing one needs new entries)
- A postmortem review meeting needs its outcomes captured

## When NOT to use

- Reporting status outward → `communication/stakeholder-updates`
- The meeting raised a new initiative that needs scoping → `business-analysis/skills/ba-initiative-scoping` (link it from the notes, don't scope it inside them)
- Requirements elicited in the meeting need structuring → `business-analysis/skills/ba-initiative-scoping` (its elicitation guide)
- The artifact is the postmortem itself → `communication/incident-postmortem`

## Inputs needed

Ask only what's missing:

1. **The raw material** — transcript, notes, or the user's recap
2. **Meeting metadata** — purpose, date, attendees (roles suffice if names are sensitive)
3. **Existing decision log path**, if the project keeps one (append, don't fork)

## Procedure

1. **Distill, don't transcribe.** Nobody reads a prose replay. Collapse discussion to its outcome; keep at most one line of rationale per decision — enough to stop the same debate recurring.
2. **A decision needs a decider.** "We agreed" with no name is how decisions get re-opened. Capture *who decided* (or "consensus — named participants"), the decision, the rationale, and alternatives explicitly rejected (one line — this is the highest-value content months later).
3. **Decisions have statuses: Proposed / Decided / Superseded.** Nothing is ever deleted from a decision log; a reversal is a new entry that marks the old one Superseded with a link. The log is append-only history.
4. **An action item has one owner — a person, not a team — and a due date.** "Owner: frontend team" means nobody. If the meeting didn't assign one, the item goes in as `⚠️ unowned` at the top of the follow-ups — making the gap visible is the skill's job, inventing an owner is not.
5. **Action ≠ decision.** "We'll use Postgres" is a decision; "Marco sets up the Postgres instance by Friday" is the action it spawns. Capture both, cross-referenced.
6. **Open questions get a who-answers and a by-when** — otherwise they are how scope quietly drifts. Parking-lot items (raised, explicitly not discussed) are listed so they aren't lost.
7. **Separate fact from interpretation.** If you're inferring a decision from an ambiguous transcript, tag it `#inferred` and name what was actually said — same observation/inference discipline as `business-analysis`.
8. **Anything that grew beyond a line links out** to its owning artifact (story, BA writeup, postmortem) rather than being restated.

## Output format

```markdown
# <Meeting name> — <YYYY-MM-DD>

**Purpose:** <one line>  **Attendees:** <names / roles>  **Notes by:** <name>

## TL;DR
- <the 1–3 outcomes someone who skipped the meeting must know>

## Decisions
| # | Decision | Decider | Rationale (one line) | Rejected alternatives | Status |
|---|----------|---------|----------------------|-----------------------|--------|
| D-1 | Promo codes are case-insensitive | PO (Elena) | Support tickets show users typing lowercase | Case-sensitive (schema default) | Decided |
| D-2 | Defer multi-code stacking to Q3 | Consensus | Out of current epic's scope | — | Decided |

## Action items
| # | Action | Owner | Due | From | Status |
|---|--------|-------|-----|------|--------|
| A-1 | Update API schema for case-insensitive codes | @marco | 2026-06-17 | D-1 | Open |
| A-2 | ⚠️ unowned — confirm rounding rule with finance | — | — | Q-1 | Open |

## Open questions
- [ ] Q-1: Rounding rule for percentage discounts — **answers:** finance — **by:** 2026-06-19

## Parking lot
- <raised but explicitly not discussed>

## Links
- <stories / BA writeup / postmortem touched by this meeting>
```

For a running **decision log**, append the Decisions rows to the project's `DECISIONS.md` with the meeting date — one table, newest first, statuses maintained.

## Anti-patterns to flag

- **Transcript dump** — ten paragraphs of "then X said…" with the decision buried in the seventh.
- **Decision without a decider** — guarantees the debate reruns next sprint.
- **"Team will look into it"** — no owner, no date, no follow-up protocol; it will not happen.
- **Silent reversal** — a new decision contradicting an old one without marking it Superseded; the log now lies.
- **"Discussed X"** with no outcome recorded — either a decision, an action, an open question, or parking lot; pick one.
- **Minutes as status update** — if it's headed to stakeholders, it's `stakeholder-updates` material, written for that audience.

## Handoffs

- Communicate the outcomes outward → `communication/stakeholder-updates`
- A new initiative surfaced → `business-analysis/skills/ba-initiative-scoping`
- Refinement outcomes change stories → `business-analysis/skills/ba-story-writer` (ours) or `business-analysis/skills/ba-backlog-auditor` (theirs)
- Decisions that change tested behavior → flag to `qa/manual/test-basis-analyzer` (the basis may be stale)
- Postmortem review actions → tracked in the postmortem's action table (`communication/incident-postmortem`)
