# QA — Email Testing against a Real Mailbox over IMAP (Java)

Scaffolds a thin, intent-revealing wrapper over Jakarta Mail (`Store` / `Folder` / `SearchTerm` over `imaps`) plus TestNG helpers that **poll a real provider mailbox** (Gmail / Outlook / any IMAP server) for a specific message — by recipient alias + subject + received-date bound — walk the `MimeMultipart` for HTML / text body / attachments, extract links / OTP codes, and clean up by flagging the message `\Seen` / `\Deleted` rather than wiping an inbox.

This is the sibling for flows that must exercise the **genuine provider inbox** — real MX, real spam/routing, real provider quirks — not an SMTP sink or a test-SaaS server. Two consequences shape the whole skill:

- **There is no per-test unique-inbox trick** (no `{uuid}@{serverId}.mailosaur.net`) and **no `DELETE all` HTTP API** (no Mailpit wipe). Isolation comes from **Gmail `+tag` / dot aliases** — `youraccount+{uuid}@gmail.com` all land in the *one* real inbox — plus a **received-date lower bound** and a **server-side search by To + Subject**. Cleanup is per-message via IMAP flags (`Flags.Flag.SEEN` / `Flags.Flag.DELETED` + close-with-expunge), not a wipe.
- **No SDK "blocks until arrived" primitive exists.** The wait **is** a real **poll-with-deadline loop** over the IMAP search — but still **no `Thread.sleep`-only wait**: poll the search on an interval against a deadline (the same `waitFor` shape as `qa/java/skills/email-testing`). Real-provider delivery is slower, so the default budget is larger (~25s).

## When to use

- Signup / password-reset / magic-link / OTP flows that must hit a **real provider mailbox** over IMAP (genuine deliverability path, not a sink or SaaS capture)
- Teams already owning a dedicated test Gmail / Outlook / M365 account they want to drive from CI
- Selenium / Playwright-Java E2E tests that click an emailed link or type an emailed OTP read from the real inbox
- Integration tests asserting `From`, subject templates, HTML link targets, attachment shape on real delivery

## When NOT to use

- Self-hosted SMTP sink, zero external deps, fully offline CI → `qa/java/skills/email-testing`
- Hosted sandbox with per-test inboxes + a blocking SDK wait + SMS → `qa/java/skills/email-testing`
- SendGrid sandbox-mode (mail-send API, no delivery) → `qa/java/skills/email-testing`
- TS or .NET stacks → `qa/{typescript,dotnet}/skills/email-testing`
- Production deliverability / DKIM / SPF auditing — this polls a mailbox, it is not a relay verifier

## Inputs needed

Ask at most 2 questions; infer the rest from the test sources and existing support classes.

1. Scenario: signup welcome / OTP / password reset / magic link / arbitrary subject match?
2. Where do `IMAP_USER` (mailbox address) and `IMAP_PASSWORD` (Gmail **App Password**, or an OAuth2 XOAUTH2 token) come from in this environment? They are **secrets** — never commit them.

## IMAP surface (cheat-sheet — Jakarta Mail)

| Call | Purpose |
|---|---|
| `Session.getInstance(props)` | Build a session (`mail.store.protocol=imaps`) |
| `Store store = session.getStore("imaps"); store.connect(host, 993, user, appPassword)` | TLS IMAP connection (App Password) |
| `Folder inbox = store.getFolder("INBOX"); inbox.open(Folder.READ_WRITE)` | Open INBOX (read-write so flags/expunge work) |
| `new AndTerm(new RecipientStringTerm(TO, alias), new SubjectTerm(subject), new ReceivedDateTerm(GE, since))` | To + Subject + received-after term |
| `Message[] msgs = inbox.search(term)` | **Server-side** search |
| `message.getContent()` / `MimeMultipart` walk | HTML + text + attachments (`getDisposition()`) |
| `message.setFlag(Flags.Flag.SEEN, true)` | Mark processed (cleanup, not a wipe) |
| `message.setFlag(Flags.Flag.DELETED, true)` + `inbox.close(true)` | Per-message delete + expunge |
| `store.close()` | Close the session (always, in teardown) |

