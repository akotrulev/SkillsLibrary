# Unit-testing lane — plan of action (backend + frontend)

**Date:** 2026-08-09 · *frontend track added 2026-08-09*
**Goal:** close the library's one structural test-lane hole — **nothing owns in-process, no-I/O tests of non-rendering logic**. Backend has no test skill at all; frontend has one that covers rendering and explicitly disclaims everything else. Both dead-end in the same sentence ("plain NUnit otherwise" / "a plain Vitest test on the function").
**Status:** **COMPLETE — all phases delivered 2026-08-09.** Phase 0 resolved (every recommended option taken) · Phases 1–3: three new skills (`be-{dotnet,java,node}-unit-testing`), each wired into its agent as a new Phase 3, each registered, **each verified by a real compile-and-run** · Phase 4: planner routing maps, catalogs, plugin descriptions · Phases 5–7: both FE `component-testing` skills rescoped to own the non-rendering half, the react audit's §O glob blindness fixed and 4 rows added, both FE agent gates extended.

**Verification results (the point of the standing rule below):**

| Phase | Verified with | Result | Defect it caught |
|---|---|---|---|
| 1 dotnet | scratch net10.0 solution, CPM, nullable on (SDK 10.0.301) | **10/10 pass, 0 warnings** | `Arg.Is<T>(e => e.X)` raises **CS8602** — the flagship snippet violated the skill's own 0-warning gate |
| 2 java | `javac -Xlint:all` + JUnit Platform Console (JDK 21, Mockito 5.14.2, AssertJ 3.26.3) | **9/9 pass, lint-clean** | none in the skill — and it *proved* the documented `BigDecimal` trap (`isEqualByComparingTo` passes where `isEqualTo` fails on `2.50` vs `2.5`) |
| 3 node | Vitest 3.2.7 + `tsc --noEmit` strict (Node 22) | **11/11 pass, tsc clean** | Vitest's own types need `lib: ESNext` + `@types/node`, or `tsc --noEmit` fails inside `node_modules` — which would have blocked the agent's Phase-3 gate on every fresh setup |

**Standing rule this plan adopts:** every stack phase ends with a **runnable** verification of its own recipes, not a review of them. Two of the three defects above were invisible to reading.


**Scope — two tracks:**
- **Track A — backend:** `backend/{dotnet,java,node}` — 3 new skills, 3 agent rewires, 1 checklist extension.
- **Track B — frontend:** `frontend/{blazor,react}` — **0 new skills**; 2 skill rescopes, 2 agent gate edits, 1 checklist extension (§3b explains why the answer differs).

**Out of scope:** `qa/` (its altitude is unchanged — verified: 181 `SKILL.md` files, 26 agents, none authors unit tests), `frontend/react-native/` (under construction), `observability/`, `data/`, `devops/`.

---

## 1. The gap (verified 2026-08-09)

### 1a — Backend: no skill authors unit tests at all

| Where | What's there | Verdict |
|---|---|---|
| `backend/<stack>/skills/` | dotnet: `auth0` `code-review` `cognito` `database-code` `pattern-guide` `pattern-writer` `standards-audit` · java: same −`standards-audit` · node: 4 skills | **No test-authoring skill in any stack** |
| `backend/dotnet/skills/pattern-writer/SKILL.md:27` | "Scaffolding tests against a generated pattern → use `qa/dotnet/skills/api-test-author/writer` if it's API-facing, **plain NUnit otherwise**" (also `:45`, `:203`) | "Plain NUnit" is the entire guidance — no project setup, no seam/double policy, no fixture conventions |
| `backend/node/skills/pattern-writer/SKILL.md:307` | "Tests (Vitest by default) alongside (`*.spec.ts`)" | One line |
| `backend/java/skills/pattern-writer/SKILL.md:262` | "A **TestNG** test using the conventions from `qa/java/skills/api-test-author/writer` if API-facing, **otherwise plain TestNG + AssertJ**" (also `:27`, `:269`, `:277`) | **Worse than the dotnet dead-end, not absent.** *(Corrected 2026-08-09 — an earlier pass reported "no test mention at all"; the grep pattern lacked "TestNG".)* It points dev-side unit tests at **TestNG**, which is the **QA suite's** runner per `CLAUDE.md` Stack defaults. Spring Boot's own `spring-boot-starter-test` ships **JUnit 5 + Mockito + AssertJ** — so the guidance sends an agent to the wrong runner for the lane |
| `backend/dotnet/skills/standards-audit/references/conformance-checklist.md:243` | Section M "Testability & contract tests" — M2 flags direct `DateTime.Now`/`Guid.NewGuid()`, M1 flags endpoints with no test project | Audits *testability*; nothing writes the tests |
| `qa/{dotnet,java,typescript}/skills/` | 37–43 skills, all integration-and-above (`api-test-author`, `db-testing`, `ui-test-author`, `api-contract-testing`, …) | **No unit-test skill in any of the three stacks** |
| `engineering-practices/test-driven-development/SKILL.md` (373 lines) | Red-green-refactor discipline, Iron Law, rationalization table, red flags | Deliberately framework-agnostic — one incidental `jest.fn()` at `:99`. Owns the *loop*, not the mechanics |
| `backend/<stack>/agents/be-<stack>.md:3` | "Do NOT use for test authoring (qa-*-dotnet)" | The agent disclaims it and points at a peer that operates one altitude up |

