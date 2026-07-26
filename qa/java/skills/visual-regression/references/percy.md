# Visual Regression — Percy (Java / TestNG)

The Java port of the canonical `qa-visual-regression-typescript`. Same hosted model, same review
workflow, same `percy exec` agent — re-expressed in `io.percy:percy-playwright-java` +
Playwright-Java + TestNG idioms. Percy (by BrowserStack) **uploads a DOM snapshot** of the page and
**renders + diffs it server-side**; baselines live in Percy's cloud, keyed by git branch, and are
reviewed/approved in a web UI. The build is gated on that review, not on a local artifact.

This is an **assertion layer** on top of the page objects and specs
`qa-ui-test-writer-playwright-java` already authored. You do not write new page objects here — you add
a `percy.snapshot(name)` call and wrap your build's test command in `percy exec`.

## Why graduate from built-in snapshots to Percy

The biggest pain in the free `playwright-snapshots` skill is the **cross-platform rendering
problem**: a baseline rendered on a dev Mac (`...-darwin.png`) never matches Linux CI, so you must
generate baselines *inside the CI container* (and Java, like .NET, has no `--update-snapshots` — you
delete-and-rerun). Percy makes that problem **disappear** by rendering server-side:

| | Built-in snapshots | **Percy (this skill)** |
|---|---|---|
| What leaves the test | Nothing — a PNG is diffed locally | A **DOM snapshot** is uploaded |
| Where rendering happens | Your machine / CI container | **Percy's servers**, consistently |
| Where baselines live | Committed `*-snapshots/*.png` in your repo | **Percy cloud**, keyed by git branch |
| `-{platform}` baselines | Yes — the whole headache | **None** |
| Baseline-in-CI-container rule | Mandatory | **Not needed** |
| Updating a baseline | delete-and-rerun (no `--update-snapshots` in Java) | **Approve in the review UI** |
| Diff budget | `setMaxDiffPixelRatio` etc. per assertion | No per-call pixel knob — **`percyCSS` + region ignores** |
| Gate | Local pass/fail + `-diff.png` artifact | **Status check** linking the visual review |
| Cost | Free | Paid (per snapshot) |

State this contrast plainly: with Percy there are **no in-repo baselines, no `-{platform}` naming, no
in-CI-container baseline generation, and no delete-and-rerun** — baselines are managed in Percy and
auto-established from the **base branch**.

## Setup

The Percy CLI (the local agent) is a Node tool — install it even in a JVM repo — plus the Maven/Gradle
binding:

```bash
npm install --save-dev @percy/cli      # the agent that renders + uploads
```

```kotlin
// build.gradle.kts
dependencies {
    testImplementation("com.microsoft.playwright:playwright:1.50.0")
    testImplementation("io.percy:percy-playwright-java:1.2.+")
    testImplementation("org.testng:testng:7.+")
}
```

```xml
<!-- or Maven -->
<dependency>
  <groupId>io.percy</groupId>
  <artifactId>percy-playwright-java</artifactId>
  <version>1.2.1</version>
  <scope>test</scope>
</dependency>
```

`PERCY_TOKEN` is the **only secret** — a per-project write token. In CI it comes from the secret store
(see the ci-pipelines cross-link), never committed. Locally `export PERCY_TOKEN=<token>`.

## How you run the suite — `percy exec`

You do **not** call Percy's API to start a build. Wrap your existing test command in `percy exec`,
which starts the local Percy agent (a proxy that receives DOM snapshots, runs asset discovery, and
uploads to Percy), runs the suite, then finalizes the build:

```bash
PERCY_TOKEN=<token> npx percy exec -- ./gradlew test
# or: PERCY_TOKEN=<token> npx percy exec -- mvn test
```

**Percy no-ops gracefully when the agent isn't running.** If you run `gradle test` *without*
`percy exec` (or `PERCY_TOKEN` is absent), `percy.snapshot()` detects Percy is not running, logs a
warning, **skips the snapshot, and the test still passes**. A developer without the token runs the
functional suite untouched — the visual assertions simply don't fire. That's why `percy.snapshot` is
safe to leave in shared specs.

