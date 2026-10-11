---
name: oidc-concepts
description: Use when explaining OAuth 2.0 / OpenID Connect concepts that are the same across providers — roles, Authorization Code + PKCE, Client Credentials, ID vs access vs refresh tokens, JWT validation, rotation, scopes vs RBAC — plus the Auth0-vs-Cognito comparison that picks the provider skill. Triggers: "explain Authorization Code + PKCE", "ID token vs access token", "Auth0 vs Cognito differences". Do NOT use for provider-specific setup (`auth/auth0-*` / `auth/cognito-*`).
---

# Auth — OAuth 2.0 / OpenID Connect Concepts (Shared)

The **provider-agnostic** mental model every auth skill in this library builds on. OAuth 2.0 (authorization) + OpenID Connect (authentication on top of it) work the same way whoever issues the tokens — the differences between providers are configuration and a handful of claim/endpoint quirks, captured in the comparison table below. Provider-specific layers: [`auth/_shared/auth0-concepts`](../auth0-concepts/SKILL.md) (Auth0) and the `cognito-*` skills (AWS Cognito) inline.

## When to use

- Deciding which OAuth/OIDC **flow** fits a use case
- Understanding what a provider/stack skill is configuring under the hood
- Debugging a token-validation failure conceptually before reaching for code
- Choosing between Auth0 and Cognito, or reading a token from either

## When NOT to use

- Provider-specific entities, dashboard, custom claims → [`auth/_shared/auth0-concepts`](../auth0-concepts/SKILL.md) (Auth0) · the `cognito-*` skills (Cognito)
- Wiring code in a stack → `auth/{auth0,cognito}-{dotnet,java,react,blazor}`

## The four roles

| Role | Who | In our systems |
|---|---|---|
| **Resource Owner** | the end user | the human signing in |
| **Client** | the app requesting access | your SPA, mobile app, Blazor app, or an M2M service |
| **Authorization Server** | issues tokens | Auth0 tenant / Cognito user pool |
| **Resource Server** | consumes access tokens | your backend API |

**One resource server per backend, one client per app.** A SPA and a mobile app are two clients hitting the same API.

## Flows we use

Per `CLAUDE.md`: **Authorization Code + PKCE** for SPAs / native / server-rendered web, **Client Credentials** for service-to-service. Never Implicit, ROPC, or Hybrid.

### Authorization Code + PKCE

1. Client generates a `code_verifier` (random) + `code_challenge` (SHA-256 of it).
2. Redirect to `/authorize` with `response_type=code`, `code_challenge`, `code_challenge_method=S256`, `scope=openid profile email <api-scopes>` (+ provider-specific API targeting — see the table).
3. User authenticates; the authorization server redirects back with a `code`.
4. Client POSTs the `code` + `code_verifier` to the token endpoint.
5. Returns `access_token` (for the API), `id_token` (about the user, for the client), and usually a `refresh_token`.

**PKCE replaces the client secret** for public clients (browser / mobile / desktop) that can't keep one secret.

### Client Credentials (M2M)

Service POSTs `grant_type=client_credentials` + client id/secret (+ provider-specific API targeting) → a short-lived `access_token` with **no user context and no refresh token**. Each consumer service gets its own machine client — never share credentials.

### Refresh tokens & rotation

Authorization-Code clients get a refresh token to obtain new access tokens without re-prompting. Enable **rotation + reuse detection**: the server invalidates the whole token family if a previously-used refresh token is replayed (theft signal). Access tokens stay short (5–60 min); the refresh token carries continuity.

## Client types

| Type | Secret? | Auth to token endpoint | Examples |
|---|---|---|---|
| **Public** | no | PKCE only | SPA, mobile, desktop, Blazor WASM |
| **Confidential** | yes | client secret (Basic/POST) + PKCE | server-rendered web, Blazor Server, M2M |

A secret in a browser bundle is not a secret. Public clients use PKCE; confidential clients (with a server to hold the secret) add the secret.

## Tokens — what they're for

| Token | For | Format | Lifetime | Rule |
|---|---|---|---|---|
| **ID token** | the **client**, to know who the user is | JWT | short | never send it to an API |
| **Access token** | the **API**, to authorize the request | JWT (RS256) | short | the only token the API trusts |
| **Refresh token** | the client, to get a new access token | opaque | long, rotated | store server-side / in the SDK cache; revocable |

