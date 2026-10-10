# Assertions — Playwright for Java 1.63

Web-first assertions retry until they pass or the assertion timeout (5 s by default) runs out. They are the
only way a UI test checks page state. Import them with
`import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;`. The version in
brackets is where an API first shipped.

## 1. The web-first set

**Locator assertions** — `assertThat(locator).<matcher>(...)`:

| Checks | Matcher |
|---|---|
| Presence and visibility | `isVisible()`, `isHidden()`, `isAttached()`, `isInViewport()` |
| State | `isEnabled()`, `isDisabled()`, `isEditable()`, `isChecked()`, `isFocused()`, `isEmpty()` |
| Text | `hasText(String \| String[])` (whole text), `containsText(...)` (substring) |
| Form values | `hasValue("42")`, `hasValues(new String[] {"a", "b"})` for a multi-select |
| Count | `hasCount(3)` |
| Accessibility | `hasAccessibleName("Sign in")`, `hasAccessibleDescription(...)`, `hasAccessibleErrorMessage("Email is required")` [1.50], `hasRole(AriaRole.BUTTON)` [1.44] |
| Classes | `containsClass("selected")` [1.52] matches class names one by one; `hasClass("a b")` matches the whole attribute |
| Attributes and style | `hasAttribute("aria-expanded", "true")`, `hasId(...)`, `hasCSS("color", "rgb(0, 0, 0)")`, `hasCSS(..., new LocatorAssertions.HasCSSOptions().setPseudo(...))` [1.60], `hasJSProperty(...)` |
| Structure | `matchesAriaSnapshot(yaml)` |

`isEditable()` throws when the element is not an editable kind of element at all, such as a `<div>`
[1.50]; point it at the input itself.

**Page assertions** — `assertThat(page).<matcher>(...)`, written inside a page object method or a test
that holds the page object's locators:

- `hasURL(String)` resolves the string against the context's base URL and compares the **whole** URL;
  `hasURL(Pattern)` matches part of it. There is no predicate form in Java (Node only).
- `hasTitle(...)`.
- `matchesAriaSnapshot(yaml)` on the whole page [1.60].

Java has no screenshot assertion. Visual comparison is owned by `qa/java/skills/visual-regression`.

## 2. Aria snapshots

`matchesAriaSnapshot` compares the accessibility tree against a YAML template: roles, names and states,
without pixels. It is the cheapest structural check of a region.

```java
assertThat(ordersPage.list()).matchesAriaSnapshot("""
        - list "Orders":
          - listitem: /Order #\\d+/
        """);
```

- Locator form since 1.49, page form since 1.60. `/children: equal` makes child matching strict and `/url:`
  checks link targets [1.52]; input `placeholder` is compared [1.56].
- Java keeps the template in the test as a text block; the TypeScript snapshot files do not exist here.
- Get a first template from `locator.ariaSnapshot()`, or from the recorder's **Assert snapshot** button
  (`lifecycle.md` §8), then trim it to what the test is about.

## 3. One expected condition

Every assertion states one value. Assert `hasText("Saved")`, never
`hasText(Pattern.compile("Saved|Success"))`; `hasCount(3)`, never "at least 3"; never `assertTrue(a || b)`,
a Hamcrest `anyOf(...)` / `either(...).or(...)`, or an assertion on an `or()` locator. A regex alternation is
the commonest disguise. If two outcomes are reachable, split them into one `@Test` each or drive them from a
`@DataProvider`. The only exception is an explicit instruction to accept more than one value, recorded on the
assertion with a comment naming who asked and where.

Prefer the positive matcher: `isHidden()` over `not().isVisible()`, `isDisabled()` over `not().isEnabled()`.

## 4. No one-shot reads

A value read once and then compared does not retry, so it races the UI and fails without evidence.

