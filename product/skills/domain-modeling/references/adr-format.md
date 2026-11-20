# ADR format

An architecture decision record keeps one hard-to-reverse technical decision and the reason for it, so a later reader neither undoes it by accident nor argues it again.

## When one is written

All three tests hold, or no ADR:

1. **Hard to reverse.** Changing course later costs real work: a migration, a rewrite, a contract with another team.
2. **Surprising without context.** A reader who meets the result in the code would ask why it was done this way.
3. **The result of a real trade-off.** There were genuine alternatives, and one won for reasons worth keeping.

An easy-to-reverse choice, an obvious one or one with no alternative gets no ADR.

What usually qualifies:

| Kind | Example |
|---|---|
| Architectural shape | An event-sourced write model with a relational read model |
| Integration between areas | Billing reacts to booking events instead of calling the booking API |
| Technology with lock-in | The database, the message bus, the auth provider, the hosting target: anything that takes months to swap, not every library |
| Ownership boundaries | Which area owns which data, including the explicit "never" rules |
| Deliberate deviations | Hand-written SQL on the reporting path instead of the ORM, so nobody "fixes" it |
| Constraints the code cannot show | A data-residency rule that excludes a region, a latency target set by a partner contract |
| A rejected alternative that will come back | REST over GraphQL, for a reason that is not obvious |

## Where it lives

`docs/adr/NNNN-<slug>.md` in the project the session works in. `NNNN` is four digits: the highest existing number plus one, `0001` for the first. `<slug>` is the decision in kebab-case. The folder is created with its first ADR. A business rule table is not an ADR: it is a `DEC-` file in `docs/business-model/decisions/`.

## The template

The default is a title and one paragraph: the context, the decision, and why.

```markdown
# Billing reacts to booking events

Billing must charge for every confirmed booking, and the booking API is owned by another team with a weekly release cadence. Billing subscribes to `BookingConfirmed` on the outbox stream instead of calling the booking API, so either side can deploy alone; the cost is that a charge lags its booking by seconds, which the business accepted. Decided in docs/specs/004-billing-design.md.
```

Add a section only when it earns its place:

| Section | Add it when |
|---|---|
| `**Status:** proposed \| accepted \| superseded by NNNN` under the title | The decision may be revisited, or it already has been |
| `## Considered options` | The rejected alternatives are worth remembering, with one line each on why they lost |
| `## Consequences` | A downstream effect is not obvious from the decision itself |

## Writers and changes

- **Written by** `product:feature` during the interview, the `solution-planner` blueprint step, and any plan task that records a `D<n>` passing the three tests. A plan-born ADR cites the plan and its `D<n>`.
- **Superseded, never edited away.** A changed decision is a new ADR; the old one gains `**Status:** superseded by NNNN` and keeps its text.
- **Read before changing what it covers.** Work that touches what an ADR decides respects it, or writes the ADR that supersedes it.
