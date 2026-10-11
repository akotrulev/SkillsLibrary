---
name: api-fuzzing
description: Use when fuzzing an API from its OpenAPI/GraphQL schema with Schemathesis — property-based generated requests that catch 5xx crashes and contract violations, wired as a CI gate. Language-agnostic (CLI/Docker), any stack. Triggers: "fuzz our API", "schema-based negative testing", "run Schemathesis in CI". Not for authorization/BOLA (`permission-testing`) or a crawling DAST scan (`active-scan`).
---

# Security Testing — API Fuzzing (Schemathesis, shared)

Property-based fuzzing of an OpenAPI/GraphQL API against a **running** app. A single language-agnostic
skill: **Schemathesis** is a Python CLI / Docker image / GitHub Action that reads your app's **schema** and
its live **HTTP surface** — it does not care what language the app is written in, so there is no
three-stack split (the architectural fact the master ref spells out). Load this **alongside**
`qa-<stack>:security-foundations` (the OWASP map, the authorization-to-scan rule, the triage discipline live there —
this skill defers to them and does not re-state them in full).

**Schemathesis** (v4.x, MIT; used in CI by Spotify, WordPress, JetBrains, Red Hat) generates **thousands**
of test cases from the schema and asserts **properties** — not exact responses. Where an example-based test
says "POST this body → expect this 201 body," a property fuzzer says "for *any* input the schema permits,
the response must conform to the schema, and *no* input — however malformed — should ever produce a 500 or
an undeclared status." It finds the request you didn't think to write.

> **⚠️ Fuzzing SENDS GENERATED REQUESTS and can mutate state.** Schemathesis will `POST`/`PUT`/`PATCH`/
> `DELETE` with generated bodies — it can create, corrupt, and delete data. It is an **active** tool. Per
> the master ref's authorization-to-scan rule (`qa-<stack>:security-foundations`): **never run it against production or
> a shared environment.** Point it only at a **throwaway env you own and are authorized to attack** — a
> Testcontainers/compose-spun ephemeral app, ready on a wait strategy. Use a **seeded test tenant** and **clean up after**. See the safe-env callout
> below.

## Decision matrix — where Schemathesis property-fuzzing fits

| Need | Use | Why |
|------|-----|-----|
| **Property** checks across thousands of generated inputs from the spec (schema conformance, malformed-input 500s, status/content-type conformance) on a **running** app | **this skill (Schemathesis)** | Generative + property-based; finds the inputs you didn't write; non-zero exit → build gate |
| Deep **active attack** scan — inject SQLi/XSS/traversal payloads, crawl, attack rules | `qa-<stack>:active-scan` (DAST) | ZAP *attacks* with a payload library; Schemathesis *fuzzes from the schema* and checks conformance — different engines, different findings |
| **Example-based** functional contract / conformance ("this request → this exact response") | `qa-{stack}:api-tests` | Hand-written, deterministic, asserts business behavior on known examples — not generative |
| **BOLA / BFLA / IDOR** — does User A reach User B's object? | `qa-{stack}:permission-testing` | Authz logic; a fuzzer's requests are well-formed HTTP and it has no cross-user object map — **it cannot find BOLA** |
| Business-logic / sensitive-flow abuse (API6) | manual pentest (master ref) | Logic flaws are invisible to generators; humans only |

**Rule of thumb:** Schemathesis is your **spec-driven property fuzzer** — it proves the API behaves like its
own contract under inputs you'd never hand-write. It complements, never replaces, the ZAP active scan
(payload-based attack), example-based contract tests (known behavior), and the access-control matrix (authz
logic the fuzzer is blind to). A green fuzz run says **conformance + robustness held**; it says **nothing**
about access control or business logic.

## Setup — no embedding, it hits HTTP (CLI / Docker / Action)

Schemathesis is **language-agnostic** — it talks to the running app over HTTP and reads the spec. There is
nothing to add to your app's build; pick one of three invocations.

```bash
# 1. CLI (Python) — pin the major
pipx install "schemathesis>=4,<5"     # or: uv tool install schemathesis
schemathesis run https://app.example.com/openapi.json

# 2. Docker — no Python on the runner
docker run --rm schemathesis/schemathesis:stable \
  run http://host.docker.internal:8080/openapi.json
```

