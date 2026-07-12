---
name: observability-opentelemetry-java
description: Use when the user asks to instrument a Java 21 / Spring Boot 3 service with OpenTelemetry — traces, metrics, log correlation — using the Java auto-instrumentation agent or the SDK, exporting OTLP to a Collector. Triggers: "instrument with OTel", "add Java auto-instrumentation agent", "add a custom @WithSpan", "Micrometer to OTel", "wire OTLP exporter". Do NOT use for .NET (use `observability/opentelemetry-dotnet`), Node (use `observability/opentelemetry-node`), or log shaping (use `observability/structured-logging-java`).
---

# Observability — OpenTelemetry (Java 21 / Spring Boot 3)

Instruments a Java 21 + Spring Boot 3 service with OpenTelemetry. Default is the **OpenTelemetry Java agent** for auto-instrumentation (zero code changes), plus the SDK for custom spans and metrics. Exports OTLP/gRPC to a local Collector that forwards to Tempo / Prometheus / Loki.

## Stack

- **Java 21 + Spring Boot 3.x**
- **OpenTelemetry Java agent** (`opentelemetry-javaagent.jar`) — recommended default; one JAR, no code changes for HTTP / JDBC / Kafka / Redis / Mongo / gRPC instrumentation
- **`io.opentelemetry:opentelemetry-api`** + **`opentelemetry-extension-annotations`** — for custom spans and `@WithSpan`
- **Micrometer + OpenTelemetry bridge** (`io.opentelemetry:opentelemetry-micrometer1-shim`) — Spring Boot's `MeterRegistry` flows through OTel
- Log correlation via the SLF4J/Logback bridge from `observability/structured-logging-java`
- Resource attributes follow OTel semantic conventions

## When to use

- New Spring Boot service needs OTel
- Existing service has Micrometer + Spring Cloud Sleuth; migrating to OTel
- Adding `@WithSpan` to a domain method
- Adding a custom `Counter` / `Histogram` / gauge
- Wiring the Java agent in a Dockerfile / Kubernetes manifest

## When NOT to use

- .NET service → `observability/opentelemetry-dotnet`
- Node service → `observability/opentelemetry-node`
- Log shape / sinks → `observability/structured-logging-java`
- Dashboards / queries → `observability/grafana-dashboards` + `observability/logql-promql`

## Inputs needed

1. **Service name + version + environment** — resource attributes
2. **Collector endpoint** (`http://otel-collector:4317`)
3. **Sampling strategy** — agent supports head-based `parentbased_traceidratio=0.1` plus tail at the Collector
4. **Auto-instrumentation vs SDK-only** — agent is default; SDK-only for short-lived processes / GraalVM native images
5. **Custom spans** — service methods that should be visible as spans

## Setup — Java agent (default)

The agent is a separate `-javaagent` JAR. App code only needs the annotation library.

### Dependencies (Gradle)

```groovy
dependencies {
    implementation 'io.opentelemetry.instrumentation:opentelemetry-instrumentation-annotations:2.7.0'
    // Micrometer bridge if Spring Boot's MeterRegistry is in use:
    implementation 'io.opentelemetry:opentelemetry-micrometer1-shim:1.40.0-alpha'
    // Spring Boot starter sets up Micrometer; OTel exporter is wired below
}
```

### Agent launch

Download once during image build:

```dockerfile
FROM eclipse-temurin:21-jre
ARG OTEL_AGENT_VERSION=2.7.0
ADD https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/download/v${OTEL_AGENT_VERSION}/opentelemetry-javaagent.jar /opt/otel/agent.jar

ENV JAVA_TOOL_OPTIONS="-javaagent:/opt/otel/agent.jar"
ENV OTEL_SERVICE_NAME=orders-api
ENV OTEL_RESOURCE_ATTRIBUTES="service.version=${VERSION},deployment.environment=${ENV}"
ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
ENV OTEL_EXPORTER_OTLP_PROTOCOL=grpc
ENV OTEL_TRACES_SAMPLER=parentbased_traceidratio
ENV OTEL_TRACES_SAMPLER_ARG=0.1
ENV OTEL_LOGS_EXPORTER=none                 # logs flow via stdout JSON → Loki (not via OTel)
ENV OTEL_METRICS_EXPORTER=otlp
ENV OTEL_PROPAGATORS=tracecontext,baggage
ENTRYPOINT ["java","-jar","/app/app.jar"]
```

That's the entire wiring — auto-instrumentation now covers Spring MVC, Spring WebFlux, RestTemplate, WebClient, JDBC (Postgres / MySQL / SQL Server), JPA, Mongo, Redis (Lettuce/Jedis), Kafka, gRPC, and ~80 more libraries.

### Custom spans with `@WithSpan`

```java
import io.opentelemetry.instrumentation.annotations.WithSpan;
import io.opentelemetry.instrumentation.annotations.SpanAttribute;

@Service
public class OrderProcessor {

    @WithSpan("order.process")
    public void process(@SpanAttribute("order.id") UUID orderId,
                        @SpanAttribute("tenant.id") String tenantId) {
        // span is started/ended around this call; attributes set automatically
    }
}
```

`@WithSpan` works only on Spring-managed beans (or any class proxied by the agent). For self-invocation, get the tracer directly:

```java
private static final Tracer tracer = GlobalOpenTelemetry.getTracer("App.Orders", "1.0.0");

Span span = tracer.spanBuilder("order.process").startSpan();
try (Scope ignored = span.makeCurrent()) {
    span.setAttribute("order.id", orderId.toString());
    // work
    span.setStatus(StatusCode.OK);
} catch (Exception e) {
    span.recordException(e);
    span.setStatus(StatusCode.ERROR, e.getMessage());
    throw e;
} finally {
    span.end();
}
```

