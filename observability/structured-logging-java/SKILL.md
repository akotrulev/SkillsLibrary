---
name: observability-structured-logging-java
description: Use when the user asks to set up or refactor logging in a Java 21 / Spring Boot 3 service — SLF4J + Logback with JSON encoding, MDC for correlation, sinks to console / Loki / Elastic. Triggers: "set up structured logging in Spring Boot", "Logback JSON config", "ship logs to Loki", "add MDC correlation IDs", "this log line is wrong". Do NOT use for .NET (use `observability/serilog-structured-logging`) or Node (use `observability/structured-logging-node`), or for tracing/metrics (use `observability/opentelemetry-java`).
---

# Observability — Structured Logging (Java 21 / Spring Boot 3)

Sets up SLF4J + Logback as the logging stack in a Java 21 + Spring Boot 3 service. Logs are JSON via `logstash-logback-encoder`, written with placeholder logging (never `+` concatenation or `String.format`), enriched with MDC (`traceId`, `spanId`, `tenantId`, `requestId`), and shipped to Loki for prod / stdout JSON for everywhere.

## Stack

- **Java 21 + Spring Boot 3.x**
- **SLF4J 2.x** as the API
- **Logback** as the implementation (Spring Boot default)
- **`net.logstash.logback:logstash-logback-encoder`** for JSON output
- **`io.opentelemetry.instrumentation:opentelemetry-logback-mdc-1.0`** to bridge OTel trace context → MDC
- Shipping: stdout JSON → container runtime → Promtail / Fluent Bit / Vector → Loki. Direct Loki appenders exist (`com.github.loki4j:loki-logback-appender`) but stdout-first is the portable default.

## When to use

- New Spring Boot service needs logging
- Replacing `System.out.println` / plain `logger.info("text " + var)` with structured logs
- Adding MDC correlation IDs / trace propagation
- Wiring logs to Loki
- Masking PII / secrets in log output

## When NOT to use

- .NET service → `observability/serilog-structured-logging`
- Node service → `observability/structured-logging-node`
- Distributed tracing or metrics → `observability/opentelemetry-java`
- LogQL query authoring → `observability/logql-promql`
- Dashboard layout → `observability/grafana-dashboards`

## Inputs needed

1. **Target environment(s)** + sink per env (stdout JSON everywhere by default; direct Loki only if no log forwarder is available)
2. **Service name + version** — go into MDC / static fields
3. **PII / sensitive fields** that must never appear in logs
4. **Tracing in scope?** — if `observability/opentelemetry-java` is configured, plug the MDC bridge

## Setup

### Dependencies (Gradle)

```groovy
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter'
    implementation 'net.logstash.logback:logstash-logback-encoder:7.4'
    implementation 'io.opentelemetry.instrumentation:opentelemetry-logback-mdc-1.0:2.7.0-alpha'
}
```

### `src/main/resources/logback-spring.xml`

```xml
<configuration>
  <springProperty name="serviceName"    source="spring.application.name" defaultValue="unknown"/>
  <springProperty name="serviceVersion" source="info.app.version"        defaultValue="0.0.0"/>
  <springProperty name="env"            source="spring.profiles.active"  defaultValue="local"/>

  <appender name="JSON" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="net.logstash.logback.encoder.LoggingEventCompositeJsonEncoder">
      <providers>
        <timestamp><fieldName>timestamp</fieldName><pattern>yyyy-MM-dd'T'HH:mm:ss.SSSXXX</pattern></timestamp>
        <logLevel><fieldName>level</fieldName></logLevel>
        <loggerName><fieldName>logger</fieldName></loggerName>
        <threadName><fieldName>thread</fieldName></threadName>
        <mdc/>                                  <!-- emits MDC keys flat: traceId, spanId, tenantId, ... -->
        <stackTrace>
          <throwableConverter class="net.logstash.logback.stacktrace.ShortenedThrowableConverter">
            <maxDepthPerThrowable>30</maxDepthPerThrowable>
            <rootCauseFirst>true</rootCauseFirst>
          </throwableConverter>
        </stackTrace>
        <message><fieldName>message</fieldName></message>
        <pattern>
          <pattern>
            {
              "service.name":    "${serviceName}",
              "service.version": "${serviceVersion}",
              "environment":     "${env}"
            }
          </pattern>
        </pattern>
        <arguments includeNonStructuredArguments="false"/>
      </providers>
    </encoder>
  </appender>

  <!-- Bridge OTel span context (traceId, spanId) into MDC for every log -->
  <turboFilter class="io.opentelemetry.instrumentation.logback.mdc.v1_0.OpenTelemetryAppender"/>

  <root level="INFO">
    <appender-ref ref="JSON"/>
  </root>

  <!-- Tame chatty libraries -->
  <logger name="org.springframework"          level="WARN"/>
  <logger name="org.hibernate"                level="WARN"/>
  <logger name="org.apache.kafka"             level="WARN"/>
  <logger name="org.springframework.web"      level="INFO"/>
</configuration>
```

