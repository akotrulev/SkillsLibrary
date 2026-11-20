# Self-check before handing off

Read from `SKILL.md` before the plan is handed off. Mark each item holds or fixed.

1. Every row of §1's gap table traces to a task, and every task traces back to a row. Every functional area in `blueprint.md`, migration, resource, screen, external client and blocking unknown is a task.
2. Reading the tasks in `order`, each could be started at its position. Every `Depends on` id exists and points backwards.
3. The sequencing shape is stated in the header with the execution model that selected it. Under agent-batched, every batch is one agent against one file tree, every contract-wave stub names the batch that fills it, and the plan says which capability becomes usable at which batch.
4. Every task states one `Deliverable`, as a result. Every user-facing capability has a last task whose deliverable says what a user can then do, and the run ending there covers the whole Step 1 capability set, screens and reachability included. Every frontend task cites its screen ids and the responsiveness budget; every web `fe` task quotes its routes' §4a rendering spec.
5. Every task binds to an **exact** catalog agent name and exact skill names, and carries `Epic`, `Story` and one `Stack` of the `plan-format.md` §4 list. Every `Epic` resolves in `epic-map.md` and every non-`E0` `Story` in `stories.md`.
6. Every `Budget` itemizes its drivers, the task table's cell agrees, and every estimate over ~150k names its split point inside its own stack or says why the task is one thing.
7. Every task names a declared stream and a unique `order`. Every stream traces to an `epic-map.md` §2 lane (or a recorded stack split of one) and says why it is internally sequential. Every pair of tasks whose `Files` overlap is ordered against each other. Every prompt block opens with a `Depends on:` line of ids only.
8. Every task's bullets are checkable and cite the design pack by section.
9. Every code task says `Gate: own tests` with **filtered** commands, `Gate: none` appears only on a task with nothing runnable, and the last runnable task runs the whole set (`plan-format.md` §5). The header note states what a halfway stop leaves.
10. `## Prompts — one per task` has one block per task that has not landed, each naming one task, an exact agent, exact skills and pack **sections**. Every `Blocked on <id>` placeholder is matched by a bullet and a line on that task. `## Close-out — every task` sits directly above it, verbatim from `plan-format.md` §7.
11. Every `As built` note carries `file:line` or command output read this session. §1, §2, §6 and the task table exist, §6 empty before execution starts. The header `Status:` line says what is built, what is next and what is built but unverified.
12. **Test-first plans:** every endpoint and journey is covered by a `Q` task that precedes the tasks turning its tests green, and every behaviour the plan must keep with no test has a pin task first.
13. **Plans that serve stories:** every epic has a test plan and every story a test-case suite, from `TD` tasks that follow the stub task and precede every `Q` task. Each `Q` task depends on its epic's test-plan task, and the last runnable task checks each plan's Definition of Done. A plan without `TD` tasks records the opt-out in its header.
14. **The plan's last task is `DOC1`** (`plan-format.md` §5), its prompt naming the environment or saying none, or the header says `Documentation task: none — <why>`. The gate task's `Files` name no product documentation.
15. The block that will delete the last prompt carries the filing duty (`plan-format.md` §8), and `NNN` was taken from the high-water mark across `docs/plans/` **and** `docs/plans/implemented/`.
