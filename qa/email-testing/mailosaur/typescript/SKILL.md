---
name: qa-email-testing-mailosaur-typescript
description: Use when the user asks to assert on real outbound email or SMS in TypeScript (Vitest / Jest / Playwright) integration or E2E tests using the hosted Mailosaur service + the official `mailosaur` npm SDK — capture signup welcome / OTP / password-reset / magic-link messages delivered to a per-test `{uuid}@{serverId}.mailosaur.net` inbox, extract subject / recipient / HTML body / links / OTP codes, download attachments, verify SMS one-time passcodes. Triggers: "verify the welcome email with Mailosaur", "extract the OTP from the reset email", "Mailosaur fixture for the Playwright suite", "assert the magic-link", "check the SMS verification code". Do NOT use for the self-hosted SMTP sink (`qa/email-testing/mailpit/typescript`), Gmail IMAP polling (`qa/email-testing/gmail-imap/typescript`), SendGrid sandbox mode (`qa/email-testing/sendgrid-sandbox/typescript`), or .NET / JVM stacks (`qa/email-testing/mailosaur/{dotnet,java}`).
---

# QA — Email & SMS Testing with Mailosaur (TypeScript)

Scaffolds a thin, intent-revealing wrapper over the official `mailosaur` npm SDK plus Vitest / Playwright helpers that **await** a specific message in a per-test `{uuid}@{serverId}.mailosaur.net` inbox, extract HTML / text body / links / OTP codes, download attachments, and verify SMS. Mailosaur is a **hosted** service: the SUT sends real email through its real provider to a Mailosaur inbox address, and the SDK's `messages.get(...)` blocks until the message arrives or the timeout fires — that built-in wait is the sanctioned wait, so there is **no manual `setTimeout` / `waitForTimeout` poll loop** anywhere in this skill.

## When to use

- Signup / password-reset / magic-link / OTP / receipt flows that need an email assertion against a **real delivery path** (real SMTP/provider → real inbox), not just an SMTP sink
- Playwright E2E tests that click an emailed link or type an emailed OTP
- Integration tests asserting `From`, `subject` templates, HTML link targets, attachment shape
- **SMS / phone** one-time-passcode flows (same SDK, an SMS-enabled server)
- Teams that want zero local infra in CI — no container, just an API key + server ID secret

## When NOT to use

- Self-hosted SMTP sink, no cloud account, fully offline CI → `qa/email-testing/mailpit/typescript`
- Polling a real Gmail / Outlook mailbox over IMAP → `qa/email-testing/gmail-imap/typescript`
- SendGrid sandbox-mode (mail-send API, no delivery) → `qa/email-testing/sendgrid-sandbox/typescript`
- .NET or JVM stacks → `qa/email-testing/mailosaur/{dotnet,java}`
- Production deliverability / DKIM / SPF auditing — Mailosaur captures, it is not a relay verifier

## Mailpit vs Mailosaur — pick the right sibling

| | **Mailosaur** (this skill) | **Mailpit** (`qa/email-testing/mailpit/typescript`) |
|---|---|---|
| Hosting | Hosted SaaS, API key + server ID | Self-hosted container (Testcontainers / compose) |
| Delivery path | **Real** — SUT's real provider delivers to a real inbox | SMTP sink — SUT points its SMTP client at the container |
| Wait primitive | SDK `messages.get(..., { timeout })` blocks until arrival | You poll the HTTP search API with a deadline |
| Per-test isolation | Unique `{uuid}@{serverId}.mailosaur.net` address (no shared inbox) | `DELETE /api/v1/messages` between tests |
| SMS testing | ✅ same SDK, SMS server | ❌ |
| Secrets | API key + server ID (secret store) | None |
| Offline CI | ❌ needs network to Mailosaur | ✅ fully offline |

Use **Mailosaur** when you want to exercise the real send path or test SMS; use **Mailpit** when you want zero external dependencies and offline CI.

## Inputs needed

Ask at most 2 questions; infer the rest from `package.json`, `playwright.config.ts`, existing fixtures.

1. Scenario: signup welcome / OTP / password reset / magic link / SMS code / arbitrary subject match?
2. Where do the `MAILOSAUR_API_KEY` and `MAILOSAUR_SERVER_ID` come from in this environment (CI secret store, `.env.test`)? They are **secrets** — never commit them.

