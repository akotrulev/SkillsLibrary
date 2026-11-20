---
name: performance
description: Use when a Windows app starts slowly, janks, leaks or ships big (x:Bind, virtualization, handler leaks, Native AOT, trimming, WPR). Triggers "it is slow". Not for crash triage (error-handling).
disable-model-invocation: true
---

# Windows — Performance

How a Windows app stays fast: **the window shows before the work finishes, the UI thread never waits, lists virtualize, bindings are compiled, handlers do not outlive their page, and the cost is measured with a trace rather than guessed.** Audit rows: section N of `desktop-windows:standards-audit`. Design facts: `design/ui-ux-pro-max --stack winui`.

## Version lane

| Concern | Primary | Note |
|---|---|---|
| Binding | `x:Bind` (compiled; default mode `OneTime`) | `{Binding}` is reflection: slower and breaks under Native AOT and trimming |
| XAML load | `x:Load`, `x:Phase`, `ListView` / `ItemsRepeater` virtualization | `x:Phase` in item templates stages realization |
| Native AOT | `PublishAot` supported for WinUI; **`x:Bind` only** (§4.2) | A library or a `{Binding}` that needs reflection is the blocker |
| Trimming | `PublishTrimmed`; the ILLink warnings are the work list | `[DynamicallyAccessedMembers]` on what reflection reaches |
| XAML optimisations | WinAppSDK 2.3.1 added opt-in XAML optimisations (`XamlChangeIds`); 2.5.4-exp fixed resource-tracking memory growth | Read the release notes of the version in use before adopting an opt-in |
| Profilers | **WPR / WPA** (ETW), **PerfView**, Visual Studio Performance Profiler, `dotnet-counters`, `dotnet-trace`, `dotnet-gcdump` | All free; start with the one already in the project's docs |
| `[WPF]` | Virtualization (`VirtualizingStackPanel`), `Freeze()` on brushes, `{Binding}` is the norm | Not AOT-capable |
| `[WinForms]` | `SuspendLayout` / `ResumeLayout`, `DoubleBuffered`, virtual-mode grids | |
| `[C++]` | Hop to the background once, back once per result (audit N1) | `desktop-windows:cpp-winrt` |

Never up-level a TFM or Windows App SDK to gain speed as a side effect; say what the new version fixes and ask.

## When to use

- Slow start, a janky scroll, a growing working set, a large package, a slow list
- "Should this be `x:Bind`?", "can we publish AOT?", "where is the time going?"

## When NOT to use

- Crashes and fail-fast → `desktop-windows:error-handling`
- Network timeouts and retry → `desktop-windows:networking`
- Local database design → `desktop-windows:offline-and-storage`

---

## Measure first

Every change in this skill starts with a number and ends with one.

| Question | Tool | What to read |
|---|---|---|
| Where did startup go? | **WPR** with the `GeneralProfile` (`wpr -start GeneralProfile`, run, `wpr -stop trace.etl`), open in **WPA** | CPU sampled by stack from process start to first frame; disk and file I/O during start |
| .NET CPU and allocations | **PerfView** (Collect → Run), or `dotnet-trace collect` | `Events View`, GC stats, hot call tree |
| UI thread stalls | The Visual Studio Performance Profiler *UI analysis* / WPA *UI delays*; Windows Performance Analyzer's *Responsiveness* graphs | Frames over 16 ms; one handler holding the thread |
| Memory growth | `dotnet-counters monitor` (GC heap, gen2 count), a `dotnet-gcdump` before and after, a Visual Studio heap snapshot diff | Page or view-model types that survive navigation |
| Binding cost | **XAML Binding Failures** and **Live Visual Tree** in Visual Studio; a trace of `Microsoft-Windows-XAML` | Reflection bindings; layout passes per frame |

Rules for a measurement: a **Release** build on the target hardware class (not a dev machine only), cold start and warm start measured separately, three runs, the median recorded in the report. Never "feels faster".

## Startup

The goal: the first frame is up quickly and the rest arrives behind it.

1. **`App` and the first `Window` constructors do no I/O.** No database open, no settings migration, no network call, no large file read before the window shows.
2. **Show the window, then load.** The page's `Loaded` handler starts the load asynchronously and the page shows its loading state (`desktop-windows:error-handling`).
3. **Defer what is not on the first screen:** `x:Load="False"` on panels, tabs and flyouts content; services resolved lazily (`Lazy<T>` / `IServiceProvider` at the point of use, not a locator in a view model); a second window created on demand.
4. **Start the long pole first, off the UI thread:** open the local database and warm the HTTP client on a background task started in `OnLaunched`, awaited at the first use.
5. **One DI container build, no reflection scanning** (`AddAssembly...` over every type); register explicitly (`desktop-windows:architecture`).
6. A splash is a loading state, not a delay: no artificial wait, and it is removed on first meaningful content.
7. `ReadyToRun` (`PublishReadyToRun`) trades size for faster JIT-free start on a self-contained app; measure before turning it on.

