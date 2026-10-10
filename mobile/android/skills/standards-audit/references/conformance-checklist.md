# mobile-android Conformance Checklist — the 24 sections

The audit's spine. Section letters and check numbers are **permanent** — a finding is `<letter><n>` (`B3`, `M1`) and keeps that ID across every round, forever. Never renumber; append new checks at the end of a section with the next free number. The letters are identical on all three mobile stacks (`react-native`, `ios`, `android`): `M` is Accessibility everywhere.

**How to read a row.** *Check* = the invariant. *Violation looks like* = what disqualifies it. *Find it with* = a mechanical lead (a grep hit is never a finding — read the code). *Sev* = the default severity; adjust for real impact and say why.

**Recipes** use `rg` (ripgrep), which honours `.gitignore` — so `build/`, `.gradle/`, `.idea/` and `local.properties` are skipped without flags. Without ripgrep, `grep -rn --include='*.kt' --include='*.kts' --include='*.xml' --exclude-dir=build --exclude-dir=.gradle` is equivalent. Set the source roots once:

```bash
SRC=$(ls -d app/src */src 2>/dev/null | tr '\n' ' ')   # adjust to the repo layout
rg -n "<pattern>" $SRC -g '*.kt' -g '*.kts' -g '*.xml'                      # the shape every recipe below uses
```

If the repo gitignores generated sources (KSP / Room / Hilt output under `build/generated/`) you still need to read, add `--no-ignore` and exclude it explicitly — and say so in the report's coverage line.

**The version lane gates everything.** Before flagging, confirm the check applies to the detected Kotlin, AGP and Compose BOM versions (AGP 9 / Kotlin 2.4 primary, AGP 8 supported in brownfield), whether the UI is Compose or Views, and whether any Kotlin Multiplatform module exists. Rows tagged **[AGP9]**, **[KMP]** and **[Views]** apply only in that lane.

**Fragment sections.** K, L, T, U and X carry no rows here: their rows live in `mobile/_shared/<skill>/references/audit-checks.md` and are filtered by the `Stacks` column. Every other section is filled by the task that writes its skill — an empty section means that skill is not written yet, not that the code passes.

**Severity.** blocker — ships a crash, a store rejection, or a hard security rule break. major — a rule in CLAUDE.md § Mobile code rules broken where it will hurt soon. minor — style, naming, a single missing label. nit — preference.

---

