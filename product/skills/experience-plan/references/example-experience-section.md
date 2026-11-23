# Golden example — a spec's `## Experience`

The filled `## Experience` section for `product/skills/experience-plan`, from the toy spec the four
design skills share: `docs/specs/006-booking-cancellation-design.md`, feature F3 *Booking
cancellation* of the system plan `docs/plans/004-workshop-booking-system.md`. Its `## Data model` is
[`example-data-model-section.md`](../../data-model-plan/references/example-data-model-section.md), which
also lists the acceptance criteria AC1–AC6 cited below; its `## API surface` is
[`example-api-surface-section.md`](../../api-surface-plan/references/example-api-surface-section.md).
**The shapes and disciplines are normative; the domain content is illustrative.**

F2's spec, `docs/specs/007-booking-a-seat-design.md`, designed the screens S1 Schedule, S2 Session
detail and S3 My bookings. This feature adds one dialog and changes two of those screens, so it shows
both a new screen block and delta blocks.

---

````markdown
## Experience

**Frontend agent:** `fe-react` — per §3's areas · **Discipline:** `design:app-structure`

### Builds on
| What | Defined in | This feature |
|---|---|---|
| App shell: top nav, two actors, few areas; Vite SPA | §3 cross-cutting conventions and stack | inherits; adds no destination |
| S3 My bookings, `/my/bookings` | 007 | **changed**: a row action, a cancelled state |
| S2 Session detail, `/sessions/:sessionId` (staff attendee list) | 007 | **changed**: a staff row action |

### Actors and tasks
| Id | Actor | Task | Frequency | Stakes | Source |
|---|---|---|---|---|---|
| U1 | Member | cancel my own booking so the seat is released | rare | money-adjacent (a late cancellation is not refunded) | AC1, AC2, AC5 |
| U2 | Staff | cancel a member's booking, saying why, so the seat is released | rare | money-adjacent | AC3, AC5 |

AC4 has no screen: the UI never shows another member's booking, and the rule is proved at the API.
AC6 is an email, designed in `## Integrations`.

### Navigation
**Shell:** per §3 (top nav, two actors, few areas), holding 007's destinations. No destination added:
both tasks start on a screen the member or staff member already uses, at depth one.

### Journeys

**J1 — U1 Cancel my booking** (target: 3 steps)
1. 007 S3 My bookings — row action **Cancel booking** → opens S1
2. S1 Cancel booking — inside 24 h of the start, the late warning shows above the button; **Cancel booking** → `POST bookings/{id}/cancel`
3. 007 S3 — the row shows "Cancelled" (and "Late" when it was); toast "Booking cancelled"
Failure: `session-started` → S1's failed state "This session has already started" with **Close**; the row refreshes to its real state. `invalid-state` → the same, "This booking was already cancelled".
**Acceptance:** AC1, AC2, AC5

**J2 — U2 Cancel a member's booking** (target: 3 steps)
1. 007 S2 Session detail (staff view) — attendee row **Cancel booking** → opens S1 with the reason field
2. S1 — optional reason; **Cancel booking** → `POST bookings/{id}/cancel` with `reason`
3. 007 S2 — the row leaves the attendee list and seats left goes up by one; toast "Booking cancelled — the member has been emailed"
Failure: as J1.
**Acceptance:** AC3, AC5

### Screens

#### S1 — Cancel booking

