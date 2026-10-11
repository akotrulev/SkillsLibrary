---
name: opentelemetry
description: Use when instrumenting a .NET service (10 primary, 8/9) with OpenTelemetry — traces, metrics, log correlation — exporting OTLP to a Collector. Triggers: "instrument this with OTel", "add traces / metrics", "wire OTLP exporter", "add a custom span / counter / histogram". Do NOT use for Java/Node (their siblings) or log shaping (`structured-logging-dotnet`).
---

# Observability — OpenTelemetry (.NET 10 primary / 8-9 supported)

Instruments a .NET service with OpenTelemetry: traces via `Activity` / `System.Diagnostics.DiagnosticSource`, metrics via `System.Diagnostics.Metrics.Meter`, and log correlation via Serilog's `Enrich.WithSpan()`. Exports OTLP/gRPC to a local **OpenTelemetry Collector**, which forwards to Tempo (traces), Prometheus (metrics), and Loki (logs).

## Version detection

First act on an existing project: read the `TargetFramework` from the `.csproj` and key every recipe below to it. **.NET 10 is primary; 8 and 9 are supported.** Never apply a net10/net9-only API to a down-level project, and never flag a down-level project for lacking one. The one version-gated call in this skill is exception recording — use the portable `RecordException` extension (works on all TFMs) rather than `Activity.AddException` (net9+ native); see the Rules section.

## Stack

- **.NET (10 primary, 8/9 supported)**
- `OpenTelemetry.Extensions.Hosting`, `OpenTelemetry.Exporter.OpenTelemetryProtocol`
- Instrumentation libraries: `OpenTelemetry.Instrumentation.AspNetCore`, `Http`, `EntityFrameworkCore` (community), `SqlClient`, `StackExchangeRedis`
- Resource attributes follow **OTel semantic conventions** (`service.name`, `service.version`, `deployment.environment`)
- Sampler default: `ParentBased(TraceIdRatioBased)` — head-based sampling at the edge, tail-based at the Collector if needed

## When to use

- New service needs OTel from day one
- Existing service has ad-hoc tracing/metrics and needs OTel as the single pipeline
- Adding a custom span / counter / histogram to existing code
- Wiring OTLP export to a Collector (or directly to Tempo/Prometheus for dev)
- Diagnosing why a span isn't showing up in Tempo

## When NOT to use

- Java service → `observability/opentelemetry-java`
- Node service → `observability/opentelemetry-node`
- Log shape / sinks → `observability/structured-logging-dotnet`
- Dashboards / queries → `observability/dashboards` + `observability/queries`

## Inputs needed

1. **Service name + version + environment** — these become the OTel resource attributes
2. **Collector endpoint** — typically `http://otel-collector:4317` in cluster; configurable per env
3. **Sampling strategy** — `AlwaysOn` for dev, `TraceIdRatioBased(0.1)` for prod, head-based with tail at Collector for high-cardinality
4. **Instrumentations needed** — ASP.NET Core (always), HttpClient (always), EF Core / SqlClient (if used), Redis (if used)
5. **Custom domain spans** — operations the auto-instrumentation won't capture (background workers, message handlers, in-process pipelines)

## Setup

### Packages

```bash
dotnet add package OpenTelemetry.Extensions.Hosting
dotnet add package OpenTelemetry.Exporter.OpenTelemetryProtocol
dotnet add package OpenTelemetry.Instrumentation.AspNetCore
dotnet add package OpenTelemetry.Instrumentation.Http
dotnet add package OpenTelemetry.Instrumentation.SqlClient
dotnet add package OpenTelemetry.Instrumentation.StackExchangeRedis
dotnet add package OpenTelemetry.Instrumentation.EntityFrameworkCore --prerelease
```

### Program.cs

