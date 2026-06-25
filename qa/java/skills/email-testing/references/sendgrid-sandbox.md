# QA — Validate Outbound Mail via SendGrid Sandbox Mode (Java)

Scaffolds a thin, intent-revealing wrapper over the official `com.sendgrid:sendgrid-java` SDK plus TestNG helpers that **validate the SUT's send request without delivering any email**. With a `MailSettings` whose `Setting sandboxMode.setEnable(true)`, SendGrid runs its real validator over the form, type, and shape of the request — template IDs, personalizations, dynamic template data, `from` / `reply-to`, categories — accepts a valid one with **`200`** (note: not the `202` a real send returns), and **delivers nothing**. A malformed request surfaces as a **`4xx` with an error body**.

This is the **"no inbox at all"** sibling. The other three email skills all assert on a *captured / delivered* message; **this one never produces a received message** — there is no SMTP sink, no IMAP poll, no `messages().get`. Two consequences shape the whole skill:

- **There is no wait — at all.** No poll loop, no `waitFor`, no `Thread.sleep`. A send under sandbox mode is a single request/response: you call `sg.api(request)` and assert on `response.getStatusCode()`. There is nothing to arrive, so there is nothing to wait for.
- **The strongest check needs no network and no secret.** Because the request is built locally before it goes anywhere, the deterministic assertion is on the **constructed `Mail` itself** — recipient, `templateId`, dynamic template data, categories, `from` / `reply-to`. That test runs offline, in milliseconds, with no `SENDGRID_API_KEY`. The sandbox round-trip then adds one thing the local check can't: confirmation that SendGrid's **real** validator accepts the payload (catching template-ID typos, malformed personalizations, bad dynamic-data shape) — without sending an email or needing a mailbox.

## When to use

- Asserting the SUT builds a **well-formed** transactional send: correct template ID, dynamic data, recipients, `from` / `reply-to`, categories
- Catching template-ID typos and malformed personalizations / dynamic-data shape against SendGrid's **real** validator, in CI, without delivering mail or owning a mailbox
- Unit/integration-testing the mail-notification layer (a `Notifier`) in isolation — inject a mock `SendGrid` to assert the exact request offline, or flip sandbox on for the live validate round-trip
- Fast, deterministic CI where standing up an inbox (IMAP / Mailosaur / Mailpit) is overkill because you only need "is our send request valid and accepted?"

## When NOT to use

- You must assert on a **delivered / received** message (body rendered, link clickable, OTP extracted, attachment present) — sandbox mode delivers **nothing**:
  - Real provider mailbox over IMAP → `qa/java/skills/email-testing`
  - Hosted SaaS inbox + SMS → `qa/java/skills/email-testing`
  - Self-hosted SMTP sink, offline CI → `qa/java/skills/email-testing`
- The SUT doesn't send through SendGrid's Mail Send API (uses raw SMTP, SES, etc.) → use one of the inbox siblings
- Production deliverability / DKIM / SPF / template-render auditing — sandbox proves the **request** is valid, **not** that a human-readable email rendered or was delivered
- TS or .NET stacks → `qa/{typescript,dotnet}/skills/email-testing`

## Inputs needed

Ask at most 2 questions; infer the rest from the test sources and existing support classes.

1. Scenario: welcome / password-reset / arbitrary transactional template — and which dynamic-data keys does it carry?
2. Where does `SENDGRID_API_KEY` come from in this environment (CI secret store)? It is the **one** secret and is needed **only** for the live sandbox round-trip — the payload check needs no key. Never commit it.

## SendGrid SDK surface (cheat-sheet — `com.sendgrid:sendgrid-java`)

