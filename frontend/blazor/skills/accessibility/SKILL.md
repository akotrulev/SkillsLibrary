---
name: accessibility
description: Use when making a Blazor app (.NET 8/9/10) accessible as you build — semantic-first markup, focus management under enhanced navigation (`FocusOnNavigate`, dialog focus traps), keyboard + ARIA in custom widgets, live-region announcements, skip links, icon-button labels. Triggers: "make this Blazor component accessible", "keyboard nav for a custom widget", "focus isn't announced after navigation". Do NOT use to SCAN for violations (qa `accessibility-testing`) or form validation a11y (`forms`).
---

# Blazor — Accessibility

Standardizes **authoring** accessible Blazor UIs. Targets **WCAG 2.2 AA** as the baseline. The house rule mirrors the React sibling: **lean on the platform** (real `<button>`, `<a href>`, `<dialog>`, `<label>`), reach for ARIA only when no semantic element exists, and manage the one thing an SPA-style app breaks that a classic page load gave for free — **focus and announcement on navigation**.

**Boundary — authoring, not scanning.** This skill makes the app accessible as you build it. *Verifying* it (automated axe/Lighthouse scans, WCAG audit gates in CI) is qa's [`accessibility-testing`](../../../qa) — a **peer** the orchestrator invokes separately, never loaded here. Build accessible; let QA prove it.

**What of WCAG 2.2 is *not* here.** Nine criteria are new in 2.2 and most are **design decisions made before this skill runs** — target size (2.5.8), a non-drag alternative (2.5.7), accessible authentication (3.3.8), redundant entry (3.3.7), consistent help (3.2.6), focus not obscured (2.4.11/2.4.12) and focus appearance (2.4.13). They belong to `design/accessible-by-design`; this skill implements what that decided (the focus token, the alternative control, the carried-forward value) and never invents it. A build cannot reach 2.2 AA from this file alone.

**Version rule:** the accessibility *concepts* are version-agnostic. The **net-sensitive** bits are navigation-side: `FocusOnNavigate` (net6+, but the default Blazor Web App template wires it in the `Routes.razor` from net8), and **enhanced navigation** (net8+, default in static SSR) — which swaps DOM without a full reload, so a screen reader is *not* told the page changed unless you manage focus/announcement yourself. net10 keeps the same APIs; the enhanced-nav focus gap is the same across net8/9/10.

## When to use

- Designing a custom interactive widget (menu, combobox, tabs, tree) with correct semantics + keyboard
- Focus after navigation / focus trap in a dialog / restore-focus on close
- Announcing route changes and async results (save done, N rows loaded) to a screen reader
- Adding a skip-to-content link
- Labeling icon-only buttons (row actions in a shared grid renderer especially)
- Reviewing a component for keyboard-only and screen-reader usability

## When NOT to use

- Scanning/auditing for violations (axe / Lighthouse / Pa11y CI gate) → qa `accessibility-testing` (peer, not loaded)
- Form input labels + validation-message a11y → [`forms`](../forms/SKILL.md)
- Contrast *token* setup / `focus-visible` styling mechanics → [`styling`](../styling/SKILL.md) (this skill owns *whether* contrast passes; styling owns *how* the tokens are defined)
- Component-library primitives that already ship a11y (MudBlazor dialog, Fluent tabs) → [`component-library`](../component-library/SKILL.md) (use them instead of hand-rolling)
- React → `frontend/react/skills/accessibility`

## Lean on the platform

Most a11y bugs come from re-implementing in `<div>` what the browser gives free. The browser does focus, keyboard, ARIA mapping, and form submission correctly — the moment you replace them, you own them.

| Want | Use — not |
|---|---|
| Click **and** keyboard activation | `<button>` — never `<div @onclick>` (no focus, no Enter/Space, no role) |
| Navigate to a URL | `<a href>` / `<NavLink>` — never a click-handler-only `NavigateTo` button (also a [`component-writer`](../component-writer/SKILL.md) rule) |
| Submit a form | `<button type="submit">` inside `<EditForm>` |
| Modal dialog | native `<dialog>` or a library dialog (focus trap + Esc for free) — never a `<div>` overlay |
| Label a control | `<label for>` / wrap — never placeholder-as-label |
| Loading | `aria-busy="true"` + a visible indicator |
| Page regions | `<nav>` / `<main>` (one) / `<footer>` — the `navigation` / `main` / `contentinfo` landmarks let a screen reader jump between regions; never rebuild them from `<div>`s |
| A link that opens a new tab | real `<a target="_blank" rel="noopener">` **plus** a visible "opens in new tab" cue and an `aria-label` suffix ("… (opens in new tab)") — the emission is [`component-writer`](../component-writer/SKILL.md)'s |

**Landmarks come from the elements.** Wrapping the header nav in `<nav>`, the primary content in a single `<main>`, and the site footer in `<footer>` gives screen-reader users a region map for free (and satisfies the [`ui-rules`](../ui-rules/SKILL.md) footer/nav conventions). Add `aria-label` to distinguish multiple `<nav>`s ("Primary", "Breadcrumb").

