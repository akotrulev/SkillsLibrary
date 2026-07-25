---
name: fe-react-seo-discoverability
description: Use when public/crawlable pages must rank and preview correctly — server/static rendering for public routes (client-only is blank to crawlers), per-route `metadata`/`generateMetadata`, a real 404 (`not-found.tsx`), `sitemap.ts`, `robots.ts`, JSON-LD. Triggers "make these pages crawlable", "set per-page meta and OG tags", "my page shows blank to Google", "the link preview is empty when shared". Not for the tab-title convention (`ui-conventions`) or route files (`routing`).
---

# React — SEO & Discoverability

Owns making **public, crawlable** pages rank and preview correctly: the render strategy that emits real HTML, the per-route `<head>` metadata a crawler and a social unfurl read, a truthful 404, and the site-level discovery files. Internal/authenticated app screens don't need this — it's for marketing, content, docs, product/landing, and any route a search engine or a shared link should resolve.

**The seam with siblings.** [`ui-conventions`](../ui-conventions/SKILL.md) owns the *convention* that every page has a title (tab title, one-name-one-concept); [`generator`](../generator/SKILL.md) *emits* the `metadata`/`generateMetadata` scaffold. **This skill owns the SEO *content*** hung off it: `description`, `canonical`, Open Graph / Twitter Card, and JSON-LD — the parts a crawler and an unfurl read, not the browser-tab string. No overlap.

