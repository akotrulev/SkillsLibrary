# Feature cross-section

A feature's cross-section is the set of connections that matter for it. Read it when building one for `ba-feature-conflict-check` (its pair list) or for QA.

The input is an owner id (`E<n>`, `AREA-nnn`) or a trigger id (`EVT-nnn`). It is eight lookups, each a grep, because every row carries ids under the feature-identity rule.

| # | Lookup | Where | What it yields |
|---|---|---|---|
| 1 | Own triggers and reactions | `events.md`, rows with *Owner* = id | What can start this feature, and what it does |
| 2 | Downstream | follow *Emits* → reactions whose *When* is that event, repeated | What it sets off in other features |
| 3 | Upstream | other owners' reactions whose *Emits* reach this feature's reactions | Who else can start it |
| 4 | States depended on | for each `ENT` transition this feature makes, the target state's row in the grid | Other owners' triggers that are legal in that state, plus every `—` and `?` in the row |
| 5 | Decisions | `decisions/` files this feature contributes rows to | The other contributors' rows |
| 6 | Shared data | `shared-data.md` rows naming this feature's reactions | The other writers and readers |
| 7 | Invariants | `invariants.md` rows whose *Threatened by* includes this feature's reactions | What it can break, and whether it guards against it |
| 8 | Known interactions | `interaction-map.md` entries with this feature in *Pair* | Resolved and open conflicts, each with its boundary condition |

**Depth:** two hops past the feature's own reactions. Go further where an effect moves money or cannot be undone. Done when all eight lookups have run and each row names the file and id it came from.

`ba-feature-conflict-check` uses the cross-section as its pair list when the map exists. QA reads it through `qa/manual/requirements-breakdown/references/connections.md`.
