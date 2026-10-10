# frontend/ audit — findings & plan of action

**Date:** 2026-07-12
**Scope audited:** `frontend/blazor/` (22 skills + `fe-blazor` agent), `frontend/react/` (21 skills + `fe-react` agent + 3 vendored seeds), React Native (moved to `mobile/`; superseded by `docs/plans/002-mobile-plugins.md`), plus the `fe-blazor`/`fe-react` marketplace wiring.
**Method:** structural + wiring checks inline; one deep read-only audit per shipped stack (frontmatter, cross-references, agent↔skills contract, version-awareness, size, consistency).

---

## Overall assessment

Both shipped stacks are in **very good shape** — no blockers, zero dead cross-references found across a wide spot-check, airtight agent↔skills contracts (all skills loaded by their agent, no orphans, 6-phase structure matches CLAUDE.md including the design-critique loop and visual self-critique), uniform version-awareness (net10/net8-9 and React 19/18 fallbacks correctly tagged; reviewers explicitly forbid flagging down-level projects), and consistent cross-skill rules (data-testid convention, severity tables, dark-mode/token ownership, MUI/never-Tailwind-atop-MUI).

The issues found are concentrated in four areas: **(1)** skill descriptions at or over the 1024-char hard limit, **(2)** leftover authoring artifacts shipping inside the `fe-blazor` plugin (one leaking a real client project name), **(3)** the three vendored Vercel seeds registering as independently-routable skills whose triggers shadow the curated house skills, and **(4)** small parity/metadata gaps.

---

## Findings

| # | Severity | Location | Issue | Suggested fix |
|---|----------|----------|-------|---------------|
| F1 | major | `blazor/skills/reference/SKILL.md` | Description is **1034 chars** — over the 1024-char hard limit on skill descriptions; risks truncation/rejection by the loader | Trim ≥ 34 chars (drop one redundant trigger phrase) |
| F2 | major | `blazor/skills/testability/SOURCE.md`, `blazor/skills/ui-rules/SOURCE.md` | Consumed seed material ("SEED MATERIAL — do not register as a skill") ships inside the published MIT `fe-blazor` plugin; `test-ids/SOURCE.md` **leaks a real client project name** (`FlexInvest.AdminService.API`, internal paths, REFLEX framework) and contains a stray frontmatter fragment; both reference a `frontend/PLAN.md` that no longer exists | Remove from the shippable tree (archive outside the repo or delete — content is fully absorbed into the SKILL.md files) |
| F3 | major | `blazor/DESIGN-GAP-ANALYSIS.md` | Stale working artifact (2026-07-11): says "17 skills" (now 22) and "agent not yet built" (it exists); referenced by nothing | Delete |
| F4 | major | `react/vendor/{reference,composition-patterns,view-transitions}/SKILL.md` | The three Vercel seeds ship as **independently-routable plugin skills** (`vercel-*` names, trigger-bearing descriptions, no "Do NOT use" routing). Their triggers shadow the curated house skills: `vercel-react-best-practices` ↔ `fe-react-performance`; `vercel-react-view-transitions` ↔ `fe-react-animation`; `vercel-composition-patterns` ↔ `fe-react-basics`/`component-writer`. A raw request can route straight to the seed and bypass the house version-policy/curation layer | Decide: (a) stop registering them as skills (drop from the `fe-react` plugin `skills` array; house skills keep pointing into their files), or (b) add an explicit "Do NOT use directly — load via `fe-react-{performance,motion,reference}`; deep-dive seed" clause to each vendor description. **(b) is the lighter, recommended fix** — keeps them discoverable for deep dives while preserving routing discipline |
| F5 | minor | ~16 descriptions across both stacks | Descriptions sit at or within ~3% of the 1024 cap — fragile against any edit. Blazor: `ui-rules` + `languages` (exactly 1024), `styling` 1020, `accessibility` 1014, `seo` 1012, `error-handling` 1005, `animation`/`installable-offline-app`/`component-testing`/`javascript-calls`/`responsive-design` 970–995. React: `animation` 1022, `ui-rules` 1022, `error-handling` 1021, `installable-offline-app` 1020, `seo` 1014, `component-testing` 1011, `styling` 1010, `accessibility` 1006, `responsive-design` 1002 (rest &lt; 1000) | One editing pass trimming every frontend description to **≤ 1000 chars** for headroom |
| F6 | minor | `react/skills/generator/SKILL.md` | Owns compound-component + container/presentation recipes but doesn't point at the `vendor/composition-patterns` deep-dive seed (sibling `basics` does, at its L125) | Add the "deep treatment → `frontend/react/vendor/composition-patterns`" pointer in those two sections |
| F7 | minor | `react/skills/testability/` | No `references/` at all — blazor's counterpart has `references/static-html.md` (hybrid/static-HTML surfaces). Real parity delta beyond the documented `javascript-calls` drop; plausibly intentional | Either add a short hybrid/static-surface note or state in-skill that non-React surfaces are out of scope |
| F8 | minor | `react/vendor/composition-patterns/metadata.json` | `"organization": "Engineering"` vs siblings' `"Vercel Engineering"` | Normalize to `"Vercel Engineering"` |
| F9 | nit | `react/vendor/*/README.md`, `react/vendor/*/AGENTS.md` | Standalone-repo scaffolding ("maintaining this repo") ships in the plugin bundle — dead weight for consumers; `metadata.json` alone carries provenance | Optionally strip `README.md`/`AGENTS.md` from the bundled copies |
| F10 | info | React Native seed (now `mobile/react-native/`) | Raw, unadapted Vercel import (`name: vercel-react-native-skills`, upstream `rules/`/`AGENTS.md`/`metadata.json` layout). Correctly fenced: under construction per CLAUDE.md and **not** referenced by any plugin. No action required now — captured as the future work item below | See Phase 5 |

