# Accessibility Testing — axe-core + Playwright (Java / TestNG)

The Java port of the canonical `qa-accessibility-testing-typescript`. Same axe-core rule
engine, same `violations`-as-the-gate model, same triage discipline — re-expressed in
`com.deque.html.axe-core:playwright` + Playwright-Java + TestNG idioms.

axe-core is the de-facto accessibility rule engine; the Deque Playwright binding runs it **inside your
Playwright run**, against the live DOM, and returns a structured `AxeResults` you assert on. This is an
**assertion layer** on top of the page objects and specs `qa-ui-test-author-playwright-java` already
authored — you inject an axe scan into an already-authored flow. You do **not** write new page objects
here.

Unlike the visual-regression family (free / Percy / Applitools), axe runs **entirely
in-browser**: there is **no SaaS, no agent, and no API key**. The gate is local, deterministic, and free
— `getViolations()` is empty or it isn't.

> **What automation can and can't do.** axe-core catches roughly **30–40%** of WCAG issues — the
> machine-checkable ones (missing `alt`, unlabeled inputs, color contrast, bad ARIA, duplicate IDs). It
> is a **floor, not proof of accessibility**: keyboard traps, focus order, screen-reader comprehension,
> and meaningful alt text still need manual + assistive-tech testing. Cross-link the manual/exploratory
> angle (`qa-exploratory-charter-writer`). Treat a green axe run as "no *automated* regressions," never
> "accessible."

## Setup

```kotlin
// build.gradle.kts
dependencies {
    testImplementation("com.microsoft.playwright:playwright:1.50.0")
    testImplementation("com.deque.html.axe-core:playwright:4.+")
    testImplementation("org.testng:testng:7.+")
    testImplementation("org.assertj:assertj-core:3.+")
}
```

```xml
<!-- or Maven -->
<dependency>
  <groupId>com.deque.html.axe-core</groupId>
  <artifactId>playwright</artifactId>
  <version>4.+</version>
  <scope>test</scope>
</dependency>
```

No config file, no service, no token. `AxeBuilder` bundles axe-core and injects it into the page at scan
time; the scan happens in the browser you already launched. (The artifact version tracks axe-core's
major.minor.)

## The AxeBuilder model

`new AxeBuilder(page).analyze()` injects axe-core, runs it against the current DOM, and returns an
`AxeResults` with four lists:

- **`getViolations()`** — failed rules. **This is the gate.** Each `Rule` has `getId()` (rule id, e.g.
  `color-contrast`), `getImpact()` (`minor` | `moderate` | `serious` | `critical`), `getHelp()`,
  `getHelpUrl()`, and `getNodes()` — each `CheckedNode` carries the failing `getTarget()` selector(s)
  and a `getFailureSummary()` telling you how to fix it.
- **`getPasses()`** — rules that passed (evidence, not usually asserted on).
- **`getIncomplete()`** — rules axe **could not decide** automatically (e.g. a contrast check over a
  background image). **Not a pass** — these need manual review. Don't silently ignore them.
- **`getInapplicable()`** — rules with no matching elements on the page.

The assertion is one logical assertion per the global rules (AssertJ):

```java
assertThat(results.getViolations()).isEmpty();
```

## Core pattern — scan injected into a page-object-driven flow

The page object exposes intent and drives the app to the state under test; the test stabilizes on a
condition, then scans. No selectors in the test, no fixed waits — axe analyzes the **live DOM at call
time**, so the page must be in its final state before `analyze()`.

```java
// pages/CheckoutPage.java
import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.options.AriaRole;
import com.microsoft.playwright.options.WaitForSelectorState;

public final class CheckoutPage {
    private final Page page;

    public CheckoutPage(Page page) { this.page = page; }

    public Locator form() { return page.getByTestId("checkout-form"); }

    public void goTo() { page.navigate("/checkout"); }

    /** Resolves once the form is interactive — a condition, never a fixed wait. */
    public void waitUntilReady() {
        form().getByRole(AriaRole.BUTTON, new Locator.GetByRoleOptions().setName("Pay now"))
              .waitFor(new Locator.WaitForOptions().setState(WaitForSelectorState.VISIBLE));
    }
}
```