## Mailosaur SDK surface (cheat-sheet)

| Call | Purpose |
|---|---|
| `new Mailosaur(apiKey)` | Construct the client (inject the key; never hardcode) |
| `client.messages.get(serverId, criteria, { timeout })` | **Await** the first message matching `criteria` — blocks until arrival or `timeout` (ms, default 10 000), then throws. This is the wait. |
| `client.messages.list(serverId, options)` | Page recent messages (rarely needed in tests — prefer `get`) |
| `client.messages.deleteAll(serverId)` | Empty the whole server inbox (use sparingly — see isolation rules) |
| `client.files.getAttachment(attachmentId)` | Download an attachment as a `Buffer` |
| `SearchCriteria` | `sentTo`, `sentFrom`, `subject`, `body`, `match` (`'ALL'` \| `'ANY'`) |
| `message.html.links[]` | `{ text, href }` — hyperlinks Mailosaur extracted from the HTML |
| `message.html.codes[]` / `message.text.codes[]` | `{ value }` — OTP / verification codes Mailosaur auto-detected |
| `message.html.body` / `message.text.body` | Raw bodies (extract structure; don't substring the whole thing) |
| `message.attachments[]` | `{ id, fileName, contentType, length }` |

**Inbox-address pattern:** any address `{anything}@{serverId}.mailosaur.net` routes to your server. Per test, generate `{crypto.randomUUID()}@{serverId}.mailosaur.net` so every test owns a unique recipient and needs no shared-inbox cleanup.

## Templates

### Config — `tests/integration/email/mailosaur.config.ts`

Secrets come from the environment, validated once at load. Never inline the key or server ID.

```ts
function required(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`Missing required env var ${name} (Mailosaur secret).`);
  return v;
}

export const mailosaurConfig = {
  apiKey: required('MAILOSAUR_API_KEY'),
  serverId: required('MAILOSAUR_SERVER_ID'),
  /** Default await budget for a message to arrive. Bump per-call with a comment, not here. */
  timeoutMs: Number(process.env.MAILOSAUR_TIMEOUT_MS ?? 20_000),
} as const;

/** Unique recipient per test → independent tests, no shared-inbox races. */
export function newRecipient(prefix = 'qa'): string {
  return `${prefix}-${crypto.randomUUID()}@${mailosaurConfig.serverId}.mailosaur.net`;
}
```

### Intent-revealing wrapper — `tests/integration/email/mailbox.ts`

Specs never call `messages.get` directly. They call `awaitSignupEmail`, `extractVerificationLink`, `extractOtp`. The SDK's blocking `get` is the only wait.

```ts
import Mailosaur from 'mailosaur';
import type { Message } from 'mailosaur/lib/models';
import { mailosaurConfig } from './mailosaur.config';

export class Mailbox {
  private readonly client: Mailosaur;

  constructor(
    private readonly serverId: string = mailosaurConfig.serverId,
    apiKey: string = mailosaurConfig.apiKey,
  ) {
    this.client = new Mailosaur(apiKey);
  }

  /** Await an email by recipient (+ optional subject). Blocks until arrival or timeout. */
  async awaitEmail(
    sentTo: string,
    opts: { subject?: string; timeoutMs?: number } = {},
  ): Promise<Message> {
    return this.client.messages.get(
      this.serverId,
      { sentTo, subject: opts.subject },
      { timeout: opts.timeoutMs ?? mailosaurConfig.timeoutMs },
    );
  }

  awaitSignupEmail(sentTo: string): Promise<Message> {
    return this.awaitEmail(sentTo, { subject: 'Welcome' });
  }

  /** Await an SMS to a Mailosaur phone number (SMS-enabled server). Same primitive. */
  async awaitSms(sentTo: string, timeoutMs?: number): Promise<Message> {
    return this.client.messages.get(
      this.serverId,
      { sentTo },
      { timeout: timeoutMs ?? mailosaurConfig.timeoutMs },
    );
  }

  downloadAttachment(attachmentId: string): Promise<Buffer> {
    return this.client.files.getAttachment(attachmentId);
  }

  /** Hard reset of the whole server inbox. Prefer unique recipients over this. */
  emptyServerInbox(): Promise<void> {
    return this.client.messages.deleteAll(this.serverId);
  }
}
```

### Extractors — `tests/integration/email/extractors.ts`

Prefer Mailosaur's structured `links` / `codes` over hand-rolled regex; fall back to regex only for non-standard bodies.

```ts
import type { Message } from 'mailosaur/lib/models';

export function extractOtp(message: Message): string {
  const code = message.html?.codes?.[0]?.value ?? message.text?.codes?.[0]?.value;
  if (!code) throw new Error(`No verification code found in "${message.subject}".`);
  return code;
}

export function extractLink(message: Message, mustContain: string): URL {
  const link = message.html?.links?.find((l) =>
    l.href?.toLowerCase().includes(mustContain.toLowerCase()),
  );
  if (!link?.href) {
    throw new Error(`No link containing '${mustContain}' in "${message.subject}".`);
  }
  return new URL(link.href);
}
```

### Vitest test — signup welcome

```ts
import { describe, it, expect } from 'vitest';
import request from 'supertest';
import { Mailbox } from './email/mailbox';
import { newRecipient } from './email/mailosaur.config';
import { extractLink } from './email/extractors';
import { createApp } from '../../src/app';

const mailbox = new Mailbox();
const app = createApp();

describe('signup', () => {
  it('Should_SendWelcomeEmailWithActivationLink_When_UserSignsUp', async () => {
    const email = newRecipient('signup');

    await request(app).post('/auth/signup').send({ email, password: 'Str0ng!Passw0rd' }).expect(201);

    const message = await mailbox.awaitSignupEmail(email);
    const activation = extractLink(message, '/activate?token=');

    expect(activation.searchParams.get('token')).toBeTruthy();
  });
});
```

### Playwright fixture — `tests/e2e/fixtures/mailbox.ts`

```ts
import { test as base } from '@playwright/test';
import { Mailbox } from '../../integration/email/mailbox';
import { newRecipient } from '../../integration/email/mailosaur.config';

export const test = base.extend<{ mailbox: Mailbox; recipient: string }>({
  mailbox: async ({}, use) => use(new Mailbox()),
  recipient: async ({}, use) => use(newRecipient('e2e')),
});
export { expect } from '@playwright/test';
```

```ts
import { test, expect } from './fixtures/mailbox';
import { extractOtp } from '../integration/email/extractors';

test('reset password via emailed OTP', async ({ page, mailbox, recipient }) => {
  await page.goto('/auth/reset');
  await page.getByLabel('Email').fill(recipient);
  await page.getByRole('button', { name: 'Send code' }).click();

  const message = await mailbox.awaitEmail(recipient, { subject: 'Reset code' });
  const otp = extractOtp(message);

  await page.getByLabel('Code').fill(otp);
  await page.getByLabel('New password').fill('Brand-N3w!');
  await page.getByRole('button', { name: 'Reset' }).click();
  await expect(page.getByText('Password updated')).toBeVisible();
});
```

### SMS one-time passcode

```ts
it('Should_SendSmsCode_When_PhoneVerificationRequested', async () => {
  // Mailosaur provisions a dedicated test phone number on an SMS-enabled server.
  const phoneNumber = process.env.MAILOSAUR_PHONE_NUMBER!;
  await request(app).post('/auth/phone/verify').send({ phoneNumber }).expect(202);

  const sms = await mailbox.awaitSms(phoneNumber);
  expect(extractOtp(sms)).toMatch(/^\d{6}$/);
});
```

### Attachment assertion

```ts
it('Should_AttachPdfInvoice_When_InvoiceEmailed', async () => {
  const email = newRecipient('billing');
  await request(app).post(`/invoices/${invoiceId}/email`).send({ to: email }).expect(202);

  const message = await mailbox.awaitEmail(email, { subject: 'Invoice' });
  const pdf = message.attachments?.find((a) => a.contentType === 'application/pdf');
  expect(pdf, 'expected a PDF attachment').toBeDefined();

  const bytes = await mailbox.downloadAttachment(pdf!.id!);
  expect(bytes.subarray(0, 4)).toEqual(Buffer.from('%PDF'));
});
```

## Rules

### Inbox isolation
- **Unique recipient per test**: `{uuid}@{serverId}.mailosaur.net` via `newRecipient()`. Tests stay independent and parallel-safe with no shared cleanup.
- Prefer unique recipients over `messages.deleteAll(serverId)` — `deleteAll` wipes the **whole** server and will race a parallel suite.
- Search by `sentTo` (+ `subject`), never "the latest message in the server" — another test's mail may be newer.

### Waiting
- **The wait is `messages.get(..., { timeout })`** — it blocks until a match arrives, then throws on timeout. Never wrap it in a manual `setTimeout` / `page.waitForTimeout` poll loop.
- Set `timeout` to a real SLA (default 20s here). Bump per call with a comment explaining why, not globally.

### Body assertions
- Assert on Mailosaur's **structured** output: `html.links[].href`, `html.codes[].value`. Don't substring-match the full `html.body` — copy changes break those tests every release.
- Assert a **user-visible outcome** of the link/OTP (token present, page shows "Password updated"), not the raw string shape.
- Visual / template-shape checks → `qa/visual-regression/playwright-snapshots/typescript`.

### Attachments
- Validate content type **and** magic bytes for binaries (`%PDF`, `PK`, `\x89PNG`). Check `length` before downloading large files.

### Secrets
- `MAILOSAUR_API_KEY` + `MAILOSAUR_SERVER_ID` are secrets. Read from env / secret store; never in code, `.env` committed to git, or test fixtures. In CI pull them per `qa/ci-pipelines/github-actions/typescript` (OIDC / encrypted secrets).

### What NOT to do
- No hardcoded API key or server ID.
- No manual sleep/poll around `messages.get` — its `timeout` is the wait.
- No `deleteAll` as a substitute for unique recipients in parallel suites.
- No assertions on the entire HTML body string.
- No `messages.list` + client-side filtering when `messages.get` with criteria does it server-side.

## Generation steps

1. Read `package.json` (Vitest vs Jest, Playwright presence) and existing `tests/` fixtures for house style.
2. Confirm `mailosaur` is installed (`npm i -D mailosaur`) and that `MAILOSAUR_API_KEY` / `MAILOSAUR_SERVER_ID` are wired into the test env (not committed).
3. Generate:
   - `tests/integration/email/mailosaur.config.ts`
   - `tests/integration/email/mailbox.ts`
   - `tests/integration/email/extractors.ts`
   - Concrete `{flow}-email.int.test.ts` / Playwright spec per scenario.
4. Run `npm run test:integration` (or the existing script) with the secrets present.

## Cross-references

- **`qa/email-testing/mailpit/typescript`** — the self-hosted SMTP-sink sibling. Pick Mailpit for offline CI and zero external deps; pick Mailosaur (here) for real-delivery and SMS. See the comparison table above.
- **`qa/email-testing/mailosaur/dotnet`**, **`qa/email-testing/mailosaur/java`** — the sibling stacks; same wrapper shape, same `messages.get` wait.
- **`qa/ci-pipelines/github-actions/typescript`** — where these specs run in CI and where the `MAILOSAUR_API_KEY` / `MAILOSAUR_SERVER_ID` secrets are sourced (OIDC / encrypted secrets), never hardcoded.
- **`qa/test-data-builder/typescript`** — generate unique per-test recipients through a builder.
- **`qa/db-testing/testcontainers/typescript`** — signup creates a DB row *and* sends an email; assert both.

## Sources synthesized (research-first per CLAUDE.md)

- [mailosaur/mailosaur-node — README](https://github.com/mailosaur/mailosaur-node) — `messages.get(serverId, criteria, options)`, `files.getAttachment`, `deleteAll`, `html.links` / `html.codes` shapes.
- [mailosaur — npm](https://www.npmjs.com/package/mailosaur) — package + TypeScript types.
- [Email testing with Node.js | Mailosaur docs](https://mailosaur.com/docs/email-testing/nodejs) — inbox-address pattern, default 10s wait, `timeout` option.
- [SMS testing with Node.js | Mailosaur docs](https://mailosaur.com/docs/sms-testing/nodejs) — same `messages.get` against an SMS server.

## Changelog

- 2026-05-31: Authored as the canonical TypeScript skill for the Mailosaur node (`qa/GAP-ANALYSIS.md` row 5). Anchors the 3-stack family on the `mailosaur` npm SDK's blocking `messages.get` wait.