**Verified clean (no action):** frontmatter names all match folders with full Triggers + Do-NOT routing (43/43 house skills); all spot-checked cross-references resolve (design/*, auth/*, qa/* peers, ep-* bundle paths, intra-domain links, references/ files); both agents brownfield-compliant (`Mode: FIX | EXTEND`, orientation pass, minimal-change rule) per `.skill-template/agent.md`; version policies correctly applied (incl. `forwardRef`-only-a-finding-on-19, `useActionState` vs `useFormState`, net10 `NotFoundPage`/`[PersistentState]`/`ReconnectModal` with down-level fallbacks); no SKILL.md over 500 lines; vendor skill names don't collide; marketplace `skills`/`agents` arrays for `fe-blazor`/`fe-react` all resolve on disk.

---

## Plan of action

Run phases in order; each is independently committable. Phases 1–3 are quick hygiene (≈ one short session together); Phase 4 is small content work; Phase 5 is a future multi-session effort with its own gate.

### Phase 1 — remove shipping artifacts (F2, F3)
- [ ] Delete `frontend/blazor/DESIGN-GAP-ANALYSIS.md` (stale, unreferenced)
- [ ] Delete `frontend/blazor/skills/test-ids/SOURCE.md` and `frontend/blazor/skills/ui-rules/SOURCE.md` (consumed seeds; the testability one leaks the FlexInvest client name into the published plugin — if the seeds must be kept, move them outside the repo, not just outside `skills/`)
- [ ] Grep the repo for any remaining `FlexInvest` / client-specific strings under shipped folders: `grep -ri flexinvest --include='*.md' .`

### Phase 2 — description-length pass (F1, F5)
- [ ] Fix `fe-blazor-basics` first (1034 chars — the only one confirmed over the limit)
- [ ] Trim every frontend skill description listed in F5 to ≤ 1000 chars: cut redundant trigger phrasings first, never the Do-NOT routing targets
- [ ] Re-run the length check over `frontend/**/SKILL.md` (fold whitespace, count chars) and confirm all ≤ 1000
- [ ] Optional: extend the same check to the other domains (qa/, backend/, data/, …) — likely the same authoring style produced the same crowding there

### Phase 3 — vendor-seed routing discipline (F4, F8, F9)
- [ ] **Decision (recommended: option b):** keep the three `vercel-*` seeds registered but append to each description: "Do NOT use directly — load via `frontend/react/skills/{performance | motion | reference}`; this is the deep-dive seed those skills route into." (If instead choosing option a, remove the three `./frontend/react/vendor/*` entries from `fe-react`'s `skills` array in `.claude-plugin/marketplace.json` — the house skills reference the files by path, which still resolves in-bundle)
- [ ] Fix `vendor/composition-patterns/metadata.json` organization → `"Vercel Engineering"`
- [ ] Optional: strip `README.md` + `AGENTS.md` from the three vendor dirs (keep `SKILL.md`, `rules/`/`references/`, `metadata.json` for provenance)
- [ ] Note: whichever option is chosen, keep the upstream-import provenance line in `fe-react.md` (agent line 20) accurate

### Phase 4 — small content/parity fixes (F6, F7)
- [ ] `react/skills/generator/SKILL.md`: add the `vendor/composition-patterns` deep-dive pointer in the compound-component and container/presentation sections (mirror `basics` L125's phrasing)
- [ ] `react/skills/testability/SKILL.md`: add either a short "hybrid/static-HTML surfaces" appendix (rows-by-index rule, hardcoded parent locator consts — mirror blazor's `references/static-html.md`) **or** an explicit out-of-scope statement; the current silence is the only unexplained blazor↔react delta

### Phase 5 — react-native adaptation (F10 — superseded by `docs/plans/002-mobile-plugins.md`; the stack moved to `mobile/react-native/`)
- [x] **Decision (2026-07-12):** adapt the Vercel rules into a proper **React Native stack** (agent + skills; now the `mobile-react-native` plugin), mirroring the react port pattern — one node per session, `HANDOFF.md` between sessions. The node breakdown that lived in the old `PLAN.md` is superseded by `docs/plans/002-mobile-plugins.md`.
- [x] Node 0 (groundwork): restructured the raw Vercel import into `mobile/react-native/vendor/react-native-guidelines/` (fenced seed — "Do NOT use directly" clause, `organization → "Vercel Engineering"`, this closes the F8 parity + F10 fencing items for RN).
- [x] Node 1 (foundations A): `basics` + `project-setup` skills authored (Expo SDK 56 / New-Architecture version policy locked).
- [ ] Nodes 2–7: remaining skills, phased agent, marketplace + CLAUDE.md wiring, verification — superseded by `docs/plans/002-mobile-plugins.md`.
- [ ] Until Node 7: stays **unregistered** (no plugin references it) and listed as under-construction in CLAUDE.md's scope fence.
- [ ] When built (Node 7): update CLAUDE.md scope + catalog, marketplace.json, and the new-project-setup line.

### Phase 6 — GAP: failure scoping + persistent error notification (cross-stack parity)

**Raised 2026-07-27. Landed in `frontend/react/` only — `frontend/blazor/` and React Native (now `mobile/react-native/`; superseded by `docs/plans/002-mobile-plugins.md`) still have the gap.**

**The rule** (now in CLAUDE.md's FE-React code rules and `react/skills/error-handling`): when an element depends on a request and the request fails **or the response can't be read** (transport error, auth error, or a **drifted body that fails schema validation**):

1. **Scope the failure to the response-dependent subtree.** Everything that doesn't need the response keeps rendering and stays interactive — a list page's search bar, filters, toolbar, column headers and paging survive; only the **rows** area swaps to the failed body. Same for a chart (canvas fails, legend/range picker don't), a master/detail pane, a dependent `<select>`, one dashboard tile. The canonical defect is an early `if (isError) return <Error/>` in a container that also renders the chrome — it unmounts the controls **and the filter text the user typed**.
2. **Also raise a persistent notification, top-right** — friendly message + correlation id, **no auto-dismiss for errors**, closes only on an explicit close button, deduped by key, from one root-mounted provider with one raise-point per failure path. This refines the older "never only a toast" rule: the toast is wrong *instead of* the inline state, right *in addition to* it.
3. **A drifted/unparseable response is a failed state, never an empty one** — no `safeParse`/`catch` falling through to `[]`, which renders a broken contract as "no records".

**React (done):** `error-handling` (two new sections + rules/anti-patterns/validation + description), `data-fetching` (parse failure throws a categorized error), `ui-rules` §8 (shared grid owns the three states; chrome lives above it), `test-ids` (region + notification ids), `code-review` (3 checks), `standards-audit` checklist J8–J11, CLAUDE.md FE-React code rules.

**Blazor (to do — mirror all seven):**
- [ ] `blazor/skills/error-handling/SKILL.md` — add the **failure-scoping** section (the Razor equivalent: no `@if (failed) { <ErrorPanel/> }` wrapping the whole component when the same markup renders the search/filter chrome — split into a chrome component + a data-body component, or branch only inside the body region) and the **persistent notification** section; extend Rules / What NOT to do / Validation; add the shape-failure line.
- [ ] `blazor/skills/component-library/SKILL.md` (+ its per-library references) — the persistent-error call per library: **MudBlazor** `Snackbar.Add(msg, Severity.Error, o => { o.RequireInteraction = true; o.ShowCloseIcon = true; })` with `MudSnackbarProvider` anchored `TopRight`; **Fluent UI** `IToastService.ShowToast` with `Timeout = 0` / `ToastIntent.Error`; **Radzen** `NotificationService.Notify(new NotificationMessage { Severity = Error, Duration = double.MaxValue })`; **none** → a small `NotificationService` + a fixed-position `aria-live` region.
- [ ] `blazor/skills/data-fetching/SKILL.md` — deserialization/shape failure returns a **failed** `Result`, never an empty collection.
- [ ] `blazor/skills/ui-rules/SKILL.md` — renderer-unification section: the shared grid owns loading/failed and takes only the data-dependent body.
- [ ] `blazor/skills/testability/SKILL.md` — `<Region>.Loading|Error|Retry|Empty` + `Notifications.Region|Error|Error.Close|Error.CorrelationId` test ids.
- [ ] `blazor/skills/reviewer/SKILL.md` — the three review checks (scoping, persistent notification, shape-failure-not-empty).
- [ ] `blazor/agents/fe-blazor.md` — Phase 5 self-review prompt: "kill the API and confirm the chrome survives".
- [ ] When `blazor/skills/standards-audit` is authored (per `CONFORMANCE-AUDIT-PLAN.md`), its error-resilience section must carry the J8–J11 equivalents.
- [ ] Update the CLAUDE.md **Frontend code rules** (Blazor) bullet to match the React one.

**React-Native (to do when the node lands):** `error-handling` isn't authored yet — the rule is carried by superseded by `docs/plans/002-mobile-plugins.md` (§6.5) so the skill ships with it. RN deltas to state explicitly: there is no viewport "top-right" on a phone — the notification is a **top-anchored banner inside the safe area** (below the status bar / notch), still no auto-dismiss, still an explicit close control sized to the 44pt touch target, and it must not sit under a translucent header or the keyboard; offline is a first-class failure cause (`@react-native-community/netinfo`), so the failed body distinguishes "offline" from "server error".

### Phase 7 — GAP: the second tier of failure scenarios (research 2026-07-27)

Full findings + sources: **`docs/audits/001-fe-error-resilience-research.md`**. 16 scenarios assessed against the shipped `fe-react` rule set — 8 covered, 11 gaps. The theme: the plugin covers failures that *announce themselves*, and misses the ones that present as a permanent spinner or as silently-wrong data. Applies to `blazor/` identically (deltas noted in the doc) and must be authored into `react-native/`'s `error-resilience` from the start.

Leverage order (each step ends with the matching `code-review` row + `standards-audit` §J check):
- [x] **G1 + G2 (done 2026-07-27, React only)** — request **timeout budget** (`AbortSignal.timeout` + `AbortSignal.any`, slow-tier at ~4s, hard at ~8–10s; a hung request currently spins forever) **and the stale/degraded fourth state** (a failed *refetch* must keep the last good data + mark it stale, not replace a working dashboard with an error panel — this corrects the rule shipped in Phase 6). One pass over `error-handling` + `data-fetching`.
  Landed in: `error-handling` (four-state table + "The fourth state — stale" + "Timeouts" sections, four failure surfaces, rules/anti-patterns/validation/description), `data-fetching` (the `budget()` helper, per-endpoint-class budgets, `TimeoutError` vs `AbortError`, server-side budgets — plus the G5 query-keying one-liner, which sat naturally beside the signal rule), `code-review` (5 rows), `standards-audit` §J **J12–J17**, `test-ids` (`<Region>.Stale`). Blazor + RN still owe the same (Polly/`HttpClient.Timeout` and OTA-skew deltas per the research doc).
- [x] **G3 (done 2026-07-27, React only)** — session expiry mid-session: silent refresh → replay once → **re-auth in place**, never a redirect that discards a dirty form; single-flight refresh, no refresh→401 loop; 403 ≠ 401.
  Landed in: `error-handling` ("Session expiry mid-session" — the 4-rung ladder + related rules: 403≠401, own-API-only, warn-before-deadline with the typing-isn't-idle trap, `returnTo`, RSC 401-JSON-not-redirect, multi-tab broadcast), `auth/auth0-react` (the hand-off note replacing "redirect to `loginWithRedirect`" as the default), `code-review` (3 rows, the redirect-off-401 one **blocker**), `standards-audit` §J **J18–J23**, plus rules/anti-patterns/validation/description/handoffs.
- [x] **G4 (done 2026-07-27, React only)** — deploy **version skew** / `ChunkLoadError`: `deploymentId`, once-only sessionStorage-guarded reload, "new version — reload" via the notification surface, consistent with the SW update lifecycle.
  Landed in: `error-handling` ("Deploy version skew — the tab that outlived its build": the 3-variant symptom table incl. RSC `BUILD_ID` payload skew, framework detection, guarded once-only reload, prompt-vs-force over unsaved work, CDN document-vs-asset caching, long-lived-tab build-id check), `installable-offline-app` (the one-update-affordance handshake, and the explicit note that a non-PWA app has the same problem with no service worker to signal it), `code-review` (2 rows, unguarded reload = **blocker**), `standards-audit` §J **J24–J26**.
- [x] **G5 + G6 + G12 (done 2026-07-27, React only)** — `data-fetching` correctness pass: out-of-order/stale-response race; critical-vs-optional composition (`allSettled`, dependent queries `enabled:false`, partial success); RSC/Server-Action failure scoping (a route-level `error.tsx` violates the scoping rule by construction).
  Landed in: `data-fetching` (the out-of-order/stale-answer rule with the `ignore`-flag cleanup + key-by-every-parameter; a new "Composing several calls — critical vs optional" section incl. `allSettled` over `all`, gated dependent queries that resolve to a state rather than an eternal skeleton, partial-success rendering; and "Failure scoping in the RSC lane" — `<Suspense>`+region boundary or a typed `Result`, Server Actions returning typed errors, `error.tsx` demoted to shell backstop), `code-review` (5 rows), `standards-audit` §E **E10–E14**.
- [x] **G7 + G8 + G9 (done 2026-07-27, React only)** — `error-handling` mutation/retry block: double-submit guard, idempotency key, **optimistic-rollback must notify**, 409/412 conflict UX, honor `Retry-After` on 429, notification-storm suppression + UI-level stop-retrying circuit.
  Landed in: `error-handling` (new "Mutation failures — a write fails differently from a read" section, incl. the **indeterminate-outcome** state for a timed-out write; `Retry-After` + the stop-auto-retrying-after-k circuit in the retry section; "Volume control" — cap the stack, roll up by cause, quiet on circuit-open — in the notification section), `ui-rules` §5 (per-item bulk reporting), `code-review` (6 rows), `standards-audit` §J **J27–J33**.
- [x] **G10 + G11 + G13–G16 (done 2026-07-27, React only)** — third-party dependency failure (flag provider never blocks render; analytics is log-only, payment/embed is user-visible), storage quota/private-mode degradation, stale-tab restore, deleted-entity navigation, multi-tab session sync, hydration mismatch as a reportable production event.
  Landed in: `error-handling` (new "Third-party dependencies" section with the silent-or-loud table; "Gone, not broken — the deleted entity"; hydration mismatches as reportable via `onRecoverableError`), `state-management` (new "Storage can fail — degrade, never crash" + "Multi-tab coordination" sections + rules/anti-patterns), `data-fetching` (stale-tab restore: keep `refetchOnWindowFocus`/`refetchOnReconnect` on, tune `staleTime` instead), `code-review` (4 rows), `standards-audit` §J **J34–J39**.

- [x] **`references/` split (done 2026-07-27)** — `error-handling` had grown to 474 lines. The four *situational* surfaces moved out behind a router table in the SKILL.md: `references/session-and-deploy.md` (session-expiry ladder + version skew — "the app changed underneath you") and `references/writes-and-dependencies.md` (mutation failures + third-party deps). SKILL.md is back to 408 lines and keeps the always-applicable material (surfaces map, boundaries, retry, region states, scoping, notification, empty/gone states). Relative links inside `references/` re-based to `../../`.

**Phase 7 status: complete for React** — 40 §J checks (up from 7), §E 9→15, `code-review` +25 rows. Remaining: the cross-stack port below.

#### Phase 7 — Blazor port (not started; pick up any time)

Same 11 gaps, same leverage order. **Read the React implementations first** — `frontend/react/skills/error-handling/{SKILL.md,references/*}` + `data-fetching` + `state-management` — then translate; the *rules* are identical, only the mechanism differs. Per-file work:

- [ ] `blazor/skills/error-handling/SKILL.md` — the bulk. Add: the **surfaces map** (currently 3, should be 6); the **stale fourth state** (a failed refresh keeps the last good data — Blazor has no TanStack, so this is an explicit `LastGood`/`IsStale`/`LoadedAt` triple on the region's state object, and it's *more* important here because there's no library default doing it for you); **timeouts** (`HttpClient.Timeout` per named client + `CancellationTokenSource.CancelAfter`, linked to the component's disposal token via `CreateLinkedTokenSource` — the analog of `AbortSignal.any`; distinguish a timeout `TaskCanceledException` from a user/dispose cancellation, which is *not* a failure); the **session-expiry ladder**; **version skew**; **third-party dependencies**; **mutation failures**; `Retry-After` + the stop-auto-retrying circuit; notification volume control; the **gone-not-broken** 404 state. Expect to need a `references/` split as React did.
- [ ] `blazor/skills/data-fetching/SKILL.md` — deserialization failure returns a failed `Result` (already flagged in Phase 6); **timeout budgets per endpoint class**; **critical-vs-optional composition** (`Task.WhenAll` throws on the first failure exactly like `Promise.all` — the optional-call rule is identical, using `WhenAll` over already-completed tasks and inspecting each, or per-call try/catch); **dependent chains** must resolve to a state, not an eternal spinner; **stale-tab restore** (no query library, so this is an explicit refresh on circuit resume / `OnAfterRenderAsync` re-entry).
- [ ] `blazor/skills/state-management/SKILL.md` — guarded `localStorage`/`sessionStorage` access (`ProtectedBrowserStorage` still throws through JS interop on quota/private mode, **and** it can't be touched during prerender at all — a double gap); multi-tab session sync.
- [ ] `blazor/skills/ui-rules/SKILL.md` — per-item bulk-write reporting (§5); shared grid owns loading/failed (Phase 6 item).
- [ ] `blazor/skills/reviewer/SKILL.md` — the ~25 review rows, translated.
- [ ] `blazor/skills/test-ids/SKILL.md` — `<Region>.Stale` + the notification ids (Phase 6 item).
- [ ] `auth/auth0-blazor` — the hand-off note that redirect-on-401 is the wrong default (mirror of the `auth/auth0-react` edit).
- [ ] `blazor/skills/installable-offline-app/SKILL.md` — the one-update-affordance handshake.
- [ ] `blazor/agents/fe-blazor.md` — Phase 5 self-review prompts: kill the API, hang the API, expire the session, deploy mid-session.
- [ ] When `blazor/skills/standards-audit` is authored, its §J must carry the J8–J39 equivalents (and §E the E10–E14 ones).

**Blazor-specific deltas worth stating in the skills** (not just translations):
- **Version skew is asymmetric.** Interactive Server: a redeploy drops the circuit and the reconnect path already forces a reload, so skew is mostly self-healing — but the *reconnect modal* must not present a version change as a network blip. WASM: lazy-loaded assemblies and the `blazor.boot.json` resource hashes are exactly the React chunk problem, and a stale `service-worker-assets.js` is the PWA form of it.
- **The circuit is a failure surface React doesn't have** — `error-handling` already covers reconnection; what's missing is the *interaction* with the new rules (an expired session across a reconnect, a version change detected on resume, unsaved work in a component whose circuit dropped).
- **No `AbortSignal`, no TanStack** — every one of the transport rules (timeout composition, ordering by key, keep-previous-data, refetch-on-focus) has to be written out explicitly rather than configured, which makes them *more* likely to be missing in a real codebase and worth stronger severity in the audit.
- **Prerender doubles several rules** — storage access, `window`/browser reads, and JS-interop-backed notifications are all unavailable during prerender; the failure is a first-render exception, not a runtime degradation.

### Verification (after Phases 1–4)
- [ ] `python3` length check: all frontend descriptions ≤ 1000 chars
- [ ] `grep -ri flexinvest .` → no hits in shipped folders
- [ ] Marketplace paths still resolve: every `skills`/`agents` entry for `fe-blazor`/`fe-react` exists on disk
- [ ] `git status` clean of authoring artifacts under `frontend/`
- [ ] Spot-reinstall (or dry-run validate) the two plugins if the vendor-seed registration changed
