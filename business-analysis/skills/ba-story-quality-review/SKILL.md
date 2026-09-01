---
name: ba-story-quality-review
description: Use when stories or epics were authored by someone else (client, another team, a PO) and need a review-only readiness audit before refinement or test design — INVEST, AC quality, testability, dependency hygiene. Triggers: "review these stories", "are these stories ready for the sprint", "prep these tickets for refinement", "are these ACs testable". Do NOT use to write or fix stories (`ba-story-writer`), shape epics (`ba-epic-writer`), or scope a vague ask (`ba-scoping-writeup`).
---

# Backlog Reviewer

Review-only intake audit for stories and epics **authored elsewhere**. Produces a per-story readiness verdict (Definition-of-Ready gate) plus a findings table in the library's standard severity format. Does **not** rewrite anything — it points to the fix and names the skill that applies it.

The chain assumption "we write the stories" often doesn't hold: backlogs arrive from clients, other teams, or an existing tracker. This skill is the entry point for that case, sitting in front of refinement and of the QA pipeline (`qa/manual/requirements-breakdown` consumes only stories that pass here, or proceeds with the gaps explicitly flagged).

## When to use

- Stories/epics arrive from outside the team and must be assessed before anyone commits to them
- A sprint-planning or refinement session needs a Definition-of-Ready check on candidate stories
- QA asks "can we design tests from these?" — testability audit before `qa/manual/requirements-breakdown`
- A backlog has grown organically and needs a batch hygiene pass (duplicates, god stories, dependency knots)

## When NOT to use

- You're writing or repairing the stories → `business-analysis/skills/ba-story-writer` (it fixes; this skill only finds)
- The "story" is really an unscoped initiative → `business-analysis/skills/ba-scoping-writeup`
- Epic shape needs *designing*, not auditing → `business-analysis/skills/ba-epic-writer`
- You want the testable distillation of the stories → `qa/manual/requirements-breakdown` (run this review first)

## Inputs needed

Ask only what's missing, at most 2–3 questions:

1. **The stories/epics** — pasted, exported, or a path; include AC and any linked epic
2. **Purpose of the review** — sprint readiness, refinement intake, or pre-test-design testability (changes which severities block)
3. **The team's Definition of Ready**, if non-standard (otherwise the checklist below is the DoR)

## Review checklist

Apply per story. Each failed check becomes one finding row with a severity.

**Story shape**
- As-a / I-want / So-that present; role is specific ("logged-in admin", not "user")
- The *so-that* names value to a person, not "so the system can…"
- It's a story, not a technical task — something demoable to a stakeholder

**INVEST**
- **I**ndependent — shippable without siblings in the same batch; hidden coupling is a finding
- **N**egotiable — intent, not an implementation spec in disguise
- **V**aluable — the so-that survives a stakeholder sniff test
- **E**stimable — enough info to size; unanswered design questions are findings
- **S**mall — fits a sprint; two capabilities in one story is a split candidate. A story that ships only one *layer* of a capability ("the API", "the screen") is not small, it is undemoable — verdict **Not a story**, fix is to merge it back
- **T**estable — every AC objectively verifiable

**Acceptance criteria quality**
- Given / When / Then; one behavior per scenario; no `And` chains hiding multiple behaviors
- Observable outcome in every Then — "user can do X" with no observable check is a finding
- Functional vs non-functional AC separated and both present where relevant (performance, a11y, audit)
- No AC that merely restates the story title

**Testability (what blocks `requirements-breakdown` downstream)**
- Validations state field, rule, **and** outcome on violation — a rule with no violation behavior is *silent*
- No unfalsifiable words ("fast", "user-friendly", "recently") without a number
- Contradictions between AC, or between story and linked epic, are flagged — never silently resolved
- Out-of-scope stated; absent means reviewers will assume everything is in scope

