---
name: qa-email-testing-mailpit-typescript
description: Use when the user asks to assert on outbound email in TypeScript (Vitest / Jest / Playwright) integration or E2E tests — capture signup welcome / OTP / password-reset / magic-link emails, extract subject / recipient / HTML body / links, download attachments, with Mailpit as the SMTP sink. Triggers: "verify the welcome email", "extract the OTP from the reset email in Playwright", "Mailpit fixture for the Vitest integration suite". Do NOT use for cloud sandboxes (`qa/typescript/skills/email-testing/mailosaur`), Gmail IMAP polling (`qa/typescript/skills/email-testing/gmail-imap`), .NET or JVM stacks.
---

# QA — Email Testing with Mailpit (TypeScript)

Scaffolds a typed Mailpit HTTP-API client and Vitest / Playwright helpers that poll for a specific message (by recipient + subject), extract HTML / text body / links / OTPs, download attachments, and reset the inbox between tests.

## When to use

- Signup / password-reset / magic-link / OTP / receipt flows that need an email assertion
- Playwright E2E tests that click an emailed link
- Integration tests asserting `From`, `Reply-To`, subject templates, attachment shape
- CI jobs that need a zero-dependency email capture

## When NOT to use

- Mailosaur cloud sandbox → `qa/typescript/skills/email-testing/mailosaur`
- Real Gmail / Outlook polling → `qa/typescript/skills/email-testing/gmail-imap`
- SendGrid sandbox-mode tests → `qa/typescript/skills/email-testing/sendgrid-sandbox`
- Production deliverability checks — Mailpit is a sink, not a relay verifier

## Inputs needed

1. Mailpit deployment: Testcontainers (default for CI) or already-running compose service?
2. Scenario: signup / OTP / reset / magic link / arbitrary subject match?

## Mailpit HTTP API surface (cheat-sheet)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/messages?start=0&limit=50` | List/page recent messages |
| `GET` | `/api/v1/search?query=to:user@x.com+subject:Welcome` | Search (`to:`, `from:`, `cc:`, `subject:`, `body:`, `after:`, `before:`, `tag:`) |
| `GET` | `/api/v1/message/{ID}` | Full message: `HTML`, `Text`, `Subject`, `From`, `To`, `Attachments[]` |
| `GET` | `/api/v1/message/{ID}/raw` | Raw RFC-822 |
| `GET` | `/api/v1/message/{ID}/part/{PartID}` | Download attachment |
| `GET` | `/api/v1/message/{ID}/headers` | All headers |
| `DELETE` | `/api/v1/messages` | Wipe all / by ids |

## Templates

### Mailpit container in Vitest global setup — `tests/integration/setup/mailpit.ts`

```ts
import { GenericContainer, Wait, type StartedTestContainer } from 'testcontainers';

let mailpit: StartedTestContainer;

export async function setup(): Promise<void> {
  mailpit = await new GenericContainer('axllent/mailpit:v1.20.5')
    .withExposedPorts(1025, 8025)
    .withEnvironment({ MP_MAX_MESSAGES: '0' })
    .withWaitStrategy(Wait.forHttp('/api/v1/info', 8025).forStatusCode(200))
    .start();

  process.env.SMTP_HOST = mailpit.getHost();
  process.env.SMTP_PORT = String(mailpit.getMappedPort(1025));
  process.env.MAILPIT_API = `http://${mailpit.getHost()}:${mailpit.getMappedPort(8025)}`;
}

export async function teardown(): Promise<void> {
  await mailpit?.stop();
}
```

### Typed client — `tests/integration/email/mailpit-client.ts`

```ts
export interface MailpitAddress {
  Address: string;
  Name: string;
}

export interface MailpitMessageSummary {
  ID: string;
  Subject: string;
  From: MailpitAddress;
  To: MailpitAddress[];
  Created: string;
}

export interface MailpitAttachment {
  PartID: string;
  FileName: string;
  ContentType: string;
  Size: number;
}

export interface MailpitMessage extends MailpitMessageSummary {
  HTML: string;
  Text: string;
  Attachments: MailpitAttachment[];
}

interface SearchResult {
  messages: MailpitMessageSummary[];
  total: number;
}

