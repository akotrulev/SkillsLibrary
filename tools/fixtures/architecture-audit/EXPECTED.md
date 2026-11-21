# Expected findings — `course-platform/`

The answer key for the blind architecture audit. It sits above the audited root so an audit of `course-platform/` never reads it. Line numbers are for the files as committed.

## Planted defects

| # | Files | What is wrong | Expected id | Lines |
|---|---|---|---|---|
| P1 | `src/courses/submit-course.ts`, `src/courses/duplicate-course.ts` | 40 or more near-identical lines: validation, pricing, save. They have drifted: `submit-course` rejects a title over 120 characters and `duplicate-course` does not | C1, major | `submit-course.ts:7-59` against `duplicate-course.ts:6-56`; the title-length check is `submit-course.ts:31-33` |
| P2 | `src/enrollment/enrollment-service.ts` | Every method forwards its arguments to `EnrollmentRepository` and returns the result | B2, major | `enrollment-service.ts:4-22` (methods at 7, 11, 15, 19) |
| P3 | `src/catalog/index.ts` | Exports `CatalogRow`, the persistence row type, and the mutable `catalogCache` map | B3, major | `index.ts:4` (`CatalogRow`), `index.ts:5` (`catalogCache`) |
| P4 | `tests/pricing/discount-rules.test.ts` | Imports `src/pricing/internal/discount-rules.ts`, which `src/pricing/index.ts` does not export. No test imports `src/pricing/index.ts` | D1 and D3, major | `discount-rules.test.ts:2` |
| P5 | `src/progress/student-progress.ts` | Exports `StudentProgress`. The glossary's term is `Learner`, with `Student` under `Avoid` | E1, minor | `student-progress.ts:1` |

## Decoys — not findings

| # | Files | Why it is fine | Lines |
|---|---|---|---|
| N1 | `src/payments/payment-gateway.ts` | A thin adapter over a third-party SDK type: a port over code the project does not own | `payment-gateway.ts:1` (SDK import), `13-27` (the adapter) |
| N2 | `src/pricing/index.ts` | One exported function, `quote()`, over four internal files: a deep module | `index.ts:6-10` |
| N3 | a four-line guard repeated in `src/courses/` and `src/enrollment/` | Under C1's threshold | `src/courses/find-course.ts:8-11`, `src/enrollment/enroll-learner.ts:23-26` |

## Pass bar

P1–P5 are each reported under the expected id, with a `file:line` in the named file. N1–N3 are not findings.
