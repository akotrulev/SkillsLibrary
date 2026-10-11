---
name: unit-testing
description: Use when Swift logic needs a dev-side test — Swift Testing (@Test, #expect, #require, parameterized arguments, confirmation, traits) with fakes over mocks, clock and UUID seams, URLProtocol stubs, @Observable models, region states, snapshot tests of single views. XCTest only for UI automation, performance and Objective-C exceptions. Triggers "unit-test this model", "fake the clock", "test the 401 ladder". Do NOT use for device journeys (`qa-mobile-<stack>`).
---

# iOS — Unit Testing (Swift Testing)

Owns **every dev-side test of logic the agent writes**: models, services, mappers, formatters, state machines, the request policy. In-process, no device journeys, no network, no real backend. Web analog: [`fe-react:component-testing`](../../../../frontend/react/skills/component-testing/SKILL.md) — test behaviour, not markup; fakes at the boundary; pure logic without a renderer carry over; jsdom and RTL queries do not. Sibling: [`mobile-react-native:component-testing`](../../../react-native/skills/component-testing/SKILL.md).

**Boundary.** Real devices, real navigation, permission dialogs, deep links, VoiceOver and cross-screen journeys are `qa-mobile-<stack>`'s — **Appium (XCUITest driver)**, with a **Maestro** lane (plan 003). A unit test fakes the platform, so it can never prove a gesture or a system dialog. This skill hands them the identifiers ([`test-ids`](../test-ids/SKILL.md)); it does not write the journeys.

## Version lane

| Concern | Primary (Xcode 27 · Swift 6.2+) | Notes |
|---|---|---|
| Framework | **Swift Testing** — `import Testing`, `@Test`, `@Suite`, `#expect`, `#require` | The default for every new test; ships in the toolchain |
| **XCTest only for** | UI automation (`XCUIApplication`), performance (`measure`, `XCTMetric`), Objective-C-exception tests (`XCTAssertThrowsError` on `NSException`) | Plan §4.2. UI automation journeys are `qa-mobile-<stack>`'s; the dev side keeps performance and Objective-C only |
| Both in one target | Allowed — separate files; never `XCTAssert*` inside a `@Test` or `#expect` inside an `XCTestCase` | Xcode 27 may add XCTest ↔ Swift Testing interoperability modes — unconfirmed (D24); do not rely on them |
| Exit tests (`#expect(processExitsWith:)`) | Swift 6.2+; **macOS / Linux hosts only — not an iOS target** | Put a `precondition` / `fatalError` path behind a small non-exiting API and test that, or place the unit in a Swift package tested on the host |
| Isolation | Test target default isolation follows the app; mark a suite `@MainActor` when it touches `@MainActor` code | `[Swift5 mode]` the same attributes, with the module's diagnostics |
| `[iOS16]` | Swift Testing runs wherever the toolchain does; `@Observable` tests need iOS 17+ | A project on `ObservableObject` tests it the same way |
| Snapshot | `swift-snapshot-testing` 1.19 — a lane where the project already uses it | Single views, never whole screens |
| Test plans | Unit plan and UI plan are separate; `project-setup` creates them | A unit run never launches a simulator UI |

Detect first: existing test target layout, XCTest vs Swift Testing mix, any existing fakes or builders, the snapshot library, and the test plans — extend them; never rewrite a stable XCTest suite to Swift Testing as a side effect.

## When to use

- A model, service, mapper, formatter, validator or state machine has logic
- The region states from [`error-handling`](../error-handling/SKILL.md): failed keeps the filters, stale keeps the rows, offline is not failed
- The request policy: backoff, `Retry-After`, the single-flight refresh — against a `URLProtocol` stub
- A `Codable` type, a deep-link parser, a route builder, a version comparison

## When NOT to use

- Device journeys, gestures, permission dialogs, deep links, push, VoiceOver passes → `qa-mobile-<stack>` (peer)
- Markup-only views with no branches — a snapshot of hand-written layout is a tautology
- API contract tests and real-backend integration → `qa-api-typescript` / `qa-api-dotnet` / `qa-api-java`
- Writing `accessibilityIdentifier`s → [`test-ids`](../test-ids/SKILL.md)
- Other stacks → `mobile-react-native:component-testing`, `mobile-android:unit-testing`

## Test what has behaviour

| Unit | Test? | Assert |
|---|---|---|
| `@Observable` model with logic | Yes | An action changes state; the failure path lands in `.failed` |
| Region `LoadState` transitions | Yes | Loading → loaded; refetch failure → `.stale`; drifted → `.failed` |
| Mapper, formatter, validator, `VersionPolicy` | **Yes** | Accept / reject by the offending field; boundaries; the empty input |
| Request policy (retry, `Retry-After`, circuit, refresh) | Yes | Attempts counted by a stub; delays by an injected clock |
| `Codable` payloads | Yes | A fixture decodes; a drifted one throws naming the key path |
| View with branches | Rarely — test the model; one snapshot per reusable component state | |
| Type-only files, constants, a wrapper that only forwards | No | Nothing |

## Swift Testing — the shape

```swift
import Testing

@Suite("VersionPolicy")
struct VersionPolicyTests {
    private let policy = VersionPolicy(minimum: "2.4.0", recommended: "2.10.0")

    @Test("Should_RequireUpdate_When_BuildIsBelowMinimum")
    func requiresUpdate() {
        #expect(policy.verdict(for: "2.3.9") == .mustUpdate)
    }

    @Test("Should_CompareNumerically_When_MinorHasTwoDigits", arguments: [
        ("2.9.0", VersionVerdict.canUpdate),
        ("2.10.0", VersionVerdict.current),
    ])
    func comparesNumerically(current: String, expected: VersionVerdict) {
        #expect(policy.verdict(for: current) == expected)
    }
}
```

- **A suite is a struct**: a **new instance per test**, so `init` is setup and tests cannot leak state. A suite needing teardown is a `final class` with `deinit` (or an `actor`) — cleanup lives there, never in an inline `defer` inside the test.
- **`#expect` records and continues; `#require` unwraps or throws and stops** — use `#require` for a precondition (`let first = try #require(rows.first)`), `#expect` for the assertion. No force unwrap in a test either.
- **`@Test(arguments:)` replaces a `for` loop.** One collection ⇒ one test per element; two collections ⇒ the cross product — pass `zip(a, b)` for paired rows. Arguments must be `Sendable`.
- **One expected value per assertion** — `.mustUpdate`, never "`.mustUpdate` or `.canUpdate`". Two outcomes are two arguments or two tests.
- Names read `Should_X_When_Y` in the display name; the function name stays a short noun-verb.
- **Traits**: `.tags(.network)` to group, `.timeLimit(.minutes(1))` as a hang guard, `.bug("https://…")` to record a linked defect (the only comment-like content allowed), `.enabled(if:)` / `.disabled("reason")` for an environment gate, `.serialized` only when a shared resource forces it — tests are independent by default.
- **`withKnownIssue { … }`** marks a defect not fixed yet; it fails when the issue disappears so the marker is not forgotten. Never an `if` to skip.

## Errors — assert them, never catch them

```swift
@Test("Should_ThrowDrifted_When_BodyIsNotAnOrderList")
func driftedBody() async throws {
    let client = APIClient.stubbed(status: 200, body: Fixtures.orderObjectInsteadOfList)

    await #expect(throws: APIError.drifted(endpoint: "orders")) {
        _ = try await client.send(.orders(.default))
    }
}
```

- **`#expect(throws:)` is the assertion**; a test body contains **no `do`/`catch`**. An unexpected error reaches the runner untouched and fails the test with its description.
- **A failed decode names the key path and carries the payload**: assert on the `DecodingError`'s `codingPath` through a helper that attaches the raw body, so the failure says which field broke — not "data couldn't be read".
- `try` helpers performing I/O (a teardown deleting a temp file) may catch one named error and log it — never a blanket catch.

## Seams — what makes logic testable

The five seams: **time, identity, randomness, configuration, outbound I/O.** Each is injected through the initializer; none is a global.

```swift
@MainActor
@Observable
final class DraftModel {
    private let now: @Sendable () -> Date
    private let makeID: @Sendable () -> UUID
    private(set) var draft: Draft?

    init(now: @escaping @Sendable () -> Date = Date.init, makeID: @escaping @Sendable () -> UUID = UUID.init) {
        self.now = now
        self.makeID = makeID
    }

    func start() {
        draft = Draft(id: makeID(), createdAt: now())
    }
}
```

```swift
@MainActor
@Test("Should_StampDraft_When_Started")
func startsDraft() {
    let id = UUID(uuidString: "00000000-0000-0000-0000-000000000001")!
    let model = DraftModel(now: { Date(timeIntervalSince1970: 1_000) }, makeID: { id })

    model.start()

    #expect(model.draft == Draft(id: id, createdAt: Date(timeIntervalSince1970: 1_000)))
}
```

(The `!` on a fixed literal UUID is the one allowed force unwrap — tests only, and the literal is the fixture.)

- **Time**: inject `() -> Date` for a timestamp and `any Clock<Duration>` for a delay. A backoff test uses a clock whose `sleep` records the requested duration and returns immediately — the test asserts `[1, 2, 4]` seconds, and takes none. Never `Task.sleep` in a test.
- **Outbound I/O**: a **`URLProtocol` stub** on a `URLSessionConfiguration.ephemeral` (the client's `init` already takes a `URLSession`) — **no `protocol APIClientProtocol` is created for a test**. A **one-method seam** is the smallest protocol and exists only once a fake needs it (CLAUDE.md § KISS).
- **Fakes over mocks**: a hand-written `InMemoryOrderStore` that behaves like the real one beats a mock asserting call order; assert on **outcomes** (state, stored values), not on interactions.
- Reset a `URLProtocol` stub registry per test (suite `init`), never share it across tests.

## Models, concurrency and Observation

- A `@MainActor` model's test is `@MainActor` and `async`; `await` the model's own method — **never `DispatchQueue.main.async` plus a sleep**.
- **`confirmation`** replaces expectations for "this callback fires N times": `await confirmation(expectedCount: 1) { fired in model.onChange = { fired() }; await model.reload() }`.
- **Cancellation**: start the `Task`, cancel it, `await task.value`, assert the state did not move to `.failed` ([`error-handling`](../error-handling/SKILL.md)).
- **Observation**: assert on the property after the action. Tracking changes with `withObservationTracking` or the `Observations` async sequence (iOS 26+) is for testing the *tracking* itself, rarely the model.
- **SwiftData**: a logic test uses an in-memory `ModelConfiguration(isStoredInMemoryOnly: true)`; a **migration test uses an on-disk store** in a per-test temporary directory removed in the suite's `deinit` — an in-memory store cannot prove a `SchemaMigrationPlan` ([`offline-and-storage`](../offline-and-storage/SKILL.md)).
- Keychain-touching code is tested through its protocol-free wrapper with an in-memory stand-in in unit tests; the real Keychain needs a host app and belongs to the integration plan.

## Test data

- **Builders for four or more fields** — a `Order.fixture(status: .shipped)` static returning a complete valid value with overridable defaults; or an ObjectMother in one `Fixtures` file. No duplicated inline literals across tests.
- **Fixtures** are JSON files in the test bundle loaded by one helper (`Bundle.module` in a package); a fixture that fails to load fails the test with the file name.

## Snapshot tests — a lane, single views

Only where the project already uses `swift-snapshot-testing`: **one reusable view in one state**, a fixed device configuration, light and dark, one Dynamic Type size, recorded on the CI simulator's OS version. Swift Testing uses the library's `.snapshots` trait; **never snapshot a whole screen** (it fails on every unrelated change) and never snapshot dynamic content (dates, random data). Review the diff on every update; a bulk "record all" is a skipped review.

## Rules

- Swift Testing in every new test; XCTest only for UI automation, performance and Objective-C exceptions.
- One behaviour per test, one expected value per assertion, no `if` / `for` driving assertions — parameterize instead.
- No `do`/`catch` in a test body; `#expect(throws:)` or the error reaches the runner.
- Time, identity, randomness, configuration and I/O enter through the initializer; fakes over mocks; no protocol created only for a test.
- No `Task.sleep` or timing in a test; tests are independent and order-free.
- Journeys, gestures and system dialogs go to `qa-mobile-<stack>`.

## What NOT to do

- No `XCTAssert*` inside Swift Testing, no `#expect` inside an `XCTestCase`.
- No force unwrap but the fixed-literal fixture; no `try!` — use `try` in a `throws` test.
- No `URLSession.shared` in a test; no real network, Keychain or system clock.
- No shared mutable state between tests; no `.serialized` to hide one.
- No whole-screen snapshot; no snapshot as a substitute for an assertion.
- No tests of getters, DTOs or a wrapper that only forwards; no comment narrating a test.

## Generation steps

1. Read the target's initializers, existing fakes, test plans and the framework mix; match them.
2. List the behaviours worth testing (the table above); add the missing seam to the initializer, not a global.
3. Write each test as Arrange / Act / Assert with a behaviour name; parameterize variants.
4. Add the `URLProtocol` stub, the fixed clock and the builders once, in shared test support.
5. Leave journeys as a hand-off note naming the identifiers, for `qa-mobile-<stack>`.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- The unit test plan passes on a simulator and, for packages, `swift test` on the host; each test passes alone (`-only-testing`) and in a shuffled order.
- Mutate one rule in the code under test; a test fails with a message naming the value.
- No `XCTAssert` in a Swift Testing file; no `try!`; no `sleep` or `Task.sleep`.

## Handoffs

- Device journeys, gestures, VoiceOver passes → `qa-mobile-<stack>` · API contract tests → the `qa-api-<stack>` peer
- Identifiers → [`test-ids`](../test-ids/SKILL.md) · state ownership and seams → [`architecture`](../architecture/SKILL.md)
- Request policy under test → [`networking`](../networking/SKILL.md) · region states → [`error-handling`](../error-handling/SKILL.md)
- Test plans and targets → [`project-setup`](../project-setup/SKILL.md)
