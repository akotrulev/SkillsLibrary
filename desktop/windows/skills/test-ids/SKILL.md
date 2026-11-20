---
name: test-ids
description: Use when adding AutomationId to a Windows app so WinCore, NovaWindows or FlaUI can locate elements. Triggers "E2E can't find this control". Not for writing desktop tests (qa-desktop-typescript).
disable-model-invocation: true
---

# Windows — Testability (`AutomationId` writer)

Adds and audits test ids on WinUI, WPF, WinForms and C++/WinRT apps so desktop suites locate every element by one stable id. It is the dev-side half of a loop QA owns: `qa-desktop-<lang>`'s explorer reads the live UIA tree and files a `missing-testids.md`; this skill consumes it. The mobile twins (`mobile-android:test-ids`, `mobile-ios:test-ids`) carry the naming and static-row rules; the macOS twin is `desktop-macos:test-ids`. Audit rows: section R of `desktop-windows:standards-audit`.

## Version lane

| Concern | WinUI on WinAppSDK 2.6 (primary) | Note |
|---|---|---|
| Id | `AutomationProperties.AutomationId="Login.EmailField"` | The UIA `AutomationId` property |
| `[WPF]` | The same attached property; WPF controls with no id and no `x:Uid` expose none | |
| `[WinForms]` | The UIA `AutomationId` of a control is its `Name` property; `AccessibleName` is the label, not the id | **Not verified against a primary source here**: confirm in the live tree with Accessibility Insights |
| `[C++]` | The same XAML attached property in markup | Win32 controls: the control ID |
| WebView2 content | Not UIA: Playwright over CDP (`connectOverCDP`), by the page's own `data-testid` | `fe-react` / `fe-blazor` rules |
| Uno | `AutomationId` takes effect only with `IsUiAutomationMappingEnabled=true` | Detected and named, not taught (D5) |

## What the tools read — the contract E1 builds on

Verified 2026-11-15 against the WinCore `API.md`, the FlaUI.WebDriver README and Microsoft Learn ("Use the AutomationID property").

| Element kind | Property the developer sets | WinCore 3.3.2 (Appium 3) | FlaUI 5.0.0 / FlaUI.WebDriver |
|---|---|---|---|
| WinUI / WPF / C++/WinRT XAML element | `AutomationProperties.AutomationId` | `accessibility id` (`~Id` in WebdriverIO): a native `PropertyCondition(AutomationId)`, rated the fastest strategy | `ByAutomationId` (FlaUI); `accessibility id` (WebDriver), `By.Id` and a CSS `#id` also map to the automation id |
| WinForms control | `Control.Name` (UIA `AutomationId`; see the lane note) | `accessibility id` | `ByAutomationId` |
| Win32 control | The control ID | `accessibility id` | `ByAutomationId` |
| List or container | Its **own** `AutomationId` | Relative find: `element.$("~Orders.Row")` searches only that element's descendants | `container.FindAll(TreeScope.Descendants, cf.ByAutomationId("Orders.Row"))` |
| Row inside a container | A static id, the same for every row (`Orders.Row`) | Found inside the container; the row is picked by the text of its child (`Orders.Row.Title`) or by position in the result | The same: enumerate inside the container |
| Label for people | `AutomationProperties.Name` | `name` strategy: **never an id** | `ByName`: never an id |
| Element with no id | — | `class name`, `name` or `xpath` fallback | `ByName` / `ByClassName`; each fallback is a row in `missing-testids.md` |

Facts that decide the rules:

- **`accessibility id` is the `AutomationId`.** WinCore's `id` strategy is the **`RuntimeId`**, a number that changes every run: **never use `id` for a stable locator.** NovaWindows 1.5.0 (the documented fallback) also maps `accessibility id` to the `AutomationId`.
- **`AutomationId` is unique among siblings only**, not across the tree (Learn). Two screens, or two rows of a list, may repeat an id. So **every container carries its own id**, and a locator starts at the window or at a container and descends; an absolute search (`driver.$`) covers the whole attached window.
- The id is absent on top-level application windows, on WPF elements with no id or `x:Uid`, and on Win32 controls with no control ID: the explorer files each as a missing id.
- WinCore 3.3.2 is the build for Appium 3 (4.x needs Appium 4); `appium-windows-driver` (WinAppDriver) is legacy and never taught here (D9).

