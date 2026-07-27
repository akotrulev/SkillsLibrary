# Frontend error-handling & resilience — scenario research and coverage gaps

**Date:** 2026-07-27
**Scope:** `frontend/react/skills/*` (the shipped `fe-react` rule set), read against a failure-scenario taxonomy built from current practice.
**Method:** coverage sweep of the 24 fe-react skills (grep + read of the resilience-bearing ones: `error-handling`, `data-fetching`, `realtime`, `state-management`, `forms`, `installable-offline-app`, `ui-rules`, `performance`, `auth/auth0-react`), then web research on frontend failure modes, version skew, fetch race conditions, session-expiry UX, timeout budgets, and third-party degradation.
**Trigger:** the failure-scoping + persistent-notification rule landed the same day (`frontend/PLAN.md` Phase 6). This asks the follow-up question: *what else fails, and does the plugin have a rule for it?*

---

## Summary

The plugin covers the **five classic surfaces** well — render exceptions, failed reads, live-connection drops, empty states, and (as of today) failure scoping + the persistent notification. What it does **not** cover is most of the *second* tier: the failures that don't announce themselves as an error at all. **A hung request, a stale-but-successful response, an expired session, a deploy that deletes the chunk the open tab is about to request, and a failed background refetch all currently fall through the rule set** — three of them by rendering a permanently-spinning skeleton, which is the exact defect class the three-state rule exists to kill.

16 scenarios assessed: **8 covered**, **3 partial**, **11 gaps** (some scenarios split into covered/gap halves). Ranked below; P1 items are ones where the current rules produce a *wrong* result, not merely an unspecified one.

---

## What is already covered (no action)

| # | Scenario | Where |
|---|---|---|
| C1 | Unhandled render/lifecycle exception | `error-handling` — three-tier boundaries (`global-error.tsx` / `error.tsx` / per-feature `react-error-boundary`) |
| C2 | Read fails (network / 5xx / 4xx) | `error-handling` three-state region + `data-fetching` `problemError` categorization |
| C3 | Transient fault absorbed | retry + exponential backoff, idempotent-only, no 4xx retry |
| C4 | Failure scoped to the data-dependent subtree | `error-handling` (added 2026-07-27) |
| C5 | Persistent top-right notification, user-dismissed | `error-handling` (added 2026-07-27) |
| C6 | Drifted/unparseable response body | `data-fetching` (Zod at the boundary, throws) + `error-handling` (renders failed, not empty) |
| C7 | WS/SSE drop, stale live data, reconnect status | `realtime` (socket) + `error-handling` (UX consistency) |
| C8 | Empty-state taxonomy (no records / no filter / filtered-out) | `error-handling` |

**Partial:** offline (`installable-offline-app` owns the SW/data strategy; `error-handling` has one line and no rule on write queuing) · client-error reporting (Sentry/OTel named, no rule on sampling or PII in breadcrumbs) · optimistic mutations (`forms`/`state-management` cover the happy path; the *rollback UX* is unspecified — see G7).

---

## Gaps, ranked

### P1 — the current rules produce a wrong result

**G1. No request timeout — the hung request spins forever.**
Nothing in the plugin sets a deadline. A request that never resolves (dropped connection, a proxy holding the socket, a wedged backend) leaves the region in `isPending` **indefinitely**, and the browser's own default is ~300s in Chrome — far past any user's patience. The three-state rule is defeated by a fourth non-state: *loading forever*. Every read needs a budget (~8–10s typical, longer for exports) via `AbortSignal.timeout(ms)`, combined with the user-cancel/unmount signal through `AbortSignal.any([...])` (both Baseline since 2024). `TimeoutError` categorizes distinctly from a 5xx ("taking longer than expected — retry"), and a *slow* request should cross a soft threshold (~4s) into a "still working" affordance before it crosses the hard one.
→ `data-fetching` (produce: the budget + the signal composition), `error-handling` (render: the slow tier + the timeout failed state), `code-review` + audit checklist.

**G2. Failed background refetch wipes good data.**
The rule added today says a failed read renders the failed body. Taken literally on a *refetch* (poll, window-focus refetch, filter change, `invalidateQueries`), that **replaces data the user is currently reading with an error panel** — a strictly worse outcome than the stale data. The distinction the rule set is missing: **initial-load failure → failed body; refetch failure → keep the last good data, mark it stale, notify.** TanStack Query already exposes this (`isPending` vs `isError` with `data !== undefined`, `placeholderData: keepPreviousData`). Without it, a flaky poll makes a working dashboard unreadable.
→ `error-handling` (a fourth state: *stale/degraded*), `data-fetching`, audit checklist.

