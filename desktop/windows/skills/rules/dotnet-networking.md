---
paths:
  - "**/*{Client,Api,Endpoint,Endpoints,Socket,Gateway}.cs"
  - "**/{Networking,Network,Api,Http,Clients}/**/*.cs"
---

<!-- desktop-windows rules v1 (2026-11-15): .NET networking. Installed by /desktop-windows:rules; edit the paths above to where this project keeps its API code. -->

# .NET networking standards (desktop)

Severity tags as in the core C# rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- `HttpClient` only through `IHttpClientFactory` typed clients; never `new HttpClient()` per call, never a static one without a `PooledConnectionLifetime`. *major*
- Every request sits inside a timeout budget (`HttpClient.Timeout` or a linked `CancellationTokenSource`). *major*
- Every client method takes and passes a `CancellationToken`; a closing window cancels it. *major*
- ProblemDetails is read once into a typed failure; user text comes from the failure kind, never the server string. *major*
- Only idempotent requests retry, with capped backoff and jitter, and `Retry-After` is honoured; a POST never retries without an idempotency key. *major*
- One token refresh is in flight at a time; a second `401` signs out; tokens never reach URLs, logs or settings. *blocker*
- A malformed or unparseable body is a failed state, never an empty one; deserialization failures name the path and keep the body for the log. *major*
- TLS only; no `ServerCertificateCustomValidationCallback` that returns `true`, no `http://` without a recorded reason. *blocker*
- Offline is told apart from a server error and offers no retry loop; the window revalidates on activation, resume from sleep and connectivity change. *major*
- A `ClientWebSocket` reconnects with capped backoff, closes with the window and delivers to the UI batched. *major*
- Socket and server messages are untrusted input: parsed to a typed model, bounded in size, never executed or used as a path. *major*
