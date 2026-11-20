# Sequencing shape: feature-complete

The default for user-facing work, read when `SKILL.md` Step 2 selects it. One capability at a time, each usable end to end before the next begins. The foundation tasks come first, but only the foundations the **first** capability needs, never every foundation every capability will eventually want.

| Order | Tasks |
|---|---|
| First | Human-blocked provisioning the first capability needs, one task per provisioning track |
| Then | Scaffold, layout, config + validation, CI skeleton, and the cross-cutting surfaces (auth, error envelope, shared DTOs) the first capability actually depends on, nothing speculative |
| Then | **The telemetry base**, one `observability-engineer-<stack>` task, so every request any later task serves shows up in Grafana while it is being built |
| Then | **Test design** (`TD`) for every epic the plan serves: the test-plan task (`qa-test-planner`), then the test-case tasks (`qa-test-case-designer`). They need the stubs and the stories, nothing else, so they sit here once rather than once per capability |
| Then | Capability A's whole set from Step 1, in its natural order: migration → its stubs and OpenAPI asset → its `Q` tasks → entities + rules → service → endpoint bodies → wiring → unit tests → its screens (the app-shell task precedes the first capability's `Q` journeys and screens) |
| Then | Capability B's own set, plus only the foundations B is the first to need |
| Then | One run of tasks per remaining capability, most valuable first |
| Last | The OpenAPI asset's regeneration (test-first) or generation (test-after), business dashboards and alert rules, rate limiting, performance; then the gate task (the whole set); then **the documentation task** (`DOC1`, the documenter agent) |

Test-first costs this shape two agent switches per capability (its `Q` tasks, then back to its implementation); a capability's last task still delivers it.

- **A capability's last task delivers the capability.** Its `Deliverable` is the behavioural sentence, *"a user with the `booker` permission can book a session and then see it under their bookings"*, not "the tasks are done". Order the capability's tasks so exactly one of them makes that true, and make it the last of the run.
- **Deferred foundations are named, not forgotten.** Where a capability's run deliberately stops short of a shared surface a later one will need (a generic error envelope, a pagination convention, a caching layer), say so in that task's `Not in <id>` and place the generalization in the task that first needs it.
- **Schema order stays global.** Migrations run in the order `data-model.md` states even when the sequence is per-capability; a capability's tasks own the migrations for its own entities, at their stated position in that sequence.
