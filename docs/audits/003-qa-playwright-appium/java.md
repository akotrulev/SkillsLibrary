# Audit: Playwright in the Java QA lane

**Scope:** `qa/java/agents/*`, `qa/java/commands/*`, every Playwright-bearing file under `qa/java/skills/**` (43 files from `grep -ril playwright qa/java`), `qa/reporting/java/**`, `qa/cicd/java/**`, `qa/_shared/python-web-testing/**`. Selenium/Appium only where they intersect.
**Mode:** read-only. No repo file was edited.
**Date:** 2026-10-10.
**External facts verified this session** (all fetched 2026-10-10):
- playwright.dev/java API pages: `class-locatorassertions`, `class-pageassertions`, `class-page`, `class-websocketroute`, `multithreading`, `test-assertions`, `emulation`, `codegen`, `release-notes`.
- Maven Central `maven-metadata.xml` for `com.microsoft.playwright:playwright`, `com.deque.html.axe-core:playwright`, `io.qameta.allure:allure-testng`, `io.percy:percy-playwright-java` and `com.applitools:eyes-playwright-java5`.
- The `microsoft/playwright-mcp` README.

Severity follows `CLAUDE.md` (blocker / major / minor / nit). Every finding has one class:
- **Data**: a stale version or fact.
- **Code**: wrong example code.
- **Logical**: two sources disagree.

---

## 0. Headline

1. **The default visual-regression tool does not exist in Java.** `playwright-snapshots.md` uses `assertThat(page|locator).hasScreenshot(...)` throughout. Playwright for Java has no screenshot assertion: `LocatorAssertions` has 26 methods and none of them is `hasScreenshot`, and `PageAssertions` has only `hasTitle`, `hasURL` and `matchesAriaSnapshot`. Yet the visual-regression skill sends readers there first ("start here").
2. **The canonical `BaseTest` is not safe to run in parallel.** It keeps `Playwright` and `Browser` in `static` fields and `page` in an instance field. Other skills in the same library tell you to run tests in parallel: `browser-cloud-setup` with `parallel="methods"` and `data-driven-testing` with `@DataProvider(parallel = true)`. Playwright Java is not thread-safe (playwright.dev/java/docs/multithreading). Nine incompatible base-class lifecycles are scattered across the skills.
3. **Evidence capture (trace, screenshot, video) is effectively untaught for the UI agent.**
   - It lives only in `qa/reporting/java/skills/test-reports`, which `qa-ui-java` is forbidden to load.
   - The only snippet calls `tracing().stop()` on a context that `BaseTest` never started tracing.
   - Video and codegen have zero coverage, and `show-trace` has zero hits.
4. **Version drift.**
   - Playwright core is pinned at 1.49.0 in the canonical writer, 1.50.0 at six sites and 1.60.0 in BDD. The current release is **1.63.0** (Maven Central, 2026-09-14).
   - Two Maven snippets use the Gradle-only `4.+` / `5.+` syntax, which Maven cannot resolve.
   - The glob-pattern breaking change is attributed to 1.43; it shipped in **1.52**.
5. **Modern locator and assertion surface is absent.** There is no coverage of:
   - `filter(...)` (and `setVisible`), `and()`, `or()`, `describe()`, `frameLocator` / `contentFrame`, `setTestIdAttribute`;
   - `hasAccessibleName` / `hasRole` / `containsClass`, `matchesAriaSnapshot`;
   - the clock, colorScheme / reducedMotion / geolocation / permissions, device emulation, codegen and WebMCP.

---

## 1. Version-pin inventory

**49 pin sites in scope.** That breaks down as:
- 24 Playwright-family sites: core, Docker image, floors, grid capability, MCP package and companion libraries.
- 14 Allure sites.
- 11 TestNG/AssertJ co-pins inside Playwright-bearing files.

`qa/_shared/python-web-testing` has **zero** pins: no requirements file, no `playwright==`.

### 1a. Playwright core, Docker image, floors, grid, MCP

| # | File:line | Exact string | Note |
|---|---|---|---|
| 1 | `qa/java/skills/ui-test-author/playwright/SKILL.md:57` | `testImplementation("com.microsoft.playwright:playwright:1.49.0")` | Canonical writer is the **oldest** pin; current is 1.63.0 |
| 2 | `qa/java/skills/visual-regression/references/playwright-snapshots.md:41` | `…playwright:1.50.0` | |
| 3 | `qa/java/skills/visual-regression/references/percy.md:48` | `…playwright:1.50.0` | |
| 4 | `qa/java/skills/visual-regression/references/applitools.md:44` | `…playwright:1.50.0` | |
| 5 | `qa/java/skills/accessibility-testing/references/axe-playwright.md:29` | `…playwright:1.50.0` | |
| 6 | `qa/java/skills/accessibility-testing/references/lighthouse-ci.md:46` | `…playwright:1.50.0` | |
| 7 | `qa/java/skills/bdd-project-scaffold/SKILL.md:20` | `` `com.microsoft.playwright:playwright` (**1.60.0**, sync API) `` | |
| 8 | `qa/java/skills/bdd-project-scaffold/SKILL.md:80` | `…playwright:1.60.0` | Newest pin, still 3 minors behind |
| 9 | `qa/java/skills/visual-regression/references/playwright-snapshots.md:251` | `mcr.microsoft.com/playwright/java:v1.50.0-noble` | The same file says at line 250 that the tag "must match your playwright version". It does not match the writer's 1.49.0 (#1) |
| 10 | `qa/java/skills/network-mocking/references/playwright-routes.md:10` | `(sync API, Playwright ≥ 1.49)` | Floor |
| 11 | `qa/java/skills/network-mocking/references/cdp.md:12` | `(sync API, Playwright ≥ 1.49)` | Floor |
| 12 | `qa/java/skills/realtime-stream-testing/SKILL.md:71` | `(≥ **1.48** for routeWebSocket)` | Correct: routeWebSocket shipped in 1.48 |
| 13 | `qa/java/skills/realtime-stream-testing/SKILL.md:190` | `routeWebSocket, ≥ 1.48` | |
| 14 | `qa/java/skills/realtime-stream-testing/SKILL.md:192` | `(Playwright **1.48**)` | |
| 15 | `qa/java/skills/network-mocking/references/playwright-routes.md:327` | `not supported** since Playwright 1.43` | **Wrong.** The release notes say 1.52: "Glob URL patterns … do not support ? and [] anymore" |
| 16 | `qa/java/skills/network-mocking/references/playwright-routes.md:365` | `No glob ?/[abc] since 1.43` | Wrong, as #15 |
| 17 | `qa/java/skills/browser-cloud-setup/references/details.md:83` | `caps.put("client.playwrightVersion", "1.x");` | Placeholder; the comment says "pin … in real config" |
| 18 | `qa/java/skills/page-objects-from-url/SKILL.md:30` | `claude mcp add playwright npx @playwright/mcp@latest -- --caps=testing,storage` | Unpinned `@latest`. The caps are valid per the current README |