## Naming: `Screen.ElementType[.Qualifier]`

PascalCase, dot-separated, ASCII. No spaces, snake_case, kebab-case, numeric ids, GUIDs, list indexes, state values or localized text.

- **Screen** — the page or window: `Login`, `Orders`, `Orders.Detail`.
- **ElementType** — the role: `SubmitButton`, `EmailField`, `List`, `Row`, `Tab`, `Banner`, `Toolbar`.
- **Qualifier** — a semantic name from code (an enum member, a field name, an action), never data.

```
Login.EmailField       Login.SubmitButton      Orders.List
Orders.Row             Orders.Row.Title        Orders.Row.Status
Orders.Banner          Orders.FailedRegion     Shell.NavItem.Orders
```

Ids are never localized, never derived from `Name`, and never changed to follow a copy edit: a rename breaks every suite that uses it (QA's `missing-testids.md` is the only change request).

## Tagging rules

### 1. What carries an id

| Element | Rule |
|---|---|
| Every interactive control | `Button`, `TextBox`, `PasswordBox`, `NumberBox`, `ComboBox`, `CheckBox`, `ToggleSwitch`, `RadioButtons` (and each option), `Slider`, `HyperlinkButton`, `MenuFlyoutItem`, `NavigationViewItem`, `TabViewItem`, `AppBarButton` |
| Every list and grid container | `ListView`, `GridView`, `ItemsRepeater`, `TreeView`, `DataGrid`-style controls: the container's own id, `Orders.List` |
| Every region the suite asserts on | The three-state regions (`Orders.FailedRegion`, `Orders.LoadingRegion`), the `InfoBar` (`Orders.Banner`), the empty state, dialogs (`Orders.DeleteDialog`) |
| Window-level structure | The toolbar, the title bar, the navigation pane: a container id each |
| Rows | The root of the `DataTemplate`: `Orders.Row`, and the parts a test reads: `Orders.Row.Title`, `Orders.Row.Status` |
| Not tagged | Decorative elements (`AccessibilityView="Raw"`), layout panels with no assertion, static text no test reads |

### 2. Where the id goes in each lane

```xaml
<Page>
    <Grid AutomationProperties.AutomationId="Orders.Content">
        <ListView AutomationProperties.AutomationId="Orders.List" ItemsSource="{x:Bind ViewModel.Rows}">
            <ListView.ItemTemplate>
                <DataTemplate x:DataType="vm:OrderRow">
                    <StackPanel AutomationProperties.AutomationId="Orders.Row">
                        <TextBlock AutomationProperties.AutomationId="Orders.Row.Title" Text="{x:Bind Title}" />
                        <TextBlock AutomationProperties.AutomationId="Orders.Row.Status" Text="{x:Bind Status}" />
                    </StackPanel>
                </DataTemplate>
            </ListView.ItemTemplate>
        </ListView>
        <Button AutomationProperties.AutomationId="Orders.RefreshButton"
                AutomationProperties.Name="Refresh orders" Command="{x:Bind ViewModel.RefreshCommand}" />
    </Grid>
</Page>
```

| Lane | How |
|---|---|
| WinUI, `[C++]` | The attached property in markup; `AutomationProperties` needs no namespace declaration in XAML |
| `[WPF]` | `AutomationProperties.AutomationId` in XAML |
| `[WinForms]` | Set `Name` in the designer or in code; give every control a deliberate name, not `button1` |
| Code-created controls | `AutomationProperties.SetAutomationId(element, "Orders.Row")` |
| Custom controls | Expose the property on the control's root; a peer's `GetAutomationIdCore()` returns the id from the element |
| Dynamic rows | The template root's id is static; the **content** (title) distinguishes rows. A per-item id (`Orders.Row.1234`) is a finding |

- **Prefer inline in the markup.** Do not add a wrapper control or a helper class just to carry ids.
- **A row id repeats among siblings, which UIA allows** and the house rule requires (static, no index, no data in the id). The suite enumerates inside `Orders.List` and picks by the child text or by position. Confirm in the live tree that the id lands on the row's element or its child (a `ListViewItem` wraps the template root: **built but unverified** for this release; the explorer's page source is the authority).
- A literal repeated in three or more places in code (a view or test helper) may be a `const` in a `static class` named for the screen; XAML keeps the literal.

