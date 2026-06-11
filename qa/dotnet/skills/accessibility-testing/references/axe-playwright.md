# Accessibility Testing — axe-core + Playwright (.NET / NUnit)

The .NET port of the canonical `qa-accessibility-testing-typescript`. Same axe-core rule
engine, same `violations`-as-the-gate model, same triage discipline — re-expressed in
`Deque.AxeCore.Playwright` + `Microsoft.Playwright.NUnit` idioms, async all the way down.

axe-core is the de-facto accessibility rule engine; `Deque.AxeCore.Playwright` runs it **inside your
Playwright run**, against the live DOM, and returns a structured `AxeResult` you assert on. This is an
**assertion layer** on top of the page objects and specs `qa-ui-test-author-playwright-dotnet` already
authored — you inject an axe scan into an already-authored flow. You do **not** write new page objects
here.

Unlike the visual-regression family (free / Percy / Applitools), axe runs **entirely
in-browser**: there is **no SaaS, no agent, and no API key**. The gate is local, deterministic, and free
— `Violations` is empty or it isn't.

> **What automation can and can't do.** axe-core catches roughly **30–40%** of WCAG issues — the
> machine-checkable ones (missing `alt`, unlabeled inputs, color contrast, bad ARIA, duplicate IDs). It
> is a **floor, not proof of accessibility**: keyboard traps, focus order, screen-reader comprehension,
> and meaningful alt text still need manual + assistive-tech testing. Cross-link the manual/exploratory
> angle (`qa-exploratory-charter-writer`). Treat a green axe run as "no *automated* regressions," never
> "accessible."

## Setup

```xml
<!-- Tests.csproj -->
<ItemGroup>
  <PackageReference Include="Microsoft.Playwright.NUnit" Version="1.50.0" />
  <PackageReference Include="Deque.AxeCore.Playwright" Version="4.*" />
  <PackageReference Include="NUnit" Version="4.*" />
  <PackageReference Include="NUnit3TestAdapter" Version="4.*" />
  <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.*" />
</ItemGroup>
```

No config file, no service, no token. `AxeBuilder` bundles axe-core and injects it into the page at scan
time; the scan happens in the browser you already launched. (The package versions track axe-core's
major.minor — `Deque.AxeCore.Playwright` 4.11.x bundles axe-core 4.11.x.)

## The AxeBuilder model

`await new AxeBuilder(page).AnalyzeAsync()` injects axe-core, runs it against the current DOM, and
returns an `AxeResult` with four arrays:

- **`Violations`** — failed rules. **This is the gate.** Each `AxeResultItem` has `Id` (rule id, e.g.
  `color-contrast`), `Impact` (`minor` | `moderate` | `serious` | `critical`), `Help`, `HelpUrl`, and
  `Nodes` — each `AxeResultNode` carries the failing `Target` selector(s) and a `FailureSummary` telling
  you how to fix it.
- **`Passes`** — rules that passed (evidence, not usually asserted on).
- **`Incomplete`** — rules axe **could not decide** automatically (e.g. a contrast check over a
  background image). **Not a pass** — these need manual review. Don't silently ignore them.
- **`Inapplicable`** — rules with no matching elements on the page.

> There is also an extension shortcut, `await page.RunAxe()`, which returns the same `AxeResult`. Prefer
> the explicit `new AxeBuilder(page)` form — it's the one that takes scoping/tag calls and ports
> identically to TS/Java.

The assertion is one logical assertion per the global rules:

```csharp
Assert.That(result.Violations, Is.Empty);
```

## Core pattern — scan injected into a page-object-driven flow

The page object exposes intent and drives the app to the state under test; the test stabilizes on a
condition, then scans. No selectors in the test, no fixed waits — axe analyzes the **live DOM at call
time**, so the page must be in its final state before `AnalyzeAsync()`. Inherit `PageTest` for the
managed `Page`.

```csharp
// Pages/CheckoutPage.cs
using Microsoft.Playwright;

public sealed class CheckoutPage
{
    private readonly IPage _page;
    public ILocator Form => _page.GetByTestId("checkout-form");

    public CheckoutPage(IPage page) => _page = page;

    public Task GotoAsync() => _page.GotoAsync("/checkout");

    /// <summary>Resolves once the form is interactive — a condition, never a fixed wait.</summary>
    public Task WaitUntilReadyAsync() =>
        Form.GetByRole(AriaRole.Button, new() { Name = "Pay now" })
            .WaitForAsync(new() { State = WaitForSelectorState.Visible });
}
```

