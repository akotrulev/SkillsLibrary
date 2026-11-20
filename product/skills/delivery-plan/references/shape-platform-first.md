# Sequencing shape: platform-first

The layered shape, read when `SKILL.md` Step 2 selects it: a service or platform with no single user journey at stake, where several areas land together and the consumer is another system. The same tasks run in layer order, completed across every area.

| Order | Tasks |
|---|---|
| First | Human-blocked provisioning from `integrations.md` |
| Then | Scaffold, project layout, config + validation, CI skeleton |
| Then | Migrations, in their stated order |
| Then | The telemetry base: SDK wiring, the local Grafana stack, a RED dashboard (`observability-engineer-<stack>`) |
| Then | Auth wiring, error middleware, shared DTOs, which every later task depends on |
| Then | Every endpoint routed as a `501 not-implemented` stub and the OpenAPI asset generated from it; the app shell with a placeholder per screen route, where there are screens |
| Then | The `TD` tasks: the test plan per epic, then the test-case suites per story |
| Then | The `Q` tasks: API acceptance tests per resource group, journey tests per journey, red on the stubs |
| Then | One task per resource: entity → persistence → service → endpoint bodies → unit tests, turning that resource's `Q` tests green |
| Then | External clients, webhook handlers, background jobs, one per dependency |
| Last | Rate limiting, business dashboards and alert rules, performance; then the gate task; then **the documentation task** (`DOC1`, the documenter agent) |

Test-first costs this shape one more layer before the first resource task: the stubs and the `Q` tasks.