export class MailpitClient {
  constructor(private readonly baseUrl: string = process.env.MAILPIT_API!) {}

  async waitFor(
    toAddress: string,
    subjectContains: string,
    opts: { timeoutMs?: number; pollMs?: number } = {},
  ): Promise<MailpitMessageSummary> {
    const timeoutMs = opts.timeoutMs ?? 15_000;
    const pollMs = opts.pollMs ?? 250;
    const deadline = Date.now() + timeoutMs;
    const query = encodeURIComponent(`to:${toAddress} subject:"${subjectContains}"`);

    while (Date.now() < deadline) {
      const res = await fetch(`${this.baseUrl}/api/v1/search?query=${query}&limit=1`);
      if (!res.ok) throw new Error(`Mailpit search failed: ${res.status} ${res.statusText}`);
      const body = (await res.json()) as SearchResult;
      if (body.messages.length > 0) return body.messages[0];
      await new Promise((r) => setTimeout(r, pollMs));
    }
    throw new Error(
      `No Mailpit message to '${toAddress}' with subject '${subjectContains}' within ${timeoutMs}ms.`,
    );
  }

  async get(id: string): Promise<MailpitMessage> {
    const res = await fetch(`${this.baseUrl}/api/v1/message/${id}`);
    if (!res.ok) throw new Error(`Mailpit get failed: ${res.status}`);
    return (await res.json()) as MailpitMessage;
  }

  async downloadAttachment(messageId: string, partId: string): Promise<Buffer> {
    const res = await fetch(`${this.baseUrl}/api/v1/message/${messageId}/part/${partId}`);
    if (!res.ok) throw new Error(`Mailpit attachment failed: ${res.status}`);
    return Buffer.from(await res.arrayBuffer());
  }

