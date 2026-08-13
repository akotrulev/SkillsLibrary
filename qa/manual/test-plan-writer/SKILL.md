---
name: qa-test-plan-writer
description: Use when the user asks for a feature or release test plan — the planning document that fixes scope (in/out/deferred), test approach per level, harness & tooling, environments & test data, artifacts, a scenario-level case inventory with reuse status, and entry/exit criteria. Triggers: "write a test plan for X", "plan the testing for this feature", "what do we need to test this". Do NOT use for the risk strategy alone (test-strategy), step-by-step cases (test-case-writer), or automation code.
---

# QA — Test Plan Writer

Assembles and formats a **feature-level test plan**: one document that says what will be tested and what won't, at which level, with which harness, by whom, producing which artifacts, and when testing is done. It is the planning layer between `test-strategy` (risk reasoning) and the executing skills/agents (cases, automation) — lean IEEE 829 / ISO 29119-3 shape, none of the ceremony.

This skill **owns the document**: its sections, tables, grammar, and quality bar. The *content* comes from elsewhere — the test basis from `requirements-breakdown` (or exploration), the risk register from `test-strategy`, technique choices from `test-design-techniques`, and the inventory of existing automation from reading the repo. The full feature→plan flow is orchestrated by the `qa/manual/agents/qa-test-planner` agent; load this skill to shape and quality-gate what that flow produced.

## When to use

- A feature (documented or not) needs a written plan before test effort starts
- The team asks "what is needed to test this" — harness, environments, data, people/agents, artifacts
- An existing plan must be revised after the spec, the harness, or the scope changed
- The QA section of an RFC / PR description needs a real plan, not a paragraph

## When NOT to use

