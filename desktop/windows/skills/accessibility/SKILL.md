---
name: accessibility
description: Use when a Windows app needs accessibility (UI Automation names and peers, Narrator, keyboard and access keys, High Contrast, text scaling). Triggers "make it accessible". Not for test ids (test-ids).
disable-model-invocation: true
---

# Windows — Accessibility

How a Windows app is made usable without a mouse or a screen: **every interactive element has a name UI Automation exposes, every command is reachable from the keyboard with a visible focus, High Contrast and text scaling are honoured, and no state is shown by colour alone.** Target: WCAG 2.2 AA (EN 301 549; European Accessibility Act in force since 2025-06-28). Audit rows: section M of `desktop-windows:standards-audit`. Design facts: `design/ui-ux-pro-max --stack winui`.

## Version lane

| Concern | WinUI on WinAppSDK 2.6 (primary) | Note |
|---|---|---|
| Tree | UI Automation, from the XAML element tree; built-in controls ship peers | `FrameworkElementAutomationPeer` for custom controls |
| Name | `AutomationProperties.Name` or `LabeledBy` | Same attached property in WPF; WinForms uses `AccessibleName` |
| Screen readers | Narrator (`Win+Ctrl+Enter`), NVDA | Both read the UIA tree: one implementation |
| Inspection | **Accessibility Insights for Windows**: Live inspect, automated checks (FastPass), tab-stops view | Microsoft's recommended tool (Learn, "Test apps built with the Windows App SDK and WinUI 3", 2026-09-10) |
| `[WPF]` | Same properties; `AutomationPeer` overrides | `TextScaleFactor` is not applied to WPF text automatically |
| `[WinForms]` | `AccessibleName` / `AccessibleRole` / `AccessibleDescription`; .NET 11 exposes `TextScaleFactor` through `SystemVisualSettings` | |
| `[C++]` | Same XAML properties; peers are runtime classes in IDL | `desktop-windows:cpp-winrt` |

Detect first: custom controls (`OnCreateAutomationPeer`), `AutomationProperties` use, `HighContrast` theme dictionaries, and whether a keyboard-accelerator layer exists. Extend them; never rewrite a working peer.

## When to use

- A new screen or control; "Narrator reads nothing here"; a High Contrast bug; "tab order is wrong"
- Reviewing a screen against the §8 accessibility rows

## When NOT to use

- `AutomationId` for E2E → `desktop-windows:test-ids` (the id is never the name)
- Accelerators and access keys as *commands* → `desktop-windows:windows-and-navigation`
- Theme dictionaries and the type ramp → `desktop-windows:styling`

---

## The five rules

1. **Name every interactive element.** The name is for people: short, localized, no role word (`Delete order`, not `Delete button`).
2. **Use the semantic control.** `Button`, `HyperlinkButton`, `ListView`, `ToggleSwitch` carry role, state and keyboard behaviour. A clickable `Border` or `Grid` with a `Tapped` handler has none of them and is a finding.
3. **Every core scenario completes with the keyboard**, and focus is always visible.
4. **High Contrast and text scaling work** because the layout uses theme resources and no fixed text size.
5. **Never state by colour alone**, never contrast below 4.5:1 for text and 3:1 for graphics and focus.

## Names, roles, descriptions

| Need | Property | Rule |
|---|---|---|
| Name | `AutomationProperties.Name` | Set when the visible content is not a good name (icon-only button) |
| Name from a label | `AutomationProperties.LabeledBy="{x:Bind FieldLabel}"` | For inputs whose label is a separate `TextBlock`; `Header` on `TextBox` / `ComboBox` / `NumberBox` already does it |
| Help | `AutomationProperties.HelpText` | One sentence of what happens, shown by Narrator after a pause; not a repeat of the name |
| Decorative | `AutomationProperties.AccessibilityView="Raw"` | Dividers, background images, a glyph beside text already read |
| Group | A container with a name | A `Grid` is not announced; a `ListView`, `Expander` or `GroupBox`-style header is |
| Heading | `AutomationProperties.HeadingLevel="Level1"` | One per section; Narrator navigates by heading |
| Landmark | `AutomationProperties.LandmarkType` (`Navigation`, `Main`, `Search`, `Form`) | One `Main` per window |
| Position | `PositionInSet` / `SizeOfSet` | Only for a custom list built from non-list controls |
| Required | `AutomationProperties.IsRequiredForForm="True"` | On required inputs, with the visible marker |

```xaml
<Button AutomationProperties.AutomationId="Orders.DeleteButton"
        AutomationProperties.Name="Delete order"
        Command="{x:Bind ViewModel.DeleteCommand}">
    <FontIcon Glyph="&#xE74D;" AutomationProperties.AccessibilityView="Raw" />
</Button>
```

