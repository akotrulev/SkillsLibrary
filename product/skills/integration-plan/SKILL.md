---
name: plan-integrations
description: Use when a feature spec needs its ## Integrations section (external services, keys, limits, retries). Triggers "what external services do we depend on". Not for own endpoints (plan-api-surface).
disable-model-invocation: true
user-invocable: false
---

# Integrations — the feature spec's `## Integrations` section

Everything the feature depends on that the system does not control. The part of a design most often written as a one-liner ("we'll use SendGrid for email") and most often the reason a build stalls, because nobody asked who has the account, which environment the key is for, what happens when it 429s, and whether a developer can run the system without it.

Two failure modes this section exists to prevent:

1. **The blocking unknown discovered late:** an API key that needs a procurement request, a sandbox that takes two weeks to provision, a partner contract not yet signed. Cheap to surface at design time, expensive at task time.
2. **The undefined failure mode:** nobody decided what the system does when the provider is down, so it does whatever the HTTP client's default happens to be.

`/product:plan-feature` reads this file in its step 8 when the feature depends on a service outside the system, after the `## API surface`, and presents the result as one section of the spec. The user's approval of that section, then of the spec, is the gate; there is no other.

## Input

- **The spec so far:** the goal, the decisions from the interview, `## Acceptance criteria`, and the `## API surface` (endpoints that call out, background jobs, the outbound webhooks it emits).
- **The system plan's §3, when the feature came from one:** the external systems in its architecture diagram, the auth provider, and the config-and-secrets convention. Read the specs of the features this one depends on: their `## Integrations` holds the dependencies already designed.
- **Standalone (no system plan):** the existing clients, config keys and secret stores, `#observed` with `file:line`.

## Output

The `## Integrations` section of `docs/specs/NNN-<feature>-design.md`, with these subsections in this order: `### Builds on` · `### Register` · `### Dependencies` · `### Secrets` · `### Failure matrix` · `### Blocking unknowns` · `### Local development` · `### Routed to devops-engineer`. A subsection with nothing to say is one line saying so.

[`references/example-integrations-section.md`](references/example-integrations-section.md) is a filled section from the toy spec all four design skills share: its shapes are normative, its domain content illustrative.

## Scope

**This feature only, on top of what exists.** A dependency §3 names, or that an earlier feature's spec designed, is **referenced, never redefined**: a row in `### Builds on` naming where it is defined, plus a delta block only where this feature changes how it is used (a new template, a new webhook event, a higher volume). The identity provider is §3's; this section never re-specifies it. A new external system the system plan did not foresee is put to the user as "this changes the system plan's §3 <line>: keep it or change it?", and `plan-feature`'s close-out records an approved change.

---

## Procedure

### Step 1 — The register

Every external system this feature adds, on one screen; one this feature only uses is in `### Builds on`. Seeded from §3 and completed by walking `## API surface` for outbound calls and inbound triggers:

| # | System | What it does for us | Direction | Protocol | Criticality | Account owner | Status |
|---|---|---|---|---|---|---|---|
| X1 | SendGrid | Transactional email | outbound | REST | **degraded** — queue and retry, never block the request | Platform team | account exists `#confirmed` |
| X2 | Stripe | Card payments + refunds | both | REST + inbound webhook | **critical** — checkout fails without it | Finance | sandbox `[TBD - Finance, wk 2]` |

`X` ids are this spec's own; a dependency another spec defined keeps that spec's id and is cited as `007 X1`.

**Criticality has exactly three values**, and each is a design commitment, not a label:

| Value | Means | The section must then say |
|---|---|---|
| **critical** | The feature cannot function without it | What the user sees when it is down (503 + `Retry-After`, per the validation catalog) |
| **degraded** | The feature works, something is deferred or reduced | *Which* behaviour degrades, and how the deferred work completes later |
| **optional** | Absence is invisible to the user | Confirm it is genuinely invisible: analytics that block a request are not optional |

**Direction** drives everything downstream: `outbound` needs credentials, timeouts and retries; `inbound` needs signature verification, replay protection and idempotency; `both` needs all of it.

### Step 2 — A block per dependency

One block per register row, with these fields; the worked content lives in the example, so do not restate it here:

````markdown
#### X<n> — <System> (<what it is>)

**Purpose:** <one sentence — what it does for this feature>
**Direction:** <outbound | inbound | both> · **Criticality:** <critical | degraded | optional>
**Docs:** <link> · **API version pinned to:** <version>
**Acceptance:** <the AC<k> this dependency carries>

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

Rules the block must honour, whatever the system:

- **Retry only on 5xx / timeout / 429, never on a 4xx.** A 4xx retried is the same wrong request sent twice.
- **Outbound idempotency keys are our own ids** (a booking id, not a random UUID per attempt), so a retry cannot double-apply.
- **A webhook endpoint is anonymous but signature-verified:** state it as an explicit exception to the API-wide 401 rule, and verify over the **raw** body before parsing.
- **A fallback of "none" is stated, not omitted:** say what the user sees and what state the affected record stays in.
- **Fakes live at our own client interface, never the vendor's wire format;** the pinned API version means a version bump is its own task with its own test pass.

### Step 3 — Category-specific rules

