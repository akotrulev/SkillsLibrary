---
name: fe-react-routing
description: Use when adding, nesting, or debugging routes in a Next.js App Router app — file conventions (`page`/`layout`/`template`/`loading`/`not-found`/`route`), parallel (`@slot`) and intercepting (`(.)`) modal routes, `middleware.ts` gating. Triggers "add a route/page for X", "make this a modal route", "my layout remounts on every navigation", "protect these routes with middleware". Not for project setup (`project-setup`), fetching in a route (`data-fetching`), or metadata (`seo`).
---

# React — Routing & Navigation (Next.js App Router)

Owns the **URL → UI mapping**: which file makes a route, how routes nest and share chrome, how a segment reads its params, how you move between routes, and what runs before a route renders. Blazor's `@page` directive collapses this into one line; the App Router spreads it across a file-convention system, so it gets its own skill.

**The seam with siblings.** [`project-setup`](../project-setup/SKILL.md) picks the **render target and per-route rendering strategy** at setup time; this skill owns the **route topology** you build inside that choice. [`data-fetching`](../data-fetching/SKILL.md) owns what a route *fetches* once it renders; [`seo`](../seo/SKILL.md) owns the `metadata` hung off a route; [`error-handling`](../error-handling/SKILL.md) owns what `error.tsx` *renders*. This skill owns only the files, the segments, and the navigation between them.

**Version rule.** In **Next 15**, `params` and `searchParams` are **Promises** — `await` them (or `use()` them in a Client Component). In **Next 14** they are plain objects. This is the single most common upgrade break; check the Next major before writing either. Route groups, parallel/intercepting routes, `middleware.ts`, and `generateStaticParams` are stable on both. The **Vite SPA** lane uses **React Router 7** instead — the file conventions below do not exist there; see "The Vite / React Router lane".

## When to use

- Adding a route, a nested route, or shared chrome across a group of routes
- Reading a dynamic segment (`[slug]`, `[...path]`) or a query string
- Building a modal route (URL-addressable overlay that survives refresh + share)
- Gating routes before render (auth, locale, A/B, redirects) via `middleware.ts`
- Navigating programmatically, or reacting to the current path/query
- Diagnosing "my layout remounts", "searchParams broke my static build", "params is a Promise"

## When NOT to use

- Choosing App Router vs Pages Router vs Vite at project setup → [`project-setup`](../project-setup/SKILL.md)
- Fetching/mutating data inside a route → [`data-fetching`](../data-fetching/SKILL.md)
- `metadata` / `generateMetadata` / `sitemap.ts` content → [`seo`](../seo/SKILL.md)
- What the error / loading UI *looks like* → [`error-handling`](../error-handling/SKILL.md)
- Locale-prefixed routing mechanics → [`languages`](../languages/SKILL.md) (it owns the `[locale]` segment; this skill owns the rest of the tree)
- Auth *provider* wiring → `auth/auth0-react`; this skill only owns the middleware **gate**
- Blazor → `frontend/blazor/skills/basics` (`@page` routing)

## The file conventions

Inside `app/`, **the folder is the URL, the file is the role.** A folder only becomes a route when it contains a `page.tsx` (or `route.ts`).

| File | Role | Re-renders on sibling navigation? |
|---|---|---|
| `page.tsx` | The route's UI. Makes the segment publicly routable. | Yes — it *is* the route |
| `layout.tsx` | Shared chrome wrapping children. Receives `children`. | **No — it persists**, state survives |
| `template.tsx` | Like a layout, but **remounts** per navigation | Yes — fresh instance every time |
| `loading.tsx` | Suspense fallback for the segment | — |
| `error.tsx` | Error boundary for the segment (must be `'use client'`) | — |
| `not-found.tsx` | UI for `notFound()` and unmatched URLs | — |
| `default.tsx` | Fallback for an unmatched **parallel** slot | — |
| `route.ts` | HTTP endpoint (GET/POST/…) instead of UI | — |

**`layout` vs `template` is the answer to "why does/doesn't my state reset".** A layout is mounted once and kept — a scroll position, an open sidebar, or a form draft inside it survives navigation between its children. A template remounts on every navigation, so it resets. Reach for `template.tsx` only when you *want* the reset (enter animations, per-route logging); a layout is the default.

**`page.tsx` and `route.ts` cannot coexist** in the same segment — one URL, one handler.

### Folders that don't become URL segments

```
app/
  (marketing)/            # route GROUP — organizes files, adds NOTHING to the URL
    layout.tsx            #   marketing-only chrome
    about/page.tsx        #   → /about   (NOT /marketing/about)
  (app)/
    layout.tsx            #   authenticated chrome — a separate root for this group
    dashboard/page.tsx    #   → /dashboard
  _components/            # PRIVATE folder — underscore opts the subtree out of routing
    Chart.tsx
```

