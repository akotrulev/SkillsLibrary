---
name: qa-contract-testing-pact-typescript
description: Use when the user asks to set up consumer-driven contract testing with Pact in a Node 20 + TypeScript service (`@pact-foundation/pact` PactV3+) — consumer tests with Vitest, provider verification, Pact Broker publish, can-i-deploy, state handlers. Triggers: "set up Pact for our Node service", "PactV3 consumer test in TS for X", "verify our TS provider against Y's contract", "wire can-i-deploy in our Node deploy". Do NOT use for .NET consumers or providers (use `qa/dotnet/skills/contract-testing-pact`), Java consumers or providers (use `qa/java/skills/contract-testing-pact`), live-service API tests (use `qa/typescript/skills/api-test-author/generator`), or OpenAPI-only validation. Load `qa/_shared/contract-testing-pact` alongside this skill for the Broker / matchers / can-i-deploy concepts.
---

# QA — Contract Testing with Pact (TypeScript / `@pact-foundation/pact`)

Wires Pact V3+ into a Node 20 + TypeScript service via `@pact-foundation/pact` for consumer-driven contract testing with Vitest. Covers the consumer test, provider verification, state handlers, and CI publish. Load `qa/_shared/contract-testing-pact` for the Broker model, matchers reference, and `can-i-deploy` gate that are shared across all stacks.

## When to use

- A Node 20 / TypeScript service consumes or produces an HTTP API and needs contract coverage.
- Replacing brittle multi-service E2E tests with Pact-JS verification.
- Catching breaking changes at the Node producer side before they ship.
- Pairing with `qa/_shared/contract-testing-pact` for Broker / `can-i-deploy` wiring.

## When NOT to use

- .NET consumer or provider → `qa/dotnet/skills/contract-testing-pact`
- Java consumer or provider → `qa/java/skills/contract-testing-pact`
- Live-service API tests (no contract) → `qa/typescript/skills/api-test-author/generator`
- OpenAPI-only validation with no consumer-driven aspect → schema validation libraries

## Stack

- **Runtime**: Node 20
- **Language**: TypeScript (strict)
- **Test runner**: Vitest (Jest works the same way — adjust imports)
- **Pact lib**: `@pact-foundation/pact` (v12+ for PactV3/V4; v15+ for V4 pact format)
- **Broker CLI**: `pactfoundation/pact-cli:latest` (containerized — language-independent)

Project layout (monorepo example):

```
packages/
├── cart-service/                      ← consumer
│   ├── package.json
│   └── src/
│       └── clients/
│           └── orders.ts
└── orders-service/                    ← provider
    ├── package.json
    └── src/
tests/
├── cart-service.contract/
│   ├── package.json                   ← devDeps: @pact-foundation/pact, vitest
│   ├── vitest.config.ts
│   ├── pacts/                         ← generated, gitignored
│   └── src/
│       └── orders.consumer.spec.ts
└── orders-service.contract/
    ├── package.json
    ├── vitest.config.ts
    └── src/
        └── orders.provider.spec.ts
```

`pacts/` is generated output — `.gitignore` it. The Broker is the source of truth.

### Dependencies (consumer-contract module)

```jsonc
// tests/cart-service.contract/package.json
{
  "type": "module",
  "scripts": {
    "test": "vitest run"
  },
  "devDependencies": {
    "@pact-foundation/pact": "^12.5.0",
    "vitest": "^1.6.0",
    "typescript": "^5.4.0"
  }
}
```

## Consumer test (Vitest, PactV3)

