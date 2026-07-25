---
name: qa-dotnet-conformance-audit
description: Use to audit a whole .NET test suite against the qa-dotnet plugin's conventions — NUnit structure, waits, page objects, locators, API layering, DB verification, secrets, Allure, CI wiring — producing a saved, re-runnable findings report in `docs/audits/`. Read-only; it never fixes. Triggers "audit our test suite against the conventions", "re-audit — what did we fix since last round". Not for one test file (a `reviewer` skill) or fixing anything (the `qa-*-dotnet` agents).
---

# qa-dotnet Conformance Audit

Audit an existing **.NET test suite** against the conventions this plugin defines — the global Test-code rules in `CLAUDE.md` plus the hard rules each `qa/dotnet/skills/*`, `qa/reporting/dotnet/*`, and `qa/cicd/*` skill owns — and produce **one saved report**: every finding evidenced at `file:line`, severity-tabled, mapped to the skill that owns the fix.

**Read-only analysis on test code.** The audit points; the `qa-*-dotnet` agents fix.

**Announce at start:** "I'm using the `qa-dotnet-conformance-audit` skill in Mode A (baseline) / Mode B (re-audit) on `<repo/path>`."

## THE SCOPE FENCE — this audits the test suite, not the application

Every finding must be about **test code**: the suite's own structure, layering, waits, data, assertions, reporting, and CI wiring. The application under test is owned by `be-dotnet` / `fe-blazor` / `fe-react` and their conformance audits.

- A brittle locator is a **suite** finding (section F) — even when the root cause is a missing `data-testid`. Report the suite's locator strategy, and hand the missing-testid list to the `fe-*` peer via `missing-testids.md`.
- A failing test that reveals an application bug is **not** a conformance finding — it's a bug report (`qa/manual/bug-report-writer`).
- Application design smells you notice while reading tests get **named in the handoff section**, never scored as findings here.

If the user actually wants the app audited, say so and name the right skill instead of quietly widening scope.

## Read before sweeping

1. **[`ep-conformance-audit`](../../../../engineering-practices/conformance-audit/SKILL.md)** — the engine: Mode A/B rounds, the artifact contract, evidence rules, severity semantics, grouping/coverage policy, the 5 phases, the hostile self-review. **Read it first.**
2. [`references/conformance-checklist.md`](references/conformance-checklist.md) — the 14 lettered sections (A–N) and every check. **Read end-to-end** before Phase 2.
3. `engineering-practices/conformance-audit/references/report-template.md` — the Round-1 / Round-N skeletons. Read before Phase 3.

Load the **owning skill** (named per section in the checklist) whenever a check is ambiguous, tool-keyed, or you are about to write its fix direction. When checklist and skill disagree, **the skill wins** — and report the disagreement.

Report path: `docs/audits/<YY-MM-DD-HHmm>-qa-dotnet-conformance-r<N>.md`.

## The fence — what this is not

| Job | Owner |
|---|---|
| Review one test file / one diff, inline severity table | [`api-test-author/reviewer`](../api-test-author/reviewer/SKILL.md) · [`ui-test-author/reviewer`](../ui-test-author/reviewer/SKILL.md) · [`bdd-reviewer`](../bdd-reviewer/SKILL.md) — this skill **rolls their checklists up to suite scale** |
| Audit the **application** the suite tests | **peers** `be-dotnet-conformance-audit` · `fe-blazor`/`fe-react` conformance audits |
| Test-case design coverage from requirements | **peer** `qa-manual-test-designer` (+ `qa/manual/test-basis-analyzer`) — section N reports *suite shape*, not requirement coverage |
| Filing a defect the suite exposed | `qa/manual/bug-report-writer` |
| Running a security scan | **peer** `qa-security` — section K inventories secret hygiene in test code only |
| Code vs a written spec, or a feature trace | `ep-spec-compliance-audit` / `ep-feature-audit` / the `code-auditor` agent |
| Applying any fix found here | the matching `qa-api-dotnet` / `qa-ui-dotnet` / `qa-mobile-dotnet` / `qa-reporting-dotnet` / `qa-cicd-dotnet` agent |