**Route:** none: a dialog over 007 S3 and 007 S2 · **Actors:** member, staff
**Page type:** confirmation · **Surface:** modal (the interruption is the value: the action cannot be undone, and the seat may be taken at once)
**Primary action:** Cancel booking · secondary: Keep booking (closes, focus back on the row)
**Regions:** summary (workshop title, starts-at) · late warning (member, inside 24 h: "This is less than 24 hours before the start, so it will not be refunded") · reason (staff only, optional, 200 characters)
**States:** loaded · submitting (button in-flight, both buttons disabled) · failed (inside the dialog, with the refusal's reason and **Close**)
**Data needed:** the booking's workshop title and starts-at · the time until which cancelling is free (member) · nothing new for staff, who are never late
**Test ids:** `CancelBooking.Dialog` · `CancelBooking.LateWarning` · `CancelBooking.ReasonInput` · `CancelBooking.ConfirmButton` · `CancelBooking.KeepButton`
**Serves:** U1, U2 · **Journeys:** J1, J2

#### 007 S3 — My bookings — changed
**Primary action (row):** Cancel booking, on a confirmed booking whose session has not started; on a started one it is disabled with the reason "Session has started" (disable, don't hide)
**States (row):** confirmed · cancelled (muted, "Cancelled", and "Late" when it was)
**Data needed (added):** each booking's status, whether it was a late cancellation, the time until which cancelling is free
**Test ids (added):** `MyBookings.CancelButton` · `MyBookings.CancelledLabel`
**Journeys (added):** J1

#### 007 S2 — Session detail — changed (staff view)
**Primary action (attendee row, staff):** Cancel booking → S1
**Data needed (added):** none: 007's attendee list already carries each booking's id
**Test ids (added):** `SessionDetail.AttendeeCancelButton`
**Journeys (added):** J2

### Rendering plan
**Pattern:** all `csr` — §3 put the app on a Vite SPA. The procedure, run on both changed routes,
gives `ssr` with `cache: private` (signed-in, personal, not long-session tools). The interview put it
to the owner as "this changes the system plan's §3 Frontend line: keep it or change it?", and the
owner kept the SPA: nothing in the app is public, and the cost is a skeleton on first paint
(Decisions from the interview). No route is added.

```yaml
rendering_plan:
  stack: vite-spa
  routes:
    - path: /my/bookings
      screen: 007 S3
      mode: csr
      cache: private
      shell: static
      offline: false
      signals: { discoverability: not-needed, audience: signed-in, freshness: never, personalisation: page, interactivity: light }
    - path: /sessions/:sessionId
      screen: 007 S2
      mode: csr
      cache: private
      shell: static
      offline: false
      signals: { discoverability: not-needed, audience: signed-in, freshness: never, personalisation: section, interactivity: light }
  acceptance:
    - a deep link and a refresh on both routes land on the route, not a 404
    - the cancellation dialog opens without a network round trip
```

### Screen ↔ endpoint matrix
*(filled by the API step against `## API surface`)*

| Screen | Endpoint | Purpose on this screen |
|---|---|---|
| S1 | `POST /api/v1/bookings/{bookingId}/cancel` | Cancel booking (member and staff) |
| 007 S3 | `GET /api/v1/my/bookings` (changed) | `status`, `lateCancel`, and `freeCancelUntil` for S1's late warning |
| 007 S2 | `GET /api/v1/sessions/{sessionId}/bookings` (007, unchanged) | the attendee row's `bookingId` |

Coverage: user-facing endpoints this feature adds, on ≥ 1 screen: 1/1. Data needs resolved: 3/3
(`freeCancelUntil` is a computed field the API step added rather than stored).

### Cross-cutting
**Density, accelerators, first run:** per 007. · **Notification surface:** inline + toast, no Undo: a
cancelled seat may be booked by someone else at once. The member's email is `## Integrations`'.
**Responsiveness budget (acceptance criteria for every frontend task):**
- [ ] every press acknowledged ≤ 100 ms (pressed state; Cancel booking disables with in-flight state)
- [ ] a region still loading at 300 ms shows a content-shaped skeleton, never a blank or page-centre spinner
- [ ] a region still loading at ~4 s says so; a timed-out region fails with retry, scoped to itself
- [ ] no layout shift on load; the cancelled row changes in place

### Open questions
| # | Question | Owner |
|---|---|---|
| — | none of its own; whether members give a reason too is `## Data model` open question 1, and only S1's reason region would change | |
````
