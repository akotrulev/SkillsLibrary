# QA Skills Library — Gap Analysis & Build Plan

_Audit date: 2026-05-28_

Goal: a Claude skills library that covers **UI, API, and performance test authoring + pipeline execution**, with first-class support for **email**, **network monitoring**, and **database** verification inside tests.

> **Library-wide convention (this audit forward):** every skill ships **three sibling implementations** under `{skill}/{java,dotnet,typescript}/SKILL.md`. Shared cross-stack rules live in `{skill}/_shared/SKILL.md` (optional). Process / non-code skills (test strategy, charters, bug reports, metrics) stay single-folder. Existing skills that don't follow this convention are flagged for restructure below.

---

## 1. What we have today

### Authoring (good coverage)
| Area | Skill | Stacks covered |
|------|-------|----------------|
| API test generator | `qa/api-test-author/generator/{dotnet,java,typescript}` | NUnit+RestSharp, RestAssured+TestNG, Vitest+fetch+Zod |
| API test reviewer | `qa/api-test-author/reviewer` | .NET, Java |
| API client scaffolder | `qa/api-client-writer` | .NET (Accelerator) only |
| API DTO writer | `qa/api-dto-writer/{dotnet,java,typescript}` | All three |
| UI test generator | `qa/ui-test-author/playwright/{typescript,java,dotnet}`, `qa/ui-test-author/selenium-java`, `qa/ui-test-author/appium` | Playwright (TS/Java/.NET), Selenium-Java, Appium (.NET) |
| UI test reviewer | `qa/ui-test-author/reviewer` | All stacks above |
| Page object architecture | `qa/page-object-architect` | Cross-stack design |
| Contract testing | `qa/contract-testing-pact` | JS/.NET/Java |
| Performance | `qa/performance` | k6, NBomber, Gatling |

### Planning / process (good coverage)
- `qa/test-case-writer`, `qa/exploratory-charter-writer`, `qa/bug-report-writer`
- `qa/_shared/test-strategy`, `qa/_shared/quality-metrics`
- `qa/test-data-builder` (builders / ObjectMother)
- `qa/accelerator-conventions` (in-house framework rules)
- `qa/allure-reporting` (results)
- `qa/webapp-testing` (Playwright Python toolkit — Anthropic-provided)

### Adjacent (in `devops/`)
- `github-actions`, `azure-pipelines`, `gitlab-ci`, `aws-deployment`, `azure-deployment`, `kubernetes`, `docker`, `iac-bicep-terraform`, `environment-config`
- These give generic CI knowledge but no **QA-pipeline** patterns (sharding, browser matrices, allure publish, perf gates, flaky-quarantine, etc.).

---

## 2. Gaps (mapped to the user's asks)

### A. Pipelines — explicit ask
**Status: partial.** Generic CI skills exist; no QA-specific pipeline skill.

- **Missing:** `qa/ci-pipelines/{github-actions,azure-pipelines,gitlab-ci}` — sharding Playwright across N runners, TestNG parallel groups, NUnit `--parallel`, Allure publish + history, JUnit/TRX result upload, retry-on-failure policy, perf gates (k6 thresholds → fail build), test-impact selection, artifacts (videos, traces, HAR), secrets via OIDC, env-per-PR.
- **Missing:** `qa/test-environments` — Testcontainers + docker-compose patterns to stand up app+DB+queue+mailcatcher per test job; ephemeral env teardown.
- **Missing:** `qa/cloud-grid-config` — BrowserStack / Sauce Labs / LambdaTest / AWS Device Farm wiring for Playwright + Appium (capabilities, parallelism limits, video, secret handling).

### B. Email service — explicit ask
**Status: missing entirely.**

- **New:** `qa/email-testing/{mailpit,mailosaur,gmail-imap,sendgrid-sandbox}` — capture sign-up / OTP / password-reset / magic-link emails, extract HTML body & links, assert subject/recipient/From, poll-with-timeout helpers, attachment download. Stacks: .NET, Java, TS.
- Should integrate with `qa/test-data-builder` (test user inbox per run) and `qa/ui-test-author/*` (verify post-signup email then click link).

