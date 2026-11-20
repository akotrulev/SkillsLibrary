# Glossary (KB runs) and language examples

Loaded by `SKILL.md` when a KB run writes `glossary.md`, and when a sentence needs a model for turning code into the client's words.

## Glossary

The table, its columns and its rules (synonyms under `Avoid`, drift kept as a finding) are in `${CLAUDE_PLUGIN_ROOT}/engineering-practices/domain-modeling/references/glossary-format.md`. What a KB run adds:

- **Every domain term the trace found gets a row**, mapping the vocabularies: the client's own term from the trace's `Client vocabulary` table, what it means, and what the code calls it.
- **`Called in code` comes from the code you read**: every identifier for the concept, a legacy one marked `(legacy)`, with the `file:line` in *Notes* and the tag `#observed`.
- **Two identifiers for one concept** are one row, both under `Called in code`: a naming split in the code is not a synonym in the client's language, so `Avoid` stays as the client's words decide.
- **Drift found in the code** (one client word, a different concept per area) is recorded and left to the `business-analyst` agent; never merge it.

## The same fact, in the code and in the guide

| In the code | In the guide |
|---|---|
| `POST /bookings/{id}/cancel` → 409 when `status != Pending` | You can only cancel an order that has not yet shipped |
| unique index `(tenant_id, order_number)` | Order numbers are unique within an organisation |
| `BookingConfirmed` via outbox after commit | Your credits are worked out after the booking is confirmed |
| `Math.Ceiling(qty * price * rate * 100) / 100` | SEC fee = ROUNDUP(Qty × Fill price × SEC rate, 2) |
| `[Authorize(Roles = "Admin")]` on `PUT /plans/{id}` | Only administrators can change a plan |