```csharp
// Tests/CheckoutAccessibilityTests.cs
using Deque.AxeCore.Playwright;
using Microsoft.Playwright.NUnit;
using NUnit.Framework;

[TestFixture]
public class CheckoutAccessibilityTests : PageTest
{
    [Test]
    public async Task Should_have_no_a11y_violations_When_checkout_form_loaded()
    {
        var checkout = new CheckoutPage(Page);
        await checkout.GotoAsync();
        await checkout.WaitUntilReadyAsync();              // stabilize on a condition first…

        var result = await new AxeBuilder(Page)            // …then scan the live DOM
            .WithTags(new[] { "wcag2a", "wcag2aa", "wcag21a", "wcag21aa" })
            .AnalyzeAsync();

        Assert.That(result.Violations, Is.Empty);          // one logical assertion = the gate
    }
}
```

## Scoping + rule selection

Scope the scan and pick which rules count — the analogue of `Target.Region` / match levels in the
visual family, but here it's *which rules*, not *how lenient*:

```csharp
var result = await new AxeBuilder(Page)
    .Include("#checkout-form")           // scan only this component
    .Exclude(".third-party-widget")      // skip an embed you don't own
    .WithTags(new[] { "wcag2aa", "wcag21aa" })   // the WCAG level that IS your gate
    .AnalyzeAsync();
```

- **`.Include(selector)` / `.Exclude(selector)`** — scan a component, not the whole page. Cleaner
  failures, and lets you gate a new component to zero while the legacy page still has debt. `.Exclude`
  third-party iframes/widgets you can't fix.
- **`.WithTags([...])`** — pick the ruleset = pick which WCAG level is your gate. Common tags:
  `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`, plus `best-practice`. **Decide your
  conformance target once** and apply the same tags everywhere — `wcag2a wcag2aa wcag21a wcag21aa` is
  the common "AA" gate.
- **`.WithRules([...])` / `.DisableRules([...])`** — surgical control of individual rule ids; overrides
  tags for those rules.
- **`.Options(...)`** — raw axe-core run options (overrides `WithRules`/`WithTags`); reach for it last.

### A shared AxeBuilder factory (DRY the config)

Configure tags/excludes once via an injected helper so every test stays clean and consistent — the
constructor-injection-friendly analogue of the TS fixture:

```csharp
// Support/AxeScanner.cs
using Deque.AxeCore.Playwright;
using Microsoft.Playwright;

public static class AxeScanner
{
    private static readonly string[] WcagAa = { "wcag2a", "wcag2aa", "wcag21a", "wcag21aa" };

    /// <summary>Org-wide tags + excludes in one place — call .Include(...) per test as needed.</summary>
    public static AxeBuilder ForPage(IPage page) =>
        new AxeBuilder(page).WithTags(WcagAa).Exclude("#third-party-chat");
}
```

```csharp
var result = await AxeScanner.ForPage(Page).Include("#dashboard").AnalyzeAsync();
Assert.That(result.Violations, Is.Empty);
```

## The triage reality — a real app has pre-existing violations

A green-field `Is.Empty` only works on a clean page. Real apps have debt. The disciplined patterns, in
order of preference:

**1. Gate *new* violations only — baseline the known set.** Fail only on additions. This stops the
bleeding without a big-bang fix, and every new feature ships clean:

```csharp
[Test]
public async Task Should_introduce_no_new_a11y_violations_When_profile_loaded()
{
    await Page.GotoAsync("/profile");
    var result = await AxeScanner.ForPage(Page).AnalyzeAsync();

    // Known debt, each with a tracking ticket — shrink this set, never grow it.
    var known = new HashSet<string> { "color-contrast" /* JIRA-1234 */, "landmark-one-main" /* JIRA-1235 */ };
    var newViolations = result.Violations.Where(v => !known.Contains(v.Id)).ToList();

    Assert.That(newViolations, Is.Empty);    // gate additions; legacy debt tracked separately
}
```

**2. Disable a *documented* false-positive — never blanket-disable.** If a rule genuinely misfires on
your markup, `.DisableRules(...)` with a ticket reference in a comment. Disabling to make a real failure
go away is hiding a bug:

```csharp
var result = await new AxeBuilder(Page)
    .DisableRules(new[] { "scrollable-region-focusable" })   // axe false-positive on virtualized list — JIRA-2001
    .AnalyzeAsync();
```

**3. Don't silently pass `Incomplete`.** axe couldn't decide — surface it for manual review rather than
treating it as green:

```csharp
if (result.Incomplete.Length > 0)
    TestContext.Out.WriteLine($"axe needs manual review for: {string.Join(", ", result.Incomplete.Select(i => i.Id))}");
```

