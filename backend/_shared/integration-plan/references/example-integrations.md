# Golden example — `integrations.md`

The filled example for `be-shared-integration-plan`, from the **workshop-booking** toy initiative shared by all five planner examples. **Shapes and disciplines are normative; domain content is illustrative.** A real artifact writes a full block per dependency — this example writes SendGrid in full (the degraded-mode one, where the interesting policy lives) and abbreviates Auth0, saying so.

---

# Workshop Booking — Integration Plan

**Date:** 2026-08-02 · **Written by:** `be-shared-integration-plan`
**Blueprint:** `./blueprint.md` · **API surface:** `./api-surface.md`

## 1. Dependency register

| # | System | What it does for us | Direction | Protocol | Criticality | Account owner | Status |
|---|---|---|---|---|---|---|---|
| X1 | Auth0 | Identity, token issuance, JWKS, roles | inbound (token validation) | OIDC | **critical** — nobody signs in without it | Studio owner | tenant `[TBD - owner, week 1]` |
| X2 | SendGrid | Booking confirmation + cancellation emails | outbound | REST | **degraded** — email is queued and retried; a booking never fails because email did | Studio owner | account `[TBD - owner, week 1]` |

## 2. Dependencies

### X2 — SendGrid (email)

**Purpose:** transactional email only — booking confirmed, booking cancelled (member- and staff-initiated).
**Direction:** outbound REST · **Criticality:** degraded
**Docs:** SendGrid v3 mail send · **API version pinned to:** v3

**Auth**
| Aspect | Value |
|---|---|
| Method | API key, `Authorization: Bearer` |
| Rotation | On demand; single key |

**Configuration** *(names and locations only — never values)*
| Key | Where it lives | Environments | Provisioned by |
|---|---|---|---|
| `Email__ApiKey` | user-secrets (local) / Container Apps secret (staging, prod) | distinct per env | Owner → devops-engineer |
| `Email__FromAddress` | appsettings (non-secret) | all | — |

**Environments**
| Env | Provider environment | Notes |
|---|---|---|
| local | **Mailpit sink — no SendGrid at all** | a developer runs the system with nothing provisioned |
| staging | SendGrid sandbox mode | accepted-but-not-delivered; **cannot email real members by construction** |
| prod | SendGrid live, domain-authenticated | SPF/DKIM/DMARC — prerequisite task T0.2; skipping this ships email to spam |

**Limits & budget:** free tier 100/day vs expected peak ~60/day — fine for v1, alert at 80 `⚠️ Assumption: v1 volume holds`.

**Resilience**
| Aspect | Policy |
|---|---|
| Sending | **Asynchronous, always** — the booking commits first, the email is a background send |
| Retry | 3 attempts, exponential backoff, only on 5xx/timeout/429; a 4xx is logged and dropped |
| Fallback | None needed — the booking stands; the member still sees it in "my bookings" |

**Bounce & complaint handling:** log-and-review in v1; no inbound webhook `#confirmed` (owner accepts manual review at this volume).

**Data crossing the boundary:** member name, member email, session title + time. Nothing else.

**Local dev & test**
| Layer | Approach |
|---|---|
| Local run | Mailpit |
| Unit / component | Fake at our own `IEmailSender` seam — never assert on SendGrid's wire format |
| Integration | `qa-email-testing-dotnet` against Mailpit |

**Open questions:** none.

### X1 — Auth0 — abbreviated in this example
A real artifact writes the full block. Notable rows: Authorization Code + PKCE (SPAs) / JWT bearer validation (API) via `be-dotnet-auth0`; JWKS cached with rotation tolerance; claim mapping `permissions[]` → the two permissions in `api-surface.md` §4; **IdP-down behavior:** already-issued tokens keep working until `exp` — new sign-ins fail with the SPA's own outage message; config keys `Auth0__Domain`, `Auth0__Audience` (non-secret, appsettings).

## 3. Secrets checklist

| Secret | Store | Environments | Provisioned by | Needed by task | Rotation | Status |
|---|---|---|---|---|---|---|
| `Email__ApiKey` | Container Apps secrets | staging, prod (distinct) | Owner → devops | T13 (email sender) | on demand | `[TBD - owner, wk 1]` |
| Auth0 tenant + application config | Auth0 dashboard | one tenant, per-env applications | Owner | T5 (auth wiring) | n/a | `[TBD - owner, wk 1]` |

## 4. Failure matrix

| System | If it is slow | If it is down | If it returns garbage | User-visible effect |
|---|---|---|---|---|
| Auth0 | Token validation is local (JWKS cached) — unaffected | Existing sessions work until token expiry; new sign-ins fail | Signature/claims fail closed → 401 | Sign-in unavailable; booked members unaffected |
| SendGrid | Background send waits; booking already committed | Queue drains on recovery | Log, drop after retries | Email arrives late or not at all; booking always stands |

## 5. Blocking unknowns

| # | Unknown | Owner | Needed by | Blocks tasks |
|---|---|---|---|---|
| U1 | Auth0 tenant + per-env applications created | Owner | week 1 | T5, and every task after it that needs sign-in |
| U2 | SendGrid account + domain authentication | Owner | before prod cutover | T13 in prod only — local/staging proceed via Mailpit/sandbox |

Each is also a register `[TBD]` and a P0 prerequisite task (T0.1, T0.2) in `delivery-plan.md` — the three-places rule.

## 6. Local development

A developer clones, runs `docker compose up` (PostgreSQL + Mailpit), and signs in against the shared Auth0 **dev** application. Nothing secret is required beyond the dev-app client id (non-secret, committed). Honest answer: day-one runnable except sign-in before U1 lands — mitigated by a documented test-token fallback in week 1 only.

## 7. Routed to `devops-engineer`

| Need | Why |
|---|---|
| Container Apps secret store + per-env config wiring | Owns stores and wiring; this plan only names keys |
| SendGrid domain-auth DNS records | DNS is infrastructure |
