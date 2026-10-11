---
name: ui-code-audit
description: Use for a CODE-level UI audit — read UI source files and flag violations of the vendored Vercel Web Interface Guidelines: missing aria-labels, `<div onClick>` navigation, unlabeled inputs, `transition: all`. Runs offline against the pinned snapshot. Triggers "audit my UI code against web interface guidelines", "pre-ship UI code audit", "review this markup before we ship". Not for experience-level review (`design:ux-review`) or axe/Lighthouse scanning (qa `accessibility-testing`).
metadata:
  author: vercel
  version: "1.1.0"
---

# Web Interface Guidelines — code-level UI audit

Reviews UI **source files** against the Vercel Web Interface Guidelines and
reports terse `file:line` findings. This is the **code-level** altitude — it
reads markup, attributes, and interaction handlers in the files you point it at
(is the icon button missing `aria-label`, is navigation a `<div onClick>`, does
the animation honor `prefers-reduced-motion`). It does **not** judge flows,
information architecture, or visual taste — those are other skills (see the
fence below).

**Corpus authority.** The facts this skill decides with come from the vendored [`design:corpus`](../ui-ux-pro-max/SKILL.md) corpus — **it is the source of truth, and where it and this skill disagree on a fact, the corpus wins.** The Vercel snapshot below is one of two rulesets: the corpus adds 119 UX guidelines with paired good/bad code examples, 44 React/Next performance rules, and per-stack conventions for all 22 supported stacks. Run both:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/scripts/search.py" "<pattern you found>" --domain ux
python3 "${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/scripts/search.py" "<pattern you found>" --domain react
python3 "${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/scripts/search.py" "<pattern you found>" --stack <detected stack>
```

A corpus row's severity is the finding's severity.

## How it works — local-first

The ruleset is vendored at [`references/guidelines.md`](references/guidelines.md)
— a pinned snapshot of Vercel's upstream `command.md` (provenance in the file
header and in [`../ATTRIBUTIONS.md`](../ATTRIBUTIONS.md)). The audit works with
no network.

1. **Read `references/guidelines.md`** — the pinned baseline. This always works.
2. *Optional freshness step:* if the network is available, WebFetch the upstream
   URL below and prefer it **only if it parses cleanly**. On any failure
   (offline, fetch error, unexpected content) fall back **silently** to the
   vendored copy. Never hard-fail on the fetch — a missing network is normal.
   ```
   https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
   ```
3. **Read the target files** (the `<file-or-pattern>` argument). If none was
   given, ask which files/pattern to review.
4. **Apply every rule** from the guidelines to each file.
5. **Output findings** in the guidelines' terse `file:line` format — grouped by
   file, one issue + location per line, `✓ pass` for a clean file, no preamble.

## What it checks

The vendored ruleset covers, per file: accessibility (semantic HTML before ARIA,
labeled controls, keyboard handlers), focus states, forms, animation
(`prefers-reduced-motion`, compositor-friendly properties), typography, content
handling and empty states, image dimensions (CLS), performance (list
virtualization, no layout reads in render), navigation & URL state, touch,
safe-area/layout, dark-mode/theming, i18n formatting, hydration safety, hover
states, copy, and an explicit anti-pattern list to flag.

## House overrides

The vendored ruleset's **Content & Copy** section (Title Case for headings and
buttons, `&` over "and", …) is **superseded by
[`design/ux-writing`](../ux-writing/SKILL.md)** — sentence case, active verb
labels, one voice across both stacks. The audit emits **no findings** from that
section; a label that follows `ux-writing` is correct. Every other section of
the vendored ruleset applies unchanged.

## Do NOT use for

- **Experience-level review** — flows, friction, Nielsen heuristics, IA →
  [`design/ux-review`](../ux-review/SKILL.md). This skill audits the
  code; ux-review audits the experience.
- **Automated a11y scanning** (axe / Lighthouse, per-state WCAG scans, CI
  budgets) → qa `accessibility-testing`. This skill reads source statically; it
  does not run a scanner against a live page.
- **Visual taste / identity** — palette, type, composition → [`design/visual-identity`](../visual-identity/SKILL.md).
- **Copy wording** — the words inside the UI → [`design/ux-writing`](../ux-writing/SKILL.md).
