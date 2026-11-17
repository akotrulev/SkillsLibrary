---
paths:
  - "**/tests/{builders,mothers,seeders,data,test-data}/**"
  - "**/{e2e,e2e-tests,api-tests,apitests,ui-tests,mobile-tests,desktop-tests,acceptance-tests}/**/{builders,mothers,seeders,data,test-data}/**"
  - "**/*{Mother,Seeder}.ts"
  - "**/{e2e,tests,e2e-tests,ui-tests,api-tests}/**/fixtures.ts"
---

<!-- qa-typescript rules v1 (2026-11-17): test data. Installed by /qa-typescript:rules; edit the paths above to where this project keeps its builders, mothers, seeders, fixtures and data files. -->

# Test data

Severity tags as in the core rules. The codebase wins where it consistently does otherwise.

- Data with four or more fields comes from a builder or ObjectMother: pure (no persistence or async), typed as the real DTO, deterministic valid defaults (no `Date.now()`, no randomness on an asserted field). *minor*
- By default a test creates what it changes, with a value unique per test, and registers it for teardown in a fixture or hook. *major*
- Reference data: a search or filter test may read curated records already in the environment. They are named in the test or feature and never modified, and the test asserts the result is not empty before asserting on its rows; "every row has X" over nothing proves nothing. *blocker for a missing guard, else major*
- Pre-clean: a precondition may delete a leftover record before the test (a hook, fixture or `Given … does not exist` step), besides teardown, so a crashed run cannot poison the next. It goes through the API or a seeder, not a UI sequence. *minor*
- Keep on failure: teardown may keep what a failed test created, deleting on a pass and logging the kept ids on a failure (`testInfo.status !== testInfo.expectedStatus` in Playwright). That check is the teardown registry's legal branch, and it needs names unique per run so leftovers never collide. *major*
