# 015 — Skill-authoring remediation, from audit 004 — plan (2026-11-20)

**Goal:** Clear every finding of `docs/audits/004-skill-authoring-r1.md` (528 findings, 249 major)
against the house authoring standard (`engineering-practices/writing-for-agents/SKILL.md`, R1–R23).
The owner settles the 24 logical conflicts in one round of questions first. One task then fixes the
shared shapes: the agent template, the standard itself and the 23 `rules` skills. Twenty per-plugin
tasks fix their own files, and a gate task runs the lint, the size audit and the surface check over the
whole library.

**Status:** Written by 014 A5 on 2026-11-20. No task has run yet. Next: L1, the owner's answers to O1–O24.
Then T1, then P1–P20 (any three at a time), then G1. **Unverified:** the audit's line numbers. About
two thirds of A3's judgment rows and most of A4's Code rows were never re-read at their lines, so every
task re-reads its rows first (§2, D6). **Metered:** about 23 sessions of subscription usage. The user
starts the queue.

**Test design:** none. The plan serves no stories, and it changes skill text only. The check is
`tools/skill-lint.py`, `tools/token-audit.py` and `tools/plugin-surface-check.py`, which already exist.
**Documentation task:** none. This is the skills library, and the skill text the tasks edit is itself
the documentation. Two documents change only if registration changes: the catalog
(`docs/skills-catalog.md`) and `README.md`. That happens only under O10 (a), and then P20 updates
their rows in the same task. No product behaviour changes for a `be-documenter` to trace.
**Telemetry smoke:** none. No service is built.

---

## 1. What already exists, and what is missing

Counts and locations are the audit's (`docs/audits/004-skill-authoring-r1.md`, cited as "004"), checked
again on 2026-11-20 with `python3 tools/skill-lint.py --json` (238 findings, exit 1) and
`python3 tools/token-audit.py --violations-only` (89 violations, exit 1).

| Need | Today | Gap |
|---|---|---|
| Size budgets (R2): skill description ≤ 200, body ≤ 16,000, agent file ≤ 14,000 | 89 violations. 22 descriptions are over: 19 of them `rules` (209–222), plus `security/metasploit-setup` 452, `experience-plan` 246 and `test-plan-writer` 232. 63 bodies are over, from `delivery-plan` 73,093 down to `auth0-blazor` 16,035. 4 agent files are over: `be-documenter` 17,599, `solution-planner` 16,835, `qa-test-case-designer` 16,323, `qa-test-planner` 14,847. | Every one is under budget, reached by R16 and R17 moves and never by cutting a rule only that body states (D3). T1 takes the descriptions. Each body and agent goes to the P task of its plugin. |
| Long reference files open with a contents list (R9) | 89 files over 300 lines have none: 76 in the `qa-*` lanes, 9 in `qa/cicd`, and the rest in `backend/_shared`, `frontend/react`, `mobile/*`, `desktop/*`, `security/standards-audit` and plan-format (004 Appendix "R9") | One contents list per file, by plugin (D7) |
| Front-door shape (R7, R3, R6) | 64 R7 findings: the 23 `rules` skills, `python-web-testing`, four `dev` front doors, and five unregistered skills read as front doors. 31 R3 findings in 20 files, mostly the missing `Not for` clause. 5 R6 findings in 4 hidden skills (004 Appendix). | T1 takes the `rules` skills. The P tasks take the rest. Unregistered skills gain `disable-model-invocation: true` (D5). |
| Pointers resolve (R8) | 22 dangling pointers (004 "Data issues", lint rows) | Each pointer names its owner by path (P2, P4, P5, P19) |
| No placeholders, no hidden-skill invocation, agent shape (R10, R12, R13) | 11 R10, 2 R12 and 6 R13 findings (004 "Code issues", lint major rows) | Fixed in the owning P task |
| Always-loaded rule files are small (R23) | 4 core files over 6,000 and 17 others over 2,500 (004, size rows) | Trimmed to constraints, with the recipe pointed at (P1, P4, P8, P14, P17, P18, P20) |
| One meaning, one place (R17) | 45 judgment rows. Every one of the 14 sampled skills has one. 20 of the 24 front-door agents cache their rule-file listing (004 "Summary"). | Restatements become pointers, by path (all P tasks) |
| Checkable done-when (R15) | 24 rows: generation steps that end on an activity, Done-when cells that name no artifact, and the template's open-ended Fix sweep (`.skill-template/agent.md:33`), which 47 agents carry | T1 fixes the template line. Each P task fixes its agents' line and its steps. |
| R16, R18, R19, R20, R21 | 17, 12, 28, plus rows of R20 and R21 (004 judgment tables) | Fixed with the skill they name |
| Stale facts (Data issues) | 12 judgment rows (004 "Data issues", "Data issues (A4)") | Fixed with the skill they name |
| Logical conflicts | 30 rows: A3 has 7 judgment and 8 R11 rows, A4 has 15. Each is two texts that cannot both hold. | Asked once, as O1–O24 (L1). The owning task applies the answer (D1). |
| The coverage-in-a-task line (A4 left it unverified) | Checked on 2026-11-20 with `grep -n "own tests"`. Not only `mobile/android/skills/unit-testing/SKILL.md:180, 219` carries it. So do `backend/{dotnet:221, java:244, node:264, python:153, 165, rust:188}/skills/unit-testing/SKILL.md`, `mobile/ios/skills/unit-testing/SKILL.md:162, 183`, `mobile/react-native/skills/component-testing/SKILL.md:169, 188`, `frontend/blazor/skills/component-testing/SKILL.md:116, 127`, `frontend/react/skills/component-testing/SKILL.md:152, 161` and possibly `desktop/windows/skills/unit-testing/SKILL.md:185`. `desktop/macos/skills/unit-testing` does not. | Part of O12, applied by P5–P9 |

## 2. How a finding is fixed

Every P task and T1 follows this method. The prompts cite it as "§2".

1. **Re-read each row at its line first** (D6). The audit's lines are mostly unverified, so look at the
   line before you edit it. A row that is wrong at its line is dropped, and the task's `As built` names it
   with the reason. A row whose line moved is fixed where the text now is.
2. **The fix is the row's `Suggested fix`** in 004, found by grepping the report for the path. The fix
   changes only when the row's own text shows it is wrong, and then the task records a `D<n>`.
3. **R2 (size)** is met by moving and deleting, in this order:
   - delete restatements of a rule file or `CLAUDE.md` and point at the rule instead (R17);
   - delete no-op sentences (R19) and closing `## Rules` or `## What NOT to do` lists that repeat the body;
   - move material that only some branches reach into `references/<topic>.md`, behind a pointer that
     names the condition: "a re-audit with a prior report → read `references/re-audit.md`" (R16).
   
   A rule that only this body states stays. Done when `token-audit` no longer lists the file.
4. **R17 pointers** name the rule by file and heading or line, for example "per `android-tests.md`" or
   "`CLAUDE.md` 'Test code rules'". The pointer text never re-lists the rule. A fact one command away,
   such as a folder listing, a pinned version or a count, is replaced by the command or the owning
   file.
5. **R9:** directly after the H1 (or after the frontmatter where there is no H1), write
   `**Contents:**` and then one bullet per `##` heading, in order, using the heading text. A throwaway
   script in `/tmp` may generate the lists (D7). Read each file's list once before you keep it.
6. **R7** for a front door: add `## When to use` and `## When NOT to use`, each one to three lines, and
   name the sibling front door in the second one. **R3**: the description reads `Use when …`, then
   `Triggers "…"`, and ends with `Not for <case> (<sibling>).`.
7. **R15:** each step ends on a state someone else can check, such as "every X has Y" or "the table
   lists …". Never end a step on an activity.
8. **An O row** (§5) is applied only as `## Answered questions` records it. While an O is **deferred**,
   its lines stay as they are, and the task names them in `As built` as held.
9. **Stay inside your paths.** A defect you find outside the files your task names goes into `As built`
   for G1, and you do not edit it. A rule file's `paths:` frontmatter is never changed.
10. **Gate.** `python3 tools/skill-lint.py <your paths>` prints `0 findings`. The only lines it may still
    print are those of a deferred O, and each of those is named in `As built`. Where your task has R2
    rows, `python3 tools/token-audit.py --violations-only | grep -E '<your pattern>'` prints nothing.
    `python3 tools/plugin-surface-check.py` prints `OK`. A qa task also runs
    `python3 tools/qa-version-check.py` and gets `OK`.

## 3. How the work is split

- **L1 comes first.** It asks the owner O1–O24 in one message and records the answers (D1).
- **T1 comes second.** It fixes the shared shapes that the per-plugin tasks copy:
  - `.skill-template/agent.md`: the Fix sweep (R15) and, under O18, the `Gate evidence` line;
  - the standard's own R8 and R20 rows (O1, O5);
  - the 23 `rules` skills, one shape fixed once across every plugin (D2).
- **P1–P20 follow, one cluster of plugins each.** A cluster is merged with its neighbour while the session
  stays under about 150k. Mechanical rows (R3, R6, R7, R8, R9, R10, R12, R13) are batched by rule within
  the task, and judgment rows go with the skill they name. The files are disjoint, so any three P tasks
  run side by side. Each one depends on L1 and T1, and on nothing else.
- **G1 comes last.** It runs the whole sweep over the library, fixes what is left, and files the plan.
- **T2 exists only if an answer changes the lint.** That is O1 (b), O3 (b) or O4 (b). L1 then writes T2
  (stack `infra`), placed after T1, together with its prompt.

Every task's stack is `docs` (T2's is `infra`), and its agent is `general-purpose`: skill text is the
library's own source, and no catalog agent owns it.

## 4. What G1 sweeps

```bash
python3 tools/skill-lint.py                       # 0 findings, or only a deferred O's lines, each named in Status
python3 tools/token-audit.py --violations-only    # exit 0: no violations
python3 tools/plugin-surface-check.py             # OK
python3 tools/qa-version-check.py                 # OK
python3 -m pytest tools/test_skill_lint.py -q     # green (T2 may have changed the lint)
git diff --name-only "$(git log --diff-filter=A --format=%h -1 -- docs/plans/015-skill-authoring-remediation.md)" HEAD
```

The last command lists every file the plan touched. G1 then reads each new `references/*.md` file
and each pointer that the tasks added beside a moved section, to catch what the lint cannot see: a
pointer to a heading that does not exist, and a "per `<rule file>`" that names the wrong file. **What a
halfway stop leaves:** each landed task's lint, size and surface checks green over its own paths. The
library-wide sweep has not run until G1.

## 5. Open questions

All 30 logical-conflict rows of 004 are here: A3's 7 judgment rows, A3's 8 R11 rows (folded into O3
and O4) and A4's 15. Each one needs an owner's choice, not a fix. L1 asks them all at once. Reading (a)
is the audit's suggested fix and the recommended one.

| # | Question | Options | Blocks | Owner |
|---|---|---|---|---|
| O1 | R8 in the standard says a pointer resolves "relative to that file's folder". D16 made the lint also resolve inside a skill named in a code span on the same line or the line above, and agents' Load cells rely on that (`writing-for-agents/SKILL.md:102` vs `tools/skill-lint.py`). | (a) Reword R8 to the lint's reading. (b) Keep R8 strict: revert D16 (b) in the lint, and rewrite every Load-cell pointer as a full path (about 136 sites). | T1; under (b), a new T2 and every P task with agents | the user |
| O2 | `writing-plans/SKILL.md:156–158` lists 8 stacks with no `mobile` or `desktop`, and `:311` says "exactly one of the eight". Plan-format §4 (`plan-format.md:122`) has ten. `delivery-plan/SKILL.md:687` says "eight values" against its own list of ten at `:120`. | (a) Point at plan-format §4 as the one list and drop every count. (b) Keep local lists, made complete, with the count "ten". | P1, P3 | the user |
| O3 | R11 flags *slice* used as the knowledge base's cross-section term, not as a unit of work: `ba-project-memory/SKILL.md:116`, `cross-feature-test-design/SKILL.md:28, 30`, `cross-feature-test-design/references/example-cancel-booking.md:9, 76, 103`, `requirements-breakdown/references/connections.md:9` | (a) Rename it to the house word *cross-section* in those headings and table headers. (b) Make an R11 exception for the KB term, in the standard and in the lint. | P19, P20; under (b), T1 and a new T2 | the user |
| O4 | R11 flags *Phase* used as the expand/contract migration term: `data/_shared/migrations/SKILL.md:63`. | (a) Change the table header to "Step". (b) Make an R11 exception for the migration term, in the standard and in the lint. | P10; under (b), T1 and a new T2 | the user |
| O5 | The standard's R20 row (`writing-for-agents/SKILL.md:114`) lists five house words. "Leading words" (`:73`) lists six, adding *done when*. | (a) Keep the list once, at `:73`, and have the R20 row point at it. (b) Keep the list in the R20 row, and have `:73` point at it. | T1 | the user |
| O6 | `quality-constraints/SKILL.md:32` puts a test believed wrong under "a dated decision in the plan". `:39` puts it in "the plan's open issues". | (a) Both rows say "a dated `D<n>` in the plan's open issues and the final message". (b) Both rows say "a dated `D<n>` under the plan's `## Decisions`". | P1 | the user |
| O7 | `qa/dotnet/skills/inhouse-framework-conventions/SKILL.md:150` asserts `Expect(Page).ToHaveURLAsync(…)` in a test body. `:170–172` of the same file says tests never call a Page method, and `qa/java/…/SKILL.md:283` lists `assertThat(page).hasURL(…)` as an anti-example. | (a) Assert the URL through a page-object member. (b) State the URL assertion as the sanctioned exception, in all three lanes. | P17; under (b), also P14 and P18 | the user |
| O8 | `qa/typescript/skills/inhouse-framework-conventions/SKILL.md:134` writes the rule as `this.selector("key")`, but the example and `PageBase` at `:100–110` use `this.locator(…)`. | (a) The rule says `this.locator("key")`. (b) The example and `PageBase` change to `this.selector`. | P18 | the user |
| O9 | `qa/typescript/…/inhouse-framework-conventions/SKILL.md:208` wraps page methods in `test.step(…)`, but the `LoginPage` example at `:109–114` does not. Java and .NET carry `@Step` and `[AllureStep]`. | (a) Add `test.step` to the example. (b) Drop the rule from the TypeScript lane. | P18 | the user |
| O10 | `/dev:refine` runs `business-analysis/agents/requirements-author.md` from `dev`, which declares no dependencies (`.claude-plugin/marketplace.json`). Its steps (`:44, 56, 66–69`) load `business-analysis/skills/ba-*`, `qa/manual/requirements-breakdown` and `.claude/rules/business-analysis/`, and none of them exist in a `dev`-only install. | (a) Register the agent and `refine` in `business-analysis` (which depends on `dev`), giving `/business-analysis:refine`, and update the catalog and README rows. (b) Bundle what it loads into `dev`. | P20 | the user |
| O11 | `design/visual-identity/SKILL.md:79, 88, 108` calibrates **six** default looks, and checklist item 3 tests "the six". `:73` and the agents' Done-when cells (`fe-blazor:34`, `fe-react:19, 36`, `mobile-react-native:35`, `mobile-ios:30`) critique against "the three AI-default looks". | (a) Use one count, by pointer: "the default looks in `visual-identity` Calibration", everywhere. (b) Calibration names three looks, and the checklist tests three. | P5, P6, P7 | the user |
| O12 | `mobile/android/skills/unit-testing/SKILL.md:180, 219, 223` and the siblings listed in §1 say "a plan task's `Gate: own tests` runs this [coverage measure]". Plan-format (`plan-format.md:204, 276`) and `CLAUDE.md` "Planning" say no task but the gate runs it. | (a) Every sibling says: "Inside a plan task, write a test per branch; the floor is measured in the gate task. Outside a plan, run it before you report." (b) Plan-format §5 and `CLAUDE.md` "Planning" change to let a task measure its own files. | P5, P6, P7, P8, P9; under (b), P1 instead | the user |
| O13 | The kube-bench benchmark ids disagree: `devops/k8s-security/SKILL.md:133` has `gke-1.2.0`, `:462` has `aks-1.0`, and `devops/k8s-security/references/kube-bench.md:21–22` has `aks-1.7` and `gke-1.6.0`. | (a) The ids live only in `references/kube-bench.md`, checked against kube-bench's current release (`dev:source-grounding`), and the skill points at it. (b) The ids stay inline in the skill, and both files are corrected to the current release. | P11 | the user |
| O14 | `frontend/react/skills/error-handling/SKILL.md:221–229` (and `124–135`) derives `q.isError ? 'failed'`, so a failed refetch over held data replaces the rows with the failed body. `:168–175` and `frontend/react/skills/rules/react.md:65` keep the data, marked stale. | (a) Derive `q.isError && q.data === undefined ? 'failed' : 'loaded'`, plus `stale={q.isError && q.data !== undefined}`. (b) A failed refetch replaces the rows, and `react.md:65` and the stale rules change to match. | P6 | the user |
| O15 | `data/dynamodb/SKILL.md:307` says "a thin repository per logical entity". `CLAUDE.md` "Pattern application" says "Repository pattern only when there is a real abstraction need". | (a) "Wrap it in a repository only when a second store or a test seam needs it." (b) A documented DynamoDB exception: a repository per entity is the sanctioned seam. | P10 | the user |
| O16 | `observability/logs-traces-setup/SKILL.md:301–318` has trace-correlation rows for dotnet, java and node and says "one config serves all stacks". be-rust also emits `trace_id` (`observability/structured-logging-rust`) and has no row. The smoke query at `:402` uses `env=`, but the label is `environment` (`:119`). | (a) Add the rust row, and use `{service=…, environment=…}`. (b) Scope the table to the OTel-SDK stacks, point rust at `structured-logging-rust`, and fix the label. | P10 | the user |
| O17 | `security/agents/security-architect.md:21` limits write reach to `docs/security/**`, `detections/**` and the cache "only", but `:44` writes the conformance audit into `docs/audits/`. | (a) Add `docs/audits/` to `:21`. (b) Write the conformance audit under `docs/security/`, by changing `:44`. | P12 | the user |
| O18 | Fourteen agents report "coverage output" in `Gate evidence:` on every run: `fe-blazor:65`, `fe-react:65`, `mobile-react-native:65`, `mobile-ios:60`, `mobile-android:60`, `desktop-macos:60`, `desktop-windows:38, 56, 83`, `be-dotnet:54`, `be-java:52`, `be-node:52`, `be-python:59` and `be-rust:54`. `tooling-engineer` also does, found by grep. The template (`.skill-template/agent.md:51`) does not, and in a plan task only the gate measures coverage. | (a) Template wording everywhere: `Gate evidence: <the Gate: line's commands and results>`. (b) Keep coverage, and the template gains "coverage, outside a plan task". | T1, P5–P9, P20 | the user |
| O19 | `backend/java/agents/be-java.md:26, 30` omits two things that `backend/dotnet/agents/be-dotnet.md:26, 30` has: the `auth/_shared/{auth0-concepts,oidc-concepts}` auth row, and "the telemetry base belongs to `observability-engineer-java`; never rebuild it". | (a) be-java matches be-dotnet. (b) The omission is deliberate, so be-dotnet drops both and each agent states why. | P9 | the user |
| O20 | `qa/typescript/agents/qa-ui-typescript.md:50` drops the sentence "a test you believe is wrong stays red: record a dated `D<n>`, and still finish". `qa-ui-java.md:52`, `qa-ui-dotnet.md:52` and the template carry it. | (a) Restore the template sentence. (b) Drop it from the template and every agent. | P18 (and T1, P14, P17 under b) | the user |
| O21 | The three `qa-ui-*` agents disagree on clarifying questions: "two or three up front" (`qa-ui-java.md:21`), "one" (`qa-ui-java.md:55`, `qa-ui-dotnet.md:55`) and "at most one" (`qa-ui-typescript.md:53`). | (a) All three say "ask at most one clarifying question, only when information is missing". (b) All three say "ask two or three clarifying questions up front". | P14, P17, P18 | the user |
| O22 | `engineering-practices/standards-audit-engine/SKILL.md:3, 10–16` says "Always enter through the stack skill", yet `design/agents/design-auditor.md:10, 27` loads the engine directly, because design has no `standards-audit` skill. | (a) The engine says "through a stack's `standards-audit` skill or `design-auditor`". (b) Design gains a `standards-audit` skill, and design-auditor enters through it. | P2 (and P5 under b) | the user |
| O23 | `tooling/_shared/capability-contract/SKILL.md:149` makes the CLI destructive gate "a prompt plus `--yes`". `tooling/skills/rules/tool-contract.md:21` makes it "a prompt plus `--yes` and `--dry-run`". | (a) The rule owns it: delete the restatement from the skill. (b) The skill's reading wins: drop `--dry-run` from the rule. | P20 | the user |
| O24 | `training-data/_shared/td-dataset-formats/SKILL.md:22–23` shows the envelope as `synthetic:claude-distill` with `CC-BY-4.0`. The rule (`training-data/skills/rules/datasets.md`) and `:44` want `synthetic:<exact-model-id>` and `synthetic-review-required`. | (a) Fix the example to the rule. (b) Widen the rule to accept a family id. | P20 | the user |

