---
name: design-accessible-by-design
description: Use when the accessibility decision is a DESIGN decision — the WCAG 2.2 criteria code cannot fix (target size, non-drag alternative, accessible auth, redundant entry, consistent help, focus not obscured), cognitive design, and layout for translation (expansion, RTL, CJK). Triggers "is this design accessible", "WCAG 2.2 compliance", "European Accessibility Act", "will this survive translation". Not for accessible markup (a stack's `accessibility`) or scanning a build (qa `accessibility-testing`).
---

# Accessible by design — the decisions a scan cannot make

Owns the accessibility work that happens **before there is code to audit**: the criteria that are layout, flow, and pattern choices rather than markup; the cognitive load a screen imposes; and the shape a layout must have to survive translation. The failure this prevents is the most expensive one in the discipline — an app that passes every automated scan, ships with correct ARIA, and still cannot be used, because the drag-only kanban, the 16-px row action, the puzzle at sign-in, and the German label that truncates were all decided months before the first `aria-` attribute was written.

**The three-way fence — this is the first of three, and the order matters:**

| | Owns | Who |
|---|---|---|
| **Design** | The decisions below — what size, what alternative, what flow, what load | **this skill** |
| **Author** | Semantic markup, focus management, live regions, ARIA in custom widgets, contrast verification | a stack's `accessibility` ([Blazor](../../frontend/blazor/skills/accessibility/SKILL.md) · [React](../../frontend/react/skills/accessibility/SKILL.md)) |
| **Verify** | axe / Lighthouse runs, per-state WCAG scans, CI gates, screen-reader regression | qa `accessibility-testing` |

Automated tooling catches a minority of WCAG failures and almost none of the seven criteria below — they are not scannable, because a machine cannot tell whether an alternative path *exists*, only whether an attribute does. Decide here; author there; prove it in QA.

**Corpus authority.** The facts this skill decides with come from the vendored [`design-ui-ux-pro-max`](../ui-ux-pro-max/SKILL.md) corpus — **it is the source of truth, and where it and this skill disagree on a fact, the corpus wins.** Search one **observable outcome** at a time with explicit accessibility terms — `"focus not obscured"`, `"dragging movements"`, `"accessible authentication"`, `"error summary validation"` — then, if needed, the component domain, then the stack:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/scripts/search.py" "<observable outcome>" --domain ux
```

Never accept a generic accessibility result for a specific interaction or WCAG criterion. The pre-delivery accessibility checklist in `design/ui-ux-pro-max/references/pro-rules.md` is canonical for app UI.

## Why this is not optional any more

The **European Accessibility Act** has been enforceable since **28 June 2025**, with penalties up to €3 million and the possibility of market exclusion. It works through **EN 301 549**, which today carries WCAG 2.1 AA; **V4.1.1, expected during 2026, moves it to WCAG 2.2 AA**. The compliance instruction from every source is the same: build to **2.2 AA now**. Accessibility overlay widgets were explicitly stated by the European Commission not to deliver compliance — an overlay is a finding, not a fix.

Target **WCAG 2.2 Level AA** as the floor for every project unless the brief names a higher bar.

## 1. The WCAG 2.2 criteria that are design decisions

The nine criteria WCAG 2.2 added skew heavily toward cognitive access, low vision, and motor limits — which is exactly why so many of them land here rather than in a stack skill.

| Criterion | Level | The design decision | The finding it produces |
|---|---|---|---|
| **2.4.11 Focus Not Obscured (Minimum)** | AA | Sticky headers, sticky footers, cookie bars and floating toolbars must not cover the focused element. Decide the sticky chrome's height against the scroll-into-view offset. | A keyboard user tabs to a field that is behind the sticky header |
| **2.4.12 Focus Not Obscured (Enhanced)** | AAA | As above, with *no* part obscured. | — |
| **2.4.13 Focus Appearance** | AAA | The focus indicator is a **token decision** — a minimum area and a contrast ratio against both the focused control and its background, in light *and* dark. Not the browser default outline you removed. | The focus ring is invisible on the brand-tinted surface |
| **2.5.7 Dragging Movements** | AA | **Every drag has a non-drag equivalent** — reorder needs move-up/move-down or a position field; a kanban needs a "move to column" action; a slider needs a number input; a resize handle needs a preset or a value. Single-pointer, no path. | The board can only be used with a mouse and fine motor control |
| **2.5.8 Target Size (Minimum)** | AA | **24×24 CSS px minimum** for every pointer target, or sufficient spacing between them. This constrains **density, icon-button size, and table row actions directly** — it is the criterion most often broken by a "compact" density decision. | The row's delete icon is 16 px and sits 2 px from edit |
| **3.2.6 Consistent Help** | A | If help exists — contact, chat, a help link — it sits in the **same relative place on every page**. An IA and shell decision, made once. | Help is in the footer on one page and the account menu on another |
| **3.3.7 Redundant Entry** | A | Do not ask again for what the user already gave in the same process — carry it forward, or offer it as a selectable default. | The shipping address must be retyped as the billing address |
| **3.3.8 Accessible Authentication (Minimum)** | AA | **No cognitive-function test as the only path** — no puzzle, no memory game, no transcription, no "type the third character of your password". Paste must work, and password managers must not be blocked. | The sign-in has an image puzzle and blocks paste on the OTP field |
| **3.3.9 Accessible Authentication (Enhanced)** | AAA | As above, with object recognition also excluded. | — |

**Do:** write these as acceptance criteria on the screen spec, next to the functional ones. **Don't:** send any of them to a scan — an axe run will pass all nine while the app fails every one.

## 2. Target size and density — where the two rules collide

Density is a design decision (`ux-patterns` §5) and target size is now a legal floor, so they must be decided together:

- **24×24 CSS px** is the WCAG 2.2 AA minimum for any pointer target. **44×44 px** is the ergonomic target for touch-primary surfaces — the figure originates in Apple's original 3.5-inch iPhone HIG and survives as a floor, not a method.
- **Spacing counts.** The criterion is satisfiable by *spacing* as well as size: a 20-px icon with a 24-px exclusion zone passes. Adjacent small targets are the real failure — density buys its compactness out of the gaps.
- **A "compact" density does not license 16-px row actions.** Compact reduces padding and row height; it does not shrink the hit area below the floor. Where a compact table cannot fit compliant row actions, move them into an overflow menu with one compliant trigger.
- **Position is part of the target.** On touch, the highest-frequency and highest-stakes controls belong in the comfortably reachable zone; a control in the hard-to-reach corner needs a larger target, a clearer affordance, or a second path to the same action. Phones are 6.1–6.9 inches now and are held lower and often two-handed — do not design to a 2007 grip.
- **Destructive controls are never adjacent to frequent ones** in the thumb arc or in a row's action cluster.

## 3. Cognitive accessibility and neurodiversity

WCAG was built primarily around sensory and motor impairment; cognitive access is the thinnest part of the standard and the part that has moved most since. The question stops being *can this be perceived* and becomes **can this be understood and used**.

- **Predictability over novelty.** The same action lives in the same place, behaves the same way, and is called the same thing everywhere. Ambiguity, sudden layout change, and sensory excess are the load — this is the accessibility face of `ux-patterns`' one-shell rule and `ux-writing`'s one-name-one-concept.
- **Chunk long processes, and save the draft.** A long form is the canonical failure case for working-memory limits: break it into steps with visible progress, save between steps, and never lose input on back (`ux-patterns` §3's wizard rules, applied for a different reason). This is also 3.3.7's positive form — carry information forward so nothing must be held in the head.
- **Let the user turn things down.** Motion, autoplay, sound, and density are user-controllable where the app has them; `prefers-reduced-motion` is the floor, not the whole answer.
- **No time limits on comprehension or entry** — no countdown on a form, no toast carrying the only copy of an error, no session timeout without warning and extension.
- **Plain language, short blocks, real structure.** Short paragraphs, lists, headings that describe, and collapsible sections for depth. Generous whitespace is a cognitive feature, not decoration.
- **One job per element** (shared with `ux-writing`): a label labels, a hint demonstrates. An element quietly doing two jobs costs the most from the readers who can spare it least.

## 4. Designing for translation

Localization mechanics belong to a stack's `languages` skill; the **layout constraint** is a design decision, and retrofitting it is the expensive path.

- **Design for 30–50% text expansion.** German and Russian run 30–50% longer than English; Finnish and Hungarian can exceed it. A button sized to its English label is a button that breaks. Nav labels, tabs, table headers and chips are where it bites first.
- **CSS logical properties are the authoring default** — `inline-start`/`block-end` rather than left/right/top/bottom — so RTL is a `dir` flip rather than a mirrored stylesheet. Decide this at design time; the stack implements it.
- **RTL mirrors more than text.** Layout, nav order, icon direction (arrows, progress, chevrons), and the reading order of paired elements all mirror. Logos, clocks, and media controls generally do not.
- **Never build a sentence from fragments.** Concatenated strings and inline-substituted clauses cannot be translated correctly; a whole sentence with named placeholders can. Plurals go through the locale's rules, not `if (n === 1)`.
- **No text baked into images** — it cannot be translated, resized, or read aloud.
- **Pseudo-localization is a design-review step**, not a QA one: run it as soon as there are screens, and it catches truncation, clipping, concatenation, and hardcoded strings before a single real translation exists. Test at least one RTL, one CJK, and one high-expansion European locale.

## Review checklist

- **All nine WCAG 2.2 criteria** in §1 are decided and written as acceptance criteria; none is deferred to a scan.
- **Every drag interaction has a documented non-drag path** (2.5.7).
- **Every pointer target is ≥ 24×24 CSS px or adequately spaced**; touch-primary targets ≥ 44×44; the density decision was checked against this floor, not made independently of it (2.5.8).
- **Authentication has a path with no cognitive-function test**, and paste / password managers work (3.3.8).
- **Nothing is asked twice** within one process (3.3.7); **help sits in one consistent place** (3.2.6).
- **Sticky chrome does not obscure the focused element** at any scroll position (2.4.11).
- **The focus indicator is a defined token** with stated size and contrast, verified in light *and* dark.
- **Cognitive load addressed:** predictable structure, chunked long processes with saved drafts, no time limits, user-controllable motion and density, plain language.
- **Translation survivable:** layouts hold at +50% text, logical properties are the default, no concatenated sentences, no text in images, pseudo-localization run.
- **Overlay widgets are absent** — or present and filed as a finding.

## What NOT to do

- Do not claim "WCAG 2.2 AA" while covering only 2.1 ground — the 2.2 delta is nine criteria and most of them are here.
- Do not treat an axe/Lighthouse pass as evidence for anything in §1.
- Do not ship drag as the only path, a cognitive-function test as the only auth, or a 16-px row action.
- Do not size a container to its English string, or compose a sentence by concatenation.
- Do not install an accessibility overlay and call the obligation met.
- Do not write the ARIA here — that is the stack's `accessibility`; this decides what the ARIA will have to describe.

## Related

- A stack's `accessibility` ([Blazor](../../frontend/blazor/skills/accessibility/SKILL.md) · [React](../../frontend/react/skills/accessibility/SKILL.md)) — **authoring**: semantics, focus management, live regions, ARIA, contrast verification. Receives these decisions; owns the code.
- A stack's `responsive-design` — breakpoint reflow and zoom/reflow (WCAG 1.4.10); **target sizing is decided here** and implemented there.
- A stack's `languages` — the localization mechanics (message catalogs, `Intl`, `dir`, locale routing) this skill's layout constraints feed.
- qa `accessibility-testing` — the automated scans and CI gate. Peer, invoked separately.
- [`design/ux-patterns`](../ux-patterns/SKILL.md) — density (§5), wizards and forms (§3/§4), first run (§8): the decisions this skill constrains.
- [`design/ux-writing`](../ux-writing/SKILL.md) — plain language, one-name-one-concept, and the no-visual-references rule, which is this discipline expressed in copy.
- [`design/design-tokens`](../design-tokens/SKILL.md) — where the focus-indicator and target-size decisions become tokens.
- [`design-ui-ux-pro-max`](../ui-ux-pro-max/SKILL.md) — outcome-searchable accessibility guidelines and the canonical pre-delivery checklist.
