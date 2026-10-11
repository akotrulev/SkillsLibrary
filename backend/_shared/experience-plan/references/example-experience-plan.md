# Workshop Booking — Experience Plan

**Date:** 2026-08-27 · **Written by:** `dev:plan-experience` · **Discipline:** `design:app-structure`
**Inputs:** `./blueprint.md` (§2 capabilities, §3b FLOW-001/002, §6 routing) · `./data-model.md`
**Frontend agent:** `fe-react` — per the routing map (Next.js App Router, MUI)

## 1. Actors & primary tasks

| Id | Actor | Task | Frequency | Stakes | Source |
|---|---|---|---|---|---|
| U1 | Member | book a seat on an upcoming session so it is held for me | weekly | money-adjacent | blueprint §2 Booking · FLOW-002 `#confirmed` |
| U2 | Member | see my upcoming bookings so I know where to be | weekly | routine | blueprint §2 Booking `#confirmed` |
| U3 | Member | cancel a booking inside the policy window so my seat is released | rare | money-adjacent (late-cancel mark) | blueprint §2 Booking · DEC-001 `#confirmed` |
| U4 | Anyone signed in | browse the published schedule to pick a session | weekly | routine | blueprint §2 Scheduling `#confirmed` |
| U5 | Staff | publish a workshop and add its sessions so members can book | weekly | routine | blueprint §2 Scheduling `#confirmed` |
| U6 | Staff | mark attendance on a session so the record is right | daily (on session days) | compliance | blueprint §2 Booking `#confirmed` |
| U7 | Staff | cancel any member's booking (member notified) | rare | money-adjacent | DEC-001 R3 `#confirmed` |

Ranking: members live on U4 → U1 and U2; staff live on U6 and U5. Two home screens, one per role (§2).

## 2. App shell & navigation

**Shell:** top nav — four member destinations, two staff destinations; every page is a document, not a workbench; no grouping need. · **Rejected:** sidebar — five destinations would waste the column on every page. · **Mobile:** bottom tabs (Schedule · My bookings · Account) for members; drawer for staff.
**Role handling:** one nav with role-hidden destinations (Workshops and Attendance render only for `workshops:manage`) — one app, one shell; the blueprint's single Auth0 tenant with roles makes separate entry points dishonest.

