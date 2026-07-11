# none — CSS-isolation only, own primitives

No component library. You build a small set of primitives (Button, TextField, Dialog, Toast, DataTable) with plain HTML + CSS isolation, and own the entire look. Pick this when the design is fully bespoke, the payload budget is tight, or a component library would fight the design system rather than serve it.

**Trade-off, stated honestly:** you now own every accessibility detail (focus trap in dialogs, ARIA roles, keyboard nav in the table), every responsive breakpoint, and the DataGrid features (paging/sort/filter/virtualization) a library gives for free. Choose this only when the design genuinely demands it — for most CRUD apps, MudBlazor/Radzen is less work and more accessible out of the box. If you find yourself rebuilding a DataGrid, reconsider the decision.

## What replaces the library

| Library gives you | Here you use |
|---|---|
| Styled controls | Raw HTML + **CSS isolation** (`.razor.css`) per component — [`styling`](../styling/SKILL.md) owns this |
| Theme + dark mode | Your own **design tokens** as CSS custom properties on `:root` / `[data-theme]`, from `design/theme-factory` — [`styling`](../styling/SKILL.md) |
| DataGrid | `<table>` + Blazor **`<Virtualize>`** for long lists; server-side paging via a [`data-access`](../../data-access/SKILL.md) call; you write sort/filter |
| Dialog service | A `Dialog` primitive using the native `<dialog>` element + a small scoped service, or a cascaded overlay host |
| Snackbar/toast | A `ToastService` (scoped) + a host component rendered once in the interactive layout |

## Providers you build — once, at the interactive layout root

The same rule as any library: your toast/dialog **host** components live once under an interactive render mode, and the services that drive them are scoped:

```csharp
// Program.cs (Server AND .Client for Auto/WASM)
builder.Services.AddScoped<ToastService>();
builder.Services.AddScoped<DialogHostService>();
```

```razor
@* MainLayout.razor *@
@Body
<ToastHost />     @* renders queued toasts; subscribes to ToastService.Changed *@
<DialogHost />    @* renders the active dialog; interactive *@
```

```csharp
public sealed class ToastService
{
    private readonly List<Toast> _items = new();
    public IReadOnlyList<Toast> Items => _items;
    public event Action? Changed;
    public void Show(string message, ToastLevel level = ToastLevel.Info)
    { _items.Add(new(message, level)); Changed?.Invoke(); }
}
```

The host subscribes in `OnInitialized` and **unsubscribes in `Dispose`** (`@implements IDisposable`) — the state-container pattern from [`reference`](../reference/SKILL.md).

## Dialog with the native `<dialog>` element

```razor
<dialog @ref="_el" data-testid="ConfirmDialog.Root">
    <p>@Message</p>
    <button @onclick="() => Close(true)" data-testid="ConfirmDialog.Confirm">Delete</button>
    <button @onclick="() => Close(false)" data-testid="ConfirmDialog.Cancel">Cancel</button>
</dialog>
```

Use `showModal()` via minimal JS interop (`.razor.js` collocated module) — native `<dialog>` gives you the focus trap and `Escape`-to-close for free, which is most of the accessibility win. Name the object in destructive confirms (ui-conventions).

## DataTable with server-side paging + Virtualize

```razor
<table data-testid="Orders.Grid">
    <thead>…sortable headers (buttons, not click-handler divs)…</thead>
    <tbody>
        <Virtualize ItemsProvider="LoadAsync" Context="o">
            <tr><td>@o.Number</td><td style="text-align:right">@o.Total.ToString("C")</td></tr>
        </Virtualize>
    </tbody>
</table>

@code {
    async ValueTask<ItemsProviderResult<OrderDto>> LoadAsync(ItemsProviderRequest req)
    {
        var page = await Data.GetOrdersAsync(req.StartIndex, req.Count);   // server-side — data-access
        return new ItemsProviderResult<OrderDto>(page.Items, page.Total);
    }
}
```

`<Virtualize>` is built into Blazor — no library needed for windowed rendering. You still write sort/filter yourself and push them into the `data-access` query.

## Theming + dark mode

Design tokens as CSS custom properties, toggled by a `data-theme` attribute on `<html>`; a one-line JS snippet reads `prefers-color-scheme` and any persisted choice. This is entirely [`styling`](../styling/SKILL.md)'s domain — read it. No component theme system to configure because there are no library components.

## Render-mode gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Toast/dialog host does nothing | Host not under an interactive render mode, or service not scoped | Host in the interactive layout; `AddScoped` in both `Program.cs` for Auto |
| `<button @onclick>` in a primitive dead | Primitive used on a static-SSR page | Interactive island |
| Focus escapes the dialog | Not using native `<dialog>`/`showModal()` and no manual focus trap | Native `<dialog>`, or implement a focus trap (`accessibility` sibling, Session E) |
| Table janky at thousands of rows | Full list rendered without windowing | `<Virtualize>` + server-side paging |

**`data-testid`:** trivial — it's raw HTML, so inline `data-testid="..."` directly. Your own components take a `[Parameter] string? TestId` prefix and compose suffixes ([`testability`](../../testability/SKILL.md) Rule for custom components).

## Validation

- Toast + dialog services scoped and hosts mounted interactively (in both `Program.cs` for Auto).
- Dialog uses native `<dialog>`/`showModal()` (focus trap + Escape for free) or a verified manual trap.
- Long lists use `<Virtualize>` with server-side paging via `data-access`.
- Dark mode toggles via `data-theme` + tokens ([`styling`](../styling/SKILL.md)); keyboard-only pass on dialog + table (a11y is on you here).
