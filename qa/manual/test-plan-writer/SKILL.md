---
name: test-plan-writer
description: Use when writing a test plan for an epic, a feature or a release; versions, what is tested, approach, harness, scenarios, Definition of Ready and Done. Triggers "write a test plan for X". Not for risk strategy alone (test-strategy).
---

# QA — Test Plan Writer

Assembles and formats a **test plan**: one document that says which versions are under test, what will be tested and what won't, at which level, with which harness, in which scenarios, by whom, producing which artifacts, when testing may start (Definition of Ready) and when it is done (Definition of Done). Its unit is whatever it is handed: **an epic and its stories** (the default after `/dev:refine`), one feature, or a release. It is the planning layer between `test-strategy` (risk reasoning) and the executing skills/agents (cases, automation) — lean IEEE 829 / ISO 29119-3 shape, none of the ceremony.

This skill **owns the document**: its sections, tables, grammar, and quality bar. The *content* comes from elsewhere — the test basis from `requirements-breakdown` (or exploration), the risk register from `test-strategy`, technique choices from `test-design-techniques`, and the inventory of existing automation from reading the repo. The full feature→plan flow is orchestrated by the `qa/manual/agents/qa-test-planner` agent; load this skill to shape and quality-gate what that flow produced.

## When to use

- A feature (documented or not) needs a written plan before test effort starts
- The team asks "what is needed to test this" — harness, environments, data, people/agents, artifacts
- An existing plan must be revised after the spec, the harness, or the scope changed
- The QA section of an RFC / PR description needs a real plan, not a paragraph

## When NOT to use