- An icon-only control gets a `ToolTip` with the same words, so sighted users get them too.
- **Do not hide content from screen readers with `Visibility="Collapsed"`** to keep it visible: collapsed removes it for everyone. Use `AccessibilityView="Raw"` for the decorative case.
- A `ListView` row's name is its content text; set `AutomationProperties.Name` on the item template root only when the row's text alone is ambiguous (`{x:Bind Title}, {x:Bind Status}`).

## Custom controls and peers

A control derived from `Control` gets a peer for free only for the role it inherits. Override `OnCreateAutomationPeer` and derive from `FrameworkElementAutomationPeer` when the role is new:

```csharp
public sealed class RatingBar : Control
{
    protected override AutomationPeer OnCreateAutomationPeer() => new RatingBarAutomationPeer(this);
}

public sealed class RatingBarAutomationPeer(RatingBar owner) : FrameworkElementAutomationPeer(owner), IRangeValueProvider
{
    protected override string GetClassNameCore() => nameof(RatingBar);
    protected override AutomationControlType GetAutomationControlTypeCore() => AutomationControlType.Slider;
    protected override object GetPatternCore(PatternInterface patternInterface) =>
        patternInterface == PatternInterface.RangeValue ? this : base.GetPatternCore(patternInterface);

    public double Value => ((RatingBar)Owner).Value;
    public double Minimum => 0;
    public double Maximum => 5;
    public double SmallChange => 1;
    public double LargeChange => 1;
    public bool IsReadOnly => false;
    public void SetValue(double value) => ((RatingBar)Owner).Value = value;
}
```

- The **pattern is the contract** (Invoke, Toggle, RangeValue, Selection, ExpandCollapse): a control that acts like a button implements Invoke and also handles Space and Enter.
- Raise property changes (`RaisePropertyChangedEvent`) when the value changes, or Narrator reads a stale value.
- Prefer composing built-in controls to writing a peer. A peer is code to test: Accessibility Insights, then a Narrator pass.

## Live regions and announcements

| Need | Use |
|---|---|
| A status line that changes (`Saved`, `3 results`) | `AutomationProperties.LiveSetting="Polite"` on the `TextBlock` |
| A failure that needs attention now | The `InfoBar` (it announces on open); `Assertive` only for a blocking error |
| A one-off announcement from code | `AutomationPeer.RaiseNotificationEvent(kind, processing, message, activityId)` on the element's peer |
| Loading progress | `ProgressRing` / `ProgressBar` with a `Name`; announce the result, not each tick |

Do not announce on every keystroke or timer tick; it floods Narrator.

## Keyboard and focus

- **Tab order follows reading order.** Fix the layout before reaching for `TabIndex`; set `TabIndex` on every control of a group or on none (an unset control sorts after the set ones).
- `IsTabStop="False"` for decoration; a control that must be reachable never has it off.
- **Access keys** (`AccessKey="S"`, shown after `Alt`) for the commands of a dialog and menu; **accelerators** (`KeyboardAccelerator Modifiers="Control" Key="S"`) for the app's commands; both listed in `desktop-windows:windows-and-navigation`. Standard shortcuts (`Ctrl+C/V/Z/S/F`, `F5`, `Esc`) keep their meaning.
- Arrow keys move inside a composite control (`ListView`, `TabView`, menus, `RadioButtons`); `Tab` moves between composites. `XYFocusKeyboardNavigation="Enabled"` on a custom grid of tiles.
- **Focus is visible and never lost.** Keep the default focus visual; if restyled it meets 3:1 against its surroundings (`FocusVisualPrimaryBrush`). After a dialog closes, focus returns to the control that opened it; after a delete, to the next row, not to the window.
- A new page or window sets initial focus to its main control (`Control.Focus(FocusState.Programmatic)` in `Loaded`), never to the title bar.
- A `ContentDialog` traps focus by design; a custom overlay must also (`TabFocusNavigation="Cycle"`), and closes on `Esc`.
- No hover-only information or command; no gesture-only command (drag with no keyboard equivalent).

## High Contrast

- Colours come from `{ThemeResource}` brushes. A control with a hex literal ignores the user's palette and is a finding (`desktop-windows:styling`).
- A custom theme dictionary adds a `HighContrast` key and maps to the system colour brushes (`SystemColorWindowColor`, `SystemColorWindowTextColor`, `SystemColorHighlightColor`, `SystemColorGrayTextColor`, `SystemColorHotlightColor`).
- Images that carry meaning get a High Contrast variant (`.contrast-high` qualifier) or use a `FontIcon`, which takes the foreground.
- **Test each screen in two High Contrast themes** (Settings → Accessibility → Contrast themes: Aquatic and Night sky), then in a light and a dark theme.
- React to a live change with `AccessibilitySettings.HighContrastChanged` only for drawn content (a canvas); styled controls update themselves.

