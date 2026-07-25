---
name: qa-security-testing-dependency-scanning-dotnet
description: Use when wiring SCA (dependency-vulnerability scanning) as a CI gate for a .NET build — `dotnet list package --vulnerable` over the direct + transitive tree, failing above a severity threshold, with a ticketed suppression path. Triggers "fail the build on vulnerable dependencies", "add dependency scanning", "gate new CVEs". Not for runtime DAST (`security-testing/zap-baseline`) or container/IaC layers (`container-iac-scanning`).
---

# Security Testing — Dependency Scanning / SCA (.NET)

**Software Composition Analysis (SCA)** answers a different security question from DAST: not "is the
running app exploitable over HTTP?" (that's ZAP, `zap-baseline`) but **"does my dependency tree contain package
versions with known CVEs?"** It reads your **build graph / lockfile** — direct *and* **transitive**
dependencies — matches each package+version against a vulnerability feed (the **GitHub Advisory Database**
that backs NuGet audit, plus NVD), and **fails the build** when a finding crosses a severity threshold. It
needs **no running app** (contrast DAST): it's a static, fast, every-PR pipeline gate.

> **⚠️ SCA vs DAST — two orthogonal layers, run both.** ZAP scans the **running app's HTTP
> surface** (missing headers, cookie flags, info leaks). SCA scans your **dependency tree** (a
> vulnerable `Newtonsoft.Json`, a transitive `System.*` package…). A clean ZAP baseline says nothing about
> a deserialization CVE in a transitive package; a clean SCA says nothing about a missing CSP header.
> **Together they close Phase 2's `security-testing` family — wire both gates.**

> **Stack-native first.** Unlike `zap-baseline` (one language-agnostic Docker tool), SCA is **stack-native**: each
> ecosystem has its own first-class auditor. .NET's are **`dotnet list package --vulnerable`** (the CLI,
> parse-and-assert) and **NuGet audit** (`<NuGetAudit>` — a build-integrated gate, warnings on restore) —
> so this skill leads with them. **OWASP Dependency-Check** is the cross-stack common denominator (its
> richest form is the Gradle plugin — the Java sibling is canonical for this node); reach for it only when
> you need parity with a JVM/TS monorepo. The **discipline** — severity-gate, ticketed-suppress,
> fail-the-build, report→Allure — is identical across all three; only the tool differs.

## Decision matrix — where SCA fits

| Need | Use | Why |
|------|-----|-----|
| Gate the **dependency tree** (direct + transitive CVEs) in every PR | **this skill** | Native, static, fast, no running app; fails the build above a severity threshold |
| Build-integrated gate (warnings on every `restore`/`build`) | **NuGet audit** (`<NuGetAudit>`) | No separate step — `NuGetAuditLevel` + warnings-as-errors |
| Scan the **running app's HTTP surface** (headers, cookies, info leaks) | zap-baseline | DAST probes live traffic — orthogonal layer; run both |
| **Remediate** vulnerable deps automatically | Dependabot / Renovate | They *bump*; SCA *gates*. Complementary — gate + auto-fix |
| Gate only the deps a PR **adds/changes** (diff-scoped) | `dependency-review-action` | PR-diff gate on GitHub; pairs with the full-tree scan |
| **Cross-stack** parity in a polyglot monorepo | OWASP Dependency-Check | One tool over NuGet + Maven + npm; otherwise the native tools are simpler |

**Rule of thumb:** SCA is your **dependency-tree CVE gate**; it complements — does not replace — DAST
(`zap-baseline`). Pair the gate with a *remediation* tool (Dependabot/Renovate) so findings get fixed, not just
flagged.

## Setup — the two native paths

**Path A — NuGet audit (build-integrated, the recommended default).** Audit runs automatically on
`restore`/`build` and emits `NU1901`–`NU1904` warnings for vulnerable packages. Turn the warnings into a
**gate** by failing the build on them:

```xml
<!-- Directory.Build.props — apply across the solution -->
<Project>
  <PropertyGroup>
    <NuGetAudit>true</NuGetAudit>                 <!-- on by default; explicit is good -->
    <NuGetAuditMode>all</NuGetAuditMode>          <!-- direct + transitive (default 'all' on net10+, else 'direct') -->
    <NuGetAuditLevel>high</NuGetAuditLevel>       <!-- gate on High+ (low|moderate|high|critical) -->
    <!-- Make the audit warnings FAIL the build (the gate). Scope to the NU190x codes, not all warnings: -->
    <WarningsAsErrors>$(WarningsAsErrors);NU1901;NU1902;NU1903;NU1904</WarningsAsErrors>
  </PropertyGroup>
</Project>
```

