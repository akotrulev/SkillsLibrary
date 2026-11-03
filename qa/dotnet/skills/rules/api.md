---
paths:
  - "**/*{ApiTests,IntegrationTests}/**/*.cs"
  - "**/TestCore/**/{Http,Clients}/**/*.cs"
---

<!-- qa-dotnet rules v1 (2026-11-03): API tests. Installed by /qa-dotnet:rules; edit the paths above to where this project keeps its API suites. -->

# .NET API test standards (RestSharp, Playwright APIRequest)

Severity tags as in the core rules. The codebase wins where it consistently does otherwise.

- Every request goes through a typed `{Resource}Client` on the suite's base client: no `new RestClient`, `HttpClient` or raw `context.GetAsync` in a test, and one HTTP stack per suite. *major*
- A client takes its token in the constructor (`string.Empty` for anonymous) and never mints one; tokens are cached per fixture. *major*
- An endpoint with a body has a raw overload (no deserializing) and a typed one (`HttpStatusCode expected`) that calls it, asserts and returns the DTO. Bodies are DTOs, not `object`. No `try`/`catch` in a client. *major*
- DTOs: one per file, `[JsonPropertyName]` on every property, defaults over nullable, `DateTimeOffset` for dates, no methods or validation. *minor*
- The exact status is asserted first as an `HttpStatusCode`: never `response.Ok`, "any 4xx" or a raw integer. *major; minor for the integer*
- A happy path calls the typed overload, does not re-assert the status, checks the echoed and server-set fields, and reads back what it wrote. *major*
- A 400/404/422 test calls the raw overload, attaches the body, then asserts the `ProblemDetails`; only a 401 is a lone status check, with no deserializing. *major*
- Every endpoint has a test without a token that asserts `401`. *major*
- Bodies are read as DTOs through the suite's `Deserialize<T>`, never `JsonSerializer.Deserialize`, `JsonNode` or dictionaries in a test. *major*
- Playwright `APIRequest`: one lifecycle (`BasePlaywrightApiTest`, `ParallelScope.Self`), identity set on the context, contexts from `NewContextAsync` disposed by the base, `FailOnStatusCode` off. *major*
- GraphQL: the client returns the envelope, never throws; assert `errors` by code and path, pass variables separately, never interpolated. gRPC: assert the `StatusCode` and rich error details, never an HTTP status. *major*
- Explicit local types, no `var`; a client variable is named for its type (`orderClient`), never `client`. *minor*
