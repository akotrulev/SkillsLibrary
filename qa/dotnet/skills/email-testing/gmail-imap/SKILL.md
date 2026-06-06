---
name: qa-email-testing-gmail-imap-dotnet
description: Use when the user asks to assert on email delivered to a *real* provider mailbox (Gmail / Outlook / any IMAP account) in .NET (NUnit) integration or E2E tests by polling over IMAP with MailKit's `ImapClient` — find a signup welcome / OTP / password-reset / magic-link message by To + Subject + `since`, extract HTML / text body / links / OTP codes from the `MimeMessage`, download attachments, then clean up via IMAP flags. Triggers: "poll the real Gmail inbox over IMAP", "read the verification email from our test Gmail account with MailKit", "ImapClient fixture for the NUnit suite", "extract the OTP from the password-reset email in the real mailbox". Do NOT use for the self-hosted SMTP sink (`qa/dotnet/skills/email-testing/mailpit`), the hosted Mailosaur sandbox (`qa/dotnet/skills/email-testing/mailosaur`), SendGrid sandbox mode (`qa/dotnet/skills/email-testing/sendgrid-sandbox`), or TS / JVM stacks (`qa/{typescript,java}/skills/email-testing/gmail-imap`).
---

# QA — Email Testing against a Real Mailbox over IMAP (.NET)

Scaffolds a thin, intent-revealing wrapper over MailKit's `ImapClient` plus NUnit fixtures that **poll a real provider mailbox** (Gmail / Outlook / any IMAP server) for a specific message — by recipient alias + subject + `since` time bound — extract HTML / text body / links / OTP codes from the parsed `MimeMessage`, download attachments, and clean up by flagging the message `\Seen` / `\Deleted` rather than wiping an inbox.

This is the sibling for flows that must exercise the **genuine provider inbox** — real MX, real spam/routing, real provider quirks — not an SMTP sink or a test-SaaS server. Two consequences shape the whole skill:

- **There is no per-test unique-inbox trick** (no `{guid}@{serverId}.mailosaur.net`) and **no `DELETE all` HTTP API** (no Mailpit wipe). Isolation comes from **Gmail `+tag` / dot aliases** — `youraccount+{guid}@gmail.com` all land in the *one* real inbox — plus a **`since` time bound** and a **server-side search by To + Subject**. Cleanup is per-message via IMAP flags (`MessageFlags.Seen` / `MessageFlags.Deleted` + `ExpungeAsync`), not a wipe.
- **No SDK "blocks until arrived" primitive exists.** The wait **is** a real **poll-with-deadline loop** over the IMAP search — but still **no `Thread.Sleep` / `Task.Delay`-only wait**: poll the search on an interval against a deadline (the same `WaitForAsync` shape as `qa/dotnet/skills/email-testing/mailpit`). Real-provider delivery is slower, so the default budget is larger (~25s).

## When to use

- Signup / password-reset / magic-link / OTP flows that must hit a **real provider mailbox** over IMAP (genuine deliverability path, not a sink or SaaS capture)
- Teams already owning a dedicated test Gmail / Outlook / M365 account they want to drive from CI
- E2E tests (Playwright .NET / Selenium) that click an emailed link or type an emailed OTP read from the real inbox
- Integration tests asserting `From`, subject templates, HTML link targets, attachment shape on real delivery

## When NOT to use

- Self-hosted SMTP sink, zero external deps, fully offline CI → `qa/dotnet/skills/email-testing/mailpit`
- Hosted sandbox with per-test inboxes + a blocking SDK wait + SMS → `qa/dotnet/skills/email-testing/mailosaur`
- SendGrid sandbox-mode (mail-send API, no delivery) → `qa/dotnet/skills/email-testing/sendgrid-sandbox`
- TS or JVM stacks → `qa/{typescript,java}/skills/email-testing/gmail-imap`
- Production deliverability / DKIM / SPF auditing — this polls a mailbox, it is not a relay verifier

## gmail-imap vs mailosaur vs mailpit — pick the right sibling

