# STRIDE-per-element — the enumeration deep dive

STRIDE is a **mnemonic for what can go wrong**, invented at Microsoft (Kohnfelder & Garg, 1999). Each letter
is the *violation of one security property*, which is what makes it enumerable rather than a brainstorm:

| Letter | Threat | Property violated | The one-line question |
|---|---|---|---|
| **S** | **Spoofing** | Authentication | Can something pretend to be this element? |
| **T** | **Tampering** | Integrity | Can its data or code be modified in place or in flight? |
| **R** | **Repudiation** | Non-repudiation | Can an actor deny having done it, and can we prove otherwise? |
| **I** | **Information disclosure** | Confidentiality | Can someone read what they shouldn't? |
| **D** | **Denial of service** | Availability | Can someone make it unavailable or unaffordably slow? |
| **E** | **Elevation of privilege** | Authorization | Can someone do more than their role allows? |

## The per-element chart (the load-bearing table)

**STRIDE-per-element** is the discipline that makes enumeration finite: not every letter applies to every
element type, so you walk each DFD element against **only its applicable letters**. This is the classic
Microsoft chart — memorize it, it is the whole method:

| Element type | S | T | R | I | D | E |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| **External entity** (user, third-party API, mobile client) | ✅ | | ✅ | | | |
| **Process** (service, function, container, job) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Data store** (DB, bucket, cache, queue, log, secret store) | | ✅ | ✅¹ | ✅ | ✅ | |
| **Data flow** (HTTP call, SQL connection, message, file write) | | ✅ | | ✅ | ✅ | |

¹ Repudiation applies to a data store **when the store is the evidence** — an audit log, an event stream, an
append-only ledger. A tamperable or unwritten audit log is a repudiation threat about the *store*, not the
actor.

**Why the blanks are correct, not laziness.** A data flow cannot be *spoofed* — the endpoints are spoofed, and
that threat is filed against the process or external entity. A data store cannot *elevate privilege* — it has
no execution context; the process reading it does. Filing threats against the wrong element is the most
common quality defect in a first threat model: it produces duplicates and orphans nobody can assign.

**Every crossing of a trust boundary is enumerated twice** — once for the sending element, once for the
receiving one. A boundary crossing with no threats recorded is a modelling error, not a safe flow.

---

## The threat catalogue per category

Use these as prompts, not as a checklist to copy. Each entry names the concrete mechanism, so the threat
statement stays specific enough to test.

### S — Spoofing (authentication)

| Mechanism | Typical evidence to look for | Spine |
|---|---|---|
| Stolen/replayed bearer token; no `aud`/`iss`/`exp` validation | JWT middleware config, clock-skew allowance | OWASP A07 · ATT&CK **T1550.001** (Application Access Token) |
| Credential stuffing / weak password policy | no lockout, no rate limit on `/login` | A07 · **T1110** (Brute Force) |
| Long-lived static cloud key instead of federated identity | `AWS_SECRET_ACCESS_KEY` in CI, no OIDC | A07 · A02 · **T1078.004** (Valid Accounts: Cloud) |
| Unauthenticated service-to-service call inside the mesh | no mTLS, "internal network is trusted" | A01 |
| Webhook with no signature verification | raw-body HMAC check absent | A08 (Data Integrity) |
| Spoofed sender in a queue/topic (no producer identity) | broker ACLs absent | A01 |
| Kubernetes SA token mounted into every pod by default | `automountServiceAccountToken` unset | **T1528** (Steal Application Access Token) |

### T — Tampering (integrity)

| Mechanism | Typical evidence | Spine |
|---|---|---|
| Mass assignment / over-posting into a domain entity | DTO binds the entity directly | A01 · A05 (Injection) |
| Unsigned/unpinned build artifact or base image | `:latest` tags, no cosign attestation | **A03** (Software Supply Chain) · A08 · **T1195.002** |
| Client-side price/role/quantity trusted by the server | server re-reads none of it | A06 (Insecure Design) |
| Writable config/feature-flag store reachable from the app tier | flag store shares creds with the app | A02 |
| IaC state file writable by CI without locking | no remote+locked backend | **T1578** (Modify Cloud Compute Infrastructure) |
| Container running with a writable root filesystem + `root` | no `readOnlyRootFilesystem`, no `runAsNonRoot` | **T1611** (Escape to Host) |
| SQL/NoSQL/command injection mutating data | string-concatenated query | A05 |

### R — Repudiation (non-repudiation)

| Mechanism | Typical evidence | Spine |
|---|---|---|
| Security-relevant action not logged at all (login, role change, refund, export) | no audit event on the handler | A09 (Logging & Alerting Failures) |
| Audit log writable/deletable by the same identity it records | one DB user for app + audit | A09 |
| Log lacks actor, tenant, correlation id, or a trusted timestamp | unstructured `log.info("done")` | A09 |
| Cloud trail disabled, not multi-region, or short-retention | CloudTrail/Activity Log config | **T1562.008** (Impair Defenses: Cloud Logs) |
| Shared/service account performs user-attributable acts | one `svc-admin` for all operators | A07 |

