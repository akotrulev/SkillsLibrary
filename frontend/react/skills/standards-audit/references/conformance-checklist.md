# fe-react Conformance Checklist — the 19 sections

The audit's spine. Section letters and check numbers are **permanent** — a finding is `<letter><n>` (`B3`, `M1`) and keeps that ID across every round, forever. Never renumber; append new checks at the end of a section with the next free number.

**How to read a row.** *Check* = the invariant. *Violation looks like* = what disqualifies it. *Find it with* = a mechanical lead (a grep hit is never a finding — read the code). *Sev* = the default severity; adjust for real impact and say why.

**Recipes** use `rg` (ripgrep), which honours `.gitignore` — so `node_modules/`, `.next/`, `dist/`, and `coverage/` are skipped without flags. Without ripgrep, `grep -rn --include='*.tsx' --include='*.ts' --exclude-dir=node_modules --exclude-dir=.next` is equivalent. Set the source roots once:

```bash
SRC=$(ls -d app src pages 2>/dev/null | tr '\n' ' ')   # adjust to the repo layout
rg -n "<pattern>" $SRC                                  # the shape every recipe below uses
```

If the repo gitignores generated *source* you still need to read (a `src/generated/` client), add `--no-ignore` and exclude it explicitly — and say so in the report's coverage line.

**The version lane gates everything.** Before flagging, confirm the check applies to the detected React/Next major, render target, and Compiler state. Rows tagged **[19]**, **[18]**, **[App]**, **[Vite]**, **[Compiler-on]** apply only in that lane.

---