**G3. Session expiry mid-session discards unsaved work.**
No skill owns the *UX* of a 401 while the user is working — `auth/auth0-react` owns the token/refresh mechanics and stops there. The default implementation (interceptor → `loginWithRedirect()`) unmounts the app and **destroys a half-filled form**, which is the same defect class as the early-return we just fixed, one level up. The rule: 401 → attempt silent refresh → **replay the original request once** → only if that fails, re-authenticate **in place** (modal/overlay) so the route and the dirty form survive; concurrent 401s queue behind **one** refresh (no refresh stampede, no infinite refresh→401 loop); a redirect is acceptable only from a read-only surface. And **403 ≠ 401**: a permission failure renders a permission-denied body in the scoped region, no retry, no re-auth.
→ new section in `error-handling`, cross-linked from `auth/auth0-react` and `forms` (dirty-state preservation).

**G4. Deploy version skew — `ChunkLoadError` on an open tab.**
Not mentioned anywhere in `frontend/react/`. A deploy invalidates the chunks an open tab is about to lazy-load; the next route navigation throws `ChunkLoadError` and the user sees a blank route or the app error boundary. Rules: set Next's `deploymentId` (14.1.4+) so the framework detects the mismatch and forces a reload; catch chunk/import errors globally and recover with a **once-only** reload guarded in `sessionStorage` (an unguarded reload is a reload loop); surface "a new version is available — reload" through the notification surface added today; keep it consistent with the service-worker update lifecycle `installable-offline-app` already owns. The RSC payload has the same skew problem — an old client requesting a deleted flight response.
→ new section in `error-handling`, cross-link `installable-offline-app` + `performance` (lazy boundaries).

**G5. Race / out-of-order responses.**
`data-fetching` threads `AbortSignal` for *cancellation on unmount*, but never names the defect it also prevents: **response B resolving before response A leaves the UI showing A's data under B's filter**. Classic in search-as-you-type and rapid filter changes. Rule: never `setState` from an un-guarded async in an effect (ignore-flag or abort in cleanup); prefer a keyed query (`queryKey: ['orders', filters]`) so ordering is the library's problem; the same rule covers the stale-closure variant.
→ `data-fetching` correctness rules, `code-review`, audit checklist.

### P2 — real defect classes, currently unspecified

**G6. Composition of multiple/dependent calls.** A page with N reads has no rule on how they compose. Missing: **critical vs optional data** (an optional widget's 500 must not fail the page — `Promise.allSettled`, never `Promise.all`, when one result is non-essential); dependent chains (parent fails → child query must be `enabled: false`, not fire, and **not** sit spinning); partial success rendering (show what resolved, scope the failure to what didn't). Follows directly from the scoping rule but isn't derivable from it.
→ `data-fetching` + `error-handling`.

**G7. Mutation failure semantics.** Retry rules exist; the *outcomes* don't. Missing: double-submit prevention (disable on pending — the button state is the guard); **idempotency key** for retryable writes; **optimistic rollback UX** — a row silently snapping back is a defect, the rollback must notify; **409/412 concurrency conflict** rendering (`ui-rules` mandates optimistic concurrency on the write path but nothing renders the conflict: "someone else changed this — reload / overwrite"); 422 → field errors (`forms` owns it, no cross-link).
→ `error-handling` (a mutation-failure subsection), `forms`, `ui-rules` cross-links.

**G8. 429 / `Retry-After` not honored.** The rule says "don't retry 4xx except 408/429" but not what to do *with* a 429: read `Retry-After`, back off to at least that, tell the user ("too many requests — retrying in Ns") rather than hammering, and stop after a bounded number of attempts.
→ `error-handling` retry section.

**G9. Notification storms / UI-level circuit breaking.** A 5s poll against a down endpoint raises a notification per tick. Dedupe-by-key (added today) handles identical errors; it does not handle **escalating volume across regions** during a backend outage. Needs: suppress-after-N with a count roll-up, and a **UI-level stop** — after k consecutive failures, stop auto-retrying and switch to manual retry only ("we've stopped retrying automatically").
→ `error-handling`.

**G10. Third-party / non-API dependency failure.** Maps, payment iframes, analytics, feature-flag providers, web fonts, embeds. Rules: every third party is wrapped in its own boundary and given a timeout+facade; **the feature-flag provider must never block render** (default values, fail-open/closed stated per flag); an analytics failure is invisible to the user (**no** notification — it is a log-only failure); a payment/embed failure **is** user-visible and needs a stated fallback path. The user-visible/log-only split is the part teams get backwards.
→ new short section in `error-handling`; `performance` already owns the loading-strategy half.

**G11. Client-side storage failures.** `localStorage` throws on quota exceeded and in Safari private mode; IndexedDB can be blocked entirely. Both TanStack's persisted cache and a Zustand `persist` store will throw on write. Rule: all storage access goes through a wrapper that catches and degrades to in-memory — a persistence failure must never crash the app or block a render.
→ `state-management` (owner) + `installable-offline-app` (offline data), noted in `error-handling`.

### P3 — worth a line, not a section

