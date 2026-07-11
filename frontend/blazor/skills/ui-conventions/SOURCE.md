# SEED MATERIAL — do not register as a skill

Production-audit distillation handed over 2026-07-11 (already generalized — project specifics removed).
Becomes `frontend/blazor/skills/ui-conventions/SKILL.md` in Session D — see `frontend/PLAN.md` §3b item 10
for what this skill owns vs what gets folded into siblings: §1–2 → `data-access`, §3–4 → `error-resilience`,
§8 + `<PageTitle>` → the `generator` refresh, §16 → `accessibility`, §17 → the `auth/auth0-blazor` patch
(Session A), §18 → `project-scaffold`. Everything else (display correctness, table ergonomics, CRUD/edit
semantics, state-dependent actions, confirmations, bulk ops, IA, renderer unification) stays here.

The doc below was distilled from an **admin-portal** audit, but the skill is **business-case agnostic**:
every retained rule applies to any data-driven web application — customer-facing or internal — wherever
the app shows grids/lists, edits entities, or exposes state-changing actions. When authoring SKILL.md,
drop the admin framing ("operators" → "users", "portal" → "app"); keep the defect-class rationale.

---

# Blazor Server Admin Portal — Best Practices

Distilled from a full UX/functional/security audit of a production Blazor Server admin portal (Radzen components, descriptor/generator-driven CRUD). Every rule below traces back to a real defect class found in the field. Project-specific details removed; the rules are generic to any Blazor Server (or comparable component-driven) internal admin surface.

---

## 1. Routing & generated-descriptor integrity

- **Never index a route dictionary directly** (`Routes["read"]`). Use `TryGetValue` and fail with an explicit, diagnosable message — a missing key must not crash the page with a bare `KeyNotFoundException`.
- **Validate generated descriptors at build/test time.** A startup check or unit test should assert that every page's required routes ("read", "list", "update", …) exist in the descriptor it binds to. Generator misclassifications should fail CI, not production page loads.
- **Fix generator classification at the source.** A `GET` with a single `{id}` parameter returning a non-array DTO is a "read", not a "list". Patch individual descriptors as a stopgap, but teach the generator the rule so the whole class of defect disappears.
- **Route templates and substitutions must be verified together.** A helper that builds URLs from templates should throw if any `{placeholder}` remains unsubstituted — never send a literal `{accountId}` to the server. Copy-pasted substitution code (`.Replace("{id}", …)` against a template that uses `{accountId}`) is a guaranteed silent 404.
- **Lookup/dropdown endpoints with route parameters must substitute them from form context.** A lookup service that calls a parameterized endpoint verbatim and swallows the 404 produces silently empty dropdowns — the worst failure mode, because nothing looks broken.

## 2. Data shape & deserialization

- **Match the deserialization type to the endpoint's actual shape.** Deserializing a single-object endpoint into `T[]` + `FirstOrDefault()` yields `null` and a blank section, not an error. Typed clients generated from the API spec prevent this class entirely.
- **Contract-test the UI's DTOs and routes against the API spec** (OpenAPI/swagger). Script-verify every route, DTO name, and listed field — drift between generator output and spec should be caught mechanically.

## 3. Error handling & operator feedback

- **Never render raw server responses or `ex.Message` to operators.** Response bodies may be JSON or stack traces. Route every API call through one shared invoker that categorizes errors (problem-details → friendly message; unknown → generic message + correlation id) and logs the raw detail server-side.
- **Never swallow failures into blank sections.** A `try/catch` that leaves a component empty hides outages. Every data region needs three states: loading, loaded, failed — the failed state rendered inline (with retry), not just a transient toast.
- **Grid load failures need an inline error region in the grid itself.** A toast disappears; the operator is left staring at an empty grid indistinguishable from "no data".

## 4. Loading & empty states

- **Bind the grid's loading indicator on the shared renderer.** One `IsLoading` binding in the shared grid component fixes every page; without it, initial fetch and every reload show blank or stale rows.
- **Use skeletons for detail panes** and a visible progress affordance for long fetches.
- **Empty states must be actionable.** Distinguish "no records exist" (offer the create action) from "no filter applied yet" (say "enter a filter to begin" *in the grid area*, not as a toast) from "filter matched nothing" (offer to clear filters).

## 5. Enum & value display

- **Never show raw enum integers.** If the API models an enum as an int, the display layer must own a value→name map. Watch for generators emitting int enums as plain numbers with numeric formatting (`1.00` instead of `Active`).
- **Humanize PascalCase enum names** (`PartiallyFilled` → `Partially Filled`) through one shared helper.
- **Apply enum display in *every* render path** — grid cells, grid filters, detail panes, forms, extended/secondary list renderers. The classic failure: only the form renderer humanizes, and the same value renders three different ways across the portal.
- **When patching one entity's enum display, sweep for siblings.** Child/related entities with the same enum are routinely missed.

