# Evidence capture — Microsoft.Playwright 1.63 (.NET / NUnit)

Every capture API in its .NET spelling, with the version it shipped in. `SKILL.md` decides what to capture
and where it lands; this file is how. The samples derive from
`qa/dotnet/skills/ui-test-author/playwright/assets/BaseTest.cs` (`Example.UiTests.Support.BaseTest : PageTest`),
which owns the browser, the context, the page and the failure evidence. A sample adds its own `[SetUp]` /
`[TearDown]`; NUnit runs a derived `[SetUp]` after `BaseTest.StartTracing` and a derived `[TearDown]` before
`BaseTest.KeepEvidenceOnFailure`, so the page is open in both.

`BaseTest`'s protected helpers name and attach a recording exactly like the failure evidence (plan D42):

| Member | Returns / does |
|---|---|
| `EvidenceName()` | `<Class>.<Test>` with every character outside `[A-Za-z0-9._-]` replaced by `_` |
| `Artifact(name, extension)` | `<WorkDirectory>/playwright-artifacts/<name>.<extension>` |
| `Attach(name, contentType, path)` | `TestContext.AddTestAttachment(path, name)` and `AllureApi.AddAttachment(name, contentType, path)` |

## 1. Screenshots

### 1.1 The API — `Page.ScreenshotAsync`, `Locator.ScreenshotAsync`

`Page.ScreenshotAsync(new PageScreenshotOptions { ... })` returns `byte[]`; `Path` also writes the file and
creates its folder.

| `PageScreenshotOptions` | Values | Note |
|---|---|---|
| `Path` | file path | Format from the extension; relative to the current directory — pass an absolute path |
| `FullPage` | `false` | The whole scrollable page. Page only |
| `Clip` | `new Clip { X, Y, Width, Height }` | Page only |
| `Type` | `ScreenshotType.Png` · `Jpeg` · `Webp` [1.62] | `Quality` (0–100): jpeg default 80; webp default 100 is lossless |
| `Mask` | `IEnumerable<ILocator>` | Covers each match with a box, invisible matches included; `MaskColor = "#00FF00"` [1.35] |
| `Animations` | `ScreenshotAnimations.Allow` · `Disabled` | Disabled fast-forwards finite animations and resets infinite ones |
| `Caret` | `ScreenshotCaret.Hide` · `Initial` | Default `Hide` |
| `Scale` | `ScreenshotScale.Device` · `Css` | `Css` keeps HiDPI images small |
| `Style` | CSS text [1.41] | Applied during capture; pierces shadow DOM and iframes — hides a clock, an avatar, a token. There is no `StylePath` |
| `OmitBackground` | `true` | Transparent background; not for jpeg |
| `Timeout` | ms | |

- `Locator.ScreenshotAsync(new LocatorScreenshotOptions { ... })` takes the same options except `FullPage`
  and `Clip`. It waits for actionability, scrolls the element into view and clips to it; anything covering
  the element shows in the image.
- `IElementHandle.ScreenshotAsync` is discouraged; use the locator form.
- A one-off from the shell: `pwsh bin/Debug/net10.0/playwright.ps1 screenshot --full-page <url> <file>`.

### 1.2 The failure screenshot

`BaseTest.KeepScreenshotAsync` takes `new() { Path = Artifact(name, "png"), FullPage = true }` on failure,
after the trace is saved and before the context closes, and attaches it. There is no catch around it (plan
D31): a crashed page fails the teardown, and the trace is already on disk.

### 1.3 A screenshot at a chosen point

An `Evidence` helper sits beside the page objects and is built in the test class's own `[SetUp]`. The test
calls it; it never calls `Page`.

```csharp
using Allure.Net.Commons;
using Microsoft.Playwright;

namespace Example.UiTests.Support;

public sealed class Evidence(IPage page)
{
    public async Task ScreenshotAsync(string name)
    {
        var png = await page.ScreenshotAsync(new()
        {
            FullPage = true,
            Animations = ScreenshotAnimations.Disabled,
            Caret = ScreenshotCaret.Hide,
            Scale = ScreenshotScale.Css,
        });
        AllureApi.AddAttachment(name, "image/png", png, ".png");
    }
}
```

