---
name: mobile-android-unit-testing
description: Use when Kotlin or Compose logic needs a dev-side test — JUnit 4 (JUnit 5 only where the mannodermaus plugin is present), fakes over mocks, runTest with StandardTestDispatcher, Turbine for Flow, ViewModel and region-state tests, MockWebServer, Robolectric, Compose UI test v2 (its dispatcher change), accessibility checks, Roborazzi. Triggers "unit-test this ViewModel", "my Compose test broke after v2". Do NOT use for device journeys (`qa-mobile-<stack>`).
---

# Android — Unit Testing (JUnit 4 + fakes)

Owns **every dev-side test of logic the agent writes**: ViewModels, repositories, mappers, formatters, state machines, the request policy, and the Compose UI of a single screen. In-process, no device journeys, no real backend. Web analog: [`fe-react-component-testing`](../../../../frontend/react/skills/component-testing/SKILL.md) — test behaviour, not markup; fakes at the boundary; pure logic without a renderer carry over; jsdom and RTL queries do not. Sibling: [`mobile-ios-unit-testing`](../../../ios/skills/unit-testing/SKILL.md).

**Boundary.** Real devices, real navigation, permission dialogs, deep links, TalkBack and cross-screen journeys are `qa-mobile-<stack>`'s — **Appium (UiAutomator2)** with a **Maestro** lane (plan 003). A unit test fakes the platform, so it can never prove a system dialog or a gesture on hardware. This skill hands them the ids ([`test-ids`](../test-ids/SKILL.md)); it does not write the journeys.

## Version lane

| Concern | Primary | Notes |
|---|---|---|
| Runner | **JUnit 4** (`org.junit.Test`, `@RunWith`) | The default: Robolectric, Compose rules and `androidTest` need it |
| `[JUnit5]` | JUnit 5 **only where the `de.mannodermaus.android-junit5` plugin is already applied** — and only for plain-JVM tests | Never mix both runners in one module's `test` source set; never add the plugin as a side effect |
| Coroutines | `kotlinx-coroutines-test`: `runTest`, `StandardTestDispatcher`, `TestScope`, `advanceUntilIdle()`, `testScheduler` | `Dispatchers.setMain` through one **`MainDispatcherRule`** |
| Flow | **Turbine** (`app.cash.turbine`) — `flow.test { awaitItem() }` | Version-key against the project's catalog (1.2.0 at last check — **built but unverified**) |
| Local Android | **Robolectric** (4.17 line in §4.3; stable-release status **unconfirmed**) with `@RunWith(AndroidJUnit4::class)` | **JDK 21 toolchain** for SDK 36 targets; `@Config(sdk = [36])` set once in `robolectric.properties` |
| Compose UI | **Compose UI test v2** — `androidx.compose.ui.test.junit4.v2.createComposeRule` / `androidx.compose.ui.test.v2.runComposeUiTest` | **Runs on `StandardTestDispatcher`** — see below. v2 needs `ui-test-junit4` 1.11.0-alpha03+; `ComposeUiTestConfig` 1.13.0-alpha01+ — both are well below the BOM 2026.09 line |
| Screenshots | **Roborazzi** (JVM, over Robolectric) — a lane where the project already uses it | Single composables, never whole screens |
| Compose a11y | `enableAccessibilityChecks()` from `androidx.compose.ui:ui-test-junit4-accessibility` (Compose 1.8+) | One screen, one test |
| `[AGP8]` | Same libraries; `testOptions.unitTests.isIncludeAndroidResources = true` for Robolectric | AGP 9 default is the same — set it explicitly |

Detect first: the runner (`junit`, `junit-jupiter`, `mannodermaus`), the existing fakes and `MainDispatcherRule`, whether tests are Hilt-instrumented, and the screenshot library — extend them; never migrate a stable suite as a side effect.

## When to use

- A ViewModel, repository, mapper, formatter, validator or state machine has logic
- The region states from [`error-handling`](../error-handling/SKILL.md): failed keeps the filters, stale keeps the rows, offline is not failed
- The request policy: backoff, `Retry-After`, the single-flight refresh — against `MockWebServer`
- A serializable payload, a deep-link parser, a route builder, a version comparison
- One Compose screen's states and its accessibility check

