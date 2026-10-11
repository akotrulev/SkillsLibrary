# Lifecycle — Playwright for Java 1.63 with TestNG

`assets/BaseTest.java` is the one Playwright lifecycle in the Java lane. Every Java skill that drives a
browser — visual regression, accessibility, network mocking, responsive, language, cloud grids — extends it
and amends it through its hooks; none declares its own `Playwright.create()`. This file explains why it is
shaped the way it is and how to run it.

## 1. Why instance fields plus `parallel="classes"`

**Playwright Java is not thread-safe.** The threading guide says every method of `Playwright`, and of every
object it created (`Browser`, `BrowserContext`, `Page`, `Locator`), must be called on the thread that created
the `Playwright` instance; several instances, each on its own thread, are fine
(playwright.dev/java/docs/multithreading).

**TestNG `parallel="classes"` keeps a class on one thread.** testng.org: *"TestNG will run all the methods
in the same class in the same thread, but each class will be run in a separate thread."* (checked
2026-10-10). So a class's `@BeforeClass`, `@BeforeMethod`, `@Test`, `@AfterMethod` and `@AfterClass` all run
on the thread whose `@BeforeClass` created the `Playwright`, and TestNG makes one instance per class, so no
other thread ever sees its fields.

| Shape | What goes wrong |
|---|---|
| `static Playwright` / `static Browser` built in `@BeforeSuite` | `@BeforeSuite` runs once, on a different thread from the class workers, so every class touches Playwright off its creating thread. It is also static mutable state |
| `parallel="methods"` | Two methods of the same instance run on two threads: they overwrite each other's `page` and call Playwright from a thread that did not create it |
| `@DataProvider(parallel = true)` | Rows run on the data-provider thread pool (10 threads by default), with the same two failures. Data providers stay sequential; the class is the unit of parallelism |
| `ThreadLocal<Page>` per method | Works around `parallel="methods"` with hidden per-thread static state. Not used (plan D8) |

`parallel="instances"` is equally safe (*"all the methods in the same instance in the same thread"*) and is
the mode for a `@Factory` that builds several instances of one class.

**`thread-count` is the number of browsers running at once** — each class launches its own browser
process. Size it to the CI agent's memory. The cost of this shape is no method-level parallelism: a slow
class is one thread, so split a large class by feature.

## 2. What runs when

| Hook | `BaseTest` does |
|---|---|
| `@BeforeClass launchBrowser` | `Playwright.create()`, the test-id attribute, then `newBrowser(playwright)` — by default `chromium().launch(launchOptions())` headless unless `HEADED=1` |
| `@BeforeMethod openContext` | A new context from `contextOptions()` plus `BASE_URL` and the raw-video folder; tracing started; a new page |
| `@AfterMethod closeContext` | Failure evidence, then `context.close()`, then the video (§5) |
| `@AfterClass closeBrowser` | `playwright.close()`, which closes the browser |

- **Inheritance order is guaranteed.** TestNG runs `@Before…` methods from the highest superclass down and
  `@After…` methods in reverse. A test class's own `@BeforeMethod` (building page objects, seeding data)
  therefore sees an open page, and its own `@AfterMethod` (deleting seeded data) runs before `BaseTest`
  closes the context.
- **Every configuration method is `alwaysRun = true`.** Without it, a run filtered by group
  (`useTestNG { includeGroups("smoke") }`) skips the ungrouped `BaseTest` hooks and every test fails on a
  null `page`.
- Page objects are built in the test class (`LoginTest.createPages()`), never as fields of `BaseTest`; a base
  class that knows every page grows without bound.

## 3. The hooks

Override, never copy, the lifecycle:

```java
@Override
protected BrowserType.LaunchOptions launchOptions() {
    return new BrowserType.LaunchOptions().setArgs(List.of("--enable-features=WebMCP"));
}

@Override
protected Browser.NewContextOptions contextOptions() {
    return new Browser.NewContextOptions().setStorageStatePath(AuthSetup.USER_STATE);
}

@Override
protected Browser newBrowser(Playwright playwright) {
    return BrowserStackGrid.connect(playwright, GridTarget.EDGE_WINDOWS_11, getClass().getSimpleName());
}
```

