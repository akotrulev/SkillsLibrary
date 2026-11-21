---
paths:
  - "**/*.runsettings"
  - "**/{allureConfig,reqnroll}.json"
  - "**/*{ApiTests,UiTests,AppiumTests,MobileTests,DesktopTests,E2ETests,IntegrationTests,AcceptanceTests,BddTests,Bdd.Tests,PerfTests,PerformanceTests,LoadTests,TestCore}/**/*.csproj"
  - "**/*{ApiTests,UiTests,AppiumTests,MobileTests,DesktopTests,E2ETests,IntegrationTests,AcceptanceTests,BddTests,Bdd.Tests,PerfTests,PerformanceTests,LoadTests,TestCore}/**/appsettings*.json"
  - "**/.editorconfig"
---

<!-- qa-dotnet rules v2 (2026-11-21): suite config and analyzers. Ids checked against the analyzers' documentation on 2026-11-21 (SDK 10.0, Threading.Analyzers 18, BannedApiAnalyzers 5, NUnit.Analyzers 4). Installed by /qa-dotnet:rules; edit the paths above to fit this project, re-run to compare with the plugin's copy. -->

# Test-suite configuration standards

Severity tags as in the core rules. The codebase wins where it consistently does otherwise.

- No secret in any committed file: no password, token, client secret, access key or credentialed connection string in `appsettings*.json`, a `.runsettings` or a `.env` (commit `.env.example` only). Reference an environment variable. *blocker*
- Base URLs, browser, device, timeouts and worker counts come from the environment or the per-environment `appsettings.<env>.json`, never a literal in code. *major*
- Under Central Package Management `Directory.Packages.props` is the only version source: no `Version=` on a `PackageReference`. *blocker*
- Versions are pinned, never floating (`5.*`); `Microsoft.Playwright.NUnit` stays on the lane's pin (1.63). Never up-level a package as a side effect. *major*
- A Playwright `.runsettings` holds only `BrowserName`, `LaunchOptions`, `ExpectTimeout` and `TestIdAttribute`; `<Headless>` or `<Shard>` directly under `<Playwright>` is ignored. *major*
- A grid's `NumberOfTestWorkers` comes from one environment variable and never exceeds the plan's session cap or the device count. *major*
- One Allure adapter per project, `allureConfig.json` copied to output; never `Allure.NUnit` and `Allure.XUnit` writing the same `allure-results/`, which is never committed. *minor*

## Enforced by the build

Each row is a rule of `automation.md` that an analyzer detects, so the build catches it before a review does. Rules no stock analyzer detects stay in that file and get no row: a branch, loop or `try` in a test body, an empty `catch` of a named type, one assertion per behaviour, one expected value per assertion, intent-named page objects, static mutable state, a skip without a reason.

| House rule (file, section) | Tool | Rule id or setting | Level |
|---|---|---|---|
| No `Thread.Sleep`, `Task.Delay` or `WaitForTimeoutAsync` as a wait (`automation.md`, Async and waiting) | `Microsoft.CodeAnalysis.BannedApiAnalyzers` | `RS0030`, those members in `BannedSymbols.txt` | error |
| NUnit constraint assertions only: no `ClassicAssert`, `StringAssert`, `CollectionAssert`, `FileAssert`, `DirectoryAssert`, no FluentAssertions (`automation.md`, Test shape) | `Microsoft.CodeAnalysis.BannedApiAnalyzers` | `RS0030`, those types in `BannedSymbols.txt` | error |
| No `[Order]` chain: a test runs alone and in any order (`automation.md`, Test shape) | `Microsoft.CodeAnalysis.BannedApiAnalyzers` | `RS0030`, `OrderAttribute` in `BannedSymbols.txt` | error |
| No retry attribute except `[Retry(2)]` on a documented hotspot (`automation.md`, Async and waiting) | `Microsoft.CodeAnalysis.BannedApiAnalyzers` | `RS0030`, `RetryAttribute` in `BannedSymbols.txt` | error |
| `System.Text.Json`, never `Newtonsoft.Json` (`automation.md`, Data, config and secrets) | `Microsoft.CodeAnalysis.BannedApiAnalyzers` | `RS0030`, `N:Newtonsoft.Json` in `BannedSymbols.txt` | error |
| No `.Result`, `.Wait()` or `.GetAwaiter().GetResult()` (`automation.md`, Async and waiting) | `Microsoft.VisualStudio.Threading.Analyzers` | `VSTHRD002` | error |
| No `async void` (`automation.md`, Async and waiting) | `Microsoft.VisualStudio.Threading.Analyzers` | `VSTHRD100` | error |
| A test method returns `Task`, never `void` (`automation.md`, Async and waiting) | `NUnit.Analyzers` | `NUnit1012` | error |
| Every call that returns a task is awaited (`automation.md`, Async and waiting) | the compiler and `Microsoft.VisualStudio.Threading.Analyzers` | `CS4014` in an async method, `VSTHRD110` in a sync one | error |
| A `catch` names one exception type, never `Exception` or a bare `catch` (`automation.md`, Errors and cleanup) | .NET SDK analyzers | `CA1031` | error |
| Nullable is enabled in every suite project (`automation.md`, Data, config and secrets) | MSBuild | `<Nullable>enable</Nullable>` in `Directory.Build.props` | setting |

