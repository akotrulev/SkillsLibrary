---
name: qa-dotnet-standards-audit
description: Use when auditing a .NET test suite against the qa-dotnet plugin's conventions, producing a saved, re-runnable findings report in `docs/audits/`. Scopeable to the whole suite or to just one discipline. Read-only; it never fixes. Triggers "audit our test suite against the conventions", "re-audit — what did we fix since last round", "audit just our API tests". Not for one test file (a `reviewer` skill) or fixing anything (the `qa-*-dotnet` agents).
---

# qa-dotnet Conformance Audit

Audit an existing **.NET test suite** against the conventions this plugin defines — the global Test-code rules in `CLAUDE.md` plus the hard rules each `qa/dotnet/skills/*`, `qa/reporting/dotnet/*`, and `qa/cicd/*` skill owns — and produce **one saved report**: every finding evidenced at `file:line`, severity-tabled, mapped to the skill that owns the fix.

**Read-only analysis on test code.** The audit points; the `qa-*-dotnet` agents fix.

State the mode — Mode A (baseline) or Mode B (re-audit) — the `<repo/path>` and the scope (api | ui | mobile | all) in the first line of output, so the reader knows which comparison the report makes.

## The scope fence — this audits the test suite, not the application

Every finding must be about **test code**: the suite's own structure, layering, waits, data, assertions, reporting, and CI wiring. The application under test is owned by `be-dotnet` / `fe-blazor` / `fe-react` and their conformance audits.

- A brittle locator is a **suite** finding (section F) — even when the root cause is a missing `data-testid`. Report the suite's locator strategy, and hand the missing-testid list to the `fe-*` peer via `missing-testids.md`.
- A failing test that reveals an application bug is **not** a conformance finding — it's a bug report (`qa/manual/bug-report-writer`).
- Application design smells you notice while reading tests get **named in the handoff section**, never scored as findings here.

If the user actually wants the app audited, say so and name the right skill instead of quietly widening scope.

## Discipline scope — whole suite, or just API / UI / mobile

By default this audits the **whole suite**. The user may narrow it to one automation discipline instead — useful when a repo owns multiple suites (e.g. an API project and a Playwright project) and only one changed:

| Scope | Sections in play | Sections skipped | Tagged rows skipped |
|---|---|---|---|
| `api` | A, B, C, G, H, I, J\*, K, L, M, N | E, F | A9, A10, D3, D5, D6, D9, D10, I3, I11–I13, K9, M16 **[PW]** · D4 **[Sel]** · D12 **[Appium]** |
| `ui` | A, B, C, E, F, G, I, J\*, K, L, M, N | H | D12 **[Appium]** · E14 **[Appium]** — keep every **[PW/Sel]** row |
| `mobile` | A, B, C, E, F, G, I, J\*, K, L, M, N | H | A9, A10, D3, D5, D6, D9, D10, E16, E17, F2, I3, I11–I13, K9, M16 **[PW]** · D4, E13, F7 **[Sel]** — keep D12 **[Appium]**, E14 **[Appium]** |
| `all` (default) | every section the Step-1 probes find applicable | — | — |

\* **J is discipline-independent** — it stays gated by its own probe (does the suite touch a DB/broker/storage/mail), in every scope. An API, UI, or mobile suite can all do external verification.

A, B, C, G, I, K, L, M, N (minus the tagged rows above) are **universal** — every scope runs them, because suite hygiene, secrets, reporting, and CI wiring aren't discipline-specific.

**State the resolved scope** in the start announcement and as the first line of the report's **§2 Scope & coverage** (`**Discipline scope:** api | ui | mobile | all`), ahead of the `In scope: <dirs>` line. If the task doesn't say, ask: *"Audit the whole suite, or just API / UI / mobile automation?"*

**Round comparability:** a scope-limited round is not comparable section-for-section to a whole-suite round. If the scope changed since the prior round, say so explicitly in the Round-N delta (§1 Movement / lane changes), and never report a section as "regressed" or "resolved" when it simply wasn't in this round's scope — it's **untouched**, not closed.

## Read before sweeping

1. **[`ep-standards-audit-engine`](../../../../engineering-practices/standards-audit-engine/SKILL.md)** — the engine: Mode A/B rounds, the artifact contract, evidence rules, severity semantics, grouping/coverage policy, the 5 steps, the hostile self-review. **Read it first.**
2. [`references/conformance-checklist.md`](references/conformance-checklist.md) — the 14 lettered sections (A–N) and every check. **Read end-to-end** before Step 2.
3. `engineering-practices/standards-audit-engine/references/report-template.md` — the Round-1 / Round-N skeletons. Read before Step 3.

Load the **owning skill** (named per section in the checklist) whenever a check is ambiguous, tool-keyed, or you are about to write its fix direction. When checklist and skill disagree, **the skill wins** — and report the disagreement.

Report path: `docs/audits/<NNN>-qa-dotnet-conformance-r<N>.md`.

## The fence — what this is not

