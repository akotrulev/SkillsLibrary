---
paths:
  - "**/build.gradle.kts"
  - "**/build.gradle"
  - "**/config/checkstyle/*.xml"
---

<!-- be-java rules v1 (2026-11-21): lint. Ids checked against the tools' documentation on 2026-11-21 (Error Prone 2.53, Checkstyle 14.4, Gradle 9.6, JDK 21). Installed by /be-java:rules; edit the paths above to where this project keeps its Gradle build files and Checkstyle config, re-run to compare with the plugin's copy. -->

# Java lint standards

Severity tags as in the core Java rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

Each row below is a rule of `java.md` or `java-tests.md` that Error Prone or Checkstyle detects, so the build catches it before a review does. Rules no stock check detects stay in those files and get no row: constructor injection, `@Transactional` self-invocation, SQL built by concatenation, one assertion per test, module boundaries (an ArchUnit test, not a lint).

## Enforced by the build

| House rule (file, section) | Tool | Rule id or setting | Level |
|---|---|---|---|
| No static mutable state; `static final` constants are fine (`java.md`, Dependency injection) | Error Prone | `NonFinalStaticField` | error |
| No `System.out`, no `printStackTrace()`; log through SLF4J (`java.md`, Logging, errors and secrets) | Error Prone | `SystemOut`, `CatchAndPrintStackTrace` | error |
| Catch specific exceptions, never `catch (Exception e)` (`java.md`, Logging, errors and secrets) | Checkstyle | `IllegalCatch` | error |
| A caught exception is never ignored, and a rethrow keeps the cause (`java.md`, Logging, errors and secrets) | Error Prone | `EmptyCatch`, `UnusedException` | error |
| `InterruptedException` is never swallowed (`java.md`, Threading and async) | Error Prone | `InterruptedExceptionSwallowed` | error |
| No `new Thread(…)` in business code (`java.md`, Threading and async) | Checkstyle | `IllegalInstantiation` for `java.lang.Thread` | error |
| `Optional` is a return type only, never a field or a parameter (`java.md`, Types) | Checkstyle | `IllegalType` for `java.util.Optional` on fields, parameters and record components | error |
| A unit test has no Spring context: no `@SpringBootTest`, `@DataJpaTest`, `@WebMvcTest`, `@MockBean` (`java-tests.md`) | Checkstyle | `IllegalImport` in `checkstyle-test.xml` | error |
| No `try`/`catch` in a test; use `assertThatThrownBy` (`java-tests.md`) | Checkstyle | `IllegalToken` for `LITERAL_CATCH` in `checkstyle-test.xml` | error |

A row the project's config does not enforce is *minor*.

Turning a row off to pass a gate is *major* (`engineering:quality-constraints`).

How the rows are wired:

- Each Error Prone row is named in `options.errorprone { error(…) }` on every `JavaCompile` task, with `error_prone_core` on the `errorprone` configuration. `error(…)` sets the id to ERROR whether or not Error Prone runs it by default, so a finding fails `compileJava`.
- Each Checkstyle row is a module in `config/checkstyle/checkstyle.xml`, with `severity` set to `error` on the `Checker` and `maxWarnings = 0` in Gradle, so a finding fails `checkstyleMain`. The two test rows live in a second file, `checkstyle-test.xml`, wired to `checkstyleTest` only: an integration source set gets whichever file its own task is given.
- A boundary that must catch everything (a global exception handler) suppresses its row where it stands, with the reason in the same change: `@SuppressWarnings("EmptyCatch")` for Error Prone, `@SuppressWarnings("checkstyle:illegalcatch")` for Checkstyle, which needs `SuppressWarningsFilter` and `SuppressWarningsHolder` in the config.
- Generated code is checked, not skipped. Error Prone reads every compiled source, annotation-processor output and a class marked `@Generated` included, and Checkstyle reads a generated directory added to `sourceSets.main.java` (it never reads annotation-processor output). Exclude both by path in the build file, as the block below does; no other file decides it.
- Three rows detect only part of their prose rule. `InterruptedExceptionSwallowed` fires where a `catch (Exception | Throwable)` hides an `InterruptedException`; a `catch (InterruptedException e)` that only logs stays a review finding. `IllegalCatch` also flags `catch (RuntimeException e) { throw e; }`. `IllegalType` with `memberModifiers` skips local variables, as the rule allows, and misses a non-`final` field with no access modifier.

`build.gradle.kts`:

```kotlin
plugins {
    checkstyle
    id("net.ltgt.errorprone") version "5.2.0"
}

dependencies {
    errorprone("com.google.errorprone:error_prone_core:2.53.0")
}

tasks.withType<JavaCompile>().configureEach {
    options.errorprone {
        excludedPaths = ".*/build/generated/.*"
        error(
            "NonFinalStaticField",
            "SystemOut",
            "CatchAndPrintStackTrace",
            "EmptyCatch",
            "UnusedException",
            "InterruptedExceptionSwallowed",
        )
    }
}

checkstyle {
    toolVersion = "14.4.0"
    configFile = file("config/checkstyle/checkstyle.xml")
    maxWarnings = 0
}

tasks.named<Checkstyle>("checkstyleMain") {
    exclude { it.file.path.contains("/build/generated/") }
}

tasks.named<Checkstyle>("checkstyleTest") {
    configFile = file("config/checkstyle/checkstyle-test.xml")
}
```

`config/checkstyle/checkstyle.xml`:

```xml
<?xml version="1.0"?>
<!DOCTYPE module PUBLIC "-//Checkstyle//DTD Checkstyle Configuration 1.3//EN" "https://checkstyle.org/dtds/configuration_1_3.dtd">
<module name="Checker">
  <property name="severity" value="error"/>
  <module name="SuppressWarningsFilter"/>
  <module name="TreeWalker">
    <module name="SuppressWarningsHolder"/>
    <module name="IllegalCatch"/>
    <module name="IllegalInstantiation">
      <property name="classes" value="java.lang.Thread"/>
    </module>
    <module name="IllegalType">
      <property name="illegalClassNames" value="java.util.Optional"/>
      <property name="tokens" value="PARAMETER_DEF, RECORD_COMPONENT_DEF, VARIABLE_DEF"/>
      <property name="memberModifiers" value="LITERAL_PRIVATE, LITERAL_PROTECTED, LITERAL_PUBLIC, FINAL, LITERAL_STATIC"/>
    </module>
  </module>
</module>
```

`config/checkstyle/checkstyle-test.xml`:

```xml
<?xml version="1.0"?>
<!DOCTYPE module PUBLIC "-//Checkstyle//DTD Checkstyle Configuration 1.3//EN" "https://checkstyle.org/dtds/configuration_1_3.dtd">
<module name="Checker">
  <property name="severity" value="error"/>
  <module name="SuppressWarningsFilter"/>
  <module name="TreeWalker">
    <module name="SuppressWarningsHolder"/>
    <module name="IllegalImport">
      <property name="illegalClasses" value="org.springframework.boot.test.context.SpringBootTest, org.springframework.boot.test.mock.mockito.MockBean, org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest, org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest"/>
    </module>
    <module name="IllegalToken">
      <property name="tokens" value="LITERAL_CATCH"/>
    </module>
  </module>
</module>
```