| Hook | Called | Default | Override it for |
|---|---|---|---|
| `launchOptions()` | by the default `newBrowser` | empty options | a launch flag (WebMCP, a debugging port) |
| `contextOptions()` | in `@BeforeMethod`, once per test | empty options | storage state, viewport, device, locale, time zone, media |
| `newBrowser(playwright)` | in `@BeforeClass`, after the test-id attribute is set | `chromium().launch(launchOptions())`, headless unless `HEADED=1` | a browser the class does not launch itself — `chromium().connect(wsEndpoint)` to a cloud grid (`qa/java/skills/browser-cloud-setup`) |

`BaseTest` applies its own settings **after** calling the hook: headless from `HEADED` (in the default
`newBrowser`), `setBaseURL` from `BASE_URL` and the video folder. A subclass therefore cannot drop the base URL
or the failure evidence by forgetting `super`. An override of `newBrowser` replaces the launch, so
`launchOptions()` and `HEADED` no longer apply to that class; the browser it returns is still released by
`playwright.close()` in `@AfterClass`, which for a connected browser closes the connection and so ends the
remote session. Device and media emulation go in `contextOptions()` too — see
`emulation-and-mobile-web.md`. There is one base class: a role, a device, a launch flag or a grid target is an
override on the class that needs it, never a second base class.

## 4. Environment

| Variable | Read by | Effect |
|---|---|---|
| `BASE_URL` | `openContext` | `setBaseURL`, so `page.navigate("/login")` and `page.request().post("/api/…")` resolve. Missing → `IllegalStateException` naming the variable |
| `HEADED` | `launchBrowser` | `1` runs headed; anything else headless |
| `E2E_USER`, `E2E_PASSWORD` | `LoginTest`, `AuthSetup` | The test account |
| `PLAYWRIGHT_JAVA_SRC` | Playwright | Set to `src/test/java` by the `test` task, so traces show the test source |

`requiredEnv(name)` is the one way to read a required variable. The test-id attribute is set per
`Playwright` instance with `playwright.selectors().setTestIdAttribute(...)`, which is why it lives in
`@BeforeClass`.

## 5. Failure evidence and the hook order

| Evidence | Kept when | Path |
|---|---|---|
| Full-page screenshot | the test failed | `build/playwright-artifacts/<Class>.<method>.png` |
| Trace (screenshots, DOM snapshots, sources) | the test failed | `build/playwright-artifacts/<Class>.<method>.zip` |
| Video | the test failed | `build/playwright-artifacts/<Class>.<method>.webm` |

A passing test leaves nothing: `tracing().stop()` with no path discards the trace, and `video.delete()`
removes the raw recording from `build/playwright-videos/`. Each kept file is also attached to Allure.

**The order inside `closeContext` is fixed:**

1. Read `page.video()` and keep the reference — the page is gone after step 3.
2. On failure, the screenshot (needs the live page) and `tracing().stop(setPath)` (needs the context).
3. `context.close()`. The video is written only when the context closes.
4. On failure, `video.saveAs(path)`. **Java's `saveAs` throws until the page or context is closed**, unlike
   Node.
5. `video.delete()` always.

**allure-java 3.0 API:** `Allure.attachment(name, type, stream, AttachmentOptions.withFileExtension(ext))`.
The 2.x `Allure.addAttachment(...)` does not exist in 3.0. The trace is attached as
`application/vnd.allure.playwright-trace`.

**The one catch.** `keepScreenshot` catches `PlaywrightException` — a crashed or closed page cannot be
photographed — logs it with a message template and returns, so the trace and video are still kept. That is
the CLAUDE.md exception for an I/O helper: one named exception, logged, never blanket. It matters because
TestNG's default `configfailurepolicy` is `skip`: a failing `@AfterMethod` would skip every remaining test
in the class. There is no catch in a test, in a hook body, or around an assertion.

Screencasts, HAR, aria snapshots in traces and deliberate recordings belong to
`qa/java/skills/evidence-capture`, which builds on these defaults rather than adding a second hook.

## 6. Signed-in state

Sign in once per suite run and reuse the state in every signed-in class. The file is rewritten on every run,
so it never goes stale, and it lives under `build/`, so it is never committed.

