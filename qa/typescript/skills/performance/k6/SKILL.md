---
name: qa-performance-k6-typescript
description: Use when the user asks to design or author k6 (Grafana k6) performance / load tests in JavaScript/TypeScript. Triggers: "write a k6 script for endpoint X", "design a k6 average load test", "spike test in k6".
---

# QA — Performance Testing with k6 (TypeScript / JavaScript)

Authors k6 scripts against deployed services. k6 ships as a single Go binary and accepts JS (or TS via the `xk6-ts` bundler / esbuild) scripts; this skill defaults to **plain ESM JavaScript** because it runs unmodified in `grafana/k6`. For TS authoring, bundle to JS before running.

## When to use

- Default tool for new perf work in any stack — k6 is language-independent at runtime.
- Smoke / average / stress / spike / soak / capacity tests of HTTP, gRPC, or WebSocket endpoints.
- Browser-level perf via `k6/browser` (Chromium-driven) where Playwright would be overkill.
- CI smoke perf gate on PRs.

## When NOT to use

- NBomber (.NET-native author experience) → `qa/dotnet/skills/performance/nbomber`
- Gatling (JVM-native author experience) → `qa/java/skills/performance/gatling`
- Functional behavior tests → `qa/typescript/skills/api-test-author/generator/<stack>` / `qa/typescript/skills/ui-test-author/<stack>`
- Unit benchmarks → Vitest bench / `tinybench`
- Defining the SLO itself → `qa/manual/quality-metrics`

Load `qa/_shared/performance` for workload models, open-loop vs closed-loop guidance, environment policy, and the reporting template.

## Layout

```
tests/perf/
├── lib/
│   ├── auth.js                 ← token fetch / refresh helper
│   ├── fixtures.js             ← setup() / teardown() shared helpers
│   └── env.js                  ← BASE_URL / TOKEN resolution
├── orders-smoke.js             ← smoke
├── orders-average.js           ← average load
├── orders-spike.js             ← spike
├── orders-soak.js              ← soak / endurance
└── package.json                ← devDeps for TS bundling (optional)
```

## Average-load test against a JSON API

```javascript
// tests/perf/orders-average.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Counter } from 'k6/metrics';

const latency = new Trend('orders_get_latency', true);
const errors  = new Counter('orders_errors');

export const options = {
  scenarios: {
    average: {
      executor: 'ramping-arrival-rate',
      startRate: 5, timeUnit: '1s',
      preAllocatedVUs: 50, maxVUs: 200,
      stages: [
        { target: 50,  duration: '1m'  },  // ramp up
        { target: 50,  duration: '5m'  },  // hold
        { target: 0,   duration: '30s' },  // ramp down
      ],
    },
  },
  thresholds: {
    'http_req_duration{name:GET /orders/{id}}': ['p(95)<300', 'p(99)<800'],
    'http_req_failed':                          ['rate<0.005'],
    'orders_errors':                            ['count<10'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'https://api-staging.yourco.com';
const TOKEN    = __ENV.AUTH_TOKEN;
const IDS      = ['o-001', 'o-002', 'o-003', 'o-004', 'o-005'];

export default function () {
  const id  = IDS[Math.floor(Math.random() * IDS.length)];
  const res = http.get(`${BASE_URL}/orders/${id}`, {
    headers: { Authorization: `Bearer ${TOKEN}` },
    tags: { name: 'GET /orders/{id}' },
  });

  latency.add(res.timings.duration);

  const ok = check(res, {
    'status is 200': (r) => r.status === 200,
    'has id field':  (r) => r.json('id') === id,
  });
  if (!ok) errors.add(1);

  sleep(0.1);
}
```

Notes:
- `ramping-arrival-rate` (open-loop) — the right executor for "we want N RPS regardless of VU performance". `ramping-vus` (closed-loop) is for "we want N concurrent users".
- `thresholds` keyed by **route tag** so a fast endpoint doesn't mask a slow one.
- `__ENV.BASE_URL` / `__ENV.AUTH_TOKEN` — no hardcoded secrets.
- `res.json('id')` — JSONPath form is faster than `res.json().id` because it stops at the first match.

## Smoke (1-minute PR gate)