## 6. Formatting consistency

- **Define one canonical format per data type, portal-wide, and centralize it:**
  - Date: one format (e.g. ISO `yyyy-MM-dd`).
  - Date-time: one format, one decision on seconds (grids vs details must match or differ *by rule*, not by accident).
  - Money: one layout (amount + currency-code position), one precision.
  - Percent: one precision, one spacing rule.
  - Domain-specific precision (e.g. FX rates) defined once, not per page.
- **Label the timezone** wherever timestamps appear, or convert consistently. Mixing UTC, exchange-local, and relative ages without labels is a correctness hazard for operators.
- **Hand-written pages must use the same formatting tokens/helpers as generated pages.** Hand-rolled `string.Format` calls are where every deviation lives.
- **Every renderer must implement the full display-token set.** If one renderer supports `date:ISO`, `multiline`, `email` tokens and another falls through to `.ToString()`, fields silently render raw depending on which page shows them. Share the token→render logic in one place.

## 7. Identifiers & foreign keys

- **Never show a raw GUID where a name exists.** If the descriptor/metadata layer declares a lookup for a field, the *list* renderers must resolve it too — not just the forms. Render the resolved name; demote the GUID to a tooltip + copy affordance.
- **Composite human keys beat surrogate keys in cells** (e.g. `SYMBOL.EXCHANGE` reads well; a uuid never does).
- **Build a small cached identity directory** (id → name/email/label) over the existing list endpoints for cross-cutting name resolution in hand-written grids and pickers.
- **Pickers should be human-first:** type-ahead over name/email/label (GUID accepted as input but not the primary display); auto-resolve when unambiguous.

## 8. Navigation: real links, not click handlers

- **Every in-app navigation must be a real anchor** (`<a href>` / link component), never a button whose click handler calls `NavigateTo(...)`. Handler-only navigation kills open-in-new-tab, ctrl/middle-click, and copy-link-address across the entire portal.
- **Blazor Server supports this fully:** a `target="_blank"` anchor triggers a normal HTTP request that prerenders and opens its own circuit — same as pasting a deep link. Use `rel="noopener"` on `target="_blank"`.
- **Every entity that has a detail page should be reachable by a stable URL from anywhere its id appears** — grid cells, dashboard tiles, KPI cards, event feeds. Dashboard stat cards should be links to the surface they summarize.
- **If the canonical detail route requires parent ids the current DTO doesn't carry** (e.g. `/users/{userId}/accounts/{accountId}` but you only have `accountId`), add a lightweight resolver route (`/accounts/{id}` → look up owner → redirect). One resolver page unlocks linking portal-wide.
- **Fix linking at the renderer level, not per page:** a `link:{entity}` display token (or `LinkSpec` on the field metadata) understood by all shared renderers turns an id cell into name-as-link + GUID tooltip in one pass.
- **Account/entity-scoped pages should accept deep-link query parameters** (`?accountId=`, `?userId=`) so detail pages can link into filtered operational views.

## 9. State-dependent actions

- **Disable, don't hide.** Row actions that appear/disappear by state cause blank action cells and layout shift, and hide capability discovery. Render the action disabled with a tooltip explaining *why* it's unavailable.
- **Don't swap a control's meaning in place** (same button toggling approve↔unapprove via icon/color change). Use two clearly labeled actions or an explicit toggle control.
- **Never render an action the backend will always reject in that state.** Gate button enablement from the same state machine the backend enforces; every descriptor action needs its visibility/enablement condition set (a `null` gate = renders everywhere = guaranteed rejected clicks).
- **Every backend-mandated follow-up must have a UI affordance.** If the server's error says "create a new version instead", the UI must offer that path (e.g. "Copy as new version" prefilled from the source, key fields cleared). An error message that names an action the UI doesn't offer — or that the backend itself rejects — is a design bug.
- **Audit the full state machine:** every state must be reachable and every transition must be exposed (or explicitly out of scope). Dead enum states and untriggerable transitions are defects.

## 10. Destructive actions & confirmations

- **Every destructive action needs a confirmation dialog.** No exceptions for "small" actions like cancel/deactivate.
- **The confirmation must restate the action and name the specific object** by its friendly label — "Delete margin group 'EU Equities'?" — never the raw type name + key, and never a generic "Are you sure?".
- **The confirm button is verb-labeled and danger-styled** ("Delete group", red), not a neutral "OK"/"Confirm".
- **Dangerous-action styling must be consistent** — a warning title with a neutral confirm button sends a mixed signal.

