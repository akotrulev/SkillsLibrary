# The orientation-cache file template

The skeleton written to `docs/agent-context/<agent-name>.md`. The **header block is fixed** — the validation gate parses it, so keep the field names and order exactly. The **body sections are the agent's**: the headings below are the common spine, and each agent replaces the bracketed content with the fields its own orientation derives.

---

```markdown
<!-- orientation-cache v1 -->
# Agent orientation — <agent-name>

**Agent:** <agent-name>
**Written:** <YYYY-MM-DD>
**Last verified:** <YYYY-MM-DD>
**Baseline commit:** <full sha>
**Fingerprint:** <path>@<sha256:8>, <path>@<sha256:8>, ...

> Written and maintained by the `<agent-name>` agent per `ep-agent-orientation-cache`.
> A map of what this code **is** — never findings (`docs/audits/`), plans (`docs/plans/`), or specs (`docs/specs/`).
> Lines are `#confirmed` unless tagged `#inferred` or `#volatile`. Volatile lines are always re-probed.

## Version lane

<The detected versions and the guidance lane they select. Invalidated by any fingerprint-file change.>

## Build, run & test

<The exact commands, from the project's own scripts/targets — not guessed. Green-on-arrival status is deliberately NOT recorded here; it is re-verified every run.>

## Layout

<Where things live, at directory altitude. One line per area, each naming the section of this file that maps its seams.>

## Seams to reuse

<The inventory that makes a later run cheap: what already exists that a change should extend rather than duplicate, with file:line evidence and the file that sets each convention. Agent-specific — the largest section.>

## Conventions observed

<How this project does things where it differs from, or narrows, the plugin defaults. Cite the project's own CLAUDE.md/README rather than restating it.>

## Known unknowns

<One consolidated list. Things not derivable from the repo, deliberately unmapped areas, and every `#inferred` line worth confirming on the next run that touches it.>

## Session log

<Newest first, keep 10.>

- <YYYY-MM-DD> · <FULL|FIX|EXTEND> · <one line: what changed, and what that changed in this map>
```

---

## Fingerprint files

The paths whose change invalidates the version lane. Pick the ones that exist; record the hash of each (`sha256`, first 8 chars — `shasum -a 256 <path>`). Typical sets:

| Stack | Fingerprint files |
|---|---|
| .NET | `*.csproj` (or `Directory.Build.props`), `Directory.Packages.props`, `global.json` |
| Java | `build.gradle.kts` / `pom.xml`, `gradle/libs.versions.toml`, `gradle-wrapper.properties` |
| Node / TS | `package.json`, the lockfile, `tsconfig.json`, the bundler/framework config |
| Frontend | the above plus the component-library and styling entry points |
| DevOps | Dockerfile, IaC root module, pipeline YAML, the k8s base kustomization |
| Data | the migrations directory head + the ORM/config file *(the server version probe is `#volatile`, not fingerprinted)* |

## Worked example (`be-dotnet`, abridged)

```markdown
<!-- orientation-cache v1 -->
# Agent orientation — be-dotnet

**Agent:** be-dotnet
**Written:** 2026-07-30
**Last verified:** 2026-08-01
**Baseline commit:** 4f2a91c8e7d3b05a1c6e8f2d9b4a7c3e5d1f8a02
**Fingerprint:** Directory.Build.props@a1b2c3d4, Directory.Packages.props@e5f6a7b8, global.json@11c2d3e4

## Version lane

- TFM `net10.0` (Directory.Build.props:6) — .NET 10 primary lane, up-level recipes apply
- EF Core 10.0.x (Directory.Packages.props:14)
- `<Nullable>enable</Nullable>` solution-wide (Directory.Build.props:8)

## Build, run & test

- Build: `dotnet build Ordering.sln` · Test: `dotnet test` (NUnit, 3 test projects)
- Run API: `dotnet run --project src/Ordering.Api`

## Layout

- `src/Ordering.Api` — endpoints + composition root → Seams §DI
- `src/Ordering.Domain` — entities, no dependencies → Seams §Domain
- `src/Ordering.Infrastructure` — EF Core, external clients → Seams §Persistence
- `tests/` — owned by the `qa-api-dotnet` peer, not this agent

## Seams to reuse

**DI** — built-in MS.DI, one `AddOrderingModule()` extension per module (Api/Extensions/ServiceCollectionExtensions.cs:12); constructor injection throughout, no service locator #confirmed

**Persistence** — `AppDbContext` at Infrastructure/Data/AppDbContext.cs:18; `IEntityTypeConfiguration<T>` per aggregate in Data/Configurations/ (9 files); migrations in Data/Migrations/, latest `20260728_AddOrderHold`; `RowVersion` optimistic concurrency on Order only #confirmed

**Result handling** — no MediatR; endpoints call handlers directly, handlers return `Result<T>` (Domain/Results/Result.cs:9). CQRS is deliberately absent — the complexity threshold was not met #confirmed

**Telemetry** — OTel via the shared `AddOrderingTelemetry()` (Api/Extensions/TelemetryExtensions.cs:20); OTLP to the Collector, no direct exporters #confirmed

## Conventions observed

- Records for DTOs, classes for entities — project CLAUDE.md §3
- Endpoints are minimal APIs grouped per aggregate, not controllers #confirmed

## Known unknowns

- Whether `Ordering.Infrastructure/External/` clients are generated or handwritten #inferred (handwritten — no codegen config found)
- `tests/` layering not mapped: owned by the `qa-api-dotnet` peer

## Session log

- 2026-08-01 · EXTEND · added order-hold slice; new `OrderHoldConfiguration` + migration → Seams §Persistence updated
- 2026-07-30 · FULL · first orientation
```
