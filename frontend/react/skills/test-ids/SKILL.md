---
name: fe-react-test-ids
description: Use when adding, auditing, or fixing `data-testid` attributes in pages/components so UI suites can target the app — including consuming a `missing-testids.md` report from QA's `page-objects-from-url`. Covers per-library attribute mechanics (MUI `slotProps`, Mantine/Chakra rest-props, shadcn/none). Triggers "add testids to this page", "audit the data-testids", "the E2E test can't find this element". Not for writing the UI tests (`qa-ui-typescript`).
---

# React — Testability (`data-testid` writer)

Adds and audits `data-testid` attributes on React components so automated UI suites target the app by stable, intention-revealing locators. This is the dev-side half of a loop QA owns: `qa/typescript/skills/page-objects-from-url` locates **data-testid-first** and files a `missing-testids.md` report for elements that lack one — this skill consumes that report.

**Version rule:** version-agnostic across React 18/19 and Next 14/15 — a `data-testid` is a plain JSX attribute and behaves identically in Server and Client Components. The only React-specific note: an RSC can carry testids on presentational markup, but the elements a test actually *drives* (click/type) live under a `'use client'` boundary — tag both.

## When to use

- Add `data-testid` attributes to one or more `.tsx` files for automated UI testing
- Audit an existing page for missing / inconsistent / colliding testids
- Apply the convention to newly written pages or components
- A `missing-testids.md` report has been handed over by QA
- Decide where the attribute goes on a specific component-library control

## When NOT to use

- Writing UI tests / page objects → the QA stack agent (`qa-ui-typescript`)
- Component scaffolding at large → [`component-writer`](../component-writer/SKILL.md) (which already emits testids per this convention)
- Choosing/wiring the component library → [`component-library`](../component-library/SKILL.md)
- Blazor → `frontend/blazor/skills/test-ids`

## Output format

Single attribute only: `data-testid="..."`. No `aria-label` mirroring the value, no second attribute. Always PascalCase, dot-separated segments. (Accessible labels are an accessibility concern, owned by [`accessibility`](../accessibility/SKILL.md) — never conflate the two.)

## The rules

### 1. Where the attribute goes

| Element kind | How to set `data-testid` |
|---|---|
| Raw HTML leaf (`<button>`, `<input>`, `<a>`, `<td>`, `<span>` used as anchor) | Inline attribute: `<button data-testid="…">` |
| Component-library control (see matrix below) | **Inline attribute** on the component tag; the library spreads unmatched/rest props onto the rendered root. For slotted internals, use the library's slot API (`slotProps`) or the specific compound part. |
| Custom component we own | A `testId` **prefix** prop the component composes its own suffix onto (Rule 4) |

Prefer the **inline attribute** whenever it works — it's the simplest and produces identical DOM. Do **not** introduce wrapper components (`AppButton`, `AppTextField`) just to carry testids.

#### Per-library attribute mechanics

This matrix is the companion to [`component-library`](../component-library/SKILL.md)'s — it promised these exact forms:

| Library | Inline `data-testid="…"` | Slotted / compound internals |
|---|---|---|
| **MUI** | ✅ forwarded to the rendered root on most components | Use `slotProps` to reach an internal element — e.g. `<TextField slotProps={{ htmlInput: { 'data-testid': 'Login.EmailField' } }} />`, `slotProps={{ root: { 'data-testid': '…' } }}`. MUI X `DataGrid` root takes `data-testid` inline; cells are addressed by column/row. |
| **Mantine** | ✅ forwarded to the rendered root (Mantine spreads rest props) | Rare; when a portal/inner element is the target, use the component's `*Props` escape hatch (e.g. `inputProps`) |
| **Chakra UI v3** | ✅ forwarded to the rendered root | Compound components: put the attribute on the **specific part** — `<Dialog.Content data-testid="…">`, `<Table.Row data-testid="…">` |
| **shadcn/ui** | ✅ trivial — the component source is yours; add it directly on the JSX, or thread a `testId` prop | Add directly on the underlying Radix/primitive element in your copied source |
| **none (headless)** | ✅ trivial — it's your JSX | Your primitives take a `testId` prop and compose suffixes (Rule 4) |

