---
name: auth-auth0-android
description: Use when adding/fixing Auth0 sign-in in a native Kotlin / Jetpack Compose Android app with Auth0.Android — Universal Login in Custom Tabs (PKCE), App Links callback, SecureCredentialsManager (Keystore), biometric unlock, refresh rotation, logout, passkeys. Triggers "add Auth0 login", "browser doesn't return", "biometric prompt for stored credentials". Do NOT use for Auth0 concepts (`auth-auth0-concepts`), React Native (`auth-auth0-react-native`), or iOS (`auth-auth0-ios`).
---

# Auth — Auth0 in Android (Kotlin)

Wires **Auth0.Android** into a Compose app. **Universal Login in the system browser (Custom Tabs) with PKCE is the only login flow** — no embedded `WebView` login (RFC 8252). Concepts: `auth-auth0-concepts` / `auth-oidc-concepts`.

## Version lane (checked 2026-10-10)

| Fact | Value |
|---|---|
| SDK | `com.auth0.android:auth0` **4.1.0** (2026-08-27) |
| Requires | `minSdk` **26**, Java 17 (`compileOptions` and `jvmTarget` 17). A project with `minSdk` < 26 stays on the **v3** line — never raise `minSdk` as a side effect |
| Project lane | Kotlin 2.x, Compose, JDK 21 toolchain (CLAUDE.md); the Gradle dependency goes in the version catalog |
| Application type | **Native** — no client secret |

## When to use

- New Auth0 sign-in / sign-out in a Kotlin app; calling a protected API
- The Custom Tab stays open or never returns to the app
- Session restore at launch, biometric-protected credentials, silent renewal

## When NOT to use

- Auth0 entities, `audience`, RBAC → `auth-auth0-concepts`
- RN / Expo → `auth-auth0-react-native`; Swift → `auth-auth0-ios`
- Keystore / storage rules in general → `mobile-shared-security`
- Backend validation → `backend/*/auth0`

## Setup

```kotlin
dependencies {
    implementation(libs.auth0)
}

android {
    defaultConfig {
        manifestPlaceholders["auth0Domain"] = "@string/com_auth0_domain"
        manifestPlaceholders["auth0Scheme"] = "https"
    }
}
```

`com_auth0_domain` and `com_auth0_client_id` come from per-flavour resources (public values; the secret does not exist). `INTERNET` permission in the manifest.

Dashboard (Native application): Allowed Callback **and** Logout URLs `https://DOMAIN/android/PACKAGE/callback`; **Device Settings** → package name + **SHA-256 fingerprints** (debug, upload, and the **Play App Signing** key — the one users actually run) so Auth0 serves a valid `assetlinks.json`; grants Authorization Code + Refresh Token; **Refresh Token Rotation ON** with reuse detection and lifetimes.

`https` + App Links is the default: Auth0 itself notes a **custom scheme can be claimed by another app** (client impersonation). If a custom scheme is unavoidable (no verified domain), set `auth0Scheme` and call `.withScheme("myapp")` on both login and logout; record it as an exception.

## Login, session, logout

```kotlin
class AuthRepository(
    private val account: Auth0,
    private val credentialsManager: SecureCredentialsManager,
    private val appContext: Context,
) {
    suspend fun signIn(activity: Activity): Credentials {
        val credentials = WebAuthProvider.login(account)
            .withAudience(BuildConfig.AUTH0_AUDIENCE)
            .withScope("openid profile email offline_access")
            .await(activity)
        credentialsManager.saveCredentials(credentials)
        return credentials
    }

    suspend fun signOut(activity: Activity) {
        WebAuthProvider.logout(account).await(activity)
        credentialsManager.clearCredentials()
    }

    suspend fun restore(): Credentials? =
        if (credentialsManager.hasValidCredentials()) credentialsManager.awaitCredentials() else null
}
```

- Use an **`Activity`** context to launch Custom Tabs, not the application context. The repository takes it per call; it never stores it.
- `withAudience` is required for a JWT access token; `offline_access` yields the refresh token (`saveCredentials` needs `expires_at` and an access or ID token).
- `logout` ends the **Auth0 browser (SSO) session**; the logout URL must be in Allowed Logout URLs or the tab stays open. Local clearing alone lets the next login silently succeed.
- Failures: `isBrowserAppNotAvailable` and `isAuthenticationCanceled` on `AuthenticationException` are distinct states — cancel is not an error banner; no browser is a message with a recovery.
- ViewModel: one `uiState: StateFlow` — `Restoring | SignedOut | SignedIn | Failed` — collected with `collectAsStateWithLifecycle`; dispatchers injected; no ViewModel-to-UI events. The sign-in button carries `Modifier.testTag("Auth.SignIn")`.

