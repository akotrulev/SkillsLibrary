# Snapshot (approval) testing with ApprovalTests

Read this when a unit's output is a **large, structured value** whose whole shape is the contract: a mapper that
builds a 30-field DTO, a problem-detail translation, a generated document, a rendered template, a serialized
payload. ApprovalTests writes the output to a `*.received.*` file, compares it with the `*.approved.*` file a person
approved, and fails on any difference.

## Snapshot or targeted assertion

| The behaviour under test | Use |
|---|---|
| One value, one rule (a total, a status, a rounding boundary) | A targeted `assertThat` — a snapshot hides the one thing the test is about inside a file nobody reads |
| A branch of a mapper or validator | A targeted assertion per branch — the coverage floor counts asserting tests, and a snapshot asserts everything at once |
| The full shape of a large output, where any unintended change is a defect (field renamed, null appeared, order changed) | **A snapshot** |
| Output with no single owner of truth (generated SQL, an OpenAPI document, an email body) | **A snapshot**, reviewed in the diff like code |

A snapshot is **one logical assertion** — "the output equals the approved output" — so it obeys the one-assertion
rule. It never replaces the boundary tests: keep the `@ParameterizedTest` rows for the rules, add one snapshot for
the shape.

## Dependency and version lane

| Artifact | Version | Note |
|---|---|---|
| `com.approvaltests:approvaltests` | **31.0.0** (Java 8+, verified on Maven Central, 2026-11) | Not managed by the Spring Boot BOM, so it is pinned in the build; runs under JUnit 5 with no extension |

```kotlin
dependencies {
    testImplementation("com.approvaltests:approvaltests:31.0.0")
}
```

JSON snapshots use the Jackson already on the classpath (Boot 3.x ships Jackson 2): `JsonJacksonApprovals`. On
Jackson 3 the class is `JsonJackson3Approvals`.

## A snapshot test

```java
class OrderMapperTest {

    @Test
    void should_MapEveryOrderField_when_OrderIsShipped() {
        var order = anOrder().withStatus(SHIPPED).build();

        var dto = OrderMapper.toDto(order);

        JsonJacksonApprovals.verifyAsJson(dto, mapper -> mapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS),
            new Options().withScrubber(new GuidScrubber()));
    }
}
```

- `verifyAsJson` serializes with `findAndRegisterModules()` (so `java.time` types work), sorts map entries by key,
  and pretty-prints; the builder function adjusts the mapper — ISO dates read better in a review than epoch numbers.
- The approved file lands beside the test class as
  `OrderMapperTest.should_MapEveryOrderField_when_OrderIsShipped.approved.json`.
- Plain text output: `Approvals.verify(text)`; HTML: `Approvals.verifyHtml(html)`; any object's `toString()`:
  `Approvals.verify(object)`.
- Parameterized: `Approvals.NAMES.withParameters(options, region)` (or `Approvals.NAMES.withParameters(region)` with
  no other options) adds the value to the file name, so each row has its own approved file.

## Scrubbers — what makes a snapshot stable

- **Prefer fixing the seam to scrubbing.** A date from a `Clock.fixed` the test passes in, or an id from a stubbed
  `IdGenerator`, is already stable; scrubbing is for values the test cannot control.
- **`GuidScrubber`** replaces each UUID with `guid_1`, `guid_2`…; the same value always maps to the same number, so
  "these two ids are equal" survives scrubbing.
- **`DateScrubber.getScrubberFor("<an example>")`** recognises the example's format and replaces each date with
  `[Date1]`…; it throws when it does not know the format.
- **Anything else that varies per run** — a token, a host name, a port — gets a
  `new RegExScrubber("<pattern>", "[name]")` scoped to the one test that needs it.
- Several at once: `new Options().withScrubber(Scrubbers.scrubAll(guids, dates, tokens))`, applied in that order.

## Where the files live

Approved files sit beside the test by default. To keep them out of the package listing, a `PackageSettings` class in
the test package root moves them for every test below it:

```java
package com.acme.ordering;

public class PackageSettings {
    public static final String UseApprovalSubdirectory = "approvals";
}
```

## Source control

- `.gitignore`: `*.received.*` — the received file is the failed run's output, never committed.
- **Commit every `*.approved.*`**, reviewed in the pull request like code.
- `.gitattributes`: `*.approved.* text eol=lf` — ApprovalTests ignores line-ending differences when it compares,
  but the pull-request diff stays clean.

## CI never accepts a snapshot

- A test with **no `.approved.` file fails** and writes a `.received.` file. That is the behaviour CI must keep: a
  missing snapshot is a test that was never approved.
- **Never approve automatically** — no `AutoApproveReporter`, no step copying received over approved. Accepting a
  snapshot is a human decision, made locally in the diff tool the default reporter opens, or by renaming the received
  file to `.approved.`.
- On CI, set `APPROVAL_TESTS_USE_REPORTER=org.approvaltests.reporters.QuietReporter` so a failure reports without
  trying to open a diff tool, and upload `**/*.received.*` as a build artifact on failure so the reviewer sees what
  changed without re-running.
- A Jackson upgrade (it arrives with a Boot upgrade) can change JSON formatting: run the snapshot tests after the
  bump, review the diffs, then accept them in the same change.
