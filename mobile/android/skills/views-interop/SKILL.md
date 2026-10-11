---
name: views-interop
description: Use when the Android codebase is XML Views or mixes Views and Compose — ViewBinding, Fragments and view lifecycle, RecyclerView with ListAdapter, ComposeView with DisposeOnViewTreeLifecycleDestroyed, AndroidView, edge-to-edge in Views. Triggers "add a screen to this Views app", "embed Compose in a Fragment", "wrap a View in Compose", "ComposeView leaks". Do NOT use for a new Compose screen (`mobile-android:ui-components`) or a rewrite (`-migration`).
---

# Android — Views and Interop

Views are in **maintenance mode** (Google I/O 2026) — they are not deprecated, and most shipping apps are full of them. This skill covers the **Views lane**: how to add to and change an XML codebase safely, and the **two seams** between Views and Compose, in both directions. New screens in a Compose-first app are [`ui-components`](../ui-components/SKILL.md); moving a codebase from Views to Compose is [`mobile-android:migration`](../migration/SKILL.md). Sibling: [`mobile-ios:uikit`](../../../ios/skills/uikit/SKILL.md).

## Version lane

| Concern | Primary | Supported / notes |
|---|---|---|
| New screens | Compose — a Views app gets Compose for *new* screens through the seams below | A pure-Views app stays Views until a migration is chosen; do not mix styles in one screen without a reason |
| View access | **ViewBinding** (`buildFeatures { viewBinding = true }`) | Kotlin synthetics and `findViewById` appear in older code — match in files you do not own; `kotlin-android-extensions` is gone, never add |
| Screens | Fragments in a single `FragmentContainerView` activity + Navigation component, or Navigation Compose host | Multi-activity apps are present in many codebases — extend, do not collapse |
| Compose in Views | `ComposeView` with `ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed` in Fragments | `DisposeOnDetachedFromWindowOrReleasedFromPool` for `RecyclerView` items |
| Views in Compose | `AndroidView` with `update` | `AndroidViewBinding` for an inflated layout |
| Lists | `RecyclerView` + `ListAdapter` + `DiffUtil` | `ListView` and manual `notifyDataSetChanged` in older code |
| Toolchain | AGP 9 / Kotlin 2.4 primary; AGP 8 in brownfield | Never raised as a side effect |

Detect first: `viewBinding` / `dataBinding` flags, Fragments or Activities, XML themes (AppCompat vs Material Components), RxJava / LiveData, `kapt` and the DI container. **Match what is there.** DataBinding is a lane: do not add it to a ViewBinding project, do not rip it out of one that has it.

## When to use

- Adding or changing a screen, a layout or an adapter in an XML codebase
- Embedding a Compose screen or component in a Fragment or a layout
- Wrapping a View (`MapView`, `PlayerView`, `WebView`, an ad view) in Compose
- A `ComposeView` that leaks, a Fragment whose binding crashes after `onDestroyView`
- Insets, edge-to-edge and the IME in a Views activity

## When NOT to use

- A new screen in an app that is mostly Compose → [`ui-components`](../ui-components/SKILL.md)
- Replacing Views with Compose, Java → Kotlin, LiveData / Rx → Flow → [`mobile-android:migration`](../migration/SKILL.md)
- State ownership → [`architecture`](../architecture/SKILL.md) · routes → [`navigation`](../navigation/SKILL.md)
- Theme and tokens → [`styling`](../styling/SKILL.md) (a Material Components XML theme is read here, written there)
- Another stack → `mobile-ios:uikit`, `mobile-react-native:native-modules`

## Inputs needed

- ViewBinding / DataBinding / neither; Fragments or Activities; the navigation owner
- Whether Compose is already on the classpath (BOM, Kotlin Compose plugin)
- The state holder in use (ViewModel + `StateFlow`, LiveData, Rx)

## Fragments — the view has its own lifecycle

A Fragment outlives its view. **The binding is nulled in `onDestroyView`**; a reference after that is a crash or a leak.

```kotlin
@AndroidEntryPoint
class OrdersFragment : Fragment(R.layout.fragment_orders) {

    private val viewModel: OrdersViewModel by viewModels()
    private var binding: FragmentOrdersBinding? = null

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        val views = FragmentOrdersBinding.bind(view).also { binding = it }
        val adapter = OrdersAdapter(onClick = viewModel::onOrderSelected)
        views.list.adapter = adapter
        views.refresh.setOnRefreshListener(viewModel::refresh)

        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state -> render(views, adapter, state) }
            }
        }
    }

    override fun onDestroyView() {
        binding = null
        super.onDestroyView()
    }
}
```

