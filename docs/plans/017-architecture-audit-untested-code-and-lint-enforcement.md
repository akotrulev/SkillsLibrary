# 017 — Architecture audit, untested-code skill and lint-enforced house rules — plan (2026-11-21)

**Goal:** Take into the library what the "Strategic AI Coding" study guide has that the library lacks.
- A read-only **architecture audit**: shallow modules, forwarding layers, duplicated logic, tests tied to
  internals, and code that drifts from the glossary. It is a third lane of `code-auditor`.
- One rule that **unit tests go through the unit's entry point**.
- A stack-agnostic skill for **changing code that has no tests**.
- Each stack's mechanically checkable house rules **named as lint rules**, so a gate catches them.

**Status:** As of 2026-11-21, A1, FX1, R1, U1 and L1–L5 have landed; C1 (catalog and README) is next, then G1 (the whole set,
the blind fixture run, filing).
- **Built but unverified:** the lint tables are proven in scratch projects only, never in a real project. Limits L5 records: the
  `qa-java` `@Test` suppression keys on the annotation's simple name and Maven wiring was not run; `.features-gen/**` is ignored by
  the library's own description of `bddgen`, not by a run of it. L5 left no row unverified; the items L2 lists as unverified stand (see its As built).
- **Only the user can do:** restart after G1 and type `/engineering:audit` on a real project. Run one
  stack's `<plugin>:rules` in a real project to see its lint-gap report.

**Test design:** none. The plan serves no stories and changes skill text, rule files, the manifest and
one lint script. The checks are the four scripts in `tools/`, the scratch-project proofs in §7 and the
blind fixture run in §4.

**Documentation task:** none. This is the skills library, and the skill text is the documentation. C1
updates the catalog and `README.md` from what landed (the 016 precedent).

**Telemetry smoke:** none. No service is built.

---

## 1. What already exists, and what is missing

| Need | Today | Gap |
|---|---|---|
| A sweep for structural decay across a codebase | `code-auditor` has two lanes: SPEC (`engineering/spec-vs-code-audit`) and FEATURE (`engineering/feature-audit`), chosen at `engineering/agents/code-auditor.md` "Every run" step 4. Neither looks at module structure. `backend/_shared/code-review` (`architecture-review`) checks layering and pattern stacking on backends only, inline, with no saved report. No file in the library mentions module depth | A third lane, ARCHITECTURE, run on the existing `engineering/standards-audit-engine` with a checklist `engineering` owns (A1, §3) |
| Depth and duplication checked in review | `architecture-review` has Layering, Pattern stacking, Abstraction, Boundaries. `CLAUDE.md` "Simplicity" has "Flat over layered" | `architecture-review` points at sections B and C of the new checklist (A1) |
| Code checked against the glossary | `product/skills/domain-modeling/references/glossary-format.md` has `Avoid` and `Called in code` columns. `engineering/agent-orientation-cache/SKILL.md:62` tells agents to read the glossary. No audit flags an identifier that uses an avoided term | Section E of the checklist, and one line in `feature-audit` (A1) |
| Proof the lane finds what it claims | `CONTRIBUTING.md` "Testing a new skill" step 5: point a reviewer at code with known issues. No such code exists for an architecture audit | A seeded fixture and a blind run (FX1, G1, §4) |
| Unit tests that survive a rewrite of the code behind them | `backend/dotnet/skills/rules/dotnet-tests.md:20` and `backend/java/skills/rules/java-tests.md:19` ban reflection and `InternalsVisibleTo`. `backend/node/skills/rules/node-tests.md:22` bans `@ts-expect-error` into private state, as *minor*. The other nine tests rule files and `CLAUDE.md` "Test code rules" say nothing. The 80% branch rule says to design tests branch by branch and not where to reach the branch from | One bullet in `CLAUDE.md`, and one line in each tests rule file (R1, §5) |
| A procedure for changing code that has no tests | One table row, `backend/dotnet/skills/unit-testing/references/risk-hotspots.md:47` ("write characterization tests that pin today's behaviour") | A stack-agnostic `engineering` skill (U1, §6) |
| House rules a linter enforces | Uneven. `backend/rust/skills/rules/cargo.md:19` and `backend/python/skills/rules/python-project.md:14` name lint rules. `desktop/macos/skills/project-setup/SKILL.md:117` names three SwiftLint rules. `be-dotnet`, `be-java` and `be-node` name none: `no any` (`backend/node/skills/rules/node.md:27`) and "never `.Result`" are prose only | A lint table per stack, a setup pointer, an audit check and a lint-gap report (L1–L5, §7) |
| The catalog and README describe all of it | `docs/skills-catalog.md:13` lists 8 `engineering` skills. `README.md:75` starts the rules table | C1 |

## 2. Where each piece lives

| Piece | Path | Registered as |
|---|---|---|
| The architecture lane | `engineering/architecture-audit/SKILL.md` | `engineering:audit-architecture`, a front door |
| Its checklist | `engineering/architecture-audit/references/checklist.md` | read by path |
| The fixture | `tools/fixtures/architecture-audit/course-platform/` | not registered |
| The fixture's answer key | `tools/fixtures/architecture-audit/EXPECTED.md` | not registered |
| The untested-code skill | `engineering/untested-code/SKILL.md` | `engineering:untested-code`, a front door |
| The entry-point rule | `CLAUDE.md` "Test code rules", and each stack's `skills/rules/*-tests.md` | rule files |
| The lint tables | each stack's `skills/rules/`, in the file §7 names | rule files |

The architecture report is saved in the audited project as
`docs/audits/<NNN>-architecture-conformance-r<N>.md`. The engine's naming line
(`engineering/standards-audit-engine/SKILL.md`, "Artifacts") gains the word `architecture` beside the
plugin names.

`engineering` goes from 8 registered skills to 10, and from 7 front doors to 9
(`FRONT_DOORS` in `tools/plugin-surface-check.py:41`).

## 3. The architecture lane

**How it runs.** `/engineering:audit` loads `code-auditor`. Its step 4 picks the lane. A question about
structure, duplication, module boundaries or the health of a codebase, with no spec in hand and no single
feature named, is the ARCHITECTURE lane. The agent then reads `engineering/standards-audit-engine` (Mode A
and B, evidence rules, report template, hostile self-review) and `engineering/architecture-audit` (the
checklist). Nothing in the engine is copied into the new skill.

**The skill supplies what the engine asks a checklist owner for:**

- **Step 0, the language lane.** Detect each language in scope and how it hides things: C# `internal`,
  Java package-private and modules, TypeScript exports and barrels, Python `_name` and `__all__`, Rust
  `pub` and `pub(crate)`, Swift access levels, Kotlin `internal`. A member is public only in that
  language's sense.
- **Step 1, applicability.** Section D applies when the scope has tests. Section E applies when
  `docs/business-model/glossary.md` exists. Each N/A names its probe.
- **A module** is a directory, package or project that other code imports through a surface: an index
  file, a public type, a project reference. The module map is section A's output and the report's first
  table.
- **The fence.** One feature's behaviour is `audit-feature`. Stack conventions are the stack's
  `standards-audit`. One diff is the stack's `code-review`. Pruning tests is `qa-<stack>:test-audit`.

**The checklist.** Ids are permanent. A1 writes the Locate recipe for each row.

| # | Check | Bad sign | Severity |
|---|---|---|---|
| A1 | Every top-level area has one stated purpose | A `utils`, `common`, `shared` or `helpers` area that unrelated modules import | minor |
| A2 | Each module has one entry surface | Callers import files from inside the module, past its index or public types | major |
| A3 | Dependencies between modules have no cycle | Module X imports Y and Y imports X, directly or through a third | major |
| B1 | A module hides more than it exposes | Most public members are one-line forwards or bare data. A caller must know the internals to use it | major for a module, minor for one type |
| B2 | No forwarding layer | A type whose methods pass the same arguments to one collaborator and return its result | major |
| B3 | Internals stay inside | A persistence row type, a mutable collection or a config object in the public surface | major |
| B4 | One decision lives in one module | A file format, a protocol detail or a magic value that two modules each encode | major |
| C1 | No near-identical block in two modules | 20 or more lines, or two whole functions, that match apart from names | major when the copies have drifted, minor when identical |
| C2 | One business rule, one implementation | The same validation, calculation or status rule written in two places | major |
| C3 | No parallel modules | Two modules of the same shape that differ by a noun | minor |
| D1 | Tests enter through the entry surface | A test reaches a non-public member: reflection, widened visibility, a deep import, a suppressed type error | major |
| D2 | Tests assert outcomes | A call assertion on a collaborator the module owns, where the outcome is observable at the entry surface | minor |
| D3 | A module with rules has a test through its surface | Only its internal files are tested | major |
| E1 | Code uses the glossary's term | An identifier, route or UI string that uses a term listed under `Avoid` | minor |
| E2 | Code names match the glossary | A concept's identifier differs from its `Called in code` cell | minor |
| E3 | One term, one concept | The code uses one glossary term for two things | major, a logical conflict owned by `business-analyst` |

**Never a finding:**

- A small module with a small surface. Size is not depth.
- An adapter over code the project does not own. That is a port.
- Duplication under C1's threshold, or in tests, generated code and migrations.
- A consistent project convention. The engine's deviations table holds it.
- An interface with one implementation. That row is `architecture-review`'s; cite it, never restate it.

**Fix directions (D3).** A shallow module is merged into its caller or its callee. A forwarding layer is
removed. Duplicated logic moves into one module that both callers use, and only when two callers exist
today. No fix direction proposes a new layer, a base class or a generic framework.

**Owners named per section**, as the engine requires: B and C, the stack agent and `CLAUDE.md`
"Simplicity". D, the stack's `unit-testing` skill, with `qa-<stack>:test-audit` as the peer for pruning.
E, `product/skills/domain-modeling/references/glossary-format.md`; E3 goes to `business-analyst`, which
needs `product` enabled.

**Evidence.** Static, per the engine. A clone detector such as `jscpd` runs only on the user's opt-in
for that audit and corroborates a read, never replaces it.

## 4. The fixture and the blind run

**A1 does not read this section, and G1 does not read it before its report is saved.** A checklist tuned
to the fixture proves nothing.

`tools/fixtures/architecture-audit/course-platform/` is a small TypeScript project that is read and never
built: no `package.json` dependencies, no install. It holds `docs/business-model/glossary.md` in the
format of `glossary-format.md`, `src/` and `tests/`. Per the house comment rules it has no comments, so
nothing in the code names a planted defect.

**Planted, one per row:**

| # | Files | What is wrong | Expected id |
|---|---|---|---|
| P1 | `src/courses/submit-course.ts`, `src/courses/duplicate-course.ts` | 40 or more near-identical lines: validation, pricing, save. They have drifted: `submit-course` rejects a title over 120 characters and `duplicate-course` does not | C1, major |
| P2 | `src/enrollment/enrollment-service.ts` | Every method forwards its arguments to `EnrollmentRepository` and returns the result | B2, major |
| P3 | `src/catalog/index.ts` | Exports `CatalogRow`, the persistence row type, and the mutable `catalogCache` map | B3, major |
| P4 | `tests/pricing/discount-rules.test.ts` | Imports `src/pricing/internal/discount-rules.ts`, which `src/pricing/index.ts` does not export. No test imports `src/pricing/index.ts` | D1 and D3, major |
| P5 | `src/progress/student-progress.ts` | Exports `StudentProgress`. The glossary's term is `Learner`, with `Student` under `Avoid` | E1, minor |

**Decoys that must not be reported as findings:**

| # | Files | Why it is fine |
|---|---|---|
| N1 | `src/payments/payment-gateway.ts` | A thin adapter over a third-party SDK type: a port over code the project does not own |
| N2 | `src/pricing/index.ts` | One exported function, `quote()`, over four internal files: a deep module |
| N3 | a four-line guard repeated in `src/courses/` and `src/enrollment/` | Under C1's threshold |

`EXPECTED.md` sits one level above the audited root, so an audit of `course-platform/` never reads it. It
holds the two tables above and the pass bar.

**The pass bar.** P1–P5 are each reported under the expected id, with a `file:line` in the named file.
N1–N3 are not findings.

**The blind run, in G1.** G1 adopts `code-auditor` through `engineering/commands/audit.md`, treats
`tools/fixtures/architecture-audit/course-platform/` as the project root, and asks for an architecture
audit of the whole project. The report is saved as
`course-platform/docs/audits/001-architecture-conformance-r1.md`. Only then does G1 open `EXPECTED.md`.

**On a miss.** G1 fixes the checklist, never the fixture and never `EXPECTED.md`. It deletes the failed
report, records in `As built` what was missed and what changed, and runs again. The second run is no
longer blind, and `Status:` says so.

## 5. Tests go through the entry point

**The bullet for `CLAUDE.md` "Test code rules"**, placed directly above the coverage bullet:

> - **A unit test goes through the unit's public entry point and asserts what comes out of it**: the return value, the state it changed or the message it sent. No reflection, no visibility widened for the test, no reach into private state, and no call assertion on a collaborator the unit owns. A branch that cannot be reached that way is a class waiting to be extracted. The code behind the entry point can then be rewritten without editing the test.

**The line for each tests rule file**, one line, *major*, in the stack's own idiom (D7):

| File | Today | R1 |
|---|---|---|
| `backend/dotnet/skills/rules/dotnet-tests.md` | line 20 bans `InternalsVisibleTo` and reflection | Add the call-assertion half to that line |
| `backend/java/skills/rules/java-tests.md` | line 19 bans reflection into private methods | Add the call-assertion half |
| `backend/node/skills/rules/node-tests.md` | line 22, `@ts-expect-error` into private state, *minor* | A *major* line of its own: no import of an un-exported file, no `@ts-expect-error` into private state |
| `backend/python/skills/rules/python-tests.md` | nothing | No test of a `_private` name from outside its module |
| `backend/rust/skills/rules/rust-tests.md` | nothing | Never make an item `pub` for a test. An in-module `#[cfg(test)]` test may see private items, which is the language's design |
| `frontend/react/skills/rules/react-tests.md`, `frontend/blazor/skills/rules/blazor-tests.md` | nothing | Assert what renders and what the handler was called with, never component internals or private fields |
| `mobile/react-native/skills/rules/react-native-tests.md` | nothing | As React |
| `mobile/android/skills/rules/android-tests.md` | nothing | No visibility widened for a test |
| `mobile/ios/skills/rules/swift-tests.md`, `desktop/macos/skills/rules/swift-tests.md` | nothing | `@testable import` is the access. Never raise an access level for a test |
| `desktop/windows/skills/rules/win-tests.md` | nothing | As .NET |

Before writing a line, R1 reads the "doubles" and "seams" parts of that stack's unit-test skill. Where
the skill says otherwise, the skill wins, the line follows it, and `As built` records it.

## 6. The untested-code skill

`engineering/untested-code/SKILL.md`, name `untested-code`, a front door.

Draft description, to be checked against the 200-character budget:
`Use when changing or refactoring code that has no tests (pin today's behaviour first). Triggers "refactor this legacy class", "this has no tests". Not for red gates (quality-constraints).`

**The procedure it teaches**, each step with its "done when":

1. **Name the change point** and the behaviour around it that must stay the same. Done when both are
   written down.
