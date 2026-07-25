---
name: be-dotnet-conformance-audit
description: Use to audit a whole .NET service against the be-dotnet plugin's conventions — pattern application, DI lifetimes, async, layering, EF Core persistence, API contract, JWT/RBAC auth, resilience, config/secrets, OTel + Serilog observability — producing a saved, re-runnable findings report in `docs/audits/`. Read-only; it never fixes. Triggers: "audit our .NET service against the plugin conventions", "does this API follow our backend rules", "conformance audit of this C# codebase", "give me a findings .md for our service", "re-audit — what did we fix since last round". Do NOT use to review one file or diff (`be-dotnet-reviewer`), to check code against a product spec (`ep-spec-compliance-audit` / `code-auditor`), to trace one feature (`ep-feature-audit`), to audit a test suite (`qa-dotnet-conformance-audit`), or to fix anything (the `be-dotnet` agent).
---

# be-dotnet Conformance Audit

Audit an existing **.NET service** against the conventions this plugin defines — the global + backend code rules in `CLAUDE.md` plus the hard rules each `backend/dotnet/skills/*` skill owns, and the two observability invariants the bundled `observability/*` skills own — and produce **one saved report**: every finding evidenced at `file:line`, severity-tabled, mapped to the skill that owns the fix.

**Read-only analysis on product code.** The audit points; the `be-dotnet` agent fixes.

**Announce at start:** "I'm using the `be-dotnet-conformance-audit` skill in Mode A (baseline) / Mode B (re-audit) on `<repo/path>`."

## Read before sweeping

1. **[`ep-conformance-audit`](../../../../engineering-practices/conformance-audit/SKILL.md)** — the engine: Mode A/B rounds, the artifact contract, evidence rules, severity semantics, grouping/coverage policy, the 5 phases, the hostile self-review. **Read it first.**
2. [`references/conformance-checklist.md`](references/conformance-checklist.md) — the 14 lettered sections (A–N) and every check. **Read end-to-end** before Phase 2.
3. `engineering-practices/conformance-audit/references/report-template.md` — the Round-1 / Round-N skeletons. Read before Phase 3.

Load the **owning skill** (named per section in the checklist) whenever a check is ambiguous, version-keyed, or you are about to write its fix direction. When checklist and skill disagree, **the skill wins** — and report the disagreement.

Report path: `docs/audits/<YY-MM-DD-HHmm>-be-dotnet-conformance-r<N>.md`.

## The fence — what this is not

| Job | Owner |
|---|---|
| Review one file / one diff, inline severity table, no artifact | [`reviewer`](../reviewer/SKILL.md) — this skill **reuses its checklists at repo scale** |
| Code vs a written spec / stories / ACs | `ep-spec-compliance-audit` (or the `code-auditor` agent) |
| "How does feature X actually work / where is it defective" | `ep-feature-audit` |
| Auditing the **test suite** that covers this service | **peer** `qa-dotnet-conformance-audit` — this skill audits production code only |
| Attacking authz / injection (proving exploitability) | **peer** `qa-security` — section I inventories the gates; it does not attack them |
| Schema / DDL / index design, cross-engine migration strategy | **peer** `data-architect` — section G covers EF Core mechanics only |
| Applying any fix found here | the `be-dotnet` agent (Mode FIX / EXTEND) |

## Phase 0 — the .NET version lane *(never skip)*

```bash
ls *.sln **/*.csproj 2>/dev/null
cat Directory.Build.props Directory.Packages.props 2>/dev/null   # TFM + central package management
grep -rh "TargetFramework\|LangVersion\|Nullable\|TreatWarningsAsErrors" --include=*.csproj --include=*.props .
grep -rh "Microsoft.EntityFrameworkCore\|Npgsql\|SqlServer\|Serilog\|OpenTelemetry\|MediatR\|FluentValidation\|Polly" --include=*.csproj --include=*.props .
ls global.json 2>/dev/null; dotnet --version 2>/dev/null   # SDK pin
git log --oneline -5
```

Record: **TFM** (net8.0 / net9.0 / net10.0, or a mix across projects) · **`Nullable`** enable/disable per project · **EF Core major** (must match the TFM major) · **DB provider** · **project topology** (layered / vertical-slice / single project) · **web framework** (controllers vs minimal APIs) · **logging stack** (Serilog / MEL) · **OTel present?** · **auth SDK** (Auth0 / Cognito / other / none) · **MediatR / FluentValidation / Polly present?**

**The version rule binds every finding.** .NET 10 is primary, 8/9 supported. Never flag a net8 project for lacking a net9/net10 API (e.g. `Activity.AddException` is net9+ — the portable `RecordException` is correct everywhere; primary constructors are net8+). A **mixed-TFM solution** is itself finding A2, not a licence to audit every project against the highest TFM present.

Then read 2–3 representative files (a controller/endpoint, a service, the `DbContext` + one configuration) to calibrate conventions.

## Phase 1 — applicability

| Section | Applies when | Probe |
|---|---|---|
| G (persistence) | EF Core is referenced | `grep -rl EntityFrameworkCore --include=*.csproj .` |
| I (service-side auth) | An auth SDK / JWT bearer wiring exists | `grep -rl "AddJwtBearer\|AddAuthentication" --include=*.cs .` |
| L (observability) | Serilog and/or OpenTelemetry referenced — **absent is finding L1**, not N/A | `grep -rl "Serilog\|OpenTelemetry" --include=*.csproj .` |
| H (API contract) | The service exposes HTTP | `grep -rl "MapControllers\|MapGet\|ApiController" --include=*.cs .` |
| B-CQRS rows | MediatR referenced | `grep -rl MediatR --include=*.csproj .` |

A–F, J, K, M, N apply to every .NET service. Sections that are N/A must name the probe that decided it.

## Handoffs

- **Apply the fixes** → the `be-dotnet` agent, Mode FIX (a defect) or EXTEND (a missing capability). The priority table is the handoff artifact.
- **One file / one diff instead** → [`reviewer`](../reviewer/SKILL.md); cross-stack/architecture altitude → `backend/_shared/reviewer`.
- **Missing contract tests (section M)** → **peer** `qa-api-dotnet` writes them; this audit only reports their absence.
- **Security-flavoured findings (I2–I6, K1)** → **peer** `qa-security` owns proving exploitability.
- **Schema/index/migration strategy beyond EF mechanics (section G)** → **peer** `data-architect`.
- **Observability gaps (section L)** → the `observability-engineer-dotnet` sibling agent in this plugin.
- **Code vs a spec, or a feature trace** → `ep-spec-compliance-audit` / `ep-feature-audit` / the `code-auditor` agent.
