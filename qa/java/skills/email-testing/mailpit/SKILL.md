---
name: qa-email-testing-mailpit-java
description: Use when the user asks to assert on outbound email in Java 21 + Spring Boot 3 + TestNG (or JUnit 5) integration / E2E tests — capture signup welcome / OTP / password-reset / magic-link emails, extract subject / recipient / HTML body / links, download attachments, with Mailpit as the SMTP sink. Triggers: "verify the welcome email", "extract the OTP in the Selenium test", "Mailpit container for the Spring integration tests". Do NOT use for Mailosaur (`qa/java/skills/email-testing/mailosaur`), Gmail IMAP (`qa/java/skills/email-testing/gmail-imap`), .NET or TS stacks.
---

# QA — Email Testing with Mailpit (Java)

Scaffolds a typed Mailpit HTTP-API client (Java 21 `HttpClient` + Jackson) and TestNG / JUnit helpers that poll for a specific message, extract HTML / text / links / OTPs, download attachments, and reset the inbox between tests. Wires Mailpit into Spring Boot via `@DynamicPropertySource` so the SUT writes to the container.

## When to use

- Signup / password-reset / magic-link / OTP / receipt flows needing an email assertion
- Selenium / Playwright-Java E2E tests that click an emailed link
- Integration tests asserting `From`, `Reply-To`, subject templates, attachment shape
- CI jobs that need zero-dependency email capture

## When NOT to use

- Mailosaur cloud sandbox → `qa/java/skills/email-testing/mailosaur`
- Real Gmail / Outlook IMAP → `qa/java/skills/email-testing/gmail-imap`
- SendGrid sandbox-mode → `qa/java/skills/email-testing/sendgrid-sandbox`
- Production deliverability — Mailpit is a sink

## Inputs needed

1. Mailpit deployment: Testcontainers (default) or compose / Helm chart already running?
2. Scenario: signup / OTP / reset / magic link / arbitrary subject match?

## Mailpit API surface (cheat-sheet)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/messages?start=0&limit=50` | List/page |
| `GET` | `/api/v1/search?query=to:user@x.com+subject:Welcome` | Search (`to:`, `from:`, `subject:`, `body:`, `tag:`, `before:`, `after:`) |
| `GET` | `/api/v1/message/{ID}` | Full message + attachments metadata |
| `GET` | `/api/v1/message/{ID}/raw` | Raw RFC-822 |
| `GET` | `/api/v1/message/{ID}/part/{PartID}` | Download attachment |
| `DELETE` | `/api/v1/messages` | Wipe all / by ids |

## Templates

### Gradle additions

```kotlin
dependencies {
    testImplementation("org.testcontainers:testcontainers")
    testImplementation("com.fasterxml.jackson.module:jackson-module-kotlin") // or jackson-databind
    testImplementation("org.assertj:assertj-core:3.26.3")
}
```

### Mailpit container — `support/MailpitSupport.java`

```java
package com.flexinvest.support;

import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.wait.strategy.Wait;

public final class MailpitSupport {

    public static final GenericContainer<?> MAILPIT =
        new GenericContainer<>("axllent/mailpit:v1.20.5")
            .withExposedPorts(1025, 8025)
            .withEnv("MP_MAX_MESSAGES", "0")
            .waitingFor(Wait.forHttp("/api/v1/info").forPort(8025).forStatusCode(200));

    static {
        MAILPIT.start();
        Runtime.getRuntime().addShutdownHook(new Thread(MAILPIT::stop));
    }

    public static String apiBaseUrl() {
        return "http://" + MAILPIT.getHost() + ":" + MAILPIT.getMappedPort(8025);
    }

    public static String smtpHost() { return MAILPIT.getHost(); }
    public static int    smtpPort() { return MAILPIT.getMappedPort(1025); }

    private MailpitSupport() {}
}
```

### Spring wiring in the test base

```java
@DynamicPropertySource
static void mailpitProps(DynamicPropertyRegistry registry) {
    registry.add("spring.mail.host", MailpitSupport::smtpHost);
    registry.add("spring.mail.port", () -> String.valueOf(MailpitSupport.smtpPort()));
    registry.add("spring.mail.properties.mail.smtp.auth", () -> "false");
    registry.add("spring.mail.properties.mail.smtp.starttls.enable", () -> "false");
}
```

