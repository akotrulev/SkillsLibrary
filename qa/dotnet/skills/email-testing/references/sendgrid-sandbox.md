# QA — Validate Outbound Mail via SendGrid Sandbox Mode (.NET)

Scaffolds a thin, intent-revealing wrapper over the official `SendGrid` NuGet SDK plus NUnit fixtures that **validate the SUT's send request without delivering any email**. With `MailSettings.SandboxMode.Enable = true`, SendGrid runs its real validator over the form, type, and shape of the request — template IDs, personalizations, dynamic template data, `from` / `reply-to`, categories — accepts a valid one with **`HttpStatusCode.OK` (200)** (note: not the `Accepted` (202) a real send returns), and **delivers nothing**. A malformed request surfaces as a **`4xx` with an error body**.

This is the **"no inbox at all"** sibling. The other three email skills all assert on a *captured / delivered* message; **this one never produces a received message** — there is no SMTP sink, no IMAP poll, no `Messages.GetAsync`. Two consequences shape the whole skill:

- **There is no wait — at all.** No `WaitForAsync`, no poll loop, no `Thread.Sleep` / `Task.Delay`. A send under sandbox mode is a single request/response: you `await client.SendEmailAsync(msg)` and assert on `response.StatusCode`. There is nothing to arrive, so there is nothing to wait for.
- **The strongest check needs no network and no secret.** Because the request is built locally before it goes anywhere, the deterministic assertion is on the **constructed `SendGridMessage` itself** — recipient, `TemplateId`, template data, categories, `From` / `ReplyTo`. That test runs offline, in milliseconds, with no `SENDGRID_API_KEY`. The sandbox round-trip then adds one thing the local check can't: confirmation that SendGrid's **real** validator accepts the payload (catching template-ID typos, malformed personalizations, bad dynamic-data shape) — without sending an email or needing a mailbox.

## When to use

- Asserting the SUT builds a **well-formed** transactional send: correct template ID, dynamic data, recipients, `From` / `ReplyTo`, categories
- Catching template-ID typos and malformed personalizations / dynamic-data shape against SendGrid's **real** validator, in CI, without delivering mail or owning a mailbox
- Unit/integration-testing the mail-notification layer (a `Notifier`) in isolation — inject a fake `ISendGridClient` to assert the exact payload offline, or flip sandbox on for the live validate round-trip
- Fast, deterministic CI where standing up an inbox (IMAP / Mailosaur / Mailpit) is overkill because you only need "is our send request valid and accepted?"

## When NOT to use

- You must assert on a **delivered / received** message (body rendered, link clickable, OTP extracted, attachment present) — sandbox mode delivers **nothing**:
  - Real provider mailbox over IMAP → `qa/dotnet/skills/email-testing`
  - Hosted SaaS inbox + SMS → `qa/dotnet/skills/email-testing`
  - Self-hosted SMTP sink, offline CI → `qa/dotnet/skills/email-testing`
- The SUT doesn't send through SendGrid's Mail Send API (uses raw SMTP, SES, etc.) → use one of the inbox siblings
- Production deliverability / DKIM / SPF / template-render auditing — sandbox proves the **request** is valid, **not** that a human-readable email rendered or was delivered
- TS or JVM stacks → `qa/{typescript,java}/skills/email-testing`

## Inputs needed

Ask at most 2 questions; infer the rest from the test project and existing fixtures.

1. Scenario: welcome / password-reset / arbitrary transactional template — and which dynamic-data keys does it carry?
2. Where does `SENDGRID_API_KEY` come from in this environment (CI secret store, user-secrets)? It is the **one** secret and is needed **only** for the live sandbox round-trip — the payload check needs no key. Never commit it.

## SendGrid SDK surface (cheat-sheet — `SendGrid` NuGet)

| Call | Purpose |
|---|---|
| `new SendGridClient(apiKey)` (implements `ISendGridClient`) | The client; inject `ISendGridClient` for DI and fakes — never hardcode the key |
| `await client.SendEmailAsync(msg, ct)` | Send → `Response`. Under sandbox: validates, delivers nothing |
| `new SendGridMessage()` | The message; `SetFrom`, `AddTo`, `SetReplyTo`, `SetTemplateId`, `SetTemplateData`, `AddCategory` |
| `msg.SetTemplateId("d-...")` | Dynamic template ID |
| `msg.SetTemplateData(object)` | Dynamic template data → stored on `Personalizations[0].TemplateData` |
| `msg.MailSettings = new MailSettings { SandboxMode = new SandboxMode { Enable = true } }` | **Sandbox**: full validation, no delivery → `200` (real send → `202`) |
| `msg.Personalizations[0].Tos` / `.TemplateData` | The recipients + data to assert on locally |
| `response.StatusCode` | `HttpStatusCode.OK` (200) under sandbox; `Accepted` (202) for a real send; `4xx` on a malformed request |