## 11. Forms & edit semantics

- **A form must only render fields that actually persist.** If the update mapper ignores a target, the field must not be editable — an edit that shows a success toast and silently discards the value is the worst form defect. Cross-check form fields ↔ update-DTO properties ↔ mapper ignore-list mechanically (a test can do this).
- **Immutable/PK fields are read-only in edit mode.** Server-side re-stamping of the key after mapping means an editable key field is a silent no-op.
- **State transitions do not belong in edit forms.** An editable `Status`/`Stage` dropdown bypasses the transition actions' side effects (timestamps, notifications, guards). Remove the field; force the explicit action.
- **Prefer patch-style update DTOs (nullable fields + only-non-null semantics) or subset "Mod" DTOs.** Subset DTOs give field gating *by construction* — immutable fields simply don't exist on the edit contract.
- **Full-PUT edits need optimistic concurrency** (RowVersion / ETag + `If-Match`). Read-prefill-then-PUT-everything silently overwrites concurrent changes made between dialog open and save.
- **Admin write paths must enforce the same domain guards as self-service paths** (uniqueness checks, verified-field locks). A management endpoint that bypasses them creates inconsistent state (e.g. changing a verified phone while the verified flag stays true).
- **Complex object fields need real sub-forms.** An `object`-typed field falling through to a text box renders `ToString()` output and can't round-trip — it's effectively uneditable while looking editable.
- **Compliance-sensitive flags (consent, verification) should be read-only or gated behind an explicit audited action** with a mandatory reason, never a plain checkbox.
- **Validation is inline and per-field, as-you-type,** with required-field indicators. Anti-patterns: a silently disabled submit button with no message; validation surfaced only as a toast on submit; array/row editors skipping the per-field validation the rest of the form has.
- **Don't render an Add/Create button whose endpoint isn't implemented.** Hide it or implement it; a guaranteed 500 on a primary button is a broken promise.

## 12. Write-path / column completeness

- **Never ship a grid column the write path never populates.** For every listed field, verify some code path actually stamps it (the classic failure: the read path maps a column faithfully, but the create path's DTO/mapper never sets it, so it's NULL on every row in every environment).
- **Structured data belongs in structured columns.** If the grid's core purpose is showing a value or a state transition, it must be a real column — not free text buried in a notes field.
- **Stamp correlation/audit fields (user id, correlation id, previous/new state) at write time** from the context that has them; backfill existing rows when adding the column.

## 13. Table ergonomics

