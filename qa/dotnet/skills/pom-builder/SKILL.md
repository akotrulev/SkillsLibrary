---
name: qa-pom-builder-dotnet
description: Use when the user gives a website URL or an HTML page and wants a Page Object Model extracted/built/updated from it for a .NET Playwright suite. Triggers: "build a POM from this URL", "extract locators from this page", "update the LoginPage object from the live site". For end-to-end suite work prefer the phased agent `qa-ui-dotnet` / `qa-bdd-dotnet` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — POM Builder from Live Page (.NET)

Builds or updates a **Page Object Model class from a real page** — a live URL driven through the **Playwright MCP server**, or a static HTML file when no environment is reachable. Elements are located by **`data-testid` first** (the standing contract with the dev team); interactable elements missing the attribute are recorded in a `missing-testids.md` report for the developers and given a best-available fallback locator with a `// TODO` marker in the meantime.

Output is a page object per the conventions in `qa/dotnet/skills/ui-test-author/playwright` (.NET 8, `Microsoft.Playwright` async API, `private readonly ILocator` fields + public `ILocator` properties for assertion targets, intent-named methods) — this skill owns **extraction and locator policy**, not test authoring.

## When to use

- The user provides a URL or HTML file and wants a page object created from it
- An existing page object must be reconciled against the current state of a page (elements added/removed/renamed)
- The team wants an inventory of which elements on a page lack `data-testid`

## When NOT to use

- Designing where pages/components/flows live → `qa/dotnet/skills/page-object-architect`
- Writing or tagging the tests that use the POM → `qa/dotnet/skills/ui-test-author/playwright`
- Reviewing an existing page object → `qa/dotnet/skills/ui-test-author/reviewer`
- Java / TypeScript stacks → `qa/java/skills/pom-builder` / `qa/typescript/skills/pom-builder`
- The page is behind auth you have no credentials for, or the URL is unreachable and no HTML was provided → **ask the user**; never fabricate locators

## Prerequisites

The Playwright MCP server must be connected. If its tools (`mcp__playwright__browser_navigate`, `mcp__playwright__browser_snapshot`, `mcp__playwright__browser_evaluate`, …) are not available, stop and tell the user to add it:

```
claude mcp add playwright npx @playwright/mcp@latest -- --caps=testing,storage
```

- `--caps=testing` adds `browser_generate_locator` (server-recommended locator per element)
- `--caps=storage` adds `browser_set_storage_state` / `browser_storage_state` (seed an authenticated session without scripting the login UI)
- The server's test-id attribute defaults to `data-testid`; if the project uses another attribute, pass `--test-id-attribute` and note the deviation. Mirror it in code via `Playwright.Selectors.SetTestIdAttribute("...")` so `GetByTestId` matches.
- Version nuance: current releases target elements via a `target` parameter; older releases used `ref`. Snapshot output emits refs as `[ref=eN]` either way. Refs are only valid within one snapshot — re-snapshot after any navigation or DOM change.

**HTML-file mode**: when the user supplies HTML instead of a URL, skip MCP entirely — parse the markup directly (Read + grep for elements). State clearly in the report that dynamic state (menus, modals, post-JS rendering) was not observed.

## Inputs needed

Confirm before extracting. **Ask, don't guess** — if any of these are unclear, prompt the user:

1. **Page source** — URL (which environment?) or HTML file path
2. **Target project** — repo path; where page objects live (default `Tests/Pages/`)
3. **Auth** — anonymous page, or signed-in (credentials source / storage-state file)
4. **Page name** — what the class should be called (`LoginPage`, `CheckoutOverviewPage`); infer from URL/title and confirm
5. **Dynamic states in scope** — should hidden-until-interaction elements (dropdown panels, modals, accordion bodies) be captured? Default: capture what one click reveals on primary menus; ask before going deeper

## Procedure

### 1. Check for an existing POM

- Glob the target project for `**/Pages/**/*.cs` (and `**/Pom/**/*.cs`) and grep for the page's URL or name.
- **Exists** → this is an **update**: you will diff extracted elements against its current locators (step 5).
- **Doesn't exist** → this is a **create**: if the project has no `Pages/` structure at all, load `qa/dotnet/skills/page-object-architect/SKILL.md` first and lay down the minimal architecture before adding the first page.

### 2. Reach the page

- `mcp__playwright__browser_navigate` to the URL.
- Auth required → prefer `browser_set_storage_state` with a saved session; otherwise drive the login form once (`browser_type` + `browser_click`), and handle JS dialogs via `browser_handle_dialog`. If credentials are missing, **stop and ask**.
- Confirm the right page loaded (snapshot shows the expected heading/landmark) before extracting. Wrong page → ask the user, don't guess.

### 3. Extract elements — two passes, both required

**Pass A — structure** (`mcp__playwright__browser_snapshot`): the accessibility tree gives every element's role, accessible name, and ref. This is the inventory of *what is on the page*: interactables (button, link, textbox, checkbox, radio, combobox, switch, slider, menuitem, tab) and visible informational elements (heading, alert, status, img, significant text).

**Pass B — test ids** (`mcp__playwright__browser_evaluate`): the snapshot **does not contain `data-testid`** — harvest it explicitly:

```js
() => [...document.querySelectorAll('[data-testid]')].map(e => ({
  testid: e.getAttribute('data-testid'),
  tag: e.tagName.toLowerCase(),
  role: e.getAttribute('role'),
  type: e.getAttribute('type'),
  text: e.textContent?.trim().slice(0, 60),
  visible: !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length)
}))
```

