# Visual Regression — Percy (Java / Playwright 1.63 + TestNG)

Percy (BrowserStack) **uploads a DOM snapshot** of the page and **renders and diffs it server-side**.
Baselines live in Percy's cloud, keyed by git branch, and a person approves changes in its review UI. The
build is gated on that review — a status check — not on anything the test asserts. The Java binding is
`io.percy:percy-playwright-java`; the agent that receives snapshots is the Node `@percy/cli`, wrapped around
the Gradle run with `percy exec`.

This is an **assertion layer** on page objects that already exist. A Percy class extends
`com.example.uitests.support.BaseTest` (`qa/java/skills/ui-test-author/playwright/assets/BaseTest.java`) and
adds one `percy.snapshot(...)` call to a flow the page objects drive.

## Why graduate from screenshot plus comparator to Percy

| | Screenshot plus comparator | **Percy** |
|---|---|---|
| What leaves the test | Nothing — a PNG is compared locally | A **DOM snapshot** is uploaded |
| Where rendering happens | The pinned image | **Percy's renderers**, the same for everyone |
| Where baselines live | `src/test/resources/baselines/<os>-<browser>/` | **Percy cloud**, per branch |
| Baselines made in the pinned image | Mandatory | **Not needed** |
| Updating a baseline | `UPDATE_BASELINES=1` in the image, reviewed in the PR diff | **Approve in the review UI** |
| Tolerance | Comparator settings and masks | `percyCSS`, `scope`, ignore regions — no pixel ratio |
| Gate | An AssertJ assertion on the comparison | **The Percy status check** |
| Cost | Free | Paid, per snapshot |

## 1. Setup

Pins checked on 2026-10-11 (Maven Central, npm):

```kotlin
dependencies {
    testImplementation("io.percy:percy-playwright-java:1.2.1")
}
```

```bash
npm install --save-dev --save-exact @percy/cli@1.32.11
```

`PERCY_TOKEN` is the **only** secret — a per-project write token from the CI secret store, never committed
or logged. Locally: `export PERCY_TOKEN=<token>`.

## 2. Running the suite — `percy exec`

`percy exec` starts the local agent (it receives snapshots, discovers assets and uploads them), runs the
command, then finalizes the build:

```bash
npx percy exec -- ./gradlew --no-daemon visualTest
```

**Without the agent, `percy.snapshot` is a no-op.** The binding's healthcheck fails, every snapshot call
returns `null`, and the test passes. A developer without the token runs the functional suite untouched, and
a CI job that forgets `percy exec` gets no visual coverage at all — so the visual job always runs under it.

The `visualTest` task and the `visual` group are the same as the comparator lane's
(`references/playwright-snapshots.md` §1): visual tests run nightly, not in the PR gate.

## 3. `.percy.yml` — project-wide snapshot config

The agent's config, identical for every language binding:

```yaml
version: 2
snapshot:
  widths:
    - 375
    - 1280
  min-height: 1024
  percy-css: |
    [data-testid="Chat.Launcher"] { visibility: hidden !important; }
discovery:
  allowed-hostnames:
    - cdn.example.test
  network-idle-timeout: 250
```

`percy exec --config ./config/.percy.yml -- …` when it is not at the repository root. Per-snapshot options
deep-merge over it: per-call values win, and a per-call `null` never clears a configured value.

## 4. The core pattern

```java
package com.example.uitests.tests;

import com.example.uitests.pages.PricingPage;
import com.example.uitests.support.BaseTest;
import io.percy.playwright.Percy;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import java.util.List;
import java.util.Map;

public class PricingPercyTest extends BaseTest {
    private Percy percy;
    private PricingPage pricingPage;

    @BeforeMethod(alwaysRun = true)
    public void createPercy() {
        page.clock().setFixedTime("2026-10-10T09:00:00Z");
        percy = new Percy(page);
        pricingPage = new PricingPage(page);
    }

    @Test(groups = "visual",
          description = "No assertion: Percy renders and diffs this snapshot server-side; the build's Percy status check, approved in Percy's review UI, is the verdict.")
    public void Should_UploadPlanTableSnapshot_When_PlansLoad() {
        pricingPage.open();

        percy.snapshot("Pricing.PlanTable", Map.of(
                "widths", List.of(375, 1280),
                "scope", "[data-testid='Pricing.PlanTable']",
                "percyCSS", "[data-testid='Pricing.PromoBadge'] { visibility: hidden !important; }"));
    }
}
```

