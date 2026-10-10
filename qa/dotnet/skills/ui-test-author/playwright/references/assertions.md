# Assertions — Microsoft.Playwright 1.63 with NUnit 4

Web-first assertions retry until they pass or the assertion timeout (5 s by default) runs out. They are the
only way a UI test checks page state. Inside a `BaseTest` subclass, `Expect(...)` is an inherited method of
`PlaywrightTest`; anywhere else (a `[SetUpFixture]`, a helper) add
`using static Microsoft.Playwright.Assertions;`. The version in brackets is where an API first shipped.

## 1. The web-first set

**Locator assertions** — `await Expect(locator).<Matcher>Async(...)`:

| Checks | Matcher |
|---|---|
| Presence and visibility | `ToBeVisibleAsync()`, `ToBeHiddenAsync()`, `ToBeAttachedAsync()`, `ToBeInViewportAsync()` |
| State | `ToBeEnabledAsync()`, `ToBeDisabledAsync()`, `ToBeEditableAsync()`, `ToBeCheckedAsync()`, `ToBeFocusedAsync()`, `ToBeEmptyAsync()` |
| Text | `ToHaveTextAsync(string \| Regex \| IEnumerable)` (whole text), `ToContainTextAsync(...)` (substring) |
| Form values | `ToHaveValueAsync("42")`, `ToHaveValuesAsync(new[] { "a", "b" })` for a multi-select |
| Count | `ToHaveCountAsync(3)` |
| Accessibility | `ToHaveAccessibleNameAsync("Sign in")`, `ToHaveAccessibleDescriptionAsync(...)`, `ToHaveAccessibleErrorMessageAsync("Email is required")` [1.50], `ToHaveRoleAsync(AriaRole.Button)` [1.44] |
| Classes | `ToContainClassAsync("selected")` [1.52] matches class names one by one; `ToHaveClassAsync("a b")` matches the whole attribute |
| Attributes and style | `ToHaveAttributeAsync("aria-expanded", "true")`, `ToHaveIdAsync(...)`, `ToHaveCSSAsync("color", "rgb(0, 0, 0)")`, `ToHaveCSSAsync(..., new() { Pseudo = PseudoElement.Before })` [1.60], `ToHaveJSPropertyAsync(...)` |
| Structure | `ToMatchAriaSnapshotAsync(yaml)` |

`ToBeEditableAsync()` throws when the element is not an editable kind of element at all, such as a
`<div>` [1.50]; point it at the input itself.

**Page assertions** — `await Expect(page).<Matcher>Async(...)`, written in a test that holds the page
object's locators, or in the page object's optional `ExpectLoadedAsync()`:

- `ToHaveURLAsync(string)` resolves the string against the context's `BaseURL` and compares the **whole**
  URL; a glob such as `"**/dashboard"` never matches. `ToHaveURLAsync(new Regex("/dashboard$"))` matches part
  of it. Globs belong to `Page.WaitForURLAsync("**/dashboard")`, which waits rather than asserts.
- `ToHaveTitleAsync(...)`.
- `ToMatchAriaSnapshotAsync(yaml)` on the whole page [1.60].

**API response assertions** — `Expect(response).ToBeOKAsync()` exists, but it accepts any 2xx; assert the
exact status instead (§7).

.NET has no screenshot assertion — there is no `ToHaveScreenshotAsync`; `toHaveScreenshot` is the Node test
runner's. Visual comparison is owned by `qa/dotnet/skills/visual-regression`.

## 2. Aria snapshots

`ToMatchAriaSnapshotAsync` compares the accessibility tree against a YAML template: roles, names and
states, without pixels. It is the cheapest structural check of a region.

```csharp
await Expect(_ordersPage.List).ToMatchAriaSnapshotAsync("""
    - list "Orders":
      - listitem: /Order #\d+/
    """);
```

- Locator form since 1.49, page form since 1.60. `/children: equal` makes child matching strict and `/url:`
  checks link targets [1.52]; input `placeholder` is compared [1.56].
- .NET keeps the template in the test as a raw string literal; the TypeScript snapshot files do not exist
  here.
- Get a first template from `await locator.AriaSnapshotAsync()`, or from the recorder's **Assert snapshot**
  button (`lifecycle.md` §9), then trim it to what the test is about.

## 3. One expected condition

Every assertion states one value. Assert `ToHaveTextAsync("Saved")`, never
`ToHaveTextAsync(new Regex("Saved|Success"))`; `ToHaveCountAsync(3)`, never "at least 3"; never
`Is.EqualTo(a).Or.EqualTo(b)`, `Is.AnyOf(...)`, a `||` inside `Assert.That`, `Does.Match("a|b")`, or an
assertion on an `Or()` locator. A regex alternation is the commonest disguise. If two outcomes are
reachable, split them into one `[Test]` each or parameterize with `[TestCase]`. The only exception is an
explicit instruction to accept more than one value, recorded on the assertion with a comment naming who
asked and where.

Prefer the positive matcher: `ToBeHiddenAsync()` over `Not.ToBeVisibleAsync()`, `ToBeDisabledAsync()` over
`Not.ToBeEnabledAsync()`.

## 4. No one-shot reads

A value read once and then compared does not retry, so it races the UI and fails without evidence.

