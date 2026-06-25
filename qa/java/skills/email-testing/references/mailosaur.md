# QA — Email & SMS Testing with Mailosaur (Java)

Scaffolds a thin, intent-revealing wrapper over the official `com.mailosaur:mailosaur-java` SDK plus TestNG helpers that **await** a specific message in a per-test `{uuid}@{serverId}.mailosaur.net` inbox, extract HTML / text body / links / OTP codes, download attachments, and verify SMS. Mailosaur is a **hosted** service: the SUT sends real email through its real provider to a Mailosaur inbox address, and `messages().get(...)` blocks until the message arrives or the timeout fires — that built-in wait is the sanctioned wait, so there is **no `Thread.sleep`** poll loop anywhere in this skill.

## When to use

- Signup / password-reset / magic-link / OTP / receipt flows that need an email assertion against a **real delivery path** (real SMTP/provider → real inbox), not just an SMTP sink
- Selenium / Playwright-Java E2E tests that click an emailed link or type an emailed OTP
- Integration tests asserting `From`, `subject` templates, HTML link targets, attachment shape
- **SMS / phone** one-time-passcode flows (same SDK, an SMS-enabled server)
- Teams that want zero local infra in CI — no container, just an API key + server ID secret

## When NOT to use

- Self-hosted SMTP sink, no cloud account, fully offline CI → `qa/java/skills/email-testing`
- Polling a real Gmail / Outlook mailbox over IMAP → `qa/java/skills/email-testing`
- SendGrid sandbox-mode (mail-send API, no delivery) → `qa/java/skills/email-testing`
- TS or .NET stacks → `qa/{typescript,dotnet}/skills/email-testing`
- Production deliverability / DKIM / SPF auditing — Mailosaur captures, it is not a relay verifier

## Inputs needed

Ask at most 2 questions; infer the rest from the test sources and existing support classes.

1. Scenario: signup welcome / OTP / password reset / magic link / SMS code / arbitrary subject match?
2. Where do the `MAILOSAUR_API_KEY` and `MAILOSAUR_SERVER_ID` come from in this environment (CI secret store, env)? They are **secrets** — never commit them.

## Mailosaur SDK surface (cheat-sheet)

