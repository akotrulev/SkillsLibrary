---
name: fe-blazor-seo-discoverability
description: Use when a Blazor app (.NET 8/9/10) has public/crawlable pages that must rank and preview correctly — default public routes to static SSR (interactivity kills crawlability of the initial payload), per-request `<PageTitle>`/`<HeadContent>` meta description + Open Graph/Twitter Card tags, streaming placeholders that stay in the response (not JS-injected) so crawlers see them, a real 404 (`NotFoundPage` + `NavigationManager.NotFound()` on net10; `Router` `NotFound` on net8/9), canonical URLs, `sitemap.xml`, `robots.txt`, JSON-LD. Triggers: "make these pages crawlable / SEO-friendly", "set per-page meta and OG tags", "my page shows blank to Google", "add a sitemap / robots.txt". Do NOT use for the `<PageTitle>` tab-title *convention* (`frontend/blazor/skills/ui-conventions`) or its scaffold emission (`frontend/blazor/skills/generator`) — this skill owns the meta/OG/canonical/JSON-LD CONTENT, not the title rule; not render-mode selection generally (`frontend/blazor/skills/project-scaffold`); not React.
---

# Blazor — SEO & Discoverability

Owns making **public, crawlable** pages rank and preview correctly: the render mode that emits real HTML, the per-request `<head>` metadata a crawler and a social unfurl read, a truthful 404, and the site-level discovery files. Internal/authenticated app screens don't need this — it's for marketing, content, docs, product/landing, and any route a search engine or a shared link should resolve.

**The seam with siblings.** [`ui-conventions`](../ui-conventions/SKILL.md) owns the *convention* that every page has a `<PageTitle>` (tab title, one-name-one-concept); [`generator`](../generator/SKILL.md) *emits* that `<PageTitle>` in page scaffolds. **This skill owns the SEO *content*** hung off it: the `<meta name="description">`, canonical link, Open Graph / Twitter Card tags, and JSON-LD — the parts a crawler and an unfurl read, not the browser-tab string. No overlap: they set the title convention, SEO fills the head with discovery metadata.

**Version rule:** `<PageTitle>`/`<HeadContent>`/`<HeadOutlet>` and static-SSR prerendering are net8+. The **net-sensitive** delta is the 404: **net10** ships `NotFoundPage` on the `Router` + programmatic `NavigationManager.NotFound()` that returns a real **HTTP 404** and re-executes to the page; **net8/9** only has the `Router`'s `NotFound` render fragment, which renders content but returns **HTTP 200** — an SEO defect (soft-404). The net8/9 workaround (status-code re-execution middleware) is tagged below.

## When to use

- Deciding the render mode for a public/marketing/content route (crawlability)
- Setting per-page `title` + `meta description` + Open Graph/Twitter tags from route data
- Making streamed content visible to crawlers
- Returning a correct 404 (status code + page)
- Adding canonical URLs, `sitemap.xml`, `robots.txt`
- Adding JSON-LD structured data (Article, Product, BreadcrumbList, Organization)

## When NOT to use

- The `<PageTitle>` tab-title **convention** → [`ui-conventions`](../ui-conventions/SKILL.md); its **emission** in scaffolds → [`generator`](../generator/SKILL.md)
- Choosing render modes for the app generally → [`project-scaffold`](../project-scaffold/SKILL.md) (this skill applies the *public-page* corollary)
- WASM startup performance of a public page → [`performance`](../performance/SKILL.md)
- Internal/authenticated screens (no crawler ever sees them) — skip SEO entirely
- React → its own stack

## Crawlability = render mode. Public pages default to static SSR

A crawler reads the **HTTP response body**. Whatever a page needs interactivity/JS to render **is not in that body** on first paint — so an Interactive Server or WASM page whose content loads *after* the circuit/runtime starts is blank to a crawler and to a social unfurl bot (which never runs JS at all).

| Public route type | Render mode | Why |
|---|---|---|
| Marketing / landing / content / docs / blog | **Static SSR** (no `@rendermode`) | Full HTML in the response; fastest first paint; nothing to hydrate |
| Product/listing that needs a little interactivity | Static SSR + **islands** (interactive component *within* a static page) | Content crawlable; only the widget hydrates |
| Public page that's genuinely app-like | Static SSR **prerender** (`prerender: true`, the default) then interactive | Prerender emits crawlable HTML; interactivity takes over client-side |