After tagging a library control the first time, **verify in the rendered DOM** that the attribute landed on a sensible element — some components forward to an outer wrapper rather than the interactive leaf; tests must know which.

### 2. Naming: `PageOrComponent.ElementType[.Qualifier]`

PascalCase segments, dot-separated. No spaces, no kebab-case, no numeric ids, no array indexes, no enabled/disabled state values.

- **PageOrComponent** — the page locator root, derived from the route turned into PascalCase: `/operations/scheduled-jobs` → `Operations.ScheduledJobs`. If the file has a natural component name (a row, a card), use that.
- **ElementType** — the role: `SubmitButton`, `EmailField`, `Grid`, `Row`, `AddButton`, `Action`, `ConfirmDialog`.
- **Qualifier** *(optional)* — a meaningful semantic value: enum name, field name, action name. Never numeric ids or indexes.

```
Operations.ScheduledJobs.AddButton
Operations.ScheduledJobs.Action.Pause
Operations.ScheduledJobs.Form.Field.Cron
ExposureFeeChargesGrid.Grid
ExposureFeeChargesGrid.Row.Symbol
```

### 3. Extract repeated values into a `const`

When the same locator is used more than once, extract it.

- **Static** → a module-level `const` (PascalCase name).
- **Dynamic** → build inline from data already in scope.

```tsx
const CloseButtonTestId = 'ToastMessage.CloseButton';

<button data-testid={CloseButtonTestId} onClick={close}>×</button>
```

When three or more sites in one file share a screen-scoped prefix, extract a `TestIdPrefix` const and interpolate:

```tsx
const TestIdPrefix = 'Assets.IndexSearch';

<TextField data-testid={`${TestIdPrefix}.Query`} />
<Button data-testid={`${TestIdPrefix}.SubmitButton`}>Search</Button>
<DataGrid data-testid={`${TestIdPrefix}.ResultsGrid`} rows={rows} columns={cols} />
```

Renaming the section becomes a one-line edit instead of grep-and-replace. When composing from an optional prefix prop, use a non-null fallback — never let it collapse to `undefined`:

```tsx
// ✅ always a string
const composedTestId = `${testId ?? ''}.Title`;
<h2 data-testid={composedTestId}>{title}</h2>

// ❌ collapses to a missing attribute
<h2 data-testid={testId ? `${testId}.Title` : undefined}>{title}</h2>
```

### 4. Components compose their suffix

A custom component takes a `testId` prefix and appends its element type:

```tsx
// StatusBadge.tsx
type Props = { testId?: string; status: ItemStatus };

export function StatusBadge({ testId, status }: Props) {
  const composedTestId = `${testId ?? ''}.StatusBadge`;
  return <span data-testid={composedTestId}>{status}</span>;
}
```

Caller passes the **prefix only**:

```tsx
<StatusBadge testId="Order.Header" status={status} />
{/* renders: data-testid="Order.Header.StatusBadge" */}
```

Pass-through wrappers (a component that delegates to another without adding a meaningful role) forward `testId` untouched — only the terminal component appends a suffix. A component that also forwards to a DOM element can accept the standard `'data-testid'` prop directly and spread it (`{...{ 'data-testid': testId }}`) when it's the leaf, or compose a suffix when it owns sub-elements.

### 5. Which elements get a `data-testid`

Apply to:
- Interactive elements: `<button>`, `<a>` used as nav, `<input>`, `<select>`, `<textarea>`, library buttons/inputs/dropdowns/switches/date pickers, menu items.
- List/grid containers: `<table>`, library data grids, custom list roots.
- Read anchors: status badges, computed totals, toast/error banners, empty states, dynamic text a test must read.
- The states of every data region and the app notification surface — `<Region>.Loading`, `<Region>.Error`, `<Region>.Retry`, `<Region>.Empty`, `<Region>.Stale` (data held after a failed refetch), plus `Notifications.Region`, `Notifications.Error`, `Notifications.Error.Close`, `Notifications.Error.CorrelationId`. Without these a test can't tell a *failed* region from an *empty* one, or assert the error notification never auto-dismisses ([`error-handling`](../error-handling/SKILL.md)).

