# WebMCP — .NET (Microsoft.Playwright 1.63, `Page.EvaluateAsync`)

Microsoft.Playwright is pinned at 1.63.0: NuGet has no 1.64 yet, and `Page.Webmcp` arrives with 1.64.
Until then the suite reads and calls tools through `Page.EvaluateAsync` against `document.modelContext` —
the same `getTools()` / `executeTool()` calls Playwright 1.64 makes internally. Read the SKILL.md traps
first.

## 1. The launch flag lives in a runsettings, and the suite runs on its own

`PageTest` launches the browser **once per worker** and every later fixture on that worker reuses it,
whatever it overrides (plan 003 D32). A per-class `LaunchOptionsAsync()` override is therefore unreliable,
and the flag goes in a settings file instead:
[`assets/webmcp.runsettings`](../assets/webmcp.runsettings) repeats the writer's `ui.runsettings` keys
(`BrowserName`, `ExpectTimeout`, `TestIdAttribute`, `LaunchOptions/Headless`) and adds:

```xml
<LaunchOptions>
  <Headless>true</Headless>
  <Args>['--enable-features=WebMCP']</Args>
</LaunchOptions>
```

The adapter parses `Args` as a JSON array. Copy the file beside `ui.runsettings`, and
[`assets/WebMcpTests.cs`](../assets/WebMcpTests.cs) and [`assets/ProductPage.cs`](../assets/ProductPage.cs)
into the test project. The fixture is
`[Category("webmcp")]`, which splits the project into two runs:

| Run | Command |
|---|---|
| The WebMCP suite | `dotnet test --settings webmcp.runsettings --filter TestCategory=webmcp` |
| Everything else | `dotnet test --filter TestCategory!=webmcp` |

`--settings` replaces the csproj's `RunSettingsFilePath` for that run only. The main run — locally and in
every CI job — must carry `TestCategory!=webmcp` once the fixture exists; without the flag
`document.modelContext` is undefined and the WebMCP tests fail. The root-namespace `AuthSetup` signs in
before this fixture too, so the WebMCP run needs `E2E_USER` and `E2E_PASSWORD` as well as `BASE_URL`.

## 2. Chromium 153 and the evaluate route

1.63 bundles Chromium 153, which predates Chrome 155's change: `executeTool` wants the input as a JSON
**string**, and `getTools()` returns `inputSchema` as a string. The asset's scripts handle both. They are
Chromium-only, like the runsettings; Firefox's prototype exposes a different entry point.

The writer's rule holds — a test class calls no raw `Page` method — so the scripts live in the page object,
`ProductPage` (namespace `Example.UiTests.Pages`), beside its URL and its `CartBadge` locator. The test
class keeps only the assertion-side helpers.

| Member | What it does |
|---|---|
| `ProductPage.SettledToolsAsync(name, present, timeoutMs)` | `SettledToolsJs` lists this frame's tools (`tool.window === window`), parses string schemas, and resolves once `name` is present (or absent), re-checking on every `toolchange` event, or when the timeout passes. Returns a `JsonElement` array of `{ name, inputSchema, annotations }` |
| `ProductPage.CallToolAsync(name, input, timeoutMs)` | `CallToolJs`: `executeTool` with the object input, retried as a JSON string on `Failed to parse input`, raced against the timeout; returns the parsed result |
| `WebMcpTests.RegisteredToolAsync(name)` | The tool's `JsonElement`, or an `AssertionException` naming the tools that were listed |
| `WebMcpTests.CallAddToCartAsync(quantity)` | Waits for the tool to register, then calls it |

Why an event-driven wait: .NET Playwright has no `expect.poll`, and `WaitForFunctionAsync` does not await
an async predicate — a `Promise` is truthy, so it would return at once. `EvaluateAsync` itself has no
timeout, so every helper carries `TimeoutMs` into the script. The anonymous argument objects keep their
lower-case property names (`name`, `present`, `timeout`), which is what the scripts destructure.

## 3. Annotations on this route

The evaluate route returns the spec's names with their defaults: `readOnlyHint`, `untrustedContentHint`,
`consequentialHint` (all present, `false` unless set) and `debugging`. The asset asserts
`consequentialHint`. From 1.64, `Page.Webmcp.ToolsAsync()` returns `readOnly` / `untrustedContent` /
`consequential`, only when true — change the key when the suite moves.

## 4. Errors

An `executeTool` failure reaches .NET as a `PlaywrightException` carrying the DOMException name; the
page's own message does not cross, and a throwing `execute` gives only an `OperationError`. Error-path
tests assert an `isError` result (checklist C13). A throw that the test expects is asserted with
`Assert.ThrowsAsync<PlaywrightException>(…)`, never caught.

## 5. Frames

The scripts filter `tool.window === window`, so they report the frame they run in. For a child frame, find
it in `Page.Frames` and give that frame's page object the same script through `frame.EvaluateAsync(…)`; the
iframe needs `allow="tools"`.

## 6. Evidence

`BaseTest` keeps the failure evidence like any other test:
`<WorkDirectory>/playwright-artifacts/WebMcpTests.<Test>.{zip,png,webm}`, attached to the TRX and Allure.
Observing the page's own agent through the CDP `WebMCP` domain is documented in the TypeScript reference;
whether the bundled Chromium 153 serves that experimental domain is not established, so no .NET gate is
built on it until 1.64.

## 7. From 1.64

When `Microsoft.Playwright.NUnit` 1.64 is on NuGet (plan 003 §2.5): from 1.64,
`await Page.Webmcp.ToolsAsync(new() { Timeout = 10_000 })` and
`await Page.Webmcp.CallToolAsync("add_to_cart", new Dictionary<string, object> { ["sku"] = "sku-123", ["quantity"] = 2 }, new() { Timeout = 10_000 })`
replace `CallToolJs` and the listing half of `SettledToolsJs` inside `ProductPage`; `Frame.Webmcp` covers
child frames. The
launch flag still lives in `webmcp.runsettings` and the suite keeps its own run. Keep the event-driven wait
for registration and removal, and move the annotation assertion to the normalized `consequential` key.
