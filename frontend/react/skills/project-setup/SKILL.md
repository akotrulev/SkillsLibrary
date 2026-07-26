---
name: fe-react-project-setup
description: Use when standing up a new app from zero — Next.js 15 App Router (primary) or Vite SPA (fallback) — rendering strategy per route, server/client boundary, feature folders, strict TS, ESLint/Prettier, typed env config. Triggers "create a new React/Next.js project", "scaffold a Next.js App Router app", "which rendering strategy for this route". Not for scaffolding into an existing app (`component-writer`), the route tree (`routing`), or upgrades (`migration`).
---

# React — Project Scaffold

Stands up a **Next.js 15 App Router** app (primary) or a **Vite SPA** (fallback lane) from zero: the framework choice, the **rendering strategy decided per route** (Server Component default / Client island / static / dynamic / streaming), the feature-folder layout and the `'use client'` boundary, and the quality gates every project ships with (strict TS, ESLint flat config, Prettier, a locked package manager, typed env).

**Version rule:** detect the installed React/Next major from `package.json` **first** — it drives every version-sensitive recipe. React 19 + Next 15 are primary; React 18 + Next 14 are tagged fallbacks. Never emit a React-19-only API (`use()`, ref-as-prop, Actions) into a React 18 project, or an async-request-API pattern into Next 14.

## When to use

- New Next.js App Router app, or a new Vite React SPA
- Deciding the rendering strategy for a specific route (static/dynamic/streaming; where the client islands sit)
- Setting up feature folders, the `'use client'` boundary, strict TS, ESLint/Prettier, env config

## When NOT to use

- Adding a component/page to an existing app → [`component-writer`](../component-writer/SKILL.md)
- Request/response data fetching → [`data-fetching`](../data-fetching/SKILL.md)
- Live/push data → [`realtime`](../realtime/SKILL.md)
- Component library + theming → [`component-library`](../component-library/SKILL.md), [`styling`](../styling/SKILL.md)
- Auth0 wiring → `auth/auth0-react`
- Concepts / RSC explanation → [`basics`](../basics/SKILL.md)

## Inputs needed

0. **Framework + versions** — Next.js App Router (default) or Vite SPA; React 18/19, Next 14/15 (drives recipe variants)
1. **Route shapes** — the routes/features and their data shape (content · API-consuming · live/push · offline) — this drives per-route rendering, not one global choice
2. **Backend** — is there an API to consume, a database the server touches directly, or both?
3. **Auth** — needed at scaffold time? (pairs with `auth/auth0-react`)
4. **Component library** — MUI (default) or another (pairs with [`component-library`](../component-library/SKILL.md))

## Create the app

### Next.js App Router (primary)

```bash
pnpm create next-app@latest my-app --ts --app --eslint --src-dir --import-alias "@/*"
# then, per house style: MUI + emotion, no Tailwind (see component-library/styling)
```

| Prompt | Choice | Why |
|---|---|---|
| TypeScript | **yes** | strict mode is a house rule |
| App Router | **yes** | RSC is the primary target |
| `src/` directory | **yes** | keeps `app/` and code out of the repo root |
| Import alias | **`@/*`** | stable absolute imports |
| Tailwind | **no** (default lib is MUI) | one styling authority; only "yes" if the chosen library is shadcn — [`styling`](../styling/SKILL.md) |
| Turbopack | yes | faster dev builds |

### Vite SPA (fallback lane)

```bash
pnpm create vite@latest my-app -- --template react-ts
pnpm add react-router-dom @tanstack/react-query
```

No server runtime, no RSC — every component is a client component, data comes from hooks against your API, routing is React Router 7. Choose this only when there is genuinely no server-render need (an internal tool behind auth, an embedded widget). Everything below that says "RSC" or "Server Component" collapses to "there's only the client" in this lane.

## Rendering strategy — per route, not per app

**Server Components are the default; client interactivity is opt-in per island.** A content page, an API-consuming dashboard, and a live ticker do not share a strategy. Decide per route:

```
Does this route need client interactivity (state, effects, event handlers, browser APIs)?
  NO  → keep it a Server Component (no JS shipped). Add <Suspense> + streaming for slow data.
  YES → keep the route a Server Component and push 'use client' onto the interactive leaves.
        Is the data personalized / request-time (cookies, headers, search params)?
          YES → dynamic rendering (opt out of static: the request APIs force it)
          NO  → static rendering (default) — prerender at build; revalidate on a timer/tag (ISR)
        Is first data slow but the shell can paint now?
          → wrap the slow part in <Suspense> and stream it
```

