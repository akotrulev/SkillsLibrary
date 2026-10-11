# Accessibility Testing — axe-core + Playwright (Java / Playwright 1.63 + TestNG)

`com.deque.html.axe-core:playwright` runs the axe-core rule engine **inside your Playwright run**, against the
live DOM, and returns an `AxeResults` you assert on. It is an **assertion layer** on page objects that already
exist: a scan is added to a flow the page objects drive. axe runs entirely in the browser — no SaaS, no
agent, no API key.

> **What automation can and cannot do.** axe catches the machine-checkable share of WCAG — missing
> `alt`, unlabelled inputs, contrast, invalid ARIA, duplicate ids. It is a **floor, not proof**: keyboard
> traps, focus order and screen-reader comprehension still need manual and assistive-technology testing
> (`qa-<stack>:exploratory-charter-writer`). A green scan means "no automated regressions", never "accessible".

## 1. Setup

```kotlin
dependencies {
    testImplementation("com.deque.html.axe-core:playwright:4.13.0")
}
```

Exact, never `4.+` — a Maven `+` range is not even a valid version. The artifact bundles axe-core and
injects it at scan time; its version tracks axe-core's major and minor (checked on Maven Central on
2026-10-11: 4.13.0 is the latest). Playwright, TestNG, AssertJ and allure-testng come from J1's build
(`qa/java/skills/ui-test-author/playwright/assets/build.gradle.kts`).

## 2. The model

`new AxeBuilder(page).analyze()` returns `com.deque.html.axecore.results.AxeResults`:

| List | Meaning |
|---|---|
| `getViolations()` | Failed rules — **the gate** |
| `getIncomplete()` | Rules axe could not decide (contrast over an image). **Not a pass** — a person reviews them |
| `getPasses()` / `getInapplicable()` | Evidence; rarely asserted |

Each `Rule` has `getId()` (`color-contrast`), `getImpact()` (`minor` · `moderate` · `serious` · `critical`),
`getHelp()`, `getHelpUrl()`, `getTags()` and `getNodes()`. Each `CheckedNode` has `getTarget()` — an `Object`
holding the selector path, so print it with `String.valueOf` — `getHtml()` and `getFailureSummary()`.
`isErrored()` / `getErrorMessage()` report a scan that failed to run.

## 3. The native assertions come first

axe finds rule violations; it does not know what a control *should* be called. Assert the intended contract
with `hasAccessibleName`, `hasAccessibleDescription`, `hasAccessibleErrorMessage` [1.50], `hasRole` [1.44]
and `matchesAriaSnapshot` from `qa/java/skills/ui-test-author/playwright/references/assertions.md` §1–§2. A
form gets both: an axe scan per state, and a native assertion for the error message the story specifies
(§6).

## 4. The shared helper — `support/A11yScan.java`

The conformance target is **WCAG 2.2 AA**, set once. Every scan attaches its violations and its
incompletes **before** the test asserts, so a failure carries the evidence and incompletes are visible on
every run.

