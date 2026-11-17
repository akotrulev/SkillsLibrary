# Web Interface Guidelines

The ruleset [`ui-code-audit`](../SKILL.md) applies to web UI source. Sections are numbered 1–16 to match that skill's `## Review checklist`, so a section number is a check number. *Content & Copy* is unnumbered: it is superseded.

**Stack tags.** A rule tagged **[React]**, **[Next.js]** or **[Tailwind]** applies only on that stack; skip it elsewhere. An untagged rule applies to any web stack, and code in its parentheses is an example of the rule, not the rule.

## 1. Accessibility

- Icon-only buttons need `aria-label`
- Form controls need `<label>` or `aria-label`
- Interactive elements need keyboard handlers (React `onKeyDown`/`onKeyUp`)
- `<button>` for actions, `<a>` for navigation (React `<Link>`, Blazor `NavLink`), not `<div onClick>`
- Images need `alt` (or `alt=""` if decorative)
- Decorative icons need `aria-hidden="true"`
- Async updates (toasts, validation) need `aria-live="polite"`
- Use semantic HTML (`<button>`, `<a>`, `<label>`, `<table>`) before ARIA
- Headings hierarchical `<h1>`–`<h6>`; include skip link for main content
- `scroll-margin-top` on heading anchors

## 2. Focus States

- Interactive elements need a visible focus indicator (Tailwind `focus-visible:ring-*`, or equivalent CSS)
- Never `outline: none` (Tailwind `outline-none`) without focus replacement
- Use `:focus-visible` over `:focus` (avoid focus ring on click)
- Group focus with `:focus-within` for compound controls

## 3. Forms

- Inputs need `autocomplete` and meaningful `name`
- Use correct `type` (`email`, `tel`, `url`, `number`) and `inputmode`
- Never block paste (`onPaste` + `preventDefault`)
- Labels clickable (`<label for>`, React `htmlFor`, or wrapping control)
- Disable spellcheck on emails, codes, usernames (`spellcheck="false"`, React `spellCheck={false}`)
- Checkboxes/radios: label + control share single hit target (no dead zones)
- Submit button stays enabled until request starts; spinner during request
- Errors inline next to fields; focus first error on submit
- Placeholders end with `…` and show example pattern
- `autocomplete="off"` on non-auth fields to avoid password manager triggers
- Warn before navigation with unsaved changes (`beforeunload` or router guard)

## 4. Animation

- Honor `prefers-reduced-motion` (provide reduced variant or disable)
- Animate `transform`/`opacity` only (compositor-friendly)
- Never `transition: all`—list properties explicitly
- Set correct `transform-origin`
- SVG: transforms on `<g>` wrapper with `transform-box: fill-box; transform-origin: center`
- Animations interruptible—respond to user input mid-animation

## 5. Typography

- `…` not `...`
- Curly quotes `"` `"` not straight `"`
- Non-breaking spaces: `10&nbsp;MB`, `⌘&nbsp;K`, brand names
- Loading states end with `…`: `"Loading…"`, `"Saving…"`
- `font-variant-numeric: tabular-nums` for number columns/comparisons
- Use `text-wrap: balance` or `text-pretty` on headings (prevents widows)

## 6. Content Handling

- Text containers handle long content (truncation, line clamping or word breaking; Tailwind `truncate`, `line-clamp-*`, `break-words`)
- Flex children need `min-width: 0` (Tailwind `min-w-0`) to allow text truncation
- Handle empty states—don't render broken UI for empty strings/arrays
- User-generated content: anticipate short, average, and very long inputs

## 7. Images

- `<img>` needs explicit `width` and `height` (prevents CLS)
- Below-fold images: `loading="lazy"`
- Above-fold critical images: `fetchpriority="high"` (Next.js `priority`)

## 8. Performance

- Large lists (>50 items): virtualize (`content-visibility: auto`; React `virtua`, Blazor `<Virtualize>`)
- No layout reads in render (`getBoundingClientRect`, `offsetHeight`, `offsetWidth`, `scrollTop`)
- Batch DOM reads/writes; avoid interleaving
- **[React]** Prefer uncontrolled inputs; controlled inputs must be cheap per keystroke
- Add `<link rel="preconnect">` for CDN/asset domains
- Critical fonts: `<link rel="preload" as="font">` with `font-display: swap`

## 9. Navigation & State

- URL reflects state—filters, tabs, pagination, expanded panels in query params
- Links use `<a>` (React `<Link>`, Blazor `NavLink`) for Cmd/Ctrl+click, middle-click support
- Deep-link all stateful UI (React: if it uses `useState`, consider URL sync via nuqs or similar)
- Destructive actions need confirmation modal or undo window—never immediate

## 10. Touch & Interaction

- `touch-action: manipulation` (prevents double-tap zoom delay)
- `-webkit-tap-highlight-color` set intentionally
- `overscroll-behavior: contain` in modals/drawers/sheets
- During drag: disable text selection, `inert` on dragged elements
- `autofocus` (React `autoFocus`) sparingly—desktop only, single primary input; avoid on mobile

## 11. Safe Areas & Layout

- Full-bleed layouts need `env(safe-area-inset-*)` for notches
- Avoid unwanted scrollbars: `overflow-x: hidden` (Tailwind `overflow-x-hidden`) on containers, fix content overflow
- Flex/grid over JS measurement for layout

## 12. Dark Mode & Theming

- `color-scheme: dark` on `<html>` for dark themes (fixes scrollbar, inputs)
- `<meta name="theme-color">` matches page background
- Native `<select>`: explicit `background-color` and `color` (Windows dark mode)

## 13. Locale & i18n

- Dates/times: locale-aware formatting (JS `Intl.DateTimeFormat`), not hardcoded formats
- Numbers/currency: locale-aware formatting (JS `Intl.NumberFormat`), not hardcoded formats
- Detect language via `Accept-Language` / `navigator.languages`, not IP
- Brand names, code tokens, identifiers: wrap with `translate="no"` to prevent garbled auto-translation

## 14. Hydration Safety

- **[React]** Inputs with `value` need `onChange` (or use `defaultValue` for uncontrolled)
- Date/time rendering: guard against hydration mismatch (server vs client)
- **[React]** `suppressHydrationWarning` only where truly needed

## 15. Hover & Interactive States

- Buttons/links need a `:hover` state (Tailwind `hover:`) for visual feedback
- Interactive states increase contrast: hover/active/focus more prominent than rest

## Content & Copy (superseded)

Superseded by [`design/ux-writing`](../../ux-writing/SKILL.md): no findings come from this section. Kept for reference only.

- Active voice: "Install the CLI" not "The CLI will be installed"
- Title Case for headings/buttons (Chicago style)
- Numerals for counts: "8 deployments" not "eight"
- Specific button labels: "Save API Key" not "Continue"
- Error messages include fix/next step, not just problem
- Second person; avoid first person
- `&` over "and" where space-constrained

## 16. Anti-patterns (flag these)

- `user-scalable=no` or `maximum-scale=1` disabling zoom
- `onPaste` with `preventDefault`
- `transition: all`
- `outline: none` (Tailwind `outline-none`) without focus-visible replacement
- Inline click-handler navigation (React `onClick`, Blazor `@onclick` calling `NavigateTo`) without `<a>`
- `<div>` or `<span>` with click handlers (should be `<button>`)
- Images without dimensions
- Large lists rendered without virtualization (React `.map()`, Blazor `@foreach`)
- Form inputs without labels
- Icon buttons without `aria-label`
- Hardcoded date/number formats (JS: use `Intl.*`)
- `autofocus` (React `autoFocus`) without clear justification