2. **Find the test point**: the narrowest public entry that reaches the change point (§5's rule).
3. **Get it under test.** Where a dependency blocks the test, make the smallest mechanical edit that
   opens a seam: pass the dependency in through the constructor, or put a port over code the project does
   not own. These edits change no behaviour, and they are the only edits made before tests exist.
4. **Write characterization tests.** They assert what the code does today, wrong behaviour included.
   Done when the branches of the methods about to change are covered to the floor in `CLAUDE.md` "Test
   code rules".
5. **Record what looks wrong, and do not fix it.** A behaviour that looks like a defect is pinned as it
   is and reported as a finding. Fixing it is a separate change.
6. **Make the change test-first.** A characterization test that the change must alter is named in the
   report with the old and the new expectation.

**Evidence at the end:** the coverage of the changed methods before the change, and the list of
characterization tests the change altered. The skill points to the stack's `unit-testing` skill for
doubles and seams, to `engineering:quality-constraints` for not weakening a test, and to
`engineering:verify` for the completion claim. It copies none of them.

`backend/dotnet/skills/unit-testing/references/risk-hotspots.md:47` gains a pointer to the skill.

## 7. Lint-enforced house rules

**The shape, the same in every stack.** L1 lands it first, and L2–L5 follow what L1 landed.

1. **A table in a rule file**, under the heading `## Enforced by the build`:
   `| House rule | Tool | Rule id or setting | Level |`. Each row names the prose rule it enforces by
   file. Below the table go two lines: a row the project's config does not enforce is *minor*, and
   turning one off to pass a gate is *major* (`engineering:quality-constraints`).
2. **A pointer in the stack's `project-setup` skill**, where the stack has one: write the lint config
   from that table. The skill carries no second copy of the list.
3. **One check row in the stack's `standards-audit` checklist**, where the stack has one: every row of
   the table is on at error level in the project's lint config.
4. **One step in the stack's `rules` skill** (`<stack>/skills/rules/SKILL.md`): read the project's lint
   config and list every table row it does not enforce under `Not enforced by the build:` in the report.
   The step never edits the project's config (D10).

**A row is added only when all four hold (D9):**

- The prose rule is tagged *major* or *blocker* in the stack's rule files.
- A rule of the stack's own linter detects it. No custom lint rule is written.
- The id is checked against the tool's official rule documentation for the stack's version lane
  (`engineering:source-grounding`), and the rule file's header comment carries the date.
- The rule fires once on a violation in a scratch project (below).

**Where the table goes.** The file whose `paths:` match the stack's lint config, after adding at most the
lint config's own glob. Where no file fits, a new `<prefix>-lint.md`. A new file is added to the path
proposals in step 5 of the stack's `rules` skill.

| Task | Stack | Tool | Table goes in | Setup skill | Audit checklist |
|---|---|---|---|---|---|
| L1 | `be-dotnet` | Roslyn analyzers: `.editorconfig`, `Directory.Build.props` | new `backend/dotnet/skills/rules/dotnet-lint.md` | — | `backend/dotnet/skills/standards-audit` (beside N8) |
| L1 | `fe-blazor` | the same | new `frontend/blazor/skills/rules/blazor-lint.md` | `frontend/blazor/skills/project-setup` | — |
| L1 | `desktop-windows` | the same, C# lanes only | `desktop/windows/skills/rules/package-config.md`, plus the `.editorconfig` glob | `desktop/windows/skills/project-setup` | `desktop/windows/skills/standards-audit` |
| L2 | `be-node` | typescript-eslint, flat config | new `backend/node/skills/rules/node-lint.md` | — | — |
| L2 | `fe-react` | the same, plus the React plugins | new `frontend/react/skills/rules/react-lint.md` | `frontend/react/skills/project-setup` | `frontend/react/skills/standards-audit` |
| L2 | `mobile-react-native` | `eslint-config-expo/flat` | new `mobile/react-native/skills/rules/react-native-lint.md` | `mobile/react-native/skills/project-setup` | `mobile/react-native/skills/standards-audit` |
| L3 | `be-java` | Error Prone and Checkstyle, in Gradle | new `backend/java/skills/rules/java-lint.md` | — | — |
| L3 | `mobile-android` | detekt and Android Lint | `mobile/android/skills/rules/android-build.md` | `mobile/android/skills/project-setup` | `mobile/android/skills/standards-audit` |
| L4 | `mobile-ios`, `desktop-macos` | SwiftLint | each stack's `xcode-config.md`, plus the `.swiftlint.yml` glob | each stack's `project-setup` | each stack's `standards-audit` |
| L4 | `be-python` | ruff, mypy | `backend/python/skills/rules/python-project.md` | — | — |
| L4 | `be-rust` | clippy, `[lints]` | `backend/rust/skills/rules/cargo.md` | — | — |
| L5 | `qa-dotnet` | Roslyn analyzers, NUnit.Analyzers | `qa/dotnet/skills/rules/suite-config.md`, plus the `.editorconfig` glob | — | `qa/dotnet/skills/standards-audit` |
| L5 | `qa-java` | Error Prone and Checkstyle | `qa/java/skills/rules/qa-java-suite.md` | — | — |
| L5 | `qa-typescript` | typescript-eslint, `eslint-plugin-playwright` | new `qa/typescript/skills/rules/qa-typescript-lint.md` | — | — |

**Candidate rows.** These ids were written from memory on 2026-11-21 and are **unverified**. Each L task
checks every id, drops or replaces one it cannot find in the tool's documentation, and names it in
`As built`. The task also mines the stack's own rule files for more rows that pass the four tests.

| Family | House rule | Candidate |
|---|---|---|
| .NET | Never block on a task (`.Result`, `.Wait()`) | `VSTHRD002` (Microsoft.VisualStudio.Threading.Analyzers), or `RS0030` with `BannedSymbols.txt` |
| .NET | Message templates, never interpolation, in log calls | `CA2254` |
| .NET | Cancellation tokens are passed on | `CA2016` |
| .NET | Nullable on, warnings are errors | `<Nullable>enable</Nullable>`, `<TreatWarningsAsErrors>true</TreatWarningsAsErrors>` |
| .NET tests | No `Thread.Sleep` | `RS0030` banning `M:System.Threading.Thread.Sleep(System.Int32)` |
| TypeScript | No `any` | `@typescript-eslint/no-explicit-any`, and the `no-unsafe-*` rules of the `strictTypeChecked` preset |
| TypeScript | Async all the way | `@typescript-eslint/no-floating-promises`, `@typescript-eslint/no-misused-promises` |
| TypeScript | A suppression states its reason | `@typescript-eslint/ban-ts-comment` with `allow-with-description`; `eslint-comments/require-description` |
| React | Hook rules, exhaustive deps | `react-hooks/rules-of-hooks`, `react-hooks/exhaustive-deps` |
| React | Keys are stable ids | `react/no-array-index-key` |
| TypeScript tests | No `waitForTimeout`, no branch in a test | `playwright/no-wait-for-timeout`, `playwright/no-conditional-in-test` |
| Kotlin | No `!!`, no `GlobalScope`, dispatchers injected | detekt `UnsafeCallOnNullableType`, `GlobalCoroutineUsage`, `InjectDispatcher` |
| Kotlin, Java | No swallowed exception | detekt `SwallowedException`; Checkstyle `IllegalCatch` |
| Swift | No force unwrap, cast or try | SwiftLint `force_unwrapping`, `force_cast`, `force_try` |
| Python | Structured logging, no blind `except` | ruff `G004`, `BLE001` |
| Rust | No `unwrap` in application code | clippy `unwrap_used`, already in `cargo.md:19` |

**The scratch-project proof.** Outside the repo, in `"$TMPDIR/017-<task id>/<stack>/"`: the smallest
project the tool accepts, a lint config holding the table's rows, and one source file that breaks each
row. The linter must report every id. `As built` quotes the output line per id.

| Tool | On this Mac |
|---|---|
| Roslyn analyzers | `dotnet` 10 is installed: `dotnet build` |
| ESLint | `node` and `npx` are installed: `npx eslint` |
| ruff, mypy | `uv` is installed: `uvx ruff check`, `uvx mypy` |
| Error Prone, Checkstyle, detekt | Gradle is not on PATH. Run through the image: `docker run --rm -v "$P:/w" -w /w gradle:9.6.0-jdk21 gradle <task>` |
| clippy | `cargo` is not installed. Run through a `rust` image in Docker |
| SwiftLint | not installed. Try a SwiftLint image in Docker |

A row whose tool cannot be run here stays in the table and is listed as **unverified** in `As built` and
in `Status:`. A scratch project is never committed.

## 8. What G1 runs

In this order:

1. `python3 tools/plugin-surface-check.py` prints `OK`.
2. `python3 tools/skill-lint.py | tail -1` prints `0 findings`. That was the output on 2026-11-21.
3. `python3 tools/token-audit.py --violations-only` exits 0.
4. `python3 -m pytest tools/test_skill_lint.py -q` passes. Delete `.pytest_cache` afterwards.
5. `python3 tools/qa-version-check.py` prints `OK`.
6. The manifest holds both skills and ten in all:

   ```bash
   python3 - <<'PY'
   import json
   p = next(x for x in json.load(open('.claude-plugin/marketplace.json'))['plugins'] if x['name'] == 'engineering')
   s = p['skills']
   assert './engineering/architecture-audit' in s and './engineering/untested-code' in s and len(s) == 10, s
   print('OK')
   PY
   ```

7. All 15 stacks have the table and the lint-gap step. This prints nothing:

   ```bash
   for d in backend/dotnet backend/java backend/node backend/python backend/rust frontend/react \
            frontend/blazor mobile/react-native mobile/ios mobile/android desktop/macos \
            desktop/windows qa/dotnet qa/java qa/typescript; do
     git grep -q "## Enforced by the build" -- "$d/skills/rules/" || echo "no table: $d"
     git grep -q "Not enforced by the build" -- "$d/skills/rules/SKILL.md" || echo "no step: $d"
   done
   ```

8. Every tests rule file in §5 carries its line. Read the twelve files; no grep proves the wording.
9. Every `rules/SKILL.md` that L1–L5 touched lists exactly the files beside it. The lint cannot see a row
   that names a missing file.
10. The blind fixture run and the comparison with `EXPECTED.md` (§4).

This repo's `grep` is ugrep and misses lines. Every search in this plan is `git grep`, with
`--untracked` for files not yet committed.

## 9. Decisions

**D1 — The architecture audit runs on the existing audit engine, with a checklist `engineering` owns,
entered through `code-auditor`.** The engine already owns the rounds, the evidence rules and the report
template. Cost: the report has fixed sections A–E, never a per-feature decomposition, and its file name
ends `-conformance-r<N>.md`, which `engineering/rules/audits.md` does not match. That is true of every
conformance report today.

| Option | Verdict | Why |
|---|---|---|
| Engine plus an `engineering` checklist | chosen | No second copy of Mode A and B |
| A standalone lane with its own templates | rejected | Repeats the engine |
| A section in each stack's `standards-audit` | rejected (O2) | Only eight stacks have one, and `be-dotnet` is the only backend among them |

**D2 — Module depth is checked, never instructed (O3).** No rule file tells an agent to build deep
modules. Cost: an agent can still write a shallow module, and it is caught only by an audit or a review.

**D3 — The fix direction for a shallow module is to merge it, never to wrap it.** Consolidation is
proposed only for logic that two callers already duplicate. This keeps the lane inside `CLAUDE.md`
"Simplicity". Cost: the audit never proposes a shared framework, even where a team would want one.

**D4 — The depth and duplication rows live once, in the checklist, and `architecture-review` points at
them.** The frontend, mobile and desktop reviewers work on one diff and get no pointer. Cost: a project
with no backend plugin gets these checks from the audit only.

**D5 — The fixture is TypeScript, is never built, and is audited once, blind.** Cost: one model run on
one language is weak evidence. A run on a real repository stays unverified until the user makes one.

**D6 — Both new skills are front doors, and no stack agent gets a pointer to them.** Cost: two more
descriptions in every session of every project, about 100 tokens, and each skill fires only when its
description matches.

**D7 — The entry-point rule yields to the language's own test access.** Rust's in-module tests and
Swift's `@testable import` stay allowed. The rule bans widening visibility for a test and asserting calls
on an owned collaborator. Cost: a Rust or Swift test can still bind to a private function.

**D8 — Each stack carries its own lint table.** Cost: the `no-explicit-any` row appears in four plugins,
as its prose rule already does.

| Option | Verdict | Why |
|---|---|---|
| A table per stack, in the stack's rule files | chosen | A project installs one plugin per category, and each must be complete |
| One table per tool family, installed by `engineering:rules` | rejected | Puts stack content in the language-agnostic plugin |

**D9 — A lint row needs a *major* or *blocker* prose rule, an existing rule of the stack's linter, an id
checked against the documentation, and one firing in a scratch project.** Cost: rules no off-the-shelf
lint detects stay prose: constructor injection, one assertion per test, intent-named page objects.

**D10 — A `rules` skill reports lint gaps and never edits a project's lint config.** Cost: a person or a
stack agent still has to turn the rules on.

**D11 — No scheduled audit.** The guide runs its architecture skill from a cron job that also refactors.
Here an audit is started by a person and fixes nothing. Cost: decay is found only when someone asks.

**D12 — A1 built the checklist rows with a `Locate` column and a sixth "never a finding" bullet
(2026-11-21).** §3's table has `Check`, `Bad sign` and `Severity`; the checklist adds `Locate`, the
recipe the engine's Step 2 asks a checklist owner for, and shares two shell variables (`$IMPORTS`,
`$PUBLIC`) set once per language lane. The "never a finding" list gains Rust's in-file `#[cfg(test)]`
module and Swift's `@testable import`, which D7 already allows for the entry-point rule. Cost: two
language-specific patterns to maintain; visibility widened only for a test stays D1.

**D13 — FX1 added tests for four more modules, a `package.json` and a `tsconfig.json` to the fixture
(2026-11-21).** §4 names only `tests/pricing/`. Left alone, `courses`, `enrollment`, `catalog` and
`progress` hold rules and no test, which D3 ("a module with rules has a test through its surface") can
read as four more findings beside P4. So each of the four has one test file through its index, and the
four tests use no internal import. The plan's P4 line "No test imports `src/pricing/index.ts`" still
holds. `package.json` (name, `private`, `type`, no dependencies) and a strict `tsconfig.json` tell an
audit the language lane; the SDK behind N1 is the bare import `@acme/payments-sdk`, which resolves to
nothing because nothing is installed. Cost: the fixture is 35 files, not about 20, and G1 reads all of them.

**D14 — `fe-blazor` sets its analyzer severities in a `.globalconfig`, not a `.editorconfig`
(2026-11-21).** §7 names `.editorconfig` for every .NET stack. In a scratch Razor project an
`RS0030` severity written in `.editorconfig`, even in a `[*]` section, stayed a warning inside a `.razor`
`@code` block, and the same line in a `.globalconfig` (`is_global = true`) made it an error. The Razor
source generator's files are not under the project folder, so no `.editorconfig` section matches them.
`be-dotnet` and `desktop-windows` keep `.editorconfig`: their code is all handwritten `.cs`. Cost:
`fe-blazor` has one more config file beside the `.editorconfig` that already holds its style. The
alternative, a `.editorconfig` for the rows and a `.globalconfig` for `RS0030` alone, would split one table
across two files. Every later task checks whether its tool skips generated code, or configures it
separately, before it names the file the severities live in.