Merge the passes by matching text/role/position. Every interactable from Pass A is now either **testid-backed** or **missing a testid**.

- Element purpose ambiguous (icon-only button, unnamed control)? `browser_evaluate` its outerHTML for context; still unclear → **ask the user** what it does before naming a method after it.
- Dynamic states in scope (step 5 of inputs): interact (`browser_click`), **re-snapshot** (old refs are stale), extract the revealed elements, and record which interaction reveals them.
- `browser_generate_locator` (if available) per interactable as a cross-check on your chosen locator.

### 4. Report missing test ids

Write (or update) `missing-testids.md` **at the test project root** — one file for the whole suite, one section per page, regenerated section-wise on each run:

```markdown
# Missing data-testid report

For the dev team: interactable elements that need a `data-testid` attribute.
Until added, the test suite uses fallback locators marked `// TODO` in the page objects.

## LoginPage — /login (extracted 2026-06-05, staging)

| Element | Role | Visible text / label | Suggested testid | Fallback locator in use |
|---------|------|----------------------|------------------|-------------------------|
| Sign-in button | button | "Sign in" | `login-submit` | `GetByRole(AriaRole.Button, name "Sign in")` |
| Password reveal | button | (eye icon, no text) | `login-password-reveal` | CSS `.pwd-field .icon-eye` ⚠ brittle |
```

- Suggested testids follow `<page>-<element>` kebab-case (match the project's existing convention if one exists — check Pass B's harvest first).
- Elements whose only fallback is raw CSS/XPath get a ⚠ — these are the ones to escalate.
- Visible-but-non-interactable elements (headings, icons, static text) that tests will assert on belong in the report too, in a separate "assertion targets" subsection, only if they lack both a testid and a unique role/text handle.

### 5. Build or update the POM

Apply the page-object rules from `qa/dotnet/skills/ui-test-author/playwright` (constructor takes `IPage`, `private readonly ILocator` fields initialized in the constructor, public `ILocator` properties for assertion targets, intent-named `async Task` actions, no assertions in actions). Locator policy for every element:

1. `page.GetByTestId("...")` — **the default**; every testid-backed element uses it
2. Element missing a testid → best fallback in this order: `GetByRole(+Name)` → `GetByLabel` → `GetByPlaceholder` → `GetByText(exact)` → CSS (last resort), **plus** `// TODO: missing data-testid '<suggested>' — see missing-testids.md` on the field

**Update mode**: diff before writing —

- New element on page, not in class → add field + action
- Field in class, element gone from page → flag it in your report and ask before deleting (it may belong to a state you didn't reach)
- Element's testid changed → update the locator, note it as a breaking rename for the team
- Existing fallback locator where a testid now exists → upgrade to `GetByTestId`, drop the TODO, remove the row from `missing-testids.md`
- Never reorder/rename existing public methods that tests already call without flagging it

### 6. Verify and hand off

- `dotnet build` (or project equivalent) → must compile clean.
- If a smoke test exists for the page, run it; if the POM is new, verify the load-assertion landmark against one more live snapshot.
- Report: elements extracted (counts: testid-backed / fallback / ⚠ CSS), POM created or updated (diff summary), `missing-testids.md` path, open questions.
- Test authoring from this POM → `qa/dotnet/skills/ui-test-author/playwright` (tests are written from user-provided test cases in `qa/manual/test-case-writer` format and tagged by area).

## Rules

- **`data-testid` is the primary locator** for every element that has one — no exceptions, even when a pretty `GetByRole` exists. One convention, grep-able, immune to copy and i18n changes.
- **Never invent a testid that isn't in the DOM.** The report *suggests* names; the POM only uses what exists today.
- **Every fallback locator carries the TODO marker** — that marker is the contract that it gets upgraded once the dev team acts on the report.
- **Ask, don't guess** — unclear element purpose, ambiguous page name, unreachable URL, missing credentials, unexpected page state: all stop-and-ask, never improvise.
- Re-snapshot after every interaction or navigation — refs go stale.
- One page object per extraction run. Multi-page sweeps are sequential runs, each with its own report section.
- HTML-file mode cannot see JS-rendered or interaction-revealed elements — say so explicitly in the report rather than implying full coverage.

## Anti-patterns

- Building the POM from the snapshot alone (Pass A) — you'll emit role-based locators for elements that *have* testids, violating the contract
- Dumping every DOM node into the page object — extract what a user can interact with or a test will assert on, not wrapper divs
- Guessing what an icon button does from its CSS class name
- Deleting "stale" fields in update mode without confirming the element isn't state-dependent
- Writing tests in the same breath — that's `ui-test-author/playwright`'s job, after the POM compiles
- Fabricating locators for a page you never actually reached

## Handoffs

- POM architecture (first page in a bare project, splitting a god page) → `qa/dotnet/skills/page-object-architect`
- Writing/tagging tests against the built POM → `qa/dotnet/skills/ui-test-author/playwright`
- Formal test cases the tests are written from → `qa/manual/test-case-writer`
- Reviewing the resulting page object → `qa/dotnet/skills/ui-test-author/reviewer`
- Java / TypeScript siblings → `qa/java/skills/pom-builder` / `qa/typescript/skills/pom-builder`
