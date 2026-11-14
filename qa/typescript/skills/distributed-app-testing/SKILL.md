---
name: distributed-app-testing
description: Use when a TypeScript suite must boot the whole multi-service system from its compose file (Testcontainers) for a test run. Triggers "test the whole stack". Not for one API alone (db-testcontainers).
---

# QA — Distributed App Testing (Testcontainers `DockerComposeEnvironment` + Vitest / Playwright)

Scaffolds a global setup that starts the system's **compose file** — every service built from the current source,
plus its database, broker and mail sink — with Testcontainers' `DockerComposeEnvironment`, waits until each service
the journey touches answers its health endpoint, resolves the mapped URLs, and hands them to the tests. The test
sees the system as it runs: real processes, real containers, real network between them.

**The fence.** This is a **process-boundary test**: each service runs in its own container, so a test cannot swap a
module, stub a dependency in-process, or call a function directly. It belongs to the `qa-api-typescript` lane, never
to a `be-*` unit-test task. A function's logic is unit-tested by the `be-node` `unit-testing` skill; one API with its
database is a `db-testing/testcontainers` setup (`db-testcontainers`), which is lighter and lets the test own the
app's wiring. Reach for this skill when the behaviour under test spans the services the compose file wires together.

## When to use

- The repo has a compose file (`compose.yaml`, `docker-compose.yml`) and the test must exercise two or more of its
  services together: an API and its worker, an API and the email it sends, a web app and its backend.
- The wiring itself is under test: service-to-service URLs, environment, health checks, start order.
- Replacing a hand-run `docker compose up` + shell script harness with one that starts and stops with the suite.

## When NOT to use

- One API plus its database → `db-testing/testcontainers`
- A unit of logic → `be-node` `unit-testing`
- Broker, blob or email assertions against one service → `messaging-testing`, `file-storage-testing`,
  `email-testing`
- Load → `load-testing`; micro-benchmarks → `benchmarks`
- A system with no compose file — write one as product infrastructure first (`devops`); never invent one inside the
  test folder only to test with it

## Inputs needed

1. The compose file(s) and the services the journey touches (names exactly as the file declares them), with the
   container port and health path of each.
2. What the compose file reads to vary its shape (`${VAR}` interpolation, `profiles:`), so the test can turn off
   persistent volumes and external dependencies.

## Version lane

| Package | Version | Rule |
|---|---|---|
| `testcontainers` | **12.2.1** (Node ≥ 22.22, verified on npm 2026-11) | A Node 22 project below 22.22 pins **11.14.0**; never up-level Node to reach 12 |
| `vitest` | The project's major (5.1 current) | `globalSetup` + `project.provide` / `inject` exist from Vitest 3 on |
| `@playwright/test` | **1.64** | `globalSetup` returning a teardown function |

`DockerComposeEnvironment` shells out to the **Docker Compose v2 CLI** (`docker compose`), so the machine and the CI
agent need Docker and the Compose plugin. Testcontainers registers the compose project with its reaper (Ryuk), so a
crashed run still has its containers removed.

## Procedure

1. Detect the Node major, the runner (Vitest / Playwright / both), the compose files, and each service's container
   port and health endpoint; match them.
2. Make the test-facing compose file publish **container ports only** (`ports: ["8080"]`), never fixed host ports
   (`"8080:8080"`): Docker picks a free host port and the setup reads it back. Where the dev file fixes host ports,
   add `compose.test.yaml` that replaces them (`ports: !override ["8080"]`, Docker Compose 2.24+).
3. Write **one global setup per test project**: start the environment once, wait for health, provide the URLs, and
   return the teardown from the same function — never a start per file or per test: a compose `up` with `--build`
   builds every image and boots every container, which takes minutes.
4. Make each test independent of the others sharing the system: unique data per test (a builder with a unique email
   or key), and a unique recipient for any mail it waits for.
5. Run the suite; the first run on a clean agent builds and pulls images, so budget the startup timeout for it.

## Templates

### Starting the system — `tests/system/support/system.ts`

```ts
import { DockerComposeEnvironment, Wait, type StartedDockerComposeEnvironment } from 'testcontainers';

const STARTUP_BUDGET_MS = 300_000;

export interface SystemUrls {
  apiUrl: string;
  mailpitUrl: string;
  databaseUrl: string;
}

export async function startSystem(repoRoot: string): Promise<StartedDockerComposeEnvironment> {
  return new DockerComposeEnvironment(repoRoot, ['compose.yaml', 'compose.test.yaml'])
    .withBuild()
    .withEnvironment({ PAYMENTS_MODE: 'sandbox', USE_VOLUMES: 'false' })
    .withWaitStrategy('api-1', Wait.forHttp('/health', 8080).forStatusCode(200))
    .withWaitStrategy('worker-1', Wait.forHttp('/health', 8081).forStatusCode(200))
    .withWaitStrategy('mailpit-1', Wait.forHttp('/api/v1/info', 8025).forStatusCode(200))
    .withWaitStrategy('db-1', Wait.forHealthCheck())
    .withStartupTimeout(STARTUP_BUDGET_MS)
    .up();
}

export function systemUrls(environment: StartedDockerComposeEnvironment): SystemUrls {
  const db = environment.getContainer('db-1');
  return {
    apiUrl: httpUrl(environment, 'api-1', 8080),
    mailpitUrl: httpUrl(environment, 'mailpit-1', 8025),
    databaseUrl: `postgres://test:test@${db.getHost()}:${db.getMappedPort(5432)}/app`,
  };
}

