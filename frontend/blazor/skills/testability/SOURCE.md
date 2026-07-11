# SEED MATERIAL — do not register as a skill

Verbatim production skill ("Blazor data-testid Writer", FlexInvest Admin service) handed over 2026-07-11.
Generalize into `frontend/blazor/skills/testability/SKILL.md` in Session A — see `frontend/PLAN.md` §3b item 0
for the generalization deltas (strip project paths, per-library attribute mechanics, metadata-driven-UI
generalization of the descriptor-CRUD section, fix the `@attributes`-vs-inline inconsistency in the
anti-pattern table). The rules themselves (naming, consts, row locators, data derivation) carry over unchanged.

---

---
description: "Add data-testid attributes to Blazor (Razor) pages and components in the Admin service so they can be targeted by automated UI tests. Use when the user asks to add, audit, or fix testids/data-testid attributes in .razor files."
---

# Skill: Blazor data-testid Writer

## When to use

Invoke when the user wants to:
- Add `data-testid` attributes to one or more `.razor` files for automated UI testing
- Audit an existing page for missing/inconsistent testids
- Apply the testid convention to newly written admin pages or components

Scope is the Admin service (`Microservices/Admin/FlexInvest.AdminService.API/**/*.razor`) and the Broker simulator UI (`Microservices/Broker/FlexInvest.BrokerService.API/wwwroot/index.html`). The naming (Rule 2), const-prefix (Rule 3), row-template (Rule 6), and data-derivation (Rule 7) rules apply to any UI in the repo; the Blazor-specific mechanics (Radzen inline-attribute / `@attributes` splat, component `TestId` props, descriptor-driven grids) apply only to `.razor` files. For non-Blazor UIs see the "Static HTML / jQuery-template UIs" section below.

## Output format

Single attribute only: `data-testid="..."`. No `aria-label`, no second attribute mirroring the value. Always PascalCase, dot-separated segments.

## The rules

### 1. Where the attribute goes

| Element kind | How to set `data-testid` |
|---|---|
| Raw HTML leaf (`<button>`, `<input>`, `<a>`, `<td>`, `<span>` used as anchor) | Inline attribute: `<button data-testid="...">` |
| Radzen component (`<RadzenButton>`, `<RadzenTextBox>`, `<RadzenDropDown>`, `<RadzenSwitch>`, `<RadzenDataGrid>`, etc.) | **Inline attribute**: `<RadzenButton data-testid="..." />`. Radzen's `RadzenComponent` base captures unmatched attributes via `[Parameter(CaptureUnmatchedValues = true)]` and forwards them to the rendered root. The Blazor compiler emits `AddAttribute` calls directly — no per-render `Dictionary<string, object>` allocation. Use the `@attributes` dictionary form **only** when the testid is genuinely dynamic inside a loop (see Rule 7). |
| Custom Razor component we own | Add a `[Parameter] public string? TestId { get; set; }` and either render it onto a leaf or splat it into a Radzen child. |

#### Setting `data-testid` on Radzen

Prefer the inline attribute form. It's compile-time, allocation-free, and produces identical DOM output:

```razor
@* ✅ Preferred — inline attribute *@
<RadzenButton Text="Save" Click="Save" data-testid="Login.SubmitButton" />
<RadzenTextBox @bind-Value="email" data-testid="Login.EmailField" />
<RadzenDataGrid TItem="User" Data="@users" data-testid="Users.Grid" />
```

Use the `@attributes` dictionary form **only** when the testid is built from a loop variable or other dynamic data where a named local genuinely reads better (see Rule 7):

```razor
@foreach (var section in Enum.GetValues<EPortfolioSections>())
{
    var tabAttrs = new Dictionary<string, object>
    {
        ["data-testid"] = $"PortfolioStack.Tab.{section}"
    };
    <RadzenTabsItem Text="@section.ToString()" @attributes="tabAttrs" />
}
```

Static interpolations (`$"{TidPrefix}.SubmitButton"`) fit fine in the inline form — no dictionary needed.

Do **not** introduce wrapper components (`AppButton`, `AppTextBox`, etc.) for the sake of testids.

### 2. Naming: `PageOrComponent.ElementType[.Qualifier]`

PascalCase segments, dot-separated. No spaces, no kebab-case, no numeric IDs, no array indexes, no enabled/disabled state values.

- **PageOrComponent** — the page locator root, derived from the `@page` route turned into PascalCase. `/operations/scheduled-jobs` → `Operations.ScheduledJobs`. `/trade/exposure-day-count-settings` → `Trade.ExposureDayCountSettings`. If the file already has a natural component name (a row, a card), use that.
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

```razor
@foreach (var col in Columns)
{
    var columnLocator = $"PortfolioTableConfigModal.Column.{col.Name}";
    <div data-testid="@columnLocator">@col.Name</div>
}
```

When three or more sites in one file share a screen-scoped prefix, extract a `TidPrefix` const and interpolate:

```razor
@code {
    private const string TidPrefix = "Asset.MarketIndexOverviews.FmpSearch";
}

<RadzenTextBox @bind-Value="searchQuery" data-testid="@($"{TidPrefix}.Query")" />
<RadzenButton Text="Search" Click="@DoSearch" data-testid="@($"{TidPrefix}.SubmitButton")" />
<RadzenDataGrid TItem="FmpSuggestion" Data="@suggestions" data-testid="@($"{TidPrefix}.ResultsGrid")" />
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

```csharp
@* SymbolStatusBadge.razor *@
@code {
    [Parameter] public string? TestId { get; set; }
    [Parameter] public SymbolStatus Status { get; set; }

    private string ComposedTestId => $"{TestId ?? ""}.SymbolStatusBadge";
}

<span data-testid="@ComposedTestId">@Status</span>
```

Caller passes the **prefix only**:

```razor
<SymbolStatusBadge TestId="Symbol.Header" Status="@status" />
@* renders: data-testid="Symbol.Header.SymbolStatusBadge" *@
```

Pass-through wrappers (a component that delegates to another component without adding a meaningful role) forward `TestId` as-is — only the terminal component appends a suffix.

### 5. Which elements get a `data-testid`

Apply to:
- Interactive elements: `<button>`, `<a>` used as nav, `<input>`, `<select>`, `<textarea>`, `RadzenButton`, `RadzenTextBox`, `RadzenNumeric`, `RadzenDropDown`, `RadzenSwitch`, `RadzenCheckBox`, `RadzenDatePicker`, action menu items.
- List/grid containers: `<table>`, `RadzenDataGrid`, custom list roots.
- Test anchors: status badges, computed totals, toast/error banners, dynamic text the test must read.

Skip:
- Decorative `<div>`/`<span>` wrappers, layout containers.
- Static `<label>` text already addressable through its associated input.
- Pure styling elements (icons unless they're the interactive target).

### 6. List rows: hardcoded static parent locator

Row components rendered repeatedly inside a list **must not** accept a per-row testid prop. The parent locator is hardcoded as a `const` inside the row component, and child elements namespace under it.

```razor
@* SchedulerRow.razor *@
@code {
    private const string RowLocator = "SchedulerRow";
    [Parameter] public SchedulerInfo Model { get; set; } = default!;
}

<tr data-testid="@RowLocator">
    <td data-testid="@($"{RowLocator}.Name")">@Model.Name</td>
    <td data-testid="@($"{RowLocator}.Cron")">@Model.Cron</td>
    <td data-testid="@($"{RowLocator}.Status")">@(Model.IsPaused ? "Paused" : "Active")</td>
</tr>
```

Tests address individual rows by index against the shared `SchedulerRow` selector. Per-row keys (id, symbol, ticker) **must not** appear in the parent locator.

When the same role renders twice in a single row instance (e.g. regular vs after-hours change percent), distinguish by sub-namespace:

```razor
<Delta TestId="SymbolListItem" ... />              @* → SymbolListItem.ChangePercent *@
<Delta TestId="SymbolListItem.AfterHours" ... />   @* → SymbolListItem.AfterHours.ChangePercent *@
```

For one-off composite components (a page header, a single summary card), screen-scoped parent is fine: `Symbol.Header`, with children `Symbol.Header.Ticker`, `Symbol.Header.Price`.

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

@* ❌ Hand-maintained mapping — drifts when enum values are renamed/added *@
private static readonly Dictionary<EPortfolioSections, string> TabTestIds = new()
{
    [EPortfolioSections.Positions] = "PortfolioStack.Tab.Positions",
    [EPortfolioSections.Orders]    = "PortfolioStack.Tab.Orders",
};
```

For string values already in scope (`selectedTab`, `item.Label`, `field.Name`), interpolate directly: `$"AccountActivityTabFiltersModal.{selectedTab}.{item.Label}"`.

**Why:** lookup tables drift — a new enum value silently falls through to a default, a renamed value leaves a stale entry. Direct interpolation binds the locator to the source identifier so renames propagate automatically.

## Page locator derivation

Default: turn the `@page` route into PascalCase, dropping leading `/admin` if present.

| Route | Page locator root |
|---|---|
| `/operations/scheduled-jobs` | `Operations.ScheduledJobs` |
| `/trade/exposure-day-count-settings` | `Trade.ExposureDayCountSettings` |
| `/users/{Id}` | `Users.Detail` (drop route params; use a meaningful suffix) |
| `/` | `Home` |

If the page has a single dominant component (e.g. a header card or a wizard step), prefer that component's name as the locator root.

## Descriptor-driven pages (REFLEX-specific)

The Admin panel renders most CRUD via `DescriptorCrudList` → `CrudList<>` → `CrudForm` / `ActionDialog`. Page-level `.razor` files are usually 4 lines and have nothing to attribute.

For these pages, **edit the framework components** so they emit systematic testids derived from the descriptor:

| Component | Emit |
|---|---|
| `CrudList<>` root grid | `{Descriptor.Entity}.Grid` |
| Row element | `{Descriptor.Entity}.Row` |
| Add button | `{Descriptor.Entity}.AddButton` |
| Edit / Delete buttons (built-in) | `{Descriptor.Entity}.Builtin.Edit` / `.Builtin.Delete` |
| Custom action button | `{Descriptor.Entity}.Action.{ActionSpec.Name}` (PascalCase the action name) |

