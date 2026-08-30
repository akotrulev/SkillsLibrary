# Golden example — `epic-map.md`

The filled example for `be-shared-epic-map`, from the **workshop-booking** toy initiative shared by all the planner examples. **Shapes and disciplines are normative; domain content is illustrative.**

Two things to read for rather than copy: `E0` is planner-created and carries no stories, and `E1` splits into two lanes because two of its stories share no files — the cheapest parallelism in the plan, and invisible if nobody looks for it.

---

# Workshop Booking — Epic Map

**Date:** 2026-08-02 · **Written by:** `be-shared-epic-map`
**Pack:** `./epics.md` · `./stories.md` · `./blueprint.md` · `./delivery-plan.md`

> `E0` is planner-created: it carries no stories and does not appear in `epics.md`.
> It is the contract-and-foundations lane every other epic waits on. A cross-artifact
> check looking for a backlog entry for `E0` is checking the wrong thing.

## 1. Epics and where they land

| Epic | Stories | Lands in | Agents | Depends on |
|---|---|---|---|---|
| `E0` Contract + foundations | — *(planner-created, no stories)* | `WorkshopBooking.sln`, `src/Api/Program.cs`, `src/Api/Configuration/*`, `src/Api/Migrations/*`, `src/Shared/*`, `.github/workflows/ci.yml`, `web/app/layout.tsx`, `web/app/(nav)/*`, `web/lib/api-client.ts` | `be-dotnet`, `fe-react`, `human` | — |
| `E1` Timetable | US1–US5 | `src/Scheduling/*`, `tests/Scheduling.Tests/*`, `web/app/timetable/*`, `web/app/admin/workshops/*` | `be-dotnet`, `fe-react` | `E0` |
| `E2` Booking | US6–US10 | `src/Booking/*`, `tests/Booking.Tests/*`, `web/app/bookings/*` | `be-dotnet`, `fe-react` | `E0`, `E1` — it books against a session `E1` publishes, and its screens link into `E1`'s timetable detail |
| `E3` Member profile | US11–US13 | `src/Membership/*`, `tests/Membership.Tests/*`, `web/app/profile/*` | `be-dotnet`, `fe-react` | `E0` |
| `E4` Confirmation email | US14 | `src/Notifications/*`, `tests/Notifications.Tests/*` | `be-dotnet` | `E0`, `E2` — it sends on the `BookingConfirmed` event `E2` raises |

`E0` is not empty here: the repo is greenfield, so every line of it is real work. Its `human` row is
the two provisioning tasks from `integrations.md` §5 (the Auth0 tenant, the SendGrid sender domain) —
they are gates in wave 1, not lanes anyone schedules.

## 2. Lanes

Story-altitude lanes, with the stack splits `delivery-plan.md` derived from them recorded back here
per the one-stack-per-task rule — an epic-map lane spanning a backend tree and a web tree becomes two
streams in the delivery plan, and this document says so rather than letting the two disagree.

| Lane | Epic | Stories | Stack split in `delivery-plan.md` | Internally sequential because |
|---|---|---|---|---|
| `foundations` | `E0` | — | `foundations-api` (`be`) · `schema` (`be`) · `foundations-ui` (`fe`) | The API side edits the solution root or `Program.cs`; the web side edits the layout and route tree. `schema` splits out because `src/Api/Migrations/*` is disjoint from both and is globally ordered by definition |
| `timetable-api` | `E1` | US1–US3 | — (already one stack) | `src/Scheduling/*` throughout: the entities, the service, the endpoints and their tests are one tree built in order |
| `timetable-ui` | `E1` | US4–US5 | — (already one stack) | `web/app/timetable/*` and `web/app/admin/workshops/*` share the session-card component. Waits on `timetable-api` — the screens call the endpoints it delivers |
| `booking` | `E2` | US6–US10 | `booking-api` (`be`) · `booking-ui` (`fe`) | The cancellation rules and the my-bookings screen both read the booking aggregate, so each side is one tree; the screens wait on the endpoints |
| `profile` | `E3` | US11–US13 | `profile-api` (`be`) · `profile-ui` (`fe`) | `src/Membership/*` then `web/app/profile/*`, one tree per side |
| `email` | `E4` | US14 | — (already one stack) | One story, one tree — a lane of one task |

