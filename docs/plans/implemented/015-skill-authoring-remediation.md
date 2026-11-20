# 015 — Skill-authoring remediation, from audit 004 — plan (2026-11-20)

**Goal:** Clear every finding of `docs/audits/004-skill-authoring-r1.md` (528 findings, 249 major)
against the house authoring standard (`engineering-practices/writing-for-agents/SKILL.md`, R1–R23).
The owner settles the 24 logical conflicts in one round of questions first. One task then fixes the
shared shapes: the agent template, the standard itself and the 23 `rules` skills. Twenty per-plugin
tasks fix their own files, and a gate task runs the lint, the size audit and the surface check over the
whole library.

**Status:** Delivered and filed (2026-11-20). Audit 004's 528 findings are cleared: the owner answered all 24 logical conflicts (`## Answered questions (2026-11-20)`, none deferred), L1, T1, C1 and P1–P20 landed, and G1's whole-library sweep is green: `skill-lint` `0 findings`, `token-audit --violations-only` exit 0 (no body over budget, so no D3 overage), `plugin-surface-check` and `qa-version-check` `OK`, `test_skill_lint.py` 95 passed. G1 also fixed P6, P7, P10, P14, P17 and P20's outside-their-paths items (D24). P20 registered O10 (b) as D22: five authoring skills `/dev:refine` loads moved from `business-analysis` to `dev`. **Unverified:** `dev` installed alone with the moved skills (the surface check passes; no installed plugin was run). **For a round-2 audit:** two unregistered bodies over 16,000 (`claude-api`, `product-analytics`) and inline comments in a few code samples, named in G1's `As built`. **Metered:** about 25 sessions of subscription usage.

**Test design:** none. The plan serves no stories, and it changes skill text only. The check is
`tools/skill-lint.py`, `tools/token-audit.py` and `tools/plugin-surface-check.py`, which already exist.
**Documentation task:** none. This is the skills library, and the skill text the tasks edit is itself
the documentation. Two documents change only if registration changes: the catalog
(`docs/skills-catalog.md`) and `README.md`. O10 was answered (b), bundling into `dev`. Where that bundle
changes what the catalog or README lists for `dev`, P20 updates those rows in the same task. C1 edits the
catalog's gating wording (O12). No product behaviour changes for a `be-documenter` to trace.
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
| The coverage-in-a-task line (A4 left it unverified) | Checked on 2026-11-20 with `grep -n "own tests"`. Not only `mobile/android/skills/unit-testing/SKILL.md:180, 219` carries it. So do `backend/{dotnet:221, java:244, node:264, python:153, 165, rust:188}/skills/unit-testing/SKILL.md`, `mobile/ios/skills/unit-testing/SKILL.md:162, 183`, `mobile/react-native/skills/component-testing/SKILL.md:169, 188`, `frontend/blazor/skills/component-testing/SKILL.md:116, 127`, `frontend/react/skills/component-testing/SKILL.md:152, 161` and possibly `desktop/windows/skills/unit-testing/SKILL.md:185`. `desktop/macos/skills/unit-testing` does not. | O12's answer, applied by C1 with the rest of the gating rule |

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
11. **C1's gating wording stays.** C1 rewrites the plan-task gating rule (O12) in the files it lists, and
    it lands before any P task. A P task's trims and moves keep that wording as C1 wrote it, and a
    pointer to the rule points at it rather than re-listing it.

## 3. How the work is split

- **L1 comes first.** It asks the owner O1–O24 in one message and records the answers (D1).
- **T1 comes second.** It fixes the shared shapes that the per-plugin tasks copy:
  - `.skill-template/agent.md`: the Fix sweep (R15) and, under O18, the `Gate evidence` line;
  - the standard's own R8 and R20 rows (O1, O5);
  - the 23 `rules` skills, one shape fixed once across every plugin (D2).
- **C1 runs beside T1.** O12 changed how a plan task gates (D9). C1 rewrites that rule, in one wording,
  in every file that states it, before any P task trims those files. Its files and T1's are disjoint.
- **P1–P20 follow, one cluster of plugins each.** A cluster is merged with its neighbour while the session
  stays under about 150k. Mechanical rows (R3, R6, R7, R8, R9, R10, R12, R13) are batched by rule within
  the task, and judgment rows go with the skill they name. The files are disjoint, so any three P tasks
  run side by side. Each one depends on L1, T1 and C1, and on nothing else.
- **G1 comes last.** It runs the whole sweep over the library, fixes what is left, and files the plan.
- **There is no T2.** O1, O3 and O4 were all answered (a), so the lint does not change.

Every task's stack is `docs`, and its agent is `general-purpose`: skill text is the library's own
source, and no catalog agent owns it.

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

None open. L1 put all 30 logical-conflict rows of 004 to the owner as O1–O24 on 2026-11-20, and the owner
answered every one, deferring none. The answers are in `## Answered questions (2026-11-20)`, after
`## 6. Decisions`.

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

**D8 (2026-11-20) — L1 asked O1–O24 in eight rounds of at most four questions, not in one message.**
L1's prompt said one message. `engineering-practices/brainstorming/SKILL.md` step 2 says that with a
multiple-choice question tool, a round holds at most four questions, and the owner pointed at the skill.
The two extra rounds were follow-ups: O20's scope, and O12's coverage and red-test details.

| Option | Verdict | Why |
|---|---|---|
| Rounds of four through the question tool, most-unblocking first | chosen | The skill's rule, and the owner asked for it |
| One message listing all 24 | rejected | It was L1's wording, and the owner overruled it |

Cost: eight round-trips instead of one.

**D9 (2026-11-20) — O12's answer is applied by a new task, C1, which runs beside T1 and before every P
task.** The answer lets each task run the tests of the landed tasks above it and measure coverage. That
reverses the 2026-11-19 "every task gates only its own tests" rule, which is stated in about 25 files
across `dev`, `backend/_shared`, `qa/_shared`, the qa lanes and the 11 unit- and component-testing skills.

| Option | Verdict | Why |
|---|---|---|
| One task, C1, rewrites the rule everywhere with one wording | chosen | One wording, applied once, before the P tasks trim those files |
| Each owning P task applies P1's wording | rejected | It chains every P task onto P1 and spreads one rule over a dozen sessions |
| A separate plan, 016 | rejected | It leaves this plan's gating lines contradicting the owner's answer until 016 runs |

Cost: one more session. Every P task now also depends on C1.

**D10 (2026-11-20) — T1 kept a name-only list in three `rules` skills instead of dropping the table
everywhere.** The plan says drop the "Loads when" column and its glosses. `desktop-macos`,
`desktop-windows` and `mobile-ios` count their files by the table's order ("leaving test files out of the
first four"), and `desktop-windows` marks lane-only files. `data` keeps its `Installed` column.

| Option | Verdict | Why |
|---|---|---|
| Drop the table in 19 files; keep a name-only list or the `Installed` column in the other 4 | chosen | Nothing is cached that `paths:` or `ls` shows, and no positional reference breaks |
| Drop the table in all 23 | rejected | It leaves "the first four" and "(WPF only)" pointing at nothing |
| Keep a name-only table in all 23 | rejected | It caches an `ls` in 19 files that nothing refers to |

Cost: four files differ in shape from the other 19. P8 and P10 may therefore still see a file list there.

**D11 (2026-11-20) — T1 did not edit `security-governance.md:40`, so T1's gate shows one finding.** The
lint scans the folder of a `SKILL.md` it is given, and finds the `TBD` marker P12 owns. The edit was refused
as outside T1's files. Cost: T1's `0 findings` is not reachable until P12 lands. P12's row is unchanged.

**D12 (2026-11-20) — P1 left `rules/plans.md` at 6,876 chars, not under R23's 6,000.** The plan says keep the
constraints and point at plan-format for the procedure. P1 did that: it turned the close-out section into four
constraint lines, the order, documentation and `TD` rows into pointers, and the stack-runs sentences into a
pointer. What remains is the checkable constraints and C1's gate rule (O12), about 1,600 chars of it.

| Option | Verdict | Why |
|---|---|---|
| Stop at 6,876; every remaining line is a constraint with a severity | chosen | A reviewer reads these lines as findings, and `plans.md` is the rule file for plans |
| Cut below 6,000 | rejected | It drops a *blocker* or *major* constraint, or C1's O12 wording |
| Treat `plans.md` as a non-core file with the 2,500 limit | rejected | The limit cannot hold the constraints of a plan |

Cost: G1's R23 sweep still lists `plans.md` unless the owner reads the row as met by the pointers.

**D14 (2026-11-20) — P7 went past the audit's rows in four small places.** The rows name `mobile-android:30` as an R15 defect but give no critique to name; `mobile-android:3` as R17 but only in the findings table's `:3, 17` shorthand; and the "(plan 003)" defect only for the Android `unit-testing` skill.
Reading 1 (the plan): fix exactly the rows. Reading 2 (built): Android step 1 names the critique table, as the iOS and RN agents do, so its Done-when is checkable; the description loses its version pair; and the two sibling skills lose the same "(plan 003)" note. Cost: Android step 1 now asks for a critique table it did not ask for before; two sibling files were edited without a row.

**D14 (2026-11-20) — P4 moved the guide's shape into a reference, and deleted `feature-docs.md`'s Shape section instead of moving it.** The plan says move the shape and procedure of `feature-docs.md:9–40` into the skill `be-feature-documenter` loads. Reading 1 (the plan): copy the text. Reading 2 (built): `doc-business-model` already states every Shape bullet, so a copy would be a second statement (R17). `feature-docs.md` keeps a one-line pointer and two bars. Separately, `doc-business-model` (27,914) could not reach 16,000 by deleting alone, so its guide shape moved to `references/guide-shape.md`. Every guide run needs that file, which R16 would keep inline.

| Option | Verdict | Why |
|---|---|---|
| Move the shape to `guide-shape.md`, behind a "before writing or editing a guide body" pointer, named in both agents' Load cells | chosen | Meets D3 without dropping a rule, and the file is read on every guide run |
| Keep the shape inline and cut other rules | rejected | D3 forbids cutting a rule only this body states |

Cost: a run that skips the pointer writes a guide without the shape; the Load cells and the one-line summary in `SKILL.md` are the guard.


**D15 (2026-11-20) — P6 moved and deleted more than the plan lists, because the listed rows left five bodies over 16,000.** The plan lists R2 for four bodies without a method, and R15, R16, R17, R19 for `error-handling` in place. Reading 1 (the plan): fix exactly those rows and record the overage under D3. Reading 2 (built): also move by branch (R16) and delete echo sections (§2 item 3). `error-handling` reached 16,013 only after its Validation and its notification wiring moved out; `ui-rules` §5–§7 moved, `## Rules` and `## Validation` went; `data-fetching`'s timeout paragraph became a pointer to the one copy in `error-handling`; `basics` lost a Blazor comparison table and a navigation section that restates `react.md`; `animation` lost its `## Rules` and `## What NOT to do` lists. No rule that only one body states was cut.

| Option | Verdict | Why |
|---|---|---|
| Move by branch and delete the echo lists | chosen | Meets D3 with every rule kept in one place, and each moved file has a pointer that names its condition |
| Record the overage under D3 | rejected | Five bodies would stay over 16,000 and `token-audit` would still print them |

Cost: a run that skips a pointer misses the notification wiring, the validation scenarios, the nav/footer rules or the modal-or-route choice; the "Situational surfaces" table and the §5–§7 stubs are the guard.

**D16 (2026-11-20) — P12 moved and deleted more than the plan lists, because the listed rows left three devops bodies over 16,000.** The plan lists R2 for `infra-controls-validation`, `container-runtime-security` and `cloud-posture` without a method, and R16 moves for `cloud-incident-response`. Reading 1 (the plan): fix exactly those rows and record the overage under D3. Reading 2 (built): also move by branch (R16) and delete echo sections (§2 item 3). Each of the three lost its `## Anti-patterns`, whose bullets restate the families, fences and rules above them; their `## Rules` shrank to what no other section states. `infra-controls-validation` moved its CI wiring and its OWASP/ATT&CK per-finding mapping to `references/ci-wiring.md` and `references/finding-mapping.md`. `cloud-posture` moved its CI wiring to `references/ci-wiring.md`. `container-runtime-security` pointed its kube-hunter and Falco sections at the existing `references/{kube-hunter,falco}.md`, which already held the flag table, the Job manifest, the Helm install and the custom rules; it ends at 10,243 bytes. `cloud-incident-response` pointed its per-cloud telemetry table and containment commands at `references/{aws,azure,gcp}-ir.md`, which held both. No rule that only one body states was cut. Cost: a run that skips a pointer misses the CI wiring, the finding mapping or the per-cloud commands; each pointer names its condition.

**D17 (2026-11-20) — P11 moved and deleted more than the plan lists, because the listed rows left all three bodies over 16,000.** The plan lists R2 for `supply-chain-security` and `iac-security` without a method, and R16 for `k8s-security`'s per-tool sections and CI workflow. Reading 1 (the plan): fix exactly those rows and record the overage under D3. Reading 2 (built): also move by branch (R16) and delete echo sections (§2 item 3). Each of the three lost `## Anti-patterns` and `## Rules`, whose bullets restate the sections above them; every guardrail is stated once where its section teaches it (the live-cluster authorization callout in `k8s-security`; keyless-only signing, both verify flags and "sign the digest" in `supply-chain-security`; baseline-only-shrinks and the sensitive plan JSON in `iac-security`). The CI workflows moved to a new `references/ci-wiring.md` in each skill, behind "wiring this into a pipeline". `k8s-security`'s exception YAML moved to `references/exceptions.md`, its per-tool flags and catalogs into the three existing references, and the supply-chain provenance paths A and B, the admission policy and rollout ladder, the cosign v2→v3 notes and the framework mapping into `references/slsa-provenance.md` and `references/cosign-sigstore.md`. `iac-security` moved its flag table and `.checkov.yml` into `references/checkov.md`. No rule that only one body states was cut. Cost: a run that skips a pointer misses the CI wiring, the exceptions file or the per-tool commands; each pointer names its condition.

**D18 (2026-11-20) — P14 went past the plan's rows in three places, and ran its gate with the agent files named one by one.** (1) The gate line passes the folder `qa/java/agents` to `skill-lint`, which exits with `no SKILL.md under qa/java/agents`, because the lint takes a skill folder, an agent `.md` or a rule file. Reading 1 (the plan): run the line as written. Reading 2 (built): pass the seven `qa/java/agents/*.md` files, and the line is otherwise as written. The P17 and P18 gate lines carry the same folder path and need the same change. (2) The plan lists no method for the R2 rows of `api-contract-testing` and `test-quality-check`. Reading 1: fix those rows alone and record the overage under D3. Reading 2 (built): move by branch (§2 item 3), the message-pact section to `references/message-pacts.md` and the separate-repo section to `references/separate-repo.md`, and replace the `## Rules` and `## What NOT to do` lists with seven positive guardrails. (3) T1's note says each agent's `Gate evidence` line belongs to its P task, but P14's list does not name it. Reading 1: leave it. Reading 2 (built): the seven qa-java agents carry the O18 wording. Cost: two new reference files that G1 reads, and the agents lost the per-agent evidence hints (the pass rate over N runs for `qa-llm-java`, the strict-threshold proof for `qa-performance-java`), which the Done-when cells still carry.


