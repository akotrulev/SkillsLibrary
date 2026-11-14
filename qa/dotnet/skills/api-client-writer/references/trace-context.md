# Trace context — one trace id per test, on every request

A failed API test is diagnosed in the backend's telemetry: the spans in Tempo and the log lines in Loki. They
are found by trace id only if the test sent one. Every request a test makes carries a W3C `traceparent`
header with **the same trace id for the whole test**, so the backend's spans for that test land in one trace
and `qa/reporting/dotnet/skills/test-reports` (`references/trace-links.md`) can link to it from the failed
result.

## The header

`traceparent: 00-<trace-id>-<parent-id>-01` (W3C Trace Context, version `00`):

| Field | Value |
|---|---|
| `trace-id` | 32 lowercase hex characters (16 bytes); all zeros is invalid and the backend ignores the header |
| `parent-id` | 16 lowercase hex characters (8 bytes), new for each request; all zeros is invalid |
| `trace-flags` | `01` — sampled, so a parent-based sampler (the OpenTelemetry SDK default) records the trace |

The backend's OpenTelemetry instrumentation (ASP.NET Core, Spring, Node HTTP) reads the header with its
default W3C propagator and makes its server span a child of `parent-id`. The test exports no span of its own,
so Tempo shows the trace with a missing root; the backend's spans are all there.

## The trace id: derived from the NUnit test

NUnit's per-test property bag is read-only, and clients are created inside each test from `AuthToken`, so the
trace id is derived instead of stored: a keyed hash of `TestContext.CurrentContext.Test.ID` (unique per test
in a run) with a salt fixed once per test run. The client computes it per request; `BaseApiTest`'s
`[TearDown]` computes the same value for the report link. No client constructor changes.

```csharp
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using NUnit.Framework;

namespace ApiTests.Support;

public static class TestTrace
{
    private static readonly string RunSalt = Guid.NewGuid().ToString("N");

    public static string CurrentTraceId() =>
        Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(RunSalt + TestContext.CurrentContext.Test.ID)))
            .ToLowerInvariant()[..32];

    public static string NewTraceparent() =>
        $"00-{CurrentTraceId()}-{ActivitySpanId.CreateRandom().ToHexString()}-01";
}
```

`RunSalt` is a constant for the process, not mutable state: two runs never share a trace id, and every call
in one test returns the same one. A `[Repeat]` or `[Retry]` attempt keeps the test's id, so its attempts share
one trace — read them apart by span start time.

## The interceptor (RestSharp 111+)

RestSharp's `Interceptor` hook runs for every request a `RestClient` sends. `BaseApiClient` registers it once
in the options it builds the client from, so every `{Resource}Client` inherits it:

```csharp
using RestSharp.Interceptors;

namespace ApiTests.Clients;

public sealed class TraceparentInterceptor : Interceptor
{
    public override ValueTask BeforeHttpRequest(HttpRequestMessage requestMessage, CancellationToken cancellationToken)
    {
        requestMessage.Headers.Add("traceparent", TestTrace.NewTraceparent());
        return ValueTask.CompletedTask;
    }
}
```

```csharp
protected BaseApiClient(string baseUri)
    : base(new RestClientOptions(baseUri) { Interceptors = [new TraceparentInterceptor()] })
{
}
```

Keep whatever else the project's `BaseApiClient` already passes in its options; add only `Interceptors`.
A project on RestSharp below 111 has no interceptors: add the header in `BaseApiClient.Execute` with
`request.AddOrUpdateHeader("traceparent", TestTrace.NewTraceparent())`.

## Recording the trace id

The id is recorded where a reader of the failure looks: `BaseApiTest`'s `[TearDown]` writes it to the test
output and, on failure, attaches the Tempo and Loki links (`test-reports`, `references/trace-links.md`). A test
that sends no request has no trace; the link points at an empty search, which is harmless.

## Rules

- One trace id per test, a new `parent-id` per request, flags `01`. Never a fixed trace id in config, never
  one per client instance (two clients in one test would split the trace).
- The header goes only to the API under test. A client for a third party (a payment sandbox, an identity
  provider) is built without the interceptor — a trace id leaked to a vendor is noise in their logs and tells
  them what you run.
- Checked 2026-11-14: RestSharp 114 `Interceptor.BeforeHttpRequest` on NUnit 4.6 — the header reaches the
  server with the trace id `[TearDown]` computes.
