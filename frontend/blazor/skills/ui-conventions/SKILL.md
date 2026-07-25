---
name: fe-blazor-ui-conventions
description: Use on every data-driven feature build for UI correctness — display (humanized enums, one format per type, names not raw GUIDs), table ergonomics (deterministic sort, server paging, filter parity), CRUD semantics (form↔DTO parity, read-only PKs, optimistic concurrency), disable-don't-hide, confirmations, IA. Triggers: "review this grid/form", "the enum shows as a number", "an edit discards a field". Do NOT use for fetch mechanics (`data-access`) or error states (`error-resilience`).
---

# Blazor — UI Conventions (data-driven correctness)

Cross-cutting UI-correctness conventions for **any data-driven web application** — customer-facing or internal — wherever the app shows grids/lists, edits entities, or exposes state-changing actions. Every rule here traces to a real defect class, not taste. **Loaded on every feature build**, not conditionally: these are the rules that keep a hundred pages consistent instead of a hundred slightly-different pages.

**Version rule:** these are UI-correctness conventions, largely **version-agnostic** across net8/net9/net10. Where a mechanism is version-sensitive (the `<PageTitle>` component, `[PersistentState]`) the owning sibling skill carries the version note; this skill states the *convention*.

## What this skill owns vs. its siblings

The conventions split across the feature-build skills by domain; this skill owns the **display, edit, action, table, and IA correctness** layer. Its siblings own the rest — don't duplicate:

| Concern | Owner |
|---|---|
| Route/descriptor integrity, deserialization shape, contract-testing DTOs | [`data-access`](../data-access/SKILL.md) (§1–2) |
| Error rendering, three-state regions, empty-state UX, categorized invoker | [`error-resilience`](../error-resilience/SKILL.md) (§3–4) |
| Real-anchor navigation (`<a href>` over `NavigateTo`), `<PageTitle>` *emission* | [`generator`](../generator/SKILL.md) (§8, §15-emit) |
| Accessible labels, contrast, color-not-alone | [`accessibility`](../accessibility/SKILL.md) (§16) |
| Auth/session lifecycle | `auth/auth0-blazor` (§17) |
| Config hygiene (no hardcoded hosts) | [`project-scaffold`](../project-scaffold/SKILL.md) (§18) |
| **Everything below** | **this skill** |

## When to use

- Building or reviewing any grid, list, detail pane, or edit form
- An enum renders as a number; a GUID shows where a name should; formats vary page-to-page
- Rows reorder/duplicate across paging or after an edit
- An edit succeeds but a value doesn't stick; a Status dropdown bypasses transition logic
- A destructive action fires without confirming what it hits
- The same concept is named/verbed differently across pages

## When NOT to use

- The mechanics of fetching, routing, deserializing → [`data-access`](../data-access/SKILL.md)
- Rendering the failed/empty states themselves → [`error-resilience`](../error-resilience/SKILL.md)
- Making navigation a real anchor / emitting `<PageTitle>` → [`generator`](../generator/SKILL.md)
- A11y labels + contrast → [`accessibility`](../accessibility/SKILL.md)

---

## 1. Display correctness

The layer decides how a stored value becomes a shown value. The failures are all "technically rendered, semantically wrong."

### Enums — humanize in *every* render path

- **Never show a raw enum integer.** If the API models an enum as an int, the display layer owns a value→name map (watch generators that emit int enums as numbers — `1.00` instead of `Active`).
- **Humanize PascalCase names** (`PartiallyFilled` → "Partially Filled") through **one shared helper**.
- **Apply it in every render path** — grid cells, grid *filters*, detail panes, forms, secondary/extended renderers. The classic bug: only the form renderer humanizes, so the same value reads three different ways across the app.
- **Derive the map from the enum itself** (`Enum.GetValues`, `[Display]`/`[Description]` attributes) — never a hand-maintained `Dictionary<TEnum,string>` that drifts on rename (mirrors [`testability`](../testability/SKILL.md)'s derive-don't-hardcode rule).
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
- **Stable test ids on selection controls** so UI automation can drive bulk flows ([`testability`](../testability/SKILL.md)).

