# architecture Conformance Audit — course-platform — Round 1

**Date:** 2026-11-21 · **Branch:** plan-queue/017-architecture-audit-untested-code-and-6a9edb · **Commit:** 52802fc3
**Auditor:** `code-auditor` (read-only — no product code was changed) · **Lane skill:** `engineering/architecture-audit` (`engineering:audit-architecture`), run on `standards-audit-engine`

Mode: A — BASELINE · ARCHITECTURE lane — whole project (task: "architecture audit of the whole project")
Rules: plugin copy (not installed) — `/engineering:rules` installs `audits.md` into the project.
Orientation: full (no cache existed) — `docs/agent-context/code-auditor.md` written.

## 1. Detected lane

| Item | Value |
|---|---|
| Language | TypeScript only: 25 files in `src/`, 7 in `tests/` (`git ls-files \| sed -E 's/.*\.//' \| sort \| uniq -c`) |
| Compiler | `strict: true`, `noUncheckedIndexedAccess`, `moduleResolution: Bundler`, target ES2023 (`tsconfig.json:3-8`); ESM (`package.json:4`) |
| Hides things by | an unexported name in a file; a module's surface is its `index.ts` barrel (`src/<area>/index.ts`, six of them) |
| Build layout | `package.json` has no scripts and no dependencies (`package.json:1-5`); no build or test command is declared |
| Test runner | Vitest, from the imports (`tests/progress/progress.test.ts:1`) `#inferred` |
| Glossary | `docs/business-model/glossary.md`, 5 terms |

Every finding below is judged **against this lane**. A TypeScript file without an index has no surface of its own; `export` in a file counts only when the module's `index.ts` re-exports it.

Recipes: this machine's regex has no `\b`, so the word-boundary recipes ran with `-w` or `([^A-Za-z]|$)`; every empty result below was re-run in that form before it was trusted.

## 2. Scope & coverage

- **In scope:** the whole project root: `src/` (6 modules), `tests/` (5 areas), `docs/business-model/`.
- **Excluded:** nothing. There is no build output, no vendored code and no generated code in the tree.
- **Files in scope:** 35 · **files read:** 35 (every source and test file read in full).
- **Evidence mode:** static. Nothing was built or run.

## 3. Applicability matrix

| Section | Status | Decided by |
|---|---|---|
| A — Module map and dependencies | Applicable | always |
| B — Module depth | Applicable | always |
| C — Duplicated logic | Applicable | always |
| D — Tests and the entry surface | Applicable | `git ls-files -- '*test*' '*Test*' '*spec*' '*Spec*'` → 5 test files and 2 in-memory repositories under `tests/` |
| E — Code against the glossary | Applicable | `ls docs/business-model/glossary.md` → present |

### Module map

| Module | Surface | Public members | Body lines | Imports |
|---|---|---|---|---|
| `src/catalog` | `index.ts` | 5 exports (`CatalogService`, `CatalogSource`, `CatalogEntry`, `CatalogRow`, `catalogCache`) | 55 | none |
| `src/courses` | `index.ts` | 7 exports | 155 | `pricing` |
| `src/enrollment` | `index.ts` | 5 exports | 97 | `catalog`, `payments` |
| `src/payments` | `index.ts` | 2 exports | 29 | none (`@acme/payments-sdk`, external) |
| `src/pricing` | `index.ts` | 1 function, `quote` (`pricing/index.ts:6`) | 41 | none |
| `src/progress` | `index.ts` | 2 exports + 1 type | 22 | none |

`src/pricing/internal/` holds four files behind the surface; nothing outside `pricing` imports them from `src/` (`git grep -n -E "from .\.\./[a-z]+/" -- src` is empty). There are no groupings: every top-level area is a module.

## 4. Conformance summary

| Section | Applicable checks | Conforming | Violated | Unverifiable |
|---|---|---|---|---|
| A — Module map and dependencies | 3 | 3 | 0 | 0 |
| B — Module depth | 4 | 2 | 2 | 0 |
| C — Duplicated logic | 3 | 1 | 2 | 0 |
| D — Tests and the entry surface | 3 | 1 | 2 | 0 |
| E — Code against the glossary | 3 | 2 | 1 | 0 |
| **Total** | **16** | **9** | **7** | **0** |

C2 is violated by the same two functions as C1 and is counted once as a finding (under C1), so 7 violated checks make 6 findings.

**Findings:** 0 blocker · 5 major · 1 minor · 0 nit
**By class:** Data 0 · Code 6 · Logical conflicts 0 (C1 carries an owner question, Q-2)
**Overall conformance:** 9/16 applicable checks (56%)

## 5. Findings by section

### A — Module map and dependencies