```csharp
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using OpenTelemetry.Metrics;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r
        .AddService(
            serviceName:    builder.Configuration["Service:Name"]!,
            serviceVersion: builder.Configuration["Service:Version"]!)
        .AddAttributes(new KeyValuePair<string, object>[]
        {
            new("deployment.environment", builder.Environment.EnvironmentName)
        }))
    .WithTracing(t => t
        .SetSampler(builder.Environment.IsProduction()
            ? new ParentBasedSampler(new TraceIdRatioBasedSampler(0.1))
            : new AlwaysOnSampler())
        .AddAspNetCoreInstrumentation(o =>
        {
            o.RecordException = true;
            o.Filter = ctx => !ctx.Request.Path.StartsWithSegments("/health");
        })
        .AddHttpClientInstrumentation(o => o.RecordException = true)
        .AddSqlClientInstrumentation(o =>
        {
            o.SetDbStatementForText = true;          // record parameterised SQL
            o.RecordException = true;
        })
        .AddRedisInstrumentation()
        .AddSource("App.*")                          // every custom ActivitySource in the app
        .AddOtlpExporter(o =>
        {
            o.Endpoint = new Uri(builder.Configuration["Otel:Endpoint"]!);
            o.Protocol = OtlpExportProtocol.Grpc;
        }))
    .WithMetrics(m => m
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddRuntimeInstrumentation()                 // GC, threadpool, exceptions
        .AddProcessInstrumentation()
        .AddMeter("App.*")
        .AddOtlpExporter(o =>
        {
            o.Endpoint = new Uri(builder.Configuration["Otel:Endpoint"]!);
            o.Protocol = OtlpExportProtocol.Grpc;
        }));
```

`AddSource("App.*")` and `AddMeter("App.*")` use wildcards so every `ActivitySource`/`Meter` named with the `App.` prefix is auto-included. Use one source per logical subsystem (`App.Orders`, `App.Payments`).

### Custom spans

```csharp
public sealed class OrderProcessor
{
    private static readonly ActivitySource Source = new("App.Orders", "1.0.0");

    public async Task ProcessAsync(Guid orderId, CancellationToken ct)
    {
        using var activity = Source.StartActivity("order.process", ActivityKind.Internal);
        activity?.SetTag("order.id", orderId);
        activity?.SetTag("tenant.id", _tenantContext.TenantId);

        try
        {
            await DoWorkAsync(ct);
            activity?.SetStatus(ActivityStatusCode.Ok);
        }
        catch (Exception ex)
        {
            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);
            activity?.RecordException(ex);
            throw;
        }
    }
}
```

`ActivityKind.Internal` for in-process; `Server` / `Client` are added by the auto-instrumentations. Tags use **dot.case** keys — matches OTel conventions and queries cleanly in Tempo.

### Custom metrics

```csharp
public sealed class OrderMetrics
{
    private static readonly Meter Meter = new("App.Orders", "1.0.0");

    public static readonly Counter<long> OrdersCreated =
        Meter.CreateCounter<long>("orders.created", unit: "{order}", description: "Orders created");

    public static readonly Histogram<double> ProcessingDurationSeconds =
        Meter.CreateHistogram<double>("orders.processing.duration", unit: "s", description: "Order processing duration");

    public static readonly UpDownCounter<long> OrdersInFlight =
        Meter.CreateUpDownCounter<long>("orders.in_flight", unit: "{order}");
}

// usage
OrderMetrics.OrdersCreated.Add(1, new KeyValuePair<string, object?>("tenant.id", tenantId));
```

Use `Counter` for monotonic counts, `Histogram` for durations, `UpDownCounter` for in-flight gauges. Naming is `lowercase.dot.case` per OTel — Prometheus exporter translates to `orders_created_total` automatically.

### Log correlation

Wire `Enrich.WithSpan()` into Serilog (see `observability/structured-logging-dotnet`). Every log line emitted inside an active span gets `TraceId` / `SpanId` fields, which Loki uses to link to the trace in Tempo.

## Sampling

- **Dev**: `AlwaysOnSampler` — see every span while iterating
- **Staging**: `TraceIdRatioBasedSampler(1.0)` then taper
- **Prod**: `ParentBasedSampler(TraceIdRatioBasedSampler(0.1))` is the safe default — keep 10% of new traces, always honor upstream sampling decisions. Use tail-based sampling at the Collector (sample by error / latency) when you want "all errors + 1% of OK".

Sampling decisions are made at trace start; sampled-out spans cost nearly nothing in the app. Tail-sampling lives in the Collector, not the app.

## Cardinality

The two metric pitfalls:

1. **High-cardinality attributes** (`order.id`, `user.id`) as metric labels — explodes the time-series count and crashes Prometheus. Use them on **spans**, never on metric counters.
2. **Span attributes that change per-call** for the same operation — fine. Spans are sampled, the storage cost is bounded.

Rule of thumb: metric attributes should have bounded cardinality (route, method, status, tenant for small tenant counts). Anything per-record belongs on a span.

## Propagation

The default `Propagators.DefaultTextMapPropagator` handles **W3C Trace Context** (`traceparent`) and **Baggage**. For services that talk to legacy Zipkin/B3 systems, register the B3 propagator additionally.

`HttpClient` auto-injects `traceparent` when instrumented. For message bus / queue work, inject manually:

```csharp
var ctx = Activity.Current?.Context;
var carrier = new Dictionary<string, string>();
Propagators.DefaultTextMapPropagator.Inject(new PropagationContext(ctx ?? default, Baggage.Current),
    carrier, (c, k, v) => c[k] = v);
// attach `carrier` to the outgoing message headers
```

## Rules

- One `ActivitySource` per logical subsystem, named `App.<Area>`; reuse it (`static readonly`), never create per-call
- One `Meter` per subsystem with the same naming pattern
- Span names are **operation names**, not user data: `order.process`, `payment.charge`, `user.fetch` — not `process_order_42`
- Metric names are `lowercase.dot.case`; use `{unit}` curly-brace notation per OTel spec
- Set `activity.SetStatus(...)` and `RecordException(...)` on the exception path (`Activity.AddException` is .NET 9+ only) — without it, error spans look successful
- Exclude `/health` / `/metrics` / `/swagger` from instrumentation via the `Filter` callback — they otherwise dominate sampling
- Resource attributes include `service.name`, `service.version`, `deployment.environment` — required for cross-service queries
- OTLP endpoint comes from configuration / env vars; never hardcoded
- Production sampling capped at 10% by default; raise per env if volume permits
- Custom metric attributes have bounded cardinality (≤ a few hundred values per attribute)

## What NOT to do

- No `Activity.Current` reads in business logic — use `ActivitySource.StartActivity()` to create new spans, never inspect the ambient one for control flow
- No per-record attribute on a counter (`order.id` as a metric tag) — that's a span
- No spans wrapping single field access — instrument **operations**, not function calls
- No raw `System.Console.WriteLine` for "tracing" — that's not what tracing means
- No exporter pointing directly at Tempo / Prometheus from the app — go through an OTel Collector so sampling, batching, and routing can change without app redeploy
- No `AlwaysOnSampler` in production
- No span names containing values (`order.process.42`) — that's what tags are for
- No `Activity.Current.AddBaggage` for everything — baggage propagates to every downstream service and is expensive; use sparingly for cross-cutting fields like `tenant.id`
- No mixing `System.Diagnostics.Tracing` (`EventSource`) and OTel — pick one
- No instrumentation library at a version mismatched with `OpenTelemetry` core — version-pin all OTel packages together

## Generation steps

1. Confirm service name/version/env, Collector endpoint, sampling strategy, and which instrumentations are needed.
2. Install the package set above; pin all OTel packages to the same version.
3. Add the `AddOpenTelemetry().WithTracing(...).WithMetrics(...)` block to `Program.cs`.
4. Add Serilog `Enrich.WithSpan()` if structured logging is in scope (see `observability/structured-logging-dotnet`).
5. Create one `ActivitySource` + one `Meter` per business subsystem; wire instrumentation into the code that should emit spans/metrics.
6. Configure the Collector (separate concern) to receive OTLP and route to Tempo / Prometheus / Loki.
7. Smoke locally with a docker-compose stack (Collector + Tempo + Prometheus + Grafana). Confirm `traceparent` rides outbound HTTP, spans appear in Tempo, metrics appear in Prometheus.

## Handoffs

- Log shape and sinks → `observability/structured-logging-dotnet`
- LogQL / PromQL query patterns → `observability/queries`
- Dashboard layout → `observability/dashboards`
- Java equivalent → `observability/opentelemetry-java`
- Node equivalent → `observability/opentelemetry-node`