```javascript
export const options = {
  scenarios: {
    smoke: {
      executor: 'constant-arrival-rate',
      rate: 5, timeUnit: '1s',
      duration: '1m',
      preAllocatedVUs: 5, maxVUs: 10,
    },
  },
  thresholds: {
    'http_req_failed':                          ['rate<0.001'],
    'http_req_duration{name:GET /orders/{id}}': ['p(95)<400'],
  },
};
```

## Spike

```javascript
export const options = {
  scenarios: {
    spike: {
      executor: 'ramping-arrival-rate',
      startRate: 10, timeUnit: '1s',
      preAllocatedVUs: 50, maxVUs: 500,
      stages: [
        { target: 10,  duration: '1m'  },   // baseline
        { target: 500, duration: '10s' },   // spike
        { target: 500, duration: '1m'  },   // hold
        { target: 10,  duration: '1m'  },   // recovery
      ],
    },
  },
};
```

## Soak (4-hour endurance)

```javascript
export const options = {
  scenarios: {
    soak: {
      executor: 'constant-arrival-rate',
      rate: 100, timeUnit: '1s',
      duration: '4h',
      preAllocatedVUs: 200, maxVUs: 500,
    },
  },
  thresholds: {
    'http_req_duration{name:GET /orders/{id}}': ['p(95)<300'],
    'http_req_failed':                          ['rate<0.01'],
  },
};
```

Watch the **slope**: latency drifting upward over the 4 hours is the leak the soak is meant to catch.

## Setup / teardown

```javascript
export function setup() {
  // Create perf fixtures via the same client production uses.
  const token = http.post(`${__ENV.AUTH_URL}/oauth/token`, { /* ... */ }).json('access_token');
  const orderIds = createSeededOrders(token, 10);
  return { token, orderIds };
}

export default function (data) {
  const id = data.orderIds[Math.floor(Math.random() * data.orderIds.length)];
  http.get(`${BASE_URL}/orders/${id}`, { headers: { Authorization: `Bearer ${data.token}` } });
}

export function teardown(data) {
  // Always clean up seeded data — namespace ids with the run id so parallel runs don't collide.
  deleteSeededOrders(data.token, data.orderIds);
}
```

`setup` runs once before the test; `teardown` runs once after. Their return value is the `data` argument to `default` and `teardown`.

## Custom metrics

```javascript
import { Trend, Counter, Rate, Gauge } from 'k6/metrics';

const checkoutLatency = new Trend('checkout_latency', true);
const checkoutOk      = new Rate('checkout_success_rate');

checkoutLatency.add(res.timings.duration);
checkoutOk.add(res.status === 200);
```

Threshold against custom metrics: `'checkout_success_rate': ['rate>0.99']`.

## TypeScript authoring

Write `.ts`, compile to `.js` for the runner. Recommended bundler config (`esbuild`):

```jsonc
// package.json
{
  "scripts": {
    "build:perf": "esbuild tests/perf/orders-average.ts --bundle --target=es2020 --platform=neutral --external:k6 --external:k6/* --outfile=dist/orders-average.js"
  },
  "devDependencies": {
    "@types/k6": "^0.49.0",
    "esbuild": "^0.21.0",
    "typescript": "^5.4.0"
  }
}
```

Run `k6 run dist/orders-average.js`. Mark every `k6` / `k6/*` import as external so esbuild doesn't try to resolve them.

## Tool version pinning

Pin the k6 image / binary version everywhere:

```yaml
- name: Smoke perf
  run: |
    docker run --rm -i \
      -e BASE_URL=$STAGING_URL \
      -e AUTH_TOKEN=$STAGING_TOKEN \
      grafana/k6:0.49.0 run --quiet - < tests/perf/orders-smoke.js
```

`grafana/k6:latest` is forbidden — results drift on tool updates.

## CI integration

### GitHub Actions — smoke on PR

```yaml
perf-smoke:
  runs-on: ubuntu-latest
  if: github.event_name == 'pull_request'
  steps:
    - uses: actions/checkout@v4
    - name: Run k6 smoke
      run: |
        docker run --rm -i \
          -e BASE_URL=${{ secrets.STAGING_URL }} \
          -e AUTH_TOKEN=${{ secrets.STAGING_TOKEN }} \
          grafana/k6:0.49.0 run --quiet --out json=k6-results.json - \
          < tests/perf/orders-smoke.js
    - uses: actions/upload-artifact@v4
      if: always()
      with: { name: k6-results, path: k6-results.json }
```

