---
name: platform-integration
description: Use when adding pickers, share, clipboard, drag and drop, background tasks, widgets, WebView2 or Windows AI to WinUI. Triggers "open a file dialog". Not for toasts (activation-and-notifications).
---

# Windows — Platform Integration

How the app reaches the rest of Windows without breaking least privilege: **the Windows App SDK pickers, share, clipboard, drag and drop, out-of-process background tasks, widgets, a locked-down WebView2, and the Windows AI APIs behind readiness checks.** Audit rows: section J of `desktop-windows:standards-audit`. Windows AI detail: [`references/windows-ai.md`](references/windows-ai.md).

## Version lane

| Concern | Windows App SDK 2.6 (primary) | Note |
|---|---|---|
| Pickers | `Microsoft.Windows.Storage.Pickers` (1.8+), constructed with `AppWindow.Id`, returns `PickFileResult.Path` | Legacy `Windows.Storage.Pickers` needs `WinRT.Interop.InitializeWithWindow.Initialize(picker, hwnd)` |
| Background tasks | `Microsoft.Windows.ApplicationModel.Background.BackgroundTaskBuilder`, **MSIX only**, COM server in the manifest | WinUI has no `OnBackgroundActivated` |
| Share target / source | identity-gated; manifest `windows.shareTarget` | **Share-target activation in 2.x not re-verified (2026-11-15)** — build, run packaged, record |
| Widgets | Windows App SDK widget providers | packaged, Windows 11 |
| WebView2 | `Microsoft.Web.WebView2` 1.0.4314.35 | lock down (below) |
| Windows AI | `Microsoft.Windows.AI.*` | readiness + consent + LAF → reference |
| Identity | notifications, background tasks, associations, share target need packaged identity | an unpackaged app has none of them |

## When to use

- "Open or save a file", "paste an image", "drop files on the window", "share this"
- A task that runs when the app is closed, a widget, an embedded web page
- On-device AI features

## When NOT to use

- Toasts, push, protocol/file activation, startup task → `desktop-windows:activation-and-notifications`
- Window and navigation shell → `desktop-windows:windows-and-navigation`
- Local storage, `PasswordVault`, SQLite → `desktop-windows:offline-and-storage`
- HTTP calls → `desktop-windows:networking`; P/Invoke, COM → `desktop-windows:interop`

---

## Pickers — the Windows App SDK ones

```csharp
public async Task<string?> PickDocumentAsync(Window window, CancellationToken ct)
{
    var picker = new FileOpenPicker(window.AppWindow.Id)
    {
        SuggestedStartLocation = PickerLocationId.DocumentsLibrary,
        ViewMode = PickerViewMode.List,
    };
    picker.FileTypeFilter.Add(".myapp");
    PickFileResult? result = await picker.PickSingleFileAsync();
    return result?.Path;
}
```

- **Construct with `AppWindow.Id`** of the window that owns the dialog. No `InitializeWithWindow`, no raw `HWND`, for the new pickers. A picker created with the wrong window opens behind it or throws.
- **`null` is cancel,** a normal outcome, never an error banner.
- The user picks the file: the app needs **no broad file capability** (`broadFileSystemAccess` / `runFullTrust` file rights are not requested for this). Remember the choice with a path the app re-opens through the picker's result, not a saved global path assumption.
- **`FileSavePicker`** takes `SuggestedFileName`, a `FileTypeChoices` map and writes through a temp file then moves, so a failed write never leaves half a document (`desktop-windows:offline-and-storage`).
- **`FolderPicker`** for export folders; check write access before the long operation.
- **A path from a picker is data, not trust:** open read-only, cap size, validate content (`desktop-windows:activation-and-notifications` file rules).
- An **elevated** app cannot receive drag-drop from a non-elevated one — another reason never to elevate.

## Clipboard

- `Clipboard.GetContent()` → `DataPackageView`; `Contains(StandardDataFormats.Text)` before `GetTextAsync()`. Handle `COMException` when another process holds the clipboard: retry once with a short delay on a non-UI thread, then show a quiet inline message — never a modal.
- `DataPackage` with `SetText`, `SetBitmap`, `SetStorageItems`; `RequestedOperation = Copy`. Call `Clipboard.Flush()` before exit when the data must outlive the app.
- **Pasted content is untrusted** like a file: size cap, type check, sanitize before rendering (a pasted HTML fragment never reaches `WebView2` unescaped).
- Never write secrets to the clipboard without clearing them; if you must, set `ClipboardContentOptions.IsAllowedInHistory = false` and `IsRoamable = false`.
- Standard commands (`Ctrl+C`, `Ctrl+X`, `Ctrl+V`) keep their shortcuts → `desktop-windows:windows-and-navigation`.

## Drag and drop

- **Target:** `AllowDrop="True"`, `DragOver` sets `AcceptedOperation` and a caption, `Drop` reads `e.DataView` and `await e.DataView.GetStorageItemsAsync()`. Take a **deferral** when you await in the handler.
- **Validate every dropped item** (extension, size, count) and say what was rejected and why in the banner.
- **Source:** `CanDrag="True"` with `DragStarting` setting the `DataPackage`; the drag visual follows the selection.
- **Keyboard parity:** every drag-drop action has a keyboard path (cut/paste, a "Move to…" command) — drag-drop alone fails the keyboard-first rule.
- Reordering a list uses `CanReorderItems` plus a command alternative.

## Share

