---
paths:
  - "**/*{Client,API,Api,Endpoint,Endpoints,Socket}.swift"
  - "**/{Networking,Network,API,Api}/**/*.swift"
---

<!-- mobile-ios rules v1 (2026-11-03): networking. Installed by /mobile-ios:rules; edit the paths above to where this project keeps its API client. -->

# Swift networking standards

Severity tags as in the core Swift rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- One concrete client, matching the one present: no `APIClientProtocol` with one conformer "for testing" (inject a `URLProtocol`-stubbed session), no second HTTP layer, no Alamofire beside a working `URLSession`. *major*
- `https` only; no `URLSessionDelegate` that trusts every `serverTrust`; no hard-coded `localhost` or LAN URL in a release configuration. The base URL is configuration, not a secret. *blocker*
- Every request has a timeout budget by endpoint class, never the seven-day default; `timedOut` fails, `cancelled` is silent. *major*
- Cancellation flows from `.task(id:)` or an owned `Task` handle; no unowned `Task { }` for a request; no `DispatchQueue.main.async` after one. *major*
- Retries live in one place: at most 2 for reads, jittered, honouring `Retry-After`; none for a write without an idempotency key; none while offline. *major*
- A decode failure is a categorised error that renders as failed; no `try?` on a decode, no `catch {}`. *major*
- A `401` triggers exactly one shared refresh (an actor), one replay, then re-auth in place; `403` is permission-denied; a third party's `401` never starts the ladder. *major*
- A write carries one idempotency key per intent; an unknown outcome is reconciled, not reported as failed. *major*
- An unsupported-app-version response shows the forced-update screen, and the check fails open; a `404` on a record is "gone", never retried. *major*
- Sockets close on background and on owner exit; foreground and reconnect revalidate. *major*
- No token, body or personal data in a log. *major*
- Endpoints are built by name in one place; reads off the critical path do not fail the screen, and independent calls do not wait on each other. *minor*
