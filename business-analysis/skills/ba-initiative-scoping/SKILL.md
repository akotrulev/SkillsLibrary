---
name: ba-initiative-scoping
description: Use when the user needs to turn a vague business problem, stakeholder request, or feature idea into a structured single-initiative scoping writeup — capturing goals, scope, stakeholders, constraints, risks, and success metrics. Triggers: "do a BA writeup for X", "what's missing from this brief", "help me scope this initiative", "turn this stakeholder ask into something engineering can act on". Do NOT use for writing user stories (use business-analysis/skills/ba-story-writer), checking a feature against the WHOLE project's business model (use ba-feature-conflict-sweep — that's cross-feature, this is one initiative), the testable distillation of a single doc (use qa/manual/test-basis-analyzer), bug reports (use qa/manual/bug-report-writer), or test cases (use qa/manual/test-case-writer).
---

# Initiative Scoping

Converts an ambiguous business request into a structured artifact engineering and product can act on. Output is decision-ready: scope, stakeholders, constraints, risks, success metrics, and open questions — separated and labeled.

## When to use

- A stakeholder dropped a request that's too vague to estimate
- A feature idea needs scoping before it goes to refinement
- You need to surface assumptions before committing to a plan
- A discovery doc needs to be sharper before review

## When NOT to use

- The requirement is already crisp and just needs user stories → `business-analysis/skills/ba-story-writer`
- The user wants a technical design / ADR → out of scope (use a design doc skill)
- The user wants meeting minutes or a status update → `communication/stakeholder-updates`

## Inputs needed

Ask only what's missing:

1. **The ask in the stakeholder's own words** (paste verbatim if possible)
2. **Who is asking** (role + team) and **who is affected**
3. **What problem is this solving?** (the *why*, not the *what*)
4. **Known constraints** — deadlines, budget, compliance, tech stack
5. **What's explicitly out of scope** (if known)
6. **How will we know it worked?** (metric, KPI, qualitative signal)

If the user can't answer "why" or "how will we know it worked", surface that as the first risk — it usually predicts the work will need to be redone.

## Eliciting the inputs (when the stakeholder is available)

When the inputs above don't exist yet and a stakeholder can be asked, drive the discovery — don't wait for a brief. One question at a time; verbatim answers go in the notes (`communication/meeting-notes` for the session writeup).

**Question bank by gap:**

| Missing | Ask |
|---|---|
| The *why* | "Walk me through the last time this problem cost you something — what happened?" Then five-whys until the answer is a business outcome, not a feature. |
| Users | "Who touches this on a bad day? Who complains when it breaks?" (roles → named people) |
| Scope | "If we shipped only one slice this quarter, which? What would you happily never get?" |
| Success | "Six months from now, what number or behavior proves this worked?" Push for baseline → target. |
| Constraints | "What's fixed — date, budget, compliance, systems we must keep?" |
| Risks | "What's the way this most plausibly fails or gets cancelled?" |

**Technique notes:** five-whys for the problem statement (stop at a business outcome, not at "we need the feature"); walk the current workflow end-to-end before discussing the future one (a lightweight event-storming pass — events, actors, pain points — beats abstract requirement talk); ask for the last concrete instance, never the general case ("usually" hides the edge cases that become Open questions).

## Procedure

1. **Separate observation from inference.** Quote the stakeholder verbatim in one section; your interpretation goes in a separate "Analysis" section. Reviewers must be able to challenge the interpretation without re-reading the original.
2. **Force a problem statement before any solution wording.** If the user wrote "add a CSV export button", the problem is *not* "missing button" — it's whatever workflow that button unblocks. Push back until you have it.
3. **Stakeholder map.** List by role: decision-maker, contributor, informed, blocked-by. Names are better than roles when known.
4. **Scope: in / out / deferred.** Three columns. "Deferred" is not "out" — it's a follow-up commitment.
5. **Success metrics must be measurable or explicitly qualitative.** "Improve UX" is not a metric. "Reduce time-to-first-export from 4 min to <1 min for 80% of users" is.
6. **Risks with likelihood × impact.** Two-axis, not a single "risk level". A low-likelihood/high-impact risk needs a mitigation plan; a high-likelihood/low-impact one usually doesn't.
7. **Open questions** are not risks — they are unknowns blocking the analysis. Each one names the person who can answer it.
8. **Assumptions section.** Every assumption you made because the stakeholder didn't say. Reviewers will catch the wrong ones — that's the point.

## Output format

```markdown
# Business Analysis: <short title>

**Requested by:** <name, role>  **Date:** <YYYY-MM-DD>  **Status:** Draft

## 1. Original request (verbatim)
> <quote stakeholder>

## 2. Problem statement
<one paragraph — the *why*, not the *what*>

## 3. Goals & success metrics
- <Goal 1> — Metric: <measurable target>
- <Goal 2> — Metric: <measurable target>

## 4. Stakeholders
| Role            | Name | Interest                          |
|-----------------|------|-----------------------------------|
| Decision-maker  |      |                                   |
| Contributor     |      |                                   |
| Informed        |      |                                   |

## 5. Scope
| In scope | Out of scope | Deferred |
|----------|--------------|----------|
|          |              |          |

## 6. Constraints
- Deadline / budget / compliance / tech / dependency

## 7. Assumptions
1. <assumption>
2. ...

## 8. Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
|      | L/M/H      | L/M/H  |            |

## 9. Open questions (blocking)
- [ ] <question> — owner: <name>

## 10. Recommended next step
<one sentence: refine, prototype, kill, escalate>
```

## Anti-patterns to flag

- **Solution disguised as requirement.** "Add a button that..." — challenge it; what problem does the button solve?
- **Unfalsifiable success metric.** "Better performance" with no number or baseline.
- **Single-axis risk.** "Risk: medium" with no separation of likelihood and impact.
- **Missing decision-maker.** If no one has authority to approve scope, the analysis will not converge.
- **Scope = everything stakeholder mentioned.** A BA who never says "out of scope" isn't doing analysis.

## Handoffs

- Tight enough to refine? → `business-analysis/skills/ba-story-writer`
- Engineering needs a contract? → API/DTO skills under `qa/<stack>/skills/api-dto-writer`
- Stakeholder update needed? → `communication/stakeholder-updates`
- QA needs the testable distillation (business logic, validations, observable implementation notes)? → `qa/manual/test-basis-analyzer` — don't re-derive it here; the BA writeup is one of its inputs
