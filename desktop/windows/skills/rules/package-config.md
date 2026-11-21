---
paths:
  - "**/Package.appxmanifest"
  - "**/*.csproj"
  - "**/*.vcxproj"
  - "**/Directory.Build.props"
  - "**/Directory.Packages.props"
  - "**/app.manifest"
  - "**/*.pubxml"
  - "**/nuget.config"
  - "**/.editorconfig"
---

<!-- desktop-windows rules v2 (2026-11-21): project, manifest, packaging and analyzers. Analyzer ids checked against the analyzers' documentation on 2026-11-21 (SDK 10.0, Threading.Analyzers 18, BannedApiAnalyzers 5, NUnit.Analyzers 4). Installed by /desktop-windows:rules; edit the paths above to where this project keeps its project files and analyzer config. -->

# Project, manifest and packaging standards (Windows)

Severity tags as in the core C# rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- No secret in a project file, props, manifest, `nuget.config` or the package; no committed `.pfx` with a password or Artifact Signing credential. *blocker*
- The TFM carries the OS part (`net10.0-windows10.0.26100.0`); `TargetPlatformMinVersion` is written explicitly; .NET 8 and 9 are out of support since 2026-11-10 and are a migration finding, never a target. *major*
- Windows App SDK is the 2.x stable channel; no experimental package, no CsWinRT 3.x preview. *blocker for experimental*
- Never raise the TFM, the Windows App SDK major, the C++ standard or the platform list as a side effect of other work. *major*
- Nullable on and `TreatWarningsAsErrors` set once in `Directory.Build.props`; package versions are central (`Directory.Packages.props`). *major*
- `Microsoft.Windows.SDK.BuildTools.WinUIAnalyzer` is on every WinUI app project. *minor*
- Packaged MSIX unless a reason is recorded (`WindowsPackageType=None` carries it); ClickOnce is not used for WinUI. *major*
- Platforms are `x64;ARM64`, never `Any CPU`, on a packaged project. *minor*
- Capabilities are minimal and each has a recorded reason; `runFullTrust` is the only broad one a desktop app needs; no `allowElevation`, no `requireAdministrator` in `app.manifest`. *blocker for elevation; major otherwise*
- File and protocol associations are declared narrowly and only for a packaged app; manifest strings are localized. *minor*
- `PublishAot` and trimming are decisions: warnings are read, and `{Binding}` reflection paths are gone first. *major*
- Releases are signed (Store, or Azure Artifact Signing) and the update channel is signed; an unpackaged app updates through a signed feed. *blocker*
- C++: `/W4 /WX /permissive-`, `Microsoft.Windows.CppWinRT` as the current stable NuGet, the C++ standard unchanged. *major*

## Enforced by the build

C# lanes only (WinUI, WPF, WinForms). The C++ rule above is the compiler's `/W4 /WX`, not an analyzer. Each row is a rule of `csharp.md`, `dotnet-networking.md` or `win-tests.md` that a Roslyn analyzer detects. Rules no stock analyzer detects stay in those files and get no row: constructor injection, static mutable state, a sealed state type per data region.

| House rule | Tool | Rule id or setting | Level |
|---|---|---|---|
| Nullable reference types on and warnings are errors (`csharp.md`, Safety and types) | MSBuild | `<Nullable>enable</Nullable>` and `<TreatWarningsAsErrors>true</TreatWarningsAsErrors>` in `Directory.Build.props` | setting |
| No `.Result`, `.Wait()` or `.GetAwaiter().GetResult()` (`csharp.md`, Safety and types) | `Microsoft.VisualStudio.Threading.Analyzers` | `VSTHRD002` | error |
| `async void` only on an event handler (`csharp.md`, Safety and types) | `Microsoft.VisualStudio.Threading.Analyzers` | `VSTHRD100` | error |
| Nothing blocks the UI thread: no `Thread.Sleep` (`csharp.md`, Concurrency and the UI thread) | `Microsoft.CodeAnalysis.BannedApiAnalyzers` | `RS0030`, `Thread.Sleep` in `BannedSymbols.txt` | error |
| A `CancellationToken` is passed on to the calls that take one (`csharp.md`, Concurrency and the UI thread) | .NET SDK analyzers | `CA2016` | error |
| Log calls use `ILogger` message templates, never interpolation (`csharp.md`, Errors, logging and secrets) | .NET SDK analyzers | `CA2254` | error |
| No blanket `catch (Exception)` outside a boundary (`csharp.md`, Errors, logging and secrets) | .NET SDK analyzers | `CA1031` | error |
| `HttpClient` comes from `IHttpClientFactory`, never `new HttpClient()` (`dotnet-networking.md`) | `Microsoft.CodeAnalysis.BannedApiAnalyzers` | `RS0030`, `HttpClient` constructor in `BannedSymbols.txt` | error |
| A test never sleeps or delays; it waits on a condition (`win-tests.md`) | `Microsoft.CodeAnalysis.BannedApiAnalyzers` | `RS0030`, `Task.Delay` in `BannedSymbols.Tests.txt`; `Thread.Sleep` from `BannedSymbols.txt` | error |
| A test method returns `Task`, never `void` (`win-tests.md`) | `NUnit.Analyzers` | `NUnit1012` | error |

A row the project's config does not enforce is *minor*.

Turning a row off to pass a gate is *major* (`engineering:quality-constraints`).

How the rows are wired:

- Each `error` row is `dotnet_diagnostic.<id>.severity = error` in `.editorconfig`. The analyzer packages are `PackageReference`s with `PrivateAssets="all"` in `Directory.Build.props`, versioned in `Directory.Packages.props`.
- Every `RS0030` row is one line in a `BannedSymbols` file, added to the project as `<AdditionalFiles Include="BannedSymbols.txt" />`. Every C# project gets `BannedSymbols.txt`; test projects add `BannedSymbols.Tests.txt`.
- `VSTHRD100` flags an event handler too: a handler whose whole body is inside `try`/`catch` carries a `[SuppressMessage]` with its `Justification`. `Microsoft.VisualStudio.Threading.Analyzers` also turns on `VSTHRD200` (the `Async` suffix) as a warning, which `TreatWarningsAsErrors` makes an error; no house rule asks for it, so the project sets it to `suggestion`.
- Roslyn skips generated code, so a `[RelayCommand]` or `[ObservableProperty]` expansion is not checked; the handwritten method under it is.
- `CA1031` is suppressed with a `Justification` at a real boundary only: the unhandled-exception handlers and the one place a failure becomes a typed reason.

`BannedSymbols.txt`:

```
M:System.Threading.Thread.Sleep(System.Int32);The UI thread never blocks
M:System.Threading.Thread.Sleep(System.TimeSpan);The UI thread never blocks
M:System.Net.Http.HttpClient.#ctor;Use a typed client from IHttpClientFactory
```

`BannedSymbols.Tests.txt`:

```
M:System.Threading.Tasks.Task.Delay(System.Int32);Wait on a condition
M:System.Threading.Tasks.Task.Delay(System.TimeSpan);Wait on a condition
```
