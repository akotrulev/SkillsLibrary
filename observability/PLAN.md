# observability/ — Remediation Plan

Plan of action from the 2026-07-12 audit. Work through phases **in order**, one phase per session/agent. Check off tasks as completed. Every task lists exact files, exact edits where possible, and a verification step. Do not improvise beyond what a task says; if something doesn't match the description, stop and report instead of guessing.

**Context for the executing model:**
- This repo is a skills library. Each skill is `observability/<skill-name>/SKILL.md` with YAML frontmatter (`name`, `description`) followed by a markdown body.
- Repo-wide conventions live in `/CLAUDE.md` (root). Key ones for this plan: stack defaults (.NET 10 primary / 8-9 supported · Java 21 + Spring Boot 3 · Node 24 active LTS / 22 maintenance, Node 20 EOL since Apr 2026), and the **version-policy rule**: skills are version-aware — they instruct detecting the project's version first and never applying an up-level API to a down-level project.
- The folder is **not yet published** (not in `.claude-plugin/marketplace.json`) — do not add it to the marketplace in Phases 1–3. That happens only in Phase 5.

---

## Phase 1 — Correctness blockers + broken references (mechanical, no judgment calls)

### 1.1 Fix the Logback `OpenTelemetryAppender` misuse (blocker)

`io.opentelemetry.instrumentation.logback.mdc.v1_0.OpenTelemetryAppender` is an **appender wrapper**, not a TurboFilter. The current config will fail at Logback startup.

- [x] **File:** `observability/structured-logging-java/SKILL.md`
  - In the `logback-spring.xml` sample (~line 92), replace:
    ```xml
    <!-- Bridge OTel span context (traceId, spanId) into MDC for every log -->
    <turboFilter class="io.opentelemetry.instrumentation.logback.mdc.v1_0.OpenTelemetryAppender"/>

    <root level="INFO">
      <appender-ref ref="JSON"/>
    </root>
    ```
    with:
    ```xml
    <!-- Bridge OTel span context (traceId, spanId) into MDC for every log.
         OpenTelemetryAppender is a WRAPPER appender: it decorates the real appender. -->
    <appender name="OTEL" class="io.opentelemetry.instrumentation.logback.mdc.v1_0.OpenTelemetryAppender">
      <appender-ref ref="JSON"/>
    </appender>

    <root level="INFO">
      <appender-ref ref="OTEL"/>
    </root>
    ```
  - Sweep the same file for the phrase "turbo-filter" / "turboFilter" in prose (e.g. the "Correlation with traces" section ~line 190, the Rules list ~line 230, Generation steps ~line 255) and reword each to "the `OpenTelemetryAppender` wrapper appender".
- [x] **File:** `observability/opentelemetry-java/SKILL.md`
  - Lines ~141 and ~205 call it "the `OpenTelemetryAppender` turbo-filter". Reword both to "the `OpenTelemetryAppender` wrapper appender (see `observability/structured-logging-java`)".
- [x] **Verify:** `grep -rn -i "turbofilter\|turbo-filter" observability/` returns nothing.

### 1.2 Fix `Activity.AddException` on .NET 8 (blocker)

`Activity.AddException(Exception)` exists only in .NET 9+. The skill pins .NET 8, where the correct call is OpenTelemetry's `RecordException` extension (namespace `OpenTelemetry.Trace`).

- [x] **File:** `observability/opentelemetry-dotnet/SKILL.md`
  - In the "Custom spans" sample (~line 136), replace `activity?.AddException(ex);` with `activity?.RecordException(ex);` and ensure the sample's `using` block includes `using OpenTelemetry.Trace;` (add it to the code snippet's usings if snippet shows usings; the Program.cs snippet already imports it).
  - In the Rules list (~line 209), change "Set `activity.SetStatus(...)` and `AddException(...)` on the exception path" to "Set `activity.SetStatus(...)` and `RecordException(...)` on the exception path (`Activity.AddException` is .NET 9+ only)".
- [x] **Verify:** `grep -rn "AddException" observability/` only matches the parenthetical note, not code.

### 1.3 Fix broken cross-reference `qa/_shared/quality-metrics`

The skill actually lives at `qa/manual/quality-metrics`.

