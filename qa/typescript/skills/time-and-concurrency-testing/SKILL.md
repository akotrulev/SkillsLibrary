---
name: time-and-concurrency-testing
description: Use when a Node 24 / TypeScript API suite must run a scheduled job on demand, control the clock at a time boundary, fire concurrent requests, or deliver a message or webhook twice — the temporal, concurrency and idempotency cases of a cross-feature suite. Triggers: "run the nightly job in a test", "freeze the clock at the cut-off", "two requests at once", "message delivered twice". Do NOT use for broker plumbing (`messaging-testing`) or fault injection (`failure-injection-testing`).
---

# QA — Time and Concurrency Testing (Node 24 + TypeScript / Vitest)

Automates the case forms `qa/manual/test-case-writer` writes under **Temporal** and **Concurrency**: a schedule run on demand, the clock set to an instant, N requests released together, a message or webhook delivered twice. The manual lane names the *Environment needs* in a case's Setup or Preconditions; this skill turns each need into a seam, or into a named deferral.

## When to use

- A case's technique is temporal or concurrency, or its Setup names *Environment needs* (a way to run `<schedule>` on demand, a clock set to `<instant>` in `<timezone>`).
- "Run the monthly posting in a test", "cancel one second after the cut-off", "two members book the last seat", "the event is delivered twice".

## When NOT to use

- Waiting for an async effect (`within <budget>, <observable>`) — use the suite's poller: `waitFor` in `qa/typescript/skills/db-testing/connection`, or `vi.waitFor` / `expect.poll`, with the case's budget as its timeout.
- Broker setup, topics, consumers, DLQ → `qa/typescript/skills/messaging-testing`.
- A dependency fault or a retry after a fault → `qa/typescript/skills/failure-injection-testing`.
- Flag state → `qa/typescript/skills/feature-flag-testing`.
- Writing the plain endpoint tests → `qa/typescript/skills/api-test-author/writer`.
- Load and capacity → `qa-performance-typescript`. Java / .NET → the same-named skill in `qa-java` / `qa-dotnet`.

## Inputs needed

1. **The case's technique and its *Environment needs*** — from the test-case document. No document: ask which job, which instant and timezone, which invariant.
2. **The host mode**, detected from the suite, not asked: **in-process** when specs boot the app themselves (`Test.createTestingModule`, an `createApp()` factory, the same host `feature-flag-testing` pins flags in); **deployed** when specs only call `getTestEnvironment().baseUrl`.
3. **The scheduler and queue the product uses** — `@nestjs/schedule`, `node-cron`, BullMQ, a cloud scheduler — from `package.json` and the module wiring.
4. **The invariant** the concurrency or duplicate case protects (`INV-…`), stated as a query the suite can run.

## Procedure

### 1. Pick the seam, in this order

