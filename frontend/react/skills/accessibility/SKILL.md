---
name: fe-react-accessibility
description: Use when a component must work for keyboard and screen-reader users — semantic-first markup, focus management under client-side navigation, keyboard + ARIA in custom widgets via Radix/React Aria, dialog focus trap/restore, live regions. Triggers "make this component accessible", "keyboard nav for a custom widget", "focus isn't announced after navigation", "screen reader skips this control". Not for SCANNING for violations (qa `accessibility-testing`) or form validation a11y (`forms`).
---

# React — Accessibility

Standardizes **authoring** accessible React UIs. Targets **WCAG 2.2 AA** as the baseline. The house rule: **lean on the platform** (real `<button>`, `<a href>`, `<dialog>`, `<label>`), reach for ARIA only when no semantic element exists, use a tested primitive library (Radix / React Aria) for complex widgets, and manage the one thing an SPA/App-Router app breaks that a classic page load gave for free — **focus and announcement on navigation**.

**Boundary — authoring, not scanning.** This skill makes the app accessible as you build it. *Verifying* it (automated axe/Lighthouse scans, WCAG audit gates in CI, screen-reader regression) is qa's `accessibility-testing` — a **peer** the orchestrator invokes separately, never loaded here. `eslint-plugin-jsx-a11y` in the dev loop is fine and expected (it catches the easy mistakes as you type); the *runtime* scan + CI gate is QA's. Build accessible; let QA prove it.

**What of WCAG 2.2 is *not* here.** Nine criteria are new in 2.2 and most are **design decisions made before this skill runs** — target size (2.5.8), a non-drag alternative (2.5.7), accessible authentication (3.3.8), redundant entry (3.3.7), consistent help (3.2.6), focus not obscured (2.4.11/2.4.12) and focus appearance (2.4.13). They belong to `design/accessible-by-design`; this skill implements what that decided (the focus token, the alternative control, the carried-forward value) and never invents it. A build cannot reach 2.2 AA from this file alone.

**Version rule:** the accessibility *concepts* are version-agnostic. React 19's `ref`-as-prop (no `forwardRef`) is how you attach refs for focus management; on React 18 wrap with `forwardRef` (tagged below). The **navigation-focus gap** is the same across App Router (`<Link>` client navigation) and the Vite SPA lane (React Router) — both swap the DOM without a full reload, so nothing is announced unless you manage it.

## When to use

- Designing a custom interactive widget (menu, combobox, tabs, tree, dialog) with correct semantics + keyboard
- Focus after navigation / focus trap in a dialog / restore-focus on close
- Announcing route changes and async results (save done, N rows loaded) to a screen reader
- Adding a skip-to-content link
- Labeling icon-only buttons (row actions in a shared grid especially)
- Reviewing a component for keyboard-only and screen-reader usability

## When NOT to use

- Scanning/auditing for violations (axe / Lighthouse / Pa11y CI gate) → qa `accessibility-testing` (peer, not loaded)
- Form input labels + validation-message a11y → [`forms`](../forms/SKILL.md)
- Contrast *token* setup / `:focus-visible` styling mechanics → [`styling`](../styling/SKILL.md) (this skill owns *whether* contrast passes; styling owns *how* the tokens are defined)
- `prefers-reduced-motion` mechanics on animations → [`animation`](../animation/SKILL.md) (this skill owns *that* motion must respect it; motion owns the how)
- Component-library primitives that already ship a11y (MUI Dialog, Mantine Tabs) → [`component-library`](../component-library/SKILL.md) (use them instead of hand-rolling)
- Blazor → `frontend/blazor/skills/accessibility`

## Lean on the platform

Most a11y bugs come from re-implementing in `<div>` what the browser gives free. The browser does focus, keyboard, ARIA mapping, and form submission correctly — the moment you replace them, you own them.

| Want | Use — not |
|---|---|
| Click **and** keyboard activation | `<button>` — never `<div onClick>` (no focus, no Enter/Space, no role) |
| Navigate to a URL | `<a href>` / `<Link href>` / `<NavLink>` — never a click-handler-only `router.push` on a `<div>` (also a [`component-writer`](../component-writer/SKILL.md) rule) |
| Submit a form | `<button type="submit">` inside `<form>` |
| Modal dialog | native `<dialog>` or a Radix/React Aria/library dialog (focus trap + Esc for free) — never a `<div>` overlay |
| Label a control | `<label htmlFor>` / wrap — never placeholder-as-label |
| Loading | `aria-busy="true"` + a visible indicator |
| Page regions | `<nav>` / `<main>` (one) / `<footer>` — the `navigation`/`main`/`contentinfo` landmarks let a screen reader jump between regions; never rebuild them from `<div>`s |
| A link that opens a new tab | real `<a target="_blank" rel="noopener">` **plus** a visible "opens in new tab" cue and an `aria-label` suffix ("… (opens in new tab)") — emission is [`component-writer`](../component-writer/SKILL.md)'s |

