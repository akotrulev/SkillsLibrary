---
name: qa-api-project-scaffold-dotnet
description: Use when starting an API test-automation project from zero in C# / .NET 10 (8-9 supported) — solution layout, exact package versions, local setup, and run commands for a standalone RestSharp + NUnit suite. Triggers: "scaffold an API test project", "set up a .NET API test suite from scratch", "what versions for a C# API test framework", "create the solution structure for API tests". Composable: explains how to fold in ui/mobile/performance dotnet modules later.
---

# API Test Project Scaffold (C# / .NET 10)

This skill stands up a **complete, runnable API test solution from zero**: directory layout, the exact tool and library versions, the local-machine setup, and the commands to create and run it. It is **standalone** — the project it produces runs on its own — and **composable**: it is one project in a flat solution, sharing a `TestCore` class library with the UI / mobile / performance modules. Adding a sibling is purely additive (see *Expanding into a multi-module solution*).

**Version rule:** new projects target **net10.0** (the library primary). net8 (LTS, supported to Nov 2026) and net9 (STS) are supported fallbacks — target them **only** to match an existing solution's `TargetFramework`; never up-level a down-level repo. When adding this suite into an existing solution, adopt that solution's TFM. Substitute your chosen TFM for `net10.0` everywhere below.

The structure follows the established dotnet layout: **flat projects at the solution root** (no `src/`/`tests/` nesting), **per-project config** so each suite is independently configurable/dockerizable, a shared **`TestCore`**, and **Central Package Management (CPM)** so versions are pinned once. Authoring conventions (DTOs, typed clients, test bodies, builders, deep verification) live in the `qa-api-dotnet` skills — this skill owns the **project shell**.

## When to use

- A fresh repo with no .NET test solution yet, and the user wants API coverage.
- The user asks which versions / structure / setup a C# API test framework should use.
- You are about to author API tests and there is no solution to put them in.

## When NOT to use

- The solution already exists → author into it with the `qa-api-dotnet` skills, don't re-scaffold.
- UI / mobile / performance scaffolding → use the matching `*-project-scaffold-dotnet` skill.

## Tooling & versions

Versions are pinned **once** in `Directory.Packages.props` (CPM) — each `.csproj` references packages **without** a `Version` attribute. Do not put `<PackageReference Version=…>` in project files (that triggers `NU1008` under CPM).

| Concern | Package / tool | Version | Notes |
|---|---|---|---|
| SDK | .NET SDK | **10.0 (LTS)** | Pin in `global.json` (`rollForward: latestFeature`). C# 14. On a down-level repo pin 8.0/9.0 to match. |
| Test runner | `NUnit` | **4.3.2** | NUnit 4 — classic asserts live in `NUnit.Framework.Legacy`; use `Assert.That`. |
| Test adapter | `NUnit3TestAdapter` | **5.0.0** | Required for `dotnet test` discovery. |
| Test host | `Microsoft.NET.Test.Sdk` | **17.14.1** | |
| HTTP client | `RestSharp` | **112.1.0** | Post-v107 async-first fluent API (`RestClient` + `RestRequest`); no legacy `IRestResponse`. |
| Assertions | `FluentAssertions` | **6.12.1** | **Deliberately pinned to 6.12.x** — the last pre-commercial-license line (v8 requires a paid license for commercial use). Do **not** bump to 7.x/8.x without a license review. |
| JSON | `System.Text.Json` | **matches TFM** | Ships in the shared framework — reference explicitly only if a transitive pin is needed (`10.0.0` on net10, `8.0.5` on net8). Default serializer; no Newtonsoft unless a spec forces it. |
| Reporting | `Allure.NUnit` | **2.12.1** | Wiring owned by `qa-reporting-dotnet`; this scaffold only leaves the per-project `allureConfig.json` hook. |
| Allure CLI | `allure` tool | **local tool** | `dotnet tool install allure` in `.config/dotnet-tools.json`. |

Optional, add only when the spec demands it: `Testcontainers.PostgreSql` 4.1.0 (real-DB verification), `PactNet` (contracts), gRPC (`Grpc.Net.Client` 2.66.0), GraphQL.

