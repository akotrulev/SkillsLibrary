# UI/UX and visual design practice — 2026 research, and where this library stands

**Date:** 2026-08-27 · **Scope:** current external practice across usability, accessibility, visual design, AI-era interfaces and regulation, mapped against the ten `design/*` skills and the stack skills they hand off to.

## Overview

This is two documents in one. **Part 1** is the research: the practices the field currently holds, each as a *do* and a *don't* you can hand to a reviewer. **Part 2** is what it means here — where the library already owns a practice (most of them), where it silently doesn't, and what to build. The second half is the point; the first half is the evidence for it.

The headline: the library's coverage of **classical** UX is strong and in places better than the public sources — the task-inventory→IA derivation, the responsiveness budget and the slot/voice split in `ux-writing` are all sharper than the generic advice. The gaps are all in the same shape: **practices that moved from "good craft" to "legal obligation" or "new medium" in the last 24 months**, and one **dangling handoff** where a rule is routed to a skill that doesn't own it.

---

# Part 1 — The practices

## A. Accessibility stopped being craft and became law

The European Accessibility Act became enforceable **28 June 2025**, with penalties up to €3M and market bans; it works through EN 301 549, which currently carries WCAG 2.1 AA, with **V4.1.1 (expected 2026) moving to WCAG 2.2 AA**. The practical instruction from every compliance source is to target 2.2 AA *now*. Accessibility overlay widgets were explicitly stated by the European Commission not to constitute compliance.

WCAG 2.2 added **nine** success criteria, and the striking thing for a design library is how many are **design-time decisions, not code or scan findings**:

| Criterion | The design decision it forces |
|---|---|
| 2.4.11/2.4.12 **Focus Not Obscured** | A sticky header/footer or cookie bar must not cover the focused element — a layout decision |
| 2.4.13 **Focus Appearance** (AAA) | The focus indicator's size and contrast are token decisions, not a default outline |
| 2.5.7 **Dragging Movements** | Every drag (reorder, slider, kanban, resize) needs a non-drag alternative — a pattern decision |
| 2.5.8 **Target Size (Minimum)** — 24×24 CSS px | Density, icon-button size and table row-action size are directly constrained |
| 3.2.6 **Consistent Help** | Help/contact must sit in the same relative place on every page — an IA/shell decision |
| 3.3.7 **Redundant Entry** | Don't ask twice for what the user already entered in the process — a flow decision |
| 3.3.8 **Accessible Authentication** | No cognitive-function test (puzzle, memory, transcription) as the only auth path; allow paste and password managers |

**Do:** treat 2.5.8, 3.3.7, 3.3.8, 3.2.6 and 2.4.11 as *design* acceptance criteria written into the screen spec. Give every drag interaction a click/keyboard equivalent at design time. Size icon buttons and row actions to ≥24×24 CSS px (44×44 for touch-primary).
**Don't:** defer any of this to an axe scan — automated tooling catches a minority of WCAG failures, and almost none of these seven. Don't buy an overlay.

## B. Deceptive design is now a regulated category

DSA **Article 25** prohibits dark patterns outright across EU platforms (deception · manipulation · distortion of autonomy). The FTC treats them as unfair/deceptive under §5 — the **$2.5B Amazon Prime settlement (Sept 2025)** turned on enrolment being pushed repeatedly during checkout while the opt-out was obscured, and a cancellation flow of four pages, six clicks and fifteen options.

**Do:** make cancel/decline **symmetric** with accept — same prominence, same number of steps, same visual weight. Make consent granular, unbundled and revocable in one place. Pre-select nothing that costs the user money or privacy. State recurring charges and renewal dates at the point of commitment.
**Don't:** ship confirmshaming ("No thanks, I like paying full price"), a roach-motel cancellation, countdown timers that reset, fake scarcity, pre-ticked marketing consent, "reject all" buried a level deeper than "accept all", or an interstitial that must be dismissed to see the price.

Note the second-order finding from the research: LLM-generated e-commerce components were measured to contain deceptive designs at scale by default — which is directly relevant to a library whose output is generated UI.

## C. AI-native interfaces are a distinct discipline

The strongest new pattern set, and the one with no classical equivalent. NN/g's *State of UX 2026* argues UI is becoming commoditized and that "more interactions are mediated" by assistant/agent layers — the interface's job shifts toward being **the accountability layer between user intent and autonomous action**.

