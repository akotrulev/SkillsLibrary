---
name: ui-rules
description: Use when building a data-driven Blazor feature, for UI correctness (humanized enums, formats, stable sort, paging, CRUD parity). Triggers "enum shows as a number". Not for fetching (data-fetching).
disable-model-invocation: true
---

# Blazor — UI Conventions (data-driven correctness)

Cross-cutting UI-correctness conventions for any data-driven web application, wherever the app shows grids/lists, edits entities, or exposes state-changing actions. Every rule here traces to a real defect class. Loaded on every feature build, so a hundred pages stay consistent.

**Version rule:** these conventions are version-agnostic across net8/net9/net10; where a mechanism is version-sensitive (`<PageTitle>`, `[PersistentState]`) the owning sibling skill carries the version note.

## What this skill owns vs. its siblings

This skill owns the **display, edit, action, table, and IA correctness** layer; its siblings own the rest:

| Concern | Owner |
|---|---|
| Route/descriptor integrity, deserialization shape, contract-testing DTOs | [`data-fetching`](../data-fetching/SKILL.md) (§1–2) |
| Error rendering, three-state regions, empty-state UX, categorized invoker | [`error-handling`](../error-handling/SKILL.md) (§3–4) |
| Real-anchor navigation (`<a href>` over `NavigateTo`), `<PageTitle>` *emission* | [`component-writer`](../component-writer/SKILL.md) (§8, §15-emit) |
| Accessible labels, contrast, color-not-alone | [`accessibility`](../accessibility/SKILL.md) (§16) |
| Auth/session lifecycle | `auth/auth0-blazor` (§17) |
| Config hygiene (no hardcoded hosts) | [`project-setup`](../project-setup/SKILL.md) (§18) |
| **Everything below** | **this skill** |

## 1. Display correctness

The layer decides how a stored value becomes a shown value. The failures are all "technically rendered, semantically wrong."

### Enums — humanize in *every* render path

- **Never show a raw enum integer.** If the API models an enum as an int, the display layer owns a value→name map (watch generators that emit int enums as numbers — `1.00` instead of `Active`).
- **Humanize PascalCase names** (`PartiallyFilled` → "Partially Filled") through **one shared helper**.
- **Apply it in every render path** — grid cells, grid *filters*, detail panes, forms, secondary/extended renderers. The classic bug: only the form renderer humanizes, so the same value reads three different ways across the app.
- **Derive the map from the enum itself** (`Enum.GetValues`, `[Display]`/`[Description]` attributes) — never a hand-maintained `Dictionary<TEnum,string>` that drifts on rename (mirrors [`test-ids`](../test-ids/SKILL.md)'s derive-don't-hardcode rule).
- **When you patch one entity's enum display, sweep its siblings** — child/related entities with the same enum are routinely missed.

### Formatting — one canonical format per type, centralized

Define **one** format per data type app-wide and centralize it in shared helpers:

| Type | One rule, app-wide |
|---|---|
| Date | one format (e.g. ISO `yyyy-MM-dd`) |
| Date-time | one format; one decision on seconds (grids vs details match, or differ *by rule* not accident) |
| Money | one amount+currency layout, one precision |
| Percent | one precision, one spacing |
| Domain precision (FX rate, weight…) | defined once, not per page |

- **Always label the timezone** (or convert consistently). Mixing UTC / local / relative-age unlabeled is a correctness hazard.
- **Hand-written pages use the same format helpers as generated pages** — hand-rolled `string.Format` is where every deviation lives.
- **Every renderer implements the full display-token set.** If one renderer supports `date:ISO`/`multiline`/`email` and another falls through to `.ToString()`, fields render raw depending on which page shows them. Share the token→render logic in one place (see §5, renderer unification).

### Identifiers & foreign keys — names, not GUIDs

- **Never show a raw GUID where a name exists.** If metadata declares a lookup for a field, the **list** renderers must resolve it too, not just the forms. Render the resolved name; demote the GUID to a tooltip + copy affordance.
- **Composite human keys beat surrogate keys in cells** (`SYMBOL.EXCHANGE` reads; a uuid never does).
- **Build a small cached identity directory** (id → name/label) over existing list endpoints for cross-cutting resolution in hand-written grids and pickers.
- **Pickers are human-first:** type-ahead over name/label (GUID accepted as input, not the primary display); auto-resolve when unambiguous.

---

## 2. Table ergonomics