**D15 — L4 kept the rows its stacks already named, and counts a lint's own regex config as no new
rule (2026-11-21).** §7 admits a row only for a *major* or *blocker* prose rule detected by a rule the
linter ships, and writes no custom lint rule. Three rows fail that: SwiftLint `no_print` (prose *minor*)
and `no_gcd_main`, both `custom_rules` regexes that `project-setup` already told both Swift stacks to
write, and the ruff `PTH` family (prose *minor*), named in `python-project.md`. L4's own instruction was to
move lines the stacks already name into the table, so they became rows and the prose that listed them is
gone. Cost: three rows rest on a *minor* tag, and two are regexes the project keeps in `.swiftlint.yml`.
The reading that dropped them would have removed a documented behaviour from the setup skills. A row stays
only where the rule detects the whole construct the prose names: `PLW0603` is the `global` statement the
prose lists, `PGH003` is a `# type: ignore` without a code; L1's `CA2211`, which sees only externally
visible static fields, stays dropped.

**D16 — The `pattern-writer` scaffolds of `be-python` and `be-rust` disagree with the new tables, and
the tables win (2026-11-21).** The Python scaffold writes `ignore = ["ANN401"]`, and the Rust scaffold
writes `print_stdout`, `print_stderr` and `allow_attributes_without_reason` at `warn`. L4 did not edit them
(they are outside its files and carry a full config the table would then duplicate). Each table says in its
wired notes that it wins over a scaffold. Cost: a project scaffolded before a later edit starts with a
config the table calls a gap, and its first `rules` run lists the rows.

**D17 — L2 cites the checklist for two React Native rows, puts a `tsc` row in each lint file, and runs
the React proofs on ESLint 9 (2026-11-21).** §7 and D9 take a row from a *major* tag in the stack's rule
files, and name the table's `paths:` as `eslint.config.*`. Three readings differ. (1) `mobile-react-native`'s
rule files carry no TypeScript rule, but its conformance checklist tags `B1` (strict) and `B2` (no `any`)
*major*, so those two rows cite the checklist; the alternative was no `any` row and no `strict` row in the one
stack whose audit already checks both. (2) Each of the three tables has one `setting` row for `tsc`
(`strict`, and for be-node `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes`), the analogue of L1's
`<Nullable>`, so each file's `paths:` also matches `tsconfig*.json` and step 8 reads `tsconfig`; the
alternative left a *major* rule of `node-config.md` and `react.md` without a row. (3) `fe-react` and
`mobile-react-native` prove on ESLint 9.39.5 because `eslint-plugin-react` and `eslint-plugin-jsx-a11y`
peer ESLint 9 at most; `be-node` proves on 10.15.0. The tables name the version beside each proof. Cost: three
rule files load on every `tsconfig` read in a monorepo, about 2k tokens each, and a project on ESLint 10 that
wants the React rows must wait for the plugins.

**D18 — L3 proves the Android Lint rows in a real project, carries detekt's type-resolution wiring in the
table, and edits `pattern-writer` of `be-java` (2026-11-21).** The L3 prompt expected an Android scratch
project to need an SDK the image lacks, and the Android Lint rows to stay unverified. Three readings differ.
(1) The host has an Android SDK whose licences the user already accepted. A copy of its platform and
build-tools, mounted into `gradle:9.6.0-jdk21` run as `linux/amd64` (AGP's `aapt2` is an x86-64 binary and
does not start in the arm64 image), builds AGP 9.4.1, so every Android Lint row fired and none is
unverified. (2) detekt 1.23.8's Gradle plugin registers only `detekt` on AGP 9, and without a `classpath`
it skips type-resolution rules without a failure. Five of the seven detekt rows are such rules, so the
table carries the `classpath` and `jvmTarget` wiring and step 8 says those rows need it. The alternative,
rows with no such note, would let an audit pass while the rules ran on nothing. (3) The `be-java`
`pattern-writer` is outside §7's list for that stack. Its Rules sentence now names `java-lint.md` and its
validation line runs `checkstyleTest`, so the scaffold's own gate runs the two test rows. Android's
`project-setup` lost "and `GlobalScope`" from its `ForbiddenMethodCall` sentence, because `GlobalCoroutineUsage`
in the table detects it. Cost: a project on detekt 1.23.8 carries about fifteen lines of classpath wiring,
detekt 2 (alpha) is unverified, and the proof depends on the host's SDK copy.

**D19 — L5 builds the Java sleep, branch and `try` rows from Checkstyle's regex and token checks, gives
`qa-java` no Error Prone row, and leaves `.NET` rows out where no analyzer exists (2026-11-21).** Three
readings differ. (1) L3's note says neither Error Prone nor Checkstyle has a stock check for `Thread.sleep`, so
it gets no row. Checkstyle does ship `RegexpSinglelineJava`, a stock module configured with a regex, and D15
already counts a lint's own regex config as no new rule. The sleep row is on L5's own list, so `qa-java` has
`NoSleep`, `NoDependsOnMethods` and `ConfigAlwaysRun` as three configured instances of it. Cost: `NoSleep`
misses a statically imported `sleep(…)`, and `ConfigAlwaysRun` flags `alwaysRun = true` written on the next
line. (2) §7 names Error Prone for `qa-java`, and `qa-java-suite.md` names no Error Prone row: `EmptyCatch`
passes a block holding only a comment, so `EmptyCatchBlock` with `commentFormat` `^$` detects more, and
`CatchFail` did not fire on TestNG's `Assert.fail`. The alternative, two rows on one prose rule, would write
it twice. (3) The L5 prompt lists no sleep, no branch, no focused test, no skipped test without a reason and no
empty `catch` for all three stacks. `qa-dotnet` has the sleep row only: no stock analyzer detects a branch, a
loop or a `try` in a test body, a skip reason or an empty `catch` of a named type, and NUnit has no focus. Its
other rows come from mining `automation.md`. The `qa-typescript` file matches `tsconfig*.json` as well as
`eslint.config.*` and carries a `strict` row, as D17 did for the TypeScript stacks; §7 names only
`eslint.config.*`. Cost: a project that installs `qa-dotnet` finds no lint for the linear-test rule, which
stays a review finding (`B4` in the checklist).

## Answered questions (2026-11-21)

**O1 — Which of the guide's six items join the plan: all six.** The untested-code skill and the lint
tables were added on the user's answer.
**O2 — Where the architecture audit lives: a third lane of `code-auditor`.**
**O3 — Whether "keep modules deep" becomes a rule agents follow while writing: no, audit and review
only.**
**O4 — How the lane is proven: a seeded fixture, audited blind in the gate task.**

## 10. Tasks

What a halfway stop leaves: each landed task's own checks are green over the folders it touched. The
whole set in §8 has not run, and the lane has not been run on the fixture.

### A1 — The architecture lane, its checklist and its entry through code-auditor

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `engineering:audit-architecture` is registered and listed, `code-auditor` routes a
structure question to it, and `engineering/architecture-audit/references/checklist.md` holds the 16 checks
of §3 with a Locate recipe each. `python3 tools/plugin-surface-check.py` prints `OK`.
**Depends on:** —
**Budget:** ~130k. Drivers:
- `CLAUDE.md` 25k.
- This plan §1–§3 and D1–D4 8k.
- The engine and its report template ~12k.
- `code-auditor`, the audit command and `feature-audit` ~10k.
- `backend/dotnet/skills/standards-audit` as the pattern, the skill and the head of its checklist ~10k.
- `architecture-review` 4k.
- `engineering/writing-for-agents`, its `skill-mechanics.md` and `.skill-template/reviewer.SKILL.md` ~14k.
- The `engineering` manifest entry and `plugin-surface-check.py` ~8k.
- Writes ~30k. Tool output ~8k.

**Gate: own tests** — `python3 tools/plugin-surface-check.py`,
`python3 tools/skill-lint.py engineering backend/_shared/code-review | tail -1`,
`python3 tools/token-audit.py --violations-only`, `python3 -m pytest tools/test_skill_lint.py -q`. Do not
run the unfiltered `skill-lint`.

- `engineering/architecture-audit/SKILL.md`: name `audit-architecture`, a front door, with `When to use`
  and `When NOT to use`. It holds what §3 says the skill supplies and reads the engine by path. Draft
  description, to be checked against the 200-character budget:
  `Use when auditing a codebase's structure (shallow modules, forwarding layers, duplicated logic, tests tied to internals). Triggers "audit the architecture". Not for one feature (audit-feature).`
- `references/checklist.md`: sections A–E in the row format of
  `backend/dotnet/skills/standards-audit/references/conformance-checklist.md`, each section naming its
  owner, plus the "never a finding" list and the fix-direction rule.
- `engineering/standards-audit-engine/SKILL.md`: the lane table names the architecture checklist as a
  CONVENTION-lane rule set, and "Artifacts" allows `architecture` in the file name.
- `engineering/agents/code-auditor.md`: step 4 gains the ARCHITECTURE lane, the Steps table says what
  A1–A3 mean for it, and the description and the Report block name it. The agent stays under 14,000
  characters and its description under 360.
- `engineering/commands/audit.md`: the `description` and the closing paragraph name the third lane.
- `engineering/feature-audit/SKILL.md`: a "When NOT to use" row sends structure questions to the new
  lane. Under "Functionality narrative", one sentence: where `docs/business-model/glossary.md` exists, an
  identifier that uses an `Avoid` term is a finding, a code issue, minor, citing the glossary row.
- `backend/_shared/code-review/SKILL.md`: a "Module depth and duplication" section that points at
  sections B and C of the checklist, and one Procedure step. No row is copied.
- `.claude-plugin/marketplace.json`: `./engineering/architecture-audit` in the `engineering` skills.
  `tools/plugin-surface-check.py`: `audit-architecture` in `FRONT_DOORS`.
- **Not in A1:** the fixture (FX1), the catalog and the README (C1), and any run of the lane (G1).

**As built (2026-11-21):**
- Built: `engineering/architecture-audit/SKILL.md` (`audit-architecture`, 193-char description, 6,532-char
  body, front door, `When to use` / `When NOT to use`) and `references/checklist.md` (16 checks A1–E3, a
  Locate recipe per row). The engine's lane table and "Artifacts" line, `code-auditor` (step 4, the Steps
  table, description 351 chars, file 8,748), `commands/audit.md`, `feature-audit` (a "When NOT to use"
  row and the glossary sentence), `backend/_shared/code-review/SKILL.md` ("Module depth and duplication"
  and Procedure step 6, "Produce the table" is now 7), `marketplace.json` and `FRONT_DOORS` carry the
  lane.
- Gate, all green: `python3 tools/plugin-surface-check.py` prints `OK`; `skill-lint engineering
  backend/_shared/code-review` ends `0 findings`; `token-audit --violations-only` exits 0 with 0
  violations; `pytest tools/test_skill_lint.py` 95 passed.
- Recipes: run once on this repository for syntax only (`git grep`, `git ls-files`, `sort`, `uniq`, `cksum`
  all ran); none ran on the fixture. Whether they find the seeded defects is G1's blind run.
- Not committed: the queue commits, as the task prompt's own commit line is overridden by the queue.
- Divergences are D12.

### FX1 — The seeded fixture and its answer key

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `tools/fixtures/architecture-audit/course-platform/` holds the five planted defects and
the three decoys of §4, and `tools/fixtures/architecture-audit/EXPECTED.md` lists each with its expected
check id and file.
**Depends on:** —
**Budget:** ~60k. Drivers:
- `CLAUDE.md` 25k.
- This plan §3 (the check table only) and §4 6k.
- `glossary-format.md` 2k.
- Writes ~20k, about 20 small files.
- Tool output ~3k.

**Gate: none** — the fixture is read and never built, and nothing in `tools/` runs over it. The check is
the self-review in the last bullet.

- Write `course-platform/` as §4 describes: `docs/business-model/glossary.md`, `src/` with the modules
  `courses`, `enrollment`, `catalog`, `pricing`, `progress` and `payments`, and `tests/pricing/`.
- No comment anywhere in the fixture. No file or identifier name hints at a defect.
- Outside the planted defects the code follows the house rules, so the audit has nothing else to find.
- `EXPECTED.md`: the two tables of §4, with line numbers added, and the pass bar.
- Self-review, done when each line holds: P1's two files share at least 40 lines apart from names, and
  only one of them has the title-length check. Every method of `enrollment-service.ts` forwards.
  `src/pricing/index.ts` does not export `internal/discount-rules.ts`, and no test imports the index.
  `Student` is under `Avoid` in the glossary. Each decoy matches its "why it is fine".
- **Not in FX1:** reading `engineering/architecture-audit/`. The fixture is written from §3 and §4 alone.

**As built (2026-11-21):**
- `tools/fixtures/architecture-audit/course-platform/` is 35 files: `package.json` (no dependencies),
  a strict `tsconfig.json`, `docs/business-model/glossary.md`, 25 files under `src/` and 7 under `tests/`.
  `EXPECTED.md` sits beside it. Divergences are D13: a test file per rule-bearing module beside
  `tests/pricing/`, and the two config files.
- Planted at: P1 `src/courses/submit-course.ts:7-59` against `duplicate-course.ts:6-56`, the title check
  at `submit-course.ts:31-33`; P2 `src/enrollment/enrollment-service.ts:4-22`; P3
  `src/catalog/index.ts:4-5`; P4 `tests/pricing/discount-rules.test.ts:2`; P5
  `src/progress/student-progress.ts:1`. Decoys: N1 `src/payments/payment-gateway.ts:13-27`, N2
  `src/pricing/index.ts:6-10`, N3 `src/courses/find-course.ts:8-11` and
  `src/enrollment/enroll-learner.ts:23-26`.
- Self-review, each line held: a `diff` of the two P1 files with their names normalised shows four
  differences (the `MAX_TITLE_LENGTH` constant, the title check, `sourceCourseId`, `duplicatedFrom`), 55
  of 57 lines identical; only `submit-course.ts` has a title-length check. All four methods of
  `enrollment-service.ts` return `this.repository.<same name>(<same arguments>)`.
  `src/pricing/index.ts` exports `quote` and nothing else; no file under `tests/` imports it
  (`git grep -n --untracked "pricing'" -- tests` is empty). The glossary's `Learner` row has `Student`
  under `Avoid`; `git grep -n --untracked -i student` hits only `src/progress/` and
  `tests/progress/progress.test.ts`, which use `StudentProgress`. No comment: `git grep -n --untracked
  -E "^\s*(//|\*|/\*)"` over the fixture is empty.
- Unverified: the fixture was never typechecked or run, by design (D5). The tests are written to be
  valid Vitest, and the SDK shape in `payment-gateway.ts` is an invented one.
- Not committed: the queue commits, as the task prompt's own commit line is overridden by the queue.

### R1 — Unit tests go through the entry point, in CLAUDE.md and the tests rule files

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `CLAUDE.md` "Test code rules" holds the bullet of §5, and each of the twelve tests rule
files in §5 holds its line, tagged *major*.
**Depends on:** —
**Budget:** ~85k. Drivers:
- `CLAUDE.md` 25k.
- This plan §5 and D7 3k.
- The twelve tests rule files ~15k.
- The doubles and seams parts of ten unit-test skills ~25k.
- Writes ~8k. Lint output ~5k.

**Gate: own tests** — `python3 tools/skill-lint.py backend frontend mobile desktop | tail -1`,
`python3 tools/token-audit.py --violations-only`. Do not run the unfiltered `skill-lint`.

- Add the bullet to `CLAUDE.md`, word for word, directly above the coverage bullet.
- For each row of §5's table, read the stack's unit-test skill first, then add or extend the one line.
- Where a rule file has a version comment in its header, raise the version and the date.
- **Not in R1:** any unit-test skill's text, the QA rule files, and section D of the architecture
  checklist (A1).
