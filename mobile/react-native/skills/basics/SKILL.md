---
name: mobile-react-native-basics
description: Use when the user asks to explain a React Native / Expo concept — native primitives (`View`/`Text`/`Pressable`) vs the DOM, why there is **no RSC / `'use client'` boundary** on device, the New Architecture (Fabric renderer, TurboModules, Bridgeless, JSI), the Hermes engine, Expo-managed vs bare workflow, the RN thread model (JS thread vs UI/native thread), hooks and React 19 in RN, `StyleSheet` vs the CSS cascade, and the atomic-design taxonomy. Triggers "what's the RN equivalent of X in React web", "why is there no server component here", "what is Fabric / TurboModules / the New Architecture", "JS thread vs UI thread", "Expo Go vs dev client vs bare", "atom or organism / how deep to prop-drill". Do NOT use for scaffolding a project (use `mobile/react-native/skills/project-setup`), generating a screen/component (use `mobile/react-native/skills/generator`), reviewing (use `mobile/react-native/skills/reviewer`), or React **web** concepts (use `frontend/react/skills/reference`).
---

# React Native / Expo — Reference

Conceptual reference for React Native + Expo — the on-device rendering model, the New Architecture, the thread model, and the "wait, this isn't the DOM" surprises that trip up developers arriving from React web. Everything here runs **on the device**; there is no server-rendering split.

## Version applicability

Detect the **Expo SDK**, **React Native**, and **React** majors first (from `package.json` / `app.json`) and key every recipe to them.

| Concern | Primary (SDK 56 · RN 0.85 · React 19.2) | Supported floor (SDK 53–55) |
|---|---|---|
| Architecture | New Architecture only (Fabric + TurboModules + Bridgeless) — always-on since SDK 55 | New Arch default since SDK 52; SDK 53 first with full React 19 support |
| JS engine | **Hermes v1** (default) | Hermes (pre-v1) |
| React features | React 19: `use()`, Actions, `useActionState`, `useOptimistic`, `ref` as a prop, React Compiler (opt-in via `babel-plugin-react-compiler`) | React 19 from SDK 53; below that (SDK ≤52) is out of scope for this stack |
| Navigation | Expo Router (its own React-Navigation fork; do not also install `react-navigation`) | Expo Router on top of React Navigation (SDK ≤55) |

**Never author an old-architecture (`Paper`/bridge) recipe as the primary path** — the New Architecture is the assumed baseline.

## When to use

- "What's the React Native equivalent of `<div>` / `<a>` / CSS / `useMediaQuery`?"
- "Why isn't there a Server Component / `'use client'` here?"
- "What is Fabric / TurboModules / Bridgeless / JSI — do I need to care?"
- "What runs on the JS thread vs the UI thread, and why does that matter for animation?"
- "Expo Go vs dev client vs bare — which am I on?"
- "Atom or organism? How deep should I prop-drill?"

## When NOT to use

- Standing up a project / EAS / config → [`project-setup`](../project-setup/SKILL.md)
- Scaffolding a screen/component → [`generator`](../generator/SKILL.md)
- Picking a state library in depth → [`architecture`](../architecture/SKILL.md)
- Reviewing → [`reviewer`](../reviewer/SKILL.md)
- React **web** (RSC, DOM, Next.js) → `frontend/react/skills/reference`
- Auth0 in the app → `auth/auth0-react` (+ `auth/_shared/auth0-concepts`)

---

## The single biggest mental shift: there is no server render

React web on the App Router is **a server app with selective client interactivity** (RSC default, `'use client'` islands). **React Native has none of that.** Every component runs **on the device**, in the JS runtime, always. There is:

- **No RSC, no `'use client'`, no `'use server'`, no Server Actions, no hydration.** A component is just a component. Do not look for the boundary — it isn't there.
- **No SEO / metadata / crawling** — a native binary is not a web page. (That whole `fe-react` skill is dropped here.)
- **No URL as state.** Navigation is Expo Router file routes + typed params; there is no address bar the user edits. State that would be "in the URL" on web lives in **navigation params** or a store.

What *does* carry over unchanged: hooks and their rules, the one-way data flow, keys, effect-dependency discipline, React 19 APIs, Context vs store, Suspense (`use()` + a Suspense boundary works in RN), and the composition patterns.

