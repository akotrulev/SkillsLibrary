---
name: qa-flaky-test-quarantine-dotnet
description: Detect, retry, **quarantine**, and report flaky tests in a .NET 10 (8-9 supported) / NUnit suite. Triggers: "this NUnit test is flaky, stop it blocking CI", "quarantine our flaky tests but keep running them", "retry failed tests in NUnit including on exceptions".
---

# Flaky-Test Quarantine (.NET 8 / NUnit)

This is the **.NET sibling** of the single-node `qa/reporting/dotnet/skills/flaky-test-quarantine/` family, **ported** from the
canonical **Java/TestNG** file (`qa-flaky-test-quarantine-java`). The **four-move loop** is identical; only
the runner API and the quarantine filter change. **NUnit's flaky surface is genuinely thinner than
TestNG's** — `[Retry]` is method-level with no suite-wide auto-apply, and Allure.NUnit has no first-class
`[Flaky]` attribute — so this file says so plainly and gives the practical .NET routes for each move.

## What "flaky" means (and what it does not)

A **flaky test** passes and fails **non-deterministically against the same code** — a race, a timing
assumption, an order dependency, a real-but-rare backend hiccup. It is *not*:

- a test that **always** fails on a change → that's a **caught regression**, fix the code;
- a test that **always** fails regardless of the change → that's a **broken test**, fix the test.

> **The discipline this skill encodes.** A retry is a **band-aid**, not a cure. Retrying to green **hides
> real bugs** (a 1-in-3 race is a real bug) and lets new flakiness slip in unnoticed. So the policy is a
> **four-move loop**, not "just add retries":
>
> 1. **Detect** — surface which tests are flaky (Allure history), don't guess.
> 2. **Retry — once, bounded** — absorb *true* transients on the gate so one hiccup doesn't fail a clean PR.
> 3. **Quarantine** — move a *known* flaky test out of the **merge gate** into a **non-gating lane** that
>    still runs and reports it, tagged with a **ticket**. The gate stays trustworthy; the flake stays visible.
> 4. **Report & fix-or-delete** — track flaky-rate over time; every quarantined test has an owner and a
>    ticket; quarantine **shrinks**, never grows. A test that can't be de-flaked gets deleted, not left to rot.

## Decision matrix — which move for which situation

| Situation | Move | Mechanism |
|-----------|------|-----------|
| A clean PR occasionally red on a *transient* (network blip, cold cache) | **Retry once** | `[Retry(1)]` or `[RetryOnFailure(1)]` on the prone test |
| A *known* flaky test, ticketed, not yet fixed | **Quarantine** | `[Category("Flaky")]` + `[AllureIssue]`; excluded from gate filter, run in non-gating lane |
| A test that fails the same way every run | **Fix the code/test** | Not flakiness — a real bug; no retry, no quarantine |
| A flaky test no one will own/fix | **Delete it** | A test you don't trust and won't fix is worse than no test |
| Need to *know* which tests are flaky | **Detect** | Allure history-based flaky mark + flaky-rate metric |

**Rule of thumb:** *transient on otherwise-green* → one retry. *Known-flaky, ticketed* → quarantine category
+ non-gating lane. *Deterministic failure* → it's a bug, fix it. **Never** crank retries to mask a real race.

## Stack

- .NET 8, C# (nullable reference types on), NUnit 4.x — **async all the way** in the tests; **no
  `Thread.Sleep` / `Task.Delay`-as-wait** (sleeps *cause* flakiness — cross-link the condition-wait in
  `qa-db-connection-dotnet` / `qa-messaging-testing-*`)
- `NUnit` — `[Retry(n)]` (built-in) + a custom `RetryOnFailureAttribute : IRepeatTest` (retries on errors too)
- `[Category("Flaky")]` + `dotnet test --filter "TestCategory!=Flaky"` (gate) vs `"TestCategory=Flaky"` (lane)
- `Allure.NUnit` — Allure's **Retries** tab + **history-based** flaky detection + the `AllureLifecycle` API
  to mark a result flaky (cross-link `qa-test-reports-dotnet` for the full Allure wiring)

