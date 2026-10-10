# Mobile lane audit — SkillsLibrary (read-only, 2026-10-10)

Repo: `/Users/aleksandarkotrulev/RiderProjects/SkillsLibrary` @ `2bec288` (clean, master). No repo file was edited.
All paths below are repo-relative. Every finding carries a `file:line` or a URL; registry versions were read live on 2026-10-10.

---

## 0. What is the "mobile plugin" in this repo?

There is **no standalone mobile plugin**. `.claude-plugin/marketplace.json` ships 16 plugins and none is mobile. Mobile is a **lane bundled inside each of `qa-java` / `qa-dotnet` / `qa-typescript`** (`marketplace.json:46-47,60-62,80-81,88,94,127,150` · `:192-193,207-209,228-230,238,245,279,302` · `:344-345,368-370,388-389,395,401,426,450`). It consists of:

- one agent per stack: `qa-mobile-{java,dotnet,typescript}`
- one slash command per stack: `/qa-mobile-<stack>`
- seven per-stack skills: `ui-test-author/appium`, `mobile-app-crawler`, `mobile-screen-explorer`, `mobile-screen-objects`, `mobile-native-features`, `device-cloud`, plus `mobile-project-setup` (dotnet only)
- two shared security skills, `mobile-app-scan` and `mobile-runtime-testing`. These belong to the `qa-security` agent (Step 4c, `qa/_shared/agents/qa-security.md:101`), not to the mobile agents.

Three neighbours touch the lane without belonging to it:

- **Mobile web** belongs to `qa-ui-<stack>`: each mobile agent's description says it does not handle mobile web (`qa/java/agents/qa-mobile-java.md:3`). `qa-ui-*` has no device-emulation guidance at all (see §3).
- **Mobile BDD** belongs to `qa-bdd-typescript` (`qa/typescript/skills/gherkin-step-code/references/cucumberjs-appium.md`).
- `frontend/react-native/` is a planned `fe-react-native` **dev** stack, not a QA one. It is listed as under construction (`CLAUDE.md:199`) and no plugin references it. It holds 5 of 20 planned skills, no agent and a stale `HANDOFF.md`. It was last touched in commit `f40d080 WIP` on 2026-08-21.

In practice, "working on the qa and mobile plugins" means editing the three `qa-*` plugins. The mobile lane is about 9.1k lines over 58 files.

---

## 1. Inventory

### 1.1 Agents and commands

| File | Lines | Steps | Notes |
|---|---|---|---|
| `qa/java/agents/qa-mobile-java.md` | 163 | 1 Foundations · 2 Author · 3 Deep verification · 4 Review (`:115-120`) | Line 13 promises "scaffold → …", but there is no scaffold step or skill |
| `qa/dotnet/agents/qa-mobile-dotnet.md` | 133 | **0 Project scaffold** (`mobile-project-setup`) · 1–4 as Java (`:83-89`) | Only stack with a scaffold step |
| `qa/typescript/agents/qa-mobile-typescript.md` | 163 | 1–4 as Java (`:115-120`) | Line 13 promises "scaffold", which does not exist |
| `qa/{java,dotnet,typescript}/commands/qa-mobile-<stack>.md` | 16 each | Thin wrappers: read the agent file, then follow it | `$ARGUMENTS`; with no task given, runs orientation only |

### 1.2 Skills (per stack)

| Skill | java | dotnet | typescript | Role |
|---|---|---|---|---|
| `ui-test-author/appium` | 269 | 397 + `references/details.md` 132 + 4 `.cs` assets | 256 | Page-object and test conventions (the rulebook) |
| `mobile-screen-explorer` | 184 | 186 | 187 | One screen at a time through the Appium MCP; locator ladder; `missing-testids.md` |
| `mobile-screen-objects` | 122 | 123 | 118 | Turns an explorer inventory into a page-object class |
| `mobile-app-crawler` (+ `references/crawl-policy.md`, `assets/screen-map-template.md`) | 199 | 199 | 199 | Multi-screen walk: CRAWL / RESUME / PROCESS modes. The policy and template files are byte-identical across the three stacks (md5 `1646306e…` and `e68543ec…`) |
| `mobile-native-features` (+ `references/details.md`) | 387 | 380 | 382 | Deep links, permissions, biometrics, push, lifecycle, clipboard, orientation |
| `device-cloud` (+ `references/details.md` for java/dotnet) | 221 | 237 | 387 | BrowserStack App Automate, Sauce RDC, AWS Device Farm |
| `mobile-project-setup` | — | 165 | — | .NET only; no Java or TS equivalent |
| `responsive-testing` (Playwright, owned by `qa-ui-*`) | 243 | 247 | 223 | Viewport breakpoints only; hands device emulation off (§3) |
| `gherkin-step-code/references/cucumberjs-appium.md` | — | — | 143 | CucumberJS + WDIO mobile BDD (owned by `qa-bdd-typescript`) |
| `ui-test-author/review` (Appium rows) | `:111-126` | `:116-132` | `:117-133` | Reviewer smell tables |
| `standards-audit` (mobile scope) | — | `SKILL.md:24-39` | — | .NET only; there is no Java or TS conformance audit |

Shared (cross-stack, `qa-security` Step 4c): `qa/_shared/security-testing/mobile-app-scan/` (SKILL 110 + android/ios/mobsf-static references) and `qa/_shared/security-testing/mobile-runtime-testing/` (SKILL 108 + frida-objection/mobsf-dynamic/traffic-interception references).

### 1.3 `frontend/react-native/`

- Contents: `PLAN.md` (119 lines), `HANDOFF.md` (50), the vendored `vendor/react-native-guidelines/` (Vercel, Jan 2026, 38 rules), and 5 skills: `reference`, `project-scaffold`, `state-management`, `component-library` (+5 refs), `styling`. There is no agent folder.
- Wiring: **no plugin** in `marketplace.json` references it. It is fenced as under construction at `CLAUDE.md:199` and `docs/skills-catalog.md:7`, and README calls it a "parked seed" (`README.md:215,327`).
- State: `PLAN.md:101` shows Node 2 unticked, yet 3 of Node 2's 4 skills exist (`responsive-design` is missing). `HANDOFF.md:3,37` still says "Next session → Node 2". The skills carry **87 broken relative links** to skills that are not written yet, plus links to `design/frontend-design`, which no longer exists (the `design/` folder now has `visual-identity`, `design-tokens`, …). Example: `skills/component-library/SKILL.md:63`.

### 1.4 How the catalog and README describe mobile

- `docs/skills-catalog.md:17,37,58,61-63,93,103`: mobile is presented as a discipline inside each qa plugin. Line 58 names `ui-test-author/reviewer`, but the folder is `ui-test-author/review` (`ls qa/*/skills/ui-test-author/`).
- `README.md:30,37,73,260`: "API / UI / mobile …" per plugin, plus the `/qa-mobile-<stack>` row.

### 1.5 Git history (`git log -- 'qa/*/agents/qa-mobile-*' frontend/react-native …`)

The newest mobile commits are the conformance-sweep tasks: `ab0bfda` S6 (dotnet), `ae0b224` S8 (java) and `47b7b4a` S10 (typescript), all on 2026-09-26, plus `850f4e9` S11 (`qa/_shared`). That sweep fixed plan and gate wording. It did **not** re-pin versions, so the Appium 2.x baseline survived it. The crawler arrived in `0e19773` / `395cf6b` ("Add craw for appium", 2026-07-25). The newest react-native commit is `f40d080 WIP` (2026-08-21).

---

## 2. The agents: steps, skills, tools, evidence