- **As built (2026-11-21):** `CLAUDE.md` "Test code rules" holds the §5 bullet word for word, directly above
  the coverage bullet (`git grep -n "goes through the unit's public entry point" CLAUDE.md`). Each of the
  twelve rule files holds one new or extended line tagged *major*, and its header comment is raised from
  `v1 (2026-11-03)` to `v2 (2026-11-21)` (`v1 (2026-11-15)` for the three desktop files).
  - **Where the skills won (§5 rule):** `.NET`, Java and Node unit-test skills allow `Received()` /
    `verify()` / `toHaveBeenCalledWith` when the call is the contract (an event published, an email sent), and
    the Rust skill allows `mockall` for call counts. So those lines ban a call assertion only on *a collaborator
    the unit owns* and say a call that is the contract may be asserted. Windows already allowed a mock library
    for a call sequence that is the behaviour; its line is worded the same way.
  - **Node:** the old `@ts-expect-error` clause came out of the *minor* line and now sits in a *major* line of its
    own, with the un-exported-file import and the owned-collaborator call assertion.
  - **Rust:** the line also bans `pub(crate)` widening, and keeps in-module `#[cfg(test)]` access (D7).
  - **Android:** names `internal` and `@VisibleForTesting` as the widenings.
  - **Outside R1's files:** `tools/token-audit.py --violations-only` was red before R1 touched anything
    (`product/skills/codebase-survey/SKILL.md` description at 217 chars, over the 200 budget, from commit
    6ede62fd). Shortened to 196 chars, wording otherwise unchanged, so the gate is green.
  - **Gate:** `python3 tools/skill-lint.py backend frontend mobile desktop | tail -1` → `0 findings`;
    `python3 tools/token-audit.py --violations-only` → exit 0.
  - **Not committed:** the queue commits, so there is no `docs: 017 R1` commit from this session.

### U1 — The untested-code skill

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `engineering:untested-code` is registered and listed, and its `SKILL.md` teaches the six
steps of §6, each with its "done when". `python3 tools/plugin-surface-check.py` prints `OK`.
**Depends on:** A1. Both edit the `engineering` entry of `.claude-plugin/marketplace.json` and
`FRONT_DOORS` in `tools/plugin-surface-check.py`.
**Budget:** ~80k. Drivers:
- `CLAUDE.md` 25k.
- This plan §5–§6 and D6 4k.
- `engineering/writing-for-agents` and `skill-mechanics.md` ~12k.
- `quality-constraints` and `verify-before-done` as patterns ~6k.
- `risk-hotspots.md` 3k. The skill template 2k.
- The manifest entry and `plugin-surface-check.py` ~8k.
- Writes ~12k. Tool output ~6k.

**Gate: own tests** — `python3 tools/plugin-surface-check.py`,
`python3 tools/skill-lint.py engineering backend/dotnet/skills/unit-testing | tail -1`,
`python3 tools/token-audit.py --violations-only`, `python3 -m pytest tools/test_skill_lint.py -q`. Do not
run the unfiltered `skill-lint`.

- `engineering/untested-code/SKILL.md` from the template that fits, with `When to use` and
  `When NOT to use`: the six steps, the evidence, and the three pointers of §6.
- `When NOT to use` names: code that already has tests, a red gate (`quality-constraints`), and finding a
  bug's cause (`debugging`).
- `.claude-plugin/marketplace.json`: `./engineering/untested-code` in the `engineering` skills, and the
  plugin `description` names both new skills. `tools/plugin-surface-check.py`: `untested-code` in
  `FRONT_DOORS`.
- `backend/dotnet/skills/unit-testing/references/risk-hotspots.md:47`: a pointer to the skill.
- **Not in U1:** pointers in stack agents (D6), and the catalog (C1).

**As built (2026-11-21):**
- Built: `engineering/untested-code/SKILL.md` (`untested-code`, 187-char description, front door, `When to use` / `When NOT to use`): the six steps of §6, each with a "done when"; the evidence; the three pointers. Step 5's check is two things per behaviour called wrong (a test whose name says it pins current behaviour, and a findings row) plus a production diff since step 4 with no fixing edit.
- Wired: `./engineering/untested-code` in the `engineering` skills of `marketplace.json`, `untested-code` in `FRONT_DOORS` (`tools/plugin-surface-check.py`), and `risk-hotspots.md:47` ends with a pointer. The plugin description now names the architecture audits (A1 had not) and `untested-code`. No stack agent was touched (D6).
- Gate, all green: `plugin-surface-check.py` prints `OK`; `skill-lint engineering backend/dotnet/skills/unit-testing` ends `0 findings`; `token-audit --violations-only` exits 0 with 0 violations; `pytest tools/test_skill_lint.py` 95 passed.
- Not committed: the queue commits. No divergence from the plan.

### L1 — Lint tables for the .NET stacks, and the shape the other four tasks copy

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `be-dotnet`, `fe-blazor` and `desktop-windows` each carry an `## Enforced by the build`
table in the rule file §7 names, a setup pointer and an audit check where §7 lists one, and the lint-gap
step in their `rules` skill. Every row's id fired once in a scratch project, or is listed as unverified.
**Depends on:** —
**Budget:** ~150k. Drivers:
- `CLAUDE.md` 25k.
- This plan §7, D8–D10 6k.
- The three stacks' rule files, mined for *major* rules ~30k.
- Two `project-setup` skills, the relevant parts ~12k.
- Three `rules/SKILL.md` ~9k. Two checklists, the tooling sections ~8k.
- Analyzer documentation lookups ~20k.
- Writes ~20k. Scratch-project output ~20k.

**Gate: own tests** —
`python3 tools/skill-lint.py backend/dotnet frontend/blazor desktop/windows | tail -1`,
`python3 tools/token-audit.py --violations-only`, and §7's scratch-project proof with `dotnet build`. Do
not run the unfiltered `skill-lint`.

- Per stack, in this order: mine the rule files, check each candidate id, prove it in the scratch
  project, then write the four placements of §7.
- `desktop-windows`: C# lanes only. The C++/WinRT lane's `/W4 /WX` rule stays where it is.
- A new rule file copies the frontmatter and header-comment form of a file beside it, and is added to
  step 5 of that stack's `rules` skill.
- **Before stopping, rewrite the L2–L5 prompt blocks** wherever the shape landed differently from §7: a
  heading, a column, the wording of the lint-gap step.
- **Not in L1:** `qa-dotnet` (L5), and writing any custom analyzer.

**As built (2026-11-21):**
- Built: `backend/dotnet/skills/rules/dotnet-lint.md` (new, 15 rows), `frontend/blazor/skills/rules/blazor-lint.md` (new, 5 rows) and an `## Enforced by the build` section at the end of `desktop/windows/skills/rules/package-config.md` (10 rows, `**/.editorconfig` added to its `paths:`, header now v2). Setup pointers: `frontend/blazor/skills/project-setup/SKILL.md` ("Analyzer rules" beside `.editorconfig`, plus the rules line and the exit gate) and `desktop/windows/skills/project-setup/SKILL.md` (a bullet after "Directory.Build.props and central packages"). Checklist rows: `N13` (be-dotnet) and `B13` (desktop-windows, index row now `B1–B13`), each appended after the section's last row, never renumbered. Lint-gap step: step 8 `Report lint gaps` in the three `rules/SKILL.md`, a bullet for the config files in step 5, and the report line `Not enforced by the build: none | <id: house rule>   (one line per row)`. The two `code-review/SKILL.md` that list their rule files name the new file.
- The shape L2–L5 copy: the table row is `| House rule (file, section) | Tool | Rule id or setting | Level |`, `Level` is `error` or `setting`; under it the two severity lines, each on its own line; then `How the rows are wired:` bullets (where the severity lives, caveats a user hits); then the tool's own config file, in a fenced block, when the rows need one (`BannedSymbols.txt`). A new file's header comment reads `<plugin> rules v1 (2026-11-21): <topic>. Ids checked against the analyzers' documentation on 2026-11-21 (<versions>). Installed by …`. An existing file goes v1 → v2 with the same sentence.
- Candidate ids (§7), checked against the docs fetched 2026-11-21 (`learn.microsoft.com` source in `dotnet/docs`, `microsoft.github.io/vs-threading`, `roslyn-analyzers` help, `nunit.analyzers`, `dotnet/efcore` source) and each fired: `VSTHRD002`, `CA2254`, `CA2016`, `RS0030` (`Thread.Sleep`), `<Nullable>`, `<TreatWarningsAsErrors>`. None dropped. Ids added from the stack's own rules: `VSTHRD100`, `CA2200`, `CA1031`, `EF1002`, `EF1003`, `NUnit1012`, and `RS0030` for `new HttpClient()`, time and ids, lazy loading, `Migrate`/`EnsureCreated`, `UseInMemoryDatabase`, `Task.Delay`.
- Dropped for failing D9 (named so L5 does not re-add them): `CA2211` (flags only externally visible static fields, so "no static mutable state" is half-detected); `CA5359` (covers only `ServicePointManager.ServerCertificateValidationCallback`, not the `HttpClientHandler` callback `dotnet-networking.md` bans); no analyzer for constructor injection, a service locator, `!`/`#nullable disable`, `dynamic`, one assertion per test, or an empty `catch` of a specific type. `EF1003` exists only from EF Core 10 (`EF1002` is in 8, 9 and 10), so the row says so. `TreatWarningsAsErrors` is a row only on desktop-windows, where `csharp.md` tags it *major*; `be-dotnet` does not tag it and `blazor-config.md` tags it *minor*, so those two have no such row.
- Surprises that changed the text: `VSTHRD100` flags an event handler too (desktop-windows: each permitted handler carries a `[SuppressMessage]` with a `Justification`, proven to silence it). `Microsoft.VisualStudio.Threading.Analyzers` turns `VSTHRD200` on as a warning, so each table says the project sets it to `suggestion`. Roslyn skips Razor-generated code for `VSTHRD002`, `VSTHRD100` and `CA2016` (nothing fires in a `@code` block; `.razor.cs` is checked), and only `RS0030` reaches it, but only when its severity is in a `.globalconfig`, never a `.editorconfig` section (D14). `RS0030` with `M:Type.Member` and no parameter list matches the parameterless overload only: each overload is its own line.
- Proof, `dotnet build` (SDK 10.0.301) in `$TMPDIR/017-L1/{dotnet,blazor,windows}`, ids at `error` in the config and `TreatWarningsAsErrors` off except on windows (scratch kept out of the repo). The windows project is a `net10.0-windows10.0.26100.0` library built with `EnableWindowsTargeting`; no WinUI app project was built on this Mac. One output line per id (be-dotnet; the other two print the same ids):
  - `src/Violations.cs(7,46): error VSTHRD002: Synchronously waiting on tasks or awaiters may cause deadlocks. Use await or JoinableTaskFactory.Run instead.`
  - `src/Handler.cs(7,23): error VSTHRD100: Avoid "async void" methods, because any exceptions not handled by the method will crash the process`
  - `src/Violations.cs(19,15): error CA2016: Forward the 'ct' parameter to the 'ReadToEndAsync' method or pass in 'CancellationToken.None' explicitly to indicate intentionally not propagating the token`
  - `src/Violations.cs(13,67): error CA2254: The logging message template should not vary between calls to 'LoggerExtensions.LogInformation(ILogger, string?, params object?[])'`
  - `src/Violations.cs(25,48): error CA2200: Re-throwing caught exception changes stack information`
  - `src/Violations.cs(31,9): error CA1031: Modify 'Blanket' to catch a more specific allowed exception type, or rethrow the exception`
  - `src/Persistence.cs(13,66): error EF1002: Method 'FromSqlRaw' inserts interpolated strings directly into the SQL, without any protection against SQL injection.` and `(15,66): error EF1003: Method 'FromSqlRaw' inserts concatenated strings …`
  - `tests/ViolationTests.cs(8,6): error NUnit1012: The async test method must have a non-void return type`
  - `RS0030`, one line per banned symbol, all fired: `HttpClient.HttpClient()`, `DateTime.UtcNow`, `DateTime.Now`, `DateTimeOffset.Now`, `DateTimeOffset.UtcNow`, `Guid.NewGuid()`, `ProxiesExtensions`, `RelationalDatabaseFacadeExtensions.Migrate(DatabaseFacade)`, `…MigrateAsync(DatabaseFacade, CancellationToken)`, `DatabaseFacade.EnsureCreated()`, `…EnsureCreatedAsync(CancellationToken)`, and in the test list `Thread.Sleep(int)`, `Thread.Sleep(TimeSpan)`, `Task.Delay(int)`, `Task.Delay(TimeSpan)`, `InMemoryDbContextOptionsExtensions`. Example: `src/Violations.cs(36,30): error RS0030: The symbol 'DateTime.UtcNow' is banned in this project: Inject TimeProvider`.
  - `<Nullable>`: `src/Violations.cs(42,20): warning CS8600: Converting null literal or possible null value to non-nullable type.` (an `error` under `TreatWarningsAsErrors`, shown on the windows project: `src/Violations.cs(32,20): error CS8600`).
  - fe-blazor: `src/Details.razor.cs(5,47): error VSTHRD002`, `(7,24): error VSTHRD100`, `(12,15): error CA2016`; `src/Orders.razor(13,36): error RS0030: The symbol 'HttpClient.HttpClient()' is banned in this project`; `tests/WaitTests.cs(8,29): error RS0030: The symbol 'Thread.Sleep(int)'`, `(11,46): … 'Task.Delay(int)'`.
  - desktop-windows: `src/Violations.cs(26,28): error RS0030: The symbol 'Thread.Sleep(int)' is banned in this project: The UI thread never blocks`, plus the ids above.
- Gate, all green: `python3 tools/skill-lint.py backend/dotnet frontend/blazor desktop/windows | tail -1` prints `0 findings`; `python3 tools/token-audit.py --violations-only` exits 0 with 0 violations; the proof above.
- Not committed: the queue commits. Nothing unverified: every table row fired. The one decision that differs from §7 is D14.

### L2 — Lint tables for the TypeScript stacks

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `be-node`, `fe-react` and `mobile-react-native` each carry the table, the setup pointer
and audit check where §7 lists one, and the lint-gap step. Every row's id fired once under `npx eslint`
in a scratch project, or is listed as unverified.
**Depends on:** L1, for the shape as it landed.
**Budget:** ~150k. Drivers:
- `CLAUDE.md` 25k.
- This plan §7, D8–D10 and L1's `As built` 7k.
- `backend/dotnet/skills/rules/dotnet-lint.md` as the pattern 2k.
- The three stacks' rule files ~35k.
- Two `project-setup` skills, the lint parts ~8k.
- Three `rules/SKILL.md` ~9k. Two checklists ~8k.
- typescript-eslint and plugin documentation lookups ~20k.
- Writes ~18k. Scratch-project output ~18k.

**Gate: own tests** —
`python3 tools/skill-lint.py backend/node frontend/react mobile/react-native | tail -1`,
`python3 tools/token-audit.py --violations-only`, and §7's scratch-project proof with `npx eslint`. Do not
run the unfiltered `skill-lint`.

- Per stack: mine, check, prove, then write the four placements.
- Rule ids follow the stack's version lane: the flat config, and the typescript-eslint major the stack's
  skills name.
- `mobile-react-native` builds on `eslint-config-expo/flat`. Rows it already turns on are listed as
  provided by the preset.
- **Not in L2:** `qa-typescript` (L5), and a second formatter or linter the stack does not already name.