```java
package com.example.uitests.support;

import com.deque.html.axecore.playwright.AxeBuilder;
import com.deque.html.axecore.results.AxeResults;
import com.deque.html.axecore.results.Rule;
import com.microsoft.playwright.Page;
import io.qameta.allure.Allure;
import io.qameta.allure.AttachmentOptions;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

public final class A11yScan {
    public static final List<String> WCAG_22_AA = List.of("wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa");
    public static final Map<String, String> FALSE_POSITIVES = Map.of(
            "scrollable-region-focusable", "A11Y-2001: misfires on the virtualized order list");
    public static final Map<String, String> KNOWN_VIOLATIONS = Map.of(
            "color-contrast", "A11Y-1234",
            "landmark-one-main", "A11Y-1235");

    private final Page page;

    public A11yScan(Page page) {
        this.page = page;
    }

    public AxeResults scanPage() {
        return analyze(builder());
    }

    public AxeResults scanWithin(String testId) {
        return analyze(builder().include("[data-testid='" + testId + "']"));
    }

    public static List<Rule> newViolations(List<Rule> violations) {
        return violations.stream().filter(rule -> !KNOWN_VIOLATIONS.containsKey(rule.getId())).toList();
    }

    public static List<Rule> blockingViolations(List<Rule> violations) {
        return violations.stream()
                .filter(rule -> "critical".equals(rule.getImpact()) || "serious".equals(rule.getImpact()))
                .toList();
    }

    private AxeBuilder builder() {
        return new AxeBuilder(page)
                .withTags(WCAG_22_AA)
                .exclude("[data-testid='Chat.Widget']")
                .disableRules(List.copyOf(FALSE_POSITIVES.keySet()));
    }

    private static AxeResults analyze(AxeBuilder scan) {
        AxeResults results = scan.analyze();
        attach("axe-violations", results.getViolations());
        attach("axe-incomplete", results.getIncomplete());
        return results;
    }

    private static void attach(String name, List<Rule> rules) {
        String text = rules.stream()
                .map(A11yScan::describe)
                .collect(Collectors.joining("\n", rules.size() + " rule(s)\n", ""));
        Allure.attachment(name, "text/plain",
                new ByteArrayInputStream(text.getBytes(StandardCharsets.UTF_8)),
                AttachmentOptions.withFileExtension("txt"));
    }

    private static String describe(Rule rule) {
        String targets = rule.getNodes().stream()
                .map(node -> String.valueOf(node.getTarget()))
                .collect(Collectors.joining(", "));
        return "[" + rule.getImpact() + "] " + rule.getId() + ": " + rule.getHelp() + " (" + rule.getHelpUrl() + ")\n  " + targets;
    }
}
```

- `withTags(List)` picks the ruleset, which is picking the WCAG level. `best-practice` adds axe's own
  recommendations beyond WCAG; add it here deliberately, never per test.
- `include` / `exclude` take a CSS selector (or a list, `FromFrames`, `FromShadowDom`); the helper builds
  them from test ids, so a test passes `"Signup.Form"`, never a selector. `exclude` is for embeds you do not
  own.
- `disableRules` is only for a **documented** false positive, with its ticket and reason in
  `FALSE_POSITIVES`. Disabling a rule to hide a real failure hides a bug.
- `withRules(List)` runs only the named rules; `options(AxeRunOptions)` is raw axe run options and overrides
  both — reach for it last.
- The three maps and the list are immutable constants (`List.of`, `Map.of`), not shared mutable state.
- The attachments are plain text — rule, impact, help link and the failing selectors — one per scan, so the
  Allure report names the fix without a local re-run.

## 5. The core pattern — one scan per state

```java
package com.example.uitests.tests;

import com.deque.html.axecore.results.AxeResults;
import com.deque.html.axecore.results.Rule;
import com.example.uitests.pages.SignupPage;
import com.example.uitests.support.A11yScan;
import com.example.uitests.support.BaseTest;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;
import static org.assertj.core.api.Assertions.assertThat;

public class SignupAccessibilityTest extends BaseTest {
    private SignupPage signupPage;
    private A11yScan a11y;

    @BeforeMethod(alwaysRun = true)
    public void createPages() {
        signupPage = new SignupPage(page);
        a11y = new A11yScan(page);
    }

    @Test(groups = "a11y")
    public void Should_HaveNoWcagViolations_When_SignupFormIsEmpty() {
        signupPage.open();

        AxeResults results = a11y.scanWithin("Signup.Form");

        assertThat(results.getViolations()).extracting(Rule::getId)
                .as("axe violations in the empty sign-up form").isEmpty();
    }

    @Test(groups = "a11y")
    public void Should_HaveNoWcagViolations_When_ValidationErrorsShow() {
        signupPage.submitEmpty();

        AxeResults results = a11y.scanWithin("Signup.Form");

        assertThat(results.getViolations()).extracting(Rule::getId)
                .as("axe violations in the sign-up form with errors").isEmpty();
    }

    @Test(groups = "a11y")
    public void Should_AnnounceEmailRequired_When_SignupSubmittedEmpty() {
        signupPage.submitEmpty();

        assertThat(signupPage.email()).hasAccessibleErrorMessage("Enter an email address");
    }
}
```

- axe analyzes the DOM **at call time**, so the page object drives the state and waits on a condition
  first: `open()` returns once the form is visible, `submitEmpty()` once the error summary is. An open menu,
  an expanded accordion and a form showing errors are different DOMs with different accessibility
  surfaces — scan each one. Never `Thread.sleep` or `waitForTimeout` before a scan.
