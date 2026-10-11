---
name: time-and-concurrency-testing
description: Use when a .NET 10 (8–9) / NUnit API suite must run a scheduled job on demand, control the clock at a time boundary, fire concurrent requests, or deliver a message or webhook twice — the temporal, concurrency and idempotency cases of a cross-feature suite. Triggers: "run the nightly job in a test", "freeze the clock at the cut-off", "two requests at once", "message delivered twice". Do NOT use for broker plumbing (`messaging-testing`) or fault injection (`failure-injection-testing`).
---

# QA — Time and Concurrency Testing (.NET 10 + WebApplicationFactory / NUnit)

Automates the case forms `qa/manual/test-case-writer` writes under **Temporal** and **Concurrency**: a schedule run on demand, the clock set to an instant, N requests released together, a message or webhook delivered twice. The manual lane names the *Environment needs* in a case's Setup or Preconditions; this skill turns each need into a seam, or into a named deferral.

## When to use

- A case's technique is temporal or concurrency, or its Setup names *Environment needs* (a way to run `<schedule>` on demand, a clock set to `<instant>` in `<timezone>`).
- "Run the monthly posting in a test", "cancel one second after the cut-off", "two members book the last seat", "the event is delivered twice".

## When NOT to use

- Waiting for an async effect (`within <budget>, <observable>`) — use the suite's poller, `DbWaits.WaitForRowAsync` in `qa/dotnet/skills/db-testing/verification-queries`, with the case's budget as its timeout.
- Broker setup, topics, consumers, DLQ → `qa/dotnet/skills/messaging-testing`.
- A dependency fault or a retry after a fault → `qa/dotnet/skills/failure-injection-testing`.
- Flag state → `qa/dotnet/skills/feature-flag-testing`.
- Load and capacity → `qa-performance-dotnet`.

## Inputs needed

1. **The case's technique and its *Environment needs*** — from the test-case document. No document: ask which job, which instant and timezone, which invariant.
2. **The host mode**, detected from the suite, not asked: **in-process** when tests boot the app themselves (a `WebApplicationFactory<Program>` — the host `feature-flag-testing` pins flags in); **deployed** when tests only call the configured base URL through the typed RestSharp clients.
3. **The scheduler the product uses** — Hangfire, Quartz.NET, a `BackgroundService`, a Kubernetes `CronJob` — from the `.csproj` files and the job classes.
4. **The invariant** the concurrency or duplicate case protects (`INV-…`), stated as a query the suite can run.

## Procedure

### 1. Pick the seam, in this order

