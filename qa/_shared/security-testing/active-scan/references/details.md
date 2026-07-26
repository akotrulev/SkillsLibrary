# Deep-dive details — `qa-security-active-scan`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## The `plan.yaml` walkthrough — AF jobs, top to bottom

A plan is `env` (contexts + URLs the jobs share) followed by an ordered `jobs` list. ZAP runs the jobs in
order; each reads/writes the shared session.

```yaml
# plan.yaml — annotated ZAP Automation Framework active-scan plan
env:                                   # shared environment: contexts + the URLs jobs operate on
  contexts:
    - name: "target-app"
      urls: ["https://app.test.internal"]      # base URL(s); a throwaway env you OWN and may attack
      includePaths: ["https://app.test.internal/.*"]
      excludePaths: ["https://app.test.internal/logout.*"]   # don't let the spider log itself out
      authentication:                  # see "Authentication" below; secrets come from env vars, NOT here
        method: "browser"              # browser-based auto-detection (modern default for SPAs/forms)
        parameters:
          loginPageUrl: "https://app.test.internal/login"
          browserId: "firefox-headless"
      sessionManagement: { method: "headers" }
      users:
        - name: "scan-user"
          credentials:                 # ${ENV} placeholders resolved from process env — never literals
            username: "${ZAP_USER}"
            password: "${ZAP_PASS}"
      verification:                    # how ZAP confirms it is still logged in mid-scan
        method: "response"
        loggedInRegex: "\\bLogout\\b"
        loggedOutRegex: "\\bLogin\\b"
  parameters:
    failOnError: true                  # abort the plan on a job error
    failOnWarning: false
    progressToStdout: true

jobs:
  - type: passiveScan-config           # tune passive rules before any traffic is generated
    parameters: { scanOnlyInScope: true }

  - type: spider                       # classic crawler — discover the URL surface
    parameters: { context: "target-app", user: "scan-user", maxDuration: 5 }   # minutes, bounded

  - type: spiderAjax                   # JS/SPA crawler — needed for React/Blazor/Angular routes
    parameters: { context: "target-app", user: "scan-user", maxDuration: 5, browserId: "firefox-headless" }

  # --- Spec importers (use the one(s) matching your surface; seed URLs for the active scan) ---
  - type: openapi                      # import an OpenAPI/Swagger doc → seed API endpoints
    parameters: { apiUrl: "https://app.test.internal/openapi.json", targetUrl: "https://app.test.internal", context: "target-app" }
  # - type: graphql                    #   GraphQL: introspect the schema, seed queries/mutations
  #   parameters: { endpoint: "https://app.test.internal/graphql", schemaUrl: "https://app.test.internal/graphql/schema" }
  # - type: soap                       #   SOAP: import a WSDL
  #   parameters: { wsdlUrl: "https://app.test.internal/service?wsdl" }
  # - type: postman                    #   Postman: import a collection
  #   parameters: { collectionFile: "/zap/wrk/collection.json" }

  - type: requestor                    # fire specific requests (e.g. hit an endpoint the spider misses)
    parameters: { user: "scan-user" }
    requests:
      - url: "https://app.test.internal/api/orders/1"
        method: "GET"

  - type: replacer                     # rewrite requests in-flight — inject a bearer token on every call
    rules:
      - description: "Inject bearer token"
        matchType: "REQ_HEADER"
        matchString: "Authorization"
        matchRegex: false
        replacementString: "Bearer ${ZAP_BEARER}"   # resolved from env, NOT committed
        tokenProcessing: false

  - type: activeScan                   # ⚠️ THE ATTACK JOB — injects SQLi/XSS/traversal payloads
    parameters:
      context: "target-app"
      user: "scan-user"
      policy: "api-min-strength"       # references the activeScan-policy job below
      maxRuleDurationInMins: 5
      maxScanDurationInMins: 60        # always bound the active scan
    policyDefinition: {}               # or define inline; or reference a named policy job

  - type: activeScan-policy            # define a reusable scan policy (which attack rules, what strength)
    name: "api-min-strength"
    policy: "api-min-strength"
    scanRules:
      - id: 40018                       # SQL Injection
        strength: "high"
        threshold: "low"
      - id: 40012                       # Cross Site Scripting (Reflected)
        strength: "high"
        threshold: "medium"
      - id: 6                           # Path Traversal
        strength: "medium"

  - type: alertFilter                  # THE TRIAGE GATE — reclassify alerts (see qa-security-shared triage)
    alertFilters:
      - ruleId: 10096                   # Timestamp disclosure on hashed asset names
        newRisk: "False Positive"       # flip to FP — JIRA-4101, accepted
        url: "https://app\\.test\\.internal/static/.*"
        urlRegex: true
      - ruleId: 10038                   # CSP missing — raise so it counts toward the fail threshold
        newRisk: "High"

  - type: report                       # emit machine + human reports
    parameters:
      template: "sarif-json"            # SARIF for code-scanning upload
      reportDir: "/zap/wrk"
      reportFile: "zap-active.sarif"
  - type: report
    parameters: { template: "modern", reportDir: "/zap/wrk", reportFile: "zap-active.html" }   # human report
```

Job order is deliberate: configure passive rules → discover the surface (spider + spiderAjax + spec
importers + requestor) → set up token injection (replacer) → **attack** (activeScan with a policy) →
**triage** (alertFilter) → **report** (SARIF + HTML). Every duration is **bounded** — never let an active
scan run unbounded.

### Exit status & thresholds — the fail-the-build gate

The process exit code alone (`0`/`1`/`2`) is coarse — it does **not** by itself fail on "found 3 High
alerts." Historically this was a friction point (GitHub issue **#6928** — "Automation Framework should be
able to set exit value based on alerts"). The modern answer: drive the build fail off **alert counts by
risk** rather than the raw exit code.

```yaml
  # Fail the run when the active scan finds High/Medium alerts above a threshold.
  - type: outputSummary               # prints a per-risk alert tally to stdout for the CI step to read
    parameters: { format: "short" }
```

Practical approaches, in order of preference:
1. Parse the **SARIF / JSON report** in the CI step and fail on counts (e.g. *any High after alertFilter*) —
   the most portable gate, identical to how `qa-security-shared` consolidates SARIF.
2. Use the official **`zaproxy/action-af`** Action, which surfaces alert counts and can fail the job.
3. Run a small **`script`** job (issue #6928's documented workaround) that calls `controlExit(code)` based
   on `alertCounts` — flip the process exit on a High/Medium count.

Bake the *known-noise* triage into the `alertFilter` job (flip FPs to "False Positive", raise the rules you
will not regress on), then gate on **new** High/Medium alerts — the same ticketed-suppression discipline as
`qa-security-shared`; don't repeat the rationale here.