> Built-in Edit/Delete sit under `.Builtin.*` so a custom `ActionSpec` with `Name = "Edit"` or `"Delete"` does not collide with the framework-emitted row buttons. Custom verbs always use `.Action.{Name}`.
| Gear menu trigger | `{Descriptor.Entity}.GearMenu` |
| Gear menu column toggle | `{Descriptor.Entity}.GearMenu.Column.{FieldName}` |
| `CrudForm` field | `{Descriptor.Entity}.Form.Field.{FieldName}` |
| `CrudForm` submit / cancel | `{Descriptor.Entity}.Form.Submit` / `.Form.Cancel` |
| `ActionDialog` field | `{Descriptor.Entity}.Action.{ActionName}.Field.{FieldName}` |
| `ActionDialog` confirm / cancel | `{Descriptor.Entity}.Action.{ActionName}.Confirm` / `.Cancel` |

This makes every descriptor-driven page selectable without per-page work, consistent with the descriptor-first principle in `.claude/rules/admin-blazor.md`.

Hand-rolled pages (dashboards, wizards, simulators) follow rules 1–7 directly.

## Static HTML / jQuery-template UIs

For non-Blazor UIs (currently only the broker simulator at `Microservices/Broker/FlexInvest.BrokerService.API/wwwroot/index.html`), Rules 2, 3, 5, 6, and 7 apply unchanged. The mechanics differ:

- **Static markup** (`<button>`, `<input>`, `<select>`, `<table>`, sectioning `<div>`s): set `data-testid="..."` inline as a plain HTML attribute. No splat needed — the browser routes the attribute to the element directly.
- **JS-rendered rows** (template strings appended via `$tbody.append`, `insertAdjacentHTML`, `el.innerHTML`, or framework loops): hardcode the parent locator as a `const` near the render function and interpolate it into every child element. Never put a per-row id into the locator value.

  ```js
  // ✅ Hardcoded parent locator, namespaced children
  const ROW = 'BrokerSimulator.OrderBook.Row';
  $tbody.append(`
      <tr data-testid="${ROW}">
          <td data-testid="${ROW}.OrderId">${escapeHtml(order.orderId)}</td>
          <td data-testid="${ROW}.Symbol">${escapeHtml(order.symbol)}</td>
      </tr>
  `);

  // ❌ Per-row id leaks into the locator
  <tr data-testid="BrokerSimulator.OrderBook.Row.${order.orderId}">
  ```

- **Modals / dialogs** (Bootstrap `data-bs-target`): tag the modal's outer `<div>` and every form control / submit button inside.
- **Sub-templates that render twice** (e.g. quotes Cards vs. Table view): give each its own sub-namespace (`Quotes.Card`, `Quotes.Row`) per the Rule 6 sub-namespace pattern.
- **Pagination buttons**: `${ParentLocator}.Page.{n}` is acceptable — the page number is the role, not an opaque id.
- **Empty-state rows**: tag the placeholder `<tr>` with `${Section}.EmptyState` so tests can assert "no data" cleanly.

Apply Rule 5 unchanged: tag interactive elements, list/grid containers, and read-only cells the tests will read. Skip decorative wrappers.

## Procedure when invoked

1. Confirm scope with the user: a single file, a directory, or a feature area. Do not silently rewrite the whole admin tree.
2. For each target `.razor` file:
   1. Determine the page locator root (route-derived or component-derived per the rules above).
   2. Walk the markup. For each candidate element (rule 5), generate the locator and apply it via the right mechanism (inline attribute, Radzen splat, component prop, hardcoded row const).
   3. Skip decorative elements; note them in the summary.
3. If the target is a descriptor-driven page (4-line `<DescriptorCrudList>` shell), do **not** touch the page — propose edits to the framework components instead, in a separate diff.
4. Run `dotnet build Microservices/Admin/FlexInvest.AdminService.API/FlexInvest.AdminService.API.csproj --no-restore` to confirm nothing broke.
5. Report:
   - Files modified, with locator counts per file.
   - Decorative elements skipped (so the user can override if any need anchoring).
   - Locator collisions detected (same testid on two distinct elements) — these block completion.

## Anti-patterns to flag

| Anti-pattern | Fix |
|---|---|
| `data-testid="@($"Row.{model.Id}")"` on a list row | Hardcode static row locator (rule 6) |
| `data-testid` on a layout `<div>` with no test purpose | Remove |
| `Dictionary<TEnum, string>` mapping enum → testid | Replace with inline `$"...{enumValue}"` (rule 7) |
| Inline `?:` collapsing to `null` | Use `?? ""` and a named local (rule 3) |
| New `AppButton`/`AppTextBox` wrapper introduced just to carry testids | Splat onto the Radzen control via `@attributes` instead |
| Two distinct elements sharing the same locator | Sub-namespace one of them (rule 6 sub-namespace pattern) |
| kebab-case or snake_case segments | PascalCase only |
| Locators containing numeric IDs, GUIDs, or array indexes | Use enum names or field names; rows are addressed by index over a shared locator |