### 1b. Companion libraries

| # | File:line | Exact string | Current (Maven Central) | Note |
|---|---|---|---|---|
| 19 | `qa/java/skills/accessibility-testing/references/axe-playwright.md:30` | `com.deque.html.axe-core:playwright:4.+` | 4.13.0 | Dynamic version |
| 20 | `qa/java/skills/accessibility-testing/references/axe-playwright.md:41` | `<version>4.+</version>` | 4.13.0 | **Invalid in Maven.** `+` is Gradle syntax; Maven needs a range such as `[4,5)` or an exact version |
| 21 | `qa/java/skills/visual-regression/references/percy.md:49` | `io.percy:percy-playwright-java:1.2.+` | 1.2.1 | Gradle and Maven lines disagree in style |
| 22 | `qa/java/skills/visual-regression/references/percy.md:59` | `<version>1.2.1</version>` | 1.2.1 | Current |
| 23 | `qa/java/skills/visual-regression/references/applitools.md:45` | `com.applitools:eyes-playwright-java5:5.+` | 5.86.9 | Dynamic version |
| 24 | `qa/java/skills/visual-regression/references/applitools.md:55` | `<version>5.+</version>` | 5.86.9 | **Invalid in Maven**, as #20 |

### 1c. Allure (Playwright attachment path)

| # | File:line | Exact string |
|---|---|---|
| 25 | `qa/java/skills/ui-test-author/playwright/SKILL.md:51` | `id("io.qameta.allure") version "2.11.2"` |
| 26 | `qa/java/skills/ui-test-author/playwright/SKILL.md:59` | `io.qameta.allure:allure-testng:2.27.0` |
| 27 | `qa/java/skills/bdd-project-scaffold/SKILL.md:63` | `id("io.qameta.allure") version "2.12.0"` |
| 28 | `qa/java/skills/bdd-project-scaffold/SKILL.md:85` | `// testImplementation("io.qameta.allure:allure-cucumber7-jvm:2.35.3")` |
| 29 | `qa/reporting/java/skills/test-reports/SKILL.md:28` | `` `io.qameta.allure:allure-testng:2.+` `` |
| 30 | `qa/reporting/java/skills/test-reports/SKILL.md:30` | `` `io.qameta.allure:allure-rest-assured:2.+` `` |
| 31 | `qa/reporting/java/skills/test-reports/SKILL.md:38` | `id("io.qameta.allure") version "2.12.0"` |
| 32 | `qa/reporting/java/skills/test-reports/SKILL.md:43` | `version.set("2.27.0")` |
| 33 | `qa/reporting/java/skills/test-reports/SKILL.md:51` | `io.qameta.allure:allure-testng:2.27.0` |
| 34 | `qa/reporting/java/skills/test-reports/SKILL.md:52` | `io.qameta.allure:allure-rest-assured:2.27.0` |
| 35 | `qa/reporting/java/skills/test-reports/SKILL.md:223` | `…/allure2/releases/download/2.27.0/allure-2.27.0.tgz` |
| 36 | `qa/reporting/java/skills/test-reports/SKILL.md:255` | `…/allure-2.27.0.tgz` |
| 37 | `qa/cicd/java/skills/ci-pipelines/references/azure-pipelines.md:265` | `npm install -g allure-commandline@2.30.0` |
| 38 | `qa/cicd/java/skills/ci-pipelines/references/gitlab-ci.md:250` | `npm i -g allure-commandline@2.30.0` |

Outside strict scope, the same library has more drift: `allure-testng:2.29.0` at `feature-flag-testing/SKILL.md:76`, `failure-injection-testing/SKILL.md:75` and `mobile-native-features/SKILL.md:77`. Maven Central's current `allure-testng` is **3.0.0**; the last 2.x is 2.35.5.

### 1d. TestNG/AssertJ co-pins in Playwright-bearing files

| # | File:line | Exact string |
|---|---|---|
| 39 | `ui-test-author/playwright/SKILL.md:58` | `org.testng:testng:7.10.2` |
| 40 | `ui-test-author/playwright/SKILL.md:60` | `org.assertj:assertj-core:3.26.3` |
| 41 | `visual-regression/references/playwright-snapshots.md:42` | `org.testng:testng:7.10.2` |
| 42 | `visual-regression/references/percy.md:50` | `org.testng:testng:7.+` |
| 43 | `visual-regression/references/applitools.md:46` | `org.testng:testng:7.+` |
| 44 | `accessibility-testing/references/axe-playwright.md:31` | `org.testng:testng:7.+` |
| 45 | `accessibility-testing/references/axe-playwright.md:32` | `org.assertj:assertj-core:3.+` |
| 46 | `accessibility-testing/references/lighthouse-ci.md:47` | `org.testng:testng:7.+` |
| 47 | `accessibility-testing/references/lighthouse-ci.md:48` | `org.assertj:assertj-core:3.+` |
| 48 | `bdd-project-scaffold/SKILL.md:83` | `org.assertj:assertj-core:3.26.3` |
| 49 | `qa/reporting/java/skills/test-reports/SKILL.md:53` | `org.testng:testng:7.10.+` |

### 1e. Inconsistencies

