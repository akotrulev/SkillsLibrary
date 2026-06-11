# Deep-dive details — `qa-feature-flag-testing-typescript`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Path B — LaunchDarkly `TestData` (the named real-provider path)

`new integrations.TestData()` replaces LaunchDarkly's streaming connection with a programmable in-process source
— the **real LD evaluation engine** runs your targeting rules against it. Wire it in via
`{ updateProcessor: td.getFactory(), sendEvents: false }` (no analytics leave the test) — the SDK key is a
placeholder, never the production key.

```typescript
// tests/support/flags/launchdarkly-fixture.ts
import { init, integrations, type LDClient } from '@launchdarkly/node-server-sdk';

/** A deterministic LDClient: TestData replaces the stream; no events; placeholder key. */
export class LaunchDarklyFixture {
  readonly data = new integrations.TestData();
  readonly client: LDClient;

  constructor() {
    this.client = init('test-sdk-key-not-real', {
      updateProcessor: this.data.getFactory(), // PINNED in-process — never the live service (idea #1)
      sendEvents: false,                       // no analytics calls leave the test run
    });
  }

  async ready(): Promise<void> {
    await this.client.waitForInitialization({ timeout: 10 });
  }

  close(): void {
    this.client.close();
  }
}
```

### Targeting with the real rule engine — `ifMatch` / `variationForContext` / fallthrough

```typescript
// tests/flags/beta-targeting.test.ts
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { LaunchDarklyFixture } from '../support/flags/launchdarkly-fixture';

describe('beta targeting for the new checkout', () => {
  let ld: LaunchDarklyFixture;

  beforeEach(async () => {
    ld = new LaunchDarklyFixture(); // fresh state — no leakage between tests (idea #4)
    await ld.ready();
  });

  afterEach(() => ld.close());

  it('should target beta tier and one named user, and fall through for everyone else', async () => {
    await ld.data.update(
      ld.data
        .flag('new-checkout')
        .booleanFlag()
        .variationForContext('user', 'qa-canary', true)   // a per-context target
        .ifMatch('user', 'tier', 'beta').thenReturn(true) // a rule — evaluated by the REAL engine
        .fallthroughVariation(false),                     // the explicit default
    );

    const canary = { kind: 'user', key: 'qa-canary' };
    const beta   = { kind: 'user', key: 'user-7', tier: 'beta' };
    const free   = { kind: 'user', key: 'user-9', tier: 'free' };

    await expect(ld.client.boolVariation('new-checkout', canary, false)).resolves.toBe(true);  // named key
    await expect(ld.client.boolVariation('new-checkout', beta, false)).resolves.toBe(true);    // rule match
    await expect(ld.client.boolVariation('new-checkout', free, false)).resolves.toBe(false);   // fallthrough
  });
});
```

### The kill-switch lifecycle — flip mid-flight, assert graceful degradation (idea #4)

`td.update(...)` propagates to the live client **as if LaunchDarkly streamed the change** — so one test proves
the off-path engages *without a restart*. This is the flag analogue of `qa-chaos-testing-typescript`'s
steady → perturb → assert-degraded lifecycle (and the boundary: a *flag* flip is this skill; a *dependency fault*
is chaos).

```typescript
it('should engage the recommendations fallback when the kill-switch flips mid-flight', async () => {
  await ld.data.update(ld.data.flag('recommendations-enabled').booleanFlag().variationForAll(true));
  const page = new ProductPageService(ld.client);

  // 1. steady state — the feature is on and serving.
  await expect(page.render('sku-1')).resolves.toMatchObject({ hasRecommendations: true });

  // 2. flip the kill-switch — no restart, no redeploy; propagates like a streamed change.
  await ld.data.update(ld.data.flag('recommendations-enabled').booleanFlag().variationForAll(false));

  // 3. assert the DEGRADED path: the page still renders, recommendations replaced by the contracted fallback.
  const degraded = await page.render('sku-1');
  expect(degraded.isRendered).toBe(true);                 // page survives the kill
  expect(degraded.hasRecommendations).toBe(false);        // feature is off
  expect(degraded.fallbackMessage).toBe('Recommendations are temporarily unavailable');
});
```

> On the OpenFeature path the same lifecycle runs through **`provider.putConfiguration({...})`** — it replaces
> the in-memory flag set and emits a configuration-changed event to the live client.

### Bridging both — prod code on OpenFeature, `TestData` behind the LD provider

When production talks OpenFeature but the org runs LaunchDarkly, compose the two: the LD OpenFeature provider
accepts `LDOptions`, so the `TestData` factory threads straight through and the code under test stays
vendor-neutral.

```typescript
import { LaunchDarklyProvider } from '@launchdarkly/openfeature-node-server';

const ldProvider = new LaunchDarklyProvider('test-sdk-key-not-real', {
  updateProcessor: ld.data.getFactory(), // TestData behind the LD provider
  sendEvents: false,
});
await OpenFeature.setProviderAndWait('checkout', ldProvider);
const flags = OpenFeature.getClient('checkout'); // prod-shaped: pure OpenFeature
```

