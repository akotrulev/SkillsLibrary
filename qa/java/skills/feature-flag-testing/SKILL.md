---
name: qa-feature-flag-testing-java
description: >-
  Write **feature-flag** tests in Java 21 with **OpenFeature** (`dev.openfeature:sdk` + its built-in
  **`InMemoryProvider`**) as the vendor-neutral spine and **LaunchDarkly** (`launchdarkly-java-server-sdk` +
  its first-class **`TestData`** fixture) as the named real-provider path + TestNG, proving code whose behavior
  **branches on a flag** is correct on EVERY branch. Covers the trait that makes a flag test deterministic:
  **you NEVER evaluate the flag against a live/remote flag service — you PIN the flag state inside the test**
  (an in-memory/test data source wired in setup; the production SDK key never appears in a test run), because
  "run against whatever the environment's flags say" makes the test nondeterministic, environment-coupled, and
  incapable of exercising the *other* branch. The discipline: **a flag is a branch — test BOTH sides** (and every
  variation of a multivariate flag) as a matrix; **targeting rules are tested via the evaluation context**
  (user/segment attributes in `EvaluationContext` / `LDContext` → assert the right variation lands, incl. the
  fallthrough/default); **flag lifecycle is part of the test** (flip a kill-switch mid-test via `td.update(...)`
  and assert the degradation path engages without a restart; clean flag state between tests so it never leaks).
  Covers OpenFeature `Flag.builder()` variants + `contextEvaluator`, `setProviderAndWait`, domain-scoped clients,
  `InMemoryProvider.updateFlags`, LaunchDarkly `TestData.dataSource()`, `FlagBuilder`
  (`booleanFlag`/`variations`/`variationForKey`/`ifMatch`/`fallthroughVariation`), `Components.noEvents()`, and
  the LaunchDarkly OpenFeature provider bridging both. Triggers: "test a feature flag / feature toggle", "test
  both sides of a flag", "pin a flag state in tests", "test LaunchDarkly targeting rules", "OpenFeature
  InMemoryProvider test", "test the kill-switch path", "our test fails depending on which flags are on in the
  environment". Do NOT use for: the .NET stack (use qa-feature-flag-testing-dotnet), the TypeScript stack (use
  qa-feature-flag-testing-typescript), stubbing the flag service's **HTTP endpoint** with WireMock (use the
  SDK's test data source instead — mocking the wire is the anti-pattern here, see qa-api-mocking-wiremock-java
  only for dependencies that have no test fixture), standing the flag service up as a **container** (flag state
  is pinned in-process, not via qa-test-environments-java), **dependency-fault** resilience (a broken DB/API is
  qa-chaos-testing-java; a kill-switch *flag* flip is this skill), the generic **parameterized-matrix mechanics**
  (qa-data-driven-testing-java — the on/off table binds through it), or flag **management/rollout strategy**
  (percentage rollouts, experimentation/A-B analytics, dashboard ops — out of scope).
---

# QA — Feature-Flag Testing (Java 21 / OpenFeature + LaunchDarkly `TestData` + TestNG) — **canonical stack**