| ID | Sev | Class | Finding |
|---|---|---|---|
| V1 | major | Data / Logical | Four different Playwright pins: **1.49.0** (#1, the canonical writer), **1.50.0** (#2–#6, #9), **1.60.0** (#7–#8), and floors **≥1.48 / ≥1.49** (#10–#14). The current release is **1.63.0**. A suite assembled from several skills gets conflicting coordinates. |
| V2 | major | Code | `<version>4.+</version>` (#20) and `<version>5.+</version>` (#24) are not valid Maven versions, so a Maven build fails dependency resolution. |
| V3 | minor | Data | Glob `?`/`[]` removal is dated "1.43" (#15–#16); the actual release is 1.52. |
| V4 | minor | Logical | The Docker tag `v1.50.0` (#9) does not match the writer's `1.49.0` (#1). The file's own rule (line 250) says they must match; a mismatch means a browser-revision mismatch inside the container. |
| V5 | minor | Data / Logical | Allure drift: Gradle plugin 2.11.2 vs 2.12.0; adapter 2.27.0 vs 2.29.0 vs 2.35.3 vs `2.+`; CLI 2.27.0 vs 2.30.0. Allure 3.0.0 is now current. |
| V6 | minor | Logical | Pinning style is mixed in one family: exact (`1.50.0`), Gradle dynamic (`7.+`, `4.+`, `1.2.+`) and invalid Maven `+`. Dynamic versions make the one-command gate non-reproducible. |
| V7 | minor | Data | Python Playwright is never pinned. `python-web-testing` ships no requirements file and installs nothing explicitly. |
| V8 | nit | Data | `@playwright/mcp@latest` (#18) is unpinned. It is acceptable for an interactive tool, but the `target` vs `ref` nuance documented at line 36 is version-sensitive. |

---

## 2. Capability coverage matrix (Playwright for Java)

Legend: **OK** = correct and current · **Partial** · **Missing** · **Wrong**.

### 2a. Locators

| Capability | Where taught | Status | Note |
|---|---|---|---|
| `getByTestId` | `ui-test-author/playwright/SKILL.md:150,260`; `page-objects-from-url/SKILL.md:113,135` | OK | Testid-first is the house contract |
| `getByRole(AriaRole.X, new Page.GetByRoleOptions().setName(..).setExact(..))` | `ui-test-author/playwright/SKILL.md:153,261,302`; `axe-playwright.md:94` (`Locator.GetByRoleOptions`) | OK | The 1.60 `setDescription` option is not mentioned |
| `getByLabel` / `getByPlaceholder` / `getByText(setExact)` | `ui-test-author/playwright/SKILL.md:262-264` | Partial | Listed in the ladder only; no example |
| `getByAltText` / `getByTitle` | none | Missing | Not in the locator ladder |
| `filter(new Locator.FilterOptions().setHas/HasNot/HasText/HasNotText/setVisible)` | none (0 hits for `FilterOptions`, `setHasText`, `setVisible`) | Missing | The primary "row containing X" idiom. `setVisible` arrived in 1.51 |
| `and()` / `or()` | none | Missing | |
| Chaining (`locator.getByRole(...)`) | `playwright-snapshots.md:129`; `axe-playwright.md:94` | Partial | Used incidentally; never taught as a rule |
| `describe()` | none | Missing | Java 1.53; useful for trace and report readability |
| `frameLocator` / `contentFrame` | none | Missing | No iframe guidance anywhere in the lane |
| Strictness | `ui-test-author/playwright/SKILL.md:302` | Partial | One line about `setExact`. No explanation of strict-mode violations or of `first()`/`nth()` as a smell |
| `nth`/`first` misuse | none (`responsive-testing/SKILL.md:168` uses `cards.first()` legitimately) | Missing | Not in the review list |
| `playwright.selectors().setTestIdAttribute(...)` | none; `page-objects-from-url/SKILL.md:35` covers only the MCP flag `--test-id-attribute` | Missing | The TS sibling mirrors it into code (`qa/typescript/skills/page-objects-from-url/SKILL.md:36`). Java review recommends a `data-test` attribute (`ui-test-author/review/SKILL.md:37`) with no `setTestIdAttribute`, so `getByTestId` would not match |
| Scoping / "within" pattern | `page-object-design/SKILL.md:45,89,157`; `ui-test-author/review/SKILL.md:138` | Partial | Prose only ("component takes a parent `Locator`"); no code. No `filter(setHas)` row scoping |

### 2b. Web-first assertions (`PlaywrightAssertions.assertThat`)

| Capability | Where taught | Status | Note |
|---|---|---|---|
| `isVisible` / `hasText` / `containsText` / `hasCount` / `isEnabled` | `ui-test-author/playwright/SKILL.md:168,198,206-207,282` | OK | |
| Positive preference (`isHidden`, `isDisabled`) | `ui-test-author/playwright/SKILL.md:283,320` | OK | |
| `hasAccessibleName` / `hasAccessibleDescription` / `hasAccessibleErrorMessage` / `hasRole` | none | Missing | Since 1.44 / 1.50. Natural fit for a11y and locator verification |
| `containsClass` | none | Missing | 1.52 |
| `matchesAriaSnapshot` (Locator 1.49, Page 1.60) / `page.ariaSnapshot()` (1.59) | none | Missing | No aria-snapshot coverage anywhere in the lane |
| `hasURL` | `inhouse-framework-conventions/SKILL.md:136` | OK | |
| `hasAttribute` / `hasCSS` | `language-testing/SKILL.md:192,196` | Partial | Line 196 is vacuous: `Pattern.compile(".+")` matches `0px` |
| `assertThat(APIResponse).isOK()` | `ui-test-author/playwright/SKILL.md:251` | Logical conflict | `api-test-author/playwright/SKILL.md:212-213` bans "any 2xx" status checks |
| `setDefaultAssertionTimeout` | `playwright-snapshots.md:73` | OK (API) | Only inside the fabricated visual base class |
| Per-assertion timeout | `ui-test-author/playwright/SKILL.md:287` uses `new AssertOptions()`; `cdp.md:223` uses `new LocatorAssertions.IsVisibleOptions().setTimeout(30_000)` | Wrong / OK | `AssertOptions` does not exist; `cdp.md` has it right |
| Custom failure message | `ui-test-author/playwright/SKILL.md:286`; `ui-test-author/review/SKILL.md:61,153` | Wrong | Java `assertThat` has **no message parameter** (test-assertions page). The example uses `banner.getText()`, a Selenium API (Locator has `textContent()`/`innerText()`), as a one-shot check |

### 2c. TestNG lifecycle and parallelism

| Capability | Where taught | Status | Note |
|---|---|---|---|
| Playwright/Browser per thread | `ui-test-author/playwright/SKILL.md:86-87,94-99` | **Wrong** | `private static Playwright` / `protected static Browser` are built in `@BeforeSuite` and used from `@BeforeMethod`. They are not thread-safe and break the CLAUDE.md:40 no-static-mutable-state rule |
| BrowserContext per test | `ui-test-author/playwright/SKILL.md:105-120` | Partial | Per-method context is right, but `context`/`page` are **instance** fields. With `parallel="methods"`, threads share the instance |
| `ThreadLocal` factory | Demanded at `ui-test-author/review/SKILL.md:135` | Missing | All 16 `ThreadLocal` hits are Selenium/Appium or "no ThreadLocal in glue". No Playwright example |
| `parallel=methods` safety | `browser-cloud-setup/references/details.md:247` (`parallel="methods" thread-count="5"`) with instance fields at 103-105; `data-driven-testing/SKILL.md:283-288` (`parallel = true` rows) | Wrong | Recommended alongside lifecycles that race |
| Lifecycle consistency | 9 variants: `BaseTest` (static, suite scope), `BaseVisualTest` (`@BeforeClass`, `playwright-snapshots.md:68`), `I18nBaseTest` (per-class shared page, `language-testing/references/details.md:32-41`), `GridWebTestBase` (per-method `Playwright.create`), `PlaywrightTestBase` (`inhouse-framework-conventions/SKILL.md:125`), `CdpBaseTest` (`cdp.md:186`), undefined `BasePlaywrightTest` (`axe-playwright.md:108,338`), undefined `BaseUiTest` (`responsive-testing/SKILL.md:85`), per-test `Playwright.create()` in Percy/Applitools (`percy.md:153-160`, `applitools.md:169-175`), and `BaseApiTest` per class (`api-test-author/playwright/SKILL.md:89-119`) | Logical conflict | No single lifecycle source |

### 2d. Evidence capture

| Capability | Where taught | Status | Note |
|---|---|---|---|
| Screenshot on failure | `qa/reporting/java/skills/test-reports/SKILL.md:120-135` | Partial | Uses `page.screenshot()` with defaults. It lives in reporting, which `qa-ui-java` cannot load (`qa-ui-java.md:18`) |
| `Page.ScreenshotOptions` / `Locator.ScreenshotOptions` (`setMask`, `setMaskColor`, `setAnimations`, `setCaret`, `setStyle`, `setFullPage`, `setScale`) | Only inside fabricated `HasScreenshotOptions` (`playwright-snapshots.md:180-221`) | Wrong / Missing | `setStylePath` (`playwright-snapshots.md:205,219`) does not exist on Java `ScreenshotOptions`; only `setStyle(String)` (1.41) does. The real `ScreenshotOptions` are never shown (0 hits) |
| Video (`setRecordVideoDir`/`Size`, `page.video().saveAs()`/`delete()` after context close) | none (0 hits) | Missing | |
| Tracing (`context.tracing().start/stop`, `setPath` only on failure, `startChunk`, `group`) | `test-reports/SKILL.md:130-137` | Partial / Wrong | `stop(setPath)` runs only on failure, so a passing test never stops its trace. `FileInputStream` at line 133 leaks. `BaseTest` never calls `start`, so `stop` throws on every failure. `startChunk`/`group` are missing |
| HAR (`setRecordHarPath`, `routeFromHAR`) | `playwright-routes.md:263-283,348-351` | OK | 1.60 `tracing().startHar()` is not mentioned |
| Allure attachments | `test-reports/SKILL.md:128,132`; `playwright-snapshots.md:285`; `axe-playwright.md:276-286`; `percy.md:257`; `applitools.md:290` | OK (`Allure.addAttachment`) | `@Attachment` is not mentioned (0 hits) |
| TestNG `ITestListener` for on-failure capture | Mentioned only: `inhouse-framework-conventions/SKILL.md:194`, `gitlab-ci.md:215,328` | Missing | No example. `@AfterMethod` ordering against `BaseTest.closeContext()` is never addressed |

### 2e. Network and API

| Capability | Where taught | Status | Note |
|---|---|---|---|
| `route` / `fulfill` / `abort` / `resume` / `fallback`, handler order | `playwright-routes.md:43-56,83-99,331-339` | OK | `resume` vs `continue` and "no `setJson`" are correct |
| `routeFromHAR` record/replay | `playwright-routes.md:259-283,348-351` | OK | |
| `routeWebSocket` | `realtime-stream-testing/SKILL.md:190-211` | **Wrong** | `onMessage` receives a `WebSocketFrame` (verified), so `message.contains(...)` at 202 does not compile |
| `waitForRequest` / `waitForResponse(pred, Runnable)` | `playwright-routes.md:52,169,342`; `ui-test-author/playwright/SKILL.md:292-298` | OK / Wrong | `ui-test-author:294` assigns it to `APIResponse`; it returns `Response` |
| `APIRequestContext` | `api-test-author/playwright/SKILL.md:17-23,76-119` | OK (API) | Thread-safety of per-class contexts under parallel runs is not discussed |
| `context.request()` seeding | `ui-test-author/playwright/SKILL.md:247-253` | Wrong | Relative `/api/orders` with no `setBaseURL` on the context |
| CDP | `cdp.md` | OK (mostly) | `browserName` at 202 is undefined |
| Latency | `playwright-routes.md:55,301-313` | Logical conflict | `Thread.sleep` inside a handler, which `ui-test-author/review` bans |

### 2f. Clock, emulation, aria, tooling

| Capability | Where taught | Status | Note |
|---|---|---|---|
| `page.clock()` | none | Missing | 1.45 (verified). `visual-regression/SKILL.md:38` says "freeze … clocks" with no method |
| Device emulation (Java has **no** `playwright.devices()` registry) | `responsive-testing/SKILL.md:48,207` routes to "Device emulation options in `ui-test-author/playwright`" | Missing (broken reference) | `ui-test-author` has none; 0 hits for `setIsMobile` / `setHasTouch` / `setDeviceScaleFactor` / `setUserAgent` |
| Viewport | `responsive-testing/SKILL.md:63,94,165,179` | OK | |
| colorScheme / reducedMotion | none | Missing | Both matter for visual stabilization |
| locale / timezone | `language-testing/references/details.md:36-39`; `language-testing/SKILL.md:58,270` | OK | |
| geolocation / permissions | none | Missing | |
| Offline | `playwright-routes.md:287-299` | OK | |
| Aria snapshots | none | Missing | |
| Codegen (`mvn exec:java -e -D exec.mainClass=com.microsoft.playwright.CLI -D exec.args="codegen …"`) | none (0 hits) | Missing | The same exec form appears only for `install` at `playwright-snapshots.md:48`, as Maven in a Gradle-default lane |
| Trace viewer (`show-trace`) | Referenced at `ui-test-author/playwright/SKILL.md:325`, `playwright-routes.md:381`, `cdp.md:385` | Missing | Never says how to record or open a trace |
| Browser install in CI | `github-actions.md:263-267`, `gitlab-ci.md:205-206` call `./gradlew :e2e:installPlaywrightBrowsers` | Wrong | Task defined nowhere. The Azure pipeline (library default CI) has no Playwright step (`azure-pipelines.md:200-235`) |
| Playwright MCP tool names | `qa-ui-java.md:4` and `qa-bdd-java.md:4` | OK | 13 tools each: `browser_navigate`, `browser_snapshot`, `browser_evaluate`, `browser_click`, `browser_type`, `browser_fill_form`, `browser_select_option`, `browser_handle_dialog`, `browser_wait_for`, `browser_take_screenshot`, `browser_generate_locator` (testing cap), `browser_set_storage_state` and `browser_storage_state` (storage cap). All exist in the current README |
| MCP usage in the skill | `page-objects-from-url/SKILL.md:27,33-36,60-61,66,68,83-85` | OK | `target` vs `ref` (line 36) matches the README |
| MCP tools absent from the agent | `browser_hover` (hover-revealed menus), `browser_press_key`, `browser_resize`, `browser_tabs`, `browser_navigate_back`, `browser_console_messages`, `browser_network_requests`, `browser_close`, `browser_find` | Partial | The dynamic-state extraction step (`page-objects-from-url/SKILL.md:48,84`) cannot reveal hover menus |
| Playwright test agents (planner / generator / healer) | none | Missing (n/a) | They target `@playwright/test`; worth one line saying Java has none |
| WebMCP | none (0 hits across the **whole repo**) | Missing | |

---

## 3. Anti-patterns and defects found in examples

### Blockers

| ID | Class | Location | Issue | Suggested fix |
|---|---|---|---|---|
| D1 | Code (+Data) | `qa/java/skills/visual-regression/references/playwright-snapshots.md:25-27,152-155,180-191,218-221,327-332`; routed as the default at `visual-regression/SKILL.md:18,26,30` | **Fabricated API.** `assertThat(page|locator).hasScreenshot(...)`, `PageAssertions.HasScreenshotOptions` and `LocatorAssertions.HasScreenshotOptions` do not exist in Playwright Java (verified on the LocatorAssertions and PageAssertions pages and in test-assertions). Baseline auto-creation, `*-snapshots/` naming (92-99) and `*-actual/-expected/-diff.png` output (263) are `@playwright/test` behaviours. Nothing in the reference compiles or produces the described artifacts. | Rewrite: Java has no built-in visual assertion. Either make Percy or Applitools the Java default, or teach `locator.screenshot(new Locator.ScreenshotOptions().setMask(..).setAnimations(DISABLED).setCaret(HIDE).setStyle(..))` plus an explicit image comparator and baseline store. Fix the "start here" routing. |
| D2 | Code / Logical | `qa/java/skills/ui-test-author/playwright/SKILL.md:86-87,94-99,105-120` | **Not parallel-safe.** `Playwright` and `Browser` are `static`, while `context`/`page` are instance fields. Playwright Java requires every object to be used on the thread that created its `Playwright` (multithreading doc). This breaks under `parallel="methods"` (`browser-cloud-setup/references/details.md:247`) or `@DataProvider(parallel = true)` (`data-driven-testing/SKILL.md:283-287`). It also breaks CLAUDE.md:40, and `ui-test-author/review/SKILL.md:135` demands a ThreadLocal factory. | One `ThreadLocal<Playwright>`/`Browser` per worker thread with a fresh `BrowserContext`+`Page` per test (held in ThreadLocals), or state plainly "parallel = classes/instances only". Make this the single lifecycle every specialized skill extends. |

### Major

| ID | Class | Location | Issue | Suggested fix |
|---|---|---|---|---|
| D3 | Code | `browser-cloud-setup/references/details.md:102-105,247` | `GridWebTestBase` keeps `playwright`/`browser`/`page` in instance fields and is paired with `parallel="methods" thread-count="5"`. Concurrent methods overwrite `page`. | Same fix as D2, or `parallel="classes"`. |
| D4 | Code | `ui-test-author/playwright/SKILL.md:294` | `APIResponse resp = page.waitForResponse(...)`. `Page.waitForResponse` returns `Response` (verified), so this does not compile. | `Response resp = …` |
| D5 | Code | `ui-test-author/playwright/SKILL.md:287` | `new AssertOptions().setTimeout(...)` names a class that does not exist. | `new LocatorAssertions.IsVisibleOptions().setTimeout(...)`, as `cdp.md:223` already does. |
| D6 | Code / Logical | `ui-test-author/playwright/SKILL.md:286`; `ui-test-author/review/SKILL.md:61,153` | "Failures name the subject" via `assertEquals(banner.getText(), "Saved", msg)`. `getText()` is Selenium, the check is one-shot (contradicting line 282), and Java `PlaywrightAssertions` has no message overload. The review would flag every web-first assertion as missing a message. | Carve Playwright out of the rule: subject naming via Allure `@Step` names or `Locator.describe()` (1.53). Keep the message rule for AssertJ/TestNG assertions. |
| D7 | Code | `ui-test-author/playwright/SKILL.md:107-111` (no `setBaseURL`) with `:158` `page.navigate("/login")` and `:249` `context.request().post("/api/orders")`; `language-testing/references/details.md:36-38,64`; `language-testing/SKILL.md:252-254` | Relative URLs with no base URL fail with an invalid-URL error, so the canonical example does not run. | Add `.setBaseURL(System.getenv("BASE_URL"))` to `NewContextOptions` in the single `BaseTest`. |
| D8 | Code | `realtime-stream-testing/SKILL.md:201-203` | `ws.onMessage(message -> { if (message.contains("subscribe")) … })`. The handler is `Consumer<WebSocketFrame>` (verified). | `frame -> "subscribe".equals(frame.text())` or `frame.text().contains(...)` |
| D9 | Code | `network-mocking/references/playwright-routes.md:122,131` | `mockApi` is a local in the first test and used undeclared in the second, so it does not compile. | Construct `new MockApi(page)` in each test, per the skill's own rule at 112-114. |
| D10 | Code | `language-testing/references/details.md:32-41` | Context and page are created once per class (`@BeforeClass`) and shared by every test. This breaks test independence (`ui-test-author/playwright/SKILL.md:328`) and the CLAUDE.md "any order" rule. | Per-method context with locale and timezone options, on the shared lifecycle. |
| D11 | Code / Logical | `responsive-testing/SKILL.md:99-105` | `if (width < MD) { assert A } else { assert B }` in the test body breaks CLAUDE.md:96 and the skill's own rule at 226. | Two DataProviders (below-bp, at-bp) or a `(width, expectedVariant)` row. |
| D12 | Logical | `applitools.md:186-194,369-381` | `try { … } finally { eyes.close(false); }` inside `@Test`. CLAUDE.md:94 says cleanup is "never in an inline `try/finally`". | Hold `Eyes` in a field and call `eyes.close(false)` in `@AfterMethod(alwaysRun = true)`. |
| D13 | Code | `accessibility-testing/references/lighthouse-ci.md:166-187` | The test launches Chromium with `--remote-debugging-port`, drives `browser.newPage()` to a signed-in state, then runs `npx lighthouse … --port`. Lighthouse opens and navigates its **own** target in the default browser context, while `browser.newPage()` lives in a new, isolated context. The signed-in state is not what gets audited, and Lighthouse's default storage reset compounds this. Other problems: the fixed port 9222 breaks parallel runs, `try (Playwright …)` sits in the test body, and the URL is hardcoded to `localhost:8080`. | Audit only public pages with LHCI, or pass auth through Lighthouse's own mechanisms (`--extra-headers`, a puppeteer script). State the limitation. |
| D14 | Code | `inhouse-framework-conventions/SKILL.md:102-108` | `page.fill(selector)`, `page.click(selector)` and `page.innerText(selector)` are page-level selector APIs that playwright.dev marks "Discouraged … Use locator-based …". `getErrorMessage()` returns a one-shot `String`, so tests lose auto-wait. | `page.locator(selector("emailInput")).fill(...)`; return a `Locator` for assertions. |
| D15 | Logical / Code | `qa/reporting/java/skills/test-reports/SKILL.md:123-137` vs `ui-test-author/playwright/SKILL.md:117-120` | Several defects in the failure attacher: (a) it needs `page`/`context` open, but `BaseTest.closeContext()` is another `@AfterMethod` with undefined order; (b) `BaseTest` never starts tracing, so `tracing().stop()` throws and masks the real failure; (c) the trace is never stopped on pass; (d) `FileInputStream` leaks at 133. | Own capture inside the one lifecycle: start tracing in `@BeforeMethod`; in a single `@AfterMethod(alwaysRun = true)` stop with `setPath` on failure and without a path on pass; screenshot before `context.close()`; `video().saveAs()` after it. |
| D16 | Code | `playwright-snapshots.md:230-236` | The PDF "baseline" is byte-equality over `page.pdf(...)`. PDFs embed CreationDate and an ID, so this never matches. | Compare extracted text or rendered pages, or drop the example. |
| D17 | Code | `qa/cicd/java/skills/ci-pipelines/references/github-actions.md:266`, `gitlab-ci.md:206` | `./gradlew :e2e:installPlaywrightBrowsers` is defined nowhere in the library (repo-wide grep). `playwright-snapshots.md:48` gives a Maven `exec:java` form instead, in a Gradle-default lane. | Ship the Gradle `JavaExec` task (`mainClass = "com.microsoft.playwright.CLI"`, `args("install","--with-deps","chromium")`) once, in `ui-test-author/playwright`, and reference it. |
| D18 | Logical | `azure-pipelines.md:200-235` | Azure DevOps is the library default CI (`CLAUDE.md:21`), but its UI job is Selenium-only. It has no Playwright browser install and no trace/video artifact. | Add a Playwright-for-Java UI job mirroring `github-actions.md:237-300`. |
| D19 | Logical | `playwright-snapshots.md:243-255` vs `github-actions.md:249`, `gitlab-ci.md:197-206` | The visual skill requires baselines generated and compared "inside the same container CI uses" (`mcr…/playwright/java`), but every CI recipe runs on bare `ubuntu-latest`. Baselines will not match. This persists after D1 is fixed. | Run the UI job in `container: mcr.microsoft.com/playwright/java:v<pinned>-noble`. |
| D20 | Logical | Mandated: `qa-ui-java.md:46`; `ui-test-author/playwright/SKILL.md:152,260,265`; `page-objects-from-url/SKILL.md:8,114,121,137`. Banned: `engineering-practices/code-comments/SKILL.md:16`, `CLAUDE.md:52`, `qa-ui-java.md:36` | The `// TODO: missing data-testid` marker is required by several skills, and a "no TODO / no inline comments" rule is loaded on every run by the same agent. Line 152 even puts the TODO inside a constructor body. | Pick one: record the fallback in `missing-testids.md` only, and make the grep-able marker a named constant or a `@MissingTestId` annotation. Otherwise state the exception in `ep-code-comments`. |
| D21 | Logical | Sanctioned: `playwright-routes.md:55,301-313`; `email-testing/references/gmail-imap.md:200`, `mailpit.md:134`; `test-login-tokens/references/details.md:247`. Banned: `ui-test-author/review/SKILL.md:54,78` ("any literal millisecond sleep … blocker", "anywhere"); `CLAUDE.md:99` | `Thread.sleep` is allowed in some skills and an automatic blocker in the review. Java also runs route handlers on the Playwright dispatch loop, so a sleep there stalls **all** event processing, not just one request. | Add the sanctioned exceptions to the review table. Prefer CDP throttling (`cdp.md`) or a server-side delay for latency. |
| D22 | Logical | See the lifecycle row in §2c | Nine incompatible lifecycles, three of them referencing undefined symbols: `BasePlaywrightTest` (`axe-playwright.md:108,338`), `BaseUiTest` plus `baseUrl` (`responsive-testing/SKILL.md:85,95,166,180`) and `browserName` (`cdp.md:202`). | Every specialized skill extends the single `BaseTest` from `ui-test-author/playwright`. |
| D23 | Logical | `responsive-testing/SKILL.md:48,207` → `ui-test-author/playwright` | Broken reference: device emulation is promised and absent. Java has no device registry (verified on the emulation page). | Add a short emulation section: `setViewportSize`, `setDeviceScaleFactor`, `setIsMobile`, `setHasTouch`, `setUserAgent`, `setColorScheme`, `setReducedMotion`, `setGeolocation`, `setPermissions`. |
| D24 | Logical | `qa/_shared/python-web-testing/SKILL.md:33,64,84-85,93`; `examples/console_logging.py:22,25-26,31`; `examples/static_html_automation.py:17,20-26`; `examples/element_discovery.py:11` | The skill teaches the opposite of every stack rule: `wait_for_load_state('networkidle')` as a "Do", `wait_for_timeout()`, `wait_for_selector()`, and discouraged `page.click('text=…')`/`page.fill`. It writes to `/mnt/user-data/outputs/` (a claude.ai sandbox path), has no version pin and ships `.DS_Store`. It is bundled into `qa-java` (`.claude-plugin/marketplace.json:48`) and reachable only by auto-trigger (`docs/skills-catalog.md:30`). | Rewrite to the house wait rules (`expect(locator).to_be_visible()`, no networkidle or timeouts), fix the output paths, pin `playwright`, delete `.DS_Store`. Or drop it from the plugin. |

### Minor

| ID | Class | Location | Issue |
|---|---|---|---|
| D25 | Data | `playwright-routes.md:327,365` | Glob change dated 1.43; it is 1.52 (V3). |
| D26 | Logical | `ui-test-author/playwright/SKILL.md:215` vs `:308` | "There is no second base class" vs "create a separate base class per role". |
| D27 | Logical | `ui-test-author/playwright/SKILL.md:251` vs `api-test-author/playwright/SKILL.md:212-213` | `assertThat(res).isOK()` (any 2xx) vs "assert the exact status, never `ok()`". |
| D28 | Logical | Naming vs CLAUDE.md:90 and `qa-ui-java.md:30` (`Should_X_When_Y`) | Six styles: `signsInWithValidCredentials` (`ui-test-author/playwright/SKILL.md:193,279`, which mandates it); `rendersEmptyStateWhen…` (`playwright-routes.md:121`); `shouldKeep…When…` (`cdp.md:215`); `Should_match_…_When_…` (`playwright-snapshots.md:147`); `should_push_…` (`realtime-stream-testing/SKILL.md:172`); `should_<outcome>_when_<condition>` (`inhouse-framework-conventions/SKILL.md:129,143`). |
| D29 | Logical | `playwright-snapshots.md:118`, `percy.md:122`, `applitools.md:131` vs `ui-test-author/playwright/SKILL.md:269` | `public final Locator revenueCard` vs "`private final Locator` fields". Also `goto_()` (`playwright-snapshots.md:125`) vs `goTo()`. |
| D30 | Logical | `playwright-routes.md:124,131,134,194,220-222,290-296`; `cdp.md:218,237-239,305`; `axe-playwright.md:187,241,294`; `playwright-snapshots.md:175,182`; `language-testing/SKILL.md:136,144,191-193`; `responsive-testing/SKILL.md:95-98,166-167` | `page.navigate(...)`, `page.getByTestId(...)` and `page.locator(...)` appear directly in test classes, against `ui-test-author/playwright/SKILL.md:274,323-324` and "page objects expose intent". |
| D31 | Logical | `playwright-routes.md:28-29,321,388-389`; `cdp.md:3,28,30,389,392`; `proxy.md:7` (`cdp/java`), `proxy.md:350-351` | Self-referential or dead cross-references. They should point to `references/cdp.md`, `references/proxy.md` and `ui-test-author/playwright`. |
| D32 | Logical | `playwright-snapshots.md:253,283`; `bdd-project-scaffold/SKILL.md:119,129` | Maven `mvn -B test` and `target/…` paths in a Gradle-default lane. |
| D33 | Data | `browser-cloud-setup/references/details.md:83` | `client.playwrightVersion` is `"1.x"`; BrowserStack expects the installed client version. |
| D34 | Code | `test-reports/SKILL.md:130-133` | Temp trace never deleted; stream unclosed; screenshot is viewport-only with no `setFullPage`. |
| D35 | Code / Logical | `language-testing/SKILL.md:196` and `:154` vs `:267` | `hasCSS(..., ".+")` is vacuous. Hardcoded currency literals contradict the skill's own "hardcoding a formatted number" anti-pattern. |
| D36 | Code | `axe-playwright.md:214-217` | `if` plus `System.out.println` in test code, against CLAUDE.md:42/96 and `ui-test-author/playwright/SKILL.md:325`. |
| D37 | Code | `cdp.md:241-244` | The cache-disabled test asserts the **first** captured avatar response (`findFirst`), so it passes whether or not a re-fetch happened. |
| D38 | Logical | `percy.md:165-172,316-330` vs `ui-test-author/review/SKILL.md:74` | Percy tests contain no assertion; the review grades "asserts nothing" as a blocker. Document the exception. |
| D39 | Code / Logical | `production-uptime-checks/SKILL.md:172-173` | `catch (Exception)` misses the `AssertionFailedError` (an `Error`) thrown by `PlaywrightAssertions`. It logs only `getMessage()` and captures no screenshot or trace on probe failure. The skill is an orphan (`docs/skills-catalog.md:30`) although `qa-ui-java.md:123` hands probes to `qa-api-java`, which never loads it. |
| D40 | Logical | `ui-test-author/playwright/SKILL.md:288,313`; `ui-test-author/review/SKILL.md:79,85` | The networkidle ban covers only `navigate(setWaitUntil)`, not `page.waitForLoadState(LoadState.NETWORKIDLE)`. `page.type` (deprecated), `waitForSelector` and `querySelector`/`ElementHandle` are absent from the review list. |
| D41 | Logical | `qa-ui-java.md:4`, `qa-bdd-java.md:4` | MCP tool list lacks `browser_hover`, `browser_press_key`, `browser_resize` and `browser_tabs`, which hover menus and responsive extraction need. |
| D42 | Logical | `github-actions.md:274`, `azure-pipelines.md:222`, `gitlab-ci.md:211` (`-Pheadless=true`) vs `ui-test-author/playwright/SKILL.md:65,97` (`-Dplaywright.headless`) | The CI flag is never read. |
| D43 | Logical | `github-actions.md:283-284`, `gitlab-ci.md:221-222`, `azure-pipelines.md:227` | Upload `e2e/build/screenshots` and `e2e/build/playwright-traces`, which no skill writes. `test-reports` writes temp files into Allure. |
| D44 | Logical | `gherkin-step-code/SKILL.md:51` vs `ui-test-author/playwright/SKILL.md:270` | "Every … page object gets `TestContext` injected" vs page constructor "`(Page page)` — never config". |
| D45 | Code | `ui-test-author/playwright/SKILL.md:219-232` | `AuthState` reuses `build/.auth/user.json` forever with no expiry check, and has no private constructor. |
| D46 | Logical | `responsive-testing/SKILL.md:63-64` vs `:94,165` | "Never `setViewportSize` per test" vs per-test `setViewportSize` in the core pattern. |
| D47 | Logical | `ui-test-author/playwright/SKILL.md:285` vs `CLAUDE.md:94` | The skill bans any catch in `@AfterMethod`; CLAUDE.md permits a narrow, logged catch in an I/O teardown helper. `playwright-snapshots.md:285-289` violates the stricter Java rule. |
| D48 | Logical | `bdd-project-scaffold/SKILL.md:118` and `:128` | Sets both `@SelectClasspathResource("features")` and `cucumber.features`. When `cucumber.features` is set, the JUnit Platform engine ignores discovery selectors. |
| D49 | Logical | `ui-test-author/review/SKILL.md:37` | Suggests a `data-test` attribute. `getByTestId` defaults to `data-testid` and `setTestIdAttribute` is never taught. |
| D50 | nit / minor | Samples throughout | **Inline comments** in sample bodies against CLAUDE.md:52, more than 80 occurrences. For example: `playwright-snapshots.md:72,150,155,177,181,185,189,234`; `percy.md:159,169,171,254`; `applitools.md:97,100-101,161,183,189,191,193,199`; `playwright-routes.md:222,239,264,273-274,315`; `cdp.md:84,98,191,216,220,253,306,318,328,332`; `axe-playwright.md:114,116,120,196,206,216,227,242,244,275,278,296`; `responsive-testing/SKILL.md:95,101,116,154,183-187`; `language-testing/SKILL.md:136,139,144,146-147,154,159,192`; `bdd-project-scaffold/SKILL.md:69,73,79-81,84,90,114,148-151,189-190`; `gherkin-step-code/SKILL.md:86,129`; `production-uptime-checks/SKILL.md:158,161,166,170,173,175`; `browser-cloud-setup/references/details.md:71,83,165,175-178`. |
| D51 | nit | `ui-test-author/playwright/SKILL.md:341` | "Add the page object as a protected field on `BaseTest`" grows a god base class. KISS says construct pages in the test. |
| D52 | nit | `api-test-author/playwright/SKILL.md:43,132` | `org.apache.http.HttpStatus` pulls in legacy HttpComponents 4 just for constants. |

### Out of strict scope, but intersecting

- `ui-test-author/selenium/SKILL.md:188` sets a 10 s implicit wait while `BasePage` uses `WebDriverWait` (47-51). That mix is a **major** finding under `ui-test-author/review/SKILL.md:107` and `page-object-design/SKILL.md:211`.
- `network-mocking/references/proxy.md` (Selenium):
  - Its test bodies use `try/finally` (220-235, 250-265, 276-285).
  - The 500 test (~271-286) asserts nothing.
  - It relies on BrowserUp Proxy, which is unmaintained.
- The same fabricated screenshot assertion exists in the .NET lane: `qa/dotnet/skills/visual-regression/references/playwright-snapshots.md:25-26` (`Expect(Page).ToHaveScreenshotAsync()`).
- `banner.getText()` is copied into the TS writer: `qa/typescript/skills/ui-test-author/playwright/SKILL.md:199`.

---

## 4. Parity with TypeScript

| Topic | TypeScript | Java | Verdict |
|---|---|---|---|
| Visual regression | Real `toHaveScreenshot` with a config-level `toHaveScreenshot` block and `trace: 'on-first-retry'` (`qa/typescript/skills/visual-regression/references/playwright-snapshots.md:20-29,40-60`) | Ports it 1:1 to an API that does not exist (D1). **Java has no built-in screenshot assertion.** The skill does not say so; it teaches `hasScreenshot` as if it existed, plus a "no `--update-snapshots`, delete and rerun" workflow that also does not exist | **Contradicts reality.** Java should teach either hosted diffing (Percy/Applitools are real Java bindings, `percy.md`, `applitools.md`) or `Locator.screenshot(ScreenshotOptions…)` plus an explicit comparator |
| Lifecycle | Fixture-driven page objects, fresh `page` per test from the runner (`ui-test-author/playwright/SKILL.md:79-99`, TS) | Base class with static state (D2) and nine variants (D22) | **Lags.** Needs one ThreadLocal lifecycle |
| Auth | `setup` project plus dependent projects (TS 125-151) | Static `synchronized` `AuthState` with UI login (Java 219-232); the token-seeding path lives in `test-login-tokens/references/details.md:184-215` | Acceptable port; Java should cross-reference `test-login-tokens` |
| Retry / poll | `expect(...).toPass()` / `expect.poll` (TS 212) | "Awaitility (if added)" (Java 300), no example | **Lags** |
| Custom assertion message | `expect(x, msg)` exists, though TS 199 also misuses `getText()` | Not available; the rule is unsatisfiable (D6) | **Contradicts** unless carved out |
| Lint | `eslint-plugin-playwright` (TS 17) | Nothing | Expected gap; the review checklist must compensate |
| Trace and video config | Review rows "trace/video `retain-on-failure`" (`qa/typescript/skills/ui-test-author/review/SKILL.md:99,147`) | No evidence row in the Java review; capture only in reporting (D15) | **Lags** |
| testIdAttribute mirroring | `test.use({ testIdAttribute })` / `selectors.setTestIdAttribute` (`qa/typescript/skills/page-objects-from-url/SKILL.md:36`) | Missing (`page-objects-from-url/SKILL.md:35`) | **Lags** |
| Devices | `devices['Desktop Chrome']` (TS 149) | No registry exists in Java; nothing teaches manual descriptors (D23) | **Lags** |
| `waitForResponse` ordering | Promise-before-action (TS 205-211) | `waitForResponse(pred, Runnable)` shape is right, but the type is wrong (D4) | Port correct conceptually |
| Playwright → ZAP proxy (authenticated DAST) | `qa/_shared/security-testing/client-side-security/references/spa-dast.md:50-67` (TS only) | No `BrowserType.LaunchOptions().setProxy(...)` example | Minor gap |
| filter / and / or / frameLocator / ariaSnapshot / clock | Absent in TS too | Absent | **Both lanes lag.** Fix once in each writer |

---

## 5. Structural observations

### How `qa-ui-java` loads skills (wiring points for a new skill)

1. **Frontmatter tools.** `qa/java/agents/qa-ui-java.md:4` lists the MCP tools.
2. **Skill-loading protocol.** `qa-ui-java.md:16-25`: the agent reads every `SKILL.md` listed for a step before starting it. Its root is `qa/java/skills/` **only**; `qa/reporting/`, `qa/cicd/`, `qa/manual/` and security are explicitly excluded (line 18). The ep-* skills are always loaded (line 25).
3. **Step table.** `qa-ui-java.md:108-115` names the skill paths per step: Foundations (1), Author (2), Specialized layers (3), Review (4).
4. **Orientation cache.** "Seams to reuse" at `qa-ui-java.md:78`.
5. **Plugin manifest.** `.claude-plugin/marketplace.json`, `qa-java` plugin `skills` array (Java skills listed around the `./qa/java/skills/...` block; `python-web-testing` is at line 48).
6. **Catalog.** `docs/skills-catalog.md` (catalog and orphan list at line 30).
7. **Sibling agents.** `qa-bdd-java.md:105` (step 4 loads `ui-test-author/playwright`) should also pick up any lifecycle or evidence skill.

**To wire a new skill:**
- Create `qa/java/skills/<name>/SKILL.md` with frontmatter `name: qa-<name>-java`.
- Add its path to the right Step row of `qa-ui-java.md`, and of `qa-bdd-java.md` step 4.
- Add it to the `qa-java` skills array in `marketplace.json` and to `docs/skills-catalog.md`.
- Add matching review rows to `ui-test-author/review/SKILL.md`.

### Who should own the proposed topics

| Topic | Recommended owner | Why |
|---|---|---|
| **Evidence capture** (screenshot, video, trace, HAR on failure) | `qa/java/skills/ui-test-author/playwright`, as part of the single `BaseTest` lifecycle (a `references/evidence.md` if the 353-line file needs room), loaded in **Step 1** | Capture is a lifecycle concern: start tracing in `@BeforeMethod`, decide in one `@AfterMethod`, save video after `context.close()`. `qa-ui-java` cannot load `qa/reporting` (`qa-ui-java.md:18`), which is why D15 exists. `test-reports` keeps only the Allure-attach mechanics and links back. A separate skill would add a second lifecycle owner, which is the D22 problem again |
| **Locator scoping** (`filter` with `setHas`/`setHasText`/`setVisible`, chaining, `and`/`or`, `frameLocator`, strictness, `nth`/`first` smell, `describe`, `setTestIdAttribute`) | Code in `ui-test-author/playwright` (extend the "Locator preference order" block at lines 256-265); architectural "component takes parent `Locator`" stays in `page-object-design/SKILL.md:85-90`; review rows in `ui-test-author/review/SKILL.md:70-91` | One authority for locator mechanics; POM shape stays with the architect skill |
| **WebMCP testing** | New `qa/java/skills/webmcp-testing`, loaded in `qa-ui-java` **Step 3** (specialized layers), with a cross-reference from `tooling/` (the MCP builder side) | It is a page-exposed agent-tool surface exercised in a real browser (Playwright `page.evaluate` against the page's registered tools), so it is the UI lane, not `qa-llm-java`, which tests model output quality. Zero mentions anywhere in the repo today. Verify the browser API's availability and status at authoring time; it is an early-stage proposal |

**Also:** collapse the nine lifecycles (D22) into the one `BaseTest` before adding any skill. Every specialized skill (visual, a11y, responsive, i18n, CDP, grid, realtime browser surface) should say "extends `BaseTest` from `ui-test-author/playwright`" rather than defining its own.

---

## 6. Counts

- **Version-pin sites:** 49 (24 Playwright-family, 14 Allure, 11 TestNG/AssertJ). Python: 0 pins.
- **Findings:** 2 blocker · 22 major (D3–D24) · 26 minor (D25–D50) · 2 nit (D51–D52) · 8 version items (V1–V8).
- **By class** (counting multi-class findings once, by primary class):

  | Class | Defects | Version items |
  |---|---|---|
  | Data | 2 | 4 |
  | Code | 20 | 1 |
  | Logical | 30 | 3 |