**Key point:** sandbox mode lives on the **message** (`MailSettings.SandboxMode`), not the client. Keep the message *builders* pure (no key, no client, no sandbox flag) so they serve production too; let the `Notifier` decide whether to flip sandbox on — that way tests assert on the pure payload offline and never touch `MailSettings` themselves.

## Templates

### Config — `IntegrationTests/Email/SendGridOptions.cs`

Template IDs + `From` are non-secret defaults (so the payload check needs no secret). The API key is read lazily and **only** when a live send actually happens.

```csharp
namespace IntegrationTests.Email;

public sealed record SendGridOptions(
    string From, string ReplyTo, string WelcomeTemplateId, string PasswordResetTemplateId)
{
    public static SendGridOptions Defaults() => new(
        Environment.GetEnvironmentVariable("SENDGRID_FROM") ?? "no-reply@flexinvest.test",
        Environment.GetEnvironmentVariable("SENDGRID_REPLY_TO") ?? "support@flexinvest.test",
        Environment.GetEnvironmentVariable("SENDGRID_TEMPLATE_WELCOME") ?? "d-welcome00000000000000000000000",
        Environment.GetEnvironmentVariable("SENDGRID_TEMPLATE_RESET") ?? "d-reset000000000000000000000000");

    /// <summary>The ONE secret, read lazily — only the live sandbox round-trip needs it.</summary>
    public static string ApiKey() =>
        Environment.GetEnvironmentVariable("SENDGRID_API_KEY")
            ?? throw new InvalidOperationException("Missing required env var SENDGRID_API_KEY (SendGrid secret).");
}
```

### Pure message builders — `IntegrationTests/Email/Messages.cs`

No client, no key, no sandbox flag — just the `SendGridMessage` the SUT would send. This is what the deterministic, offline, no-secret test asserts on. Dynamic data is a `Dictionary<string, object>` so the test can index it back cleanly.

```csharp
using SendGrid.Helpers.Mail;

namespace IntegrationTests.Email;

public static class Messages
{
    public static SendGridMessage Welcome(SendGridOptions opts, string to, string firstName, string activationUrl)
    {
        var msg = new SendGridMessage();
        msg.SetFrom(new EmailAddress(opts.From));
        msg.SetReplyTo(new EmailAddress(opts.ReplyTo));
        msg.AddTo(new EmailAddress(to));
        msg.SetTemplateId(opts.WelcomeTemplateId);
        msg.SetTemplateData(new Dictionary<string, object>
        {
            ["first_name"] = firstName,
            ["activation_url"] = activationUrl,
        });
        msg.AddCategory("welcome");
        msg.AddCategory("transactional");
        return msg;
    }

    public static SendGridMessage PasswordReset(SendGridOptions opts, string to, string otp)
    {
        var msg = new SendGridMessage();
        msg.SetFrom(new EmailAddress(opts.From));
        msg.SetReplyTo(new EmailAddress(opts.ReplyTo));
        msg.AddTo(new EmailAddress(to));
        msg.SetTemplateId(opts.PasswordResetTemplateId);
        msg.SetTemplateData(new Dictionary<string, object> { ["otp"] = otp });
        msg.AddCategory("password-reset");
        msg.AddCategory("transactional");
        return msg;
    }
}
```

### Intent-revealing wrapper — `IntegrationTests/Email/Notifier.cs`

Tests call `SendWelcomeAsync` / `SendPasswordResetAsync`, never `SendEmailAsync` or `MailSettings`. The `Notifier` injects `ISendGridClient` (constructor injection — pass a fake in unit tests) and owns the sandbox decision. `BuildWelcome` is exposed so a test can assert the final, sandbox-applied message without sending.

```csharp
using SendGrid;
using SendGrid.Helpers.Mail;

namespace IntegrationTests.Email;

public sealed class Notifier
{
    private readonly ISendGridClient _client;
    private readonly SendGridOptions _options;
    private readonly bool _sandbox;

    public Notifier(ISendGridClient client, SendGridOptions options, bool sandbox = false)
    {
        _client = client;
        _options = options;
        _sandbox = sandbox;
    }

    /// <summary>Apply sandbox mode at send time so the pure builders stay production-usable.</summary>
    private SendGridMessage Prepare(SendGridMessage msg)
    {
        if (_sandbox)
        {
            msg.MailSettings = new MailSettings { SandboxMode = new SandboxMode { Enable = true } };
        }
        return msg;
    }

    public SendGridMessage BuildWelcome(string to, string firstName, string activationUrl) =>
        Prepare(Messages.Welcome(_options, to, firstName, activationUrl));

    public Task<Response> SendWelcomeAsync(
        string to, string firstName, string activationUrl, CancellationToken ct = default) =>
        _client.SendEmailAsync(BuildWelcome(to, firstName, activationUrl), ct);

    public Task<Response> SendPasswordResetAsync(string to, string otp, CancellationToken ct = default) =>
        _client.SendEmailAsync(Prepare(Messages.PasswordReset(_options, to, otp)), ct);
}

public static class SandboxNotifierFactory
{
    /// <summary>Canonical live test entry-point: a real client in sandbox mode. Reads the key lazily.</summary>
    public static Notifier Create() =>
        new(new SendGridClient(SendGridOptions.ApiKey()), SendGridOptions.Defaults(), sandbox: true);
}
```

