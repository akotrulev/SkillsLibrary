---
name: winforms
description: Use when working in a WinForms app on .NET 10/11 (dark mode, ShowAsync, high DPI, binding, MVVM-ish structure, VisualStylesMode). Triggers "WinForms". Not for moving to WinUI (migration).
disable-model-invocation: true
---

# Windows — WinForms Lane

How a WinForms codebase is built and modernized **as WinForms**: **dark mode through `SetColorMode`, async dialogs, per-monitor DPI, data binding to view models, and the .NET 11 renderer as an explicit opt-in.** The lane stays itself. Moving to WinUI is a `desktop-windows:migration` run, never a side effect (`A6`). Audit rows: section D, tagged `[WinForms]`.

## Version lane

| Concern | Primary | Note |
|---|---|---|
| Runtime | **.NET 10 LTS** (`net10.0-windows`); .NET 11 STS supported | .NET 8/9 out of support since 2026-11-10; .NET Framework is a `migration` finding |
| Dark mode | `Application.SetColorMode(SystemColorMode.System \| Dark \| Classic)` — **stable since .NET 10** (the `WFO5001` experimental diagnostic is gone) | Call before the first form is created |
| Async dialogs | `Form.ShowAsync`, `Form.ShowDialogAsync`, `TaskDialog.ShowDialogAsync` — **stable since .NET 10** (`WFO5002` gone) | |
| Screen capture | `Form.ScreenCaptureMode` (.NET 10) | Use it for forms showing secrets |
| Clipboard | Shared with WPF; `GetData` obsolete (`WFDEV005`) → `TryGetData<T>` | `BinaryFormatter` is gone: JSON-friendly clipboard APIs |
| .NET 11 renderer | `Application.SetDefaultVisualStylesMode(VisualStylesMode.Net11)`, `Appearance.ToggleSwitch`, `SystemVisualSettingsChanged`, `FormRevealMode.Deferred`, `SuspendPainting()`, `KioskModeManager` | **Opt-in; RC1 notes warned the rendering "isn't final".** Never turned on as a side effect, and not by default in a .NET 10 project (the API is .NET 11) |
| MVVM | CommunityToolkit.Mvvm 8.4.2 | Binding source objects, no XAML |
| Designer | Visual Studio 2026 WinForms designer; out-of-process designer for .NET | Designer-owned `*.Designer.cs` is generated code (`V8`) |

## Stay in the lane

- **Detect first:** `UseWindowsForms`, `Program.cs` with `ApplicationConfiguration.Initialize()`, `*.Designer.cs`. Report lane and TFM before changing anything.
- **Never add `UseWinUI`, `Microsoft.WindowsAppSDK`, or WinUI controls** to a WinForms app to get a modern look (`A6`). A WinUI view inside WinForms is XAML hosting: a deliberate migration step (`desktop-windows:interop`).
- **Modernize in place:** .NET 10, nullable on, `Directory.Build.props`, host + DI, async everywhere, dark mode, per-monitor DPI, TaskDialog, then optionally the .NET 11 renderer. WinRT APIs come through the OS-suffixed TFM.
- **Third-party suites** (DevExpress, Telerik, Syncfusion) own their skins; their skin manager is the styling authority.

## Startup — the one place

```csharp
internal static class Program
{
    [STAThread]
    private static async Task Main()
    {
        ApplicationConfiguration.Initialize();
        Application.SetColorMode(SystemColorMode.System);

        using var host = AppHost.Build();
        await host.StartAsync();
        Application.Run(host.Services.GetRequiredService<MainForm>());
        await host.StopAsync();
    }
}
```