- **Collect with `viewLifecycleOwner`, never `this`**, and wrap in `repeatOnLifecycle(STARTED)` (or `flowWithLifecycle`) so collection stops in the background and restarts on return. `lifecycleScope.launchWhenStarted` is deprecated — never use it.
- A `Fragment(layout)` constructor with `FragmentXBinding.bind(view)` avoids the inflate boilerplate; the nullable `binding` is cleared in `onDestroyView`.
- **One `uiState` rule applies here too** (D26): the Fragment renders state and sends plain calls to the ViewModel; there is no `SharedFlow` / `Channel` event for "navigate" or "show error". The outcome is a field the Fragment consumes and the ViewModel clears.
- Arguments: Navigation Safe Args or `requireArguments()` with a typed key; **never a mutable bundle shared across fragments** — shared state is a ViewModel scoped to the nav graph (`by navGraphViewModels`) or the activity (`by activityViewModels`, used sparingly).
- A Fragment result: the Fragment Result API (`setFragmentResultListener`) or a shared ViewModel — never a direct reference to another Fragment.
- **Fragment transactions only in the navigation owner**; not from a ViewModel, not from a View.
- Process death: ViewModel + `SavedStateHandle` as in [`architecture`](../architecture/SKILL.md); a View with state-less `id`s does not restore — every restorable View has an `android:id`.

## `RecyclerView`

`ListAdapter` + `DiffUtil` on the domain id, `onBind` only assigns, no `notifyDataSetChanged`, click lambdas capture ids, and empty/loading/failed is a sibling view scoped to the list body. The adapter sample is in [`references/recyclerview.md`](references/recyclerview.md).

## Compose inside Views — `ComposeView`

```kotlin
class SummaryFragment : Fragment() {

    private val viewModel: SummaryViewModel by viewModels()

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View =
        ComposeView(requireContext()).apply {
            setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed)
            setContent {
                AppTheme {
                    val state by viewModel.uiState.collectAsStateWithLifecycle()
                    SummaryContent(state = state, onRetry = viewModel::refresh)
                }
            }
        }
}
```