## A — Build health, version lane & migration hygiene
*Owning skills: [`project-setup`](../../project-setup/SKILL.md) · [`migration`](../../migration/SKILL.md) · [`basics`](../../basics/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| A1 | The project builds and type-checks clean | Red on arrival — build errors, `tsc --noEmit` errors, lint errors | Opt-in run only; otherwise inspect CI config + recent failures. Report as arrival state | major |
| A2 | One React major, coherently applied | React 19 installed but the codebase is written to 18 idioms throughout (or vice versa) | `package.json` vs `rg "forwardRef|useActionState|useOptimistic|\buse\(" $SRC` | major |
| A3 | No stranded half-migration | Both `app/` and `pages/` carrying live routes with no migration plan; `next/navigation` and `next/router` both imported | `ls app pages src/app src/pages`; `rg "from 'next/router'" $SRC` | major |
| A4 | Version-appropriate APIs only | Up-level API on a down-level project (e.g. `useActionState` on React 18) — a real runtime break, not a style call | `rg "useActionState\|useOptimistic\|useFormStatus" $SRC` + the detected major | blocker |
| A5 | **[19]** `forwardRef` retired | `forwardRef(` in new code on React 19, where `ref` is a plain prop | `rg "forwardRef" $SRC` | minor |
| A6 | Deps not EOL / abandoned in the plugin's lane | Node 20 (EOL Apr 2026) in `engines`/CI; Next 13 or lower; React 17 | `package.json` `engines`, CI workflow node version | major |
| A7 | Lockfile matches one package manager | Two lockfiles committed | `ls *lock*` | minor |

---

## B — RSC & the `'use client'` boundary  **[App]**
*Owning skills: [`basics`](../../basics/SKILL.md) · [`component-writer`](../../component-writer/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| B1 | `'use client'` sits on the smallest interactive leaf | Directive at the top of `page.tsx`/`layout.tsx` (or a barrel/index) because one child is interactive — drags the subtree into the bundle | `rg -l "^'use client'" $SRC \| grep -E "(page\|layout)\.tsx$"` | major |
| B2 | Server Components fetch; Client Components interact | `async` component body or `await fetch(...)` inside a `'use client'` file | Files from B1's `-l` list, then `rg "await |async function" <file>` | blocker |
| B3 | No server-only import in a client module | DB client, server SDK, `fs`, private env read, or a secret-bearing util imported into a `'use client'` file | `rg "process\.env\.(?!NEXT_PUBLIC_)" $SRC` cross-referenced with client files; check `server-only` package usage | blocker |
| B4 | Boundary props are serializable | A function, class instance, or Map/Set passed from a Server to a Client Component | Read the props at each client-boundary call site | major |
| B5 | Client Components compose server output via `children` | A `'use client'` file `import`ing a Server Component | Imports in client files resolving to non-client modules that do server work | major |
| B6 | No sequential-await waterfall | Independent `await`s serialized in one RSC where `Promise.all` fits | `rg -A6 "await .*fetch" $SRC` and read for consecutive awaits | major |
| B7 | Slow sections stream behind `<Suspense>` | A slow fetch blocking the whole route's TTFB, no `loading.tsx`, no boundary | `find $SRC -name 'loading.tsx'`; `rg "<Suspense" $SRC` | minor |
| B8 | `'use client'` count is proportionate | Nearly every file client — the app is an SPA wearing App Router clothes | `rg -l "^'use client'" $SRC \| wc -l` vs total component count | major |

---

## C — Routing & navigation
*Owning skill: [`routing`](../../routing/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| C1 | In-app navigation is a real `<Link href>` | `onClick={() => router.push(...)}` on a `<div>`/`<button>` for ordinary navigation | `rg "router\.push" $SRC` | major |
| C2 | **[App]** Every parallel slot has a `default.tsx` | An `@slot` directory with no `default.tsx` — hard-navigation 404s | `find $SRC -type d -name '@*'` then check for `default.tsx` | major |
| C3 | **[App]** Every intercepting route ships its non-intercepted page | `(.)`/`(..)` route with no standalone page for direct URL entry | `find $SRC -type d -name '(.*)'` | major |
| C4 | Route topology is deliberate | Layout used where a template is needed (state persisting across sibling routes that should remount), or a flat route tree bypassing existing groups | `find $SRC -name 'layout.tsx' -o -name 'template.tsx'`; read the tree | minor |
| C5 | **[App]** `middleware.ts` gate is narrow and matched | No `matcher`, so middleware runs on every asset request; or auth enforced *only* in middleware with no server-side re-check | `cat middleware.ts` | major |
| C6 | Route handlers validate input and set status honestly | `route.ts` returning 200 on failure, or parsing the body with no schema | `find $SRC -name 'route.ts'`; `rg "await req.json\(\)" $SRC` | major |
| C7 | Dynamic segments typed and guarded | `params.id` consumed with no existence check → a 500 instead of `notFound()` | `rg "params" $SRC` in dynamic segment folders | minor |
| C8 | **[Vite]** Router config centralized | Routes declared ad hoc across files instead of one route tree | read `main.tsx` / router setup | minor |

---

## D — State ownership
*Owning skill: [`state-management`](../../state-management/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| D1 | Server state lives in RSC fetch / TanStack Query — **not** a client store | Fetched API data copied into Zustand/Redux/`useState` and re-synced by hand | `rg "create\(|createSlice|useState" $SRC` around fetch call sites | major |
| D2 | No `useEffect` deriving state | `useState` + `useEffect` recomputing a value from props/state instead of computing in render | `rg -B2 -A6 "useEffect\(" $SRC \| rg "setState\|set[A-Z]"` | major |
| D3 | No set-state-from-props effect | `useEffect(() => setX(props.x), [props.x])` — use `key` or restructure ownership | same as D2 | major |
| D4 | Context value has stable identity | `<Ctx.Provider value={{ a, b }}>` allocated inline every render on a hot provider | `rg "\.Provider value=\{\{" $SRC` | major |
| D5 | Read/write contexts split where write churn is high | One provider carrying everything → whole tree re-renders on any change | Read each provider's value shape and consumer count | major |
| D6 | State lifted only as far as needed | App-level store holding a dropdown's open flag; or shared state owned by one sibling and drilled sideways | Read store slices for ephemeral UI keys | minor |
| D7 | URL-as-state for shareable view state | Filters/tabs/pagination in `useState` only — refresh and deep-link lose them | `rg "useSearchParams" $SRC` vs filter/tab components | minor |
| D8 | No mutable module-level state as shared component state | `let cache = []` / `export const store = {}` at module scope holding user data | `rg "^(let\|var) " $SRC` | blocker |

---

## E — Data access & realtime transport
*Owning skills: [`data-fetching`](../../data-fetching/SKILL.md) · [`realtime`](../../realtime/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| E1 | One data-fetching lane per surface, per the transport map | RSC fetch, TanStack Query, SWR, and raw `useEffect`+`fetch` all present with no rule about which is used when | `rg "useQuery\|useSWR\|useEffect.*fetch\|await fetch" $SRC` | major |
| E2 | HTTP goes through a typed client / server util | `fetch('http://…' + id)` string literals scattered through components, no error typing | `rg "fetch\(['\"\`]" $SRC` | minor |
| E3 | Server errors are mapped to UI, not swallowed | `catch {}`, `void fetchX()`, or a raw response body rendered | `rg "catch\s*\{\s*\}\|catch\s*\(\w+\)\s*\{\s*\}" $SRC` | major |
| E4 | ProblemDetails / 422 mapped to fields or a real message | Validation failures shown as "Something went wrong" or a JSON blob | Read each mutation's error path | major |
| E5 | No double-fetch across prerender → interactive | The same data fetched in an RSC and re-fetched by a client hook on mount | Compare RSC fetches with client hooks on the same route | major |
| E6 | Mutations invalidate / revalidate their reads | Data changes but the list doesn't (no `revalidatePath`/`revalidateTag`/`invalidateQueries`) | `rg "revalidatePath\|revalidateTag\|invalidateQueries" $SRC` vs mutation count | major |
| E7 | Retries only on idempotent requests | Blind retry wrapping a POST/mutation | `rg "retry" $SRC` | major |
| E8 | **[realtime]** Subscriptions clean up | `new WebSocket` / `new EventSource` / `subscribe(` in an effect with no teardown | `rg -A10 "new WebSocket\|new EventSource\|\.subscribe\(" $SRC` | major |
| E9 | **[realtime]** Connection status is visible; snapshot→live handoff is defined | Live region silently stops updating on disconnect; no reconnect path; duplicate or missed events at handoff | Read the realtime hook | major |
| E10 | Responses cannot land out of order | An effect fetch calling `setState` with no `ignore` flag / abort in cleanup, or a query key missing a parameter the request uses (`['orders']` for a search-driven fetch) — a stale answer silently overwrites a newer one | `rg -A8 "useEffect\(" $SRC \| rg "fetch\|\.then\("` and read for a cleanup; read every `queryKey` against its `queryFn` args | major |
| E11 | Optional calls can't fail the page | `Promise.all` spanning a critical read and an enrichment read — one dead nice-to-have service 500s the whole page | `rg "Promise\.all" $SRC` and classify each member; `rg "Promise.allSettled" $SRC` | major |
| E12 | Dependent queries are gated and resolve to a state | A child query firing with an `undefined` parent id, or left rendering a skeleton forever because the parent failed (no `enabled`, no unavailable state) | `rg "enabled:" $SRC` vs queries consuming another query's `data` | major |
| E13 | **[App]** Failable reads are scoped below the segment | Every read throwing straight to the segment's `error.tsx`, so one failed fetch replaces the route incl. its search/filters | Read RSC pages: is the failable read in its own `<Suspense>`+boundary, or returning a Result? | major |
| E14 | **[App]** Server Actions return typed errors for expected failures | Action `throw`ing on a validation/business failure — reaches the client as a generic error with no field mapping and no correlation id | `rg -A15 "'use server'" $SRC \| rg "throw"` | major |

---

## F — Forms & validation
*Owning skill: [`forms`](../../forms/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| F1 | Forms use React Hook Form + Zod (or a Server Action + `useActionState` **[19][App]**) | Hand-rolled `useState` per field with ad-hoc validation | `rg "<form" $SRC` vs `rg "useForm\|zodResolver" $SRC` | major |
| F2 | One schema validates client **and** server | Client-only validation; the Server Action / route handler trusts the payload | Compare the form schema with the handler's parsing | blocker |
| F3 | Field errors are associated with fields | Errors only in a summary; no `aria-invalid` / `aria-describedby` tie-in | `rg "aria-invalid" $SRC` vs input count | minor |
| F4 | Server errors map back to fields (`setError`) | 422 swallowed or shown as a raw blob | `rg "setError" $SRC` vs mutation forms | major |
| F5 | Submit is disabled/pending in flight | Double-submit possible; no pending affordance | Read each submit button | minor |
| F6 | Controlled/uncontrolled is explicit | `value` without `onChange`; both `value` and `defaultValue` | `rg "value=\{" $SRC` on inputs | major |

---

## G — Component library & styling authority
*Owning skills: [`component-library`](../../component-library/SKILL.md) · [`styling`](../../styling/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| G1 | **One** styling authority app-wide | Tailwind layered on MUI/Mantine/Chakra; `sx` + Tailwind + CSS Modules fighting on the same elements | `package.json` for `tailwindcss` + a CSS-in-JS library; `rg "className=\"[a-z-]+ (flex\|grid\|p-\d)" $SRC` | major |
| G2 | One component library, not three | Two libraries installed and both rendering controls | `package.json` for `@mui/*`, `@mantine/*`, `@chakra-ui/*`, `radix-ui` | major |
| G3 | `globals.css` holds only tokens + reset | Component styles dumped in the global stylesheet | `wc -l` + read `globals.css` / `index.css` | major |
| G4 | Design tokens as CSS custom properties; no literals in modules | Hardcoded hex/px colors in `*.module.css` or `sx` | `rg "#[0-9a-fA-F]{3,8}\b" --glob '*.module.css' --glob '*.tsx' $SRC` | minor |
| G5 | Functional tokens named by purpose | `--color-red` used for danger; brand and functional tokens conflated | Read the token file | minor |
| G6 | One color system — library theme and custom tokens bridged | Two diverging palettes (theme says one thing, CSS vars another) | Compare the theme file with the token file | major |
| G7 | Dark mode is an authored second palette | `filter: invert()`, negated hex, or contrast never re-checked | `rg "invert\(" $SRC`; read the dark palette | major |
| G8 | No descendant selectors reaching into a child's internals | `.parent .childInternal {}` in a module instead of a `className` prop | `rg "^\.\w+ \." --glob '*.module.css' $SRC` | minor |
| G9 | Fonts via `next/font` (App) — no raw `<link>` Google Fonts | `<link href="fonts.googleapis…">` | `rg "fonts.googleapis" .` | minor |

---

## H — Responsive & motion
*Owning skills: [`responsive-design`](../../responsive-design/SKILL.md) · [`animation`](../../animation/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| H1 | One breakpoint set app-wide (CSS vars + TS mirror, or the library's) | Magic width numbers scattered across modules; a second breakpoint system beside the library's | `rg "@media[^{]*\d+px" $SRC \| sort -u` — more than the documented set is the finding | major |
| H2 | Mobile-first `min-width` only | `max-width` cascades bolted onto a mobile-first codebase; `min-`+`max-` on one boundary | `rg "max-width:\s*\d+px" $SRC` | minor |
| H3 | Intrinsic CSS before breakpoints | Breakpoint soup where `auto-fit`/`minmax`/flex-wrap would do | Read the heaviest media-query modules | minor |
| H4 | **[SSR]** `useMediaQuery` guarded against hydration mismatch | JS breakpoint hook driving layout on a server-rendered surface with no mount guard / `ssrMatchMedia` | `rg "useMediaQuery\|matchMedia" $SRC` | major |
| H5 | No horizontal overflow; no fixed-dimension content regions | Fixed `width: 1200px` on a content region; images with no `max-width` | `rg "width:\s*\d{3,}px" $SRC` | minor |
| H6 | Visual reorder never breaks focus order | CSS `order`/`grid-area` reshuffling while DOM order stays wrong | `rg "order:\s*-?\d\|grid-area" $SRC` | major |
| H7 | `prefers-reduced-motion` is a hard floor | Any animation/transition with no reduced-motion path | `rg "prefers-reduced-motion" $SRC` vs `rg "transition:\|animation:\|framer-motion\|motion/react" $SRC` | major |
| H8 | Motion is CSS-first; JS animation is justified | A JS animation library pulled in for hover/fade effects CSS handles | `package.json` + usage sites | minor |

---

## I — Accessibility
*Owning skill: [`accessibility`](../../accessibility/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| I1 | Interactive elements are real `<button>`/`<a>`/`<input>` | `<div onClick>` / `<span onClick>` — loses keyboard + SR | `rg "<(div\|span\|li)[^>]*onClick" $SRC` | major |
| I2 | Semantic HTML before ARIA | `role="button"` on a div; ARIA compensating for a wrong element | `rg "role=\"" $SRC` | major |
| I3 | Every form field has a label | `<input>` with no `<label htmlFor>` / `aria-label` | `rg "<input" $SRC` cross-checked with labels | major |
| I4 | Composite widgets carry roles + relationships | Hand-rolled tabs/menu/dialog with no `role`/`aria-*`, instead of Radix / React Aria | `rg "Modal\|Dialog\|Tabs\|Menu" $SRC` | major |
| I5 | Focus managed on dialogs and client route changes | Modal opens without moving focus; route change strands focus (no `<main>` focus/announce) | `rg "autoFocus\|focus\(\)\|useRef<HTML" $SRC` around dialogs/route changes | major |
| I6 | Color is not the only state signifier | Errors/status shown only by color | Read status/badge/error components | minor |
| I7 | Images have meaningful `alt` (or `alt=""` when decorative) | `<img>` with no `alt`; raw `<img>` instead of `next/image` **[App]** | `rg "<img" $SRC` | minor |
| I8 | Landmarks and heading order | No `<main>`; heading levels skipping (h1 → h3) | `rg "<main\|<h[1-6]" $SRC` | minor |
| I9 | Icon-only controls have accessible names | `<IconButton>` / `<button><Icon/></button>` with no `aria-label` | `rg "IconButton\|<button[^>]*>\s*<" $SRC` | major |

---

## J — Error resilience
*Owning skill: [`error-handling`](../../error-handling/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| J1 | Every data region has explicit loading / loaded / **failed** states | Failure collapses into a blank section indistinguishable from "no data" | Read every fetch consumer; `rg "isLoading\|isPending" $SRC` vs `rg "isError\|error" $SRC` — the gap is the finding | major |
| J2 | **[App]** An error boundary wraps failable features | No `error.tsx` anywhere under `app/`; one data error crashes the whole page | `find $SRC -name 'error.tsx' -o -name 'global-error.tsx'` | major |
| J3 | **[Vite/18]** `react-error-boundary` (or equivalent) around failable trees | No boundary at all — a render throw blanks the app | `rg "ErrorBoundary" $SRC` | major |
| J4 | Never leak `error.message` / response bodies to users | Raw exception text rendered | `rg "\{error\.message\}\|\{err\.message\}" $SRC` | major |
| J5 | No swallowed rejections | `try {…} catch { }`, unhandled `void promise` | `rg "catch\s*\{\s*\}" $SRC` | major |
| J6 | Empty state is distinct from failed state | One "No results" covering both | Read list components | minor |
| J7 | Recovery path exists | Failure state with no retry / no navigation out | Read the failed branches | minor |
| J8 | Failure is scoped to the data-dependent subtree | An early `if (isError) return <Error/>` in a container that also renders the search bar / filters / toolbar — one failed call unmounts the whole page section and the user's typed filter state | `rg -n "if \(\w*\.?(isError\|error)\)\s*return" $SRC`, then read each hit: does the same component render chrome below the return? | major |
| J9 | Every surfaced failure raises a **persistent** notification | Error toast with an auto-dismiss timeout, no close button, not top-right, or no notification at all beside the inline state | `rg "autoClose\|duration\|persist\|autoHideDuration" $SRC` around the toast/snackbar calls; `rg "enqueueSnackbar\|toast\.\|notifications\.show\|toaster\." $SRC` | major |
| J10 | One root-mounted notification provider; one raise-point per failure path | Per-feature toast portals; the same failure notified at the call site *and* in a global `QueryCache.onError` (double-fire) | `rg "SnackbarProvider\|<Toaster\|<Notifications" $SRC` (expect one) + read the query/mutation error handlers | minor |
| J11 | An unreadable/drifted response fails, not empties | `safeParse` / `catch` falling through to `[]` or `null`, so a contract break renders as "no records" | `rg "safeParse\|\?\? \[\]\|catch.*=> \[\]" $SRC` | major |
| J12 | Every request carries a timeout budget | No `AbortSignal.timeout` anywhere — any hung call spins forever (browser default ~300s); or a `setTimeout`+`controller.abort()` race hand-rolled where the static fits | `rg "AbortSignal\.timeout\|AbortSignal\.any" $SRC` (absence across the data layer is the finding); `rg "setTimeout.*abort\(\)" $SRC` | major |
| J13 | Timeout budget composes with, not replaces, the cancel signal | `signal: AbortSignal.timeout(ms)` inside a `queryFn` that was handed a `signal` — unmount no longer cancels | Read each `queryFn` that destructures `signal` | minor |
| J14 | `AbortError` is not treated as a failure | A user-cancelled/unmounted request rendering a failed state or raising a notification | Read the error categorization helper (`problemError`/`toAppError`) for the `name === 'AbortError'` branch | minor |
| J15 | A failed **refetch** keeps the data on screen | `if (isError) return <Error/>` with no `data !== undefined` check — a blipped poll or focus-refetch replaces a working table with an error panel; no stale marker / "as of" time | `rg -n "isError" $SRC` and read each: does it guard on existing data? | major |
| J16 | No skeleton flash on page/filter change | Paginated or filtered lists dropping to `isPending` between keys — no `placeholderData: keepPreviousData` | `rg "keepPreviousData\|placeholderData" $SRC` vs the paginated query count | minor |
| J17 | Actions unsafe on stale data are disabled while stale | Price/balance/availability rendered stale with the write action still enabled | Read the stale-state branches of value-bearing regions | major |
| J18 | A mid-session 401 recovers before it redirects | `loginWithRedirect()` / `router.push('/login')` called directly from the 401 path — the app unmounts and unsaved work is lost; no silent refresh, no replay, no in-place re-auth | `rg "loginWithRedirect\|/login" $SRC` and read every 401 handler / response interceptor | blocker |
| J19 | Refresh is single-flight | Every failing request refreshing on its own — a rotation stampede that revokes the token family under reuse detection | Read the interceptor: is there one shared in-flight refresh promise the others await? | major |
| J20 | The replay is bounded | A replayed request that can re-enter the refresh path — infinite refresh→401 loop against the IdP | Look for a retry flag/marker on the replayed request | major |
| J21 | 401 and 403 handled differently | A permission denial triggering a refresh or a logout, or rendering as "session expired" | `rg "401\|403\|status ===" $SRC` in the error mapping | major |
| J22 | Only the app's own API can end the session | A third-party host's 401 running the ladder / logging the user out | Read the interceptor's host check | minor |
| J23 | XHR/Server-Action auth failures answer 401, not a redirect | `middleware.ts` or a route handler 302-ing a `fetch`/Action caller to the IdP — arrives as an opaque/CORS failure, never a login | `cat middleware.ts`; `rg "redirect\(" $SRC` in route handlers + actions | major |
| J24 | Deploy version skew is handled | Lazy routes / `next/dynamic` / `React.lazy` in use with no `ChunkLoadError` recovery and no `deploymentId` — every deploy breaks tabs that were already open | `rg "next/dynamic\|React\.lazy\|import\(" $SRC` vs `rg "ChunkLoadError\|Failed to fetch dynamically" $SRC`; check `next.config` for `deploymentId` | major |
| J25 | The skew reload is guarded and once-only | `location.reload()` in a chunk-error path with no `sessionStorage`/flag guard — an infinite reload loop when the new build is genuinely broken | `rg -B3 -A3 "location\.reload" $SRC` | blocker |
| J26 | One "new version available" affordance | A PWA waiting-worker prompt **and** a separate skew prompt, or a forced reload over unsaved work | `rg "new version\|SKIP_WAITING\|useRegisterSW" $SRC` | minor |
| J27 | Submit controls disable while pending | `onClick`/`onSubmit` handler with no `isPending`/`isSubmitting` disable — a second click duplicates the write (a duplicate charge on a payment) | `rg "onSubmit\|mutate\(" $SRC` and read for a `disabled=` tied to pending state | major |
| J28 | Retryable writes carry an idempotency key | A retried POST with no `Idempotency-Key` header (or equivalent) — a timed-out create becomes two records | `rg -i "idempotency" $SRC` vs mutations configured with `retry` | major |
| J29 | Optimistic rollback is announced | `onError` rolling back the cache with no notification — the user saw it work and walks away believing it saved | `rg -A10 "onMutate\|setQueryData" $SRC` → read each `onError` | major |
| J30 | 409/412 conflicts are handed back, not retried | A conflict auto-retried or silently overwriting — the other person's edit is erased | `rg "409\|412\|If-Match\|ETag" $SRC` | major |
| J31 | Bulk writes report per item | A blanket success toast over a partial failure, or a blanket failure hiding what succeeded | Read bulk/batch mutation handlers | major |
| J32 | `Retry-After` honoured; retries bounded | 429/503 retried on the client's own schedule, or auto-retry continuing indefinitely through an outage with no manual-only fallback | `rg -i "retry-after" $SRC`; read the `retry` predicates for an attempt cap | major |
| J33 | Notification volume is capped and rolled up | One toast per failing region per attempt — an outage buries the UI (and its own close buttons) | Read the notification provider for a stack cap / grouping | minor |
| J34 | Third-party failures are contained and correctly silent-or-loud | A widget/embed crash reaching the route boundary; an analytics failure toasted at the user; a flag provider gating first paint or with no default values | `rg "next/script\|<Script\|<iframe\|useFlag\|LaunchDarkly\|OpenFeature" $SRC` and read each for a boundary/timeout/default | major |
| J35 | Storage access is guarded and degrades | Bare `localStorage.getItem/setItem` or `JSON.parse` of storage with no `try/catch` — throws on quota / private mode / blocked context and breaks the render | `rg "localStorage\.\|sessionStorage\.\|indexedDB" $SRC` | major |
| J36 | Sessions are synced across tabs | Sign-out in one tab leaving a sibling rendering as signed-in; no `BroadcastChannel`/`storage` listener on auth transitions | `rg "BroadcastChannel\|addEventListener\('storage'" $SRC` | minor |
| J37 | A missing record reads as "gone", not "broken" | 404 on a detail route rendered as a generic failure with a retry that can never work; deleted row still in the list after the delete | `rg "notFound\(\)\|404" $SRC`; read delete mutations for invalidation | minor |
| J38 | Stale-tab restore revalidates | `refetchOnWindowFocus: false` / `refetchOnReconnect: false` set globally to quiet refetches — a restored tab shows hours-old data as current | `rg "refetchOnWindowFocus\|refetchOnReconnect" $SRC` | major |
| J39 | Recoverable errors are reported | No `onRecoverableError` / no hydration-mismatch reporting — the signal dies in a console nobody reads | `rg "onRecoverableError\|onCaughtError\|onUncaughtError" $SRC` | minor |

---

## K — Performance
*Owning skill: [`performance`](../../performance/SKILL.md) · vendored ruleset `frontend/react/vendor/reference/`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| K1 | Keys are stable domain ids | `key={index}` on a reorderable/filterable list — state and focus corruption | `rg "key=\{(i\|idx\|index)\}" $SRC` | major |
| K2 | No components defined inside components | A child component declared in a parent's body — remounts every render | `rg -B2 "const [A-Z]\w+ = \(" $SRC` inside component bodies | major |
| K3 | Derived data computed in render, not stored | A second `useState` mirroring a filtered/sorted list | see D2 | major |
| K4 | Large lists virtualized | Thousands of rows straight into the DOM | `rg "\.map\(" $SRC` on unbounded collections; check for `react-window`/`virtuoso`/`DataGrid` | major |
| K5 | **[Compiler-on]** No hand-rolled memoization | `useMemo`/`useCallback`/`memo` sprinkled where the Compiler already memoizes | `rg "useMemo\|useCallback\|React.memo" $SRC` + compiler flag | minor |
| K6 | **[Compiler-off]** Memoization is justified | Memo hooks with no memoized consumer — pure cost; or a hot path with none | same grep, read the consumers | minor |
| K7 | Heavy non-critical components code-split | A chart/editor/map library in the initial bundle | `rg "dynamic\(\|lazy\(" $SRC` vs heavy deps in `package.json` | major |
| K8 | No barrel-import cost | `import { X } from '@mui/material'` patterns pulling the world (where the library needs deep imports) | `rg "from '@mui/material'\|from 'lodash'" $SRC` | minor |
| K9 | Images optimized | Raw `<img>` with full-size assets; no `sizes`/`priority` on LCP image **[App]** | `rg "<img\|next/image" $SRC` | minor |
| K10 | No render-time expensive work | Sorting/parsing a large array or `JSON.parse` in a component body every render | Read hot component bodies | major |
| K11 | Lazy `useState` initializer for expensive values | `useState(expensive())` / `useState(localStorage.getItem(...))` runs every render | `rg "useState\((?!\)|null|''|\[\]|\{\}|false|true|0)" $SRC` | minor |

---

## L — SEO & discoverability  **[App]**
*Owning skill: [`seo`](../../seo/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| L1 | Public pages are server-rendered | Core content behind a client render / `ssr: false` dynamic import | `rg "ssr:\s*false" $SRC`; B1's client-route list | major |
| L2 | Every route sets a title | `metadata`/`generateMetadata` missing — the tab shows the app default on a content page | `find $SRC -name 'page.tsx'` vs `rg "export const metadata\|generateMetadata" $SRC` | minor |
| L3 | OG / social metadata on shareable routes | No `openGraph` anywhere | `rg "openGraph" $SRC` | minor |
| L4 | A truthful 404 | Missing route returns 200 with an empty page; no `not-found.tsx`, no `notFound()` call | `find $SRC -name 'not-found.tsx'`; `rg "notFound\(\)" $SRC` | major |
| L5 | Canonical, sitemap, robots present | No `sitemap.ts` / `robots.ts` on a public site | `find $SRC -name 'sitemap.*' -o -name 'robots.*'` | minor |
| L6 | Structured data where it earns its place | Product/article pages with no JSON-LD (only where the product needs it) | `rg "application/ld\+json" $SRC` | nit |

---

## M — Testability (`data-testid`)
*Owning skill: [`test-ids`](../../test-ids/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| M1 | Every interactive element carries a `data-testid` | Buttons/inputs/selects/menu items untagged | `rg "<button\|<input\|<select\|<textarea\|Button\|TextField" $SRC \| wc -l` vs `rg "data-testid" $SRC \| wc -l` | minor |
| M2 | Every list/grid container carries one | `<table>` / DataGrid / list root untagged | `rg "<table\|DataGrid\|role=\"grid\"" $SRC` | minor |
| M3 | No locator collisions | The same testid value on two distinct elements | `rg -o "data-testid=\"[^\"]+\"" $SRC \| sort \| uniq -d` | major |
| M4 | Row locators are static | Array index, numeric id, GUID, or a state value interpolated into a testid | `rg "data-testid=\{" $SRC` | major |
| M5 | Naming is `PageOrComponent.ElementType[.Qualifier]`, PascalCase dot-separated | kebab-case, snake_case, spaces, or free-form values | `rg -o "data-testid=\"[^\"]+\"" $SRC \| rg -v "^[A-Z]"` | nit |
| M6 | Repeated values extracted to a `const` | The same literal string repeated across component and test | duplicate literals from M3's output | nit |
| M7 | No wrapper components introduced just to carry testids | `AppButton` existing only to add a testid | Read thin wrappers | minor |

Findings in this section are the direct input to the `missing-testids.md` handshake with `qa-ui-typescript`.

---

## N — UI conventions
*Owning skill: [`ui-rules`](../../ui-rules/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| N1 | Destructive actions confirm by naming the object | Generic "Are you sure?"; `window.confirm`; no confirmation at all | `rg "window.confirm\|Are you sure" $SRC`; read delete handlers | major |
| N2 | Grids/lists sort deterministically with a tiebreaker | Order changes between identical refetches | Read sort logic / query ordering | minor |
| N3 | Display values are humanized | Raw enum ints, bare GUIDs, ISO timestamps shown where a name/format exists | `rg "\{.*\.id\}\|toISOString" $SRC` | minor |
| N4 | Links open same-tab by default | `target="_blank"` on an internal route, or without `rel="noopener"` + a cue | `rg "target=\"_blank\"" $SRC` | major |
| N5 | Surface chosen deliberately | A long/multi-step flow trapped in a modal; a blocking modal over data the user must read | Read modal contents | major |
| N6 | Tables/lists have an empty state | A blank region where "no data" should be stated | see J6 | minor |
| N7 | Dates/numbers/currency formatted per locale conventions | Manual `.split('-')` date munging; hardcoded `$` | `rg "toLocaleDate\|Intl\.\|\\$\{" $SRC` | minor |
| N8 | Copy is consistent and active-voice | Three different words for the same object; passive/blaming error text | Read the shared copy surfaces (`design/ux-writing` altitude) | nit |

---

## O — Component & pure-logic tests
*Owning skill: [`component-testing`](../../component-testing/SKILL.md)*

**Glob note:** component tests are `*.test.tsx`, pure-logic tests are `*.test.ts`. Layer-agnostic checks below sweep **both** (`*.test.{ts,tsx}`) — a repo with zero pure-logic tests must not pass this section clean.

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| O1 | A test runner is configured and green | No Vitest/Jest at all, or a suite nobody runs | `package.json` scripts + `find . -name '*.test.ts*'` | major |
| O2 | Logic-bearing components and custom hooks are covered | Reducers, guards, derived-state components, `use*` hooks with no test | Compare hooks/logic components with test files | major |
| O3 | No markup-only snapshot tests standing in for assertions | `toMatchSnapshot()` as the only assertion | `rg "toMatchSnapshot" $SRC` | minor |
| O4 | Queries prefer role/label over testid | `getByTestId` everywhere in unit tests where `getByRole` fits | `rg "getByTestId" --glob '*.test.tsx' $SRC` | minor |
| O5 | Async-RSC logic is extracted and unit-tested | An async Server Component with untestable inline fetching and no extracted function | Read async page components | minor |
| O6 | No conditional logic driving assertions | `if`/`for` deciding what a test asserts | `rg "\bif\s*\(" --glob '*.test.{ts,tsx}' $SRC` | minor |
| O7 | Tests are independent and deterministic | Shared mutable fixture across tests; `waitForTimeout`/`sleep` instead of condition waits | `rg "setTimeout\|sleep\(" --glob '*.test.{ts,tsx}' $SRC` | major |
| O8 | Non-rendering logic has pure-logic tests | Zod schemas, formatters, mappers, stores, URL serializers, extracted async-RSC fetches with no `*.test.ts` beside them | `find $SRC -name '*.test.ts'` vs the schema/util/store inventory; spot-check 3 schemas + the stores | major |
| O9 | Pure-logic tests don't render | `render()`/`renderHook` inside a `*.test.ts`, or a formatter tested through a component | `rg "render\(" --glob '*.test.ts' $SRC` | minor |
| O10 | Assertions on schema errors use path/code, not message | `expect(err.message).toBe('Required')` — breaks on locale or a Zod bump | `rg "issues\[0\]\?\.message\|error.message" --glob '*.test.{ts,tsx}' $SRC` | minor |
| O11 | Browser seams are injected, not global | Logic reading `Date.now()`/`window`/`localStorage` directly, so its test needs jsdom | `rg "Date.now\(\)\|localStorage\|window\." $SRC --glob '!*.test.*'` cross-referenced with untested units | major |

---

## P — Localization  *(conditional)*
*Owning skill: [`languages`](../../languages/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| P1 | No hardcoded user-facing strings in localized UI | Literal English text in JSX on a multi-language app | `rg ">[A-Z][a-z]+ [a-z]+" $SRC` (visual scan) vs `t(` usage | major |
| P2 | Locale pipeline matches the render strategy | Locale resolved client-side only on server-rendered routes (flash of wrong language) | Read the i18n setup + middleware | major |
| P3 | Formatting via `Intl`, not string surgery | Manual date/number formatting bypassing the locale | `rg "toLocaleDate\|Intl\." $SRC` vs manual formatting | minor |
| P4 | RTL supported where a locale needs it | `dir` never set; physical CSS properties (`margin-left`) instead of logical (`margin-inline-start`) | `rg "dir=\|margin-left\|padding-left" $SRC` | minor |
| P5 | Catalogs complete — no missing-key fallbacks in production | Keys rendering as raw ids | Compare catalog files across locales | minor |

---

## Q — PWA / offline  *(conditional)*
*Owning skill: [`installable-offline-app`](../../installable-offline-app/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| Q1 | Manifest complete (name, icons, display, start_url, theme) | Partial manifest — install prompt never fires | `cat public/manifest.json` / `app/manifest.ts` | major |
| Q2 | Service worker generated by the supported tool | Hand-rolled SW with ad-hoc caching | `rg "serwist\|vite-plugin-pwa\|workbox" package.json`; `ls public/sw.js` | major |
| Q3 | An explicit update lifecycle exists | "I redeployed and nothing changed" — no skip-waiting/update prompt path | Read the SW registration | major |
| Q4 | Offline covers *data*, not just the shell | Shell loads offline, every screen shows a spinner forever | Read the offline data strategy | major |
| Q5 | Dynamic routes show an honest offline state | A per-request server-rendered route precached as if it worked | Compare precache scope with route render strategies | major |

---

## R — Auth wiring  *(conditional)*
*Owning skills: `auth/auth0-react` · `auth/_shared/auth0-concepts`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| R1 | The right SDK lane for the render target | `@auth0/auth0-react` (SPA PKCE) used on App Router where `@auth0/nextjs-auth0` belongs, or vice versa | `package.json` + render target | major |
| R2 | Tokens never in `localStorage` / never in a client store | Access token persisted to `localStorage`/Zustand | `rg "localStorage.*token\|token.*localStorage" $SRC` | blocker |
| R3 | Authorization enforced server-side, not only in the UI | Route protected only by a conditional render / client redirect | Compare client guards with server/middleware checks | blocker |
| R4 | Secrets only in server env | `NEXT_PUBLIC_`-prefixed client secret; secret in a `'use client'` module | `rg "NEXT_PUBLIC_.*(SECRET\|KEY\|TOKEN)" .` | blocker |
| R5 | Session read server-side in RSC / Actions / handlers **[App]** | Session fetched client-side and trusted for authorization | `rg "getSession\|useUser" $SRC` | major |
| R6 | Logout clears session and local state | Logout leaves cached user data / a live query cache behind | Read the logout path | minor |

---

## S — Project structure, TS strictness, secrets & comments
*Owning skills: [`project-setup`](../../project-setup/SKILL.md) · [`basics`](../../basics/SKILL.md) · [`code-review`](../../code-review/SKILL.md) (S10–S12)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| S1 | `strict: true` in `tsconfig.json` | Strict off, or `strictNullChecks`/`noImplicitAny` individually disabled | `cat tsconfig.json` | major |
| S2 | No `any` | `: any`, `as any`, `as unknown as X` | `rg ":\s*any\b\|as any\|as unknown as" $SRC` | major |
| S3 | No bare suppressions | `@ts-ignore` / `@ts-expect-error` / `eslint-disable` with no justification comment | `rg "@ts-ignore\|@ts-expect-error\|eslint-disable" $SRC` | major |
| S4 | Variant props are discriminated unions | `variant?: string` with stringly-typed branching | `rg "variant\??:\s*string" $SRC` | major |
| S5 | Feature-folder layout, consistently applied | Half the app in `features/`, half in a flat `components/` dump of 90 files | `ls src/**; find $SRC -name '*.tsx' \| sed 's\|/[^/]*$\|\|' \| sort \| uniq -c \| sort -rn \| head` | minor |
| S6 | No secrets in the client bundle or in the repo | API keys, connection strings, tokens committed or `NEXT_PUBLIC_`-exposed | `rg "NEXT_PUBLIC_" .`; `rg -i "api[_-]?key\|secret\|password" --glob '!*.test.*' $SRC` | blocker |
| S7 | Lint + format configured and enforced | No ESLint config, or a config nothing runs | `ls .eslintrc* eslint.config.*`; CI workflow | minor |
| S8 | Structured logging on the server; no stray `console.log` | `console.log` in server code and hot render paths | `rg "console\.(log\|debug)" $SRC` | minor |
| S9 | Env access is validated and typed | `process.env.X!` used raw with no schema/validation | `rg "process\.env\." $SRC` | minor |
| S10 | No inline comments inside component bodies, hooks, or JSX | Step markers (`// render the header`, `{/* the list */}`), a line restating the line below, leftover `TODO`/`FIXME` with no ticket, commented-out JSX | `rg -n "^\s+//\|\{/\*" $SRC` then read the hits that sit inside a body — a hit is never a finding | minor |
| S11 | TSDoc only where the name genuinely cannot carry the meaning | A doc block restating the component name; TSDoc on every member of a `Props` interface or every field of a Zod schema | `rg -n -A1 "^\s*/\*\*" $SRC` — check what each sits above | minor |
| S12 | Surviving comments are true and load-bearing | A comment describing behaviour the component no longer has — the comment is the defect, and deletion is the fix | Read the code around every comment S10/S11 surfaced; grep cannot decide this one | major |

**S10–S12 are the audit face of [`engineering-practices/code-comments`](../../../../../engineering-practices/code-comments/SKILL.md)** — read it for the rule, the complex-flow test that earns TSDoc, the never-comment trivia list, and the family-vs-per-finding reporting split (S10 is one family with a count and 3–5 cited sites; each **S12** stale comment is its own finding). Two local notes: the `'use client'` / `'use server'` directives are **not** comments, and **S3 already owns bare suppressions** — an un-justified `eslint-disable-next-line react-hooks/exhaustive-deps` belongs there, not here.

---

## Section index — for the report's applicability matrix

| Letter | Section | Conditional? |
|---|---|---|
| A | Build health, version lane & migration hygiene | always |
| B | RSC & the `'use client'` boundary | App Router only |
| C | Routing & navigation | always (rows tagged per lane) |
| D | State ownership | always |
| E | Data access & realtime transport | realtime rows conditional |
| F | Forms & validation | always (skip if no forms — say so) |
| G | Component library & styling authority | always |
| H | Responsive & motion | always |
| I | Accessibility | always |
| J | Error resilience | always |
| K | Performance | always |
| L | SEO & discoverability | App Router / public site |
| M | Testability (`data-testid`) | always |
| N | UI conventions | always |
| O | Component & pure-logic tests | always (absence is O1) |
| P | Localization | multi-language apps only |
| Q | PWA / offline | installable/offline apps only |
| R | Auth wiring | apps with auth only |
| S | Project structure, TS strictness, secrets & comments | always |
