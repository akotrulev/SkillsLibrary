---
name: unit-testing
description: Use when Kotlin or Compose logic needs a dev-side unit test (JUnit, runTest, Turbine, Robolectric, Kover). Triggers "unit-test this ViewModel". Not for device journeys (qa-mobile-typescript).
disable-model-invocation: true
---

# Android — Unit Testing (JUnit 4 + fakes)

Owns **every dev-side test of logic the agent writes**: ViewModels, repositories, mappers, formatters, state machines, the request policy, and the Compose UI of a single screen. In-process, no device journeys, no real backend. Web analog: [`fe-react:component-testing`](../../../../frontend/react/skills/component-testing/SKILL.md) — test behaviour, not markup; fakes at the boundary; pure logic without a renderer carry over; jsdom and RTL queries do not. Sibling: [`mobile-ios:unit-testing`](../../../ios/skills/unit-testing/SKILL.md).

**Boundary.** Real devices, real navigation, permission dialogs, deep links, TalkBack and cross-screen journeys are `qa-mobile-<stack>`'s — **Appium (UiAutomator2)** with a **Maestro** lane. A unit test fakes the platform, so it can never prove a system dialog or a gesture on hardware. This skill hands them the ids ([`test-ids`](../test-ids/SKILL.md)); it does not write the journeys.

## Version lane

| Concern | Primary | Notes |
|---|---|---|
| Runner | **JUnit 4** (`org.junit.Test`, `@RunWith`) | The default: Robolectric, Compose rules and `androidTest` need it |
| `[JUnit5]` | JUnit 5 **only where the `de.mannodermaus.android-junit5` plugin is already applied** — and only for plain-JVM tests | Never mix both runners in one module's `test` source set; never add the plugin as a side effect |
| Coroutines | `kotlinx-coroutines-test`: `runTest`, `StandardTestDispatcher`, `TestScope`, `advanceUntilIdle()`, `testScheduler` | `Dispatchers.setMain` through one **`MainDispatcherRule`** |
| Flow | **Turbine** (`app.cash.turbine`) — `flow.test { awaitItem() }` | Version-key against the project's catalog |
| Local Android | **Robolectric** with `@RunWith(AndroidJUnit4::class)` | **JDK 21 toolchain** for SDK 36 targets; `@Config(sdk = [36])` set once in `robolectric.properties` |
| Compose UI | **Compose UI test v2** — `androidx.compose.ui.test.junit4.v2.createComposeRule` / `androidx.compose.ui.test.v2.runComposeUiTest` | **Runs on `StandardTestDispatcher`** — see `references/compose-ui-tests.md` |
| Screenshots | **Roborazzi** (JVM, over Robolectric) — a lane where the project already uses it | Single composables, never whole screens |
| Compose a11y | `enableAccessibilityChecks()` from `androidx.compose.ui:ui-test-junit4-accessibility` (Compose 1.8+) | One screen, one test |
| `[AGP8]` | Same libraries; `testOptions.unitTests.isIncludeAndroidResources = true` for Robolectric | AGP 9 default is the same — set it explicitly |

Detect first: the runner (`junit`, `junit-jupiter`, `mannodermaus`), the existing fakes and `MainDispatcherRule`, whether tests are Hilt-instrumented, and the screenshot library — extend them; never migrate a stable suite as a side effect.

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

- Names, assertions, parameterized variants and the dispatcher choice: per `android-tests.md`.
- **`runTest` owns time.** It runs on a `StandardTestDispatcher` with a virtual clock; `delay` costs nothing. Inject the dispatcher into the class under test (`TestDispatcher(testScheduler)`), never reach for `Dispatchers.Main` directly — the rule sets it for the ones you do not own.
- **Advance explicitly**: `advanceUntilIdle()` to drain, `advanceTimeBy(1_000)` + `runCurrent()` to step.
- **Unconfined** runs launched coroutines eagerly and hides ordering bugs; use it only for a collector that must see every emission, and say why in the test's name.
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

- **`assertFailsWith<T>` (kotlin.test) or `assertThrows` is the assertion**, per `android-tests.md`.
- **A failed decode names the path and carries the payload**: assert on the `SerializationException`'s path through a test client that attaches the raw body — "Unexpected JSON token at offset 0" tells the reader nothing.
- A teardown registry doing I/O (closing `MockWebServer`) may catch one named exception and log it; cleanup runs in `@After` or the `TestWatcher`.

## Seams — what makes logic testable

The five seams: **time, identity, randomness, configuration, outbound I/O.** Each is injected through the constructor; none is a global.

The `Clock` / id-factory constructor sample is in [`references/flows-and-seams.md`](references/flows-and-seams.md).

