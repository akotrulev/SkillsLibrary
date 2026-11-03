---
paths:
  - "**/app/**/{page,layout,route,error,global-error,loading,not-found,default,template}.{ts,tsx,js,jsx}"
  - "**/{actions,queries}/**/*.{ts,tsx}"
  - "**/*.{actions,queries}.{ts,tsx}"
  - "**/actions.{ts,tsx}"
  - "**/middleware.{ts,js}"
---

<!-- fe-react rules v1 (2026-11-03): data and server code. Installed by /fe-react:rules; edit the paths above to where this app keeps its fetch code. -->

# React data-fetching and server-code standards

Severity tags as in the core React rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- Fetch on the server by default; TanStack Query only when the client owns the request. Fetch logic lives in a data module; base URLs from config. *major*
- No HTTP hop from a Server Component to your own API; call it in-process from a `server-only` module. *major*
- Independent awaits run in parallel; `allSettled` once a call is optional; a slow section streams in `<Suspense>`. *major*
- Next 15 does not cache `fetch`: state `revalidate` / `tags` / `no-store`; Server Actions mutate, then `revalidateTag` / `revalidatePath`. *major*
- Every request has a timeout composed with the cancel signal (`AbortSignal.any`); `TimeoutError` is a failure, `AbortError` is not. *major*
- The query key holds every parameter the request uses; an effect fetch ignores or aborts a stale answer in its cleanup. *major*
- Parse responses with the endpoint's Zod schema; a parse failure is failed, never `[]`. A URL with an unsubstituted `{placeholder}` throws. *major*
- `ProblemDetails` becomes friendly text and the correlation id; the detail is logged server-side. Server Actions return typed errors for expected failures. `global-error.tsx` and `error.tsx` are backstops; a failable read is scoped below the segment. *major*
- Retry idempotent calls only, never a 4xx; honour `Retry-After`, cap attempts. A retried write carries an idempotency key; a 409/412 is handed back; a rollback notifies. *major*
- A 401 runs single-flight refresh, one replay, re-auth in place; never a redirect off unsaved work. A 403 is not a refresh. *blocker*
- Keep `refetchOnWindowFocus` / `refetchOnReconnect` on. *major*
- A chunk-load failure reloads once, `sessionStorage`-guarded; set `deploymentId`. *blocker*
- `middleware.ts` has a scoped `matcher` and is not authorization; `redirect()` stays outside `try`; on Next 15 `await params`. *major*
- Client errors reach the server, never console-only. *minor*