## Text scaling and magnification

- WinUI text scales with *Settings → Accessibility → Text size* when `IsTextScaleFactorEnabled` stays `True` (the default). **Never set it to `False`** and never lock a font size.
- No fixed `Height` on a text-bearing element; `MinHeight`, `Auto` rows, `TextWrapping`. Test at 225% text with the window at its minimum size.
- Layout survives display scaling (100–300%) and a window resized small; scroll before clip.
- `UISettings.TextScaleFactor` / `TextScaleFactorChanged` only for text that is drawn (a canvas or a render surface).
- Windows Magnifier follows keyboard focus: keep focus where the action is.

## Colour, motion, transparency

- State is colour + shape + text: an error is a red border **and** an icon **and** a message; a selected row has an indicator, not only a fill.
- Contrast 4.5:1 for body text, 3:1 for large text, icons and focus; check both themes.
- Honour **animation effects off**: read `UISettings.AnimationsEnabled`, and replace motion with a fade or an instant change (`desktop-windows:styling` owns the presets).
- Honour **transparency effects off**: Mica and Acrylic fall back to a solid brush by themselves in the built-in materials; a custom translucent surface reads `UISettings.AdvancedEffectsEnabled`.
- No flashing content above three flashes per second.
- A time limit (a toast, a timeout) is extendable or absent; the persistent `InfoBar` never auto-dismisses.

## Forms

The label, the error text and the required marker are programmatically tied to the field (`Header`, `LabeledBy`, an error `TextBlock` with `LiveSetting="Polite"`); the error never shows by a red border only. Details: `desktop-windows:forms`.

## Narrator pass (60 seconds per screen)

1. Start Narrator (`Win+Ctrl+Enter`). Press `Tab` through the screen: each stop announces name, role and state.
2. Scan mode (`Caps+Space`), then arrow through: headings, landmarks and lists announce as such.
3. Trigger a failure and a success: both are announced without moving focus.
4. Open and close a dialog: focus goes in and returns.
5. Run Accessibility Insights FastPass on the window: zero automated failures; walk the tab-stops view.

Narrator and NVDA are manual passes; a static read proves names and properties exist, never what is spoken, so the audit reports **requires dynamic test → `qa-security`'s accessibility lane or `qa-desktop-<lang>`** as unverified.

## Telemetry

None for the properties. A metric `app.accessibility_setting` (high contrast on/off, text scale bucket) is a business decision, never a default, and never carries user data.

## Generation steps

1. Detect lane and existing peers; read `design/ui-ux-pro-max --stack winui` for the contrast and focus rows.
2. Build with semantic controls; add names to every icon-only control.
3. Walk the tab order and fix the layout first; add access keys and accelerators.
4. Add live regions for status and failure.
5. Replace any literal colour with a theme resource and add the `HighContrast` mapping.
6. Run the Narrator pass and Accessibility Insights; fix; run High Contrast and 225% text.

## Validation

- `rg -n "<(Button|ToggleButton|AppBarButton|HyperlinkButton)[^>]*>" -g '*.xaml'` hits with no `Content` text and no `AutomationProperties.Name`: none.
- No `Tapped` / `PointerPressed` on a non-interactive element used as a button.
- No `IsTextScaleFactorEnabled="False"`.
- Accessibility Insights FastPass: clean on every screen touched.

## Common gotchas

- **Icon-only button with no `Name`** — Narrator says "button".
- **`Name` set to the role or the id** — `Delete button`, `btnDelete`.
- **`Collapsed` used to hide a duplicate from readers** — it hides it from everyone.
- **`AutomationProperties.Name` set on a container that also has focusable children** — the children are shadowed in some readers; name the control that takes focus.
- **A custom peer with no `RaisePropertyChangedEvent`** — the value read is stale.
- **Focus lost after a `ListView` item is removed** — the window gets focus; set it to the neighbour.
- **Mica over a custom translucent panel** — in High Contrast the text sits on the system window colour only if the brush is a theme resource.
- **A hard-coded 12 px font** — it ignores the text-size setting.

## Handoffs

- Ids are separate and never names → `desktop-windows:test-ids`; translations of names → `desktop-windows:languages`
- Accelerators, access keys, window commands → `desktop-windows:windows-and-navigation`
- Theme and motion → `desktop-windows:styling`; failure region and `InfoBar` → `desktop-windows:error-handling`
- Mac counterpart → `desktop-macos:accessibility`
