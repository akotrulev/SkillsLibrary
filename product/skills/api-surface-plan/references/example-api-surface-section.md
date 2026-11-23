# Golden example — a spec's `## API surface`

The filled `## API surface` section for `product/skills/api-surface-plan`, from the toy spec the four
design skills share: `docs/specs/006-booking-cancellation-design.md`, feature F3 *Booking
cancellation* of the system plan `docs/plans/004-workshop-booking-system.md`. Its `## Data model` is
[`example-data-model-section.md`](../../data-model-plan/references/example-data-model-section.md), which
also lists the acceptance criteria AC1–AC6 cited below. **The shapes and disciplines are normative;
the domain content is illustrative.**

F2's spec, `docs/specs/007-booking-a-seat-design.md`, already holds the API-wide contract, the
`SessionSummary` schema, the booking endpoints and the project's copy of the validation catalog, so
this section shows what "referenced, never redefined" looks like: one new endpoint, one delta block.

---

````markdown
## API surface

### Builds on
| What | Defined in | This feature |
|---|---|---|
| Error envelope, UUID v7 ids, cursor pagination (`?cursor=&limit=`, at most 100) | §3, cross-cutting conventions | inherits |
| Base path `/api/v1`, Bearer JWT from Auth0, roles `member` / `staff` from the namespaced roles claim | §3 Auth; 007 `### API-wide contract` | inherits |
| `SessionSummary` (`id`, `workshopTitle`, `startsAt`, `capacity`, `seatsLeft`, `status`) | 007 `### Shared schemas` | returns it from the cancel endpoint |
| `GET /api/v1/my/bookings` — My bookings | 007 | **changed**: three response fields |
| `GET /api/v1/sessions/{sessionId}/bookings` — Session attendees (staff) | 007 | unchanged; staff cancel from its rows, which carry `bookingId` |
| `docs/specs/validation-catalog.md` and its open choices (unknown fields rejected with 400; field validation 400; another member's booking is 404) | 007 `### Validation & error contract` | inherits |

### API-wide contract
Per §3 and 007. No decision left open, no deviation. Idempotency: none, as in 007; a repeated cancel
is a 409 `invalid-state`, never a second cancellation.

### Endpoint map
| Service | Resource | Method | Path | Name | Description | Auth | Idempotent | Success |
|---|---|---|---|---|---|---|---|---|
| Booking | Bookings | POST | `/api/v1/bookings/{bookingId}/cancel` | Cancel booking | `confirmed → cancelled`; frees the seat; sets `lateCancel` per the 24 h rule | `member` (own booking) · `staff` (any booking) | no | 200 |
| Booking | Bookings | GET | `/api/v1/my/bookings` | My bookings (changed) | 007's list, now showing cancelled bookings and the free-cancellation deadline | `member` | yes | 200 |

The cancellation is an action on a sub-path, never `PATCH {status}`. Consumers: the SPA's
cancellation dialog (member and staff) and 007's My bookings screen.

### Shared schemas
None new. `SessionSummary` is 007's.

### Validation & error contract
**Standard set:** `docs/specs/validation-catalog.md` (committed with 007), applied to every endpoint below.
**This feature's instantiation:**
- Referential integrity, `bookingId`: exists → visible (a member sees only their own; staff see all) → in a valid state. A member naming another member's booking gets **404** `not-found`, per 007's V5.3 choice (AC4).
- State transitions (from `## Data model`, state diagram): every undrawn arrow is a 409 `invalid-state` — cancel a `cancelled` booking, cancel an `attended` one (AC5).
- Business invariant (V6.7): cancel after the session's `startsAt` → 409 `session-started` (AC5).
- Uniqueness (from `## Data model`): the one-seat rule now covers live bookings only; no new duplicate rule.
- Rate limiting: unchanged; none in v1.

### Endpoints

#### POST `/api/v1/bookings/{bookingId}/cancel` — Cancel booking
**Purpose:** cancels one confirmed booking before its session starts and gives the seat back at once.
**Auth:** `member` for a booking they hold; `staff` for any booking. The canceller is the caller; no `memberId` in the body.
**Acceptance:** AC1, AC2, AC3, AC4, AC5

**Request body** — optional.
| Field | Type | Required | Constraints | Notes |
|---|---|---|---|---|
| `reason` | string | no | 1–200 chars, trimmed; accepted from `staff` only | → `bookings.cancel_reason`; shown in the member's email (AC3) |

**Response 200**
| Field | Type | Notes |
|---|---|---|
| `id` | uuid | |
| `status` | enum | always `cancelled` here |
| `lateCancel` | bool | server-computed: `true` only when a member cancels less than 24 h before `startsAt` (AC2); always `false` for staff (AC3) |
| `cancelledAt` | datetime | server-computed |
| `session` | SessionSummary | 007's schema; `seatsLeft` already includes the freed seat (AC1) |

**Errors:** standard set, plus —
| Status | Condition | `type` slug |
|---|---|---|
| 409 | the booking is `cancelled` or `attended` | `invalid-state` |
| 409 | the session has started | `session-started` |
| 403 | a `member` sends `reason` | `forbidden` (V4.3: the field is staff-only) |

The status change and the seat counter's decrement are one transaction (`## Data model`). Two cancels of
one booking racing each other: the conditional update lets one win; the other gets 409 `invalid-state`.
The email is sent after the commit (`## Integrations`); its failure never fails this request (AC6).

#### GET `/api/v1/my/bookings` — My bookings — changed; defined in 007
Only the delta. The list item gains:
| Field | Type | Notes |
|---|---|---|
| `status` | enum | now also `cancelled` (AC1) |
| `lateCancel` | bool | as above |
| `freeCancelUntil` | datetime | server-computed: the session's `startsAt` minus 24 h; the dialog's late warning reads it (AC2) |

Default sort, filters and paging unchanged. No new error.

### Pagination, filtering & sorting
Per 007. The cancel endpoint returns no list.

### Versioning & deprecation
`/v1`. The `GET /my/bookings` change is additive: a client that ignores the new fields keeps working.

### Outbound webhooks
None.

### Consumers
| Consumer | Resources used | Notes |
|---|---|---|
| SPA, member screens | `POST /bookings/{id}/cancel`, `GET /my/bookings` | the dialog and 007's My bookings |
| SPA, staff screens | `POST /bookings/{id}/cancel` | from 007's session attendee list |

### Open questions
| # | Question | Blocks | Owner |
|---|---|---|---|
| — | none: whether members may give a reason is `## Data model` open question 1, and only the 403 row above would change | | |
````

The screen ↔ endpoint matrix this section fills lives in `## Experience`:
[`example-experience-section.md`](../../experience-plan/references/example-experience-section.md).
