---
name: qa-email-testing-mailpit-dotnet
description: Use when the user asks to assert on outbound email in .NET integration or E2E tests — capture signup welcome / OTP / password-reset / magic-link emails sent by the SUT, extract subject / recipient / HTML body / links, download attachments, with Mailpit as the SMTP sink. Triggers: "verify the welcome email was sent", "extract the OTP from the reset email", "assert the magic-link in the signup test", "Mailpit fixture for tests". Do NOT use for production email delivery (use SendGrid / Postmark direct), for cloud-only sandboxes (use `qa/email-testing/mailosaur/dotnet`), or for inbox polling against real Gmail (use `qa/email-testing/gmail-imap/dotnet`).
---

# QA — Email Testing with Mailpit (.NET)

Scaffolds a typed Mailpit HTTP-API client and NUnit helpers that poll for a specific message (by recipient + subject), extract HTML/text body, links, and attachments, and reset the inbox between tests. Mailpit is the local SMTP sink — point the SUT's `SMTP_HOST`/`SMTP_PORT` at the container, then assert via Mailpit's HTTP API on port 8025.

## When to use

- Signup / password-reset / magic-link / OTP / invoice / receipt flows that need an email assertion
- E2E tests that must click a link from an email (verify, reset, accept invite)
- Integration tests asserting `From`, `Reply-To`, subject templates, or attachment presence/format
- CI jobs that need a zero-dependency email capture (Mailpit is one Docker image with no DB)

## When NOT to use

- Cloud-hosted email sandboxes with per-test inboxes → `qa/email-testing/mailosaur/dotnet`
- Real Gmail / Outlook inbox polling → `qa/email-testing/gmail-imap/dotnet`
- SendGrid sandbox-mode tests against the SendGrid API → `qa/email-testing/sendgrid-sandbox/dotnet`
- Production deliverability / DKIM / SPF validation — Mailpit is a sink, not a relay verifier

## Inputs needed

Ask at most 2 questions.

1. Is Mailpit already running in the test environment (docker-compose / CI service container), or should this skill scaffold it via Testcontainers?
2. Which scenario? (signup welcome / OTP / password reset / magic link / arbitrary subject match)

## Mailpit HTTP API surface (cheat-sheet)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/messages?start=0&limit=50` | List/page recent messages |
| `GET` | `/api/v1/search?query=to:user@x.com+subject:Welcome` | Search (supports `to:`, `from:`, `cc:`, `subject:`, `body:`, `after:`, `before:`, `tag:`) |
| `GET` | `/api/v1/message/{ID}` | Full message: `HTML`, `Text`, `Subject`, `From`, `To`, `Attachments[]`, `Inline[]` |
| `GET` | `/api/v1/message/{ID}/raw` | Raw RFC-822 source |
| `GET` | `/api/v1/message/{ID}/part/{PartID}` | Download attachment by part ID |
| `GET` | `/api/v1/message/{ID}/headers` | All headers |
| `DELETE` | `/api/v1/messages` | Body `{"ids":["..."]}` or empty body to wipe all |
| `POST` | `/api/v1/send` | Send via Mailpit (rarely needed in tests) |

Search query operators are the most powerful surface — prefer them over fetching all then filtering client-side.

## Templates

### Mailpit container fixture (Testcontainers) — `IntegrationTests/Fixtures/MailpitFixture.cs`

```csharp
using DotNet.Testcontainers.Builders;
using DotNet.Testcontainers.Containers;
using NUnit.Framework;

namespace IntegrationTests.Fixtures;

public abstract class MailpitFixture
{
    private static readonly IContainer Mailpit = new ContainerBuilder()
        .WithImage("axllent/mailpit:v1.20.5")
        .WithPortBinding(1025, true) // SMTP
        .WithPortBinding(8025, true) // HTTP API + UI
        .WithEnvironment("MP_MAX_MESSAGES", "0") // disable rotation in tests
        .WithWaitStrategy(Wait.ForUnixContainer()
            .UntilHttpRequestIsSucceeded(r => r.ForPort(8025).ForPath("/api/v1/info")))
        .Build();

    protected MailpitClient Mail { get; private set; } = null!;
    protected string SmtpHost => Mailpit.Hostname;
    protected ushort SmtpPort => Mailpit.GetMappedPublicPort(1025);

    [OneTimeSetUp]
    public async Task StartMailpitAsync()
    {
        await Mailpit.StartAsync();

        Uri apiBase = new($"http://{Mailpit.Hostname}:{Mailpit.GetMappedPublicPort(8025)}");
        Mail = new MailpitClient(apiBase);
    }

    [SetUp]
    public async Task ClearInboxAsync()
    {
        await Mail.DeleteAllAsync();
    }

    [OneTimeTearDown]
    public async Task DisposeMailpitAsync()
    {
        await Mailpit.DisposeAsync();
    }
}
```

