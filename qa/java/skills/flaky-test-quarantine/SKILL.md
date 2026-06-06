---
name: qa-flaky-test-quarantine-java
description: >-
  Detect, retry, **quarantine**, and report flaky tests in a Java 21 / TestNG suite — so an
  intermittently-failing test stops blocking the merge gate **without** being silently deleted or
  retried-to-green forever. Covers the TestNG `IRetryAnalyzer` (bounded re-run of a failed test) applied
  suite-wide via an `IAnnotationTransformer` listener (no per-test edits); Maven Surefire
  `rerunFailingTestsCount` as the build-tool alternative; **quarantine** via TestNG groups
  (`@Test(groups = "flaky")`) excluded from the gate suite and run in a separate **non-gating** job; and the
  **Allure flaky flag** two ways — the explicit `io.qameta.allure.Flaky` annotation (paired with `@Issue`
  for the tracking ticket) and Allure's **history-based auto-detection** (failed→passed→failed across the
  last 5 launches). Triggers: "this test is flaky, stop it blocking the pipeline", "quarantine the flaky
  tests but keep running them", "retry failed tests a couple of times in TestNG", "make Allure flag our
  flaky tests", "set up a flaky-test quarantine lane in CI". Do NOT use for: the .NET stack (use
  qa-flaky-test-quarantine-dotnet), the TypeScript stack (use qa-flaky-test-quarantine-typescript), fixing a
  genuinely-broken test (a deterministic failure is a bug, not flakiness — fix it), writing the tests
  themselves (use qa-ui-test-author-* / qa-api-test-author-*), eventual-consistency waits inside one test
  (use the condition-wait in qa-db-testing-client-java / qa-messaging-testing-*), or full Allure setup (use
  qa-allure-reporting-java).
---

# Flaky-Test Quarantine (Java 21 / TestNG) — **canonical stack**

This is the **canonical** stack of the single-node `qa/java/skills/flaky-test-quarantine/` family, and it leads by
judgment (the "lead where the tool is most authentic" call #22 WireMock / #27 dependency-scanning / #30
Kafka made): TestNG's `IRetryAnalyzer` + `IAnnotationTransformer` is the **richest, most first-class
flaky-handling surface** of the three runners — a suite-wide retry policy with zero per-test edits, plus
native group-based quarantine. The `dotnet` (NUnit `[Retry]` + a custom `IRepeatTest` attribute) and
`typescript` (Playwright `retries` → "flaky" status + Vitest `retry`) siblings are **ported** from this
file — the *moves* are identical; only the runner API and the quarantine filter change.

## What "flaky" means (and what it does not)

A **flaky test** passes and fails **non-deterministically against the same code** — a race, a timing
assumption, an order dependency, a real-but-rare backend hiccup. It is *not*:

- a test that **always** fails on a change → that's a **caught regression**, fix the code;
- a test that **always** fails regardless of the change → that's a **broken test**, fix the test.

> **The discipline this skill encodes.** A retry is a **band-aid**, not a cure. Retrying to green **hides
> real bugs** (a 1-in-3 race is a real bug) and lets new flakiness slip in unnoticed. So the policy is a
> **four-move loop**, not "just add retries":
>
> 1. **Detect** — surface which tests are flaky (Allure history + the "flaky" status), don't guess.
> 2. **Retry — once, bounded** — absorb *true* transients on the gate so one hiccup doesn't fail a clean PR.
> 3. **Quarantine** — move a *known* flaky test out of the **merge gate** into a **non-gating lane** that
>    still runs and reports it, tagged with a **ticket**. The gate stays trustworthy; the flake stays visible.
> 4. **Report & fix-or-delete** — track flaky-rate over time; every quarantined test has an owner and a
>    ticket; quarantine **shrinks**, never grows. A test that can't be de-flaked gets deleted, not left to rot.

## Decision matrix — which move for which situation

| Situation | Move | Mechanism |
|-----------|------|-----------|
| A clean PR occasionally red on a *transient* (network blip, cold cache) | **Retry once** on the gate | `IRetryAnalyzer` (max 1) suite-wide |
| A *known* flaky test, ticketed, not yet fixed | **Quarantine** | `@Test(groups = "flaky")` + `@Flaky` + `@Issue`; excluded from gate, run in non-gating lane |
| A test that fails the same way every run | **Fix the code/test** | Not flakiness — a real bug; no retry, no quarantine |
| A flaky test no one will own/fix | **Delete it** | A test you don't trust and won't fix is worse than no test |
| Need to *know* which tests are flaky | **Detect** | Allure history-based flaky mark + the Retries tab + flaky-rate metric |