### 2.1 Skills loaded per step (identical in all three agents except .NET's Step 0)

- **Always loaded:** `ep-agent-orientation-cache` and `ep-code-comments`.
- **Brownfield work adds:** `ep-systematic-debugging`, `ep-verify-before-done`, `ep-writing-plans` (`qa-mobile-java.md:18-25`).

| Step | Skills | Exit gate |
|---|---|---|
| 0 (dotnet only) | `mobile-project-setup` | `dotnet build` clean; "Appium 2 + driver installed, `driver doctor` clean" (`qa-mobile-dotnet.md:85`) |
| 1 Foundations | `page-object-design`, `mobile-app-crawler`, `mobile-screen-explorer` + `mobile-screen-objects`, `test-data-builder`, `test-login-tokens`, `device-cloud` or `browser-cloud-setup` | build clean; app installs; one smoke flow green (`qa-mobile-java.md:117`) |
| 2 Author | `ui-test-author/appium`, `mobile-native-features`, `data-driven-testing` | suite green on the target device (`:118`) |
| 3 Deep verification | `network-mocking`, `db-testing/connection`, `email-testing` | green (`:119`) |
| 4 Review | `ui-test-author/review` | no blocker or major rows (`:120`) |

**Never loaded by any mobile agent:** `responsive-testing` (owned by `qa-ui-*`), `mobile-app-scan` / `mobile-runtime-testing` (owned by `qa-security`), `cucumberjs-appium` (owned by `qa-bdd`), and the reporting skills (owned by `qa-reporting-*`). The last one matters for evidence capture (§2.3).

### 2.2 `tools:` frontmatter

All three agents list the same 14 Appium-MCP tools plus core tools (`qa-mobile-java.md:4`, `qa-mobile-dotnet.md:4`, `qa-mobile-typescript.md:4`):

`select_device, appium_session_management, appium_app_lifecycle, appium_get_page_source, appium_find_element, appium_ai, appium_gesture, appium_set_value, appium_get_text, appium_screenshot, appium_mobile_keyboard, appium_alert, appium_context, appium_mobile_device_control`

