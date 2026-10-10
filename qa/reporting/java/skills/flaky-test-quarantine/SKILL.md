---
name: qa-flaky-test-quarantine-java
description: Use when flaky tests in a Java 21 / TestNG suite must be detected, **quarantined** and reported. Triggers: "this test is flaky, stop it blocking the pipeline", "quarantine the flaky tests but keep running them", "find which TestNG tests are flaky". Not for Allure wiring (`qa-test-reports-java`), the pipeline lanes (`qa-ci-pipelines-java`), or fixing test logic (the owning qa-*-java agent).
---

# Flaky-Test Quarantine (Java 21 / TestNG) — **canonical stack**

This is the **canonical** stack of the single-node `qa/reporting/java/skills/flaky-test-quarantine/` family:
TestNG **groups** give native quarantine, and allure-java has a first-class `@Flaky` annotation. The `dotnet`
(NUnit `[Category("Flaky")]` + a filter) and `typescript` (a `@flaky` tag + `--grep-invert`) siblings are
ported from this file — the *moves* are identical; only the runner API and the quarantine filter change.

**Retries are not this skill's to set.** `qa/cicd/ci-conventions` owns the retry policy: none, except a
documented network-flake hotspot. With no in-run retry, TestNG never turns a red test green, so **detection
comes from Allure history and the quarantine category**, never from a retry (plan D7).

## What "flaky" means (and what it does not)

A **flaky test** passes and fails **non-deterministically against the same code** — a race, a timing
assumption, an order dependency, a real-but-rare backend hiccup. It is *not*:

- a test that **always** fails on a change → that's a **caught regression**, fix the code;
- a test that **always** fails regardless of the change → that's a **broken test**, fix the test.

> **The discipline this skill encodes.** A retry hides real bugs (a 1-in-3 race is a real bug) and lets new
> flakiness slip in unnoticed. So the policy is a **four-move loop**, not "add retries":
>
> 1. **Detect** — Allure history across launches marks the tests that flip; a known one carries `@Flaky`.
> 2. **Hotspot** — a *documented* network-flake hotspot may opt into one retry on its own `@Test`, dated and
>    linked to an issue. Nothing else retries.
> 3. **Quarantine** — move a *known* flaky test out of the **merge gate** into a **non-gating lane** that
>    still runs and reports it, tagged with a **ticket**. The gate stays trustworthy; the flake stays visible.
> 4. **Report & fix-or-delete** — track flaky-rate over time; every quarantined test has an owner and a
>    ticket; quarantine **shrinks**, never grows. A test that can't be de-flaked gets deleted, not left to rot.

## Decision matrix — which move for which situation

| Situation | Move | Mechanism |
|-----------|------|-----------|
| Need to *know* which tests are flaky | **Detect** | Allure history marks (Flaky, Regressed, Fixed) |
| A third-party sandbox or infra warm-up fails a clean run now and then, and the issue is filed | **Hotspot** | `@Test(retryAnalyzer = RetryOnce.class)` on that test only, with `@Issue` and a date |
| A *known* flaky test, ticketed, not yet fixed | **Quarantine** | `@Test(groups = "flaky")` + `@Flaky` + `@Issue`; excluded from the gate, run in a non-gating lane |
| A test that fails the same way every run | **Fix the code/test** | Not flakiness — a real bug; no retry, no quarantine |
| A flaky test no one will own/fix | **Delete it** | A test you don't trust and won't fix is worse than no test |

**Rule of thumb:** *seen flaky in history* → `flaky` group + `@Flaky` + ticket + non-gating lane.
*Deterministic failure* → it's a bug, fix it. **Never** add retries to mask a race.

## Stack

- Java 21, TestNG 7.12.0 — **no `Thread.sleep`** anywhere (flakiness is usually *caused* by sleeps; cross-link
  the condition-wait in `qa-db-connection-java` / `qa-messaging-testing-*`)
- `io.qameta.allure:allure-testng:3.0.0` — the `@Flaky` annotation, history-based detection and the
  categories file (cross-link `qa-test-reports-java` for the full Allure wiring; this skill only adds the
  flaky pieces)
- Gradle Kotlin DSL — the gate `test` task excludes the `flaky` group; a **`flakyQuarantine`** task runs only
  that group with `ignoreFailures`

```
src/test/
├── java/support/
│   └── RetryOnce.java              ← the one-retry analyzer a documented hotspot opts into
└── resources/
    └── categories.json             ← the "Known flaky (quarantined)" triage bucket, first
testng.xml                          ← the project's one suite; the Gradle tasks filter its groups
```

## Move 1 — Detect

**Allure's history-based detection** — identical across every stack (a *report* feature, not a language one).
With Allure **history enabled** (the `history/` folder carried across runs — see `qa-test-reports-java`),
Allure adds the **Flaky** mark when, across the latest **5 launches**, a test:

1. got **Failed** at some point within those 5 launches, **and**
2. got **Passed** at least once since that failure, **and**
3. is **Failed or Broken** in the **latest** launch.