### Typed Mailpit client — `IntegrationTests/Email/MailpitClient.cs`

Strongly-typed wrapper around the API. One client per fixture; thread-safe via `HttpClient`.

```csharp
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace IntegrationTests.Email;

public sealed class MailpitClient
{
    private readonly HttpClient _http;

    public MailpitClient(Uri apiBase)
    {
        _http = new HttpClient { BaseAddress = apiBase };
    }

    public async Task<MailpitMessageSummary> WaitForAsync(
        string toAddress,
        string subjectContains,
        TimeSpan? timeout = null,
        CancellationToken cancellationToken = default)
    {
        TimeSpan budget = timeout ?? TimeSpan.FromSeconds(15);
        DateTime deadline = DateTime.UtcNow + budget;
        string query = Uri.EscapeDataString($"to:{toAddress} subject:\"{subjectContains}\"");

        while (DateTime.UtcNow < deadline)
        {
            cancellationToken.ThrowIfCancellationRequested();

            MailpitSearchResult? result = await _http.GetFromJsonAsync<MailpitSearchResult>(
                $"/api/v1/search?query={query}&limit=1",
                cancellationToken);

            if (result is { Messages.Count: > 0 })
            {
                return result.Messages[0];
            }

            await Task.Delay(250, cancellationToken);
        }

        throw new AssertionException(
            $"No Mailpit message to '{toAddress}' with subject containing '{subjectContains}' within {budget.TotalSeconds:N0}s.");
    }

    public async Task<MailpitMessage> GetAsync(string id, CancellationToken cancellationToken = default)
    {
        return (await _http.GetFromJsonAsync<MailpitMessage>(
            $"/api/v1/message/{id}",
            cancellationToken))!;
    }

    public async Task<byte[]> DownloadAttachmentAsync(string messageId, string partId, CancellationToken ct = default)
    {
        return await _http.GetByteArrayAsync($"/api/v1/message/{messageId}/part/{partId}", ct);
    }

    public async Task DeleteAllAsync(CancellationToken cancellationToken = default)
    {
        HttpRequestMessage req = new(HttpMethod.Delete, "/api/v1/messages")
        {
            Content = JsonContent.Create(new { ids = Array.Empty<string>() }),
        };
        (await _http.SendAsync(req, cancellationToken)).EnsureSuccessStatusCode();
    }
}

public sealed record MailpitSearchResult(
    [property: JsonPropertyName("messages")] IReadOnlyList<MailpitMessageSummary> Messages,
    [property: JsonPropertyName("total")] int Total);

public sealed record MailpitMessageSummary(
    [property: JsonPropertyName("ID")] string Id,
    [property: JsonPropertyName("Subject")] string Subject,
    [property: JsonPropertyName("From")] MailpitAddress From,
    [property: JsonPropertyName("To")] IReadOnlyList<MailpitAddress> To,
    [property: JsonPropertyName("Created")] DateTimeOffset Created);

public sealed record MailpitMessage(
    [property: JsonPropertyName("ID")] string Id,
    [property: JsonPropertyName("Subject")] string Subject,
    [property: JsonPropertyName("From")] MailpitAddress From,
    [property: JsonPropertyName("To")] IReadOnlyList<MailpitAddress> To,
    [property: JsonPropertyName("HTML")] string Html,
    [property: JsonPropertyName("Text")] string Text,
    [property: JsonPropertyName("Attachments")] IReadOnlyList<MailpitAttachment> Attachments);

public sealed record MailpitAddress(
    [property: JsonPropertyName("Address")] string Address,
    [property: JsonPropertyName("Name")] string Name);

public sealed record MailpitAttachment(
    [property: JsonPropertyName("PartID")] string PartId,
    [property: JsonPropertyName("FileName")] string FileName,
    [property: JsonPropertyName("ContentType")] string ContentType,
    [property: JsonPropertyName("Size")] long Size);
```

### Link / OTP extractors — `IntegrationTests/Email/EmailExtractors.cs`

Use compiled regexes once; don't sprinkle inline regex in tests.

