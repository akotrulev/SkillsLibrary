---
name: networking
description: Use when a Mac app calls an API (URLSession async, timeouts, retries, token refresh, sandbox network entitlement, ATS). Triggers "request hangs after wake". Not for the failure UI (error-handling).
---

# macOS — Networking

Owns the **request-level half** of resilience on the Mac: how a call is made, cancelled, timed out, retried, authenticated and categorised, and how a socket lives and dies with a window and with sleep. The UI half (failed region, inline banner, stale marker) is `error-handling`'s; this skill produces the categorised error it renders. The client is the same as on iOS (`mobile-ios:networking`); the Mac adds the sandbox entitlement, App Transport Security, wake from sleep and several windows on one model. Audit rows are section H of `desktop-macos:standards-audit`.

## Version lane

| Concern | Primary | Notes |
|---|---|---|
| Transport | `URLSession` `data(for:)` / `bytes(for:)` | macOS 12+ |
| Decoding | `Codable` with a stated date and key strategy | — |
| Isolation | Client `Sendable`, results cross to `@MainActor` models | Swift 5-mode: `@Sendable` closures |
| Reachability | `NWPathMonitor`, never a ping | macOS 10.14+ |
| Wake and activation | `NSWorkspace.didWakeNotification`, `scenePhase == .active` | revalidate on both |
| Sandbox | `com.apple.security.network.client` for outgoing calls; `network.server` only for a listening socket | **[MAS]** and any sandboxed build |
| ATS | On for Mac too; an exception carries a recorded reason | — |

Detect an existing client first (Alamofire, Moya, a generated OpenAPI client, an in-house wrapper). **Match it; never add a second HTTP layer.**

## When to use

- Writing the API client, a call, an upload, a download
- A request hangs after the Mac wakes; a retry storm; a duplicate write
- Attaching a token, handling `401`, replaying once
- A call fails only in the sandboxed build ("The operation couldn't be completed", `-1003`)
- A `URLSessionWebSocketTask` or SSE stream that must survive sleep

## When NOT to use

- The failed region, banner, offline indicator, forced-update prompt → `error-handling`
- Persisting responses, an offline write queue, token storage → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Where server data lives in the view tree → [`architecture`](../architecture/SKILL.md)
- Form submit UX and field errors → [`forms`](../forms/SKILL.md)
- Auth provider setup → `auth0-macos`; ATS pinning policy, secrets → `desktop/_shared/security`
- A helper that talks to the network on the app's behalf → [`background-and-helpers`](../background-and-helpers/SKILL.md)
- iOS → `mobile-ios:networking`; Windows → `desktop-windows:networking`

## The sandbox entitlement comes first

A sandboxed app that makes **any** outgoing connection needs `com.apple.security.network.client` in the entitlements file. Without it every request fails at connect time and nothing in the response says why. Add it with the first call, record the reason beside the key in the entitlements review, and add `network.server` only for an app that listens. An XPC helper with its own sandbox profile needs its own entitlement; it does not inherit the app's.

- `http://` needs an ATS exception per domain, with a recorded reason; `NSAllowsArbitraryLoads` is a **major** finding.
- A loopback dev server is `NSAllowsLocalNetworking`, set in a Debug `.xcconfig` only.
- Local-network access (a printer, a NAS) can raise a system prompt: ask in context, and the denied path is a working screen with an **Open System Settings** link (`sandbox-and-permissions`).

## One concrete client

One type owns the session, the base URL, the budgets and the decode. **A concrete `final class`, not a protocol with one implementation**; a protocol appears when a second implementation exists (a test fake counts) and is the smallest seam the caller needs.