**4. Phase the rollout by impact.** When even the baseline is huge, gate on the worst first and ratchet
down over time:

```csharp
var blocking = result.Violations.Where(v => v.Impact is "critical" or "serious").ToList();
Assert.That(blocking, Is.Empty);     // gate critical+serious now; widen to moderate/minor later
```

## A11y-specific stabilization — scan per state, not per page

axe analyzes the **live DOM at call time**. So scan **after** the page reaches the state under test, and
scan **once per meaningful state** — an open menu, an expanded accordion, a validation-error form are
different DOMs with different a11y surfaces. Drive the state via page-object intent, wait on a condition,
then scan:

```csharp
[Test]
public async Task Should_have_no_a11y_violations_When_nav_menu_open()
{
    var nav = new NavBar(Page);
    await Page.GotoAsync("/");
    await nav.OpenAccountMenuAsync();                                 // page-object intent
    await nav.AccountMenu.WaitForAsync(new() { State = WaitForSelectorState.Visible });  // condition

    var result = await new AxeBuilder(Page).Include("[role='menu']").AnalyzeAsync();
    Assert.That(result.Violations, Is.Empty);
}
```

Never call a fixed `Task.Delay(...)` / `Thread.Sleep` before a scan — it races the DOM and makes the gate
flaky.

## Reporting the gate — violations into Allure, fail CI on non-empty

axe gives you everything to make a failure actionable: rule id, impact, helpUrl, and the failing
selector + fix summary. Attach the JSON and a readable summary to Allure so the report names the rule
without anyone re-running locally (cross-link `qa-allure-reporting-dotnet`):

```csharp
// Support/A11yReport.cs
using System.Text;
using System.Text.Json;
using Allure.Net.Commons;
using Deque.AxeCore.Commons;

public static class A11yReport
{
    public static void Attach(IReadOnlyList<AxeResultItem> violations)
    {
        if (violations.Count == 0) return;
        // Machine-readable: the full violation objects.
        AllureApi.AddAttachment("axe-violations.json", "application/json",
            Encoding.UTF8.GetBytes(JsonSerializer.Serialize(violations)));
        // Human-readable: one line per failing node.
        var sb = new StringBuilder();
        foreach (var v in violations)
        {
            sb.AppendLine($"[{v.Impact}] {v.Id}: {v.Help}").AppendLine($"  {v.HelpUrl}");
            foreach (var n in v.Nodes) sb.AppendLine($"  {string.Join(" ", n.Target.Selectors)}");
        }
        AllureApi.AddAttachment("axe-summary.txt", "text/plain", Encoding.UTF8.GetBytes(sb.ToString()));
    }
}
```

```csharp
[Test]
public async Task Should_have_no_a11y_violations_When_settings_loaded()
{
    await Page.GotoAsync("/settings");
    var result = await new AxeBuilder(Page).WithTags(new[] { "wcag2aa" }).AnalyzeAsync();
    A11yReport.Attach(result.Violations);     // attach BEFORE asserting, so a failure carries the report
    Assert.That(result.Violations, Is.Empty);
}
```

The CI job fails because the assertion fails — no extra wiring beyond uploading the Allure results and
the attached JSON (cross-link `qa-ci-pipelines-dotnet`). There is **no API key to inject**
here — call that out as the contrast with the visual-regression family (`percy` `PERCY_TOKEN` / `applitools`
`APPLITOOLS_API_KEY`): axe runs in-browser, so the only thing CI needs is the artifact upload.

## Anti-patterns

- **`Task.Delay(500)` / `Thread.Sleep` before `AnalyzeAsync()`.** axe scans the DOM at call time; a
  sleep races it and is slow (and `Thread.Sleep` violates the global rules). *Fix:* wait on a condition
  (`Locator.WaitForAsync`, spinner hidden), then scan.
- **One scan per page, ignoring interactive states.** Menus/modals/error states have their own a11y
  surface. *Fix:* scan per meaningful state after driving the app there.
- **Blanket `.DisableRules` / cranking tags down to make it pass.** That hides real failures. *Fix:*
  `.DisableRules` only a *documented* false-positive with a ticket; otherwise fix the markup.
- **Treating `Incomplete` as a pass.** axe abstained; the issue may be real. *Fix:* surface incompletes
  for manual review.
- **Asserting on `result.Violations.Count == 0` with a bare bool.** The bool throws away the diff.
  *Fix:* `Assert.That(result.Violations, Is.Empty)` — NUnit prints the collection contents on failure.
- **Scanning the whole page when the feature under test is one component.** Legacy debt drowns the new
  regression. *Fix:* `.Include(selector)` the component; gate it to zero.
