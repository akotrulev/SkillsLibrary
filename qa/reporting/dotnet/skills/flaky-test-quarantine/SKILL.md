---
name: flaky-test-quarantine
description: Use when flaky tests in a .NET 10 (8/9 supported) / NUnit suite must be detected, **quarantined** and reported. Triggers: "this NUnit test is flaky, stop it blocking CI", "quarantine our flaky tests but keep running them", "find which NUnit tests are flaky". Not for Allure wiring (`qa-dotnet:test-reports`), the pipeline lanes themselves (`qa-dotnet:ci-pipelines`), or fixing the test's logic (the owning qa-*-dotnet agent).
---

# Flaky-Test Quarantine (.NET 10 / NUnit)

This is the **.NET sibling** of the single-node `flaky-test-quarantine` family, ported from the canonical
**Java/TestNG** file (`qa-java:flaky-test-quarantine`). The **four-move loop** is identical; only the runner
API and the quarantine filter change: an NUnit `[Category("Flaky")]` and a `dotnet test --filter`.

**Retries are not this skill's to set.** `qa/cicd/ci-conventions` owns the retry policy: none, except a
documented network-flake hotspot. With no in-run retry, NUnit never turns a red test green, so **detection
comes from Allure history and the quarantine category**, never from a retry (plan D7).

## What "flaky" means (and what it does not)

A **flaky test** passes and fails **non-deterministically against the same code** — a race, a timing
assumption, an order dependency, a real-but-rare backend hiccup. It is *not*:

- a test that **always** fails on a change → that's a **caught regression**, fix the code;
- a test that **always** fails regardless of the change → that's a **broken test**, fix the test.

> **The discipline this skill encodes.** A retry hides real bugs (a 1-in-3 race is a real bug) and lets new
> flakiness slip in unnoticed. So the policy is a **four-move loop**, not "add retries":
>
> 1. **Detect** — Allure history across launches marks the tests that flip.
> 2. **Hotspot** — a *documented* network-flake hotspot may opt into one retry on its own `[Test]`, dated and
>    linked to an issue. Nothing else retries.
> 3. **Quarantine** — move a *known* flaky test out of the **merge gate** into a **non-gating lane** that
>    still runs and reports it, tagged with a **ticket**. The gate stays trustworthy; the flake stays visible.
> 4. **Report & fix-or-delete** — track flaky-rate over time; every quarantined test has an owner and a
>    ticket; quarantine **shrinks**, never grows. A test that can't be de-flaked gets deleted, not left to rot.

## Decision matrix — which move for which situation

| Situation | Move | Mechanism |
|-----------|------|-----------|
| Need to *know* which tests are flaky | **Detect** | Allure history marks (Flaky, Regressed, Fixed) |
| A third-party sandbox or infra warm-up fails a clean run now and then, and the issue is filed | **Hotspot** | `[Retry(2)]` on that test only, with `[AllureIssue]` and a date |
| A *known* flaky test, ticketed, not yet fixed | **Quarantine** | `[Category("Flaky")]` + `[AllureIssue]`; excluded from the gate filter, run in a non-gating job |
| A test that fails the same way every run | **Fix the code/test** | Not flakiness — a real bug; no retry, no quarantine |
| A flaky test no one will own/fix | **Delete it** | A test you don't trust and won't fix is worse than no test |

**Rule of thumb:** *seen flaky in history* → `Flaky` category + ticket + non-gating job. *Deterministic
failure* → it's a bug, fix it. **Never** add retries to mask a race.

## Stack

- .NET 10 (8/9 supported), C# (nullable reference types on), NUnit 4.x — **async all the way**; **no
  `Thread.Sleep` / `Task.Delay`-as-wait** (sleeps *cause* flakiness — cross-link the condition-wait in
  `qa-dotnet:db-connection` / `qa-dotnet:messaging-testing`)
- `Allure.NUnit` 2.15.0 — history-based detection and the categories file (cross-link
  `qa-dotnet:test-reports` for the full Allure wiring; this skill only adds the flaky pieces)
- `dotnet test --filter` — the gate adds `TestCategory!=Flaky`; a quarantine job runs `TestCategory=Flaky`

```
UiTests/
├── Tests/…                 ← quarantined tests carry [Category("Flaky")] + [AllureIssue]
└── categories.json         ← the "Known flaky (quarantined)" triage bucket, first
```

## Move 1 — Detect

**Allure's history-based detection** — identical across every stack (a *report* feature, not a language one).
With Allure **history enabled** (the `history/` folder carried across runs — see `qa-dotnet:test-reports`),
Allure adds the **Flaky** mark when, across the latest **5 launches**, a test:

1. got **Failed** at some point within those 5 launches, **and**
2. got **Passed** at least once since that failure, **and**
3. is **Failed or Broken** in the **latest** launch.

It tracks **5 stability marks** off history: **Flaky**, **Retried**, **Fixed** (new pass after a fail),
**Regressed** (new fail after a pass), **Malfunctioned** (new broken). Treat **Flaky** and **Regressed** on an
unchanged area as the quarantine *candidate* list, and **Fixed** as the signal to lift a test *out* of
quarantine.