- **Deterministic sort, always.** Every list needs a default server-side `ORDER BY` with a unique tiebreaker (e.g. `CreatedAt DESC, Id`). Without it: edited rows jump position after reload (the DB may physically relocate updated rows), and paging duplicates/drops rows. Wire the default sort through the shared renderer so every page gets it.
- **Numbers right-align.** Integers included, not just decimals.
- **Cap column widths and truncate long text** (~30 chars + ellipsis) with the full value in a tooltip or the detail pane. Never dump a full document body, hash, or free-text blob into a grid cell.
- **Page-size options, not a fixed page size.** Server-side paging for real datasets; don't load entire result sets client-side in some grids while others page server-side.
- **Filtering parity:** if the shared grids offer per-column filters, hand-written grids must too — especially on the columns operators most need (status badges that can't be filtered by status are a recurring miss).
- **Sortability should be consistent within a grid** — mixed sortable/unsortable columns with no rationale reads as broken.
- **Row → detail navigation must be consistent** across grids: same affordance (view link/anchor) everywhere a detail page exists.

## 14. Bulk operations

- **Multi-select needs visible affordances:** a leading checkbox column (row-click-only selection is undiscoverable), a tri-state header select-all, and selection styling strong enough to differ from hover (background tint + accent bar), plus a persistent selected-count.
- **Select-all scopes to the visible, filtered page** when filtering/paging is server-side — it must never silently select rows the operator isn't looking at. Tooltip it: "Select all visible rows (respects current filters)".
- **Where operators do repetitive row-by-row state changes** (approve/cancel/resolve backlogs), provide batch endpoints + bulk UI. Thirty click-confirm cycles for one logical operation is a workflow defect.
- **Stable test ids on selection controls** so UI automation can drive bulk flows.

## 15. Information architecture & consistency

- **One name → one concept.** Two pages with identical titles over different entities must be disambiguated in the page title itself, not just by the nav group above them.
- **One verb per operation portal-wide.** The same corrective concept must not be "Cancel" / "Mark as Failed" / "Disapprove" / "Resolve" on four sibling pages.
- **`<PageTitle>` on every page** (emit it from the shared page/renderer so generated pages get it for free) — browser tabs full of the same generic title are unusable.
- **One breadcrumb source.** Global auto-breadcrumbs *or* per-page bars, never both; breadcrumb segments show friendly names, not raw GUID URL segments.
- **Nav groups have a size budget** (~7–10 items); split groups mixing distinct concerns; no loose ungrouped leftovers; deliberate group ordering.
- **Standardize the small stuff once:** one dialog width scale, one page-header treatment, one date-range-filter component (with a clear affordance), one filter-trigger label.
- **Delete dead pages and duplicate routes** — orphan copies of list pages confuse navigation and search.
- **Duplicate/near-duplicate entity grids** (two metrics tables sharing ~12 fields with drifted column order) should share one field definition or be consolidated.

## 16. Accessibility

- **Every icon-only button needs an accessible label** (`Title`/`aria-label`) — especially the shared renderer's built-in row actions, where one omission un-labels every grid in the portal.
- **Never signal state by color or icon alone**; pair with text or a labeled tooltip.
- **Watch contrast on muted/secondary text and active-state colors** against the actual backgrounds used.
- **Consistency within a control group:** if one button in a row has a tooltip, its siblings must too.

## 17. Auth & session lifecycle (Blazor Server specifics)

- **Register a `RevalidatingServerAuthenticationStateProvider`.** Blazor Server captures auth state once at circuit creation; without revalidation, a tab stays authenticated (UI *and* outgoing API tokens) after logout in another tab, until token expiry. A short interval (1–5 min) bounds the window.
- **A circuit has no live `HttpContext`** — the revalidator can't re-read the cookie. Stamp a session marker at sign-in: either an expiry claim to validate against, or (stronger) a server-side session registry keyed by a `session_id` claim. The registry makes logout authoritative across tabs *and* kills replayed cookies.
- **Implement refresh-token flow; don't ship a hard session cliff.** A fixed cookie lifetime just under token lifetime means mid-task logouts and, worse, live circuits sending expired tokens → downstream 401s surfacing as generic errors. Two cooperating pieces:
  - Cookie `OnValidatePrincipal`: near expiry, exchange the refresh token, rewrite the ticket (`ShouldRenew = true`). Covers full HTTP requests.
  - Circuit-side token service with a server-side cache: circuits outlive HTTP requests and can't rewrite cookies, so the refreshed token must live server-side, preferred over the stale cookie token.
- **Logout must revoke the refresh token** at the IdP and evict the session registry entry, then sign out both schemes. Otherwise "logout" doesn't mean logout.
- **Password reset must also evict the target user's active sessions** — resetting a password does not invalidate live cookies by itself.
- **Host login on your own (sub)domain with your branding.** Redirecting operators to a generic IdP domain trains them to type admin credentials into unfamiliar addresses. Prefer IdP custom-domain + hosted-UI branding over building a native credential form (which transfers MFA/reset/lockout ownership to you).
- **Define the password-reset story explicitly:** self-service (hosted, linked from login, no account enumeration in responses) and admin-initiated (audited, reason required).
- **Test the lifecycle explicitly:** work past token expiry in both a fresh load and a long-open tab; logout in tab 1 kills tab 2 within the interval; replayed pre-logout cookie rejected; revoked refresh token signs out cleanly, no error loop.

## 18. Configuration hygiene

- **No hardcoded URLs or fallback hosts in components** (`http://localhost:...` fallbacks diverge from the configured path and break quietly in deployed environments). External system links (back-office cockpits, vendor consoles) come from configuration.
- **Mind external asset dependencies** (fonts/CDNs) if the portal may run air-gapped.

## 19. Systemic: renderer unification & the generator feedback loop

- **Most portal-wide inconsistency traces to renderer divergence.** N grid renderers (rich generated / lean generated / hand-written) means every display rule — enums, formats, links, loading, truncation — is implemented 0–1 times instead of once. Consolidate to one renderer core; hand-written pages compose it rather than reimplementing cells.
- **Fix at the highest leverage point, in order:** (1) safety-critical gaps (missing confirmations, raw error dumps); (2) one-change-fixes-all renderer bindings (loading state, lookup resolution, page titles, action labels); (3) per-page standardization (filters, page sizes, vocabulary).
- **Keep a manual patch layer over generated descriptors** (post-build hook) for corrections — but treat every patch as a generator bug report. The patch fixes today's page; the generator fix kills the defect class.
- **Sweep, don't spot-fix.** Every defect found by hand ("this page crashes on a missing route key") is a class ("which other pages index that key?"). Audit the class before closing the ticket.