```yaml
# 3. GitHub Action — the CI-first path
- uses: schemathesis/action@v3
  with:
    schema: 'http://localhost:8080/openapi.json'
```

The schema source is a **URL** (`https://app/openapi.json`) **or a local file** (`./openapi.yaml`).
**GraphQL** is supported the same way — point at the GraphQL endpoint and Schemathesis fuzzes queries
against the introspected schema. The target is always a **running** app.

> **Container→target reachability** is the #1 Docker gotcha (same as the ZAP skill): a `localhost` target
> inside the Schemathesis container points at the *container*. Use `--network host` on Linux CI,
> `http://host.docker.internal:<port>` on Mac/Windows, or a shared Docker network + service name.

## Invocation + the selectable checks and steps

`schemathesis run <schema>` derives an operation per path×method from the spec, **generates** inputs, sends
them, and runs **checks** (the properties) on each response.

### The checks — the properties asserted

| Check | Property | Catches | OWASP |
|-------|----------|---------|-------|
| **response_schema_conformance** | the response body matches the schema declared for that status | spec drift, undocumented fields, wrong types | API9 |
| **negative_data_rejection** | malformed / boundary inputs are **rejected** (4xx), not crashed-on | validation-bypass, 500s on bad input | A05 / API4 |
| **positive_data_acceptance** | schema-valid inputs are **accepted** (not wrongly 4xx'd) | over-strict / broken validation | API9 |
| **status_code_conformance** | the response status is one the schema **declares** | undeclared 500/403/302 leaks | API9 |
| **content_type_conformance** | the `Content-Type` matches what the schema declares | wrong/missing media type | API8 |
| **not_a_server_error** | **no input** produces a 5xx | crashes on edge inputs | A05 / API4 |

Select checks with `--checks` (e.g. `--checks all` or `--checks response_schema_conformance,not_a_server_error`);
`--exclude-checks` drops one. Each failing check is a reported failure that drives the exit code.

### The steps — what gets generated

Schemathesis runs in **selectable steps**; pick with `--steps`:

| Step | What it does |
|-------|--------------|
| `examples` | replay the **examples embedded in the schema** (closest to example-based) |
| `coverage` | deterministic boundary/edge values aiming for schema **coverage** |
| `fuzzing` | property-based **generated** inputs (the core fuzzer — the thousands of cases) |
| `stateful` | chain operations via **OpenAPI links** (create→get→delete sequences) — see below |

```bash
schemathesis run https://app.example.com/openapi.json \
  --checks all \
  --steps examples,coverage,fuzzing,stateful \
  --max-examples 200 \
  --workers auto \
  --header "Authorization: Bearer $API_TOKEN" \
  --report junit
```

`--max-examples` bounds generated cases per operation (keep CI bounded); `--workers auto` parallelizes;
`--include-path` / `--exclude-path` scope to specific operations.

## The gate — non-zero exit + JUnit XML

> **The build gate is the process exit code: Schemathesis exits NON-ZERO on any detected failure.** A failed
> check (a 500 on a malformed input, a response that violates the declared schema, an undeclared status)
> fails the run, which fails the CI step. This is the same exit-code-is-the-gate model as the ZAP baseline
> skill — no extra assertion harness needed; the tool *is* the gate.

Export machine-readable results and feed them to the CI test report:

```bash
schemathesis run https://app.example.com/openapi.json \
  --report junit \                       # JUnit XML → the CI test report + Allure
  --report-junit-path reports/schemathesis-junit.xml
```

- **JUnit XML** (`--report junit`) → the pipeline's test-report surface and Allure (cross-link
  `qa-<stack>:test-reports`) — a failing run names each failing operation/check without re-running.
- **VCR cassettes** (`--report vcr`) and **HAR** (`--report har`) capture the **exact requests** for
  **repro** — attach them as CI artifacts so a confirmed finding is replayable outside CI.

## The safe-env + auth callout (defer the rule to the master ref, but state it)

**Run only against a throwaway env you own.** Per `qa-<stack>:security-foundations`'s authorization-to-scan rule, an
active tool that sends generated mutating requests must never touch prod or a shared environment. Concretely:

- **Spin an ephemeral target** — Testcontainers / `docker compose up --wait`. Wait on a **readiness condition** (healthcheck / `--wait`), never a sleep
  (global rule). Scanning before the app is ready gives false-clean or connection-error noise.
- **Use a seeded test tenant** and **clean up after** — fuzzing creates/mutates/deletes data; isolate it to
  a disposable tenant and tear it down (or recreate the env per run) so runs are independent and repeatable.

**Auth — token from env, read lazily, never committed:**

```bash
schemathesis run https://app.example.com/openapi.json \
  --header "Authorization: Bearer $API_TOKEN"       # $API_TOKEN from the environment, not the file
```

Acquire the token from `qa-{stack}:test-login-tokens` (M2M / ROPG for a seeded test user) and inject it via
an **env var read at runtime**. Never put a token in the workflow YAML, a config file, or the command line
literal (global rule: no secrets in code/config).

## Stateful testing — create→get→delete via OpenAPI links

The `stateful` step makes Schemathesis chain operations using the **OpenAPI `links`** declared in your
spec: it uses the `id` returned by `POST /resources` as the path parameter for `GET /resources/{id}` and
`DELETE /resources/{id}`, fuzzing whole **sequences** and asserting the properties hold across them
(e.g. a resource you just created is then retrievable; a deleted one then 404s).

```bash
schemathesis run https://app.example.com/openapi.json --steps stateful --checks all
```