```
Tests/
├── Quarantine/
│   └── RetryOnFailureAttribute.cs   ← custom IRepeatTest: retries on failure AND exception
├── Support/
│   └── FlakyMarkBase.cs             ← base fixture: marks [Category("Flaky")] results flaky in Allure
├── allureConfig.json                ← Allure config (see qa-test-reports-dotnet)
└── categories.json                  ← an Allure "Known flaky (quarantined)" triage bucket
```

## Move 2 — Retry, bounded (NUnit `[Retry]`, and its limits)

NUnit ships `[Retry(n)]`: re-run a failed test up to `n` extra times. Keep `n` **low — 1** on the gate; the
cap is the whole safety mechanism.

```csharp
[Test]
[Retry(1)]   // one extra attempt to absorb a true transient — NOT a knob to crank
public async Task Should_authorize_payment_When_card_is_valid()
{
    var result = await _gateway.AuthorizeAsync(Cards.Valid().WithAmount(1999).Build());
    Assert.That(result.Status, Is.EqualTo(AuthStatus.Approved));   // one logical assertion
}
```

> **Two real limits of built-in `[Retry]` — state them, don't trip over them:**
> 1. **Method-level only.** It **cannot** be applied at fixture or assembly scope (NUnit issue #2452) —
>    there is **no suite-wide auto-apply** like TestNG's `IAnnotationTransformer`. You opt in per test. This
>    actually fits quarantine well: you retry the *transient-prone* gate tests deliberately, not everything.
> 2. **Historically retries on assertion *failure*, not on an unexpected *exception*** (NUnit issue #2543).
>    A test that throws (a flaky `HttpRequestException`, say) may not be retried by `[Retry]`.

For the exception case — and to make the policy explicit — use a **custom `IRepeatTest` attribute** (the
same interface `[Retry]` implements) that re-runs on **both** failure and error:

```csharp
using System;
using NUnit.Framework;
using NUnit.Framework.Interfaces;
using NUnit.Framework.Internal;
using NUnit.Framework.Internal.Commands;

[AttributeUsage(AttributeTargets.Method, AllowMultiple = false)]
public sealed class RetryOnFailureAttribute : NUnitAttribute, IRepeatTest
{
    private readonly int _maxRetries;
    public RetryOnFailureAttribute(int maxRetries = 1) => _maxRetries = maxRetries;

    public TestCommand Wrap(TestCommand command) => new RetryCommand(command, _maxRetries);

    private sealed class RetryCommand(TestCommand inner, int maxRetries) : DelegatingTestCommand(inner)
    {
        public override TestResult Execute(TestExecutionContext context)
        {
            var remaining = maxRetries;
            while (true)
            {
                try
                {
                    context.CurrentResult = innerCommand.Execute(context);
                }
                catch (Exception ex)   // built-in [Retry] does NOT retry here — this attribute does
                {
                    context.CurrentResult ??= context.CurrentTest.MakeTestResult();
                    context.CurrentResult.RecordException(ex);
                }

                if (context.CurrentResult.ResultState.Status != TestStatus.Failed || remaining-- <= 0)
                    return context.CurrentResult;

                context.CurrentResult = context.CurrentTest.MakeTestResult();   // fresh result for the re-run
            }
        }
    }
}
```

```csharp
[Test]
[RetryOnFailure(1)]   // re-runs on failure OR exception, bounded at 1 on the gate
public async Task Should_load_dashboard_When_session_is_valid() { /* ... */ }
```

### CI-level alternative — re-run only the failed tests

`dotnet test` has **no native rerun-failing-tests** flag (unlike Maven Surefire). The build-tool-level
analogue is a CI step that re-runs *only* the failures from the first pass (parse the TRX, re-filter):

```yaml
- name: Tests (first pass, gate)
  run: dotnet test --filter "TestCategory!=Flaky" --logger "trx;LogFileName=pass1.trx"
  continue-on-error: true
# A second step parses pass1.trx for failed FQNs and re-runs ONLY those with --filter "FullyQualifiedName=..."
```

Pick **one** retry mechanism per project (`[RetryOnFailure]` *or* the CI rerun) — stacking them multiplies
the cap and re-introduces the masking problem.

## Move 3 — Quarantine (`[Category("Flaky")]` + a non-gating lane)

Quarantine = **take a known-flaky test out of the merge gate, but keep running it and reporting it.** In
NUnit the lever is a **category** filtered at `dotnet test` time.

```csharp
using Allure.Net.Commons;
using NUnit.Framework;

public class CheckoutTests : FlakyMarkBase   // base marks Flaky-category results flaky in Allure (Move 4)
{
    [Test]
    [Category("Flaky")]                 // ← out of the gate, into the quarantine lane
    [Property("Issue", "CHECKOUT-871")] // ← the ticket tracking the de-flake — quarantine is NEVER permanent
    public async Task Should_settle_payment_When_gateway_is_slow()
    {
        // ... the intermittently-failing assertion, awaiting a real fix under CHECKOUT-871
    }
}
```

**The gate excludes the category; the quarantine lane includes only it and never blocks** — driven entirely
by the `--filter` (cross-link `qa-ci-pipelines`):

```yaml
- name: Gate suite (blocks merge)
  run: dotnet test --filter "TestCategory!=Flaky"        # quarantined tests never block the merge

- name: Quarantine lane (visibility only)
  if: always()
  run: dotnet test --filter "TestCategory=Flaky"         # still runs + reports
  continue-on-error: true                                # a red quarantine lane does NOT fail the pipeline

- name: Upload Allure results
  if: always()
  uses: actions/upload-artifact@v4
  with: { name: allure-results, path: '**/bin/**/allure-results/' }
```

> **Why a *running* quarantine lane, not `[Ignore]` / `Explicit`.** An ignored test rots — the feature
> drifts, the test silently lies, no one notices when it could be re-enabled. A quarantined test **still
> runs** (off the gate), so you keep its signal, you see when it stabilises (Allure history flips it to
> **Fixed**), and the ticket stays honest. Quarantine is a **waiting room**, not a graveyard.

## Move 4 — Report the flaky flag in Allure

Allure surfaces flakiness, and the **history-based auto-detection is identical across every stack** — it's a
*report* feature, not a language one. With Allure **history enabled** (the `history/` folder carried across
runs — see `qa-test-reports-dotnet`), Allure auto-adds the **Flaky** mark when, across the latest **5
launches**, a test:

1. got **Failed** at some point within those 5 launches, **and**
2. got **Passed** at least once since that failure, **and**
3. is **Failed or Broken** in the **latest** launch.

It tracks **5 stability marks** off history: **Flaky**, **Retried**, **Fixed** (new pass after a fail),
**Regressed** (new fail after a pass), **Malfunctioned** (new broken). Treat **Retried** + **Flaky** as your
quarantine *candidate* list, and **Fixed** as the signal to lift a test *out* of quarantine.

> **The honest .NET divergence from Java.** Allure.NUnit has **no first-class `[Flaky]` attribute** (Java's
> `io.qameta.allure.Flaky` has no equivalent here). Two practical routes: lean on history-based detection
> (above), and/or **mark the result flaky programmatically** via the `AllureLifecycle` API — cleanest in a
> base fixture keyed off the quarantine category, so a quarantined test is visibly yellow even on a green run:

```csharp
using Allure.Net.Commons;
using NUnit.Framework;
using NUnit.Framework.Interfaces;

public abstract class FlakyMarkBase
{
    [TearDown]
    public void MarkFlakyInAllure()
    {
        var isQuarantined = TestContext.CurrentContext.Test.Properties["Category"]?.Contains("Flaky") == true;
        if (isQuarantined)
            AllureLifecycle.Instance.UpdateTestCase(tc => tc.flaky = true);   // paint it yellow in Allure
    }
}
```

Add `[AllureIssue("CHECKOUT-871")]` (or the `[Property("Issue", …)]` above) so the **ticket** travels with
the flagged test in the report. **A triage bucket in `categories.json`** keeps quarantined/flaky failures out
of "real" failures (the adapter picks it up — see `qa-test-reports-dotnet`):

```json
[
  { "name": "Known flaky (quarantined)", "matchedStatuses": ["failed", "broken"],
    "traceRegex": ".*TimeoutException.*|.*WebDriverTimeoutException.*|.*TaskCanceledException.*" }
]
```

**Track flaky-rate over time, not per-run green.** A single green run proves nothing about a flaky test. The
metric that matters is *flaky-rate* (flaky marks ÷ total) trending **down** — wire it into the team dashboard
(`qa/manual/quality-metrics`). A growing quarantine category is a smell: tagging faster than fixing.

## Anti-patterns

- **Cranking the retry cap to make CI green.** `[Retry(5)]` doesn't fix a 1-in-3 race — it hides it. *Fix:*
  cap the gate at **1**; quarantine the rest with a ticket.
- **Retrying a *deterministic* failure.** Fails every run → retrying wastes CI minutes before the same red.
  *Fix:* it's a caught regression or broken test — fix it.
- **Assuming `[Retry]` retries on exceptions.** It historically does not (issue #2543). *Fix:* use the
  custom `[RetryOnFailure]` that catches and re-runs on error too.
- **Expecting `[Retry]` to work at fixture/assembly scope.** It's method-level only (issue #2452). *Fix:*
  apply it per transient-prone test, or drive rerun from CI.
- **`[Ignore]` / `[Explicit]` as "quarantine".** A skipped test rots and lies. *Fix:* `[Category("Flaky")]`
  + a non-gating filtered lane that **still runs** it; keep the signal and the history.
- **Quarantine with no ticket / no owner.** An untracked category only grows. *Fix:* every
  `[Category("Flaky")]` carries `[AllureIssue]`/`[Property("Issue",…)]`; review each sprint; it must **shrink**.
- **Stacking `[RetryOnFailure]` *and* a CI rerun.** Caps multiply; you're back to masking. *Fix:* one mechanism.
- **Fighting a `Task.Delay`-induced flake with more retries.** The sleep is the *cause*. *Fix:* replace it
  with a condition-wait (`WaitForAsync` from `qa-db-connection-dotnet`), then most "flakiness" disappears.

## Examples

**End-to-end: a transient on the gate (retried once) vs a known flaky (quarantined + tracked).**

```csharp
public class PaymentFlowTests : FlakyMarkBase
{
    private PaymentGateway _gateway = null!;

    [SetUp]
    public void SetUp() => _gateway = new PaymentGateway(_httpClient);   // constructor injection

    // GATE test — normally deterministic. A true transient (cold-start 503) gets exactly one more shot.
    [Test]
    [RetryOnFailure(1)]
    public async Task Should_authorize_payment_When_card_is_valid()
    {
        var result = await _gateway.AuthorizeAsync(Cards.Valid().WithAmount(1999).Build());
        Assert.That(result.Status, Is.EqualTo(AuthStatus.Approved));
    }

    // QUARANTINED test — known to race the async settlement webhook. Off the gate, still run + flagged + ticketed.
    [Test]
    [Category("Flaky")]
    [Property("Issue", "PAY-1204")]
    public async Task Should_mark_settled_When_webhook_arrives_within_sla()
    {
        await _gateway.AuthorizeAsync(Cards.Valid().Build());
        // de-flake (PAY-1204): wait on the settlement condition, not a fixed window. Until then, quarantined.
        var settlement = await WaitFor.Async(
            probe:     ct => _ledger.SettlementForAsync(_orderId, ct),
            predicate: s  => s.State == SettlementState.Settled,
            timeout:   TimeSpan.FromSeconds(10),
            interval:  TimeSpan.FromMilliseconds(200));
        Assert.That(settlement.State, Is.EqualTo(SettlementState.Settled));
    }
}
```

The gate is green if the non-flaky tests pass (one retry absorbed any transient); the quarantine lane's
result is reported in Allure (flaky-flagged, history-tracked) but **never** fails the pipeline.

## Rules (hard constraints)

- **Retry is bounded and low on the gate** — `[Retry(1)]` or `[RetryOnFailure(1)]`. The cap is the safety
  mechanism; never crank it to hide failures. Use the custom `IRepeatTest` attribute when you need
  retry-on-exception (built-in `[Retry]` historically doesn't).
- **One retry mechanism**, never `[RetryOnFailure]` + a CI rerun together (caps multiply). NUnit retry is
  **method-level only** — no fixture/assembly auto-apply; opt in per prone test.
- **Quarantine = category + non-gating lane, never `[Ignore]`.** `[Category("Flaky")]`, excluded by
  `--filter "TestCategory!=Flaky"` on the gate, run by a `--filter "TestCategory=Flaky"` step with
  `continue-on-error: true`. The test keeps running.
- **Every quarantined test carries a ticket** (`[AllureIssue]` / `[Property("Issue",…)]`) and is marked flaky
  in Allure (no attribute exists → the `AllureLifecycle.UpdateTestCase(tc => tc.flaky = true)` base-teardown
  route, or history-based detection). The category **shrinks**; review each sprint; un-fixable → **deleted**.
- **Allure flags flakiness via history** — identical 5-launch rule across stacks (history enabled).  Track
  **flaky-rate trending down**, not per-run green.
- **A deterministic failure is a bug, not a flake** — fix the code/test; do not retry or quarantine it.
- **No `Thread.Sleep` / `Task.Delay`-as-wait** — replace with condition-waits (`WaitForAsync`); async all the
  way. Test names `Should_X_When_Y`; one logical assertion; no conditional logic in tests; builders for
  4+-field test data; structured logging.

## Cross-references

- `qa-flaky-test-quarantine-java` — the **canonical** stack this is ported from. TestNG `IRetryAnalyzer` +
  `IAnnotationTransformer` gives true **suite-wide** retry (no per-test edits) and native group-based
  quarantine + the first-class `@Flaky` annotation — the surface NUnit is thinner than. Same four moves.
- `qa-flaky-test-quarantine-typescript` — same four moves, Playwright/Vitest: Playwright `retries` → the
  built-in **"flaky"** status + tag/`--grep-invert @flaky` or a separate project for the lane; Vitest `retry`.
- `qa-test-reports-dotnet` (#?) — the **full** Allure.NUnit wiring this layers on: the adapter,
  history/trends (required for auto-flaky detection), `categories.json`, CI publish. Base setup lives there.
- `qa-_shared-quality-metrics` — track **flaky-rate over time**; a quarantine category that grows is the
  metric to watch.
- `qa-db-connection-dotnet` / `qa-messaging-testing-dotnet` — the
  `WaitForAsync` **condition-wait** that *prevents* the eventual-consistency flakiness this skill quarantines.
- `qa-ui-test-writer-playwright-dotnet` / `qa-api-test-writer-dotnet` — where the quarantined tests
  are authored; flakiness is best fixed at the source (stable locators, intent-not-selectors).
- `qa-ci-pipelines` (github-actions / azure-pipelines / gitlab-ci references) — the gate-lane vs quarantine-lane job
  wiring (`continue-on-error` on the non-gating lane).