### 3. The id and the name are separate

`AutomationProperties.Name` is the sentence a person hears (`Refresh orders`, localized). `AutomationId` is the stable token a machine finds (`Orders.RefreshButton`, never localized). Never set one from the other, never use the name as the id, and never change an id to fix a name (`desktop-windows:accessibility`).

### 4. Containers

Every container the suite searches inside has its id. A page with a toolbar, a list and a detail pane has three container ids; a dialog has its own; the `InfoBar` has its own. A locator then reads: window → container → row → part.

## The hand-off loop

1. `qa-desktop-<lang>` runs its screen explorer against the live app (WinCore page source, or `winapp ui inspect` where installed) and files **`missing-testids.md`**: each element with no `AutomationId`, the fallback locator it used, the screen, and its role.
2. This skill, run by the `desktop-windows` agent, takes the file, adds the ids by the naming rule, and removes each row it fixed.
3. The explorer reruns; a row that remains means the id did not reach the UIA tree (wrong element, a collapsed parent, a template root that is not exposed).

Where `winapp` is installed (0.8.0, preview), `winapp ui inspect` prints the tree with ids and is a quick self-check; where it is not, Accessibility Insights for Windows (Live inspect) shows `AutomationId` for the element under the cursor. Neither is required.

## Checking an id reached the tree

| Check | How |
|---|---|
| One element | Accessibility Insights → Live inspect → hover: `AutomationId` row |
| The tree | `winapp ui inspect` (optional), or the WinCore page source |
| Uniqueness | Within each container: every non-row id appears once; rows repeat the same id on purpose |
| No name leak | `rg -n "AutomationId=\"[^\"]*\s" -g '*.xaml'` — no spaces in an id |

## Telemetry

None. An id is not a metric and carries no data.

## Rules

1. Every interactive element and every list or grid container has an `AutomationId`.
2. `Screen.ElementType[.Qualifier]`, PascalCase, dot-separated, ASCII, static.
3. Never the accessibility name, never localized, never an index, a GUID, an id or a state.
4. Containers carry their own id; rows are located inside the container and picked by content.
5. Set inline; no wrapper control to carry ids.
6. WinCore's `id` strategy is the `RuntimeId`: QA uses `accessibility id`.
7. A rename of an id is a coordinated change with the QA suite.

## Generation steps

1. Detect the lane (UI framework, packaged or not) and any existing ids; extend the convention already used.
2. List the screens; for each, the containers, the interactive elements, the assertion regions.
3. Apply the names and set the property inline; for WinForms set `Name`.
4. Process `missing-testids.md` if QA filed one.
5. Check the tree with Accessibility Insights or the explorer; fix what did not reach it.

## Validation

- `rg -n "<(Button|TextBox|PasswordBox|NumberBox|ComboBox|CheckBox|ToggleSwitch|ListView|GridView|ItemsRepeater|HyperlinkButton|ToggleButton|AppBarButton|MenuFlyoutItem|NavigationViewItem|TabViewItem|InfoBar)\b(?![^>]*AutomationId)" --pcre2 -g '*.xaml'` — each hit is an untagged element (read the multi-line cases).
- No id contains a space, an index, a GUID or a Resource key.
- The explorer's run files no `missing-testids.md` rows for the screens touched.

## Common gotchas

- **The `Name` used as the id** — it is localized and changes with copy.
- **`id=` used in a WinCore locator** — it is the `RuntimeId`.
- **A list with no container id** — the locator starts at the window and finds another screen's rows.
- **An id on a layout panel above the list instead of the list** — the container the suite searches in has none.
- **A per-item id** — the id embeds data; the suite breaks on new data.
- **A `ContentDialog` and a `Flyout` live in their own popup tree** — the id is set inside, and the suite searches from the window root, not the page.
- **WinForms controls left as `button1`** — ids that mean nothing and collide.
- **Uno left without `IsUiAutomationMappingEnabled`** — every id is ignored.

## Handoffs

- Names and Narrator → `desktop-windows:accessibility`; dialogs and lists → `desktop-windows:ui-components`
- The explorer, the drivers and the suites → `qa-desktop-typescript`, `qa-desktop-java`, `qa-desktop-dotnet` (E1–E3)
- Dev-side tests of view models → `desktop-windows:unit-testing`; the macOS twin → `desktop-macos:test-ids`
