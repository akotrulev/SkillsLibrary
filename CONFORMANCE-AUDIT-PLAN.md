# Conformance-audit rollout — plan of action

**Date:** 2026-07-25
**Goal:** every shipped stack plugin gets the same one-call, read-only **conformance audit** that `fe-react` now has — sweep an existing codebase against *that plugin's own* conventions and save a re-runnable findings report to `docs/audits/`.
**Status:** in progress. **Done:** the shared engine (`ep-standards-audit-engine`), **Phase 3 — `be-dotnet`**, and **Phase 7 — `qa-dotnet`** (all built 2026-07-25, Option B). **Deferred from Phase 1:** the `fe-react` refactor onto the engine — so `fe-react` still carries its own procedure copy + report template, a known temporary duplication. *(Engine registration is no longer deferred: as of 2026-07-26 it ships in all nine `qa-*` / `fe-*` / `be-*` / `devops` plugins.)* **Remaining:** Phase 2 (`fe-blazor`), Phases 4–5 (`be-java`, `be-node`), Phases 6+8 (`qa-java`, `qa-typescript`), Phase 9 (cross-cutting sweep). **Known gaps in the lane as it stands are tracked in §8** — including the five plugins that now carry the engine with no rule set behind it, and the two domains (`data`, `business-analysis`) deliberately left without a conformance lane.
**Scope:** `qa/` (java · dotnet · typescript) · `frontend/` (blazor; react done) · `backend/` (dotnet · java · node). **Out of scope:** `frontend/react-native/` (under construction), `data/`, `business-analysis/`, `observability/` as a standalone (its rules ride inside the backend audits — see Phase 3).

---

## 1. What already exists (the reference implementation)

`frontend/react/skills/standards-audit/` — built 2026-07-25, the template every stack copies:

| File | Lines | Content |
|---|---|---|
| `SKILL.md` | 202 | Fence table (vs `reviewer` / `code-auditor` / `ep-*-audit`) · Mode A/B · artifacts · 5 phases (version gate → applicability matrix → sweep → report → hostile self-review) · evidence rules · severity · read-only contract · output contract · handoffs |
| `references/conformance-checklist.md` | 339 | **19 lettered sections (A–S), 143 checks** — each row = invariant + what a violation looks like + an `rg`/`find` recipe + default severity, with the owning skill named per section |
| `references/report-template.md` | 209 | Round-1 and Round-N report skeletons (movement block, per-section rollups, defect families, deviations table, leverage-ordered priority) |
| `frontend/react/commands/fe-react-audit.md` | 25 | The one-call entry point, Mode auto-detect |

Registered in `.claude-plugin/marketplace.json` under `fe-react` (skill + command); named as a single-skill trigger in `frontend/react/agents/fe-react.md`; catalogued in `CLAUDE.md` + `README.md`.

**Proven-out design decisions worth keeping verbatim in every stack:**

1. **Version gate before any finding** — detect the stack's version lane first; never flag a down-level project for lacking an up-level API. This is the #1 false-positive source.
2. **Applicability matrix before the sweep** — each section is Applicable / N/A / Unknown, and N/A must name the probe that decided it. Stops "no i18n found" findings on a single-locale app.
3. **Grouped findings with a defect family** — 20 sites of one mistake = one finding with a count + 3–5 examples + `+n more (<the grep>)`, not 20 rows.
4. **Deviations ≠ findings** — consistent-and-intentional divergence from a plugin default gets a deviations row + one question for the owner, not a severity.
5. **Read-only contract, hard** — `Write`/`Edit` for the report only; fixes go back through the owning stack agent in a separate run.
6. **IDs are permanent** — `<SectionLetter><CheckNumber>` (`B3`, `M1`), so a finding ID names the rule it breaks and rounds stay comparable.

---

## 2. Architecture decision — **RESOLVED: Option B** (implemented for the engine + `be-dotnet` + `qa-dotnet`)

The **procedure** (modes, artifacts, evidence rules, severity, report templates, self-review) is 100% stack-agnostic — ~55% of the react `SKILL.md` plus the whole `report-template.md`. The **checklist** is 100% stack-specific. Three ways to handle that:

| | Option A — self-contained per stack | **Option B — shared engine + per-stack checklist (recommended)** | Option C — per-domain engine |
|---|---|---|---|
| Shape | Copy the react skill 7×, edit the checklist | One `engineering-practices/standards-audit-engine/` engine (`ep-standards-audit-engine`) holding procedure + report template; each stack ships a thin `SKILL.md` + its checklist | An engine each in `qa/_shared/`, `backend/_shared/`; frontend has no `_shared`, so blazor/react stay self-contained |
| New skill folders | 7 | 8 (1 engine + 7 stacks) | 9 (2 engines + 7 stacks) |
| Procedure copies to maintain | **8** | **1** | 3 |
| Path resolution in installed plugins | Trivially fine | **Fine — `engineering-practices/*` is already bundled into all eight `qa-*`/`fe-*`/`be-*` plugins** (verified in `marketplace.json`) | Fine within a domain |
| Fits existing precedent | The library's "self-contained plugin" doctrine | `ep-spec-vs-code-audit` + `ep-feature-audit` already live there — this is the **third audit lane** | `qa/_shared/performance` + tool skill; `backend/_shared/pattern-guide` + stack skill |
| Risk | Procedure drift across 8 files; a fix to the evidence rules has to land 8× | Engine's description could out-trigger the stack skills → must carry an explicit "do NOT invoke directly" clause (the `vendor/*` lesson, `frontend/PLAN.md` F4) | Two engines to keep in sync; frontend left out |

**Chosen: Option B** (implemented 2026-07-25 for the engine, `be-dotnet`, and `qa-dotnet`; the react refactor is still outstanding). One procedure, eight checklists. `engineering-practices/` is the only folder already bundled into every stack plugin, it already hosts the sibling audit lanes, and the third-lane framing is clean: **SPEC lane** (code vs the user's spec) · **FEATURE lane** (spec-less behaviour trace) · **CONVENTION lane** (code vs the plugin's fixed rule set).

**Consequences to accept if Option B is chosen:**
- `fe-react`'s skill is refactored onto the engine in Phase 1. Its **public surface does not change** — same skill name (`fe-react-standards-audit`), same command (`/fe-react-audit`), same report path and ID grammar.
- `ep-*` skill count goes 14 → 15 everywhere it's stated (`CLAUDE.md`, `README.md`, plugin descriptions).
- The engine gets a hard "loaded, not invoked" description clause, and no trigger phrases a user would type.

**Rejected sub-option worth recording:** a middle `_shared` layer holding "cross-stack backend rules" / "cross-stack QA rules". Looked attractive, but the rules that seem shared aren't: `.Result` vs `.block()` vs a floating promise; `Thread.Sleep` vs `waitForTimeout` vs implicit-wait soup; field `@Autowired` vs property injection vs a module singleton. Each stack needs its own *violation shape* and its own *grep recipe*, so the row can't be shared — only the sentence above it. Not worth a third file in the load path.

---

## 3. Naming & wiring conventions (fixed — apply identically to all 7)

| Thing | Pattern | Examples |
|---|---|---|
| Skill folder | `<domain>/<stack>/skills/standards-audit/` (qa/frontend) · `backend/<stack>/skills/standards-audit/` | `qa/java/skills/standards-audit/` |
| Frontmatter `name:` | `<plugin-prefix>-standards-audit` | `qa-java-standards-audit`, `fe-blazor-standards-audit`, `be-node-standards-audit` |
| Checklist | `references/conformance-checklist.md` | — |
| Command file | `<domain>/<stack>/commands/<plugin>-audit.md` | `qa/java/commands/qa-java-audit.md` |
| Command name | `/<plugin>-audit` | `/qa-java-audit`, `/fe-blazor-audit`, `/be-dotnet-audit` |
| Report path (in the target repo) | `docs/audits/<NNN>-<plugin>-conformance-r<N>.md` | `docs/audits/007-be-java-conformance-r1.md` |
| Finding ID | `<SectionLetter><CheckNumber>` — permanent across rounds | `G7`, `M1` |
| Engine skill | `engineering-practices/standards-audit-engine/` → `ep-standards-audit-engine` | loaded, never invoked directly |

**Per-stack wiring checklist (repeat every phase):**
- [ ] Add the skill path to the plugin's `skills` array in `.claude-plugin/marketplace.json`
- [ ] Add the command path to the plugin's `commands` array
- [ ] Add a **single-skill trigger** paragraph to the stack's primary agent(s), stating: loads the audit alone, read-only, no phase runs, fixes are a separate FIX/EXTEND run, and the three-way fence
- [ ] Mention the audit in the plugin `description` (one clause, watch the 1024-char cap)
- [ ] Update the domain catalog in `CLAUDE.md` (skill counts + the Test/review bullet + the commands sentence)
- [ ] Update `README.md` (plugin bullet, the commands table for that plugin, the status table row)

**QA agent note:** each qa stack has **six** agents (`qa-api`, `qa-ui`, `qa-mobile`, `qa-performance`, `qa-llm`, `qa-bdd`) plus the shared `qa-test-case-designer` / `qa-security` / `qa-cicd-*` / `qa-reporting-*`. Do **not** add the trigger paragraph to all of them. Put it in `qa-api-<stack>` and `qa-ui-<stack>` only (the two most likely to be asked "audit our suite"), and rely on `/qa-<stack>-audit` as the deterministic path.