---

## 6. Information architecture & consistency

- **One name → one concept.** Two pages with identical titles over different entities must be disambiguated in the **page title itself**, not just the nav group above them.
- **One verb per operation app-wide.** The same corrective concept must not be "Cancel" / "Mark as Failed" / "Disapprove" / "Resolve" on four sibling pages.
- **`<PageTitle>` on every page** — browser tabs full of the same generic title are unusable. (This skill mandates the *convention*; [`generator`](../generator/SKILL.md) *emits* it from the shared page/renderer so generated pages get it free.)
- **One breadcrumb source** — global auto-breadcrumbs *or* per-page bars, never both; segments show friendly names, not raw GUID URL segments.
- **Standardize the small stuff once:** one dialog-width scale, one page-header treatment, one date-range-filter component, one filter-trigger label.
- **Delete dead pages and duplicate routes;** consolidate near-duplicate grids (two tables sharing ~12 fields with drifted column order → one field definition).

### Navigation

- **Always indicate the current location.** The single most common nav defect is failing to show where the user is now — highlight the active nav item with a **distinct state that isn't color alone** (weight, an indicator bar, `aria-current="page"`), and add breadcrumbs on deep hierarchies. (`NavLink`'s `Active` class is the hook; the not-color-alone + `aria-current` a11y side is [`accessibility`](../accessibility/SKILL.md)'s.)
- **Group and label over count — the "7 items max" rule is a myth.** Menus rely on *recognition*, not recall; a well-grouped menu of 12–15 clear items beats a "clean" menu of 5 vague ones. The nav-group size budget (~7–10 *per group*) is about splitting groups that mix distinct concerns, not capping total items. What matters is grouping and label quality.
- **Front-load labels with the distinguishing word and name content, not org structure** — "Pricing", not "Our pricing options"; "Reports", not the internal team that owns them. (The wording discipline is [`design/ux-writing`](../../../../design/ux-writing/SKILL.md); the IA requirement that labels map to content lives here.)
- **Don't hide navigation when there's room to show it** — the desktop layout shows top-level items; the hamburger/drawer is a small-screen affordance, not a default (the breakpoint mechanics are [`responsive-design`](../responsive-design/SKILL.md)'s nav-collapse pattern).

### Footers

The footer is the user's **last-resort lookup** — where they go for the things the header didn't surface. It's low-cost and high-value; give it real content in priority order:

- **Utility links** (Contact, Privacy, Terms, support) on every site; **doormat navigation** (repeat the top nav) so a long page doesn't force a scroll back up; **secondary-audience tasks** (Careers, Investors, Press) on multi-audience sites; **link columns** (the "fat footer") only for large, deep sites; engagement (newsletter, social) and trust signals (certifications) where they earn their place.
- **Fat footer for large multi-audience sites; slim utility footer for focused web apps** (version, status, help, legal) — don't bolt a marketing fat-footer onto an internal tool.
- **Use the semantic `<footer>` element** (it creates the `contentinfo` landmark — [`accessibility`](../accessibility/SKILL.md)), group links into **explicitly labeled** columns ("Contact us", "Documentation" — never a vague "Resources"), keep it visible and legible (don't hide it behind a desktop accordion), and on mobile trim to essentials, stacking into accordions only if it would otherwise run several screens tall.

## 7. Choosing the surface — modal, page, or new tab

Where a task happens is a correctness decision, not a styling one: the wrong surface hides the context the user needs or breaks the back button. Decide before you build.

### Modal (overlay/drawer) or a separate page?

Ask in order:
1. **Does the task need the underlying screen's context?** Yes → an overlay/drawer over that screen, not a full page navigation.
2. **Is it short and self-contained?** Yes → modal candidate. Multi-step or long forms → a **separate page**.
3. **Will the user reference or copy data from the background while working?** Yes → a **non-modal** side panel/drawer, never a blocking modal (which hides exactly what they need).
4. **Is it a repeated, high-frequency task?** Then both a modal *and* a page navigation add friction — prefer **inline editing** or expandable rows.

- **Use a blocking modal only when the interruption itself is the value:** destructive/irreversible confirmations (§4 owns their content), a critical alert the user must acknowledge, or deliberately slowing input verification.
- **Use a separate page when** the flow is multi-step, needs full attention, or benefits from a **URL** (bookmarkable, shareable, back-button- and deep-link-friendly) — a real route with a `<PageTitle>` (§6), not a modal pretending to be a page.
- **Modal hygiene** (mechanics owned by [`accessibility`](../accessibility/SKILL.md) — cross-linked, not restated): an obvious exit (×, `Esc`, click-outside), focus trapped while open and restored on close, never stack modals, and **never open a modal the user didn't trigger** (unrequested pop-ups are the single most-disliked pattern).

### Same tab or new tab?

- **Default: open links in the same tab.** New tabs break the back button, disorient users who don't notice the switch, and are worst on mobile. "We'll lose the visitor" is a business rationalization, not a user need — anyone who wants a new tab can ⌘/middle-click.
- **Legitimate `target="_blank"` exceptions:** reference material needed *while completing the current task* (help docs, a spec beside a form), a link whose navigation would destroy unsaved work or interrupt a process (media playing, checkout), and non-HTML documents (PDFs) that would hijack the tab.
- **If you do open a new tab, signal it** — a visible "opens in new tab" affordance plus a screen-reader hint, and `rel="noopener"`. The anchor mechanics (real `<a>`, the affordance + `aria-label` suffix, `rel`) are [`generator`](../generator/SKILL.md)'s; the *decision* to open a new tab at all is this skill's.

---

## 8. Systemic — renderer unification & the highest-leverage fix

This is *why* the rules above are keepable at scale, not one-offs.

- **Most app-wide inconsistency traces to renderer divergence.** N grid renderers (rich generated / lean generated / hand-written) means every display rule — enums, formats, links, loading, truncation — is implemented **0–1 times instead of once**. Consolidate to **one renderer core** that hand-written pages *compose* rather than reimplement.
- **Fix at the highest-leverage point, in order:** (1) safety-critical gaps (missing confirmations, raw error dumps); (2) **one-change-fixes-all renderer bindings** (loading state, lookup resolution, page titles, action labels); (3) per-page standardization (filters, page sizes, vocabulary).
- **Treat a generated-descriptor patch layer as a bug report against the generator.** The patch fixes today's page; the generator fix kills the defect *class*.
- **Sweep, don't spot-fix.** Every hand-found defect ("this page crashes on a missing route key") is a *class* ("which other pages index that key?"). Audit the class before closing the ticket.

---

## Rules

- **Enums humanized in every render path** from one derived helper; sweep siblings on any fix.
- **One canonical format per data type**, centralized; timezone labeled; hand-written pages use the shared helpers; every renderer implements the full token set.
- **Names, not GUIDs**, resolved in list renderers too; cached identity directory; human-first pickers.
- **Deterministic server-side default sort with a unique tiebreaker** on every list; numbers right-aligned; widths capped; server paging with size options; filter/sortability parity; consistent row→detail affordance.
- **Forms render only persisted fields** (form↔DTO↔mapper parity, mechanically checked); PKs read-only; **state via explicit actions, never an editable `Status`**; patch/subset DTOs; optimistic concurrency on full-PUT; same guards as self-service; no column the write path never fills.
- **Disable-don't-hide** with why-tooltips, gated by the backend's state machine; every mandated follow-up has an affordance; full state-machine reachability.
- **Every destructive action confirms by naming the object**, verb-labeled danger-styled button.
- **Bulk: checkbox column + tri-state select-all scoped to the filtered page + selected-count + batch endpoints + stable test ids.**
- **One name→one concept, one verb per operation, `<PageTitle>` everywhere, one breadcrumb source, nav-group budgets, no dead/duplicate pages.**
- **Navigation shows the current location** (distinct active state, not color alone), groups+labels over item count, front-loaded content labels, visible top-level nav on desktop.
- **Footer is semantic `<footer>`** with explicitly-labeled columns and utility/doormat links, sized to the site (fat vs slim).
- **Pick the surface deliberately** — modal only when the interruption is the value, a page when it needs a URL, same tab by default; no unrequested modals.
- **Unify renderers; fix at the highest leverage; treat descriptor patches as generator bugs; sweep the class.**

## What NOT to do

- No raw enum int / bare GUID / `.ToString()` fallthrough shown to a user.
- No per-page `string.Format` diverging from the shared format helpers; no unlabeled timezone.
- No list without a deterministic server-side sort + tiebreaker; no full document/blob in a grid cell; no client-side load of an entire dataset.
- No editable field the update path ignores; no editable PK; no editable `Status` dropdown standing in for a transition action; no full-PUT without concurrency control.
- No grid column the write path never populates.
- No action that renders-then-rejects; no destructive action without an object-naming confirmation; no neutral confirm button on a danger dialog.
- No row-click-only multi-select; no select-all that reaches beyond the filtered page.
- No two pages/verbs for one concept; no missing `<PageTitle>`; no double breadcrumb source; no dead/duplicate routes.
- No nav without a current-location indicator; no hamburger on desktop where the bar fits; no menu trimmed to a magic 7 at the cost of clear grouping.
- No `<div>`-based footer; no vague column label ("Resources") hiding its links; no marketing fat-footer on a focused web app.
- No blocking modal for a task that needs the background visible; no modal the user didn't trigger; no `target="_blank"` without an "opens in new tab" signal + `rel="noopener"`.
- No spot-fix of a defect that's actually a class; no third grid renderer where the shared one should be composed.

## Validation

- Grep for raw enum/`ToString()` in cells; every enum renders humanized in grid, filter, detail, and form.
- One format helper per type; a page audit shows no hand-rolled `string.Format`; timezones labeled.
- No GUID visible where a lookup exists; pickers type-ahead by name.
- Every list has a default server sort with a unique tiebreaker; reload after an edit → no row jumps; page 2 has no dupes from page 1.
- Mechanical form↔DTO↔mapper parity check passes; PKs read-only; no editable `Status`; full-PUT sends `If-Match`.
- Every destructive action shows a named-object confirmation; disabled actions have why-tooltips.
- Bulk flows: checkbox column present, select-all scoped to filter, selected-count shown, batch endpoint used.
- `<PageTitle>` on every route; no duplicate titles for distinct concepts; nav groups within budget; no dead routes.
- The active nav item is visibly marked (and not by color alone) on every page; desktop shows top-level nav, hamburger only below the breakpoint.
- Footer is a `<footer>` with labeled columns; new-tab links carry a visible signal + `rel="noopener"`; no auto-opened modals.

## Handoffs

- Route/deserialization/contract mechanics → [`data-access`](../data-access/SKILL.md)
- Rendering the failed/loading/empty states → [`error-resilience`](../error-resilience/SKILL.md)
- Real-anchor navigation, `<PageTitle>` emission, the new-tab affordance + `rel="noopener"` → [`generator`](../generator/SKILL.md)
- Nav collapse / hamburger breakpoint mechanics, sticky-header behavior → [`responsive-design`](../responsive-design/SKILL.md)
- Modal focus-trap/restore mechanics, `contentinfo`/`navigation` landmarks, current-location not-by-color-alone → [`accessibility`](../accessibility/SKILL.md)
- The wording of nav labels, footer column labels, and confirmation copy → [`design/ux-writing`](../../../../design/ux-writing/SKILL.md)
- Field-level validation UX → [`forms`](../forms/SKILL.md)
- Stable `data-testid` on grids/actions/selection → [`testability`](../testability/SKILL.md)
- Virtualization / server-paging perf → [`performance`](../performance/SKILL.md)
- Accessible labels + contrast (icon-only buttons, color-not-alone) → [`accessibility`](../accessibility/SKILL.md)
- Auth/session lifecycle → `auth/auth0-blazor`