### C. Network monitoring — explicit ask
**Status: missing entirely.**

- **New:** `qa/network-monitoring/playwright-routes` — `page.route`, `page.on('request'|'response')`, request mocking, request assertion (was X called, with what payload), latency injection, offline mode, header tampering, HAR capture+replay.
- **New:** `qa/network-monitoring/cdp` — Chrome DevTools Protocol for deeper hooks (throttling, cache disable, security headers checks).
- **New:** `qa/network-monitoring/proxy` — mitmproxy / BrowserMob / WireMock as MITM for non-Playwright stacks (Appium, Selenium); recording flows, asserting traffic, fault injection.
- **Optional later:** `qa/network-monitoring/api-tracing` — extracting `traceparent` from test requests and joining to Tempo / App Insights for cross-system assertions (ties to `observability/opentelemetry-*`).

### D. Database connection & queries — explicit "plus"
**Status: missing entirely.**

- **New:** `qa/db-testing/{dotnet,java,typescript}` — connect from tests (Dapper / Npgsql / SqlClient; Spring JdbcTemplate or jOOQ; node-postgres / Prisma / Knex), seed fixtures via builder, query-based assertions (was the row written, in what state), safe cleanup (`TRUNCATE … CASCADE`, transactional rollback, per-test schemas), wait-for-eventual-consistency helpers, snapshot/restore for heavy fixtures.
- **New:** `qa/db-testing/testcontainers` — Postgres / SQL Server / Mongo / Redis containers per suite, schema migration on startup (Flyway / EF migrations / node-pg-migrate), shared container per test class vs per test trade-offs.
- **New:** `qa/db-testing/query-author` — guardrails for safe SQL in tests (parameterized, read-only verifications, no `SELECT *` in assertions, naming the column you assert on).

### E. Other gaps (recommend, not explicitly asked)

| Priority | Skill | Why |
|---|---|---|
| High | `qa/visual-regression/{playwright-snapshots,percy,applitools}` | Pixel diffs are routinely requested; Playwright snapshot config has sharp edges (font rendering, CI baselines) |
| High | `qa/accessibility-testing/{axe-playwright,lighthouse-ci}` | a11y is a standard release gate; no skill today |
| High | `qa/auth0-test-tokens` | Bridge between `auth/auth0-*` and QA — fetch M2M / ROPG / device-code tokens for test users; rotate; stash in test context. Avoids each team re-inventing |
| Medium | `qa/api-mocking/{wiremock,msw,mountebank,prism}` | Service virtualization for tests where dependencies are flaky/unavailable |
| Medium | `qa/messaging-testing/{service-bus,sqs,kafka,rabbitmq}` | Async assertions: produced message X, consumed → side-effect Y |
| Medium | `qa/file-storage-testing/{s3,azure-blob}` | Upload/download/lifecycle assertions |
| Medium | `qa/synthetic-monitoring/{k6-cloud,datadog-synthetics,playwright-monitor}` | Production smoke as a deliverable from QA |
| Medium | `qa/security-testing/{zap-baseline,dependency-scanning}` | DAST + SCA in the pipeline; ships well with `devops/github-actions` |
| Medium | `qa/feature-flag-testing/{launchdarkly,growthbook,openfeature}` | Tests must opt-in/out of flag states deterministically |
| Low | `qa/websocket-sse-testing` | Streaming endpoints currently uncovered |
| Low | `qa/mobile-device-farm` | Cloud Appium wiring (BrowserStack/Sauce/Device Farm) — also useful for non-Accelerator Appium |
| Low | `qa/i18n-testing` | Locale matrices, pseudo-localization |
| Low | `qa/data-driven-testing` | CSV / JSON / Excel-driven parameterized tests across stacks |
| Low | `qa/flaky-test-quarantine` | Detection + auto-quarantine + reporting; complements `_shared/quality-metrics` |

