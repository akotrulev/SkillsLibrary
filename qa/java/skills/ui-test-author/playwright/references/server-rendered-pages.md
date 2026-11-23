# Server-rendered pages — hydration and raw HTML

Read this when the app under test serves HTML from the server (SSG, ISR, SSR, streamed SSR). The source of truth is [`product/skills/experience-plan/references/rendering-strategy.md`](../../../../../../product/skills/experience-plan/references/rendering-strategy.md) (§ Verification); the routes and their modes are the `rendering_plan` in the feature spec's `### Rendering plan` (under `## Experience`). A browser test passes on the hydrated DOM whether or not the server rendered anything, so server-rendered content is proved on the raw HTML.

## 1. Wait for hydration, never for visibility

A server-rendered element is visible before it is clickable: the click lands before the handler is attached and is lost. The app sets the signal; the page object waits on it:

- `data-hydrated="true"` on `<body>`, set once by one client component in the root layout.
- `data-hydrated="true"` on the island's own root, for an island that hydrates later (a React island inside a streamed `<Suspense>` boundary).

```java
public void goTo() {
    page.navigate("/");
    assertThat(page.locator("body")).hasAttribute("data-hydrated", "true");
}

public void addToCart() {
    assertThat(recommendations).hasAttribute("data-hydrated", "true");
    addButton.click();
}
```

- `assertThat` is `PlaywrightAssertions.assertThat`. The wait lives in `goTo()` or in the intent method that first touches the island; a test never repeats it. It is not a forbidden wait: auto-waiting cannot see this condition.
- Never `waitForTimeout`, `NETWORKIDLE`, or visibility as a proxy.
- The app has no signal: add a `missing-testids.md` row (page, island, `data-hydrated`) for the `fe-*` agent and stop at the request; do not work around it in the test.

## 2. Assert server-rendered content on the raw HTML

For each route the `rendering_plan` marks `ssg`, `isr`, `ssr` or `ssr-streaming`, a test fetches the route's HTML through `PageHtmlClient` and asserts each `server_rendered_content` item and the `cache` value. A test never calls `page.request().get` itself.

```java
public final class PageHtmlClient {
    private final APIRequestContext request;

    public PageHtmlClient(APIRequestContext request) {
        this.request = request;
    }

    public PageHtml get(String route) {
        APIResponse response = request.get(route);
        String markup = response.text().replaceAll("(?is)<script.*?</script>", "");
        return new PageHtml(response.status(), response.headers().getOrDefault("cache-control", ""), markup);
    }
}

@Test
public void shouldContainProductNameWhenProductPageIsServerRendered() {
    PageHtml html = pageHtml.get("/products/trail-shoe");
    assertThat(html.markup()).as("raw HTML of /products/trail-shoe").contains("Trail Shoe");
}

@Test
public void shouldBeSharedCacheableWhenProductPageIsCdnPublic() {
    PageHtml html = pageHtml.get("/products/trail-shoe");
    assertThat(html.cacheControl()).containsPattern("s-maxage=\\d+");
}
```

- `PageHtml` is a record; `markup` has the `<script>` blocks removed, so content that exists only in a hydration payload fails. The `assertThat` in the tests is the suite's AssertJ one.
- `cdn-public` asserts `s-maxage`. Personalised HTML asserts the single directive the plan names, `private` or `no-store`, one test per route.
- Build the client in `@BeforeMethod` from `page.request()`. Interactive behaviour stays on `page` actions.

## 3. Deferred sections and CSR routes

- A deferred (streamed) section: one test mocks its data source with a 5 s delay and one with a `500`, and asserts the fallback shows (`qa/java/skills/network-mocking`).
- A `csr` route: open it by deep link, reload, and assert the page object's landing element; a 404 fails both.