**As built (2026-11-21):**
- Built: `backend/node/skills/rules/node-lint.md` (new, 15 rows), `frontend/react/skills/rules/react-lint.md` (new, 22 rows) and `mobile/react-native/skills/rules/react-native-lint.md` (new, 15 rows). Each has `paths:` on `eslint.config.*` and `tsconfig*.json` (the last for its `tsc` `setting` row), the header comment v1 (2026-11-21) with the versions, the two severity lines, `How the rows are wired:`, and the stack's `eslint.config` in a fenced block. The proof ran the block extracted from each file, not a hand copy. Setup pointers: `frontend/react/skills/project-setup/SKILL.md` ("Lint rules" bullet in the quality gates, the `Rules` line and the exit-gate line) and `mobile/react-native/skills/project-setup/SKILL.md` ("Lint rules" bullet in "Quality gates every project ships with"; that skill has no exit gate, so the bullet is the gate). Checklist rows `S13` (fe-react; its index has no row ranges) and `B13` (mobile-react-native, index now `B1–B13`), each appended after the section's last row. Step 8 `Report lint gaps`, a step-5 lint-config bullet and the report line in the three `rules/SKILL.md`; the three `code-review/SKILL.md` name the new file.
- Candidate ids (§7), checked against tagged sources fetched 2026-11-21 (typescript-eslint v8.73.0 `docs/rules`, ESLint v10.15.0 `docs/src/rules`, eslint-plugin-react v7.37.5, eslint-plugin-jsx-a11y v6.10.2, eslint-plugin-eslint-comments v4.8.1, the react-hooks 7.1.1 README and `react.dev/reference/eslint-plugin-react-hooks`, eslint-plugin-react-native v5.0.0, the `eslint-config-expo` 57.0.2 README and its loaded config, Next 15.5.29 `03-eslint.mdx`) and each fired: `@typescript-eslint/no-explicit-any`, the five `no-unsafe-*`, `no-floating-promises`, `no-misused-promises`, `ban-ts-comment` with `allow-with-description`, `@eslint-community/eslint-comments/require-description`, `react-hooks/rules-of-hooks`, `react-hooks/exhaustive-deps`, `react/no-array-index-key`. None dropped. One replaced: `react/no-unstable-nested-components` by `react-hooks/static-components`, since both fire on a component defined in a component and the second is already in the plugin's `recommended` set at `error`, so a project gets one report, not two. `playwright/*` stays with L5.
- Ids added from the stacks' own rules: `@typescript-eslint/no-non-null-assertion`, `switch-exhaustiveness-check` with `allowDefaultCaseForExhaustiveSwitch: false`, `no-console`, `no-alert`; `no-restricted-properties` for `process.env` and `$queryRawUnsafe`/`$executeRawUnsafe`; `no-restricted-syntax` for `as unknown as`, for a test body's control flow, for `container.querySelector`, for `allowFontScaling={false}` and for the `'use client'` directive; `no-restricted-globals` for `setTimeout` and `vi` in tests and `window`/`document` in the app; `no-restricted-imports` for `@react-navigation/*`, `TouchableOpacity`, `Image`, `vitest` and the DOM Testing Library; `react-hooks/set-state-in-effect`; `react/jsx-no-constructed-context-values`, `react/jsx-no-target-blank`, `react/jsx-no-leaked-render`; `jsx-a11y/{no-static-element-interactions,click-events-have-key-events,alt-text,label-has-associated-control,tabindex-no-positive}`; `react-native/no-raw-text`; and `tsc` `setting` rows (`strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`).
- Dropped for failing D9 (named so L5 does not re-add them): `@typescript-eslint/no-unsafe-type-assertion` (flags every narrowing `as`, so it is wider than "no `as unknown as`", which is a `no-restricted-syntax` selector instead); `react-hooks/purity` (sees `Date.now()` and `Math.random()` only, the prose bundles `window` and `localStorage`); core `no-empty` (an empty `catch`, not one that returns `null`); `react-native-a11y/*` (3.5.1 peers ESLint 8, and predates the `role`/`aria-*` props the rule prescribes); `eslint-plugin-testing-library` (no stack skill names it); `react-hooks/exhaustive-deps` for mobile-react-native (only `project-setup` says "keep it on", untagged); module reach-in for be-node (the stack already names dependency-cruiser, not a lint).
- Surprises that changed the text: ESLint 10.15 installs with typescript-eslint and not beside eslint-plugin-react or eslint-plugin-jsx-a11y (peer 9 at most, `ERESOLVE`), so the React and React Native proofs ran on ESLint 9.39.5 and the Node one on 10.15.0; typescript-eslint 8.73 declares TypeScript below 6.1, so the scratch pinned 6.0.3 (latest is 7.0.2). `eslint-config-next` 16.4.6 sets `exhaustive-deps` and `alt-text` to `warn` and `jsx-no-target-blank` to `off`, ignores `.next/**`, and ships react-hooks 7; `eslint-config-next@15.5.29` ships react-hooks 5.2.0 (no `set-state-in-effect`, no `static-components`) and works with react-hooks 7.1.1 registered after `FlatCompat`. `react/jsx-no-target-blank` flags `rel="noopener"` alone unless `allowReferrer: true`, and the house rule says `noopener`. `eslint-config-expo` 57.0.2 sets `rules-of-hooks`, `set-state-in-effect` and `static-components` to `error`, `exhaustive-deps` to `warn`, ignores only `android/app/build`, and does not register `eslint-plugin-react-native`. `no-restricted-syntax`, `no-restricted-properties` and `no-restricted-globals` take one options array per file and a later config object replaces it, so the test and config-folder blocks repeat the entries. A type-aware rule never silently skips: a file outside the `tsconfig` `include` fails with a parsing error (shown for `.expo/types/router.d.ts` and `expo-env.d.ts`).
- D14 answer: ESLint does not skip generated code. It lints every file `ignores` does not name (only `node_modules` and `.git` by default), and dot folders count. A `src/generated/client.ts` with an `any` reported `no-explicit-any` in all three scratch projects until the folder was in `ignores`; `.expo/types/router.d.ts` did the same in the Expo one. The Next preset ignores `.next/**` on its own. The severity is not read from another file: it is the same `eslint.config.*`. Each table says so and each config block lists the folders.
- Proof, `npx eslint` in `$TMPDIR/017-L2/{node,react,rn}` (Node 22.23.4; kept out of the repo). One line per id, quoted from the run of the extracted config block:
  - be-node (ESLint 10.15.0, typescript-eslint 8.73.0): `src/violations.ts:5:38 error Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any`; `:11:9 Unsafe assignment of an `any` value  no-unsafe-assignment`; `:19:8 Unsafe argument of type `any` assigned to a parameter of type `string`  no-unsafe-argument`; `:18:3 Unsafe call of an `any` typed value  no-unsafe-call`; `:12:19 Unsafe member access .id on an `any` value  no-unsafe-member-access`; `src/strict-violations.ts:2:3 Unsafe return of a value of type `any`  no-unsafe-return`; `:23:10 Forbidden non-null assertion  no-non-null-assertion`; `:27:11 Switch is not exhaustive. Cases not matched: "tri"` and `:44:5 The switch statement is exhaustive, so the default case is unnecessary  switch-exhaustiveness-check`; `src/orders.test.ts:23:3 Promises must be awaited, end with a call to .catch …  no-floating-promises`; `:59:17 Promise returned in function argument where a void return was expected  no-misused-promises`; `:70:3 Use "@ts-expect-error" instead of "@ts-ignore" …` and `:72:3 Include a description after the "@ts-expect-error" directive …  ban-ts-comment`; `:74:0 Unexpected undescribed directive comment …  @eslint-community/eslint-comments/require-description`; `src/orders.test.ts:18:3 Unexpected console statement  no-console`; `:87:10 'process.env' is restricted from being used. Read configuration through loadConfig()`, `:91:9 '$queryRawUnsafe' is restricted …` and `:92:9 '$executeRawUnsafe' is restricted …  no-restricted-properties` (`src/config/config.ts` reads `process.env` and reports nothing); `:50:10 No as unknown as X` and `src/orders.test.ts:6:3 A test body is linear …  no-restricted-syntax`; `src/orders.test.ts:22:34 Unexpected use of 'setTimeout'  no-restricted-globals`. `tsc --noEmit` (TypeScript 6.0.3): `src/strict-violations.ts(1,29): error TS7006`, `(7,10): error TS18048: 'first' is possibly 'undefined'`, `(14,14): error TS2375 … 'exactOptionalPropertyTypes: true'`.
  - fe-react (Next 16.4.6 preset, ESLint 9.39.5, react-hooks 7.1.1): `src/Violations.tsx:10:5 React Hook "useState" is called conditionally  react-hooks/rules-of-hooks`; `:15:6 React Hook useEffect has a missing dependency: 'value'  react-hooks/exhaustive-deps`; `:14:5 Error: Calling setState synchronously within an effect can trigger cascading renders  react-hooks/set-state-in-effect`; `:23:15 Error: Cannot create components during render  react-hooks/static-components`; `:27:51 Do not use Array index in keys  react/no-array-index-key`; `:31:31 The object passed as the value prop to the Context provider changes every render  react/jsx-no-constructed-context-values`; `:37:7 Using target="_blank" without rel="noreferrer" or rel="noopener" …  react/jsx-no-target-blank`; `:38:7 Avoid non-native interactive elements …  jsx-a11y/no-static-element-interactions` and `Visible, non-interactive elements with click handlers must have at least one keyboard listener  jsx-a11y/click-events-have-key-events`; `:39:7 img elements must have an alt prop …  jsx-a11y/alt-text`; `:40:7 A form label must be associated with a control  jsx-a11y/label-has-associated-control`; `:41:24 Avoid positive integer values for tabIndex  jsx-a11y/tabindex-no-positive`; `:38:27 Unexpected confirm  no-alert`; `:6:34 Unexpected any  no-explicit-any`; `src/unsafe.ts:13:14 no-unsafe-argument`, `:8:3 no-unsafe-call`, `:7:19 no-unsafe-member-access`, `:9:3 no-unsafe-return` and `Violations.tsx:46:14 no-unsafe-assignment`; `Violations.tsx:49:10 No as unknown as X`, `src/Violations.test.tsx:8:3 A test body is linear …` and `:26:18 Query by role or label, never by selector  no-restricted-syntax`; `src/Violations.test.tsx:25:34 Unexpected use of 'setTimeout'  no-restricted-globals`; `:27:3 Promises must be awaited … ` on an unawaited `userEvent.setup()` call, `no-floating-promises`; `:53:3 Use "@ts-expect-error" instead of "@ts-ignore"  ban-ts-comment`; `:57:0 Unexpected undescribed directive comment  require-description`. `tsc`: `src/s.tsx(1,19): error TS7006`. The Vite lane (no preset, `reactHooks.configs.flat.recommended` plus the plugins registered) fired all 20 ids; Next 15.5.29 with `FlatCompat` and react-hooks 7.1.1 fired the four hook ids.
  - mobile-react-native (`eslint-config-expo` 57.0.2, ESLint 9.39.5, `@testing-library/react-native` 14.1.0): `src/Violations.tsx:14:5 Error: Calling setState synchronously within an effect …  react-hooks/set-state-in-effect` (provided by the preset); `:17:11 Raw text (some text) cannot be used outside of a <Text> tag  react-native/no-raw-text`; `:19:8 Potential leaked value that might cause unintentionally rendered values or rendering crashes  react/jsx-no-leaked-render`; `:24:46 Do not use Array index in keys  react/no-array-index-key`; `:8:34 Unexpected any  no-explicit-any`; `src/Violations.test.tsx:26:3 Promises must be awaited …` on an unawaited RNTL 14 `render(...)`, `no-floating-promises`; `no-restricted-imports`: `:1:1 'vitest' import is restricted`, `:2:1 '@testing-library/react' import is restricted`, `Violations.tsx:2:10 'Image' import from 'react-native' is restricted`, `:2:17 'TouchableOpacity' …`, `:3:1 '@react-navigation/native' import is restricted … by a pattern`, and `'@testing-library/dom' import is restricted` in a second file; `no-restricted-globals`: `Violations.tsx:30:22 Unexpected use of 'window'`, `:31:21 … 'document'`, `src/Violations.test.tsx:25:34 … 'setTimeout'`, and `Unexpected use of 'vi'` in a file with no import; `no-restricted-syntax`: `Violations.tsx:1:1 'use client' is a web directive`, `:21:15 Text scales with the system setting; never lock it`, `Violations.test.tsx:9:3 A test body is linear …`. `tsc`: `src/s.tsx(1,19): error TS7006`.
- Gate, all green: `python3 tools/skill-lint.py backend/node frontend/react mobile/react-native | tail -1` prints `0 findings`; `python3 tools/token-audit.py --violations-only` exits 0; the proof above.
- Not committed: the queue commits. Verified: every row fired. Unverified: the `tsc` row's behaviour on TypeScript 7 (typescript-eslint declares it unsupported, so the typed rows were not run there); the mobile row for `@react-navigation/*` on a project that is not on Expo Router (the table says to drop it); Next 15 beyond the four hook ids.

### L3 — Lint tables for the JVM stacks

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `be-java` and `mobile-android` each carry the table, the setup pointer and audit check
where §7 lists one, and the lint-gap step. Every row's id fired once in a scratch Gradle project run
through Docker, or is listed as unverified.
**Depends on:** L1, for the shape as it landed.
**Budget:** ~130k. Drivers:
- `CLAUDE.md` 25k.
- This plan §7, D8–D10 and L1's `As built` 7k.
- The pattern file 2k.
- The two stacks' rule files ~30k.
- `backend/java/skills/pattern-writer/SKILL.md` around line 267, and Android's `project-setup` ~8k.
- Two `rules/SKILL.md` ~6k. One checklist ~4k.
- Error Prone, Checkstyle and detekt documentation lookups ~20k.
- Writes ~14k. Docker and Gradle output ~15k.

**Gate: own tests** — `python3 tools/skill-lint.py backend/java mobile/android | tail -1`,
`python3 tools/token-audit.py --violations-only`, and §7's scratch-project proof through the
`gradle:9.6.0-jdk21` image. Do not run the unfiltered `skill-lint`.

- Per stack: mine, check, prove, then write the four placements.
- detekt rule names changed between majors. Use the names of the major the Android skills pin.
- ArchUnit is a test, not a lint. It gets no row.
- **Not in L3:** `qa-java` (L5).

