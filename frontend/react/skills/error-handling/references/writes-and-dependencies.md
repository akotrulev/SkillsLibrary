# React — Write failures & third-party dependencies

Two situational surfaces: a **write** that fails (costing work, possibly half-applied), and a **third-party dependency** that fails (someone else's JavaScript, failing on its own schedule).

*Deep dive for [`fe-react-error-handling`](../SKILL.md). Load when the situation applies.*

---

## Mutation failures — a write fails differently from a read

A failed read costs the user information; a failed **write** costs them work, and may have half-happened. Three properties separate writes from reads: they are always user-initiated (so a failure is **always** notified — there is no "background" write the user didn't ask for), they may have succeeded on the server despite the error, and they often leave the UI showing something that never persisted.

- **The pending state is the double-submit guard.** Disable the submit control while the mutation is in flight (`isPending`) — a second click on "Pay" is not a UX wrinkle, it's a duplicate charge. Guard the Enter-key path too, not just the button, and never rely on a debounce for correctness.
- **Retryable writes carry an idempotency key.** Generate it **per user intent, not per attempt** (one key for the "create order" the user initiated; the same key on every retry of it) so a server that already processed the first attempt returns the original result instead of creating a second order. This is what makes a timed-out POST safe to retry — without it, it isn't.
- **A rolled-back optimistic update must be announced.** The optimistic row appears, the server rejects, the row silently reverts — and the user, who saw it work, walks away believing it saved. **The rollback is exactly when a notification is mandatory**, and the message says what didn't happen ("Couldn't move the ticket — it's back in Review"), not just "Error". Restore any input the user would otherwise have to retype; never clear a form on a failed submit.
- **A conflict (409/412) is not an error to retry — it's a decision to hand back.** Someone else changed the record since it was loaded. Render it as its own outcome: *"This was updated by someone else"*, with the choice — reload theirs, or overwrite with a re-issued `If-Match`. **Never silently retry a conflict**, which is precisely how the other person's edit gets erased. ([`ui-rules`](../../ui-rules/SKILL.md) mandates the concurrency token on full-replace writes; this renders what happens when it fires.)
- **422 belongs on the fields.** A validation failure maps back to the offending inputs ([`forms`](../../forms/SKILL.md) `setError`), not to a toast — a top-right notification for "email is invalid" leaves the user hunting for the field.
- **Bulk writes report per item.** "12 of 15 archived, 3 failed" with the three named and retryable — never a blanket success toast over a partial failure, and never a blanket failure that hides the 12 that worked ([`ui-rules`](../../ui-rules/SKILL.md) bulk operations).
- **An unknown outcome is its own state.** A write that timed out or lost the connection has an **indeterminate** result — say so ("We couldn't confirm whether this saved") and refetch to establish the truth, rather than asserting a failure that may have succeeded.

## Third-party dependencies — fail without taking the app with them

Your API is not the only thing that can be down. Maps, payment iframes, analytics, feature-flag providers, chat widgets, fonts and embeds all fail independently, and each ships someone else's JavaScript into your page. **The split that teams get backwards is which failures the user should hear about:**

| Dependency | If it fails | User-visible? |
|---|---|---|
| Analytics / tags / session replay | Nothing — the page is unaffected | **No.** Log it. A toast about a failed analytics beacon is noise about a problem the user cannot act on |
| Feature-flag provider | Evaluate to **default values** and render | **No** — but the defaults must be deliberate, and the failure alarmed to the team |
| Maps / charts / rich embed | That region shows its failed body | **Yes**, scoped to the region |
| Payment / signing / auth iframe | The flow cannot complete | **Yes**, prominently, with a stated fallback path |

- **Every third party gets its own boundary and its own timeout.** A widget that throws during render must degrade its region, not the route; a script that never loads must not leave a region loading forever (same budget rule as any request).
- **A feature-flag provider must never block render.** Initialize with sane defaults (bootstrapped/cached values), decide **fail-open vs fail-closed per flag** — a kill-switch flag fails *closed*, a rollout flag fails to its default variant — and never gate first paint on a network call to the flag service.
- **Load them so failure is cheap** — `next/script` with the right strategy, facades for heavy embeds (a static preview that loads the real thing on interaction), `sandbox` on untrusted iframes. [`performance`](../../performance/SKILL.md) owns the loading-strategy half; this skill owns what the UI does when the thing never arrives.
- **A third-party 401/500 is never your session's problem** (see [`session-and-deploy.md`](session-and-deploy.md)) and never your app's error boundary's problem if you can help it.