- **In a Fragment, always `DisposeOnViewTreeLifecycleDestroyed`** — the default (`DisposeOnDetachedFromWindowOrReleasedFromPool`) disposes the composition when the view detaches during a Fragment back-stack operation and **loses `rememberSaveable` state** when the view returns. The composition then lives until the Fragment's *view lifecycle* ends.
- In a `RecyclerView` item, **keep the default** `DisposeOnDetachedFromWindowOrReleasedFromPool` — pooled holders release the composition. In a plain `Activity`, `setContent { }` from `androidx.activity.compose` is enough.
- The Compose theme wraps the content (`AppTheme`) and reads the same tokens as the XML theme where both exist; a Views-only theme is not re-implemented — [`styling`](../styling/SKILL.md) owns the mapping (`MdcTheme` is gone; use the app's Material 3 theme or an explicit mapping).
- **State flows one way**: the ViewModel owns it; the `ComposeView` collects it with `collectAsStateWithLifecycle`; callbacks go up as function parameters. A `ComposeView` never reaches into a Fragment.
- Multiple `ComposeView`s on one screen are fine; **more than a handful in one list** is a rewrite signal, not a tuning problem.
- In XML: `<androidx.compose.ui.platform.ComposeView android:id="@+id/summary" … />`, then `binding.summary.setContent { }` after `setViewCompositionStrategy`.

## Views inside Compose — `AndroidView`

```kotlin
@Composable
fun PlayerSurface(player: Player, modifier: Modifier = Modifier) {
    AndroidView(
        factory = { context -> PlayerView(context).apply { useController = false } },
        update = { view -> view.player = player },
        onRelease = { view -> view.player = null },
        modifier = modifier,
    )
}
```

- `factory` runs **once**; every state-dependent assignment goes in `update`, which re-runs when the state it reads changes. A listener registered in `factory` that captures changing state is stale — register in `update` and clear in `onRelease`.
- **`onRelease` releases what the View holds** (players, map handles, listeners); lifecycle-aware Views (`MapView`) also need a `LifecycleEventObserver` via `LocalLifecycleOwner` forwarding `onResume` / `onPause` / `onDestroy`.
- `AndroidViewBinding(ItemLegacyBinding::inflate)` embeds an XML layout during a migration.
- Do not nest a scrolling View in a scrolling composable on the same axis; give it a bounded height.
- `WebView`: first-party content, JavaScript off by default, file access off, `shouldOverrideUrlLoading` allow-list, debugging off in release — [`mobile-<stack>:security`](../../../_shared/security/references/android.md) § 5.

## Edge-to-edge, insets and the IME in Views

Edge-to-edge is **enforced at targetSdk 35**; predictive back is on at 36.

- Call `enableEdgeToEdge()` before `super.onCreate` in the Activity; handle insets with `ViewCompat.setOnApplyWindowInsetsListener(view) { v, insets -> … }` reading `WindowInsetsCompat.Type.systemBars()` / `ime()` — **apply the inset as padding or margin to the View that needs it, then return `WindowInsetsCompat.CONSUMED`** only when children should not get it.
- A scrolling screen uses `android:clipToPadding="false"` with bottom inset padding so content scrolls under the navigation bar; a bottom bar takes the bottom inset itself.
- The IME: `ViewCompat.setWindowInsetsAnimationCallback` for synchronised movement, or `adjustResize` plus an `ime()` inset listener; a focused `EditText` stays visible (`android:windowSoftInputMode="adjustResize"` and a `ScrollView`).
- Back: `OnBackPressedDispatcher` + `OnBackPressedCallback` (never `onBackPressed()` override — deprecated, ignored by predictive back); opt in with `android:enableOnBackInvokedCallback="true"`.

## Resources, themes and accessibility in XML

- Strings in `strings.xml` with `tools:ignore` only with a reason; no hardcoded text in layouts; dimensions in `dp` / `sp`, never `px`; touch targets ≥ **48 dp** (`minWidth` / `minHeight` or padding); `contentDescription` on every actionable `ImageView` and `android:importantForAccessibility="no"` on decoration.
- **Test ids are `android:id`** — PascalCase-ish static ids (`@+id/orders_list` is the convention; the Appium-visible `resource-id` is the id) on every interactive View and list container; **never `contentDescription` as an id** ([`test-ids`](../test-ids/SKILL.md)).
- `ConstraintLayout` / `LinearLayout` flat hierarchies; no deeply nested weights; `RecyclerView`, not `ScrollView` + `LinearLayout`, for unbounded content.
- Theme attributes (`?attr/colorPrimary`, `?attr/textAppearanceBodyLarge`), not hex literals, in layouts; night resources in `values-night`; `Theme.Material3.*` parent.

## Rules

- Match the codebase's binding and navigation style; add Compose only through the two seams.
- ViewBinding access is nulled in `onDestroyView`; collection uses `viewLifecycleOwner` + `repeatOnLifecycle`.
- `ListAdapter` + `DiffUtil` on domain ids; `onBind` only assigns; no `notifyDataSetChanged`.
- `ComposeView` in a Fragment uses `DisposeOnViewTreeLifecycleDestroyed`; in a pooled item, the default.
- `AndroidView` puts state in `update` and releases in `onRelease`.
- One `uiState`, no event channel, in Views as in Compose (D26).
- Edge-to-edge and insets are handled; the IME never hides the focused field.
- Every interactive View carries a static `android:id`; every actionable image a `contentDescription`.

## What NOT to do

- No `findViewById` or synthetic imports in new code; no `lateinit var binding` that is never cleared in a Fragment.
- No `lifecycleScope.launchWhenStarted`; no collecting in `onCreateView` with `this` as the lifecycle owner.
- No `Handler().postDelayed` for UI timing; no `AsyncTask`; no `Thread` + `runOnUiThread` for I/O.
- No `ComposeView` with the default strategy inside a Fragment; no `setContent` before the strategy is set.
- No state duplicated in a View's field **and** the ViewModel; no ViewModel reference captured in an `AndroidView` factory.
- No `onBackPressed()` override; no `adjustPan` hacks for a covered field.
- No Compose "wrapper" `Fragment` per tiny composable; no second navigation library beside the one present.
- No `dataBinding` added to a ViewBinding project; no rewrite of a working screen as a side effect.

## Generation steps

1. Detect the lane: binding, Fragments/Activities, theme parent, DI, the state holder, whether Compose is present.
2. Read two existing screens and match their structure.
3. Write the layout XML (themed, inset-aware, with ids and descriptions) and the Fragment/Activity with `viewLifecycleOwner` collection.
4. Add the adapter with `ListAdapter`/`DiffUtil` where a list exists.
5. For Compose in Views: set the strategy, wrap in the app theme, collect state with lifecycle; for Views in Compose: `factory` / `update` / `onRelease`.
6. Handle insets, back and the IME; add ids.
7. Add ViewModel unit tests; Fragment tests are `FragmentScenario` with Robolectric ([`unit-testing`](../unit-testing/SKILL.md)).

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Build clean; Android Lint (`ViewBinding`, `UnusedResources`, `HardcodedText`, `ContentDescription`), detekt and ktlint pass.
- Rotate and navigate back: no crash from a stale binding; a `ComposeView` keeps its `rememberSaveable` state across a Fragment back-stack pop; LeakCanary (debug) shows no retained view.
- With the IME open and font scale 200 %: the focused field and the list's last row stay reachable; edge-to-edge shows content under the bars with correct padding.
- TalkBack reads every actionable View; Layout Inspector shows a flat hierarchy.
- Dev-side tests: [`mobile-android:unit-testing`](../unit-testing/SKILL.md).

## Handoffs

- New Compose screens → [`ui-components`](../ui-components/SKILL.md) · theme mapping → [`styling`](../styling/SKILL.md)
- State and ViewModels → [`architecture`](../architecture/SKILL.md) · routes → [`navigation`](../navigation/SKILL.md)
- Rewrites, Rx / LiveData → Flow → [`mobile-android:migration`](../migration/SKILL.md)
- Test ids → [`test-ids`](../test-ids/SKILL.md) · accessibility → `mobile-android:accessibility`
- WebView and manifest hardening → [`mobile-<stack>:security`](../../../_shared/security/SKILL.md)
