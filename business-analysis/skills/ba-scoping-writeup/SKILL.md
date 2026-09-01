---
name: ba-scoping-writeup
description: Use when turning a vague business problem, stakeholder request, or feature idea into a structured single-initiative scoping writeup. Carries the elicitation question bank for thin briefs. Triggers: "do a BA writeup for X", "help me scope this initiative", "we got a PRD/BRD — what's actually in scope". Do NOT use for writing user stories (`ba-story-writer`), cross-feature conflict checks (`ba-feature-conflict-check`), or single-doc test distillation (`qa/manual/requirements-breakdown`).
---

# Initiative Scoping

Converts an ambiguous business request into a structured artifact engineering and product can act on. Output is decision-ready: actors, capabilities, constraints, success measures, scope, risks, and open questions — separated and labeled. Inside the delivery lane this document **is** `docs/plans/<NNN>-<initiative>/requirements.md`, written by `requirements-author` (`/dev-refine`); standalone, it is the scoping writeup handed to whoever plans next.

## When to use

- A stakeholder dropped a request that's too vague to estimate
- A feature idea needs scoping before it goes to refinement
- You need to surface assumptions before committing to a plan
- A discovery doc needs to be sharper before review

## When NOT to use

- The requirement is already crisp and just needs user stories → `business-analysis/skills/ba-story-writer`
- The user wants a technical design / ADR for one already-clear feature → `/dev-design` (`ep-brainstorming`)
- The user wants meeting minutes or a status update → not this domain

## Inputs needed

Ask only what's missing, **in one batched message** — numbered, each question with 2–4 concrete options and what will be assumed if unanswered. At most two rounds; a third round means designing by interview, so record the assumption and move on:

1. **The ask in the stakeholder's own words** (paste verbatim if possible)
2. **Who is asking** (role + team) and **who is affected**
3. **What problem is this solving?** (the *why*, not the *what*)
4. **Known constraints** — deadlines, budget, compliance, tech stack
5. **What's explicitly out of scope** (if known)
6. **How will we know it worked?** (metric, KPI, qualitative signal)

If the user can't answer "why" or "how will we know it worked", surface that as the first risk and the first open question — never invent a number to fill the gap, and never refuse to proceed: the rest of the document is still written.

## Eliciting the inputs (when the stakeholder is available)

When the inputs above don't exist yet and a stakeholder can be asked, drive the discovery — don't wait for a brief. Verbatim answers go into §1 of the output. The question bank below is what a live interview draws on; in an agent run its questions are folded into the single batch above, not asked one at a time.

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

1. **Separate observation from inference.** Quote the stakeholder verbatim in §1; constraints in §5 are attributed to whoever stated them; every inference goes in §8. Reviewers must be able to challenge the interpretation without re-reading the original.
2. **Force a problem statement before any solution wording.** If the user wrote "add a CSV export button", the problem is *not* "missing button" — it's whatever workflow that button unblocks. Push back until you have it.
3. **Actors, not a stakeholder list.** Every actor has a goal — what they are trying to get done — and one of them is named the decision-maker who can approve scope. Names are better than roles when known.
4. **Capabilities as outcomes, never mechanism.** §4 says what the system must let an actor do and the business rules with their numbers. No stack, table, endpoint, screen or component — a requirement that names a technology has decided something it was not asked to decide. A business-imposed constraint ("must reuse the current identity provider") is recorded in §5 as a constraint, attributed.
5. **Scope: in / out / deferred.** Three columns. "Deferred" is not "out" — it's a follow-up commitment.
6. **Success must be measurable or explicitly qualitative.** "Improve UX" is not a metric. "Reduce time-to-first-export from 4 min to <1 min for 80% of users" is. A baseline → target where one exists.
7. **Risks with likelihood × impact.** Two-axis, not a single "risk level". A low-likelihood/high-impact risk needs a mitigation plan; a high-likelihood/low-impact one usually doesn't.
8. **Open questions** are not risks — they are unknowns blocking the analysis. Each one names the person who can answer it and what it blocks.
9. **Assumptions section.** Every assumption you made because the stakeholder didn't say, one line each. Reviewers will catch the wrong ones — that's the point.

## Output format

This is the shape of `requirements.md`. Ten sections, this order, none dropped — an empty section says why it is empty.

```markdown
# Requirements — <short title>

**Requested by:** <name, role>  **Date:** <YYYY-MM-DD>  **Status:** Draft

## 1. The ask, verbatim
> <what the user actually said, quoted — never paraphrased; everything below is checked against this>

## 2. Problem & why now
<one paragraph — the problem in the business's terms, and what not doing it costs>

## 3. Actors
| Actor | What they are trying to get done | Role in this initiative |
|-------|----------------------------------|-------------------------|
| <role / name> | <goal> | decision-maker / primary user / contributor / informed |

## 4. What it must do
- <capability, as an outcome an actor gets — no mechanism>
- <business rule, with its number: limit, window, threshold>

## 5. Constraints
- <regulatory / contractual / "must reuse X" / deadline> — stated by <who>

## 6. Success
- <measure with baseline → target, or an explicitly qualitative signal and who judges it>

## 7. Scope
| In scope | Out of scope (refused) | Deferred (follow-up) |
|----------|------------------------|----------------------|
|          |                        |                      |

## 8. Assumptions
1. <every inference made because the stakeholder did not say — one line each>

## 9. Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
|      | L/M/H      | L/M/H  |            |

## 10. Open questions
- [ ] <question> — owner: <name> — blocks: <what>
```

## Anti-patterns to flag

- **Solution disguised as requirement.** "Add a button that..." — challenge it; what problem does the button solve?
- **Technology in §4.** "Store bookings in a new table" is a design decision, not a capability. Record what the actor can do; the mechanism is `solution-planner`'s.
- **Unfalsifiable success metric.** "Better performance" with no number or baseline.
- **Single-axis risk.** "Risk: medium" with no separation of likelihood and impact.
- **Missing decision-maker.** If no one has authority to approve scope, the analysis will not converge.
- **Scope = everything stakeholder mentioned.** A BA who never says "out of scope" isn't doing analysis.

## Handoffs

- Inside the delivery lane → `requirements-author` (`/dev-refine`) runs this skill as its Step 2 and continues into `ba-epic-writer` and `ba-story-writer`
- Standalone and tight enough to refine? → `business-analysis/skills/ba-epic-writer`, then `business-analysis/skills/ba-story-writer`
- QA needs the testable distillation (business logic, validations, observable implementation notes)? → `qa/manual/requirements-breakdown` — don't re-derive it here; this document is one of its inputs. It ships in this plugin; every other `qa/*` peer is invoked separately, never loaded here.