Route groups are how you give two sections **different layouts without different URLs** — the single most useful convention in the system, and the one most often missed. Private `_folders` let colocated components live next to the routes that use them without becoming routes.

### Dynamic segments

```
app/blog/[slug]/page.tsx          → /blog/hello          params: { slug: 'hello' }
app/shop/[...path]/page.tsx       → /shop/a/b/c          params: { path: ['a','b','c'] }   (catch-all, requires ≥1)
app/docs/[[...path]]/page.tsx     → /docs AND /docs/a/b  params: { path?: string[] }       (optional catch-all)
```

**Next 15 — `params` and `searchParams` are Promises:**

```tsx
// app/blog/[slug]/page.tsx  — Next 15 (Server Component)
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ page?: string }>;
}) {
  const { slug } = await params;
  const { page = '1' } = await searchParams;
  return <Post slug={slug} page={Number(page)} />;
}
```

```tsx
// Next 14 — plain objects, no await
export default async function Page({ params }: { params: { slug: string } }) {
  return <Post slug={params.slug} />;
}
```

Pre-render the known set with `generateStaticParams` (this is also what makes the route static):

```tsx
export async function generateStaticParams() {
  const posts = await getPosts();
  return posts.map((p) => ({ slug: p.slug }));   // keys must match the folder name
}
```

## Modal routes: parallel + intercepting routes

A **URL-addressable modal** — opens over the current page on click, but is a real page on refresh or when the link is shared. This needs both conventions together.

```
app/
  layout.tsx                       # renders {children} AND {modal}
  page.tsx                         # the feed  →  /
  @modal/
    default.tsx                    # returns null — required, or hard nav breaks the slot
    (.)photo/[id]/page.tsx         # INTERCEPTS /photo/:id during client nav → renders in the slot
  photo/[id]/page.tsx              # the real full page  →  /photo/:id  (refresh / share / crawler)
```

```tsx
// app/layout.tsx
export default function RootLayout({
  children,
  modal,
}: {
  children: React.ReactNode;
  modal: React.ReactNode;      // the @modal slot arrives as a prop named after the folder
}) {
  return <html><body>{children}{modal}</body></html>;
}
```

- `@folder` is a **parallel route** — a named slot rendered alongside `children`, passed to the layout as a prop. It adds nothing to the URL.
- `(.)segment` **intercepts** that route during *client-side* navigation only. Prefixes: `(.)` same level · `(..)` one level up · `(..)(..)` two levels up · `(...)` from the app root.
- **Every slot needs a `default.tsx`.** On a hard navigation (refresh, direct hit) Next can't recover the slot's state and renders `default.tsx`; without one you get a 404. Returning `null` is the normal answer.
- The **non-intercepted route must still exist** (`photo/[id]/page.tsx`) — that's what a refresh, a shared link, and a crawler get.

## Navigation

```tsx
import Link from 'next/link';
<Link href="/dashboard">Dashboard</Link>            // in-app navigation is always a real anchor
<Link href="/heavy" prefetch={false}>Heavy</Link>   // opt out of prefetch for rarely-taken links
```

Per the FE code rules: **in-app navigation is a real `<Link href>`, never an `onClick` `router.push` on a `<div>`.** A click handler is not keyboard-focusable, has no href for middle-click / open-in-new-tab / "copy link", and is invisible to crawlers. Use `router.push` only for navigation that follows a *non-click* event — a completed mutation, a redirect after login, a form result.

```tsx
'use client';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';

const router = useRouter();        // .push .replace .back .forward .refresh
const pathname = usePathname();    // '/blog/hello' — re-renders on route change
const params = useSearchParams();  // ReadonlyURLSearchParams
```

**`useSearchParams` opts the closest Suspense boundary into client rendering.** In a statically rendered route, calling it without a `<Suspense>` wrapper above it fails the build (`useSearchParams should be wrapped in a suspense boundary`). Wrap the component that reads it, or read `searchParams` in the Server Component page instead — prefer the server read.

**Server-side navigation** (Server Components, Route Handlers, Server Actions):

```tsx
import { redirect, notFound } from 'next/navigation';
if (!session) redirect('/login');   // 307 (or 303 from an Action)
if (!post) notFound();              // renders the nearest not-found.tsx, sends 404
```

Both work by **throwing** a special error. Never call them inside a `try { } catch { }` that swallows everything — the catch eats the redirect and the navigation silently doesn't happen. Call them outside the try, or re-throw.

