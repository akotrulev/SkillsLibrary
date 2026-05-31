---
name: qa-email-testing-mailosaur-dotnet
description: Use when the user asks to assert on real outbound email or SMS in .NET (NUnit) integration or E2E tests using the hosted Mailosaur service + the official `Mailosaur` NuGet SDK — capture signup welcome / OTP / password-reset / magic-link messages delivered to a per-test `{guid}@{serverId}.mailosaur.net` inbox, extract subject / recipient / HTML body / links / OTP codes, download attachments, verify SMS one-time passcodes. Triggers: "verify the welcome email with Mailosaur", "extract the OTP from the reset email", "Mailosaur fixture for the NUnit suite", "assert the magic-link", "check the SMS verification code". Do NOT use for the self-hosted SMTP sink (`qa/email-testing/mailpit/dotnet`), Gmail IMAP polling (`qa/email-testing/gmail-imap/dotnet`), SendGrid sandbox mode (`qa/email-testing/sendgrid-sandbox/dotnet`), or TS / JVM stacks (`qa/email-testing/mailosaur/{typescript,java}`).
---

# QA — Email & SMS Testing with Mailosaur (.NET)

Scaffolds a thin, intent-revealing wrapper over the official `Mailosaur` NuGet SDK plus NUnit fixtures that **await** a specific message in a per-test `{guid}@{serverId}.mailosaur.net` inbox, extract HTML / text body / links / OTP codes, download attachments, and verify SMS. Mailosaur is a **hosted** service: the SUT sends real email through its real provider to a Mailosaur inbox address, and `Messages.GetAsync(...)` blocks until the message arrives or the timeout fires — that built-in wait is the sanctioned wait, so there is **no `Thread.Sleep`** poll loop anywhere in this skill.

## When to use

- Signup / password-reset / magic-link / OTP / receipt flows that need an email assertion against a **real delivery path** (real SMTP/provider → real inbox), not just an SMTP sink
- E2E tests (Playwright .NET / Selenium) that click an emailed link or type an emailed OTP
- Integration tests asserting `From`, `subject` templates, HTML link targets, attachment shape
- **SMS / phone** one-time-passcode flows (same SDK, an SMS-enabled server)
- Teams that want zero local infra in CI — no container, just an API key + server ID secret

## When NOT to use

- Self-hosted SMTP sink, no cloud account, fully offline CI → `qa/email-testing/mailpit/dotnet`
- Polling a real Gmail / Outlook mailbox over IMAP → `qa/email-testing/gmail-imap/dotnet`
- SendGrid sandbox-mode (mail-send API, no delivery) → `qa/email-testing/sendgrid-sandbox/dotnet`
- TS or JVM stacks → `qa/email-testing/mailosaur/{typescript,java}`
- Production deliverability / DKIM / SPF auditing — Mailosaur captures, it is not a relay verifier

## Mailpit vs Mailosaur — pick the right sibling

| | **Mailosaur** (this skill) | **Mailpit** (`qa/email-testing/mailpit/dotnet`) |
|---|---|---|
| Hosting | Hosted SaaS, API key + server ID | Self-hosted container (Testcontainers / compose) |
| Delivery path | **Real** — SUT's real provider delivers to a real inbox | SMTP sink — SUT points its SMTP client at the container |
| Wait primitive | SDK `Messages.GetAsync(..., MessageSearchParams { Timeout })` blocks until arrival | You poll the HTTP search API with a deadline |
| Per-test isolation | Unique `{guid}@{serverId}.mailosaur.net` address (no shared inbox) | `DELETE /api/v1/messages` between tests |
| SMS testing | ✅ same SDK, SMS server | ❌ |
| Secrets | API key + server ID (secret store) | None |
| Offline CI | ❌ needs network to Mailosaur | ✅ fully offline |

Use **Mailosaur** when you want to exercise the real send path or test SMS; use **Mailpit** when you want zero external dependencies and offline CI.

## Inputs needed

Ask at most 2 questions; infer the rest from the test project and existing fixtures.

1. Scenario: signup welcome / OTP / password reset / magic link / SMS code / arbitrary subject match?
2. Where do the `MAILOSAUR_API_KEY` and `MAILOSAUR_SERVER_ID` come from in this environment (CI secret store, user-secrets)? They are **secrets** — never commit them.

## Mailosaur SDK surface (cheat-sheet)

