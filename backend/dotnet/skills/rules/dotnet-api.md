---
paths:
  - "**/*{Controller,Endpoints}.cs"
  - "**/{Controllers,Endpoints}/**/*.cs"
---

<!-- be-dotnet rules v1 (2026-11-03): HTTP API. Installed by /be-dotnet:rules; edit the paths above to where this project maps its endpoints. -->

# ASP.NET Core API standards

Severity tags as in the core .NET rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- A controller action or endpoint is transport only: it calls an application service and never touches the `DbContext`. Logic in an action is the defect. *major*
- Request input is validated at the boundary (FluentValidation, DataAnnotations or an endpoint filter). *major*
- An EF entity is never bound as a request body or returned as a response. *major*
- Errors are `ProblemDetails`, mapped by one global exception handler, not a `try`/`catch` per action; no `ex.Message` or stack trace reaches the caller. *major*
- Status codes are honest: no 200 with an error payload, no 500 for a validation failure. *major*
- Collection endpoints page with a maximum page size. *major*
- A write clients may retry is idempotent (an idempotency key or a natural-key guard). *major*
- Long work is queued, not run inside the request. *major*
- Authorization is a named policy (`[Authorize(Policy = …)]`, `RequireAuthorization`), never `IsInRole` or claim-string branching in a handler; every non-public endpoint names the policy it needs. *major*
- `[AllowAnonymous]` only on health, metrics and discovery; health endpoints exist and are anonymous. *major; minor for a missing health endpoint*
- The contract is documented with OpenAPI. *minor*
