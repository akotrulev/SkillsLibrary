# Observability — Windows reference

Facts from `docs/research/012-desktop-plugins/windows.md` §9 (verified 2026-11-15). §4.6 note: whether `winui-mvvm` wires `Microsoft.Extensions.Hosting` is not verified, so these samples show both the Host path and plain construction. Sentry's `IsGlobalModeEnabled` guidance for desktop apps and the exact exporter patch version were reported inconsistently by secondary sources: read docs.sentry.io and nuget.org before pinning.

## OpenTelemetry .NET (1.21.0) in a desktop process

A desktop process is long-lived and has no request scope: tracing is explicit around user-visible operations, and the SDK is built once in the composition root.

```csharp
public static class Telemetry
{
    public static IHost AddTelemetry(this IHostBuilder builder, Uri gateway, string ingestKey, string version)
    {
        builder.ConfigureServices(services =>
        {
            services.AddOpenTelemetry()
                .ConfigureResource(r => r
                    .AddService("shop-desktop-windows", serviceVersion: version)
                    .AddAttributes(new Dictionary<string, object>
                    {
                        ["deployment.environment.name"] = "production",
                        ["session.id"] = Guid.NewGuid().ToString()
                    }))
                .WithTracing(t => t
                    .AddSource("Shop.Desktop")
                    .SetSampler(new ParentBasedSampler(new TraceIdRatioBasedSampler(0.05)))
                    .AddHttpClientInstrumentation()
                    .AddOtlpExporter(o =>
                    {
                        o.Endpoint = new Uri(gateway, "v1/traces");
                        o.Protocol = OtlpExportProtocol.HttpProtobuf;
                        o.Headers = $"x-ingest-key={ingestKey}";
                    }));
        });
        return builder.Build();
    }
}
```

- `AddOpenTelemetry()` lives on the Host's DI; a project without a Host builds the same providers with `Sdk.CreateTracerProviderBuilder()` in `App`'s constructor and disposes them on exit.
- `AddOtlpExporter` uses the **batch** processor by default; never `SimpleActivityExportProcessor` in release. OTLP/HTTP protobuf to the gateway, never a backend host.
- Instrument by `ActivitySource` (`Shop.Desktop`): `using var activity = Source.StartActivity("document.save")`; no ASP.NET instrumentation (there is no server); `AddHttpClientInstrumentation` for outbound calls with the query string excluded.
- No `AddMeter` per click: a counter per business event, a histogram per user-visible duration.
- Dispose the provider (or the Host) on `AppWindow.Closing` / `Application.Exit` so the final batch flushes; a laptop sleep (`PowerManager`) triggers `ForceFlush`.
- Exporter failures are swallowed by the SDK and logged to its self-diagnostics; they never reach the UI thread. A full queue drops.

## `ILogger`

```csharp
public sealed partial class SyncService(ILogger<SyncService> logger)
{
    [LoggerMessage(Level = LogLevel.Information, Message = "Sync finished: {ItemCount} items")]
    private partial void LogSyncFinished(int itemCount);
}
```

- Source-generated `LoggerMessage` (message template, named fields); never `$"..."` into a log call; no `Debug.WriteLine` or `Console.WriteLine` of a value.
- Logs reach Loki only through the OTel logs exporter (`AddOpenTelemetry` logging provider with `IncludeFormattedMessage = false`, `ParseStateValues = true`) behind the same scrubber; a file sink under local app data is for support bundles, rotated, and carries no token or full path.
- Log level in release is `Information`; `Debug` never leaves the machine.

## Sentry .NET 7.0.0 (WinUI, WPF)

```csharp
public partial class App : Application
{
    public App()
    {
        SentrySdk.Init(options =>
        {
            options.Dsn = Dsn;
            options.Release = $"shop-desktop-windows@{Version}";
            options.SendDefaultPii = false;
            options.TracesSampleRate = 0.05;
            options.SetBeforeSend(Scrubber.Scrub);
        });
        InitializeComponent();
    }
}
```

- Initialise in the `App` constructor, **not** `OnLaunched` (Sentry's WinUI compatibility note: the hub may not initialise correctly there). Unhandled exceptions are captured automatically; with trimming on, add an `UnhandledException` handler and `SentrySdk.FlushAsync` after capture.
- WPF needs the WPF integration as well as `SentrySdk.Init`; WinForms uses the .NET SDK with `Application.ThreadException` hooked.
- `SendDefaultPii` stays off (it adds user IP and username); the user.name Windows account is never attached.
- Scrubbing: `SetBeforeSend` and `SetBeforeBreadcrumb` remove `Authorization`, query strings, and the user profile folder from every file path (`C:\Users\<name>\` → `%USERPROFILE%`).
- Upload PDBs with `sentry-cli` from CI; the auth token lives in the pipeline secret store. Packaged MSIX builds keep symbols out of the package.
- **WER** remains the platform channel: Partner Center health reports for Store MSIX, and the `windows.diagnosticServiceModule` manifest extension (Windows App SDK 2.5.1) to hook crashes; local dump collection for LOB apps. WER and Sentry coexist; the *reporter* count rule (U1) counts third-party reporters.
- App Insights is allowed only for an Azure-only app, and then it is *the* reporter: never beside Sentry.

## Not in the app

The Collector, gateway limits, retention, dashboards and alert rules: `observability-engineer-dotnet` (and the other `observability-engineer-<stack>` agents).