---

## 4. Per-stack section designs

Each is a first-cut section list to review, not final. Target 12–20 sections, 100–150 checks — the react build landed at 19/143, which felt right: dense enough to be a real sweep, short enough to read.

**One cross-cutting rule every stack's checklist must carry** (already landed in `be-dotnet` §N, `fe-react` §S, `qa-dotnet` §B): the global **Comments** rules in `CLAUDE.md` — no inline comments; a doc comment only where the name genuinely cannot carry the meaning, and only on a complex flow; stale comments are `major`. Put it in the structure/hygiene section rather than inventing a letter for it, and keep the reporting convention the three landed sections use: **the "no inline comments" check is reported as one finding family** (count + 3–5 representative `file:line`s + the worst offender + one fix direction), while each **stale** comment is its own finding, because each is a distinct false statement.

### 4.1 `fe-blazor` — 20 sections (the Blazor twin of react's 19)

Same spine, Blazor mechanics. `javascript-calls` is the one section with no react counterpart.

| Letter | Section | Owning skill(s) | Notes / signature checks |
|---|---|---|---|
| A | Build health & version lane | `project-setup` | TFM detection (net8/9/10); never flag down-level for `[PersistentState]`/`NotFoundPage`/`AddValidation()`/`ReconnectModal` |
| B | Render modes & the interactivity boundary | `reference`, `project-setup` | `@rendermode` **never hardcoded in a reusable component**; static SSR default; prerender double-fetch; `[PersistentState]` (net10) vs manual `PersistentComponentState` (net8/9) |
| C | Routing & navigation | `generator`, `ui-rules` | Real anchor / `NavLink`, never click-handler-only `NavigateTo`; `NotFoundPage` (net10) vs `UseStatusCodePagesWithReExecute` |
| D | State management | `state-management` | Scoped state containers + `Changed` events; **no static mutable state**; **background→UI only via `InvokeAsync`** |
| E | Data access & realtime | `data-fetching`, `realtime` | WASM/HTTP vs interactive-SSR service injection; `IHttpClientFactory` typed clients; streaming rendering; circuit-as-WebSocket vs SignalR client; subscription disposal |
| F | Forms & validation | `forms` | `EditForm` + FluentValidation; `OnValidSubmit`; `<ValidationMessage For>` per field; server errors surfaced |
| G | Component library & styling | `component-library`, `styling` | Library theme owns the library; **CSS isolation + `::deep`**, no global-stylesheet dumping; tokens; authored dark palette |
| H | Responsive & motion | `responsive-design`, `motion` | Breakpoint contract + **C# mirror**; `prefers-reduced-motion` hard floor |
| I | Accessibility | `accessibility` | Semantic before ARIA; focus under enhanced navigation; ARIA in custom components |
| J | Error resilience | `error-handling` | `ErrorBoundary`; **reconnection UX**; three-state regions; Polly on outbound |
| K | Performance | `performance` | `@key` on lists; `ShouldRender`; WASM startup budget; Server circuit scale; no chatty interop in render |
| L | SEO & discoverability | `seo` | Static SSR for public pages; meta/OG; real 404; sitemap |
| M | Testability (`data-testid`) | `test-ids` | Same convention as react — PascalCase dot-separated, static row locators, no collisions |
| N | UI conventions | `ui-rules` | Object-naming confirmations; deterministic sort; humanized display values |
| O | Component tests | `component-testing` | bUnit v2, logic-bearing components only; E2E belongs to `qa-ui-dotnet` |
| P | Localization | `localization` | `IStringLocalizer`/`.resx`; **per-render-mode culture pipeline** (Server `RequestLocalization`+cookie vs WASM satellite assemblies/ICU); `@bind:culture`; RTL |
| Q | PWA / offline | `installable-offline-app` | WASM-only installable+offline; **Server can only be installable** — flag an offline claim on a Server app |
| R | Auth wiring | `auth/auth0-blazor` | `AuthorizeView` + cascading auth state; server-side enforcement, not UI-only; no tokens in `localStorage` |
| S | **JS interop discipline** | `javascript-calls` | `IJSObjectReference` disposed (`IAsyncDisposable`); **never called in `OnInitializedAsync`**; `JSDisconnectedException` handled; no-interop-where-C#-suffices |
| T | Project structure, nullability, secrets & comments | `project-setup` | `<Nullable>enable</Nullable>`; no secrets in `appsettings.json`; DI registration hygiene; constructor injection only; **no inline comments** — XML doc only on complex flows where the name can't carry the meaning; no stale comments (see the global **Comments** rules) |