- `PricingPage` is the page object from `references/playwright-snapshots.md` §5; `open()` returns once the plan
  table is visible. Percy captures the DOM **at call time**, so a half-loaded page uploads a half-loaded
  snapshot.
- One `Percy` per page, built in the class's own `@BeforeMethod`, where the page `BaseTest` opened already
  exists. Nothing to close: there is no Percy session per test.
- The clock is frozen before the page loads, so dates in the captured DOM are stable.
- **The test has no assertion, and says so** in `@Test(description = …)` — the TestNG form of the TS lane's
  `no-assertion` annotation (plan D50). The description reaches the TestNG report and Allure.

## 5. Snapshot options

`percy.snapshot(name, Map<String, Object> options)` takes the options by name; positional overloads exist —
`snapshot(name)`, `snapshot(name, widths)`, `snapshot(name, widths, minHeight)`, up to
`snapshot(name, widths, minHeight, enableJavaScript, percyCSS, scope)` — but a map reads better than a row
of `null`s.

| Key | Meaning |
|---|---|
| `widths` | Viewport widths Percy renders at, server-side. Overrides `.percy.yml` |
| `minHeight` | Minimum render height (default 1024) |
| `enableJavaScript` | Run JS in Percy's renderer. Off by default: the captured DOM renders statically |
| `percyCSS` | CSS injected **only in Percy's renderer**, before the diff — the stabilization lever |
| `scope` | A CSS selector; only that subtree is snapshotted — the element snapshot. Build it from a test id |
| `regions` | Ignore / consider regions built with `percy.createRegion(params)` — for a region a selector cannot isolate |

**Percy has no per-call pixel budget.** Hide the specific dynamic region with `percyCSS`
(`visibility: hidden`) and narrow the snapshot with `scope`; do not try to loosen the diff.

## 6. CI and the review gate

The nightly visual job runs `npx percy exec -- ./gradlew --no-daemon :e2e:visualTest` with `PERCY_TOKEN`
from the secret store. Percy renders server-side, so this job does **not** need the pinned image: the normal
UI job's runner, JDK 21 and `installPlaywrightBrowsers` step (`qa/cicd/java/skills/ci-pipelines`) are enough,
plus Node for `@percy/cli`.

1. The run uploads snapshots; Percy diffs them against the base branch's approved baseline.
2. Percy posts a status check on the commit: **changes detected** (needs review) or **no changes**.
3. A reviewer approves or rejects in Percy's UI. Approving updates the branch baseline.
4. On merge, the approved snapshots become the base branch's baseline for the next PR.

There is no diff image to upload: the diff lives in Percy, linked from the status check and the
`percy exec` log. A functional failure in a Percy class still gets `BaseTest`'s screenshot, trace and video.

## Anti-patterns

- **A `Playwright.create()`, browser or `@AfterMethod` teardown in a Percy class.** *Fix:* extend `BaseTest`.
- **`Thread.sleep` or `waitForTimeout` before `percy.snapshot`.** *Fix:* the page object's ready signal.
- **Loosening the diff to stop a flake.** *Fix:* `percyCSS` on the specific region; `scope` to the element.
- **Running the visual task without `percy exec` and expecting coverage.** Every snapshot is a no-op.
- **A Percy test without the `description`.** It reads as a forgotten assertion.
- **Committing baseline PNGs beside Percy.** *Fix:* Percy keeps the baselines; delete them.
- **Logging or committing `PERCY_TOKEN`.** It is a write credential.
- **A Maven `+` range or an unpinned `@percy/cli`.** *Fix:* the exact versions in §1.

## Rules

- Extend `BaseTest`; build `Percy` in the class's `@BeforeMethod`; reach the state through page objects.
- Stabilize on the page object's condition and the frozen clock; never a sleep.
- Run under `percy exec`; `PERCY_TOKEN` comes from the secret store only.
- Hide dynamic regions with `percyCSS`, narrow with `scope`, built from test ids.
- The test has no assertion and states it in `@Test(description = "No assertion: …")`; the Percy status
  check is the gate.
- `io.percy:percy-playwright-java:1.2.1` and `@percy/cli@1.32.11`, exact.

## Cross-references

- `references/playwright-snapshots.md` — the free sibling, and `PricingPage`.
- `references/applitools.md` — visual AI, match levels and a browser/device grid.
- `qa/java/skills/ui-test-author/playwright` — `BaseTest` and page objects.
- `qa/cicd/java/skills/ci-pipelines` — the schedule gate, the secret store, the UI job's runner setup.
- `qa-visual-regression-typescript` (`@percy/playwright`), `qa-visual-regression-dotnet` (`PercyIO.Playwright`).
