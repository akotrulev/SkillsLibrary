# Stack-native MCP servers — .NET and Java

**Take this lane only when the sidecar cannot work**: the capabilities are in-process and there is no HTTP API to reach them through. If the project already exposes HTTP, the TypeScript sidecar is the better answer — one deployable stays one deployable, and the SDK is stronger. **Never add an HTTP API to the project just to enable a sidecar**, and never rewrite the project to suit the tool surface.

Both SDKs below are younger than the TypeScript one and their APIs move. **Check the installed package version and its README before generating registrations** — the shapes here are the current ones, not permanent ones.

Everything in the parent `SKILL.md` still applies: one tool per capability, the shared envelope, the closed error vocabulary, examples in every parameter description, clamped paging, a `confirm` gate on destructive capabilities.

---

## .NET (net10.0 / net8.0)

Package: `ModelContextProtocol` (+ `ModelContextProtocol.AspNetCore` for HTTP transport). Confirm the version:

```bash
dotnet add package ModelContextProtocol
dotnet list package
```

Host wiring, stdio:

```csharp
var builder = Host.CreateApplicationBuilder(args);

builder.Logging.AddConsole(o => o.LogToStandardErrorThreshold = LogLevel.Trace);

builder.Services
    .AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly();

builder.Services.AddOptions<ContosoOptions>()
    .BindConfiguration("Contoso")
    .ValidateDataAnnotations()
    .ValidateOnStart();

builder.Services.AddHttpClient<IOrdersClient, OrdersClient>();

await builder.Build().RunAsync();
```

`LogToStandardErrorThreshold` is not optional on stdio: **the default console logger writes to stdout and corrupts the protocol stream.** `ValidateOnStart` is the fail-fast gate from the contract's dependency table.

A tool:

```csharp
[McpServerToolType]
public sealed class OrderTools(IOrdersClient client)
{
    [McpServerTool(Name = "orders_place", Destructive = false, ReadOnly = false, Idempotent = true)]
    [Description("Creates a pending order from resolved customer and product ids and reserves stock. " +
                 "Use after resolving ids with customers_list and products_search; to read an existing order use orders_get. " +
                 "Retrying with the same idempotencyKey returns the original order.")]
    public async Task<Envelope<OrderSummary>> PlaceAsync(
        [Description("Customer id from customers_list. Example: 3f2a1c8e-…")] Guid customerId,
        [Description("ISO 4217 currency, one of EUR, USD, GBP. Example: EUR")] string currency,
        [Description("Order lines, 1–100.")] IReadOnlyList<OrderLineInput> lines,
        [Description("Caller-generated, stable across retries of one attempt. Example: place-7f3a")] string idempotencyKey,
        CancellationToken ct)
    {
        var result = await client.PlaceAsync(customerId, currency, lines, idempotencyKey, ct);
        return result.Match(
            order => Envelope.Ok(OrderSummary.From(order)),
            conflict => Envelope.Error<OrderSummary>(ErrorCode.Conflict, conflict.Message, conflict.Field));
    }
}
```

- Tool classes are registered by `WithToolsFromAssembly()` and get **constructor injection** — the same DI rules as the rest of the project, no service locator.
- `[Description]` on the method is the routing text; `[Description]` on every parameter carries the example. The schema is generated from the signature, so **the C# types are the contract**: `Guid` not `string`, an `enum` not a `string`, a `record` for nested input.
- Records for inputs and outputs; nullable reference types on.
- Async all the way, `CancellationToken` threaded through — the SDK passes one, and a tool that ignores it cannot be cancelled by the client.
- The envelope is a shared type, and every tool returns it. Exceptions are caught at the client boundary and mapped to `ErrorCode`, never allowed to escape the handler.

HTTP transport instead of stdio, when the server is shared:

```csharp
builder.Services.AddMcpServer().WithHttpTransport().WithToolsFromAssembly();
// …
app.MapMcp();
```

Mount it behind the app's existing authentication. Do not invent an auth scheme in the tool layer.

Smoke it the same way as any other lane:

```bash
dotnet build
npx @modelcontextprotocol/inspector dotnet run --project src/Orders.Mcp
```

---

## Java 21 / Spring Boot 3.x

Starter: `spring-ai-starter-mcp-server` (stdio) or `spring-ai-starter-mcp-server-webmvc` (HTTP). Gradle (Kotlin DSL), version from the Spring AI BOM the project already pins — **do not introduce a second BOM**.

```yaml
spring:
  main:
    banner-mode: off
  ai:
    mcp:
      server:
        name: orders-mcp
        version: 1.0.0
        stdio: true
```

`banner-mode: off` plus routing logging to stderr, for the same stdout reason as every other lane.

A tool:

```java
@Service
public class OrderTools {

    private final OrdersClient client;

    public OrderTools(OrdersClient client) {
        this.client = client;
    }

    @Tool(name = "orders_place",
          description = "Creates a pending order from resolved customer and product ids and reserves stock. "
                      + "Use after resolving ids with customers_list and products_search; to read an existing order use orders_get. "
                      + "Retrying with the same idempotencyKey returns the original order.")
    public Envelope<OrderSummary> place(
            @ToolParam(description = "Customer id from customers_list. Example: 3f2a1c8e-…") UUID customerId,
            @ToolParam(description = "ISO 4217 currency. Example: EUR") Currency currency,
            @ToolParam(description = "Order lines, 1-100.") List<OrderLine> lines,
            @ToolParam(description = "Caller-generated, stable across retries. Example: place-7f3a") String idempotencyKey) {
        return client.place(customerId, currency, lines, idempotencyKey);
    }
}
```

Registered by exposing the bean's methods as callbacks:

```java
@Bean
ToolCallbackProvider orderToolCallbacks(OrderTools tools) {
    return MethodToolCallbackProvider.builder().toolObjects(tools).build();
}
```

- `record` types for inputs and outputs; an `enum` for every enumerated field — the JSON schema is generated from the signature, so the types are the contract.
- Constructor injection, no field injection.
- Config from `@ConfigurationProperties` with `@Validated`, failing at startup when a required value is missing.
- Errors caught at the client boundary and mapped to the closed vocabulary; nothing thrown out of a `@Tool` method.

---

## Deciding, in one table

| Situation | Build |
|---|---|
| Project is Node/TS | TypeScript, in-process |
| Project has an HTTP API (any stack) | TypeScript sidecar |
| .NET, in-process capabilities only | .NET, `ModelContextProtocol` |
| Java, in-process capabilities only | Spring AI MCP |
| Project has no API and adding one is cheap and independently justified | Say so, but still do not couple the two decisions — the sidecar is not a reason to add an API |