**As built (2026-11-21):**
- Built: `backend/java/skills/rules/java-lint.md` (new, 9 rows, `paths:` on the Gradle build files and `config/checkstyle/*.xml`); an `## Enforced by the build` section at the end of `mobile/android/skills/rules/android-build.md` (18 rows: 2 `setting`, 16 `error`; header now v2; `paths:` gained `**/detekt.yml` and `**/lint.xml`; line 25 became the two `setting` rows and a shorter ktlint line). Android pointer: a "Lint rules" bullet in `project-setup/SKILL.md` plus an exit-gate line. Check row `A20` (index `A1–A20`). Step 8 `Report lint gaps`, a step-5 bullet and the report line in both `rules/SKILL.md`. `java-lint.md` added to the list in `backend/java/skills/code-review/SKILL.md`. Also `backend/java/skills/pattern-writer/SKILL.md` (D18).
- Candidates (§7) checked against the docs (errorprone.info/bugpatterns, checkstyle.org 14.4, detekt.dev 1.23.8) and each fired: `IllegalCatch`, `UnsafeCallOnNullableType`, `GlobalCoroutineUsage`, `InjectDispatcher`. Not used: `SwallowedException` (its prose rule, a typed reason and never `message`, is wider than what it detects, and it was not run). Ids added from the stacks' own rules: Error Prone `NonFinalStaticField`, `SystemOut`, `CatchAndPrintStackTrace`, `EmptyCatch`, `UnusedException`, `InterruptedExceptionSwallowed`; Checkstyle `IllegalInstantiation`, `IllegalType`, `IllegalImport`, `IllegalToken`; detekt `SleepInsteadOfDelay`, `SuspendFunSwallowedCancellation`, `EmptyCatchBlock`, `ForbiddenMethodCall`; Android Lint `UnspecifiedImmutableFlag`, `UnsafeIntentLaunch`, `ExportedContentProvider`, `ExportedService`, `InsecureBaseConfiguration`, `AcceptsUserCertificates`, `WakelockTimeout`, `NotifyDataSetChanged`, `HardcodedText`, `PxUsage`, `ContentDescription`, `ModifierParameter`, `CoroutineCreationDuringComposition`.
- Dropped for failing D9 (named so L5 does not re-add them): no stock check for `Thread.sleep` in Java (Error Prone 2.53 has none, Checkstyle has no method-call ban, `MatchXpath` and `RegexpSingleline` are custom rules), `@Autowired` on a field, `@Transactional` self-invocation, SQL by concatenation, Lombok `@Data` on an entity, `@Enumerated(STRING)`, `BigDecimal` compared with `isEqualTo` (`BigDecimalEquals` sees only `.equals`), "domain classes carry no Spring annotations" (ArchUnit). Android: `CleartextTraffic` and `UsesCleartextTraffic` are not ids in Lint 32.4 (`Unknown issue id`), so `usesCleartextTraffic="true"` has no row.
- Surprises that changed the text: detekt 1.23.8's plugin registers only `detekt` on AGP 9 and, with no `classpath`, skips its type-resolution rules without a failure (D18); Error Prone checks every compiled source, annotation-processor output and a class marked `@Generated` included, and `excludedPaths` is the only way out; Checkstyle reads a generated directory added to `sourceSets.main.java` and never annotation-processor output; Android Lint (`checkGeneratedSources` off) and detekt (`src/main`, `src/test` only) skip generated code; `@SuppressWarnings("checkstyle:illegalcatch")` works only with `SuppressWarningsFilter` and `SuppressWarningsHolder`; `IllegalType` with `memberModifiers` skips locals and parameters are unaffected; `warningsAsErrors` makes `GradleDependency`, `OldTargetApi` and `UnusedResources` fail a fresh project.
- Proof. Java: `gradle:9.6.0-jdk21` in `$TMPDIR/017-L3/java`, Error Prone 2.53.0 (plugin 5.2.0), Checkstyle 14.4.0. One line per id: `Violations.java:7: error: [NonFinalStaticField] Static fields should almost always be final.`, `:18: error: [SystemOut] Production code should not print to standard out or standard error.`, `:25: error: [CatchAndPrintStackTrace] Logging or rethrowing exceptions should usually be preferred to catching and calling printStackTrace`, `:32: error: [EmptyCatch] Caught exceptions should not be ignored`, `:39: error: [UnusedException] This catch block catches an exception and re-throws another, but swallows the caught exception`, `:47: error: [InterruptedExceptionSwallowed] This catch block appears to be catching an explicitly declared InterruptedException as an Exception/Throwable`; Checkstyle `Violations.java:48:11: Catching 'Exception' is not allowed. [IllegalCatch]`, `:63:16: Instantiation of java.lang.Thread should be avoided. [IllegalInstantiation]`, `:9:19`, `:11:27`, `:66:26: Usage of type 'Optional' is not allowed. [IllegalType]` (field, parameter, record component; the two local `Optional`s were not flagged), and in `checkstyleTest` `ViolationTest.java:4:1: Illegal import - org.springframework.boot.test.context.SpringBootTest. [IllegalImport]` (also `MockBean`, `DataJpaTest`, `WebMvcTest`) and `:16:11: Using 'catch' is not allowed. [IllegalToken]`. Both suppressions silenced their line; `excludedPaths` and the `checkstyleMain` `exclude` removed the generated-code findings (11 Error Prone errors with generated code, 7 without).
- Proof. Android: AGP 9.4.1 (Kotlin 2.2.10 built in), detekt 1.23.8, Lint 32.4.1 in `$TMPDIR/017-L3/android`, run with `docker run --platform linux/amd64` and a copy of the host's Android SDK (platform 37.0). Lint with the ids at `error` in `lint.xml` and `warningsAsErrors = false`: `MainActivity.kt:18: Error: Missing PendingIntent mutability flag [UnspecifiedImmutableFlag]`, `MainActivity.kt:13: Error: This intent could be coming from an untrusted source. … [UnsafeIntentLaunch]`, `AndroidManifest.xml:13: Error: Exported content providers can provide access to potentially sensitive data [ExportedContentProvider]`, `:17: Error: Exported service does not require permission [ExportedService]`, `network_security_config.xml:3: Error: Insecure Base Configuration [InsecureBaseConfiguration]`, `:6: Error: The Network Security Configuration allows the use of user certificates in the release version of your app [AcceptsUserCertificates]`, `MainActivity.kt:22: Error: Provide a timeout when requesting a wakelock with PowerManager.Wakelock.acquire(long timeout). … [WakelockTimeout]`, `Adapter.kt:13: Error: It will always be more efficient to use more specific change events if you can. … [NotifyDataSetChanged]`, `screen.xml:9: Error: Hardcoded string "Hello", should use @string resource [HardcodedText]`, `:13: Error: Avoid using "px" as units; use "dp" instead [PxUsage]`, `:15: Error: Missing contentDescription attribute on image [ContentDescription]`, `Screen.kt:11: Error: Modifier parameter should be the first optional parameter [ModifierParameter from androidx.compose.ui]`, `Screen.kt:18: Error: Calls to launch should happen inside a LaunchedEffect and not composition [CoroutineCreationDuringComposition from androidx.compose.runtime]`. The same flag-less `PendingIntent` in a generated source (`Gen.kt`) was not reported. detekt with `classpath` set: `Kotlin.kt:16:37: Calling !! on a nullable type … [UnsafeCallOnNullableType]`, `:20:9: This use of GlobalScope should be replaced by CoroutineScope or coroutineScope. [GlobalCoroutineUsage]`, `:47:53: Dispatcher IO is used without dependency injection. [InjectDispatcher]`, `:30:16: This use of Thread.sleep() inside a suspend function should be replaced by delay(). [SleepInsteadOfDelay]`, `:33:45: The runCatching has suspend call inside. … [SuspendFunSwallowedCancellation]`, `:43:44: Empty catch block detected. … [EmptyCatchBlock]`, `:23:27: The method kotlinx.coroutines.runBlocking has been forbidden: Blocks the calling thread [ForbiddenMethodCall]`, `:26:16: … java.lang.Thread.sleep …`, `:50:58: … androidx.compose.runtime.collectAsState …`, and `SampleTest.kt:7:16: … java.lang.Thread.sleep … [ForbiddenMethodCall]` in test code (a `!!` in the same test file was not flagged). `Analysis failed with 19 weighted issues.` with `maxIssues: 0`; without a `classpath` only `GlobalCoroutineUsage` and `EmptyCatchBlock` of these ran.
- Gate, all green: `python3 tools/skill-lint.py backend/java mobile/android | tail -1` prints `0 findings`; `python3 tools/token-audit.py --violations-only` exits 0; the proof above. Not committed: the queue commits. Nothing unverified. `ktlint` has no row and was not run.

### L4 — Lint tables for the Swift, Python and Rust stacks

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `mobile-ios`, `desktop-macos`, `be-python` and `be-rust` each carry the table in the
file §7 names, the setup pointer and audit check where §7 lists one, and the lint-gap step. Every row's
id fired once in a scratch project, or is listed as unverified.
**Depends on:** L1, for the shape as it landed.
**Budget:** ~140k. Drivers:
- `CLAUDE.md` 25k.
- This plan §7, D8–D10 and L1's `As built` 7k.
- The pattern file 2k.
- The four stacks' rule files ~40k.
- Two `project-setup` skills, the lint parts ~6k.
- Four `rules/SKILL.md` ~12k. Two checklists ~8k.
- SwiftLint, ruff and clippy documentation lookups ~15k.
- Writes ~14k. Scratch-project output ~12k.

**Gate: own tests** —
`python3 tools/skill-lint.py mobile/ios desktop/macos backend/python backend/rust | tail -1`,
`python3 tools/token-audit.py --violations-only`, and §7's scratch-project proof with `uvx ruff check`,
with clippy through a `rust` image, and with SwiftLint through an image if one runs. Do not run the
unfiltered `skill-lint`.

- These stacks already name lint rules. Move the existing lines into the table's form and add what is
  missing. Delete a prose line the table now states, so the rule is written once.
- `mobile-ios` and `desktop-macos` get the same Swift rows, each in its own file (D8).
- **Not in L4:** raising a toolchain pin or adding a linter a stack does not name.

**As built (2026-11-21):**
- Built, per stack. `mobile-ios` and `desktop-macos`: an `## Enforced by the build` section at the end of each `xcode-config.md` (9 rows: 5 SwiftLint, 2 `custom_rules`, 2 compiler settings; `**/.swiftlint.yml` added to `paths:`; header v1 → v2), the `.swiftlint.yml` and the tests-folder child config in a fenced block. `be-python`: the table in `python-project.md` (19 rows, header v1 → v2). `be-rust`: the table in `cargo.md` (18 rows, header v1 → v2), `Cargo.toml` and `clippy.toml` blocks. Setup pointers: `mobile/ios/skills/project-setup/SKILL.md` and `desktop/macos/skills/project-setup/SKILL.md` (the "Format and lint" paragraph now points at the table, and each exit gate says every row is configured); `mobile/ios/skills/project-setup/references/packages-and-config.md` lost its second `.swiftlint.yml` copy. Check rows: `B25` (mobile-ios, index `B1–B25`) and `B18` (desktop-macos, `B1–B18`), appended, nothing renumbered. Lint-gap step: step 8 `Report lint gaps` in the four `rules/SKILL.md`, a step-5 bullet naming each stack's lint config, and the report line `Not enforced by the build: none | <id: house rule>   (one line per row)`. No `code-review/SKILL.md` edit: no new rule file.
- Prose moved into the tables and deleted: `python-project.md` (the ruff `S`/`ANN`/`PTH`/`T20` line), `cargo.md` (the "lint table denies `unwrap_used`…" line; the "Lints live once" line stays, the table has a setting row for it), the SwiftLint sentence in both `project-setup` skills. Dropped with it, because no house rule asks for it: `unused_import` (an analyzer rule, which `swiftlint lint` never runs), `unused_declaration`, `closure_spacing` and `explicit_acl`.
- Dropped candidates, named so L5 does not re-add them. Swift: `accessibility_trait_for_button` (accepts `.onTapGesture` with a trait, the house rule bans it), `accessibility_label_for_image` (*minor*), `todo` (*minor*), `unhandled_throwing_task`. Python: `PLR1714` (rewrites `a == x or a == y` to `in (…)`, which the tests rule bans), `S105`–`S107` (match identifier names only, so "no secret in code" is not what they detect), `PT011`, `ASYNC251`, `F403`. Rust: `indexing_slicing` and `arithmetic_side_effects` (flag every index and sum, not the input-derived ones), `wildcard_enum_match_arm` (flags enums the crate does not own), `expect_used`, `as_conversions`. §7's candidates: `force_unwrapping`, `force_cast`, `force_try`, `G004`, `BLE001`, `unwrap_used` all kept and fired; none dropped.
- Docs checked 2026-11-21: `realm.github.io/SwiftLint/<id>.html` (each id 200, `force_unwrapping` and `implicitly_unwrapped_optional` default `warning`), `uvx ruff rule <id>` and `docs.astral.sh/ruff/rules/` (ruff 0.17.6), mypy 2.4.1 `config_file` and `command_line` pages, and the clippy 1.100.0 lint index (every id present; `unused_result_ok` added in 1.82, `allow_attributes` in 1.70, `let_underscore_lock` deny by default, `disallowed_*` style, the rest `restriction`/`pedantic`/`suspicious`).
- Surprises that changed the text. `BLE001` skips an `except Exception` that re-raises or calls `logger.exception`; `S110` flags only `except Exception: pass`. `TID251` bans a module's submodules too (`urllib.parse`) and attributes (`time.sleep`). `unused_result_ok` suggests `let _ = …`, which `let_underscore_must_use` forbids, so the pair leaves only handling the error. `treatAllWarnings(as:)` is unavailable below `swift-tools-version: 6.2`. `// swiftlint:disable all` trips `blanket_disable_command`, so generated Swift is excluded by path. Clippy lints an `include!`d `OUT_DIR` file with the crate's table (`#[expect(…, reason)]` on the including module silences it); a workspace member without `[lints] workspace = true` gets no rule and no warning. In edition 2024 `std::env::set_var` is `unsafe`, so `unsafe_code = "forbid"` already stops it.
- Proof, in `$TMPDIR/017-L4/{swift,swift-compiler,swiftpm,xcode,python,rust}`, never in the repo. SwiftLint 0.65.1 through `ghcr.io/realm/swiftlint:latest` (the first pull was denied by a stale `ghcr.io` credential; `docker logout ghcr.io` fixed it), `lint --strict`. The macOS stack has the same rows and the same tool, so it ran once:
  - `Packages/Core/Sources/Core/Violations.swift:7:21: error: Force Unwrapping Violation: Force unwrapping should be avoided (force_unwrapping)`; `:11:22: … Force Cast Violation … (force_cast)`; `:15:16: … Force Try Violation … (force_try)`; `:4:15: … Implicitly Unwrapped Optional Violation … (implicitly_unwrapped_optional)`; `:21:17: … No Empty Block Violation … (no_empty_block)`; `:26:9: error: no_print Violation: Use os.Logger. (no_print)`; `:31:9: error: no_gcd_main Violation: Use MainActor isolation. (no_gcd_main)`.
  - Child config: the same file copied under `Tests/` printed `force_cast` and the rest, and no `force_unwrapping` or `force_try`. `**/Generated` in `excluded` silenced `Generated/G.swift:3:28`; without it, `error: Force Unwrapping Violation`. An `@IBOutlet var label: UILabel!` was not flagged.
  - Compiler, `xcodebuild -scheme App -destination 'platform=macOS' SWIFT_VERSION=6 SWIFT_TREAT_WARNINGS_AS_ERRORS=YES build` (Xcode 27.0, Swift 6.4): `Sources/App/Generated.swift:2:16: error: static property 'cache' is not concurrency-safe because it is nonisolated global shared mutable state [#MutableGlobalVariable]` and `Sources/App/Counter.swift:3:13: error: initialization of immutable value 'unused' was never used`. With neither setting the same package prints those as `warning:` and `** BUILD SUCCEEDED **`. SwiftPM at tools 6.2 with `swiftLanguageModes: [.v6]` and `.treatAllWarnings(as: .error)`: `Sources/App/Generated/Strings.swift:2:16: error: static property 'cache' is not concurrency-safe …`.
  - ruff 0.17.6 (`uvx ruff check . --output-format concise`), file `src/worker/violations.py`: `19:26: ANN401 Dynamically typed expressions (typing.Any) are disallowed in `value``; `70:19: PGH003 Use specific rule codes when ignoring type issues`; `59:5: PTH123 `open()` should be replaced by `Path.open()``; `60:5: PTH118`; `24:40: B006 Do not use mutable data structures for argument defaults`; `48:12: PLW0603 Using the global statement to update `_state` is discouraged`; `35:5: E722 Do not use bare `except``; `39:12: BLE001 Do not catch blind exception: `Exception``; `39:5: S110 `try`-`except`-`pass` detected`; `59:5: SIM115 Use a context manager for opening files`; `53:5: S602`, `78:5: S604 Function call with `shell=True` parameter identified`, `54:5: S605`; `55:5: S307`; `56:5: S102 Use of `exec` detected`; `57:5: S301`; `58:5: S506 Probable use of unsafe `yaml.load``; `20:17: G004 Logging statement uses f-string`; `21:5: T201 `print` found`; `TID251`: `61:5 `time.sleep` is banned: Never sleep to synchronise.`, `62:5 `signal.alarm``, `63:5 `threading.Timer``, `11:8 `requests``, `5:8 `socket``, `13:1 `urllib``, and `httpx` in a second file. `tests/test_violations.py` (an `assert`, no annotations) printed nothing.
  - mypy 2.4.1: with the table, `src/worker/mypyviolations.py:1: error: Function is missing a type annotation  [no-untyped-def]` and `:10: error: Statement is unreachable  [unreachable]`; with no `[tool.mypy]`, `Success: no issues found`; with `strict = true` only, the first error alone. A `case _` after an exhaustive `match`: `matchcase.py:24: error: Statement is unreachable  [unreachable]`.
  - clippy 0.1.100 (rustc 1.100.0) in `rust:latest` plus `rustup component add clippy`, `cargo clippy --workspace --all-targets --keep-going`, edition 2024: `app/src/lib.rs:15: clippy::unwrap_used: used `unwrap()` on an `Option` value`; `19 let_underscore_must_use`; `23 unused_result_ok: ignoring a result with `.ok()` is misleading`; `27 let_underscore_lock: non-binding let on a synchronization lock`; `31 map_err_ignore`; `35 exit: usage of `process::exit``; `39 cast_possible_truncation: casting `u64` to `u8` may truncate the value`; `43 string_slice`; `49 await_holding_lock: this `MutexGuard` is held across an await point`; `55 print_stdout`, `56 print_stderr`; `60 undocumented_unsafe_blocks: unsafe block missing a safety comment` and `60 unsafe_code: usage of an `unsafe` block`; `63 allow_attributes: #[allow] attribute found`, `66 allow_attributes_without_reason`; `70 disallowed_methods … `std::thread::sleep``, `71 … `std::env::var``, `72 … `std::env::var_os``; `8 disallowed_macros … `lazy_static::lazy_static``; `disallowed_types` for `once_cell::sync::Lazy`, `sync::OnceCell`, `unsync::Lazy`, `unsync::OnceCell`; `legacy/src/lib.rs:2 disallowed_methods … `std::env::set_var`` (edition 2021 crate). A `#[cfg(test)]` `Some(1).unwrap()` printed no `unwrap_used`; member `plain`, with no `[lints] workspace = true`, printed nothing; `target/…/out/generated.rs:1: clippy::unwrap_used` fired in the `include!`d file until `#[expect(clippy::unwrap_used, reason = …)]` went on the module.
