---
name: mobile-ios-networking
description: Use when an iOS app must call an API — URLSession async/await + Codable, one concrete client, timeout budgets per endpoint class, Task cancellation, bounded retries with Retry-After, no retry offline, ProblemDetails, a token-refresh actor, URLSessionWebSocketTask. Triggers "request hangs on cell", "retry storm", "refresh token race". Do NOT use for the failure UI (`mobile-ios-error-handling`), forms, or persistence (`-offline-and-storage`).
---

# iOS — Networking

Owns the **request-level half** of resilience: how a call is made, cancelled, timed out, retried, authenticated and categorised, and how a socket lives and dies with the app. The **UI half** (failed region, banner, stale marker, retry button) is `mobile-ios-error-handling`'s; this skill produces the categorised error it renders. Web analog: [`fe-react-data-fetching`](../../../../frontend/react/skills/data-fetching/SKILL.md) — the timeout, ordering and critical-vs-optional rules carry over; RSC, Server Actions and cache tags do not.

## Version lane

| Concern | Primary (Swift 6.2+, iOS 17+) | `[iOS16]` / Swift 5 mode |
|---|---|---|
| Transport | `URLSession` with `data(for:)` / `bytes(for:)` async APIs | Same (available since iOS 15) |
| Decoding | `Codable` + `JSONDecoder` with a stated date and key strategy | Same |
| Isolation | The client is `nonisolated` and `Sendable` (a final class with immutable state, or an actor); results cross to `@MainActor` models | Same; `@Sendable` closures instead of region isolation where Swift 5 mode |
| Cancellation | `Task` cancellation throws `CancellationError` / `URLError.cancelled`; `.task` cancels with the view | Same |
| Streaming | `URLSession.bytes(for:)` → `AsyncBytes.lines` for SSE | Same |
| Typed throws | Optional (Swift 6); an `APIError` enum thrown through untyped `throws` is fine | Same |
| Reachability | `NWPathMonitor` (Network framework), never a ping | Same |

Detect an existing client first (Alamofire, Moya, a generated OpenAPI client, an in-house wrapper) — **match it; never add a second HTTP layer.** Those are lanes, not defects.

## When to use

- Writing the API client or a call against it, an upload, a download
- A request hangs on a bad cell link; a retry storm; a duplicate write
- Attaching a token, handling `401`, replaying once
- Refetching on foreground and on reconnect
- A `URLSessionWebSocketTask` or SSE stream that must pause in the background

## When NOT to use

- Rendering failure, the banner, offline indicator, forced-update prompt → `mobile-ios-error-handling`
- Persisting responses, an offline write queue, sync and conflicts → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Where server data lives in the view tree → [`architecture`](../architecture/SKILL.md)
- Form submit UX and field errors → [`forms`](../forms/SKILL.md)
- Auth provider setup (Universal Login, `CredentialsManager`) → `auth-auth0-ios`; token storage → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Registering a device token with the server → `mobile-ios-notifications-and-links`
- Background uploads that outlive the app → `mobile-ios-system-integration`
- Another stack → `mobile-react-native-networking`, `mobile-android-networking`

## One concrete client

One type owns the session, the base URL, the budgets and the decode. **It is a concrete `final class`, not a protocol with one implementation.** A protocol appears the day a second implementation exists — a test fake counts — and then it is the *smallest* seam the caller needs (often one method), not a mirror of the whole client.

