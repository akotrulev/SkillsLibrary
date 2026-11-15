---
name: unit-testing
description: Use when Swift logic in a Mac app needs a dev-side unit test (Swift Testing, fakes, clock seams, URLProtocol stubs). Triggers "unit-test this model". Not for window journeys (qa-desktop-typescript).
---

# macOS: Unit Testing (Swift Testing)

Owns **every dev-side test of logic the agent writes**: models, services, mappers, formatters, state machines, the request policy, command enablement. In-process, no window journeys, no network, no real backend. Web analog: [`fe-react:component-testing`](../../../../frontend/react/skills/component-testing/SKILL.md): test behaviour, not markup; fakes at the boundary. Sibling: [`mobile-ios:unit-testing`](../../../../mobile/ios/skills/unit-testing/SKILL.md) (the same framework rules; the Mac runs tests on the host, with no simulator). Audit rows are section S of `desktop-macos:standards-audit`.

**Boundary.** Real windows, menus, panels, permission prompts, multi-window flows and VoiceOver are `qa-desktop-<lang>`'s (Appium **Mac2**). A unit test fakes the platform, so it can never prove a click or a system dialog. This skill hands QA the identifiers ([`test-ids`](../test-ids/SKILL.md)); it does not write the journeys.

## Version lane

| Concern | Primary (Xcode 27 · Swift 6) | Notes |
|---|---|---|
| Framework | **Swift Testing**: `import Testing`, `@Test`, `@Suite`, `#expect`, `#require` | Default for every new test |
| **XCTest only for** | UI automation (`XCUIApplication`, owned by QA), performance (`measure`, `XCTMetric`), Objective-C-exception tests | Never `XCTAssert*` inside a `@Test`, never `#expect` inside an `XCTestCase`. Xcode 27 warns at runtime on cross-framework misuse |
| Host | **Tests run on the host Mac**: `-destination 'platform=macOS'`; there is no simulator | A test that touches the real Keychain, `NSOpenPanel` or the user's folders is not a unit test |
| Exit tests | `#expect(processExitsWith:)` (Swift 6.2+) **works on a macOS host** | Prefer a small non-exiting API; use an exit test for a real `precondition` |
| Isolation | Mark a suite `@MainActor` when it touches `@MainActor` code | `[Swift5 mode]` same attributes, module diagnostics |
| `[mac13]` | Swift Testing runs wherever the toolchain does; `@Observable` tests need macOS 14+ | An `ObservableObject` project tests it the same way |
| Snapshot | `swift-snapshot-testing` 1.19 supports `NSView` / `NSViewController` image strategies: a lane where already used | Single views only |
| ViewInspector | 0.10.5, SwiftUI view unit tests: a lane where already used | Test the model first |
| Repeat runs | `swift test --maximum-repetitions … --repeat-until` (Xcode 27) | The cheapest flake check |
| Test plans | A unit plan and a UI plan are separate; `project-setup` creates them | A unit run never launches the app UI |

Detect first: the test target layout, XCTest vs Swift Testing mix, existing fakes and builders, the snapshot library and the test plans; extend them. Never rewrite a stable XCTest suite to Swift Testing as a side effect.

## When to use

- A model, service, mapper, formatter, validator or state machine has logic
- Region states from [`error-handling`](../error-handling/SKILL.md): failed keeps the filters, stale keeps the rows, offline is not failed, wake revalidates once
- Command enablement: a menu command is disabled, not hidden, in the states the model says
- The request policy against a `URLProtocol` stub; a `Codable` type, a URL-scheme parser, a route builder, a version comparison
- Multi-window state: one model, two consumers

## When NOT to use

- Window journeys, menus, panels, drag and drop, permission prompts, VoiceOver → `qa-desktop-<lang>` (peer)
- Markup-only views with no branches: a snapshot of hand-written layout is a tautology
- API contract tests and real-backend integration → `qa-api-typescript` / `qa-api-dotnet` / `qa-api-java`
- Writing `accessibilityIdentifier`s → [`test-ids`](../test-ids/SKILL.md)
- Windows apps → `desktop-windows:unit-testing`; iOS → `mobile-ios:unit-testing`

## Test what has behaviour

| Unit | Test? | Assert |
|---|---|---|
| `@Observable` model with logic | Yes | An action changes state; the failure path lands in `.failed` |
| Region `LoadState` transitions | Yes | Loading → loaded; refetch failure → `.stale`; drifted → `.failed` |
| Wake / reactivation / reconnect | Yes | Each trigger calls `revalidate()` once; one within the debounce window does not |
| Command enablement (`canArchive`, `isSaving`) | Yes | Disabled when nothing is selected or a write is in flight |
| Mapper, formatter, validator, `VersionPolicy` | **Yes** | Accept / reject by the offending field; boundaries; empty input |
| Request policy (retry, `Retry-After`, circuit, refresh) | Yes | Attempts counted by a stub; delays by an injected clock |
| `Codable` payloads, URL-scheme and file-activation parsers | Yes | A fixture decodes; a malformed one throws naming the key path; a hostile URL is rejected |
| Security-scoped bookmark handling | Yes, behind a fake | Stale → recreated; `stop` balanced on every path |
| View with branches | Rarely: test the model; one snapshot per reusable component state | |
| Type-only files, constants, a wrapper that only forwards | No | Nothing |