```typescript
// tests/cart-service.contract/src/orders.consumer.spec.ts
import path from 'node:path';
import { describe, it, expect } from 'vitest';
import { PactV3, MatchersV3 } from '@pact-foundation/pact';
import { fetchOrder } from '../../../packages/cart-service/src/clients/orders.js';

const { string, regex, integer } = MatchersV3;

const provider = new PactV3({
  consumer: 'cart-service',
  provider: 'orders-service',
  dir: path.resolve(process.cwd(), 'pacts'),
  logLevel: 'info',
});

describe('orders consumer', () => {
  it('GET /orders/{id} returns the order', async () => {
    provider
      .given('order 123 exists for customer cus_alice')
      .uponReceiving('a request for order 123')
      .withRequest({
        method: 'GET',
        path: '/orders/123',
        headers: { Accept: 'application/json' },
      })
      .willRespondWith({
        status: 200,
        headers: { 'Content-Type': regex(/application\/json/, 'application/json') },
        body: {
          id: string('123'),
          customerId: string('cus_alice'),
          status: regex(/^(pending|paid|cancelled|refunded)$/, 'paid'),
          totalMinor: integer(9999),
          currency: regex(/^[A-Z]{3}$/, 'EUR'),
        },
      });

    await provider.executeTest(async (mock) => {
      const order = await fetchOrder('123', mock.url);
      expect(order.id).toBe('123');
      expect(order.status).toBe('paid');
    });
  });
});
```

- Assert **types** via `MatchersV3.string` / `integer` / `regex`. Reserve exact values for true enum constraints.
- `given(...)` names a provider state — the provider implements a matching handler in its state handlers map.
- `provider.executeTest(async (mock) => ...)` boots the in-process mock, hands its URL to the callback, and writes the pact file on success.

## Provider verification (Vitest)

```typescript
// tests/orders-service.contract/src/orders.provider.spec.ts
import { describe, it, beforeAll, afterAll } from 'vitest';
import { Verifier } from '@pact-foundation/pact';
import { createServer } from '../../../packages/orders-service/src/server.js';
import { ordersRepo } from '../../../packages/orders-service/src/orders.repo.js';

const PORT = 5050;
let stop: () => Promise<void>;

beforeAll(async () => {
  const server = await createServer();
  await new Promise<void>((resolve) => server.listen(PORT, resolve));
  stop = () => new Promise<void>((resolve) => server.close(() => resolve()));
});

afterAll(async () => {
  await stop();
});

describe('orders provider verification', () => {
  it('honors all consumer contracts in the broker', async () => {
    await new Verifier({
      provider: 'orders-service',
      providerBaseUrl: `http://localhost:${PORT}`,
      pactBrokerUrl: process.env.PACT_BROKER_BASE_URL,
      pactBrokerToken: process.env.PACT_BROKER_TOKEN,
      consumerVersionSelectors: [
        { mainBranch: true },
        { deployedOrReleased: true },
      ],
      publishVerificationResult: true,
      providerVersion: process.env.GIT_SHA,
      providerVersionBranch: process.env.BRANCH_NAME,
      stateHandlers: {
        'order 123 exists for customer cus_alice': async () => {
          await ordersRepo.upsert({
            id: '123',
            customerId: 'cus_alice',
            status: 'paid',
            totalMinor: 9999,
            currency: 'EUR',
          });
        },
      },
    }).verifyProvider();
  }, /* timeout */ 120_000);
});
```

State handlers are plain async functions keyed by state name. They run before the matching interaction; teardown is rarely needed (most handlers idempotent-upsert into a per-test database).

## CI — consumer side

```bash
pnpm --filter ./tests/cart-service.contract test   # runs Vitest, writes pact

docker run --rm \
  -v "$PWD/tests/cart-service.contract/pacts:/pacts" \
  -e PACT_BROKER_BASE_URL=$PACT_BROKER_BASE_URL \
  -e PACT_BROKER_TOKEN=$PACT_BROKER_TOKEN \
  pactfoundation/pact-cli:latest \
  broker publish /pacts \
  --consumer-app-version "$GIT_SHA" \
  --branch "$BRANCH_NAME"
```

## CI — provider side

```bash
PACT_BROKER_BASE_URL=$BROKER \
PACT_BROKER_TOKEN=$TOKEN \
GIT_SHA=$GIT_SHA \
BRANCH_NAME=$BRANCH_NAME \
  pnpm --filter ./tests/orders-service.contract test