## `.percy.yml` — project-wide snapshot config

Set rendering width(s), min height, global CSS, and discovery once, in repo (identical schema across
all three stacks — it's the agent's config, not the language binding's):

```yaml
# .percy.yml
version: 2
snapshot:
  widths:
    - 375    # mobile
    - 1280   # desktop
  min-height: 1024
  percy-css: |
    .intercom-launcher, [data-testid="live-clock"] { visibility: hidden !important; }
  enable-javascript: false
discovery:
  allowed-hostnames:
    - cdn.flexinvest.test
  network-idle-timeout: 250
```

`percy exec --config ./.percy.yml -- ./gradlew test` if the file isn't at the default location.

## Core pattern — `percy.snapshot` on a page-object-driven flow

The page object exposes intent; the test stabilizes **application** state on a condition, then calls
`percy.snapshot`. No selectors in the test, no fixed waits. Construct one `Percy` per `Page`.

```java
// pages/DashboardPage.java
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Locator;
import com.microsoft.playwright.options.AriaRole;
import com.microsoft.playwright.options.WaitForSelectorState;

public final class DashboardPage {
    private final Page page;
    public final Locator revenueCard;

    public DashboardPage(Page page) {
        this.page = page;
        this.revenueCard = page.getByTestId("revenue-card");
    }

    public void goto_() {
        page.navigate("/dashboard");
    }

    /** Returns once the card's data has rendered — a condition, never a fixed wait. */
    public void waitUntilLoaded() {
        revenueCard.getByRole(AriaRole.STATUS)
            .waitFor(new Locator.WaitForOptions().setState(WaitForSelectorState.HIDDEN));
    }
}
```

```java
// DashboardTest.java
import com.microsoft.playwright.*;
import io.percy.playwright.Percy;
import org.testng.annotations.*;

public class DashboardTest {
    private Playwright playwright;
    private Browser browser;
    private Page page;
    private Percy percy;

    @BeforeMethod
    public void setUp() {
        playwright = Playwright.create();
        browser = playwright.chromium().launch();
        page = browser.newContext(new Browser.NewContextOptions()
            .setBaseURL("http://localhost:3000")).newPage();
        percy = new Percy(page);          // one Percy per page
    }

    @AfterMethod
    public void tearDown() { browser.close(); playwright.close(); }

    @Test
    public void Should_Capture_DashboardPercySnapshot_When_Loaded() {
        DashboardPage dashboard = new DashboardPage(page);
        dashboard.goto_();
        dashboard.waitUntilLoaded();      // stabilize on a condition first…

        percy.snapshot("Dashboard — revenue card");   // …then snapshot (DOM uploaded, rendered server-side)
    }
}
```

`percy.snapshot` does not assert pass/fail in the test — it uploads a snapshot. Percy decides pass/fail
later, server-side, against the branch baseline, and surfaces it as an **unreviewed status check**, not
a thrown assertion. Stabilize before snapshotting: Percy captures the DOM *at call time*, so a
half-loaded page uploads a half-loaded snapshot.

## Snapshot options — the positional `snapshot(...)` signature

The Java binding uses a **positional** signature (no options Map for the web `snapshot`):
`percy.snapshot(name, widths, minHeight, enableJavaScript, percyCSS, scope)`. Overloads let you pass a
prefix and omit the rest:

```java
import java.util.Arrays;
import java.util.List;

List<Integer> widths = Arrays.asList(375, 768, 1280);   // override .percy.yml per snapshot
Integer minHeight = 1024;
boolean enableJavaScript = false;
String percyCSS = "[data-testid=\"promo-banner\"] { visibility: hidden !important; } " +
                  "[data-testid=\"last-seen\"] { visibility: hidden !important; }";
String scope = "[data-testid=\"pricing-table\"]";        // snapshot only this element's subtree

percy.snapshot("Pricing page", widths, minHeight, enableJavaScript, percyCSS, scope);

// Shorter overloads — pass only what you need:
percy.snapshot("Pricing page (widths only)", widths);
percy.snapshot("Pricing page (widths + minHeight)", widths, minHeight);
```

The parameters, precisely:

- **`widths`** — viewport widths Percy renders at, server-side. Overrides `.percy.yml`.
- **`minHeight`** — minimum render height (default 1024).
- **`enableJavaScript`** — run JS in Percy's renderer. Off by default (Percy renders the captured DOM
  statically). Turn on only when the page needs client-side JS to paint correctly.
