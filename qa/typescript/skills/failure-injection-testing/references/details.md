# Deep-dive details — `qa-failure-injection-testing-typescript`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## The mechanism — proxy BETWEEN app and dependency (idea #2)

Stand the dependency and Toxiproxy up on a **shared Docker `Network`**, create a proxy whose **upstream** is the
dependency and whose **listen** side is what the app connects to, then **point the app at the proxy's mapped
port**. Everything downstream flows through the fault point.

```ts
// tests/support/chaos/startChaos.ts
import { Network, type StartedNetwork } from 'testcontainers';
import { PostgreSqlContainer, type StartedPostgreSqlContainer } from '@testcontainers/postgresql';
import { ToxiProxyContainer, type StartedToxiProxyContainer } from '@testcontainers/toxiproxy';
import { ChaosProxy } from './ChaosProxy.js';

export interface ChaosFixture {
  chaos: ChaosProxy;            // the intent-named toxic helper; app points at chaos.host():chaos.port()
  stop: () => Promise<void>;
}

/** Stands the dependency + Toxiproxy up on one Network and exposes the proxied connection point. */
export async function startChaos(): Promise<ChaosFixture> {
  const network: StartedNetwork = await new Network().start();

  const dependency: StartedPostgreSqlContainer = await new PostgreSqlContainer('postgres:16-alpine')
    .withNetwork(network)
    .withNetworkAliases('db')             // the upstream host on the shared network
    .start();

  const toxiproxy: StartedToxiProxyContainer = await new ToxiProxyContainer('ghcr.io/shopify/toxiproxy:2.11.0')
    .withNetwork(network)
    .start();

  // upstream = the dependency by its network alias + internal port; listen side is mapped to a host port.
  const proxy = await toxiproxy.createProxy({ name: 'db', upstream: 'db:5432' });

  // The app connects HERE — the proxy's mapped listen host/port, NOT the real dependency's port.
  const chaos = new ChaosProxy(proxy.instance, proxy.host, proxy.port);

  return {
    chaos,
    stop: async () => { await toxiproxy.stop(); await dependency.stop(); await network.stop(); },
  };
}
```

> The app under test must be configured to talk to `chaos.host():chaos.port()` (the connection string / base URL /
> broker bootstrap pointed at the proxy), **not** the dependency directly. That redirection *is* the chaos setup —
> if the app bypasses the proxy, no toxic can reach it.

## The toxic helper — `tests/support/chaos/ChaosProxy.ts`

One helper owns the proxy handle and exposes **intent-named** fault operations and a **lifecycle** primitive, so
tests read `chaos.injectLatency(...)`, `chaos.cutConnection()`, `chaos.healed()` — never raw `proxy.addToxic({...})`
scattered across `it(...)` blocks. Each injected toxic is named so it can be removed.

```ts
// tests/support/chaos/ChaosProxy.ts
import type { Proxy } from 'toxiproxy-node-client';

/** Intent-named fault injection over a single Toxiproxy proxy, with a remove-all "heal" for the lifecycle. */
export class ChaosProxy {
  private readonly injected: string[] = [];

  constructor(
    private readonly proxy: Proxy,
    private readonly proxyHost: string,
    private readonly proxyPort: number,
  ) {}

  host(): string { return this.proxyHost; }   // the app points its connection string here…
  port(): number { return this.proxyPort; }   // …and at this port

  /** Slow every response by `ms` (+ jitter) — the "dependency is slow" fault. */
  async injectLatency(ms: number, jitter = 0, toxicity = 1): Promise<void> {
    await this.add('latency', 'latency', 'downstream', { latency: ms, jitter }, toxicity);
  }

  /** Stop all data and close the connection after `ms` — the "dependency hangs then drops" fault. */
  async injectTimeout(ms: number): Promise<void> {
    await this.add('timeout', 'timeout', 'upstream', { timeout: ms });
  }

  /** Reset the TCP peer after `ms` — the "connection dropped" fault that exercises retry/breaker code. */
  async cutConnection(ms = 0, toxicity = 1): Promise<void> {
    await this.add('reset', 'reset_peer', 'downstream', { timeout: ms }, toxicity);
  }

  /** Throttle the backend dependency to `rateKbps` KB/s — bandwidth starvation (NOT device conditioning). */
  async throttle(rateKbps: number): Promise<void> {
    await this.add('bw', 'bandwidth', 'downstream', { rate: rateKbps });
  }

  /** Cut the response after `bytes` — a partial/truncated response the app must not persist as valid. */
  async truncateAfter(bytes: number): Promise<void> {
    await this.add('limit', 'limit_data', 'downstream', { bytes });
  }

  /** Remove ALL injected toxics — the dependency is "healed" (lifecycle step: assert recovery after this). */
  async healed(): Promise<void> {
    for (const name of this.injected) await this.proxy.removeToxic(name);
    this.injected.length = 0;
  }

  private async add(
    name: string,
    type: string,
    stream: 'upstream' | 'downstream',
    attributes: Record<string, number>,
    toxicity = 1,
  ): Promise<void> {
    await this.proxy.addToxic({ name, type, stream, toxicity, attributes } as never);
    this.injected.push(name);
  }
}
```