```swift
final class APIClient: Sendable {
    private let session: URLSession
    private let baseURL: URL
    private let tokens: TokenStore
    private let decoder = JSONDecoder.api

    init(baseURL: URL, tokens: TokenStore, session: URLSession = APIClient.makeSession()) {
        self.baseURL = baseURL
        self.tokens = tokens
        self.session = session
    }

    static func makeSession() -> URLSession {
        let configuration = URLSessionConfiguration.default
        configuration.waitsForConnectivity = false
        configuration.timeoutIntervalForRequest = 15
        configuration.timeoutIntervalForResource = 60
        return URLSession(configuration: configuration)
    }

    func send<Response: Decodable>(
        _ endpoint: Endpoint<Response>,
        endpointClass: EndpointClass = .read
    ) async throws -> Response {
        var request = try endpoint.urlRequest(relativeTo: baseURL)
        request.timeoutInterval = endpointClass.budget
        request.setValue(try await tokens.accessToken().bearerHeader, forHTTPHeaderField: "Authorization")

        let (data, response) = try await perform(request)
        guard let http = response as? HTTPURLResponse else { throw APIError.unexpected }
        guard (200..<300).contains(http.statusCode) else { throw APIError(response: http, body: data) }
        do { return try decoder.decode(Response.self, from: data) }
        catch { throw APIError.drifted(endpoint: endpoint.name) }
    }
}
```

- **The base URL comes from an `.xcconfig` value surfaced through `Info.plist`**: public by design, `https` only, no secret in it.
- **`Endpoint<Response>` is a value** (path, method, query, body, name) built in one file; no string URLs at call sites.
- **A decode failure throws `APIError.drifted`**, never `try?` into an empty array. The UI renders *failed*, not *empty*.
- **Never log a URL with a query secret, a body or a token.** Log status, endpoint name and correlation id through `os.Logger`.
- The only mutable state is the token, in the `TokenStore` actor (single-flight refresh): the pattern is `mobile-ios:networking`'s `references/request-policy.md`; the Mac stores the refresh token in the data protection keychain ([`offline-and-storage`](../offline-and-storage/SKILL.md)).

## Timeout budgets — by endpoint class

```swift
enum EndpointClass {
    case read, write, upload

    var budget: TimeInterval {
        switch self {
        case .read: 15
        case .write: 30
        case .upload: 120
        }
    }
}
```

- Without a per-request budget a call on a dead link waits `timeoutIntervalForResource` (default seven days). Set both, and keep `waitsForConnectivity = false` for user-initiated calls so an offline click fails fast.
- `URLError.timedOut` is a **failure** (render it); `CancellationError` and `URLError.cancelled` are **not**: the user closed the window or changed the query. Never notify on them.

## Cancellation — the window owns the request

```swift
struct OrdersPane: View {
    @Environment(APIClient.self) private var api
    @State private var state: LoadState<[Order]> = .loading

    var body: some View {
        OrdersTable(state: state)
            .task(id: query) { await load() }
    }

    private func load() async {
        state = .loading
        do { state = .loaded(try await api.send(.orders(query))) }
        catch is CancellationError { return }
        catch let error as URLError where error.code == .cancelled { return }
        catch { state = .failed(AppError(error)) }
    }
}
```

- `.task(id:)` cancels the previous request when the key changes **and when the window closes**, so a slow answer for a replaced query never overwrites a newer one. A hand-rolled `Task { }` stores its handle and cancels it in `onDisappear` / `deinit`.
- A background failure (a refresh nobody asked for) never raises a modal alert; it marks the region stale and shows the inline banner.

## Retries — bounded, polite, never offline

| Situation | Rule |
|---|---|
| Idempotent read failing with a network error, `408`, `429`, `502`, `503`, `504` | up to **2** retries, exponential backoff with jitter |
| `429` / `503` with `Retry-After` | wait exactly that, capped; never sooner |
| Write (`POST` / `PATCH`) | retried **only** with an `Idempotency-Key` the server honours, generated once per user intent |
| Other `4xx` | never retry |
| **Offline** (`NWPath.status != .satisfied`) | no retry: fail fast, or queue ([`offline-and-storage`](../offline-and-storage/SKILL.md)) |
| Repeated failures on one endpoint | open a circuit for a cool-down, then one probe |

Retries live in **one** place (`perform` in the client).

## Revalidate on wake, activation and reconnect

A Mac sleeps with the lid shut and the app open; every held connection is dead on wake and every cached read may be stale. Three triggers call the same `load()`:

```swift
@Observable
final class Connectivity {
    private(set) var isOnline = true
    private let monitor = NWPathMonitor()

    init() {
        monitor.pathUpdateHandler = { [weak self] path in
            Task { @MainActor in self?.isOnline = path.status == .satisfied }
        }
        monitor.start(queue: DispatchQueue(label: "Connectivity"))
    }

    deinit { monitor.cancel() }
}
```

- Window reactivation: `.onChange(of: scenePhase) { _, phase in if phase == .active { … } }`.
- Wake: observe `NSWorkspace.shared.notificationCenter` for `NSWorkspace.didWakeNotification` once, in the app-wide model; **wait for `isOnline`** before the revalidate (the radio takes seconds).
- Reconnect: `.onChange(of: connectivity.isOnline)`.
- **One model, several windows**: the revalidate updates the shared model, so every window shows the same answer. A write in one window never leaves another on old data.

## Realtime — `URLSessionWebSocketTask`

Open while a window needs it, cancel when the last window that needs it closes, and **cancel on `NSWorkspace.willSleepNotification`**: the socket is dead on wake anyway. Reconnect with jittered backoff only when `isOnline`, and **revalidate what the stream feeds** after every reconnect (messages were missed). Receive in one `Task` cancelled with its owner; decode each frame like any response and drop-and-count a malformed one. An app that must hear while closed uses a push or a login-item helper ([`background-and-helpers`](../background-and-helpers/SKILL.md)), not a held-open socket.

## Downloads and uploads

A large transfer that must outlive the window uses a background `URLSession` (`URLSessionConfiguration.background(withIdentifier:)`) owned by the app-wide model; the user can quit and the system finishes it. Write the result into the sandbox container, not a user folder. A destination the user picked is written through its security-scoped bookmark (`sandbox-and-permissions`).

## Rules

Standards come from the desktop-macos rule files in `.claude/rules/desktop-macos/` (`/desktop-macos:rules` installs them), or the plugin's copies when the project has none; CLAUDE.md § Desktop code rules wins where they differ.

## Generation steps

1. Read the existing client and token handling; detect Swift mode and deployment target; check the entitlements file for `network.client`.
2. Define endpoint classes and budgets; write or extend `APIClient`, `Endpoint`, `APIError`.
3. Put retry, `Retry-After` and the circuit in `perform`; add `Connectivity` and the wake observer to the app-wide model.
4. Add the `TokenStore` actor with single-flight refresh.
5. Write feature calls as `Endpoint` values; load from `.task(id:)`; map `APIError` for `forms` and `error-handling`.
6. Realtime: open and cancel with the owning window; cancel on sleep; revalidate on reconnect.
7. Tests: `URLProtocol` stub or a fake of the one-method seam, injected clock for backoff (`unit-testing`).

## Validation

- A sandboxed build makes a call and succeeds; removing `network.client` makes it fail, and the failure is visible in the failed state.
- Network Link Conditioner at 100% loss: a request fails at its deadline; closing the window cancels silently.
- Sleep and wake the Mac with a window open: one revalidate runs after `isOnline`, every window shows new data.
- A `503` with `Retry-After: 5` retries after 5 s; N concurrent `401`s cause one refresh.

## Common gotchas

- **Every request fails only in the release build**: `network.client` missing from the sandbox entitlements.
- **A stale list after wake**: the app revalidated on activation only, and the Mac woke with the window already active.
- **A socket that "reconnects" with a dead task**: cancel before sleep, open a new task after.
- **`NSAllowsArbitraryLoads` to fix one HTTP host**: a per-domain exception with a reason instead.
- **Retrying in the view model** on top of the client: attempts multiply.
- **`try?` around decode**: drift becomes an empty table.

## Handoffs

- Failed region, banner, stale, forced update → `error-handling`
- Cache, write queue, token storage → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- State ownership → [`architecture`](../architecture/SKILL.md) · field errors → [`forms`](../forms/SKILL.md)
- Entitlements, permissions → [`sandbox-and-permissions`](../sandbox-and-permissions/SKILL.md)
- ATS, pinning, secrets → `desktop/_shared/security`
- API contract tests → `qa-api-typescript` / `qa-api-dotnet` / `qa-api-java`
- iOS counterpart → `mobile-ios:networking`