- [x] **Files:** `observability/logql-promql/SKILL.md` (2 occurrences, ~lines 21 and 293) and `observability/grafana-dashboards/SKILL.md` (2 occurrences, ~lines 22 and 197).
  - Replace every `qa/_shared/quality-metrics` with `qa/manual/quality-metrics`.
- [x] **Verify:** `grep -rn "qa/_shared/quality-metrics" observability/` returns nothing, and `ls qa/manual/quality-metrics` exists.

### 1.4 Remove the invented .NET API reference

- [x] **File:** `observability/opentelemetry-dotnet/SKILL.md`, Stack section (~line 15).
  - Delete the bullet: `` `OpenTelemetry.Extensions.Hosting.Internal.LogToActivityEventConversionExtensions` for ILogger → span events when needed `` — this `Internal` type is not a real public API. Do not replace it with anything (log correlation is already covered by the Serilog handoff).
- [x] **Verify:** `grep -rn "LogToActivityEvent" observability/` returns nothing.

### 1.5 Fix the misleading Java agent endpoint-exclusion rule

- [x] **File:** `observability/opentelemetry-java/SKILL.md`, Rules list (~line 182).
  - Replace: `Exclude /actuator/health / /actuator/prometheus from server-span sampling via OTEL_INSTRUMENTATION_COMMON_DEFAULT_ENABLED=true + per-instrumentation filters`
  - With: `Exclude /actuator/health and /actuator/prometheus spans at the Collector via a filter processor on http.route (the agent has no stable per-URL exclusion env var); see the tail_sampling/filter examples in observability/loki-tempo-setup`
- [x] **Verify:** `grep -rn "OTEL_INSTRUMENTATION_COMMON_DEFAULT_ENABLED" observability/` returns nothing.

### 1.6 Fix the `startActiveSpan` prose error (Node)

`startActiveSpan` never auto-ends a span; only the explicit `span.end()` does.

- [x] **File:** `observability/opentelemetry-node/SKILL.md`, ~line 152.
  - Replace: `Always end the span (the callback flavor handles this for you on the success path; the manual flavor needs finally).`
  - With: `startActiveSpan only scopes the context — it never ends the span for you. Always call span.end() in a finally block, in both the callback and manual flavors.`

### 1.7 De-duplicate resource wiring in the .NET sample

- [x] **File:** `observability/opentelemetry-dotnet/SKILL.md`, Program.cs sample (~lines 65–110).
  - The sample builds a standalone `ResourceBuilder` **and** calls `.ConfigureResource(...)` **and** calls `.SetResourceBuilder(resource)` inside each signal. Consolidate to the modern single path:
    - Delete the standalone `var resource = ResourceBuilder.CreateDefault()...` block.
    - Change `.ConfigureResource(r => r.AddService(builder.Configuration["Service:Name"]!))` to:
      ```csharp
      .ConfigureResource(r => r
          .AddService(
              serviceName:    builder.Configuration["Service:Name"]!,
              serviceVersion: builder.Configuration["Service:Version"]!)
          .AddAttributes(new KeyValuePair<string, object>[]
          {
              new("deployment.environment", builder.Environment.EnvironmentName)
          }))
      ```
    - Delete both `.SetResourceBuilder(resource)` lines (one under `WithTracing`, one under `WithMetrics`).
- [x] **Verify:** the sample contains exactly one resource configuration call and `grep -n "SetResourceBuilder" observability/` returns nothing.

### 1.8 Remove deprecated Java artifact from the Stack list

- [x] **File:** `observability/opentelemetry-java/SKILL.md`, Stack section (~line 13 area).
  - The Stack list mentions `opentelemetry-extension-annotations` (deprecated). The Gradle block later correctly uses `io.opentelemetry.instrumentation:opentelemetry-instrumentation-annotations`. Update the Stack bullet to name `opentelemetry-instrumentation-annotations` instead. Also fix the same stale artifact name if it appears in the frontmatter `description`.
- [x] **Verify:** `grep -rn "extension-annotations" observability/` returns nothing.

### Phase 1 exit criteria
All 8 tasks checked; every `grep` verification passes; `git diff --stat` touches only the 5 named SKILL.md files. Commit as one commit: `Fix correctness blockers and broken refs in observability/`.

---

