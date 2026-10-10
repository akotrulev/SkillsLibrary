# Android — Robolectric, Roborazzi and test data

*Deep dive for [`mobile-android-unit-testing`](../SKILL.md).*

---

## Robolectric and Roborazzi

- **Robolectric** for code that needs a `Context`, resources or a Compose host on the JVM; **not** for plain logic (a pure-JVM test is faster) and **not** a substitute for a device (it does not render real GPU output or exercise a real `WorkManager` scheduler — use `TestListenableWorkerBuilder` and `WorkManagerTestInitHelper`).
- `@RunWith(AndroidJUnit4::class)` and `@GraphicsMode(GraphicsMode.Mode.NATIVE)` for screenshot tests.
- **Roborazzi** records and verifies one composable in one state: a fixed `@Config(qualifiers = "w360dp-h640dp-xhdpi")`, light and dark, one font scale; **never a whole screen** and never dynamic content (dates, random data). `./gradlew recordRoborazziDebug` then `verifyRoborazziDebug`; review every diff on an update — a bulk record is a skipped review.

## Test data

- **Builders for four or more fields** — `Order.fixture(status = Shipped)` returning a complete valid value with overridable defaults; or an ObjectMother in one `Fixtures.kt`. No duplicated inline literals across tests.
- **Fixtures** are JSON files in `src/test/resources` loaded by one helper; a missing fixture fails the test with its name.

