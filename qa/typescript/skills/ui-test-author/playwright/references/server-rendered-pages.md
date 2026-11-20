# Server-rendered pages — hydration and raw HTML

Read this when the app under test serves HTML from the server (SSG, ISR, SSR, streamed SSR). The source of truth is [`product/skills/experience-plan/references/rendering-strategy.md`](../../../../../../product/skills/experience-plan/references/rendering-strategy.md) (§ Verification); the routes and their modes are the experience plan's `rendering_plan` (§4a of `experience-plan.md`). A browser test passes on the hydrated DOM whether or not the server rendered anything, so server-rendered content is proved on the raw HTML.

## 1. Wait for hydration, never for visibility

A server-rendered element is visible before it is clickable: the click lands before the handler is attached and is lost. The app sets the signal; the page object waits on it:

- `data-hydrated="true"` on `<body>`, set once by one client component in the root layout.
- `data-hydrated="true"` on the island's own root, for an island that hydrates later (a React island inside a streamed `<Suspense>` boundary, any Blazor island).

```ts
async goto(): Promise<void> {
  await this.page.goto('/');
  await expect(this.page.locator('body')).toHaveAttribute('data-hydrated', 'true');
}

async addToCart(): Promise<void> {
  await expect(this.recommendations).toHaveAttribute('data-hydrated', 'true');
  await this.addButton.click();
}
```

- The wait lives in `goto()` or in the intent method that first touches the island; a spec never repeats it. It is not the "redundant `waitFor()`" `ui-tests.md` bans: auto-waiting cannot see this condition.
- Never `waitForTimeout`, `networkidle`, or visibility as a proxy.
- The app has no signal: add a `missing-testids.md` row (page, island, `data-hydrated`) for the `fe-*` agent and stop at the request; do not work around it in the test.

## 2. Assert server-rendered content on the raw HTML

For each route the `rendering_plan` marks `ssg`, `isr`, `ssr` or `ssr-streaming`, a test fetches the route's HTML through `PageHtmlClient` and asserts each `server_rendered_content` item and the `cache` value. A spec never calls `request.get` itself.

```ts
export class PageHtmlClient {
  constructor(private readonly request: APIRequestContext) {}

  async get(route: string): Promise<PageHtml> {
    const response = await this.request.get(route);
    const body = await response.text();
    return {
      status: response.status(),
      cacheControl: response.headers()['cache-control'] ?? '',
      markup: body.replace(/<script[\s\S]*?<\/script>/gi, ''),
    };
  }
}

test('Should_ContainProductName_When_ProductPageIsServerRendered', async ({ pageHtml }) => {
  const html = await pageHtml.get('/products/trail-shoe');
  expect(html.markup, 'raw HTML of /products/trail-shoe').toContain('Trail Shoe');
});

test('Should_BeSharedCacheable_When_ProductPageIsCdnPublic', async ({ pageHtml }) => {
  const html = await pageHtml.get('/products/trail-shoe');
  expect(html.cacheControl).toMatch(/s-maxage=\d+/);
});
```

- `markup` has the `<script>` blocks removed, so content that exists only in a hydration payload fails.
- `cdn-public` asserts `s-maxage`. Personalised HTML asserts the single directive the plan names, `private` or `no-store`, one test per route.
- Interactive behaviour stays on `page` actions.

## 3. Deferred sections and CSR routes

- A deferred (streamed) section: one test mocks its data source with a 5 s delay and one with a `500`, and asserts the fallback shows (`qa/typescript/skills/network-mocking`, the `MockApi` fixture).
- A `csr` route: open it by deep link, reload, and assert the page object's landing element; a 404 fails both.
