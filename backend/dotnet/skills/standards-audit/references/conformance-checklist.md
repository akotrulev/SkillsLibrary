# be-dotnet Conformance Checklist — the 14 sections

The audit's spine. Section letters and check numbers are **permanent** — a finding is `<letter><n>` (`C3`, `G7`) and keeps that ID across every round, forever. Never renumber; append new checks at the end of a section with the next free number.

**How to read a row.** *Check* = the invariant. *Violation looks like* = what disqualifies it. *Find it with* = a mechanical lead (a hit is never a finding — read the code). *Sev* = the default severity; adjust for real impact and say why.

**Recipes** use `rg` (ripgrep), which honours `.gitignore` — so `bin/`, `obj/`, and `packages/` are skipped without flags. Without ripgrep, `grep -rn --include='*.cs' --exclude-dir=bin --exclude-dir=obj` is equivalent.

```bash
rg -n "<pattern>" --glob '*.cs'        # the shape every recipe below uses
rg -n "<pattern>" --glob '*.csproj'    # project-level checks
```

**The version lane gates everything.** .NET **10 primary / 8–9 supported**. Rows tagged **[net9+]**, **[net10]**, **[EFC8+]** apply only in that lane. Never flag a down-level project for lacking an up-level API, and never propose one as a fix.

**Owning skills:** [`pattern-guide`](../../pattern-guide/SKILL.md) · [`pattern-writer`](../../pattern-writer/SKILL.md) · [`code-review`](../../code-review/SKILL.md) · [`database-code`](../../database-code/SKILL.md) · [`auth0`](../../auth0/SKILL.md) · [`cognito`](../../cognito/SKILL.md) · `backend/_shared/{reference,reviewer}` · the bundled `observability/{opentelemetry-dotnet,structured-logging-dotnet}`.

---

## A — Build health, TFM & version lane
*Owning skills: `pattern-guide`, `code-review`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| A1 | The solution builds and analyzers are clean | Red on arrival — build errors, analyzer warnings treated as noise | Opt-in run only (`dotnet build`); otherwise inspect CI config + recent failures. Report as arrival state | major |
| A2 | One TFM across the solution (or a deliberate, documented split) | Projects spread across net6/net8/net10 with no migration plan — and the audit can't pick one lane | `rg -n "TargetFramework" --glob '*.csproj' --glob '*.props' \| sort -u` | major |
| A3 | TFM is supported | net6/net7 (out of support) or a preview TFM in `main` | same as A2 | major |
| A4 | EF Core major matches the TFM major | net8 project on EF Core 9/10 packages, or net10 on EF Core 8 | `rg -n "EntityFrameworkCore.*Version" --glob '*.csproj' --glob '*.props'` | major |
| A5 | `Nullable` enabled in every project | `<Nullable>` missing or `disable` | `rg -n "<Nullable>" --glob '*.csproj' --glob '*.props'` — count vs project count | major |
| A6 | Warnings are errors on CI at minimum | `TreatWarningsAsErrors` absent everywhere and CI ignores warnings | `rg -n "TreatWarningsAsErrors\|WarningsAsErrors" --glob '*.csproj' --glob '*.props'` | minor |
| A7 | Central package management or consistent versions | The same package pinned to three different versions across projects | `rg -o "Include=\"[^\"]+\" Version=\"[^\"]+\"" --glob '*.csproj' \| sort -u` | minor |
| A8 | SDK pinned for reproducible builds | No `global.json` on a multi-TFM or CI-built repo | `ls global.json` | nit |
| A9 | No up-level API on a down-level TFM | `Activity.AddException` **[net9+]**, or a net10-only API, compiled into a net8 project | `rg -n "AddException\(" --glob '*.cs'` + the detected TFM | blocker |

---