| Call | Purpose |
|---|---|
| `new SendGrid(apiKey)` | The client; inject it (constructor injection) and mock it in unit tests — never hardcode the key |
| `new Mail()` | The message; `setFrom`, `setReplyTo`, `setTemplateId`, `addPersonalization`, `addCategory`, `setMailSettings` |
| `mail.setTemplateId("d-...")` | Dynamic template ID |
| `new Personalization()` + `p.addTo(new Email(to))` + `p.addDynamicTemplateData(key, value)` | Recipient + dynamic data block |
| `MailSettings ms = new MailSettings(); Setting s = new Setting(); s.setEnable(true); ms.setSandboxMode(s); mail.setMailSettings(ms);` | **Sandbox**: full validation, no delivery → `200` (real send → `202`) |
| `Request req = new Request(); req.setMethod(Method.POST); req.setEndpoint("mail/send"); req.setBody(mail.build());` | Build the API request from the `Mail` |
| `Response response = sg.api(req)` | Send → `Response`. Under sandbox: validates, delivers nothing |
| `response.getStatusCode()` | `200` under sandbox; `202` for a real accepted send; `4xx` on a malformed request |

**Key point:** sandbox mode lives on the **message** (`mail.setMailSettings(...)`), not the client. Keep the message *builders* pure (no key, no client, no sandbox flag) so they serve production too; let the `Notifier` decide whether to flip sandbox on — that way tests assert on the pure `Mail` offline and never build `MailSettings` themselves.

## Templates

### Gradle additions

```kotlin
dependencies {
    testImplementation("com.sendgrid:sendgrid-java:4.10.3")
    testImplementation("org.mockito:mockito-core:5.12.0")
    testImplementation("org.assertj:assertj-core:3.26.3")
}
```

### Config — `support/email/SendGridConfig.java`

Template IDs + `from` are non-secret defaults (so the payload check needs no secret). The API key is read lazily and **only** when a live send actually happens.

```java
package com.flexinvest.support.email;

public final class SendGridConfig {

    private final String from;
    private final String replyTo;
    private final String welcomeTemplateId;
    private final String passwordResetTemplateId;

    private SendGridConfig(String from, String replyTo,
                           String welcomeTemplateId, String passwordResetTemplateId) {
        this.from = from;
        this.replyTo = replyTo;
        this.welcomeTemplateId = welcomeTemplateId;
        this.passwordResetTemplateId = passwordResetTemplateId;
    }

    /** Non-secret send defaults — usable offline by the pure builders, no API key required. */
    public static SendGridConfig defaults() {
        return new SendGridConfig(
            envOr("SENDGRID_FROM", "no-reply@flexinvest.test"),
            envOr("SENDGRID_REPLY_TO", "support@flexinvest.test"),
            envOr("SENDGRID_TEMPLATE_WELCOME", "d-welcome00000000000000000000000"),
            envOr("SENDGRID_TEMPLATE_RESET", "d-reset000000000000000000000000"));
    }

    /** The ONE secret, read lazily — only the live sandbox round-trip needs it. */
    public static String apiKey() {
        String v = System.getenv("SENDGRID_API_KEY");
        if (v == null || v.isBlank()) {
            throw new IllegalStateException("Missing required env var SENDGRID_API_KEY (SendGrid secret).");
        }
        return v;
    }

    private static String envOr(String name, String fallback) {
        String v = System.getenv(name);
        return (v == null || v.isBlank()) ? fallback : v;
    }

    public String from()                    { return from; }
    public String replyTo()                 { return replyTo; }
    public String welcomeTemplateId()       { return welcomeTemplateId; }
    public String passwordResetTemplateId() { return passwordResetTemplateId; }
}
```

### Pure message builders — `support/email/Messages.java`

No client, no key, no sandbox flag — just the `Mail` the SUT would send. This is what the deterministic, offline, no-secret test asserts on via the `Mail` getters.