```bash
dotnet restore   # NuGet audit runs here → NU190x warnings → errors via WarningsAsErrors (the gate)
```

**Path B — `dotnet list package --vulnerable` (explicit CLI scan, parse-and-assert).** Best for a
dedicated CI step or a test-driven assertion:

```bash
dotnet restore
dotnet list package --vulnerable --include-transitive                 # human-readable
dotnet list package --vulnerable --include-transitive --format json   # machine-readable → parse / Allure
```

> **`--include-transitive` is not optional.** Without it you scan only the packages you declared and miss
> exactly the transitive ones that carry most real CVEs. Always include it.

## The SCA model — scan direct + transitive deps against a CVE feed

Both paths resolve the **full** dependency graph — every NuGet package the build pulls in, **including
transitive ones you never declared** — and match each package+version against the **GitHub Advisory
Database** (the source NuGet audit queries) / NVD. Each match is a CVE with a **severity** (low / moderate /
high / critical). The defining traits:

- **Transitive coverage is the whole point.** You declared `Microsoft.AspNetCore.*`; it dragged in
  transitive packages. SCA flags a CVE in a transitive `System.Text.Encodings.Web` you never typed.
- **No running app.** Build-graph-driven; runs in seconds. Contrast DAST, which needs a deployed
  target.
- **The gate is a severity threshold** — `NuGetAuditLevel` / your parse-and-assert filter. Pick it
  deliberately: start at `critical`, ratchet to `high` as you clear the backlog.

## The build-fail gate