- Gate, all green: `python3 tools/skill-lint.py mobile/ios desktop/macos backend/python backend/rust | tail -1` prints `0 findings`; `python3 tools/token-audit.py --violations-only` exits 0; the proof above.
- Nothing is unverified. Two limits: the `SWIFT_VERSION` and `SWIFT_TREAT_WARNINGS_AS_ERRORS` rows ran as `xcodebuild` build-setting overrides on a SwiftPM package, not as keys in an `.xcconfig` of a real `.xcodeproj`; SwiftLint ran in a Linux image, so it checked syntax only, without importing UIKit or AppKit. The `swift-format` block in `packages-and-config.md` still carries `NeverForceUnwrap` and `NeverUseForceTry`, which duplicate `force_unwrapping` and `force_try`; left as the stack named them. Not committed: the queue commits. One divergence from §7: D15 and D16. The Rust header cites 1.100 as the toolchain the proof ran on; no pin was raised (the version policy in `CLAUDE.md` still reads 1.99, which is not L4's to change).

### L5 — Lint tables for the three QA stacks

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `qa-dotnet`, `qa-java` and `qa-typescript` each carry the table for test-code rules in
the file §7 names, the audit check in `qa/dotnet/skills/standards-audit`, and the lint-gap step. Every
row's id fired once in a scratch project, or is listed as unverified.
**Depends on:** L1, for the shape as it landed.
**Budget:** ~160k. Drivers:
- `CLAUDE.md` 25k.
- This plan §7, D8–D10 and L1's `As built` 7k.
- The pattern file 2k.
- The three stacks' suite-wide rule files (`automation.md`, `suite-config.md`, `qa-java.md`,
  `qa-java-suite.md`, `qa-typescript.md`, `ui-tests.md`) ~40k.
- Three `rules/SKILL.md` ~12k. One checklist ~5k.
- NUnit.Analyzers, `eslint-plugin-playwright`, Error Prone and Checkstyle lookups ~25k.
- Writes ~16k. Scratch-project output ~25k.

**Gate: own tests** — `python3 tools/skill-lint.py qa/dotnet qa/java qa/typescript | tail -1`,
`python3 tools/token-audit.py --violations-only`, `python3 tools/qa-version-check.py`, and §7's
scratch-project proof with `dotnet build`, `npx eslint` and the Gradle image. Do not run the unfiltered
`skill-lint`.

- The rows come from `CLAUDE.md` "Test code rules": no sleep, no `waitForTimeout`, no branch, loop or
  `try` in a test body, no focused or skipped test without a reason, no empty `catch`.
- A scratch .NET project that references Allure.NUnit builds with `-p:AspectInjector_Enabled=false`.
- Playwright rule ids are for the versions `tools/qa-version-check.py` pins.
- **Not in L5:** the per-lane rule files (API, BDD, mobile, desktop). Only the suite-wide ones are mined.

**As built (2026-11-21):**
- Built. `qa-dotnet`: an `## Enforced by the build` section at the end of `qa/dotnet/skills/rules/suite-config.md` (11 rows, `**/.editorconfig` added to `paths:`, header v1 → v2) with the `BannedSymbols.txt` block, check row `A11` appended after `A10` in `qa/dotnet/skills/standards-audit/references/conformance-checklist.md` (the index row for section A carries no row range, so nothing to update), and step 8 `Report lint gaps` plus a step-5 sentence for the analyzer config and the report line in `qa/dotnet/skills/rules/SKILL.md`. `qa-java`: the section at the end of `qa/java/skills/rules/qa-java-suite.md` (7 Checkstyle rows, `**/config/checkstyle/*.xml` added to `paths:`, header v1 → v2) with the `checkstyle.xml` block, step 8 and a step-5 bullet in `qa/java/skills/rules/SKILL.md`. `qa-typescript`: new `qa/typescript/skills/rules/qa-typescript-lint.md` (18 rows, `paths:` on `eslint.config.*` and `tsconfig*.json`, header v1) with the `eslint.config.mjs` block, step 8 and a step-5 bullet in `qa/typescript/skills/rules/SKILL.md`. None of the three stacks has a `code-review/SKILL.md`, so no list of rule files changed.
- Rows, with the ids checked on 2026-11-21 against the NUnit.Analyzers index, the vs-threading and roslyn-analyzers help, the `eslint-plugin-playwright` README and rule pages (every id in the table is in 2.12.2, which asks only for ESLint 8.40), the Checkstyle 14.4 check pages and the Error Prone 2.53 bug-pattern pages. §7's candidates for these stacks: `RS0030` for `Thread.Sleep`, `playwright/no-wait-for-timeout` and `playwright/no-conditional-in-test` all fired and stayed; none was dropped. Added from the suite-wide files: .NET `RS0030` (`Task.Delay` and `WaitForTimeoutAsync` per overload, `ClassicAssert`/`StringAssert`/`CollectionAssert`/`FileAssert`/`DirectoryAssert`, FluentAssertions, `OrderAttribute`, `RetryAttribute`, `N:Newtonsoft.Json`), `VSTHRD002`, `VSTHRD100`, `VSTHRD110`, `CS4014`, `NUnit1012`, `CA1031`, `<Nullable>`; TypeScript the rest of the table; Java `IllegalToken`, `EmptyCatchBlock`, `IllegalCatch` and three `RegexpSinglelineJava` ids.
- Dropped for failing D9, named so nobody re-adds them. .NET: no analyzer detects a branch, loop or `try` in a test body, an empty `catch` of a named type, a skipped test without a reason or a focused test (NUnit has no focus), so `qa-dotnet` has none of those four rows. `CA2200` fired but no qa-dotnet prose names `throw ex`; `NUnit2059` sees only an un-awaited `Assert.ThrowsAsync`; `CA2211` stays dropped (L1); `[Ignore]`/`[Explicit]` reasons are *minor* prose. TypeScript: `no-nth-methods` and `no-raw-locators` flag more than the locator rule bans; `no-console` is *minor*. Java: Error Prone gets no row (D19), `System.out` and `printStackTrace()` are *minor* in `qa-java.md`, `enabled = false` without a ticket cannot be read from the annotation, and a static `WebDriver` is only half-detected by any regex.
- Surprises that changed the text. `CS4014` (compiler) fires in an async method and `VSTHRD110` in a sync one, so the row names both. A `RS0030` line whose package the project does not reference (Playwright, FluentAssertions, Newtonsoft.Json) is ignored without a warning. `Allure.NUnit` 2.15.0 depends on `Newtonsoft.Json` 13.0.4, so a project that pins 13.0.3 fails with `NU1605`. `no-conditional-in-test` flags `if`, `switch` and the ternary but not `||` or `&&` inside `expect(…)`, so "one expected value" stays prose. `prefer-web-first-assertions` skips `expect(page.url())`, so that row carries a `no-restricted-syntax` selector too. Dropping the plugin's `recommended` preset also drops the plugin registration: the spec block needs `plugins: { playwright }`. `SuppressionXpathSingleFilter` is a child of `TreeWalker`, not `Checker`, and `IllegalToken` has no `message` property. Error Prone `EmptyCatch` passes a block holding only a comment; `EmptyCatchBlock` with `commentFormat` `^$` flags it. Error Prone `CatchFail` did not fire on TestNG's `Assert.fail`.
- Generated code (D14). .NET: an `<auto-generated>` file under the project folder got `RS0030` at the `.editorconfig` severity and nothing from `VSTHRD002` or `CA1031`; Reqnroll writes `A.feature.cs` beside the feature with that header, and a Reqnroll.NUnit 3.3.4 project built with 0 warnings and 0 errors under the severities. TypeScript: ESLint lints generated code unless `ignores` names it. Java: Checkstyle lints a generated `srcDir`, and `exclude("gen/**")` on `checkstyleTest` silences it. All three are in the tables.
- Proof, in `$TMPDIR/017-L5/{dotnet,reqn,plain,ts,java}`, never in the repo.
  - .NET, `dotnet build -p:AspectInjector_Enabled=false` (SDK 10.0.301, BannedApiAnalyzers 5.6.0, Threading.Analyzers 18.12.1, NUnit.Analyzers 4.15.0, NUnit 4.6.1, Microsoft.Playwright.NUnit 1.63.0, Allure.NUnit 2.15.0), every id at `error` in `.editorconfig`:
    - `ViolationTests.cs(14,9): error RS0030: The symbol 'Thread.Sleep(int)' is banned in this project: Wait on a condition`; the same message for `Thread.Sleep(TimeSpan)` (15), `Task.Delay(int)` (16), `Task.Delay(int, CancellationToken)` (17), `Task.Delay(TimeSpan)` (18), `Task.Delay(TimeSpan, CancellationToken)` (19), `Task.Delay(TimeSpan, TimeProvider)` (20), `Task.Delay(TimeSpan, TimeProvider, CancellationToken)` (21), `IPage.WaitForTimeoutAsync(float)` (26), `IFrame.WaitForTimeoutAsync(float)` (27).
    - `(33,9): error RS0030: The symbol 'ClassicAssert' is banned in this project: Use Assert.That with a constraint`; `StringAssert` (34,9), `CollectionAssert` (35,9), `FileAssert` (36,9), `DirectoryAssert` (37,9), `AssertionExtensions` (38,9); `(41,12): … 'NUnit.Framework.OrderAttribute' … A test runs alone and in any order`; `(44,12): … 'NUnit.Framework.RetryAttribute'`; `(48,55): … The symbol 'Newtonsoft.Json' is banned in this project: Use System.Text.Json`.
    - `(50,6): error NUnit1012: The async test method must have a non-void return type`; `(51,23): error VSTHRD100: Avoid "async void" methods`; `(56,28)` and `(57,36): error VSTHRD002: Synchronously waiting on tasks or awaiters may cause deadlocks`; `(64,9): error CS4014: Because this call is not awaited`; `(99,9): error VSTHRD110: Observe the awaitable result of this method call`; `(74,9): error CA1031: Modify 'Should_Swallow' to catch a more specific allowed exception type` (and `(76,9)` for the bare `catch`); `(90,20): warning CS8600: Converting null literal or possible null value to non-nullable type` for `<Nullable>`.
    - `suite/obj/Gen/Generated.cs(7,34): error RS0030: The symbol 'Thread.Sleep(int)' is banned`, and nothing for `VSTHRD002` or `CA1031` in the same file. `plain/T.cs(7,34): error RS0030` was the only line from a project with NUnit alone, and `[SuppressMessage("ApiDesign", "RS0030:Do not use banned APIs", Justification = …)]` on a `[Retry(2)]` test printed nothing.
  - TypeScript, `npx eslint tests -f json` (ESLint 9.39.5, typescript-eslint 8.73.0, eslint-plugin-playwright 2.12.2, TypeScript 6.0.3, `@playwright/test` 1.64.0, eslint-comments 4.8.1, Node 22.12), the table's config, every id appeared:
    - `violations.spec.ts:8:9 playwright/no-wait-for-timeout — Unexpected use of page.waitForTimeout()`; `9:28 no-restricted-globals — Unexpected use of 'setTimeout'`; `11:9 no-restricted-properties — 'browser.pause' is restricted`; `2:1 no-restricted-imports — 'node:timers/promises' import is restricted`.
    - `16:3`, `19:13`, `20:3 playwright/no-conditional-in-test — Avoid having conditionals in tests`; `34:5 playwright/no-conditional-expect — Avoid calling `expect` conditionally`; `25:3`, `28:3`, `31:3`, `40:3 no-restricted-syntax — A test body is linear: no loop or try`; `39:31 no-restricted-syntax — A caught error is handled or reaches the runner, never swallowed`; `42:11 no-empty — Empty block statement`; `84:13 no-restricted-syntax — No as unknown as X`; `webfirst.spec.ts:7:10 no-restricted-syntax — Assert the URL with await expect(page).toHaveURL()`.
    - `46:6 playwright/no-focused-test`; `50:6 … no-skipped-test — Unexpected use of the `.skip()` annotation` and `54:6` for `.fixme()`; `59:3 playwright/require-annotation-reason — The `.skip()` annotation should say why`; `63:1 playwright/expect-expect — Test has no assertions`; `69:38 playwright/no-networkidle`; `70:27 playwright/no-force-option`; `71:9 playwright/no-wait-for-navigation`; `72:3` and `webfirst.spec.ts:5:3 playwright/prefer-web-first-assertions — Replace textContent() with toHaveText()`; `webfirst.spec.ts:8:27 playwright/prefer-to-have-count — Use toHaveCount() instead`; `await.spec.ts:4:3 playwright/missing-playwright-await — 'toHaveURL' must be awaited or returned`.
    - `floating.ts:3:3 @typescript-eslint/no-floating-promises — Promises must be awaited`; `77:12 @typescript-eslint/no-explicit-any — Unexpected any`; `78:3` and `80:3 @typescript-eslint/ban-ts-comment`; `82:0 @eslint-community/eslint-comments/require-description — Unexpected undescribed directive comment`; `npx tsc -p tsconfig.json`: `tests/strict.ts(1,14): error TS2322: Type 'null' is not assignable to type 'string'`.
    - `src/generated/api.ts:1:17 @typescript-eslint/no-explicit-any` under `--no-ignore`; with the config's `ignores`, `npx eslint src` says every file matching `src` is ignored. A bare `test.skip()` printed `no-skipped-test` and `require-annotation-reason`; `test.skip(browserName === 'firefox', 'WET-204 layout breaks')` printed nothing; `expect(flag || x)` and `expect(flag && page)` printed nothing.
  - Java, `docker run … gradle:9.6.0-jdk21 gradle checkstyleTest -x compileTestJava` (Gradle 9.6.0, JDK 21, Checkstyle 14.4.0, `net.ltgt.errorprone` 5.2.0 with Error Prone 2.53.0, TestNG 7.12.0, Playwright 1.63.0), the `checkstyle.xml` copied out of the rule file: `ViolationTests.java:20: Wait on a condition, never sleep [NoSleep]` (`Thread.sleep`; 21 `TimeUnit.SECONDS.sleep`, 22 `waitForTimeout`); `:27:9: Using 'if' is not allowed. [TestBodyLinear]` (`else` 29:11, `?` 32:23, `switch` 33:9, `for` 39:9 and 42:9, `while` 45:9, `do` 48:9); `:55:9: Using 'try' is not allowed. [TestHasNoTry]` (and `:94:9` inside a `@BeforeMethod`); `:66:70: Empty catch block. [EmptyCatchBlock]` (and `:96:43`, a block holding only a comment); `:70:11: Catching 'Exception' is not allowed. [IllegalCatch]` (`Throwable` at 75:11); `:89: A test runs alone and in any order [NoDependsOnMethods]`; `:12: A TestNG configuration method is alwaysRun = true [ConfigAlwaysRun]`.
    - Not flagged, as the table says: a `DriverFactory` with `if` and `try` outside any `@Test`; an `if` inside a `@BeforeMethod`; a `catch (Exception)` under `@SuppressWarnings("checkstyle:IllegalCatch")`; a statically imported `sleep(3)`. A false positive: `@BeforeMethod(` with `alwaysRun = true)` on the next line (`ViolationTests.java:106`).
    - Error Prone, `error("EmptyCatch")`: `ViolationTests.java:66: error: [EmptyCatch] Caught exceptions should not be ignored`, nothing at 96, nothing for `CatchFail`. Generated: `generated-src/gen/Gen.java:5: Wait on a condition, never sleep [NoSleep]`, and 0 lines from `generated-src` after `exclude("gen/**")`; Error Prone reported `Gen.java:8: error: [EmptyCatch]` until `excludedPaths` named the folder.
