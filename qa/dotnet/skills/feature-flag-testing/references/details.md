# Deep-dive details — `qa-dotnet:feature-flag-testing`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Path A — OpenFeature `InMemoryProvider` (the vendor-neutral spine, idea #1)

The provider is the seam. Production code asks an OpenFeature `IFeatureClient` for flag values; the test swaps in
an `InMemoryProvider` holding exactly the flags the scenario pins. **Use a domain-scoped provider + client**
(`SetProviderAsync("checkout", ...)` / `GetClient("checkout")`) — `Api.Instance` is a global singleton, and a
domain keeps parallel test fixtures from clobbering each other's provider (no static mutable state leaking across
tests). In .NET the `Flag<T>` context evaluator returns the **variant key** for a given context.

```csharp
namespace Tests.Support.Flags;

using OpenFeature;
using OpenFeature.Model;
using OpenFeature.Providers.Memory;

/// <summary>Pins flag state for one test: a fresh InMemoryProvider per fixture, bound to a domain-scoped client.</summary>
public sealed class FlagFixture
{
    private readonly string _domain;
    private readonly Dictionary<string, Flag> _flags = new();

    public FlagFixture(string domain) => _domain = domain;

    /// <summary>Pin a boolean flag to a fixed state — the simplest "pin, don't fetch".</summary>
    public FlagFixture WithBooleanFlag(string key, bool enabled)
    {
        _flags[key] = new Flag<bool>(
            new Dictionary<string, bool> { ["on"] = true, ["off"] = false },
            enabled ? "on" : "off");
        return this;
    }

    /// <summary>Pin a multivariate flag to one named variant (test EVERY variant via the matrix, idea #2).</summary>
    public FlagFixture WithVariant<T>(string key, Dictionary<string, T> variants, string selected)
    {
        _flags[key] = new Flag<T>(variants, selected);
        return this;
    }

    /// <summary>Pin a context-aware rule: the evaluator picks the VARIANT KEY from the EvaluationContext (idea #3).</summary>
    public FlagFixture WithRule<T>(string key, Dictionary<string, T> variants, string defaultVariant,
                                   Func<EvaluationContext, string> variantForContext)
    {
        _flags[key] = new Flag<T>(variants, defaultVariant, variantForContext);
        return this;
    }

    /// <summary>Wire the pinned flags in and return the client the code under test should use.</summary>
    public async Task<IFeatureClient> ClientAsync()
    {
        await Api.Instance.SetProviderAsync(_domain, new InMemoryProvider(_flags));   // awaits READY — no race on first read
        return Api.Instance.GetClient(_domain);
    }
}
```

### Both sides of the branch — the on/off matrix (idea #2)

One parameterized test per flag-touching behavior; one row per flag state. The rows pin the flag; the assertions
verify **each branch's own contract** — the off-row asserts the *legacy* behavior, not merely "no error".

```csharp
namespace Tests.Flags;

using FluentAssertions;
using NUnit.Framework;
using Tests.Support.Flags;

[TestFixture]
public class CheckoutFlagTests
{
    // flagState | expectedFlow — BOTH sides, every run (idea #2)
    [TestCase(true,  "express-checkout")]
    [TestCase(false, "classic-checkout")]
    public async Task Should_RouteToTheContractedFlow_When_TheFlagIsInEachState(bool enabled, string expectedFlow)
    {
        var flags = await new FlagFixture("checkout")
            .WithBooleanFlag("new-checkout", enabled)            // PINNED — not fetched (idea #1)
            .ClientAsync();

        var checkout = new CheckoutService(flags);               // constructor injection — the client is a dependency

        var result = await checkout.StartCheckoutAsync("sku-1");
        result.Flow.Should().Be(expectedFlow, "flag {0} routes to its contracted flow", enabled ? "on" : "off");
    }
}
```

> The off-row is **not** a formality: it is the only coverage of the path every un-migrated user is on, and the
> only proof a rollback is safe. A multivariate flag gets one row per variation — exhaustively (`control` /
> `treatment-a` / `treatment-b`), via the same `[TestCase]`/`[TestCaseSource]` mechanics as
> `qa-dotnet:data-driven-testing`.

### Targeting via the evaluation context (idea #3)

The rule lives in the fixture; the test varies the **context** and asserts three cases — matching, non-matching,
and **the fallthrough/default** (the case targeting bugs hide in).

```csharp
[Test]
public async Task Should_ServeTheNewCheckout_When_TheUserIsBetaTierOnly()
{
    var flags = await new FlagFixture("checkout")
        .WithRule("new-checkout",
            new Dictionary<string, bool> { ["on"] = true, ["off"] = false }, "off",
            ctx => ctx.TryGetValue("tier", out var tier) && tier.AsString == "beta" ? "on" : "off")
        .ClientAsync();

    var betaUser   = EvaluationContext.Builder().SetTargetingKey("user-1").Set("tier", "beta").Build();
    var freeUser   = EvaluationContext.Builder().SetTargetingKey("user-2").Set("tier", "free").Build();
    var anonNoTier = EvaluationContext.Builder().SetTargetingKey("user-3").Build();   // the forgotten third case

    (await flags.GetBooleanValueAsync("new-checkout", false, betaUser)).Should().BeTrue("matching context");
    (await flags.GetBooleanValueAsync("new-checkout", false, freeUser)).Should().BeFalse("non-matching context");
    (await flags.GetBooleanValueAsync("new-checkout", false, anonNoTier)).Should().BeFalse("fallthrough/default");
}
```

