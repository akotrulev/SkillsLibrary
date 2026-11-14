# Blazor apps — interactivity and the error UI

Read this when the app under test is **Blazor** (a Blazor Web App with Server, WebAssembly or Auto render
modes, or a standalone WebAssembly app). Two Blazor behaviours break ordinary Playwright tests: a page is
visible before it is interactive, and an unhandled component exception does not fail the page — it shows a yellow
bar and leaves the rest of the UI on screen.

## 1. Wait for interactivity on a condition

A Blazor Web App prerenders the page as static HTML, then attaches the interactive runtime (a SignalR circuit, or
the WebAssembly runtime). Between the two, buttons render and accept clicks that **no handler receives**: the click
is lost and the test fails later, far from the cause.

Wait for a condition the app exposes once it is interactive — never for time:

| The app renders | The test waits with |
|---|---|
| Controls disabled until interactive: `disabled="@(!RendererInfo.IsInteractive)"` (.NET 9+) | `await Expect(checkout.SubmitButton).ToBeEnabledAsync();` |
| A marker set after the first interactive render (.NET 8, or any version): the component renders `data-interactive="true"` on its root once `OnAfterRenderAsync(firstRender)` has run in an interactive render mode | `await Expect(Page.GetByTestId("Checkout.Form")).ToHaveAttributeAsync("data-interactive", "true");` |

- Put the wait in the page object's `GoToAsync()` (or its optional `ExpectLoadedAsync()`), so every test that
  opens the page starts on an interactive page and no test repeats it.
- The marker is product code: ask the `fe-blazor` side for it when the app has none, and record the gap in
  `missing-testids.md` meanwhile. Disabling controls until interactive is also the better user experience, so it
  is usually the one to ask for.
- **Never** `WaitForLoadStateAsync(LoadState.NetworkIdle)`: a Server-mode circuit keeps its WebSocket open, and a
  WebAssembly app may still be downloading — network quiet says nothing about handlers being attached.
- **Never** poll the JavaScript runtime (`WaitForFunctionAsync("typeof Blazor !== 'undefined'")` or similar): the
  `Blazor` object exists before components become interactive, and the check couples the test to framework
  internals.

## 2. Assert the error UI is hidden after every journey

The Blazor templates include `<div id="blazor-error-ui">` in the layout, hidden by CSS; the framework shows it
when a component throws an unhandled exception. The page around it keeps rendering, so a journey can "pass"
while the app has crashed underneath.

Assert it is hidden at the end of every test, once, in the Blazor base class's `[TearDown]`, before the context
closes:

```csharp
using Microsoft.Playwright;
using NUnit.Framework;

namespace Example.UiTests.Support;

public abstract class BlazorTest : BaseTest
{
    [TearDown]
    public async Task ExpectNoUnhandledBlazorErrorAsync()
    {
        await Expect(Page.Locator("#blazor-error-ui"), "Blazor showed its unhandled-error UI during the test")
            .ToBeHiddenAsync();
    }
}
```

- NUnit runs a derived class's `[TearDown]` before the base class's, so this runs while the page is still open
  and `BaseTest`'s evidence capture runs after it — a failure here still gets its screenshot, trace and video.
- `#blazor-error-ui` is the template's id and the one place the id selector is right: it is framework markup, not
  a product element with a test id. If the app renamed it, use the app's id.
- A test that **expects** the error UI (a deliberate fault) asserts `ToBeVisibleAsync()` itself and lives in a
  class that does not derive from `BlazorTest`.
- For Server mode, a dropped circuit shows the reconnect UI (`#components-reconnect-modal`; check the id
  in the app's `App.razor` or `ReconnectModal.razor`). A journey that should never lose its circuit can assert that hidden the same way.

## 3. Test ids

`fe-blazor` emits `data-testid` on every interactive element and list container (PascalCase, dot-separated), so
the locator ladder in `locators.md` applies unchanged. A component library that renders its own markup (MudBlazor,
Fluent UI) passes `data-testid` through `UserAttributes` / `AdditionalAttributes`; where it cannot, scope from the
nearest owned test id.
