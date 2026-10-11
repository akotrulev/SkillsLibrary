---
name: time-and-concurrency-testing
description: Use when a Java 21 / TestNG API suite must run a scheduled job on demand, control the clock at a time boundary, fire concurrent requests, or deliver a message or webhook twice — the temporal, concurrency and idempotency cases of a cross-feature suite. Triggers: "run the nightly job in a test", "freeze the clock at the cut-off", "two requests at once", "message delivered twice". Do NOT use for broker plumbing (`messaging-testing`) or fault injection (`failure-injection-testing`).
---

# QA — Time and Concurrency Testing (Java 21 + Spring Boot 3.x / TestNG)

Automates the case forms `qa/manual/test-case-writer` writes under **Temporal** and **Concurrency**: a schedule run on demand, the clock set to an instant, N requests released together, a message or webhook delivered twice. The manual lane names the *Environment needs* in a case's Setup or Preconditions; this skill turns each need into a seam, or into a named deferral.

## When to use

- A case's technique is temporal or concurrency, or its Setup names *Environment needs* (a way to run `<schedule>` on demand, a clock set to `<instant>` in `<timezone>`).
- "Run the monthly posting in a test", "cancel one second after the cut-off", "two members book the last seat", "the event is delivered twice".

## When NOT to use

- Waiting for an async effect (`within <budget>, <observable>`) — use the suite's poller, `DbWaits.waitForRow` in `qa/java/skills/db-testing/verification-queries` (Awaitility), with the case's budget as its timeout.
- Broker setup, topics, consumers, DLQ → `qa/java/skills/messaging-testing`.
- A dependency fault or a retry after a fault → `qa/java/skills/failure-injection-testing`.
- Flag state → `qa/java/skills/feature-flag-testing`.
- Load and capacity → `qa-performance-java`.

## Inputs needed

1. **The case's technique and its *Environment needs*** — from the test-case document. No document: ask which job, which instant and timezone, which invariant.
2. **The host mode**, detected from the suite, not asked: **in-process** when tests boot the app themselves (`@SpringBootTest` on `AbstractTestNGSpringContextTests`, the host `feature-flag-testing` pins flags in); **deployed** when tests only call the configured base URL through the typed clients.
3. **The scheduler the product uses** — Spring `@Scheduled`, Quartz, a Kubernetes `CronJob` — and whether ShedLock guards it, from the build file and the job classes.
4. **The invariant** the concurrency or duplicate case protects (`INV-…`), stated as a query the suite can run.

## Procedure

### 1. Pick the seam, in this order

