# WPF → WinUI, or modernize WPF in place

**A recorded decision comes first**, with the owner. Microsoft's decision guide names both paths; the default here is **modernize in place**, because WPF on .NET 10 / 11 is supported and the move to WinUI has blockers a WPF app often has: a WCF server, ASMX, `System.Configuration`, COM, and third-party control vendors with no WinUI build. The XAML Designer for WinUI is also not yet available in Visual Studio (no date).

## Decision record (write it before any code)

| Question | Moves toward |
|---|---|
| Does the app need Fluent 2, Mica, the new `TitleBar`, WinUI-only controls, MSIX-first features? | WinUI |
| Does it depend on blockers above, on `DataGrid`-class vendor controls, on `Window` features WinUI lacks? | Modernize in place |
| Can the team keep two UI stacks for the length of a view-by-view move? | WinUI, via hosting ([`interop`](../../interop/SKILL.md)) |
| Is the app near end of life? | Modernize in place, or leave it |

## Modernize in place

.NET 10 ([`dotnet-8-9-to-10`](dotnet-8-9-to-10.md) first if needed), nullable and warnings as errors, host and DI, `ThemeMode` or the merged Fluent dictionary, per-monitor DPI, virtualized lists, `AutomationId`s, WinRT APIs through the OS-suffixed TFM and the Windows App SDK NuGet where an API needs it, and MSIX packaging. All of it is inside [`wpf`](../../wpf/SKILL.md); the lane stays WPF.

## Move to WinUI, view by view

1. Hosting first: WinUI views inside the WPF shell (XAML Islands / `DesktopWindowXamlSource`) or the reverse, as a recorded step with the Windows App SDK added deliberately (A6).
2. Move leaves first: a view with no children, then its host. Share view models through a UI-free library, so each moves once.
3. Use Microsoft's `wpf-patterns-winui3` guide (and the `winui-wpf-migration` agent skill where installed, D10) for the mapping of controls, bindings (`{Binding}` → `x:Bind`), resources and commands.
4. Remove the hosting layer when the last WPF view is gone; delete the WPF project last.

## Verify

Each moved view renders at 100% and 150% scale in light, dark and High Contrast; keyboard-only works; audit sections A, D, E, M for the moved views.
