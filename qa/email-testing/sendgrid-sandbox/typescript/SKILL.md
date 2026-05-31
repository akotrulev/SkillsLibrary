---
name: qa-email-testing-sendgrid-sandbox-typescript
description: Use when the user asks to validate the SUT's *outbound* mail-send request through SendGrid **sandbox mode** in TypeScript (Vitest / Jest) integration tests with the official `@sendgrid/mail` SDK — build a `MailDataRequired` (template ID + dynamic template data + personalizations + from/reply-to + categories), send it with `mailSettings.sandboxMode.enable = true` so SendGrid fully validates the request but delivers nothing, assert the API returns 2xx, and assert on the locally-built `Mail` payload before the network even runs. Triggers: "test our SendGrid send without delivering email", "validate the template ID and dynamic data against SendGrid", "sandbox-mode SendGrid integration test", "assert the Mail payload our notifier builds". Do NOT use for asserting on a *received / delivered* message — there is no inbox, no poll, no wait here (real Gmail mailbox → `qa/email-testing/gmail-imap/typescript`; hosted Mailosaur inbox → `qa/email-testing/mailosaur/typescript`; self-hosted SMTP sink → `qa/email-testing/mailpit/typescript`) — or for .NET / JVM stacks (`qa/email-testing/sendgrid-sandbox/{dotnet,java}`).
---

# QA — Validate Outbound Mail via SendGrid Sandbox Mode (TypeScript)

Scaffolds a thin, intent-revealing wrapper over the official `@sendgrid/mail` SDK (Node 20 + TS) plus Vitest helpers that **validate the SUT's send request without delivering any email**. With `mailSettings.sandboxMode.enable = true`, SendGrid runs its real validator over the form, type, and shape of the request — template IDs, personalizations, dynamic template data, `from` / `reply-to`, categories — accepts a valid one with **`200 OK`** (note: not the `202 Accepted` a real send returns), and **delivers nothing**. A malformed request surfaces as **`4xx` with an error body**.

This is the **"no inbox at all"** sibling. The other three email skills all assert on a *captured / delivered* message; **this one never produces a received message** — there is no SMTP sink, no IMAP poll, no `messages.get`. Two consequences shape the whole skill:

- **There is no wait — at all.** No `waitFor`, no poll loop, no `setTimeout` / `waitForTimeout`. A send under sandbox mode is a single request/response: you `await client.send(msg)` and assert on the `ClientResponse.statusCode`. There is nothing to arrive, so there is nothing to wait for.
- **The strongest check needs no network and no secret.** Because the request is built locally before it goes anywhere, the deterministic assertion is on the **constructed `Mail` payload itself** — recipient, subject, `templateId`, `dynamicTemplateData`, categories, `from` / `reply-to`. That test runs offline, in milliseconds, with no `SENDGRID_API_KEY`. The sandbox round-trip then adds one thing the local check can't: confirmation that SendGrid's **real** validator accepts the payload (catching template-ID typos, malformed personalizations, bad dynamic-data shape) — without sending an email or needing a mailbox.

## When to use

- Asserting the SUT builds a **well-formed** transactional send: correct template ID, dynamic data keys, recipients, `from` / `reply-to`, categories
- Catching template-ID typos and malformed personalizations / dynamic-data shape against SendGrid's **real** validator, in CI, without delivering mail or owning a mailbox
- Unit/integration-testing the mail-notification layer (a `Notifier`) in isolation — inject a fake client to assert the exact payload offline, or flip sandbox on for the live validate round-trip
- Fast, deterministic CI where standing up an inbox (IMAP / Mailosaur / Mailpit) is overkill because you only need "is our send request valid and accepted?"

## When NOT to use

- You must assert on a **delivered / received** message (body rendered, link clickable, OTP extracted, attachment present) — sandbox mode delivers **nothing**:
  - Real provider mailbox over IMAP → `qa/email-testing/gmail-imap/typescript`
  - Hosted SaaS inbox + SMS → `qa/email-testing/mailosaur/typescript`
  - Self-hosted SMTP sink, offline CI → `qa/email-testing/mailpit/typescript`
