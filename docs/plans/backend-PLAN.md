# backend/ audit — findings & plan of action

**Date:** 2026-07-12
**Scope audited:** `backend/_shared/` (2 skills), `backend/dotnet/` (6 skills + `be-dotnet` agent), `backend/java/` (6 skills + `be-java` agent), `backend/node/` (4 skills + `be-node` agent), plus the `be-dotnet`/`be-java`/`be-node` marketplace wiring.
**Method:** full read of all 21 files (~5,000 lines) against `.skill-template/agent.md`, `CLAUDE.md` global/backend rules, cross-reference resolution, version-awareness, and technical correctness of the code recipes.

---

## Overall assessment

The domain is structurally sound: all three agents are fully brownfield-compliant against `.skill-template/agent.md` (orientation pass, FIX/EXTEND modes, both output contracts, minimal-change rule), the marketplace `skills`/`agents` arrays all resolve on disk, frontmatter naming is uniform (`be-<stack>-*`, `be-shared-*`), all descriptions are comfortably under the 1024-char limit (max 848), the scope fences to `data/` and `qa/` are consistently stated, and the one-pattern-per-problem / severity-table discipline is applied everywhere.

The issues concentrate in four areas: **(1)** the .NET `pattern-guide` skill is a stub relative to its siblings — 3 pattern cards against Java's ~12 and Node's ~13, with its own unchecked coverage checklist admitting it; **(2)** `be-node` has no service-side auth skill (the gap CLAUDE.md itself documents); **(3)** a handful of technically wrong or stale code recipes (the EF Core concurrency example is internally contradictory, `HasCheckConstraint` is obsolete, the Java Strategy recipe breaks under Spring proxies, Prisma tracing is no longer a preview feature); **(4)** consistency drift — two Java auth skills missing the Version-policy section, and dead cross-references to under-construction folders shipping inside the published plugins.

---

## Findings

