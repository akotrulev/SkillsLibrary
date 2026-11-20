---
name: desktop-window-objects
description: Use when creating or updating a C# window object for a macOS or Windows app (Appium or FlaUI) from explored elements. Triggers "create a window object". Not for finding elements.
disable-model-invocation: true
---

# QA — Desktop Window Object Builder (.NET)

Turns a discovered element inventory into a **C# window object**: a `BaseWindow` subclass under `DesktopTests/Windows/`. It consumes the element table and locator rungs from `qa/dotnet/skills/desktop-screen-explorer` (or an inventory the user supplies) and emits or updates one window class. It owns **codegen, multi-window and dialog handling, waits, and the create/update diff**, in two lanes: **Appium** (default, macOS and Windows) and **FlaUI 5.0.0** (Windows only). The shared rules (id contract, window-object rules, window scoping) are `qa/_shared/desktop-testing`; the NUnit conventions are `qa/dotnet/skills/ui-test-author/appium`. The mobile twin is `qa/dotnet/skills/mobile-screen-objects`.

**One lane per suite, never mixed.** Read `DesktopTests.csproj`: `Appium.WebDriver` means the Appium lane, `FlaUI.UIA3` the FlaUI lane. Both packages present is a defect to report.

## Inputs needed

1. **Window name** (PascalCase: `LibraryWindow`, `SettingsWindow`, `ExportDialog`) and whether it is a main window, a document window, a sheet or a dialog.
2. **Element list**: per element the name, type and rung from the explorer (the test id first).
3. **Landmark**: one container id that proves the window is up (`VerifyWindowLoaded()`).
4. **Actions**: user-intent actions and, for each, whether it opens another window or dialog (→ its class).
5. **Lane and target project**: Appium or FlaUI, the repo path and the existing `DesktopTests/Windows/` convention.

## Conventions

The standards an emitted object must meet are the qa-dotnet rule files `desktop-tests.md`, `page-objects.md` and `automation.md` (the project's copy in `.claude/rules/qa-dotnet/`, or the plugin's in `qa/dotnet/skills/rules/`). The codegen specifics:

- Element access goes through `BaseWindow`'s finders, in ladder order: `ByTestId` (Appium `MobileBy.AccessibilityId`; FlaUI `ByAutomationId`) → a finder scoped to a container for rows → a named label or native fallback → XPath last.
- Each id is a `private const string {Element}Id`; a fallback is `{Element}Fallback`. Elements are private; a window exposes intent methods and queries, never an `AppiumElement` or `AutomationElement`.
- A navigation action returns the destination's window object; a same-window action returns `void`.
- Namespace `DesktopTests.Windows`, file `DesktopTests/Windows/<Window>.cs`. Repeating rows are region components keyed by a visible value and re-resolved inside their container; native controls (a combo box, a date picker, a tab view, a table) are control components in `DesktopTests/Components/Controls/`, written at first use. Neither extends `BaseWindow`.
- Per-platform ids (only where one object serves both apps) live in a locator map keyed by `PLATFORM`: one accessor per element, and no action branches on the platform.

## Template: Appium lane

```csharp
using OpenQA.Selenium;
using OpenQA.Selenium.Appium;
using OpenQA.Selenium.Support.UI;

namespace DesktopTests.Windows;

public abstract class BaseWindow
{
    private static readonly TimeSpan Timeout = TimeSpan.FromSeconds(10);

    protected AppiumDriver Driver { get; }

    protected BaseWindow(AppiumDriver driver) => Driver = driver;

    public abstract void VerifyWindowLoaded();

    internal static By TestId(string id) => MobileBy.AccessibilityId(id);

    internal static WebDriverWait Wait(AppiumDriver driver, string message)
    {
        var wait = new WebDriverWait(driver, Timeout) { Message = message };
        wait.IgnoreExceptionTypes(typeof(NoSuchElementException), typeof(StaleElementReferenceException));
        return wait;
    }

    protected AppiumElement ByTestId(string id) => Present(TestId(id));

    protected AppiumElement ByName(string name) => Present(By.Name(name));

    protected AppiumElement ByXPath(string xpath) => Present(By.XPath(xpath));

    private AppiumElement Present(By locator) =>
        Wait(Driver, $"No element found for {locator}").Until(_ => Driver.FindElements(locator).FirstOrDefault())!;
}
```

