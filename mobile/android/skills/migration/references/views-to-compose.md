# Views → Compose

Source: developer.android.com/develop/ui/compose/migrate/strategy. Views are in maintenance mode, not deprecated; the move is **incremental**, Views and Compose coexist until the last Fragment goes. A full rewrite on a branch is the anti-pattern. The seams are [`views-interop`](../../views-interop/SKILL.md); the target UI is [`ui-components`](../../ui-components/SKILL.md).

## Google's order

1. **New screens in Compose.** A Fragment returns a `ComposeView` from `onCreateView()` with `ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed`; Fragments and the Navigation component stay.
2. **New features on existing screens** as a `ComposeView` added to the layout, `setContent` after inflation.
3. **A common component library** — extract reusable composables into one package or module once two features need them; that is also where the design system lives. Theme from XML to Material 3 (`styling`): one theme source, mapped once, not two palettes.
4. **Replace features one screen at a time.** Simple screens first (welcome, confirmation, settings, mostly static data); mixed Views / Compose screens move to Compose bottom-up until the whole screen is composable.
5. **Remove Fragments and the Navigation component last.** Move to Navigation Compose (or Navigation 3, [`navigation-to-nav3`](navigation-to-nav3.md)) only after **every** destination is a screen-level composable. Until then, keep the Fragment-based navigation.

## Per-screen procedure

1. Pin behaviour with a test (Espresso or a screenshot) on the Views screen.
2. Write the composable with hoisted state and a screen ViewModel exposing one `uiState` ([`architecture`](../../architecture/SKILL.md)); keep the ViewModel if it exists — a LiveData ViewModel gets the Flow move first ([`livedata-rx-to-flow`](livedata-rx-to-flow.md)).
3. Swap: the Fragment's `onCreateView` returns the `ComposeView`; delete the XML layout and the binding class in the same commit.
4. Lists: `RecyclerView` + `ListAdapter` → `LazyColumn` with `key` and `contentType` ([`ui-components`](../../ui-components/SKILL.md)).
5. Carry the **test ids**: `Modifier.testTag` + `testTagsAsResourceId` at the root, the same names the Views screen used as `android:id`s so the QA suite does not change ([`test-ids`](../../test-ids/SKILL.md)).
6. Carry accessibility: labels, `contentDescription`, 48 dp targets, focus order ([`accessibility`](../../accessibility/SKILL.md)).

## Traps

- **`ComposeView` in a Fragment without the right composition strategy leaks** — the default disposes on window detach, which is wrong for a Fragment's view.
- Two themes at once: Material Components XML and Material 3 Compose drift; the mapping is a single converter or a re-skin decision ([`styling`](../../styling/SKILL.md)).
- `AndroidView` islands multiply; each is a screen not yet migrated, tracked on the list.
- Insets are handled twice (XML `fitsSystemWindows` and Compose) — pick one per screen.
- Process death: a Fragment that restored view state through `onSaveInstanceState` now needs `rememberSaveable` / `SavedStateHandle`.
- Do not migrate Views and raise `targetSdk` together — the edge-to-edge change at 35 hides which one moved the layout.

## Verify

- `rg -n "findViewById|ViewBinding|R.layout" -g '*.kt'` shrinks per commit; the screen's layout file is deleted.
- The pinned test passes against the Compose screen; TalkBack reads it in the same order.