```java
// tests/CheckoutAccessibilityTest.java
import com.deque.html.axecore.playwright.AxeBuilder;
import com.deque.html.axecore.results.AxeResults;
import java.util.List;
import org.testng.annotations.Test;
import static org.assertj.core.api.Assertions.assertThat;

public class CheckoutAccessibilityTest extends BasePlaywrightTest {  // provides the managed Page

    @Test
    public void Should_have_no_a11y_violations_When_checkout_form_loaded() {
        CheckoutPage checkout = new CheckoutPage(page);
        checkout.goTo();
        checkout.waitUntilReady();                              // stabilize on a condition first…

        AxeResults results = new AxeBuilder(page)               // …then scan the live DOM
            .withTags(List.of("wcag2a", "wcag2aa", "wcag21a", "wcag21aa"))
            .analyze();

        assertThat(results.getViolations()).isEmpty();          // one logical assertion = the gate
    }
}
```

## Scoping + rule selection

Scope the scan and pick which rules count — the analogue of `Target.region` / match levels in the visual
family, but here it's *which rules*, not *how lenient*:

```java
AxeResults results = new AxeBuilder(page)
    .include(List.of("#checkout-form"))         // scan only this component
    .exclude(List.of(".third-party-widget"))    // skip an embed you don't own
    .withTags(List.of("wcag2aa", "wcag21aa"))   // the WCAG level that IS your gate
    .analyze();
```

- **`.include(List)` / `.exclude(List)`** — scan a component, not the whole page. Cleaner failures, and
  lets you gate a new component to zero while the legacy page still has debt. `.exclude` third-party
  iframes/widgets you can't fix.
- **`.withTags(List)`** — pick the ruleset = pick which WCAG level is your gate. Common tags: `wcag2a`,
  `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`, plus `best-practice`. **Decide your conformance target
  once** and apply the same tags everywhere — `wcag2a wcag2aa wcag21a wcag21aa` is the common "AA" gate.
- **`.withRules(List)` / `.disableRules(List)`** — surgical control of individual rule ids; overrides
  tags for those rules.
- **`.options(String)`** — raw axe-core run options as JSON (overrides `withRules`/`withTags`); reach for
  it last.

### A shared AxeBuilder factory (DRY the config)

Configure tags/excludes once via a helper so every test stays clean and consistent — the analogue of the
TS fixture:

```java
// support/AxeScanner.java
import com.deque.html.axecore.playwright.AxeBuilder;
import com.microsoft.playwright.Page;
import java.util.List;

public final class AxeScanner {
    private static final List<String> WCAG_AA = List.of("wcag2a", "wcag2aa", "wcag21a", "wcag21aa");
    private AxeScanner() {}

    /** Org-wide tags + excludes in one place — call .include(...) per test as needed. */
    public static AxeBuilder forPage(Page page) {
        return new AxeBuilder(page).withTags(WCAG_AA).exclude(List.of("#third-party-chat"));
    }
}
```

```java
AxeResults results = AxeScanner.forPage(page).include(List.of("#dashboard")).analyze();
assertThat(results.getViolations()).isEmpty();
```

## The triage reality — a real app has pre-existing violations

A green-field `isEmpty()` only works on a clean page. Real apps have debt. The disciplined patterns, in
order of preference:

**1. Gate *new* violations only — baseline the known set.** Fail only on additions. This stops the
bleeding without a big-bang fix, and every new feature ships clean:

```java
@Test
public void Should_introduce_no_new_a11y_violations_When_profile_loaded() {
    page.navigate("/profile");
    AxeResults results = AxeScanner.forPage(page).analyze();

    // Known debt, each with a tracking ticket — shrink this set, never grow it.
    Set<String> known = Set.of("color-contrast" /* JIRA-1234 */, "landmark-one-main" /* JIRA-1235 */);
    List<Rule> newViolations = results.getViolations().stream()
        .filter(v -> !known.contains(v.getId()))
        .toList();

    assertThat(newViolations).isEmpty();     // gate additions; legacy debt tracked separately
}
```

**2. Disable a *documented* false-positive — never blanket-disable.** If a rule genuinely misfires on
your markup, `.disableRules(...)` with a ticket reference in a comment. Disabling to make a real failure
go away is hiding a bug:

```java
AxeResults results = new AxeBuilder(page)
    .disableRules(List.of("scrollable-region-focusable"))   // axe false-positive on virtualized list — JIRA-2001
    .analyze();
```

**3. Don't silently pass `getIncomplete()`.** axe couldn't decide — surface it for manual review rather
than treating it as green:

```java
if (!results.getIncomplete().isEmpty()) {
    String ids = results.getIncomplete().stream().map(Rule::getId).collect(Collectors.joining(", "));
    System.out.println("axe needs manual review for: " + ids);   // or your structured logger
}
```

**4. Phase the rollout by impact.** When even the baseline is huge, gate on the worst first and ratchet
down over time:

```java
List<Rule> blocking = results.getViolations().stream()
    .filter(v -> "critical".equals(v.getImpact()) || "serious".equals(v.getImpact()))
    .toList();
assertThat(blocking).isEmpty();     // gate critical+serious now; widen to moderate/minor later
```

## A11y-specific stabilization — scan per state, not per page

axe analyzes the **live DOM at call time**. So scan **after** the page reaches the state under test, and
scan **once per meaningful state** — an open menu, an expanded accordion, a validation-error form are
different DOMs with different a11y surfaces. Drive the state via page-object intent, wait on a condition,
then scan:

```java
@Test
public void Should_have_no_a11y_violations_When_nav_menu_open() {
    NavBar nav = new NavBar(page);
    page.navigate("/");
    nav.openAccountMenu();                                              // page-object intent
    nav.accountMenu().waitFor(new Locator.WaitForOptions()
        .setState(WaitForSelectorState.VISIBLE));                      // condition, not a sleep

    AxeResults results = new AxeBuilder(page).include(List.of("[role='menu']")).analyze();
    assertThat(results.getViolations()).isEmpty();
}
```

Never `page.waitForTimeout(...)` / `Thread.sleep(...)` before a scan — it races the DOM and makes the
gate flaky.

## Reporting the gate — violations into Allure, fail CI on non-empty

axe gives you everything to make a failure actionable: rule id, impact, helpUrl, and the failing
selector + fix summary. Attach the JSON and a readable summary to Allure so the report names the rule
without anyone re-running locally (cross-link `qa-allure-reporting-java`):

```java
// support/A11yReport.java
import com.deque.html.axecore.results.Rule;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.qameta.allure.Allure;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;

public final class A11yReport {
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private A11yReport() {}

    public static void attach(List<Rule> violations) throws Exception {
        if (violations.isEmpty()) return;
        // Machine-readable: the full violation objects.
        Allure.addAttachment("axe-violations.json", "application/json",
            new ByteArrayInputStream(MAPPER.writeValueAsBytes(violations)), ".json");
        // Human-readable: one line per failing node.
        StringBuilder sb = new StringBuilder();
        for (Rule v : violations) {
            sb.append('[').append(v.getImpact()).append("] ").append(v.getId())
              .append(": ").append(v.getHelp()).append("\n  ").append(v.getHelpUrl()).append('\n');
            v.getNodes().forEach(n -> sb.append("  ").append(String.join(" ", n.getTarget())).append('\n'));
        }
        Allure.addAttachment("axe-summary.txt", "text/plain",
            new ByteArrayInputStream(sb.toString().getBytes(StandardCharsets.UTF_8)), ".txt");
    }
}
```

```java
@Test
public void Should_have_no_a11y_violations_When_settings_loaded() throws Exception {
    page.navigate("/settings");
    AxeResults results = new AxeBuilder(page).withTags(List.of("wcag2aa")).analyze();
    A11yReport.attach(results.getViolations());     // attach BEFORE asserting, so a failure carries it
    assertThat(results.getViolations()).isEmpty();
}
```

The CI job fails because the assertion fails — no extra wiring beyond uploading the Allure results and
the attached JSON (cross-link `qa-ci-pipelines-java`). There is **no API key to inject**
here — call that out as the contrast with the visual-regression family (`percy` `PERCY_TOKEN` / `applitools`
`APPLITOOLS_API_KEY`): axe runs in-browser, so the only thing CI needs is the artifact upload.

## Anti-patterns

- **`page.waitForTimeout(500)` / `Thread.sleep` before `analyze()`.** axe scans the DOM at call time; a
  sleep races it and is slow (and violates the global rules). *Fix:* wait on a condition
  (`Locator.waitFor`, spinner hidden), then scan.
- **One scan per page, ignoring interactive states.** Menus/modals/error states have their own a11y
  surface. *Fix:* scan per meaningful state after driving the app there.
- **Blanket `.disableRules` / cranking tags down to make it pass.** That hides real failures. *Fix:*
  `.disableRules` only a *documented* false-positive with a ticket; otherwise fix the markup.
- **Treating `getIncomplete()` as a pass.** axe abstained; the issue may be real. *Fix:* surface
  incompletes for manual review.
- **Asserting on `getViolations().size() == 0` with a bare boolean.** The bool throws away the diff.
  *Fix:* `assertThat(results.getViolations()).isEmpty()` — AssertJ prints the collection on failure.