**First rule of ARIA: don't use ARIA if a semantic element will do.** ARIA is a patch for missing semantics — a wrong `role`/`aria-*` is worse than none. Reach for it only for custom widgets with no native equivalent, live regions, and relationships (`aria-describedby`/`aria-controls`/`aria-labelledby`). When you must, follow the **ARIA Authoring Practices Guide (APG)** patterns verbatim.

## Focus management under enhanced navigation — the Blazor-specific gap

A classic full-page load moves focus to the top and the screen reader announces the new document. Blazor **enhanced navigation** (default for static SSR; also interactive routing) patches the DOM in place — **no reload, so nothing is announced and focus stays where it was** (often on a now-removed link). You must restore it.

**1. `FocusOnNavigate` — focus the `<h1>` on every route change.** The template wires it in `Routes.razor`; keep it, and give every page a single top-level `<h1>`:

```razor
@* Routes.razor *@
<Router AppAssembly="@typeof(Program).Assembly">
    <Found Context="routeData">
        <RouteView RouteData="@routeData" DefaultLayout="@typeof(Layout.MainLayout)" />
        <FocusOnNavigate RouteData="@routeData" Selector="h1" />
    </Found>
</Router>
```

- The `Selector` element must be **focusable** — `FocusOnNavigate` adds `tabindex="-1"` to the matched `<h1>` so it can receive programmatic focus without entering the tab order. One `<h1>` per page (also good document structure).
- **Enhanced-nav edge case:** for navigations that don't re-run the Router's `Found` (in-page enhanced form posts, `data-enhance` updates), hook the JS `enhancedload` event to re-assert focus/announcement:
  ```js
  Blazor.addEventListener('enhancedload', () => { /* move focus to the updated region's heading, or announce */ });
  ```

**2. Programmatic focus** — `ElementReference.FocusAsync()` after an action that changes context (open a panel, reveal an error summary, focus the first invalid field on submit):

```razor
<input @ref="_search" />
@code {
    private ElementReference _search;
    protected override async Task OnAfterRenderAsync(bool firstRender)
    {
        if (firstRender) await _search.FocusAsync();   // or after revealing a region
    }
}
```
Use the `autofocus` attribute only for a page's single primary input; scripted `FocusAsync` for everything conditional.

**3. Dialogs — trap while open, restore on close.** A native `<dialog>` opened with `showModal()` traps focus and closes on `Esc` for free — prefer it (or a library dialog that does the same). If you hand-roll an overlay you own: move focus into the dialog on open, **trap** Tab within it (first↔last wrap), close on `Esc`, and **restore focus to the invoking element** on close. Never leave focus stranded behind a modal.

## Live-region announcements

Focus handles "where am I"; a **live region** handles "something just happened" without moving focus. Render a persistent, visually-hidden region and write to it:

```razor
<div aria-live="polite" role="status" class="visually-hidden">@_announcement</div>
@* "Order saved.", "12 results loaded.", "Filter applied — 0 matches." *@
```

- `aria-live="polite"` / `role="status"` — waits for a pause (async results, save confirmations, result counts). `role="alert"` / `aria-live="assertive"` — interrupts (errors only; use sparingly).
- The region must exist in the DOM **before** you write to it — swapping the whole node in doesn't announce. Update its text content, not its presence.
- **Route-change announcement:** `FocusOnNavigate` covers most cases; add a polite region announcing the new page name for flows where focusing `<h1>` isn't enough (e.g. wizard steps that keep focus in the form).
- A component library's snackbar/toast is often already a live region — verify (`role="status"`) rather than double-announcing.

## Keyboard + ARIA in custom widgets

If you can't use a library primitive, follow the **APG** for the widget: correct `role`, the expected key map, and managed focus.

| Widget | Keys (APG) | Focus model |
|---|---|---|
| Menu / menubar | `↑↓` move, `Enter`/`Space` activate, `Esc` close, `Home/End` | roving `tabindex` (one item tabbable) |
| Tabs | `←→` between tabs, `Enter`/`Space` (or auto) select | roving `tabindex`; `aria-selected` |
| Combobox | `↓` open, `↑↓` options, `Enter` commit, `Esc` cancel | `aria-expanded`/`aria-activedescendant` |
| Tree | `↑↓` nodes, `←→` collapse/expand | roving `tabindex` |

Baseline for **every** interactive element: reachable by `Tab`, activates on `Enter` (links/buttons) or `Space` (buttons/checkboxes), a visible **focus indicator** (never `outline:none` without a replacement — [`styling`](../styling/SKILL.md) owns `:focus-visible`), and logical DOM tab order (avoid `tabindex > 0`). Use **roving tabindex** for composite widgets — one stop for the group, arrows move within — never make every child tabbable.

## Display-level a11y (ui-rules seed §16)

These are the most-missed rules and they scale badly through shared renderers — one omission multiplies across every grid:

- **Every icon-only button gets an accessible label.** A bare `<MudIconButton Icon="@Icons.Delete" />` announces nothing. Add `Title`/`aria-label` (`"Delete order"`). The **shared grid renderer's built-in row actions** are the highest-leverage spot: one missing label there un-labels *every* grid in the app — fix it on the renderer, per [`ui-rules`](../ui-rules/SKILL.md) renderer unification. (Note: this label is a **separate** attribute from the `data-testid` [`test-ids`](../test-ids/SKILL.md) owns — never mirror one into the other.)
- **Never signal state by color or icon alone** (a red dot, a green check). ~1 in 12 men can't distinguish red/green; a screen reader sees nothing. Pair every color/icon state with **text or a labeled tooltip** ("Active", "Failed"). The **current nav location** is a state too — mark the active item with more than color (weight, an indicator, and `aria-current="page"` on the `NavLink`), never a color change alone (the IA requirement to *show* current location is [`ui-rules`](../ui-rules/SKILL.md)'s).
- **Contrast** — check muted/secondary text and active/hover/selected-row colors against the **actual backgrounds** they render on (a token that passes on white can fail on the striped-row or brand-tinted surface). WCAG 2.2 AA: **4.5:1** body text, **3:1** large text (≥24px, or ≥19px bold) and UI-component/graphic boundaries (input borders, icons, focus rings); AAA is 7:1 if the brief targets it. **Re-verify every pair in dark mode** — a ratio that passes on a light surface routinely fails on a dark one, so dark tokens get their own check, not a reuse. Token *definition* is [`styling`](../styling/SKILL.md)'s; *whether it passes* is this skill's.
- **Consistency within a control group** — if one row action has a tooltip, its siblings must too; if one is icon+label, the group is.

## Rules

- **Semantic element first, ARIA only for the gap** — `<button>`/`<a href>`/`<dialog>`/`<label>` before any `role`/`aria-*`.
- **Keep `FocusOnNavigate`** in `Routes.razor` with a single `<h1>` per page; hook `enhancedload` for enhanced-nav updates the Router doesn't catch.
- **Move focus deliberately** after context changes (`FocusAsync`); trap-and-restore focus in dialogs; prefer native `<dialog>`/library dialogs that do it for you.
- **One persistent polite live region** for async results/counts; `role="alert"` for errors only; update its text, never swap the node.
- **Custom widgets follow the APG** key map + roving tabindex; every interactive element is `Tab`-reachable with a visible focus indicator.
- **Every icon-only button is labeled** (`Title`/`aria-label`), fixed on the shared renderer; **never color/icon alone** for state (including the active nav item — add `aria-current="page"`); contrast checked on the **real** background and **re-checked in dark mode**; consistency within a control group.
- **Real landmark elements** (`<nav>`/`<main>`/`<footer>`) for page regions, `aria-label` on repeated `<nav>`s; a **new-tab link** carries an `aria-label` "(opens in new tab)" suffix + `rel="noopener"`.

## What NOT to do

- No `<div @onclick>` where a `<button>`/`<a>` fits (no keyboard, no focus, no role).
- No page without a focusable `<h1>` + `FocusOnNavigate` — enhanced nav then leaves screen-reader users silently stranded.
- No focus left behind a modal, no dialog without focus trap + restore.
- No live region swapped in at announce time (must pre-exist), no `assertive` for routine updates.
- No custom widget with `<div>`s and click handlers instead of the APG role/keys; no `tabindex > 0`; no `outline:none` without a replacement.
- No icon-only button without a label; no state shown by color/icon alone; no contrast checked only against white when it renders on a tinted surface.
- **Do not run axe/Lighthouse here** — hand that to qa `accessibility-testing`.

## Validation

Inside a `Gate: none` plan task, run none of these checks and report "written, not run"; the plan's gate task runs them.

- **Keyboard-only pass** on every key flow: reach and operate everything with `Tab`/`Shift+Tab`/`Enter`/`Space`/arrows/`Esc`; focus is always visible; no trap outside an intentional modal.
- **Navigate between pages** with a screen reader (or focus-visible eye test): focus lands on the new `<h1>` and the page is announced.
- **Open/close a dialog**: focus enters it, Tab wraps inside, `Esc` closes, focus returns to the trigger.
- **Trigger an async result**: the polite region announces it once, without stealing focus.
- Every **icon-only button** has an audible label; toggle a **state** — it's conveyed by text, not color alone.
- Then hand off to qa `accessibility-testing` for the automated WCAG scan gate.

## Handoffs

- Automated axe/Lighthouse WCAG scan + CI gate → qa `accessibility-testing` (**peer**, not loaded)
- WCAG 2.2 **design-time** criteria (target size, drag alternative, accessible auth, redundant entry, consistent help, focus not obscured), cognitive/neurodiversity design, and layout-for-translation → `design/accessible-by-design`
- Contrast **token** definition + `:focus-visible` styling → [`styling`](../styling/SKILL.md)
- Form-input labels + validation-message a11y → [`forms`](../forms/SKILL.md)
- Accessible library primitives (dialog/tabs/menu that ship a11y) → [`component-library`](../component-library/SKILL.md)
- `data-testid` on the same elements (separate attribute) → [`test-ids`](../test-ids/SKILL.md)
- Icon-button labels / color-not-alone as a *display-correctness* concern → [`ui-rules`](../ui-rules/SKILL.md) (owns the convention; this skill owns the a11y mechanics)