**Version rule:** the Metadata API (`export const metadata` / `generateMetadata`), `not-found.tsx`/`notFound()`, `sitemap.ts`, `robots.ts`, and RSC streaming are stable on **Next 14 and 15** (Next 15's async request APIs — `await cookies()`/`params` — matter where metadata reads them). The **Vite SPA** lane has **no server render** — a client-rendered SPA is blank to crawlers/unfurl bots on first paint; SEO there requires SSR/prerendering (a framework like Remix/React Router 7 in SSR mode, or a prerender step) and **React 19 `<title>`/`<meta>` hoisting** (render metadata tags from anywhere; they hoist to `<head>`) instead of the Next Metadata API. Tag the SPA path explicitly; the App Router is primary.

## When to use

- Deciding the render strategy for a public/marketing/content route (crawlability)
- Setting per-route `title` + `meta description` + Open Graph/Twitter tags from route data
- Making streamed content visible to crawlers
- Returning a correct 404 (status code + page)
- Adding canonical URLs, `sitemap.xml`, `robots.txt`
- Adding JSON-LD structured data (Article, Product, BreadcrumbList, Organization)

## When NOT to use

- The tab-title **convention** → [`ui-conventions`](../ui-conventions/SKILL.md); its **emission** in scaffolds → [`generator`](../generator/SKILL.md)
- Choosing render strategy for the app generally → [`project-scaffold`](../project-scaffold/SKILL.md) (this skill applies the *public-page* corollary)
- Public-page load performance (bundle, LCP, streaming for speed) → [`performance`](../performance/SKILL.md)
- Internal/authenticated screens (no crawler ever sees them) — skip SEO entirely
- Blazor → `frontend/blazor/skills/seo-discoverability`

## Crawlability = render strategy. Public pages default to server rendering

A crawler reads the **HTTP response body**. Whatever a page needs client JS to render **is not in that body** on first paint — so a client-only component (a `'use client'` tree that fetches after hydration, or `next/dynamic` with `ssr:false`) is blank to a crawler and to a social unfurl bot (which never runs JS at all).

| Public route type | Render strategy | Why |
|---|---|---|
| Marketing / landing / content / docs / blog | **Static (SSG)** — Server Component, no dynamic APIs, cached | Full HTML in the response; fastest first paint; served from the edge |
| Content that changes but is cacheable | **ISR** — `revalidate` / `revalidateTag` | Static HTML, refreshed on a schedule / on demand |
| Per-request public page (personalized-but-crawlable, fresh data) | **Dynamic SSR** — Server Component that reads request data | Full HTML per request; still crawlable |
| Public page with an interactive widget | **Server Component + a `'use client'` island** | Content crawlable; only the widget hydrates |

**Rule:** default every public route to **server rendering** (a Server Component — static where possible), and add interactivity **per-island** only where a feature needs it. Never make a page's core content depend on a client render or an `ssr:false` dynamic import. (Render-strategy selection generally is [`project-scaffold`](../project-scaffold/SKILL.md)'s; this is its public-page corollary; keeping the payload small for *speed* is [`performance`](../performance/SKILL.md)'s.)

## Per-route head metadata (Metadata API)

On the App Router, export `metadata` (static) or `generateMetadata` (dynamic, from route data) from a `page.tsx`/`layout.tsx` — Next emits the tags **on the server response**, so crawlers and unfurlers see them:

```tsx
// app/products/[slug]/page.tsx
import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const p = await getProduct((await params).slug);
  if (!p) return {};                                   // 404 handled in the page via notFound()
  const url = `https://acme.com/products/${p.slug}`;
  return {
    title: `${p.name} — Acme`,                          // tab-title convention: ui-conventions
    description: p.summary,                             // unique per page — shows under the result
    alternates: { canonical: url },
    openGraph: {
      title: p.name, description: p.summary, url, type: 'website',
      images: [{ url: p.imageAbsoluteUrl }],           // MUST be absolute
    },
    twitter: { card: 'summary_large_image', title: p.name, description: p.summary },
  };
}
```

- **Description** is per-page and unique — no boilerplate site description repeated on every page.
- **Open Graph + Twitter Card** drive the link preview. `og:image` must be an **absolute** URL; provide title/description/image/url/type at minimum. Prefer the **`opengraph-image.tsx`/`twitter-image.tsx`** file conventions (Next generates the tags + can render the image with `ImageResponse`) for dynamic social cards.
- Set everything from **route/model data**, not hardcoded — the route knows its own product/article.
- `metadata` in a `layout.tsx` provides defaults; a page's `metadata` **merges over** them (title templates via `title.template`).
- **Vite/SPA fallback:** no Metadata API — render `<title>`/`<meta>`/`<link rel="canonical">` from the component (React 19 hoists them to `<head>`), but remember these only help crawlers if the page is **server-rendered/prerendered** (see the version rule).

## Streaming without breaking crawlers

RSC streaming (Suspense boundaries returning the shell first, data streaming into the **same response**) is crawler-safe **as long as the content is server-rendered, not client-injected**:

- **Server-streamed content is crawlable** — the streamed HTML arrives in the response body; a crawler reading the full response sees the final content.
- **Client-fetched-after-hydration content is not** — if the real content only appears after a `'use client'` `useEffect`/query, the crawler sees the fallback. That's the anti-pattern: don't hide crawlable content behind a client render.
- Keep the Suspense fallback semantically empty (a skeleton) and ensure the final streamed markup carries the real `<h1>`/text/links.

## A truthful 404

A wrong URL — or a valid route with no data (`/products/nonexistent`) — must return **HTTP 404**, not a 200 with a "not found" message (a soft-404 that search engines index and that dilutes the site):

```tsx
// in the page/segment
import { notFound } from 'next/navigation';
const product = await getProduct(slug);
if (!product) notFound();          // renders the nearest not-found.tsx AND returns HTTP 404
```

- Add **`app/not-found.tsx`** (global) and/or per-segment `not-found.tsx`; `notFound()` returns a real 404 status.
- The not-found page carries `metadata: { robots: { index: false } }` (noindex) and a helpful message + a link home.
- **Vite/SPA:** a client-routed "404" component returns HTTP 200 by default — a soft-404. Real status codes need the SSR framework's 404 handling or server config; note this as the down-level limitation.

## Site-level discovery: canonical, sitemap, robots

- **Canonical** — `metadata.alternates.canonical` per page, an absolute URL from a configured base host (dedupes trailing-slash / query / casing variants). Never a `localhost` fallback ([`project-scaffold`](../project-scaffold/SKILL.md) config hygiene).
- **`sitemap.ts`** — a `MetadataRoute.Sitemap` export; static array for small sites, or fetch the slugs for data-driven URLs. Include only **canonical, indexable, public** URLs; keep `lastModified` honest:
  ```ts
  // app/sitemap.ts
  import type { MetadataRoute } from 'next';
  export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
    const products = await getPublicProducts();
    return products.map((p) => ({ url: `https://acme.com/products/${p.slug}`, lastModified: p.updatedAt }));
  }
  ```
- **`robots.ts`** — a `MetadataRoute.Robots` export: allow public areas, `disallow` app/auth paths, and point to the sitemap. Don't `disallow: '/'` in production by accident (a classic launch-day de-indexing):
  ```ts
  // app/robots.ts
  export default function robots(): MetadataRoute.Robots {
    return { rules: { userAgent: '*', allow: '/', disallow: ['/app/', '/api/', '/account/'] },
             sitemap: 'https://acme.com/sitemap.xml' };
  }
  ```

## Structured data (JSON-LD)

Emit `schema.org` JSON-LD in a `<script type="application/ld+json">` rendered **from a Server Component** (so it's in the response body a crawler reads). Serialize from the model; use the right `@type` (`Article`, `Product`, `BreadcrumbList`, `Organization`, `FAQPage`). Keep it **consistent with the visible content** — Google penalizes JSON-LD describing content not on the page.

```tsx
<script type="application/ld+json"
  dangerouslySetInnerHTML={{ __html: JSON.stringify({
    '@context': 'https://schema.org', '@type': 'Product',
    name: p.name, description: p.summary, image: p.imageAbsoluteUrl,
    offers: { '@type': 'Offer', price: p.price, priceCurrency: 'USD' },
  }) }} />