## B — Pattern application
*Owning skills: `pattern-guide`, `pattern-writer`, `code-review`, `backend/_shared/pattern-guide`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| B1 | One pattern per problem — no stacking | Repository + Unit-of-Work + Specification + Mediator + Decorator on one CRUD slice | Read one slice end-to-end; `rg -l "IRepository\|ISpecification\|IUnitOfWork\|IRequestHandler" --glob '*.cs'` and look for overlap | major |
| B2 | Repository earns its keep | `IFooRepository` mirroring `DbSet<Foo>` 1:1 with `Get/Add/Update/Delete` — the `DbSet` again with extra cost | `rg -n "interface I\w+Repository" -A12 --glob '*.cs'` | major |
| B3 | CQRS/MediatR justified by real read/write asymmetry | MediatR on a slice whose handler is `_db.Add(x); await _db.SaveChangesAsync();` | `rg -l "IRequestHandler" --glob '*.cs'` then read the thinnest handlers | major |
| B4 | Strategy / Factory replace repeated `switch` chains | `switch (type)` or `if (provider == "stripe") … else if …` selecting behaviour, repeated across the codebase | `rg -n "switch \(\w+\.?\w*(Type\|Kind\|Mode\|Provider)" --glob '*.cs'` | major |
| B5 | Decorators have one responsibility | `LoggingAndRetryDecorator` / one class doing logging + retry + caching | `rg -n "class \w*(Decorator\|Decorated)" --glob '*.cs'` | major |
| B6 | Cross-cutting concerns in one place (pipeline behaviors) | Validation, logging, and metrics duplicated in every handler | `rg -n "IPipelineBehavior" --glob '*.cs'` vs handler count | major |
| B7 | No interface with one implementation forever | `IFooService`/`FooService` pairs with no second implementation and no test double need | `rg -o "interface I\w+" --glob '*.cs'` cross-checked against implementations | minor |
| B8 | No abstract base class where composition fits | `public abstract class XBase` with exactly one subclass | `rg -n "abstract class" --glob '*.cs'` | minor |
| B9 | No god service | `IOrderService` with 20+ methods spanning several bounded contexts | `rg -c "public (async )?Task" --glob '*Service.cs' \| sort -t: -k2 -rn \| head` | major |
| B10 | Pattern choice is recorded where non-obvious | CQRS/Mediator/Decorator adopted with no ADR/comment stating why | `ls docs/adr docs/decisions 2>/dev/null`; read the slice | nit |

---

## C — Dependency injection & composition
*Owning skills: `pattern-writer`, `code-review`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| C1 | Constructor injection only | Property/field injection with no constructor source; `[Inject]`-style setters | `rg -n "public \w+ \w+ \{ get; set; \}" --glob '*Service.cs'` + read ctors | major |
| C2 | No service locator in business code | `IServiceProvider.GetService<T>()` / `GetRequiredService<T>()` inside a service or handler | `rg -n "GetRequiredService<\|GetService<" --glob '*.cs'` (registration + factories are fine) | major |
| C3 | Lifetimes match dependency lifetimes | **Singleton consuming Scoped** — the captured scope is wrong forever after (classic: singleton holding `DbContext`) | `rg -n "AddSingleton" -A2 --glob '*.cs'` then trace each singleton's ctor deps | blocker |
| C4 | One registration block per module | `services.Add*` calls sprinkled through `Program.cs` instead of `AddOrdersModule(...)` extensions | `rg -c "services\.Add" Program.cs` | minor |
| C5 | Decorator registration order is explicit and documented | Registration order inverted (real implementation outside the cache) or undocumented | `rg -n "Decorate\|Decorator" --glob '*.cs'` around registration | major |
| C6 | `IOptions<T>` over raw `IConfiguration` reads in business code | `_config["Section:Key"]` / `GetValue<string>` stringly-typed in a service | `rg -n "IConfiguration\b" --glob '*.cs'` outside `Program`/startup | major |
| C7 | The right `IOptions` flavour for the lifetime | Singleton holding `IOptions<T>` where config changes must be observed (`IOptionsMonitor`) | `rg -n "IOptions<\|IOptionsSnapshot<\|IOptionsMonitor<" --glob '*.cs'` | major |
| C8 | No dependency newed up inside a class | `new HttpClient()` / `new SmtpClient()` / `new FooService(...)` inside a consumer | `rg -n "new HttpClient\(\)\|new \w+Service\(" --glob '*.cs'` | major |
| C9 | Typed `HttpClient` via `IHttpClientFactory` | `static readonly HttpClient` hand-rolled, or a new client per call (socket exhaustion) | `rg -n "AddHttpClient\|new HttpClient" --glob '*.cs'` | major |
| C10 | Registrations are testable / verifiable | No composition-root test and a container that only fails at first request | `rg -rln "BuildServiceProvider" --glob '*.cs'` and test project presence | minor |

---

