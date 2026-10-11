# AWS Device Farm — remote-run (TypeScript)

The orchestration class for the remote-run paradigm in `SKILL.md`. Every wait on AWS is a bounded poll; the interval sits between condition checks.

```typescript
import {
  DeviceFarmClient, CreateUploadCommand, GetUploadCommand, ScheduleRunCommand, GetRunCommand,
  type UploadType,
} from '@aws-sdk/client-device-farm';

export class DeviceFarmRunner {
  constructor(private readonly deviceFarm: DeviceFarmClient) {}

  async uploadAndAwait(projectArn: string, name: string, type: UploadType, bytes: Buffer): Promise<string> {
    const created = await this.deviceFarm.send(new CreateUploadCommand({ projectArn, name, type }));
    const upload = created.upload!;
    await this.putBytes(upload.url!, bytes);

    await pollUntil(5 * 60_000, 5_000, async () => {
      const status = (await this.deviceFarm.send(new GetUploadCommand({ arn: upload.arn }))).upload!.status;
      if (status === 'FAILED') throw new Error(`Upload failed: ${name}`);
      return status === 'SUCCEEDED';
    });
    return upload.arn!;
  }

  async scheduleAndAwait(
    projectArn: string, appArn: string, testPackageArn: string, testSpecArn: string, devicePoolArn: string,
  ): Promise<string> {
    const scheduled = await this.deviceFarm.send(new ScheduleRunCommand({
      projectArn, appArn, devicePoolArn,
      test: { type: 'APPIUM_NODE', testPackageArn, testSpecArn },
    }));
    const runArn = scheduled.run!.arn!;

    await pollUntil(30 * 60_000, 15_000, async () =>
      (await this.deviceFarm.send(new GetRunCommand({ arn: runArn }))).run!.status === 'COMPLETED');

    return (await this.deviceFarm.send(new GetRunCommand({ arn: runArn }))).run!.result!;
  }

  private async putBytes(url: string, bytes: Buffer): Promise<void> {
    const response = await fetch(url, { method: 'PUT', body: bytes });
    if (!response.ok) throw new Error(`Upload PUT failed: HTTP ${response.status}`);
  }
}

async function pollUntil(timeoutMs: number, intervalMs: number, condition: () => Promise<boolean>): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (!(await condition())) {
    if (Date.now() > deadline) throw new Error('Timed out waiting for the condition');
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}
```


The interval in `pollUntil` sits between condition checks. AWS auth comes from the **default credential chain**; in CI prefer **OIDC role assumption** over a long-lived key (`qa/cicd/typescript/skills/ci-pipelines`). Artifacts (logs, video, screenshots) are fetched per job through `ListArtifactsCommand` after the run, and the verdict is `PASSED`, `FAILED` or `ERRORED`.
