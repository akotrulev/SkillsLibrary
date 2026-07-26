---
name: auth-cognito-react
description: Use when the user asks to set up or modify AWS Cognito (user pools) sign-in in a React 18 + TypeScript SPA — `react-oidc-context` + `oidc-client-ts`, Authorization Code + PKCE against the user-pool issuer, protected routes, attaching the resource-server-scoped access token to fetch, silent renew, and the Cognito logout workaround. Triggers: "add Cognito login to my React app", "react-oidc-context with Cognito", "Cognito hosted UI from React", "attach the Cognito access token to fetch", "Cognito logout in React doesn't redirect", "cognito:groups in the SPA". Do NOT use for backend validation (use `backend/dotnet/skills/cognito` / `backend/java/skills/cognito`), Blazor (use `auth/cognito-blazor`), Auth0 (use `auth/auth0-react`), Cognito **identity pools**/AWS-credential vending (out of scope), or concepts (use `auth/_shared/oidc-concepts`).
---

# Auth — AWS Cognito in React (SPA)

Wires an Amazon Cognito **user pool** into a React 18 + TypeScript SPA using **`react-oidc-context`** (over `oidc-client-ts`). Authorization Code + PKCE against the pool's OIDC issuer, silent renew via refresh token, route protection, resource-server-scoped access-token attachment. The React sibling of [`auth/cognito-blazor`](../cognito-blazor/SKILL.md); the Auth0 equivalent is [`auth/auth0-react`](../auth0-react/SKILL.md).

> **Why `react-oidc-context`, not `@auth0/auth0-react`?** The Auth0 SDK is Auth0-specific. Cognito is a standard OIDC provider, so the generic `react-oidc-context` is the idiomatic path (AWS Amplify Auth is the alternative, but it drags in the whole Amplify runtime; use it only if you're already on Amplify). Generic OIDC concepts: [`auth/_shared/oidc-concepts`](../_shared/oidc-concepts/SKILL.md).

## The Cognito deltas vs Auth0 (React)

| Concern | Auth0 (`auth0-react`) | **Cognito (here)** |
|---|---|---|
| SDK | `@auth0/auth0-react` | **`react-oidc-context`** (+ `oidc-client-ts`) |
| Authority | `https://{domain}` | **`https://cognito-idp.{region}.amazonaws.com/{userPoolId}`** |
| API scoping | `audience` param | **resource-server scope** in `scope` (e.g. `https://api.yourco.com/orders.read`); **no `audience`, no `offline_access`** |
| Refresh | `useRefreshTokens` + `offline_access` | refresh token issued automatically per app-client config; `oidc-client-ts` `automaticSilentRenew` uses it |
| Logout | SDK `logout()` hits `/v2/logout` | **no `end_session_endpoint`** → manually redirect to `{hostedDomain}/logout?client_id=&logout_uri=` |
| Roles | namespaced claim | **`cognito:groups`** on the token |

## When to use

- A React SPA that needs Cognito user-pool sign-in / sign-out
- Protecting routes; attaching the access token to API calls
- Reading `cognito:groups` / scopes to gate UI affordances

## When NOT to use

- Backend JWT validation → `backend/dotnet/skills/cognito` / `backend/java/skills/cognito`
- Blazor → [`auth/cognito-blazor`](../cognito-blazor/SKILL.md)
- Auth0 → [`auth/auth0-react`](../auth0-react/SKILL.md)
- Cognito **identity pools** / AWS-credential vending → out of scope (user-pool OIDC only)
- Concepts → [`auth/_shared/oidc-concepts`](../_shared/oidc-concepts/SKILL.md)

## Inputs needed

1. **Region** + **`userPoolId`** + **public app-client id** (no secret) per env, injected as build-time env vars
2. **Hosted-UI domain** (for logout) and **callback / sign-out URLs** registered on the app client
3. **Resource server scopes** the SPA requests (e.g. `https://api.yourco.com/orders.read`)
4. **Backend API** origin the token is attached to

## Setup

### Install

```bash
pnpm add react-oidc-context oidc-client-ts
```

### Env vars (Vite)

```ini
# .env.local — never committed. Public app client → NO secret.
VITE_COGNITO_AUTHORITY=https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_ABC123
VITE_COGNITO_CLIENT_ID=<public-app-client-id>
VITE_COGNITO_HOSTED_DOMAIN=https://yourco.auth.eu-west-1.amazoncognito.com
VITE_COGNITO_SCOPE=openid profile email https://api.yourco.com/orders.read
VITE_API_ORIGIN=https://api.yourco.com
```

### Provider

```tsx
// src/auth/CognitoAuthProvider.tsx
import { AuthProvider, type AuthProviderProps } from 'react-oidc-context';
import { WebStorageStateStore } from 'oidc-client-ts';
import { type ReactNode } from 'react';

const oidcConfig: AuthProviderProps = {
  authority: import.meta.env.VITE_COGNITO_AUTHORITY!,
  client_id: import.meta.env.VITE_COGNITO_CLIENT_ID!,
  redirect_uri: window.location.origin + '/callback',
  response_type: 'code',                                   // Authorization Code + PKCE
  scope: import.meta.env.VITE_COGNITO_SCOPE!,              // NO offline_access — Cognito returns the refresh token per app-client config
  automaticSilentRenew: true,                              // uses the refresh token
  userStore: new WebStorageStateStore({ store: window.sessionStorage }),  // session, not localStorage
  // Strip the code/state from the URL after the redirect completes:
  onSigninCallback: () => window.history.replaceState({}, document.title, window.location.pathname),
};

export function CognitoAuthProvider({ children }: { children: ReactNode }) {
  return <AuthProvider {...oidcConfig}>{children}</AuthProvider>;
}
```

Wrap the app once:

```tsx
// src/main.tsx
import { CognitoAuthProvider } from './auth/CognitoAuthProvider';

createRoot(document.getElementById('root')!).render(
  <CognitoAuthProvider>
    <App />
  </CognitoAuthProvider>,
);
```

`sessionStorage` clears on tab close (safer default). Use `localStorage` only when cross-tab persistence is a real requirement and you've reasoned about the XSS exposure — never store a client secret (SPAs don't have one).

