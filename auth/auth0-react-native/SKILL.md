---
name: auth-auth0-react-native
description: Use when adding or fixing Auth0 sign-in in a React Native / Expo app with `react-native-auth0` — Universal Login in the system browser (PKCE), universal link / App Link callback, the credentials manager, biometric unlock, refresh-token rotation, logout. Triggers "add Auth0 login to the Expo app", "callback never returns to the app", "biometric unlock for the session". Do NOT use for Auth0 concepts (`auth-auth0-concepts`), native Swift/Kotlin apps (`auth-auth0-ios` / `auth-auth0-android`), or React web (`auth-auth0-react`).
---

# Auth — Auth0 in React Native / Expo

Wires `react-native-auth0` into an Expo (development build / CNG) or bare React Native app. **Universal Login in the system browser with PKCE is the only login flow** — RFC 8252 forbids embedded web-view login, and Auth0's Native application type has no client secret. Entities, `audience`, RBAC and claims are `auth-auth0-concepts`; flow and token theory is `auth-oidc-concepts`. Not repeated here.

## Version lane (checked 2026-10-10)

| Fact | Value |
|---|---|
| SDK | `react-native-auth0` **5.11.1** (2026-09-08; `auth0/react-native-auth0`) |
| Requires (v5.x) | React Native ≥ 0.78 with React 19, **Expo ≥ 53**; Expo < 53 → v4.x; **not Expo Go** — a development build or EAS build |
| Native layers | wraps Auth0.swift (iOS) and Auth0.Android; the README states iOS deployment target 14 and an Android platform minimum — read the installed README for the current floors, never lower a project's targets |
| Detect from | `package.json` (`react-native-auth0`, `expo`), `app.json` / `app.config.*` plugins, `android/app/build.gradle` for a bare app |

## When to use

- New sign-in / sign-out in an RN or Expo app against Auth0
- The browser returns but the app never receives the callback
- Silent re-login, session restore at launch, biometric unlock of stored credentials
- Calling a protected API with the access token

## When NOT to use

- Auth0 entity model, `audience`, RBAC → `auth-auth0-concepts`; generic OAuth/OIDC → `auth-oidc-concepts`
- Native Swift app → `auth-auth0-ios`; Kotlin app → `auth-auth0-android`
- Backend token validation → `backend/*/auth0` skills
- Where else secrets and tokens may live → `mobile-shared-security`

## Inputs needed

1. Auth0 tenant domain and a **Native** Application's client id (no secret), per environment
2. API audience (identifier) and scopes, incl. `offline_access` for a refresh token
3. App id: bundle id (iOS) and package name (Android), lowercase; Apple Team ID; Android SHA-256 signing fingerprints (debug, upload, **Play App Signing** key)
4. Callback style: `https` universal link / App Link (default) or a custom scheme

## Setup

```bash
npx expo install react-native-auth0
```

```json
{
  "expo": {
    "plugins": [
      ["react-native-auth0", { "domain": "yourco-dev.eu.auth0.com", "customScheme": "https" }]
    ]
  }
}
```

- `domain` is required. `customScheme: "https"` makes the Android callback an **App Link** (`android:autoVerify="true"`); any other value must be lowercase, no special characters, and the **same value is passed to `authorize` and `clearSession`**.
- The domain and client id are not secrets, but they live in config per environment, not hard-coded in components. Never put a client secret anywhere — a Native application has none.
- Bare app: set `manifestPlaceholders = [auth0Domain: ..., auth0Scheme: "https"]` in `android/app/build.gradle` and forward `RCTLinkingManager` open-URL calls in `AppDelegate`. Prefer CNG so none of that is hand-edited.

### Auth0 dashboard (Native application)

| Setting | Value |
|---|---|
| Allowed Callback URLs | `https://DOMAIN/ios/BUNDLE_ID/callback`, `https://DOMAIN/android/PACKAGE/callback` |
| Allowed Logout URLs | the same two URLs |
| Device Settings → iOS | Team ID + bundle id (serves the Apple association file) |
| Device Settings → Android | package name + SHA-256 fingerprints (serves `assetlinks.json`) |
| Grant types | Authorization Code + Refresh Token |
| Refresh Token Rotation | **ON**, reuse detection ON, set absolute + inactivity lifetimes |
| iOS capability | Associated Domains: `webcredentials:DOMAIN` (paid Apple Developer account; sign even simulator builds with the team certificate) |

Without a universal link / App Link the SDK falls back to a custom scheme (`BUNDLE_ID.auth0` on iOS); a custom scheme can be claimed by another app, so https callbacks are the default and the fallback is a recorded exception.

## Provider and login

```tsx
import { Auth0Provider, useAuth0 } from 'react-native-auth0';

export function AuthRoot({ children }: { children: ReactNode }) {
  return (
    <Auth0Provider domain={config.auth0Domain} clientId={config.auth0ClientId}>
      {children}
    </Auth0Provider>
  );
}

export function SessionControls() {
  const { authorize, clearSession, user, isLoading, error } = useAuth0();

  if (isLoading) return <SessionLoading testID="Auth.Loading" />;

  return user ? (
    <Button testID="Auth.SignOut" title="Sign out" onPress={() => clearSession({ customScheme: 'https' })} />
  ) : (
    <Button
      testID="Auth.SignIn"
      title="Sign in"
      onPress={() =>
        authorize({ scope: 'openid profile email offline_access', audience: config.auth0Audience }, { customScheme: 'https' })
      }
    />
  );
}
```

