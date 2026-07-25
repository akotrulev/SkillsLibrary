---
name: fe-react-ui-conventions
description: Use on every data-driven feature build for UI correctness — display (humanized enums, one format per type, names not raw ids), table ergonomics (deterministic sort, server paging, filter parity), CRUD semantics (form↔DTO parity, read-only PKs, optimistic concurrency), disable-don't-hide, confirmations, IA. Triggers "review this grid/form", "the enum shows as a number", "an edit discards a field", "the list order changes every refresh". Not for fetch mechanics (`data-access`).
---

# React — UI Conventions (data-driven correctness)

Cross-cutting UI-correctness conventions for **any data-driven web application** — customer-facing or internal — wherever the app shows grids/lists, edits entities, or exposes state-changing actions. Every rule here traces to a real defect class, not taste. **Loaded on every feature build**, not conditionally: these are the rules that keep a hundred pages consistent instead of a hundred slightly-different pages.

**Version rule:** these are UI-correctness conventions, **version-agnostic** across React 18/19 and Next 14/15. Where a mechanism is version-sensitive (the route title via `metadata` vs `react-helmet`, RSC vs client rendering) the owning sibling skill carries the version note; this skill states the *convention*.

## What this skill owns vs. its siblings

The conventions split across the feature-build skills by domain; this skill owns the **display, edit, action, table, and IA correctness** layer. Its siblings own the rest — don't duplicate:

| Concern | Owner |
|---|---|
| Fetch/mutation mechanics, caching/revalidation, RSC vs client data lane, DTO shape | [`data-access`](../data-access/SKILL.md) |
| Error rendering, three-state regions, empty-state UX, retry | [`error-resilience`](../error-resilience/SKILL.md) |
| Real-`<Link>` navigation over `router.push`, route-title *emission*, the new-tab affordance + `rel` | [`generator`](../generator/SKILL.md) |
| Field-level validation UX, RHF+Zod, Server-Action forms | [`forms`](../forms/SKILL.md) |
| Accessible labels, contrast, color-not-alone, focus trap/restore, landmarks | [`accessibility`](../accessibility/SKILL.md) |
| Nav collapse / hamburger breakpoint, table→card, sticky header | [`responsive-design`](../responsive-design/SKILL.md) |
| Stable `data-testid` on grids/actions/selection | [`testability`](../testability/SKILL.md) |
| Auth/session lifecycle | `auth/auth0-react` |
| Config hygiene (no hardcoded hosts) | [`project-scaffold`](../project-scaffold/SKILL.md) |
| **Everything below** | **this skill** |

## When to use

- Building or reviewing any grid, list, detail pane, or edit form
- An enum renders as a number; a GUID shows where a name should; formats vary page-to-page
- Rows reorder/duplicate across paging or after an edit
- An edit succeeds but a value doesn't stick; a Status `<select>` bypasses transition logic
- A destructive action fires without confirming what it hits
- The same concept is named/verbed differently across pages

## When NOT to use

- The mechanics of fetching, mutating, caching → [`data-access`](../data-access/SKILL.md)
- Rendering the failed/empty states themselves → [`error-resilience`](../error-resilience/SKILL.md)
- Making navigation a real `<Link>` / emitting the route title → [`generator`](../generator/SKILL.md)
- Field-level validation UX → [`forms`](../forms/SKILL.md)
- A11y labels + contrast → [`accessibility`](../accessibility/SKILL.md)

---

## 1. Display correctness

The layer decides how a stored value becomes a shown value. The failures are all "technically rendered, semantically wrong."

### Enums / unions — humanize in *every* render path

- **Never show a raw enum integer.** If the API models an enum as an int, the display layer owns a value→label map (watch codegen that emits int enums as numbers — `1` instead of `Active`).
- **Humanize PascalCase / snake values** (`PartiallyFilled` → "Partially Filled") through **one shared helper** (`humanize()` / a label map colocated with the type).
- **Apply it in every render path** — grid cells, grid *filters*, detail panes, forms, badges. The classic bug: only the form humanizes, so the same value reads three different ways across the app.
- **Derive the map from the type itself** (a `satisfies Record<Union, string>` label map next to the type, exhaustively checked) — never a hand-maintained map that drifts on rename (mirrors [`testability`](../testability/SKILL.md)'s derive-don't-hardcode rule; a `satisfies` on a union makes a new member a compile error until labeled).
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
- **Consistent row→detail affordance** across grids — same view/link everywhere a detail page exists (a real `<Link>`, [`generator`](../generator/SKILL.md)).

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