1. **In-process host** — call the job bean's method or the scheduler's trigger API, or replace the `Clock` the application injects.
2. **Deployed environment** — a trigger or clock endpoint the environment exposes for tests (an admin endpoint enabled only in test environments, the scheduler's admin API, `kubectl create job --from=cronjob/<name>`).
3. **Neither exists** — the case is **deferred**: name the missing hook in the report, hand a hook request to `be-java` as a product change, and commit no `enabled = false`, skipped or commented-out test. QA does not change product code.

Never wait for the real schedule and never change the production schedule.

### 2. One pattern per case kind

#### Job on demand — in-process

Inject the bean and call it through the context, so the proxies (`@Transactional`, ShedLock) apply:

```java
public class MonthlyPostingTest extends IntegrationTestBase {

    @Autowired private MonthlyPostingJob postingJob;
    @Autowired private ShedLockProbe shedLock;
    private LedgerProbe ledgerProbe;

    @BeforeMethod(alwaysRun = true)
    public void releaseJobLock() {
        shedLock.release("monthly-posting");
    }

    @Test
    public void Should_ChargeAccruedCredits_When_MonthlyPostingRuns() {
        Member member = members.seedWithAccrual(600L);

        postingJob.post();

        Charge charge = DbWaits.waitForRow("charge-for-" + member.id(),
            () -> ledgerProbe.chargeFor(member.id()), c -> c.amountMinor() == 600L,
            POSTING_BUDGET, Duration.ofMillis(100));
        assertThat(charge.amountMinor()).as("charge for member %s", member.id()).isEqualTo(600L);
    }
}
```

- **Spring `@Scheduled`** — the method must be non-private and non-final, and is called on the injected bean, never on `new MonthlyPostingJob(...)`. A private or final scheduled method cannot be proxied: that is a hook for `be-java`.
- **Quartz** — `scheduler.triggerJob(JobKey.jobKey("monthly-posting", "billing"))` on the injected `org.quartz.Scheduler`. It returns before the job has run, so poll the observable.
- **The real schedule firing mid-test** — if the cron is a property (`@Scheduled(cron = "${jobs.posting.cron}")`), set it to `-` (`Scheduled.CRON_DISABLED`) for the test profile. A literal cron that can fire inside the run is a request to `be-java`.
- **ShedLock** — see the trap below.

**ShedLock — the lock can make a run silently do nothing.** With `@EnableSchedulerLock` in its default `PROXY_METHOD` mode the lock is applied even when the method is called directly, and a held lock makes the call a **no-op that returns without error**. After a successful run the lock stays held until `lockAtLeastFor` elapses, and a row left by a previous test or run holds it too. So:

- Release the job's lock before each run with a cleanup helper that performs I/O and binds the name (`DELETE FROM shedlock WHERE name = :name`, in a `ShedLockProbe` under `db-testing/connection`) — in `@BeforeMethod`, and **between the two runs of an idempotency case**.
- Assert that each run **executed**. An idempotency case whose second run was skipped by the lock passes for the wrong reason. Assert a positive signal per run: a run-record row, or the job's declared "already posted" outcome — not only "no second charge".
- `lockAtLeastFor` is measured by the lock provider's clock (JVM or DB time), not the application `Clock` bean, so moving the test clock forward does not release a lock.

#### Job on demand — deployed

The test is the in-process one with `postingJob.post()` replaced by `adminClient.runJob("monthly-posting", new RunJobDto("2026-03"), HttpStatus.SC_ACCEPTED)`; the poll and the assertion are unchanged.

`adminClient` is a typed `{Resource}Client` over the test-only trigger (`api-client-writer`). For a Kubernetes `CronJob`, `CronJobRunner.runNow(cronJob, namespace)` in `references/helpers.md` runs `kubectl create job --from=cronjob/…` and waits; a failure fails loudly with the command's output and is never caught.


Register the returned job name and delete it in `@AfterMethod(alwaysRun = true)`.

#### Clock boundary

The application injects a `java.time.Clock` bean and never calls `Instant.now()`, `LocalDateTime.now()` or `System.currentTimeMillis()` directly. **In-process**, add a movable clock (`MutableClock`, in `references/helpers.md`) as a `@Primary` bean through a `@TestConfiguration`, the way `feature-flag-testing` swaps its provider, and seed relative to the controlled "now":


`IntegrationTestBase` carries `@Import(ControlledClockConfig.class)`, autowires the `MutableClock`, and resets it in `@BeforeMethod` (the cached context otherwise keeps it moved). One row per instant, one expected value each; the `Z` or offset carries the timezone:

```java
@DataProvider(name = "cancellationInstants")
public Object[][] cancellationInstants() {
    return new Object[][] {
        {"2026-03-15T10:00:00Z", 2},
        {"2026-03-15T09:59:59Z", 2},
        {"2026-03-15T10:00:01Z", 0},
    };
}

@Test(dataProvider = "cancellationInstants")
public void Should_ReturnCredits_When_CancellingAtTheCutOff(String cancelAt, int creditsBack) {
    Booking booking = bookings.seed(Bookings.valid().sessionStart(Instant.parse("2026-03-16T10:00:00Z")).credits(2).build());
    clock.set(Instant.parse(cancelAt));

    CancelledDto cancelled = bookingClient.cancel(booking.id(), HttpStatus.SC_OK);

    assertThat(cancelled.creditsReturned()).as("credits for booking %s cancelled at %s", booking.id(), cancelAt).isEqualTo(creditsBack);
}
```

DST change and month end: the same pattern, instants either side of the transition.

**Deployed.** Use the environment's test clock endpoint through a typed client and reset it in `@AfterMethod(alwaysRun = true)`. With none, seed data relative to the server's real "now" and make the boundary step larger than clock skew plus request latency, saying so in the test name (`Should_ForfeitCredits_When_CancellingFiveMinutesAfterTheCutOff`). If the application reads the system clock directly, the clock cannot be controlled: **defer** the case and hand the clock seam to `be-java`.

**Never** `Thread.sleep` to reach a boundary, and never mock static `Instant.now()` (`mockStatic`) against a running server: it moves nothing in another process and is thread-local to the mocking thread in-process.

**Version twin.** The `@TestConfiguration` + `@Primary` form works on every Boot 3.x minor. To replace a bean with a Mockito mock instead, `@MockitoBean` needs Spring Framework 6.2 (Boot 3.4+); on Boot 3.2–3.3 the twin is `@MockBean`, deprecated in 3.4 and removed in Boot 4.

#### Concurrent requests

Release N requests together behind a start gate (`Race.startTogether`, in `references/helpers.md`: a ready latch, a start latch, futures), wait for all to settle, assert the **invariant**, never which request won. Repetition comes from TestNG's `invocationCount`.


- `invocationCount = 20` runs the method 20 times, and `@BeforeMethod` / `@AfterMethod` run around every invocation, so seed inside the test or in `@BeforeMethod` and each repetition starts clean. Leave `successPercentage` at its default 100: lowering it hides the race.
- **Not** `threadPoolSize`: it runs invocations in parallel on shared fixtures and does not align requests at the same instant. The latch pair does.
- The refusal gets its own test naming the one expected refusal (`409`), never `409 or 422`.
- The invariant is a `db-testing/verification-queries` query (`confirmed ≤ capacity`), asserted after all calls settle.
- A race with a schedule releases the job call and the request behind the same gate; release the ShedLock row first.
- A failure on any invocation is a defect, never a flake to retry away.

#### Duplicate and out-of-order delivery, idempotency

The effect must happen once. Each form delivers the **same business id** a second time:

```java
@Test
public void Should_ReturnCreditsUsedTo6Not4_When_TheCancellationEventIsDeliveredTwice() {
    Booking booking = bookings.seedCancelled(Bookings.valid().creditsUsed(8).credits(2).build());
    String body = Json.write(CancellationEvents.of(booking));

    sendToCreditsQueue(body, booking.id());
    sendToCreditsQueue(body, booking.id());

    DbWaits.waitForRow("processed-" + booking.id(), () -> inboxProbe.processedCount(booking.id()),
        count -> count == 2L, CREDITS_BUDGET, Duration.ofMillis(200));
    assertThat(memberProbe.creditsUsed(booking.memberId()))
        .as("credits used for member %s", booking.memberId()).isEqualTo(6L);
}

private void sendToCreditsQueue(String body, UUID businessId) {
    sqs.sendMessage(request -> request.queueUrl(creditsUrl).messageBody(body)
        .messageGroupId(businessId.toString())
        .messageDeduplicationId(UUID.randomUUID().toString()));
}
```

- **Message** — publish through the project's `messaging-testing` reference (its producer / seed helper), with a **new broker message id and the same business id**. Broker deduplication swallows an identical publish before the consumer sees it — SQS FIFO (`messageDeduplicationId`, `ContentBasedDeduplication`), Service Bus duplicate detection, Kafka's idempotent producer — and such a test proves nothing about the consumer's idempotency. Vary the dedup id (or use a standard queue) so two deliveries reach the consumer.
- **Wait on a positive signal, never a sleep:** an inbox / processed-messages row per delivery through `DbWaits.waitForRow`, then assert the effect count. SQS queue-depth attributes are approximate, so they are not the signal.
- **Webhook** — replay the request with the same delivery id through the typed client twice; assert one effect and, if the contract says so, the same response both times.
- **Idempotency key** — resend the request with the same `Idempotency-Key`; assert one resource and the contracted response.
- **Out of order** — publish the two events in reverse order, then assert the spec's declared outcome (one value).

#### Invariant after a sequence

A `db-testing/verification-queries` query asserting the invariant's statement (`SELECT COUNT(*) … HAVING …`), run after the sequence settles.

## Anti-patterns

- **Waiting for the real schedule** or a `Thread.sleep` for the job to fire — a blocker. Trigger it.
- **An idempotency re-run that ShedLock skipped** — the test passes for the wrong reason.
- **`mockStatic(Instant.class)`** or a sleep to reach a boundary.
- **A boundary test with no controlled clock and no stated skew margin.**
- **Asserting which request won**, or an `OR` on the status.
- **A `for` loop firing the race or driving assertions** — use `invocationCount` and `Race.startTogether`; parameterize with `@DataProvider`.
- **A race with no gate** (`a(); b();` is sequential, not concurrent), or `threadPoolSize` as the barrier.
- **A duplicate test that broker deduplication defeats.**
- **An `@Test(enabled = false)` or commented-out test for a missing hook** — defer in the report instead.
- **`try`/`catch` in a test body or `@AfterMethod`** — an expected refusal is asserted on the response, an unexpected error reaches TestNG.

## Hard rules

- No sleeps and no waiting for the real schedule: jobs run on demand, effects are polled with the case's budget.
- The clock is replaced in the in-process host or driven by an environment hook; code that reads the system clock directly is deferred to `be-java`.
- A job guarded by ShedLock has its lock row released before each run, and every run's execution is asserted.
- Data is seeded relative to the controlled "now"; every instant states its timezone.
- A race test releases N requests behind a gate, repeats through `invocationCount`, and asserts the invariant, never the winner.
- A duplicate-delivery test uses a new broker message id with the same business id, and waits on a positive processed signal.
- A missing seam is a **deferral**: named in the report with the hook, handed to `be-java`, with no test body committed.
- Cleanup runs in `@BeforeMethod` / `@AfterMethod(alwaysRun = true)`; failure messages carry the evidence (ids, the instant, the response body).

## Handoffs

- A missing job trigger, clock seam or test endpoint → `be-java`, as a product change.
- Broker producer / seeding helpers, DLQ → `qa/java/skills/messaging-testing`.
- Verification queries, the poller and the cleanup helper → `qa/java/skills/db-testing/verification-queries`, `…/db-testing/connection`.
- A retry or recovery after a fault → `qa/java/skills/failure-injection-testing`.
- Typed clients for the trigger or clock endpoint → `qa/java/skills/api-client-writer`.
- The plain tests → `qa/java/skills/api-test-author/writer`; review → `…/api-test-author/review`.

## APIs checked (2026-10-11)

Java 21 · Spring Boot 3.2–3.5 (3.5.16 is the last OSS release; `@TestConfiguration` + `@Primary` on all; `@MockitoBean` from Spring Framework 6.2 / Boot 3.4, `@MockBean` deprecated in 3.4) · Spring `@Scheduled` and `Scheduled.CRON_DISABLED` · Quartz 2.x `Scheduler.triggerJob(JobKey)` (a fire-now trigger, not a synchronous run) · ShedLock 4+ (`PROXY_METHOD` default: the lock applies on a direct call, a held lock skips the method silently; `lockAtLeastFor` keeps it held) · TestNG 7.10–7.12 (`invocationCount`, `successPercentage`, `threadPoolSize`; `@BeforeMethod` per invocation unless `firstTimeOnly = true`) · Awaitility 4.
