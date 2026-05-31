---
name: qa-test-environments-typescript
description: Use when the user asks to spin up a whole multi-service environment (not just one database) for Node 20 + TypeScript integration/E2E tests via Testcontainers — `DockerComposeEnvironment` driving a committed `docker-compose.test.yml` (app + DB + queue/cache/mailcatcher), or a hand-built `GenericContainer` topology sharing a user-defined `Network` with `withNetworkAliases` for inter-container DNS, explicit per-service wait strategies (`Wait.forHttp` / `forListeningPorts` / `forLogMessage` / `forHealthCheck` — never a sleep), `withReuse()` for fast local loops vs fresh-per-suite in CI, the Ryuk reaper, and surfacing host+mapped-port connection details to tests through a fixture. Triggers: "spin up the whole stack (api + postgres + redis) for these tests", "Testcontainers docker-compose environment in Vitest", "boot app + DB + Kafka together and wait for all of them", "give my service a network alias so the container can reach the DB", "reuse the containers between local test runs". Do NOT use for a single database container with migrations + row reset (use `qa/db-testing/testcontainers/typescript`), for .NET (`qa/test-environments/dotnet`), for JVM (`qa/test-environments/java`), for the CI runner that hosts these tests (`qa/ci-pipelines/github-actions/typescript`), or for in-browser network mocking (`qa/network-monitoring/playwright-routes/typescript`).
---

# QA — Test Environments with Testcontainers + docker-compose (TypeScript)

Boots a **whole dependency topology** — application-under-test plus its real backing services (DB, cache, queue, object store, mail catcher, third-party stub) — for Node 20 + TypeScript integration/E2E tests, using the `testcontainers` npm package. This is the **general environment spin-up** skill: multi-container `docker-compose` orchestration and hand-built multi-container networks. For a *single* database container with migrations and per-test row reset, that is the narrower `qa/db-testing/testcontainers/typescript` skill — this one owns everything from two containers up.

Every service is waited on by an **explicit readiness condition**, never a fixed sleep. Connection details (host + dynamically-mapped port) are read off the started environment and surfaced to tests through a **fixture** — specs never hardcode `localhost:5432`.

## Stack

- Node 20 + TypeScript (strict mode)
- `testcontainers` (≥ 10.x — `DockerComposeEnvironment`, `Network`, `Wait`, `withReuse`)
- Vitest (`globalSetup` boots the environment once per test process); Jest is a drop-in for the same pattern
- Environment fixtures under `tests/fixtures/environment/`, compose files under `tests/fixtures/compose/`
- These suites run on `ubuntu-latest` (Docker pre-installed) under `qa/ci-pipelines/github-actions/typescript`

## When to use

- You need **more than one** container per suite: app + DB + Redis, or DB + Kafka + a third-party stub
- A committed `docker-compose.yml` already describes the dev topology and you want tests to reuse it verbatim
- The app-under-test must run *as a container* and reach its dependencies by hostname (inter-container DNS)
- You want fast local re-runs by **reusing** already-running containers, but a clean fresh environment in CI
- You're booting a mail catcher / object store / message broker that has no dedicated db-testing skill

## When NOT to use

- A single DB with migrations + per-test reset (Respawn-style) → `qa/db-testing/testcontainers/typescript`
- .NET / JVM stacks → `qa/test-environments/{dotnet,java}`
- The CI workflow that runs these (Docker enablement, artifact upload) → `qa/ci-pipelines/github-actions/typescript`
- In-browser HTTP mocking/interception (no real services) → `qa/network-monitoring/playwright-routes/typescript`
- Pure unit tests with no out-of-process dependency

## Inputs needed

Ask at most 3 questions; infer the rest from the repo.

1. **Topology** — which services make up the environment (app, DB engine, cache, queue, mail, stubs)?
2. **Source of truth** — is there an existing `docker-compose.yml` to drive, or should the topology be built in code with `GenericContainer` + a shared `Network`?
3. **Scope** — one environment per *test process* (default, via `globalSetup`) or per file?

Infer the test framework from `package.json` (Vitest preferred per CLAUDE.md), and the app image / Dockerfile location from the repo root.

## Decision matrix