Skip:
- Decorative `<div>`/`<span>` wrappers, layout containers.
- Static `<label>` text already addressable through its associated input.
- Pure styling/icon elements (unless the icon is the interactive target).

### 6. List rows: hardcoded static parent locator

Components rendered repeatedly inside a list **must not** accept a per-row testid prop. The parent locator is a hardcoded `const`, and child elements namespace under it. Tests address individual rows **by index** over the shared selector — never by embedding the row's id/key.

```tsx
// SchedulerRow.tsx
const RowTestId = 'SchedulerRow';

export function SchedulerRow({ model }: { model: SchedulerInfo }) {
  return (
    <tr data-testid={RowTestId}>
      <td data-testid={`${RowTestId}.Name`}>{model.name}</td>
      <td data-testid={`${RowTestId}.Cron`}>{model.cron}</td>
      <td data-testid={`${RowTestId}.Status`}>{model.isPaused ? 'Paused' : 'Active'}</td>
    </tr>
  );
}
```

The React key still uses the **stable domain id** (`key={model.id}` at the call site) — the key and the testid are different concerns: the key must be unique per row, the testid must be **static** so tests can select the set. Never put `model.id` into the locator.

When the same role renders twice in one row, distinguish by sub-namespace: `SymbolListItem.ChangePercent` vs `SymbolListItem.AfterHours.ChangePercent`. For one-off composites (a page header, a summary card), a screen-scoped parent is fine: `Order.Header`, with `Order.Header.Reference`, `Order.Header.Total`.

### 7. Derive locators from render-time data, not lookup tables

When a component renders items from a typed enum/union or carries the identifier in its props, build the testid inline from that data. Do **not** introduce a hand-maintained `Record<Enum, string>` map.

```tsx
// ✅ derived from data already in scope
{sections.map((section) => (
  <Tabs.Trigger key={section} value={section} data-testid={`PortfolioStack.Tab.${section}`}>
    {humanize(section)}
  </Tabs.Trigger>
))}
```

```tsx
// ❌ hand-maintained mapping — drifts when a value is renamed/added
const TabTestIds: Record<PortfolioSection, string> = { … };
```

For string values already in scope (`selectedTab`, `item.label`, `field.name`), interpolate directly: `` `ActivityFilters.${selectedTab}.${item.label}` ``.

**Why:** lookup tables drift — a new value silently falls through to a default; a renamed value leaves a stale entry. Direct interpolation binds the locator to the source identifier so renames propagate automatically.

## Page locator derivation

Default: turn the route into PascalCase, dropping a leading area segment if the whole app lives under it (e.g. `/admin`).

| Route | Page locator root |
|---|---|
| `/operations/scheduled-jobs` | `Operations.ScheduledJobs` |
| `/trade/exposure-day-count-settings` | `Trade.ExposureDayCountSettings` |
| `/users/[id]` | `Users.Detail` (drop route params; use a meaningful suffix) |
| `/` | `Home` |

If the page has a single dominant component (a header card, a wizard step), prefer that component's name as the root.

## Generated / mapped UIs (config-driven shells)

Many apps render CRUD through a config/schema-driven framework (a generic `<CrudList>` / `<CrudForm>` driven by an entity descriptor), leaving route files as thin shells with nothing to attribute. Do **not** tag such pages one by one — **edit the framework components once** so they emit systematic testids derived from the config:

| Framework surface | Emit |
|---|---|
| List/grid root | `{Entity}.Grid` |
| Row element | `{Entity}.Row` |
| Add button | `{Entity}.AddButton` |
| Built-in Edit / Delete row buttons | `{Entity}.Builtin.Edit` / `{Entity}.Builtin.Delete` |
| Custom action button | `{Entity}.Action.{ActionName}` |
| Form field | `{Entity}.Form.Field.{FieldName}` |
| Form submit / cancel | `{Entity}.Form.Submit` / `{Entity}.Form.Cancel` |
| Action-dialog field / confirm / cancel | `{Entity}.Action.{ActionName}.Field.{FieldName}` / `.Confirm` / `.Cancel` |