**`+tag` alias pattern:** Gmail (and many providers) route `youraccount+{anything}@gmail.com` and dotted variants to the *one* real inbox, but the `+tag` is preserved in the `To` header — so per test, send to `${base}+{uuid}` and search server-side by that exact recipient. Combined with a received-date lower bound (test start time), every test owns a unique, time-bounded slice of the shared inbox with no wipe.

## Templates

### Gradle additions

```kotlin
dependencies {
    testImplementation("org.eclipse.angus:angus-mail:2.0.3") // Jakarta Mail 2.x (jakarta.mail.*)
    testImplementation("org.assertj:assertj-core:3.26.3")
}
```

### Config — `support/email/ImapConfig.java`

Secrets come from the environment, validated once. Never inline the address or App Password.

```java
package com.flexinvest.support.email;

import java.time.Duration;
import java.util.UUID;

public final class ImapConfig {

    private final String host;
    private final int port;
    private final String user;
    private final String password;
    private final Duration timeout;
    private final Duration pollInterval;

    private ImapConfig(String host, int port, String user, String password,
                       Duration timeout, Duration pollInterval) {
        this.host = host;
        this.port = port;
        this.user = user;
        this.password = password;
        this.timeout = timeout;
        this.pollInterval = pollInterval;
    }

    public static ImapConfig fromEnvironment() {
        long timeoutMs = envLong("IMAP_TIMEOUT_MS", 25_000L);
        long pollMs = envLong("IMAP_POLL_MS", 2_000L);
        return new ImapConfig(
            envOr("IMAP_HOST", "imap.gmail.com"),
            (int) envLong("IMAP_PORT", 993L),
            required("IMAP_USER"),       // e.g. flexinvest.qa@gmail.com
            required("IMAP_PASSWORD"),   // Gmail App Password (or XOAUTH2 token)
            Duration.ofMillis(timeoutMs),
            Duration.ofMillis(pollMs));
    }

    private static String required(String name) {
        String v = System.getenv(name);
        if (v == null || v.isBlank()) {
            throw new IllegalStateException("Missing required env var " + name + " (IMAP secret).");
        }
        return v;
    }

    private static String envOr(String name, String fallback) {
        String v = System.getenv(name);
        return (v == null || v.isBlank()) ? fallback : v;
    }

    private static long envLong(String name, long fallback) {
        String v = System.getenv(name);
        return (v == null || v.isBlank()) ? fallback : Long.parseLong(v);
    }

    public String host()           { return host; }
    public int port()              { return port; }
    public String user()           { return user; }
    public String password()       { return password; }
    public Duration timeout()      { return timeout; }
    public Duration pollInterval() { return pollInterval; }

    /** Per-test `+tag` alias into the one real inbox → independent, searchable, no wipe. */
    public String aliasFor(String prefix) {
        int at = user.indexOf('@');
        return user.substring(0, at) + "+" + prefix + "-" + UUID.randomUUID() + user.substring(at);
    }
}
```

### Intent-revealing wrapper — `support/email/Mailbox.java`

Tests never drive `search` / `getContent` directly. They call `awaitSignupEmail`, `awaitEmail`, `markProcessed`. Connection lifecycle (connect once, poll INBOX, close on teardown) lives here — tests never leak an IMAP connection.

