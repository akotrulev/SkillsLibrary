---
paths:
  - "**/.globalconfig"
  - "**/Directory.Build.props"
  - "**/BannedSymbols*.txt"
---

<!-- fe-blazor rules v1 (2026-11-21): analyzers. Ids checked against the analyzers' documentation on 2026-11-21 (SDK 10.0, Threading.Analyzers 18, BannedApiAnalyzers 5). Installed by /fe-blazor:rules; edit the paths above to where this project keeps its analyzer config, re-run to compare with the plugin's copy. -->

# Blazor analyzer standards

Severity tags as in the core Blazor rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

Each row below is a rule of `blazor.md` or `blazor-tests.md` that a Roslyn analyzer detects, so the build catches it before a review does. Rules no stock analyzer detects stay in those files and get no row: `EventCallback<T>` parameters, `@key`, disposal, the three-state region.

## Enforced by the build

| House rule | Tool | Rule id or setting | Level |
|---|---|---|---|
| No `.Result`, `.Wait()` or `.GetAwaiter().GetResult()` (`blazor.md`, Data, errors and background work) | `Microsoft.VisualStudio.Threading.Analyzers` | `VSTHRD002` | error |
| No `async void` handler (`blazor.md`, Component contract and lifecycle) | `Microsoft.VisualStudio.Threading.Analyzers` | `VSTHRD100` | error |
| A `CancellationToken` is passed on to the calls that take one (`blazor.md`, Data, errors and background work) | .NET SDK analyzers | `CA2016` | error |
| `HttpClient` comes from `IHttpClientFactory`, never `new HttpClient()` (`blazor.md`, Data, errors and background work) | `Microsoft.CodeAnalysis.BannedApiAnalyzers` | `RS0030`, `HttpClient` constructor in `BannedSymbols.txt` | error |
| A bUnit test waits with `WaitForState`, never `Thread.Sleep` or `Task.Delay` (`blazor-tests.md`) | `Microsoft.CodeAnalysis.BannedApiAnalyzers` | `RS0030`, `Thread.Sleep` and `Task.Delay` in `BannedSymbols.Tests.txt` | error |

A row the project's config does not enforce is *minor*.

Turning a row off to pass a gate is *major* (`engineering:quality-constraints`).

How the rows are wired:

- Each `error` row is `dotnet_diagnostic.<id>.severity = error` in a `.globalconfig` (`is_global = true`). A `.editorconfig` section does not reach Razor-generated code, so an `RS0030` set there stays a warning inside `@code`. The analyzer packages are `PackageReference`s with `PrivateAssets="all"` in `Directory.Build.props`.
- Every `RS0030` row is one line in a `BannedSymbols` file, added to the project as `<AdditionalFiles Include="BannedSymbols.txt" />`. Component projects get `BannedSymbols.txt`, bUnit test projects add `BannedSymbols.Tests.txt`.
- Roslyn skips Razor-generated code for `VSTHRD002`, `VSTHRD100` and `CA2016`: they check `.cs` and `.razor.cs`, never a `@code` block. Only `RS0030` reaches into `@code`, so logic that must be checked lives in the code-behind.
- `Microsoft.VisualStudio.Threading.Analyzers` also turns on `VSTHRD200` (the `Async` suffix) as a warning, which `TreatWarningsAsErrors` makes an error. No house rule asks for it: the project sets it to `suggestion`.

`BannedSymbols.txt`:

```
M:System.Net.Http.HttpClient.#ctor;Use a typed client from IHttpClientFactory
```

`BannedSymbols.Tests.txt`:

```
M:System.Threading.Thread.Sleep(System.Int32);Wait with WaitForState
M:System.Threading.Thread.Sleep(System.TimeSpan);Wait with WaitForState
M:System.Threading.Tasks.Task.Delay(System.Int32);Wait with WaitForState
M:System.Threading.Tasks.Task.Delay(System.TimeSpan);Wait with WaitForState
```
