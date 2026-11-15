---
paths:
  - "**/*.xaml"
  - "**/*{Window,Control,Dialog,View,Page}.xaml.cs"
  - "**/{Views,Controls,Dialogs}/**/*.cs"
---

<!-- desktop-windows rules v1 (2026-11-15): WPF. Installed by /desktop-windows:rules; edit the paths above to where this project keeps its views. Apply to WPF projects (`UseWPF`) only. -->

# WPF standards

Severity tags as in the core C# rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise. A WPF app stays WPF: never add WinUI, the Windows App SDK or XAML Islands as a side effect (recorded decision first). *major*

- MVVM on CommunityToolkit.Mvvm; code-behind is view concerns only. *major*
- Binding failures are defects: `PresentationTraceSources` or the output window is read, and the binding is fixed, not silenced. *minor*
- Long lists virtualize (`VirtualizingStackPanel`, `VirtualizationMode="Recycling"`, no `CanContentScroll="False"`, no `ScrollViewer` around the list). *major*
- Colours come from theme or system resources, never literals; light, dark and High Contrast each have an entry. *major*
- The Fluent theme is an explicit choice (`ThemeMode` on `Application` or `Window`, or the merged Fluent dictionary), with its gaps noted; the status of `WPF0001` is rechecked on the SDK in use. *minor*
- Background results reach the UI through the `Dispatcher`, batched; a collection changed from another thread is synchronized (`BindingOperations.EnableCollectionSynchronization`) or marshalled. *major*
- A subscription to a static or long-lived event (`SystemEvents`, a service event) is removed on window close. *major*
- Every region has loading, loaded and failed states with one persistent inline banner; no `MessageBox` for a background failure. *major*
- Every interactive element carries `AutomationProperties.AutomationId` and `AutomationProperties.Name`; custom controls expose an `AutomationPeer`. *major*
- Dialogs are awaited from the view model through a service; no `ShowDialog()` inside a command that blocks a pump. *major*
- `x:Static` and resource keys over literals; strings come from `.resx`. *minor*