## Swift Testing: the shape

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

- **A suite is a struct**: a **new instance per test**, so `init` is setup and tests cannot leak state. A suite needing teardown is a `final class` with `deinit` (or an `actor`); cleanup lives there, never in an inline `defer`.
- **`#expect` records and continues; `#require` unwraps or throws and stops.** `#require` for a precondition, `#expect` for the assertion. No force unwrap.
- **`@Test(arguments:)` replaces a `for` loop.** Two collections ⇒ the cross product; pass `zip(a, b)` for paired rows.
- **One expected value per assertion**: never "`.mustUpdate` or `.canUpdate`". Two outcomes are two arguments or two tests.
- Names read `Should_X_When_Y` in the display name; the function name stays a short noun-verb.
- **Traits**: `.tags`, `.timeLimit(.minutes(1))` as a hang guard, `.bug("https://…")` to record a linked defect (the only comment-like content allowed), `.enabled(if:)` / `.disabled("reason")`, `.serialized` only when a shared resource forces it.
- **`withKnownIssue { … }`** marks a defect not yet fixed; it fails when the issue disappears. Never an `if` to skip.

## Errors: assert them, never catch them

```swift
@Test("Should_ThrowDrifted_When_BodyIsNotAnAlbumList")
func driftedBody() async throws {
    let client = APIClient.stubbed(status: 200, body: Fixtures.albumObjectInsteadOfList)

    await #expect(throws: APIError.drifted(endpoint: "albums")) {
        _ = try await client.send(.albums(.default))
    }
}
```

- **`#expect(throws:)` is the assertion**; a test body has **no `do`/`catch`**. An unexpected error reaches the runner untouched.
- **A failed decode names the key path and carries the payload**: assert on the `DecodingError`'s `codingPath` through a helper that attaches the raw body.
- A helper performing I/O (a teardown deleting a temp file) may catch one named error and log it, never a blanket catch.

## Seams: what makes logic testable

**Time, identity, randomness, configuration, outbound I/O**, plus on the Mac **the workspace** (wake, sleep, activation) and **the file system** (panels, bookmarks). Each is injected through the initializer; none is a global.

```swift
@MainActor
@Observable
final class LibraryModel {
    private let now: @Sendable () -> Date
    private let wakes: AsyncStream<Void>
    private(set) var lastLoaded: Date?

    init(now: @escaping @Sendable () -> Date = Date.init, wakes: AsyncStream<Void>) {
        self.now = now
        self.wakes = wakes
    }

    func observeWake() async {
        for await _ in wakes { await revalidate() }
    }
}
```

```swift
@MainActor
@Test("Should_RevalidateOnce_When_MacWakes")
func revalidatesOnWake() async {
    let (stream, wake) = AsyncStream<Void>.makeStream()
    let api = FakeAlbumAPI()
    let model = LibraryModel(now: { Date(timeIntervalSince1970: 1_000) }, wakes: stream, api: api)

    let observing = Task { await model.observeWake() }
    wake.yield()
    wake.finish()
    await observing.value

    #expect(api.loadCount == 1)
}
```