## D — Async & concurrency
*Owning skill: `code-review`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| D1 | No sync-over-async | `.Result`, `.Wait()`, `.GetAwaiter().GetResult()` in production code | `rg -n "\.Result\b\|\.Wait\(\)\|GetAwaiter\(\)\.GetResult\(\)" --glob '*.cs'` | blocker |
| D2 | No `async void` outside event handlers | `public async void HandleX(...)` — exceptions escape the caller and crash the process | `rg -n "async void" --glob '*.cs'` | blocker |
| D3 | `CancellationToken` threaded through every async method | `Task DoAsync()` with no token, or a token accepted and then not passed down | `rg -n "(async )?Task(<[^>]+>)? \w+Async\(" --glob '*.cs'` and read the signatures | major |
| D4 | No `Task.Run` to "make it async" | `await Task.Run(() => SyncWork())` around I/O that was already async | `rg -n "Task\.Run\(" --glob '*.cs'` | major |
| D5 | No fire-and-forget without a failure path | `_ = DoAsync();` / an unawaited call with no continuation, logging, or channel | `rg -n "^\s*_ = \w+Async\(\|(?<!await )\w+Async\([^)]*\);$" --glob '*.cs'` | major |
| D6 | No `.ConfigureAwait` confusion / no sync blocking in a lock | `lock` around awaited work; `SemaphoreSlim.Wait()` in async code | `rg -n "lock \(" -A6 --glob '*.cs' \| rg "await"`; `rg -n "\.Wait\(\)" --glob '*.cs'` | major |
| D7 | No `*Sync` method returning `Task` (or the inverse) | `public Task DoSync()` — the name lies about the contract | `rg -n "Task\b[^;]*\bSync\(" --glob '*.cs'` | major |
| D8 | Background work uses `IHostedService` / `BackgroundService` | A `Thread`/`Timer` started in a constructor or controller | `rg -n "new Thread\(\|new Timer\(" --glob '*.cs'` | major |
| D9 | Concurrent collections where shared state is genuinely concurrent | `Dictionary`/`List` mutated from multiple requests (see also E1) | `rg -n "static.*Dictionary<\|static.*List<" --glob '*.cs'` | blocker |
| D10 | `IAsyncEnumerable` / streaming for large result sets | A whole table materialized into a `List<T>` and returned | `rg -n "ToListAsync\(\)" --glob '*.cs'` on unbounded queries | minor |

---

## E — State & immutability
*Owning skills: `code-review`, `backend/_shared/pattern-guide`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| E1 | No static mutable state | `private static List<Foo> _cache = new();` — shared across requests, unsynchronized | `rg -n "static (?!readonly\|const)\w" --glob '*.cs'` | blocker |
| E2 | Constants are `const` / `static readonly` | A mutable `static` field used as if it were a constant | same as E1 | major |
| E3 | DTOs and value objects are immutable | `class Order { public List<Line> Lines { get; set; } }` — mutable collection exposed | `rg -n "public List<\w+> \w+ \{ get; set; \}" --glob '*.cs'` | major |
| E4 | `record` for value-shaped data | A mutable `class` with init-only props pretending to be a value type | `rg -n "public class \w+Dto\|public class \w+Request\|public class \w+Response" --glob '*.cs'` | minor |
| E5 | Read-only surfaces return read-only types | `List<T>` returned where callers must not mutate | `rg -n "public (List\|\w+\[\]) \w+" --glob '*.cs'` | minor |
| E6 | `sealed` by default on concrete classes | Public concrete class, no `sealed`, no real subclass | `rg -n "public class " --glob '*.cs'` vs `rg -c "public sealed class"` | minor |
| E7 | No `!` null-forgiving to silence the compiler | `x!.Foo` instead of a guard, `?.`, or a real fix | `rg -n "\w!\.\|\w!\)" --glob '*.cs'` | major |
| E8 | Domain invariants enforced in the type, not by convention | Public setters allowing an invalid aggregate; no factory/guard | Read 2–3 aggregates | major |

---

