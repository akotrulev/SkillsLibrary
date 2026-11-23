# Rendering strategy — SSR, CSR and hybrid, decided per route

**Rendering is decided per route, never per app.** The planner classifies every web route as SSG, ISR, SSR, streaming SSR or CSR, records the signals behind the choice, and writes it into the feature spec's `### Rendering plan` (under `## Experience`) before any code exists. The `fe-<stack>` agent builds to that spec and may not change a route's `mode` on its own; the `qa-ui-<stack>` agent proves it from the raw HTML.

Web UIs only. Native mobile and desktop apps are client-rendered by nature and skip this file.

**Default when signals conflict:** render the first view on the server, add client interactivity as islands, and move a route to full CSR only when it sits behind a login **and** is used as a working tool for long sessions.

## Terms

| Term | HTML built where | When | First view | Interactivity |
|---|---|---|---|---|
| CSR | Browser | after the JS bundle downloads and runs | empty shell or skeleton | the whole app once loaded |
| SSR | Server | per request | complete HTML | after hydration |
| SSG | Build | at build time | complete HTML from the CDN | after hydration |
| ISR | Server | at build, then regenerated on a timer or on demand | complete HTML from the CDN | after hydration |
| Streaming SSR | Server | per request, in chunks as data arrives | shell first, sections fill in | per section |

- **Hydration** — the browser re-runs component code over server HTML to attach handlers. Until it finishes the page looks ready but clicks do nothing.
- **Island** — an interactive component that ships its own JS and hydrates alone; the rest of the page ships none.
- **Server component** — runs only on the server and ships no JS (React Server Components; Blazor static SSR).
- **Progressive enhancement** — the page works as plain HTML (links, forms); JS adds behaviour on top.

## Decision procedure — per route

Ask in order; the first match decides the base mode, then the island rule adds interactivity.

1. **Same content for every visitor, changes rarely (days or more)?** → `ssg`. Marketing, docs, blog, legal.
2. **Public, must be found by search or link previews, changes often or per request?** → `ssr`, CDN-cached when the response is not personalised. Changes on a known cadence (catalogue, hourly prices) → `isr`.
3. **Public SSR, but a section depends on slow or personalised data** (reviews, recommendations, stock, greeting)? → `ssr-streaming`: shell and fast sections first; the slow ones streamed or client-fetched.
4. **Behind login and used as a working tool for long sessions** (dashboard, admin, data grid, editor, designer)? → `csr` from a static shell; server-render only the shell when first paint matters.
5. **Must work offline or inside a native wrapper?** → `csr` (PWA).
6. **Island rule, after 1–3:** every interactive component on an SSG/ISR/SSR page is an island with its own JS; everything else ships none.

A signed-in page that is **not** a long-session tool (account, my bookings, a detail page) matches none of 1–5 and takes the default: `ssr` with `cache: private`.

| Signal | Question | Pushes toward |
|---|---|---|
| Discoverability | Must search engines, AI agents or link unfurlers read it? | SSR / SSG |
| Audience | Anonymous or signed-in? | anonymous → SSR; signed-in → CSR allowed |
| Freshness | How old may the HTML be: never, minutes, days? | never → SSR; minutes → ISR; days → SSG |
| Personalisation | Does the HTML differ per user? | SSR uncached, or SSR shell + client fetch |
| Interactivity | Forms and buttons, or drag, canvas, live state? | heavy → CSR or a large island |
| Session length | Seconds (bounce risk) or hours (tool)? | seconds → SSR; hours → CSR |
| Device and network | Low-end phones, mobile data? | SSR, minimal JS |
| Offline | Must it work with no network? | CSR |
| Secrets and rules | Pricing, permissions or keys involved in rendering? | SSR (kept on the server) |

## Hybrid patterns — pick the simplest that covers the routes

