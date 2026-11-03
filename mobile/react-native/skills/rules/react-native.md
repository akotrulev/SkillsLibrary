---
paths:
  - "app/**/*.{ts,tsx}"
  - "src/app/**/*.{ts,tsx}"
  - "**/*.{native,ios,android}.{ts,tsx}"
---

<!-- mobile-react-native rules v1 (2026-11-03): core. Installed by /mobile-react-native:rules; widen the paths above to this project's app folder, re-run to compare with the plugin's copy. -->

# React Native / Expo code standards

Apply these to every TypeScript file of the app you write, edit or review. The tag after a rule is the severity a review reports: **blocker** ships a crash, a store rejection or a security break, **major** is a design or correctness problem, **minor** is style, **nit** is preference. UI, accessibility, forms, data, route, test and Expo-config rules are separate files that load with those files.

**The codebase wins.** Where this project consistently does something another way, follow the project and do not flag it. Detect the Expo SDK, RN and React majors, Expo Router or bare React Navigation, CNG or committed `ios/` / `android/`, React Compiler on or off, and the Reanimated, Gesture Handler, FlashList, MMKV and RNTL majors (`package.json`, `app.json`) before writing. SDK 57 is primary, 55–56 supported, 54 the floor: never use an API the project's version lacks (`createMMKV` on MMKV 3, `native-tabs` on SDK 57, RNTL 14 async APIs on 13) and never flag a down-level project for lacking one. Below SDK 54 is one finding and a `migration` run.

## Simplicity

- Write the simplest thing that meets the requirement, then stop: no interface with one implementer, no wrapper that only forwards, no store for state one screen owns. An abstraction is earned on the second real need. *major, fix by inlining*
- Prefer the platform: an Expo SDK module or plain JS before a native module or a new dependency; no second HTTP client, i18n library or component kit beside the project's own. *major*
- Cut structure, never correctness: three-state regions, accessibility, cleanup, denied paths and tests stay.
- Never up-level the SDK, a toolchain or a deployment target as a side effect, and never put a version move in a feature change; it is a `migration` run. *major*

## Platform

- All text inside `<Text>`; a string or `{value}` as a direct child of a `View` crashes in release. *blocker*
- Conditional rendering with a boolean, never `{count && <X/>}` with a number. *blocker*
- No DOM assumptions: no `window`, `document`, URL-as-state, `'use client'`, `useActionState` or `<form action>`. *major*
- New Architecture only; never a Paper-architecture recipe. *major*
- No `@react-navigation/*` import in an Expo Router app (SDK 56+). *major*
- Native packages installed with `npx expo install`, never `add`. *major*
- On React 19, `ref` is a prop: no `forwardRef`. *minor*

## State

- Server state lives in TanStack Query, never copied into Zustand, Context or another store. *major*
- State is minimal ground truth; derive the rest in render. No `useEffect` syncing two states, no `useReducer` for one boolean. *major*
- One Context or store per concern, read through selectors and a throwing consumer hook; no giant `AppStore`, no prop drilling past 2–3 levels. *minor*
- Compiler on: no `useMemo` / `useCallback` / `memo` for render cost, only where identity is a contract; never turn the Compiler on or off as a side effect. *minor*

## Data regions and failures

- Every data region has loading, loaded, failed and empty, plus stale and offline. A failure is scoped to the response-dependent subtree: header, search and filters survive; no early `return <Error/>` above them; a failed refetch keeps the data and shows the stale marker. *major*
- Every surfaced failure also raises the one persistent banner: safe-area top, user-dismissed with a 44 pt close, deduped, at most 3 visible. Never a console-only catch, a vanishing `Alert` or a swallowed rejection. *major*
- Never render `error.message`, a stack or a response body; show a reference id and a retry. *major*
- Offline is not a server error and never retries; `AbortError` renders nothing; `TimeoutError` has its own body. *major*
- Empty is not failed: no generic "No data"; a 404 record is "gone" and is not retried. *minor*

## Network, secrets and lifecycle

- Every request has a timeout budget (`AbortSignal.timeout`) composed with the caller's signal, never replacing it; no spinner that can run forever. *major*
- Responses are parsed with Zod; a parse failure is *failed*, never empty. *major*
- No secret in the bundle: `EXPO_PUBLIC_*`, `app.json` `extra` and source are public. *blocker*
- Tokens only in `expo-secure-store`; no token, password or PII in AsyncStorage, MMKV, a persisted store, plaintext SQLite, a file, a route param or a log line. *blocker*
- https only; no hardcoded `localhost` or LAN URL in a release build. *blocker*
- Deep links and push payloads are untrusted input: schema-checked and allow-listed before they route; a link parameter never reaches `Linking.openURL`, a WebView `source`, a file path or a query. *major*
- No disk, network or heavy compute blocking the JS or UI thread. *major*
- Work a screen starts stops when it goes: effects clean up, fetches abort, sockets close on background and unmount. *major*
- Returning to the foreground revalidates: `focusManager` on `AppState`, `onlineManager` on NetInfo, mounted once. *major*
- A permission is asked in context, on the user's tap, after a pre-prompt; never on mount or in a root layout. The denied path is a working screen with an alternative and "Open Settings"; status is re-read on foreground; ask for the least. *major*

## Comments

- No comments inside function bodies: no step markers, no restating the next line, no commented-out code, no `TODO`. Extract and name the step instead. *minor; major when the comment is wrong or covers an unclear name*
- TSDoc only where the name cannot carry the meaning: a non-obvious business rule, a constraint on callers, a deliberate deviation and its reason. Scaffolded template comments are removed. *nit*