## Phase 2 — Rename `serilog-structured-logging` → `structured-logging-dotnet`

Restores sibling symmetry (`structured-logging-{dotnet,java,node}`) and fixes inbound references elsewhere in the repo that already point at `observability/structured-logging-dotnet`.

- [x] `git mv observability/serilog-structured-logging observability/structured-logging-dotnet`
- [x] In the moved `SKILL.md`, change frontmatter `name: observability-serilog-structured-logging` → `name: observability-structured-logging-dotnet`. Keep "Serilog" prominent in the `description` (it is a trigger keyword) — e.g. start it "Use when the user asks to set up or refactor logging in a .NET service using Serilog — …".
- [x] Update every reference across the whole repo:
  - Run `grep -rln "serilog-structured-logging" .` (from repo root, excluding `.git`).
  - In each hit, replace `observability/serilog-structured-logging` → `observability/structured-logging-dotnet` and `observability-serilog-structured-logging` → `observability-structured-logging-dotnet`.
  - Expected hit locations: the other 8 observability SKILL.md files (When NOT to use / Handoffs sections), possibly `devops/` and `backend/` skills.
- [x] **Verify:** `grep -rn "serilog-structured-logging" . --exclude-dir=.git` returns nothing; `grep -rn "observability/structured-logging-dotnet" . --exclude-dir=.git` shows the old inbound refs from devops/backend now resolving to a folder that exists.
- [x] Commit: `Rename serilog-structured-logging to structured-logging-dotnet`.
## Phase 3 — Version-policy rewrite (one skill per task; needs care, follow the patterns exactly)

Goal: every stack-bound skill becomes **version-aware** like the rest of the library — the skill's first instruction is "detect the project's version, key every recipe to it, never up-level a down-level project."

**Reference pattern to imitate:** read `frontend/blazor/skills/*/SKILL.md` (any one) and the "Version policy" sections in root `CLAUDE.md` before starting. The pattern is: primary version leads, down-level fallbacks are tagged inline ("net8/9: use X instead"), and a short "Version detection" note near the top tells the model to check the project first (TFM in `.csproj` / `java -version` + Spring Boot BOM / `engines` + CI matrix in `package.json`).

### 3.1 `opentelemetry-dotnet` — .NET 10 primary / 8-9 supported

- [x] Frontmatter description: change ".NET 8 service" → ".NET service (10 primary, 8/9 supported)".
- [x] Title + intro: same change. Add a **Version detection** note right after the intro: "First act on an existing project: read the `TargetFramework` from the `.csproj` and key every recipe below to it. Never apply a net10-only API to a net8/net9 project."
- [x] Body sweep: replace every standalone ".NET 8" with ".NET 10 primary / 8-9 supported" or just ".NET" where version doesn't matter.
- [x] Add one version-keyed note where behavior differs: `RecordException` (OTel extension, works on all TFMs) vs `Activity.AddException` (net9+ native) — recommend `RecordException` as the portable default (Phase 1.2 already set the code this way).

### 3.2 `structured-logging-dotnet` — same treatment

- [x] Frontmatter + title + intro: ".NET 8" → ".NET (10 primary, 8/9 supported)". Add the same Version detection note.
- [x] No API in this skill is version-gated (Serilog surface is stable across TFMs) — state that explicitly in the Version detection note so down-level projects aren't flagged.

### 3.3 `opentelemetry-node` — Node 24 primary / 22 maintenance

- [x] Frontmatter description: "Node 20 + TypeScript" → "Node 24 (22 maintenance) + TypeScript". Title + intro + Stack section: same.
- [x] Add Version detection note: "Check `engines.node` in package.json / the CI matrix. Node 24 is active LTS, 22 is maintenance; **Node 20 is EOL since April 2026 — flag it, don't target it.**"
- [x] Sweep the body for "Node 20" — replace all.

### 3.4 `structured-logging-node` — same treatment as 3.3.

### 3.5 `opentelemetry-java` + `structured-logging-java` — already Java 21 + Spring Boot 3 (correct)

- [x] Add only the Version detection note (Java release + Spring Boot BOM version) to each, for consistency with the rest of the library. No version changes.

### 3.6 Refresh stale hard-pinned artifact versions

Do a web search for the current stable version of each before editing (do NOT guess):

