# Navigation, footers and the choice of surface

The reference for `ui-rules` §6 (navigation, footers) and §7 (the surface). Read it when the task adds or changes a nav menu, breadcrumb trail or footer, or opens a modal, drawer, separate page or new tab.

## Navigation

- **Always indicate the current location.** The single most common nav defect is failing to show where the user is now — highlight the active nav item with a **distinct state that isn't color alone** (weight, an indicator bar, `aria-current="page"`), and add breadcrumbs on deep hierarchies. (`NavLink`'s `Active` class is the hook; the not-color-alone + `aria-current` a11y side is [`accessibility`](../../accessibility/SKILL.md)'s.)
- **Group and label over count — the "7 items max" rule is a myth.** Menus rely on *recognition*, not recall; a well-grouped menu of 12–15 clear items beats a "clean" menu of 5 vague ones. The nav-group size budget (~7–10 *per group*) is about splitting groups that mix distinct concerns, not capping total items. What matters is grouping and label quality.
- **Front-load labels with the distinguishing word and name content, not org structure** — "Pricing", not "Our pricing options"; "Reports", not the internal team that owns them. (The wording discipline is [`design/ux-writing`](../../../../../design/ux-writing/SKILL.md); the IA requirement that labels map to content lives here.)
- **Don't hide navigation when there's room to show it** — the desktop layout shows top-level items; the hamburger/drawer is a small-screen affordance, not a default (the breakpoint mechanics are [`responsive-design`](../../responsive-design/SKILL.md)'s nav-collapse pattern).

## Footers

The footer is the user's **last-resort lookup** — where they go for the things the header didn't surface. It's low-cost and high-value; give it real content in priority order:

- **Utility links** (Contact, Privacy, Terms, support) on every site; **doormat navigation** (repeat the top nav) so a long page doesn't force a scroll back up; **secondary-audience tasks** (Careers, Investors, Press) on multi-audience sites; **link columns** (the "fat footer") only for large, deep sites; engagement (newsletter, social) and trust signals (certifications) where they earn their place.
- **Fat footer for large multi-audience sites; slim utility footer for focused web apps** (version, status, help, legal) — don't bolt a marketing fat-footer onto an internal tool.
- **Use the semantic `<footer>` element** (it creates the `contentinfo` landmark — [`accessibility`](../../accessibility/SKILL.md)), group links into **explicitly labeled** columns ("Contact us", "Documentation" — never a vague "Resources"), keep it visible and legible (don't hide it behind a desktop accordion), and on mobile trim to essentials, stacking into accordions only if it would otherwise run several screens tall.

## Choosing the surface — modal, page, or new tab

Where a task happens is a correctness decision, not a styling one: the wrong surface hides the context the user needs or breaks the back button. Decide before you build.

### Modal (overlay/drawer) or a separate page?

Ask in order:
1. **Does the task need the underlying screen's context?** Yes → an overlay/drawer over that screen, not a full page navigation.
2. **Is it short and self-contained?** Yes → modal candidate. Multi-step or long forms → a **separate page**.
3. **Will the user reference or copy data from the background while working?** Yes → a **non-modal** side panel/drawer, never a blocking modal (which hides exactly what they need).
4. **Is it a repeated, high-frequency task?** Then both a modal *and* a page navigation add friction — prefer **inline editing** or expandable rows.

- **Use a blocking modal only when the interruption itself is the value:** destructive/irreversible confirmations (§4 owns their content), a critical alert the user must acknowledge, or deliberately slowing input verification.
- **Use a separate page when** the flow is multi-step, needs full attention, or benefits from a **URL** (bookmarkable, shareable, back-button- and deep-link-friendly) — a real route with a `<PageTitle>` (§6), not a modal pretending to be a page.
- **Modal hygiene** (mechanics owned by [`accessibility`](../../accessibility/SKILL.md) — cross-linked, not restated): an obvious exit (×, `Esc`, click-outside), focus trapped while open and restored on close, never stack modals, and **never open a modal the user didn't trigger** (unrequested pop-ups are the single most-disliked pattern).

### Same tab or new tab?

- **Default: open links in the same tab.** New tabs break the back button, disorient users who don't notice the switch, and are worst on mobile. "We'll lose the visitor" is a business rationalization, not a user need — anyone who wants a new tab can ⌘/middle-click.
- **Legitimate `target="_blank"` exceptions:** reference material needed *while completing the current task* (help docs, a spec beside a form), a link whose navigation would destroy unsaved work or interrupt a process (media playing, checkout), and non-HTML documents (PDFs) that would hijack the tab.
- **If you do open a new tab, signal it** — a visible "opens in new tab" affordance plus a screen-reader hint, and `rel="noopener"`. The anchor mechanics (real `<a>`, the affordance + `aria-label` suffix, `rel`) are [`component-writer`](../../component-writer/SKILL.md)'s; the *decision* to open a new tab at all is this skill's.
