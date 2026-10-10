---
name: mobile-android-code-review
description: Use when reviewing a Kotlin / Compose / Views diff — `!!`, blocked main thread, `GlobalScope`, lifecycle-blind collection, ViewModel events, work in composition, missing timeouts and failed states, secrets outside Keystore storage, exported components, unvalidated links, untagged elements — plus an emulator screenshot pass. Triggers "review this screen", "review this PR". Do NOT use for a whole-repo audit (`mobile-android-standards-audit`), explanations or writing code.
---

# Android — Code Review

A **hostile review of one diff** against the conformance checklist's rows and CLAUDE.md § Mobile code rules, then a **screenshot pass** on the running app. Findings go in the standard severity table; the review **does not rewrite** — it points, and the `mobile-android` agent (or the author) fixes. A whole-repo sweep with a saved report is [`standards-audit`](../standards-audit/SKILL.md), which reuses these checks at repo scale.

## Version lane

Detect before flagging: Kotlin (`gradle/libs.versions.toml`), AGP and Gradle (`gradle/wrapper/gradle-wrapper.properties`), `compileSdk` / `targetSdk` / `minSdk`, the Compose BOM, Compose vs Views for the files in the diff, KSP vs kapt, Hilt vs manual DI, Room 2.8 vs 3, Navigation 3 vs Navigation Compose, any Kotlin Multiplatform module.

| Lane | Review consequence |
|---|---|
| **AGP 9 · Kotlin 2.4 · compile 37 / target 36** | The rows as written |
| AGP 8 / Kotlin 2.0–2.3 | `[AGP9]` rows are advice for the project's own migration run, not findings on a feature diff; a *new* module applying `kotlin-android` or `kapt` on AGP 9 is A5 / A10 |
| Views screen `[Views]` | The Views rows (D-section `views-interop` rows) apply; a Compose rule is not flagged on an XML screen, and a Views codebase is not asked to convert |
| Navigation Compose 2.10 | `[N3]` rows (Navigation 3) are not findings; type-safe routes are correct |
| Room 2.8 | `androidx.room3` rows are not findings; KSP and `suspend` / `Flow` DAOs still are |
| Below minSdk 24 or a floor mismatch | One finding (A7) plus a [`migration`](../migration/SKILL.md) run |

An API above the detected Kotlin, compileSdk or BOM is a **finding** (A1 / A7); `EncryptedSharedPreferences` in new code is a major (I-section); a `@Preview` missing on a new screen is a minor.

## When to use

- A `.kt` / `.kts` / `.xml` / `AndroidManifest.xml` / `libs.versions.toml` / `proguard-rules.pro` diff, before merge
- Step 5 of the agent: the whole change set, after the quality layers
- "Why does this recompose forever / lose its state on rotation / crash after process death?"

## When NOT to use

- Whole codebase, saved re-runnable report → [`standards-audit`](../standards-audit/SKILL.md)
- Explaining a concept → [`basics`](../basics/SKILL.md); writing code → the owning feature skill
- Reviewing **E2E test code** (Appium / UiAutomator / Maestro) → peer `qa-mobile-java` / `qa-mobile-dotnet` / `qa-mobile-typescript`
- Pen-test or runtime security → peer `qa-security` (`mobile-app-scan`, `mobile-runtime-testing`)
- A spec-versus-code audit → `code-auditor`

## Inputs needed

1. **The diff** (files or `git diff` range) and the screens it touches
2. **Lane facts** above, from the project's catalog and build files
3. **Whether an emulator is available** for the screenshot pass

## Procedure

1. **Map the diff to checklist sections** with the table below; open [`conformance-checklist.md`](../standards-audit/references/conformance-checklist.md) at only those sections and run each row's *Find it with* recipe **over the changed files**.
2. **Read the code at every hit.** A grep hit is a lead, not a finding.
3. **Verify the rule's owner** when a row is ambiguous — load the owning skill; the skill wins over the checklist, and the disagreement is reported.
4. **Run the screenshot pass** (below) if an emulator is available; otherwise say it was not run.
5. **Write the table**; one row per defect family with a count, not per site.