## `middleware.ts` — the pre-render gate

One `middleware.ts` at the project root, running **before** the matched route renders. The right place for auth gates, locale detection, and redirects; the wrong place for data fetching or heavy work (it runs on every matched request, on the Edge runtime by default).

```ts
// middleware.ts
import { NextResponse, type NextRequest } from 'next/server';

export function middleware(req: NextRequest) {
  const session = req.cookies.get('session');
  if (!session) {
    const url = new URL('/login', req.url);
    url.searchParams.set('from', req.nextUrl.pathname);   // send them back after login
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|login).*)'],
};
```

- **Always set a `matcher`.** Without one the middleware runs on every request including static assets — a measurable cost on every page load.
- Middleware is a **coarse gate, not authorization.** It sees a cookie, not your domain rules. Re-check the real permission in the Server Component / Route Handler / Server Action that returns the data — a middleware-only check is bypassable by anything that reaches the handler another way.

## Route handlers

```ts
// app/api/products/route.ts
import { NextResponse } from 'next/server';

export async function GET(req: Request) {
  const products = await getProducts();
  return NextResponse.json(products);
}

export async function POST(req: Request) {
  const body = await req.json();               // validate with Zod — see `forms` / `data-fetching`
  return NextResponse.json(await create(body), { status: 201 });
}
```

Use these for webhooks, third-party callbacks, SSE streams ([`realtime`](../realtime/SKILL.md)), and endpoints a non-React client consumes. **Do not** add a route handler just so your own Server Component can fetch it — a Server Component should call the data source directly; the extra HTTP hop is pure latency.

## The Vite / React Router lane

No file conventions — routes are declared in code with **React Router 7**. The concepts map, the mechanics don't:

| App Router | React Router 7 |
|---|---|
| `app/blog/[slug]/page.tsx` | `<Route path="blog/:slug" element={<Post />} />` |
| `layout.tsx` | a parent `<Route element={<Layout />}>` with `<Outlet />` |
| `params` | `useParams()` |
| `searchParams` | `useSearchParams()` |
| `redirect()` | `<Navigate to>` / `redirect()` in a loader |
| `middleware.ts` | a guard component / loader wrapping the routes |
| parallel + intercepting | no equivalent — hold modal state in the URL query yourself |

There is no server render in a plain Vite SPA, so no route is crawlable — see [`seo`](../seo/SKILL.md).

## Anti-patterns

| Anti-pattern | Why it's wrong | Do instead |
|---|---|---|
| `<div onClick={() => router.push('/x')}>` | Not focusable, no href, no middle-click, invisible to crawlers | `<Link href="/x">` |
| `'use client'` on `layout.tsx` to use one hook | Makes the whole subtree client, kills RSC for every child | Keep the layout server; extract the interactive bit into a client leaf |
| `template.tsx` used as the default wrapper | Remounts on every navigation — resets state, refires effects, re-animates | `layout.tsx` unless you specifically want the reset |
| Parallel slot with no `default.tsx` | Hard navigation 404s the slot | Add `default.tsx` returning `null` |
| Intercepting route without the real route | Refresh / share / crawler hits a dead URL | Always ship the non-intercepted `page.tsx` too |
| `useSearchParams()` with no Suspense in a static route | Build error, or the whole route silently goes dynamic | Wrap in `<Suspense>`, or read `searchParams` on the server |
| `redirect()` inside `try/catch` | The catch swallows the thrown redirect; navigation never happens | Call it outside the try, or re-throw |
| `middleware.ts` with no `matcher` | Runs on static assets — cost on every request | Always scope the `matcher` |
| Middleware treated as authorization | Bypassable; it only sees a cookie | Re-check permission where the data is returned |
| Route handler fetched by your own Server Component | Needless HTTP hop and serialization | Call the data source directly in the RSC |
| Reading `params.slug` without `await` on Next 15 | `params` is a Promise — you get `undefined`/a warning | `const { slug } = await params` |

## Related skills

- [`project-setup`](../project-setup/SKILL.md) — render target + per-route rendering strategy (this skill builds inside that decision)
- [`data-fetching`](../data-fetching/SKILL.md) — what a route fetches once matched
- [`seo`](../seo/SKILL.md) — `metadata` per route, `sitemap.ts`, real 404 content
- [`error-handling`](../error-handling/SKILL.md) — what `error.tsx` / `not-found.tsx` render
- [`languages`](../languages/SKILL.md) — the `[locale]` segment and locale middleware
- [`basics`](../basics/SKILL.md) — the RSC / `'use client'` boundary these files sit on
