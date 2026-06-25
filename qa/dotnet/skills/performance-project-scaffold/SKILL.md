---
name: qa-performance-project-scaffold-dotnet
description: Use when starting a load/performance test project from zero in C# / .NET 8 — solution layout, exact package versions, local setup, and run commands for a standalone NBomber console suite. Triggers: "scaffold a performance test project", "set up an NBomber suite from scratch", "what versions for a C# load test framework", "create the solution structure for load tests". Composable: explains how to fold in api/ui/mobile dotnet modules later.
---

# Performance Test Project Scaffold (C# / .NET 8)

This skill stands up a **complete, runnable load-test solution from zero**: directory layout, exact tool/library versions, local setup, and the commands to create and run it. It is **standalone** and **composable** — one project in a flat solution sharing a `TestCore` library with the api / ui / mobile modules (see *Expanding into a multi-module solution*).

NBomber runs as a **console application**, not an NUnit test project — it has its own runner, scenario model, and HTML/CSV report output. In the flat solution it sits alongside the test projects but simply **does not reference NUnit / `Microsoft.NET.Test.Sdk`** (CPM lists those versions, but only the test projects reference them). Scenario design, thresholds, and the perf-suite review checklist are owned by the `qa-performance-dotnet` skills + `qa/_shared/performance` — this skill owns the **project shell**.

## When to use

- A fresh repo with no .NET load-test project, and the user wants performance coverage.
- The user asks which versions / structure / setup an NBomber framework should use.

## When NOT to use

- The solution already exists → author scenarios into it with the `qa-performance-dotnet` skills.
- API / UI / mobile scaffolding → use the matching `*-project-scaffold-dotnet` skill.
- Functional API/UI tests → those are NUnit projects, not this console-app shape.

## Tooling & versions

Versions are pinned **once** in `Directory.Packages.props` (CPM); csprojs reference packages **without** a `Version` attribute.

| Concern | Package / tool | Version | Notes |
|---|---|---|---|
| SDK | .NET SDK | **8.0 (LTS)** | `global.json`, C# 12. |
| Project type | console app | — | `dotnet new console`, **not** `nunit`. NBomber owns the runner. |
| Load engine | `NBomber` | **6.0.0** | Scenario/step model + HTML/CSV/markdown reports. |
| HTTP plugin | `NBomber.Http` | **6.0.0** | Must match the NBomber major (v6). |
| HTTP client | `RestSharp` *(opt)* | **112.1.0** | Or `HttpClient`; reuse the API module's typed clients when composing (below). |
| Data plugin | `NBomber.Data` *(opt)* | **6.0.0** | Feed CSV/JSON datasets into steps. |
| Reporting | NBomber built-in + `Allure` *(opt)* | **2.12.1** | NBomber emits its own report; Allure attachment owned by `qa-reporting-dotnet`. |

NBomber's HTML report is self-contained — you do not need the Allure CLI to read results, unlike the functional modules.

## Prerequisites & local setup

```bash
dotnet --version
# The target environment must be reachable and SAFE to load-test (a dedicated perf/staging env
# — never production without sign-off). Auth: a pre-fetched token or M2M client creds (auth0-test-tokens).
```

Performance has the lightest local toolchain (no browsers, no emulators) but the strictest **environment** discipline: confirm the target tolerates load and thresholds reflect a real SLA before running.

## Project layout (standalone)

```
<Product>/                              # git repo root = solution root (flat projects)
├── <Product>.sln
├── global.json                         ┐
├── Directory.Build.props               │ solution-scoped, shared by every project
├── Directory.Packages.props            │ (CPM version table)
├── nuget.config · .editorconfig        ┘
├── .gitignore
├── TestCore/                           # ← shared library (composition seam)
│   ├── Configuration/
│   ├── Http/                           # client/auth factory (shared with the API module)
│   ├── GlobalUsings.cs
│   └── TestCore.csproj
└── PerfTests/                          # CONSOLE app, not nunit — no test-host packages
    ├── Scenarios/                      # one file per scenario (OrdersAverage, etc.)
    ├── Datasets/                       # CSV/JSON feeders (NBomber.Data)
    ├── Thresholds/                     # SLA assertions / report-failure rules
    ├── Program.cs                      # NBomberRunner.RegisterScenarios(...).Run()
    ├── appsettings.json                # ┐ per-project config — base URL, virtual users,
    ├── appsettings.staging.json        # │ duration, SLA; independently dockerizable
    ├── Dockerfile                      # │
    ├── GlobalUsings.cs                 # │
    ├── README.md                       # ┘
    └── PerfTests.csproj                # references TestCore (no NUnit / Microsoft.NET.Test.Sdk)
```

