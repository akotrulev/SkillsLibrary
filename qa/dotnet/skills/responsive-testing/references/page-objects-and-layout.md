# Page objects and the `Layout` helper — `qa-dotnet:responsive-testing`

The support code the samples in `SKILL.md` call. Page objects expose **variant intent** and the regions a test
measures; `Layout` **measures and returns numbers**. Neither asserts — the test does. All of it sits in the
UI project from `qa/dotnet/skills/ui-test-author/playwright` (namespaces `Example.UiTests.Pages` and
`Example.UiTests.Support`).

## `Breakpoints` — the one place widths live

Mirror the app's own definition (the theme, `$grid-breakpoints`, the Tailwind `screens`, the tokens file).
The constants are `const` so a `[TestFixture(...)]` attribute can take `Breakpoints.Md - 1`.

```csharp
using Microsoft.Playwright;

namespace Example.UiTests.Support;

public static class Breakpoints
{
    public const int Sm = 640;
    public const int Md = 768;
    public const int Lg = 1024;
    public const int Xl = 1280;
    public const int Height = 720;

    public static ViewportSize Viewport(int width) => new() { Width = width, Height = Height };
}
```

## `AppShellPage` — the navigation variants

```csharp
using Microsoft.Playwright;

namespace Example.UiTests.Pages;

public enum NavVariant
{
    Desktop,
    Hamburger,
}

public sealed class AppShellPage
{
    private readonly IPage _page;
    private readonly ILocator _desktopNav;
    private readonly ILocator _hamburgerNav;

    public AppShellPage(IPage page)
    {
        _page = page;
        _desktopNav = page.GetByTestId("Nav.Desktop").Describe("Desktop navigation");
        _hamburgerNav = page.GetByTestId("Nav.Hamburger").Describe("Hamburger menu button");
    }

    public ILocator Nav(NavVariant variant) => variant switch
    {
        NavVariant.Desktop => _desktopNav,
        NavVariant.Hamburger => _hamburgerNav,
        _ => throw new ArgumentOutOfRangeException(nameof(variant), variant, "Unknown navigation variant"),
    };

    public async Task OpenAsync() => await _page.GotoAsync("/");
}
```

`GotoAsync("/")` resolves against `BaseTest`'s `BaseURL`. A test asserts on `Nav(...)`, so both locators carry
`Describe(...)` and a failure names the variant.

## `ProductsPage` — the grid and the regions beside it

```csharp
using Microsoft.Playwright;

namespace Example.UiTests.Pages;

public sealed class ProductsPage
{
    private readonly IPage _page;

    public ProductsPage(IPage page)
    {
        _page = page;
        Cards = page.GetByTestId("ProductGrid.Card").Describe("Product cards");
        Filters = page.GetByTestId("Products.Filters").Describe("Product filters");
        Results = page.GetByTestId("Products.Results").Describe("Product results");
    }

    public ILocator Cards { get; }

    public ILocator Filters { get; }

    public ILocator Results { get; }

    public async Task OpenAsync()
    {
        await _page.GotoAsync("/products");
        await Cards.First.WaitForAsync();
    }
}
```

`OpenAsync()` returns once the first card is visible — the load signal the measurements need. That is the one
place `.First` is right here: any card will do, and the wait is not followed by an action on it.

## `Layout` — measures, never asserts

```csharp
using Microsoft.Playwright;

namespace Example.UiTests.Support;

public sealed class Layout(IPage page)
{
    public const float TolerancePx = 1f;

    public async Task<int> ColumnCountAsync(ILocator cards)
    {
        var boxes = await BoxesAsync(cards);
        var firstRowTop = boxes.Min(box => box.Y);
        return boxes.Count(box => Math.Abs(box.Y - firstRowTop) <= TolerancePx);
    }

    public Task<int> HorizontalOverflowAsync() =>
        page.EvaluateAsync<int>("() => document.documentElement.scrollWidth - document.documentElement.clientWidth");

    public async Task<float> LeftEdgeSpreadAsync(params ILocator[] elements)
    {
        var boxes = await Task.WhenAll(elements.Select(BoxAsync));
        return boxes.Max(box => box.X) - boxes.Min(box => box.X);
    }

    public async Task<float> OverlapDepthAsync(ILocator first, ILocator second)
    {
        var a = await BoxAsync(first);
        var b = await BoxAsync(second);
        var width = Math.Min(a.X + a.Width, b.X + b.Width) - Math.Max(a.X, b.X);
        var height = Math.Min(a.Y + a.Height, b.Y + b.Height) - Math.Max(a.Y, b.Y);
        return Math.Max(0f, Math.Min(width, height));
    }

    public Task ResizeToAsync(int width) => page.SetViewportSizeAsync(width, Breakpoints.Height);

    private static async Task<LocatorBoundingBoxResult> BoxAsync(ILocator element) =>
        await element.BoundingBoxAsync()
        ?? throw new InvalidOperationException($"{element} has no bounding box: it is not visible");

    private static async Task<LocatorBoundingBoxResult[]> BoxesAsync(ILocator elements) =>
        await Task.WhenAll((await elements.AllAsync()).Select(BoxAsync));
}
```

- **Tolerance** is one pixel, for sub-pixel rendering. Never compare an absolute coordinate.
- **`OverlapDepthAsync`** is how far two boxes intrude into each other (`0` when they are apart); the test
  asserts it is at most `TolerancePx`.
- **`ResizeToAsync`** is for live-resize tests only. Every other test gets its width from the fixture's
  `ContextOptions()` and never resizes.
- **A box that does not exist fails loudly**, naming the locator — a hidden element has no bounding box, and a
  `null` must never become a `0` that passes an overlap check.
- **Measure after a web-first wait.** `ProductsPage.OpenAsync()` waits for the first card; after a resize,
  assert the new variant with `Expect(...)` first and measure afterwards.