## F — Layering & boundaries
*Owning skills: `code-review`, `backend/_shared/code-review`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| F1 | Domain has no infrastructure dependencies | `Domain/` project referencing `Microsoft.EntityFrameworkCore`, `HttpClient`, or a cloud SDK | `rg -n "PackageReference\|ProjectReference" Domain*/**/*.csproj` | major |
| F2 | Controllers/endpoints don't touch the `DbContext` | `AppDbContext` injected into a controller and queried inline | `rg -n "DbContext" --glob '*Controller.cs' --glob '*Endpoints.cs'` | major |
| F3 | Persistence types don't cross the API boundary | EF entities returned from an endpoint (lazy-load surprises, over-posting, coupling) | `rg -n "ActionResult<\w+>\|Results\.Ok\(" --glob '*Controller*.cs' --glob '*Endpoints*.cs'` then check the returned type | major |
| F4 | Application code doesn't `new` infrastructure types | `new SqlConnection(...)` / `new BlobServiceClient(...)` in a handler | `rg -n "new (Sql\|Npgsql\|Blob\|Queue\|S3)\w*Client\?*\(" --glob '*.cs'` | major |
| F5 | Cross-feature access goes through public contracts | Feature A reaching into Feature B's `Internal/` namespace | `rg -n "using .*\.Internal" --glob '*.cs'` | major |
| F6 | Infrastructure implements application-owned interfaces | The application project referencing the infrastructure project (dependency inverted the wrong way) | Read `ProjectReference` graph | major |
| F7 | One mapping seam, not scattered manual mapping | The same entity→DTO projection hand-written in six places | `rg -n "new \w+Dto\(" --glob '*.cs' \| sort \| uniq -c \| sort -rn \| head` | minor |
| F8 | `internal` by default for implementations | Everything `public` in an assembly with a small real contract surface | `rg -c "public (sealed )?class" --glob '*.cs'` vs `internal` | nit |

---

## G — Persistence (EF Core mechanics)
*Owning skill: `database-code` · deeper schema/index work → **peer** `data-architect`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| G1 | `DbContext` is Scoped, one per bounded context | Registered Singleton, or one god-context for the whole system | `rg -n "AddDbContext\|AddDbContextPool" -A3 --glob '*.cs'` | blocker |
| G2 | `DbContext` never shared across threads/tasks | The same context used in `Task.WhenAll` branches | `rg -n "Task\.WhenAll" -B8 --glob '*.cs'` and check for context reuse | blocker |
| G3 | Lazy loading is off | `UseLazyLoadingProxies()`, or `virtual` navigations + the proxies package | `rg -n "UseLazyLoadingProxies\|Proxies" --glob '*.cs' --glob '*.csproj'` | major |
| G4 | `AsNoTracking()` on read paths | Read queries hydrating tracked entities for no reason | `rg -c "AsNoTracking" --glob '*.cs'` vs read-query count | major |
| G5 | Projections instead of full-entity hydration | `ToListAsync()` of whole entities feeding a small DTO | `rg -n "Include\(" -A4 --glob '*.cs'` — `Include` + projection defeats the projection | major |
| G6 | No N+1 | A query in a `foreach` over a parent collection; a navigation walked after a projection | `rg -n "foreach" -A6 --glob '*.cs' \| rg "await .*(Async\(\)\|LoadAsync)"` | major |
| G7 | No client-side evaluation of filters | `ToList()`/`ToListAsync()` *before* `Where(...)` — pulls the table into memory | `rg -n "ToListAsync\(\)\s*\)?\s*\.\s*Where\|ToList\(\)\.Where" --glob '*.cs'` | major |
| G8 | Optimistic concurrency on shared-write aggregates | No `[Timestamp]`/`rowversion` (SQL Server) or `xmin` token (Npgsql) on aggregates several actors write | `rg -n "Timestamp\]\|IsRowVersion\|UseXminAsConcurrencyToken\|IsConcurrencyToken" --glob '*.cs'` | major |
| G9 | Concurrency token matches the provider | `[Timestamp] byte[]` mapped to Postgres `xmin` (Npgsql maps `xmin` as `uint`, not `byte[]`) — internally contradictory | Read the entity + its `IEntityTypeConfiguration` together | blocker |
| G10 | `IEntityTypeConfiguration<T>` per entity | Inline `modelBuilder.Entity<T>(...)` blocks accumulating in `OnModelCreating` | `rg -c "modelBuilder.Entity<" --glob '*Context.cs'` | minor |
| G11 | Migrations under source control, applied from the pipeline | `Database.Migrate()` / `EnsureCreated()` at app startup | `rg -n "Database\.Migrate\(\)\|EnsureCreated\(\)" --glob '*.cs'` | major |
| G12 | One migration tool | EF migrations + DbUp/Flyway in the same project | `ls **/Migrations 2>/dev/null`; `rg -n "DbUp\|Flyway\|FluentMigrator" --glob '*.csproj'` | major |
| G13 | No `SaveChanges` in a loop | `await _db.SaveChangesAsync()` inside `foreach` | `rg -n "foreach" -A8 --glob '*.cs' \| rg "SaveChangesAsync"` | major |
| G14 | Bulk paths use set-based operations **[EFC8+]** | Load-modify-save loops where `ExecuteUpdateAsync`/`ExecuteDeleteAsync` fits | `rg -n "ExecuteUpdateAsync\|ExecuteDeleteAsync" --glob '*.cs'` vs bulk loops | minor |
| G15 | Raw SQL is parameterized | String concatenation/interpolation into `FromSqlRaw`/`ExecuteSqlRaw` with user input | `rg -n "FromSqlRaw\|ExecuteSqlRaw" --glob '*.cs'` | blocker |
| G16 | Transaction boundaries are explicit and minimal | Multi-aggregate writes with no transaction; or a transaction spanning an HTTP call | `rg -n "BeginTransactionAsync\|TransactionScope" --glob '*.cs'` | major |
| G17 | `Find`/`First` results are null-checked before mutation | `var x = await _db.Orders.FindAsync(id); x.Status = …` with no null guard | `rg -n "FindAsync\(\|FirstOrDefaultAsync\(" -A3 --glob '*.cs'` | major |
| G18 | Connection strings come from config/secret store | Literal connection string in `appsettings.json` or code | `rg -n "Server=\|Host=\|Data Source=" --glob '*.json' --glob '*.cs'` | blocker |

