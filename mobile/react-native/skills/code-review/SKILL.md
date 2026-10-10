---
name: mobile-react-native-code-review
description: Use when reviewing a React Native / Expo diff — text outside `<Text>`, hand-edited `ios/` or `android/`, un-virtualized lists, missing timeouts and failed states, untagged elements, secrets in `EXPO_PUBLIC_*`, unvalidated links, motion off the UI thread — plus a simulator screenshot pass. Triggers "review this screen", "review this PR", "is this RN code ok". Do NOT use for a whole-repo audit (`mobile-react-native-standards-audit`), explanations (`-basics`) or writing code.
---

# React Native / Expo — Code Review

A **hostile review of one diff** against the conformance checklist's rows and CLAUDE.md § Mobile code rules, then a **screenshot pass** on the running app. Findings go in the standard severity table; the review **does not rewrite** — it points, and the `mobile-react-native` agent (or the author) fixes. A whole-repo sweep with a saved report is [`standards-audit`](../standards-audit/SKILL.md), which reuses these checks at repo scale.

## Version lane

Detect before flagging: Expo SDK and RN (`package.json`), Expo Router or bare React Navigation, React Compiler on or off (`reactCompiler` in `app.json`), Gesture Handler / FlashList / MMKV / RNTL majors, `ios/` and `android/` tracked (`[bare]`) or ignored (CNG).

| Lane | Review consequence |
|---|---|
| **57 primary** | The rows as written |
| `[SDK58]` | 58-only APIs are correct on 58 and a finding on 57; the reverse for 57 workarounds after an upgrade |
| 55–56 / 54 floor | Apply the rows keyed to that SDK; never flag a down-level project for lacking a 57 API |
| Below 54 | One finding (A1) plus a [`migration`](../migration/SKILL.md) run — do not review against rules it cannot meet |

A manual `useMemo` / `useCallback` is a finding only when the React Compiler is on; a `forwardRef` only on React 19; an `estimatedItemSize` only on FlashList 2.

## When to use

- A `.ts` / `.tsx` / `app.json` / `app.config.*` / config-plugin diff, before merge
- Step 5 of the agent: the whole change set, after the quality layers
- "Why does this jank / crash on Android only / lose its state?"

## When NOT to use

- Whole codebase, saved re-runnable report → [`standards-audit`](../standards-audit/SKILL.md)
- Explaining a concept → [`basics`](../basics/SKILL.md); writing code → the owning feature skill
- Reviewing **E2E test code** (Appium / Maestro) → peer `qa-mobile-typescript`
- Pen-test or runtime security → peer `qa-security` (`mobile-app-scan`, `mobile-runtime-testing`)
- A spec-versus-code audit → `code-auditor`

## Inputs needed

1. **The diff** (files or `git diff` range) and the screens it touches
2. **Lane facts** above, from `package.json` and `app.json`
3. **Whether a simulator / emulator is available** for the screenshot pass

## Procedure

1. **Map the diff to checklist sections** with the table below; open [`conformance-checklist.md`](../standards-audit/references/conformance-checklist.md) at only those sections and run each row's *Find it with* recipe **over the changed files**.
2. **Read the code at every hit.** A grep hit is a lead, not a finding.
3. **Verify the rule's owner** when a row is ambiguous — load the owning skill; the skill wins over the checklist, and the disagreement is reported.
4. **Run the screenshot pass** (below) if a device is available; otherwise say it was not run.
5. **Write the table**; one row per defect family with a count, not per site.

| The diff touches | Sections |
|---|---|
| `package.json`, `app.json`, `eas.json`, config plugins | A, B, K, L, T |
| Screens, components, lists, markup | D, E, M, N, R |
| Routes, links, notifications | F, J, K |
| Forms, inputs | G, M |
| API client, queries, sockets | H, O, K |
| Storage, caches, tokens | I, K |
| Device APIs, permissions, native modules | J, K, L |
| Animation, gestures | Q, N, M |
| Strings, formatting | P |
| State, stores, DI | C, V |
| Tests | S, R |
| Purchases | X |

## The rules every diff is held to (§5, in review form)