`E1` is two lanes here, not one, and it is the cheapest parallelism in the plan. US1–US3 land entirely
in `src/Scheduling/*` and US4–US5 entirely in `web/app/**`; the file sets are disjoint, so the only
thing sequencing them is `timetable-ui`'s dependency on the endpoints. That is an edge, not a lane
merge — and it is why `timetable-api` can run alongside `profile-api` in wave 2 while `timetable-ui`
waits for wave 3.

`E2`, `E3` and `foundations` arrive at the same shape one step later, when the delivery plan applies
the one-stack rule to their tasks. The waves below are written in the split form, because that is what
an operator actually opens.

## 3. Waves

```
Wave 1   foundations-api ∥ schema ∥ foundations-ui   (E0)    3 lanes  ██ must land first
Wave 2   timetable-api (E1) ∥ profile-api (E3)               2 lanes
Wave 3   timetable-ui (E1) ∥ booking-api (E2) ∥ profile-ui (E3)
                                                             3 lanes
Wave 4   booking-ui (E2) ∥ email (E4)                        2 lanes
```

Wave 1's three lanes are disjoint: the solution root and `Program.cs`, against `src/Api/Migrations/*`,
against `web/app/**`. `foundations-ui`'s typed API client is written against `api-surface.md`, not
against the implemented endpoints, so it does not wait on them — which is the whole reason the
contracts are `E0` work.

Wave 3's three lanes are disjoint for the same reason — `web/app/timetable/*` + `web/app/admin/*`,
against `src/Booking/*`, against `web/app/profile/*`. Wave 4's two are `web/app/bookings/*` against
`src/Notifications/*`, and `email` waits on the `BookingConfirmed` event `booking-api` raises in wave 3,
not on the screens.

`E2` spans two waves because its API half depends only on `E0`'s schema and contracts while its screens
additionally depend on `E1`'s timetable detail page — the Book action lives there. Splitting it at the
wave boundary is what lets the booking API be built while the timetable UI is still in flight;
`delivery-plan.md`'s task order carries the same split.

**No capability is usable until both its lanes have landed.** `E1` is not usable when `timetable-api`
finishes in wave 2 — it is usable when `timetable-ui` finishes in wave 3, and the delivery plan puts
the behavioural deliverable on that task. That is the price of one agent per lane, and it is stated
here rather than discovered at a demo.

## 4. Critical path

**Four waves:** `E0` → `E1` API → `E1` UI + `E2` API + `E3` UI → `E2` screens + `E4`. Nothing in the
dependency graph makes it shorter than four.

The one edge worth challenging is **`E2`'s screens depending on `E1`'s timetable detail page** — they
need somewhere to put the Book button. If the booking flow were reachable from the member's own
dashboard instead, `E2` would collapse into wave 3 entirely and the plan would be three waves.
That is a product decision, not an engineering one; it is open question Q1 below.

The `E0` → everything edge is not worth challenging. It is the contract every other lane binds to,
and shortening it means building against contracts that do not exist yet.

## 5. Overlaps resolved

| Epics | Shared file | Resolution |
|---|---|---|
| `E1`, `E2`, `E3` | `src/Api/Program.cs` — each module registers its own routes | Pulled into `E0`: the `IEndpointModule` seam is an `E0` task, and each module self-registers. Without it, all three epics are one lane |
| `E1`, `E2`, `E3` | `web/lib/api-client.ts` — every screen imports its typed calls | Pulled into `E0`: the whole client is generated in `foundations-ui` from `api-surface.md` §5, before any screen exists. A screen task adding its own calls to it would collide with every other screen task |
| `E1`, `E2`, `E3` | `web/app/(nav)/nav-items.ts` — each area adds a nav entry | Pulled into `E0`: the full nav map ships in the app-shell task, with every entry present from the start. Areas add screens behind entries that already exist |
| `E2`, `E4` | `src/Booking/BookingService.cs` — the email handler was first drafted inside the booking service | Not an overlap: `E4` subscribes to the `BookingConfirmed` event rather than being called from the service. `E4`'s files are `src/Notifications/*` only, and the edge is a dependency |
| `E1`, `E2` | `src/Api/Migrations/*` — both add tables | Pulled into `E0`: the whole migration sequence (001–003) lands in the foundations lane, in `data-model.md`'s stated order. Migrations are globally ordered by definition and never split across concurrent lanes |

## 6. Open questions

| # | Question | Blocks | Owner |
|---|---|---|---|
| Q1 | Is the Book action reachable from the member dashboard, or only from a timetable session detail page? Dashboard-only would collapse `E2` into wave 3 and make the plan three waves | `E2` screens — lane `booking`, wave 4 | Studio owner |