### I — Information disclosure (confidentiality)

| Mechanism | Typical evidence | Spine |
|---|---|---|
| BOLA/IDOR — object id in the path with no per-object ownership check | handler loads by id, no tenant filter | A01 · API1:2023 |
| Excessive data exposure — full entity serialized to the client | no response DTO | API3:2023 |
| Verbose errors / stack traces / framework banners | `DeveloperExceptionPage` in prod | A02 · A10 |
| Storage bucket or DB reachable from the internet | public ACL, `0.0.0.0/0` SG | A02 · **T1530** (Data from Cloud Storage) |
| Secrets in env dumps, images, logs, or client bundles | `docker history`, sourcemaps | A02 · A04 · **T1552.001** (Unsecured Credentials: Files) |
| Plaintext transport for an internal hop | HTTP between pods, unencrypted DB link | A04 (Cryptographic Failures) |
| PII crossing a trust boundary to a third party with no DPA/redaction | outbound payload contains full records | A02 |

### D — Denial of service (availability)

| Mechanism | Typical evidence | Spine |
|---|---|---|
| No rate limit / quota per identity on an expensive endpoint | report, search, export, LLM call | API4:2023 |
| Unbounded page size / result set / upload size | no `maxPageSize`, no body cap | API4:2023 |
| No pod/container resource limits → noisy-neighbour eviction | `resources.limits` absent | **T1499** (Endpoint DoS) |
| Retry storm without jitter or circuit breaker | naive `retry(5)` across a fan-out | — |
| ReDoS / zip bomb / decompression bomb on a parsing path | user-supplied regex or archive | A05 · A10 |
| Single point of failure with no PDB / min-replicas | `replicas: 1` for a tier-1 service | — |

### E — Elevation of privilege (authorization)

| Mechanism | Typical evidence | Spine |
|---|---|---|
| BFLA — an admin function reachable by a normal role | route missing an authorization policy | A01 · API5:2023 |
| Role/claim taken from the request instead of the token | `X-Role` header trusted | A01 |
| Over-broad cloud IAM (`*:*`, `iam:PassRole`, wildcard trust policy) | policy JSON review | A01 · **T1078.004** |
| K8s RBAC binding to `cluster-admin`, or `escalate`/`bind`/`impersonate` verbs | RoleBinding review | **T1078.003** |
| Privileged container / `hostPID` / `hostPath` / added `CAP_SYS_ADMIN` | pod spec review | **T1611** (Escape to Host) |
| Deserialization or SSTI reaching code execution | `BinaryFormatter`, template from user input | A05 · A08 · **T1190** |
| SSRF reaching the cloud metadata endpoint (IMDSv1) | outbound fetch with a user-supplied URL | **A01** (SSRF folded in, 2025) · **T1552.005** (Cloud Instance Metadata API) |

---

## Working the enumeration

1. **One element at a time, applicable letters only.** Finish the element before moving on — jumping around
   is how a boundary crossing ends up with no threats.
2. **Write the threat as a sentence with an actor, an action, and a consequence.** "An authenticated tenant-B
   user retrieves tenant-A invoices by changing the id in the path, disclosing customer PII" is testable.
   "IDOR risk" is not.
3. **Record the existing mitigation and its evidence** (`file:line`, policy name, manifest path) in the same
   row. A threat with a verified mitigation is still a row — it is what a retest re-checks.
4. **Say "not applicable" out loud, with a reason.** A silently skipped letter is indistinguishable from an
   overlooked one. `S — n/a, element is a data store` is a complete answer.
5. **Stop at the element boundary.** Depth beyond "what can go wrong here" belongs in an attack tree
   (`references/attack-trees.md`), not in a deeper STRIDE row.

## Where STRIDE runs out

STRIDE enumerates **technical property violations**. It is weak on, and must be supplemented for:

- **Business-logic abuse** — a legal sequence of legal operations with an illegal outcome (refund loops,
  coupon stacking, negative quantities). Model these as **abuse cases** or an attack tree; the library's
  `qa/manual/test-design-techniques` decision tables and `business-analysis:decision-table` are the better instruments.
- **Privacy** — "we collect it lawfully but retain it forever" is not a STRIDE letter. **LINDDUN**
  (Linkability, Identifiability, Non-repudiation, Detectability, Disclosure of information, Unawareness,
  Non-compliance) is the privacy-specific counterpart; run it alongside STRIDE when the system holds
  regulated personal data.
- **Risk-centric prioritisation** — STRIDE tells you what can go wrong, not what to fix first. That is the
  attack tree plus the register's likelihood × impact column, or a **PASTA**-style risk-centric pass on a
  high-stakes system.