## Credentials manager (Keystore) and biometrics

```kotlin
val localAuthenticationOptions = LocalAuthenticationOptions.Builder()
    .setTitle("Unlock your session")
    .setDescription("Accessing your account")
    .setAuthenticationLevel(AuthenticationLevel.STRONG)
    .setNegativeButtonText("Cancel")
    .setDeviceCredentialFallback(true)
    .setPolicy(BiometricPolicy.Session(300))
    .build()

val credentialsManager = SecureCredentialsManager(
    AuthenticationAPIClient(account),
    context,
    SharedPreferencesStorage(context),
    fragmentActivity,
    localAuthenticationOptions,
)
```

- `SecureCredentialsManager` encrypts the credentials with a **Keystore-held AES key**; the encrypted blob sits in app-private storage — the **only** sanctioned place. Tokens never go to `SharedPreferences` in the clear, DataStore, Room, files or logs (`mobile-shared-security` K2).
- Biometric prompts need a `FragmentActivity` (Compose hosts: `FragmentActivity`/`AppCompatActivity`), a **secured lock screen**, and a `BiometricPolicy` (`Session(seconds)`, `Always`, `AppLifecycle`). `isBiometricSessionValid()` / `clearBiometricSession()` control it.
- A changed lock screen can invalidate the Keystore key: stored credentials become undecryptable until the user signs in again. Treat the resulting `CredentialsManagerException` as **signed out**, not a crash.
- Create **one** manager (injected singleton). Save/get are thread-safe; do not run renewals from parallel managers.
- Biometrics gate retrieval on this device; they are not a server factor. The no-biometrics path (password login) is a working screen.
- `awaitCredentials()` renews an expired access token with the stored refresh token and **saves the rotated token for you**. No stored refresh token or `invalid_grant` → sign in again.

### API calls

```kotlin
suspend fun authorizedGet(url: String): Response {
    val credentials = credentialsManager.awaitCredentials()
    val request = Request.Builder().url(url)
        .header("Authorization", "Bearer ${credentials.accessToken}")
        .build()
    return httpClient.newCall(request).await()
}
```

`httpClient` carries timeouts (CLAUDE.md § Mobile code rules). A 401 → one `awaitCredentials()` and one replay; 403 is permission, never a re-login. The ID token never goes to the API.

## Refresh-token rotation

Tenant setting; the manager persists the rotated token. A flaky network can lose the rotation response — set the tenant **rotation overlap period** so a single retry of the old token works. Reuse detection kills the token family on replay: a forced sign-out is correct.

## Passkeys

Auth0.Android 4.x supports passkey sign-up/login through the Authentication API (Credential Manager API, Android 9+ with Google Play services). Requires a database connection with passkeys enabled and the domain's `assetlinks.json` to carry the `delegate_permission/common.get_login_creds` relation. Optional; Universal Login stays the baseline.

## Rules

- Custom Tabs Universal Login with PKCE only; no `WebView` login, no password grant
- App Links (`https`) callback; fingerprints include the Play App Signing key
- `audience` + `offline_access` explicit; rotation + reuse detection ON
- One `SecureCredentialsManager`; tokens only in Keystore-backed storage via the SDK
- Activity context for browser launch, never retained
- Access token to the API, never the ID token
- Structured logging (Timber/Logcat templates) with no token or claim values; no `!!` outside tests

## What NOT to do

- No client secret in `strings.xml`, `BuildConfig` or `gradle.properties` committed
- No `SharedPreferences`/DataStore copy of tokens; no `isLoggedIn` flag as the source of truth
- No `minSdk` bump to adopt v4 — stay on v3 and say so
- No `GlobalScope` for sign-in; use the ViewModel scope with injected dispatchers
- No manifest `exported` activities beyond the SDK's `RedirectActivity`

## Generation steps

1. Confirm domain, Native client id, audience, package name, flavours, SHA-256 fingerprints incl. Play App Signing, `minSdk`.
2. Dashboard URLs, Device Settings, rotation.
3. Add the dependency (version catalog), placeholders and resources.
4. Build `AuthRepository`, the `SecureCredentialsManager`, and the ViewModel `uiState`.
5. Add biometric options if required; handle the no-lock-screen path.
6. Smoke on a **device**: sign in, kill and relaunch (restores), call the API, sign out, confirm the next sign-in asks for credentials; verify the App Link with `adb shell pm get-app-links PACKAGE`.

## Handoffs

- Concepts → `auth-auth0-concepts`; storage rules → `mobile-shared-security`
- Project / Gradle / manifest → `mobile-android-project-setup`; links → `mobile-android-notifications-and-links`
- Networking → `mobile-android-networking`; purchase user link → `mobile-shared-in-app-purchases`
