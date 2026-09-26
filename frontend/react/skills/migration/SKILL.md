---
name: fe-react-migration
description: Use when upgrading a React or Next.js codebase across a major — React 18→19 (removed APIs, `forwardRef`, React Compiler) or Next 14→15 (async `params`/`searchParams`/`cookies()`, caching defaults flipped) — or porting Pages Router→App Router incrementally. Covers the official codemods and what they miss. Triggers "upgrade us to React 19", "migrate to Next 15", "move off the Pages Router", "params is a Promise now". Not for a fresh project (`project-setup`).
---

# React — Version Migration

Owns getting an **existing** codebase from one major to the next: what breaks, what the codemod handles, what it silently doesn't, and the order to do it in. Three migrations, in dependency order — **Next 15 requires React 19 for the App Router**, so a Next upgrade usually forces the React upgrade first.

**The seam with siblings.** Every other skill in this stack is *version-aware* — it applies the guidance keyed to what's already there. This skill is the only one that **changes** which version lane the project is in. Run it deliberately, as its own change, never bundled into a feature fix (per the agent's brownfield rule: a fix does not smuggle in a version upgrade).

**Order of operations:** React 18→19 → Next 14→15 → (optionally) Pages→App Router. Each step ships and is verified before the next starts. Never run two majors in one PR — when something breaks you won't know which upgrade caused it.

## When to use

- Upgrading React across 18→19, or Next across 14→15
- Adopting the App Router in a Pages Router codebase
- Diagnosing a post-upgrade break: `params` undefined, `defaultProps` ignored, data suddenly stale-or-not, `useFormState` gone
- Deciding whether an upgrade is worth doing at all right now

## When NOT to use

- New project on current versions → [`project-setup`](../project-setup/SKILL.md)
- Refactoring one component without changing versions → [`component-writer`](../component-writer/SKILL.md) / [`code-review`](../code-review/SKILL.md)
- Minor/patch bumps — those are dependency hygiene, not migration
- Component-library majors (MUI 5→6, etc.) → [`component-library`](../component-library/SKILL.md)

## Before you start — the gate

1. **Clean tree, green build.** `tsc --noEmit` 0 errors, lint 0 warnings, tests green *before* you touch a version. You cannot attribute a new failure otherwise.
2. **Its own change, its own PR.** One major per PR. Work in the checkout you are given — never create a branch or worktree.
3. **Inventory the blast radius** — grep for the removed APIs below and count. That number is the real size of the job; the version bump itself is one line.
4. **Check the floor.** React 19 needs Node 18+; Next 15 needs Node 18.18+. Both of those Node lines are past EOL (Node 20 since April 2026), so the house floor is Node 22 with Node 24 primary — if the project is below it, flag it; the Node upgrade is a separate prerequisite.

## React 18 → 19

```bash
npx codemod@latest react/19/migration-recipe     # runs the official recipe
npm i react@19 react-dom@19 && npm i -D @types/react@19 @types/react-dom@19
```

**Removed — the codemod catches most, but grep to confirm:**

| Removed | Replacement | Grep |
|---|---|---|
| `propTypes` on function components | TypeScript props | `propTypes` |
| `defaultProps` on function components | ES default parameters | `defaultProps` |
| String refs (`ref="x"`) | Callback refs / `useRef` | `ref="` |
| `ReactDOM.render` / `hydrate` | `createRoot` / `hydrateRoot` | `ReactDOM.render`, `ReactDOM.hydrate` |
| `ReactDOM.findDOMNode` | A real ref | `findDOMNode` |
| `useFormState` | `useActionState` (from `react`) | `useFormState` |
| Legacy Context (`childContextTypes`) | `createContext` | `childContextTypes` |

**Changed, not removed — the ones that bite silently:**

- **`forwardRef` is no longer needed.** `ref` is a normal prop on function components. Existing `forwardRef` still works — don't churn the whole codebase; drop it as you touch files.
- **Ref callbacks may return a cleanup function.** A callback ref that used to *implicitly* return something (an arrow body like `ref={el => (map[id] = el)}`) is now interpreted as returning a cleanup. Give those arrows a block body: `ref={el => { map[id] = el; }}`.
- **`useReducer` / `useState` init typing tightened** — some previously-inferred generics now need annotating.
- **Errors are no longer re-thrown to `window.onerror` by default** — hook `onUncaughtError` / `onCaughtError` on `createRoot` if you report client errors ([`error-handling`](../error-handling/SKILL.md)).
- **Hydration mismatch messages changed shape.** Existing log-scraping or error-grouping rules will miss them.