```csharp
using System.Text.RegularExpressions;

namespace IntegrationTests.Email;

public static partial class EmailExtractors
{
    [GeneratedRegex(@"\b(\d{6})\b")]
    private static partial Regex SixDigitOtp();

    [GeneratedRegex(@"https?://[^\s""'<>]+", RegexOptions.IgnoreCase)]
    private static partial Regex AnyUrl();

    public static string ExtractOtp(MailpitMessage message)
    {
        Match m = SixDigitOtp().Match(message.Text);
        if (!m.Success)
        {
            throw new AssertionException($"No 6-digit OTP found in email '{message.Subject}'.");
        }
        return m.Groups[1].Value;
    }

    public static Uri ExtractFirstLink(MailpitMessage message, string mustContain)
    {
        foreach (Match m in AnyUrl().Matches(message.Html))
        {
            if (m.Value.Contains(mustContain, StringComparison.OrdinalIgnoreCase))
            {
                return new Uri(m.Value);
            }
        }
        throw new AssertionException(
            $"No link containing '{mustContain}' found in email '{message.Subject}'.");
    }
}
```

### Test — signup welcome assertion

```csharp
[Test]
[AllureFeature("Authentication")]
[AllureStory("Signup welcome email")]
[AllureSeverity(SeverityLevel.normal)]
public async Task Signup_SendsWelcomeEmail_WithActivationLink()
{
    string email = $"signup-{Guid.NewGuid():N}@test.local";

    HttpResponseMessage response = await _client.PostAsJsonAsync("/auth/signup", new
    {
        Email = email,
        Password = "Str0ng!Passw0rd",
    });
    response.EnsureSuccessStatusCode();

    MailpitMessageSummary summary = await Mail.WaitForAsync(email, "Welcome to FlexInvest");
    MailpitMessage full = await Mail.GetAsync(summary.Id);
    Uri activationLink = EmailExtractors.ExtractFirstLink(full, "/activate?token=");

    Assert.Multiple(() =>
    {
        Assert.That(full.From.Address, Is.EqualTo("no-reply@flexinvest.test"));
        Assert.That(full.To, Has.Exactly(1).Matches<MailpitAddress>(a => a.Address == email));
        Assert.That(full.Html, Does.Contain("Welcome"));
        Assert.That(activationLink.Query, Does.Contain("token="));
    });
}
```

### Test — OTP extraction

```csharp
[Test]
public async Task ResetPassword_SendsOtp_WhichLogsIn()
{
    string email = "existing-user@test.local";
    await _client.PostAsJsonAsync("/auth/reset", new { Email = email });

    MailpitMessageSummary summary = await Mail.WaitForAsync(email, "Reset code");
    MailpitMessage full = await Mail.GetAsync(summary.Id);
    string otp = EmailExtractors.ExtractOtp(full);

    HttpResponseMessage verify = await _client.PostAsJsonAsync("/auth/verify-reset", new
    {
        Email = email,
        Otp = otp,
        NewPassword = "Brand-N3w!"
    });

    Assert.That(verify.StatusCode, Is.EqualTo(System.Net.HttpStatusCode.OK));
}
```

### Test — attachment assertion

```csharp
[Test]
public async Task GenerateInvoice_SendsPdfAttachment()
{
    string email = "billing@test.local";
    await _client.PostAsync($"/invoices/{invoiceId}/email", null);

    MailpitMessageSummary summary = await Mail.WaitForAsync(email, "Invoice");
    MailpitMessage full = await Mail.GetAsync(summary.Id);
    MailpitAttachment pdf = full.Attachments.Single(a => a.ContentType == "application/pdf");

    byte[] bytes = await Mail.DownloadAttachmentAsync(summary.Id, pdf.PartId);

    Assert.Multiple(() =>
    {
        Assert.That(pdf.FileName, Does.StartWith("invoice-"));
        Assert.That(bytes, Has.Length.GreaterThan(1024));
        Assert.That(bytes[..4], Is.EqualTo(new byte[] { 0x25, 0x50, 0x44, 0x46 })); // %PDF magic
    });
}
```

## Rules

### Inbox isolation
- **One Mailpit instance per fixture**; clear with `DELETE /api/v1/messages` in `[SetUp]`.
- **Unique recipient per test**: `$"signup-{Guid.NewGuid():N}@test.local"`. Never share addresses across tests.
- Never assert "the only email in the inbox is X" — assert "a message matching `to + subject` exists". Other tests in parallel may have sent unrelated mail.