| One-shot read (banned) | Web-first fix |
|---|---|
| `Assert.That(await loc.IsVisibleAsync(), Is.True)` | `await Expect(loc).ToBeVisibleAsync()` |
| `Assert.That(await loc.TextContentAsync(), Is.EqualTo("Saved"))` / `InnerTextAsync()` | `await Expect(loc).ToHaveTextAsync("Saved")` |
| `loc.Text` | Does not exist — `.Text` is Selenium's `IWebElement`. Use `ToHaveTextAsync` |
| `Assert.That(await loc.InputValueAsync(), Is.EqualTo("42"))` | `await Expect(loc).ToHaveValueAsync("42")` |
| `Assert.That(await loc.CountAsync(), Is.EqualTo(3))` | `await Expect(loc).ToHaveCountAsync(3)` |
| `Assert.That(await loc.GetAttributeAsync("aria-expanded"), Is.EqualTo("true"))` | `await Expect(loc).ToHaveAttributeAsync("aria-expanded", "true")` |
| `Assert.That(Page.Url, Is.EqualTo(...))` | `await Expect(Page).ToHaveURLAsync(...)` |
| `Assert.That(await loc.IsCheckedAsync(), Is.True)` | `await Expect(loc).ToBeCheckedAsync()` |

Reading a value is fine when it feeds the next step rather than an assertion (an order number copied from
the confirmation into a search box).

## 5. Timeouts and waiting

- **Per assertion:** every matcher takes its options with `Timeout`, for example
  `await Expect(report).ToBeVisibleAsync(new() { Timeout = 15_000 })`.
- **Default:** `<ExpectTimeout>` in the `.runsettings` (`lifecycle.md` §5). The adapter applies it as a
  process-wide static before every test. Never call `SetDefaultExpectTimeout(...)` per fixture or per test:
  fixtures run in parallel and the last call wins for all of them.
- **A condition fed by an event:** complete a `TaskCompletionSource` from the event and await it with a
  timeout, or use the `RunAndWaitFor…Async` method Playwright has for it (request, response, console
  message, popup, download):

  ```csharp
  var pageError = new TaskCompletionSource<string>();
  Page.PageError += (_, error) => pageError.TrySetResult(error);
  await _checkoutPage.PlaceOrderAsync();
  var error = await pageError.Task.WaitAsync(TimeSpan.FromSeconds(5));
  ```

  Then assert the value with `Assert.That`. `WaitAsync` throws `TimeoutException` when the event never
  comes, which fails the test with that message.
- `Page.WaitForFunctionAsync(...)` and `locator.WaitForFunctionAsync(...)` [1.62] are for page state no
  matcher can see. Never a hand-rolled `while` loop with `Task.Delay`, and never `WaitForTimeoutAsync`;
  raise the matcher's timeout instead.
- `Page.RunAndWaitForResponseAsync(action, predicate)` starts the wait and the action together, so the
  response cannot arrive first; a `WaitForResponseAsync` started after the click races it.
- Playwright .NET documents no soft form of its web-first assertions. Independent checks on one screen are
  separate tests, or one behaviour asserted with several hard assertions.

## 6. Failure messages name the subject

A failure reading `Expected: "Saved" But was: ""` cannot be told apart from a locator that matched the
wrong element. Every assertion names its subject.

| Assertion | How the subject is named |
|---|---|
| `Expect(locator, "message")` [1.60] | The message prefixes the failure: `Expect(_loginPage.Error, $"sign-in error for {user}")`. The same overloads exist for `Expect(page, message)` and `Expect(response, message)` |
| `Expect(locator)` | `Describe("Success banner")` on the locator, so the failure and the trace print the description |
| NUnit on a value | The message argument with the evidence: `Assert.That(created.Status, Is.EqualTo(201), await created.TextAsync())` |

Describe every locator a test asserts on, and add the message where the record or the user matters. Java
has no message parameter and relies on `describe()` alone; TypeScript passes the message to `expect`.

## 7. Expected exceptions and HTTP responses

- **An expected exception from async code is `Assert.ThrowsAsync<T>`**, which awaits the delegate:

  ```csharp
  var error = Assert.ThrowsAsync<InvalidOperationException>(() => _ordersClient.CancelShippedAsync(orderId));
  Assert.That(error!.Message, Does.Contain(orderId));
  ```

  `Assert.Throws<T>(() => SomethingAsync())` is a bug: an `async` method puts its exception inside the
  returned `Task`, which the synchronous delegate discards, so the assertion reports that nothing was
  thrown. An `async () => …` lambda passed to `Assert.Throws` is `async void`, which NUnit rejects. On NUnit
  4, `Assert.ThrowsAsync` blocks and returns the exception; NUnit 5 makes it awaitable, which is one reason
  this library stays on 4.x. Never a `try`/`catch` in a test.
- **Assert the exact status with the body as the message:**
  `Assert.That(created.Status, Is.EqualTo(201), await created.TextAsync())`. Never
  `Assert.That(res.Ok, Is.True)` or `ToBeOKAsync()` — both accept any 2xx and print nothing useful. Seeding
  with `Page.APIRequest` is in `lifecycle.md` §8.
- **`RunAndWaitForResponseAsync` returns `IResponse`.** Match on the URL and method, then assert the status,
  so a `500` fails with evidence instead of timing out. It lives in a page object method:

  ```csharp
  public Task<IResponse> SaveOrderAsync() =>
      _page.RunAndWaitForResponseAsync(
          () => _save.ClickAsync(),
          response => response.Url.EndsWith("/api/orders") && response.Request.Method == "POST");
  ```

  The test then asserts `Assert.That(saved.Status, Is.EqualTo(201), await saved.TextAsync())`.