`[packaged]` `Application` activation also costs: keep the manifest's extensions to what is used.

## UI thread

- **Nothing blocks it:** no disk, network, database or heavy compute (§5). `await` the work; results return through `DispatcherQueue.TryEnqueue`, **batched**: one enqueue for a hundred rows, never a hundred.
- **Never `.Result` / `.Wait()` / `.GetAwaiter().GetResult()`** in production code. A blocked UI thread plus a continuation that needs it is a deadlock.
- A long loop over data stays off-thread and reports one result; a loop that must touch UI yields (`await Task.Yield()` is not a fix: chunk it and enqueue per chunk, or virtualize).
- `async void` only for an event handler with a whole-body `try`/`catch` (`desktop-windows:basics`).
- `DispatcherTimer` for UI ticks only; a timer under 100 ms that updates bindings is a finding.
- Cancel work a page started when the page unloads (`CancellationTokenSource` cancelled in `Unloaded`).

## Bindings

| Use | Rule |
|---|---|
| `x:Bind` | The default; set the mode explicitly where the value changes: `Mode=OneWay`, `TwoWay` for inputs |
| `x:Bind` in a `DataTemplate` | Needs `x:DataType`; add `x:Phase` for rows with expensive parts |
| `{Binding}` | Only where `x:Bind` cannot reach (a dynamic `DataContext`); it is not AOT-safe and is a finding elsewhere |
| `OneTime` | Static labels, ids, anything that never changes |
| Converters | `x:Bind` function binding (`{x:Bind local:Fmt.Money(ViewModel.Total)}`) over `IValueConverter` for simple formatting |

