---
paths:
  - "**/*.xaml"
  - "**/*{Page,Window,Control,Dialog,View,Template}.xaml.cs"
  - "**/{Views,Pages,Controls,Dialogs}/**/*.cs"
---

<!-- desktop-windows rules v1 (2026-11-15): WinUI and XAML. Installed by /desktop-windows:rules; edit the paths above to where this project keeps its views. Apply to WinUI projects only. -->

# WinUI and XAML standards

Severity tags as in the core C# rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise. A WinUI rule is never flagged in a WPF or WinForms project, and the reverse.

## Views and binding

- `x:Bind` over `{Binding}`; `x:Bind` states its `Mode` where the value changes, and every `DataTemplate` has `x:DataType`. *major*
- Code-behind holds view concerns only (focus, animation, a handler that forwards to a command); no business logic, no I/O, no `HttpClient`. *major*
- Every data region renders loading, loaded, empty and failed from one state, plus stale and offline where cached; the failure is scoped to the response-dependent subtree, so search, filters and toolbar keep rendering. *major*
- Every surfaced failure also opens the one persistent `InfoBar` (`IsClosable`, no auto-dismiss), closed only by the user and deduped; never a `ContentDialog` for a background failure. *major*
- Never render `Exception.Message`, a raw server string or a response body. *major*
- Lists over about 20 items are virtualized (`ListView`, `GridView`, `ItemsRepeater` with a layout) with a bounded height, never inside a `ScrollViewer` that unbounds them; keys are stable domain ids. *major*
- Experimental-channel controls and APIs (`TableView`, `Chart`, `InkCanvas`, `Window.Width/Height`) never ship. *blocker*
- Controls come from the semantic choice (`Button`, `HyperlinkButton`, `ToggleSwitch`, `NumberBox`, `CalendarDatePicker`); a clickable `Grid` or `Border` is a real control. *major*
- An icon-only button has a `ToolTip` and an accessible name. *major*

## Windows, navigation and commands

- Windows are `AppWindow`s with a stated minimum size; size, position and presenter state are saved on close and restored on launch, validated against the live displays. *major*
- The title bar is the `TitleBar` control; `ExtendsContentIntoTitleBar` is set before a tall height. *minor*
- Navigation is `NavigationView` items and a `Frame` wired for back; in-app navigation is a real item or `HyperlinkButton`, never a click handler on a panel. *major*
- Every command is reachable from the keyboard: access keys and `KeyboardAccelerator`s with standard shortcuts kept (`Ctrl+S`, `Ctrl+Z`, `F1`, `Alt+F4`); menu and toolbar items share one `XamlUICommand`. *major*
- An unavailable command is disabled (`CanExecute`), never hidden. *major*
- A page parameter that arrives from activation is validated before `Frame.Navigate`. *major*
- `ContentDialog` is for a decision, with `XamlRoot` set, one open at a time; a long form is a page. *major*

## Forms

- Validation lives on the view model (`ObservableValidator`), shown at the field as text, announced, and never by colour alone; submit validates every field and focuses the first invalid one. *major*
- Errors appear on lost focus, then live; never on an untouched field at load. *minor*
- A failed submit keeps the user's input and shows the `InfoBar`; a double submit is prevented. *major*
- A secret field is a `PasswordBox`, never logged, persisted or left in the view model. *blocker*
- `NumberBox` empty (`NaN`) is handled; `InputScope` is set; spell check is off for ids, codes and emails. *major*
- A dirty form asks before it is left. *major*