**Backlog hygiene (batch reviews only)**
- Duplicate or overlapping stories
- Dependency cycles or undeclared blocked-by links
- God stories (one story carrying a whole epic's outcome)
- Orphan stories with no epic / no measurable parent outcome; epics without a WHO / DO WHAT / SO THAT MEASURABLE one-liner
- Inconsistent slicing axis across one epic's children

## Severity mapping

Use the library's standard severities:

- **blocker** — story cannot proceed: no value statement, AC untestable as written, or contradiction with its epic/sibling that changes scope
- **major** — will hurt soon: missing/generic role, `And`-chained multi-behavior AC, undeclared dependency, silent validation (no on-violation behavior), split candidate
- **minor** — format or naming: AC not in Gherkin, missing out-of-scope section, vague title
- **nit** — optional preference

Calibrate to the stated purpose: for a *testability* review, silent validations and unfalsifiable AC escalate to **blocker** (they stall test design); for *sprint readiness*, sizing and dependency findings weigh heaviest.

## Output format

```markdown
# Backlog Review — <batch / source name>

**Source:** <where the stories came from>  **Purpose:** <sprint readiness / refinement intake / pre-test-design>
**Reviewed:** <YYYY-MM-DD>  **Stories reviewed:** <n>

## Verdicts
| Story | Verdict | Blocking findings |
|-------|---------------------------------------------|-------------------|
| US12 | ✅ Ready | — |
| US13 | 🛠 Needs work | 2 |
| US14 | ✂️ Split candidate | 1 |
| US15 | ❌ Not a story (technical task) | 1 |

## Findings
| Severity | Location | Issue | Suggested fix |
|----------|------------------|--------------------------------------------|--------------------------------------------|
| blocker  | US13 AC2 | "loads fast" — unfalsifiable | Quantify: e.g. p95 < 2s; owner to confirm |
| major    | US13 AC1 | `And` chain hides 3 behaviors | One Given/When/Then per behavior |
| major    | US14 | Two capabilities (export + schedule) in one story | Split by workflow step; same epic |

## Backlog-level findings *(batch reviews)*
| Severity | Scope | Issue | Suggested fix |
|----------|-------------|--------------------------------------|----------------------------|
| major    | E4 | Children mix two slicing axes | Re-slice by workflow steps |

## What blocks test design
<The findings that would stall `qa/manual/requirements-breakdown` — silent validations, contradictions, unfalsifiable AC — so QA knows exactly what to chase. "None" if clean.>

## Recommended next step
<one sentence: e.g. "Route US13/US14 to ba-story-writer for repair; US12 can proceed to requirements-breakdown now.">
```

Story and epic ids are quoted as the source backlog writes them; where the backlog has none, assign `US<n>`/`E<n>` in reading order and say so, so the findings are citable.

## Rules

- **Review-only.** Never rewrite a story during the review — point to the fix; `business-analysis/skills/ba-story-writer` applies it. (Library-wide review behavior.)
- Every finding cites its location (story ID + AC number) so the author can act without re-reading the review.
- Verdicts are per story; a batch never gets one blended verdict.
- Don't manufacture findings to look thorough — a clean story gets ✅ and zero rows.
- Don't re-litigate product decisions; review the story's *quality*, not whether the feature is a good idea (that was settled upstream in `ba-scoping-writeup`).

## Anti-patterns to flag in the backlog

- **Spec-as-story** — implementation steps pasted into AC; nothing negotiable left
- **AC by screenshot** — "works like the design" with no behavioral criteria
- **The eternal blocked story** — dependency named but no owner or date
- **Tracker archaeology** — stories whose AC contradict the current epic because they predate a pivot

## Handoffs

- Findings need applying → `business-analysis/skills/ba-story-writer` (story repair) or `business-analysis/skills/ba-epic-writer` (epic shape)
- Story is really an unscoped initiative → `business-analysis/skills/ba-scoping-writeup`
- Ready stories, QA next → `qa/manual/requirements-breakdown`, or `qa/manual/agents/qa-test-case-designer` for the full basis → suite flow
- Review uncovered a live defect reference → `qa/manual/bug-report-writer`

Only `qa/manual/requirements-breakdown` ships in this plugin; the other `qa/*` peers are invoked separately, never loaded here.