```csharp
using NUnit.Framework;
using OpenQA.Selenium.Appium;

namespace DesktopTests.Windows;

public sealed class LibraryWindow : BaseWindow
{
    private const string RootId = "Library.Window";
    private const string SearchFieldId = "Library.SearchField";
    private const string AlbumTableId = "Library.AlbumTable";

    public LibraryWindow(AppiumDriver driver) : base(driver) { }

    public override void VerifyWindowLoaded() =>
        Assert.That(Wait(Driver, "Library.Window was not found").Until(_ => ByTestId(RootId).Displayed), Is.True,
            "LibraryWindow is not visible");

    public void SearchFor(string text) => ByTestId(SearchFieldId).SendKeys(text);

    public AlbumRow Album(string title) => new(Driver, ByTestId(AlbumTableId), title);
}
```

The row is picked by its content, never by position, and re-resolved from its container on each call, because an `AutomationId` repeats across rows and is unique among siblings only:

```csharp
using OpenQA.Selenium.Appium;

namespace DesktopTests.Windows;

public sealed class AlbumRow
{
    private const string RowId = "Library.Row";
    private const string TitleId = "Library.Row.Title";

    private const string ArtistId = "Library.Row.Artist";

    private readonly AppiumDriver _driver;
    private readonly AppiumElement _table;
    private readonly string _title;

    internal AlbumRow(AppiumDriver driver, AppiumElement table, string title)
    {
        _driver = driver;
        _table = table;
        _title = title;
    }

    public string Artist() => Row().FindElement(BaseWindow.TestId(ArtistId)).Text;

    public void Open() => Row().Click();

    private AppiumElement Row() =>
        BaseWindow.Wait(_driver, $"No {RowId} shows {_title}").Until(_ =>
            _table.FindElements(BaseWindow.TestId(RowId))
                .FirstOrDefault(row => row.FindElement(BaseWindow.TestId(TitleId)).Text == _title))!;
}
```

On macOS a row that combines its children (`.accessibilityElement(children: .combine)`) exposes only the row id: match the key against the row's own `Text` and drop the child accessors.

A fallback (no id yet): name the constant `*Fallback`, prefer a native query to XPath and add the `missing-testids.md` row. On Windows `By.Name` reads the UIA `Name`; on Mac2 `name` is the `identifier`, so a macOS label fallback is a `predicate string` on `label` (see the explorer for how to send it):

```csharp
private const string ExportButtonFallback = "Export…";
private AppiumElement ExportButton() => ByName(ExportButtonFallback);
```

## Template: FlaUI lane (Windows only)

A window object here wraps a FlaUI `Window` (or a container `AutomationElement`) and the automation. FlaUI's own `Window` class is not extended: ours is `BaseWindow`.

```csharp
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Conditions;
using FlaUI.Core.Tools;
using FlaUI.UIA3;

namespace DesktopTests.Windows;

public abstract class BaseWindow
{
    private static readonly TimeSpan Timeout = TimeSpan.FromSeconds(10);

    protected AutomationElement Root { get; }

    protected BaseWindow(AutomationElement root) => Root = root;

    public abstract void VerifyWindowLoaded();

    internal static AutomationElement Present(AutomationElement scope, Func<ConditionFactory, ConditionBase> condition, string what) =>
        Retry.WhileNull(() => scope.FindFirstDescendant(condition), Timeout, throwOnTimeout: true,
            timeoutMessage: $"No element found for {what}").Result!;

    protected AutomationElement ByTestId(string id) => Present(Root, cf => cf.ByAutomationId(id), id);
}
```

```csharp
using FlaUI.Core.AutomationElements;
using NUnit.Framework;

namespace DesktopTests.Windows;

public sealed class LibraryWindow : BaseWindow
{
    private const string RootId = "Library.Window";
    private const string SearchFieldId = "Library.SearchField";

    public LibraryWindow(AutomationElement window) : base(window) { }

    public override void VerifyWindowLoaded() =>
        Assert.That(ByTestId(RootId).IsAvailable, Is.True, "LibraryWindow is not visible");

    public void SearchFor(string text) => ByTestId(SearchFieldId).AsTextBox().Enter(text);
}
```

