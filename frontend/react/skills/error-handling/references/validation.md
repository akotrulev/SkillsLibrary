# Error-handling validation

*Deep dive for [`fe-react:error-handling`](../SKILL.md). Read it when verifying a change to error handling: writing the tests, or a review pass.*

Each line is one scenario and the one state a test observes after it. Done when every line holds.

- Throw in a feature component → its boundary's `Orders.Error` renders friendly text with a `Ref:` id, and the page around it stays interactive.
- Make a fetch 500 → `Orders.Error` shows inside the rows area, not a blank grid; `Orders.Error.Retry` recovers on the next success.
- Make a fetch 503 once → the retry absorbs it, and `Orders.Error` never appears.
- With that 500 still failing → `Orders.Search` and `Orders.Filters` stay mounted, enabled and holding the typed text; only the rows area carries the error.
- During that failure → exactly one `Notifications.Error` (with `Notifications.Error.CorrelationId`) is present after 60s and leaves only through `Notifications.Error.Close`.
- Fail the same call three times → `Notifications.Region` holds one `Notifications.Error`, not three.
- Return a drifted body (a renamed field, an object where an array was expected) → `Orders.Error` shows, not `Orders.Empty`, and one `Notifications.Error` appears.
- Delay the response past the budget → `Orders.Error` shows the timeout message at the deadline and `Orders.Loading` does not persist beyond it; the "still loading" text appeared first.
- Navigate away mid-request → no `Orders.Error` and no `Notifications.Error` appear.
- Load, then fail the refetch → `Orders.Stale` shows an "as of" time over the still-rendered rows, `Orders.Error` is absent, and one `Notifications.Error` appears.
- Fail a refetch on data that is dangerous when stale → the action that depends on it is disabled, with the reason in its tooltip.
- Change a filter or page → rows stay on screen until the new ones arrive, and the new key's first load shows `Orders.Loading`, not `Orders.Stale`.
- Fail two of three independent tiles → two tiles show their `Error` body and the third shows its data.
- Fail a mutation with an optimistic update → the row reverts, a `Notifications.Error` names what did not happen, and the form still holds the typed values.
- Return 503 from every endpoint → `Notifications.Region` holds at most 3 entries plus one "+N more", auto-retry stops after *k* attempts, and each region offers its Retry button.
- Leave a tab backgrounded past `staleTime` and return → a refetch request fires and the rows show the new data.
- Empty each way (no records, no filter, filtered out) → three distinct messages, each with its action.
- Force a client error → the report reaches the server log or Sentry with the correlation id; force a hydration mismatch → `onRecoverableError` reports it.
- Block the third-party hosts at the network level → the app renders, flags take their defaults, the map region shows its failed body, and no analytics `Notifications.Error` appears.
- Simulate a deploy across an open tab → one reload lands on the new build with no loop, and a tab with unsaved work shows the prompt instead.
- Expire the session mid-form, then save → one refresh fires across all in-flight calls, the save replays, and the typed values are still there; make the refresh fail → the re-auth appears in place; a 403 shows permission-denied and leaves the session untouched.
- Drop the network → the offline banner appears and the live region shows "reconnecting"; restore → both clear.
- Delete a record in another tab, then act on its detail page → "no longer exists" with a way out, and the list no longer shows the row.
