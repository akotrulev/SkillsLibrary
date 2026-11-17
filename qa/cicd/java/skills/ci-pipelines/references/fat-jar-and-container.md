# QA — One runnable test jar and a containerized run (Java 21, TestNG)

Builds the suite into **one runnable jar** (test classes, test resources, `testng.xml` and the test runtime classpath, run by TestNG's own `main`) and runs that jar in a **container that writes the Allure report to a mounted volume**. The jar runs anywhere a JRE is: a machine without Gradle, a scheduled job, a container. The container is the same run on any CI host. Both are linked from `qa/java/skills/api-project-setup`, `qa/java/skills/ui-project-setup` and this skill's `SKILL.md`.

Verified 2026-11-17: the Kotlin DSL task against the Gradle 9.9 user manual (*Working With Files*, "Using `Project.zipTree()` and the `Jar` task"); `-testjar` and `-xmlpathinjar` in `org.testng.CommandLineArgs` of TestNG 7.12.0; `ADD --checksum` (Dockerfile syntax 1.6+) and exec-form `ENTRYPOINT` in the Dockerfile reference; `docker run`'s exit status (the command's own code, except 125–127) in the Docker docs; `--single-file`, `--clean` and `-o` in `allure-commandline` 2.46.1. Run end to end on 2026-11-17 with the API scaffold: `./gradlew fatJar` (wrapper 9.6.1) inside the build stage, the API image built, and the container run against a local service: exit 0 on a pass, exit 1 on a failure, `-groups smoke` passed through, `allure-results/` and a single-file `allure-report/index.html` written to the mounted folder. The UI image was not built.

## When to use

- The suite must run where Gradle is not installed, or as one artifact promoted from build to run.
- A pull request or a scheduled job runs the suite in a container and keeps the report.

## When NOT to use

- A CI job that already runs `./gradlew test` on a runner: keep that, it is the lane in the host references.
- Visual baselines in the Playwright image: `qa/java/skills/visual-regression/references/playwright-snapshots.md` §8.

## The `fatJar` task

Added to the suite's `build.gradle.kts` (the API scaffold's asset already has it; the UI scaffold appends it to the Playwright asset's build):

```kotlin
tasks.register<Jar>("fatJar") {
    group = "build"
    description = "One runnable jar: test classes, test resources, testng.xml and the test runtime classpath."
    archiveFileName.set("${rootProject.name}.jar")
    manifest {
        attributes("Main-Class" to "org.testng.TestNG")
    }
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
    from(sourceSets.test.get().output)
    from("testng.xml")
    dependsOn(configurations.testRuntimeClasspath)
    from({
        configurations.testRuntimeClasspath.get().filter { it.name.endsWith("jar") }.map { zipTree(it) }
    })
    exclude("META-INF/*.SF", "META-INF/*.DSA", "META-INF/*.RSA", "META-INF/*.EC", "META-INF/INDEX.LIST")
}
```

- `sourceSets.test` and `testRuntimeClasspath`, not `main` and `runtimeClasspath`: the framework lives in `src/test/java` and its libraries are `testImplementation`, so nothing moves to production scope to make the jar.
- The manifest is written through `attributes(...)`, so its lines are well formed; a hand-written `Main-Class` line with a leading space is not read and the jar does not start.
- Signature files are excluded: a signed library's `.SF`/`.RSA` no longer matches the merged jar and the JVM refuses it. `INDEX.LIST` is excluded too: Groovy (pulled in by RestAssured) ships one that lists only its own packages, and a class loader that trusts it misses every other class.
- `DuplicatesStrategy.EXCLUDE` keeps the first copy of a duplicate entry. A duplicate `META-INF/services/*` file would lose one library's service registration; check with `unzip -l build/libs/<name>.jar | grep META-INF/services` after adding a library. The current pins have none.
- Keep Gradle's default directory entries. TestNG's `<package>` scan lists a package through its directory entry, and a jar without them runs zero tests (exit code 8).
- `testng.xml` sits at the jar root, so `-xmlpathinjar testng.xml` finds it.

## Run it

```bash
./gradlew fatJar
java -jar build/libs/api-tests.jar -testjar build/libs/api-tests.jar -xmlpathinjar testng.xml
java -DAPI_URL=https://api.staging.example.test -jar build/libs/api-tests.jar -testjar build/libs/api-tests.jar -xmlpathinjar testng.xml -groups smoke
```

