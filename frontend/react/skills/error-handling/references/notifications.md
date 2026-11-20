# The persistent error notification

*Deep dive for [`fe-react:error-handling`](../SKILL.md). Read it when wiring the notification provider, raising a notification from a new failure path, or when several regions can fail at once.*

**Contents:**

- What this skill adds to the contract
- Per component library
- Where it is raised
- Volume control

## What this skill adds to the contract

Position, dismissal and content are `react.md`'s rule. Success and info notifications may auto-dismiss in ~4–6s; an error never does.

| Property | Value |
|---|---|
| Semantics | container `aria-live="polite"` + `role="status"` for info, `role="alert"` for errors; the close button (`aria-label="Close"`) is keyboard-reachable and focus is not stolen from the user's current field |
| Dedupe | key by `correlationId ?? (code + region)`, so a retried-then-failed call updates the existing entry (with a count) instead of stacking five copies |
| Scope | one provider mounted **once** at the root client island; features call a hook (`useNotify().error(appError)`) and never mount their own portal |

Stable test ids ([`test-ids`](../../test-ids/SKILL.md)): `Notifications.Region`, `Notifications.Error`, `Notifications.Error.Close`, `Notifications.Error.CorrelationId`.

## Per component library

[`component-library`](../../component-library/SKILL.md) owns mounting the provider. Each call below is persistent, closable and top-right.

| Library | Persistent-error call |
|---|---|
| MUI (notistack) | `enqueueSnackbar(msg, { variant: 'error', persist: true, anchorOrigin: { vertical: 'top', horizontal: 'right' }, action: closeButton })` |
| Mantine | `notifications.show({ color: 'red', autoClose: false, withCloseButton: true })` + `<Notifications position="top-right" />` |
| Chakra v3 | `toaster.error({ duration: null, meta: { closable: true } })`, toaster created with `placement: 'top-end'` |
| **shadcn (sonner)**, the default lane | `toast.error(msg, { duration: Infinity, closeButton: true })` + `<Toaster position="top-right" />` |
| none | a small `NotificationProvider` context + a fixed-position `<ul aria-live="polite">` portal, with the same contract |

## Where it is raised

One place per failure path: the global TanStack `QueryCache.onError` / `MutationCache.onError` handler (one change covers every query), a boundary's `onError`, or the Server-Action result handler. Raising it also at the call site double-fires.

## Volume control

An outage must not become a wall of toasts. Dedupe handles the *same* error repeating, not a backend outage failing six regions at once with six correlation ids. Three defenses, in order:

1. **Cap the stack.** Show at most ~3 notifications and collapse the rest into one "+4 more issues" entry that expands, because a stack taller than the viewport hides its own close buttons.
2. **Roll up by cause, not by call.** Six regions failing on one 503 is **one** message ("Some data couldn't be loaded — the service is unavailable"), grouped on status/code plus a short time window. The per-region inline states already say *which* regions.
3. **Let the retry circuit quiet it.** Once a region stops auto-retrying (the *k*-consecutive-failures rule under Fetch resilience in `SKILL.md`), it stops re-notifying: one persistent entry with a count, not one per attempt.
