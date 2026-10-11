---
name: auth0-concepts
description: Use when explaining Auth0-specific concepts before picking a stack recipe — tenants, applications, APIs, the `audience` parameter, RBAC, organizations, namespaced custom claims, Actions, connections. The Auth0 layer on top of `oidc-concepts`. Triggers: "what's an Auth0 API vs application", "why is my Auth0 token opaque", "RBAC with Auth0". Do NOT use for generic OAuth/OIDC theory (`oidc-concepts`), Cognito (`cognito-*`), or stack implementation (the stack's auth0 skill).
---

# Auth0 — Concepts (Shared)

Conceptual reference for **Auth0** used across every stack in this library. This is the **Auth0-specific layer** — the provider-agnostic protocol (roles, Authorization Code + PKCE, Client Credentials, ID/access/refresh tokens, JWT validation, rotation, public vs confidential clients, scopes/RBAC/ABAC) lives in [`auth/_shared/oidc-concepts`](../oidc-concepts/SKILL.md); **read that first**. Here: the Auth0 entity model (Tenant / Application / API / Connection / Action), the `audience` behavior, RBAC / organizations / namespaced custom claims, and connections. The stack skills (`auth/auth0-{dotnet,java,react,blazor}`) implement these.

## When to use

- Picking the right Auth0 entities for a new system (one API or many; one app or per-environment; per-tenant or multi-tenant)
- Deciding which OAuth/OIDC flow fits a use case
- Understanding what a stack-specific skill is configuring under the hood
- Designing RBAC, organizations, or custom claim strategy before implementation
- Debugging a token validation failure conceptually before reaching for code

## When NOT to use

- Wiring code in a specific stack → `backend/dotnet/skills/auth0` / `backend/java/skills/auth0` / `auth/auth0-react` / `auth/auth0-blazor`
- Generic OAuth/OIDC theory (flows, tokens, JWT validation) shared across providers → [`auth/_shared/oidc-concepts`](../oidc-concepts/SKILL.md)
- AWS Cognito → the `cognito-*` skills

## Mental model — the core entities

| Entity | What it represents | Created in Auth0 as |
|---|---|---|
| **Tenant** | A single Auth0 environment (`yourco-dev.eu.auth0.com`) | A separate Auth0 tenant per environment (dev / staging / prod) |
| **Application** | A *client* that requests tokens (your SPA, mobile app, M2M client) | One Application per client. Type matters: SPA, Regular Web, Native, M2M. |
| **API** (resource server) | The audience tokens are *for* (your backend) | One API per logical backend, with an **identifier** that becomes the JWT `aud` |
| **Connection** | An identity source (Username-Password DB, Google, Microsoft, LDAP, SAML, custom OIDC) | Enabled per Application — you decide which directories an app can authenticate against |
| **Action** | Inline JS that runs at well-defined extensibility points (post-login, pre-user-registration, etc.) | Used to add custom claims, enforce MFA conditionally, sync to your DB |
| **Role / Permission** | RBAC primitives Auth0 manages for you | Permissions are scoped to an API; roles bundle permissions; assigned to users or via Actions |
| **Organization** | A grouping of users + roles + connections, multi-tenant primitive | Optional but the right model when your app is B2B |

**One API per backend, one Application per client.** A `SpaApp` (SPA) and a `MobileApp` (Native) both authenticate against the same `OrdersAPI` (API) — the API is *what* you protect; the Application is *who is asking*.

## Flows, tokens & JWT validation → `oidc-concepts`, with these Auth0 specifics

The flow mechanics (Authorization Code + PKCE, Client Credentials), the ID/access/refresh token model, and the JWT-validation checklist are provider-agnostic — see [`auth/_shared/oidc-concepts`](../oidc-concepts/SKILL.md). What is **Auth0-specific**:

- **`audience` is mandatory on `/authorize` and `/oauth/token`.** Without it Auth0 issues an **opaque** access token usable only against `/userinfo` — your API can't validate it. The `audience` is the **API identifier** (`https://api.yourco.com`), *not* the application's `client_id`. (This is the single biggest Auth0 gotcha; Cognito has no `audience` and always issues a JWT — see the comparison in `oidc-concepts`.)
- **Access tokens are RS256 JWTs** when the API uses the JWT profile; the API validates `iss == https://<tenant>/` and `aud` contains the API identifier. JWKS is at `https://<tenant>/.well-known/jwks.json`.
- **Refresh tokens** require the `offline_access` scope; enable **rotation + reuse detection** at the application level (Auth0 kills the whole token family on replay).
- **Authorization claim** is the **`permissions`** array when "Add Permissions in the Access Token" is enabled on the API (see RBAC below), or the standard `scope` claim.
- **M2M** uses an Auth0 **M2M Application** per consumer; the Client Credentials call still needs `audience` (the target API identifier).

## RBAC, organizations, and custom claims

### RBAC (the default for B2C and simple B2B)

- Define **Permissions** on the API (`orders:read`, `orders:write`)
- Define **Roles** that bundle permissions (`Customer`, `Admin`, `Support`)
- Assign roles to users (directly, or via an Action based on email domain / metadata)
- Enable **"Add Permissions in the Access Token"** on the API settings — `permissions: ["orders:read", ...]` lands in the JWT for the backend to enforce

### Organizations (the default for B2B)

- Each customer is an `Organization` in Auth0
- Users are members of one or more orgs
- Membership carries org-specific roles
- The API receives the `org_id` claim in the access token and uses it for tenant scoping
- Use orgs when you need: invitations, org-specific branding, org-specific connections (e.g., this org uses Azure AD SSO)

### Custom claims

Auth0 namespaces all custom claims to avoid collisions with standard claims. Add via a post-login Action:

```javascript
exports.onExecutePostLogin = async (event, api) => {
  const ns = 'https://yourco.com/';
  api.idToken.setCustomClaim(`${ns}tenant_id`, event.user.app_metadata?.tenant_id);
  api.accessToken.setCustomClaim(`${ns}tenant_id`, event.user.app_metadata?.tenant_id);
};
```

Always namespace (`https://yourco.com/tenant_id`) — un-namespaced custom claims are silently dropped by Auth0 for security.

## Tenants — one per environment

- `yourco-dev.<region>.auth0.com` for development
- `yourco-stg.<region>.auth0.com` for staging
- `yourco.<region>.auth0.com` for production

Different tenants because the configuration (callbacks, connections, branding, secrets) is environment-specific and you don't want a dev mistake to affect prod. **Deploy.io** / **Auth0 Deploy CLI** moves configuration between tenants via Git.

## Connections

- **Database connection** — Auth0 hosts the user store (default: `Username-Password-Authentication`). Enables passwordless, MFA, password policy.
- **Social** — Google, Microsoft, Apple, GitHub. Each requires a developer app on the provider side; Auth0 wraps it.
- **Enterprise** — SAML, WS-Federation, OIDC, AD/LDAP, Azure AD (Entra ID), Google Workspace. The standard B2B story.
- **Passwordless** — Email / SMS one-time codes; magic links

Enable per-application: an internal admin app might allow only Azure AD; a public-facing app allows Google + Username/Password.

## Secrets, callbacks, CORS

- **Allowed Callback URLs** — every URL your app might be redirected back to. Per-environment, comma-separated.
- **Allowed Logout URLs** — where `/v2/logout` can return to
- **Allowed Web Origins** — for SPAs using silent auth (`iframe`-based session check)
- **Allowed Origins (CORS)** — for the `/oauth/token` endpoint (SPA flow)
- **Client Secret** — only present on Regular Web Apps and M2M; **never** on SPAs / Native (PKCE replaces it)

Store client secrets in your secret store (Azure Key Vault / AWS Secrets Manager) — never in source.

## Common pitfalls (Auth0-specific)

Generic pitfalls (ID token to the API, long-lived access tokens, Implicit Flow) are in [`oidc-concepts`](../oidc-concepts/SKILL.md). Auth0-specific:

- **Mixing the API audience with the application client_id.** `audience` on `/authorize` must be the API identifier (`https://api.yourco.com`), not the SPA's client id.
- **Forgetting `audience` on `/authorize`.** Auth0 issues an opaque access token usable only for `/userinfo`; your API can't validate it.
- **Skipping the namespace on custom claims.** Auth0 drops un-namespaced custom claims silently.
- **Sharing a tenant across environments.** Inevitable cross-env breakage — one tenant per env.

## Sizing the setup

| You need | Set up |
|---|---|
| Public SPA + backend API | 1 SPA Application + 1 API (per env tenant) |
| SPA + Mobile + same backend | 1 SPA + 1 Native + 1 API (per env tenant) |
| M2M call from service A to service B | 1 M2M Application (A) + grant on service B's API |
| Per-customer B2B | Organizations on top of the SPA + API |
| White-labelled / branded per customer | Organizations with org-specific branding + connections |

## Handoffs

- Provider-agnostic OAuth/OIDC model (flows, tokens, JWT validation, Auth0-vs-Cognito) → [`auth/_shared/oidc-concepts`](../oidc-concepts/SKILL.md)
- .NET / ASP.NET Core API or web → `backend/dotnet/skills/auth0`
- React SPA → `auth/auth0-react`
- Java / Spring Boot backend → `backend/java/skills/auth0`
- Blazor Server / WASM → `auth/auth0-blazor`
- Storing / rotating client secrets → `devops/environment-config` + Key Vault / Secrets Manager
- Roles + permissions in tests → use seeded users in the test tenant; document in `qa/manual/test-strategy`