| Category | Must state |
|---|---|
| **Email / SMS / push** | Sender identity + domain auth (SPF/DKIM/DMARC; skip it and email lands in spam) · template ownership (in-provider vs in-repo) · **bounce and complaint handling** · a per-environment guard so staging cannot reach real customers (allowlist or sandbox mode; state which) · unsubscribe/consent obligations · sending is asynchronous |
| **Payments** | Tokenization boundary and the resulting PCI scope · currency and rounding, matching `## Data model` · refunds/chargebacks as first-class flows · **reconciliation**: which system is the source of truth when they disagree, and how the mismatch is detected |
| **Identity provider** | Only what this feature changes (a new claim, a new role, a new M2M client); the provider itself is §3's · JWKS caching + rotation · what happens on IdP outage for already-issued tokens · handshake to `auth/_shared/{auth0-concepts,oidc-concepts}` |
| **Object storage** | Bucket/container per environment · access model (pre-signed URLs vs proxying; pick one, say why) · size and content-type limits, validated server-side · lifecycle/retention · public-vs-private default |
| **Message broker** | Topic/queue naming · delivery semantics (at-least-once by default, so consumers are idempotent) · ordering actually required · **dead-letter queue and who watches it** · schema evolution · consumer-group shape |
| **Search index** | Source of truth stays the DB · indexing trigger and acceptable staleness · reindex procedure · what the API returns when the index is behind or down |
| **Partner / internal APIs** | Contract source (OpenAPI file? none?) · versioning and deprecation notice · a named human contact · SLA · sandbox availability, **the most common blocking unknown** |
| **Inbound webhooks (any provider)** | Signature verification over the **raw** body before parsing · replay window · idempotency on the provider's event id · fast ack then async processing · what happens when the payload shape changes |

### Step 4 — Secrets

Every credential the feature adds, in one table, because this is what someone has to action:

| Secret | Store | Environments | Provisioned by | Needed by | Rotation | Status |
|---|---|---|---|---|---|---|

- **No values.** Not in the spec, not in a repo file, not in a code comment, not "temporarily". The section carries the key **name** and its **location**, in the store §3's config-and-secrets convention names.
- **Distinct per environment.** One key shared across staging and prod is a finding, stated as one.
- **"Needed by"** names the component or behaviour that reads it; the implementation plan turns it into the task that wires it.
- **`devops-engineer` owns the store and the wiring;** this table is its input.

### Step 5 — Blocking unknowns

Anything a human must obtain (an account, a sandbox, a contract, a key, a partner contact, a compliance sign-off) is **three things at once**:

1. A register row with status `[TBD - <owner>, <by when>]`.
2. A row in `### Blocking unknowns`, and an open question of the spec.
3. A **human prerequisite task** in the feature's implementation plan, which the dependent tasks name in `Depends on:`. `writing-plans` writes it from this row.

The third is what makes the difference: a blocking unknown recorded only as prose gets discovered by the agent that hits it.

### Step 6 — The failure matrix

One table that makes the feature's degraded behaviour reviewable in one read, one row per dependency the feature adds or newly relies on:

| System | If it is slow | If it is down | If it returns garbage | User-visible effect |
|---|---|---|---|---|
| Stripe | timeout at 10s → 504 | circuit opens → 503 + `Retry-After` | reject, order stays `pending` | checkout unavailable, no double charge |

"Returns garbage" (a schema change, an unexpected enum, a 200 with an error body) is the column most often missing, and the one most often responsible for a 500 that should have been a handled 502.

---

## Section template

```markdown
## Integrations

### Builds on
| Dependency | Defined in | This feature |
|---|---|---|

### Register
| # | System | What it does for us | Direction | Protocol | Criticality | Account owner | Status |
|---|---|---|---|---|---|---|---|

### Dependencies
<one block per new dependency; one delta block per changed one, headed with its spec>

### Secrets
| Secret | Store | Environments | Provisioned by | Needed by | Rotation | Status |
|---|---|---|---|---|---|---|

### Failure matrix
| System | If it is slow | If it is down | If it returns garbage | User-visible effect |
|---|---|---|---|---|

### Blocking unknowns
| # | Unknown | Owner | Needed by | Blocks |
|---|---|---|---|---|

### Local development
<Can a developer run the feature with nothing provisioned? What is faked, what is a sandbox, what is genuinely required.>

### Routed to `devops-engineer`
| Need | Why |
|---|---|
```

## Self-check before presenting the section

1. Every external system the feature touches is either in `### Builds on` with where it is defined, or a register row with a block; nothing §3 or an earlier spec defined is redefined.
2. Every block traces to a caller in `## API surface` or a named background job, and carries an `**Acceptance:**` line where a criterion depends on it.
3. Every outbound dependency has a timeout, a retry policy that excludes 4xx, and a stated failure mode; every inbound webhook has signature verification, a replay window and idempotency on the provider event id.
4. Every secret is name-and-location only, distinct per environment, with a provisioner and a "needed by".
5. Every blocking unknown exists in all three places (register row, blocking-unknowns row, the human prerequisite task the plan will hold).
6. `### Local development` answers honestly whether a developer can run the feature on day one.
7. Every `critical` dependency's user-visible failure is described in the same terms `## API surface` uses (503 + `Retry-After`, not "it errors").

## Version policy

The integration contract is version-agnostic; two things are not. **Pin the provider's API version explicitly** where the provider supports it (Stripe, Twilio, Shopify): an unpinned integration breaks on someone else's release schedule, and a version bump is its own task with its own test pass. And keep **SDK majors keyed to the project's runtime lane** per `CLAUDE.md`'s Stack defaults (.NET 10 / 8-9 · Java 21 + Spring Boot 3.x · Node 24 / 22): never plan an SDK major that requires a runtime the project does not target.