**Landmarks come from the elements.** Wrap the header nav in `<nav>`, the primary content in a single `<main id="main-content">`, and the footer in `<footer>` — that gives screen-reader users a region map for free (and satisfies the [`ui-rules`](../ui-rules/SKILL.md) footer/nav conventions). Add `aria-label` to distinguish multiple `<nav>`s ("Primary", "Breadcrumb").

**First rule of ARIA: don't use ARIA if a semantic element will do.** ARIA is a patch for missing semantics — a wrong `role`/`aria-*` is worse than none. Reach for it only for custom widgets with no native equivalent, live regions, and relationships (`aria-describedby`/`aria-controls`/`aria-labelledby`). When you must, follow the **ARIA Authoring Practices Guide (APG)** patterns verbatim.

## Focus management under client-side navigation — the SPA/App-Router gap

A classic full-page load moves focus to the top and the screen reader announces the new document. A client-side navigation (`next/link`, React Router `<Link>`) **patches the DOM in place — no reload, so nothing is announced and focus stays where it was** (often on a now-removed link). You must restore it. This is the React analog of Blazor's enhanced-navigation focus gap.

**1. On route change, move focus to the new page's `<h1>` and announce it.** Give every page a single top-level `<h1>`, and on navigation focus the main heading (or the `<main>`), then announce via a live region. A small hook in the root layout, keyed on the pathname:

```tsx
'use client';
import { usePathname } from 'next/navigation';   // App Router (Vite: useLocation from react-router)
import { useEffect, useRef } from 'react';

export function RouteFocus({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const mainRef = useRef<HTMLElement>(null);
  const firstRender = useRef(true);
  useEffect(() => {
    if (firstRender.current) { firstRender.current = false; return; }  // don't steal focus on initial load
    mainRef.current?.focus();          // <main tabIndex={-1}> so it can receive programmatic focus
  }, [pathname]);
  return <main id="main-content" ref={mainRef} tabIndex={-1}>{children}</main>;
}
```

- The focus target needs `tabIndex={-1}` so it can receive programmatic focus without entering the tab order.
- Pair with a **skip-to-content link** so keyboard users can jump straight to `#main-content`:
  ```tsx
  <a href="#main-content" className="skip-link">Skip to content</a>
  ```
  ```css
  .skip-link { position: absolute; top: -40px; left: 0; background: #000; color: #fff; padding: 8px; }
  .skip-link:focus { top: 0; }   /* invisible until focused */
  ```

**2. Programmatic focus after a context change** — reveal a panel, show an error summary, focus the first invalid field on submit. Attach a `ref` (a plain prop on React 19; `forwardRef` on 18) and call `.focus()` after the state change:

```tsx
const searchRef = useRef<HTMLInputElement>(null);
useEffect(() => { if (revealed) searchRef.current?.focus(); }, [revealed]);
```

Use the `autoFocus` attribute only for a page's single primary input; scripted focus for everything conditional (a stray `autoFocus` traps screen-reader users).

**3. Dialogs — trap while open, restore on close.** A native `<dialog>` opened with `showModal()` traps focus and closes on `Esc` for free — prefer it, or a **Radix / React Aria Dialog** (focus trap + restore + correct roles built in). If you hand-roll an overlay you own: move focus in on open, **trap** Tab within it (first↔last wrap), close on `Esc`, and **restore focus to the trigger** on close.

```tsx
export function useFocusTrap<T extends HTMLElement>(active: boolean) {
  const ref = useRef<T>(null);
  useEffect(() => {
    if (!active || !ref.current) return;
    const root = ref.current;
    const nodes = root.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
    );
    const first = nodes[0], last = nodes[nodes.length - 1];
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
    };
    root.addEventListener('keydown', onKey);
    return () => root.removeEventListener('keydown', onKey);
  }, [active]);
  return ref;
}
```

Better: don't hand-roll it — Radix/React Aria's `<Dialog>` does trap + restore + `Esc` correctly.

## Live-region announcements

Focus handles "where am I"; a **live region** handles "something just happened" without moving focus. Render a persistent, visually-hidden region and write to it:

```tsx
<div aria-live="polite" role="status" className="sr-only">{announcement}</div>
{/* "Order saved.", "12 results loaded.", "Filter applied — 0 matches." */}
```

- `aria-live="polite"` / `role="status"` — waits for a pause (async results, save confirmations, result counts). `role="alert"` / `aria-live="assertive"` — interrupts (errors only; use sparingly).
- The region must exist in the DOM **before** you write to it — mounting the whole node at announce time doesn't announce. Update its text content, not its presence.
- **Route-change announcement:** the focus hook covers most cases; add a polite region announcing the new page name for flows where focusing `<main>` isn't enough (wizard steps that keep focus in the form).
- A component library's snackbar/toast is often already a live region — verify (`role="status"`) rather than double-announcing.

