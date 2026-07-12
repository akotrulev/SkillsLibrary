---
name: auth-auth0-react
description: Use when the user asks to set up or modify Auth0 in a React 18 + TypeScript SPA — `@auth0/auth0-react`, Authorization Code + PKCE, protected routes, calling a protected API with access tokens, silent refresh, organizations. Triggers: "add Auth0 login to my React app", "protect a route with Auth0", "attach the access token to fetch", "log out properly". Do NOT use for backend token validation (use `backend/dotnet/skills/auth0` / `backend/java/skills/auth0`), Blazor (use `auth/auth0-blazor`), or concepts (use `auth/_shared/auth0-concepts`).
---

# Auth — Auth0 in React (SPA)

Wires Auth0 into a React 18 + TypeScript SPA using `@auth0/auth0-react`. Authorization Code + PKCE flow, refresh-token rotation, route protection, access-token attachment to outbound `fetch`. Targets Vite or Next.js — App Router note: Auth0's `@auth0/nextjs-auth0` is the recommended Next.js path; this skill is for plain React SPAs and the SPA portions of Vite apps.

## Stack

- **React 18 + TypeScript (strict)**
- **`@auth0/auth0-react`** (the official SPA SDK)
- Authorization Code + PKCE (no client secret in the browser)
- Refresh token rotation enabled in the Auth0 SPA Application
- For Next.js App Router prefer `@auth0/nextjs-auth0` — referenced at the end of this skill

## When to use

- A new React SPA that needs Auth0 sign-in / sign-out
- Protecting routes (`react-router` or similar)
- Attaching the access token to `fetch` calls to a backend API
- Reading user profile / permissions in components
- Adding organization support (B2B)

## When NOT to use

- Backend JWT validation → `backend/dotnet/skills/auth0` / `backend/java/skills/auth0`
- Blazor Server / WASM → `auth/auth0-blazor`
- Concepts (audience, RBAC, organizations) → `auth/_shared/auth0-concepts`
- Next.js App Router with server-side session management → use `@auth0/nextjs-auth0` (this skill is the SPA pattern)

## Inputs needed

1. **Auth0 tenant domain** + **SPA Application client_id** + **API audience** (per env, injected at build time as env vars)
2. **Callback / logout URLs** registered in the Auth0 SPA Application
3. **Backend API** the SPA will call (its audience + the scopes/permissions it needs)
4. **Organization model** — single tenant or org-scoped sign-in

## Setup

### Install

```bash
pnpm add @auth0/auth0-react
```

### Env vars (Vite example)

```ini
# .env.local — never committed
VITE_AUTH0_DOMAIN=yourco-dev.eu.auth0.com
VITE_AUTH0_CLIENT_ID=...
VITE_AUTH0_AUDIENCE=https://api.yourco.com
```

For Next.js with the SPA pattern, prefix with `NEXT_PUBLIC_` so they're available client-side. **Never** put a client secret in front-end env vars — SPA Applications don't have one (PKCE replaces it).

### Provider

```tsx
// src/auth/Auth0ProviderWithNavigate.tsx
import { Auth0Provider, type AppState } from '@auth0/auth0-react';
import { type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

export function Auth0ProviderWithNavigate({ children }: { children: ReactNode }) {
  const navigate = useNavigate();

  const onRedirectCallback = (appState?: AppState) => {
    navigate(appState?.returnTo ?? window.location.pathname);
  };

  return (
    <Auth0Provider
      domain={import.meta.env.VITE_AUTH0_DOMAIN!}
      clientId={import.meta.env.VITE_AUTH0_CLIENT_ID!}
      authorizationParams={{
        redirect_uri: window.location.origin + '/callback',
        audience: import.meta.env.VITE_AUTH0_AUDIENCE,
        scope: 'openid profile email offline_access',
      }}
      cacheLocation="memory"             // 'localstorage' only if you really need cross-tab persistence
      useRefreshTokens={true}
      onRedirectCallback={onRedirectCallback}
    >
      {children}
    </Auth0Provider>
  );
}
```

Wrap your app once:

```tsx
// src/main.tsx
import { BrowserRouter } from 'react-router-dom';
import { Auth0ProviderWithNavigate } from './auth/Auth0ProviderWithNavigate';

createRoot(document.getElementById('root')!).render(
  <BrowserRouter>
    <Auth0ProviderWithNavigate>
      <App />
    </Auth0ProviderWithNavigate>
  </BrowserRouter>
);
```

`cacheLocation: 'memory'` is the safer default (tokens cleared on tab close). Use `'localstorage'` only when cross-tab persistence is a real requirement and you've reasoned about XSS exposure.

### Login / logout

```tsx
import { useAuth0 } from '@auth0/auth0-react';

export function AuthControls() {
  const { isAuthenticated, isLoading, loginWithRedirect, logout, user } = useAuth0();

  if (isLoading) return null;

  return isAuthenticated ? (
    <>
      <span>{user?.name}</span>
      <button onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}>Sign out</button>
    </>
  ) : (
    <button onClick={() => loginWithRedirect({ appState: { returnTo: window.location.pathname } })}>Sign in</button>
  );
}
```

`appState.returnTo` rides through the redirect and is restored by `onRedirectCallback` so the user lands back on the page they tried to visit.

### Protected routes

```tsx
import { withAuthenticationRequired } from '@auth0/auth0-react';

export const Protected = withAuthenticationRequired(Component, {
  onRedirecting: () => <LoadingScreen />,
});

// Or with react-router v6
<Route path="/dashboard" element={<Protected />} />
```

