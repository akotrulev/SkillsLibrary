# Trace context — one trace id per test, on every request

A failed API test is diagnosed in the backend's telemetry: the spans in Tempo and the log lines in Loki. They
are found by trace id only if the test sent one. Every request a test makes carries a W3C `traceparent`
header with **the same trace id for the whole test**, so the backend's spans for that test land in one trace
and `qa/reporting/typescript/skills/test-reports` (`references/trace-links.md`) can link to it from the failed
result.

## The header

`traceparent: 00-<trace-id>-<parent-id>-01` (W3C Trace Context, version `00`):

| Field | Value |
|---|---|
| `trace-id` | 32 lowercase hex characters (16 bytes); all zeros is invalid and the backend ignores the header |
| `parent-id` | 16 lowercase hex characters (8 bytes), new for each request; all zeros is invalid |
| `trace-flags` | `01` — sampled, so a parent-based sampler (the OpenTelemetry SDK default) records the trace |

The backend's OpenTelemetry instrumentation reads the header with its default W3C propagator and makes its
server span a child of `parent-id`. The test exports no span of its own, so Tempo shows the trace with a
missing root; the backend's spans are all there.

## The trace id: derived from the current Vitest test

Clients are created with `create{Resource}Client(jwt)` and know nothing of the test, so the trace id is derived
instead of passed: a hash of the current test's file and full name (`expect.getState()`) with a salt fixed
once per worker. `baseClient` computes it per request; the reporting setup file (`test-reports`) computes the
same value on failure. No factory signature changes.

```ts
// src/support/testTrace.ts
import { createHash, randomBytes } from 'node:crypto';
import { expect } from 'vitest';

const RUN_SALT = randomBytes(16).toString('hex');

export function currentTraceId(): string {
  const { testPath, currentTestName } = expect.getState();
  return createHash('sha256').update(`${RUN_SALT}|${testPath}|${currentTestName}`).digest('hex').slice(0, 32);
}

export function newTraceparent(): string {
  return `00-${currentTraceId()}-${randomBytes(8).toString('hex')}-01`;
}
```

`RUN_SALT` is a module constant, not mutable state: two runs never share a trace id, and every call in one test
returns the same one. The setup file and `baseClient` import the same module in the same worker, so they see
the same salt.

## `baseClient` sends it

`createBaseClient`'s `execute` adds the header to every request, beside `Authorization`:

```ts
import { newTraceparent } from '../support/testTrace.js';

const headers: Record<string, string> = {
  accept: 'application/json',
  traceparent: newTraceparent(),
  ...(authToken ? { authorization: `Bearer ${authToken}` } : {}),
};
```

Keep the rest of the project's `execute` as it is; add only the `traceparent` entry.

## Playwright `APIRequestContext` projects

A suite that sends its API calls through Playwright Test's `request` fixture sets the header on the context it
creates per test, with `extraHTTPHeaders`:

```ts
api: async ({ playwright }, use, testInfo) => {
  const traceId = randomBytes(16).toString('hex');
  testInfo.annotations.push({ type: 'trace-id', description: traceId });
  const api = await playwright.request.newContext({
    baseURL: requiredEnv('API_URL'),
    extraHTTPHeaders: { traceparent: `00-${traceId}-${randomBytes(8).toString('hex')}-01` },
  });
  await use(api);
  await api.dispose();
},
```

One `parent-id` for the whole test is still a valid trace; the trace id is what joins the spans.

## Rules

- One trace id per test, a new `parent-id` per request where the client allows it, flags `01`. Never a fixed
  trace id in config.
- The header goes only to the API under test. A client for a third party is built without it — a trace id
  leaked to a vendor is noise in their logs and tells them what you run.
- `expect.getState()` tracks the current test only for tests that run one at a time in a worker. A
  `test.concurrent` block shares the global state; an API suite keeps its tests sequential within a file,
  which its data cleanup already relies on.
- Checked 2026-11-14 on Vitest 3.2: `expect.getState()` returns the running test's `testPath` and
  `currentTestName` inside the test body.