### F. Coverage gaps inside existing skills
- `qa/api-client-writer` — **only .NET / Accelerator**. Add Java and TS siblings for parity with `api-test-author`.
- `qa/ui-test-author/appium` — **.NET only**. Add Java and TS siblings (most mobile shops use Java/TS).
- `qa/api-test-author/reviewer` — no TypeScript coverage; generator has TS, reviewer doesn't.
- `qa/performance` — has overview but no per-tool generator subdirs like `qa/performance/{k6,nbomber,gatling}`. Splitting will let each go deeper (workload modelling, distributed run, results to Grafana).
- `qa/contract-testing-pact` — solid; consider a sibling `qa/contract-testing-spring-cloud-contract` for pure-JVM shops.

---

## 3. Proposed structure (after changes)

Convention: every **code-producing** skill has `{java,dotnet,typescript}/SKILL.md` siblings + optional `_shared/SKILL.md`. **Process** skills (planning, metrics, bug reports) stay flat. Tool-specific skills (e.g. `mailpit`, `wiremock`) still get the three stack subfolders, because the consumer API differs per language.

```
qa/
├── _shared/                                       ← process-level, stack-agnostic
│   ├── quality-metrics/SKILL.md
│   ├── test-strategy/SKILL.md
│   └── ci-conventions/SKILL.md                    ← NEW
│
├── api-test-author/
│   ├── generator/{java,dotnet,typescript}/SKILL.md
│   └── reviewer/{java,dotnet,typescript}/SKILL.md ← ADD typescript
├── api-client-writer/{java,dotnet,typescript}/SKILL.md   ← ADD java, typescript
├── api-dto-writer/{java,dotnet,typescript}/SKILL.md
│
├── ui-test-author/
│   ├── playwright/{java,dotnet,typescript}/SKILL.md
│   ├── selenium/{java,dotnet,typescript}/SKILL.md ← RESTRUCTURE (currently java-only)
│   ├── appium/{java,dotnet,typescript}/SKILL.md   ← ADD java, typescript
│   └── reviewer/{java,dotnet,typescript}/SKILL.md ← SPLIT (currently single)
│
├── page-object-architect/{java,dotnet,typescript}/SKILL.md   ← SPLIT
│
├── performance/
│   ├── k6/typescript/SKILL.md                     ← k6 is JS-native; TS only
│   ├── nbomber/dotnet/SKILL.md                    ← .NET-only by tool design
│   ├── gatling/java/SKILL.md                      ← JVM-only by tool design
│   └── _shared/SKILL.md                           ← workload modelling, SLOs, gates
│
├── ci-pipelines/                                  ← NEW
│   ├── github-actions/{java,dotnet,typescript}/SKILL.md
│   ├── azure-pipelines/{java,dotnet,typescript}/SKILL.md
│   └── gitlab-ci/{java,dotnet,typescript}/SKILL.md
│
├── test-environments/{java,dotnet,typescript}/SKILL.md       ← NEW (Testcontainers)
├── cloud-grid-config/{java,dotnet,typescript}/SKILL.md       ← NEW (BrowserStack/Sauce)
│
├── email-testing/                                 ← NEW
│   ├── mailpit/{java,dotnet,typescript}/SKILL.md
│   ├── mailosaur/{java,dotnet,typescript}/SKILL.md
│   ├── gmail-imap/{java,dotnet,typescript}/SKILL.md
│   └── sendgrid-sandbox/{java,dotnet,typescript}/SKILL.md
│
├── network-monitoring/                            ← NEW
│   ├── playwright-routes/{java,dotnet,typescript}/SKILL.md
│   ├── cdp/{java,dotnet,typescript}/SKILL.md
│   └── proxy/{java,dotnet,typescript}/SKILL.md    ← mitmproxy / BrowserMob bindings
│
├── db-testing/                                    ← NEW
│   ├── client/{java,dotnet,typescript}/SKILL.md   ← connect, seed, assert, clean
│   ├── testcontainers/{java,dotnet,typescript}/SKILL.md
│   └── query-author/{java,dotnet,typescript}/SKILL.md
│
├── visual-regression/                             ← NEW
│   ├── playwright-snapshots/{java,dotnet,typescript}/SKILL.md
│   ├── percy/{java,dotnet,typescript}/SKILL.md
│   └── applitools/{java,dotnet,typescript}/SKILL.md
│
├── accessibility-testing/                         ← NEW
│   ├── axe-playwright/{java,dotnet,typescript}/SKILL.md
│   └── lighthouse-ci/{java,dotnet,typescript}/SKILL.md
│
├── auth0-test-tokens/{java,dotnet,typescript}/SKILL.md       ← NEW
│
├── api-mocking/                                   ← NEW
│   ├── wiremock/{java,dotnet,typescript}/SKILL.md
│   ├── msw/{java,dotnet,typescript}/SKILL.md
│   ├── mountebank/{java,dotnet,typescript}/SKILL.md
│   └── prism/{java,dotnet,typescript}/SKILL.md
│
├── messaging-testing/                             ← NEW
│   ├── service-bus/{java,dotnet,typescript}/SKILL.md
│   ├── sqs/{java,dotnet,typescript}/SKILL.md
│   ├── kafka/{java,dotnet,typescript}/SKILL.md
│   └── rabbitmq/{java,dotnet,typescript}/SKILL.md
│
├── file-storage-testing/                          ← NEW
│   ├── s3/{java,dotnet,typescript}/SKILL.md
│   └── azure-blob/{java,dotnet,typescript}/SKILL.md
│
├── synthetic-monitoring/{java,dotnet,typescript}/SKILL.md    ← NEW
├── security-testing/                              ← NEW
│   ├── zap-baseline/{java,dotnet,typescript}/SKILL.md
│   └── dependency-scanning/{java,dotnet,typescript}/SKILL.md
├── feature-flag-testing/{java,dotnet,typescript}/SKILL.md    ← NEW
├── flaky-test-quarantine/{java,dotnet,typescript}/SKILL.md   ← NEW
├── websocket-sse-testing/{java,dotnet,typescript}/SKILL.md   ← NEW
├── i18n-testing/{java,dotnet,typescript}/SKILL.md            ← NEW
├── data-driven-testing/{java,dotnet,typescript}/SKILL.md     ← NEW
├── mobile-device-farm/{java,dotnet,typescript}/SKILL.md      ← NEW
│
├── contract-testing-pact/{java,dotnet,typescript}/SKILL.md   ← RESTRUCTURE
├── allure-reporting/{java,dotnet,typescript}/SKILL.md        ← RESTRUCTURE
├── test-data-builder/{java,dotnet,typescript}/SKILL.md       ← RESTRUCTURE
│
├── test-case-writer/SKILL.md                      ← process, stays flat
├── bug-report-writer/SKILL.md                     ← process, stays flat
├── exploratory-charter-writer/SKILL.md            ← process, stays flat
└── accelerator-conventions/SKILL.md               ← in-house, stays flat (single stack)
```

