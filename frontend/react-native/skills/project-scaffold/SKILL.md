---
name: fe-react-native-project-scaffold
description: Use when the user asks to stand up a React Native + Expo app from zero — `create-expo-app` with Expo Router (file-based routing), the Expo-managed workflow (Expo Go vs dev client) and EAS Build/Submit, `app.json`/config-plugin setup, the feature-folder + `app/` route layout, and the quality gates every project ships with (strict TS, ESLint flat config, Prettier, pnpm, typed env via `expo-constants`). Triggers "create a new React Native / Expo app", "scaffold an Expo Router project", "set up EAS build", "dev client vs Expo Go", "add a config plugin", "set up the folder structure / strict TS / env config for RN". Do NOT use to scaffold a screen/component into an existing app (use `frontend/react-native/skills/generator`), wire navigation routes (use `frontend/react-native/skills/navigation`), pick a component/styling library (use `frontend/react-native/skills/component-library` / `styling`), or wire auth (use `auth/auth0-react`).
---

# React Native / Expo — Project Scaffold

Stands up a **React Native app on the Expo-managed workflow** from zero: `create-expo-app` with **Expo Router**, the dev-client-vs-Expo-Go decision, **EAS Build/Submit**, `app.json` + config plugins, the `app/` route + feature-folder layout, and the quality gates every project ships with (strict TS, ESLint flat config, Prettier, pnpm, typed env).

**Version rule:** detect the installed **Expo SDK / RN / React** majors (`package.json`, `app.json`) **first**. SDK 56 (RN 0.85, React 19.2, Hermes v1) is primary; SDK 54–55 supported; **SDK 53 is the floor** (React 19 + New Architecture). The **New Architecture is always-on** — never scaffold an old-architecture project. Never emit a React-19 API into an SDK-≤52 (React 18) project.

## When to use

- New Expo app (managed workflow, Expo Router)
- Deciding Expo Go vs dev client vs bare for the project
- Setting up EAS Build/Submit, `app.json`, config plugins
- Feature folders + `app/` routes, strict TS, ESLint/Prettier, typed env

## When NOT to use

- Adding a screen/component to an existing app → [`generator`](../generator/SKILL.md)
- Defining the route tree / navigators → [`navigation`](../navigation/SKILL.md)
- Component library + theming → [`component-library`](../component-library/SKILL.md), [`styling`](../styling/SKILL.md)
- Data fetching / live data → [`data-access`](../data-access/SKILL.md), [`realtime`](../realtime/SKILL.md)
- Auth0 wiring → `auth/auth0-react`
- Concepts (New Arch, threads, primitives) → [`reference`](../reference/SKILL.md)

## Inputs needed