- The SUT doesn't send through SendGrid's Mail Send API (uses raw SMTP, SES, etc.) → use one of the inbox siblings
- Production deliverability / DKIM / SPF / template-render auditing — sandbox proves the **request** is valid, **not** that a human-readable email rendered or was delivered
- .NET or JVM stacks → `qa/email-testing/sendgrid-sandbox/{dotnet,java}`

## sendgrid-sandbox vs gmail-imap vs mailosaur vs mailpit — pick the right sibling

| | **sendgrid-sandbox** (this skill) | **gmail-imap** (`.../gmail-imap/typescript`) | **mailosaur** (`.../mailosaur/typescript`) | **mailpit** (`.../mailpit/typescript`) |
|---|---|---|---|---|
| What it asserts on | The **send request** the SUT builds + that SendGrid accepts it | A **received** message in a real provider inbox | A **received** message in a hosted SaaS inbox | A **received** message in a self-hosted sink |
| Produces a received message? | **No — nothing is delivered** | Yes (real MX → inbox) | Yes (real provider → Mailosaur) | Yes (SUT's SMTP → sink) |
| Wait primitive | **None** — single request/response | Poll IMAP search with a deadline | SDK `messages.get(..., {timeout})` blocks | Poll HTTP search with a deadline |
| Per-test isolation | None needed (no inbox) | `+tag` alias + `since` bound | Unique `{uuid}@{serverId}.mailosaur.net` | `DELETE /api/v1/messages` |
| Secrets | `SENDGRID_API_KEY` (live check only) | Mailbox + App Password | API key + server ID | None |
| Offline CI | ✅ for the **payload** check; ❌ for the validate round-trip | ❌ | ❌ | ✅ |
| Catches | Template-ID typos, bad dynamic-data shape, malformed personalizations | Real deliverability, body/links/OTP, attachments | Same as gmail-imap, plus SMS | Same, fully offline |

Pick **sendgrid-sandbox** to prove the SUT's send request is **valid and accepted** without delivering mail; pick any of the other three when the test must assert on a message that was actually **received**.

## Inputs needed

Ask at most 2 questions; infer the rest from `package.json` and existing fixtures.

1. Scenario: welcome / password-reset / arbitrary transactional template — and which dynamic-data keys does it carry?
2. Where does `SENDGRID_API_KEY` come from in this environment (CI secret store, `.env.test`)? It is the **one** secret and is needed **only** for the live sandbox round-trip — the payload check needs no key. Never commit it.

## SendGrid SDK surface (cheat-sheet — `@sendgrid/mail`)

| Call | Purpose |
|---|---|
| `import { MailService } from '@sendgrid/mail'` / `new MailService()` | An injectable client instance (the default export is a shared singleton — prefer an instance for DI) |
| `client.setApiKey(key)` | Inject the API key (never hardcode); needed only to actually call the API |
| `await client.send(msg)` | Send → resolves to `[ClientResponse, {}]`. Under sandbox: validates, delivers nothing |
| `MailDataRequired` | The message type: `to`, `from`, `replyTo`, `subject`, `templateId`, `dynamicTemplateData`, `personalizations`, `categories`, `mailSettings` |
| `msg.mailSettings = { sandboxMode: { enable: true } }` | **Sandbox**: full validation, no delivery → `200 OK` (real send → `202 Accepted`) |
| `msg.templateId` + `msg.dynamicTemplateData` | Dynamic template + its data object (the substitutions the template renders) |
| `msg.personalizations[]` | Per-recipient `to` / `dynamicTemplateData` blocks for multi-recipient sends |
| `msg.categories` | Tags for analytics/segmentation — assert they're set correctly |
| `response.statusCode` | `200` under sandbox (valid, undelivered); `202` for a real accepted send; `4xx` on a malformed request |

**Key point:** sandbox mode lives on the **message** (`mailSettings.sandboxMode.enable`), not on the client. Keep the message *builders* pure (no key, no client, no sandbox flag) so they serve production too; let the `Notifier` decide whether to flip sandbox on — that way specs assert on the pure payload offline and never poke `mailSettings` themselves.

## Templates

### Config — `tests/integration/email/sendgrid.config.ts`

Template IDs + `from` are non-secret defaults (so the payload check needs no secret). The API key is read lazily and **only** when a live send actually happens.

```ts
function required(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`Missing required env var ${name} (SendGrid secret).`);
  return v;
}

/** Non-secret send defaults — usable offline by the pure builders, no API key required. */
export const mailDefaults = {
  from: process.env.SENDGRID_FROM ?? 'no-reply@flexinvest.test',
  replyTo: process.env.SENDGRID_REPLY_TO ?? 'support@flexinvest.test',
  templates: {
    welcome: process.env.SENDGRID_TEMPLATE_WELCOME ?? 'd-welcome00000000000000000000000',
    passwordReset: process.env.SENDGRID_TEMPLATE_RESET ?? 'd-reset000000000000000000000000',
  },
} as const;

/** The ONE secret, read lazily — only the live sandbox round-trip needs it. */
export function sendgridApiKey(): string {
  return required('SENDGRID_API_KEY');
}
```

### Pure message builders — `tests/integration/email/messages.ts`

No client, no key, no sandbox flag — just the `Mail` the SUT would send. This is what the deterministic, offline, no-secret test asserts on.

```ts
import type { MailDataRequired } from '@sendgrid/mail';
import { mailDefaults } from './sendgrid.config';

export function welcomeMessage(
  to: string,
  data: { firstName: string; activationUrl: string },
): MailDataRequired {
  return {
    to,
    from: mailDefaults.from,
    replyTo: mailDefaults.replyTo,
    templateId: mailDefaults.templates.welcome,
    dynamicTemplateData: { first_name: data.firstName, activation_url: data.activationUrl },
    categories: ['welcome', 'transactional'],
  };
}

export function passwordResetMessage(
  to: string,
  data: { otp: string },
): MailDataRequired {
  return {
    to,
    from: mailDefaults.from,
    replyTo: mailDefaults.replyTo,
    templateId: mailDefaults.templates.passwordReset,
    dynamicTemplateData: { otp: data.otp },
    categories: ['password-reset', 'transactional'],
  };
}
```

### Intent-revealing wrapper — `tests/integration/email/notifier.ts`

Specs call `sendWelcome` / `sendPasswordReset`, never `client.send` or `mailSettings`. The `Notifier` injects the client (constructor injection — pass a fake in unit tests) and owns the sandbox decision. `buildWelcome` is exposed so a test can assert the final, sandbox-applied payload without sending.

```ts
import { MailService } from '@sendgrid/mail';
import type { ClientResponse, MailDataRequired } from '@sendgrid/mail';
import { welcomeMessage, passwordResetMessage } from './messages';
import { sendgridApiKey } from './sendgrid.config';

export class Notifier {
  constructor(
    private readonly client: MailService,
    private readonly sandbox = false,
  ) {}

  /** Apply sandbox mode at send time so the pure builders stay production-usable. */
  private prepare(msg: MailDataRequired): MailDataRequired {
    return this.sandbox
      ? { ...msg, mailSettings: { ...msg.mailSettings, sandboxMode: { enable: true } } }
      : msg;
  }

  buildWelcome(to: string, data: { firstName: string; activationUrl: string }): MailDataRequired {
    return this.prepare(welcomeMessage(to, data));
  }

  async sendWelcome(
    to: string,
    data: { firstName: string; activationUrl: string },
  ): Promise<ClientResponse> {
    const [response] = await this.client.send(this.buildWelcome(to, data));
    return response;
  }

  async sendPasswordReset(to: string, data: { otp: string }): Promise<ClientResponse> {
    const [response] = await this.client.send(this.prepare(passwordResetMessage(to, data)));
    return response;
  }
}

/** Canonical test entry-point: a real client in sandbox mode. Reads the key lazily. */
export function sandboxNotifier(): Notifier {
  const client = new MailService();
  client.setApiKey(sendgridApiKey());
  return new Notifier(client, true);
}
```

### Vitest — deterministic payload check (offline, no secret)

The strongest assertion runs without the network or the API key: the builder produced the right shape. Multiple `expect`s, one behavior — "the welcome message is well-formed".

```ts
import { describe, it, expect } from 'vitest';
import { welcomeMessage } from './email/messages';
import { mailDefaults } from './email/sendgrid.config';

describe('welcome message payload', () => {
  it('Should_AddressTemplatedWelcomeWithActivationData_When_Built', () => {
    const msg = welcomeMessage('jane@acme.test', {
      firstName: 'Jane',
      activationUrl: 'https://app.flexinvest.test/activate?token=abc123',
    });

    expect(msg.to).toBe('jane@acme.test');
    expect(msg.from).toBe(mailDefaults.from);
    expect(msg.templateId).toBe(mailDefaults.templates.welcome);
    expect(msg.dynamicTemplateData).toMatchObject({
      first_name: 'Jane',
      activation_url: expect.stringContaining('token='),
    });
    expect(msg.categories).toContain('welcome');
  });
});
```

### Vitest — Notifier applies sandbox, sends valid payload (offline, fake client)

Constructor injection lets us assert the exact payload handed to `send` — sandbox flag included — with zero network and no secret.

```ts
import { describe, it, expect, vi } from 'vitest';
import { MailService } from '@sendgrid/mail';
import { Notifier } from './email/notifier';

describe('Notifier in sandbox mode', () => {
  it('Should_EnableSandboxOnTheSentMessage_When_SandboxNotifier', async () => {
    const client = new MailService();
    const send = vi
      .spyOn(client, 'send')
      .mockResolvedValue([{ statusCode: 200, headers: {}, body: {} } as never, {}]);
    const notifier = new Notifier(client, true);

    await notifier.sendPasswordReset('jane@acme.test', { otp: '123456' });

    const [sent] = send.mock.calls[0];
    expect(sent).toMatchObject({
      to: 'jane@acme.test',
      mailSettings: { sandboxMode: { enable: true } },
    });
  });
});
```

### Vitest — live sandbox round-trip (SendGrid's real validator accepts it)

The only test that touches the network and needs the key. No wait, no inbox — just assert the status code. `200` means the payload is valid and **nothing was delivered**.

```ts
import { describe, it, expect } from 'vitest';
import { sandboxNotifier } from './email/notifier';

describe('SendGrid sandbox validation', () => {
  it('Should_Return200AndDeliverNothing_When_SentInSandboxMode', async () => {
    const notifier = sandboxNotifier();

    const response = await notifier.sendWelcome('jane@acme.test', {
      firstName: 'Jane',
      activationUrl: 'https://app.flexinvest.test/activate?token=abc123',
    });

    // 200 under sandbox (a real, accepted send returns 202); the email is never delivered.
    expect(response.statusCode).toBe(200);
  });
});
```

### Vitest — a malformed template ID is rejected by the validator

Sandbox catches what the local check can't: SendGrid's validator rejects a bad template ID with a `4xx`. The SDK throws on non-2xx, so assert the rejection.

```ts
import { describe, it, expect } from 'vitest';
import { MailService } from '@sendgrid/mail';
import { Notifier } from './email/notifier';
import { sendgridApiKey } from './email/sendgrid.config';

describe('SendGrid sandbox validation', () => {
  it('Should_Reject_When_TemplateIdIsMalformed', async () => {
    const client = new MailService();
    client.setApiKey(sendgridApiKey());
    const notifier = new Notifier(client, true);

    // 'not-a-template' is not a valid dynamic-template ID → SendGrid validates and rejects.
    await expect(
      client.send({
        to: 'jane@acme.test',
        from: 'no-reply@flexinvest.test',
        templateId: 'not-a-template',
        mailSettings: { sandboxMode: { enable: true } },
      }),
    ).rejects.toThrow();
  });
});
```

## Rules

### Sandbox mode (validate-only, no delivery)
- Sandbox lives on the **message** (`mailSettings.sandboxMode.enable = true`), not the client. Apply it in the `Notifier`, not in specs — specs never poke `mailSettings`.
- A valid sandbox send returns **`200`**, a real accepted send returns **`202`**. Assert `200` in sandbox tests; a `202` means sandbox was **not** actually on (and you may have delivered mail).
- Sandbox proves the **request** is valid — **not** that a human-readable email rendered or was delivered. For body/render/delivery assertions, use the inbox siblings.

### No wait, no inbox
- There is **no** poll, **no** `waitFor`, **no** `setTimeout` / `waitForTimeout`. A send is one request/response. If you find yourself waiting for something to arrive, you want a different sibling.
- Nothing to clean up — no inbox, no messages, no per-test isolation. Tests are independent by construction.

### Payload-first assertions
- Make the **offline payload check** the primary assertion: `to`, `from` / `replyTo`, `templateId`, `dynamicTemplateData`, `categories`. It needs no key and no network and catches the most common mistakes.
- Use the live sandbox round-trip to add what local checks can't: SendGrid's real validator accepting (or rejecting) the payload.
- Don't assert on rendered HTML or links — nothing rendered. That's an inbox-sibling concern.

### Secrets
- `SENDGRID_API_KEY` is the **only** secret and is needed **only** for the live sandbox round-trip. Read it lazily (`sendgridApiKey()`), never at module top-level, so the payload check stays key-free. Never commit it; in CI pull it per `qa/ci-pipelines/github-actions/typescript`.

### What NOT to do
- No hardcoded API key.
- No poll / wait / sleep of any kind — this is request/response.
- No asserting `202` in a sandbox test (that means delivery happened).
- No `mailSettings` poking in specs — the `Notifier` owns sandbox.
- No body/render/link/attachment assertions — nothing is delivered; use an inbox sibling.
- No reading the API key at import time — it would break the offline payload check.

## Generation steps

1. Read `package.json` (Vitest vs Jest) and existing `tests/` fixtures for house style.
2. Confirm `@sendgrid/mail` is installed (`npm i -D @sendgrid/mail`) and that `SENDGRID_API_KEY` (+ optional `SENDGRID_TEMPLATE_*`, `SENDGRID_FROM`) are wired into the test env for the live check (not committed).
3. Generate:
   - `tests/integration/email/sendgrid.config.ts`
   - `tests/integration/email/messages.ts`
   - `tests/integration/email/notifier.ts`
   - Concrete `{flow}-mail.int.test.ts` — at minimum the offline payload check + the live sandbox round-trip.
4. Run the offline checks anywhere (`npm run test:unit`); run the live sandbox test with `SENDGRID_API_KEY` present.

## Cross-references

- **`qa/email-testing/gmail-imap/typescript`**, **`qa/email-testing/mailosaur/typescript`**, **`qa/email-testing/mailpit/typescript`** — the three inbox siblings. See the four-way pick table: this skill validates the **send request** and delivers nothing; those three assert on a **received** message (real provider / hosted SaaS / self-hosted sink).
- **`qa/email-testing/sendgrid-sandbox/dotnet`** (`SendGrid` NuGet), **`qa/email-testing/sendgrid-sandbox/java`** (`com.sendgrid:sendgrid-java`) — the sibling stacks; same builder + `Notifier` shape, same `200`-under-sandbox assertion.
- **`qa/ci-pipelines/github-actions/typescript`** — where these tests run in CI and where the `SENDGRID_API_KEY` secret is sourced (OIDC / encrypted secrets), never hardcoded.
- **`qa/test-data-builder/typescript`** — build the `dynamicTemplateData` objects through a builder when they grow past 4 fields.

## Sources synthesized (research-first per CLAUDE.md)

- [Sandbox Mode | SendGrid Docs (Twilio)](https://www.twilio.com/docs/sendgrid/for-developers/sending-email/sandbox-mode) — `mail_settings.sandbox_mode.enable` validates form/type/shape, **never delivers**, returns `200 OK` (vs `202 Accepted` for a real send); errors surface as `4xx` with a body.
- [sendgrid/sendgrid-nodejs — README](https://github.com/sendgrid/sendgrid-nodejs) — `setApiKey`, `send(msg)` resolving to `[ClientResponse, {}]`, `MailDataRequired` fields (`templateId`, `dynamicTemplateData`, `personalizations`, `categories`, `mailSettings`).
- [How to enable sandbox · Issue #612 · sendgrid/sendgrid-nodejs](https://github.com/sendgrid/sendgrid-nodejs/issues/612) — `mailSettings: { sandboxMode: { enable: true } }` on the message object.

## Changelog

- 2026-05-31: Authored as the canonical TypeScript skill for the sendgrid-sandbox node (`qa/GAP-ANALYSIS.md` row 7). Anchors the 3-stack family on `@sendgrid/mail` sandbox mode — the "validate-send-only, no inbox, no wait" sibling: assert the locally-built `Mail` payload offline + a `200`-under-sandbox live round-trip. Closes the `email-testing` family.
