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

## O — Component tests
*Owning skill: [`component-testing`](../../component-testing/SKILL.md)*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| O1 | A component test runner is configured and green | No Vitest/Jest at all, or a suite nobody runs | `package.json` scripts + `find . -name '*.test.tsx'` | major |
| O2 | Logic-bearing components and custom hooks are covered | Reducers, guards, derived-state components, `use*` hooks with no test | Compare hooks/logic components with test files | major |
| O3 | No markup-only snapshot tests standing in for assertions | `toMatchSnapshot()` as the only assertion | `rg "toMatchSnapshot" $SRC` | minor |
| O4 | Queries prefer role/label over testid | `getByTestId` everywhere in unit tests where `getByRole` fits | `rg "getByTestId" --glob '*.test.tsx' $SRC` | minor |
| O5 | Async-RSC logic is extracted and unit-tested | An async Server Component with untestable inline fetching and no extracted function | Read async page components | minor |
| O6 | No conditional logic driving assertions | `if`/`for` deciding what a test asserts | `rg "\bif\s*\(" --glob '*.test.tsx' $SRC` | minor |
| O7 | Tests are independent and deterministic | Shared mutable fixture across tests; `waitForTimeout`/`sleep` instead of condition waits | `rg "setTimeout\|sleep\(" --glob '*.test.tsx' $SRC` | major |

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

## S — Project structure, TS strictness & secrets
*Owning skills: [`project-setup`](../../project-setup/SKILL.md) · [`basics`](../../basics/SKILL.md)*

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
| O | Component tests | always (absence is O1) |
| P | Localization | multi-language apps only |
| Q | PWA / offline | installable/offline apps only |
| R | Auth wiring | apps with auth only |
| S | Project structure, TS strictness & secrets | always |
