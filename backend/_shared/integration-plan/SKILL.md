---
name: be-shared-integration-plan
description: Use when a planned backend needs its external dependencies specified — every system it calls, with auth, config keys (never values), limits, retry/circuit-breaker policy, and local-dev/test strategy. Triggers "what external services do we depend on", "what API keys do we need", "how do we handle it when the provider is down". Do NOT use to provision secret stores (`devops-engineer`), write client code (`be-<stack>`), or plan this service's own endpoints (`be-shared-api-surface-plan`).
---

# Integration Plan — the external dependency register

Everything the service does not control. The section of a plan most often written as a one-liner ("we'll use SendGrid for email") and most often the reason a build stalls — because nobody asked who has the account, which environment the key is for, what happens when it 429s, and whether a developer can run the system without it.

Two failure modes this document exists to prevent:

1. **The blocking unknown discovered late** — an API key that needs a procurement request, a sandbox that takes two weeks to provision, a partner contract that has not been signed. These are cheap to surface at plan time and expensive at task time.
2. **The undefined failure mode** — nobody decided what the system does when the provider is down, so it does whatever the HTTP client's default happens to be.

**Announce at start:** "I'm using the `be-shared-integration-plan` skill to plan the external dependencies."

**Prerequisites:** an approved `blueprint.md` (its External systems section is the seed list) and `api-surface.md` (endpoints that call out, and the outbound webhooks it emits).

## When to use

- Step 5 of a `be-planner` run
- A new external system is being added to an existing planned build (`EXTEND`)
- An existing integration needs documenting before it is changed (`RESUME` — read the client code and config, mark `#confirmed`, then plan the delta)

## When NOT to use

- The ask is to provision the secret store, the network path, or the environments → `devops-engineer` (this plan *tells* it what is needed)
- The ask is to write the client, the retry policy code, or the webhook handler → `be-<stack>`
- The dependency is this system's own database or cache → that is `data-model.md` and the blueprint's tech stack, not an integration

## Output

**`docs/plans/<NNN>-<initiative>/integrations.md`** in the initiative folder.

**A filled golden example is at `references/example-integrations.md`** (the shared `001-workshop-booking` pack — shapes normative, domain content illustrative).

---

## Procedure

### Step 1 — The register

Every external system on one screen. Seeded from the blueprint, then completed by walking `api-surface.md` for outbound calls and inbound triggers:

| # | System | What it does for us | Direction | Protocol | Criticality | Account owner | Status |
|---|---|---|---|---|---|---|---|
| X1 | SendGrid | Transactional email (verification, receipts) | outbound | REST | **degraded** — queue and retry, never block the request | Platform team | account exists `#confirmed` |
| X2 | Stripe | Card payments + refunds | both | REST + inbound webhook | **critical** — checkout fails without it | Finance | sandbox `[TBD - Finance, wk 2]` |
| X3 | Auth0 | Identity, token issuance, JWKS | inbound (token validation) | OIDC | **critical** | Platform team | tenant exists `#confirmed` |

**Criticality has exactly three values**, and each is a design commitment, not a label:

| Value | Means | The plan must then say |
|---|---|---|
| **critical** | The feature cannot function without it | What the user sees when it is down (503 + `Retry-After`, per the validation catalog) |
| **degraded** | The feature works, something is deferred or reduced | *Which* behavior degrades, and how the deferred work completes later |
| **optional** | Nice to have; absence is invisible to the user | Confirm it is genuinely invisible — analytics that block a request are not optional |

**Direction** drives everything downstream: `outbound` needs credentials, timeouts, and retries; `inbound` needs signature verification, replay protection, and idempotency; `both` needs all of it.

### Step 2 — A block per dependency

One block per register row, with these fields — the worked content lives in `references/example-integrations.md`; do not restate it here:

````markdown
### X<n> — <System> (<what it is>)

**Purpose:** <one sentence — what it does for us>
**Direction:** <outbound | inbound | both> · **Criticality:** <critical | degraded | optional>
**Docs:** <link> · **API version pinned to:** <version>

