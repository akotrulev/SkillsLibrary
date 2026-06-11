# Deep-dive details — `qa-chaos-testing-dotnet`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## The toxic helper — `Support/Chaos/ChaosProxy.cs`

One helper owns the proxy handle and exposes **intent-named** fault operations and a **heal** for the lifecycle, so
tests read `Chaos.InjectLatency(...)`, `Chaos.CutConnection()`, `Chaos.Healed()` — never raw `proxy.Add(new
TimeoutToxic { ... })` scattered across `[Test]` methods. Each injected toxic is named so it can be removed.

```csharp
namespace Tests.Support.Chaos;

using Toxiproxy.Net;
using Toxiproxy.Net.Toxics;

/// Intent-named fault injection over a single Toxiproxy proxy, with a remove-all "heal" for the lifecycle.
public sealed class ChaosProxy(Proxy proxy, string host, int port)
{
    private readonly List<string> _injected = [];

    public string Host => host;   // the app points its connection string here…
    public int Port => port;      // …and at this port

    /// Slow every response by `millis` (+ jitter) — the "dependency is slow" fault.
    public ToxicBase InjectLatency(int millis, int jitter) =>
        Add(new LatencyToxic { Name = "latency", Stream = ToxicDirection.DownStream,
            Attributes = { Latency = millis, Jitter = jitter } });

    /// Stop all data and close the connection after `millis` — the "dependency hangs then drops" fault.
    public ToxicBase InjectTimeout(int millis) =>
        Add(new TimeoutToxic { Name = "timeout", Stream = ToxicDirection.UpStream,
            Attributes = { Timeout = millis } });

    /// Reset the TCP peer after `millis` — the "connection dropped" fault that exercises retry/breaker code.
    public ToxicBase CutConnection(int millis) =>
        Add(new ResetPeerToxic { Name = "reset", Stream = ToxicDirection.DownStream,
            Attributes = { Timeout = millis } });

    /// Throttle the backend dependency to `rateKbps` KB/s — bandwidth starvation (NOT device conditioning).
    public ToxicBase Throttle(int rateKbps) =>
        Add(new BandwidthToxic { Name = "bw", Stream = ToxicDirection.DownStream,
            Attributes = { Rate = rateKbps } });

    /// Cut the response after `bytes` — a partial/truncated response the app must not persist as valid.
    public ToxicBase TruncateAfter(int bytes) =>
        Add(new LimitDataToxic { Name = "limit", Stream = ToxicDirection.DownStream,
            Attributes = { Bytes = bytes } });

    /// Make a toxic probabilistic (0..1) for an intermittent/flappy fault.
    public ToxicBase WithToxicity(ToxicBase toxic, double toxicity)
    {
        toxic.Toxicity = toxicity;
        proxy.UpdateToxic(toxic.Name, toxic);
        return toxic;
    }

    /// Remove ALL injected toxics — the dependency is "healed" (lifecycle step: assert recovery after this).
    public void Healed()
    {
        foreach (var name in _injected) proxy.RemoveToxic(name);
        _injected.Clear();
    }

    private ToxicBase Add(ToxicBase toxic)
    {
        proxy.Add(toxic);
        _injected.Add(toxic.Name);
        return toxic;
    }
}
```

## The mechanism — proxy BETWEEN app and dependency (idea #2)

Stand the dependency and Toxiproxy up on a **shared Docker `Network`**, create a proxy whose **upstream** is the
dependency and whose **listen** side is what the app connects to, then **point the app at the proxy's mapped
port**.

```csharp
namespace Tests.Support.Chaos;

using DotNet.Testcontainers.Builders;
using DotNet.Testcontainers.Networks;
using Testcontainers.PostgreSql;
using Testcontainers.Toxiproxy;
using Toxiproxy.Net;
using Toxiproxy.Net.Toxics;

public abstract class BaseChaosTest
{
    private static readonly INetwork Network = new NetworkBuilder().Build();

    protected static PostgreSqlContainer Dependency = null!;   // the dependency under fault (example)
    protected static ToxiproxyContainer Toxiproxy = null!;
    protected ChaosProxy Chaos = null!;                        // the intent-named toxic helper

    [OneTimeSetUp]
    public async Task StartInfrastructure()
    {
        Dependency = new PostgreSqlBuilder()
            .WithImage("postgres:16-alpine")
            .WithNetwork(Network)
            .WithNetworkAliases("db")                          // the upstream host on the shared network
            .Build();
        Toxiproxy = new ToxiproxyBuilder()
            .WithImage("ghcr.io/shopify/toxiproxy:2.11.0")
            .WithNetwork(Network)
            .Build();
        await Dependency.StartAsync();
        await Toxiproxy.StartAsync();

        var connection = new Connection(Toxiproxy.Hostname, Toxiproxy.GetMappedPublicPort(ToxiproxyBuilder.ControlPort));
        var client = connection.Client();
        var proxy = client.Add(new Proxy
        {
            Name = "db",
            Listen = "0.0.0.0:8666",                           // proxy listen side
            Upstream = "db:5432",                              // the dependency by its network alias + internal port
            Enabled = true,
        });

        // The app connects HERE — the proxy's mapped listen port, NOT the real dependency's port.
        var proxiedHost = Toxiproxy.Hostname;
        var proxiedPort = Toxiproxy.GetMappedPublicPort(8666);
        Chaos = new ChaosProxy(proxy, proxiedHost, proxiedPort);
    }

    [OneTimeTearDown]
    public async Task StopInfrastructure()
    {
        if (Toxiproxy is not null) await Toxiproxy.DisposeAsync();
        if (Dependency is not null) await Dependency.DisposeAsync();
    }
}
```

> The app under test must be configured to talk to `Chaos.Host:Chaos.Port` (the connection string / base URL /
> bootstrap server pointed at the proxy), **not** the dependency directly. That redirection *is* the chaos setup.
