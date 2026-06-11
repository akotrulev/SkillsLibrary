---
name: qa-db-testing-testcontainers-typescript
description: Use when the user asks to scaffold TypeScript (Vitest / Jest) integration tests backed by a real database (Postgres / SQL Server / MongoDB / Redis) via the `testcontainers` npm package. Triggers: "spin up Postgres for these tests", "Testcontainers fixture in Vitest", "stop using in-memory pg-mem". Not for SQL query authoring guardrails → `db-testing/query-author`.
---

# QA — DB Testing with Testcontainers (TypeScript)

Scaffolds Vitest global-setup files that boot a real database container per test process, run migrations once, and reset row data between tests via `pg-truncate` / Prisma's `$executeRaw` / collection-drop for Mongo. Optimised for `vitest run` locally and in Azure Pipelines.

## When to use

- New `tests/integration/{feature}.int.test.ts` that hits a real DB
- Replacing `pg-mem` / in-memory mocks with a real engine
- API tests (Supertest / Nest's `INestApplication`) asserting DB side-effects
- Cross-version checks (Postgres 16 vs 17 via Vitest projects)

## When NOT to use

- Pure unit tests with no SQL surface
- .NET / JVM stacks — see siblings
- Performance/load against the DB → `qa/typescript/skills/performance/k6`
- SQL safety review of assertion queries → `qa/typescript/skills/db-testing/query-author`

## Inputs needed

Ask at most 2 questions.

1. Engine? (Postgres default; SQL Server / Mongo / Redis on request)
2. Schema source: Prisma migrations, Knex migrations, Drizzle, raw SQL files, or Flyway image init?

Infer the test framework from `package.json` (Vitest preferred per CLAUDE.md; Jest is a drop-in for the same patterns).

## Decision matrix

| Question | Default | Override when |
|---|---|---|
| Container scope | **Per test process** via `globalSetup` | Per file only when tests cannot share an instance |
| Image tag | **Pinned** (`postgres:17.2`) | Never `latest` |
| Schema lifecycle | **Migrate once** in `globalSetup` | Per-test migrate only when validating rollback |
| Row reset | **Truncate all tables** (cascade) in `beforeEach` | Transactional rollback when SUT participates in the same TX (rare with HTTP) |
| Connection string | **Injected** via env var (`DATABASE_URL`) | Never hardcoded |
| Parallelism | Vitest `fileParallelism: false` for integration project | Higher only with one container per file *and* proven isolation |

## Templates

### Vitest config — `vitest.integration.config.ts`

```ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['tests/integration/**/*.int.test.ts'],
    globalSetup: ['./tests/integration/setup/global-setup.ts'],
    setupFiles: ['./tests/integration/setup/reset-rows.ts'],
    fileParallelism: false,
    testTimeout: 30_000,
    hookTimeout: 60_000,
    reporters: ['default', ['junit', { outputFile: 'reports/junit-integration.xml' }]],
  },
});
```

### Global setup — `tests/integration/setup/global-setup.ts`

```ts
import { PostgreSqlContainer, type StartedPostgreSqlContainer } from '@testcontainers/postgresql';
import { execSync } from 'node:child_process';

let container: StartedPostgreSqlContainer;

export async function setup(): Promise<void> {
  container = await new PostgreSqlContainer('postgres:17.2')
    .withDatabase('appdb')
    .withUsername('test')
    .withPassword('test')
    .start();

  process.env.DATABASE_URL = container.getConnectionUri();

  // Migrations: prefer the prod tool. Examples below — pick one.
  execSync('npx prisma migrate deploy', { stdio: 'inherit', env: process.env });
  // execSync('npx knex migrate:latest', { stdio: 'inherit', env: process.env });
}

export async function teardown(): Promise<void> {
  await container?.stop();
}
```

### Row reset — `tests/integration/setup/reset-rows.ts`

```ts
import { afterEach } from 'vitest';
import { Pool } from 'pg';

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

afterEach(async () => {
  await pool.query(`
    DO $$
    DECLARE r record;
    BEGIN
      FOR r IN
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public' AND tablename <> '_prisma_migrations'
      LOOP
        EXECUTE format('TRUNCATE TABLE %I RESTART IDENTITY CASCADE', r.tablename);
      END LOOP;
    END $$;
  `);
});
```

For high-throughput suites, swap to [`@databases/pg-test`](https://www.atdatabases.org/docs/pg-test) or Postgres template databases (`CREATE DATABASE x TEMPLATE seeded`) — drop and recreate in <50 ms.

### Integration test — `tests/integration/transactions.int.test.ts`

```ts
import { describe, expect, it, beforeAll, afterAll } from 'vitest';
import request from 'supertest';
import { Pool } from 'pg';
import { createApp } from '../../src/app';

const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const app = createApp();

describe('POST /transactions', () => {
  afterAll(async () => {
    await pool.end();
  });

  it('persists a row', async () => {
    const res = await request(app).post('/transactions').send({ amount: 12.5, currency: 'EUR' });

    const { rows } = await pool.query<{ count: string }>('SELECT count(*) FROM transactions');

    expect(res.status).toBe(201);
    expect(rows[0].count).toBe('1');
  });
});
```

### MongoDB / Redis (no truncate; drop collections / flush DB)

```ts
import { MongoDBContainer } from '@testcontainers/mongodb';
import { MongoClient } from 'mongodb';

const mongo = await new MongoDBContainer('mongo:7.0').start();
const client = await new MongoClient(mongo.getConnectionString(), { directConnection: true }).connect();

afterEach(async () => {
  const db = client.db('appdb');
  for (const c of await db.listCollections().toArray()) {
    await db.collection(c.name).drop().catch(() => {});
  }
});
```

Redis: `await redis.flushDb()` in `afterEach`.

### Custom wait strategy (generic container only)

```ts
import { GenericContainer, Wait } from 'testcontainers';

const c = await new GenericContainer('ghcr.io/myco/legacy-app:1.4.0')
  .withExposedPorts(8080)
  .withWaitStrategy(Wait.forHttp('/health', 8080).forStatusCode(200))
  .start();
```

**Never** `setTimeout` to wait for readiness — every module ships a correct wait strategy.

## Rules

### Fixture structure
- One container per *test process* via `globalSetup`. Vitest reuses the process across files in the same project — the container starts once.
- `globalSetup` and `setupFiles` are async — use `await`; never `.then()` chains.
- Tear down in `teardown()` even on failure. Testcontainers' Ryuk reaper covers leaks but explicit teardown speeds CI shutdown.

### Image pinning
- Specific tags only (`postgres:17.2`). Document the production version in a comment.

### Schema lifecycle
- Migrate via the same tool the app uses (`prisma migrate deploy`, `knex migrate:latest`, `drizzle-kit push`).
- Never `prisma db push --accept-data-loss` in tests — that diverges from prod migration history.
- Seed shared reference data *after* migration in `globalSetup`; exclude those tables from truncate.

### Row reset
- Default: TRUNCATE all `public` tables (Postgres) in `afterEach`. Faster and FK-safe than DELETE.
- For Mongo/Redis, drop collections / flushDb.
- Transactional rollback works only when the SUT runs inside the test's TX — uncommon for HTTP integration tests.

### Connection string handling
- Read once from the container (`getConnectionUri()`), expose via `process.env.DATABASE_URL` in `globalSetup`.
- Never hardcode `localhost:5432` — Testcontainers assigns dynamic ports.
- Never log the connection string (secrets policy).

### Parallelism
- `fileParallelism: false` for the integration project. UNIT tests stay parallel in a separate project.
- If parallelising integration files: one container *per file* via `beforeAll`, not the shared `globalSetup` pattern.

### Diagnostics
- On failure, dump container logs to the test reporter: `await container.logs().then(stream => …)` in a Vitest `onTestFailed` hook. Pair with `qa/typescript/skills/allure-reporting`.

### What NOT to do
- No `setTimeout` waiting for the DB — use the built-in wait strategy.
- No `latest` image tags.
- No hardcoded ports — always read from `container.getMappedPort()`.
- No mixing of in-memory and Testcontainers drivers in the same suite.
- No `prisma db push` or `EnsureCreated`-style schema shortcuts.
- No `console.log(process.env.DATABASE_URL)` (secrets policy).
- No starting a container inside `beforeEach` — that's per-test container creation.
- No swallowing errors in `globalSetup` — let Vitest mark the suite errored.

## Generation steps

1. Read `package.json` to confirm Vitest vs Jest, Prisma / Knex / Drizzle, existing setup files.
2. Confirm production migration tool and schema location.
3. Generate:
   - `vitest.integration.config.ts`
   - `tests/integration/setup/global-setup.ts`
   - `tests/integration/setup/reset-rows.ts`
   - Concrete `tests/integration/{feature}.int.test.ts`
   - `package.json` updates: add `testcontainers`, `@testcontainers/postgresql` (or mongodb/mssql), `pg`, `supertest`, `vitest`, `@vitest/coverage-v8`.
4. Add npm script: `"test:integration": "vitest run --config vitest.integration.config.ts"`.
5. Run the script — expect green or a real assertion failure.

## Cross-references

- **`qa/typescript/skills/db-testing/query-author`** — assertion-query SQL guardrails.
- **`qa/typescript/skills/test-data-builder`** — seed builders (preferred over inline literals).
- **`qa/typescript/skills/test-environments`** — multi-container orchestration via docker-compose.
- **`qa/typescript/skills/ci-pipelines`** — DinD enablement and reporter wiring.
- **`qa/typescript/skills/allure-reporting`** — attach container logs on failure.