## Prerequisites & local setup

```bash
dotnet --version            # expect 10.0.x (or the repo's pinned 8.0.x / 9.0.x)
docker --version            # only if you add Testcontainers-backed DB verification
# Allure CLI installed as a repo-local tool in the create steps; or: brew install allure
```

No browsers or device emulators are needed for an API suite — the cheapest module to stand up.

## Project layout (standalone)

```
<Product>/                              # git repo root = solution root (flat projects)
├── <Product>.sln
├── global.json                         # pins SDK 10.0         ┐
├── Directory.Build.props               # net10.0, nullable,    │ solution-scoped,
│                                       #   langversion, analyzers │ shared by every project
├── Directory.Packages.props            # CPM: every <PackageVersion> (the version table) │
├── nuget.config                        # single package source │
├── .editorconfig                       #                        │
├── .config/dotnet-tools.json           # allure local tool      ┘
├── .gitignore
├── TestCore/                           # ← shared library (composition seam)
│   ├── Configuration/                  # env config binding, TestSettings
│   ├── Http/                           # RestClient factory, auth/log handlers
│   ├── Reporting/                      # Allure step/attachment helpers
│   ├── Builders/                       # builder / ObjectMother base
│   ├── GlobalUsings.cs
│   └── TestCore.csproj                 # PackageReferences WITHOUT Version (CPM)
└── ApiTests/                           # this discipline's project
    ├── Clients/                        # one typed client per service
    ├── Models/                         # request/response DTOs (records)
    ├── TestData/                       # per-domain builders / fixtures
    ├── Helpers/
    ├── Tests/                          # grouped by service / feature
    ├── Tools/                          # one-off scripts / spec downloaders
    ├── Config/
    ├── allureConfig.json               # ┐ per-project config — keeps the
    ├── appsettings.json                # │ suite independently configurable
    ├── appsettings.test.json           # │ and dockerizable
    ├── Dockerfile                      # │ (CI shards this suite on its own)
    ├── GlobalUsings.cs                 # │
    ├── README.md                       # ┘ run instructions for this suite
    └── ApiTests.csproj                 # references TestCore
```

Why flat + per-project config: each test project owns its `appsettings`, `allureConfig`, and `Dockerfile`, so it runs and ships on its own — and folding in a sibling module never means merging shared config. `TestCore` is the one shared project; version/build settings are centralized in the root files.

## Create from zero

```bash
mkdir <Product> && cd <Product>
git init
dotnet new globaljson --sdk-version 10.0.100 --roll-forward latestFeature
dotnet new sln -n <Product>

dotnet new classlib -o TestCore -f net10.0
dotnet new nunit    -o ApiTests -f net10.0
dotnet sln add TestCore ApiTests
dotnet add ApiTests reference TestCore

dotnet new tool-manifest
dotnet tool install allure

# Turn on CPM first (create Directory.Packages.props — see below), THEN add packages.
# With CPM on, `dotnet add package` writes the version to Directory.Packages.props
# and a versionless <PackageReference> to the csproj automatically.
dotnet add ApiTests package RestSharp
dotnet add ApiTests package FluentAssertions
dotnet add ApiTests package Allure.NUnit
dotnet add TestCore package RestSharp
dotnet add TestCore package System.Text.Json

dotnet build         # exit gate: 0 errors, 0 warnings
```

`Directory.Packages.props` — the single version table (CPM):

```xml
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
    <CentralPackageTransitivePinningEnabled>true</CentralPackageTransitivePinningEnabled>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Microsoft.NET.Test.Sdk" Version="17.14.1" />
    <PackageVersion Include="NUnit" Version="4.3.2" />
    <PackageVersion Include="NUnit3TestAdapter" Version="5.0.0" />
    <PackageVersion Include="RestSharp" Version="112.1.0" />
    <!-- FluentAssertions deliberately pinned to the last pre-commercial-license line; see the version table. -->
    <PackageVersion Include="FluentAssertions" Version="6.12.1" />
    <!-- System.Text.Json ships in the shared framework; pin explicitly only for a transitive fix (10.0.0 on net10, 8.0.5 on net8). -->
    <PackageVersion Include="System.Text.Json" Version="10.0.0" />
    <PackageVersion Include="Allure.NUnit" Version="2.12.1" />
  </ItemGroup>
</Project>
```