## Native primitives — the DOM replacements

There are no HTML elements. You compose a fixed set of **native primitives** from `react-native` (and `expo-*`):

| React web | React Native | Notes |
|---|---|---|
| `<div>` | `<View>` | flex container; **no** `display:block`, flex is the default and only layout |
| text (bare, in `<p>`/`<span>`) | `<Text>` | **all text must be inside `<Text>`** — a bare string in a `<View>` crashes. → `vendor/react-native-guidelines/rules/rendering-text-in-text-component.md` |
| `<a href>` | Expo Router `<Link href>` | file-based route; not a URL bar |
| `<button>` | `<Pressable>` | prefer over `TouchableOpacity`. → `.../rules/ui-pressable.md` |
| `<img>` | `<Image>` from **`expo-image`** | not RN's core `Image`. → `.../rules/ui-expo-image.md` |
| `<input>` | `<TextInput>` | controlled the same way |
| scroll container | `<ScrollView>` (small) / `<FlatList>`/**FlashList** (lists) | never map a large array inside a `ScrollView`. → performance skill |
| CSS file / `sx` | `StyleSheet.create({...})` objects | no cascade, no inheritance (except some `Text` props), no media queries |

**No CSS cascade.** Styles are plain objects; there is no inheritance down the tree (a `color` on a parent `View` does **not** reach child `Text`), no `@media`, no pseudo-classes. Responsiveness comes from `useWindowDimensions` + `Platform`, not breakpoints. → [`styling`](../styling/SKILL.md), [`responsive-design`](../responsive-design/SKILL.md).

## The New Architecture — what it is, what you must know

Since SDK 52 (default) / SDK 55 (mandatory), Expo runs the **New Architecture**. You rarely touch it directly, but it changes the mental model:

- **JSI (JavaScript Interface)** — a synchronous C++ bridge between JS and native, replacing the old asynchronous JSON "bridge." Native calls can now be synchronous and hold references to native objects.
- **Fabric** — the new rendering system. The React tree is reconciled into a native view tree with less serialization overhead; layout can be measured synchronously.
- **TurboModules** — native modules are lazy-loaded and typed via **Codegen** from TS specs, instead of all eagerly loaded at startup.
- **Bridgeless** — the old bridge is gone entirely; everything goes through JSI.

**Why you care as an app developer:** the practical payoff is that **Reanimated worklets and Gesture Handler run animations on the UI thread** without round-tripping the (now-absent) bridge — which is why the [`motion`](../motion/SKILL.md) skill insists on GPU-only properties and worklets. Also: `expo-*` packages all support the New Arch; a random old third-party native module may not, and that's the main compatibility risk when adding deps.

## The thread model — why animation rules exist

RN runs your JS on a dedicated **JS thread**, separate from the **UI (native/main) thread** that draws frames. Consequences that drive other skills:

- **A busy JS thread drops frames.** Heavy work (parsing, big `.map`, non-memoized list items) blocks JS and the UI stutters. → [`performance`](../performance/SKILL.md).
- **Animating via React state re-renders on the JS thread** → jank. **Reanimated worklets run on the UI thread** and animate `transform`/`opacity` on the GPU without JS involvement. → [`motion`](../motion/SKILL.md), `.../rules/animation-gpu-properties.md`, `.../rules/animation-derived-value.md`.
- **Lists virtualize** so off-screen items aren't kept in the tree. → `.../rules/list-performance-virtualize.md`.

## Hermes

**Hermes** is the default JS engine (v1 as of SDK 56) — an engine built for RN: fast startup (bytecode precompiled at build time), lower memory. Practical notes: `console.log` is slower than you'd expect (strip in release), and some very new JS syntax may need the Babel/Metro transform rather than running natively. You don't configure it; just know release builds run bytecode, not your source.

## Expo-managed vs bare — which workflow am I on?

| | Expo Go | Dev client (managed + custom native) | Bare RN |
|---|---|---|---|
| Custom native modules | No (only Expo SDK) | **Yes** (via config plugins / prebuild) | Yes |
| `ios/` `android/` folders in repo | No | Usually no (generated by `prebuild`) | Yes (checked in) |
| Build | Expo Go app | EAS Build → dev client | EAS Build / Xcode / Gradle |
| This stack's default | quick prototypes | **primary for real apps** | fallback lane |

**Config plugins** (`app.json` `plugins`) are how the managed workflow configures native code without ejecting — the managed replacement for editing `Info.plist`/`AndroidManifest.xml` by hand. → [`project-setup`](../project-setup/SKILL.md), `.../rules/fonts-config-plugin.md`.

## React 19 in React Native

React 19 ships from SDK 53. The additions behave the same as on web, minus anything server-only:

- `use()` + Suspense for reading promises/context in render — works on device.
- Actions / `useActionState` / `useOptimistic` — the hooks work; there are **no Server Actions**, so `action` is a plain async function, not a server reference. Forms use React Hook Form + Zod. → [`forms`](../forms/SKILL.md).
- **`ref` is a plain prop** — no `forwardRef` on React 19. On an SDK ≤52 (React 18) project, `forwardRef` is still correct — do not flag it.
- **React Compiler** auto-memoizes; enable via `babel-plugin-react-compiler`. It has RN-specific gotchas with Reanimated shared values and destructuring. → `.../rules/react-compiler-reanimated-shared-values.md`, `.../rules/react-compiler-destructure-functions.md`.

## State: ground truth and derived values

Same discipline as web: keep **one source of truth**, compute derived values in render (don't mirror them into state), minimize what a component subscribes to. → `.../rules/state-ground-truth.md`, `.../rules/react-state-minimize.md`, `.../rules/react-state-fallback.md`, and [`architecture`](../architecture/SKILL.md) for the library choice.

## Atomic-design taxonomy (shared with `fe-react`)

Same naming and ownership rules as the web stack — components are organized atom → molecule → organism → template → screen:

- **Atom** — one primitive with styling/props, no domain knowledge (`AppText`, `PrimaryButton`, `Avatar`). Owns no server state.
- **Molecule** — a few atoms bound to one small job (`SearchField`, `ListRow`, `FormField`).
- **Organism** — a self-contained section with its own data/state (`ProductList`, `CheckoutForm`, `CommentThread`).
- **Template / Screen** — a route target under `app/` (Expo Router). Screens compose organisms; screens own navigation and the data fetch.
- **Prop-drilling limit:** 2–3 levels. Past that, lift to Context (client state) or a store — not deeper drilling. Server state belongs to TanStack Query, never a store. → [`architecture`](../architecture/SKILL.md).

## The React-web ↔ React-Native cheat sheet

| Web idiom | React Native | Skill |
|---|---|---|
| `'use client'` boundary | none — all on device | this file |
| `<div>` / `<span>` / `<p>` | `<View>` / `<Text>` | this file |
| `<a href>` / router | Expo Router `<Link href>` / typed params | [`navigation`](../navigation/SKILL.md) |
| CSS / MUI `sx` | `StyleSheet.create` / Nativewind | [`styling`](../styling/SKILL.md) |
| `useMediaQuery` / breakpoints | `useWindowDimensions` / `Platform` / `SafeAreaView` | [`responsive-design`](../responsive-design/SKILL.md) |
| `data-testid` | **`testID`** | [`testability`](../testability/SKILL.md) |
| SEO / metadata | dropped (native app) | — |
| PWA / service worker | offline-first (MMKV + sync) | [`offline-first`](../offline-first/SKILL.md) |
| axe / Lighthouse | `accessibilityRole/Label`, VoiceOver/TalkBack | [`accessibility`](../accessibility/SKILL.md) |
| Vitest + RTL | Jest + React Native Testing Library | [`component-testing`](../component-testing/SKILL.md) |

## The vendored rules pack

Deep, rule-by-rule guidance (impact-ranked, incorrect-vs-correct examples) lives in the vendored Vercel seed at `mobile/react-native/vendor/react-native-guidelines/` — 35+ rules across list-performance, animation, navigation, UI, state, rendering, monorepo, config. Load it **through** the house skill that routes into it ([`performance`](../performance/SKILL.md), [`motion`](../motion/SKILL.md), [`ui-conventions`](../ui-conventions/SKILL.md), [`navigation`](../navigation/SKILL.md), this `reference`), never as a standalone skill.