A test calls `await _evidence.ScreenshotAsync("Cart.BeforeCheckout")`. A screenshot is evidence, not an
assertion: .NET has no screenshot assertion (`ToHaveScreenshotAsync` does not exist), and comparing one to a
baseline is `qa/dotnet/skills/visual-regression`.

## 2. Video

- **Recording** is a context option: `RecordVideoDir` and `RecordVideoSize = new RecordVideoSize { Width =
  1280, Height = 720 }` on `BrowserNewContextOptions`. `BaseTest.ContextOptions()` sets the folder
  (`<WorkDirectory>/playwright-videos`); a class sets only the size, in an override that starts from
  `base.ContextOptions()`. The size defaults to the viewport scaled to fit 800×800.
- **The file is complete only after `Context.CloseAsync()`.** `Page.Video` is `IVideo?`; read it before the
  close, while the page exists.
- The API is **`PathAsync()`**, `SaveAsAsync(path)` and `DeleteAsync()`. playwright.dev's C# sample shows
  `GetPathAsync()`, which does not exist. `PathAsync()` throws against a remote browser (Docker `run-server`,
  a grid); `SaveAsAsync` works there.
- `BaseTest.KeepEvidenceOnFailure` therefore reads `Page.Video`, closes the context, `SaveAsAsync`-es the video
  only on failure and always calls `DeleteAsync()`, so `playwright-videos/` is empty after every test.
- `VideosPath` / `VideoSize` were removed in 1.60. Video in 1.63 is VP8 WebM (VP9 arrives in 1.64). There are
  no video modes in .NET; "keep on failure" is the `SaveAsAsync`-on-failure above. From 1.64: `RecordVideoFps`.

## 3. Screencast — a recording you start and stop [1.59]

`Page.Screencast` records the span you choose and annotates it — the Playwright team's "agentic video
receipt".

| Call | Does |
|---|---|
| `StartAsync(new() { Path, Size = new ScreencastSize { Width, Height }, Quality, OnFrame = frame => … })` | Starts recording; `Path` gets a `.webm` on stop; `OnFrame` streams JPEG frames. Returns `Task<IAsyncDisposable>` |
| `StopAsync()` | Ends the recording and writes the path |
| `ShowActionsAsync(new() { Position = AnnotatePosition.TopRight, Cursor = ScreencastCursor.Pointer, Duration = 500 })` / `HideActionsAsync()` | Annotates each action |
| `ShowChapterAsync(title, new() { Description, Duration = 2000 })` | A centred chapter card over a blurred page |
| `ShowOverlayAsync(html, new() { Duration })` / `ShowOverlaysAsync()` / `HideOverlaysAsync()` | Custom HTML over the page; `ShowOverlayAsync` returns `IAsyncDisposable` |

- `AnnotatePosition` is an enum — `TopLeft`, `Top`, `TopRight`, `BottomLeft`, `Bottom`, `BottomRight`. The
  1.59 release-note samples pass `"top-right"`, which does not compile in C#.
- The recording crosses `[SetUp]` and `[TearDown]`, so the samples call `StopAsync()` instead of an
  `await using` on the returned `IAsyncDisposable`, which would stop it at the end of `[SetUp]`.
- `FontSize` is deprecated from 1.64. From 1.64: `ScreencastStartOptions.Fps`,
  `ScreencastShowActionsOptions.Style`.

Known issues, open or regressed on 2026-10-10:

- **The video is lost if the page closes before `StopAsync()`** (issue #41608). Stop first, always.
- `BaseTest`'s own video and trace already run a screencast on every page. When one is running, its
  configuration wins over the size passed to `StartAsync`; whether the receipt's path is still written beside
  the running video has not been run in this library.
- Tracing clamps the capture size and pads with grey (#42274).
- There is no `SaveAsAsync`; the path is local to the client process even against a remote browser (#42392).

A receipt starts in the class's `[SetUp]` and stops in its `[TearDown]`, which runs before `BaseTest` closes
the context:

```csharp
using Example.UiTests.Pages;
using Example.UiTests.Support;
using Microsoft.Playwright;
using NUnit.Framework;

namespace Example.UiTests.Tests;

public class CheckoutReceiptTests : BaseTest
{
    private string _receipt = null!;
    private CheckoutPage _checkout = null!;

    [SetUp]
    public async Task StartReceipt()
    {
        _receipt = Artifact(EvidenceName(), "receipt.webm");
        Directory.CreateDirectory(Path.GetDirectoryName(_receipt)!);
        await Page.Screencast.StartAsync(new() { Path = _receipt });
        await Page.Screencast.ShowActionsAsync(new() { Position = AnnotatePosition.TopRight });
        _checkout = new CheckoutPage(Page);
    }

    [Test]
    public async Task Should_ConfirmOrder_When_CartHasOneItem()
    {
        await _checkout.OpenAsync();
        await ChapterAsync("Pay");
        await _checkout.PayWithSavedCardAsync();

        await Expect(_checkout.Confirmation, "confirmation after paying").ToHaveTextAsync("Order confirmed");
    }

    [TearDown]
    public async Task KeepReceipt()
    {
        await Page.Screencast.StopAsync();
        Attach("receipt", "video/webm", _receipt);
    }

    private Task ChapterAsync(string title) => Page.Screencast.ShowChapterAsync(title);
}
```

There is no catch (plan D31). A crashed page fails `StopAsync()`; NUnit records the teardown error on that
test and still runs `BaseTest.KeepEvidenceOnFailure`, which keeps the trace. The folder is created first
because no failure may have created it yet. The receipt is kept for a passing and a failing test alike; it
sits beside the failure evidence, so CI uploads it with a failed run's artifacts and Allure carries it on
every run.

## 4. Trace

### 4.1 The failure trace

`BaseTest.StartTracing` starts the trace on every context; `KeepTraceAsync` stops it with a path on failure,
and a pass calls `StopAsync()` with no path, which discards it.

| `TracingStartOptions` | Records | Since |
|---|---|---|
| `Screenshots = true` | Screenshots for the timeline filmstrip | 1.12 |
| `Snapshots = true` | A DOM snapshot and the network on every action | 1.12 |
| `Sources = true` | The test source beside each action | 1.17 |
| `AriaSnapshots = true` | An aria snapshot on every action — the viewer's **Display Aria** mode | 1.63 |
| `ScreenSnapshots = true` | A screenshot on every action | 1.63 |
| `Title` / `Name` | The viewer title (`BaseTest` uses the test's full name) / the intermediate file prefix | 1.17 |
| `Live = true` | An unarchived trace updated in real time | 1.59 |

`BaseTest` sets the first three and `Title`. Adding the 1.63 pair is an edit to `BaseTest.StartTracing`,
never a second tracer; they make the zip larger.

**Raw tracing does not record assertions.** The Node runner's `trace` option records `expect` calls and
`test.step`s; `Context.Tracing` does not. The trace shows the actions up to the failure; the assertion message
is in the NUnit result, the TRX and Allure.

### 4.2 Making a trace readable

- `Locator.Describe("Checkout button")` [1.53] names a locator in traces and reports; the writer requires it
  on every page-object locator whose role and name do not identify it.
- `Tracing.GroupAsync(name)` [1.49] / `GroupEndAsync()` groups actions in the viewer — the .NET stand-in for
  `test.step`. A page-object method wraps its actions so the trace reads as the journey:

```csharp
public async Task CheckOutAsync()
{
    await _page.Context.Tracing.GroupAsync("Check out");
    await _reviewButton.ClickAsync();
    await _payButton.ClickAsync();
    await _page.Context.Tracing.GroupEndAsync();
}
```

- `AllureApi.Step("Check out", async () => …)` names the same span in the report; the two coexist.

### 4.3 Chunks

`Tracing.StartChunkAsync(new() { Title })` / `StopChunkAsync(new() { Path })` [1.15] cut several traces from
one `StartAsync` — for a context that outlives one test, which `BaseTest`'s context per test does not. Inside
`BaseTest` there is nothing to chunk.

## 5. HAR

- **Per test, on purpose** — `Context.Tracing.StartHarAsync(path, options)` [1.60] / `StopHarAsync()`. One HAR
  per tracing at a time; it records alongside `BaseTest`'s trace. The usings are those of §3; the class's
  tests and page objects are left out.

```csharp
public class OrdersNetworkTests : BaseTest
{
    private string _har = null!;

    [SetUp]
    public async Task StartHar()
    {
        _har = Artifact(EvidenceName(), "har");
        Directory.CreateDirectory(Path.GetDirectoryName(_har)!);
        await Context.Tracing.StartHarAsync(_har, new() { Content = HarContentPolicy.Omit, Mode = HarMode.Minimal });
    }

    [TearDown]
    public async Task KeepHar()
    {
        await Context.Tracing.StopHarAsync();
        Attach("network.har", "application/json", _har);
    }
}
```

- **For every test of a class** — `RecordHarPath`, `RecordHarContent`, `RecordHarMode` and
  `RecordHarUrlFilterString` / `RecordHarUrlFilterRegex` in the class's `ContextOptions()` override. The HAR
  is written on `Context.CloseAsync()`, which `BaseTest` calls after the class's `[TearDown]`, so the class
  cannot attach it, and the path is the same for every test of the class. Prefer the per-test form.
- `HarContentPolicy`: `Omit` (no bodies — the PII-safe default), `Embed`, or `Attach` (the default for a
  `.zip` path). `HarMode.Minimal` keeps only what replay needs.
- HAR and traces include WebSocket traffic since 1.61.
- From the shell: `pwsh bin/Debug/net10.0/playwright.ps1 open --save-har=evidence/app.har --save-har-glob="**/api/**" <url>`.
- Replaying or updating a HAR (`RouteFromHARAsync`) is `qa/dotnet/skills/network-mocking`.

## 6. Attachments

| Call | Use |
|---|---|
| `TestContext.AddTestAttachment(path, description)` | NUnit's own: the file goes into the TRX and the IDE's test result. A file path only |
| `AllureApi.AddAttachment(name, type, path)` | A file on disk — every recording above, through `BaseTest.Attach` |
| `AllureApi.AddAttachment(name, type, byte[] content, ".png")` | Bytes with an extension — the `Evidence` helper. Without the extension the download loses its suffix |
| `AllureApi.AddAttachment(path, name)` | A file whose type Allure infers from the extension |
| `AllureApi.AddScreenDiff(expected, actual, diff)` | Three PNG files shown as Allure's image-diff widget — produced by `qa/dotnet/skills/visual-regression` |

- **Three strings is a path.** `AllureApi.AddAttachment("response.json", "application/json", body)` treats
  `body` as a file path and attaches nothing; text goes in as `Encoding.UTF8.GetBytes(body)` with `".json"`.
- The trace type is `application/vnd.allure.playwright-trace`, which Allure opens in the trace viewer.
- Attachments made in a `[TearDown]` belong to that test; where Allure shows them (the test body or its
  teardown section) has not been checked in this library.
- Adapter wiring (`[AllureNUnit]`, `allureConfig.json`), history and publishing are
  `qa/reporting/dotnet/skills/test-reports`.

## 7. No `error-context.md` in .NET

The Node runner writes `error-context.md` (the error plus an AI-mode aria snapshot) on every failure. .NET
does not. The nearest .NET evidence is the screenshot, the trace with `AriaSnapshots = true` read through
`trace snapshot`, or an explicit capture: `AriaSnapshotAsync(new() { Mode = AriaSnapshotMode.Ai })` [1.59] on
a locator, attached as `text/plain` bytes from a helper. Adding it to every failure is a `BaseTest` change.

## 8. Viewing and reading evidence

`playwright.ps1` appears under `bin/<cfg>/net10.0/` after the first build and needs PowerShell 7 (`dotnet tool
install --global PowerShell` when `pwsh` is missing).

| Command | Does |
|---|---|
| `pwsh bin/Debug/net10.0/playwright.ps1 show-trace <zip>` | The trace viewer |
| https://trace.playwright.dev | Loads a trace in the browser without uploading it; `?trace=<url>` opens a hosted one (CORS applies) |
| `npx playwright@1.63.0 trace open <zip>` | Opens a trace for the analysis commands below — the agent route [1.59]. Without Node: `pwsh bin/Debug/net10.0/playwright.ps1 trace open <zip>` (plan D43) |
| `trace errors` · `console` · `requests` · `request <id>` | Errors, page log, network |
| `trace actions [--grep <text>] [--errors-only]` · `action <id>` | The action list and one action's detail |
| `trace snapshot <id> --name before\|after` · `screenshot <id>` | The DOM or the screen at an action |
| `trace attachments` · `attachment <n>` · `close` | Attachments in the trace; close removes the extracted data in `.playwright-cli/trace/` |
| Allure | Opens an attached `application/vnd.allure.playwright-trace` in the trace viewer; the viewer page needs internet access, the trace bytes are not uploaded |

Prefix each analysis command with `npx playwright@1.63.0` or `pwsh bin/Debug/net10.0/playwright.ps1`; the open
trace is remembered in the working directory between calls. `trace install-skill` installs Microsoft's trace
skill for agents; this skill already documents the commands, so it is optional.

## 9. Exploratory capture: Playwright MCP and `playwright-cli`

| Capture | Playwright MCP (`--caps=devtools` for video and trace) | `playwright-cli` |
|---|---|---|
| Screenshot | `mcp__playwright__browser_take_screenshot` `{ filename, fullPage, type: "png", scale: "css" }` — with `filename` no image is returned and the path resolves against the workspace root [MCP 0.0.74] | `screenshot [ref] --filename=<f> --full-page` (`--type png\|jpeg\|webp`, `--hires`) |
| Start video | `mcp__playwright__browser_start_video` `{ filename, size: { width, height }, fps, cursor }` (fps default 25) | `video-start <f.webm> --size=1280x720 --fps=25 --cursor` |
| Stop video | `mcp__playwright__browser_stop_video` | `video-stop` |
| Chapters and action overlays | not granted to the qa agents | `video-chapter <title>`, `video-show-actions`, `video-hide-actions` |
| Start trace | `mcp__playwright__browser_start_tracing` | `tracing-start` |
| Stop trace | `mcp__playwright__browser_stop_tracing` — returns links to the trace files | `tracing-stop` — traces under `.playwright-cli/traces/` |
| Page state as text | `mcp__playwright__browser_snapshot` `{ filename }` | `snapshot --filename=<f>` (snapshots go to `.playwright-cli/page-*.yml`, not into the context) |

- MCP output without an explicit `filename` goes to the server's `--output-dir` (`.playwright-mcp/`);
  videos under its `videos/` folder.
- The CLI is `npm i -g @playwright/cli@latest`. It keeps an in-memory profile by default and closes a
  headless session after an hour.
- Both run their own Playwright on Node, independent of the suite's 1.63 binding. Open their traces with §8.

## 10. Codegen's recorder

`pwsh bin/Debug/net10.0/playwright.ps1 codegen --target csharp-nunit --test-id-attribute data-testid -o Recorded.cs <url>`
records actions into a `PageTest` class. `--save-har`, `--save-storage`, `--device` and `--viewport-size`
also apply. The toolbar has **Pick locator**, **Assert visibility**, **Assert text**, **Assert value** and
**Assert snapshot** (emits `ToMatchAriaSnapshotAsync`). The recording is a draft: every locator is rewritten
against the ladder in `qa/dotnet/skills/ui-test-author/playwright/references/locators.md`, the class derives
from `BaseTest`, and it is never committed.

## 11. Size and CI

- .NET has no blob reporter: each shard uploads its own `UiTests/bin/<cfg>/net10.0/playwright-artifacts/` on
  failure and its own `UiTests/bin/<cfg>/net10.0/allure-results/` on every run; the Allure publish job merges
  the results.
- Never upload `playwright-videos/` — it is empty after a run, and mid-run it holds only the running test's
  raw recording.
- Size levers: `ScreenshotScale.Css` for HiDPI screenshots; `Jpeg` or `Webp` with `Quality < 100` for ad-hoc
  screenshots; a smaller `RecordVideoSize`; `HarContentPolicy.Omit`.
- Upload paths, the NUnit-filter shards and retention: `qa/cicd/dotnet/skills/ci-pipelines` and
  `qa/cicd/ci-conventions`.