```swift
final class APIClient: Sendable {
    private let session: URLSession
    private let baseURL: URL
    private let tokens: TokenStore
    private let decoder: JSONDecoder

    init(baseURL: URL, tokens: TokenStore, session: URLSession = APIClient.makeSession()) {
        self.baseURL = baseURL
        self.tokens = tokens
        self.session = session
        self.decoder = JSONDecoder.api
    }

    static func makeSession() -> URLSession {
        let configuration = URLSessionConfiguration.default
        configuration.waitsForConnectivity = false
        configuration.timeoutIntervalForRequest = 15
        configuration.timeoutIntervalForResource = 60
        configuration.requestCachePolicy = .useProtocolCachePolicy
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

- **The base URL comes from an `.xcconfig` value surfaced through `Info.plist`** — it is public by design; no secret rides in it. `https` only; an ATS exception carries a recorded reason ([`mobile-shared-security`](../../../_shared/security/SKILL.md) § 1).
- **`Endpoint<Response>` is a value** (path, method, query, body, name) built by name in one file — no string URLs at call sites, and a route table that fails a test when a `{placeholder}` is left unsubstituted.
- **A decode failure throws `APIError.drifted`** — never `try?` into an empty array. A single-object endpoint is not decoded as a list. The UI renders *failed*, not *empty*.
- **Never log a URL with a query secret, a body, or a token**; log status, endpoint name and the correlation id through `os.Logger` with `privacy: .public` only on those.
- The client is `Sendable`; it holds no mutable state. The one piece of mutable state — the current token — lives in the `TokenStore` actor below.

The categorised `APIError`, the retry loop, the token actor, ProblemDetails mapping and the socket wrapper are in [`references/request-policy.md`](references/request-policy.md).

## Timeout budgets — by endpoint class, in one table

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

- **A request on a dying cell link otherwise waits as long as `timeoutIntervalForResource`** (default seven days). Set both `timeoutIntervalForRequest` (idle) and a per-request `timeoutInterval`, and keep `waitsForConnectivity = false` for user-initiated calls so an offline tap fails fast; `true` is for background transfers only.
- Budgets are **longer than web's** and are set here, never at call sites.
- `URLError.timedOut` is a **failure** (render the timeout body); `CancellationError` / `URLError.cancelled` is **not** — the user left. Never notify on it.

## Cancellation — the view owns the request

```swift
struct OrdersView: View {
    @Environment(APIClient.self) private var api
    @State private var state: LoadState<[Order]> = .loading