## Create from zero

```bash
mkdir <Product> && cd <Product>
git init
dotnet new globaljson --sdk-version 8.0.100 --roll-forward latestFeature
dotnet new sln -n <Product>

dotnet new classlib -o TestCore  -f net8.0
dotnet new console  -o PerfTests -f net8.0
dotnet sln add TestCore PerfTests
dotnet add PerfTests reference TestCore

# Create Directory.Packages.props (CPM on) FIRST, then add packages versionlessly:
dotnet add PerfTests package NBomber
dotnet add PerfTests package NBomber.Http

dotnet build        # exit gate: 0 errors, 0 warnings
dotnet run --project PerfTests          # runs scenarios, writes ./reports
```

`Directory.Packages.props` (CPM version table) + `Directory.Build.props` (settings only) are as in `qa-api-project-scaffold-dotnet`. **Key difference:** `PerfTests.csproj` references **only** NBomber packages — never `NUnit` / `Microsoft.NET.Test.Sdk`, even though CPM may list their versions for sibling test projects. `Program.cs` entry point shape (scenario bodies owned by `performance/nbomber`):

```csharp
NBomberRunner
    .RegisterScenarios(OrdersAverageLoad.Build())
    .WithReportFolder("reports")
    .WithReportFormats(ReportFormat.Html, ReportFormat.Csv)
    .Run();
```

## Run

```bash
dotnet run --project PerfTests
ASPNETCORE_ENVIRONMENT=staging dotnet run --project PerfTests
# HTML report lands in PerfTests/reports/ — open index.html
```

CI gates on the run's threshold result (NBomber returns a failed status when an SLA assertion fails) — owned by `qa-cicd-dotnet` (perf gate) and `qa/_shared/performance`.

## Conventions (the shell only)

- **Console app, one scenario per file** under `Scenarios/`; `Program.cs` only registers and runs.
- **Thresholds are explicit and SLA-derived** (p95/p99 latency, error rate) — a run with no failing threshold is not a passing perf test, it's an unasserted one.
- **Config-driven load**: virtual users, ramp, duration, base URL from per-project `appsettings.<env>.json` — never hard-coded in scenarios.
- **Reuse, don't reimplement, the API client**: when composing with the API module, point scenarios at `TestCore`'s typed clients instead of raw `HttpClient`.

Scenario shapes, injection profiles, threshold tuning, and the review checklist are owned by `qa-performance-dotnet` (`performance/nbomber`) and `qa/_shared/performance`. Defer to them.

## Expanding into a multi-module solution

Flat solution + shared `TestCore` + CPM make this purely additive. The most common pairing is **performance + api** (reuse the typed clients to drive load):

1. Install `qa-api-dotnet` and run its scaffold **inside this repo**, skipping `global.json`, `Directory.Build.props`, `Directory.Packages.props`, `.config`, the `.sln`, and `TestCore` (already present).
2. Add the API test project (`dotnet new nunit -o ApiTests`, `dotnet sln add ApiTests`, `dotnet add ApiTests reference TestCore`) and its packages. The API project references NUnit/test-host; **`PerfTests` still must not** — that separation is per-project, so there is nothing to scope or merge.
3. Promote the typed clients + auth/config into `TestCore`; both the perf scenarios and the API tests consume them.
4. `dotnet run --project PerfTests` runs load; `dotnet test` runs the functional suites. Add `.slnf` filters per discipline. UI (`PlaywrightTests`) and mobile (`AppiumTests`) fold in the same way (each its own NUnit project with its own config).

## Setup checklist

- [ ] `global.json` pins SDK 8.0; `Directory.Packages.props` (CPM) is the only version source; csprojs versionless
- [ ] `Directory.Build.props` carries settings only
- [ ] `TestCore` is a shared library; `PerfTests` references it
- [ ] `PerfTests` is a **console app** and references **no** NUnit / `Microsoft.NET.Test.Sdk` packages
- [ ] Target environment confirmed safe to load-test; auth token/creds sourced from config
- [ ] Every scenario has an explicit, SLA-derived threshold
- [ ] Load profile (VUs, ramp, duration, URL) read from per-project `appsettings.<env>.json`
- [ ] `dotnet build` clean; `dotnet run` produces an HTML report under `reports/`