A row the project's config does not enforce is *minor*.

Turning a row off to pass a gate is *major* (`engineering:quality-constraints`).

How the rows are wired:

- Each `error` row is `dotnet_diagnostic.<id>.severity = error` in `.editorconfig`. The analyzer packages are `PackageReference`s with `PrivateAssets="all"` in `Directory.Build.props`.
- Every `RS0030` row is one line in `BannedSymbols.txt`, added to each suite project as `<AdditionalFiles Include="BannedSymbols.txt" />`. A line whose package the project does not reference (Playwright, FluentAssertions, Newtonsoft.Json) is ignored without a warning, so one file serves every suite project. A `M:Type.Member` line with no parameter list matches the parameterless overload only, so each overload is its own line, as `Thread.Sleep` and `Task.Delay` show below.
- `Task.Delay` is banned as a wait. The one sanctioned use, the server-dictated poll interval of a device-code flow, sits in the token provider with a `[SuppressMessage]` carrying its `Justification`. A documented `[Retry(2)]` hotspot suppresses `RS0030` the same way.
- `CA1031` also flags a probe, seeder or teardown registry that must catch broadly. It suppresses the rule with a `Justification`, logs what it caught and never swallows it.
- Roslyn skips generated code for `VSTHRD002`, `VSTHRD100` and `CA1031` (a file with an `<auto-generated>` header, such as the Reqnroll `*.feature.cs` beside each feature), but not for `RS0030`, which reports there at the `.editorconfig` severity. A Reqnroll project built clean under these severities in a scratch project.
- `Microsoft.VisualStudio.Threading.Analyzers` turns on `VSTHRD200` (the `Async` suffix) as a warning, which flags every `Should_X` test returning `Task`. The project sets `VSTHRD200` to `suggestion`.
- `Allure.NUnit` depends on `Newtonsoft.Json`, so the package stays restored. The `Newtonsoft.Json` row bans its use in source, not its presence.

`BannedSymbols.txt`:

```
M:System.Threading.Thread.Sleep(System.Int32);Wait on a condition
M:System.Threading.Thread.Sleep(System.TimeSpan);Wait on a condition
M:System.Threading.Tasks.Task.Delay(System.Int32);Wait on a condition
M:System.Threading.Tasks.Task.Delay(System.Int32,System.Threading.CancellationToken);Wait on a condition
M:System.Threading.Tasks.Task.Delay(System.TimeSpan);Wait on a condition
M:System.Threading.Tasks.Task.Delay(System.TimeSpan,System.Threading.CancellationToken);Wait on a condition
M:System.Threading.Tasks.Task.Delay(System.TimeSpan,System.TimeProvider);Wait on a condition
M:System.Threading.Tasks.Task.Delay(System.TimeSpan,System.TimeProvider,System.Threading.CancellationToken);Wait on a condition
M:Microsoft.Playwright.IPage.WaitForTimeoutAsync(System.Single);Wait on a condition
M:Microsoft.Playwright.IFrame.WaitForTimeoutAsync(System.Single);Wait on a condition
T:NUnit.Framework.Legacy.ClassicAssert;Use Assert.That with a constraint
T:NUnit.Framework.Legacy.StringAssert;Use Assert.That with a constraint
T:NUnit.Framework.Legacy.CollectionAssert;Use Assert.That with a constraint
T:NUnit.Framework.Legacy.FileAssert;Use Assert.That with a constraint
T:NUnit.Framework.Legacy.DirectoryAssert;Use Assert.That with a constraint
T:FluentAssertions.AssertionExtensions;Use Assert.That with a constraint
T:NUnit.Framework.OrderAttribute;A test runs alone and in any order
T:NUnit.Framework.RetryAttribute;Fix the test; a documented hotspot suppresses this with its reason
N:Newtonsoft.Json;Use System.Text.Json
```
