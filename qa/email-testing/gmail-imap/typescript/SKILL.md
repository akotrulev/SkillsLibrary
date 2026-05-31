---
name: qa-email-testing-gmail-imap-typescript
description: Use when the user asks to assert on email delivered to a *real* provider mailbox (Gmail / Outlook / any IMAP account) in TypeScript (Vitest / Jest / Playwright) integration or E2E tests by polling over IMAP with `imapflow` + `mailparser` — find a signup welcome / OTP / password-reset / magic-link message by To + Subject + `since`, extract HTML / text body / links / OTP codes, download attachments, then clean up via IMAP flags. Triggers: "poll the real Gmail inbox over IMAP", "read the verification email from our test Gmail account", "imapflow fixture for the Playwright suite", "extract the OTP from the password-reset email in the real mailbox". Do NOT use for the self-hosted SMTP sink (`qa/email-testing/mailpit/typescript`), the hosted Mailosaur sandbox (`qa/email-testing/mailosaur/typescript`), SendGrid sandbox mode (`qa/email-testing/sendgrid-sandbox/typescript`), or .NET / JVM stacks (`qa/email-testing/gmail-imap/{dotnet,java}`).
---

# QA — Email Testing against a Real Mailbox over IMAP (TypeScript)

Scaffolds a thin, intent-revealing wrapper over `imapflow` (Node 20 + TS) plus `mailparser`'s `simpleParser`, with Vitest / Playwright helpers that **poll a real provider mailbox** (Gmail / Outlook / any IMAP server) for a specific message — by recipient alias + subject + `since` time bound — extract HTML / text body / links / OTP codes, download attachments, and clean up by flagging the message `\Seen` / `\Deleted` rather than wiping an inbox.

This is the sibling for flows that must exercise the **genuine provider inbox** — real MX, real spam/routing, real provider quirks — not an SMTP sink or a test-SaaS server. Two consequences shape the whole skill:

- **There is no per-test unique-inbox trick** (no `{uuid}@{serverId}.mailosaur.net`) and **no `DELETE all` HTTP API** (no Mailpit wipe). Isolation comes from **Gmail `+tag` / dot aliases** — `youraccount+{uuid}@gmail.com` all land in the *one* real inbox — plus a **`since` time bound** and a **server-side search by To + Subject**. Cleanup is per-message via IMAP flags (`\Seen` / `\Deleted` + `expunge`), not a wipe.
- **No SDK "blocks until arrived" primitive exists.** The wait **is** a real **poll-with-deadline loop** over the IMAP search — but still **no fixed `setTimeout` / `waitForTimeout`**: poll the search on an interval against a deadline (the same `waitFor` shape as `qa/email-testing/mailpit/typescript`). Real-provider delivery is slower, so the default budget is larger (~25s).

## When to use

- Signup / password-reset / magic-link / OTP flows that must hit a **real provider mailbox** over IMAP (genuine deliverability path, not a sink or SaaS capture)
- Teams already owning a dedicated test Gmail / Outlook / M365 account they want to drive from CI
- Playwright E2E tests that click an emailed link or type an emailed OTP read from the real inbox
- Integration tests asserting `From`, subject templates, HTML link targets, attachment shape on real delivery

## When NOT to use

- Self-hosted SMTP sink, zero external deps, fully offline CI → `qa/email-testing/mailpit/typescript`
- Hosted sandbox with per-test inboxes + a blocking SDK wait + SMS → `qa/email-testing/mailosaur/typescript`
- SendGrid sandbox-mode (mail-send API, no delivery) → `qa/email-testing/sendgrid-sandbox/typescript`
- .NET or JVM stacks → `qa/email-testing/gmail-imap/{dotnet,java}`
- Production deliverability / DKIM / SPF auditing — this polls a mailbox, it is not a relay verifier

## gmail-imap vs mailosaur vs mailpit — pick the right sibling