- **Deterministic sort, always.** Every list needs a default **server-side** `ORDER BY` with a **unique tiebreaker** (e.g. `CreatedAt DESC, Id`). Without it, edited rows jump position after reload (the DB may physically relocate updated rows) and **paging duplicates/drops rows**. Wire the default sort through the shared renderer so every page gets it.
- **Numbers right-align** (integers too, not just decimals).
- **Cap column widths, truncate long text** (~30 chars + ellipsis) with the full value in a tooltip / detail pane. Never dump a document body, hash, or free-text blob into a cell.
- **Page-size options, server-side paging** for real datasets. Don't load an entire result set client-side in some grids while others page server-side. (Perf side of virtualization: [`performance`](../performance/SKILL.md).)
- **Filter parity:** if shared grids offer per-column filters, hand-written grids must too — especially the columns users most need (a status badge you can't filter by status is a recurring miss).
- **Consistent sortability within a grid** — mixed sortable/unsortable columns with no rationale reads as broken.
- **Consistent row→detail affordance** across grids — same view/link everywhere a detail page exists.
- **Sticky header row** on any table that scrolls past a screen — a column you cannot name is a column you cannot read. (Reflow/stickiness mechanics: [`responsive-design`](../responsive-design/SKILL.md).)
- **Selection is signalled by the row, not only the checkbox** — a selected row carries a background/border change; a 16-px tick is not a state indicator. Selection **survives paging** within one task, and the count of what is selected is always visible.
- **Bulk actions appear as a contextual toolbar on selection**, above the table, and disappear with it — not a permanently-rendered row of buttons that are disabled most of the time.
- **Quick filters apply instantly; advanced filters get an Apply.** A single-value toggle re-queries on click; a multi-condition builder waits for a deliberate submit. An **Apply button on a quick filter is a known confusion source** — users cannot tell whether the click took.
- **Active filters render as removable chips** with a count and a clear-all, above the data region so a failed load never unmounts them.
- **Inline edit for the repeated, high-frequency change** (§7's surface rule) — and an inline edit commits or cancels explicitly; a row that saves on blur loses work to a stray click.
- **Row actions live behind one compliant trigger when space is tight** — an overflow menu with a ≥24×24 CSS px target beats four 16-px icons crammed into a compact row (sizing rule: `design/accessible-by-design`).

---

## 3. CRUD & edit semantics

The highest-severity defect class: an edit that **looks** like it worked and silently didn't.

- **A form renders only fields that actually persist.** If the update mapper ignores a target, the field must not be editable — an edit that shows a success toast and discards the value is the worst form defect. **Cross-check form fields ↔ update-DTO properties ↔ mapper ignore-list mechanically** (a test can do this).
- **Immutable / PK fields are read-only in edit.** Server-side re-stamping of the key means an editable key field is a silent no-op.
- **State transitions are explicit actions, never an editable `Status`/`Stage` dropdown** — a dropdown bypasses the transition's side effects (timestamps, notifications, guards). Remove the field; force the action (§4).
- **Prefer patch DTOs (nullable + only-non-null) or subset "Mod" DTOs** — a subset DTO gives field gating *by construction*: immutable fields simply don't exist on the edit contract.
- **Full-PUT edits need optimistic concurrency** (RowVersion / ETag + `If-Match`). Read-prefill-then-PUT-everything silently overwrites concurrent changes made between dialog-open and save.
- **Write paths enforce the same domain guards as self-service paths** (uniqueness, verified-field locks). A management endpoint that bypasses them creates inconsistent state.
- **Complex object fields need real sub-forms** — an `object`-typed field falling to a text box renders `ToString()` and can't round-trip (uneditable while looking editable).
- **Compliance-sensitive flags (consent, verification) are read-only or behind an explicit audited action** with a mandatory reason — never a plain checkbox.
- **Don't render an Add/Create button whose endpoint isn't implemented** — a guaranteed 500 on a primary button is a broken promise. (Field-validation UX itself: [`forms`](../forms/SKILL.md).)

### Write-path / column completeness

- **Never ship a grid column the write path never populates.** For every listed field, verify some code path stamps it — the classic failure: the read path maps a column, but the create path's DTO/mapper never sets it, so it's NULL on every row in every environment.
- **Structured data belongs in structured columns** — if the grid's purpose is showing a value or a state transition, it's a real column, not free text in a notes field.
- **Stamp correlation/audit fields at write time** (user id, correlation id, previous/new state) from the context that has them; backfill when adding a column.

---

## 4. State-dependent actions & confirmations

- **Disable, don't hide.** Actions that appear/disappear by state cause blank action cells, layout shift, and hide capability discovery. Render the action **disabled with a why-tooltip**.
- **Don't swap a control's meaning in place** (one button toggling approve↔unapprove via icon/color). Use two labeled actions or an explicit toggle.
- **Never render an action the backend will always reject in that state.** Gate enablement from the **same state machine the backend enforces** — a `null` gate = renders everywhere = guaranteed rejected clicks.
- **Every backend-mandated follow-up has a UI affordance.** If the server says "create a new version instead," the UI must offer that path (e.g. "Copy as new version," prefilled, key fields cleared). An error naming an action the UI doesn't offer is a design bug.
- **Audit the full state machine** — every state reachable, every transition exposed (or explicitly out of scope). Dead states and untriggerable transitions are defects.

### Destructive-action confirmations

- **Every destructive action confirms** — no exception for "small" ones (cancel/deactivate).
- **The confirmation restates the action and names the specific object** by its friendly label — "Delete margin group **'EU Equities'**?" — never the raw type + key, never a bare "Are you sure?".
- **The confirm button is verb-labeled and danger-styled** ("Delete group," red), not a neutral "OK." A warning title with a neutral confirm button sends a mixed signal.

---

## 5. Bulk operations

- **Multi-select needs visible affordances:** a leading **checkbox column** (row-click-only selection is undiscoverable), a **tri-state select-all** header, selection styling stronger than hover (background tint + accent bar), and a persistent **selected-count**.
- **Select-all scopes to the visible, filtered page** when filtering/paging is server-side — never silently select rows the user isn't looking at. Tooltip it: "Select all visible rows (respects current filters)."
- **Where users grind row-by-row** (approve/cancel/resolve backlogs), provide **batch endpoints + bulk UI** — thirty click-confirm cycles for one logical operation is a workflow defect.
- **Stable test ids on selection controls** so UI automation can drive bulk flows ([`test-ids`](../test-ids/SKILL.md)).

---

## 6. Information architecture & consistency

- **One name → one concept.** Two pages with identical titles over different entities must be disambiguated in the **page title itself**, not just the nav group above them.
- **One verb per operation app-wide.** The same corrective concept must not be "Cancel" / "Mark as Failed" / "Disapprove" / "Resolve" on four sibling pages.
- **`<PageTitle>` on every page** — browser tabs full of the same generic title are unusable. (This skill mandates the *convention*; [`component-writer`](../component-writer/SKILL.md) *emits* it from the shared page/renderer so generated pages get it free.)
- **One breadcrumb source** — global auto-breadcrumbs *or* per-page bars, never both; segments show friendly names, not raw GUID URL segments.
- **Standardize the small stuff once:** one dialog-width scale, one page-header treatment, one date-range-filter component, one filter-trigger label.
- **Delete dead pages and duplicate routes;** consolidate near-duplicate grids (two tables sharing ~12 fields with drifted column order → one field definition).

**Navigation menus, breadcrumbs and footers** → when the task adds or changes one, read [`references/navigation-and-surfaces.md`](references/navigation-and-surfaces.md) (Navigation, Footers).

## 7. Choosing the surface — modal, page, or new tab

The task opens a modal, drawer, separate page or a link in a new tab → read [`references/navigation-and-surfaces.md`](references/navigation-and-surfaces.md) (Choosing the surface) and decide the surface before you build.


---

## 8. Systemic — renderer unification & the highest-leverage fix

- **Most app-wide inconsistency traces to renderer divergence.** N grid renderers (rich generated / lean generated / hand-written) means every display rule — enums, formats, links, loading, truncation — is implemented **0–1 times instead of once**. Consolidate to **one renderer core** that hand-written pages *compose* rather than reimplement.
- **Fix at the highest-leverage point, in order:** (1) safety-critical gaps (missing confirmations, raw error dumps); (2) **one-change-fixes-all renderer bindings** (loading state, lookup resolution, page titles, action labels); (3) per-page standardization (filters, page sizes, vocabulary).
- **Treat a generated-descriptor patch layer as a bug report against the generator.** The patch fixes today's page; the generator fix kills the defect *class*.
- **Sweep, don't spot-fix.** Every hand-found defect ("this page crashes on a missing route key") is a *class* ("which other pages index that key?"). Audit the class before closing the ticket.

---

## Rules

The standards this skill's output must meet are the fe-blazor rule files, not a list here: `blazor-ui.md`, `blazor-forms.md` and `blazor-markup.md`. Read the project's copy in `.claude/rules/fe-blazor/`, or the plugin's in `frontend/blazor/skills/rules/` when the project has not installed them (`/fe-blazor:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Validation

- Grep for raw enum/`ToString()` in cells; every enum renders humanized in grid, filter, detail, and form.
- One format helper per type; a page audit shows no hand-rolled `string.Format`; timezones labeled.
- No GUID visible where a lookup exists; pickers type-ahead by name.
- Every list has a default server sort with a unique tiebreaker; reload after an edit → no row jumps; page 2 has no dupes from page 1.
- Mechanical form↔DTO↔mapper parity check passes; PKs read-only; no editable `Status`; full-PUT sends `If-Match`.
- Every destructive action shows a named-object confirmation; disabled actions have why-tooltips.
- Bulk flows: checkbox column present, select-all scoped to filter, selected-count shown, batch endpoint used.
- `<PageTitle>` on every route; no duplicate titles for distinct concepts; nav groups within budget; no dead routes.
- Every item in `references/navigation-and-surfaces.md` that applies to the task passes.
