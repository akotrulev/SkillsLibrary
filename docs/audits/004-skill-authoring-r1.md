# 004 — Skill-authoring audit, round 1 (2026-11-20)

**Standard:** `engineering-practices/writing-for-agents/SKILL.md`, rules R1–R23.
**Plan:** `docs/plans/014-authoring-standard-domain-language-feature-prototype.md`, §8, D7, D16, D17, tasks A3 (the lint and the front doors) and A4 (the agents, the sample and the summary).
**Read-only.** Nothing outside `tools/` was changed; the remediation is the next plan's (A5).

## Scope

| Part | What | How | Task |
|---|---|---|---|
| Lint | every in-scope `SKILL.md` with its rule files and `references/*.md`, and every agent in `marketplace.json` | `python3 tools/skill-lint.py --json` (R1, R3, R6–R14) | A3 |
| Size | every skill and agent | `python3 tools/token-audit.py --violations-only` (R2) | A3 |
| Judgment | the 38 listed front doors | read, against R4 and R15–R23 | A3 |
| Judgment | each plugin's front-door agent; one hidden skill per domain folder | read, against R13–R23 | A4 |

Excluded from the lint by name: `auth/cognito-*/`, `communication/`, `extras/`, `meta/skill-creator/`, `.skill-template/`, `tools/fixtures/`, `**/vendor/**`, and since this round `**/bundled/**` (upstream rule sets left unregistered on purpose, D16).

### The lint, ruled before it was trusted

The first sweep gave **552** findings. Two rules were mostly reading text that is not what they mean, so the lint was fixed rather than the findings reported (D16; fixtures `tools/fixtures/skill-lint/r12-hidden-mention/` and `r8-named-skill/`; `python3 -m pytest tools/test_skill_lint.py -q` → 95 passed, 99% branch):

- **R12** flagged any form of invoke/call/run anywhere on a line beside a hidden `plugin:name` (140 findings, 2 real: "when running against …", "`docker run`", "a failing run", "which you cannot invoke yourself"). It now needs the Skill tool named, or a bare `invoke`/`call`/`run` right before the name, not negated. `spec-vs-code-audit/SKILL.md:50`, the line A2 asked about, names the agent and is clean.
- **R8** resolved a backticked `references/x.md` against the file's own folder only, so a pointer into another skill named on the same line (`` `evidence-capture` + `references/playwright.md` `` in agents' Load cells) failed (158 findings). It now also resolves inside a skill named in a code span on that line or the line above (hard-wrapped prose). An unqualified pointer still fails, and those 22 are real (Data issues below).
- **`bundled/`** held upstream text that the house standard never governed (R1, R7, R10, R11 hits in `frontend/react/bundled/`, `qa/_shared/bundled/security-audit/`, …).

After the fixes: **238 findings in 172 files** (41 major, 197 minor), exit 1.

## Lint summary — per plugin × rule

A file registered in several plugins counts once, under all of them. `(unregistered)` holds the skills loaded by path only (`docs/skills-catalog.md:24`).

| Plugin | R1 | R3 | R6 | R7 | R8 | R9 | R10 | R11 | R12 | R13 | R14 | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| (unregistered) |  | 17 |  | 9 |  |  |  |  |  |  |  | 26 |
| be-dotnet |  |  |  | 2 |  |  |  |  |  |  |  | 2 |
| be-java |  |  |  | 2 |  |  |  |  |  |  |  | 2 |
| be-node |  |  |  | 2 |  |  |  |  |  |  |  | 2 |
| be-python |  |  |  | 2 |  |  |  |  |  |  |  | 2 |
| be-rust |  |  |  | 2 |  |  |  |  |  |  |  | 2 |
| business-analysis |  |  |  | 2 |  |  | 5 | 1 |  |  |  | 8 |
| data |  |  |  | 2 |  |  |  | 1 |  |  |  | 3 |
| design |  |  |  | 2 | 6 |  |  |  |  | 1 |  | 9 |
| desktop-macos |  | 1 |  | 2 |  | 1 |  |  |  |  |  | 4 |
| desktop-macos, desktop-windows |  | 1 |  |  |  |  |  |  |  |  |  | 1 |
| desktop-windows |  | 1 |  | 2 |  | 1 |  |  |  |  |  | 4 |
| dev |  | 2 |  | 9 | 6 | 4 | 1 |  | 1 | 2 |  | 25 |
| devops |  |  |  | 2 |  |  |  |  |  |  |  | 2 |
| fe-blazor |  | 1 |  | 2 | 1 |  |  |  |  |  |  | 4 |
| fe-react |  | 1 | 1 | 2 |  | 2 |  |  |  |  |  | 6 |
| mobile-android |  | 2 |  | 2 |  | 1 |  |  |  |  |  | 5 |
| mobile-ios |  | 1 |  | 2 |  | 1 |  |  |  |  |  | 4 |
| mobile-react-native |  | 1 |  | 2 |  | 1 |  |  |  |  |  | 4 |
| penetration-testing |  | 1 |  |  |  |  |  |  |  |  |  | 1 |
| qa-dotnet |  | 2 |  | 2 | 1 | 29 |  |  |  |  |  | 34 |
| qa-dotnet, qa-java, qa-typescript |  |  | 3 | 2 | 4 | 1 | 3 | 6 |  | 2 |  | 21 |
| qa-java |  |  |  | 2 | 1 | 24 |  |  |  |  |  | 27 |
| qa-typescript |  |  | 1 | 2 | 3 | 23 |  |  |  |  |  | 29 |
| security-governance |  |  |  | 2 |  | 1 | 2 |  |  |  |  | 5 |
| tooling |  |  |  | 2 |  |  |  |  | 1 |  |  | 3 |
| training-data |  |  |  | 2 |  |  |  |  |  | 1 |  | 3 |
| **Total** | 0 | 31 | 5 | 64 | 22 | 89 | 11 | 8 | 2 | 6 | 0 | **238** |

### Size budgets (R2, `token-audit`)

89 violations: 22 skill descriptions over 200 chars, 63 `SKILL.md` bodies over 16,000, 0 agent descriptions over 360, 4 agent files over 14,000 (`be-documenter` 17,599, `solution-planner` 16,835, `qa-test-case-designer` 16,323, `qa-test-planner` 14,847). By plugin: qa-java 20, dev 11, devops 7, qa-dotnet 6, qa-typescript 6, fe-react 6, penetration-testing 6, fe-blazor 4, data 4, be-dotnet 3, the rest 1–2. Among front doors: 19 of the 23 `rules` descriptions (209–222 chars) and three bodies (`writing-plans` 25,316, `spec-vs-code-audit` 24,887, `feature-audit` 19,996). The full list is the command's output; it is not copied here.

## The listed front doors (38)

Registered skills without `disable-model-invocation: true`, from `.claude-plugin/marketplace.json`: 40 listings, 38 skills (`python-web-testing` is registered in all three `qa-*` plugins).

| Plugin | Front doors |
|---|---|
| dev | `feature` (`engineering-practices/brainstorming`) · `plan-feature` (`writing-plans`) · `debugging` (`systematic-debugging`) · `verify` (`verify-before-done`) · `quality-constraints` · `source-grounding` · `writing-for-agents` · `notebooklm` · `audit-spec` (`spec-vs-code-audit`) · `audit-feature` (`feature-audit`) · `rules` |
| design | `prototype` · `rules` |
| qa-java, qa-dotnet, qa-typescript | `python-web-testing` (`qa/_shared/`, one skill) · `inhouse-framework-conventions` (one per lane) · `rules` (one per lane) |
| fe-blazor, fe-react, data, business-analysis, mobile-react-native, mobile-ios, mobile-android, desktop-macos, desktop-windows, be-dotnet, be-java, be-node, be-python, be-rust, devops, security-governance, training-data, tooling | `rules` (one each) |

The 23 `rules` skills share one shape and were judged as a group; a shared finding is one row naming all of them.

## Findings

Severity per the rule table and `CLAUDE.md` "Review behavior". Every row cites its rule. Lint rows are listed whole for the major rules; the minor lint rules (R3, R6, R7, R9) are listed by file in the closing appendix, since `python3 tools/skill-lint.py <path>` reproduces each line.

### Data issues

Wrong facts in the text: dangling paths (R8), stale names and versions.

| Severity | Location | Issue | Suggested fix |
|---|---|---|---|
| major | backend/_shared/business-documentation/references/example-area.md:82 | R8 — pointer 'bookings.md' does not resolve |  |
| major | backend/_shared/business-documentation/references/example-area.md:139 | R8 — pointer 'scheduling.md' does not resolve |  |
| major | backend/_shared/business-documentation/references/example-area.md:233 | R8 — pointer 'bookings.md' does not resolve |  |
| major | backend/_shared/business-documentation/references/example-area.md:234 | R8 — pointer 'scheduling.md' does not resolve |  |
| major | design/agents/design-auditor.md:74 | R8 — pointer 'references/report-template.md' does not resolve | Name the engine by path: `engineering-practices/standards-audit-engine/references/report-template.md` |
| major | design/design-tokens/SKILL.md:23 | R8 — pointer 'references/pro-rules.md' does not resolve | Name the owner: `design/ui-ux-pro-max/references/pro-rules.md` |
| major | design/iconography/SKILL.md:23 | R8 — pointer 'references/pro-rules.md' does not resolve | Name the owner: `design/ui-ux-pro-max/references/pro-rules.md` |
| major | design/motion/SKILL.md:23 | R8 — pointer 'references/pro-rules.md' does not resolve | Name the owner: `design/ui-ux-pro-max/references/pro-rules.md` |
| major | design/ux-patterns/SKILL.md:31 | R8 — pointer 'references/pro-rules.md' does not resolve | Name the owner: `design/ui-ux-pro-max/references/pro-rules.md` |
| major | design/visual-identity/SKILL.md:32 | R8 — pointer 'references/pro-rules.md' does not resolve | Name the owner: `design/ui-ux-pro-max/references/pro-rules.md` |
| major | engineering-practices/notebooklm/SKILL.md:23 | R8 — pointer 'scripts/run.py' does not resolve | Point into the bundle: `engineering-practices/bundled/notebooklm/scripts/run.py` |
| major | engineering-practices/notebooklm/SKILL.md:40 | R8 — pointer 'scripts/config.py' does not resolve | Point into the bundle: `engineering-practices/bundled/notebooklm/scripts/config.py` |
| major | frontend/blazor/skills/accessibility/SKILL.md:11 | R8 — pointer '../../../qa' does not resolve | Link the skill itself: `../../../../qa/<stack>/skills/accessibility-testing/SKILL.md`, or name it without a link |
| major | qa/manual/agents/qa-explorer.md:28 | R8 — pointer 'references/probes.md' does not resolve | Name the owner: `qa/manual/app-exploration/references/probes.md` |
| major | qa/manual/agents/qa-explorer.md:39 | R8 — pointer 'references/checks.md' does not resolve | Name the owner: `qa/manual/app-exploration/references/checks.md` |
| major | qa/manual/agents/qa-explorer.md:40 | R8 — pointer 'references/checks.md' does not resolve | Name the owner: `qa/manual/app-exploration/references/checks.md` |
| major | qa/manual/cross-feature-test-design/SKILL.md:21 | R8 — pointer 'references/connections.md' does not resolve | Name the owner on this line, as line 11 does |
| major | qa/reporting/dotnet/skills/test-reports/SKILL.md:171 | R8 — pointer 'references/trace-correlation.md' does not resolve | Name the path: `qa/<stack>/skills/ui-test-author/playwright/references/trace-correlation.md` |
| major | qa/reporting/java/skills/test-reports/SKILL.md:178 | R8 — pointer 'references/trace-correlation.md' does not resolve | Name the path: `qa/<stack>/skills/ui-test-author/playwright/references/trace-correlation.md` |
| major | qa/reporting/typescript/skills/test-reports/SKILL.md:163 | R8 — pointer 'references/trace-correlation.md' does not resolve | Name the path: `qa/<stack>/skills/ui-test-author/playwright/references/trace-correlation.md` |
| major | qa/typescript/skills/bdd-project-scaffold/SKILL.md:132 | R8 — pointer 'references/config-and-fixtures.md' does not resolve | Name the owning skill on the same line |
| major | qa/typescript/skills/ui-test-author/review/SKILL.md:15 | R8 — pointer 'references/config-and-fixtures.md' does not resolve | Name the owning skill on the same line |
| major | engineering-practices/writing-plans/SKILL.md:3 | R3/R1 rename leftover — "Not for the design itself (design)": no skill is named `design` since `dev:design` became `feature` (D3); G1's cross-reference read missed it | "Not for the design itself (feature)." |
| major | engineering-practices/systematic-debugging/SKILL.md:3 | Same leftover — "Not for new work (design)" | "Not for new work (feature)." |
| minor | engineering-practices/writing-plans/SKILL.md:311 | "exactly one of the eight" stacks counts the list at :156–158, which lacks `mobile` and `desktop` (Logical conflicts) | Drop the count, or make it match plan-format's ten |
| minor | qa/dotnet/skills/inhouse-framework-conventions/SKILL.md:239 | `IRestResponse` was removed in RestSharp 107 | "a typed DTO, not `RestResponse`" |