| Decision | Default | Override when |
|---|---|---|
| Orchestration | **`DockerComposeEnvironment`** driving a committed `docker-compose.test.yml` | Hand-built `GenericContainer` + `Network` when there's no compose file or you need per-container code control |
| Environment scope | **Per test process** via Vitest `globalSetup` | Per file (`beforeAll`) only when files genuinely cannot share an environment |
| Inter-container DNS | Compose service names (built-in network) / `withNetworkAliases('db')` on a shared `Network` | — (never hardcode container IPs) |
| Wait strategy | **Per service**: `Wait.forHttp('/health')` for the app, `Wait.forListeningPorts()`/`forLogMessage` for deps | `Wait.forHealthCheck()` when the compose service defines a `healthcheck` |
| Reuse | **`.withReuse()` locally** (+ `testcontainers.reuse.enable=true`); **fresh per suite in CI** | Never reuse in CI — a leaked dirty container makes runs non-deterministic |
| Image tags | **Pinned** (`postgres:17.2`, `redis:7.4`) | Never `latest` |
| Connection details | **Read from the started env** (`getMappedPort`/`getHost`) and surfaced via the fixture | Never hardcode `localhost:5432` — ports are dynamic |
| Teardown | `environment.down()` in `globalSetup`'s `teardown` (Ryuk as backstop) | Skip `down()` only for a reused local environment (leave it running) |

## Patterns

### Multi-service environment from a committed compose file — `tests/fixtures/compose/docker-compose.test.yml`

Drive the same compose topology dev uses. Define a `healthcheck` per service so Testcontainers can wait on it directly.

```yaml
services:
  postgres:
    image: postgres:17.2
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test -d appdb"]
      interval: 1s
      timeout: 5s
      retries: 30

  redis:
    image: redis:7.4
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 1s
      retries: 30

  api:
    build: ../../..            # the app-under-test image
    environment:
      DATABASE_URL: postgres://test:test@postgres:5432/appdb   # service-name DNS, not localhost
      REDIS_URL: redis://redis:6379
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    ports:
      - "8080"                 # host port assigned dynamically; read it back, never assume 8080
```

### Environment fixture — `tests/fixtures/environment/stack.ts`

Wrap the environment in a small object that exposes **intent** (`apiBaseUrl`, `databaseUrl`), not raw container handles. Specs ask the fixture for a URL; they never call `getMappedPort` themselves.

```ts
import {
  DockerComposeEnvironment,
  Wait,
  type StartedDockerComposeEnvironment,
} from 'testcontainers';
import { resolve } from 'node:path';

const COMPOSE_DIR = resolve(__dirname, '../compose');
const COMPOSE_FILE = 'docker-compose.test.yml';

export interface Stack {
  readonly apiBaseUrl: string;
  readonly databaseUrl: string;
  readonly redisUrl: string;
}

let environment: StartedDockerComposeEnvironment | undefined;

export async function startStack(): Promise<Stack> {
  // CI never reuses — a leaked dirty container would make the run non-deterministic.
  const reuse = process.env.CI !== 'true';

  let builder = new DockerComposeEnvironment(COMPOSE_DIR, COMPOSE_FILE)
    // Explicit readiness per service — never a fixed sleep.
    .withWaitStrategy('postgres', Wait.forHealthCheck())
    .withWaitStrategy('redis', Wait.forHealthCheck())
    .withWaitStrategy('api', Wait.forHttp('/health', 8080).forStatusCode(200));

  if (reuse) builder = builder.withProjectName('qa-stack-local'); // stable name → reusable locally

  environment = await builder.up();

  const api = environment.getContainer('api-1');     // compose appends "-1" to the service name
  const pg = environment.getContainer('postgres-1');
  const redis = environment.getContainer('redis-1');

  return {
    apiBaseUrl: `http://${api.getHost()}:${api.getMappedPort(8080)}`,
    databaseUrl: `postgres://test:test@${pg.getHost()}:${pg.getMappedPort(5432)}/appdb`,
    redisUrl: `redis://${redis.getHost()}:${redis.getMappedPort(6379)}`,
  };
}