- **`percyCSS`** — CSS injected **only in Percy's renderer**, applied right before the diff. Your
  primary stabilization lever — there is **no per-call pixel-ratio knob**. Hide dynamic regions with
  `visibility: hidden`.
- **`scope`** — CSS selector; Percy snapshots only that element's subtree (the analogue of an element
  screenshot — less noise than full page).

### Hiding dynamic regions is `percyCSS`, not a pixel budget

The built-in skill tames flakiness with `setMaxDiffPixelRatio` / `setMask`. **Percy has neither.** The
lever is `percyCSS` (per-snapshot or global in `.percy.yml`). Neutralize the *specific* dynamic region;
don't loosen the whole diff:

```java
percy.snapshot("Profile header", null, null, false,
    "img.gravatar { visibility: hidden !important; } " +
    "[data-testid=\"last-seen\"] { visibility: hidden !important; }", null);
```

## CI integration + the review gate

In CI, `percy exec` wraps `./gradlew test` (or `mvn test`) exactly as locally; `PERCY_TOKEN` comes from
the secret store. After the build finalizes, Percy posts a **GitHub/GitLab status check** linking the
visual review. The build is **green only once the diffs are approved** in Percy's UI (or auto-approved).
Baselines auto-establish from the **base branch**, so a PR diffs against `main`'s last approved
snapshots.

```yaml
# inside your test job — see qa-ci-pipelines-java for the full pipeline
- name: Visual tests (Percy)
  env:
    PERCY_TOKEN: ${{ secrets.PERCY_TOKEN }}   # from the secret store; never inline
  run: npx percy exec -- ./gradlew test
```

Contrast with built-in snapshots: there is **no `-diff.png` artifact to upload** — the diff lives in
Percy's UI. Link the Percy build URL into Allure so reviewers jump straight to it (cross-link
`qa-test-reports-java`):

```java
import io.qameta.allure.Allure;

@AfterSuite
public void linkPercyBuild() {
    // percy exec exports the build URL in recent CLI versions.
    String url = System.getenv("PERCY_BUILD_URL");
    if (url != null && !url.isEmpty()) {
        Allure.link("Percy visual review", url);
    }
}
```

The review-UI workflow, concretely:
1. PR runs `percy exec -- ./gradlew test`; Percy renders + diffs against the base-branch baseline.
2. Percy posts a status check: **changes detected** (needs review) or **no changes** (auto-green).
3. A reviewer approves/rejects in Percy's UI. Approving updates the branch baseline.
4. On merge, the approved snapshots become `main`'s baseline for the next PR.

## Anti-patterns

- **Committing `*-snapshots/` PNGs alongside Percy.** Percy keeps baselines in the cloud — in-repo
  PNGs are the built-in-snapshots model and don't apply. *Fix:* delete them; rely on the Percy
  baseline.
- **`page.waitForTimeout(500)` before `percy.snapshot`.** Percy captures the DOM at call time; a sleep
  is flaky and slow. *Fix:* wait on a condition (`document.fonts.ready` via `page.evaluate`, spinner
  hidden, `Locator.waitFor`), then snapshot.
- **Trying to "loosen the diff" to stop flakes.** Percy has no per-call pixel budget. *Fix:* hide the
  specific dynamic region with `percyCSS` (`visibility: hidden`).
- **Running `gradle test` without `percy exec` and expecting visual coverage.** `percy.snapshot`
  silently no-ops when the agent isn't running. *Fix:* run via `percy exec -- ./gradlew test` with
  `PERCY_TOKEN` set; reserve bare `gradle test` for functional-only runs.
- **Hardcoding / logging `PERCY_TOKEN`.** It's a write credential. *Fix:* env only, from the CI secret
  store, read lazily, never echoed.
- **Treating a Percy "diff" as a thrown test failure.** It's an unreviewed **status check**, not an
  in-test assertion. *Fix:* gate the merge on the Percy status check; review in the UI.
