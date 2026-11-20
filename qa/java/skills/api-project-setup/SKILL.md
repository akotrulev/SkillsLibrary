---
name: api-project-setup
description: Use when starting a RestAssured + TestNG API test project from zero in Java (Gradle, pins, Env, fat jar). Triggers "scaffold an API test project". Not for adding tests (api-tests).
disable-model-invocation: true
---

# API Test Project Scaffold (Java 21)

This skill stands up a **runnable, empty API test project from zero**: the Gradle Kotlin DSL build with the exact pins, the layout, the `Env` config loader with its override order, the base client and base test, one smoke test that proves the wiring, the run commands, a fat test jar and a container. It owns the **project shell**. DTOs, clients and test classes are authored with `api-models`, `api-client-writer` and `api-test-author/writer`; this skill copies its own `assets/` into the layout and points at those skills for everything after the smoke test.

**Version rule:** new projects use Java 21 (17 is the minimum) and Gradle with the Kotlin DSL. An existing Maven project stays on Maven with the same coordinates; an existing suite is authored into, never re-scaffolded.

## Tooling & versions

`assets/build.gradle.kts` holds exactly these pins. The Allure rows are the one pin set of `qa/reporting/java/skills/test-reports`; TestNG and AssertJ match the other Java scaffolds.

| Concern | Package / tool | Version | Notes |
|---|---|---|---|
| Language | Java toolchain | **21** | `languageVersion.set(JavaLanguageVersion.of(21))`; 17 minimum on a down-level repo |
| Build | Gradle (wrapper) | **9.6** | Kotlin DSL; the wrapper pins it for every machine and the image |
| HTTP client | `io.rest-assured:rest-assured` | **6.3.0** | Java 17+, Groovy 5. Verified on Maven Central 2026-11-17; 7.0.0 is a release candidate, not used |
| JSON | `com.fasterxml.jackson.core:jackson-databind` | **2.22.4** | RestAssured 6.3.0 is built on Jackson 2.22 and does not pull it in (optional dependency): declare it |
| Dates | `com.fasterxml.jackson.datatype:jackson-datatype-jsr310` | **2.22.4** | `JavaTimeModule` for `OffsetDateTime` |
| Test runner | `org.testng:testng` | **7.12.0** | allure-testng 3 needs TestNG ≥ 7.10 |
| Assertions | `org.assertj:assertj-core` | **3.27.7** | |
| Reporting | `io.qameta.allure:allure-testng`, `allure-rest-assured` | **3.0.0** | Gradle plugin `io.qameta.allure` **4.3.0** with `allureJavaVersion.set("3.0.0")` |
| Report generator | `allure-commandline` | **2.46.1** | `allure.version` in the build; the CLI pin on a runner and in the image |
| Status constants | `org.apache.http.HttpStatus` | from RestAssured | httpcore 4.4.16 arrives with RestAssured's `httpclient` 4.5.14 |

## Prerequisites & local setup

```bash
java --version
docker --version
```

