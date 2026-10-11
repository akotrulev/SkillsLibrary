---
name: standards-audit
description: Use to audit a whole React Native / Expo app against the mobile-react-native plugin's conventions — version lane, structure, UI, navigation, data, native code, accessibility, resilience, test ids, security and store fragments — as a saved, re-runnable report in `docs/audits/`. Read-only. Triggers "audit our RN app against the plugin conventions". Do NOT use to review one diff (`mobile-react-native:conventions-review`) or check code against a spec (`code-auditor`).
---

# mobile-react-native Conformance Audit

Audit an existing **React Native / Expo app** against the conventions this plugin defines — CLAUDE.md § Mobile code rules plus the hard rules each `mobile/react-native/skills/*` skill owns and the five `mobile/_shared/*` fragments — and produce **one saved report**: every finding evidenced at `file:line`, severity-tabled, mapped to the skill that owns the fix.

**Read-only analysis on product code.** The audit points; the `mobile-react-native` agent fixes.

State the mode — Mode A (baseline) or Mode B (re-audit) — and the target path in the first line of output.

## Read before sweeping

1. **[`engineering-practices/standards-audit-engine`](../../../../engineering-practices/standards-audit-engine/SKILL.md)** — Mode A/B rounds, the artifact contract, evidence rules, severity semantics, grouping and coverage policy, the five steps, the hostile self-review. **Read it first**; this file adds only what is specific to React Native.
2. [`references/conformance-checklist.md`](references/conformance-checklist.md) — sections A–X and every check; the section index at its end. **Read end-to-end** before Step 2.
3. `engineering-practices/standards-audit-engine/references/report-template.md` — the Round-1 / Round-N skeletons. Read before Step 3.
4. The fragments for sections K, L, T, U, X: `mobile/_shared/{security,store-compliance,release,observability,in-app-purchases}/references/audit-checks.md` — rows whose `Stacks` column names `react-native`.

Load the **owning skill** (named per section in the checklist) whenever a check is ambiguous, version-keyed, or you are about to write its fix direction. When checklist and skill disagree, **the skill wins** — and report the disagreement.

Report path: `docs/audits/<NNN>-mobile-react-native-conformance-r<N>.md`.

## The fence — what this is not

| Job | Owner |
|---|---|
| Review one diff, inline table, no artifact, screenshot pass | [`code-review`](../code-review/SKILL.md) — this skill reuses its rows at repo scale |
| Code vs a written spec / stories | `dev:audit-spec` (or the `code-auditor` agent) |
| How one feature works, where it is defective | `dev:audit-feature` |
| Proof of pinning, on-disk data, resilience controls on a built binary | **peer** `qa-security` (`mobile-app-scan`, `mobile-runtime-testing`) — a row a static read cannot prove is reported **unverified**, never passed |
| E2E suites, device journeys | **peer** `qa-mobile-typescript` |
| Design heuristics on screens | `design/ux-review` on screenshots |
| Applying any fix | the `mobile-react-native` agent |

## Step 0 — the Expo / React Native version lane *(never skip)*

```bash
cat package.json | rg '"(expo|react-native|react|expo-router|@react-navigation/[a-z-]+|typescript|react-native-reanimated|react-native-gesture-handler|@shopify/flash-list|react-native-mmkv|@testing-library/react-native|nativewind|react-native-purchases|expo-iap|react-native-iap)"'
rg -n "newArchEnabled|jsEngine|reactCompiler|typedRoutes|\"plugins\"|runtimeVersion|updates" app.json app.config.* 2>/dev/null
ls app.json app.config.* eas.json metro.config.js babel.config.js pnpm-lock.yaml yarn.lock package-lock.json bun.lock 2>/dev/null
git ls-files ios android | head -5
ls ios android 2>/dev/null | head; git log --oneline -5
```

Record: **Expo SDK** (57 primary · 58 next · 55–56 supported · 54 floor · below 54 → finding A1 and a [`migration`](../migration/SKILL.md) hand-off, never audited as if current) · **RN and React** · **Expo Router or bare React Navigation** · **workflow** — Expo-managed CNG (`ios/` and `android/` ignored) / Expo with committed native folders / bare `[bare]` · **New Architecture status** · **Hermes** · **React Compiler on or off** · **Gesture Handler / FlashList / MMKV / RNTL majors** · **package manager** · **EAS profiles and OTA policy**.

