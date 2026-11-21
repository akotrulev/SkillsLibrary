---
paths:
  - "**/*Tests/**/*.cs"
  - "**/*{Tests,Test}.cs"
  - "**/*Tests/**/*.cpp"
  - "**/*{Tests,Test}.cpp"
---

<!-- desktop-windows rules v2 (2026-11-21): tests. Installed by /desktop-windows:rules; edit the paths above to where this project keeps its tests. -->

# Windows test standards

Severity tags as in the core C# rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise. Force-unwrapping (`!`) and `null!` are allowed here only for a fixture literal.

- NUnit is the runner for view models and services; MSTest only inside the WinUI Unit Test App with `[UITestMethod]`, and only for code that needs XAML types (D8). C++ logic is GoogleTest over a XAML-free core library. *minor*
- Logic lives in a UI-free library; view models never touch the dispatcher, so the test project's TFM matches the project it references. *major*
- Names describe behaviour: `Should_X_When_Y` or `Given_Y_When_X_Then_Z`. *minor*
- One behaviour per test, each assertion expecting one value: never `Is.EqualTo(200).Or.EqualTo(204)`. No `if`, `for` or `switch` driving assertions; variants are `[TestCase]` / `[TestCaseSource]` (`TEST_P` in GoogleTest). *major*
- No `try`/`catch` in a test body: `Assert.ThrowsAsync<T>` for an expected error; cleanup is registered in `[TearDown]`. *major*
- No `Thread.Sleep`, `Task.Delay` or polling loop; wait on a condition. No `async void` test. *major*
- Time goes through `TimeProvider` (`FakeTimeProvider`); identity, randomness, I/O and dispatcher enter through the constructor. *major*
- No `InternalsVisibleTo` or reflection to reach private behaviour; extract the class. Assert the return value, the state changed or the message sent, never a call on a collaborator the class owns. *major*
- Fakes over mocks, asserting outcomes rather than call order; no interface created only for a test; no in-memory stand-in for a shipped database, and network tests use a stub handler, never a live host. *major*
- Tests are independent and order-free: no shared mutable state. *major*
- Test data with four or more fields comes from a builder. *minor*
- New code reaches 80% of branches (lines on the C++ lane), designed branch by branch; only an asserting test counts; exclusions are listed by name and never hide behaviour. *major*
- No tests of DTOs, getters or forwarding wrappers; window journeys, dialogs and shell integration belong to the `qa-desktop-<lang>` suite. *minor*
