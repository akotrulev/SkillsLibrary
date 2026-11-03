---
name: ui-tests-review
description: Use when reviewing existing .NET UI test code or page objects (Playwright, Selenium, Appium). Triggers "review this Playwright spec". Not for writing new tests (ui-tests-playwright).
---

# QA — UI Test & Page Object Reviewer (.NET / C#)

Reviews .NET UI test code (Playwright .NET, Selenium .NET, Appium .NET) and its page objects against the qa-dotnet rule files. Produces a findings table in the format defined in `CLAUDE.md`. **Does not rewrite the code** — points to the fix and lets the human apply it.

## When to use

- A diff or file (page object, `[Test]` class, fixture, `BaseTest`, `BasePage`, `.runsettings`, `.csproj`) is submitted for review
- Pre-merge gate on a PR touching `Pages/`, `Tests/`, `AppiumTests/Pages/`, or any NUnit/xUnit UI test

## When NOT to use

- Generating new code → `qa/dotnet/skills/ui-test-author/playwright`, `qa/dotnet/skills/ui-test-author/selenium`, `qa/dotnet/skills/ui-test-author/appium`
- Architecting the POM → `qa/dotnet/skills/page-object-design`
- Reviewing API tests → `qa/dotnet/skills/api-test-author/review`
- Reviewing Java or TypeScript UI code → `qa/java/skills/ui-test-author/review`, `qa/typescript/skills/ui-test-author/review`

## Inputs needed

1. **Stack** — Playwright .NET, Selenium .NET, or Appium .NET
2. **Files** to review (page objects, `[Test]` classes, fixtures, `BaseTest`/`BasePage`, `.runsettings`, `.csproj`)
3. **Context** — new feature, refactor, or bug fix?
4. **Project conventions** — anything overriding the stack defaults (a different test-id attribute, banned XPath, required `[AllureStep]`)

## Output format

```
| Severity | Location                | Issue                                  | Suggested fix                                               |
|----------|-------------------------|----------------------------------------|-------------------------------------------------------------|
| blocker  | Pages/LoginPage.cs:42   | `Task.Delay(2000)` used as UI sync     | Replace with `Expect(locator).ToBeVisibleAsync()` auto-wait |
| major    | Pages/ProductPage.cs:18 | XPath where a `data-testid` exists     | Switch to `GetByTestId("Inventory.Item")`                   |
| minor    | Pages/CartPage.cs:55    | Inline `Page.Locator("...")` repeated  | Promote to `private readonly ILocator _summary` field       |
```

The severity is the tag on the rule broken. End with one line: `Rules: project .claude/rules/qa-dotnet/ | plugin copy (not installed)`.

**Do not rewrite the code during review.** If the user wants a rewrite, hand off to the matching generator skill.

## The checklist is the rule file

Every check, and the severity it reports, lives in one place: the qa-dotnet rule files `automation.md` (core, including page objects and comments), `web-ui.md` (Playwright, Selenium), `mobile-ui.md` (Appium), and `suite-config.md` for a `.runsettings`, `.csproj` or `appsettings*.json` under review.

1. **The project's copies first**: `.claude/rules/qa-dotnet/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `qa/dotnet/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/qa-dotnet:rules` installs them.

Read `automation.md` and the stack's file, plus each other file whose `paths:` match a file under review, in full before the first finding. A rule loaded on its own by the session is not enough: a review needs every file that applies. Never review from memory of the rules, and never add a check the files do not contain; propose it as a rule change instead. The mechanics behind the Playwright rules are in `qa/dotnet/skills/ui-test-author/playwright` (`references/lifecycle.md`, `locators.md`, `assertions.md`).

## Version policy

Detect the TFM, NUnit major, `Microsoft.Playwright` (1.63 lane) or `Selenium.WebDriver`, and `Appium.WebDriver` (9 for Appium 3, 8.x for an Appium 2 cloud) first. Code that calls an API the pinned version lacks (`GetPathAsync`, `Within`, `GetByRef` on 1.63; `ILocator.Text`) does not compile: report it as a **blocker**. The rule file's "the codebase wins" line applies: a convention the suite follows consistently is not a finding.

## Procedure

1. Identify the stack from imports and file location; read the rule files, then each file under review end to end.
2. Walk the rules in this order: async and waiting, errors and cleanup, assertions, lifecycle (`BaseTest`, driver, parallelism), locators, then the rest. Most blockers live there.
3. Per finding: file and line, the rule broken, a one-sentence fix. The severity is the tag on the rule, never a new judgment. **Do not rewrite the code**; hand off to the matching generator.

## Handoffs

- A rule is missing or wrong → edit the project's `.claude/rules/qa-dotnet/`; for every project, the plugin's `qa/dotnet/skills/rules/`
- Need to rewrite → the matching generator under `qa/dotnet/skills/ui-test-author/`
- Architecture is the real problem → `qa/dotnet/skills/page-object-design`
- Test data shape is wrong → `qa/dotnet/skills/test-data-builder`
- API tests in the same PR → `qa/dotnet/skills/api-test-author/review`
- Allure reporting questions → `qa/reporting/dotnet/skills/test-reports`
