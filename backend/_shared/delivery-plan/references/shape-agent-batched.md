# Sequencing shape: agent-batched

The one-operator shape, read when `SKILL.md` Step 2 selects it. It trades "one capability at a time" for the smallest number of agent switches and file-tree reloads: the same tasks grouped by **who executes them and what they touch**, so each batch is one agent working one tree once.

| Order | Tasks |
|---|---|
| First | Human-blocked provisioning from `integrations.md`, still one task per provisioning track |
| Then | **The contract wave**: one batch carrying everything both sides bind to, for the **whole initiative** rather than the first capability: the full migration sequence, the entity/model types, the shared DTOs and the error envelope, auth wiring, config keys, the typed endpoint signatures with their request/response contracts (stubbed where the behaviour lands later; a test-first plan routes every endpoint to the `501 not-implemented` stub and generates the OpenAPI asset from it), the generated or hand-written API client the frontend imports, and the app shell + nav map + route tree (a placeholder per screen route). Once this lands, no later batch waits on a different agent |
| Then | **The telemetry base**, its own batch because its agent is `observability-engineer-<stack>`: the SDK wiring, the local Grafana stack and the RED dashboard, on the contract wave's scaffold |
| Then | **Test-design batches** (`TD`): the test plans for every epic in one `qa-test-planner` batch, then the test-case suites in as few `qa-test-case-designer` batches as fit |
| Then | **API acceptance batches** (`Q`, `qa-api-<stack>`): one per resource group that fits a session, written against the stubs and red on them, automating the test plan's scenarios bound to them |
| Then | **Journey batches** (`Q`, `qa-ui-<stack>` / `qa-mobile-<stack>` / `qa-desktop-<lang>`): written against the agreed test ids and red on the placeholders |
| Then | **Backend, one batch per module**: a module is a file tree one agent owns (`src/Booking/*`): its entities, domain rules, service, endpoint bodies, registration and unit tests, in a single task. Most-depended-on module first |
| Then | **Frontend, one batch per screen area**: an area is one nav section of `experience-plan.md` §2 and the screens under it, with their components, routes, states and wiring, in a single task, ordered by the nav map |
| Last | The OpenAPI asset's regeneration, business dashboards and alert rules, rate limiting, then the **verification batch**: the full build, the whole test run (old and new), the journeys and the coverage floor, once more across the plan. The acceptance tests are not deferred to it: they ran red before the implementation, and each batch turned its own green. After it, **the documentation batch** (`DOC1`, the documenter agent) closes the plan |

**What may be merged into one batch, all four or it stays separate:**

- **Same agent.** A batch spanning two agents is two tasks. This is the rule the shape exists for.
- **Same file tree**, or trees that no other batch touches. The Step 3 overlap rule is unchanged and still hard.
- **No gate between them**: no human prerequisite, no approval, no open question either one waits on.
- **Every dependency already satisfied by an earlier batch.** A merge that pulls a `Depends on` forward is a reordering, not a merge.

**Two things never merge:** work on opposite sides of the contract wave (a capability's screens do not join its backend module batch because they are one feature), and two tasks whose deliverables cannot be stated as one sentence.

**What the shape costs, stated in the plan rather than discovered:**

- **No capability is usable until both its batches have landed.** The plan says which capabilities become usable at which batch, and the frontend batch that completes each one still carries the behavioural deliverable.
- **Test-first adds two agent switches**, the API batch and the journey batch, between the contract wave and the first module batch.
- **Stubs must be unmistakable.** A contract-wave endpoint with no behaviour yet answers exactly the standard stub response (`501` `application/problem+json`, `type` slug `not-implemented`, `detail` naming the module batch that fills it; validation catalog V8.6), never a fake success or an empty list, and the batch's `Not in <id>` names that batch. An indistinguishable stub is the failure mode of this shape, and a `Q` test cannot be red for the right reason without one.
- **Task discipline does not relax.** A batch *is* a task (`plan-format.md` §4–§5): one deliverable, one agent, its own unit tests and its own gate.

**Several plan packs executed as one delivery** (three initiative folders that together make one working application): the shape is decided once across all of them and the batching is derived across the packs. One contract wave covers every pack's schema and contracts, then the module batches, then the area batches. Tasks keep their own pack's ids and are cited as `<NNN-initiative>/<id>`; the batch order lives in the pack that owns the contract wave, and the others' delivery plans point at it.
