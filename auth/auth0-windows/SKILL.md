---
name: auth0
description: Use when adding or fixing Auth0 login in a Windows WinUI or WPF app (.NET, system browser, PKCE, PasswordVault/DPAPI). Triggers "add Auth0 login". Not for tenant setup or OIDC theory.
---

# Auth — Auth0 in Windows desktop apps (.NET)

Wires Auth0 into a WinUI or WPF app with the **RFC 8252 native-app flow: the user's default browser + PKCE, redirect back to the app.** An embedded web view (WebView2 or otherwise) is never the login surface (RFC 8252 §8.12). Concepts: `auth/_shared/auth0-concepts` / `auth/_shared/oidc-concepts`.

## Version lane (checked 2026-11-15)

| Fact | Value |
|---|---|
| Auth0's .NET SDK | **`Auth0.OidcClient.*`** (github.com/auth0/auth0-oidc-client-net). Packages exist for **WPF** (`Auth0.OidcClient.WPF` 4.4.0, 2025-07-22), **WinForms** and UWP; **there is no WinUI package** |
| What this skill uses | **`Auth0.OidcClient.Core`** (the package the WPF one builds on, ≥ 4.2.0) with the app's own `IBrowser` that opens the system browser — for **both** WinUI and WPF |
| Why not `Auth0.OidcClient.WPF` | Its quickstart logs in **inside a WebView2 popup** (auth0.com/docs/quickstart/native/wpf-winforms). That is an embedded user agent; it is allowed only as a recorded deviation, never by default |
| Underlying OIDC library | `IdentityModel.OidcClient` is **deprecated and unlisted**; the successor is **`Duende.IdentityModel.OidcClient` 7.1.1** (2026-10-16; netstandard2.0, net8–net10; Apache-2.0). Check which one the pinned `Auth0.OidcClient.Core` version resolves and take its `IBrowser` namespace from that package |
| Runtime | .NET **10 LTS** primary / 11 supported; 8 and 9 are out of support — flag, do not target (CLAUDE.md § Desktop; plan 012 §4.2). WinUI on Windows App SDK **2.x**. Never up-level the TFM to adopt a package |

Verify the Core package's current version and `Auth0ClientOptions.Browser` on nuget.org before writing code; this skill's API names are the shape, not a pinned copy.

## When to use

- New Auth0 sign-in / sign-out in WinUI or WPF; calling a protected API
- Browser login finishes but the app never receives the result (activation / loopback)
- Session restore at launch, silent refresh, secure token storage

## When NOT to use

- Concepts, RBAC, `audience` → `auth/_shared/auth0-concepts`
- macOS → `auth/auth0-macos`; Blazor/web → `auth/auth0-blazor`
- Token storage, IPC and URL-activation hardening in general → `desktop/_shared/security`
- Backend validation → `backend/*/auth0`

## Choose the redirect (one per app)

| | Loopback (`http://127.0.0.1:PORT/callback`) | Protocol activation (`com.yourco.app:/callback`) |
|---|---|---|
| RFC 8252 | §7.3 — IP literal, **not `localhost`** (§8.3) | §7.1 — reverse-domain private-use scheme, single slash |
| Packaged WinUI | Works; the app listens on `HttpListener` bound to loopback only | **Default for packaged MSIX**: `uap:Protocol` in the manifest, delivered through `AppInstance` activation |
| WPF / unpackaged | **Default** — no registration | Needs a per-user registry scheme; the second launch must hand the URI to the running instance |
| Risks | Another local process can bind first; **PKCE + `state` are mandatory** and the listener closes after one request | Another app can claim the scheme; PKCE makes a stolen code useless. The activation URI is untrusted input (§5) |

Register the exact URI in **Allowed Callback URLs and Allowed Logout URLs**. Auth0 matches callback URLs exactly — register a **fixed** loopback port (and fail with a clear message if it is busy) unless the tenant is confirmed to accept any port.

## Setup

Public values only: domain, Native client id, audience. A Native application has no client secret — none in `appsettings.json`, resources or the MSIX.

Dashboard: grants Authorization Code + Refresh Token; **Refresh Token Rotation ON** with reuse detection; `offline_access` requested.

```csharp
public sealed class SystemBrowser(IBrowserLauncher launcher, ILoopbackListener listener) : IBrowser
{
    public async Task<BrowserResult> InvokeAsync(BrowserOptions options, CancellationToken cancellationToken)
    {
        await launcher.OpenAsync(new Uri(options.StartUrl));
        var callbackUrl = await listener.WaitForCallbackAsync(options.EndUrl, cancellationToken);
        return new BrowserResult { Response = callbackUrl, ResultType = BrowserResultType.Success };
    }
}
```