**Tool-bound exceptions** (cannot have all three stacks):
- `performance/nbomber` — .NET only by tool design.
- `performance/gatling` — JVM only by tool design.
- `performance/k6` — JS/TS only by tool design.
- `accelerator-conventions` — single in-house framework (currently .NET).

For these, the rule becomes "ship the stack(s) the tool actually supports" and document the limitation in the skill description.

---

## 4. Build backlog (prioritized)

**Counting rule:** every new skill node = **3 SKILL.md files** (`java/`, `dotnet/`, `typescript/`) unless flagged as tool-bound. Estimates are per-stack first-cut. Build one stack as the canonical reference, then port to the other two.

### Phase 0 — restructure existing skills to the convention

These already exist but violate the three-stack layout. Restructure before adding new content. Status: ☐ todo · 🔄 in progress · ☑ done.

| # | Status | Skill | Action |
|---|--------|-------|--------|
| 0.1 | ☑ | `qa/ui-test-author/selenium-java` | Rename to `qa/ui-test-author/selenium/java`; add `selenium/dotnet`, `selenium/typescript` ✓ done 2026-05-28 |
| 0.2 | ☑ | `qa/ui-test-author/appium` (.NET) | Move to `qa/ui-test-author/appium/dotnet`; add `appium/java`, `appium/typescript` ✓ done 2026-05-28 |
| 0.3 | ☑ | `qa/ui-test-author/reviewer` | Split into `reviewer/{java,dotnet,typescript}` ✓ done 2026-05-29 |
| 0.4 | ☑ | `qa/api-test-author/reviewer` (.NET + Java) | Added `reviewer/typescript` ✓ done 2026-05-29 |
| 0.5 | ☑ | `qa/api-client-writer` (.NET only) | Added `java`, `typescript` siblings (dotnet pre-existing) ✓ done 2026-05-29 |
| 0.6 | ☑ | `qa/page-object-architect` | Split into `{java,dotnet,typescript}` ✓ done 2026-05-29 |
| 0.7 | ☑ | `qa/contract-testing-pact` | Split into `{java,dotnet,typescript}` + `_shared` ✓ done 2026-05-29 |
| 0.8 | ☑ | `qa/allure-reporting` | Split into `{java,dotnet,typescript}` ✓ done 2026-05-29 |
| 0.9 | ☑ | `qa/test-data-builder` | Split into `{java,dotnet,typescript}` ✓ done 2026-05-29 |
| 0.10 | ☑ | `qa/performance` | Split into `performance/{k6/typescript, nbomber/dotnet, gatling/java, _shared}` ✓ done 2026-05-29 |