- `-D` on the `java` command is read by `Env` directly; an environment variable wins over it (`Env`'s precedence: environment, then system property, then `env.properties`).
- TestNG's exit code is the result and nothing may swallow it: `0` all passed, `1` a failure, `2` a skip, `8` no test ran. A wrapper script keeps it (below); a pipeline step never adds `|| true`.
- Allure results go where `allure.results.directory` points; pass `-Dallure.results.directory=allure-results` so the run does not depend on a default. The Gradle Allure plugin sets it for `./gradlew test`, not for the jar.
- `@Step` methods need the AspectJ weaver as a `-javaagent`, which the Gradle plugin adds to `./gradlew test` and the jar run does not have. The jar's report still has every test, the HTTP exchanges and `BaseTest`'s failure evidence, which are written without weaving; steps from `@Step` appear only in the Gradle run.

## Data files come from the classpath

A source-tree path (`src/test/resources/orders.csv`) does not exist inside the jar. Every file a test reads lives under `src/test/resources` and is opened through the class loader:

```java
try (InputStream rows = OrdersData.class.getClassLoader().getResourceAsStream("data/orders.csv")) {
```

`Env` reads `env.properties` the same way. A file a test writes (evidence, downloads) goes under the working directory, which the container mounts.

## The container

The image is built **from the working tree** (`COPY . .`), never by cloning the repository inside it, so a pull-request run tests the pull request. The base images, the Gradle version (the wrapper's `gradle-wrapper.properties`) and the Allure CLI are pinned. No secret is in the image: credentials arrive at `docker run` as environment variables.

`run-tests.sh`, at the project root and executable:

```sh
#!/bin/sh
set -u
java -Dallure.results.directory=allure-results -jar /app/tests.jar -testjar /app/tests.jar -xmlpathinjar testng.xml "$@"
status=$?
allure generate --clean --single-file -o allure-report allure-results || exit 1
exit "$status"
```

The script returns the test run's code; a report that cannot be generated fails a green run instead of hiding. Its two lines of control flow are infrastructure, like a base test's.

`Dockerfile`, API suite:

```dockerfile
# syntax=docker/dockerfile:1.7
FROM eclipse-temurin:21.0.13_9-jdk-noble AS build
WORKDIR /src
COPY . .
RUN ./gradlew --no-daemon fatJar

FROM eclipse-temurin:21.0.13_9-jre-noble
ADD --checksum=sha256:37428164f310c8d137cfdd2c3a25d049b233261ddab13e1bd4dfd7627b5cbf8d \
    https://repo1.maven.org/maven2/io/qameta/allure/allure-commandline/2.46.1/allure-commandline-2.46.1.tgz /tmp/allure.tgz
RUN tar -xzf /tmp/allure.tgz -C /opt && rm /tmp/allure.tgz
ENV PATH="/opt/allure-2.46.1/bin:${PATH}"
COPY --from=build /src/build/libs/api-tests.jar /app/tests.jar
COPY --chmod=0755 run-tests.sh /app/run-tests.sh
WORKDIR /reports
ENTRYPOINT ["/app/run-tests.sh"]
```

UI suite: the same first five lines (the syntax directive and the build stage), then a runtime stage on the Playwright image, whose tag equals the Playwright pin (`qa/java/skills/ui-test-author/playwright`, **Versions**). The image already holds the browsers for 1.63.0 and a Java runtime newer than 21, which runs the jar unchanged.

```dockerfile
FROM mcr.microsoft.com/playwright/java:v1.63.0-noble
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
ADD --checksum=sha256:37428164f310c8d137cfdd2c3a25d049b233261ddab13e1bd4dfd7627b5cbf8d \
    https://repo1.maven.org/maven2/io/qameta/allure/allure-commandline/2.46.1/allure-commandline-2.46.1.tgz /tmp/allure.tgz
RUN tar -xzf /tmp/allure.tgz -C /opt && rm /tmp/allure.tgz
ENV PATH="/opt/allure-2.46.1/bin:${PATH}"
COPY --from=build /src/build/libs/ui-tests.jar /app/tests.jar
COPY --chmod=0755 run-tests.sh /app/run-tests.sh
WORKDIR /reports
ENTRYPOINT ["/app/run-tests.sh"]
```

`.dockerignore`, so the host's build output and secrets never enter the build context:

```
.git/
.gradle/
build/
allure-results/
reports/
.env
```

Build and run:

```bash
docker build -t api-tests .
docker run --rm --user "$(id -u):$(id -g)" -e API_URL -v "$PWD/reports:/reports" api-tests
docker run --rm --user "$(id -u):$(id -g)" -e API_URL -v "$PWD/reports:/reports" api-tests -groups smoke
docker run --rm --ipc=host -e BASE_URL -e E2E_USER -e E2E_PASSWORD -v "$PWD/reports:/reports" ui-tests
```

- `/reports` is the working directory, so everything the run writes lands in the mounted folder: `allure-results/`, the single-file report `allure-report/index.html`, and the UI suite's `build/playwright-artifacts/`. The report goes to a subfolder because `--clean` deletes its output folder, and a mount point cannot be deleted.
- Arguments after the image name reach TestNG (`-groups smoke`), through the exec-form `ENTRYPOINT` and `"$@"`.
- `docker run` exits with the script's code, so the CI step fails when a test fails. Docker's own failures are 125–127.
- `-e NAME` with no value passes the caller's variable through; a CI job maps its secret store to those names. Never `ENV` or `ARG` a secret in the Dockerfile: both are kept in the image's history.
- `--user` makes the files in `./reports` belong to the caller. The Playwright image runs as root by default; add `--user pwuser` there only when the tests visit untrusted sites, and give that user a writable mount.
- Bumping Playwright means bumping the image tag in the same change, or the run fails with "Executable doesn't exist". A new Allure CLI version changes the URL, the folder name in `PATH` and the checksum (`sha256sum` of the archive from Maven Central).

## In CI

The container lane in each host reference is two steps, build then run, with the `reports` folder uploaded on every outcome:

```bash
docker build -t "$SUITE" .
docker run --rm --user "$(id -u):$(id -g)" -e API_URL -v "$PWD/reports:/reports" "$SUITE"
```

The run step is gating: no `continue-on-error`, no `|| true`. The upload step runs always (`if: always()`, `condition: always()`, `when: always`) so a red run keeps its report. A GitLab Docker-executor job has no daemon by default: it needs the `docker:dind` service, and copies the report out with `docker cp` instead of a bind mount (`gitlab-ci.md`, container lane).

## Do not

- Clone the repository inside the image (it tests the default branch, not the change).
- Use a floating tag (`eclipse-temurin:21`, `playwright/java:latest`) or install the Allure CLI without a version.
- Add `|| true`, `set +e` around the test command, or `continue-on-error` on the step that runs it.
- Bake a credential into `env.properties`, an `ENV` line or a build argument.
- Read a data file from `src/test/resources/...` by path.
