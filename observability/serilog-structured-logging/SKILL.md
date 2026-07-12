---
name: observability-serilog-structured-logging
description: Use when the user asks to set up or refactor logging in a .NET 8 service using Serilog — message templates, enrichers, sinks to console / Loki / Seq / Application Insights, scope / correlation, sensitive-data masking. Triggers: "set up Serilog", "configure structured logging in .NET", "ship logs to Loki", "add correlation IDs", "this log line is wrong". Do NOT use for Java (use `observability/structured-logging-java`) or Node (use `observability/structured-logging-node`), or for tracing/metrics (use `observability/opentelemetry-dotnet`).
---

# Observability — Serilog Structured Logging (.NET 8)

Sets up Serilog as the **only** logging stack in a .NET 8 service. Logs are JSON, written via message templates (never `$"interpolated"`), enriched with correlation/trace IDs from the active OpenTelemetry activity, and shipped to Loki for prod / Seq for local dev.

## Stack

- **.NET 8**
- **Serilog** (`Serilog.AspNetCore`) — replaces `Microsoft.Extensions.Logging` providers
- Enrichers: `Serilog.Enrichers.Environment`, `Serilog.Enrichers.Thread`, `Serilog.Enrichers.Span` (OTel activity → log)
- Sinks: `Serilog.Sinks.Console` (always, JSON formatted), `Serilog.Sinks.Grafana.Loki` (prod), `Serilog.Sinks.Seq` (local dev)
- **Schema**: `Microsoft.Extensions.Logging.ILogger<T>` everywhere in app code — Serilog is wired up underneath; the static `Log` class is for the host only
- Levels per env: dev `Debug`, staging `Information`, prod `Information` with `Warning` overrides for chatty namespaces

## When to use

- New .NET 8 service needs logging
- Logs are unstructured (`Console.WriteLine`, `_logger.LogInformation($"...")`) and need to become structured
- Adding correlation IDs / trace propagation to logs
- Pointing logs at Loki / Seq / Application Insights
- Masking sensitive data (PII, tokens) in log output

## When NOT to use

- Java service → `observability/structured-logging-java`
- Node / TypeScript service → `observability/structured-logging-node`
- Distributed tracing or metrics (different concern) → `observability/opentelemetry-dotnet`
- LogQL/PromQL query authoring → `observability/logql-promql`
- Dashboard layout → `observability/grafana-dashboards`

## Inputs needed

1. **Target environment(s)** — local, dev, staging, prod, and the sink per env
2. **Loki / Seq / App Insights** endpoint + auth (env-injected, never in code)
3. **Service name + version** — drives `service.name` / `service.version` labels
4. **PII / sensitive fields** that must never appear in logs
5. **Tracing in scope?** — if OpenTelemetry is configured, enrich logs with `TraceId` / `SpanId`

## Setup

### Packages

```bash
dotnet add package Serilog.AspNetCore
dotnet add package Serilog.Enrichers.Environment
dotnet add package Serilog.Enrichers.Span
dotnet add package Serilog.Sinks.Grafana.Loki
dotnet add package Serilog.Sinks.Seq
dotnet add package Serilog.Formatting.Compact
```

### Program.cs

```csharp
using Serilog;
using Serilog.Formatting.Compact;

var builder = WebApplication.CreateBuilder(args);

builder.Host.UseSerilog((ctx, sp, cfg) => cfg
    .ReadFrom.Configuration(ctx.Configuration)
    .ReadFrom.Services(sp)
    .Enrich.FromLogContext()
    .Enrich.WithEnvironmentName()
    .Enrich.WithMachineName()
    .Enrich.WithSpan()
    .Enrich.WithProperty("service.name", ctx.Configuration["Service:Name"]!)
    .Enrich.WithProperty("service.version", ctx.Configuration["Service:Version"]!)
    .WriteTo.Console(new CompactJsonFormatter())
    .WriteTo.Conditional(
        _ => ctx.HostingEnvironment.IsProduction(),
        wt => wt.GrafanaLoki(
            ctx.Configuration["Loki:Url"]!,
            labels: new[] {
                new Serilog.Sinks.Grafana.Loki.LokiLabel { Key = "service",     Value = ctx.Configuration["Service:Name"]! },
                new Serilog.Sinks.Grafana.Loki.LokiLabel { Key = "environment", Value = ctx.HostingEnvironment.EnvironmentName }
            }))
    .WriteTo.Conditional(
        _ => ctx.HostingEnvironment.IsDevelopment(),
        wt => wt.Seq(ctx.Configuration["Seq:Url"]!)));

var app = builder.Build();
app.UseSerilogRequestLogging();   // structured access log
```

`CompactJsonFormatter` produces single-line JSON (Loki-friendly). `UseSerilogRequestLogging` emits one structured log per HTTP request with method, path, status, elapsed.

### appsettings.json

```json
{
  "Serilog": {
    "MinimumLevel": {
      "Default": "Information",
      "Override": {
        "Microsoft": "Warning",
        "Microsoft.AspNetCore.Hosting": "Warning",
        "Microsoft.AspNetCore.Mvc": "Warning",
        "Microsoft.AspNetCore.Routing": "Warning",
        "System.Net.Http.HttpClient": "Warning"
      }
    }
  }
}
```

`Override` is mandatory — without it, ASP.NET Core's per-request infrastructure logs flood the pipeline.

## Writing logs

### Use message templates, not interpolation

```csharp
// ✅ correct — properties land as structured fields
_logger.LogInformation("Order {OrderId} created for customer {CustomerId} totalling {TotalMinor} {Currency}",
    order.Id, order.CustomerId, order.TotalMinor, order.Currency);

// ❌ wrong — flattens to one opaque string, can't be filtered or aggregated
_logger.LogInformation($"Order {order.Id} created for customer {order.CustomerId} totalling {order.TotalMinor} {order.Currency}");
```

