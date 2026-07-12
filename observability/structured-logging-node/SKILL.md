---
name: observability-structured-logging-node
description: Use when the user asks to set up or refactor logging in a Node 20 + TypeScript service — pino (preferred) or winston, JSON output, correlation IDs via AsyncLocalStorage, shipping to Loki / Datadog. Triggers: "set up structured logging in Node", "use pino in NestJS / Express", "ship logs to Loki", "add a request ID middleware", "redact secrets from logs". Do NOT use for .NET (use `observability/serilog-structured-logging`) or Java (use `observability/structured-logging-java`), or for tracing/metrics (use `observability/opentelemetry-node`).
---

# Observability — Structured Logging (Node 20 / TypeScript)

Sets up **pino** as the default logging stack for Node 20 + TypeScript services (NestJS or Express). Logs are JSON to stdout, enriched with `requestId`, `traceId`, `spanId` via `AsyncLocalStorage`, with built-in `redact` for secrets. Winston is documented as a fallback when an ecosystem dependency forces it.

## Stack

- **Node 20** + TypeScript (strict mode)
- **pino** — chosen for speed (10–50× faster than winston in benchmarks), built-in `redact`, child-logger composition, first-class JSON
- **`pino-http`** for Express; **`nestjs-pino`** for NestJS
- **`@opentelemetry/instrumentation-pino`** to inject trace context into every log
- **`pino-pretty`** in `NODE_ENV=development` for human-friendly local console output (never enabled in prod)
- Shipping: stdout JSON → container runtime → Promtail / Vector / Fluent Bit → Loki

Winston is acceptable when an upstream framework already configures it (NestJS without `nestjs-pino`); the rules below port over with different syntax.

## When to use

- New Node service needs logging
- Replacing `console.log` / unstructured prints with JSON logs
- Adding request-scoped correlation IDs without threading them through every function
- Wiring OTel trace context into log lines
- Masking PII / secrets in log output

## When NOT to use

- .NET service → `observability/serilog-structured-logging`
- Java / Spring Boot service → `observability/structured-logging-java`
- Distributed tracing or metrics → `observability/opentelemetry-node`
- LogQL query authoring → `observability/logql-promql`
- Dashboard layout → `observability/grafana-dashboards`

## Inputs needed

1. **Framework** — NestJS, Express, Fastify, bare Node
2. **Target environment(s)** + sink per env (stdout JSON everywhere; pretty console only in `development`)
3. **Service name + version** — go into base fields
4. **PII / secrets** to redact (auth tokens, cookies, card numbers, password fields)
5. **OTel in scope?** — if so, install the pino instrumentation so trace ids ride every log

## Setup

### Packages

```bash
pnpm add pino pino-http
pnpm add -D pino-pretty
# OTel correlation
pnpm add @opentelemetry/instrumentation-pino
# NestJS only
pnpm add nestjs-pino
```

### Logger module — `src/logger/logger.ts`

```typescript
import pino, { Logger } from 'pino';

const isDev = process.env.NODE_ENV === 'development';

export const logger: Logger = pino({
  level: process.env.LOG_LEVEL ?? (isDev ? 'debug' : 'info'),
  base: {
    'service.name':    process.env.SERVICE_NAME    ?? 'unknown',
    'service.version': process.env.SERVICE_VERSION ?? '0.0.0',
    environment:       process.env.NODE_ENV        ?? 'development',
  },
  timestamp: pino.stdTimeFunctions.isoTime,
  redact: {
    paths: [
      'req.headers.authorization',
      'req.headers.cookie',
      '*.password',
      '*.token',
      '*.cardNumber',
      '*.ssn',
    ],
    censor: '***REDACTED***',
  },
  transport: isDev ? { target: 'pino-pretty', options: { colorize: true, singleLine: true } } : undefined,
});
```

`redact.paths` is non-negotiable in prod — without it any developer mistake leaks secrets to the log pipeline.

### Express + `pino-http`

```typescript
import express from 'express';
import pinoHttp from 'pino-http';
import { randomUUID } from 'crypto';
import { logger } from './logger/logger';

const app = express();

app.use(pinoHttp({
  logger,
  genReqId: (req, res) => {
    const id = (req.headers['x-request-id'] as string) ?? randomUUID();
    res.setHeader('x-request-id', id);
    return id;
  },
  customLogLevel: (req, res, err) => {
    if (err || res.statusCode >= 500) return 'error';
    if (res.statusCode >= 400) return 'warn';
    return 'info';
  },
  serializers: {
    req: (req) => ({ id: req.id, method: req.method, url: req.url }),
    res: (res) => ({ statusCode: res.statusCode }),
  },
}));
```

`req.log` is now a child logger with `reqId` attached on every call. Use it inside route handlers: `req.log.info({ orderId }, 'order created')`.

### NestJS + `nestjs-pino`

```typescript
// main.ts
import { NestFactory } from '@nestjs/core';
import { Logger } from 'nestjs-pino';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule, { bufferLogs: true });
  app.useLogger(app.get(Logger));
  await app.listen(3000);
}
bootstrap();
```

```typescript
// app.module.ts
import { LoggerModule } from 'nestjs-pino';

@Module({
  imports: [
    LoggerModule.forRoot({
      pinoHttp: {
        level: process.env.LOG_LEVEL ?? 'info',
        redact: ['req.headers.authorization', 'req.headers.cookie', '*.password'],
        genReqId: (req, res) => {
          const id = (req.headers['x-request-id'] as string) ?? randomUUID();
          res.setHeader('x-request-id', id);
          return id;
        },
      },
    }),
  ],
})
export class AppModule {}
```

