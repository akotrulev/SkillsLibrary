# Navigation and footers (ui-rules §6)

*Deep dive for [`fe-react:ui-rules`](../SKILL.md). Read it when the task contains a nav menu, breadcrumbs or a footer.*

**Contents:**

- Navigation
- Footers

## Navigation

- **Always indicate the current location.** The single most common nav defect is failing to show where the user is now — highlight the active nav item with a **distinct state that isn't color alone** (weight, an indicator bar, `aria-current="page"`), and add breadcrumbs on deep hierarchies. (`NavLink`'s active state / `usePathname` is the hook; the not-color-alone + `aria-current` a11y side is [`accessibility`](../../accessibility/SKILL.md)'s.)
- **Group and label over count — the "7 items max" rule is a myth.** Menus rely on *recognition*, not recall; a well-grouped menu of 12–15 clear items beats a "clean" menu of 5 vague ones. The nav-group size budget (~7–10 *per group*) is about splitting groups that mix distinct concerns, not capping total items.
- **Front-load labels with the distinguishing word and name content, not org structure** — "Pricing", not "Our pricing options"; "Reports", not the internal team that owns them. (The wording discipline is [`design/ux-writing`](../../../../../design/ux-writing/SKILL.md); the IA requirement that labels map to content lives here.)
- **Don't hide navigation when there's room to show it** — the desktop layout shows top-level items; the hamburger/drawer is a small-screen affordance, not a default (the breakpoint mechanics are [`responsive-design`](../../responsive-design/SKILL.md)'s nav-collapse pattern).

## Footers

The footer is the user's **last-resort lookup** — where they go for the things the header didn't surface. It's low-cost and high-value; give it real content in priority order:

- **Utility links** (Contact, Privacy, Terms, support) on every site; **doormat navigation** (repeat the top nav) so a long page doesn't force a scroll back up; **secondary-audience tasks** (Careers, Investors, Press) on multi-audience sites; **link columns** (the "fat footer") only for large, deep sites; engagement (newsletter, social) and trust signals (certifications) where they earn their place.
- **Fat footer for large multi-audience sites; slim utility footer for focused web apps** (version, status, help, legal) — don't bolt a marketing fat-footer onto an internal tool.
- **Use the semantic `<footer>` element** (it creates the `contentinfo` landmark — [`accessibility`](../../accessibility/SKILL.md)), group links into **explicitly labeled** columns ("Contact us", "Documentation" — never a vague "Resources"), keep it visible and legible, and on mobile trim to essentials, stacking into accordions only if it would otherwise run several screens tall.