### Typed client — `support/email/MailpitClient.java`

```java
package com.flexinvest.support.email;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;

public final class MailpitClient {

    private final HttpClient http = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(5))
        .build();
    private final ObjectMapper json = new ObjectMapper();
    private final String baseUrl;

    public MailpitClient(String baseUrl) {
        this.baseUrl = baseUrl;
    }

    public MessageSummary waitFor(String toAddress, String subjectContains, Duration timeout) throws Exception {
        long deadline = System.currentTimeMillis() + timeout.toMillis();
        String query = URLEncoder.encode("to:" + toAddress + " subject:\"" + subjectContains + "\"",
            StandardCharsets.UTF_8);

        while (System.currentTimeMillis() < deadline) {
            HttpResponse<String> resp = http.send(
                HttpRequest.newBuilder(URI.create(baseUrl + "/api/v1/search?query=" + query + "&limit=1")).build(),
                HttpResponse.BodyHandlers.ofString());
            if (resp.statusCode() != 200) {
                throw new AssertionError("Mailpit search failed: " + resp.statusCode());
            }
            SearchResult body = json.readValue(resp.body(), SearchResult.class);
            if (!body.messages().isEmpty()) return body.messages().get(0);
            Thread.sleep(250);
        }
        throw new AssertionError("No Mailpit message to '" + toAddress
            + "' with subject '" + subjectContains + "' within " + timeout);
    }

    public Message get(String id) throws Exception {
        HttpResponse<String> resp = http.send(
            HttpRequest.newBuilder(URI.create(baseUrl + "/api/v1/message/" + id)).build(),
            HttpResponse.BodyHandlers.ofString());
        if (resp.statusCode() != 200) throw new AssertionError("Mailpit get failed: " + resp.statusCode());
        return json.readValue(resp.body(), Message.class);
    }

    public byte[] downloadAttachment(String messageId, String partId) throws Exception {
        HttpResponse<byte[]> resp = http.send(
            HttpRequest.newBuilder(URI.create(baseUrl + "/api/v1/message/" + messageId + "/part/" + partId)).build(),
            HttpResponse.BodyHandlers.ofByteArray());
        if (resp.statusCode() != 200) throw new AssertionError("Mailpit attachment failed: " + resp.statusCode());
        return resp.body();
    }

    public void deleteAll() throws Exception {
        HttpResponse<Void> resp = http.send(
            HttpRequest.newBuilder(URI.create(baseUrl + "/api/v1/messages"))
                .method("DELETE", HttpRequest.BodyPublishers.ofString("{\"ids\":[]}"))
                .header("content-type", "application/json")
                .build(),
            HttpResponse.BodyHandlers.discarding());
        if (resp.statusCode() >= 300) throw new AssertionError("Mailpit delete failed: " + resp.statusCode());
    }

    public record SearchResult(List<MessageSummary> messages, int total) {}

    public record MessageSummary(
        @JsonProperty("ID") String id,
        @JsonProperty("Subject") String subject,
        @JsonProperty("From") Address from,
        @JsonProperty("To") List<Address> to,
        @JsonProperty("Created") String created) {}

    public record Message(
        @JsonProperty("ID") String id,
        @JsonProperty("Subject") String subject,
        @JsonProperty("From") Address from,
        @JsonProperty("To") List<Address> to,
        @JsonProperty("HTML") String html,
        @JsonProperty("Text") String text,
        @JsonProperty("Attachments") List<Attachment> attachments) {}

    public record Address(
        @JsonProperty("Address") String address,
        @JsonProperty("Name") String name) {}

    public record Attachment(
        @JsonProperty("PartID") String partId,
        @JsonProperty("FileName") String fileName,
        @JsonProperty("ContentType") String contentType,
        @JsonProperty("Size") long size) {}
}
```

### Extractors

