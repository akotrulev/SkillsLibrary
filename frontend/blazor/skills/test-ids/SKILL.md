---
name: fe-blazor-test-ids
description: Use when adding, auditing, or fixing `data-testid` attributes in Blazor (.razor) pages and components so UI suites can target the app — including consuming a `missing-testids.md` report from QA's `page-objects-from-url` / `mobile-screen-explorer`. Triggers: "add testids to this page", "audit the data-testids", "QA sent a missing-testids report". Do NOT use to write the UI tests (`qa-ui-dotnet`) or build page objects (qa `page-objects-from-url`).
---

# Blazor Testability — `data-testid` Writer

Adds and audits `data-testid` attributes on Blazor components so automated UI suites target the app by stable, intention-revealing locators. This is the dev-side half of a loop QA owns: `qa/{stack}/skills/page-objects-from-url` and `mobile-screen-explorer` locate **data-testid-first** and file a `missing-testids.md` report for elements that lack one — this skill consumes that report.

## When to use

- Add `data-testid` attributes to one or more `.razor` files for automated UI testing
- Audit an existing page for missing / inconsistent / colliding testids
- Apply the convention to newly written pages or components
- A `missing-testids.md` report has been handed over by QA

## When NOT to use

- Writing UI tests / page objects → the QA stack agents (`qa-ui-dotnet`)
- Hybrid static-HTML/JS surfaces → same rules, mechanics in `references/static-html.md`
- Component scaffolding at large → `frontend/blazor/skills/component-writer` (which already emits testids per this convention)

## Output format

Single attribute only: `data-testid="..."`. No `aria-label` mirroring the value, no second attribute. Always PascalCase, dot-separated segments. (Accessible labels are an accessibility concern, owned separately — never conflate the two.)

## The rules

### 1. Where the attribute goes

| Element kind | How to set `data-testid` |
|---|---|
| Raw HTML leaf (`<button>`, `<input>`, `<a>`, `<td>`, `<span>` used as anchor) | Inline attribute: `<button data-testid="...">` |
| Component-library control (see matrix below) | **Inline attribute** on the component tag: `<RadzenButton data-testid="..." />`. The library's unmatched-attribute capture forwards it to the rendered root. Compile-time, allocation-free, identical DOM. |
| Custom Razor component we own | `[Parameter] public string? TestId { get; set; }` — a **prefix** the component composes its own suffix onto (Rule 4) |

Use the `@attributes` dictionary form **only** when the testid is genuinely dynamic inside a loop and a named local reads better (Rule 7). Static interpolations (`$"{TidPrefix}.SubmitButton"`) fit fine inline — no dictionary needed. **Inline always wins when both work.**

Do **not** introduce wrapper components (`AppButton`, `AppTextBox`, …) for the sake of testids.

#### Per-library attribute mechanics

All major Blazor component libraries capture unmatched attributes via `[Parameter(CaptureUnmatchedValues = true)]` and splat them onto the rendered root — so the inline form works across the board. Where the captured dictionary is exposed (for programmatic composition), the parameter name differs:

| Library | Capture parameter (on the base class) | Inline `data-testid="..."` on the tag |
|---|---|---|
| **Radzen** | `Attributes` (`RadzenComponent`) | ✅ forwarded to the rendered root |
| **MudBlazor** | `UserAttributes` (`MudComponentBase`) | ✅ for most components; a few (e.g. `MudTabPanel`) don't render captured attributes — verify the DOM and fall back to tagging an inner anchor element |
| **Fluent UI Blazor** | `AdditionalAttributes` (`FluentComponentBase`) | ✅ forwarded to the rendered root |
| **Telerik / Syncfusion (enterprise)** | Per-component `HtmlAttributes` / attribute dictionaries — check the component's API | Usually ✅; where not, tag the nearest owned wrapper element already in your markup |
| **Plain HTML / own components** | `@attributes="AdditionalAttributes"` splat (standard Blazor pattern) | ✅ trivially inline |