- `java --version` prints 21 (or the repo's 17). Gradle need not be installed once the wrapper is committed; create the wrapper with a local Gradle once (`gradle wrapper --gradle-version 9.6`).
- Docker is needed only for the container run. No browser, emulator or Appium server: the cheapest suite to stand up.

## Project layout

```
api-tests/
├── build.gradle.kts                 # assets/build.gradle.kts: pins, Allure, -D forwarding, fatJar
├── settings.gradle.kts              # assets/settings.gradle.kts
├── testng.xml                       # assets/testng.xml: parallel="classes"
├── Dockerfile · run-tests.sh · .dockerignore   # fat-jar-and-container.md
├── gradlew · gradle/wrapper/
├── .gitignore
└── src/test/
    ├── resources/env.properties     # assets/env.properties: non-secret defaults only
    └── java/com/example/apitests/
        ├── support/
        │   ├── Env.java             # assets/Env.java: the config class
        │   ├── BaseApiTest.java     # assets/BaseApiTest.java: telemetry link on failure
        │   ├── TestTrace.java       # api-client-writer/references/trace-context.md
        │   └── TelemetryLinks.java  # test-reports/references/trace-links.md
        ├── clients/
        │   ├── BaseApiClient.java   # assets/BaseApiClient.java: spec, strict mapper, parse failures
        │   ├── TraceparentFilter.java # api-client-writer/references/trace-context.md
        │   └── HealthClient.java    # assets/HealthClient.java: the smoke's client
        ├── models/health/HealthDto.java   # assets/HealthDto.java
        └── tests/health/HealthTest.java   # assets/HealthTest.java: the smoke
```

- Everything lives in the **test source set** and every library is `testImplementation`: a test project has no production code, and the qa-java rule globs expect `src/test/java`. A repo that already keeps clients under `src/main/java` keeps them there.
- Name the folder `api-tests`: the qa-java rule files match that folder name for the build file (`qa-java-suite.md`). As a module of a larger build, include it from the root `settings.gradle.kts` (`include("api-tests")`) and run `./gradlew :api-tests:test`.
- New resources follow `api-client-writer` and `api-models`: `clients/{api}/{Resource}Client.java`, `models/{api}/{resource}/{Resource}Dto.java`, `tests/{api}/{resource}/{Operation}{Resource}Test.java`.

## Create from zero

```bash
mkdir api-tests && cd api-tests
git init
gradle wrapper --gradle-version 9.6
mkdir -p src/test/resources src/test/java/com/example/apitests/{support,clients,models/health,tests/health}
```

Copy the assets from `qa/java/skills/api-project-setup/assets/`:

| Asset | Goes to |
|---|---|
| `build.gradle.kts`, `settings.gradle.kts`, `testng.xml` | the project root |
| `env.properties` | `src/test/resources/` |
| `Env.java`, `BaseApiTest.java` | `support/` |
| `BaseApiClient.java`, `HealthClient.java` | `clients/` |
| `HealthDto.java` | `models/health/` |
| `HealthTest.java` | `tests/health/` |

Then copy the three listings the base classes use, replacing `com.{org}` with the package root: `TestTrace` and `TraceparentFilter` from `qa/java/skills/api-client-writer/references/trace-context.md`, `TelemetryLinks` from `qa/reporting/java/skills/test-reports/references/trace-links.md`. Rename the package root `com.example.apitests` to the project's group in every file and in `testng.xml`, and point `HealthClient`'s `GET_PATH` and `HealthDto` at the service's real health contract (Spring Actuator answers `/actuator/health` with `{"status":"UP"}`).

```bash
./gradlew compileTestJava
API_URL=https://api.staging.example.test ./gradlew test
```

The exit gate: it compiles with no warning, and the smoke is green against a reachable service.

## Configuration: `Env`

One config class, one name constant and one typed getter per key; a missing key fails fast naming the key and the three ways to set it. **Precedence, one order everywhere:**

1. the environment variable (`API_URL=… ./gradlew test`, `docker run -e API_URL`, the CI secret store);
2. the JVM system property (`./gradlew test -DAPI_URL=…`, `java -DAPI_URL=… -jar …`);
3. `src/test/resources/env.properties`, read from the classpath, so it works inside the fat jar.

- `env.properties` is committed and holds **non-secret defaults only**, one line per key `Env` reads. A secret (a client secret, a password) has no line in it: the environment is its only source, and `Env` reports it missing by name. Auth0 keys follow `qa/java/skills/test-login-tokens`, which reads them from the environment.
- Gradle runs tests in a forked JVM, so a `-D` given to Gradle does not reach the test by itself. The build forwards exactly the keys `env.properties` declares:

```kotlin
val envKeys: Set<String> = Properties()
    .apply { file("src/test/resources/env.properties").inputStream().use { load(it) } }
    .stringPropertyNames()

tasks.test {
    useTestNG {
        suites("testng.xml")
    }
    envKeys.forEach { key -> System.getProperty(key)?.let { systemProperty(key, it) } }
}
```

- A key no class reads is not declared. Add a key in three places in one change: the constant and getter in `Env`, the default in `env.properties` (none for a secret), the caller.
- `Env` holds no mutable state: the file is read once into a constant, and nothing writes system properties.

## The base client and the smoke

- `BaseApiClient` is the one HTTP stack: `spec()` builds a fresh RestAssured request per call (no `RestAssured.baseURI` or other static global), adds `TraceparentFilter` then `AllureRestAssured`, and sends `Authorization: Bearer` unless the token is `""` (anonymous). Its `ObjectMapper` registers `JavaTimeModule` once and enables `FAIL_ON_UNKNOWN_PROPERTIES`, so an undeclared response field fails the parse. `deserialize` / `deserializeList` attach the raw body, then fail naming the target type, Jackson's reference chain (the JSON path) and the payload.
- Clients follow `api-client-writer`: a raw overload returning `Response`, a typed overload that asserts the expected status and returns the DTO. Where that skill's template builds the base URI from `ConfigurationLoader.getTestEnvironment().apiUri()`, this project's call is `Env.apiUrl()`.
- `BaseApiTest` is the class every test extends. Its `@AfterMethod(alwaysRun = true)` attaches the Grafana trace links to a failed test when `GRAFANA_URL` is set (`test-reports/references/trace-links.md`).
- `HealthTest.Should_ReportUp_When_ServiceIsRunning` builds an anonymous `HealthClient` in `@BeforeMethod(alwaysRun = true)` and asserts the typed call's status and body. It reads no environment-owned record, so it runs against any environment. It proves the build, `Env`, the base client, the strict mapper, Allure and the runner; it is not a test of the service.

## Run

```bash
./gradlew test
./gradlew test -DAPI_URL=https://api.staging.example.test
API_URL=https://api.staging.example.test ./gradlew test --tests '*HealthTest'
./gradlew clean test allureReport
./gradlew allureReport --single-file=true
./gradlew fatJar
java -jar build/libs/api-tests.jar -testjar build/libs/api-tests.jar -xmlpathinjar testng.xml -groups smoke
```

- allure-java 3 no longer cleans its results folder: run `clean` before a local report.
- The fat jar, its exit codes, the classpath rule for data files, the Dockerfile that runs the suite and writes the single-file report to a mounted volume, and the CI container lane: [`qa/cicd/java/skills/ci-pipelines/references/fat-jar-and-container.md`](../../../cicd/java/skills/ci-pipelines/references/fat-jar-and-container.md).
- The single-file report on its own: `qa/reporting/java/skills/test-reports/references/single-file-report.md`.

## `.gitignore`

```
build/
.gradle/
allure-results/
allure-report/
reports/
.env
```

## Conventions (the shell only)

The standards the shell must meet are the qa-java rule files, not a list here: `qa-java.md` (core), `qa-java-api.md` and `qa-java-suite.md`. Tell the user to install them with the shell (`/qa-java:rules` copies them into `.claude/rules/qa-java/`); until then read the plugin's copies in `qa/java/skills/rules/`. Where they and this skill's recipes disagree, the rule files win.

- **Tokens** are fetched once per identity in setup with `qa/java/skills/test-login-tokens` and passed to a client's constructor; never in a test, a client or `Env`.
- **Allure**: the adapter, the HTTP filter and the base test's hook are wired; annotations, categories and publishing are `qa/reporting/java/skills/test-reports`'s.
- **CI**: the host pipelines and their container lane are `qa/cicd/java/skills/ci-pipelines`.

## Setup checklist

- [ ] JDK 21 (or the repo's 17); `gradlew` committed with Gradle 9.6
- [ ] `build.gradle.kts` from the assets: every pin above, no `+` or `latest`, every library `testImplementation`
- [ ] Framework code under `src/test/java`; package root renamed in code and in `testng.xml`
- [ ] `Env` is the only config reader; `env.properties` holds non-secret defaults, one line per key read; secrets only in the environment
- [ ] `-D` reaches the test JVM through the forwarding block; the environment wins over `-D`, `-D` over the file
- [ ] `BaseApiClient` builds a spec per call, no static RestAssured state; strict `ObjectMapper`
- [ ] `TestTrace`, `TraceparentFilter`, `TelemetryLinks` copied from their references
- [ ] `HealthTest` green against the target environment; `./gradlew compileTestJava` warning-free
- [ ] `./gradlew fatJar` produces a jar that runs the smoke with `-groups smoke`
