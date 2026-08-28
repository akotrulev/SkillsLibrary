---
name: design-ux-patterns
description: Use when DESIGNING how an application is used — before it is built or planned — the user-task inventory → information architecture, app-shell choice (sidebar / top nav / hybrid), page anatomy per page type (list, detail, form, dashboard, wizard, settings), form layout, density, expert accelerators (global search, command palette, shortcuts), notification surface, first-run onboarding, and the responsiveness budget. Output is a decision block the plan or the build consumes. Triggers "design the navigation", "what should the app shell be", "how should this page be laid out", "make this easy to use", "the app feels clunky and I haven't built it yet". Not for judging a built UI (`design-ux-review`), data-display correctness (the stack's `ui-rules`), words (`design-ux-writing`), or the look (`design-visual-identity`).
---

# UX patterns — designing how the app is used

Owns the **experience decisions a product UI is built from**: who uses it and for what, how those tasks become a navigation structure, what shell wraps every page, what each kind of page is made of, and how the app answers the user's actions. It is **generative** — it produces decisions before code exists — where [`design/ux-review`](../ux-review/SKILL.md) judges a build after the fact. The failure it prevents is an app whose every page is correct and whose whole is still hard to use: a nav that mirrors the database instead of the user's day, a shell that changes shape between pages, a dashboard of tiles that lead nowhere, a create form four clicks from the list it belongs to, a save that gives no sign it happened.

**What this skill owns:** the task inventory and the IA derived from it; the app-shell decision; page anatomy per page type; form layout; density; expert accelerators; the notification surface; first-run and progressive disclosure; the responsiveness budget. **What it does not own — cross-link, never restate:** data-display and CRUD *correctness* (the stack's `ui-rules` — humanized enums, deterministic sort, disable-don't-hide, confirmations, modal-vs-route mechanics); the loading / failed / empty *states* and their rendering (the stack's `error-handling`); breakpoint *reflow* (the stack's `responsive-design`); motion *implementation* (the stack's `animation`); focus, landmarks, contrast (the stack's `accessibility`); the *words* ([`design/ux-writing`](../ux-writing/SKILL.md)); the *look* ([`design/visual-identity`](../visual-identity/SKILL.md)).

Stack-agnostic and code-free by design: a planner loads it to write an experience plan, a frontend agent loads it to fill its decision record, and neither gets a component out of it.

**Corpus authority.** The facts this skill decides with come from the vendored [`design-ui-ux-pro-max`](../ui-ux-pro-max/SKILL.md) corpus — **it is the source of truth, and where it and this skill disagree on a fact, the corpus wins.** 119 UX guidelines, each with platform, description, do/don't, good and bad code examples, and severity:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/scripts/search.py" "<observable outcome>" --domain ux
```

Query the outcome (`"error summary validation"`, `"bottom nav deep linking"`), not the component. The priority ordering of those guidelines — accessibility and touch first, charts last — lives in the corpus skill's table and in `design/ui-ux-pro-max/references/quick-reference.md`. A **marketing** page's section order is [`design-landing-patterns`](../landing-patterns/SKILL.md), not this skill.

## When to use

- Designing a new application's navigation and layout, or a new functional area's screens, before any route exists.
- Writing the experience section of a plan (`be-shared-experience-plan`) — actors, journeys, screen map, per-screen pattern.
- A frontend agent's architecture step: the app shell, the nav map, and the page type of each route go into the decision record.
- A user says the app is hard to navigate or "feels clunky" and the question is *how it should be shaped*, not *what is wrong with the current build* (that is `ux-review`).

## 1. Task inventory → information architecture

Navigation is derived, never brainstormed. Start from what people do, not from what the system stores.

**Inventory the tasks.** For each actor, list the tasks as *verb + object + outcome* ("approve a pending invoice so it is paid this cycle"), with **frequency** (many times a day · daily · weekly · rare) and **stakes** (routine · money/compliance · irreversible). A task named after a table ("manage users") is not yet a task — ask what the person is trying to get done.

**Rank.** The three to five highest-frequency tasks define the home screen and the primary navigation. Everything else is reachable, but not prominent. Rare-and-high-stakes tasks (delete the account, change billing) live under settings, not in the primary nav.

**Group by the user's mental model.** Nav groups follow how the actor thinks about their work, not the org chart, the database schema, or the module layout. A test: a new hire in that role should choose the right group on the first try. The stack's `ui-rules` carries the grouping-size and label rules (group and label over count; front-load the distinguishing word; one name → one concept) — apply them here at design time.

**Depth budget.** Every primary task starts within **one click** of the shell (a top-level destination or the home screen's primary action); every other task within two. A task at depth three is a finding against the IA, not a job for breadcrumbs.

**Output — the nav map:**

| Destination | Nav placement | Actor(s) | Tasks it serves | Page type (§3) |
|---|---|---|---|---|
| Invoices | primary · sidebar | finance | approve pending, find one, export month | list → detail |
| Settings › Billing | secondary · account menu | owner | change plan, update card | settings |

One row per destination; the *Nav placement* column is the IA decision, the *Tasks* column is its evidence. A destination with no task is decoration; a frequent task with no destination is the gap the review would have found later.

## 2. The app shell

The shell is what every page shares; it is decided **once** and never changes shape between pages. It carries the brand/home link, the primary navigation, and the global utilities — search, notifications, the account menu — in the same place on every screen.

| Shell | Choose when | Not when |
|---|---|---|
| **Sidebar** (vertical primary nav) | An operational tool people *live in*: ≥ 6 primary destinations, grouped; data-dense pages that want full width for tables | ≤ 5 destinations (a sidebar of four items wastes a column) |
| **Top nav** (horizontal primary nav) | ≤ 6 destinations; content- or consumer-facing; the pages are documents, not workbenches | Destinations need groups or will grow — a top bar cannot group and overflows badly |
| **Hybrid** (sidebar for sections + a slim top bar for global utilities) | The sidebar shell, once global search / notifications / account need a stable home the sidebar footer cannot hold | A small app — it is two shells' worth of chrome |

Rules that hold for any shell:

- **Collapsible, never hidden, on desktop.** A collapsed sidebar keeps icons with tooltips; the hamburger/drawer is the small-screen form only (reflow mechanics: the stack's `responsive-design`). On mobile, a **bottom tab bar** is the right shell for ≤ 5 consumer-facing destinations; a drawer for everything else.
- **You-are-here on every page** — active state on the nav item (not by color alone) *and* the page title; breadcrumbs from depth two (`ui-rules` owns the one-breadcrumb-source rule).
- **The shell never swallows the page's primary action.** Global actions (search, new notification, account) belong to the shell; the page's action ("New invoice") belongs to the page header (§3).
- **Home is a screen, not a redirect.** It shows the top-ranked tasks' entry points and what needs attention now; for a tool with one dominant task, home *is* that task's list.

## 3. Page anatomy, by page type

Every page has the same skeleton — **header · optional toolbar · content region(s)** — so people learn it once:

- **Page header:** the title (one `h1`, and it is the same words as the nav label and the route title — `ui-rules`' one-name rule); breadcrumb above it from depth two; **one primary action** at the right, verb-labeled (`ux-writing`); at most two secondary actions visible, the rest in an overflow menu; a short status/summary line when the entity has state.
- **Toolbar** (list pages): search, filters, view switch, bulk actions — rendered *above* the data region so a failed load never unmounts them (`error-handling` owns the scoping).
- **Content region(s):** each carries its own loading / loaded / failed / empty state (`error-handling`); a page never shows one spinner for everything.

| Page type | Made of | Primary action | Rules |
|---|---|---|---|
| **List** | toolbar · table or card grid · pagination | Create the entity | A row is a link to its detail; the table is the default, cards only when the visual (image, status) *is* the information; filters reflect in the URL; correctness rules (sort, paging, truncation, bulk) are `ui-rules`' |
| **Detail** | header with status + key facts · sections or tabs · related lists | The entity's most frequent state action (Approve, Publish) | Tabs only when sections are independent and > 3; otherwise one scrolling page with anchored sections; related lists link back to their own list pages; edit is in place or a sibling route, never a modal for a long form |
| **Form** (create / edit) | one column · grouped sections · sticky footer for long forms | Save (verb + object) | Layout in §4; a create form opens from the list's primary action and returns to the created item's detail on success |
| **Dashboard** | KPI row · one primary chart · one or two tables of what needs attention | None, or the top task's entry | Every tile is a link to the list it summarises, filtered to the tile's meaning; no tile without a next step; no chart without a question it answers (chart craft: [`design/charts`](../charts/SKILL.md)); "what needs my attention" beats "what happened" |
| **Wizard** | numbered steps · progress · back/next · a review step | Finish (verb + object) | Only for ≥ 4 steps whose later inputs depend on earlier ones; otherwise a sectioned form; draft is saved between steps; back never loses input; the review step is the confirmation |
| **Settings** | grouped sections, each a small form | Save per section (or autosave with a visible "Saved" state) | Destructive settings (delete workspace) are the last section, visually separated, confirmed by object name (`ui-rules`) |

**Where the task happens** — page, drawer, or modal — is `ui-rules`' surface rule; apply it here when assigning a page type: quick peek or edit-with-context → drawer; multi-step, long, or shareable → its own route; blocking modal only when the interruption is the value.

## 4. Form layout

- **One column.** Multi-column forms break the eye's path and hide fields; the exception is a genuinely paired short field (city · postcode).
- **Labels above fields**, always visible — placeholders are hints, never labels (`ui-code-audit` flags the code smell; the decision is here).
- **Group into titled sections** past ~7 fields; the section title is the user's word for that part of the object.
- **Required is the default; mark the optional.** Marking every required field with an asterisk on a form that is 90 % required inverts the signal.
- **Field width follows expected content** — a 40-character-wide field for a 4-digit code invites the wrong input.
- **Defaults and prefill do the common case.** A field the system can infer (currency from the account, date as today, the current user as owner) is prefilled and editable, not empty.
- **Primary action where the eye ends:** bottom of the form, leading edge, verb-labeled; Cancel beside it as the secondary; a destructive action is never adjacent to Save. Long forms get a sticky footer so the action is always reachable.
- **Unsaved changes are guarded** on navigation away (mechanics: `ui-code-audit`'s rule / the stack's `forms`); validation timing and error rendering are the stack's `forms`.
- **Progressive disclosure inside a form:** advanced or rarely-used fields sit behind an "Advanced" expander, collapsed by default, never hidden on another page.

## 5. Density and hierarchy

- **Pick one density for the app and state it** — *comfortable* for consumer and occasional use, *compact* for tools people use all day with tables on most pages. A user-facing density toggle is earned only when both audiences are real.
- **Hierarchy comes from three text tones and weight, not from many sizes.** Primary text, secondary/muted, and disabled/placeholder; headings step the type scale, body does not. (The scale and tones are tokens — [`design/design-tokens`](../design-tokens/SKILL.md).)
- **Whitespace groups; lines separate.** Related controls sit closer to each other than to anything else; a divider is for unrelated regions.
- **Tables are the densest element on the page and set its rhythm** — row height, cell padding and column alignment are decided once app-wide (`ui-rules` owns alignment/truncation correctness).

## 6. Expert accelerators

Frequent users outgrow the nav within a week; the app should have somewhere for them to go.

- **Global search / command palette (`⌘K` / `Ctrl+K`)** once the app has more than ~20 destinations or the user's day starts with "find the record" — it searches **destinations and records** in one box, and every result is a link. Below that threshold a search field on the list page is enough. What the results surface itself must do is §10.
- **Keyboard shortcuts for the top three tasks** (create, search, save/approve), discoverable through a `?` overlay and shown in tooltips. Never override browser or OS shortcuts.
- **Saved views** — a named filter + sort + column set on any list a user returns to daily; the default view is the most common task's.
- **Recents and favourites** in the shell when the entity count is large and the user's working set is small.
- **Bulk actions** wherever a task repeats row by row (`ui-rules` owns the selection mechanics and per-item reporting).

## 7. Feedback and notifications

The user must never wonder whether something happened.

| Signal | Use for | Never for |
|---|---|---|
| **Inline state** (the row updates, the badge changes, "Saved" beside the button) | Anything visible on the current screen | — it is always the first choice |
| **Toast** (transient, auto-dismissing) | Success of an action whose result is *not* visible on screen ("Invoice sent"), with an Undo where reversible | Errors (they persist — `error-handling`), or repeating what the screen already shows |
| **Persistent notification** (top-right, closes only by hand) | Failures (`error-handling` owns it) | Successes |
| **Notification centre / inbox** (a shell utility with a badge) | Asynchronous events the user must come back to: a report finished, an approval requested of them, a job failed overnight | Apps with no asynchronous events — an empty bell is a broken promise |

One toast at a time; a bulk operation reports once, per item (`ui-rules`).

## 8. First run and progressive disclosure

- **The first-run empty state is a guided setup, not a tour.** A checklist of the two to four things that make the app useful ("Add your first project", "Invite a teammate"), each a real action, dismissible once complete. Product tours are skipped; checklists are done.
- **Every empty state is an invitation** — the no-records / no-match / by-design split and the copy are `ux-writing`'s; that the page has a primary action in its empty state is decided here.
- **Progressive disclosure at every level:** the nav shows the primary destinations, settings hold the rare ones; a form shows the common fields, "Advanced" holds the rest; a detail page shows the summary, sections hold the depth. Nothing is *hidden* — it is *staged*.
- **Contextual hints once.** A new capability gets one inline hint at the point of use, dismissed permanently on first interaction; never a modal, never a recurring tip.

## 9. The responsiveness budget

Perceived speed is a design requirement; the build meets it or the feature is not done.

| Window | The user must see | Owner of the mechanics |
|---|---|---|
| **≤ 100 ms** after any press | The control acknowledges: pressed state; a submit button disables and shows its in-flight state; a toggle flips immediately | the stack's `animation` (hover/press) · `forms` (submit state) |
| **≤ 300 ms** for a load | If not finished, a **skeleton shaped like the coming content** in the region — never a page-centre spinner, never a blank | the stack's `error-handling` (three-state regions) |
| **~4 s** still loading | The region acknowledges it is alive ("Still loading…" / progress) | `error-handling`'s soft threshold |
| **Timeout budget** | A failed state with a retry, scoped to the region | `error-handling` |

- **Optimistic updates for reversible, low-conflict actions** (star, toggle, reorder, mark read) — the screen changes at once and reconciles on the response; a failure reverts *and* says so. Never optimistic for money, sends, or deletes.
- **No layout shift on load:** skeletons and images reserve their space; content arriving does not push what the user is reading.
- **Navigation feels instant:** the shell renders immediately and only the page region loads; likely next routes are prefetched (the stack's `routing` / `performance`).
- **One region's wait never blocks the page.** Independent regions load independently.

**The same budget, in the field's measuring vocabulary.** The windows above are the *design* requirement; **Core Web Vitals** are how it is measured in production, at the **75th percentile** of real sessions — not the median, and not your machine. **LCP < 2.5 s** (the main content is on screen) · **INP < 200 ms** (every interaction acknowledges — INP replaced FID in March 2024, measures *all* interactions and reports the worst, and is now the most-failed of the three) · **CLS < 0.1** (nothing moves under the reader — the metric form of the no-layout-shift rule above). Write the budget as design acceptance criteria; the stack's `performance` skill owns hitting the numbers and `frontend/_shared/product-analytics` owns measuring them in the field. A design that meets the windows and a build that fails INP are the same defect reported twice.

## 10. Search results and filtering

§6 covers how search gets the user *to* a destination. This is the surface they land on when the answer is a **result set** — the second half of every list, catalogue, and knowledge base.

- **Autocomplete is instant or it is noise.** Suggestions appear as the user types, and any perceptible lag breaks the flow; a suggestion list that arrives after the user has finished typing has cost them time rather than saved it. Suggest destinations and records, never just query strings.
- **Match the user's vocabulary, not the database's.** Synonyms (couch/sofa), the domain's slang, brand terms and misspellings resolve to the same results. A high refinement rate — most users searching twice — is a **matching defect**, not user behaviour.
- **Facets are derived from the result set, not from the schema.** Show only facets that would change *this* result set; hide the ones that return nothing or everything. Order them by what people actually use.
- **Active filters are always visible and individually removable** — chips with a count and a clear-all, above the results. A filter the user cannot see is a filter they will blame the results for.
- **Quick filters apply instantly; advanced filters get an Apply.** The split is by cost: a single-value toggle re-queries on click, a multi-condition builder waits for a deliberate submit. An Apply button on a quick filter is a reliably confusing pattern — users don't know whether their click took.
- **Zero results is a state with work to do, never a dead end.** Say plainly that nothing matched *this* query, then offer the way forward: spelling correction, the broadened query, the filter to clear, or popular/related records. The words are [`ux-writing`](../ux-writing/SKILL.md)'s; that the state offers an *action* is decided here.
- **The query and the filters live in the URL.** A result set is the most-shared thing in an app — if it cannot be linked, pasted, or reloaded, the user re-derives it every time (`ui-rules` owns the URL-reflection mechanics).
- **Preserve the search on return.** Coming back from a result to the list restores the query, filters, sort, and scroll position; losing them is the most common reason a person abandons a search-driven task.

## Output — the experience decision block

Whoever loads this skill produces this block (into the plan's `experience-plan.md`, or the frontend agent's decision record):

```markdown
**Actors & primary tasks:** <actor> — <verb + object + outcome> (<frequency> · <stakes>), …
**App shell:** sidebar | top nav | hybrid — <why, in one line>; mobile: drawer | bottom tabs
**Density:** comfortable | compact — <why>
**Nav map:** <the §1 table>
**Screens:** per screen — <id> · <title = nav label = route title> · <route> · <page type> · <surface: page | drawer | modal> · <primary action> · <regions and their states> · <the data it needs>
**Accelerators:** <global search / shortcuts / saved views, or "none — under threshold">
**Notification surface:** inline + toast | + notification centre — <why>
**First run:** <the setup checklist items>
**Responsiveness budget:** the §9 table, as acceptance criteria
```

## Review checklist

- Every primary task is within one click of the shell; nothing the inventory ranks high is at depth three.
- Nav groups follow the actor's mental model; every destination serves a listed task; every frequent task has a destination.
- One shell, decided once, identical on every page; you-are-here on every page; the page's primary action is in the page header, not the shell.
- Every screen names its page type, its surface, its primary action, and its regions' states.
- Forms are one column, labels above, sectioned past ~7 fields, optional marked, common case prefilled, primary action at the end.
- One density, stated; hierarchy by tone and weight.
- Accelerators match the app's size — a command palette past ~20 destinations, shortcuts for the top three tasks, saved views on daily lists.
- Feedback follows the §7 table: inline first, toast for off-screen success, persistent for failure, a notification centre only for real asynchronous events.
- First run is a checklist of real actions; disclosure stages, never hides.
- The §9 budget is written into acceptance criteria, and its Core Web Vitals form (LCP < 2.5 s · INP < 200 ms · CLS < 0.1 at p75) is the number the build is measured on.
- Search results carry visible removable filters, a query in the URL, and a zero-results state that offers an action (§10).

## What NOT to do

- No nav that mirrors the schema or the org chart; no "Manage" / "Tools" / "More" as a destination.
- No shell that changes between pages; no page's primary action buried in a shell menu; no hamburger on desktop.
- No dashboard tile without a link to what it counts; no dashboard as the home of a single-task tool.
- No multi-column forms; no placeholder-as-label; no asterisk on every field; no long form in a modal.
- No wizard for three independent fields; no tour where a checklist would do; no recurring tips.
- No page-centre spinner; no blank region while loading; no toast for what the screen already shows; no empty notification bell.
- No optimistic update on money, sends, or deletes.
- No zero-results dead end; no Apply button on a quick filter; no facet that returns nothing; no search whose query and filters vanish from the URL or on the way back from a result.

## Related

- [`design/ux-review`](../ux-review/SKILL.md) — judges a built UI against the decisions made here; its IA and flow findings cite the decision they contradict.
- [`design/ux-writing`](../ux-writing/SKILL.md) — the words on the labels, actions, empty states and hints this skill positions.
- [`design/visual-identity`](../visual-identity/SKILL.md) — the look; its application lane styles the shell and pages decided here.
- [`design/design-tokens`](../design-tokens/SKILL.md) — the spacing, type and tone scales density and hierarchy are expressed in.
- [`design/charts`](../charts/SKILL.md) — the dashboard's charts.
- A stack's `ui-rules` ([Blazor](../../frontend/blazor/skills/ui-rules/SKILL.md) · [React](../../frontend/react/skills/ui-rules/SKILL.md)) — display/CRUD/table/bulk/confirmation correctness, the surface rule, the nav-label rules; this skill applies them at design time.
- A stack's `error-handling` — the three-state regions, the persistent failure notification, the soft-threshold acknowledgement.
- A stack's `responsive-design` — the shell's reflow (sidebar → drawer, table → card).
- `backend/_shared/experience-plan` (`be-shared-experience-plan`) — the planner artifact that carries this skill's decision block for a whole initiative.
- [`design-ui-ux-pro-max`](../ui-ux-pro-max/SKILL.md) — the 119 UX guidelines this skill decides against.
- [`design-landing-patterns`](../landing-patterns/SKILL.md) — the marketing-page counterpart to this skill's application IA.