- **Multi-select needs visible affordances:** a leading **checkbox column** (row-click-only selection is undiscoverable), a **tri-state select-all** header, selection styling stronger than hover (background tint + accent bar), and a persistent **selected-count**.
- **Select-all scopes to the visible, filtered page** when filtering/paging is server-side — never silently select rows the user isn't looking at. Tooltip it: "Select all visible rows (respects current filters)."
- **Where users grind row-by-row** (approve/cancel/resolve backlogs), provide **batch endpoints + bulk UI** — thirty click-confirm cycles for one logical operation is a workflow defect.
- **Stable `data-testid` on selection controls** so UI automation can drive bulk flows ([`testability`](../testability/SKILL.md)).

---

## 6. Information architecture & consistency

- **One name → one concept.** Two pages with identical titles over different entities must be disambiguated in the **title itself**, not just the nav group above them.
- **One verb per operation app-wide.** The same corrective concept must not be "Cancel" / "Mark as Failed" / "Disapprove" / "Resolve" on four sibling pages.
- **A title on every route** — `metadata`/`generateMetadata` (App Router) or `react-helmet` (SPA); browser tabs full of the same generic title are unusable. (This skill mandates the *convention*; [`generator`](../generator/SKILL.md) *emits* it so pages get it for free.)
- **One breadcrumb source** — global auto-breadcrumbs *or* per-page bars, never both; segments show friendly names, not raw id URL segments.
- **Standardize the small stuff once:** one dialog-width scale, one page-header treatment, one date-range-filter component, one filter-trigger label.
- **Delete dead pages and duplicate routes;** consolidate near-duplicate grids (two tables sharing ~12 fields with drifted column order → one column definition).

### Navigation

