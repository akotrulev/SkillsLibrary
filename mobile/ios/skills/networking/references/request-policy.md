# Request policy — error, retry, token actor, ProblemDetails, socket

Read when writing `perform`, `APIError`, the refresh path or a realtime wrapper. Samples follow CLAUDE.md § KISS: concrete types, no protocol until a second implementation exists.

## 1. The categorised error

One enum the UI renders and the forms map. Cases name the *kind* of failure, never carry a raw server string to the screen.

```swift
enum APIError: Error {
    case offline
    case timedOut
    case unauthorized
    case notFound
    case conflict
    case invalid(ProblemDetails)
    case throttled(retryAfter: Duration?)
    case server(status: Int)
    case drifted(endpoint: String)
    case unexpected

    init(response: HTTPURLResponse, body: Data) {
        switch response.statusCode {
        case 401: self = .unauthorized
        case 404: self = .notFound
        case 409: self = .conflict
        case 422, 400: self = .invalid(ProblemDetails(body: body))
        case 429, 503: self = .throttled(retryAfter: response.retryAfter)
        case 500...: self = .server(status: response.statusCode)
        default: self = .unexpected
        }
    }

    var isRetryableRead: Bool {
        switch self {
        case .timedOut, .throttled, .server(status: 502), .server(status: 504): true
        default: false
        }
    }

    var retryAfter: Duration? {
        if case .throttled(let retryAfter) = self { retryAfter } else { nil }
    }
}

extension HTTPURLResponse {
    var retryAfter: Duration? {
        guard let value = value(forHTTPHeaderField: "Retry-After") else { return nil }
        if let seconds = Int(value) { return .seconds(seconds) }
        guard let date = HTTPDateFormat.date(from: value) else { return nil }
        return .seconds(max(0, date.timeIntervalSinceNow))
    }
}
```

`URLError` maps at one place: `.notConnectedToInternet`, `.networkConnectionLost`, `.dataNotAllowed` → `.offline`; `.timedOut` → `.timedOut`; `.cancelled` is re-thrown as `CancellationError`, never wrapped.

## 2. ProblemDetails (RFC 9457)

```swift
struct ProblemDetails: Decodable, Equatable {
    let type: String?
    let title: String?
    let status: Int?
    let errors: [String: [String]]?
    let traceId: String?

    init(body: Data) {
        self = (try? JSONDecoder().decode(ProblemDetails.self, from: body))
            ?? ProblemDetails(type: nil, title: nil, status: nil, errors: nil, traceId: nil)
    }

    init(type: String?, title: String?, status: Int?, errors: [String: [String]]?, traceId: String?) {
        self.type = type; self.title = title; self.status = status
        self.errors = errors; self.traceId = traceId
    }
}
```

`errors` is what [`forms`](../../forms/SKILL.md) maps onto fields. `title` and `detail` are **log material**, not user copy — the screen shows a localized string chosen by the *case*. `traceId` goes to `os.Logger` and into the "report a problem" payload.

## 3. `perform` — the one place that retries

```swift
extension APIClient {
    func perform(_ request: URLRequest, attempt: Int = 0) async throws -> (Data, URLResponse) {
        do {
            let (data, response) = try await session.data(for: request)
            if let http = response as? HTTPURLResponse, http.statusCode == 401 {
                try await tokens.refreshAfterRejection(of: request)
                return try await session.data(for: request.authorized(by: tokens))
            }
            return (data, response)
        } catch let error as URLError {
            throw try await retryOrThrow(map(error), request: request, attempt: attempt)
        }
    }

    private func retryOrThrow(_ error: APIError, request: URLRequest, attempt: Int) async throws -> (Data, URLResponse) {
        guard request.isRetryable, error.isRetryableRead, attempt < 2, await connectivity.isOnline else { throw error }
        let delay: Duration = error.retryAfter ?? .milliseconds(Int(1000 * pow(2, Double(attempt)) + .random(in: 0..<500)))
        try await Task.sleep(for: min(delay, .seconds(30)))
        return try await perform(request, attempt: attempt + 1)
    }
}
```

- `request.isRetryable` is true for `GET` / `HEAD`, or for any method carrying an `Idempotency-Key` header.
- `Task.sleep(for:)` throws `CancellationError` when the owner goes — a retry never outlives its screen.
- The **circuit** is a small actor keyed by endpoint name: after N consecutive failures it throws `.server` immediately for a cool-down, then allows one probe. Add it on the second endpoint that needs it, not before.
- 401 on a request that already carried a refreshed token is final: throw `.unauthorized` — the caller re-authenticates in place.

## 4. The token actor — single-flight refresh

```swift
actor TokenStore {
    private var current: Credentials
    private var refreshing: Task<Credentials, Error>?
    private let refresh: @Sendable (String) async throws -> Credentials
    private let persist: @Sendable (Credentials) throws -> Void

    init(
        current: Credentials,
        refresh: @escaping @Sendable (String) async throws -> Credentials,
        persist: @escaping @Sendable (Credentials) throws -> Void
    ) {
        self.current = current
        self.refresh = refresh
        self.persist = persist
    }

    func accessToken() -> String { current.accessToken }

    func refreshAfterRejection(of request: URLRequest) async throws {
        if request.value(forHTTPHeaderField: "Authorization") != "Bearer \(current.accessToken)" { return }
        let task = refreshing ?? Task { [current, refresh] in try await refresh(current.refreshToken) }
        refreshing = task
        defer { refreshing = nil }
        current = try await task.value
        try persist(current)
    }
}
```

- **Single flight**: N concurrent `401`s share one `Task`; the others find the token already changed and just replay.
- **Replay once.** A second `401` is `.unauthorized`, not another refresh.
- The refresh token and access token are persisted through the Keychain with a `…ThisDeviceOnly` class ([`offline-and-storage`](../../offline-and-storage/SKILL.md)); the actor's `persist` closure is that one call.
- A refresh that fails with `invalid_grant` clears the credentials and signals re-auth — a modal in place, biometric first where enrolled (`mobile-ios:auth0`'s `CredentialsManager` is the Auth0 shape).

## 5. The WebSocket wrapper

```swift
final class EventSocket: Sendable {
    private let task: URLSessionWebSocketTask

    init(url: URL, session: URLSession) {
        task = session.webSocketTask(with: url)
        task.resume()
    }

    func events() -> AsyncThrowingStream<Event, Error> {
        AsyncThrowingStream { continuation in
            let reader = Task {
                do {
                    while !Task.isCancelled {
                        let message = try await task.receive()
                        if let event = Event(message) { continuation.yield(event) }
                    }
                } catch { continuation.finish(throwing: error) }
            }
            continuation.onTermination = { _ in
                reader.cancel()
                task.cancel(with: .goingAway, reason: nil)
            }
        }
    }
}
```

The owner (`.task` on the screen, gated by `scenePhase == .active`) iterates `events()`; leaving or backgrounding cancels the iteration, which closes the socket. A reconnect loop uses the same jittered backoff, runs only while `isOnline`, and ends with a revalidation of the polled data. `Event(message)` returns `nil` for a malformed frame, which is counted through `os.Logger`, never thrown into the render.

## 6. Uploads and large downloads

- User-initiated uploads under the `.upload` budget use `session.upload(for:from:)` / `upload(for:fromFile:)`; a file is streamed from disk, never loaded as `Data`.
- A transfer that must survive suspension uses a **background `URLSession`** (`URLSessionConfiguration.background(withIdentifier:)`) — that is `mobile-ios:system-integration`'s lane.
- Resumable downloads keep `resumeData` from `URLError.downloadTaskResumeData`; clean temp files on completion.