| Strategy | What it is | Best for | Cost |
|---|---|---|---|
| **Static (default)** | prerendered at build, cached; `revalidate` for ISR | content, marketing, catalog, anything not per-user | stale until revalidated |
| **Dynamic** | rendered per request (triggered by `cookies()`/`headers()`/`searchParams`/`no-store`) | dashboards, personalized pages, authed views | a server render per request |
| **Streaming** | shell now, slow parts stream in via `<Suspense>` | slow first data, above-the-fold speed matters | more moving parts; ensure fallbacks are designed |
| **Client island** | a `'use client'` leaf inside a server route | one interactive widget on an otherwise static page | ships that subtree's JS — keep it small |

**Don't make the whole route a Client Component** to get one interactive button — that drags the entire subtree into the bundle. Keep the route server, island the button (the boundary rule from [`basics`](../basics/SKILL.md)). Document the per-route decision in the Phase-1 decision record, like the Blazor render-mode map.

## Project layout — feature folders + the app router tree

Next's `app/` directory is the **routing** tree (folders = URL segments; `page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`, `not-found.tsx`, `route.ts`). Your **code** lives in feature folders under `src/`, imported by the thin route files:

```
src/
  app/                         # routing only — thin files that import from features/
    layout.tsx                 # root layout (providers, <html>, fonts)
    page.tsx                   # "/" — imports from features/
    orders/
      page.tsx                 # "/orders" — a Server Component that fetches + composes
      loading.tsx              # Suspense fallback for the segment
      error.tsx                # 'use client' error boundary for the segment
      [id]/page.tsx            # "/orders/:id"
    api/                       # route handlers (route.ts) if this app owns endpoints
  features/                    # capability-first code
    orders/
      OrderTable.tsx           # organism (Server or Client per interactivity)
      OrderRow.tsx
      useOrders.ts             # client data hook (TanStack Query) if needed
      orders.actions.ts        # 'use server' Server Actions
      orders.schema.ts         # Zod schemas / types
  components/                  # shared, reuse-first atoms + generic molecules
    Button.tsx
    SearchBox.tsx
  lib/                         # cross-cutting: api client, env, utils
  theme/                       # MUI theme / tokens (see styling)
```

**Feature folders over type folders.** Group by capability (`features/orders/{OrderTable, useOrders, orders.actions, orders.schema}`), not by artifact type (`components/`, `hooks/`, `services/` split apart). A feature is deletable and reviewable as one unit. Keep `app/` files **thin** — routing, layout, and composition; the real logic lives in `features/`.

### Component layering — reuse levels inside feature folders

Feature folders answer *"which capability owns this?"*; a reuse-level taxonomy answers *"how widely is this shared?"*. Use both — the level decides *where the file lives*, not a competing top-level folder tree.

| Level | What it is | Reuse scope → where it lives | Server/Client |
|---|---|---|---|
| **Atom** | one indivisible control — `Button`, `CurrencyInput`, `Badge`, `Spinner` | app-wide → shared `components/` | agnostic; client only if it has an event handler |
| **Molecule** | a few atoms doing one small job — `SearchBox`, `LabeledField`, `Pagination` | app-wide if generic, else the feature folder | client if interactive |
| **Organism** | a domain-aware section — `OrderTable`, `CustomerCard` | feature folder (`features/orders/OrderTable.tsx`) | either; data via props or a client hook |
| **Template** | a layout arrangement with slots, no real data — `AppShell`, `TwoPaneLayout` | `components/` or `app/*/layout.tsx` | Server Component |
| **Page / route** | a routable `page.tsx` that fetches + composes organisms | `app/<segment>/page.tsx`, logic in `features/` | Server Component that decides where islands sit |

- **Cross-feature atoms/molecules → shared `components/`.** Feature-specific organisms + route composition → the feature folder / `app/`.
- **Promote on the second reuse, not the first** — premature "atomization" produces a library of one-consumer atoms nobody can find. Duplicate once; extract on the second use.
- **Atoms and molecules stay domain-free** — no data hooks, no domain types; that starts at the organism. This is what keeps them reusable across features. (The conceptual treatment lives in [`basics`](../basics/SKILL.md).)

> **Don't build a global `atoms/`/`molecules/`/`organisms/` tree.** It fights feature folders and scatters one capability across three directories. Keep the taxonomy as a placement heuristic.

## Quality gates (every project)

