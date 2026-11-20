# The ten inventories — column specifications

Load this before writing any inventory. Each section gives what the inventory records and its `guide`-profile reduction; `file:line` stays on every item in both profiles. The Tasks inventory's columns live in `SKILL.md`.

## 1. Tasks
What people do, built first: the person's words, actor, `screen › control`, the entry points it calls, and the source row (route, test or plan line).

| # | Task (the person's words) | Who | Screen › control | Entry points it calls | Source |
|---|---|---|---|---|---|
| 1 | Cancel a booking | Member | Your bookings › Cancel booking | `POST /bookings/{id}/cancel` | `app/bookings/page.tsx:42` |

Every role, administrators included: back-office and settings screens are tasks. Take the control's text from the route and its translation file (default language); a control not found is `none — searched …`, never a guess.

## 2. Capabilities
What a user or system can make this area do: one business-language verb phrase each, with actor and entry point, plus the entry point's **contract** in one line (request → response, or the schema file holding it) and its **authorization** string (policy, permission, scope).

> "A customer can cancel an order that has not yet shipped (`OrdersController.cs:88`)" `#observed`

**`guide`:** the capability and its actor only — no contract line, no authorization string.

## 3. Business rules
Every condition, threshold, calculation and eligibility test the code enforces — what the business cares most about, and most likely written nowhere else.

| Rule | Condition | Effect | Inputs | Met in | Evidence | Tier |
|---|---|---|---|---|---|---|
| Refund window | Order closed more than 30 days ago | Refund rejected | — | Request a refund | `RefundService.cs:88` | `#observed` |
| Overage charge | Credits used exceed the plan's credits | The excess is charged at the overage price | credits used, credits in the plan, overage price per credit | Monthly posting | `Posting.cs:57` | `#observed` |

Write the rule as the business would state it. **Record the number, not a rounding** — "30 days", not "about a month".

- **Met in** names the task (by its Tasks row) or the automatic work where a person meets the rule; a rule that spans several says `everywhere`. The guide's *Rules and limits* table needs it.
- **Inputs** is filled for every calculation: each input in the client's words (from `Client vocabulary`), with the rounding, day-count and currency conventions the code applies. The guide's *How it is calculated* is written from it.

## 4. Validations & gates
Authorization, input validation, preconditions, state guards — each with its failure in user terms **and** the technical outcome (status or problem type, exception type). Where the person sees a message, **quote the refusal text verbatim** with its source (`"You can't cancel within 24 hours of the session."` — `Resources/Bookings.en.resx:12`); "none shown — searched …" for a bare status.

**`guide`:** the user-visible failure and the verbatim message only — no technical outcome.

## 5. Entity states & transitions
Per owned entity: the states, the moves, who triggers each, and what is blocked — from enums, status columns, guard clauses and the transitions the code *refuses*. **Refusals matter as much as transitions:** a missing arrow is a business rule ("a shipped order never returns to pending"), usually written nowhere else.

Record, per state, **whether the product shows it to a person** — the label as shown and where (a badge on a screen, a word in an email), from `Client vocabulary`; or `not shown — searched …`. The guide draws a state diagram only for states a person sees.

**`guide`:** only the statuses a person sees, with their moves and refusals.

## 6. Decision points
Any branch where more than two inputs combine to select an outcome (pricing, eligibility, routing, discounting, risk scoring): the inputs, the combinations, the result of each. Decision tables built from them expose the code's gaps and contradictions.

## 7. Integrations
Per external system: the trigger, what is sent (business-level, not payload schemas), what comes back, and **what happens when it fails** — timeout, retry, fallback, or unhandled (a finding). Also **what a person notices**: who is told, what they receive, what they experience when the system is down or refuses.

**`guide`:** only what a person notices, and the failure as they experience it — not what is sent or expected (the trigger and the failure behavior are still read to find that out).

## 8. Edges
Where this area touches another, one hop out. For every emitted event, message, outbox row or notification, find its consumers (`file:line`, owning area). (`full`) For every written field, find the readers **and other writers**, scheduled jobs' queries included. State how each reaction runs and what happens when it fails.

| # | Entry point | Kind | Reads | Writes | Also written by | Emits | Reacted to by (one hop out) | Mode | On failure | What people notice | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `POST /bookings/{id}/cancel` | command | `Booking.status`, `Session.start` | `Booking.status`, `Session.seats_taken` | `Booking.status`: `BookingExpiryJob.cs:31` (Scheduling) | `BookingCancelled` | `BookingCancelledHandler.cs:19` (Credits) | after commit, `?` | `?` | The member gets the credits back | `BookingService.cs:88-104` |

- **Kind**: `command`, `schedule`, `timeout`, `external`, `event`. **Mode**: `in request`, `after commit, <guarantee>`, `scheduled`, `best effort`. **On failure**: rolls back, retried n× then dead-letter, compensates, unhandled.
- **A mode or guarantee the code does not show is `?`.** A library name proves nothing: at-least-once only where a retry, redelivery or missing acknowledgement is visible in code or configuration.
- **A negative claim names its search**: "no consumer of `BookingCancelled` — searched `BookingCancelled`, `booking.cancelled` under `src/`".
- Stop at one hop; the consumer's own events are its row when its area is traced.
- **Also record, for the models and for what a person notices:** what runs after commit; the retry count and what follows the last retry; a reaction's delay where the code shows a delay, schedule or poll interval. Anything not shown is `?`.
- **What people notice** is filled for every row, and above all for **automatic work** (the row's Kind is `schedule`, `timeout` or a consumer no task triggers): which person sees, receives, is charged or loses what — "members with overage see one charge for the month", "unused credits from the month before are lost" — not what the job does inside. Work nobody notices is `none`. The schedule is a `Business rules` row (*Met in* the automatic work).

**`guide`:** keep Entry point, Kind, Emits, Reacted to by (with the area that owns the reaction — the other guide a person may be sent to), On failure **as the person experiences it**, What people notice, Evidence. Drop **Reads, Writes, Also written by, Mode**.

## 9. Configuration & switches
Every configuration key, option class, environment variable name, feature flag and behaviour-changing constant: where defined, default, effect, whether it varies per environment or tenant, and who can change it and where (a screen, a deployment setting, nowhere). **Names only — never a secret's value.** A constant that looks like it should be configurable (cut-off, rate, window) is recorded with its number and is an open question. "None — searched …" is recorded.

**`guide`:** the value, who can change it and where — no definition site, no environment spread.

## 10. Tests & telemetry
The tests covering the area (path and line, what each covers, what none covers — boundaries especially) and the telemetry emitted (decision-point logs, spans, metrics; library and names). Tests evidence intent, never behaviour. A missing test or telemetry is a technical finding.

**`guide`:** not recorded. Tests are read only as leads for intent and example values.
