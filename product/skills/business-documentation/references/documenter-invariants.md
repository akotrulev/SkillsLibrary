# Documenter invariants — `documenter` and `feature-documenter`

Read by both documenter agents before their first step. It holds every rule the two share; each agent file adds only its own paths, steps and report. Where an agent file and this file disagree, this file wins and the agent file is the defect.

**Done when** the run meets every rule below and its report says where a rule bent (a blocked capture, an escalated answer, a session that ran out).

## What a guide may say

`product:doc-business-model`'s disciplines govern the guide: purposes only from a source (2), every person with administrators included (4), describe and never judge (6). Two more bind the run:

- **Document only what people can reach.** A capability behind a dead route, a disabled flag or an unreachable branch is reported, never written up.
- **The KB outranks you.** A `#confirmed` entry the trace contradicts is escalated with both readings (*KB stale* vs *code defect*), never overwritten.

## What a run may touch

- **Read-only on the codebase.** `Write`/`Edit` reach only the agent's own documentation paths (its file names them), `docs/deliveries/**`, its orientation cache under `docs/agent-context/` and, in a plan, the close-out edits (its task and prompt blocks, `Status:`, the filing move). Never source, config or test.
- **`Bash` is inspection plus filing**: reading, `mkdir`/`mv` of screenshots, `git rm` of a retired `.behind-the-scenes.md` / `.technical*.md`, a plan close-out's `git mv` and commits, and the read-only lint `python3 ${CLAUDE_PLUGIN_ROOT}/product/skills/business-documentation/scripts/doc-lint.py`. Never a build, test run, install or app start; the renderer is only printed.
- **The browser is for looking.** Drive the product only to capture the guide's screens, with the given test logins, on a **non-production** environment. A form with test data may be submitted when a screenshot needs the result; deleting, paying or emailing a real person, never. Logins and addresses are written nowhere, the orientation cache included.
- **Workspace.** The given checkout; no new branch or worktree. Commit only when asked or the plan says to.

## Every run

- **Updated in place, never recreated** ([`reconcile.md`](reconcile.md)). An existing guide keeps its file, `Created` date and facts; a guide in an earlier shape (lint `old-shape`, `renamed-section`, `about-shape`) moves into the current shape and has only the code delta re-traced, closing with `doc-lint.py --kept-from <old sha>`. Retired `.behind-the-scenes.md` and `.technical.md` siblings are read as leads, then deleted.
- **Intent sources.** As `DOC1`: the feature spec the plan builds (the prompt names it; else the plan's header): its goal, its decisions and its `## Acceptance criteria`; or, for a plan built from a story backlog, the stories the plan names. Standalone: search `docs/specs/` for a spec covering the scope, then `docs/plans/**`, `implemented/` included, for a plan or stories that do, naming the searches in the report (none found is normal). They are the approved purposes and the *Not delivered* baseline, never evidence of what was built.
- **Fold the answered open questions** of every guide in scope before anything else is written (reconcile procedure, step 1). An answer the code contradicts stays and is escalated.
- **Screens — ask once, never block.** Unless the request or plan prompt gives them, ask for a running non-production environment and a test login per role (administrators included) in the run's first message to the person; carry on. No environment: write every guide in full, record `**Screenshots:** pending — <why>` and repeat the need in the report. Only the person can waive screenshots (`waived — <their reason>`). A no-screen system or feature needs no environment — say so.
- **Before reporting**, update the orientation cache per `engineering/agent-orientation-cache`: correct what the run disproved, re-stamp, prepend a session-log line.

## Session estimate

A session costs `85,000` fixed (harness, skills, references, rule file, working overhead) **plus, per area or feature in it, traced source lines × 12 + 25,000** (its guide written and re-read, its screenshots captured when an environment is given). Traced lines are the files its entry points and screens reach, counted with `wc -l`. A session stays ≤ 135k of its 150k budget, the margin being for reading output back; a scope over it is split first (the survey splits the area, a feature run proposes a tighter fence). When the orientation cache records a real run's figure, estimate from that instead.

## As `DOC1` — the last task of a delivery plan

The prompt block is the spec, `## Close-out — every task` the close-out, `Gate:` what runs. Nobody is watching: Plan Queue runs the task unattended.

- **Never block.** Every gate that asks a person in a standalone run is answered by the plan: the scope is what the plan's tasks touched, the names come from its spec (or its epics and stories), and an ambiguity is settled by the plan's reading and recorded in the report. A `DOC1` run never waits for a confirmation and never writes a documentation plan.
- **Evidence.** `As built` notes are leads, the code at HEAD is the evidence, the spec (or the stories) the source of purpose. Nothing intended but unbuilt is documented as built: it goes to *Not delivered* and the report.
- **The delivery note last**: `docs/deliveries/<NNN>-<plan-slug>.md` (the plan's number and slug) per [`delivery-note.md`](delivery-note.md), from the code at HEAD and the guides just written; the gate adds `doc-lint.py --dir docs/deliveries`.
- **Screens.** Without an environment the guides land with screenshots pending and `Status:` lists them built but unverified; a later capture run closes it.
- **A scope past the session.** Document the areas or features in the order of the plan's tasks; when the session's budget runs out, keep the `DOC1` block with a `Picking up from:` line naming what is left, per the close-out, and do not file the plan. The delivery note is written by the session that finishes.