## Path A — OpenFeature `InMemoryProvider` (the vendor-neutral spine, idea #1)

The provider is the seam. Production code asks an OpenFeature `Client` for flag values; the test swaps in an
`InMemoryProvider` holding exactly the flags the scenario pins. **Use a domain-scoped provider + client**
(`setProviderAndWait('checkout', ...)` / `getClient('checkout')`) — the `OpenFeature` singleton is global state,
and a domain keeps parallel test files from clobbering each other's provider. In Node the flag's
`contextEvaluator` returns the **variant key** for a given context.

```typescript
// tests/support/flags/flag-fixture.ts
import {
  Client,
  EvaluationContext,
  InMemoryProvider,
  OpenFeature,
  type FlagConfiguration,
} from '@openfeature/server-sdk';

/** Pins flag state for one test: a fresh InMemoryProvider per fixture, bound to a domain-scoped client. */
export class FlagFixture {
  private readonly flags: FlagConfiguration = {};

  constructor(private readonly domain: string) {}

  /** Pin a boolean flag to a fixed state — the simplest "pin, don't fetch". */
  withBooleanFlag(key: string, enabled: boolean): this {
    this.flags[key] = {
      disabled: false,
      variants: { on: true, off: false },
      defaultVariant: enabled ? 'on' : 'off',
    };
    return this;
  }

  /** Pin a multivariate flag to one named variant (test EVERY variant via the matrix, idea #2). */
  withVariant<T>(key: string, variants: Record<string, T>, selected: string): this {
    this.flags[key] = { disabled: false, variants, defaultVariant: selected };
    return this;
  }

  /** Pin a context-aware rule: the evaluator picks the VARIANT KEY from the EvaluationContext (idea #3). */
  withRule<T>(
    key: string,
    variants: Record<string, T>,
    defaultVariant: string,
    variantForContext: (ctx: EvaluationContext) => string,
  ): this {
    this.flags[key] = { disabled: false, variants, defaultVariant, contextEvaluator: variantForContext };
    return this;
  }

  /** Wire the pinned flags in and return the client the code under test should use. */
  async client(): Promise<Client> {
    await OpenFeature.setProviderAndWait(this.domain, new InMemoryProvider(this.flags)); // awaits READY — no race
    return OpenFeature.getClient(this.domain);
  }
}
```

### Both sides of the branch — the on/off matrix (idea #2)

One parameterized test per flag-touching behavior; one row per flag state. The rows pin the flag; the assertions
verify **each branch's own contract** — the off-row asserts the *legacy* behavior, not merely "no error".

```typescript
// tests/flags/checkout-flag.test.ts
import { describe, expect, it } from 'vitest';
import { FlagFixture } from '../support/flags/flag-fixture';
import { CheckoutService } from '../../src/checkout/checkout-service';

describe('checkout flow under the new-checkout flag', () => {
  // flagState | expectedFlow — BOTH sides, every run (idea #2)
  it.each([
    { enabled: true,  expectedFlow: 'express-checkout' },
    { enabled: false, expectedFlow: 'classic-checkout' },
  ])('should route to $expectedFlow when the flag is $enabled', async ({ enabled, expectedFlow }) => {
    const flags = await new FlagFixture('checkout')
      .withBooleanFlag('new-checkout', enabled) // PINNED — not fetched (idea #1)
      .client();

    const checkout = new CheckoutService(flags); // constructor injection — the client is a dependency

    const result = await checkout.startCheckout('sku-1');
    expect(result.flow).toBe(expectedFlow);
  });
});
```

> The off-row is **not** a formality: it is the only coverage of the path every un-migrated user is on, and the
> only proof a rollback is safe. A multivariate flag gets one row per variation — exhaustively (`control` /
> `treatment-a` / `treatment-b`), via the same `it.each` mechanics as `qa-data-driven-testing-typescript`.

### Targeting via the evaluation context (idea #3)

The rule lives in the fixture; the test varies the **context** and asserts three cases — matching, non-matching,
and **the fallthrough/default** (the case targeting bugs hide in).

```typescript
it('should serve the new checkout only to beta-tier users', async () => {
  const flags = await new FlagFixture('checkout')
    .withRule('new-checkout', { on: true, off: false }, 'off', (ctx) =>
      ctx.tier === 'beta' ? 'on' : 'off',
    )
    .client();

  const betaUser   = { targetingKey: 'user-1', tier: 'beta' };
  const freeUser   = { targetingKey: 'user-2', tier: 'free' };
  const anonNoTier = { targetingKey: 'user-3' };               // the forgotten third case

  await expect(flags.getBooleanValue('new-checkout', false, betaUser)).resolves.toBe(true);   // matching
  await expect(flags.getBooleanValue('new-checkout', false, freeUser)).resolves.toBe(false);  // non-matching
  await expect(flags.getBooleanValue('new-checkout', false, anonNoTier)).resolves.toBe(false); // fallthrough
});
```