> Built-ins sit under `.Builtin.*` so a custom action named `Edit`/`Delete` never collides with the framework's row buttons — custom verbs always use `.Action.{Name}`.

Every config-driven page becomes selectable with zero per-page work. Hand-rolled pages (dashboards, wizards) follow Rules 1–7 directly.

## Consuming a `missing-testids.md` report

When QA's `page-objects-from-url` hands over a report of elements it could not locate testid-first:

1. Treat each listed element as a Rule 5 candidate; derive its locator per Rules 2–7.
2. Elements the report lists but Rule 5 classifies as decorative: don't tag — note them in the response so QA can re-anchor.
3. Report back locator counts + collisions (see the contract below) so QA can regenerate the page objects.

## Procedure when invoked

1. Confirm scope: a single file, a directory, a feature area, or a `missing-testids.md` report. Do not silently rewrite the whole tree.
2. For each target `.tsx` file:
   1. Determine the page locator root (route-derived or component-derived).
   2. Walk the JSX. For each candidate element (Rule 5), generate the locator and apply it via the right mechanism (inline attribute, library slot/rest-prop, `testId` prefix prop, hardcoded row const).
   3. Skip decorative elements; note them in the summary.
3. If the target is a config-driven shell, do **not** touch the page — propose edits to the framework components in a separate diff.
4. Type-check / build the touched project (`pnpm tsc --noEmit`) to confirm nothing broke.
5. Report per the contract:
   - Files modified, with locator counts per file.
   - Decorative elements skipped (so the user can override if any need anchoring).
   - **Locator collisions detected (same testid on two distinct elements) — these block completion.**

## Anti-patterns to flag

| Anti-pattern | Fix |
|---|---|
| `data-testid={`Row.${model.id}`}` on a list row | Hardcode the static row locator (Rule 6) |
| `data-testid` on a layout `<div>` with no test purpose | Remove |
| `Record<Enum, string>` mapping enum → testid | Replace with inline `` `…${enumValue}` `` (Rule 7) |
| Ternary collapsing to `undefined` | Use `?? ''` and a named local (Rule 3) |
| New `AppButton`/`AppTextField` wrapper introduced just to carry testids | Set the inline attribute on the library control — its rest-prop spread forwards it (Rule 1) |
| Two distinct elements sharing one locator | Sub-namespace one of them (Rule 6) |
| kebab-case or snake_case segments | PascalCase only |
| Locators containing numeric ids, GUIDs, or array indexes | Use enum/field names; rows are addressed by index over a shared static locator |
| Array index reused as both React `key` and testid qualifier | `key` = stable domain id; testid = static role — different concerns |
| `aria-label` added to mirror a testid | One attribute only — a11y labels belong to [`accessibility`](../accessibility/SKILL.md) |

## Out of scope

Non-React surfaces (a static-HTML admin tool, a jQuery-era template UI, a raw `innerHTML` widget) are **not** covered here — this skill owns `.tsx` component markup only. A React app renders everything through React, so there is no in-app hybrid surface to address (this is the deliberate delta from `frontend/blazor/skills/test-ids`, whose `references/static-html.md` exists because a Blazor app can ship a non-Blazor page beside it). If a project genuinely mixes a non-React island in, apply the same rules — naming (Rule 2), const prefix (Rule 3), static row locators (Rule 6), data derivation (Rule 7) — with a plain inline `data-testid` attribute and a hardcoded parent-locator `const` for JS-rendered rows.

## Handoffs

- Page objects / UI tests against these locators → `qa-ui-typescript` (peer agent; `page-objects-from-url` locates data-testid-first)
- Scaffolding new components (testids emitted by default) → [`component-writer`](../component-writer/SKILL.md)
- Per-library control mechanics / choosing the library → [`component-library`](../component-library/SKILL.md)
- Responsive variant-suffixed testids (visible vs hidden layout) → [`responsive-design`](../responsive-design/SKILL.md)
- Reviewing testid hygiene as part of a broader review → [`code-review`](../code-review/SKILL.md)
- Accessible labels (not the same as testids) → [`accessibility`](../accessibility/SKILL.md)