    var body: some View {
        OrdersList(state: state)
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

- **`.task(id:)` cancels the previous request when the key changes**, so a slow answer for a replaced query can never overwrite a newer one. A hand-rolled `Task { }` stores the handle and cancels it in `onDisappear` / `deinit`.
- **Child work inherits cancellation**; `async let` and `TaskGroup` cancel their children. A detached task does not — avoid `Task.detached` for requests.
- A `catch` that swallows `CancellationError` into `.failed` shows a failure banner every time the user scrolls away.

## Retries — bounded, polite, never offline

| Situation | Rule |
|---|---|
| Idempotent read (`GET`) failing with a network error, `408`, `429`, `502`, `503`, `504` | up to **2** retries, exponential backoff with jitter |
| `429` / `503` with `Retry-After` | wait **exactly that** (seconds or HTTP date), capped; never sooner |
| Write (`POST` / `PATCH`) | retried **only** with an `Idempotency-Key` the server honours; otherwise never |
| `4xx` other than `408` / `429` | never retry — the caller's bug or the user's input |
| **Device offline** (`NWPath.status != .satisfied`) | **no retry at all** — fail fast, or queue ([`offline-and-storage`](../offline-and-storage/SKILL.md)) |
| Repeated failures on one endpoint | open a circuit: stop for a cool-down, then one probe; surface *failed*, not a spinner |

Retries live in **one** place (`perform` in the client, [`references/request-policy.md`](references/request-policy.md)). A retry inside a view model or a call site on top of it multiplies attempts. Retries cost battery and data; **an idempotency key is generated once per user intent** (per draft or per tap-sequence), not per attempt.

## Foreground and reconnect

The app revalidates when it returns to the foreground and when the network returns — `error-handling` shows it, networking triggers it:

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

A view revalidates with `.onChange(of: scenePhase) { _, phase in if phase == .active { … } }` and `.onChange(of: connectivity.isOnline)`; both call the same `load()`. Pull-to-refresh (`.refreshable`) is the canonical manual refetch — a failed pull keeps the list and marks it stale.

## Ordering and critical vs optional

- **Key a reload by every parameter it depends on** (`.task(id: QueryKey(search:filters:page))`).
- **Classify each call critical or optional**: `async let` / `TaskGroup` with a thrown error only for calls critical together; `Result`-capturing children (`group.addTask { await Result { … } }`) the moment one is optional, and render the partial result.
- A dependent call runs inside the first one's `do` block, not behind a flag that spins when its parent failed.
- **Pagination**: load the next page when the last row's `.onAppear` / `.task` fires; cancel on key change; never fetch all pages up front.
- **Mutations** disable their control while pending, carry the idempotency key, and refresh or patch precisely the state they change.

## Realtime — `URLSessionWebSocketTask`

Pull above; push is a socket the app opens **only while foregrounded and the screen needs it.** Open on `scenePhase == .active`, cancel on `.background` (iOS suspends idle sockets anyway), reconnect with jittered backoff only when `isOnline`, and **revalidate what the stream feeds** after every reconnect — messages were missed. Receive in one `Task` that is cancelled with its owner; decode each frame like any response and drop-and-count a malformed one. Background delivery is push (`mobile-ios-notifications-and-links`), not a held-open socket. The wrapper is in [`references/request-policy.md`](references/request-policy.md).

## Rules

- One concrete client; a protocol only with a second implementation; match an existing client.
- `https` only; the base URL is configuration, not a secret; no `URLSessionDelegate` that trusts every `serverTrust`.
- A budget on every request by endpoint class; `timedOut` fails, `cancelled` is silent.
- Cancellation flows from `.task(id:)` / owned `Task` handles; no unowned `Task { }` for a request.
- Retries ≤ 2 for reads, jittered, honouring `Retry-After`; none for writes without an idempotency key; none while offline; one place.
- Decode failure is `drifted` and renders as failed.
- `401` triggers exactly one shared refresh (an actor), then one replay, then re-auth in place.
- Sockets closed on background and on owner exit.
- No token, body or PII in logs.

## What NOT to do

- No request with the default seven-day resource timeout; no `Thread.sleep` / `DispatchSemaphore` waiting on a request.
- No `DispatchQueue.main.async` after a request — return to `@MainActor` by isolation.
- No `try?` on a decode; no `catch {}`; no `localizedDescription` rendered.
- No `Alamofire` added to a project that has `URLSession` working; no second client beside the one present.
- No protocol `APIClientProtocol` with one conformer "for testing" — inject the session (`URLProtocol` stub) or a one-method seam when the fake exists.
- No `NSAllowsArbitraryLoads`; no hardcoded `localhost` / LAN URL in a release configuration.
- No retry on a `POST` without an idempotency key; no fixed-interval retry without jitter.
- No socket opened in `body` or left open in the background.

## Generation steps

1. Read the existing client, token handling and `Endpoint` style; detect Swift mode and deployment target.
2. Define endpoint classes and budgets; write or extend `APIClient`, `Endpoint`, `APIError`.
3. Put retry, `Retry-After` and the circuit in `perform`; add the `Connectivity` observer.
4. Add the `TokenStore` actor and single-flight refresh ([`references/request-policy.md`](references/request-policy.md)).
5. Write feature calls as `Endpoint` values; load from `.task(id:)`; map `APIError` for [`forms`](../forms/SKILL.md) and `error-handling`.
6. Realtime: open and cancel the socket with `scenePhase`; revalidate on reconnect.
7. Add tests with a `URLProtocol` stub or a fake of the one-method seam.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Build clean with warnings as errors; the project's `swift-format` / SwiftLint pass.
- On a device with the Network Link Conditioner on "100% loss": a request past its budget fails at the deadline with a timeout; leaving the screen cancels silently.
- Airplane mode: no retry attempts in the network log; reconnect refetches.
- A `503` with `Retry-After: 5` retries after 5 s, not sooner; N concurrent `401`s cause exactly one refresh.
- Dev-side tests (`URLProtocol` stub, injected clock for backoff): [`mobile-ios-unit-testing`](../unit-testing/SKILL.md).

## Handoffs

- Failed region, banner, stale, forced update → `mobile-ios-error-handling`
- Persisted cache, write queue, token storage → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- State ownership → [`architecture`](../architecture/SKILL.md) · field errors → [`forms`](../forms/SKILL.md)
- ATS, pinning, secrets → [`mobile-shared-security`](../../../_shared/security/SKILL.md)
- API contract tests → `qa-api-typescript` / `qa-api-dotnet` / `qa-api-java` (peer of the backend)
