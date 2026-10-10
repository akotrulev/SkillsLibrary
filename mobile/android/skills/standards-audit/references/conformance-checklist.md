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
| D16 | `[Views]` A Fragment's binding is nulled in `onDestroyView` and not touched after | A `lateinit var binding` never cleared; a callback using `binding` after the view is gone | `rg -n "lateinit var binding\|_binding" $SRC -g '*.kt'`; read each Fragment for `onDestroyView` | major |
| D17 | `[Views]` Flows are collected with `viewLifecycleOwner` inside `repeatOnLifecycle(STARTED)` | `lifecycleScope.launch { flow.collect }` with `this`; `launchWhenStarted` | `rg -n "launchWhenStarted\|launchWhenResumed\|lifecycleScope.launch" $SRC -g '*.kt'`; read each hit's owner | major |
| D18 | `[Views]` Lists are `ListAdapter` + `DiffUtil` on the domain id | `notifyDataSetChanged()`; `areItemsTheSame` comparing positions; work in `onBindViewHolder` | `rg -n "notifyDataSetChanged\|areItemsTheSame" $SRC -g '*.kt'` | major |
| D19 | `[Views]` A `ComposeView` in a Fragment sets `DisposeOnViewTreeLifecycleDestroyed` before `setContent` | The default strategy in a Fragment; `setContent` before the strategy | `rg -n "ComposeView" -A4 $SRC -g '*.kt' -g '*.xml'` | major |
| D20 | `AndroidView` keeps state in `update`, releases in `onRelease`, and registers lifecycle-aware Views | A listener in `factory` capturing changing state; a `MapView` / player never released | `rg -n "AndroidView\(" -A10 $SRC -g '*.kt'` | major |
| D21 | `[Views]` Back goes through `OnBackPressedDispatcher`, not an `onBackPressed()` override | `override fun onBackPressed`; no `enableOnBackInvokedCallback` at target 36 | `rg -n "override fun onBackPressed\|enableOnBackInvokedCallback" $SRC -g '*.kt' -g '*.xml'` | major |
| D22 | `[Views]` New view access is ViewBinding; no `findViewById` or synthetics added | `findViewById` in new code; `kotlinx.android.synthetic` imports | `rg -n "findViewById\|kotlinx.android.synthetic" $SRC -g '*.kt'` | minor |
| D23 | `[Views]` Layouts carry no hardcoded text or `px`; actionable images have a `contentDescription`; targets ≥ 48 dp | `android:text="Save"`; `android:layout_width="40px"`; an `ImageButton` with none | `rg -n 'android:text="[^@]\|[0-9]px"' $SRC -g '*.xml'`; `rg -L "contentDescription" $SRC -g '*.xml'` | major |
| D24 | `[Views]` Edge-to-edge insets are applied to the View that needs them; the IME never hides the focused field | `fitsSystemWindows` hacks; no inset listener on a bottom bar; `adjustPan` forced on | `rg -n "setOnApplyWindowInsetsListener\|fitsSystemWindows\|windowSoftInputMode" $SRC -g '*.kt' -g '*.xml'` | major |
| D25 | `[Views]` A Views screen follows the one-`uiState` rule — no `SharedFlow` / `Channel` event for navigation or errors | `Channel<…>` / `SharedFlow` collected in a Fragment to navigate or show a toast | `rg -n "Channel<\|MutableSharedFlow\|receiveAsFlow" $SRC -g '*.kt'`; read each consumer | major |

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
| G1 | Form state is one draft in `uiState`; the validator is a pure function with tests | Validation inside a composable; a regex in `onValueChange`; state copied into a `remember` | `rg -n "Regex\(\|Patterns\.\|contains\('@'\)" $SRC -g '*.kt'`; read each hit's location | major |
| G2 | Text fields use one API per form — `TextFieldState` or value-based | Both in one screen; `remember { mutableStateOf("") }` shadowing ViewModel state | `rg -n "TextFieldState\|onValueChange" $SRC -g '*.kt'` | minor |
| G3 | Every field sets `KeyboardOptions` type and `ImeAction`; `Next` is wired | An email field with `KeyboardType.Text`; `ImeAction.Next` with no `KeyboardActions` / focus move | `rg -n "TextField\(" -A12 $SRC -g '*.kt'`; `rg -L "KeyboardOptions" $SRC -g '*Form*.kt'` | major |
| G4 | The IME never covers the focused field | A form with no `imePadding()` / inset handling; `adjustPan` as the fix | `rg -n "imePadding\|WindowInsets.ime\|windowSoftInputMode" $SRC -g '*.kt' -g '*.xml'`; read each form screen | major |
| G5 | Errors appear on focus loss or submit, clear on edit, are text plus `isError` | An error raised on first keystroke; colour only; no `supportingText` | `rg -n "isError\|supportingText" $SRC -g '*.kt'` | major |
| G6 | Server field errors map onto fields; unmapped ones show at form level | A `422` shown only as a toast; field names dropped | `rg -n "Validation\|errors\[" $SRC -g '*.kt'`; read the submit path | major |
| G7 | A submit is guarded in the ViewModel and carries one idempotency key per draft | Only `enabled = !pending`; a key regenerated per attempt | `rg -n "Pending\|Idempotency" $SRC -g '*.kt'` | major |
| G8 | A secret field is never in `SavedStateHandle`, `rememberSaveable`, logs or analytics | `savedStateHandle["password"]`; `rememberSaveable { mutableStateOf(password) }` | `rg -n "rememberSaveable\|savedStateHandle\[" $SRC -g '*.kt'`; read each hit's name | blocker |
| G9 | Autofillable fields declare `ContentType`; sign-in uses Credential Manager | A login with no `contentType`; Google One Tap / `GoogleSignIn` / FIDO2 API in new code | `rg -n "ContentType\|GoogleSignIn\|BeginSignInRequest\|Fido2" $SRC -g '*.kt'` | major |
| G10 | Interactive fields and the submit button carry a static `testTag` | A field with none; a tag built from user text or an index | `rg -n "testTag" $SRC -g '*.kt'`; compare to the field list | minor |

