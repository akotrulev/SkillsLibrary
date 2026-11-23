# Skeleton template — the system plan's §3

Read before writing §3 of a system plan. The subsection order is the contract;
[`example-skeleton.md`](example-skeleton.md) shows it filled, and
[`system-plan-format.md`](system-plan-format.md) is the file it sits in.

````markdown
## 3. The skeleton

### Stack and versions
| Dimension | Choice | Version | Why | Evidence |
|---|---|---|---|---|
<!-- One row per dimension the system needs. Evidence: detected (with file:line) | stated | proposed | proposed → approved. -->

**Version lane:** <what was detected and what it implies; an upgrade the system needs is its own feature, never a side effect.>

### Architecture
**Style:** <choice> — <why it is earned for this system>
**Rejected:** <what was considered, and why not>
**Patterns in play:** <pattern — the reason it is earned, one line each; or "none beyond framework idioms">
**Modules:** <modular monolith only: module → schema → owning area → public surface → split trigger, one row each>
**Repository layout:** <one repo per product, its top-level folders; or multi-repo with the stated reason>

```mermaid
flowchart LR
```

### Areas
| Area | Purpose | Serves | Trees | Agents |
|---|---|---|---|---|
<!-- Serves: the E ids from §4, or "all" for the foundation area. Trees: path globs a reader can falsify. Agents: exact catalog names. -->

**Capabilities with no agent:** <named plainly, with what covers them instead; or "none".>

### Auth
<Provider and flows (SPA, service-to-service), roles and where they come from, where each check is enforced, and what a user may read of other users' data.>

### Shared entities
| Entity | Owner area | One line |
|---|---|---|
<!-- Only the entities two or more features bind to. Fields, states and relationships are each feature spec's ## Data model. -->

### Cross-cutting conventions
| Concern | Convention |
|---|---|
| Error envelope | |
| Ids | |
| Pagination | |
| Dates and time zones | |
| Tenancy | |
| Config and secrets | |
| Telemetry base | |
| App shell | <only when something is user-facing: sidebar, top nav or hybrid, with its reason> |
````

A row that does not apply says why in its cell (`Tenancy | single tenant: one studio`), never left
blank. A subsection the system does not need, such as `App shell` for a service with no user, is one
line saying so.