**Rule of thumb:** *transient on otherwise-green* → one retry. *Known-flaky, ticketed* → quarantine group +
non-gating lane. *Deterministic failure* → it's a bug, fix it. **Never** crank retries up to mask a real race.

## Stack

- Java 21, TestNG 7.x — **no `Thread.sleep`** anywhere (flakiness is usually *caused* by sleeps; don't fight
  it with more; cross-link the condition-wait in `qa-db-testing-client-java` / `qa-messaging-testing-*`)
- `org.testng:testng` — `IRetryAnalyzer` (the retry hook) + `IAnnotationTransformer` (apply it suite-wide)
- `io.qameta.allure:allure-testng` — the **Retries** tab + the `@Flaky` annotation + history-based detection
  (cross-link `qa-allure-reporting-java` for the full Allure wiring; this skill only adds the flaky pieces)
- Gradle Kotlin DSL — a **gate** `test` task (excludes `flaky`) + a **`flakyQuarantine`** task (`ignoreFailures`)
- Maven Surefire `rerunFailingTestsCount` shown as the **build-tool-level alternative** to `IRetryAnalyzer`

```
src/test/
├── java/quarantine/
│   ├── RetryAnalyzer.java          ← the bounded retry hook (IRetryAnalyzer)
│   └── RetryListener.java          ← applies RetryAnalyzer to every @Test (IAnnotationTransformer)
└── resources/
    ├── META-INF/services/
    │   └── org.testng.ITestNGListener   ← registers RetryListener suite-wide (ServiceLoader)
    └── categories.json             ← an Allure "Known flaky (quarantined)" triage bucket
testng-gate.xml                     ← the merge gate: excludes group "flaky"
testng-quarantine.xml               ← the non-gating lane: includes only group "flaky"
```

## Move 2 — Retry, bounded, suite-wide (`IRetryAnalyzer`)

`IRetryAnalyzer.retry(result)` is called by TestNG **after a `@Test` fails**; return `true` to re-run it.
Keep the cap **low** — `1` on the gate. The cap is the whole safety mechanism: a high cap is how flakiness
gets hidden.

```java
package quarantine;

import org.testng.IRetryAnalyzer;
import org.testng.ITestResult;

/** Re-runs a failed test up to a bounded cap. Default 1 on the gate — NOT a knob to crank to hide bugs. */
public final class RetryAnalyzer implements IRetryAnalyzer {

    // Configurable per task (-Dtest.retry.count=...): 1 on the gate, a little higher in the quarantine lane.
    private static final int MAX_RETRIES = Integer.getInteger("test.retry.count", 1);

    private int attempts = 0;

    @Override
    public boolean retry(ITestResult result) {
        if (attempts < MAX_RETRIES) {
            attempts++;
            return true;   // re-run — TestNG marks the earlier attempt as a retry, not a failure
        }
        return false;      // give up — report the failure honestly
    }
}
```

**Apply it to every test without editing every test** — an `IAnnotationTransformer` listener stamps the
analyzer onto each `@Test` at load time:

```java
package quarantine;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import org.testng.IAnnotationTransformer;
import org.testng.annotations.ITestAnnotation;

/** Stamps RetryAnalyzer onto every @Test suite-wide — no per-test @Test(retryAnalyzer = ...) edits. */
public final class RetryListener implements IAnnotationTransformer {

    @Override
    public void transform(ITestAnnotation annotation, Class<?> testClass,
                          Constructor<?> testConstructor, Method testMethod) {
        // Respect an explicit per-test analyzer if one is already set; otherwise apply the default.
        if (annotation.getRetryAnalyzer() == null) {
            annotation.setRetryAnalyzer(RetryAnalyzer.class);
        }
    }
}
```

Register the listener **suite-wide via ServiceLoader** — one line, no `@Listeners` on every base class.
Put the listener's fully-qualified name in `src/test/resources/META-INF/services/org.testng.ITestNGListener`:

```
quarantine.RetryListener
```