- `authorize()` opens the system browser (`ASWebAuthenticationSession` on iOS, Custom Tabs on Android); the SDK runs PKCE. With no `scope` it requests `openid profile email` — add `offline_access` to receive a refresh token, and `audience` or the access token is opaque (`auth-auth0-concepts`).
- Errors are a state, not a crash: `a0.browser_not_available` (no browser on the device) and a user cancel are different outcomes; map both to messages and keep the app usable.
- Signed-out vs loading vs error is a three-state region; `testID` on every control, PascalCase dot-separated.

## Credentials and session restore

- **Storage is the SDK's**: Keychain on iOS; on Android the credentials are encrypted with a Keystore-held key and stored in app-private storage. **Tokens are never copied to `AsyncStorage`, MMKV, `expo-secure-store` by hand, or logs** — `mobile-shared-security` K2.
- With `Auth0Provider`, credentials are saved on login and cleared on logout automatically. Without it (the `new Auth0({...})` client) call `auth0.credentialsManager` `saveCredentials` yourself.
- At launch: `hasValidCredentials()` → `getCredentials()`; `getCredentials()` renews an expired access token with the refresh token and is safe to call concurrently. A renewal failure (`invalid_grant`, revoked, rotated away) means **signed out**, not retry forever.

### API calls

```ts
export function useApiClient() {
  const { getCredentials } = useAuth0();

  return useCallback(async (path: string, init: RequestInit = {}) => {
    const credentials = await getCredentials();
    const response = await fetch(`${config.apiBaseUrl}${path}`, {
      ...init,
      headers: { ...init.headers, Authorization: `Bearer ${credentials.accessToken}` },
      signal: AbortSignal.timeout(15_000),
    });
    if (!response.ok) throw new ApiError(response.status, await response.text());
    return response.json();
  }, [getCredentials]);
}
```

Feed it to TanStack Query as the `queryFn`. A 401 triggers one `getCredentials()` refresh and a single replay; a 403 is a permission outcome and never runs that path. Send the **access token** to the API, never the ID token.

## Biometric unlock

```ts
const localAuthenticationOptions = {
  title: 'Unlock your session',
  evaluationPolicy: LocalAuthenticationStrategy.deviceOwnerWithBiometrics,
  fallbackTitle: 'Use passcode',
  authenticationLevel: LocalAuthenticationLevel.strong,
  deviceCredentialFallback: true,
};

<Auth0Provider domain={...} clientId={...} localAuthenticationOptions={localAuthenticationOptions}>
```

- Retrieving credentials then prompts Face ID / Touch ID / the Android biometric prompt. The prompt text and `NSFaceIDUsageDescription` (iOS purpose string) must be specific — `mobile-shared-store-compliance` L4.
- It protects *retrieval of stored credentials on this device*; it is not a second factor at the server. Test it on a **real iOS device** (the simulator does not exercise it).
- A device with no secured lock screen cannot enrol — the denied path is a working screen (password login, still PKCE).

## Refresh-token rotation

Rotation is a tenant setting and the SDK stores the rotated token for you. Two practical rules: **never run two renewals at once** (use the one credentials manager the SDK gives you; do not build a parallel refresh), and when a flaky network can drop the rotation response, set the tenant's **rotation overlap period** so one retry of the old token succeeds. Reuse detection kills the token family on replay — a forced sign-out after a suspected replay is correct.

## Logout

`clearSession()` clears **the browser (SSO) session at Auth0** as well as the stored credentials; clearing local storage alone leaves the next `authorize()` silently re-signing the user in. The logout URL must be in **Allowed Logout URLs**, or the browser stays open. After logout drop every per-user cache (TanStack Query `clear()`, push token association, purchase user link).

## Rules

- System-browser Universal Login + PKCE only; no `WebView` login, no resource-owner password grant
- Native application type; no client secret in code, `app.json`, `extra` or `EXPO_PUBLIC_*`
- `audience` and `offline_access` set explicitly; refresh-token rotation + reuse detection ON
- https callbacks (universal link / App Link); a custom scheme only as a recorded exception
- Tokens live only in the SDK's Keychain / Keystore-backed storage
- One credentials manager; renewals are not duplicated
- `clearSession` on logout, with the same `customScheme` used at login

## What NOT to do

- No `AsyncStorage` / MMKV / `SecureStore` copy of an access or refresh token
- No `react-native-webview` login page
- No ID token in `Authorization` headers
- No `console.log(credentials)`
- No Expo Go testing of auth — it needs the development build
- No lowering iOS / Android targets to satisfy the SDK; report and let `project-setup` / `migration` decide

## Generation steps

1. Confirm domain, Native client id, audience, bundle id, package name, fingerprints, Team ID.
2. Configure the Auth0 dashboard rows above; enable rotation and reuse detection.
3. Add the plugin to `app.json`; build a development build (`npx expo prebuild` / EAS).
4. Wrap the app in `Auth0Provider`; add the session controls and the API client.
5. Add biometric options if the product needs them; handle the no-biometrics path.
6. Smoke flow on a **device**: sign in, kill and relaunch (session restores), call the API, sign out, confirm the next sign-in prompts for credentials.

## Handoffs

- Concepts → `auth-auth0-concepts`, `auth-oidc-concepts`
- Token storage rules → `mobile-shared-security`; purchase user link → `mobile-shared-in-app-purchases`
- Expo project, config plugins, builds → `mobile-react-native-project-setup`; deep links → `mobile-react-native-notifications-and-links`
- Server state / API client → `mobile-react-native-networking`
- Backend validation → `backend/dotnet/skills/auth0` / `backend/java/skills/auth0`
