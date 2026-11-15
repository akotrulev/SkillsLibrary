# Delivery note — what a plan built

Load this when writing the delivery note of a plan. The note is written only when the documenter runs as the plan's documentation task (`DOC1`), after the guides are updated — never on a standalone run.

One file per plan, **`docs/deliveries/<NNN>-<plan-slug>.md`** (`<NNN>` is the plan's number), in the same place for `be-documenter` and `be-feature-documenter`. It is for the product owner: what the plan delivered, in business words, with a link into the guide for each thing.

````markdown
# What was delivered — <the plan's title, in the client's words>

<One sentence: what people can do now that they could not before.>

## New — what people can do now
| Story | Who | What they can do now | Read more |
|---|---|---|---|
| US3 | Members | Cancel a booking and get the credits back when it is 24 hours or more ahead | [Cancel a booking](../business-model/areas/credits-and-charges.md#cancel-a-booking) |

## Changed — what works differently
| What | Before | Now | Who notices |
|---|---|---|---|

## Not delivered
| Story | What was planned | What the product does today |
|---|---|---|

## Questions this raised
<n> new questions for the product owner — in [<guide>](…#open-questions).

## About this document
**Delivered:** YYYY-MM-DD
**Describes:** the product as it was on YYYY-MM-DD

<!-- delivery · plan: NNN · source: be-documenter @ <sha> · stories: US1, US2, US3 · audience: shareable -->
````

## Rules

- **Read from what landed, never from the plan's intentions.** *New* and *Changed* come from the code at `HEAD` and the guides just updated: the reconcile verdicts **New**, and the `~~old~~ → new` facts. *Read more* links the guide's task.
- **`## Not delivered` is always present.** It holds every story or acceptance criterion the plan held that the code at `HEAD` does not do, or does differently, with what the product does today. When everything was built, the heading holds one line, "Everything the plan set out to build was built.", and no table.
- **A plan with no stories** puts `—` in the *Story* column and takes its rows from the plan's task deliverables.
- **Story ids are allowed in the *Story* column** — they are the product owner's own. They are the only ids; no `AREA-`, `FLOW-`, `Q<n>` or other internal id appears.
- **The guide's language rules apply:** the client's words, no code names, jargon, status codes or tier tags, no judging words, no guarantee words, no roadmap promises. A difference between a story and the code is stated as a fact ("Unused credits are lost on the 1st of the month"), never as a fault.
- **Empty tables are dropped with their heading**, except *Not delivered*. *Questions this raised* is dropped when the run raised none.
- **The stamp** is the last line: `delivery`, `plan`, `source: <agent> @ <sha>`, `stories` (every story the plan held), `audience: shareable`. `**Delivered:**` is the date of the run; `**Describes:**` the date the product was read.
- **Rendering and lint** are the guide's: `render-html.py --dir docs/deliveries` and `doc-lint.py --dir docs/deliveries` (or a named file). The lint knows a delivery note by its first line, `# What was delivered`, runs the language rules on it, and requires `## Not delivered`, `## About this document` and the stamp.

## Worked example

The `workshop-booking` toy of [`example-area.md`](example-area.md), as the plan that built the credits would leave it in `docs/deliveries/004-session-credits.md`:

```markdown
# What was delivered — Session credits and charges

Members can now spend a monthly allowance of credits on sessions and pay only for the bookings beyond it, on plans and rates that staff set.

## New — what people can do now
| Story | Who | What they can do now | Read more |
|---|---|---|---|
| US1 | Members | Book a session and see its cost in credits, by tier: Standard 1, Workshop 2, Masterclass 3 | [Book a session](../business-model/areas/credits-and-charges.md#book-a-session) |
| US2 | Members | Keep booking when the credits have run out; the shortfall is charged as an overage | [Book a session](../business-model/areas/credits-and-charges.md#book-a-session) |
| US3 | Members | Cancel a booking and get the credits back when it is 24 hours or more ahead | [Cancel a booking](../business-model/areas/credits-and-charges.md#cancel-a-booking) |
| US4 | Staff | Set plans, session tiers and a member's personal overage rate on the Session credits screen | [Set up plans and tiers](../business-model/areas/credits-and-charges.md#set-up-plans-and-tiers) |
| US5 | Members | See one overage charge for the month's total on the 1st of the month | [Monthly posting](../business-model/areas/credits-and-charges.md#monthly-posting) |

## Changed — what works differently
| What | Before | Now | Who notices |
|---|---|---|---|
| What a booking costs | Every booking was charged the session's price | A booking spends the member's credits first; only the shortfall is charged. A Masterclass of 3 credits with 2 left spends 2 and charges £6.00 on Basic (1 credit × £6.00) | Members |

## Not delivered
| Story | What was planned | What the product does today |
|---|---|---|
| US6 | Unused credits carry over to the next month | Unused credits are lost on the 1st of the month |

## Questions this raised
4 new questions for the product owner — in [Session credits & charges](../business-model/areas/credits-and-charges.md#open-questions).

## About this document
**Delivered:** 2026-09-14
**Describes:** the product as it was on 2026-09-14

<!-- delivery · plan: 004 · source: be-documenter @ e5d7b02 · stories: US1, US2, US3, US4, US5, US6 · audience: shareable -->
```
