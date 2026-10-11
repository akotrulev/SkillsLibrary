# Accessibility Testing — axe-core + Playwright (.NET 10 / Microsoft.Playwright 1.63 + NUnit)

`Deque.AxeCore.Playwright` runs the axe-core rule engine **inside your Playwright run**, against the live DOM,
and returns an `AxeResult` you assert on. It is an **assertion layer** on page objects that already exist: a
scan is added to a flow the page objects drive. axe runs entirely in the browser — no SaaS, no agent, no API
key.

> **What automation can and cannot do.** axe catches the machine-checkable share of WCAG — missing `alt`,
> unlabelled inputs, contrast, invalid ARIA, duplicate ids. It is a **floor, not proof**: keyboard traps,
> focus order and screen-reader comprehension still need manual and assistive-technology testing
> (`qa-exploratory-charter-writer`). A green scan means "no automated regressions", never "accessible".

## 1. Setup

`Deque.AxeCore.Playwright` **4.13.0** (checked on NuGet on 2026-10-11: the latest stable; a 4.14.0 alpha
exists) is already in the writer's `Directory.Packages.props`, so the project only references it:

```xml
<ItemGroup>
  <PackageReference Include="Deque.AxeCore.Playwright" />
</ItemGroup>
```

Exact, never a floating `4.*`. The package targets .NET Standard 2.1, bundles axe-core 4.13 and injects it at
scan time; it brings `Deque.AxeCore.Commons` 4.13.0 (the result and option types). Playwright, NUnit and
Allure.NUnit come from the writer's project (`qa/dotnet/skills/ui-test-author/playwright/assets/UiTests.csproj`).

## 2. The API — extension methods, no builder

The .NET package exposes **extension methods**, not a builder class (read from
`dequelabs/axe-core-nuget` at the 4.13.0 release, `packages/playwright/src`). The builder you know from the
TypeScript (`new AxeBuilder({ page })`) and Java (`new AxeBuilder(page)`) packages does not exist in .NET:

| Call | Scans |
|---|---|
| `await page.RunAxe(AxeRunOptions? options = null)` | The whole page |
| `await page.RunAxe(AxeRunContext context, AxeRunOptions? options = null)` | The page, limited by `Include` / `Exclude` CSS selectors (`List<AxeSelector>`) |
| `await locator.RunAxe(AxeRunOptions? options = null)` | The elements the locator matches — the component scan |

`RunAxeLegacy` exists on both and is marked obsolete — "a last resort", in Deque's words; never use it.

`AxeRunOptions` (namespace `Deque.AxeCore.Commons`) picks the ruleset:

| Property | Meaning |
|---|---|
| `RunOnly = RunOnlyOptions.Tags("wcag2a", …)` | Only rules with these tags — picking the tags is picking the WCAG level. `RunOnlyOptions.Rules(...)` names rules instead |
| `Rules = new Dictionary<string, RuleOptions> { ["rule-id"] = new() { Enabled = false } }` | Turns individual rules off (or on) on top of `RunOnly` |
| `ResultTypes`, `Iframes`, `Selectors`, `XPath`, `Ancestry`, `FrameWaitTime` | Raw axe run options — reach for them last |

The result, `AxeResult`:

| Member | Meaning |
|---|---|
| `Violations` | Failed rules — **the gate** |
| `Incomplete` | Rules axe could not decide (contrast over an image). **Not a pass** — a person reviews them |
| `Passes` / `Inapplicable` | Evidence; rarely asserted |

Each `AxeResultItem` has `Id` (`color-contrast`), `Impact` (`minor` · `moderate` · `serious` · `critical`),
`Help`, `HelpUrl`, `Tags` and `Nodes`. Each `AxeResultNode` has `Target` — an `AxeSelector` whose
`ToString()` is the selector path, through frames and shadow roots — `Html` and the `Any` / `All` / `None`
checks that explain the failure.

## 3. The native assertions come first