After tagging a library control the first time, **verify in the rendered DOM** that the attribute landed on a sensible element — some components forward to an outer wrapper rather than the interactive leaf; tests must know which.

### 2. Naming: `PageOrComponent.ElementType[.Qualifier]`

PascalCase segments, dot-separated. No spaces, no kebab-case, no numeric IDs, no array indexes, no enabled/disabled state values.

- **PageOrComponent** — the page locator root, derived from the `@page` route turned into PascalCase: `/operations/scheduled-jobs` → `Operations.ScheduledJobs`. If the file has a natural component name (a row, a card), use that.
- **ElementType** — the role: `SubmitButton`, `EmailField`, `Grid`, `Row`, `AddButton`, `Action`, `ConfirmDialog`.
- **Qualifier** *(optional)* — meaningful semantic value: enum name, field name, action name. Never numeric IDs or indexes.

```
Operations.ScheduledJobs.AddButton
Operations.ScheduledJobs.Action.Pause
Operations.ScheduledJobs.Form.Field.Cron
ExposureFeeChargesGrid.Row
ExposureFeeChargesGrid.Row.Symbol
```

### 3. Extract repeated values into a `const`

When the same locator is used more than once, extract it.

- **Static** → `private const string` in the `@code` block, PascalCase.
- **Dynamic** → inline `var` (or `@{}` block) inside the loop / render path.

```razor
@code {
    private const string CloseButtonLocator = "ToastMessage.CloseButton";
}

<button data-testid="@CloseButtonLocator" @onclick="Close">×</button>
```

When three or more sites in one file share a screen-scoped prefix, extract a `TidPrefix` const and interpolate:

```razor
@code {
    private const string TidPrefix = "Assets.IndexSearch";
}

<RadzenTextBox @bind-Value="searchQuery" data-testid="@($"{TidPrefix}.Query")" />
<RadzenButton Text="Search" Click="@DoSearch" data-testid="@($"{TidPrefix}.SubmitButton")" />
<RadzenDataGrid TItem="Suggestion" Data="@suggestions" data-testid="@($"{TidPrefix}.ResultsGrid")" />
```

Renaming the section becomes a one-line edit instead of grep-and-replace.

When a component composes its testid from a `TestId` prefix, always use a non-null fallback and assign to a named local — never inline a `?:` that collapses to `null`:

```razor
@* ✅ Always a string *@
@{ var composedTestId = $"{TestId ?? ""}.Title"; }
<h2 data-testid="@composedTestId">@Title</h2>

@* ❌ collapses to null/missing attribute *@
<h2 data-testid="@(TestId is null ? null : $"{TestId}.Title")">@Title</h2>
```

### 4. Components compose their suffix

A custom Razor component takes a `TestId` prefix and appends its element type:

```razor
@* StatusBadge.razor *@
<span data-testid="@ComposedTestId">@Status</span>

@code {
    [Parameter] public string? TestId { get; set; }
    [Parameter] public ItemStatus Status { get; set; }

    private string ComposedTestId => $"{TestId ?? ""}.StatusBadge";
}
```

Caller passes the **prefix only**:

```razor
<StatusBadge TestId="Order.Header" Status="@status" />
@* renders: data-testid="Order.Header.StatusBadge" *@
```

Pass-through wrappers (a component that delegates to another component without adding a meaningful role) forward `TestId` untouched — only the terminal component appends a suffix.

### 5. Which elements get a `data-testid`

Apply to:
- Interactive elements: `<button>`, `<a>` used as nav, `<input>`, `<select>`, `<textarea>`, library buttons/inputs/dropdowns/switches/date pickers, action menu items.
- List/grid containers: `<table>`, library data grids, custom list roots.
- Read anchors: status badges, computed totals, toast/error banners, empty states, dynamic text the test must read.

