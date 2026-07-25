# `fe-react-native` stack — build plan

**Date started:** 2026-07-12
**Origin:** `frontend/plan.md` Phase 5 (F10) — decision taken: **adapt the vendored Vercel React-Native import into a full `fe-react-native` stack**, mirroring the `frontend/react/` port (stack-first, domain-encapsulated, one phased orchestrator agent, one marketplace plugin).
**Cadence:** one node per session (per the library's node-per-session workflow). After each node: tick the boxes here, rewrite `HANDOFF.md`, so context can be cleared between nodes.

---

## Target shape

A self-contained `fe-react-native` plugin — the **mobile** sibling of `fe-react` — that owns a React Native + Expo app build (greenfield) **and** brownfield fix/extend, end-to-end across six phases: scaffold → architecture foundations (with a design-critique loop) → feature build → quality layers → Jest + React Native Testing Library component tests → hostile self-review (with a visual self-critique pass). It loads **only** `frontend/react-native/skills/*` plus the named `design/*` and `auth/auth0-react` skills (and, for brownfield, the bundled `ep-*` skills). QA (`qa-mobile-typescript`, `qa-manual-test-designer`, `qa-security`, `qa-cicd-typescript`) are **peers** it invokes separately, connected by the `testID` / `missing-testids.md` handshake.

### Version policy (locked from research 2026-07-12)

- **Expo SDK 56 primary** (React Native 0.85, React 19.2, Hermes v1 default) / **SDK 54–55 supported** / **SDK 53 is the floor** (first SDK with React 19 + full New-Architecture support).
- **New Architecture (Fabric + TurboModules + Bridgeless) is the assumed baseline** — always-on since SDK 55, default since SDK 52; never author an old-architecture (`Paper`/bridge) recipe as primary.
- **Expo Router** is the primary navigation lane (file-based; since SDK 56 it maintains its own fork of React Navigation and no longer sits on top of it — do not install `react-navigation` alongside `expo-router`). Bare **React Navigation** native-stack/native-tabs is the fallback lane for non-Expo-Router / bare projects.
- **Expo-managed (Expo Go / dev client + EAS)** is primary; **bare RN** is the tagged fallback.
- Every skill is version-aware: the agent's first act on an existing project is to detect the Expo SDK + RN + React majors from `package.json`/`app.json` and key every recipe to them. Never up-level a down-level project; never flag a down-level project for lacking an up-level API.

### Web→native deltas the port must encode (the reason this isn't just "fe-react on a phone")

| Web (`fe-react`) concept | React-Native replacement |
|---|---|
| RSC / `'use client'` boundary | **No RSC** — all components run on-device; the boundary story is gone. `reference` states this up front. |
| DOM elements (`div`/`span`/`a`) | Native primitives (`View`/`Text`/`Pressable`); **text must be inside `<Text>`** |
| CSS / MUI `sx` | `StyleSheet.create` (default) / Nativewind / Tamagui; no cascade, no media queries |
| `<Link href>` routing, URL-as-state | Expo Router file routes + typed params; **navigation params, not URL** |
| SEO / metadata | **N/A** — dropped; a native app is not crawled |
| PWA / service worker | **Offline-first** (MMKV/AsyncStorage + sync) — replaces `pwa-offline` |
| `data-testid` | **`testID`** prop (+ `accessibilityLabel`); same authoring discipline, different attribute |
| Vitest + RTL | **Jest + React Native Testing Library**; E2E is Maestro/Detox → `qa-mobile-typescript` peer |
| `useMediaQuery` / container queries | `useWindowDimensions` + `SafeAreaView` + `Platform` + orientation |
| axe / Lighthouse a11y | `accessibilityRole/Label/State`, VoiceOver/TalkBack, `expo-doctor`/a11y inspector |

---

## Skill set (20 skills — parity map to `fe-react`'s 21)

Dropped from web: `seo-discoverability` (no crawling), `pwa-offline` (→ `offline-first`). Added for native: `navigation` (first-class RN concern). Net: 20.

Each skill is marked with its **seed source** in the vendored `vendor/react-native-guidelines/rules/` pack where one exists (S = seeded, — = authored fresh).

### Foundations (6)
- `reference` — RN/Expo mental model: native primitives, **no-RSC** note, the New Architecture (Fabric/TurboModules/Bridgeless), Hermes, Expo-managed vs bare, hooks lifecycle, React 19 in RN, atomic-design taxonomy, the React-web↔RN map, and the index into the vendored rules pack. **S** (rendering-*, react-state-*, react-compiler-*, state-*)
- `project-scaffold` — `create-expo-app` from zero, Expo Router file routes, dev-client vs Expo Go, EAS build/submit, `app.json`/config plugins, strict TS/ESLint/Prettier/pnpm, typed env (`expo-constants`/`.env`). **S** (monorepo-*, fonts-config-plugin, imports-design-system-folder)
- `state-management` — server vs client state, Zustand, TanStack Query, Context split; navigation params as state (no URL). **S** (react-state-*, state-ground-truth)
- `component-library` — one-of-N: RN primitives + StyleSheet (default) · Nativewind · Tamagui · React Native Paper · gluestack; `references/<lib>.md`. —
- `styling` — `StyleSheet.create` authority / Nativewind, design tokens, type scale, dark mode via `useColorScheme`, no-cascade discipline. **S** (ui-styling)
- `responsive-design` — `useWindowDimensions`, `SafeAreaView`, orientation, `Platform.select`, tablet/foldable, `PixelRatio`. **S** (ui-safe-area-scroll, ui-scrollview-content-inset, ui-measure-views)

### Feature build (8)
- `generator` — screens/components/native-module recipes, compound components. **S** (design-system-compound-components)
- `forms` — React Hook Form + Zod, `KeyboardAvoidingView`, native inputs, `expo-secure-store` for sensitive fields. —
- `data-access` — `fetch`/TanStack Query, request cancellation, `AppState`-aware refetch, ProblemDetails→UI. —
- `realtime` — WebSocket/SSE in RN, `AppState` foreground/background handling, reconnection. —
- `navigation` — Expo Router (primary) / React Navigation native-stack & native-tabs (fallback): typed routes, params, deep links, guards. **S** (navigation-native-navigators)
- `testability` — `testID` authoring + audit, per-library matrix, `missing-testids.md` handshake to `qa-mobile-typescript`. —
- `ui-conventions` — native UI patterns: `Pressable` over `TouchableOpacity`, `expo-image`, native menus (Zeego), native modals, image galleries, list/empty/loading conventions. **S** (ui-pressable, ui-expo-image, ui-image-gallery, ui-menus, ui-native-modals)
- `motion` — Reanimated + Gesture Handler: GPU-only props (transform/opacity), `useDerivedValue`, `Gesture.Tap` over Pressable, `prefers-reduced-motion` (`AccessibilityInfo.isReduceMotionEnabled`), layout animations, shared element transitions. **S** (animation-*, react-compiler-reanimated-shared-values)
- `localization` — `expo-localization` + i18n lib, RTL via `I18nManager`, `Intl` hoisting, per-locale formatting. **S** (js-hoist-intl)

*(count note: feature-build lists 9 bullets; `localization` is grouped here for build-order but counts toward the 20; see node table.)*

### Quality layers (4)
- `accessibility` — `accessibilityRole/Label/State/Hint`, VoiceOver/TalkBack, focus order, dynamic type, min touch target; hands a11y scan to QA. —
- `performance` — the CRITICAL seed: list virtualization (FlashList/LegendList over FlatList), item memoization, stable callbacks/refs, no inline objects, image perf, scroll-position-without-state, the RN cost centers. **S** (list-performance-* — 8 rules, scroll-position-no-state)
- `error-resilience` — error boundaries, network-failure UX, three-state regions, idempotent retry, crash reporting handoff (Sentry). —
- `offline-first` — MMKV/AsyncStorage, TanStack Query persistence, optimistic mutation queue, connectivity (`expo-network`/NetInfo), conflict strategy. —

### Test + review (2)
- `component-testing` — Jest + React Native Testing Library, logic-bearing components + custom hooks, `jest-expo` preset; E2E (Maestro/Detox) is the `qa-mobile-typescript` peer. —
- `reviewer` — hostile senior review, standard severity table; RN checklist (text-in-Text, list-perf, GPU-only animation, testID coverage, no old-arch APIs, navigation-as-real-route). **S** (all — it audits against every rule)

---

## Node breakdown (one node ≈ one session)

- [x] **Node 0 — Groundwork** *(this session)*: decision taken; restructure raw Vercel import → `vendor/react-native-guidelines/` (fenced seed, org fixed, routing clause added); write this PLAN.md.
- [x] **Node 1 — Foundations A** *(done 2026-07-12)*: `reference` + `project-scaffold`.
- [ ] **Node 2 — Foundations B**: `state-management` + `component-library` + `styling` + `responsive-design`.
- [ ] **Node 3 — Feature build A**: `generator` + `forms` + `data-access` + `realtime`.
- [ ] **Node 4 — Feature build B**: `navigation` + `testability` + `ui-conventions` + `motion` + `localization`.
- [ ] **Node 5 — Quality layers**: `accessibility` + `performance` + `error-resilience` + `offline-first`.
- [ ] **Node 6 — Test + review + agent**: `component-testing` + `reviewer` + the phased `fe-react-native` agent (mirror `fe-react.md`, six phases, brownfield section per `.skill-template/agent.md`).
- [ ] **Node 7 — Wiring + docs**: marketplace `fe-react-native` plugin entry (skills + agent + vendor seed + design/* + auth/auth0-react); update root `CLAUDE.md` (scope fence, new "Frontend-React-Native dev catalog" section, new-project-setup line, remove from under-construction list); run the verification checklist below.

Each authored skill: research-first (current Expo/RN docs), mirror the matching `fe-react` skill's shape/voice, version-aware table, When-to-use / When-NOT-to-use routing, description ≤ 1000 chars (per `frontend/plan.md` Phase 2 discipline), no SKILL.md > 500 lines, seed-fed skills point into `vendor/react-native-guidelines/rules/<rule>.md`.

---

## Verification (after Node 7)
- [ ] All 20 skill folders present with a valid SKILL.md (name matches folder, frontmatter description ≤ 1000 chars, Triggers + Do-NOT routing).
- [ ] Agent↔skills contract airtight: every skill loaded by the agent, no orphans, six-phase structure, brownfield section present.
- [ ] Seed-fed skills each reference the correct `vendor/react-native-guidelines/rules/*.md` files; vendor seed carries the "Do NOT use directly" fence.
- [ ] Marketplace `fe-react-native` `skills`/`agents`/vendor paths all resolve on disk.
- [ ] Version policy applied uniformly (Expo SDK 56 primary / 54–55 / 53 floor; New Arch baseline; no old-arch primary recipe).
- [ ] `CLAUDE.md` updated (scope, catalog, setup line); react-native removed from the under-construction list.
- [ ] `frontend/plan.md` Phase 5 boxes ticked; this PLAN.md + HANDOFF.md reflect final state.
