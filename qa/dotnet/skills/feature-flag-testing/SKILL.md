---
name: qa-feature-flag-testing-dotnet
description: Use when testing feature-flagged code in .NET 10 (8-9 supported) / NUnit — pin flag state in-process with OpenFeature's `InMemoryProvider` or LaunchDarkly's `TestData` fixture (never a live flag service), cover BOTH sides of every flag, drive targeting through the evaluation context. Triggers: "test a feature flag", "test both sides of a flag", "pin a flag state in tests". Do NOT use for the API/UI assertions inside a branch (`qa-api-test-writer-dotnet`).
---

# QA — Feature-Flag Testing (.NET 8 / OpenFeature + LaunchDarkly `TestData` + NUnit)

Scaffolds **deterministic feature-flag tests** in .NET for code whose behavior branches on a flag, using
[**OpenFeature**](https://openfeature.dev) — the CNCF vendor-neutral flag API — with its built-in
**`InMemoryProvider`** as the test spine, and [**LaunchDarkly**](https://launchdarkly.com)'s server SDK
**`TestData`** fixture as the named real-provider path (the two compose: production code talks OpenFeature, the
LaunchDarkly OpenFeature provider sits behind it, and `TestData` pins what that provider sees). This is a
**ported sibling** of the **canonical** `qa-feature-flag-testing-java` — same four ideas, same fixtures, same
section order; the SDK surface is the `OpenFeature` NuGet + `LaunchDarkly.ServerSdk` and the runner is NUnit.

> **The discipline this skill encodes** — four ideas that separate a correct flag test from an
> environment-coupled reflex:
>
> 1. **PIN the flag, don't fetch it.** A feature-flag test **never evaluates against a live/remote flag
>    service** — the reflex "run against whatever the environment's flags say" makes the test nondeterministic
>    (someone flips a flag → your suite changes meaning), environment-coupled, and structurally incapable of
>    testing the *other* branch. Instead the test **wires an in-memory/test data source in setup** — OpenFeature's
>    `InMemoryProvider`, or LaunchDarkly's `TestData` — and pins exactly the flag state the scenario needs. **The
>    production SDK key never appears in a test run.**
> 2. **A flag is a branch — test BOTH sides.** Shipping a flag means shipping *two* code paths (or N, for a
>    multivariate flag); a suite that only runs with the flag on has zero coverage of the path your users on the
>    old experience are living in — and zero proof the rollback is safe. Every flag-touching behavior gets a
>    **matrix**: on/off for a boolean, every variation for a multivariate — bound as parameterized rows
>    (`qa-data-driven-testing-dotnet` mechanics), not copy-pasted test methods.
> 3. **Targeting rules are tested via the evaluation context.** "Beta users get the new checkout" is a *rule*,
>    not a constant — so the test feeds **user/segment attributes** through the `EvaluationContext` (OpenFeature)
>    / `Context` (LaunchDarkly) and asserts the right variation lands for a matching context, a non-matching
>    context, **and the fallthrough/default** (the forgotten third case). With `TestData` the *real* LaunchDarkly
>    evaluation engine runs your rule — you're testing the targeting semantics, not a hand-rolled stub of them.
> 4. **Flag lifecycle is part of the discipline.** A kill-switch only earns its name if flipping it **mid-flight**
>    actually degrades gracefully — `td.Update(...)` propagates to a live client like a streamed change, so one
>    test proves the off-path engages *without a restart* (the flag analogue of `qa-failure-injection-testing-dotnet`'s
>    heal-and-recover). And flag state is **cleaned between tests** (fresh provider/fixture per test or rebuilt
>    in `[SetUp]`) so a pinned flag never leaks into the next test — test independence.

## Decision matrix — flag scenario → mechanism → what you assert

| You want to prove | Pin via | Assert |
|---|---|---|
| **Behavior with the flag ON** | `InMemoryProvider` flag default variant `"on"` / `td.Flag(k).VariationForAll(true)` | the new path's behavior (response shape, UI state, side effect) |
| **Behavior with the flag OFF** (the rollback path) | same fixture, `"off"` / `VariationForAll(false)` | the **legacy** path still works — the branch your un-migrated users live in |
| **Every variation of a multivariate flag** | variants dictionary / `Variations(LdValue...)` + a parameterized matrix | one row per variation; the matrix is exhaustive (idea #2) |
| **A targeting rule routes the right users** | variant-key context evaluator (OpenFeature) / `IfMatch(...).ThenReturn(...)` (TestData — real LD rule engine) | matching context → new variation; non-matching → fallthrough; **default asserted explicitly** |
| **A specific user/key is targeted** | `td.Flag(k).VariationForKey(ContextKind.Default, "user-key", true)` | that key gets the variation; any other key gets the fallthrough |
| **The kill-switch degrades gracefully mid-flight** | flip with `td.Update(...)` while the client is live | before: feature on; after the flip (no restart): the off-path/fallback engages |
| **The code uses the contracted default when evaluation fails** | unknown flag key / no provider for the domain | the *code default* (the value passed to `GetBooleanValueAsync(key, default)`) drives a safe path |
| **Flag state never leaks between tests** | fresh fixture per test (`[SetUp]`) | any test runs alone and in any order — independence |

## Stack

- .NET 8, **NUnit** (the global default .NET runner) + **FluentAssertions** + **Allure.NUnit**
- **OpenFeature** — the `OpenFeature` NuGet — the vendor-neutral API the *production code* talks
  (`IFeatureClient.GetBooleanValueAsync/GetStringValueAsync/...`), plus the built-in test spine:
  `OpenFeature.Providers.Memory.InMemoryProvider` + `Flag<T>`
- **LaunchDarkly server SDK** — `LaunchDarkly.ServerSdk` — for projects on LaunchDarkly; its
  `LaunchDarkly.Sdk.Server.Integrations.TestData` fixture is the deterministic data source
- **LaunchDarkly OpenFeature provider** — `LaunchDarkly.OpenFeature.ServerProvider` — bridges the two: prod code
  stays on OpenFeature, `TestData` pins what the LD provider sees
- Layout: `Tests/Flags/` (the flag tests), `Tests/Support/Flags/` (the `FlagFixture` helper)

```xml
<!-- Tests.csproj (excerpt) -->
<ItemGroup>
  <PackageReference Include="OpenFeature" Version="2.13.0" />                          <!-- includes InMemoryProvider -->
  <PackageReference Include="LaunchDarkly.ServerSdk" Version="8.6.0" />                <!-- includes TestData -->
  <PackageReference Include="LaunchDarkly.OpenFeature.ServerProvider" Version="2.1.0" />
  <PackageReference Include="NUnit" Version="4.2.2" />
  <PackageReference Include="FluentAssertions" Version="6.12.1" />
</ItemGroup>
```

> **Which path?** **OpenFeature `InMemoryProvider`** when the code under test talks the OpenFeature API (the
> recommended posture — vendor-neutral, no LD dependency in the test). **LaunchDarkly `TestData`** when the code
> talks the LD SDK directly, *or* when you need the **real LD evaluation engine** to run a targeting rule /
> per-key target / fallthrough exactly as production would (idea #3). They compose via the LD OpenFeature
> provider. Either way the production SDK key and the live flag service are **absent from the test**.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Path A — OpenFeature `InMemoryProvider` (the vendor-neutral spine, idea #1)**; **Path B — LaunchDarkly `TestData` (the named real-provider path)**.

## The code default — the third state every flag has

Every evaluation carries a **code default** (`GetBooleanValueAsync("key", false)` / `BoolVariation(..., false)`)
used when the flag is missing or the provider isn't ready. That default is a *contract*: it must select the
**safe** branch. Test it by evaluating a key the fixture never defined.

```csharp
[Test]
public async Task Should_FallBackToTheSafeLegacyPath_When_TheFlagIsUnknown()
{
    var flags = await new FlagFixture("checkout").ClientAsync();   // NO flags pinned at all

    var checkout = new CheckoutService(flags);

    // The code default (false → classic) drives the behavior — the safe branch, asserted explicitly.
    (await checkout.StartCheckoutAsync("sku-1")).Flow.Should().Be("classic-checkout");
}
```

## The boundary — flag *testing* vs flag *management*

This skill tests **code that branches on a flag**, with the flag state pinned in-process. It is **not** flag
management or rollout strategy: creating flags in the dashboard, percentage rollouts, prerequisites,
experimentation/A-B *analytics*, or flag-cleanup tooling are platform ops, out of scope. Two adjacent boundaries
worth drawing every time: stale-flag hygiene (a flag whose both-sides tests have asserted the same behavior for
months is a removal candidate — flag it in review, don't let the matrix rot), and the kill-switch *off-path
behavior* (this skill) vs a *dependency fault* behind it (`qa-failure-injection-testing-dotnet`).

## Anti-patterns

- **Evaluating against the live/remote flag service** (the production SDK key + streaming connection in a test).
  Nondeterministic, environment-coupled, and someone flipping a dashboard toggle changes what your suite means.
  *Fix:* `InMemoryProvider` / `TestData` wired in setup; the live service and real key never appear (idea #1).
- **Stubbing the flag service's HTTP endpoint with WireMock.** You'd be reverse-engineering the SDK's wire
  protocol (polling/streaming payload shapes) — brittle and pointless when the SDK ships a **first-class test
  fixture**. *Fix:* the SDK's own test source.
- **Testing only the flag-on path.** Zero coverage of the branch your un-migrated users run, zero proof the
  rollback is safe. *Fix:* the on/off (or all-variations) matrix — every flag-touching behavior, both sides (idea #2).
- **Asserting only "no error" on the off-row.** The legacy branch has its *own* contract. *Fix:* the off-row
  asserts the legacy behavior as specifically as the on-row asserts the new one.
- **Hand-rolling a targeting stub instead of testing the rule.** `Setup(f => f.IsEnabled(It.IsAny<...>())).Returns(true)`
  bypasses the targeting semantics entirely. *Fix:* feed attributes through the `EvaluationContext` / `Context`
  and let the (in-memory or real-LD) engine evaluate; assert matching, non-matching, **and fallthrough** (idea #3).
- **Forgetting the fallthrough/default cases.** Targeting bugs live where no rule matches — and the *code default*
  is a separate, third state. *Fix:* one assertion per case: match / no-match / fallthrough; plus the
  unknown-flag test for the code default.
- **Flag state leaking between tests.** A test that pins `new-checkout=on` in a shared singleton poisons every
  test after it — order-dependent failures. *Fix:* fresh fixture per test (`[SetUp]`), domain-scoped OpenFeature
  clients (`Api.Instance` is shared state — scope it), `Dispose()` the `LdClient` in `[TearDown]`.
- **`if (flagEnabled) { Assert A } else { Assert B }` inside one test.** Conditional logic in tests is banned —
  and it means the test passes no matter which branch ran. *Fix:* the parameterized matrix: one `[TestCase]` row
  per state, each with its own expected value.
- **Blocking on the async evaluation API.** `.Result` / `.GetAwaiter().GetResult()` on `GetBooleanValueAsync` is
  banned. *Fix:* async all the way — `async Task` tests, `await` every evaluation.
- **Treating a kill-switch as config you only test statically.** A kill-switch that's never been flipped
  mid-flight in a test is a hope, not a control. *Fix:* the lifecycle test — on → `td.Update(off)` → assert the
  degradation path, no restart (idea #4).

## Examples

**End-to-end: the inverted reflex.** An environment-coupled suite reads
`GetBooleanValueAsync("new-checkout", false)` against whatever the staging environment says — green Monday, red
Tuesday, and the off-path never runs. This skill's author writes: a `FlagFixture` pinning `new-checkout` per row,
a two-row `[TestCase]` matrix asserting `express-checkout` *and* `classic-checkout`, a context test for the beta
rule with the fallthrough asserted, and a kill-switch flip test. Same flag, deterministic — and **both** branches
covered.

**Composing with the neighbors.** The branch under test often *contains* the things other skills assert — the
on-path writes a new table (`qa-db-connection-dotnet`), emits a new event
(`qa-messaging-testing-dotnet`), or renders a new page (`qa-ui-test-writer-playwright-dotnet`). This
skill pins which branch runs; those skills assert what the branch does. The variation matrix binds through
`qa-data-driven-testing-dotnet`; the kill-switch degradation assertion borders `qa-failure-injection-testing-dotnet` (flag
flip vs dependency fault — adjacent, not the same).

## Rules (hard constraints)

- **Pin the flag state in-process — never evaluate against a live/remote flag service in a test.** OpenFeature
  `InMemoryProvider` or LaunchDarkly `TestData`, wired in setup. The production SDK key never appears in a test
  run (and no real key in code anyway — no secrets in code).
- **Every flag-touching behavior is tested on BOTH sides** (every variation for multivariate) via a parameterized
  matrix — never only the on-path, never conditional logic inside a test.
- **The off-row asserts the legacy branch's own contract**, not merely "no error".
- **Targeting rules are exercised through the evaluation context** (`EvaluationContext` / `Context`), asserting
  match, no-match, **and the fallthrough/default** — plus the **code default** via an unknown-flag evaluation.
- **Don't stub the flag service's HTTP wire** — use the SDK's first-class test source; WireMock is for
  dependencies that lack one.
- **Kill-switches get a lifecycle test**: on → flip via `td.Update(...)` mid-flight → assert the degradation path
  engages without a restart.
- **Flag state never leaks between tests**: fresh fixture per test, domain-scoped OpenFeature clients
  (`Api.Instance` is shared state), `Dispose()` the `LdClient` in teardown. Tests run alone, in any order.
- **The flag client is constructor-injected** into the code under test — never a static lookup. NUnit +
  FluentAssertions; **async all the way** (`await SetProviderAsync` so the first evaluation never races
  initialization; never `.Result`).

## Cross-references

- `qa-feature-flag-testing-java` — the **canonical** stack this sibling is ported from (`dev.openfeature:sdk` +
  `launchdarkly-java-server-sdk` `TestData` + TestNG); same four ideas, same fixtures, different SDK surface.
- `qa-feature-flag-testing-typescript` — the other sibling (`@openfeature/server-sdk` +
  `@launchdarkly/node-server-sdk` `TestData` + Vitest).
- `qa-data-driven-testing-dotnet` — the **matrix mechanics** the on/off/variation table binds through
  (`[TestCase]`/`[TestCaseSource]` row-binding); this skill defines *what* the rows are, that one defines *how*
  rows drive tests.
- `qa-failure-injection-testing-dotnet` — the **kill-switch boundary**: the off-path of a flag flip is this skill; a
  faulted dependency behind the feature is chaos. The lifecycle shape (steady → perturb → assert-degraded) is shared.
- `qa-api-test-writer-dotnet` · `qa-ui-test-writer-playwright-dotnet` — the branch under test is
  usually an API or UI behavior; those skills own the assertion style inside each pinned branch.
- `qa-test-login-tokens-dotnet` — the same "test fixture over live service" posture applied to auth; pairs
  when targeting rules key off claims-derived attributes.
- `qa-test-reports-dotnet` — render the flag matrix as named results (one per variation row).