- **G12. RSC/Server-Action failure scoping.** A throw in a Server Component escalates to the *route's* `error.tsx` — which violates the scoping rule by construction. The RSC form of the rule: per-region `<Suspense>` + a region-scoped boundary, or return a Result and render the failed body inline. Server Actions should return typed errors rather than throwing. → `data-fetching` + `error-handling`.
- **G13. Stale tab / restore.** A tab restored from bfcache or woken after hours renders hours-old data as current. Refetch on focus/`visibilitychange` (TanStack default — say so), and mark data stale while it revalidates. → `data-fetching`.
- **G14. Deleted-entity navigation.** Open detail page for a record another user deleted → 404 on refetch. Distinguish "not found" from "failed" in the scoped region; offer navigation back to the list. `routing`/`seo` own `not-found.tsx` for the route-level case only. → `error-handling` + `routing`.
- **G15. Multi-tab coordination.** Two tabs, one session: token refreshed in tab A, tab B holds the old one; a logout in one tab leaves the other live. `storage`/`BroadcastChannel` sync. → `auth/auth0-react` + `state-management`.
- **G16. Hydration mismatch as a failure mode.** `basics`/`performance` treat it as a *cause* to avoid; nothing says what to do when it happens in production (React recovers by client re-rendering, logs a recoverable error; a throwing mismatch blanks the route). Report it, don't ignore it. → `basics` cross-link to `error-handling`.

---

> **Status (2026-07-27, same day):** all 11 gaps are **closed for `frontend/react/`** — see `frontend/PLAN.md` Phase 7 for what landed where. `frontend/blazor/` and `frontend/react-native/` still carry them.

## Recommended sequencing (leverage order)

1. **G1 + G2 together** — both change what the three-state region *is* (a timeout tier; a stale/degraded fourth state). They rewrite the same section, and G2 corrects a rule shipped today. Highest leverage: one edit to `error-handling` + `data-fetching`.
2. **G3 (session expiry)** — a self-contained new section; the highest-impact *user-visible* defect on the list (lost work).
3. **G4 (version skew)** — self-contained, mechanical, and invisible until it isn't.
4. **G5 + G6 + G12** — one editing pass over `data-fetching`'s correctness rules.
5. **G7 + G8 + G9** — one editing pass: the mutation/retry/notification-volume block in `error-handling`.
6. **G10 + G11 + G13–G16** — short additions in their owning skills.

Each step also lands in `code-review`'s resilience table and `standards-audit`'s section J (currently J1–J11) — the audit is what makes these enforceable rather than advisory.

## Cross-stack

Everything above is stack-shaped, not React-specific. `frontend/blazor/` has the **same 11 gaps** (its `error-handling` mirrors the React one section-for-section), with these deltas: version skew is smaller for Blazor Server (the circuit reconnect already forces a reload) but real for WASM lazy assemblies; the timeout budget is `HttpClient.Timeout`/Polly rather than `AbortSignal`; session expiry is the circuit + cookie-auth pair. `frontend/react-native/`'s `error-resilience` skill isn't authored yet — it should ship with these rules rather than inherit the gap (offline and stale-tab-restore are *more* central on mobile, and version skew becomes OTA-update skew).

Track alongside `frontend/PLAN.md` Phase 6.

## Sources

- [Designing Resilient Frontend Systems: Handling Failures Gracefully](https://beyondthecode.medium.com/designing-resilient-frontend-systems-handling-failures-gracefully-10c3c3a2d1b4)
- [A guide to graceful degradation in web development — LogRocket](https://blog.logrocket.com/guide-graceful-degradation-web-development/)
- [Building Resilient Frontends: Architecting for Partial Failures and Fallbacks](https://medium.com/@sonali.nogja.08/%EF%B8%8F-building-resilient-frontends-how-to-architect-for-partial-failures-and-fallbacks-79029a12d8ee)
- [Next.js Version Skew Protection: The Complete 2026 Guide](https://makerkit.dev/blog/tutorials/force-update-nextjs)
- [Next.js Stale Chunk & Cache Mismatch — Resolution Playbook](https://medium.com/@tarequlislam105150/next-js-stale-chunk-cache-mismatch-resolution-playbook-cdcf556b594c)
- [Fetching data in React: the case of lost Promises — Developer Way](https://www.developerway.com/posts/fetching-in-react-lost-promises)
- [Fixing Race Conditions in React with useEffect — Max Rozen](https://maxrozen.com/race-conditions-fetching-data-react-with-useeffect)
- [AbortSignal.timeout() — MDN](https://developer.mozilla.org/docs/Web/API/AbortSignal/timeout_static)
- [How to Timeout a fetch() Request — Dmitri Pavlutin](https://dmitripavlutin.com/timeout-fetch-request/)
- [Please stop redirecting to login on 401 errors — DEV](https://dev.to/aragossa/please-stop-redirecting-to-login-on-401-errors-3c0l)
- [Best Practices for Application Session Management — Auth0](https://auth0.com/blog/application-session-management-best-practices/)
- [Session/idle-timeout redirect silently discards unsaved edits — strapi#26571](https://github.com/strapi/strapi/issues/26571)
- [Load Third-Party JavaScript — web.dev](https://web.dev/optimizing-content-efficiency-loading-third-party-javascript)
