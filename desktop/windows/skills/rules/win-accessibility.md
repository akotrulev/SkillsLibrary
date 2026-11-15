---
paths:
  - "**/*.xaml"
  - "**/*{Page,Window,Control,Dialog,View,Form}.xaml.cs"
  - "**/*{Form,UserControl}.cs"
  - "**/{Views,Pages,Controls,Dialogs,Forms}/**/*.cs"
---

<!-- desktop-windows rules v1 (2026-11-15): accessibility, keyboard and test ids. Installed by /desktop-windows:rules; edit the paths above to where this project keeps its UI. -->

# Windows accessibility, keyboard and test-id standards

Severity tags as in the core C# rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise. The target is WCAG 2.2 AA on UI Automation, Narrator and the keyboard.

## Names, roles and announcements

- Every interactive element has an accessible name (`AutomationProperties.Name`, a bound label, or `AccessibleName` on WinForms); the name is for people and is localized. *major*
- Semantic controls, not clickable panels; a custom control exposes the right `AutomationPeer`, control pattern and change events. *major*
- A status or failure change is announced (`LiveSetting`, `RaiseNotificationEvent`); an `InfoBar` announces itself, a hand-built banner does not. *major*
- Decorative elements are `AccessibilityView="Raw"`; content is never `Collapsed` only to hide it from readers. *minor*
- A Narrator and Accessibility Insights pass is recorded for each screen touched. *minor*

## Keyboard and focus

- Every command is reachable from the keyboard; the focus visual is never removed; tab order is complete and follows reading order (`TabIndex`, `XYFocusKeyboardNavigation` only with a reason). *major*
- Access keys on menus and buttons, standard shortcuts kept; a focus trap (a dialog, a flyout) returns focus to its trigger on close. *major*

## Contrast, text and settings

- Text scales with the system setting and is never locked (`IsTextScaleFactorEnabled` stays true). *major*
- High Contrast is honoured: system colours or theme resources with a `HighContrast` entry, tested on each screen. *major*
- No state by colour alone; contrast 4.5:1 for text and 3:1 for graphics and focus. *major*
- Animation effects and transparency settings are honoured. *minor*

## Test ids

- Every interactive element and every list or grid container carries `AutomationProperties.AutomationId` (WinForms: a deliberate `Name`). *major*
- Ids are `Screen.ElementType[.Qualifier]`, PascalCase, dot-separated, static; never the accessible name, never localized, never an index, a GUID or a state value. *major*
- An id is unique among siblings only, so every list carries its own id and rows are located inside it; rows and the parts a test reads are tagged inside the `DataTemplate`. *major*
- Banners, loading and failed regions, empty states and dialogs carry ids. *major*
- `RuntimeId` (`id` in WinCore) is never a locator. *major*