**New capability you can now adopt** (incrementally — the upgrade doesn't require it): `use()`, Actions + `useActionState` + `useOptimistic` ([`forms`](../forms/SKILL.md)), `<title>`/`<meta>` hoisting ([`seo`](../seo/SKILL.md)), and the **React Compiler** for auto-memoization.

> **React Compiler is a separate decision, not part of the upgrade.** Turn it on only after React 19 has shipped and is stable in production, and only on a codebase that follows the Rules of React — it is a build-time optimizer, and a component that mutates props or reads refs during render will behave differently under it. Enable it, run the full suite, and check [`performance`](../performance/SKILL.md) before assuming a win.

## Next 14 → 15

```bash
npx @next/codemod@canary upgrade latest
```

**Breaking change 1 — request APIs are async.** This is the one that touches the most files:

```tsx
// Next 14
export default function Page({ params, searchParams }: { params: { slug: string } }) {
  const c = cookies();
  return <X slug={params.slug} />;
}

// Next 15 — params, searchParams, cookies(), headers(), draftMode() all return Promises
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ q?: string }>;
}) {
  const { slug } = await params;
  const c = await cookies();
  return <X slug={slug} />;
}
```

In a **Client Component**, unwrap with `use()` instead of `await`: `const { slug } = use(params);`. See [`routing`](../routing/SKILL.md) for the full segment/param model.

**Breaking change 2 — caching defaults flipped.** Next 14 cached aggressively by default; Next 15 does not. Nothing errors — your app just does more work than it used to, or shows fresher data than you designed for:

| | Next 14 default | Next 15 default |
|---|---|---|
| `fetch()` | cached (`force-cache`) | **not cached** (`no-store`) |
| `GET` Route Handlers | cached | **not cached** |
| Client Router Cache (page segments) | 30s reuse | **0 — refetched on nav** |

Re-opt in explicitly where you relied on it: `fetch(url, { cache: 'force-cache' })`, `export const dynamic = 'force-static'`, or `experimental.staleTimes` for the router cache. Audit this deliberately — a silent 3× jump in origin requests is the usual symptom of skipping it.

**Also changed:** `next/font` is built in (drop `@next/font`); `images.domains` → `images.remotePatterns`; the App Router requires **React 19** (the Pages Router still accepts 18); ESLint 9 support.

## Pages Router → App Router

**Both routers run in the same app.** This is an incremental migration, not a rewrite — `app/` takes precedence for a matching path, everything else keeps falling through to `pages/`. Migrate route by route, lowest-traffic first, shipping each.

| Pages Router | App Router |
|---|---|
| `pages/about.tsx` | `app/about/page.tsx` |
| `pages/_app.tsx` + `pages/_document.tsx` | `app/layout.tsx` (one root layout with `<html>`/`<body>`) |
| `getServerSideProps` | `async` Server Component that awaits its data directly |
| `getStaticProps` + `getStaticPaths` | `generateStaticParams` + a cached `fetch` |
| `getInitialProps` | — (no equivalent; restructure) |
| `pages/api/x.ts` | `app/api/x/route.ts` exporting `GET`/`POST` |
| `next/router` (`useRouter().query`) | `next/navigation` (`useParams`, `useSearchParams`, `usePathname`) |
| `next/head` | the Metadata API ([`seo`](../seo/SKILL.md)) |

**The migration order that works:**

1. Add `app/layout.tsx` (root layout) — required before any `app/` route renders.
2. Move **leaf, low-traffic, static** routes first. Verify each in production.
3. Convert `getServerSideProps`/`getStaticProps` to direct `await` in the Server Component. The data logic usually survives unchanged; the *plumbing* around it disappears.
4. Move API routes to route handlers **last** — the Pages Router versions keep working, and nothing forces the move.
5. Delete `pages/` only when it is empty.

**The trap:** the reflex port is to paste `'use client'` at the top of every migrated page so the old hooks and event handlers keep working. That produces an App Router app with none of its benefits — one giant client bundle, no RSC. Port the page as a **Server Component**, then push `'use client'` down to the leaves that genuinely need interactivity ([`basics`](../basics/SKILL.md), [`performance`](../performance/SKILL.md)).

## Verification (every migration, non-negotiable)

Per [`ep-verify-before-done`](../../../../engineering-practices/verify-before-done/SKILL.md) — an upgrade you haven't run is not done. Inside a `Gate: none` plan task, run none of these checks and report the upgrade as "written, not run"; the plan's gate task runs them.

1. `<pm> build` clean · `tsc --noEmit` 0 errors · lint 0 warnings
2. `<pm> test` green (Vitest) — plus the `qa-ui-typescript` peer's E2E suite if one exists; a major upgrade is exactly when E2E earns its cost
3. **Boot the app and click the critical paths.** Hydration mismatches, caching-default changes, and lost `'use client'` boundaries do not show up in a type check.
4. Diff the **network panel** on a key route before/after a Next 15 upgrade — this is how you catch the caching flip.
5. Report what changed, what the codemod did, and what you fixed by hand.

## Anti-patterns

| Anti-pattern | Why it's wrong | Do instead |
|---|---|---|
| Two majors in one PR | A break can't be attributed | One major per PR, verified and shipped |
| Upgrade bundled into a feature/bugfix | Review becomes impossible; a revert takes the feature with it | Separate change, separate PR |
| Trusting the codemod's exit code | Codemods handle syntax, not semantics — the caching flip and async params in dynamic call sites are missed | Grep the removed-API table yourself; boot the app |
| `'use client'` on every migrated page | App Router with none of its benefits | Server Component by default, client at the leaves |
| Big-bang `pages/` → `app/` rewrite | Both routers coexist; a rewrite is all risk, no need | Route by route, ship each |
| Enabling React Compiler in the same PR as the React 19 bump | Two variables, one experiment | Ship 19, stabilize, then evaluate the Compiler |
| Leaving `params` un-awaited because "it still renders" | It's a Promise — you're reading `undefined` or relying on a deprecation shim | `await params` (or `use(params)` client-side) |

## Related skills

- [`routing`](../routing/SKILL.md) — the async `params`/`searchParams` model you migrate *to*
- [`basics`](../basics/SKILL.md) — the RSC boundary a Pages→App migration has to get right
- [`data-fetching`](../data-fetching/SKILL.md) — caching/`revalidate` semantics the Next 15 defaults changed
- [`performance`](../performance/SKILL.md) — verifying the upgrade didn't regress bundle/render cost
- [`component-testing`](../component-testing/SKILL.md) — the suite that proves the migration held