- **A changing test name splits a test's history.** A `[TestCase]` argument that is a timestamp or a GUID
  makes a new test every run; keep generated values out of test-case arguments.
- **Reproducing a suspect locally** — `[Repeat(20)]` on that one test runs it twenty times in sequence and
  stops at the first failure. It is a local experiment, never committed.
- **Reading a flaky UI failure** — its trace, screenshot and video are in
  `bin/<cfg>/net10.0/playwright-artifacts/` (`qa/dotnet/skills/evidence-capture`). Read them before tagging.

## Move 2 — The documented hotspot

`ci-conventions` allows a per-test retry only for a documented network-flake hotspot. It goes on that
`[Test]`, never on a fixture, an assembly or the pipeline:

```csharp
[Test]
[Retry(2)]
[AllureIssue("PAY-1188")]
[AllureDescription("Retry: payment sandbox cold starts, 2026-10-10, PAY-1188")]
public async Task Should_AuthorizePayment_When_CardIsValid()
{
    var result = await _gateway.AuthorizeAsync(Cards.Valid().WithAmount(1999).Build());

    Assert.That(result.Status, Is.EqualTo(AuthStatus.Approved));
}
```

- **`[Retry(n)]` counts total attempts**, not retries: `[Retry(2)]` is one run plus one retry, and
  `[Retry(1)]` does nothing.
- **Check what the installed NUnit retries.** NUnit's documentation has said that only an assertion failure
  triggers a retry and an unexpected exception does not. A Playwright `Expect(...)` timeout surfaces as an
  exception, so a UI hotspot is stubbed (`qa/dotnet/skills/network-mocking`), not retried.
- No custom `IRepeatTest` attribute, no TRX-parse-and-rerun step, no platform retry on the test task: each
  retries more than one documented test, which `ci-conventions` bans.
- A hotspot retry is still a smell: its issue is reviewed every sprint, and the retry is removed when the
  dependency is stubbed or fixed.

## Move 3 — Quarantine (`[Category("Flaky")]` + a non-gating job)

Quarantine = **take a known-flaky test out of the merge gate, but keep running it and reporting it.** In
NUnit the lever is a **category**, filtered at `dotnet test` time.

```csharp
[Test]
[Category("Flaky")]
[AllureIssue("CHECKOUT-871")]
public async Task Should_SettlePayment_When_GatewayIsSlow()
{
    await _checkout.PayWithAsync(Cards.Valid().Build());

    await Expect(_checkout.SettlementBanner, "settlement banner after paying").ToHaveTextAsync("Settled");
}
```

**The gate excludes the category; the quarantine job includes only it and never blocks:**

```bash
dotnet test UiTests/UiTests.csproj --filter "TestCategory!=Flaky"
dotnet test UiTests/UiTests.csproj --filter "TestCategory=Flaky"
```

- On a sharded UI gate, the category joins the shard's class filter:
  `--filter "(<shard filter>)&TestCategory!=Flaky"` (`qa-dotnet:ci-pipelines`).
- The quarantine lane is a **separate CI job**, unsharded, with `continue-on-error: true` (GitHub),
  `continueOnError: true` (Azure) or `allow_failure: true` (GitLab). It is the **one** non-gating exception
  `ci-conventions` allows: it runs only `Flaky` tests, still uploads its Allure results and failure
  evidence, and never blocks the merge.
- No retry in the quarantine lane either: its job is to report the flake honestly.
- `[Category]` on a fixture class quarantines every test in it — use it only when the fixture shares the
  cause.

> **Why a *running* quarantine lane, not `[Ignore]` / `[Explicit]`.** An ignored test rots — the feature
> drifts, the test silently lies, no one notices when it could be re-enabled. A quarantined test **still
> runs** (off the gate), so you keep its signal, you see when it stabilises (Allure history flips it to
> **Fixed**), and the ticket stays honest. Quarantine is a **waiting room**, not a graveyard.

## Move 4 — Report the flaky flag in Allure

**(a) The quarantined set** is visible by its category: Allure.NUnit reports NUnit categories as tags, so
the report's `Flaky` tag lists every quarantined test, and `[AllureIssue]` carries its ticket.

**(b) The triage bucket matches the flaky flag, not an exception type.** In `categories.json`, the bucket
uses Allure's `flaky` matcher and comes **first**, because a result takes the first category that matches:

```json
[
  { "name": "Known flaky (quarantined)", "matchedStatuses": ["failed", "broken"], "flaky": true }
]
```

Allure sets the flag from history (Move 1). Allure.NUnit has no flaky attribute, and Allure's categories
match a status, a message, a trace or the flaky flag — not a tag — so the bucket fills with what history has
proven flaky, and the `Flaky` tag shows what the team has quarantined. A trace regex such as
`.*TimeoutException.*` is a failure class, not a flakiness verdict: filing every timeout as "known flaky"
hides real regressions, and every Playwright action timeout would land there. The rest of the file is
`qa-dotnet:test-reports`'s.

