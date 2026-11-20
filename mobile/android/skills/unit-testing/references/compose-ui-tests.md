# Android — Compose UI tests

*Deep dive for [`mobile-android:unit-testing`](../SKILL.md). Samples have no inline comments (CLAUDE.md § Comments).*

---

## Compose UI test v2 — and the dispatcher change

v2 needs `ui-test-junit4` 1.11.0-alpha03+, and `ComposeUiTestConfig` needs 1.13.0-alpha01+; the Compose BOM the project uses carries both.

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

with `import androidx.compose.ui.test.junit4.v2.createComposeRule` (v2).

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
- **Find by `testTag`, then by semantics** (`onNodeWithContentDescription`, `onNodeWithText`) — the tag is the contract ([`test-ids`](../../test-ids/SKILL.md)); `onNodeWithTag` works **without** the root `testTagsAsResourceId` flag.
- **Test the screen's stateless composable with a hand-built state** — the ViewModel is covered by its own test; a screen test that boots a Hilt graph is an integration test.

## Accessibility check

```kotlin
@Test
fun Should_PassAccessibilityChecks_When_OrdersLoaded() {
    compose.setContent { AppTheme { OrdersScreen(OrdersUiState.loaded(), NoOpOrdersActions) } }
    compose.enableAccessibilityChecks()

    compose.onRoot().tryPerformAccessibilityChecks()
}
```

It catches a missing label, low contrast, a small target and a traversal-order problem; every `performClick` also runs the checks. It **complements** a TalkBack pass ([`accessibility`](../../accessibility/SKILL.md)); it never replaces one, and a green check is not an accessibility claim.
