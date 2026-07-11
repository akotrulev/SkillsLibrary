---
name: fe-blazor-js-interop
description: Use when a Blazor component (.NET 8/9/10) genuinely needs JavaScript — the mechanics of calling JS from .NET and .NET from JS safely. Covers collocated `.razor.js` ES modules loaded as `IJSObjectReference` (never global functions/inline JS), `IJSInProcessObjectReference` for synchronous WASM, loading interop in `OnAfterRenderAsync` (never `OnInitializedAsync`/prerender), `IAsyncDisposable` teardown with the `JSDisconnectedException` trap on Server, `[JSInvokable]` + `DotNetObjectReference` callbacks with disposal, `IJSStreamReference`/byte-stream transfer, and the net10 constructor-invocation + JS-property read/write APIs. Triggers: "call this JS library from Blazor", "wrap a browser API (clipboard/geolocation/canvas)", "invoke a C# method from JS", "why does my JS interop throw during prerender". Do NOT use where C# suffices (interop is the last resort), for motion/observers (use `motion`), realtime hubs (use `realtime`), or CSS/`::deep` work (use `styling`).
---

# Blazor — JavaScript Interop

Owns the **mechanics** of the JS↔.NET boundary: how to call JavaScript from a component, call C# back from JavaScript, load and dispose modules, and move data across — *once you've decided interop is unavoidable*. Whether to reach for it at all is a house rule, restated below.

**House rule (from CLAUDE.md): no JS interop where C# suffices.** Interop is a last resort — it adds a serialization hop, a disposal obligation, and a render-mode landmine. Before writing any, check that a native Blazor construct, a CSS technique ([`motion`](../motion/SKILL.md), [`styling`](../styling/SKILL.md)), or a component-library feature ([`component-library`](../component-library/SKILL.md)) can't do it. Legitimate interop: a browser API with no .NET surface (clipboard, geolocation, `IntersectionObserver`, Web Crypto, canvas/WebGL), or an established JS library with no Blazor equivalent. Everything else stays in C#.

**Version rule:** the core pattern (collocated module + `IJSObjectReference` + `OnAfterRenderAsync` load + `IAsyncDisposable`) is **identical across net8/9/10**. Deltas: **net9+** adds `ComponentBase.RendererInfo.IsInteractive` to detect whether interop is even possible yet (cleaner than the old "did `OnAfterRenderAsync` fire" heuristic); **net10** adds constructing JS objects via a constructor function and reading/writing JS object properties directly from .NET (below). Never apply the net10 property/constructor APIs to a down-level project — use a wrapper function in the module instead.

## When to use