This is the single most important rule. A log line that uses `$"..."` is a log line you can't filter on in Loki.

### PascalCase the placeholders

`{OrderId}`, `{CustomerId}` — the property name becomes the JSON field. Consistent casing across the codebase means consistent LogQL queries.

### Scopes for cross-cutting context

```csharp
using (_logger.BeginScope(new Dictionary<string, object> { ["TenantId"] = tenantId, ["RequestId"] = requestId }))
{
    // every log inside this block has TenantId + RequestId attached
}
```

### Log exceptions, don't stringify them

```csharp
// ✅ correct — the exception is structured (Type, Message, StackTrace as fields)
_logger.LogError(ex, "Failed to process order {OrderId}", order.Id);

// ❌ wrong — stack trace collapses into one field
_logger.LogError("Failed to process order {OrderId}: {Error}", order.Id, ex.ToString());
```

## Correlation with traces

With `Enrich.WithSpan()` and OpenTelemetry configured (`observability/opentelemetry-dotnet`), every log emitted inside an active span gets `TraceId` and `SpanId` fields. Loki + Tempo wire these to "Jump to trace" in Grafana — non-negotiable for prod debugging.

```csharp
// In a Controller / handler, the trace context is already active
_logger.LogInformation("Processing payment for {OrderId}", id);
// Emitted JSON includes: "TraceId":"a1b2c3...", "SpanId":"d4e5f6..."
```

## Levels & cardinality

| Level | When |
|---|---|
| `Verbose` / `Trace` | Never in production. Dev-only diagnostic noise. |
| `Debug` | Per-request internal detail; off in staging/prod by default |
| `Information` | Domain events worth keeping (order created, user signed in, job ran) |
| `Warning` | Recoverable: retry succeeded, fallback used, contract drift detected |
| `Error` | Operation failed in a way the user/caller will notice |
| `Fatal` | Process can't continue (rare; usually only at startup) |

Cardinality rule: **Loki labels are not log fields.** Labels are coarse (service, environment, level). High-cardinality data (`OrderId`, `UserId`) belongs in the JSON body, not as a Loki label. A label per request id will tank Loki.

## Sensitive data

- Never log full request/response bodies on auth, payment, or user-data endpoints
- Mask PII fields explicitly via a destructuring policy:

```csharp
.Destructure.ByTransforming<User>(u => new { u.Id, u.Email /* hashed elsewhere */ })
.Destructure.ToMaximumDepth(3)
.Destructure.ToMaximumStringLength(2000)
```

- Add a `MaskPiiEnricher` for tokens / card numbers / IDs that match a regex
- Audit at PR review — every new `LogInformation` that takes a user object goes through the reviewer

## Rules

- Serilog is the **only** logging stack — remove `Microsoft.Extensions.Logging.Console` from `Program.cs`
- Use `ILogger<T>` everywhere in app code; the static `Log` is only for the host setup
- Message templates only — never string interpolation in `Log*` calls
- PascalCase placeholders — `{OrderId}`, not `{orderId}` or `{order_id}`
- JSON output everywhere (`CompactJsonFormatter`) — human-readable console only in `Development`
- Loki labels are low-cardinality (`service`, `environment`, `level`). Everything else is a structured field.
- `UseSerilogRequestLogging()` is wired up — but configure `GetLevel` to drop noisy 200s to `Debug` if traffic is high
- Configuration via `appsettings.json` + env vars; never hardcode endpoints or tokens in `Program.cs`
- Override chatty namespaces (`Microsoft.*`, `System.Net.Http.HttpClient`) to `Warning`
- Exceptions go through the `Exception` parameter, never `.ToString()` into the message

## What NOT to do

- No `Console.WriteLine` / `Debug.WriteLine` in production code paths
- No `$"interpolated"` strings in `Log*` calls
- No `.ToString()`-ing an exception into the message — pass the exception as the first arg
- No logging the entire request DTO on every endpoint — pick the fields that matter
- No `LogInformation` on tight loops (per-item logs in a batch processor) — log a single summary
- No per-request Loki labels (`order_id`, `user_id` as labels) — labels are categorical, fields are dimensional
- No `Verbose` / `Debug` in production minimum level
- No sink writes inside a transaction or hot loop — Serilog batches but a misconfigured sink still costs
- No secret material in logs (tokens, passwords, raw card numbers) — mask via enricher or refuse to log
- No two logging stacks side by side (`ILogger` + `Serilog.Log.*`) — pick one path and remove the other

## Generation steps

1. Confirm environments, sink targets, service name/version, and PII rules with the user.
2. Install the package set above.
3. Replace any existing `builder.Logging.*` calls with `builder.Host.UseSerilog(...)`.
4. Add `appsettings.json` `Serilog:MinimumLevel` block with `Override` for `Microsoft.*` and `System.Net.Http.HttpClient`.
5. Wire `UseSerilogRequestLogging()`; tune `GetLevel` to demote 2xx to `Debug` if the service is high-traffic.
6. If OTel is configured, add `Enrich.WithSpan()`; otherwise add it later when adding `observability/opentelemetry-dotnet`.
7. Sweep the codebase for `$"..."` inside `Log*` calls; replace with message templates.
8. Smoke locally — run the service, hit a few endpoints, confirm Seq shows structured fields with `TraceId`/`SpanId`.

## Handoffs

- Distributed tracing + metrics → `observability/opentelemetry-dotnet`
- LogQL queries against Loki → `observability/logql-promql`
- Dashboard layout → `observability/grafana-dashboards`
- Java equivalent → `observability/structured-logging-java`
- Node equivalent → `observability/structured-logging-node`