Skip:
- Decorative `<div>`/`<span>` wrappers, layout containers.
- Static `<label>` text already addressable through its associated input.
- Pure styling elements (icons unless they're the interactive target).

### 6. List rows: hardcoded static parent locator

Row components rendered repeatedly inside a list **must not** accept a per-row testid prop. The parent locator is hardcoded as a `const` inside the row component, and child elements namespace under it.

```razor
@* SchedulerRow.razor *@
<tr data-testid="@RowLocator">
    <td data-testid="@($"{RowLocator}.Name")">@Model.Name</td>
    <td data-testid="@($"{RowLocator}.Cron")">@Model.Cron</td>
    <td data-testid="@($"{RowLocator}.Status")">@(Model.IsPaused ? "Paused" : "Active")</td>
</tr>

@code {
    private const string RowLocator = "SchedulerRow";
    [Parameter] public SchedulerInfo Model { get; set; } = default!;
}
```

Tests address individual rows by index against the shared `SchedulerRow` selector. Per-row keys (id, symbol, ticker) **must not** appear in the parent locator.

When the same role renders twice in a single row instance (e.g. regular vs after-hours change percent), distinguish by sub-namespace:

```razor
<Delta TestId="SymbolListItem" ... />              @* → SymbolListItem.ChangePercent *@
<Delta TestId="SymbolListItem.AfterHours" ... />   @* → SymbolListItem.AfterHours.ChangePercent *@
```

For one-off composite components (a page header, a single summary card), a screen-scoped parent is fine: `Order.Header`, with children `Order.Header.Reference`, `Order.Header.Total`.

### 7. Derive locators from render-time data, not lookup tables

When a component renders rows/items from a typed `enum` or carries the identifier in its props, build the testid inline from that data. Do **not** introduce a hand-maintained `Dictionary<TEnum, string>`.

```razor
@* ✅ Inline, derived from data already in scope *@
@foreach (var section in Enum.GetValues<EPortfolioSections>())
{
    var tabAttrs = new Dictionary<string, object>
    {
        ["data-testid"] = $"PortfolioStack.Tab.{section}"
    };
    <RadzenTabsItem Text="@section.ToString()" @attributes="tabAttrs" />
}
```

```csharp
// ❌ Hand-maintained mapping — drifts when enum values are renamed/added
private static readonly Dictionary<EPortfolioSections, string> TabTestIds = new() { ... };
```

For string values already in scope (`selectedTab`, `item.Label`, `field.Name`), interpolate directly: `$"ActivityFilters.{selectedTab}.{item.Label}"`.

**Why:** lookup tables drift — a new enum value silently falls through to a default; a renamed value leaves a stale entry. Direct interpolation binds the locator to the source identifier so renames propagate automatically.

## Page locator derivation

Default: turn the `@page` route into PascalCase, dropping a leading area segment if the whole app lives under it (e.g. `/admin`).

| Route | Page locator root |
|---|---|
| `/operations/scheduled-jobs` | `Operations.ScheduledJobs` |
| `/trade/exposure-day-count-settings` | `Trade.ExposureDayCountSettings` |
| `/users/{Id}` | `Users.Detail` (drop route params; use a meaningful suffix) |
| `/` | `Home` |

If the page has a single dominant component (a header card, a wizard step), prefer that component's name as the locator root.

## Metadata-driven UIs (generated shells)

Many apps render CRUD through a metadata/descriptor framework (a generic `CrudList<T>` / `CrudForm` driven by an entity descriptor), leaving page-level `.razor` files as 4-line shells with nothing to attribute. Do **not** tag such pages one by one — **edit the framework components once** so they emit systematic testids derived from the metadata:

| Framework surface | Emit |
|---|---|
| List/grid root | `{Entity}.Grid` |
| Row element | `{Entity}.Row` |
| Add button | `{Entity}.AddButton` |
| Built-in Edit / Delete row buttons | `{Entity}.Builtin.Edit` / `{Entity}.Builtin.Delete` |
| Custom action button | `{Entity}.Action.{ActionName}` (PascalCase the action name) |
| Form field | `{Entity}.Form.Field.{FieldName}` |
| Form submit / cancel | `{Entity}.Form.Submit` / `{Entity}.Form.Cancel` |
| Action-dialog field / confirm / cancel | `{Entity}.Action.{ActionName}.Field.{FieldName}` / `.Confirm` / `.Cancel` |

> Built-ins sit under `.Builtin.*` so a custom action named `Edit` or `Delete` never collides with the framework-emitted row buttons — custom verbs always use `.Action.{Name}`.

Every metadata-driven page becomes selectable with zero per-page work, and a new entity gets its full locator set for free. Hand-rolled pages (dashboards, wizards) follow Rules 1–7 directly.

## Consuming a `missing-testids.md` report

When QA's `page-objects-from-url` / `mobile-screen-explorer` hands over a report of elements it could not locate testid-first:

1. Treat each listed element as a Rule 5 candidate; derive its locator per Rules 2–7.
2. Elements the report lists but Rule 5 classifies as decorative: don't tag — note them in the response so QA can re-anchor.
3. Report back locator counts + collisions (see contract below) so QA can regenerate the page objects.

## Procedure when invoked

1. Confirm scope: a single file, a directory, a feature area, or a `missing-testids.md` report. Do not silently rewrite the whole tree.
2. For each target `.razor` file:
   1. Determine the page locator root (route-derived or component-derived).
   2. Walk the markup. For each candidate element (Rule 5), generate the locator and apply it via the right mechanism (inline attribute, capture-forwarding on library controls, `TestId` prefix prop, hardcoded row const).
   3. Skip decorative elements; note them in the summary.
3. If the target is a metadata-driven shell page, do **not** touch the page — propose edits to the framework components instead, in a separate diff.
4. Outside a `Gate: none` plan task, build the touched project (`dotnet build`) to confirm nothing broke.
5. Report per the contract:
   - Files modified, with locator counts per file.
   - Decorative elements skipped (so the user can override if any need anchoring).
   - **Locator collisions detected (same testid on two distinct elements) — these block completion.**

## Anti-patterns to flag

| Anti-pattern | Fix |
|---|---|
| `data-testid="@($"Row.{model.Id}")"` on a list row | Hardcode static row locator (Rule 6) |
| `data-testid` on a layout `<div>` with no test purpose | Remove |
| `Dictionary<TEnum, string>` mapping enum → testid | Replace with inline `$"...{enumValue}"` (Rule 7) |
| Inline `?:` collapsing to `null` | Use `?? ""` and a named local (Rule 3) |
| New `AppButton`/`AppTextBox` wrapper introduced just to carry testids | Set the inline attribute on the library control — its unmatched-attribute capture forwards it (Rule 1) |
| `@attributes` dictionary for a static testid | Inline attribute — the dictionary form is for loop-dynamic values only (Rule 1) |
| Two distinct elements sharing the same locator | Sub-namespace one of them (Rule 6) |
| kebab-case or snake_case segments | PascalCase only |
| Locators containing numeric IDs, GUIDs, or array indexes | Use enum names or field names; rows are addressed by index over a shared locator |
| `aria-label` added to mirror a testid | One attribute only — a11y labels are owned by the accessibility skill, on their own merits |

## References

- `references/static-html.md` — the same rules applied to non-Blazor surfaces in hybrid apps (static HTML pages, JS string-template rendering).

## Handoffs

- Page objects / UI tests against these locators → `qa-ui-dotnet` (peer agent; `page-objects-from-url` locates data-testid-first)
- Scaffolding new components (testids emitted by default) → `frontend/blazor/skills/component-writer`
- Reviewing testid hygiene as part of a broader review → `frontend/blazor/skills/code-review`