This catches conformance failures that only appear **after** a state change (the response shape drifts on
the second call, a created resource isn't found) — exactly the create→get→delete robustness an example
test rarely exercises. It needs `links` in the spec; without them, only single-operation fuzzing runs.

## Reporting the gate — JUnit XML → CI test report + Allure

```yaml
# .github/workflows/api-fuzzing.yml — spin app → fuzz → report
name: API Fuzzing (Schemathesis)
on: [pull_request]
jobs:
  schemathesis:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - name: Start the app (throwaway env)
        run: docker compose up -d --wait          # --wait blocks on healthchecks, NOT a sleep
      - name: Schemathesis fuzz
        uses: schemathesis/action@v3
        with:
          schema: 'http://localhost:8080/openapi.json'
          args: >-
            --checks all
            --steps examples,coverage,fuzzing,stateful
            --max-examples 150
            --report junit --report-junit-path reports/schemathesis-junit.xml
        env:
          SCHEMATHESIS_HOOKS: ''
          API_TOKEN: ${{ secrets.API_TOKEN }}      # injected as env, referenced via --header in args
      - name: Publish JUnit to Allure
        if: always()
        run: cp reports/schemathesis-junit.xml allure-results/    # cross-link qa-<stack>:test-reports
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: schemathesis-report, path: reports/ }
```

The job: **spin the app** (`compose up --wait`) → **fuzz** (`schemathesis/action`, exit non-zero gates the
job) → **publish** the JUnit XML to the test report + Allure and upload the VCR/HAR repro as an artifact.
Cross-link `qa-<stack>:ci-pipelines` for the OIDC-secret + artifact wiring.

## OWASP mapping (what it covers — and what it does NOT)

| Schemathesis finding | OWASP item |
|----------------------|------------|
| Malformed/edge input → 500 or stack-trace leak (`not_a_server_error`, `negative_data_rejection`) | **A05 Injection** (malformed-input handling), **A10 Mishandling of Exceptional Conditions** |
| Boundary/large/extreme values accepted unbounded | **API4 Unrestricted Resource Consumption** |
| Wrong content-type, undeclared status, misconfigured response | **API8 Security Misconfiguration** |
| Response/spec drift, undocumented fields, schema non-conformance | **API9 Improper Inventory Management** (spec/inventory conformance) |

> **It does NOT find:** **BOLA/BFLA/IDOR** (API1/API3/API5 — authz logic; fuzzer sends well-formed HTTP with
> no cross-user object map → use `qa-{stack}:permission-testing`) or **business-logic /
> sensitive-flow abuse** (API6 — manual pentest). A green Schemathesis run is **not** "API secure." Defer
> the scanner-blind-spot framing to `qa-<stack>:security-foundations` and say so in every report.

## Anti-patterns

- **Fuzzing prod or a shared env.** It sends generated mutating requests — it will corrupt/delete data.
  *Fix:* a throwaway env you own (Testcontainers/compose), per the master ref's authorization rule.
- **No app-readiness wait** (sleep-then-fuzz, or fuzz on startup). Races startup → false-clean or
  connection-error noise. *Fix:* `compose up --wait` / a Testcontainers wait strategy — never a fixed sleep.
- **Committing the auth token** in the workflow YAML / config / CLI literal. *Fix:* env var (`$API_TOKEN`)
  read lazily, referenced via `--header`; secret from the CI secret store.
- **Treating a green fuzz run as "API secure"** while ignoring BOLA/BFLA. Conformance ≠ authorization.
  *Fix:* run `permission-testing` for authz and reserve business-logic abuse for a manual pentest.
- **No seeded test tenant / no cleanup.** Fuzz-created data bleeds across runs → flaky, non-independent
  results. *Fix:* a disposable seeded tenant; tear it down or recreate the env per run.
- **Gating on flaky generated noise without repro.** A failure on a random generated input is unactionable
  if you can't reproduce it. *Fix:* pin `--hypothesis-seed <n>` (or capture the printed seed) and keep the
  VCR/HAR cassette so the exact case replays deterministically before you gate on it.
- **Dismissing schema-conformance failures as "just the spec is wrong."** A response that violates the
  declared schema is a real defect — either the **app** drifted (a bug) or the **spec** drifted (API9
  inventory rot that breaks every consumer). *Fix:* fix one side; never blanket-suppress conformance checks.
- **`--checks` left at a single weak check.** Running only `not_a_server_error` misses conformance drift.
  *Fix:* `--checks all` and select down only with a documented reason.
- **Unbounded generation in CI.** No `--max-examples` → slow, nondeterministic runs. *Fix:* bound it; run
  the deep `--max-examples` sweep on a slower scheduled cadence.

## Rules (hard constraints)

- The gate is Schemathesis's **non-zero exit on any detected failure**; export **JUnit XML**
  (`--report junit`) into the CI test report + Allure, and keep **VCR/HAR** for repro.
- **Active tool — never fuzz prod or a shared env.** Target a **throwaway env you own**
  (Testcontainers/compose), ready on a **wait condition** (never a sleep), with a **seeded test tenant** and
  **cleanup after**. (Defers to `qa-<stack>:security-foundations`'s authorization-to-scan rule.)
- **No secrets in config:** the auth token comes from an **env var read lazily** (`--header
  "Authorization: Bearer $API_TOKEN"`), sourced from `qa-{stack}:test-login-tokens`; never committed.
- Run **`--checks all`** by default; run the **`stateful`** step when the spec declares OpenAPI `links`.
- For any gated failure, **pin `--hypothesis-seed` + keep the cassette** so it reproduces deterministically.
- Treat **schema-conformance** failures as real defects (app or spec); never blanket-suppress them.
- **A green run ≠ "API secure"** — Schemathesis is blind to **BOLA/BFLA** (use `permission-testing`)
  and **business-logic abuse** (manual pentest). Map findings to A05/API4/API8/API9; say so in reports.

## Cross-references

- `qa-<stack>:security-foundations` — the **master ref**: OWASP Top 10:2025 / API 10:2023 map, the **authorization-to-scan**
  rule this skill defers to, the triage discipline, the scanner-blind-spot framing. Load **alongside** this.
- `qa-<stack>:active-scan` — the **DAST active attack** scan (payload injection,
  crawl) — a different engine from spec-driven property fuzzing; run both.
- `qa-{stack}:permission-testing` — the functional **BOLA/BFLA/IDOR** authz matrix the
  fuzzer **cannot** find; the highest-value layer most teams miss.
- `qa-{stack}:api-tests` — **example-based** functional contract/conformance tests (hand-written,
  deterministic) — the non-generative counterpart.
- `qa-{stack}:test-login-tokens` — acquire the M2M/ROPG token (for a seeded test user) injected via
  `--header`, read lazily from env.
- `qa-<stack>:test-reports` — attach the JUnit XML + VCR/HAR repro.
- `qa-<stack>:ci-pipelines` + `qa-<stack>:ci-conventions` — wire the `schemathesis/action` job,
  OIDC secrets, artifact upload.