| The diff touches | Sections |
|---|---|
| Gradle files, catalog, `gradle.properties`, R8 rules | A, B, K, L, T |
| Composables, components, lists | C, D, E, M, N, R |
| Views, Fragments, `ComposeView`, `AndroidView` | D (Views rows), M, N |
| Routes, links, notifications, `assetlinks.json` | F, J, K |
| Forms, inputs | G, M |
| API client, sockets | H, O, K |
| Room / DataStore / Keystore / files / WorkManager | I, K |
| Permissions, camera, location, widgets, services, alarms | J, K, L |
| Animation, gestures | Q, N, M |
| String resources, formats | P |
| ViewModels, repositories, DI modules | B, C, V |
| Tests | S, R |
| Purchases | X |
| `commonMain` / a KMP module | W, C |

## The rules every diff is held to (§5, in review form)

| Check | Bad sign | Severity |
|---|---|---|
| No `!!` outside tests | `value!!` in app or library source | blocker |
| The main thread is never blocked | `runBlocking`, `Thread.sleep`, `.get()` on a future, disk / network / Room query call on `Dispatchers.Main` or in a composable body | blocker |
| Secrets live in Keystore-backed storage, never in the binary | A token in `SharedPreferences` / plain DataStore / `BuildConfig` / `strings.xml`; a key in `local.properties` copied into the APK | blocker |
| TLS only | `usesCleartextTraffic="true"` or a `cleartextTrafficPermitted` with no recorded reason; a `TrustManager` / `HostnameVerifier` accepting everything | blocker |
| Push and link payloads are validated | A route, `Intent` or `Class.forName` built from unchecked `intent.data` / `remoteMessage.data` | blocker |
| Components are exported on purpose | `android:exported="true"` with no filter reason; an exported `ContentProvider` or `Service` with no permission; a mutable `PendingIntent` | blocker |
| Every shipped Room schema migrates | An entity changed with no `Migration` / auto-migration; `fallbackToDestructiveMigration()` in a release path | blocker |
| Every permission is declared and asked in context | A runtime permission used with no manifest entry; a request in `Application.onCreate` / first composition; no denied-path screen | major |
| No `GlobalScope`; dispatchers are injected | `GlobalScope.launch`; `Dispatchers.IO` hardcoded in a class that needs a test | major |
| Flows are collected with the lifecycle | `collectAsState()` on a ViewModel flow; `lifecycleScope.launch { flow.collect }` with no `repeatOnLifecycle` | major |
| One `uiState` per screen; no ViewModel-to-UI events | A `Channel` / `SharedFlow` of one-shot UI events; several `StateFlow`s a screen combines by hand | major |
| No work in composition | A network call, `Json.decode`, a large sort or `DateFormat` built in a composable body; side effects outside `LaunchedEffect` / `DisposableEffect` | major |
| Async work is owned by its screen | A coroutine launched in a composable with no structured scope; a `viewModelScope` job never cancelled on a new request | major |
| Every request has a timeout budget | An `OkHttpClient` built with defaults; a spinner that can run forever | major |
| Data regions have all states | No failed / stale / offline path; a failure that blanks the toolbar and the screen; `runCatching` turning a failure into empty | major |
| Failures surface in one persistent banner | A `Log`-only catch, a `Toast`, a snackbar that vanishes, `Text(e.message)` | major |
| Unbounded lists are lazy, with stable keys | `Column(Modifier.verticalScroll)` over server data; `items(list)` with no `key` / `contentType`; index as key | major |
| Every interactive element and list container has a `testTag`, and the root exposes `testTagsAsResourceId` | A `Button` / `TextField` / `LazyColumn` with none; an id built from an index, GUID or state; `contentDescription` used as an id | major |
| Accessible | An icon-only button with no `contentDescription`; `clickable` on a `Box` with no role; text in `dp`; target < 48 dp | major |
| Dependencies arrive by constructor | A service locator, a `companion` singleton, `Hilt` field injection in a class outside an entry point | major |
| No unearned abstraction | An interface with one implementer; a use case that only forwards to a repository; a ViewModel that mirrors a model | major |
| Animator duration scale honoured | Custom motion that ignores `ANIMATOR_DURATION_SCALE` / reduced motion | major |
| Strings localized | A literal in `Text("…")`; a string built by concatenation instead of a resource with arguments | major |
| Fakes over mocks; `runTest` in new tests; no `try` / `if`, `OR` or sleep in a test body | `mockk` for a repository; `Thread.sleep`; `assertTrue(a == x \|\| a == y)` | major |
| `commonMain` stays platform-free `[KMP]` | `android.*` import, Hilt, or a token in shared storage | major |
| No inline comment, no commented-out code, no `TODO` | `//` inside a body | minor |
| A version, SDK or toolchain move inside a feature diff | `compileSdk`, `targetSdk`, AGP, Kotlin or the BOM changed beside a feature | major — reject; it is a [`migration`](../migration/SKILL.md) run |