- [x] `observability/opentelemetry-java/SKILL.md`: OTel java agent `2.7.0` (Dockerfile ARG + Gradle annotation lib), `opentelemetry-micrometer1-shim:1.40.0-alpha`.
- [x] `observability/structured-logging-java/SKILL.md`: `logstash-logback-encoder:7.4` (current major is 8.x), `opentelemetry-logback-mdc-1.0:2.7.0-alpha`.
- [x] After updating, add a one-line note near each snippet: "Pin all OTel artifacts to one release train; check the latest at the OpenTelemetry releases page."
- [x] `observability/logql-promql/SKILL.md` ~line 95: update "Native histograms (Prometheus 2.40+)" to note Prometheus 3.x is current and native histograms are stable there.

### 3.7 Promtail → Grafana Alloy (currency fix)

Grafana deprecated Promtail (announced Feb 2025, EOL ~Mar 2026) in favor of **Grafana Alloy**. Web-search "Grafana Alloy Loki logs Kubernetes Helm" for the current config shape before writing.

- [x] **File:** `observability/loki-tempo-setup/SKILL.md`
  - Forwarder decision table (Inputs needed ~line 33 and the "Log forwarders" section ~lines 140–172): make **Grafana Alloy** the recommended default; keep Vector and Fluent Bit as alternatives; demote Promtail to a "legacy — deprecated by Grafana, EOL 2026; migrate with `alloy convert`" note.
  - Replace the Promtail Helm sample with an equivalent Alloy sample (`grafana/alloy` chart; `loki.source.kubernetes` / `discovery.kubernetes` + `loki.write` river config) achieving the same thing: tail pod logs, parse JSON, attach only the low-cardinality labels (`service`, `environment`, `level`, `namespace`), push to Loki.
  - Sweep the file (and the architecture diagram) for "Promtail" — every remaining mention should be in the legacy note only.
- [x] Also sweep the other 8 skills: `grep -rn "Promtail" observability/` — replace incidental mentions ("Promtail / Vector / Fluent Bit") with "Alloy / Vector / Fluent Bit".

### Phase 3 exit criteria
`grep -rn "\.NET 8\b\|Node 20" observability/` returns only tagged-fallback/EOL-note mentions; `grep -rn "Promtail" observability/` returns only the legacy note; every stack skill has a Version detection note. Commit: `Version-policy rewrite for observability/ (.NET 10, Node 24, Alloy)`.

---

## Phase 4 — Fill the metrics gap: new skill `prometheus-mimir-setup`

`loki-tempo-setup` explicitly declares Prometheus/Mimir "a separate skill" that doesn't exist, yet `logql-promql` and `grafana-dashboards` depend on it. Author it.

**Before writing: research existing skills first** (per repo policy) — web-search for well-regarded Prometheus/Mimir setup guides and skill implementations and borrow structure. Then mirror the structure of `observability/loki-tempo-setup/SKILL.md` exactly (same section order: frontmatter → intro → When to use → When NOT to use → Inputs needed → Architecture → main content → Rules → What NOT to do → Generation steps → Handoffs).