### Code issues

Text that breaks a rule.

**Lint, major rules.**

| Severity | Location | Issue | Suggested fix |
|---|---|---|---|
| major | backend/_shared/experience-plan/SKILL.md:159 | R10 — placeholder 'TBD' | Put the marker in a code span (D13), or write the house form in backticks |
| major | business-analysis/skills/ba-dependency-map/references/example-dependency-map.md:27 | R10 — placeholder 'TBD' | Put the marker in a code span (D13), or write the house form in backticks |
| major | business-analysis/skills/ba-dependency-map/references/example-dependency-map.md:38 | R10 — placeholder 'TBD' | Put the marker in a code span (D13), or write the house form in backticks |
| major | business-analysis/skills/ba-dependency-map/references/example-dependency-map.md:39 | R10 — placeholder 'TBD' | Put the marker in a code span (D13), or write the house form in backticks |
| major | business-analysis/skills/ba-dependency-map/references/example-dependency-map.md:79 | R10 — placeholder 'TBD' | Put the marker in a code span (D13), or write the house form in backticks |
| major | business-analysis/skills/ba-dependency-map/references/example-dependency-map.md:91 | R10 — placeholder 'TBD' | Put the marker in a code span (D13), or write the house form in backticks |
| major | qa/_shared/webmcp-testing/SKILL.md:42 | R10 — placeholder 'TBD' | Put the marker in a code span (D13), or write the house form in backticks |
| major | qa/manual/test-plan-writer/SKILL.md:130 | R10 — placeholder 'TBD' | Put the marker in a code span (D13), or write the house form in backticks |
| major | qa/manual/test-strategy/SKILL.md:166 | R10 — placeholder 'TBD' | Put the marker in a code span (D13), or write the house form in backticks |
| major | security/rules-security-governance/security-governance.md:40 | R10 — placeholder 'TBD' | Put the marker in a code span (D13), or write the house form in backticks |
| major | security/standards-audit/references/conformance-checklist.md:253 | R10 — placeholder 'TBD' | Put the marker in a code span (D13), or write the house form in backticks |
| major | backend/_shared/agents/solution-planner.md:68 | R12 — tells a model to invoke hidden skill dev:plan-delivery; name the path to Read, or the agent | Name the path to Read (`backend/_shared/delivery-plan`) |
| major | tooling/skills/mcp-builder/SKILL.md:11 | R12 — tells a model to invoke hidden skill tooling:capability-contract; name the path to Read, or the agent | Name the agent or path: "read `tooling/skills/capability-contract`" / the `tooling-engineer` agent |
| major | backend/_shared/agents/be-feature-documenter.md:89 | R13 — '## Report' holds no Mode: line | Add the template's `## Report` block with a `Mode:` line |
| major | design/agents/design-auditor.md:94 | R13 — '## Report' holds no Mode: line | Add the template's `## Report` block with a `Mode:` line |
| major | engineering-practices/agents/code-auditor.md:51 | R13 — '## Report' holds no Mode: line | Add the template's `## Report` block with a `Mode:` line |
| major | qa/manual/agents/qa-feature-spec-writer.md:33 | R13 — '## Steps' holds no table with Load and Done when columns | Make Steps the template table (`# | Step | Load | Done when`) |
| major | qa/manual/agents/qa-feature-spec-writer.md:100 | R13 — '## Report' holds no Mode: line | Add the template's `## Report` block with a `Mode:` line |
| major | training-data/agents/dataset-auditor.md:60 | R13 — '## Report' holds no Mode: line | Add the template's `## Report` block with a `Mode:` line |

**Lint, minor rules (counts; files in the appendix).**

| Severity | Location | Issue | Suggested fix |
|---|---|---|---|
| minor | 23 `rules` SKILL.md + `python-web-testing`, `systematic-debugging`, `verify-before-done`, `writing-plans`, `notebooklm` (R7, 55 findings, 28 files) | R7 — listed front doors without `## When to use` / `## When NOT to use` | Add both headings; for `rules`, one line each ("installing or updating the rules" / "writing code: the rule files apply themselves") |
| minor | `engineering-practices/{agent-orientation-cache,code-comments,standards-audit-engine}`, `ai-development/{claude-api,mcp-builder}` (R7 9, R3 15) | R7/R3 — unregistered skills carry no `disable-model-invocation: true`, so the shared front-door test (`plugin-surface-check` rule 7, `skill-lint`) reads them as front doors | Add the flag: it states what they are and keeps them hidden if ever registered; then their description shape is moot (R3) |
| minor | 31 findings, 20 files (R3) | R3 — description lacks `Use when`, `Triggers "…"` or the closing `Not for <case> (<sibling>).` — mostly the closing clause (the `auth0-*` skills, `desktop/_shared/security`, `kotlin-multiplatform`, …) | Add the missing clause |
| minor | 5 findings, 4 files (R6) | R6 — hidden skills with routing headings (`Handoff`, `When to use Pact at all`, `When NOT to use any of these tools`) | Rename to a topic heading ("Choosing Pact", "Profiler hand-off") |
| minor | 89 findings, 89 files (R9; 76 in the three `qa-*` lanes) | R9 — reference files over 300 lines with no contents list before the first `##` | Add a contents list of the `##` headings |

**Size, front doors (R2) and always-loaded rule files (R23).**

| Severity | Location | Issue | Suggested fix |
|---|---|---|---|
| major | 19 of 23 `rules` SKILL.md (all but `design`, `business-analysis`, `desktop-macos`, `desktop-windows`; 209–222 chars) | R2 — description over 200 chars | Drop the parenthetical list of what the rules cover; the trigger and the sibling stay |
| major | engineering-practices/writing-plans/SKILL.md (25,316), engineering-practices/spec-vs-code-audit/SKILL.md (24,887), engineering-practices/feature-audit/SKILL.md (19,996) | R2 — front-door body over 16,000 chars | Disclose by branch (R16 rows below): the restated rules go to pointers, Mode B to `references/` |
| major | engineering-practices/rules/feature-docs.md (10,500), engineering-practices/rules/plans.md (8,206), business-analysis/skills/rules/business-model.md (6,909), desktop/macos/skills/rules/swift.md (6,686) | R23 — rule file over 6,000 chars (largest file per folder taken as the core file); `feature-docs.md:9–40` carries the document's shape and procedure, which belongs in the documenting skill | Keep the constraints; move shape and procedure behind a one-line pointer |
| major | 17 non-core rule files over 2,500 chars: business-analysis `backlog-stories.md` 4,065, `backlog-epics.md` 2,646, `backlog-requirements.md` 2,541; desktop-macos `swiftui-mac.md` 3,945, `xcode-config.md` 3,422, `mac-accessibility.md` 3,413, `swift-persistence.md` 2,934, `appkit.md` 2,547, `swift-networking.md` 2,502; desktop-windows `winui-xaml.md` 3,610, `cppwinrt.md` 3,571, `win-accessibility.md` 2,788; qa-dotnet `desktop-tests.md` 3,403, `web-ui.md` 2,714; qa-java `desktop-tests.md` 3,636, `qa-java-ui.md` 2,523; qa-typescript `ui-tests.md` 2,685 | R23 — rule file over 2,500 chars | Trim to the constraints; point at the skill for the recipe |

**Judgment, the front doors.**

