---
paths:
  - "**/*.xaml"
  - "**/*{Page,Window,Control,Dialog,View,Template}.xaml.cs"
  - "**/{Views,Pages,Controls,Dialogs}/**/*.cs"
---

<!-- desktop-windows rules v1 (2026-11-15): WinUI and XAML. Installed by /desktop-windows:rules; edit the paths above to where this project keeps its views. Apply to WinUI projects only. -->

# WinUI and XAML standards

Severity tags as in the core C# rules. The codebase wins where it consistently does otherwise. A WinUI rule is never flagged in a WPF or WinForms project, and the reverse. Recipes: `ui-components`, `windows-and-navigation`, `forms`.

## Views and binding

- `x:Bind` over `{Binding}`; every `DataTemplate` has `x:DataType`. *major*
- Code-behind holds view concerns only: no business logic, no I/O. *major*
- Every data region renders loading, loaded, empty and failed from one state (plus stale and offline where cached), scoped to the response-dependent subtree. *major*
- Every surfaced failure also opens the one persistent `InfoBar` (`IsClosable`, no auto-dismiss), closed only by the user; never a `ContentDialog` for a background failure; never render `Exception.Message`. *major*
- Long lists are virtualized with a bounded height, never inside a `ScrollViewer` that unbounds them; keys are stable domain ids. *major*
- Experimental-channel controls and APIs never ship. *blocker*
- A clickable `Grid` or `Border` is a real control (`Button`, `HyperlinkButton`). *major*

## Windows, navigation and commands

- Windows are `AppWindow`s with a stated minimum size; size, position and presenter state are saved on close and restored on launch, validated against the live displays. *major*
- In-app navigation is a `NavigationView` item or `HyperlinkButton`, never a click handler on a panel; a page parameter from activation is validated before `Frame.Navigate`. *major*
- Every command is reachable from the keyboard (access keys, `KeyboardAccelerator`s, standard shortcuts kept); an unavailable command is disabled, never hidden. *major*
- `ContentDialog` is for a decision, with `XamlRoot` set. *major*

## Forms

- Validation lives on the view model (`ObservableValidator`), shown at the field as text and never by colour alone; submit validates every field and focuses the first invalid one. *major*
- A failed submit keeps the user's input; a dirty form asks before it is left. *major*
- A secret field is a `PasswordBox`, never logged, persisted or left in the view model. *blocker*