## 6. Decisions

**D1 — The owner answers every logical conflict once, first (L1), and the owning task applies the
answer.** Each P prompt carries both readings of its O rows, so L1 only records the answers. L1
rewrites a block only when an answer is neither (a) nor (b). Cost: all 21 tasks after L1 wait on one
human reply.

| Option | Verdict | Why |
|---|---|---|
| L1 first, the answers applied by the owning task | chosen | The decision travels with the skill, and the queue pauses once |
| A blocked task after G1 that applies every answer | rejected | It edits each file twice, and the plan stays open until the reply comes |
| Each P task asks its own questions | rejected | Up to fifteen separate pauses |

**D2 — One task, T1, fixes the 23 `rules` skills and the agent template across every plugin.** They share
one shape, and A3 judged them as a group. Batching by rule fixes the shape once, and the per-plugin
tasks then copy the corrected template. Cost: T1 touches a file in every plugin and runs alone,
before any P task.

**D3 — Size (R2) is met only by R16 moves and R17 or R19 deletions.** A rule that only one body states
stays, even when its body is still over budget. The task then records the remaining overage as a
`D<n>` with the file and the figure, and G1 decides. Cost: a body may end just under budget rather than
well under it.

**D4 — A `rules` skill's `When to use` and `When NOT to use` are one line each** (004's suggestion):
"installing or updating the rules", and "writing code: the rule files apply themselves". Cost: none
beyond 46 short lines.

**D5 — The unregistered skills gain `disable-model-invocation: true`.** They are
`engineering-practices/{agent-orientation-cache,code-comments,standards-audit-engine}` and
`ai-development/{claude-api,mcp-builder}`. The flag states what they are: loaded by path, never listed.
It also clears their R7 and R3 findings without writing front-door sections for skills that no session
reaches by trigger. Cost: registering one later takes a deliberate flip of the flag.

**D6 — Every task re-reads its rows at the line before fixing.** A3 and A4 re-read only their Data and
Logical rows and a sample of the rest. A wrong row is dropped and named, never fixed into a defect.
Cost: about 5k of reading per task.

**D7 — R9 contents lists may be generated by a throwaway script, never committed, that reads each
file's `##` headings.** 89 files take the same edit. Cost: each generated list is still read once.

## 7. Tasks

### L1 — The owner's answers to O1–O24

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each of O1–O24 sits in `## Answered questions (<date>)` as `**O<n> — <question>: <answer>.**`, and the `## Open questions` table holds only questions the owner deferred. Any answer that changes the lint (O1 b, O3 b, O4 b) has its task T2 written with its prompt.
**Depends on:** —.
**Budget:** ~55k. `CLAUDE.md` 25k, this plan's §5 and §6 8k, the prompt blocks it may rewrite ~12k, writes ~6k, the owner's reply 4k.
**Gate: none.** It records decisions. Nothing is runnable.

- Ask the owner every open question in **one** message. For each, give the two readings and the recommended one, which is (a).
  Under Plan Queue, end the message with the question and the line `PLAN_QUEUE: QUESTION`, and wait.
- Record each answer under a new `## Answered questions (<date>)` section, placed after `## 6. Decisions`.
  Delete its row from the `## Open questions` table. A question the owner defers stays in the table,
  with "deferred" in its Blocks cell.
- An answer that is neither (a) nor (b) is written into the owning prompt blocks as the exact edit, in
  place.
- If O1 (b), O3 (b) or O4 (b) is chosen, write task T2 after T1. Its stack is `infra` and its agent is
  `general-purpose`. Its deliverable is `tools/skill-lint.py` implementing the chosen readings, with a
  fixture for each. Its gate is `python3 -m pytest tools/test_skill_lint.py -q` and the coverage line from
  014 G1. Add T2 to the task table and its prompt block after T1's, and add `T2` to the `Depends on` line
  of every P task.
  - Under O1 (b), T2 also rewrites every Load-cell pointer that only D16's reading resolves as a full
    path. List them first with `python3 tools/skill-lint.py --json` run against the stricter lint.
- If O12 (b) is chosen, move its edit from P5–P9 into P1's block. P1 owns plan-format and
  `engineering-practices/rules/plans.md`, and `CLAUDE.md` "Planning".
- **Not in L1:** editing any skill.

### T1 — The agent template, the standard, and the 23 `rules` skills

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `.skill-template/agent.md:33` ends Fix on a checkable sweep, and `:51` carries O18's
`Gate evidence` wording. `writing-for-agents/SKILL.md` carries O1's R8 reading and O5's single
house-word list. All 23 `rules` SKILL.md are under 200 description chars, have both R7 headings, a
done-when on every step, no "Loads when" column and no hard-coded file count. Each of them gives
`0 findings` under the lint.
**Depends on:** L1.
**Budget:** ~135k. `CLAUDE.md` 25k, this plan's §2, §5 and §6 10k, the standard 4k, the template 1k, the 23 `rules` SKILL.md read (137k chars, about 35k) and rewritten (~45k), the 004 rule rows 3k, gate output 3k.
**Gate: own tests.** `python3 tools/skill-lint.py engineering-practices/writing-for-agents <the 23 rules SKILL.md paths>`
gives `0 findings`. `python3 tools/token-audit.py --violations-only | grep -E 'rules/SKILL.md|rules-security-governance/SKILL.md'`
prints nothing. `python3 tools/plugin-surface-check.py` gives `OK`.

- `.skill-template/agent.md:33`, R15: the Fix line ends "…then sweep: every sibling sharing the
  defect's pattern fixed or listed in the report".
- `.skill-template/agent.md:51`, O18: apply the answer. Under (a), keep the line as it is,
  `Gate evidence: <command + result>`, reworded to `<the Gate: line's commands and results>`. Under (b), add
  "coverage, outside a plan task".
- `engineering-practices/writing-for-agents/SKILL.md:102`, O1: apply the answer. Under (a), the R8 row
  reads "…exists relative to that file's folder, or inside a skill named in a code span on the same line
  or the line above". 014's plan is filed by then, so its §3 stays as it is.
- `engineering-practices/writing-for-agents/SKILL.md:73` and `:114`, O5: apply the answer.
- Under O3 (b) or O4 (b): add the R11 exception to the R11 row of the standard.
- The 23 `rules` SKILL.md are `backend/{dotnet,java,node,python,rust}/skills/rules/SKILL.md`,
  `business-analysis/skills/rules/SKILL.md`, `data/rules/SKILL.md`, `design/rules/SKILL.md`,
  `desktop/{macos,windows}/skills/rules/SKILL.md`, `devops/rules/SKILL.md`,
  `engineering-practices/rules/SKILL.md`, `frontend/{blazor,react}/skills/rules/SKILL.md`,
  `mobile/{android,ios,react-native}/skills/rules/SKILL.md`, `qa/{dotnet,java,typescript}/skills/rules/SKILL.md`,
  `security/rules-security-governance/SKILL.md`, `tooling/skills/rules/SKILL.md` and
  `training-data/skills/rules/SKILL.md`. In each:
  - **R2.** Applies to 19 of them; `design`, `business-analysis`, `desktop/macos` and `desktop/windows`
    are already within budget. Drop the description's parenthetical list of what the rules cover, and
    keep the trigger and the sibling.
  - **R7.** Add `## When to use` with "installing or updating the rules", and `## When NOT to use` with
    "writing code: the rule files apply themselves" (D4).
  - **R17.** Drop the rule-file table's "Loads when" column and its glosses, because step 5 reads each
    file's `paths:`.
  - **R17, step 2.** Applies to 21 of them, all but `dev` and `tooling`. Replace the hard-coded count
    ("all five files", "all eleven", …) with the form at `engineering-practices/rules/SKILL.md:32`:
    every `*.md` beside SKILL.md, and stop if there are none.
  - **R15.** Give steps 3, 4, 5 and 7 a done-when. Step 3 is done when "every source file is in the
    target". Step 5 is done when "every file each command lists is matched by an installed glob, or a
    glob is proposed for it". Step 7 is done when "each contradiction is listed, or the report says
    none".
  - **R16.** The unattended paragraph shrinks to one sentence inline, and the rest moves under the
    step it governs.
  - **R19.** Delete "A person types `/<plugin>:rules`." Also delete, in 22 of them (all but `tooling`),
    the clause "so a session that never touches … never pays for …".
  - **R18.** Delete "Never guess the answer."