**Do:**
- **Stream tool calls inline as they happen** — showing inputs and outputs during the run, rather than after, is repeatedly cited as the single highest-value improvement in agent UX.
- **Put the user in the driving seat visibly** — a stop/interrupt control on every long action, and a visible edit/reject/flag affordance on every AI output. Users who know they can correct an AI engage with it more.
- **Give approvals the accumulated context**, not a terse approve/deny — context-carrying approval prompts produce faster and more accurate human decisions.
- **Express uncertainty** — a confidence signal, or the top alternatives considered, so the user knows when to verify.
- **Label AI-generated content explicitly** — 78% of consumers call this important to trust; 31% trust a brand *less* when undisclosed AI output is detected.
- **Design the event model before the component library** — progress for long-running work, shared state display, resumability.

**Don't:** show a spinner for a multi-minute agent run; hide tool use behind a summary; ship an approve/deny with no context; imply certainty the model doesn't have; add an AI feature with no user-visible job ("AI fatigue" is the named 2026 risk, on both the practitioner and user side).

## D. Perceived performance is measured differently now

**INP replaced FID in March 2024** and is now the most-failed Core Web Vital — ~43% of sites miss it. Thresholds at the 75th percentile: **LCP < 2.5 s · INP < 200 ms · CLS < 0.1**. INP measures *every* interaction and reports the worst, so a single slow handler on a rarely-used control still fails the origin.

**Do:** treat the classical perception thresholds (100 ms acknowledge · ~1 s flow · ~4 s "say you're alive") as the *design* budget, and INP/LCP/CLS as the *measurement* of it — they are the same requirement in two vocabularies. Reserve space for everything that arrives late.
**Don't:** report a median. Don't equate "fast on my machine" with the 75th percentile of real sessions.

## E. Data-dense enterprise UI

The most under-specified area in generic UX writing, and the most common shape of an internal tool.

**Do:** sticky header row on scroll; sort indicator that doesn't disturb header alignment; **quick filters instant, advanced filters behind Apply**; active filters as removable chips with a count and clear-all; selection shown by row highlight, not the checkbox alone; a contextual bulk toolbar on selection; client-side sort under ~1,000 rows, server-side above; inline edit or expandable rows for high-frequency repeated edits; reveal row actions contextually rather than rendering every button in every row.
**Don't:** put an Apply button on a quick filter (users are routinely confused by them); rely on a 16-px checkbox as the only selection signal; load the whole result set client-side "for now"; lose selection or scroll position across paging.

## F. Search and findability

**Do:** autocomplete that feels instant; synonym handling (couch/sofa) and spelling correction; facets that hide when irrelevant to the current query/category; active facets always visible and individually removable; a zero-results state that *does something* — spelling suggestion, broadened query, popular/related items, clear-filters (≈56% of users continue when alternatives are offered).
**Don't:** ship a zero-results dead end; make the user re-type to remove one filter; keep facets that return nothing; treat a high refinement rate as user behaviour rather than a defect in matching.

## G. Touch and mobile ergonomics

The 44×44 pt rule dates from the 3.5-inch iPhone held one-handed. Phones are now 6.1–6.9 inches and held lower and often two-handed; the rule survives as a **floor**, not a design method. WCAG 2.2 adds a 24×24 CSS px minimum as a *legal* floor.

**Do:** put the highest-frequency, highest-stakes controls in the reachable zone; compensate for hard-zone controls with larger targets, clearer affordance or an alternative path; keep a spacing gap between adjacent targets, not just size; give every gesture a visible equivalent.
**Don't:** rely on a gesture as the only path to an action; place destructive controls adjacent to frequent ones in the thumb arc; treat 44 pt as sufficient without considering position.

## H. Cognitive accessibility and neurodiversity

WCAG was built primarily around sensory and motor impairment; cognitive access is thinner in the standard and is where 2026 attention has moved. The question is not "can they perceive it" but "can they understand and use it".

**Do:** predictable, consistent structure (autism: ambiguity and sensory excess are the load); chunk long processes into steps with visible progress and saved drafts (ADHD: working-memory lapses, long forms are the failure case); short paragraphs, bullets, collapsible sections; generous whitespace; plain language; let the user control motion, sound and density.
**Don't:** rely on time limits; auto-play motion; use decorative or low-contrast type for body copy; shift layout under the reader; make the user hold information across steps.

## I. Internationalization is a design constraint, not a translation step

