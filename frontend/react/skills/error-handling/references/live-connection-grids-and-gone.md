# Live connections, grids and deleted records

*Deep dive for [`fe-react:error-handling`](../SKILL.md). Read the section whose situation the task contains.*

**Contents:**

- Live connection and offline: a WebSocket or SSE feed, or a task that must work offline
- Inline error region inside grids: a data grid in the task
- Gone, not broken: a detail page, or a region bound to one record

## Live connection and offline: a WebSocket or SSE feed, or a task that must work offline

React has **no persistent server circuit** (unlike Blazor), so there is no circuit-reconnect modal. The analogous surfaces are the live-data socket and network offline.

- **Live WS/SSE drop:** [`realtime`](../../realtime/SKILL.md) owns the socket, its backoff reconnection and a connection status (`connecting`/`open`/`reconnecting`/`closed`). This skill makes that status **legible and consistent**: a "reconnecting…" affordance on the live region, and stale live data dimmed and marked stale, never shown as current while the socket is down. One disconnect event, two layers.
- **Offline:** gate optimistic actions on `navigator.onLine` plus the `online`/`offline` events, show an offline banner, and queue or block writes rather than failing them silently. TanStack Query pauses and resumes queries and mutations across offline→online, so lean on it rather than hand-rolling.

## Inline error region inside grids: a data grid in the task

A grid load failure renders its error **in the grid area**, never only as a toast: an empty grid is indistinguishable from "no rows". Bind the loading and failed states on the **shared table/grid component** ([`ui-rules`](../../ui-rules/SKILL.md) renderer unification) so every grid gets them from one change, and never reimplement them per page.

## Gone, not broken: a detail page, or a region bound to one record

A detail page whose record was deleted, or whose id was pasted wrong, comes back **404**. Rendering that as "something went wrong" sends the user retrying a request that will never work, so treat it as its own outcome: *"This order no longer exists"*, with a way out (back to the list, or the search that found it).

- **Route level:** `not-found.tsx` plus `notFound()` ([`routing`](../../routing/SKILL.md)).
- **Below the route:** a region that lost its record renders the gone state in place, and any action bound to it is removed rather than left to fail.
- **The paired defect** is a list that still shows the deleted row until the next refetch: invalidate the list on delete.