axe finds rule violations; it does not know what a control *should* be called. Assert the intended contract
with `ToHaveAccessibleNameAsync`, `ToHaveAccessibleDescriptionAsync`, `ToHaveAccessibleErrorMessageAsync`,
`ToHaveRoleAsync` and `ToMatchAriaSnapshotAsync` from
`qa/dotnet/skills/ui-test-author/playwright/references/assertions.md` §1–§2. A form gets both: an axe scan per
state, and a native assertion for the error message the story specifies (§5).

## 4. The shared helper — `Support/A11yScan.cs`

The conformance target is **WCAG 2.2 AA**, set once. Every scan attaches its violations and its incompletes
**before** the test asserts, so a failure carries the evidence and incompletes are visible on every run.

```csharp
using System.Text;
using Allure.Net.Commons;
using Deque.AxeCore.Commons;
using Deque.AxeCore.Playwright;
using Microsoft.Playwright;

namespace Example.UiTests.Support;

public sealed class A11yScan(IPage page)
{
    public static readonly IReadOnlyDictionary<string, string> FalsePositives = new Dictionary<string, string>
    {
        ["scrollable-region-focusable"] = "A11Y-2001: misfires on the virtualized order list",
    };

    public static readonly IReadOnlyDictionary<string, string> KnownViolations = new Dictionary<string, string>
    {
        ["color-contrast"] = "A11Y-1234",
        ["landmark-one-main"] = "A11Y-1235",
    };

    private const string ThirdPartyChat = "[data-testid='Chat.Widget']";

    public async Task<AxeResult> ScanPageAsync()
    {
        var result = await page.RunAxe(new AxeRunContext { Exclude = [new AxeSelector(ThirdPartyChat)] }, Options());
        Attach(result);
        return result;
    }

    public async Task<AxeResult> ScanAsync(ILocator region)
    {
        var result = await region.RunAxe(Options());
        Attach(result);
        return result;
    }

    public static IEnumerable<string> NewViolations(IEnumerable<AxeResultItem> violations) =>
        violations.Select(rule => rule.Id).Where(id => !KnownViolations.ContainsKey(id));

    public static IEnumerable<string> BlockingViolations(IEnumerable<AxeResultItem> violations) =>
        violations.Where(rule => rule.Impact is "critical" or "serious").Select(rule => rule.Id);

    private static AxeRunOptions Options() => new()
    {
        RunOnly = RunOnlyOptions.Tags("wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"),
        Rules = FalsePositives.Keys.ToDictionary(rule => rule, _ => new RuleOptions { Enabled = false }),
    };

    private static void Attach(AxeResult result)
    {
        AttachRules("axe-violations", result.Violations);
        AttachRules("axe-incomplete", result.Incomplete);
    }

    private static void AttachRules(string name, AxeResultItem[] rules)
    {
        var text = $"{rules.Length} rule(s)\n{string.Join('\n', rules.Select(Describe))}";
        AllureApi.AddAttachment(name, "text/plain", Encoding.UTF8.GetBytes(text), ".txt");
    }

    private static string Describe(AxeResultItem rule) =>
        $"[{rule.Impact}] {rule.Id}: {rule.Help} ({rule.HelpUrl})\n  {string.Join(", ", rule.Nodes.Select(node => node.Target))}";
}
```

- **The tags are the WCAG level.** `wcag22aa` is the 2.2 AA addition; `best-practice` adds axe's own
  recommendations beyond WCAG — add it here deliberately, never per test.
- **`ScanAsync(ILocator)`** scans what a page object's locator matches, so the test passes
  `_signupPage.Form`, never a selector, and the scan honours the project's test-id attribute.
  **`ScanPageAsync()`** scans the page and excludes embeds you do not own; `AxeRunContext` takes CSS selectors
  only, which is why the one exclusion is a constant here.
- **A rule is disabled only for a documented false positive**, with its ticket and reason in
  `FalsePositives`. Disabling a rule to hide a real failure hides a bug.