- **Full-page snapshots of a dynamic page.** Noisy reviews. *Fix:* `scope` to the element under test;
  `percyCSS` away the rotating bits.

## Examples

**End-to-end: a pricing-table visual gate reviewed in Percy.**

```java
import com.microsoft.playwright.*;
import io.percy.playwright.Percy;
import org.testng.annotations.*;
import java.util.Arrays;

public class PricingTest {
    private Playwright playwright;
    private Browser browser;
    private Page page;
    private Percy percy;

    @BeforeMethod
    public void setUp() {
        playwright = Playwright.create();
        browser = playwright.chromium().launch();
        page = browser.newContext(new Browser.NewContextOptions()
            .setBaseURL("http://localhost:3000")).newPage();
        percy = new Percy(page);
    }

    @AfterMethod
    public void tearDown() { browser.close(); playwright.close(); }

    @Test
    public void Should_Capture_PricingTable_When_PlansLoaded() {
        PricingPage pricing = new PricingPage(page);
        pricing.goto_();
        pricing.waitUntilPlansRendered();            // condition, not sleep
        page.evaluate("document.fonts.ready");        // fonts settled before DOM capture

        percy.snapshot(
            "Pricing — plan table",
            Arrays.asList(375, 1280),                 // mobile + desktop, rendered server-side
            null,                                     // minHeight default
            false,                                    // enableJavaScript
            "[data-testid=\"promo-banner\"] { visibility: hidden !important; }", // rotates daily
            "[data-testid=\"pricing-table\"]");       // element subtree, not full page
    }
}
```

Lifecycle for this test:
1. Dev makes an intended CSS change to the pricing table.
2. CI runs `percy exec -- ./gradlew test`; Percy renders at 375px + 1280px and diffs vs `main`.
3. Percy's status check flags the change; the dev reviews + approves the diff in Percy's UI.
4. On merge, the approved render becomes `main`'s baseline — the next PR diffs against it.

## Rules (hard constraints)

- Visual regression is an assertion layer on existing page objects/specs — add `percy.snapshot`, don't
  author new page objects here. Page objects expose intent + locators; no selectors in tests.
- Stabilize **application** state on a condition before `percy.snapshot`; never `waitForTimeout` —
  Percy captures the DOM at call time.
- Run the suite under `percy exec -- <mvn|gradle> test`; `percy.snapshot` no-ops gracefully without the
  agent.
- `PERCY_TOKEN` is the **only** secret: env-only, from the CI secret store, read lazily, never logged
  or committed.
- No in-repo `*-snapshots/` baselines, no `-{platform}` naming, no delete-and-rerun — baselines live in
  Percy and are managed via the **review UI**, auto-established from the base branch.
- Stabilize/neutralize dynamic regions with **`percyCSS`** (`visibility: hidden`) and `scope`, not a
  diff budget — Percy has no per-call pixel-ratio knob.
- Prefer `scope`d element snapshots over full-page; render responsive widths via `widths` /
  `.percy.yml`, not extra tests.
- The gate is the **Percy status check** (review/approve), not a thrown assertion or a local artifact.

## Cross-references

- `qa-visual-regression-typescript` — the **canonical** skill this ports (`@percy/playwright`
  `percySnapshot`, `.percy.yml`, `percy exec`).
- `qa-visual-regression-dotnet` — the .NET / NUnit sibling (`PercyIO.Playwright`,
  `Percy.Snapshot(page, name, options)`).
- `references/playwright-snapshots.md` — the **free** sibling: in-repo baselines you
  diff yourself, with the CI-container discipline Percy removes. Start here; graduate to Percy.
- `references/applitools.md` (`applitools`, next) — the visual-AI sibling: AI diff tolerance + a
  cross-browser rendering grid.
- `qa-ui-test-writer-playwright-java` — the page objects/specs `percy.snapshot` is called inside.
- `qa-ci-pipelines-java` — where `PERCY_TOKEN` is sourced and `percy exec` wraps the
  Gradle/Maven test step.
- `qa-test-reports-java` — link the Percy build URL into the report.
