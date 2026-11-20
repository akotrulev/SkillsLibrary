---
name: api-project-setup
description: Use when starting an API test project from zero in TypeScript (Vitest, fetch, Zod, pins, config loader). Triggers "scaffold an API test project". Not for writing tests (api-tests).
disable-model-invocation: true
---

# API Test Project Scaffold (TypeScript, Vitest + fetch + Zod)

This skill stands up a **runnable, empty API test project from zero**: the layout, exact versions, the config loader, the base client, one smoke test that proves the wiring, and the run commands. It owns the **project shell**. The test conventions belong to the author skills: specs to `api-test-author/writer`, clients to `api-client-writer`, schemas to `api-models`, tokens to `test-login-tokens`. The files the shell needs ship in `assets/` here, compiled and run; copy them, never re-type them.

**Version rule:** new projects use Node 24 (22 maintenance) and TypeScript strict mode. Vitest 5 needs Node ^22.12 or ≥ 24. Node 20 is end-of-life: never target it. In an existing repo keep its Node, Vitest and Zod majors.

The stack default is **Vitest + native `fetch` + Zod** with `{resource}Client` factories that have a raw and a typed method. A project that already runs Playwright Test puts its API specs in that suite instead, through the `request` fixture: `qa/typescript/skills/api-test-author/playwright`, and the shell is `qa/typescript/skills/ui-project-setup`.

## Tooling & versions

`assets/package.json` holds these exact pins (`npm i -D -E`, no ranges). Every one is a dev dependency: a test project ships nothing.

| Concern | Package / tool | Version | Notes |
|---|---|---|---|
| Runtime | Node | **24** | 22 maintenance; `engines.node` is `>=22.12.0`, Vitest 5's floor |
| Language | `typescript` | **5.9.3** | `strict: true`, `noUncheckedIndexedAccess`, `module: NodeNext` (the stack's other assets' pin) |
| Types | `@types/node` | **24.19.2** | |
| Runner | `vitest` | **5.1.0** | Run with `vitest run`; checked 2026-11-17 with `allure-vitest` 3.13.0 and `expect.getState()` (the trace id) |
| Schemas | `zod` | **4.6.7** | Response objects are `.strict()`; the base client's `parseBody` reports `issues[].path` and `code` with the raw body |
| HTTP | native `fetch` | Node built-in | No axios, got or supertest |
| Reporting | `allure-vitest`, `allure-js-commons` | **3.13.0** | Pins of `qa/reporting/typescript/skills/test-reports`, which owns the wiring |
| Allure CLI | `allure-commandline` | **2.46.1** | Installed and pinned by `test-reports`; this scaffold installs none |

Add only when the plan needs them: `auth0` (`test-login-tokens`), Testcontainers (`db-testing/testcontainers`), Pact (`api-contract-testing`).

## Prerequisites & local setup

```bash
node --version
npm --version
```

`node --version` prints v24.x (or v22.12+). No browser, emulator or Docker is needed: an API suite is the cheapest module to stand up. A Java runtime is needed only to turn results into a report (`test-reports`).

## Project layout (standalone)

```
<product>-api-tests/
├── package.json · package-lock.json      # assets/package.json; commit the lock
├── tsconfig.json                         # assets/tsconfig.json
├── vitest.config.ts                      # specs glob, default + junit + allure reporters
├── .env.example · .gitignore · README.md
├── specs/                                # stored OpenAPI assets (qa/_shared/api-spec-assets)
└── src/
    ├── config/environment.ts             # the one config loader: requiredEnv, getTestEnvironment
    ├── support/testTrace.ts              # one traceparent trace id per test
    ├── clients/
    │   ├── baseClient.ts                 # execute(): fetch, traceparent, Authorization; parseBody()
    │   └── platform/healthClient.ts      # the smoke's client: raw get() + typed getTyped()
    ├── models/platform/health/           # health.schema.ts (Zod) + health.types.ts (z.infer)
    └── specs/platform/health/getHealth.spec.ts
```

`{api}/{resource}` folders follow `api-test-author/writer`: one client module per resource, one spec per operation. `testTrace.ts` and the `traceparent` line in `baseClient.ts` are the code of `api-client-writer`'s `references/trace-context.md`. The folder name ends in `-api-tests` so the installed rule files' default globs match it.

## Configuration

**One loader, one precedence.** `src/config/environment.ts` reads every setting through `requiredEnv(name)`: `process.env` wins (the shell, a sourced local `.env`, or the CI secret store), then the committed non-secret default in that file's `DEFAULTS`; a key with neither throws naming the key. `getTestEnvironment()` exposes the typed settings the clients read (`apiUri`). Clients and specs never read `process.env`.

| Key | Default | Read by |
|---|---|---|
| `API_BASE_URL` | `http://localhost:8080` | `getTestEnvironment().apiUri`, every client |