| Check | Bad sign | Severity |
|---|---|---|
| Text only inside `<Text>` | A string or `{value}` as a direct child of `View` — crashes on release | blocker |
| Secrets stay out of the bundle | A key or token in `EXPO_PUBLIC_*`, `app.json` `extra`, or source; a token in `AsyncStorage` / MMKV | blocker |
| Native edits live in config | A change under `ios/` or `android/` on a CNG project — the next `prebuild --clean` erases it | blocker |
| TLS only | `usesCleartextTraffic`, `NSAllowsArbitraryLoads` without a recorded reason | blocker |
| Links and push payloads are validated | A route built from an unchecked URL / payload field | major |
| Every request has a timeout | `fetch` with no `AbortSignal.timeout`, a spinner that can run forever | major |
| Data regions have all states | No failed / stale / offline path; a failure that blanks the toolbar and the screen; offline shown as a server error | major |
| Failures surface in one persistent banner | A `console.log`-only catch, an `Alert` that vanishes, a swallowed rejection | major |
| Unbounded lists are virtualized | `ScrollView` + `.map` over server data; `FlatList` where the project uses FlashList / Legend List | major |
| Server state in TanStack Query | A fetched list copied into Zustand / Context | major |
| Animation on the UI thread | `Animated` JS-driver or `setState` per frame; animating `width` / `top` instead of transform / opacity | major |
| Focus and resume revalidate | No `focusManager` / `AppState` wiring; stale data after returning to foreground | major |
| Every interactive element and list container has a `testID` | A `Pressable` / `TextInput` / list without one; a `testID` built from an index, GUID or state value; the accessibility label used as an id | major |
| Accessible | An icon-only `Pressable` with no `accessibilityLabel`; `allowFontScaling={false}`; target < 44 pt | major |
| Permissions asked in context | A permission requested on launch; no denied-path screen | major |
| No `@react-navigation/*` in an Expo Router app (SDK 56+) | An import of it beside `expo-router` | major |
| Compiler-aware memoization | Hand-rolled `useMemo` / `useCallback` with the Compiler on | minor |
| No inline comment, no commented-out code, no `TODO` | `//` inside a body | minor |
| No unearned abstraction | An interface with one implementer; a wrapper that only forwards | major |

## The screenshot pass (Step 5)

Only when a simulator or emulator is available and the app builds; otherwise report "screenshot pass not run" and why. Never build inside a `Gate: none` plan task.

```bash
xcrun simctl io booted screenshot ios-<screen>.png
adb exec-out screencap -p > android-<screen>.png
```

`Read` each image. Capture the changed screens in **light and dark**, with **large text** (system font scale) and in each of loading, loaded, failed and empty where the diff changes them. Check against the diff, not against taste: safe-area clipping under the notch / home indicator, text truncation at large scale, contrast, touch-target size, the error banner position, platform-native controls (no iOS look on Android, no web look anywhere). Cite the `design/ux-review` heuristic and the corpus row (`design/ui-ux-pro-max --stack react-native`) behind each visual finding. Save images only under a scratch folder inside the worktree and delete them before committing.

## Output format

```
| Severity | Location | Issue | Suggested fix |
|----------|----------|-------|---------------|
| blocker  | src/features/profile/ProfileCard.tsx:21 | `{user.name}` rendered directly inside `<View>` — crashes in release | Wrap in `<Text>` |
| major    | src/features/orders/api.ts:14 | `fetch(url)` without a timeout budget | `AbortSignal.timeout(10_000)` per `networking` |
```

Close with the lane line (`SDK 57 · Expo Router · Compiler on · CNG`), the screenshot-pass status, and the finding counts by severity. Severities follow the checklist: blocker ships a crash, a store rejection or a hard security rule break; major breaks a § Mobile code rule where it will hurt soon; minor is style; nit is preference.

## Anti-patterns to always flag

- A version upgrade or lane move inside a feature diff — reject it; it is a [`migration`](../migration/SKILL.md) run
- A comment that exists because a name is unclear (major — the fix is the rename)
- A test that asserts nothing, or an `OR` in an assertion (Test code rules)
- `try` / `catch` inside a test body

## Handoffs

- Fix → the `mobile-react-native` agent (FIX or EXTEND), or the owning skill named per section
- Repo-wide → [`standards-audit`](../standards-audit/SKILL.md); version moves → [`migration`](../migration/SKILL.md)
- Lock the fix with a test → [`component-testing`](../component-testing/SKILL.md)
- Missing ids → [`test-ids`](../test-ids/SKILL.md); E2E review → peer `qa-mobile-typescript`
- Security proof → peer `qa-security`
