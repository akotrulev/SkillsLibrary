# Email HTML snapshots — ApprovalTests on mail captured by Mailpit

Read this after `references/mailpit.md` when the **rendered email itself** is under test: a template change, a
layout regression, copy that legal signed off, a link that must stay in the footer. The targeted assertions in
`mailpit.md` prove the message arrived, went to the right person, and carries a working link or code; a snapshot
proves the whole body did not change by accident. Keep both — the snapshot never replaces the recipient, link and
OTP assertions.

## When a snapshot fits

| Question | Assertion |
|---|---|
| Did the welcome email arrive, to this address, from this sender? | Targeted (`mailpit.md`) |
| Does the activation link work? | Extract it and call it (`mailpit.md`) |
| Did the template's layout, copy, or footer change? | **Snapshot** |
| Does every locale's template render the same structure? | **Snapshot** per locale (a `@DataProvider` row each) |

## Dependencies

| Artifact | Version | Why |
|---|---|---|
| `com.approvaltests:approvaltests` | **31.0.0** (Java 8+, works with TestNG and JUnit 5) | The snapshot engine: writes `*.received.*`, compares with `*.approved.*` |
| `org.jsoup:jsoup` | **1.24.1** | Pretty-prints the HTML so the diff shows the changed element, not one 40 kB line |

Verified on Maven Central, 2026-11. Neither is managed by the Spring Boot BOM, so both are pinned in the build.

```kotlin
dependencies {
    testImplementation("com.approvaltests:approvaltests:31.0.0")
    testImplementation("org.jsoup:jsoup:1.24.1")
}
```

## One normalizer for every email snapshot

```java
package com.flexinvest.support.email;

import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;

public final class EmailHtml {

    private static final int INDENT = 2;

    private EmailHtml() {}

    public static String pretty(String html) {
        Document document = Jsoup.parse(html);
        document.outputSettings().prettyPrint(true).indentAmount(INDENT);
        return document.outerHtml();
    }
}
```

Bump jsoup alone, re-run, and review the snapshot diffs before accepting: a new jsoup version can change the
pretty-printer's output without any template having changed.

## Scrubbing what changes per send

An email is full of per-send values. Scrub each one, or the snapshot fails on every run:

| Value | Scrub |
|---|---|
| The unique per-test recipient (`signup-<uuid>@test.local`) | A `RegExScrubber` over `Pattern.quote(recipient)` → `[recipient]` |
| Activation / reset / magic-link tokens in `href`s | A regex replacing the parameter value → `[token]` |
| One-time codes | The same → `[otp]` |
| Dates and times rendered in the body | `DateScrubber.getScrubberFor("<an example in the template's format>")` |
| Tracking-pixel and click-tracking URLs | Replace the query string → `[tracking]` |
| The SUT's host and port (`http://localhost:51234`) | A `RegExScrubber` over `Pattern.quote(baseUrl)` → `[base-url]` |

Scrub the **value**, keep the **shape**: `href="[base-url]/activate?token=[token]"` still proves the link points at
the activation route with a token parameter.

```java
package com.flexinvest.support.email;

import java.util.regex.Pattern;
import org.approvaltests.core.Options;
import org.approvaltests.core.Scrubber;
import org.approvaltests.scrubbers.DateScrubber;
import org.approvaltests.scrubbers.RegExScrubber;
import org.approvaltests.scrubbers.Scrubbers;

public final class EmailScrubbers {

    private static final Scrubber TOKENS = new RegExScrubber("(?<=[?&](token|code)=)[^&\"'\\s<]+", "[token]");
    private static final Scrubber ONE_TIME_CODES = new RegExScrubber("\\b\\d{6}\\b", "[otp]");
    private static final Scrubber TRACKING = new RegExScrubber("(?<=/t/(open|click)\\?)[^\"'\\s<]+", "[tracking]");
    private static final Scrubber SENT_DATES = DateScrubber.getScrubberFor("2024-12-17");

    private EmailScrubbers() {}

    public static Options forMessageTo(String recipient, String baseUrl) {
        return new Options().withScrubber(Scrubbers.scrubAll(
            new RegExScrubber(Pattern.quote(recipient), "[recipient]"),
            new RegExScrubber(Pattern.quote(baseUrl), "[base-url]"),
            TOKENS,
            ONE_TIME_CODES,
            TRACKING,
            SENT_DATES));
    }
}
```