- **Always indicate the current location.** The single most common nav defect is failing to show where the user is now — highlight the active nav item with a **distinct state that isn't color alone** (weight, an indicator bar, `aria-current="page"`), and add breadcrumbs on deep hierarchies. (`NavLink`'s active state / `usePathname` is the hook; the not-color-alone + `aria-current` a11y side is [`accessibility`](../accessibility/SKILL.md)'s.)
- **Group and label over count — the "7 items max" rule is a myth.** Menus rely on *recognition*, not recall; a well-grouped menu of 12–15 clear items beats a "clean" menu of 5 vague ones. The nav-group size budget (~7–10 *per group*) is about splitting groups that mix distinct concerns, not capping total items.
- **Front-load labels with the distinguishing word and name content, not org structure** — "Pricing", not "Our pricing options"; "Reports", not the internal team that owns them. (The wording discipline is [`design/ux-writing`](../../../../design/ux-writing/SKILL.md); the IA requirement that labels map to content lives here.)
- **Don't hide navigation when there's room to show it** — the desktop layout shows top-level items; the hamburger/drawer is a small-screen affordance, not a default (the breakpoint mechanics are [`responsive-design`](../responsive-design/SKILL.md)'s nav-collapse pattern).

### Footers

The footer is the user's **last-resort lookup** — where they go for the things the header didn't surface. It's low-cost and high-value; give it real content in priority order:

- **Utility links** (Contact, Privacy, Terms, support) on every site; **doormat navigation** (repeat the top nav) so a long page doesn't force a scroll back up; **secondary-audience tasks** (Careers, Investors, Press) on multi-audience sites; **link columns** (the "fat footer") only for large, deep sites; engagement (newsletter, social) and trust signals (certifications) where they earn their place.
- **Fat footer for large multi-audience sites; slim utility footer for focused web apps** (version, status, help, legal) — don't bolt a marketing fat-footer onto an internal tool.
- **Use the semantic `<footer>` element** (it creates the `contentinfo` landmark — [`accessibility`](../accessibility/SKILL.md)), group links into **explicitly labeled** columns ("Contact us", "Documentation" — never a vague "Resources"), keep it visible and legible, and on mobile trim to essentials, stacking into accordions only if it would otherwise run several screens tall.

## 7. Choosing the surface — modal, page, or new tab

Where a task happens is a correctness decision, not a styling one: the wrong surface hides the context the user needs or breaks the back button. Decide before you build.

### Modal (overlay/drawer) or a separate route?

Ask in order:
1. **Does the task need the underlying screen's context?** Yes → an overlay/drawer over that screen, not a full navigation.
2. **Is it short and self-contained?** Yes → modal candidate. Multi-step or long forms → a **separate route**.
3. **Will the user reference or copy data from the background while working?** Yes → a **non-modal** side panel/drawer, never a blocking modal (which hides exactly what they need).
4. **Is it a repeated, high-frequency task?** Then both a modal *and* a navigation add friction — prefer **inline editing** or expandable rows.

- **Use a blocking modal only when the interruption itself is the value:** destructive/irreversible confirmations (§4 owns their content), a critical alert the user must acknowledge, or deliberately slowing input verification.
- **Use a separate route when** the flow is multi-step, needs full attention, or benefits from a **URL** (bookmarkable, shareable, back-button- and deep-link-friendly) — a real route with a title (§6). In App Router, an **intercepting/parallel route** gives a modal that's *also* a real URL (deep-linkable, refresh-safe) — reach for it when a modal needs to survive a reload or share.
- **Modal hygiene** (mechanics owned by [`accessibility`](../accessibility/SKILL.md) — cross-linked, not restated): an obvious exit (×, `Esc`, click-outside), focus trapped while open and restored on close, never stack modals, and **never open a modal the user didn't trigger** (unrequested pop-ups are the single most-disliked pattern).

### Same tab or new tab?

- **Default: open links in the same tab.** New tabs break the back button, disorient users who don't notice the switch, and are worst on mobile. Anyone who wants a new tab can ⌘/middle-click a real `<Link>`.
- **Legitimate `target="_blank"` exceptions:** reference material needed *while completing the current task* (help docs, a spec beside a form), a link whose navigation would destroy unsaved work or interrupt a process (media playing, checkout), and non-HTML documents (PDFs) that would hijack the tab.
- **If you do open a new tab, signal it** — a visible "opens in new tab" affordance plus a screen-reader hint, and `rel="noopener"`. The anchor mechanics (real `<a>`/`<Link>`, the affordance + `aria-label` suffix, `rel`) are [`generator`](../generator/SKILL.md)'s; the *decision* to open a new tab at all is this skill's.

---

## 8. Systemic — component/renderer unification & the highest-leverage fix

This is *why* the rules above are keepable at scale, not one-offs.

- **Most app-wide inconsistency traces to renderer divergence.** N grid/cell renderers (a MUI DataGrid here, a hand-rolled `<table>` there, a config-driven list elsewhere) means every display rule — enums, formats, links, loading, truncation — is implemented **0–1 times instead of once**. Consolidate to **one cell-renderer + one grid config** that hand-written pages *compose* rather than reimplement.
- **Fix at the highest-leverage point, in order:** (1) safety-critical gaps (missing confirmations, raw error dumps); (2) **one-change-fixes-all shared bindings** (loading state, lookup resolution, route titles, action labels); (3) per-page standardization (filters, page sizes, vocabulary).
- **Treat a config-driven patch layer as a bug report against the framework component.** The patch fixes today's page; the framework fix kills the defect *class*.
- **Sweep, don't spot-fix.** Every hand-found defect ("this page crashes on a missing lookup key") is a *class* ("which other pages index that key?"). Audit the class before closing the ticket.

---

## Rules

- **Enums humanized in every render path** from one derived helper; sweep siblings on any fix.
- **One canonical format per data type**, centralized (`Intl`-based); timezone labeled; hand-written pages use the shared helpers; every renderer implements the full token set.
- **Names, not ids/GUIDs**, resolved in list renderers too; cached identity directory; human-first pickers.
- **Deterministic server-side default sort with a unique tiebreaker** on every list; numbers right-aligned; widths capped; server paging with size options; filter/sortability parity; consistent row→detail affordance.
- **Forms render only persisted fields** (form↔DTO↔mapper parity, mechanically checked); PKs read-only; **state via explicit actions, never an editable `Status` `<select>`**; patch/subset types; optimistic concurrency on full-replace; same guards as self-service; no column the write path never fills.
- **Disable-don't-hide** with why-tooltips, gated by the backend's state machine; every mandated follow-up has an affordance; full state-machine reachability.
- **Every destructive action confirms by naming the object**, verb-labeled danger-styled button; never `window.confirm`.
- **Bulk: checkbox column + tri-state select-all scoped to the filtered page + selected-count + batch endpoints + stable test ids.**
- **One name→one concept, one verb per operation, a title on every route, one breadcrumb source, nav-group budgets, no dead/duplicate pages.**
- **Navigation shows the current location** (distinct active state, not color alone), groups+labels over item count, front-loaded content labels, visible top-level nav on desktop.
- **Footer is semantic `<footer>`** with explicitly-labeled columns and utility/doormat links, sized to the site.
- **Pick the surface deliberately** — modal only when the interruption is the value, a route (or intercepting route) when it needs a URL, same tab by default; no unrequested modals.
- **Unify renderers; fix at the highest leverage; treat config-patch layers as framework bugs; sweep the class.**

## What NOT to do

- No raw enum int / bare id-GUID / `String(value)` fallthrough shown to a user.
- No per-page inline formatting diverging from the shared helpers; no unlabeled timezone.
- No list without a deterministic server-side sort + tiebreaker; no full document/blob in a grid cell; no client-side load of an entire dataset.
- No editable field the update path ignores; no editable PK; no editable `Status` `<select>` standing in for a transition; no full-replace without concurrency control.
- No grid column the write path never populates.
- No action that renders-then-rejects; no destructive action without an object-naming confirmation; no neutral confirm button on a danger dialog; no `window.confirm`.
- No row-click-only multi-select; no select-all that reaches beyond the filtered page.
- No two pages/verbs for one concept; no route without a title; no double breadcrumb source; no dead/duplicate routes.
- No nav without a current-location indicator; no hamburger on desktop where the bar fits; no menu trimmed to a magic 7 at the cost of clear grouping.
- No `<div>`-based footer; no vague column label ("Resources"); no marketing fat-footer on a focused web app.
- No blocking modal for a task that needs the background visible; no modal the user didn't trigger; no `target="_blank"` without an "opens in new tab" signal + `rel="noopener"`.
- No spot-fix of a defect that's actually a class; no third grid renderer where the shared one should be composed.

## Validation

- Grep for raw enum/`String(...)`/`[object Object]` in cells; every enum renders humanized in grid, filter, detail, and form.
- One format helper per type; a page audit shows no ad-hoc inline formatting; timezones labeled.
- No id/GUID visible where a lookup exists; pickers type-ahead by name.
- Every list has a default server sort with a unique tiebreaker; refetch after an edit → no row jumps; page 2 has no dupes from page 1.
- Mechanical form↔DTO↔mapper parity check passes; PKs read-only; no editable `Status`; full-replace sends `If-Match`.
- Every destructive action shows a named-object confirmation; disabled actions have why-tooltips.
- Bulk flows: checkbox column present, select-all scoped to filter, selected-count shown, batch endpoint used.
- A title on every route; no duplicate titles for distinct concepts; nav groups within budget; no dead routes.
- The active nav item is visibly marked (and not by color alone) on every page; desktop shows top-level nav, hamburger only below the breakpoint.
- Footer is a `<footer>` with labeled columns; new-tab links carry a visible signal + `rel="noopener"`; no auto-opened modals.

## Handoffs

- Fetch / mutation / caching / DTO shape → [`data-access`](../data-access/SKILL.md)
- Rendering the failed/loading/empty states → [`error-resilience`](../error-resilience/SKILL.md)
- Real-`<Link>` navigation, route-title emission, the new-tab affordance + `rel="noopener"` → [`generator`](../generator/SKILL.md)
- Nav collapse / hamburger breakpoint, table→card, sticky header → [`responsive-design`](../responsive-design/SKILL.md)
- Modal focus-trap/restore, `contentinfo`/`navigation` landmarks, current-location not-by-color-alone → [`accessibility`](../accessibility/SKILL.md)
- The wording of nav labels, footer column labels, confirmation copy → [`design/ux-writing`](../../../../design/ux-writing/SKILL.md)
- Field-level validation UX → [`forms`](../forms/SKILL.md)
- Stable `data-testid` on grids/actions/selection → [`testability`](../testability/SKILL.md)
- Virtualization / server-paging perf → [`performance`](../performance/SKILL.md)
- Auth/session lifecycle → `auth/auth0-react`
