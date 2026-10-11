---
name: migration
description: Use when an Android project changes lane — AGP 8 → 9 (built-in Kotlin, compilerOptions, kapt → KSP), Views → Compose, Java → Kotlin, Groovy → KTS, LiveData / RxJava → Flow, Dagger → Hilt, Navigation Compose → Navigation 3, Room 2 → 3, a targetSdk raise, EncryptedSharedPreferences replacement. Triggers "move us to AGP 9", "kapt fails", "drop LiveData". Do NOT use for feature work, a new app (`mobile-android:project-setup`) or a minor dependency bump.
---

# Android — Migration

Owns changing the **toolchain, framework, library generation or target SDK** of an existing project. Every other Android skill applies what is already there; this one is the only skill that moves the lane, and it does so as **its own change** — never inside feature work, never two moves at once, never past one module, one screen or one table per commit series.

## Version lane

| Lane | Value | Migration consequence |
|---|---|---|
| **Primary** | Kotlin 2.4 · AGP 9.4 · Gradle 9.6 · compile 37 / target 36 / min 24 · JDK 21 · Compose BOM 2026.09 | The target unless the project names another |
| Supported | Kotlin 2.0–2.3 · AGP 8.x · targetSdk 35 for existing apps | Never raised as a side effect of other work |
| **Temporary** | `android.builtInKotlin=false`, `android.newDsl=false`, `com.android.legacy-kapt`, `com.android.built-in-kotlin` | Escape hatches — **each removed in AGP 10**. Every use carries a dated removal task |
| Dated | Play: new apps **and updates** must target API 36 since **2026-08-31** (extension to 2026-11-01) | The one deadline — [`target-sdk-behaviour`](references/target-sdk-behaviour.md) |
| Below Kotlin 2.0 / AGP 8 | — | A finding plus an AGP / Kotlin run first; never authored for |

## When to use

- The user names a move from the table below
- The audit reports A1, A3, A5, A6, A7 or A10 ([`standards-audit`](../standards-audit/SKILL.md) section A)
- A post-migration break: `Cannot add extension with name 'kotlin'`, a release build that crashes only after R8, a screen that lost state, a Room `no such table`

## When NOT to use

- New app → [`project-setup`](../project-setup/SKILL.md)
- Feature work, bug fix → the agent's FIX / EXTEND modes; they never up-level a lane
- A patch / minor dependency bump with no lane change — dependency hygiene
- Moving KMP modules to the library plugin → covered in [`agp8-to-9`](references/agp8-to-9.md); the KMP design itself is [`kotlin-multiplatform`](../kotlin-multiplatform/SKILL.md)
- iOS → `mobile-ios:migration`; an Expo project's native side → `mobile-react-native:migration`

## Inputs needed

1. **The move** — one row below. A request for two is two runs, in the table's order
2. **Current state** — Kotlin, AGP, Gradle, JDK; `compileSdk` / `targetSdk` / `minSdk`; Compose BOM or Views; DI (Dagger / Hilt / Koin / none); Room version; navigation library; `kapt` users
3. **The unit** — one module, one screen or one DAO per commit; order is leaves first
4. **Whether a Play deadline is near** — it decides what moves first

## The gate — before any lane moves

1. **Clean tree, green baseline.** Record `./gradlew assembleDebug testDebugUnitTest lintDebug detekt ktlintCheck` and the connected tests *before* touching anything, or no later failure is attributable. Outside a `Gate: none` plan task, run them; inside one, say they were not run.
2. **One unit, one change.** Commit per module / screen / table so a failure bisects. Work in the checkout you are given — never create a branch or worktree.
3. **Inventory first** — count `kapt` users, `LiveData` types, Fragments, `.java` files, `androidx.room` imports, `EncryptedSharedPreferences` call sites. That number is the size of the job; a number you cannot bound is a reason to ask.
4. **Read the source of the move**, not memory: developer.android.com/build/migrate-to-built-in-kotlin, the AGP release notes, the Compose migration guides, the Navigation 3 and Room 3 pages, the behaviour-changes page per API level.
5. **Never combine** two moves. AGP 9 plus Navigation 3 plus Room 3 in one PR leaves no way to tell which broke the build.

## The moves