```

The verifier publishes results back via `publishVerificationResult: true`.

## `can-i-deploy` gate (both pipelines)

See `qa/_shared/contract-testing-pact` for the shared `can-i-deploy` and `record-deployment` commands. Wire them in the deploy stage of **both** the consumer and the provider pipelines, before `kubectl apply` / Cloud Run / Lambda update.

## Rules (TypeScript-specific)

- **Strict TypeScript.** `tsconfig.json` has `"strict": true`. No `any` in matcher signatures or DTO types.
- **ESM-first.** Use `"type": "module"` in contract-test packages; import with explicit `.js` extensions on relative paths.
- **PactV3** (or V4 with `@pact-foundation/pact` v15+) — do not author V1/V2 unless interoperating with an older Broker.
- **The consumer's HTTP client accepts a `baseUrl` argument.** Tests pass `mock.url` — never hardcode `http://localhost`.
- **State handlers as plain async functions** keyed by state name; they seed a real (containerized) database, not in-memory globals.
- **Vitest `beforeAll`/`afterAll`** to boot/teardown the provider HTTP server on a fixed port (`5050` in examples).
- **`pacts/` gitignored** per contract-test package; never committed.
- **Floating promises forbidden** — every `executeTest` and `verifyProvider` must be `await`ed; enable ESLint `no-floating-promises`.
- **No `Date.now()` / `Math.random()` in matchers** — use `regex` / `string` / `integer` with stable example values.

## What NOT to do

- No verifying against the consumer's `localhost` test instance — boot the real provider HTTP server (e.g. `createServer().listen(5050)`) and verify against it.
- No leaking provider-state endpoints into production builds — keep state handlers inside the Verifier config, not as routes on the real service.
- No exact-value matchers everywhere — over-asserting breaks on harmless field additions.
- No pact files committed and treated as the source of truth.
- No mixing `supertest` with `@pact-foundation/pact` Verifier — Verifier needs a real HTTP target.
- No `setTimeout` / arbitrary delays between consumer call and assertion — the mock is already running.
- No publishing without `--branch` and `--consumer-app-version` — Broker becomes incapable of correctly answering `can-i-deploy`.
- No `consumerVersionSelectors: [{ mainBranch: true }]` alone — always include `{ deployedOrReleased: true }`.
- No `nock` / `msw` for the same call you're contract-testing — Pact owns the mock during the consumer test.

## Generation steps

1. Add a new package under `tests/{service}.contract/` with `@pact-foundation/pact` and `vitest` as devDependencies; set `"type": "module"`.
2. For the consumer: scaffold `{provider}.consumer.spec.ts` building a `PactV3`; add one interaction with `given(...)` + `uponReceiving(...)`; run `pnpm test`; confirm a pact file appears under `pacts/`.
3. For the provider: scaffold `{service}.provider.spec.ts` that boots the real server on `5050`, calls `new Verifier({ ... }).verifyProvider()`, with `stateHandlers` for each state name.
4. Wire consumer CI: Vitest → `pact-cli broker publish` with `--branch` and `--consumer-app-version`.
5. Wire provider CI: Vitest with `PACT_BROKER_*` and `GIT_SHA` / `BRANCH_NAME` env vars exported.
6. Add `can-i-deploy` and `record-deployment` to both deploy pipelines (see `_shared`).
7. Smoke a full cycle: change the contract on the consumer → fail provider verification → fix → success.

## Handoffs

- Cross-stack Broker / `can-i-deploy` / matchers concepts → `qa/_shared/contract-testing-pact`
- .NET consumer/provider → `qa/dotnet/skills/contract-testing-pact`
- Java consumer/provider → `qa/java/skills/contract-testing-pact`
- Live-service API tests → `qa/typescript/skills/api-test-author/generator`
- DTOs / Zod schemas → `qa/typescript/skills/api-dto-writer`
- CI pipeline syntax → `qa/typescript/skills/ci-pipelines/{github-actions,azure-pipelines,gitlab-ci}` or `devops/<ci>`
- Allure publishing for contract test results → `qa/typescript/skills/allure-reporting`