**Auth** — method, rotation policy, and (if inbound) how we verify the caller
**Configuration** — key **names** and store **locations** only, per environment, with who provisions each
**Environments** — which provider environment each of local / staging / prod talks to
**Limits & budget:** <provider limit> · <our expected peak> · <connect/read timeouts>
**Resilience** — retry policy, idempotency, circuit breaker, and the stated fallback
**Inbound webhook** *(if any)* — endpoint, replay protection, idempotency, ordering, failure handling
**Data crossing the boundary:** <fields, PII called out>
**Local dev & test** — local run, unit/component, integration, contract layers
**Open questions:** <or "none">
````

Rules the block must honor, whatever the system:

- **Retry only on 5xx / timeout / 429 — never on a 4xx.** A 4xx retried is the same wrong request sent twice.
- **Outbound idempotency keys are our own ids** (an order id, not a random UUID per attempt), so a retry cannot double-apply.
- **A webhook endpoint is anonymous but signature-verified** — state it as an explicit exception to the API-wide 401 rule, and verify over the **raw** body before parsing.
- **A fallback of "none" is stated, not omitted** — say what the user sees (e.g. 503 + `Retry-After`) and what state the affected record stays in.
- **Fakes live at our own client interface, never the vendor's wire format**; the pinned API version means a version bump is its own task with its own test pass.

### Step 3 — Category-specific rules

The blocks above are the shape; these are the things each category needs that are easy to omit:

| Category | Must state |
|---|---|
| **Email / SMS / push** | Sender identity + domain auth (SPF/DKIM/DMARC — a plan that skips this ships email into spam folders) · template ownership (in-provider vs in-repo) · **bounce and complaint handling** · a per-environment guard so staging cannot email real customers (allowlist or sandbox mode — state which) · unsubscribe/consent obligations · whether sending is synchronous (it should not be) |
| **Payments** | Tokenization boundary and the resulting PCI scope · currency and rounding, matching `data-model.md` · refunds/chargebacks as first-class flows, not afterthoughts · **reconciliation** — which system is the source of truth when they disagree, and how the mismatch is detected |
| **Identity provider** | Flows in use (Authorization Code + PKCE for SPAs, Client Credentials for M2M) · JWKS caching + rotation · claim mapping (permissions, tenant, roles) · what happens on IdP outage for already-issued tokens · handshake to `auth/_shared/{auth0-concepts,oidc-concepts}` |
| **Object storage** | Bucket/container per environment · access model (pre-signed URLs vs proxying — pick one, say why) · size and content-type limits, validated server-side · lifecycle/retention · public-vs-private default |
| **Message broker** | Topic/queue naming · delivery semantics (at-least-once by default → consumers are idempotent) · ordering guarantees actually required · **dead-letter queue and who watches it** · schema evolution rules · consumer-group/competing-consumer shape |
| **Search index** | Source of truth stays the DB · indexing trigger (sync/async/batch) and acceptable staleness · reindex procedure · what the API returns when the index is behind or down |
| **Partner / internal APIs** | Contract source (OpenAPI file? none?) · versioning and deprecation notice · a named human contact · SLA · sandbox availability — **the single most common blocking unknown** |
| **Inbound webhooks (any provider)** | Signature verification over the **raw** body before parsing · replay window · idempotency on the provider's event id · fast ack then async processing · what happens when the payload shape changes |

### Step 4 — The consolidated secrets checklist

Every credential, in one table, because this is what someone has to action:

| Secret | Store | Environments | Provisioned by | Needed by task | Rotation | Status |
|---|---|---|---|---|---|---|

Hard rules:

- **No values.** Not in the plan, not in a repo file, not in a code comment, not "temporarily". The plan carries the key **name** and its **location**.
- **Distinct per environment.** One key shared across staging and prod is a finding, stated as one.
- **"Needed by task" ties to `delivery-plan.md`** — that is what turns "we need a key" into work that gets scheduled.
- **`devops-engineer` owns the store and the wiring**; this table is its input.

### Step 5 — Blocking unknowns

Anything a human must obtain — an account, a sandbox, a contract, a key, a partner contact, a compliance sign-off — is **three things at once**:

1. A row in the register with status `[TBD - <owner>, <by when>]`
2. An open question in this document
3. A **prerequisite task** in `delivery-plan.md`, on which the dependent tasks declare `dependsOn`