**D19 (2026-11-20) — P16 deleted the closing lists of six scanner skills and named the `performance` heading its own way.** (1) The plan lists R2 for seven bodies without a method. Reading 1 (the plan): fix those rows alone and record the overage under D3. Reading 2 (built): apply §2 item 3. `image-infra-scan`, `code-scan`, `known-vuln-scan`, `active-scan`, `secrets-scan`, `certificate-scan` and `api-spec-assets` lost their `## Anti-patterns`, and the six scanners their `## Rules (hard constraints)`, whose bullets restate the sections above them. A rule only the list stated stayed, as `## Guardrails` (`active-scan`: bounded durations and the parsed-SARIF gate; `secrets-scan`: a live true-positive is rotated, never allowlisted; `certificate-scan` and `known-vuln-scan`: no secrets in scan config; `known-vuln-scan`: wait on readiness) or as one line in the body (`image-infra-scan`: no secrets in scan config). `api-spec-assets` moved its renamed-spec variant to `references/renamed-spec.md`. (2) The audit's R6 suggestion names "Profiler hand-off", but the flagged `performance` heading is "When NOT to use any of these tools", a list of other skills. Reading 1: rename it "Profiler hand-off". Reading 2 (built): "Work that belongs to other skills"; the real profiler section keeps its own heading. `contract-testing-pact` became one `## Choosing Pact` section with "Use Pact when" and "Use something else when" lists. Cost: a run that skips a pointer misses the renamed-spec commands.

**D20 (2026-11-20) — P17 deleted the closing lists of five skills and applied O18 to all seven agents, beyond the plan's rows.** (1) The plan lists R2 for five bodies without a method. Reading 1 (the plan): fix those rows alone and record the overage under D3. Reading 2 (built): apply §2 item 3. `passive-scan`, `permission-testing` and `dependency-scan` lost their `## Rules (hard constraints)`, `api-tests-grpc` lost it and its `## Examples` and "Ported from" paragraph, and `failure-injection-testing` lost the same pair and its "port of the canonical" paragraph, because their bullets restate the sections above them. A rule only the list stated stayed: `failure-injection-testing` gained the anti-pattern "raw `proxy.Add(…)` in a `[Test]`", and `permission-testing` gained the line "tag each case with its OWASP API id and WSTG-ATHZ test id". The two programmatic listings of `passive-scan` moved to `references/programmatic-path.md`, and the API3 section of `permission-testing` to `references/object-property.md`, each behind a pointer that names the condition. (2) The plan's P17 rows list the Fix line and the O20 (b) clause for the agents but not the `Gate evidence` line. Reading 1: leave it. Reading 2 (built): the template's Close-out note says each agent's `Gate evidence` line belongs to its P task, so all seven carry the O18 wording. (3) `desktop-tests.md` needed 900 characters cut, more than the R23 row implies. The cuts: the driver pins (now "`desktop-project-setup`"), the window-switch commands (now "`desktop-window-objects`"), the "returns the destination's window object" clause (`page-objects.md` states it), and wording. Cost: a desktop rule file points at two skills for facts it used to carry. The `WEBVIEW2_USER_DATA_FOLDER` per-worker note left the rule file and stays in `desktop-project-setup`.

**D21 (2026-11-20) — P19 renamed the knowledge base's *slice* in the body text of seven files, not only in the headings and table headers.** O3 (a) names the headings and headers. Reading 1 (the plan): rename those six lines and leave "slice id", "KB slice" and "the slice depth" in the prose, which then disagrees with its own headers. Reading 2 (built): rename the term in `cross-feature-test-design` (`SKILL.md`, `example-cancel-booking.md`), `requirements-breakdown` (`SKILL.md`, `connections.md`), `test-case-writer/SKILL.md:39`, `qa-test-case-designer.md` and `qa-test-planner.md`, so "cross-section id" and "`KB cross-section @ <date>`" read the same everywhere. `bug-report-writer/SKILL.md:23` ("the relevant slice" of a log) and the JavaScript `.slice(` calls in `probes.md` are not the knowledge-base term and stay. Cost: the `Built from:` line of a basis now says `KB cross-section @ <date>`, so a basis written before this edit says `KB slice`.

**D12 (2026-11-20) — The flag D5 adds does not clear R3 or R6, so P2 rewrote the five descriptions and renamed three headings.** D5 and P2 read the flag as clearing both. `tools/skill-lint.py` still applies R3 (description shape) to a hidden skill and R6 (no routing heading) to it. Reading 1 (the plan): add the flag only, and the gate keeps 17 findings. Reading 2 (built): add the flag, then give each of the five a description of the shape `Use when …. Triggers "…". Not for … (sibling).`, and rename `## Handoffs` (`code-comments`, `agent-orientation-cache`) to `## Applied by` and `## Where else things live`, and `## When to Use WebFetch` (`claude-api`) to `## Fetching live documentation`. Cost: five descriptions lost their "Do NOT invoke directly" wording. The flag now states that. Another task that adds the flag to a skill must do the same, or change the lint.

**D13 (2026-11-20) — P3 moved more of `delivery-plan` than the plan lists, because the listed moves left it near 38,000 chars.** The plan lists the shape and reconcile moves and the R17 and R19 cuts, and names the gate as no `token-audit` line. Reading 1 (the plan): make only those moves, and record the remaining overage under D3. Reading 2 (built): also move by branch, so the file ends at 14,790. New references: `references/task-block-rules.md` (frontend, rendering, signals, batch, `Q` and `TD` rules, read when a task is of that kind) and `references/self-check.md` (read before handing off). The inline `B3` and `Q1` task blocks, the plan template and the Mission Control block were deleted, because `references/example-delivery-plan.md` carries each filled. The "Tracking execution" section was deleted, because plan-format §7 owns it. `references/reconcile.md` is where `solution-planner.md:68` now points (P4's `:68` row, rewritten in its block). Cost: a planner follows two more pointers, and the Step 4 rules that apply to every task stay inline.

**D22 (2026-11-20) — P20 bundled `requirements-author`'s skills into `dev` by moving five registrations, and the labels changed with them.** O10 (b) says bundle what the agent loads into `dev`. `plugin-surface-check` forbids a skill registered by two categories, so a bundle is a move, not a copy.

| Option | Verdict | Why |
|---|---|---|
| Move `ba-scoping-writeup`, `ba-epic-writer`, `ba-story-writer`, `ba-story-quality-review` and `ba-project-memory` from `business-analysis` to `dev`, listed first in `dev`'s `skills` | chosen | `business-analysis` depends on `dev`, so it keeps all five, and `dev` alone now has what `/dev:refine` loads |
| Also move `qa/manual/requirements-breakdown` | rejected | It is registered in `qa-java`, `qa-dotnet` and `qa-typescript` (category `qa`), and moving it renames `qa-<stack>:requirements-breakdown` in about a dozen qa files. The agent already loads it by its path, which resolves because the plugin root is the repo |
| Also move the `rules` skill | rejected | `dev` has its own `rules`. The agent reads `business-analysis/skills/rules/` by path when the project has none |

Reading 1 (the plan): list the bundle and make it, with no word on names. Reading 2 (built): the labels are `dev:scoping`, `dev:epics`, `dev:stories`, `dev:story-review` and `dev:knowledge-base`. P20 changed them in its own paths, in `README.md` and in `docs/skills-catalog.md`. About 20 files outside P20's paths still say `business-analysis:<label>`, and G1 renames them (P20's `As built`). Cost: `/business-analysis:stories` no longer exists, and `/dev:stories` does.

**D23 (2026-11-20) — P20 went past the plan's rows in three small places.** (1) The gate line passes the folders `business-analysis/agents` and `training-data/agents`, which `skill-lint` rejects (D18). Reading 1 (the plan): run the line as written. Reading 2 (built): pass the agent files one by one. (2) The audit's R18 row for `business-analyst.md` names `:19` and `:60`, but `:19` holds a positive line ("Model only what a question demands") and only `:60` carries the prohibition. Reading 2: fix `:60` and leave `:19`. (3) The audit suggests `references/feature-slice.md`. O3 (a) renamed the term, so the file is `references/feature-cross-section.md`, its H1 is "Feature cross-section", and the `ba-project-memory` heading is "Connection cross-section". Cost: `ba-feature-conflict-check/SKILL.md:40` still says "feature slice" until G1.

**D24 (2026-11-20) — G1 fixed items beyond the audit's rows and left others, because the outside-my-paths notes asked for both.** The plan says fix each outside-my-paths item in place and send new findings outside 004's rules to a round-2 audit. Reading 1 (the plan): fix every item the notes list. Reading 2 (built): fix those that name an audit rule or a logical conflict (the `dev:` labels, "feature slice", R21 example comments, the `cosmosdb` repository, the stale `Llm` sample, the test-body `switch`, the floating versions, the version restatements in two agent descriptions), and leave the five that are not findings under the rule they would be filed under (`name:` values, a routing line, an "Out of scope:" line that names its owners). Cost: the left items are named in G1's `As built`, and a reader who disagrees reopens them in round 2.

## Answered questions (2026-11-20)

- **O1 — How R8 resolves a pointer: (a). R8 is reworded to the lint's reading. A pointer resolves relative to its file's folder, or inside a skill named in a code span on the same line or the line above. D16 stays, so there is no T2.**
- **O2 — The list of stacks: (a). Plan-format §4 is the one list. `writing-plans` and `delivery-plan` point at it and drop every count.**
- **O3 — *Slice* as the knowledge base's term: (a). It is renamed *cross-section* in those headings and table headers. There is no R11 exception.**
- **O4 — *Phase* in the migrations table: (a). The table header becomes "Step".**
- **O5 — The list of house words: (a). The list lives once, at `writing-for-agents` "Leading words" (`:73`), and the R20 row points at it.**
- **O6 — Where a test believed wrong is recorded: (a). Both rows say "a dated `D<n>` in the plan's open issues and the final message".**
- **O7 — The URL assertion in a .NET test body: (a). The URL is asserted through a page-object member.**
- **O8 — `selector` or `locator`: (a). The rule says `this.locator("key")`.**
- **O9 — `test.step` in the TypeScript lane: (a). It is added to the `LoginPage` example.**
- **O10 — What `/dev:refine` loads that `dev` lacks: (b). What it loads is bundled into `dev`. P20 lists the bundle and makes it.**
- **O11 — Six or three default looks: (a). One reference with no count, everywhere: "the default looks in `visual-identity` Calibration".**
- **O12 — What a plan task runs and measures: the owner's own reading, neither (a) nor (b). A task runs its own tests plus the tests that the landed tasks above it in the same plan wrote, except acceptance tests bound to a deliverable that no landed task has built yet. It measures the branch-coverage floor over the files that it and those tasks touched. The last runnable task stays the full gate: the smoke suite, every test the plan wrote, and the coverage floor. Task C1 rewrites the rule wherever it is stated (D9), and P5–P9 no longer carry O12.**
- **O13 — The kube-bench ids: (a). They live only in `references/kube-bench.md`, checked against the current release, and the skill points at it.**
- **O14 — A failed refetch over data already shown: (a). The region is `failed` only when `q.data === undefined`. Otherwise it is `loaded`, with `stale={q.isError && q.data !== undefined}`.**
- **O15 — The DynamoDB repository: (a). "Wrap it in a repository only when a second store or a test seam needs it."**
- **O16 — Rust trace correlation: (a). Add the Rust row. The smoke query uses `{service=…, environment=…}`.**
- **O17 — Where `security-architect` may write: (a). `docs/audits/` is added at `:21`.**
- **O18 — Coverage in `Gate evidence`: the owner's own reading, which follows from O12. The template and every agent say `Gate evidence: <the Gate: line's commands and results, including coverage>`.**
- **O19 — be-java and be-dotnet: (a). be-java gains the `auth/_shared` row and the telemetry-base line.**
- **O20 — The "a test believed wrong stays red" sentence: (b). It is dropped from the template and from all 30 agents that carry it. `CLAUDE.md` "Planning" and plan-format keep the rule. `qa-ui-typescript` already lacks it.**
- **O21 — Clarifying questions in the `qa-ui-*` agents: the owner's own reading, neither (a) nor (b). All three say "Ask as many clarifying questions as needed." This departs from `CLAUDE.md` "When uncertain", which says to ask one, on the owner's word.**
- **O22 — How `design-auditor` enters the standards-audit engine: (a). The engine says "through a stack's `standards-audit` skill or `design-auditor`".**
- **O23 — The CLI destructive-action gate: (a). The rule owns it (`--yes` and `--dry-run`), and the skill's restatement is deleted.**
- **O24 — The synthetic-envelope example: (a). The example is fixed to match the rule.**

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
- **As built (2026-11-20):** The owner answered all of O1–O24, and none was deferred. The answers are in
  `## Answered questions (2026-11-20)`, and §5's table is gone.
  - The questions went out in eight rounds through the question tool, not in one message (D8).
  - Three answers are the owner's own wording. Each is written into its prompt blocks:
    - O12 adds task C1, its section and its prompt (D9), and its rows leave P5–P9.
    - O18 goes into T1, P5–P9 and P20.
    - O21 goes into P14, P17 and P18.
  - O20 (b) was confirmed as "the template and all 30 agents". T1, P5–P11, P14, P17, P19 and P20 each
    carry its edit for their own agents.
  - No answer changes the lint, so there is no T2.
  - Every P block and G1 now depends on C1.
  - Proof: `grep -c '^- \*\*O[0-9]* — ' docs/plans/015-skill-authoring-remediation.md` gives 24.

### C1 — The plan-task gating rule, everywhere it is stated (O12)

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** every file listed below states O12's rule in the wording below. No line left in them
says that a task never runs an earlier task's tests, or that only the gate task measures coverage.
**Depends on:** L1. Runs beside T1, because their files are disjoint.
**Budget:** ~130k.
- `CLAUDE.md`: 25k.
- O12's answer and D9: 2k.
- plan-format §5: ~8k to read and ~4k written.
- `rules/plans.md`: 3k.
- The other ~25 files, read about 20 lines around each grep hit: ~35k read and ~20k written.
- Gate output: 3k.

**Gate: own tests.**
- The old-rule grep below prints nothing over C1's paths.
- `python3 tools/skill-lint.py <C1's skill paths>` prints no more findings than it did before C1. Record
  both counts in `As built`.
- `python3 tools/plugin-surface-check.py` gives `OK`.

**The wording.** Each file keeps its own voice and length, but it says the same thing. The core rule,
for `CLAUDE.md` "Planning" and plan-format §5:

> **Every task gates its own work and the work landed above it.** Before it commits, a task builds what it
> touched and runs:
> - its own tests;
> - the tests that the landed tasks above it in the same plan wrote, except acceptance tests bound to a
>   deliverable that no landed task has built yet (those first run in the task that builds the
>   deliverable, or in the gate task);
> - the branch-coverage floor, measured over the files that it and those tasks touched.
>
> It runs on a small core budget, on ports of its own, and never under a machine-wide test lock. The
> last runnable task stays the plan's one run under the project's test lock: the smoke suite, every
> test the plan wrote, and the coverage floor.

In the unit- and component-testing skills: "Inside a plan task, the `Gate:` line runs this over the files
the task and the landed tasks above it touched. Outside a plan, run it before you report."

**Find the sites first.** Run this over the paths below:

```bash
grep -rn -e "own tests" -e "earlier task" -e "coverage run" -e "coverage measure" -e "only its own" <paths>
```

Each line it prints either changes to the new rule, or `As built` names it as unrelated.

**The paths.**
- `CLAUDE.md`, two places in "Planning":
  - the bullet "Every task gates only its own tests (2026-11-19)";
  - in the "In review" bullet, the clause naming an intermediate task that runs another task's tests or
    a coverage run as a major finding. Narrow it to running another plan's tests or the unfiltered suite.
- `engineering-practices/writing-plans/references/plan-format.md`: §5 (`:195–206`, `:270–280`) and every
  other hit.
- `engineering-practices/rules/plans.md`.
- `engineering-practices/writing-plans/SKILL.md`.
- `engineering-practices/verify-before-done/SKILL.md`.
- `engineering-practices/quality-constraints/SKILL.md`.
- `backend/_shared/delivery-plan/SKILL.md` and `references/example-delivery-plan.md`.
- `backend/_shared/session-budget/SKILL.md` and `references/prompts-section-template.md`.
- `backend/_shared/codebase-survey/references/documentation-plan.md`.
- `qa/_shared/test-first/SKILL.md` and `qa/_shared/test-audit/SKILL.md`.
- `qa/{dotnet,java,typescript}/skills/api-contract-testing/SKILL.md`.
- `docs/skills-catalog.md`.
- The testing skills:
  - `frontend/{blazor,react}/skills/component-testing/SKILL.md`;
  - `mobile/react-native/skills/component-testing/SKILL.md`;
  - `mobile/{ios,android}/skills/unit-testing/SKILL.md`;
  - `desktop/windows/skills/unit-testing/SKILL.md`;
  - `backend/{dotnet,java,node,python,rust}/skills/unit-testing/SKILL.md`;
  - `backend/rust/skills/database-code/SKILL.md`.