**Rule:** default every public route to **static SSR**; add interactivity per-island only where a feature needs it, and only with **prerender on** so the first response is still complete HTML. Never make a page's core content depend on a client render mode. (Render-mode selection generally is [`project-scaffold`](../project-scaffold/SKILL.md)'s; this is its public-page corollary.)

## Per-request head metadata

`<HeadOutlet>` (in `App.razor`'s `<head>` from the template) is the sink; `<PageTitle>` and `<HeadContent>` on a page push into it, and — critically — **with static SSR/prerender these are emitted on the server response**, so crawlers and unfurlers see them. Set them per route from real data:

```razor
@page "/products/{Slug}"
<PageTitle>@_p.Name — Acme</PageTitle>       @* tab title convention: ui-conventions *@
<HeadContent>
    <meta name="description" content="@_p.Summary" />
    <link rel="canonical" href="@Canonical($"/products/{Slug}")" />
    @* Open Graph — the social unfurl *@
    <meta property="og:title" content="@_p.Name" />
    <meta property="og:description" content="@_p.Summary" />
    <meta property="og:image" content="@_p.ImageAbsoluteUrl" />
    <meta property="og:type" content="product" />
    <meta property="og:url" content="@Canonical($"/products/{Slug}")" />
    @* Twitter Card *@
    <meta name="twitter:card" content="summary_large_image" />
</HeadContent>
```

- **Description** is per-page and unique — it's what shows under the title in results. No boilerplate-repeated site description on every page.
- **Open Graph + Twitter Card** drive the link preview on social/chat. `og:image` must be an **absolute** URL. Provide `og:title`/`description`/`image`/`url`/`type` at minimum.
- Set these from **route/model data**, not hardcoded — the page knows its own product/article.
- Multiple `<HeadContent>` on one page: fine (they compose into `<HeadOutlet>`); keep tag **keys** (a given `meta name`) unique so you don't emit duplicates.

## Streaming rendering without breaking crawlers

`[StreamRendering]` lets a slow page return its shell immediately then stream the data in on the **same response**. Because the streamed content arrives **in the HTTP response body** (Blazor patches it via `blazor-ssr` markers in the stream, not a post-load `fetch`), a crawler that reads the full response still sees the final content — **as long as the content is server-rendered, not JS-injected**. So:

- **Server-streamed content is crawlable** — the placeholder is replaced within the response.
- **JS/interactive-mode-injected content is not** — if the real content only appears after a WASM/circuit render, the crawler sees the placeholder. That's the anti-pattern: don't hide crawlable content behind a client render.
- Keep the loading placeholder semantically empty (a skeleton), and ensure the final streamed markup carries the real `<h1>`/text/links.

## A truthful 404

A wrong URL must return **HTTP 404**, not a 200 with a "not found" message (a soft-404 — search engines index it and dilute the site).

```razor
@* net10 — Routes.razor *@
<Router AppAssembly="@typeof(Program).Assembly" NotFoundPage="typeof(Pages.NotFound)">
    <Found Context="routeData"> ... </Found>
</Router>
```
- **net10:** set `NotFoundPage` on the `Router`; call **`NavigationManager.NotFound()`** from a page when a *valid route* has no *data* (e.g. `/products/nonexistent`) — it re-executes to the 404 page and returns a real 404 status. The `NotFound` page carries `<PageTitle>Not found</PageTitle>` and a `noindex` meta.
- **net8/9:** the `Router`'s `<NotFound>` fragment renders the page but returns **HTTP 200**. To get a real status code, add **`UseStatusCodePagesWithReExecute("/not-found")`** in the pipeline and let the SSR endpoint set the 404. Tag this as the down-level path.
- 404 (and other error) pages should be `<meta name="robots" content="noindex">`.

## Site-level discovery: canonical, sitemap, robots

- **Canonical** — one `<link rel="canonical">` per page pointing at the preferred absolute URL (dedupes trailing-slash / query / casing variants). Build absolute URLs from a configured base host (never a `localhost` fallback — [`project-scaffold`](../project-scaffold/SKILL.md) config hygiene).
- **`sitemap.xml`** — either a static file (small, stable sites) or a **dynamic SSR endpoint** for data-driven URLs. As a minimal-API endpoint returning `application/xml`:
  ```csharp
  app.MapGet("/sitemap.xml", async (ISlugSource slugs) => {
      var urls = await slugs.PublicUrlsAsync();
      var xml = BuildUrlset(urls);           // <urlset><url><loc>…</loc><lastmod>…</lastmod></url>…
      return Results.Text(xml, "application/xml");
  });
  ```
  Include only canonical, indexable, public URLs; keep `lastmod` honest.
- **`robots.txt`** — a static file in `wwwroot` (served as-is): allow crawling of public areas, `Disallow:` app/auth paths, and point to the sitemap (`Sitemap: https://host/sitemap.xml`). Don't `Disallow: /` in production by accident (a classic launch-day de-indexing).

## Structured data (JSON-LD)

Emit `schema.org` JSON-LD in a `<script type="application/ld+json">` via `<HeadContent>` — it powers rich results (breadcrumbs, article bylines, product price/rating). Serialize from the model; use the right `@type` (`Article`, `Product`, `BreadcrumbList`, `Organization`, `FAQPage`). Because it's emitted server-side on static SSR, crawlers read it directly. Keep it consistent with the visible content (Google penalizes JSON-LD that describes content not on the page).

## Rules

- **Public routes default to static SSR**; interactivity per-island only, always with **prerender on** — never make core content depend on a client render mode.
- **Per-page unique `title` + `meta description`**; set from route/model data.
- **Open Graph + Twitter Card** on shareable pages, `og:image` absolute.
- **One canonical link per page**, absolute, from a configured base host.
- **Streamed content stays server-rendered** (in the response), never JS-injected — else it's invisible to crawlers.
- **Real 404 status**: net10 `NotFoundPage` + `NavigationManager.NotFound()`; net8/9 `UseStatusCodePagesWithReExecute`; error/404 pages `noindex`.
- **Ship `sitemap.xml` (canonical URLs only) + `robots.txt`** (allow public, disallow app/auth, link the sitemap).
- **JSON-LD** for content that earns rich results, consistent with the visible page.

## What NOT to do

- No public page whose content only renders after WASM/circuit start (blank to crawlers + unfurl bots).
- No shared/boilerplate `meta description` repeated across pages; no missing OG tags on shareable pages; no relative `og:image`.
- No content hidden behind a *client* render that a crawler needs (streaming is fine; JS-injection is not).
- No soft-404 (200 with "not found"); no indexable 404/error page.
- No missing/wrong canonical; no `Disallow: /` shipped to production; no `sitemap.xml` listing non-canonical or authed URLs.
- No JSON-LD describing content that isn't on the page.
- **Don't** re-own the `<PageTitle>` tab-title convention (ui-conventions) or its scaffold emission (generator) — only the SEO metadata content.

## Validation

- **View source** (not the rendered DOM) on a public page: the `<h1>`, body text, `title`, `meta description`, canonical, OG tags, and JSON-LD are all present in the **response HTML**.
- Fetch a page with JS disabled (or `curl`) — the core content is there.
- Hit a non-existent URL → **HTTP 404** (check the status, not just the page), and it's `noindex`.
- `sitemap.xml` returns valid XML of canonical public URLs; `robots.txt` allows public paths, disallows app/auth, links the sitemap.
- Run a URL through a rich-results / OG-preview checker → title/description/image/structured-data render correctly.

## Handoffs

- `<PageTitle>` tab-title convention → [`ui-conventions`](../ui-conventions/SKILL.md); its emission in scaffolds → [`generator`](../generator/SKILL.md)
- Render-mode selection across the app → [`project-scaffold`](../project-scaffold/SKILL.md)
- Public-page load performance (WASM startup, prerender cost) → [`performance`](../performance/SKILL.md)
- Configured base-host / no-localhost-fallback for absolute URLs → [`project-scaffold`](../project-scaffold/SKILL.md)
- Automated Lighthouse SEO/score gate in CI → qa `accessibility-testing`/CI peers (Lighthouse covers SEO + a11y + perf categories)