### Phase 1 — explicit asks (highest priority)

Each row = 3 stack skills unless noted.

| # | Status | Skill node | Stacks | Notes |
|---|--------|-----------|--------|-------|
| 1 | ☑ | `qa/db-testing/client/{java,dotnet,typescript}` | 3 | All 3 stacks ✓ 2026-05-29 |
| 2 | ☑ | `qa/db-testing/testcontainers/{java,dotnet,typescript}` | 3 | Postgres / SQL Server / Mongo / Redis lifecycle per stack — all 3 stacks ✓ 2026-05-29 |
| 3 | ☐ | `qa/db-testing/query-author/{java,dotnet,typescript}` | 3 | Parameterized SQL, read-only assertion queries, no `SELECT *` |
| 4 | ☑ | `qa/email-testing/mailpit/{java,dotnet,typescript}` | 3 | HTTP API client per stack — all 3 stacks ✓ 2026-05-29 |
| 5 | ☐ | `qa/email-testing/mailosaur/{java,dotnet,typescript}` | 3 | Official SDK per stack |
| 6 | ☐ | `qa/email-testing/gmail-imap/{java,dotnet,typescript}` | 3 | JavaMail / MailKit / imapflow |
| 7 | ☐ | `qa/email-testing/sendgrid-sandbox/{java,dotnet,typescript}` | 3 | Optional; rounds out the family |
| 8 | ☐ | `qa/network-monitoring/playwright-routes/{java,dotnet,typescript}` | 3 | `page.route`, HAR, mocking |
| 9 | ☐ | `qa/network-monitoring/cdp/{java,dotnet,typescript}` | 3 | Throttling, security headers |
| 10 | ☐ | `qa/network-monitoring/proxy/{java,dotnet,typescript}` | 3 | mitmproxy (TS via Python sidecar), BrowserMob (Java), Titanium-Web-Proxy (.NET) |
| 11 | ☐ | `qa/ci-pipelines/github-actions/{java,dotnet,typescript}` | 3 | Shard matrix, Allure publish, perf gate, OIDC secrets |
| 12 | ☑ | `qa/ci-pipelines/azure-pipelines/{java,dotnet,typescript}` | 3 | Same patterns, Azure idioms — all 3 stacks ✓ 2026-05-29 |
| 13 | ☐ | `qa/ci-pipelines/gitlab-ci/{java,dotnet,typescript}` | 3 | Same patterns, GitLab idioms |
| 14 | ☐ | `qa/test-environments/{java,dotnet,typescript}` | 3 | Testcontainers + docker-compose per stack |