`Directory.Build.props` — shared **settings only** (no versions):

```xml
<Project>
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>   <!-- or net8.0 / net9.0 to match an existing repo -->
    <LangVersion>latest</LangVersion>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
  </PropertyGroup>
</Project>
```

Each project then references only what it needs, versionless, e.g. `ApiTests.csproj`:

```xml
<ItemGroup>
  <PackageReference Include="Microsoft.NET.Test.Sdk" />
  <PackageReference Include="NUnit" />
  <PackageReference Include="NUnit3TestAdapter" />
  <PackageReference Include="RestSharp" />
  <PackageReference Include="FluentAssertions" />
  <PackageReference Include="Allure.NUnit" />
</ItemGroup>
```

## Run

```bash
dotnet test                                   # all API tests
dotnet test --filter "FullyQualifiedName~Orders"
ASPNETCORE_ENVIRONMENT=test dotnet test       # pick env overrides (appsettings.test.json)
allure serve allure-results
```

## Conventions (the shell only)

- **Config**: per-project `appsettings.json` + `appsettings.<env>.json`; base URLs, timeouts, flags from env vars. **No secrets in any committed file.**
- **Auth**: token acquisition lives in `TestCore/Http` (Auth0 M2M / ROPG per `auth0-test-tokens`), injected into the `RestClient` factory — never inline in tests.
- **DI**: constructor injection only; no static mutable state. Async all the way (`await`, never `.Result`).
- **Allure hook**: leave the per-project `allureConfig.json` + the `Allure.NUnit` reference; `qa-reporting-dotnet` owns the decorators and CI publish.

DTO shapes, typed-client structure, test naming, builders, and deep verification are owned by the `qa-api-dotnet` skills. Defer to them.

## Expanding into a multi-module solution

Flat solution + shared `TestCore` + CPM make this purely additive. To add a sibling module (e.g. **api + ui**):

1. Install the sibling plugin (`qa-ui-dotnet`) and run its scaffold **inside this repo**, skipping `global.json`, `Directory.Build.props`, `Directory.Packages.props`, `.config`, the `.sln`, and `TestCore` — they already exist.
2. Add only the sibling's project: `dotnet new nunit -o PlaywrightTests`, `dotnet sln add PlaywrightTests`, `dotnet add PlaywrightTests reference TestCore`, then its packages (Playwright, etc.) — which append their `<PackageVersion>` to the existing `Directory.Packages.props`. The sibling keeps its **own** `appsettings`/`allureConfig`/`Dockerfile`, so there is nothing to merge.
3. Promote anything both modules need (env config binding, auth-token helper, Allure setup) **up into `TestCore`**. Keep discipline-specific helpers (RestClient factory, page-object base) in their own project.
4. `dotnet test` runs every test project; `dotnet test ApiTests` runs one. Add a `.slnf` solution filter per discipline (`api.slnf`, `ui.slnf`) for focused IDE load / CI sharding instead of splitting into multiple solutions.

The same recipe folds in `AppiumTests` (Appium) and a `PerfTests` console project (NBomber — see `qa-performance-project-scaffold-dotnet`).

## Setup checklist

- [ ] `global.json` pins SDK 10.0 (or the repo's 8.0/9.0); `dotnet --version` agrees
- [ ] `Directory.Packages.props` (CPM on) is the only version source; csprojs are versionless
- [ ] `Directory.Build.props` carries settings only (`Nullable`/`TreatWarningsAsErrors` on)
- [ ] `TestCore` exists as a shared library; `ApiTests` references it
- [ ] Per-project `appsettings.json`/`appsettings.test.json`/`allureConfig.json`/`Dockerfile`/`README.md` present
- [ ] Allure local tool installed (`.config/dotnet-tools.json`)
- [ ] No secrets in `appsettings*.json`; secrets via env vars
- [ ] `dotnet build` → 0 errors / 0 warnings; `dotnet test` discovers the placeholder
