# Crawl policy — signatures, safe actions, bounds, resumption

The mechanics behind the crawl loop. Stack-agnostic: identical for the .NET, Java, and TypeScript siblings.

---

## 1. Screen signatures

A crawl must answer "have I been here before?" thousands of times, and must answer it the same way whether the list has 0 items or 400. A **signature** is the answer.

### Compute it from structure, never from data

```
signature = hash(
    platformAnchor          +
    sorted(stableIds of interactable nodes)
)
```

**`platformAnchor`**

| Platform | Anchor | Notes |
|---|---|---|
| Android | current activity name (from the session's `currentActivity`) | Single-Activity apps (most React Native / Compose apps) return the same value for every screen — the anchor is then near-useless and the id set carries the whole signature. That is expected, not a failure |
| iOS | the navigation bar's `name`, else the root window's first `XCUIElementTypeNavigationBar` / `XCUIElementTypeOther` accessibility id | Fall back to the id set alone when no nav bar exists (modals, full-screen media) |

**`stableIds`** — per node, the first available of: iOS `name` (the accessibility id); Android `resource-id`, else `content-desc`. Nodes with none contribute nothing.

### What is deliberately excluded

| Excluded | Why |
|---|---|
| Visible **text** and **values** | It's data. "Orders (3)" and "Orders (0)" are one screen. Also immune to i18n — the same screen in German must not read as new |
| **Bounds / coordinates** | Change with device, orientation, font scale, and keyboard visibility |
| Node **order** | Reorderable content (sorted lists, feeds) would otherwise churn the signature — hence `sorted(...)` |
| **Screenshots** | Never an identity signal. Two pixel-identical captures can be different states; two different captures are routinely one screen |

### Weak-signature fallback

Some screens genuinely expose no stable ids (an unlabelled WebView, a canvas-rendered view). Then:

1. Fall back to the sorted multiset of **element class names + depth**, and mark the screen `⚠ weak signature` in the map.
2. Treat weak-signature matches as **provisional** — confirm with a screenshot and, if still ambiguous, **ask the user** whether it's the same screen.
3. A weak signature is itself a finding: report it as a testability gap alongside the missing accessibility ids. A screen that automation can't identify is a screen tests can't reliably assert they're on.

### Screen vs state variant

Two signatures differing by **one or two ids** are usually **one screen in two states** — populated vs empty, valid vs error, signed-in vs anonymous chrome. Record the second as a **variant** of the first (`LoginScreen [validation-error]`), not a new screen. It becomes one page object with an extra query method, never two classes.

Genuinely different screens differ by most of their id set.

---

## 2. Safe-action policy

The crawler taps things on a live app wired to a live backend. This section is the hard floor, and it is **deny-by-default at every ambiguity**.

### Never tapped — the standing denylist

Match case-insensitively against an element's accessibility id, resource-id, visible text, **and** its `content-desc`, in the app's current locale *and* English:

| Class | Matches include |
|---|---|
| **Money** | pay, purchase, buy, checkout, order (as a submit), subscribe, upgrade, withdraw, transfer, send money, tip, donate, confirm payment |
| **Destruction** | delete, remove, clear, wipe, reset, deactivate, close account, unsubscribe, cancel (a subscription or order — *not* a dialog's "Cancel" dismiss button), archive, block, report |
| **Outbound comms** | send, post, publish, share, invite, submit review, comment, call, email |
| **Session** | log out, sign out, switch account, forget device, revoke |
| **Identity & security** | change password, change email, 2FA setup/disable, biometric enrolment, permission revocation |
| **App state** | factory reset, clear cache/data, restore purchases, install/update |
| **External exits** | anything opening a browser, dialer, store listing, or another app (the crawl loses the app and often the session) |

### Deny-by-default beyond the list

- **Icon-only with no accessibility id and no text** → denied. The most common icon-only buttons are exactly delete, share, and send. Report it as an element needing a `testID`; do not tap to find out.
- **Any dialog offering an irreversible choice** → dismiss via the *negative* option (Cancel / No / Back), never the affirmative. If there is no safe dismiss, record Blocked and ask.
- **Destructive-looking styling** (red, trash icon, "danger" in the id) with a non-destructive label → denied until the user confirms.
- **Form submits** → allowed only when the user explicitly puts that form in scope and supplies the data. A crawl never invents form input and never submits with the account's existing data.

### Allowed by default

Navigation that only changes what is displayed: tab-bar items, list-row opens, back/up, menu opens, expand/collapse, scroll, pull-to-refresh, filter/sort toggles, and read-only detail views.

### Per-app overrides

Take the user's app-specific additions at the start and record them in the map header. The user may **add** denials freely. Removing a standing denial requires them to say so explicitly, per action, and it is recorded in the map header as an override — so a later reader can see why the crawl tapped "Send."

### Escape hatch

If a denied action is the **only** remaining exit from a screen, do not tap it. Record the screen as a coverage gap with the blocking action named, and report that reaching what's beyond needs a human or a purpose-built fixture.

---

## 3. Bounds and defaults

| Bound | Default | Why |
|---|---|---|
| `maxScreens` | **40** | Past ~40 the map outgrows what a single page-object design session can absorb; scope to a feature area instead |
| `maxDepth` | **6** edges from the start screen | Deep chains are usually wizard steps — enumerate those deliberately, not by crawling |
| `timeBox` | **30 min** of wall clock | Sessions get reclaimed; a bounded run that reports honestly beats an open-ended one that dies |
| `rowsPerList` | **1** representative row | 40 rows of one detail screen is one screen |
| `revisitLimit` | **3** inbound edges per screen | After three, stop recording edges to it; the graph is established |
| `settleTimeout` | **10 s** for the post-tap transition | Condition-based (source stabilises), never a fixed sleep |

Every bound is user-overridable at the start and **recorded in the map header**. Whichever bound fires is named in the report — a crawl that stopped at `maxScreens` has produced a partial map and must say so.

### Stop conditions, in precedence order

1. Session lost or app crashed → stop, report the last-known screen and the crash (a crash **is** a finding: hand it to the `qa-test-case-designer` agent, which owns bug reports)
2. Time box elapsed
3. `maxScreens` reached
4. Frontier empty (**the only clean completion**)
5. Every remaining exit is denylisted

---

## 4. Resumption

The map file **is** the saved state — there is no separate cursor.

| Column in `screen-map.md` | Role on resume |
|---|---|
| Signature | Rebuilds the Visited set |
| Status (`captured` / `frontier` / `blocked`) | Rebuilds the frontier and blocked list |
| Path | How to navigate back to a frontier screen |

**On resume:**

1. Load the map. Rebuild Visited / Frontier / Blocked from it.
2. Screenshot → extract → signature the current screen. That tells you where the device actually is, which is frequently *not* where the crawl stopped.
3. Navigate to the nearest frontier entry using its recorded path, verifying by signature at each hop.
4. Continue.

**Never** restart or reinstall the app to reach a known state — under `noReset` that discards exactly the state the map documents.

**Build changed since the last run?** The map is stale evidence. Say so in the report, re-verify each signature as screens are revisited, and flag every screen whose ids moved — a shifted accessibility id is a breaking rename for any page object already built against it.