| Severity | Location | Issue | Suggested fix |
|---|---|---|---|
| major | all 23 `rules` SKILL.md, Procedure steps 3, 4, 5, 7 (e.g. backend/dotnet/skills/rules/SKILL.md:33–44, engineering-practices/rules/SKILL.md:33–44) | R15 — only step 2 has a stop condition; the others end on an activity ("Copy each file", "read CLAUDE.md … and list them") | Add a done-when per step: 3 "every source file is in the target"; 7 "each contradiction listed, or the report says none" |
| major | all 23 `rules` SKILL.md, step 5 "Fit the paths" (backend/dotnet/skills/rules/SKILL.md:37–42 widest) | R15 — not exhaustive: never says when the search is complete | "every file each command lists is matched by an installed glob, or a glob is proposed for it" |
| major | all 23 `rules` SKILL.md, the rule-file table (backend/dotnet/skills/rules/SKILL.md:13–19, engineering-practices/rules/SKILL.md:13–17) | R17 — the "Loads when" column caches each rule file's own `paths:` frontmatter, one `head` away; two copies drift when a glob changes | Drop the column and the glosses; step 5 already reads each file's `paths:` |
| major | 21 `rules` SKILL.md (all but `dev`, `tooling`), step 2 (backend/dotnet/skills/rules/SKILL.md:32 "all five files"; qa/dotnet "all eleven"; desktop/windows "all twelve") | R17 — hard-coded file count, an `ls` cached in text (every count is right today) | Use `engineering-practices/rules/SKILL.md:32`'s form: every `*.md` beside SKILL.md, stop if empty |
| minor | all 23 `rules` SKILL.md, the unattended paragraph (backend/dotnet/skills/rules/SKILL.md:27) | R16 — the headless branch's rule sits inline before the Procedure | One sentence inline; the rest under the step it governs |
| minor | all 23 `rules` SKILL.md (backend/dotnet/skills/rules/SKILL.md:25) | R19 — "A person types `/<plugin>:rules`." changes nothing a model does | Delete the sentence |
| minor | 22 `rules` SKILL.md (all but `tooling`; backend/dotnet/skills/rules/SKILL.md:9) | R19 — "so a session that never touches persistence code never pays for …" explains path scoping, changes no behaviour | Delete the clause |
| minor | all 23 `rules` SKILL.md (backend/dotnet/skills/rules/SKILL.md:27, "Never guess the answer.") | R18 — bare prohibition after its positive target | Delete it; the `.plugin` fallback is the target |
| major | engineering-practices/writing-plans/SKILL.md:68, 91, 108, 154, 174, 239 | R15 — steps 1–6 end on no done-when | Step 1 "the gap table written, each Today cell with `file:line`"; step 3 "every task has its position and its Depends on" |
| major | engineering-practices/writing-plans/SKILL.md:253 (and 136–145, 279–287) | R17 — restates the gate rule, the two closing tasks and the close-out from `CLAUDE.md` "Planning" and plan-format §5/§7 | One-line pointers to plan-format §5 and the `plans.md` rule file |
| major | engineering-practices/writing-plans/SKILL.md:156–158 | R17 — the stack list is a second copy of plan-format §4 and has drifted (Logical conflicts) | Point at plan-format §4 |
| minor | engineering-practices/writing-plans/SKILL.md:14, 98–99 | R19 — "DRY. YAGNI. Frequent commits." and "You reason best about code you can hold in context" | Delete |
| minor | engineering-practices/writing-plans/SKILL.md:82–89, 341–344 | R16 — the web-route rendering block and self-review item 16 inline; only web plans reach them | Move behind "a web route in the plan → read …" |
| minor | engineering-practices/writing-plans/SKILL.md:38, 297–344 | R20 — "checkpoint reports", and "check" for self-review items | "task reports"; name the items as criteria |
| major | engineering-practices/systematic-debugging/SKILL.md:22, 90, 112, 183–184 | R15 — steps 1–3 have no done-when; the "Success Criteria" cells "Understand what and why", "Identify differences" are not checkable | Step 1 "reproduced, the failing component named with the evidence line"; step 3 "one hypothesis confirmed or refuted by a single-variable change" |
| major | engineering-practices/systematic-debugging/SKILL.md:60–75 | R21 — the bash example carries `# Layer 1: …` inline comments | Delete them; the `echo "=== … ==="` lines already label each layer |
| minor | engineering-practices/systematic-debugging/SKILL.md:44–78 | R16 — the 35-line multi-component example is inline; only cross-component bugs need it | Move behind "the bug crosses component boundaries → read …" |
| minor | engineering-practices/systematic-debugging/SKILL.md:27, 36, 105, 131, 148–149 | R18 — bare prohibitions ("Don't skip past errors", "don't guess", …) | State the target: "read every warning and trace line", "gather more data", … |
| minor | engineering-practices/systematic-debugging/SKILL.md:16, 28, 100 | R19 — "They often contain the exact solution"; 100 repeats 99 | Delete |
| minor | engineering-practices/systematic-debugging/SKILL.md:181 | R20 — the column "Success Criteria" paraphrases *done when* | Rename the column "Done when" |
| minor | engineering-practices/verify-before-done/SKILL.md:18 | R20 — "The Gate Function" uses *gate* for an evidence check; the house *gate* is a task's `Gate:` line (used so at :16) | "The evidence check" |
| minor | engineering-practices/verify-before-done/SKILL.md:12, 106–112 | R19 — "Why This Matters" and a restatement of :10 | Delete |
| major | engineering-practices/quality-constraints/SKILL.md:33, 34, 36, 38–40 | R17 — rows restate `CLAUDE.md` "Test code rules" (no OR assertion, no swallowed error, coverage exclusions, no test written to move the number) | Each row: a pointer to the rule by name plus its diff-evidence command |
| major | engineering-practices/quality-constraints/SKILL.md:45 | R15 — "When a check goes red" ends on "carry on" | End on "the test unedited and the reason recorded in the plan's open issues" |
| minor | engineering-practices/quality-constraints/SKILL.md:10, 17, 42, 45 | R20 — "check" for what the house calls a gate | *gate* for the task's tests, *evidence* for the diff commands |
| minor | engineering-practices/quality-constraints/SKILL.md:12 | R19 — "An agent writes more than anyone reads…" | Delete |
| major | engineering-practices/source-grounding/SKILL.md:27, 37, 52, 56 | R15 — steps 1–4 have no done-when | Step 2 "the page for the detected version fetched and its signature extracted"; step 3 "every version-bound decision traces to that page or is flagged unverified" |
| minor | engineering-practices/source-grounding/SKILL.md:48 | R18 — "Never a primary source: forum answers, …" without the target first | Lead with "Use only official docs, changelogs, migration guides and standards" |
| minor | engineering-practices/source-grounding/SKILL.md:10, 71–74 | R19 — the opening sentence and "Common mistakes" restate steps 2–4 | Delete |
| major | engineering-practices/notebooklm/SKILL.md:22–25 | R15 — load-order steps 1–4 have no done-when | Step 1 "bundled SKILL.md and AUTHENTICATION.md read, the notebook library path known" |
| major | engineering-practices/notebooklm/SKILL.md:54 | R17 — pins `patchright==1.55.2`, `python-dotenv==1.0.0` cached from `bundled/notebooklm/requirements.txt` | "`run.py` installs `requirements.txt` into the venv on first use" |
| minor | engineering-practices/notebooklm/SKILL.md:8 | R19 — restates the description | Delete |
| major | engineering-practices/brainstorming/SKILL.md:62–64 | R17 — "YAGNI", "follow existing patterns" restate `CLAUDE.md` "Simplicity (KISS)" and the read-2–3-files rule | Point at the section; keep the design-specific part |
| minor | engineering-practices/brainstorming/SKILL.md:20 | R20 — "runs its own design gate": *gate* for an approval | "design approval" |
| major | engineering-practices/spec-vs-code-audit/SKILL.md:147, 151, 175–177, 241–243 | R15 — Mode A steps 2–4 and Mode B step 1 have no done-when | Step 3 "every register id has one verdict, its evidence trail and confidence"; step 4 "every section has its rollup and the three finding headings" |
| major | engineering-practices/spec-vs-code-audit/SKILL.md:111, 114, 165–173, 247, 262–268, 333–339 | R17 — restates `engineering-practices/rules/audits.md:15–27` (three classes, permanent ids, Resolved only on a re-trace, section summaries) | Keep the verdict table and templates; point at `audits.md` for the rest |
| minor | engineering-practices/spec-vs-code-audit/SKILL.md:237–339 | R16 — Mode B (≈100 lines) inline; only a re-audit reaches it | `references/re-audit.md` behind "a register and a prior report exist" |
| minor | engineering-practices/spec-vs-code-audit/SKILL.md:10, 51, 343, 345 | R19 — "read-only" stated three times; the Evidence pointer twice | Keep :10 |
| major | engineering-practices/feature-audit/SKILL.md:80, 84, 112, 175 | R15 — Mode A steps 2–5 have no done-when | "every entry point under a lettered surface"; "every finding has mechanism, scenario, severity, class and fix direction" |
| major | engineering-practices/feature-audit/SKILL.md:100–108, 183, 187, 207, 285–289 | R17 — restates `audits.md` and duplicates audit-spec's class table | Point at `audits.md`; keep the "Typical here" column |
| minor | engineering-practices/feature-audit/SKILL.md:177–289 | R16 — Mode B inline | `references/re-audit.md` behind "a prior report exists" |
| minor | engineering-practices/feature-audit/SKILL.md:10, 50, 295 | R19 — read-only repeated; "Same policy as audit-spec" adds nothing beyond the pointer | Keep one |
| minor | design/prototype/SKILL.md:32, 49–57 | R16 — step 7 and "In-app hand-off" are on-request only, inline | `references/in-app-handoff.md` behind "the user asks for the variants inside the real app" |
| minor | design/prototype/SKILL.md:8 | R19 — "No app has to run, and no stack's code is touched" repeats Rules :61 | Delete at :8 |
| major | qa/_shared/python-web-testing/SKILL.md:46–56 | R17 — the Never/Instead table and locator order restate the `qa-*` UI rule files (e.g. `qa/typescript/skills/rules/ui-tests.md:21`) | Point at the rule; keep only the Python spellings |
| major | qa/_shared/python-web-testing/SKILL.md:134 | R22 — "move it to the stack-native skill" names neither the agent nor a path; :13–15 names `qa-ui-<stack>` correctly | "hand it to the `qa-ui-<stack>` agent" |
| minor | qa/_shared/python-web-testing/SKILL.md:121–134 | R16 — the pytest-playwright section inline; only a repeated check reaches it | `references/` behind "the same verification will run again" |
| major | qa/java/skills/inhouse-framework-conventions/SKILL.md:172–178, 263–275, 277–; qa/dotnet/…:174–180, 263–, 278–; qa/typescript/…:165–171, 237–, 251– | R17 — Rules, Quality bar and Anti-examples restate `CLAUDE.md` "Test code rules", three times per file | Point at the rules once; keep the Accelerator specifics (JSON screens, `locator(key)`, `PageBase`, `test-core`) |
| minor | qa/java/skills/inhouse-framework-conventions/SKILL.md:249–261; qa/dotnet/…:249–261; qa/typescript/…:223–235 | R19 — "Claude Code workflow" section ("when rate-limited … degrade gracefully") | Delete, or keep only the commands |
| major | qa/typescript/skills/inhouse-framework-conventions/SKILL.md:155 | R21 — the example inlines `'Wrong-Passw0rd!'`, against the unique-value rule and its own :168 | `withPassword(\`Wrong-${crypto.randomUUID()}\`)`, as the Java and .NET lanes do |

Passed clean on R4 and the description half of R23: every front door's description is a *when* plus at most one clause of *what*. `writing-for-agents` passes R15–R23 against itself (one minor conflict below). R22 holds where a front door points at a hidden skill by a repo path to `Read` (`brainstorming/SKILL.md:33`, `spec-vs-code-audit/SKILL.md:49, 93, 348`, `feature-audit/SKILL.md:298`, `inhouse-framework-conventions` → `evidence-capture`): a path is what R12 and R22 accept.

### Logical conflicts

Two texts that cannot both hold; the owner decides.