- **Source:** `DataTransferManager` for the window — `DataTransferManagerInterop.GetForWindow(hwnd)` and `ShowShareUIForWindow(hwnd)` (the `HWND` comes from `WindowNative.GetWindowHandle(window)`); fill `DataRequested` with title, text, URI or files. The share UI is the platform's: do not draw your own.
- **Target (receive shared content):** needs package identity and a `windows.shareTarget` manifest extension; arrives as an activation → the router validates it like any activation. **Not re-verified for Windows App SDK 2.x on 2026-11-15** — a task that builds it checks the manifest and activation kind against current Microsoft Learn first and records the result in the plan.

## Background tasks — packaged, out of process

- **When:** work that must run when the app is closed (sync, a timer, a system event). Not for work the app can do while open; not for keeping the app alive.
- **Shape (verified 2026-11-15):** register through the Windows App SDK `BackgroundTaskBuilder` (full-trust COM), with a `windows.comServer` `com:Extension` in the manifest and `LaunchAndActivationPermission` on the `com:ExeServer`. **MSIX packaging is required.** WinUI has no `OnBackgroundActivated`; the trigger activates your registered COM class.
- **Register once.** Check for an existing registration before registering, or unregister-all then re-register at launch, so a task never doubles.
- **Some triggers are unsupported** for full-trust apps (for example `TimeZoneChange`); read the trigger list before choosing one.
- **No `ExtendedExecutionSession` in WinUI:** a background task must finish its work in the time the system grants — make the work resumable and idempotent, persist progress, cancel on `Canceled`.
- **Never surface a modal from a background task;** a failure is logged, recorded and shown as the banner on next launch.
- Unpackaged apps use a scheduled task or a service — a recorded decision, and not a way around least privilege.

## Widgets

- Windows App SDK **widget providers**: a COM server, an Adaptive Cards template (JSON) and a provider class implementing the widget provider interface; packaged, Windows 11.
- **A widget shows data, not controls:** a card with at most a few actions that open the app through a protocol activation (validated → `desktop-windows:activation-and-notifications`).
- Cache the last good data so the card renders offline; update through the provider on a budget, never on a tight timer.
- Card text meets contrast and scales; every action has a label.

## WebView2 — locked down

- **Package:** `Microsoft.Web.WebView2` 1.0.4314.35; `await WebView.EnsureCoreWebView2Async()` before any use. The Evergreen runtime is the default; a fixed-version runtime is a recorded decision.
- **Navigation allowlist:** handle `NavigationStarting`, cancel anything off the allowlist (scheme `https`, exact hosts), including redirects, `NewWindowRequested` (set `Handled = true`; open allowed links through the system browser) and `FrameNavigationStarting`.
- **Settings in release:** `AreDevToolsEnabled = false`, `AreDefaultContextMenusEnabled = false`, `IsStatusBarEnabled = false`, `AreBrowserAcceleratorKeysEnabled = false`, `IsGeneralAutofillEnabled = false`, `IsPasswordAutosaveEnabled = false`.
- **Bridge messages are untrusted input.** `WebMessageReceived` → `TryGetWebMessageAsString()` (not `WebMessageAsJson` blindly), check `args.Source` against the allowlist, parse to a typed record, ignore unknown shapes. **No `AddHostObjectToScript` of a broad object;** expose one narrow, typed method at most.
- **Local content** through `SetVirtualHostNameToFolderMapping` with `Deny` or `Allow` cross-origin access chosen on purpose, never `file://` and never `NavigateToString` with user-supplied HTML.
- **A Content-Security-Policy** on local pages; no `eval`, no inline script.
- **User data folder** under the app's local data (packaged: `ApplicationData.Current.LocalFolder`), never a shared or world-writable path; clear it on sign-out.
- **Failure is a state:** `CoreWebView2.ProcessFailed` and `NavigationCompleted` with `IsSuccess = false` → the region's failed state and the `InfoBar`, never a blank WebView.
- Accessibility: the WebView2 exposes the page's own tree; give it `AutomationProperties.Name` and test it with Narrator.
- Deeper rules and audit rows: `desktop/_shared/security`.

## Windows AI APIs

Phi Silica, text recognition, image description, super resolution, segmentation and erase, speech — all behind `GetReadyState`, user consent before any model download, and for Phi Silica a Limited Access Feature. **Phi Silica is being replaced by Aion Instruct** (Windows Insider from November 2026, retail from January 2027, Phi Silica removed). Read [`references/windows-ai.md`](references/windows-ai.md) before writing any of it.

## Common gotchas

- **Picker constructed with the wrong `AppWindow.Id`** — behind the window or an exception; pass the owning window's id.
- **`InitializeWithWindow` copied from an old answer** — not needed for the new pickers; needed only for the legacy ones.
- **`await` in `Drop` without a deferral** — the drop completes before the data is read.
- **A background task registered at every launch** — duplicates; check or re-register.
- **WebView2 used before `EnsureCoreWebView2Async`** — null `CoreWebView2`.
- **Devtools left on** — a release-build finding.
- **A path assumed after a restart** — the user may have moved the file; re-pick.
- **Elevated app, broken drag-drop and no notifications** — drop elevation.

## Handoffs

- Activation, toasts, startup, push → `desktop-windows:activation-and-notifications`
- Storage, secrets → `desktop-windows:offline-and-storage`; HTTP → `desktop-windows:networking`
- COM, `HWND`, P/Invoke → `desktop-windows:interop`
- WebView2 and bridge security rows, signing → `desktop/_shared/security`, `desktop/_shared/distribution`
- Banner and failed states → [`ui-components`](../ui-components/SKILL.md), `desktop-windows:error-handling`
- Mac counterpart → `desktop-macos:sandbox-and-permissions`, `desktop-macos:system-integration`
