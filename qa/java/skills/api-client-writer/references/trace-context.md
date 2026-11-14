# Trace context — one trace id per test, on every request

A failed API test is diagnosed in the backend's telemetry: the spans in Tempo and the log lines in Loki. They
are found by trace id only if the test sent one. Every request a test makes carries a W3C `traceparent`
header with **the same trace id for the whole test**, so the backend's spans for that test land in one trace
and `qa/reporting/java/skills/test-reports` (`references/trace-links.md`) can link to it from the failed
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

## The trace id: an attribute of the TestNG result

TestNG keeps one `ITestResult` per test invocation, and `Reporter.getCurrentTestResult()` returns it on the
test's thread. The trace id lives in that result's attributes: created on the test's first request, read by
every later one, and read again by `BaseApiTest`'s `@AfterMethod(alwaysRun = true)` through its injected
`ITestResult`. No client constructor changes.

```java
package com.{org}.apitests.support;

import java.security.SecureRandom;
import java.util.HexFormat;
import org.testng.ITestResult;
import org.testng.Reporter;

public final class TestTrace {
    public static final String ATTRIBUTE = "traceId";
    private static final HexFormat HEX = HexFormat.of();
    private static final SecureRandom RANDOM = new SecureRandom();

    private TestTrace() {
    }

    public static String newTraceparent() {
        return "00-" + traceIdOf(Reporter.getCurrentTestResult()) + "-" + randomHex(8) + "-01";
    }

    private static String traceIdOf(ITestResult result) {
        Object existing = result.getAttribute(ATTRIBUTE);
        if (existing != null) {
            return (String) existing;
        }
        String created = randomHex(16);
        result.setAttribute(ATTRIBUTE, created);
        return created;
    }

    private static String randomHex(int bytes) {
        byte[] buffer = new byte[bytes];
        RANDOM.nextBytes(buffer);
        return HEX.formatHex(buffer);
    }
}
```

A test invoked twice (`invocationCount`, a data-provider row, a retry) gets a new `ITestResult` and so a new
trace.

## The filter (REST Assured)

REST Assured runs every registered `Filter` around each request. `BaseApiClient.spec()` adds it beside the
`AllureRestAssured` filter, so every `{Resource}Client` inherits it:

```java
package com.{org}.apitests.clients;

import com.{org}.apitests.support.TestTrace;
import io.restassured.filter.Filter;
import io.restassured.filter.FilterContext;
import io.restassured.response.Response;
import io.restassured.specification.FilterableRequestSpecification;
import io.restassured.specification.FilterableResponseSpecification;

public final class TraceparentFilter implements Filter {
    @Override
    public Response filter(FilterableRequestSpecification request, FilterableResponseSpecification response, FilterContext context) {
        request.header("traceparent", TestTrace.newTraceparent());
        return context.next(request, response);
    }
}
```

```java
protected RequestSpecification spec() {
    return RestAssured.given()
        .baseUri(baseUri)
        .header("Authorization", "Bearer " + jwt)
        .filter(new TraceparentFilter())
        .filter(new AllureRestAssured());
}
```

`TraceparentFilter` goes before `AllureRestAssured`, so the recorded HTTP exchange shows the header.

## Rules

- One trace id per test, a new `parent-id` per request, flags `01`. Never a fixed trace id in config, never
  one per client instance.
- The header goes only to the API under test. A client for a third party is built without the filter — a
  trace id leaked to a vendor is noise in their logs and tells them what you run.
- `Reporter.getCurrentTestResult()` is the test's result only on the thread running the test. A request sent
  from another thread (an `ExecutorService` inside a test) has no current result; keep requests on the test
  thread, which the suite's rules already require.
