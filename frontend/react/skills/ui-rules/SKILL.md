---
name: ui-rules
description: Use when building a data-driven React feature, for UI correctness (humanized enums, formats, stable sort, paging, CRUD parity). Triggers "enum shows as a number". Not for fetching (data-fetching).
disable-model-invocation: true
---

# React — UI Conventions (data-driven correctness)

Cross-cutting UI-correctness conventions for **any data-driven web application**, wherever the app shows grids/lists, edits entities, or exposes state-changing actions. Every rule traces to a real defect class, not taste, and **loads on every feature build**: they keep a hundred pages consistent instead of a hundred slightly-different pages.

The standards are the fe-react rule files `react.md` and `react-forms.md` (`.claude/rules/fe-react/` in the project, or `frontend/react/skills/rules/` until `/fe-react:rules` installs them); where they disagree with this skill, the rule files win. The sections below are the detail behind them, and own what they leave out: bulk operations, navigation, footers, the modal-or-route choice and the systemic fix.

**Version rule:** the conventions are **version-agnostic** across React 18/19 and Next 14/15; the owning sibling skill carries the version note for a version-sensitive mechanism.

## What this skill owns vs. its siblings

The conventions split across the feature-build skills by domain; this skill owns the **display, edit, action, table, and IA correctness** layer. Its siblings own the rest — don't duplicate:

| Concern | Owner |
|---|---|
| Fetch/mutation mechanics, caching/revalidation, RSC vs client data lane, DTO shape | [`data-fetching`](../data-fetching/SKILL.md) |
| Error rendering, three-state regions, empty-state UX, retry | [`error-handling`](../error-handling/SKILL.md) |
| Real-`<Link>` navigation over `router.push`, route-title *emission*, the new-tab affordance + `rel` | [`component-writer`](../component-writer/SKILL.md) |
| Field-level validation UX, RHF+Zod, Server-Action forms | [`forms`](../forms/SKILL.md) |
| Accessible labels, contrast, color-not-alone, focus trap/restore, landmarks | [`accessibility`](../accessibility/SKILL.md) |
| Nav collapse / hamburger breakpoint, table→card, sticky header | [`responsive-design`](../responsive-design/SKILL.md) |
| Stable `data-testid` on grids/actions/selection | [`test-ids`](../test-ids/SKILL.md) |
| Auth/session lifecycle | `auth/auth0-react` |
| Config hygiene (no hardcoded hosts) | [`project-setup`](../project-setup/SKILL.md) |
| **Everything below** | **this skill** |

## 1. Display correctness

The layer decides how a stored value becomes a shown value. The failures are all "technically rendered, semantically wrong."

### Enums / unions — humanize in *every* render path

- **Never show a raw enum integer.** If the API models an enum as an int, the display layer owns a value→label map (watch codegen that emits int enums as numbers — `1` instead of `Active`).
- **Humanize PascalCase / snake values** (`PartiallyFilled` → "Partially Filled") through **one shared helper** (`humanize()` / a label map colocated with the type).
- **Apply it in every render path** — grid cells, grid *filters*, detail panes, forms, badges. The classic bug: only the form humanizes, so the same value reads three different ways across the app.
- **Derive the map from the type itself** (a `satisfies Record<Union, string>` label map next to the type, exhaustively checked) — never a hand-maintained map that drifts on rename (mirrors [`test-ids`](../test-ids/SKILL.md)'s derive-don't-hardcode rule; a `satisfies` on a union makes a new member a compile error until labeled).
- **When you patch one entity's enum display, sweep its siblings** — child/related entities with the same enum are routinely missed.

### Formatting — one canonical format per type, centralized

Define **one** format per data type app-wide and centralize it (shared `format*` helpers, an `Intl` wrapper):

| Type | One rule, app-wide |
|---|---|
| Date | one format (e.g. ISO `yyyy-MM-dd`) |
| Date-time | one format; one decision on seconds (grids vs details match, or differ *by rule* not accident) |
| Money | one amount+currency layout, one precision (`Intl.NumberFormat` with `style: 'currency'`) |
| Percent | one precision, one spacing |
| Domain precision (FX rate, weight…) | defined once, not per page |

