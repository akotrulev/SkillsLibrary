---
name: auth0
description: Use when adding or fixing Auth0 login in a native macOS Swift/SwiftUI app (Auth0.swift, PKCE, Keychain). Triggers "add Auth0 login to the Mac app". Not for tenant setup or OIDC theory.
disable-model-invocation: true
---

# Auth — Auth0 in macOS (Swift)

Wires **Auth0.swift** into a SwiftUI (or AppKit) Mac app. **Universal Login in the system browser session (`ASWebAuthenticationSession`) with PKCE is the only login flow** — no embedded `WKWebView` login (RFC 8252 §8.12). Concepts: `auth/_shared/auth0-concepts` / `auth/_shared/oidc-concepts`.

## Version lane (checked 2026-11-15)

| Fact | Value |
|---|---|
| SDK | **Auth0.swift 3.x** (3.3.x per the README's Carthage line — read the Releases page for the exact tag), Swift 6 |
| Minimum | macOS **12.0**; Xcode 26.x per the README. The project's own deployment target (CLAUDE.md § Desktop: macOS 15 new / 13 existing) wins; never raise it to adopt the SDK |
| Universal-link callback | macOS **14.4+** (Xcode 15.3+, paid Apple Developer account); older systems fall back to a custom URL scheme |
| Install | Swift Package Manager `https://github.com/auth0/Auth0.swift` |

Source: github.com/auth0/Auth0.swift (README, macOS section).

## Setup

`Auth0.plist` (`ClientId`, `Domain`) or values in code. Both are public; a Native application has no secret.

Dashboard (Native application): Allowed Callback **and** Logout URLs `https://DOMAIN/macos/BUNDLE_ID/callback` and `BUNDLE_ID://DOMAIN/macos/BUNDLE_ID/callback` (the fallback); grants Authorization Code + Refresh Token; **Refresh Token Rotation ON** with reuse detection. Xcode: **Associated Domains** `webcredentials:DOMAIN` for the https callback.

Sandbox (§5 least privilege): the App Sandbox needs **Outgoing Connections (Client)** (`com.apple.security.network.client`) for the token calls; the Keychain items the SDK writes need no extra entitlement for the app's own access group. Record the reason for each entitlement.

## Login, session, logout

```swift
@MainActor
@Observable
final class AuthSession {
    private let credentialsManager = CredentialsManager(authentication: Auth0.authentication())
    private(set) var state: State = .restoring

    enum State { case restoring, signedOut, signedIn(UserInfo), failed(AuthFailure) }

    func restore() async {
        guard credentialsManager.canRenew() || credentialsManager.hasValid() else { state = .signedOut; return }
        do {
            let credentials = try await credentialsManager.credentials()
            state = .signedIn(try credentialsManager.user ?? UserInfo(jwt: credentials.idToken))
        } catch {
            logger.error("Restore failed: \(error.localizedDescription, privacy: .public)")
            state = .signedOut
        }
    }

    func signIn() async {
        do {
            let credentials = try await Auth0.webAuth()
                .useHTTPS()
                .audience(AuthConfig.audience)
                .scope("openid profile email offline_access")
                .start()
            _ = credentialsManager.store(credentials: credentials)
            state = .signedIn(try UserInfo(jwt: credentials.idToken))
        } catch WebAuthError.userCancelled {
            state = .signedOut
        } catch {
            state = .failed(AuthFailure(error))
        }
    }

    func signOut() async {
        do {
            try await Auth0.webAuth().useHTTPS().clearSession()
        } catch {
            logger.error("Remote sign-out failed: \(error.localizedDescription, privacy: .public)")
        }
        _ = credentialsManager.clear()
        state = .signedOut
    }
}
```

- `.useHTTPS()` only where the deployment target is ≥ macOS 14.4; below it omit it and the SDK uses the custom scheme. Record which one ships.
- `AuthFailure` is the app's one mapping of `WebAuthError` / `CredentialsManagerError` to user text; the failed state raises the persistent inline banner (CLAUDE.md § Desktop). The user cancelling is a state, not an error.
- `signOut` clears local credentials even when the remote call fails; the failure is logged with `os.Logger` and no token values.
- The sign-in button carries `accessibilityIdentifier("Auth.SignIn")`; sign-out lives in the app menu (`Account`), disabled — never hidden — while signed out.

## Credentials manager (Keychain)

```swift
func authorizedRequest(_ url: URL) async throws -> URLRequest {
    let credentials = try await credentialsManager.credentials()
    var request = URLRequest(url: url, timeoutInterval: 15)
    request.setValue("Bearer \(credentials.accessToken)", forHTTPHeaderField: "Authorization")
    return request
}
```

- The manager stores in the **Keychain** and renews an expired access token with the stored refresh token; renewed credentials are saved automatically.
- Use **one** manager instance for the whole app — every window shares it. Several managers renew in parallel and trip refresh-token reuse detection.
- `clear()` removes the default entry; `clearAll()` removes every entry for the service/access group, so give Auth0 its own `storeKey`.
- A hard failure (`invalid_grant`, reuse detected) means signed out. A transient one (network, 429, 5xx) keeps the stale state with a retry, per the offline rule.
- Revalidate on window reactivation and wake from sleep (§5): call `credentials()` again; do not trust an in-memory flag.
- A 401 → one `credentials()` + one replay; 403 is permission, never a re-login.

## Sign in with Apple through Auth0

Offer it when third-party login is the primary sign-in on a Mac App Store build. Use `ASAuthorizationAppleIDProvider` and exchange the code with `Auth0.authentication().login(appleAuthorizationCode:...)`. On account deletion revoke the Apple token server-side.

## Rules

- `ASWebAuthenticationSession` Universal Login with PKCE only; no `WKWebView`, no password grant
- `audience` + `offline_access` explicit; rotation + reuse detection ON
- One `CredentialsManager`; tokens only in the Keychain via the SDK
- Access token to the API, never the ID token
- `os.Logger` only; no token or claim values; no force unwrap outside tests

## What NOT to do

- No client secret in `Auth0.plist` or source
- No `UserDefaults` / `@AppStorage` for tokens or an "isLoggedIn" source of truth
- No `clearAll()` on a shared Keychain service
- No embedded web view "to keep the user in the app"
- No raising the deployment target to adopt the SDK

## Generation steps

1. Confirm domain, Native client id, audience, bundle id, deployment target, sandbox on/off.
2. Dashboard URLs and rotation; Associated Domains; network-client entitlement.
3. Add the package and `Auth0.plist`; build `AuthSession`.
4. Render `restoring / signedOut / signedIn / failed` in SwiftUI.
5. Smoke on a signed build: sign in, quit and relaunch (restores), call the API, sign out, confirm the next sign-in asks for credentials.