| | **gmail-imap** (this skill) | **mailosaur** (`qa/dotnet/skills/email-testing/mailosaur`) | **mailpit** (`qa/dotnet/skills/email-testing/mailpit`) |
|---|---|---|---|
| What it hits | A **real** provider mailbox over IMAP | Hosted SaaS capture inbox | Self-hosted SMTP **sink** (container) |
| Delivery path | Real MX → real inbox | Real provider → Mailosaur inbox | SUT points SMTP at the sink |
| Wait primitive | **Poll IMAP search** with a deadline | SDK `Messages.GetAsync(..., Timeout)` blocks | Poll HTTP search with a deadline |
| Per-test isolation | `+tag` alias into one inbox + `since` bound | Unique `{guid}@{serverId}.mailosaur.net` | `DELETE /api/v1/messages` between tests |
| Cleanup | Flag `Seen` / `Deleted` + expunge (per message) | (unique address — none needed) | Wipe-all API |
| Secrets | Mailbox address + **App Password** | API key + server ID | None |
| Offline CI | ❌ needs network to the provider | ❌ needs network to Mailosaur | ✅ fully offline |

Pick **gmail-imap** when the test must prove mail lands in a genuine provider inbox; **mailosaur** for a frictionless real-delivery path with per-test inboxes and SMS; **mailpit** for offline, zero-dependency CI.

## Inputs needed

Ask at most 2 questions; infer the rest from the test project and existing fixtures.

1. Scenario: signup welcome / OTP / password reset / magic link / arbitrary subject match?
2. Where do `IMAP_USER` (mailbox address) and `IMAP_PASSWORD` (Gmail **App Password**, or an OAuth2 XOAUTH2 token) come from in this environment? They are **secrets** — never commit them.

## IMAP surface (cheat-sheet — MailKit)

| Call | Purpose |
|---|---|
| `using var client = new ImapClient();` | Construct (disposable) |
| `await client.ConnectAsync("imap.gmail.com", 993, SecureSocketOptions.SslOnConnect, ct)` | TLS-on-connect session |
| `await client.AuthenticateAsync(user, appPassword, ct)` | App Password auth (or `SaslMechanismOAuth2` for XOAUTH2) |
| `await client.Inbox.OpenAsync(FolderAccess.ReadWrite, ct)` | Open INBOX (read-write so flags/expunge work) |
| `await client.Inbox.SearchAsync(query, ct)` | **Server-side** search → `IList<UniqueId>` |
| `SearchQuery.ToContains(alias).And(SearchQuery.SubjectContains(s)).And(SearchQuery.DeliveredAfter(since))` | To + Subject + since |
| `await client.Inbox.GetMessageAsync(uid, ct)` | Fetch → `MimeMessage` (`HtmlBody`, `TextBody`, `Attachments`) |
| `await client.NoOpAsync(ct)` | Refresh folder state between polls (see new mail) |
| `await client.Inbox.AddFlagsAsync(uid, MessageFlags.Seen, true, ct)` | Mark processed (cleanup, not a wipe) |
| `await client.Inbox.AddFlagsAsync(uid, MessageFlags.Deleted, true, ct)` + `ExpungeAsync` | Per-message delete |
| `await client.DisconnectAsync(true, ct)` | Close the session (always, in teardown) |

**`+tag` alias pattern:** Gmail (and many providers) route `youraccount+{anything}@gmail.com` and dotted variants to the *one* real inbox, but the `+tag` is preserved in the `To` header — so per test, send to `${base}+{guid}` and search server-side by that exact `To`. Combined with a `since` lower bound (test start time), every test owns a unique, time-bounded slice of the shared inbox with no wipe.

## Templates

### Config — `IntegrationTests/Email/ImapOptions.cs`

Secrets come from the environment, validated once. Never inline the address or App Password.

```csharp
namespace IntegrationTests.Email;

public sealed record ImapOptions(
    string Host, int Port, string User, string Password, TimeSpan Timeout, TimeSpan PollInterval)
{
    public static ImapOptions FromEnvironment()
    {
        static string Required(string name) =>
            Environment.GetEnvironmentVariable(name)
                ?? throw new InvalidOperationException($"Missing required env var {name} (IMAP secret).");

        int timeoutMs = int.TryParse(Environment.GetEnvironmentVariable("IMAP_TIMEOUT_MS"), out int t) ? t : 25_000;
        int pollMs = int.TryParse(Environment.GetEnvironmentVariable("IMAP_POLL_MS"), out int p) ? p : 2_000;
        return new ImapOptions(
            Environment.GetEnvironmentVariable("IMAP_HOST") ?? "imap.gmail.com",
            int.TryParse(Environment.GetEnvironmentVariable("IMAP_PORT"), out int port) ? port : 993,
            Required("IMAP_USER"),          // e.g. flexinvest.qa@gmail.com
            Required("IMAP_PASSWORD"),      // Gmail App Password (or XOAUTH2 token)
            TimeSpan.FromMilliseconds(timeoutMs),
            TimeSpan.FromMilliseconds(pollMs));
    }

    /// <summary>Per-test `+tag` alias into the one real inbox → independent, searchable, no wipe.</summary>
    public string AliasFor(string prefix = "qa")
    {
        int at = User.IndexOf('@');
        return $"{User[..at]}+{prefix}-{Guid.NewGuid():N}{User[at..]}";
    }
}
```