**Do:** design for **30–50% text expansion** (German, Russian; Finnish/Hungarian worse); use CSS **logical properties** throughout so RTL is a `dir` flip rather than a mirrored stylesheet; run **pseudo-localization** early to catch truncation, concatenation and hardcoded strings before translation exists; test a matrix of one RTL, one CJK, one high-expansion European locale.
**Don't:** compose sentences by concatenating fragments; bake text into images; size containers to the English string; treat RTL as text alignment (icons, progress direction, and nav order mirror too).

## J. Visual direction — the 2026 defaults to design *against*

The trend set has turned over. Currently ubiquitous: **bento grids**, **glassmorphism / Apple's Liquid Glass** (2025 announcement accelerated it exactly as the backlash began; matured into "Glassmorphism 2.0" — glass only on modals, floating toolbars, notification panels), and **kinetic/elastic typography**. The consensus critique is not that these are bad but that they are applied without reason.

**Do:** spend an effect where it carries meaning — glass on the floating layer that genuinely floats, kinetic type on a hero moment, bento where the tiles really are different weights of content. Ask of every trend: what user problem does this solve?
**Don't:** apply a trend uniformly (glass on every card, motion on every element); mistake fashion for identity; keep a "calibration list" of AI-default looks that is itself out of date.

## K. Forms and checkout — the best-evidenced area in the field

Baymard's 200,000+ hours of testing: the average checkout has **14.88 fields against the 6–8 actually needed**; forced account creation costs about a third of customers; "steps within steps" is the biggest single offender; Apply buttons on fields confuse users routinely.

**Do:** cut to the fields the order genuinely needs; guest checkout; one flat step sequence; mark the optional rather than the required when most are required; prefill and infer.
**Don't:** ask for the same data twice across steps (now also WCAG 3.3.7); hide the total or shipping cost until the last step; validate only on submit.

## L. Trust, consent and privacy

**Do:** ask for a permission at the moment of value, with the reason, after a priming explanation; make consent granular and revocable from one obvious place; disclose data use in the flow, not only in a policy.
**Don't:** request notification/location/camera on first launch with no context; bundle consents; use "we value your privacy" as a wrapper on a bundled accept.

---

# Part 2 — What this means for the library

## What is already owned — and owned well

Most of Part 1 has a home here, and several practices are covered more sharply than the public sources state them:

| Practice | Owned by | Note |
|---|---|---|
| IA derived from a ranked task inventory; depth budget | `design/ux-patterns` §1 | Stronger than the generic sources — nav is *derived*, never brainstormed |
| App shell, page anatomy per page type, form layout, density | `ux-patterns` §2–§5 | Covers Part 1 §K's layout half |
| Accelerators, feedback/notification surface, first run | `ux-patterns` §6–§8 | |
| Perception budget (100 ms / 300 ms / ~4 s) | `ux-patterns` §9, `ux-review` | The design half of §D |
| Nielsen's 10, flow friction, undo-over-confirm, IA sanity | `design/ux-review` | |
| Token tiers, purpose naming, dark mode as a swap | `design/design-tokens` | |
| Palette/type/composition, restraint, the AI-default critique | `design/visual-identity` | Mechanism is right; the *list* is stale — see G1 |
| Copy voice, one-name-one-concept, error/empty wording | `design/ux-writing` | Sharper than any source read |
| Markup/attribute/handler violations | `design/ui-code-audit` | |
| Table correctness (sort, paging, truncation, bulk, surface choice) | stack `ui-rules` §1–§8 | Covers much of §E |
| Localization mechanics (next-intl/i18next, `Intl`, `dir`) | stack `languages` | Covers §I's implementation half |
| Core Web Vitals incl. INP | stack `performance`, `frontend/_shared/product-analytics` | Covers §D's measurement half |
| Focus management, live regions, contrast, semantic-first | stack `accessibility` | Covers WCAG 2.1-era ground |

## The gaps, ranked

**G1 — `visual-identity`'s calibration list is out of date.** *(major)*
The skill's central mechanism is "AI-generated design clusters around three looks — don't spend a free axis on them", naming cream/terracotta+serif, near-black+acid accent, and broadsheet hairline. That list is 2024-era. The 2026 defaults are **bento grids, Liquid Glass / Glassmorphism 2.0, and kinetic/elastic type**. A calibration list that lags the actual defaults inverts the skill's purpose — it waves through exactly what it exists to catch.
*Evidence:* `design/visual-identity/SKILL.md` "Calibration" paragraph.