  async deleteAll(): Promise<void> {
    const res = await fetch(`${this.baseUrl}/api/v1/messages`, {
      method: 'DELETE',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ ids: [] }),
    });
    if (!res.ok) throw new Error(`Mailpit delete failed: ${res.status}`);
  }
}
```

### Extractors — `tests/integration/email/extractors.ts`

```ts
const OTP_RE = /\b(\d{6})\b/;
const URL_RE = /https?:\/\/[^\s"'<>]+/gi;

export function extractOtp(text: string): string {
  const m = OTP_RE.exec(text);
  if (!m) throw new Error('No 6-digit OTP found in email body.');
  return m[1];
}

export function extractFirstLink(html: string, mustContain: string): URL {
  for (const m of html.matchAll(URL_RE)) {
    if (m[0].toLowerCase().includes(mustContain.toLowerCase())) return new URL(m[0]);
  }
  throw new Error(`No link containing '${mustContain}' found in HTML.`);
}
```

### Vitest test — signup welcome

```ts
import { describe, it, expect, beforeEach } from 'vitest';
import request from 'supertest';
import { MailpitClient } from './email/mailpit-client';
import { extractFirstLink } from './email/extractors';
import { createApp } from '../../src/app';

const mail = new MailpitClient();
const app = createApp();

beforeEach(() => mail.deleteAll());

describe('signup', () => {
  it('sends a welcome email with an activation link', async () => {
    const email = `signup-${crypto.randomUUID()}@test.local`;

    await request(app).post('/auth/signup').send({ email, password: 'Str0ng!Passw0rd' }).expect(201);

    const summary = await mail.waitFor(email, 'Welcome to FlexInvest');
    const full = await mail.get(summary.ID);
    const link = extractFirstLink(full.HTML, '/activate?token=');

    expect(full.From.Address).toBe('no-reply@flexinvest.test');
    expect(full.To).toHaveLength(1);
    expect(full.To[0].Address).toBe(email);
    expect(link.searchParams.get('token')).toBeTruthy();
  });
});
```

### Playwright fixture — `tests/e2e/fixtures/mailpit.ts`

```ts
import { test as base } from '@playwright/test';
import { MailpitClient } from './mailpit-client';

export const test = base.extend<{ mail: MailpitClient }>({
  mail: async ({}, use) => {
    const m = new MailpitClient(process.env.MAILPIT_API);
    await m.deleteAll();
    await use(m);
  },
});
export { expect } from '@playwright/test';
```

```ts
import { test, expect } from './fixtures/mailpit';
import { extractOtp } from './extractors';

test('reset password via OTP', async ({ page, mail }) => {
  const email = 'existing-user@test.local';
  await page.goto('/auth/reset');
  await page.getByLabel('Email').fill(email);
  await page.getByRole('button', { name: 'Send code' }).click();

  const summary = await mail.waitFor(email, 'Reset code');
  const full = await mail.get(summary.ID);
  const otp = extractOtp(full.Text);

  await page.getByLabel('Code').fill(otp);
  await page.getByLabel('New password').fill('Brand-N3w!');
  await page.getByRole('button', { name: 'Reset' }).click();
  await expect(page.getByText('Password updated')).toBeVisible();
});
```

### Attachment assertion

```ts
it('emails a PDF invoice', async () => {
  const email = 'billing@test.local';
  await request(app).post(`/invoices/${invoiceId}/email`).expect(202);

  const summary = await mail.waitFor(email, 'Invoice');
  const full = await mail.get(summary.ID);
  const pdf = full.Attachments.find((a) => a.ContentType === 'application/pdf')!;
  const bytes = await mail.downloadAttachment(summary.ID, pdf.PartID);

  expect(pdf.FileName).toMatch(/^invoice-/);
  expect(bytes.byteLength).toBeGreaterThan(1024);
  expect(bytes.subarray(0, 4)).toEqual(Buffer.from('%PDF'));
});
```

## Rules

### Inbox isolation
- One Mailpit instance per test process (`globalSetup`); clear with `DELETE /api/v1/messages` in `beforeEach`.
- Unique recipient per test: `crypto.randomUUID()`.
- Never assert "the only email is X" — assert "a message matching `to + subject` exists".

### Waiting
- Always poll with a budget (`waitFor`). Default 15s.
- No `setTimeout`-only waits in tests. Use the helper, which respects deadlines.
- Mailpit ships a WebSocket; prefer polling unless you have a reproducer polling can't handle.

### Search queries
- Combine `to:` + `subject:`. Never fetch all then filter client-side.
- Quote multi-word subjects: `subject:"Reset code"`.

### Body assertions
- Extract structure (links, OTPs, headers); don't substring-match the full HTML — copy changes break those tests.
- Visual / template-shape checks → `qa/typescript/skills/visual-regression/playwright-snapshots`.

### Attachments
- Validate content type **and** magic bytes for binaries.
- Check `Size` before downloading large attachments.

### SUT wiring
- Inject Mailpit via `SMTP_HOST` / `SMTP_PORT` env vars (or whatever the SUT reads).
- Disable TLS in the test profile — Mailpit accepts plaintext.
- Never let production SMTP credentials leak into the test profile.

### What NOT to do
- No hardcoded ports — read from `getMappedPort()`.
- No `latest` image tag — pin `axllent/mailpit:v1.20.5`.
- No shared inbox across tests without a `beforeEach` cleanup.
- No inline regex — centralise in `extractors.ts`.
- No assertions on the entire HTML string.

## Generation steps

1. Read `package.json` (Vitest vs Jest, Playwright presence) and existing `tests/integration/setup` files.
2. Confirm Mailpit deployment mode (Testcontainers vs compose).
3. Generate:
   - `tests/integration/setup/mailpit.ts` (or `playwright.config.ts` global setup)
   - `tests/integration/email/mailpit-client.ts`
   - `tests/integration/email/extractors.ts`
   - Concrete `{flow}-email.int.test.ts` per scenario
4. Add `MAILPIT_API` / `SMTP_HOST` / `SMTP_PORT` to the SUT's test profile.
5. Run `npm run test:integration` (or the existing script).

## Cross-references

- **`qa/typescript/skills/test-data-builder`** — unique-email builder.
- **`qa/typescript/skills/db-testing/testcontainers`** — signup creates a DB row *and* sends an email.
- **`qa/typescript/skills/ci-pipelines/azure-pipelines`** — Mailpit as a service container in the pipeline.
- **`qa/typescript/skills/allure-reporting`** — attach raw email source on failure.