It tracks **5 stability marks** off history: **Flaky**, **Retried**, **Fixed** (new pass after a fail),
**Regressed** (new fail after a pass), **Malfunctioned** (new broken). Treat **Flaky** and **Regressed** on an
unchanged area as the quarantine *candidate* list, and **Fixed** as the signal to lift a test *out* of
quarantine.

- **History restarts once after the allure-java 2.x → 3.0 upgrade**: 3.0 computes TestNG identifiers
  differently, so detection needs five fresh launches.
- **A changing runtime parameter splits a test's history.** Exclude it:
  `Allure.parameter("startedAt", startedAt, true)`.
- **Reproducing a suspect locally** — `@Test(invocationCount = 20)` on that one test runs it twenty times in
  sequence. It is a local experiment, never committed.

## Move 2 — The documented hotspot

`ci-conventions` allows a per-test retry only for a documented network-flake hotspot. It goes on that
`@Test`, never suite-wide:

```java
package support;

import org.testng.IRetryAnalyzer;
import org.testng.ITestResult;

public final class RetryOnce implements IRetryAnalyzer {
    private boolean retried;

    @Override
    public boolean retry(ITestResult result) {
        if (retried) {
            return false;
        }
        retried = true;
        return true;
    }
}
```

```java
@Test(retryAnalyzer = RetryOnce.class)
@Issue("PAY-1188")
@Description("Retry: payment sandbox cold starts, 2026-10-10, PAY-1188")
public void Should_AuthorizePayment_When_CardIsValid() {
    checkoutPage.payWith(Cards.valid().build());

    assertThat(checkoutPage.confirmation()).hasText("Approved");
}
```

TestNG instantiates the analyzer for the test method, so the instance field counts that test's attempts. A
hotspot retry is still a smell: its issue is reviewed every sprint, and the retry is removed when the
dependency is stubbed (`qa/java/skills/network-mocking`) or fixed.

## Move 3 — Quarantine (a TestNG group and a non-gating lane)

Quarantine = **take a known-flaky test out of the merge gate, but keep running it and reporting it.** The
lever is a TestNG **group**, filtered by Gradle. The project's one `testng.xml` (for UI suites,
`qa/java/skills/ui-test-author/playwright/assets/testng.xml` with `parallel="classes"`) stays as it is; no
second suite file.

```java
@Test(groups = "flaky")
@Flaky
@Issue("CHECKOUT-871")
public void Should_SettlePayment_When_GatewayIsSlow() {
    checkoutPage.payWith(Cards.valid().build());

    assertThat(checkoutPage.settlementBanner()).hasText("Settled");
}
```

The gate excludes the group; a second `Test` task runs only it and never fails the build:

```kotlin
tasks.test {
    useTestNG {
        suites("testng.xml")
        excludeGroups("flaky")
    }
    environment("PLAYWRIGHT_JAVA_SRC", "src/test/java")
}

val flakyQuarantine by tasks.registering(Test::class) {
    testClassesDirs = sourceSets["test"].output.classesDirs
    classpath = sourceSets["test"].runtimeClasspath
    useTestNG {
        suites("testng.xml")
        includeGroups("flaky")
    }
    environment("PLAYWRIGHT_JAVA_SRC", "src/test/java")
    ignoreFailures = true
}
```

- A custom `Test` task needs its `testClassesDirs` and `classpath` set explicitly.
- TestNG applies command-line group filters to the suite file's tests, so one suite serves both tasks.
  `BaseTest`'s configuration methods are `alwaysRun = true`, which is what keeps them running under a group
  filter.
- No retry in the quarantine lane either: its job is to report the flake honestly.
- CI runs the two lanes as **separate jobs**, the quarantine one non-gating (cross-link
  `qa-ci-pipelines-java`), so a quarantine failure's evidence never mixes with the gate's.

The quarantine lane is the **one** non-gating exception `ci-conventions` allows: it runs only `flaky` tests,
still reports them to Allure, and never blocks the merge.

> **Why a *running* quarantine lane, not `enabled = false`.** A disabled test rots — the feature drifts, the
> test silently lies, and no one notices when it could be re-enabled. A quarantined test **still runs** (off
> the gate), so you keep its signal, you see when it stabilises (Allure history flips it to **Fixed**), and
> the ticket stays honest. Quarantine is a **waiting room**, not a graveyard.

## Move 4 — Report the flaky flag in Allure

**(a) Explicit — the `@Flaky` annotation.** `io.qameta.allure.Flaky` marks a test result flaky even when it
passes, so a quarantined test is visibly distinct from a healthy one in every report. `@Flaky` takes **no
message** — pair it with `@Issue("…")` so the ticket travels with it.

**(b) Automatic — history-based detection** (Move 1), which catches the flakiness you haven't tagged yet.

**The quarantine category matches the flaky flag, not an exception type.** In
`src/test/resources/categories.json`, the bucket uses Allure's `flaky` matcher and comes **first**, because a
result takes the first category that matches:

```json
[
  { "name": "Known flaky (quarantined)", "matchedStatuses": ["failed", "broken"], "flaky": true }
]
```

The rest of the file is `qa-test-reports-java`'s. A trace regex such as `.*TimeoutException.*` is a failure
class, not a flakiness verdict: filing every timeout as "known flaky" hides real regressions.

**Track flaky-rate over time, not per-run green.** A single green run proves nothing about a flaky test. The
metric that matters is *flaky-rate* (flaky marks ÷ total tests) trending **down** — wire it into the team's
quality dashboard (`qa/manual/quality-metrics`). A growing `flaky` group is a smell: tagging faster than fixing.

## Anti-patterns

- **A suite-wide retry.** An `IAnnotationTransformer` that stamps an analyzer on every `@Test`, a
  `RetryListener` in `META-INF/services`, or Maven Surefire's `rerunFailingTestsCount` — each retries every
  test, which `ci-conventions` bans. *Fix:* no retry; quarantine with a ticket.
- **Detecting flakes through retries.** With no retry, TestNG never reports "passed on retry". *Fix:* Allure
  history and the `flaky` category.
- **Retrying a *deterministic* failure.** Fails every run → retrying wastes CI minutes before the same red.
  *Fix:* it's a caught regression or broken test — fix it.
- **`enabled = false` as "quarantine".** A disabled test stops running, rots, and lies. *Fix:*
  `@Test(groups = "flaky")` + a non-gating lane that **still runs** it.
- **Quarantine with no ticket / no owner.** An untracked group only grows. *Fix:* every
  `@Test(groups = "flaky")` carries `@Issue("…")`; review the group every sprint; it must **shrink**.
- **A "known flaky" category matched on `TimeoutException`.** *Fix:* match `"flaky": true`.
- **Fighting a sleep-induced flake with retries.** A `Thread.sleep`-based wait is the *cause*. *Fix:* replace
  it with a condition-wait (Playwright's auto-waiting assertions; Awaitility in `qa-db-connection-java` /
  `qa-messaging-testing-*`), then most "flakiness" disappears.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Examples**.

## Rules (hard constraints)

- **Retries follow `qa/cicd/ci-conventions`** — none, except `@Test(retryAnalyzer = RetryOnce.class)` on a
  documented hotspot, dated and linked. Never a suite-wide analyzer, listener or Surefire rerun.
- **Detection = Allure history + the `flaky` category.** TestNG's "retried" status is not used.
- **Quarantine = group + non-gating lane, never `enabled = false`.** `@Test(groups = "flaky")`, excluded from
  the gate with `excludeGroups("flaky")`, run by a `flakyQuarantine` task with `ignoreFailures = true` in a
  separate CI job. The test keeps running.
- **Every quarantined test carries `@Issue("…")`** (an owned ticket) and `@Flaky`. The group **shrinks** over
  time; review it each sprint; a test that can't be de-flaked is **deleted**, not left in quarantine forever.
- **The quarantine category matches `"flaky": true`** and is first in `categories.json`.
- **A deterministic failure is a bug, not a flake** — fix the code/test; do not retry or quarantine it.
- **No `Thread.sleep`** — replace with condition-waits, don't paper over them with retries. Test names
  `Should_X_When_Y`; one logical assertion; no conditional logic in tests; builders for 4+-field test data;
  structured logging.

## Cross-references

- `qa-flaky-test-quarantine-dotnet` — same four moves, NUnit: `[Category("Flaky")]` + `dotnet test --filter
  "TestCategory!=Flaky"` for the gate vs a non-gating filtered run; Allure.NUnit flaky + history.
- `qa-flaky-test-quarantine-typescript` — same four moves, Playwright: `{ tag: '@flaky' }` +
  `--grep-invert @flaky` on the gate, a separate `--grep @flaky` job, and a nightly `--repeat-each` lane.
- `qa-test-reports-java` — the **full** Allure wiring this layers on: `allure-testng` 3.0, the weaver,
  history/trends (required for auto-flaky detection), `categories.json`, CI publish.
- `qa-ci-conventions-shared` — the retry policy this skill defers to.
- `qa-_shared-quality-metrics` — track **flaky-rate over time**; a quarantine group that grows is the metric
  to watch.
- `qa-db-connection-java` / `qa-messaging-testing-java` — the **condition-wait** (Awaitility) that *prevents*
  the eventual-consistency flakiness this skill quarantines.
- `qa-ui-test-writer-playwright-java` — where the quarantined UI tests are authored and where `BaseTest` and
  `testng.xml` live; flakiness is best fixed at the source (stable locators, web-first assertions).
- `qa-evidence-capture-java` — the trace, video and screenshot a flaky failure leaves behind, and how to read
  them.
- `qa-ci-pipelines-java` (its GitHub Actions, Azure Pipelines and GitLab CI references) — the gate job and the
  non-gating quarantine job.
