# Programmatic path — `qa-dotnet:passive-scan`

Docker via `Process`, then parse the JSON report.

To drive the scan from an NUnit test (assert programmatically, attach to Allure, gate on parsed counts),
invoke the image as a one-shot container and parse the JSON report. **Async all the way** (no
`.Result`/`.Wait()`) — this is the .NET re-expression of the TS `child_process` runner:

```csharp
// Support/ZapBaseline.cs — the Docker-port runner: one-shot container + JSON parse (no SDK exists)
using System.Diagnostics;
using System.Text.Json;

public sealed record ZapAlert(string PluginId, string Alert, string RiskCode, string RiskDesc, string Count);

public sealed record ZapResult(int ExitCode, IReadOnlyList<ZapAlert> Alerts, string ReportJsonPath, string ReportHtmlPath);

public static class ZapBaseline
{
    /// <summary>
    /// Runs `passive-scan.py` in the zaproxy container against a running target; returns the exit code
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
                "passive-scan.py",
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
        _app = new ContainerBuilder("myorg/web:latest")
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
