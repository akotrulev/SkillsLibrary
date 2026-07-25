---
name: qa-appium-explore-java
description: Use when a Java mobile suite needs to explore the currently open Android/iOS app on a real device or emulator through the Appium MCP server — enumerate elements, derive accessibility-id-first locators, and produce a `missing-testids.md` report for the dev team. Triggers "explore this screen", "what's on the current screen", "find the locators for X", "inventory this app screen". Do NOT use to emit the screen object from that inventory (use `qa-appium-page-object-java`), to author the mobile test itself (use `qa-ui-test-author-appium-java`), for web pages (use `qa-pom-builder-java`), or for non-Java projects (use `qa-appium-explore-{dotnet,typescript}`). For end-to-end suite work prefer the phased agent `qa-mobile-java` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — Appium Live-App Explorer (Java)

Drives the **currently running app on a connected device or emulator through the Appium MCP server**, enumerates what's on screen, and reports each element with an **accessibility-id-first** locator — so `qa/java/skills/appium-page-object` can emit a Java page object and `qa/java/skills/ui-test-author/appium` can author the tests. This skill owns **device interaction, element discovery, and locator policy** — it does **not** generate page objects or tests (hand those off).

This is the mobile counterpart of the web `qa/java/skills/pom-builder`: live extraction via MCP, a primary-locator contract with the dev team, and a `missing-testids.md` report for what the app fails to expose. One difference simplifies the mobile flow — the page-source XML **already contains the accessibility id** (`content-desc` on Android, `name` on iOS, both mapping to a React Native `testID`), so a single page-source read inventories structure *and* ids; there is no separate "harvest the test ids" pass.

## When to use

- The app is open on a device/emulator and the user wants to know what's on the current screen
- Locators must be discovered or verified against the live UI before a page object is built or fixed
- The team wants an inventory of which on-screen elements lack a stable accessibility id (`testID`)
- A flow must be walked on the device (tap/type/swipe) to reveal screens whose elements are then captured

## When NOT to use

- Emitting / updating the Java page object class → `qa/java/skills/appium-page-object`
- Writing or tagging the TestNG tests → `qa/java/skills/ui-test-author/appium`
- Designing where screen objects / components / flows live → `qa/java/skills/page-object-architect`
- Web pages driven in a browser → `qa/java/skills/pom-builder`
- OS-surface features (permission dialogs, push, deep links, biometrics) → `qa/java/skills/mobile-native-features`

## Prerequisites

The **Appium MCP server** must be connected. If its tools (`mcp__appium-mcp__appium_session_management`, `mcp__appium-mcp__appium_get_page_source`, …) are not available, stop and tell the user to add it:

```
claude mcp add appium-mcp -- npx -y appium-mcp@latest
```

- A running **Appium 2.x** server at the default `http://127.0.0.1:4723`, and a device/emulator connected (`adb devices` for Android; a booted simulator / UDID for iOS). Quick health check: `curl -s http://127.0.0.1:4723/status` succeeds and the server's `Available drivers:` log line lists your driver (`uiautomator2` / `xcuitest`).
- `appium_ai` (vision-based natural-language element finding) only works when the server is launched with `AI_VISION_ENABLED=true` — treat it as optional.
- Never start a session blindly — see Session lifecycle.

**Optional companion server — `@appium/mcp-documentation`.** When environment setup or a driver-specific question comes up, the Appium team's docs server answers it authoritatively (`claude mcp add appium-mcp-documentation -- npx -y @appium/mcp-documentation`). Its tools: `appium_skills` (ordered setup/troubleshoot SKILLs by `platform`/`driver`/`mode`) and `appium_documentation_query` (RAG over the official Appium + driver docs). Prefer it over guessing or community forums for setup, doctor failures, and locator-strategy questions.

## Tool reference

| Need | Appium MCP tool |
|------|-----------------|
| Discover / pick device | `mcp__appium-mcp__select_device` |
| Create / attach / list / select / delete a session | `mcp__appium-mcp__appium_session_management` |
| Install / launch / terminate / query app state | `mcp__appium-mcp__appium_app_lifecycle` |
| **Enumerate every element on screen (XML)** | `mcp__appium-mcp__appium_get_page_source` |
| Locate one element by a strategy | `mcp__appium-mcp__appium_find_element` |
| Find an ambiguous element by natural language | `mcp__appium-mcp__appium_ai` *(optional)* |
| Tap / double-tap / long-press / swipe / scroll-to-element | `mcp__appium-mcp__appium_gesture` |
| Enter text | `mcp__appium-mcp__appium_set_value` |
| Read element text (assertions) | `mcp__appium-mcp__appium_get_text` |
| Screenshot to verify visually | `mcp__appium-mcp__appium_screenshot` |
| Hide keyboard / check visibility | `mcp__appium-mcp__appium_mobile_keyboard` |
| Handle an alert dialog | `mcp__appium-mcp__appium_alert` |
| Switch native ↔ webview (hybrid apps) | `mcp__appium-mcp__appium_context` |
| Lock/unlock, shake, open notifications | `mcp__appium-mcp__appium_mobile_device_control` |