0. **SDK + versions** — Expo SDK (56 default), RN, React majors — drives every version-sensitive recipe.
1. **Workflow** — Expo Go (prototype) vs **dev client** (real app, default) vs bare (fallback). Any custom native module → dev client or bare.
2. **Screens/routes** — the route tree and each route's data shape (content · API-consuming · live · offline) — drives folder layout, not one global choice.
3. **Backend** — is there an API to consume? (pairs with [`data-access`](../data-access/SKILL.md))
4. **Auth** — needed at scaffold time? (pairs with `auth/auth0-react`)
5. **Component library** — RN primitives + StyleSheet (default) or another (pairs with [`component-library`](../component-library/SKILL.md))
6. **Targets** — iOS / Android / web (Expo supports web via react-native-web; note if it's in scope).

## Create the app

```bash
# pnpm is the house default; create-expo-app scaffolds Expo Router + TS by default
pnpm create expo-app@latest my-app        # pick the "Navigation (TypeScript)" / default template
cd my-app
pnpm expo install expo-router react-native-safe-area-context react-native-screens
```

The default template ships **Expo Router**, TypeScript, and an `app/` directory. Confirm `package.json` "expo" is the SDK you want; `pnpm expo install <pkg>` (not `pnpm add`) picks the version compatible with the detected SDK — always use it for RN/Expo packages.

| Decision | Choice | Why |
|---|---|---|
| Router | **Expo Router** (file-based) | primary navigation lane; typed routes. Do **not** also install `react-navigation` (SDK 56 Expo Router forks it) |
| Language | **TypeScript strict** | house rule; template is TS already |
| Package manager | **pnpm** | house default; lock it (`packageManager` field) |
| Workflow | **dev client** for real apps | Expo Go can't load custom native modules |

### Workflow decision — Expo Go vs dev client vs bare

- **Expo Go** — zero-build prototyping; only the Expo SDK's native modules. Outgrow it the moment you need a custom native dep.
- **Dev client** (`expo-dev-client` + EAS Build) — **the default for a real app.** Managed workflow, but you can add native modules via config plugins / prebuild. No checked-in `ios/`/`android/`.
- **Bare** — `ios/`/`android/` checked in, full native control; the fallback lane when you must hand-edit native projects. Version-aware recipes still apply.

## `app.json` / `app.config.ts` + config plugins

Native configuration in the managed workflow happens through `app.json` (or `app.config.ts` for dynamic/typed config), **not** by hand-editing `Info.plist` / `AndroidManifest.xml`. Key fields: `name`, `slug`, `scheme` (deep links → [`navigation`](../navigation/SKILL.md)), `ios`/`android` identifiers, `plugins`, `newArchEnabled` (true/implicit on SDK 55+).

**Config plugins** run at `prebuild` to modify native projects. Add native capabilities (fonts, permissions, splash) as plugins:

```jsonc
// app.json (excerpt)
{
  "expo": {
    "scheme": "myapp",
    "plugins": [
      "expo-router",
      ["expo-font", { "fonts": ["./assets/fonts/Inter.ttf"] }],
      ["expo-splash-screen", { "image": "./assets/splash.png", "resizeMode": "contain" }]
    ]
  }
}
```

Custom fonts go through the **`expo-font` config plugin**, not runtime `Font.loadAsync` in the render path — see `frontend/react-native/vendor/react-native-guidelines/rules/fonts-config-plugin.md`.

## Folder layout

Expo Router owns `app/` (routes = files); everything else is feature folders under `src/`:

```
app/                      # Expo Router routes (the ONLY routing source)
  _layout.tsx             # root layout (providers, Stack/Tabs)
  (tabs)/                 # route group → tab navigator
    _layout.tsx
    index.tsx             # a screen
  [id].tsx                # dynamic route with typed param
  +not-found.tsx          # 404 screen
src/
  components/             # shared atoms/molecules (AppText, PrimaryButton)
  features/<feature>/     # organism + hooks + api for one feature
    components/
    hooks/
    api.ts
  lib/                    # api client, storage, env, theme tokens
  theme/                  # design tokens, StyleSheet helpers
assets/                   # fonts, images, splash
```

- **Routes live only in `app/`.** A screen file default-exports the screen; navigation structure is expressed by `_layout.tsx` files and route groups (`(group)`), not a central config. → [`navigation`](../navigation/SKILL.md).
- Keep the `app/` files thin — they compose feature organisms from `src/features/*`. Business logic never lives in a route file.
- Re-export a **design-system folder** rather than importing third-party UI deep across the app → `.../rules/imports-design-system-folder.md`.

## Quality gates every project ships with

- **TypeScript strict** — `tsconfig.json` extends `expo/tsconfig.base`, `"strict": true`, no `any`. Enable **typed routes**: `app.json` → `experiments.typedRoutes: true` for compile-checked `<Link href>`.
- **ESLint flat config** — `pnpm expo lint` scaffolds `eslint-config-expo`; keep the flat `eslint.config.js`. Add `eslint-plugin-react-hooks` (exhaustive-deps).
- **Prettier** — shared config; format on commit.
- **Typed env** — never hardcode secrets. Public config via `app.config.ts` `extra` → read through `expo-constants` (`Constants.expoConfig.extra`); `EXPO_PUBLIC_*` env vars are inlined at build (public only — never a real secret). Sensitive tokens go in `expo-secure-store` at runtime, not env.
- **Package manager locked** — `packageManager` field; use `pnpm expo install` for RN/Expo deps so versions match the SDK.

## EAS Build / Submit

```bash
pnpm dlx eas-cli@latest login
eas build:configure          # writes eas.json (development / preview / production profiles)
eas build --profile development --platform ios   # dev-client build
eas build --profile production --platform all
eas submit --platform ios    # to the stores
```

- **`development` profile** builds the **dev client** (includes `expo-dev-client`, debuggable).
- **`preview`** = internal distribution (ad-hoc / APK) for QA.
- **`production`** = store-ready.
- Secrets are **EAS secrets / env**, never committed. OTA JS updates via **EAS Update** (`expo-updates`) — note it ships JS/asset changes only, not native changes.

## Monorepo (if applicable)

If the app lives in a monorepo (pnpm workspace / Turborepo): keep **native dependencies in the app package**, not hoisted to a shared package (`.../rules/monorepo-native-deps-in-app.md`), and pin a **single version of each dependency across packages** to avoid duplicate native modules (`.../rules/monorepo-single-dependency-versions.md`). Metro must be configured for workspace resolution.

## Handoffs

- Route tree & navigators → [`navigation`](../navigation/SKILL.md)
- Component library + theme tokens → [`component-library`](../component-library/SKILL.md), [`styling`](../styling/SKILL.md)
- First screens/components → [`generator`](../generator/SKILL.md)
- Data layer → [`data-access`](../data-access/SKILL.md)
- Auth → `auth/auth0-react` (+ `auth/_shared/auth0-concepts`)
- `testID` conventions for QA → [`testability`](../testability/SKILL.md) (`missing-testids.md` handshake to `qa-mobile-typescript`)
