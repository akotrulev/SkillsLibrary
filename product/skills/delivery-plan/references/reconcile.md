# The reconcile procedure (RESUME mode)

Read when a plan and partly built code both exist. Run it **before** re-sequencing anything.

**The governing rule: the plan is a lead, not evidence.** An `As built` note, a green pipeline, a commit message, a deleted prompt block and the header `Status:` line are all claims. A verdict is assigned only after reading the code **this session**.

**A red build is a finding about the task that left it.** Every task gates what it wrote, so run its gate yourself and attribute each failure to the task that owns the file before assigning verdicts.

1. **Read the design pack**, so you know what was supposed to exist.
2. **Walk each task** in the task table and look for its artifacts: the files it names, the migration, the endpoint, the registration. Done when every task has been looked for.
3. **Assign a verdict** with `file:line` evidence:

| Verdict | Means |
|---|---|
| **Done** | The deliverable exists and every bullet on the task is satisfied by code you read this session |
| **Partial** | Some bullets satisfied; name exactly which are missing |
| **Not started** | No artifacts found. Say what you searched for, because a negative claim needs its search named |
| **Diverged** | Built, but differently from the plan. **Both readings recorded; the human decides** |
| **Blocked** | Cannot proceed: a prerequisite, a missing credential, a red build |

4. **Escalate every divergence.** Usually the code is right and the plan is stale, but the plan is never silently rewritten to match, because the other possibility is a defect. Present both readings, recommend one, and append the resolution to the plan's `## Decisions` as a dated `D<n>`.
5. **Sweep the class.** If one task diverged because the plan assumed a convention the project does not use, every other pending task assuming it is also wrong. Fix them together.
6. **Check the baseline.** Does the repo build and do its tests pass *right now*? A plan that assumes a green baseline while the build is red is wrong from task one. Report a red state as a finding; it is not yours to silently fix.
7. **Re-sequence what remains**, then have `product:plan-session-budget` re-derive the budgets that changed and rewrite `## Prompts — one per task` **from what you found**, not from what it previously said. Delete the blocks of tasks the reconcile found `Done`; restore a block for a task whose prompt was deleted on a claim the code does not support, and say so in `Status:`.

Report the reconcile as counts plus the divergences in full:

```
Reconcile: 7 Done · 2 Partial · 11 Not started · 1 Diverged · 0 Blocked
Diverged — C1 (auth wiring): plan specifies policy-based authorization;
  code uses role attributes directly (src/Api/Program.cs:44-58).
  Recommend adopting the code and amending the plan: policies buy nothing
  here with three flat roles. Your call.
```