| Call | Purpose |
|---|---|
| `new MailosaurClient(apiKey)` | Construct the client (inject the key; never hardcode) |
| `client.messages().get(params, criteria)` | **Await** the first message matching `criteria` — blocks until arrival or `params` timeout (ms, default 10 000), then throws. This is the wait. |
| `client.messages().list(params)` | Page recent messages (rarely needed — prefer `get`) |
| `client.messages().deleteAll(serverId)` | Empty the whole server inbox (use sparingly — see isolation rules) |
| `client.files().getAttachment(attachmentId)` | Download an attachment as `byte[]` |
| `new MessageSearchParams().withServer(id).withTimeout(ms)` | Server target + await budget |
| `new SearchCriteria().withSentTo(..).withSubject(..).withBody(..).withSentFrom(..)` | Match filters |
| `message.html().links()` | each `link.text()` / `link.href()` — Mailosaur-extracted hyperlinks |
| `message.html().codes()` / `message.text().codes()` | each `code.value()` — auto-detected OTP / verification codes |
| `message.html().body()` / `message.text().body()` | Raw bodies (extract structure; don't substring the whole thing) |
| `message.attachments()` | each `att.id()` / `att.fileName()` / `att.contentType()` / `att.length()` |

**Inbox-address pattern:** any address `{anything}@{serverId}.mailosaur.net` routes to your server. Per test, generate `{UUID.randomUUID()}@{serverId}.mailosaur.net` so every test owns a unique recipient and needs no shared-inbox cleanup.

## Templates

### Gradle additions

```kotlin
dependencies {
    testImplementation("com.mailosaur:mailosaur-java:7.+")
    testImplementation("org.assertj:assertj-core:3.26.3")
}
```

### Config — `support/email/MailosaurConfig.java`

Secrets come from the environment, validated once. Never inline the key or server ID.

```java
package com.flexinvest.support.email;

import java.time.Duration;
import java.util.UUID;

public final class MailosaurConfig {

    private final String apiKey;
    private final String serverId;
    private final Duration timeout;

    private MailosaurConfig(String apiKey, String serverId, Duration timeout) {
        this.apiKey = apiKey;
        this.serverId = serverId;
        this.timeout = timeout;
    }

    public static MailosaurConfig fromEnvironment() {
        long timeoutMs = System.getenv("MAILOSAUR_TIMEOUT_MS") != null
            ? Long.parseLong(System.getenv("MAILOSAUR_TIMEOUT_MS")) : 20_000L;
        return new MailosaurConfig(
            required("MAILOSAUR_API_KEY"),
            required("MAILOSAUR_SERVER_ID"),
            Duration.ofMillis(timeoutMs));
    }

    private static String required(String name) {
        String v = System.getenv(name);
        if (v == null || v.isBlank()) {
            throw new IllegalStateException("Missing required env var " + name + " (Mailosaur secret).");
        }
        return v;
    }

    public String apiKey()    { return apiKey; }
    public String serverId()  { return serverId; }
    public Duration timeout() { return timeout; }

    /** Unique recipient per test → independent tests, no shared-inbox races. */
    public String newRecipient(String prefix) {
        return prefix + "-" + UUID.randomUUID() + "@" + serverId + ".mailosaur.net";
    }
}
```

### Intent-revealing wrapper — `support/email/Mailbox.java`

Tests never call `messages().get` directly. They call `awaitSignupEmail`, `extractVerificationLink`, `extractOtp`. The SDK's blocking `get` is the only wait.

```java
package com.flexinvest.support.email;

import com.mailosaur.MailosaurClient;
import com.mailosaur.models.Message;
import com.mailosaur.models.MessageSearchParams;
import com.mailosaur.models.SearchCriteria;

import java.time.Duration;

public final class Mailbox {

    private final MailosaurClient client;
    private final String serverId;
    private final Duration timeout;

    public Mailbox(MailosaurConfig config) {
        this.client = new MailosaurClient(config.apiKey());
        this.serverId = config.serverId();
        this.timeout = config.timeout();
    }

    /** Await an email by recipient (+ optional subject). Blocks until arrival or timeout. */
    public Message awaitEmail(String sentTo, String subject, Duration timeoutOverride) throws Exception {
        MessageSearchParams params = new MessageSearchParams()
            .withServer(serverId)
            .withTimeout((int) (timeoutOverride != null ? timeoutOverride : timeout).toMillis());
        SearchCriteria criteria = new SearchCriteria().withSentTo(sentTo);
        if (subject != null) criteria.withSubject(subject);
        return client.messages().get(params, criteria);
    }

    public Message awaitSignupEmail(String sentTo) throws Exception {
        return awaitEmail(sentTo, "Welcome", null);
    }

    /** Await an SMS to a Mailosaur phone number (SMS-enabled server). Same primitive. */
    public Message awaitSms(String sentTo, Duration timeoutOverride) throws Exception {
        MessageSearchParams params = new MessageSearchParams()
            .withServer(serverId)
            .withTimeout((int) (timeoutOverride != null ? timeoutOverride : timeout).toMillis());
        return client.messages().get(params, new SearchCriteria().withSentTo(sentTo));
    }

    public byte[] downloadAttachment(String attachmentId) throws Exception {
        return client.files().getAttachment(attachmentId);
    }

    /** Hard reset of the whole server inbox. Prefer unique recipients over this. */
    public void emptyServerInbox() throws Exception {
        client.messages().deleteAll(serverId);
    }
}
```

### Extractors — `support/email/EmailExtractors.java`

Prefer Mailosaur's structured `links()` / `codes()` over hand-rolled regex.

```java
package com.flexinvest.support.email;

import com.mailosaur.models.Link;
import com.mailosaur.models.Message;

import java.net.URI;

public final class EmailExtractors {

    private EmailExtractors() {}

    public static String extractOtp(Message message) {
        if (message.html() != null && message.html().codes() != null && !message.html().codes().isEmpty()) {
            return message.html().codes().get(0).value();
        }
        if (message.text() != null && message.text().codes() != null && !message.text().codes().isEmpty()) {
            return message.text().codes().get(0).value();
        }
        throw new AssertionError("No verification code found in '" + message.subject() + "'.");
    }

    public static URI extractLink(Message message, String mustContain) {
        if (message.html() != null && message.html().links() != null) {
            for (Link link : message.html().links()) {
                if (link.href() != null && link.href().toLowerCase().contains(mustContain.toLowerCase())) {
                    return URI.create(link.href());
                }
            }
        }
        throw new AssertionError("No link containing '" + mustContain + "' in '" + message.subject() + "'.");
    }
}
```

### TestNG base — `support/MailosaurTestBase.java`

```java
package com.flexinvest.support;

import com.flexinvest.support.email.Mailbox;
import com.flexinvest.support.email.MailosaurConfig;
import org.testng.annotations.BeforeClass;

public abstract class MailosaurTestBase {

    protected MailosaurConfig mailConfig;
    protected Mailbox mail;

    @BeforeClass
    public void initMailosaur() {
        mailConfig = MailosaurConfig.fromEnvironment();
        mail = new Mailbox(mailConfig);
    }
}
```

### TestNG signup test

```java
public class SignupEmailIT extends MailosaurTestBase {

    @Autowired private TestRestTemplate http;

    @Test
    public void should_send_welcome_email_with_activation_link_on_signup() throws Exception {
        String email = mailConfig.newRecipient("signup");

        ResponseEntity<Void> response = http.postForEntity("/auth/signup",
            new SignupRequest(email, "Str0ng!Passw0rd"), Void.class);
        assertEquals(response.getStatusCode(), HttpStatus.CREATED);

        Message message = mail.awaitSignupEmail(email);
        URI activation = EmailExtractors.extractLink(message, "/activate?token=");

        assertTrue(activation.getQuery().contains("token="));
    }
}
```

### TestNG OTP / SMS tests

```java
@Test
public void should_log_in_when_reset_otp_entered() throws Exception {
    String email = mailConfig.newRecipient("reset");
    http.postForEntity("/auth/reset", new ResetRequest(email), Void.class);

    Message message = mail.awaitEmail(email, "Reset code", null);
    String otp = EmailExtractors.extractOtp(message);

    ResponseEntity<Void> verify = http.postForEntity("/auth/verify-reset",
        new VerifyResetRequest(email, otp, "Brand-N3w!"), Void.class);
    assertEquals(verify.getStatusCode(), HttpStatus.OK);
}

@Test
public void should_send_sms_code_when_phone_verification_requested() throws Exception {
    // Mailosaur provisions a dedicated test phone number on an SMS-enabled server.
    String phoneNumber = System.getenv("MAILOSAUR_PHONE_NUMBER");
    http.postForEntity("/auth/phone/verify", new PhoneRequest(phoneNumber), Void.class);

    Message sms = mail.awaitSms(phoneNumber, null);
    assertTrue(EmailExtractors.extractOtp(sms).matches("\\d{6}"));
}
```

### TestNG attachment test

```java
@Test
public void should_attach_pdf_invoice_when_invoice_emailed() throws Exception {
    String email = mailConfig.newRecipient("billing");
    http.postForEntity("/invoices/" + invoiceId + "/email", new EmailToRequest(email), Void.class);

    Message message = mail.awaitEmail(email, "Invoice", null);
    Attachment pdf = message.attachments().stream()
        .filter(a -> "application/pdf".equals(a.contentType()))
        .findFirst().orElseThrow(() -> new AssertionError("expected a PDF attachment"));

    byte[] bytes = mail.downloadAttachment(pdf.id());

    assertThat(pdf.fileName()).startsWith("invoice-");
    assertThat(new String(bytes, 0, 4)).isEqualTo("%PDF");
}
```

## Rules

### Inbox isolation
- **Unique recipient per test**: `{uuid}@{serverId}.mailosaur.net` via `mailConfig.newRecipient()`. Tests stay independent and parallel-safe with no shared cleanup.
- Prefer unique recipients over `messages().deleteAll(serverId)` — `deleteAll` wipes the **whole** server and will race a parallel suite.
- Search by `withSentTo` (+ `withSubject`), never "the latest message in the server".

### Waiting
- **The wait is `messages().get(params.withTimeout(ms), criteria)`** — it blocks until a match arrives, then throws on timeout. Never `Thread.sleep` around it.
- Set the timeout to a real SLA (default 20s here). Bump per call with a comment, not globally.

### Body assertions
- Assert on Mailosaur's **structured** output: `html().links()`/`href()`, `html().codes()`/`value()`. Don't substring-match the full `html().body()`.
- Assert a **user-visible outcome** of the link/OTP, not the raw string shape.
- Visual / template-shape checks → `qa/java/skills/visual-regression`.

### Attachments
- Validate content type **and** magic bytes for binaries. Check `length()` before downloading large files.

### Secrets
- `MAILOSAUR_API_KEY` + `MAILOSAUR_SERVER_ID` are secrets. Read from env / secret store; never in code or committed `application-test.yml`. In CI pull them per `qa/cicd/java/skills/ci-pipelines` (OIDC / encrypted secrets).

### What NOT to do
- No hardcoded API key or server ID.
- No `Thread.sleep` around `get` — its timeout is the wait.
- No `deleteAll` as a substitute for unique recipients in parallel suites.
- No assertions on the entire HTML body string.
- No `list` + client-side filtering when `get` with criteria does it server-side.

## Generation steps

1. Read `src/test/java/.../support` for existing base classes and conventions.
2. Confirm `com.mailosaur:mailosaur-java` is on the test classpath and that `MAILOSAUR_API_KEY` / `MAILOSAUR_SERVER_ID` are wired into the test env (not committed).
3. Generate:
   - `support/email/MailosaurConfig.java`
   - `support/email/Mailbox.java`
   - `support/email/EmailExtractors.java`
   - `support/MailosaurTestBase.java`
   - `{Flow}EmailIT.java` per scenario, plus the `build.gradle.kts` dependency.
4. Run `./gradlew test --tests "*EmailIT"` with the secrets present.

## Cross-references

- **`qa/java/skills/email-testing`** — the self-hosted SMTP-sink sibling. Pick Mailpit for offline CI and zero external deps; pick Mailosaur (here) for real-delivery and SMS. See the comparison table above.
- **`qa/typescript/skills/email-testing`** (canonical), **`qa/dotnet/skills/email-testing`** — sibling stacks; same wrapper shape, same `messages().get` wait.
- **`qa/cicd/java/skills/ci-pipelines`** — where these tests run in CI and where the `MAILOSAUR_API_KEY` / `MAILOSAUR_SERVER_ID` secrets are sourced (OIDC / encrypted secrets), never hardcoded.
- **`qa/java/skills/test-data-builder`** — generate unique per-test recipients through a builder.
- **`qa/java/skills/db-testing/testcontainers`** — signup creates a DB row *and* sends an email; assert both.