- `IBrowserLauncher` is `Windows.System.Launcher.LaunchUriAsync` (WinUI) or `Process.Start` with `UseShellExecute` (WPF). `ILoopbackListener` wraps `HttpListener` on `127.0.0.1`, answers the browser with a static "you can close this tab" page, and returns the full callback URL. For protocol activation, replace it with a `TaskCompletionSource` completed from `AppInstance.GetCurrent().Activated`.
- Timeout and user-closed-the-tab → `BrowserResultType.Timeout` / `UserCancel`, handled as a state, not a crash.

## Session, login, logout

```csharp
public sealed class AuthSession(Auth0Client client, ITokenStore tokenStore, ILogger<AuthSession> logger)
{
    public async Task<SessionState> RestoreAsync(CancellationToken cancellationToken)
    {
        var refreshToken = tokenStore.ReadRefreshToken();
        if (refreshToken is null) return SessionState.SignedOut;
        var result = await client.RefreshTokenAsync(refreshToken, cancellationToken: cancellationToken);
        if (result.IsError)
        {
            logger.LogWarning("Refresh failed: {Error}", result.Error);
            tokenStore.Clear();
            return SessionState.SignedOut;
        }
        tokenStore.Save(result.RefreshToken ?? refreshToken);
        return SessionState.SignedIn(result.AccessToken, result.AccessTokenExpiration);
    }

    public async Task<SessionState> SignInAsync(CancellationToken cancellationToken)
    {
        var result = await client.LoginAsync(cancellationToken: cancellationToken);
        if (result.IsError) return SessionState.Failed(result.Error);
        tokenStore.Save(result.RefreshToken);
        return SessionState.SignedIn(result.AccessToken, result.AccessTokenExpiration);
    }

    public async Task SignOutAsync(CancellationToken cancellationToken)
    {
        await client.LogoutAsync(cancellationToken: cancellationToken);
        tokenStore.Clear();
    }
}
```

- The SDK has **no credentials manager** on Windows: this class and `ITokenStore` are it. Keep **one** instance (constructor-injected singleton in the host) so refreshes never run in parallel and trip reuse detection.
- Rotation: always save the **new** refresh token from each refresh.
- Only the **refresh token** is persisted; the access token stays in memory and is re-minted at launch. Hard failure (`invalid_grant`) → clear and signed out; network failure → keep the stored token and show the offline/stale state.
- Run every call off the UI thread's blocking path (`await`) and return to the UI through `DispatcherQueue.TryEnqueue` (WinUI) / `Dispatcher` (WPF).
- Revalidate on window activation and after resume from sleep (§5).
- State renders as `restoring / signedOut / signedIn / failed` with a persistent `InfoBar` (WinUI) on failure. The sign-in button carries `AutomationProperties.AutomationId="Auth.SignIn"` and an `AutomationProperties.Name`.

## Token storage (§5: `PasswordVault` / DPAPI only)

| Lane | Store | Notes |
|---|---|---|
| Packaged WinUI | `Windows.Security.Credentials.PasswordVault` | Per-user, per-app; resource = app id, user name = `refresh_token` |
| WPF, unpackaged, .NET | `ProtectedData.Protect(..., DataProtectionScope.CurrentUser)` to a file under `%LOCALAPPDATA%\<App>` | Add `entropy` bytes; `LocalMachine` scope is never used |

Never `appsettings.json`, `ApplicationData.LocalSettings`, the registry in clear text, or logs. Log `result.Error`, never a token or claim value.

## Rules

- System browser + PKCE only; no WebView2/WebBrowser login, no password grant, no implicit flow
- Loopback uses `127.0.0.1` and closes after one request; private-use scheme is reverse-domain with a single slash
- `state` and PKCE verified by the SDK; do not disable them
- `audience` + `offline_access` explicit; rotation + reuse detection ON
- One `AuthSession`; refresh token only in `PasswordVault` / DPAPI
- Access token to the API, never the ID token
- `ILogger` message templates; constructor injection; no static mutable state

## What NOT to do

- No client secret anywhere in the package
- No `localhost` in the redirect; no wildcard or shared-port redirect
- No parallel refreshes; no token in `LocalSettings` or a plain file
- No `Auth0.OidcClient.WPF` popup login without a recorded deviation
- No raising the TFM or Windows App SDK major to adopt a package

## Generation steps

1. Confirm lane (WinUI packaged / WPF), TFM, domain, client id, audience.
2. Pick the redirect from the table; register it as callback and logout URL; set rotation.
3. Add `Auth0.OidcClient.Core`; write `SystemBrowser`, the listener or activation hook, `ITokenStore`.
4. Build `AuthSession` and bind its states in the view model.
5. Smoke on a built app: sign in, relaunch (restores), call the API, sign out, confirm the next sign-in asks for credentials and the vault entry is gone.

## Handoffs

- Concepts → `auth/_shared/auth0-concepts`; storage and activation hardening → `desktop/_shared/security`
- Packaging manifest and signing → `desktop/_shared/distribution`
- UI states, `InfoBar`, threading → the Windows desktop skills