### Grafana Cloud k6

For richer scenarios (cluster mode, dashboards), add `loadimpact` options:

```javascript
export const options = {
  ext: {
    loadimpact: {
      projectID: 12345,
      name: 'orders-average',
    },
  },
};
```

Run with `k6 cloud run --token $K6_CLOUD_TOKEN script.js`.

## Output to Prometheus / Loki (correlate during the test)

```bash
k6 run -o experimental-prometheus-rw script.js
```

Configure the remote-write endpoint via `K6_PROMETHEUS_RW_SERVER_URL`. The metrics land in Prometheus alongside the service's own metrics — `observability/grafana-dashboards` shows both on one chart.

## Rules (k6-specific)

- **Open-loop (`arrival-rate`) by default.** Closed-loop (`vus`) only when modelling a fixed concurrency cap.
- **`thresholds` mandatory** and keyed by `{name:…}` tag for per-route gates.
- **`tags: { name: '…' }`** on every `http.*` call — without it, `http_req_duration` averages across endpoints.
- **`__ENV.*`** for `BASE_URL`, tokens, and tunables; never hardcode.
- **`preAllocatedVUs`** sized realistically (rule of thumb: target RPS × p95 latency in seconds + 20% headroom). Don't `maxVUs: 10000`.
- **`setup()` / `teardown()`** for seeded fixtures; namespace fixture ids by `__VU` + `Date.now()` to avoid parallel-run collisions.
- **Pin k6 image** (`grafana/k6:0.49.0`); never `:latest`.
- **No `JSON.parse(JSON.stringify(...))`** to clone — use `Object.assign({}, …)` or spread; `JSON` is hot-path expensive in VU loops.
- **No `console.log` in the steady state** — it costs ~10% throughput at high RPS. Use `--verbose` only locally.

## What NOT to do

- No `http_req_duration` thresholds aggregated across all routes — always tag and threshold per route.
- No closed-loop VU test for an RPS target.
- No hardcoded tokens or base URLs.
- No `sleep(0)` (zero sleep) inside hot loops — k6 already handles arrival-rate spacing; explicit `sleep` is for closed-loop pacing only.
- No `--vus 10000 --duration 1h` "to see what happens" — bound the test or set an exit threshold.
- No `tags: { name: '…' }` missing on `http.*` calls — per-route gates break.
- No mixing arrival-rate scenarios with VU scenarios in the same `options.scenarios` unless you really mean it (they compete for VUs from the same pool).
- No `check(...)` calls that don't increment a Rate or Counter — failed checks alone aren't a gate.
- No writing to test-environment databases without `teardown()` cleanup.
- No `import 'somepkg'` outside `k6` / `k6/*` from a script being run directly by `k6 run` — bundle via esbuild first.

## Generation steps

1. Confirm tool (k6), workload model, SLO targets, target environment. (See `_shared`.)
2. Pick the executor (open-loop for RPS targets).
3. Write the script with `tags: { name: '…' }` on every request and per-route `thresholds`.
4. Wire env vars (`BASE_URL`, `AUTH_TOKEN`).
5. Add `setup()` / `teardown()` for seeded fixtures, namespacing ids per run.
6. If authoring in TS, configure esbuild to mark `k6` / `k6/*` as external; run `npm run build:perf`.
7. Add CI step (smoke on PR; full on release). Pin `grafana/k6:<version>`.
8. Run locally; review per-route thresholds; confirm the test fails when an SLO is breached.
9. Add the report to the release / change notes (see `_shared` template).

## Handoffs

- Workload models, environment policy, reporting → `qa/_shared/performance`
- NBomber (.NET) → `qa/dotnet/skills/performance/nbomber`
- Gatling (Java) → `qa/java/skills/performance/gatling`
- SLO targets the test validates → `qa/manual/quality-metrics`
- Grafana dashboards for server-side correlation → `observability/grafana-dashboards`
- LogQL / PromQL for queries → `observability/logql-promql`
- Pipeline integration → `qa/cicd/typescript/skills/ci-pipelines/{github-actions,azure-pipelines,gitlab-ci}` or `devops/<ci>`
- Allure publishing for perf reports → `qa/reporting/typescript/skills/allure-reporting`
- Bug filings discovered during perf → `qa/manual/bug-report-writer`