### Phase 2 — broaden authoring coverage (after Phase 0 restructure)

| # | Status | Skill node | Stacks | Notes |
|---|--------|-----------|--------|-------|
| 15 | ☐ | `qa/cloud-grid-config/{java,dotnet,typescript}` | 3 | BrowserStack / Sauce / LambdaTest / Device Farm |
| 16 | ☐ | `qa/auth0-test-tokens/{java,dotnet,typescript}` | 3 | M2M + ROPG + device-code for test users |
| 17 | ☐ | `qa/visual-regression/playwright-snapshots/{java,dotnet,typescript}` | 3 | |
| 18 | ☐ | `qa/visual-regression/percy/{java,dotnet,typescript}` | 3 | |
| 19 | ☐ | `qa/visual-regression/applitools/{java,dotnet,typescript}` | 3 | |
| 20 | ☐ | `qa/accessibility-testing/axe-playwright/{java,dotnet,typescript}` | 3 | |
| 21 | ☐ | `qa/accessibility-testing/lighthouse-ci/{java,dotnet,typescript}` | 3 | |
| 22 | ☐ | `qa/api-mocking/wiremock/{java,dotnet,typescript}` | 3 | WireMock has all three client libs |
| 23 | ☐ | `qa/api-mocking/msw/{java,dotnet,typescript}` | 3 | TS primary; Java/.NET via sidecar |
| 24 | ☐ | `qa/api-mocking/mountebank/{java,dotnet,typescript}` | 3 | HTTP-driven, stack-agnostic |
| 25 | ☐ | `qa/api-mocking/prism/{java,dotnet,typescript}` | 3 | OpenAPI-driven mock; CLI + container |
| 26 | ☐ | `qa/security-testing/zap-baseline/{java,dotnet,typescript}` | 3 | |
| 27 | ☐ | `qa/security-testing/dependency-scanning/{java,dotnet,typescript}` | 3 | OWASP DC + stack-native (NuGet audit / `npm audit` / Gradle versions) |

### Phase 3 — broader coverage

| # | Status | Skill node | Stacks | Notes |
|---|--------|-----------|--------|-------|
| 28 | ☐ | `qa/messaging-testing/service-bus/{java,dotnet,typescript}` | 3 | |
| 29 | ☐ | `qa/messaging-testing/sqs/{java,dotnet,typescript}` | 3 | |
| 30 | ☐ | `qa/messaging-testing/kafka/{java,dotnet,typescript}` | 3 | |
| 31 | ☐ | `qa/messaging-testing/rabbitmq/{java,dotnet,typescript}` | 3 | |
| 32 | ☐ | `qa/file-storage-testing/s3/{java,dotnet,typescript}` | 3 | |
| 33 | ☐ | `qa/file-storage-testing/azure-blob/{java,dotnet,typescript}` | 3 | |
| 34 | ☐ | `qa/synthetic-monitoring/{java,dotnet,typescript}` | 3 | |
| 35 | ☐ | `qa/feature-flag-testing/{java,dotnet,typescript}` | 3 | LaunchDarkly / GrowthBook / OpenFeature |
| 36 | ☐ | `qa/flaky-test-quarantine/{java,dotnet,typescript}` | 3 | TestNG retry analyzer / NUnit retry / Vitest retry + reporting |
| 37 | ☐ | `qa/websocket-sse-testing/{java,dotnet,typescript}` | 3 | |
| 38 | ☐ | `qa/i18n-testing/{java,dotnet,typescript}` | 3 | |
| 39 | ☐ | `qa/data-driven-testing/{java,dotnet,typescript}` | 3 | CSV / JSON / Excel |
| 40 | ☐ | `qa/mobile-device-farm/{java,dotnet,typescript}` | 3 | Pairs with `cloud-grid-config` |

