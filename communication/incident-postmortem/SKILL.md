---
name: communication-incident-postmortem
description: Use when the user needs to write up an incident after it's resolved — a blameless postmortem / incident review / RCA document for internal learning or a sanitized customer-facing RCA. Triggers: "write the postmortem for yesterday's outage", "incident review doc for INC-123", "RCA writeup the customer asked for", "what should the incident report cover". Do NOT use for live incident response or runbooks (out of scope), filing the defect that caused it (use qa/manual/bug-report-writer), or routine status updates (use communication/stakeholder-updates).
---

# Incident Postmortem

Produces a **blameless** postmortem after an incident is resolved: quantified impact, an evidence-based timeline, contributing factors (plural — never a single "root cause" pinned on a person), what went well / what went poorly / where we got lucky, and action items that each have one owner and a due date. Optionally derives a sanitized customer-facing RCA from the internal document.

A postmortem is a learning artifact, not a punishment. Its value is measured by whether the action items ship — a postmortem without follow-through is worse than none, because it creates the illusion of improvement.

## When to use

- An incident is resolved and the team owes a written review (most teams gate this on severity)
- A customer or stakeholder asked for an RCA
- A near-miss revealed a risk worth recording even though impact was avoided ("where we got lucky" is the whole document)
- Recurring small incidents need one consolidating writeup to justify systemic fixes

## When NOT to use

- The incident is still live → respond first; this skill starts after resolution
- You need to file the underlying defect → `qa/manual/bug-report-writer`
- You need to tell stakeholders about status/impact mid-incident → `communication/stakeholder-updates`
- You want monitoring/probes so it's caught earlier next time → that's an action item; implementation lives in `qa/<stack>/skills/synthetic-monitoring` / `chaos-testing`

## Inputs needed

Ask only what's missing, at most 2–3 questions:

1. **The incident facts** — alert/ticket links, chat-channel export, monitoring graphs, deploy log; whatever evidence exists
2. **Impact data** — who was affected, how many, for how long, which SLO/SLA burned, revenue/data effects if known
3. **Audience** — internal engineering-wide (default), or also a customer-facing RCA
4. **Severity classification** the org uses (SEV1–3 or P1–P4), if any

## Procedure

