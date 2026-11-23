---
name: prototype
description: Use when a screen or flow should be seen in a few variants before it is built. Triggers "prototype this screen", "show me layout options". Not for a whole visual identity (visual-identity).
---

# Prototype — see a screen before it is built

A prototype is throwaway work that answers one question: *which shape should this screen take?* This skill renders **2–5 structurally different variants** of one screen or flow, in the project's own design language, as **one self-contained HTML file** a person opens and flips through. The chosen variant, and why, is the deliverable; the file is the evidence.

Every variant shares one design language: the project's when it has one, a corpus-led direction chosen in a style interview when it has none. Variants differ in **structure** (layout, information hierarchy, primary affordance), never only in colour or copy.

## Inputs needed

- The screen or flow, and what a person must be able to do on it.
- The project root, read for the design language, the stack and realistic data.
- Optional: the number of variants, the states, the viewports, and the spec path when `/product:plan-feature` (the `product` plugin) sent you here.

## Procedure

1. **State the question.** Name the screen or flow, the job a person does on it, the number of variants (3 by default, 5 at most: past 5 they stop disagreeing and turn into noise), the states, and the viewports. Write it as one plan line: "Three variants of the booking list, states loaded / loading / empty / failed, desktop and phone." Derive a kebab-case `<slug>` from the screen's name. **Done when** the plan line is shown to the user and the slug is fixed. With nobody to answer, take the defaults and say so in the plan line.

2. **Detect the design language.** Read `references/design-language.md` and walk its detection order for the detected stack. For each of the seven parts (palette, type, spacing, radius, elevation, components, iconography) stop at the first source that answers it. Show the **design-language block**: each part, its value and the file it came from. When only some parts are missing, ask for those alone. **Done when** every part is sourced or answered, and the block is shown before anything is built. When no part is found at all, go to step 3; otherwise skip it.

3. **No design language: the style interview.** Run the interview in `references/design-language.md` ("Style interview"): one round on product and audience, mood, density and light/dark, then the corpus query, then 2–3 directions offered as one question, each citing its corpus style, palette and font-pairing rows. The chosen direction is the language of **this prototype only**. **Done when** the user has picked one direction (or, unattended, the recommended one is taken and named as such) and it is shown as a design-language block whose sources are corpus rows.

4. **Build the file.** Read `references/html-shell.md` and write `docs/prototypes/<slug>/index.html` to its contract. Draft the variants first, one line each, on the axes under "Structural variants" below; redraft any two that share a layout and a primary affordance. Then build: every data region in every state the shell requires, realistic data, the switcher bar, the URL round-trip. **Done when** each check in html-shell.md's "Done when" list is ticked for the file.

5. **Show it.** Open the file: `open` on macOS, `xdg-open` on Linux, `Invoke-Item` in PowerShell on Windows. On request, screenshot every variant × state into `docs/prototypes/<slug>/screenshots/` (the command is in `references/html-shell.md`), or publish the page with the Artifact tool when the session has one. Give the user the `?variant=` keys and the keyboard shortcuts. **Done when** the file is open, or its path and URL keys are handed over when nothing can open it.

6. **Record the verdict.** The user picks a variant or combines parts of several ("B's list with A's filter bar" is the usual answer, and a good one). Write it as the `prototype-verdict` line at the top of the file: date, the variant or the combination, and why. When `/product:plan-feature` called this skill, also write it into that spec, beside the decision it settles, with a link to the file. **Done when** the verdict line is in the file and, for a spec-driven run, in the spec. A variant left unpicked is recorded as `undecided`, with the open question.

7. **In-app variants, on request only.** When the user asks for the variants inside the real app (beside its header, sidebar and data), read `references/in-app-handoff.md` and delegate the brief to the stack's agent, or have the user type its command (`/fe-react`, `/fe-blazor`, `/mobile-react-native`, `/mobile-ios`, `/mobile-android`, `/desktop-macos`, `/desktop-windows`). **Done when** the brief is delivered to the agent, or handed to the user to paste, and it names the file, the variants and the verdict so far.

## Structural variants

A variant earns its place by disagreeing with the others about at least one of these:

| Axis | Disagreements that make a real variant |
|---|---|
| Layout | a list, a table, a board, a calendar, a split pane (list and detail side by side), a single focused card |
| Hierarchy | what comes first and largest: the next item, the totals, the search, the most recent change |
| Primary affordance | an inline action per row, a detail drawer, a step-by-step wizard, a command or search field, drag and drop |
| Navigation | tabs, a sidebar, filter chips, a segmented control, progressive disclosure |

Hold constant across variants: the tokens, the type, the icon family, the copy voice and the data. A variant may share a small piece (the page header), never the layout itself. A variant that would look like its neighbour in a greyscale thumbnail is a recolour: redraft it with the shared layout ruled out.

The variants follow the platform's conventions when the target is native: a phone variant uses the platform's navigation and controls, a desktop variant its window chrome and menus. The design facts behind them come from the corpus (`--stack <stack>`), and the house mobile and desktop rules for the app hold for the prototype's states too.

## Rules

- **The design language is read, never changed.** This skill writes `docs/prototypes/<slug>/` and the verdict line in a spec, nothing else: no token file, no theme, no `design-system/` folder, no app code. Turning a chosen direction into the project's tokens is `visual-identity`'s work; offer it (see When NOT to use).
- **The corpus decides design facts.** Directions, palettes, pairings, contrast and per-stack conventions come from `design/ui-ux-pro-max`, cited by row. Run its search without `--persist`; never pass `--force` unless the user asks for it by name.
- **Real data shapes the variants.** Seeds, fixtures, OpenAPI examples, stories and test builders come first; invented data follows the domain's real shapes and lengths. Production records and personal data never go into a prototype.

## Output format

```
docs/prototypes/<slug>/
  index.html            the variants, the switcher, the plan, language and verdict lines
  screenshots/          only on request: <variant>-<state>-<theme>-<viewport>.png
```

The reply to the user: the plan line, the design-language block, the file path, the URL keys (`?variant=B&state=failed&theme=dark&viewport=phone`), and the shortcuts (`1`–`5` pick a variant, `s` cycles the states).

## Example

The user asks for options for a studio's booking list in a Next.js app with shadcn/ui.

```
Plan: Three variants of the booking list, states loaded / loading / empty / failed, desktop and phone.

Design language
| Part        | Value                                         | From                              |
|-------------|-----------------------------------------------|-----------------------------------|
| Palette     | neutral stone surfaces, accent blue-600, status set, light + dark | app/globals.css:4-58 |
| Type        | Inter 400/500/600, scale 12–30                | app/layout.tsx:8, tailwind.config.ts:21 |
| Spacing     | 4 px base                                     | tailwind.config.ts (default)      |
| Radius      | 0.5rem                                        | components.json, app/globals.css:6 |
| Elevation   | hairline borders, shadow-md on popovers only  | components/ui/popover.tsx:19      |
| Components  | shadcn new-york: Table, Sheet, Tabs, Badge    | components/ui/                    |
| Iconography | lucide-react, 16 px, stroke 2                 | package.json, components/nav.tsx  |

Variants
A  Table by day, row actions inline (cancel, reschedule)
B  Week calendar; a booking opens a detail sheet
C  "Next up" card first, then a compact list behind status tabs
```

Opened at `docs/prototypes/booking-list/index.html`. The verdict, a day later: "C's next-up card above B's calendar: members check what is next far more than they browse the week."

## When to use

- A screen or flow is about to be built and its shape is not yet settled: "show me options", "prototype this screen", "what could this look like".
- `/product:plan-feature` reached a decision that needs to be seen before it is written into the spec.
- An existing screen is being redesigned, and the candidates should be compared side by side.

## When NOT to use

- The app needs its whole look (palette, type, tokens) chosen or changed: delegate to the stack agent (`fe-react`, `fe-blazor`, `mobile-*`, `desktop-*`), which loads `visual-identity`, or type `/design:visual-identity`.
- A brand book, logo or brand colours should become the project's tokens: type `/design:brand-import`.
- A built UI, screenshot or mockup needs a UX review: delegate to the `design-auditor` agent, or type `/design:ux-review`.
- The chosen variant should now be built for real: delegate to the stack agent, with the prototype and its verdict as the brief.
- The question is about logic or a state model, not about how a screen looks: `/product:plan-feature` interviews it (needs the `product` plugin enabled).