| Destination | Nav placement | Actor(s) | Tasks it serves | Page type |
|---|---|---|---|---|
| Schedule | primary · first item · member home | member, staff | U4, U1 (entry) | list → detail |
| My bookings | primary | member | U2, U3 | list |
| Workshops | primary · staff only · staff home | staff | U5 | list → detail → form |
| Attendance | primary · staff only | staff | U6, U7 | list (today's sessions) → detail |
| Account | account menu | all | sign out, profile | settings |

Depth check: U1 is Schedule → Session detail → Book (one click to the list, the action on the second screen); U6 is Attendance → today's session (one click). Nothing at depth three.

## 3. Journeys

**J1 — U1 Book a seat** (target: 3 steps · FLOW-002)
1. S1 Schedule — pick a date range (default: next 14 days) → `GET sessions?from&to`
2. S2 Session detail — **Book seat** → `POST sessions/{id}/bookings`
3. S2 (same screen) — booking shown inline under the header; toast "Seat booked" with **Undo** (→ cancel path, inside the 24 h window by construction)
Failure: `capacity-reached` → S2 region shows the failed state "This session is full" with **Back to schedule**; waitlist is out of scope (blueprint §2). Back-button from S2 returns to S1 with the date range preserved (URL state).

**J2 — U2/U3 See and cancel a booking** (target: 2 steps)
1. S3 My bookings — upcoming first → `GET my/bookings`
2. S3 row action **Cancel booking** → confirmation names the session and, past the 24 h window, states the late-cancel consequence (DEC-001) → `POST bookings/{id}/cancel`; row updates inline to "Cancelled"
Failure: `invalid-state` (already cancelled elsewhere) → row refreshes to its real state, persistent notification explains.

**J3 — U5 Publish a workshop with sessions** (target: 4 steps)
1. S4 Workshops — **New workshop** → S5
2. S5 Workshop form (create) — Save → `POST workshops` → lands on S6 (draft)
3. S6 Workshop detail — **Add session** (drawer: starts-at, capacity) → `POST workshops/{id}/sessions`, repeat
4. S6 — **Publish workshop** → `POST workshops/{id}/publish`; status chip flips to Published
Failure: publish with zero sessions → the action is disabled with the reason "Add at least one session" (disable-don't-hide).

**J4 — U6 Mark attendance** (target: 2 steps)
1. S7 Attendance — today's sessions (default filter = today) → `GET sessions?from=today&to=today`
2. S2 Session detail (staff view) — attendee list, **Mark attended** per row → `POST bookings/{id}/attend`; row state updates inline, optimistic (reversible — `[TBD - product owner, before T-build]` whether un-attend exists; until then not optimistic)

## 4. Screens

### S1 — Schedule

**Route:** `/schedule` · **Nav:** Schedule · **Actors:** member, staff
**Page type:** list · **Surface:** page
**Primary action:** none (browse) — the row is the action
**Regions:** toolbar (date range, workshop filter — URL-reflected) · session list (grouped by day; title, workshop, starts-at, seats left)
**States:** loading skeleton (day groups) · loaded · failed (list only; toolbar stays) · empty — no-records "No sessions scheduled yet" vs no-match "No sessions in this range. Clear filters"
**Data needed:** sessions in range with workshop title, startsAt, capacity, bookedCount (aggregate — not stored), whether I already hold a booking on each
**Serves:** U4, U1 · **Journeys:** J1

### S2 — Session detail

**Route:** `/sessions/{sessionId}` · **Nav:** Schedule › (breadcrumb) · **Actors:** member, staff
**Page type:** detail · **Surface:** page (shareable)
**Primary action:** Book seat (member; disabled with reason when full or already booked) · Mark attended per attendee row (staff)
**Regions:** header (workshop title, starts-at, seats left, status chip) · description · my booking (member, when held) · attendee list (staff only)
**States:** each region loading skeleton · loaded · failed with retry · attendee list empty "No bookings yet"
**Data needed:** session with workshop title, description, startsAt, capacity, bookedCount · my booking on it, if any · attendees with member display name and attendance state (staff)
**Serves:** U1, U6 · **Journeys:** J1, J4

### S3 — My bookings

**Route:** `/my/bookings` · **Nav:** My bookings · **Actors:** member
**Page type:** list · **Surface:** page
**Primary action:** none — Cancel booking is the row action; empty state's action is **Browse the schedule** → S1
**Regions:** list (upcoming first, then past, collapsed)
**States:** loading skeleton · loaded · failed · empty no-records "No bookings yet. Browse the schedule"
**Data needed:** my bookings with session title, startsAt, state, whether cancel is inside the free window (computed from DEC-001 — server-side, so the confirmation copy is right)
**Serves:** U2, U3 · **Journeys:** J2

### S4 — Workshops (staff)

**Route:** `/staff/workshops` · **Nav:** Workshops · **Actors:** staff
**Page type:** list · **Surface:** page
**Primary action:** New workshop → S5
**Regions:** toolbar (status filter) · workshop list (title, status chip, session count, next session)
**States:** loading skeleton · loaded · failed · empty no-records "No workshops yet. Create your first workshop" vs no-match
**Data needed:** all workshops with status, session count, next session startsAt
**Serves:** U5 · **Journeys:** J3

### S5 — Workshop form (create / edit)

**Route:** `/staff/workshops/new` · `/staff/workshops/{workshopId}/edit` · **Nav:** Workshops › (breadcrumb) · **Actors:** staff
**Page type:** form · **Surface:** page (edit is the same form, prefilled)
**Primary action:** Save workshop · Cancel → back to S4 or S6; unsaved-changes guard
**Regions:** one column: title, description
**States:** loaded · saving (button in-flight) · server errors surfaced per field
**Data needed:** the workshop (edit) — title, description; status is read-only here (transitions are actions on S6, never an editable select)
**Serves:** U5 · **Journeys:** J3

### S6 — Workshop detail (staff)

**Route:** `/staff/workshops/{workshopId}` · **Nav:** Workshops › (breadcrumb) · **Actors:** staff
**Page type:** detail · **Surface:** page
**Primary action:** Publish workshop (draft; disabled with reason until ≥ 1 session) · secondary: Edit → S5 · Add session (drawer — short, needs the workshop context)
**Regions:** header (title, status chip) · description · sessions list (starts-at, capacity, booked)
**States:** loading skeleton · loaded · failed · sessions empty "No sessions yet. Add a session"
**Data needed:** workshop with status, description · its sessions with capacity and bookedCount
**Serves:** U5 · **Journeys:** J3

### S7 — Attendance (staff)

**Route:** `/staff/attendance` · **Nav:** Attendance · **Actors:** staff
**Page type:** list · **Surface:** page
**Primary action:** none — rows open S2 (staff view)
**Regions:** toolbar (date, default today) · session list (starts-at, workshop, booked / attended counts)
**States:** loading skeleton · loaded · failed · empty "No sessions today"
**Data needed:** sessions on the date with bookedCount and attendedCount (aggregates)
**Serves:** U6, U7 · **Journeys:** J4

## 5. Screen ↔ endpoint matrix

*(filled by the API step against `api-surface.md` §4)*

| Screen | Endpoint | Purpose on this screen |
|---|---|---|
| S1 | `GET /api/v1/sessions` | session list with `bookedCount`, `myBookingId` |
| S2 | `GET /api/v1/sessions/{sessionId}` | header, description, my booking, attendees (staff) |
| S2 | `POST /api/v1/sessions/{sessionId}/bookings` | Book seat |
| S2 | `POST /api/v1/bookings/{bookingId}/attend` | Mark attended (staff) |
| S3 | `GET /api/v1/my/bookings` | list with `cancelWindow` |
| S3 | `POST /api/v1/bookings/{bookingId}/cancel` | Cancel booking |
| S4 | `GET /api/v1/workshops` | list with `sessionCount`, `nextSessionAt` |
| S5 | `POST /api/v1/workshops` · `PUT /api/v1/workshops/{workshopId}` | Save workshop |
| S6 | `GET /api/v1/workshops/{workshopId}` · `POST …/sessions` · `POST …/publish` | detail, Add session, Publish |
| S7 | `GET /api/v1/sessions?from&to` | today's sessions with counts |

Coverage: user-facing endpoints on ≥ 1 screen 10/10 (staff `POST /bookings/{id}/cancel` reaches S2's attendee row — U7); data needs resolved 7/7 (`bookedCount`, `attendedCount`, `sessionCount`, `cancelWindow` are computed fields the API step added rather than stored).

## 6. Cross-cutting

**Density:** comfortable — weekly use, few rows per screen. · **Accelerators:** none — five destinations, under threshold; the date filter is the search. · **Notification surface:** inline + toast (Undo on booking); no notification centre — no asynchronous events reach the member in-app (emails are SendGrid's). · **First run:** member — none (the schedule *is* the first screen); staff — empty S4 invites "Create your first workshop".

**Responsiveness budget (acceptance criteria for every frontend task):**
- [ ] every press acknowledged ≤ 100 ms (pressed state; Book seat / Save disable with in-flight state)
- [ ] a region still loading at 300 ms shows a content-shaped skeleton, never a blank or page-centre spinner
- [ ] a region still loading at ~4 s says so; a timed-out region fails with retry, scoped to itself
- [ ] no layout shift on load; S2's regions load independently

## 7. Open questions

| # | Question | Owner |
|---|---|---|
| Q1 | Does un-attend exist (makes Mark attended optimistic)? | product owner, before the S2 task |
