---
name: error-handling
description: Use when a Windows screen can fail: loading/loaded/failed/stale/offline states, InfoBar, unhandled-exception handlers, stowed exceptions. Triggers "show the error". Not for server retry policy (networking).
---

# Windows — Error Resilience

How a Windows app fails well: **every data region has loading, loaded, failed, stale and offline states; a failure is scoped to the subtree that depends on the response; every surfaced failure also raises one persistent `InfoBar` that only the user closes; and a crash leaves enough evidence to fix it.** It is the fe-react rule set (`frontend/react/skills/error-handling`) and the mobile deltas, with the desktop deltas below. Audit rows: section O of `desktop-windows:standards-audit`. Design facts: `design/ui-ux-pro-max --stack winui`.

## Version lane

| Concern | WinUI on WinAppSDK 2.6 (primary) | Note |
|---|---|---|
| Banner | `InfoBar` (`IsClosable="True"`, `Severity="Error"`), at the top of the window content | Never `MessageBox`, never `ContentDialog` for a foreground failure, never a toast |
| Unhandled | `Application.UnhandledException`, `AppDomain.CurrentDomain.UnhandledException`, `TaskScheduler.UnobservedTaskException` | WinUI can fail-fast before a handler runs: the stowed exception is the evidence |
| Crash triage | `winapp run --debug-output [--symbols]` decodes stowed exceptions (**winapp 0.8.0, public preview**) | Fallback: a WER dump opened in WinDbg (`!pde.dse`, **not verified here**); Visual Studio's exception settings |
| Crash reporting | WER (Partner Center health reports for Store MSIX; local dumps for LOB); Sentry .NET 7.0.0 | `desktop-shared:observability` |
| `[WPF]` | `Application.DispatcherUnhandledException` | Same state model, `InfoBar` is a hand-built banner (or the toolkit's) |
| `[WinForms]` | `Application.ThreadException` + `SetUnhandledExceptionMode` (`desktop-windows:winforms`) | A banner `Panel` at the top of the form |
| `[C++]` | `hresult_error` caught once at the boundary; `fire_and_forget` fail-fasts (`desktop-windows:cpp-winrt`) | |

Detect first: an existing error type or result type, an `InfoBar` host, handler registration in `App`, and the telemetry exporter. Extend them.

## When to use

- A screen loads, saves or deletes; "what shows when the call fails?"; a crash report with no stack
- Reviewing a window against the §8 error rows

## When NOT to use

- Retry, backoff, `Retry-After`, ProblemDetails mapping → `desktop-windows:networking`
- Field-level validation → `desktop-windows:forms`
- Speed of loading → `desktop-windows:performance`

## The failure surfaces

| Surface | Where it shows | Dismissal |
|---|---|---|
| Region failed | In the pane that depends on the response, with Retry | The retry; the region recovers when data arrives |
| Window banner | One `InfoBar` at the top of the window content | **Only the user**, with the close button |
| Field | Beside the input (`desktop-windows:forms`) | On edit |
| Modal | `ContentDialog` only for a user decision (discard changes?) | The choice |
| System notification | Only for work that finished while the app was in the background, never for a foreground failure | The system |
| Fatal | The unhandled-exception path: log, save, restart prompt | — |

**A background failure never raises a modal.** A failure the user cannot act on is a banner and a log line, not a dialog.

## Data regions — five states

A region owns its state, never a nullable list plus a flag:

```csharp
public abstract record Load<T>
{
    public sealed record Loading : Load<T>;
    public sealed record Loaded(T Value) : Load<T>;
    public sealed record Failed(FailureKind Kind, string Message) : Load<T>;
    public sealed record Stale(T Value, FailureKind Kind) : Load<T>;
}

public enum FailureKind { Offline, Timeout, Server, Unauthorized, NotFound, Drifted, Storage }
```

The view model holds one `Load<T>` per region and the page switches on it (`VisualStateManager` with one group, or `x:Load`):

| State | Shows | Never |
|---|---|---|
| Loading | A `ProgressRing` or skeleton of the final layout, and the previous content under it on a refresh | A blank pane |
| Loaded | The data; the empty case is its own message with an action | A spinner that stays |
| Failed | In the **pane only**: the icon, a plain sentence by `FailureKind`, a **Retry** button | `ex.Message`, a stack trace, a blank pane |
| Stale | The last good data, a "Last updated 10:42" line, a refresh action | Throwing the data away because a refresh failed |
| Offline | `FailureKind.Offline`: "You are offline", the stale data if any, retry on reconnect | The same text as a server error |

- **A drifted or unparseable response is Failed (`Drifted`), never an empty list.** Deserialize through the typed models (`desktop-windows:networking`); a missing required field fails.
- **Every request has a timeout budget** (a linked `CancellationTokenSource`), and a timeout is `FailureKind.Timeout`.
- **A refetch that fails after a success is Stale, not Failed.**
- **Distinguish offline from server error**: `NetworkInformation.GetInternetConnectionProfile()` and the exception type (`HttpRequestException` with no status code) decide; the status code decides the rest. A 401 goes to the sign-in flow, a 404 on a deleted item is "this item is gone" with the list refreshed.
- **An empty result is a state with copy and an action** (a first-run empty, a no-results-for-filter empty with "Clear filters", a permission-empty), never a blank pane.

### Scope the failure to the subtree

A window with a sidebar, toolbar, search box and an inspector keeps all of them when the content pane fails. Only the response-dependent subtree swaps to its Failed body; the search box, the filters and the navigation keep rendering and keep working.

```xaml
<Grid>
    <Grid.RowDefinitions>
        <RowDefinition Height="Auto" />
        <RowDefinition Height="Auto" />
        <RowDefinition Height="*" />
    </Grid.RowDefinitions>
    <InfoBar Grid.Row="0" x:Name="Banner" AutomationProperties.AutomationId="Orders.Banner"
             Severity="Error" IsClosable="True"
             IsOpen="{x:Bind ViewModel.BannerOpen, Mode=TwoWay}"
             Title="{x:Bind ViewModel.BannerTitle, Mode=OneWay}"
             Message="{x:Bind ViewModel.BannerMessage, Mode=OneWay}" />
    <CommandBar Grid.Row="1" AutomationProperties.AutomationId="Orders.Toolbar" />
    <Grid Grid.Row="2" AutomationProperties.AutomationId="Orders.Content">
        <ListView x:Name="Rows" AutomationProperties.AutomationId="Orders.List"
                  Visibility="{x:Bind ViewModel.ShowRows, Mode=OneWay}" />
        <StackPanel x:Name="FailedBody" AutomationProperties.AutomationId="Orders.FailedRegion"
                    Visibility="{x:Bind ViewModel.ShowFailed, Mode=OneWay}">
            <TextBlock x:Uid="Orders.FailedText" />
            <Button x:Uid="Orders.RetryButton" AutomationProperties.AutomationId="Orders.RetryButton"
                    Command="{x:Bind ViewModel.RetryCommand}" />
        </StackPanel>
    </Grid>
</Grid>
```

## The window banner — persistent, user-dismissed

- **One `InfoBar` per window**, first row of the content, above the toolbar. It shows the most recent failure the user has not dismissed; a second failure replaces or appends to the message, it does not stack dialogs.
- **Every failure that sets a region's Failed state also opens the banner.** A drifted response, a failed save, a failed refresh behind Stale: all raise it.
- `IsClosable="True"` and no `DispatcherTimer`, no `Task.Delay` closing it: **only the user's close button dismisses it.**
- The text is a sentence from `FailureKind` plus an action (`Retry`, `Sign in`), never the raw exception, a status code alone or a stack.
- It is a normal element in the tab order and has a `LiveSetting`/announces on open (`InfoBar` does by default).
- `Severity` follows the effect: `Error` for a failed action, `Warning` for stale or offline, `Informational` for a recovered state.

## Desktop deltas (plan 012 §6.4)

| Rule | Windows form |
|---|---|
| Revalidate on return | Window activation (`Window.Activated` with `WindowActivationState != Deactivated`), **wake from sleep** (`Microsoft.Windows.System.Power.PowerManager.SystemSuspendStatusChanged`, verify the member on the SDK in use), and a network change (`NetworkInformation.NetworkStatusChanged`) each call the same `RefreshAsync` once, de-duplicated |
| Multi-window | One model object (a singleton service holding the data, raising change events); every window's view model observes it; a write in one window never leaves another showing old data. The failure state is per window, the data is shared |
| Version skew | An update (Velopack, Store) never restarts over unsaved work; a server-forced minimum version is a prompt the user can postpone until the work is saved |
| Mutation failures | Quitting mid-write is routine: autosave to a temp file then an atomic replace, and on relaunch reconcile the indeterminate outcome (ask the server, show "We could not confirm your last change") rather than drop it |
| Storage failures | A full disk, a revoked file permission or a locked database is a recoverable, explained `FailureKind.Storage` state with the path's *kind* (never the user's path in telemetry) and a way out |
| Third-party dependency | See below: each degrades to a scoped failed region |

