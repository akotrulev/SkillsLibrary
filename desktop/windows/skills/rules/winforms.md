---
paths:
  - "**/*Form.cs"
  - "**/*Form.Designer.cs"
  - "**/*{UserControl,Dialog}.cs"
  - "**/{Forms,Controls,Dialogs}/**/*.cs"
---

<!-- desktop-windows rules v1 (2026-11-15): WinForms. Installed by /desktop-windows:rules; edit the paths above to where this project keeps its forms. Apply to WinForms projects (`UseWindowsForms`) only. -->

# WinForms standards

Severity tags as in the core C# rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise. A WinForms app stays WinForms: never add WinUI as a side effect. *major*

- The form is passive: it binds to a view model or presenter, and an event handler forwards and returns. Logic in a handler is a finding; `*.Designer.cs` is generated and never edited by hand beyond what the designer would write. *major*
- Dark mode is set before the first form (`Application.SetColorMode(SystemColorMode.System)` on .NET 9+); colours are system colours, never literals. *major*
- High DPI is on (`ApplicationHighDpiMode`, `PerMonitorV2`); layout is anchored, docked or in `TableLayoutPanel` / `FlowLayoutPanel`, never absolute pixel positions. *major*
- Dialogs are awaited (`ShowAsync`, `ShowDialogAsync` on .NET 10), never nested modal loops with `Application.DoEvents`. *major*
- `VisualStylesMode.Net11` is an explicit opt-in on a .NET 11 project, never a default. *minor*
- A large `DataGridView` runs in virtual mode; work off the UI thread returns through `Control.BeginInvoke` or `await`, batched. *major*
- Long-lived subscriptions (a service event, a `Timer`, `SystemEvents`) are removed in `FormClosed` / `Dispose`. *major*
- Controls are named deliberately (`Name` becomes the `AutomationId`: `Screen.ElementType.Qualifier`), and interactive controls carry `AccessibleName` and `AccessibleRole` where the default is wrong. *major*
- Every data region has loading, loaded and failed states and one persistent inline banner; no `MessageBox` for a background failure. *major*
- Strings come from `.resx` and `CurrentUICulture`; no literal in the designer for user-visible text. *minor*