- Wrapping a browser API with no .NET equivalent (clipboard, geolocation, `matchMedia`, Web Share, File System Access)
- Driving a JS library that has no Blazor port (a charting/maps/editor lib rendering into a `@ref`'d node)
- Letting JS call back into C# (an observer callback, a resize handler, a third-party event)
- Transferring binary data (upload/download, canvas pixels) across the boundary
- Diagnosing "interop threw during prerender / static SSR"

## When NOT to use

- Anything C# can already do (formatting, state, navigation, HTTP) — **stay in C#**
- Scroll reveals / entrance animation / view transitions → [`motion`](../motion/SKILL.md) (CSS first; interop only as its documented fallback)
- SignalR hubs / server push / live streams → [`realtime`](../realtime/SKILL.md)
- CSS isolation, `::deep`, focus-visible → [`styling`](../styling/SKILL.md)
- Focus movement / live-region announcements → [`accessibility`](../accessibility/SKILL.md) (uses `ElementReference.FocusAsync`, minimal interop)

## The one correct shape: a collocated ES module behind `IJSObjectReference`

**Never** register global JS functions or inline `<script>` — they pollute the global scope and can't be tree-shaken or scoped. Collocate a module next to the component (`Widget.razor` → `Widget.razor.js`), import it lazily, hold the handle, dispose it.

```razor
@* Widget.razor *@
@implements IAsyncDisposable
@inject IJSRuntime JS

<div @ref="_host"></div>

@code {
    private ElementReference _host;
    private IJSObjectReference? _module;

    // Interop runs ONLY after the component is interactive — OnAfterRenderAsync is the
    // first place a JS runtime exists. Never call JS from OnInitializedAsync (prerender has none).
    protected override async Task OnAfterRenderAsync(bool firstRender)
    {
        if (!firstRender) return;
        _module = await JS.InvokeAsync<IJSObjectReference>(
            "import", "./Components/Widget.razor.js");   // main project: ./{path}.razor.js
        await _module.InvokeVoidAsync("init", _host);
    }

    public async ValueTask DisposeAsync()
    {
        if (_module is not null)
        {
            try { await _module.InvokeVoidAsync("dispose"); await _module.DisposeAsync(); }
            catch (JSDisconnectedException) { /* Server circuit already gone — nothing to clean up */ }
        }
    }
}
```

```js
// Widget.razor.js — a real ES module; no globals
let instance;
export function init(host) { instance = new SomeLib(host); }
export function dispose() { instance?.destroy(); instance = null; }
```

- **Module path:** main project → `./{ComponentPath}.razor.js`; a **Razor Class Library** → `./_content/{AssemblyName}/{ComponentPath}.razor.js`. Get this wrong and `import` 404s silently.
- **The `JSDisconnectedException` trap is Server-only.** On an interactive-**Server** circuit, disposal can run *after* the client disconnected, so the interop call throws — catch and ignore it. In **WASM** there's no circuit to lose; you may drop the try/catch.
- **Load in `OnAfterRenderAsync(firstRender)`**, not `OnInitializedAsync` — see the render-mode section. Never `await` a hidden JS call in `OnInitializedAsync`; it throws during prerender.

## `IJSObjectReference` vs `IJSInProcessObjectReference` — WASM can go synchronous

- **`IJSRuntime` / `IJSObjectReference`** — async, works in every render mode (Server marshals over the circuit). The default; use it unless you've measured a WASM hot path.
- **`IJSInProcessRuntime` / `IJSInProcessObjectReference`** — **WASM only**, synchronous, no serialization round-trip. Cast to it (`(IJSInProcessRuntime)JS`) for tight client-side loops. It still implements `IAsyncDisposable`/`IDisposable` — dispose it or leak.

Don't reach for the in-process variant to "simplify away await" — it fails at runtime the moment the component runs on Server or during prerender.

## Calling .NET from JavaScript — `[JSInvokable]` + `DotNetObjectReference`

For an **instance** method (the common case — a callback tied to *this* component), pass a `DotNetObjectReference<T>` into the module and **dispose it** alongside the module:

```razor
@implements IAsyncDisposable
@code {
    private IJSObjectReference? _module;
    private DotNetObjectReference<Widget>? _self;

    protected override async Task OnAfterRenderAsync(bool firstRender)
    {
        if (!firstRender) return;
        _self = DotNetObjectReference.Create(this);
        _module = await JS.InvokeAsync<IJSObjectReference>("import", "./Widget.razor.js");
        await _module.InvokeVoidAsync("wire", _self);
    }

    [JSInvokable]
    public Task OnJsEvent(string payload)   // JS calls dotnet.invokeMethodAsync('OnJsEvent', ...)
    {
        // mutate state, then StateHasChanged — see the InvokeAsync note below
        return InvokeAsync(StateHasChanged);
    }

    public async ValueTask DisposeAsync()
    {
        if (_module is not null) { try { await _module.DisposeAsync(); } catch (JSDisconnectedException) { } }
        _self?.Dispose();   // a leaked DotNetObjectReference pins the component forever
    }
}
```

- A **`static [JSInvokable]`** method (`JS.InvokeAsync` targeting `[JSInvokable("Name")]` on a static) needs no object reference — use it for app-global callbacks, not per-component ones.
- **Marshal UI mutations through `InvokeAsync(StateHasChanged)`.** A JS callback arrives off Blazor's synchronization context; touching component state directly races the renderer — the same rule [`realtime`](../realtime/SKILL.md) enforces for background→UI updates.
- **Every `DotNetObjectReference.Create` needs a matching `Dispose`** — it's a GC root; forgetting it leaks the whole component on each navigation.

## net10: construct JS objects and read/write properties from .NET

net10 lets .NET create a JS instance via its constructor and get an `IJSObjectReference` handle, then read/modify data and accessor properties — removing hand-written wrapper functions for simple object graphs:

```csharp
// net10 only
await using var map = await JS.InvokeConstructorAsync<IJSObjectReference>("google.maps.Map", host, opts);
await map.SetPropertyAsync("zoom", 12);
var zoom = await map.GetPropertyAsync<int>("zoom");
```

On **net8/9**, achieve the same with a one-line wrapper in the collocated module (`export function makeMap(h,o){ return new google.maps.Map(h,o); }`). Keep the net10 APIs behind the version gate — they don't exist down-level.

## Moving data across the boundary

- **Small values** serialize as JSON automatically. Keep payloads small — every arg/return crosses a (de)serialization step, doubled on Server (over the wire).
- **Binary** — pass a **`IJSStreamReference`** (JS→.NET) or a **`DotNetStreamReference`** (.NET→JS) and read the stream; never base64 a large blob through a JSON string.
- **Chatty patterns cost most on Server.** Batch: one interop call returning a shaped object beats ten property reads. On WASM, prefer `IJSInProcessObjectReference` for genuinely hot loops.

## Render modes: interop's hardest edge

Interop needs a live JS runtime, which **does not exist during prerender or on static SSR**. Rules:

- **Never call JS in `OnInitializedAsync`/`OnParametersSetAsync`** — they run during prerender; the call throws `InvalidOperationException` ("JavaScript interop calls cannot be issued at this time").
- **`OnAfterRenderAsync` is the safe entry point** — it only fires once the component is interactive (Server circuit up, or WASM loaded).
- **net9+:** gate optional interop with `if (RendererInfo.IsInteractive)` when a component may render statically — cleaner than inferring from render count.
- A **statically-rendered** component (no `@rendermode`) never becomes interactive → its interop never runs. If a feature *needs* JS, the consumer must give it an interactive render mode ([`project-scaffold`](../project-scaffold/SKILL.md) owns that decision); the component stays render-mode-agnostic (CLAUDE.md rule).

## Rules

- **C# first** — write interop only for a browser API or JS library with no .NET equivalent.
- **Collocated ES module behind `IJSObjectReference`** — never global functions or inline `<script>`.
- **Load in `OnAfterRenderAsync(firstRender)`**, never `OnInitializedAsync` (prerender has no JS runtime).
- **`IAsyncDisposable` always** — dispose the module and every `DotNetObjectReference`; wrap Server disposal in a `JSDisconnectedException` catch.
- **`InvokeAsync(StateHasChanged)`** for any UI update triggered by a `[JSInvokable]` callback.
- **`IJSInProcessObjectReference` only on WASM**, only for a measured hot path; still dispose it.
- **Binary via stream references**, never base64-through-JSON.
- **net10 constructor/property APIs stay version-gated**; use a module wrapper on net8/9.
- **Components stay render-mode-agnostic** — the interactive mode is the consumer's choice.

## What NOT to do

- No inline `<script>` or `window.myGlobalFn` — unscoped, unmanaged, un-disposable.
- No interop in `OnInitializedAsync` — it throws during prerender/static SSR.
- No module or `DotNetObjectReference` without `DisposeAsync`/`Dispose` — leaks on every navigation.
- No Server disposal without the `JSDisconnectedException` trap — a benign disconnect surfaces as an error.
- No direct component-state mutation from a JS callback — marshal via `InvokeAsync`.
- No `IJSInProcessRuntime` cast in a component that can render on Server or prerender — runtime failure.
- No net10 `Get/SetPropertyAsync`/`InvokeConstructorAsync` on a net8/9 target — the API isn't there.
- No interop to do what CSS or a native Blazor feature already does.

## Validation

- Prerender a page using the component → no "interop calls cannot be issued at this time" error (the call is in `OnAfterRenderAsync`, not init).
- Navigate away and back repeatedly → memory stable (module + `DotNetObjectReference` disposed; no growing handle count).
- Kill the Server circuit (stop the app tab mid-session) → disposal doesn't surface an unhandled `JSDisconnectedException`.
- Trigger the JS→.NET callback → the UI updates (it went through `InvokeAsync(StateHasChanged)`), no cross-thread render warning.
- On WASM, a hot interop loop using `IJSInProcessObjectReference` → no per-call async overhead; still disposed on teardown.
- Render the component **statically** (no render mode) → it degrades gracefully (interop simply doesn't run); nothing throws.

## Handoffs

- Whether interop is even needed / native alternatives → [`reference`](../reference/SKILL.md) + this skill's house rule
- CSS animation, scroll reveals, view transitions (interop only as fallback) → [`motion`](../motion/SKILL.md)
- SignalR client / server push / streaming → [`realtime`](../realtime/SKILL.md)
- Focus + announcements (`ElementReference.FocusAsync`, minimal interop) → [`accessibility`](../accessibility/SKILL.md)
- Which render mode a JS-dependent component needs → [`project-scaffold`](../project-scaffold/SKILL.md)
- CSS isolation / `::deep` for a JS-library's injected DOM → [`styling`](../styling/SKILL.md)