---

## H — API contract & validation
*Owning skills: `pattern-writer`, `code-review`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| H1 | Input validated at the boundary | A request DTO reaching domain logic with no FluentValidation validator / DataAnnotations / minimal-API filter | `rg -l "AbstractValidator<" --glob '*.cs'` vs request-DTO count | major |
| H2 | Errors are `ProblemDetails` (RFC 7807) | Ad-hoc `{ error: "..." }` shapes, or plain strings, per endpoint | `rg -n "ProblemDetails\|AddProblemDetails" --glob '*.cs'` | major |
| H3 | Status codes are honest | 200 with an error payload; 500 for a validation failure; 404 vs 403 confusion | Read each endpoint's failure paths | major |
| H4 | No over-posting | The EF entity bound directly as the request body | `rg -n "\[FromBody\] \w+" --glob '*.cs'` — check the bound type isn't an entity | major |
| H5 | Collection endpoints are bounded | List endpoint with no pagination / no max page size | `rg -n "IEnumerable<\|List<" --glob '*Controller*.cs' --glob '*Endpoints*.cs'` | major |
| H6 | Retryable writes are idempotent | POST/PUT with no idempotency key or natural-key guard, exposed to client retries | Read the write endpoints | major |
| H7 | The contract is documented and versioned | No OpenAPI/Swagger, or a breaking change shipped with no version segment | `rg -n "AddSwaggerGen\|AddOpenApi\|MapOpenApi" --glob '*.cs'` | minor |
| H8 | Long operations don't block the request thread | A 30-second job run inline in the request instead of queued | Read the slowest endpoints | major |
| H9 | Health endpoints exist and are anonymous | No `/health`, or health requiring auth (breaks probes) | `rg -n "AddHealthChecks\|MapHealthChecks" --glob '*.cs'` | minor |

---