## When NOT to use

- Device journeys, gestures, permission dialogs, deep links, push, TalkBack passes → `qa-mobile-<stack>` (peer)
- Markup-only composables with no branches — a screenshot of hand-written layout is a tautology
- API contract tests and real-backend integration → `qa-api-typescript` / `qa-api-dotnet` / `qa-api-java`
- Writing `testTag`s → [`test-ids`](../test-ids/SKILL.md)
- Other stacks → `mobile-react-native-component-testing`, `mobile-ios-unit-testing`

## Test what has behaviour

| Unit | Test? | Assert |
|---|---|---|
| ViewModel with logic | Yes | An action changes `uiState`; the failure path lands in `Failed`; the saved-state value is read and written |
| Region `LoadState` transitions | Yes | Loading → loaded; refetch failure → `Stale`; drifted → `Failed`; offline with data → `Stale` |
| Mapper, formatter, validator, `VersionPolicy` | **Yes** | Accept / reject by the offending field; boundaries; the empty input |
| Request policy (retry, `Retry-After`, circuit, refresh) | Yes | Attempts counted by `MockWebServer`; delays by the virtual clock |
| Serializable payloads | Yes | A fixture decodes; a drifted one throws naming the path |
| A composable with branches | One screen per state set, through the semantics tree | Visible text, enabled state, `testTag`, the callback fired |
| Type-only files, constants, a DAO interface, a wrapper that only forwards | No | Nothing |

## The shape — JUnit 4, fakes, one assertion per behaviour

```kotlin
class OrdersViewModelTest {

    @get:Rule
    val mainDispatcher = MainDispatcherRule()

    private val repository = FakeOrdersRepository()
    private val connectivity = FakeConnectivity(online = true)

    @Test
    fun Should_KeepRowsAndMarkStale_When_RefreshFails() = runTest {
        repository.seed(Orders.defaultPage())
        val viewModel = OrdersViewModel(repository, connectivity, SavedStateHandle())
        viewModel.uiState.test {
            awaitLoaded()
            repository.failNextRefresh(ApiError.TimedOut)

            viewModel.refresh()

            assertEquals(Orders.defaultPage(), awaitStale().value)
        }
    }
}

class MainDispatcherRule(
    val dispatcher: TestDispatcher = StandardTestDispatcher(),
) : TestWatcher() {
    override fun starting(description: Description) = Dispatchers.setMain(dispatcher)
    override fun finished(description: Description) = Dispatchers.resetMain()
}
```

- **Names read `Should_X_When_Y`**; one convention per module.
- **One expected value per assertion** — `assertEquals(Orders.defaultPage(), …)`, never "loaded or stale". Two outcomes are two tests or `@RunWith(Parameterized::class)` rows.
- **`runTest` owns time.** It runs on a `StandardTestDispatcher` with a virtual clock; `delay` costs nothing. Inject the dispatcher into the class under test (`TestDispatcher(testScheduler)`), never reach for `Dispatchers.Main` directly — the rule sets it for the ones you do not own.
- **Advance explicitly**: `advanceUntilIdle()` to drain, `advanceTimeBy(1_000)` + `runCurrent()` to step. **No real `Thread.sleep` or `delay` waiting on a result.**
- **Standard, not Unconfined.** `UnconfinedTestDispatcher` runs launched coroutines eagerly and hides ordering bugs; use it only for a collector that must see every emission, and say why in the test's name.
- **Cancellation**: `launch`, `cancel()`, `advanceUntilIdle()`, assert the state did not move to `Failed` ([`error-handling`](../error-handling/SKILL.md)).

## Errors — assert them, never catch them

```kotlin
@Test
fun Should_ThrowDrifted_When_BodyIsNotAnOrderList() = runTest {
    server.enqueue(MockResponse().setBody(Fixtures.ORDER_OBJECT_INSTEAD_OF_LIST))

    val error = assertFailsWith<ApiException> { api.orders(page = 1, query = null) }

    assertEquals(ApiError.Drifted(endpoint = "orders"), error.apiError)
}
```