---

## H — Networking & realtime
*Owning skill: [`networking`](../../networking/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| H1 | One client per API; a second HTTP layer is not added beside an existing one | Retrofit and Ktor and a hand-rolled `HttpURLConnection` in one module | `rg -n "Retrofit.Builder\|HttpClient\(\|HttpURLConnection" $SRC -g '*.kt'` | major |
| H2 | Every request has connect, read, write and a per-class call timeout | `OkHttpClient()` with defaults; no `callTimeout` | `rg -n "callTimeout\|readTimeout\|OkHttpClient" $SRC -g '*.kt'` | major |
| H3 | `CancellationException` is rethrown; no `catch (e: Exception)` swallows it | `runCatching { api.call() }` around a suspend call with no rethrow | `rg -n "runCatching\|catch \(e: Exception\|catch \(e: Throwable" $SRC -g '*.kt'` | major |
| H4 | Requests are owned by `viewModelScope` / `collectLatest`; no `GlobalScope`, no unowned scope | `GlobalScope.launch`; `CoroutineScope(Dispatchers.IO).launch` in a repository | `rg -n "GlobalScope\|CoroutineScope\(Dispatchers" $SRC -g '*.kt'` | major |
| H5 | Retries live in one interceptor: ≤ 2 for reads, jittered, `Retry-After` honoured, none offline | A retry loop in a ViewModel and in an interceptor; fixed delay; a `POST` retried with no key | `rg -n "retry\|Retry-After\|delay\(" $SRC -g '*.kt'` | major |
| H6 | A write retried or queued carries an `Idempotency-Key` created once per intent | No key on a `POST`; a key generated per attempt | `rg -n "Idempotency" $SRC -g '*.kt'`; read each `@POST` | major |
| H7 | A decode failure is `Drifted` and renders as failed, never empty | `getOrDefault(emptyList())`; `ignoreUnknownKeys` with `?: emptyList()` on a required field | `rg -n "getOrDefault\|getOrNull\(\)\|emptyList\(\)" $SRC -g '*.kt'` | major |
| H8 | The `Authenticator` refreshes once (single-flight), replays once, never loops, uses a separate client | N parallel `401`s refresh N times; the refresh client shares the authenticator | `rg -n "Authenticator\|authenticate\(" -A15 $SRC -g '*.kt'` | blocker |
| H9 | No token, body or PII is logged; no logging interceptor in release | `Level.BODY` outside debug; `Log.d(…token…)` | `rg -n "HttpLoggingInterceptor\|Level\.BODY\|Log\.[dv]\(" $SRC -g '*.kt'` | blocker |
| H10 | `https` only; cleartext and trust are decided in Network Security Config | `usesCleartextTraffic="true"`; a trust-all `X509TrustManager`; `HostnameVerifier { _, _ -> true }` | `rg -n "usesCleartextTraffic\|X509TrustManager\|HostnameVerifier\|cleartextTrafficPermitted" $SRC -g '*.kt' -g '*.xml'` | blocker |
| H11 | No user CA outside `<debug-overrides>`; a pin-set has a backup pin and an expiry | `<certificates src="user"/>` in a base config; one pin; none | `rg -n 'src="user"\|<pin ' $SRC -g '*.xml'` | major |
| H12 | The app revalidates on foreground and on reconnect; connectivity is a callback `Flow`, not a ping | A `Runtime.exec("ping")`; no refetch on return | `rg -n "registerDefaultNetworkCallback\|isReachable\|repeatOnLifecycle" $SRC -g '*.kt'` | major |
| H13 | A WebSocket is opened only while the screen is `STARTED` and closed after; reconnect is jittered and followed by a refetch | A socket opened in a composable body or a singleton and never closed; no refetch after reconnect | `rg -n "newWebSocket\|WebSocket" $SRC -g '*.kt'` | major |
| H14 | No blocking network or `runBlocking` on the main thread | `runBlocking` outside the `Authenticator`; `.execute()` in a ViewModel | `rg -n "runBlocking\|\.execute\(\)" $SRC -g '*.kt'` | blocker |
| H15 | `[KMP]` The shared Ktor client sets `HttpTimeout`, bounded `HttpRequestRetry` and single-flight `Auth` | A Ktor client with no timeout plugin | `rg -n "HttpTimeout\|HttpRequestRetry\|HttpClient\(" $SRC -g '*.kt'` | major |

---

## I — Offline, storage & sync
*Owning skill: [`offline-and-storage`](../../offline-and-storage/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| I1 | New databases are Room 3 (`androidx.room3`) on KSP with a `SQLiteDriver`; Room 2.8 stays `[Room2]` | `kapt(`; a new database on `androidx.room`; both groups on one database | `rg -n "kapt\|androidx.room:\|androidx.room3" $SRC -g '*.kts' -g '*.toml' -g '*.kt'` | major |
| I2 | Room 3 DAOs are `suspend` or `Flow`; no `LiveData` / Rx return types in new code; integrations come from `room3-*` artifacts | `LiveData<List<…>>` DAO on Room 3; `PagingSource` with no `room3-paging` | `rg -n "LiveData<\|Observable<\|Flowable<\|PagingSource<" $SRC -g '*.kt'` | major |
| I3 | Every version bump has a migration and a committed schema JSON; no destructive fallback on user data | `fallbackToDestructiveMigration()` on a user database; `version` bumped, `schemas/` unchanged | `rg -n "fallbackToDestructiveMigration\|exportSchema" $SRC -g '*.kt'`; `ls */schemas` | blocker |
| I4 | Entities, DTOs and domain types are separate; no entity in a composable | An `@Entity` carrying `@Serializable` and shown directly | `rg -n "@Entity" -A8 $SRC -g '*.kt'` | minor |
| I5 | No main-thread database or DataStore read | `allowMainThreadQueries()`; `runBlocking { dataStore.data.first() }` | `rg -n "allowMainThreadQueries\|runBlocking" $SRC -g '*.kt'` | blocker |
| I6 | Settings are DataStore, one instance per file; new code adds no `SharedPreferences` | `getSharedPreferences` in new code; two `preferencesDataStore` on one name | `rg -n "getSharedPreferences\|preferencesDataStore\|PreferenceManager" $SRC -g '*.kt'` | major |
| I7 | **No `EncryptedSharedPreferences`, `EncryptedFile`, `MasterKey` or `security-crypto` in new code** | Any import of `androidx.security.crypto` | `rg -n "androidx.security.crypto\|EncryptedSharedPreferences\|MasterKey" $SRC -g '*.kt' -g '*.kts' -g '*.toml'` | major |
| I8 | Brownfield `EncryptedSharedPreferences` is flagged with a migration owner, not rewritten as a side effect | A use with no migration note in the report | `rg -n "EncryptedSharedPreferences" $SRC -g '*.kt'` | major |
| I9 | Secrets are Keystore-backed (Tink `Aead` over a Keystore-wrapped keyset, or a Keystore key); a decrypt failure means signed out | A token in plain DataStore, Room, files or `SharedPreferences`; a hardcoded passphrase | `rg -n "KeyGenParameterSpec\|AndroidKeysetManager\|accessToken\|refreshToken" $SRC -g '*.kt'`; read each store | blocker |
| I10 | Backup rules exclude databases, DataStore, keyset and tokens | `allowBackup="true"` with no `dataExtractionRules` and `fullBackupContent` | `rg -n "allowBackup\|dataExtractionRules\|fullBackupContent" $SRC -g '*.xml'` | major |
| I11 | Room (or the repository's source of truth) feeds the UI; a failed refresh keeps rows and marks them stale | A screen that blanks on a failed refresh; the network response fed straight to the UI | `rg -n "fun refresh\|observe\w*\(\)" $SRC -g '*.kt'` | major |
| I12 | Offline writes use an outbox with idempotency keys drained by unique WorkManager work | An in-memory retry list; `GlobalScope` sync; non-unique periodic work | `rg -n "enqueueUniqueWork\|OneTimeWorkRequest\|GlobalScope" $SRC -g '*.kt'` | major |
| I13 | A storage failure degrades to memory and surfaces; a user database is never auto-wiped | A `catch { }` around a write; `deleteDatabase` on open failure of a user database | `rg -n "SQLiteFullException\|deleteDatabase\|catch \(e: IOException" $SRC -g '*.kt'` | major |
| I14 | Caches are size-bounded and rebuildable; writes are atomic | An unbounded cache directory; a direct overwrite of a good file | `rg -n "cacheDir\|filesDir\|renameTo\|LruCache" $SRC -g '*.kt'` | minor |

---

## J — Device features, permissions & native code
*Owning skills: [`device-features`](../../device-features/SKILL.md) · [`notifications-and-links`](../../notifications-and-links/SKILL.md) · [`system-integration`](../../system-integration/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| J1 | Permissions are requested in context after a pre-prompt; none at launch | `requestPermissions` in `Application.onCreate` or the first screen's init | `rg -n "RequestPermission\|requestPermissions\|RequestMultiplePermissions" $SRC -g '*.kt'`; read each call site | major |
| J2 | A denied screen works: what is unavailable, the alternative, **Open Settings**; status is rechecked on resume | A blank preview on denial; a cached `granted` flag; no Settings link | `rg -n "shouldShowRequestPermissionRationale\|ACTION_APPLICATION_DETAILS_SETTINGS" $SRC -g '*.kt'` | major |
| J3 | The manifest declares only used permissions, with `maxSdkVersion` where retired | An unused `READ_CONTACTS`; `WRITE_EXTERNAL_STORAGE` at the current target | `rg -n "uses-permission" $SRC -g 'AndroidManifest.xml'` | major |
| J4 | Photos and video are picked with the photo picker; `READ_MEDIA_*` only for core broad media access | `READ_MEDIA_IMAGES` or `READ_EXTERNAL_STORAGE` for an upload or avatar | `rg -n "READ_MEDIA\|READ_EXTERNAL_STORAGE\|PickVisualMedia" $SRC -g '*.kt' -g '*.xml'` | major |
| J5 | No `MANAGE_EXTERNAL_STORAGE`; documents use SAF or MediaStore | The permission in the manifest | `rg -n "MANAGE_EXTERNAL_STORAGE" $SRC -g '*.xml'` | blocker |
| J6 | A picked `Uri` is treated as temporary and untrusted; reads are off the main thread | `File(uri.path)`; a full bitmap decoded in a click handler | `rg -n "uri\.path\|decodeStream\|openInputStream" $SRC -g '*.kt'` | major |
| J7 | CameraX is bound to a lifecycle owner; a system capture intent is used when enough | A camera held after the screen leaves; `CAMERA` requested for a plain photo | `rg -n "bindToLifecycle\|ProcessCameraProvider\|TakePicture" $SRC -g '*.kt'` | major |
| J8 | Location requests coarse and fine together; precise only when needed; background is separate and declared | `ACCESS_BACKGROUND_LOCATION` in the same flow; fine-only for "stores near me" | `rg -n "ACCESS_COARSE_LOCATION\|ACCESS_FINE_LOCATION\|ACCESS_BACKGROUND_LOCATION" $SRC -g '*.kt' -g '*.xml'` | major |
| J9 | Location updates are removed with the lifecycle and never logged | `requestLocationUpdates` with no `removeLocationUpdates` / `awaitClose` | `rg -n "requestLocationUpdates\|removeLocationUpdates\|awaitClose" $SRC -g '*.kt'` | major |
| J10 | `BiometricPrompt` unlocks a Keystore key through a `CryptoObject`; enrolment and hardware states have screens | A success callback that sets `isUnlocked = true`; no `canAuthenticate` check | `rg -n "BiometricPrompt\|CryptoObject\|canAuthenticate\|setUserAuthenticationRequired" $SRC -g '*.kt'` | blocker |
| J11 | Sign-in uses Credential Manager; cancellation is silent; the server owns the passkey challenge | `GoogleSignIn` / One Tap / FIDO2 in new code; the challenge generated on the device | `rg -n "CredentialManager\|GoogleSignIn\|BeginSignInRequest\|Fido2" $SRC -g '*.kt'` | major |
| J12 | `ACCESS_LOCAL_NETWORK` is requested in context only where a feature reaches the LAN, and the target is not raised for it | The permission with no LAN feature; a targetSdk bump in the same change | `rg -n "ACCESS_LOCAL_NETWORK\|NsdManager\|targetSdk" $SRC -g '*.kt' -g '*.kts' -g '*.xml'` | major |

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
