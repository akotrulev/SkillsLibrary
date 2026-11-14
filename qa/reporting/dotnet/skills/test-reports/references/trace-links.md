# Trace links — from a failed test to its backend trace and logs

Every request a test sends carries one `traceparent` trace id per test (``qa/dotnet/skills/api-client-writer``, `references/trace-context.md`;
UI tests: ``qa/dotnet/skills/ui-test-author/playwright``, `references/trace-correlation.md`). On failure the result gets one `telemetry`
attachment of type `text/uri-list`: a comment line with the trace id, a Grafana Explore link to the trace in
Tempo, and one to the log lines carrying that id in Loki. A passing test gets nothing.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `GRAFANA_URL` | none — **no links are written** | Grafana's base URL, e.g. `http://localhost:3000` for the local stack under `deploy/local/` |
| `GRAFANA_TEMPO_UID` | `tempo` | The Tempo data source's uid (the observability skills provision `tempo`) |
| `GRAFANA_LOKI_UID` | `loki` | The Loki data source's uid (provisioned as `loki`) |

A missing `GRAFANA_URL` skips the attachment; it never fails or skips the test. Links are built only from the
trace id and these variables — never from a response body or a token.

## The Explore URL

Grafana's Explore URL is `<grafana>/explore?schemaVersion=1&orgId=1&panes=<url-encoded JSON>`, where each
pane holds a data source uid, its queries and a time range:

- **Tempo** — `queryType: "traceql"` with the bare trace id as `query`; the TraceQL editor looks a trace up by
  id.
- **Loki** — `{service_name=~".+"} |= "<trace id>"`: a line filter, so it matches the .NET `TraceId` and the
  Java/Node `trace_id` field names alike (`observability/logs-traces-setup`'s correlation contract). Narrow the
  selector to `{service_name="<service>"}` where the project has one service.
- **Range** — `now-1h` to `now`, wide enough for a CI run read soon after. A report read days later widens the
  range in Explore.

When a Grafana version rejects the generated pane, open a trace in that Grafana's Explore, copy the URL, and
compare the decoded `panes` JSON with the helper's.

## The helper

```csharp
using System.Text.Json;

namespace ApiTests.Support;

public static class TelemetryLinks
{
    public static string? UriList(string traceId)
    {
        var grafana = Environment.GetEnvironmentVariable("GRAFANA_URL");
        if (string.IsNullOrWhiteSpace(grafana))
        {
            return null;
        }
        var tempo = Environment.GetEnvironmentVariable("GRAFANA_TEMPO_UID") ?? "tempo";
        var loki = Environment.GetEnvironmentVariable("GRAFANA_LOKI_UID") ?? "loki";
        return string.Join("\r\n",
            $"# trace-id {traceId}",
            Explore(grafana, tempo, new { refId = "A", datasource = new { type = "tempo", uid = tempo }, queryType = "traceql", query = traceId }),
            Explore(grafana, loki, new { refId = "A", datasource = new { type = "loki", uid = loki }, expr = $"{{service_name=~\".+\"}} |= \"{traceId}\"" }));
    }

    private static string Explore(string grafana, string datasourceUid, object query)
    {
        var panes = JsonSerializer.Serialize(new
        {
            a = new { datasource = datasourceUid, queries = new[] { query }, range = new { from = "now-1h", to = "now" } },
        });
        return $"{grafana.TrimEnd('/')}/explore?schemaVersion=1&orgId=1&panes={Uri.EscapeDataString(panes)}";
    }
}
```

## Attach on failure — API tests

`BaseApiTest` gets one more `[TearDown]`. The trace id is `TestTrace.CurrentTraceId()`, the value the
client's interceptor sent; it is written to the test output on every run, and the links are attached only on
failure:

```csharp
[TearDown]
public void LinkTelemetryOnFailure()
{
    var traceId = TestTrace.CurrentTraceId();
    TestContext.Out.WriteLine($"trace-id {traceId}");
    var links = TelemetryLinks.UriList(traceId);
    if (TestContext.CurrentContext.Result.Outcome.Status != TestStatus.Failed || links is null)
    {
        return;
    }
    AllureApi.AddAttachment("telemetry", "text/uri-list", Encoding.UTF8.GetBytes(links), ".uri");
}
```

The byte-array overload with its extension, never the string overload — its third argument is a file path.

## Attach on failure — Playwright UI tests

`BaseTest`'s `[TearDown]` already attaches the trace, screenshot and video on failure. The trace-correlation
reference adds the trace id to `BaseTest`; the same `TelemetryLinks.UriList(traceId)` result is attached there,
beside the other evidence, with the same call.

## Triage a failed run

The reporting agent's triage step follows this procedure for each failed test it is asked to diagnose. It
reads; it changes no product or test code.

1. **Open the evidence.** The `telemetry` attachment's Tempo link shows the backend's spans for the test: find
   the span with an error status, the HTTP 5xx, or the span that ate the time. The Loki link shows every log
   line carrying the trace id: read the first error, not the last. Add the test's own evidence — the response
   body, the Playwright trace, the assertion message.
2. **Line it up against the change timeline.** From Allure history, when did this test last pass? List what
   changed between that run and this one: deploys of each service the trace touches (the pipeline's history,
   the `service.version` resource attribute on the spans), commits to the test suite, configuration and
   feature-flag changes, seed-data or schema migrations. A failure that starts at a change makes that change
   the first suspect.
3. **Rank three to five hypotheses**, most likely first, each with the cheapest test that would **falsify**
   it — an experiment whose result rules the hypothesis out, not one that merely fits it:

   | # | Hypothesis | Falsified if | Result |
   |---|---|---|---|
   | H1 | `orders-api` 2.14.0 rejects the new `currency` field | the same request passes against 2.13.x | |
   | H2 | The seeded customer is stale after the migration | a freshly seeded customer fails the same way | |
   | H3 | `payments-stub` was down during the run | its span in the trace returned `200` | |

4. **Run the falsifiers, cheapest first**, and strike each hypothesis its experiment rules out. Stop when one
   survives every experiment that could have killed it.
5. **Report the root-cause candidate with its evidence**: the trace id, the span and its status, the log line,
   the deploy or commit id, and each falsifier's result. Classify it — product defect, test defect, test data,
   environment — and hand it to its owner. A failure that passes and fails on the same code is not closed as
   "flaky": it goes to `flaky-test-quarantine`'s De-flake move.

No trace to open — `GRAFANA_URL` unset, the header not sent, the backend not sampling — is said in the report,
and the triage falls back to the response body and the backend's logs for the test's time window.