Closing with unsaved work: handle `AppWindow.Closing` and set `args.Cancel = true`, then ask with a `ContentDialog` offering Save / Don't save / Cancel; the dialog is the one modal here because it needs a decision. Details of the write path are in [`references/writes-and-dependencies.md`](references/writes-and-dependencies.md).

## Dependencies that die

WebView2 runtime missing or crashed, an unregistered COM server, a dead helper process and an unavailable Windows AI API each degrade to a scoped Failed region with Retry, never an app crash. Detection per dependency: [`references/writes-and-dependencies.md`](references/writes-and-dependencies.md).

## Unhandled exceptions

Register in `App`, in this order, and keep the handlers short:

```csharp
public App()
{
    UnhandledException += OnUnhandled;
    AppDomain.CurrentDomain.UnhandledException += OnDomainUnhandled;
    TaskScheduler.UnobservedTaskException += OnUnobserved;
}
```

| Handler | Does | Does not |
|---|---|---|
| `Application.UnhandledException` | Logs with the exception, saves recoverable drafts, sets `e.Handled = true` only when the app state is known good | Swallow it to keep running in an unknown state |
| `AppDomain…UnhandledException` | Logs, flushes telemetry (the process is ending) | Show UI |
| `TaskScheduler.UnobservedTaskException` | Logs and calls `SetObserved()`; it is a missed `await`, treat as a defect | Hide the defect forever: each one gets a ticket |

