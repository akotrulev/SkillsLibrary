# Cross-artifact checks — Step 9 of the solution-planner

Read at Step 9, after Steps 7–8, over the whole pack in `docs/plans/<NNN>-<initiative>/`. Each check spans two or more artifacts, so no single planning skill's self-check sees it. Fix what you find inline, then re-run the check. A brownfield run re-enters only the touched steps, but Steps 7–9 always run.

**Done when** every line below holds and the report's `Coverage (step 9)` counts are real.

**Backlog and tasks**

- Every capability in `requirements.md` §4 reaches an epic, and every epic reaches a task.
- Every cited `E` / `US` id exists, unrenumbered (`E0` excepted).
- Every capability's last task states behaviourally what a user can then do.

**Model, API and screens**

- Every API field resolves to a column, a computed value or a named external source, and every table is read or written.
- Every user-facing endpoint is on a screen (or named machine-to-machine), and every screen's data need resolves to an endpoint.
- Every journey's screens exist and are built by a task citing their ids.
- Every web route has a §4a rendering entry free of the reference's anti-patterns; its `fe` task quotes it; its server-rendered content is asserted on the raw HTML by a `Q` task.

**Plan shape**

- Lanes the epic map runs together are disjoint in the delivery plan's `Files` lists, not only in the epic map's own claim.
- In a test-first plan, every AC with an API or journey outcome reaches a `Q` test, and untested behaviour the plan must keep has a pin task.
- Every epic with stories has a test plan from a `TD` task, and every story a test-case suite; each `Q` task depends on the test-plan task for its epic; the gate task checks each plan's Definition of Done (or the header records the opt-out).
- The plan's last task is `DOC1` (stack `docs`, `documenter` or `feature-documenter`), depends on the gate task and names the documents it updates.
- A telemetry-base task follows the scaffold, and every `be` task that adds an entry point, an outbound call, a job or a business event names its spans, logs and metrics.
- Every agent and skill name resolves in the catalog.