### Test — deterministic payload check (offline, no secret)

The strongest assertion runs without the network or the API key: the builder produced the right shape. Multiple `Assert` calls, one behavior — "the welcome message is well-formed".

```csharp
using NUnit.Framework;
using SendGrid.Helpers.Mail;

namespace IntegrationTests.Email;

[TestFixture]
public class WelcomeMessageTests
{
    [Test]
    public void Should_AddressTemplatedWelcomeWithActivationData_When_Built()
    {
        SendGridOptions opts = SendGridOptions.Defaults();

        SendGridMessage msg = Messages.Welcome(opts, "jane@acme.test", "Jane",
            "https://app.flexinvest.test/activate?token=abc123");

        var data = (IDictionary<string, object>)msg.Personalizations[0].TemplateData!;
        Assert.Multiple(() =>
        {
            Assert.That(msg.Personalizations[0].Tos[0].Email, Is.EqualTo("jane@acme.test"));
            Assert.That(msg.From.Email, Is.EqualTo(opts.From));
            Assert.That(msg.TemplateId, Is.EqualTo(opts.WelcomeTemplateId));
            Assert.That(data["activation_url"], Does.Contain("token="));
            Assert.That(msg.Categories, Does.Contain("welcome"));
        });
    }
}
```

### Test — Notifier applies sandbox, sends valid payload (offline, fake client)

Constructor injection lets us capture the exact `SendGridMessage` handed to `SendEmailAsync` — sandbox flag included — with zero network and no secret. (NSubstitute; Moq is equivalent.)

```csharp
using System.Net;
using NSubstitute;
using NUnit.Framework;
using SendGrid;
using SendGrid.Helpers.Mail;

namespace IntegrationTests.Email;

[TestFixture]
public class NotifierSandboxTests
{
    [Test]
    public async Task Should_EnableSandboxOnTheSentMessage_When_SandboxNotifier()
    {
        SendGridMessage? captured = null;
        ISendGridClient client = Substitute.For<ISendGridClient>();
        client.SendEmailAsync(Arg.Do<SendGridMessage>(m => captured = m), Arg.Any<CancellationToken>())
            .Returns(new Response(HttpStatusCode.OK, null, null));
        var notifier = new Notifier(client, SendGridOptions.Defaults(), sandbox: true);

        await notifier.SendPasswordResetAsync("jane@acme.test", "123456");

        Assert.That(captured!.MailSettings.SandboxMode.Enable, Is.True);
    }
}
```

### Test — live sandbox round-trip (SendGrid's real validator accepts it)

The only test that touches the network and needs the key. No wait, no inbox — just assert the status code. `OK` (200) means the payload is valid and **nothing was delivered**.

```csharp
using System.Net;
using NUnit.Framework;
using SendGrid;

namespace IntegrationTests.Email;

[TestFixture]
public class SendGridSandboxTests
{
    [Test]
    public async Task Should_Return200AndDeliverNothing_When_SentInSandboxMode()
    {
        Notifier notifier = SandboxNotifierFactory.Create();

        Response response = await notifier.SendWelcomeAsync("jane@acme.test", "Jane",
            "https://app.flexinvest.test/activate?token=abc123");

        // 200 OK under sandbox (a real, accepted send returns 202 Accepted); the email is never delivered.
        Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.OK));
    }

    [Test]
    public async Task Should_Reject_When_TemplateIdIsMalformed()
    {
        var client = new SendGridClient(SendGridOptions.ApiKey());
        var msg = new SendGridMessage();
        msg.SetFrom(new SendGrid.Helpers.Mail.EmailAddress("no-reply@flexinvest.test"));
        msg.AddTo(new SendGrid.Helpers.Mail.EmailAddress("jane@acme.test"));
        msg.SetTemplateId("not-a-template"); // not a valid dynamic-template ID
        msg.MailSettings = new SendGrid.Helpers.Mail.MailSettings
        {
            SandboxMode = new SendGrid.Helpers.Mail.SandboxMode { Enable = true },
        };

        Response response = await client.SendEmailAsync(msg);

        // SendGrid validates and rejects with a 4xx (the SDK returns the status; it does not throw).
        Assert.That((int)response.StatusCode, Is.GreaterThanOrEqualTo(400));
    }
}
```

