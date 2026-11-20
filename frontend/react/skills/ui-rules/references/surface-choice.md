# Choosing the surface — modal, page, or new tab (ui-rules §7)

*Deep dive for [`fe-react:ui-rules`](../SKILL.md). Read it when the task contains a modal, a drawer, or a link that may open a new tab.*

**Contents:**

- Modal (overlay/drawer) or a separate route?
- Same tab or new tab?

Where a task happens is a correctness decision, not a styling one: the wrong surface hides the context the user needs or breaks the back button. Decide before you build.

## Modal (overlay/drawer) or a separate route?

Ask in order:
1. **Does the task need the underlying screen's context?** Yes → an overlay/drawer over that screen, not a full navigation.
2. **Is it short and self-contained?** Yes → modal candidate. Multi-step or long forms → a **separate route**.
3. **Will the user reference or copy data from the background while working?** Yes → a **non-modal** side panel/drawer, never a blocking modal (which hides exactly what they need).
4. **Is it a repeated, high-frequency task?** Then both a modal *and* a navigation add friction — prefer **inline editing** or expandable rows.

- **Use a blocking modal only when the interruption itself is the value:** destructive/irreversible confirmations (§4 owns their content), a critical alert the user must acknowledge, or deliberately slowing input verification.
- **Use a separate route when** the flow is multi-step, needs full attention, or benefits from a **URL** (bookmarkable, shareable, back-button- and deep-link-friendly) — a real route with a title (§6). In App Router, an **intercepting/parallel route** gives a modal that's *also* a real URL (deep-linkable, refresh-safe) — reach for it when a modal needs to survive a reload or share.
- **Modal hygiene** (mechanics owned by [`accessibility`](../../accessibility/SKILL.md) — cross-linked, not restated): an obvious exit (×, `Esc`, click-outside), focus trapped while open and restored on close, never stack modals, and **never open a modal the user didn't trigger** (unrequested pop-ups are the single most-disliked pattern).

## Same tab or new tab?

- **Default: open links in the same tab.** New tabs break the back button, disorient users who don't notice the switch, and are worst on mobile. Anyone who wants a new tab can ⌘/middle-click a real `<Link>`.
- **Legitimate `target="_blank"` exceptions:** reference material needed *while completing the current task* (help docs, a spec beside a form), a link whose navigation would destroy unsaved work or interrupt a process (media playing, checkout), and non-HTML documents (PDFs) that would hijack the tab.
- **If you do open a new tab, signal it** — a visible "opens in new tab" affordance plus a screen-reader hint, and `rel="noopener"`. The anchor mechanics (real `<a>`/`<Link>`, the affordance + `aria-label` suffix, `rel`) are [`component-writer`](../../component-writer/SKILL.md)'s; the *decision* to open a new tab at all is this skill's.