| Call | Purpose |
|---|---|
| `new MailosaurClient(apiKey)` | Construct the client (inject the key; never hardcode) |
| `await client.Messages.GetAsync(serverId, criteria, searchParams)` | **Await** the first message matching `criteria` — blocks until arrival or `searchParams.Timeout` (ms, default 10 000), then throws. This is the wait. |
| `await client.Messages.ListAsync(serverId, options)` | Page recent messages (rarely needed — prefer `GetAsync`) |
| `await client.Messages.DeleteAllAsync(serverId)` | Empty the whole server inbox (use sparingly — see isolation rules) |
| `await client.Files.GetAttachmentAsync(attachmentId)` | Download an attachment as `byte[]` |
| `new SearchCriteria { SentTo, SentFrom, Subject, Body, Match }` | `Match` is `SearchMatchOperator.All` \| `.Any` |
| `message.Html.Links[]` | `{ Text, Href }` — hyperlinks Mailosaur extracted from the HTML |
| `message.Html.Codes[]` / `message.Text.Codes[]` | `{ Value }` — OTP / verification codes Mailosaur auto-detected |
| `message.Html.Body` / `message.Text.Body` | Raw bodies (extract structure; don't substring the whole thing) |
| `message.Attachments[]` | `{ Id, FileName, ContentType, Length }` |

**Inbox-address pattern:** any address `{anything}@{serverId}.mailosaur.net` routes to your server. Per test, generate `{Guid.NewGuid():N}@{serverId}.mailosaur.net` so every test owns a unique recipient and needs no shared-inbox cleanup.

## Templates

### Config — `IntegrationTests/Email/MailosaurOptions.cs`

Secrets come from the environment, validated once. Never inline the key or server ID.

```csharp
namespace IntegrationTests.Email;

public sealed record MailosaurOptions(string ApiKey, string ServerId, TimeSpan Timeout)
{
    public static MailosaurOptions FromEnvironment()
    {
        static string Required(string name) =>
            Environment.GetEnvironmentVariable(name)
                ?? throw new InvalidOperationException($"Missing required env var {name} (Mailosaur secret).");

        int timeoutMs = int.TryParse(Environment.GetEnvironmentVariable("MAILOSAUR_TIMEOUT_MS"), out int ms) ? ms : 20_000;
        return new MailosaurOptions(
            Required("MAILOSAUR_API_KEY"),
            Required("MAILOSAUR_SERVER_ID"),
            TimeSpan.FromMilliseconds(timeoutMs));
    }

    /// <summary>Unique recipient per test → independent tests, no shared-inbox races.</summary>
    public string NewRecipient(string prefix = "qa") => $"{prefix}-{Guid.NewGuid():N}@{ServerId}.mailosaur.net";
}
```

### Intent-revealing wrapper — `IntegrationTests/Email/Mailbox.cs`

Tests never call `Messages.GetAsync` directly. They call `AwaitSignupEmailAsync`, `ExtractVerificationLink`, `ExtractOtp`. The SDK's blocking `GetAsync` is the only wait.

```csharp
using Mailosaur;
using Mailosaur.Models;

namespace IntegrationTests.Email;

public sealed class Mailbox
{
    private readonly MailosaurClient _client;
    private readonly string _serverId;
    private readonly TimeSpan _timeout;

    public Mailbox(MailosaurOptions options)
    {
        _client = new MailosaurClient(options.ApiKey);
        _serverId = options.ServerId;
        _timeout = options.Timeout;
    }

    /// <summary>Await an email by recipient (+ optional subject). Blocks until arrival or timeout.</summary>
    public Task<Message> AwaitEmailAsync(string sentTo, string? subject = null, TimeSpan? timeout = null)
    {
        var criteria = new SearchCriteria { SentTo = sentTo, Subject = subject };
        var searchParams = new MessageSearchParams { Timeout = (int)(timeout ?? _timeout).TotalMilliseconds };
        return _client.Messages.GetAsync(_serverId, criteria, searchParams);
    }

    public Task<Message> AwaitSignupEmailAsync(string sentTo) => AwaitEmailAsync(sentTo, "Welcome");

    /// <summary>Await an SMS to a Mailosaur phone number (SMS-enabled server). Same primitive.</summary>
    public Task<Message> AwaitSmsAsync(string sentTo, TimeSpan? timeout = null)
    {
        var searchParams = new MessageSearchParams { Timeout = (int)(timeout ?? _timeout).TotalMilliseconds };
        return _client.Messages.GetAsync(_serverId, new SearchCriteria { SentTo = sentTo }, searchParams);
    }

    public Task<byte[]> DownloadAttachmentAsync(string attachmentId) => _client.Files.GetAttachmentAsync(attachmentId);

    /// <summary>Hard reset of the whole server inbox. Prefer unique recipients over this.</summary>
    public Task EmptyServerInboxAsync() => _client.Messages.DeleteAllAsync(_serverId);
}
```

### Extractors — `IntegrationTests/Email/EmailExtractors.cs`

Prefer Mailosaur's structured `Links` / `Codes` over hand-rolled regex.

```csharp
using Mailosaur.Models;
using NUnit.Framework;

namespace IntegrationTests.Email;

public static class EmailExtractors
{
    public static string ExtractOtp(Message message)
    {
        string? code = message.Html?.Codes?.FirstOrDefault()?.Value
            ?? message.Text?.Codes?.FirstOrDefault()?.Value;
        if (string.IsNullOrEmpty(code))
        {
            throw new AssertionException($"No verification code found in '{message.Subject}'.");
        }
        return code;
    }

    public static Uri ExtractLink(Message message, string mustContain)
    {
        MessageLink? link = message.Html?.Links?
            .FirstOrDefault(l => l.Href?.Contains(mustContain, StringComparison.OrdinalIgnoreCase) == true);
        if (link?.Href is null)
        {
            throw new AssertionException($"No link containing '{mustContain}' in '{message.Subject}'.");
        }
        return new Uri(link.Href);
    }
}
```

### Fixture base — `IntegrationTests/Fixtures/MailosaurFixture.cs`

```csharp
using IntegrationTests.Email;
using NUnit.Framework;

namespace IntegrationTests.Fixtures;

public abstract class MailosaurFixture
{
    protected MailosaurOptions Options { get; private set; } = null!;
    protected Mailbox Mail { get; private set; } = null!;

    [OneTimeSetUp]
    public void InitMailosaur()
    {
        Options = MailosaurOptions.FromEnvironment();
        Mail = new Mailbox(Options);
    }
}
```

### Test — signup welcome

```csharp
[Test]
[AllureFeature("Authentication")]
public async Task Should_SendWelcomeEmailWithActivationLink_When_UserSignsUp()
{
    string email = Options.NewRecipient("signup");

    HttpResponseMessage response = await _client.PostAsJsonAsync("/auth/signup", new
    {
        Email = email,
        Password = "Str0ng!Passw0rd",
    });
    response.EnsureSuccessStatusCode();

    Message message = await Mail.AwaitSignupEmailAsync(email);
    Uri activation = EmailExtractors.ExtractLink(message, "/activate?token=");

    Assert.That(activation.Query, Does.Contain("token="));
}
```

### Test — OTP password reset

```csharp
[Test]
public async Task Should_LogIn_When_ResetOtpEntered()
{
    string email = Options.NewRecipient("reset");
    await _client.PostAsJsonAsync("/auth/reset", new { Email = email });

    Message message = await Mail.AwaitEmailAsync(email, "Reset code");
    string otp = EmailExtractors.ExtractOtp(message);

    HttpResponseMessage verify = await _client.PostAsJsonAsync("/auth/verify-reset", new
    {
        Email = email,
        Otp = otp,
        NewPassword = "Brand-N3w!",
    });

    Assert.That(verify.StatusCode, Is.EqualTo(System.Net.HttpStatusCode.OK));
}
```

### Test — SMS one-time passcode

```csharp
[Test]
public async Task Should_SendSmsCode_When_PhoneVerificationRequested()
{
    // Mailosaur provisions a dedicated test phone number on an SMS-enabled server.
    string phoneNumber = Environment.GetEnvironmentVariable("MAILOSAUR_PHONE_NUMBER")!;
    await _client.PostAsJsonAsync("/auth/phone/verify", new { PhoneNumber = phoneNumber });

    Message sms = await Mail.AwaitSmsAsync(phoneNumber);

    Assert.That(EmailExtractors.ExtractOtp(sms), Does.Match(@"^\d{6}$"));
}
```

### Test — attachment

```csharp
[Test]
public async Task Should_AttachPdfInvoice_When_InvoiceEmailed()
{
    string email = Options.NewRecipient("billing");
    await _client.PostAsJsonAsync($"/invoices/{invoiceId}/email", new { To = email });

    Message message = await Mail.AwaitEmailAsync(email, "Invoice");
    Mailosaur.Models.Attachment pdf = message.Attachments.Single(a => a.ContentType == "application/pdf");

    byte[] bytes = await Mail.DownloadAttachmentAsync(pdf.Id);

    Assert.Multiple(() =>
    {
        Assert.That(pdf.FileName, Does.StartWith("invoice-"));
        Assert.That(bytes[..4], Is.EqualTo(new byte[] { 0x25, 0x50, 0x44, 0x46 })); // %PDF magic
    });
}
```

## Rules

### Inbox isolation
- **Unique recipient per test**: `{guid}@{serverId}.mailosaur.net` via `Options.NewRecipient()`. Tests stay independent and parallel-safe with no shared cleanup.
- Prefer unique recipients over `Messages.DeleteAllAsync(serverId)` — `DeleteAll` wipes the **whole** server and will race a parallel suite.
- Search by `SentTo` (+ `Subject`), never "the latest message in the server".

### Waiting
- **The wait is `Messages.GetAsync(..., MessageSearchParams { Timeout })`** — it blocks until a match arrives, then throws on timeout. Never `Thread.Sleep` / `Task.Delay` around it.
- Set `Timeout` to a real SLA (default 20s here). Bump per call with a comment, not globally.
- Async all the way: every call is awaited; no `.Result` / `.GetAwaiter().GetResult()`.

### Body assertions
- Assert on Mailosaur's **structured** output: `Html.Links[].Href`, `Html.Codes[].Value`. Don't substring-match the full `Html.Body`.
- Assert a **user-visible outcome** of the link/OTP, not the raw string shape.
- Visual / template-shape checks → `qa/visual-regression/playwright-snapshots/dotnet`.

### Attachments
- Validate content type **and** magic bytes for binaries. Check `Length` before downloading large files.

### Secrets
- `MAILOSAUR_API_KEY` + `MAILOSAUR_SERVER_ID` are secrets. Read from env / user-secrets / secret store; never in code or committed `appsettings`. In CI pull them per `qa/ci-pipelines/github-actions/dotnet` (OIDC / encrypted secrets).

### What NOT to do
- No hardcoded API key or server ID.
- No `Thread.Sleep` around `GetAsync` — its `Timeout` is the wait.
- No `DeleteAllAsync` as a substitute for unique recipients in parallel suites.
- No assertions on the entire HTML body string.
- No `ListAsync` + client-side filtering when `GetAsync` with criteria does it server-side.

## Generation steps

1. Read existing `IntegrationTests/Fixtures/` for the SUT bootstrap (`WebApplicationFactory`) and house style.
2. Confirm the `Mailosaur` NuGet package is referenced and that `MAILOSAUR_API_KEY` / `MAILOSAUR_SERVER_ID` are wired into the test env (not committed).
3. Generate:
   - `IntegrationTests/Email/MailosaurOptions.cs`
   - `IntegrationTests/Email/Mailbox.cs`
   - `IntegrationTests/Email/EmailExtractors.cs`
   - `IntegrationTests/Fixtures/MailosaurFixture.cs`
   - Concrete `IntegrationTests/{Flow}EmailTests.cs` per scenario.
4. Run `dotnet test --filter "FullyQualifiedName~Email"` with the secrets present.

## Cross-references

- **`qa/email-testing/mailpit/dotnet`** — the self-hosted SMTP-sink sibling. Pick Mailpit for offline CI and zero external deps; pick Mailosaur (here) for real-delivery and SMS. See the comparison table above.
- **`qa/email-testing/mailosaur/typescript`** (canonical), **`qa/email-testing/mailosaur/java`** — sibling stacks; same wrapper shape, same `GetAsync` wait.
- **`qa/ci-pipelines/github-actions/dotnet`** — where these tests run in CI and where the `MAILOSAUR_API_KEY` / `MAILOSAUR_SERVER_ID` secrets are sourced (OIDC / encrypted secrets), never hardcoded.
- **`qa/test-data-builder/dotnet`** — generate unique per-test recipients through a builder.
- **`qa/db-testing/testcontainers/dotnet`** — signup creates a DB row *and* sends an email; assert both.

## Sources synthesized (research-first per CLAUDE.md)

- [mailosaur/mailosaur-dotnet — README](https://github.com/mailosaur/mailosaur-dotnet) — `MailosaurClient`, `Messages.Get`/`GetAsync`, `Files.GetAttachment`, `SearchCriteria`, message shape.
- [How to test email and SMS in .NET | Mailosaur docs](https://mailosaur.com/docs/email-testing/dotnet/getting-started) — `MessageSearchParams` timeout, inbox-address pattern, NUnit/XUnit/MSTest support.
- [mailosaur — NuGet](https://www.nuget.org/packages/mailosaur) — package version surface.
- [Email and SMS Testing API | Mailosaur](https://mailosaur.com/docs/api) — `html.links` / `html.codes` / attachment fields.

## Changelog

- 2026-05-31: Ported from the canonical `qa/email-testing/mailosaur/typescript` (`qa/GAP-ANALYSIS.md` row 5). Re-expressed in the `Mailosaur` NuGet SDK + NUnit; preserved the blocking `Messages.GetAsync` wait and the unique-recipient isolation model.
