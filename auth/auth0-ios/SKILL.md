---
name: auth-auth0-ios
description: Use when adding/fixing Auth0 sign-in in a native Swift / SwiftUI iOS app with Auth0.swift — Universal Login via ASWebAuthenticationSession (PKCE), universal-link callback, CredentialsManager on the Keychain, biometric unlock, refresh rotation, logout. Triggers "add Auth0 login", "callback doesn't return", "Face ID for stored credentials". Do NOT use for Auth0 concepts (`auth-auth0-concepts`), React Native (`auth-auth0-react-native`), or Android (`auth-auth0-android`).
---

# Auth — Auth0 in iOS (Swift)

Wires **Auth0.swift** into a SwiftUI (or UIKit) app. **Universal Login in `ASWebAuthenticationSession` with PKCE is the only login flow** — no embedded `WKWebView` login (RFC 8252). Concepts: `auth-auth0-concepts` / `auth-oidc-concepts`.

## Version lane (checked 2026-10-10)

| Fact | Value |
|---|---|
| SDK | **Auth0.swift 3.1.0** (2026-08-19), Swift tools 6.0, Swift 6 language mode in the package |
| Minimum | iOS **15**; Xcode 26.x per the README. The project's own deployment target (CLAUDE.md: iOS 17 primary / 16 supported) wins; never raise it as a side effect |
| Universal-link callback | iOS **17.4+** (Xcode 15.3+); older systems fall back to a custom URL scheme |
| Install | Swift Package Manager `https://github.com/auth0/Auth0.swift` (CocoaPods/Carthage are the legacy lane) |

## When to use

- New Auth0 sign-in / sign-out in a Swift app; calling a protected API with the token
- The web login closes but the app never gets the result
- Session restore at launch, biometric unlock, silent renewal
- Native Sign in with Apple exchanged for Auth0 tokens

## When NOT to use

- Concepts, RBAC, `audience` → `auth-auth0-concepts`
- RN / Expo → `auth-auth0-react-native`; Kotlin → `auth-auth0-android`
- Keychain / ATS rules in general → `mobile-shared-security`
- Backend validation → `backend/*/auth0`

## Setup

Config in `Auth0.plist` (`ClientId`, `Domain`) or passed in code. Both are public; the secret does not exist for a Native application.

```swift
struct AuthConfig {
    static let domain = "yourco-dev.eu.auth0.com"
    static let audience = "https://api.yourco.com"
}
```

