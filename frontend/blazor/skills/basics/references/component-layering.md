# Component architecture — the layering taxonomy

The atomic-design vocabulary (**atom → molecule → organism → template → page**) is the conceptual reasoning behind Blazor component structure. [`project-setup`](../../project-setup/SKILL.md) owns the **placement heuristic** — which reuse level lives in shared `Components/` vs a feature folder, and the "promote on the second reuse" rule. Read its layering table for *where files go*; this section is *why the levels differ* and the design rules for each. Don't build a global `Atoms/`/`Molecules/` folder tree — the taxonomy is a placement heuristic, not a directory structure ([`project-setup`](../../project-setup/SKILL.md) says so and shows the folder layout).

## The levels, and what changes as you go up

| Level | Domain awareness | Owns state? | Data reach | Render mode |
|---|---|---|---|---|
| **Atom** | None | No — fully controlled | None | Agnostic (runs anywhere) |
| **Molecule** | None (generic) | **Only ephemeral UI state** (see below) | None | Agnostic |
| **Organism** | Yes — knows a model slice | Local view state OK; domain state via injection/params | Via an injected [`data-fetching`](../../data-fetching/SKILL.md) interface or parameters | Agnostic |
| **Template** | None (layout only) | No | None | Usually Static |
| **Page** | Yes — orchestrates | Owns the fetch + page-level state | Owns the data fetch | **Sets** the render mode at `@page` |

The through-line: **domain knowledge and data ownership climb as you go up; render-mode-agnosticism holds until the page.** An atom that injects a data service or names a domain type has skipped two levels — it's a mislabeled organism and won't be reusable.

## Naming

- **Atom/molecule names describe the control, not the domain**: `InputCurrency`, `SearchBox`, `Pagination`, `Badge` — never `OrderSearchBox` (that domain-coupling makes it a one-use organism).
- **Organism names name the domain concept**: `OrderTable`, `CustomerCard`, `CheckoutSummary`.
- **Page names match the route/capability**; templates name the arrangement (`TwoPaneLayout`, `MainLayout`).
- One name → one concept across the app (the IA rule [`ui-rules`](../../ui-rules/SKILL.md) enforces app-wide).

## Prop-drilling limits — when to stop passing parameters down

Passing a value through 1–2 layers is fine. Past that, or when many siblings need it, the parameter chain is a smell:

| Depth / shape | Use |
|---|---|
| 1–2 levels, one value | `[Parameter]` passing (plain, explicit, testable) |
| Deep subtree, cross-cutting (theme, current user, edit context) | `CascadingValue` / `[CascadingParameter]` (Blazor's Context) with `IsFixed` when static |
| Shared across routes / unrelated subtrees | A **scoped service** (state container below) — not cascading, not drilling |
| A callback drilled 3+ levels to bubble an event | Reconsider structure, or a scoped service raising an event; never `Action` params (use `EventCallback`) |

Rule of thumb: **drill parameters, cascade cross-cutting context, service-inject shared state.** If you're drilling the same value past three organisms, promote it to a cascade or a service. If you're drilling a *callback* up through layers, the event probably belongs on a scoped state container that the interested components subscribe to directly.

## When a molecule (or any component) owns state

Default: components are **controlled** — value in via `[Parameter]`, changes out via `EventCallback`. A component may own state only when the state is **ephemeral and purely presentational** and would be noise to hoist:

- ✅ **Own it:** a dropdown's open/closed flag, a "show password" toggle, hover/focus visual state, an accordion's expanded section, an in-progress (not-yet-submitted) inline edit buffer. None of this outlives the component or matters to anyone else.
- ❌ **Don't own it — lift it (or put it in a container):** the selected value of a picker (the parent needs it), form field values that must round-trip to a submit ([`forms`](../../forms/SKILL.md) owns the `EditContext`), anything two components must agree on, anything that must survive navigation or prerender (`[PersistentState]`), any domain data (that's [`data-fetching`](../../data-fetching/SKILL.md)/[`state-management`](../../state-management/SKILL.md)).

Test: *if another component or the server needs to know this value, it isn't the molecule's to own.* Ephemeral UI toggles stay local; everything else lifts to a parameter, a cascade, or a scoped service.

## Composition over configuration

Prefer composing small components (pass `RenderFragment` slots) over one component with 20 `[Parameter]`s and mode flags. A `Card` with `Header`/`Body`/`Footer` `RenderFragment`s beats a `Card` with `ShowHeader`/`HeaderText`/`ShowFooter`/... booleans — the global "composition over inheritance/configuration" rule, applied to the render tree. This is also what keeps atoms/molecules domain-free: they expose slots, the organism fills them with domain content.