| Pattern | Boundary | Use when | Cost |
|---|---|---|---|
| Route split | URL prefix: `/p/*` SSR, `/app/*` or `/create/*` CSR | a public site plus a signed-in tool | two build targets or two route groups; shared header and auth work in both |
| Islands / server components | component: server by default, interactive leaves marked | content or data pages with a few widgets | island props must be serialisable; no shared client state without a store |
| Streaming sections | section: shell flushes first, slow sections stream in | one or two slow data sources | no redirect or status change after the first byte; every section needs a fallback |
| SSR shell + client fetch | data: layout server-rendered, personal data fetched in the browser | a cached public page with a per-user strip | layout shift unless space is reserved; that data is invisible to crawlers |

Micro-frontends (separately deployed widgets composed into one page) answer a multi-team problem, not a rendering one; this library does not plan them.

Rules for drawing the boundary:

- Anything a crawler or AI agent must read — title, price, description, structured data — is on the server side.
- Anything that changes per keystroke, drag or frame is on the client side.
- Hand-off between modes is a normal navigation with the state in the URL or an API, never shared memory (product SKU and options as query parameters into the editor).
- Space is reserved for anything filled after first paint.

The large stores all do this: eBay streams SSR with partial hydration ([async fragments](https://innovation.ebayinc.com/stories/async-fragments-rediscovering-progressive-html-rendering-with-marko/)), Amazon server-renders product pages and loads each widget's JS after above-the-fold content, Shutterfly server-renders product pages (Next.js RSC) and runs its editor at `/create/*` as a separate client app. Copy the shape: route split where browsing ends and creating begins, price and structured data server-rendered, slow sections streamed, JS per widget rather than one bundle.

## Stack mapping — name the stack's own mechanism

| Mode | Next.js App Router | Vite SPA | Blazor Web App (.NET 8+) |
|---|---|---|---|
| `ssg` | Server Component, static (default); `generateStaticParams` for dynamic segments | pre-render plugin only | no built-in SSG — static SSR + output caching stands in |
| `isr` | `export const revalidate = <s>`, or tag revalidation | n/a | static SSR + `@attribute [OutputCache(Duration = <s>)]`, `app.UseOutputCache()` |
| `ssr` | request APIs (`cookies()`, `headers()`, `searchParams`) or `dynamic = 'force-dynamic'` | not built in | static SSR (the default render mode) |
| `ssr-streaming` | `<Suspense>` boundary or `loading.tsx` around the slow section | n/a | `@attribute [StreamRendering]` (net9+; `[StreamRendering(true)]` on net8) |
| `csr` | a `'use client'` route with client-only data, behind its own route group | the default | `InteractiveWebAssembly` with `prerender: false` |
| island | a `'use client'` leaf inside a server route | n/a | per-component `@rendermode InteractiveServer` / `InteractiveWebAssembly` / `InteractiveAuto` |

A Vite SPA is the right stack only when **every** route classifies `csr`. One public SSR route in the set means Next.js (or Blazor) with a route split, not two apps.

**Blazor:** `InteractiveServer` holds a SignalR circuit per user, so it suits internal tools with modest concurrency; public traffic takes `InteractiveWebAssembly` or `InteractiveAuto`.

## Output contract — the spec's `### Rendering plan`

One block per route, in this shape. The implementer may not change `mode`; a disagreement is a dated `D<n>` the planner rules on.

```yaml
rendering_plan:
  stack: nextjs-app-router        # nextjs-app-router | vite-spa | blazor
  routes:
    - path: /p/[slug]
      screen: S2                   # the screen id in `## Experience`
      mode: ssr                    # ssg | isr | ssr | ssr-streaming | csr
      revalidate_seconds: null     # isr only
      cache: cdn-public            # cdn-public | private | none
      signals:
        discoverability: required  # required | not-needed
        audience: anonymous        # anonymous | signed-in
        freshness: minutes         # never | minutes | days
        personalisation: none      # none | section | page
        interactivity: light       # none | light | heavy
      server_rendered_content:     # must be in the raw HTML
        - title
        - price
        - json-ld Product
      islands:
        - name: AddToCart
          hydrate: on-load         # on-load | on-visible | on-idle | on-interaction (React); Blazor: render_mode instead
      deferred_sections:           # streamed or client-fetched, each with a fallback
        - name: Reviews
          strategy: stream         # stream | client-fetch
          fallback: skeleton, 320px reserved
      handoff:                     # leaving this mode
        - to: /create/[sku]
          state: query-params      # sku, options, quantity
    - path: /create/[sku]
      screen: S5
      mode: csr
      cache: private
      shell: static
      offline: false
  acceptance:
    - raw HTML of every ssg/isr/ssr route contains its server_rendered_content
    - JS shipped on /p/[slug] under 150 KB gzipped
    - LCP under 2.5 s on mid-range mobile over 4G; CLS under 0.1
```

Required: `path`, `screen`, `mode`, `cache`, `signals`, and `server_rendered_content` on every non-`csr` route. The JS and LCP figures are starting targets; the planner sets the project's own. In an existing app, routes read out of the code are marked `#observed` and a mode the procedure would change becomes an open question, never a silent rewrite.

## Verification — who proves what

Server-rendered assertions read the **raw HTML**, not the hydrated page: a browser test passes either way.

**Acceptance tests — the `Q` task (`qa-ui-<stack>`), red before the screens exist:**

- Every `ssg`/`isr`/`ssr` route: the raw response body (fetched through a page-HTML client, never `request.get` inline in a spec) contains each `server_rendered_content` item in the HTML, not only inside a script payload.
- Every route: response headers match `cache` (`Cache-Control` with `s-maxage` on `cdn-public`; `private` or `no-store` on personalised HTML, never shared-cacheable).
- Every deferred section: shows its fallback when its source is delayed 5 s and when it returns 500 (network-mocked), with no layout shift.
- Every `csr` route: a deep link and a refresh land on the route, not a 404.
- Interaction on a server-rendered page waits for the hydration signal before acting (below), never for visibility: SSR elements are visible before they are clickable.

**Build gate — the `fe` task, beside the acceptance tests it turns green:**

- No hydration-mismatch warning in the console on any server-rendered route.
- With JavaScript disabled, every `ssg`/`isr`/`ssr` route shows its main content and working links.
- The bundle report shows JS only for the listed islands; `acceptance` budgets (JS bytes, LCP, CLS) met.
- A `csr` route is served as a static shell with no server render.

**The hydration signal is the app's job, on every route** (a `csr` route sets it too, once its shell is interactive, so page objects wait the same way everywhere). React: one client component in the root layout sets `data-hydrated="true"` on `<body>` in an effect; an island inside a streamed `<Suspense>` boundary hydrates later and sets `data-hydrated` on its own root. Blazor: every interactive island sets `data-hydrated` on its own root in `OnAfterRenderAsync(firstRender)`, which runs only once the component is interactive. A page object waits on that attribute; no sleeps.

## Anti-patterns — the planner rejects a plan showing one

| Anti-pattern | Why it hurts | Fix |
|---|---|---|
| One mode for the whole app | public pages lose SEO (all CSR) or tools pay a server render per click (all SSR) | classify per route |
| Public product data fetched in the browser | crawlers and AI agents see an empty page | move it into `server_rendered_content` |
| SSR page that hydrates the whole tree | ships an SPA's JS plus the server cost | islands; mark only the interactive leaves |
| Personalised HTML cached at the CDN | one user's data served to another | `cache: private`, or SSR shell + client fetch for the personal strip |
| Page blocked on its slowest API | time to first byte equals the slowest call | stream that section with a fallback |
| Redirect or status decided after streaming starts | headers already sent; wrong status reaches the browser | decide auth, redirects and 404 before the first flush |
| Browser-only APIs (`window`, `localStorage`) in server code | crash or hydration mismatch | move them to a client component or an effect |
| Editor or designer built as SSR | a server round trip per interaction; state duplicated | route split: a CSR app behind its own prefix |
| Unreserved space for late content | layout shift, misclicks, poor CLS | fixed-size placeholders |
| Tests that pass on the hydrated DOM only | SSR regressions go unnoticed | raw-HTML assertions |

Source: *Rendering Strategy Guide: SSR, CSR & Hybrid* (2026-11-19).