## Path B — LaunchDarkly `TestData` (the named real-provider path)

`TestData.DataSource()` replaces LaunchDarkly's streaming connection with a programmable in-process source — the
**real LD evaluation engine** runs your targeting rules against it. Wire it into the configuration with
`Components.NoEvents` (no analytics leave the test) — the SDK key is a placeholder, never the production key.

```csharp
namespace Tests.Support.Flags;

using LaunchDarkly.Sdk.Server;
using LaunchDarkly.Sdk.Server.Integrations;

/// <summary>A deterministic LdClient: TestData replaces the stream; no events; placeholder key.</summary>
public sealed class LaunchDarklyFixture : IDisposable
{
    public TestData Data { get; } = TestData.DataSource();
    public LdClient Client { get; }

    public LaunchDarklyFixture()
    {
        var config = Configuration.Builder("test-sdk-key-not-real")
            .DataSource(Data)                     // PINNED in-process — never the live service (idea #1)
            .Events(Components.NoEvents)          // no analytics calls leave the test run
            .Build();
        Client = new LdClient(config);
    }

    public void Dispose() => Client.Dispose();
}
```

### Targeting with the real rule engine — `IfMatch` / `VariationForKey` / fallthrough

```csharp
namespace Tests.Flags;

using FluentAssertions;
using LaunchDarkly.Sdk;
using NUnit.Framework;
using Tests.Support.Flags;

[TestFixture]
public class BetaTargetingTests
{
    private LaunchDarklyFixture _ld = null!;

    [SetUp]
    public void FreshFlagState() => _ld = new LaunchDarklyFixture();     // no leakage between tests (idea #4)

    [TearDown]
    public void CloseClient() => _ld.Dispose();

    [Test]
    public void Should_TargetBetaTierAndOneNamedUser_When_EveryoneElseFallsThrough()
    {
        _ld.Data.Update(_ld.Data.Flag("new-checkout")
            .BooleanFlag()
            .VariationForKey(ContextKind.Default, "qa-canary", true)     // a per-key target
            .IfMatch("tier", LdValue.Of("beta")).ThenReturn(true)        // a rule — evaluated by the REAL engine
            .FallthroughVariation(false));                               // the explicit default

        var canary = Context.Builder("qa-canary").Build();
        var beta   = Context.Builder("user-7").Set("tier", "beta").Build();
        var free   = Context.Builder("user-9").Set("tier", "free").Build();

        _ld.Client.BoolVariation("new-checkout", canary, false).Should().BeTrue("named key targeted");
        _ld.Client.BoolVariation("new-checkout", beta, false).Should().BeTrue("rule match");
        _ld.Client.BoolVariation("new-checkout", free, false).Should().BeFalse("fallthrough");
    }
}
```

### The kill-switch lifecycle — flip mid-flight, assert graceful degradation (idea #4)

`td.Update(...)` propagates to the live client **as if LaunchDarkly streamed the change** — so one test proves
the off-path engages *without a restart*. This is the flag analogue of `qa-dotnet:failure-injection-testing`'s
steady → perturb → assert-degraded lifecycle (and the boundary: a *flag* flip is this skill; a *dependency fault*
is chaos).

```csharp
[Test]
public async Task Should_EngageTheRecommendationsFallback_When_TheKillSwitchFlipsMidFlight()
{
    _ld.Data.Update(_ld.Data.Flag("recommendations-enabled").BooleanFlag().VariationForAll(true));
    var page = new ProductPageService(_ld.Client);

    // 1. steady state — the feature is on and serving.
    (await page.RenderAsync("sku-1")).HasRecommendations.Should().BeTrue();

    // 2. flip the kill-switch — no restart, no redeploy; propagates like a streamed change.
    _ld.Data.Update(_ld.Data.Flag("recommendations-enabled").BooleanFlag().VariationForAll(false));

    // 3. assert the DEGRADED path: the page still renders, recommendations replaced by the contracted fallback.
    var degraded = await page.RenderAsync("sku-1");
    degraded.IsRendered.Should().BeTrue("page survives the kill");
    degraded.HasRecommendations.Should().BeFalse("feature is off");
    degraded.FallbackMessage.Should().Be("Recommendations are temporarily unavailable");
}
```

### Bridging both — prod code on OpenFeature, `TestData` behind the LD provider

When production talks OpenFeature but the org runs LaunchDarkly, compose the two: the test builds the
`TestData`-backed `LdClient`, wraps it in the LD OpenFeature provider, and the code under test stays
vendor-neutral.

```csharp
using LaunchDarkly.OpenFeature.ServerProvider;

await Api.Instance.SetProviderAsync("checkout", new Provider(_ld.Client));   // LD provider over the TestData-backed client
var flags = Api.Instance.GetClient("checkout");                              // prod-shaped: pure OpenFeature
```