- **No Playwright MCP tools.** That is correct for native work.
- **Every listed name exists** in `appium-mcp` 1.95.8 (published 2026-10-10; https://github.com/appium/appium-mcp).
- **These real `appium-mcp` tools are missing from the list:** `appium_screen_recording`, `appium_mobile_permissions`, `appium_geolocation`, `appium_orientation`, `appium_mobile_clipboard`, `appium_perform_actions`, `appium_drag_and_drop`, `appium_get_window_size`, `appium_mobile_device_info`, `appium_driver_settings`, `prepare_ios_simulator`, `appium_prepare_ios_real_device`, `generate_locators`, `appium_generate_tests`.
- **The documentation tools are missing too.** The agents and skills tell the model to "prefer" `appium_skills` / `appium_documentation_query` (`qa-mobile-java.md:52`, `qa/java/skills/mobile-screen-explorer/SKILL.md:40`). Those tools come either from a separate `appium-mcp-documentation` server or from `appium-mcp` itself with `APPIUM_MCP_DOCS_ENABLED=true`, and neither is in any agent's tool list. An agent with an explicit `tools:` list cannot call them.

### 2.3 How evidence is captured today

| Evidence | Where | Verdict |
|---|---|---|
| Screenshot while exploring | MCP `appium_screenshot` (`mobile-screen-explorer/SKILL.md:55,81,119`) | OK for exploration. The crawler saves to `docs/app-map/screenshots/<Screen>.png` (`mobile-app-crawler/SKILL.md:99,144`) but never says to set `SCREENSHOTS_DIR`. Without it, `appium-mcp` writes to `os.tmpdir()` (https://github.com/appium/appium-mcp). |
| Screenshot on test failure | **Nowhere in the mobile lane.** `BaseMobileTest` in all three stacks has no failure hook (`qa/java/skills/ui-test-author/appium/SKILL.md:196`, `qa/dotnet/skills/ui-test-author/appium/SKILL.md:123-138`, TS uses `wdio.conf.ts` with no `afterTest`). The reporting skills only show Playwright and Selenium (`qa/reporting/java/skills/test-reports/SKILL.md:99,120-146`, dotnet `:99,120-147`). | **Gap** |
| Screen recording | **Nowhere.** `grep startRecordingScreen\|recording` over `qa/` returns no hit in any mobile file. | **Gap** |
| Device logs (logcat / syslog / crash logs) | **Nowhere.** No `logcat`, `syslog` or `getLogs` in any mobile file, even though UiAutomator2 captures logcat by default (`appium:skipLogcatCapture` defaults to false, https://github.com/appium/appium-uiautomator2-driver#readme). | **Gap** |
| "Attach a screenshot per native-flow result" | Stated as prose only (`qa/java/skills/mobile-native-features/SKILL.md:65,386`, dotnet `:65,379`, TS `:63,381`) | No code |
| Mobile BDD failure screenshot | `cucumberjs-appium.md:110` takes `browser.takeScreenshot()` and **discards the result** | Defect (C17) |
| Device-cloud video | Indirect: the dashboard URL is attached via the reporting peer (`qa/java/skills/device-cloud/SKILL.md:221`); AWS uses `listArtifacts` (`:113`) | Acceptable |
| Gate evidence | Command output text in the output contract (`qa-mobile-java.md:137`) | Text only |

---

## 3. Where mobile touches Playwright

| Topic | Finding | Evidence | Correct and current? |
|---|---|---|---|
| Mobile-web emulation (`devices[...]`, `isMobile`, `hasTouch`, `deviceScaleFactor`, UA) | **No skill covers it.** All three `responsive-testing` skills hand "Real mobile UX (touch, DPR, UA)" to `ui-test-author/playwright`. That skill only mentions `devices['Desktop Chrome']` (TS `:149`); Java and .NET have nothing. `isMobile`, `hasTouch` and `deviceScaleFactor` appear nowhere in `qa/`. | `qa/typescript/skills/responsive-testing/SKILL.md:48,187`; `qa/java/…:48,207`; `qa/dotnet/…:49,211`; grep for `isMobile\|hasTouch` returns nothing | The hand-off goes to a skill that does not cover it (L9) |
| Ownership fence | The mobile agents exclude mobile web and point to `qa-ui-*` (`qa-mobile-java.md:3`, dotnet `:3`, TS `:3`). The `qa-ui-*` agents exclude native mobile (`qa/java/agents/qa-ui-java.md:3`). | — | Fence is consistent, but the mobile-web side is empty |
| Responsive breakpoint testing | BVA at bp−1 / bp, structural geometry, overflow checks, live resize using web-first assertions; no `waitForTimeout` | TS `:16-36`, Java/.NET same shape | The guidance is correct and current. Two defects: an `if` drives the assertions (C10), and the samples call `setViewportSize` in each test, which the skill's own rule forbids (L19) |
| Playwright Android (`_android`, `device.launchBrowser()`, `device.webView()`) | **Absent.** It is experimental, Node.js only (Java, .NET and Python API pages return 404), and needs ADB plus Chrome 105 or later | https://playwright.dev/docs/api/class-android ; `curl` of `/java/docs/api/class-android` and `/dotnet/…` → 404 | Absence is fine for Java/.NET. For TS it is an optional lane (WebView or Android Chrome), worth at most a reference note |
| `connectOverCDP` to Chrome on Android | Absent | grep shows nothing | n/a |
| WebView / hybrid testing | Only .NET has code (`RunInWebView`, `qa/dotnet/skills/ui-test-author/appium/SKILL.md:245-273`). Java and TS have none, yet their native-features skills claim the appium skill covers it (L7). WDIO's own `getContexts` / `switchContext` (match by title or URL) are not used. | https://webdriver.io/docs/api/mobile | Partial. The .NET chromedriver advice is wrong (D9) |
| Mobile web through Appium (`browserName: Chrome/Safari` on a device or farm) | Absent from the mobile lane. `browser-cloud-setup` covers desktop grids. | grep `browserName` | Gap. Real-device mobile web has no owner |

---

## 4. Version-pin inventory

All "current" values were read on 2026-10-10 from registry.npmjs.org, repo1.maven.org, api.nuget.org and pypi.org, as noted.

| File:line | Exact string | Current (2026-10-10) | Verdict |
|---|---|---|---|
| `qa/java/agents/qa-mobile-java.md:3,10,64` | `Appium 2.x + TestNG` | **appium 3.8.0** (2025-08-18 for 3.0.0; 2.x ended at 2.19.0 on 2025-06-01) | **Stale (major)** |
| `qa/java/skills/ui-test-author/appium/SKILL.md:3,8,15` | `Appium 2.x`, `Appium server 2.x` | appium 3.8.0 | Stale |
| `qa/dotnet/skills/ui-test-author/appium/SKILL.md:3,8,16` | `Appium 2.x` | appium 3.8.0 | Stale |
| `qa/typescript/skills/ui-test-author/appium/SKILL.md:10,15,19` | `Appium 2.x`, `appium 2.x` | appium 3.8.0 | Stale |
| `qa/{java,dotnet,typescript}/skills/mobile-screen-explorer/SKILL.md:36/37/37` | `A running **Appium 2.x** server at … 127.0.0.1:4723` | appium 3.8.0; `appium-mcp` embeds UiAutomator2/XCUITest and needs no separate server for local sessions | Stale and misleading |
| `qa/{java,dotnet,typescript}/skills/mobile-app-crawler/SKILL.md:62` | `an Appium 2.x server on http://127.0.0.1:4723` | same | Stale |
| `qa/dotnet/agents/qa-mobile-dotnet.md:85`; `qa/dotnet/skills/mobile-project-setup/SKILL.md:38,160` | `Appium 2 + driver installed`; `appium (npm) 2.x` | 3.8.0 | Stale |
| `qa/dotnet/skills/mobile-project-setup/SKILL.md:39` | `appium-uiautomator2-driver` **`latest 2.x`** | **8.7.0** (2026-09-14). The 2.x line dates from 2022; 4.x was the last to support Appium 2; 5.0.0+ requires Appium 3 | **Badly stale (major)** |
| `qa/dotnet/skills/mobile-project-setup/SKILL.md:40` | `appium-xcuitest-driver` `latest` | 12.16.0 (2026-10-08); 9.x was the last for Appium 2 | OK as written; implicit Appium 3 requirement |
| `qa/dotnet/skills/mobile-project-setup/SKILL.md:48` | `node --version  # 18+ recommended` | Appium 3 engines `^20.19.0 \|\| ^22.12.0 \|\| >=24.0.0`; library policy is Node 24/22; Node 18 is EOL | **Wrong (major)** |
| `qa/typescript/skills/mobile-native-features/SKILL.md:76`; `qa/typescript/skills/bdd-project-scaffold/SKILL.md:161` | `"appium": "^2.11.0"` | 3.8.0 | Stale |
| `qa/java/skills/ui-test-author/appium/SKILL.md:14`; `qa/java/skills/device-cloud/SKILL.md:15`; `qa/java/skills/mobile-native-features/SKILL.md:61` | `io.appium:java-client 9.x` | **10.1.1** (2026-04-20) stable; **11.0.0** (2026-10-07) requires Appium 3 and Selenium ≥4.50 (https://github.com/appium/java-client/blob/master/CHANGELOG.md) | Stale |
| `qa/java/skills/mobile-native-features/SKILL.md:74` | `io.appium:java-client:9.3.0` | 10.1.1 / 11.0.0 | Stale; contradicts `bdd-project-scaffold:21,81` |
| `qa/java/skills/bdd-project-scaffold/SKILL.md:21,81` | `java-client **10.1.1** (Appium 2.x)` | 10.1.1 is current; the "(Appium 2.x)" label is stale | Intra-Java contradiction |
| `qa/java/skills/mobile-native-features/SKILL.md:75-77` | `testng:7.10.2`, `assertj-core:3.26.3`, `allure-testng:2.29.0` | testng 7.12.0; assertj 3.27.7; allure-testng 2.35.5 / 3.0.0 | Stale (minor) |
| `qa/dotnet/skills/ui-test-author/appium/SKILL.md:10,15`; `device-cloud/SKILL.md:15`; `mobile-native-features/SKILL.md:60` | `Appium.WebDriver 8.x … major version tracks Selenium's` | **9.0.0** (2026-09-16); 8.4.0 (2026-09-09). The major does **not** track Selenium: every 8.x/9.x depends on Selenium.WebDriver 4.x (nuget registration) | Stale and factually wrong |
| `qa/dotnet/skills/mobile-native-features/SKILL.md:73-75` | `Appium.WebDriver 8.0.0`, `NUnit 4.2.2`, `Allure.NUnit 2.12.1` | 9.0.0 / NUnit 5.0.0 (4.6.1 on the 4.x line) / Allure.NUnit 2.15.0 | Stale; NUnit contradicts `mobile-project-setup:31` (4.3.2) |
| `qa/dotnet/skills/mobile-project-setup/SKILL.md:31-37` | `NUnit 4.3.2`, `NUnit3TestAdapter 5.0.0`, `Microsoft.NET.Test.Sdk 17.14.1`, `Appium.WebDriver 8.0.0 … depends on Selenium ≥4.36`, `Selenium 4.44.0`, `FluentAssertions 6.12.1` (deliberate), `Allure.NUnit 2.12.1` | NUnit 5.0.0 / adapter 6.3.1 / Test.Sdk 18.10.1 / Appium.WebDriver 9.0.0 / Selenium 4.51.0 / Allure.NUnit 2.15.0. Appium.WebDriver **8.0.0** depends on Selenium **≥4.29**; ≥4.36 only applies from 8.1.0. Selenium.Support stopped being transitive in 6.0.0. | Stale and wrong in places |
| `qa/dotnet/skills/ui-test-author/appium/SKILL.md:14`; `device-cloud/SKILL.md:14`; `mobile-native-features/SKILL.md:59` | `.NET 8` | Library primary is .NET 10 (`CLAUDE.md` version policy; `qa-mobile-dotnet.md:3,10`); `mobile-project-setup:10,30` says net10 | Contradiction |
| `qa/typescript/skills/ui-test-author/appium/SKILL.md:15`; `mobile-native-features/SKILL.md:59,73-75`; `bdd-project-scaffold/SKILL.md:156-160`; `browser-cloud-setup/SKILL.md:16`; `cucumberjs-appium.md:9` | `WebdriverIO 9.x`, `"^9.0.0"` | **webdriverio 10.0.2**. 10.0.0 shipped 2026-10-05 and needs Node ≥22.19. 9.32.0 (2026-09-20) is still maintained; WDIO 9's mobile commands are Appium-3-compatible (v9 `appium.ts:1196-1199`) | Acceptable "supported" lane; add 10 as primary |
| `cucumberjs-appium.md:9` | `@cucumber/cucumber 13.x` | 13.3.0; `@wdio/cucumber-framework` 10.0.1 peers `^13.2.1` | **Current**. The caveat at `:123` holds |
| `qa/typescript/agents/qa-mobile-typescript.md:3,10` | `Node 24` | Appium 3 and WDIO 10 accept it | OK |
| `qa/_shared/security-testing/mobile-app-scan/SKILL.md:13`; `mobile-runtime-testing/SKILL.md:17` | `MobSF v4.4.6` | v4.5.3 (2026-09-21, GitHub releases) | Minor |
| `mobile-runtime-testing/SKILL.md:14-15`; `references/frida-objection.md:3-4` | `Frida 17.16.4`, `objection v1.12.4` | frida 17.23.3 (2026-10-09); objection 1.12.5 (PyPI) | Nit (same major) |
| `mobile-runtime-testing/references/traffic-interception.md:10` | `mitmproxy (8.x)` | **12.2.3** (PyPI). 8.x dates from 2022 | Stale (minor) |
| `frontend/react-native/PLAN.md:15`; `HANDOFF.md:26` | `Expo SDK 56 primary (RN 0.85 …)` | expo 57.0.27 (2026-10-06); react-native 0.87.1 | Nit (unwired stack) |
| Device-cloud SDKs | Java `software.amazon.awssdk:devicefarm` (no version); .NET `AWSSDK.DeviceFarm`; TS `@aws-sdk/client-device-farm`; OkHttp `4.x`; Gson | awssdk devicefarm 2.46.x; AWSSDK.DeviceFarm 4.0.102.6 | Unpinned; fine |

---

## 5. Findings

Severity follows `CLAUDE.md` (blocker / major / minor / nit). The findings are split into three classes: **Data issues** (wrong or stale facts), **Code issues** (sample or template defects) and **Logical conflicts** (contradictions between files, or with the global rules).

### 5.1 Data issues (wrong or stale facts)

| ID | Severity | Location | Issue | Suggested fix |
|---|---|---|---|---|
| D1 | major | §4 rows 1–10 (e.g. `qa-mobile-java.md:3`, `ui-test-author/appium/SKILL.md:15` ×3, `mobile-screen-explorer/SKILL.md:36`, `mobile-project-setup/SKILL.md:38-39`) | The whole lane is keyed to **Appium 2.x**. Appium 3.0.0 shipped 2025-08-18 and 3.8.0 is current. UiAutomator2 ≥5 and XCUITest ≥10 require Appium 3. Appium 3 removed `/appium/app/background`, `/app/reset`, `/device/finger_print`, `/device/open_notifications`, `/device/set_clipboard`, `/start_recording_screen` (now driver extensions), and made the `--allow-insecure` scope prefix mandatory (https://appium.io/docs/en/latest/guides/migrating-2-to-3/). | Make the lane version-aware: **Appium 3 primary, 2.x supported (frozen at 2.19)**. Pin driver majors per server major. Prefer `mobile:` extensions in every sample. |
| D2 | major | `qa/dotnet/skills/mobile-project-setup/SKILL.md:39,48` | "`appium-uiautomator2-driver` latest **2.x**" (current 8.7.0; 2.x is from 2022) and "node **18+** recommended" (Appium 3 requires 20.19, 22.12 or ≥24). | Pin "uiautomator2 8.x (Appium 3) / 4.x (Appium 2)" and "Node 24 (22 supported)". |
| D3 | major | `qa/java/skills/ui-test-author/review/SKILL.md:117,122`; `qa/typescript/…/review/SKILL.md:128`; `qa/dotnet/…/review/SKILL.md:127`; `qa/dotnet/skills/standards-audit/references/conformance-checklist.md:68` | The reviewers push **removed APIs**: `AppiumDriver<MobileElement>` (generics and `MobileElement` were removed in java-client 8), `driver.resetApp()` (removed in java-client 9.0.0 per its CHANGELOG), `driver.reset()` / `ResetApp()` (`/appium/app/reset` was removed in Appium 3; the replacement is `mobile: clearApp`, emulator only). They sit in a **blocker**-severity row. | Replace with "fresh session / `noReset:false` / `mobile: clearApp` (sim/emulator) / `terminateApp`+`activateApp`". Drop `<MobileElement>`. |
| D4 | major | `qa/typescript/skills/device-cloud/SKILL.md:260,283` | The TS remote-run lane schedules `type: 'APPIUM_JAVA_TESTNG'` for a WebdriverIO suite. Device Farm has **`APPIUM_NODE`** (https://docs.aws.amazon.com/devicefarm/latest/APIReference/API_ScheduleRunTest.html). | Use `APPIUM_NODE` + `APPIUM_NODE_TEST_PACKAGE` + a Node test spec. |
| D5 | major | `qa/typescript/skills/ui-test-author/appium/SKILL.md:16,197,202`; `mobile-native-features/SKILL.md:62`; `device-cloud/SKILL.md:19,196,204` | "Mocha (or **Vitest**) with `@wdio/mocha-framework`". The WDIO testrunner supports Mocha, Jasmine and Cucumber only (https://webdriver.io/docs/frameworks). `expect.soft (Vitest)` is not a WDIO pattern. | Mocha (default) / Cucumber. If standalone `remote()` + Vitest is wanted, make it a separate, explicit lane (see L6). |
| D6 | major | `qa/dotnet/skills/ui-test-author/appium/SKILL.md:52`; `qa/*/skills/mobile-screen-explorer/SKILL.md:10,96` | Claims "accessibility id = Android `content-desc` = React Native `testID` … same id both platforms". Since RN 0.64, `testID` is emitted as Android **`resource-id`**, not `content-desc`. `content-desc` comes from `accessibilityLabel`, so `~testID` misses on Android (https://dev.to/nextlevelbeard/an-end-to-the-abuse-of-accessibility-ids-5d2j ; https://discuss.appium.io/t/react-native-ui-element-access-via-testid/7845). UiAutomator2 auto-prefixes `<package>:id/` on id lookups (README, `disableIdLocatorAutocompletion`). Compose `testTag` needs `mapTestTagToResourceId` (driver ≥8.4.0). Confidence is medium (secondary sources); verify on the target RN version. | Ladder per platform: iOS `accessibility id` (= `accessibilityIdentifier`); Android RN/Compose `id` (resource-id). Do not tell devs to put test ids in `accessibilityLabel`, which is screen-reader text. |
| D7 | major | `qa/*/agents/qa-mobile-*.md:4` vs https://github.com/appium/appium-mcp | The agent tool lists omit `appium_screen_recording`, `appium_mobile_permissions`, `appium_geolocation`, `appium_orientation`, `appium_mobile_clipboard`, `generate_locators` and others (§2.2). They also omit the docs tools the agents tell the model to prefer (`qa-mobile-java.md:52`). | Add the tools. Set `APPIUM_MCP_DOCS_ENABLED=true` (with `@appium/mcp-documentation` installed) and list `mcp__appium-mcp__appium_documentation_query` / `appium_skills`, or drop the instruction. |
| D8 | minor | `qa-mobile-java.md:42`, dotnet `:41,48`, TS `:42`; `mobile-screen-explorer/SKILL.md:36-37` ×3 | "appium-mcp, default Appium endpoint `http://127.0.0.1:4723`" and "AI vision needs `AI_VISION_ENABLED=true`". `appium-mcp` embeds drivers; a server is only needed for `remoteServerUrl` sessions. AI vision also needs `AI_VISION_API_BASE_URL` and `AI_VISION_API_KEY` (README). | Correct the prerequisites. Keep the 4723 health check for test runs, not for MCP. |
| D9 | major | `qa/dotnet/skills/ui-test-author/appium/SKILL.md:273` | "set `chromedriverAutodownload=true` in caps". There is no such capability. Autodownload is the server feature flag `--allow-insecure uiautomator2:chromedriver_autodownload` (UiAutomator2 README; Appium 3 requires the scope prefix). | Fix the instruction and mention `appium:chromedriverExecutableDir`. |
| D10 | minor | `qa/java/skills/mobile-native-features/SKILL.md:281`; dotnet `:273`; TS `:272` | The `allowEnrollBiometrics` capability does not exist in the XCUITest capability reference (https://raw.githubusercontent.com/appium/appium-xcuitest-driver/master/docs/reference/capabilities.md). `mobile: enrollBiometric` is enough (execute-methods "mobile: enrollBiometric"). | Delete the cap line. |
| D11 | minor | `qa/java/skills/mobile-native-features/SKILL.md:185-188` (+ dotnet/TS equivalents) | "On a real iOS device … open it through Safari". XCUITest `mobile: deepLink` (driver ≥4.17, Xcode 14.3+, iOS 16.4+) carries no simulator-only restriction, unlike `sendBiometricMatch` / `enrollBiometric`, which say "on Simulator" (execute-methods doc). | Make `mobile: deepLink` primary on both; keep the Safari route as a fallback for iOS <16.4. |
| D12 | minor | `qa/dotnet/skills/ui-test-author/appium/SKILL.md:10`; `mobile-project-setup/SKILL.md:34-35` | "Major version tracks Selenium's"; "8.0.0 depends on Selenium ≥4.36"; "Selenium.Support transitive". All three are false per the nuget registration (8.0.0 → ≥4.29; Support dropped at 6.0.0). | Correct them. |
| D13 | minor | `traffic-interception.md:10`; `mobile-app-scan/SKILL.md:13` | `mitmproxy (8.x)` (current 12.2.3); MobSF 4.4.6 (current 4.5.3). | Re-pin. |
| D14 | minor | §4 (java-client 9.x, testng/assertj/allure, NUnit/adapter/Test.Sdk/Allure.NUnit, WDIO 9 only) | Patch and minor pins are stale; WDIO 10 shipped 2026-10-05. | One version table per stack, re-pinned in a single pass. |
| D15 | minor | 9 files: `qa/{java,dotnet,typescript}/skills/mobile-app-crawler/SKILL.md:198-199`, `…/references/crawl-policy.md:136`, `…/assets/screen-map-template.md:104` (also `qa/_shared/security/SETUP.md:185`) | Leftover tool-call markup `</content>` / `</invoke>` ships inside skill bodies. | Delete the trailing lines. |
| D16 | minor | `docs/skills-catalog.md:58` | Names `ui-test-author/reviewer`; the folder is `review`. | Rename in the catalog. |
| D17 | nit | `qa/dotnet/skills/ui-test-author/appium/SKILL.md:180-186,243` | `mobile: scrollGesture` is described as "scroll … until an element is found" (it scrolls by percent and returns a bool). `TouchAction` is called "deprecated" when it is removed (java-client 11 CHANGELOG; Appium 3 removed `/touch/*`). | Reword. |
| D18 | nit | `README.md:215` | Calls `react-native/` a "parked seed" although it holds 5 authored skills. | Reword. |

### 5.2 Code issues (sample and template defects)

| ID | Severity | Location | Issue | Suggested fix |
|---|---|---|---|---|
| C1 | **blocker** | `qa/dotnet/skills/ui-test-author/appium/assets/page_template.cs:23,28,31,59` | The template **does not compile**: ctor takes `IWebDriver` but the base needs `AppiumDriver` (`:23`); `VerifyPageLoaded` lacks `override` of the abstract member (`:28`); `landmark.IsDisplayed()` should be the `Displayed` property (`:31`); `.GetText()` should be `.Text` (`:59`). It also inlines a locator string (`:59`), has banner comments and TODOs (`:13-58`), and a doc comment saying "returns … or void" (`:46`). | Rewrite from `references/details.md:56-90`; strip the comments. |
| C2 | **blocker** (on current deps) | `qa/java/skills/device-cloud/references/details.md:141-142,160-161` | `org.openqa.selenium.html5.Location` / `LocationContext` were removed in Selenium 4.35.0, and java-client 10 removed its Location APIs (java-client CHANGELOG 10.0.0). With current Selenium the helper fails to compile. Under java-client 11, `AppiumDriver` no longer extends `RemoteWebDriver`, which breaks the `RemoteWebDriver` parameter too. | Use `mobile: setGeolocation` (UiAutomator2 README) / `io.appium.java_client.Location`, typed on `AppiumDriver`. |
| C3 | major | `qa/java/skills/device-cloud/references/details.md:188-198`; `qa/dotnet/skills/device-cloud/references/details.md:186-198` | Test bodies use `try { … } finally { driver.Quit(); }`. That breaks the global rule "A test body contains no try/catch … cleanup … in the teardown hook, never in an inline try/finally". TS does it correctly (`device-cloud/SKILL.md:206-209`). | Move to `@AfterMethod(alwaysRun = true)` / `[TearDown]`. |
| C4 | major | `qa/java/skills/device-cloud/SKILL.md:109`; `qa/dotnet/skills/device-cloud/SKILL.md:128-129`; `qa/typescript/skills/device-cloud/SKILL.md:270` | `putBytesToPresignedUrl` is a silent no-op ("omitted for brevity" / `Task.CompletedTask`). The upload never happens, the poll times out after 5 minutes, and the cause is invisible. That is a fake success. | Implement the PUT (5 lines each) or throw `UnsupportedOperationException` / `NotImplementedException`. |
| C5 | major | `qa/typescript/skills/mobile-native-features/SKILL.md:143` | `driver.setClipboard(text, "plaintext")` passes raw text. WDIO's `setClipboard` requires **base64** content (https://raw.githubusercontent.com/webdriverio/webdriverio/v9/packages/webdriverio/src/commands/mobile/setClipboard.ts lines 9-21). | `Buffer.from(text).toString('base64')`. |
| C6 | minor | `qa/java/skills/mobile-native-features/SKILL.md:134-137`; `qa/typescript/skills/mobile-native-features/SKILL.md:120-123` (dotnet equivalent) | `openDeepLink` always sends `package`, which is wrong for iOS (`bundleId`). The comment points to "per-platform helpers below", which do not exist. | Two intent methods, or pass the key per platform. |
| C7 | minor | ~330 inline-comment lines across mobile samples (e.g. `qa/dotnet/skills/ui-test-author/appium/SKILL.md:70-92,111-133`; `qa/typescript/skills/device-cloud/SKILL.md` 28 lines; `qa/java/skills/mobile-native-features/SKILL.md` 36 lines; `ui-test-author/appium/assets/BaseAppiumPage.cs:26,47`) | Samples the agent copies violate "No inline comments" (`CLAUDE.md` Comments). The model reproduces them, which undercuts the agents' own "Emit no comments" rule (`qa-mobile-java.md:37`). | Strip the samples. Move explanation into the surrounding prose. |
| C8 | minor | `qa/java/skills/ui-test-author/appium/SKILL.md:69-71`; `qa/typescript/skills/ui-test-author/appium/SKILL.md:77-80` | `isElementVisible` either returns `true` or throws on timeout, never `false`. The name lies. The .NET asset does it right (`assets/BaseAppiumPage.cs:41-45`). | Catch `TimeoutException` / `waitForDisplayed({reverse})` and return false, as .NET does. |
| C9 | minor | `qa/java/skills/ui-test-author/appium/SKILL.md:138-153`; `qa/typescript/skills/ui-test-author/appium/SKILL.md:133,151-154` | The scoped component captures the parent element eagerly and calls `parent.findElement` with no wait. It extends `BaseAppiumPage`, so the inherited finders search from the root (an easy way to escape the scope). The TS version casts `el as ChainablePromiseElement` and calls the global `$$` outside `BasePage` (against `:86,222`). Java `OrderRow` has no `verifyPageLoaded` (against `:208`). | See §6.2 for a lazy, waited scoping pattern. |
| C10 | major | `qa/typescript/skills/responsive-testing/SKILL.md:92-98,148`; `qa/java/…:99`; `qa/dotnet/…:99` | `if (width < BREAKPOINTS.md) { expect A } else { expect B }` inside tests breaks "No conditional logic in tests (no if … driving assertions)". | Parameterize with the expected variant as data, e.g. `[{width, visible:'nav-hamburger', hidden:'nav-desktop'}]`. |
| C11 | minor | `qa/dotnet/skills/ui-test-author/appium/SKILL.md:88-90` | Hardcodes `DeviceName = "iPhone 15"` and `platformVersion "17.4"`, against its own rule at `:361`. | Use `Env.DeviceName`, as the asset does (`AppiumDriverFactory.cs:48`). |
| C12 | minor | `qa/dotnet/skills/ui-test-author/appium/SKILL.md:269-270` | The page object calls `Driver.FindElement(By.CssSelector(...))`, against its own rule at `:350`. | Add a base helper. |
| C13 | minor | `qa/dotnet/skills/ui-test-author/appium/references/details.md:14,33,52` vs `assets/BaseAppiumPage.cs:49-59` | The details file uses `ExpectedConditions` (from the unmaintained `DotNetSeleniumExtras`) without its `using`, so it does not compile. The asset it says to "see for the full file" is different code. | Make details.md mirror the asset. |
| C14 | minor | `qa/typescript/skills/ui-test-author/appium/SKILL.md:176,202` | The sample assertion has no `message` (against `:201`). "Aggregate `await Promise.all([...])`" is not a soft assertion: it fails fast and runs WebDriver commands concurrently. | Add the message. Drop the `Promise.all` advice. |
| C15 | minor | `qa/java/skills/mobile-native-features/SKILL.md:69,111-112` | The path says `support/native/` but the package is `support.nativefeatures`. `native` is a reserved Java keyword, so the stated path cannot be a package. | Use `support/nativefeatures/` throughout. |
| C16 | minor | `qa/java/skills/mobile-native-features/SKILL.md:228,237-238`; `references/details.md:52-56` | Commented-out code (`// or: driver.executeScript(...)`); raw `driver.findElement` / `WebDriverWait` with inline locators in test bodies. | Move into `NativeFeatures` intent methods. |
| C17 | minor | `qa/typescript/skills/gherkin-step-code/references/cucumberjs-appium.md:110` | `await browser.takeScreenshot()` result is discarded, so no evidence is attached. | Attach through `this.attach(png, 'image/png')` / the Allure reporter. |
| C18 | nit | `qa/java/skills/mobile-native-features/SKILL.md:273` | The reject path calls `approveFingerprint(99)`, so the method name contradicts the intent. | Add `rejectFingerprint()`. |

### 5.3 Logical conflicts

| ID | Severity | Location | Issue | Suggested fix |
|---|---|---|---|---|
| L1 | major | §2.3 | **There is no failure-evidence contract for Appium**: no screenshot, recording, page source or logcat on failure in any stack. The mobile agents do not load the reporting skills, and the reporting skills only cover Playwright and Selenium. | Add a failure-evidence section to `ui-test-author/appium`'s `BaseMobileTest` in all three stacks (see §6.1) and an Appium row in `qa/reporting/*/test-reports`. |
| L2 | major | `qa/typescript/agents/qa-mobile-typescript.md:30` vs `qa/typescript/skills/ui-test-author/appium/SKILL.md:211,221` and `CLAUDE.md` Test code rules | The agent allows "`browser.pause` only as a documented last resort". The skill bans it outright, as do the global rules ("No `Thread.Sleep` / `await page.waitForTimeout`"). | Delete the agent's exception. |
| L3 | major | `qa/java/skills/ui-test-author/appium/SKILL.md:203,250`; `qa/dotnet/…:57,312,367`; `qa/typescript/…:188,226`; `mobile-screen-explorer/SKILL.md:99,151` ×3; `mobile-screen-objects/SKILL.md:37,89-90,97,103,111` ×3 | Every fallback locator must carry a `// TODO` ("that marker is the contract"). The global Comments rule says "no `TODO`/`FIXME` left behind" (`CLAUDE.md` Comments). | Make `missing-testids.md` the contract and the constant name the marker (`…_XPATH_FALLBACK`). Drop the TODO. |
| L4 | major | `qa/java/skills/ui-test-author/appium/SKILL.md:196,228-230`; `qa/java/skills/page-object-design/SKILL.md:70` vs `CLAUDE.md` "No static mutable state" and `qa/dotnet/skills/ui-test-author/appium/SKILL.md:362` | Java prescribes a static `ThreadLocal<AppiumDriver>` in `AppiumDriverFactory`. .NET forbids static drivers (and the .NET checklist rates them a blocker, `conformance-checklist.md:67`). | Decide once. Either record a sanctioned exception for `ThreadLocal` holders in `CLAUDE.md`, or use an instance field in Java too (TestNG creates one class instance; use `parallel="classes"` or a per-method factory). |
| L5 | major | `qa/java/skills/mobile-native-features/SKILL.md:372`; `qa/typescript/skills/mobile-native-features/SKILL.md:365` vs `qa/java/skills/ui-test-author/appium/SKILL.md` and `qa/typescript/skills/ui-test-author/appium/SKILL.md` (grep `WEBVIEW` and `swipe` → nothing) | Native-features says the appium skill covers "`mobile:` gesture idioms … native↔WEBVIEW context switching". **Java and TS have neither gestures nor WebView switching.** Only .NET does (`:173-273`). | Port the .NET gestures and WebView sections to Java (W3C `PointerInput`, `mobile:`) and TS (`browser.action('pointer')`, `switchContext({title/url})`). |
| L6 | major | `qa/typescript/skills/device-cloud/SKILL.md:21,213` vs `qa/typescript/skills/ui-test-author/appium/SKILL.md:186`; `mobile-screen-objects/SKILL.md:37` | The farm test does `new LoginPage(driver)` with a standalone `remote()` + Vitest session, claiming the page objects "run unchanged". The page objects take no driver and use WDIO's global `$`, which is not bound in standalone mode. | Drive the farm through `wdio.conf.ts` + `@wdio/browserstack-service` (a capabilities array as the matrix), or make the page objects driver-injected everywhere. |
| L7 | major | `qa/dotnet/skills/device-cloud/SKILL.md:20,105,133` | The .NET remote-run lane schedules `APPIUM_JAVA_TESTNG`. Device Farm has **no .NET Appium type** (AWS ScheduleRunTest enum), so the .NET suite cannot "run unchanged on the farm". | State that Device Farm remote-run is unavailable for .NET (use a live-session farm), or document the custom-environment test-spec route as an explicit, unverified deviation. |
| L8 | major | `qa/dotnet/skills/mobile-project-setup/SKILL.md:78-81` vs `qa/dotnet/agents/qa-mobile-dotnet.md:45,58`; `ui-test-author/appium/SKILL.md:23,369` | The scaffold creates `AppiumTests/Screens/` and `Support/AppiumDriverFactory.cs`. Every other .NET file uses `AppiumTests/Pages/`, and the agent's PROCESS-mode backlog check globs `AppiumTests/Pages/`. | Pick `Pages/` (the majority) and fix the scaffold. |
| L9 | major | `responsive-testing/SKILL.md:48` (TS), `:48` (Java), `:49` (.NET) vs `ui-test-author/playwright` ×3 | Device emulation (touch, DPR, UA, `isMobile`) is handed to a skill that does not cover it. With the mobile agents excluding mobile web, **mobile web has no owner**. | Add a "Mobile web" section to `ui-test-author/playwright` ×3: `devices[...]` projects, `isMobile`/`hasTouch`, `tap()`, `geolocation`/permissions, and an honest note that emulation is not a real device. Route real-device mobile web to `device-cloud` with `browserName`. |
| L10 | minor | `qa/java/agents/qa-mobile-java.md:13`; `qa-mobile-typescript.md:13` vs §1.2 | They promise a "scaffold" step, but only .NET has `mobile-project-setup`. Java and TS also have no `standards-audit`, so there is no mobile conformance audit. | Either author `mobile-project-setup` for Java and TS or remove "scaffold" from those agents. |
| L11 | minor | `qa/java/skills/ui-test-author/appium/SKILL.md:146-147,190,202`; dotnet `:299,311`; TS `:176,187` vs `CLAUDE.md` "Page objects expose intent, not selectors" and `qa-mobile-java.md:30` | Accessors return raw `WebElement` / `AppiumElement`, and tests assert on them (`home.profileAvatar().isDisplayed()`). | Expose `isProfileAvatarShown()` / `profileName()`. Keep elements private. |
| L12 | minor | `qa/java/skills/ui-test-author/appium/SKILL.md:183-184,213` vs `qa-mobile-java.md:30` and `CLAUDE.md` Test code rules | The Java skill names tests in camelCase (`successfulLoginLandsOnHome`). The agent and global rules require `Should_X_When_Y`, and Java's own device-cloud and native samples use `Should_…`. | Align on `Should_X_When_Y`. |
| L13 | minor | `qa/java/skills/ui-test-author/review/SKILL.md:120,133`; `qa/java/skills/page-object-design/SKILL.md:87` vs `ui-test-author/appium/SKILL.md:204` | The reviewer and designer say locators are `private static final By`; the authoring skill says `private static final String …_ID`. | Pick one. |
| L14 | minor | `qa/typescript/skills/ui-test-author/review/SKILL.md:121,123` vs `ui-test-author/appium/SKILL.md:46,187` | Reviewer: `BaseMobilePage`, `WebdriverIO.Element`. Author: `BasePage`, `ChainablePromiseElement`. | Align. |
| L15 | minor | `qa/dotnet/skills/ui-test-author/review/SKILL.md:128`; `mobile-project-setup/SKILL.md:120,135,162` vs `ui-test-author/appium/SKILL.md:67,339` | Capability and platform selection is described three ways: `appsettings.<platform>.json`, `dotnet test --filter "Platform=Android"`, and `Env` / `-p:Platform=`. | One mechanism. |
| L16 | minor | `qa/java/skills/mobile-screen-objects/SKILL.md:37`; dotnet/TS equivalents vs `ui-test-author/appium` base classes | They require "native query" finders (`androidUIAutomator`, `iOSClassChain`) through inherited finders, but `BaseAppiumPage` only has accessibility-id, id and XPath finders. | Add `findByAndroidUiAutomator` / `findByIosClassChain` to the base classes. |
| L17 | minor | `qa/dotnet/skills/ui-test-author/appium/SKILL.md:388`; `qa/java/skills/mobile-screen-explorer/SKILL.md:174`; `mobile-app-crawler/SKILL.md:190` ×3; `crawl-policy.md:108` vs `qa-mobile-java.md:36` | They hand off to `qa/manual/test-case-writer` for "authoring the test" and to `bug-report-writer` for crashes. The agents may not load `qa/manual` and route bugs to `qa-test-case-designer`. | Route both to the peer agent. |
| L18 | minor | `qa/java/skills/mobile-native-features/SKILL.md:64` vs `ui-test-author/appium/SKILL.md:216` | AssertJ in native-features versus TestNG `Assert` in the appium skill, within the same suite. | Pick one. |
| L19 | minor | `qa/typescript/skills/responsive-testing/SKILL.md:64-65` vs `:87,144` (same in Java `:63-64` vs `:94,165`; .NET `:66` vs `:94,163`) | The rule says "never `setViewportSize` scattered per test except live-resize specs", but every boundary sample does exactly that. | Use `test.use({ viewport })` per parameter or a project per width class. |
| L20 | minor | `qa/typescript/skills/responsive-testing/SKILL.md:221` | The TS skill cross-references `frontend/blazor/skills/responsive-design`; the TS front-end peer is React. The target is also outside the `qa-typescript` plugin bundle. | Point to `frontend/react/skills/responsive-design` by name only. |
| L21 | minor | `frontend/react-native/PLAN.md:32,92`; `skills/project-scaffold/SKILL.md:145` | RN plans hand E2E (**Maestro/Detox**) to `qa-mobile-typescript`, which is WebdriverIO + Appium only. No Maestro or Detox skill exists in `qa/` (grep shows nothing). `PLAN.md:101` and `HANDOFF.md:37` are stale, and there are 87 broken links. | Decide the RN E2E lane (Appium via WDIO is already there) before resuming Node 2. Refresh PLAN and HANDOFF. |
| L22 | nit | `qa/dotnet/skills/mobile-project-setup/SKILL.md:140` vs `ui-test-author/appium/SKILL.md:317` | "No assertions inside screen objects" conflicts with "`VerifyPageLoaded()` asserts the landmark". | Say "except `VerifyPageLoaded`". |
| L23 | nit | `qa/dotnet/skills/ui-test-author/appium/SKILL.md:396` | The device-farm cross-reference points to `browser-cloud-setup (Step 2)` instead of `device-cloud`. | Fix the reference. |
| L24 | nit | `qa/java/agents/qa-mobile-java.md:149`; TS `:149` | The brownfield "Stack detected" example lists NUnit and .NET in the Java and TS agents. | Use a stack-local example. |

**What looked fine (no finding):** no `Thread.sleep`, `browser.pause(n)`, `waitForTimeout` or `Task.Delay(n)` as a wait in any mobile code sample. Locators are not XPath-heavy (one illustrative XPath per file). OR-assertions are banned explicitly in all three appium skills (`java :218,240`; `dotnet :326,357`; `ts :203,224`). Every `qa/…` path cross-reference in the 44 mobile markdown files resolves (scripted check). The crawler's safe-action policy and PROCESS mode are coherent. The MASVS / MASTG / MASWE spine in the security skills reads as current.

---

## 6. Mobile analogues of the Playwright asks

### 6.1 Screenshots and screen recordings on failure (Appium)

| Piece | Recommended mechanism (Appium 3 era) | Source |
|---|---|---|
| Screenshot on failure | Java: `@AfterMethod(alwaysRun = true)` + `ITestResult.getStatus() == FAILURE` → `((TakesScreenshot) driver).getScreenshotAs(BYTES)` → `Allure.addAttachment`. .NET: `[TearDown]` + `TestContext.CurrentContext.Result.Outcome.Status == TestStatus.Failed` → `Driver.GetScreenshot().AsByteArray`. TS: `afterTest(test, ctx, { passed })` in `wdio.conf.ts` → `browser.takeScreenshot()` → `@wdio/allure-reporter`. Hooks may branch; tests may not. | Pattern mirrors `qa/reporting/java/skills/test-reports/SKILL.md:139-146` |
| Page source on failure | `driver.getPageSource()` attached as XML. This is the mobile equivalent of a DOM snapshot and the best locator-debugging artifact. | — |
| Device logs | Android `driver.manage().logs().get("logcat")` (UiAutomator2 captures by default unless `appium:skipLogcatCapture`); iOS `syslog` / crashlog via `se/log` (Appium 3 moved `/log` to `/se/log`). | UiAutomator2 README; migration guide |
| Screen recording, kept only on failure | Start in setup, stop in teardown, attach only on failure (Playwright's `retain-on-failure`). Android: `mobile: startMediaProjectionRecording` / `stopMediaProjectionRecording` (Android 10+, Appium Settings helper). iOS: `mobile: startXCTestScreenRecording` (Xcode 15 / iOS 17+; real devices on iOS <18 need the `xctest_screen_record` flag), or XCUITest's `startRecordingScreen` / `mobile: startScreenRecording` (still implemented in `lib/commands/recordscreen.ts`). The core `/appium/start_recording_screen` route was removed in Appium 3 and moved into drivers. | UiAutomator2 README §`mobile: startMediaProjectionRecording`; https://raw.githubusercontent.com/appium/appium-xcuitest-driver/master/docs/reference/execute-methods.md ; migration guide |
| Farms | Video and logs are on by default at BrowserStack and Sauce; attach the session URL (already in `device-cloud` → reporting). AWS: `listArtifacts` for video. | `qa/java/skills/device-cloud/SKILL.md:113,221` |
| Agent-side (MCP) | Add `mcp__appium-mcp__appium_screen_recording` (`action: start\|stop`, returns the MP4 path). Set `SCREENSHOTS_DIR=docs/app-map/screenshots` in the MCP config so crawler screenshots land in the repo, not `os.tmpdir()`. | https://github.com/appium/appium-mcp |
| Ownership | `ui-test-author/appium` owns the hook in `BaseMobileTest`; `qa-reporting-<stack>` owns the attach mechanics. Today neither owns it (L1). Recordings can contain PII, so apply the same redaction and retention as HAR files. | — |

### 6.2 Scoping locators to an element ("within an element") for mobile screen objects

- **What exists:** the component-scoped-to-parent pattern (`qa/java/skills/ui-test-author/appium/SKILL.md:133-164`; `qa/dotnet/…/references/details.md:93-128`; `qa/typescript/…/SKILL.md:121-155`; `page-object-design/SKILL.md:45,89`).
- **Mobile-specific problems:**
  - The parent element is captured eagerly. RecyclerView and UITableView recycle cells on scroll, so a held element goes stale (`StaleElementReferenceException`).
  - There is no wait on the child lookup.
  - The component inherits root-scoped finders.
  - The TS version casts away type safety.
- **Proposed pattern** (the equivalent of Playwright's lazy `locator.locator()`):
  1. A component holds a **parent locator** plus a **row key**, never an element, and re-resolves on every call. Java: `wait.until(ExpectedConditions.presenceOfNestedElementLocatedBy(parentBy, childBy))` (Selenium `ExpectedConditions`); .NET: `DefaultWait` resolving `parent.FindElement(child)` inside the lambda; TS: chained, lazy `$('~OrderRow').$('~OrderRow.Title')`.
  2. Pick the row by a **visible key inside it**, keeping the static row id from the house testid rule (no ids or indexes in the locator). TS: `$$('~OrderRow').find(async r => (await r.$('~OrderRow.Number').getText()) === 'A-1001')`.
  3. When the platform can do it in one native query, scope there. Android: `new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().resourceId("…:id/OrderRow").childSelector(…))`. iOS class chain: ``**/XCUIElementTypeCell[`name == "OrderRow"`]/**/XCUIElementTypeStaticText[`name == "OrderRow.Title"`]``.
  4. Components do **not** extend the root page base. Give them a small scoped finder set, plus `verifyPageLoaded` (or remove that rule for components).

### 6.3 WebMCP for mobile

**Not applicable to native apps.** WebMCP is a draft Web Machine Learning CG API (`document.modelContext`) through which a web document registers tools for agents. It has no iOS or Android native surface (https://webmachinelearning.github.io/webmcp/, Draft CG Report 2026-10-09). For mobile it only matters for **mobile web and WebView content**, and then only where the embedded engine implements it. That puts it in `qa-ui-*`'s lane, not `qa-mobile-*`'s.

The native analogue of "the app exposes agent tools" is the `tooling/` lane (`tool-mcp-builder`). The analogue of "an agent drives the app" is the existing `appium-mcp`.

---

## 7. Sources

- Live registries (2026-10-10): https://registry.npmjs.org/appium · /webdriverio · /@wdio/appium-service · /appium-uiautomator2-driver · /appium-xcuitest-driver · /appium-mcp · /@appium/mcp-documentation · /@cucumber/cucumber · /@wdio/cucumber-framework · /expo · /react-native ; https://repo1.maven.org/maven2/io/appium/java-client/maven-metadata.xml (+ selenium-java, testng, assertj-core, allure-testng) ; https://api.nuget.org/v3-flatcontainer/{appium.webdriver,selenium.webdriver,nunit,nunit3testadapter,microsoft.net.test.sdk,allure.nunit,fluentassertions,awssdk.devicefarm}/index.json ; https://api.nuget.org/v3/registration5-semver1/appium.webdriver/index.json ; https://pypi.org/pypi/{mitmproxy,frida,objection}/json ; https://api.github.com/repos/MobSF/Mobile-Security-Framework-MobSF/releases/latest
- Appium 2→3 migration: https://appium.io/docs/en/latest/guides/migrating-2-to-3/
- java-client CHANGELOG: https://github.com/appium/java-client/blob/master/CHANGELOG.md
- Appium .NET client releases: https://github.com/appium/dotnet-client/releases
- appium-mcp README (tool list, `SCREENSHOTS_DIR`, `APPIUM_MCP_DOCS_ENABLED`, AI vision vars, embedded drivers): https://github.com/appium/appium-mcp
- UiAutomator2 README (deepLink, fingerprint, backgroundApp, setGeolocation, startMediaProjectionRecording, `chromedriver_autodownload`, id autocompletion, `mapTestTagToResourceId`): https://raw.githubusercontent.com/appium/appium-uiautomator2-driver/master/README.md
- XCUITest execute methods and capabilities: https://raw.githubusercontent.com/appium/appium-xcuitest-driver/master/docs/reference/execute-methods.md ; https://raw.githubusercontent.com/appium/appium-xcuitest-driver/master/docs/reference/capabilities.md ; `lib/commands/recordscreen.ts`
- WebdriverIO: https://webdriver.io/docs/frameworks ; https://webdriver.io/docs/api/mobile ; v9 `setClipboard` source https://raw.githubusercontent.com/webdriverio/webdriverio/v9/packages/webdriverio/src/commands/mobile/setClipboard.ts ; v9 protocol https://raw.githubusercontent.com/webdriverio/webdriverio/v9/packages/wdio-protocols/src/protocols/appium.ts
- AWS Device Farm ScheduleRunTest: https://docs.aws.amazon.com/devicefarm/latest/APIReference/API_ScheduleRunTest.html
- Playwright Android (Node only; Java, .NET and Python pages 404): https://playwright.dev/docs/api/class-android ; emulation: https://playwright.dev/docs/emulation
- RN testID → resource-id (secondary sources): https://dev.to/nextlevelbeard/an-end-to-the-abuse-of-accessibility-ids-5d2j ; https://discuss.appium.io/t/react-native-ui-element-access-via-testid/7845
- WebMCP draft: https://webmachinelearning.github.io/webmcp/
