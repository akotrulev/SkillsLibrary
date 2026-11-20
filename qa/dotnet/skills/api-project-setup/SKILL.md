---
name: api-project-setup
description: Use when starting a RestSharp + NUnit API test project from zero in .NET (layout, package versions, run commands). Triggers "scaffold an API test project". Not for adding tests (api-tests).
disable-model-invocation: true
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
- UI / mobile / performance scaffolding → use the matching `qa/dotnet/skills/<discipline>-project-setup` skill.
- A Java or TypeScript API suite → `qa/java/skills/api-project-setup` / `qa/typescript/skills/api-project-setup`.

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
| Reporting | `Allure.NUnit` | **2.15.0** | Wiring owned by `qa-reporting-dotnet`; this scaffold only leaves the per-project `allureConfig.json` hook. |
| Allure CLI | not a NuGet tool | — | Installed and pinned by `qa/reporting/dotnet/skills/test-reports`; this scaffold installs none. |

Optional, add only when the spec demands it: `Testcontainers.PostgreSql` 4.16.0 (real-DB verification), `PactNet` (contracts), gRPC (`Grpc.Net.Client` 2.66.0), GraphQL.

## Prerequisites & local setup

```bash
dotnet --version            # expect 10.0.x (or the repo's pinned 8.0.x / 9.0.x)
docker --version            # only if you add Testcontainers-backed DB verification
# Allure CLI: see qa/reporting/dotnet/skills/test-reports
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
├── .editorconfig                       #                        ┘
├── .gitignore
├── TestCore/                           # ← shared library (composition seam)
│   ├── Configuration/                  # Env.cs — the one config loader
│   ├── Http/                           # RestClient factory, auth/log handlers
│   ├── Reporting/                      # Allure steps and attachments
│   ├── Builders/                       # builder / ObjectMother base
│   ├── GlobalUsings.cs
│   └── TestCore.csproj                 # PackageReferences WITHOUT Version (CPM)
└── ApiTests/                           # this discipline's project
    ├── Clients/                        # one typed client per service
    ├── Models/                         # request/response DTOs (records)
    ├── TestData/                       # per-domain builders / fixtures
    ├── Auth/                           # token provider (qa-dotnet:test-login-tokens)
    ├── Tests/                          # grouped by service / feature
    ├── Specs/                          # stored OpenAPI assets: {service}-openapi-YYYY-MM-DD.json
    ├── Tools/                          # one-off scripts / spec downloaders
    ├── allureConfig.json               # ┐ per-project config — keeps the
    ├── appsettings.json                # │ suite independently configurable
    ├── .env.example                    # │ and dockerizable
    ├── Dockerfile                      # │ (CI shards this suite on its own)
    ├── GlobalUsings.cs                 # │
    ├── README.md                       # ┘ run instructions for this suite
    └── ApiTests.csproj                 # references TestCore
```

Why flat + per-project config: each test project owns its `appsettings`, `allureConfig` and `Dockerfile`, so it runs and ships on its own and a sibling module never merges shared config. Versions and build settings live in the root files.

## Create from zero

```bash
mkdir <Product> && cd <Product>
git init
dotnet new globaljson --sdk-version 10.0.100 --roll-forward latestFeature
dotnet new sln -n <Product>

dotnet new classlib -o TestCore -f net10.0
dotnet new classlib -o ApiTests -f net10.0
dotnet sln add TestCore ApiTests
dotnet add ApiTests reference TestCore

# Create Directory.Packages.props (below) first: `dotnet add package` then writes a
# versionless <PackageReference>. `dotnet new nunit` is not used: its csproj carries
# inline versions, which fail restore under CPM (NU1008).
for p in Microsoft.NET.Test.Sdk NUnit NUnit3TestAdapter RestSharp FluentAssertions Allure.NUnit; do
  dotnet add ApiTests package $p
done
dotnet add TestCore package RestSharp

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
    <PackageVersion Include="FluentAssertions" Version="6.12.1" />
    <PackageVersion Include="Allure.NUnit" Version="2.15.0" />
  </ItemGroup>
</Project>
```

`Directory.Build.props` — shared **settings only** (no versions):

```xml
<Project>
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
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
<ItemGroup>
  <Content Include="appsettings.json;allureConfig.json" CopyToOutputDirectory="PreserveNewest" />
</ItemGroup>
```

## Configuration

**One loader, one precedence:** an environment variable overrides `appsettings.json`, which holds only committed, non-secret defaults. Secrets (the `AUTH0_*` variables of `test-login-tokens`) have no committed value: they come from the environment, and `.env.example` lists their names with empty values. `TestCore/Configuration/Env.cs` declares one name constant and one typed getter per key that code reads, and a missing key fails naming it:

```csharp
using System.Text.Json;

namespace Example.TestCore.Configuration;

public static class Env
{
    private const string ApiBaseUrlKey = "API_BASE_URL";

    private static readonly Dictionary<string, string> Defaults = LoadDefaults();

    public static Uri ApiBaseUrl => new(Required(ApiBaseUrlKey));

    private static string Required(string key)
    {
        var value = Environment.GetEnvironmentVariable(key) ?? Defaults.GetValueOrDefault(key);
        if (string.IsNullOrWhiteSpace(value))
        {
            throw new InvalidOperationException($"Configuration key {key} is not set: export it or add it to appsettings.json");
        }
        return value;
    }

    private static Dictionary<string, string> LoadDefaults()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "appsettings.json");
        return JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(path)) ?? [];
    }
}
```