**G2 — WCAG 2.2's design-time criteria are owned by nobody.** *(major, and it is a legal exposure)*
Both stack `accessibility` skills state "Targets **WCAG 2.2 AA** as the baseline" but contain **no mention** of target size, dragging alternatives, accessible authentication, redundant entry, consistent help, or focus-not-obscured — searched for criterion numbers and names across both files, zero hits. What they cover is 2.1-era: semantics, focus management, live regions, contrast. Worse, these seven are mostly *design* decisions, so even a complete stack skill would be receiving them too late.
*Evidence:* `frontend/react/skills/accessibility/SKILL.md:8` and `frontend/blazor/skills/accessibility/SKILL.md:8` claim 2.2 AA; heading list shows no 2.2 section.

**G3 — a dangling handoff: touch targets.** *(major — a logical conflict, not a gap)*
`responsive-design` routes touch targets to the `accessibility` skill in two places. The `accessibility` skill never mentions them. So the rule is *stated as owned* and is owned by no one — the worst failure mode for a cross-linked library, because the reader stops looking.
*Evidence:* `frontend/react/skills/responsive-design/SKILL.md:22` and `:174` → `accessibility`, which has zero hits for "touch target" / "target size".

**G4 — no AI-experience skill at all.** *(major)*
Searched the whole repo for agentic/generative-UI vocabulary: **zero hits** outside QA's AI-*testing* skills. The library can build a React app and test an LLM feature, but has nothing that says how an AI feature should *behave* on screen — streaming tool calls, stop/interrupt, approval-with-context, confidence display, correction affordance, AI labelling. Given that a large share of what these agents will be asked to build in 2026 is AI-surfaced, this is the biggest missing *capability*, as opposed to the biggest missing *rule*.

**G5 — no ethical-design lane.** *(major)*
No skill mentions dark patterns, deceptive design or consent symmetry (`ui-rules:108` covers compliance *flags*, a different thing). `ux-review` runs Nielsen's 10, which will not catch an asymmetric cancellation flow — heuristic #3 (user control) is about exits from a *state*, not about a subscription you cannot leave. This is now enforced law with nine-figure penalties, and the research notes LLM-generated commerce UI carries these patterns *by default* — which makes it a house rule for a code-generating library, not a nice-to-have.

**G6 — search-results UX is unowned.** *(minor)*
`ux-patterns` §6 covers the command palette and global search as *accelerators* — how you reach a destination. Nothing owns the results surface: facet behaviour, quick-vs-advanced filters, active-filter chips, and the zero-results state (`ux-writing` covers the *words* of an empty state; the *behaviour* of a zero-result search — suggest, broaden, clear — is a pattern decision).

