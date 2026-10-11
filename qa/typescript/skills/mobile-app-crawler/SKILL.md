---
name: qa-mobile-app-crawler-typescript
description: Use when a TypeScript (WebdriverIO) suite must crawl MANY screens of a live mobile app (Appium MCP) into a resumable screen map. Triggers "crawl the app", "we explored the app already, now build the POMs". Do NOT use for a single screen (`qa-mobile-screen-explorer-typescript`), a screen object (`qa-mobile-screen-objects-typescript`), the folder tree (`qa-page-object-design-typescript`), tests (`qa-ui-test-writer-appium-typescript`), or web apps (`qa-page-objects-from-url-typescript`).
---

# QA — Appium App Crawler (TypeScript)

Walks a live app **screen by screen** across many screens and accumulates one **persistent, resumable screen map** — then detects which elements recur across screens so the page-object tree is designed from evidence instead of guesswork.

This is the multi-screen layer above `qa/typescript/skills/mobile-screen-explorer`. That skill is the single-screen primitive and stays that way: *"one screen per extraction run."* This skill owns everything that spans screens — **the frontier/visited walk, the safe-action policy, the crawl bounds, the accumulated artifact, and cross-screen component detection**. It calls `mobile-screen-explorer` once per screen for the actual element extraction and locator ladder; it never re-derives locator policy.

**It writes no code.** The map is an input to `page-object-design` (structure) and `mobile-screen-objects` (per-screen classes). A crawl that emits a `*Page.ts` has overstepped.

## When to use

- The user wants the whole app — or a whole feature area — inventoried before any page objects exist
- A greenfield mobile suite needs a screen map to design `src/pages/mobile/` from
- **Screens were already captured but never built into page objects** — a map (or loose `mobile-screen-explorer` inventories) is sitting unused and the backlog needs reconciling and driving to page objects → **PROCESS mode**, no re-crawl
- An existing suite must be reconciled against the app as it ships today (which screens have no page object; which page objects point at screens that are gone)
- The team wants one consolidated `missing-testids.md` covering every reachable screen, not one screen at a time

## When NOT to use