- A failure the user can act on is handled **at the operation** (`try` around the awaited call in the view model's command), mapped to a `FailureKind`, and never reaches these handlers.
- **No empty `catch`, no `catch (Exception)` that only logs and continues** (CLAUDE.md § Test code rules for tests; § Code quality for code). A catch either maps to a state or rethrows.
- An `async void` event handler wraps its whole body in `try`/`catch` and routes to the state; an exception out of it fails fast.
- A fatal exception: write the log and the draft, then let the process end. Never loop a restart.

## Stowed-exception triage

WinUI and XAML failures fail fast with a **stowed exception** (`0xC000027B`) carrying the real HRESULT and stack.

1. Reproduce with `winapp run --debug-output --symbols` (winapp 0.8.0, preview): it decodes the stowed exceptions into the console. Needs Developer Mode.
2. Without `winapp`: attach Visual Studio and break on *Common Language Runtime* and *Win32* exceptions, or open the WER dump in WinDbg (`!pde.dse`, not verified here).
3. Read the HRESULT first: `0x8001010E` wrong thread (`DispatcherQueue.TryEnqueue`), `0x80070057` bad argument at a XAML property, `0x80004005` unspecified (read the inner), `0xC000027B` is only the wrapper.
4. A XAML parse failure names the markup line and column in the stowed message; `x:Bind` failures name the property path.
5. Keep the PDBs of each release; a dump without them is a hash.

## Telemetry

A log at each decision point (`FailureKind`, operation name, status code, never the body or user data), a span around each load and save with the failure recorded, and a metric `app.failure` counter tagged by `kind` and `region`. The unhandled handlers flush the exporter before the process ends.

## Rules

1. Five states per data region, a `Load<T>` or equivalent; no null-plus-flag.
2. The failure is scoped to the response-dependent subtree; navigation, search, filters and toolbar keep working.
3. Every surfaced failure also opens the one window `InfoBar`; only the user's close dismisses it.
4. A drifted response is Failed, never empty; a failed refresh behind data is Stale; offline is told apart from a server error.
5. A timeout on every request; a cancel on page unload.
6. Never show `Exception.Message`; the text comes from `FailureKind`.
7. Wake, reactivation and a network change revalidate; windows share one model.
8. Quit and update never discard unsaved work; an indeterminate write is reconciled.
9. No empty `catch`; unhandled handlers log, save and end.

## Generation steps

1. Detect the lane and existing error types and banner host; define `FailureKind` and the region state.
2. Write the region body (Failed with Retry, Stale line, Offline copy, empty states) and the one `InfoBar`; wire every region failure to it.
3. Register the three handlers; add wake, activation, network revalidation and `Closing`.
4. Run `winapp run --debug-output` once with a forced failure to prove the evidence arrives.

## Validation

- `rg -n "catch\s*(\(Exception[^)]*\))?\s*\{\s*\}" -g '*.cs'` — none; `rg -n "\.Message\b" -g '*.xaml' -g '*.cs'` — no raw message shown in UI.
- `rg -n "MessageBox|MessageDialog" -g '*.cs'` — none for a failure.
- `rg -n "IsClosable=\"False\"|DispatcherTimer" -g '*.xaml' -g '*.cs'` — no auto-closing banner.
- A forced server failure leaves the toolbar and search working and the banner open until closed.

## Common gotchas

- **The whole page swaps to an error view** — the sidebar and search vanish.
- **The banner closes itself after five seconds** — a timer on an `InfoBar`.
- **A failed refresh clears the list** — it should be Stale.
- **`e.Handled = true` on everything** — the app limps on corrupt state.
- **A modal `ContentDialog` from a background timer** — it steals focus and blocks the window.
- **A 401 shown as a generic error** — it is a sign-in prompt.
- **Closing with a pending write** — no `Closing` handler.
- **A stowed exception read as the cause** — the cause is its inner HRESULT.

## Handoffs

- Retry, ProblemDetails, token refresh → `desktop-windows:networking`; field errors → `desktop-windows:forms`
- `InfoBar` markup and the three-state template → `desktop-windows:ui-components`
- Autosave, atomic writes, revoked permissions → `desktop-windows:offline-and-storage`
- Crash reporting and spans → `desktop-shared:observability`; accessibility of the banner → `desktop-windows:accessibility`
- Mac counterpart → `desktop-macos:error-handling`