- **Always label the timezone** (or convert consistently). Mixing UTC / local / relative-age unlabeled is a correctness hazard.
- **Hand-written pages use the same format helpers as generated pages** — inline `` `${value}%` `` / hand-rolled `toLocaleString` calls are where every deviation lives.
- **Every renderer implements the full display-token set.** If one cell renderer supports `date:ISO`/`multiline`/`email` and another falls through to `String(value)`, fields render raw depending on which page shows them. Share the token→render logic in one place (see §8).

### Identifiers & foreign keys — names, not ids

- **Never show a raw GUID / surrogate id where a name exists.** If a field is a lookup FK, the **list** renderers must resolve it too, not just the forms. Render the resolved name; demote the id to a tooltip + copy affordance.
- **Composite human keys beat surrogate keys in cells** (`SYMBOL.EXCHANGE` reads; a uuid never does).
- **Build a small cached identity directory** (id → name/label, via a TanStack Query cache over existing list endpoints) for cross-cutting resolution in hand-written grids and pickers.
- **Pickers are human-first:** type-ahead over name/label (id accepted as input, not the primary display); auto-resolve when unambiguous.

---

## 2. Table ergonomics

- **Deterministic sort, always.** Every list needs a default **server-side** `ORDER BY` with a **unique tiebreaker** (e.g. `createdAt DESC, id`). Without it, edited rows jump position after refetch and **paging duplicates/drops rows**. Wire the default sort through the shared grid config so every page gets it.
- **Numbers right-align** (integers too, not just decimals).
- **Cap column widths, truncate long text** (~30 chars + ellipsis) with the full value in a tooltip / detail pane. Never dump a document body, hash, or free-text blob into a cell.
- **Server-side paging with page-size options** for real datasets — don't load an entire result set into the client for some grids while others page server-side. (Virtualization/perf: [`performance`](../performance/SKILL.md).)
- **Filter parity:** if shared grids offer per-column filters, hand-written grids must too — especially the columns users most need (a status badge you can't filter by status is a recurring miss).
- **Consistent sortability within a grid** — mixed sortable/unsortable columns with no rationale reads as broken.
- **Consistent row→detail affordance** across grids — same view/link everywhere a detail page exists (a real `<Link>`, [`component-writer`](../component-writer/SKILL.md)).
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

- **A form renders only fields that actually persist.** If the update mapper ignores a target, the field must not be editable — an edit that shows a success toast and discards the value is the worst form defect. **Cross-check form fields ↔ update-DTO properties ↔ mapper mechanically** (the Zod schema ↔ the DTO type ↔ the API contract — a test can diff them).
- **Immutable / PK fields are read-only in edit.** Server-side re-stamping of the key means an editable key field is a silent no-op.
- **State transitions are explicit actions, never an editable `Status`/`Stage` `<select>`** — a dropdown bypasses the transition's side effects (timestamps, notifications, guards). Remove the field; force the action (§4).
- **Prefer patch payloads (partial + only-changed) or subset "Mod" DTOs** — a subset type gives field gating *by construction*: immutable fields simply don't exist on the edit type, so TypeScript won't let the form bind them.
- **Full-replace (PUT) edits need optimistic concurrency** (RowVersion / ETag + `If-Match`). Read-prefill-then-PUT-everything silently overwrites concurrent changes made between form-open and save.
- **Write paths enforce the same domain guards as self-service paths** (uniqueness, verified-field locks). A management endpoint that bypasses them creates inconsistent state.
- **Complex object fields need real sub-forms** — an object-typed field falling to a text input renders `[object Object]` and can't round-trip (uneditable while looking editable).
- **Compliance-sensitive flags (consent, verification) are read-only or behind an explicit audited action** with a mandatory reason — never a plain checkbox.
- **Don't render an Add/Create button whose endpoint isn't implemented** — a guaranteed 500 on a primary button is a broken promise. (Field-validation UX itself: [`forms`](../forms/SKILL.md).)

### Write-path / column completeness

- **Never ship a grid column the write path never populates.** For every listed field, verify some code path stamps it — the classic failure: the read path maps a column, but the create path's payload/mapper never sets it, so it's `null` on every row in every environment.
- **Structured data belongs in structured columns** — if the grid's purpose is showing a value or a state transition, it's a real column, not free text in a notes field.
- **Stamp correlation/audit fields at write time** (user id, correlation id, previous/new state) from the context that has them; backfill when adding a column.

---

## 4. State-dependent actions & confirmations

- **Disable, don't hide.** Actions that appear/disappear by state cause blank action cells, layout shift, and hide capability discovery. Render the action **disabled with a why-tooltip** (`title` / an accessible tooltip, `aria-disabled` where a native `disabled` swallows focus).
- **Don't swap a control's meaning in place** (one button toggling approve↔unapprove via icon/color). Use two labeled actions or an explicit toggle.
- **Never render an action the backend will always reject in that state.** Gate enablement from the **same state machine the backend enforces** — a missing gate = renders everywhere = guaranteed rejected clicks.
- **Every backend-mandated follow-up has a UI affordance.** If the server says "create a new version instead," the UI must offer that path (e.g. "Copy as new version," prefilled, key fields cleared). An error naming an action the UI doesn't offer is a design bug.
- **Audit the full state machine** — every state reachable, every transition exposed (or explicitly out of scope). Dead states and untriggerable transitions are defects.

### Destructive-action confirmations

- **Every destructive action confirms** — no exception for "small" ones (cancel/deactivate). Use a real confirm dialog, never the browser's blocking `window.confirm`.
- **The confirmation restates the action and names the specific object** by its friendly label — "Delete margin group **'EU Equities'**?" — never the raw type + id, never a bare "Are you sure?".
- **The confirm button is verb-labeled and danger-styled** ("Delete group," red), not a neutral "OK." A warning title with a neutral confirm button sends a mixed signal.

---

## 5. Bulk operations

A multi-select or a bulk action in the task → read [`references/bulk-operations.md`](references/bulk-operations.md).

---

## 6. Information architecture & consistency

- **One name → one concept.** Two pages with identical titles over different entities must be disambiguated in the **title itself**, not just the nav group above them.
- **One verb per operation app-wide.** The same corrective concept must not be "Cancel" / "Mark as Failed" / "Disapprove" / "Resolve" on four sibling pages.
- **A title on every route** — `metadata`/`generateMetadata` (App Router) or `react-helmet` (SPA); browser tabs full of the same generic title are unusable. (This skill mandates the *convention*; [`component-writer`](../component-writer/SKILL.md) *emits* it so pages get it for free.)
- **One breadcrumb source** — global auto-breadcrumbs *or* per-page bars, never both; segments show friendly names, not raw id URL segments.
- **Standardize the small stuff once:** one dialog-width scale, one page-header treatment, one date-range-filter component, one filter-trigger label.
- **Delete dead pages and duplicate routes;** consolidate near-duplicate grids (two tables sharing ~12 fields with drifted column order → one column definition).

### Navigation and footers

A nav menu, breadcrumbs or a footer in the task → read [`references/navigation-and-footers.md`](references/navigation-and-footers.md).

---

## 7. Choosing the surface — modal, page, or new tab

A modal, a drawer, or a link that may open a new tab in the task → read [`references/surface-choice.md`](references/surface-choice.md).

---

## 8. Systemic — component/renderer unification & the highest-leverage fix

This is *why* the rules above are keepable at scale, not one-offs.

- **Most app-wide inconsistency traces to renderer divergence.** N grid/cell renderers (a MUI DataGrid here, a hand-rolled `<table>` there, a config-driven list elsewhere) means every display rule — enums, formats, links, loading, truncation — is implemented **0–1 times instead of once**. Consolidate to **one cell-renderer + one grid config** that hand-written pages *compose* rather than reimplement.
- **The shared grid/region component owns the three states** (loading / failed / loaded) and takes the response-dependent body only — the search bar, filters and toolbar are the *page's*, above it, so a failed load empties the rows without unmounting the controls. Bind once there and every list gets correct failure scoping for free ([`error-handling`](../error-handling/SKILL.md) owns the states and the persistent top-right notification that accompanies them).
- **Fix at the highest-leverage point, in order:** (1) safety-critical gaps (missing confirmations, raw error dumps); (2) **one-change-fixes-all shared bindings** (loading state, lookup resolution, route titles, action labels); (3) per-page standardization (filters, page sizes, vocabulary).
- **Treat a config-driven patch layer as a bug report against the framework component.** The patch fixes today's page; the framework fix kills the defect *class*.
- **Sweep, don't spot-fix.** Every hand-found defect ("this page crashes on a missing lookup key") is a *class* ("which other pages index that key?"). Audit the class before closing the ticket.

---