Dashboard (Native application): callback and logout URLs `https://DOMAIN/ios/BUNDLE_ID/callback` and `BUNDLE_ID://DOMAIN/ios/BUNDLE_ID/callback` (the fallback); **Device Settings** → Team ID + bundle id; grants Authorization Code + Refresh Token; **Refresh Token Rotation ON** with reuse detection and lifetimes. Xcode: **Associated Domains** capability with `webcredentials:DOMAIN`; a paid Apple Developer account and a team-signed build even in the simulator.

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
            state = .signedIn(try UserInfo(jwt: credentials.idToken))
        } catch {
            state = .signedOut
        }
    }

    func signIn() async {
        do {
            let credentials = try await Auth0.webAuth()
                .useHTTPS()
                .audience(AuthConfig.audience)
                .scope("openid profile email offline_access")
                .useCredentialsManager(credentialsManager)
                .start()
            state = .signedIn(try UserInfo(jwt: credentials.idToken))
        } catch let error as WebAuthError where error == .userCancelled {
            state = .signedOut
        } catch {
            state = .failed(AuthFailure(error))
        }
    }

    func signOut() async {
        try? await Auth0.webAuth()
            .useHTTPS()
            .useCredentialsManager(credentialsManager)
            .logout()
        state = .signedOut
    }
}
```

- `.useHTTPS()` selects the universal-link callback. `.audience(...)` is required for a JWT access token; `offline_access` yields the refresh token.
- `.useCredentialsManager(_:)` on **both** `start()` and `logout()` — omit it on logout and the stored credentials survive.
- `logout()` clears the Auth0 **browser (SSO) session cookie**; clearing only local storage lets the next `start()` sign the user straight back in. The logout URL must be an Allowed Logout URL.
- `UserInfo(jwt:)` is the SDK's ID-token decoder; the ID token is for the app, **never** the `Authorization` header.
- The `@Observable` model is `@MainActor` (CLAUDE.md § iOS); `signOut` swallowing the error is a deliberate best-effort — failure is logged with `os.Logger`, local state still clears. SwiftUI renders the four states in one `switch`; the sign-in button carries `accessibilityIdentifier("Auth.SignIn")`.
- The user cancelling the sheet is a state, not an error banner.

## Credentials manager (Keychain)

```swift
let credentials = try await credentialsManager.credentials()
```

- The manager stores in the **Keychain** and renews an expired access token with the stored refresh token; renewed credentials are saved automatically — do not call `store(credentials:)` again.
- `credentials()`, `renew()` and the API/SSO variants are thread-safe only through **one** manager instance — do not create several.
- `clear()` removes the default entry; `clearAll()` removes every entry for the service/access group, so give Auth0 its own `storeKey` / service. Never copy tokens to `UserDefaults` or the app's own files (`mobile-shared-security` K2).
- Transient renewal failures (network, 429, 5xx) can be retried with `maxRetries: 1`; this only works if the tenant's **rotation overlap period** is ≥ 180 s. A hard failure (`invalid_grant`, reuse detected) means signed out.

### API calls

```swift
func authorizedRequest(_ url: URL) async throws -> URLRequest {
    let credentials = try await credentialsManager.credentials()
    var request = URLRequest(url: url, timeoutInterval: 15)
    request.setValue("Bearer \(credentials.accessToken)", forHTTPHeaderField: "Authorization")
    return request
}
```

A 401 → one `credentials()` + one replay; 403 is permission, never a re-login.

## Biometric unlock

```swift
credentialsManager.enableBiometrics(
    withTitle: "Unlock your session",
    policy: .session(timeoutInSeconds: 300)
)
```

- Policies: `.default`, `.always`, `.session(timeoutInSeconds:)`, `.appLifecycle()`; `evaluationPolicy: .deviceOwnerAuthentication` allows passcode fallback. `clearBiometricSession()` / `isBiometricSessionValid()` give explicit control.
- Needs `NSFaceIDUsageDescription` (specific text — `mobile-shared-store-compliance` L4). Biometrics gate **retrieval on this device**; they are not a server factor. `userProfile()` reads the Keychain **without** the prompt, so keep sensitive data out of the ID-token claims you display unguarded.
- The cancelled / unavailable path is a working screen, not a dead end.

## Sign in with Apple through Auth0

Rule 4.8: if third-party/social login is the primary sign-in, offer Sign in with Apple. Use the native `ASAuthorizationAppleIDProvider` sheet and exchange the Apple authorization code with `Auth0.authentication().login(appleAuthorizationCode:...)` (native social login in the SDK; enable the Apple connection in Auth0). On account deletion the **Apple token must be revoked** server-side (`mobile-shared-store-compliance` L6).

## Passkeys

Auth0.swift supports passkey sign-up/login with the Authentication API; it needs `webcredentials:DOMAIN` (already present), a database connection with passkeys enabled and iOS 16.6+. Treat as optional; it does not replace Universal Login.

## Rules

- `ASWebAuthenticationSession` Universal Login with PKCE only; no `WKWebView` login, no password grant
- `.useHTTPS()` with a universal link on 17.4+; the scheme fallback is recorded
- `audience` + `offline_access` explicit; rotation + reuse detection ON
- One `CredentialsManager`; `useCredentialsManager` on login and logout
- Tokens only in the Keychain via the SDK — never `UserDefaults`
- Access token to the API, never the ID token
- `os.Logger` with no token or claim values; no force unwrap outside tests

## What NOT to do

- No client secret in `Auth0.plist` or source
- No `UserDefaults` / `@AppStorage` for tokens or "isLoggedIn" as the source of truth
- No parallel renewals across managers
- No `clearAll()` on a shared Keychain service
- No raising the deployment target to adopt the SDK

## Generation steps

1. Confirm domain, Native client id, audience, bundle id, Team ID, deployment target.
2. Dashboard URLs, Device Settings, rotation; add the `webcredentials:` capability.
3. Add the package; add `Auth0.plist`; build `AuthSession`.
4. Render `restoring / signedOut / signedIn / failed` in SwiftUI.
5. Add biometrics if required; wire Sign in with Apple if 4.8 applies.
6. Smoke on a **device**: sign in, relaunch (restores), call the API, sign out, confirm the next sign-in asks for credentials.

## Handoffs

- Concepts → `auth-auth0-concepts`; storage rules → `mobile-shared-security`
- Project / SPM / entitlements → `mobile-ios-project-setup`; links → `mobile-ios-notifications-and-links`
- Networking → `mobile-ios-networking`; purchase user link → `mobile-shared-in-app-purchases`
