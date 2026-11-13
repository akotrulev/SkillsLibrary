---
name: story-review
description: Use when reviewing stories or epics someone else wrote for readiness (one whole feature, clear goal and plan, met-or-not AC, testability). Triggers "review these stories". Not for writing stories (stories).
---

# Backlog Reviewer

Review-only intake audit for stories and epics **authored elsewhere**. Produces a per-story readiness verdict (Definition-of-Ready gate) plus a findings table in the library's standard severity format. Does **not** rewrite anything — it points to the fix and names the skill that applies it.

The chain assumption "we write the stories" often doesn't hold: backlogs arrive from clients, other teams, or an existing tracker. This skill is the entry point for that case, sitting in front of refinement and of the QA pipeline (`qa/manual/requirements-breakdown` consumes only stories that pass here, or proceeds with the gaps explicitly flagged).

## When to use

- Stories/epics arrive from outside the team and must be assessed before anyone commits to them
- A planning or refinement session needs a Definition-of-Ready check on candidate stories
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
2. **Purpose of the review** — build readiness, refinement intake, or pre-test-design testability (changes which severities block)
3. **The team's Definition of Ready**, if non-standard (otherwise the checklist below is the DoR)

## Review checklist

Apply per story; each failed check becomes one finding row with a severity. The per-story checks (one whole feature with one goal, a plan and not a design, every included part proven, met-or-not acceptance criteria, testability, no technology) are the business-analysis rule files `backlog-stories.md`, and `backlog-epics.md` for epics, not a list here:

1. **The project's copies first**: `.claude/rules/business-analysis/`. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `business-analysis/skills/rules/`. Say in the report that the project has no installed rules and that `/business-analysis:rules` installs them.

Read them in full before the first finding; never review from memory of the rules, and never add a check the files do not contain (propose it as a rule change instead). For a backlog from outside `docs/plans/` (a tracker export, a client document), skip the id, heading, section-order and `Source` rules and judge the content: an "As a / I want / so that" line is read as the goal and Given / When / Then scenarios as the acceptance criteria, each held to the same met-or-not bar. A layer-only story gets the verdict **Not a story**; a fragment of a feature (login with no way to register) gets **Merge candidate**.

**Backlog hygiene (batch reviews only)**
- Duplicate or overlapping stories
- Dependency cycles or undeclared blocked-by links
- Fragment stories (one feature spread over several stories, none usable alone) and catch-all stories (two unrelated features under one title)
- Orphan stories with no epic / no measurable parent outcome; epics without a WHO / DO WHAT / SO THAT MEASURABLE one-liner
- Stories of one epic cut along two different axes

## Severity mapping

Use the library's standard severities:

- **blocker** — story cannot proceed: no goal, AC untestable as written, an invented number, or contradiction with its epic/sibling that changes scope
- **major** — will hurt soon: generic person, a plan that only restates the goal, an included part with no AC, an AC walking through several situations, undeclared dependency, silent validation (no on-violation behavior), split or merge candidate
- **minor** — format or naming: sections missing or out of order, AC unnumbered, no `Not included` list, vague title
- **nit** — optional preference

Calibrate to the stated purpose: for a *testability* review, silent validations and unfalsifiable AC escalate to **blocker** (they stall test design); for *build readiness*, wholeness and dependency findings weigh heaviest.

## Output format

```markdown
# Backlog Review — <batch / source name>

**Source:** <where the stories came from>  **Purpose:** <build readiness / refinement intake / pre-test-design>
**Reviewed:** <YYYY-MM-DD>  **Stories reviewed:** <n>

## Verdicts
| Story | Verdict | Blocking findings |
|-------|---------------------------------------------|-------------------|
| US12 | ✅ Ready | — |
| US13 | 🛠 Needs work | 2 |
| US14 | ✂️ Split candidate | 1 |
| US15 | ❌ Not a story (technical task) | 1 |
| US16 | 🧩 Merge candidate (fragment of US13) | 1 |

## Findings
| Severity | Location | Issue | Suggested fix |
|----------|------------------|--------------------------------------------|--------------------------------------------|
| blocker  | US13 AC2 | "loads fast" — unfalsifiable | Quantify: e.g. p95 < 2s; owner to confirm |
| major    | US13 AC1 | Walks through 3 situations in one criterion | One criterion per situation, each with its outcome |
| major    | US13 | "Reset password" is included but no AC proves it | Add criteria for it working and for the expired link |
| major    | US14 | Two goals (export + schedule) in one story | Split into two stories; same epic |
| major    | US16 | Login alone; no use without registration in US13 | Merge into US13 as an included part |

## Backlog-level findings *(batch reviews)*
| Severity | Scope | Issue | Suggested fix |
|----------|-------------|--------------------------------------|----------------------------|
| major    | E4 | Its stories are cut along two axes | Re-cut by workflow steps |

## What blocks test design
<The findings that would stall `qa/manual/requirements-breakdown` — silent validations, contradictions, unfalsifiable AC — so QA knows exactly what to chase. "None" if clean.>

## Recommended next step
<one sentence: e.g. "Route US13/US14 to business-analysis:stories for repair; US12 can proceed to requirements-breakdown now.">
```

Story and epic ids are quoted as the source backlog writes them; where the backlog has none, assign `US<n>`/`E<n>` in reading order and say so, so the findings are citable.

## Rules

- **Review-only.** Never rewrite a story during the review — point to the fix; `business-analysis/skills/ba-story-writer` applies it. (Library-wide review behavior.)
- Every finding cites its location (story ID + AC number) so the author can act without re-reading the review.
- Verdicts are per story; a batch never gets one blended verdict.
- Don't manufacture findings to look thorough — a clean story gets ✅ and zero rows.
- Don't re-litigate product decisions; review the story's *quality*, not whether the feature is a good idea (that was settled upstream in `business-analysis:scoping`).

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