export async function stopStack(): Promise<void> {
  // In CI, tear the environment down. Locally with reuse on, leave it running for the next run.
  if (process.env.CI === 'true') await environment?.down();
}
```

> **Compose reuse caveat:** the Node binding does **not** support reusing *compose* environments across processes the way `GenericContainer.withReuse()` does ([testcontainers-node#288](https://github.com/testcontainers/testcontainers-node/issues/288)). A stable `withProjectName` lets `docker compose` itself short-circuit already-running services on a local re-run; for true cross-run reuse use the `GenericContainer` topology below.

### Vitest wiring — `vitest.integration.config.ts` + `globalSetup`

Boot the environment **once per test process** and publish its URLs as env vars the tests read.

```ts
// vitest.integration.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['tests/integration/**/*.int.test.ts'],
    globalSetup: ['./tests/integration/setup/global-setup.ts'],
    fileParallelism: false,   // one shared environment; parallel files would race it
    testTimeout: 30_000,
    hookTimeout: 120_000,     // image pull + multi-service boot on a cold runner
    reporters: ['default', ['junit', { outputFile: 'reports/junit-integration.xml' }]],
  },
});
```

```ts
// tests/integration/setup/global-setup.ts
import { startStack, stopStack } from '../../fixtures/environment/stack';

export async function setup(): Promise<void> {
  const stack = await startStack();
  process.env.API_BASE_URL = stack.apiBaseUrl;
  process.env.DATABASE_URL = stack.databaseUrl;
  process.env.REDIS_URL = stack.redisUrl;
}

export async function teardown(): Promise<void> {
  await stopStack();
}
```

```ts
// tests/integration/checkout.int.test.ts
import { describe, expect, it } from 'vitest';

describe('POST /checkout against the full stack', () => {
  it('Should_persist_order_and_publish_event_When_checkout_succeeds', async () => {
    const res = await fetch(`${process.env.API_BASE_URL}/checkout`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ sku: 'ABC', qty: 2 }),
    });

    expect(res.status).toBe(201);
  });
});
```

### Hand-built topology with a shared network — `tests/fixtures/environment/network-stack.ts`

No compose file? Build the topology in code. A user-defined `Network` + `withNetworkAliases` gives containers **DNS names** to reach each other; the app container talks to `db:5432`, the host talks to the app's mapped port.

```ts
import { GenericContainer, Network, Wait, type StartedNetwork, type StartedTestContainer } from 'testcontainers';

export interface NetworkStack {
  readonly apiBaseUrl: string;
  stop(): Promise<void>;
}

export async function startNetworkStack(): Promise<NetworkStack> {
  const network: StartedNetwork = await new Network().start();

  const db: StartedTestContainer = await new GenericContainer('postgres:17.2')
    .withNetwork(network)
    .withNetworkAliases('db')                 // the app reaches it as host "db"
    .withEnvironment({ POSTGRES_DB: 'appdb', POSTGRES_USER: 'test', POSTGRES_PASSWORD: 'test' })
    .withExposedPorts(5432)
    .withWaitStrategy(Wait.forListeningPorts())
    .start();

  const api: StartedTestContainer = await new GenericContainer('myorg/api:test')
    .withNetwork(network)
    .withEnvironment({ DATABASE_URL: 'postgres://test:test@db:5432/appdb' }) // alias, not host:port
    .withExposedPorts(8080)
    .withWaitStrategy(Wait.forHttp('/health', 8080).forStatusCode(200))
    .start();

  return {
    apiBaseUrl: `http://${api.getHost()}:${api.getMappedPort(8080)}`,
    async stop() {
      await api.stop();
      await db.stop();
      await network.stop();   // Ryuk also reaps these if the process dies first
    },
  };
}
```

### Container reuse for fast local loops

`withReuse()` keeps a `GenericContainer` running between test runs; the next run with an identical config hash attaches to it instead of booting a fresh one. Gate it off in CI.

```ts
const db = await new GenericContainer('postgres:17.2')
  .withEnvironment({ POSTGRES_DB: 'appdb', POSTGRES_USER: 'test', POSTGRES_PASSWORD: 'test' })
  .withExposedPorts(5432)
  .withWaitStrategy(Wait.forListeningPorts())
  .withReuse()                          // no-op unless reuse is enabled (see below)
  .start();