- Risk register / pyramid sizing / release quality gates **alone** → `qa/manual/test-strategy` (this plan *embeds* its outputs)
- Step-by-step test cases → `qa/manual/test-case-writer` / the `qa-test-case-designer` agent (the plan's case inventory is scenario-level, deliberately without steps)
- An exploratory session brief → `qa/manual/exploratory-charter-writer`
- Automation code → the stack agents (`qa-api-<stack>`, `qa-ui-<stack>`, …)
- Measuring an existing process → `qa/manual/quality-metrics`

## Inputs needed

1. **Test basis** — a `requirements-breakdown` document, or an exploration/session report, or a stated description with its assumptions tagged
2. **Risk register + scope call** — from `test-strategy`
3. **Automation inventory** — what already exists in the repo: harness, API clients, page objects, suites, and which parts of the feature they already cover (with `file:line`)
4. **Constraints** — deadline, environments available, accounts/access, team/agent capacity

Missing input is not a blocker: write the section from what exists and put a `[TBD — reason]` plus an open question in its place. A plan with named unknowns beats no plan.

## The document

Saved to **`docs/test-plans/<NNN>-<feature-slug>-test-plan.md`** in the target project (`NNN` = next free number; never reuse). Target length **2–4 pages** — a plan nobody reads plans nothing.

```markdown
# Test Plan — <feature> (<NNN>)

## 1. Overview & references
<one paragraph: the feature, why it matters, the one-line risk headline>
| Basis | Source | Confidence |
|---|---|---|
| <doc / session report / code surface / stated description> | <path or link> | documented · #observed · #assumption |

## 2. Scope
**In scope** — | Item | Basis ref | Why it matters |
**Out of scope** — | Item | Reason | Revisit when |
**Deferred** — | Item | Reason | Target |

## 3. Risks driving the plan
<the top rows of the test-strategy risk register — ID, risk, L×I, mitigation. Reference, don't re-derive.>

## 4. Test approach — levels & types
| Level/type | Covers | Automated? | Harness (§5) | Executor |
<unit · integration · contract · API · UI/E2E · mobile · exploratory · performance · security · accessibility — only the rows this feature earns; a skipped standard level is an out-of-scope row with a reason>

## 5. Harness & tooling
| Level | Framework / runner | Where tests live | Status |
<Status is exactly one of **detected** (read from the repo, cite the path) · **stated** (the user said so) · **proposed** (your call — mark it, they approve it)>

## 6. Existing automation & reuse
| Seam | Path | State |
<API clients · DTOs · page/screen objects · BDD step catalog · builders/fixtures · CI lane · reporting — what exists and is reusable, what exists but is stale, what's absent>
Already covered: | Feature surface | Existing test | Evidence (file:line) |

## 7. Environments & test data
| Environment | Purpose | Access / accounts | External deps (mock · sandbox · live) |
Test data strategy: <builders/ObjectMother · seeding · anonymized copy — and who provides what>

## 8. Artifacts
| Artifact | Produced by | Location |
<test-basis doc · case suites · feature files · POMs/clients built · bug reports · Allure/report output · coverage matrix — each with an owner and a path>

## 9. Case inventory
| ID | Case (behavior, not steps) | Level | Technique | Priority | Coverage | Executor | Traces to |
<ID = TP-###. Coverage is exactly one of **existing** (already automated — cite file:line in §6) · **extend** (seam exists, scenario missing) · **new** (seam must be built first). Executor is an exact library agent/skill name.>

## 10. Entry & exit criteria
Entry: <what must be true to start — env up, basis confirmed, accounts issued>
Exit: <numbers, not adjectives — every P1 case executed/passing, no open blocker/major, gates green>

## 11. Assumptions & open questions
<every #assumption and [TBD] from above, one row each, with who can answer it>
```

## Section rules

- **Scope is closed.** Every testable item from the basis appears in exactly one of in / out / deferred. Out-of-scope without a reason is not out of scope — it's forgotten.
- **The harness is looked up before it is invented.** `detected` rows cite the repo path; `proposed` rows exist only where nothing was detected and name what the stack defaults would choose. Never propose a second harness beside a working detected one.
- **Reuse before build.** A case is `new` only after §6 shows no seam for it; a plan whose inventory is all-`new` against a repo with existing suites is wrong, not thorough.
- **Cases are scenario-level.** One row per behavior — title, level, technique, priority, coverage status, executor, trace. **No steps, no test data values**; that is `test-case-writer` / the stack agents' work, and duplicating it here guarantees drift.
- **Executors are picked, not invented.** Every case row and artifact row names an exact agent/skill (`qa-api-<stack>`, `qa-ui-<stack>`, `qa-test-case-designer`, `qa-security`, …). A name that doesn't resolve to the library is a defect.
- **Every case traces** — to a basis line, a risk ID, or an `#observed`/`#assumption` tag. An untraceable case is a guess wearing an ID.
- **Exit criteria are checkable.** "Every P1 case executed, 0 open blockers, contract suite green in CI" — never "sufficient confidence".
- **Unknowns are first-class.** `[TBD — reason]` in place, and a row in §11 with an owner. A silent gap is worse than a named one.

## What NOT to do

- No steps or concrete data in the case inventory — that's the suite's job, not the plan's
- No re-deriving the risk register — embed `test-strategy`'s output and reference its IDs
- No "regression testing" as a phase — regression coverage is a property of the suites the plan names
- No plan that ignores existing automation — §6 is mandatory even when it says "none found (searched: <globs>)"
- No unowned artifacts — every §8 row has a producer
- No 12-page plan — if a section outgrows the document, it's a separate artifact the plan links to

## Generation steps

1. Collect the four inputs; for each missing one, write the `[TBD]` + open question instead of stalling
2. Close the scope: every basis item into in / out / deferred with reasons
3. Fill §4–§6 from the automation inventory — detected first, proposed only for gaps
4. Build the case inventory: conditions × techniques → scenario rows; stamp coverage status from §6; assign executors
5. Write entry/exit criteria as checks; collect every assumption and TBD into §11
6. Self-review against the Section rules; save to `docs/test-plans/`

## Handoffs

- Risk register & gates depth → `qa/manual/test-strategy`
- Basis document → `qa/manual/requirements-breakdown`
- Technique selection depth → `qa/manual/test-design-techniques`
- Step-by-step suite from the inventory → `qa/manual/test-case-writer` / the `qa-test-case-designer` agent
- Automation of `extend`/`new` rows → `qa-api-<stack>` · `qa-ui-<stack>` · `qa-mobile-<stack>` · `qa-performance-<stack>` · `qa-llm-<stack>` · `qa-bdd-<stack>`
- Security rows → the `qa-security` agent
- CI & reporting artifacts → `qa-cicd-<stack>` · `qa-reporting-<stack>`
- Exploratory rows → `qa/manual/exploratory-charter-writer`