- A FlaUI row is a region component taking its container `AutomationElement` and a row key: `container.FindAllDescendants(cf => cf.ByAutomationId(RowId)).FirstOrDefault(row => row.FindFirstDescendant(cf => cf.ByAutomationId(TitleId))?.Name == title)` inside `Retry.WhileNull`, re-resolved on each call, never an index.
- `Retry.WhileNull` is the wait; the options (`throwOnTimeout`, `timeoutMessage`) are from the FlaUI wiki and were not compiled here. Never `Thread.Sleep` and never `Wait.UntilInputIsProcessed` as a stand-in for a condition.
- Search from the window or a container, never from `automation.GetDesktop()`.
- `ByName` (a label locator) is the fallback rung, with a `missing-testids.md` row.

## Multi-window and dialogs

- **A window object is bound to one window.** The action that opens another window returns the destination's object, and its constructor or `VerifyWindowLoaded()` switches to it. Switching is a method on `BaseWindow`, never inline in a test.
- **Mac2:** find the window with `Driver.ExecuteScript("macos: listWindows")` (driver 4.5.0 and later) and match on `title`. **WinCore:** `Driver.WindowHandles` omits untitled windows, so use `Driver.ExecuteScript("windows: getWindows")` and match on `title` or `className`, then `Driver.SwitchTo().Window(handle)`.
- **FlaUI:** a window is its own `Window`: `app.GetAllTopLevelWindows(automation)` and match `Title`, or `window.ModalWindows` for a dialog opened from it. A message box or file dialog is another window, not a descendant.
- A dialog that must appear is asserted by waiting on its landmark, with a message naming the dialog; the action that confirms or cancels returns the parent window's object.
- A system panel (open/save, permission) is another process: model it as its own small object read from its tree, or report it. A UAC prompt is never driven.
- A quit with unsaved work is asserted: the confirmation prompt appears, then the test chooses.

## Waits

`BaseWindow.Wait` (`WebDriverWait`, Appium) or `Retry.WhileNull` (FlaUI) is the only wait. Add a new wait to the base class, never inline in a window object or a test; no `Thread.Sleep` or `Task.Delay`, including after a click or a window open. The timeout message names the element and the window. Implicit wait stays zero.

## Procedure

1. **Check for an existing object.** Glob `**/Windows/<Window>.cs`. Exists → **update** (step 4). No `DesktopTests/Windows/` → run `qa/dotnet/skills/desktop-project-setup` first.
2. **Map each element to a constant and finder** by its rung. Test-id elements use `ByTestId`; fallbacks are `*Fallback` with a `missing-testids.md` row. Each repeating group becomes a region component keyed by a visible value inside its container; each native control a control component (reuse the one in `Components/Controls/` when it exists).
3. **Write the class**: constants, constructor, `VerifyWindowLoaded()` on the landmark, one intent-named action per user action (no flag parameter, no platform `if`), one query method per datum a test reads, returning a value. Stub any destination window that does not exist.
4. **Update mode, diff before writing:**
   - New element, not in the class → add constant and accessor or action.
   - Constant in the class, element gone → flag and **ask** before deleting (it may belong to a state not reached).
   - An id changed → update the constant and note a breaking rename.
   - A fallback where an id now exists → upgrade to `ByTestId`, rename, drop the `missing-testids.md` row.
   - Never reorder or rename public methods tests already call without flagging it.
5. **Verify:** `dotnet build` clean. Confirm the landmark matches what the explorer reported.
6. **Report:** class created or updated (diff summary), counts (id-backed / fallback / ⚠ XPath), destination stubs, open questions.

## Rules

- **Discovery is not this skill's job**: never invent a locator.
- One class per window; update in place rather than creating a duplicate.
- A window object never calls `Driver.FindElement` or `FindFirstDescendant` outside `BaseWindow`'s finders and scoped components. The only assertion inside an object is `VerifyWindowLoaded()`.
- Everything else is the rule files named under Conventions; where they and this skill disagree, the rule files win.
