---
name: qa-security-testing-zap-baseline-dotnet
description: OWASP ZAP **baseline** DAST scan as a CI build gate from a .NET / NUnit pipeline: spider a **running** app for a bounded time and run ZAP's **passive** rules (no attack payloads.
---

# Security Testing — OWASP ZAP Baseline Scan (.NET / NUnit)

The .NET port of the canonical `qa-security-testing-zap-baseline-typescript`. Same baseline scan model,
same exit-code build gate, same ticketed-triage discipline — re-expressed for a .NET shop, which makes the
honest shape of this node plain.

OWASP **ZAP** (Zed Attack Proxy) is the de-facto open-source DAST scanner. The **baseline scan**
(`zap-baseline.py`, in the `ghcr.io/zaproxy/zaproxy` Docker image) spiders a **running** app for a short
bounded time, runs ZAP's **passive** rules — no attack payloads — and reports alerts by risk, exiting
**non-zero to fail the build** when alerts cross a threshold. The canonical *shift-left DAST gate in the
pipeline*: fast, safe against a deployed/ephemeral env, CI-native.

> **⚠️ Baseline (passive) vs full scan (active).** `zap-baseline.py` runs **passive** rules only — it
> observes spidered/proxied traffic and flags what it can *see* (missing `Content-Security-Policy`,
> `Set-Cookie` without `Secure`/`HttpOnly`, verbose `Server` headers, info leaks). It sends **no attack
> payloads**, so it's safe and fast (~1–few min) and the right PR gate. `zap-full-scan.py` adds the
> **active** scanner that *injects* SQLi/XSS/traversal payloads — it **mutates state and must never run
> against production or a shared environment**. This skill is the **baseline** gate; reach for the full
> scan only against a throwaway env you own, on a slower cadence.

> **⚠️ Tool-invoked-via-Docker — there is no .NET ZAP SDK.** ZAP's baseline scan is a **Docker
> invocation**, language-agnostic. Unlike axe-playwright where `Deque.AxeCore.Playwright` was a
> first-class NuGet, here there is **no NuGet to embed ZAP**. So .NET is a **CLI/Docker-driven** stack
> (the same port shape as lighthouse-ci): you **invoke the `zaproxy` image as a subprocess**
> (`System.Diagnostics.Process` → `docker run … zap-baseline.py`) and **parse the JSON report**
> (`System.Text.Json`) to gate the pipeline. The structure (spin app → scan → assert on exit code/report)
> ports from the TS canonical; the *invocation* is a `Process`, not an SDK call. Say so plainly to anyone
> reaching for a NuGet — there isn't one.

## Decision matrix — where ZAP baseline fits

| Need | Use | Why |
|------|-----|-----|
| Passive DAST gate on a **running** app in every PR (headers, cookie flags, info leaks) | **this skill** | Safe (no payloads), fast, CI-native; exits non-zero to fail the build |
| Deep active attack testing (SQLi/XSS/traversal payloads) on a throwaway env | `zap-full-scan.py` (out of scope here) | Active scanner mutates state — never prod/shared; slower cadence |
| **Dependency / library** CVEs (vulnerable NuGet packages, transitive CVEs) | dependency-scanning | SCA reads your project/lockfile; ZAP scans running HTTP — orthogonal layers |
| Per-component **accessibility** rule assertions | axe-playwright | Different concern; same *ticketed-baseline triage* discipline applies |

**Rule of thumb:** ZAP baseline is your **passive DAST PR gate** against a running app. It complements —
does not replace — SCA dependency scanning: different layers (running-app HTTP surface vs your
dependency tree). Run both; together they close Phase 2's `security-testing` family.

## Setup — no NuGet, just Docker (and optionally the GitHub Action)

There is no NuGet for the scan — you need **Docker** on the runner and the ZAP image:

```bash
docker pull ghcr.io/zaproxy/zaproxy:stable      # the image carrying zap-baseline.py
```

Your test project needs only NUnit + a JSON parser (`System.Text.Json`, already in the BCL) — and
`Testcontainers` if you spin the SUT from the test:

```xml
<!-- Tests.csproj -->
<ItemGroup>
  <PackageReference Include="NUnit" Version="4.*" />
  <PackageReference Include="NUnit3TestAdapter" Version="4.*" />
  <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.*" />
  <PackageReference Include="Testcontainers" Version="3.*" />   <!-- to stand up the SUT -->
</ItemGroup>
```

