# Golden example — the system plan's §5

The filled §5 for `product/skills/epic-map`, from a larger cut of the toy **workshop-booking** system
than the format file's §9 example: five features, with a member profile and a confirmation email
added. **Shapes and disciplines are normative; domain content is illustrative.**

Three things to read for rather than copy: the foundation feature absorbs every incidental shared
edit, so the features after it collide only where they really share a tree; F2 and F3 can be refined
beside each other but never built beside each other; and F5's edge names the event it waits on, not
just the feature.

---

````markdown
## 5. Features side by side

| Feature | Epic | Areas and trees | Depends on | Refined beside | Built beside |
|---|---|---|---|---|---|
| F1 Foundation | — | Foundation: `src/Api/*`, `contracts/*`, `web/app/layout.tsx`, `web/app/(nav)/*`, `web/lib/*`, `.github/*`, `deploy/local/*` | — | F2, F3, F4 | — |
| F2 Booking a seat | E1 | Booking: `src/Booking/*`, `tests/Booking.Tests/*`, `web/app/schedule/*`, `web/app/bookings/*` | F1 — the Member and Session entities, auth, the app shell | F3, F4, F5 | F4 |
| F3 Booking cancellation | E2 | Booking: `src/Booking/*`, `tests/Booking.Tests/*`, `web/app/bookings/*` | F1 — auth roles and the Booking entity | F2, F4, F5 | F4 |
| F4 Member profile | E3 | Membership: `src/Membership/*`, `tests/Membership.Tests/*`, `web/app/profile/*` | F1 — the Member entity and auth | F2, F3, F5 | F2, F3, F5 |
| F5 Confirmation email | E1 | Notifications: `src/Notifications/*`, `tests/Notifications.Tests/*` | F2 — the `BookingConfirmed` event it sends on | F2, F3, F4 | F4 |

F2 and F3 can be specced at the same time: §3 fixed the Booking entity and the roles both bind to,
so neither interview waits on the other. They cannot be built at the same time: both land in
`src/Booking/*` and `web/app/bookings/*`. F5 can be specced beside F2 because §3's conventions name the
event shape, but it is built only after F2 raises the event.

The critical path is F1 → F2 → F5. The edge worth challenging is F5's wait on F2: if the email were
sent from a scheduled job reading bookings instead of on the event, F5 would depend on F1 only.
````

**Overlaps resolved, and where the fix went.** The collisions Step 5 found, each fixed before the
table above was written:

| Features | Shared file | Resolution |
|---|---|---|
| F2, F3, F4 | `src/Api/Program.cs`: each module registers its routes | Moved into F1: the module seam is a foundation task, and each module registers itself |
| F2, F3, F4 | `web/app/(nav)/nav-items.ts`: each area adds a nav entry | Moved into F1: the full nav map ships with the app shell, every entry present from the start |
| F2, F4 | `src/Api/Migrations/*`: both add tables | Each module keeps its migrations in its own tree (`src/Booking/Migrations/*`, `src/Membership/Migrations/*`), one schema per module as §3's modules say, so no two features write one migrations folder |
| F2, F5 | `src/Booking/BookingService.cs`: the email was first drafted inside the booking service | Not an overlap: F5 subscribes to `BookingConfirmed`, so its files are `src/Notifications/*` only, and the edge is a dependency |

This table is the working the skill does; it is not part of §5. A collision that changes §3 (the
module seam, the nav map, where migrations live) is recorded in the system plan's `## Decisions`.