function httpUrl(environment: StartedDockerComposeEnvironment, container: string, port: number): string {
  const started = environment.getContainer(container);
  return `http://${started.getHost()}:${started.getMappedPort(port)}`;
}
```

- **Wait strategies match container names, not service names.** Compose v2 names the first replica
  `<service>-1`, so the `api` service is `'api-1'`; a strategy keyed `'api'` matches nothing and Testcontainers only
  logs a warning.
- **Wait for healthy, not for running.** With no strategy, Testcontainers waits for the service's compose
  `healthcheck:` when it has one, else for listening ports — and a listening port is not a ready service.
  `Wait.forHttp(path, port)` probes from the host, so it also works for distroless images that have no `curl` to run
  a compose healthcheck with; `Wait.forHealthCheck()` suits images that ship their own (Postgres, Redis).
- **One startup budget** for the whole `up`; with `withBuild()` on a clean agent, 5 minutes, not 30 s.
- **`withBuild()`** builds the services from the working tree, so the test runs the code under review, not an image
  someone pushed last week.
- **Leave the project name random** (the default): parallel CI jobs on one Docker host then never share containers,
  networks or volumes. A fixed `withProjectName` is for a stack started by hand outside the suite.
- **No retry wrapper on the test's HTTP client.** A retry turns a real 5xx into a pass on the second try; the health
  wait already removes the startup race.

### Vitest — `tests/system/setup/start-system.ts`

```ts
import type { TestProject } from 'vitest/node';
import { startSystem, systemUrls } from '../support/system.js';

export default async function setup(project: TestProject): Promise<() => Promise<void>> {
  const environment = await startSystem(project.config.root);
  const urls = systemUrls(environment);

  project.provide('apiUrl', urls.apiUrl);
  project.provide('mailpitUrl', urls.mailpitUrl);
  project.provide('databaseUrl', urls.databaseUrl);

  return async () => {
    await environment.down({ timeout: 30_000 });
  };
}

declare module 'vitest' {
  export interface ProvidedContext {
    apiUrl: string;
    mailpitUrl: string;
    databaseUrl: string;
  }
}
```

```ts
// vitest.system.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['tests/system/**/*.system.test.ts'],
    globalSetup: ['./tests/system/setup/start-system.ts'],
    testTimeout: 30_000,
  },
});
```

- **Global setup runs in a different scope from the tests**, before the workers exist: a variable set there is
  invisible to them. Pass serializable values with `project.provide` and read them with `inject('apiUrl')`; the
  `ProvidedContext` declaration types both ends.
- **The teardown is returned by the function that started the stack**, so it holds the started environment without
  module-level state. `down({ timeout })` waits for the stack to go and removes its volumes; without a timeout it
  returns before the containers are gone.

### Playwright — `tests/e2e/global-setup.ts`

```ts
import { startSystem, systemUrls } from '../system/support/system.js';

export default async function globalSetup(): Promise<() => Promise<void>> {
  const environment = await startSystem(process.cwd());
  const urls = systemUrls(environment);

  process.env.API_URL = urls.apiUrl;
  process.env.MAILPIT_URL = urls.mailpitUrl;

  return async () => {
    await environment.down({ timeout: 30_000 });
  };
}
```

Run Playwright from the repo root, where the compose files are. Its workers start after global setup and inherit its
environment variables, so `process.env` is the hand-over here; fixtures read them through `requiredEnv('API_URL')`.
Prefer `globalSetup` over a setup *project* for this: a setup project runs in a worker that exits before the teardown
project runs, so nothing would hold the started environment to bring it down.

### A test

```ts
import { describe, expect, inject, it } from 'vitest';
import { OrderRequestBuilder } from '../builders/order-request.builder.js';
import { newTraceparent } from '../support/testTrace.js';

const apiUrl = inject('apiUrl');

