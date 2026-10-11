---
name: dependency-scan
description: Use when wiring SCA (dependency-vulnerability scanning) as a CI gate for a Java build — OWASP Dependency-Check Gradle plugin scanning the direct + transitive tree against CVE feeds, failing above a CVSS threshold, with a ticketed suppression file. Triggers: "fail the build on vulnerable dependencies", "add dependency scanning", "gate new CVEs". Not for runtime DAST → `security-testing/passive-scan`.
---

# Security Testing — Dependency Scanning / SCA (Java)

**Software Composition Analysis (SCA)** answers a different security question from DAST: not "is the
running app exploitable over HTTP?" (that's ZAP, `passive-scan`) but **"does my dependency tree contain library
versions with known CVEs?"** It reads your **build graph / lockfile** — direct *and* **transitive**
dependencies — matches each component+version against a vulnerability feed (the **NVD**, GitHub Advisory
Database, OSV), and **fails the build** when a finding crosses a severity/CVSS threshold. It needs **no
running app** (contrast DAST): it's a static, fast, every-PR pipeline gate.

> **⚠️ SCA vs DAST — two orthogonal layers, run both.** ZAP scans the **running app's HTTP
> surface** (missing headers, cookie flags, info leaks). SCA scans your **dependency tree** (vulnerable
> `log4j`, `jackson`, transitive `commons-text`…). A clean ZAP baseline says nothing about a Log4Shell in
> your classpath; a clean SCA says nothing about a missing CSP header. **Together they close Step 2's
> `security-testing` family — wire both gates.**

> **Stack-native first — and why Java is canonical for this node.** Unlike `passive-scan` (one language-agnostic
> Docker tool), SCA is **stack-native**: each ecosystem has its own first-class auditor (`npm audit`,
> `dotnet list package --vulnerable`). But **OWASP Dependency-Check** is the cross-stack common denominator,
> and its richest, most first-class form is the **Gradle plugin** — a real build task with a proper
> severity gate (`failBuildOnCVSS`), a structured suppression format (`<suppress>` XML with notes + expiry),
> and NVD-DB caching. So **Java leads** (same reasoning as `wiremock` picking Java for WireMock: lead with the
> stack where the tool is most authentic), and the TS/.NET siblings **translate the discipline** —
> severity-gate, ticketed-suppress, fail-the-build, report→Allure — onto their native tools (`npm audit`,
> `dotnet list package --vulnerable` + NuGet audit), each noting Dependency-Check as the shared option.

## Decision matrix — where SCA fits

| Need | Use | Why |
|------|-----|-----|
| Gate the **dependency tree** (direct + transitive CVEs) in every PR | **this skill** | Static, fast, no running app; fails the build above a CVSS threshold |
| Scan the **running app's HTTP surface** (headers, cookies, info leaks) | passive-scan | DAST probes live traffic — orthogonal layer; run both |
| **Remediate** an out-of-date / vulnerable dep automatically | Dependabot / Renovate | They *raise PRs to bump*; SCA *gates*. Complementary — gate + auto-fix |
| Gate only the deps a PR **adds/changes** (diff-scoped) | `dependency-review-action` | PR-diff gate on GitHub; pairs with the full-tree scan here |

**Rule of thumb:** SCA is your **dependency-tree CVE gate**; it complements — does not replace — DAST
(`passive-scan`). Pair the gate with a *remediation* tool (Dependabot/Renovate) so findings get fixed, not just
flagged.

## Setup — the OWASP Dependency-Check Gradle plugin

```kotlin
// build.gradle.kts
plugins {
    java
    id("org.owasp.dependencycheck") version "10.0.4"   // the SCA gate task
}

dependencyCheck {
    failBuildOnCVSS = 7.0f                 // ❌ fail the build on any CVE with CVSS ≥ 7.0 (High+)
    failOnError = true                     // fail if the analyzer itself errors (don't silently pass)
    suppressionFile = "config/dependency-check/suppressions.xml"  // ticketed allow-list (below)
    formats = listOf("HTML", "JSON", "SARIF")   // report formats → Allure + GitHub code-scanning
    // The NVD API is rate-limited without a key. Provide one via env, lazily — never hard-code it.
    nvd.apiKey = System.getenv("NVD_API_KEY")
    nvd.datafeedUrl = System.getenv("NVD_DATAFEED_URL")  // optional mirror for air-gapped/CI caching
}
```