For the CI-first path you need **no local install** — the `zaproxy/action-baseline` Action wraps the image.

## The baseline scan model — spider, passive-scan, report, exit-code

`zap-baseline.py -t <targetUrl>` does three things against an **already-running** app: **spider** for
`-m <minutes>` (default **1**; `-j` adds the Ajax spider for SPAs), **passive-scan** the traffic (no
payloads) collecting **alerts** by risk (**High / Medium / Low / Informational**), and **report**
(`-J`/`-r`/`-x`/`-w`) + **exit with a code that gates the build**.

| Flag | Meaning |
|------|---------|
| `-t <url>` | **Target** URL (required) — the running app |
| `-m <min>` | Spider duration in minutes (default `1`) |
| `-j` | Also run the **Ajax spider** (SPA/JS routes) |
| `-c <file>` | **Rules config** — flip rule-ids to `IGNORE`/`WARN`/`FAIL` (the triage gate) |
| `-l <level>` | Minimum alert level to **report**: `PASS`/`IGNORE`/`INFO`/`WARN`/`FAIL` |
| `-J/-r/-x/-w` | Write **JSON / HTML / XML / Markdown** report |
| `-a` | Include **alpha** passive rules |
| `-I` | Do **not** fail on warnings (only `FAIL`-level fails) |
| `-n <ctx>` | ZAP **context** file (authenticated scans) |
| `-z <opts>` | Pass-through ZAP options |
| `-T <min>` | Max minutes to wait for ZAP startup |

### Exit codes are the gate

`zap-baseline.py` maps alerts to a process exit code — **the build-fail mechanism**, identical across all
three stacks:

| Exit | Meaning | Build |
|------|---------|-------|
| `0` | Success — no alerts at/above the gate | ✅ pass |
| `1` | At least one **`FAIL`**-level alert | ❌ **fail** |
| `2` | At least one **`WARN`**, no `FAIL`s | ⚠️ pass-or-fail (your policy) |
| `3` | Other failure (couldn't start / target unreachable) | ❌ fail (infra) |

By default ZAP reports **every** alert as `WARN` → an unconfigured run exits **2**. You make the gate
meaningful with the **rules config** (`-c`): promote what matters to `FAIL` (→ exit 1, fail the build),
demote known/accepted ones to `IGNORE`. Many teams pass on `2` (warnings tracked) and hard-fail on `1`.

## The triage gate — `-c rules.tsv` (front and center, like `axe-playwright`'s ticketed baseline)

A real app's first run lights up with WARNs; gating on *every* alert mutes the gate. Use the **ticketed
rules config**: tab-separated, each ZAP rule-id set to `IGNORE`/`WARN`/`FAIL`, **every `IGNORE` carrying a
ticket + reason** — the same allow-list discipline as `qa-accessibility-testing-dotnet`
(`axe-playwright`), ported to ZAP.

```tsv
# .zap/rules.tsv — tab-separated: <rule-id>	<IGNORE|WARN|FAIL>	(reason)
# Promote the rules we will not regress on → FAIL (exit 1, fails the build):
10038	FAIL	(Content Security Policy header missing — must ship)
10054	FAIL	(Cookie without SameSite attribute)
# Demote documented, ticketed accepted-risk / false-positives → IGNORE:
10015	IGNORE	(No Cache-control header on public marketing pages — JIRA-3101, accepted)
10096	IGNORE	(Timestamp disclosure false-positive on static asset hashes — JIRA-3102)
# Scope out a third-party widget URL we don't own (rule-id OUTOFSCOPE <regex>):
10027	OUTOFSCOPE	https://widget\.thirdparty\.com/.*
```

- Columns are **tab-separated**: `<rule-id>` ⇥ `<IGNORE|WARN|FAIL>` ⇥ `(reason)`. Use `*` for all rules.
- `IGNORE` → not reported. `WARN` → reported, doesn't fail (exit 2). `FAIL` → reported and **fails the
  build** (exit 1). `OUTOFSCOPE <regex>` excludes URLs.
- **Discipline (reuse `axe-playwright`'s framing):** gate **new** findings — promote fixed rules to `FAIL` so they
  can't regress; every `IGNORE` is a *documented, ticketed* accepted risk, not a silent suppression.
  Shrink the IGNORE list over time; never grow it to silence a real failure.

## Running the scan — the CI-first path (`zaproxy/action-baseline`)

The natural home is CI. The official Action wraps the image, runs the baseline, uploads the report, and
optionally opens a tracking issue (cross-link `qa-ci-pipelines-dotnet`):

```yaml
# .github/workflows/zap-baseline.yml
name: ZAP Baseline DAST
on: [pull_request]
jobs:
  zap_baseline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5             # so the Action can read .zap/rules.tsv
      - name: Start the app
        run: docker compose up -d --wait      # --wait blocks on healthchecks, NOT a sleep
      - name: ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.15.0
        with:
          target: 'http://localhost:5000'
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a -j'                # alpha rules + Ajax spider
          fail_action: true                   # fail the job on alerts (else relies on rules→FAIL)
          allow_issue_writing: true
          artifact_name: zap_baseline_report
          token: ${{ secrets.GITHUB_TOKEN }}
```

`target` (running app URL), `rules_file_name` (the `-c` config), `cmd_options` (extra flags), `fail_action`
(`true` fails on any alert; default `false` → only `FAIL`-promoted rules fail via the exit code),
`allow_issue_writing` (default `true`), `docker_name` (default `ghcr.io/zaproxy/zaproxy:stable`),
`artifact_name`. The .NET pipeline calls the same Action — it's language-agnostic.

> **Wait on a condition, never a sleep.** The app must be **ready** before the scan or you get
> false-clean/exit-3 results. Use `docker compose up --wait` or a Testcontainers wait strategy — never
> `Task.Delay`/`Thread.Sleep`. Global rule: no fixed waits.

## Running the scan — the programmatic path (Docker via `Process` + parse JSON)

To drive the scan from an NUnit test (assert programmatically, attach to Allure, gate on parsed counts),
invoke the image as a one-shot container and parse the JSON report. **Async all the way** (no
`.Result`/`.Wait()`) — this is the .NET re-expression of the TS `child_process` helper:

```csharp
// Support/ZapBaseline.cs — the Docker-port helper: one-shot container + JSON parse (no SDK exists)
using System.Diagnostics;
using System.Text.Json;

public sealed record ZapAlert(string PluginId, string Alert, string RiskCode, string RiskDesc, string Count);

public sealed record ZapResult(int ExitCode, IReadOnlyList<ZapAlert> Alerts, string ReportJsonPath, string ReportHtmlPath);

public static class ZapBaseline
{
    /// <summary>
    /// Runs `zap-baseline.py` in the zaproxy container against a running target; returns the exit code
    /// (the gate: 0 clean · 1 FAIL · 2 WARN-only · 3 infra) plus the parsed alerts.
    /// </summary>
    public static async Task<ZapResult> RunAsync(string targetUrl, string rulesTsvPath)
    {
        var work = Directory.CreateTempSubdirectory("zap-").FullName;
        var psi = new ProcessStartInfo
        {
            FileName = "docker",
            // --network host lets the container reach a localhost target on Linux CI; on Mac/Windows use
            // http://host.docker.internal:<port>. Reachability is the #1 gotcha — see Anti-patterns.
            ArgumentList =
            {
                "run", "--rm", "--network", "host",
                "-v", $"{work}:/zap/wrk:rw",
                "-v", $"{rulesTsvPath}:/zap/wrk/rules.tsv:ro",
                "ghcr.io/zaproxy/zaproxy:stable",
                "zap-baseline.py",
                "-t", targetUrl,
                "-c", "rules.tsv",            // ticketed triage gate (relative to /zap/wrk)
                "-J", "report.json",
                "-r", "report.html",
                "-a",                         // include alpha passive rules
            },
            RedirectStandardError = true,
            UseShellExecute = false,
        };
        using var proc = Process.Start(psi)
            ?? throw new InvalidOperationException("Could not start `docker run` — is Docker on PATH?");
        await proc.WaitForExitAsync();

        var reportJsonPath = Path.Combine(work, "report.json");
        await using var stream = File.OpenRead(reportJsonPath);
        using var doc = await JsonDocument.ParseAsync(stream);

        var alerts = new List<ZapAlert>();
        if (doc.RootElement.TryGetProperty("site", out var sites))
            foreach (var site in sites.EnumerateArray())
                if (site.TryGetProperty("alerts", out var siteAlerts))
                    foreach (var a in siteAlerts.EnumerateArray())
                        alerts.Add(new ZapAlert(
                            a.GetProperty("pluginid").GetString()!,
                            a.GetProperty("alert").GetString()!,
                            a.GetProperty("riskcode").GetString()!,    // "0" info … "3" high
                            a.GetProperty("riskdesc").GetString()!,
                            a.GetProperty("count").GetString()!));

        return new ZapResult(proc.ExitCode, alerts, reportJsonPath, Path.Combine(work, "report.html"));
    }
}
```

```csharp
// Tests/ZapBaselineTests.cs
using NUnit.Framework;
using DotNet.Testcontainers.Builders;     // ContainerBuilder + Wait
using DotNet.Testcontainers.Containers;   // IContainer

[TestFixture]
public class ZapBaselineTests
{
    private IContainer _app = null!;
    private string _target = null!;

    [OneTimeSetUp]
    public async Task StartApp()
    {
        // Stand up the SUT. Wait on a readiness condition.
        _app = new ContainerBuilder()
            .WithImage("myorg/web:latest")
            .WithPortBinding(5000, true)
            .WithWaitStrategy(Wait.ForUnixContainer().UntilHttpRequestIsSucceeded(r => r.ForPath("/health").ForPort(5000)))
            .Build();
        await _app.StartAsync();
        _target = $"http://localhost:{_app.GetMappedPublicPort(5000)}";
    }

    [OneTimeTearDown]
    public async Task StopApp() => await _app.DisposeAsync();

    [Test]
    public async Task Should_pass_baseline_When_no_FAIL_level_alerts()
    {
        var result = await ZapBaseline.RunAsync(_target, Path.GetFullPath(".zap/rules.tsv"));
        ZapReportAttachment.Attach(result);                  // attach BEFORE asserting, so a failure carries the report

        // The exit code IS the gate: 0 clean, 2 warnings-only (policy-pass), 1 means a FAIL-promoted rule fired.
        Assert.That(result.ExitCode, Is.Not.EqualTo(1));     // one logical assertion = the build gate
    }

    [Test]
    public async Task Should_have_no_high_risk_alerts_When_baseline_scanned()
    {
        var result = await ZapBaseline.RunAsync(_target, Path.GetFullPath(".zap/rules.tsv"));
        ZapReportAttachment.Attach(result);
        var high = result.Alerts.Where(a => a.RiskCode == "3").ToList();   // riskcode 3 = High
        Assert.That(high, Is.Empty);                         // assert on the parsed report, not just the exit code
    }
}
```

Two complementary gates: the **exit-code gate** (`Is.Not.EqualTo(1)` — let `-c rules.tsv` decide what
`FAIL`s, all policy in one ticketed file) and the **parsed-report gate** (`Is.Empty` on a `RiskCode`/
`PluginId` filter — a test-level assertion independent of the rules file). The TS canonical / Java sibling
parse the same `site[].alerts[]` shape.

## Authenticated scans (keep it light — the headline is the unauthenticated gate)

The baseline gate's sweet spot is the **unauthenticated** surface (headers, cookies, public pages). For
behind-login pages, baseline can take a ZAP **context** file (`-n context.context`) or pass auth options
through `-z`; full authenticated flows are really the **full scan's** job. If you do auth, inject any
credentials via **env vars read lazily** (`Environment.GetEnvironmentVariable`), never in the committed
context file or `cmd_options` (global rule: no secrets in code).

## Reporting the gate — ZAP report into Allure + CI artifact

`zap-baseline.py` writes `report.json`/`.html`/`.xml` to the mounted work dir. Attach to Allure so a
failing run names the alerts without re-scanning (cross-link `qa-allure-reporting-dotnet`):

```csharp
// Support/ZapReportAttachment.cs
using Allure.Net.Commons;

public static class ZapReportAttachment
{
    public static void Attach(ZapResult result)
    {
        AllureApi.AddAttachment("zap-report.html", "text/html", File.ReadAllBytes(result.ReportHtmlPath));
        var summary = string.Join("\n", result.Alerts.Select(a =>
            $"[{a.RiskDesc}] {a.Alert} (rule {a.PluginId}) x{a.Count}"));
        AllureApi.AddAttachment("zap-alerts.txt", "text/plain",
            System.Text.Encoding.UTF8.GetBytes(summary.Length == 0 ? "no alerts" : summary));
    }
}
```

- **Allure** — attach the HTML + a readable alert summary (rule id, risk, count).
- **CI artifact** — the Action's `artifact_name` upload, or upload the work dir (cross-link
  `qa-ci-pipelines-dotnet`).
- **Tracking issue** — `allow_issue_writing: true` opens/updates a GitHub issue.

## Anti-patterns

- **Looking for a NuGet ZAP SDK.** There isn't one — ZAP's baseline is a Docker command. *Fix:* invoke the
  image via `Process` (or the Action) and parse the JSON.
- **Running `zap-full-scan.py` (active) against prod/shared env.** It injects payloads and mutates state.
  *Fix:* use the **baseline** (passive) gate; reserve the full scan for a throwaway env you own.
- **Scanning before the app is ready** (`Task.Delay` then scan). Races startup → false-clean/exit 3.
  *Fix:* `compose up --wait` / a Testcontainers wait strategy — never `Task.Delay`/`Thread.Sleep`.
- **Blocking on the subprocess with `.Result`/`.Wait()`.** Violates async-all-the-way. *Fix:* `await
  proc.WaitForExitAsync()`, `await JsonDocument.ParseAsync(...)`.
- **Container can't reach the target.** A `localhost` target inside the ZAP container points at the
  *container*. *Fix:* `--network host` on Linux CI / `host.docker.internal` on Mac/Windows / shared Docker
  network with the service name.
- **Gating on every alert with no rules config.** Every run exits 2; the gate gets muted. *Fix:* a ticketed
  `-c rules.tsv` — promote what matters to `FAIL`, `IGNORE` documented accepted risks.
- **Blanket-`IGNORE`ing to make it green.** Hides real findings. *Fix:* `IGNORE` only with a ticket +
  reason; shrink the list over time (the `axe-playwright` discipline).
- **Treating a clean baseline as "secure."** Passive scanning sees only what's on the wire. *Fix:* pair
  with SCA, the full active scan on a safe env, and manual pentest.
- **Committing auth credentials in the context file / `cmd_options`.** *Fix:* env vars, read lazily.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Examples**.

## Rules (hard constraints)

- The gate is the **process exit code** of `zap-baseline.py` (`1` = `FAIL`-level alert → fail the build),
  optionally plus a **parsed-report** assertion (`RiskCode`/`PluginId` counts). One logical assertion per
  test. Test names `Should_X_When_Y`.
- **No native .NET SDK** — invoke the `zaproxy` image as a subprocess (`Process`) and parse the JSON
  report with `System.Text.Json`. **Async all the way**: `await proc.WaitForExitAsync()`,
  `await JsonDocument.ParseAsync(...)` — never `.Result`/`.Wait()`/`Thread.Sleep`.
- **Baseline = passive only** (safe in CI). Never run the **active** full scan against prod/shared env.
- The app must be **ready** before scanning — wait on a **condition** (`compose up --wait` / a
  Testcontainers wait strategy), never `Task.Delay`/`Thread.Sleep`.
- Triage with a **ticketed `-c rules.tsv`**: promote real rules to `FAIL`, `IGNORE` only *documented,
  ticketed* accepted risks; `OUTOFSCOPE <regex>` third-party URLs. Gate **new** findings; shrink the
  IGNORE list (the `axe-playwright` discipline).
- Solve **container→target reachability** explicitly (`--network host` / `host.docker.internal` / shared
  Docker network).
- **No secrets in code**: any auth context/credentials via env vars, read lazily.
- Attach the JSON/HTML report to **Allure** + upload as a CI artifact. A clean baseline ≠ "secure" — pair
  with SCA, a safe-env full scan, and manual pentest.

## Cross-references

- `qa-security-testing-zap-baseline-typescript` — the **canonical** skill, TS (house default; the scan is
  language-agnostic `docker run`). This .NET sibling is the `Process` + `System.Text.Json` port of it.
- `qa-security-testing-zap-baseline-java` — same skill, Java / TestNG. Same Docker choreography via
  `ProcessBuilder` + Jackson.
- `qa-security-testing-dependency-scanning-dotnet` — the **SCA** sibling that closes the
  `security-testing` family: NuGet/transitive CVEs from your project vs ZAP's running-app HTTP surface.
  Different layers — run both.
- `qa-accessibility-testing-dotnet` — the **ticketed-baseline triage** discipline
  reused here for `-c rules.tsv`.
- `qa-accessibility-testing-dotnet` — the closest **port-shape precedent**: a
  CLI/Docker tool invoked via `Process` from .NET with the report parsed as JSON.
- `qa-ci-pipelines-dotnet` — the `zaproxy/action-baseline` job, `fail_action`, artifact
  upload, Docker availability.
- `qa-allure-reporting-dotnet` — attach the ZAP HTML/JSON report and alert summary.