### Custom metrics — Micrometer (recommended)

Spring Boot already exposes Micrometer's `MeterRegistry`. With the OTel bridge dependency added, Micrometer counters / timers flow into OTel and out via OTLP.

```java
@Service
public class OrderMetrics {
    private final Counter created;
    private final Timer processing;

    public OrderMetrics(MeterRegistry registry) {
        this.created    = Counter.builder("orders.created").register(registry);
        this.processing = Timer.builder("orders.processing.duration").register(registry);
    }

    public void onCreated() { created.increment(); }
    public <T> T time(Supplier<T> s) { return processing.record(s); }
}
```

The bridge applies OTel naming conventions automatically (`orders.created` → Prometheus `orders_created_total`).

### Log correlation

The `OpenTelemetryAppender` turbo-filter from `observability/structured-logging-java` injects `traceId` / `spanId` into MDC for every log emitted inside an active span. No additional wiring here.

## Sampling

Set via env vars on the agent:

- `OTEL_TRACES_SAMPLER=always_on` for dev
- `OTEL_TRACES_SAMPLER=parentbased_traceidratio` + `OTEL_TRACES_SAMPLER_ARG=0.1` for prod
- Tail-based sampling at the Collector for "all errors + 1%"

Never set `always_on` in production unless the service is extremely low-traffic.

## Cardinality

- Span attributes can carry per-record IDs (`order.id`, `user.id`) — span storage is sampled
- Metric attributes must have **bounded** cardinality. `tenant.id` is OK if there are tens; not if there are millions. `order.id` as a metric tag is **always wrong**.
- Spring MVC's `http.route` attribute is normalised (`/orders/{id}` not `/orders/42`) by the agent — keep it that way.

## Propagation

Default propagators: `tracecontext,baggage`. The agent injects `traceparent` into outbound HTTP automatically. For Kafka the agent injects headers automatically too. For custom RPC frameworks, use `Propagators.getDefaultTextMapPropagator()` and inject manually.

## Agent vs SDK-only

| Choose agent | Choose SDK-only |
|---|---|
| Standard JVM container | GraalVM native image (agent doesn't attach) |
| Wide library coverage needed | Minimal classpath, AOT-friendly |
| You don't want to touch app code | You want explicit control over instrumentations |
| Spring Boot, JPA, Kafka, Redis | Plain `java -jar` worker without these |

For SDK-only, use `io.opentelemetry:opentelemetry-sdk-extension-autoconfigure` and configure via env vars / system properties. Most teams should use the agent.

## Rules

- One Java agent JAR per container, version-pinned in the Dockerfile
- Service identity via `OTEL_SERVICE_NAME` + `OTEL_RESOURCE_ATTRIBUTES` env vars — never hardcoded in code
- `@WithSpan` only on Spring-managed beans (or wherever AOP proxies apply); use the `Tracer` API otherwise
- Span names are operation names (`order.process`), not values
- Metric names lowercase dot.case (`orders.created`, `orders.processing.duration`)
- Use Micrometer for metrics in Spring Boot apps (don't bypass to raw OTel meters); the bridge handles the rest
- Exclude `/actuator/health` / `/actuator/prometheus` from server-span sampling via `OTEL_INSTRUMENTATION_COMMON_DEFAULT_ENABLED=true` + per-instrumentation filters
- Sampling capped at 10% in production; raise per env if volume permits
- Logs flow via stdout JSON (`OTEL_LOGS_EXPORTER=none`); only switch to OTel logs export if the log pipeline truly needs OTLP

## What NOT to do

- No `Spring Cloud Sleuth` alongside OTel — `spring-cloud-sleuth-otel` is the migration bridge, then remove Sleuth
- No raw OTel `Meter` calls in a Spring service that already uses Micrometer — pick one, don't double-emit
- No span names with embedded values (`order.process.42`) — values go in attributes
- No `@WithSpan` on private methods called via `this.` — Spring AOP won't proxy them
- No high-cardinality metric tags (`order.id`, `request.id`)
- No agent + reactor/WebFlux without verifying the agent's reactor instrumentation — confirm `traceparent` rides across reactive operators
- No `OTEL_TRACES_SAMPLER=always_on` in production
- No `OTEL_EXPORTER_OTLP_ENDPOINT` pointing at Tempo directly — go through a Collector
- No two agents (e.g. an APM vendor agent + OTel agent) — they conflict on instrumentation; pick one
- No mixing `tracecontext` and `b3` propagators silently — declare the set explicitly

## Generation steps

1. Confirm service identity, Collector endpoint, sampling, instrumentations, and whether agent or SDK is appropriate.
2. Add the agent JAR to the Dockerfile (or to the deployment manifest) with the env vars above.
3. Add the annotation library + Micrometer bridge dependencies in `build.gradle`.
4. Add `@WithSpan` to ~5 high-value domain methods (the ones you'd want to debug in prod first).
5. Confirm `observability/structured-logging-java` is in place; `OpenTelemetryAppender` provides `traceId`/`spanId` MDC.
6. Local smoke: docker-compose with the app + Collector + Tempo + Prometheus + Grafana; hit a few endpoints; confirm spans in Tempo, metrics in Prometheus, logs linked by trace ID in Grafana.

## Handoffs

- Log shape and sinks → `observability/structured-logging-java`
- LogQL / PromQL query patterns → `observability/logql-promql`
- Dashboard layout → `observability/grafana-dashboards`
- .NET equivalent → `observability/opentelemetry-dotnet`
- Node equivalent → `observability/opentelemetry-node`