- **`assertFailsWith<T>` (kotlin.test) or `assertThrows` is the assertion**; a test body contains **no `try` / `catch`**. An unexpected exception reaches the runner untouched and fails the test with its message.
- **A failed decode names the path and carries the payload**: assert on the `SerializationException`'s path through a helper that attaches the raw body — "Unexpected JSON token at offset 0" tells the reader nothing.
- A cleanup helper doing I/O (a teardown closing `MockWebServer`) may catch one named exception and log it — never a blanket catch. Resource cleanup is `@After` / the `TestWatcher`, never an inline `try` / `finally`.

## Seams — what makes logic testable

The five seams: **time, identity, randomness, configuration, outbound I/O.** Each is injected through the constructor; none is a global.

The `Clock` / id-factory constructor sample is in [`references/flows-and-seams.md`](references/flows-and-seams.md).

- **Time**: inject `Clock` (kotlin.time / `kotlinx-datetime`) for a timestamp; a delay uses the coroutine scheduler, which the test controls. A backoff test uses a `Sleeper` fake that records the requested durations and returns — the test asserts `[1, 2, 4]` seconds and takes none.
- **Outbound I/O**: **`MockWebServer`** (OkHttp's `mockwebserver3`) behind the real `OkHttpClient` + Retrofit — the same stack as production; **no `interface ApiClient` is created for a test** ([`networking`](../networking/SKILL.md)). The seam for a ViewModel is the **repository**, and the fake is a hand-written class.
- **Fakes over mocks.** A `FakeOrdersRepository` with an in-memory list, `seed`, `failNextRefresh` and a `MutableStateFlow` behaves like the real one and is shared by every ViewModel test; assert on **outcomes** (state, stored values), not on interactions (`verify(repo).refresh()`). **No Mockito or MockK in a sample, and none added to a project that has neither** — a project that already has one may keep it for a type it cannot fake (a final framework class), never for the repository.

## Flow and seams — detail

Turbine usage (`awaitItem`, `expectNoEvents`, `StateFlow` conflation, `WhileSubscribed` shutdown) and the Room / DataStore / `MockWebServer` seam recipes are in [`references/flows-and-seams.md`](references/flows-and-seams.md).

## Compose UI test v2 — and the dispatcher change

```kotlin
class OrdersScreenTest {

    @get:Rule
    val compose = createComposeRule()

    @Test
    fun Should_KeepFiltersInteractive_When_ListFails() {
        compose.setContent {
            AppTheme {
                OrdersScreen(OrdersUiState.failed(query = "mug"), actions = NoOpOrdersActions)
            }
        }

        compose.onNodeWithTag("Orders.Search").assertIsEnabled()
        compose.onNodeWithTag("Orders.Error").assertIsDisplayed()
    }
}
```

with `import androidx.compose.ui.test.junit4.v2.createComposeRule` (v2). Facts, verified at the Compose migration page 2026-10-10:

| v1 (deprecated) | v2 |
|---|---|
| `androidx.compose.ui.test.junit4.createComposeRule` / `createAndroidComposeRule` / `createEmptyComposeRule` | the same names in `androidx.compose.ui.test.junit4.v2` |
| `androidx.compose.ui.test.runComposeUiTest` / `runAndroidComposeUiTest` / `runEmptyComposeUiTest` | the same names in `androidx.compose.ui.test.v2` |
| Coroutines on **`UnconfinedTestDispatcher`** — launched work runs immediately | Coroutines on **`StandardTestDispatcher`** — launched work is **queued** and runs only when the test advances the virtual clock |

- **Tests that rely on immediate execution break**: a `LaunchedEffect`, a `viewModel.load()` or a `produceState` that used to have finished by the next line has not. Fix the *test*, not the dispatcher: `compose.waitForIdle()` or `compose.runOnIdle { assert… }` before asserting state; `compose.mainClock.scheduler.runCurrent()` when `autoAdvance` is off; `mainClock.advanceTimeBy(1_000 + 16)` to step a `delay` (the 16 is a frame buffer).
- **Prefer `runComposeUiTest { }` over `createComposeRule()` + `runTest { }`** — two schedulers in one test is how v2 migrations go flaky; one `runComposeUiTest` has one.
- **v2 pins `InputMode.Touch`** at the start of each test; a keyboard-focus test sets `ComposeUiTestConfig(inputMode = InputMode.Keyboard)` (1.13+).
- `ComposeUiTestConfig` replaces the deprecated `effectContext`, `runTestContext` and `testTimeout` parameters (1.13.0-alpha01+).
- **A project on v1 is not flagged for being on v1** until it bumps to a version where v1 is removed; a *new* test is written on v2. Migrate by package rename first, then fix the red tests one at a time.
- **Find by `testTag`, then by semantics** (`onNodeWithContentDescription`, `onNodeWithText`) — the tag is the contract ([`test-ids`](../test-ids/SKILL.md)); `onNodeWithTag` works **without** the root `testTagsAsResourceId` flag.
- **Test the screen's stateless composable with a hand-built state** — the ViewModel is covered by its own test; a screen test that boots a Hilt graph is an integration test.

### Accessibility check

```kotlin
@Test
fun Should_PassAccessibilityChecks_When_OrdersLoaded() {
    compose.setContent { AppTheme { OrdersScreen(OrdersUiState.loaded(), NoOpOrdersActions) } }
    compose.enableAccessibilityChecks()

    compose.onRoot().tryPerformAccessibilityChecks()
}
```

It catches a missing label, low contrast, a small target and a traversal-order problem; every `performClick` also runs the checks. It **complements** a TalkBack pass ([`accessibility`](../accessibility/SKILL.md)); it never replaces one, and a green check is not an accessibility claim.

## Robolectric, Roborazzi and test data

When Robolectric earns its cost, the Roborazzi record / verify loop, builders and fixtures: [`references/robolectric-and-screenshots.md`](references/robolectric-and-screenshots.md). Builders for four or more fields; no duplicated inline literals.

## Rules

- JUnit 4 and fakes in every new test; JUnit 5 only where the plugin is present; no mock framework added.
- One behaviour per test, one expected value per assertion, no `if` / `for` driving assertions — parameterize.
- No `try` / `catch` in a test body; `assertFailsWith` or the exception reaches the runner.
- Time, identity, randomness, configuration and I/O enter through the constructor; no interface created only for a test.
- `runTest` + `StandardTestDispatcher`; advance the clock explicitly; **no real sleep**; tests are independent and order-free.
- Compose tests are v2, wait for idle before asserting launched work, and test one stateless screen with hand-built state.
- Journeys, gestures and system dialogs go to `qa-mobile-<stack>`.

## What NOT to do

- No `Thread.sleep`, `delay` or `Dispatchers.setMain(UnconfinedTestDispatcher())` to make a test pass.
- No `!!` even in a test where `assertNotNull` / `requireNotNull` would name the value in the failure.
- No mocking of Room, DataStore, Retrofit or the repository; no `mockk<ViewModel>()`.
- No whole-screen screenshot; no screenshot as a substitute for an assertion.
- No v1 Compose rule in a new test; no `waitForIdle()` as a reflex around a test that does not need it.
- No tests of getters, DTOs or forwarding wrappers; no comment narrating a test.

## Generation steps

1. Read the target's constructors, existing fakes, `MainDispatcherRule`, runner and Compose-test version; match them.
2. List the behaviours worth testing; add the missing seam to the constructor, not a global.
3. Write each test as Arrange / Act / Assert with a behaviour name; parameterize variants; put shared fakes, fixtures and builders in test support.
4. Leave journeys as a hand-off note naming the `testTag`s, for `qa-mobile-<stack>`.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- `./gradlew testDebugUnitTest` passes on JDK 21; each test passes alone (`--tests`) and in a shuffled order; `connectedDebugAndroidTest` for the Compose rules that need a device.
- Mutate one rule in the code under test; a test fails with a message naming the value.
- No `Thread.sleep`, `runBlocking` or v1 Compose rule import in a test.

## Handoffs

- Device journeys, gestures, TalkBack passes → `qa-mobile-<stack>` · API contract tests → the `qa-api-<stack>` peer
- Ids → [`test-ids`](../test-ids/SKILL.md) · state ownership and seams → [`architecture`](../architecture/SKILL.md)
- Request policy under test → [`networking`](../networking/SKILL.md) · region states → [`error-handling`](../error-handling/SKILL.md)
- Gradle test options, JDK toolchain → [`project-setup`](../project-setup/SKILL.md)
