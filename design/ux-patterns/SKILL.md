---
name: app-structure
description: Use when designing how an app is used before it is built (IA, app shell, navigation, page anatomy, onboarding). Triggers "design the navigation". Not for reviewing a built UI (ux-review).
disable-model-invocation: true
---

# UX patterns — designing how the app is used

Owns the **experience decisions a product UI is built from**: who uses it and for what, how those tasks become a navigation structure, what shell wraps every page, what each kind of page is made of, and how the app answers the user's actions. It is **generative** — it produces decisions before code exists — where [`design/ux-review`](../ux-review/SKILL.md) judges a build after the fact. The failure it prevents is an app whose every page is correct and whose whole is still hard to use: a nav that mirrors the database instead of the user's day, a shell that changes shape between pages, a dashboard of tiles that lead nowhere, a create form four clicks from the list it belongs to, a save that gives no sign it happened.

**What this skill owns:** the task inventory and the IA derived from it; the app-shell decision; page anatomy per page type; form layout; density; expert accelerators; the notification surface; first-run and progressive disclosure; the responsiveness budget. **What it does not own — cross-link, never restate:** data-display and CRUD *correctness* (the stack's `ui-rules` — humanized enums, deterministic sort, disable-don't-hide, confirmations, modal-vs-route mechanics); the loading / failed / empty *states* and their rendering (the stack's `error-handling`); breakpoint *reflow* (the stack's `responsive-design`); motion *implementation* (the stack's `animation`); focus, landmarks, contrast (the stack's `accessibility`); the *words* ([`design/ux-writing`](../ux-writing/SKILL.md)); the *look* ([`design/visual-identity`](../visual-identity/SKILL.md)).

Stack-agnostic and code-free by design: a planner loads it to write an experience plan, a frontend agent loads it to fill its decision record, and neither gets a component out of it.