- **Wake and activation**: the app wires `NSWorkspace.didWakeNotification` into an `AsyncStream<Void>` at the root; the unit test feeds the stream. The model never reads `NSWorkspace` itself.
- **Time**: inject `() -> Date` for a timestamp and `any Clock<Duration>` for a delay. A backoff test uses a clock whose `sleep` records the duration and returns at once. Never `Task.sleep` in a test.
- **Outbound I/O**: a **`URLProtocol` stub** on an ephemeral `URLSession` (the client's `init` takes a session); **no `protocol APIClientProtocol` for a test**. A one-method seam exists only once a fake needs it (CLAUDE.md § KISS).
- **Fakes over mocks**: a hand-written `InMemoryAlbumStore` that behaves like the real one beats a mock asserting call order. Assert **outcomes**, not interactions.
- Reset a `URLProtocol` stub registry per test (suite `init`).
- **`UserDefaults`**: a unit test uses `UserDefaults(suiteName: "test-\(UUID())")` and removes the suite in `deinit`; never `.standard`.
- **Security-scoped bookmarks and panels**: behind a one-method fake (`resolve(bookmark) -> URL`); the real sandbox and `NSOpenPanel` belong to QA and the integration plan.
- Keychain-touching code is tested through its wrapper with an in-memory stand-in; the real data-protection Keychain needs a signed host app.

## Models, concurrency and several windows

- A `@MainActor` model's test is `@MainActor` and `async`; `await` the model's own method, **never `DispatchQueue.main.async` plus a sleep**.
- **`confirmation`** replaces expectations for "this callback fires N times".
- **Cancellation**: start the `Task`, cancel it, `await task.value`, assert the state did not move to `.failed`.
- **Two windows, one model**: two consumer objects (a selection model per window) over one data model: write through the first, assert the second observes the new value. The window itself is not created.
- **SwiftData**: a logic test uses an in-memory `ModelConfiguration(isStoredInMemoryOnly: true)`; a **migration test uses an on-disk store** in a per-test temporary directory removed in `deinit`.
- Observation: assert on the property after the action; `withObservationTracking` is for testing the tracking itself.

## Test data

- **Builders for four or more fields**: `Album.fixture(status: .imported)` returns a complete valid value with overridable defaults; or one `Fixtures` file. No duplicated inline literals.
- **Fixtures** are JSON files in the test bundle loaded by one helper (`Bundle.module` in a package); a fixture that fails to load fails the test with the file name.

## Snapshot tests: a lane, single views

Only where the project already uses `swift-snapshot-testing`: one reusable view in one state through the `NSView` / `NSHostingView` image strategy, a fixed size, light and dark, recorded on the CI Mac's macOS version. **Never snapshot a whole window** and never dynamic content (dates, random data). Review the diff on every update.

## Rules

Standards a test must meet come from the desktop-macos rule file `swift-tests.md` in `.claude/rules/desktop-macos/` (`/desktop-macos:rules` installs it), or the plugin's copy when the project has none; where it and this skill disagree, the rule file wins.

## Coverage floor: at least 80% of the code you wrote

The tests cover **at least 80% of the code the change wrote**: every type it created, whole, and the methods it changed in an existing file. The scope is the change, never the repo.

- **Xcode reports line coverage, not branches**, so on this lane the floor is 80% of the changed **lines**; the branch list is still how the tests are designed.
- **Design for every branch.** List the outcomes of the code you wrote (each `if`/`else` and `guard`, `switch` case including `default` and `@unknown default`, ternary, `??`, an `if let` that finds `nil`, each `catch` and `throw`, each region state, a loop run zero times and many) and give each a test or an `arguments:` case that asserts its effect.
- **Only an asserting test counts.** A test that runs code without an `#expect` on what it did is a **major** finding.
- **Leave out what *Test what has behaviour* does not test, by name**: view files, `#Preview` blocks, type-only files, constants, forwarding wrappers, generated code. The report names each one left out. Never reach 80% by lowering the number.
- **Measure** over the files you wrote:

  ```bash
  xcodebuild test -scheme <Scheme> -testPlan Unit -destination 'platform=macOS' \
    -enableCodeCoverage YES -resultBundlePath build/Unit.xcresult
  xcrun xccov view --report --json build/Unit.xcresult
  ```

  `lineCoverage` on the changed files (`targets[].files[]`) is the number. A local Swift package: `swift test --enable-code-coverage`, then the JSON at `swift test --show-codecov-path`.
- **Below 80%, write the missing tests.** The uncovered lines are the list.

## Generation steps

1. Read the target's initializers, existing fakes, test plans and the framework mix; match them.
2. List the behaviours worth testing and each one's branch outcomes: that list is the test plan; add the missing seam to the initializer, not a global.
3. Write each test as Arrange / Act / Assert with a behaviour name; parameterize variants.
4. Add the `URLProtocol` stub, the fixed clock, the workspace stream and the builders once, in shared test support.
5. Leave journeys as a hand-off note naming the identifiers, for `qa-desktop-<lang>`.

## Validation

- The unit plan passes with `-destination 'platform=macOS'`; each test passes alone (`-only-testing`) and in a shuffled order.
- Mutate one rule in the code under test; a test fails with a message naming the value.
- Line coverage of the changed code is at least 80%, reported as a figure.
- No `XCTAssert` in a Swift Testing file; no `try!`; no `sleep` or `Task.sleep`.

## Handoffs

- Window journeys, menus, panels, VoiceOver passes → `qa-desktop-<lang>` · API contract tests → the `qa-api-<stack>` peer
- Identifiers → [`test-ids`](../test-ids/SKILL.md) · state ownership and seams → [`architecture`](../architecture/SKILL.md)
- Request policy under test → [`networking`](../networking/SKILL.md) · region states → [`error-handling`](../error-handling/SKILL.md)
- Test plans and targets → [`project-setup`](../project-setup/SKILL.md)