- A secret (client secret, password, token) has **no default** and never sits in a committed file: CI injects it, a developer exports it.
- A key is declared when the first code reads it, and not before: the Auth0 keys arrive with the token provider (`test-login-tokens`).

`.env.example`, committed, with no real values:

```
API_BASE_URL=
```

Load a local copy with `set -a; source .env; set +a`. `.gitignore`:

```
node_modules/
test-results/
allure-results/
allure-report/
.env
```

## Create from zero

```bash
mkdir <product>-api-tests && cd <product>-api-tests
git init
cp -R <skills>/qa/typescript/skills/api-project-setup/assets/. .
npm install
npm run typecheck
```

`<skills>` is this library's root (`${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Then rename `"name"` in `package.json`, write `.env.example`, `.gitignore` and `README.md` from this page, and commit `package-lock.json`. Every later install is `npm ci`.

The smoke assumes an unauthenticated `GET /health` returning `{ "status": "Healthy" }`. Point it at the API's own health or status endpoint: change `GET_PATH`, the schema's fields and the expected value, keeping the shape (typed client call, one assertion). An API with no such endpoint uses its first read-only, unauthenticated endpoint the same way.

## The smoke test

```ts
import { describe, expect, it } from 'vitest';
import { createHealthClient } from '../../../clients/platform/healthClient.js';

describe('GET /health', () => {
  it('Should_ReportHealthy_When_ApiIsUp', async () => {
    const health = await createHealthClient('').getTyped(200);

    expect(health.status, 'health status').toBe('Healthy');
  });
});
```

It proves the chain: the config loader resolves the base URL, `execute` sends the request with a `traceparent`, the typed method asserts the exact status, and `parseBody` validates the strict schema, so a field the API added fails with `<root> unrecognized_keys` and the body. `''` builds an anonymous client. The body reads nothing it did not request and creates nothing, so it needs no teardown.

## Run

```bash
npm test
npx vitest run src/specs/platform/health
API_BASE_URL=https://api.staging.example.test npm test
npx vitest run -t "Should_ReportHealthy"
```

The exit gate for the project: `npm run typecheck` clean and the smoke green against a reachable API. `npm test` writes `test-results/junit.xml` and `allure-results/`; turning the results into a report (also as one HTML file) is `qa/reporting/typescript/skills/test-reports`. CI is `qa/cicd/typescript/skills/ci-pipelines`: install with `npm ci`, run `npm test`, no `|| true`.

## Conventions (the shell only)

The standards the shell must meet are the qa-typescript rule files, not a list here: `qa-typescript.md`, `api-tests.md` and `test-data.md`. Tell the user to install them with the shell (`/qa-typescript:rules` copies them into `.claude/rules/qa-typescript/`); until then read the plugin's copies in `qa/typescript/skills/rules/`. Where they and this skill's recipes disagree, the rule files win.

- **One base client.** `createBaseClient` is the only `fetch` call in the project. It skips `Authorization` for `''`, drops `undefined` query values and adds `traceparent`. Its one `catch` narrows a `SyntaxError` from a body that claims JSON and rethrows with the body.
- **Auth**: tokens come from a token provider (`test-login-tokens`), fetched by the spec and passed to `create{Resource}Client(jwt)`; a client never fetches one.
- **Allure hook**: the `allure-vitest/reporter` entry in `vitest.config.ts`; `test-reports` owns the runtime calls, categories and CI publish.

Spec shapes, clients, schemas, builders and the scenario set are owned by the author skills. Defer to them.

## Expanding

- **A second API group** is a new `src/clients/<api>/`, `src/models/<api>/` and `src/specs/<api>/`; the base client and config loader are shared.
- **API + UI in one repo:** the UI suite is a sibling folder from `qa/typescript/skills/ui-project-setup`, with its own `package.json`, `playwright.config.ts` and `env.ts`. Keep two lockfiles rather than one `package.json` serving two runners; the UI suite's fixtures seed data through its own `request` fixture.

## Setup checklist

- [ ] Node 24 (22.12+ supported); `package.json` pins exact versions, all dev dependencies; `package-lock.json` committed
- [ ] `tsconfig.json` strict, `noUncheckedIndexedAccess`, `module: NodeNext`
- [ ] `src/config/environment.ts` is the only reader of `process.env`; precedence env → committed default → fail naming the key
- [ ] No secret in a committed file; `.env` ignored, `.env.example` committed with empty values
- [ ] `baseClient.ts` sends `traceparent` on every request
- [ ] `vitest.config.ts` writes `test-results/junit.xml` and `allure-results/`
- [ ] The smoke points at the API's own health or status endpoint
- [ ] `npm run typecheck` clean; `npm test` green.
