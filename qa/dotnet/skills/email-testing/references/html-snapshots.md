# Email HTML snapshots — Verify on mail captured by Mailpit

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
| Does every locale's template render the same structure? | **Snapshot** per locale (`[TestCase("en")]`, `[TestCase("de")]`) |

## Packages

| Package | Version | Why |
|---|---|---|
| `Verify.NUnit` | **33.1.5** on NUnit 4 (needs `NUnit` ≥ 4.6.1) · **33.4.0** on NUnit 5 | The snapshot engine |
| `Verify.AngleSharp` | **5.1.2** | Pretty-prints HTML so the diff shows the changed element, not one 40 kB line |

Verified on nuget.org, 2026-11. Verify versions released after 1 September 2026 fall under the Open Source
Maintenance Fee for organizations with revenue, and from v33 a build-time check reads the declaration from
`Directory.Build.props`; record the team's decision (sponsor, exemption, or pin `Verify.NUnit` 32.0.0) before adding
it.

## Settings once, in a module initializer

```csharp
using System.Runtime.CompilerServices;
using VerifyTests.AngleSharp;

namespace IntegrationTests;

internal static class VerifyInitializer
{
    [ModuleInitializer]
    internal static void Initialize()
    {
        HtmlPrettyPrint.All();
        VerifierSettings.ScrubInlineGuids();
    }
}
```

## Scrubbing what changes per send

An email is full of per-send values. Scrub each one, or the snapshot fails on every run:

| Value | Scrub |
|---|---|
| The unique per-test recipient (`signup-<guid>@test.local`) | `ScrubReplace(recipient, "{Recipient}")` |
| Activation / reset / magic-link tokens in `href`s | A source-generated regex replacing the token value with `{Token}` |
| One-time codes | The same, `{Otp}` |
| Dates and times rendered in the body | `ScrubInlineDateTimes("<the template's format>")` |
| Tracking-pixel and click-tracking URLs | Replace the query string with `{Tracking}` |
| The SUT's host and port (`http://localhost:51234`) | `ScrubReplace(baseUrl, "{BaseUrl}")` |

Scrub the **value**, keep the **shape**: `href="{BaseUrl}/activate?token={Token}"` still proves the link points
at the activation route with a token parameter.

```csharp
using System.Text.RegularExpressions;

namespace IntegrationTests.Email;

public static partial class EmailScrubbers
{
    [GeneratedRegex(@"(?<=[?&](token|code)=)[^&""'\s<]+", RegexOptions.IgnoreCase)]
    private static partial Regex TokenValue();

    [GeneratedRegex(@"\b\d{6}\b")]
    private static partial Regex SixDigitCode();

    public static string? ScrubSecrets(string line) =>
        SixDigitCode().Replace(TokenValue().Replace(line, "{Token}"), "{Otp}");
}
```

## The test

```csharp
[Test]
public async Task Should_RenderTheWelcomeEmail_When_AUserSignsUp()
{
    string email = $"signup-{Guid.NewGuid():N}@test.local";
    HttpResponseMessage response = await _client.PostAsJsonAsync("/auth/signup", new SignUpRequestBuilder()
        .WithEmail(email)
        .Build());
    Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.Created), await response.Content.ReadAsStringAsync());

    MailpitMessageSummary summary = await Mail.WaitForAsync(email, "Welcome");
    MailpitMessage message = await Mail.GetAsync(summary.Id);

    await Verify(message.Html, "html")
        .ScrubReplace(email, "{Recipient}")
        .ScrubReplace(_client.BaseAddress!.GetLeftPart(UriPartial.Authority), "{BaseUrl}")
        .ScrubLinesWithReplace(EmailScrubbers.ScrubSecrets);
}
```

- Snapshot `message.Html` (the `HTML` field of `GET /api/v1/message/{id}`) — the body the SUT produced. Add a
  second test on `message.Text` with `Verify(message.Text, "txt")` when the plain-text part matters.
- The file lands beside the test as `<Class>.Should_RenderTheWelcomeEmail_When_AUserSignsUp.verified.html` —
  open it in a browser to review the rendering, read the diff in the pull request to review the change.
- Per-locale or per-variant runs: parameterize the test; Verify adds the parameter values to the file name.

## Source control and CI

- `.gitignore` `*.received.*`; commit every `*.verified.*`; `.gitattributes`
  `*.verified.html text eol=lf working-tree-encoding=UTF-8`.
- A missing `.verified.html` **fails** the test — CI keeps that. Never call `AutoVerify()`; a person accepts a
  changed email after looking at it.
- On failure, upload `**/*.received.*` as an artifact so the reviewer sees the rendered change
  (`qa/cicd/dotnet/skills/ci-pipelines`).

## Anti-patterns

- **Snapshotting the raw MIME source.** Boundaries, `Message-ID` and encodings change per send; snapshot the
  decoded HTML and text parts.
- **Scrubbing so much that nothing is left.** If every line is scrubbed, the snapshot proves only that an email
  exists; scrub values, not elements.
- **A snapshot instead of the link check.** A scrubbed link is a shape, not a working link — keep the extract-and-
  call test from `mailpit.md`.