- **Time**: inject `Clock` (kotlin.time / `kotlinx-datetime`) for a timestamp; a delay uses the coroutine scheduler, which the test controls. A backoff test uses a `Sleeper` fake that records the requested durations and returns — the test asserts `[1, 2, 4]` seconds and takes none.
- **Outbound I/O**: **`MockWebServer`** (OkHttp's `mockwebserver3`) behind the real `OkHttpClient` + Retrofit — the same stack as production; **no `interface ApiClient` is created for a test** ([`networking`](../networking/SKILL.md)). The seam for a ViewModel is the **repository**, and the fake is a hand-written class.
- **Fakes over mocks.** A `FakeOrdersRepository` with an in-memory list, `seed`, `failNextRefresh` and a `MutableStateFlow` behaves like the real one and is shared by every ViewModel test; assert on **outcomes** (state, stored values), not on interactions (`verify(repo).refresh()`). **No Mockito or MockK in a sample, and none added to a project that has neither** — a project that already has one may keep it for a type it cannot fake (a final framework class), never for the repository.

## Flow and seams — detail

Turbine usage (`awaitItem`, `expectNoEvents`, `StateFlow` conflation, `WhileSubscribed` shutdown) and the Room / DataStore / `MockWebServer` seam recipes are in [`references/flows-and-seams.md`](references/flows-and-seams.md).

## Compose UI tests

Write every new Compose UI test on v2, one stateless screen per test with a hand-built state. A task that writes or migrates one → read [`references/compose-ui-tests.md`](references/compose-ui-tests.md): the v2 sample, the move from `UnconfinedTestDispatcher` to `StandardTestDispatcher` (launched work is queued until the clock advances), and the accessibility check.

## Robolectric, Roborazzi and test data

When Robolectric earns its cost, the Roborazzi record / verify loop, builders and fixtures: [`references/robolectric-and-screenshots.md`](references/robolectric-and-screenshots.md). Builders for four or more fields; no duplicated inline literals.

## Rules

The standards this skill's output must meet are the mobile-android rule files, not a list here: `android-tests.md`. Read the project's copy in `.claude/rules/mobile-android/`, or the plugin's in `mobile/android/skills/rules/` when the project has not installed them (`/mobile-android:rules` does). Where they and this skill's recipes disagree, the rule files win. The coverage floor below is how its 80% rule is measured.

## Coverage floor — ≥ 80% of the branches you wrote

The tests cover **at least 80% of the branches in the code the change wrote**: every class it created, whole, and the functions it changed in a file that already existed. The scope is the change, never the repo.

- **Design for every branch; 80% is what gets measured.** Before writing tests, list the branch outcomes in the code you wrote — each `if`/`else`, `when` arm including `else`, `?:` and `?.`, short-circuit `&&`/`||`, `try`/`catch`, a failing `require`/`check`, an early `return`, each region state (loading / loaded / failed / stale / offline), a loop run zero times and many — and give each a test or a parameterized row that asserts its effect. The slack under 100% is for branches no honest unit test reaches, such as the ones the compiler adds around coroutines and inline functions.
- **Only an asserting test counts.** A test that runs a branch without asserting what it did is a **major** finding — it moves the number and catches nothing. *Validation*'s mutate-one-rule check is how hollow coverage gets caught.
- **Leave out what *Test what has behaviour* does not test, by name.** Type-only files, constants, DAO interfaces, forwarding wrappers and generated code (`androidGeneratedClasses()`, plus KSP / Room / Hilt output) stay out of the measured class list, and the report names each one left out. Never reach 80% by lowering the number or by a Kover exclusion over code that has behavior.
- **Measure** with Kover, set up once per module as in [`references/coverage-kover.md`](references/coverage-kover.md). Inside a plan task, the `Gate:` line runs this over the files the task and the landed tasks above it touched. Outside a plan, run it before you report.
- **Below 80%, write the missing tests.** The HTML report's missed branches are the list.

## Generation steps

1. Read the target's constructors, existing fakes, `MainDispatcherRule`, runner and Compose-test version, and match them. Done when the test plan names the runner, the dispatcher rule and each fake it reuses.
2. Write the branch-outcome list (*Coverage floor*), one row per outcome, with each missing seam added to the constructor, not a global. Done when every behaviour worth testing has its rows.
3. Write each test as Arrange / Act / Assert with a behaviour name, parameterized variants, and shared fakes, fixtures and builders in test support. Done when every row has a test asserting its effect.
4. Write the journeys as a hand-off note for `qa-mobile-<stack>`. Done when each journey is a line naming its `testTag`s.

## Validation

Inside a plan task, `Gate: own tests` runs this task's tests — the red run, then green —, the tests of the landed tasks above it, and the *Coverage floor* measure over the files the task and those tasks touched; the last runnable task runs everything else.

- `./gradlew testDebugUnitTest` passes on JDK 21; each test passes alone (`--tests`) and in a shuffled order; `connectedDebugAndroidTest` for the Compose rules that need a device.
- Mutate one rule in the code under test; a test fails with a message naming the value.
- Branch coverage of the changed code ≥ 80% (*Coverage floor*), reported as a figure.
- No `Thread.sleep`, `runBlocking` or v1 Compose rule import in a test.
