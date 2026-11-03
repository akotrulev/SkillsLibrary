---
paths:
  - "**/*.runsettings"
  - "**/{allureConfig,reqnroll}.json"
  - "**/*{ApiTests,UiTests,AppiumTests,MobileTests,E2ETests,IntegrationTests,AcceptanceTests,BddTests,Bdd.Tests,PerfTests,PerformanceTests,LoadTests,TestCore}/**/*.csproj"
  - "**/*{ApiTests,UiTests,AppiumTests,MobileTests,E2ETests,IntegrationTests,AcceptanceTests,BddTests,Bdd.Tests,PerfTests,PerformanceTests,LoadTests,TestCore}/**/appsettings*.json"
---

<!-- qa-dotnet rules v1 (2026-11-03): suite config. Installed by /qa-dotnet:rules; edit the paths above to fit this project. -->

# Test-suite configuration standards

Severity tags as in the core rules. The codebase wins where it consistently does otherwise.

- No secret in any committed file: no password, token, client secret, access key or credentialed connection string in `appsettings*.json`, a `.runsettings` or a `.env` (commit `.env.example` only). Reference an environment variable. *blocker*
- Base URLs, browser, device, timeouts and worker counts come from the environment or the per-environment `appsettings.<env>.json`, never a literal in code. *major*
- Under Central Package Management `Directory.Packages.props` is the only version source: no `Version=` on a `PackageReference`. *blocker*
- Versions are pinned, never floating (`5.*`); `Microsoft.Playwright.NUnit` stays on the lane's pin (1.63). Never up-level a package as a side effect. *major*
- A Playwright `.runsettings` holds only `BrowserName`, `LaunchOptions`, `ExpectTimeout` and `TestIdAttribute`; `<Headless>` or `<Shard>` directly under `<Playwright>` is ignored. *major*
- A grid's `NumberOfTestWorkers` comes from one environment variable and never exceeds the plan's session cap or the device count. *major*
- One Allure adapter per project, `allureConfig.json` copied to output; never `Allure.NUnit` and `Allure.XUnit` writing the same `allure-results/`, which is never committed. *minor*
