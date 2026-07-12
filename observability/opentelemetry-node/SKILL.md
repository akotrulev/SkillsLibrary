---
name: observability-opentelemetry-node
description: Use when the user asks to instrument a Node 20 + TypeScript service (NestJS / Express / Fastify) with OpenTelemetry — traces, metrics, log correlation — and export OTLP to a Collector. Triggers: "instrument this Node service with OTel", "add a custom span / counter", "auto-instrument http and pg", "wire OTLP gRPC exporter", "trace context propagation". Do NOT use for .NET (use `observability/opentelemetry-dotnet`), Java (use `observability/opentelemetry-java`), or log shaping (use `observability/structured-logging-node`).
---

# Observability — OpenTelemetry (Node 20 / TypeScript)

Instruments a Node 20 + TypeScript service with OpenTelemetry. Bootstraps via a `-r` preload that registers auto-instrumentations **before** application code requires anything, exposes a `tracer` and `meter` API for custom spans/metrics, and ships OTLP/gRPC to a Collector that forwards to Tempo / Prometheus / Loki.

## Stack

- **Node 20 + TypeScript** (strict mode)
- **`@opentelemetry/sdk-node`** + **`@opentelemetry/auto-instrumentations-node`** — auto-instruments `http`, `express`, `fastify`, `pg`, `mysql2`, `mongodb`, `redis`/`ioredis`, `aws-sdk`, `grpc`, ~80 libraries
- **`@opentelemetry/exporter-trace-otlp-grpc`** + **`@opentelemetry/exporter-metrics-otlp-grpc`**
- **`@opentelemetry/instrumentation-pino`** — bridges OTel context → pino logs (see `observability/structured-logging-node`)
- Resource attributes via `@opentelemetry/resources` and `@opentelemetry/semantic-conventions`

## When to use

- New Node service needs OTel
- Adding auto-instrumentation to an existing NestJS / Express / Fastify service
- Adding custom spans to a worker / consumer / background job
- Adding a custom counter / histogram (request count, queue depth, processing time)
- Wiring OTLP export to a Collector

## When NOT to use

- .NET service → `observability/opentelemetry-dotnet`
- Java service → `observability/opentelemetry-java`
- Log shape / sinks → `observability/structured-logging-node`
- Dashboards / queries → `observability/grafana-dashboards` + `observability/logql-promql`

## Inputs needed

1. **Service name + version + environment**
2. **Collector endpoint** (`http://otel-collector:4317`)
3. **Sampling strategy**
4. **Framework** (NestJS, Express, Fastify, bare Node) — affects how some auto-instrumentations attach
5. **Custom domain spans** — workers, message handlers, in-process pipelines that auto-instrumentation won't see

## Setup

### Packages

```bash
pnpm add @opentelemetry/api \
         @opentelemetry/sdk-node \
         @opentelemetry/auto-instrumentations-node \
         @opentelemetry/exporter-trace-otlp-grpc \
         @opentelemetry/exporter-metrics-otlp-grpc \
         @opentelemetry/resources \
         @opentelemetry/semantic-conventions \
         @opentelemetry/instrumentation-pino
```

### Bootstrap — `src/otel.ts`

```typescript
import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-grpc';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-grpc';
import { PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';
import { resourceFromAttributes } from '@opentelemetry/resources';
import { ATTR_SERVICE_NAME, ATTR_SERVICE_VERSION } from '@opentelemetry/semantic-conventions';
import { PinoInstrumentation } from '@opentelemetry/instrumentation-pino';
import { ParentBasedSampler, TraceIdRatioBasedSampler } from '@opentelemetry/sdk-trace-base';

const isProd = process.env.NODE_ENV === 'production';

const sdk = new NodeSDK({
  resource: resourceFromAttributes({
    [ATTR_SERVICE_NAME]:    process.env.OTEL_SERVICE_NAME ?? 'unknown',
    [ATTR_SERVICE_VERSION]: process.env.SERVICE_VERSION   ?? '0.0.0',
    'deployment.environment': process.env.NODE_ENV ?? 'development',
  }),
  sampler: isProd
    ? new ParentBasedSampler({ root: new TraceIdRatioBasedSampler(0.1) })
    : undefined,                                        // default = AlwaysOn in dev
  traceExporter: new OTLPTraceExporter({
    url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT ?? 'http://otel-collector:4317',
  }),
  metricReader: new PeriodicExportingMetricReader({
    exporter: new OTLPMetricExporter({
      url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT ?? 'http://otel-collector:4317',
    }),
    exportIntervalMillis: 30_000,
  }),
  instrumentations: [
    getNodeAutoInstrumentations({
      '@opentelemetry/instrumentation-http': {
        ignoreIncomingRequestHook: (req) => req.url === '/health' || req.url === '/metrics',
      },
      '@opentelemetry/instrumentation-fs': { enabled: false },   // fs is noisy; opt-in only
    }),
    new PinoInstrumentation(),
  ],
});

sdk.start();

process.on('SIGTERM', () => { sdk.shutdown().finally(() => process.exit(0)); });
```

### Wire it before app code loads

This is the single biggest gotcha in Node OTel: instrumentations patch modules **at require time**. If your app requires `express` before `otel.ts` runs, the patches don't apply.

Two ways to fix it:

```jsonc
// package.json
"scripts": {
  "start": "node --require ./dist/otel.js dist/main.js"
}
```

Or import otel as the very first line of `src/main.ts`:

```typescript
import './otel';                  // MUST be first
import { NestFactory } from '@nestjs/core';
```

