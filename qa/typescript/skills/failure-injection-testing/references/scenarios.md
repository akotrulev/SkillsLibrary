# Fault scenarios — `qa-typescript:failure-injection-testing`

The retry, partial-response and probabilistic samples moved out of SKILL.md for on-demand loading. Each uses the `fixture.chaos` injector and `OrderTraffic` driver from `references/details.md`.

## Retry count — assert exactly the contracted attempts

A `reset_peer` on the connection makes attempts fail; assert the app makes **exactly** the contracted number of
tries (via a cockatiel `onRetry` counter, or by counting calls that reach the upstream), then succeeds/falls back —
not infinite, not one.

```ts
it('retries exactly three times then falls back on connection resets', async () => {
  const { chaos } = fixture;
  const app = OrderService.connectedTo(chaos.host(), chaos.port());
  await chaos.cutConnection();                          // every attempt's connection is reset

  const result = await app.placeOrderWithRetry('sku-1');

  expect(result.isFallback).toBe(true);
  // The PATTERN: bounded retries, not a runaway loop — assert the configured attempt count.
  expect(app.lastAttemptCount, 'maxAttempts honored').toBe(3);

  await chaos.healed();
});
```

## Partial / garbled response — `slicer` / `limit_data` (don't persist corruption)

A response cut mid-stream must surface as an error the app handles — it must **not** be parsed and persisted as a
valid (truncated) record. Inject `limit_data` (cut after N bytes) or `slicer` (fragment the stream), drive a read,
and assert the app rejects the partial result and leaves state uncorrupted.

```ts
it('rejects and does not persist a truncated response', async () => {
  const { chaos } = fixture;
  await chaos.truncateAfter(64);                        // cut every response after 64 bytes
  const app = CatalogService.connectedTo(chaos.host(), chaos.port());

  const result = await app.loadCatalog();

  expect(result.isError, 'partial response surfaces as an error').toBe(true);
  expect(app.lastPersistedCatalog, 'no truncated record persisted').toBeNull();

  await chaos.healed();
});
```

## Probabilistic faults — `toxicity` for flappy dependencies

A `toxicity` below 1.0 applies the toxic to only a *fraction* of connections — an intermittent, flappy dependency.
Assert the app's retries smooth over the failing fraction so the user-visible outcome stays correct.

```ts
it('tolerates an intermittently resetting dependency', async () => {
  const { chaos } = fixture;
  await chaos.cutConnection(0, 0.3);                    // reset the connection only 30% of the time
  const app = OrderService.connectedTo(chaos.host(), chaos.port());

  const results = await new OrderTraffic(app).placeWithRetry('sku-1', 20);

  expect(results.filter((r) => !r.isSuccess), 'retries absorb an intermittent fault').toEqual([]);

  await chaos.healed();
});
```

> Probabilistic faults are still **deterministic in intent** (a fixed toxicity), unlike real production chaos —
> that determinism is what makes them a *test*. For true randomized cluster chaos, see the boundary note below.
