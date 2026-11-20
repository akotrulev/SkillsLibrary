# Blueprint template — `blueprint.md`

Read before writing `blueprint.md`. The section order is the contract; `references/example-blueprint.md` shows it filled.

```markdown
# <Initiative> — Solution Blueprint

**Date:** YYYY-MM-DD · **Written by:** `dev:plan-blueprint` · **Status:** DRAFT — awaiting approval
**Initiative folder:** `docs/plans/<NNN>-<initiative>/`
**Entry mode:** NEW | DETAIL | RESUME | EXTEND — <what settled it>
**Sources:** <requirements docs, stories, KB entries, repo paths — with what each contributed>

## 1. The initiative
<3–5 sentences: problem, for whom, what changes when it ships, what success looks like.>

**Success signals:** <measurable where possible; `[TBD - <owner>]` where not.>

## 2. Functional areas
| Area | Epics | Purpose | User-facing capabilities | Primary actors | Key entities | In scope | Out of scope | Depends on |
|---|---|---|---|---|---|---|---|

**Explicitly not in this initiative:** <the boundary, stated once, plainly.>

**Existing data & backfill:** <the system of record being replaced and what comes across, or "none — no predecessor system".>

## 2b. Actors & app shell
<!-- Only when a User-facing capabilities cell is non-empty; otherwise the single line "no user-facing area". -->
| Actor | Most frequent tasks (verb + object + outcome) | Evidence |
|---|---|---|

**App shell:** sidebar | top nav | hybrid — <one-line reason, per `design/ux-patterns` §2> · `proposed`
<!-- Nav map, journeys, screens: experience-plan.md (Step 3), not here. -->

## 3. Architecture
**Style:** <choice> — <why it is earned for this system>
**Rejected:** <what you considered and why not>
**Patterns in play:** <pattern — the reason it is earned. One line each.>
**Modules:** <for a modular monolith: module → schema → owning functional area, one row each, and the split trigger (if any) that would make it a service. Omit for a service-based style.>
**Repository layout:** <one repo per product — contracts/, services/<name>/ with its driving acceptance tests beside the code, web/ mobile/, e2e/, deploy/local/ — or multi-repo with the stated reason (independent teams or release cadences) and one plan per repo.>

```mermaid
flowchart LR
```

**Cross-cutting concerns:** <auth, error handling, logging/telemetry, config, background work — one line each on the approach. Telemetry names the local Grafana stack (`deploy/local/`: Collector, Loki, Tempo, Prometheus, Grafana) and says the telemetry base lands in the foundation.>

## 3b. Key flows & decisions
<!-- One flowchart per primary business flow (named actors, every exit labeled incl. failure).
     One decision table per 3+-input business rule, with a declared hit policy.
     Link to KB artifacts by ID (FLOW-nnn / DEC-nnn) where a business-model KB exists. -->

## 4. Tech stack
| Dimension | Choice | Version | Why | Evidence |
|---|---|---|---|---|

**Version lane:** <what was detected and what it implies; any upgrade this plan assumes, as its own task.>

## 5. External systems
| System | What it does for us | Direction | Criticality | Detail owed to |
|---|---|---|---|---|
<!-- Detail lands in integrations.md — this is the architecture-altitude view only. -->

## 6. Routing map — who builds what
| Area / concern | Agent | Skills it will load | Note |
|---|---|---|---|

**Capabilities with no agent:** <named plainly, with what covers them instead.>

**Execution model:** <one operator, sequential batches | concurrent lanes / Mission Control | no user journey at stake> — <what settled it, and the sequencing shape it selects>

## 7. Non-functional targets
| Dimension | Target | Evidence |
|---|---|---|
| Scale | | |
| Latency | | |
| Availability | | |
| Retention & deletion | | |
| Compliance | | |
| Tenancy & isolation | | |

## 8. Risks
| Risk | Likelihood | Impact | Mitigation / early signal |
|---|---|---|---|

## 9. Assumptions
- ⚠️ **Assumption:** <…> — *confirm by:* <who/when>

## 10. Open questions
**Q1 — <question>?**
*Context:* …
- **A. …** *(recommended)* — …
- **B. …** — …
*Blocks:* …

## 11. Approval
- [ ] Functional areas and scope boundary confirmed, each naming the epic ids it serves
- [ ] Every epic in `epics.md` served by at least one area
- [ ] Actors, their primary tasks and the app shell confirmed (or "no user-facing area")
- [ ] Architecture style and pattern choices confirmed
- [ ] Key flows modelled, every failure exit labeled; decision-table hit policies confirmed (not inferred)
- [ ] Tech stack `proposed` rows confirmed
- [ ] Non-functional targets confirmed or explicitly deferred
- [ ] Open questions answered or deferred with an owner

**Approved by:** <name> · **Date:** <YYYY-MM-DD>
```
