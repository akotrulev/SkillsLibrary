---
name: ui-code-audit
description: Use when auditing UI source against the web interface guidelines (aria-labels, div onClick, unlabeled inputs). Triggers "pre-ship UI code audit". Not for UX review (ux-review).
metadata:
  version: "1.2.0"
disable-model-invocation: true
---

# Web Interface Guidelines — code-level UI audit

Reviews UI **source files** against the web interface guidelines and
reports terse `file:line` findings. This is the **code-level** altitude — it
reads markup, attributes, and interaction handlers in the files you point it at
(is the icon button missing `aria-label`, is navigation a `<div onClick>`, does
the animation honor `prefers-reduced-motion`). It does **not** judge flows,
information architecture, or visual taste — those are other skills (see the
fence below).

**Corpus authority.** The facts this skill decides with come from the [`design:corpus`](../ui-ux-pro-max/SKILL.md) corpus — **it is the source of truth, and where it and this skill disagree on a fact, the corpus wins.** The guidelines ruleset below is one of two rulesets: the corpus adds 119 UX guidelines with paired good/bad code examples, 44 React/Next performance rules, and per-stack conventions for all 22 supported stacks. Run both:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/scripts/search.py" "<pattern you found>" --domain ux
python3 "${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/scripts/search.py" "<pattern you found>" --domain react
python3 "${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/scripts/search.py" "<pattern you found>" --stack <detected stack>
```

A corpus row's severity is the finding's severity.

## How it works — local-first

The ruleset lives at [`references/guidelines.md`](references/guidelines.md).
The audit works with no network.

1. **Read `references/guidelines.md`** — the baseline. This always works.
2. **Read the target files** (the `<file-or-pattern>` argument). If none was
   given, ask which files/pattern to review.
3. **Apply every rule** from the guidelines to each file, skipping a rule
   tagged for another stack (**[React]**, **[Next.js]**, **[Tailwind]**).
4. **Output findings** as terse `file:line` lines — grouped by file, one issue
   + location per line, `✓ pass` for a clean file, no preamble, no explanation
   unless the fix is non-obvious.

## What it checks

The ruleset covers, per file: accessibility (semantic HTML before ARIA,
labeled controls, keyboard handlers), focus states, forms, animation
(`prefers-reduced-motion`, compositor-friendly properties), typography, content
handling and empty states, image dimensions (CLS), performance (list
virtualization, no layout reads in render), navigation & URL state, touch,
safe-area/layout, dark-mode/theming, i18n formatting, hydration safety, hover
states, and an explicit anti-pattern list to flag. Its rules are framework-neutral
web rules unless tagged for one stack; code named in a rule's parentheses is an
example for a stack, not the rule. It is a web ruleset: a native app is judged
as *On a native app* says.

## House overrides

The ruleset's **Content & Copy** section (Title Case for headings and
buttons, `&` over "and", …) is **superseded by
[`design/ux-writing`](../ux-writing/SKILL.md)** — sentence case, active verb
labels, one voice across both stacks. The audit emits **no findings** from that
section; a label that follows `ux-writing` is correct. Every other section of
the ruleset applies unchanged.

## On a native app

React Native, SwiftUI, Jetpack Compose, WinUI, WPF and AppKit have no web
markup, so `references/guidelines.md` does not apply. G is judged against the
corpus instead, citing the row or item each verdict rests on:

- the app/native interface rows: `search.py "<pattern>" --domain web`;
- the detected stack's file: `search.py "<pattern>" --stack <stack>` (the corpus
  has none for AppKit: say so, as for a zero-result search);
- the *Pre-Delivery Checklist* in [`pro-rules.md`](../ui-ux-pro-max/references/pro-rules.md),
  its Interaction, Light/Dark Mode, Layout and Accessibility items (its Process
  items say how to check, not what). Touch and safe-area rows and items are
  mobile-only; on desktop, `quick-reference.md` §1–§3 stands in, as pro-rules'
  scope notice says.

**Ids.** That checklist is unnumbered and is the corpus's, not this skill's, so
a native finding keeps the number of the check below whose topic it breaks; the
`web` rows' categories line up: Accessibility G1, Forms G3, Animation G4,
Typography G5, Performance G8, Navigation and State G9, Touch G10, Safe Areas
G11, Theming G12, Feedback G15, Anti-Pattern G16. G14 is N/A on native. No
second ruleset is written here.

**G judges the interface the code produces** (labels, targets, states, insets,
contrast), never the stack's code conventions (state ownership, concurrency,
lifecycle, test ids); those are the stack's `/<plugin>:audit`, listed as a
handoff.

## Review checklist

The form `/design:audit` sweeps as section G: one check per section of `references/guidelines.md`, in the ruleset's order, or per topic on a native app. A finding id names the section broken (`G3` is Forms) and its `file:line` names the rule. The list is numbered because finding ids cite the numbers: new checks are appended, none is renumbered or removed.

1. **Accessibility**: labelled controls, semantic elements before ARIA, keyboard handlers, alt text, live regions.
2. **Focus states**: a visible `:focus-visible` indicator, never a bare `outline: none`.
3. **Forms**: `autocomplete`, the right `type`, clickable labels, inline errors, paste never blocked, an unsaved-changes guard.
4. **Animation**: `prefers-reduced-motion` honoured, transform and opacity only, no `transition: all`, interruptible.
5. **Typography**: `…`, curly quotes, non-breaking spaces, tabular numbers, balanced headings.
6. **Content handling**: long, short and empty content all render.
7. **Images**: explicit dimensions, lazy below the fold, priority above it.
8. **Performance**: large lists virtualized, no layout reads in render, preconnect and font preload.
9. **Navigation and state**: state in the URL, real links, destructive actions confirmed or undoable.
10. **Touch and interaction**: `touch-action`, `overscroll-behavior` in overlays, `autoFocus` used sparingly.
11. **Safe areas and layout**: safe-area insets, no stray scrollbars, CSS layout over JS measurement.
12. **Dark mode and theming**: `color-scheme`, `theme-color`, explicit colours on a native `<select>`.
13. **Locale and i18n**: `Intl` formatting, language from the browser, `translate="no"` on identifiers.
14. **Hydration safety**: controlled inputs have `onChange`, date rendering is guarded.
15. **Hover and interactive states**: every control has a hover state, and states gain contrast.
16. **Anti-patterns**: nothing from the ruleset's flagged list is present.

*Content & Copy* has no number: it is superseded, as *House overrides* says.

## Do NOT use for

- **Experience-level review** — flows, friction, Nielsen heuristics, IA →
  [`design/ux-review`](../ux-review/SKILL.md). This skill audits the
  code; ux-review audits the experience.
- **Automated a11y scanning** (axe / Lighthouse, per-state WCAG scans, CI
  budgets) → qa `accessibility-testing`. This skill reads source statically; it
  does not run a scanner against a live page.
- **Visual taste / identity** — palette, type, composition → [`design/visual-identity`](../visual-identity/SKILL.md).
- **Copy wording** — the words inside the UI → [`design/ux-writing`](../ux-writing/SKILL.md).
