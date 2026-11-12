# System overview — the same three levels

Load this when writing or refreshing `system-overview.md` and its two siblings — never for an area or feature set.

`system-overview.md` is the entry point for a reader who knows nothing; its two siblings carry what that reader later wants. All three carry the standard header block, with `**Audience:** shareable` on Level 1 and `internal` on the other two, and the same `Derived from` sha.

**`system-overview.md` (Level 1)** — plain:

```markdown
# <System> — What it does
**Created:** YYYY-MM-DD
**Owned by:** `dev:doc-business-model`
**Derived from:** code by `be-documenter` @ `<sha>` on YYYY-MM-DD
**Audience:** shareable
**Levels:** [Guide](system-overview.md) · [Behind the scenes](system-overview.behind-the-scenes.md) · [Technical reference](system-overview.technical.md)

## Overview
<One paragraph: what the system is for, who uses it, and what it produces. Business terms only.>

## The areas
| ID | Area | What it does for users | Document | Depth |
|---|---|---|---|---|
| AREA-001 | Identity & access | … | [areas/identity.md](areas/identity.md) | full |

## End-to-end flows
### New customer's first order
1. **Identity & access** — the customer registers and verifies their email
2. **Catalog** — they browse and add items to a basket
3. **Ordering** — they place the order
4. **Billing** — payment is taken
5. **Notifications** — they receive confirmation
6. **Fulfilment** — the warehouse ships it

## Foundations
<How sign-in and permissions work, how failures reach users, how organisations' data is kept apart. One or two plain lines each.>

## What is not documented
| Area / surface | Why | Revisit when |
|---|---|---|
```

**`system-overview.behind-the-scenes.md` (Level 2)** — written from the dependency map; `EVT-`/`RX-`/`INV-` ids appear only in Level 3, and Level 2's neutral wording, banned words and guarantee words apply:

```markdown
# <System> — Behind the scenes
<header block — Audience: internal>

## At a glance                ← a few sentences and one Mermaid map of the areas and what starts what
## What runs when              ← scheduled and background work, in plain words
## Outside services            ← optional: each service the system talks to, and what happens if it is down
## Where information lives     ← which area owns which records, and which areas read them
## How a failure travels       ← where a problem in one area is noticed in another
## End-to-end flows
### <Flow — same heading as in system-overview.md>
                               ← lanes used only where needed: Straight away (while the person waits) ·
                                 Afterwards (in the background) · On a schedule
```

**`system-overview.technical.md` (Level 3)** — the architecture an agent needs on arrival:

```markdown
# <System> — Technical reference
<header block — Audience: internal>

## How to read this            ← tier legend, path convention, id scheme
## Stack and versions
## Module structure            ← where each area's code lives
## Foundations                 ← authentication and authorisation, tenancy, error handling and problem types,
                                 logging and telemetry, configuration and secrets handling, background-work framework
## Coverage ledger             ← every entry point, job and consumer assigned to exactly one area or parked, with a reason
## Findings                    ← system-wide; links to events.md, shared-data.md, invariants.md, glossary.md
## Evidence index              ← backs both plain files
```

Flows sit under `## End-to-end flows` as `###` headings in both plain files, and the evidence index cites them exactly as an area's: `<Flow heading> · step N`.

**"What is not documented" is mandatory.** A documentation set that does not state its own limits gets read as complete, and the parts nobody traced become the parts everyone assumes are fine.