```java
package com.flexinvest.support.email;

import jakarta.mail.Flags;
import jakarta.mail.Folder;
import jakarta.mail.Message;
import jakarta.mail.Session;
import jakarta.mail.Store;
import jakarta.mail.search.AndTerm;
import jakarta.mail.search.ComparisonTerm;
import jakarta.mail.search.ReceivedDateTerm;
import jakarta.mail.search.RecipientStringTerm;
import jakarta.mail.search.SearchTerm;
import jakarta.mail.search.SubjectTerm;

import java.time.Duration;
import java.util.Date;
import java.util.Properties;

public final class Mailbox implements AutoCloseable {

    private final ImapConfig config;
    private Store store;
    private Folder inbox;

    public Mailbox(ImapConfig config) {
        this.config = config;
    }

    public void connect() throws Exception {
        Properties props = new Properties();
        props.put("mail.store.protocol", "imaps");
        Session session = Session.getInstance(props);
        store = session.getStore("imaps");
        store.connect(config.host(), config.port(), config.user(), config.password());
        inbox = store.getFolder("INBOX");
        inbox.open(Folder.READ_WRITE); // read-write so flag/expunge cleanup works
    }

    /**
     * Poll the real inbox until a message to {@code sentTo} (+ optional subject),
     * received after {@code since}, arrives — or the deadline fires. NOT a fixed
     * sleep: a deadline loop over the server-side IMAP search, interval-paced.
     */
    public Message awaitEmail(String sentTo, String subject, Date since, Duration timeoutOverride)
            throws Exception {
        Duration budget = timeoutOverride != null ? timeoutOverride : config.timeout();
        Date sinceDate = since != null ? since : new Date(System.currentTimeMillis() - 60_000);
        long deadline = System.currentTimeMillis() + budget.toMillis();

        SearchTerm term = new AndTerm(
            new RecipientStringTerm(Message.RecipientType.TO, sentTo),
            new ReceivedDateTerm(ComparisonTerm.GE, sinceDate));
        if (subject != null) {
            term = new AndTerm(term, new SubjectTerm(subject));
        }

        while (System.currentTimeMillis() < deadline) {
            inbox.getMessageCount(); // forces a NOOP so newly delivered mail is visible
            Message[] found = inbox.search(term);
            if (found.length > 0) {
                return found[found.length - 1]; // newest match
            }
            Thread.sleep(config.pollInterval().toMillis()); // poll cadence, not the wait itself
        }
        throw new AssertionError("No message to '" + sentTo + "'"
            + (subject != null ? " subject '" + subject + "'" : "") + " within " + budget);
    }

    public Message awaitSignupEmail(String sentTo, Date since) throws Exception {
        return awaitEmail(sentTo, "Welcome", since, null);
    }

    /** Cleanup is per-message, not a wipe: flag SEEN, or DELETED + expunge on close. */
    public void markProcessed(Message message, boolean delete) throws Exception {
        message.setFlag(delete ? Flags.Flag.DELETED : Flags.Flag.SEEN, true);
    }

    @Override
    public void close() throws Exception {
        if (inbox != null && inbox.isOpen()) inbox.close(true); // expunge DELETED-flagged
        if (store != null && store.isConnected()) store.close();
    }
}
```

### Extractors — `support/email/EmailExtractors.java`