- [x] Create `observability/prometheus-mimir-setup/SKILL.md` with frontmatter `name: observability-prometheus-mimir-setup` and a description in the house format (Use when… Triggers: … Do NOT use for…).
- [x] Required content:
  - Prometheus (single-cluster default) vs **Mimir** (multi-cluster / long-retention / HA) decision table.
  - Scrape config vs OTLP remote-write from the OTel Collector (this library's default path — the Collector already exports `prometheusremotewrite`; align with the config in `loki-tempo-setup`).
  - **Exemplar storage** enablement (`--enable-feature=exemplar-storage` / Mimir equivalent) — required by the exemplar wiring `grafana-dashboards` depends on.
  - Recording/alerting **rule deployment** (rule files in Git, loaded via Helm/sidecar; the rules themselves are `logql-promql`'s domain — link, don't duplicate).
  - Retention + cardinality limits; object storage for Mimir.
  - Kubernetes Helm sample values (`prometheus-community/kube-prometheus-stack` or `grafana/mimir-distributed`) in the same style as the Loki/Tempo samples.
- [x] Handoffs must link: `observability/logql-promql` (query/rule syntax), `observability/grafana-dashboards` (panels/exemplar config), `observability/loki-tempo-setup` (Collector hub), `devops/kubernetes` + `devops/iac-bicep-terraform`.
- [x] Update the other skills to point at it:
  - `loki-tempo-setup` "When NOT to use" ~line 24: replace "(related but separate skill)" with "→ `observability/prometheus-mimir-setup`".
  - `grafana-dashboards` and `logql-promql`: add it to Handoffs.
- [x] **Verify:** `grep -rn "separate skill" observability/` returns nothing; new SKILL.md is ≤ ~350 lines (match siblings).
- [x] Commit: `Add prometheus-mimir-setup skill`.

---

## Phase 5 — Agent + packaging (do this LAST; needs human review before publishing)

### 5.1 Author the `observability-engineer` agent(s)

**Decision (2026-07-12): per-stack agents, bundled into the `be-*` plugins.** The user chose to bundle observability into the backend plugins rather than ship a standalone plugin. Because `be-*` is strictly per-stack, the single cross-stack agent the plan first envisioned became three per-stack agents.

- [x] Read `.skill-template/agent.md` (the mandatory brownfield-capable template) and `backend/dotnet/agents/be-dotnet.md` for shape (the observability agents are siblings in the same plugin).
- [x] Create `observability/agents/observability-engineer-{dotnet,java,node}.md` (three files):
  - **Phases:** 1 Discover (detect stack + version, existing telemetry, what's shipped where) → 2 Backend setup (loki-tempo-setup + prometheus-mimir-setup) → 3 Instrument (the stack's opentelemetry-* + structured-logging-*) → 4 Query & dashboards (logql-promql + grafana-dashboards) → 5 Hostile review (cardinality audit, cross-store nav actually wired, no direct-to-backend exporters).
  - **Brownfield:** orient first, then FIX or EXTEND re-entering only the touched phase — discipline wording from the template.
  - Loads **only** `observability/*` skills. Names as **peers** (not loads): `be-{stack}` (the instrumented service, sibling in-plugin), `qa-cicd-{stack}` (CI wiring), `devops/kubernetes` + `devops/iac-bicep-terraform` (cluster/IaC), `qa/manual/quality-metrics` (SLO math).
- [x] **Human check-in done** — packaging shape confirmed: **bundle into `be-*`** (not standalone).

### 5.2 Publish (bundle into `be-*`)

- [x] Add the 6 `observability/*` skills + the stack's `observability-engineer-{stack}` agent to each `be-dotnet` / `be-java` / `be-node` entry in `.claude-plugin/marketplace.json`; refresh each plugin's description to mention observability. (No standalone `observability` plugin.)
- [x] Update root `CLAUDE.md`: add observability to the in-scope list in the Scope blockquote, add an "Observability catalog" section, and update the published-plugins line (observability bundled into `be-*`).
- [x] Commit: `Ship observability/ domain: bundle observability-engineer agents + skills into be-*`.

---

## Phase 6 — Trace-ID correlation contract (parsing correctness)

The three stacks emit three different trace-id JSON field names (Serilog `TraceId` · Logback MDC `traceId`? · pino `trace_id`), and the two derived-field regexes in `loki-tempo-setup` (`"trace_id":"(\w+)"`) and `grafana-dashboards` (`"traceId":"(\w+)"`) contradict each other — each matches at most one stack. Fix by declaring **one canonical contract** and making every regex match every stack.

### 6.1 Verify the actual emitted field names (web search — do NOT guess)

- [x] Web-verify the exact default JSON field names each stack emits:
  - Serilog `Enrich.WithSpan()` / `Serilog.Enrichers.Span` — expected `TraceId` / `SpanId` (PascalCase).
  - `io.opentelemetry.instrumentation.logback.mdc.v1_0.OpenTelemetryAppender` — verify whether the MDC keys are `trace_id`/`span_id` (snake_case) or `traceId`/`spanId`. The Java skill currently claims **both** in different sentences (~lines 8, 75, 199) — fix whichever is wrong.
  - `@opentelemetry/instrumentation-pino` — expected `trace_id` / `span_id`.
- [x] **File:** each `structured-logging-{dotnet,java,node}/SKILL.md` — add a short "**Trace-correlation contract**" note stating the exact JSON field name that stack emits (verified, not assumed), and that this is the name the Loki derived field must match.

### 6.2 One canonical derived-field regex everywhere

- [x] Decide the canonical regex that matches all three stacks' emissions, e.g.:
  ```
  Regex: "(?:trace_?[iI]d|TraceId)"\s*:\s*"([0-9a-fA-F]{32})"
  ```
  (W3C trace ids are 32 hex chars — `\w+` is too loose and can capture garbage.) Adjust to whatever 6.1 verified.
- [x] **File:** `observability/loki-tempo-setup/SKILL.md` — "Loki derived fields (logs → traces)" section (~line 314): replace the regex with the canonical one; add a per-stack field-name table (dotnet → `TraceId`, java → …, node → `trace_id`); note the derived field is configured with an **internal link** (`datasourceUid` of Tempo, query `${__value.raw}`).
- [x] **File:** `observability/grafana-dashboards/SKILL.md` — "Logs → traces via derived fields" section (~line 91): same canonical regex + point at `loki-tempo-setup` as the owning definition (link, don't duplicate the table).
- [x] **File:** `observability/logql-promql/SKILL.md` (~line 178 `line_format`, ~line 249): make the field-name usage consistent with the per-stack table (`| json` field names differ per stack — say so once).
- [x] **Verify:** `grep -rn 'Regex' observability/` shows the identical canonical regex in both files; no bare `"trace_id":"(\w+)"` / `"traceId":"(\w+)"` remains.

### 6.3 Close the traceability loop: Tempo trace → logs

Currently only logs→traces (derived fields) and metrics→traces (exemplars) are wired. The third leg — **trace → logs** — is missing.

- [x] **File:** `observability/loki-tempo-setup/SKILL.md` — in "Cross-store navigation", add a third wiring: Tempo data source **`tracesToLogsV2`** config (target Loki datasource, `tags: [service]` mapped to the Loki `service` label, `spanStartTimeShift: -5m` / `spanEndTimeShift: 5m`, `filterByTraceID: true`). Show the provisioned-datasource YAML shape (data sources are declared via Helm/Terraform per the existing rule).
- [x] **File:** `observability/grafana-dashboards/SKILL.md` — mention the third leg so the "complete loop" reads: alert → dashboard → exemplar → trace → logs → (derived field) back to trace.
- [x] Also add `tracesToMetrics` as a one-line optional mention (span → RED metrics of that service).
- [x] **Verify:** `grep -rn "tracesToLogs" observability/` hits both files.
- [x] Commit: `Trace-ID correlation contract: canonical derived-field regex + trace→logs leg`.

---

## Phase 7 — Multi-service dashboards + 4xx/5xx discipline

### 7.1 Fleet / multi-service overview dashboard

- [ ] **File:** `observability/grafana-dashboards/SKILL.md` — add a "**Fleet overview (multi-service)**" section after the standard RED template:
  - Purpose: one dashboard answering "which service is unhealthy right now" across all services; drill into the per-service RED dashboard via **data links** on the service name.
  - Panel set: RED-by-service **table** (req/s, 5xx %, p95 — one row per service, sorted by error rate desc, thresholds coloring); top-N error-rate time-series; **Tempo service-graph panel** (`nodeGraph`, fed by the `metrics_generator.service_graphs` processor already enabled in `loki-tempo-setup`); active-alerts panel grouped by service.
  - `$service` becomes multi-value (`includeAll: true`) on the fleet dashboard; per-service dashboard keeps single-value.
  - Data-link pattern: table cell → `/d/<per-service-uid>?var-service=${__data.fields.service}`.
- [ ] Update Generation steps + Rules to name the two-tier model: **one fleet overview + one RED dashboard per service**, linked both ways.

### 7.2 4xx vs 5xx discipline

- [ ] **File:** `observability/grafana-dashboards/SKILL.md` — RED template table: split the single error panel into **5xx rate %** and **4xx rate %** (separate series, separate panels or one panel with two queries). Add the discipline note: **5xx = server fault → alert; 4xx = client behavior → observe, don't page** — except a 4xx *spike* (rate anomaly vs baseline, or 401/403 surge = credential-stuffing / broken-auth signal → tactical alert, and a 404 surge after deploy = broken route/link).
- [ ] **File:** `observability/logql-promql/SKILL.md` — add canonical recipes near the existing error-ratio idiom: 5xx ratio by service/route, 4xx ratio excluding expected noise (`status!~"401|403"` variant and the opposite security-watch variant), and the equivalent LogQL for apps whose only signal is logs.
- [ ] **Verify:** `grep -rn '4\.\.' observability/` hits grafana-dashboards + logql-promql recipes (not just the old single line).

### 7.3 Traceability column on tables

- [ ] **File:** `observability/grafana-dashboards/SKILL.md` — "Top slow routes" and fleet tables gain a data-link column into Tempo search (`service` + `http_route` pre-filled) so table rows are one click from traces. State the loop explicitly in one sentence in the Exemplars section.
- [ ] Commit: `Fleet overview dashboards + 4xx/5xx discipline`.

---

## Phase 8 — Unhealthy-service alerting

### 8.1 Health-alert pack (rule syntax)

- [ ] **File:** `observability/logql-promql/SKILL.md` — add a "**Service-health alert pack**" section (PromQL rules, YAML shape ready for the rule deployment path in `prometheus-mimir-setup`):
  - `up == 0` (scrape target down) **and** `absent(up{service="X"})` (target vanished — the alert people forget).
  - Kubernetes: restart loops (`increase(kube_pod_container_status_restarts_total[15m]) > 3`), pods not ready (`kube_pod_status_ready{condition="true"} == 0` sustained), deployment replica mismatch.
  - Blackbox probe failure (`probe_success == 0`) as the outside-in check.
  - 5xx burn-rate pair (fast 1h / slow 6h) — reference the existing burn-rate row in grafana-dashboards, keep the math here.
  - Rule hygiene: every rule has `for:`, `severity` label, `runbook_url` annotation; alert on symptoms, not causes.
- [ ] **Verify:** `grep -n "absent(" observability/logql-promql/SKILL.md` hits.

### 8.2 Alertmanager (routing) in `prometheus-mimir-setup`

- [ ] **File:** `observability/prometheus-mimir-setup/SKILL.md` — replace the "Alertmanager routing / on-call escalation — out of scope" line (~line 25) with a new "**Alertmanager**" section: deployed by `kube-prometheus-stack` (or Mimir's built-in multi-tenant Alertmanager), routing tree by `severity` + `service` labels, grouping (`group_by: [alertname, service]`), inhibition (critical inhibits warning for same service), and a **dead-man's-switch** (`Watchdog` always-firing alert → external heartbeat) so silence itself alerts. Receivers (Slack / PagerDuty / Opsgenie) shown as config shape, not vendor tutorials.
- [ ] Keep the scope fence: rule *syntax* stays in `logql-promql`; this skill owns rule/router *deployment*.
- [ ] **Verify:** `grep -rn "out of scope" observability/prometheus-mimir-setup/SKILL.md` returns nothing about Alertmanager.

### 8.3 Sweep the agents + handoffs

- [ ] **Files:** `observability/agents/observability-engineer-{dotnet,java,node}.md` — Phase 4 (Query & dashboards) wording gains "fleet overview + per-service RED dashboards, health-alert pack, Alertmanager routing"; Phase 5 review checklist gains "trace→logs leg wired; derived-field regex matches this stack's actual field name; 4xx/5xx split; dead-man's-switch present".
- [ ] Cross-check Handoffs sections across the 6 stack-agnostic/setup skills still resolve (run the global verification loops below).
- [ ] Commit: `Unhealthy-service alerting: health-alert pack + Alertmanager routing`.

---

## Global verification (run after every phase)

```bash
# no dangling intra-repo skill references out of observability/
grep -rno "observability/[a-z-]*" observability/ | sed 's/.*://' | sort -u | while read p; do [ -d "$p" ] || echo "BROKEN: $p"; done
# no dangling references INTO observability/ from the rest of the repo
grep -rno "observability/[a-z-]*" --include=SKILL.md --include=*.md qa backend frontend devops data 2>/dev/null | sed 's/.*:\(observability[^ ]*\)/\1/' | sort -u | while read p; do [ -d "$p" ] || echo "BROKEN INBOUND: $p"; done
```

Both loops must print nothing (Phase 4 fixes the last expected gap).
