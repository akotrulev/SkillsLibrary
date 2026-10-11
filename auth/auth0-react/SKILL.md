---
name: auth0
description: Use when setting up or modifying Auth0 in a React 19/18 + TypeScript app — two lanes: `@auth0/nextjs-auth0` for the Next.js App Router (middleware, server-side session in RSC/Actions/handlers) and `@auth0/auth0-react` for a Vite/CRA SPA (Auth Code + PKCE, protected routes). Triggers "add Auth0 login", "protect a route", "read the session in a Server Component", "attach the access token to fetch". Not for backend token validation or provider concepts (`auth0-concepts`).
---

# Auth — Auth0 in React

Wires Auth0 into a React 19/18 + TypeScript app. **Pick the lane by render target — this is the first decision, and it is not a preference:**

| Render target | SDK | Where the session lives |
|---|---|---|
| **Next.js App Router** (primary) | **`@auth0/nextjs-auth0`** | Encrypted **HTTP-only cookie**, read on the server |
| **Vite / CRA SPA** (fallback) | **`@auth0/auth0-react`** | In-memory in the browser, refresh-token rotation |

The App Router lane is **not** the SPA lane with extra steps. A Server Component cannot call a React hook, so `useAuth0()` is unreachable from the majority of an App Router app — using the SPA SDK there forces `'use client'` across your whole tree and gives up server-side session checks. Read [The Next.js App Router lane](#the-nextjs-app-router-lane) for that path; the sections after it are the SPA pattern.

## Stack (SPA lane)

- **React 19/18 + TypeScript (strict)**
- **`@auth0/auth0-react`** (the official SPA SDK)
- Authorization Code + PKCE (no client secret in the browser)
- Refresh token rotation enabled in the Auth0 SPA Application
- **Next.js App Router → use the `@auth0/nextjs-auth0` lane below instead**

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
- Cognito instead of Auth0 → `auth/cognito-react`

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

`getAccessTokenSilently` handles refresh transparently; if refresh fails (revoked, expired beyond refresh), it throws.

**What happens next is a UX decision, and redirecting straight to `loginWithRedirect` is the wrong default** — it unmounts the app and destroys any unsaved work on screen. The recovery ladder (single-flight refresh → replay the original request once → **re-authenticate in place** via a modal/`loginWithPopup` → redirect only from a surface with nothing to lose, and only with `returnTo` the exact route) is owned by `frontend/react/skills/error-handling`. This skill owns the token mechanics; that one owns what the user sees. Note also that a **403 must not run this ladder** — it is a permission outcome, not an expired session.

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

## The Next.js App Router lane

`@auth0/nextjs-auth0` v4. The session is an **encrypted HTTP-only cookie** the server reads — so a Server Component, a Server Action, a route handler, and middleware can all check auth without shipping a token to the browser.

### 1. Environment

```bash
# .env.local — NONE of these are NEXT_PUBLIC_; they must stay server-side
AUTH0_SECRET=            # openssl rand -hex 32 — encrypts the session cookie
APP_BASE_URL=http://localhost:3000
AUTH0_DOMAIN=your-tenant.eu.auth0.com
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=     # this is a REGULAR WEB APPLICATION in Auth0, not a SPA
AUTH0_AUDIENCE=          # your API identifier, if you call a protected API
```

The Auth0 application type is **Regular Web Application** here, not SPA — the code exchange happens server-side with a client secret. Callback URL `http://localhost:3000/auth/callback`, logout URL `http://localhost:3000`. Per the global rules: secrets come from the environment + a secret store, never from committed files.

### 2. The client + middleware

```ts
// src/lib/auth0.ts
import { Auth0Client } from '@auth0/nextjs-auth0/server';

export const auth0 = new Auth0Client({
  authorizationParameters: {
    scope: 'openid profile email',
    audience: process.env.AUTH0_AUDIENCE,   // required to get an API access token
  },
});
```

```ts
// middleware.ts  (project root)
import type { NextRequest } from 'next/server';
import { auth0 } from './src/lib/auth0';

export async function middleware(request: NextRequest) {
  return await auth0.middleware(request);   // mounts /auth/login, /auth/logout, /auth/callback
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
```

The middleware mounts the auth routes **and** rolls the session cookie — it is required, not optional. See [`fe-react:routing`](../../frontend/react/skills/routing/SKILL.md) for the `matcher` rules.

### 3. Reading the session

```tsx
// A Server Component — no hook, no 'use client'
import { auth0 } from '@/lib/auth0';

export default async function Page() {
  const session = await auth0.getSession();
  if (!session) return <a href="/auth/login">Sign in</a>;
  return <p>Hello {session.user.name}</p>;
}
```

```tsx
// A Client Component that needs the user
'use client';
import { useUser } from '@auth0/nextjs-auth0';

export function UserMenu() {
  const { user, isLoading } = useUser();
  if (isLoading) return <Spinner />;
  return user ? <SignOut /> : <a href="/auth/login">Sign in</a>;
}
```

Wrap the app in `<Auth0Provider>` (from `@auth0/nextjs-auth0`) in the root layout only if you use `useUser()`. **Login and logout are plain anchors to `/auth/login` and `/auth/logout`** — real navigations to server routes, not `router.push`.

### 4. Protecting a route

```tsx
// Gate where the data is returned — middleware alone is not authorization
import { redirect } from 'next/navigation';
import { auth0 } from '@/lib/auth0';

export default async function AdminPage() {
  const session = await auth0.getSession();
  if (!session) redirect('/auth/login');
  if (!session.user['https://acme.com/roles']?.includes('admin')) redirect('/403');
  return <Admin />;
}
```

Namespaced custom claims (`https://acme.com/roles`) come from an Auth0 Action — see `auth/_shared/auth0-concepts`.

### 5. Calling a protected API

```ts
// Server-side: get the access token and forward it
import { auth0 } from '@/lib/auth0';

export async function getOrders() {
  const { token } = await auth0.getAccessToken();
  const res = await fetch(`${process.env.API_URL}/orders`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Orders failed: ${res.status}`);
  return res.json();
}
```

Fetch on the **server** and pass serializable data down as props. Sending the access token to the browser so a Client Component can call the API defeats the point of the cookie-based session.

### App Router anti-patterns

| Anti-pattern | Why it's wrong | Do instead |
|---|---|---|
| `@auth0/auth0-react` in an App Router app | Hooks can't run in Server Components; forces `'use client'` everywhere | `@auth0/nextjs-auth0` |
| `NEXT_PUBLIC_AUTH0_CLIENT_SECRET` | Ships the secret to every browser | Server-only env vars |
| Middleware as the only auth check | Coarse and bypassable — it sees a cookie, not your rules | Re-check in the RSC / Action / handler that returns data |
| `router.push('/auth/login')` | Client-side push to a server route | A real `<a href="/auth/login">` |
| Access token handed to the client | Cookie-session model exists to avoid that | Fetch server-side, pass data as props |
| Skipping `audience` | You get an opaque token, not a JWT your API can validate | Set `audience` in `authorizationParameters` |

## Handoffs

- Concepts → `auth/_shared/auth0-concepts`
- Backend validation → `backend/dotnet/skills/auth0` or `backend/java/skills/auth0`
- Blazor → `auth/auth0-blazor`
- Route topology + middleware mechanics → `frontend/react/skills/routing`
- React patterns (custom hooks, providers) → `frontend/react/skills/component-writer`
- E2E with auth → `qa/typescript/skills/ui-test-author/playwright` (use `storageState` for an authenticated session)