No findings.

- A1 conforms. No `utils`, `common`, `shared` or `helpers` area: `git ls-files ':(icase)*/utils/*' ':(icase)*/common/*' ':(icase)*/shared/*' ':(icase)*/helpers/*'` returns nothing.
- A2 conforms. Every import that crosses a module goes to the other module's index: `src/courses/submit-course.ts:1` (`'../pricing'`), `src/enrollment/enroll-learner.ts:1-2` (`'../catalog'`, `'../payments'`). Negative search: `git grep -n -E "from .\.\./[a-z]+/" -- src` is empty. The one deep import in the project is a test (see D1).
- A3 conforms. The edges are `courses → pricing`, `enrollment → catalog` and `enrollment → payments`; `git grep -h -o -E "from .\.\./[a-z]+" -- src/<module>` per module shows no edge back, so there is no pair and no longer cycle.

**Rollup — A:** The dependency graph is a clean fan-in on three leaf modules, and every cross-module import goes through a barrel. Nothing to act on here; the only boundary breach is in the tests (D1).

### B — Module depth

| ID | Sev | Check | Evidence | Fix direction (owner) |
|---|---|---|---|---|
| B2 | major | No forwarding layer | `src/enrollment/enrollment-service.ts:4-22` — `EnrollmentService` has four methods and all four return `this.repository.<same name>(<same arguments>)` (`:7-9`, `:11-13`, `:15-17`, `:19-21`); `create` only renames `save` `#confirmed`. It is the only file the forward-count recipe flags (`git grep -c -E "(return\|=>) +(await +)?(this\.\|_)[A-Za-z]+\.[A-Za-z]+\(" -- src ':!*[Tt]est*'` → `enrollment-service.ts:4`). `enrollLearner` takes it as its first argument (`src/enrollment/enroll-learner.ts:18`) and calls only those four methods | Delete the class; `enrollLearner` takes the `EnrollmentRepository` it already wraps (`enrollment-repository.ts:3-8`) — `CLAUDE.md` "Simplicity" (flat over layered), applied by the `be-node` agent |
| B3 | major | Internals stay inside | `src/catalog/index.ts:5` exports `catalogCache`, the module-level `new Map<string, CatalogRow>()` (`src/catalog/catalog-cache.ts:3`); `index.ts:4` exports `CatalogRow`, the persistence row (`course_id`, `price_cents`, `is_published`, `catalog-row.ts:2-5`) `#confirmed`. Every `CatalogService` instance reads and writes that one map (`catalog-service.ts:21`, `:23`, `:28`, `:33`) | Make the cache a private field of `CatalogService`, drop the `catalogCache` export, and keep `CatalogRow` inside the module by having `CatalogSource` yield `CatalogEntry` — `CLAUDE.md` "Code quality rules" (no static mutable state), applied by the `be-node` agent |

B3 failure scenario: any importer of `../catalog` can call `catalogCache.clear()` or `.set(...)` and change what `find` and `list` return without `refresh`; and two `CatalogService` instances built from different sources overwrite each other's data, because the map is shared (`catalog-service.ts:21`).

- B1 conforms. Public `export` lines against body lines (`git grep -c -E "^export " -- <module>` and `wc -l`) are 10/55, 17/155, 12/97, 5/29, 6/41 and 5/22 for `catalog`, `courses`, `enrollment`, `payments`, `pricing` and `progress`; most of them are type exports, and `pricing` exposes one function. `pricing` hides four rule files behind one function (`src/pricing/index.ts:6-10`). `enrollment` is the one module whose public class hides nothing; that is B2 and is counted there, once.
- B4 conforms. Each business decision lives in one module: the percent-off table in `src/pricing/internal/discount-rules.ts:1-4`, the VAT rate in `tax-rules.ts:1`, the price floor in `price-floor.ts:1`. Search: `git grep -n -i -e discount -e vat -e tax -e eligib -e expire -- src ':!*[Tt]est*'` hits `pricing` and the `discountCode` field that `courses` passes through (`submit-course.ts:14`, `:49`), nothing else. The repeated-literal search found one repeated message (see section 8).

**Rollup — B:** `pricing` is the model of the section: a one-function surface over real rules. The two violations are both a module that leaks its seam: `enrollment` exposes a class that only passes calls through, and `catalog` exposes its storage. Fix B3 first, since the shared map is state, not only shape.

### C — Duplicated logic