- Risk register / pyramid sizing / release quality gates **alone** → `qa/manual/test-strategy` (this plan *embeds* its outputs)
- Step-by-step test cases → `qa/manual/test-case-writer` / the `qa-test-case-designer` agent (the plan's case inventory is scenario-level, deliberately without steps)
- An exploratory session brief → `qa/manual/exploratory-charter-writer`; exploring the running app → the `qa-explorer` agent
- Automation code → the stack agents (`qa-api-<stack>`, `qa-ui-<stack>`, …)
- Measuring an existing process → `qa/manual/quality-metrics`

## Inputs needed

1. **Test basis** — an epic and its stories (`epics.md` + `stories.md` in `docs/plans/<NNN>-<initiative>/`) distilled by `requirements-breakdown`, or a `requirements-breakdown` document from any other source, or an exploration/session report, or a stated description with its assumptions tagged
2. **Risk register + scope call** — from `test-strategy`
3. **Automation inventory** — what already exists in the repo: harness, API clients, page objects, suites, and which parts of the feature they already cover (with `file:line`)
4. **Versions** — the build or release under test, and the browsers, operating systems, devices and API versions it must work on
5. **Constraints** — deadline, environments available, accounts/access, team/agent capacity

Missing input is not a blocker: write the section from what exists and put a `[TBD — reason]` plus an open question in its place. A plan with named unknowns beats no plan.

## The document

Saved to **`docs/test-plans/<NNN>-<feature-slug>-test-plan.md`** in the target project (`NNN` = next free number; never reuse). Target length **2–4 pages** — a plan nobody reads plans nothing.

```markdown
# Test Plan — <epic or feature> (<NNN>)

**Covers:** <E2 Booking — US6 Booking a place, US7 The waiting list | the feature | the release>
**Plan version:** <1 · YYYY-MM-DD> <on a revision: 2 · YYYY-MM-DD · what changed>

## 1. Overview & references
<one paragraph: what is being tested, why it matters, the one-line risk headline>
| Basis | Source | Confidence |
|---|---|---|
| <epics.md E2 · stories.md US6–US7 · doc / session report / code surface / stated description> | <path or link> | documented · #observed · #assumption |

## 2. Versions
**Under test** — | Item | Version | Source |
<the application build or release · each service and its API / contract version · the database schema or migration level · the basis itself (stories.md at commit or date)>
**Tested on** — | Platform | Versions | Why these |
<browsers · operating systems · devices and screen sizes · locales — the matrix the product supports, narrowed with a reason>
**Tested with** — | Tool | Version | Source |
<test runner and libraries, read from the repo's manifest>
<Source is exactly one of **detected** (cite the file) · **stated** · `[TBD — who knows]`. A version is never guessed.>

## 3. Scope — what is to be tested
**In scope** — | Item | Basis ref | Why it matters |
<from stories: one row per included part, its ref the story and its criteria — `US6 · Book a class with room · AC1–AC4`>
**Out of scope** — | Item | Reason | Revisit when |
**Deferred** — | Item | Reason | Target |

## 4. Risks driving the plan
<the top rows of the test-strategy risk register — ID, risk, L×I, mitigation. Reference, don't re-derive.>

## 5. Test approach — levels & types
| Level/type | Covers | Automated? | Harness (§6) | Executor |
<unit · integration · contract · API · UI/E2E · mobile · exploratory · performance · security · accessibility — only the rows this feature earns; a skipped standard level is an out-of-scope row with a reason>

## 6. Harness & tooling
| Level | Framework / runner | Where tests live | Status |
<Status is exactly one of **detected** (read from the repo, cite the path) · **stated** (the user said so) · **proposed** (your call — mark it, they approve it)>

## 7. Existing automation & reuse
| Seam | Path | State |
<API clients · DTOs · page/screen objects · BDD step catalog · builders/fixtures · CI lane · reporting — what exists and is reusable, what exists but is stale, what's absent>
Already covered: | Feature surface | Existing test | Evidence (file:line) |

## 8. Environments & test data
| Environment | Purpose | Access / accounts | External deps (mock · sandbox · live) |
Test data strategy: <builders/ObjectMother · seeding · anonymized copy — and who provides what>

## 9. Artifacts
| Artifact | Produced by | Location |
<test-basis doc · case suites · feature files · POMs/clients built · bug reports · Allure/report output · coverage matrix — each with an owner and a path>

## 10. Scenarios (the case inventory)
| ID | Scenario (behavior, not steps) | Layer | Level | Technique | Priority | Coverage | Executor | Traces to |
<Layer is one of journey · rule · state · data · interaction · temporal · concurrency · field. Journey rows come first.>
<ID = TP-###. Coverage is exactly one of **existing** (already automated — cite file:line in §7) · **extend** (seam exists, scenario missing) · **new** (seam must be built first). Executor is an exact library agent/skill name. Traces to a story criterion (`US6 AC3`), a basis line or a risk id.>

## 11. Definition of Ready and Definition of Done
**Ready — testing may start when**
- [ ] <every in-scope story is ready: no `[TBD]` in its criteria, no open blocker from `business-analysis:story-review`>
- [ ] <the build in §2 is deployed to the §8 environment>
- [ ] <accounts, test data and external sandboxes in §8 are issued and reachable>
- [ ] <the harness in §6 runs green on the default branch>

**Done — testing is finished when**
- [ ] <every P1 scenario executed and passing on every platform in §2>
- [ ] <every acceptance criterion of every in-scope story has at least one passing case>
- [ ] <0 open blocker or major defects; each minor accepted by name>
- [ ] <the `extend` and `new` P1 scenarios are automated and green in CI>
- [ ] <results reported (§9) and every open question in §12 answered or accepted by the decision-maker>

## 12. Assumptions & open questions
<every #assumption and [TBD] from above, one row each, with who can answer it>
```

## Section rules

- **Versions are looked up or stated, never guessed.** The build under test is named exactly (a version, a tag or a commit), so a result can be tied to what was tested; a platform row says why it is in the matrix. A plan revised for a new build bumps its plan version and says what changed.
- **Scope is closed.** Every testable item from the basis appears in exactly one of in / out / deferred. Out-of-scope without a reason is not out of scope — it's forgotten. From stories, the items are the stories' included parts: every part of every covered story lands in one of the three.
- **The harness is looked up before it is invented.** `detected` rows cite the repo path; `proposed` rows exist only where nothing was detected and name what the stack defaults would choose. Never propose a second harness beside a working detected one.
- **Reuse before build.** A case is `new` only after §7 shows no seam for it; a plan whose inventory is all-`new` against a repo with existing suites is wrong, not thorough.
- **The inventory is business first.** Every actor goal in the basis has a journey row, end to end, to the business outcome; every rule and every calculated figure has a row; rows are listed journeys, then rules and calculations, then states and connections, then fields, which are at most a third of the inventory. An inventory of field checks around one happy path plans the wrong work.
- **Cases are scenario-level.** One row per behavior — title, level, technique, priority, coverage status, executor, trace. **No steps, no test data values**; that is `test-case-writer` / the stack agents' work, and duplicating it here guarantees drift.
- **Executors are picked, not invented.** Every case row and artifact row names an exact agent/skill (`qa-api-<stack>`, `qa-ui-<stack>`, `qa-test-case-designer`, `qa-security`, …). A name that doesn't resolve to the library is a defect.
- **Every scenario traces** — to a story criterion (`US6 AC3`), a basis line, a risk ID, or an `#observed`/`#assumption` tag. An untraceable scenario is a guess wearing an ID. From stories, every acceptance criterion has at least one scenario, or a row in out of scope saying why not.
- **Ready and Done are checklists of facts.** Each line is something a person can tick by looking: "every P1 scenario executed and passing, 0 open blockers, contract suite green in CI" — never "sufficient confidence". Ready is what must be true before the first test runs; Done is what must be true before testing is called finished. A line nobody can check is deleted or given its number.
- **Unknowns are first-class.** `[TBD — reason]` in place, and a row in §12 with an owner. A silent gap is worse than a named one.

## What NOT to do

- No steps or concrete data in the case inventory — that's the suite's job, not the plan's
- No re-deriving the risk register — embed `test-strategy`'s output and reference its IDs
- No "regression testing" as a step — regression coverage is a property of the suites the plan names
- No plan that ignores existing automation — §7 is mandatory even when it says "none found (searched: <globs>)"
- No unowned artifacts — every §9 row has a producer
- No 12-page plan — if a section outgrows the document, it's a separate artifact the plan links to

## Generation steps

1. Collect the five inputs; for each missing one, write the `[TBD]` + open question instead of stalling
2. Fill §2: the build under test, the platform matrix, the tool versions read from the repo
3. Close the scope: every basis item (every included part of every covered story) into in / out / deferred with reasons
4. Fill §5–§7 from the automation inventory — detected first, proposed only for gaps
5. Build the scenarios: conditions × techniques → scenario rows; stamp coverage status from §7; assign executors
6. Write the Definition of Ready and the Definition of Done as checklists; collect every assumption and TBD into §12
7. Self-review against the Section rules; save to `docs/test-plans/`

## Handoffs

- Risk register & gates depth → `qa/manual/test-strategy`
- Epics and stories the plan covers → the `requirements-author` agent (`/dev:refine`); a story not ready to test from → `business-analysis:story-review`
- Basis document → `qa/manual/requirements-breakdown`
- Technique selection depth → `qa/manual/test-design-techniques`
- Step-by-step suites from the scenarios, one per story → `qa/manual/test-case-writer` / the `qa-test-case-designer` agent (`/qa-<stack>:test-cases`)
- Automation of `extend`/`new` rows → `qa-api-<stack>` · `qa-ui-<stack>` · `qa-mobile-<stack>` · `qa-performance-<stack>` · `qa-llm-<stack>` · `qa-bdd-<stack>`
- Security rows → the `qa-security` agent
- CI & reporting artifacts → `qa-cicd-<stack>` · `qa-reporting-<stack>`
- Exploratory rows → the `qa-explorer` agent (an agent explores the running build) or `qa/manual/exploratory-charter-writer` (a charter for a human's session)
