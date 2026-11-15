# UWP → WinUI

A UWP app moves to WinUI on Windows App SDK 2.x with C# on .NET 10, packaged. Microsoft's "migrate from UWP" guide is the source; this reference carries the shape.

## What changes

| UWP | WinUI (Windows App SDK) |
|---|---|
| `CoreWindow`, `CoreApplicationView`, `ApplicationView` | `Window` and `AppWindow`; no `CoreWindow` |
| `Window.Current`, `Dispatcher` | the window instance you hold, `DispatcherQueue` |
| Pickers and dialogs find the window implicitly | `Microsoft.Windows.Storage.Pickers` built with `AppWindow.Id`; `ContentDialog.XamlRoot` set |
| `Windows.UI.Xaml.*` | `Microsoft.UI.Xaml.*` |
| UWP app model, lifecycle suspend/resume | desktop lifecycle: activation through `AppInstance`, no suspension |
| Sandbox always | full trust (`runFullTrust`) unless you restrict capabilities; keep capabilities minimal with a reason |

## Steps

1. **Baseline and inventory** (the gate): count `Window.Current`, `CoreWindow`, `Dispatcher`, background tasks, `Windows.UI.Xaml` uses and third-party UWP controls.
2. **New WinUI project** beside the UWP one (`winapp new --template winui-mvvm`, or the Visual Studio template); share logic through a library both reference, then move page by page. Delete the UWP project last.
3. **Replace the app model**: activation through `AppInstance`, startup tasks, toasts through `AppNotificationManager` ([`activation-and-notifications`](../../activation-and-notifications/SKILL.md)).
4. **Replace window-bound APIs** (pickers, dialogs, share, `CoreWindow` input) with the window-id versions ([`platform-integration`](../../platform-integration/SKILL.md)).
5. **Apply the house rules to what you move**: `x:Bind`, three-state regions, test ids, accessibility. Moving is not redesigning: those are follow-ups unless the owner asked.

## Verify

Each moved page renders and runs; activation, notifications and the pickers each run once; a clean packaged install starts; section A and D of the audit pass for the moved pages.