- `ApplicationConfiguration.Initialize()` reads the project's `ApplicationHighDpiMode`, `ApplicationDefaultFont` and `ApplicationVisualStyles` properties — set them in the `.csproj`, not in code.
- **Host and DI** as in every desktop app; forms and their view models are resolved from the container, constructor-injected (`C3`). The designer needs a parameterless constructor: add a `protected` one used only by the designer, or move logic out of the form so the designer constructor is trivial.
- **Unhandled exceptions:** `Application.SetUnhandledExceptionMode(ThreadExceptionMode.CatchException)` plus `Application.ThreadException` and `AppDomain.UnhandledException` → log, show the failed state (`desktop-windows:error-handling`).

## Architecture — MVVM-ish with binding

WinForms has data binding but no commands or templates. Keep the form passive:

- **View model:** `ObservableObject` + `[ObservableProperty]` / `[RelayCommand]`; the form binds with `BindingSource`: `nameTextBox.DataBindings.Add(nameof(TextBox.Text), viewModel, nameof(viewModel.Name), false, DataSourceUpdateMode.OnPropertyChanged)`.
- **Commands:** a `ToolStripButton` / `Button` click calls `viewModel.SaveCommand.Execute(null)` (or `ExecuteAsync`); `CanExecuteChanged` toggles `Enabled`. One handler per control, no logic inside (`D23`).
- **Binding formatting:** `Binding.Format` / `Parse` for conversions; `ErrorProvider` bound to `INotifyDataErrorInfo` (`ObservableValidator`) shows the field error as an icon and text; also set `AccessibleDescription` so Narrator reads it (`G5`).
- **Collections:** `BindingList<T>` or a `BindingSource` over an `ObservableCollection<T>`; `DataGridView` in virtual mode for big sets (`D14`).
- **Three-state regions:** the loading `ProgressBar`/overlay, the loaded grid, a failed panel with Retry. One **persistent banner** at the top of the form content (a docked `Panel` with text and a close button) for a surfaced failure; never a `MessageBox` for a background failure.
- **Dialogs:** `TaskDialog.ShowDialogAsync(owner, page)` for decisions, with a named primary button and a destructive action never the default; `MessageBox` only for the trivial.

## Async and the UI thread

- **Handlers are `async void` with a try/catch body, nothing else is** (`B7`). Use `await`; never `.Result`, `.Wait()` or `Application.DoEvents()` loops (`B8`).
- **Show forms without blocking:** `await form.ShowDialogAsync(owner)` and `await form.ShowAsync()` return when the form closes, so a dialog's lifetime can be awaited in a workflow without nesting a message loop by hand.
- **Marshalling:** after an `await` the `WindowsFormsSynchronizationContext` resumes on the UI thread. From a plain thread use `control.BeginInvoke(...)`, never `Invoke` from a loop (blocks); check `InvokeRequired` only at a boundary that can be hit from both.
- **Background work is cancelled when the form closes:** a `CancellationTokenSource` cancelled in `FormClosing`/`OnFormClosed` and disposed (`F5`).
- **`BackgroundWorker` and `Timer` (WinForms) are legacy for new code:** use `Task.Run` with progress through `IProgress<T>`, and `PeriodicTimer` with a token.

## High DPI

- **Per-monitor v2:** `<ApplicationHighDpiMode>PerMonitorV2</ApplicationHighDpiMode>` in the `.csproj`; the manifest is generated.
- **Layout:** `AutoScaleMode.Dpi`, `TableLayoutPanel` / `FlowLayoutPanel` with docking and anchoring, never absolute pixel positions for new forms. Test at 100 %, 150 % and 200 %, and drag the window across monitors with different scales (`D19`).
- **Images** ship at several sizes or as vectors; `ImageList` entries are scaled once, not per paint.
- **Fonts:** `ApplicationDefaultFont` (the system font); never a hard-coded `Font("Tahoma", 8)`.
- Handle `DpiChanged` for custom-painted controls and cached bitmaps.

## Dark mode and theming

```csharp
Application.SetColorMode(SystemColorMode.System);
```