**Strict TypeScript** — `tsconfig.json` extends the Next base and turns on the full strict surface:

```jsonc
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "verbatimModuleSyntax": true,
    "paths": { "@/*": ["./src/*"] }
  }
}
```

- **ESLint (flat config)** — `next/core-web-vitals` + `@typescript-eslint` (type-checked rules) + `eslint-plugin-react-hooks` (the exhaustive-deps + rules-of-hooks gate). **Prettier** for formatting (or Biome for both). Wire them into a `lint`/`format` script and CI — style drift fails the build, not review.
- **Locked package manager** — commit the lockfile; pin the manager with `"packageManager": "pnpm@x.y.z"` in `package.json` (or Corepack). pnpm is the house default (strict, fast); npm/yarn are fine if the repo already uses them — match, don't convert.
- **React Compiler** — enable it in a new Next 15 app (`experimental.reactCompiler` / the stable flag for your version) so `useMemo`/`useCallback` are mostly automatic; [`performance`](../performance/SKILL.md) says where you still hand-memoize.
- **Absolute imports** via the `@/*` alias — no `../../../` climbs.

## Config hygiene (env)

- **No hardcoded URLs or `localhost` fallbacks in components.** Base addresses come from env, read through a **typed, validated** config module (Zod-parse `process.env` once at startup in `src/lib/env.ts`) — a missing var fails fast at boot, not mysteriously at runtime.
- **`NEXT_PUBLIC_` is a client-exposure boundary.** Only vars that are safe in the browser bundle get that prefix. **Secrets (API keys, DB URLs, tokens) are server-only** — no `NEXT_PUBLIC_`, never imported into a Client Component. A leaked secret is a scaffold-time bug.
- **`.env.local` is git-ignored** for local, non-secret overrides; real secrets live in the platform's secret store (global rule).
- External-system links (consoles, vendor dashboards) are config keys, not string literals.

## Rules

- **Server Component default; `'use client'` opt-in per leaf.** Keep routes server; island the interactive parts.
- **Decide rendering strategy per route** (static/dynamic/streaming) from its data shape, using the matrix; document it.
- **Feature folders**, not type folders; `app/` files stay thin. Layer by reuse level as a placement heuristic; promote to shared on the second consumer.
- **Strict TS + ESLint (hooks rules) + Prettier + locked lockfile** from commit one — retrofitting is painful.
- **Real `<Link>` navigation**, `not-found.tsx` per app, `metadata` on every route (see [`component-writer`](../component-writer/SKILL.md), [`seo`](../seo/SKILL.md)).
- **Typed, validated env**; secrets server-only; no `NEXT_PUBLIC_` on secrets.
- **Version keyed** — follow the detected React/Next major; no React-19-only API in an 18 project.

## What NOT to do

- No blanket `'use client'` on a route "to keep it simple" — it opts the whole subtree into the bundle.
- No one-rendering-strategy-for-the-whole-app; no hardcoded strategy inside a reusable component (the route decides).
- No `NEXT_PUBLIC_` on a secret; no secret imported into a Client Component; no DB/server-only dep reachable from a `'use client'` file.
- No global `atoms/`/`molecules/`/`organisms/` tree competing with feature folders; no domain types inside an atom; no extracting a shared component before a second consumer exists.
- No hardcoded URLs / `localhost` fallbacks; no `../../../` imports when the alias exists.
- No React-19-only API in a React 18 project; no async-request-API pattern in Next 14.

## Validation (exit gate)

- `pnpm build` — **clean** (type errors and lint errors fail it).
- App **boots**: `pnpm dev`, home route renders.
- **One route per chosen strategy renders** — a static content route, one dynamic/personalized route, and (if used) a streamed route with its `loading.tsx`. Confirm a client island hydrates and a Server Component ships no JS for its subtree.
- Lockfile committed; `@/*` alias resolves; typed env parses at boot.

## Handoffs

- Fetch data into these routes → [`data-fetching`](../data-fetching/SKILL.md) (request/response · Server Actions) · [`realtime`](../realtime/SKILL.md) (live/push)
- Scaffold pages/components/forms → [`component-writer`](../component-writer/SKILL.md) · [`forms`](../forms/SKILL.md)
- Component library + theme → [`component-library`](../component-library/SKILL.md), [`styling`](../styling/SKILL.md)
- Auth → `auth/auth0-react`
- Concepts / RSC explanation → [`basics`](../basics/SKILL.md)
- CI pipeline for the app → `qa/cicd/typescript` (peer, invoked separately)
