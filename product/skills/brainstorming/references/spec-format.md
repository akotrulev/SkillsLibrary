# The design and the spec

The design rules step 8 presents against, then the file step 9 writes.

## Design rules

- **Small, well-bounded units.** Each unit has one purpose, a defined interface, and can be understood and tested without reading its internals. For each one, say what it does, how it is used and what it depends on. A unit you cannot describe that way needs better boundaries.
- **Scope and patterns follow `CLAUDE.md`:** "Simplicity (KISS)" for what stays out, and the read-2–3-existing-files rule ("Backend code rules") for matching the codebase. The design-specific part: where existing code stands in the way of the work (a file grown too large, a tangled responsibility), include a targeted improvement in the design, and leave unrelated refactoring out.

## The spec

`docs/specs/NNN-<feature>-design.md`, resolved against the project the session is working in, never this skills-library checkout or a global config directory unless the user asks for a global copy. `NNN` is zero-padded and scoped to `docs/specs/`: the highest existing prefix plus one, `001` when the folder is empty or absent. A user preference for the spec location wins.

```markdown
# Booking cancellation Design

**Date:** 2026-11-20 · **Written by:** `/product:plan-feature`
**System plan:** docs/plans/021-gym-system-system.md F3

## Goal
## Architecture
## Components
## Data flow
## Error handling
## Testing
## Acceptance criteria
- **AC1** — A member cancels their own booking more than 24 h before the session; the seat is released and the booking shows as cancelled.
- **AC2** — A member cancelling inside 24 h is told no refund applies before confirming.
## Data model
## Experience
### Rendering plan
## API surface
## Decisions from the interview
- Who can cancel a booking → the member and staff; a member cancels a booking staff made for them → closes *ownership*, opens *staff audit trail*
- Refund on late cancellation → none inside 24 h → closes *refund policy*
## Engineering calls
- The seat limit is a database constraint, not a check in code: two members taking the last seat at once cannot both succeed
- Cancellation is a status on the booking, never a delete: staff can see who cancelled and when
## Prototype
```

- **`**System plan:**`** names the system plan and the feature id, in SYSTEM mode only.
- **`## Acceptance criteria`** holds `AC1…ACn`, each one condition a tester can mark met or not met, in the user's words. The plan's `TD` and `Q` tasks cite them as `<spec path> AC<k>`; an id is never renumbered once the plan cites it.
- **The design sections** (`## Data model`, `## Experience`, `## API surface`, `## Integrations`) appear only when step 8 read their skill; the example has no integration.
- `## Decisions from the interview` holds one line per answer, in step 6's read-back order. `## Engineering calls` holds one line per call the session made itself (the call, then what it means for a person or why), in the order step 6 read them back; a call the user reopened moves to `## Decisions from the interview`. `## Prototype` holds the chosen variant and why, when a prototype was made; leave the heading out otherwise.
- **A draft on hold** adds `**Status:** on hold — <the open question>` under the date line.
