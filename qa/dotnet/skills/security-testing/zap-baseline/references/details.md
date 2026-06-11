# Deep-dive details — `qa-security-testing-zap-baseline-dotnet`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Examples

**End-to-end: a passive DAST PR gate that fails on regressed security headers, triages known noise, and
attaches the report.**

```tsv
# .zap/rules.tsv — the ticketed triage gate
10038	FAIL	(CSP header missing — must ship; gate any regression)
10063	FAIL	(Permissions-Policy header missing)
10015	IGNORE	(No Cache-control on public marketing pages — JIRA-3101, accepted)
10096	IGNORE	(Timestamp disclosure false-positive on asset hashes — JIRA-3102)
```

```csharp
// Tests/HeaderRegressionTests.cs — the parsed-report gate variant
[Test]
public async Task Should_fail_baseline_When_csp_header_dropped()
{
    var result = await ZapBaseline.RunAsync(_target, Path.GetFullPath(".zap/rules.tsv"));
    ZapReportAttachment.Attach(result);
    // Rule 10038 (CSP) is promoted to FAIL in rules.tsv → exit 1 when it fires.
    Assert.That(result.ExitCode, Is.Not.EqualTo(1), "A FAIL-level alert fired — see the attached ZAP report");
}
```

Lifecycle for this gate:
1. A dev ships a change that drops the `Content-Security-Policy` header on the app shell.
2. The PR runs the baseline scan against the compose-spun app (ready on healthchecks).
3. Rule `10038` is promoted to `FAIL` → ZAP exits **1** → **the job fails**, with the alert (rule id,
   risk, affected URLs) in the uploaded report artifact and the tracking issue.
4. The dev restores the header; the scan exits 0/2; the gate goes green. The two `IGNORE`d rules stay
   tracked by their JIRA tickets, shrinking over time — never grown to silence a real finding.