| # | Move | Reference | One-line shape |
|---|---|---|---|
| 0 | **targetSdk 35 → 36 → 37** — dated | [`target-sdk-behaviour`](references/target-sdk-behaviour.md) | One API level per run; set it explicitly; test the behaviour changes |
| 1 | **AGP 8 → 9** | [`agp8-to-9`](references/agp8-to-9.md) | Remove `kotlin-android`, `kotlinOptions` → `compilerOptions`, kapt → KSP, variant API, explicit `targetSdk`; escape hatches temporary |
| 2 | Groovy → KTS, Java → Kotlin | [`java-kotlin-gradle-kts`](references/java-kotlin-gradle-kts.md) | Build files one at a time; Java one leaf class at a time |
| 3 | LiveData / RxJava → Flow | [`livedata-rx-to-flow`](references/livedata-rx-to-flow.md) | Repository first, ViewModel next, UI last |
| 4 | Dagger → Hilt | [`dagger-to-hilt`](references/dagger-to-hilt.md) | Component by component; KSP; entry points bridge |
| 5 | Room 2 → 3 | [`room2-to-3`](references/room2-to-3.md) | Package rename, `SQLiteDriver`, suspend DAOs, schema JSON kept |
| 6 | Views → Compose | [`views-to-compose`](references/views-to-compose.md) | Google's order: new screens, features, design system, simple screens, Fragments and navigation last |
| 7 | Navigation Compose → Navigation 3 | [`navigation-to-nav3`](references/navigation-to-nav3.md) | `NavKey` routes, `NavDisplay`, one atomic change |
| 8 | `EncryptedSharedPreferences` → DataStore + Tink / Keystore | [`encrypted-prefs-replacement`](references/encrypted-prefs-replacement.md) | Read old, write new, delete old — once, per key |

Order: 0 moves first when its date is near; 1 before 3–5 (Hilt 2.59+ needs AGP 9; KSP is mandatory); 2 any time after 1; 5 after 1; 6 before 7 (Navigation 3 is a Compose-only library); 8 with whichever run touches the storage.

## Cross-move rules

- **Never up-level as a side effect.** A feature task that finds AGP 8, `kapt`, LiveData or an old Room reports it and offers this skill — it does not start it.
- **Escape hatches are temporary and dated.** `android.builtInKotlin=false`, `android.newDsl=false`, `com.android.legacy-kapt`, `com.android.built-in-kotlin` carry an issue id and a removal task; all of them stop working in AGP 10. A green build reached by flipping a flag is not a migration.
- **A deployment-level raise is its own move.** `targetSdk` and `minSdk` change in their own commit; a `minSdk` raise is the only change allowed to delete `Build.VERSION` branches.
- **Tests move with the code.** A moved seam keeps (or gains) a test that fails on the old behaviour ([`unit-testing`](../unit-testing/SKILL.md)); a migration with none has proved nothing.
- **R8 and process death only fail in release and on a real kill.** Verify a release-config build and an `adb shell am kill` restore for every move that touches state or the build.
- **Warnings are the work list.** Do not suppress a deprecation to finish; do not widen a keep rule to `**`.
- **No destructive Room fallback** to get a migration through; user data is never rebuilt from nothing.

## Verification (every move, non-negotiable)

1. `./gradlew assembleDebug assembleRelease` is clean for the unit moved; detekt / ktlint / Lint match or beat the baseline.
2. The unit-test suite matches or beats the baseline; one test exercises the moved seam.
3. The app launches on an emulator and the primary flow runs end to end; a screenshot on a UI move.
4. A **release-configuration** build (R8 full mode) runs the moved path.
5. For state / storage moves, kill the process (`adb shell am kill`) and reopen — state restores, data is intact.
6. Re-run the conformance audit's section A ([`standards-audit`](../standards-audit/SKILL.md)).

## Rules

- One move, one unit, one commit series; never two moves in a change.
- AGP 9 escape hatches are listed as temporary with a removal date; AGP 10 removes them.
- `targetSdk` is explicit and raised one level at a time, with the behaviour change tested.
- kapt becomes KSP; `legacy-kapt` only with a dated task.
- Room 2.8 stays Room 2.8 until the Room 3 move is chosen; the two never mix inside one database.
- Work in the checkout given; never create a branch.

## What NOT to do

- Set `android.builtInKotlin=false` and call AGP 9 done.
- Rewrite LiveData, Room and Navigation "while upgrading Gradle".
- Raise `targetSdk` to reach a library, or leave it unset because AGP 9 defaults it to `compileSdk`.
- Convert Java to Kotlin and redesign in the same commit.
- Replace `EncryptedSharedPreferences` by wiping the user's stored token.
- Migrate Views to Compose by rewriting the whole app on a branch.

## Handoffs

- Gradle target state → [`project-setup`](../project-setup/SKILL.md); Kotlin standard → [`basics`](../basics/SKILL.md)
- State and DI target → [`architecture`](../architecture/SKILL.md); routes → [`navigation`](../navigation/SKILL.md)
- Database target → [`offline-and-storage`](../offline-and-storage/SKILL.md); the Views lane while it lasts → [`views-interop`](../views-interop/SKILL.md)
- KMP target → [`kotlin-multiplatform`](../kotlin-multiplatform/SKILL.md)
- Tests that prove the move → [`unit-testing`](../unit-testing/SKILL.md)
