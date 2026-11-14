# De-flake — find why a flaky test flips, then fix the cause

Quarantine detects and contains; it does not explain. A quarantined test leaves the lane only when its cause is
named and fixed, so every quarantine ticket ends in this move. A retry is never the fix: it hides a 1-in-N race
that real users hit too.

## 1. Classify the cause

| Cause | Signature | Where it goes |
|---|---|---|
| **Test order / pollution** | Passes alone, fails in the suite (or only after a particular test); the failure follows the order, not the code | Bisect for the polluter: run the suspect with halves of the preceding tests until one pair reproduces it (`engineering-practices/systematic-debugging/find-polluter.sh` does this for file-scoped state). Fix the polluter's teardown, not the victim |
| **Timing** | Fails more under load or on a slower runner; the trace shows the assertion before the data or the element was ready; a fixed sleep or a one-shot read nearby | Replace the guess with a wait on the condition (`engineering-practices/systematic-debugging/condition-based-waiting.md`; web-first assertions, a polling wait) |
| **Shared data** | Fails when run in parallel; two tests touch the same record, user, mailbox or counter; the failing value belongs to another test | Each test creates and deletes its own data (`test-data-builder`); unique keys per test; never a shared "test user" a test mutates |
| **Environment** | Clusters by runner, region, time of day or a dependency's deploy; the trace shows a downstream timeout or 5xx outside the system under test | Stub the dependency (`network-mocking`) or fix the environment; a documented hotspot may take the one dated retry |
| **Real product race** | Fails on the same code with the test doing nothing wrong: double submit, lost update, an event handled before its write commits | A product defect: file it with the reproduction, the test stays as the regression guard, and the product is fixed. Never a retry |

Read the failed run's evidence first — the trace, screenshot and video, and the backend trace and logs linked by
the `telemetry` attachment (`test-reports`, `references/trace-links.md`). The class usually shows there.

## 2. Reproduce it on demand

A cause is confirmed when the test fails on purpose. Raise the pressure one lever at a time and record the
failure rate for each:

| Lever | How (Java / TestNG) |
|---|---|
| Repeat | `@Test(invocationCount = 50)` on the one test, locally and never committed; every invocation runs and is reported |
| Concurrent repeats | `@Test(invocationCount = 50, threadPoolSize = 8)` runs the invocations on eight threads — the cheapest race amplifier for API tests (not for Playwright UI tests: one `BaseTest` context per class is not thread-safe) |
| Order | Run it alone (`./gradlew test --tests '*.CheckoutTest.Should_X_When_Y'`), then with its class, then the suite; TestNG has no shuffle, so vary which classes run before it with `--tests` |
| Parallelism | Raise `thread-count` on the `parallel="classes"` suite in `testng.xml` for the experiment |
| CPU | Pin the app's container to one CPU (`docker run --cpus=1`); for a Playwright UI test on Chromium, `JsonObject rate = new JsonObject(); rate.addProperty("rate", 4); context.newCDPSession(page).send("Emulation.setCPUThrottlingRate", rate);` |
| Network | Delay the dependency's route (`network-mocking`) to widen a suspected window |

## 3. Compare a passing run with a failing one

Keep the evidence of one green and one red run of the same test on the same commit, and diff them: the step
where the traces diverge, the requests and their order (HAR or the backend trace), the timing of the step
before the failed assertion, the test data each used, the worker or thread it ran on, and what ran before it.
The first difference that is not a consequence of the failure is the lead.

## 4. Fix, prove, release

- Fix the cause in the class it belongs to — polluter teardown, a condition wait, per-test data, a stub, or the
  product.
- Prove it with the same reproduction recipe: the run that failed N times in M now passes M of M at the same
  pressure, with M large enough to have caught the old rate (a 1-in-20 flake needs well over 20 runs).
- Take the test out of quarantine in the same change, close the ticket with the cause and the proof, and let
  Allure history mark it **Fixed**.
- A test whose cause cannot be found after this move, and that nobody will own, is deleted — never moved back
  to the gate with a retry.
