# WebMCP — Java (Playwright 1.63, `page.evaluate`)

Playwright Java is pinned at 1.63.0: Maven Central has no 1.64 yet, and `page.webmcp()` arrives with 1.64.
Until then the suite reads and calls tools through `page.evaluate` against `document.modelContext` — the
same `getTools()` / `executeTool()` calls Playwright 1.64 makes internally. Read the SKILL.md traps first.

## 1. The launch flag

[`assets/WebMcpTest.java`](../assets/WebMcpTest.java) extends the writer's `BaseTest` and overrides its
launch hook:

```java
@Override
protected BrowserType.LaunchOptions launchOptions() {
    return new BrowserType.LaunchOptions().setArgs(List.of("--enable-features=WebMCP"));
}
```

`BaseTest` launches one browser per class in `@BeforeClass` and stamps the headless flag after this hook,
so `HEADED=1` still works and no other class gets the flag. The class sits in `com.example.uitests.tests`,
the package the writer's `testng.xml` scans, so it runs with the suite under `parallel="classes"`.

## 2. Chromium 153 and the evaluate route

1.63 bundles Chromium 153, which predates Chrome 155's change: `executeTool` wants the input as a JSON
**string**, and `getTools()` returns `inputSchema` as a string. The asset's scripts handle both, so they
keep working when a later Chromium takes objects. They are Chromium-only, like `BaseTest`; Firefox's
prototype exposes a different entry point.

The writer's rule holds — a test class calls no raw `page` method — so the scripts live in the page object,
[`assets/ProductPage.java`](../assets/ProductPage.java) (package `com.example.uitests.pages`), beside its URL
and its `Cart.Badge` locator. The test class keeps only the assertion-side helpers.

| Member | What it does |
|---|---|
| `ProductPage.settledTools(name, present, timeoutMs)` | `SETTLED_TOOLS_JS` lists this frame's tools (`tool.window === window`), parses string schemas, and resolves once `name` is present (or absent), re-checking on every `toolchange` event, or when the timeout passes. Returns `List<Map<?, ?>>` of `{ name, inputSchema, annotations }` |
| `ProductPage.callTool(name, input, timeoutMs)` | `CALL_TOOL_JS`: `executeTool` with the object input, retried as a JSON string on `Failed to parse input`, raced against the timeout; returns the parsed result |
| `WebMcpTest.registeredTool(name)` | The tool's map, or an `AssertionError` naming the tools that were listed |
| `WebMcpTest.callAddToCart(quantity)` | Waits for the tool to register, then calls it |

Why an event-driven wait: Java has no `expect.poll`, and `page.waitForFunction` does not await an async
predicate — a `Promise` is truthy, so it would return at once. `page.evaluate` itself has no timeout, so
every helper carries `TIMEOUT_MS` into the script.

`page.evaluate` maps a JS object to `Map<String, Object>` and an array to `List<Object>`. The tests assert
with AssertJ through `asInstanceOf(InstanceOfAssertFactories.MAP)`, so a missing or non-object value fails
with its description instead of a `NullPointerException`; the cart badge uses Playwright's web-first
`assertThat(locator)`.

## 3. Annotations on this route

The evaluate route returns the spec's names with their defaults: `readOnlyHint`, `untrustedContentHint`,
`consequentialHint` (all present, `false` unless set) and `debugging`. The asset asserts
`consequentialHint`. From 1.64, `page.webmcp().tools()` returns `readOnly` / `untrustedContent` /
`consequential`, only when true — change the key when the suite moves.

## 4. Errors

An `executeTool` failure reaches Java as a `PlaywrightException` carrying the DOMException name; the
page's own message does not cross, and a throwing `execute` gives only an `OperationError`. Error-path
tests assert an `isError` result (checklist C13). A throw that the test expects is asserted with
`assertThrows(PlaywrightException.class, …)`, never caught.

## 5. Frames

The helpers filter `tool.window === window`, so they report the frame they run in. For a child frame, find
it in `page.frames()` and give that frame's page object the same script through `frame.evaluate(…)`; the
iframe needs `allow="tools"`.

## 6. Running it

- The tests need `BASE_URL` and an app that registers the tools; they belong to group `webmcp`, so a run
  against an environment without WebMCP excludes them with `excludeGroups("webmcp")` in the Gradle
  `useTestNG` block.
- Failure evidence comes from `BaseTest` like any other test: `build/playwright-artifacts/WebMcpTest.<method>.{png,zip,webm}`.
- Observing the page's own agent through the CDP `WebMCP` domain is documented in the TypeScript
  reference; whether the bundled Chromium 153 serves that experimental domain is not established, so no
  Java gate is built on it until 1.64.

## 7. From 1.64

When `com.microsoft.playwright:playwright` 1.64 is on Maven Central (plan 003 §2.5): from 1.64,
`page.webmcp().tools(new WebMCP.ToolsOptions().setTimeout(10_000))` and
`page.webmcp().callTool("add_to_cart", Map.of("sku", "sku-123", "quantity", 2), new WebMCP.CallToolOptions().setTimeout(10_000))`
replace `CALL_TOOL_JS` and the listing half of `SETTLED_TOOLS_JS` inside `ProductPage`; `frame.webmcp()`
covers child frames.
Keep the event-driven wait for registration and removal — Java still has no polling assertion — and move
the annotation assertion to the normalized `consequential` key.
