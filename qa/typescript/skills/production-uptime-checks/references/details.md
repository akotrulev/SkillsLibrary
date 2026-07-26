# Deep-dive details — `qa-production-uptime-checks-typescript`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Alerting + SLA thresholds — the part that makes it a monitor

A check that fails into the void is useless. **Alert channels** are shared constructs attached to checks;
the **retry strategy** absorbs a single transient blip so on-call isn't paged for nothing, while a *sustained*
failure does page.

```typescript
// monitoring/src/alert-channels.ts
import { EmailAlertChannel, SlackAlertChannel, PagerdutyAlertChannel } from 'checkly/constructs';

export const emailChannel = new EmailAlertChannel('email-oncall', {
  address: 'oncall@acme.example',
  sendFailure: true,
  sendRecovery: true,
  sendDegraded: true,       // the SLA-breach (degradedResponseTime) signal — slow-but-up is still worth knowing
  sslExpiry: true,
  sslExpiryThreshold: 30,   // also alert 30 days before the TLS cert expires
});

export const slackChannel = new SlackAlertChannel('slack-alerts', {
  url: process.env.SLACK_WEBHOOK_URL!,   // secret from env, NEVER committed
  channel: '#storefront-alerts',
});

export const pagerdutyChannel = new PagerdutyAlertChannel('pd-oncall', {
  serviceKey: process.env.PAGERDUTY_KEY!,
});
```

```typescript
// Retry strategy — bounded, so a flake doesn't page, but a real outage does. Attach per-check or per-group.
import { RetryStrategyBuilder } from 'checkly/constructs';

const retryStrategy = RetryStrategyBuilder.linearStrategy({
  maxRetries: 2,            // bounded — like the flaky-quarantine cap, this is a SAFETY knob, not a mask
  baseBackoffSeconds: 30,
  sameRegion: false,        // retry from a DIFFERENT region — distinguishes a regional blip from a real outage
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
// then on a check: new ApiCheck('...', { group: storefrontGroup, ... })
```
