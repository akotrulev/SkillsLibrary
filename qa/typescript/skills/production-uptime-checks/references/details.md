# Deep-dive details — `qa-production-uptime-checks-typescript`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Alerting + SLA thresholds — the part that makes it a monitor

A check that fails into the void is useless. **Alert channels** are shared constructs attached to checks;
the **retry strategy** absorbs a single transient blip so on-call isn't paged for nothing, while a *sustained*
failure does page. `sendDegraded` carries the SLA-breach (`degradedResponseTime`) signal — slow-but-up is
still worth knowing — and `sslExpiryThreshold` alerts 30 days before the TLS certificate expires. Webhook URLs
and service keys come from env, never committed.

```typescript
import { EmailAlertChannel, SlackAlertChannel, PagerdutyAlertChannel } from 'checkly/constructs';

export const emailChannel = new EmailAlertChannel('email-oncall', {
  address: 'oncall@acme.example',
  sendFailure: true,
  sendRecovery: true,
  sendDegraded: true,
  sslExpiry: true,
  sslExpiryThreshold: 30,
});

export const slackChannel = new SlackAlertChannel('slack-alerts', {
  url: process.env.SLACK_WEBHOOK_URL!,
  channel: '#storefront-alerts',
});

export const pagerdutyChannel = new PagerdutyAlertChannel('pd-oncall', {
  serviceKey: process.env.PAGERDUTY_KEY!,
});
```

`monitoring/src/alert-channels.ts`. The retry strategy is bounded, so a flake doesn't page but a real outage
does — a safety knob like the flaky-quarantine cap, never a mask. `sameRegion: false` retries from a different
region, which tells a regional blip from a real outage. Attach it per check or per group.

```typescript
import { RetryStrategyBuilder } from 'checkly/constructs';

const retryStrategy = RetryStrategyBuilder.linearStrategy({
  maxRetries: 2,
  baseBackoffSeconds: 30,
  sameRegion: false,
});
```

Share schedule + locations + alerts across a set of checks with a **`CheckGroup`**:

```typescript
import { CheckGroup, Frequency } from 'checkly/constructs';

export const storefrontGroup = new CheckGroup('storefront-group', {
  name: 'Storefront',
  frequency: Frequency.EVERY_5M,
  locations: ['us-east-1', 'eu-west-1'],
  alertChannels: [emailChannel, slackChannel],
  retryStrategy,
});
```

A check joins the group with `group: storefrontGroup` and inherits its schedule, locations, alerts and retry.

## Secrets from env, never logged

Target URLs, API keys, and test-user creds come from the environment — read lazily, never committed, never
logged. Checkly env vars with **`secret: true`** are write-only (masked in output, traces, and the UI):

```typescript
environmentVariables: [
  { key: 'BASE_URL', value: 'https://staging.acme.example' },
  { key: 'E2E_PASSWORD', value: process.env.SYNTHETIC_PASSWORD!, secret: true },
],
```

In CI, `CHECKLY_API_KEY` and `CHECKLY_ACCOUNT_ID` come from the secret store, never `checkly.config.ts`;
`npx checkly test -e BASE_URL=https://staging.acme.example --record` overrides a variable per run.

## The CI workflow — gate, then deploy

The pipeline runs `checkly test --record` to gate the merge, then (on main,
after deploy) `checkly deploy --force` to promote the monitoring config (`qa-ci-pipelines-typescript` wires it):

```yaml
- name: Synthetic dry-run (gate the PR)
  run: npx checkly test --record --reporter=github
  env: { CHECKLY_API_KEY: ${{ secrets.CHECKLY_API_KEY }}, CHECKLY_ACCOUNT_ID: ${{ secrets.CHECKLY_ACCOUNT_ID }} }

- name: Deploy the monitors (main only, post-deploy)
  if: github.ref == 'refs/heads/main'
  run: npx checkly deploy --force
  env: { CHECKLY_API_KEY: ${{ secrets.CHECKLY_API_KEY }}, CHECKLY_ACCOUNT_ID: ${{ secrets.CHECKLY_ACCOUNT_ID }} }
```