```java
package com.flexinvest.support.email;

import com.sendgrid.helpers.mail.Mail;
import com.sendgrid.helpers.mail.objects.Email;
import com.sendgrid.helpers.mail.objects.Personalization;

public final class Messages {

    private Messages() {}

    public static Mail welcome(SendGridConfig config, String to, String firstName, String activationUrl) {
        Mail mail = new Mail();
        mail.setFrom(new Email(config.from()));
        mail.setReplyTo(new Email(config.replyTo()));
        mail.setTemplateId(config.welcomeTemplateId());

        Personalization personalization = new Personalization();
        personalization.addTo(new Email(to));
        personalization.addDynamicTemplateData("first_name", firstName);
        personalization.addDynamicTemplateData("activation_url", activationUrl);
        mail.addPersonalization(personalization);

        mail.addCategory("welcome");
        mail.addCategory("transactional");
        return mail;
    }

    public static Mail passwordReset(SendGridConfig config, String to, String otp) {
        Mail mail = new Mail();
        mail.setFrom(new Email(config.from()));
        mail.setReplyTo(new Email(config.replyTo()));
        mail.setTemplateId(config.passwordResetTemplateId());

        Personalization personalization = new Personalization();
        personalization.addTo(new Email(to));
        personalization.addDynamicTemplateData("otp", otp);
        mail.addPersonalization(personalization);

        mail.addCategory("password-reset");
        mail.addCategory("transactional");
        return mail;
    }
}
```

### Intent-revealing wrapper — `support/email/Notifier.java`

Tests call `sendWelcome` / `sendPasswordReset`, never `sg.api` or `MailSettings`. The `Notifier` injects the `SendGrid` client (constructor injection — pass a mock in unit tests) and owns the sandbox decision. `buildWelcome` is exposed so a test can assert the final, sandbox-applied `Mail` without sending.

```java
package com.flexinvest.support.email;

import com.sendgrid.Method;
import com.sendgrid.Request;
import com.sendgrid.Response;
import com.sendgrid.SendGrid;
import com.sendgrid.helpers.mail.Mail;
import com.sendgrid.helpers.mail.objects.MailSettings;
import com.sendgrid.helpers.mail.objects.Setting;

import java.io.IOException;

public final class Notifier {

    private final SendGrid client;
    private final SendGridConfig config;
    private final boolean sandbox;

    public Notifier(SendGrid client, SendGridConfig config, boolean sandbox) {
        this.client = client;
        this.config = config;
        this.sandbox = sandbox;
    }

    /** Apply sandbox mode at send time so the pure builders stay production-usable. */
    private Mail prepare(Mail mail) {
        if (sandbox) {
            Setting sandboxMode = new Setting();
            sandboxMode.setEnable(true);
            MailSettings mailSettings = new MailSettings();
            mailSettings.setSandboxMode(sandboxMode);
            mail.setMailSettings(mailSettings);
        }
        return mail;
    }

    public Mail buildWelcome(String to, String firstName, String activationUrl) {
        return prepare(Messages.welcome(config, to, firstName, activationUrl));
    }

    public Response sendWelcome(String to, String firstName, String activationUrl) throws IOException {
        return send(buildWelcome(to, firstName, activationUrl));
    }

    public Response sendPasswordReset(String to, String otp) throws IOException {
        return send(prepare(Messages.passwordReset(config, to, otp)));
    }

    private Response send(Mail mail) throws IOException {
        Request request = new Request();
        request.setMethod(Method.POST);
        request.setEndpoint("mail/send");
        request.setBody(mail.build());
        return client.api(request);
    }

    /** Canonical live test entry-point: a real client in sandbox mode. Reads the key lazily. */
    public static Notifier sandbox() {
        return new Notifier(new SendGrid(SendGridConfig.apiKey()), SendGridConfig.defaults(), true);
    }
}
```

### TestNG — deterministic payload check (offline, no secret)

The strongest assertion runs without the network or the API key: the builder produced the right shape. Multiple asserts, one behavior — "the welcome message is well-formed".

```java
package com.flexinvest.support.email;

import com.sendgrid.helpers.mail.Mail;
import com.sendgrid.helpers.mail.objects.Personalization;
import org.testng.annotations.Test;

import static org.assertj.core.api.Assertions.assertThat;

public class WelcomeMessageTest {

    @Test
    public void should_address_templated_welcome_with_activation_data_when_built() {
        SendGridConfig config = SendGridConfig.defaults();

        Mail mail = Messages.welcome(config, "jane@acme.test", "Jane",
            "https://app.flexinvest.test/activate?token=abc123");

        Personalization personalization = mail.getPersonalization().get(0);
        assertThat(personalization.getTos().get(0).getEmail()).isEqualTo("jane@acme.test");
        assertThat(mail.getFrom().getEmail()).isEqualTo(config.from());
        assertThat(mail.getTemplateId()).isEqualTo(config.welcomeTemplateId());
        assertThat(personalization.getDynamicTemplateData().get("activation_url").toString()).contains("token=");
        assertThat(mail.getCategories()).contains("welcome");
    }
}
```