| Severity | Location | Issue | Suggested fix |
|---|---|---|---|
| major | engineering-practices/writing-for-agents/SKILL.md (R8 row) vs tools/skill-lint.py (D16) | R8 — the standard says a pointer resolves "relative to that file's folder"; the lint, by D16, also resolves inside a skill named on the line, which agents' Load cells rely on | Owner of the standard: reword R8 to the lint's reading, or rewrite every Load-cell pointer as a full path |
| major | engineering-practices/writing-plans/SKILL.md:156–158 vs engineering-practices/writing-plans/references/plan-format.md:122 | plan-feature's stack list has no `mobile` or `desktop`; plan-format §4 has both, and `CLAUDE.md` "Planning" names mobile tasks | Point at plan-format §4 as the one list |
| minor | business-analysis/skills/ba-project-memory/SKILL.md:116 | R11 — heading uses 'slice', the KB cross-section term of test design, not a unit of work | Owner decides: house word ("cross-section") or an R11 exception for the domain term |
| minor | data/_shared/migrations/SKILL.md:63 | R11 — table header uses 'Phase'; here it is the expand/contract migration term, not a unit of work | Owner decides: "Step" in the header, or an R11 exception for the migration term |
| minor | qa/manual/cross-feature-test-design/SKILL.md:28 | R11 — heading uses 'slice', the KB cross-section term of test design, not a unit of work | Owner decides: house word ("cross-section") or an R11 exception for the domain term |
| minor | qa/manual/cross-feature-test-design/SKILL.md:30 | R11 — table header uses 'Slice', the KB cross-section term, not a unit of work | Owner decides: house word ("cross-section") or an R11 exception for the domain term |
| minor | qa/manual/cross-feature-test-design/references/example-cancel-booking.md:9 | R11 — heading uses 'slice', the KB cross-section term of test design, not a unit of work | Owner decides: house word ("cross-section") or an R11 exception for the domain term |
| minor | qa/manual/cross-feature-test-design/references/example-cancel-booking.md:76 | R11 — table header uses 'Slice', the KB cross-section term, not a unit of work | Owner decides: house word ("cross-section") or an R11 exception for the domain term |
| minor | qa/manual/cross-feature-test-design/references/example-cancel-booking.md:103 | R11 — table header uses 'Slice', the KB cross-section term, not a unit of work | Owner decides: house word ("cross-section") or an R11 exception for the domain term |
| minor | qa/manual/requirements-breakdown/references/connections.md:9 | R11 — heading uses 'slice', the KB cross-section term of test design, not a unit of work | Owner decides: house word ("cross-section") or an R11 exception for the domain term |
| minor | engineering-practices/writing-for-agents/SKILL.md:114 vs :73 | R20 — the R20 row lists the vocabulary as five words; "Leading words" lists six (*done when*) | One list, pointed at |
| minor | engineering-practices/quality-constraints/SKILL.md:32 vs :39 | A test believed wrong is "a dated decision in the plan" at :32 and "the plan's open issues" at :39; `CLAUDE.md` "Planning" says both | "a dated `D<n>` in the plan's open issues and the final message" in both rows |
| major | qa/dotnet/skills/inhouse-framework-conventions/SKILL.md:150 vs :170–172, and qa/java/…/SKILL.md:283 | The .NET example asserts `Expect(Page).ToHaveURLAsync(…)` in the test body; the same file says tests never call a Page method, and the Java lane lists `assertThat(page).hasURL(…)` as an anti-example | Assert through a page-object member, or state the URL assertion as the sanctioned exception in all three lanes |
| major | qa/typescript/skills/inhouse-framework-conventions/SKILL.md:134 vs :100–110 | The rule says `this.selector("key")`; the example and `PageBase` use `this.locator(…)` | Make the rule `this.locator("key")` |
| major | qa/typescript/skills/inhouse-framework-conventions/SKILL.md:208 vs :109–114 | The rule wraps page methods in `test.step(…)`; the `LoginPage` example does not (Java and .NET carry `@Step` / `[AllureStep]`) | Add `test.step` to the example, or drop the rule |

## Round 1, second half (A4): the front-door agents and the sample

Judged against R13–R23 for agents (R13 and R14 are the lint's and sit above; R16, R21 apply to an agent's inline material and examples) and R4, R15–R21 for hidden skills (R22 and R23 do not apply to a hidden skill). Read by three Sonnet reviewers on one brief (`/tmp`, not kept); every Data and Logical row, and a sample of the Code rows, was re-read at its line before it went in. Three reviewer rows were dropped as wrong: `delivery-plan/SKILL.md:88` (`backend/_shared/session-budget/references/prompts-section-template.md` exists), `delivery-plan/SKILL.md:421` (the lint resolves `experience-plan/references/…` by D16), and a group row that called the template's own text a finding.

### The front-door agents (24)

The agent each plugin's name command runs (`commands/<plugin>.md` → `Read … agents/<agent>.md`). Seven plugins have no name command; for them the command the plugin presents as its entry was taken, as recorded in D17.

