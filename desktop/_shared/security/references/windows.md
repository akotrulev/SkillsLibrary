# Security — Windows reference

Lane: WinUI on Windows App SDK 2.x with C# (primary), WPF, WinForms and C++/WinRT; packaged MSIX by default, unpackaged where the project is. Facts from `docs/research/012-desktop-plugins/windows.md` §5, §6 and Microsoft Learn (Win32 DLL security, WebView2 security; verified 2026-11-15). §4.6 items stay open: **`PasswordVault` for unpackaged apps** and the Windows Hello / passkey APIs are not verified — check before writing either as fact.

## Credentials and data at rest

- Tokens in `PasswordVault` (Credential Locker) on packaged apps; on unpackaged apps or where the vault is unverified, DPAPI through `ProtectedData.Protect(..., DataProtectionScope.CurrentUser)` or `DataProtectionProvider("LOCAL=user")`, with the blob in the user's local app data.

```csharp
public sealed class TokenStore
{
    private const string Resource = "Example.App.Auth";

    public void Save(string account, string token)
    {
        var vault = new PasswordVault();
        vault.Add(new PasswordCredential(Resource, account, token));
    }

    public string? Read(string account)
    {
        var vault = new PasswordVault();
        var matches = vault.FindAllByResource(Resource).Where(c => c.UserName == account);
        var credential = matches.FirstOrDefault();
        credential?.RetrievePassword();
        return credential?.Password;
    }
}
```

`FindAllByResource` throws when nothing is stored: the real code wraps that one named exception into an empty result and logs it.
- Never `appsettings.json`, the registry in clear, `ApplicationData.LocalSettings`, a plain file, a `.resx`, or a literal in source. Debug builds use `dotnet user-secrets` or environment variables, never a committed file.
- A secret held as `string` cannot be wiped; hold short-lived secret bytes in a `byte[]` and `CryptographicOperations.ZeroMemory` them after use. Sign-out drops cached tokens.

## Least privilege and capabilities

- Never require elevation: `requireAdministrator` in an app manifest is a blocker for a normal app, and an elevated app cannot send or receive app notifications.
- Packaged apps declare the minimum capabilities in `Package.appxmanifest`; `runFullTrust` is listed with its reason (WinUI desktop apps need it), `broadFileSystemAccess`, `allowElevation` and `rescap` capabilities each carry a recorded reason. Prefer the Windows App SDK pickers over broad file access.
- Per-user data goes under `LocalApplicationData` / the package's `LocalFolder`; nothing writable by the user sits beside the executable, and nothing is written to `Program Files`.

## DLL loading (DA8)

The default search order starts with the application directory, then system directories, then the current directory, then `PATH`; a writable directory early in that list is a planting site (Microsoft Learn, *Dynamic-Link Library Security*).

- Native code: call `SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_DEFAULT_DIRS)` once, first thing in process start, then `AddDllDirectory` for any extra folder; load with `LoadLibraryExW` and an absolute path or `LOAD_LIBRARY_SEARCH_*` flags. `SetDllDirectory(L"")` once early removes the current directory where a flag set is not possible. Never `SearchPath` then `LoadLibrary`.
- C# P/Invoke: declare `[DefaultDllImportSearchPaths(DllImportSearchPath.SafeDirectories)]` (or `System32` / `AssemblyDirectory` as the library requires) on the import or the assembly; `NativeLibrary.Load(absolutePath)` for runtime loads. A bare `DllImport("name")` with no search-path attribute is a finding.
- A plug-in folder is read from the install location, never from a user-writable path, and plug-ins are loaded only if signed by the app's publisher.
- Do not decide anything from whether a `LoadLibrary` call succeeds (a planted copy answers too). Unpackaged installers do not drop binaries into user-writable folders that a higher-privilege process later loads from.
- Compiler and linker protections for C++ (`/GS`, `/DYNAMICBASE`, `/HIGHENTROPYVA`, `/guard:cf`, `/CETCOMPAT`) are set in the `.vcxproj`; their effect on the built binary is **requires dynamic test → `qa-security`**.