`<mdc/>` emits every MDC key as a top-level JSON field. The composite encoder flattens everything — no nested `"context": {...}` wrapper that fights Loki queries.

### Profile overrides

For local dev a colorized console pattern is nicer than JSON. Use a Spring profile guard:

```xml
<springProfile name="local">
  <appender name="PRETTY" class="ch.qos.logback.core.ConsoleAppender">
    <encoder><pattern>%d{HH:mm:ss.SSS} %-5level [%X{traceId:-}] %logger{20} - %msg%n</pattern></encoder>
  </appender>
  <root level="INFO"><appender-ref ref="PRETTY"/></root>
</springProfile>
<springProfile name="!local">
  <root level="INFO"><appender-ref ref="JSON"/></root>
</springProfile>
```

## Writing logs

### Use placeholders, not concatenation

```java
// ✅ correct — args are captured as structured arguments
log.info("Order {} created for customer {} totalling {} {}", orderId, customerId, totalMinor, currency);

// ❌ wrong — collapsed to a single opaque string
log.info("Order " + orderId + " created for customer " + customerId);
log.info(String.format("Order %s created", orderId));
```

### Use `StructuredArguments` for first-class fields

For values that must be queryable as fields (not just appear in the message), use Logstash's `StructuredArguments`:

```java
import static net.logstash.logback.argument.StructuredArguments.kv;

log.info("Order created {}", kv("orderId", order.getId()), kv("customerId", order.getCustomerId()));
// JSON has: "orderId": "...", "customerId": "...", and message: "Order created"
```

Pick a convention per project — placeholders OR `StructuredArguments` — and apply it consistently. `StructuredArguments` is preferred for values you grep on in Loki.

### MDC for cross-cutting context

```java
try (MDC.MDCCloseable ignored1 = MDC.putCloseable("tenantId", tenantId);
     MDC.MDCCloseable ignored2 = MDC.putCloseable("requestId", requestId)) {
    // every log inside this block has tenantId + requestId attached
}
```

Spring filter / interceptor to set `requestId` at the edge:

```java
@Component
public class RequestIdFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
        throws IOException, ServletException {
        String id = Optional.ofNullable(req.getHeader("X-Request-Id")).orElseGet(() -> UUID.randomUUID().toString());
        try (MDC.MDCCloseable ignored = MDC.putCloseable("requestId", id)) {
            res.setHeader("X-Request-Id", id);
            chain.doFilter(req, res);
        }
    }
}
```

### Log exceptions, don't stringify them

```java
// ✅ correct — exception serialized with structured stack trace
log.error("Failed to process order {}", orderId, ex);

// ❌ wrong — stack trace collapses into message
log.error("Failed to process order {}: {}", orderId, ex.toString());
```

The exception **must be the last argument**, not a placeholder substitution — that's how SLF4J knows to render it.

## Correlation with traces