**G7 — cognitive accessibility / neurodiversity is unowned.** *(minor)*
Adjacent material exists (progressive disclosure in `ux-patterns` §8, minimalism as Nielsen #8), but the specific discipline — predictability, chunking with saved drafts, motion/density control, no time limits — is stated nowhere.

**G8 — table depth, second tier.** *(minor)*
`ui-rules` §2 plus `ux-patterns` §3/§5 cover the correctness half well. Unowned: sticky header on scroll (routed to `responsive-design`), filter chips, quick-vs-advanced filter timing, selection persistence across paging, column resize/reorder.

**G9 — i18n as a design-time constraint.** *(minor)*
`languages` owns the mechanics; nothing owns the *design* constraint — 30–50% expansion in the layout, logical properties as the default authoring mode, pseudo-localization as a design-review step. `ux-writing` writes copy with no expansion rule.

**G10 — the perception budget doesn't name the metric the field measures.** *(nit)*
`ux-patterns` §9 is excellent and entirely classical. One cross-link to INP < 200 ms / LCP < 2.5 s / CLS < 0.1 (already in stack `performance`) would let a design-time budget and a CI gate speak the same language.

## Recommendations

Sized against the library's own conventions — a new skill only where a genuine domain exists, otherwise a section in the skill that already owns the neighbourhood.

**Do first — cheap and high-leverage:**

1. **G1** — rewrite `visual-identity`'s calibration paragraph to the 2026 default set (bento, glass 2.0/Liquid Glass, kinetic type), and add a line making the list explicitly perishable with a review date, so it cannot silently rot again. *One paragraph.*
2. **G3** — resolve the dangling handoff: either give the stack `accessibility` skills a target-size rule, or (better, with G2) let the new design skill own the design-time decision and have `responsive-design` point there. *One decision, two cross-links.*
3. **G10** — one cross-link in `ux-patterns` §9. *One line.*

**Then — the two new skills that carry real weight:**

4. **G2 + G7 + G9 + G3 → a new `design/accessible-by-design` skill.** The design-time half of accessibility: the seven WCAG 2.2 criteria that are layout/flow/pattern decisions, target sizing and density, the cognitive/neurodiversity set, and the i18n layout constraint. It sits exactly where this library already draws its lines — `ux-patterns` decides, the stack `accessibility` authors, qa `accessibility-testing` verifies — and it closes the "2.2 AA baseline" claim the stack skills currently can't back. Add it to `design-auditor` as a new section.
5. **G5 → a new `design/ethical-patterns` skill.** Deceptive-design taxonomy, consent symmetry, cancellation parity, pricing disclosure, permission priming, with the DSA/FTC framing as the *why*. Short, checkable, and it becomes a `design-auditor` section that no Nielsen pass would produce.

**Then — the capability bet:**

6. **G4 → a new `design/ai-experience` skill.** The on-screen behaviour of AI features: streaming and inline tool-call visibility, stop/interrupt, approval-with-context, confidence and uncertainty display, the correction affordance, AI labelling, and the empty/failure/refusal states an AI surface needs that a CRUD screen doesn't. This is the one that expands what the library can *do* rather than tightening what it already does.

**Finally — the small ones:**

7. **G6** → a `## Search and results` section in `ux-patterns` (it owns the accelerator half already).
8. **G8** → extend `ui-rules` §2 with the second-tier table ergonomics, or fold them into the `ux-patterns` table rhythm section — whichever keeps the correctness/design split clean.

Every new skill above needs the same two follow-ups the library always requires: a `design-auditor` section letter with its own `## Review checklist`, and a row in the skills catalog.

## Open questions

- **Does `design/` become a plugin?** Three new skills plus an agent starts to look like a domain that stands alone rather than a layer bundled into `fe-blazor`/`fe-react`. Bundling still argues for itself (nobody audits a design without a frontend), but it is now a real question rather than an obvious no.
- **Is `ai-experience` a design skill or a frontend one?** The *patterns* are design; the *implementation* (streaming transport, resumable runs, token-by-token render) is `fe-react`'s `realtime`/`data-fetching`. Probable answer: design owns the pattern, the stack owns the transport — the same split as everything else here — but it is worth deciding before writing.
- **How far does the ethical lane reach?** Stopping at "don't ship these patterns" is clean. Extending to "flag when the *product requirement* is a dark pattern" puts the library in the position of refusing a requested build, which is a policy decision, not a design one.
- **Does the AI-default calibration list need an owner and a cadence?** It rots on roughly an 18-month cycle. Either it gets a dated review note, or it moves to something the agent derives at run time rather than recalls.

## Evidence

| # | Claim used | Source |
|---|---|---|
| 1 | EAA enforceable 28 Jun 2025; EN 301 549 V4.1.1 → WCAG 2.2 AA; overlays ≠ compliance | [Level Access](https://www.levelaccess.com/compliance-overview/european-accessibility-act-eaa/) · [EC digital-strategy](https://digital-strategy.ec.europa.eu/en/policies/web-accessibility-directive-standards-and-harmonisation) · [UX Design Institute via TechRev](https://www.techrev.us/blog/top-10-proven-ui-ux-design-best-practices-to-win-users-in-2026/) |
| 2 | WCAG 2.2's nine new criteria and their content | [W3C WAI](https://www.w3.org/WAI/standards-guidelines/wcag/) · [AllAccessible](https://www.allaccessible.org/blog/wcag-22-complete-guide-2025) · [WCAG 2.2 checklist](https://web-accessibility-checker.com/en/blog/wcag-2-2-checklist-2026) |
| 3 | DSA Art. 25 prohibition; FTC §5; $2.5B Amazon settlement, Sept 2025 | [Pandectes](https://pandectes.io/blog/dark-patterns-in-2026-what-the-ftcs-new-rules-mean/) · [Berkeley Tech Law Journal](https://btlj.org/2025/11/trapped-by-design-how-dark-patterns-manipulate-your-choices-and-the-regulators-fighting-back/) · [European Parliament](https://www.europarl.europa.eu/RegData/etudes/ATAG/2025/767191/EPRS_ATA(2025)767191_EN.pdf) |
| 4 | Deceptive designs in LLM-generated commerce components | [arXiv 2502.13499](https://arxiv.org/pdf/2502.13499) |
| 5 | UI as commoditized differentiator; AI-mediated interaction; AI fatigue | [NN/g State of UX 2026](https://www.nngroup.com/articles/state-of-ux-2026/) |
| 6 | Agent UX patterns — inline tool-call visibility highest-value; approval-with-context; accountability layer | [Zylos](https://zylos.ai/research/2026-05-28-agentic-ux-frontend-design-patterns-ai-agents/) · [Mantlr](https://mantlr.com/blog/designing-for-ai-agents-ux-patterns-2026) · [Fuselab](https://fuselabcreative.com/ui-design-for-ai-agents/) |
| 7 | AI trust — 78% want labelling, 31% trust less when undisclosed; confidence signals; correction affordance | [Parallel](https://www.parallelhq.com/blog/designing-ai-transparency-trust) · [reloadux](https://reloadux.com/blog/ai-uncertainty-trust-design-framework/) |
| 8 | INP replaced FID Mar 2024; LCP 2.5 s / INP 200 ms / CLS 0.1 at p75; ~43% fail INP | [corewebvitals.io](https://www.corewebvitals.io/core-web-vitals) · [Incremys](https://www.incremys.com/en/resources/blog/core-web-vitals) · [SitePoint](https://www.sitepoint.com/core-web-vitals-2026-fix-interaction-to-next-paint/) |
| 9 | Enterprise table patterns — quick vs advanced filters, chips, selection highlight, client/server sort threshold | [Pencil & Paper](https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-data-tables) · [Stéphanie Walter](https://stephaniewalter.design/blog/essential-resources-design-complex-data-tables/) · [uxpatterns.dev](https://uxpatterns.dev/patterns/data-display/table) |
| 10 | Checkout — 14.88 vs 6–8 fields, guest checkout, steps-within-steps, Apply buttons | [Baymard](https://baymard.com/learn/checkout-flow-ux-optimization) · [Baymard mobile](https://baymard.com/blog/mobile-checkout) |
| 11 | Search — zero-results alternatives ≈56% continue; facet behaviour; autocomplete | [UXPin](https://www.uxpin.com/studio/blog/advanced-search-ux/) · [UXmatters](https://www.uxmatters.com/mt/archives/2009/09/best-practices-for-designing-faceted-search-filters.php) · [Nulab](https://nulab.com/learn/design-and-ux/search-ux-best-practices/) |
| 12 | Touch — 44 pt origin and its limits, thumb zones, 25% error rate below minimum | [NN/g](https://www.nngroup.com/articles/touch-target-size/) · [72Technologies](https://www.72technologies.com/blog/tap-targets-thumb-zones-mobile-ux) |
| 13 | Neurodiversity — WCAG's cognitive thinness, ADHD/autism/dyslexia design implications | [Stéphanie Walter](https://stephaniewalter.design/blog/neurodiversity-and-ux-essential-resources-for-cognitive-accessibility/) · [Accessibility Checker](https://www.accessibilitychecker.org/blog/neurodivergent-ux-design/) |
| 14 | i18n — 30–50% expansion, logical properties, pseudo-localization, test matrix | [SimpleLocalize](https://simplelocalize.io/blog/posts/ui-localization-best-practices/) · [Crowdin](https://crowdin.com/blog/best-practices-for-ui-localization) · [Lingoport](https://lingoport.com/blog/what-are-the-best-approaches-to-localize-ui-strings/) |
| 15 | Visual defaults — bento, Liquid Glass/Glassmorphism 2.0, kinetic type, and the backlash | [Creative Boom](https://www.creativeboom.com/insight/10-trends-creatives-are-so-over-in-2026/) · [Studio Meyer](https://studiomeyer.io/en/blog/webdesign-trends-2026-reality-check) · [Tenet](https://www.wearetenet.com/blog/ui-ux-design-trends) |
| 16 | Library coverage claims in Part 2 | Read this round: `design/*/SKILL.md` (all 10), `frontend/{react,blazor}/skills/{accessibility,responsive-design,ui-rules,languages}/SKILL.md`, `frontend/_shared/product-analytics/SKILL.md` |
