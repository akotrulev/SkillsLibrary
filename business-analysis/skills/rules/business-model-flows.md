---
paths:
  - "docs/business-model/flows/**/*.md"
---

<!-- business-analysis rules v1 (2026-11-03): flows. Installed by /business-analysis:rules; edit to fit this project. -->

# Business flow standards

Severity tags as in the core business-model rules: **blocker**, **major**, **minor**, **nit**. The KB wins where it consistently does otherwise. The template and the event-timeline procedure are `business-analysis:process-flow`'s.

- A Mermaid `flowchart`, not BPMN XML. A `sequenceDiagram` is an investigation of one boundary scenario inside a conflict sweep, never a flow file. *minor*
- Every action has a named actor (customer, reviewer, payment provider, scheduler, the system); more than one actor means `subgraph` swimlanes. An action with no actor is flagged, never guessed. *major*
- One named start trigger, and every path ends in a named outcome, failures included. A path that just stops is a gap finding. *major*
- Every decision node labels every exit, the failure or `no` exit too. Where the source is silent on an exit, it is an open question, never an omitted arrow. *major*
- Every waiting step has its timeout, cancellation and never-arrives exit. *major*
- A merge states what is true at the join; branches that leave the world in different states end separately. *minor*
- Node ids are stable: Mermaid id `n<k>` is `FLOW-nnn.k`. New nodes take the next free number; existing ones are never renumbered. *blocker*
- The Steps table gives every node its actor, precondition, action, postcondition and source. *major*
- An "Event timeline" section lists the past-tense domain events in order with pivotal events marked; an order nobody can state is an open question. *minor*
- What else reacts to an event is a reaction in `events.md`, not prose in the flow file. *minor*
- A happy-path-only chart is an illustration, not a model; extending an existing flow beats a near-duplicate file. *major*
