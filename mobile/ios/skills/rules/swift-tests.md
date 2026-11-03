---
paths:
  - "**/*Tests/**/*.swift"
  - "**/*{Tests,Test}.swift"
---

<!-- mobile-ios rules v1 (2026-11-03): tests. Installed by /mobile-ios:rules; edit to fit this project. -->

# Swift test standards

Severity tags as in the core Swift rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise. Force unwrap and `try!` are allowed here only as below.

- Swift Testing for every new test; XCTest only for UI automation, performance and Objective-C exceptions. *minor*
- One framework per test: no `XCTAssert*` in Swift Testing, no `#expect` in an `XCTestCase`. *major*
- No `do`/`catch` in a test body: `#expect(throws:)` for an expected error, `try` in a `throws` test otherwise, `#require` for preconditions. *major*
- No `if`, `for` or `switch` driving assertions; variants are `@Test(arguments:)`. *major*
- One behaviour per test, and each assertion expects one value: never `#expect(a == x || a == y)`. *major*
- No `Task.sleep`, `sleep` or `DispatchQueue` timing; wait on a condition. *major*
- Time, identity, randomness, configuration and I/O enter through the initializer; fakes over mocks, asserting outcomes rather than call order; no protocol created only for a test. *major; minor for mocks*
- Network tests use a `URLProtocol` stub on an ephemeral session, never `URLSession.shared` or a live host; no real Keychain or system clock. *blocker*
- Tests are independent and order-free: no shared mutable state, no `.serialized` to hide one. *major*
- Names state behaviour; test data with four or more fields comes from a builder. *minor*
- No force unwrap or `try!` beyond a fixed fixture literal. *minor*
- Snapshots cover one reusable view in one state, never a whole screen or dynamic content, and never stand in for an assertion. *minor*
- A migration test uses an on-disk store, never an in-memory one. *major*
- No tests of getters, DTOs or forwarding wrappers; journeys, gestures and system dialogs belong to the `qa-mobile-<stack>` suite. *minor*
- New code ships with tests covering at least 80% of the lines it wrote (Xcode measures lines, not branches), designed branch by branch; only an asserting test counts. *major*