## I — Service-side auth
*Owning skills: `auth0`, `cognito` (+ `auth/_shared/{auth0-concepts,oidc-concepts}`) · exploitability → **peer** `qa-security`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| I1 | JWT bearer validates issuer, audience, lifetime, signing key | `ValidateIssuer/ValidateAudience/ValidateLifetime = false`, or `SignatureValidator` short-circuited | `rg -n "TokenValidationParameters" -A12 --glob '*.cs'` | blocker |
| I2 | **Cognito lane:** `ValidateAudience = false` **plus** `token_use == "access"` and a `client_id` allow-list | Audience validated against a Cognito access token (no `aud` → always fails or mis-validates), or `token_use` never checked (an ID token replays as an access token) | `rg -n "token_use\|ValidateAudience" --glob '*.cs'` | blocker |
| I3 | RS256 only | `HS256`/symmetric key accepted | `rg -n "HS256\|SymmetricSecurityKey" --glob '*.cs'` | blocker |
| I4 | `RequireHttpsMetadata = true` outside local | Set `false` unconditionally | `rg -n "RequireHttpsMetadata" --glob '*.cs'` | major |
| I5 | Clock skew capped (~30s, not the 5-minute default) | `ClockSkew` untouched or widened to "fix" clock issues | `rg -n "ClockSkew" --glob '*.cs'` | minor |
| I6 | Authorization is policy-based, not string-branching | `if (user.IsInRole("admin"))` / permission strings compared inline in handlers | `rg -n "IsInRole\(\|HasClaim\(" --glob '*.cs'` | major |
| I7 | Every non-public endpoint carries an explicit policy | `[Authorize]` with no policy where a specific permission/scope is required; `[AllowAnonymous]` beyond health/metrics/discovery | `rg -n "\[Authorize\]\|\[AllowAnonymous\]\|RequireAuthorization" --glob '*.cs'` | major |
| I8 | Custom claims read via their full namespaced URI | Bare `tenant_id` lookup that silently returns null | `rg -n "FindFirst\(\"\|Claims.*==\s*\"" --glob '*.cs'` | major |
| I9 | M2M tokens cached with a safety margin | A client-credentials token fetched per outbound call | `rg -n "client_credentials\|GetTokenAsync" --glob '*.cs'` | major |
| I10 | Outbound auth via a `DelegatingHandler` on a typed client | Manual `Authorization` header construction in business code | `rg -n "Headers.Authorization\|Bearer " --glob '*.cs'` | minor |
| I11 | Client secrets only in a secret store | Secret in `appsettings*.json`, source, or a committed `.env` | `rg -ni "client_?secret" --glob '*.json' --glob '*.cs' --glob '*.yml'` | blocker |
| I12 | Tenant isolation enforced server-side | Tenant taken from a request field instead of the token claim | `rg -n "TenantId" --glob '*.cs'` — trace the source | blocker |

---

## J — Error handling & resilience
*Owning skill: `code-review`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| J1 | No swallowed exceptions | `catch (Exception) { }` / `catch { return default; }` — failure passes silently | `rg -n "catch\s*(\(\w+( \w+)?\))?\s*\{\s*\}" --glob '*.cs'`; `rg -n "catch" -A3 --glob '*.cs' \| rg "return (default\|null);"` | major |
| J2 | Specific exception types caught | `catch (Exception ex)` wrapping a block with three distinct failure modes | `rg -n "catch \(Exception" --glob '*.cs'` | major |
| J3 | No re-throw that loses the stack trace | `catch (Exception ex) { throw ex; }` | `rg -n "throw ex;" --glob '*.cs'` | major |
| J4 | One global exception handler maps to `ProblemDetails` | Try/catch repeated in every controller action | `rg -n "IExceptionHandler\|UseExceptionHandler\|ExceptionFilter" --glob '*.cs'` | major |
| J5 | Internals never leak in responses | `ex.Message`/`ex.ToString()`/stack trace returned to callers | `rg -n "ex\.Message\|ex\.ToString\(\)\|StackTrace" --glob '*.cs'` — check response paths | major |
| J6 | Outbound calls have timeouts | `HttpClient` with the default 100s and no per-request timeout | `rg -n "AddHttpClient" -A6 --glob '*.cs'` | major |
| J7 | Retry/circuit-breaker on remote dependencies (Polly / `AddStandardResilienceHandler`) | No resilience policy on a chatty downstream dependency | `rg -n "AddStandardResilienceHandler\|AddPolicyHandler\|Polly" --glob '*.cs' --glob '*.csproj'` | major |
| J8 | Retries only on idempotent operations | A blind retry policy wrapping a non-idempotent POST | `rg -n "Retry" -B4 --glob '*.cs'` | major |
| J9 | Exceptions aren't control flow | Expected validation failures thrown and caught as flow | Read validation paths | minor |
| J10 | Graceful shutdown honoured | `IHostApplicationLifetime`/token ignored by background work; in-flight work dropped | `rg -n "BackgroundService\|ExecuteAsync\(CancellationToken" -A10 --glob '*.cs'` | minor |

---