## The screenshot pass (Step 5)

Only when an emulator is available and the app builds; otherwise report "screenshot pass not run" and why. Never build inside a `Gate: none` plan task.

```bash
adb exec-out screencap -p > android-<screen>.png
```

`Read` each image. Capture the changed screens in **light and dark**, at **a large font scale** (`adb shell settings put system font_scale 2.0`) and at a **tablet / foldable size** where the app supports one, in each of loading, loaded, failed and empty where the diff changes them. Check against the diff, not against taste: edge-to-edge insets under the status and navigation bars, text truncation at large sizes, contrast, touch-target size, the error banner position, Material 3 components rather than a web or iOS look. Cite the `design/ux-review` heuristic and the corpus row (`design/ui-ux-pro-max --stack jetpack-compose`) behind each visual finding. Save images only under a scratch folder inside the worktree and delete them before committing.

## Output format

```
| Severity | Location | Issue | Suggested fix |
|----------|----------|-------|---------------|
| blocker  | app/src/main/kotlin/profile/ProfileViewModel.kt:41 | `user.avatarUrl!!` on a server value — crashes on a missing avatar | Handle null and show the placeholder per `basics` |
| major    | app/src/main/kotlin/orders/OrdersClient.kt:18 | `OkHttpClient()` with no timeout budget | Per-endpoint-class timeouts per `networking` |
```

Close with the lane line (`Kotlin 2.4 · AGP 9.4 · compile 37 / target 36 / min 24 · Compose · Hilt`), the screenshot-pass status, and the finding counts by severity. Severities follow the checklist: blocker ships a crash, a store rejection or a hard security rule break; major breaks a § Mobile code rule where it will hurt soon; minor is style; nit is preference.

## Anti-patterns to always flag

- An AGP, Kotlin, SDK-level or Compose BOM move inside a feature diff — reject it; it is a [`migration`](../migration/SKILL.md) run
- A comment that exists because a name is unclear (major — the fix is the rename)
- A test that asserts nothing, or an `OR` in an assertion (Test code rules)
- `try` / `catch` inside a test body
- A migration PR that changes behaviour beside the conversion

## Handoffs

- Fix → the `mobile-android` agent (FIX or EXTEND), or the owning skill named per section
- Repo-wide → [`standards-audit`](../standards-audit/SKILL.md); version moves → [`migration`](../migration/SKILL.md)
- Lock the fix with a test → [`unit-testing`](../unit-testing/SKILL.md)
- Missing ids → [`test-ids`](../test-ids/SKILL.md); E2E review → peer `qa-mobile-java` / `qa-mobile-dotnet` / `qa-mobile-typescript`
- Security proof → peer `qa-security`