- Raise `PropertyChanged` only when the value changed (the toolkit's `[ObservableProperty]` does).
- A collection that changes by hundreds of items replaces the collection or uses a batching list; hundreds of `Add` calls each raise a change.
- Do not bind a property that recomputes a heavy value on every read; compute once into a field.

## Lists and virtualization

- `ListView`, `GridView` and `ItemsRepeater` virtualize; **a `StackPanel` or `ItemsControl` inside a `ScrollViewer` does not**, and is a finding past about 20 items.
- **Never put a virtualizing list inside a vertical `ScrollViewer`** or an `Auto`-height row: it measures every item and loses virtualization. Give it a bounded height (a `*` row).
- Fixed-height rows (`ItemsRepeater` with `StackLayout` and a known item size) measure faster; avoid per-item `Height="Auto"` with large text where a layout can be constant.
- **Paging:** `ISupportIncrementalLoading` or `IncrementalLoadingCollection` from the toolkit; the page size is a number the project chose.
- A template is light: no nested virtualizing lists, no `Image` without `DecodePixelWidth` / `DecodePixelHeight` for thumbnails, no per-row `ThemeShadow`.
- `x:Phase` stages heavy row parts so first paint is cheap.
- A grid of thousands of cells, a chart, a canvas: draw with a render surface (`Win2D`, `SwapChainPanel`), not thousands of elements; the experimental `Chart` / `TableView` never ship (§4.2).

## Images

`BitmapImage.DecodePixelWidth` to the display size; load from a stream on a background task; keep a `BitmapImage` per URI in a small LRU; `ImageCache` is not built in. Large collages animate on the compositor (`Visual` animations), not through layout.

## Memory and leaks

The usual leaks in a desktop app are not the GC's fault: something strong still points at a dead page.

| Leak | Fix |
|---|---|
| A **static** event, a singleton service's event, or an `IMessenger` strong subscription held by a page | Unsubscribe in `Unloaded`; use `WeakReferenceMessenger` (the toolkit default) and `IRecipient<T>` |
| A lambda handler (`button.Click += (s, e) => ...`) on a longer-lived source | Named handler removed on `Unloaded`, or the page owns the source |
| `x:Bind` event bindings to a view model that outlives the view | Fine: the page owns them; check `Bindings.StopTracking()` in `Unloaded` for pages cached by `NavigationCacheMode` |
| `NavigationCacheMode.Required` on every page | Cache only pages whose state is worth keeping |
| A `Task` or `CancellationTokenSource` never cancelled | Cancel in `Unloaded`; dispose the source |
| `WebView2` not closed | `Close()` the control when the page goes; one environment per profile |
| `BitmapImage` / `SoftwareBitmap` / streams held after use | `using` / dispose; set `Source = null` on unload for big images |
| Native handles and COM objects (`[C++]` and interop) | `SafeHandle`; `com_ptr`; revoke event tokens (`desktop-windows:interop`, `:cpp-winrt`) |

Confirm with a heap diff: navigate to a page ten times and back; the page type count must not grow. WinAppSDK versions that leak XAML resource-tracking memory or orphan native objects in .NET apps are fixed in later builds (2.5.4-exp notes): keep the app on the current 2.6.x stable patch before chasing a leak you cannot find in your own code.

## Native AOT and trimming

| Step | Command and check |
|---|---|
| Preconditions | `x:Bind` everywhere (no `{Binding}`), no reflection-based serializer without a source generator (`System.Text.Json` with a `JsonSerializerContext`), no `Assembly.Load` |
| Turn on | `<PublishAot>true</PublishAot>` in the app project; publish with `dotnet publish -c Release -r win-x64` (and `win-arm64`) |
| Read | Every `IL2xxx` / `IL3xxx` warning is a defect: fix, annotate, or remove the dependency; never suppress without a recorded reason |
| Verify | Run the published binary through the primary scenarios; AOT surfaces failures at run time that a build does not |
| `[packaged]` | MSIX of an AOT build; check the start-up gain with WPR before and after |

Native AOT is a decision, not a default: it removes JIT start-up cost and reduces size, and it fences reflection, `dynamic` and some libraries. Where it is not adopted, `PublishTrimmed` with the warnings read is the middle path and `PublishReadyToRun` the cheap one. Never turn either on for a WPF or WinForms app without checking the designer-generated code and third-party controls.

## Disk, network, power

- Settings and small state: write on change, debounced, not per keystroke. Database writes in batches inside a transaction.
- One `HttpClient` through `IHttpClientFactory`; HTTP/2 where the server offers it; no polling faster than the data changes (`desktop-windows:networking`).
- **A background app is quiet:** when the window is minimized or the machine is on battery saver, stop animations and polling (`Window.VisibilityChanged`, `PowerManager.EnergySaverStatusChanged`); wake and revalidate on return.
- Do not keep a timer, a `FileSystemWatcher` or a socket alive for a window that closed.

## Size and install

- **Framework-dependent** packaged MSIX is the default and keeps the download small; self-contained and AOT trade size for independence (§4.2).
- Trim unused assets and languages; one asset per scale only as needed.
- Do not ship debug symbols in the package; keep them for crash triage (`desktop-windows:error-handling`).

## Telemetry

A startup span (`app.start`) from process start to first content, with `cold` / `warm`; a metric `app.start.duration` histogram; a metric for list load time per screen. Names only, never data. The span and the histogram are what the plan's telemetry smoke looks for (`desktop-shared:observability`).

## Rules

1. Measure before and after, in Release, on target hardware; report the median.
2. The UI thread does no I/O or heavy work; results return batched.
3. `x:Bind` is the default; `{Binding}` is a recorded exception.
4. Lists virtualize and have a bounded height; templates are light.
5. Every handler, timer, messenger subscription and token is released when its page unloads.
6. Nothing costly before the first frame.
7. AOT and trimming are decisions with their warnings read, never switched on blindly.

## Generation steps

1. Detect lane, TFM and whether AOT or trimming is on; start with a cold-start and a navigation trace.
2. Remove I/O from `App` and the first page; add the loading state.
3. Convert `{Binding}` to `x:Bind`; add `x:DataType`, `x:Phase`, `x:Load` where measured.
4. Fix lists: virtualized, bounded, incremental.
5. Walk the leak table with a heap diff.
6. Decide AOT with the warnings in hand; measure again; record the numbers.

## Validation

- `rg -n "\{Binding " -g '*.xaml'` — each hit has a recorded reason.
- `rg -n "\.Result\b|\.Wait\(\)|GetAwaiter\(\)\.GetResult\(\)" -g '*.cs'` — none in production code.
- `rg -n "<ScrollViewer" -g '*.xaml'` — none contains a `ListView`, `GridView` or `ItemsRepeater`.
- A heap diff after ten navigations shows no growing page type.
- Cold-start median recorded before and after.

## Common gotchas

- **`ListView` inside a `ScrollViewer`** — every row is realized; startup and scrolling slow down together.
- **A strong messenger subscription** — each visit to a page adds a live receiver.
- **`x:Bind` defaults to `OneTime`** — a value that changes silently stops updating; set the mode.
- **Dispatching per item** — a hundred `TryEnqueue` calls cost more than one.
- **Debug build timed** — the numbers are meaningless.
- **AOT turned on, `{Binding}` left in** — a run-time failure after publish.
- **A splash with a fixed delay** — it is the slowness.
- **Measuring on the dev machine only** — the target class (an older laptop, ARM64) is the benchmark.

## Handoffs

- Failure states while loading → `desktop-windows:error-handling`; local storage → `desktop-windows:offline-and-storage`
- XAML structure and lists → `desktop-windows:ui-components`; project properties → `desktop-windows:project-setup`
- Native hops → `desktop-windows:cpp-winrt`; observability base → `desktop-shared:observability`
- Mac counterpart → `desktop-macos:performance`