## K — Configuration & secrets
*Owning skills: `pattern-writer`, `code-review`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| K1 | No secrets in source or `appsettings*.json` | Connection strings with passwords, API keys, client secrets, tokens committed | `rg -ni "password=\|secret\|apikey\|api_key\|Bearer [A-Za-z0-9]" --glob '*.json' --glob '*.cs' --glob '*.yml'` | blocker |
| K2 | Secrets come from env vars + a secret store | The service reads a secret from a file checked into the repo | `rg -n "AddUserSecrets\|AddKeyVault\|AddSecretsManager\|GetEnvironmentVariable" --glob '*.cs'` | major |
| K3 | Typed options with validation | `IOptions<T>` registered without `ValidateDataAnnotations()`/`ValidateOnStart()`, so bad config fails at first use | `rg -n "AddOptions<\|Configure<" -A3 --glob '*.cs'` | major |
| K4 | Environment-specific config is layered, not branched in code | `if (env == "Production")` deciding behaviour inside services | `rg -n "IsProduction\(\)\|IsDevelopment\(\)" --glob '*.cs'` outside startup | minor |
| K5 | No hardcoded URLs / hosts / ports | Literal `https://api.internal…` in a service | `rg -n "https?://" --glob '*.cs'` | major |
| K6 | Feature toggles read through config, not recompiled constants | `const bool UseNewFlow = true` | `rg -n "const bool" --glob '*.cs'` | minor |
| K7 | Config keys are consistent and namespaced | Three spellings of the same section across projects | `rg -o "\"[A-Z]\w+:[A-Za-z:]+\"" --glob '*.cs' \| sort -u` | nit |

---

## L — Observability
*Owning skills (bundled in this plugin): `observability/opentelemetry-dotnet`, `observability/structured-logging-dotnet` · agent sibling: `observability-engineer-dotnet`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| L1 | The service emits telemetry at all | No OTel, no structured logging — only `Console.WriteLine` / default MEL console | `rg -n "OpenTelemetry\|Serilog" --glob '*.csproj'` | major |
| L2 | Structured logging uses **message templates**, never interpolation | `_logger.LogInformation($"Order {id} created")` — destroys the structured field | `rg -n "Log(Information\|Warning\|Error\|Debug\|Critical)\(\\$\"" --glob '*.cs'` | major |
| L3 | `ILogger<T>` injected; the static logger only in host setup | `Serilog.Log.Information(...)` in service code | `rg -n "Log\.(Information\|Error\|Warning)\(" --glob '*.cs'` | minor |
| L4 | Exceptions passed as the exception parameter | `_logger.LogError(ex.ToString())` — loses structure and stack | `rg -n "LogError\(ex\.ToString\|LogError\(\\$?\"" --glob '*.cs'` | major |
| L5 | **Bounded metric cardinality** — per-record ids are span attributes, never metric labels/tags | `order.id` / `user.id` / a trace id as a counter or histogram tag — explodes the series count | `rg -n "\.Add\(1,\|RecordHistogram\|Record\(" -A3 --glob '*.cs'`; `rg -n "new KeyValuePair<string, object" --glob '*.cs'` | blocker |
| L6 | **The Collector is the seam** — no exporter pointing straight at Tempo/Prometheus/Loki | `AddOtlpExporter` configured with a backend URL instead of the Collector; a Prometheus scrape endpoint standing in for the pipeline | `rg -n "AddOtlpExporter\|Endpoint = \|OTEL_EXPORTER_OTLP_ENDPOINT" --glob '*.cs' --glob '*.json' --glob '*.yml'` | major |
| L7 | One `ActivitySource`/`Meter` per subsystem, `static readonly`, reused | A new `ActivitySource` constructed per call or per request | `rg -n "new ActivitySource\(\|new Meter\(" --glob '*.cs'` | major |
| L8 | Span names are operation names, not data | `order.process.42` / a name built by interpolation | `rg -n "StartActivity\(\\$?\"" --glob '*.cs'` | major |
| L9 | Error spans are marked | Exception path with no `SetStatus(ActivityStatusCode.Error)` + `RecordException` (portable; `Activity.AddException` is **[net9+]**) | `rg -n "SetStatus\|RecordException" --glob '*.cs'` vs catch blocks | major |
| L10 | Logs correlate to traces | No `TraceId`/`SpanId` enricher, so a log line can't be pivoted to its trace | `rg -n "TraceId\|WithSpan\|Enrich.With" --glob '*.cs'` | major |
| L11 | Health/metrics/swagger excluded from instrumentation | `/health` dominating traces and sampling | `rg -n "Filter = \|FilterHttpRequestMessage\|RequestFilter" --glob '*.cs'` | minor |
| L12 | Sampling configured for production | `AlwaysOnSampler` in production | `rg -n "AlwaysOnSampler\|SetSampler\|TraceIdRatioBased" --glob '*.cs'` | major |
| L13 | Log levels sane; no PII/secrets in logs | `Debug`/`Verbose` as the production minimum; whole request DTOs, tokens, or card numbers logged | `rg -n "MinimumLevel\|\"Default\": \"Debug\"" --glob '*.cs' --glob '*.json'`; read the widest log calls | blocker |
| L14 | Loki labels stay low-cardinality | `order_id`/`user_id` configured as Loki **labels** rather than JSON fields | `rg -n "Labels\|labels:" --glob '*.json' --glob '*.yml'` | major |
| L15 | Trace context propagated across async boundaries | Queue/bus messages published with no `traceparent` injected — the trace breaks at the hop | `rg -n "Propagators\|Inject\(" --glob '*.cs'` vs publish sites | major |
| L16 | OTel package versions pinned as one train | Instrumentation packages at a different major than `OpenTelemetry` core | `rg -n "OpenTelemetry[^\"]*Version" --glob '*.csproj' --glob '*.props'` | minor |