- **Not in T1:** the rule files beside each SKILL.md (R23 belongs to the P task of their plugin), and
  every agent (each agent's Fix line and `Gate evidence` line belong to its P task).

### P1 — dev: the planning and verification front doors

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** these files give `0 findings` under the lint, and `token-audit` no longer lists
`writing-plans`: `engineering-practices/{writing-plans,systematic-debugging,verify-before-done,quality-constraints,source-grounding,notebooklm,brainstorming}`
and `engineering-practices/rules/plans.md`. Every row below is fixed or named as dropped.
**Depends on:** L1, T1.
**Budget:** ~115k. `CLAUDE.md` 25k, §2 and §5 of this plan 6k, the standard's rows 3k. Read and rewrite: `writing-plans` (6.5k to read, ~7k written), plan-format §4, §5 and §7 for its pointers (~6k), `systematic-debugging` 5k, `verify-before-done` 3k, `quality-constraints` 3k, `source-grounding` 2k, `notebooklm` 3k, `brainstorming` 4k, `plans.md` (2k to read, ~2k written). Plus the R9 list 1k and gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py engineering-practices/writing-plans engineering-practices/systematic-debugging engineering-practices/verify-before-done engineering-practices/quality-constraints engineering-practices/source-grounding engineering-practices/notebooklm engineering-practices/brainstorming engineering-practices/rules/plans.md`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'writing-plans|systematic-debugging|verify-before-done|quality-constraints|source-grounding|notebooklm|brainstorming'`.
Then run `python3 tools/plugin-surface-check.py`.

- **`engineering-practices/writing-plans/SKILL.md`** (25,316 chars)
  - **R2.**
  - **Data, `:3`.** "Not for the design itself (design)" becomes "(feature)".
  - **O2, at `:156–158` and `:311`.**
  - **R7.**
  - **R15, at `:68, 91, 108, 154, 174, 239`.** Steps 1–6 each get a done-when.
  - **R17, at `:253` (and `:136–145`, `:279–287`).** Replace each with a one-line pointer to plan-format §5 and §7 and to `rules/plans.md`.
  - **R19, at `:14` and `:98–99`.**
  - **R16, at `:82–89` and `:341–344`.** These go behind "a web route in the plan → read …".
  - **R20, at `:38` and `:297–344`.** "checkpoint reports" becomes "task reports"; the self-review items become criteria.
- **`engineering-practices/writing-plans/references/plan-format.md`.** R9.
- **`engineering-practices/systematic-debugging/SKILL.md`**
  - **Data, `:3`.** "(design)" becomes "(feature)".
  - **R7.**
  - **R15, at `:22, 90, 112, 183–184`.**
  - **R21, at `:60–75`.** Delete the `# Layer` comments.
  - **R16, at `:44–78`.** This goes behind "the bug crosses component boundaries → read …".
  - **R18, at `:27, 36, 105, 131, 148–149`.**
  - **R19, at `:16, 28, 100`.**
  - **R20, at `:181`.** The column becomes "Done when".
- **`engineering-practices/verify-before-done/SKILL.md`.** R7; R20 at `:18` (→ "The evidence check"); R19 at `:12` and `:106–112`.
- **`engineering-practices/quality-constraints/SKILL.md`.** R17 at `:33, 34, 36, 38–40`; R15 at `:45`; R20 at `:10, 17, 42, 45`; R19 at `:12`; O6 at `:32` and `:39`.
- **`engineering-practices/source-grounding/SKILL.md`.** R15 at `:27, 37, 52, 56`; R18 at `:48`; R19 at `:10` and `:71–74`.
- **`engineering-practices/notebooklm/SKILL.md`.** R8 at `:23` and `:40` (point into `engineering-practices/bundled/notebooklm/scripts/`); R7; R15 at `:22–25`; R17 at `:54`; R19 at `:8`.
- **`engineering-practices/brainstorming/SKILL.md`.** R17 at `:62–64`; R20 at `:20` (→ "design approval").
- **`engineering-practices/rules/plans.md`** (8,206 chars). R23: keep the constraints, and move procedure behind a pointer to plan-format.
- **Only under O12 (b):** plan-format §5 (`:204, 276`) and `CLAUDE.md` "Planning" let a task measure its own files' coverage, with the exact wording L1 recorded.
- **Not in P1:** `engineering-practices/rules/SKILL.md` (T1), and `engineering-practices/rules/feature-docs.md` (P4).

### P2 — dev: the audit front doors and the unregistered skills

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `spec-vs-code-audit` and `feature-audit` are under 16,000 chars. Mode B of each is in
`references/re-audit.md`. These all give `0 findings` under the lint:
`engineering-practices/{spec-vs-code-audit,feature-audit,standards-audit-engine,agent-orientation-cache,code-comments}`,
`ai-development/{claude-api,mcp-builder}` and `engineering-practices/agents/code-auditor.md`.
**Depends on:** L1, T1.
**Budget:** ~105k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k, `engineering-practices/rules/audits.md` read 2k. Read and rewrite: `spec-vs-code-audit` (6k to read, ~8k written), `feature-audit` (5k to read, ~7k written), `standards-audit-engine` (3k to read, ~3k written), the five frontmatter flags 3k, and `code-auditor.md` (3k to read, ~2k written). Plus the template 1k and gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py engineering-practices/spec-vs-code-audit engineering-practices/feature-audit engineering-practices/standards-audit-engine engineering-practices/agent-orientation-cache engineering-practices/code-comments ai-development/claude-api ai-development/mcp-builder engineering-practices/agents/code-auditor.md`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'spec-vs-code-audit|feature-audit'`.
Then run `python3 tools/plugin-surface-check.py`.

- **`engineering-practices/spec-vs-code-audit/SKILL.md`**
  - **R2.**
  - **R15, at `:147, 151, 175–177, 241–243`.**
  - **R17, at `:111, 114, 165–173, 247, 262–268, 333–339`.** Point at `engineering-practices/rules/audits.md:15–27`, and keep the verdict table and the templates.
  - **R16, at `:237–339`.** Mode B moves to `references/re-audit.md`, behind "a register and a prior report exist".
  - **R19, at `:10, 51, 343, 345`.**
- **`engineering-practices/feature-audit/SKILL.md`**
  - **R2.**
  - **R15, at `:80, 84, 112, 175`.**
  - **R17, at `:100–108, 183, 187, 207, 285–289`.** Point at `audits.md`, and keep the "Typical here" column.
  - **R16, at `:177–289`.** This moves to `references/re-audit.md`.
  - **R19, at `:10, 50, 295`.**
- **`engineering-practices/standards-audit-engine/SKILL.md`**
  - **Data and R4, at `:3`.** The description becomes "Use when a stack's `standards-audit` skill (`/<plugin>:audit`) or the `design-auditor` starts a conformance round."
  - **R17, at `:120–127`.** The severities follow `CLAUDE.md` "Review behavior"; keep the impact-qualifier rule.
  - **R19, at `:158–164`.**
  - **O22, at `:3` and `:10–16`.**
  - **R3 and R7.** Handled through D5.
- **D5, R7 and R3:** add `disable-model-invocation: true` to these five unregistered skills:
  - `engineering-practices/agent-orientation-cache/SKILL.md`
  - `engineering-practices/code-comments/SKILL.md`
  - `engineering-practices/standards-audit-engine/SKILL.md`
  - `ai-development/claude-api/SKILL.md`
  - `ai-development/mcp-builder/SKILL.md`

  Then confirm that the lint no longer reads any of them as a front door.
- **`engineering-practices/agents/code-auditor.md:51`, R13.** Add the template's `## Report` block, with a `Mode:` line.
- **Not in P2:** `engineering-practices/rules/audits.md`, which is read only.

### P3 — dev: `delivery-plan`, `session-budget`, `experience-plan`

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `backend/_shared/delivery-plan` and `backend/_shared/session-budget` are under 16,000
chars. `experience-plan`'s description is ≤ 200. All three folders give `0 findings` under the lint.
**Depends on:** L1, T1.
**Budget:** ~120k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k. `delivery-plan` is read (18k) and rewritten, with its shape and reconcile material moved into references (~18k written). Plan-format §3–§5 and §7 for the pointers 8k. `session-budget` (4k to read, ~5k written), the two R9 lists 2k, `experience-plan` 2k, gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py backend/_shared/delivery-plan backend/_shared/session-budget backend/_shared/experience-plan`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'delivery-plan|session-budget|experience-plan'`.
Then run `python3 tools/plugin-surface-check.py`.

- **`backend/_shared/delivery-plan/SKILL.md`** (73,093 chars)
  - **R2.**
  - **R17, at `:51–67, 359–369, 510–512, 614–623`.** The gate rule becomes one sentence plus "plan-format §5".
  - **R17, at `:343–381` and `:439–451`.** Keep what this skill adds (`Epic`, `Story`, `Stream`, `Order`, `Skills`, `Files`, the routing map), and cite §4 for the rest.
  - **R17, at `:18–48` and `:145`.** Replace them with one pointer line, keeping the epic/story binding.
  - **R17, at `:486–489, 559, 614–625`.** Write "copy plan-format §7 verbatim".
  - **R19, at `:9–35`.**
  - **R20, at `:125, 175, 205`.** "Out of scope" becomes `Not in <id>`.
  - **R16, at `:157–227`.** These move to `references/shape-<name>.md`, behind "Sequencing shape: <name>".
  - **R16, at `:563–598`.** This moves to `references/reconcile.md`, behind "a plan and partly built code both exist".
  - **Data and O2, at `:687`.**
- **`backend/_shared/delivery-plan/references/example-delivery-plan.md`.** R9.
- **`backend/_shared/session-budget/SKILL.md`** (16,907 chars). R2.
- **`backend/_shared/session-budget/references/prompts-section-template.md`.** R9.
- **`backend/_shared/experience-plan/SKILL.md`.** R2 (the description is 246 chars); R10 at `:159`, where the marker goes in a code span (014 D13).
- **Not in P3:** any other `backend/_shared/` skill (P4).

### P4 — dev: `solution-blueprint`, `business-documentation`, `feature-trace` and the planning and documenting agents

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** these are under budget: `solution-blueprint` and `business-documentation` (16,000), and `be-documenter.md` and `solution-planner.md` (14,000). Each path below gives `0 findings` under the lint. `rules/feature-docs.md` is ≤ 6,000.
**Depends on:** L1, T1.
**Budget:** ~125k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k, the template 1k. Read and rewrite: `solution-blueprint` (8k to read, ~7k written), `business-documentation` and `example-area.md` (9k to read, ~7k written), `be-documenter` (4.5k to read, ~4k written), `solution-planner` (4.2k to read, ~4k written), `be-feature-documenter` (3k to read, ~2k written), `feature-docs.md` and its target skill (6k to read, ~4k written). Plus the R9 list 1k and gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py backend/_shared/solution-blueprint backend/_shared/business-documentation backend/_shared/feature-trace backend/_shared/agents/be-documenter.md backend/_shared/agents/solution-planner.md backend/_shared/agents/be-feature-documenter.md engineering-practices/rules/feature-docs.md`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'solution-blueprint|business-documentation|be-documenter|solution-planner'`.
Then run `python3 tools/plugin-surface-check.py`.

- **`backend/_shared/solution-blueprint/SKILL.md`** (30,276 chars). R2.
- **`backend/_shared/business-documentation/SKILL.md`** (27,914 chars). R2, R3.
- **`backend/_shared/business-documentation/references/example-area.md:82, 139, 233, 234`.** R8: `bookings.md` and `scheduling.md` are example file names, so put them in a form the lint reads as a pattern or name them without backticks.
- **`backend/_shared/feature-trace/references/trace-recipes.md`.** R9.
- **`backend/_shared/agents/be-documenter.md`** (17,599 chars). R2.
- **`backend/_shared/agents/solution-planner.md`** (16,835 chars). R2; R12 at `:68`, where the path to read is `backend/_shared/delivery-plan`.
- **`backend/_shared/agents/be-feature-documenter.md:89`.** R13: add the `## Report` block with a `Mode:` line.
- **`engineering-practices/rules/feature-docs.md`** (10,500 chars). R23: keep the constraints at `:9–40`. Move the document's shape and procedure into the skill `be-feature-documenter` loads for the shape, which its Steps table's Load cells name. Leave a one-line pointer behind.
- **Not in P4:** `delivery-plan`, `session-budget` and `experience-plan` (P3), and `requirements-author` (P20).

### P5 — design and fe-blazor

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each path below gives `0 findings` under the lint. `fe-blazor`'s `ui-rules`, `basics` and `auth0-blazor` are under 16,000 chars.
**Depends on:** L1, T1.
**Budget:** ~125k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k, the template 1k. `design-auditor` (3.5k to read, ~5k written, including the Chrome reference), five R8 lines 2k, `visual-identity` (4k to read, ~4k written), `prototype` (2k to read, ~2k written). `fe-blazor.md` (2.5k to read, ~3k written), `ui-rules` (5k to read, ~5k written), `basics` (4.6k to read, ~4k written), `auth0-blazor` (4k to read, ~3k written), `accessibility` 1k, `component-testing` 2k, `experience-plan/references/rendering-strategy.md` read 2k, gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py design/agents/design-auditor.md design/design-tokens design/iconography design/motion design/ux-patterns design/visual-identity design/prototype design/ux-review frontend/blazor/agents/fe-blazor.md frontend/blazor/skills/ui-rules frontend/blazor/skills/basics frontend/blazor/skills/accessibility frontend/blazor/skills/component-testing auth/auth0-blazor`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'frontend/blazor|auth0-blazor'`.
Then run `python3 tools/plugin-surface-check.py`.

- **`design/agents/design-auditor.md`**
  - **R8, at `:74`.** The pointer becomes `engineering-practices/standards-audit-engine/references/report-template.md`.
  - **R13, at `:94`.** Add `## Report` with a `Mode:` line.
  - **R15, at `:73` and `:75`.**
  - **R17, at `:18`.** Write "the skills in the Sections table".
  - **R16, at `:17`.** The Chrome protocol moves to `design/ux-review/references/claude-in-chrome.md` (`ux-review` is the live-UI skill the Sections table loads), behind "driving Claude in Chrome → read …".
  - **R18, at `:16, 17, 20`.**
- **The five `pro-rules` pointers, R8.** In `design/{design-tokens,iconography,motion}/SKILL.md:23`, `design/ux-patterns/SKILL.md:31` and `design/visual-identity/SKILL.md:32`, the pointer becomes `design/ui-ux-pro-max/references/pro-rules.md`.
- **`design/visual-identity/SKILL.md`**
  - **R17, at `:17`.** Drop every corpus count.
  - **R15, at `:75–90`.**
  - **R17, at `:48–52, 64–70, 106–115`.**
  - **R19, at `:9, 88, 94, 96`.**
  - **R20, at `:7`.** The heading becomes `# Visual identity`.
  - **O11, at `:73, 79, 88, 108`.**
- **`design/prototype/SKILL.md`.** R16 at `:32` and `:49–57`, moved to `references/in-app-handoff.md`; R19 at `:8`.
- **`frontend/blazor/agents/fe-blazor.md`**
  - **R17, at `:20`.** "Read the rules" becomes the template wording, naming the core file.
  - **R15, at `:34` and `:36`.** Each proof is named.
  - **O11, at `:34`.**
  - **R17, at `:16`.** Write one sentence plus a pointer to `backend/_shared/experience-plan/references/rendering-strategy.md`.
  - **R19, at `:14` and `:16`.**
  - **The Fix line.** Use T1's template sweep wording.
  - **O18, at `:65`.**
- **`frontend/blazor/skills/ui-rules/SKILL.md`** (21,122 chars) and **`frontend/blazor/skills/basics/SKILL.md`** (18,619 chars). R2.
- **`auth/auth0-blazor/SKILL.md`** (16,035 chars). R2, R3.
- **`frontend/blazor/skills/accessibility/SKILL.md:11`.** R8: name the QA skill without a link, or link `../../../../qa/<stack>/skills/accessibility-testing/SKILL.md`.
- **`frontend/blazor/skills/component-testing/SKILL.md:116, 127`.** O12.
- **Not in P5:** `design/rules` and `frontend/blazor/skills/rules` (T1), and `standards-audit-engine` (P2).

### P6 — fe-react

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** these are under 16,000 chars: `frontend/react/skills/{error-handling,ui-rules,data-fetching,basics,animation}`. Each path below gives `0 findings` under the lint.
**Depends on:** L1, T1.
**Budget:** ~125k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k, the template 1k, `rules/react.md` and `react-data.md` read 3k. Read and rewrite: `error-handling` (8.5k to read, ~10k written), `ui-rules` (6k to read, ~5k written), `data-fetching` (5k to read, ~5k written), `basics` (4.3k to read, ~4k written), `animation` (4.2k to read, ~4k written), `fe-react.md` (3k to read, ~4k written). Plus R9 2k, R6 1k, `component-testing` 1k, `auth0-react` 1k and gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py frontend/react/agents/fe-react.md frontend/react/skills/error-handling frontend/react/skills/ui-rules frontend/react/skills/data-fetching frontend/react/skills/basics frontend/react/skills/animation frontend/react/skills/data-grid frontend/react/skills/standards-audit frontend/react/skills/component-testing auth/auth0-react`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'frontend/react'`.
Then run `python3 tools/plugin-surface-check.py`.

- **`frontend/react/skills/error-handling/SKILL.md`** (33,390 chars)
  - **R2.**
  - **R21, at `:45, 49, 72–73, 130–135, 159–165, 188–194, 214–228`.**
  - **R17, at `:77–79, 199, 245–256, 304–318`.** Point at `rules/react.md:65` and `rules/react-data.md:20, 24`.
  - **R15, at `:322–344`.**
  - **R19, at `:256`.**
  - **R16, at `:101–108` and `:280–286`.**
  - **O14, at `:221–229` and `:124–135`.**
- **R2 bodies.** `frontend/react/skills/ui-rules/SKILL.md` (23,086 chars), `data-fetching/SKILL.md` (20,054 chars), `basics/SKILL.md` (17,124 chars) and `animation/SKILL.md` (16,679 chars).
- **R9.** `frontend/react/skills/data-grid/references/feature-recipes.md` and `frontend/react/skills/standards-audit/references/conformance-checklist.md`.
- **`frontend/react/skills/component-testing/SKILL.md`.** R6: rename the routing heading to a topic heading. O12 at `:152` and `:161`.
- **`frontend/react/agents/fe-react.md`**
  - **R17, at `:24`.** The rules listing becomes the template wording.
  - **R15, at `:36` and `:38`.**
  - **O11, at `:19` and `:36`.**
  - **R17, at `:18`.** Write one sentence plus the `rendering-strategy.md` pointer.
  - **R17, at `:19`.** Delete the invariant and keep the Done-when cells.
  - **The Fix line.** Use T1's template sweep wording.
  - **O18, at `:65`.**
- **`auth/auth0-react/SKILL.md`.** R3.
- **Not in P6:** `frontend/react/skills/rules` (T1). `rules/react.md` changes only under O14 (b).

### P7 — mobile-react-native, mobile-ios, mobile-android

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each path below gives `0 findings` under the lint. `mobile/android/skills/unit-testing` is under 16,000 chars. No mobile agent caches a version floor or a rule-file listing.
**Depends on:** L1, T1.
**Budget:** ~100k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k, the template 1k. The three agents: 7k to read and ~9k written. Android `unit-testing` (4k to read, ~6k written, including two references), the iOS and RN testing lines 2k, three R9 lists 3k, four R3 descriptions 3k, `android-tests.md` read 1k, gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py mobile/react-native/agents/mobile-react-native.md mobile/ios/agents/mobile-ios.md mobile/android/agents/mobile-android.md mobile/android/skills/unit-testing mobile/android/skills/kotlin-multiplatform mobile/ios/skills/unit-testing mobile/react-native/skills/component-testing mobile/android/skills/standards-audit mobile/ios/skills/standards-audit mobile/react-native/skills/standards-audit auth/auth0-android auth/auth0-ios auth/auth0-react-native`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'mobile/'`.
Then run `python3 tools/plugin-surface-check.py`.

- **`mobile/react-native/agents/mobile-react-native.md`**
  - **R17, at `:21`.** Use the template's rules wording.
  - **R17, at `:16`.** Point at the version policy.
  - **R15, at `:35` and `:37`.**
  - **O11, at `:35`.**
  - **R18, at `:12`.** Delete "Never load `qa/`".
  - **The Fix line.**
  - **O18, at `:65`.**
- **`mobile/ios/agents/mobile-ios.md`**
  - **R17, at `:16`.** Keep the "a view in a folder no glob covers" note.
  - **R17, at `:17` and `:39`.**
  - **R15, at `:30` and `:32`.**
  - **O11, at `:30`.**
  - **R18, at `:12`.**
  - **The Fix line.**
  - **O18, at `:60`.**
- **`mobile/android/agents/mobile-android.md`**
  - **Data, `:17`.** Write "below the `store-compliance` target is a finding", with no number.
  - **R17, at `:16`, `:3` and `:17`.**
  - **R15, at `:30, 32, 34`.**
  - **R18, at `:12`.**
  - **The Fix line.**
  - **O18, at `:60`.**
- **`mobile/android/skills/unit-testing/SKILL.md`** (16,505 chars)
  - **R2.**
  - **Data, `:11, 20–22, 135, 183`.** Delete the plan refs and the verification notes.
  - **R17, at `:75–78` and `:95–97`.** Write "per `android-tests.md`".
  - **R15, at `:210–215`.**
  - **R16, at `:113–163` and `:173–208`.** These move to `references/compose-ui-tests.md` and `references/coverage-kover.md`.
  - **R20, at `:96–97`.** Write "a test client" and "a teardown registry".
  - **O12, at `:180, 219, 223`.**
- **The two sibling testing lines, O12.** `mobile/ios/skills/unit-testing/SKILL.md:162, 183` and `mobile/react-native/skills/component-testing/SKILL.md:169, 188`.
- **R9.** `mobile/{android,ios,react-native}/skills/standards-audit/references/conformance-checklist.md`.
- **R3.** `mobile/android/skills/kotlin-multiplatform/SKILL.md`, and `auth/auth0-{android,ios,react-native}/SKILL.md`.
- **Not in P7:** the mobile `rules` skills (T1), and `mobile/_shared/` (no rows).

### P8 — desktop-macos, desktop-windows

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each path below gives `0 findings` under the lint. `desktop/macos/skills/rules/swift.md` is ≤ 6,000 chars, and every other listed rule file is ≤ 2,500. Neither desktop agent caches a rule-file listing, a version floor or a command table.
**Depends on:** L1, T1.
**Budget:** ~120k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k, the template 1k. The two agents: 5.6k to read and ~7k written. Ten rule files: 9k to read and ~10k written, plus ~10k reading the owning skills that the trimmed recipes point at. `desktop/windows/skills/unit-testing`: 3.7k to read and ~3k written. Plus two R9 lists 2k, three R3 descriptions 2k and gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py desktop/macos/agents/desktop-macos.md desktop/windows/agents/desktop-windows.md desktop/macos/skills/rules/swift.md desktop/macos/skills/rules/swiftui-mac.md desktop/macos/skills/rules/xcode-config.md desktop/macos/skills/rules/mac-accessibility.md desktop/macos/skills/rules/swift-persistence.md desktop/macos/skills/rules/appkit.md desktop/macos/skills/rules/swift-networking.md desktop/windows/skills/rules/winui-xaml.md desktop/windows/skills/rules/cppwinrt.md desktop/windows/skills/rules/win-accessibility.md desktop/windows/skills/unit-testing desktop/macos/skills/standards-audit desktop/windows/skills/standards-audit desktop/_shared/security auth/auth0-macos auth/auth0-windows`.
Then run `wc -c desktop/macos/skills/rules/*.md desktop/windows/skills/rules/*.md`. The core file must be ≤ 6,000 and every other file ≤ 2,500.
Then run `python3 tools/plugin-surface-check.py`.

- **`desktop/macos/agents/desktop-macos.md`**
  - **R17, at `:16` and `:17`.** Keep the "a view in a folder no glob covers" note.
  - **R15, at `:32` and `:35`.**
  - **R18, at `:12`.**
  - **The Fix line.**
  - **O18, at `:60`.**
- **`desktop/windows/agents/desktop-windows.md`**
  - **R17, at `:16`.**
  - **R15, at `:55` and `:58`.** This also clears the restated "Desktop code rules".
  - **R17, at `:31–40`.** Each row gets one pointer to its owning skill: `project-setup`, `unit-testing` or `cpp-winrt/references/testing-and-coverage.md`.
  - **R19, at `:42`.**
  - **R18, at `:12`.**
  - **The Fix line.**
  - **O18, at `:38, 56, 83`.**
- **R23, macOS.** `desktop/macos/skills/rules/swift.md` (6,688 chars), `swiftui-mac.md` (3,959), `xcode-config.md` (3,428), `mac-accessibility.md` (3,414), `swift-persistence.md` (2,940), `appkit.md` (2,547) and `swift-networking.md` (2,502). Trim each to its constraints, and point at the skill for the recipe.
- **R23, Windows.** `desktop/windows/skills/rules/winui-xaml.md` (3,610 chars), `cppwinrt.md` (3,571) and `win-accessibility.md` (2,788).
- **`desktop/windows/skills/unit-testing/SKILL.md`**
  - **R17, at `:94–101, 138–140, 169–177`.**
  - **R17, at `:18, 104, 132`.** Drop the numbers.
  - **R21, at `:57` and `:123`.**
  - **R19, at `:165–167` and `:199`.**
  - **O12, at `:185`.** Only if the line runs the coverage measure inside a plan task.
- **R9.** `desktop/{macos,windows}/skills/standards-audit/references/conformance-checklist.md`.
- **R3.** `desktop/_shared/security/SKILL.md` and `auth/auth0-{macos,windows}/SKILL.md`.
- **Not in P8:** `mobile/ios/skills/rules/*`. They share file names, but they are within budget and have no rows.

### P9 — be-dotnet, be-java, be-node, be-python, be-rust

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each path below gives `0 findings` under the lint. These are under 16,000 chars: `backend/{java,dotnet,node}/skills/unit-testing`, `backend/python/skills/media-processing` and `backend/rust/skills/pattern-writer`. No `be-*` agent caches its rule-file listing or the version policy.
**Depends on:** L1, T1.
**Budget:** ~125k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k, the template 1k. The five agents: 8k to read and ~10k written. Five R2 bodies: 23k to read and ~25k written. `python-pipeline.md` and `python-container.md` read 2k, `auth/_shared` R3 2k, gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py backend/dotnet/agents/be-dotnet.md backend/java/agents/be-java.md backend/node/agents/be-node.md backend/python/agents/be-python.md backend/rust/agents/be-rust.md backend/dotnet/skills/unit-testing backend/java/skills/unit-testing backend/node/skills/unit-testing backend/python/skills/unit-testing backend/rust/skills/unit-testing backend/python/skills/media-processing backend/rust/skills/pattern-writer auth/_shared/auth0-concepts auth/_shared/oidc-concepts`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'backend/(dotnet|java|node|python|rust)/'`.
Then run `python3 tools/plugin-surface-check.py`.

- **The five agents.** These are `backend/{dotnet,java,node,python,rust}/agents/be-<stack>.md`. In each:
  - **R17, "Read the rules".** It is at `:16` in four of them and at `:22` in `be-python`. Use the template wording, and keep be-rust's inline `#[cfg(test)]` note and be-node's narrow `*.ts` globs.
  - **R17, the version asides.** These are at `:17` (`:23` in `be-python`, `:8` and `:17` in `be-rust`). Write "the lane per the core rule file and `CLAUDE.md` 'Version policy'".
  - **R15, Steps 1 and 4.** These are at `:25` and `:28` (`:31` and `:34` in `be-python`). Step 1 is done when "the `pattern-guide` earn-it criterion is quoted against the code, or 'no pattern'". Step 4 is done when "the `code-review` findings table has no blocker or major row".
  - **The Fix line.**
  - **O18.** It is at `:54` in `be-dotnet`, `:52` in `be-java`, `:52` in `be-node`, `:59` in `be-python` and `:54` in `be-rust`.
- **`backend/python/agents/be-python.md:16–17`.** R17: one line each, pointing at `python-pipeline.md:12` and `python-container.md:14`. Keep the contract invariant at `:18`.
- **`backend/java/agents/be-java.md:26, 30`.** O19.
- **R2 bodies.**
  - `backend/java/skills/unit-testing/SKILL.md` (19,052 chars)
  - `backend/dotnet/skills/unit-testing/SKILL.md` (18,219)
  - `backend/node/skills/unit-testing/SKILL.md` (17,906)
  - `backend/python/skills/media-processing/SKILL.md` (19,038)
  - `backend/rust/skills/pattern-writer/SKILL.md` (17,975)
- **O12.** `backend/dotnet/skills/unit-testing/SKILL.md:221`, `java/…:244`, `node/…:264`, `python/…:153, 165` and `rust/…:188`.
- **R3.** `auth/_shared/auth0-concepts/SKILL.md` and `auth/_shared/oidc-concepts/SKILL.md`.
- **Not in P9:** `observability/` (P10), and the `be-*` `rules` skills (T1).

### P10 — data and observability

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** these are under 16,000 chars: `data/{dynamodb,elasticsearch,cosmosdb}` and `observability/logs-traces-setup`. Each path below gives `0 findings` under the lint.
**Depends on:** L1, T1.
**Budget:** ~110k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k, the template 1k. `data-architect.md` (2.2k to read, ~2k written), `dynamodb` (4.8k to read, ~7k written, including two references), `elasticsearch` (4.5k to read, ~4k written), `cosmosdb` (4.2k to read, ~4k written), `migrations` 1k, `logs-traces-setup` (4.2k to read, ~6k written), the four observability agents' Fix lines 3k, gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py data/agents/data-architect.md data/dynamodb data/elasticsearch data/cosmosdb data/_shared/migrations observability/logs-traces-setup observability/agents/observability-engineer-dotnet.md observability/agents/observability-engineer-java.md observability/agents/observability-engineer-node.md observability/agents/observability-engineer-rust.md`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'data/(dynamodb|elasticsearch|cosmosdb)|logs-traces-setup'`.
Then run `python3 tools/plugin-surface-check.py`.

- **`data/agents/data-architect.md`.** R17 at `:24` (the rules listing); the Fix line at `:42`.
- **`data/dynamodb/SKILL.md`** (19,149 chars)
  - **R2.**
  - **Data, `:14, 24, 96`.** Delete `:24` and the GA date. `:96` becomes "eventually consistent reads only".
  - **R21, at `:110–119, 141, 234, 237`.**
  - **R15, at `:302–308`.**
  - **R17, at `:274–300`.**
  - **R18, at `:289–300`.**
  - **R16, at `:105–207`.** These move to `references/connections.md` and `references/security-iam.md`.
  - **O15, at `:307`.**
- **R2 bodies.** `data/elasticsearch/SKILL.md` (17,886 chars) and `data/cosmosdb/SKILL.md` (16,849 chars).
- **`data/_shared/migrations/SKILL.md:63`.** O4.
- **`observability/logs-traces-setup/SKILL.md`** (16,869 chars)
  - **R2.**
  - **Data, `:129` and `:193`.** Write "Promtail reached end of life in Mar 2026; use Alloy" once.
  - **R15, at `:394–403`.**
  - **R17, at `:368–392`.**
  - **R21, at `:138–173`.**
  - **R16, at `:183–189` and `:343–358`.**
  - **O16, at `:301–318` and `:402`.**
- **`observability/agents/observability-engineer-{dotnet,java,node,rust}.md`.** The Fix line.
- **Not in P10:** `data/rules` (T1).

### P11 — devops: the agent, `k8s-security`, `supply-chain-security`, `iac-security`

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** these are under 16,000 chars: `devops/{k8s-security,supply-chain-security,iac-security}`. Each path below gives `0 findings` under the lint.
**Depends on:** L1, T1.
**Budget:** ~125k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k, the template 1k. `devops-engineer.md` (2.6k to read, ~3k written). `k8s-security` (9k to read, ~10k written), with its references read 3k. `supply-chain-security` (9k to read, ~9k written). `iac-security` (7.8k to read, ~8k written). Gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py devops/agents/devops-engineer.md devops/k8s-security devops/supply-chain-security devops/iac-security`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'devops/(k8s-security|supply-chain-security|iac-security)'`.
Then run `python3 tools/plugin-surface-check.py`.

- **`devops/agents/devops-engineer.md`**
  - **R17, at `:22`.**
  - **R15, at `:50`.** The row 2 done-when gains "…or the run stops with the map and proposal reported and nothing written".
  - **R18, at `:16` and `:52`.**
  - **The Fix line.**
- **`devops/k8s-security/SKILL.md`** (36,584 chars)
  - **R2.**
  - **R17, at `:40–57` and `:458–522`.** Delete `## Rules`.
  - **R17, at `:79–114, 210–217, 400–456`.** Each pin appears once, with the map and lists behind their references.
  - **R21, at `:82–83, 92–93, 125–139, 161–173, 192–204, 242–251, 268–273, 287–292, 364–381, 400–409`.**
  - **R19, at `:16–22`.**
  - **R16, at `:122–230` and `:400–456`.**
  - **Data, `:545`.** Write "(step 4, Kubernetes and runtime)".
  - **O13, at `:133–134`, `:462` and `references/kube-bench.md:21–22`.**
- **R2 bodies.** `devops/supply-chain-security/SKILL.md` (36,528 chars) and `devops/iac-security/SKILL.md` (31,022 chars).
- **Not in P11:** the other devops skills (P12), and `devops/rules` (T1).

### P12 — devops, the rest, and security-governance

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** these are under 16,000 chars: `devops/{infra-controls-validation,container-runtime-security,cloud-posture}` and `security/cloud-incident-response`. Each path below gives `0 findings` under the lint.
**Depends on:** L1, T1.
**Budget:** ~115k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k. `infra-controls-validation` (6.4k to read, ~7k written), `container-runtime-security` (5.7k to read, ~6k written), `cloud-posture` (5.5k to read, ~6k written), `security-architect.md` (2.2k to read, ~2k written), `cloud-incident-response` (5.3k to read, ~6k written), `runbooks.md` read 2k, the R10 and R9 edits 3k, gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py devops/infra-controls-validation devops/container-runtime-security devops/cloud-posture security/agents/security-architect.md security/cloud-incident-response security/rules-security-governance/security-governance.md security/standards-audit`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'infra-controls-validation|container-runtime-security|cloud-posture|cloud-incident-response'`.
Then run `python3 tools/plugin-surface-check.py`.

- **R2 bodies.**
  - `devops/infra-controls-validation/SKILL.md` (25,703 chars)
  - `devops/container-runtime-security/SKILL.md` (22,947 chars)
  - `devops/cloud-posture/SKILL.md` (22,000 chars)
- **`security/agents/security-architect.md`**
  - **R17, at `:26`.**
  - **R15, at `:40`.**
  - **R19, at `:12, 18, 42, 53`.** Keep the Invariant at `:18`.
  - **O17, at `:21` and `:44`.**
- **`security/cloud-incident-response/SKILL.md`** (21,277 chars)
  - **R2.**
  - **R15, at `:63–84`.**
  - **R17, at `:107–118`.** Point at `security/rules-security-governance/runbooks.md` "Cloud incident response".
  - **R19, at `:9–13, 63–64, 109–110, 126–128`.**
  - **R16, at `:47–59` and `:69–75`.**
  - **Data, `:131`.**
- **R10.** `security/rules-security-governance/security-governance.md:40` and `security/standards-audit/references/conformance-checklist.md:253`.
- **R9.** `security/standards-audit/references/conformance-checklist.md`.
- **Not in P12:** `security/rules-security-governance/SKILL.md` (T1), and the penetration-testing skills (P13).

### P13 — penetration-testing

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** these are under 16,000 chars: `security/{cloud-attack-azure,cloud-attack-aws,cloud-recon-enumeration,atomic-simulation,cloud-attack-gcp}`. `metasploit-setup`'s description is ≤ 200 chars and R3-shaped. `penetration-tester.md` gives `0 findings` under the lint.
**Depends on:** L1, T1.
**Budget:** ~110k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k. `penetration-tester.md` (2.8k to read, ~3k written). Five R2 bodies: 23k to read and ~25k written. `metasploit-setup` description 2k, gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py security/agents/penetration-tester.md security/cloud-attack-azure security/cloud-attack-aws security/cloud-recon-enumeration security/atomic-simulation security/cloud-attack-gcp security/metasploit-setup`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'security/(cloud-attack|cloud-recon|atomic-simulation|metasploit-setup)'`.
Then run `python3 tools/plugin-surface-check.py`.

- **`security/agents/penetration-tester.md`**
  - **R15, at `:56` and `:64`.**
  - **R17, at `:20` and `:62`.** Keep each control once, in Invariants.
  - **R19, at `:18`.**
- **R2 bodies.**
  - `security/cloud-attack-azure/SKILL.md` (21,020 chars)
  - `security/cloud-attack-aws/SKILL.md` (19,859)
  - `security/cloud-recon-enumeration/SKILL.md` (18,538)
  - `security/atomic-simulation/SKILL.md` (16,496)
  - `security/cloud-attack-gcp/SKILL.md` (16,331)
- **`security/metasploit-setup/SKILL.md`.** R2 (the description is 452 chars); R3.
- **Not in P13:** the scope and authorization controls themselves. They stay, stated once each.

### P14 — qa-java: the lane's agents, conventions, rule files, contents lists and three bodies

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each path below gives `0 findings` under the lint. `qa/java/skills/{ai-feature-testing,api-contract-testing,test-quality-check}` are under 16,000 chars. Both rule files are ≤ 2,500. The Playwright MCP command lives once in the lane, in `page-objects-from-url`.
**Depends on:** L1, T1.
**Budget:** ~125k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k, the template 1k. `qa-ui-java.md` (3k to read, ~3k written), six Fix lines 4k, `inhouse-framework-conventions` (5k to read, ~4k written), two rule files (1.5k to read, ~3k written), 21 R9 lists ~8k by script, the MCP command in two skills 3k. `ai-feature-testing` (5.3k to read, ~7k written), `api-contract-testing` (5.2k to read, ~5k written), `test-quality-check` (4.7k to read, ~5k written). Gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py qa/java/agents qa/java/skills/inhouse-framework-conventions qa/java/skills/rules/desktop-tests.md qa/java/skills/rules/qa-java-ui.md qa/java/skills/page-objects-from-url qa/java/skills/evidence-capture qa/java/skills/ai-feature-testing qa/java/skills/api-contract-testing qa/java/skills/test-quality-check <the 21 R9 skill folders below>`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'qa/java/skills/(ai-feature-testing|api-contract-testing|test-quality-check)/'`.
Then run `python3 tools/qa-version-check.py`, and then `python3 tools/plugin-surface-check.py`.

- **`qa/java/agents/qa-ui-java.md`**
  - **R17, at `:16`.**
  - **R17, at `:25`.** The MCP command becomes a pointer to `page-objects-from-url`.
  - **R18, at `:32` and `:55`.**
  - **The Fix line, at `:46`.**
  - **O21, at `:21` and `:55`.**
- **The Fix line.** `qa/java/agents/qa-{api,bdd,desktop,llm,mobile,performance}-java.md`.
- **The MCP command, R17.** Keep `qa/java/skills/page-objects-from-url/SKILL.md` as the one home of the `claude mcp add … @playwright/mcp@…` command. `qa/java/skills/evidence-capture/SKILL.md` points at it.
- **`qa/java/skills/inhouse-framework-conventions/SKILL.md`.** R17 at `:172–178, 263–275, 277–`; R19 at `:249–261`. Under O7 (b), the URL exception goes in at `:283`.
- **R23.** `qa/java/skills/rules/desktop-tests.md` (3,636 chars) and `qa/java/skills/rules/qa-java-ui.md` (2,523).
- **`qa/java/skills/ai-feature-testing/SKILL.md`** (21,319 chars)
  - **R2.**
  - **R21, at `:237, 260–261, 274`.** Use an injected `LlmClient` and a shared `ObjectMapper`.
  - **R21, at `:234, 238, 255, 261–262, 277`.**
  - **R21, at `:236, 238, 259, 273`.** Write `Should_X_When_Y` names and named constants.
  - **R17, at `:20–37, 86–89, 281–306, 321–339`.**
  - **R19, at `:9–20`.**
  - **R18, at `:64–72` and `:281–306`.**
- **R2 bodies.** `qa/java/skills/api-contract-testing/SKILL.md` (20,664 chars) and `qa/java/skills/test-quality-check/SKILL.md` (18,714 chars).
- **R9, in `qa/java/skills/`.**
  - `analytics-testing/references/playwright.md`
  - `browser-cloud-setup/references/details.md`
  - `email-testing/references/{gmail-imap,mailosaur,mailpit,sendgrid-sandbox}.md`
  - `evidence-capture/references/playwright.md`
  - `file-storage-testing/references/{azure-blob,s3}.md`
  - `language-testing/references/details.md`
  - `messaging-testing/references/{kafka,rabbitmq,service-bus,sqs}.md`
  - `network-mocking/references/{cdp,playwright-routes,proxy}.md`
  - `payment-testing/references/stripe-api.md`
  - `realtime-stream-testing/references/details.md`
  - `test-login-tokens/references/details.md`
  - `visual-regression/references/playwright-snapshots.md`
- **Not in P14:** `qa/java/skills/{data-driven-testing,failure-injection-testing,api-test-author/grpc,security-testing/*}` (P15), `qa/_shared` (P16) and `qa/java/skills/rules/SKILL.md` (T1).

### P15 — qa-java: the remaining bodies

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** these six `qa/java` skills are under 16,000 chars, and each gives `0 findings` under the lint.
**Depends on:** L1, T1.
**Budget:** ~110k. `CLAUDE.md` 25k, §2 6k, the standard's rows 3k. Six bodies: 29k to read and ~30k written. `qa/java/skills/rules/*.md` read 3k as R17 targets. Gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py qa/java/skills/data-driven-testing qa/java/skills/failure-injection-testing qa/java/skills/api-test-author/grpc qa/java/skills/security-testing/passive-scan qa/java/skills/security-testing/dependency-scan qa/java/skills/security-testing/permission-testing`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'qa/java/skills/(data-driven-testing|failure-injection-testing|api-test-author/grpc|security-testing)/'`.
Then run `python3 tools/qa-version-check.py`, and then `python3 tools/plugin-surface-check.py`.

- **R2.** These are in `qa/java/skills/`:
  - `data-driven-testing/SKILL.md` (19,798 chars)
  - `failure-injection-testing/SKILL.md` (20,126)
  - `api-test-author/grpc/SKILL.md` (20,090)
  - `security-testing/passive-scan/SKILL.md` (19,923)
  - `security-testing/dependency-scan/SKILL.md` (18,411)
  - `security-testing/permission-testing/SKILL.md` (17,613)
- **Not in P15:** the `qa/_shared/security-testing/*` skills (P16).

### P16 — qa/_shared

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** the seven `qa/_shared` bodies below are under 16,000 chars. These give `0 findings` under the lint: `python-web-testing`, `webmcp-testing`, `contract-testing-pact` and `performance`.
**Depends on:** L1, T1.
**Budget:** ~125k. `CLAUDE.md` 25k, §2 6k, the standard's rows 3k. Seven bodies: 31k to read and ~35k written. `python-web-testing` (3k to read, ~4k written), with `qa/typescript/skills/rules/ui-tests.md` read 1k. `webmcp-testing`, `contract-testing-pact` and `performance`: 4k. Gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py qa/_shared/security-testing qa/_shared/api-spec-assets qa/_shared/python-web-testing qa/_shared/webmcp-testing qa/_shared/contract-testing-pact qa/_shared/performance`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'qa/_shared/'`.
Then run `python3 tools/qa-version-check.py`, and then `python3 tools/plugin-surface-check.py`.

- **R2.** These are in `qa/_shared/`:
  - `security-testing/image-infra-scan/SKILL.md` (19,111 chars)
  - `security-testing/code-scan/SKILL.md` (18,476)
  - `security-testing/known-vuln-scan/SKILL.md` (18,062)
  - `security-testing/active-scan/SKILL.md` (16,788)
  - `security-testing/secrets-scan/SKILL.md` (16,672)
  - `security-testing/certificate-scan/SKILL.md` (16,258)
  - `api-spec-assets/SKILL.md` (18,353)
- **`qa/_shared/python-web-testing/SKILL.md`**
  - **R7.**
  - **R17, at `:46–56`.** Point at the `qa-*` UI rule files and keep only the Python spellings.
  - **R22, at `:134`.** Write "hand it to the `qa-ui-<stack>` agent".
  - **R16, at `:121–134`.**
- **`qa/_shared/webmcp-testing/SKILL.md:42`.** R10.
- **R6.** `qa/_shared/contract-testing-pact/SKILL.md` and `qa/_shared/performance/SKILL.md`. Rename the routing headings to topic headings: "Choosing Pact", "Profiler hand-off".
- **Not in P16:** each lane's own skills (P14, P15, P17, P18).

### P17 — qa-dotnet

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each path below gives `0 findings` under the lint. The five `qa/dotnet` bodies below are under 16,000 chars. Both rule files are ≤ 2,500. The Playwright MCP command lives once in the lane.
**Depends on:** L1, T1.
**Budget:** ~140k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k, the template 1k. `qa-ui-dotnet.md` (3k to read, ~3k written), six Fix lines 4k, `inhouse-framework-conventions` (5k to read, ~4k written), two rule files (1.6k to read, ~3k written), 26 R9 lists ~9k by script, two R3 descriptions 2k, the MCP command 3k. Five bodies: 23k to read and ~25k written. Gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py qa/dotnet/agents qa/dotnet/skills/inhouse-framework-conventions qa/dotnet/skills/rules/desktop-tests.md qa/dotnet/skills/rules/web-ui.md qa/dotnet/skills/page-objects-from-url qa/dotnet/skills/evidence-capture qa/dotnet/skills/desktop-screen-explorer qa/dotnet/skills/desktop-window-objects qa/dotnet/skills/security-testing qa/dotnet/skills/api-test-author qa/dotnet/skills/failure-injection-testing <the 26 R9 skill folders below>`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'qa/dotnet/'`.
Then run `python3 tools/qa-version-check.py`, and then `python3 tools/plugin-surface-check.py`.

- **`qa/dotnet/agents/qa-ui-dotnet.md`**
  - **R17, at `:16`.**
  - **R17, at `:17`.** Point at the version policy.
  - **R17, at `:29`.** The MCP command becomes a pointer to `page-objects-from-url`.
  - **R17, at `:46`.** Write "the trace commands in `evidence-capture`".
  - **The Fix line.**
  - **O21, at `:55`.**
- **The Fix line.** `qa/dotnet/agents/qa-{api,bdd,desktop,llm,mobile,performance}-dotnet.md`.
- **The MCP command, R17.** Its one home is `qa/dotnet/skills/page-objects-from-url/SKILL.md`. `qa/dotnet/skills/evidence-capture/SKILL.md` points at it.
- **`qa/dotnet/skills/inhouse-framework-conventions/SKILL.md`**
  - **Data, `:239`.** Write "a typed DTO, not `RestResponse`".
  - **R17, at `:174–180, 263–, 278–`.**
  - **R19, at `:249–261`.**
  - **O7, at `:150` and `:170–172`.**
- **R23.** `qa/dotnet/skills/rules/desktop-tests.md` (3,403 chars) and `qa/dotnet/skills/rules/web-ui.md` (2,714).
- **R3.** `qa/dotnet/skills/desktop-screen-explorer/SKILL.md` and `qa/dotnet/skills/desktop-window-objects/SKILL.md`.
- **R2.** These are in `qa/dotnet/skills/`:
  - `security-testing/passive-scan/SKILL.md` (19,853 chars)
  - `api-test-author/grpc/SKILL.md` (18,597)
  - `security-testing/permission-testing/SKILL.md` (17,748)
  - `failure-injection-testing/SKILL.md` (17,468)
  - `security-testing/dependency-scan/SKILL.md` (17,014)
- **R9, in `qa/dotnet/skills/`.**
  - `accessibility-testing/references/{axe-playwright,lighthouse-ci}.md`
  - `ai-feature-testing/references/details.md`
  - `analytics-testing/references/playwright.md`
  - `api-test-author/writer/references/details.md`
  - `browser-cloud-setup/references/details.md`
  - `email-testing/references/{gmail-imap,mailosaur,mailpit,sendgrid-sandbox}.md`
  - `evidence-capture/references/playwright.md`
  - `file-storage-testing/references/{azure-blob,s3}.md`
  - `language-testing/references/details.md`
  - `messaging-testing/references/{kafka,rabbitmq,service-bus,sqs}.md`
  - `network-mocking/references/{cdp,playwright-routes,proxy}.md`
  - `payment-testing/references/stripe-api.md`
  - `realtime-stream-testing/references/details.md`
  - `standards-audit/references/conformance-checklist.md`
  - `test-login-tokens/references/details.md`
  - `visual-regression/references/playwright-snapshots.md`
- **Not in P17:** `qa/dotnet/skills/rules/SKILL.md` (T1), and `qa/_shared` (P16).

### P18 — qa-typescript

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each path below gives `0 findings` under the lint. The five `qa/typescript` bodies below are under 16,000 chars. `ui-tests.md` is ≤ 2,500. The Playwright MCP command lives once in the lane.
**Depends on:** L1, T1.
**Budget:** ~140k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k, the template 1k. `qa-ui-typescript.md` (3k to read, ~3k written), four Fix lines 3k, `inhouse-framework-conventions` (5k to read, ~5k written), `ui-tests.md` (0.7k to read, ~1.5k written), 20 R9 lists ~8k by script, R8 ×2 and R6 2k, the MCP command 3k. Five bodies: 23k to read and ~25k written. Gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py qa/typescript/agents qa/typescript/skills/inhouse-framework-conventions qa/typescript/skills/rules/ui-tests.md qa/typescript/skills/page-objects-from-url qa/typescript/skills/evidence-capture qa/typescript/skills/bdd-project-scaffold qa/typescript/skills/ui-test-author/review qa/typescript/skills/benchmarks qa/typescript/skills/failure-injection-testing qa/typescript/skills/security-testing qa/typescript/skills/data-driven-testing qa/typescript/skills/api-test-author/grpc <the 20 R9 skill folders below>`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'qa/typescript/'`.
Then run `python3 tools/qa-version-check.py`, and then `python3 tools/plugin-surface-check.py`.

- **`qa/typescript/agents/qa-ui-typescript.md`**
  - **R17, at `:16`.**
  - **R17, at `:27`.** The MCP command becomes a pointer to `page-objects-from-url`.
  - **The Fix line, at `:44`.**
  - **O20, at `:50`.**
  - **O21, at `:53`.**
- **The Fix line.** `qa/typescript/agents/qa-{api,bdd,desktop,mobile}-typescript.md`. Also apply it in `qa-llm-typescript.md` and `qa-performance-typescript.md` if they carry a Fix sweep in other words, which `grep -n "Fix" ` will show.
- **The MCP command, R17.** Its one home is `qa/typescript/skills/page-objects-from-url/SKILL.md`. `qa/typescript/skills/evidence-capture/SKILL.md` points at it.
- **`qa/typescript/skills/inhouse-framework-conventions/SKILL.md`**
  - **R17, at `:165–171, 237–, 251–`.**
  - **R19, at `:223–235`.**
  - **R21, at `:155`.** Write ``withPassword(`Wrong-${crypto.randomUUID()}`)``.
  - **O8, at `:134`.**
  - **O9, at `:208` and `:109–114`.**
- **R23.** `qa/typescript/skills/rules/ui-tests.md` (2,685 chars).
- **R8.** At `qa/typescript/skills/bdd-project-scaffold/SKILL.md:132` and `qa/typescript/skills/ui-test-author/review/SKILL.md:15`, name the skill that owns `references/config-and-fixtures.md` on the same line.
- **R6.** `qa/typescript/skills/benchmarks/SKILL.md`.
- **R2.** These are in `qa/typescript/skills/`:
  - `failure-injection-testing/SKILL.md` (20,074 chars)
  - `security-testing/passive-scan/SKILL.md` (19,766)
  - `security-testing/dependency-scan/SKILL.md` (17,020)
  - `data-driven-testing/SKILL.md` (16,824)
  - `api-test-author/grpc/SKILL.md` (16,353)
- **R9, in `qa/typescript/skills/`.**
  - `ai-feature-testing/references/details.md`
  - `analytics-testing/references/playwright.md`
  - `browser-cloud-setup/references/details.md`
  - `email-testing/references/{gmail-imap,mailosaur,mailpit,sendgrid-sandbox}.md`
  - `evidence-capture/references/playwright.md`
  - `file-storage-testing/references/{azure-blob,s3}.md`
  - `language-testing/references/details.md`
  - `messaging-testing/references/{kafka,rabbitmq,service-bus,sqs}.md`
  - `network-mocking/references/{playwright-routes,proxy}.md`
  - `payment-testing/references/stripe-api.md`
  - `realtime-stream-testing/references/details.md`
  - `test-login-tokens/references/details.md`
- **Not in P18:** `qa/typescript/skills/rules/SKILL.md` (T1), and `qa/_shared` (P16).

### P19 — qa/manual, qa/reporting, qa/cicd

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each path below gives `0 findings` under the lint. `qa-test-case-designer.md` and `qa-test-planner.md` are ≤ 14,000 chars. `test-plan-writer`'s description is ≤ 200 chars.
**Depends on:** L1, T1.
**Budget:** ~110k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k, the template 1k. `qa-feature-spec-writer.md` (3k to read, ~4k written), `qa-explorer.md` 2k, `cross-feature-test-design` and its references 4k, `connections.md` 1k, two R10 edits 2k. `qa-test-case-designer` (4k to read, ~4k written), `qa-test-planner` (3.7k to read, ~2k written), `test-plan-writer` description 1k, three reporting R8 lines 2k, six Fix lines 4k, nine `qa/cicd` R9 lists and `probes.md` ~6k, `probes.md`'s MCP command 1k. Gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py qa/manual qa/reporting qa/cicd`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'qa/manual/'`.
Then run `python3 tools/qa-version-check.py`, and then `python3 tools/plugin-surface-check.py`.

- **`qa/manual/agents/qa-feature-spec-writer.md`.** R13 at `:33`: Steps becomes the template table (`# | Step | Load | Done when`). R13 at `:100`: add `## Report` with a `Mode:` line.
- **`qa/manual/agents/qa-explorer.md:28, 39, 40`.** R8: the pointers become `qa/manual/app-exploration/references/probes.md` and `…/checks.md`.
- **`qa/manual/cross-feature-test-design/SKILL.md:21`.** R8: name the owner on the line, as `:11` does.
- **O3.**
  - `qa/manual/cross-feature-test-design/SKILL.md:28, 30`
  - `qa/manual/cross-feature-test-design/references/example-cancel-booking.md:9, 76, 103`
  - `qa/manual/requirements-breakdown/references/connections.md:9`
- **R10.** `qa/manual/test-plan-writer/SKILL.md:130` and `qa/manual/test-strategy/SKILL.md:166`.
- **R2.** The description of `qa/manual/test-plan-writer/SKILL.md` (232 chars), and the agents `qa/manual/agents/qa-test-case-designer.md` (16,323 chars, plus its Fix line) and `qa/manual/agents/qa-test-planner.md` (14,847).
- **`qa/manual/app-exploration/references/probes.md`.** R9. R17: the MCP command becomes a pointer to the lane's `page-objects-from-url`.
- **R8.** At `qa/reporting/{dotnet:171,java:178,typescript:163}`, in `skills/test-reports/SKILL.md`, the path becomes `qa/<stack>/skills/ui-test-author/playwright/references/trace-correlation.md`.
- **The Fix line.** `qa/reporting/agents/qa-reporting-{dotnet,java,typescript}.md` and `qa/cicd/agents/qa-cicd-{dotnet,java,typescript}.md`.
- **R9.** `qa/cicd/{dotnet,java,typescript}/skills/ci-pipelines/references/{azure-pipelines,github-actions,gitlab-ci}.md`.
- **Not in P19:** the lane plugins' own skills (P14–P18).

### P20 — business-analysis, training-data, tooling, and `/dev:refine`

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each path below gives `0 findings` under the lint. `business-model.md` is ≤ 6,000 chars, and the three backlog rule files are ≤ 2,500. `requirements-author` is registered as O10 answered, with the catalog and README rows matching.
**Depends on:** L1, T1.
**Budget:** ~130k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k, the template 1k. `requirements-author.md` (3k to read, ~3k written) and `business-analyst.md` (2.6k to read, ~2k written). `ba-project-memory` (3.6k to read, ~4k written), with `kb-lint.py` read 2k. `example-dependency-map.md` 2k. Four rule files: 4k to read and ~4k written. `dataset-engineer.md` and `dataset-auditor.md` 4k, `td-dataset-formats` (2.7k to read, ~3k written), `tooling-engineer.md` (2.2k to read, ~2k written), `mcp-builder` 1k, `capability-contract` (2.9k to read, ~3k written). Under O10 (a), `marketplace.json`, the catalog and README edits ~10k. Gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py business-analysis/agents business-analysis/skills/ba-project-memory business-analysis/skills/ba-dependency-map business-analysis/skills/rules/business-model.md business-analysis/skills/rules/backlog-stories.md business-analysis/skills/rules/backlog-epics.md business-analysis/skills/rules/backlog-requirements.md training-data/agents training-data/_shared/td-dataset-formats tooling/agents/tooling-engineer.md tooling/skills/mcp-builder tooling/_shared/capability-contract`.
Then run `wc -c business-analysis/skills/rules/*.md`.
Then run `python3 tools/plugin-surface-check.py`. It must give `OK`, and after an O10 (a) move it is the check of the new registration.

- **`business-analysis/agents/requirements-author.md`**
  - **R17, at `:14–30`.** Two lines, the audit's.
  - **R15, at `:56`.** AUDIT mode gets a done-when.
  - **R17, at `:67`.** Write "every section of `ba-scoping-writeup`'s format, in order".
  - **R18, at `:36, 74, 86`.**
  - **O10.** Under (a), move `refine` from `engineering-practices/commands/refine.md` into the business-analysis plugin's commands, register it and the agent in `business-analysis` in `.claude-plugin/marketplace.json`, remove both from `dev`, and update their rows in `docs/skills-catalog.md` and `README.md`. Under (b), list what `dev` must bundle, and bundle it.
- **`business-analysis/agents/business-analyst.md`.** R17 at `:38` and `:52` (write "every class in the `ba-feature-conflict-check` taxonomy"); R18 at `:19` and `:60`; the Fix line at `:56`.
- **`business-analysis/skills/ba-project-memory/SKILL.md`**
  - **R17, at `:34–58`.** Write "Read and update per `business-model.md`".
  - **R17, at `:66–111`.** Point at `kb-lint.py`. First run `python3 business-analysis/skills/ba-project-memory/scripts/kb-lint.py --help`, to confirm what it checks.
  - **R16, at `:116–131`.**
  - **R19, at `:52`.**
  - **O3, at `:116`.**
- **`business-analysis/skills/ba-dependency-map/references/example-dependency-map.md:27, 38, 39, 79, 91`.** R10: each marker goes in a code span.
- **R23.** `business-analysis/skills/rules/business-model.md` (6,909 chars), `backlog-stories.md` (4,065), `backlog-epics.md` (2,646) and `backlog-requirements.md` (2,541).
- **`training-data/agents/dataset-engineer.md`.** R17 at `:23`; R19 at `:18`; the Fix line at `:45`.
- **`training-data/agents/dataset-auditor.md:60`.** R13: add `## Report` with a `Mode:` line.
- **`training-data/_shared/td-dataset-formats/SKILL.md`**
  - **R17, at `:13, 31–33, 52–58, 81, 96, 102–105, 124–134`.**
  - **R16, at `:60–98`.**
  - **R19, at `:22, 113, 134`.**
  - **O24, at `:22–23`.**
- **`tooling/agents/tooling-engineer.md`.** R17 at `:44`; R18 and R19 at `:17` and `:19`; the Fix line at `:51`; O18 on its `Gate evidence` line, which names coverage (found by grep, not in 004).
- **`tooling/skills/mcp-builder/SKILL.md:11`.** R12: name the `tooling-engineer` agent, or the path `tooling/_shared/capability-contract`.
- **`tooling/_shared/capability-contract/SKILL.md`.** R17 at `:71–75, 112–115, 132–134, 149–151`; R15 at `:25–153`; R19 at `:9, 119, 150`; O23 at `:149`.
- **Not in P20:** the `business-analysis`, `training-data` and `tooling` `rules` skills (T1), and `tooling/skills/rules/tool-contract.md` unless O23 (b).

### G1 — Gate: the whole library once more, then filing

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `python3 tools/skill-lint.py` over the whole library gives `0 findings`. The only exception is the lines of an O the owner deferred, and `Status:` names each one. `token-audit.py --violations-only` exits 0. `plugin-surface-check.py` and `qa-version-check.py` give `OK`, and the lint's tests are green. The plan is filed.
**Depends on:** L1, T1, P1–P20.
**Budget:** ~110k. `CLAUDE.md` 25k, this plan's `As built` notes 15k, tool output summarised 10k, fixes ~30k, the read of new references and pointers ~20k, plan edits 6k.
**Gate (this is the last runnable task, so it runs the whole set once more across the plan, in order):** the commands in §4.

- Run the whole set once. Fix each failure with its narrowest command, for example
  `python3 tools/skill-lint.py <path>`. Rerun only what failed, then run the whole set once more
  (plan-format §5).
- Read every `references/*.md` file the plan created, and every pointer added beside a moved section.
  Each must land on a real heading or line.
- Collect every "found outside my paths" item from the `As built` notes, and fix each one in place.
- Name in `Status:` every deferred O and every `D<n>` (D3) where a body is still over budget.
- Add each touched skill's per-file char count to `As built`. Get it from `wc -c` on the files that
  `git diff --name-only` lists.
- **Not in G1:** new findings outside 004's rules. They go into a round-2 audit, not into this plan.

## Close-out — every task

Before you stop, in this order, in this file. Another task may be running in this working tree:
re-read this file immediately before these edits, and touch only your own task block, your own prompt
block and the line that says which have landed.

1. **As built** — append a dated `**As built (YYYY-MM-DD):**` bullet to your task block: what differed
   from the plan, the ids and names you assigned, what is built but unverified, and the `file:line` or
   command output that proves the deliverable exists. Never edit an earlier note.
2. **Decisions** — where you built something differently from the plan, append a dated `D<n>` to
   `## Decisions` with both readings. A divergence is recorded, never absorbed.
3. **The blocks below yours** — rewrite, in place, every prompt block whose assumptions your work
   changed (a renamed file, a changed signature, a moved gate), and write any block left
   `Blocked on <your id>` from what you now know.
4. **Status** — rewrite the header `**Status:**` line: what is built, what is next, what is built but
   unverified. When a task is running beside you, leave it: the next task that waits for you rewrites it.
5. **Commit the work** — the code, its tests and these plan edits together, on the current branch (under
   Plan Queue, the plan's branch in its worktree; never check out the default branch), adding only your
   own files, by path — never `git add -A`. Your prompt block is still in the plan.
6. **Merge, gate task only** — if you are the task that ran the whole set and this plan runs on its own
   branch, merge the default branch into it now, resolve every conflict by keeping both sides' rows,
   re-run the failing suites if code conflicted, and commit the merge, so the plan merges back cleanly
   and the documentation task after you documents the merged code.
7. **Your own block** — only now delete it, and update the line above the blocks that says which have
   landed, in a follow-up commit of its own: `docs: delete <id>'s prompt (<plan>)`. Do not stop between
   the two commits. Stopping mid-task: keep it, with a `Picking up from:` line. Blocked: keep it, naming
   the blocker and its owner. When the queue says other tasks of this plan are running beside you, do
   not commit, stash, reset or check out at all: make this deletion your last edit, and the queue
   commits the work and the deletion together.
8. **Filing** — if your deletion left no blocks, rewrite `**Status:**` one final time (what the plan
   delivered, what is still unverified), `git mv` this plan into `docs/plans/implemented/`, same name and
   number — a `solution-planner` pack moves its whole initiative folder — and add its row to that
   folder's README where there is one, in the same follow-up commit.

## Prompts — one per task

Run them in order, one session each. Each block is complete on its own. Every gate runs locally, in the
session that runs the task. No prompt edits a file outside the paths it names (§2 item 9).

- L1 runs first and waits for the owner's answers.
- T1 runs alone after L1.
- After T1, P1–P20 run side by side, three at a time. Their files are disjoint.
- G1 waits for every P task.

| # | Stack | Agent | Depends on | Runs beside | Budget |
|---|---|---|---|---|---|
| — | answer O1–O24, in reply to L1's question | **the user** | — | — | — |
| L1 | `docs` | `general-purpose` | none | — | ~55k |
| T1 | `docs` | `general-purpose` | L1 | — | ~135k |
| P1 | `docs` | `general-purpose` | L1, T1 | P2–P20 (three at a time) | ~115k |
| P2 | `docs` | `general-purpose` | L1, T1 | P1, P3–P20 | ~105k |
| P3 | `docs` | `general-purpose` | L1, T1 | P1–P2, P4–P20 | ~120k |
| P4 | `docs` | `general-purpose` | L1, T1 | P1–P3, P5–P20 | ~125k |
| P5 | `docs` | `general-purpose` | L1, T1 | P1–P4, P6–P20 | ~125k |
| P6 | `docs` | `general-purpose` | L1, T1 | P1–P5, P7–P20 | ~125k |
| P7 | `docs` | `general-purpose` | L1, T1 | P1–P6, P8–P20 | ~100k |
| P8 | `docs` | `general-purpose` | L1, T1 | P1–P7, P9–P20 | ~120k |
| P9 | `docs` | `general-purpose` | L1, T1 | P1–P8, P10–P20 | ~125k |
| P10 | `docs` | `general-purpose` | L1, T1 | P1–P9, P11–P20 | ~110k |
| P11 | `docs` | `general-purpose` | L1, T1 | P1–P10, P12–P20 | ~125k |
| P12 | `docs` | `general-purpose` | L1, T1 | P1–P11, P13–P20 | ~115k |
| P13 | `docs` | `general-purpose` | L1, T1 | P1–P12, P14–P20 | ~110k |
| P14 | `docs` | `general-purpose` | L1, T1 | P1–P13, P15–P20 | ~125k |
| P15 | `docs` | `general-purpose` | L1, T1 | P1–P14, P16–P20 | ~110k |
| P16 | `docs` | `general-purpose` | L1, T1 | P1–P15, P17–P20 | ~125k |
| P17 | `docs` | `general-purpose` | L1, T1 | P1–P16, P18–P20 | ~140k |
| P18 | `docs` | `general-purpose` | L1, T1 | P1–P17, P19–P20 | ~140k |
| P19 | `docs` | `general-purpose` | L1, T1 | P1–P18, P20 | ~110k |
| P20 | `docs` | `general-purpose` | L1, T1 | P1–P19 | ~130k |
| G1 | `docs` | `general-purpose` | L1, T1, P1–P20 | — | ~110k |

No task has landed. All 23 prompts are live.

---

### L1 — the owner's answers to O1–O24 (general-purpose, docs)

````
Depends on: none
Agent: general-purpose · Stack: docs

Task L1 of docs/plans/015-skill-authoring-remediation.md. Get the owner's answers to the 24 logical
conflicts the audit found, and record them so that each later task applies its own.

Read, in this order:
1. The plan: §3, §5 (the Open questions table, O1–O24), D1, task L1, and "Close-out — every task".
2. The task table under "## Prompts — one per task".

Do:
- Ask the owner every question in §5 in ONE message. For each one, give the number, the question in a
  sentence, readings (a) and (b), and "recommended: (a)". Then stop and wait for the reply. Under Plan
  Queue, end with the question and the line `PLAN_QUEUE: QUESTION`.
- When the answers arrive, add `## Answered questions (<date>)` directly after `## 6. Decisions`. Give
  one line per answer: `**O<n> — <question in a few words>: <answer>.**`. Delete each answered row from
  the Open questions table. A row the owner defers stays, with "deferred" added to its Blocks cell.
- An answer that is neither (a) nor (b): write the exact edit into each prompt block that §5's Blocks
  column names, in place.
- If O1 (b), O3 (b) or O4 (b) is chosen, write task T2 after T1. Its stack is `infra`, its agent
  `general-purpose`, and it depends on L1. Its deliverable is `tools/skill-lint.py` implementing the
  chosen readings, with a fixture each in `tools/fixtures/skill-lint/`. Its gate is
  `python3 -m pytest tools/test_skill_lint.py -q` and
  `python3 -m coverage run --branch -m pytest tools/test_skill_lint.py -q && python3 -m coverage report --include=tools/skill-lint.py`
  at ≥ 80% branch.
  - Under O1 (b), T2 also rewrites as a full path every Load-cell pointer that only D16's reading
    resolved, listed with the stricter lint.
  - Add T2's row to the task table and its prompt block after T1's, and add `T2` to every P block's
    `Depends on:` line.
- If O12 (b) is chosen, move O12's edit out of P5–P9 and into P1's block. That block then edits
  plan-format §5 (`:204, 276`) and `CLAUDE.md` "Planning".

Traps:
- Edit no skill. Record answers and rewrite prompt blocks only.
- Never answer a question yourself. Never treat silence as (a).

Gate: none. It records decisions.

Commit: `docs(plans): 015 L1 — the owner's answers to O1–O24`.
Close out per the plan's "Close-out — every task" before you stop.
````

### T1 — the agent template, the standard, and the 23 rules skills (general-purpose, docs)

````
Depends on: L1
Agent: general-purpose · Stack: docs

Task T1 of docs/plans/015-skill-authoring-remediation.md. Fix the shared shapes that the per-plugin
tasks copy: the agent template, the standard's own R8 and R20 rows, and the 23 `rules` skills.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table (R2, R7, R8, R11, R15–R20) and
   "Leading words".
2. The plan: §2, `## Answered questions` (O1, O3, O4, O5, O18), D2, D4, task T1, and
   "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md: the rows whose Location starts "all 23 `rules`",
   "19 of 23", "21 `rules`" or "22 `rules`" (Code issues, "Judgment, the front doors"), the
   `.skill-template/agent.md` Fix row (Code issues A4), and the `Gate evidence` row (Logical conflicts
   A4).
4. .skill-template/agent.md, then engineering-practices/rules/SKILL.md as the model for step 2's form.

Fix, by path:
- .skill-template/agent.md:33, R15. Fix ends "…then sweep: every sibling sharing the defect's pattern
  fixed or listed in the report".
- .skill-template/agent.md:51, O18. Under (a): `Gate evidence: <the Gate: line's commands and results>`.
  Under (b): add "coverage, outside a plan task".
- engineering-practices/writing-for-agents/SKILL.md:102, O1. Under (a), R8 reads "…exists relative to
  that file's folder, or inside a skill named in a code span on the same line or the line above".
- engineering-practices/writing-for-agents/SKILL.md:73 and :114, O5. One list, pointed at.
- Under O3 (b) or O4 (b): the R11 row of the standard states the exception.
- The 23 rules SKILL.md files:
  - backend/{dotnet,java,node,python,rust}/skills/rules/SKILL.md
  - business-analysis/skills/rules/SKILL.md
  - data/rules/SKILL.md
  - design/rules/SKILL.md
  - desktop/{macos,windows}/skills/rules/SKILL.md
  - devops/rules/SKILL.md
  - engineering-practices/rules/SKILL.md
  - frontend/{blazor,react}/skills/rules/SKILL.md
  - mobile/{android,ios,react-native}/skills/rules/SKILL.md
  - qa/{dotnet,java,typescript}/skills/rules/SKILL.md
  - security/rules-security-governance/SKILL.md
  - tooling/skills/rules/SKILL.md
  - training-data/skills/rules/SKILL.md

  In each:
  - R2. Applies to all but design, business-analysis, desktop/macos and desktop/windows. Drop the
    description's parenthetical list, and keep the trigger and the sibling.
  - R7 (D4). Add `## When to use` with "installing or updating the rules", and `## When NOT to use`
    with "writing code: the rule files apply themselves".
  - R17. Drop the rule-file table's "Loads when" column and its glosses.
  - R17, step 2. Applies to all but dev and tooling. Replace the hard-coded count with the form at
    engineering-practices/rules/SKILL.md:32.
  - R15. Steps 3, 4, 5 and 7 get a done-when. Step 3: "every source file is in the target". Step 5:
    "every file each command lists is matched by an installed glob, or a glob is proposed for it".
    Step 7: "each contradiction listed, or the report says none".
  - R16. The unattended paragraph becomes one sentence inline, and the rest goes under the step it
    governs.
  - R19. Delete "A person types `/<plugin>:rules`.". In all but tooling, also delete the clause "so a
    session that never touches … never pays for …".
  - R18. Delete "Never guess the answer.".

Traps:
- Re-read each row at its line first (§2 item 1). A file whose shape differs from the group's gets its
  own fix, named in As built.
- The rule files beside each SKILL.md are NOT yours (R23 belongs to the P tasks), and neither is any
  agent. 014's plan is filed: never edit it.

Gate: own tests.
  python3 tools/skill-lint.py engineering-practices/writing-for-agents backend/dotnet/skills/rules/SKILL.md backend/java/skills/rules/SKILL.md backend/node/skills/rules/SKILL.md backend/python/skills/rules/SKILL.md backend/rust/skills/rules/SKILL.md business-analysis/skills/rules/SKILL.md data/rules/SKILL.md design/rules/SKILL.md desktop/macos/skills/rules/SKILL.md desktop/windows/skills/rules/SKILL.md devops/rules/SKILL.md engineering-practices/rules/SKILL.md frontend/blazor/skills/rules/SKILL.md frontend/react/skills/rules/SKILL.md mobile/android/skills/rules/SKILL.md mobile/ios/skills/rules/SKILL.md mobile/react-native/skills/rules/SKILL.md qa/dotnet/skills/rules/SKILL.md qa/java/skills/rules/SKILL.md qa/typescript/skills/rules/SKILL.md security/rules-security-governance/SKILL.md tooling/skills/rules/SKILL.md training-data/skills/rules/SKILL.md
    → 0 findings
  python3 tools/token-audit.py --violations-only | grep -E 'rules/SKILL.md|rules-security-governance/SKILL.md'   → prints nothing
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 T1 — agent template, standard R8/R20, the 23 rules skills`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P1 — dev: the planning and verification front doors (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P1 of docs/plans/015-skill-authoring-remediation.md. Fix audit 004's findings in dev's planning
and verification front doors.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R2, R7, R8, R15–R21, R23.
2. The plan: §2, `## Answered questions` (O2, O6, O12), task P1, and "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md. Find each row by grepping its path below; its Suggested fix
   is the fix.
4. engineering-practices/writing-plans/references/plan-format.md §4, §5 and §7: the targets of the
   pointers you write.

Fix, by path and rule:
- engineering-practices/writing-plans/SKILL.md (25,316 chars):
  - R2.
  - :3, Data: "(design)" becomes "(feature)".
  - :156–158 and :311, O2.
  - R7.
  - :68, 91, 108, 154, 174, 239, R15: steps 1–6 each get a done-when.
  - :253 with :136–145 and :279–287, R17: one-line pointers to plan-format §5 and §7 and to
    rules/plans.md.
  - :14 and :98–99, R19.
  - :82–89 and :341–344, R16: behind "a web route in the plan → read …".
  - :38 and :297–344, R20: "task reports"; the self-review items become criteria.
- engineering-practices/writing-plans/references/plan-format.md: R9.
- engineering-practices/systematic-debugging/SKILL.md:
  - :3, Data: "(design)" becomes "(feature)".
  - R7.
  - :22, 90, 112, 183–184, R15.
  - :60–75, R21.
  - :44–78, R16.
  - :27, 36, 105, 131, 148–149, R18.
  - :16, 28, 100, R19.
  - :181, R20: the column becomes "Done when".
- engineering-practices/verify-before-done/SKILL.md:
  - R7.
  - :18, R20: "The evidence check".
  - :12 and :106–112, R19.
- engineering-practices/quality-constraints/SKILL.md:
  - :33, 34, 36, 38–40, R17.
  - :45, R15.
  - :10, 17, 42, 45, R20.
  - :12, R19.
  - :32 and :39, O6.
- engineering-practices/source-grounding/SKILL.md:
  - :27, 37, 52, 56, R15.
  - :48, R18.
  - :10 and :71–74, R19.
- engineering-practices/notebooklm/SKILL.md:
  - :23 and :40, R8: point into engineering-practices/bundled/notebooklm/scripts/.
  - R7.
  - :22–25, R15.
  - :54, R17.
  - :8, R19.
- engineering-practices/brainstorming/SKILL.md:
  - :62–64, R17.
  - :20, R20: "design approval".
- engineering-practices/rules/plans.md (8,206 chars), R23: keep the constraints, and point at
  plan-format for the procedure. Keep its `paths:`.
- Only under O12 (b): plan-format.md:204, 276 and CLAUDE.md "Planning", with the wording L1 recorded.

Traps:
- Re-read each row at its line before editing (§2 item 1). The line numbers are mostly unverified.
- R2 is met by R16 moves and R17/R19 deletions only (D3). A rule only writing-plans states stays.
- engineering-practices/rules/SKILL.md is T1's, and rules/feature-docs.md is P4's: do not edit them.

Gate: own tests.
  python3 tools/skill-lint.py engineering-practices/writing-plans engineering-practices/systematic-debugging engineering-practices/verify-before-done engineering-practices/quality-constraints engineering-practices/source-grounding engineering-practices/notebooklm engineering-practices/brainstorming engineering-practices/rules/plans.md   → 0 findings
  python3 tools/token-audit.py --violations-only | grep -E 'writing-plans|systematic-debugging|verify-before-done|quality-constraints|source-grounding|notebooklm|brainstorming'   → prints nothing
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P1 — dev planning and verification front doors`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P2 — dev: the audit front doors and the unregistered skills (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P2 of docs/plans/015-skill-authoring-remediation.md. Fix audit 004's findings in the two audit
front doors, the audit engine, the five unregistered skills and code-auditor.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R2, R3, R4, R7, R13,
   R15–R19.
2. The plan: §2, `## Answered questions` (O22), D5, task P2, and "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md. Find each row by grepping its path below.
4. engineering-practices/rules/audits.md (the target of the R17 pointers), and .skill-template/agent.md
   `## Report`.

Fix, by path and rule:
- engineering-practices/spec-vs-code-audit/SKILL.md:
  - R2.
  - :147, 151, 175–177, 241–243, R15.
  - :111, 114, 165–173, 247, 262–268, 333–339, R17: point at audits.md:15–27, and keep the verdict
    table and the templates.
  - :237–339, R16: Mode B moves to references/re-audit.md, behind "a register and a prior report exist".
  - :10, 51, 343, 345, R19.
- engineering-practices/feature-audit/SKILL.md:
  - R2.
  - :80, 84, 112, 175, R15.
  - :100–108, 183, 187, 207, 285–289, R17: point at audits.md, and keep "Typical here".
  - :177–289, R16: references/re-audit.md, behind "a prior report exists".
  - :10, 50, 295, R19.
- engineering-practices/standards-audit-engine/SKILL.md:
  - :3, Data and R4: "Use when a stack's `standards-audit` skill (`/<plugin>:audit`) or the
    `design-auditor` starts a conformance round."
  - :120–127, R17: severities per CLAUDE.md "Review behavior"; keep the impact-qualifier rule.
  - :158–164, R19.
  - :3 and :10–16, O22.
- D5 (R7, R3): add `disable-model-invocation: true` to the frontmatter of each of these:
  - engineering-practices/agent-orientation-cache/SKILL.md
  - engineering-practices/code-comments/SKILL.md
  - engineering-practices/standards-audit-engine/SKILL.md
  - ai-development/claude-api/SKILL.md
  - ai-development/mcp-builder/SKILL.md
- engineering-practices/agents/code-auditor.md:51, R13: the template's `## Report` block with a
  `Mode:` line.

Traps:
- Re-read each row at its line first (§2 item 1).
- Mode B moves whole, with its done-whens. Keep the pointer naming the condition in the SKILL.md.
- audits.md is read-only to this task.

Gate: own tests.
  python3 tools/skill-lint.py engineering-practices/spec-vs-code-audit engineering-practices/feature-audit engineering-practices/standards-audit-engine engineering-practices/agent-orientation-cache engineering-practices/code-comments ai-development/claude-api ai-development/mcp-builder engineering-practices/agents/code-auditor.md   → 0 findings
  python3 tools/token-audit.py --violations-only | grep -E 'spec-vs-code-audit|feature-audit'   → prints nothing
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P2 — dev audit front doors, audit engine, unregistered skills`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P3 — dev: delivery-plan, session-budget, experience-plan (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P3 of docs/plans/015-skill-authoring-remediation.md. Bring delivery-plan and session-budget under
budget, and clear the rest of their findings.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R2, R9, R10, R16, R17, R19,
   R20.
2. The plan: §2, `## Answered questions` (O2), D3, task P3, and "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md: the rows for backend/_shared/delivery-plan (Code issues
   A4, "The sample"), and its :687 row (Data issues A4).
4. engineering-practices/writing-plans/references/plan-format.md §3, §4, §5 and §7: the targets of
   the pointers.

Fix, by path and rule:
- backend/_shared/delivery-plan/SKILL.md (73,093 chars):
  - R2.
  - :51–67, 359–369, 510–512, 614–623, R17: one sentence plus "plan-format §5".
  - :343–381 and :439–451, R17: keep Epic, Story, Stream, Order, Skills, Files and the routing map,
    and cite §4 for the rest.
  - :18–48 and :145, R17: one pointer line, keeping the epic/story binding.
  - :486–489, 559, 614–625, R17: "copy plan-format §7 verbatim".
  - :9–35, R19.
  - :125, 175, 205, R20: `Not in <id>`.
  - :157–227, R16: references/shape-<name>.md, behind "Sequencing shape: <name>".
  - :563–598, R16: references/reconcile.md, behind "a plan and partly built code both exist".
  - :687, Data and O2.
- backend/_shared/delivery-plan/references/example-delivery-plan.md: R9.
- backend/_shared/session-budget/SKILL.md (16,907 chars): R2.
- backend/_shared/session-budget/references/prompts-section-template.md: R9.
- backend/_shared/experience-plan/SKILL.md:
  - R2: the description is 246 chars.
  - :159, R10: the marker goes in a code span.

Traps:
- Re-read each row at its line first (§2 item 1). 014 A4 confirmed that :88 and :421 resolve; leave
  them.
- delivery-plan's own additions to plan-format stay. Only the restatements go.
- The other backend/_shared skills are P4's.

Gate: own tests.
  python3 tools/skill-lint.py backend/_shared/delivery-plan backend/_shared/session-budget backend/_shared/experience-plan   → 0 findings
  python3 tools/token-audit.py --violations-only | grep -E 'delivery-plan|session-budget|experience-plan'   → prints nothing
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P3 — delivery-plan, session-budget, experience-plan`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P4 — dev: solution-blueprint, business-documentation, feature-trace and the documenting agents (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P4 of docs/plans/015-skill-authoring-remediation.md. Bring the planning and documenting skills and
agents under budget, and clear their lint findings and feature-docs.md's R23.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R2, R3, R8, R9, R12, R13,
   R16, R17, R23.
2. The plan: §2, D3, task P4, and "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md. Find each row by grepping its path below.
4. .skill-template/agent.md (`## Report`, and the Fix line as T1 left it).

Fix, by path and rule:
- backend/_shared/solution-blueprint/SKILL.md (30,276 chars): R2.
- backend/_shared/business-documentation/SKILL.md (27,914 chars): R2, R3.
- backend/_shared/business-documentation/references/example-area.md:82, 139, 233, 234, R8:
  `bookings.md` and `scheduling.md` are sample file names. Make the lint read them as patterns, or write
  them without backticks.
- backend/_shared/feature-trace/references/trace-recipes.md: R9.
- backend/_shared/agents/be-documenter.md (17,599 chars): R2.
- backend/_shared/agents/solution-planner.md (16,835 chars):
  - R2.
  - :68, R12: name the path to Read, `backend/_shared/delivery-plan`.
- backend/_shared/agents/be-feature-documenter.md:89, R13: `## Report` with a `Mode:` line.
- engineering-practices/rules/feature-docs.md (10,500 chars), R23: keep the constraints. Move the
  document's shape and procedure (:9–40) into the skill that be-feature-documenter's Load cells name
  for the shape, and leave a one-line pointer. Keep its `paths:`.

Traps:
- Re-read each row at its line first (§2 item 1).
- An agent over 14,000 loses restatements and branch material to its skills' references/, never a
  step or a boundary.
- delivery-plan, session-budget and experience-plan are P3's. engineering-practices/rules/SKILL.md is
  T1's.

Gate: own tests.
  python3 tools/skill-lint.py backend/_shared/solution-blueprint backend/_shared/business-documentation backend/_shared/feature-trace backend/_shared/agents/be-documenter.md backend/_shared/agents/solution-planner.md backend/_shared/agents/be-feature-documenter.md engineering-practices/rules/feature-docs.md   → 0 findings
  python3 tools/token-audit.py --violations-only | grep -E 'solution-blueprint|business-documentation|be-documenter|solution-planner'   → prints nothing
  wc -c engineering-practices/rules/feature-docs.md   → ≤ 6,000
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P4 — blueprint, business-documentation, documenting agents, feature-docs rule`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P5 — design and fe-blazor (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P5 of docs/plans/015-skill-authoring-remediation.md. Fix audit 004's findings in design and
fe-blazor.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R2, R3, R8, R13, R15–R20.
2. The plan: §2, `## Answered questions` (O11, O12, O18), task P5, and "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md. Find each row by grepping its path below; group rows that
   name fe-blazor among many agents are in "Agents, shared defects".
4. .skill-template/agent.md as T1 left it (the Fix line, `Gate evidence`, "Read the rules").

Fix, by path and rule:
- design/agents/design-auditor.md:
  - :74, R8: engineering-practices/standards-audit-engine/references/report-template.md.
  - :94, R13: `## Report` with `Mode:`.
  - :73 and :75, R15.
  - :18, R17: "the skills in the Sections table".
  - :17, R16: the Chrome protocol moves to design/ux-review/references/claude-in-chrome.md (ux-review
    is the live-UI skill the Sections table loads). Leave a pointer that names the condition "driving
    Claude in Chrome → read …".
  - :16, 17, 20, R18.
- R8, with the target design/ui-ux-pro-max/references/pro-rules.md:
  - design/design-tokens/SKILL.md:23
  - design/iconography/SKILL.md:23
  - design/motion/SKILL.md:23
  - design/ux-patterns/SKILL.md:31
  - design/visual-identity/SKILL.md:32
- design/visual-identity/SKILL.md:
  - :17, R17: drop every count.
  - :75–90, R15.
  - :48–52, 64–70, 106–115, R17.
  - :9, 88, 94, 96, R19.
  - :7, R20: "# Visual identity".
  - :73, 79, 88, 108, O11.
- design/prototype/SKILL.md:
  - :32 and :49–57, R16: references/in-app-handoff.md.
  - :8, R19.
- frontend/blazor/agents/fe-blazor.md:
  - :20, R17: the template's rules wording.
  - :34 and :36, R15.
  - :34, O11.
  - :16, R17: one sentence plus backend/_shared/experience-plan/references/rendering-strategy.md.
  - :14 and :16, R19.
  - The Fix line: T1's wording.
  - :65, O18.
- R2: frontend/blazor/skills/ui-rules/SKILL.md (21,122 chars) and frontend/blazor/skills/basics/SKILL.md
  (18,619).
- auth/auth0-blazor/SKILL.md (16,035 chars): R2, R3.
- frontend/blazor/skills/accessibility/SKILL.md:11, R8.
- frontend/blazor/skills/component-testing/SKILL.md:116 and :127, O12.

Traps:
- Re-read each row at its line first (§2 item 1).
- design/rules and frontend/blazor/skills/rules are T1's. standards-audit-engine is P2's.
- Under O11 (a) the agents name no count. They point at visual-identity's Calibration.

Gate: own tests.
  python3 tools/skill-lint.py design/agents/design-auditor.md design/design-tokens design/iconography design/motion design/ux-patterns design/visual-identity design/prototype design/ux-review frontend/blazor/agents/fe-blazor.md frontend/blazor/skills/ui-rules frontend/blazor/skills/basics frontend/blazor/skills/accessibility frontend/blazor/skills/component-testing auth/auth0-blazor   → 0 findings
  python3 tools/token-audit.py --violations-only | grep -E 'frontend/blazor|auth0-blazor'   → prints nothing
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P5 — design and fe-blazor`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P6 — fe-react (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P6 of docs/plans/015-skill-authoring-remediation.md. Fix audit 004's findings in fe-react.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R2, R3, R6, R9, R15–R21.
2. The plan: §2, `## Answered questions` (O11, O12, O14, O18), task P6, and "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md: the error-handling rows ("The sample"), its O14 row, and the
   rows naming fe-react.
4. frontend/react/skills/rules/react.md:65 and frontend/react/skills/rules/react-data.md:20, 24, as the
   R17 targets. Also .skill-template/agent.md as T1 left it.

Fix, by path and rule:
- frontend/react/skills/error-handling/SKILL.md (33,390 chars):
  - R2.
  - :45, 49, 72–73, 130–135, 159–165, 188–194, 214–228, R21: caption "Wrong:" and "Right:" in prose.
  - :77–79, 199, 245–256, 304–318, R17.
  - :322–344, R15.
  - :256, R19.
  - :101–108 and :280–286, R16.
  - :221–229 and :124–135, O14.
- R2, in frontend/react/skills/:
  - ui-rules/SKILL.md (23,086 chars)
  - data-fetching/SKILL.md (20,054)
  - basics/SKILL.md (17,124)
  - animation/SKILL.md (16,679)
- R9:
  - frontend/react/skills/data-grid/references/feature-recipes.md
  - frontend/react/skills/standards-audit/references/conformance-checklist.md
- frontend/react/skills/component-testing/SKILL.md:
  - R6.
  - :152 and :161, O12.
- frontend/react/agents/fe-react.md:
  - :24, R17.
  - :36 and :38, R15.
  - :19 and :36, O11.
  - :18, R17: one sentence plus the rendering-strategy.md pointer.
  - :19, R17: delete the invariant.
  - The Fix line.
  - :65, O18.
- auth/auth0-react/SKILL.md: R3.

Traps:
- Re-read each row at its line first (§2 item 1).
- The examples must still obey CLAUDE.md "Frontend code rules (React)" once their comments go. Make
  them right, not shorter.
- rules/react.md changes only under O14 (b). The rules SKILL.md is T1's.

Gate: own tests.
  python3 tools/skill-lint.py frontend/react/agents/fe-react.md frontend/react/skills/error-handling frontend/react/skills/ui-rules frontend/react/skills/data-fetching frontend/react/skills/basics frontend/react/skills/animation frontend/react/skills/data-grid frontend/react/skills/standards-audit frontend/react/skills/component-testing auth/auth0-react   → 0 findings
  python3 tools/token-audit.py --violations-only | grep -E 'frontend/react'   → prints nothing
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P6 — fe-react`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P7 — mobile-react-native, mobile-ios, mobile-android (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P7 of docs/plans/015-skill-authoring-remediation.md. Fix audit 004's findings in the three mobile
plugins.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R2, R3, R9, R15–R20.
2. The plan: §1 (the coverage-in-a-task row), §2, `## Answered questions` (O11, O12, O18), task P7,
   and "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md: the rows naming mobile-react-native, mobile-ios,
   mobile-android or mobile/android/skills/unit-testing.
4. .skill-template/agent.md as T1 left it, and mobile/android/skills/rules/android-tests.md (an R17
   target).

Fix, by path and rule:
- mobile/react-native/agents/mobile-react-native.md:
  - :21, R17.
  - :16, R17.
  - :35 and :37, R15.
  - :35, O11.
  - :12, R18.
  - The Fix line.
  - :65, O18.
- mobile/ios/agents/mobile-ios.md:
  - :16, R17: keep "a view in a folder no glob covers".
  - :17 and :39, R17.
  - :30 and :32, R15.
  - :30, O11.
  - :12, R18.
  - The Fix line.
  - :60, O18.
- mobile/android/agents/mobile-android.md:
  - :17, Data: "below the `store-compliance` target is a finding", with no number.
  - :16, :3 and :17, R17.
  - :30, 32, 34, R15.
  - :12, R18.
  - The Fix line.
  - :60, O18.
- mobile/android/skills/unit-testing/SKILL.md (16,505 chars):
  - R2.
  - :11, 20–22, 135, 183, Data.
  - :75–78 and :95–97, R17.
  - :210–215, R15.
  - :113–163 and :173–208, R16: references/compose-ui-tests.md and references/coverage-kover.md.
  - :96–97, R20.
  - :180, 219, 223, O12.
- O12 in the siblings:
  - mobile/ios/skills/unit-testing/SKILL.md:162, 183
  - mobile/react-native/skills/component-testing/SKILL.md:169, 188
- R9: mobile/{android,ios,react-native}/skills/standards-audit/references/conformance-checklist.md.
- R3:
  - mobile/android/skills/kotlin-multiplatform/SKILL.md
  - auth/auth0-android/SKILL.md
  - auth/auth0-ios/SKILL.md
  - auth/auth0-react-native/SKILL.md

Traps:
- Re-read each row at its line first (§2 item 1).
- The version facts are kept by pointing at CLAUDE.md "Version policy" and the core rule file, never
  by updating the number.
- The mobile rules SKILL.md files are T1's.

Gate: own tests.
  python3 tools/skill-lint.py mobile/react-native/agents/mobile-react-native.md mobile/ios/agents/mobile-ios.md mobile/android/agents/mobile-android.md mobile/android/skills/unit-testing mobile/android/skills/kotlin-multiplatform mobile/ios/skills/unit-testing mobile/react-native/skills/component-testing mobile/android/skills/standards-audit mobile/ios/skills/standards-audit mobile/react-native/skills/standards-audit auth/auth0-android auth/auth0-ios auth/auth0-react-native   → 0 findings
  python3 tools/token-audit.py --violations-only | grep -E 'mobile/'   → prints nothing
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P7 — mobile agents and skills`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P8 — desktop-macos, desktop-windows (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P8 of docs/plans/015-skill-authoring-remediation.md. Fix audit 004's findings in the two desktop
plugins, including their oversized rule files.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R3, R9, R15–R21, R23.
2. The plan: §2, `## Answered questions` (O12, O18), task P8, and "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md: the rows naming desktop-macos, desktop-windows or
   desktop/windows/skills/unit-testing, and the R23 rows.
4. .skill-template/agent.md as T1 left it.

Fix, by path and rule:
- desktop/macos/agents/desktop-macos.md:
  - :16 and :17, R17.
  - :32 and :35, R15.
  - :12, R18.
  - The Fix line.
  - :60, O18.
- desktop/windows/agents/desktop-windows.md:
  - :16, R17.
  - :55 and :58, R15.
  - :31–40, R17: one pointer per row to project-setup, unit-testing or
    cpp-winrt/references/testing-and-coverage.md.
  - :42, R19.
  - :12, R18.
  - The Fix line.
  - :38, 56, 83, O18.
- R23, trim each to its constraints and point at the skill for the recipe. In
  desktop/macos/skills/rules/:
  - swift.md (6,688 chars, the core file: ≤ 6,000)
  - swiftui-mac.md (3,959)
  - xcode-config.md (3,428)
  - mac-accessibility.md (3,414)
  - swift-persistence.md (2,940)
  - appkit.md (2,547)
  - swift-networking.md (2,502)

  In desktop/windows/skills/rules/:
  - winui-xaml.md (3,610)
  - cppwinrt.md (3,571)
  - win-accessibility.md (2,788)
- desktop/windows/skills/unit-testing/SKILL.md:
  - :94–101, 138–140, 169–177, R17.
  - :18, 104, 132, R17: drop the numbers.
  - :57 and :123, R21.
  - :165–167 and :199, R19.
  - :185, O12, only if the line measures coverage inside a plan task.
- R9: desktop/{macos,windows}/skills/standards-audit/references/conformance-checklist.md.
- R3:
  - desktop/_shared/security/SKILL.md
  - auth/auth0-macos/SKILL.md
  - auth/auth0-windows/SKILL.md

Traps:
- Re-read each row at its line first (§2 item 1).
- A trimmed rule-file line keeps its constraint. Only the how-to moves, and only to a skill that
  already teaches it or gains it in this task. Keep every `paths:`.
- mobile/ios/skills/rules/* share file names and are not yours. The desktop rules SKILL.md files are
  T1's.

Gate: own tests.
  python3 tools/skill-lint.py desktop/macos/agents/desktop-macos.md desktop/windows/agents/desktop-windows.md desktop/macos/skills/rules/swift.md desktop/macos/skills/rules/swiftui-mac.md desktop/macos/skills/rules/xcode-config.md desktop/macos/skills/rules/mac-accessibility.md desktop/macos/skills/rules/swift-persistence.md desktop/macos/skills/rules/appkit.md desktop/macos/skills/rules/swift-networking.md desktop/windows/skills/rules/winui-xaml.md desktop/windows/skills/rules/cppwinrt.md desktop/windows/skills/rules/win-accessibility.md desktop/windows/skills/unit-testing desktop/macos/skills/standards-audit desktop/windows/skills/standards-audit desktop/_shared/security auth/auth0-macos auth/auth0-windows   → 0 findings
  wc -c desktop/macos/skills/rules/*.md desktop/windows/skills/rules/*.md   → swift.md ≤ 6,000, the rest named above ≤ 2,500
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P8 — desktop agents, rule files and unit-testing`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P9 — be-dotnet, be-java, be-node, be-python, be-rust (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P9 of docs/plans/015-skill-authoring-remediation.md. Fix audit 004's findings in the five backend
plugins.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R2, R3, R15, R17.
2. The plan: §1 (the coverage-in-a-task row), §2, `## Answered questions` (O12, O18, O19), task P9,
   and "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md: the "Agents, shared defects" rows naming be-*, and the
   be-python and be-java rows.
4. .skill-template/agent.md as T1 left it.

Fix, by path and rule:
- In each of backend/{dotnet,java,node,python,rust}/agents/be-<stack>.md:
  - R17, "Read the rules" (:16; :22 in be-python): the template wording. Keep be-rust's
    `#[cfg(test)]` note and be-node's narrow `*.ts` globs.
  - R17, the version asides (:17; :23 in be-python; :8 and :17 in be-rust): "the lane per the core
    rule file and CLAUDE.md 'Version policy'".
  - R15, Steps 1 and 4 (:25 and :28; :31 and :34 in be-python). Step 1: "the `pattern-guide` earn-it
    criterion quoted against the code, or 'no pattern'". Step 4: "the `code-review` findings table has
    no blocker or major row".
  - The Fix line.
  - O18: be-dotnet:54, be-java:52, be-node:52, be-python:59, be-rust:54.
- backend/python/agents/be-python.md:16–17, R17: pointers to python-pipeline.md:12 and
  python-container.md:14.
- backend/java/agents/be-java.md:26 and :30, O19.
- R2:
  - backend/java/skills/unit-testing/SKILL.md (19,052 chars)
  - backend/dotnet/skills/unit-testing/SKILL.md (18,219)
  - backend/node/skills/unit-testing/SKILL.md (17,906)
  - backend/python/skills/media-processing/SKILL.md (19,038)
  - backend/rust/skills/pattern-writer/SKILL.md (17,975)
- O12:
  - backend/dotnet/skills/unit-testing/SKILL.md:221
  - backend/java/skills/unit-testing/SKILL.md:244
  - backend/node/skills/unit-testing/SKILL.md:264
  - backend/python/skills/unit-testing/SKILL.md:153, 165
  - backend/rust/skills/unit-testing/SKILL.md:188
- R3: auth/_shared/auth0-concepts/SKILL.md and auth/_shared/oidc-concepts/SKILL.md.

Traps:
- Re-read each row at its line first (§2 item 1). The five agents are near-copies, so fix one, then
  carry the same edit to the other four, line by line.
- observability/ is P10's. The be-* rules SKILL.md files are T1's.

Gate: own tests.
  python3 tools/skill-lint.py backend/dotnet/agents/be-dotnet.md backend/java/agents/be-java.md backend/node/agents/be-node.md backend/python/agents/be-python.md backend/rust/agents/be-rust.md backend/dotnet/skills/unit-testing backend/java/skills/unit-testing backend/node/skills/unit-testing backend/python/skills/unit-testing backend/rust/skills/unit-testing backend/python/skills/media-processing backend/rust/skills/pattern-writer auth/_shared/auth0-concepts auth/_shared/oidc-concepts   → 0 findings
  python3 tools/token-audit.py --violations-only | grep -E 'backend/(dotnet|java|node|python|rust)/'   → prints nothing
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P9 — be-* agents and skills`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P10 — data and observability (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P10 of docs/plans/015-skill-authoring-remediation.md. Fix audit 004's findings in data and
observability.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R2, R11, R15–R18, R21.
2. The plan: §2, `## Answered questions` (O4, O15, O16), task P10, and "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md: the rows naming data/dynamodb,
   observability/logs-traces-setup, data-architect and data/_shared/migrations.
4. .skill-template/agent.md as T1 left it.

Fix, by path and rule:
- data/agents/data-architect.md:
  - :24, R17.
  - :42, the Fix line.
- data/dynamodb/SKILL.md (19,149 chars):
  - R2.
  - :14, 24, 96, Data.
  - :110–119, 141, 234, 237, R21.
  - :302–308, R15.
  - :274–300, R17.
  - :289–300, R18.
  - :105–207, R16: references/connections.md and references/security-iam.md.
  - :307, O15.
- R2: data/elasticsearch/SKILL.md (17,886 chars) and data/cosmosdb/SKILL.md (16,849).
- data/_shared/migrations/SKILL.md:63, O4.
- observability/logs-traces-setup/SKILL.md (16,869 chars):
  - R2.
  - :129 and :193, Data.
  - :394–403, R15.
  - :368–392, R17.
  - :138–173, R21.
  - :183–189 and :343–358, R16.
  - :301–318 and :402, O16.
- observability/agents/observability-engineer-{dotnet,java,node,rust}.md: the Fix line.

Traps:
- Re-read each row at its line first (§2 item 1).
- data/rules is T1's. The be-* agents are P9's.

Gate: own tests.
  python3 tools/skill-lint.py data/agents/data-architect.md data/dynamodb data/elasticsearch data/cosmosdb data/_shared/migrations observability/logs-traces-setup observability/agents/observability-engineer-dotnet.md observability/agents/observability-engineer-java.md observability/agents/observability-engineer-node.md observability/agents/observability-engineer-rust.md   → 0 findings (only O4's line if deferred)
  python3 tools/token-audit.py --violations-only | grep -E 'data/(dynamodb|elasticsearch|cosmosdb)|logs-traces-setup'   → prints nothing
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P10 — data and observability`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P11 — devops: the agent, k8s-security, supply-chain-security, iac-security (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P11 of docs/plans/015-skill-authoring-remediation.md. Fix audit 004's findings in devops-engineer
and the three largest devops skills.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R2, R15–R19, R21.
2. The plan: §2, `## Answered questions` (O13), D3, task P11, and "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md: the rows naming devops/k8s-security and devops-engineer.
4. devops/k8s-security/references/{kube-bench,kubescape,polaris}.md (the R16 and R17 targets), and
   .skill-template/agent.md as T1 left it.

Fix, by path and rule:
- devops/agents/devops-engineer.md:
  - :22, R17.
  - :50, R15.
  - :16 and :52, R18.
  - The Fix line.
- devops/k8s-security/SKILL.md (36,584 chars):
  - R2.
  - :40–57 and :458–522, R17: delete `## Rules`.
  - :79–114, 210–217, 400–456, R17.
  - :82–83, 92–93, 125–139, 161–173, 192–204, 242–251, 268–273, 287–292, 364–381, 400–409, R21: keep
    `# EXPECTED:` and the ticket-and-reason comments.
  - :16–22, R19.
  - :122–230 and :400–456, R16.
  - :545, Data.
  - :133–134, :462 and references/kube-bench.md:21–22, O13. Check the ids against kube-bench's
    current release, through `dev:source-grounding`.
- R2: devops/supply-chain-security/SKILL.md (36,528 chars) and devops/iac-security/SKILL.md (31,022).

Traps:
- Re-read each row at its line first (§2 item 1).
- Keep the live-cluster authorization rule, stated once. It is a guardrail.
- The other devops skills are P12's. devops/rules is T1's.

Gate: own tests.
  python3 tools/skill-lint.py devops/agents/devops-engineer.md devops/k8s-security devops/supply-chain-security devops/iac-security   → 0 findings
  python3 tools/token-audit.py --violations-only | grep -E 'devops/(k8s-security|supply-chain-security|iac-security)'   → prints nothing
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P11 — devops agent, k8s, supply-chain and IaC security`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P12 — devops, the rest, and security-governance (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P12 of docs/plans/015-skill-authoring-remediation.md. Bring the remaining devops skills and
cloud-incident-response under budget, and fix security-governance's findings.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R2, R9, R10, R15–R17, R19.
2. The plan: §2, `## Answered questions` (O17), D3, task P12, and "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md: the rows naming security-architect,
   security/cloud-incident-response, security-governance.md and security/standards-audit.
4. security/rules-security-governance/runbooks.md "Cloud incident response", the R17 target.

Fix, by path and rule:
- R2:
  - devops/infra-controls-validation/SKILL.md (25,703 chars)
  - devops/container-runtime-security/SKILL.md (22,947)
  - devops/cloud-posture/SKILL.md (22,000)
- security/agents/security-architect.md:
  - :26, R17.
  - :40, R15.
  - :12, 18, 42, 53, R19: keep the Invariant at :18.
  - :21 and :44, O17.
- security/cloud-incident-response/SKILL.md (21,277 chars):
  - R2.
  - :63–84, R15.
  - :107–118, R17.
  - :9–13, 63–64, 109–110, 126–128, R19.
  - :47–59 and :69–75, R16.
  - :131, Data.
- R10: security/rules-security-governance/security-governance.md:40 and
  security/standards-audit/references/conformance-checklist.md:253.
- R9: security/standards-audit/references/conformance-checklist.md.

Traps:
- Re-read each row at its line first (§2 item 1).
- security-governance.md is an always-loaded rule file. Edit only its :40 marker. Its size has no row.
- security/rules-security-governance/SKILL.md is T1's. The penetration-testing skills are P13's.

Gate: own tests.
  python3 tools/skill-lint.py devops/infra-controls-validation devops/container-runtime-security devops/cloud-posture security/agents/security-architect.md security/cloud-incident-response security/rules-security-governance/security-governance.md security/standards-audit   → 0 findings
  python3 tools/token-audit.py --violations-only | grep -E 'infra-controls-validation|container-runtime-security|cloud-posture|cloud-incident-response'   → prints nothing
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P12 — devops remainder and security-governance`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P13 — penetration-testing (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P13 of docs/plans/015-skill-authoring-remediation.md. Bring the penetration-testing skills under
budget, and fix penetration-tester's findings.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R2, R3, R15–R17, R19.
2. The plan: §2, D3, task P13, and "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md: the rows naming security/agents/penetration-tester.md.

Fix, by path and rule:
- security/agents/penetration-tester.md:
  - :56 and :64, R15.
  - :20 and :62, R17: each control once, in Invariants.
  - :18, R19.
- R2:
  - security/cloud-attack-azure/SKILL.md (21,020 chars)
  - security/cloud-attack-aws/SKILL.md (19,859)
  - security/cloud-recon-enumeration/SKILL.md (18,538)
  - security/atomic-simulation/SKILL.md (16,496)
  - security/cloud-attack-gcp/SKILL.md (16,331)
- security/metasploit-setup/SKILL.md:
  - R2: the description is 452 chars.
  - R3.

Traps:
- Re-read each row at its line first (§2 item 1).
- Scope, authorization and logging controls are guardrails. Each one stays, stated once. Only
  per-cloud or per-tool branch material moves to references/.

Gate: own tests.
  python3 tools/skill-lint.py security/agents/penetration-tester.md security/cloud-attack-azure security/cloud-attack-aws security/cloud-recon-enumeration security/atomic-simulation security/cloud-attack-gcp security/metasploit-setup   → 0 findings
  python3 tools/token-audit.py --violations-only | grep -E 'security/(cloud-attack|cloud-recon|atomic-simulation|metasploit-setup)'   → prints nothing
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P13 — penetration-testing`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P14 — qa-java: the lane's agents, conventions, rule files, contents lists and three bodies (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P14 of docs/plans/015-skill-authoring-remediation.md. Fix audit 004's findings in the qa-java
lane's agents, conventions skill, rule files and reference files, and in three bodies.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R2, R9, R15–R21, R23.
2. The plan: §2, `## Answered questions` (O7, O21), D7, task P14, and "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md: the rows naming qa-ui-java, the qa-java
   inhouse-framework-conventions, qa/java/skills/ai-feature-testing, the R23 rows, and the MCP-command
   row.
4. .skill-template/agent.md as T1 left it.

Fix, by path and rule:
- qa/java/agents/qa-ui-java.md:
  - :16, R17.
  - :25, R17: the MCP command becomes a pointer to page-objects-from-url.
  - :32 and :55, R18.
  - :46, the Fix line.
  - :21 and :55, O21.
- The Fix line: qa/java/agents/qa-{api,bdd,desktop,llm,mobile,performance}-java.md.
- The MCP command, R17: its one home is qa/java/skills/page-objects-from-url/SKILL.md, and
  qa/java/skills/evidence-capture/SKILL.md points at it.
- qa/java/skills/inhouse-framework-conventions/SKILL.md:
  - :172–178, 263–275, 277–, R17.
  - :249–261, R19.
  - :283, only under O7 (b).
- R23: qa/java/skills/rules/desktop-tests.md (3,636 chars) and qa/java/skills/rules/qa-java-ui.md
  (2,523).
- qa/java/skills/ai-feature-testing/SKILL.md (21,319 chars):
  - R2.
  - :237, 260–261, 274, R21.
  - :234, 238, 255, 261–262, 277, R21.
  - :236, 238, 259, 273, R21.
  - :20–37, 86–89, 281–306, 321–339, R17.
  - :9–20, R19.
  - :64–72 and :281–306, R18.
- R2: qa/java/skills/api-contract-testing/SKILL.md (20,664 chars) and
  qa/java/skills/test-quality-check/SKILL.md (18,714).
- R9, in qa/java/skills/:
  - analytics-testing/references/playwright.md
  - browser-cloud-setup/references/details.md
  - email-testing/references/{gmail-imap,mailosaur,mailpit,sendgrid-sandbox}.md
  - evidence-capture/references/playwright.md
  - file-storage-testing/references/{azure-blob,s3}.md
  - language-testing/references/details.md
  - messaging-testing/references/{kafka,rabbitmq,service-bus,sqs}.md
  - network-mocking/references/{cdp,playwright-routes,proxy}.md
  - payment-testing/references/stripe-api.md
  - realtime-stream-testing/references/details.md
  - test-login-tokens/references/details.md
  - visual-regression/references/playwright-snapshots.md

Traps:
- Re-read each row at its line first (§2 item 1).
- Test examples must still obey CLAUDE.md "Test code rules": Should_X_When_Y names, no inline
  comments, injected clients. tools/qa-version-check.py must still find the Playwright pin where it
  expects it.
- data-driven-testing, failure-injection-testing, grpc and security-testing are P15's. qa/_shared is
  P16's. The rules SKILL.md is T1's.

Gate: own tests.
  python3 tools/skill-lint.py qa/java/agents qa/java/skills/inhouse-framework-conventions qa/java/skills/rules/desktop-tests.md qa/java/skills/rules/qa-java-ui.md qa/java/skills/page-objects-from-url qa/java/skills/evidence-capture qa/java/skills/ai-feature-testing qa/java/skills/api-contract-testing qa/java/skills/test-quality-check qa/java/skills/analytics-testing qa/java/skills/browser-cloud-setup qa/java/skills/email-testing qa/java/skills/file-storage-testing qa/java/skills/language-testing qa/java/skills/messaging-testing qa/java/skills/network-mocking qa/java/skills/payment-testing qa/java/skills/realtime-stream-testing qa/java/skills/test-login-tokens qa/java/skills/visual-regression   → 0 findings
  python3 tools/token-audit.py --violations-only | grep -E 'qa/java/skills/(ai-feature-testing|api-contract-testing|test-quality-check)/'   → prints nothing
  wc -c qa/java/skills/rules/desktop-tests.md qa/java/skills/rules/qa-java-ui.md   → each ≤ 2,500
  python3 tools/qa-version-check.py   → OK
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P14 — qa-java agents, conventions, rule files, references`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P15 — qa-java: the remaining bodies (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P15 of docs/plans/015-skill-authoring-remediation.md. Bring six qa-java skills under the
16,000-char body budget.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R2, R16, R17, R19.
2. The plan: §2, D3, task P15, and "Close-out — every task".
3. qa/java/skills/rules/*.md, the R17 targets: a restated rule becomes a pointer to them.

Fix, R2, by path (all in qa/java/skills/):
- data-driven-testing/SKILL.md (19,798 chars)
- failure-injection-testing/SKILL.md (20,126)
- api-test-author/grpc/SKILL.md (20,090)
- security-testing/passive-scan/SKILL.md (19,923)
- security-testing/dependency-scan/SKILL.md (18,411)
- security-testing/permission-testing/SKILL.md (17,613)

Traps:
- These have no judgment rows in 004. Only R2 is to fix, by §2 item 3. Any other defect you see goes
  into As built for G1.
- A version pin moved to references/ must still be where tools/qa-version-check.py reads it.
- qa/_shared/security-testing/* is P16's.

Gate: own tests.
  python3 tools/skill-lint.py qa/java/skills/data-driven-testing qa/java/skills/failure-injection-testing qa/java/skills/api-test-author/grpc qa/java/skills/security-testing/passive-scan qa/java/skills/security-testing/dependency-scan qa/java/skills/security-testing/permission-testing   → 0 findings
  python3 tools/token-audit.py --violations-only | grep -E 'qa/java/skills/(data-driven-testing|failure-injection-testing|api-test-author/grpc|security-testing)/'   → prints nothing
  python3 tools/qa-version-check.py   → OK
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P15 — qa-java bodies under budget`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P16 — qa/_shared (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P16 of docs/plans/015-skill-authoring-remediation.md. Bring the shared QA skills under budget, and
fix python-web-testing, webmcp-testing and the two R6 skills.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R2, R6, R7, R10, R16, R17,
   R22.
2. The plan: §2, D3, task P16, and "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md: the rows naming qa/_shared/python-web-testing.
4. qa/typescript/skills/rules/ui-tests.md:21, an R17 target.

Fix, by path and rule:
- R2, in qa/_shared/:
  - security-testing/image-infra-scan/SKILL.md (19,111 chars)
  - security-testing/code-scan/SKILL.md (18,476)
  - security-testing/known-vuln-scan/SKILL.md (18,062)
  - security-testing/active-scan/SKILL.md (16,788)
  - security-testing/secrets-scan/SKILL.md (16,672)
  - security-testing/certificate-scan/SKILL.md (16,258)
  - api-spec-assets/SKILL.md (18,353)
- qa/_shared/python-web-testing/SKILL.md:
  - R7.
  - :46–56, R17: point at the qa-* UI rule files, and keep the Python spellings.
  - :134, R22: "hand it to the `qa-ui-<stack>` agent".
  - :121–134, R16.
- qa/_shared/webmcp-testing/SKILL.md:42, R10.
- R6: qa/_shared/contract-testing-pact/SKILL.md and qa/_shared/performance/SKILL.md. Use topic
  headings: "Choosing Pact", "Profiler hand-off".

Traps:
- Re-read each row at its line first (§2 item 1).
- python-web-testing is a front door registered in all three qa-* plugins. Keep its description's
  trigger.
- tools/qa-version-check.py reads pins in python-web-testing and webmcp-testing. Keep them.

Gate: own tests.
  python3 tools/skill-lint.py qa/_shared/security-testing qa/_shared/api-spec-assets qa/_shared/python-web-testing qa/_shared/webmcp-testing qa/_shared/contract-testing-pact qa/_shared/performance   → 0 findings
  python3 tools/token-audit.py --violations-only | grep -E 'qa/_shared/'   → prints nothing
  python3 tools/qa-version-check.py   → OK
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P16 — qa/_shared`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P17 — qa-dotnet (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P17 of docs/plans/015-skill-authoring-remediation.md. Fix audit 004's findings in the qa-dotnet
lane.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R2, R3, R9, R15–R19, R23.
2. The plan: §2, `## Answered questions` (O7, O20, O21), D7, task P17, and "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md: the rows naming qa-ui-dotnet, the qa-dotnet
   inhouse-framework-conventions, the R23 rows, and the MCP-command row.
4. .skill-template/agent.md as T1 left it.

Fix, by path and rule:
- qa/dotnet/agents/qa-ui-dotnet.md:
  - :16, R17.
  - :17, R17.
  - :29, R17: the MCP command becomes a pointer to page-objects-from-url.
  - :46, R17: "the trace commands in `evidence-capture`".
  - The Fix line.
  - :55, O21.
- The Fix line: qa/dotnet/agents/qa-{api,bdd,desktop,llm,mobile,performance}-dotnet.md.
- The MCP command, R17: its one home is qa/dotnet/skills/page-objects-from-url/SKILL.md, and
  qa/dotnet/skills/evidence-capture/SKILL.md points at it.
- qa/dotnet/skills/inhouse-framework-conventions/SKILL.md:
  - :239, Data: "a typed DTO, not `RestResponse`".
  - :174–180, 263–, 278–, R17.
  - :249–261, R19.
  - :150 and :170–172, O7.
- R23: qa/dotnet/skills/rules/desktop-tests.md (3,403 chars) and qa/dotnet/skills/rules/web-ui.md
  (2,714).
- R3: qa/dotnet/skills/desktop-screen-explorer/SKILL.md and
  qa/dotnet/skills/desktop-window-objects/SKILL.md.
- R2, in qa/dotnet/skills/:
  - security-testing/passive-scan/SKILL.md (19,853 chars)
  - api-test-author/grpc/SKILL.md (18,597)
  - security-testing/permission-testing/SKILL.md (17,748)
  - failure-injection-testing/SKILL.md (17,468)
  - security-testing/dependency-scan/SKILL.md (17,014)
- R9, in qa/dotnet/skills/:
  - accessibility-testing/references/{axe-playwright,lighthouse-ci}.md
  - ai-feature-testing/references/details.md
  - analytics-testing/references/playwright.md
  - api-test-author/writer/references/details.md
  - browser-cloud-setup/references/details.md
  - email-testing/references/{gmail-imap,mailosaur,mailpit,sendgrid-sandbox}.md
  - evidence-capture/references/playwright.md
  - file-storage-testing/references/{azure-blob,s3}.md
  - language-testing/references/details.md
  - messaging-testing/references/{kafka,rabbitmq,service-bus,sqs}.md
  - network-mocking/references/{cdp,playwright-routes,proxy}.md
  - payment-testing/references/stripe-api.md
  - realtime-stream-testing/references/details.md
  - standards-audit/references/conformance-checklist.md
  - test-login-tokens/references/details.md
  - visual-regression/references/playwright-snapshots.md

Traps:
- Re-read each row at its line first (§2 item 1).
- tools/qa-version-check.py must still find the Playwright 1.63.0 pin where it expects it.
- qa/dotnet/skills/rules/SKILL.md is T1's. qa/_shared is P16's.

Gate: own tests.
  python3 tools/skill-lint.py qa/dotnet/agents qa/dotnet/skills/inhouse-framework-conventions qa/dotnet/skills/rules/desktop-tests.md qa/dotnet/skills/rules/web-ui.md qa/dotnet/skills/page-objects-from-url qa/dotnet/skills/evidence-capture qa/dotnet/skills/desktop-screen-explorer qa/dotnet/skills/desktop-window-objects qa/dotnet/skills/security-testing qa/dotnet/skills/api-test-author qa/dotnet/skills/failure-injection-testing qa/dotnet/skills/accessibility-testing qa/dotnet/skills/ai-feature-testing qa/dotnet/skills/analytics-testing qa/dotnet/skills/browser-cloud-setup qa/dotnet/skills/email-testing qa/dotnet/skills/file-storage-testing qa/dotnet/skills/language-testing qa/dotnet/skills/messaging-testing qa/dotnet/skills/network-mocking qa/dotnet/skills/payment-testing qa/dotnet/skills/realtime-stream-testing qa/dotnet/skills/standards-audit qa/dotnet/skills/test-login-tokens qa/dotnet/skills/visual-regression   → 0 findings
  python3 tools/token-audit.py --violations-only | grep -E 'qa/dotnet/'   → prints nothing
  wc -c qa/dotnet/skills/rules/desktop-tests.md qa/dotnet/skills/rules/web-ui.md   → each ≤ 2,500
  python3 tools/qa-version-check.py   → OK
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P17 — qa-dotnet`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P18 — qa-typescript (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P18 of docs/plans/015-skill-authoring-remediation.md. Fix audit 004's findings in the
qa-typescript lane.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R2, R6, R8, R9, R17, R19,
   R21, R23.
2. The plan: §2, `## Answered questions` (O7, O8, O9, O20, O21), D7, task P18, and
   "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md: the rows naming qa-ui-typescript, the qa-typescript
   inhouse-framework-conventions, the R23 rows, and the MCP-command row.
4. .skill-template/agent.md as T1 left it.

Fix, by path and rule:
- qa/typescript/agents/qa-ui-typescript.md:
  - :16, R17.
  - :27, R17: the MCP command becomes a pointer to page-objects-from-url.
  - :44, the Fix line.
  - :50, O20.
  - :53, O21.
- The Fix line: qa/typescript/agents/qa-{api,bdd,desktop,mobile}-typescript.md. Also
  qa-llm-typescript.md and qa-performance-typescript.md, if `grep -n "Fix"` shows an open-ended sweep
  there.
- The MCP command, R17: its one home is qa/typescript/skills/page-objects-from-url/SKILL.md, and
  qa/typescript/skills/evidence-capture/SKILL.md points at it.
- qa/typescript/skills/inhouse-framework-conventions/SKILL.md:
  - :165–171, 237–, 251–, R17.
  - :223–235, R19.
  - :155, R21: withPassword(`Wrong-${crypto.randomUUID()}`).
  - :134, O8.
  - :208 and :109–114, O9.
- R23: qa/typescript/skills/rules/ui-tests.md (2,685 chars).
- R8: qa/typescript/skills/bdd-project-scaffold/SKILL.md:132 and
  qa/typescript/skills/ui-test-author/review/SKILL.md:15. Name the skill owning
  references/config-and-fixtures.md on the same line.
- R6: qa/typescript/skills/benchmarks/SKILL.md.
- R2, in qa/typescript/skills/:
  - failure-injection-testing/SKILL.md (20,074 chars)
  - security-testing/passive-scan/SKILL.md (19,766)
  - security-testing/dependency-scan/SKILL.md (17,020)
  - data-driven-testing/SKILL.md (16,824)
  - api-test-author/grpc/SKILL.md (16,353)
- R9, in qa/typescript/skills/:
  - ai-feature-testing/references/details.md
  - analytics-testing/references/playwright.md
  - browser-cloud-setup/references/details.md
  - email-testing/references/{gmail-imap,mailosaur,mailpit,sendgrid-sandbox}.md
  - evidence-capture/references/playwright.md
  - file-storage-testing/references/{azure-blob,s3}.md
  - language-testing/references/details.md
  - messaging-testing/references/{kafka,rabbitmq,service-bus,sqs}.md
  - network-mocking/references/{playwright-routes,proxy}.md
  - payment-testing/references/stripe-api.md
  - realtime-stream-testing/references/details.md
  - test-login-tokens/references/details.md

Traps:
- Re-read each row at its line first (§2 item 1).
- This lane is Playwright 1.64. tools/qa-version-check.py must still find its pin.
- qa/typescript/skills/rules/SKILL.md is T1's. qa/_shared is P16's.

Gate: own tests.
  python3 tools/skill-lint.py qa/typescript/agents qa/typescript/skills/inhouse-framework-conventions qa/typescript/skills/rules/ui-tests.md qa/typescript/skills/page-objects-from-url qa/typescript/skills/evidence-capture qa/typescript/skills/bdd-project-scaffold qa/typescript/skills/ui-test-author/review qa/typescript/skills/benchmarks qa/typescript/skills/failure-injection-testing qa/typescript/skills/security-testing qa/typescript/skills/data-driven-testing qa/typescript/skills/api-test-author/grpc qa/typescript/skills/ai-feature-testing qa/typescript/skills/analytics-testing qa/typescript/skills/browser-cloud-setup qa/typescript/skills/email-testing qa/typescript/skills/file-storage-testing qa/typescript/skills/language-testing qa/typescript/skills/messaging-testing qa/typescript/skills/network-mocking qa/typescript/skills/payment-testing qa/typescript/skills/realtime-stream-testing qa/typescript/skills/test-login-tokens   → 0 findings
  python3 tools/token-audit.py --violations-only | grep -E 'qa/typescript/'   → prints nothing
  wc -c qa/typescript/skills/rules/ui-tests.md   → ≤ 2,500
  python3 tools/qa-version-check.py   → OK
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P18 — qa-typescript`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P19 — qa/manual, qa/reporting, qa/cicd (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P19 of docs/plans/015-skill-authoring-remediation.md. Fix audit 004's findings in the manual-QA,
reporting and CI/CD trees.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R2, R8, R9, R10, R11, R13,
   R15, R17.
2. The plan: §2, `## Answered questions` (O3), D7, task P19, and "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md: the rows whose Location starts qa/manual or qa/reporting.
4. .skill-template/agent.md as T1 left it (Steps table, `## Report`, the Fix line).

Fix, by path and rule:
- qa/manual/agents/qa-feature-spec-writer.md:
  - :33, R13: Steps becomes the template table.
  - :100, R13: `## Report` with `Mode:`.
- qa/manual/agents/qa-explorer.md:28, 39, 40, R8: qa/manual/app-exploration/references/probes.md and
  …/checks.md.
- qa/manual/cross-feature-test-design/SKILL.md:21, R8: name the owner on the line, as :11 does.
- O3:
  - qa/manual/cross-feature-test-design/SKILL.md:28, 30
  - qa/manual/cross-feature-test-design/references/example-cancel-booking.md:9, 76, 103
  - qa/manual/requirements-breakdown/references/connections.md:9
- R10: qa/manual/test-plan-writer/SKILL.md:130 and qa/manual/test-strategy/SKILL.md:166.
- R2:
  - qa/manual/test-plan-writer/SKILL.md: the description is 232 chars.
  - qa/manual/agents/qa-test-case-designer.md (16,323 chars), plus its Fix line.
  - qa/manual/agents/qa-test-planner.md (14,847).
- qa/manual/app-exploration/references/probes.md:
  - R9.
  - R17: the Playwright MCP command becomes a pointer to the lane's page-objects-from-url.
- R8, the path qa/<stack>/skills/ui-test-author/playwright/references/trace-correlation.md:
  - qa/reporting/dotnet/skills/test-reports/SKILL.md:171
  - qa/reporting/java/skills/test-reports/SKILL.md:178
  - qa/reporting/typescript/skills/test-reports/SKILL.md:163
- The Fix line: qa/reporting/agents/qa-reporting-{dotnet,java,typescript}.md and
  qa/cicd/agents/qa-cicd-{dotnet,java,typescript}.md.
- R9: qa/cicd/{dotnet,java,typescript}/skills/ci-pipelines/references/{azure-pipelines,github-actions,gitlab-ci}.md.

Traps:
- Re-read each row at its line first (§2 item 1).
- probes.md loses its pin. Confirm with tools/qa-version-check.py that no expected pin lived only
  there.
- Under O3 (b), the R11 lines stay, and T2's lint exception clears them.

Gate: own tests.
  python3 tools/skill-lint.py qa/manual qa/reporting qa/cicd   → 0 findings (only O3's lines if deferred)
  python3 tools/token-audit.py --violations-only | grep -E 'qa/manual/'   → prints nothing
  python3 tools/qa-version-check.py   → OK
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P19 — qa/manual, qa/reporting, qa/cicd`.
Close out per the plan's "Close-out — every task" before you stop.
````

### P20 — business-analysis, training-data, tooling, and /dev:refine (general-purpose, docs)

````
Depends on: L1, T1
Agent: general-purpose · Stack: docs

Task P20 of docs/plans/015-skill-authoring-remediation.md. Fix audit 004's findings in
business-analysis, training-data and tooling, and apply O10 to /dev:refine.

Read, in this order:
1. engineering-practices/writing-for-agents/SKILL.md: the rule table rows R10, R12, R13, R15–R19, R23.
2. The plan: §2, `## Answered questions` (O3, O10, O18, O23, O24), task P20, and
   "Close-out — every task".
3. docs/audits/004-skill-authoring-r1.md: the rows naming requirements-author, business-analyst,
   ba-project-memory, ba-dependency-map, the business-analysis R23 rows, dataset-engineer,
   dataset-auditor, td-dataset-formats, tooling-engineer, mcp-builder and capability-contract.
4. .skill-template/agent.md as T1 left it. Under O10 (a), also CONTRIBUTING.md "Names and registration".

Fix, by path and rule:
- business-analysis/agents/requirements-author.md:
  - :14–30, R17: two lines.
  - :56, R15.
  - :67, R17.
  - :36, 74, 86, R18.
  - O10. Under (a): move engineering-practices/commands/refine.md into the business-analysis plugin's
    commands, register it and the agent in business-analysis in .claude-plugin/marketplace.json,
    remove both from dev, and update their rows in docs/skills-catalog.md and README.md. Under (b):
    bundle what it loads into dev, listing it first.
- business-analysis/agents/business-analyst.md:
  - :38 and :52, R17.
  - :19 and :60, R18.
  - :56, the Fix line.
- business-analysis/skills/ba-project-memory/SKILL.md:
  - :34–58, R17.
  - :66–111, R17: point at kb-lint.py after reading what it checks.
  - :116–131, R16.
  - :52, R19.
  - :116, O3.
- business-analysis/skills/ba-dependency-map/references/example-dependency-map.md:27, 38, 39, 79, 91,
  R10: each marker goes in a code span.
- R23, in business-analysis/skills/rules/:
  - business-model.md (6,909 chars, the core file: ≤ 6,000)
  - backlog-stories.md (4,065)
  - backlog-epics.md (2,646)
  - backlog-requirements.md (2,541)
- training-data/agents/dataset-engineer.md:
  - :23, R17.
  - :18, R19.
  - :45, the Fix line.
- training-data/agents/dataset-auditor.md:60, R13: `## Report` with `Mode:`.
- training-data/_shared/td-dataset-formats/SKILL.md:
  - :13, 31–33, 52–58, 81, 96, 102–105, 124–134, R17.
  - :60–98, R16.
  - :22, 113, 134, R19.
  - :22–23, O24.
- tooling/agents/tooling-engineer.md:
  - :44, R17.
  - :17 and :19, R18 and R19.
  - :51, the Fix line.
  - Its `Gate evidence` line, O18.
- tooling/skills/mcp-builder/SKILL.md:11, R12.
- tooling/_shared/capability-contract/SKILL.md:
  - :71–75, 112–115, 132–134, 149–151, R17.
  - :25–153, R15.
  - :9, 119, 150, R19.
  - :149, O23.

Traps:
- Re-read each row at its line first (§2 item 1).
- A registration move is the one change here that plugin-surface-check judges. Run it after the move,
  and fix every row it names before going on.
- The rules SKILL.md files are T1's. tooling/skills/rules/tool-contract.md changes only under O23 (b).

Gate: own tests.
  python3 tools/skill-lint.py business-analysis/agents business-analysis/skills/ba-project-memory business-analysis/skills/ba-dependency-map business-analysis/skills/rules/business-model.md business-analysis/skills/rules/backlog-stories.md business-analysis/skills/rules/backlog-epics.md business-analysis/skills/rules/backlog-requirements.md training-data/agents training-data/_shared/td-dataset-formats tooling/agents/tooling-engineer.md tooling/skills/mcp-builder tooling/_shared/capability-contract   → 0 findings (only O3's line if deferred)
  wc -c business-analysis/skills/rules/*.md   → business-model.md ≤ 6,000, the three backlog files ≤ 2,500
  python3 tools/plugin-surface-check.py   → OK

Commit: `docs(skills): 015 P20 — business-analysis, training-data, tooling, /refine`.
Close out per the plan's "Close-out — every task" before you stop.
````

### G1 — the whole library once more, then filing (general-purpose, docs)

````
Depends on: L1, T1, P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, P11, P12, P13, P14, P15, P16, P17, P18, P19, P20
Agent: general-purpose · Stack: docs

Task G1 of docs/plans/015-skill-authoring-remediation.md. This is the last task: run the whole sweep
over the library, fix what it finds, and file the plan.

Read, in this order:
1. The plan: the header, §2, §4, `## Answered questions`, the Open questions still deferred, every
   task's `As built` note (the "outside my paths" items and every D3 `D<n>`), task G1, and
   "Close-out — every task".
2. engineering-practices/writing-plans/references/plan-format.md §5, "The last task's fix loop".

Gate (this is the last runnable task, so it runs the whole set once more across the plan, in order):
  python3 tools/skill-lint.py                       → 0 findings, or only a deferred O's lines
  python3 tools/token-audit.py --violations-only    → exit 0
  python3 tools/plugin-surface-check.py             → OK
  python3 tools/qa-version-check.py                 → OK
  python3 -m pytest tools/test_skill_lint.py -q     → green
  git diff --name-only "$(git log --diff-filter=A --format=%h -1 -- docs/plans/015-skill-authoring-remediation.md)" HEAD

Do:
- Use the fix loop: run the whole set once; fix each failure with its narrowest command
  (`python3 tools/skill-lint.py <path>`); rerun only what failed; then run the whole set once more.
- Read every references/*.md file the plan created, and every pointer added beside a moved section.
  Each must land on a real heading or line.
- Fix each "outside my paths" item from the As built notes.
- Name in Status every deferred O and every body still over budget under a D3 `D<n>`.

Traps:
- A failure may belong to any P task. Fix it in place, and name the task in As built.
- New findings outside audit 004's rules go to a round-2 audit, not into this plan.
- There is no documentation task, so you delete the last prompt block, and you file the plan
  (close-out step 8: git mv to docs/plans/implemented/; that folder has no README).

Commit: `docs(skills): 015 G1 — whole-library sweep`.
Close out per the plan's "Close-out — every task" before you stop.
````