**The version rule binds every finding.** Never flag a down-level project for lacking an up-level API (`createMMKV` on MMKV 3, `native-tabs` on SDK 57, RNTL 14 async APIs on RNTL 13, `estimatedItemSize` absence on FlashList 1); never apply an up-level recipe to it. A **`[SDK58]`** row applies only on 58; a **`[bare]`** row only to a bare project. A project mid-migration is finding A, not a licence to audit it against the highest lane present.

Then read 2–3 representative files (a route, a feature screen, the API client or query setup) to calibrate conventions.

## Step 1 — applicability

| Section | Applies when | Probe |
|---|---|---|
| F (Expo Router rows) | `expo-router` is installed | `rg -n '"expo-router"' package.json` |
| F (React Navigation rows `[bare]`) | `@react-navigation/*` without `expo-router` | `rg -n '@react-navigation' package.json` |
| I (storage) | Any persistence library or `expo-secure-store` is referenced | `rg -ln "react-native-mmkv\|expo-sqlite\|op-sqlite\|expo-secure-store\|AsyncStorage" package.json $SRC` |
| J (native code) | `modules/`, a config plugin, or committed `ios/` / `android/` exists | `ls modules plugins 2>/dev/null`; `git ls-files ios android` |
| P (localization) | More than one locale is shipped or `expo-localization` / i18n referenced | `rg -ln "expo-localization\|i18next\|lingui" package.json` |
| Q (motion) | Reanimated, Gesture Handler or `Animated` is used | `rg -ln "react-native-reanimated\|react-native-gesture-handler\|Animated" $SRC` |
| S (tests) | A Jest config exists — **no dev-side tests at all is a section S finding** (cite S1 if another runner is present), not N/A | `rg -ln "jest" package.json` |
| T (release) | `eas.json` or store config exists — absent is a finding | `ls eas.json fastlane 2>/dev/null` |
| U (observability) | Always; **absent crash reporting is a finding**, not N/A | `rg -ln "sentry\|crashlytics\|expo-observe" package.json` |
| X (in-app purchases) | The app sells anything: `react-native-purchases`, `expo-iap`, `react-native-iap` | `rg -n "react-native-purchases\|expo-iap\|react-native-iap" package.json` |

A–E, G, H, K, L, M, N, O, R, V apply to every app. A section that is N/A must name the probe that decided it. `$SRC` is set by the checklist's recipe header.

## Step 2 notes — what the engine does not say

- **Generated folders.** Under CNG, `ios/` and `android/` are ignored by `rg`; do not add `--no-ignore` unless the project commits them, and state it in the coverage line. A committed `ios/` / `android/` is read as native code (section J) and as `[bare]`.
- **Static-first.** Run no build, type-check, lint, Jest or device unless the user opts in for this audit. `npx expo-doctor` is not static — A4 reports "run `expo-doctor` to settle" as **Unverifiable** until it is run.
- **Fragments.** Cite fragment findings with the fragment's own id (`K3`, `L2`); unreachable-by-static rows say **requires dynamic test → `qa-security`**.
- **Deviations.** A deliberate project convention (NativeWind as the styling authority, a CSS-in-JS kit, Redux for client state) is a noted deviation, not a finding; an inconsistent one is a finding.

## Handoffs

- **Apply fixes** → the `mobile-react-native` agent, FIX or EXTEND; a version or lane finding → [`migration`](../migration/SKILL.md) as its own run. The priority table is the artifact.
- **One diff instead** → [`code-review`](../code-review/SKILL.md)
- **Security-flavoured and unverified rows (K, part of L, T)** → peer `qa-security`
- **E2E gaps and test-id coverage proof** → peer `qa-mobile-typescript`
- **Design review of screens** → `design/ux-review`
- **A spec or feature trace** → `dev:audit-spec` / `dev:audit-feature` / `code-auditor`