`ApiTests/appsettings.json` keys are the variable names: `{ "API_BASE_URL": "https://api.staging.example.test" }`. Add a key only with the getter that reads it.

The one smoke test, `ApiTests/Tests/SmokeTests.cs`, proves the wiring. Point it at the service's health endpoint and delete the template's `UnitTest1.cs`:

```csharp
using System.Net;
using Allure.NUnit;
using Example.TestCore.Configuration;
using NUnit.Framework;
using RestSharp;

namespace Example.ApiTests.Tests;

[AllureNUnit]
[Category("smoke")]
public class SmokeTests
{
    [Test]
    public async Task Should_ReturnOk_When_HealthIsRequested()
    {
        using var client = new RestClient(Env.ApiBaseUrl);

        var response = await client.ExecuteGetAsync(new RestRequest("health"));

        Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.OK), response.Content);
    }
}
```

Rename the `Example` namespace to `<Product>`. Real tests call a typed client in `Clients/` (`api-client-writer`), not a bare `RestClient`.

## Run

```bash
dotnet test                                   # all API tests
dotnet test --filter "FullyQualifiedName~Orders"
dotnet test --filter "TestCategory=smoke"
API_BASE_URL=https://api.dev.example.test dotnet test   # the environment overrides appsettings.json
```

## Container

`ApiTests/Dockerfile`, built from the solution root so it sees `Directory.Packages.props` and `TestCore`. The base tag equals the SDK `global.json` pins:

```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:10.0.100-noble
WORKDIR /src
COPY . .
RUN dotnet build ApiTests/ApiTests.csproj -c Release
ENTRYPOINT ["dotnet", "test", "ApiTests/ApiTests.csproj", "-c", "Release", "--no-build"]
```

```bash
docker build -f ApiTests/Dockerfile -t api-tests .
docker run --rm --init -e API_BASE_URL \
  -v "$PWD/allure-results:/src/ApiTests/bin/Release/net10.0/allure-results" api-tests
```

- Built from the working tree (`COPY`), never by cloning the repository inside the image, so a pull-request build tests the pull request. Packages restore at the versions `Directory.Packages.props` pins.
- The exec-form `ENTRYPOINT` makes `dotnet test` the container's command, and `docker run` returns its exit code: no shell wrapper, no `|| true`.
- Secrets arrive only as `-e` at run time (add one `-e` per secret the token provider reads), never `ARG`, `ENV` or a copied file. `.dockerignore` excludes `**/bin`, `**/obj` and `.env*`.
- `allure-results/` lands in the mounted host folder, where the report is generated (`qa/reporting/dotnet/skills/test-reports`).

## Conventions (the shell only)

The standards the shell must meet are the qa-dotnet rule files, not a list here: `automation.md`, `api.md` and `suite-config.md`. Tell the user to install them with the shell (`/qa-dotnet:rules` copies them into `.claude/rules/qa-dotnet/`); until then read the plugin's copies in `qa/dotnet/skills/rules/`. Where they and this skill's recipes disagree, the rule files win.

- **Auth**: token acquisition lives in `ApiTests/Auth` (Auth0 M2M / ROPG per `test-login-tokens`), injected into the `RestClient` factory — never inline in tests.
- **Allure hook**: leave the per-project `allureConfig.json` + the `Allure.NUnit` reference; `qa-reporting-dotnet` owns the decorators and CI publish.

DTO shapes, typed-client structure, test naming, builders, and deep verification are owned by the `qa-api-dotnet` skills. Defer to them.

## Expanding into a multi-module solution

Flat solution + shared `TestCore` + CPM make this purely additive. To add a sibling module (e.g. **api + ui**):

1. Install the sibling plugin (`qa-ui-dotnet`) and run its scaffold **inside this repo**, skipping `global.json`, `Directory.Build.props`, `Directory.Packages.props`, `.config`, the `.sln`, and `TestCore` — they already exist.
2. Add only the sibling's project: `dotnet new nunit -o UiTests`, `dotnet sln add UiTests`, `dotnet add UiTests reference TestCore`, then its packages (Playwright, etc.) — which append their `<PackageVersion>` to the existing `Directory.Packages.props`. The sibling keeps its **own** `appsettings`/`allureConfig`/`Dockerfile`, so there is nothing to merge.
3. Promote anything both modules need (env config binding, the token provider, Allure setup) **up into `TestCore`**. Keep discipline-specific pieces (RestClient factory, page-object base) in their own project.
4. `dotnet test` runs every test project; `dotnet test ApiTests` runs one. Add a `.slnf` solution filter per discipline (`api.slnf`, `ui.slnf`) for focused IDE load / CI sharding instead of splitting into multiple solutions.

The same recipe folds in `AppiumTests` (Appium) and a `PerfTests` console project (NBomber — see `qa-dotnet:performance-project-setup`).

## Setup checklist

- [ ] `global.json` pins SDK 10.0 (or the repo's 8.0/9.0); `dotnet --version` agrees
- [ ] `Directory.Packages.props` (CPM on) is the only version source; csprojs are versionless
- [ ] `Directory.Build.props` carries settings only (`Nullable`/`TreatWarningsAsErrors` on)
- [ ] `TestCore` exists as a shared library; `ApiTests` references it
- [ ] Per-project `appsettings.json`/`.env.example`/`allureConfig.json`/`Dockerfile`/`README.md` present
- [ ] `Env` is the one config loader: environment over `appsettings.json`, a missing key fails naming it, no key declared that nothing reads
- [ ] No secrets in `appsettings*.json`; secrets via env vars
- [ ] `dotnet build` → 0 errors / 0 warnings; the smoke test is green against a reachable service.