## Keyboard + ARIA in custom widgets — use a library

The complex APG patterns (combobox, menu, tabs, tree, listbox) have changed across spec revisions and are easy to get subtly wrong. **Use Radix UI or React Aria** (or the component library's primitive) rather than hand-rolling — they ship the correct roles, key maps, roving tabindex, and focus management:

| Widget | Reach for | Keys (APG) it handles |
|---|---|---|
| Dialog / Modal | Radix `Dialog` / React Aria / native `<dialog>` | focus trap, `Esc`, restore, `aria-modal` |
| Menu / Dropdown | Radix `DropdownMenu` / React Aria `Menu` | `↑↓` move, `Enter`/`Space`, `Esc`, type-ahead, roving tabindex |
| Tabs | Radix `Tabs` / React Aria | `←→` between tabs, `aria-selected`, `aria-controls` |
| Combobox / Autocomplete | Downshift / Radix / React Aria `ComboBox` | `↓` open, options, `Enter` commit, `Esc`, `aria-activedescendant` |
| Tree | React Aria `Tree` | `↑↓` nodes, `←→` collapse/expand, roving tabindex |

If you genuinely must build one, follow the **APG** for that widget: correct `role`, the expected key map, and **roving tabindex** (one stop for the group, arrows move within — never make every child tabbable).

Baseline for **every** interactive element: reachable by `Tab`, activates on `Enter` (links/buttons) or `Space` (buttons/checkboxes), a visible **focus indicator** (never `outline:none` without a replacement — [`styling`](../styling/SKILL.md) owns `:focus-visible`), logical DOM tab order (avoid `tabIndex > 0`).

## Images & icons

| Purpose | Render |
|---|---|
| Conveys meaning (photo, chart) | `<img alt="<concise description>" />` (Next `<Image alt>`) |
| Decorative | `alt=""` (empty alt — screen reader skips) — **missing** `alt` is a bug; empty is intentional |
| Icon paired with visible text | `<svg aria-hidden="true">` (the text is the label) |
| Icon-only button | `<button aria-label="Delete order"><TrashIcon aria-hidden="true"/></button>` |

## Display-level a11y (ui-rules cross-cut)

These are the most-missed rules and they scale badly through shared components — one omission multiplies across every grid:

- **Every icon-only button gets an accessible label** (`aria-label`). A bare `<IconButton><TrashIcon/></IconButton>` announces nothing. The **shared grid's row actions** are the highest-leverage spot: one missing label there un-labels *every* grid — fix it on the shared component ([`ui-rules`](../ui-rules/SKILL.md) renderer unification). This label is a **separate** attribute from the `data-testid` [`test-ids`](../test-ids/SKILL.md) owns — never mirror one into the other.
- **Never signal state by color or icon alone** (a red dot, a green check). ~1 in 12 men can't distinguish red/green; a screen reader sees nothing. Pair every color/icon state with **text or a labeled tooltip** ("Active", "Failed"). The **current nav location** is a state too — mark the active item with more than color (weight, an indicator, and `aria-current="page"` on the active `<Link>`).
- **Contrast** — check muted/secondary text and active/hover/selected-row colors against the **actual backgrounds** they render on (a token that passes on white can fail on a striped-row or brand-tinted surface). WCAG 2.2 AA: **4.5:1** body text, **3:1** large text (≥24px, or ≥19px bold) and UI-component/graphic boundaries (input borders, icons, focus rings). **Re-verify every pair in dark mode** — a ratio that passes on a light surface routinely fails on a dark one, so dark tokens get their own check, not a reuse. Token *definition* is [`styling`](../styling/SKILL.md)'s; *whether it passes* is this skill's.
- **Consistency within a control group** — if one row action has a tooltip, its siblings must too; if one is icon+label, the group is.
- **`prefers-reduced-motion`** must be honored on non-essential animation ([`animation`](../animation/SKILL.md) owns the mechanics; this skill owns that it's required).

## React-specific traps

- **`role="button"` on a `<div>`** with `onClick` but no `onKeyDown` — keyboard users can't activate. Use a real `<button>`.
- **`aria-hidden="true"` on a focusable element** — the screen reader hears nothing but the keyboard still lands on it (silent trap).
- **Live region added at render time** — it must be in the DOM *before* the message appears or the SR misses it.
- **Defensive `'use client'` everywhere** dragging semantic server-rendered markup client-side (also a [`performance`](../performance/SKILL.md) cost) — keep semantic content in Server Components.
- **`<select>` replaced by a clever `<div>` dropdown** — the native `<select>` is highly accessible; don't.
- **`outline: none`** without a `:focus-visible` replacement.

## Rules

- **Semantic element first, ARIA only for the gap** — `<button>`/`<a href>`/`<dialog>`/`<label>` before any `role`/`aria-*`.
- **Manage focus + announce on client navigation** (single `<h1>` per page, focus `<main tabIndex={-1}>` on route change); **skip-to-content** link in the layout.
- **Move focus deliberately** after context changes; **trap-and-restore** focus in dialogs; prefer native `<dialog>` / Radix / React Aria that do it for you.
- **One persistent polite live region** for async results/counts; `role="alert"` for errors only; update its text, never mount it at announce time.
- **Complex widgets come from a tested library** (Radix / React Aria / the component library) — don't hand-roll combobox/menu/tabs/tree; if you must, follow the APG + roving tabindex.
- **Every interactive element** is `Tab`-reachable with a visible focus indicator; no `tabIndex > 0`; no `outline:none` without a replacement.
- **Every icon-only button is labeled** (`aria-label`), fixed on the shared component; **never color/icon alone** for state (incl. active nav — add `aria-current="page"`); contrast checked on the **real** background and **re-checked in dark mode**; consistency within a control group.
- **Images have `alt`** (`alt=""` for decorative); icons paired with text are `aria-hidden`.
- **Real landmark elements** (`<nav>`/`<main>`/`<footer>`), `aria-label` on repeated `<nav>`s; new-tab links carry an `aria-label` "(opens in new tab)" suffix + `rel="noopener"`.
- **`eslint-plugin-jsx-a11y`** in the dev loop (the runtime scan is QA's).

## What NOT to do

- No `<div onClick>` where a `<button>`/`<a>` fits; no `role="button"` div without `onKeyDown`.
- No page without a focusable `<h1>`/`<main>` + route-change focus — client nav then leaves screen-reader users silently stranded.
- No focus left behind a modal; no dialog without focus trap + restore; no hand-rolled combobox/menu where a library exists.
- No live region mounted at announce time (must pre-exist); no `assertive` for routine updates.
- No `tabIndex > 0`; no `outline:none` without a replacement; no `aria-hidden` on a focusable element.
- No icon-only button without a label; no state shown by color/icon alone; no contrast checked only against white when it renders on a tinted/dark surface.
- No `<img>` without `alt`; no placeholder-as-label; no `<select>` re-implemented as a `<div>`.
- No defensive `'use client'` dragging semantic content client-side.
- No reliance on `:hover` alone to reveal important info (tooltips, truncated-value reveals) — keyboard and touch users never trigger it; pair with focus or make it visible by default.
- **Do not run axe/Lighthouse here** — hand that to qa `accessibility-testing`.

## Validation

Inside a `Gate: none` plan task, run none of these checks and report "written, not run"; the plan's gate task runs them.

- **Keyboard-only pass** on every key flow: reach and operate everything with `Tab`/`Shift+Tab`/`Enter`/`Space`/arrows/`Esc`; focus is always visible; no trap outside an intentional modal.
- **Navigate between routes** with a screen reader (or focus-visible eye test): focus lands on the new page's `<main>`/`<h1>` and the page is announced.
- **Open/close a dialog**: focus enters it, Tab wraps inside, `Esc` closes, focus returns to the trigger.
- **Trigger an async result**: the polite region announces it once, without stealing focus.
- Every **icon-only button** has an audible label; toggle a **state** — it's conveyed by text, not color alone.
- **Zoom to 200%** — layout stays usable, no clipped content, no horizontal scroll trap.
- **High-contrast / forced-colors mode** — the page stays readable (borders/focus rings don't vanish when custom colors are overridden).
- Then hand off to qa `accessibility-testing` for the automated WCAG scan gate.

## Handoffs

- Automated axe/Lighthouse WCAG scan + CI gate → qa `accessibility-testing` (**peer**, not loaded)
- WCAG 2.2 **design-time** criteria (target size, drag alternative, accessible auth, redundant entry, consistent help, focus not obscured), cognitive/neurodiversity design, and layout-for-translation → `design/accessible-by-design`
- Contrast **token** definition + `:focus-visible` styling → [`styling`](../styling/SKILL.md)
- Form-input labels + validation-message a11y → [`forms`](../forms/SKILL.md)
- `prefers-reduced-motion` animation mechanics → [`animation`](../animation/SKILL.md)
- Accessible library primitives (dialog/tabs/menu that ship a11y) → [`component-library`](../component-library/SKILL.md)
- `data-testid` on the same elements (separate attribute) → [`test-ids`](../test-ids/SKILL.md)
- Icon-button labels / color-not-alone as a *display-correctness* concern → [`ui-rules`](../ui-rules/SKILL.md) (owns the convention; this skill owns the a11y mechanics)