## Phase 0 — the suite lane *(never skip)*

```bash
ls *.sln **/*Tests.csproj **/*.Tests.csproj 2>/dev/null
rg -n "PackageReference" --glob '*Tests.csproj' --glob '*.props'    # runner + tooling
rg -n "TargetFramework|Nullable" --glob '*Tests.csproj' --glob '*.props'
ls .github/workflows azure-pipelines.yml .gitlab-ci.yml 2>/dev/null
ls allureConfig.json **/allureConfig.json categories.json 2>/dev/null
rg -n "LevelOfParallelism|Parallelizable" --glob '*.cs'
git log --oneline -5
```

Record: **runner** (NUnit primary / xUnit / MSTest) · **TFM + `Nullable`** · **UI driver** (Playwright .NET / Selenium 4 / Appium 2 / none) · **API stack** (RestSharp / Playwright `APIRequestContext` / HttpClient) · **assertion library** (`Assert.That` house rule vs FluentAssertions) · **BDD** (Reqnroll present?) · **Testcontainers / DB access?** · **Allure wired?** · **CI host** · **parallelism settings** · **perf tool** (NBomber?).

**The lane gates every finding.** Do not flag a suite for lacking a tool it doesn't use (no Playwright → the Playwright rows are N/A, not violations), and judge assertion/DI style against the **project's** stated convention where one exists (a documented FluentAssertions house style is a deviation to note, not a finding). A suite on xUnit is not "wrong" for lacking NUnit attributes — map the rule to the runner in use and say so.

Then read 2–3 representative files (a test fixture, a page object or API client, a builder) to calibrate conventions.

## Phase 1 — applicability

| Section | Applies when | Probe |
|---|---|---|
| E, F (page objects, locators) | A UI or mobile suite exists | `rg -l "Playwright\|Selenium\|Appium" --glob '*.csproj'` |
| H (API layering) | An API suite exists | `rg -l "RestSharp\|HttpClient\|APIRequestContext" --glob '*.cs'` |
| J (external verification) | The suite touches a DB / broker / storage / mail | `rg -l "Npgsql\|SqlConnection\|Testcontainers\|Dapper\|Kafka\|ServiceBus" --glob '*.csproj'` |
| L (reporting & flake) | Allure is wired — **absent is finding L1**, not N/A | `rg -l "Allure" --glob '*.csproj'` |
| M (CI wiring) | A pipeline definition exists — **absent is finding M1** | `ls .github/workflows azure-pipelines.yml .gitlab-ci.yml` |
| N-mutation row | Stryker.NET configured (dotnet has the tool; TS does not) | `ls stryker-config.json`; `rg -l "dotnet-stryker" .` |

A–D, G, I, K apply to every .NET test suite. Sections that are N/A must name the probe that decided it.

## Handoffs

- **Apply the fixes** → the owning agent per section: `qa-api-dotnet` (H, I) · `qa-ui-dotnet` / `qa-mobile-dotnet` (E, F, D) · `qa-reporting-dotnet` (L) · `qa-cicd-dotnet` (M) · the relevant authoring agent for A–C, G, J, K, N. The priority table is the handoff artifact.
- **One file / one diff instead** → the family reviewer skills named in the fence table.
- **Missing `data-testid`s the suite works around (section F)** → `missing-testids.md` to the `fe-blazor` / `fe-react` peer.
- **Requirement-coverage gaps** (not suite-shape gaps) → **peer** `qa-manual-test-designer`.
- **Application findings noticed in passing** → name them in the handoff block and point at `be-dotnet-conformance-audit` / the `fe-*` audit; never score them here.
- **Security gates for the app** → **peer** `qa-security`.
