---
name: process-flow
description: Use when turning requirements into a BPMN-style Mermaid business flow with actors, decisions and failure paths. Triggers "map the flow for this feature". Not for entity lifecycles (state-grid).
disable-model-invocation: true
---

# BA — Flow Mapper

Turns requirements into a **business-flow model that forces the questions the prose never answers**: what happens on failure? who acts at this step? where does the timeout path go? which branches rejoin? The model is a reasoning instrument, not documentation — every standard it must meet exists because prose requirements systematically hide a class of gap that the diagram makes impossible to hide.

The notation is a **Mermaid flowchart** (text-based, diffable, token-cheap, renders in GitHub/artifacts) with **BPMN's discipline borrowed as authoring rules** — not BPMN XML.

## Contract with the KB

Per `product/skills/ba-project-memory`: **read first** (`INDEX.md` + any existing flow files this feature touches + `glossary.md` for the terms it uses), **update after** (the flow file, `INDEX.md`, `active-context.md`). Extending an existing flow beats creating a near-duplicate — check the INDEX before authoring `flows/<new>.md`.

## Standards (the BPMN discipline)

What a flow file must meet (named actors and swimlanes, a start trigger and named outcomes with no dead ends, every decision exit labelled including failure, timeout and never-arrives exits, merges that state what rejoins, stable `FLOW-nnn.k` node ids, the precondition → action → postcondition steps table, glossary terms only) is the product rule files, not a list here: `business-model-flows.md` plus the core `business-model.md`. Read the project's copy in `.claude/rules/product/`, or the plugin's in `product/skills/rules/` when the project has not installed them (`/product:rules` does). Where they and this skill disagree, the rule files win. They are also this skill's quality bar.

## The event-timeline pass (do this before drawing)

A degraded — deliberately solo-agent — form of event storming. Before drawing the chart:

1. **Derive the domain-event list** from the requirements: past-tense facts ("Order Placed", "Payment Captured", "Refund Issued").
2. **Order them on a timeline.** Where order is unclear or contested, that's a hotspot → open question.
3. **Ask per event:** *what must already have happened?* (missing preconditions = missing upstream steps) and *who else reacts to this?* (hidden fan-out: notifications, quotas, lifecycle jobs, analytics — the recurring interaction hotspots). The answers to "who else reacts" are recorded as reactions in `events.md` through `product:dependency-map`, not left in the flow file.
4. **Mark pivotal events** — ownership/step boundaries ("Payment Captured" hands off from checkout to fulfillment). Pivotal events are the natural seams for splitting a big flow into linked sub-flow files.

The timeline is scaffolding; keep it in the flow file under "Event timeline" — it's the cheapest cross-feature ordering check the sweep has.

## Flow file format (`docs/business-model/flows/<flow>.md`)

````markdown
# Flow — <Name> (FLOW-001)

**Created:** <YYYY-MM-DD>
**Owned by:** `product:process-flow`
**Last updated:** <YYYY-MM-DD> by `product:process-flow` — <one line what changed>

**Sources**: <US<n> / BRD / contract refs> · **Feature**: <E<n> label, or AREA-nnn>
**Actors**: <list>
**Trigger**: <the start event>
**Outcomes**: <every terminal state, incl. failures>

## Diagram
```mermaid
flowchart TD
    subgraph customer [Customer]
        n1([Customer submits order])
    end
    subgraph system [System]
        n2{Stock available?}
        n3[Reserve stock]
        n5([Order confirmed])
        n6[Release stock]
        n7([Order rejected — out of stock])
        n8([Order rejected — payment])
    end
    subgraph provider [Payment provider]
        n4[Capture payment]
    end
    n1 --> n2
    n2 -->|yes| n3
    n2 -->|no| n7
    n3 --> n4
    n4 -->|captured| n5
    n4 -->|declined| n6
    n4 -->|timeout 30s| n6
    n6 --> n8
```

## Steps
| Node | Actor | Precondition | Action | Postcondition | Source |
|---|---|---|---|---|---|
| FLOW-001.4 | Payment provider | stock reserved | capture the payment | payment captured or declined or timed out | US42 AC2 |

## Event timeline
Order Placed → Stock Reserved → Payment Captured *(pivotal — hands to fulfillment)* → …

## Open questions
- ❓ [TBD - source silent] What happens to the reservation if the customer abandons before payment? ⚠️ Assumption: released after 15 min `#inferred`
````

## Anti-example

Bad: a happy-path-only flowchart — `Submit → Validate → Pay → Done` — with no actors, no failure exits, drawn in chat and never persisted. That's an illustration of the requirements, not a model of them; it answers no question the prose didn't.

Good: the same flow with the declined/timeout/abandon paths forced into the open, three of them flagged `[TBD]` because the requirements are genuinely silent — those flags are the deliverable.