| | **gmail-imap** (this skill) | **mailosaur** (`qa/email-testing/mailosaur/typescript`) | **mailpit** (`qa/email-testing/mailpit/typescript`) |
|---|---|---|---|
| What it hits | A **real** provider mailbox over IMAP | Hosted SaaS capture inbox | Self-hosted SMTP **sink** (container) |
| Delivery path | Real MX → real inbox | Real provider → Mailosaur inbox | SUT points SMTP at the sink |
| Wait primitive | **Poll IMAP search** with a deadline | SDK `messages.get(..., {timeout})` blocks | Poll HTTP search with a deadline |
| Per-test isolation | `+tag` alias into one inbox + `since` bound | Unique `{uuid}@{serverId}.mailosaur.net` | `DELETE /api/v1/messages` between tests |
| Cleanup | Flag `\Seen` / `\Deleted` + expunge (per message) | (unique address — none needed) | Wipe-all API |
| Secrets | Mailbox address + **App Password** | API key + server ID | None |
| Offline CI | ❌ needs network to the provider | ❌ needs network to Mailosaur | ✅ fully offline |

Pick **gmail-imap** when the test must prove mail lands in a genuine provider inbox; **mailosaur** for a frictionless real-delivery path with per-test inboxes and SMS; **mailpit** for offline, zero-dependency CI.

## Inputs needed

Ask at most 2 questions; infer the rest from `package.json`, `playwright.config.ts`, existing fixtures.

1. Scenario: signup welcome / OTP / password reset / magic link / arbitrary subject match?
2. Where do `IMAP_USER` (mailbox address) and `IMAP_PASSWORD` (Gmail **App Password**, or an OAuth2 XOAUTH2 token) come from in this environment? They are **secrets** — never commit them.

## IMAP surface (cheat-sheet — `imapflow` + `mailparser`)