```

Reuse only activates when `testcontainers.reuse.enable=true` is set in `~/.testcontainers.properties` (or `TESTCONTAINERS_REUSE_ENABLE=true`). With reuse on, **do not** call `.stop()`/`down()` — leave the container running for the next run. CI sets neither, so the same code boots fresh and Ryuk reaps it.

### Custom wait strategy for a bespoke service

Built-in modules ship correct waits; for a generic image, wait on a **real readiness signal**.

```ts
const broker = await new GenericContainer('confluentinc/cp-kafka:7.6.1')
  .withExposedPorts(9092)
  .withWaitStrategy(Wait.forLogMessage(/started \(kafka.server.KafkaServer\)/))
  .start();
```

`Wait.forLogMessage` (regex on stdout), `Wait.forListeningPorts()`, `Wait.forHttp(path, port).forStatusCode(n)`, `Wait.forHealthCheck()` (Docker `HEALTHCHECK`). **Never** `await new Promise(r => setTimeout(r, ms))` to wait for readiness.

## Rules

### Topology & orchestration
- Prefer driving a **committed `docker-compose.test.yml`** so tests and dev share one topology definition. Build it in code (`GenericContainer` + `Network`) only when there's no compose file or you need per-container control (reuse, custom waits, per-container code).
- Boot the environment **once per test process** via Vitest `globalSetup` (or per file in `beforeAll` if files can't share). Never start the whole stack in `beforeEach`.
- Containers talk to each other by **service name** (compose) or **network alias** (`withNetworkAliases`) — never by hardcoded container IP.

### Wait strategies (no sleeps)
- Every service gets an **explicit readiness condition**. App → `Wait.forHttp('/health')`; DB/broker → `forListeningPorts`/`forLogMessage`/`forHealthCheck`.
- Define a `healthcheck` in compose and wait with `Wait.forHealthCheck()` so the readiness contract lives next to the service.
- **No `setTimeout`/`await delay(ms)`** as a readiness wait, anywhere.

### Connection details
- Read host + port off the **started** environment (`container.getHost()`, `container.getMappedPort(internalPort)`); ports are assigned dynamically by Docker.
- Surface them through the fixture as intent-named URLs (`apiBaseUrl`, `databaseUrl`); specs read env vars / the fixture, never `getMappedPort` directly.
- **Never** hardcode `localhost:5432` or the compose-internal port — that's the container-to-container port, not the host-mapped one.
- Never log a connection string that carries credentials (secrets policy).

### Reuse vs fresh
- `withReuse()` + `testcontainers.reuse.enable=true` for **fast local loops**; with reuse on, do not tear down.
- **CI always boots fresh and tears down** — gate reuse on `process.env.CI !== 'true'`. A reused dirty container makes CI non-deterministic.
- Compose-environment reuse is not supported in the Node binding — use a stable `withProjectName` for local re-runs, or the `GenericContainer` topology for true reuse.

### Teardown & the reaper
- Call `environment.down()` / `container.stop()` + `network.stop()` in `teardown` (CI). The **Ryuk** reaper is the backstop that kills leaked containers if the process dies — never the primary cleanup.
- Don't disable Ryuk (`TESTCONTAINERS_RYUK_DISABLED=true`) except on a runner that forbids the sidecar — then you own teardown entirely.

### Images & scope
- Pin every image (`postgres:17.2`, not `latest`/`17`). Document the prod version in a comment.
- `fileParallelism: false` for a single shared environment; one environment *per file* only with proven isolation.

### Diagnostics
- On failure, attach service logs to the reporter: `await container.logs()` → stream to an Allure attachment. Pair with `qa/allure-reporting/typescript`.

### What NOT to do
- No `setTimeout`/`delay(ms)` to wait for a service — use a `Wait.*` strategy.
- No `latest`/floating image tags.
- No hardcoded `localhost:<fixed-port>` — read `getMappedPort()` from the started container.
- No container-to-container traffic via IP — use compose service names / `withNetworkAliases`.
- No `withReuse()` left active in CI (gate on `process.env.CI`), and no `down()` when reuse is on locally.
- No starting the full stack in `beforeEach` — that's a fresh environment per test.
- No migrations / per-test row reset logic in here — that's `qa/db-testing/testcontainers/typescript`'s job; this skill stops at booting the topology.
- No logging a credentialed connection string (secrets policy).
- No swallowing a `globalSetup` boot error — let Vitest mark the suite errored so CI fails loudly.

## Generation steps

1. Read `package.json` (Vitest vs Jest), any existing `docker-compose.yml`, and the app `Dockerfile` to learn the topology and image source.
2. Confirm the **topology**, the **source of truth** (compose file vs code), and the **scope** (per-process vs per-file).
3. Generate:
   - `tests/fixtures/compose/docker-compose.test.yml` (if driving compose) with a `healthcheck` per service.
   - `tests/fixtures/environment/stack.ts` (or `network-stack.ts`) exposing intent-named URLs, with explicit per-service waits and CI-gated reuse.
   - `vitest.integration.config.ts` + `tests/integration/setup/global-setup.ts` publishing the URLs as env vars.
   - A concrete `tests/integration/{feature}.int.test.ts` hitting the booted stack.
   - `package.json`: add `testcontainers`; script `"test:integration": "vitest run --config vitest.integration.config.ts"`.
4. Run `pnpm test:integration` — expect a green run or a real assertion failure, not a boot/wait crash. Run `tsc --noEmit` for strict-TS green.
5. Confirm reuse works locally (set `testcontainers.reuse.enable=true`, run twice — the second is fast) and that CI (`CI=true`) boots fresh and tears down.

## Cross-references

- **`qa/test-environments/dotnet`** + **`qa/test-environments/java`** — the sibling stacks porting this canonical TS skill into `Testcontainers`/NUnit and `org.testcontainers`/TestNG idioms.
- **`qa/db-testing/testcontainers/typescript`** — the narrower skill for a *single* DB container with migrations + per-test reset; this environment skill is what you graduate to when the suite needs the app + DB + other services together. It cross-links back here for multi-container orchestration.
- **`qa/db-testing/client/typescript`** — the DB client/query wiring that runs against the `databaseUrl` this fixture surfaces.
- **`qa/ci-pipelines/github-actions/typescript`** — runs these suites on `ubuntu-latest` (Docker pre-installed, Ryuk works out of the box); uploads JUnit + logs.
- **`qa/test-data-builder/typescript`** — seeds data into the booted services.
- **`qa/allure-reporting/typescript`** — attach per-service container logs on failure.

## Sources synthesized (research-first per CLAUDE.md)

- [Testcontainers for Node.js — Docker Compose](https://node.testcontainers.org/features/compose/) — `DockerComposeEnvironment`, `.withWaitStrategy(service, …)`, `.up()`, `getContainer('service-1')`, `getMappedPort`/`getHost`.
- [Testcontainers for Node.js — Containers & Networks](https://node.testcontainers.org/features/containers/) — `GenericContainer`, `Network`, `withNetworkAliases`, `Wait.forHttp`/`forListeningPorts`/`forLogMessage`/`forHealthCheck`, `withReuse()`.
- [Container Reuse — testcontainers-node (DeepWiki)](https://deepwiki.com/testcontainers/testcontainers-node/4.1-container-reuse) and [testcontainers-node#288](https://github.com/testcontainers/testcontainers-node/issues/288) — `testcontainers.reuse.enable`, config-hash matching, and the compose-reuse limitation.
- [Wim Deblauwe — Testcontainers with multiple containers](https://www.wimdeblauwe.com/blog/2025/05/14/combine-testcontainers-and-spring-boot-with-multiple-containers/) — multi-service topology, healthchecks, and inter-container DNS via network aliases.

## Changelog

- 2026-05-31: Authored as the **canonical** stack of the new `qa/test-environments/` node (QA Skills Library Phase 1, `qa/GAP-ANALYSIS.md` row 14). Establishes the structure the `dotnet`/`java` siblings mirror: a committed `docker-compose.test.yml` driven by `DockerComposeEnvironment` with per-service `Wait.*` strategies; an intent-revealing `Stack` fixture surfacing host+mapped-port URLs; Vitest `globalSetup` boot-once; a hand-built `GenericContainer` + `Network` topology with `withNetworkAliases` for inter-container DNS; CI-gated `withReuse()`; Ryuk-as-backstop teardown. Scoped explicitly *above* `qa/db-testing/testcontainers/typescript` (single DB + migrations) — this node owns multi-container environments. Notes the Node compose-reuse limitation (testcontainers-node#288).