- **Blocking on the async SDK with `.Result` / `.GetAwaiter().GetResult()`.** Violates async-all-the-way.
  *Fix:* `await AnalyzeAsync()`.
- **Calling a green axe run "accessible."** It covers ~30–40% of WCAG. *Fix:* pair with manual +
  assistive-tech testing; treat axe as the automated floor.

## Examples

**End-to-end: a per-component a11y gate that ships new features clean against a legacy page.**

```csharp
// Tests/SignupAccessibilityTests.cs
using Deque.AxeCore.Playwright;
using Microsoft.Playwright.NUnit;
using NUnit.Framework;

[TestFixture]
public class SignupAccessibilityTests : PageTest
{
    [Test]
    public async Task Should_have_no_a11y_violations_When_signup_form_empty()
    {
        var signup = new SignupPage(Page);
        await signup.GotoAsync();
        await signup.WaitUntilReadyAsync();                       // condition, not sleep

        var result = await AxeScanner.ForPage(Page).Include("#signup-form").AnalyzeAsync();
        A11yReport.Attach(result.Violations);
        Assert.That(result.Violations, Is.Empty);
    }

    [Test]
    public async Task Should_have_no_a11y_violations_When_validation_errors_shown()
    {
        var signup = new SignupPage(Page);
        await signup.GotoAsync();
        await signup.SubmitEmptyAsync();                          // page-object intent
        await signup.ErrorSummary.WaitForAsync(new() { State = WaitForSelectorState.Visible });

        var result = await AxeScanner.ForPage(Page).Include("#signup-form").AnalyzeAsync();
        A11yReport.Attach(result.Violations);
        Assert.That(result.Violations, Is.Empty);                // error state has its own a11y surface
    }
}
```

Lifecycle for this gate:
1. A dev adds a new field to the signup form.
2. CI runs the E2E suite; the axe scan runs in the same browser, on the live DOM, per state.
3. If the new field is missing a label, `Violations` is non-empty — the build fails with the rule id
   (`label`), the failing selector, and the helpUrl in the Allure attachment.
4. The dev fixes the markup; the gate goes green. Legacy debt on other pages is tracked separately by
   the ticketed allow-list, shrinking over time.

## Rules (hard constraints)

- A11y testing is an **assertion layer** on existing page objects/specs — inject the axe scan, don't
  author new page objects here. Page objects expose intent + locators; no selectors in tests.
- One logical assertion per test: `Assert.That(result.Violations, Is.Empty)` (or a filtered subset).
  Test names `Should_X_When_Y`.
- Async all the way: `await AnalyzeAsync()` — never `.Result` / `.GetAwaiter().GetResult()`.
- Stabilize on a **condition** (interactivity/visibility) before `AnalyzeAsync()`; never `Thread.Sleep`
  / fixed `Task.Delay` — axe scans the live DOM at call time.
- Scan **per meaningful state** (menu open, accordion expanded, errors shown), not once per page.
- Pick the WCAG level deliberately via `.WithTags` and apply it consistently (a shared factory).
- Triage with discipline: baseline known debt with **ticketed** allow-lists, `.DisableRules` only
  *documented* false-positives, and surface `Incomplete` for manual review — never silently pass it.
- **No SaaS, no API key** (axe runs in-browser) — the gate is local and deterministic. The only CI need
  is the violations-JSON/Allure artifact upload.
- axe covers ~30–40% of WCAG: it's the automated **floor**, not proof of accessibility. Pair with
  manual + assistive-tech testing.

## Cross-references

- `qa-accessibility-testing-typescript` — the **canonical** skill, TS / Vitest+Playwright
  (`new AxeBuilder({ page }).analyze()`, `results.violations`).
- `qa-accessibility-testing-java` — same skill, Java / TestNG
  (`com.deque.html.axe-core:playwright`, `new AxeBuilder(page).analyze()`, `results.getViolations()`).
- `references/lighthouse-ci.md` — the audit/score sibling: full-page
  perf/SEO/PWA + a11y **score** threshold, a separate Lighthouse pass. Run both: axe gates, Lighthouse
  trends.
- `qa-ui-test-author-playwright-dotnet` — the page objects/specs the axe scan is injected into. Author
  the flow there; add the a11y scan here.
- `qa-ci-pipelines-dotnet` — where the job fails on the assertion and the violations JSON
  is uploaded as an artifact. Note: **no secret to inject** (contrast `percy`/`applitools`).
- `qa-allure-reporting-dotnet` — attach the violations JSON + readable summary to the report.
- `qa-exploratory-charter-writer` — the manual/assistive-tech testing that covers the ~60% axe can't.
