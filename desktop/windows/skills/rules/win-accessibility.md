---
paths:
  - "**/*.xaml"
  - "**/*{Page,Window,Control,Dialog,View,Form}.xaml.cs"
  - "**/*{Form,UserControl}.cs"
  - "**/{Views,Pages,Controls,Dialogs,Forms}/**/*.cs"
---

<!-- desktop-windows rules v1 (2026-11-15): accessibility, keyboard and test ids. Installed by /desktop-windows:rules; edit the paths above to where this project keeps its UI. -->

# Windows accessibility, keyboard and test-id standards

Severity tags as in the core C# rules. The codebase wins where it consistently does otherwise. The target is WCAG 2.2 AA on UI Automation, Narrator and the keyboard. Recipes: `accessibility`, `test-ids`.

## Names, roles and announcements

- Every interactive element has a localized accessible name (`AutomationProperties.Name`, or `AccessibleName` on WinForms). *major*
- Semantic controls, not clickable panels; a custom control exposes the right `AutomationPeer`, control pattern and change events. *major*
- A status or failure change is announced (`LiveSetting`, `RaiseNotificationEvent`); an `InfoBar` announces itself, a hand-built banner does not. *major*
- Decorative elements are `AccessibilityView="Raw"`. *minor*

## Keyboard and focus

- Every command is reachable from the keyboard; the focus visual is never removed; tab order is complete and follows reading order. *major*
- Access keys on menus and buttons, standard shortcuts kept; a dialog or flyout returns focus to its trigger on close. *major*

## Contrast, text and settings

- Text scales with the system setting and is never locked (`IsTextScaleFactorEnabled` stays true). *major*
- High Contrast is honoured on each screen: system colours or theme resources with a `HighContrast` entry. *major*
- No state by colour alone. *major*

## Test ids

- Every interactive element and every list or grid container carries `AutomationProperties.AutomationId` (WinForms: a deliberate `Name`). *major*
- Ids are `Screen.ElementType[.Qualifier]`, PascalCase, dot-separated, static; never the accessible name, never localized, never an index, GUID or state value. *major*
- Every list carries its own id and rows are located inside it; rows and the parts a test reads are tagged inside the `DataTemplate`. *major*
- Banners, loading and failed regions, empty states and dialogs carry ids. *major*
- `RuntimeId` is never a locator. *major*
