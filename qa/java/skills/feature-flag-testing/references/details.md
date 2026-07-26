# Deep-dive details — `qa-feature-flag-testing-java`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

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
the off-path engages *without a restart*. This is the flag analogue of `qa-failure-injection-testing-java`'s
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
