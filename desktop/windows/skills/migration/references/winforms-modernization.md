# WinForms modernization

WinForms is a supported lane. Modernizing it means **.NET 10, then the WinForms features that arrived with it**, and the app stays WinForms: never `UseWinUI` or the Windows App SDK as a side effect, and a WinUI view inside a form is XAML hosting, a recorded decision ([`interop`](../../interop/SKILL.md)).

## Order (one per change)

1. **.NET Framework → .NET 10**, if needed ([`framework-to-dotnet10`](framework-to-dotnet10.md)); or .NET 8/9 → 10 ([`dotnet-8-9-to-10`](dotnet-8-9-to-10.md)).
2. **Project hygiene**: nullable, warnings as errors, `Directory.Build.props`, central package versions.
3. **Host and DI**, with forms built from the container; logic moves out of handlers into view models or presenters, form by form ([`winforms`](../../winforms/SKILL.md)).
4. **Async everywhere**: `ShowAsync` / `ShowDialogAsync` (stable since .NET 10) instead of nested modal loops and `Application.DoEvents`.
5. **Dark mode** with `Application.SetColorMode` before the first form; literal colours become system colours.
6. **High DPI**: `PerMonitorV2`; absolute positions become anchors, docking or layout panels.
7. **Optionally on .NET 11**, `VisualStylesMode.Net11` as an explicit opt-in, after the owner asks for the modern look; Microsoft's notes said the rendering was not final at RC1, so state what was verified on the SDK in use.

## Verify

Build with warnings as errors, tests green, the app launches at 100% and 150% scale, dark and light, and the primary flow runs; `AutomationId`s (control `Name`s) are unchanged unless a rename was the point.
