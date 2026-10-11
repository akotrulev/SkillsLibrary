# Deep-dive details — `qa-java:failure-injection-testing`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## The mechanism — proxy BETWEEN app and dependency (idea #2)

Stand the dependency and Toxiproxy up on a **shared Docker `Network`**, create a proxy whose **upstream** is the
dependency and whose **listen** side is what the app connects to, then **point the app at the proxy's mapped
port**. Everything downstream flows through the fault point.

```java
package support.chaos;

import eu.rekawek.toxiproxy.Proxy;
import eu.rekawek.toxiproxy.ToxiproxyClient;
import org.testcontainers.containers.Network;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.containers.ToxiproxyContainer;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;

import java.io.IOException;

/** Stands the dependency + Toxiproxy up on one Network and exposes the proxied connection point. */
public abstract class BaseChaosTest {
    private static final Network NETWORK = Network.newNetwork();

    protected static PostgreSQLContainer<?> dependency;       // the dependency under fault (example)
    protected static ToxiproxyContainer toxiproxy;
    protected ChaosProxy chaos;                               // the intent-named toxic helper

    @BeforeClass(alwaysRun = true)
    public void startInfrastructure() throws IOException {
        dependency = new PostgreSQLContainer<>("postgres:16-alpine")
                .withNetwork(NETWORK)
                .withNetworkAliases("db");                    // the upstream host on the shared network
        toxiproxy = new ToxiproxyContainer("ghcr.io/shopify/toxiproxy:2.11.0")
                .withNetwork(NETWORK);
        dependency.start();
        toxiproxy.start();

        ToxiproxyClient client = new ToxiproxyClient(toxiproxy.getHost(), toxiproxy.getControlPort());
        // listen on 8666 inside the proxy; upstream = the dependency by its network alias + internal port.
        Proxy proxy = client.createProxy("db", "0.0.0.0:8666", "db:5432");

        // The app connects HERE — the proxy's mapped listen port, NOT the real dependency's port.
        String proxiedHost = toxiproxy.getHost();
        int proxiedPort = toxiproxy.getMappedPort(8666);
        chaos = new ChaosProxy(proxy, proxiedHost, proxiedPort);
    }

    @AfterClass(alwaysRun = true)
    public void stopInfrastructure() {
        if (toxiproxy != null) toxiproxy.stop();
        if (dependency != null) dependency.stop();
    }
}
```

> The app under test must be configured to talk to `chaos.host():chaos.port()` (the JDBC URL / base URL / broker
> bootstrap server pointed at the proxy), **not** the dependency directly. That redirection *is* the chaos setup —
> if the app bypasses the proxy, no toxic can reach it.

## The toxic helper — `support/chaos/ChaosProxy.java`

One helper owns the proxy handle and exposes **intent-named** fault operations and a **lifecycle** primitive, so
tests read `chaos.injectLatency(...)`, `chaos.cutConnection()`, `chaos.healed()` — never raw
`proxy.toxics().timeout(...)` scattered across `@Test` methods. Each injected toxic is named so it can be removed.

```java
package support.chaos;

import eu.rekawek.toxiproxy.Proxy;
import eu.rekawek.toxiproxy.model.Toxic;
import eu.rekawek.toxiproxy.model.ToxicDirection;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/** Intent-named fault injection over a single Toxiproxy proxy, with a remove-all "heal" for the lifecycle. */
public final class ChaosProxy {
    private final Proxy proxy;
    private final String host;
    private final int port;
    private final List<String> injected = new ArrayList<>();

    public ChaosProxy(Proxy proxy, String host, int port) {
        this.proxy = proxy; this.host = host; this.port = port;
    }

    public String host() { return host; }   // the app points its connection string here…
    public int port()    { return port; }   // …and at this port

    /** Slow every response by `millis` (+ jitter) — the "dependency is slow" fault. */
    public Toxic injectLatency(long millis, long jitter) throws IOException {
        Toxic t = proxy.toxics().latency("latency", ToxicDirection.DOWNSTREAM, millis).setJitter(jitter);
        injected.add("latency");
        return t;
    }

    /** Stop all data and close the connection after `millis` — the "dependency hangs then drops" fault. */
    public void injectTimeout(long millis) throws IOException {
        proxy.toxics().timeout("timeout", ToxicDirection.UPSTREAM, millis);
        injected.add("timeout");
    }

    /** Reset the TCP peer after `millis` — the "connection dropped" fault that exercises retry/breaker code. */
    public Toxic cutConnection(long millis) throws IOException {
        Toxic t = proxy.toxics().resetPeer("reset", ToxicDirection.DOWNSTREAM, millis);
        injected.add("reset");
        return t;
    }

    /** Throttle the backend dependency to `rateKbps` KB/s — bandwidth starvation (NOT device conditioning). */
    public void throttle(long rateKbps) throws IOException {
        proxy.toxics().bandwidth("bw", ToxicDirection.DOWNSTREAM, rateKbps);
        injected.add("bw");
    }

    /** Cut the response after `bytes` — a partial/truncated response the app must not persist as valid. */
    public void truncateAfter(long bytes) throws IOException {
        proxy.toxics().limitData("limit", ToxicDirection.DOWNSTREAM, bytes);
        injected.add("limit");
    }

    /** Make a toxic probabilistic (0..1) for an intermittent/flappy fault. */
    public Toxic withToxicity(Toxic toxic, float toxicity) throws IOException {
        toxic.setToxicity(toxicity);
        return toxic;
    }

    /** Remove ALL injected toxics — the dependency is "healed" (lifecycle step: assert recovery after this). */
    public void healed() throws IOException {
        for (String name : injected) proxy.toxics().get(name).remove();
        injected.clear();
    }
}
```