### Intent-revealing wrapper — `IntegrationTests/Email/Mailbox.cs`

Tests never drive `SearchAsync` / `GetMessageAsync` directly. They call `AwaitSignupEmailAsync`, `AwaitEmailAsync`, `MarkProcessedAsync`. Connection lifecycle (connect once, poll INBOX, disconnect on teardown) lives here — tests never leak an IMAP connection.

```csharp
using MailKit;
using MailKit.Net.Imap;
using MailKit.Search;
using MailKit.Security;
using MimeKit;
using NUnit.Framework;

namespace IntegrationTests.Email;

public sealed record FoundEmail(UniqueId Uid, MimeMessage Message);

public sealed class Mailbox : IAsyncDisposable
{
    private readonly ImapClient _client = new();
    private readonly ImapOptions _options;

    public Mailbox(ImapOptions options) => _options = options;

    public async Task ConnectAsync(CancellationToken ct = default)
    {
        await _client.ConnectAsync(_options.Host, _options.Port, SecureSocketOptions.SslOnConnect, ct);
        await _client.AuthenticateAsync(_options.User, _options.Password, ct);
        await _client.Inbox.OpenAsync(FolderAccess.ReadWrite, ct);
    }

    /// <summary>
    /// Poll the real inbox until a message to <paramref name="sentTo"/> (+ optional subject),
    /// received after <paramref name="since"/>, arrives — or the deadline fires. NOT a fixed
    /// sleep: a deadline loop over the server-side IMAP search, interval-paced.
    /// </summary>
    public async Task<FoundEmail> AwaitEmailAsync(
        string sentTo, string? subject = null, DateTime? since = null,
        TimeSpan? timeout = null, CancellationToken ct = default)
    {
        TimeSpan budget = timeout ?? _options.Timeout;
        DateTime sinceUtc = since ?? DateTime.UtcNow.AddMinutes(-1);
        DateTime deadline = DateTime.UtcNow + budget;

        SearchQuery query = SearchQuery.ToContains(sentTo).And(SearchQuery.DeliveredAfter(sinceUtc));
        if (subject is not null) query = query.And(SearchQuery.SubjectContains(subject));

        while (DateTime.UtcNow < deadline)
        {
            ct.ThrowIfCancellationRequested();
            await _client.NoOpAsync(ct); // refresh folder so new mail is visible
            IList<UniqueId> uids = await _client.Inbox.SearchAsync(query, ct);
            if (uids.Count > 0)
            {
                UniqueId uid = uids[^1]; // newest match
                MimeMessage message = await _client.Inbox.GetMessageAsync(uid, ct);
                return new FoundEmail(uid, message);
            }
            await Task.Delay(_options.PollInterval, ct);
        }
        throw new AssertionException(
            $"No message to '{sentTo}'{(subject is null ? "" : $" subject '{subject}'")} within {budget.TotalSeconds:N0}s.");
    }

    public Task<FoundEmail> AwaitSignupEmailAsync(string sentTo, DateTime? since = null, CancellationToken ct = default)
        => AwaitEmailAsync(sentTo, "Welcome", since, ct: ct);

    /// <summary>Cleanup is per-message, not a wipe: flag Seen, or Deleted + expunge.</summary>
    public async Task MarkProcessedAsync(UniqueId uid, bool delete = false, CancellationToken ct = default)
    {
        if (delete)
        {
            await _client.Inbox.AddFlagsAsync(uid, MessageFlags.Deleted, true, ct);
            await _client.Inbox.ExpungeAsync(new[] { uid }, ct);
        }
        else
        {
            await _client.Inbox.AddFlagsAsync(uid, MessageFlags.Seen, true, ct);
        }
    }

    public async ValueTask DisposeAsync()
    {
        if (_client.IsConnected) await _client.DisconnectAsync(true);
        _client.Dispose();
    }
}
```

### Extractors — `IntegrationTests/Email/EmailExtractors.cs`