**Corpus authority.** The facts this skill decides with come from the [`design:corpus`](../ui-ux-pro-max/SKILL.md) corpus — **it is the source of truth, and where it and this skill disagree on a fact, the corpus wins.** 119 UX guidelines, each with platform, description, do/don't, good and bad code examples, and severity:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/scripts/search.py" "<observable outcome>" --domain ux
```

Query the outcome (`"error summary validation"`, `"bottom nav deep linking"`), not the component. The priority ordering of those guidelines — accessibility and touch first, charts last — lives in the corpus skill's table and in `design/ui-ux-pro-max/references/quick-reference.md`. A **marketing** page's section order is [`design:landing-patterns`](../landing-patterns/SKILL.md), not this skill.

## Native apps

On a mobile or desktop app the method holds — task inventory and depth budget, page types, forms, density, feedback, first run, the §9 windows. The web shell and its devices do not transfer; the platform's navigation replaces them:

- **Shell (§2):** mobile — bottom tabs for 3–5 top-level areas, extras under More or Settings, back that keeps screen state (corpus `--domain web`: *Bottom Tabs*, *Back Behavior*); macOS — a `NavigationSplitView` sidebar, every command in the menu bar; Windows — `NavigationView` + `Frame`.
- **Accelerators (§6):** `⌘K` and the `?` overlay become menu-bar commands with standard shortcuts (macOS) or access keys and accelerators (Windows).
- **§9 and §10:** Core Web Vitals give way to the stack's `performance` launch and frame budgets; "in the URL" becomes deep links and restored screen state.

Platform facts: the corpus (`--domain web` for iOS / Android / React Native rows, `--stack swiftui | jetpack-compose | react-native | winui | wpf`, `design/ui-ux-pro-max/references/pro-rules.md` for mobile) and the stack's `navigation` (mobile), `windows-and-scenes` + `menus-and-commands` (macOS), `windows-and-navigation` (Windows). The web skills named here have same-named native counterparts, except: `animation` is `styling` on desktop, `responsive-design` is `styling`'s adaptive layout, and `ui-rules` has none — its rules apply as stated.

## 1. Task inventory → information architecture

Navigation is derived, never brainstormed: tasks as *verb + object + outcome* with frequency and stakes; the top three to five define home and the primary nav; groups follow the actor's mental model; **depth budget** — every primary task within **one click** of the shell, the rest within two. Method: [`references/information-architecture.md`](references/information-architecture.md).

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

Any shell: collapsible, never hidden, on desktop; you-are-here on every page; never swallows the page's primary action; home is a screen, not a redirect ([rules](references/information-architecture.md)).

## 3. Page anatomy, by page type

Every page has the same skeleton — **header · optional toolbar · content region(s)** — so people learn it once. What each type is made of and its rules: [`references/page-anatomy.md`](references/page-anatomy.md).

| Page type | Primary action |
|---|---|
| **List** | Create the entity |
| **Detail** | The entity's most frequent state action (Approve, Publish) |
| **Form** (create / edit) | Save (verb + object) |
| **Dashboard** | None, or the top task's entry |
| **Wizard** | Finish (verb + object) |
| **Settings** | Save per section (or autosave with a visible "Saved" state) |

**Where the task happens** — page, drawer, or modal — is `ui-rules`' surface rule; apply it here when assigning a page type: quick peek or edit-with-context → drawer; multi-step, long, or shareable → its own route; blocking modal only when the interruption is the value.

## 4. Form layout

One column; labels above; sections past ~7 fields; mark the optional; prefill the common case; the primary action where the eye ends; unsaved changes guarded; advanced fields behind an expander. In full: [`references/page-anatomy.md`](references/page-anatomy.md).

## 5. Density and hierarchy

**One density**, stated — *comfortable* for occasional use, *compact* for all-day tools. Hierarchy from **three text tones and weight**, not many sizes. In full: [`references/density-and-feedback.md`](references/density-and-feedback.md).

## 6. Expert accelerators

Frequent users outgrow the nav within a week: a command palette (`⌘K` / `Ctrl+K`) past ~20 destinations, shortcuts for the top three tasks, saved views, recents, bulk actions. In full: [`references/accelerators-and-first-run.md`](references/accelerators-and-first-run.md).

## 7. Feedback and notifications

The user must never wonder whether something happened: **inline state first**; a **toast** for off-screen success; **persistent** for failure; a **notification centre** only for real asynchronous events. The table: [`references/density-and-feedback.md`](references/density-and-feedback.md).

## 8. First run and progressive disclosure

First run is a setup checklist of real actions, not a tour; disclosure stages, never hides. In full: [`references/accelerators-and-first-run.md`](references/accelerators-and-first-run.md).

## 9. The responsiveness budget

Perceived speed is a design requirement; the build meets it or the feature is not done.

| Window | The user must see | Owner of the mechanics |
|---|---|---|
| **≤ 100 ms** after any press | The control acknowledges: pressed state; a submit button disables and shows its in-flight state; a toggle flips immediately | the stack's `animation` (hover/press) · `forms` (submit state) |
| **≤ 300 ms** for a load | If not finished, a **skeleton shaped like the coming content** in the region — never a page-centre spinner, never a blank | the stack's `error-handling` (three-state regions) |
| **~4 s** still loading | The region acknowledges it is alive ("Still loading…" / progress) | `error-handling`'s soft threshold |
| **Timeout budget** | A failed state with a retry, scoped to the region | `error-handling` |

Optimism only where reversible (never money, sends, deletes); no layout shift; one region's wait never blocks the page. Measured as **Core Web Vitals** at p75 — **LCP < 2.5 s · INP < 200 ms · CLS < 0.1**. In full: [`references/responsiveness-and-search.md`](references/responsiveness-and-search.md).

## 10. Search results and filtering

The **result set** after §6's search: visible removable filters, quick filters instant, zero results offers an action, query and filters in the URL and kept on return. In full: [`references/responsiveness-and-search.md`](references/responsiveness-and-search.md).

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

Numbered because audit finding ids cite the numbers: new checks are appended, and none is renumbered or removed (a retired check keeps its number and says *retired*).

1. Every primary task is within one click of the shell; nothing the inventory ranks high is at depth three.
2. Nav groups follow the actor's mental model; every destination serves a listed task; every frequent task has a destination.
3. One shell, decided once, identical on every page; you-are-here on every page; the page's primary action is in the page header, not the shell.
4. Every screen names its page type, its surface, its primary action, and its regions' states.
5. Forms are one column, labels above, sectioned past ~7 fields, optional marked, common case prefilled, primary action at the end.
6. One density, stated; hierarchy by tone and weight.
7. Accelerators match the app's size — a command palette past ~20 destinations, shortcuts for the top three tasks, saved views on daily lists.
8. Feedback follows the §7 table: inline first, toast for off-screen success, persistent for failure, a notification centre only for real asynchronous events.
9. First run is a checklist of real actions; disclosure stages, never hides.
10. The §9 budget is written into acceptance criteria, and its Core Web Vitals form (LCP < 2.5 s · INP < 200 ms · CLS < 0.1 at p75) is the number the build is measured on.
11. Search results carry visible removable filters, a query in the URL, and a zero-results state that offers an action (§10).

## What NOT to do

- No nav that mirrors the schema or the org chart; no "Manage" / "Tools" / "More" as a destination.
- No shell that changes between pages; no page's primary action buried in a shell menu; no hamburger on desktop.
- No dashboard tile without a link to what it counts; no dashboard as the home of a single-task tool.
- No multi-column forms; no placeholder-as-label; no asterisk on every field; no long form in a modal.
- No wizard for three independent fields; no tour where a checklist would do; no recurring tips.
- No page-centre spinner; no blank region while loading; no toast for what the screen already shows; no empty notification bell.
- No optimistic update on money, sends, or deletes.
- No zero-results dead end; no Apply button on a quick filter; no facet that returns nothing; no search whose query and filters vanish from the URL or on the way back from a result.
