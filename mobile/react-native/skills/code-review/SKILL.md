---
name: conventions-review
description: Use when reviewing a React Native/Expo diff against plugin conventions, plus a simulator screenshot pass. Triggers "review this PR". Not for a whole-repo audit (standards-audit).
---

# React Native / Expo — Reviewer

A **hostile review of one diff** against the mobile-react-native rule files, then a **screenshot pass** on the running app. Findings go in the standard severity table; the review **does not rewrite**: it points, and the `mobile-react-native` agent (or the author) fixes. A whole-repo sweep with a saved report is [`standards-audit`](../standards-audit/SKILL.md).

## The checklist is the rule files

Every check, and the severity it reports, lives in one place: the mobile-react-native rule files `react-native.md` (core), `react-native-ui.md`, `react-native-a11y.md`, `react-native-forms.md`, `react-native-data.md`, `react-native-routes.md`, `react-native-tests.md` and `expo-config.md`.

1. **The project's copies first**: `.claude/rules/mobile-react-native/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `mobile/react-native/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/mobile-react-native:rules` installs them.

Read `react-native.md`, plus each other file whose `paths:` match a file under review, in full before the first finding. The project's globs may be narrower than its app; judge by what the file is: a component or screen (`.tsx`) takes ui, a11y and forms, a client, store or storage module (`.ts`) takes data, a route file takes routes, a test takes tests, `app.json` / `app.config.*` / `eas.json` / a config plugin / a native folder takes `expo-config.md`. A rule loaded on its own by the session is not enough: a review needs every file that applies. Never review from memory of the rules, and never add a check the files do not contain; propose it as a rule change instead.

## Version lane

Detect before flagging: Expo SDK and RN (`package.json`), Expo Router or bare React Navigation, React Compiler on or off (`reactCompiler` in `app.json`), Gesture Handler / FlashList / MMKV / RNTL majors, `ios/` and `android/` tracked (`[bare]`) or ignored (CNG).

| Lane | Review consequence |
|---|---|
| **57 primary** | The rules as written |
| `[SDK58]` | 58-only APIs are correct on 58 and a finding on 57; the reverse for 57 workarounds after an upgrade |
| 55–56 / 54 floor | Apply the rules keyed to that SDK; never flag a down-level project for lacking a 57 API |
| Below 54 | One finding plus a [`migration`](../migration/SKILL.md) run — do not review against rules it cannot meet |

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

1. Read the rule files that apply (above), then each changed file end to end.
2. Walk the blockers first: text outside `<Text>`, secrets and token storage, hand edits to generated native folders, cleartext traffic, concatenated SQL. Then the rest in rule-file order.
3. Per finding: file and line, the rule broken, a one-sentence fix. The severity is the tag on the rule, never a new judgment. One row per defect family with a count, not per site.
4. Run the screenshot pass (below) if a device is available; otherwise say it was not run.
5. Do not rewrite. Hand off to the agent or the owning skill.

## The screenshot pass (Step 5)

Only when a simulator or emulator is available and the app builds; otherwise report "screenshot pass not run" and why.

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

Close with the lane line (`SDK 57 · Expo Router · Compiler on · CNG`), the screenshot-pass status, the finding counts by severity, and one line: `Rules: project .claude/rules/mobile-react-native/ | plugin copy (not installed)`.

## Handoffs

- Fix → the `mobile-react-native` agent (FIX or EXTEND), or the owning feature skill
- Repo-wide → [`standards-audit`](../standards-audit/SKILL.md); version moves → [`migration`](../migration/SKILL.md)
- Lock the fix with a test → [`component-testing`](../component-testing/SKILL.md)
- Missing ids → [`test-ids`](../test-ids/SKILL.md); E2E review → peer `qa-mobile-typescript`
- Security proof → peer `qa-security`
- A rule is missing or wrong → edit the project's `.claude/rules/mobile-react-native/`; for every project, the plugin's `mobile/react-native/skills/rules/`
