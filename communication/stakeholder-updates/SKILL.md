---
name: communication-stakeholder-updates
description: Use when the user needs to write a status update, weekly report, or async stakeholder summary aimed at non-engineers (PM, leadership, customers). Triggers: "write the weekly update", "summarize this sprint for leadership", "draft the customer-facing release note", "what should I tell the steerco". Do NOT use for engineering changelogs / commit summaries, or for formal BA writeups (use business-analysis/skills/ba-initiative-scoping).
---

# Stakeholder Updates

Produces async, skim-first updates for non-engineering audiences. Optimized for the reader who has 30 seconds, with a path to detail for the reader who has 5 minutes.

## When to use

- Weekly / bi-weekly status note to leadership or a steering committee
- Customer-facing release summary
- Async update replacing a recurring status meeting
- Risk escalation note when a project is going sideways

## When NOT to use

- Engineering-only changelog or commit summary → out of scope
- Bug report → `qa/manual/bug-report-writer`; incident postmortem → `communication/incident-postmortem`
- Meeting minutes / decision capture → `communication/meeting-notes`
- Initial scoping of a new initiative → `business-analysis/skills/ba-initiative-scoping`

## Inputs needed

1. **Audience** — leadership, PMs, a specific customer, a steerco
2. **Their decision** — what do you want them to *do* or *know* after reading?
3. **Period covered** — week, sprint, since last update
4. **What shipped, what slipped, what's next**
5. **Any blocker that needs their action**
6. **Confidentiality** — public, internal-all, internal-leadership, customer-shareable

## Procedure

1. **Lead with the headline, not the recap.** First line answers: *should the reader keep reading, and what changes for them?*
2. **TL;DR in 3 bullets max.** A reader who stops here should still walk away with the right picture.
3. **Use RAG status honestly.** Green / Amber / Red applies per workstream, not per project. A single "green" hiding one amber and one red is dishonest reporting.
4. **Wins, slips, next** — three short sections. Past, present, future. No more than 3 items each at this altitude; link out for detail.
5. **Blockers must name an owner and an ask.** "Blocked on legal review" with no ask is venting; "Need legal to confirm by Wed" is a status update.
6. **Translate engineering terms.** "Refactored the ingestion pipeline" → "Reduced data delays from 4h to 20min". If you can't translate it, ask whether it belongs in this audience's update at all.
7. **Risks at the bottom, not buried.** A risk that's not visible can't be acted on.
8. **Length discipline.** Weekly update: under 250 words. Steerco: under 500. If it's longer, you're writing a doc, not an update.

## Output format (weekly)

```markdown
# <Project> — Update for <Audience>
**Period:** <YYYY-MM-DD to YYYY-MM-DD>  **Status:** 🟢 / 🟡 / 🔴

## TL;DR
- <bullet>
- <bullet>
- <bullet>

## Shipped
- <outcome — what the user / business gets now>

## Slipped
- <item> — new date: <YYYY-MM-DD>, reason: <one line>

## Next
- <item> — target: <YYYY-MM-DD>

## Blockers / asks
- **Ask:** <what you need> — **Owner:** <name> — **By:** <date>

## Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|

## Workstream RAG
| Stream | Status | Note |
|--------|--------|------|
```

## Output format (release / customer-facing)

```markdown
# <Release name / version> — <YYYY-MM-DD>

**What's new for you:** <one sentence, user-benefit framing>

## Highlights
- <Benefit-led bullet — not feature-led>

## Improvements
- ...

## Fixes
- ...

## Known issues
- ...

## What's next
- <forward-looking, no firm dates unless committed>
```

## Anti-patterns to flag

- **Activity log masquerading as a status update.** "Team worked on X, Y, Z" — leadership needs *outcomes*, not activity.
- **Single-status project.** Real projects have workstreams that don't all move together.
- **Hidden red.** A green overall with a red dependency is misreporting.
- **Feature-led release notes.** "Added new endpoint /v2/foo" → readers don't care; what does it *enable*?
- **Update with no ask and no decision implied.** Why is the audience reading?
- **Date slip without a new date.** "Delayed" with no commitment is a non-answer.

## Handoffs

- New initiative needs scoping → `business-analysis/skills/ba-initiative-scoping`
- Incident debrief → `communication/incident-postmortem`
- Decisions behind this update need a durable record → `communication/meeting-notes`
