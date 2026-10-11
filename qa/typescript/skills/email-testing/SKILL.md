---
name: email-testing
description: Use when a Node 24 / TypeScript / Vitest test suite must capture and assert email the SUT sends. Triggers "assert the welcome email was sent", "extract the OTP/reset link from the email", "test email content/recipients". Pick the sink in the decision matrix, then read its reference file. Do NOT use for broker messages (use `qa-typescript:messaging-testing`) or for in-app notification UI (use `qa-typescript:ui-tests-playwright`).
---

# QA — Email Testing (TypeScript)

One registered skill, 4 tools — a project uses exactly one. Identify the project's tool
(dependencies, docker-compose, infra config; ask one question if ambiguous), then **read the matching
`references/<tool>.md` end-to-end before writing any code** — it carries the full model, patterns,
templates, anti-patterns, and hard rules for that tool. This file only routes and holds the rules
shared by every tool in the family.

## Tools in this family

| Read | Use when |
|------|----------|
| `references/mailpit.md` | Local/dev SMTP sink — fastest feedback, no external account, runs in Docker/Testcontainers |
| `references/mailosaur.md` | Hosted inbox SaaS — real MX delivery path, team-visible inbox, spam analysis |
| `references/gmail-imap.md` | Real Gmail mailbox over IMAP — true end-to-end delivery through the real provider |
| `references/sendgrid-sandbox.md` | SendGrid sandbox mode — assert the send-API call without delivering anything |

## Decision matrix — pick the tool

| | **sendgrid-sandbox** (`references/sendgrid-sandbox.md`) | **gmail-imap** (`.../gmail-imap/typescript`) | **mailosaur** (`.../mailosaur/typescript`) | **mailpit** (`.../mailpit/typescript`) |
|---|---|---|---|---|
| What it asserts on | The **send request** the SUT builds + that SendGrid accepts it | A **received** message in a real provider inbox | A **received** message in a hosted SaaS inbox | A **received** message in a self-hosted sink |
| Produces a received message? | **No — nothing is delivered** | Yes (real MX → inbox) | Yes (real provider → Mailosaur) | Yes (SUT's SMTP → sink) |
| Wait primitive | **None** — single request/response | Poll IMAP search with a deadline | SDK `messages.get(..., {timeout})` blocks | Poll HTTP search with a deadline |
| Per-test isolation | None needed (no inbox) | `+tag` alias + `since` bound | Unique `{uuid}@{serverId}.mailosaur.net` | `DELETE /api/v1/messages` |
| Secrets | `SENDGRID_API_KEY` (live check only) | Mailbox + App Password | API key + server ID | None |
| Offline CI | ✅ for the **payload** check; ❌ for the validate round-trip | ❌ | ❌ | ✅ |
| Catches | Template-ID typos, bad dynamic-data shape, malformed personalizations | Real deliverability, body/links/OTP, attachments | Same as gmail-imap, plus SMS | Same, fully offline |

Pick **sendgrid-sandbox** to prove the SUT's send request is **valid and accepted** without delivering mail; pick any of the other three when the test must assert on a message that was actually **received**.

## Shared rules (every tool in this family)

- Unique recipient or subject token per test — no inbox cross-talk between tests.
- Condition-wait for arrival — never a sleep.
- Assert parsed content (links, codes, recipients), not raw MIME string equality.
- Clean the sink/inbox per test or use per-test addresses.

## Cross-references

Each `references/<tool>.md` carries its own cross-references to sibling skills (DB verification,
test environments, CI, chaos). Route there after picking the tool.