### Login / logout — the Cognito logout workaround

Login is standard. **Logout needs a manual redirect** because Cognito omits `end_session_endpoint`: `removeUser()` clears the local session, then send the browser to the Cognito `/logout` URL so the Cognito session cookie is also cleared.

```tsx
import { useAuth } from 'react-oidc-context';

export function AuthControls() {
  const auth = useAuth();

  const signOut = async () => {
    await auth.removeUser();                                // clear local oidc-client-ts session
    const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID!;
    const domain = import.meta.env.VITE_COGNITO_HOSTED_DOMAIN!;
    const logoutUri = encodeURIComponent(window.location.origin);   // must be an Allowed sign-out URL
    window.location.assign(`${domain}/logout?client_id=${clientId}&logout_uri=${logoutUri}`);
  };

  if (auth.isLoading) return null;
  return auth.isAuthenticated ? (
    <>
      <span>{auth.user?.profile['cognito:username'] as string}</span>
      <button onClick={signOut}>Sign out</button>
    </>
  ) : (
    <button onClick={() => auth.signinRedirect()}>Sign in</button>
  );
}
```

### Protected routes

```tsx
import { useAuth } from 'react-oidc-context';
import { type ReactNode, useEffect } from 'react';

export function RequireAuth({ children }: { children: ReactNode }) {
  const auth = useAuth();
  useEffect(() => {
    if (!auth.isLoading && !auth.isAuthenticated && !auth.activeNavigator) {
      void auth.signinRedirect({ state: { returnTo: window.location.pathname } });
    }
  }, [auth.isLoading, auth.isAuthenticated, auth.activeNavigator]);

  if (auth.isLoading || !auth.isAuthenticated) return <LoadingScreen />;
  return <>{children}</>;
}
```

Per-permission gates read `cognito:groups` / scopes and conditionally render — the **backend is the enforcer**; the UI is a hint.

### Calling the API