## Inputs needed

Confirm before exploring. **Ask, don't guess:**

1. **Platform** — Android, iOS, or both (decides which locator strategies are legal)
2. **App** — package/bundle id and whether a session is already running (default: attach to the live one, preserve state with `noReset`)
3. **Target project** — repo path, so discovered locators match an existing screen-object convention
4. **Scope** — just the current screen, or a flow to walk; how deep into interaction-revealed state (menus, sheets, modals) to go
5. **iOS only** — UDID if not auto-detected

## Procedure

### 1. Session lifecycle

- **Always check for an active session first** (`appium_session_management` → list/select). If one exists, **attach** to it rather than starting a new one — preserve the user's current app state.
- No session → `select_device` to pick the target, then `appium_session_management` to create one with `noReset: true` (don't reinstall/relaunch) and, for Android, `autoGrantPermissions: true`. For iOS supply the `bundleId` and UDID.
- **Closing:** detach (leave the app running) unless the user explicitly wants it killed; killing the app discards the state the next exploration needs.

### 2. Reach the screen

- Confirm what's in front of you with `appium_screenshot` before extracting. If it's the wrong screen, `appium_gesture` / `appium_app_lifecycle` to navigate — or **ask the user**; never extract from a screen you can't identify.

### 3. Enumerate elements — one page-source read

- `appium_get_page_source` returns the screen's XML tree. For each node capture the attributes the element **actually exposes**: **accessibility id** (`content-desc` on Android, `name` on iOS), **platform id** (`resource-id` on Android), visible **`text`/`label`/`value`**, **`class`/type** (→ element type), and `clickable`/`enabled`/`displayed`/`bounds`.
- Read source from the **same conditions the test will run under** — same device/emulator, OS version, app build, orientation, and permission state. A tree captured under different state is not evidence for a different one (Appium XCUITest element-lookup guidance).
- Classify every node as **interactable** (EditText/Button/Switch/`XCUIElementType*Button|TextField|Cell`, anything `clickable=true`) or **visible-informational** (TextView/StaticText/Image the tests will assert on). Drop layout wrappers.
- **Hybrid apps:** if the target lives in a WebView, confirm the active context with `appium_context` first. An element that's only in the WebView DOM won't appear in the `NATIVE_APP` source — switch context before treating it as a locator problem.
- **If a visible element is absent from the source entirely, stop hunting selectors.** Per the Appium team, a missing node is almost always an accessibility, app-state, active-app, or context issue — not locator syntax. Check: is a system alert / share sheet / overlay the active window (`appium_alert`)? Is the app mid-transition? Is accessibility metadata missing in the build? Report that, don't fabricate an XPath.
- Element purpose unclear (icon-only button, blank `content-desc`)? Read its node attributes; still unclear → `appium_ai` with a natural-language description, or **ask the user** before naming anything after it. Never guess what an icon does from its class.

### 4. Locator ladder (the contract)

For every element choose the highest available rung and record the **Java** call. Tie every locator to an attribute you can **see in the current source** — never to a guessed one.

1. `AppiumBy.accessibilityId("…")` — **the default**; `content-desc` / `name` (= RN `testID`). Use it whenever present, even if a nicer id exists. *(On iOS, `id` / `name` / `accessibility id` are synonyms over the element's `name` attribute — confirm it's stable in this app's source before relying on it.)*
2. `By.id("…")` — Android `resource-id` when there's no accessibility id
3. Native query when neither above is stable: `AppiumBy.androidUIAutomator("…")` (Android — useful when ids/accessibility metadata are missing; keep it narrow and log-readable) · `AppiumBy.iOSNsPredicateString("…")` or `AppiumBy.iOSClassChain("…")` (iOS — for native filtering / hierarchy scoping)
4. `By.xpath("…")` — **last resort**, always paired with a `// TODO: missing accessibility id '<suggested>' — see missing-testids.md`. Treat a working XPath as **proof the node exists, not the final fix**: use it to learn the tree, then downgrade to a stronger native locator the moment the source exposes one.

### 5. Report missing accessibility ids

Write/update `missing-testids.md` at the **test project root** — one file, one section per screen, regenerated section-wise each run (reuse the `pom-builder` format):

```markdown
## LoginScreen (extracted 2026-06-05, Pixel 8 / Android 15)

| Element | Type | Visible text / label | Suggested testID | Fallback locator in use |
|---------|------|----------------------|------------------|-------------------------|
| Email field   | EditText | (hint "Email")  | `login-email`  | `By.id("com.app:id/email")` |
| Password reveal | Button | (eye icon, no text) | `login-password-reveal` | `By.xpath("//*[@class='…ImageButton'][2]")` ⚠ brittle |
```

- Suggested ids follow `<screen>-<element>` kebab-case (match the project's existing convention if one exists).
- Elements whose only handle is XPath get a ⚠ — those are the ones to escalate to the RN devs as `testID=` props.

### 6. Reveal dynamic state (only if in scope)

- Interact with `appium_gesture` (tap/swipe) or `appium_set_value`, then **re-read `appium_get_page_source`** — the previous tree is stale after any transition. Record which interaction revealed which elements. Take a screenshot to confirm the new screen.

### 7. Hand off

- Emit/update the page object → `qa/java/skills/appium-page-object` (feed it the element table + locator-ladder rung per element).
- Author tests against it → `qa/java/skills/ui-test-author/appium`.

## Output format

When reporting a screen:

1. **Screen name** (your best identification of the screen)
2. **Element table** — columns: Element · Type · Accessibility id (`testID`) · Resource id · Fallback locator · Java locator call
3. **Missing testIDs** — the `missing-testids.md` section, with ⚠ on XPath-only elements
4. **Suggested next actions** — what to explore, build, or fix next

## Troubleshooting

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| `No active session` | Session not started or timed out | Attach via `appium_session_management`; only create one if none exists |
| `Connection refused` / `curl /status` fails | Appium server not running | Tell the user to start `appium server` on `127.0.0.1:4723`; confirm the driver is in `Available drivers:` |
| Visible element absent from page source | Accessibility / app-state / active-app / context issue — **not** a locator problem | Don't write an XPath. Check for a system alert/overlay (`appium_alert`), wait out a transition, or switch context (hybrid); re-read source |
| Element only in WebView, not native source | Wrong context | `appium_context` → switch to `WEBVIEW_*`, re-read source, then locate |
| Lookup works intermittently / is slow on iOS | Snapshot/tree depth or active-window problem | Confirm the element's attributes in a same-state source dump; consult `appium_documentation_query` (XCUITest element-lookup guide) before tweaking selectors |
| Tap has no effect | Element obscured or off-screen | `appium_screenshot` to verify; `appium_gesture` scroll-to-element first |
| Stale element after navigation | Tree changed between read and act | Re-read `appium_get_page_source` — refs/source are per-screen |

## Rules

- **Accessibility id is the primary locator** for every element that has one — no exceptions, even when a pretty `resource-id` exists. One grep-able convention, immune to i18n and layout churn.
- **Never invent an id that isn't in the tree.** The report *suggests* names; only locate by what the live app exposes today.
- **Every fallback locator carries the `// TODO` marker** — that marker is the contract that it gets upgraded once the devs add the `testID`.
- **Re-read the page source after every interaction or navigation** — the tree goes stale.
- **Ask, don't guess** — unidentified screen, ambiguous element purpose, missing UDID/credentials, unexpected state: stop and ask.
- **Attach, don't restart** — preserve live app state; detach on close, never reinstall under `noReset`.
- **No assertions or test code here** — this skill discovers and reports; codegen is the next two skills' job.
- One screen per extraction run. A flow is a sequence of runs, each with its own report section.

## Anti-patterns

- Starting a fresh session when one is already live (wipes the user's state)
- Emitting `By.xpath`/`resource-id` locators for elements that *have* a `content-desc` — violates the accessibility-id contract
- Dumping every XML node into the report — capture interactables and assertion targets, not layout wrappers
- Guessing what an icon button does from its class name instead of `appium_ai` / asking
- Extracting from a stale page source after a tap (refresh first)
- Writing the page object or tests in the same breath — that's the next skills' job

## Handoffs

- Emit / update the Java page object → `qa/java/skills/appium-page-object`
- Write / tag the TestNG tests → `qa/java/skills/ui-test-author/appium`
- Screen-object architecture (base classes, sub-packages) → `qa/java/skills/page-object-architect`
- OS-surface features (permissions, push, deep links, biometrics) → `qa/java/skills/mobile-native-features`
- Formal test cases the tests are written from → `qa/manual/test-case-writer`
- Appium environment setup / doctor failures / driver-specific questions → the `@appium/mcp-documentation` server (`appium_skills`, `appium_documentation_query`)

## Reference

Authoritative locator guidance distilled into the ladder and troubleshooting above comes from the Appium team's own skills repo and driver docs — consult them (or `appium_documentation_query`) for the full strategy list:

- UiAutomator2 element location & locators — `https://github.com/appium/appium-uiautomator2-driver#element-location`
- XCUITest locator strategies — `https://appium.github.io/appium-xcuitest-driver/latest/reference/locator-strategies/`
- XCUITest element-lookup troubleshooting — `https://appium.github.io/appium-xcuitest-driver/latest/guides/elements-lookup-troubleshooting/`
- Appium skills repo (`appium/skills`) — environment setup + troubleshooting SKILLs, served by `@appium/mcp-documentation`