1. **In-process host** — call the job's handler, the scheduler's own trigger, or replace the clock the application injects.
2. **Deployed environment** — a trigger or clock endpoint the environment exposes for tests (an admin endpoint enabled only in test environments, the scheduler's admin API, `kubectl create job --from=cronjob/<name>`).
3. **Neither exists** — the case is **deferred**: name the missing hook in the report, hand a hook request to `be-node` as a product change, and commit no skipped, `todo` or commented-out test. QA does not change product code.

Never wait for the real schedule and never change the production schedule.

### 2. One pattern per case kind

#### Job on demand — in-process

Pick the first that matches the product.

```ts
import { SchedulerRegistry } from '@nestjs/schedule';

it('should charge the accrued credits when the monthly posting runs', async () => {
  const member = await seedMemberWithAccrual({ accruedMinor: 600 });

  await host.app.get(SchedulerRegistry).getCronJob('monthly-posting').fireOnTick();

  const charge = await waitFor(() => ledgerProbe.chargeFor(member.id), (c) => c.amountMinor === 600, postingBudget);
  expect(charge.amountMinor, `charge for member ${member.id}`).toBe(600);
});
```

- **NestJS `@Cron`** — the job must carry a `name` (`@Cron(expr, { name: 'monthly-posting' })`). `SchedulerRegistry.getCronJob(name).fireOnTick()` runs the tick now. Still poll the observable: the tick resolving does not prove a queued effect landed.
- **BullMQ** — the in-process `Worker` consumes from a Testcontainers Redis: `await queue.add('post-month', { month }, { jobId: crypto.randomUUID() })`, then poll the observable. Or call the processor's handler directly: `await postMonth({ month }, deps)`.
- **node-cron 4** — call `task.execute()` on the task handle the host exposes. node-cron 3 has no public run-now: call the handler the task wraps.
- **Plain function** — import the exported job function and call it with the host's dependencies.

#### Job on demand — deployed

```ts
it('should charge the accrued credits when the monthly posting runs', async () => {
  const member = await seedMemberWithAccrual({ accruedMinor: 600 });

  await adminClient.runJobTyped('monthly-posting', { month: '2026-03' });

  const charge = await waitFor(() => ledgerProbe.chargeFor(member.id), (c) => c.amountMinor === 600, postingBudget);
  expect(charge.amountMinor, `charge for member ${member.id}`).toBe(600);
});
```

`adminClient` is a typed `{resource}Client` over the test-only trigger (`api-client-writer`). For a Kubernetes `CronJob`, a helper that performs I/O runs it; its failure propagates with stderr and is never caught:

```ts
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const run = promisify(execFile);

export async function runCronJobNow(cronJob: string, namespace: string): Promise<string> {
  const job = `${cronJob}-test-${crypto.randomUUID().slice(0, 8)}`;
  await run('kubectl', ['create', 'job', job, `--from=cronjob/${cronJob}`, '-n', namespace]);
  await run('kubectl', ['wait', '--for=condition=complete', `job/${job}`, '--timeout=120s', '-n', namespace]);
  return job;
}
```

Register the returned job name and delete it in `afterEach`.

#### Clock boundary

The application injects its clock (a `CLOCK` token, a `Clock` interface) and never reads `Date.now()` directly. **In-process**, override the provider the way `feature-flag-testing` overrides its flag provider, and seed relative to the controlled "now":

```ts
export interface Clock { now(): Date }

export class ControlledClock implements Clock {
  constructor(private instant: Date) {}
  now(): Date { return new Date(this.instant); }
  set(instant: Date): void { this.instant = instant; }
}

export async function startHost(clock: Clock): Promise<Host> {
  const moduleRef = await Test.createTestingModule({ imports: [AppModule] })
    .overrideProvider(CLOCK).useValue(clock)
    .compile();
  const app = moduleRef.createNestApplication();
  await app.listen(0);
  return { app, baseUrl: await app.getUrl() };
}
```

One row per instant, one expected value each; offsets in the ISO string carry the timezone:

```ts
const sessionStart = new Date('2026-03-16T10:00:00Z');

it.each([
  { cancelAt: '2026-03-15T10:00:00Z', creditsBack: 2 },
  { cancelAt: '2026-03-15T09:59:59Z', creditsBack: 2 },
  { cancelAt: '2026-03-15T10:00:01Z', creditsBack: 0 },
])('should return $creditsBack credits when cancelling at $cancelAt, 24 h before start', async ({ cancelAt, creditsBack }) => {
  const booking = await seedBooking({ sessionStart, credits: 2 });
  clock.set(new Date(cancelAt));

  const response = await bookingClient.cancel(booking.id);

  expect(response.status, `cancel ${booking.id} at ${cancelAt}`).toBe(200);
  expect(CancelledSchema.parse(response.bodyJson).creditsReturned).toBe(creditsBack);
});
```

DST change and month end are the same pattern with instants either side of the transition.

**Deployed.** Use the environment's test clock endpoint through a typed client, and reset it in `afterEach`. With none, seed data relative to the server's real "now" and make the boundary step larger than clock skew plus request latency, saying so in the test name (`…when cancelling 5 minutes after the cut-off`). If the application reads the system clock directly, the clock cannot be controlled: **defer** the case and hand the clock seam to `be-node`.

**Never** `vi.useFakeTimers()` or `vi.setSystemTime()` against a separately running server: they move only the test process's clock, never the server's, and they break the client's own timeouts. They are legitimate only for code that runs inside the test process (a unit test of the job function with an injected scheduler), which is not this skill's lane.

#### Concurrent requests

Release N requests together behind a start barrier, wait for all to settle, assert the **invariant**, never which request won. Repetition comes from the runner's `repeats` option.

```ts
export async function startTogether<T>(count: number, act: (index: number) => Promise<T>): Promise<T[]> {
  const barrier = Promise.withResolvers<void>();
  const calls = Array.from({ length: count }, async (_, index) => {
    await barrier.promise;
    return act(index);
  });
  barrier.resolve();
  return Promise.all(calls);
}

test('should confirm exactly one booking when two members take the last seat', { repeats: 19 }, async () => {
  const session = await seedSession({ capacity: 1 });
  const tokens = await seedMemberTokens(2);

  const responses = await startTogether(2, (i) => bookingClient(tokens[i]).book(session.id));

  expect(responses.filter((r) => r.status === 201), `confirmed of ${responses.length} for session ${session.id}`).toHaveLength(1);
  expect(await bookingDbProbe.confirmedCount(session.id), `confirmed rows for session ${session.id}`).toBe(1);
});
```

- `repeats: 19` runs the test 20 times; `beforeEach` and `afterEach` run on every repetition, so seed inside the test or in `beforeEach` and every repetition starts clean. The option goes second: `test(name, { repeats }, fn)`.
- The refusals get their own assertion naming the one expected refusal (`409`), in a separate test, never `409 or 422`.
- The invariant is a `db-testing/verification-queries` query (`confirmed ≤ capacity`), asserted after all calls settle.
- A race with a schedule (a cancellation landing while a job runs) releases the job trigger and the request behind the same barrier.
- Passing on 20 repeats does not prove the absence of a race; a failure on any repeat is a defect, never a flake to retry away.

#### Duplicate and out-of-order delivery, idempotency

The effect must happen once. Each form delivers the **same business id** a second time:

```ts
it('should return credits used to 6, not 4, when the cancellation event is delivered twice', async () => {
  const booking = await seedCancelledBooking({ creditsUsed: 8, creditsBack: 2 });
  const event = cancellationEvent(booking);

  await producer.publish(event, { dedupId: crypto.randomUUID() });
  await producer.publish(event, { dedupId: crypto.randomUUID() });
  await queueProbe.untilDrained(creditsQueue);

  expect(await memberDbProbe.creditsUsed(booking.memberId), `credits used for member ${booking.memberId}`).toBe(6);
});
```

- **Message** — publish through the project's `messaging-testing` reference (its producer / seed helper), with a **new broker message id and the same business id**. Broker deduplication swallows an identical publish before the consumer sees it — SQS FIFO (`MessageDeduplicationId`, `ContentBasedDeduplication`), Service Bus duplicate detection, Kafka's idempotent producer, a BullMQ repeated `jobId` — and such a test proves nothing about the consumer's idempotency. Vary the dedup id (or use a standard queue) so two deliveries reach the consumer.
- **Wait on a positive signal, never a sleep:** the queue drained (depth and in-flight zero), or an inbox / processed-messages row per delivery, then assert the effect count.
- **Webhook** — replay the request with the same delivery id through the typed client twice; assert one effect and, if the contract says so, the same response both times.
- **Idempotency key** — resend the request with the same `Idempotency-Key`; assert one resource and the contracted response.
- **Out of order** — publish the two events in reverse order, then assert the declared outcome (ignored, reordered, or the last write wins as the spec states) with one expected value.

#### Invariant after a sequence

A `db-testing/verification-queries` query asserting the invariant's statement (`SELECT COUNT(*) … HAVING …`), run after the sequence settles.

## Anti-patterns

- **Waiting for the real schedule** or a `setTimeout` for the job to fire — a blocker. Trigger it.
- **Changing the production schedule** (`@Cron` expression, CronJob spec) so it fires soon.
- **`vi.useFakeTimers()` / `vi.setSystemTime()` against a running server.**
- **Reading `new Date()` inside the assertion** or seeding "tomorrow" from the test process while the server's clock decides the boundary.
- **A boundary test with no controlled clock and no stated skew margin.**
- **Asserting which request won**, or `expect([201, 409]).toContain(status)`.
- **A `for` loop firing the race or driving assertions** — use `repeats` and `startTogether`; parameterize with `it.each`.
- **A race with no barrier** (`await a(); await b();` is sequential, not concurrent).
- **A duplicate test that broker deduplication defeats.**
- **A fixed sleep before asserting "still one".**
- **A skipped, `todo` or commented-out test for a missing hook** — defer in the report instead.
- **`try`/`catch` in a test body** — an expected refusal is asserted on the response, an unexpected error reaches Vitest.

## Hard rules

- No sleeps and no waiting for the real schedule: jobs run on demand, effects are polled with the case's budget.
- The clock is replaced in the in-process host or driven by an environment hook; fake timers never stand in for a server's clock.
- Data is seeded relative to the controlled "now"; every instant states its timezone.
- A race test releases N requests behind a barrier, repeats through the runner's option, and asserts the invariant, never the winner.
- A duplicate-delivery test uses a new broker message id with the same business id, and waits on a positive processed signal.
- One expected value per assertion — never an `OR`; no conditional logic or loops driving assertions.
- A missing seam is a **deferral**: named in the report with the hook, handed to `be-node`, with no test body committed.
- Cleanup (reset clock, delete the created job, created rows) is registered in `afterEach`; the tests are independent and run in any order.
- Failure messages name the subject and carry the evidence (ids, the instant, the response body).

## Handoffs

- A missing job trigger, clock seam or test endpoint → `be-node`, as a product change.
- Broker producer / seeding helpers, DLQ → `qa/typescript/skills/messaging-testing`.
- Verification queries and the poller → `qa/typescript/skills/db-testing/verification-queries`, `…/db-testing/connection`.
- A retry or recovery after a fault → `qa/typescript/skills/failure-injection-testing`.
- Typed clients for the trigger or clock endpoint → `qa/typescript/skills/api-client-writer`.
- The plain specs → `qa/typescript/skills/api-test-author/writer`; review → `…/api-test-author/review`.

## APIs checked (2026-10-11)

Node 24 and 22 (`Promise.withResolvers`, 22+) · Vitest 3, 4 and 5 (`repeats` in the test options; hooks run per repeat) · `@nestjs/schedule` on `cron` 3.5 and 4.4 (`CronJob.fireOnTick(): Promise<void>`) · BullMQ 6.3 (a repeated `jobId` is ignored; `Worker` takes a processor function) · node-cron 4.6 (`ScheduledTask.execute()`; no public equivalent in 3.0).