| # | Severity | Location | Issue | Suggested fix |
|---|----------|----------|-------|---------------|
| F1 | major | `dotnet/skills/reference/SKILL.md` | Covers only **3 of the 15 patterns** on its own "Coverage checklist" (Strategy, Repository, Mediator). The `be-dotnet` agent's Phase 1 loads this skill to make the pattern decision for seven promised patterns — Decorator, Factory, Options, Pipeline, Specification have **no .NET card** (Java has ~12 cards, Node ~13). The checklist openly ships as "expand over time" | Author the missing cards to at least the set the agent description + generator cover (Decorator, Factory, Builder, Specification, Options, Pipeline/CoR, CQRS-full, Unit of Work); then delete the coverage checklist |
| F2 | major | `node/` (whole stack) | **No `auth0`/`cognito` skill** — the documented gap: `be-node` is the only backend plugin without service-side auth, `qa-typescript:test-login-tokens` has no implementation to complement, and `be-node` doesn't bundle `auth/_shared/{auth0-concepts,oidc-concepts}` | Author `backend/node/skills/{auth0,cognito}` (Express: `express-oauth2-jwt-bearer` / `jose`; NestJS: guard + `passport-jwt`; Cognito: `aws-jwt-verify` + the no-`aud`/`token_use`/`client_id` deltas mirroring the dotnet/java siblings; outbound M2M with cached client-credentials tokens). Bundle the two `auth/_shared` concepts skills into `be-node`; update the agent, marketplace description, and CLAUDE.md gap note |
| F3 | major | `dotnet/skills/persistence/SKILL.md` (entity + `OrderConfiguration` examples) | Concurrency recipe is **internally contradictory and broken on Npgsql**: the entity declares `[Timestamp] byte[] RowVersion` (the SQL Server `rowversion` pattern) while `OrderConfiguration` maps that same `byte[]` property to Postgres `xmin` with `HasColumnType("xid")` — Npgsql maps `xmin` as a `uint`, not `byte[]`. The later "For Postgres" block shows the correct `uint` shadow-property mapping, contradicting the config above it | Make the main example provider-consistent (pick one provider end-to-end) and present the other as an explicit delta block; on Npgsql prefer `UseXminAsConcurrencyToken()` / the `uint` property |
| F4 | major | `java/skills/auth0/SKILL.md`, `java/skills/cognito/SKILL.md` | Both **lack the `## Version policy` section** that every other stack-bound backend skill carries (including their dotnet siblings) — a break of the library's version-aware invariant | Add the section (Java release + Spring Boot/Spring Security major detection; note the Boot 2.x/Security 5 fallback would differ and is out of scope) |
| F5 | minor | `dotnet/skills/persistence/SKILL.md:128` | `builder.HasCheckConstraint(...)` on `EntityTypeBuilder` is **obsolete since EF Core 7** — the skill claims to be current EF Core 8/9/10 API | Use `builder.ToTable(t => t.HasCheckConstraint("ck_orders_status", ...))` |
| F6 | minor | `node/skills/persistence/SKILL.md` (OTel section) | Stale Prisma guidance: `previewFeatures = ["tracing"]` — tracing is **GA since Prisma 6.1** (no preview flag). Worth a general currency pass on the Prisma section (e.g. the newer `prisma-client` generator vs `prisma-client-js`) | Drop the preview flag; re-verify the Prisma recipe against the current major |
| F7 | minor | `java/skills/reference/SKILL.md` (Strategy), `java/skills/generator/SKILL.md` (Strategy recipe) | Strategy map keyed on `p.getClass().getAnnotation(Qualifier.class).value()` — **breaks under CGLIB/JDK proxies** (the proxy class doesn't carry the annotation, e.g. once a strategy is `@Transactional` or decorated) and NPEs if a variant misses `@Qualifier` | Replace with Spring-native `Map<String, PricingStrategy>` constructor injection (keyed by bean name) or a `String mode()` method on the interface |
| F8 | minor | 6 handoffs → `devops/environment-config` (both persistence + all four auth skills); `java/skills/cognito` description + handoffs → `auth/cognito-react`; `node/skills/pattern-guide` description + handoffs → React Native (`mobile/react-native`) | Cross-references to **under-construction, un-bundled** targets ship inside the published plugins — dead pointers for a plugin consumer (`devops/` and `react-native` are explicitly fenced off in CLAUDE.md; `cognito-react` is authored but not wired) | Hedge each like `_shared/code-review` already does ("if available in your install") or replace with the plain guidance ("env vars + secret store") |
| F9 | minor | All stack skills' Handoffs sections | Handoffs point at `qa/<stack>/skills/...` **paths**, which don't resolve in an installed `be-*` plugin (qa ships as separate plugins). Agents correctly name peer *agents* instead | In skill handoffs, name the peer agent (`qa-api-<stack>`) rather than the sibling plugin's skill path, or annotate "(separate `qa-<stack>` plugin)" |
| F10 | nit | `dotnet/skills/reference/SKILL.md` (Strategy example) | The consumer hardcodes `[FromKeyedServices("loyalty")]`, undercutting the pattern's run-time-selection point; the generator's keyed-resolver version is correct | Align the reference example with the generator's resolver shape |
| F11 | nit | `dotnet/skills/database-code` (408 L), `node/skills/database-code` (427 L) | Largest skills in the domain; library convention pushes deep sections to `references/details.md`. Not over any hard limit — optional | If touched for F3/F6 anyway, consider moving the Drizzle/TypeORM recipes and bulk-ops sections to `references/` |
| F12 | info | `backend/*/agents/*.md` vs marketplace | Agents name 7 `ep-*` skills for brownfield; the plugins bundle 10 (also `brainstorming`, `delegate-to-subagents`, `parallel-agents`). Matches `.skill-template/agent.md`, so no action — recorded so it isn't "rediscovered" later | None |

**Verified clean (no action):** all three agents template-compliant (two modes, orientation pass, phases table with exit gates, peer list, both output contracts, When-uncertain block); marketplace `skills`/`agents` arrays for `be-*` all resolve on disk; frontmatter names match folders with Triggers + Do-NOT routing on all 16 skills; description lengths 392–848 chars (max well under 1024); version policy present and correct in all dotnet + node skills and java reference/generator/persistence/reviewer (including the "never flag a down-level project" clause); scope fences to `data/` (`_shared/{migrations,slow-query-fixes,schema-design,caching-patterns}` + engine skills) consistently drawn; severity tables and one-pattern-per-problem rule uniform across the three reviewers and `_shared/code-review`.

---

## Plan of action

Run phases in order; each is independently committable. Phases 1–2 are one short session of surgical edits; Phase 3 is content authoring inside one existing file; Phase 4 is the one real build effort (own session, per the one-node-per-session handoff loop).

### Phase 1 — correctness fixes in shipped recipes (F3, F5, F7, F10)
- [ ] `dotnet/skills/database-code`: rewrite the concurrency example provider-consistently — entity + configuration for one provider end-to-end, the other provider as an explicit delta block (`uint xmin` / `UseXminAsConcurrencyToken()` for Npgsql, `[Timestamp]` `rowversion` for SQL Server)
- [ ] `dotnet/skills/database-code`: replace obsolete `HasCheckConstraint` with the `ToTable(t => t.HasCheckConstraint(...))` form
- [ ] `java/skills/pattern-guide` + `java/skills/pattern-writer`: replace the `getClass().getAnnotation(Qualifier.class)` strategy-map keying with `Map<String, PricingStrategy>` bean-name injection (or an interface `mode()` method); note the proxy pitfall
- [ ] `dotnet/skills/pattern-guide`: align the Strategy consumer example with the generator's keyed-resolver shape (drop the hardcoded `[FromKeyedServices("loyalty")]` consumer)

### Phase 2 — consistency & dead-reference pass (F4, F8, F9)
- [ ] Add `## Version policy` to `java/skills/auth0` and `java/skills/cognito` (mirroring the dotnet siblings' wording, keyed to Java release + Boot major)
- [ ] Hedge or replace all 6 `devops/environment-config` handoffs ("env vars + secret store; `devops/environment-config` if available in your install")
- [ ] `java/skills/cognito`: hedge/drop the `auth/cognito-react` pointers (description + handoffs) until that skill ships
- [ ] `node/skills/pattern-guide`: hedge/drop the React Native pointers (description + When-NOT + handoffs) — superseded by `docs/plans/002-mobile-plugins.md`
- [ ] Sweep all `qa/<stack>/skills/...` handoffs across the 16 skills: name the peer agent (`qa-api-<stack>` etc.) or annotate "(separate qa plugin)"

### Phase 3 — close the .NET pattern-reference gap (F1)
- [ ] Author the missing cards in `dotnet/skills/pattern-guide`: Decorator, Factory/Abstract Factory, Builder, Specification, Options, Pipeline/Chain of Responsibility, Unit of Work, CQRS (full) — same card shape as the existing three (Intent / When / When NOT / Minimal example / Common mistakes / Related), examples keyed to net8-compatible API per the skill's own version policy
- [ ] Keep each card lean (the generator holds the scaffolding depth; the reference holds the decision) — target staying under ~450 lines total or split to `references/`
- [ ] Delete the "Coverage checklist" section once coverage matches the agent description
- [ ] Parity check afterwards: confirm every pattern named in the three agent descriptions has a card in its stack's reference skill

### Phase 4 — `be-node` service-side auth (F2) — own session
- [ ] Author `backend/node/skills/auth0/SKILL.md` (`be-node-auth0`): Express lane (`express-oauth2-jwt-bearer`) + NestJS lane (guard + `passport-jwt`/`jose`), RS256/JWKS validation, `permissions`-claim authorization middleware/guard, namespaced custom claims, outbound Client Credentials with cached tokens — mirroring the dotnet/java siblings' section structure (Version policy, Stack, Inputs, Inbound, Outbound, Rules, What NOT to do, Generation steps, Handoffs)
- [ ] Author `backend/node/skills/cognito/SKILL.md` (`be-node-cognito`): `aws-jwt-verify` (the AWS-supported verifier handles `token_use` + `client_id` natively), the deltas-vs-Auth0 table (no `aud`, `scope` claim, `cognito:groups`, hosted-domain token endpoint), outbound M2M via `scope` + Basic auth
- [ ] Update `node/agents/be-node.md`: auth in the description/triggers, skill-loading protocol (+ `auth/_shared/{auth0-concepts,oidc-concepts}`), Phase 2 skills column
- [ ] Update `.claude-plugin/marketplace.json`: add the two skills + the two `auth/_shared` concepts skills to `be-node`; extend the plugin description
- [ ] Update root `CLAUDE.md`: remove the "no `auth0`/`cognito` skill yet (gap…)" note from the Backend catalog and adjust the published-plugins scope line
- [ ] Research-first per the standing rule: check existing highly-rated skills/templates for Express/NestJS JWT + Cognito verification before authoring

### Phase 5 — optional currency & size pass (F6, F11)
- [ ] `node/skills/database-code`: drop `previewFeatures = ["tracing"]`; re-verify the Prisma section against the current major (generator name, tracing registration)
- [ ] If Phase-1 edits touch the two big persistence files anyway, consider extracting Drizzle/TypeORM recipes (node) and the bulk-ops/transactions deep sections (dotnet) into `references/details.md`