The `--require` flag is the safer default for production — it removes the risk of someone reordering imports.

### Custom spans

```typescript
import { trace, SpanStatusCode, SpanKind } from '@opentelemetry/api';

const tracer = trace.getTracer('app.orders', '1.0.0');

export async function processOrder(orderId: string, tenantId: string): Promise<void> {
  await tracer.startActiveSpan('order.process', { kind: SpanKind.INTERNAL }, async (span) => {
    span.setAttribute('order.id', orderId);
    span.setAttribute('tenant.id', tenantId);
    try {
      await doWork();
      span.setStatus({ code: SpanStatusCode.OK });
    } catch (err) {
      span.recordException(err as Error);
      span.setStatus({ code: SpanStatusCode.ERROR, message: (err as Error).message });
      throw err;
    } finally {
      span.end();
    }
  });
}
```

`startActiveSpan` makes the new span the current one so any auto-instrumented call inside `doWork()` becomes a child span. Always end the span (the callback flavor handles this for you on the success path; the manual flavor needs `finally`).

### Custom metrics

```typescript
import { metrics } from '@opentelemetry/api';

const meter = metrics.getMeter('app.orders', '1.0.0');

export const ordersCreated = meter.createCounter('orders.created', {
  description: 'Orders created',
  unit: '{order}',
});

export const processingDuration = meter.createHistogram('orders.processing.duration', {
  description: 'Order processing duration',
  unit: 's',
});

export const ordersInFlight = meter.createUpDownCounter('orders.in_flight', {
  description: 'Orders being processed right now',
  unit: '{order}',
});

// Usage
ordersCreated.add(1, { 'tenant.id': tenantId });

const start = performance.now();
try {
  await processOrder(id, tenantId);
} finally {
  processingDuration.record((performance.now() - start) / 1000, { 'tenant.id': tenantId });
}
```

### Log correlation

`@opentelemetry/instrumentation-pino` is already registered in the SDK bootstrap. Pino logs emitted inside an active span gain `trace_id` and `span_id` fields automatically. See `observability/structured-logging-node` for the matching log config.

## Sampling

- Dev: SDK default (AlwaysOn)
- Prod: `ParentBased(TraceIdRatioBased(0.1))` — 10% head-based sampling, always honor parent decision
- Tail sampling (errors + slow + N% baseline) at the Collector, not in the app

## Cardinality

- Span attributes can be high-cardinality (`order.id`, `user.id`) — spans are sampled
- Metric attributes must be **bounded** — never put `order.id` or `request.id` on a metric
- HTTP route normalization: confirm the framework reports `http.route` as `/orders/:id` (not the substituted URL); Fastify and Express auto-instrumentations do this; raw `http` module does not

## Propagation

W3C `traceparent` and `baggage` by default. The HTTP auto-instrumentation injects on outbound `fetch` / `http.request`. For queues / Kafka:

```typescript
import { context, propagation, trace } from '@opentelemetry/api';

const carrier: Record<string, string> = {};
propagation.inject(context.active(), carrier);
// attach `carrier` to outgoing message headers
```

On the consumer side:

```typescript
const parentCtx = propagation.extract(context.active(), msgHeaders);
context.with(parentCtx, () => {
  // any spans here are children of the producer's span
});
```

## Rules

- OTel SDK starts **before** any framework code is required — use `node --require` in production, or put `import './otel'` as the literal first line in dev
- One tracer / meter per logical subsystem, named `app.<area>`
- Span names are operation names (`order.process`), not values
- Metric names are `lowercase.dot.case`
- Always end spans (use the callback `startActiveSpan` form when possible)
- Set `SpanStatusCode.ERROR` + `recordException` on the error path
- Exclude health / metrics / static asset routes from server spans
- Resource attributes from env vars (`OTEL_SERVICE_NAME`, `SERVICE_VERSION`, `NODE_ENV`) — never hardcoded
- Production sampling at 10%; tune per env
- Metric attributes have bounded cardinality
- Shutdown the SDK on `SIGTERM` so the final batch flushes

## What NOT to do

- No imports of app modules **before** the SDK starts — silently breaks all auto-instrumentation
- No `console.log` for "tracing" — that's logging, not tracing
- No span per single function call — instrument **operations** (HTTP request, DB call, message handler)
- No `order.id` / `user.id` / `request.id` as a metric attribute
- No exporter pointing directly at Tempo — go through a Collector
- No `AlwaysOnSampler` in production
- No multiple `NodeSDK` instances per process
- No `instrumentation-fs` enabled in production (extremely noisy spans)
- No mixing OTel and a vendor APM agent that monkey-patches the same modules — they fight
- No span names with embedded values

## Generation steps

1. Confirm service identity, framework, Collector endpoint, and sampling with the user.
2. Install the package set; create `src/otel.ts` from the template.
3. Wire it via `node --require` in `package.json` start scripts and the Dockerfile.
4. Add `instrumentation-pino` and confirm `observability/structured-logging-node` is in place.
5. Add 3-5 custom spans where domain logic lives (worker job, message handler, complex orchestration).
6. Add the counter / histogram / up-down-counter trio for the service's core domain object.
7. Local smoke with docker-compose (Collector + Tempo + Prometheus + Grafana); hit endpoints, confirm spans, metrics, and log-trace correlation.

## Handoffs

- Log shape and sinks → `observability/structured-logging-node`
- LogQL / PromQL query patterns → `observability/logql-promql`
- Dashboard layout → `observability/grafana-dashboards`
- .NET equivalent → `observability/opentelemetry-dotnet`
- Java equivalent → `observability/opentelemetry-java`
