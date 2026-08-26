# Stack-native CLIs — .NET and Java

Match the project's stack so the tool builds, tests, and ships with everything else. Everything in the parent `SKILL.md` applies unchanged: `<bin> <noun> <verb>`, one command per capability, `--json` emitting the envelope, stdout reserved for results, the exit-code table, secrets from configuration only, `--dry-run` and a confirmation on destructive commands.

---

## .NET — `System.CommandLine`

**Check the installed version before writing.** `System.CommandLine` is still shipping betas and has renamed core members between them (`SetHandler` → `SetAction`; `Option<T>` construction and `ParseResult` accessors have both moved). Generate against the API of the version in the project, not from memory:

```bash
dotnet add package System.CommandLine --prerelease
dotnet list package
```

Package it as a `dotnet tool` so installation is one line:

```xml
<PropertyGroup>
  <PackAsTool>true</PackAsTool>
  <ToolCommandName>orders</ToolCommandName>
  <Nullable>enable</Nullable>
  <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
</PropertyGroup>
```

Shape:

```csharp
var json = new Option<bool>("--json") { Description = "Emit the result envelope as JSON on stdout" };
var yes  = new Option<bool>("--yes")  { Description = "Skip confirmation prompts" };

var root = new RootCommand("Drive the Contoso ordering surface from a terminal or a script.");
root.Options.Add(json);
root.Options.Add(yes);

var orders = new Command("orders", "Orders");
root.Subcommands.Add(orders);

var customerId = new Option<Guid>("--customer-id")
{
    Description = "Customer id from `orders customers list`. Example: 3f2a1c8e-…",
    Required = true,
};
var currency = new Option<Currency>("--currency")
{
    Description = "ISO 4217, one of EUR|USD|GBP. Example: EUR",
    Required = true,
};

var place = new Command("place", "Create a pending order from resolved ids and reserve stock.");
place.Options.Add(customerId);
place.Options.Add(currency);

place.SetAction(async (parse, ct) =>
{
    var input = new PlaceOrderInput(parse.GetValue(customerId), parse.GetValue(currency), …);
    var envelope = await client.PlaceAsync(input, ct);
    return Output.Write(envelope, parse.GetValue(json));
});

orders.Subcommands.Add(place);
return await root.Parse(args).InvokeAsync();
```

- **`Option<T>` with a real T does the parsing** — `Guid`, `enum`, `DateTimeOffset`, `int`. Never take a `string` and parse it yourself; the parser's error message is better than yours and it appears before any work runs.
- **`Output.Write` is the single exit point**, returning the exit code from the envelope's error code exactly as the TypeScript runner does. Nothing else writes to `Console.Out`; diagnostics use `Console.Error` or `ILogger` bound to stderr.
- **Constructor injection** for the client via the generic host, configured once in `Program.cs`; commands resolve it from DI, never `new` it inline.
- **`CancellationToken` threaded through** every async action — `SetAction`'s async overload supplies one and it carries Ctrl-C.
- Config through `IConfiguration` in the documented precedence (flag → env → file → default) with `ValidateOnStart`; secrets from environment or a secret store, never an option.
- `TreatWarningsAsErrors` plus nullable on, so the build is the first check.

---

## Java 21 — picocli

Gradle (Kotlin DSL), packaged as a runnable jar; add the annotation processor so help and completion are generated at build time rather than reflectively at runtime.

```kotlin
dependencies {
    implementation("info.picocli:picocli:4.7.6")
    annotationProcessor("info.picocli:picocli-codegen:4.7.6")
}
```

```java
@Command(name = "orders", mixinStandardHelpOptions = true, version = "1.0.0",
         description = "Drive the Contoso ordering surface from a terminal or a script.",
         subcommands = { OrdersCommand.class, ProductsCommand.class })
public final class Cli {
    @Option(names = "--json", scope = ScopeType.INHERIT,
            description = "Emit the result envelope as JSON on stdout")
    boolean json;

    @Option(names = "--yes", scope = ScopeType.INHERIT,
            description = "Skip confirmation prompts")
    boolean yes;

    public static void main(String[] args) {
        System.exit(new CommandLine(new Cli()).execute(args));
    }
}
```

```java
@Command(name = "place", description = "Create a pending order from resolved ids and reserve stock.")
final class PlaceCommand implements Callable<Integer> {

    @Option(names = "--customer-id", required = true,
            description = "Customer id from `orders customers list`. Example: 3f2a1c8e-…")
    UUID customerId;

    @Option(names = "--currency", required = true,
            description = "ISO 4217, one of ${COMPLETION-CANDIDATES}. Example: EUR")
    Currency currency;

    @Option(names = "--line", required = true, arity = "1..*",
            description = "Repeatable, productId:quantity, 1-100 lines. Example: 9c1b77d2-…:2")
    List<OrderLine> lines;

    @Override
    public Integer call() {
        return Output.write(client.place(customerId, currency, lines), json);
    }
}
```

- **`ScopeType.INHERIT`** puts the global flags on every subcommand without redeclaring them.
- **Typed fields do the parsing**: `UUID`, an `enum`, and a custom `ITypeConverter` for `productId:quantity`. A converter failure is a picocli parse error — mapped to exit `2` — before any work runs.
- **`${COMPLETION-CANDIDATES}`** puts the enum values into the help text automatically, so the enumeration cannot drift from the type.
- **`Callable<Integer>` returns the exit code**, from the same table as every other lane. `Output.write` is the only writer to `System.out`; everything else goes to `System.err` or SLF4J.
- Config through the project's existing mechanism, in the documented precedence; secrets from the environment or a store, never an `@Option`.

---

## Both lanes

| Rule | Why |
|---|---|
| The typed option is the validation | The parser's error beats a hand-rolled one and fires before any work |
| One `Output.write` / `Output.Write` | No command can invent its own shape or exit code |
| stdout is results only | Anything else breaks every pipe |
| No prompt unless stdin is a TTY | A prompt in CI hangs forever |
| `--dry-run` on write and destructive commands | The cheapest way to make an irreversible command safe to try |
| Commit a shell smoke script walking one flow | It tests the contract, the parsing, and the envelope together |