**Track flaky-rate over time, not per-run green.** A single green run proves nothing about a flaky test. The
metric that matters is *flaky-rate* (flaky marks ÷ total tests) trending **down** — wire it into the team's
quality dashboard (`qa/manual/quality-metrics`). A growing `Flaky` category is a smell: tagging faster than
fixing.

## Anti-patterns

- **Retrying everything.** A custom `IRepeatTest` stamped on every test, a CI step that re-runs the failures
  from the TRX, `retryCountOnTaskFailure` on the test task — each retries more than a documented hotspot,
  which `ci-conventions` bans. *Fix:* no retry; quarantine with a ticket.
- **Detecting flakes through retries.** With no retry, NUnit never reports "passed on retry". *Fix:* Allure
  history and the `Flaky` category.
- **`[Retry(1)]` as "one retry".** It is one attempt — no retry at all. *Fix:* `[Retry(2)]`, on a documented
  hotspot only.
- **Retrying a *deterministic* failure.** Fails every run → retrying wastes CI minutes before the same red.
  *Fix:* it's a caught regression or broken test — fix it.
- **`[Ignore]` / `[Explicit]` as "quarantine".** A skipped test rots and lies. *Fix:* `[Category("Flaky")]`
  + a non-gating job that **still runs** it.
- **Quarantine with no ticket / no owner.** An untracked category only grows. *Fix:* every
  `[Category("Flaky")]` carries `[AllureIssue]`; review it each sprint; it must **shrink**.
- **A "known flaky" category matched on `TimeoutException`.** *Fix:* match `"flaky": true`.
- **A second base class for flaky marking.** UI fixtures already derive from `BaseTest`; a `FlakyMarkBase`
  cannot sit beside it. *Fix:* the category and the history flag.
- **Fighting a `Task.Delay`-induced flake with retries.** The sleep is the *cause*. *Fix:* replace it with a
  condition-wait (Playwright's auto-waiting `Expect`; `WaitForAsync` in `qa-dotnet:db-connection`), then most
  "flakiness" disappears.

## Rules (hard constraints)

- **Retries follow `qa/cicd/ci-conventions`** — none, except `[Retry(2)]` on a documented hotspot, dated and
  linked. Never a custom repeat attribute on every test, a CI rerun step or a platform retry on assertions.
- **Detection = Allure history + the `Flaky` category.** NUnit's retried status is not used.
- **Quarantine = category + non-gating job, never `[Ignore]`.** `[Category("Flaky")]`, excluded from the gate
  with `TestCategory!=Flaky` (joined to the shard filter on a sharded gate), run by a separate
  `TestCategory=Flaky` job that is allowed to fail. The test keeps running.
- **Every quarantined test carries `[AllureIssue("…")]`** (an owned ticket). The category **shrinks** over
  time; review it each sprint; a test that can't be de-flaked is **deleted**, not left in quarantine forever.
- **The quarantine bucket matches `"flaky": true`** and is first in `categories.json`.
- **A deterministic failure is a bug, not a flake** — fix the code/test; do not retry or quarantine it.
- **No `Thread.Sleep` / `Task.Delay`-as-wait** — replace with condition-waits; async all the way. Test names
  `Should_X_When_Y`; one logical assertion; no conditional logic in tests; builders for 4+-field test data;
  structured logging.

## Cross-references

- `qa-java:flaky-test-quarantine` — the **canonical** stack this is ported from: a TestNG `flaky` group,
  `@Flaky`, and the same history-based detection.
- `qa-typescript:flaky-test-quarantine` — same four moves, Playwright: `{ tag: '@flaky' }` +
  `--grep-invert @flaky` on the gate, a separate `--grep @flaky` job, and a nightly `--repeat-each` lane.
- `qa-dotnet:test-reports` — the **full** Allure.NUnit wiring this layers on: the adapter, history/trends
  (required for auto-flaky detection), `categories.json`, the report CLI.
- `qa-<stack>:ci-conventions` — the retry policy this skill defers to.
- `qa-dotnet:evidence-capture` — the trace, video and screenshot a flaky UI failure leaves behind, and how
  to read them.
- `qa-<stack>:quality-metrics` — track **flaky-rate over time**; a quarantine category that grows is the
  metric to watch.
- `qa-dotnet:db-connection` / `qa-dotnet:messaging-testing` — the `WaitForAsync` **condition-wait** that
  *prevents* the eventual-consistency flakiness this skill quarantines.
- `qa-dotnet:ui-tests-playwright` / `qa-dotnet:api-tests` — where the quarantined tests are
  authored and where `BaseTest` lives; flakiness is best fixed at the source (stable locators, web-first
  assertions).
- `qa-dotnet:ci-pipelines` (its GitHub Actions, Azure Pipelines and GitLab CI references) — the gate job, the
  shard filter and the non-gating quarantine job.