### TestNG — Notifier applies sandbox, sends valid request (offline, mock client)

Constructor injection lets us mock `SendGrid`, capture the exact `Request`, and assert the serialized body carries sandbox mode + the template — zero network, no secret. (Mockito.)

```java
package com.flexinvest.support.email;

import com.sendgrid.Request;
import com.sendgrid.Response;
import com.sendgrid.SendGrid;
import org.mockito.ArgumentCaptor;
import org.testng.annotations.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

public class NotifierSandboxTest {

    @Test
    public void should_enable_sandbox_on_the_sent_request_when_sandbox_notifier() throws Exception {
        SendGrid client = mock(SendGrid.class);
        when(client.api(any(Request.class))).thenReturn(new Response(200, "", java.util.Map.of()));
        Notifier notifier = new Notifier(client, SendGridConfig.defaults(), true);

        notifier.sendPasswordReset("jane@acme.test", "123456");

        ArgumentCaptor<Request> captor = ArgumentCaptor.forClass(Request.class);
        org.mockito.Mockito.verify(client).api(captor.capture());
        assertThat(captor.getValue().getBody()).contains("\"sandbox_mode\":{\"enable\":true}");
    }
}
```

### TestNG — live sandbox round-trip (SendGrid's real validator accepts it)

The only test that touches the network and needs the key. No wait, no inbox — just assert the status code. `200` means the payload is valid and **nothing was delivered**.

```java
package com.flexinvest.support.email;

import com.sendgrid.Method;
import com.sendgrid.Request;
import com.sendgrid.Response;
import com.sendgrid.SendGrid;
import com.sendgrid.helpers.mail.Mail;
import com.sendgrid.helpers.mail.objects.Email;
import com.sendgrid.helpers.mail.objects.MailSettings;
import com.sendgrid.helpers.mail.objects.Personalization;
import com.sendgrid.helpers.mail.objects.Setting;
import org.testng.annotations.Test;

import static org.assertj.core.api.Assertions.assertThat;

public class SendGridSandboxIT {

    @Test
    public void should_return_200_and_deliver_nothing_when_sent_in_sandbox_mode() throws Exception {
        Notifier notifier = Notifier.sandbox();

        Response response = notifier.sendWelcome("jane@acme.test", "Jane",
            "https://app.flexinvest.test/activate?token=abc123");

        // 200 under sandbox (a real, accepted send returns 202); the email is never delivered.
        assertThat(response.getStatusCode()).isEqualTo(200);
    }

    @Test
    public void should_reject_when_template_id_is_malformed() throws Exception {
        SendGrid sg = new SendGrid(SendGridConfig.apiKey());

        Mail mail = new Mail();
        mail.setFrom(new Email("no-reply@flexinvest.test"));
        mail.setTemplateId("not-a-template"); // not a valid dynamic-template ID
        Personalization p = new Personalization();
        p.addTo(new Email("jane@acme.test"));
        mail.addPersonalization(p);
        Setting sandboxMode = new Setting();
        sandboxMode.setEnable(true);
        MailSettings mailSettings = new MailSettings();
        mailSettings.setSandboxMode(sandboxMode);
        mail.setMailSettings(mailSettings);

        Request request = new Request();
        request.setMethod(Method.POST);
        request.setEndpoint("mail/send");
        request.setBody(mail.build());
        Response response = sg.api(request);

        // SendGrid validates and rejects with a 4xx (the SDK returns the status; it does not throw).
        assertThat(response.getStatusCode()).isGreaterThanOrEqualTo(400);
    }
}
```

## Rules

