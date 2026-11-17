# Task inventory → information architecture, and the shell rules

The depth behind [`ux-patterns`](../SKILL.md) §1 and §2. The nav-map table and the shell table stay in the skill.

## §1 — from the task inventory to the nav

Navigation is derived, never brainstormed. Start from what people do, not from what the system stores.

**Inventory the tasks.** For each actor, list the tasks as *verb + object + outcome* ("approve a pending invoice so it is paid this cycle"), with **frequency** (many times a day · daily · weekly · rare) and **stakes** (routine · money/compliance · irreversible). A task named after a table ("manage users") is not yet a task — ask what the person is trying to get done.

**Rank.** The three to five highest-frequency tasks define the home screen and the primary navigation. Everything else is reachable, but not prominent. Rare-and-high-stakes tasks (delete the account, change billing) live under settings, not in the primary nav.

**Group by the user's mental model.** Nav groups follow how the actor thinks about their work, not the org chart, the database schema, or the module layout. A test: a new hire in that role should choose the right group on the first try. The stack's `ui-rules` carries the grouping-size and label rules (group and label over count; front-load the distinguishing word; one name → one concept) — apply them here at design time.

**Depth budget.** Every primary task starts within **one click** of the shell (a top-level destination or the home screen's primary action); every other task within two. A task at depth three is a finding against the IA, not a job for breadcrumbs.

## §2 — rules that hold for any shell

- **Collapsible, never hidden, on desktop.** A collapsed sidebar keeps icons with tooltips; the hamburger/drawer is the small-screen form only (reflow mechanics: the stack's `responsive-design`). On mobile, a **bottom tab bar** is the right shell for ≤ 5 consumer-facing destinations; a drawer for everything else.
- **You-are-here on every page** — active state on the nav item (not by color alone) *and* the page title; breadcrumbs from depth two (`ui-rules` owns the one-breadcrumb-source rule).
- **The shell never swallows the page's primary action.** Global actions (search, new notification, account) belong to the shell; the page's action ("New invoice") belongs to the page header (§3).
- **Home is a screen, not a redirect.** It shows the top-ranked tasks' entry points and what needs attention now; for a tool with one dominant task, home *is* that task's list.
