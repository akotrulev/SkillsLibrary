# React — Session expiry & deploy version skew

The two failures where **the app itself changed underneath the user** — their session ended, or their tab outlived its build. Both are recoverable in place, and both destroy unsaved work when handled with a redirect or a reload reflex.

*Deep dive for [`fe-react-error-handling`](../SKILL.md). Load when the situation applies.*

---

## Session expiry mid-session — recover in place, never discard work

A 401 arriving while someone is *working* is a resilience problem, not an auth problem. `auth/auth0-react` owns the token lifecycle (silent refresh, rotation, reuse detection) and hands over exactly here: **what the UI does when a call comes back 401.** The default implementation — an interceptor that calls `loginWithRedirect()` — unmounts the app and **destroys a half-filled form**. That is the same defect as the early-return in the failure-scoping section, one level up: a failure taking away work the user could still have saved.

**The ladder, in order. Stop at the first rung that works:**

```
401 → 1. Silent refresh (single-flight)         → success → 2. Replay the original request once → done, user saw nothing
                                                → failure → 3. Re-authenticate IN PLACE (modal/overlay) → replay → done
                                                          → declined/failed → 4. Failed state in the scoped region + persistent notification
                                                                                (redirect to login only from a surface with nothing to lose)
```

1. **Silent refresh is single-flight.** Ten queries failing 401 at once must trigger **one** refresh; the rest queue on that promise and replay after it. Ten parallel refreshes is a token-rotation stampede that revokes the family and logs everyone out — with reuse detection on (which `auth/auth0-react` mandates), it's worse than the original error.
2. **Replay exactly once, and mark the retry.** A replayed request that 401s again must **not** re-enter the ladder — that's the infinite refresh→401→refresh loop that hammers the IdP. One flag on the request; second 401 goes straight to rung 3.
3. **Re-authenticate in place.** A modal/overlay login (or a popup — `loginWithPopup`) keeps the route mounted, so the form, the filters, the scroll position, and the unsaved text all survive. On success, replay the pending request(s) and dismiss. **This is the rung teams skip**, and it is the one that saves the work.
4. **Redirect is the last resort, and only from a clean surface.** Read the dirty state before navigating: any open form with `formState.isDirty`, any pending mutation, any editor with unsaved content ⇒ **do not redirect**. Show the re-auth affordance instead. For long-lived forms, also persist a local draft as belt-and-braces (through the guarded storage wrapper — see the storage rule, and note it may be unavailable).

**Related rules**

- **403 is not 401.** A permission failure means *this user may not do this* — it renders a permission-denied body in the scoped region, offers **no retry**, and never triggers a refresh or a re-auth. Conflating them produces the classic "logged out for clicking an admin button" bug. (Some backends answer 404 instead of 403 to avoid leaking existence — treat it as denied, not as a broken link, when the route is one the user reached from an authorized list.)
- **Only the app's own API triggers the ladder.** A 401 from a third-party or unrelated host must never log the user out of your app.
- **Warn before the deadline, not after.** Idle/absolute session limits should surface a countdown ("signing you out in 2 minutes — stay signed in?") *before* expiry, because the alternative is a user typing for ten minutes into a session that is already dead. Note the trap: **idle timers keyed to HTTP activity treat a user typing a long form as idle** — key the warning to the session's actual expiry, and let a keystroke count as activity where the backend allows a keepalive.
- **Return the user to where they were.** If a redirect does happen, `returnTo` the exact route (including query/filters), not the dashboard.
- **RSC / App Router:** a middleware redirect is right for a *document* navigation, and wrong for a `fetch` — a 302 to the IdP arrives at client code as an opaque failure or a CORS error, not a login. Route handlers and Server Actions return **401 JSON** to XHR/Action callers and let the client run the ladder; only full-page navigations redirect.
- **Multi-tab:** a refresh in one tab should not leave a sibling tab holding a dead token, and a logout in one tab should not leave another rendering as signed-in — broadcast the transition (`BroadcastChannel`/`storage` event) so the other tabs re-render or show the re-auth affordance.

## Deploy version skew — the tab that outlived its build

Every deploy creates a window where **the app in the browser is older than the app on the server**. A tab left open across a deploy still holds the previous build's chunk map; the next lazy-loaded route requests a hashed chunk the deploy deleted, and the user gets a `ChunkLoadError` — surfacing as a blank route or the nearest error boundary, on a click that has nothing wrong with it. It is invisible in development (nothing is ever deleted) and reliable in production, which is why it usually ships.

Three variants, same root cause:

| Symptom | Cause |
|---|---|
| `ChunkLoadError: Loading chunk N failed` / `Failed to fetch dynamically imported module` | A lazy route/component chunk was removed by the new deploy |
| RSC navigation fails or renders nothing **[App]** | The client requests a flight/RSC payload for a `BUILD_ID` that no longer exists |
| Old HTML with new chunks (or the reverse) | A CDN/proxy caching `index.html` or the document out of step with the assets |

**The rules:**

- **Let the framework detect it.** Next 14.1.4+ supports **`deploymentId`** in `next.config` — it stamps requests with the build and lets the server answer a mismatch, so the client can hard-reload onto the current build instead of failing. Set it from the CI build/commit id. (Vercel's Skew Protection does this for you; self-hosted deployments must wire it themselves.)
- **Catch the chunk error globally and recover once.** A boundary that only *displays* a chunk error is a dead end — the recovery is a reload onto the new build. Handle `ChunkLoadError` / dynamic-import failures in the root boundary and the `window.onerror`/`onunhandledrejection` handler, and reload — **guarded by a `sessionStorage` flag so it happens at most once**. An unguarded auto-reload against a genuinely broken build is an infinite reload loop, which is worse than the error it replaces. If the flag says we already reloaded, show the failed state and stop.
- **Offer the reload, don't always force it.** A skew detected while the user has unsaved work follows the same rule as session expiry: **prompt** via the persistent notification ("A new version is available — Reload") rather than reloading under their hands. Force-reload only when the current view is already broken.
- **Keep it consistent with the service worker.** A PWA has this same conversation through the waiting-worker prompt ([`installable-offline-app`](../../installable-offline-app/SKILL.md) owns that lifecycle). **Wire one "new version available" affordance, not two** — the SW prompt and the skew prompt are the same message to the user. Note the non-PWA case is not covered by that skill: an app with no service worker still needs this.
- **Cache the document short, the hashed assets long.** `index.html`/the RSC document must not be cached long by a CDN while content-hashed assets are immutable — that mismatch manufactures skew on every deploy. (Infra-side, but it's the fix when skew persists despite the above.)
- **Long-lived tabs need a nudge.** Dashboards and kiosk screens can sit open for days. Where that's the norm, check the build id on focus/interval and surface the same reload prompt before the user hits a broken chunk.
