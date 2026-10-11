# Helpers for `time-and-concurrency-testing`

Copy into `Tests/Support/Time/`; each helper performs I/O or holds test state, so its failures are the contract and are never caught.

## CronJobRunner

```csharp
public static class CronJobRunner
{
    public static async Task<string> RunNowAsync(string cronJob, string ns, CancellationToken ct)
    {
        string job = $"{cronJob}-test-{Guid.NewGuid().ToString("N")[..8]}";
        await KubectlAsync(ct, "create", "job", job, $"--from=cronjob/{cronJob}", "-n", ns);
        await KubectlAsync(ct, "wait", "--for=condition=complete", $"job/{job}", "--timeout=120s", "-n", ns);
        return job;
    }

    private static async Task KubectlAsync(CancellationToken ct, params string[] arguments)
    {
        ProcessStartInfo start = new("kubectl", arguments)
        {
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        using Process process = Process.Start(start)!;
        Task<string> output = process.StandardOutput.ReadToEndAsync(ct);
        Task<string> errors = process.StandardError.ReadToEndAsync(ct);
        await process.WaitForExitAsync(ct);
        Assert.That(process.ExitCode, Is.Zero,
            $"kubectl {string.Join(' ', arguments)} -> {await output}{await errors}");
    }
}
```

## The factory with a controlled clock

```csharp
public sealed class ApiFactory : WebApplicationFactory<Program>
{
    public static readonly DateTimeOffset DefaultNow = new(2026, 3, 1, 0, 0, 0, TimeSpan.Zero);

    public FakeTimeProvider Clock { get; } = new(DefaultNow);

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.ConfigureTestServices(services =>
        {
            services.RemoveAll<TimeProvider>();
            services.AddSingleton<TimeProvider>(Clock);
        });
    }
}
```

Top-level `Program.cs` needs `public partial class Program;` for `WebApplicationFactory<Program>`.

The base fixture creates the factory once and rewinds the clock before each test, because the host is cached across tests:

```csharp
public abstract class IntegrationTestBase
{
    protected ApiFactory Factory { get; private set; } = null!;

    [OneTimeSetUp]
    public void StartHost() => Factory = new ApiFactory();

    [OneTimeTearDown]
    public async Task StopHost() => await Factory.DisposeAsync();

    [SetUp]
    public void ResetClock() => Factory.Clock.AdjustTime(ApiFactory.DefaultNow);
}
```

## Race

```csharp
public static class Race
{
    public static async Task<IReadOnlyList<T>> StartTogetherAsync<T>(int count, Func<int, Task<T>> action)
    {
        int arrived = 0;
        TaskCompletionSource allReady = new(TaskCreationOptions.RunContinuationsAsynchronously);
        TaskCompletionSource gate = new(TaskCreationOptions.RunContinuationsAsynchronously);

        Task<T>[] calls = Enumerable.Range(0, count)
            .Select(index => Task.Run(async () =>
            {
                if (Interlocked.Increment(ref arrived) == count)
                {
                    allReady.SetResult();
                }
                await gate.Task;
                return await action(index);
            }))
            .ToArray();

        await allReady.Task;
        gate.SetResult();
        return await Task.WhenAll(calls);
    }
}
```

Keep `count` small (2–10): every call holds a thread-pool thread until the gate opens.

```csharp
[Test, Repeat(20)]
public async Task Should_ConfirmExactlyOneBooking_When_TwoMembersTakeTheLastSeat()
{
    SessionDto session = await sessions.SeedAsync(SessionBuilder.Valid().WithCapacity(1).Build());
    createdSessionIds.Add(session.Id);

    IReadOnlyList<RestResponse> responses = await Race.StartTogetherAsync(2,
        index => memberBookingClients[index].BookAsync(session.Id));

    Assert.That(responses.Count(response => response.StatusCode == HttpStatusCode.Created), Is.EqualTo(1),
        $"confirmed of {responses.Count} requests for session {session.Id}");
    Assert.That(await bookingProbe.ConfirmedCountAsync(session.Id), Is.EqualTo(1L),
        $"confirmed rows for session {session.Id}");
}
```