1. **In-process host** — call the job's handler, the scheduler's trigger API, or replace the `TimeProvider` the application injects.
2. **Deployed environment** — a trigger or clock endpoint the environment exposes for tests (an admin endpoint enabled only in test environments, the scheduler's admin API, `kubectl create job --from=cronjob/<name>`).
3. **Neither exists** — the case is **deferred**: name the missing hook in the report, hand a hook request to `be-dotnet` as a product change, and commit no `[Ignore]`, `[Explicit]` or commented-out test. QA does not change product code.

Never wait for the real schedule and never change the production schedule.

### 2. One pattern per case kind

#### Job on demand — in-process

Resolve the job from the host's container, so its dependencies and the replaced clock apply:

```csharp
[Test]
public async Task Should_ChargeAccruedCredits_When_MonthlyPostingRuns()
{
    MemberDto member = await members.SeedWithAccrualAsync(600L);
    using IServiceScope scope = Factory.Services.CreateScope();

    await scope.ServiceProvider.GetRequiredService<MonthlyPostingJob>().PostAsync(CancellationToken.None);

    ChargeRow charge = await DbWaits.WaitForRowAsync(
        ct => ledgerProbe.ChargeForAsync(member.Id, ct), row => row.AmountMinor == 600L,
        PostingBudget, TimeSpan.FromMilliseconds(100), logger);
    Assert.That(charge.AmountMinor, Is.EqualTo(600L), $"charge for member {member.Id}");
}
```

- **Plain job class or `IHostedService` with a public work method** — call that method, as above. A `BackgroundService` whose loop lives in `ExecuteAsync` is usually not invocable: do **not** start the host and wait for its timer. Ask `be-dotnet` to extract the work into a method the host registers (a hook request) and defer the case.
- **Hangfire** — `IRecurringJobManager.TriggerJob(recurringJobId)` from the host's container (`RecurringJob.Trigger` is obsolete since 1.7.31). It enqueues a background job and the schedule is untouched, so a Hangfire **server** must be running in the host (not every test host starts one) and the observable is polled. With no server, call the job's method on the resolved class instead. Job ids can be case-sensitive.
- **Quartz.NET** — `await scheduler.TriggerJob(new JobKey("monthly-posting", "billing"))` on the `ISchedulerFactory`'s scheduler, which must be started. It returns before the job has run, so poll the observable. The call is awaitable in 3.x and 4.x.
- **The real schedule firing mid-test** — a cron read from configuration is overridden in the factory (`ConfigureAppConfiguration`) to a date that never fires. A literal cron that can fire inside the run is a request to `be-dotnet`.

#### Job on demand — deployed

The test is the in-process one with the job call replaced by `adminClient.RunJob("monthly-posting", new RunJobDto("2026-03"), HttpStatusCode.Accepted)`; the poll and the assertion are unchanged.

`adminClient` is a typed `{Resource}Client` over the test-only trigger (`api-client-writer`). For a Kubernetes `CronJob`, `CronJobRunner.RunNowAsync(cronJob, ns, ct)` in `references/helpers.md` runs `kubectl create job --from=cronjob/…` and waits; a failure fails loudly with the command's output and is never caught.

Register the returned job name and delete it in `[TearDown]`.

#### Clock boundary

The application injects a `TimeProvider` and never reads `DateTime.UtcNow`, `DateTimeOffset.UtcNow` or `DateTime.Now` directly. **In-process**, replace it in `ConfigureTestServices` with a `FakeTimeProvider`, the way `feature-flag-testing` swaps its provider (`ApiFactory` and the base fixture are in `references/helpers.md`), and seed relative to the controlled "now". One row per instant, one expected value each; the offset carries the timezone:

```csharp
[TestCase("2026-03-15T10:00:00+00:00", 2)]
[TestCase("2026-03-15T09:59:59+00:00", 2)]
[TestCase("2026-03-15T10:00:01+00:00", 0)]
public async Task Should_ReturnCredits_When_CancellingAtTheCutOff(string cancelAt, int creditsBack)
{
    BookingDto booking = await bookings.SeedAsync(BookingBuilder.Valid()
        .WithSessionStart(DateTimeOffset.Parse("2026-03-16T10:00:00+00:00")).WithCredits(2).Build());
    Factory.Clock.AdjustTime(DateTimeOffset.Parse(cancelAt));

    CancelledDto cancelled = bookingClient.Cancel(booking.Id, HttpStatusCode.OK);

    Assert.That(cancelled.CreditsReturned, Is.EqualTo(creditsBack),
        $"credits for booking {booking.Id} cancelled at {cancelAt}");
}
```

- `FakeTimeProvider` comes from the `Microsoft.Extensions.TimeProvider.Testing` package. `SetUtcNow` and `Advance` only move **forward** and throw going back, so the boundary rows above use `AdjustTime`, which also rewinds; it shifts outstanding timers by the same delta and fires none, so use `Advance` when a timer must fire.
- The `Z`/offset in the instant carries the timezone. A schedule in a local zone: `Clock.SetLocalTimeZone(TimeZoneInfo.FindSystemTimeZoneById("Europe/London"))` (IANA ids work on Linux and macOS and on Windows with ICU).
- DST change and month end: the same pattern, instants either side of the transition.
- Timers and `Task.Delay(delay, timeProvider)` inside the app fire when the test calls `Advance`; real time never moves them.

**Deployed.** Use the environment's test clock endpoint through a typed client and reset it in `[TearDown]`. With none, seed data relative to the server's real "now" and make the boundary step larger than clock skew plus request latency, saying so in the test name (`Should_ForfeitCredits_When_CancellingFiveMinutesAfterTheCutOff`). If the application reads the system clock directly, the clock cannot be controlled: **defer** the case and hand the `TimeProvider` seam to `be-dotnet`.

**Never** `Thread.Sleep` or `Task.Delay` to reach a boundary, and never set the machine clock.

**Version twin.** `TimeProvider` is part of the base library from .NET 8; below .NET 8 the polyfill is `Microsoft.Bcl.TimeProvider`. `FakeTimeProvider` needs the `Microsoft.Extensions.TimeProvider.Testing` package on every TFM, and the replacement above is the same on .NET 8, 9 and 10. A .NET 8 project that registers its own `IClock` instead keeps that seam: replace it the same way.

#### Concurrent requests

Release N requests together behind a start gate (`Race.StartTogetherAsync`, in `references/helpers.md`: a ready signal, a `TaskCompletionSource` gate, `Task.WhenAll`), wait for all to settle, assert the **invariant**, never which request won. Repetition comes from NUnit's `[Repeat]`.

- `[Repeat(20)]` runs the method 20 times with `[SetUp]` and `[TearDown]` around each repetition, so seed inside the test or in `[SetUp]` and each run starts clean. It stops at the first failure by default, which is right: a failure on any repetition is a defect, not a flake to retry. `[Repeat]` applies to test methods only, not fixtures.
- Not `Parallelizable` as the barrier: it runs different tests in parallel on shared fixtures and does not align requests at the same instant. The gate does.
- The refusal gets its own test naming the one expected refusal (`409`), never `409 or 422`.
- The invariant is a `db-testing/verification-queries` query (`confirmed ≤ capacity`), asserted after all calls settle.
- A race with a schedule releases the job call and the request behind the same gate.

#### Duplicate and out-of-order delivery, idempotency

The effect must happen once. Each form delivers the **same business id** a second time:

```csharp
[Test]
public async Task Should_ReturnCreditsUsedTo6Not4_When_TheCancellationEventIsDeliveredTwice()
{
    BookingDto booking = await bookings.SeedCancelledAsync(BookingBuilder.Valid().WithCreditsUsed(8).WithCredits(2).Build());
    string body = JsonSerializer.Serialize(CancellationEvents.Of(booking));

    await SendToCreditsQueueAsync(body, booking.Id);
    await SendToCreditsQueueAsync(body, booking.Id);

    await DbWaits.WaitForRowAsync(ct => inboxProbe.ProcessedAsync(booking.Id, ct), row => row.Count == 2,
        CreditsBudget, TimeSpan.FromMilliseconds(200), logger);
    Assert.That(await memberProbe.CreditsUsedAsync(booking.MemberId), Is.EqualTo(6L),
        $"credits used for member {booking.MemberId}");
}

private Task SendToCreditsQueueAsync(string body, Guid businessId) =>
    sqs.SendMessageAsync(new SendMessageRequest
    {
        QueueUrl = creditsUrl,
        MessageBody = body,
        MessageGroupId = businessId.ToString(),
        MessageDeduplicationId = Guid.NewGuid().ToString(),
    });
```

- **Message** — publish through the project's `messaging-testing` reference (its producer / seed helper), with a **new broker message id and the same business id**. Broker deduplication swallows an identical publish before the consumer sees it — SQS FIFO (`MessageDeduplicationId`, content-based deduplication), Service Bus duplicate detection, Kafka's idempotent producer — and such a test proves nothing about the consumer's idempotency. Vary the dedup id (or use a standard queue) so two deliveries reach the consumer.
- **Wait on a positive signal, never a sleep:** an inbox / processed-messages row per delivery through `DbWaits.WaitForRowAsync`, then assert the effect count. SQS queue-depth attributes are approximate, so they are not the signal.
- **Webhook** — replay the request with the same delivery id through the typed client twice; assert one effect and, if the contract says so, the same response both times.
- **Idempotency key** — resend the request with the same `Idempotency-Key`; assert one resource and the contracted response.
- **Out of order** — publish the two events in reverse order, then assert the spec's declared outcome (one value).

#### Invariant after a sequence

A `db-testing/verification-queries` query asserting the invariant's statement (`SELECT COUNT(*) … HAVING …`), run after the sequence settles.

## Anti-patterns

- **Waiting for the real schedule** or a `Task.Delay` for the job to fire — a blocker. Trigger it.
- **Starting the host and waiting for a `BackgroundService` timer** — request the hook instead.
- **A sleep or a changed machine clock** to reach a boundary.
- **A boundary test with no controlled clock and no stated skew margin.**
- **Asserting which request won**, or an `OR` on the status.
- **A `for` loop firing the race or driving assertions** — use `[Repeat]` and `Race.StartTogetherAsync`; parameterize with `[TestCase]`.
- **A race with no gate** (`await a; await b;` is sequential, not concurrent), or `Parallelizable` as the barrier.
- **A duplicate test that broker deduplication defeats.**
- **An `[Ignore]` or commented-out test for a missing hook** — defer in the report instead.
- **`try`/`catch` in a test body or `[TearDown]`** — an expected refusal is asserted on the response, an unexpected error reaches NUnit.
- **`.Result` / `.Wait()`** on the gate or the calls — async all the way.

## Hard rules

- No sleeps and no waiting for the real schedule: jobs run on demand, effects are polled with the case's budget.
- The clock is replaced in the in-process host or driven by an environment hook; code that reads the system clock directly is deferred to `be-dotnet`.
- Data is seeded relative to the controlled "now"; every instant states its offset or timezone.
- A race test releases N requests behind a gate, repeats through `[Repeat]`, and asserts the invariant, never the winner.
- A duplicate-delivery test uses a new broker message id with the same business id, and waits on a positive processed signal.
- A missing seam is a **deferral**: named in the report with the hook, handed to `be-dotnet`, with no test body committed.
- Cleanup runs in `[TearDown]`; failure messages carry the evidence (ids, the instant, the response body).

## Handoffs

- A missing job trigger, `TimeProvider` seam or test endpoint → `be-dotnet`, as a product change.
- Broker producer / seeding helpers, DLQ → `qa/dotnet/skills/messaging-testing`.
- Verification queries, the poller and the cleanup helper → `qa/dotnet/skills/db-testing/verification-queries`, `…/db-testing/connection`.
- A retry or recovery after a fault → `qa/dotnet/skills/failure-injection-testing`.
- Typed clients for the trigger or clock endpoint → `qa/dotnet/skills/api-client-writer`.
- The plain tests → `qa/dotnet/skills/api-test-author/writer`; review → `…/api-test-author/review`.

## APIs checked (2026-10-11)

.NET 8–10 · `TimeProvider` (base library from .NET 8) · `Microsoft.Extensions.TimeProvider.Testing` `FakeTimeProvider` (`Advance`, `SetUtcNow` forward-only, `AdjustTime`, `SetLocalTimeZone`, `CreateTimer`; checked against the library's current source and Microsoft Learn, not a per-TFM package page) · Hangfire 1.7.31+ (`TriggerJob`; `RecurringJob.Trigger` obsolete) · Quartz.NET 3.x and 4.0 (`TriggerJob(JobKey, JobDataMap?, CancellationToken)`; 4.x return type not confirmed, `await` works either way) · NUnit 4 `[Repeat]` (stops at first failure; `StopOnFailure` since 4.3.0; per-repetition `[SetUp]` from the attribute's wrapping design, not a doc sentence) · `WebApplicationFactory` `ConfigureTestServices`.
