---
name: activation-and-notifications
description: Use when handling single instancing, protocol/file activation, startup tasks, restart or app notifications. Triggers "single instance", "toast". Not for windows (windows-and-navigation).
disable-model-invocation: true
---

# Windows — Activation and Notifications

How the OS starts and re-enters the app, and how the app talks back: **`AppInstance.FindOrRegisterForKey` / `RedirectActivationToAsync` for single instancing, protocol and file activation treated as untrusted input, a startup task, `AppNotificationManager`, and WNS push.** Audit rows: section J of `desktop-windows:standards-audit`. Never a mutex.

## Version lane

| Concern | Windows App SDK 2.6 (primary) | Note |
|---|---|---|
| Instancing | `Microsoft.Windows.AppLifecycle.AppInstance` | WinUI apps are **multi-instance by default**; redirection is **not terminal** — the caller must exit itself |
| Custom `Main` | `DISABLE_XAML_GENERATED_MAIN` now *renames* the generated main (`XamlGeneratedProgram.XamlGeneratedMain()`) instead of removing it (2.3.1) | recheck on a 1.x → 2.x migration |
| Notifications | `AppNotificationManager` + `AppNotificationBuilder` | WinUI, WPF, WinForms, console; packaged or unpackaged |
| Identity-gated | file and protocol associations, startup task, background tasks, share target need **package identity** | an unpackaged app registers associations another way and records why |
| WPF / WinForms | same `AppInstance` API, from `Main` | → `desktop-windows:wpf`, `:winforms` |

## When to use

- "Only one copy of my app", "open this file in the running window", `myapp://` links
- Launch at sign-in, relaunch after update or crash
- Toasts with actions, push from a server

## When NOT to use

- Window creation, navigation, accelerators → `desktop-windows:windows-and-navigation`
- Pickers, share, drag and drop, WebView2, background tasks → `desktop-windows:platform-integration`
- Token storage, signing → `desktop/_shared/security`, `desktop/_shared/distribution`

---

## Single instancing — `AppInstance`, never a mutex

A named mutex cannot hand the second launch's arguments to the first. `AppInstance` can.

```csharp
public static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        WinRT.ComWrappersSupport.InitializeComWrappers();
        var activation = AppInstance.GetCurrent().GetActivatedEventArgs();
        var keyInstance = AppInstance.FindOrRegisterForKey("MyApp.Main");

        if (!keyInstance.IsCurrent)
        {
            RedirectAndWait(keyInstance, activation);
            return 0;
        }

        keyInstance.Activated += OnActivated;
        Application.Start(_ => _ = new App());
        return 0;
    }

    private static void RedirectAndWait(AppInstance target, AppActivationArguments activation)
    {
        var done = new ManualResetEventSlim();
        Task.Run(async () =>
        {
            await target.RedirectActivationToAsync(activation);
            done.Set();
        });
        done.Wait();
    }
}
```

- **Redirect before any UI or service starts** — the second process must exit quickly and cheaply.
- **`RedirectActivationToAsync` must be awaited** or the redirect fails; on an STA `Main` run it on another thread and wait on an event, as above. This single blocking wait in `Main`, before any window exists, is the one allowed exception to "never block"; it is not on a UI thread with a message loop.
- **`Activated` fires on a background thread.** Marshal to the window with `DispatcherQueue.TryEnqueue`, bring the window forward (`AppWindow.Show()`, restore if minimized), then route.
- **Guard circular redirection.** Redirection is not terminal; A → B → A loops forever. One key, one owner, and the redirected instance never redirects again.
- **A crashed owner:** keys are released with the process; a redirect racing the exit can still target a dying instance. Call `UnregisterKey()` on a deliberate exit.
- **Multi-instance by choice** (one window per document): key the instance by the document identity, not the app.
- Packaged apps may declare the single-instance intent in the manifest; code still owns the redirect.

## Activation arguments are untrusted input

Protocol URIs, file paths, toast arguments and command lines come from outside the app — another process, a web page, a file in an email. **Validate before routing** (CLAUDE.md § Desktop code rules).

```csharp
public static class ActivationRouter
{
    public static Route? FromProtocol(Uri uri)
    {
        if (uri.Scheme != "myapp" || uri.Host != "orders") return null;
        var id = uri.AbsolutePath.Trim('/');
        return Guid.TryParse(id, out var orderId) ? new Route.Order(orderId) : null;
    }

    public static Route? FromFile(IStorageItem item)
    {
        if (item is not StorageFile file) return null;
        return Path.GetExtension(file.Path).Equals(".myapp", StringComparison.OrdinalIgnoreCase)
            ? new Route.Document(file.Path)
            : null;
    }
}
```

- **Allowlist** scheme, host and path shape; parse ids to their type; reject everything else and **show the normal start screen**, never an error that echoes the input.
- **A protocol link never performs a destructive or paid action** by itself; it navigates, and the user confirms inside the app. No `delete`, `pay` or `logout` verbs in a deep link.
- **Files:** check extension and magic bytes, cap size, open read-only, parse defensively; never execute, never trust a path inside the file.
- **Command-line `Launch` arguments** are parsed with a real parser into a typed options record; unknown flags are ignored, not passed to a shell.
- **Toast arguments** are validated the same way (below) — a toast can be replayed from the Action Center.
- **Log the rejection** as a structured event with the activation kind, never the raw payload if it can carry tokens or personal data.
- Dispatch on `args.Kind` (`Launch`, `File`, `Protocol`, `AppNotification`, `StartupTask`, `Restart`); an unknown kind routes to the start screen.