- `extracting(Rule::getId)` makes the failure message the list of rule ids; the attachment holds the
  detail. One logical assertion per test.
- AssertJ's `assertThat` and Playwright's `assertThat` are both static-imported; Java picks by argument
  type (`List` versus `Locator`).
- The third test is §3's native assertion: the scan proves no rule broke; this test proves the field says
  what the story requires. `email()` returns a locator with `describe("Email field")`, which names it in the
  failure.

## 6. Triage — a real app has existing violations

In order of preference:

1. **Gate new violations only.** Known debt lives in `KNOWN_VIOLATIONS`, each with its ticket; the map only
   shrinks: `assertThat(A11yScan.newViolations(results.getViolations())).extracting(Rule::getId).as("new axe violations").isEmpty()`.
2. **Disable a documented false positive** through `FALSE_POSITIVES` (§4), never in a test.
3. **Read the incompletes.** `axe-incomplete` is attached on every scan; reviewing it is part of accepting
   a new screen. There is no `if` and no `println` for them in a test.
4. **Ratchet by impact** when even the debt is large:
   `assertThat(A11yScan.blockingViolations(results.getViolations())).extracting(Rule::getId).as("critical and serious violations").isEmpty()`,
   then widen to every impact once the backlog clears.

## 7. CI

The scans run inside the normal UI job (`qa/cicd/java/skills/ci-pipelines`); the job fails because the
assertion fails. A failed scan's test also gets `BaseTest`'s screenshot, trace and video in
`build/playwright-artifacts/`, and the attachments travel in the Allure results. No secret is needed — the
contrast with Percy's and Applitools' keys.

## Anti-patterns

- **`Thread.sleep` or `waitForTimeout` before `analyze()`.** *Fix:* the page object waits for the state.
- **One scan per page, ignoring interactive states.** *Fix:* one scan per meaningful state.
- **Tags that stop at WCAG 2.1 AA.** *Fix:* `wcag22aa` in `WCAG_22_AA`.
- **Tags or excludes repeated per test.** They drift. *Fix:* the helper.
- **`if (!results.getIncomplete().isEmpty()) System.out.println(…)`.** A condition in a test, and silent in
  CI. *Fix:* the helper attaches the incompletes on every scan.
- **`new AxeBuilder(page)` or `page.navigate` in a test.** *Fix:* the helper and the page objects.
- **A whole-page scan for one new component.** Legacy debt drowns the regression. *Fix:* `scanWithin`.
- **`String.join(" ", node.getTarget())`.** `getTarget()` returns `Object`; it does not compile.
  *Fix:* `String.valueOf(node.getTarget())`.
- **`Allure.addAttachment(...)`.** Removed in allure-java 3.0. *Fix:* `Allure.attachment(..., AttachmentOptions)`.
- **A green scan reported as "accessible".**

## Rules

- `com.deque.html.axe-core:playwright:4.13.0`, exact.
- WCAG 2.2 AA tags, excludes and false positives live in one helper, built in the class's `@BeforeMethod`.
- One logical assertion per test: the violation ids `isEmpty()` with `.as("<subject>")`, or a named subset.
- Stabilize through the page object before a scan; scan once per meaningful state.
- Every scan attaches its violations and incompletes with `Allure.attachment(..., AttachmentOptions)`.
- Known debt is ticketed and only shrinks; false positives are documented.
- Tests reach pages through page objects; selectors are built from test ids inside the helper.
- Pair every scan of a story's form with the native assertion for what the story specifies.

## Cross-references

- `references/lighthouse-ci.md` — the score-and-trend sibling for public pages.
- `qa/java/skills/ui-test-author/playwright` — `BaseTest`, page objects, `references/assertions.md`.
- `qa/java/skills/evidence-capture` — the failure evidence beside the scan's attachments.
- `qa/cicd/java/skills/ci-pipelines` — the UI job the scans run in.
- `qa-typescript:accessibility-testing` (`@axe-core/playwright`), `qa-dotnet:accessibility-testing`
  (`Deque.AxeCore.Playwright`).
- `qa-<stack>:exploratory-charter-writer` — the manual and assistive-technology testing axe cannot do.