### Total volume

- Phase 0 restructure: ~10 existing skills repositioned, **~22 new SKILL.md files** to bring siblings to parity.
- Phase 1: 14 skill nodes × 3 stacks ≈ **42 SKILL.md files**.
- Phase 2: 13 skill nodes × 3 stacks ≈ **39 SKILL.md files**.
- Phase 3: 13 skill nodes × 3 stacks ≈ **39 SKILL.md files**.
- **Grand total: ~140 SKILL.md files** across 40 skill nodes.

### Build strategy per skill node

**Step 0 — research first.** Before writing, WebSearch for existing high-quality skills, prompt templates, or community examples for the same `{stack, tool}`. Prioritize: Anthropic's official skills repo, well-starred GitHub repos, official tool docs, established QA blogs / conference talks. Note the top 2–3 sources and synthesize their patterns into our skill rather than starting from a blank page. Skip the search only for in-house-only topics (e.g. `accelerator-conventions`).

Then:

1. **Pick a canonical stack** for the first pass (usually the one the user is currently building in, or whichever has the richest tooling — e.g. WireMock → Java, MSW → TypeScript, NBomber → .NET).
2. **Write the canonical skill** fully — frontmatter, examples, anti-patterns.
3. **Port to the other two stacks** by translation: keep section structure, swap code samples, adjust library choices (Testcontainers-java → Testcontainers .NET → Testcontainers-node).
4. **Add `_shared/SKILL.md`** only if there is genuine cross-stack guidance (workload modelling, SLOs, secret hygiene). Don't create empty `_shared` folders.
5. Cross-link siblings in the `description` field's "Do NOT use for" line so the matcher routes correctly.

---

## 5. Cross-cutting conventions to enforce in every new skill

- **Research first.** Before drafting, web-search for existing high-rated Claude skills / agents / community guides for the same tool + stack. Borrow trigger phrasing, section structure, and canonical examples; call out which sources you drew from. Don't reinvent from scratch.
- Frontmatter follows `.skill-template/*.SKILL.md` exactly (`name:`, `description:` with triggers + anti-triggers).
- Honors global rules in `CLAUDE.md` (async, constructor injection, structured logging, secrets policy, test naming).
- Each generator skill ships at least one **runnable example** in its stack (mirroring `webapp-testing/examples/`).
- Each generator has a matching **reviewer** entry under the same root (or extends an existing reviewer).
- Cross-references: every new skill links to its neighbors (e.g. `db-testing` ↔ `test-environments` ↔ `ci-pipelines`).
- Pipeline skills must show: secret handling via OIDC (no PATs), Allure publish, artifact retention, retry policy, **and** how to fail-fast on real failures vs flakes.

---

## 6. First slice to build (recommended starting point)

Build a **vertical slice** — author → run in CI → with DB + email assertions → Allure out — in **one canonical stack first** (.NET, given the Accelerator gravity), then port:

1. `qa/db-testing/testcontainers/dotnet/SKILL.md` — unblocks integration-style API tests away from shared dev DBs.
2. `qa/email-testing/mailpit/dotnet/SKILL.md` — smallest viable email surface; every signup / reset flow can now assert in CI.
3. `qa/ci-pipelines/github-actions/dotnet/SKILL.md` (or `azure-pipelines/dotnet` if that's primary) — codifies shard + Allure + perf-gate once.

Then **port each to `java/` and `typescript/`** before moving to the next phase 1 row. This keeps the library balanced rather than top-heavy in one stack.