`token_use` (or an equivalent) distinguishes an ID token from an access token on providers that issue both as JWTs from the same issuer — the API must reject a token whose `token_use` isn't the access type (a common replay bug). **The two most common OAuth bugs:** calling the API with the ID token, and parsing the access token in the client for profile data (use the ID token / `/userinfo`).

## JWT validation — what every backend enforces

1. **Signature** — fetch JWKS from the issuer's `/.well-known/jwks.json`, cache, rotate. Never hand-build the JWKS URL — discover it from the issuer.
2. **Algorithm** — RS256 only; reject `alg: none` and HS256 (RFC 8725).
3. **Issuer** — `iss` equals the exact issuer URL.
4. **Recipient** — validate `aud` where the provider sets it; **where it doesn't (Cognito access tokens have no `aud`), validate `token_use == "access"` + an allow-list of `client_id`** instead.
5. **Timestamps** — `exp` in the future, `nbf`/`iat` sane within a small clock skew (cap at ~30s, not the 5-minute default).
6. **Authorization** — the endpoint's required **scope** (`scope`/`scp` claim) or **permission/group** (RBAC) is present.

The stack skills wire this into middleware (ASP.NET Core `AddJwtBearer`, Spring Security resource server, `express-oauth2-jwt-bearer`, Blazor auth).

## Authorization models

- **Scopes** — what the *client* was granted (`orders.read`); coarse, consented at login. An API/resource-server scope authorizes an operation.
- **RBAC** — roles bundle permissions/groups assigned to *users*; the token carries a permissions/groups claim the API enforces.
- **ABAC** — attribute-based (tenant id, region, ownership) evaluated at request time for row/field-level rules scopes can't express.

Enforce authorization at the **API** (the resource server is the source of truth); the UI only hides affordances.

## Provider comparison — Auth0 vs AWS Cognito

The axes where the same OIDC concept is wired differently (pick the provider skill accordingly):

| Axis | Auth0 | AWS Cognito |
|---|---|---|
| Issuer | `https://{tenant}/` | `https://cognito-idp.{region}.amazonaws.com/{userPoolId}` |
| Authorize/token/logout host | same as issuer | separate **hosted-UI domain** (`{domain}.auth.{region}.amazoncognito.com`) |
| API targeting | **`audience`** param → API-scoped access token (opaque **without** it) | **resource-server custom scopes** (`https://api/…`); access token is **always a JWT**; **no `audience`** |
| `aud` on access token | your API identifier | **absent** → validate `token_use=access` + `client_id` |
| Refresh | request `offline_access` | returned automatically per app-client config (**no `offline_access`**) |
| Roles claim | namespaced custom claim | **`cognito:groups`** |
| Logout | `/v2/logout?client_id=&returnTo=` | `/logout?client_id=&logout_uri=` (**no `end_session_endpoint`** in metadata — build by hand) |
| Custom claims | must be **namespaced** (`https://yourco.com/…`) | pre-token-generation Lambda; `custom:` attribute prefix |
| Revocation | `/oauth/revoke` + Management API | `/oauth2/revoke` + `AdminUserGlobalSignOut` |

## Common pitfalls (provider-agnostic)

- Calling the API with the **ID token** (use the access token).
- Parsing the **access token in the client** for profile info (use the ID token / `/userinfo`).
- **Long-lived access tokens** — keep them short; rely on refresh/silent auth.
- **Implicit Flow** anywhere — deprecated; Authorization Code + PKCE only.
- **Client secret in a public client** — PKCE replaces it.
- **Sharing one authorization-server environment across dev/prod** — separate tenant/user-pool per environment.
- **Trusting the client for authorization** — the API enforces.

## Handoffs

- Auth0 specifics (entities, `audience`, namespaced claims, Organizations, connections) → [`auth/_shared/auth0-concepts`](../auth0-concepts/SKILL.md)
- Cognito specifics → the `cognito-*` skills (deltas encoded inline)
- Stack code → `auth/{auth0,cognito}-{dotnet,java,react,blazor}`
- Storing secrets → `devops/environment-config` + Key Vault / AWS Secrets Manager