- **`SystemColorMode.System`** follows the user's app-mode setting; `Dark` forces it; `Classic` keeps the old look. It applies to forms, common controls and the title bar; third-party and owner-drawn controls may not follow (verify per control).
- **Custom colours come from `SystemColors`** and `Control.DefaultBackColor`, never literals; owner-drawn and third-party controls must read the current colours at paint time (`Application.ColorMode`, `Control.BackColor`).
- **React to a change:** `SystemEvents.UserPreferenceChanged` (unsubscribe on close); on .NET 11, `Application.SystemVisualSettingsChanged`. Redraw, do not restart.
- **High Contrast:** `SystemInformation.HighContrast` — use system colours and do not override them; test every screen (section M).
- **Gaps:** some controls and third-party skins do not honour dark mode fully; list them, never paper over with literal colours.

## The .NET 11 renderer — explicit opt-in

```csharp
Application.SetDefaultVisualStylesMode(VisualStylesMode.Net11);
```

- **Only when the project targets .NET 11 and the owner asked for the modern look.** Microsoft's RC1 notes said the rendering "isn't final"; verify on the SDK in use and say what was checked.
- **Test every custom-painted and owner-drawn control** after enabling it; `Appearance.ToggleSwitch` replaces a `CheckBox` styled as a switch only where the control table calls for an on/off applied now (`D11`).
- Reversible: it is one call; keep it out of shared libraries, set once in `Program`.

## Windows, keyboard and input

- **Access keys** with `&` in `Text`; `ShortcutKeys` on `ToolStripMenuItem`; standard shortcuts keep their meaning (`F9`); **disable, never hide**, an unavailable item (`F10`); menu, toolbar and context menu share one `Action`-like command definition (`F11`).
- **Tab order:** `TabIndex` set for the whole form or not at all, `TabStop=false` on decoration; set `AcceptButton` / `CancelButton` for `Enter` / `Esc` on single-purpose dialogs.
- **State:** save `Bounds` / `WindowState` (use `RestoreBounds` when maximized) on close, validate against `Screen.AllScreens` on restore; ask about unsaved work in `FormClosing` with `e.Cancel` (`F2`, `F3`).
- **Secrets:** `TextBox.UseSystemPasswordChar` for passwords, `Form.ScreenCaptureMode` on forms that show secrets, never log field values.
- **Accessibility:** `AccessibleName`, `AccessibleDescription`, `AccessibleRole`; `Label.UseMnemonic` with `LabelFor`; **`AccessibleName` is not the test id** — set `Name` to the PascalCase dot-separated id the tests read (`desktop-windows:test-ids`).

## Performance

- **Flicker and slow repaint:** `DoubleBuffered` through `SuspendLayout` / `ResumeLayout` around bulk changes; on .NET 11 `SuspendPainting()` scopes.
- **`DataGridView` over thousands of rows:** virtual mode, no autosize on every cell, no per-cell formatting handlers that hit the database.
- **Handlers and timers** on long-lived objects keep forms alive: unsubscribe on close; dispose forms you `Show()`.

## Telemetry

The shared base (`desktop-shared:observability`): `ILogger` from the host, a span per command doing I/O, a metric per business event. WinForms adds the `ThreadException` log and a `form.opened` counter by form name.

## Common gotchas

- **`SetColorMode` after the first form exists** — no effect on it; call it first.
- **Hard-coded `BackColor`s** — break dark mode and High Contrast.
- **`Invoke` from a worker loop** — the UI thread stalls; `BeginInvoke`, batched.
- **`ShowDialog()` in an async workflow** — nested message loop; `ShowDialogAsync`.
- **`Application.DoEvents()`** — re-entrancy bugs; `await` instead.
- **Absolute-position layout** — breaks at 150 % and on monitor moves.
- **Designer-only parameterless constructor with real logic** — runs in the designer.
- **`VisualStylesMode.Net11` enabled "for the look"** — it is final-in-progress; opt-in with a reason.
- **WinUI added "just for one view"** — a lane change; run `migration`.