- Scrubbers run in the order given: the recipient and base URL first, so the narrower patterns never cut into them.
- `DateScrubber.getScrubberFor` takes an example in the template's format and throws when it does not know the
  format; a format outside its table (`14 November 2026`) gets a `RegExScrubber` of its own.
- **Prefer fixing the seam to scrubbing.** A date the SUT takes from an injected `Clock` the test pins, or a token
  from a stubbed generator, is already stable; scrubbing is for what the test cannot control.

## The test

```java
public class WelcomeEmailSnapshotIT extends IntegrationTestBase {

    private final MailpitClient mail = new MailpitClient(MailpitSupport.apiBaseUrl());

    @Autowired private TestRestTemplate http;

    @Test
    public void Should_RenderTheWelcomeEmail_When_AUserSignsUp() throws Exception {
        String email = "signup-" + UUID.randomUUID() + "@test.local";
        ResponseEntity<Void> response = http.postForEntity("/auth/signup",
            new SignUpRequestBuilder().withEmail(email).build(), Void.class);
        assertEquals(response.getStatusCode(), HttpStatus.CREATED);

        var summary = mail.waitFor(email, "Welcome", Duration.ofSeconds(15));
        var message = mail.get(summary.id());

        Approvals.verifyHtml(EmailHtml.pretty(message.html()), EmailScrubbers.forMessageTo(email, http.getRootUri()));
    }
}
```

- Snapshot `message.html()` (the `HTML` field of `GET /api/v1/message/{id}`) — the body the SUT produced. Add a
  second test on `message.text()` with `Approvals.verify(message.text(), options)` when the plain-text part matters.
- The file lands beside the test class as
  `WelcomeEmailSnapshotIT.Should_RenderTheWelcomeEmail_When_AUserSignsUp.approved.html` — open it in a browser to
  review the rendering, read the diff in the pull request to review the change.
- Per-locale or per-variant runs: a `@DataProvider` row each, and `options.forFile().withAdditionalInformation(locale)`
  — the value joins the file name, so each row has its own approved file.

## Approving, source control and CI

- **A missing or different `.approved.html` fails** the test and writes the `.received.html` beside it. The person
  who changed the template reviews the received file (the diff tool the default reporter opens, or a browser) and
  approves it by renaming it to `.approved.html`.
- `.gitignore` `*.received.*`; commit every `*.approved.*`. ApprovalTests ignores line-ending differences when it
  compares, but `.gitattributes` `*.approved.html text eol=lf` keeps the pull-request diff clean.
- **Never approve automatically** — no `AutoApproveReporter`, no script copying received over approved in CI. A
  person accepts a changed email after looking at it.
- On CI, set `APPROVAL_TESTS_USE_REPORTER=org.approvaltests.reporters.QuietReporter`, so a failure reports without
  trying to open a diff tool, and upload `**/*.received.*` as an artifact so the reviewer sees the rendered change
  (`qa/cicd/java/skills/ci-pipelines`).

## Anti-patterns

- **Snapshotting the raw MIME source.** Boundaries, `Message-ID` and encodings change per send; snapshot the decoded
  HTML and text parts.
- **Scrubbing so much that nothing is left.** If every line is scrubbed, the snapshot proves only that an email
  exists; scrub values, not elements.
- **A snapshot instead of the link check.** A scrubbed link is a shape, not a working link — keep the extract-and-
  call test from `mailpit.md`.
- **Snapshotting the unformatted HTML.** One long line diffs as "everything changed"; always go through
  `EmailHtml.pretty`.