### Protocol and file associations

Declared in `Package.appxmanifest` (`uap:Protocol`, `uap:FileTypeAssociation`) — packaged only. Register the narrowest set: the scheme and extensions the app handles, with `DisplayName` and a logo. Windows 11 lets the user choose the default handler; never assume the association is yours.

## Startup task and restart

- **Launch at sign-in** is a user choice, off by default. A packaged app declares a `windows.startupTask` extension (`desktop:StartupTask` with a `TaskId`) and drives it through `Windows.ApplicationModel.StartupTask.GetAsync(taskId)` → `RequestEnableAsync()` / `Disable()`. Read `State` (`Enabled`, `Disabled`, `DisabledByUser`, `DisabledByPolicy`) and show the real state; **`DisabledByUser` cannot be re-enabled from code** — link to **Settings → Apps → Startup** instead.
- **Verified against UWP-era docs only (2026-11-15).** The Windows App SDK 2.x page for startup tasks was not found, and a community report says a WinAppSDK app needed the `Executable` / `EntryPoint` attributes removed. Build it, test it on a packaged run, and record the result; do not state a 2.x-specific rule as fact. An unpackaged app uses a per-user `Run` registry key and records why it is unpackaged.
- **Startup launches minimized** to the tray or window state the user left, and does not steal focus; dispatch on `ExtendedActivationKind.StartupTask`.
- **Restart** after an update or a crash: `AppInstance.Restart(arguments)` relaunches with arguments the new process validates like any other. Save state first; never restart over unsaved work.
- **Crash-restart registration** (`RegisterApplicationRestart`) is Win32 interop → `desktop-windows:interop`.

## App notifications — `AppNotificationManager`

```csharp
public sealed class ToastService : IDisposable
{
    public ToastService()
    {
        AppNotificationManager.Default.NotificationInvoked += OnInvoked;
        AppNotificationManager.Default.Register();
    }

    public void ShowOrderShipped(Guid orderId, string title)
    {
        var notification = new AppNotificationBuilder()
            .AddArgument("action", "openOrder")
            .AddArgument("id", orderId.ToString())
            .AddText(title)
            .AddButton(new AppNotificationButton("View")
                .AddArgument("action", "openOrder")
                .AddArgument("id", orderId.ToString()))
            .BuildNotification();
        AppNotificationManager.Default.Show(notification);
    }

    public void Dispose() => AppNotificationManager.Default.Unregister();
}
```

- **Register once, early** (before `Activated` can arrive), unregister on exit. The `NotificationInvoked` event arrives on a background thread; marshal to the UI.
- **Arguments are untrusted:** `args.Argument` is a dictionary; read `action` against an allowlist and `id` as the typed value. Unknown actions do nothing.
- **A toast the user clicks after the app exited** starts the app with an `AppNotification` activation; handle both paths through the same router.
- **Never put secrets, tokens or personal data in toast text or arguments** — the text shows on the lock screen and in the Action Center.
- **Elevated apps cannot send or receive app notifications.** Never require admin; this is one more reason (CLAUDE.md § Least privilege).
- **Do not nag.** A notification states something the user asked for or must act on; group with tags, replace rather than stack (`Tag`, `Group`, `SetTag`), clear it when resolved (`RemoveByTagAsync`).
- **Permission:** the user can turn the app's notifications off. Check `AppNotificationManager.Default.Setting`; when it is not `Enabled`, show the state in-app with a link to **Settings → System → Notifications**. The denied path is a working screen.
- Respect **Focus** and Do Not Disturb: do not use `Urgent` or `Reminder` scenarios for ordinary content.
- **Accessible:** meaningful text, button labels that say the action, no information in an image alone.

## Push (WNS)

- Windows App SDK push: `PushNotificationManager.Default.Register()`, then `CreateChannelAsync(azureAppId)` → send the channel URI to the server over TLS; channels **expire** (renew on launch and on a schedule).
- Raw push to a background activation or a toast, handled through `PushNotificationReceived`.
- The Azure app id and secret live on the server; **the client never holds the WNS client secret**.
- A push payload is untrusted input: validate and cap it like an activation.
- Requires package identity for packaged background activation; an unpackaged app can receive while running only — record the limit.

## Telemetry

Each entry point adds a log at the decision, a span around the route and a metric per business event (`desktop/_shared/observability`): `activation.received` (kind), `activation.rejected` (reason), `notification.shown` / `notification.invoked` (action). Never the payload.

## Common gotchas

- **A mutex "single instance" that drops the second launch's file** — use `AppInstance`.
- **Redirect not awaited** — the second process exits and nothing arrives; the first never activates.
- **`Activated` handler touching a control directly** — wrong thread; marshal.
- **Toast actions run `delete`** from an unvalidated argument — allowlist the action, confirm in-app.
- **Registering the notification manager after the first activation** — the click that launched the app is lost.
- **`DisabledByUser` ignored** — `RequestEnableAsync` returns the same state; explain and link to Settings.
- **Admin-run app with silent notification failure** — it never shows; drop elevation.
- **Expired WNS channel** — pushes silently stop; renew at launch.

## Handoffs

- Windows, navigation, accelerators → `desktop-windows:windows-and-navigation`
- Pickers, share target, background tasks, WebView2 → `desktop-windows:platform-integration`
- Secrets, signing, updates → `desktop/_shared/security`, `desktop/_shared/distribution`; telemetry → `desktop/_shared/observability`
- Failure banners → `desktop-windows:error-handling`
- Win32 restart registration → `desktop-windows:interop`
- Mac counterpart → `desktop-macos:system-integration`
