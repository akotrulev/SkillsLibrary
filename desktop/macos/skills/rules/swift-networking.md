---
paths:
  - "**/*{Client,API,Api,Endpoint,Endpoints,Socket}.swift"
  - "**/{Networking,Network,API,Api}/**/*.swift"
---

<!-- desktop-macos rules v1 (2026-11-15): networking. Installed by /desktop-macos:rules; edit the paths above to where this project keeps its API client. -->

# Swift networking standards (macOS)

Severity tags as in the core Swift rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- A sandboxed app that makes any outgoing connection has `com.apple.security.network.client`, with its reason recorded. *blocker*
- One concrete client, matching the one present: no `APIClientProtocol` with one conformer "for testing" (inject a `URLProtocol`-stubbed session), no second HTTP layer, no Alamofire beside a working `URLSession`. *major*
- `https` only; no `URLSessionDelegate` that trusts every `serverTrust`; no `NSAllowsArbitraryLoads` (a per-domain exception with a reason, `NSAllowsLocalNetworking` in Debug only); no hard-coded `localhost` or LAN URL in a release configuration. The base URL is configuration, not a secret. *blocker*
- Every request has a timeout budget by endpoint class, never the seven-day default; `timedOut` fails, `cancelled` is silent. *major*
- Cancellation flows from `.task(id:)` or an owned `Task` handle tied to the window or model; no unowned `Task { }` for a request. *major*
- Wake from sleep, a network change and window reactivation revalidate through the shared model, so every window shows the same answer; a socket is closed before sleep and opened fresh after wake. *major*
- Retries live in one place: at most 2 for reads, jittered, honouring `Retry-After`; none for a write without an idempotency key; none while offline. *major*
- A decode failure is a categorised error that renders as failed; no `try?` on a decode, no `catch {}`. *major*
- A `401` triggers exactly one shared refresh (an actor), one replay, then re-auth in place; `403` is permission-denied; a third party's `401` never starts the ladder. *major*
- A write carries one idempotency key per intent; an unknown outcome is reconciled, not reported as failed. *major*
- An unsupported-app-version response shows the forced-update screen, and the check fails open; a `404` on a record is "gone", never retried. *major*
- No token, body or personal data in a log; log status, endpoint name and correlation id. *major*
- Endpoints are built by name in one place; independent calls do not wait on each other. *minor*
