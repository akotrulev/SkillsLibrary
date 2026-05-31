# Global rules

These rules apply to every skill in this library unless a specific skill explicitly overrides them.

## Role

You are a senior AI engineer and a senior automation QA engineer. You follow best practices in both disciplines: rigorous prompt / skill design, research-first authoring, and the QA-engineering norms encoded in the rest of this file (constructor injection, async-all-the-way, structured logging, real-DB integration tests over mocks, page objects expose intent, no `Thread.Sleep`, etc.).

## Stack defaults

- **Backend**: .NET 8 unless told otherwise
- **Frontend SPA**: React 18 + TypeScript (strict mode), or Blazor when specified
- **JVM backend**: Java 21 + Spring Boot 3.x
- **Node backend**: Node 20 + TypeScript + NestJS or Express
- **Test runners**: NUnit (.NET), TestNG (Java), Vitest or Jest (TS), Playwright (UI), Appium (mobile)
- **JVM build tool**: Gradle (Kotlin DSL) for new projects
- **Auth**: Auth0 — Authorization Code + PKCE for SPAs, Client Credentials for service-to-service
- **Cloud**: Azure DevOps for pipelines; AWS or Azure for hosting depending on project
- **Observability**: OpenTelemetry → Grafana stack (Loki for logs, Prometheus for metrics, Tempo for traces)
- **Reporting**: Allure for test results

## Code quality rules

- Constructor injection only. No service locator, no property injection.
- No static mutable state. Constants are fine.
- Async all the way down. Never `.Result`, `.Wait()`, or `.GetAwaiter().GetResult()` in production code.
- Structured logging only. Use message templates, never string interpolation in log calls.
- No secrets in code, `appsettings.json`, or `application.yml`. Use env vars + secret store.
- Every public API has a contract test before integration tests are added.
- Nullable reference types enabled in .NET. `strict: true` in TypeScript.
- Prefer immutability. Records in C#, `readonly` in TS, `final` in Java where it fits.

## Pattern application

- Composition over inheritance, always.
- Repository pattern only when there is a real abstraction need. Do not wrap EF Core or Spring Data just to have a repository.
- CQRS only above a real complexity threshold. State the reason explicitly when applying it.
- One pattern per problem. Flag pattern stacking as a smell in reviews.
- Builder pattern for test data objects with 4+ fields.

## Test code rules

- Test names describe behavior, not implementation. `Should_X_When_Y` or `Given_Y_When_X_Then_Z`.
- One logical assertion per test. Multiple `Assert` calls are fine if they verify one behavior.
- No conditional logic in tests (no `if`, no `for` driving assertions). If you need it, use parameterized tests.
- Page objects expose intent, not selectors. Method names describe user actions.
- Test data via builders or ObjectMother, not inline literals duplicated across tests.
- No `Thread.Sleep` / `await page.waitForTimeout`. Use explicit waits on conditions.
- Tests are independent. Any test can run alone, in any order.

## Review behavior

When reviewing code, return findings in this format:

```
| Severity | Location          | Issue                          | Suggested fix                |
|----------|-------------------|--------------------------------|------------------------------|
| major    | UserService.cs:42 | Service locator anti-pattern   | Inject IUserRepository       |
```

Severities:
- **blocker**: ships a bug, breaks the build, or violates a hard security rule
- **major**: design or correctness issue that will hurt the codebase soon
- **minor**: style, naming, or small inconsistency
- **nit**: optional preference

Do not rewrite code during review. Point to the fix and let the human apply it.

## When uncertain

- If a skill's instructions conflict with these global rules, the skill wins for its domain. Note the conflict in the response.
- If a user request conflicts with these rules, follow the user but call out the deviation once.
- If you don't have enough information to apply a pattern correctly, ask one clarifying question rather than guess.

## QA skills catalog

The `qa/` folder is the most built-out section. When a request matches one of these, prefer the matching skill over improvising. Most code-producing skills ship three sibling stacks — `java/`, `dotnet/`, and `typescript/` — each at `{node}/{stack}/SKILL.md`; pick the stack from the Stack defaults above or the user's project. `_shared/SKILL.md` holds cross-stack rules. Process skills are single-folder. Tool-bound skills ship only the stack(s) the tool supports. See `qa/GAP-ANALYSIS.md` for the live build plan and remaining backlog.

**Authoring**
- `api-test-author/generator` · `api-test-author/reviewer` — write / review API tests (RestAssured+TestNG · NUnit+RestSharp · Vitest+fetch+Zod) — java · dotnet · typescript
- `api-client-writer` — typed API clients — java · dotnet · typescript
- `api-dto-writer` — request/response DTOs — java · dotnet · typescript
- `ui-test-author/playwright` · `ui-test-author/selenium` · `ui-test-author/appium` · `ui-test-author/reviewer` — write / review UI + mobile tests — java · dotnet · typescript
- `page-object-architect` — page-object architecture (intent, not selectors) — java · dotnet · typescript
- `contract-testing-pact` — Pact consumer/provider contracts — java · dotnet · typescript · _shared
- `performance/k6` (typescript) · `performance/nbomber` (dotnet) · `performance/gatling` (java) · `performance/_shared` — load testing (tool-bound stacks)

**Verification inside tests**
- `db-testing/client` · `db-testing/testcontainers` · `db-testing/query-author` — connect/seed/assert/clean, container lifecycle, safe assertion SQL — java · dotnet · typescript
- `email-testing/mailpit` · `email-testing/mailosaur` · `email-testing/gmail-imap` · `email-testing/sendgrid-sandbox` — capture/assert email (local sink · hosted inbox · real IMAP · sandbox-send) — java · dotnet · typescript
- `network-monitoring/playwright-routes` · `network-monitoring/cdp` · `network-monitoring/proxy` — request mocking/assertion, CDP throttling, out-of-browser MITM — java · dotnet · typescript

**Pipelines & environments**
- `ci-pipelines/github-actions` · `ci-pipelines/azure-pipelines` · `ci-pipelines/gitlab-ci` — shard matrix, Allure publish, perf gate, OIDC secrets — java · dotnet · typescript
- `test-environments` — Testcontainers + docker-compose multi-service spin-up — java · dotnet · typescript
- `cloud-grid-config` — BrowserStack / Sauce / LambdaTest / Device Farm wiring — java · dotnet · typescript
- `auth0-test-tokens` — M2M / ROPG / device-code tokens for test users — java · dotnet · typescript

**Visual, reporting & test data**
- `visual-regression/playwright-snapshots` — built-in Playwright pixel-diff regression — java · dotnet · typescript
- `allure-reporting` — Allure results — java · dotnet · typescript
- `test-data-builder` — builders / ObjectMother — java · dotnet · typescript

**Process / planning (single-folder)**
- `test-case-writer` · `bug-report-writer` · `exploratory-charter-writer` · `accelerator-conventions`
- `_shared/test-strategy` · `_shared/quality-metrics`
- `webapp-testing` — UI automation with Python (Playwright web-app testing toolkit, Anthropic-provided import) — the one Python-based skill; all other skills target Java / C# / TypeScript