| One-shot read (banned) | Web-first fix |
|---|---|
| `assertTrue(loc.isVisible())` | `assertThat(loc).isVisible()` |
| `assertEquals(loc.textContent(), "Saved")` / `innerText()` | `assertThat(loc).hasText("Saved")` |
| `loc.getText()` | Does not exist — `getText()` is Selenium's `WebElement`. Use `hasText` |
| `assertEquals(loc.inputValue(), "42")` | `assertThat(loc).hasValue("42")` |
| `assertEquals(loc.count(), 3)` | `assertThat(loc).hasCount(3)` |
| `assertEquals(loc.getAttribute("aria-expanded"), "true")` | `assertThat(loc).hasAttribute("aria-expanded", "true")` |
| `assertEquals(page.url(), ...)` | `assertThat(page).hasURL(...)` |
| `assertTrue(loc.isChecked())` | `assertThat(loc).isChecked()` |

Reading a value is fine when it feeds the next step rather than an assertion (an order number copied from
the confirmation into a search box).

## 5. Timeouts and waiting

- **Per assertion:** every matcher has its own options class with `setTimeout`, for example
  `assertThat(report).isVisible(new LocatorAssertions.IsVisibleOptions().setTimeout(15_000))`, or
  `HasTextOptions`, `ContainsClassOptions`, `MatchesAriaSnapshotOptions`. There is no `AssertOptions` class.
- **Default:** `PlaywrightAssertions.setDefaultAssertionTimeout(10_000)` changes it for the whole JVM. It is
  a process-wide static and classes run on parallel threads, so set it once, to one value, before any test
  runs (a `@BeforeSuite`) — never per class or per test.
- **A non-DOM condition:** Java has no `expect.poll` or `toPass`. `page.waitForCondition(supplier, new
  Page.WaitForConditionOptions().setTimeout(10_000))` blocks until a `BooleanSupplier` returns `true` while
  Playwright keeps dispatching events, which is what an event-fed list needs:

  ```java
  List<String> errors = new ArrayList<>();
  page.onPageError(errors::add);
  checkoutPage.placeOrder();
  page.waitForCondition(() -> !errors.isEmpty(), new Page.WaitForConditionOptions().setTimeout(5_000));
  ```

  Then assert the value with AssertJ. Never use it, or a hand-rolled `while` loop with `Thread.sleep`, for
  something a web-first matcher covers — raise that matcher's timeout instead.
- `page.waitForFunction(...)` and `locator.waitForFunction(...)` [1.62] are for page state no matcher can
  see.
- Playwright Java documents no soft form of its web-first assertions. Independent checks on one screen are
  separate tests, or one behaviour asserted with several hard assertions.

## 6. Failure messages name the subject

A failure reading `expected "Saved" but was ""` cannot be told apart from a locator that matched the wrong
element. Every assertion names its subject.

| Assertion | How the subject is named |
|---|---|
| `PlaywrightAssertions.assertThat(locator)` | **There is no message parameter in Java.** `describe("Success banner")` on the locator, so the failure, the trace and the report print the description |
| AssertJ on a value | `.as(...)` with the evidence: `assertThat(response.status()).as(response.text()).isEqualTo(201)` |
| TestNG `Assert` on a value | The message argument: `assertEquals(rows.size(), 3, "order rows for " + customerId)` |

AssertJ (3.27.7) is the house choice for non-locator values: the API status, a parsed field, a count read
from an event list. TypeScript passes the message to `expect`; .NET has `Expect(locator, "message")` [1.60].

## 7. HTTP responses inside UI tests

- **Assert the exact status with the body as evidence:**
  `assertThat(created.status()).as(created.text()).isEqualTo(201)`. Never `assertThat(response).isOK()` —
  it accepts any 2xx and prints nothing useful — and never `assertTrue(response.ok())`.
- **`page.waitForResponse(predicate, action)` returns `Response`, not `APIResponse`.** Start the wait and
  perform the action in one call, so the response cannot arrive first; match on the URL and method, then
  assert the status, so a `500` fails with evidence instead of timing out. It lives in a page object method:

  ```java
  public Response saveOrder() {
      return page.waitForResponse(
              response -> response.url().endsWith("/api/orders") && "POST".equals(response.request().method()),
              save::click);
  }
  ```

  The test then asserts `assertThat(saved.status()).as(saved.text()).isEqualTo(201)`.
- `APIResponse` is what `page.request()` returns; seeding with it is in `lifecycle.md` §7.