No provider-supplied codes here (that's a Mailosaur convenience) — extract structure with the same regexes as the Mailpit skill. `MimeMessageBodies` walks the `MimeMultipart` to pull HTML / text / attachments out of the real message.

```java
package com.flexinvest.support.email;

import jakarta.mail.Message;
import jakarta.mail.Part;
import jakarta.mail.internet.MimeMultipart;

import java.io.ByteArrayOutputStream;
import java.net.URI;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class EmailExtractors {

    private static final Pattern OTP = Pattern.compile("\\b(\\d{6})\\b");
    private static final Pattern URL = Pattern.compile("https?://[^\\s\"'<>]+", Pattern.CASE_INSENSITIVE);

    private EmailExtractors() {}

    public static String extractOtp(Message message) throws Exception {
        Matcher m = OTP.matcher(MimeBodies.text(message));
        if (!m.find()) throw new AssertionError("No 6-digit OTP found in '" + message.getSubject() + "'.");
        return m.group(1);
    }

    public static URI extractLink(Message message, String mustContain) throws Exception {
        Matcher m = URL.matcher(MimeBodies.html(message));
        while (m.find()) {
            if (m.group().toLowerCase().contains(mustContain.toLowerCase())) return URI.create(m.group());
        }
        throw new AssertionError("No link containing '" + mustContain + "' in '" + message.getSubject() + "'.");
    }

    /** Walks a (possibly multipart) message to its HTML / text bodies and attachment parts. */
    public static final class MimeBodies {

        public static String html(Message message) throws Exception {
            String html = firstByType(message, "text/html");
            return html != null ? html : firstByType(message, "text/plain");
        }

        public static String text(Message message) throws Exception {
            String text = firstByType(message, "text/plain");
            return text != null ? text : firstByType(message, "text/html");
        }

        public static List<Part> attachments(Message message) throws Exception {
            List<Part> parts = new ArrayList<>();
            collectAttachments(message, parts);
            return parts;
        }

        public static byte[] bytes(Part attachment) throws Exception {
            try (var in = attachment.getInputStream(); var out = new ByteArrayOutputStream()) {
                in.transferTo(out);
                return out.toByteArray();
            }
        }

        private static String firstByType(Part part, String mimeType) throws Exception {
            if (part.isMimeType(mimeType)) {
                return (String) part.getContent();
            }
            if (part.getContent() instanceof MimeMultipart multipart) {
                for (int i = 0; i < multipart.getCount(); i++) {
                    String found = firstByType(multipart.getBodyPart(i), mimeType);
                    if (found != null) return found;
                }
            }
            return null;
        }

        private static void collectAttachments(Part part, List<Part> out) throws Exception {
            if (Part.ATTACHMENT.equalsIgnoreCase(part.getDisposition())) {
                out.add(part);
            } else if (part.getContent() instanceof MimeMultipart multipart) {
                for (int i = 0; i < multipart.getCount(); i++) {
                    collectAttachments(multipart.getBodyPart(i), out);
                }
            }
        }

        private MimeBodies() {}
    }
}
```

### TestNG base — `support/ImapTestBase.java`

```java
package com.flexinvest.support;

import com.flexinvest.support.email.ImapConfig;
import com.flexinvest.support.email.Mailbox;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;

public abstract class ImapTestBase {

    protected ImapConfig imapConfig;
    protected Mailbox mail;

    @BeforeClass
    public void connectMailbox() throws Exception {
        imapConfig = ImapConfig.fromEnvironment();
        mail = new Mailbox(imapConfig);
        mail.connect();
    }

    @AfterClass(alwaysRun = true)
    public void disconnectMailbox() throws Exception {
        if (mail != null) mail.close();
    }
}
```

### TestNG signup test

```java
public class SignupEmailIT extends ImapTestBase {

    @Autowired private TestRestTemplate http;

    @Test
    public void should_send_welcome_email_with_activation_link_on_signup() throws Exception {
        String email = imapConfig.aliasFor("signup");
        Date since = new Date(); // time-bound the search to this test

        ResponseEntity<Void> response = http.postForEntity("/auth/signup",
            new SignupRequest(email, "Str0ng!Passw0rd"), Void.class);
        assertEquals(response.getStatusCode(), HttpStatus.CREATED);

        Message message = mail.awaitSignupEmail(email, since);
        URI activation = EmailExtractors.extractLink(message, "/activate?token=");

        assertTrue(activation.getQuery().contains("token="));
        mail.markProcessed(message, true);
    }
}
```

### TestNG OTP test

```java
@Test
public void should_log_in_when_reset_otp_entered() throws Exception {
    String email = imapConfig.aliasFor("reset");
    Date since = new Date();
    http.postForEntity("/auth/reset", new ResetRequest(email), Void.class);

    Message message = mail.awaitEmail(email, "Reset code", since, null);
    String otp = EmailExtractors.extractOtp(message);

    ResponseEntity<Void> verify = http.postForEntity("/auth/verify-reset",
        new VerifyResetRequest(email, otp, "Brand-N3w!"), Void.class);
    assertEquals(verify.getStatusCode(), HttpStatus.OK);
    mail.markProcessed(message, true);
}
```

### TestNG attachment test

```java
@Test
public void should_attach_pdf_invoice_when_invoice_emailed() throws Exception {
    String email = imapConfig.aliasFor("billing");
    Date since = new Date();
    http.postForEntity("/invoices/" + invoiceId + "/email", new EmailToRequest(email), Void.class);

    Message message = mail.awaitEmail(email, "Invoice", since, null);
    Part pdf = EmailExtractors.MimeBodies.attachments(message).stream()
        .filter(p -> {
            try { return p.isMimeType("application/pdf"); } catch (Exception e) { return false; }
        })
        .findFirst().orElseThrow(() -> new AssertionError("expected a PDF attachment"));

    byte[] bytes = EmailExtractors.MimeBodies.bytes(pdf);

    assertThat(pdf.getFileName()).startsWith("invoice-");
    assertThat(new String(bytes, 0, 4)).isEqualTo("%PDF"); // magic bytes
    mail.markProcessed(message, true);
}
```

## Rules

### Inbox isolation (no unique inbox, no wipe)
- **Per-test `+tag` alias** via `imapConfig.aliasFor()` — `base+{uuid}@domain` all land in the one real inbox but carry a unique recipient. Search by that exact recipient.
- **Always received-date-bound the search** (`ReceivedDateTerm(GE, since)`) to the test's start time. The real inbox accumulates history; an unbounded search matches stale mail.
- Search **server-side by To + Subject + received-date** (`inbox.search(term)`). Never fetch-all-then-filter client-side.
- Cleanup is **per message**: `setFlag(SEEN)` or `setFlag(DELETED)` + `inbox.close(true)` to expunge. No Mailpit-style wipe and no Mailosaur-style throwaway inbox — never expunge the whole INBOX.

### Waiting (poll-with-deadline, never a fixed sleep)
- The wait is the `awaitEmail` **deadline loop** over the IMAP search. The `Thread.sleep(pollInterval)` inside it is the **poll cadence**, not the wait — there is no bare fixed sleep between send and assert.
- Touch `getMessageCount()` (a NOOP) between polls so the open folder sees newly delivered mail.
- Default budget ~25s (real delivery is slower than a sink). Bump per call with a comment, not globally.
- Pace the poll (`pollInterval`, ~2s) — Gmail throttles aggressive IMAP polling.

### Connection lifecycle
- Connect once per class (`@BeforeClass`); `close()` (store + folder) in `@AfterClass(alwaysRun = true)`. Never leak IMAP connections across tests.
- Open INBOX `Folder.READ_WRITE` so flag/expunge cleanup works.

### Body assertions
- Extract structure (links from the HTML part, OTP from the text part) and assert a **user-visible outcome** (token present, reset succeeds). Don't substring-match the full HTML.
- Visual / template-shape checks → `qa/java/skills/visual-regression`.

### Attachments
- Validate content type **and** magic bytes for binaries. Read via `getInputStream()`.

### Secrets
- `IMAP_USER` + `IMAP_PASSWORD` are secrets. The password is a Gmail **App Password** (2FA required; "less secure app access" is gone) — the pragmatic CI choice. **OAuth2 XOAUTH2** (via `mail.imaps.sasl.mechanisms=XOAUTH2`) is the more-secure option for long-lived setups. Read from env / secret store; never in code or committed `application-test.yml`. In CI pull them per `qa/cicd/java/skills/ci-pipelines`.

### What NOT to do
- No hardcoded mailbox address or App Password.
- No unbounded search — always `ReceivedDateTerm` + exact `RecipientStringTerm`.
- No `Thread.sleep` as the wait — use the deadline poll (the in-loop sleep is the cadence only).
- No whole-INBOX wipe/expunge — clean up per message only.
- No assertions on the entire HTML body string.
- No shared single alias across tests — one `+tag` per test.

## Generation steps

1. Read `src/test/java/.../support` for existing base classes and conventions.
2. Confirm `org.eclipse.angus:angus-mail` is on the test classpath and that `IMAP_USER` / `IMAP_PASSWORD` (App Password) are wired into the test env (not committed).
3. Generate:
   - `support/email/ImapConfig.java`
   - `support/email/Mailbox.java`
   - `support/email/EmailExtractors.java`
   - `support/ImapTestBase.java`
   - `{Flow}EmailIT.java` per scenario, plus the `build.gradle.kts` dependency.
4. Run `./gradlew test --tests "*EmailIT"` with the secrets present.

## Cross-references

- **`qa/java/skills/email-testing`**, **`qa/java/skills/email-testing`** — the other two email siblings. See the three-way pick table above: real provider (here) vs hosted SaaS vs self-hosted sink.
- **`qa/typescript/skills/email-testing`** (canonical, `imapflow`), **`qa/dotnet/skills/email-testing`** (MailKit) — sibling stacks; same wrapper shape, same poll-with-deadline wait.
- **`qa/cicd/java/skills/ci-pipelines`** — where these tests run in CI and where the `IMAP_PASSWORD` App Password secret is sourced (OIDC / encrypted secrets), never hardcoded.
- **`qa/java/skills/test-data-builder`** — generate per-test `+tag` aliases through a builder.
- **`qa/java/skills/db-testing/testcontainers`** — signup creates a DB row *and* sends an email; assert both.
