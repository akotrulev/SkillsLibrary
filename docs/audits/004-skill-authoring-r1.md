# 004 — Skill-authoring audit, round 1 (2026-11-20)

**Standard:** `engineering-practices/writing-for-agents/SKILL.md`, rules R1–R23.
**Plan:** `docs/plans/014-authoring-standard-domain-language-feature-prototype.md`, §8, D7, D16, tasks A3 (this part) and A4 (agents, the sample, the summary).
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