1. **Blameless framing is non-negotiable.** Assume everyone acted with good intent on the information they had. Rewrite every "X should have…" into "what made it easy for this to happen?" — human error is a symptom of a system that allowed it. People are named for *ownership of follow-ups*, never for *causing* the incident; in the narrative, use roles ("the on-call engineer"), not names.
2. **Quantify impact first.** Duration, users/requests affected, SLO burn, data loss, revenue if known. "Some users saw errors" is not impact; "12% of checkout requests failed for 43 minutes (SLO: 99.9%/30d, burned 31% of the monthly budget)" is.
3. **Timeline from evidence, not memory.** One timestamped line per event (UTC, or one declared timezone): first effect, detection, escalations, mitigation attempts (including ones that didn't work), resolution. Mark **detection** and **resolution** explicitly — the gaps between effect→detection (MTTD) and detection→resolution (MTTR) are the two numbers `qa/manual/quality-metrics` consumes.
4. **Contributing factors, plural.** Real incidents have several (a latent bug + a config change + a monitoring gap + an unclear runbook). Walk each "why" until you reach a *system* condition; stop at "human error" and you've stopped too early. Never reduce to one root cause to make the document tidy.
5. **Three lists: went well / went poorly / got lucky.** "Where we got lucky" is mandatory thinking — luck found during an incident is a risk that will not repeat its kindness (e.g. "the senior engineer happened to be online at 2am").
6. **Action items: one owner, one due date, one tracking link each.** "Be more careful" and "improve monitoring" are not action items; "Add alert on checkout error rate > 1% / 5min — @ana — 2026-06-24 — JIRA-481" is. Classify each as *detect sooner*, *mitigate faster*, or *prevent recurrence* — if all your items are in one bucket, you've under-analyzed the other two.
7. **Customer-facing RCA (when asked): derive, don't duplicate.** Strip internal names, system internals, and the lucky catches; keep impact, plain-language cause, what we've done, what we're doing. Never promise dates externally that aren't committed internally.
8. **Publish and follow up.** The document goes where the whole engineering org can read it; action items go into the tracker and get reviewed until closed. Note the review date in the document.

## Output format

```markdown
# Postmortem: <one-line incident description>

**Incident ID:** <INC-123>  **Severity:** <SEV2>  **Status:** Draft / Reviewed / Actions complete
**Date of incident:** <YYYY-MM-DD>  **Author:** <name>  **Review meeting:** <YYYY-MM-DD>

## Summary
<3–5 sentences: what broke, the user-visible effect, duration, how it was resolved. Readable by a non-engineer.>

## Impact
- **Duration:** <first effect → resolution, minutes>
- **Detection (MTTD):** <first effect → detection> — detected by <alert / customer report / chance>
- **Users/requests affected:** <quantified>
- **SLO/SLA:** <which, and budget burned>
- **Data / revenue:** <quantified, or "none">

## Timeline (<timezone>)
| Time | Event |
|------|-------|
| 14:02 | Deploy #842 rolls out to prod |
| 14:09 | Checkout error rate rises to 12% (first effect) |
| 14:31 | **Detected** — customer report via support (no alert fired) |
| 14:40 | Rollback initiated; does not resolve — cache still poisoned |
| 14:52 | Cache flushed — **resolved** |

## Contributing factors
| # | Factor | Type |
|---|--------|------|
| CF-1 | Discount calc assumed non-null promo field; deploy #842 made it nullable | latent defect |
| CF-2 | No alert on checkout error rate — detection was a customer report | monitoring gap |
| CF-3 | Rollback runbook doesn't mention the pricing cache | process gap |

## What went well
- <e.g. rollback executed in <10 min once decided>

## What went poorly
- <e.g. 22 minutes from first effect to detection, via a customer>

## Where we got lucky
- <e.g. incident began outside the regional peak; same failure at 19:00 would have hit 5× traffic>

## Action items
| # | Action | Bucket | Owner | Due | Tracking |
|---|--------|--------|-------|-----|----------|
| A-1 | Alert: checkout error rate >1%/5min | detect | @ana | 2026-06-24 | JIRA-481 |
| A-2 | Add pricing cache to rollback runbook | mitigate | @marco | 2026-06-20 | JIRA-482 |
| A-3 | Null-safety regression test for promo field | prevent | @qa | 2026-06-27 | JIRA-483 |

## Lessons learned
<2–3 sentences: the transferable insight other teams should take from this.>
```

## Anti-patterns to flag

- **A name in the cause.** "Marco's config change broke X" — the system let one config change break X; that's the factor.
- **"Root cause: human error."** Always one why short of the real factor (missing validation, missing review gate, missing alert).
- **Single tidy root cause** when the timeline clearly shows several interacting factors.
- **Action items with no owner or date** — or vague ones ("improve monitoring", "be more careful").
- **All action items in the prevent bucket** — nothing about detecting sooner or mitigating faster next time.
- **Missing "where we got lucky"** — the highest-value section for predicting the *next* incident.
- **Customer RCA written from scratch** instead of derived from the internal document — the two will drift and contradict.

## Handoffs

- MTTD / MTTR / escape-rate feed → `qa/manual/quality-metrics`
- Underlying defect needs filing → `qa/manual/bug-report-writer`
- Stakeholder/customer communication during or right after the incident → `communication/stakeholder-updates`
- Postmortem review meeting minutes + decision tracking → `communication/meeting-notes`
- Prevent/detect action items that are test work → `qa/<stack>/skills/synthetic-monitoring`, `chaos-testing`, or the matching `qa/<stack>` agent