- **Scanning the whole page when the feature under test is one component.** Legacy debt drowns the new
  regression. *Fix:* `.include(...)` the component; gate it to zero.
- **Calling a green axe run "accessible."** It covers ~30–40% of WCAG. *Fix:* pair with manual +
  assistive-tech testing; treat axe as the automated floor.
- **Duplicating tag/exclude config across every test.** Drifts over time. *Fix:* a shared `AxeScanner`
  factory.

## Examples

**End-to-end: a per-component a11y gate that ships new features clean against a legacy page.**

```java
// tests/SignupAccessibilityTest.java
import com.deque.html.axecore.playwright.AxeBuilder;
import com.deque.html.axecore.results.AxeResults;
import java.util.List;
import org.testng.annotations.Test;
import static org.assertj.core.api.Assertions.assertThat;

public class SignupAccessibilityTest extends BasePlaywrightTest {

    @Test
    public void Should_have_no_a11y_violations_When_signup_form_empty() throws Exception {
        SignupPage signup = new SignupPage(page);
        signup.goTo();
        signup.waitUntilReady();                                  // condition, not sleep

        AxeResults results = AxeScanner.forPage(page).include(List.of("#signup-form")).analyze();
        A11yReport.attach(results.getViolations());
        assertThat(results.getViolations()).isEmpty();
    }

    @Test
    public void Should_have_no_a11y_violations_When_validation_errors_shown() throws Exception {
        SignupPage signup = new SignupPage(page);
        signup.goTo();
        signup.submitEmpty();                                     // page-object intent
        signup.errorSummary().waitFor();                         // condition

        AxeResults results = AxeScanner.forPage(page).include(List.of("#signup-form")).analyze();
        A11yReport.attach(results.getViolations());
        assertThat(results.getViolations()).isEmpty();           // error state has its own a11y surface
    }
}
```

Lifecycle for this gate:
1. A dev adds a new field to the signup form.
2. CI runs the E2E suite; the axe scan runs in the same browser, on the live DOM, per state.
3. If the new field is missing a label, `getViolations()` is non-empty — the build fails with the rule
   id (`label`), the failing selector, and the helpUrl in the Allure attachment.
4. The dev fixes the markup; the gate goes green. Legacy debt on other pages is tracked separately by
   the ticketed allow-list, shrinking over time.

## Rules (hard constraints)

- A11y testing is an **assertion layer** on existing page objects/specs — inject the axe scan, don't
  author new page objects here. Page objects expose intent + locators; no selectors in tests.
- One logical assertion per test: `assertThat(results.getViolations()).isEmpty()` (or a filtered
  subset). Test names `Should_X_When_Y`.
- Stabilize on a **condition** (interactivity/visibility) before `analyze()`; never `waitForTimeout` /
  `Thread.sleep` — axe scans the live DOM at call time.
- Scan **per meaningful state** (menu open, accordion expanded, errors shown), not once per page.
- Pick the WCAG level deliberately via `.withTags` and apply it consistently (a shared factory).
- Triage with discipline: baseline known debt with **ticketed** allow-lists, `.disableRules` only
  *documented* false-positives, and surface `getIncomplete()` for manual review — never silently pass it.
- **No SaaS, no API key** (axe runs in-browser) — the gate is local and deterministic. The only CI need
  is the violations-JSON/Allure artifact upload.
- axe covers ~30–40% of WCAG: it's the automated **floor**, not proof of accessibility. Pair with
  manual + assistive-tech testing.

## Cross-references

- `qa-accessibility-testing-typescript` — the **canonical** skill, TS / Vitest+Playwright
  (`new AxeBuilder({ page }).analyze()`, `results.violations`).
- `qa-accessibility-testing-dotnet` — same skill, .NET / NUnit
  (`Deque.AxeCore.Playwright`, `new AxeBuilder(page).AnalyzeAsync()`, `result.Violations`).
- `references/lighthouse-ci.md` — the audit/score sibling: full-page
  perf/SEO/PWA + a11y **score** threshold, a separate Lighthouse pass. Run both: axe gates, Lighthouse
  trends.
- `qa-ui-test-author-playwright-java` — the page objects/specs the axe scan is injected into. Author the
  flow there; add the a11y scan here.
- `qa-ci-pipelines-java` — where the job fails on the assertion and the violations JSON is
  uploaded as an artifact. Note: **no secret to inject** (contrast `percy`/`applitools`).
- `qa-allure-reporting-java` — attach the violations JSON + readable summary to the report.
- `qa-exploratory-charter-writer` — the manual/assistive-tech testing that covers the ~60% axe can't.
