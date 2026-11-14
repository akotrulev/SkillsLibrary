---
name: ui-code-audit
description: Use when auditing UI source against the web interface guidelines (aria-labels, div onClick, unlabeled inputs). Triggers "pre-ship UI code audit". Not for UX review (ux-review).
metadata:
  version: "1.1.0"
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
3. **Apply every rule** from the guidelines to each file.
4. **Output findings** in the guidelines' terse `file:line` format — grouped by
   file, one issue + location per line, `✓ pass` for a clean file, no preamble.

## What it checks

The ruleset covers, per file: accessibility (semantic HTML before ARIA,
labeled controls, keyboard handlers), focus states, forms, animation
(`prefers-reduced-motion`, compositor-friendly properties), typography, content
handling and empty states, image dimensions (CLS), performance (list
virtualization, no layout reads in render), navigation & URL state, touch,
safe-area/layout, dark-mode/theming, i18n formatting, hydration safety, hover
states, copy, and an explicit anti-pattern list to flag.

## House overrides

The ruleset's **Content & Copy** section (Title Case for headings and
buttons, `&` over "and", …) is **superseded by
[`design/ux-writing`](../ux-writing/SKILL.md)** — sentence case, active verb
labels, one voice across both stacks. The audit emits **no findings** from that
section; a label that follows `ux-writing` is correct. Every other section of
the ruleset applies unchanged.

## Do NOT use for

- **Experience-level review** — flows, friction, Nielsen heuristics, IA →
  [`design/ux-review`](../ux-review/SKILL.md). This skill audits the
  code; ux-review audits the experience.
- **Automated a11y scanning** (axe / Lighthouse, per-state WCAG scans, CI
  budgets) → qa `accessibility-testing`. This skill reads source statically; it
  does not run a scanner against a live page.
- **Visual taste / identity** — palette, type, composition → [`design/visual-identity`](../visual-identity/SKILL.md).
- **Copy wording** — the words inside the UI → [`design/ux-writing`](../ux-writing/SKILL.md).
