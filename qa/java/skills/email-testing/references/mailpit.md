# QA — Email Testing with Mailpit (Java)

Scaffolds a typed Mailpit HTTP-API client (Java 21 `HttpClient` + Jackson) and TestNG / JUnit helpers that poll for a specific message with Awaitility, extract HTML / text / links / OTPs, and download attachments — each test isolated by its own recipient, never by wiping the shared inbox. Wires Mailpit into Spring Boot via `@DynamicPropertySource` so the SUT writes to the container.

## When to use

- Signup / password-reset / magic-link / OTP / receipt flows needing an email assertion
- Selenium / Playwright-Java E2E tests that click an emailed link
- Integration tests asserting `From`, `Reply-To`, subject templates, attachment shape
- CI jobs that need zero-dependency email capture

## When NOT to use

- Mailosaur cloud sandbox → `qa/java/skills/email-testing`
- Real Gmail / Outlook IMAP → `qa/java/skills/email-testing`
- SendGrid sandbox-mode → `qa/java/skills/email-testing`
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
| `DELETE` | `/api/v1/messages` | Wipe all / by ids — local debugging only, never from a test (see Inbox isolation) |

## Templates

### Gradle additions

```kotlin
dependencies {
    testImplementation("org.testcontainers:testcontainers")
    testImplementation("com.fasterxml.jackson.core:jackson-databind")
    testImplementation("org.awaitility:awaitility:4.2.2")
    testImplementation("org.assertj:assertj-core:3.27.7")
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
import java.util.Optional;

import static org.awaitility.Awaitility.await;

public final class MailpitClient {

    private static final Duration POLL_INTERVAL = Duration.ofMillis(250);

    private final HttpClient http = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(5))
        .build();
    private final ObjectMapper json = new ObjectMapper();
    private final String baseUrl;

    public MailpitClient(String baseUrl) {
        this.baseUrl = baseUrl;
    }

    public MessageSummary waitFor(String toAddress, String subjectContains, Duration timeout) {
        String query = URLEncoder.encode("to:" + toAddress + " subject:\"" + subjectContains + "\"",
            StandardCharsets.UTF_8);
        return await("Mailpit message to '" + toAddress + "' with subject '" + subjectContains + "'")
            .atMost(timeout)
            .pollInterval(POLL_INTERVAL)
            .until(() -> firstMatch(query), Optional::isPresent)
            .orElseThrow();
    }

    private Optional<MessageSummary> firstMatch(String query) throws Exception {
        HttpResponse<String> resp = http.send(
            HttpRequest.newBuilder(URI.create(baseUrl + "/api/v1/search?query=" + query + "&limit=1")).build(),
            HttpResponse.BodyHandlers.ofString());
        if (resp.statusCode() != 200) {
            throw new AssertionError("Mailpit search failed: " + resp.statusCode() + " " + resp.body());
        }
        return json.readValue(resp.body(), SearchResult.class).messages().stream().findFirst();
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

    @Test
    public void Should_SendWelcomeEmailWithActivationLink_When_UserSignsUp() throws Exception {
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
- One Mailpit per JVM (`static final` in `MailpitSupport`), shared by every test class.
- **Unique recipient per test** (`UUID.randomUUID()`) is the isolation; the search filters on it. There is **no
  global wipe** — `DELETE /api/v1/messages` in a `@BeforeMethod` deletes the mail another class running in
  parallel is still waiting for.
- Never assert "the only email is X" — assert "a message matching `to + subject` exists".

### Waiting
- Always use `waitFor` with a deadline. Default 15s.
- `waitFor` polls with **Awaitility** (`await(alias).atMost(timeout).pollInterval(250 ms).until(search, Optional::isPresent)`):
  it returns the first match, fails with a `ConditionTimeoutException` naming the recipient and subject, and
  rethrows a failed search at once. **No `Thread.sleep`** anywhere — not between send and assert, not inside the
  poll.

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
- No global inbox wipe; isolation is the unique recipient.

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
- **`qa/cicd/java/skills/ci-pipelines`** — Mailpit as a service container.
- **`qa/reporting/java/skills/test-reports`** — attach raw email source on failure.