```

## Rules

- **Public routes default to server rendering** (Server Component, static/ISR where possible); interactivity per-island only — never make core content depend on a client render or `ssr:false`.
- **Per-route unique `title` + `description`** via `metadata`/`generateMetadata`, set from route/model data.
- **Open Graph + Twitter Card** on shareable pages; `og:image` absolute (or the `opengraph-image` file convention).
- **One canonical per page** (`alternates.canonical`), absolute, from a configured base host.
- **Streamed content stays server-rendered** (in the response), never client-fetched-after-hydration — else it's invisible to crawlers.
- **Real 404 status**: `notFound()` + `not-found.tsx`; 404/error pages `noindex`.
- **Ship `sitemap.ts` (canonical, indexable URLs only) + `robots.ts`** (allow public, disallow app/auth, link the sitemap).
- **JSON-LD** for content that earns rich results, consistent with the visible page, emitted server-side.

## What NOT to do

- No public page whose content only renders after hydration / behind `ssr:false` (blank to crawlers + unfurl bots).
- No shared/boilerplate `description` repeated across pages; no missing OG tags on shareable pages; no relative `og:image`.
- No content hidden behind a *client* render that a crawler needs (RSC streaming is fine; client-fetch-after-hydration is not).
- No soft-404 (200 with "not found"); no indexable 404/error page.
- No missing/wrong canonical; no `disallow: '/'` shipped to production; no sitemap listing non-canonical or authed URLs.
- No JSON-LD describing content that isn't on the page.
- **Don't** re-own the tab-title convention (ui-conventions) or its scaffold emission (generator) — only the SEO metadata content.

## Validation

- **View source** (not the rendered DOM) / `curl` a public page: the `<h1>`, body text, `title`, `meta description`, canonical, OG tags, and JSON-LD are all present in the **response HTML**.
- Load the page with JS disabled — the core content is there.
- Hit a non-existent URL and a valid-route-no-data URL → **HTTP 404** (check the status, not just the page), and it's `noindex`.
- `/sitemap.xml` returns valid XML of canonical public URLs; `/robots.txt` allows public paths, disallows app/auth, links the sitemap.
- Run the URL through a rich-results / OG-preview checker → title/description/image/structured-data render correctly.

## Handoffs

- Tab-title convention → [`ui-conventions`](../ui-conventions/SKILL.md); its emission in scaffolds → [`generator`](../generator/SKILL.md)
- Render-strategy selection across the app → [`project-scaffold`](../project-scaffold/SKILL.md)
- Public-page load performance (bundle, LCP, streaming for speed) → [`performance`](../performance/SKILL.md)
- Configured base-host / no-localhost-fallback for absolute URLs → [`project-scaffold`](../project-scaffold/SKILL.md)
- Automated Lighthouse SEO/score gate in CI → qa `accessibility-testing`/CI peers (Lighthouse covers SEO + a11y + perf categories)