## Rules

### Sandbox mode (validate-only, no delivery)
- Sandbox lives on the **message** (`MailSettings.SandboxMode.Enable = true`), not the client. Apply it in the `Notifier`, not in tests — tests never touch `MailSettings`.
- A valid sandbox send returns **`OK` (200)**, a real accepted send returns **`Accepted` (202)**. Assert `OK` in sandbox tests; a `202` means sandbox was **not** actually on (and you may have delivered mail).
- Sandbox proves the **request** is valid — **not** that a human-readable email rendered or was delivered. For body/render/delivery assertions, use the inbox siblings.
- The SDK returns the status code on a `4xx`; it does not throw — assert on `response.StatusCode`, don't expect an exception.

### No wait, no inbox
- There is **no** poll, **no** `WaitForAsync`, **no** `Thread.Sleep` / `Task.Delay`. A send is one request/response. If you find yourself waiting for something to arrive, you want a different sibling.
- Nothing to clean up — no inbox, no messages, no per-test isolation. Tests are independent by construction.

### Payload-first assertions
- Make the **offline payload check** the primary assertion: recipient, `From` / `ReplyTo`, `TemplateId`, template data, categories. It needs no key and no network and catches the most common mistakes.
- Use the live sandbox round-trip to add what local checks can't: SendGrid's real validator accepting (or rejecting) the payload.
- Don't assert on rendered HTML or links — nothing rendered. That's an inbox-sibling concern.

### Code quality (per CLAUDE.md)
- Constructor-inject `ISendGridClient` into the `Notifier`; no `new SendGridClient(...)` inside the wrapper's methods.
- Async all the way: every send awaited; no `.Result` / `.GetAwaiter().GetResult()`.
- `Should_X_When_Y` test names; one logical assertion per test.

### Secrets
- `SENDGRID_API_KEY` is the **only** secret and is needed **only** for the live sandbox round-trip. Read it lazily (`SendGridOptions.ApiKey()`), never at field-initializer / fixture-setup time, so the payload check stays key-free. Never commit it; in CI pull it per `qa/cicd/dotnet/skills/ci-pipelines`.

### What NOT to do
- No hardcoded API key.
- No poll / wait / sleep of any kind — this is request/response.
- No asserting `202` in a sandbox test (that means delivery happened).
- No `MailSettings` poking in tests — the `Notifier` owns sandbox.
- No body/render/link/attachment assertions — nothing is delivered; use an inbox sibling.
- No eager key read (field initializer / `[OneTimeSetUp]`) — it would break the offline payload check.

## Generation steps

1. Read existing `IntegrationTests/` for the SUT bootstrap and house style.
2. Confirm the `SendGrid` NuGet package is referenced (and `NSubstitute` for the fake-client test) and that `SENDGRID_API_KEY` (+ optional `SENDGRID_TEMPLATE_*`, `SENDGRID_FROM`) are wired into the test env for the live check (not committed).
3. Generate:
   - `IntegrationTests/Email/SendGridOptions.cs`
   - `IntegrationTests/Email/Messages.cs`
   - `IntegrationTests/Email/Notifier.cs`
   - Concrete `IntegrationTests/Email/{Flow}MessageTests.cs` + `{Flow}SandboxTests.cs` — at minimum the offline payload check + the live sandbox round-trip.
4. Run the offline checks anywhere; run the live sandbox tests with `dotnet test --filter "FullyQualifiedName~Sandbox"` and `SENDGRID_API_KEY` present.

## Cross-references

- **`qa/dotnet/skills/email-testing`**, **`qa/dotnet/skills/email-testing`**, **`qa/dotnet/skills/email-testing`** — the three inbox siblings. See the four-way pick table: this skill validates the **send request** and delivers nothing; those three assert on a **received** message (real provider / hosted SaaS / self-hosted sink).
- **`qa/typescript/skills/email-testing`** (canonical, `@sendgrid/mail`), **`qa/java/skills/email-testing`** (`com.sendgrid:sendgrid-java`) — the sibling stacks; same builder + `Notifier` shape, same `200`-under-sandbox assertion.
- **`qa/cicd/dotnet/skills/ci-pipelines`** — where these tests run in CI and where the `SENDGRID_API_KEY` secret is sourced (OIDC / encrypted secrets), never hardcoded.
- **`qa/dotnet/skills/test-data-builder`** — build the template-data dictionaries through a builder when they grow past 4 fields.
