---
name: passive-scan
description: Use when adding an OWASP ZAP baseline (passive) DAST scan as a CI gate for a Java pipeline. Triggers "add a DAST gate to CI". Not for active injection scans (active-scan).
disable-model-invocation: true
---

# Security Testing — OWASP ZAP Baseline Scan (Java / TestNG)

The Java port of the canonical `qa-typescript:passive-scan`. Same baseline scan model,
same exit-code build gate, same ticketed-triage discipline — re-expressed for a JVM shop, which makes the
honest shape of this node plain.

OWASP **ZAP** (Zed Attack Proxy) is the de-facto open-source DAST scanner. The **baseline scan**
(`passive-scan.py`, in the `ghcr.io/zaproxy/zaproxy` Docker image) spiders a **running** app for a short
bounded time, runs ZAP's **passive** rules — no attack payloads — and reports alerts by risk, exiting
**non-zero to fail the build** when alerts cross a threshold. The canonical *shift-left DAST gate in the
pipeline*: fast, safe against a deployed/ephemeral env, CI-native.

> **⚠️ Baseline (passive) vs full scan (active).** `passive-scan.py` runs **passive** rules only — it
> observes spidered/proxied traffic and flags what it can *see* (missing `Content-Security-Policy`,
> `Set-Cookie` without `Secure`/`HttpOnly`, verbose `Server` headers, info leaks). It sends **no attack
> payloads**, so it's safe and fast (~1–few min) and the right PR gate. `zap-full-scan.py` adds the
> **active** scanner that *injects* SQLi/XSS/traversal payloads — it **mutates state and must never run
> against production or a shared environment**. This skill is the **baseline** gate; reach for the full
> scan only against a throwaway env you own, on a slower cadence.

> **⚠️ Tool-invoked-via-Docker — there is no Java ZAP SDK.** The baseline scan is a Docker invocation: Java **invokes the `zaproxy` image as a subprocess** (`ProcessBuilder` → `docker run … passive-scan.py`) and **parses the JSON report** (Jackson) to gate the pipeline. There is no Maven/Gradle artifact to embed; `org.zaproxy:zap-clientapi` drives a long-running ZAP daemon, a heavier, different model.

## Decision matrix — where ZAP baseline fits

| Need | Use | Why |
|------|-----|-----|
| Passive DAST gate on a **running** app in every PR (headers, cookie flags, info leaks) | **this skill** | Safe (no payloads), fast, CI-native; exits non-zero to fail the build |
| Deep active attack testing (SQLi/XSS/traversal payloads) on a throwaway env | `zap-full-scan.py` (out of scope here) | Active scanner mutates state — never prod/shared; slower cadence |
| **Dependency / library** CVEs (vulnerable JARs, transitive CVEs) | dependency-scan | SCA reads your build graph; ZAP scans running HTTP — orthogonal layers |
| Per-component **accessibility** rule assertions | axe-playwright | Different concern; same *ticketed-baseline triage* discipline applies |

## Setup — no Maven/Gradle artifact, just Docker (and optionally the GitHub Action)

There is no artifact for the scan — you need **Docker** on the runner and the ZAP image:

```bash
docker pull ghcr.io/zaproxy/zaproxy:stable      # the image carrying passive-scan.py
```

Your test project needs only TestNG, AssertJ and a JSON parser (Jackson), plus Testcontainers if the test spins
up the SUT. Their versions are the ones the project's build already pins.

For the CI-first path you need **no local artifact** — the `zaproxy/action-baseline` Action wraps the image.

## The baseline scan model — spider, passive-scan, report, exit-code

`passive-scan.py -t <targetUrl>` does three things against an **already-running** app: **spider** for
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

`passive-scan.py` maps alerts to a process exit code — **the build-fail mechanism**, identical across all
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
ticket + reason** — the same allow-list discipline as `qa-java:accessibility-testing`
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
optionally opens a tracking issue (cross-link `qa-java:ci-pipelines`):

```yaml
# .github/workflows/passive-scan.yml
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
          target: 'http://localhost:8080'
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a -j'                # alpha rules + Ajax spider
          fail_action: true                   # fail the job on alerts (else relies on rules→FAIL)
          allow_issue_writing: true
          artifact_name: zap_baseline_report
          token: ${{ secrets.GITHUB_TOKEN }}
```

`fail_action: true` fails on any alert; the default `false` fails only on `FAIL`-promoted rules via the exit code. The other inputs are in the Action's README. The Java pipeline calls the same Action.

> **Wait on a condition, never a sleep.** The app must be **ready** before the scan or you get
> false-clean/exit-3 results. Use `docker compose up --wait` or a Testcontainers wait strategy — never
> `Thread.sleep`. Global rule: no fixed waits.

## Running the scan — the programmatic path (Docker via `ProcessBuilder` + parse JSON)

To drive the scan from a TestNG test (assert programmatically, attach to Allure, gate on parsed counts),
invoke the image as a one-shot container and parse the JSON report with Jackson. This is the Java
re-expression of the TS `child_process` client:

```java
// support/ZapBaseline.java — the Docker-port client: one-shot container + JSON parse (no SDK exists)
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.*;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

public final class ZapBaseline {
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private ZapBaseline() {}

    public record ZapAlert(String pluginId, String alert, String riskCode, String riskDesc, String count) {}
    public record ZapResult(int exitCode, List<ZapAlert> alerts, Path reportJsonPath, Path reportHtmlPath) {}

    /**
     * Runs {@code passive-scan.py} in the zaproxy container against a running target; returns the exit
     * code (the gate: 0 clean · 1 FAIL · 2 WARN-only · 3 infra) plus the parsed alerts.
     */
    public static ZapResult run(String targetUrl, Path rulesTsvPath) throws Exception {
        Path work = Files.createTempDirectory("zap-");
        Process proc = new ProcessBuilder(
                "docker", "run", "--rm", "--network", "host",
                "-v", work + ":/zap/wrk:rw",
                "-v", rulesTsvPath.toAbsolutePath() + ":/zap/wrk/rules.tsv:ro",
                "ghcr.io/zaproxy/zaproxy:stable",
                "passive-scan.py",
                "-t", targetUrl,
                "-c", "rules.tsv",            // ticketed triage gate (relative to /zap/wrk)
                "-J", "report.json",
                "-r", "report.html",
                "-a")                         // include alpha passive rules
            .redirectErrorStream(true)
            .start();
        if (!proc.waitFor(10, TimeUnit.MINUTES)) {   // bounded wait, not Thread.sleep
            proc.destroyForcibly();
            throw new IllegalStateException("passive-scan timed out");
        }

        Path reportJsonPath = work.resolve("report.json");
        JsonNode root = MAPPER.readTree(Files.readAllBytes(reportJsonPath));
        List<ZapAlert> alerts = new ArrayList<>();
        for (JsonNode site : root.path("site")) {
            for (JsonNode a : site.path("alerts")) {
                alerts.add(new ZapAlert(
                    a.path("pluginid").asText(),
                    a.path("alert").asText(),
                    a.path("riskcode").asText(),   // "0" info … "3" high
                    a.path("riskdesc").asText(),
                    a.path("count").asText()));
            }
        }
        return new ZapResult(proc.exitValue(), alerts, reportJsonPath, work.resolve("report.html"));
    }
}
```

```java
// tests/ZapBaselineTest.java
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.wait.strategy.Wait;
import org.testng.annotations.*;
import java.nio.file.Path;
import static org.assertj.core.api.Assertions.assertThat;

public class ZapBaselineTest {
    private GenericContainer<?> app;
    private String target;

    @BeforeClass
    public void startApp() {
        app = new GenericContainer<>("myorg/web:latest")
            .withExposedPorts(8080)
            .waitingFor(Wait.forHttp("/health").forPort(8080));
        app.start();
        target = "http://localhost:" + app.getMappedPort(8080);
    }

    @AfterClass(alwaysRun = true)
    public void stopApp() { if (app != null) app.stop(); }

    @Test
    public void Should_pass_baseline_When_no_FAIL_level_alerts() throws Exception {
        var result = ZapBaseline.run(target, Path.of(".zap/rules.tsv"));
        ZapReportAttachment.attach(result);            // attach BEFORE asserting, so a failure carries the report

        assertThat(result.exitCode()).isNotEqualTo(1); // one logical assertion = the build gate
    }

    @Test
    public void Should_have_no_high_risk_alerts_When_baseline_scanned() throws Exception {
        var result = ZapBaseline.run(target, Path.of(".zap/rules.tsv"));
        ZapReportAttachment.attach(result);
        var high = result.alerts().stream().filter(a -> a.riskCode().equals("3")).toList();  // riskcode 3 = High
        assertThat(high).isEmpty();                    // assert on the parsed report, not just the exit code
    }
}
```

Two complementary gates: the **exit-code gate** (`isNotEqualTo(1)` — let `-c rules.tsv` decide what
`FAIL`s, all policy in one ticketed file) and the **parsed-report gate** (`isEmpty()` on a `riskCode`/
`pluginId` filter — a test-level assertion independent of the rules file). The TS canonical / .NET sibling
parse the same `site[].alerts[]` shape.

## Authenticated scans and Allure reporting

Baseline's sweet spot is the unauthenticated surface. A scan behind a login (`-n` context, `-z` auth options) or the Allure attachment of the ZAP report (`ZapReportAttachment`) → read `references/auth-and-reporting.md`.

## Anti-patterns

- **Looking for a Maven/Gradle ZAP SDK for the gate.** There isn't one — the baseline is a Docker command.
  (`org.zaproxy:zap-clientapi` drives a long-running daemon, a heavier model.) *Fix:* invoke the image via
  `ProcessBuilder` (or the Action) and parse the JSON with Jackson.
- **Running `zap-full-scan.py` (active) against prod/shared env.** It injects payloads and mutates state.
  *Fix:* use the **baseline** (passive) gate; reserve the full scan for a throwaway env you own.
- **Scanning before the app is ready** (`Thread.sleep` then scan). Races startup → false-clean/exit 3.
  *Fix:* `compose up --wait` / a Testcontainers wait strategy — never `Thread.sleep`.
- **`Thread.sleep` to wait on the subprocess.** *Fix:* `proc.waitFor(timeout, unit)` — a bounded wait.
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
