# Expert accelerators and first run

The depth behind [`ux-patterns`](../SKILL.md) §6 and §8.

## §6 — expert accelerators

Frequent users outgrow the nav within a week; the app should have somewhere for them to go.

- **Global search / command palette (`⌘K` / `Ctrl+K`)** once the app has more than ~20 destinations or the user's day starts with "find the record" — it searches **destinations and records** in one box, and every result is a link. Below that threshold a search field on the list page is enough. What the results surface itself must do is §10.
- **Keyboard shortcuts for the top three tasks** (create, search, save/approve), discoverable through a `?` overlay and shown in tooltips. Never override browser or OS shortcuts.
- **Saved views** — a named filter + sort + column set on any list a user returns to daily; the default view is the most common task's.
- **Recents and favourites** in the shell when the entity count is large and the user's working set is small.
- **Bulk actions** wherever a task repeats row by row (`ui-rules` owns the selection mechanics and per-item reporting).

## §8 — first run and progressive disclosure

- **The first-run empty state is a guided setup, not a tour.** A checklist of the two to four things that make the app useful ("Add your first project", "Invite a teammate"), each a real action, dismissible once complete. Product tours are skipped; checklists are done.
- **Every empty state is an invitation** — the no-records / no-match / by-design split and the copy are `ux-writing`'s; that the page has a primary action in its empty state is decided here.
- **Progressive disclosure at every level:** the nav shows the primary destinations, settings hold the rare ones; a form shows the common fields, "Advanced" holds the rest; a detail page shows the summary, sections hold the depth. Nothing is *hidden* — it is *staged*.
- **Contextual hints once.** A new capability gets one inline hint at the point of use, dismissed permanently on first interaction; never a modal, never a recurring tip.