For per-permission gates (RBAC), read the access token's `permissions` claim and conditionally render. Don't try to gate at the route level using "do I have permission X" — the backend is the enforcer; the UI is a hint.

### Calling the API

```tsx
// src/api/useApi.ts
import { useAuth0 } from '@auth0/auth0-react';
import { useCallback } from 'react';

export function useApi() {
  const { getAccessTokenSilently } = useAuth0();

  return useCallback(async <T,>(input: RequestInfo, init: RequestInit = {}): Promise<T> => {
    const token = await getAccessTokenSilently();
    const res = await fetch(input, {
      ...init,
      headers: { ...init.headers, Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return res.json() as Promise<T>;
  }, [getAccessTokenSilently]);
}
```

Usage with TanStack Query:

```tsx
const api = useApi();
const { data: orders } = useQuery({
  queryKey: ['orders'],
  queryFn: () => api<Order[]>('/api/orders'),
});
```

`getAccessTokenSilently` handles refresh transparently; if refresh fails (revoked, expired beyond refresh), it throws and you redirect to `loginWithRedirect`.

### Reading custom claims & permissions

```tsx
const { user, getIdTokenClaims } = useAuth0();
const claims = await getIdTokenClaims();
const tenantId = claims?.['https://yourco.com/tenant_id'] as string | undefined;
```

The full namespaced URI is required; un-namespaced custom claims are dropped by Auth0.

### Organizations

```tsx
loginWithRedirect({
  authorizationParams: {
    organization: orgId,                          // ID, e.g. org_abc123
    invitation: invitationId,                     // for invitation-accept flow
    redirect_uri: window.location.origin + '/callback',
  },
});
```

For multi-org users, present a tenant picker and pass the chosen org_id to the next `loginWithRedirect`.

## Auth0 dashboard settings (matching this skill)

- **Allowed Callback URLs**: `http://localhost:5173/callback`, `https://app.yourco.com/callback`, ...
- **Allowed Logout URLs**: `http://localhost:5173`, `https://app.yourco.com`, ...
- **Allowed Web Origins**: same set (required for silent auth iframes)
- **Application Type**: Single Page Application
- **Grant Types**: Authorization Code + Refresh Token (enable both)
- **Refresh Token Rotation**: ON, with **Absolute Lifetime** + **Inactivity Lifetime** set
- **Refresh Token Reuse Detection**: ON
- API → **Add Permissions in the Access Token**: ON (for RBAC)

## Rules

- Authorization Code + PKCE only; never Implicit Flow
- Refresh tokens enabled with rotation + reuse detection — the SDK handles the rest
- `cacheLocation: 'memory'` by default; document the threat model if switching to `'localstorage'`
- Backend remains the enforcer for permissions — the SPA hides UI affordances but never relies on the client for authorization
- Access tokens are short-lived; let `getAccessTokenSilently` refresh — don't cache outside the SDK
- All Auth0-related env vars are public-prefixed (`VITE_*` / `NEXT_PUBLIC_*`) — never expose a client secret (SPAs don't have one)
- The redirect handler restores `appState.returnTo` so deep links work
- Logout calls `/v2/logout` via the SDK so the Auth0 SSO session is cleared, not just the local cache
- Custom claims read via full namespaced URI
- Errors from `getAccessTokenSilently` (e.g., `login_required`) trigger `loginWithRedirect` — don't swallow

## What NOT to do

- No client secret in the front-end bundle (SPAs don't have one)
- No storing access tokens in `localStorage` manually — the SDK manages storage; cross-tab persistence is a config setting
- No "is the user an admin" check that determines whether the dangerous action is executed in code path — the backend authorizes
- No bypassing `@auth0/auth0-react` to call `/oauth/token` directly from the SPA
- No long-lived access tokens (raise refresh lifetimes, not access token lifetimes)
- No reading the ID Token to send to the API (use the access token)
- No un-namespaced custom claims (`tenant_id` raw — Auth0 strips them)
- No `audience` left off `authorizationParams` — produces an opaque token your API can't validate
- No mixing tenants across environments (`yourco.com` for dev and prod) — separate Auth0 tenant per env

## Generation steps

1. Confirm tenant domain (per env), SPA client_id, API audience, callback URLs, organization model.
2. Register the URLs in the Auth0 SPA Application; enable refresh tokens + rotation + reuse detection.
3. Install `@auth0/auth0-react`; create `Auth0ProviderWithNavigate.tsx` and wrap `<App />`.
4. Add `AuthControls` (sign in / sign out) + `withAuthenticationRequired` for protected routes.
5. Create `useApi()` (or equivalent) that injects the access token into every outbound call.
6. Smoke flow: visit a protected route while signed out, get redirected to Auth0, sign in, land back on the page, make an authenticated API call, sign out, confirm the SSO session is cleared.

## Next.js App Router note

For Next.js with the App Router, prefer **`@auth0/nextjs-auth0`** for full coverage (server actions, route handlers, server components reading session). This skill's pattern still works inside `'use client'` boundaries, but the Next.js SDK better fits the framework's data-fetching model.

## Handoffs

- Concepts → `auth/_shared/auth0-concepts`
- Backend validation → `backend/dotnet/skills/auth0` or `backend/java/skills/auth0`
- Blazor → `auth/auth0-blazor`
- React patterns (custom hooks, providers) → `frontend/react/skills/generator`
- E2E with auth → `qa/ui-test-author/playwright` (use `storageState` for an authenticated session)