No provider-supplied codes here (that's a Mailosaur convenience) — extract structure with the same compiled regexes as the Mailpit skill, against the `MimeMessage` bodies.

```csharp
using System.Text.RegularExpressions;
using MimeKit;
using NUnit.Framework;

namespace IntegrationTests.Email;

public static partial class EmailExtractors
{
    [GeneratedRegex(@"\b(\d{6})\b")]
    private static partial Regex SixDigitOtp();

    [GeneratedRegex(@"https?://[^\s""'<>]+", RegexOptions.IgnoreCase)]
    private static partial Regex AnyUrl();

    public static string ExtractOtp(MimeMessage message)
    {
        string body = message.TextBody ?? message.HtmlBody ?? string.Empty;
        Match m = SixDigitOtp().Match(body);
        if (!m.Success) throw new AssertionException($"No 6-digit OTP found in '{message.Subject}'.");
        return m.Groups[1].Value;
    }

    public static Uri ExtractLink(MimeMessage message, string mustContain)
    {
        string html = message.HtmlBody ?? message.TextBody ?? string.Empty;
        foreach (Match m in AnyUrl().Matches(html))
        {
            if (m.Value.Contains(mustContain, StringComparison.OrdinalIgnoreCase)) return new Uri(m.Value);
        }
        throw new AssertionException($"No link containing '{mustContain}' in '{message.Subject}'.");
    }

    public static byte[] ReadAttachment(MimePart attachment)
    {
        using var stream = new MemoryStream();
        attachment.Content.DecodeTo(stream);
        return stream.ToArray();
    }
}
```

### Fixture base — `IntegrationTests/Fixtures/ImapFixture.cs`

```csharp
using IntegrationTests.Email;
using NUnit.Framework;

namespace IntegrationTests.Fixtures;

public abstract class ImapFixture
{
    protected ImapOptions Options { get; private set; } = null!;
    protected Mailbox Mail { get; private set; } = null!;

    [OneTimeSetUp]
    public async Task ConnectMailboxAsync()
    {
        Options = ImapOptions.FromEnvironment();
        Mail = new Mailbox(Options);
        await Mail.ConnectAsync();
    }

    [OneTimeTearDown]
    public async Task DisconnectMailboxAsync() => await Mail.DisposeAsync();
}
```

### Test — signup welcome

```csharp
[Test]
[AllureFeature("Authentication")]
public async Task Should_SendWelcomeEmailWithActivationLink_When_UserSignsUp()
{
    string email = Options.AliasFor("signup");
    DateTime since = DateTime.UtcNow; // time-bound the search to this test

    HttpResponseMessage response = await _client.PostAsJsonAsync("/auth/signup", new
    {
        Email = email,
        Password = "Str0ng!Passw0rd",
    });
    response.EnsureSuccessStatusCode();

    FoundEmail found = await Mail.AwaitSignupEmailAsync(email, since);
    Uri activation = EmailExtractors.ExtractLink(found.Message, "/activate?token=");

    Assert.That(activation.Query, Does.Contain("token="));
    await Mail.MarkProcessedAsync(found.Uid, delete: true);
}
```

### Test — OTP password reset

```csharp
[Test]
public async Task Should_LogIn_When_ResetOtpEntered()
{
    string email = Options.AliasFor("reset");
    DateTime since = DateTime.UtcNow;
    await _client.PostAsJsonAsync("/auth/reset", new { Email = email });

    FoundEmail found = await Mail.AwaitEmailAsync(email, "Reset code", since);
    string otp = EmailExtractors.ExtractOtp(found.Message);

    HttpResponseMessage verify = await _client.PostAsJsonAsync("/auth/verify-reset", new
    {
        Email = email,
        Otp = otp,
        NewPassword = "Brand-N3w!",
    });

    Assert.That(verify.StatusCode, Is.EqualTo(System.Net.HttpStatusCode.OK));
    await Mail.MarkProcessedAsync(found.Uid, delete: true);
}
```

### Test — attachment

```csharp
[Test]
public async Task Should_AttachPdfInvoice_When_InvoiceEmailed()
{
    string email = Options.AliasFor("billing");
    DateTime since = DateTime.UtcNow;
    await _client.PostAsJsonAsync($"/invoices/{invoiceId}/email", new { To = email });

    FoundEmail found = await Mail.AwaitEmailAsync(email, "Invoice", since);
    MimePart pdf = found.Message.Attachments.OfType<MimePart>()
        .Single(a => a.ContentType.MimeType == "application/pdf");

    byte[] bytes = EmailExtractors.ReadAttachment(pdf);

    Assert.Multiple(() =>
    {
        Assert.That(pdf.FileName, Does.StartWith("invoice-"));
        Assert.That(bytes[..4], Is.EqualTo(new byte[] { 0x25, 0x50, 0x44, 0x46 })); // %PDF magic
    });
    await Mail.MarkProcessedAsync(found.Uid, delete: true);
}
```

## Rules

### Inbox isolation (no unique inbox, no wipe)
- **Per-test `+tag` alias** via `Options.AliasFor()` — `base+{guid}@domain` all land in the one real inbox but carry a unique `To`. Search by that exact `To`.
- **Always `since`-bound the search** (`SearchQuery.DeliveredAfter`) to the test's start time. The real inbox accumulates history; an unbounded search matches stale mail.
- Search **server-side by To + Subject + since**. Never fetch-all-then-filter client-side.
- Cleanup is **per message**: flag `Seen` or `Deleted` + `ExpungeAsync(new[] { uid })`. No Mailpit-style wipe and no Mailosaur-style throwaway inbox — never expunge the whole INBOX.

### Waiting (poll-with-deadline, never a fixed sleep)
- The wait is the `AwaitEmailAsync` **deadline loop** over the IMAP search. No bare `Thread.Sleep` / `Task.Delay` as the wait between send and assert.
- `NoOpAsync` between polls so the open folder sees newly delivered mail.
- Default budget ~25s (real delivery is slower than a sink). Bump per call with a comment, not globally.
- Pace the poll (`PollInterval`, ~2s) — Gmail throttles aggressive IMAP polling.
- Async all the way: every call awaited; no `.Result` / `.GetAwaiter().GetResult()`.

### Connection lifecycle
- Connect once per fixture (`[OneTimeSetUp]`); `DisconnectAsync(true)` + `Dispose` in `[OneTimeTearDown]`. Never leak IMAP connections across tests.
- Open INBOX `FolderAccess.ReadWrite` so flag/expunge cleanup works.

### Body assertions
- Extract structure (links from `HtmlBody`, OTP from `TextBody`) and assert a **user-visible outcome** (token present, reset succeeds). Don't substring-match the full HTML.
- Visual / template-shape checks → `qa/dotnet/skills/visual-regression/playwright-snapshots`.

### Attachments
- Validate content type **and** magic bytes for binaries. Read via `Content.DecodeTo`.

### Secrets
- `IMAP_USER` + `IMAP_PASSWORD` are secrets. The password is a Gmail **App Password** (2FA required; "less secure app access" is gone) — the pragmatic CI choice. **OAuth2 XOAUTH2** (`SaslMechanismOAuth2`) is the more-secure option for long-lived setups. Read from env / user-secrets / secret store; never in code or committed `appsettings`. In CI pull them per `qa/dotnet/skills/ci-pipelines/github-actions`.

### What NOT to do
- No hardcoded mailbox address or App Password.
- No unbounded search — always `DeliveredAfter` + exact `ToContains`.
- No `Thread.Sleep` as the wait — use the deadline poll.
- No whole-INBOX wipe/expunge — clean up per message only.
- No assertions on the entire HTML body string.
- No shared single alias across tests — one `+tag` per test.

## Generation steps

1. Read existing `IntegrationTests/Fixtures/` for the SUT bootstrap (`WebApplicationFactory`) and house style.
2. Confirm the `MailKit` NuGet package is referenced and that `IMAP_USER` / `IMAP_PASSWORD` (App Password) are wired into the test env (not committed).
3. Generate:
   - `IntegrationTests/Email/ImapOptions.cs`
   - `IntegrationTests/Email/Mailbox.cs`
   - `IntegrationTests/Email/EmailExtractors.cs`
   - `IntegrationTests/Fixtures/ImapFixture.cs`
   - Concrete `IntegrationTests/{Flow}EmailTests.cs` per scenario.
4. Run `dotnet test --filter "FullyQualifiedName~Email"` with the secrets present.

## Cross-references

- **`qa/dotnet/skills/email-testing/mailosaur`**, **`qa/dotnet/skills/email-testing/mailpit`** — the other two email siblings. See the three-way pick table above: real provider (here) vs hosted SaaS vs self-hosted sink.
- **`qa/typescript/skills/email-testing/gmail-imap`** (canonical, `imapflow`), **`qa/java/skills/email-testing/gmail-imap`** (Jakarta Mail) — sibling stacks; same wrapper shape, same poll-with-deadline wait.
- **`qa/dotnet/skills/ci-pipelines/github-actions`** — where these tests run in CI and where the `IMAP_PASSWORD` App Password secret is sourced (OIDC / encrypted secrets), never hardcoded.
- **`qa/dotnet/skills/test-data-builder`** — generate per-test `+tag` aliases through a builder.
- **`qa/dotnet/skills/db-testing/testcontainers`** — signup creates a DB row *and* sends an email; assert both.