```tsx
// src/api/useApi.ts
import { useAuth } from 'react-oidc-context';
import { useCallback } from 'react';

export function useApi() {
  const auth = useAuth();
  return useCallback(async <T,>(path: string, init: RequestInit = {}): Promise<T> => {
    const token = auth.user?.access_token;                 // Cognito access token (JWT)
    const res = await fetch(import.meta.env.VITE_API_ORIGIN + path, {
      ...init,
      headers: { ...init.headers, Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    });
    if (res.status === 401) { void auth.signinRedirect(); throw new Error('re-auth'); }
    if (!res.ok) throw new Error(`API ${res.status}`);
    return res.json() as Promise<T>;
  }, [auth]);
}
```

`automaticSilentRenew` refreshes the access token in the background; on a hard 401 (refresh expired/revoked), redirect to sign-in.

### Reading groups & scopes

```tsx
const auth = useAuth();
const groups = (auth.user?.profile['cognito:groups'] as string[] | undefined) ?? [];
const scopes = (auth.user?.scope ?? '').split(' ');
```

## Cognito app-client settings (matching this skill)

- **App client type**: Public client (no secret), with PKCE.
- **Allowed callback URLs**: `http://localhost:5173/callback`, `https://app.yourco.com/callback`, …
- **Allowed sign-out URLs**: `http://localhost:5173`, `https://app.yourco.com`, … (gate `logout_uri`).
- **OAuth grant types**: Authorization code grant.
- **OpenID scopes**: `openid`, `profile`, `email` + your resource-server scopes.
- **Refresh token expiration** set deliberately; **token revocation** enabled.

## Rules

- Authorization Code + PKCE only; **public app client, no secret** in the bundle.
- Authority = the user-pool issuer; **no `audience`, no `offline_access`** — request resource-server scopes; the refresh token comes automatically.
- **Logout is a manual redirect** to `{hostedDomain}/logout?client_id=&logout_uri=` after `removeUser()` (no `end_session_endpoint`); `logout_uri` must be an Allowed sign-out URL.
- `sessionStorage` by default; document the threat model before switching to `localStorage`.
- Send the **access token** (not the ID token) to the API; let `automaticSilentRenew` refresh; redirect on hard 401.
- Gate UI by `cognito:groups` / scopes; the backend authorizes.
- All Cognito env vars are `VITE_*`/`NEXT_PUBLIC_*` (public) — never a secret.

## What NOT to do

- No client secret in the front-end (public app client).
- No `audience` param (Auth0-ism) and no `offline_access` scope (Cognito rejects it).
- No relying on the SDK's standard logout to redirect to Cognito — it needs the manual `/logout` URL.
- No sending the ID token to the API (use the access token).
- No storing tokens by hand in `localStorage` — the store is a config setting.
- No client-side "is admin → do the dangerous thing" as the authorization decision — the backend enforces.
- No mixing user pools across environments.

## Generation steps

1. Confirm region + pool id + public client id (per env), hosted domain, callback/sign-out URLs, resource-server scopes, API origin.
2. Register the URLs on the Cognito app client; enable Authorization code grant + PKCE + token revocation.
3. Install `react-oidc-context` + `oidc-client-ts`; add `CognitoAuthProvider` and wrap `<App />`.
4. Add `AuthControls` (with the manual logout redirect) + `RequireAuth`.
5. Create `useApi()` that attaches the access token and re-auths on 401.
6. Smoke: visit a protected route signed out → Cognito Hosted UI → sign in → land back → authenticated API call → sign out → confirm the Cognito session cookie cleared (a fresh sign-in prompts again).

## Handoffs

- Backend validation → `backend/dotnet/skills/cognito` / `backend/java/skills/cognito`
- Blazor → [`auth/cognito-blazor`](../cognito-blazor/SKILL.md)
- Auth0 equivalent → [`auth/auth0-react`](../auth0-react/SKILL.md)
- React patterns (providers, custom hooks) → `frontend/react/skills/component-writer`
- E2E with auth → `qa/typescript/skills/ui-test-author/playwright` (use `storageState` for an authenticated session)