| Job | Owner |
|---|---|
| Review one test file / one diff, inline severity table | [`api-test-author/review`](../api-test-author/review/SKILL.md) (+ [`api-test-author/playwright`](../api-test-author/playwright/SKILL.md) § Review) · [`ui-test-author/review`](../ui-test-author/review/SKILL.md) · [`bdd-reviewer`](../bdd-reviewer/SKILL.md) — this skill **rolls their checklists up to suite scale** |
| Audit the **application** the suite tests | **peers** `be-dotnet-standards-audit` · `fe-blazor`/`fe-react` conformance audits |
| Test-case design coverage from requirements | **peer** `qa-test-case-designer` (+ `qa/manual/requirements-breakdown`) — section N reports *suite shape*, not requirement coverage |
| Filing a defect the suite exposed | `qa/manual/bug-report-writer` |
| Running a security scan | **peer** `qa-security` — section K inventories secret hygiene in test code only |
| Code vs a written spec, or a feature trace | `ep-spec-vs-code-audit` / `ep-feature-audit` / the `code-auditor` agent |
| Applying any fix found here | the matching `qa-api-dotnet` / `qa-ui-dotnet` / `qa-mobile-dotnet` / `qa-reporting-dotnet` / `qa-cicd-dotnet` agent |

## Step 0 — the suite lane *(never skip)*

```bash
ls *.sln **/*Tests.csproj **/*.Tests.csproj 2>/dev/null
rg -n "PackageReference" --glob '*Tests.csproj' --glob '*.props'    # runner + tooling
rg -n "TargetFramework|Nullable" --glob '*Tests.csproj' --glob '*.props'
ls .github/workflows azure-pipelines.yml .gitlab-ci.yml 2>/dev/null
ls allureConfig.json **/allureConfig.json categories.json 2>/dev/null
rg -n "LevelOfParallelism|Parallelizable" --glob '*.cs'
git log --oneline -5
```

Record: **runner** (NUnit primary / xUnit / MSTest) · **TFM + `Nullable`** · **UI driver** (Playwright .NET and its version / Selenium 4 / Appium / none) · **API stack** (RestSharp / Playwright `APIRequestContext` / HttpClient) · **assertion library** (`Assert.That` house rule vs FluentAssertions) · **BDD** (Reqnroll present?) · **Testcontainers / DB access?** · **Allure wired?** · **CI host** · **parallelism settings** · **perf tool** (NBomber?).

**The lane gates every finding.** Do not flag a suite for lacking a tool it doesn't use (no Playwright → the Playwright rows are N/A, not violations), and judge assertion/DI style against the **project's** stated convention where one exists (a documented FluentAssertions house style is a deviation to note, not a finding). A suite on xUnit is not "wrong" for lacking NUnit attributes — map the rule to the runner in use and say so.

Then read 2–3 representative files (a test fixture, a page object or API client, a builder) to calibrate conventions.

## Step 1 — applicability

Two filters stack: the **tool-presence probes** below (a section is N/A when its tool isn't in the repo at all), and the **discipline scope** from the section above (a section is *skipped by user choice*, not N/A, when it's outside the requested `api`/`ui`/`mobile` scope). Record which reason applied — "N/A: no Appium" and "Skipped: scope=api" are different things and the applicability matrix must say which.

| Section | Applies when | Probe |
|---|---|---|
| E, F (page objects, locators) | A UI or mobile suite exists, **and** scope is `ui`, `mobile`, or `all` | `rg -l "Playwright\|Selenium\|Appium" --glob '*.csproj'` |
| H (API layering) | An API suite exists, **and** scope is `api` or `all` | `rg -l "RestSharp\|HttpClient\|APIRequestContext" --glob '*.cs'` |
| J (external verification) | The suite touches a DB / broker / storage / mail — independent of scope | `rg -l "Npgsql\|SqlConnection\|Testcontainers\|Dapper\|Kafka\|ServiceBus" --glob '*.csproj'` |
| L (reporting & flake) | Allure is wired — **absent is finding L1**, not N/A | `rg -l "Allure" --glob '*.csproj'` |
| M (CI wiring) | A pipeline definition exists — **absent is finding M1** | `ls .github/workflows azure-pipelines.yml .gitlab-ci.yml` |
| N-mutation row | Stryker.NET configured (dotnet has the tool; TS does not) | `ls stryker-config.json`; `rg -l "dotnet-stryker" .` |

A–D, G, I, K apply to every .NET test suite. Sections that are N/A must name the probe that decided it.

## Handoffs

- **Apply the fixes** → the owning agent per section: `qa-api-dotnet` (H, I) · `qa-ui-dotnet` / `qa-mobile-dotnet` (E, F, D) · `qa-reporting-dotnet` (L) · `qa-cicd-dotnet` (M) · the relevant authoring agent for A–C, G, J, K, N. The priority table is the handoff artifact.
- **One file / one diff instead** → the family reviewer skills named in the fence table.
- **Missing `data-testid`s the suite works around (section F)** → `missing-testids.md` to the `fe-blazor` / `fe-react` peer.
- **Requirement-coverage gaps** (not suite-shape gaps) → **peer** `qa-test-case-designer`.
- **Application findings noticed in passing** → name them in the handoff block and point at `be-dotnet-standards-audit` / the `fe-*` audit; never score them here.
- **Security gates for the app** → **peer** `qa-security`.