## Named pipes, COM and local IPC (DA1, DA5)

- A `NamedPipeServerStream` for a same-user client sets a `PipeSecurity` that grants only the current user (and the service SID where one exists); the default DACL is not relied on, and `Everyone` / `AuthenticatedUsers` never appear. `PipeOptions.CurrentUserOnly` is the simple choice for same-user pipes.
- The server validates the client where identity matters (`RunAsClient`, process id and image path check), caps message size, and parses messages into typed values.
- Out-of-process COM servers and `AddHostObjectToScript` objects are surfaces: expose the smallest interface.

## Protocol and file activation (DA1, DA6)

- Handlers registered in `Package.appxmanifest` (`uap:Protocol`, `uap:FileTypeAssociation`) route through `AppInstance.GetCurrent().GetActivatedEventArgs()`. The `Uri` / file path in the args is hostile: check scheme, host, path and query against an allow-list, canonicalise paths, bound file size, open read-only first. A protocol launch never executes, deletes or authorises anything without in-app confirmation.
- A custom protocol is claimable by any app; an OAuth redirect uses the loopback or claimed-URI flow (`auth0-windows`), never a bare custom scheme carrying a code without PKCE.
- Command-line arguments are the same input as activation: no argument becomes a shell string.

## WebView2

`Microsoft.Web.WebView2` 1.0.4314.35 (research §5). Rules from Microsoft's *Develop secure WebView2 apps*:

```csharp
public async Task ConfigureAsync(WebView2 view, IReadOnlySet<string> allowedHosts)
{
    await view.EnsureCoreWebView2Async();
    var core = view.CoreWebView2;
    core.Settings.AreDevToolsEnabled = false;
    core.Settings.AreHostObjectsAllowed = false;
    core.Settings.AreDefaultContextMenusEnabled = false;
    core.Settings.IsWebMessageEnabled = true;
    core.NavigationStarting += (_, e) =>
    {
        var uri = new Uri(e.Uri);
        e.Cancel = uri.Scheme != Uri.UriSchemeHttps || !allowedHosts.Contains(uri.Host);
    };
}
```

- Treat all web content as insecure: check `Source` before `ExecuteScriptAsync`, `PostWebMessageAsJson` or trusting a `WebMessageReceived`; validate every message against a schema; design specific messages, never a generic proxy.
- Send with `PostWebMessageAsJson` built by a JSON library, never string concatenation.
- Turn off what is unused: `AreHostObjectsAllowed`, `IsWebMessageEnabled`, `IsScriptEnabled` (static content), `AreDefaultScriptDialogsEnabled`; `AreDevToolsEnabled = false` in release (`#if DEBUG` is the only place it is `true`).
- Cancel off-list navigation in `NavigationStarting` and `FrameNavigationStarting`; remove host objects on `ContentLoading` with `RemoveHostObjectFromScript`.
- `AddScriptToExecuteOnDocumentCreated` runs on every navigation: a script that exposes native data must check `location.origin`.
- Host WebView2 at standard integrity; an elevated host ignores `WEBVIEW2_*` env and HKCU overrides. WebView2 cannot run as SYSTEM.
- The user-data folder lives under the user's local app data, not next to the exe.

## Transport and updates

- HTTPS only; `ServerCertificateCustomValidationCallback = (_, _, _, _) => true` and `DangerousAcceptAnyServerCertificateValidator` are blockers. `ServicePointManager.SecurityProtocol` is not set to old protocols; the OS default stands.
- Updates: MSIX through the Store or a signed `.appinstaller`; unpackaged through a signed Velopack feed. An update source on HTTP, or a package installed with its signature check bypassed (`-AllowUnsigned`, `Add-AppxPackage -AllowUnsigned`) is a blocker. Mechanics in `desktop/_shared/distribution`.

## What a source read cannot prove

What `PasswordVault` or DPAPI actually wrote, the effective DACL on a pipe, which DLL a live process loaded (Process Monitor), the capabilities in the installed package, WebView2 behaviour after navigation, and binary hardening flags: **requires dynamic test → `qa-security`**.
