# Glossary (KB runs) and language examples

Loaded by `SKILL.md` when a KB run writes `glossary.md`, and when a sentence needs a model for turning code into the client's words.

## Glossary

Every domain term found, with its business meaning and the **mapping between the vocabularies** — the client's own term (from the trace's `Client vocabulary` table), what it means, and what the code calls it:

| Term (client) | Means | Called in code | Where the client sees it | Notes |
|---|---|---|---|---|
| Order | A confirmed purchase, from placement to delivery | `Order`, `PurchaseOrder` (legacy) | order confirmation email | Two names for one concept `#observed` |
| Account | The billing relationship, not the login | `Customer` | invoice header | **Drift:** "customer" means the *person* in Identity, the *billing entity* in Billing `#observed` |

**Terminology drift is a finding, not a merge** — record both, flag it, and let `business-analyst` resolve it.

## The same fact, in the code and in the guide

| In the code | In the guide |
|---|---|
| `POST /bookings/{id}/cancel` → 409 when `status != Pending` | You can only cancel an order that has not yet shipped |
| unique index `(tenant_id, order_number)` | Order numbers are unique within an organisation |
| `BookingConfirmed` via outbox after commit | Your credits are worked out after the booking is confirmed |
| `Math.Ceiling(qty * price * rate * 100) / 100` | SEC fee = ROUNDUP(Qty × Fill price × SEC rate, 2) |
| `[Authorize(Roles = "Admin")]` on `PUT /plans/{id}` | Only administrators can change a plan |