### 4.2 `be-dotnet` · `be-java` · `be-node` — 14 sections (one shared spine, three sets of mechanics)

The spine is identical; every row's *violation shape* and *recipe* is stack-specific. Section L is the payoff of observability being bundled into the `be-*` plugins.

| Letter | Section | Owning skill(s) | `be-dotnet` | `be-java` | `be-node` |
|---|---|---|---|---|---|
| A | Build health & version lane | `project-setup`-equivalent, `reference` | TFM; EF Core major matches TFM | JDK release + Boot BOM | Node major (**20 is EOL — flag, don't target**); `strict` |
| B | Pattern application | `_shared/reference`, `reference` | Repository wrapping EF for no reason; premature CQRS/MediatR | Repository wrapping Spring Data | Class hierarchies where discriminated unions fit |
| C | DI & composition | `generator`, `reviewer` | Service locator; captive dependency (singleton→scoped) | Field `@Autowired`; `@Component` scanning sprawl | Module-level singletons; import-time side effects |
| D | Async & concurrency | `code-review` | `.Result`/`.Wait()`/`GetAwaiter().GetResult()`; missing `CancellationToken` | `.block()` on reactive; blocking in `@Async` | Floating promises; `.then().catch()` chains in new code; unawaited async |
| E | State & immutability | `_shared/reference` | `static` mutable; records over classes | `static` mutable; `final` where it fits | Module mutable state; `readonly` |
| F | Layering & boundaries | `_shared/reviewer` | EF entities returned from controllers | JPA entities on the API surface | Prisma types leaking to route handlers |
| G | Persistence — ORM mechanics | `persistence` | `DbContext` lifetime; N+1; missing `AsNoTracking`; migrations; optimistic concurrency; bulk ops | `@Transactional` boundaries; N+1 / missing fetch joins; `@Version`; Flyway | Prisma client lifetime; N+1 / missing `include`; migration hygiene |
| H | API contract & validation | `generator` | FluentValidation/DataAnnotations at the boundary; `ProblemDetails`; honest status codes; bounded pagination; idempotency on retryable writes | Bean Validation; `@ControllerAdvice` error shape | **Zod at every boundary**; `Result<T,E>` |
| I | Service-side auth | `auth0`, `cognito` | `AddJwtBearer` issuer/audience/signing-key validation; RBAC policies; cached M2M | Resource Server + `@PreAuthorize` | **Gap — no auth skill yet** (`backend/PLAN.md` F2). Mark section N/A with a pointer, or gate this phase on F2 |
| J | Error handling & resilience | `reviewer` | Swallowed exceptions; internals leaked in responses; Polly retry/timeout/CB | Resilience4j | Typed errors, no `throw` strings |
| K | Configuration & secrets | `reviewer` | No secrets in `appsettings.json`; typed `IOptions` | No secrets in `application.yml`; `@ConfigurationProperties` | No committed `.env`; validated env schema |
| L | Observability | `observability/*` (bundled) | **Bounded metric cardinality** (per-record ids are span attributes, never metric labels) · **Collector as the seam** (no direct-to-backend exporters) · structured logging with **message templates, never interpolation** · trace-context propagation · log↔trace correlation · health endpoints. Serilog / SLF4J+Logback / pino per stack |
| M | Testability & contract tests | `reviewer` | Every public API has a contract test (coordinate with the `qa-api-<stack>` peer — the audit reports absence, the peer writes them); seams injectable; no test-only hooks in prod code |
| N | Project structure, type safety & comments | `reference` | Nullable enabled; no inline comments; XML doc only on complex flows | No raw generics; no inline comments; Javadoc only on complex flows | `strict: true`, no `any`; no inline comments; TSDoc only on complex flows |

### 4.3 `qa-java` · `qa-dotnet` · `qa-typescript` — 14 sections (**audits the test suite, not the app**)

**The critical fence, stated in every one of the three skills:** this audits **test code** against the qa conventions. The application under test belongs to `fe-*` / `be-*` — findings about the app are out of scope and get named as a handoff, not a finding. (Exception: a *missing* `data-testid` the suite has to work around is a finding **about the suite's locator strategy**, and feeds `missing-testids.md`.)

Relationship to the existing reviewers: `api-test-author/reviewer`, `ui-test-author/reviewer`, `bdd-reviewer`, and the `qa/_shared/performance` review checklist are the **per-family, per-diff** review; this is the whole-suite, saved, re-runnable roll-up of their rules — the same relationship `fe-react-code-review` has to `fe-react-standards-audit`.

| Letter | Section | Owning skill(s) | Signature checks |
|---|---|---|---|
| A | Build health & suite lane | stack scaffold skills | Runner + build tool + versions; the suite compiles and actually runs; disabled/ignored tests without a ticketed reason |
| B | Test naming, structure & comments | global test + **Comments** rules | `Should_X_When_Y` / `Given_When_Then`; **one logical assertion**; **no conditional logic** (`if`/`for` driving assertions → parameterized instead); AAA shape; **no inline comments — including `// Arrange`/`// Act`/`// Assert` banners** (the name and the AAA shape are the explanation); the only three permitted are a linked defect id, a recorded instructed deviation, and the source of a domain-fixed magic value |
| C | Independence & isolation | global test rules | Any test alone, in any order; no shared mutable state; no ordering dependency; parallel-safe |
| D | Waits & timing | `ui-test-author/*` | **No `Thread.Sleep` / `waitForTimeout` / implicit-wait soup**; explicit condition waits (Awaitility / `expect` polling / `WebDriverWait`) |
| E | Page / screen objects | `page-object-design`, `ui-test-author/*`, `mobile-screen-objects` | **Expose intent, not selectors**; mechanics + waits live in the POM; no selectors in tests or step definitions; no 900-line god-page |
| F | Locator hygiene | `page-objects-from-url`, `mobile-screen-explorer` | `data-testid` / accessibility-id first; no brittle XPath chains; no id/GUID/index embedded in a locator; a `missing-testids.md` was produced, not worked around |
| G | Test data | `test-data-builder`, `data-driven-testing` | Builders/ObjectMother at 4+ fields; no duplicated inline literals; deterministic cleanup; no prod data; no shared fixture mutated across tests |
| H | API test layering | `api-test-author/*`, `api-client-writer`, `api-models` | DTO + typed client + test layers separated; no raw HTTP in test bodies; status **and** body asserted; auth via `test-login-tokens`, never hardcoded creds |
| I | Assertion quality | reviewers | Behaviour not implementation; no assert-nothing tests; no snapshot-only standing in for assertions; negative + boundary cases present |
| J | External verification | `db-testing/*`, `messaging-testing`, `email-testing`, `file-storage-testing` | Read-only assertion SQL guardrails; **Testcontainers over a shared env, never H2 substituting for the real engine**; safe cleanup; no leaked connections; polling not sleeping |
| K | Config, secrets & environments | `ci-conventions` | No hardcoded URLs/creds; env-driven config; **no secrets committed**; per-environment profile |
| L | Reporting & flake management | `test-reports`, `flaky-test-quarantine` | Allure wired; tests tagged by severity/feature/owner/issue; **flakes quarantined-and-tracked, never masked by a blanket retry** |
| M | CI wiring | `ci-pipelines`, `ci-conventions` | Shard matrix; PR vs nightly lanes; artifacts published; **no retries hiding flakes**; OIDC not long-lived PATs; the perf/security gates the domain owns |
| N | Coverage shape | `test-strategy`, `quality-metrics`, `test-quality-check` | Contract test before integration tests; pyramid not inverted; critical flows covered; **mutation score where the tool exists** (PIT / Stryker.NET — not TS, no sibling built) |

---

## 5. Phases

One phase per session (per the established handoff loop). Each phase is independently committable and ends with the wiring checklist from §3 applied for that plugin.

### Phase 0 — Sign-off *(no code)*
- [ ] Review §2 and pick Option A / B / C
- [ ] Review the section designs in §4; add/remove sections **before** any checklist is written (letters are permanent once a report exists in the wild)
- [ ] Answer the open questions in §7

### Phase 1 — Extract the engine + refactor `fe-react` — ⚠️ **HALF DONE**
- [x] Create `engineering-practices/standards-audit-engine/SKILL.md` (`ep-standards-audit-engine`) — Mode A/B, artifacts, the 5 phases, evidence rules, severity, read-only contract, output contract, hostile self-review. **Description carries an explicit "loaded by `<stack>-conformance-audit`; do NOT invoke directly" clause** and no user-typed trigger phrases
- [x] Write the stack-agnostic report templates at `engineering-practices/standards-audit-engine/references/report-template.md` (react's copy left in place for now → **duplication to resolve**)
- [ ] Slim `frontend/react/skills/standards-audit/SKILL.md` to the stack layer: announce, load-the-engine pointer, React/Next version-gate probes, applicability matrix, section index, fence table, handoffs
- [x] Register `./engineering-practices/standards-audit-engine` in `qa-dotnet` + `be-dotnet`
- [x] Register it in the remaining stack plugins — **done 2026-07-26**, ahead of their audits landing: it now ships in all nine of `qa-{java,dotnet,typescript}` · `fe-{blazor,react}` · `be-{dotnet,java,node}` · `devops`. Harmless where no stack audit exists yet (the engine's description forbids direct routing, so it sits inert until a `standards-audit` skill loads it) and it removes a wiring step from every remaining phase. Excluded from `data` and `business-analysis`, which bundle no `ep-*` skills at all
- [ ] Delete `frontend/react/skills/standards-audit/references/report-template.md` once react points at the engine's copy
- [ ] Verify `/fe-react-audit` still resolves end-to-end and the public surface is unchanged (skill name, command, report path, ID grammar)
- [x] `ep-*` count 14 → 15 noted in `CLAUDE.md` + `README.md`, with the partial-rollout caveat stated
- [x] Revisit that caveat once all plugins carry the engine — **done 2026-07-26**; the caveat now reads "ships in all nine, inert until a stack audit loads it" rather than "only where an audit exists"
- **Gate:** react audit reads engine + checklist and nothing is lost from the 202-line original.

### Phase 2 — `fe-blazor`
- [ ] `frontend/blazor/skills/standards-audit/{SKILL.md,references/conformance-checklist.md}` per §4.1 (20 sections, ~140 checks)
- [ ] `frontend/blazor/commands/fe-blazor-audit.md`
- [ ] Single-skill trigger in `frontend/blazor/agents/fe-blazor.md`
- [ ] Wiring checklist (§3)
- **Gate:** every TFM-keyed row tagged net8/9/10; section Q flags an offline claim on a Server app; section S's disposal checks have working recipes.

### Phase 3 — `be-dotnet` ✅ **DONE 2026-07-25**
- [x] `backend/dotnet/skills/standards-audit/*` per §4.2 — **14 sections A–N, 141 checks**
- [x] `backend/dotnet/commands/be-dotnet-audit.md`; single-skill trigger in `backend/dotnet/agents/be-dotnet.md`
- [x] Section L (observability) — 16 checks against the bundled `observability/{opentelemetry,structured-logging}-dotnet`, incl. both invariants (L5 bounded cardinality = blocker, L6 Collector-as-seam)
- [x] Wiring checklist (marketplace skill + command + engine, description clause, CLAUDE.md, README.md)
- **Note:** G9 encodes the `backend/PLAN.md` F3 lesson as a **blocker** check — a `[Timestamp] byte[]` token mapped to Postgres `xmin` (Npgsql maps `xmin` as `uint`) is provider-contradictory.
- **Gate:** the spine (A–N) is written to be reusable by Phases 4–5 with only mechanics swapped; section G's concurrency rows avoid the provider contradiction recorded in `backend/PLAN.md` F3.

### Phase 4 — `be-java`  ·  ### Phase 5 — `be-node`
- [ ] Same deliverables, mechanics swapped per §4.2's columns
- [ ] **be-node decision:** section I (service-side auth) has no skill to audit against (`backend/PLAN.md` F2). Either mark it N/A with a pointer to the gap, or gate Phase 5 on authoring `backend/node/skills/{auth0,cognito}` first — decide at Phase 0
- **Gate:** all three backend checklists share section letters A–N so a polyglot shop can compare reports across services.

### Phase 7 — `qa-dotnet` ✅ **DONE 2026-07-25**
- [x] `qa/dotnet/skills/standards-audit/*` per §4.3 — **14 sections A–N, 151 checks**
- [x] `qa/dotnet/commands/qa-dotnet-audit.md`
- [x] Trigger paragraph in `qa-api-dotnet` + `qa-ui-dotnet` **only** (§3) — the other four stack agents left alone as designed
- [x] The **test-suite-not-the-app** fence stated in the skill (its own top-level section), the checklist header, and the command
- [x] Section N mutation row tagged **[Stryker.NET]** so it stays N/A where the tool isn't configured
- [x] Wiring checklist
- **Note:** tool-lane tags (`[NUnit]` `[PW]` `[Sel]` `[Appium]` `[RestSharp]` `[Reqnroll]` `[TC]`) make every tool-bound row N/A rather than violated on a suite that doesn't use that tool.

### Phase 6 — `qa-java`  ·  ### Phase 8 — `qa-typescript`
- [ ] `qa/<stack>/skills/standards-audit/*` — **port `qa/dotnet`'s A–N spine**, swapping mechanics (TestNG/Cucumber-JVM/RestAssured · Vitest/playwright-bdd/WebdriverIO) and re-tagging the tool lanes
- [ ] `qa/<stack>/commands/qa-<stack>-audit.md`
- [ ] Trigger paragraph in `qa-api-<stack>` and `qa-ui-<stack>` **only** (§3)
- [ ] The **test-suite-not-the-app** fence stated in the skill, the checklist header, and the command
- [ ] Section N: the mutation row is java/dotnet only — TS has no StrykerJS sibling skill; mark it N/A rather than inventing a rule
- [ ] Register the engine (`./engineering-practices/standards-audit-engine`) in that plugin's `skills` array
- **Gate:** section letters A–N match `qa/dotnet` verbatim so reports compare across stacks; no row audits application code; the relationship to the existing family reviewers is stated, not duplicated.

### Phase 9 — Cross-cutting sweep & docs
- [ ] Parity pass across all 8 checklists: same row grammar, same severity semantics, same version-gate tagging, same `[lane]` tag style
- [ ] Every skill description **≤ 500 chars** — superseded 2026-07-25: the ≤1000 target here collided with `TOKEN-OPTIMIZATION-PLAN.md`'s ≤500 budget, and the ≤1000 pass re-inflated qa-dotnet's always-on cost by 64% (7,631 → 12,500 tok). **≤500 is now the single library-wide budget**, enforced by `tools/token-audit.py`. Keep the fence, drop the padding: no repeated agent-routing sentence, no cross-stack sibling clauses (those siblings aren't registered in a single-plugin install), fence named against same-plugin siblings only. The 1024 hard cap is unchanged; 500 is the budget under it.
- [ ] Link check: every relative path in every new file resolves
- [ ] `marketplace.json` — all 8 plugins' `skills`/`commands` arrays resolve on disk; JSON valid; **edit as text, not via a JSON re-dump** (a re-dump normalizes non-ASCII escaping across unrelated descriptions)
- [ ] `CLAUDE.md` — per-domain catalogs, skill counts, the commands sentences, and one paragraph in the engineering-practices catalog describing the CONVENTION lane alongside SPEC and FEATURE
- [ ] `README.md` — plugin bullets, the three commands tables, the status table
- [ ] `engineering-practices/agents/code-auditor.md` — one paragraph: the CONVENTION lane exists, it belongs to the stack plugins, hand off to `/<plugin>-audit` when the ask is "does this follow our conventions" rather than a spec/feature audit
- **Gate:** `grep -c` counts in the docs match reality; a fresh reader can pick the right lane from the fence tables alone.

---

## 6. Effort estimate

| Phase | Scope | Est. |
|---|---|---|
| 0 | Review + decisions | 30 min (yours) |
| 1 | Engine extraction + react refactor + 8 registrations | 1 session |
| 2 | fe-blazor (20 sections) | 1 session |
| 3–5 | backend ×3 (14 sections each; 4 and 5 are faster once the spine exists) | 1 session each; 3 and 4+5 could combine |
| 6–8 | qa ×3 (14 sections each) | 1 session each; 7 and 8 faster after 6 |
| 9 | Sweep + docs | 0.5 session |
| | **Total** | **7–9 sessions** |

Per stack the deliverable is ~3 files / ~450 lines (SKILL.md ~90 · checklist ~300 · command ~25) plus ~6 small edits.

---

## 7. Open questions for review

1. **Architecture** — Option A, B, or C (§2)? Everything downstream depends on this.
2. **Validation targets** — is there a real repo per stack to dry-run each audit against once written? Without one, the grep recipes are unproven; with one, each phase gains a real Round-1 report as its acceptance evidence. If you have candidates, name them at Phase 0.
3. **be-node section I** — mark auth N/A with a pointer, or author `backend/node/skills/{auth0,cognito}` first (`backend/PLAN.md` F2)?
4. **QA trigger placement** — `qa-api` + `qa-ui` only (recommended), or all six stack agents?
5. **Section-count ceiling** — react landed at 19/143 and reads well. Cap the others at ~20/150, or let backend/qa run leaner (14/110 as designed)?
6. **`data` and `business-analysis`** — out of scope now, and tracked as **gap G2** (§8). Worth a follow-up plan later? (`data` would audit schema/DDL/index conformance per engine; `business-analysis` would audit KB health.) Note that adding the engine to those two plugins would not help on its own — they'd still have no rule set, and it would be the only `engineering-practices/` entry either one carries.
7. **`frontend/react-native`** — confirm it stays deferred until the stack itself ships.

---

## 8. Known gaps in the CONVENTION lane *(as of 2026-07-26)*

The engine now ships everywhere it can, which makes the remaining gaps purely about **rules**, not wiring. Each row says what is missing, what it costs today, and what closes it.

| # | Gap | Where it bites | Closes when |
|---|---|---|---|
| **G1** | **Five plugins carry the engine but have no rule set** — `qa-java`, `qa-typescript`, `fe-blazor`, `be-java`, `be-node` ship `ep-standards-audit-engine` with no `standards-audit` skill to supply sections. The engine is inert there (no rules, no command, description forbids direct routing), so the failure mode is *absence*, not misfire: a user on those stacks has no conformance lane and nothing tells them why | A `be-java` user asking "audit my service against the plugin conventions" gets the `code-auditor` SPEC/FEATURE lanes or a one-diff `code-review` — neither answers the question asked | Phases 2, 4, 5, 6, 8 land their `standards-audit` skills. Wiring is already done for all of them |
| **G2** | **`data` and `business-analysis` have no conformance lane at all** — deliberately excluded from the engine because neither plugin bundles any `ep-*` skill (`business-analysis` inlines the brownfield discipline instead of referencing skills its plugin can't resolve). Adding the engine alone would not help: they'd still have no rules, and it would be the only `engineering-practices/` entry in those plugins | `data` has 8 engines' worth of hard rules (id strategy, tenancy isolation, index shape, migration safety) and no way to sweep a repo against them; `business-analysis` has no KB-health check | A follow-up plan decides scope — see open question §7.6. Until then this is a **stated non-goal**, not an oversight |
| **G3** | **`fe-react` still duplicates the engine** — it carries its own copy of the procedure *and* `references/report-template.md`, predating the extraction. Two copies of one contract can drift, and a fix to the engine silently misses react | A future engine change (severity semantics, ID grammar, rollup rule) applies to 3 of the 4 authored audits | Phase 1's remaining items: slim the skill to the stack layer, delete the duplicate template, re-verify `/fe-react-audit` end-to-end |
| **G4** | **`devops` diverges in shape** — its 12 rule sections live inside the `devops-auditor` **agent**, not a `standards-audit` skill, because devops is outside this plan's scope (§ Scope) and its "which rules apply" question is answered by the same tool-stack confirmation gate the `devops-engineer` sibling runs. Correct for devops, but it means the lane has two shapes | Anyone generalising "every conformance audit is a skill named `<plugin>-standards-audit`" is wrong once. Section-to-owning-skill traceability still holds; only the container differs | Left as-is unless devops joins the plan. If it does, extract the sections to `devops/standards-audit/` and keep the agent as the entry point |
| **G5** | **No validation target for any audit** — open question §7.2 is still unanswered, so every checklist's grep recipes and severity calls are unproven against a real repo | A section can look rigorous and produce zero or garbage findings on first contact; the react/dotnet/qa checklists have never produced a Round-1 report on real code | A repo per stack is named at Phase 0 and each phase gains a real Round-1 report as acceptance evidence |

**The through-line:** G1 and G3 are scheduled work with owners (the phases). G2 and G4 are deliberate scope decisions that should stay written down so they aren't rediscovered as bugs. G5 is the one that could invalidate work already marked done.

---

## 9. Risks & fences

| Risk | Mitigation |
|---|---|
| **Checklist drifts from the skills it audits** | Every section names its owning skill and the skill wins on conflict; a disagreement is itself a reportable finding. Any future skill edit that changes a hard rule should touch that section's row — worth adding to the domain PLANs |
| **Engine out-triggers the stack skills** (the `vendor/*` failure mode) | Explicit "do NOT invoke directly" clause, no user-typed triggers in the engine description |
| **Four overlapping audit lanes confuse users** | The three-way fence table is mandatory in every stack skill: `reviewer` (one diff, inline) · `standards-audit` (whole repo vs the plugin's rules, saved, rounds) · `code-auditor`/`ep-*-audit` (vs the user's spec, or a spec-less feature trace) |
| **Version-lane false positives** | Version gate is Phase 0 of every run and every version-keyed row carries a lane tag |
| **Report bloat → ignored reports** | ~30-finding cap with per-family overflow; grouped findings; leverage-ordered priority table |
| **An audit that quietly edits code** | Read-only contract restated in the skill, the checklist header, and the command |
| **Shell-recipe bugs** | No `$RG`-style variables holding quoted globs (they don't re-parse in bash — hit and fixed during the react build). Recipes use plain `rg -n "<pattern>" $SRC` with a `grep -rn` fallback line |
| **QA audit drifting into the app** | The test-suite-not-the-app fence stated three times per stack (skill, checklist, command) |

---

## 10. Definition of done

- [ ] `/qa-java-audit` · `/qa-dotnet-audit` · `/qa-typescript-audit` · `/fe-blazor-audit` · `/fe-react-audit` · `/be-dotnet-audit` · `/be-java-audit` · `/be-node-audit` all run one-call, read-only, and save a report to `docs/audits/`
- [ ] All eight share one procedure (Option B), one severity table, one evidence policy, one ID grammar, and Mode A/B rounds
- [ ] Each stack's checklist is traceable to its own skills — every section names an owner
- [ ] The fence between `reviewer`, `standards-audit`, and `code-auditor`/`ep-*-audit` is stated in all eight
- [ ] `marketplace.json`, `CLAUDE.md`, and `README.md` agree with what's on disk (counts, commands, paths)
