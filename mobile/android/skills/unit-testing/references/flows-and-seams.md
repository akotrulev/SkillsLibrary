# Android — Flows and seams in tests

*Deep dive for [`mobile-android:unit-testing`](../SKILL.md). Samples have no inline comments (CLAUDE.md § Comments).*

---

## A ViewModel with injected seams

```kotlin
class DraftViewModel @Inject constructor(
    private val clock: Clock,
    private val newId: () -> String,
) : ViewModel() {

    val draft: StateFlow<Draft?>
        field = MutableStateFlow<Draft?>(null)

    fun start() {
        draft.value = Draft(id = newId(), createdAt = clock.now())
    }
}
```

```kotlin
@Test
fun Should_StampDraft_When_Started() {
    val viewModel = DraftViewModel(
        clock = FixedClock(Instant.fromEpochSeconds(1_000)),
        newId = { "draft-1" },
    )

    viewModel.start()

    assertEquals(Draft("draft-1", Instant.fromEpochSeconds(1_000)), viewModel.draft.value)
}
```

## Flow with Turbine

```kotlin
@Test
fun Should_EmitOfflineThenOnline_When_NetworkReturns() = runTest {
    val connectivity = FakeConnectivity(online = false)

    connectivity.isOnline.test {
        assertEquals(false, awaitItem())

        connectivity.setOnline(true)

        assertEquals(true, awaitItem())
    }
}
```

- `awaitItem()` suspends until the next emission under the test scheduler; **`expectNoEvents()` / `ensureAllEventsConsumed()`** (called by `test {}` on exit) fail on an unconsumed item — the guard against a silent extra emission.
- A `StateFlow` conflates: `test {}` sees the current value first. A `stateIn(WhileSubscribed(5000))` flow needs a collector — `test {}` is one, so the upstream runs; assert that **after the last collector leaves, the upstream stops** with `advanceTimeBy(5_001)`.
- Never `first()` on a hot flow and call it a test of the sequence; never collect into a list with a real `delay`.


## Storage and platform seams

- **Room**: a logic test uses `Room.inMemoryDatabaseBuilder` on Robolectric with the **real** driver; a **migration test** uses the exported schemas and `MigrationTestHelper` ([`offline-and-storage`](../../offline-and-storage/SKILL.md)) — an in-memory database cannot prove a migration. DAOs are never mocked.
- **DataStore**: a real `DataStore` over `TemporaryFolder` and a `TestScope`, never a mocked interface.
- **Keystore-backed code** is tested through the repository fake in unit tests; the real Keystore needs a device and belongs to the integration plan.