- **One screen** → `qa/typescript/skills/mobile-screen-explorer` (don't spin up a crawl for a single extraction)
- Emitting / updating a page-object class → `qa/typescript/skills/mobile-screen-objects`
- Designing where screens/components/flows live → `qa/typescript/skills/page-object-design`
- Writing or tagging the Mocha tests → `qa/typescript/skills/ui-test-author/appium`
- Web apps in a browser → `qa/typescript/skills/page-objects-from-url`
- OS-surface features (permission dialogs, push, deep links, biometrics) → `qa/typescript/skills/mobile-native-features`
- **Fuzzing / monkey-testing for crashes** — this is a *structured inventory* crawl, not a stability sweep. Random-input robustness belongs to `qa/typescript/skills/failure-injection-testing` and the platform monkey tools
- .NET / Java stacks → `qa/dotnet/skills/mobile-app-crawler` / `qa/java/skills/mobile-app-crawler`

## Modes

Decide the mode **before** touching the device — the first act is always to look for `docs/app-map/screen-map.md` and the existing `src/pages/mobile/`.

| Mode | Situation | What runs |
|---|---|---|
| **CRAWL** | No map, or a new scope | Full procedure, steps 1–6 |
| **RESUME** | Map exists, **Status** column still has `frontier` rows, and the walk was cut short (a bound fired, session lost) | Re-orient (see Resumption), continue the walk from the frontier, then steps 5–6 |
| **PROCESS** | Screens are **already captured but never built into page objects** — the map is done (or done enough) and `src/pages/mobile/` is empty, partial, or stale | **No walking at all.** Reconcile (below), then steps 5–6 only |

**PROCESS is the common brownfield case:** someone crawled the app — or hand-captured screens with `mobile-screen-explorer` — and the inventory then sat unused. Do **not** re-crawl to "make sure." The map is the evidence; a device is only needed to re-verify a specific screen whose ids are suspect.

### PROCESS mode — reconcile first

Read the map (plus any loose `docs/app-map/screens/*.md` or `missing-testids.md` sections that were captured without a map — treat those as the inventory and **back-fill a `screen-map.md`** from them so the state is durable). Then diff captured screens against the page objects on disk:

| Bucket | Meaning | Action |
|---|---|---|
| **Mapped, not built** | Screen captured, no `<Screen>Page.ts` | The backlog. Feed to `page-object-design` → `mobile-screen-objects` |
| **Built, not mapped** | Page object exists, no screen in the map | Either a screen the crawl never reached (**coverage gap** — record it) or a dead screen the app removed (**flag, ask before deleting** — never delete a page object tests may call) |
| **Both, drifted** | Both exist, but ids differ | Update mode in `mobile-screen-objects`: upgrade fallback locators the app now exposes ids for, flag changed ids as breaking renames |
| **Both, aligned** | In sync | Nothing to do — say so rather than regenerating |

Report the four bucket counts before proposing any work, and tick the **Handoff status** checklist in `screen-map.md` as each screen is built so the next session inherits the state instead of re-deriving it.

**Staleness gate.** If the app build in the map header differs from what's installed — or the map has no build recorded — say so explicitly. Then either re-verify the affected screens on a device (a short RESUME over just those) or proceed on the user's say-so with the map marked stale in the report. Never present page objects generated from a stale map as verified against the live app.

## Prerequisites

Same as `mobile-screen-explorer` — the **Appium MCP server** connected (it embeds the UiAutomator2 and XCUITest drivers, so a local Android or iOS session needs no separate Appium server; one is needed only for a `remoteServerUrl` session), `SCREENSHOTS_DIR=docs/app-map/screenshots` set in the server's registration so the crawl's screenshots land in the repo instead of `os.tmpdir()`, and a device/emulator with the app running. Load `qa/typescript/skills/mobile-screen-explorer/SKILL.md` before starting: its tool table, session lifecycle, locator ladder, and `missing-testids.md` format are the ones this skill applies per screen.

**PROCESS mode needs none of this** — it reads the existing map and the page objects on disk, so no device, session, or MCP server is required unless a screen must be re-verified.

A crawl is **long-running and stateful**. Before starting, confirm the device won't sleep and the session won't be reclaimed mid-walk — an interrupted crawl is recoverable (see Resumption) but costs a re-orientation pass.

## Inputs needed

Confirm all of these before the first tap. **Ask, don't guess** — a crawl acts on the app, so an assumption here is an action on someone's account. *(CRAWL and RESUME only. PROCESS needs just item 7 — the repo path — plus the app build to check the map against.)*

1. **Scope** — the whole app, or a named feature area (and the screen it starts from)
2. **Account & data** — which test account is logged in, and whether its data is disposable. **A crawl on a real user's account or production data is refused** until the user confirms it is a test account on a non-production environment
3. **Destructive-action policy** — the default denylist (below) plus anything app-specific that must never be tapped
4. **Auth** — credentials if the crawl will cross a login gate, and whether logout is in or out of scope (default: **out**)
5. **Bounds** — max screens, max depth, and a wall-clock time box (defaults below)
6. **Platform + device** — Android/iOS, device/emulator, OS version, app build, orientation. These are recorded in the map header; a map is only evidence for the conditions it was captured under
7. **Target project** — repo path, so the map lands beside the suite and existing page objects can be reconciled

## Procedure

### 1. Set up the map and the frontier

*(CRAWL and RESUME only — in PROCESS mode skip to step 5.)*

- Create `docs/app-map/screen-map.md` from `assets/screen-map-template.md` (or **load the existing one** — see Resumption). Record the capture conditions in its header.
- Seed the **frontier** with the current screen. Maintain three sets for the whole run:
  - **Visited** — signatures already extracted
  - **Frontier** — discovered-but-not-yet-extracted screens, each with the navigation path that reaches it
  - **Blocked** — screens deliberately not entered (denylisted action, out of scope, needs data the account lacks), each with the reason

### 2. Extract the current screen

Run `mobile-screen-explorer`'s procedure against it — screenshot to confirm identity, one `appium_get_page_source` read, classify interactables vs assertion targets, assign each element its locator-ladder rung. Then:

- Compute the **screen signature** (see `references/crawl-policy.md`) and check it against Visited. Already there → this is a **revisit**: don't re-extract, just record the new inbound edge and pop the frontier.
- New signature → write `docs/app-map/screens/<Screen>.md` with the element table, and append the screen's row to `screen-map.md`.
- Append this screen's section to the project-root `missing-testids.md` — **one shared file across the whole crawl**, regenerated section-wise, exactly as `mobile-screen-explorer` defines it. The crawler does not invent a second report.
- Save the screenshot to `docs/app-map/screenshots/<Screen>.png` so a human can audit the naming later.

### 3. Enumerate exits, then walk one

- From the element table, list every element that plausibly **navigates** (buttons, tab-bar items, list rows, nav-bar back/menu). Each becomes a candidate edge.
- **Apply the safe-action policy** (`references/crawl-policy.md`) to every candidate *before* tapping. Denylisted → move to Blocked with the reason; never tap to "see what happens."
- **List rows:** open **one** representative row, not every row — 40 rows of the same detail screen produce one screen, not 40. Record the row count and that only one was opened.
- Tap the chosen candidate, wait for the transition, **re-read the page source** (the previous tree is stale after any interaction), and record the edge as `<from> --[element]--> <to>` in the map.
- **Return to the frontier** with platform back-navigation, then verify by signature that you actually landed where you expected. If back-nav lands somewhere else (a common Android task-stack outcome), record the real edge and re-orient from there rather than assuming.

### 4. Repeat until a stop condition

Stop at the **first** of: frontier empty · max screens reached · max depth reached · time box elapsed · session lost · a denylisted action is the only remaining exit. Record which one fired — a crawl that stopped on its bound is **not** a complete map, and the report must say so.

### 5. Detect components (the payoff)

Across all captured screens, group elements by their **stable id** (iOS accessibility id; Android `resource-id`, else `content-desc`; never group by visible text — text is data, not identity):

| Signal | Reading | Becomes |
|---|---|---|
| Same id on **≥2** screens, same position band | Shared chrome | **Component** candidate (nav bar, tab bar, header, toast, search bar) |
| A repeating sibling group **within** one screen | List/grid row | **Component** scoped to a lazy parent locator plus a row key |
| Same id on **every** screen | App-wide chrome | Component + a candidate member of the base screen class |
| Ids appearing once | Screen-specific | Stays on its screen object |

Write the result to the **Component candidates** section of `screen-map.md` with, per candidate, the id, the screens it appears on, and the count. This is the evidence `page-object-design` needs for its page-vs-component-vs-flow call — the "reused on 2+ pages → component" rule is only trustworthy when someone actually counted.

Also flag **near-duplicate screens** (signatures differing by one or two ids) — usually one screen in two states, not two screens. Propose merging them into one page object with a state variant, and let the user decide.

### 6. Report and hand off

Report: screens captured / blocked / revisited, the stop condition that fired, component candidates ranked by screen count, near-duplicate merges proposed, coverage gaps (what a human must reach manually — paywalls, OTP, states the account can't produce), and the `missing-testids.md` totals.

Then hand off, in order:

1. `qa/typescript/skills/page-object-design` — feed it the map + component candidates; it designs `src/pages/mobile/` (screens, components, flows, base class)
2. `qa/typescript/skills/mobile-screen-objects` — one class per mapped screen, fed the per-screen element table
3. `qa/typescript/skills/ui-test-author/appium` — the tests

## Artifacts

```
docs/app-map/
  screen-map.md              ← the map: header, screen table, edges, components, coverage
  screens/<Screen>.md        ← one per screen: element table + locator rungs (mobile-screen-explorer output)
  screenshots/<Screen>.png   ← visual audit trail
missing-testids.md           ← project root, SHARED with mobile-screen-explorer — appended section-wise
```

Every artifact is **append/update, never overwrite** — a crawl is resumed and re-run, and the map's value is that it accumulates.

## Resumption

A crawl **will** be interrupted (session drop, device sleep, a screen needing manual data entry). It is designed for that:

1. On start, if `docs/app-map/screen-map.md` exists, load it — its Visited signatures and Frontier column *are* the saved state.
2. Re-orient: screenshot, extract, signature. Match against Visited to learn where you are.
3. Continue from the frontier. Never restart the app to "get back to a known state" under `noReset` — that discards the state the map was built against.
4. If the **app build changed** since the last run, the map is stale evidence: say so, re-verify signatures as you revisit, and flag screens whose ids moved.

## Rules

- **Never tap a denylisted action.** The policy in `references/crawl-policy.md` is a hard floor; a real account, a real payment, a real message is not recoverable by re-running. When a candidate is ambiguous, it is **denied** and reported — the crawl never resolves ambiguity by acting.
- **Test account, non-production, confirmed.** No crawl starts otherwise.
- **`mobile-screen-explorer` owns per-screen extraction and the locator ladder** — this skill never writes its own locator policy or a second `missing-testids.md`.
- **Signature, not screenshot, decides identity.** Two captures of the same screen with different data are one screen.
- **Re-read the page source after every interaction** — the tree goes stale on every transition.
- **Re-verify after every back-navigation** — never assume the return landed where you left.
- **A bounded stop is reported as incomplete.** Never present a crawl that hit its screen cap as "the whole app."
- **One representative list row**, never the whole list.
- **Ask, don't guess** — unidentifiable screen, ambiguous action, missing credentials, unexpected state: stop and ask. A crawl that guesses is a crawl that acts on someone's data.
- **No codegen.** No page objects, no tests, no assertions.

## Anti-patterns

- Tapping every button to discover what's destructive (that *is* the destruction)
- Restarting the session or reinstalling the app to reach a "clean" state mid-crawl — wipes the state under `noReset`
- Opening all 40 list rows and recording 40 screens
- Grouping recurring elements by **visible text** — that groups by data and shatters under i18n
- Treating a screen in two states (empty / populated, valid / error) as two screens
- Writing page objects during the crawl, before the structure is designed from the completed map
- Presenting a map that stopped at `maxScreens` as complete coverage
- Crawling a real user's account "just to see the screens"

## Handoffs

- Per-screen extraction, locator ladder, `missing-testids.md` format → `qa/typescript/skills/mobile-screen-explorer` **(load this first)**
- Folder tree / page vs component vs flow, fed by the map → `qa/typescript/skills/page-object-design`
- One page-object class per mapped screen → `qa/typescript/skills/mobile-screen-objects`
- Tests against those screen objects → `qa/typescript/skills/ui-test-author/appium`
- Screens gated behind permissions, push, deep links, biometrics → `qa/typescript/skills/mobile-native-features`
- Turning the map into formal test cases → `qa/manual/test-case-writer`
- Appium environment setup / doctor failures / driver questions → the `@appium/mcp-documentation` server (`appium_skills`, `appium_documentation_query`)
- .NET / Java siblings → `qa/dotnet/skills/mobile-app-crawler` / `qa/java/skills/mobile-app-crawler`

## Reference

- `references/crawl-policy.md` — screen signatures, the safe-action denylist, bounds and defaults, resumption mechanics
- `assets/screen-map-template.md` — the `screen-map.md` artifact template
