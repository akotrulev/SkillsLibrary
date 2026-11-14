# Trace links — from a failed test to its backend trace and logs

Every request a test sends carries one `traceparent` trace id per test (``qa/typescript/skills/api-client-writer``, `references/trace-context.md`;
UI tests: ``qa/typescript/skills/ui-test-author/playwright``, `references/trace-correlation.md`). On failure the result gets one `telemetry`
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

```ts
// src/support/telemetryLinks.ts
export function telemetryUriList(traceId: string): string | undefined {
  const grafana = process.env.GRAFANA_URL;
  if (!grafana) {
    return undefined;
  }
  const tempo = process.env.GRAFANA_TEMPO_UID ?? 'tempo';
  const loki = process.env.GRAFANA_LOKI_UID ?? 'loki';
  return [
    `# trace-id ${traceId}`,
    explore(grafana, tempo, { refId: 'A', datasource: { type: 'tempo', uid: tempo }, queryType: 'traceql', query: traceId }),
    explore(grafana, loki, { refId: 'A', datasource: { type: 'loki', uid: loki }, expr: `{service_name=~".+"} |= "${traceId}"` }),
  ].join('\r\n');
}

function explore(grafana: string, datasourceUid: string, query: Readonly<Record<string, unknown>>): string {
  const panes = JSON.stringify({
    a: { datasource: datasourceUid, queries: [query], range: { from: 'now-1h', to: 'now' } },
  });
  return `${grafana.replace(/\/+$/, '')}/explore?schemaVersion=1&orgId=1&panes=${encodeURIComponent(panes)}`;
}
```

## Attach on failure — Vitest API tests

A setup file, registered in `vitest.config.ts` `test.setupFiles`, registers an `onTestFailed` callback for
every test. `currentTraceId()` is the value `baseClient` sent, because the callback still runs under the
failed test:

```ts
// src/support/telemetry.setup.ts
import * as allure from 'allure-js-commons';
import { beforeEach } from 'vitest';
import { telemetryUriList } from './telemetryLinks.js';
import { currentTraceId } from './testTrace.js';

beforeEach(({ onTestFailed }) => {
  onTestFailed(async () => {
    const links = telemetryUriList(currentTraceId());
    if (links) {
      await allure.attachment('telemetry', links, { contentType: 'text/uri-list' });
    }
  });
});
```

Checked 2026-11-14 on Vitest 3.2.4 + allure-vitest 3.13.0: the attachment lands on the failed test's result,
and a passing test gets none.

## Attach on failure — Playwright UI tests

The trace-correlation fixture already holds the trace id. After `use()`, when
`testInfo.status !== testInfo.expectedStatus`, it attaches the same list with
`testInfo.attach('telemetry', { body: links, contentType: 'text/uri-list' })` — `allure-playwright` copies every
`testInfo` attachment, and the Playwright HTML report shows it too.

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