- Gate, all green: `python3 tools/skill-lint.py qa/dotnet qa/java qa/typescript | tail -1` prints `0 findings`; `python3 tools/token-audit.py --violations-only` exits 0; `python3 tools/qa-version-check.py` prints `OK`; the proof above.
- Nothing is unverified. Limits: the `@Test` suppression keys on the annotation's simple name; Maven wiring of Checkstyle was not run; Playwright .NET proof is against 1.63.0 only and ESLint proof against ESLint 9 only; `.features-gen/**` is in `ignores` by the library's own description of `bddgen` (`qa/typescript/skills/bdd-project-scaffold/SKILL.md:35`), not by a run of it. Not committed: the queue commits. Divergences from §7 and the L5 prompt are D19.

### C1 — The catalog and the README

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** `docs/skills-catalog.md` lists 10 `engineering` skills, the ARCHITECTURE lane and
`untested-code`, and says each stack's rules name their lint enforcement. `README.md` says the same where
it describes `engineering` and the rules skills.
**Depends on:** A1, U1, R1, L1, L2, L3, L4, L5. It describes what they landed.
**Budget:** ~80k. Drivers:
- `CLAUDE.md` 25k.
- This plan §1–§2 and the `As built` notes ~12k.
- The catalog lines named below ~15k. `README.md` lines 15–125 ~8k.
- Writes ~10k. Lint output ~5k.

**Gate: own tests** — `python3 tools/skill-lint.py | tail -1` (C1 runs after every writer, so the whole
tree is settled), `python3 tools/token-audit.py --violations-only`,
`git grep -n "8 skills (\`engineering" -- docs/skills-catalog.md` prints nothing.

- `docs/skills-catalog.md`: the plugin table row for `engineering` (line 13), the command table row
  (line 46), the engineering section, and one sentence in each stack section's rules line. Read only
  those; the whole file is about 55k tokens.
- `README.md`: the `engineering` line (19–23), the rules table (from line 75), and the audit bullets
  (from line 110).
- Describe what landed, from the files and the `As built` notes, never from this plan's intent. A row an
  L task left unverified is not described as enforced.
- **Not in C1:** `CLAUDE.md` (R1 made its one edit), `CONTRIBUTING.md` (nothing in it changes).

### G1 — The whole set, the blind fixture run, and filing the plan

**Stack:** `docs` · **Agent:** `general-purpose`
**Deliverable:** Every command in §8 passes on the merged tree, the blind run's report is saved in the
fixture and compared with `EXPECTED.md`, and the plan is filed.
**Depends on:** C1, FX1.
**Budget:** ~120k. Drivers:
- `CLAUDE.md` 25k.
- This plan §8, D5 and the `As built` notes 12k.
- `code-auditor`, the engine, the report template, the architecture skill and its checklist ~25k.
- The fixture, read as an audit reads it ~15k.
- The report ~12k. Tool output ~15k. Fixes and the merge ~15k.

**Gate (this is the last runnable task, so it runs the whole set once more across the plan, in order):**
the ten items of §8.

- Run items 1–9 of §8 once. Fix each failure at the narrowest file, rerun only what failed, then run
  items 1–9 once more.
- **Then the blind run, item 10.** Do not open §4 of this plan or `EXPECTED.md` first. Follow
  `engineering/commands/audit.md` by path, with `tools/fixtures/architecture-audit/course-platform/` as
  the project root and the task "architecture audit of the whole project". Save the report where the
  lane says, inside the fixture.
- Open `EXPECTED.md` and compare. On a miss or a reported decoy, follow §4 "On a miss".
- Delete `course-platform/docs/agent-context/` after the run. Commit the report.
- Merge `master` into the plan's branch (close-out step 6).
- **Status, when filing.** Name as unverified: no session has loaded the two new skills by description;
  the lane has run once, on a fixture; every lint row an L task listed as unverified; no `rules` skill
  has reported lint gaps in a real project.
- **Not in G1:** new checks or new lint rows. A finding outside §8 goes into `Status:` as a follow-up.

## Close-out — every task

Before you stop, in this order, in this file. Another task may be running in this working tree:
re-read this file immediately before these edits, and touch only your own task block, your own prompt
block and the line that says which have landed.

1. **As built** — append a dated `**As built (YYYY-MM-DD):**` bullet to your task block: what differed
   from the plan, the ids and names you assigned, what is built but unverified, and the `file:line` or
   command output that proves the deliverable exists. Never edit an earlier note.
2. **Decisions** — where you built something differently from the plan, append a dated `D<n>` to
   `## Decisions` with both readings. A divergence is recorded, never absorbed.
3. **The blocks below yours** — rewrite, in place, every prompt block whose assumptions your work
   changed (a renamed file, a changed signature, a moved gate), and write any block left
   `Blocked on <your id>` from what you now know.
4. **Status** — rewrite the header `**Status:**` line: what is built, what is next, what is built but
   unverified. When a task is running beside you, leave it: the next task that waits for you rewrites it.
5. **Commit the work** — the code, its tests and these plan edits together, on the current branch (under
   Plan Queue, the plan's branch in its worktree; never check out the default branch), adding only your
   own files, by path — never `git add -A`. Your prompt block is still in the plan.
6. **Merge, gate task only** — if you are the task that ran the whole set and this plan runs on its own
   branch, merge the default branch into it now, resolve every conflict by keeping both sides' rows,
   re-run the failing suites if code conflicted, and commit the merge, so the plan merges back cleanly
   and the documentation task after you documents the merged code.
7. **Your own block** — only now delete it, and update the line above the blocks that says which have
   landed, in a follow-up commit of its own: `docs: delete <id>'s prompt (<plan>)`. Do not stop between
   the two commits. Stopping mid-task: keep it, with a `Picking up from:` line. Blocked: keep it, naming
   the blocker and its owner. When the queue says other tasks of this plan are running beside you, do
   not commit, stash, reset or check out at all: make this deletion your last edit, and the queue
   commits the work and the deletion together.
8. **Filing** — if your deletion left no blocks, rewrite `**Status:**` one final time (what the plan
   delivered, what is still unverified), `git mv` this plan into `docs/plans/implemented/`, same name and
   number — a `solution-planner` pack moves its whole initiative folder — and add its row to that
   folder's README where there is one, in the same follow-up commit.

## Prompts — one per task

One session each. Each block is complete on its own. Every gate runs locally, in the session that runs
the task.

- A1, FX1, R1 and L1 can start at once and run beside each other: their files are disjoint.
- U1 waits for A1. L2, L3, L4 and L5 wait for L1 and run beside each other and beside U1.
- C1 waits for every writer. G1 waits for C1 and FX1 and runs the whole set.
- No prompt pushes, and no prompt commits a scratch project.

| # | Stack | Agent | Depends on | Runs beside | Budget |
|---|---|---|---|---|---|
| A1 | `docs` | `general-purpose` | none | FX1, R1, L1 | ~130k |
| FX1 | `docs` | `general-purpose` | none | every task but G1 | ~60k |
| R1 | `docs` | `general-purpose` | none | every task but C1, G1 | ~85k |
| U1 | `docs` | `general-purpose` | A1 | FX1, R1, L1–L5 | ~80k |
| L1 | `docs` | `general-purpose` | none | A1, FX1, R1, U1 | ~150k |
| L2 | `docs` | `general-purpose` | L1 | FX1, R1, U1, L3, L4, L5 | ~150k |
| L3 | `docs` | `general-purpose` | L1 | FX1, R1, U1, L2, L4, L5 | ~130k |
| L4 | `docs` | `general-purpose` | L1 | FX1, R1, U1, L2, L3, L5 | ~140k |
| L5 | `docs` | `general-purpose` | L1 | FX1, R1, U1, L2, L3, L4 | ~160k |
| C1 | `docs` | `general-purpose` | A1, U1, R1, L1, L2, L3, L4, L5 | FX1 | ~80k |
| G1 | `docs` | `general-purpose` | C1, FX1 | — | ~120k |
| — | restart, run `/engineering:audit` and one `<plugin>:rules` on a real project | **the user** | G1 | — | — |

A1, FX1, R1, U1, L1, L2, L3, L4 and L5 have landed; their prompts are deleted. The blocks below are the live ones.

---

### C1 — The catalog and the README (general-purpose, docs)

````
Depends on: A1, U1, R1, L1, L2, L3, L4, L5
Agent: general-purpose · Stack: docs

Task C1 of docs/plans/017-architecture-audit-untested-code-and-lint-enforcement.md. The goal:
docs/skills-catalog.md and README.md describe what the eight tasks above landed: ten `engineering`
skills, the ARCHITECTURE lane of `code-auditor`, `untested-code`, and each stack's lint table.

Read, in this order:
1. The plan: §1, §2, every task's As built note, task C1, and "Close-out — every task".
2. What landed: engineering/architecture-audit/SKILL.md, engineering/untested-code/SKILL.md, and one
   lint table (backend/dotnet/skills/rules/dotnet-lint.md).
3. docs/skills-catalog.md: line 13 (the `engineering` plugin row), line 46 (the command row), the
   engineering section, and the rules line of each stack section. Find them with `git grep -n`; read only
   those.
4. README.md lines 15–125.

Do:
- The catalog: `engineering` has 10 skills, named. The audit lanes are three for `code-auditor`. Each
  stack section says in one sentence that its rules name their lint enforcement and where.
- README.md: the `engineering` line, the rules table from line 75, the audit bullets from line 110.

Traps:
- Describe what landed, from the files and the As built notes. A lint row a task listed as unverified is
  not described as enforced.
- The catalog is about 55k tokens. Read only the lines named.
- CLAUDE.md and CONTRIBUTING.md are not yours to edit here.

Gate: own tests.
  python3 tools/skill-lint.py | tail -1    (0 findings; every writer has landed, so the whole tree is settled)
  python3 tools/token-audit.py --violations-only    (exit 0)
  git grep -n "8 skills (\`engineering" -- docs/skills-catalog.md    (prints nothing)

Commit: `docs: 017 C1 — catalog and README for the architecture lane, untested-code and lint tables`.
Close out per the plan's "Close-out — every task" before you stop.
````

### G1 — The whole set, the blind fixture run, and filing the plan (general-purpose, docs)

````
Depends on: C1, FX1
Agent: general-purpose · Stack: docs

Task G1 of docs/plans/017-architecture-audit-untested-code-and-lint-enforcement.md. The goal: every
command in the plan's §8 passes on the merged tree, the architecture lane is run blind on the fixture and
compared with its answer key, and the plan is filed.

Do NOT open the plan's §4 or tools/fixtures/architecture-audit/EXPECTED.md until your audit report is
saved. The run is only evidence if it is blind.

Read, in this order:
1. CLAUDE.md: "Planning".
2. The plan: §8, D5, every task's As built note, task G1, and "Close-out — every task". Skip §4.
3. For the blind run only: engineering/commands/audit.md, then what it tells you to read.

Do:
- Run items 1–9 of §8 once. Fix each failure at the narrowest file, rerun only what failed, then run
  items 1–9 once more.
- The blind run: follow engineering/commands/audit.md by path, with
  tools/fixtures/architecture-audit/course-platform/ as the project root and the task "architecture audit
  of the whole project". Save the report where the lane says, inside the fixture.
- Now read §4 and EXPECTED.md, and compare. P1–P5 must each be reported under the expected id with a
  `file:line` in the named file. N1–N3 must not be findings.
- On a miss or a reported decoy: fix the checklist, never the fixture and never EXPECTED.md. Delete the
  failed report, record in As built what was missed and what changed, and run again.
- Delete course-platform/docs/agent-context/ after the run. Commit the report.
- Merge `master` into the plan's branch (close-out step 6).

Traps:
- A second run is not blind. Say so in Status.
- The audit is read-only on the fixture's code. Its only writes are the report and the cache you delete.
- Delete `.pytest_cache` after item 4.
- A failure may belong to any earlier task. It is yours to fix, and As built names the task.
- New checks and new lint rows are not yours. A finding outside §8 goes into Status as a follow-up.

Gate (this is the last task, so it runs the whole set once more across the plan, in order): the ten
items of §8.

Status, when filing, names as unverified: no session has loaded the two new skills by description; the
lane has run once, on a fixture; every lint row an L task listed as unverified; no `rules` skill has
reported lint gaps in a real project.

Commit: `docs: 017 G1 — whole set green, blind fixture run`.
Close out per the plan's "Close-out — every task" before you stop.
````