describe('POST /orders', () => {
  it('Should_ReturnCreated_When_AValidOrderIsPosted', async () => {
    const order = new OrderRequestBuilder().build();

    const response = await fetch(`${apiUrl}/orders`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', traceparent: newTraceparent() },
      body: JSON.stringify(order),
    });
    const body = await response.text();

    expect(response.status, body).toBe(201);
  });
});
```

**Every request carries a `traceparent`** with one trace id per test (`api-client-writer/references/trace-context.md`;
a typed client built by `api-client-writer` already sends it from its `baseClient`). Across services this is what pays:
when the compose file runs the OpenTelemetry collector and the local Grafana stack, the API's spans, the worker's spans
for the message it consumed and the database calls land in **one trace**, and a failed test links straight to it
(`qa/reporting/typescript/skills/test-reports`, `references/trace-links.md`).

### Overriding the system for tests

| Need | How |
|---|---|
| Switch a behaviour the compose file interpolates | `withEnvironment({ PAYMENTS_MODE: 'sandbox' })` for `${PAYMENTS_MODE}` in the file |
| Change one service's settings, ports or volumes | A `compose.test.yaml` passed after the main file; `!override` / `!reset` replace a list instead of appending to it |
| Start only part of the system | `withProfiles('mail')`, or `.up(['api', 'db', 'mailpit'])` with the service names |
| Replace an external dependency (a payment provider) | Make the service choose it from an environment flag and set the flag; never edit the compose file per test |
| Seed or verify rows | `inject('databaseUrl')` with `db-testing/verification-queries` |

A test cannot replace code inside a running service: the service is a separate process in a separate container.
Behaviour that needs a fake belongs in the service's configuration or in a `db-testcontainers` test of that one API.

## Email — Mailpit as a compose service

When the system sends mail, declare the sink in the compose file the test starts, and point the SUT's SMTP settings at
it on the compose network (`SMTP_HOST: mailpit`, `SMTP_PORT: 1025`) — no second container started from the test:

```yaml
services:
  mailpit:
    image: axllent/mailpit:v1.20.5
    ports: ["8025"]
```

The test builds the `MailpitClient` from `email-testing/references/mailpit.md` on `inject('mailpitUrl')` and waits for
its own unique recipient:

```ts
import { MailpitClient } from '../email/mailpit-client.js';
import { uniqueRecipient } from '../email/recipients.js';

const mail = new MailpitClient(inject('mailpitUrl'));

it('Should_SendTheConfirmation_When_AnOrderIsPlaced', async () => {
  const email = uniqueRecipient('order');
  const order = new OrderRequestBuilder().withEmail(email).build();

  const response = await fetch(`${apiUrl}/orders`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', traceparent: newTraceparent() },
    body: JSON.stringify(order),
  });
  expect(response.status, await response.text()).toBe(201);

  const confirmation = await mail.get((await mail.waitFor(email, 'Order confirmation')).ID);

  expect(confirmation.To.map((to) => to.Address)).toEqual([email]);
});
```

The shared email rules apply: a unique recipient per test, a condition-wait, never a sleep, never a global wipe of
the inbox. Snapshotting the rendered email is `email-testing/references/html-snapshots.md`.

## Rules

The standards this skill's output must meet are the qa-typescript rule files, not a list here: `qa-typescript.md`,
`api-tests.md` and, for the pipeline job, `ci-tests.md`. Read the project's copy in `.claude/rules/qa-typescript/`, or
the plugin's in `qa/typescript/skills/rules/` when the project has not installed them (`/qa-typescript:rules` does).
Where they and this skill's recipes disagree, the rule files win.

## Output format

```
Created: tests/system/support/system.ts                 Purpose: start the compose stack, wait for health, resolve URLs
Created: tests/system/setup/start-system.ts             Purpose: Vitest global setup — provide URLs, return teardown
Created: vitest.system.config.ts                        Purpose: the system-test project
Created: compose.test.yaml                              Purpose: container-only ports, test settings
Created: tests/system/<area>/<feature>.system.test.ts   Purpose: Should_X_When_Y tests over the services
```

Then: the services the setup waits for and how, the settings it overrides, and the run result.

## Anti-examples

- **`new DockerComposeEnvironment(...).up()` in `beforeAll` of every file** — a full build and boot per file; the
  suite takes minutes per file. Start it once in global setup.
- **`await new Promise((r) => setTimeout(r, 10_000))` until the API answers** — wait with a health strategy.
- **Fixed host ports in the compose file the tests use** — two jobs on one agent collide; read `getMappedPort`.
- **`withWaitStrategy('api', ...)`** — a service name; the container is `api-1`, and the strategy silently never
  applies.
- **Asserting a unit's branches through the whole system** — slow and imprecise; that is the `be-node` unit test.

## Handoffs

- Database seeding and row verification → `qa/typescript/skills/db-testing/verification-queries`
- Mailpit client and email assertions → `email-testing`
- Trace ids on requests → `api-client-writer` (`references/trace-context.md`); trace links on failures →
  `qa/reporting/typescript/skills/test-reports`
- The CI job (Docker and the Compose plugin on the agent, image builds and caching) →
  `qa/cicd/typescript/skills/ci-pipelines`
- Unit tests of the logic inside a service → `be-node` `unit-testing`