## A — Version lane, toolchain & migration hygiene
*Owning skills: [`project-setup`](../../project-setup/SKILL.md) · [`migration`](../../migration/SKILL.md) · [`basics`](../../basics/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| A1 | The Kotlin version is detected, and no feature above it is used | `context(...)` or an explicit backing field in a module on Kotlin 2.3 or below; Kotlin raised as a side effect of other work | `rg -n "^kotlin\|kotlin = " gradle/libs.versions.toml`; `rg -n "context\(" $SRC -g '*.kt'` | major |
| A2 | Context receivers are gone | `context(Foo)` with a type, not a named parameter, left from the revoked feature | `rg -n "context\(\w+[,)]" $SRC -g '*.kt'` | major |
| A3 | `kapt` is not used `[AGP9]` | `kotlin-kapt` or `kapt(` in a build file | `rg -n "kapt" -g '*.kts' -g '*.gradle' -g 'libs.versions.toml'` | major |
| A4 | Explicit API mode in a library module that publishes | A published library module with `public` by default and no `explicitApi()` | `rg -n "explicitApi" -g '*.kts'` | minor |
| A5 | `org.jetbrains.kotlin.android` is not applied `[AGP9]` | `kotlin-android` / `org.jetbrains.kotlin.android` in a module, the root file or the catalog | `rg -n "kotlin.android\|org.jetbrains.kotlin.android" -g '*.kts' -g '*.gradle' -g 'libs.versions.toml'` | blocker |
| A6 | The AGP 9 opt-outs are not set `[AGP9]` | `android.builtInKotlin=false`, `android.newDsl=false` or `com.android.legacy-kapt` with no dated removal task (all gone in AGP 10) | `rg -n "builtInKotlin\|newDsl\|legacy-kapt" gradle.properties -g '*.kts' -g 'libs.versions.toml'` | major |
| A7 | SDK levels are written explicitly: compile 37, target 36, min 24 | `targetSdk` absent (AGP 9 defaults it to `compileSdk`), or raised / lowered as a side effect of other work | `rg -n "compileSdk\|targetSdk\|minSdk" -g '*.kts' -g '*.gradle'` | major |
| A8 | A JDK 21 toolchain is declared in Gradle | No `jvmToolchain`; the build relies on the IDE's JDK | `rg -n "jvmToolchain\|JavaVersion" -g '*.kts'` | major |
| A9 | Every version lives in `libs.versions.toml` | A version string in a `build.gradle.kts`; a `buildSrc` constants object beside the catalog; a Compose artifact with its own version | `rg -n "\"[a-z.]+:[a-z-]+:[0-9]" -g 'build.gradle.kts'`; `rg -n "object Versions\|object Deps" -g '*.kt'` | minor |
| A10 | Annotation processors use KSP | `kapt(`, `annotationProcessor(`, `kotlin("kapt")` | `rg -n "kapt\(\|annotationProcessor\|kotlin\(\"kapt\"\)" -g '*.kts' -g '*.gradle'` | major |
| A11 | Release builds are minified with R8 full mode and narrow keep rules | `isMinifyEnabled = false` on release, `android.enableR8.fullMode=false`, a blanket `-keep class ** { *; }` | `rg -n "isMinifyEnabled\|enableR8" -g '*.kts' gradle.properties`; `rg -n "keep class \*\*" -g '*.pro'` | major |
| A12 | detekt, ktlint and Lint run with warnings failing the build | No `.editorconfig` / `detekt.yml` / `lint.xml`; `abortOnError = false`; a formatter auto-fixing inside a build phase | `rg -n "abortOnError\|warningsAsErrors\|detekt\|ktlint" -g '*.kts' -g '*.yml'` | minor |
| A13 | A convention plugin or module exists only on its second user | `build-logic/` for one module; `:core:common` / `:core:ui` with one consumer | `rg -n "includeBuild\|include\(" settings.gradle.kts`; count dependents per module | major |

---

## B — Project structure, strictness & language standard
*Owning skills: [`project-setup`](../../project-setup/SKILL.md) · [`basics`](../../basics/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| B1 | No `!!` outside tests | `value!!` in app or module source | `rg -n "!!" $SRC -g '*.kt' -g '!*Test*'` | blocker |
| B2 | No `lateinit` for an injectable dependency | `lateinit var repo: Repo` where a constructor parameter fits | `rg -n "lateinit var" $SRC -g '*.kt'` | major |
| B3 | No `GlobalScope` | `GlobalScope.launch` / `.async` | `rg -n "GlobalScope" $SRC -g '*.kt'` | blocker |
| B4 | Dispatchers are injected, not named in a class body | `Dispatchers.IO` / `Default` / `Main` written inside a repository or ViewModel | `rg -n "Dispatchers\.(IO\|Default\|Main)" $SRC -g '*.kt' -g '!*Module*'` | major |
| B5 | No `runBlocking` in production code | `runBlocking` outside tests and `main` | `rg -n "runBlocking" $SRC -g '*.kt' -g '!*Test*'` | blocker |
| B6 | `CancellationException` is rethrown | `catch (e: Exception)` / `Throwable`, or `runCatching`, around a `suspend` call with no rethrow | `rg -n "runCatching\|catch \(\w+: (Exception\|Throwable)\)" $SRC -g '*.kt'`; read each for a suspend call | major |
| B7 | A `suspend` function that blocks is main-safe | Blocking I/O in a `suspend` function with no `withContext(ioDispatcher)`, left to the caller | `rg -n -A6 "suspend fun" $SRC -g '*.kt'`; read for blocking calls | major |
| B8 | State is a sealed interface; `when` over it has no `else` | Three booleans for loading / error / data; an `else` branch on a sealed type | `rg -n "isLoading\|isError" $SRC -g '*.kt'`; `rg -n -B6 "else ->" $SRC -g '*.kt'` | major |
| B9 | A UI state class is an immutable `data class` | A `var` property or a `MutableList` field in a state class; a `StateFlow` of a mutable object | `rg -n "data class \w+State" -A8 $SRC -g '*.kt'` | major |
| B10 | No ViewModel-to-UI events; one `uiState: StateFlow` | A `SharedFlow` / `Channel` of one-off UI events exposed from a ViewModel | `rg -n "SharedFlow\|Channel<" $SRC -g '*.kt'` | major |
| B11 | `StateFlow` is updated atomically | `_state.value = _state.value.copy(` | `rg -n "\.value = .*\.value\.copy" $SRC -g '*.kt'` | minor |
| B12 | Flows are collected lifecycle-aware | `collectAsState()`, `launchWhenStarted` or a bare `lifecycleScope.launch { flow.collect }` in UI code | `rg -n "collectAsState\(\)\|launchWhenStarted\|lifecycleScope\.launch" $SRC -g '*.kt'` | major |
| B13 | No mutable collection in a public signature | `MutableList` / `MutableMap` as a parameter or return type | `rg -n "(: \|-> )Mutable(List\|Map\|Set)<" $SRC -g '*.kt'` | minor |
| B14 | `val` over `var`; no `var` never reassigned | A `var` with no reassignment | `rg -n "\bvar \w+" $SRC -g '*.kt'`; the compiler warns on never-reassigned | minor |
| B15 | No Java-isms | `get`/`set` method pairs, `Optional`, a static-holder class, `object` holding mutable state | `rg -n "Optional<\|fun (get\|set)[A-Z]\w+\(\|^object \w+" $SRC -g '*.kt'` | minor |
| B16 | A context parameter is not a service locator | `context(...)` carrying a repository or service used as a lookup | `rg -n "context\(" $SRC -g '*.kt'` | major |
| B17 | One activity hosts the Compose tree | An `Activity` per screen with no recorded reason | `rg -n "<activity" -g 'AndroidManifest.xml'` | minor |
| B18 | Edge-to-edge is enabled and insets are handled in composables | No `enableEdgeToEdge()`; `fitsSystemWindows`; a hard-coded status-bar height | `rg -n "enableEdgeToEdge\|fitsSystemWindows\|statusBarHeight" $SRC -g '*.kt' -g '*.xml'` | major |
| B19 | Predictive back is enabled; back is not overridden | No `enableOnBackInvokedCallback`; `onBackPressed()` overridden; `KEYCODE_BACK` handled | `rg -n "enableOnBackInvokedCallback\|onBackPressed\|KEYCODE_BACK" $SRC -g '*.kt' -g '*.xml'` | major |
| B20 | The manifest does not lock orientation or resizability | `screenOrientation`, `resizeableActivity="false"`, `maxAspectRatio` (ignored at target 36 on large screens) | `rg -n "screenOrientation\|resizeableActivity\|maxAspectRatio" -g 'AndroidManifest.xml'` | major |

---

## C — Architecture, state & DI
*Owning skill: [`architecture`](../../architecture/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| C1 | Each screen ViewModel exposes one `uiState: StateFlow` and no other state flow | A second public `StateFlow` per field; a public `MutableStateFlow` | `rg -n "val \w+: (Mutable)?StateFlow" $SRC -g '*ViewModel.kt'` | major |
| C2 | No ViewModel-to-UI events: one-off outcomes are state the UI consumes | A `SharedFlow` / `Channel` of effects, snackbar or navigation events exposed from a ViewModel | `rg -n "SharedFlow\|Channel<\|receiveAsFlow" $SRC -g '*ViewModel.kt'` | major |
| C3 | State is built with `stateIn(WhileSubscribed(5_000))` from repository flows, not collected into a field in `init` | `init { viewModelScope.launch { flow.collect { _state.value = … } } }`; `SharingStarted.Eagerly` with no reason | `rg -n "stateIn\|init \{" -A4 $SRC -g '*ViewModel.kt'` | minor |
| C4 | A ViewModel holds no `Context`, `View`, `NavController` or composable | `Context` / `Application` constructor parameter, `NavController` field | `rg -n "Context\|NavController\|AndroidViewModel" $SRC -g '*ViewModel.kt'` | major |
| C5 | A composable never calls a repository or data source | A repository, DAO or client referenced in a `@Composable` | `rg -n "Repository\|Dao\b\|Api\b" $SRC -g '*Screen.kt' -g '*Composable*.kt'` | major |
| C6 | Repositories are the single source of truth and are main-safe | A ViewModel reading a DAO and the network separately; a blocking call with no injected dispatcher | `rg -n "class \w+Repository" -A12 $SRC -g '*.kt'` | major |
| C7 | A use case exists only when reused or a real rule | A `*UseCase` forwarding one repository call | `rg -n "class \w+UseCase" -A8 $SRC -g '*.kt'`; count callers | major |
| C8 | Dependencies arrive by constructor; no locator, no static state | `lateinit` injected field, `object` holding a client, `Context.getSystemService` for own classes, a `ServiceLocator` | `rg -n "ServiceLocator\|GlobalContext\|object \w+(Client\|Repository)" $SRC -g '*.kt'` | major |
| C9 | Hilt (when present) uses KSP and constructor injection, and was earned | `kapt(libs.hilt.compiler)`; field `@Inject lateinit var` in a ViewModel; Hilt in a one-screen app | `rg -n "hilt" -g '*.kts' -g 'libs.versions.toml'`; `rg -n "@Inject lateinit" $SRC -g '*.kt'` | major |
| C10 | `SavedStateHandle` carries the small state that must survive process death; nothing large | A list or model stored in `SavedStateHandle`; a draft lost after process kill | `rg -n "SavedStateHandle\|savedStateHandle\[" $SRC -g '*.kt'`; kill the process and return — requires dynamic test → `qa-mobile-android` | major |
| C11 | No LiveData or RxJava in new code | `LiveData`, `MutableLiveData`, `observeAsState`, `io.reactivex` | `rg -n "LiveData\|observeAsState\|io\.reactivex" $SRC -g '*.kt'` | minor |
| C12 | An interface exists only with a second implementation (a test fake counts) | `interface FooRepository` with one implementer and no fake | `rg -n "^(fun )?interface \w+Repository" $SRC -g '*.kt'`; count implementers | major |
| C13 | Modules are split by feature and only when earned | `:data` / `:domain` / `:ui` modules for one feature; a feature importing another feature's internals | `rg -n "include\(" settings.gradle.kts`; read each module's dependents | minor |

---

## D — UI components & platform conventions
*Owning skills: [`ui-components`](../../ui-components/SKILL.md) · [`views-interop`](../../views-interop/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| D1 | A screen composable collects `uiState` lifecycle-aware; content composables are stateless | A `ViewModel` or `NavController` passed below the screen; `collectAsState()` | `rg -n "viewModel: \w+ViewModel\|collectAsState\(\)" $SRC -g '*.kt'`; read each hit's depth | major |
| D2 | `modifier` is the first optional parameter, applied once to the root | A missing `modifier`, one applied to a child, a second `Modifier` parameter | `rg -n "@Composable" -A6 $SRC -g '*.kt'`; read signatures | minor |
| D3 | State is hoisted; business state is not in `remember` | `remember { mutableStateOf(` holding screen data; a repository result in `rememberSaveable` | `rg -n "remember \{ mutableStateOf\|rememberSaveable" $SRC -g '*.kt'` | major |
| D4 | Lazy lists use stable `key` (and `contentType` for mixed rows) | `items(list) { }` with no `key`; the index as a key | `rg -n "items\(\|itemsIndexed\(" -A2 $SRC -g '*.kt'` | major |
| D5 | Long content is a lazy list, not a scrolling `Column` | `Column(Modifier.verticalScroll)` over an unbounded collection; a `LazyColumn` nested in a same-axis scroll | `rg -n "verticalScroll" -B2 -A6 $SRC -g '*.kt'` | major |
| D6 | `LaunchedEffect` keys are the values it reads; `Unit` / `true` carries a reason | `LaunchedEffect(Unit)` that reads changing state | `rg -n "LaunchedEffect\((Unit\|true)\)" $SRC -g '*.kt'` | major |
| D7 | Every registration is disposed; callbacks use `rememberUpdatedState` | `DisposableEffect` with an empty `onDispose`; a listener added in the body | `rg -n "DisposableEffect" -A8 $SRC -g '*.kt'` | major |
| D8 | No work in composition: sort, filter, format or parse is hoisted or `remember`ed | `.sortedBy`, `Regex(`, `DateTimeFormatter.ofPattern(` inside a composable body | `rg -n "sortedBy\|sortedWith\|Regex\(\|ofPattern\(" $SRC -g '*.kt'` | major |
| D9 | Each data region renders loading, loaded, empty and failed, scoped to the region | A `when` missing `Failed` or empty; a failure replacing search or the top bar | `rg -n "is \w+UiState\.Failed\|\.Failed ->" $SRC -g '*.kt'`; read each screen | major |
| D10 | A failure is also a persistent, user-dismissed banner inside the safe area | A snackbar with `Short` / `Long` duration for a load failure, or none | `rg -n "SnackbarDuration\|showSnackbar" $SRC -g '*.kt'` | major |
| D11 | Framework or server error text is never shown | `Text(error.message` / `e.localizedMessage` / `Throwable` in UI state | `rg -n "\.message\b\|localizedMessage" $SRC -g '*.kt'` | major |
| D12 | Material 3 components, not imitations of another platform | A custom tab bar, back button, switch or alert drawn to look like iOS or the web | `rg -n "Box\(" -B2 -A8 $SRC -g '*TabBar*.kt' -g '*Switch*.kt'`; read custom controls | major |
| D13 | `@Preview` exists for reusable composables, covers states, uses no live data | A composable with no preview; one that calls a repository | `rg -L "@Preview" $SRC -g '*Content.kt' -g '*Screen.kt'` | minor |
| D14 | Expressive Material APIs are used only on material3 1.5 or an existing opt-in `[M3-1.5]` | `ExperimentalMaterial3ExpressiveApi` opt-in added in a non-Expressive project | `rg -n "ExperimentalMaterial3ExpressiveApi\|MaterialExpressiveTheme" $SRC -g '*.kt'` | major |
| D15 | `@Stable` / `@Immutable` only where the promise is true and measured | A blanket annotation on a class with a `var` or `MutableList` | `rg -n "@Stable\|@Immutable" -A4 $SRC -g '*.kt'` | minor |

---

## E — Styling, theming & adaptive layout
*Owning skill: [`styling`](../../styling/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| E1 | One `AppTheme`; screens read `MaterialTheme.*` tokens | `Color(0xFF…)`, `TextStyle(fontSize = …)` or `RoundedCornerShape(n.dp)` in a screen file | `rg -n "Color\(0x\|fontSize = [0-9]\|RoundedCornerShape\([0-9]" $SRC -g '*.kt' -g '!*Theme*' -g '!*Color*' -g '!*Type*'` | major |
| E2 | Dynamic colour has a recorded static fallback; dark theme follows the system | `dynamicColorScheme` with no API-31 guard; a fixed light theme; a colour that ignores dark | `rg -n "dynamic(Light\|Dark)ColorScheme\|isSystemInDarkTheme" $SRC -g '*.kt'` | minor |
| E3 | Text is in `sp` from typography roles and scales | `fontSize` in `dp`; `Density(fontScale = 1f)`; scaling locked | `rg -n "fontSize = .*\.dp\|fontScale = 1f\|LocalDensity provides" $SRC -g '*.kt'` | major |
| E4 | Layout survives 200% font scale: no fixed-height text containers, no `maxLines = 1` on primary text | `Modifier.height(` / `size(` around `Text`; `maxLines = 1` on a title | `rg -n "maxLines = 1\|\.height\([0-9]+\.dp\)" $SRC -g '*.kt'`; requires dynamic test → `qa-mobile-android` | major |
| E5 | Layout branches on window size class, never on device type | `Build.MODEL`, `isTablet`, `screenWidthDp` choosing a layout | `rg -n "isTablet\|Build\.MODEL\|screenWidthDp\|smallestScreenWidthDp" $SRC -g '*.kt'` | major |
| E6 | The window size class is read once at the top and passed down | `currentWindowAdaptiveInfo()` called in leaf composables | `rg -n "currentWindowAdaptiveInfo\|calculateWindowSizeClass" $SRC -g '*.kt'` | minor |
| E7 | Wide windows get two panes or bounded content width; lists become grids | A phone layout stretched across an expanded window | `rg -n "widthIn\|ListDetailPaneScaffold\|NavigationSuiteScaffold\|GridCells" $SRC -g '*.kt'`; requires dynamic test → `qa-mobile-android` | major |
| E8 | `Scaffold` `innerPadding` is applied; no `fitsSystemWindows` in Compose | `Scaffold { _ -> … }` ignoring padding; content under the status bar | `rg -n "Scaffold\(" -A8 $SRC -g '*.kt'` | major |
| E9 | The keyboard does not cover the focused field | No `imePadding()` / `adjustResize` on a form screen | `rg -n "imePadding\|windowSoftInputMode" $SRC -g '*.kt' -g '*.xml'` | major |
| E10 | State is never conveyed by colour alone | `error` colour with no icon or text; a green / red dot as the only status | `rg -n "colorScheme\.error\|Color\.(Red\|Green)" $SRC -g '*.kt'` | major |
| E11 | Material 2 is not mixed with Material 3 `[M2]` | `androidx.compose.material.` imports beside `material3` | `rg -n "import androidx\.compose\.material\.[A-Z]" $SRC -g '*.kt'` | minor |
| E12 | Material 3 Expressive is adopted only on material3 1.5 or an existing opt-in `[M3-1.5]` | `MaterialExpressiveTheme` / `MotionScheme.expressive()` in a project on 1.4 with no opt-in decision | `rg -n "MaterialExpressiveTheme\|MotionScheme\.expressive" $SRC -g '*.kt'` | major |

---

## F — Navigation & deep links
*Owning skills: [`navigation`](../../navigation/SKILL.md) · [`notifications-and-links`](../../notifications-and-links/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| F1 | One navigation library; routes and keys are serializable types | Both Navigation 3 and Navigation Compose in one graph; string routes (`"orders/{id}"`) | `rg -n "navigation3\|androidx.navigation" -g '*.kts' -g 'libs.versions.toml'`; `rg -n "composable\(\"" $SRC -g '*.kt'` | major |
| F2 | Keys carry ids, not models or lambdas | A `NavKey` / route holding a model object or function | `rg -n ": NavKey" -B1 $SRC -g '*.kt'`; read each | major |
| F3 | `NavDisplay` has the saveable-state and ViewModel-store entry decorators `[N3]` | `NavDisplay` with no `entryDecorators`; a ViewModel living past a pop | `rg -n "NavDisplay" -A8 $SRC -g '*.kt'` | major |
| F4 | Screens take callbacks; `NavController` and the back stack stay in the host | `NavController` / `NavBackStack` passed into a leaf composable or ViewModel | `rg -n "navController: NavController\|backStack: NavBackStack" $SRC -g '*.kt'` | major |
| F5 | A destination loads its own data from its key | A screen reading state only the previous screen populated | read each `entry<…>` / `composable<…>` body for its load | major |
| F6 | Top-level areas use a navigation suite, each with its own back stack | A hand-built tab bar; one stack shared across tabs | `rg -n "NavigationSuiteScaffold\|NavigationBar\|NavigationRail" $SRC -g '*.kt'` | major |
| F7 | Back is predictive and never overridden | `onBackPressed()` override, a permanently enabled `BackHandler(true)`, a custom back arrow that does not pop | `rg -n "onBackPressed\|BackHandler\|PredictiveBackHandler" $SRC -g '*.kt'` | major |
| F8 | In-app navigation is not driven by ViewModel events or `LaunchedEffect(Unit)` | A `Channel` of navigation events; `LaunchedEffect(Unit) { navigate(…) }` | `rg -n "LaunchedEffect\(Unit\)" -A4 $SRC -g '*.kt'` | major |
| F9 | A URI maps to keys through one pure, validated function; bad input is ignored | `intent.data` routed unchecked; an unchecked `pathSegments[1]`; a link parameter passed to `startActivity` | `rg -n "intent\.data\|pathSegments\|getQueryParameter" -A5 $SRC -g '*.kt'` | blocker |
| F10 | Links are handled in `onCreate` and `onNewIntent` | Only one entry point handled; a `singleTop` activity that ignores new intents | `rg -n "onNewIntent\|handleIntent" $SRC -g '*.kt'` | major |
| F11 | App Link filters are narrow `https` with `autoVerify`; a custom scheme carries no secret | `pathPattern=".*"`, an auth code or token in `myapp://`, a missing `autoVerify` | `rg -n "autoVerify\|pathPattern\|android:scheme" -g 'AndroidManifest.xml'` | major |
| F12 | A sign-in gate on a route is client UX, not authorisation | A screen hidden by a flag with no server check noted | `rg -n "isSignedIn\|isAuthenticated" -B2 $SRC -g '*.kt'`; requires dynamic test → `qa-security` | major |
| F13 | Adaptive navigation uses scene strategies / adaptive scaffolds, not a second graph `[N3]` | A duplicate set of tablet routes | `rg -n "SceneStrategy\|ListDetailPaneScaffold" $SRC -g '*.kt'` | minor |

---

## G — Forms & input
*Owning skill: [`forms`](../../forms/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## H — Networking & realtime
*Owning skill: [`networking`](../../networking/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## I — Offline, storage & sync
*Owning skill: [`offline-and-storage`](../../offline-and-storage/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## J — Device features, permissions & native code
*Owning skills: [`device-features`](../../device-features/SKILL.md) · [`notifications-and-links`](../../notifications-and-links/SKILL.md) · [`system-integration`](../../system-integration/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## K — Security
*Owning fragment: [`mobile/_shared/security`](../../../../_shared/security/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `mobile/_shared/security/references/audit-checks.md` whose `Stacks` column names `android`, and the ids are the fragment's — finding `K3` is row K3 of the security fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## L — Privacy & store compliance
*Owning fragment: [`mobile/_shared/store-compliance`](../../../../_shared/store-compliance/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `mobile/_shared/store-compliance/references/audit-checks.md` whose `Stacks` column names `android`, and the ids are the fragment's — finding `L3` is row L3 of the store-compliance fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## M — Accessibility
*Owning skill: [`accessibility`](../../accessibility/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## N — Performance
*Owning skill: [`performance`](../../performance/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## O — Error resilience
*Owning skill: [`error-handling`](../../error-handling/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## P — Localization
*Owning skill: [`languages`](../../languages/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## Q — Motion & gestures
*Owning skill: [`animation`](../../animation/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## R — Testability & test ids
*Owning skill: [`test-ids`](../../test-ids/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## S — Dev-side tests
*Owning skill: [`unit-testing`](../../unit-testing/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## T — Release & signing
*Owning fragment: [`mobile/_shared/release`](../../../../_shared/release/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `mobile/_shared/release/references/audit-checks.md` whose `Stacks` column names `android`, and the ids are the fragment's — finding `T3` is row T3 of the release fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## U — Observability & logging
*Owning fragment: [`mobile/_shared/observability`](../../../../_shared/observability/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `mobile/_shared/observability/references/audit-checks.md` whose `Stacks` column names `android`, and the ids are the fragment's — finding `U3` is row U3 of the observability fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed.

---

## V — Comments & KISS
*Owning skills: [`ep-code-comments`](../../../../../engineering-practices/code-comments/SKILL.md) · CLAUDE.md § Comments and § Simplicity (KISS)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| V1 | No inline comments in a body | A `//` line inside a function or method body — a step marker, a restatement of the next line, a section banner | `rg -n "^\s+//[^/]" $SRC -g '*.kt'` | minor |
| V2 | A doc comment states a contract, not the signature | A doc comment that restates the name or signature (`Returns the user id`, `@param id the id`) on a property, DTO, getter or single-expression function | `rg -n -A1 "^\s*\* @(return\|param)\b" $SRC -g '*.kt'` | minor |
| V3 | No commented-out code, no `TODO` / `FIXME` left behind | A `//` line holding code, or a `TODO` / `FIXME` / `HACK` marker in committed source | `rg -n "^\s*//\s*(val\|var\|fun\|import\|return\|if)\b" $SRC -g '*.kt'` · `rg -n "TODO\|FIXME\|HACK" $SRC -g '*.kt'` | minor |
| V4 | A comment that exists because the code is unclear | A comment explaining what a badly named local or method does — the fix is the rename or extraction, not a reworded comment | Read the comment hits from V1; ask whether a name would carry it | major |
| V5 | No `interface` with one implementer | An abstraction introduced for one caller and one implementation, with no second real need | `rg -n "^(fun )?interface \w+" $SRC -g '*.kt'`; then count implementers per hit | major |
| V6 | No wrapper that only forwards | A class or function whose whole body delegates one call to the next layer (service → repository → ORM as three layers) | `rg -n -A2 "fun \w+\(.*\) =\s*$" $SRC -g '*.kt'`; read each hit for a single delegated call | major |
| V7 | No configurability nothing uses | An options bag, flag, generic parameter or extension point that no caller passes or varies | `rg -n "options: \|config: \|Config\(" $SRC -g '*.kt'`; then search for a call site that supplies it | major |
| V8 | A generated or scaffolded comment is removed | A template header, a framework placeholder comment or a wizard banner left in a source file, with no tool depending on it | `rg -n "Created by\|Generated by\|This file was\|Copyright \(c\)" $SRC` — skip generated sources (KSP / Room / Hilt output under `build/generated/`) | minor |

---

## W — Kotlin Multiplatform
*Owning skill: [`kotlin-multiplatform`](../../kotlin-multiplatform/SKILL.md)* — N/A unless Kotlin Multiplatform modules exist

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|

---

## X — In-app purchases
*Owning fragment: [`mobile/_shared/in-app-purchases`](../../../../_shared/in-app-purchases/references/audit-checks.md)*

This section holds no rows of its own. The rows are those of `mobile/_shared/in-app-purchases/references/audit-checks.md` whose `Stacks` column names `android`, and the ids are the fragment's — finding `X3` is row X3 of the in-app-purchases fragment. A row a static read cannot prove says **requires dynamic test → `qa-security`** and is reported as unverified, never as passed. Not applicable unless the app sells anything.
