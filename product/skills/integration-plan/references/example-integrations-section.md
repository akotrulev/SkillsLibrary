# Golden example — a spec's `## Integrations`

The filled `## Integrations` section for `product/skills/integration-plan`, from the toy spec the four
design skills share: `docs/specs/006-booking-cancellation-design.md`, feature F3 *Booking
cancellation* of the system plan `docs/plans/004-workshop-booking-system.md`. Its `## Data model` is
[`example-data-model-section.md`](../../data-model-plan/references/example-data-model-section.md), which
also lists the acceptance criteria AC1–AC6 cited below; its `## API surface` is
[`example-api-surface-section.md`](../../api-surface-plan/references/example-api-surface-section.md).
**The shapes and disciplines are normative; the domain content is illustrative.**

F3 is the first feature that sends email, so it designs the email provider §3 only names. Auth0 is
§3's and F1's, so it is referenced, not re-specified.

---

````markdown
## Integrations

### Builds on
| Dependency | Defined in | This feature |
|---|---|---|
| Auth0: sign-in, JWT validation, the `member` / `staff` roles | §3 Auth; `docs/specs/005-foundation-design.md` | uses the existing roles; nothing new |
| Email provider | §3 architecture (named, not designed) | **designs it**: X1 below |
| Local stack in `deploy/local/` | §3 telemetry base; 005 | adds a Mailpit container |

### Register
| # | System | What it does for us | Direction | Protocol | Criticality | Account owner | Status |
|---|---|---|---|---|---|---|---|
| X1 | SendGrid | The cancellation email, to the member, whoever cancelled | outbound | REST | **degraded** — the email is sent after the cancellation commits and retried; a cancellation never fails because email did | Studio owner | account `[TBD - owner, before prod cutover]` |

### Dependencies

#### X1 — SendGrid (email)

**Purpose:** tells the member their booking was cancelled: by them, or by staff with the reason.
**Direction:** outbound REST · **Criticality:** degraded
**Docs:** SendGrid v3 mail send · **API version pinned to:** v3
**Acceptance:** AC6; AC3 (the staff reason appears in the email)

**Auth**
| Aspect | Value |
|---|---|
| Method | API key, `Authorization: Bearer` |
| Rotation | On demand; one key per environment |

**Configuration** *(names and locations only, never values)*
| Key | Where it lives | Environments | Provisioned by |
|---|---|---|---|
| `Email__ApiKey` | Key Vault (staging, prod), per §3's config-and-secrets convention | distinct per env; none locally | Owner → devops-engineer |
| `Email__FromAddress` | appsettings (non-secret) | all | — |

**Environments**
| Env | Provider environment | Notes |
|---|---|---|
| local | **Mailpit sink, no SendGrid at all** | a developer runs the feature with nothing provisioned |
| staging | SendGrid sandbox mode | accepted but not delivered: **cannot email real members by construction** |
| prod | SendGrid live, domain-authenticated | SPF/DKIM/DMARC first; without them the email lands in spam |

**Limits & budget:** free tier 100 a day against ~10 cancellations a week; connect timeout 2 s, read
timeout 5 s.

**Resilience**
| Aspect | Policy |
|---|---|
| Sending | **Asynchronous, always:** the cancellation commits, then a background send starts |
| Retry | 3 attempts, exponential backoff, only on 5xx / timeout / 429; a 4xx is logged and dropped |
| Idempotency | the booking id is the message's custom id, so a retry is recognisable in SendGrid's activity log |
| Fallback | None needed: the booking stays cancelled, and the member sees it in My bookings (AC6) |

**Bounce & complaint handling:** log-and-review in v1; no inbound webhook `#confirmed` (the owner
accepts manual review at this volume).

**Data crossing the boundary:** the member's display name and email (read through
`IMembershipApi`), the workshop title, the session's start, the staff reason. Nothing else.

**Local dev & test**
| Layer | Approach |
|---|---|
| Local run | Mailpit in `deploy/local/` |
| Unit / component | A fake at our own `IEmailSender` seam; never assert on SendGrid's wire format |
| Integration | `qa-dotnet:email-testing` against Mailpit: the email arrives, names the session and carries the staff reason (AC3, AC6) |

**Open questions:** none.

### Secrets
| Secret | Store | Environments | Provisioned by | Needed by | Rotation | Status |
|---|---|---|---|---|---|---|
| `Email__ApiKey` | Key Vault | staging, prod (distinct) | Owner → devops-engineer | the SendGrid adapter behind `IEmailSender` | on demand | `[TBD - owner, before prod cutover]` |

### Failure matrix
| System | If it is slow | If it is down | If it returns garbage | User-visible effect |
|---|---|---|---|---|
| SendGrid | the background send waits; the cancellation is already committed | retried, then dropped and logged | log, drop after retries | the email arrives late or not at all; the cancellation always stands |

### Blocking unknowns
| # | Unknown | Owner | Needed by | Blocks |
|---|---|---|---|---|
| B1 | SendGrid account, domain authentication and the staging sandbox | Studio owner | before prod cutover | the email in staging and prod only; local work proceeds against Mailpit |

B1 is also the register row's `[TBD]` and an open question of this spec, and `writing-plans` turns it
into a human prerequisite task in the feature's implementation plan, which the email task names in
`Depends on:`. The three-places rule.

### Local development
A developer runs `docker compose up` in `deploy/local/` (PostgreSQL, the Grafana stack, and now
Mailpit) and signs in against the Auth0 dev application F1 set up. Nothing secret is needed. Honest
answer: the whole feature runs on day one.

### Routed to `devops-engineer`
| Need | Why |
|---|---|
| `Email__ApiKey` in Key Vault, per environment | owns the stores and the wiring; this section only names the key |
| SendGrid domain-authentication DNS records | DNS is infrastructure |
````