**The hole in one sentence:** a `be-*` agent scaffolds a CQRS handler, a strategy resolver, a decorator, a `Result<T,E>` branch, or a domain invariant, and there is nothing in its load path telling it how to test that code below the transport — so it either writes nothing, improvises, or hands it to a `qa-*` peer that will test it through HTTP.

### 1b — Frontend: a test skill exists, and it explicitly disclaims the non-rendering half

Both FE stacks ship a `component-testing` skill (react 182 lines, Vitest + RTL; blazor 142 lines, bUnit v2). Each is well-scoped and fences E2E to its `qa-ui-*` peer correctly. **Both also push non-rendering logic out of scope and name no owner** — the same dead-end as `pattern-writer:27`:

| Where | What it says | Verdict |
|---|---|---|
| `frontend/react/skills/component-testing/SKILL.md:37` (*When NOT to use*) | "**Pure TS logic** with no rendering (a Zod schema, a formatter, a mapper) → **a plain Vitest test on the function, no RTL**" | Names the destination, owns nothing there. Not in the Handoffs list (`:175`) either |
| `frontend/blazor/skills/component-testing/SKILL.md:36` (*When NOT to use*) | "**Pure C# logic** with no rendering (a formatter, a validator class) → **a plain NUnit/xUnit test on the class**, no bUnit" | Same. Not in Handoffs (`:136`) |
| `frontend/react/.../component-testing/SKILL.md:35` | Async RSC: "Pull the data fetch into a plain async function and **unit-test *that***" | The extracted function is the single most-recommended unit in the skill — and its test has no owner |
| `frontend/react/skills/standards-audit/references/conformance-checklist.md:290` (**O5**) | "Async-RSC logic is extracted and unit-tested" — a **findable violation** | The audit flags the absence; no skill writes the fix. Exact parallel to backend §M/M2 |
| same, O1–O7 (`:287–293`) | Every grep is `--glob '*.test.tsx'` | **Non-component tests (`*.test.ts`) are invisible to the whole section** — a repo could have zero pure-logic tests and pass O clean |
| `frontend/blazor/skills/component-testing/SKILL.md` selection matrix (`:38–51`) | Rows are all *component shapes* | A state container, a validator, a mapper has no row — the matrix can't answer "should I test this?" for them |