> **Allure + TestNG retries gotcha.** With older `allure-testng`, retried attempts could show up as
> **Skipped** rather than rolled into a **Retries** tab on the test (allure-java issue #452). Use a current
> `allure-testng` (2.2x+); the retried attempts then appear under the test's **Retries** tab and the final
> status is what gates. If you still see "skipped" retries, that's the symptom — bump the adapter.

### Build-tool alternative — Maven Surefire `rerunFailingTestsCount`

If you'd rather keep retry policy in the **build tool** than in test code (e.g. a Maven shop), Surefire
re-runs failures itself and emits `flakyFailure` / `flakyError` elements in the JUnit XML — which Allure and
most CIs render as **flaky**, not failed:

```xml
<plugin>
  <groupId>org.apache.maven.plugins</groupId>
  <artifactId>maven-surefire-plugin</artifactId>
  <configuration>
    <rerunFailingTestsCount>1</rerunFailingTestsCount>   <!-- bounded — same discipline as the analyzer -->
  </configuration>
</plugin>
```

Pick **one** retry mechanism (`IRetryAnalyzer` *or* Surefire rerun), not both — stacking them multiplies the
cap and re-introduces the masking problem. For a Gradle project, `IRetryAnalyzer` is the native choice
(Gradle has no Surefire-style rerun); for Maven, either works.

## Move 3 — Quarantine (TestNG groups + a non-gating lane)

Quarantine = **take a known-flaky test out of the merge gate, but keep running it and reporting it.** TestNG
**groups** are the lever. Tag the test, exclude that group from the gate suite, and run it in a separate
**non-gating** lane.

```java
import io.qameta.allure.Flaky;
import io.qameta.allure.Issue;
import org.testng.annotations.Test;

public class CheckoutTests {

    @Test(groups = "flaky")            // ← out of the gate, into the quarantine lane
    @Flaky                             // ← paints it yellow in Allure even on a green run (see Move 4)
    @Issue("CHECKOUT-871")             // ← the ticket tracking the de-flake — quarantine is NEVER permanent
    public void shouldSettlePaymentWhenGatewayIsSlow() {
        // ... the intermittently-failing assertion, awaiting a real fix under CHECKOUT-871
    }
}
```

**The gate suite excludes `flaky`** — `testng-gate.xml` is what the merge gate runs:

```xml
<!DOCTYPE suite SYSTEM "https://testng.org/testng-1.0.dtd">
<suite name="gate">
  <test name="all-but-quarantined">
    <groups>
      <run><exclude name="flaky"/></run>   <!-- quarantined tests never block the merge -->
    </groups>
    <packages><package name="com.acme.tests"/></packages>
  </test>
</suite>
```

**The quarantine lane runs only `flaky`, and is allowed to fail** — `testng-quarantine.xml`:

```xml
<!DOCTYPE suite SYSTEM "https://testng.org/testng-1.0.dtd">
<suite name="quarantine">
  <test name="quarantined-only">
    <groups>
      <run><include name="flaky"/></run>
    </groups>
    <packages><package name="com.acme.tests"/></packages>
  </test>
</suite>
```

Gradle Kotlin DSL — a **gating** task and a **non-gating** task, each pointed at its suite:

```kotlin
tasks.test {                                            // THE GATE — blocks the merge
    useTestNG { suites("testng-gate.xml") }             // excludes group "flaky"
    systemProperty("test.retry.count", "1")             // one retry to absorb true transients
    systemProperty("allure.results.directory", "build/allure-results")
}

val flakyQuarantine by tasks.registering(Test::class) { // VISIBILITY ONLY — never blocks the pipeline
    useTestNG { suites("testng-quarantine.xml") }       // includes only group "flaky"
    systemProperty("test.retry.count", "3")             // a bit more headroom here; results still reported
    systemProperty("allure.results.directory", "build/allure-results")
    ignoreFailures = true                               // a red quarantine lane does NOT fail the build
}
```

> **Why a *running* quarantine lane, not `@Ignore`/`enabled = false`.** A disabled test rots — the feature
> drifts, the test silently lies, and no one notices when it could be re-enabled. A quarantined test **still
> runs** (off the gate), so you keep its signal, you see when it stabilises (Allure history flips it to
> **Fixed**), and the ticket stays honest. Quarantine is a **waiting room**, not a graveyard.

## Move 4 — Report the flaky flag in Allure (the two ways)

Allure surfaces flakiness **two** ways. Use both: the explicit annotation for tests you've *decided* are
flaky, and history-based detection to *catch* the ones you haven't.

**(a) Explicit — the `@Flaky` annotation.** `io.qameta.allure.Flaky` marks a test result flaky (rendered
yellow) **even when it passes** — so a quarantined test is visibly distinct from a healthy one in every
report. Note `@Flaky` takes **no message** (allure2 issue #338) — pair it with `@Issue("…")` so the *why*
and the tracking ticket travel with it (shown in Move 3).

**(b) Automatic — history-based detection.** With Allure **history enabled** (the `history/` folder carried
across runs — see `qa-allure-reporting-java`), Allure auto-adds the **Flaky** mark when, across the latest
**5 launches**, a test:

1. got **Failed** at some point within those 5 launches, **and**
2. got **Passed** at least once since that failure, **and**
3. is **Failed or Broken** in the **latest** launch.

This is what *catches* flakiness you haven't tagged yet — it turns "I think that one's flaky" into data.
Allure tracks **5 stability marks** off history: **Flaky**, **Retried**, **Fixed** (new pass after a fail),
**Regressed** (new fail after a pass), **Malfunctioned** (new broken). Treat **Retried** + **Flaky** as your
quarantine *candidate* list, and **Fixed** as the signal to lift a test *out* of quarantine.

**A triage bucket in `categories.json`** keeps quarantined/flaky failures from polluting "real" failures.
Drop this into `src/test/resources/categories.json` (the adapter picks it up — see `qa-allure-reporting-java`):

```json
[
  { "name": "Known flaky (quarantined)", "matchedStatuses": ["failed", "broken"],
    "traceRegex": ".*TimeoutException.*|.*ConditionTimeoutException.*|.*StaleElementReferenceException.*" }
]
```

**Track flaky-rate over time, not just per-run.** A single green run proves nothing about a flaky test. The
metric that matters is *flaky-rate* (flaky marks ÷ total tests) trending **down** — wire it into the team's
quality dashboard (`qa/manual/quality-metrics`). A growing quarantine group is a smell: it means you're
tagging faster than you're fixing.

## Anti-patterns

- **Cranking the retry cap to make CI green.** `retry.count = 5` doesn't fix a 1-in-3 race — it hides it,
  and a real 60%-of-the-time bug now passes. *Fix:* cap the gate at **1**; quarantine the rest with a ticket.
- **Retrying a *deterministic* failure.** If it fails every run, retrying just wastes CI minutes before the
  same red. *Fix:* that's a caught regression or a broken test — fix it, don't retry it.
- **`@Ignore` / `enabled = false` as "quarantine".** A disabled test stops running, rots, and lies. *Fix:*
  `@Test(groups = "flaky")` + a non-gating lane that **still runs** it; keep the signal and the history.
- **Quarantine with no ticket / no owner.** An untracked quarantine group only grows. *Fix:* every
  `@Test(groups = "flaky")` carries `@Issue("…")`; review the group every sprint; it must **shrink**.
- **Stacking `IRetryAnalyzer` *and* Surefire `rerunFailingTestsCount`.** The caps multiply; you're back to
  masking. *Fix:* one retry mechanism, one cap.
- **Treating a green retry as proof the test is fine.** A test that needed a retry to pass is, by
  definition, flaky. *Fix:* let Allure mark it (Retries tab / history) and add it to the candidate list.
- **Fighting a sleep-induced flake with more retries.** A `Thread.sleep`-based wait is the *cause*; retries
  paper over it. *Fix:* replace the sleep with a condition-wait (`qa-db-testing-client-java` /
  `qa-messaging-testing-*` use Awaitility), then most "flakiness" disappears.
- **One global retry cap of 3 on the gate "to be safe".** That's the masking knob in disguise. *Fix:* 1 on
  the gate; reserve the higher cap for the non-gating lane where the result doesn't block anyone.

## Examples

**End-to-end: a transient on the gate (auto-retried once) vs a known flaky (quarantined + tracked).**

```java
public class PaymentFlowTests {

    // GATE test — normally deterministic. If a true transient (a cold-start 503) reddens it,
    // RetryAnalyzer (cap 1, applied suite-wide by RetryListener) gives it exactly one more shot.
    @Test
    public void shouldAuthorizePaymentWhenCardIsValid() {
        var result = gateway.authorize(Cards.valid().withAmount(1999).build());  // test-data-builder/java
        assertThat(result.status()).isEqualTo(AuthStatus.APPROVED);              // one logical assertion
    }

    // QUARANTINED test — known to race against the gateway's async settlement webhook.
    // Off the gate (group "flaky"), still run in the quarantine lane, flagged in Allure, ticketed.
    @Test(groups = "flaky")
    @Flaky
    @Issue("PAY-1204")
    public void shouldMarkSettledWhenWebhookArrivesWithinSla() {
        gateway.authorize(Cards.valid().build());
        // the de-flake (PAY-1204) is to wait on the settlement condition, not a fixed window — until then,
        // this lives in quarantine so it can't redden a clean PR.
        var settlement = await().atMost(Duration.ofSeconds(10))
            .until(() -> ledger.settlementFor(orderId), s -> s.state() == SettlementState.SETTLED);
        assertThat(settlement.state()).isEqualTo(SettlementState.SETTLED);
    }
}
```

CI shape (two lanes — cross-link `qa-ci-pipelines-github-actions` for the full workflow):

```yaml
- name: Gate suite (blocks merge)
  run: ./gradlew test                       # testng-gate.xml — excludes "flaky", retry cap 1

- name: Quarantine lane (visibility only)
  if: always()
  run: ./gradlew flakyQuarantine            # testng-quarantine.xml — ignoreFailures, never blocks

- name: Upload Allure results               # both lanes write build/allure-results/
  if: always()
  uses: actions/upload-artifact@v4
  with: { name: allure-results, path: '**/build/allure-results/' }
```

The gate is green if the non-flaky tests pass (one retry absorbed any transient); the quarantine lane's
result is reported in Allure (flaky-flagged, history-tracked) but **never** fails the pipeline.

## Rules (hard constraints)

- **Retry is bounded and low on the gate** — cap **1** via `IRetryAnalyzer` (or Surefire
  `rerunFailingTestsCount = 1`), applied suite-wide through `RetryListener` (`IAnnotationTransformer`). The
  cap is the safety mechanism; never crank it to hide failures.
- **One retry mechanism**, never `IRetryAnalyzer` + Surefire rerun together (caps multiply).
- **Quarantine = group + non-gating lane, never `@Ignore`.** `@Test(groups = "flaky")`, excluded from
  `testng-gate.xml`, run by a `flakyQuarantine` task with `ignoreFailures = true`. The test keeps running.
- **Every quarantined test carries `@Issue("…")`** (an owned ticket) and `@Flaky`. The group **shrinks** over
  time; review it each sprint; a test that can't be de-flaked is **deleted**, not left in quarantine forever.
- **Allure flags flakiness two ways** — explicit `@Flaky` (no message → pair with `@Issue`) *and*
  history-based auto-detection (history enabled; failed→passed→failed across last 5 launches). Track
  **flaky-rate trending down**, not per-run green.
- **A deterministic failure is a bug, not a flake** — fix the code/test; do not retry or quarantine it.
- **No `Thread.sleep`** — sleep-induced waits are a top cause of flakiness; replace with condition-waits
  (Awaitility), don't paper over them with retries. Test names `Should_X_When_Y`; one logical assertion; no
  conditional logic in tests; builders for 4+-field test data; structured logging.

## Cross-references

- `qa-flaky-test-quarantine-dotnet` — same four moves, NUnit: `[Retry(n)]` (method-level only, historically
  no retry-on-exception) + a custom `IRepeatTest`/assembly-level attribute for suite-wide retry;
  `[Category("Flaky")]` + `dotnet test --filter "TestCategory!=Flaky"` for the gate vs a non-gating filtered
  run; Allure.NUnit flaky + history. Structure ported, not code.
- `qa-flaky-test-quarantine-typescript` — same four moves, Playwright/Vitest: Playwright `retries` → the
  built-in **"flaky"** status (passed-on-retry) + `test.fixme`/tag + `--grep-invert @flaky` or a separate
  project for the quarantine lane; Vitest `retry`; allure-playwright flaky + history.
- `qa-allure-reporting-java` (#?) — the **full** Allure wiring this skill layers on: `allure-testng`,
  `aspectjWeaver`, history/trends (required for auto-flaky detection), `categories.json`, CI publish. This
  skill only adds the flaky/quarantine pieces; do the base setup there.
- `qa-_shared-quality-metrics` — track **flaky-rate over time**; a quarantine group that grows is the metric
  to watch. Flaky-rate ÷ total, trending down, is the goal.
- `qa-db-testing-client-java` (#3) / `qa-messaging-testing-service-bus-java` (#28) — the **condition-wait**
  (Awaitility) that *prevents* the eventual-consistency flakiness this skill quarantines. Most flaky tests
  are sleep/timing tests in disguise; fix the wait and they leave quarantine.
- `qa-ui-test-author-playwright-java` / `qa-api-test-author-generator-java` — where the tests being
  quarantined are authored; flakiness is best fixed at the source (stable locators, intent-not-selectors).
- `qa-ci-pipelines-github-actions` / `-azure-pipelines` / `-gitlab-ci` — the gate-lane vs quarantine-lane
  job wiring (a non-gating job with `continue-on-error` / `ignoreFailures`).
