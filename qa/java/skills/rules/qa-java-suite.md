---
paths:
  - "**/testng*.xml"
  - "**/src/test/resources/{allure,junit-platform,cucumber}.properties"
  - "**/src/test/resources/categories.json"
  - "**/{apitests,api-tests,uitests,ui-tests,mobiletests,mobile-tests,e2e,e2e-tests,acceptance-tests,test-automation,perf-tests}/{build.gradle.kts,build.gradle,pom.xml}"
---

<!-- qa-java rules v1 (2026-11-03): suite config and build. Installed by /qa-java:rules; add this project's test-module build files to the paths above. -->

# Test suite configuration standards

Severity tags as in the core qa-java rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

## TestNG

- Playwright and Appium suites run `parallel="classes"`, never `parallel="methods"`. Appium `thread-count` never exceeds the device count. *blocker*
- Suites sharing one Testcontainers instance run `parallel="false"`. *major*
- The gating run excludes the `flaky` group; a separate non-gating task runs it with `ignoreFailures = true`. *major*

## Allure

- allure-java 3 on every `allure-*` module, no 2.x module beside it; one adapter per module (never `allure-testng` with `allure-jupiter`). *major*
- One pinned report generator, the same version in the build and in CI. *major*
- `categories.json` lists the quarantine category first, matching `"flaky": true`, never an exception type. *minor*
- `build/allure-results/` is an artifact, never committed. *minor*

## Build

- Every plugin and dependency is pinned: no `+`, `latest.release` or floating Gatling plugin. *major*
- Gradle Kotlin DSL for a new suite; Maven only where the project uses it; never both in one module. Extend the suite's build file, never start a second one. *minor*
- Appium java-client 11 declares `selenium-support` for `WebDriverWait`. *major*
- Cucumber modules come from one BOM, with `cucumber-picocontainer` as the whole DI wiring. *minor*