| Mechanism | How it fails the build | Threshold knob |
|-----------|------------------------|----------------|
| **NuGet audit** | `NU190x` warnings → errors via `WarningsAsErrors` | `NuGetAuditLevel` (low/moderate/high/critical) |
| **`dotnet list package --vulnerable`** | always exits **0** — **parse the output and assert** (it doesn't gate on its own) | your filter in the test/CI step |

> **Gotcha: `dotnet list package --vulnerable` does NOT set a non-zero exit code on findings.** Unlike `npm
> audit`, it returns 0 whether or not vulnerabilities exist. So the **gate is your parse-and-assert** (test
> or CI script that greps/parses the JSON and fails), *or* you rely on **NuGet audit + `WarningsAsErrors`**
> for the exit-code gate. Don't assume the command fails the build by itself — it won't.

The severity threshold (`NuGetAuditLevel=high`) mirrors the Java sibling's `failBuildOnCVSS = 7.0f` and the
TS sibling's `npm audit --audit-level=high`.

## The triage gate — ticketed `NuGetAuditSuppress` / `NoWarn` (like `axe-playwright` / `zap-baseline`)

A real project's first scan lights up — including findings you **cannot fix today** because they're in a
**transitive** package or are false positives. Gating on *everything* with no triage trains the team to
mute the gate. The disciplined approach is the **ticketed suppression** — same discipline as
`qa-accessibility-testing-dotnet` and `zap-baseline`'s `rules.tsv`, ported to SCA.

```xml
<!-- Directory.Build.props (or the .csproj) — ticketed, per-advisory suppression -->
<Project>
  <ItemGroup>
    <!-- Accepted-risk: transitive CVE we can't bump yet; ticketed so it can't rot silently. -->
    <!-- JIRA-4210: GHSA-xxxx in transitive System.* via AspNetCore; fix lands next runtime patch. -->
    <NuGetAuditSuppress Include="https://github.com/advisories/GHSA-xxxx-xxxx-xxxx" />
  </ItemGroup>
</Project>
```

- **`<NuGetAuditSuppress Include="<advisory-url>" />`** suppresses **one specific advisory** — never a
  blanket `NoWarn` of all `NU190x` (that mutes every future CVE). Scope to the advisory URL.
- .NET has **no native `until=` expiry** like Dependency-Check; emulate it by putting the re-review date in
  the comment + a tracking ticket, and audit the suppression list each release. (Track the date in the
  ticket; the comment is the reminder.)
- **Discipline (reuse `axe-playwright` / `zap-baseline`):** gate **new** CVEs; suppress only *documented, ticketed* accepted-risk;
  **shrink** the list over time, never grow it to silence a real finding. Every suppression names a ticket.

### The transitive-dep reality

The hard part of SCA: the vulnerable package is often **transitive** — you didn't declare it and can't just
bump its line. Three honest responses, in order of preference:

1. **Add a direct top-level `<PackageReference>` to the patched version** — pin the transitive package by
   declaring it directly at the fixed version, so the real bump wins:
   ```xml
   <ItemGroup>
     <!-- CVE-2023-XXXX — pin patched transitive System.Text.Json directly (JIRA-4210, fixed) -->
     <PackageReference Include="System.Text.Json" Version="8.0.5" />
   </ItemGroup>
   ```
   (Java forces the version via a Gradle constraint; npm via `overrides`. Same idea, NuGet's way.)
2. **Bump the direct parent** that pulls it in, if a patched line resolves the transitive.
3. **`<NuGetAuditSuppress>` with a ticket** *only* when neither works yet (no upstream fix) — and revisit
   each release. The direct pin is a real fix; the suppression is a tracked deferral.

## Report → Allure + SARIF / GitHub code-scanning

`dotnet list package --vulnerable --format json` emits the full finding set. Attach it (plus a summary) to
Allure so a failing run names the CVEs without re-scanning (cross-link `qa-allure-reporting-dotnet`):

```csharp
// Support/DependencyScanReport.cs — run the scan, attach JSON + summary to Allure, return the findings
using System.Diagnostics;
using System.Text.Json;
using Allure.Net.Commons;

public static class DependencyScanReport
{
    public static async Task<JsonDocument> RunVulnerableScanAsync()
    {
        using var proc = new Process
        {
            StartInfo = new ProcessStartInfo("dotnet",
                "list package --vulnerable --include-transitive --format json")
            { RedirectStandardOutput = true, UseShellExecute = false }
        };
        proc.Start();
        var json = await proc.StandardOutput.ReadToEndAsync();   // async all the way — no .Result/.Wait()
        await proc.WaitForExitAsync();

        AllureApi.AddAttachment("dotnet-vulnerable.json", "application/json",
            System.Text.Encoding.UTF8.GetBytes(json));
        return JsonDocument.Parse(json);
    }
}
```

- **Allure** — attach the JSON + a readable summary (cross-link `qa-allure-reporting-dotnet`).
- **SARIF → GitHub code-scanning** — convert the JSON to SARIF (a converter step) and feed
  `github/codeql-action/upload-sarif` so each CVE shows inline on the PR. (OWASP Dependency-Check emits
  SARIF natively if you use it for cross-stack parity.)
- **CI artifact** — upload the JSON (cross-link `qa-ci-pipelines-dotnet`).

## Optional parse-and-assert test (the programmatic path)

Because `dotnet list package --vulnerable` **doesn't gate on its own**, the parse-and-assert test is often
*the* gate, not just an optional extra (NUnit, async all the way, mirroring `zap-baseline`'s parsed-report gate):

```csharp
// Tests/DependencyVulnerabilityTests.cs
using System.Text.Json;
using NUnit.Framework;

[TestFixture]
public class DependencyVulnerabilityTests
{
    [Test]
    public async Task Should_have_no_high_severity_cves_When_dependencies_scanned()
    {
        using var doc = await DependencyScanReport.RunVulnerableScanAsync();   // attaches JSON to Allure

        var high = new List<string>();
        foreach (var project in doc.RootElement.GetProperty("projects").EnumerateArray())
        {
            if (!project.TryGetProperty("frameworks", out var frameworks)) continue;
            foreach (var fw in frameworks.EnumerateArray())
            foreach (var listName in new[] { "topLevelPackages", "transitivePackages" })
            {
                if (!fw.TryGetProperty(listName, out var packages)) continue;
                foreach (var pkg in packages.EnumerateArray())
                foreach (var vuln in pkg.GetProperty("vulnerabilities").EnumerateArray())
                {
                    var severity = vuln.GetProperty("severity").GetString();
                    if (severity is "High" or "Critical")
                        high.Add($"{pkg.GetProperty("id").GetString()} ({severity})");
                }
            }
        }
        Assert.That(high, Is.Empty, "High+ CVEs in the dependency tree");   // one logical assertion = the gate
    }
}
```

The Java/TS siblings parse their own tool's JSON the same way. Test name `Should_X_When_Y`.

## CI wiring — the gate, the remediation complement

```yaml
# .github/workflows/sca.yml — cross-link qa-ci-pipelines-dotnet
name: Dependency Scan (SCA)
on: [pull_request]

jobs:
  dependency-review:                     # PR-diff gate: fails on vulnerable deps the PR ADDS
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/dependency-review-action@v4
        with: { fail-on-severity: high }

  dotnet-sca:                            # full-tree SCA gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-dotnet@v4
        with: { dotnet-version: '8.0.x' }
      # NuGet audit gate (Directory.Build.props: NuGetAuditLevel=high + WarningsAsErrors NU190x):
      - run: dotnet restore       # NU190x → errors → fails the build (the build-integrated gate)
      # Explicit scan as report/parse-and-assert:
      - if: always()
        run: dotnet list package --vulnerable --include-transitive --format json > vulnerable.json
      - if: always()
        uses: actions/upload-artifact@v4
        with: { name: dotnet-sca-report, path: vulnerable.json }
```

- **`dependency-review-action`** — the **PR-diff** gate (fails on deps the PR *adds* above
  `fail-on-severity`); pairs with the full-tree NuGet audit.
- **Remediation complement** — **Dependabot / Renovate** *raise PRs to bump* vulnerable packages; SCA
  *gates*. Wire both: the gate stops new CVEs landing, the bot fixes the backlog.
- **No NVD cache needed** for the native tools (they query the GitHub advisory feed) — but if you use OWASP
  Dependency-Check for cross-stack parity, **cache its NVD DB** (slow cold download — see the Java sibling).

## Anti-patterns

- **Assuming `dotnet list package --vulnerable` fails the build.** It always exits **0**. *Fix:* gate via
  **NuGet audit + `WarningsAsErrors` (NU190x)** or a **parse-and-assert** step — never rely on its exit
  code.
- **Treating SCA as a substitute for DAST (or vice-versa).** A clean dependency tree says nothing about a
  missing security header; a clean ZAP baseline says nothing about a vulnerable transitive package. *Fix:*
  run **both** `zap-baseline` + `dependency-scanning` — orthogonal layers.
- **Scanning without `--include-transitive`.** Misses most real CVEs. *Fix:* always
  `--include-transitive`; `NuGetAuditMode=all`.
- **Blanket `<NoWarn>NU1901;NU1902;...</NoWarn>` to go green.** Mutes every future CVE. *Fix:* a scoped,
  **ticketed** `<NuGetAuditSuppress Include="<advisory-url>" />` for the specific advisory.
- **Suppressions with no ticket / re-review.** They rot. *Fix:* every suppression names a ticket + a
  re-review date in the comment; audit the list each release (.NET has no native `until=` — emulate it).
- **Gating without remediating.** The build stays red and the team disables the gate. *Fix:* pair the gate
  with Dependabot/Renovate.
- **`.Result`/`.Wait()` when shelling out to parse the scan.** *Fix:* `await proc.WaitForExitAsync()` /
  `await ReadToEndAsync()` — async all the way (global rule).
- **`NuGetAuditLevel=low` on day one of a legacy tree.** Everything fails; the gate gets bypassed. *Fix:*
  start at `critical`, clear the backlog, ratchet to `high`.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Examples**.

## Rules (hard constraints)

- The gate is the **build failing** — **NuGet audit `NU190x` → `WarningsAsErrors`** *or* a
  **parse-and-assert** step (because `dotnet list package --vulnerable` always exits 0). One logical
  assertion per test; test names `Should_X_When_Y`; **async all the way** when shelling out (no
  `.Result`/`.Wait()`).
- Scan **direct + transitive** deps (`--include-transitive` / `NuGetAuditMode=all`) against a CVE feed —
  transitive coverage is the point. SCA reads the **build graph** (no running app — contrast DAST).
- Triage with a **ticketed `<NuGetAuditSuppress>`** scoped to the specific advisory URL (never blanket
  `NoWarn`), with a ticket + re-review date. Gate **new** CVEs; shrink the list, never grow it (the
  `axe-playwright`/`zap-baseline` discipline). Prefer a **direct pin to the patched (transitive) version** over suppressing.
- Emit **JSON**: attach to **Allure**, upload as a CI artifact, optionally convert to **SARIF** for GitHub
  code-scanning.
- Pair the **gate** with **remediation** (Dependabot/Renovate) and the **`dependency-review-action`**
  PR-diff gate. A clean SCA ≠ "secure" — **run DAST too**: orthogonal layers.

## Cross-references

- `qa-security-testing-dependency-scanning-java` — same skill, Java / **OWASP Dependency-Check Gradle
  plugin** (`failBuildOnCVSS`, suppression XML with `until=`); the **canonical** sibling and the cross-stack
  throughline.
- `qa-security-testing-dependency-scanning-typescript` — same skill, TS / `npm audit` (`--audit-level`,
  `--json`, `overrides`/`.nsprc`).
- `qa-security-testing-zap-baseline-dotnet` — the **DAST** sibling that opened the `security-testing`
  family: ZAP probes the **running app's HTTP surface**; SCA reads your **build graph**. Orthogonal layers
  — **run both** (together they close Phase 2).
- `qa-accessibility-testing-dotnet` — the **ticketed-baseline triage** discipline
  reused here for the suppression list (gate new findings, document every suppression with a ticket).
- `qa-ci-pipelines-dotnet` — the gate step, `dependency-review-action`, artifact upload.
- `qa-allure-reporting-dotnet` — attach the `dotnet list package --vulnerable --format json` report to the
  run.