**What actually falls in the FE hole** (all of it code the FE stacks' own skills generate):

| Stack | Unowned units |
|---|---|
| **react** | Zod schemas (`forms`) · formatters/mappers · **extracted async-RSC fetch functions** (`data-fetching`) · Zustand store logic + URL-as-state serializers (`state-management`) · the breakpoint TS mirror (`responsive-design`) · `next-intl`/i18n message helpers (`languages`) · route-segment helpers & `middleware.ts` predicates (`routing`) · ProblemDetails→UI mappers (`error-handling`) |
| **blazor** | Scoped state containers + their `Changed` events (`state-management`) · FluentValidation validator classes (`forms`) · the C# breakpoint mirror (`responsive-design`) · culture/format helpers (`languages`) · `IJSObjectReference` wrapper logic that isn't interop itself (`javascript-calls`) · Polly policy config + retry predicates (`error-handling`) |

**The FE hole in one sentence:** a `fe-*` agent is told by its own test skill to write "a plain Vitest/NUnit test on the function", and then has no guidance for doing it — while the audit (react O5) already treats the absence as a finding.

---

## 2. The fence (decide this before writing a line)

The skill only earns its place if the boundary is mechanical. Proposed rule, one sentence:

> **This skill owns tests that run in-process with no I/O — no HTTP, no container, no real database, no broker, no filesystem. The moment a test boots the app or starts a container, it belongs to the `qa-api-<stack>` peer.**

| Neighbour | Owns | This skill |
|---|---|---|
| `qa-api-<stack>` (`api-test-author`, `db-testing`, `api-contract-testing`) | Contract + integration tests through the transport; `WebApplicationFactory` / `@SpringBootTest` / supertest; Testcontainers; real-DB seed-assert-clean | Never boots the app, never starts a container |
| `ep-test-driven-development` | The red-green-refactor loop, the Iron Law, when to write the test | The stack mechanics the loop needs: runner, doubles, seams, naming, project layout |
| `qa-<stack>-test-quality-check` (mutation: PIT · Stryker.NET) | Proving the tests catch seeded faults; the mutation-score gate | Writing the assertions mutation testing then grades. **No coverage-% gate here** — that lane is the mutation skill's |
| `qa-<stack>-test-data-builder` | Builder/ObjectMother architecture for the QA suite | May emit a minimal in-repo builder for a 4+ field domain object (`CLAUDE.md` rule) and names the QA skill for anything larger |
| `qa-<stack>-standards-audit` | Auditing a **test suite** against QA conventions | Not an audit lane at all — it writes code |
| `be-<stack>-code-review` | Reviewing the changed surface, incl. the tests | Not a review lane |
| `fe-<stack>-component-testing` | **Rendering** a component/hook and asserting on output (RTL/bUnit) | Nothing — different stack. On FE this skill *is* the owner (Track B, §3b) |

**Track B fence (frontend), one sentence:** the boundary is **does it render?** — if the unit needs a renderer (`render`/`renderHook`/`Render<T>`), it's a component test; if it's a plain function/class/store, it's a pure-logic test. Both live in the **same** test project, runner, and skill (§3b); E2E stays with `qa-ui-<stack>`. No new fence is introduced on FE — the existing component/E2E fence is untouched.

**`CLAUDE.md` tension to state explicitly, not silently resolve:** the global rule prefers "real-DB integration tests over mocks." That rule governs the *integration* lane, which is `qa-api-<stack>`'s. This skill's existence is not a licence to replace integration tests with mocks — each skill's SKILL.md must open by saying so, and must refuse to unit-test what only a real dependency can prove (SQL translation, migration correctness, JWT validation against a real JWKS).

**Open fence question (F1):** who audits backend unit tests? `qa-<stack>-standards-audit`'s own fence says it "audits test code only — the application under test belongs to `be-*`", which puts backend unit tests in its lane, but they live in the backend repo and are written by a `be-*` agent. Recommended answer: **`be-<stack>-standards-audit` section M gains rows for unit-test presence/shape** (see Phase 4), and `qa-<stack>-standards-audit` keeps the dedicated QA suite. Needs confirming, because it's the one place a user could get two audits over the same files.

---

## 3. Architecture decision (D1) — per-stack skill, no new `_shared` skill

| | **Option A — 3 per-stack skills (recommended)** | Option B — `_shared/unit-testing-guide` + 3 thin stack skills | Option C — fold into `pattern-writer` |
|---|---|---|---|
| Shape | `backend/<stack>/skills/unit-testing/`, self-contained | Shared doubles/seams doctrine in `_shared`, mechanics per stack | Extend the 3 existing `pattern-writer` skills with a test section |
| New folders | 3 | 4 | 0 |
| Load-path hops | 1 | 2 | 0 |
| Precedent | `database-code`, `auth0`, `code-review` are all per-stack with no `_shared` twin | `pattern-guide` + `_shared/pattern-guide`; `code-review` + `_shared/code-review` | — |
| Risk | The doubles/seams doctrine gets stated 3× and can drift | A third file in the load path for content that barely differs from `ep-test-driven-development`; the CONFORMANCE plan already rejected a "cross-stack rules" middle layer for exactly this reason (§2, rejected sub-option) | `pattern-writer` is already the largest skill in each stack; testing would be a buried subsection with no independent trigger, and `database-code`-generated code would still have no test guidance |

**Recommended: Option A.** The doctrine that *would* live in `_shared` is mostly already in `ep-test-driven-development` (which every `be-*` plugin bundles), and the parts that aren't — the test-double decision matrix, the seam taxonomy — have genuinely different violation shapes per stack: `DateTime.UtcNow` vs `Instant.now()` vs `Date.now()`; `NSubstitute` vs `Mockito.mock` vs `vi.mock`; sealed-class-blocks-substitution vs final-method-blocks-substitution vs module-mock-hoisting. Same conclusion the conformance plan reached: only the sentence above the row is shared, not the row.

**Decision D2 — no slash command.** `CLAUDE.md`'s rule: code-touching skills are reached through their owning agent, whose orientation pass is exactly what a direct call would skip. This writes code → no command. Command count stays 71.

**Decision D3 — a new agent phase, not a fold into Phase 2.** Each `be-<stack>` agent grows a phase between Generate and Review:

| # | Phase | Skills | Exit gate |
|---|---|---|---|
| 1 | Pattern decision | `pattern-guide` (+ `_shared/pattern-guide`) | unchanged |
| 2 | Generate | `pattern-writer`, `database-code`, `{auth0,cognito}` | unchanged **minus** the "passes for generated tests" clause |
| **3** | **Unit test** | **`unit-testing`** (+ `ep-test-driven-development` when running test-first) | **runner green; every logic-bearing type generated in Phase 2 has a test or a stated reason it doesn't; no test boots the app or a container** |
| 4 | Review | `code-review` (+ `_shared/code-review`) | unchanged |

Rationale for a separate phase over a Phase-2 fold: the gates differ (a build/format gate vs a runner gate + a coverage-of-generated-types check), and a brownfield FIX run must be able to re-enter *only* the test phase — "the logic is right, the tests are missing" is the single most common backend brownfield ask. Cost is renumbering Review 3→4 in three agent files.

---

## 3b. Frontend architecture decision (D5) — **rescope `component-testing`, do not add a skill**

Track B deliberately reaches the **opposite** conclusion from Track A. The asymmetry is the point: backend has *no* test skill, so a new one is the only option; frontend has *one that already owns the runner, the project, the doubles policy, the naming rules and the anti-patterns* — and is missing one section.

| | **Option A — extend `component-testing` (recommended)** | Option B — new `fe-<stack>-unit-testing` skill | Option C — rename to `fe-<stack>-unit-testing`, cover both layers |
|---|---|---|---|
| New skill folders | **0** | 2 | 0 (rename in place) |
| Duplicated content | none | **Setup, Rules, Async, Anti-patterns, Handoffs — ~60% of a 182-line skill** (same runner, same config, same project) | none |
| Trigger collision | none | **High — `component-testing`'s description already claims "unit-test this component"**; a second skill claiming "unit-test this function" competes for the same phrasing. This is exactly the failure the library guarded against for `vendor/*` (`frontend/PLAN.md` F4) and the audit engine ("loaded, never invoked") | none |
| Public surface change | description + one section; `name:` unchanged | 2 new names to register + catalog | **`name:` changes** → marketplace `skills[]`, both agents, `CLAUDE.md`, `README.md`, the react audit's §O owner link, 26 cross-refs |
| Honest? | Yes — the skill already *is* the FE unit-test skill; it just under-claims | The two would fence each other over a boundary (renders / doesn't) that costs one sentence inside one skill | Arguably the most accurate name, but a rename for one added section |

**Recommended: Option A.** The added content is genuinely small — there is **no new runner, no new config, no new project, no new doubles library, no new naming convention** (Vitest/xUnit is already configured by the skill's own *Setup* section, and its *Rules* already mandate `Should_X_When_Y`, one behavior per test, no `if`/`for`, fakes-over-mocks, no sleeps — all of which apply unchanged to a pure function). What's missing is a **selection matrix for non-rendering units** and the FE-specific seam list. That is one section, not a skill.

**Consequences to accept:**
- `component-testing`'s `description:` must grow the new triggers (`"test my Zod schema"`, `"test this formatter"`, `"test my Zustand store"`, `"unit-test this validator class"`), or the gap stays unreachable by auto-trigger even after the content exists.
- The skill's *title line* stops being strictly accurate ("Component Testing" now covers non-components). Mitigate with a subtitle — "**Component & pure-logic tests**" — and leave `name:` alone. If this grates in review, Option C is a clean follow-up that changes no content.
- **D6 — no new agent phase on FE.** Unlike backend (D3), Phase 4 already exists and already loads this skill; it only needs its **gate** extended. Phase numbering is untouched in both FE agents.

### The section to add (same shape in both stacks)

1. **Selection matrix for non-rendering units** — the §1b "unowned units" rows, each with *test it?* + *what to assert*, plus the explicit skips (a type-only module, a re-export barrel, a constants file, a thin wrapper over the library).
2. **The renders/doesn't-render rule** — one sentence, plus "if you're reaching for `render()` to test a formatter, you extracted the wrong thing."
3. **File/colocation convention** — react: `*.test.ts` beside the unit vs `*.test.tsx` for components (**and the O1–O7 grep fix, §Phase 7**); blazor: where a non-`.razor` test class lives in the bUnit project.
4. **FE seam taxonomy** — the browser-shaped seams that make FE logic untestable, mirroring backend §5.6: **`Date.now()`/`DateTime.Now`**, `crypto.randomUUID()`/`Guid.NewGuid()`, `window`/`localStorage`/`navigator`, `Math.random()`, env/config reads. This doubles as the constructive half of the react audit's hydration rule (*no browser reads during render*) — a unit that can't be tested without `window` is usually the same defect.
5. **Handoffs edit** — add the pure-logic row that both skills' Handoffs sections currently lack, and route mutation-grading to `qa-<stack>-test-quality-check` (**dotnet only** — StrykerJS has no skill; see §7).

---

## 4. Naming & wiring conventions — Track A (fixed — apply identically to all 3)

| Thing | Pattern | Examples |
|---|---|---|
| Skill folder | `backend/<stack>/skills/unit-testing/` | `backend/java/skills/unit-testing/` |
| Frontmatter `name:` | `be-<stack>-unit-testing` | `be-dotnet-unit-testing`, `be-java-unit-testing`, `be-node-unit-testing` |
| References | `references/<topic>.md` only if the SKILL.md exceeds ~350 lines | `references/doubles.md` |
| Command | **none** (D2) | — |
| Marketplace | `skills[]` of the matching `be-*` plugin only — **not** the `qa-*` plugins | `"./backend/dotnet/skills/unit-testing"` |
| Agent wiring | new Phase 3 row + FIX/EXTEND mode mentions + Phase-2 gate edit | `backend/dotnet/agents/be-dotnet.md` |

---

## 5. Skill content spec (the same 11 sections in all three, stack-idiomatic inside)

1. **Fence + the integration rule** — the §2 table, and the "mocks don't replace integration tests" statement.
2. **Version gate** — detect the runner and its major from the manifest before writing anything (`*.csproj` `PackageReference` / `build.gradle.kts` + Boot BOM / `package.json`); **the project's existing runner and assertion library always win over this skill's default.**
3. **What deserves a unit test** — a decision table over what the stack's own skills generate: domain invariant · strategy selection · decorator ordering · handler orchestration (deps faked) · `Result`/error mapping · validation rules · calculation/rounding/money · state-transition guards. And **what not to**: DTOs/records with no behaviour, EF/JPA/Prisma configuration, controllers used purely as transport, framework wiring, generated code.
4. **Project layout & setup** — where the test project/dir lives, naming, how it references the target, what the manifest needs.
5. **Naming** — `Should_X_When_Y` / `Given_Y_When_X_Then_Z` per `CLAUDE.md`, one logical assertion, no `if`/`for` driving assertions.
6. **The seam taxonomy** — the five things that make logic untestable and the injectable replacement for each: **time**, **identity**, **randomness**, **config**, **outbound I/O**. This is the constructive half of conformance check M2, and each skill must cite M2 so the audit and the fix agree.
7. **Test doubles** — decision matrix (prefer a hand-written fake → stub → mock as last resort; never mock a type you don't own; never assert on a mock where a state assertion works), plus the stack's mocking library and its specific traps.
8. **Parameterized tests** — the `CLAUDE.md` no-conditionals rule's escape hatch, per runner.
9. **Test data** — inline literals for 1–3 fields, a minimal builder at 4+, hand off to `qa-<stack>-test-data-builder` for suite-scale needs.
10. **Async & concurrency** — testing async paths without sleeps; the stack's deadlock/floating-promise traps.
11. **Handoffs** — the boundary table naming `qa-api-<stack>`, `qa-<stack>-test-quality-check`, `ep-test-driven-development`, `be-<stack>-code-review`.

### Per-stack specifics

| | **dotnet** | **java** | **node** |
|---|---|---|---|
| Runner | **NUnit** default (`CLAUDE.md` Stack defaults); xUnit fully supported when detected | **JUnit 5** | **Vitest** default; Jest when detected |
| Assertions | `Assert.That` + `Assert.Multiple` (matches `pattern-writer:203`) | **AssertJ** | Vitest `expect` |
| Doubles | **NSubstitute** default; Moq supported when detected. Trap: sealed/non-virtual blocks substitution → cross-ref conformance E6/M5 | **Mockito** + `@ExtendWith(MockitoExtension.class)`. Traps: `final` methods, static mocking as a smell, `@Mock` field injection vs constructor | DI/closures first; `vi.mock` sparingly. Traps: hoisting, module-registry state between tests, mocking Prisma's client deeply instead of the repository seam |
| Time seam | `TimeProvider` + `FakeTimeProvider` (net8+, so **all three supported TFMs**) | `java.time.Clock` injected; `Clock.fixed` | injected clock fn; `vi.useFakeTimers` |
| Async | no `.Result`/`.Wait()` in tests either; `Task`-returning tests | virtual threads / `CompletableFuture` without sleeps | no floating promises; `await expect(...).rejects` |
| Fence example | `WebApplicationFactory` → `qa-api-dotnet` | `@SpringBootTest` / `@DataJpaTest` / Testcontainers → `qa-api-java` | supertest / Testcontainers → `qa-api-typescript` |
| Version policy | .NET 10 primary / 8–9 supported | Java 21 + Boot 3.x | Node 24 primary / 22 maintenance; flag 20 (EOL Apr 2026) |

---

## 6. Phases (the checklist)

### Phase 0 — Decisions — **RESOLVED 2026-08-09** (every recommended option taken)
- [x] **D1** per-stack skills, no `_shared` twin (§3)
- [x] **D2** no slash command — command count stays 71
- [x] **D3** new agent Phase 3, Review renumbers to 4
- [x] **F1** backend unit tests are audited by `be-<stack>-standards-audit` §M (M7–M9), not `qa-<stack>-standards-audit` (§2)
- [x] **D4** dotnet doubles default: **NSubstitute 6.0.0** (+ `NSubstitute.Analyzers.CSharp` 1.0.17), Moq honoured when already present. Confirmed by the research pass — 2026 consensus is NSubstitute as the default for new projects post-SponsorLink; recorded in the skill's Stack table rather than `CLAUDE.md` (it's a stack-skill default, not a library-wide one)
- [x] **D5** frontend: rescope `component-testing`, no new FE skill (§3b)
- [x] **D6** no new FE agent phase; Phase 4's gate is extended instead
- [x] Research pass: NSubstitute-vs-Moq 2026 consensus, `FakeTimeProvider` availability (net8+, so all three TFMs), current package versions. **One decision came out of it that the plan didn't anticipate:** assertions stay on **NUnit's built-in constraint model**, *not* FluentAssertions — v8 requires a paid commercial licence (which is why `qa-api-project-setup-dotnet` deliberately pins 6.12.1), and a product repo shouldn't acquire that exposure from a test skill. Matches what `pattern-writer` already emitted (`Assert.That` + `Assert.Multiple`)

> Tracks A and B are independent after Phase 0 — either can ship first. Track B is much smaller (no new skills) and is the cheaper proof that the §3b/§5 section shape is right.

## Track A — backend

### Phase 1 — `be-dotnet-unit-testing` (the reference implementation) — **BUILT 2026-08-09**
- [x] `backend/dotnet/skills/unit-testing/SKILL.md` (247 lines) — all 11 sections in house shape (`When to use` / `When NOT to use` / `Version policy` / `Stack` / topics / `Rules` / `What NOT to do` / `Generation steps` / `Handoffs`, matching `database-code`). Opens with the never-unit-test table (EF `IQueryable`, migrations, JWT/JWKS, model binding, raw SQL) so the integration lane is protected before the first recipe
- [x] Edit `pattern-writer` `:27`, `:45`, `:203` + the Handoffs list — all four dead-ends now route to `be-dotnet-unit-testing`; the API-facing case still routes to the `qa-api-dotnet` peer
- [x] Wire `backend/dotnet/agents/be-dotnet.md` — Phase 3 row added, Review→4, Phase-2 gate lost its `dotnet test` clause (now Phase 3's), `description:` narrowed to *contract/integration/E2E* + gained the "unit-test this handler" trigger, an operating rule stating what the agent owns, the `"logic is right, tests are missing"` FIX path (re-enters Phase 3 alone), a `qa-test-quality-check-dotnet` peer row. **Two staleness bugs the plan hadn't listed and the wiring exposed:** the orientation table's *Known unknowns* row said `tests/` was owned by the `qa-api-dotnet` peer (now split — unit-test surface is the agent's own row), and the cache-update line didn't list a test project / fake / builder among the seams a run creates
- [x] Register in `marketplace.json` `be-dotnet.skills[]` (47 skills; JSON re-validated)
- [x] Minimal `CLAUDE.md` correction — the Backend catalog's "same three-phase pipeline" sentence was made false by D3, so the phase list and the dotnet skill line were updated now rather than deferred to Phase 4
- [x] **Verified against a scratch .NET 10 solution** (SDK 10.0.301, `net10.0`, CPM, nullable on): every recipe in the skill compiled and ran — **10/10 tests pass, 0 warnings**. What the run proved: all seven package pins resolve together · `FakeTimeProvider(DateTimeOffset)` + `Advance` · `Options.Create` · `Substitute.For` + `Received(1)` + `Arg.Is` + `Arg.Any` + `DidNotReceive` · `NSubstitute.ExceptionExtensions.ThrowsAsync` · `Assert.That` / `Assert.Multiple` / `Assert.ThatAsync` / `Assert.MultipleAsync` / `Assert.ThrowsAsync` (the NUnit-4 APIs the skill claims) · the three `[TestCase]` rounding rows are arithmetically right (`0.005→0.01`, `0.004→0.00`, `-0.005→-0.01`) · the builder shape
- [x] **One real defect found and fixed by the verification** — the doubles snippet's `Arg.Is<OrderPlaced>(e => e.CustomerId == …)` raises **CS8602** in a nullable-enabled test project, which fails this stack's own 0-warning gate. `Arg.Is<T>` types its predicate as possibly-null. Fixed to `e!.CustomerId` with a note explaining why, and explicitly forbidding "turn nullable off in the test project" as the workaround. **This is why Phase 2/3 must each run their own verification rather than trusting the ported shape**

### Phase 2 — `be-java-unit-testing` — **BUILT + VERIFIED 2026-08-09**
- [x] `backend/java/skills/unit-testing/SKILL.md` (263 lines) — JUnit 5 + Mockito + AssertJ, `Clock`/`Clock.offset` seam, the **Spring-context fence stated twice** (a slice test is fast but *not isolated* — `SpringExtension` is the peer's, `MockitoExtension` is ours), the `BigDecimal` scale trap, STRICT_STUBS-as-a-feature, `@InjectMocks` discouraged in favour of constructor calls
- [x] **Runner deviation stated explicitly:** `CLAUDE.md`'s TestNG default is the *QA suite's*; dev-side unit tests use **JUnit 5** because `spring-boot-starter-test` ships it and every Boot 3.x recipe assumes the Jupiter lifecycle. Same shape as `fe-blazor-component-testing`'s xUnit-for-bUnit deviation
- [x] Rewired `pattern-writer` `:27`, `:262`, Handoffs — **it was not silent on tests as this plan first recorded** (see the corrected §1a row): it pointed at *TestNG*, the QA suite's runner
- [x] Wire `backend/java/agents/be-java.md` (Phase 3, Review→4, description, operating rule, orientation row, cache line, peers); register in `be-java.skills[]` (46 skills)
- [x] **Verified:** 9/9 green, `-Xlint:all` clean

### Phase 3 — `be-node-unit-testing` — **BUILT + VERIFIED 2026-08-09**
- [x] `backend/node/skills/unit-testing/SKILL.md` (~290 lines) — Vitest (Jest when detected), **DI over `vi.mock`** with the hoisting trap explained, **both branches of every `Result<T,E>`** as a first-class section, compile-time exhaustiveness via `never`, Zod `issues[].path`/`code` (never the message), integer minor units for money, the `mockDeep<PrismaClient>()` anti-pattern called out by name, `clearMocks`/`restoreMocks` as non-optional
- [x] Edited `pattern-writer` `:29`, `:307`, Handoffs
- [x] Wire `backend/node/agents/be-node.md`; register in `be-node.skills[]` (42 skills)
- [x] **Verified:** 11/11 green, `tsc --noEmit` strict clean — and the run added the `lib`/`@types/node` prerequisite to the skill

### Phase 4 — Cross-cutting wiring (backend)
- [x] **Done early, with Phase 1** — `backend/dotnet/skills/standards-audit/references/conformance-checklist.md` §M: renamed "Testability & **unit tests**", owner line split (`unit-testing` owns M7–M9 + the constructive half of M2), **M7** (logic-bearing types have unit tests) · **M8** (the unit project stays in-process) · **M9** (no assertion-free or `UseInMemoryDatabase` "unit" tests) added, all `major`; M1–M6 IDs untouched; the section-index row updated to match
- [x] `solution-blueprint` SKILL + example routing-map rows gain `be-dotnet-unit-testing` ("Unit tests ship with the slice, not after")
- [x] `delivery-plan` SKILL + `example-delivery-plan.md` (3 tasks) + `handoff-template.md` — so `be-planner` packs and Mission Control bind the real skill name. **`delivery-plan` already assumed unit tests existed** (`:69` P4 "→ unit tests", `:99` "Unit tests cover every validation branch", `:113` "Unit tests are part of the implementation task") — it simply had no skill to name. Now it does
- [x] `CLAUDE.md` — all three stack skill lists, the pipeline sentence (three-phase → four, with each stack's runner named), the Backend code rules (a new bullet: the agent owns its unit tests, the process boundary is the fence, and in-memory providers — `UseInMemoryDatabase`/H2/SQLite-for-Postgres/`mockDeep<PrismaClient>()` — are named as false-negative machines)
- [x] `README.md` — all three `be-*` bullets ("design-pattern + persistence" → "+ unit-test", "same five skills" → six, "four pattern/persistence skills" → five)
- [x] `.claude-plugin/marketplace.json` — all three plugin descriptions
- [x] Grep sweep: **0 remaining** `three-phase` claims and **0** "Do NOT use for test authoring" disclaimers outside this plan

## Track B — frontend

### Phase 5 — `fe-react-component-testing` rescope — **DONE 2026-08-09**
- [x] Added the 5-part **Pure-logic tests (no renderer)** section (182 → 253 lines): an 11-row selection matrix keyed to the skills that *produce* each unit (Zod schemas ← `forms`, extracted fetches ← `data-fetching`, stores + URL serializers ← `state-management`, breakpoint mirror ← `responsive-design`, i18n helpers ← `languages`, middleware predicates ← `routing`, error mappers ← `error-handling`), the `*.test.ts`/`*.test.tsx` convention, the browser-seam table tied to the hydration rule, and the float-money trap
- [x] `:37` and the async-RSC pointer (`:35`) now link **into** the new section instead of dead-ending; a Handoffs row added
- [x] `description:` gained the pure-logic triggers ("test my Zod schema", "test this formatter", "test my Zustand store") — without this the content would be unreachable by auto-trigger
- [x] Subtitle → "Component & Pure-Logic Testing"; **`name:` unchanged** (`fe-react-component-testing`), so no marketplace/agent/command surface moved
- [x] `fe-react.md` Phase 4 gate extended (+ `tsc --noEmit`); **phase numbering untouched**
- [x] No new skill, so no `marketplace.json` `skills[]` change — confirmed

### Phase 6 — `fe-blazor-component-testing` rescope — **DONE 2026-08-09**
- [x] Same 5-part section, C#-idiomatic (142 → 194 lines): state containers with **`Changed` raised exactly once** and unsubscribe honoured (a leaked handler is a real Blazor bug), FluentValidation validators driven directly, culture helpers with an **explicit `CultureInfo`** (the ambient-culture test that passes locally and fails in CI), the breakpoint mirror, Polly predicates, error→UI mappers
- [x] `:36` and Handoffs now route into the section
- [x] `description:` + subtitle updated; `name:` unchanged
- [x] **Runner consistency honoured** — pure-logic tests follow the project's existing runner (the skill's documented xUnit-for-bUnit deviation); no second runner introduced
- [x] **Deliberately does not duplicate the backend treatment** — it links to `be-dotnet-unit-testing` for the NUnit/NSubstitute/`FakeTimeProvider`/builders depth, since the discipline is identical and only *where the code runs* differs
- [x] `fe-blazor.md` Phase 4 gate + the FIX-mode line at `:84` (which implied bUnit was the only option)

### Phase 7 — Cross-cutting wiring (frontend) — **DONE 2026-08-09**
- [x] **§O glob blindness fixed** — the layer-agnostic checks (O6, O7) now sweep `*.test.{ts,tsx}`, O1's runner probe widened to `*.test.ts*`; §O renamed "Component & pure-logic tests" with an explicit glob note; **4 new rows** — **O8** pure-logic coverage · **O9** no `render()` in a `*.test.ts` · **O10** schema errors asserted on path/code not message · **O11** browser seams injected not global. O1–O7 IDs untouched (permanent per the conformance plan); table integrity re-checked programmatically (11 rows, correct column count, escaped pipes intact)
- [x] `frontend/blazor` has no `standards-audit` yet — the §O-equivalent rows are recorded for whoever authors it (`CONFORMANCE-AUDIT-PLAN.md` Phase 2)
- [x] `CLAUDE.md` — both FE catalog one-liners and **both** Frontend code-rules bullets now state the two altitudes
- [x] `README.md` + both FE plugin descriptions in `marketplace.json`

---

## 7. Known gaps this plan deliberately leaves open

- **`qa/` gets no unit-test skill.** The QA domain's altitude is unchanged; if a project wants unit tests inside the dedicated QA suite rather than beside the production code, that's a `qa-*` request and a separate plan.
- **No mutation-testing wiring for TypeScript.** `qa-typescript-test-quality-check` (StrykerJS) still doesn't exist, so the node skill's "grade your assertions" handoff points at a gap. Noted, not fixed here.
- **`be-java`/`be-node` have no `standards-audit`** (per `CONFORMANCE-AUDIT-PLAN.md` Phases 4–5), so the Phase-4 §M rows land only in dotnet; the java/node checklists must include them when those audits are authored.
- **No `_shared` doubles doctrine.** If drift across the three skills shows up in review, the fallback is Option B (§3), extractable without changing any public name.
- **No mutation-testing handoff for either TS lane.** `qa-typescript-test-quality-check` (StrykerJS) doesn't exist, so both `be-node-unit-testing` and `fe-react-component-testing` will name a grader that isn't there. Same gap hit twice — worth its own small plan.
- **`frontend/react-native/` is excluded** (under construction, not shipped). Its `component-testing` equivalent will inherit the same hole; note it in `frontend/react-native/PLAN.md` rather than solving it here.
- **`design/*` and `qa/manual/*` are unaffected** — no aesthetic or test-design skill touches unit-test authoring.
- **The FE title inaccuracy is accepted, not solved** (D5 consequence). If review rejects "Component Testing" covering non-components, Option C (rename to `fe-<stack>-unit-testing`) is a content-free follow-up.
- **Cross-track consistency is asymmetric by design.** Backend gets a skill named `unit-testing`; frontend gets the same content inside a skill named `component-testing`. A user who reads both catalogs will notice. The §3b table is the written justification — keep it in the plan so the decision isn't re-litigated as an inconsistency bug.