**Not in C1:**
- `docs/plans/**`. Filed plans are never edited, and `007-test-first-delivery.md` is another plan's.
- `backend/_shared/business-documentation/evals/fixture-delivery/**`, an eval fixture.
- Every audit finding in these files. Those are the P tasks' rows (§2 item 11).
- **As built (2026-11-20):** O12's rule is in every listed file, in one wording, and the old-rule grep prints
  nothing over C1's paths.
  - `CLAUDE.md:76` is the new bullet "Every task gates its own work and the work landed above it". The "In
    review" bullet (`:85`) now names a task that runs another plan's tests or the unfiltered suite.
  - plan-format §5 (`:188–209`, `:275–296`) states the rule and the table row, and its halfway-stop line
    (`:354`) follows it. The §5 heading changed, and its R9 contents-list finding stays the one it was.
  - `Gate: own tests` stays the label of the gate line. The rule changes what it runs, not its name.
  - The 9 unit- and component-testing skills with a `Measure` bullet read "Inside a plan task, the `Gate:` line
    runs this over the files the task and the landed tasks above it touched. Outside a plan, run it before
    you report". `desktop/windows` gained that sentence in its Coverage bullet, and `backend/rust` carries it
    in step 6.
  - `qa/_shared/test-first` now says the own-tests filter runs with the landed tasks' tests.
  - `delivery-plan`'s example plan names the landed tasks' tests and a coverage read in the `C4`, `Q1`, `B2`
    and `F2` gates, and in D4 and D5.
  - Unrelated hits, left as they were: `quality-constraints:36` (a coverage-config exclusion),
    `session-budget/references/prompts-section-template.md:49` and `writing-plans/SKILL.md:363` ("its own
    files"), `documentation-plan.md:40,61` (the doc lint is a documenter task's check), the three
    `api-contract-testing` descriptions ("one API's own tests"), `test-audit:75`, `desktop/windows:112,185`,
    `backend/rust/skills/database-code:181`, `backend/rust/skills/unit-testing:157`, `CLAUDE.md:80`.
  - Lint, over the 22 `SKILL.md` paths: 8 findings before C1, 8 after. It is the same set. Over every C1
    file it can read, 8 before and 8 after.
  - `python3 tools/plugin-surface-check.py` prints `OK`.
  - The old-rule grep over the whole repo, `docs/plans/` excluded, prints nothing. `docs/plans/**` and the
    eval fixture were left alone, as the task says.

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
- `.skill-template/agent.md:51`, O18: the line becomes
  `Gate evidence: <the Gate: line's commands and results, including coverage>`.
- `.skill-template/agent.md:38`, O20 (b): delete the clause from "a test you believe is wrong stays as it
  is and red" through "The close-out gate rules on it.", and keep the read-only clause before it.
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
- **As built (2026-11-20):** every deliverable line exists and the gate is green except one finding that
  is not T1's. Proof, from the repo root:
  - `.skill-template/agent.md:33` ends "…then sweep: every sibling sharing the defect's pattern fixed or
    listed in the report." `:38` stops after "never edit, skip or weaken one." `:51` reads
    `Gate evidence: <the Gate: line's commands and results, including coverage>`.
  - `engineering-practices/writing-for-agents/SKILL.md:102` (R8) carries O1's wording, and the R20 row
    (`:114`) points at "Leading words" (`:73`), which is now the one list. O3 and O4 were answered (a), so
    the R11 row has no exception.
  - The 23 `rules` SKILL.md: `python3 tools/skill-lint.py` over them and `writing-for-agents` gives
    `1 finding`, `security/rules-security-governance/security-governance.md:40: R10 'TBD'`. That is a rule
    file beside a SKILL.md, P12's row, and T1 did not edit it (an attempted edit was refused as outside
    T1's files). The plan's `0 findings` gate for T1 cannot reach 0 until P12 lands. `token-audit` lists no
    `rules` skill (its two hits for the plan's grep are `frontend/{react,blazor}/skills/ui-rules/SKILL.md`,
    P5 and P6's). `plugin-surface-check` prints `OK`. `pytest tools/test_skill_lint.py` gives 95 passed.
  - **Rows that differed at their line (§2 item 1):**
    - R2: no description had a parenthetical list. All 19 were cut to ≤ 200 characters by dropping
      " as path-scoped rules" ("as a path-scoped rule" in `tooling`), and "test-automation " as well in
      `qa-java`. The trigger and the sibling stay.
    - R19 "so a session that never … never pays for …": found in 20 files, not 22. `data` and
      `training-data` carry no such clause (they say what a backend session gets without the agent, which
      the plan keeps as it keeps `tooling`'s). `business-analysis` and `devops` had the clause as a second
      half of a longer sentence, and only that half was deleted. `desktop-windows` also said "Install all
      twelve", now "Install every file".
    - R17 step 2: `design` also said "These two files" in its intro, now "These files".
  - **Table (D10):** removed in 19 files; kept as a name-only list in `desktop-macos`, `desktop-windows` and
    `mobile-ios` (step 5 counts "the first four" or "the first six" files by it, and `desktop-windows` marks
    WinUI, WPF, WinForms and C++/WinRT only files); kept as a `File | Installed` table in `data`, where the
    column is the install rule and not a copy of `paths:`.
  - **R16:** the unattended paragraph is one sentence inline. Its remainder went under step 4 ("With nobody to
    ask and no argument, write the plugin's copy beside it") and step 5 ("change no path and list each
    proposed glob under `Waiting for the user:`"). The heading "Run by a person or by a model" became "Run by
    a model", because the person sentence went (R19).
  - **R15:** steps 3, 4, 5 and 7 end on a done-when in 21 files. `data` has two detection steps first, so
    its steps 3, 4, 5, 6, 7 and 9 each got one. `tooling` names `tool-contract.md` in steps 3 and 4.
  - **R7:** both headings are at the end of each file, one line each, as D4 words them.
  - `engineering-practices/rules/SKILL.md` (dev): step 2 kept its form, minus "or a file named in the table
    above is missing"; the sentence "Every `*.md` beside this SKILL.md … is a rule file" went, because step 2
    says it.
  - Not verified: no skill was run end to end; the rules skills were edited as text.

### P1 — dev: the planning and verification front doors

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** these files give `0 findings` under the lint, and `token-audit` no longer lists
`writing-plans`: `engineering-practices/{writing-plans,systematic-debugging,verify-before-done,quality-constraints,source-grounding,notebooklm,brainstorming}`
and `engineering-practices/rules/plans.md`. Every row below is fixed or named as dropped.
**Depends on:** L1, T1, C1.
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
- **O12 is C1's.** C1 has already rewritten the gating rule in plan-format §5, `rules/plans.md`, `writing-plans` and `verify-before-done`. P1's R16, R17 and R23 edits keep that wording as C1 wrote it.
- **Not in P1:** `engineering-practices/rules/SKILL.md` (T1), and `engineering-practices/rules/feature-docs.md` (P4).
- **As built (2026-11-20):** every row is fixed or named below. Proof, from the repo root:
  - `python3 tools/skill-lint.py` over the eight P1 paths prints `0 findings`. `python3 tools/token-audit.py --violations-only | grep -E 'writing-plans|systematic-debugging|verify-before-done|quality-constraints|source-grounding|notebooklm|brainstorming'` prints nothing. `writing-plans/SKILL.md` was 26,046 chars (25,659 body, after C1) and is 16,286 with frontmatter (under 16,000 body).
  - `python3 tools/plugin-surface-check.py` prints one line, `dev: description of 'plan-experience' holds an unquoted ': ' (backend/_shared/experience-plan)`, and exits 1. That file is P3's, edited beside P1 (its description line differs from `HEAD`); P1 touched nothing there. It is unverified until P3 lands.
  - R16 moves: `writing-plans` web-route rendering and self-review item 16 moved to `engineering-practices/writing-plans/references/web-routes.md`, behind "A web route in the plan → read …" in Step 1 and self-review item 15. `systematic-debugging` Step 1 item 4 moved, with its `# Layer` comments deleted (R21), to `engineering-practices/systematic-debugging/references/multi-component.md`, behind "The bug crosses component boundaries → read …".
  - `writing-plans`: R17 pointers replace the two-closing-tasks bullet, the gate bullet, the close-out bullet, the halfway-stop paragraph and the test-first order bullet (plan-format §4, §5, §6, §7 and `rules/plans.md`). The stack list is gone (O2), as is the "eight" count. Self-review items are written as criteria (R20), and the two that restated plan-format §5 (gate, documentation) point at it. Steps 1–6 each end on a `Done when`. Added: `## When to use`, `## When NOT to use` (siblings `feature` and `/dev:plan-system`). R19: "DRY. YAGNI. Frequent commits.", "You reason best…", the worked budget example and the "In existing codebases" bullet are deleted.
  - C1's gating wording kept in `plans.md` and `verify-before-done`. In `plans.md` the two sentences that listed what a non-frontend and a frontend task run are replaced by "What each stack runs is plan-format §5's", which states them (`plan-format.md` §5, lines 204–207 before the contents list).
  - `plan-format.md` R9: a `**Contents:**` list of the nine `##` headings follows the H1.
  - `systematic-debugging`: `(feature)` at `:3`; `## When NOT to use`; Steps 1–3 end on a `Done when`; the table column is "Done when"; R18 rewrites at `:27, 36, 105, 131, 148–149`; R19 deletes at `:28` and `:100`.
  - `verify-before-done`: "The evidence check" (and `:14`'s "evidence check"); "Why This Matters", the `:12` sentence and the `:10` repeat deleted; `## When to use` and `## When NOT to use` added (the old "When To Apply" became the first).
  - `quality-constraints`: rows 33, 34, 36, 38, 40 point at `CLAUDE.md` "Test code rules" or `plans.md`; the red-test rows say "a dated `D<n>` in the plan's open issues and the final message" (O6); "When a gate goes red" ends on a done-when; "check" became *gate* and *evidence* (`:10, 17, 42, 45`).
  - `source-grounding`: Steps 1–4 each end on a `Done when`; the Overview and "Common mistakes" are deleted; the source list opens "Use only official docs…". `notebooklm`: `scripts/run.py` and `scripts/config.py` now point at `engineering-practices/bundled/notebooklm/scripts/…`, steps 1–4 end on a `Done when`, the pins point at `requirements.txt`, `:8` is deleted, `## When to use` and `## When NOT to use` are added. `brainstorming`: `:20` says "design approval", the design rules point at `CLAUDE.md` "Simplicity (KISS)" and the read-2–3-files rule.
  - **Dropped row:** `systematic-debugging/SKILL.md:16` (R19). The row quotes "They often contain the exact solution", which is at `:28` and is deleted there; `:16` holds the "matters most when guessing is tempting" paragraph, which changes behaviour, so it stays.
  - **Not met:** `rules/plans.md` is 6,876 chars (8,444 before), not 6,000. See D12.

### P2 — dev: the audit front doors and the unregistered skills

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `spec-vs-code-audit` and `feature-audit` are under 16,000 chars. Mode B of each is in
`references/re-audit.md`. These all give `0 findings` under the lint:
`engineering-practices/{spec-vs-code-audit,feature-audit,standards-audit-engine,agent-orientation-cache,code-comments}`,
`ai-development/{claude-api,mcp-builder}` and `engineering-practices/agents/code-auditor.md`.
**Depends on:** L1, T1, C1.
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
- **As built (2026-11-20):** every deliverable line exists. Proof, from the repo root:
  - `python3 tools/skill-lint.py` over the eight P2 paths prints `0 findings`. `python3 tools/token-audit.py --violations-only | grep -E 'spec-vs-code-audit|feature-audit'` prints nothing. `spec-vs-code-audit/SKILL.md` was 24,887 chars and `feature-audit/SKILL.md` 19,996. Both are under 16,000 now.
  - Mode B of each moved whole, with its done-whens, to `engineering-practices/{spec-vs-code-audit,feature-audit}/references/re-audit.md`. Each `SKILL.md` carries a "A register and a prior report exist →" (feature-audit: "A prior report exists →") pointer under `## The two modes`.
  - R15 done-whens are on Mode A steps 2–4 of `spec-vs-code-audit` and steps 2–5 of `feature-audit`, and on step 1 of Mode B and the Mode B report step in both reference files. R17 pointers name `audits.md` for the id, class, Resolved and section-summary rules. The class table stays in `spec-vs-code-audit`. `feature-audit` keeps only its "Typical here" column and points at that table. R19: the read-only restatements, the Evidence-rules repeat in each `## Rules`, and `standards-audit-engine`'s `## When uncertain` (all but the scope-ambiguity bullet) are deleted.
  - `standards-audit-engine/SKILL.md` description is now "Use when a stack's `standards-audit` skill (`/<plugin>:audit`) or the `design-auditor` starts a conformance round. Triggers …" (O22). Line 8 names `design-auditor` beside the stack skill. Its severity table is replaced by the pointer to `CLAUDE.md` "Review behavior", and the impact-qualifier sentence stays.
  - `disable-model-invocation: true` is in the five frontmatters. `code-auditor.md:51` now starts `Mode: A — BASELINE | B — RE-AUDIT round <N> · …`.
  - **Divergence (D12):** the flag alone did not clear R3 and R6 in the lint. P2 fixed them in the five files too.
  - `python3 tools/plugin-surface-check.py` prints `dev: description of 'plan-experience' holds an unquoted ': ' (backend/_shared/experience-plan)`, exit 1. That is P3's file, edited in this working tree while P2 ran. No P2 file is named. **Unverified:** that the check reads `OK` once P3 lands. G1 re-runs it.

### P3 — dev: `delivery-plan`, `session-budget`, `experience-plan`

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `backend/_shared/delivery-plan` and `backend/_shared/session-budget` are under 16,000
chars. `experience-plan`'s description is ≤ 200. All three folders give `0 findings` under the lint.
**Depends on:** L1, T1, C1.
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
- **As built (2026-11-20):** all three folders lint `0 findings`, `token-audit` prints nothing for them, and `plugin-surface-check` prints `OK`.
  - `delivery-plan/SKILL.md` 74,413 → 14,790 chars. Shapes are `references/shape-{feature-complete,agent-batched,platform-first}.md` behind the "Sequencing shape:" table in Step 2. The reconcile procedure is `references/reconcile.md`, behind the line after the prerequisites. The gate restatements, the §4 bullets, the preamble and the close-out paraphrase are one pointer each. "Out of scope" is `Not in <id>`. The stack list is "the `plan-format.md` §4 list" in Step 1, Step 4 and `self-check.md` item 5 (the `:687` row, O2). Extra moves are D13.
  - Rows dropped: none. `:88` and `:421` still resolve (`SKILL.md` Output line, `task-block-rules.md`). The audit's `:559` parenthetical went with the "Tracking" section.
  - `session-budget/SKILL.md` 17,140 → 15,949: the gate line and the close-out paragraph point at plan-format §5 and §7, and self-check item 6 and the `Rules` lead are shorter.
  - `experience-plan`: the description is 186 chars, with no `: ` (the first draft broke YAML and `plugin-surface-check` caught it). `:159` has `[TBD]` in a code span.
  - R9: `**Contents:**` lists in `example-delivery-plan.md` and `prompts-section-template.md`.
  - Unverified: that a planner still reaches the `task-block-rules.md` rules. Nothing ran a plan through the slimmer skill.
  - For G1: `backend/_shared/agents/solution-planner.md:68` and `docs/skills-catalog.md` still name the reconcile procedure by its old heading, which now sits in `references/reconcile.md`. The first is P4's row. `example-delivery-plan.md:571` says "Out of scope:" inside a prompt block, outside P3's row.

### P4 — dev: `solution-blueprint`, `business-documentation`, `feature-trace` and the planning and documenting agents

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** these are under budget: `solution-blueprint` and `business-documentation` (16,000), and `be-documenter.md` and `solution-planner.md` (14,000). Each path below gives `0 findings` under the lint. `rules/feature-docs.md` is ≤ 6,000.
**Depends on:** L1, T1, C1.
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
- **As built (2026-11-20):** every path in the gate lints `0 findings`, `token-audit` prints nothing for the four files, `feature-docs.md` is 5,962 bytes, and `plugin-surface-check` prints `OK`.
  - `solution-blueprint/SKILL.md` 30,276 → 16,179 chars with frontmatter (body under 16,000). Three moves, each behind a condition: `references/architecture-style.md` (greenfield or a live architecture decision, Step 3), `references/key-flows-and-decisions.md` (a flow or a 3+-input rule, Step 3.5), `references/blueprint-template.md` (before writing `blueprint.md`). The rest is R17/R19 trimming.
  - `business-documentation/SKILL.md` 27,914 → 14,146. The guide's skeleton, task format, sections, stamp and length limit are `references/guide-shape.md`; REFRESH/AREA/CAPTURE is `references/run-modes.md`. R3: the description now has `Triggers "…"` and ends `Not for tracing code (doc-feature-trace).`. The Reconcile section keeps one line per step and points at `references/reconcile.md`.
  - `example-area.md` R8: the four sibling links are `(<bookings>.md)` and `(<scheduling>.md)`, patterns the lint skips, with one sentence in the intro saying so. `trace-recipes.md` R9: `**Contents:**` replaces the `Parts:` line.
  - `be-documenter.md` 17,599 → 13,977: the delivery-chain diagram is a pointer to `solution-planner.md`, the mode paragraph is `business-documentation/references/run-modes.md`, plus R17 trims. `solution-planner.md` 16,835 → 13,977: the Step 9 cross-artifact checks are `solution-blueprint/references/pack-cross-checks.md` (named in the Step 9 Load cell), RESUME points at `delivery-plan/references/reconcile.md` (R12 at `:68` fixed; P3's note about the old heading is closed), and the chain bullets point at `plans.md`. `be-feature-documenter.md`: `## Report` opens with `Mode: WRITE | UPDATE | CAPTURE | DOC1`. Both documenter agents' Step Load cells name `references/guide-shape.md`.
  - `feature-docs.md` 10,500 → 5,962 bytes. The Shape section was already stated in `doc-business-model`, so it became one pointer plus two kept bars (every role, no formula in a task). Its constraints, the language and screenshot rules and `paths:` are kept (D14).
  - Unverified: that a documenter run reaches `guide-shape.md` from the Load cell, and that the blueprint, run through a planner, still finds its template. Nothing ran either skill.
  - For G1: `docs/skills-catalog.md` may still describe the moved sections by their old headings (`The guide`, the blueprint template).

### P5 — design and fe-blazor

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each path below gives `0 findings` under the lint. `fe-blazor`'s `ui-rules`, `basics` and `auth0-blazor` are under 16,000 chars.
**Depends on:** L1, T1, C1.
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
- **O20 (b).** In frontend/blazor/agents/fe-blazor.md: delete the clause that a test you believe is wrong stays red and is recorded as a dated `D<n>`, through "The close-out gate rules on it." Keep the read-only clause before it.
- **Not in P5:** `design/rules` and `frontend/blazor/skills/rules` (T1), and `standards-audit-engine` (P2).
- **As built (2026-11-20):** every path in the gate lints `0 findings`, `token-audit` prints nothing for `frontend/blazor` or `auth0-blazor`, and `plugin-surface-check` prints `OK`. `pytest tools` gives 95 passed.
  - `design-auditor.md`: the report-template pointer is the engine's full path, `## Report` opens `Mode: A — BASELINE | B — RE-AUDIT`, step 4 and 6 name states, the fourteen-skills count is gone, and the four "Never" lines carry their targets. The Claude-in-Chrome protocol is `design/ux-review/references/claude-in-chrome.md` (new), behind one Invariants line.
  - The five `pro-rules` pointers (`design-tokens:23`, `iconography:23`, `motion:23`, `ux-patterns:31`, `visual-identity:32`) name `design/ui-ux-pro-max/references/pro-rules.md`.
  - `visual-identity/SKILL.md` 16,199 → 15,528 bytes: heading `# Visual identity`; the studio paragraph, "Not taking a risk…" and the Chanel sentence are gone; every corpus count is gone, including "17-slot"; the recipe's accent and dark-palette bullets point at *Color is a system*; the process ends on "Done when the plan names color, type, layout and one signature, and Review checklist items 1–10 each pass or carry a stated reason"; "the six" is "the default looks in *Calibration*" at `:73`, `:79`, `:86`, checklist 3.
  - `prototype/SKILL.md`: step 7 points at `references/in-app-handoff.md` (new, holds the five-item brief); `:8` sentence deleted.
  - `fe-blazor.md` 9,950 chars: Read-the-rules is the template wording with `blazor.md` named; the rendering paragraph is one sentence plus the `rendering-strategy.md` pointer; Step 1 names the critique table in the decision record against `visual-identity` Calibration (no count); Step 3 names the `performance` budget table and a flow list; Fix line is the template's; the O20 (b) clause is gone and the read-only clause stays; `Gate evidence` is O18's wording.
  - R2: `ui-rules` 21,122 → under 16,000 by moving §6 Navigation and Footers and §7 to `references/navigation-and-surfaces.md` (the §7 heading stays as a pointer, so `§7` citations still resolve), plus a shorter lead and Validation. `basics` 18,619 → under 16,000 by moving "Component architecture" to `references/component-layering.md`, leaving a pointer. `auth0-blazor` 16,035 → under 16,000 by deleting the six "What NOT to do" lines that restate Rules.
  - `auth0-blazor` description ends `Not for tenant setup or OIDC theory (auth0-concepts).` at 193 chars. `accessibility:11` names `accessibility-testing` without a link.
  - Unverified: that an agent loading `ui-rules` or `basics` still reaches the moved sections. Nothing ran a feature build through the slimmer skills. `ui-rules` Validation now ends on "every item in the reference that applies passes", which is looser than the two lines it replaced.
  - For G1: `basics/SKILL.md` still has `name: concepts` and `auth0-blazor` has `name: auth0`, where R1 wants the topic and the folder name. Neither is in an audit row, so P5 left them.

### P6 — fe-react

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** these are under 16,000 chars: `frontend/react/skills/{error-handling,ui-rules,data-fetching,basics,animation}`. Each path below gives `0 findings` under the lint.
**Depends on:** L1, T1, C1.
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
- **`frontend/react/skills/component-testing/SKILL.md`.** R6: rename the routing heading to a topic heading.
- **`frontend/react/agents/fe-react.md`**
  - **R17, at `:24`.** The rules listing becomes the template wording.
  - **R15, at `:36` and `:38`.**
  - **O11, at `:19` and `:36`.**
  - **R17, at `:18`.** Write one sentence plus the `rendering-strategy.md` pointer.
  - **R17, at `:19`.** Delete the invariant and keep the Done-when cells.
  - **The Fix line.** Use T1's template sweep wording.
  - **O18, at `:65`.**
- **`auth/auth0-react/SKILL.md`.** R3.
- **O20 (b).** In frontend/react/agents/fe-react.md: delete the clause that a test you believe is wrong stays red and is recorded as a dated `D<n>`, through "The close-out gate rules on it." Keep the read-only clause before it.
- **Not in P6:** `frontend/react/skills/rules` (T1). `rules/react.md` changes only under O14 (b).
- **As built (2026-11-20):** every row is fixed or named below. Proof, from the repo root: `python3 tools/skill-lint.py` over the ten paths of the gate prints `0 findings`, `python3 tools/token-audit.py --violations-only | grep -E 'frontend/react'` prints nothing, and `python3 tools/plugin-surface-check.py` prints `OK`.
  - **Bodies (file chars, was → now; `token-audit` counts the body without the frontmatter, so each is a few hundred lower there):** `error-handling` 33,390 → 15,949, `ui-rules` 23,086 → 15,967, `data-fetching` 20,054 → 16,051, `basics` 17,124 → 15,716, `animation` 16,679 → 14,676. `rules/react.md` and `react-data.md` are untouched (O14 (a) needs no rule-file change).
  - **error-handling:** the R21 examples carry no comments, and the two "Wrong:" and "Right:" blocks are captioned in prose. The three-state example and the stale example fail only on `q.data === undefined` (O14), and the scope example passes `stale={q.isError && q.data !== undefined}`. The retry-test-id mismatch (`Orders.Retry` against `Orders.Error.Retry`) is now `Orders.Error.Retry` everywhere. R17: the retry, `Retry-After`, timeout-idempotency and notification position/dismissal/content restatements are one clause plus the pointer to `react.md` and `react-data.md`; the closing `## Rules` echo list is deleted and its rule-file pointer moved to the intro. R19: the "older never a toast rule" clause is gone. R16 and D15: `references/live-connection-grids-and-gone.md` (the socket and offline block, grids, "Gone, not broken"), `references/notifications.md` (the contract's extras, the library table, the raise-point, volume control) and `references/validation.md`, each behind a row of the "Situational surfaces" table. R15: every Validation line is one scenario and one observable state with its test id; the two bullets for surfaces no section teaches (`localStorage` quota, two tabs signing out) are dropped, and so are the double-click, idempotency-key, 409 and 422 clauses of the mutation line, which `references/writes-and-dependencies.md` already teaches.
  - **ui-rules, data-fetching, basics, animation:** by D15. Deleted: `ui-rules` `## Rules` and `## Validation` (the first became one intro sentence); `data-fetching` `## Rules`, and its timeout paragraph now points at `error-handling` (Timeouts); `basics` "Comparison: React ↔ Blazor" and "Navigation" (a restatement of `react.md`); `animation` `## Rules` and `## What NOT to do`. Moved: `ui-rules` §5, §6 Navigation and Footers, and §7 to `references/{bulk-operations,navigation-and-footers,surface-choice}.md`, with the section numbers kept so `component-writer`'s "ui-rules §4" and the other `§` references still resolve.
  - **R9, R6, R3:** the two reference files open with `**Contents:**` lists (16 and 20 bullets). `component-testing`'s `### Handoff` is `### Mutation grading`. `auth0-react`'s description ends `Not for tenant setup or OIDC theory (auth0-concepts).` (199 chars).
  - **fe-react.md:** the rules line is the template wording naming `react.md` as the core file; the `:18` paragraph is one sentence plus the `rendering-strategy.md` pointer; the `:19` invariant is deleted; the Step 1 Done-when names the critique table against each default look in `visual-identity` Calibration (O11); the Step 3 Done-when names the rule-file sections and the `performance` Budgets table as its proof (R15); the Fix line carries the template's sweep wording; the O20 (b) clause is gone and the read-only clause stays; `Gate evidence:` is the template line (O18).
  - **Held:** no deferred O. **Not edited, for G1:** `component-library/references/{chakra,mui,mantine,none}.md` and `seo/SKILL.md:42` carry inline example comments that cite `ui-rules` (R21); they are outside this task's paths. `animation/SKILL.md` called the motion library `animation` in 14 places (a rename artifact: `motion/react` is the import); P6 restored `motion`.

### P7 — mobile-react-native, mobile-ios, mobile-android

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each path below gives `0 findings` under the lint. `mobile/android/skills/unit-testing` is under 16,000 chars. No mobile agent caches a version floor or a rule-file listing.
**Depends on:** L1, T1, C1.
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
- **R9.** `mobile/{android,ios,react-native}/skills/standards-audit/references/conformance-checklist.md`.
- **R3.** `mobile/android/skills/kotlin-multiplatform/SKILL.md`, and `auth/auth0-{android,ios,react-native}/SKILL.md`.
- **O20 (b).** In mobile/react-native/agents/mobile-react-native.md, mobile/ios/agents/mobile-ios.md and mobile/android/agents/mobile-android.md: delete the clause that a test you believe is wrong stays red and is recorded as a dated `D<n>`, through "The close-out gate rules on it." Keep the read-only clause before it.
- **Not in P7:** the mobile `rules` skills (T1), and `mobile/_shared/` (no rows).

- **As built (2026-11-20):** every path in the gate lints `0 findings`, `token-audit --violations-only | grep mobile/` prints nothing, and `plugin-surface-check` prints `OK`.
  - The three agents: Read-the-rules is the template wording with the core file named (`react-native.md`, `swift.md`, `android.md`); the version asides at `mobile-react-native:16`, `mobile-ios:17` and `mobile-android:17` point at the core rule file and `CLAUDE.md` "Version policy" (no floor, no `targetSdk` number); the Fix line, the Step 3 and Step 5 Done-when cells, the `Gate evidence:` line and the O20 (b) clause are as the prompt lists. Step 1 names the critique table against the default looks in `visual-identity` Calibration (no count). `mobile-ios:39` now says "an older SDK" instead of "below the iOS 27 SDK".
  - `mobile-android/unit-testing/SKILL.md` 16,967 → 12,664 chars. The Compose UI test v2 section moved to `references/compose-ui-tests.md` and the Kover setup to `references/coverage-kover.md` (both new, each behind a pointer naming its condition). Plan refs, "built but unverified", "unconfirmed" and "verified … 2026-10-10" are gone; `:75–78` and `:95–97` point at `android-tests.md`; Generation steps 1–4 end on "Done when"; `:96–97` say "a test client" and "a teardown registry".
  - R9 contents lists are in the three `conformance-checklist.md` files (25, 24 and 24 entries, each including "Section index"). R3: the four descriptions end `Not for … (<sibling>).` (`mobile-ios`, `auth0-concepts` ×3).
  - Unverified: that an agent working a Compose UI test reaches `references/compose-ui-tests.md` from the one-sentence pointer. The three agents' `Steps` table was not run end to end.
  - Beyond the prompt (D14): Android step 1 gains the critique table; `mobile-android.md:3` drops "Kotlin 2.4, AGP 9.4"; "(plan 003)" is gone from `mobile/ios/skills/unit-testing` and `mobile/react-native/skills/component-testing` (the same defect as the Android row).
  - For G1: `mobile-react-native.md:3, 8` still say "SDK 57" and `mobile-ios.md:3` "Xcode 27, Swift 6.4", which restate `CLAUDE.md` "Version policy" in a description and a heading. No audit row names them, so P7 left them.

### P8 — desktop-macos, desktop-windows

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each path below gives `0 findings` under the lint. `desktop/macos/skills/rules/swift.md` is ≤ 6,000 chars, and every other listed rule file is ≤ 2,500. Neither desktop agent caches a rule-file listing, a version floor or a command table.
**Depends on:** L1, T1, C1.
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
- **R9.** `desktop/{macos,windows}/skills/standards-audit/references/conformance-checklist.md`.
- **R3.** `desktop/_shared/security/SKILL.md` and `auth/auth0-{macos,windows}/SKILL.md`.
- **O20 (b).** In desktop/macos/agents/desktop-macos.md and desktop/windows/agents/desktop-windows.md: delete the clause that a test you believe is wrong stays red and is recorded as a dated `D<n>`, through "The close-out gate rules on it." Keep the read-only clause before it.
- **Not in P8:** `mobile/ios/skills/rules/*`. They share file names, but they are within budget and have no rows.

- **As built (2026-11-20):** every path in the gate lints `0 findings`, `plugin-surface-check` prints `OK`, `token-audit --violations-only` prints nothing for `desktop/` or `auth0-macos`/`auth0-windows`, and `wc -c` is under the budget for every listed rule file.
  - Rule files, chars: `swift.md` 5,924 (core, ≤ 6,000); `swiftui-mac.md` 2,487, `xcode-config.md` 2,398, `mac-accessibility.md` 2,401, `swift-persistence.md` 2,308, `appkit.md` 2,070, `swift-networking.md` 1,912, `winui-xaml.md` 2,457, `cppwinrt.md` 2,492, `win-accessibility.md` 2,316. Every `paths:` is unchanged. Each trimmed file opens with a `Recipes:` pointer to the skills that already teach the cut how-to (`ui-components`, `windows-and-scenes`, `menus-and-commands`, `forms`, `accessibility`, `test-ids`, `appkit`, `networking`, `project-setup`, `shared/distribution`, `migration`, `cpp-winrt`); no skill gained text. `swift.md` points at `CLAUDE.md` "Simplicity (KISS)" and "Comments" instead of restating them.
  - Cut with no new home, because no skill or rule needs it: contrast ratios and the 28 pt, 10 pt and 13 pt sizes in both accessibility files, the 20-item list threshold in `winui-xaml.md`, the `#Preview`, menu-bar-icon and `UtilityWindow` lines of `swiftui-mac.md`, and `swift-networking.md`'s forced-update and `404` rows. `xcode-config.md` drops the SwiftLint line and the CocoaPods trunk date (`migration` and `project-setup` keep the date).
  - Agents: `desktop-macos.md` 10,069 and `desktop-windows.md` 11,015. Read-the-rules is the template wording with the core file named (`swift.md`; `csharp.md` for C#, `cppwinrt.md` for C++); `:17` points at the core rule file and `CLAUDE.md` "Version policy"; the "a view in a folder no glob covers" note stays. Step 3 and step 6 Done-when cells name the rule-file items, the `performance` skill's budget table (macOS) or *Measure first* figures (Windows) and "every `shared/distribution` row passed or waived with its reason"; Windows step 4 points at the floor in `unit-testing`. The Windows command table is now `## Where the commands live`, three pointer bullets (`project-setup`, `unit-testing`, `code-review`, plus the two `cpp-winrt/references/` files). The Fix line, `Gate evidence:` line and the O20 (b) clause are as the prompt lists; the read-only clause stays.
  - `desktop/windows/skills/unit-testing/SKILL.md` 14,806 → 13,160. `## Test shape` and `## Rules` point at `CLAUDE.md` "Test code rules" and keep the NUnit forms; the version numbers and `(Learn, …)` notes are gone; the two tests are `Should_ShowTwoRows_When_LoadSucceeds` (asserts the row count) and `Should_BeOnSale_When_PriceIsReduced`; `## Telemetry` and the Dispatcher gotcha are deleted.
  - R9: a `**Contents:**` list of all 22 `##` headings (including "Section index") is in both `conformance-checklist.md` files. R3: `desktop/_shared/security` ends `(qa-security).`; the two `auth0-*` descriptions end `(auth0-concepts).` and `auth0-macos` lost "native" to stay at 194 chars.
  - Unverified: that a session loading a trimmed rule file still reaches the how-to from the one-line `Recipes:` pointer; neither desktop agent's `Steps` table was run end to end.
  - For G1: `desktop-windows.md:27` still lists ".NET 8 or 9, Windows App SDK 1.x" as migration triggers, which restates `CLAUDE.md` "Version policy"; no audit row names it, so P8 left it.

### P9 — be-dotnet, be-java, be-node, be-python, be-rust

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each path below gives `0 findings` under the lint. These are under 16,000 chars: `backend/{java,dotnet,node}/skills/unit-testing`, `backend/python/skills/media-processing` and `backend/rust/skills/pattern-writer`. No `be-*` agent caches its rule-file listing or the version policy.
**Depends on:** L1, T1, C1.
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
- **R3.** `auth/_shared/auth0-concepts/SKILL.md` and `auth/_shared/oidc-concepts/SKILL.md`.
- **O20 (b).** In backend/{dotnet,java,node,python,rust}/agents/be-<stack>.md: delete the clause that a test you believe is wrong stays red and is recorded as a dated `D<n>`, through "The close-out gate rules on it." Keep the read-only clause before it.
- **Not in P9:** `observability/` (P10), and the `be-*` `rules` skills (T1).

- **As built (2026-11-20):** `skill-lint` over the 13 gate paths prints `0 findings`, `token-audit --violations-only | grep -E 'backend/(dotnet|java|node|python|rust)/'` prints nothing, `plugin-surface-check` prints `OK`.
  - Agents (chars): `be-dotnet` 6,187, `be-java` 5,392, `be-node` 6,033, `be-python` 7,036, `be-rust` 7,115. Read-the-rules is the template wording with the core file named (`dotnet.md`, `java.md`, `node.md`, `python.md`, `rust.md`), keeping be-rust's `#[cfg(test)]` note and be-node's narrow `*.ts` globs. The version asides in step 2 read "the lane per the core rule file and `CLAUDE.md` 'Version policy'"; the "past support" sentences and `be-python`'s "Never raise `requires-python`" are gone. Steps 1 and 4 and the Fix line carry the R15 wording (the sweep is "every sibling sharing the defect's pattern fixed or listed in the report"). `be-python` step 1 and `be-rust` step 1 keep their stack-specific clauses (upload classes and limits; error variants and their HTTP status) after the earn-it criterion. O18: `Gate evidence: <the Gate: line's commands and results, including coverage>` in all five, with `be-python` and `be-rust` losing their stack-specific lists. O20 (b): the "stays red … dated `D<n>` … The close-out gate rules on it." clause is deleted from all five and the read-only clause stays.
  - `be-python.md:16–17` now point at `python-pipeline.md:12` and `python-container.md:14`; the contract invariant stays. `be-java` O19: the `auth/_shared/{auth0-concepts,oidc-concepts}` row in step 2 and the telemetry-base line naming `observability-engineer-java`.
  - Dropped row: the audit's `be-rust:8` version aside is the H1 `(stable; edition 2024 primary / 2021 supported)`, which is the template's own `(<Stack / version>)` slot and matches the other four H1s. It stays. Only `:17` changed.
  - R2, chars: `java/unit-testing` 19,160 → 15,958, `dotnet/unit-testing` 18,327 → 15,732, `node/unit-testing` 18,014 → 15,830, `python/media-processing` 19,038 → 15,479, `rust/pattern-writer` 17,975 → 15,957. Order of cuts per §2 item 3: restatements of the rule file and `CLAUDE.md` first (the version-policy paragraphs now point at `CLAUDE.md` 'Version policy'; the `CLAUDE.md` mentions in the parameterized, naming and test-data lines are gone), then moves by branch. The coverage-gating sentences C1 wrote (the `Measure` lead-in and generation step 6) are untouched.
  - New references: `java/unit-testing/references/{jacoco-coverage,seam-examples}.md`, `dotnet/unit-testing/references/{coverage-measure,seam-examples}.md`, `node/unit-testing/references/tsc-prerequisite.md`, `python/media-processing/references/photo-operations.md` (dominant colours, resize ladder), `rust/pattern-writer/references/crate-per-module.md`. Each is reached from a one-line pointer that names its condition.
  - R3: `auth0-concepts` and `oidc-concepts` end `Not for … (sibling).`; both descriptions are ≤ 200 chars (198 and 197, counted without the `description:` key); `token-audit` lists neither.
  - Unverified: that a session following a new pointer finds the moved how-to (no skill was run end to end); the rule-file wording was not re-read against the trimmed bullets in `rust/pattern-writer` beyond the lints and pinning sentences quoted there.
  - For G1: `name: patterns-apply` sits in all five `backend/*/skills/pattern-writer/SKILL.md` front matters, whose folder is `pattern-writer`. No audit row names it, so P9 left it.

### P10 — data and observability

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** these are under 16,000 chars: `data/{dynamodb,elasticsearch,cosmosdb}` and `observability/logs-traces-setup`. Each path below gives `0 findings` under the lint.
**Depends on:** L1, T1, C1.
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
- **O20 (b).** In data/agents/data-architect.md: delete the clause that a test you believe is wrong stays red and is recorded as a dated `D<n>`, through "The close-out gate rules on it." Keep the read-only clause before it.
- **Not in P10:** `data/rules` (T1).

- **As built (2026-11-20):** `skill-lint` over the 10 gate paths prints `0 findings`, `token-audit --violations-only | grep -E 'data/(dynamodb|elasticsearch|cosmosdb)|logs-traces-setup'` prints nothing, `plugin-surface-check` prints `OK`. No commit was made: the queue commits.
  - **`dynamodb`** 11,742 chars (was 19,539). `:105–207` moved to `references/connections.md` (the three client blocks, comments removed) and `references/security-iam.md` (IAM, `LeadingKeys`, KMS tier, PITR, global tables), behind two pointers in `## Connections and security`. R21 `:141, 234, 237` fixed (the `// Throws…` fact is now a sentence under the block). Data `:14, 24, 96` fixed. `## Rules` keeps nine rules no other section states; `## What NOT to do` is gone and its items are folded into positive rules. Generation steps 1–5 end on a checkable `Done when`. O15 at step 4: "Wrap it in a repository only when a second store or a test seam needs it."
  - **`elasticsearch`** 16,806 to under 16,000 (token-audit counts the body): `## Rules` and `## What NOT to do` collapsed to the three rules stated nowhere else; the intro handoff paragraph, the observability bullets and the inline comments in two blocks tightened.
  - **`cosmosdb`** 16,849 to 15,324 bytes: `## Rules` and `## What NOT to do` collapsed to two rules stated nowhere else (2 MB item limit, checkpointing a change-feed processor).
  - **`migrations:63`** O4: the table header is `Steps`. Prose elsewhere in the skill still says "phase"; R11 reads headings and table headers only.
  - **`logs-traces-setup`** 14,881 chars (was 17,321 in the audit, 16,869 at run start). Vector and Fluent Bit moved to `references/forwarders.md`, multi-tenant and Grafana Cloud to `references/multi-tenant-and-cloud.md`. Promtail is stated once, in the Alloy section; the `### Promtail` section and "River config" are gone. The Alloy block lost its step markers and YAML comments. O16: the trace-correlation table has a rust row (`trace_id`, from `with_span_list(true)`), and the smoke query is `{service="<app>", environment="<env>"}`. `## Rules` keeps two rules (pinned image tags, declarative data sources); steps 1–8 each end on `Done when`.
  - **Agents.** `data-architect` `:24` is the template wording with `data.md` as the core file and keeps the "five engines have no rule file" note, now pointing at "the engine skill"; the Fix line is the template's sweep wording; the O20 (b) clause is gone and the read-only clause stays. The four `observability-engineer-*` Fix lines end on "every sibling service sharing the defect's pattern fixed or listed in the report".
  - **For G1, outside P10's paths:** `data/cosmosdb/SKILL.md` Generation step 4 still says "a typed repository per logical entity", the same CLAUDE.md "Pattern application" conflict that O15 settled for DynamoDB. Other YAML blocks in `logs-traces-setup` (Tempo, Collector, data source) still carry inline comments.

### P11 — devops: the agent, `k8s-security`, `supply-chain-security`, `iac-security`

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** these are under 16,000 chars: `devops/{k8s-security,supply-chain-security,iac-security}`. Each path below gives `0 findings` under the lint.
**Depends on:** L1, T1, C1.
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
- **O20 (b).** In devops/agents/devops-engineer.md: delete the clause that a test you believe is wrong stays red and is recorded as a dated `D<n>`, through "The close-out gate rules on it." Keep the read-only clause before it.
- **Not in P11:** the other devops skills (P12), and `devops/rules` (T1).

- **As built (2026-11-20):** all three bodies are under 16,000 chars by `token-audit` (it counts the body without the frontmatter): `k8s-security` was 36,584, `supply-chain-security` 36,528, `iac-security` 31,022; none is over, so no D3 overage is recorded. `skill-lint` over the four gate paths prints `0 findings`, `token-audit --violations-only | grep -E 'devops/(k8s-security|supply-chain-security|iac-security)'` prints nothing, `plugin-surface-check` prints `OK`. No commit was made: the queue commits. See D17 for what moved where.
  - **O13, checked through `dev:source-grounding` against kube-bench v0.16.0 (2026-08-05, the current release):** its `cfg/` tree bundles `eks-1.8.0`, `aks-1.8` and `gke-1.9.0` as the newest managed ids; `eks-1.5.0`, `aks-1.7`, `gke-1.6.0` and the skill's old `gke-1.2.0` and `aks-1.0` are all still bundled. `references/kube-bench.md` now holds the one table, with the newest ids, the `cis-1.10` / `1.11` / `1.12` map read from `cfg/config.yaml`, and the targets `node,policies,managedservices` for all three managed ids. The skill points at it. `--exit-code` exists in v0.16.0 (`cmd/root.go:162`), so the reference's old "there is no built-in `--exit-code`" line is gone.
  - **Pins:** `k8s-security` states each image tag once, in its Setup. `references/ci-wiring.md` uses `<… from Setup>` placeholders, and `references/polaris.md` lost its stale `quay.io/fairwinds/polaris:10.2.2` and `kube-score:v1.20.0`.
  - **`devops-engineer.md`:** `:22` is the template's rules wording naming `devops.md` as the core file, with no file list; row 2's done-when ends "…or the run stops with the map and proposal reported and nothing written"; `:16` and the Fix line state the target (the narrowest grant, keep the gate, the secret store); the Fix line ends in the sweep wording; the O20 (b) clause is gone and the read-only clause stays.

### P12 — devops, the rest, and security-governance

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** these are under 16,000 chars: `devops/{infra-controls-validation,container-runtime-security,cloud-posture}` and `security/cloud-incident-response`. Each path below gives `0 findings` under the lint.
**Depends on:** L1, T1, C1.
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

- **As built (2026-11-20):** every path in the gate lints `0 findings`, `token-audit --violations-only | grep -E 'infra-controls-validation|container-runtime-security|cloud-posture|cloud-incident-response'` prints nothing, and `plugin-surface-check` prints `OK`. T1's D11 finding is cleared: the `security/rules-security-governance` folder lints clean once `security-governance.md:40` is fixed. Method and extra moves are in D16. No commit was made: the queue commits.
  - **R2 sizes (token-audit chars):** `infra-controls-validation` 25,703 to about 15,800; `container-runtime-security` 22,947 to about 10,200; `cloud-posture` 22,000 to about 15,900; `cloud-incident-response` 21,277 to about 15,400.
  - **`security-architect.md`:** `:26` names the core file and says "each path-scoped file the artifacts the run writes touch"; step 6's Done-when reads "every register item cites a lane artifact path and round, every agent / framework / ATT&CK / CSF id resolves"; the "never run or sequence a lane" restatements at `:12`, `:42` and `:53` are gone and the Invariant at `:18` stays; `:21` gains `docs/audits/**` (O17).
  - **`cloud-incident-response`:** Detect, Triage, Contain, Eradicate, Recover and Lessons-learned each end on a `Done when`; `## Anti-patterns` is deleted (R17, `runbooks.md` "Cloud incident response" owns the rules; the untested-backup line moved into Recover); the per-cloud telemetry table and containment commands sit behind "Know your telemetry" (R16); the "added there by task G1" progress note now says the BCDR crosswalk row "lives there".
  - **R10 and R9:** `security-governance.md:40` and `conformance-checklist.md` K9 put `"TBD"` in a code span; `conformance-checklist.md` gains a `**Contents:**` list of its 17 `##` headings. `security-governance.md`'s size was not touched.
  - **Outside my paths:** `security/agents/penetration-tester.md` shows as modified in the working tree; it is P13's, and this task did not edit it.

### P13 — penetration-testing

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** these are under 16,000 chars: `security/{cloud-attack-azure,cloud-attack-aws,cloud-recon-enumeration,atomic-simulation,cloud-attack-gcp}`. `metasploit-setup`'s description is ≤ 200 chars and R3-shaped. `penetration-tester.md` gives `0 findings` under the lint.
**Depends on:** L1, T1, C1.
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

- **As built (2026-11-20):** every named path lints `0 findings`, the `token-audit --violations-only | grep` line prints nothing, and `plugin-surface-check` prints `OK`.
  - **`penetration-tester.md`:** `:18`'s "These nine controls are the design, not boilerplate..." is now "A run that cannot satisfy these nine controls does not start." (R19). `:62`'s "Re-read the scope file before each step and halt..." is deleted — control 1 (`:20`) already carries "re-read it before every step"; the halt behavior stays stated once, in control 9 (R17). Step 4's done-when is now "every host reached is in the action log and the scope file's in-scope list" (checkable positive, not the unfalsifiable "out-of-scope hosts never touched"); Step 3's reads "Escalation proven, or its absence evidenced by the attempts behind it"; RETEST's done-when now reads "every prior finding carries one of Resolved / Still open / Still open (regressed), each with the re-run's output" before the New-finding prefix rule (R15).
  - **R2 bodies — method is R16 moves to new `references/` files, since each file's existing references already carried only the per-tool recipes, not the per-step narrative.** `cloud-attack-azure` 21,020 → 15,367 (3 new references: `identity-token-theft.md`, `rbac-privesc.md`, `detection-surface.md`). `cloud-attack-aws` 19,859 → 14,747 (2 new: `service-exploitation.md`, `detection-surface.md`; Step 2's inline 21-paths table trimmed since `references/pmapper.md` already carries it in full). `cloud-recon-enumeration` 18,538 → 15,742 (no new references — the IMDS and IAM-enumeration sections were trimmed to summaries since `references/metadata-service.md` and `references/enumerate-iam.md` already carry the full detail; the OIDC section was tightened in place). `atomic-simulation` 16,496 → 12,138 (3 new references: `atomic-red-team.md`, `caldera.md`, `stratus-vectr.md` — this skill had no `references/` folder before). `cloud-attack-gcp` 16,331 → 15,837 (no new references — Step 2's impersonation-primitives table trimmed to prose since `references/gcp-privesc.md` already carries it in full).
  - **`metasploit-setup`:** description cut from 452 to 199 chars, reshaped to the `Use when … Triggers "…". Not for … (sibling).` form (R3).

### P14 — qa-java: the lane's agents, conventions, rule files, contents lists and three bodies

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each path below gives `0 findings` under the lint. `qa/java/skills/{ai-feature-testing,api-contract-testing,test-quality-check}` are under 16,000 chars. Both rule files are ≤ 2,500. The Playwright MCP command lives once in the lane, in `page-objects-from-url`.
**Depends on:** L1, T1, C1.
**Budget:** ~125k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k, the template 1k. `qa-ui-java.md` (3k to read, ~3k written), six Fix lines 4k, `inhouse-framework-conventions` (5k to read, ~4k written), two rule files (1.5k to read, ~3k written), 21 R9 lists ~8k by script, the MCP command in two skills 3k. `ai-feature-testing` (5.3k to read, ~7k written), `api-contract-testing` (5.2k to read, ~5k written), `test-quality-check` (4.7k to read, ~5k written). Gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py qa/java/agents qa/java/skills/inhouse-framework-conventions qa/java/skills/rules/desktop-tests.md qa/java/skills/rules/qa-java-ui.md qa/java/skills/page-objects-from-url qa/java/skills/evidence-capture qa/java/skills/ai-feature-testing qa/java/skills/api-contract-testing qa/java/skills/test-quality-check <the 21 R9 skill folders below>`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'qa/java/skills/(ai-feature-testing|api-contract-testing|test-quality-check)/'`.
Then run `python3 tools/qa-version-check.py`, and then `python3 tools/plugin-surface-check.py`.

- **`qa/java/agents/qa-ui-java.md`**
  - **R17, at `:16`.**
  - **R17, at `:25`.** The MCP command becomes a pointer to `page-objects-from-url`.
  - **R18, at `:32` and `:55`.**
  - **The Fix line, at `:46`.**
  - **O21, at `:21` and `:55`.** Each becomes "Ask as many clarifying questions as needed."
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
- **O20 (b).** In qa/java/agents/qa-{ui,api,bdd,desktop,llm,mobile,performance}-java.md: delete the clause that a test you believe is wrong stays red and is recorded as a dated `D<n>`, through "The close-out gate rules on it." Keep the read-only clause before it.
- **Not in P14:** `qa/java/skills/{data-driven-testing,failure-injection-testing,api-test-author/grpc,security-testing/*}` (P15), `qa/_shared` (P16) and `qa/java/skills/rules/SKILL.md` (T1).
- **As built (2026-11-20):** every row is fixed or named below, and the gate is green. Proof, from the repo root:
  - `python3 tools/skill-lint.py` over the gate's paths (the agents passed as the seven `qa/java/agents/*.md` files, see D18) prints `0 findings`. `token-audit --violations-only | grep -E 'qa/java/'` prints nothing. `qa-version-check.py` and `plugin-surface-check.py` print `OK`.
  - `wc -c`: `desktop-tests.md` 2,490 and `qa-java-ui.md` 2,465. Bodies: `ai-feature-testing` 14,883 (from 21,319), `api-contract-testing` 14,259 (from 20,664), `test-quality-check` 11,300 (from 18,714).
  - **`qa-ui-java.md`:** `:16` is the template's Read-the-rules wording with `qa-java.md` as the core file; `:25` points at `page-objects-from-url` "Prerequisites" with `--codegen=java` (the pin and the flags left the agent); the "ask, never guess" line is gone; `:21` and `:53` read "Ask as many clarifying questions as needed." (O21); the Fix line ends "then sweep: every sibling sharing the defect's pattern fixed or listed in the report." (`:44`); `:66` is the O18 `Gate evidence` line.
  - **The six other agents:** the Fix line ends "then sweep: every <their sibling unit> … fixed or listed in the report", and `Gate evidence:` is the O18 wording. All seven lost the "stays red … `D<n>` … The close-out gate rules on it." clause (O20 (b)); `grep -n 'D<n>' qa/java/agents/*.md` prints nothing.
  - **The MCP command:** `grep -rn 'playwright/mcp' qa/java` prints one line, `page-objects-from-url/SKILL.md:24`. `evidence-capture/SKILL.md` points at its "Prerequisites".
  - **`inhouse-framework-conventions`:** the Rules list is one sentence pointing at `CLAUDE.md` "Test code rules" and `qa-java.md`; the Claude Code workflow section is deleted, with its mention in the intro and the `.claude/commands/` layout rows; the Quality bar keeps three Accelerator items; the anti-examples keep the three Accelerator rows (selector in code, `String` read, raw `page` in a test). O7 was answered (a), so the Java lane takes no URL exception: its `assertThat(page).hasURL(…)` row stays an anti-example and the audit's `:283` row is not applied.
  - **`ai-feature-testing`:** rewritten at 14,883. The provenance (R19), the second statement of the four ideas, `## Rules`, the dependency block with its versions (the body names the project's TestNG, AssertJ and Jackson) and the anti-pattern bullets that repeated an idea section are gone; the surviving practices lead with the target and keep the key and PII guardrails. The four Java examples use an injected `llm` and a shared `mapper` from a `LlmTest` base class, `Should_X_When_Y` names, named constants and no inline comment.
  - **R2 moves:** `api-contract-testing` moved its message-pact section to `references/message-pacts.md`, and its Rules and What-NOT-to-do lists became seven positive guardrails. `test-quality-check` moved its separate-repo section to `references/separate-repo.md`. Each body points at its file with the condition that fetches it.
  - **R9:** a `**Contents:**` list after the H1 in each of the 21 reference files, by script.
  - **Rule files:** `desktop-tests.md` lost its version pins (`desktop-project-setup` owns them) and the Mac2 native-strategy line (`desktop-screen-explorer` owns it), and points at three skills for recipes. `qa-java-ui.md` lost 76 chars.
  - **Outside my paths, for G1:** `qa/java/skills/ai-feature-testing/references/details.md` still defines `Llm` as a static class (`:89–96`, `:146–160`), so its samples differ from the injected `LlmClient` that `SKILL.md` now shows. The new `references/message-pacts.md` and `references/separate-repo.md` are for G1's read of new reference files. The P17 and P18 gate lines (and their prompts) pass `qa/<lane>/agents` to `skill-lint`, which exits with a usage error (D18).

### P15 — qa-java: the remaining bodies

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** these six `qa/java` skills are under 16,000 chars, and each gives `0 findings` under the lint.
**Depends on:** L1, T1, C1.
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
- **As built (2026-11-20):** all six bodies are under 16,000 chars; the gate is green (`skill-lint` → `0 findings`, the `token-audit` grep prints nothing, `qa-version-check` → OK, `plugin-surface-check` → OK). Chars now: `data-driven-testing` 15,508, `failure-injection-testing` 15,698, `api-test-author/grpc` 15,284, `security-testing/passive-scan` 15,786, `dependency-scan` 15,471, `permission-testing` 16,216 (the audit counts the body without the frontmatter). The plan gave no method, so §2 item 3 was applied. Every body lost its closing `## Rules`, which restates the sections above it; the one rule only that list stated moved into an `## Anti-patterns` bullet (`failure-injection-testing`: toxic wiring lives in `ChaosProxy`; `grpc`: the action holds no deserialization or assertion; `permission-testing`: tag each case with its OWASP and WSTG ids). The `Examples` end-to-end paragraphs that restated an idea were deleted. By branch (R16): `data-driven-testing` → `references/excel-source.md` (Excel source); `failure-injection-testing` → `references/details.md` (partial response, probabilistic toxics); `grpc` → `references/details.md` (client- and bidi-streaming); `passive-scan` → `references/auth-and-reporting.md`; `dependency-scan` → `references/parse-and-assert.md`; `permission-testing` → `references/policy-matrix.md`. Each pointer names its condition. No version pin moved. For G1, defects seen and left alone (R2 only): `passive-scan` has floating `7.+`/`3.+`/`1.+` test dependencies; `permission-testing` has a `switch` in `Should_DenyCrossUserAccess_…` and inline comments in the test bodies; `grpc`, `passive-scan` and `permission-testing` keep inline comments in code samples (`CLAUDE.md` "Comments").

### P16 — qa/_shared

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** the seven `qa/_shared` bodies below are under 16,000 chars. These give `0 findings` under the lint: `python-web-testing`, `webmcp-testing`, `contract-testing-pact` and `performance`.
**Depends on:** L1, T1, C1.
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

- **As built (2026-11-20):** every row is fixed or named below. Proof, from the repo root: `skill-lint` over the six gate paths prints `0 findings`, `token-audit --violations-only | grep -E 'qa/_shared/'` prints nothing, `qa-version-check` prints `OK`, `plugin-surface-check` prints `OK`. `python-web-testing`: `## When to use` / `## When NOT to use` added (R7, the scope blockquote became those two), the Never/Instead table points at `qa/typescript/skills/rules/ui-tests.md`, `qa/dotnet/skills/rules/web-ui.md` and `qa/java/skills/rules/qa-java-ui.md` and keeps the Python spellings (R17), the pytest-playwright section moved to `references/pytest-check.md` behind "the same verification will run again" (R16), and "hand it to the `qa-ui-<stack>` agent" is written in two places (R22). The description, the `playwright==1.63.0` and `pytest-playwright==0.10.0` pins are unchanged. `webmcp-testing`: `` `TBD` `` in a code span (R10). Method, the `performance` heading and the R2 moves are in D19. No commit was made: the queue commits.

### P17 — qa-dotnet

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each path below gives `0 findings` under the lint. The five `qa/dotnet` bodies below are under 16,000 chars. Both rule files are ≤ 2,500. The Playwright MCP command lives once in the lane.
**Depends on:** L1, T1, C1.
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
  - **O21, at `:55`.** Each becomes "Ask as many clarifying questions as needed."
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
- **O20 (b).** In qa/dotnet/agents/qa-{ui,api,bdd,desktop,llm,mobile,performance}-dotnet.md: delete the clause that a test you believe is wrong stays red and is recorded as a dated `D<n>`, through "The close-out gate rules on it." Keep the read-only clause before it.
- **Not in P17:** `qa/dotnet/skills/rules/SKILL.md` (T1), and `qa/_shared` (P16).

- **As built (2026-11-20):** every row is fixed or named below. Proof, from the repo root: `skill-lint` over the gate's paths (the seven `qa/dotnet/agents/qa-*-dotnet.md` files named one by one, as D18 records) prints `0 findings`, `token-audit --violations-only | grep -E 'qa/dotnet/'` prints nothing, `wc -c` gives 2,487 (`desktop-tests.md`) and 2,484 (`web-ui.md`), `qa-version-check` prints `OK`, `plugin-surface-check` prints `OK` (it printed one `test-plan-writer` finding from a task running beside this one, and cleared by itself). **`qa-ui-dotnet.md`:** the Read-the-rules line is the template wording with `automation.md` as the core file (`qa-dotnet` has no `qa-dotnet.md`); `:17` points at the core rule file and `CLAUDE.md` "Version policy"; `:29` points at `page-objects-from-url` "Prerequisites" with `--codegen=csharp`; the Fix line says "the trace commands in `evidence-capture`" and ends "then sweep: every sibling page sharing the defect's pattern fixed or listed in the report"; `:55` is "Ask as many clarifying questions as needed." (O21), and the second "ask" bullet at `:32` was deleted as its duplicate. **The six other agents:** the Fix line ends "then sweep: every <their sibling unit> … fixed or listed in the report". All seven lost the "stays red … `D<n>` … The close-out gate rules on it." clause (O20 (b)), the read-only clause stays, and `Gate evidence:` is the O18 wording. `grep -rn 'D<n>' qa/dotnet/agents` prints nothing. **The MCP command:** its one home is `page-objects-from-url/SKILL.md:25`; `evidence-capture/SKILL.md` points at it. **`inhouse-framework-conventions`** (12,873 → 11,235 chars): the Claude Code workflow section and its mentions are gone (R19, R17); the Rules list is a pointer to `CLAUDE.md` "Test code rules" and `automation.md`; the Quality bar keeps four Accelerator items; the anti-examples keep four. O7 was answered (a): the example test asserts `Expect(_dashboardPage.Heading)` through a `DashboardPage` member, the `ToHaveURLAsync` bullet says a URL is never asserted in a test body, and the raw-`Page` anti-example replaces the glob row. `:239` says "a typed DTO, not `RestResponse`". **R3:** the two desktop descriptions end `Not for … (<sibling>).` and were shortened to stay ≤ 200. **R2:** method and moves are in D20. **R9:** the 26 files carry a `**Contents:**` list of their `##` headings (code spans written without backticks, as the lint reads them), generated by a throwaway script in `/tmp`. No commit was made: the queue commits.

### P18 — qa-typescript

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each path below gives `0 findings` under the lint. The five `qa/typescript` bodies below are under 16,000 chars. `ui-tests.md` is ≤ 2,500. The Playwright MCP command lives once in the lane.
**Depends on:** L1, T1, C1.
**Budget:** ~140k. `CLAUDE.md` 25k, §2 and §5 6k, the standard's rows 3k, the template 1k. `qa-ui-typescript.md` (3k to read, ~3k written), four Fix lines 3k, `inhouse-framework-conventions` (5k to read, ~5k written), `ui-tests.md` (0.7k to read, ~1.5k written), 20 R9 lists ~8k by script, R8 ×2 and R6 2k, the MCP command 3k. Five bodies: 23k to read and ~25k written. Gate output 3k.
**Gate: own tests.** Run `python3 tools/skill-lint.py qa/typescript/agents qa/typescript/skills/inhouse-framework-conventions qa/typescript/skills/rules/ui-tests.md qa/typescript/skills/page-objects-from-url qa/typescript/skills/evidence-capture qa/typescript/skills/bdd-project-scaffold qa/typescript/skills/ui-test-author/review qa/typescript/skills/benchmarks qa/typescript/skills/failure-injection-testing qa/typescript/skills/security-testing qa/typescript/skills/data-driven-testing qa/typescript/skills/api-test-author/grpc <the 20 R9 skill folders below>`.
Then run `python3 tools/token-audit.py --violations-only | grep -E 'qa/typescript/'`.
Then run `python3 tools/qa-version-check.py`, and then `python3 tools/plugin-surface-check.py`.

- **`qa/typescript/agents/qa-ui-typescript.md`**
  - **R17, at `:16`.**
  - **R17, at `:27`.** The MCP command becomes a pointer to `page-objects-from-url`.
  - **The Fix line, at `:44`.**
  - **O20 (b), at `:50`.** Nothing to do: this agent already lacks the sentence.
  - **O21, at `:53`.** Each becomes "Ask as many clarifying questions as needed."
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
- **As built (2026-11-20):** every row is fixed or named below. Proof, from the repo root: `python3 tools/skill-lint.py` over the gate's paths prints `0 findings`, `python3 tools/token-audit.py --violations-only | grep -E 'qa/typescript/'` prints nothing, `wc -c qa/typescript/skills/rules/ui-tests.md` is 2,508, and `python3 tools/qa-version-check.py` prints `OK`. No commit was made: the queue commits.
  - **Gate line, D18.** `skill-lint` takes the seven `qa/typescript/agents/*.md` files, not the folder.
  - **`plugin-surface-check` is not `OK`.** It prints `description of 'test-plan-writer' holds an unquoted ': ' (qa/manual/test-plan-writer)` for the three qa plugins. That file is P19's and was modified beside this task, so I left it.
  - **Agents.** `qa-ui-typescript.md` has the template's "Read the rules" (`:16`), the MCP command replaced by a pointer to `page-objects-from-url` "Prerequisites" (`:27`), the Fix sweep, and "Ask as many clarifying questions as needed" (`:53`); `:50` needed nothing (O20). The five other qa-typescript agents carry the template's sweep wording, and `qa-llm-typescript.md` and `qa-performance-typescript.md` did have an open sweep ("Sweep sibling cases…", "Sweep every scenario…"), so both now end "then sweep: every … fixed or listed in the report".
  - **MCP command.** It now lives once in `page-objects-from-url/SKILL.md:25`; `evidence-capture/SKILL.md` points at it.
  - **`inhouse-framework-conventions`.** Rules, Quality bar and Anti-examples now point at `CLAUDE.md` "Test code rules" and `qa-typescript.md` and keep the Accelerator rows (no literal selectors, Allure metadata, builder defaults, the `Locator` and `page.click` anti-examples). The "Claude Code workflow" keeps only the commands. `:155` is `withPassword(`Wrong-${crypto.randomUUID()}`)`, the rule at `:134` says `this.locator("key")`, and `LoginPage` wraps `goTo` and `signIn` in `test.step` (O9).
  - **`ui-tests.md`.** 2,685 to 2,508 bytes: the severity and codebase-wins sentence points at `qa-typescript.md`, `retries: 0` is dropped because the core file states it, and nine bullets are shortened without changing a constraint.
  - **R8.** `bdd-project-scaffold:132` and `review/SKILL.md:15` name `ui-test-author/playwright` on the same line as `references/config-and-fixtures.md`.
  - **R6.** `benchmarks/SKILL.md` heading "Handoff to the profiler" is now "Profiling a slow function".
  - **R2 (chars, before to after).** `failure-injection-testing` 20,074 to 15,819 (Rules section deleted, one anti-pattern deleted, retry, partial-response and probabilistic scenarios moved to the new `references/scenarios.md`); `passive-scan` 19,766 to 14,337 (Rules deleted, the programmatic path moved to the new `references/programmatic.md`); `dependency-scan` 17,020 to 15,972 (Rules deleted, two anti-patterns merged, one deleted); `data-driven-testing` 16,824 to 15,709 (the "Ported from" block deleted, streaming rows moved to the new `references/streaming-rows.md`); `grpc` 16,353 to 16,116 by `len()`, under 16,000 by `token-audit` (the "Composing" paragraph deleted). The three new reference files are for G1's read.
  - **R9.** The 20 contents lists were generated by a throwaway script in `/tmp`, with backticks removed from the items because the lint compares plain heading text. Each list was spot-read once.

### P19 — qa/manual, qa/reporting, qa/cicd

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each path below gives `0 findings` under the lint. `qa-test-case-designer.md` and `qa-test-planner.md` are ≤ 14,000 chars. `test-plan-writer`'s description is ≤ 200 chars.
**Depends on:** L1, T1, C1.
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
- **O20 (b).** In qa/reporting/agents/qa-reporting-dotnet.md: delete the clause that a test you believe is wrong stays red and is recorded as a dated `D<n>`, through "The close-out gate rules on it." Keep the read-only clause before it.
- **Not in P19:** the lane plugins' own skills (P14–P18).
- **As built (2026-11-20):** every row is fixed or named below. Proof, from the repo root: `python3 tools/skill-lint.py qa/manual qa/reporting qa/cicd` and the same over the nine agent files `qa/manual/agents/*.md qa/reporting/agents/*.md qa/cicd/agents/*.md` print `0 findings`; `python3 tools/token-audit.py --violations-only | grep -E 'qa/(manual|reporting|cicd)'` prints nothing; `python3 tools/qa-version-check.py` and `python3 tools/plugin-surface-check.py` print `OK`. `wc -c`: `qa-test-case-designer.md` 13,976, `qa-test-planner.md` 13,904, `qa-feature-spec-writer.md` 11,586, `test-plan-writer`'s description 195. No commit was made: the queue commits.
  - **O3 was answered (a), not (b)**, so the R11 lines are renamed, not held (D21). The lint run over the three trees has no R11 finding.
  - **`qa-feature-spec-writer.md`.** Steps is `# | Step | Load | Done when`. The old `Follows` and `Adds` cells went into `Load`, `Step`, or two short paragraphs (`Step 2 detail`, `Step 4 detail`). `## Report` opens with `Mode: BUILD | FIX | EXTEND — <one line>`.
  - **`qa-explorer.md`.** `:28, 39, 40` name `qa/manual/app-exploration/references/{probes,checks}.md`. Line 28's registration command now points at `qa/<stack>/skills/page-objects-from-url/SKILL.md` (web) and `qa/<stack>/skills/mobile-screen-explorer` (native), because `probes.md` no longer holds it.
  - **`probes.md`.** The `claude mcp add … @playwright/mcp@0.0.85` command and its three explanatory bullets became one sentence naming the lane's `page-objects-from-url` command, plus the one fact only this file needs: add `network` to `--caps`. `qa-version-check.py` pins no MCP version (`grep mcp tools/qa-version-check.py` finds none), so no expected pin lived only there. The contents list lists its five `##` headings.
  - **R2, `qa-test-case-designer.md` 16,504 → 13,976 and `qa-test-planner.md` 14,972 → 13,904.** Each agent's copy of the delivery-chain diagram is now a pointer to `solution-planner.md` "The delivery chain", as `be-documenter.md:16` already does (R17), with the agent's own reads and writes in one sentence. The designer also lost restatements of `requirements-breakdown` and `test-design-techniques` (parentheticals and a repeated story rule). Its `Fix` line and the planner's end on the template's sweep wording.
  - **`test-plan-writer`'s description** is 195 chars. It lost "scope" and "Definition of" for "Ready/Done", and it has no `: `, which `plugin-surface-check` rejects unquoted.
  - **R10.** `[TBD]` is in a code span at `test-plan-writer/SKILL.md:130` and `test-strategy/SKILL.md:166`.
  - **R8, `qa/reporting/*/skills/test-reports/SKILL.md:171, 178, 163`** now name `qa/<stack>/skills/ui-test-author/playwright/references/trace-correlation.md`. `cross-feature-test-design/SKILL.md:21` names `qa/manual/requirements-breakdown` on the line.
  - **The Fix line.** The six reporting and CI/CD agents end on "then sweep: every sibling sharing the defect's pattern fixed or listed in the report" (the CI/CD ones say job or host reference for sibling).
  - **O20 (b).** `qa-reporting-dotnet.md:43` keeps "Acceptance tests an earlier `Q` task wrote are read-only: never quarantine, skip or weaken one." and the clause after it is gone. `grep -rn believe qa/reporting/agents qa/cicd/agents qa/manual/agents` finds nothing.
  - **R9.** The nine `qa/cicd/*/skills/ci-pipelines/references/*.md` files have a `**Contents:**` list straight after the H1, from a throwaway script in `/tmp`.
  - **Outside my paths, for G1:** none found.

### P20 — business-analysis, training-data, tooling, and `/dev:refine`

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** each path below gives `0 findings` under the lint. `business-model.md` is ≤ 6,000 chars, and the three backlog rule files are ≤ 2,500. `requirements-author` is registered as O10 answered, with the catalog and README rows matching.
**Depends on:** L1, T1, C1.
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
- **O20 (b).** In business-analysis/agents/business-analyst.md, training-data/agents/dataset-engineer.md and tooling/agents/tooling-engineer.md: delete the clause that a test you believe is wrong stays red and is recorded as a dated `D<n>`, through "The close-out gate rules on it." Keep the read-only clause before it.
- **Not in P20:** the `business-analysis`, `training-data` and `tooling` `rules` skills (T1), and `tooling/skills/rules/tool-contract.md` unless O23 (b).
- **As built (2026-11-20):** every row is fixed or named below. Proof, from the repo root: `python3 tools/skill-lint.py` over the gate's paths (the two agent folders as the eight agent files, D23) prints `0 findings`; `wc -c business-analysis/skills/rules/*.md` gives `business-model.md` 5,992 and `backlog-epics.md` 2,500, `backlog-requirements.md` 2,426, `backlog-stories.md` 2,497; `python3 tools/plugin-surface-check.py` prints `OK` after the registration move; `python3 tools/token-audit.py --violations-only | grep -E 'business-analysis|training-data|tooling'` prints nothing; `pytest business-analysis/skills/ba-project-memory/scripts/test_kb_lint.py` passes 18.
  - **O10 (b), D22.** `.claude-plugin/marketplace.json`: `dev` lists `ba-scoping-writeup`, `ba-epic-writer`, `ba-story-writer`, `ba-story-quality-review` and `ba-project-memory` first in `skills` (28 with `rules`), and `business-analysis` lost them (6 with `rules`). The two plugin descriptions say so. `README.md` (the `business-analysis` and `dev` rows, the status table) and `docs/skills-catalog.md` (the `dev` and `business-analysis` rows, the folder introduction and every `business-analysis:<label>` for the five) use the `dev:` labels. `engineering-practices/commands/refine.md` is unchanged.
  - **`requirements-author.md`.** The 17-line delivery chain is two lines ("Your place in the lane"); AUDIT has its done-when; "every section of `ba-scoping-writeup`'s format, in order"; the three R18 lines name the owner (`solution-planner`) instead of prohibiting; the skill labels in Steps are `dev:`.
  - **`business-analyst.md`.** `:38` is the template's rules wording; `:52` says "every class in the `ba-feature-conflict-check` taxonomy"; `:60` hands the breakdown to `qa-test-case-designer`; the Fix line ends on "every sibling sharing the defect's pattern fixed or listed in the report"; O20 (b) removed the red-test clause. `:19` was wrong at its line (D23).
  - **`ba-project-memory`.** The tier table and the Read-first and Update-after lists are one line ("per `business-model.md`"); the INDEX example is one line per artifact type; the `active-context.md` skeleton is three lines; the lint paragraph points at `kb-lint.py --help`, which lists 22 rules (read first); "newest first…" is gone; the lookup moved to `references/feature-cross-section.md` behind "Connection cross-section" (O3, D23).
  - **`example-dependency-map.md`.** Five `[TBD - …]` markers are in code spans.
  - **R23.** `business-model.md` pointed its guide-shape and stamp bullets at `backend/_shared/business-documentation/references/guide-shape.md`, which states both. The three backlog files keep every constraint, with merged wording (the stories file merged the part, layer and fragment rules, and dropped "Not Given / When / Then", which `dev:stories` states). Their pointer line names `dev:<label>` and the `requirements-author` agent.
  - **Training data.** `dataset-engineer.md` (rules reading, no-op clause, Fix line, O20 (b)); `dataset-auditor.md` `## Report` opens with `Mode: BASELINE | RE-AUDIT`. `td-dataset-formats/SKILL.md` is 5,469 chars (from 10,742): the envelope table, the `messages` rules, the card list and the split rules point at `datasets.md`, `eval-sets.md` and `dataset-docs.md`; the preference, pretraining and VLM records moved behind a stage → catalog section table; the O24 example is `synthetic:claude-sonnet-5-5` with `synthetic-review-required`, and `format-catalog.md:10` says `synthetic:<exact-model-id>`.
  - **Tooling.** `tooling-engineer.md` (`:17` positive, the quoted no-op gone, coverage by pointer to `CLAUDE.md` 'Test code rules', the Fix line, O20 (b), the O18 `Gate evidence` line); `mcp-builder/SKILL.md:11` points at `tooling/_shared/capability-contract/SKILL.md`; `capability-contract/SKILL.md` has a `Done when` per step 1–6, the four `Rules:` lists replaced by pointers to `tool-contract.md` (O23: the destructive gate is the rule's), and the three R19 phrases gone. `tool-contract.md` is unchanged.
  - **Outside my paths, for G1:** (1) `business-analysis:{scoping,epics,stories,story-review,knowledge-base}` is still the label in `backend/_shared/{agents/be-documenter.md,agents/be-feature-documenter.md,agents/solution-planner.md,business-documentation/SKILL.md,codebase-survey/SKILL.md,epic-map/SKILL.md,solution-blueprint/SKILL.md}`, `business-analysis/skills/{ba-decision-table,ba-entity-state-grid,ba-epic-writer,ba-feature-conflict-check,ba-story-quality-review,ba-story-writer}/SKILL.md`, `business-analysis/skills/rules/SKILL.md`, `engineering-practices/{agent-orientation-cache/SKILL.md,commands/document-system.md}`, `frontend/_shared/product-analytics/SKILL.md`, `qa/manual/agents/qa-test-planner.md` and `qa/manual/test-plan-writer/SKILL.md`: rename each to `dev:<label>` (`grep -rIl 'business-analysis:\(scoping\|epics\|stories\|story-review\|knowledge-base\)' .`). (2) `business-analysis/skills/ba-feature-conflict-check/SKILL.md:40` says "feature slice": rename it "feature cross-section" and point it at `ba-project-memory/references/feature-cross-section.md`. (3) The plan header's `Status:` line held two decision blocks (P2's D12 and P3's D13), put there when their anchor matched the `## Answered questions` text inside `Status:`. P20 moved both into `## Decisions` and left their numbers (the plan now has two D12, two D14 and no D12 for P2's pair). A task that inserts text by that anchor must match the line-start heading.

### G1 — Gate: the whole library once more, then filing

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `python3 tools/skill-lint.py` over the whole library gives `0 findings`. The only exception is the lines of an O the owner deferred, and `Status:` names each one. `token-audit.py --violations-only` exits 0. `plugin-surface-check.py` and `qa-version-check.py` give `OK`, and the lint's tests are green. The plan is filed.
**Depends on:** L1, T1, C1, P1–P20.
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
- **As built (2026-11-20):** the whole set ran once, was fixed, and ran once more. Proof, from the repo root: `python3 tools/skill-lint.py` prints `0 findings`; `python3 tools/token-audit.py --violations-only` exits 0 (no description, body or agent file over budget); `python3 tools/plugin-surface-check.py` and `python3 tools/qa-version-check.py` print `OK`; `python3 -m pytest tools/test_skill_lint.py -q` gives 95 passed. No O is deferred, and no body is over budget under a D3 `D<n>`, so `Status:` names none.
  - **The first run found two violations, both P7's.** `auth/auth0-android/SKILL.md` (206) and `auth/auth0-react-native/SKILL.md` (202) had descriptions over 200 (P7 owns the mobile `auth0` skills). Each lost one word ("native", "or Expo" to "/Expo"). `skill-lint` was already at `0 findings`.
  - **The new references.** The plan added 68 `references/*.md` files (`git diff --name-status <plan's first commit> HEAD | grep '^A'`). Each is pointed at by its skill with the condition that fetches it, and every pointer lands on a real file, and where it names a heading, on a real heading (`Async / message contracts`, `Prerequisites`, `Choosing the surface`, `Step 0`, `Screenshots`, `Language discipline`, `Know your telemetry`). `solution-planner.md:64` points at `delivery-plan/references/reconcile.md`, which exists.
  - **Outside-my-paths items, fixed in place:**
    - P20's: the 19 files that still said `business-analysis:{scoping,epics,stories,story-review,knowledge-base}` now say `dev:<label>` (`grep -rIn 'business-analysis:\(scoping\|epics\|stories\|story-review\|knowledge-base\)' . --exclude-dir=.git | grep -v docs/` prints nothing; `docs/plans/` keeps the old labels as the record). `ba-feature-conflict-check/SKILL.md:40` says "feature cross-section" and points at `ba-project-memory/references/feature-cross-section.md`.
    - P6's: the trailing comments citing `ui-rules`, `data-fetching` or the styling skill are gone from `component-library/references/{chakra,mui,mantine,none}.md` and `seo/SKILL.md`.
    - P7's: the SDK, Xcode and Swift versions left the descriptions and headings of `mobile-react-native.md` and `mobile-ios.md`, as P7 did for Android (D14).
    - P10's: `data/cosmosdb/SKILL.md` step 4 wraps the client in a repository only when a second store or a test seam needs it (O15's wording).
    - P14's: `qa/java/skills/ai-feature-testing/references/details.md` shows an injected `LlmClient`, an `LlmTest` base class and `Should_X_When_Y` tests, as `SKILL.md` does.
    - P17's: `qa/java/skills/security-testing/permission-testing/SKILL.md` has no `switch` in a test body (the data provider carries an `InvoiceCall` per row, as the BFLA sample does), and `passive-scan/SKILL.md` has no floating `7.+` versions (it names the artifacts and says the project's build pins them).
  - **Outside-my-paths items judged not findings, left as they are:** `basics` `name: concepts` and `auth0` in the other auth0 skills, and `name: patterns-apply` in the five `pattern-writer` skills (R1 asks for a kebab-case topic, not the folder name); `desktop-windows.md:27` (".NET 8 or 9, Windows App SDK 1.x … is `migration`'s": a routing line that names its owner); `example-delivery-plan.md:571` ("Out of scope:" names each owner); the `catalog` wording of the reconcile procedure (no heading is named).
  - **For a round-2 audit, outside 004's rules or outside `token-audit`'s scope:** `ai-development/claude-api/SKILL.md` (85,025 chars) and `frontend/_shared/product-analytics/SKILL.md` (22,020) are over 16,000, and neither is a registered skill, so `token-audit` does not list them and 004 has no row for them. Other inline comments remain in code samples of `logs-traces-setup` (Tempo, Collector, data source YAML), `passive-scan` and `permission-testing` (dotnet), `grpc` and `seo` (`app/sitemap.ts`, `robots.ts`). `desktop-windows` and the `standards-audit` conformance checklists were not re-measured.
  - **Decisions.** `## Decisions` holds two `D12` and two `D14` (P2's and P3's blocks were renumbered by hand, and P4 and P7 each took `D14`). They are left as written, since an earlier note is never edited backwards; cite them by title.
  - **Char counts of the touched files** (`wc -c`, body without frontmatter as `token-audit` counts it; 163 `SKILL.md`, 61 agents, 21 rule files and 175 references changed since the plan's first commit). The largest registered bodies: `data/elasticsearch` 15,999, `devops/supply-chain-security` 15,991, `qa/java/security-testing/permission-testing` 15,972, `writing-plans` 15,962, `spec-vs-code-audit` 15,935, `component-testing` 15,935, `solution-blueprint` 15,898, `api-test-author/grpc` 15,863. Agents: `solution-planner` 13,949, `be-documenter` 13,921, `qa-test-case-designer` 13,888, `qa-test-planner` 13,820, `be-feature-documenter` 13,680. Rule files: `rules/plans.md` 6,834 (D12), `business-model.md` 5,982, `feature-docs.md` 5,953, `swift.md` 5,922, the rest at or under 2,508.
  - **Not done.** The default-branch merge (close-out step 6) and the commit: the queue commits, and a merge needs a commit. **Unverified:** `dev` installed alone with the moved skills, as before; no installed plugin was run.

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
- T1 and C1 run side by side after L1. Their files are disjoint.
- After T1 and C1, P1–P20 run side by side, three at a time. Their files are disjoint.
- G1 waits for every P task.

| # | Stack | Agent | Depends on | Runs beside | Budget |
|---|---|---|---|---|---|
| — | answer O1–O24, in reply to L1's question | **the user** | — | — | — |
| L1 | `docs` | `general-purpose` | none | — | ~55k |
| T1 | `docs` | `general-purpose` | L1 | C1 | ~135k |
| C1 | `docs` | `general-purpose` | L1 | T1 | ~130k |
| P1 | `docs` | `general-purpose` | L1, T1, C1 | P2–P20 (three at a time) | ~115k |
| P2 | `docs` | `general-purpose` | L1, T1, C1 | P1, P3–P20 | ~105k |
| P3 | `docs` | `general-purpose` | L1, T1, C1 | P1–P2, P4–P20 | ~120k |
| P4 | `docs` | `general-purpose` | L1, T1, C1 | P1–P3, P5–P20 | ~125k |
| P5 | `docs` | `general-purpose` | L1, T1, C1 | P1–P4, P6–P20 | ~125k |
| P6 | `docs` | `general-purpose` | L1, T1, C1 | P1–P5, P7–P20 | ~125k |
| P7 | `docs` | `general-purpose` | L1, T1, C1 | P1–P6, P8–P20 | ~100k |
| P8 | `docs` | `general-purpose` | L1, T1, C1 | P1–P7, P9–P20 | ~120k |
| P9 | `docs` | `general-purpose` | L1, T1, C1 | P1–P8, P10–P20 | ~125k |
| P10 | `docs` | `general-purpose` | L1, T1, C1 | P1–P9, P11–P20 | ~110k |
| P11 | `docs` | `general-purpose` | L1, T1, C1 | P1–P10, P12–P20 | ~125k |
| P12 | `docs` | `general-purpose` | L1, T1, C1 | P1–P11, P13–P20 | ~115k |
| P13 | `docs` | `general-purpose` | L1, T1, C1 | P1–P12, P14–P20 | ~110k |
| P14 | `docs` | `general-purpose` | L1, T1, C1 | P1–P13, P15–P20 | ~125k |
| P15 | `docs` | `general-purpose` | L1, T1, C1 | P1–P14, P16–P20 | ~110k |
| P16 | `docs` | `general-purpose` | L1, T1, C1 | P1–P15, P17–P20 | ~125k |
| P17 | `docs` | `general-purpose` | L1, T1, C1 | P1–P16, P18–P20 | ~140k |
| P18 | `docs` | `general-purpose` | L1, T1, C1 | P1–P17, P19–P20 | ~140k |
| P19 | `docs` | `general-purpose` | L1, T1, C1 | P1–P18, P20 | ~110k |
| P20 | `docs` | `general-purpose` | L1, T1, C1 | P1–P19 | ~130k |
| G1 | `docs` | `general-purpose` | L1, T1, C1, P1–P20 | — | ~110k |

Every task has landed. No prompt block remains.