```java
public class AuthSetup {
    public static final Path USER_STATE = Path.of("build", ".auth", "user.json");

    @BeforeSuite(alwaysRun = true)
    public void saveSignedInState() {
        try (Playwright playwright = Playwright.create()) {
            BrowserContext context = playwright.chromium().launch()
                    .newContext(new Browser.NewContextOptions().setBaseURL(BaseTest.requiredEnv("BASE_URL")));
            Page page = context.newPage();
            new LoginPage(page).signIn(new Credentials(BaseTest.requiredEnv("E2E_USER"), BaseTest.requiredEnv("E2E_PASSWORD")));
            assertThat(new HomePage(page).greeting()).isVisible();
            context.storageState(new BrowserContext.StorageStateOptions().setPath(USER_STATE));
        }
    }
}
```

- It sits in the `support` package beside `BaseTest` and is listed in `testng.xml` as a `<class>` next to
  the `<packages>` entry.
- Its `Playwright` is created and closed inside the one method, so the thread rule holds even though
  `@BeforeSuite` runs on its own thread.
- The assertion before `storageState` waits for the sign-in to finish; saving straight after the click
  saves a signed-out state.
- A second role is a second state file written by the same method, chosen in that class's
  `contextOptions()`. A signed-out class does not override `contextOptions()`.

## 7. API-seeded data

A record a test needs is created through the API in the test class's own `@BeforeMethod` and deleted in its
`@AfterMethod`, which run inside the `BaseTest` hooks (§2). `page.request()` shares the context's base URL
and cookies.

```java
private String orderLocation;

@BeforeMethod(alwaysRun = true)
public void seedOrder() {
    APIResponse created = page.request().post("/api/orders",
            RequestOptions.create().setData(Map.of("sku", "SKU-" + UUID.randomUUID(), "qty", 1)));
    assertThat(created.status()).as(created.text()).isEqualTo(201);
    orderLocation = created.headers().get("location");
}

@AfterMethod(alwaysRun = true)
public void deleteOrder() {
    APIResponse deleted = page.request().delete(orderLocation);
    assertThat(deleted.status()).as(deleted.text()).isEqualTo(204);
}
```

The status is asserted exactly with AssertJ, the body as the description. Never
`assertThat(response).isOK()`, which accepts any 2xx and prints nothing useful.

## 8. Commands

| Task | Command |
|---|---|
| Install the browser on CI | `./gradlew installPlaywrightBrowsers` (`install --with-deps chromium`; `--with-deps` installs OS packages, so it needs root or sudo on Linux) |
| Install locally | `./gradlew playwright --args="install chromium"` |
| Run headed | `HEADED=1 ./gradlew test` |
| Debug with the Inspector | `PWDEBUG=1 ./gradlew test` — headed, no timeouts, the Playwright Inspector to step through |
| Record a flow | `./gradlew playwright --args="codegen --target java --test-id-attribute data-testid -o build/codegen/Recorded.java https://app.example.test/login"` |
| Open a trace | `./gradlew playwright --args="show-trace build/playwright-artifacts/LoginTest.Should_GreetUser_When_CredentialsAreValid.zip"` |

- **The CLI is `com.microsoft.playwright.CLI`,** run by the two `JavaExec` tasks in `assets/build.gradle.kts`.
  The CI recipes in `qa/cicd/java/skills/ci-pipelines` call `installPlaywrightBrowsers`.
- **Browsers are pinned per Playwright version.** In a container, use
  `mcr.microsoft.com/playwright/java:v1.63.0-noble`; its tag always equals the package version.
- **Codegen has no TestNG target.** `--target` takes `java` (a class with `main`) or `java-junit`. Treat the
  output as a draft: move the locators into a page object on the ladder, write the test as a TestNG method
  with a `Should_X_When_Y` name, and never commit the recording. The recorder's **Assert snapshot** button
  emits `matchesAriaSnapshot`.
- **Traces also open at trace.playwright.dev**, which loads the zip in the browser without uploading it. The
  `trace open | errors | actions | …` analysis commands an agent reads a failure with are in
  `qa/java/skills/evidence-capture` (§ Reading a failure).
