---
paths:
  - "**/src/{test,integrationTest,testFixtures}/**/*.java"
  - "**/*{Test,Tests,IT}.java"
---

<!-- be-java rules v1 (2026-11-03): tests. Installed by /be-java:rules; edit to fit this project. -->

# Java test standards

Severity tags as in the core Java rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- A unit test constructs the class under test directly, with JUnit 5, Mockito and AssertJ. No Spring context: `@SpringBootTest`, `@DataJpaTest`, `@WebMvcTest` and `@MockBean` belong to integration tests. *major*
- Integration tests use the real database engine (Testcontainers), never H2. *major*
- Names state behaviour: `should_<Outcome>_when_<Condition>`. *minor*
- One logical assertion per test, and each assertion expects one value, never "this or that". *major*
- No `try`/`catch` in a test (use `assertThatThrownBy`), no `if`/`for` driving assertions (use `@ParameterizedTest`), no `Thread.sleep` (wait on a condition with Awaitility). *major*
- `BigDecimal` is compared with `isEqualByComparingTo`, never `isEqualTo`. *major*
- Inject `Clock`, id generators and config instead of mocking statics; never reach a private method by reflection, extract the class instead. *major*
- Do not test the framework (Jackson, record `equals`, Spring wiring) and do not mock `EntityManager` or a `JpaRepository` to "test a repository". *minor*
- No `lenient()` to silence a strict stub, no `verify(…)` with `any()` everywhere, no `@Disabled` without a linked issue. *minor*
- Test data with four or more fields comes from a builder. *minor*
- New code ships with unit tests covering at least 80% of the branches it wrote, measured with JaCoCo; only an asserting test counts. *major*