The `OpenTelemetryAppender` turbo-filter copies `trace_id` / `span_id` from the active OTel context into MDC. Every log emitted inside an active span gets `traceId` and `spanId` JSON fields. Loki + Tempo wire these to "Jump to trace" in Grafana.

No code changes needed in callers once the appender is registered.

## Levels & cardinality

| Level | When |
|---|---|
| `TRACE` | Never in production |
| `DEBUG` | Per-request detail; off in staging/prod by default |
| `INFO` | Domain events worth keeping |
| `WARN` | Recoverable issues; retries; fallbacks; contract drift |
| `ERROR` | Operation failed in a way the user/caller will notice |

Loki labels are categorical (`service`, `env`, `level`). High-cardinality fields (`orderId`, `userId`) go in the JSON body. The same rule as Serilog — a per-request label tanks Loki.

## Sensitive data

- Never log full request / response bodies on auth, payment, or user-data endpoints
- Add a Logback filter to drop or mask sensitive patterns:

```java
public class PiiMaskingConverter extends MessageConverter {
    private static final Pattern CARD = Pattern.compile("\\b\\d{13,19}\\b");
    @Override
    public String convert(ILoggingEvent event) {
        return CARD.matcher(super.convert(event)).replaceAll("***REDACTED***");
    }
}
```

Or filter at the source — pass DTO projections to the logger, never the entity itself.

## Rules

- SLF4J `org.slf4j.Logger` only; never `java.util.logging`, never `Log4j 1.x`, never `System.out`
- Placeholder logging (`log.info("... {} ...", arg)`) — never `+` concatenation, `String.format`, or pre-built `.toString()` on objects
- Output is JSON in every environment except `local` (where colorized console is allowed)
- Service name / version / environment as static fields in every log line
- `<mdc/>` provider in the encoder so MDC keys are top-level JSON fields
- `OpenTelemetryAppender` turbo-filter wired up so `traceId` / `spanId` ride every log
- Loki labels are low-cardinality (`service`, `environment`, `level`)
- Chatty namespaces (`org.springframework.*`, `org.hibernate.*`, `org.apache.kafka.*`) capped at `WARN`
- MDC keys cleared at the end of every request via try-with-resources / `MDCCloseable`
- Exceptions are passed as the last argument to `error` / `warn`, never `.toString()`-ed into the message

## What NOT to do

- No `System.out` / `System.err`
- No string concatenation or `String.format` inside log calls
- No `logger.info(e)` — pass the message + the exception as separate args
- No raw entity / DTO logging on hot paths — log identifiers and counts
- No DEBUG / TRACE level in production minimum config
- No nested `"context": {...}` JSON wrapper — MDC keys go flat
- No per-request Loki labels — fields, not labels
- No `Marker`-based filtering as a substitute for proper levels
- No two encoders for the same appender — pick JSON or pattern, not both
- No `static final Logger` declared at instance scope — use class-scoped Lombok `@Slf4j` or `LoggerFactory.getLogger(getClass())` consistently

## Generation steps

1. Confirm environments, sink targets (stdout JSON vs direct Loki), service name/version, and PII rules with the user.
2. Add the encoder + OTel MDC dependencies.
3. Create `src/main/resources/logback-spring.xml` from the template; tune `<springProperty>` to match the project's properties.
4. Add the `RequestIdFilter` (or equivalent) to populate `requestId` for every request.
5. If OTel is in the project, the `OpenTelemetryAppender` turbo-filter is mandatory.
6. Sweep the codebase for `+` concatenation in log calls and `e.toString()`; convert to placeholders + exception arg.
7. Smoke locally — `curl` a few endpoints, confirm JSON includes `traceId`, `spanId`, `requestId`, `service.name`.

## Handoffs

- Distributed tracing + metrics → `observability/opentelemetry-java`
- LogQL queries against Loki → `observability/logql-promql`
- Dashboard layout → `observability/grafana-dashboards`
- .NET equivalent → `observability/serilog-structured-logging`
- Node equivalent → `observability/structured-logging-node`