### Sandbox mode (validate-only, no delivery)
- Sandbox lives on the **message** (`mail.setMailSettings(...)` with `Setting.setEnable(true)`), not the client. Apply it in the `Notifier`, not in tests — tests never build `MailSettings`.
- A valid sandbox send returns **`200`**, a real accepted send returns **`202`**. Assert `200` in sandbox tests; a `202` means sandbox was **not** actually on (and you may have delivered mail).
- Sandbox proves the **request** is valid — **not** that a human-readable email rendered or was delivered. For body/render/delivery assertions, use the inbox siblings.
- The SDK returns the status code on a `4xx`; it does not throw — assert on `getStatusCode()`, don't expect an exception.

### No wait, no inbox
- There is **no** poll, **no** `waitFor`, **no** `Thread.sleep`. A send is one request/response. If you find yourself waiting for something to arrive, you want a different sibling.
- Nothing to clean up — no inbox, no messages, no per-test isolation. Tests are independent by construction.

### Payload-first assertions
- Make the **offline payload check** the primary assertion: recipient, `from` / `reply-to`, `templateId`, dynamic data, categories — via the `Mail` getters. It needs no key and no network and catches the most common mistakes.
- Use the live sandbox round-trip to add what local checks can't: SendGrid's real validator accepting (or rejecting) the payload.
- Don't assert on rendered HTML or links — nothing rendered. That's an inbox-sibling concern.

### Code quality (per CLAUDE.md)
- Constructor-inject `SendGrid` into the `Notifier`; no `new SendGrid(...)` inside the wrapper's send methods (the `sandbox()` factory is the one composition point).
- `should_x_when_y` test names; one logical assertion per test.

### Secrets
- `SENDGRID_API_KEY` is the **only** secret and is needed **only** for the live sandbox round-trip. Read it lazily (`SendGridConfig.apiKey()`), never in a `@BeforeClass` / field initializer, so the payload check stays key-free. Never commit it; in CI pull it per `qa/cicd/java/skills/ci-pipelines`.

### What NOT to do
- No hardcoded API key.
- No poll / wait / sleep of any kind — this is request/response.
- No asserting `202` in a sandbox test (that means delivery happened).
- No `MailSettings` building in tests — the `Notifier` owns sandbox.
- No body/render/link/attachment assertions — nothing is delivered; use an inbox sibling.
- No eager key read (`@BeforeClass` / field initializer) — it would break the offline payload check.

## Generation steps

1. Read `src/test/java/.../support` for existing base classes and conventions.
2. Confirm `com.sendgrid:sendgrid-java` (+ `mockito-core` for the mock-client test) is on the test classpath and that `SENDGRID_API_KEY` (+ optional `SENDGRID_TEMPLATE_*`, `SENDGRID_FROM`) are wired into the test env for the live check (not committed).
3. Generate:
   - `support/email/SendGridConfig.java`
   - `support/email/Messages.java`
   - `support/email/Notifier.java`
   - Concrete `{Flow}MessageTest.java` (offline) + `{Flow}SandboxIT.java` (live) — at minimum the payload check + the live sandbox round-trip — plus the `build.gradle.kts` dependencies.
4. Run the offline checks anywhere; run the live sandbox tests with `./gradlew test --tests "*SandboxIT"` and `SENDGRID_API_KEY` present.

## Cross-references

- **`qa/java/skills/email-testing`**, **`qa/java/skills/email-testing`**, **`qa/java/skills/email-testing`** — the three inbox siblings. See the four-way pick table: this skill validates the **send request** and delivers nothing; those three assert on a **received** message (real provider / hosted SaaS / self-hosted sink).
- **`qa/typescript/skills/email-testing`** (canonical, `@sendgrid/mail`), **`qa/dotnet/skills/email-testing`** (`SendGrid` NuGet) — the sibling stacks; same builder + `Notifier` shape, same `200`-under-sandbox assertion.
- **`qa/cicd/java/skills/ci-pipelines`** — where these tests run in CI and where the `SENDGRID_API_KEY` secret is sourced (OIDC / encrypted secrets), never hardcoded.
- **`qa/java/skills/test-data-builder`** — build the dynamic-template-data through a builder when it grows past 4 fields.
