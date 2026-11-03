---
name: ui-tests-review
description: Use when reviewing existing Java UI test code or page objects (Playwright, Selenium, Appium). Triggers "review this Playwright spec". Not for writing new tests (ui-tests-playwright).
---

# QA — UI Test & Page Object Reviewer (Java)

Reviews Java UI test code (Playwright Java, Selenium Java, Appium Java) against the qa-java rule files. Produces a findings table in the format defined in `CLAUDE.md`. **Does not rewrite the code** — points to the fix and lets the human apply it.

## When to use

- A diff or file (page object, `@Test` class, fixture, `BaseTest`, `BasePage`) is submitted for review
- Pre-merge gate on a PR touching `src/main/java/pom/`, `src/test/java/`, or any TestNG/JUnit UI test
- Second opinion on whether a Java page object is well-structured

## When NOT to use

- Generating new code → `qa/java/skills/ui-test-author/playwright`, `qa/java/skills/ui-test-author/selenium`, `qa/java/skills/ui-test-author/appium`
- Architecting the POM (sub-packages, base classes) → `qa/java/skills/page-object-design`
- Reviewing API tests → `qa/java/skills/api-test-author/review`
- Reviewing .NET UI code → `qa/dotnet/skills/ui-test-author/review`
- Reviewing TypeScript UI code → `qa/typescript/skills/ui-test-author/review`

## Inputs needed

1. **Stack** — Playwright Java, Selenium Java, or Appium Java
2. **Files** to review (page objects, `@Test` classes, fixtures, `BaseTest`/`BasePage`)
3. **Context** — new feature, refactor, or bug fix?
4. **Project conventions** — anything overriding the stack defaults (e.g. project bans XPath, mandates Allure `@Step`)

## The checklist is the rule file

Every check, and the severity it reports, lives in one place: the qa-java rule files `qa-java.md` (core) and `qa-java-ui.md`, plus `qa-java-bdd.md` when step definitions are in the diff.

1. **The project's copies first**: `.claude/rules/qa-java/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `qa/java/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/qa-java:rules` installs them.

Read `qa-java.md`, plus each other file whose `paths:` match a file under review, in full before the first finding. A rule loaded on its own by the session is not enough: a review needs every file that applies. Never review from memory of the rules, and never add a check the files do not contain; propose it as a rule change instead. A comment explaining a locator (`// the third span is the price`) is evidence the locator is positional: report the locator, not the comment.

**Version policy.** Detect Playwright Java (1.63), Selenium and Appium / java-client first; never flag a 1.63 suite for lacking a 1.64-only API. The rule files' "the codebase wins" line applies.

## Playwright Java mechanics

These are API facts of the pinned version, not standards: code that breaks one does not compile or misbehaves. The writer's mechanics are in `qa/java/skills/ui-test-author/playwright` (`references/lifecycle.md`, `locators.md`, `assertions.md`).

| Check | Bad sign | Severity |
|---|---|---|
| A base URL is set | Relative `navigate("/x")` / `request().post("/api/x")` with no `setBaseURL`, or a hardcoded host instead of `BASE_URL` | major |
| Video kept after the close | `video.saveAs(...)` before `context.close()` — Java throws | major |
| Code compiles on the pinned version | `within(`, `getByRef`, `setRecordVideoFps` or screencast `setFps` on 1.63; `Allure.addAttachment(...)` on allure-testng 3 | blocker |
| `Locator` has no `getText()` | `locator.getText()` — Selenium's `WebElement` API; it does not compile | blocker |
| Per-assertion timeouts use the matcher's options | `new AssertOptions().setTimeout(...)` — no such class; use `new LocatorAssertions.IsVisibleOptions().setTimeout(...)` | blocker |
| `waitForResponse` is typed and ordered | `APIResponse r = page.waitForResponse(...)` (it returns `Response`); a wait started after the action instead of `waitForResponse(predicate, action)` | blocker |
| `waitForFunction` not used for plain UI state | `page.waitForFunction("() => ...")` for visible/text checks | minor |
| Positive matchers preferred | `not().isVisible()` where `isHidden()` exists | nit |
| `setExact(true)` for ambiguous names | `getByText("Submit")` matching `Submit Order`, `Submitting…` | minor |

## Output format

```
| Severity | Location                | Issue                                              | Suggested fix                                                    |
|----------|-------------------------|----------------------------------------------------|------------------------------------------------------------------|
| blocker  | pom/LoginPage.java:42   | `Thread.sleep(2000)` — arbitrary wait              | Replace with `WebDriverWait` + `ExpectedConditions.visibilityOf` |
| major    | pom/ProductPage.java:18 | XPath where a `data-testid` exists                 | Switch to `By.cssSelector("[data-testid='Inventory.Item']")`     |
| minor    | pom/CartPage.java:55    | Inline `By.cssSelector(...)` repeated in 3 methods | Promote to `private static final By CART_BADGE`                  |
```

The severity is the tag on the rule, never a new judgment. End with one line: `Rules: project .claude/rules/qa-java/ | plugin copy (not installed)`.

**Do not rewrite the code during review.** If the user wants a rewrite, hand off to the matching generator skill.

## Procedure

1. Identify the **stack** from imports and file location, and read each file end-to-end before writing findings.
2. Walk the rule files, core first, then `qa-java-ui.md`; for Playwright, then the mechanics table above.
3. For each finding: file path + line, issue, one-sentence fix. **Do not rewrite the code**; hand off to the matching generator.

## Handoffs

- Need to rewrite → `qa/java/skills/ui-test-author/playwright`, `qa/java/skills/ui-test-author/selenium`, or `qa/java/skills/ui-test-author/appium`
- Architecture is the real problem (not the code) → `qa/java/skills/page-object-design`
- Test data shape is wrong → `qa/java/skills/test-data-builder`
- API tests in the same PR → `qa/java/skills/api-test-author/review`
- Allure reporting questions → `qa/reporting/java/skills/test-reports`
- A rule is missing or wrong → edit the project's `.claude/rules/qa-java/`; for every project, the plugin's `qa/java/skills/rules/`
