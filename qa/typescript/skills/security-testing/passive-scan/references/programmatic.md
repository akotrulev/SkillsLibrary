# The programmatic scan path — `qa-typescript:passive-scan`

Moved out of SKILL.md for on-demand loading.

## Docker via `child_process` + parse JSON

To drive the scan from a test (assert programmatically, attach to Allure, gate on parsed counts), invoke
the image as a one-shot container and parse the JSON report. This is the **CLI/Docker port shape** the
`.NET`/`Java` siblings mirror with `Process`/`ProcessBuilder`:

```ts
// support/passive-scan.ts — the Docker-port client: one-shot container + JSON parse (no SDK exists)
import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

export interface ZapAlert {
  pluginid: string;
  alert: string;
  riskcode: string;   // "0" info … "3" high
  riskdesc: string;   // e.g. "Medium (Medium)"
  count: string;
}

export interface ZapResult {
  exitCode: number;          // 0 clean · 1 FAIL · 2 WARN-only · 3 infra failure
  alerts: ZapAlert[];        // flattened from report.site[].alerts[]
  reportJsonPath: string;
  reportHtmlPath: string;
}

/**
 * Runs `passive-scan.py` in the zaproxy container against a running target, returns the exit code
 * (the gate) plus the parsed alerts. Mounts a work dir so the reports land on the host.
 */
export function runZapBaseline(targetUrl: string, rulesTsvPath: string): ZapResult {
  const work = mkdtempSync(join(tmpdir(), 'zap-'));
  // --network host lets the container reach a localhost target on Linux CI; on Mac/Windows the target
  // would be http://host.docker.internal:<port> instead. Reachability is the #1 gotcha — see Anti-patterns.
  const proc = spawnSync('docker', [
    'run', '--rm', '--network', 'host',
    '-v', `${work}:/zap/wrk:rw`,
    '-v', `${rulesTsvPath}:/zap/wrk/rules.tsv:ro`,
    'ghcr.io/zaproxy/zaproxy:stable',
    'passive-scan.py',
    '-t', targetUrl,
    '-c', 'rules.tsv',        // the ticketed triage gate (relative to /zap/wrk)
    '-J', 'report.json',
    '-r', 'report.html',
    '-a',                     // include alpha passive rules
  ], { encoding: 'utf-8' });

  const reportJsonPath = join(work, 'report.json');
  const report = JSON.parse(readFileSync(reportJsonPath, 'utf-8'));
  const alerts: ZapAlert[] = (report.site ?? []).flatMap((s: { alerts?: ZapAlert[] }) => s.alerts ?? []);

  return {
    exitCode: proc.status ?? 3,
    alerts,
    reportJsonPath,
    reportHtmlPath: join(work, 'report.html'),
  };
}
```

```ts
// tests/passive-scan.spec.ts
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { GenericContainer, type StartedTestContainer } from 'testcontainers';
import { runZapBaseline } from '../support/passive-scan';
import { attachZapReport } from '../support/zap-report';
import { resolve } from 'node:path';

describe('ZAP baseline DAST gate', () => {
  let app: StartedTestContainer;
  let target: string;

  beforeAll(async () => {
    // Stand up the SUT. Wait on a readiness LOG/condition.
    app = await new GenericContainer('myorg/web:latest')
      .withExposedPorts(3000)
      .withWaitStrategy(/* Wait.forHttp('/health', 3000) */ undefined as never)
      .start();
    target = `http://localhost:${app.getMappedPort(3000)}`;
  }, 120_000);

  afterAll(async () => { await app?.stop(); });

  it('Should_pass_baseline_When_no_FAIL_level_alerts', () => {
    const result = runZapBaseline(target, resolve('.zap/rules.tsv'));
    attachZapReport(result);                       // attach BEFORE asserting, so a failure carries the report

    // The exit code IS the gate: 0 clean, 2 warnings-only (policy-pass), 1 means a FAIL-promoted rule fired.
    expect(result.exitCode).not.toBe(1);           // one logical assertion = the build gate
  });

  it('Should_have_no_high_risk_alerts_When_baseline_scanned', () => {
    const result = runZapBaseline(target, resolve('.zap/rules.tsv'));
    attachZapReport(result);
    const high = result.alerts.filter((a) => a.riskcode === '3');   // riskcode 3 = High
    expect(high).toEqual([]);                       // assert on the parsed report, not just the exit code
  });
});
```

Two complementary gates, both legitimate:
- **Exit-code gate** (`expect(exitCode).not.toBe(1)`) — let the `-c rules.tsv` config decide what `FAIL`s;
  the cleanest model, all the policy lives in one ticketed file.
- **Parsed-report gate** (`expect(high).toEqual([])`) — assert directly on `riskcode`/`pluginid` counts
  when you want a test-level assertion independent of the rules file. The `.NET`/`Java` siblings parse the
  same `report.site[].alerts[]` shape with `System.Text.Json` / Jackson.
