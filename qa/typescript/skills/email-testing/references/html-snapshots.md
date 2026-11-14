# Email HTML snapshots — Vitest file snapshots on mail captured by Mailpit

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
| Does every locale's template render the same structure? | **Snapshot** per locale (`it.each(['en', 'de'])`) |
| Does it look right in Outlook and Gmail? | Neither — a rendering service or `visual-regression` |

## Packages

| Package | Version | Why |
|---|---|---|
| `vitest` | The project's major (5.1 current) | `toMatchFileSnapshot` writes the snapshot as a real `.html` file |
| `prettier` | **3.10.1** (3.x) | Formats the HTML so the diff shows the changed element, not one 40 kB line |

Verified on npm, 2026-11. Templating engines (MJML, React Email) emit minified HTML; without formatting, every
change is a one-line diff nobody can review. A Jest suite has no file snapshot built in: it snapshots the same
scrubbed, formatted string with `toMatchSnapshot()` into its `.snap` file.

## Scrubbing what changes per send

An email is full of per-send values. Scrub each one, or the snapshot fails on every run:

| Value | Scrub |
|---|---|
| The unique per-test recipient (`signup-<uuid>@test.local`) | Replace the exact address with `{Recipient}` |
| The SUT's host and port (`http://localhost:51234`) | Replace the exact base URL with `{BaseUrl}` |
| Activation / reset / magic-link tokens in `href`s | The `token` / `code` query value becomes `{Token}` |
| One-time codes | Six-digit runs become `{Otp}` |
| UUIDs in links or body (order ids) | `{Uuid}` |
| Dates and times rendered in the body | A regex for **the template's own format** becomes `{Date}` |
| Tracking-pixel and click-tracking URLs | The query string becomes `{Tracking}` |

Scrub the **value**, keep the **shape**: `href="{BaseUrl}/activate?token={Token}"` still proves the link points at
the activation route with a token parameter. Exact values (recipient, base URL) are replaced first, so the patterns
never see them.

```ts
// tests/integration/email/scrub-email.ts
import { format } from 'prettier';

const TOKEN_VALUE = /(?<=[?&](?:token|code)=)[^&"'\s<]+/gi;
const UUID = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi;
const SIX_DIGIT_CODE = /\b\d{6}\b/g;
const LONG_DATE = /\b\d{1,2} (?:January|February|March|April|May|June|July|August|September|October|November|December) \d{4}\b/g;
const TRACKING_QUERY = /(?<=https:\/\/track\.example\.com\/[^"?]*)\?[^"]*/g;

export interface PerSendValues {
  recipient: string;
  baseUrl: string;
}

export async function scrubEmail(html: string, values: PerSendValues): Promise<string> {
  const scrubbed = html
    .replaceAll(values.recipient, '{Recipient}')
    .replaceAll(values.baseUrl, '{BaseUrl}')
    .replace(TOKEN_VALUE, '{Token}')
    .replace(UUID, '{Uuid}')
    .replace(SIX_DIGIT_CODE, '{Otp}')
    .replace(LONG_DATE, '{Date}')
    .replace(TRACKING_QUERY, '?{Tracking}');
  return format(scrubbed, { parser: 'html', printWidth: 120 });
}
```

- **One scrubber for the suite**, beside `extractors.ts` — the patterns live in one place, as `mailpit.md` requires
  for its regexes. `LONG_DATE` and the tracking host are examples: write the pattern for what the templates actually
  render.
- **Prefer fixing the source to scrubbing.** A date the SUT takes from an injectable clock, set for the test
  environment, needs no scrub; scrubbing is for values the test cannot control.
- `format` is async in Prettier 3; `printWidth` only sets where lines wrap, so pick one value and keep it.

## The test

```ts
import { describe, expect, it } from 'vitest';
import request from 'supertest';
import { MailpitClient } from './email/mailpit-client';
import { uniqueRecipient } from './email/recipients';
import { scrubEmail } from './email/scrub-email';
import { SignUpRequestBuilder } from './builders/sign-up-request.builder';
import { createApp } from '../../src/app';

const mail = new MailpitClient();
const app = createApp();
const BASE_URL = process.env.PUBLIC_BASE_URL!;

describe('welcome email', () => {
  it.each(['en', 'de'])('Should_RenderTheWelcomeEmail_When_AUserSignsUpIn_%s', async (locale) => {
    const email = uniqueRecipient(`signup-${locale}`);
    await request(app)
      .post('/auth/signup')
      .send(new SignUpRequestBuilder().withEmail(email).withLocale(locale).build())
      .expect(201);

    const message = await mail.get((await mail.waitFor(email, 'Welcome')).ID);

    await expect(await scrubEmail(message.HTML, { recipient: email, baseUrl: BASE_URL })).toMatchFileSnapshot(
      `./__email_snapshots__/welcome.${locale}.html`,
    );
  });
});
```

- Snapshot `message.HTML` (the `HTML` field of `GET /api/v1/message/{id}`) — the body the SUT produced. Add a second
  test on `message.Text` into a `.txt` file when the plain-text part matters.
- **`toMatchFileSnapshot` returns a promise — `await` it**, or the test ends before the comparison and passes.
- The path is relative to the test file. Keep file snapshots in their own folder (`__email_snapshots__/`), never
  under Vitest's managed `__snapshots__/`.
- Open the `.html` file in a browser to review the rendering; read its diff in the pull request to review the change.

## Source control and CI

- Commit every `__email_snapshots__/*.html`; `.gitattributes`
  `__email_snapshots__/** text eol=lf` so a Windows checkout does not fail every comparison on line endings.
- **A missing or changed snapshot fails in CI.** With `CI` set, Vitest writes no snapshots; make it explicit in the
  pipeline with `vitest run --update=none`, so a runner without `CI` behaves the same.
- **`-u` is run by a person**, locally, after opening the new rendering — never in a pipeline step, a pre-commit hook,
  or a script that "fixes the snapshots". Accepting a changed email is a review decision.
- To show the reviewer the rendered change, the failing job may re-run the email tests with `--update=all` in its own
  workspace and upload the changed `.html` files as an artifact — never commit from it
  (`qa/cicd/typescript/skills/ci-pipelines`).
- Bump `prettier` alone, re-run, review the formatting diffs, then accept: a Prettier minor can re-wrap HTML.

## Anti-patterns

- **Snapshotting the raw MIME source.** Boundaries, `Message-ID` and encodings change per send; snapshot the decoded
  HTML and text parts.
- **Scrubbing so much that nothing is left.** If every line is scrubbed, the snapshot proves only that an email
  exists; scrub values, not elements.
- **A snapshot instead of the link check.** A scrubbed link is a shape, not a working link — keep the extract-and-call
  test from `mailpit.md`.
- **`toMatchInlineSnapshot` for an email.** A whole email inside the test file buries the test; email HTML belongs in
  a file a browser can open.
