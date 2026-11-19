# Server-rendered pages — hydration and raw HTML

Read this when the app under test serves HTML from the server (SSG, ISR, SSR, streamed SSR, Blazor prerender). The source of truth is [`backend/_shared/experience-plan/references/rendering-strategy.md`](../../../../../../backend/_shared/experience-plan/references/rendering-strategy.md) (§ Verification); the routes and their modes are the experience plan's `rendering_plan` (§4a of `experience-plan.md`). A browser test passes on the hydrated DOM whether or not the server rendered anything, so server-rendered content is proved on the raw HTML.

## 1. Wait for hydration, never for visibility

A server-rendered element is visible before it is clickable: the click lands before the handler is attached and is lost. The app sets the signal; the page object waits on it:

- `data-hydrated="true"` on `<body>`, set once by one client component in the root layout.
- `data-hydrated="true"` on the island's own root, for an island that hydrates later (a React island inside a streamed `<Suspense>` boundary, any Blazor `@rendermode` island: the component sets it in `OnAfterRenderAsync(firstRender)`, see `blazor.md`).

```csharp
public async Task GoToAsync()
{
    await _page.GotoAsync("/");
    await Expect(_page.Locator("body")).ToHaveAttributeAsync("data-hydrated", "true");
}

public async Task AddToCartAsync()
{
    await Expect(_recommendations).ToHaveAttributeAsync("data-hydrated", "true");
    await _addButton.ClickAsync();
}
```

- The wait lives in `GoToAsync()` or in the intent method that first touches the island; a test never repeats it. It is not the `WaitForAsync()` before an action that `web-ui.md` bans: auto-waiting cannot see this condition.
- Never `WaitForTimeoutAsync`, `NetworkIdle`, or visibility as a proxy.
- The app has no signal: add a `missing-testids.md` row (page, island, `data-hydrated`) for the `fe-*` agent and stop at the request; do not work around it in the test.

## 2. Assert server-rendered content on the raw HTML

For each route the `rendering_plan` marks `ssg`, `isr`, `ssr` or `ssr-streaming`, a test fetches the route's HTML through `PageHtmlClient` and asserts each `server_rendered_content` item and the `cache` value. A test never calls `Page.APIRequest.GetAsync` itself.

```csharp
public sealed class PageHtmlClient(IAPIRequestContext request)
{
    public async Task<PageHtml> GetAsync(string route)
    {
        var response = await request.GetAsync(route);
        var body = await response.TextAsync();
        var markup = Regex.Replace(body, "<script[\\s\\S]*?</script>", string.Empty, RegexOptions.IgnoreCase);
        return new PageHtml(response.Status, response.Headers.GetValueOrDefault("cache-control", string.Empty), markup);
    }
}

[Test]
public async Task Should_ContainProductName_When_ProductPageIsServerRendered()
{
    var html = await _pageHtml.GetAsync("/products/trail-shoe");
    Assert.That(html.Markup, Does.Contain("Trail Shoe"), "raw HTML of /products/trail-shoe");
}

[Test]
public async Task Should_BeSharedCacheable_When_ProductPageIsCdnPublic()
{
    var html = await _pageHtml.GetAsync("/products/trail-shoe");
    Assert.That(html.CacheControl, Does.Match(@"s-maxage=\d+"));
}
```

- `Markup` has the `<script>` blocks removed, so content that exists only in a hydration payload fails.
- `cdn-public` asserts `s-maxage`. Personalised HTML asserts the single directive the plan names, `private` or `no-store`, one test per route.
- Build the client in `[SetUp]` from `Page.APIRequest`. Interactive behaviour stays on `Page` actions.

## 3. Deferred sections and CSR routes

- A deferred (streamed) section: one test mocks its data source with a 5 s delay and one with a `500`, and asserts the fallback shows (`qa/dotnet/skills/network-mocking`; it forbids `Task.Delay` in a handler, so use the delay recipe it gives).
- A `csr` route: open it by deep link, reload, and assert the page object's landing element; a 404 fails both.
