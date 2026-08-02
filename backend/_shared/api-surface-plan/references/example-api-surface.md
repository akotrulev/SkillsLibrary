# Golden example — `api-surface.md`

The filled example for `be-shared-api-surface-plan`, from the **workshop-booking** toy initiative shared by all five planner examples. **Shapes and disciplines are normative; domain content is illustrative.** A real artifact writes a contract block for *every* endpoint — this example writes one in full (the booking-creation endpoint, where the interesting rules live) and abbreviates the rest, saying so.

---

# Workshop Booking — API Surface Plan

**Date:** 2026-08-02 · **Written by:** `be-shared-api-surface-plan`
**Blueprint:** `./blueprint.md` · **Data model:** `./data-model.md`

## 1. API-wide contract

| Decision | Choice | Note |
|---|---|---|
| Base path & versioning | `/api/v1/...` | URL versioning |
| Auth scheme | Bearer JWT (Auth0); permissions in `permissions[]`, no tenant claim (single tenant) | |
| Error body | RFC 9457 `application/problem+json` | Per the catalog |
| List envelope | `{ items, page, pageSize, total }` | Small tables; exact totals are cheap |
| Casing | `camelCase` | |
| Dates | ISO 8601 UTC `Z`; session start also returned as studio-local `startsAtLocal` | One studio, one zone |
| Idempotency | None — no money moves; a duplicate book attempt is caught by the one-seat rule (409) | Deliberate omission, stated |
| Concurrency | `ETag`/`If-Match` on `PUT /sessions/{id}` only | Only `sessions` carries a version column |
| Correlation | `traceparent` accepted and propagated | |

## 2. Endpoint map

| Service | Resource | Method | Path | Name | Description | Auth | Idempotent | Success |
|---|---|---|---|---|---|---|---|---|
| booking-api | Workshops | GET | `/api/v1/workshops` | List workshops | Published only for members; all for staff | any authenticated | yes | 200 |
| booking-api | Workshops | POST | `/api/v1/workshops` | Create workshop | Creates a `draft` workshop | `workshops:manage` | no | 201 |
| booking-api | Workshops | POST | `/api/v1/workshops/{workshopId}/publish` | Publish workshop | `draft → published` | `workshops:manage` | no | 200 |
| booking-api | Sessions | POST | `/api/v1/workshops/{workshopId}/sessions` | Schedule session | New `scheduled` session with capacity | `workshops:manage` | no | 201 |
| booking-api | Sessions | GET | `/api/v1/sessions` | List sessions | Upcoming published sessions; default sort `startsAt` asc, tie-break `id` | any authenticated | yes | 200 |
| booking-api | Sessions | PUT | `/api/v1/sessions/{sessionId}` | Edit session | Capacity/time edit; `If-Match` required | `workshops:manage` | yes | 200 |
| booking-api | Bookings | POST | `/api/v1/sessions/{sessionId}/bookings` | Book a seat | Confirmed booking for the caller | `bookings:own` | no | 201 |
| booking-api | Bookings | GET | `/api/v1/my/bookings` | My bookings | The caller's bookings, newest first | `bookings:own` | yes | 200 |
| booking-api | Bookings | POST | `/api/v1/bookings/{bookingId}/cancel` | Cancel booking | `confirmed → cancelled`; sets `lateCancel` per policy | `bookings:own` (own) / `workshops:manage` (any) | no | 200 |
| booking-api | Bookings | POST | `/api/v1/bookings/{bookingId}/attend` | Mark attended | `confirmed → attended` | `workshops:manage` | no | 200 |

State transitions are actions on sub-paths (`/publish`, `/cancel`, `/attend`) — never `PATCH {status}`. Every endpoint has a consumer: the member SPA (list/book/cancel) or the staff SPA (the rest).

## 3. Shared schemas

`PagedResult<T>` · `ProblemDetails` (per catalog §0) · `SessionSummary` (`id`, `workshopId`, `workshopTitle`, `startsAt`, `startsAtLocal`, `durationMin`, `capacity`, `seatsLeft`, `status`) — used by both session and booking responses, defined once.

## 4. Validation & error contract

**Standard set:** `references/validation-catalog.md`, applied API-wide. **This API's instantiation:**

- Unknown fields (V1.5/V1.7): **reject, 400** — two first-party SPAs, client typos should surface
- Field validation status (§2): **400** API-wide
- Permission model: Auth0 `permissions[]`; two values: `bookings:own`, `workshops:manage`
- Not-found vs forbidden (V5.3): **404** for another member's booking — a booking id is not the caller's to confirm exists
- Referential integrity: exists → visible → valid-state, on every id (`workshopId`, `sessionId`, `bookingId`)
- State transitions (from `data-model.md` §5): every undrawn arrow is a 409 `invalid-state` — cancel-after-attend, attend-after-cancel, re-cancel, publish-from-archived
- Uniqueness (from `data-model.md`): live seat per (session, member) → 409 `already-booked`; (workshop, startsAt) → 409 `duplicate-session`
- Rate limiting: none in v1 — internal member base `⚠️ Assumption: acceptable at 500 members`

## 5. Endpoints

*A real artifact writes every block; this example shows the load-bearing one.*

#### POST `/api/v1/sessions/{sessionId}/bookings` — Book a seat
**Purpose:** books one seat on a published, future session for the calling member.
**Auth:** `bookings:own`; the member is the caller — a `memberId` in the body would be ignored per the server-computed rule, so the body carries none.

**Request body** — none. The path and the token carry everything; an empty body is a valid design outcome, stated rather than padded.

**Response 201**
| Field | Type | Notes |
|---|---|---|
| `id` | uuid | |
| `session` | SessionSummary | shared schema; `seatsLeft` reflects this booking |
| `status` | enum | always `confirmed` here |
| `createdAt` | datetime | |

`Location: /api/v1/bookings/{id}`

**Errors:** standard set, plus —
| Status | Condition | `type` slug |
|---|---|---|
| 409 | session full | `session-full` |
| 409 | caller already holds a live booking on this session | `already-booked` |
| 409 | session not `scheduled`, or already started | `invalid-state` |

The capacity check is the DB-level guard from `data-model.md` §3 — the 409 comes from the constraint/lock, not from a count the request read earlier.

#### The remaining nine endpoints — abbreviated in this example
Each gets the same block: purpose, auth, request/response field tables, "standard set, plus —". Notable deltas: `PUT /sessions/{sessionId}` adds 412 `stale-resource`/428 (V6.2/V6.3) and 409 `capacity-below-bookings` (cannot set capacity under confirmed count); `/cancel` adds 409 `invalid-state` and computes `lateCancel` server-side per the blueprint's decision table.

## 6. Pagination, filtering & sorting
`page` (≥1, default 1) · `pageSize` (default 20, max 100, above-max → 400 — reject, matching V1.5's choice) · sort allowlisted per resource, always tie-broken on `id`. `GET /sessions` filters: `from`/`to` (date range, `from <= to` per V2.8), `workshopId`.

## 7. Versioning & deprecation
`/v1` until a breaking change; none anticipated in this initiative. `Deprecation`/`Sunset` headers when it comes.

## 8. Outbound webhooks
None.

## 9. Consumers
| Consumer | Resources used | Notes |
|---|---|---|
| Member SPA | Workshops (read), Sessions (read), Bookings | |
| Staff SPA | All | |

## 10. Open questions
| # | Question | Blocks | Owner |
|---|---|---|---|
| — | none — the booking-quantity question was settled at blueprint (Q1: one seat) | | |