---

## M — Testability & contract tests
*Owning skill: `code-review` · the tests themselves → **peer** `qa-api-dotnet` / `qa-dotnet-standards-audit`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| M1 | Every public API has a contract test | Endpoints with no test project reference at all | `ls **/*Tests.csproj`; compare endpoint list with test coverage | major |
| M2 | Seams are injectable/fakeable | `DateTime.Now`/`Guid.NewGuid()`/`Environment.*` called directly in logic — untestable time and identity | `rg -n "DateTime\.(Now\|UtcNow)\|Guid\.NewGuid\(\)" --glob '*.cs'` | major |
| M3 | No test-only hooks in production code | `if (env == "Test")` branches, `internal` back doors used only by tests without `InternalsVisibleTo` discipline | `rg -n "IsTest\|\"Test\"\|InternalsVisibleTo" --glob '*.cs' --glob '*.csproj'` | major |
| M4 | Business logic is reachable without HTTP | All logic inside controller actions, so nothing can be tested below the transport | Read 2–3 controllers | major |
| M5 | Static/sealed choices don't block test doubles | Sealed concrete with no interface where a test must substitute it | Cross-reference E6 findings with test needs | minor |
| M6 | Integration tests can run against a real dependency | No `WebApplicationFactory`/Testcontainers path — only mocks all the way down | `rg -n "WebApplicationFactory\|Testcontainers" --glob '*.cs' --glob '*.csproj'` | minor |

---

## N — Project structure & type safety
*Owning skills: `pattern-guide`, `pattern-writer`*

| # | Check | Violation looks like | Find it with | Sev |
|---|---|---|---|---|
| N1 | Consistent project topology | Half the solution layered, half vertical-slice, no stated convention | `ls **/*.csproj`; read the folder tree | minor |
| N2 | One type per file; namespace matches folder | Several public types in one file; namespace drift | `rg -c "^(public\|internal) (sealed )?(class\|record\|interface)" --glob '*.cs' \| rg -v ":1$"` | minor |
| N3 | No god file | A 1000-line service or `Program.cs` doing everything | `find . -name '*.cs' -not -path '*/obj/*' -exec wc -l {} + \| sort -rn \| head` | minor |
| N4 | Nullability honoured, not suppressed | `#nullable disable` sprinkled to quiet warnings | `rg -n "#nullable disable" --glob '*.cs'` | major |
| N5 | No `dynamic` / `object` where a type exists | `dynamic` in a contract or handler | `rg -n "\bdynamic\b" --glob '*.cs'` | major |
| N6 | Primary constructors / records used where they reduce noise **[net8+]** | Hand-rolled backing-field ctor boilerplate everywhere | `rg -n "private readonly \w+ _\w+;" --glob '*.cs'` | nit |
| N7 | No dead code / commented-out blocks shipped | Large commented-out regions, unused classes | `rg -n "^\s*//\s*(public\|private\|var\|await)" --glob '*.cs'` | nit |
| N8 | Analyzer/style config committed | No `.editorconfig`, so style is argued in review instead of enforced | `ls .editorconfig` | minor |

---

## Section index — for the report's applicability matrix

| Letter | Section | Conditional? |
|---|---|---|
| A | Build health, TFM & version lane | always |
| B | Pattern application | always (CQRS rows need MediatR) |
| C | Dependency injection & composition | always |
| D | Async & concurrency | always |
| E | State & immutability | always |
| F | Layering & boundaries | always |
| G | Persistence (EF Core mechanics) | EF Core present |
| H | API contract & validation | service exposes HTTP |
| I | Service-side auth | auth wiring present |
| J | Error handling & resilience | always |
| K | Configuration & secrets | always |
| L | Observability | always — **absence is L1**, not N/A |
| M | Testability & contract tests | always |
| N | Project structure & type safety | always |