| Plugin | Command | Agent | Chars |
|---|---|---|---:|
| dev | `/dev:refine` ("the front door to the delivery lane"; no `/dev`) | `business-analysis/agents/requirements-author.md` | 12,192 |
| design | `/design:audit` (its only command) | `design/agents/design-auditor.md` | 13,765 |
| qa-java · qa-dotnet · qa-typescript | `/qa-<lang>:ui` (no name command; the UI lane is each plugin's primary) | `qa/{java,dotnet,typescript}/agents/qa-ui-<lang>.md` | 12,078 · 12,141 · 11,899 |
| penetration-testing | `/penetration-testing:pentest` | `security/agents/penetration-tester.md` | 11,376 |
| security-governance | `/security-governance:architect` | `security/agents/security-architect.md` | 8,818 |
| fe-blazor · fe-react | `/fe-blazor` · `/fe-react` | `frontend/{blazor,react}/agents/fe-<stack>.md` | 9,950 · 11,144 |
| mobile-react-native · mobile-ios · mobile-android | name command | `mobile/<stack>/agents/mobile-<stack>.md` | 9,287 · 9,698 · 9,092 |
| desktop-macos · desktop-windows | name command | `desktop/<os>/agents/desktop-<os>.md` | 10,310 · 12,281 |
| be-dotnet · be-java · be-node · be-python · be-rust | name command | `backend/<stack>/agents/be-<stack>.md` | 6,505 · 5,480 · 6,212 · 7,596 · 7,273 |
| data | `/data` | `data/agents/data-architect.md` | 8,974 |
| business-analysis | `/business-analysis` | `business-analysis/agents/business-analyst.md` | 10,401 |
| devops | `/devops` | `devops/agents/devops-engineer.md` | 10,452 |
| training-data | `/training-data` | `training-data/agents/dataset-engineer.md` | 8,558 |
| tooling | `/tooling` | `tooling/agents/tooling-engineer.md` | 8,845 |

None is over the 14,000-char agent budget (R2). The lint found R13 on `design-auditor.md:94` only among these (above).

### The sample (14)

The largest hidden `SKILL.md` in each top-level domain folder: hidden means `disable-model-invocation: true`, or unregistered and loaded by path; `bundled/` and `vendor/` excluded.

| Domain folder | Sampled skill | Chars |
|---|---|---:|
| qa | `qa/java/skills/ai-feature-testing/SKILL.md` | 21,807 |
| frontend | `frontend/react/skills/error-handling/SKILL.md` | 33,975 |
| desktop | `desktop/windows/skills/unit-testing/SKILL.md` | 14,806 |
| mobile | `mobile/android/skills/unit-testing/SKILL.md` | 16,859 |
| design | `design/visual-identity/SKILL.md` | 16,199 |
| backend | `backend/_shared/delivery-plan/SKILL.md` | 73,968 |
| observability | `observability/logs-traces-setup/SKILL.md` | 17,321 |
| data | `data/dynamodb/SKILL.md` | 19,539 |
| devops | `devops/k8s-security/SKILL.md` | 37,099 |
| security | `security/cloud-incident-response/SKILL.md` | 21,776 |
| business-analysis | `business-analysis/skills/ba-project-memory/SKILL.md` | 14,216 |
| training-data | `training-data/_shared/td-dataset-formats/SKILL.md` | 10,742 |
| tooling | `tooling/_shared/capability-contract/SKILL.md` | 11,520 |
| engineering-practices | `engineering-practices/standards-audit-engine/SKILL.md` (unregistered; `domain-modeling`, 3,676, is the largest flagged one) | 12,282 |

Eight of the fourteen are over the 16,000-char body budget and already in the R2 count. R4 passes on thirteen: only `standards-audit-engine` summarises its body in the description.

### Data issues (A4)

| Severity | Location | Issue | Suggested fix |
|---|---|---|---|
| major | mobile/android/agents/mobile-android.md:17 | "A `targetSdk` below 35 is a finding": Play requires API 36 (`CLAUDE.md` "Version policy", `mobile/_shared/store-compliance/SKILL.md`), so a 35 app passes orientation and fails the store | "below the `store-compliance` target is a finding", with no number |
| major | engineering-practices/standards-audit-engine/SKILL.md:3 | The description names a `<plugin>-conformance-audit` skill and a `/<plugin>-audit` command; neither exists: the stack skills are `standards-audit` and the commands `/<plugin>:audit` | "Loaded by a stack's `standards-audit` skill (`/<plugin>:audit`)" |
| minor | backend/_shared/delivery-plan/SKILL.md:687 | "exactly one of the eight values": the list at :120 has ten (`mobile`, `desktop` added), the same drift A3 found in `writing-plans/SKILL.md:311` | "one of the Stack values in Step 1" |
| minor | devops/k8s-security/SKILL.md:545 | "runs this skill (Step 3, K8s & runtime)": `devops/agents/infra-security-tester.md:42` runs it at step 4 | "(step 4, Kubernetes and runtime)", or drop the number |
| minor | security/cloud-incident-response/SKILL.md:131 | "added there by task G1" names a task of a past plan; a progress note, not a contract | "the crosswalk row lives in `security/compliance-evidence-mapping`" |
| minor | data/dynamodb/SKILL.md:14, 24, 96 | :24 "The current data samples pinned .NET 8 + SDK v3" describes files that no longer say so; :14 a GA date; :96 garbled: GSI reads are eventually consistent only, projections do not bear on it | Delete :24 and the GA date; :96 "eventually consistent reads only" |
| minor | observability/logs-traces-setup/SKILL.md:129, 193 | Promtail "deprecated Feb 2025, EOL ~Mar 2026" in the future tense, twice; "River config" is Alloy's pre-1.0 name | "Promtail reached end of life in Mar 2026; use Alloy" once |
| minor | mobile/android/skills/unit-testing/SKILL.md:11, 20–22, 135, 183 | "(plan 003)", "§4.3" point at nothing shipped; "at last check — built but unverified", "status unconfirmed", "verified … 2026-10-10" are a past session's notes baked into the recipe | Delete the plan refs and the verification notes; version-key against the project's catalog, as :20 says |

### Code issues (A4)

**Agents, shared defects** (one row each; the files named carry the same text).

| Severity | Location | Issue | Suggested fix |
|---|---|---|---|
| major | "Read the rules" (run-start item 1) in 20 agents: fe-blazor:20, fe-react:24, mobile-react-native:21, mobile-ios:16, mobile-android:16, desktop-macos:16, desktop-windows:16, be-dotnet:16, be-java:16, be-node:16, be-python:22, be-rust:16, data-architect:24, business-analyst:38, devops-engineer:22, dataset-engineer:23, qa-ui-java:16, qa-ui-dotnet:16, qa-ui-typescript:16, security-architect:26 | R17 — each lists its plugin's rule files by name (3–10), a folder listing one `ls` away that drifts with every added file; `.skill-template/agent.md` says "the core file, plus each path-scoped file the task touches" | The template wording with the core file named; keep only what `ls` cannot show (be-rust's inline `#[cfg(test)]` note, be-node's narrow `*.ts` globs, the ios/macos "a view in a folder no glob covers") |
| major | "Derive only what it leaves open" (item 2) and version asides: mobile-react-native:16, mobile-ios:17, 39, mobile-android:3, 17, desktop-macos:17, be-dotnet:17, be-java:17, be-node:17, be-python:23, be-rust:8, 17, qa-ui-dotnet:17 | R17 — the version lane's contents and support floors ("net6/net7 are past support", "Spring Boot 2.x", "Node 20", "below SDK 54", "Playwright (1.63 lane)", "Kotlin 2.4, AGP 9.4") restate `CLAUDE.md` "Version policy" and the core rule file (`android.md:14` lists the same items) | "the lane per the core rule file and `CLAUDE.md` 'Version policy', and the seams to reuse (…)" |
| major | Done-when cells for the design critique and budgets: fe-blazor:34, 36, fe-react:36, 38, mobile-react-native:35, 37, mobile-ios:30, 32, mobile-android:30, 32, 34, desktop-macos:32, 35, desktop-windows:55, 58 | R15 — "a design plan critiqued against the three AI-default looks", "performance budget met", "accessibility rules met in code", "distribution rows clean" name no artifact or source, so done and not done look alike; desktop step 6 also restates `CLAUDE.md` "Desktop code rules" | Name the proof: the critique table in the decision record; the rule file's items passed; the `performance` skill's budget table; "every `shared/distribution` row passed or waived with its reason" |
| major | Steps 1 and 4 Done-when: be-dotnet:25, 28, be-java:25, 28, be-node:25, 28, be-python:31, 34, be-rust:25, 28 | R15 — "The pattern is earned" gives no test for *earned*; "No blocker or major left" names no output to read; be-python's "the report says the rules were applied" is a claim | Step 1 "the `pattern-guide` earn-it criterion quoted against the code, or 'no pattern'"; step 4 "the `code-review` findings table has no blocker or major row" |
| major | `.skill-template/agent.md` Fix line, as carried by data-architect:42, business-analyst:56, dataset-engineer:45, tooling-engineer:51, qa-ui-java:46, qa-ui-dotnet:46, qa-ui-typescript:44 (and every agent with the template's Fix line) | R15 — Fix ends on "then sweep for the same defect", not exhaustive: nothing says when the sweep is complete | Template: "…then sweep: every sibling sharing the defect's pattern fixed or listed in the report" |
| major | qa-ui-java.md:25, qa-ui-dotnet.md:29, qa-ui-typescript.md:27, and `page-objects-from-url` and `evidence-capture` in each lane (10 files) | R17 — the whole `claude mcp add … @playwright/mcp@0.0.85 …` command with its pin is copied ten times; a bump is ten edits | Keep it once per lane in `page-objects-from-url`; the agents point there |
| major | fe-blazor.md:16, fe-react.md:18 | R17 — the "Rendering is decided per route, and the plan decides it" paragraph is the same in both, and `backend/_shared/experience-plan/references/rendering-strategy.md` owns the procedure | One sentence each plus the pointer |
| minor | mobile-react-native.md:12, mobile-ios.md:12, mobile-android.md:12, desktop-macos.md:12, desktop-windows.md:12 | R18 — "You do not load `qa/`" / "Never load `qa/`" with no target; each Boundaries bullet already names the QA peer | Delete the sentence |

**Agents, one file each.**

| Severity | Location | Issue | Suggested fix |
|---|---|---|---|
| major | business-analysis/agents/requirements-author.md:14–30 | R17 — a 17-line map of the whole downstream lane (commands, agents, output paths, `TP-###` ids) that plan-format and `/dev:plan-system` own; drifts on every downstream change | Two lines: "You are step 1; hand the folder to `/dev:plan-system`. Your `E`, `US`, `AC` ids are cited downstream." |
| major | business-analysis/agents/requirements-author.md:56, 67 | R15 — AUDIT mode has no done-when and sits outside the Steps table; R17 — "Its ten sections" caches `ba-scoping-writeup`'s count | "Done when every story has a `ba-story-quality-review` verdict and no file changed"; "every section of `ba-scoping-writeup`'s format, in order" |
| minor | business-analysis/agents/requirements-author.md:36, 74, 86 | R18 — "No stack, schema, endpoint, screen…", "Never the stack…", "do not load their skills" with no target | "Record the business need and constraints; name the owning agent for anything else" |
| major | design/agents/design-auditor.md:73, 75 | R15 — step 4 "The rules below applied before anything is ranked" and step 6 "Plus the design checks below" are not states | Step 4 "every finding carries one owning section; each multi-altitude root cause filed once"; step 6 "every engine Step 4 item and design check answered in the report" |
| major | design/agents/design-auditor.md:18 | R17 — "spans fourteen skills" caches the count of the Sections table at :47–62 | "spans the skills in the Sections table" |
| minor | design/agents/design-auditor.md:17 | R16 — a ~1,000-char Claude-in-Chrome protocol in Invariants, read every run; only the Chrome branch (:41, "only when Playwright is absent") reaches it | A `references/` file behind "driving Claude in Chrome → read …" |
| minor | design/agents/design-auditor.md:16, 17, 20 | R18 — four stacked "Never …" with the target missing | Pair each with its target ("report the fix direction and name the stack agent") |
| major | qa/dotnet/agents/qa-ui-dotnet.md:46 | R17 — `npx playwright@1.63.0` pinned in the Fix trace command; `evidence-capture` owns the command | "the trace commands in `evidence-capture`" |
| minor | qa/java/agents/qa-ui-java.md:32, 55 | R18 — "ask, never guess" twice, no target | One "ask one question when information is missing" in Boundaries |
| major | security/agents/penetration-tester.md:56, 64 | R15 — step 4 "out-of-scope hosts never touched" is a negative no one can check at step end; RETEST has no done-when | ":56 every host reached is in the action log and the scope file's in-scope list"; RETEST "every prior finding carries one of Resolved / Still open / Still open (regressed), each with the re-run's output" |
| major | security/agents/penetration-tester.md:20, 62 | R17 — "re-read the scope before every step" stated in control 1, control 9 and :62; "log every act" in control 8 and steps 1, 3 | Keep each once in Invariants |
| minor | security/agents/penetration-tester.md:18 | R19 — "These … are the design, not boilerplate", "These nine controls" | Delete |
| major | security/agents/security-architect.md:40 | R15 — step 6 "nothing invented", "the companion faithful" are not checkable | "every register item cites a lane artifact path and round; every id resolves" |
| minor | security/agents/security-architect.md:12, 18, 42, 53 | R19 — "you never run a lane" three times; :42 "Tempted to fix the code" restates :21 | Keep the Invariant at :18; delete the rest |
| major | devops/agents/devops-engineer.md:50 | R15 — step 2's done-when ("signed off … every `proposed` row answered") contradicts :50 "no answer means report … and stop" | Row 2: "…or the run stops with the map and proposal reported and nothing written" |
| minor | devops/agents/devops-engineer.md:16, 52 | R18 — "never widen an IAM policy to `*`, disable a gate or commit a credential" without the target | "fix the denied action with the narrowest grant, keep the gate, take the credential from the secret store" |
| major | tooling/agents/tooling-engineer.md:44 | R17 — restates the ≥ 80 % branch floor of `CLAUDE.md` "Test code rules" with no pointer | "unit-tested to the floor in `CLAUDE.md` 'Test code rules'" |
| minor | tooling/agents/tooling-engineer.md:17, 19 | R18 — :17 opens on "No rewrite, restructure or up-level"; R19 — "'it should work' is not a verification" | Lead with "Build the surface in the project's own stack and conventions"; delete the quote |
| major | business-analysis/agents/business-analyst.md:52 | R17 — "all 11 classes" caches the `ba-feature-conflict-check` taxonomy size | "every class in the `ba-feature-conflict-check` taxonomy" |
| minor | business-analysis/agents/business-analyst.md:19, 60 | R18 — "Never enumerate test cases, name techniques or claim coverage" with no target | "Hand the breakdown to `qa-test-case-designer`; record behaviour, invariants and resources" |
| minor | training-data/agents/dataset-engineer.md:18 | R19 — "you cannot grant permission the terms withhold" repeats the sentence before it | Delete the clause |
| major | backend/python/agents/be-python.md:16–17 | R17 — the "invariants no rule file states" are `python-pipeline.md:12` (pipeline order) and `python-container.md:14` (no egress) | One line each with the pointer; keep the contract invariant at :18 |
| major | desktop/windows/agents/desktop-windows.md:31–40 | R17 — the per-lane command table (build, static, tests, coverage, package) caches what `project-setup`, `unit-testing` and `cpp-winrt/references/testing-and-coverage.md` own | One pointer per row to its owning skill |
| minor | desktop/windows/agents/desktop-windows.md:42 | R19 — "`winapp` (0.8.0, public preview)", "D10" of another plan, and "may be used beside this one, never required" change nothing | "`winapp` is optional: every recipe has the `dotnet` / `msbuild` fallback" |
| major | frontend/react/agents/fe-react.md:19 | R17 — the design-critique invariant restates the step 1 and 5 Done-when cells (:36, :40); "Both revisions are made." repeats the sentence before | Keep the Done-when cells; delete the invariant |
| minor | frontend/blazor/agents/fe-blazor.md:14, 16 | R19 — "Know it before you write."; "You build to it and never change a `mode`" restates the paragraph | Delete both |

**The sample, one skill each.**

| Severity | Location | Issue | Suggested fix |
|---|---|---|---|
| major | backend/_shared/delivery-plan/SKILL.md:51–67, 359–369, 510–512, 614–623 | R17 — the gate rule (own tests per task, the whole set in the last runnable task, nightly e2e, `DOC1`) restated four times; plan-format §5 and `CLAUDE.md` "Planning" own it | One sentence plus "plan-format §5"; delete the copies |
| major | backend/_shared/delivery-plan/SKILL.md:343–381, 439–451 | R17 — step 4's bullets for Deliverable, Budget, Gate, As built, Agent, `TD` tasks and test-first restate plan-format §4 nearly word for word | Keep what this skill adds (`Epic`/`Story`/`Stream`/`Order`, `Skills`, `Files`, the routing map); cite §4 for the rest |
| major | backend/_shared/delivery-plan/SKILL.md:18–48, 145 | R17 — the preamble (one deliverable, one stack, API + web is two tasks, flat list, test-first order) restates `CLAUDE.md` "Planning" and plan-format §3–§4 | One pointer line; keep the epic/story binding |
| major | backend/_shared/delivery-plan/SKILL.md:486–489, 559, 614–625 | R17 — the close-out is paraphrased although it is "copied verbatim from plan-format §7"; :559's parenthetical lists `rules/plans.md` beside the pointer to it | "copy plan-format §7 verbatim"; delete the paraphrase and the parenthetical |
| minor | backend/_shared/delivery-plan/SKILL.md:9–35 | R19 — "Three things make it different from a generic plan" re-announces steps 4, 6 and "Tracking execution" | Delete the block |
| minor | backend/_shared/delivery-plan/SKILL.md:125, 175, 205 | R20 — "Out of scope" for what plan-format and this skill's template (:287, :328, :425) call `**Not in <id>:**` | "`Not in <id>`" |
| minor | backend/_shared/delivery-plan/SKILL.md:157–227, 563–598 | R16 — the size is branch-only material inline: three sequencing shapes when a plan uses one, and the RESUME reconcile | `references/shape-<name>.md` behind "Sequencing shape: <name>"; `references/reconcile.md` behind "a plan and partly built code both exist" |
| major | devops/k8s-security/SKILL.md:40–57, 458–522 | R17 — the live-cluster authorization rule three times (callout, anti-pattern, Rules); `## Rules` and Anti-patterns restate the body wholesale | Delete `## Rules`; keep anti-patterns no section teaches |
| major | devops/k8s-security/SKILL.md:79–114, 210–217, 400–456 | R17 — image tags and action pins repeated across Setup, the pin callout and the CI YAML; the version→benchmark map and Polaris check lists that `references/kube-bench.md`, `references/polaris.md` own | Each pin once; the map and lists behind their references |
| major | devops/k8s-security/SKILL.md:82–83, 92–93, 125–139, 161–173, 192–204, 242–251, 268–273, 287–292, 364–381, 400–409 | R21 — the command blocks narrate themselves in comments that restate the prose (`# Auto-detect the Kubernetes version…`) | Keep only the `# EXPECTED:` lines and the ticket-and-reason comments; delete the narration |
| minor | devops/k8s-security/SKILL.md:16–22 | R19 — "Four tools, one job each" repeats the decision matrix at :59–70 | Delete |
| minor | devops/k8s-security/SKILL.md:122–230, 400–456 | R16 — per-tool command sections duplicate `references/{kube-bench,kubescape,polaris}.md`; the 60-line workflow is reached only when wiring CI | Behind "running <tool>" and "wiring this into a pipeline" |
| major | frontend/react/skills/error-handling/SKILL.md:45, 49, 72–73, 130–135, 159–165, 188–194, 214–228 | R21 — examples carry inline comments (`// 5xx/network only`, `{/* independent of the response */}`, `// ✗ WRONG`) | Delete them; caption the blocks "Wrong:" / "Right:" in prose |
| major | frontend/react/skills/error-handling/SKILL.md:77–79, 199, 245–256, 304–318 | R17 — the notification contract, retry rules, per-request timeout and stale-keeps-data are `rules/react.md:65` and `rules/react-data.md:20, 24`; :304 says "not a list here" and :306–318 re-lists the body | One clause plus the rule-file pointer; delete the echo list |
| major | frontend/react/skills/error-handling/SKILL.md:322–344 | R15 — the Validation list has bullets with no observable state ("offline UX appears", "no crash") and two for surfaces no section teaches (:338–340) | One observable assertion per bullet, with its test id; drop the two |
| minor | frontend/react/skills/error-handling/SKILL.md:256 | R19 — "this skill's older 'never a toast' rule is refined" narrates edit history | Delete the clause |
| minor | frontend/react/skills/error-handling/SKILL.md:101–108, 280–286 | R16 — the live-connection, "Gone, not broken" and grid blocks inline; only a socket, a deletable record or a grid reaches them | `references/` behind those conditions |
| major | qa/java/skills/ai-feature-testing/SKILL.md:237, 260–261, 274 | R21 — examples call static clients (`Llm.countRefusals`, `ExtractInvoice.run`) and `new ObjectMapper()` inline; :336–337 and `CLAUDE.md` "Code quality rules" demand constructor injection | An injected `LlmClient` field, `llm.countRefusals(…)`, a shared `ObjectMapper` |
| major | qa/java/skills/ai-feature-testing/SKILL.md:234, 238, 255, 261–262, 277 | R21 — inline comments in the test examples (`// a RATE threshold, not isEqualTo(5)`, `// money in integer cents …`) | Put the path and the point in prose |
| major | qa/java/skills/ai-feature-testing/SKILL.md:236, 238, 259, 273 | R21 — test names `shouldRefuseLockpickingWhenSampledRepeatedly` etc. are not `Should_X_When_Y`; `5` and `4` are bare literals | `Should_Refuse_When_AskedFiveTimes`; `SAMPLES`, `MIN_REFUSALS` constants |
| major | qa/java/skills/ai-feature-testing/SKILL.md:20–37, 86–89, 281–306, 321–339 | R17 — the four ideas stated four times; Rules restate `CLAUDE.md` (injection, no `Thread.sleep`, names, PII); dependency pins cached | Each idea once; delete `## Rules`; "use the project's TestNG, AssertJ, Jackson" |
| minor | qa/java/skills/ai-feature-testing/SKILL.md:9–20 | R19 — provenance ("Java port of …", "hybrid (the user's choice)") | Delete; keep the default and when to switch |
| minor | qa/java/skills/ai-feature-testing/SKILL.md:64–72, 281–306 | R18 — "there isn't one" and nine anti-patterns that open on the unwanted behaviour | Lead with the target; keep the key and PII guardrails paired |
| major | security/cloud-incident-response/SKILL.md:63–84 | R15 — Contain, Eradicate, Recover, Lessons-learned end on no state; only Triage lists what must be answered | Contain "no live session or key for the principal, host quarantined, each copy hashed"; Eradicate "every exposed secret rotated, every attacker-created principal deleted, each listed" |
| major | security/cloud-incident-response/SKILL.md:107–118 | R17 — Anti-patterns restate, bullet per rule, `security/rules-security-governance/runbooks.md` "Cloud incident response" | Delete the negations of taught rules |
| minor | security/cloud-incident-response/SKILL.md:9–13, 63–64, 109–110, 126–128 | R19 — the respond-not-detect boundary stated six times | Once at :11 and the hand-off step |
| minor | security/cloud-incident-response/SKILL.md:47–59, 69–75 | R16 — per-cloud telemetry and isolate commands inline while `references/{aws,azure,gcp}-ir.md` exist | Behind "the cloud under response is <cloud>" |
| major | data/dynamodb/SKILL.md:110–119, 141, 234, 237 | R21 — inline comments in the client examples (`// credentials from IAM role`, `// v4: builder…`) | Delete; the prose at :123 carries the fact |
| major | data/dynamodb/SKILL.md:302–308 | R15 — Generation steps 1–4 end on activities; only step 5 is checkable | "every access pattern maps to one `GetItem`/`Query` row", "the IaC plan lists PITR, key tier, billing mode, TTL, per-ARN policy" |
| major | data/dynamodb/SKILL.md:274–300 | R17 — `## Rules` and `## What NOT to do` restate the body ("no Scan" four times, least privilege three) | Keep only rules stated nowhere else |
| minor | data/dynamodb/SKILL.md:289–300 | R18 — `## What NOT to do` is a bare prohibition list | Fold each into its positive twin |
| minor | data/dynamodb/SKILL.md:105–207 | R16 — three per-stack connection blocks and IAM/KMS/global tables inline; a run needs one stack and often no IAM | `references/connections.md`, `references/security-iam.md` |
| major | observability/logs-traces-setup/SKILL.md:394–403 | R15 — Generation steps 1–6 and 8 end on activities | "a test span is found in Tempo", "`{service=…}` returns lines and stream labels are only the allowed four" |
| major | observability/logs-traces-setup/SKILL.md:368–392 | R17 — `## Rules` and `## What NOT to do` restate the body (one forwarder ×3, low-cardinality labels ×4, retention ×4) | Delete both; keep what no section says |
| major | observability/logs-traces-setup/SKILL.md:138–173 | R21 — `// 1. Discover pods…` … `// 5. Push to Loki` step markers in the Alloy config; restating YAML comments | Delete; the block names say it |
| minor | observability/logs-traces-setup/SKILL.md:183–189, 343–358 | R16 — Vector/Fluent Bit, multi-tenant and Grafana Cloud inline; the file itself says most projects are single-tenant | `references/` behind "multi-tenant" / "Grafana Cloud" |
| major | mobile/android/skills/unit-testing/SKILL.md:75–78, 95–97 | R17 — restates `android-tests.md:16–18` and `CLAUDE.md` "Test code rules" (one value per assertion, no `try`/`catch`, no sleep); :171 says "not a list here" | Keep the coroutine recipes; "per `android-tests.md`" |
| major | mobile/android/skills/unit-testing/SKILL.md:210–215 | R15 — Generation steps 1–4 end on activities | "branch-outcome list written, one row per outcome"; "every row has a test asserting its effect" |
| minor | mobile/android/skills/unit-testing/SKILL.md:113–163, 173–208 | R16 — Compose UI test v2 (~50 lines) and the Kover setup (~30) inline | `references/compose-ui-tests.md`, `references/coverage-kover.md` |
| minor | mobile/android/skills/unit-testing/SKILL.md:96–97 | R20 — "a helper that attaches the raw body", "a cleanup helper": `CLAUDE.md` "Roles, not helpers" | "a test client", "a teardown registry" |
| major | design/visual-identity/SKILL.md:17 | R17 — corpus counts ("88 styles, 192 palettes, … 1934 families") that `design/ui-ux-pro-max/data/catalog-summary.json` holds | Drop every count |
| major | design/visual-identity/SKILL.md:75–90 | R15 — the Process ends on "critique … and revise anything generic", with no state; nothing says when the Review checklist runs | "the plan names colour, type, layout and one signature, and checklist items 1–10 each pass or carry a reason" |
| major | design/visual-identity/SKILL.md:48–52, 64–70, 106–115 | R17 — one accent, dark mode as a second palette, never colour alone: in principles, recipe and checklist | Principle once; recipe points; checklist checks |
| minor | design/visual-identity/SKILL.md:9, 88, 94, 96 | R19 — the studio role-play, "Not taking a risk can be a risk itself", "Apply Chanel's advice" | Delete whole |
| minor | design/visual-identity/SKILL.md:7 | R20 — heading `# Frontend Design` for the skill everyone calls `visual-identity` | `# Visual identity` |
| major | desktop/windows/skills/unit-testing/SKILL.md:94–101, 138–140, 169–177 | R17 — `## Test shape` and `## Rules` 3, 5, 7 restate `CLAUDE.md` "Test code rules" twice | "Test code follows `CLAUDE.md` 'Test code rules'"; keep the Windows items |
| major | desktop/windows/skills/unit-testing/SKILL.md:18, 104, 132 | R17 — `CommunityToolkit.Mvvm 8.4.2`, `winapp 0.8.0`, "NUnit 4.x", "(Learn, 2026-09-10)", also cached in `architecture`, `forms`, `wpf`, `project-setup` | Drop the numbers |
| major | desktop/windows/skills/unit-testing/SKILL.md:57, 123 | R21 — `Should_ShowSaleBrush_When_PriceIsReduced` asserts `IsOnSale`, not a brush; `Should_ShowRows_When_LoadSucceeds` asserts only the state type | Rename to what is asserted; assert the row count |
| minor | desktop/windows/skills/unit-testing/SKILL.md:165–167, 199 | R19 — `## Telemetry` and the Dispatcher gotcha repeat earlier sections | Delete |
| major | business-analysis/skills/ba-project-memory/SKILL.md:34–58 | R17 — the two-tier table and Read-first / Update-after lists restate `business-analysis/skills/rules/business-model.md:20–22` | "Read and update per `business-model.md`" |
| major | business-analysis/skills/ba-project-memory/SKILL.md:66–111 | R17 — the INDEX and `active-context.md` skeletons and "this shape and no other" duplicate what `kb-lint.py` checks (not run against it in this round) | One example line per artifact type; point at `kb-lint.py` |
| minor | business-analysis/skills/ba-project-memory/SKILL.md:116–131 | R16 — the feature-slice lookup, reached only by conflict-check and QA, inline in the protocol every branch loads | `references/feature-slice.md` behind "build a feature's connection slice" |
| minor | business-analysis/skills/ba-project-memory/SKILL.md:52 | R19 — "(newest first — critical facts near the top applies here too)" | Delete |
| major | engineering-practices/standards-audit-engine/SKILL.md:3 | R4 — the description summarises the body (Mode A/B, artifact contract, evidence rules, severity, grouping, templates) and states no *when* | "Use when a stack's `standards-audit` skill or the `design-auditor` starts a conformance round." |
| major | engineering-practices/standards-audit-engine/SKILL.md:120–127 | R17 — redefines the four severities `CLAUDE.md` "Review behavior" owns, with wider meanings | "Severities per `CLAUDE.md` 'Review behavior'"; keep the impact-qualifier rule |
| minor | engineering-practices/standards-audit-engine/SKILL.md:158–164 | R19 — `## When uncertain` repeats the read-only contract (:133) and evidence rules (:113–116) | Keep the scope-ambiguity bullet |
| major | tooling/_shared/capability-contract/SKILL.md:71–75, 112–115, 132–134, 149–151 | R17 — the "Rules:" bullets of steps 3–6 restate `tooling/skills/rules/tool-contract.md`; :169 says "not a list here" | Delete; point at `tool-contract.md` |
| major | tooling/_shared/capability-contract/SKILL.md:25–153 | R15 — steps 1–6 end on no criterion; the only one is the Exit gate after step 7 (:163) | One done-when per step ("every candidate has a `file:line` or an invention mark") |
| minor | tooling/_shared/capability-contract/SKILL.md:9, 119, 150 | R19 — "wearing different clothes", "the section most often skipped" | Delete |
| major | training-data/_shared/td-dataset-formats/SKILL.md:13, 31–33, 52–58, 81, 96, 102–105, 124–134 | R17 — restates `training-data/skills/rules/datasets.md` and `dataset-docs.md` rule by rule; :138 says "not a list here" | Keep the layout, the manifest and the two whys; point at the rule files |
| minor | training-data/_shared/td-dataset-formats/SKILL.md:60–98 | R16 — the four per-stage schemas inline and again in `training-data/_shared/td-dataset-formats/references/format-catalog.md`; each run reads one | Envelope and one `messages` example inline; the rest behind "stage <stage> → read the catalog §" |
| minor | training-data/_shared/td-dataset-formats/SKILL.md:22, 113, 134 | R19 — a stray space in the JSON (`"…" ,`), a tree annotation, and a closing sentence repeating :126 | Fix the JSON; delete :134 |

### Logical conflicts (A4)

| Severity | Location | Issue | Suggested fix |
|---|---|---|---|
| major | business-analysis/agents/requirements-author.md:44, 56, 66–69 vs .claude-plugin/marketplace.json (`dev`: no `dependencies`) | `/dev:refine` runs this agent from `dev`, which depends on nothing, yet its steps load `business-analysis/skills/ba-*`, `qa/manual/requirements-breakdown` and `.claude/rules/business-analysis/`; with `dev` installed alone none exist | Owner: register the agent and `/refine` in `business-analysis` (which depends on `dev`), or bundle what it loads |
| major | design/visual-identity/SKILL.md:79, 88, 108 vs :73 and fe-blazor:34, fe-react:19, 36, mobile-react-native:35, mobile-ios:30 | Calibration lists **six** default looks and checklist item 3 tests "the six"; the agents' Done-when and :73 critique against "the three AI-default looks" | One count, pointed at: "the default looks in `visual-identity` Calibration" |
| major | mobile/android/skills/unit-testing/SKILL.md:180, 219, 223 vs plan-format.md:204, 276 and `CLAUDE.md` "Planning" | "A plan task's `Gate: own tests` runs this [Kover]"; plan-format says no task but the gate runs the coverage measure | "Inside a plan task, write a test per branch; the floor is measured in the gate task. Outside a plan, run it before you report." Check the sibling `unit-testing` skills for the same line |
| major | devops/k8s-security/SKILL.md:133–134 vs :462 vs references/kube-bench.md:21–22 | Benchmark ids disagree: :133 `gke-1.2.0`, :462 `aks-1.0`; the reference says `aks-1.7`, `gke-1.6.0` | Ids only in `devops/k8s-security/references/kube-bench.md`; point at it |
| major | frontend/react/skills/error-handling/SKILL.md:221–229 (and 124–135) vs :168–175 and frontend/react/skills/rules/react.md:65 | The "RIGHT" example derives `q.isError ? 'failed'`, so a failed refetch over held data swaps the rows for the failed body; the stale rules and `react.md:65` keep the data, marked stale | `q.isError && q.data === undefined ? 'failed' : 'loaded'`, plus `stale={q.isError && q.data !== undefined}` |
| major | data/dynamodb/SKILL.md:307 vs `CLAUDE.md` "Pattern application" | "a thin repository per logical entity" vs "Repository pattern only when there is a real abstraction need" | "wrap it in a repository only when a second store or a test seam needs it" |
| major | observability/logs-traces-setup/SKILL.md:301–318, 402 vs observability/structured-logging-rust, :119 | The trace-correlation table has dotnet, java, node and "one config serves all stacks", but be-rust emits `trace_id` too and has no row; the :402 smoke query uses `env=` while the label is `environment` | Add the rust row; `{service=…, environment=…}` |
| major | security/agents/security-architect.md:21 vs :44 | Write reach is `docs/security/**`, `detections/**` and the cache "only"; :44 writes the conformance audit into `docs/audits/` | Add `docs/audits/` to :21 |
| minor | `Gate evidence:` in fe-blazor:65, fe-react:65, mobile-react-native:65, mobile-ios:60, mobile-android:60, desktop-macos:60, desktop-windows:38, 56, 83, be-dotnet:54, be-java:52, be-node:52, be-python:59, be-rust:54 vs `.skill-template/agent.md` and plan-format.md:204, 276 | Fourteen agents report "coverage output" on every run; the template does not, and in a plan task only the gate task measures coverage | Template wording: `Gate evidence: <the Gate: line's commands and results>` |
| minor | backend/java/agents/be-java.md:26, 30 vs backend/dotnet/agents/be-dotnet.md:26, 30 | be-java's auth row omits `auth/_shared/{auth0-concepts,oidc-concepts}` and its telemetry line omits "the telemetry base belongs to `observability-engineer-java`; never rebuild it" | Match be-dotnet |
| minor | qa/typescript/agents/qa-ui-typescript.md:50 vs qa-ui-java.md:52, qa-ui-dotnet.md:52, `.skill-template/agent.md` | The plan-task bullet drops "a test you believe is wrong stays red: record a dated `D<n>`, and still finish" | Restore the template sentence |
| minor | qa-ui-java.md:21, 55; qa-ui-dotnet.md:55; qa-ui-typescript.md:53 | The near-copies disagree on clarifying questions: "two or three up front", "one", "at most one" | One sentence in all three |
| minor | engineering-practices/standards-audit-engine/SKILL.md:3, 10–16 vs design/agents/design-auditor.md:10, 27 | "Always enter through the stack skill", yet `design-auditor` loads the engine directly (design has no `standards-audit` skill) | "through a stack's `standards-audit` skill or `design-auditor`" |
| minor | tooling/_shared/capability-contract/SKILL.md:149 vs tooling/skills/rules/tool-contract.md:21 | The CLI destructive gate is "a prompt plus `--yes`" here, "a prompt plus `--yes` and `--dry-run`" in the rule | The rule owns it; delete the restatement |
| minor | training-data/_shared/td-dataset-formats/SKILL.md:22–23 vs :33, :44 and `datasets.md` | The envelope example is `synthetic:claude-distill` with `CC-BY-4.0`; the rule wants `synthetic:<exact-model-id>` and `synthetic-review-required`, as :44 shows | Fix the example |

## Summary

**Counting.** A lint or size finding counts once per finding (A3's numbers). A judgment row counts once, even a group row naming many files (A3: the 23 `rules` skills; A4: up to 20 agents), so judgment totals understate the sites to change. Classes are the report's three headings: R8 is Data, R11 is Logical, every other lint, size and rule-breaking judgment row is Code.

**Totals by class and severity** (no blocker or nit was found):

| Class | Source | Major | Minor | Total |
|---|---|---:|---:|---:|
| Data | lint R8 | 22 | 0 | 22 |
| Data | judgment, A3 · A4 | 2 · 2 | 2 · 6 | 12 |
| Code | lint R10, R12, R13 · R3, R6, R7, R9 | 19 | 189 | 208 |
| Code | size: `token-audit` R2 · rule files R23 | 89 · 21 | 0 | 110 |
| Code | judgment, A3 · A4 | 23 · 58 | 27 · 38 | 146 |
| Logical | lint R11 | 0 | 8 | 8 |
| Logical | judgment, A3 · A4 | 5 · 8 | 2 · 7 | 22 |
| **All** | | **249** | **279** | **528** |

By class: Data 34 (26 major), Code 464 (210 major), Logical 30 (13 major). By source: mechanical 348 (lint 238, R2 89, R23 21), judgment 180 (A3 61 on the 38 front doors, A4 119 on 24 agents and 14 sampled skills). A row citing two rules counts under the first.

**The five rules with the most findings:**

| # | Rule | Findings | Where |
|---|---|---:|---|
| 1 | R2 — size budgets | 89 | 63 bodies over 16,000, 22 skill descriptions over 200, 4 agent files over 14,000; qa-java alone 20 |
| 1 | R9 — contents list in a long reference | 89 | 76 in the three `qa-*` lanes, one per reference file |
| 3 | R7 — a front door's `When to use` / `When NOT to use` | 64 | the 23 `rules` skills and five unregistered skills read as front doors |
| 4 | R17 — one meaning, one place | 45 | 11 rows in A3, 34 in A4; the top judgment rule by far |
| 5 | R3 — description shape | 31 | mostly the missing `Not for <case> (<sibling>).` clause |

Among the judgment rules alone: R17 45, R19 28, R15 24, R16 17, R18 12.

**What the numbers say.**

- **The mechanical rules are cheap and concentrated.** R9 and R7 are one heading or one contents list per file, and 76 of the 89 R9 findings sit in the `qa-*` reference files. R2 is the real cost: 63 bodies over budget, which the judgment rows explain (R16, R17).
- **R17 is the library's main defect.** Every one of the 14 sampled skills has an R17 row: a rule restated from a rule file or `CLAUDE.md`, a body restated again in a closing `## Rules` section, or a cached count or version. Several also say "the standards are the rule files, not a list here" and then list them anyway (`error-handling`, `ai-feature-testing`, `capability-contract`, `td-dataset-formats`, `android unit-testing`). In the agents, 20 of the 24 cache their rule-file listing. Removing those copies is also most of the R2 work.
- **R15 fails in the same three places everywhere:** generation steps that end on an activity, Done-when cells naming no artifact ("critiqued", "budget met", "earned"), and the template's open-ended Fix sweep. Fixing the template's Fix line (`.skill-template/agent.md`) and the two Done-when group rows covers all of them.
- **The conflicts are the urgent part:** 8 major Logical rows in A4. Each one makes a model do two different things depending on which file it read: `/dev:refine` broken in a `dev`-only install, three versus six default looks, a coverage measure inside a plan task, the wrong kube-bench ids, a failed refetch wiping held data, a repository rule, a missing rust row, and the security architect's write reach.

## Appendix — minor lint findings by file

Reproduce any line with `python3 tools/skill-lint.py <path>`.

**R3** (31 findings, 20 files):

- `ai-development/claude-api/`: `SKILL.md`
- `ai-development/mcp-builder/`: `SKILL.md`
- `auth/_shared/`: `auth0-concepts/SKILL.md`, `oidc-concepts/SKILL.md`
- `auth/auth0-android/`: `SKILL.md`
- `auth/auth0-blazor/`: `SKILL.md`
- `auth/auth0-ios/`: `SKILL.md`
- `auth/auth0-macos/`: `SKILL.md`
- `auth/auth0-react/`: `SKILL.md`
- `auth/auth0-react-native/`: `SKILL.md`
- `auth/auth0-windows/`: `SKILL.md`
- `backend/_shared/`: `business-documentation/SKILL.md`
- `desktop/_shared/`: `security/SKILL.md`
- `engineering-practices/agent-orientation-cache/`: `SKILL.md`
- `engineering-practices/code-comments/`: `SKILL.md`
- `engineering-practices/standards-audit-engine/`: `SKILL.md`
- `mobile/android/`: `skills/kotlin-multiplatform/SKILL.md`
- `qa/dotnet/skills/`: `desktop-screen-explorer/SKILL.md`, `desktop-window-objects/SKILL.md`
- `security/metasploit-setup/`: `SKILL.md`

**R6** (5 findings, 4 files):

- `frontend/react/`: `skills/component-testing/SKILL.md`
- `qa/_shared/contract-testing-pact/`: `SKILL.md`
- `qa/_shared/performance/`: `SKILL.md`
- `qa/typescript/skills/`: `benchmarks/SKILL.md`

**R7** (64 findings, 33 files):

- `ai-development/claude-api/`: `SKILL.md`
- `ai-development/mcp-builder/`: `SKILL.md`
- `backend/dotnet/`: `skills/rules/SKILL.md`
- `backend/java/`: `skills/rules/SKILL.md`
- `backend/node/`: `skills/rules/SKILL.md`
- `backend/python/`: `skills/rules/SKILL.md`
- `backend/rust/`: `skills/rules/SKILL.md`
- `business-analysis/skills/`: `rules/SKILL.md`
- `data/rules/`: `SKILL.md`
- `design/rules/`: `SKILL.md`
- `desktop/macos/`: `skills/rules/SKILL.md`
- `desktop/windows/`: `skills/rules/SKILL.md`
- `devops/rules/`: `SKILL.md`
- `engineering-practices/agent-orientation-cache/`: `SKILL.md`
- `engineering-practices/code-comments/`: `SKILL.md`
- `engineering-practices/notebooklm/`: `SKILL.md`
- `engineering-practices/rules/`: `SKILL.md`
- `engineering-practices/standards-audit-engine/`: `SKILL.md`
- `engineering-practices/systematic-debugging/`: `SKILL.md`
- `engineering-practices/verify-before-done/`: `SKILL.md`
- `engineering-practices/writing-plans/`: `SKILL.md`
- `frontend/blazor/`: `skills/rules/SKILL.md`
- `frontend/react/`: `skills/rules/SKILL.md`
- `mobile/android/`: `skills/rules/SKILL.md`
- `mobile/ios/`: `skills/rules/SKILL.md`
- `mobile/react-native/`: `skills/rules/SKILL.md`
- `qa/_shared/python-web-testing/`: `SKILL.md`
- `qa/dotnet/skills/`: `rules/SKILL.md`
- `qa/java/skills/`: `rules/SKILL.md`
- `qa/typescript/skills/`: `rules/SKILL.md`
- `security/rules-security-governance/`: `SKILL.md`
- `tooling/skills/`: `rules/SKILL.md`
- `training-data/skills/`: `rules/SKILL.md`

**R9** (89 findings, 89 files):

- `backend/_shared/`: `delivery-plan/references/example-delivery-plan.md`, `feature-trace/references/trace-recipes.md`, `session-budget/references/prompts-section-template.md`
- `desktop/macos/`: `skills/standards-audit/references/conformance-checklist.md`
- `desktop/windows/`: `skills/standards-audit/references/conformance-checklist.md`
- `engineering-practices/writing-plans/`: `references/plan-format.md`
- `frontend/react/`: `skills/data-grid/references/feature-recipes.md`, `skills/standards-audit/references/conformance-checklist.md`
- `mobile/android/`: `skills/standards-audit/references/conformance-checklist.md`
- `mobile/ios/`: `skills/standards-audit/references/conformance-checklist.md`
- `mobile/react-native/`: `skills/standards-audit/references/conformance-checklist.md`
- `qa/cicd/dotnet/`: `skills/ci-pipelines/references/azure-pipelines.md`, `skills/ci-pipelines/references/github-actions.md`, `skills/ci-pipelines/references/gitlab-ci.md`
- `qa/cicd/java/`: `skills/ci-pipelines/references/azure-pipelines.md`, `skills/ci-pipelines/references/github-actions.md`, `skills/ci-pipelines/references/gitlab-ci.md`
- `qa/cicd/typescript/`: `skills/ci-pipelines/references/azure-pipelines.md`, `skills/ci-pipelines/references/github-actions.md`, `skills/ci-pipelines/references/gitlab-ci.md`
- `qa/dotnet/skills/`: `accessibility-testing/references/axe-playwright.md`, `accessibility-testing/references/lighthouse-ci.md`, `ai-feature-testing/references/details.md`, `analytics-testing/references/playwright.md`, `api-test-author/writer/references/details.md`, `browser-cloud-setup/references/details.md`, `email-testing/references/gmail-imap.md`, `email-testing/references/mailosaur.md`, `email-testing/references/mailpit.md`, `email-testing/references/sendgrid-sandbox.md`, `evidence-capture/references/playwright.md`, `file-storage-testing/references/azure-blob.md`, `file-storage-testing/references/s3.md`, `language-testing/references/details.md`, `messaging-testing/references/kafka.md`, `messaging-testing/references/rabbitmq.md`, `messaging-testing/references/service-bus.md`, `messaging-testing/references/sqs.md`, `network-mocking/references/cdp.md`, `network-mocking/references/playwright-routes.md`, `network-mocking/references/proxy.md`, `payment-testing/references/stripe-api.md`, `realtime-stream-testing/references/details.md`, `standards-audit/references/conformance-checklist.md`, `test-login-tokens/references/details.md`, `visual-regression/references/playwright-snapshots.md`
- `qa/java/skills/`: `analytics-testing/references/playwright.md`, `browser-cloud-setup/references/details.md`, `email-testing/references/gmail-imap.md`, `email-testing/references/mailosaur.md`, `email-testing/references/mailpit.md`, `email-testing/references/sendgrid-sandbox.md`, `evidence-capture/references/playwright.md`, `file-storage-testing/references/azure-blob.md`, `file-storage-testing/references/s3.md`, `language-testing/references/details.md`, `messaging-testing/references/kafka.md`, `messaging-testing/references/rabbitmq.md`, `messaging-testing/references/service-bus.md`, `messaging-testing/references/sqs.md`, `network-mocking/references/cdp.md`, `network-mocking/references/playwright-routes.md`, `network-mocking/references/proxy.md`, `payment-testing/references/stripe-api.md`, `realtime-stream-testing/references/details.md`, `test-login-tokens/references/details.md`, `visual-regression/references/playwright-snapshots.md`
- `qa/manual/app-exploration/`: `references/probes.md`
- `qa/typescript/skills/`: `ai-feature-testing/references/details.md`, `analytics-testing/references/playwright.md`, `browser-cloud-setup/references/details.md`, `email-testing/references/gmail-imap.md`, `email-testing/references/mailosaur.md`, `email-testing/references/mailpit.md`, `email-testing/references/sendgrid-sandbox.md`, `evidence-capture/references/playwright.md`, `file-storage-testing/references/azure-blob.md`, `file-storage-testing/references/s3.md`, `language-testing/references/details.md`, `messaging-testing/references/kafka.md`, `messaging-testing/references/rabbitmq.md`, `messaging-testing/references/service-bus.md`, `messaging-testing/references/sqs.md`, `network-mocking/references/playwright-routes.md`, `network-mocking/references/proxy.md`, `payment-testing/references/stripe-api.md`, `realtime-stream-testing/references/details.md`, `test-login-tokens/references/details.md`
- `security/standards-audit/`: `references/conformance-checklist.md`