Scaffolds **deterministic feature-flag tests** in Java for code whose behavior branches on a flag, using
[**OpenFeature**](https://openfeature.dev) — the CNCF vendor-neutral flag API — with its built-in
**`InMemoryProvider`** as the test spine, and [**LaunchDarkly**](https://launchdarkly.com)'s server SDK
**`TestData`** fixture as the named real-provider path (the two compose: production code talks OpenFeature, the
LaunchDarkly OpenFeature provider sits behind it, and `TestData` pins what that provider sees). This is the
**canonical** stack of the 3-stack `feature-flag-testing` family by the user's explicit choice: it pairs with the
TestNG spine the way #36/#39 do, and the OpenFeature Java SDK + LaunchDarkly Java server SDK story is mature and
first-class. The `dotnet` and `typescript` siblings are **ported** from this file — the moves are identical; only
the SDK surface changes.

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
>    (`qa-data-driven-testing-java` mechanics), not copy-pasted test methods.
> 3. **Targeting rules are tested via the evaluation context.** "Beta users get the new checkout" is a *rule*,
>    not a constant — so the test feeds **user/segment attributes** through the `EvaluationContext` (OpenFeature)
>    / `LDContext` (LaunchDarkly) and asserts the right variation lands for a matching context, a non-matching
>    context, **and the fallthrough/default** (the forgotten third case). With `TestData` the *real* LaunchDarkly
>    evaluation engine runs your rule — you're testing the targeting semantics, not a hand-rolled stub of them.
> 4. **Flag lifecycle is part of the discipline.** A kill-switch only earns its name if flipping it **mid-flight**
>    actually degrades gracefully — `td.update(...)` propagates to a live client like a streamed change, so one
>    test proves the off-path engages *without a restart* (the flag analogue of `qa-chaos-testing-java`'s
>    heal-and-recover). And flag state is **cleaned between tests** (fresh provider/fixture per test or
>    rebuilt in `@BeforeMethod`) so a pinned flag never leaks into the next test — test independence.

## Decision matrix — flag scenario → mechanism → what you assert

| You want to prove | Pin via | Assert |
|---|---|---|
| **Behavior with the flag ON** | `InMemoryProvider` flag `defaultVariant("on")` / `td.flag(k).variationForAll(true)` | the new path's behavior (response shape, UI state, side effect) |
| **Behavior with the flag OFF** (the rollback path) | same fixture, `"off"` / `variationForAll(false)` | the **legacy** path still works — the branch your un-migrated users live in |
| **Every variation of a multivariate flag** | variants map / `variations(LDValue...)` + a parameterized matrix | one row per variation; the matrix is exhaustive (idea #2) |
| **A targeting rule routes the right users** | `contextEvaluator` (OpenFeature) / `ifMatch(...).thenReturn(...)` (TestData — real LD rule engine) | matching context → new variation; non-matching → fallthrough; **default asserted explicitly** |
| **A specific user/key is targeted** | `td.flag(k).variationForKey(ContextKind.DEFAULT, "user-key", true)` | that key gets the variation; any other key gets the fallthrough |
| **The kill-switch degrades gracefully mid-flight** | flip with `td.update(...)` while the client is live | before: feature on; after the flip (no restart): the off-path/fallback engages |
| **The code uses the contracted default when evaluation fails** | unknown flag key / no provider for the domain | the *code default* (the value passed to `getBooleanValue(key, default)`) drives a safe path |
| **Flag state never leaks between tests** | fresh fixture per test (`@BeforeMethod`) | any test runs alone and in any order — independence |

## Stack

- Java 21, Gradle (Kotlin DSL), **TestNG** (the global default Java runner) + **AssertJ** + **Allure TestNG**
- **OpenFeature** — `dev.openfeature:sdk` — the vendor-neutral API the *production code* talks
  (`Client.getBooleanValue/getStringValue/...`), plus the built-in test spine:
  `dev.openfeature.sdk.providers.memory.InMemoryProvider` + `Flag.builder()`
- **LaunchDarkly server SDK** — `com.launchdarkly:launchdarkly-java-server-sdk` — for projects on LaunchDarkly;
  its `com.launchdarkly.sdk.server.integrations.TestData` fixture is the deterministic data source
- **LaunchDarkly OpenFeature provider** — `com.launchdarkly:launchdarkly-openfeature-serverprovider` — bridges
  the two: prod code stays on OpenFeature, `TestData` pins what the LD provider sees
- Layout: `src/test/java/flags/` (the flag tests), `src/test/java/support/flags/` (the `FlagFixture` helper)

```kotlin
// build.gradle.kts (excerpt)
dependencies {
    testImplementation("dev.openfeature:sdk:1.20.2")                                   // includes InMemoryProvider
    testImplementation("com.launchdarkly:launchdarkly-java-server-sdk:7.4.1")          // includes TestData
    testImplementation("com.launchdarkly:launchdarkly-openfeature-serverprovider:1.1.1")
    testImplementation("org.testng:testng:7.10.2")
    testImplementation("org.assertj:assertj-core:3.26.3")
    testImplementation("io.qameta.allure:allure-testng:2.29.0")
}
```

> **Which path?** **OpenFeature `InMemoryProvider`** when the code under test talks the OpenFeature API (the
> recommended posture — vendor-neutral, no LD dependency in the test). **LaunchDarkly `TestData`** when the code
> talks the LD SDK directly, *or* when you need the **real LD evaluation engine** to run a targeting rule /
> per-key target / fallthrough exactly as production would (idea #3). They compose via the LD OpenFeature
> provider. Either way the production SDK key and the live flag service are **absent from the test**.

## Path A — OpenFeature `InMemoryProvider` (the vendor-neutral spine, idea #1)

The provider is the seam. Production code asks an OpenFeature `Client` for flag values; the test swaps in an
`InMemoryProvider` holding exactly the flags the scenario pins. **Use a domain-scoped provider + client**
(`setProviderAndWait("checkout", ...)` / `getClient("checkout")`) — `OpenFeatureAPI` is a global singleton, and a
domain keeps parallel test classes from clobbering each other's provider (no static mutable state leaking across
tests).

```java
package support.flags;

import dev.openfeature.sdk.Client;
import dev.openfeature.sdk.OpenFeatureAPI;
import dev.openfeature.sdk.providers.memory.Flag;
import dev.openfeature.sdk.providers.memory.InMemoryProvider;

import java.util.HashMap;
import java.util.Map;

/** Pins flag state for one test: a fresh InMemoryProvider per fixture, bound to a domain-scoped client. */
public final class FlagFixture {
    private final String domain;
    private final Map<String, Flag<?>> flags = new HashMap<>();

    public FlagFixture(String domain) { this.domain = domain; }

    /** Pin a boolean flag to a fixed state — the simplest "pin, don't fetch". */
    public FlagFixture withBooleanFlag(String key, boolean enabled) {
        flags.put(key, Flag.builder()
                .variant("on", true).variant("off", false)
                .defaultVariant(enabled ? "on" : "off")
                .build());
        return this;
    }

    /** Pin a multivariate flag to one named variant (test EVERY variant via the matrix, idea #2). */
    public FlagFixture withVariant(String key, Map<String, Object> variants, String selected) {
        Flag.FlagBuilder<Object> builder = Flag.builder();
        variants.forEach(builder::variant);
        flags.put(key, builder.defaultVariant(selected).build());
        return this;
    }

    /** Pin a context-aware rule: the evaluator routes by EvaluationContext attributes (idea #3). */
    public FlagFixture withRule(String key, dev.openfeature.sdk.providers.memory.ContextEvaluator<Object> rule,
                                Map<String, Object> variants, String defaultVariant) {
        Flag.FlagBuilder<Object> builder = Flag.builder();
        variants.forEach(builder::variant);
        flags.put(key, builder.defaultVariant(defaultVariant).contextEvaluator(rule).build());
        return this;
    }

    /** Wire the pinned flags in and return the client the code under test should use. */
    public Client client() {
        OpenFeatureAPI api = OpenFeatureAPI.getInstance();
        api.setProviderAndWait(domain, new InMemoryProvider(flags));   // blocks until READY — no race on first read
        return api.getClient(domain);
    }
}
```

### Both sides of the branch — the on/off matrix (idea #2)

One parameterized test per flag-touching behavior; one row per flag state. The rows pin the flag; the assertions
verify **each branch's own contract** — the off-row asserts the *legacy* behavior, not merely "no error".

```java
package flags;

import dev.openfeature.sdk.Client;
import org.testng.annotations.DataProvider;
import org.testng.annotations.Test;
import support.flags.FlagFixture;

import static org.assertj.core.api.Assertions.assertThat;

public class CheckoutFlagTest {

    @DataProvider(name = "newCheckoutFlagStates")
    public Object[][] newCheckoutFlagStates() {
        return new Object[][] {
            // flagState | expectedFlow      — BOTH sides, every run (idea #2)
            { true,        "express-checkout" },
            { false,       "classic-checkout" },
        };
    }

    @Test(dataProvider = "newCheckoutFlagStates")
    public void shouldRouteToTheFlowContractedForEachFlagState(boolean enabled, String expectedFlow) {
        Client flags = new FlagFixture("checkout")
                .withBooleanFlag("new-checkout", enabled)        // PINNED — not fetched (idea #1)
                .client();

        CheckoutService checkout = new CheckoutService(flags);   // constructor injection — the client is a dependency

        assertThat(checkout.startCheckout("sku-1").flow())
                .as("flag %s routes to its contracted flow", enabled ? "on" : "off")
                .isEqualTo(expectedFlow);
    }
}
```

> The off-row is **not** a formality: it is the only coverage of the path every un-migrated user is on, and the
> only proof a rollback is safe. A multivariate flag gets one row per variation — exhaustively (`control` /
> `treatment-a` / `treatment-b`), via the same `@DataProvider` mechanics as `qa-data-driven-testing-java`.

### Targeting via the evaluation context (idea #3)

The rule lives in the fixture; the test varies the **context** and asserts three cases — matching, non-matching,
and **the fallthrough/default** (the case targeting bugs hide in).

```java
@Test
public void shouldServeTheNewCheckoutOnlyToBetaTierUsers() {
    Client flags = new FlagFixture("checkout")
            .withRule("new-checkout",
                    (flag, ctx) -> "beta".equals(ctx.getValue("tier").asString())
                            ? flag.getVariants().get("on")
                            : flag.getVariants().get("off"),
                    java.util.Map.of("on", true, "off", false), "off")
            .client();

    var betaUser    = new dev.openfeature.sdk.MutableContext("user-1").add("tier", "beta");
    var freeUser    = new dev.openfeature.sdk.MutableContext("user-2").add("tier", "free");
    var anonNoTier  = new dev.openfeature.sdk.MutableContext("user-3");          // the forgotten third case

    assertThat(flags.getBooleanValue("new-checkout", false, betaUser)).as("matching context").isTrue();
    assertThat(flags.getBooleanValue("new-checkout", false, freeUser)).as("non-matching context").isFalse();
    assertThat(flags.getBooleanValue("new-checkout", false, anonNoTier)).as("fallthrough/default").isFalse();
}
```

## Path B — LaunchDarkly `TestData` (the named real-provider path)

`TestData.dataSource()` replaces LaunchDarkly's streaming connection with a programmable in-process source — the
**real LD evaluation engine** runs your targeting rules against it. Wire it into `LDConfig` with
`Components.noEvents()` (no analytics leave the test) — the SDK key is a placeholder, never the production key.

```java
package support.flags;

import com.launchdarkly.sdk.server.Components;
import com.launchdarkly.sdk.server.LDClient;
import com.launchdarkly.sdk.server.LDConfig;
import com.launchdarkly.sdk.server.integrations.TestData;

/** A deterministic LDClient: TestData replaces the stream; no events; placeholder key. */
public final class LaunchDarklyFixture {
    private final TestData td = TestData.dataSource();
    private final LDClient client;

    public LaunchDarklyFixture() {
        LDConfig config = new LDConfig.Builder()
                .dataSource(td)                       // PINNED in-process — never the live service (idea #1)
                .events(Components.noEvents())        // no analytics calls leave the test run
                .build();
        client = new LDClient("test-sdk-key-not-real", config);
    }

    public TestData data()     { return td; }         // mutate flags mid-test via td.update(...) (idea #4)
    public LDClient client()   { return client; }
    public void close() throws java.io.IOException { client.close(); }
}
```

### Targeting with the real rule engine — `ifMatch` / `variationForKey` / fallthrough

```java
package flags;

import com.launchdarkly.sdk.ContextKind;
import com.launchdarkly.sdk.LDContext;
import com.launchdarkly.sdk.LDValue;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;
import support.flags.LaunchDarklyFixture;

import static org.assertj.core.api.Assertions.assertThat;

public class BetaTargetingTest {
    private LaunchDarklyFixture ld;

    @BeforeMethod(alwaysRun = true)
    public void freshFlagState() { ld = new LaunchDarklyFixture(); }     // no leakage between tests (idea #4)

    @AfterMethod(alwaysRun = true)
    public void closeClient() throws Exception { ld.close(); }

    @Test
    public void shouldTargetBetaTierAndOneNamedUserAndFallThroughForEveryoneElse() {
        ld.data().update(ld.data().flag("new-checkout")
                .booleanFlag()
                .variationForKey(ContextKind.DEFAULT, "qa-canary", true)        // a per-key target
                .ifMatch("tier", LDValue.of("beta")).thenReturn(true)           // a rule — evaluated by the REAL engine
                .fallthroughVariation(false));                                  // the explicit default

        LDContext canary = LDContext.builder("qa-canary").build();
        LDContext beta   = LDContext.builder("user-7").set("tier", "beta").build();
        LDContext free   = LDContext.builder("user-9").set("tier", "free").build();

        assertThat(ld.client().boolVariation("new-checkout", canary, false)).as("named key targeted").isTrue();
        assertThat(ld.client().boolVariation("new-checkout", beta, false)).as("rule match").isTrue();
        assertThat(ld.client().boolVariation("new-checkout", free, false)).as("fallthrough").isFalse();
    }
}
```

### The kill-switch lifecycle — flip mid-flight, assert graceful degradation (idea #4)

`td.update(...)` propagates to the live client **as if LaunchDarkly streamed the change** — so one test proves
the off-path engages *without a restart*. This is the flag analogue of `qa-chaos-testing-java`'s
steady → perturb → assert-degraded lifecycle (and the boundary: a *flag* flip is this skill; a *dependency fault*
is chaos).

```java
@Test
public void shouldEngageTheRecommendationsFallbackWhenTheKillSwitchFlipsMidFlight() {
    ld.data().update(ld.data().flag("recommendations-enabled").booleanFlag().variationForAll(true));
    ProductPageService page = new ProductPageService(ld.client());

    // 1. steady state — the feature is on and serving.
    assertThat(page.render("sku-1").hasRecommendations()).isTrue();

    // 2. flip the kill-switch — no restart, no redeploy; propagates like a streamed change.
    ld.data().update(ld.data().flag("recommendations-enabled").booleanFlag().variationForAll(false));

    // 3. assert the DEGRADED path: the page still renders, recommendations replaced by the contracted fallback.
    var degraded = page.render("sku-1");
    assertThat(degraded.isRendered()).as("page survives the kill").isTrue();
    assertThat(degraded.hasRecommendations()).as("feature is off").isFalse();
    assertThat(degraded.fallbackMessage()).isEqualTo("Recommendations are temporarily unavailable");
}
```

### Bridging both — prod code on OpenFeature, `TestData` behind the LD provider

When production talks OpenFeature but the org runs LaunchDarkly, compose the two: the test builds the
`TestData`-backed `LDClient`, wraps it in the LD OpenFeature provider, and the code under test stays
vendor-neutral.

```java
import com.launchdarkly.openfeature.serverprovider.Provider;

OpenFeatureAPI api = OpenFeatureAPI.getInstance();
api.setProviderAndWait("checkout", new Provider(ld.client()));   // LD provider over the TestData-backed client
Client flags = api.getClient("checkout");                        // prod-shaped: pure OpenFeature
```

## The code default — the third state every flag has

Every evaluation carries a **code default** (`getBooleanValue("key", false)` / `boolVariation(..., false)`) used
when the flag is missing or the provider isn't ready. That default is a *contract*: it must select the **safe**
branch. Test it by evaluating a key the fixture never defined.

```java
@Test
public void shouldFallBackToTheSafeLegacyPathWhenTheFlagIsUnknown() {
    Client flags = new FlagFixture("checkout").client();         // NO flags pinned at all

    CheckoutService checkout = new CheckoutService(flags);

    // The code default (false → classic) drives the behavior — the safe branch, asserted explicitly.
    assertThat(checkout.startCheckout("sku-1").flow()).isEqualTo("classic-checkout");
}
```

## The boundary — flag *testing* vs flag *management*

This skill tests **code that branches on a flag**, with the flag state pinned in-process. It is **not** flag
management or rollout strategy: creating flags in the dashboard, percentage rollouts, prerequisites,
experimentation/A-B *analytics*, or flag-cleanup tooling are platform ops, out of scope. Two adjacent boundaries
worth drawing every time: stale-flag hygiene (a flag whose both-sides tests have asserted the same behavior for
months is a removal candidate — flag it in review, don't let the matrix rot), and the kill-switch *off-path
behavior* (this skill) vs a *dependency fault* behind it (`qa-chaos-testing-java`).

## Anti-patterns

- **Evaluating against the live/remote flag service** (the production SDK key + streaming connection in a test).
  Nondeterministic, environment-coupled, and someone flipping a dashboard toggle changes what your suite means.
  *Fix:* `InMemoryProvider` / `TestData` wired in setup; the live service and real key never appear (idea #1).
- **Stubbing the flag service's HTTP endpoint with WireMock.** You'd be reverse-engineering the SDK's wire
  protocol (polling/streaming payload shapes) — brittle and pointless when the SDK ships a **first-class test
  fixture**. *Fix:* the SDK's own test source; reserve `qa-api-mocking-wiremock-java` for dependencies without one.
- **Testing only the flag-on path.** Zero coverage of the branch your un-migrated users run, zero proof the
  rollback is safe. *Fix:* the on/off (or all-variations) matrix — every flag-touching behavior, both sides (idea #2).
- **Asserting only "no error" on the off-row.** The legacy branch has its *own* contract. *Fix:* the off-row
  asserts the legacy behavior as specifically as the on-row asserts the new one.
- **Hand-rolling a targeting stub instead of testing the rule.** `when(flags.isEnabled(any())).thenReturn(true)`
  bypasses the targeting semantics entirely. *Fix:* feed attributes through the `EvaluationContext` / `LDContext`
  and let the (in-memory or real-LD) engine evaluate; assert matching, non-matching, **and fallthrough** (idea #3).
- **Forgetting the fallthrough/default cases.** Targeting bugs live where no rule matches — and the *code default*
  is a separate, third state. *Fix:* one assertion per case: match / no-match / fallthrough; plus the
  unknown-flag test for the code default.
- **Flag state leaking between tests.** A `@Test` that pins `new-checkout=on` in a shared singleton poisons every
  test after it — order-dependent failures. *Fix:* fresh fixture per test (`@BeforeMethod`), domain-scoped
  OpenFeature clients (the global `OpenFeatureAPI` is shared state — scope it), close `LDClient`s in teardown.
- **`if (flagEnabled) { assert A } else { assert B }` inside one test.** Conditional logic in tests is banned —
  and it means the test passes no matter which branch ran. *Fix:* the parameterized matrix: one row per state,
  each with its own expected value.
- **Treating a kill-switch as config you only test statically.** A kill-switch that's never been flipped
  mid-flight in a test is a hope, not a control. *Fix:* the lifecycle test — on → `td.update(off)` → assert the
  degradation path, no restart (idea #4).

## Examples

**End-to-end: the inverted reflex.** An environment-coupled suite reads
`client.getBooleanValue("new-checkout", false)` against whatever the staging environment says — green Monday, red
Tuesday, and the off-path never runs. This skill's author writes: a `FlagFixture` pinning `new-checkout` per row,
a two-row matrix asserting `express-checkout` *and* `classic-checkout`, a context test for the beta rule with the
fallthrough asserted, and a kill-switch flip test. Same flag, deterministic — and **both** branches covered.

**Composing with the neighbors.** The branch under test often *contains* the things other skills assert — the
on-path writes a new table (`qa-db-testing-client-java`), emits a new event (`qa-messaging-testing-kafka-java`),
or renders a new page (`qa-ui-test-author-playwright-java`). This skill pins which branch runs; those skills
assert what the branch does. The variation matrix binds through `qa-data-driven-testing-java`; the kill-switch
degradation assertion borders `qa-chaos-testing-java` (flag flip vs dependency fault — adjacent, not the same).

## Rules (hard constraints)

- **Pin the flag state in-process — never evaluate against a live/remote flag service in a test.** OpenFeature
  `InMemoryProvider` or LaunchDarkly `TestData`, wired in setup. The production SDK key never appears in a test
  run (and no real key in code anyway — no secrets in code).
- **Every flag-touching behavior is tested on BOTH sides** (every variation for multivariate) via a parameterized
  matrix — never only the on-path, never conditional logic inside a test.
- **The off-row asserts the legacy branch's own contract**, not merely "no error".
- **Targeting rules are exercised through the evaluation context** (`EvaluationContext` / `LDContext`), asserting
  match, non-match, **and the fallthrough/default** — plus the **code default** via an unknown-flag evaluation.
- **Don't stub the flag service's HTTP wire** — use the SDK's first-class test source; WireMock is for
  dependencies that lack one.
- **Kill-switches get a lifecycle test**: on → flip via `td.update(...)` (or `updateFlags`) mid-flight → assert
  the degradation path engages without a restart.
- **Flag state never leaks between tests**: fresh fixture per test, domain-scoped OpenFeature clients (the
  `OpenFeatureAPI` singleton is shared state), `LDClient.close()` in teardown. Tests run alone, in any order.
- **The flag client is constructor-injected** into the code under test — never a static lookup. TestNG +
  AssertJ; `setProviderAndWait` (not the non-blocking set) so the first evaluation never races initialization.

## Cross-references

- `qa-feature-flag-testing-dotnet` · `qa-feature-flag-testing-typescript` — the sibling stacks (`OpenFeature`
  NuGet + `LaunchDarkly.ServerSdk` `TestData` + NUnit · `@openfeature/server-sdk` + `@launchdarkly/node-server-sdk`
  `TestData` + Vitest); same four ideas, same fixtures, different SDK surface.
- `qa-data-driven-testing-java` (#39) — the **matrix mechanics** the on/off/variation table binds through
  (`@DataProvider` row-binding); this skill defines *what* the rows are, that one defines *how* rows drive tests.
- `qa-chaos-testing-java` (#48) — the **kill-switch boundary**: the off-path of a flag flip is this skill; a
  faulted dependency behind the feature is chaos. The lifecycle shape (steady → perturb → assert-degraded) is shared.
- `qa-api-mocking-wiremock-java` (#22) — what **not** to reach for here: the flag SDKs ship first-class test
  sources, so stubbing their wire protocol is the anti-pattern; WireMock covers dependencies without a fixture.
- `qa-test-environments-java` (#14) — stands real dependencies up in containers; flag state is pinned
  **in-process**, no container needed — don't stand up a flag service to test a branch.
- `qa-api-test-author-generator-java` · `qa-ui-test-author-playwright-java` — the branch under test is usually an
  API or UI behavior; those skills own the assertion style inside each pinned branch.
- `qa-auth0-test-tokens-java` (#16) — the same "test fixture over live service" posture applied to auth; pairs
  when targeting rules key off claims-derived attributes.
- `qa-allure-reporting-java` — render the flag matrix as named results (one per variation row).