```bash
./gradlew dependencyCheckAnalyze      # the gate task — scans, reports, fails above failBuildOnCVSS
./gradlew dependencyCheckUpdate       # refresh the local NVD DB cache only (no scan)
./gradlew dependencyCheckPurge        # drop the cached DB (rarely needed)
```

> **Maven variant.** The same engine ships as `org.owasp:dependency-check-maven`; bind the `check` goal,
> set `<failBuildOnCVSS>7</failBuildOnCVSS>` and `<suppressionFile>` in the plugin `<configuration>`, run
> `mvn verify` (or `mvn org.owasp:dependency-check-maven:check`). Identical discipline, different build
> tool. New projects use Gradle Kotlin DSL per house default.

The plugin's three tasks: **`dependencyCheckAnalyze`** (the scan + gate), **`dependencyCheckUpdate`**
(refresh the NVD cache), **`dependencyCheckPurge`** (clear it). `dependencyCheckAggregate` rolls a
multi-module build into one report.

## The SCA model — scan direct + transitive deps against a CVE feed

`dependencyCheckAnalyze` walks the **resolved** dependency graph — every JAR Gradle puts on the configured
classpaths, **including transitive ones you never declared** — identifies each by CPE/coordinates, and
matches it against the **National Vulnerability Database** (plus GitHub Advisory / sonatype OSS Index if
configured). Each match is a CVE with a **CVSS score** (0.0–10.0). The defining traits:

- **Transitive coverage is the whole point.** You declared `spring-boot-starter-web`; it dragged in dozens
  of transitive JARs. SCA flags a CVE in a transitive `snakeyaml` you never typed. (Contrast a naive
  "scan my `dependencies {}` block" — that misses exactly the deps you didn't choose.)
- **No running app.** Lockfile/build-graph-driven; runs in seconds-to-minutes (the NVD download is the slow
  part — cache it; see below). Contrast DAST, which needs a deployed target.
- **The gate is a CVSS threshold** — `failBuildOnCVSS = 7.0f` fails on High+ (7.0–10.0). Pick the
  threshold deliberately: start lenient (e.g. 9.0 Critical-only) and ratchet down as you clear the backlog.

## The build-fail gate — `failBuildOnCVSS`

The gate is the **build task failing**: when any in-scope dependency has a CVE with CVSS ≥
`failBuildOnCVSS`, `dependencyCheckAnalyze` throws and **Gradle exits non-zero** — same build-fail
mechanism as `passive-scan`'s process exit code, expressed as a Gradle task failure.

| `failBuildOnCVSS` | Fails on | Typical use |
|-------------------|----------|-------------|
| `0.0f` | **any** CVE (default — every finding fails) | only once the tree is clean; usually too strict to start |
| `7.0f` | **High+** (7.0–10.0) | common starting gate |
| `9.0f` | **Critical only** (9.0–10.0) | initial gate on a legacy tree with a backlog |
| `11.0f` | nothing (report-only) | observe-first mode before turning the gate on |

CVSS → severity mapping (CVSS v3): **None** 0.0 · **Low** 0.1–3.9 · **Medium** 4.0–6.9 · **High** 7.0–8.9
· **Critical** 9.0–10.0. The TS/.NET siblings express the same map as `npm audit --audit-level=high` /
NuGet `NuGetAuditLevel`.

## The triage gate — ticketed suppression XML (front and center, like `axe-playwright` / `passive-scan`)

A real project's first SCA run lights up — including findings you **cannot fix today** because they're in a
**transitive** dependency or are false positives. Gating on *every* CVE with no triage trains the team to
mute the gate. The disciplined approach is the **ticketed suppression file**: each `<suppress>` carries a
specific CVE/coordinate, a **`<notes>` ticket + reason**, and ideally an **`until=` expiry** — the same
allow-list discipline as `qa-java:accessibility-testing` and `passive-scan`'s `rules.tsv`, ported
to SCA.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- config/dependency-check/suppressions.xml -->
<suppressions xmlns="https://jeremylong.github.io/DependencyCheck/dependency-suppression.1.3.xsd">

    <!-- Accepted-risk: transitive CVE we can't bump yet; ticketed + time-boxed so it can't rot. -->
    <suppress until="2026-09-01Z">
        <notes><![CDATA[JIRA-4210: CVE in transitive snakeyaml via spring-boot-starter;
                        upstream fix lands in Boot 3.4 (due Q3). Re-review at expiry.]]></notes>
        <packageUrl regex="true">^pkg:maven/org\.yaml/snakeyaml@.*$</packageUrl>
        <cve>CVE-2022-1471</cve>
    </suppress>

    <!-- Documented false positive: the CPE matcher mis-identified our own artifact. -->
    <suppress>
        <notes><![CDATA[JIRA-4211: false positive — CPE collision with an unrelated 'commons' product.]]></notes>
        <gav regex="true">^com\.myorg/internal-commons@.*$</gav>
        <cve>CVE-2017-XXXX</cve>
    </suppress>

</suppressions>
```

- Match by **`packageUrl`** (PURL, preferred), **`gav`**, **`sha1`**, or **`cpe`**; scope the suppression
  to **a specific `<cve>`** (or `<vulnerabilityName>`) — never a blanket suppress-the-whole-dependency.
- **`until="YYYY-MM-DDZ"`** time-boxes the suppression: after that date it stops applying and the CVE
  fails the build again — forcing a re-review instead of a permanent mute. Use it for every accepted-risk.
- **Discipline (reuse `axe-playwright` / `passive-scan`):** gate **new** CVEs; `<suppress>` only *documented, ticketed*
  accepted-risk or false-positives; **shrink** the file over time, never grow it to make a real finding go
  away. Every entry's `<notes>` names a ticket.

### The transitive-dep reality

The hard part of SCA: the vulnerable library is often **transitive** — you didn't declare it and can't just
bump its line. Three honest responses, in order of preference:

1. **Force the version** — pin the transitive dep to a fixed release via a constraint, so the bump is real:
   ```kotlin
   dependencies {
       constraints {
           implementation("org.yaml:snakeyaml:2.2") {
               because("CVE-2022-1471 — force the patched transitive version (JIRA-4210)")
           }
       }
   }
   ```
   (Maven: `<dependencyManagement>`; npm: `overrides`; .NET: a direct top-level `<PackageReference>` to the
   patched version — the sibling files show each.)
2. **Bump the parent** that pulls it in (e.g. the Spring Boot BOM), if a patched line exists.
3. **Suppress-with-ticket + `until=`** *only* when neither is possible yet (upstream hasn't shipped a fix) —
   and revisit at expiry. The `force`/override is a real fix; the suppression is a tracked deferral.

## Report → Allure + SARIF / GitHub code-scanning

Dependency-Check writes `dependency-check-report.{html,json,sarif}` to `build/reports/`. Attach the HTML +
a parsed summary to Allure so a failing run names the CVEs without re-scanning, and feed the **SARIF** to
GitHub code-scanning so findings show inline on the PR (cross-link `qa-java:test-reports`):

```java
// src/test/java/security/DependencyCheckReport.java
import io.qameta.allure.Allure;
import io.qameta.allure.AttachmentOptions;
import java.io.InputStream;
import java.nio.file.*;

/** Attach the Dependency-Check HTML report + a readable CVE summary to Allure. */
public final class DependencyCheckReport {
    private static final Path REPORT_DIR = Path.of("build", "reports");

    public static void attach() throws Exception {
        Path html = REPORT_DIR.resolve("dependency-check-report.html");
        if (Files.exists(html)) {
            try (InputStream content = Files.newInputStream(html)) {
                Allure.attachment("dependency-check.html", "text/html", content,
                        AttachmentOptions.withFileExtension("html"));
            }
        }
    }
}
```

- **Allure** — attach the HTML report (cross-link `qa-java:test-reports`).
- **SARIF → GitHub code-scanning** — `formats = listOf(..., "SARIF")`, then
  `github/codeql-action/upload-sarif` surfaces each CVE inline on the PR diff.
- **CI artifact** — upload `build/reports/dependency-check-report.*` (cross-link
  `qa-java:ci-pipelines`).

## Optional parse-and-assert test (the programmatic path)

SCA is primarily a **build/CI gate** (`./gradlew dependencyCheckAnalyze`). When you want a test-level
assertion independent of the Gradle gate — e.g. a custom threshold, or to surface the count in your test
report — parse the JSON report (TestNG + AssertJ, mirroring `passive-scan`'s parsed-report gate):

```java
// src/test/java/security/DependencyVulnerabilityTest.java
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.testng.annotations.Test;
import java.nio.file.*;
import java.util.*;
import static org.assertj.core.api.Assertions.assertThat;

public class DependencyVulnerabilityTest {

    @Test
    public void Should_have_no_high_severity_cves_When_dependencies_scanned() throws Exception {
        // Assumes ./gradlew dependencyCheckAnalyze ran first (CI step) and wrote the JSON report.
        Path report = Path.of("build", "reports", "dependency-check-report.json");
        JsonNode root = new ObjectMapper().readTree(Files.readString(report));

        List<String> high = new ArrayList<>();
        for (JsonNode dep : root.path("dependencies")) {
            for (JsonNode vuln : dep.path("vulnerabilities")) {
                double cvss = vuln.path("cvssv3").path("baseScore").asDouble(
                        vuln.path("cvssv2").path("score").asDouble(0.0));
                if (cvss >= 7.0) {
                    high.add(vuln.path("name").asText() + " in " + dep.path("fileName").asText());
                }
            }
        }
        assertThat(high).as("High+ CVEs (CVSS >= 7.0) in the dependency tree").isEmpty();
    }
}
```

The `.NET`/TS siblings parse their own tool's JSON (`dotnet list package --vulnerable --format json` /
`npm audit --json`) the same way. One logical assertion; test name `Should_X_When_Y`.

## CI wiring — the gate, the NVD cache, the remediation complement

```yaml
# .github/workflows/sca.yml — cross-link qa-java:ci-pipelines
name: Dependency Scan (SCA)
on: [pull_request]

jobs:
  # PR-diff gate: fails on vulnerable deps the PR ADDS — fast first line.
  dependency-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/dependency-review-action@v4
        with:
          fail-on-severity: high          # gate the diff on High+

  # Full-tree SCA gate via Dependency-Check.
  owasp-dependency-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-java@v4
        with: { distribution: temurin, java-version: '21' }
      # Cache the NVD DB — it is SLOW to download fresh; a cold run can take many minutes.
      - uses: actions/cache@v4
        with:
          path: ~/.gradle/dependency-check-data
          key: nvd-${{ runner.os }}-${{ hashFiles('**/*.gradle.kts') }}
          restore-keys: nvd-${{ runner.os }}-
      - run: ./gradlew dependencyCheckAnalyze
        env:
          NVD_API_KEY: ${{ secrets.NVD_API_KEY }}   # secret via env — lazily, never hard-coded
      - if: always()
        uses: actions/upload-artifact@v4
        with: { name: dependency-check-report, path: build/reports/dependency-check-report.* }
      - if: always()
        uses: github/codeql-action/upload-sarif@v3
        with: { sarif_file: build/reports/dependency-check-report.sarif }
```

- **`dependency-review-action`** — the **PR-diff** gate (fails on deps the PR *adds* above
  `fail-on-severity`); pairs with the full-tree Dependency-Check scan.
- **NVD cache** — the NVD download is the slow part of a cold run (minutes). Cache
  `~/.gradle/dependency-check-data`; pass `NVD_API_KEY` (env, lazy) to raise the rate limit. **A real
  gotcha worth budgeting for.**
- **Remediation complement** — **Dependabot / Renovate** *raise PRs to bump* vulnerable deps; SCA *gates*.
  Wire both: the gate stops new CVEs landing, the bot fixes the backlog.

## Anti-patterns

- **Treating SCA as a substitute for DAST (or vice-versa).** A clean dependency tree says nothing about a
  missing security header; a clean ZAP baseline says nothing about Log4Shell on your classpath. *Fix:* run
  **both** `passive-scan` + `dependency-scan` — they're orthogonal layers.
- **Scanning only declared (direct) deps.** Most real CVEs arrive **transitively**. *Fix:* Dependency-Check
  scans the resolved graph by default — don't disable transitive analysis.
- **Blanket-suppressing a whole dependency to go green.** Hides every future CVE in it. *Fix:* `<suppress>`
  a **specific `<cve>`** with a `<notes>` ticket and an `until=` expiry.
- **Permanent suppressions with no expiry.** They rot into forgotten accepted-risk. *Fix:* `until=` on every
  accepted-risk entry so it re-fails and forces a re-review.
- **No NVD cache in CI.** Every run re-downloads the DB → slow, flaky, rate-limited. *Fix:* cache
  `dependency-check-data` + an `NVD_API_KEY` (env).
- **Gating without remediating.** The build stays red and the team disables the gate. *Fix:* pair the gate
  with Dependabot/Renovate so findings get *fixed*.
- **Hard-coding the NVD API key.** *Fix:* env var, read lazily — never in `build.gradle.kts` or committed
  config (global rule: no secrets in code).
- **`failBuildOnCVSS = 0` on day one of a legacy tree.** Everything fails; the gate gets bypassed. *Fix:*
  start at 9.0 (Critical-only), clear the backlog, then ratchet down to 7.0.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Examples**.

## Rules (hard constraints)

- The gate is the **build failing** on a CVSS threshold (`failBuildOnCVSS`), optionally plus a
  **parsed-report** assertion. One logical assertion per test; test names `Should_X_When_Y`.
- Scan **direct + transitive** deps against a CVE feed — transitive coverage is the point. SCA reads the
  **build graph** (no running app — contrast DAST).
- Triage with a **ticketed suppression file**: scope each `<suppress>` to a specific `<cve>`, with a
  `<notes>` ticket and an **`until=` expiry**. Gate **new** CVEs; shrink the file, never grow it (the
  `axe-playwright`/`passive-scan` discipline). Prefer **forcing the patched (transitive) version** over suppressing.
- **Cache the NVD DB** in CI (slow cold download) and pass the **`NVD_API_KEY` via env, lazily** — never
  hard-coded (global rule: no secrets in code).
- Emit **HTML/JSON/SARIF**: attach to **Allure**, upload as a CI artifact, feed **SARIF** to GitHub
  code-scanning.
- Pair the **gate** with a **remediation** tool (Dependabot/Renovate) and the **`dependency-review-action`**
  PR-diff gate. A clean SCA ≠ "secure" — **run DAST too**: SCA and DAST are orthogonal layers.

## Cross-references

- `qa-typescript:dependency-scan` — same skill, TS / `npm audit` (`--audit-level`,
  `--json`, `npm audit fix`, `overrides`/`.nsprc`; Dependency-Check as the shared option).
- `qa-dotnet:dependency-scan` — same skill, .NET / `dotnet list package --vulnerable
  --include-transitive` + NuGet audit (`<NuGetAudit>`, `NuGetAuditLevel`).
- `qa-java:passive-scan` — the **DAST** sibling that opened the `security-testing`
  family: ZAP probes the **running app's HTTP surface**; SCA reads your **dependency tree**. Orthogonal
  layers — **run both** (together they close Step 2).
- `qa-java:accessibility-testing` — the **ticketed-baseline triage** discipline reused
  here for the suppression file (gate new findings, document every suppression with a ticket).
- `qa-java:ci-pipelines` — the gate step, `dependency-review-action`, NVD-cache, artifact +
  SARIF upload.
- `qa-java:test-reports` — attach the Dependency-Check HTML/JSON report to the run.