Inject `Logger` into services: `constructor(@InjectPinoLogger(MyService.name) private readonly log: PinoLogger) {}`.

### OTel correlation

```typescript
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { PinoInstrumentation } from '@opentelemetry/instrumentation-pino';

registerInstrumentations({
  instrumentations: [new PinoInstrumentation()],
});
```

With this registered, every log emitted inside an active span gets `trace_id` and `span_id` injected automatically.

## Writing logs

### First argument is the object, second is the message

```typescript
// ✅ correct — fields are structured
logger.info({ orderId, customerId, totalMinor, currency }, 'order created');

// ❌ wrong — values vanish into the message string
logger.info(`order ${orderId} created for ${customerId}`);
```

This is the inverse of most logging libraries — for pino, the **object comes first**, message second. Once you internalize it, it's strictly better: every field is queryable.

### Use child loggers for cross-cutting context

```typescript
const reqLog = logger.child({ tenantId, requestId });
reqLog.info({ orderId }, 'processing order');
reqLog.info({ orderId }, 'order paid');
// both logs carry tenantId + requestId
```

`pino-http` and `nestjs-pino` already produce a child logger per request (`req.log`). Use it instead of the global one.

### Log errors with the `err` key

```typescript
try {
  await processOrder(id);
} catch (err) {
  logger.error({ err, orderId: id }, 'order processing failed');
}
```

pino's `errorSerializer` (default) renders `err.message`, `err.stack`, `err.type` as flat fields. Don't `err.toString()` or `err.stack` manually — the serializer is better.

## AsyncLocalStorage for request-scoped context

When `req.log` isn't reachable (deep in a service called from a CLI / job / worker), use `AsyncLocalStorage` to carry request context:

```typescript
import { AsyncLocalStorage } from 'async_hooks';
import { Logger } from 'pino';

export const logCtx = new AsyncLocalStorage<{ logger: Logger }>();

// In an Express middleware or NestJS interceptor:
logCtx.run({ logger: req.log }, () => next());

// Anywhere downstream:
export function getLogger(): Logger {
  return logCtx.getStore()?.logger ?? logger;
}
```

This removes the need to thread `logger` through every function signature.

## Levels & cardinality

| Level | When |
|---|---|
| `trace` | Never in production |
| `debug` | Per-request detail; off in staging/prod by default |
| `info` | Domain events worth keeping |
| `warn` | Recoverable issues, retries, fallbacks |
| `error` | Operation failed visibly |
| `fatal` | Process can't continue |

Loki labels are categorical (`service`, `environment`, `level`). `orderId`, `requestId`, `userId` are **fields**, not labels.

## Sensitive data

- `redact.paths` covers the common cases via dot-paths and wildcards
- For values that can be anywhere in the payload, write a serializer that walks the object and masks
- Better: don't pass the raw DTO to the logger — project to a logging-safe shape first

## Rules

- pino is the only logger in the process (or winston, if forced — pick one)
- `console.log` is banned in production code; flag in lint (`no-console: ['error', { allow: [] }]`)
- JSON output in every env except `development`
- `service.name`, `service.version`, `environment` as base fields on every log
- `redact.paths` includes at minimum: `req.headers.authorization`, `req.headers.cookie`, `*.password`, `*.token`
- `requestId` (or `reqId` — pick one) populated by middleware before any route handler runs
- `@opentelemetry/instrumentation-pino` registered if OTel is in the project
- Child loggers for request scope (`req.log`); `logger.child(...)` for any other cross-cutting scope
- Object-first, message-second call convention everywhere
- Errors logged as `{ err }` (or `{ err, ...context }`) — let the serializer format

## What NOT to do

- No `console.log` / `console.error` in route handlers or services
- No string interpolation in log calls — `logger.info({...}, 'message')` only
- No `JSON.stringify(payload)` inside a log call — pass the object, let pino serialize
- No `pino-pretty` in production — it's slow and not parseable
- No per-request Loki labels — labels are categorical, fields are dimensional
- No raw request body / response body logging on auth, payment, or user-data endpoints
- No `err.stack` manually — pass `err` and let the serializer
- No multiple logger instances per file — import one, child it as needed
- No `LOG_LEVEL=trace` in any environment that ships to Loki — egress costs
- No mixing pino and winston in the same process — pick one path and remove the other

## Generation steps

1. Confirm framework (NestJS / Express / Fastify / bare), environments, sink targets, service name/version, and PII rules with the user.
2. Install pino + the framework adapter (`pino-http` or `nestjs-pino`) + `pino-pretty` (dev only) + `@opentelemetry/instrumentation-pino` (if OTel is in scope).
3. Create `src/logger/logger.ts` from the template above; tune `redact.paths` for the project.
4. Wire the HTTP middleware so every request has a `requestId` and a child logger.
5. If OTel is registered, install pino instrumentation so `trace_id` / `span_id` ride every log.
6. Lint-ban `console.log` and sweep the codebase to replace existing prints.
7. Smoke locally — hit a few endpoints, confirm JSON includes `requestId`, `trace_id`, `service.name`.

## Handoffs

- Distributed tracing + metrics → `observability/opentelemetry-node`
- LogQL queries against Loki → `observability/logql-promql`
- Dashboard layout → `observability/grafana-dashboards`
- .NET equivalent → `observability/serilog-structured-logging`
- Java equivalent → `observability/structured-logging-java`