| Call | Purpose |
|---|---|
| `new ImapFlow({ host, port: 993, secure: true, auth: { user, pass } })` | Construct (TLS on connect; inject creds, never hardcode) |
| `await client.connect()` | Open the TLS IMAP session |
| `const lock = await client.getMailboxLock('INBOX')` | Open + lock INBOX; `lock.release()` when done |
| `await client.search({ to, subject, since }, { uid: true })` | **Server-side** search → array of UIDs (don't fetch-all-then-filter) |
| `client.fetchOne(uid, { source: true }, { uid: true })` | Fetch one message's raw RFC-822 `source` (a Buffer) |
| `simpleParser(source)` | Parse → `{ subject, from, to, html, text, textAsHtml, attachments[] }` |
| `parsed.attachments[]` | `{ filename, contentType, size, content: Buffer }` |
| `client.messageFlagsAdd(uid, ['\\Seen'], { uid: true })` | Mark processed (cleanup, not a wipe) |
| `client.messageDelete(uid, { uid: true })` | Flag `\Deleted` + expunge (per-message cleanup) |
| `await client.logout()` | Close the session (always, in teardown) |

**`+tag` alias pattern:** Gmail (and many providers) route `youraccount+{anything}@gmail.com` and dotted variants to the *one* real inbox, but the `+tag` is preserved in the `To` header — so per test, send to `${base}+${crypto.randomUUID()}` and search server-side by that exact `to`. Combined with a `since` lower bound (test start time), every test owns a unique, time-bounded slice of the shared inbox with no wipe.

## Templates

### Config — `tests/integration/email/imap.config.ts`

Secrets come from the environment, validated once. Never inline the address or App Password.

```ts
function required(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`Missing required env var ${name} (IMAP secret).`);
  return v;
}

const baseAddress = required('IMAP_USER'); // e.g. flexinvest.qa@gmail.com

export const imapConfig = {
  host: process.env.IMAP_HOST ?? 'imap.gmail.com',
  port: Number(process.env.IMAP_PORT ?? 993),
  user: baseAddress,
  pass: required('IMAP_PASSWORD'), // Gmail App Password (or XOAUTH2 token)
  /** Real-provider delivery is slower than a sink — default budget is generous. */
  timeoutMs: Number(process.env.IMAP_TIMEOUT_MS ?? 25_000),
  pollMs: Number(process.env.IMAP_POLL_MS ?? 2_000),
} as const;

/** Per-test `+tag` alias into the one real inbox → independent, searchable, no wipe. */
export function aliasFor(prefix = 'qa'): string {
  const [local, domain] = baseAddress.split('@');
  return `${local}+${prefix}-${crypto.randomUUID()}@${domain}`;
}
```

### Intent-revealing wrapper — `tests/integration/email/mailbox.ts`

Specs never drive `search` / `fetch` directly. They call `awaitSignupEmail`, `awaitEmail`, `markProcessed`. Connection lifecycle (connect once, lock INBOX per poll, logout on teardown) lives here — specs never leak an IMAP connection.

```ts
import { ImapFlow } from 'imapflow';
import { simpleParser, type ParsedMail } from 'mailparser';
import { imapConfig } from './imap.config';

export interface FoundEmail {
  uid: number;
  message: ParsedMail;
}

export class Mailbox {
  private client: ImapFlow;

  constructor(private readonly config = imapConfig) {
    this.client = new ImapFlow({
      host: config.host,
      port: config.port,
      secure: true,
      auth: { user: config.user, pass: config.pass },
      logger: false,
    });
  }

  async connect(): Promise<void> {
    await this.client.connect();
  }

  async close(): Promise<void> {
    await this.client.logout();
  }

  /**
   * Poll the real inbox until a message to `sentTo` (+ optional subject), received
   * after `since`, arrives — or the deadline fires. NOT a fixed sleep: a deadline
   * loop over the server-side IMAP search, interval-paced.
   */
  async awaitEmail(
    sentTo: string,
    opts: { subject?: string; since?: Date; timeoutMs?: number; pollMs?: number } = {},
  ): Promise<FoundEmail> {
    const timeoutMs = opts.timeoutMs ?? this.config.timeoutMs;
    const pollMs = opts.pollMs ?? this.config.pollMs;
    const since = opts.since ?? new Date(Date.now() - 60_000);
    const deadline = Date.now() + timeoutMs;

    while (Date.now() < deadline) {
      const lock = await this.client.getMailboxLock('INBOX');
      try {
        const uids = await this.client.search(
          { to: sentTo, subject: opts.subject, since },
          { uid: true },
        );
        if (uids && uids.length > 0) {
          const uid = uids[uids.length - 1]; // newest match
          const msg = await this.client.fetchOne(uid, { source: true }, { uid: true });
          const message = await simpleParser(msg.source);
          return { uid, message };
        }
      } finally {
        lock.release();
      }
      await new Promise((r) => setTimeout(r, pollMs));
    }
    throw new Error(
      `No message to '${sentTo}'${opts.subject ? ` subject '${opts.subject}'` : ''} within ${timeoutMs}ms.`,
    );
  }

  awaitSignupEmail(sentTo: string, since?: Date): Promise<FoundEmail> {
    return this.awaitEmail(sentTo, { subject: 'Welcome', since });
  }

  /** Cleanup is per-message, not a wipe: flag processed (or delete + expunge). */
  async markProcessed(uid: number, mode: 'seen' | 'delete' = 'seen'): Promise<void> {
    const lock = await this.client.getMailboxLock('INBOX');
    try {
      if (mode === 'delete') {
        await this.client.messageDelete(uid, { uid: true });
      } else {
        await this.client.messageFlagsAdd(uid, ['\\Seen'], { uid: true });
      }
    } finally {
      lock.release();
    }
  }
}
```

### Extractors — `tests/integration/email/extractors.ts`

No provider-supplied `html.codes` here (that's a Mailosaur convenience) — extract structure with the same regexes as the Mailpit skill, against the `mailparser` output.

```ts
import type { ParsedMail } from 'mailparser';

const OTP_RE = /\b(\d{6})\b/;
const URL_RE = /https?:\/\/[^\s"'<>]+/gi;

export function extractOtp(message: ParsedMail): string {
  const body = message.text ?? message.html ?? '';
  const m = OTP_RE.exec(body);
  if (!m) throw new Error(`No 6-digit OTP found in "${message.subject}".`);
  return m[1];
}

export function extractLink(message: ParsedMail, mustContain: string): URL {
  const html = message.html || message.textAsHtml || '';
  for (const m of html.matchAll(URL_RE)) {
    if (m[0].toLowerCase().includes(mustContain.toLowerCase())) return new URL(m[0]);
  }
  throw new Error(`No link containing '${mustContain}' in "${message.subject}".`);
}
```

### Vitest test — signup welcome

```ts
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import request from 'supertest';
import { Mailbox } from './email/mailbox';
import { aliasFor } from './email/imap.config';
import { extractLink } from './email/extractors';
import { createApp } from '../../src/app';

const mailbox = new Mailbox();
const app = createApp();

beforeAll(() => mailbox.connect());
afterAll(() => mailbox.close());

describe('signup', () => {
  it('Should_SendWelcomeEmailWithActivationLink_When_UserSignsUp', async () => {
    const email = aliasFor('signup');
    const since = new Date(); // time-bound the search to this test

    await request(app).post('/auth/signup').send({ email, password: 'Str0ng!Passw0rd' }).expect(201);

    const { uid, message } = await mailbox.awaitSignupEmail(email, since);
    const activation = extractLink(message, '/activate?token=');

    expect(activation.searchParams.get('token')).toBeTruthy();
    await mailbox.markProcessed(uid, 'delete');
  });
});
```

### Playwright fixture — `tests/e2e/fixtures/mailbox.ts`

The fixture owns the connection lifecycle so specs never leak an IMAP session, and hands each test a fresh `+tag` alias.

```ts
import { test as base } from '@playwright/test';
import { Mailbox } from '../../integration/email/mailbox';
import { aliasFor } from '../../integration/email/imap.config';

export const test = base.extend<{ mailbox: Mailbox; recipient: string }>({
  mailbox: async ({}, use) => {
    const m = new Mailbox();
    await m.connect();
    await use(m);
    await m.close();
  },
  recipient: async ({}, use) => use(aliasFor('e2e')),
});
export { expect } from '@playwright/test';
```

```ts
import { test, expect } from './fixtures/mailbox';
import { extractOtp } from '../integration/email/extractors';

test('reset password via emailed OTP', async ({ page, mailbox, recipient }) => {
  const since = new Date();
  await page.goto('/auth/reset');
  await page.getByLabel('Email').fill(recipient);
  await page.getByRole('button', { name: 'Send code' }).click();

  const { uid, message } = await mailbox.awaitEmail(recipient, { subject: 'Reset code', since });
  const otp = extractOtp(message);

  await page.getByLabel('Code').fill(otp);
  await page.getByLabel('New password').fill('Brand-N3w!');
  await page.getByRole('button', { name: 'Reset' }).click();
  await expect(page.getByText('Password updated')).toBeVisible();
  await mailbox.markProcessed(uid, 'delete');
});
```

### Attachment assertion

```ts
it('Should_AttachPdfInvoice_When_InvoiceEmailed', async () => {
  const email = aliasFor('billing');
  const since = new Date();
  await request(app).post(`/invoices/${invoiceId}/email`).send({ to: email }).expect(202);

  const { uid, message } = await mailbox.awaitEmail(email, { subject: 'Invoice', since });
  const pdf = message.attachments.find((a) => a.contentType === 'application/pdf');
  expect(pdf, 'expected a PDF attachment').toBeDefined();

  expect(pdf!.filename).toMatch(/^invoice-/);
  expect(pdf!.content.subarray(0, 4)).toEqual(Buffer.from('%PDF')); // magic bytes
  await mailbox.markProcessed(uid, 'delete');
});
```

## Rules

### Inbox isolation (no unique inbox, no wipe)
- **Per-test `+tag` alias** via `aliasFor()` — `base+{uuid}@domain` all land in the one real inbox but carry a unique `To`. Search by that exact `to`.
- **Always `since`-bound the search** to the test's start time. The real inbox accumulates history; an unbounded search will match stale mail.
- Search **server-side by To + Subject + since** (`client.search({...})`). Never fetch-all-then-filter client-side.
- Cleanup is **per message**: flag `\Seen` or `\Deleted` + expunge via `markProcessed`. There is no Mailpit-style wipe and no Mailosaur-style unique-inbox throwaway — never `expunge` the whole INBOX.

### Waiting (poll-with-deadline, never a fixed sleep)
- The wait is the `awaitEmail` **deadline loop** over the IMAP search. No bare `setTimeout` / `page.waitForTimeout` between send and assert.
- Default budget ~25s (real delivery is slower than a sink). Bump per call with a comment, not globally.
- Pace the poll (`pollMs`, ~2s) — don't hammer the provider; Gmail throttles aggressive IMAP polling.

### Connection lifecycle
- Connect once per fixture/suite; `logout()` in teardown. Never leak IMAP connections across tests.
- Lock INBOX (`getMailboxLock`) around each search/fetch and `release()` in `finally` — imapflow serialises mailbox access.

### Body assertions
- Extract structure (links via `html`, OTP via `text`) and assert a **user-visible outcome** (token present, "Password updated" shown). Don't substring-match the full HTML — copy changes break those tests.
- Visual / template-shape checks → `qa/visual-regression/playwright-snapshots/typescript`.

### Attachments
- Validate content type **and** magic bytes for binaries (`%PDF`, `PK`, `\x89PNG`). Check `size` before trusting large payloads.

### Secrets
- `IMAP_USER` + `IMAP_PASSWORD` are secrets. The password is a Gmail **App Password** (2FA required; "less secure app access" is gone) — the pragmatic CI choice. **OAuth2 XOAUTH2** is the more-secure option for long-lived setups. Read from env / secret store; never in code or a committed `.env`. In CI pull them per `qa/ci-pipelines/github-actions/typescript`.

### What NOT to do
- No hardcoded mailbox address or App Password.
- No unbounded search — always `since`-bound, always by exact `to`.
- No `Thread.Sleep`-equivalent fixed wait — use the deadline poll.
- No whole-INBOX wipe/expunge — clean up per message only.
- No assertions on the entire HTML body string.
- No shared single alias across tests — one `+tag` per test.

## Generation steps

1. Read `package.json` (Vitest vs Jest, Playwright presence) and existing `tests/` fixtures for house style.
2. Confirm `imapflow` + `mailparser` are installed (`npm i -D imapflow mailparser`) and that `IMAP_USER` / `IMAP_PASSWORD` (App Password) are wired into the test env (not committed).
3. Generate:
   - `tests/integration/email/imap.config.ts`
   - `tests/integration/email/mailbox.ts`
   - `tests/integration/email/extractors.ts`
   - Concrete `{flow}-email.int.test.ts` / Playwright spec per scenario.
4. Run `npm run test:integration` (or the existing script) with the secrets present.

## Cross-references

- **`qa/email-testing/mailosaur/typescript`**, **`qa/email-testing/mailpit/typescript`** — the other two email siblings. See the three-way pick table above: real provider (here) vs hosted SaaS vs self-hosted sink.
- **`qa/email-testing/gmail-imap/dotnet`** (MailKit), **`qa/email-testing/gmail-imap/java`** (Jakarta Mail) — sibling stacks; same wrapper shape, same poll-with-deadline wait.
- **`qa/ci-pipelines/github-actions/typescript`** — where these specs run in CI and where the `IMAP_PASSWORD` App Password secret is sourced (OIDC / encrypted secrets), never hardcoded.
- **`qa/test-data-builder/typescript`** — generate per-test `+tag` aliases through a builder.
- **`qa/db-testing/testcontainers/typescript`** — signup creates a DB row *and* sends an email; assert both.

## Sources synthesized (research-first per CLAUDE.md)

- [postalsys/imapflow — README](https://github.com/postalsys/imapflow) — `connect()`, `getMailboxLock`, `search({ to, subject, since })`, `fetchOne(..., { source: true })`, `messageFlagsAdd` / `messageDelete`, `logout()`.
- [Use Gmail account by ImapFlow for mail testing](https://blog.siposdani87.com/posts/use-gmail-account-by-imapflow-for-mail-testing) — `imap.gmail.com:993` + App Password config, connect/lock/fetch/release flow.
- [How to Test Received Emails with Cypress, Ethereal, and ImapFlow](https://www.codemancers.com/blog/2023-06-26-how-to-test-received-emails-with-cypress-ethereal-and-imapflow) — imapflow + `mailparser` `simpleParser` integration-test shape.
- [nodemailer/mailparser — `simpleParser`](https://nodemailer.com/extras/mailparser/) — parsed `{ subject, from, to, html, text, textAsHtml, attachments }` shape.

## Changelog

- 2026-05-31: Authored as the canonical TypeScript skill for the gmail-imap node (`qa/GAP-ANALYSIS.md` row 6). Anchors the 3-stack family on `imapflow` + `mailparser` and the poll-with-deadline IMAP wait (no per-test unique inbox, no wipe; `+tag` alias + `since` bound + per-message flag cleanup).
