# targetSdk 35 → 36 → 37

**The one dated move.** Play requires new apps **and updates** to target API 36 since **2026-08-31** (extensions to 2026-11-01). `compileSdk` is 37 first; `targetSdk` follows, **one level per run**, set explicitly (AGP 9 defaults it to `compileSdk`, an unreviewed behaviour change).

Source for each level: developer.android.com/about/versions/<n>/behavior-changes-all and `-behavior-changes-<n>`. Read the page for the exact level; the table is what §4.3 verified plus the shape of the work.

| Target | Behaviour that changes | Work |
|---|---|---|
| **35** | **Edge-to-edge is enforced.** Content draws under system bars | [`styling`](../../styling/SKILL.md) insets (`Scaffold` / `WindowInsets`), `enableEdgeToEdge()` in the activity, XML screens fit via `ViewCompat.setOnApplyWindowInsetsListener` |
| **36** | **Predictive back is on by default**; **orientation, aspect-ratio and resizability locks are ignored on screens ≥ sw600dp** | Replace `onBackPressed()` / `KeyEvent` back handling with `BackHandler` / `OnBackPressedCallback`; make layouts adaptive ([`styling`](../../styling/SKILL.md) window size classes); remove `screenOrientation` locks that guard broken layouts |
| **37** | The large-screen rules have **no opt-out**; `ACCESS_LOCAL_NETWORK` permission for LAN access; background-audio foreground-service rules | Test on tablet / foldable / desktop-mode emulators; declare and request `ACCESS_LOCAL_NETWORK` where the app talks to LAN devices; re-check audio FGS types ([`system-integration`](../../system-integration/SKILL.md)) |

The 36 opt-outs that existed (`android:enableOnBackInvokedCallback`, the resizability manifest properties) are the **temporary** devices of that level; each is a finding with a dated removal.

## Procedure per level

1. Baseline green; `compileSdk` already ≥ the level.
2. Read the behaviour-changes page for the level — **all-apps** and **apps targeting** sections.
3. Raise `targetSdk` alone in its own commit.
4. Run the app on an emulator of that API level with the affected flows: back gesture, rotation, a tablet size class, permissions that changed.
5. Fix per behaviour; do not widen manifest opt-outs to get through.
6. Update the Play Console declarations that depend on it (foreground-service types, permissions) — [`mobile-<stack>:store-compliance`](../../../../_shared/store-compliance/SKILL.md).

## An existing app that stays on 35

Supported — an app that targets 35 keeps working and is **not** flagged for it, unless the Play deadline applies to its next update. Raising is this skill's, never a side effect.

## Verify

- `rg -n "targetSdk" -g '*.kts' -g '*.gradle'` shows the explicit value; it is one level above the previous commit.
- Predictive back works from the system gesture on a 36 emulator; a ≥ sw600dp window resizes without a locked layout.
