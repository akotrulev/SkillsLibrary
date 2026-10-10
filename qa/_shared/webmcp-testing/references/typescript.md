# WebMCP — TypeScript (Playwright 1.64, native `page.webmcp`)

Playwright 1.64 (Node, 2026-10-07) ships the WebMCP API on `Page` and `Frame`. It is the only stack in
this library on 1.64, so it is the only one that calls the native API; Java and .NET use `evaluate` until
their 1.64 packages publish. Read the SKILL.md traps first.

## 1. Enable the feature

Playwright refuses to list or call tools unless the browser it launched got the literal
`--enable-features=WebMCP` argument. Two ways to give it:

**Per file** — what [`assets/webmcp.spec.ts`](../assets/webmcp.spec.ts) does. The spec sits beside the
writer's assets, runs in the canonical config's `chromium` project (Desktop Chrome, the signed-in storage
state, `dependencies: ['setup']`), and asks for its own launch arguments at file level:

```ts
test.use({ launchOptions: { args: ['--enable-features=WebMCP'] } });
```

`launchOptions` is a worker option, so Playwright starts a separate worker for this file and no other
file gets the flag. Choose this for one WebMCP spec.

**Per project** — for a suite of WebMCP specs, add a project to `playwright.config.ts` and keep those
specs out of `chromium`:

```ts
projects: [
  { name: 'setup', testMatch: /.*\.setup\.ts/ },
  {
    name: 'chromium',
    testIgnore: /.*webmcp.*\.spec\.ts/,
    use: { ...devices['Desktop Chrome'], storageState: authFile },
    dependencies: ['setup'],
  },
  {
    name: 'webmcp',
    testMatch: /.*webmcp.*\.spec\.ts/,
    use: {
      ...devices['Desktop Chrome'],
      storageState: authFile,
      launchOptions: { args: ['--enable-features=WebMCP'] },
    },
    dependencies: ['setup'],
  },
],
```

Then drop the file-level `test.use` from the specs. A Firefox project needs both prefs instead of the
flag, and covers no iframe tools:

```ts
{
  name: 'firefox-webmcp',
  use: {
    ...devices['Desktop Firefox'],
    launchOptions: {
      firefoxUserPrefs: { 'dom.modelcontext.enabled': true, 'dom.modelcontext.testing.enabled': true },
    },
  },
},
```

WebKit has no WebMCP; Playwright throws `WebMCP is not supported in WebKit.`

## 2. The API

| Call | Returns / throws |
|---|---|
| `page.webmcp.tools({ timeout })` | `{ name, description, inputSchema?, annotations?: { readOnly?, untrustedContent?, consequential? } }[]` — the hints only when true; `debugging` and `title` dropped |
| `page.webmcp.callTool(name, input, { timeout })` | Whatever `execute` resolved to, already JSON-parsed; an `isError: true` result comes back as is. Throws `No WebMCP tool named "x". Available tools: …` for an unknown tool, and `the invocation failed` (Chromium) when `execute` throws |
| `frame.webmcp` | The same for one child frame; a cross-origin frame needs `allow="tools"` |

`page.webmcp` covers the **main frame only**. Under the hood an injected script calls `getTools()` /
`executeTool()` (Firefox: `invokeTool()`), in the utility world in Chromium; it does not use CDP, and it
retries with a JSON-string input on Chromium before 155. Pass `{ timeout }` on every call — the JS default
is 0.

## 3. The tests in the asset

[`assets/ProductPage.ts`](../assets/ProductPage.ts) is the page object: it owns the URL (`goto(sku)`), the
`Cart.Badge` locator and the page's tool surface (`webmcp`), so the spec calls no raw `page.` method.
`assets/webmcp.spec.ts` extends the writer's `test` (from `./fixtures`) with one fixture, `productPage`:
it opens `/products/sku-123`, polls `tools()` until `add_to_cart` is listed, and yields the page object. A
tool that never registers fails the fixture with the poll's message.

The five tests cover checklist items B7 (object schema), D19 (consequential hint), C11 (valid call → UI
reflects it), C12/C13 (bad input → `isError`) and A2 (tool gone after leaving the page). Each test reads a
fresh context, so the cart starts empty. Registration and removal are always polled:

```ts
await expect.poll(() => toolNames(productPage), { timeout, message: 'tools after leaving the product page' })
  .not.toContain(addToCart);
```

A tool that throws instead of returning `isError` is asserted with the runner's rejection matcher:

```ts
await expect(productPage.webmcp.callTool('remove_from_cart', { sku }, { timeout })).rejects.toThrow('the invocation failed');
```

Use it only to pin a known C13 defect: an agent cannot read that message, so the fix is an `isError`
result, and the test then changes to assert it.

## 4. Schema validity (checklist B7)

The browser checks only that `inputSchema` serializes. Validate it against the meta-schema with Ajv (add
`ajv` as a dev dependency). The spec cites JSON Schema without a draft; the declarative explainer links
2020-12, so `Ajv2020` is the default unless the app states another draft. Added to the asset file, beside
its helpers:

```ts
import Ajv2020 from 'ajv/dist/2020';

test('Should_DeclareAValidJsonSchema_When_AddToCartIsRegistered', async ({ productPage }) => {
  const tool = await listedTool(productPage, addToCart);
  const ajv = new Ajv2020({ strict: true });

  expect(ajv.validateSchema(tool?.inputSchema as object), JSON.stringify(ajv.errors)).toBe(true);
});
```

## 5. Read-only truthfulness (checklist D18)

Record requests in a fixture that starts after the page settled, call the read-only tool, and assert that
no request other than `GET` was sent; then confirm the backend state through the API client the suite
already has. Keep the recording in the fixture — the test only reads the list.

## 6. Observing calls the page's own agent makes (Chromium, optional)

`page.webmcp` sees only calls Playwright makes. The experimental CDP `WebMCP` domain also reports calls
the page's in-page agent or the browser's agent make:

```ts
const cdp = await page.context().newCDPSession(page);
cdp.on('WebMCP.toolInvoked', event => invoked.push(event));
cdp.on('WebMCP.toolResponded', event => responded.push(event));
await cdp.send('WebMCP.enable');
```

`WebMCP.enable` emits `toolsAdded` for the tools already registered; `toolResponded` carries
`{ invocationId, status: Completed | Canceled | Error, output?, errorText? }`. The domain is
experimental: wrap it in a fixture, and expect to cast if the bundled protocol typings lag it.

## 7. Registration timing (checklist A4)

To measure time-to-first-tool or churn, wrap `ModelContext.prototype.registerTool` in `page.addInitScript`
so every registration is logged with `performance.now()` before page scripts run, then read the log with
`page.evaluate` from a fixture. Wrapping `execute` the same way records the calls.

## 8. Third-party helper

`@swissspidy/playwright-webmcp` (0.2.0, 2026-10-09) adds matchers such as `toHaveTool` and
`toMatchToolContract`, a recorder and a lint. It is new and unproven: evaluate it before adopting it, and
keep the native API as the baseline.