| ID | Sev | Check | Evidence | Fix direction (owner) |
|---|---|---|---|---|
| C1 | major (drifted; also C2) | No near-identical block in two modules; one business rule, one implementation | `src/courses/submit-course.ts:6-60` and `src/courses/duplicate-course.ts:6-57`: `diff` shows four differences in 57 lines — `MAX_TITLE_LENGTH` (`submit-course.ts:6`), the title-length check (`submit-course.ts:31-33`), `sourceCourseId` (`duplicate-course.ts:7`) and `duplicatedFrom` (`duplicate-course.ts:53`); the other 55 lines, including the six-rule validation chain (`submit-course.ts:28-45`, `duplicate-course.ts:27-41`) and the `quote` / `nextId` / `save` sequence, match `#confirmed` | Make `duplicateCourse` reuse the one validation and build path of `submitCourse` and add only `duplicatedFrom` — `CLAUDE.md` "Simplicity" (two callers exist today), applied by the `be-node` agent |

C1 failure scenario: `duplicateCourse` with a 200-character title is saved (`duplicate-course.ts:27-29` checks only that the title is non-empty), while `submitCourse` rejects the same title with `title must be at most 120 characters` (`submit-course.ts:31-33`), so a course can reach the catalog through duplication that the submit rule forbids. Whether the 120-character limit is meant to cover duplicates is an owner decision (Q-2). Both files arrive in one commit (`git log --oneline -3 -- <a> <b>`), so the drift is read from the code, not from history.

- C2 is violated by the same pair, reported under C1. The other business rules are single: the discount, floor, tax and rounding rules are each in one `pricing/internal` file and both course use cases call `quote` (`submit-course.ts:49`, `duplicate-course.ts:45`). Search: no threshold of two or more digits is written twice (`git grep -h -o -E "(>=\|<=\|>\|<) *[0-9]{2,}" -- src` is empty).
- C3 conforms. The six modules' file lists have six different checksums (`for m in …; do git ls-files src/$m | sed … | sort | cksum`).

**Rollup — C:** The project has exactly one duplicated block, but it is a whole use case, and it has already drifted on a validation rule. The pattern is a copy made to add one field. The next action is to collapse the two use cases, then settle Q-2.

### D — Tests and the entry surface

| ID | Sev | Check | Evidence | Fix direction (owner) |
|---|---|---|---|---|
| D1 | major | Tests enter through the entry surface | `tests/pricing/discount-rules.test.ts:2` imports `applyDiscount` and `percentOffFor` from `'../../src/pricing/internal/discount-rules'`, past the module's one export, `quote` (`src/pricing/index.ts:6`) `#confirmed`. Every other test imports a module index (`git grep -n -E "from .(\.\./)+src/[a-z]+/[A-Za-z_/-]+.;?$" -- tests` → this line only) | Rewrite the test to call `quote` from `'../../src/pricing'` — the stack's `unit-testing` skill, applied by the `be-node` agent |
| D3 | major | A module with rules has a test through its surface | `src/pricing` holds the discount, price floor, VAT and rounding rules (`pricing/internal/discount-rules.ts:6-15`, `price-floor.ts:3-8`, `tax-rules.ts:3-5`, `rounding.ts:1-3`); no test imports `'../../src/pricing'` (`git grep -l -E "from .\.\./\.\./src/pricing.;?$" -- tests` is empty); the one pricing test is the D1 file, and it covers `discount-rules.ts` alone (`discount-rules.test.ts:5-23`) `#confirmed`. `quote` is reached only through one case of `submitCourse`, `LAUNCH10` on a list price of 10000 (`tests/courses/submit-course.test.ts:33-37`) | Test `quote` through its surface for the floor, the zero price, VAT and rounding; this is the same rewrite as D1 — the stack's `unit-testing` skill, applied by the `be-node` agent |

D1 failure scenario: renaming or merging the functions in `internal/discount-rules.ts` breaks the only pricing test although `quote` returns the same prices. D3 failure scenario: changing `MINIMUM_PAID_PRICE_CENTS` from 99 to 0 (`price-floor.ts:1`) leaves every test green — the suite never prices anything under 99 cents.

- D2 conforms. No test asserts a call on a collaborator the project owns: `git grep -c -e toHaveBeenCalled -e '.Verify(' -e 'verify(' -e Received -e assert_called -- tests` is empty. The gateway stubs in `tests/enrollment/enroll-learner.test.ts:31-37` are objects returning a canned charge, and the tests assert the returned `status` and the saved list (`:61-64`, `:90`, `:98`).
- The `@ts-expect-error` / `@ts-ignore` / `as any).` probe over `tests/` is empty.

**Rollup — D:** Four of the five test areas go through their module's index and assert returned values. The exception is `pricing`, the module where money is calculated, and it is the only module whose rules are not tested through its surface. One rewrite of the pricing test closes both rows.

### E — Code against the glossary