That third one is what makes the difference. A blocking unknown recorded only as prose gets discovered by the agent that hits it.

### Step 6 — The dependency-failure matrix

One table that makes the system's degraded behavior reviewable in one read:

| System | If it is slow | If it is down | If it returns garbage | User-visible effect |
|---|---|---|---|---|
| SendGrid | queue, do not block | queue + alert; drain on recovery | log, alert, do not retry a 4xx | none — email arrives late |
| Stripe | timeout at 10s → 504 | circuit opens → 503 + `Retry-After` | reject, order stays `pending` | checkout unavailable, no double charge |

"Returns garbage" — a schema change, an unexpected enum, a 200 with an error body — is the column most often missing, and the one most often responsible for a 500 that should have been a handled 502.

---

## Integration plan template

```markdown
# <Initiative> — Integration Plan

**Date:** YYYY-MM-DD · **Written by:** `be-shared-integration-plan`
**Blueprint:** `./blueprint.md` · **API surface:** `./api-surface.md`

## 1. Dependency register
| # | System | What it does for us | Direction | Protocol | Criticality | Account owner | Status |
|---|---|---|---|---|---|---|---|

## 2. Dependencies
<!-- one block per system: purpose, auth, configuration, environments, limits & budget,
     resilience, inbound webhook (if any), data crossing the boundary, local dev & test, open questions -->

## 3. Secrets checklist
| Secret | Store | Environments | Provisioned by | Needed by task | Rotation | Status |
|---|---|---|---|---|---|---|

## 4. Failure matrix
| System | If it is slow | If it is down | If it returns garbage | User-visible effect |
|---|---|---|---|---|

## 5. Blocking unknowns
| # | Unknown | Owner | Needed by | Blocks tasks |
|---|---|---|---|---|

## 6. Local development
<!-- Can a developer run the system with nothing provisioned? What is faked, what is a sandbox,
     what is genuinely required. If the answer is "nothing works without prod keys", that is a finding. -->

## 7. Routed to `devops-engineer`
| Need | Why |
|---|---|
```

## Self-check before handing off

1. Every system in the blueprint's External systems table has a block here; every block traces to a caller in `api-surface.md` or a named background job.
2. Every outbound dependency has a timeout, a retry policy that excludes 4xx, and a stated failure mode. No dependency has an unstated one.
3. Every inbound webhook has signature verification, a replay window, and idempotency on the provider event id.
4. Every secret is name-and-location only, distinct per environment, with a provisioner and a task.
5. Every blocking unknown exists in all three places (register row, open question, prerequisite task).
6. Section 6 answers honestly whether a new developer can run the system on day one.
7. Every `critical` dependency's user-visible failure is described in the same terms `api-surface.md` uses (503 + `Retry-After`, not "it errors").

## Handoffs

- **→ `be-shared-delivery-plan`** (Step 6). Prerequisite tasks for blocking unknowns, plus a client-implementation task per dependency.
- **→ `devops-engineer`** — the secrets checklist and section 7 are its work order: stores, environment config, network paths, egress rules.
- **→ `be-<stack>`** — writes the typed clients, retry/circuit-breaker policies, and webhook handlers. Outbound M2M token acquisition is its `auth0`/`cognito` skill.
- **→ QA peers** — `qa-network-mocking-<stack>` (stub outbound HTTP), `qa-email-testing-<stack>` (assert what was sent), `qa-messaging-testing-<stack>` (broker assertions), `qa-file-storage-testing-<stack>` (object storage), `qa-failure-injection-testing-<stack>` (prove the failure matrix is real rather than aspirational).
- **→ `observability-engineer-<stack>`** — every boundary here is a span, and every `critical` dependency deserves an SLO and an alert.

## Version policy

The integration contract is version-agnostic; two things are not. **Pin the provider's API version explicitly** where the provider supports it (Stripe, Twilio, Shopify) — an unpinned integration breaks on someone else's release schedule, and a version bump is its own task with its own test pass. And keep **SDK majors keyed to the project's runtime lane** per `CLAUDE.md`'s Stack defaults (.NET 10 / 8-9 · Java 21 + Spring Boot 3.x · Node 24 / 22): never plan an SDK major that requires a runtime the project does not target.
