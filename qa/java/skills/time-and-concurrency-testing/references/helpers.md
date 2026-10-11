# Helpers for `time-and-concurrency-testing`

Copy into `src/test/java/support/time/`; each is a helper that performs I/O or holds test state, so its `throws` clauses are the contract.

## CronJobRunner

```java
public final class CronJobRunner {

    private CronJobRunner() {}

    public static String runNow(String cronJob, String namespace) throws IOException, InterruptedException {
        String job = cronJob + "-test-" + UUID.randomUUID().toString().substring(0, 8);
        kubectl("create", "job", job, "--from=cronjob/" + cronJob, "-n", namespace);
        kubectl("wait", "--for=condition=complete", "job/" + job, "--timeout=120s", "-n", namespace);
        return job;
    }

    private static void kubectl(String... arguments) throws IOException, InterruptedException {
        List<String> command = new ArrayList<>(List.of("kubectl"));
        command.addAll(List.of(arguments));
        Process process = new ProcessBuilder(command).redirectErrorStream(true).start();
        String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        assertThat(process.waitFor()).as("%s -> %s", String.join(" ", command), output).isZero();
    }
}
```

## MutableClock and its test configuration

```java
public final class MutableClock extends Clock {

    private final AtomicReference<Instant> instant;
    private final ZoneId zone;

    public MutableClock(Instant start, ZoneId zone) {
        this(new AtomicReference<>(start), zone);
    }

    private MutableClock(AtomicReference<Instant> instant, ZoneId zone) {
        this.instant = instant;
        this.zone = zone;
    }

    public void set(Instant moment) { instant.set(moment); }

    @Override public Instant instant() { return instant.get(); }
    @Override public ZoneId getZone() { return zone; }
    @Override public Clock withZone(ZoneId other) { return new MutableClock(instant, other); }
}

@TestConfiguration(proxyBeanMethods = false)
public class ControlledClockConfig {

    @Bean
    @Primary
    MutableClock controlledClock() {
        return new MutableClock(Instant.parse("2026-03-01T00:00:00Z"), ZoneId.of("Europe/London"));
    }
}
```

## Race

```java
public final class Race {

    private Race() {}

    public static <T> List<T> startTogether(int count, IntFunction<T> action) throws Exception {
        CountDownLatch ready = new CountDownLatch(count);
        CountDownLatch gate = new CountDownLatch(1);
        try (ExecutorService pool = Executors.newFixedThreadPool(count)) {
            List<Future<T>> calls = IntStream.range(0, count)
                .mapToObj(index -> pool.submit(() -> {
                    ready.countDown();
                    gate.await();
                    return action.apply(index);
                }))
                .toList();
            ready.await();
            gate.countDown();
            List<T> results = new ArrayList<>();
            for (Future<T> call : calls) {
                results.add(call.get());
            }
            return results;
        }
    }
}

@Test(invocationCount = 20)
public void Should_ConfirmExactlyOneBooking_When_TwoMembersTakeTheLastSeat() throws Exception {
    Session session = sessions.seed(Sessions.valid().capacity(1).build());
    createdSessionIds.add(session.id());

    List<Response> responses = Race.startTogether(2, index -> memberBookingClients.get(index).book(session.id()));

    assertThat(responses.stream().filter(response -> response.statusCode() == HttpStatus.SC_CREATED).count())
        .as("confirmed of %s requests for session %s", responses.size(), session.id()).isEqualTo(1L);
    assertThat(bookingProbe.confirmedCount(session.id()))
        .as("confirmed rows for session %s", session.id()).isEqualTo(1L);
}
```