### Waiting
- Always poll with a budget (`WaitForAsync`). Default 15s — bump only with a comment explaining the SLA.
- **No `Thread.Sleep`** between send and assert. Use the polling helper, which respects `CancellationToken`.
- Mailpit also has a WebSocket (`/api/v1/ws`); prefer the polling helper unless you have a flake reproducer that polling can't catch.

### Search queries
- Always combine `to:` + `subject:` in the search query. Never fetch all then loop client-side — it breaks under parallel suites.
- Quote multi-word subjects: `subject:"Reset code"`.
- For per-run inbox separation in shared environments, prefix subject or use a `tag:` and search by tag.

### Body assertions
- Prefer **link / OTP extraction** over substring matching the entire HTML — copy changes break those tests every release.
- For visual / template-shape checks, use `qa/visual-regression/playwright-snapshots` on a rendered preview, not Mailpit's HTML.

### Attachments
- Validate content type **and** magic bytes for binary attachments (PDF, ZIP, PNG). Filename + content-type alone are user-controlled.
- For large attachments, check `Size` first to fail fast before downloading.

### SUT wiring
- Point the SUT at Mailpit via `WebApplicationFactory.UseSetting("Smtp:Host", SmtpHost)` and `"Smtp:Port", SmtpPort.ToString()`.
- Disable any TLS/auth requirement on the SUT's SMTP client for the test profile — Mailpit accepts plaintext SMTP by default.
- Never let production email credentials leak into the test profile (secrets policy).

### What NOT to do
- No hardcoded ports — Testcontainers assigns dynamic ports; read with `GetMappedPublicPort`.
- No `latest` image tag — pin (`axllent/mailpit:v1.20.5`).
- No shared inbox across tests (no per-test cleanup); always `DELETE /api/v1/messages` in `[SetUp]`.
- No inline regex in tests — centralise in `EmailExtractors`.
- No assertions on the entire HTML body string — extract structure (links, OTPs, headers) and assert on that.
- No real mailbox (Gmail/Outlook) for Mailpit-scope tests — use the dedicated `gmail-imap` skill if you need real-provider behaviour.

## Generation steps

1. Read existing `IntegrationTests/Fixtures/` and `appsettings.Test.json` to learn the SUT's SMTP setting names.
2. Confirm Mailpit deployment mode: Testcontainers (default for unit/integration CI) vs. an already-running compose service (typical for shared dev/staging).
3. Generate:
   - `IntegrationTests/Fixtures/MailpitFixture.cs`
   - `IntegrationTests/Email/MailpitClient.cs`
   - `IntegrationTests/Email/EmailExtractors.cs`
   - Concrete `IntegrationTests/{Flow}EmailTests.cs` per scenario.
4. Update `appsettings.Test.json` (or environment override) so the SUT writes to the Mailpit container.
5. Run `dotnet test IntegrationTests/IntegrationTests.csproj --filter "FullyQualifiedName~Email"`.

## Cross-references

- **`qa/test-data-builder/dotnet`** — generate unique per-test email addresses through a builder rather than inline `Guid.NewGuid`.
- **`qa/db-testing/testcontainers/dotnet`** — pairs with this skill: signup test creates a DB row *and* sends an email; assert both.
- **`qa/ci-pipelines/azure-pipelines/dotnet`** — Mailpit as a service container in the pipeline (`services:` block) or via Testcontainers.
- **`qa/allure-reporting/dotnet`** — attach the raw email source (`GET /api/v1/message/{id}/raw`) to Allure on failure for fast diagnosis.

## Sources synthesized (research-first per CLAUDE.md)

- [axllent/mailpit — README](https://github.com/axllent/mailpit) — feature surface and Docker image tag scheme.
- [Mailpit API v1 docs](https://mailpit.axllent.org/docs/api-v1/) — REST endpoint groups (messages / search / message / send).
- [Mailpit — Integration testing guide](https://mailpit.axllent.org/docs/integration/) — patterns for using Mailpit as a CI SMTP sink.
- [Mailpit — Web UI & API server config](https://mailpit.axllent.org/docs/configuration/http/) — auth and base path handling.
- [aaronontheweb/dotnet-skills — mailpit-integration](https://agentskills.so/skills/aaronontheweb-dotnet-skills-mailpit-integration) — community Claude skill referenced as a structural baseline (page returned 403 to WebFetch; cited from search index).

## Changelog

- 2026-05-29: Authored as the canonical .NET skill for QA Skills Library Phase 1 (`qa/GAP-ANALYSIS.md` row 4).