```java
package com.flexinvest.support.email;

import java.net.URI;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class EmailExtractors {

    private static final Pattern OTP = Pattern.compile("\\b(\\d{6})\\b");
    private static final Pattern URL = Pattern.compile("https?://[^\\s\"'<>]+", Pattern.CASE_INSENSITIVE);

    private EmailExtractors() {}

    public static String extractOtp(String text) {
        Matcher m = OTP.matcher(text);
        if (!m.find()) throw new AssertionError("No 6-digit OTP found in email body.");
        return m.group(1);
    }

    public static URI extractFirstLink(String html, String mustContain) {
        Matcher m = URL.matcher(html);
        while (m.find()) {
            String found = m.group();
            if (found.toLowerCase().contains(mustContain.toLowerCase())) return URI.create(found);
        }
        throw new AssertionError("No link containing '" + mustContain + "' found in HTML.");
    }
}
```

### TestNG signup test

```java
public class SignupEmailIT extends IntegrationTestBase {

    private final MailpitClient mail = new MailpitClient(MailpitSupport.apiBaseUrl());

    @Autowired private TestRestTemplate http;

    @BeforeMethod
    public void clearInbox() throws Exception {
        mail.deleteAll();
    }

    @Test
    public void should_send_welcome_email_with_activation_link_on_signup() throws Exception {
        String email = "signup-" + java.util.UUID.randomUUID() + "@test.local";

        ResponseEntity<Void> response = http.postForEntity("/auth/signup",
            new SignupRequest(email, "Str0ng!Passw0rd"), Void.class);
        assertEquals(response.getStatusCode(), HttpStatus.CREATED);

        var summary = mail.waitFor(email, "Welcome to FlexInvest", Duration.ofSeconds(15));
        var full = mail.get(summary.id());
        URI link = EmailExtractors.extractFirstLink(full.html(), "/activate?token=");

        assertEquals(full.from().address(), "no-reply@flexinvest.test");
        assertEquals(full.to().size(), 1);
        assertEquals(full.to().get(0).address(), email);
        assertNotNull(link.getQuery());
    }
}
```

## Rules

### Inbox isolation
- One Mailpit per JVM (`static final` in `MailpitSupport`). Clear with `DELETE /api/v1/messages` in `@BeforeMethod`.
- Unique recipient per test: `UUID.randomUUID()`.
- Never assert "the only email is X" — assert "a message matching `to + subject` exists".

### Waiting
- Always use `waitFor` with a deadline. Default 15s.
- **No `Thread.sleep` between send and assert.** Use the polling helper.

### Search queries
- Combine `to:` + `subject:` server-side. Don't list-all then loop.
- Quote multi-word subjects.

### Body assertions
- Extract structure (links, OTPs). Don't substring the whole HTML body.

### Attachments
- Validate content-type **and** magic bytes for binaries.
- Check `size()` before downloading large payloads.

### SUT wiring
- `@DynamicPropertySource` into `spring.mail.*`. Disable SMTP auth + TLS in the test profile.
- Never let production SMTP credentials leak into `application-test.yml`.

### What NOT to do
- No hardcoded ports — `getMappedPort()` only.
- No `latest` image tag — pin `axllent/mailpit:v1.20.5`.
- No inline regex in tests — use `EmailExtractors`.
- No assertions on the full HTML body string.
- No shared `MailpitClient` across threads without per-test cleanup.

## Generation steps

1. Read `src/test/java/.../support` for existing base classes and conventions.
2. Confirm Mailpit deployment (Testcontainers vs compose).
3. Generate:
   - `support/MailpitSupport.java`
   - `support/email/MailpitClient.java`
   - `support/email/EmailExtractors.java`
   - `{Flow}EmailIT.java`
   - `build.gradle.kts` test dependency additions.
4. Run `./gradlew test --tests "*EmailIT"`.

## Cross-references

- **`qa/java/skills/test-data-builder`** — unique-email builder.
- **`qa/java/skills/db-testing/testcontainers`** — signup creates a DB row *and* sends an email.
- **`qa/java/skills/ci-pipelines/azure-pipelines`** — Mailpit as a service container.
- **`qa/java/skills/allure-reporting`** — attach raw email source on failure.