| ID | Sev | Check | Evidence | Fix direction (owner) |
|---|---|---|---|---|
| E1 | minor (7 sites) | Code uses the glossary's term | `src/progress/student-progress.ts:1` declares `StudentProgress`, and the glossary lists `Student` under `Avoid` for Learner (`docs/business-model/glossary.md:6`); the same type holds `learnerId` (`student-progress.ts:2`) `#confirmed`. Also `student-progress.ts:8` and `:15`, `src/progress/index.ts:1-2` (the file name `student-progress`), `tests/progress/progress.test.ts:3` and `:5`. Search: `git grep -n -i -E "student\|coupon\|voucher\|instructor\|teacher\|signup\|registration" -- src tests` hits only these | Rename the type and the file to `LearnerProgress` — `product/skills/domain-modeling` glossary, applied by the `be-node` agent |

- E2 conforms. The `Called in code` names exist: `Course` (`src/courses/course.ts:3`), `Enrollment` (`src/enrollment/enrollment.ts:3`), `learnerId` (16 uses), `authorId` (5), `discountCode` (9).
- E3 conforms. No type name is declared in two modules with different members: the declarations starting `Course`, `Enrollment`, `Learner`, `Author` and `Discount` are one per concept (`git grep -n -E "^(export )?(class\|type\|interface) +(Course\|Learner\|Enrollment\|Author\|Discount)[A-Za-z]*" -- src`). `StudentProgress` and `learnerId` name one concept with two words, which is E1.

**Rollup — E:** The code follows the glossary everywhere except the `progress` module, which still uses the old word, `Student`. It is one rename, but each day it stays, the UI strings and routes built on `progress` will carry the avoided term.

## 6. Defect families

| Family | Head | Members | Sites | One fix closes |
|---|---|---|---|---|
| Copied use case | C1 | C2 | 2 files | One validation path for submit and duplicate: closes C1, C2 and the 120-character drift |
| Pricing tested past its surface | D1 | D3 | 1 test file + 4 untested rule files | A test of `quote` through `src/pricing` closes both |

B2, B3 and E1 are single-site findings with no family.

## 7. Priority — leverage-ordered

| # | Item | Sev | Why first | Effort |
|---|---|---|---|---|
| 1 | C1 (head; C2) | major | The only finding with a behaviour difference today: duplicates skip the title limit. One fix closes two checks | S |
| 2 | D1 (head; D3) | major | Money logic with a test that breaks on refactor and cannot see a floor bug. One rewrite closes two checks | S |
| 3 | B3 | major | Shared mutable state behind a public export; the fix removes a global | S |
| 4 | B2 | major | Delete one class; makes `enrollLearner` depend on the repository directly | S |
| 5 | E1 | minor | A rename, safest last and best done alone | S |

## 8. Noted deviations (not findings)

Looked at and cleared; none is a finding.

| # | Item | Where | Why it is not a finding |
|---|---|---|---|
| D-1 | `PaymentGateway` wraps an SDK client | `src/payments/payment-gateway.ts:13-27` `#confirmed` | An adapter over code the project does not own, a port. It also maps the SDK's result to `paid` / `declined` (`:23-25`), so it is not a forward |
| D-2 | `pricing` has four tiny files behind one function | `src/pricing/index.ts:6-10`, `src/pricing/internal/` `#confirmed` | Depth is measured at the module: one public function over four rule files. Small files inside a module are not shallow modules (B1) |
| D-3 | The guard `id must not be blank` appears twice | `src/courses/find-course.ts:8-11`, `src/enrollment/enroll-learner.ts:23-26` `#confirmed` | A four-line guard on different inputs (a course id, a learner id), far under C1's 20-line threshold, and not a business rule |

## 9. Open questions

| # | Question | Blocks | Needs |
|---|---|---|---|
| Q-1 | Does the project build and do its tests pass? `package.json:1-5` declares no scripts and no dependencies, yet `src/payments/payment-gateway.ts:1` imports `@acme/payments-sdk` and the tests import `vitest` | Nothing in this report (static) | The owner's build command; a run only with explicit opt-in |
| Q-2 | Must a duplicated course obey the 120-character title limit that `submitCourse` enforces? | The direction of the C1 fix (add the check to both, or drop it from submit) | Product owner |

## 10. Unverifiable

| ID | Check | Why | What would settle it |
|---|---|---|---|
| — | None | Every check was settled by reading code and tests | — |

## 11. Handoff

- **Fixes:** the `be-node` agent (Mode FIX). Work section 7 top-down.
- **Peer-owned findings:** none. E3 found no term with two meanings, so nothing goes to `business-analyst`; Q-2 is a product-owner decision.
- **Next round:** re-run `engineering:audit-architecture`; it enters Mode B and reuses every ID above.