- The two dictionaries are read-only constants, not shared mutable state.
- The attachments are plain text — rule, impact, help link and the failing selectors — one pair per scan,
  so the Allure report names the fix without a local re-run. Three strings to `AddAttachment` would be read
  as a file path; the bytes overload takes an extension (`qa/dotnet/skills/evidence-capture/references/playwright.md` §6).

## 5. The core pattern — one scan per state

```csharp
using Microsoft.Playwright;

namespace Example.UiTests.Pages;

public sealed class SignupPage
{
    private readonly IPage _page;
    private readonly ILocator _submit;

    public SignupPage(IPage page)
    {
        _page = page;
        Form = page.GetByTestId("Signup.Form").Describe("Sign-up form");
        Email = Form.GetByTestId("Signup.Email").Describe("Email field");
        ErrorSummary = Form.GetByTestId("Signup.ErrorSummary").Describe("Error summary");
        _submit = Form.GetByTestId("Signup.Submit");
    }

    public ILocator Form { get; }

    public ILocator Email { get; }

    public ILocator ErrorSummary { get; }

    public async Task OpenAsync()
    {
        await _page.GotoAsync("/signup");
        await Form.WaitForAsync();
    }

    public async Task SubmitEmptyAsync()
    {
        await OpenAsync();
        await _submit.ClickAsync();
        await ErrorSummary.WaitForAsync();
    }
}
```

```csharp
using Example.UiTests.Pages;
using Example.UiTests.Support;
using NUnit.Framework;

namespace Example.UiTests.Tests;

[Category("a11y")]
public class SignupAccessibilityTests : BaseTest
{
    private SignupPage _signupPage = null!;
    private A11yScan _a11y = null!;

    [SetUp]
    public void CreatePages()
    {
        _signupPage = new SignupPage(Page);
        _a11y = new A11yScan(Page);
    }

    [Test]
    public async Task Should_HaveNoWcagViolations_When_SignupFormIsEmpty()
    {
        await _signupPage.OpenAsync();

        var result = await _a11y.ScanAsync(_signupPage.Form);

        Assert.That(result.Violations.Select(rule => rule.Id), Is.Empty, "axe violations in the empty sign-up form");
    }

    [Test]
    public async Task Should_HaveNoWcagViolations_When_ValidationErrorsShow()
    {
        await _signupPage.SubmitEmptyAsync();

        var result = await _a11y.ScanAsync(_signupPage.Form);

        Assert.That(result.Violations.Select(rule => rule.Id), Is.Empty, "axe violations in the sign-up form with errors");
    }

    [Test]
    public async Task Should_AnnounceEmailRequired_When_SignupSubmittedEmpty()
    {
        await _signupPage.SubmitEmptyAsync();

        await Expect(_signupPage.Email, "email field after an empty submit").ToHaveAccessibleErrorMessageAsync("Enter an email address");
    }
}
```

- axe analyzes the DOM **at call time**, so the page object drives the state and waits on a condition first:
  `OpenAsync()` returns once the form is visible, `SubmitEmptyAsync()` once the error summary is. An open menu,
  an expanded accordion and a form showing errors are different DOMs with different accessibility
  surfaces — scan each one. Never `Task.Delay` or `WaitForTimeoutAsync` before a scan.
- Asserting the **rule ids** makes the failure message the list of ids; the attachment holds the detail. One
  logical assertion per test, with a message naming the subject.
- The third test is §3's native assertion: the scan proves no rule broke; this test proves the field says
  what the story requires. `Expect(locator, "message")` [1.60] names the subject in the failure.
- `GotoAsync("/signup")` resolves against `BaseTest`'s `BaseURL` from `BASE_URL`. The `a11y` category runs in
  the normal UI job; it is only a filter handle.

## 6. Triage — a real app has existing violations

In order of preference:

1. **Gate new violations only.** Known debt lives in `KnownViolations`, each with its ticket; the dictionary
   only shrinks: `Assert.That(A11yScan.NewViolations(result.Violations), Is.Empty, "new axe violations on the dashboard")`.
2. **Disable a documented false positive** through `FalsePositives` (§4), never in a test.
3. **Read the incompletes.** `axe-incomplete` is attached on every scan; reviewing it is part of accepting a
   new screen. There is no `if` and no `Console.WriteLine` for them in a test.
4. **Ratchet by impact** when even the debt is large:
   `Assert.That(A11yScan.BlockingViolations(result.Violations), Is.Empty, "critical and serious violations")`,
   then widen to every impact once the backlog clears.

## 7. CI

The scans run inside the normal UI job (`qa/cicd/dotnet/skills/ci-pipelines`); the job fails because the
assertion fails. A failed scan's test also gets `BaseTest`'s trace, screenshot and video in
`<WorkDirectory>/playwright-artifacts/`, and the attachments travel in the Allure results. No secret is
needed — the contrast with Percy's and Applitools' keys.

## Anti-patterns

- **`new AxeBuilder(...)` in .NET.** The package has no builder. *Fix:* `RunAxe` on the locator or the page.
- **`RunAxeLegacy`.** Obsolete, to be removed. *Fix:* `RunAxe`.
- **`Task.Delay` or `WaitForTimeoutAsync` before a scan.** *Fix:* the page object waits for the state.
- **One scan per page, ignoring interactive states.** *Fix:* one scan per meaningful state.
- **Tags that stop at WCAG 2.1 AA.** *Fix:* `wcag22aa` in `Options()`.
- **Tags or exclusions repeated per test.** They drift. *Fix:* the helper.
- **`if (result.Incomplete.Length > 0) TestContext.Out.WriteLine(…)`.** A condition in a test, and silent in
  CI. *Fix:* the helper attaches the incompletes on every scan.
- **`Page.GotoAsync` or `RunAxe` in a test.** *Fix:* the page objects and the helper.
- **`Assert.That(result.Violations.Length == 0, Is.True)`.** The boolean drops the evidence. *Fix:* the rule
  ids `Is.Empty`, with a message.
- **A whole-page scan for one new component.** Legacy debt drowns the regression. *Fix:* `ScanAsync(locator)`.
- **`.Result` or `.GetAwaiter().GetResult()` on `RunAxe`.** *Fix:* await it.
- **A `Version=` on the `PackageReference` or a floating `4.*`.** *Fix:* `Directory.Packages.props` pins 4.13.0.
- **A green scan reported as "accessible".**

## Rules

- `Deque.AxeCore.Playwright` 4.13.0, pinned in `Directory.Packages.props`.
- WCAG 2.2 AA tags, exclusions and false positives live in one helper, built in the class's `[SetUp]`.
- One logical assertion per test: the violation ids `Is.Empty` with a message naming the subject, or a named
  subset.
- Stabilize through the page object before a scan; scan once per meaningful state.
- Every scan attaches its violations and incompletes with `AllureApi.AddAttachment(name, type, bytes, ".txt")`.
- Known debt is ticketed and only shrinks; false positives are documented.
- Tests reach pages through page objects and pass locators, never selectors.
- Pair every scan of a story's form with the native assertion for what the story specifies.

## Cross-references

- `references/lighthouse-ci.md` — the score-and-trend sibling.
- `qa/dotnet/skills/ui-test-author/playwright` — `BaseTest`, page objects, `references/assertions.md`.
- `qa/dotnet/skills/evidence-capture` — the failure evidence beside the scan's attachments.
- `qa/cicd/dotnet/skills/ci-pipelines` — the UI job the scans run in.
- `qa/reporting/dotnet/skills/test-reports` — Allure.NUnit wiring.
- `qa-accessibility-testing-typescript` (`@axe-core/playwright`), `qa-accessibility-testing-java`
  (`com.deque.html.axe-core:playwright`).
- `qa-exploratory-charter-writer` — the manual and assistive-technology testing axe cannot do.
