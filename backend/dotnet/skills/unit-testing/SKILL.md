---
name: be-dotnet-unit-testing
description: Use when backend C# logic needs a dev-side unit test — NUnit 4 + NSubstitute + FakeTimeProvider: what deserves a test, test-project setup, the five seams that make logic untestable, fakes-over-mocks, parameterized cases, and async assertions. Runs in-process with no HTTP, no container, no real database. Triggers "unit-test this handler", "write tests for this domain service", "test this validator/calculator", "how do I fake the clock in a test", "my service isn't testable". Do NOT use for contract/integration tests through the transport (the `qa-api-dotnet` peer), for mutation scoring (`qa-test-quality-check-dotnet`), or for Blazor components (`fe-blazor-component-testing`).
---

# .NET — Unit Testing (NUnit 4 + NSubstitute)

Owns **dev-side unit tests of backend logic**: instantiate a class directly, drive it, assert on its return value or its observable effect on a fake collaborator. **In-process only — no HTTP, no container, no real database, no broker, no filesystem, no clock.**

**The boundary, one sentence:** if the test needs a `WebApplicationFactory`, a Testcontainer, or a live dependency, it is not a unit test and it belongs to the **peer** [`qa-api-dotnet`](../../../../qa/dotnet/agents/qa-api-dotnet.md).

**This skill is not a licence to replace integration tests with mocks.** `CLAUDE.md`'s standing preference for real-DB integration tests over mocks still governs the integration lane, which is the `qa-api-dotnet` peer's. Some things are only provable against a real dependency, and a unit test that fakes them proves nothing:

| Never unit-test this | Because | Belongs to |
|---|---|---|
| An EF Core `IQueryable` (LINQ→SQL translation, `Include`, split queries) | The in-memory provider translates differently from the real one — a green test over `UseInMemoryDatabase` is a false negative machine | `qa-api-dotnet` `db-testing/testcontainers` |
| A migration | Only a real engine proves it applies | `qa-api-dotnet` + `data-architect` |
| JWT bearer validation, JWKS, RBAC policy evaluation end-to-end | The middleware pipeline is the thing under test | `qa-api-dotnet` `test-login-tokens`, `qa-security` |
| Model binding, filters, middleware order, routing | Transport concerns | `qa-api-dotnet` |
| A raw SQL string's correctness | Only the engine can parse it | `qa-api-dotnet` `db-testing/verification-queries` |

## Version policy

**First act: detect `<TargetFramework>` in the target `.csproj`.** .NET **10 primary, 8/9 supported**. Everything here works unmodified on all three — `TimeProvider` and `FakeTimeProvider` are net8+, so the time seam below is available on every supported TFM. Never up-level a project to reach a testing API, and never flag a down-level project for lacking one. Match the test project's TFM to the project under test.

## When to use

- A class the `pattern-writer` skill just generated has behavior: a strategy, a resolver, a decorator, a pipeline step, a handler, a factory.
- A domain rule, invariant, or guard clause needs to be pinned before it's refactored.
- A calculation: money, rounding, proration, tax, totals, date math.
- A mapper / `Result<T,E>`-style branch / error-to-ProblemDetails translation.
- A validator (FluentValidation rules, custom validation attributes).
- Reproducing a bug at the unit level before fixing it (`ep-systematic-debugging`'s repro step, `ep-test-driven-development`'s RED).

## When NOT to use

- Contract / integration / E2E tests through the API → **peer** `qa-api-dotnet`
- Real-DB seed-assert-clean, Testcontainers → **peer** `qa-api-dotnet` (`db-testing/*`)
- Grading whether the tests actually catch faults (mutation score) → **peer** `qa-test-quality-check-dotnet` (Stryker.NET)
- Blazor components → `fe-blazor-component-testing` (bUnit)
- Test-suite *architecture* at scale — page objects, ObjectMother, shared fixtures across hundreds of tests → **peer** `qa-api-dotnet` + `qa-test-data-builder-dotnet`
- Auditing an existing suite → **peer** `qa-dotnet-standards-audit`
- **DTOs, records with no behavior, EF configurations, DI registration code, generated code** → don't test them at all (see below)

## Stack

Versions pinned once in `Directory.Packages.props` if the repo uses CPM (`PackageReference` without `Version`; a `Version` attribute under CPM triggers `NU1008`).

| Concern | Package | Version | Notes |
|---|---|---|---|
| Runner | `NUnit` | **4.3.2** | NUnit 4 — classic asserts moved to `NUnit.Framework.Legacy`; use the constraint model (`Assert.That`) |
| Adapter | `NUnit3TestAdapter` | **5.0.0** | Required for `dotnet test` discovery |
| Host | `Microsoft.NET.Test.Sdk` | **17.14.1** | |
| Doubles | `NSubstitute` | **6.0.0** | House default. Moq is fine **if the repo already uses it** — don't introduce a second doubles library |
| Doubles analyzers | `NSubstitute.Analyzers.CSharp` | **1.0.17** | Optional but recommended — catches substituting non-virtual members, the #1 silent NSubstitute failure |
| Time | `Microsoft.Extensions.TimeProvider.Testing` | **match the TFM major** (10.x / 9.x / 8.x) | `FakeTimeProvider` |

**Assertions: use NUnit's built-in constraint model.** Do **not** add FluentAssertions to a product repo without a licence review — v8 requires a paid licence for commercial use, which is why the QA suite deliberately pins 6.12.1. If the repo already references 6.12.x, match it; otherwise `Assert.That` + `Assert.Multiple` (the convention `pattern-writer` already emits).

## What deserves a unit test — the selection matrix

| Unit shape | Test it? | What to assert |
|---|---|---|
| Domain invariant / guard clause | **Yes** | Invalid input → the specific exception/`Result` error; valid input → accepted |
| Strategy implementation | **Yes** | Input → the algorithm's output, per strategy |
| Strategy resolver / keyed lookup | **Yes** | Key → correct implementation; unknown key → the defined failure, not `null` |
| Decorator | **Yes** | Inner called exactly once with the same args **and** the added behavior happened (retry count, cache hit, log-on-failure) |
| Handler / use-case orchestration | **Yes** | Collaborators called in the right way; the returned result; the failure branch |
| Calculation (money, rounding, proration, date math) | **Yes** | Boundary values, the rounding rule, the currency/minor-unit contract |
| Mapper / `Result` translation | **Yes** | Each branch maps to the right shape; unmapped input doesn't silently become a default |
| Validator (FluentValidation) | **Yes** | Rule fires on the invalid case; the error's property name and code |
| Pipeline behavior / middleware-shaped class | **Yes** (as a class, not via the pipeline) | `next` invoked or short-circuited per condition |
| Options/config **validation** | **Yes** | `IValidateOptions<T>` rejects the bad config |
| Record/DTO with no behavior | **No** | Nothing — testing a property setter is a tautology |
| EF `DbContext` / `IEntityTypeConfiguration` | **No** | Integration lane — `qa-api-dotnet` |
| DI registration | **No** (one composition-root smoke test at most, see conformance C10) | That the container resolves the root |
| Controller as pure transport (attribute + one delegating call) | **No** | If there is logic in the action, that's the defect — move it down |
| Anything requiring a real dependency | **No** | See the table at the top |

**The tautology test:** if deleting the assertion still leaves a passing test, delete the test.

## Project layout & setup

Match the repo's existing layout first. If there is none, a unit-test project per testable assembly, named after it:

```
src/Ordering.Application/            # under test
tests/Ordering.Application.Tests/    # this project
  Orders/
    PlaceOrderHandlerTests.cs
    PricingStrategyResolverTests.cs
  Fakes/
    FakeOrderRepository.cs           # hand-written, reusable
  Builders/
    OrderBuilder.cs
```

- **One test class per class under test**, mirroring the namespace. `<ClassName>Tests`.
- The test project's TFM matches the project under test; `<IsPackable>false</IsPackable>`, `<Nullable>enable</Nullable>` (the same nullable contract as production — a test project with nullable off hides the API's real shape).
- `[TestFixture]` is optional in NUnit 4 for a class with `[Test]` methods; be consistent with the repo.
- **No `InternalsVisibleTo` to reach private behavior.** If a test needs an internal, either the behavior belongs on the public surface or it's already covered through it. (Conformance **M3** flags test-only back doors.)
- **No shared mutable state across fixtures** — no `static` collections, no `[OneTimeSetUp]` mutating a field that tests write to. NUnit parallelizes; a shared field is an order-dependent flake.

## Naming

`Should_<Outcome>_When_<Condition>` or `Given_<Y>_When_<X>_Then_<Z>` (`CLAUDE.md`). The name states behavior, never implementation:

```csharp
// good
Should_RejectOrder_When_CartIsEmpty
Should_RoundHalfUp_When_TaxHasThirdDecimal
Given_ExpiredCard_When_Charging_Then_ReturnsPaymentDeclined

// bad
TestPlaceOrder            // says nothing
Should_CallRepository     // asserts a mechanism, not a behavior
PlaceOrder_Works
```

## The five seams — what makes logic untestable

This is the constructive half of conformance check **M2** (`standards-audit`: `DateTime.Now`/`Guid.NewGuid()`/`Environment.*` called directly in logic). If you cannot write the test without one of these, **fix the seam first** — don't reach for a static mocking tool.

| Seam | Untestable | Injectable | Fake it with |
|---|---|---|---|
| **Time** | `DateTime.UtcNow`, `DateTimeOffset.Now`, `Stopwatch` | `TimeProvider` (net8+) | `FakeTimeProvider` — `SetUtcNow`, `Advance` |
| **Identity** | `Guid.NewGuid()` | `IIdGenerator` (or pass the id in) | a stub returning a fixed sequence |
| **Randomness** | `Random.Shared`, `RandomNumberGenerator` | an injected abstraction | a deterministic stub |
| **Config / env** | `Environment.GetEnvironmentVariable`, `IConfiguration` reads in logic | `IOptions<T>` / the settings record | `Options.Create(new T { … })` |
| **Outbound I/O** | `new HttpClient()`, `File.*`, direct SMTP/SDK calls | a typed client interface owned by you | a hand-written fake, or a substitute of *your* interface |

```csharp
// Time
var clock = new FakeTimeProvider(new DateTimeOffset(2026, 8, 9, 12, 0, 0, TimeSpan.Zero));
var sut = new SubscriptionService(clock);
clock.Advance(TimeSpan.FromDays(31));
Assert.That(sut.IsExpired(subscription), Is.True);
```

```csharp
// Config
var options = Options.Create(new PricingOptions { MaxDiscountPercent = 20 });
var sut = new DiscountCalculator(options);
```

**Never substitute a type you don't own** — no `Substitute.For<HttpClient>()`, no substituting `DbContext`, `TimeProvider`, or an SDK client. Wrap it in your own interface and fake that. (`TimeProvider` is the exception that already ships its own fake — use `FakeTimeProvider`, not a substitute.)

## Test doubles

**Preference order: real object → hand-written fake → stub → substitute (mock).** Reach one step further only when the previous can't express the case.

| Use | When |
|---|---|
| **The real collaborator** | It's a pure value/calculator with no I/O — faking it hides real integration bugs between the two |
| **Hand-written fake** (an in-memory `IOrderRepository` backed by a `Dictionary`) | The collaborator is stateful and used by many tests. Cheaper and clearer than re-stubbing per test |
| **Stub** (`Substitute.For<T>()` + `Returns`) | You need to feed a value in and don't care how it was called |
| **Mock assertion** (`Received()`) | The *call itself* is the observable behavior — a message published, an email sent, an audit written |

```csharp
[Test]
public async Task Should_PublishOrderPlaced_When_OrderIsAccepted()
{
    var repository = Substitute.For<IOrderRepository>();
    var publisher = Substitute.For<IEventPublisher>();
    var clock = new FakeTimeProvider(FixedNow);
    var sut = new PlaceOrderHandler(repository, publisher, clock);

    var result = await sut.HandleAsync(new PlaceOrder(CustomerId, Items), CancellationToken.None);

    Assert.That(result.IsSuccess, Is.True);
    await publisher.Received(1).PublishAsync(
        Arg.Is<OrderPlaced>(e => e!.CustomerId == CustomerId),
        Arg.Any<CancellationToken>());
}
```

**Note the `e!` in the `Arg.Is` predicate.** `Arg.Is<T>` types its predicate as accepting a possibly-null `T`, so `e => e.CustomerId == …` raises **CS8602** in a nullable-enabled test project — and a warning fails this stack's 0-warning gate. Either null-forgive (`e!.`) or guard (`e => e != null && e.…`). Do **not** disable nullable in the test project to make it go away (see *Project layout* above).

**Prefer a state assertion over a call assertion** where both are possible: `Assert.That(fakeRepo.Saved, Has.Count.EqualTo(1))` survives a refactor that `Received(1).SaveAsync(...)` does not.

### NSubstitute traps

- **A non-virtual member on a concrete class silently returns `default`** — `Returns` appears to work and does nothing. Substitute **interfaces**, and install `NSubstitute.Analyzers.CSharp` so this fails at build.
- `Returns` on an async method: `Returns(Task.FromResult(value))` or `Returns(value)` both work; for throwing use `Returns<Task<T>>(_ => throw new …)` or `ThrowsAsync` from `NSubstitute.ExceptionExtensions`.
- `Received()` with no argument means "at least once" — say `Received(1)` when you mean exactly once, and `DidNotReceive()` for the negative.
- **Don't assert on `ILogger`** — logs are not the contract. The one exception is a class whose *sole* job is producing an audit/log record.
- Never `Substitute.For<ConcreteService>()` to stub one method while running the rest — that's a partial mock, and it means the class does two jobs. Split it.

## Parameterized tests

`CLAUDE.md` forbids `if`/`for` driving assertions. NUnit's data attributes are the escape hatch:

```csharp
[TestCase(0.005, 0.01)]      // half-up at the boundary
[TestCase(0.004, 0.00)]
[TestCase(-0.005, -0.01)]    // sign symmetry
public void Should_RoundHalfAwayFromZero_When_ThirdDecimalPresent(decimal input, decimal expected)
    => Assert.That(Money.Round(input), Is.EqualTo(expected));
```

`[TestCaseSource]` for cases that need construction, `[Values]`/`[Combinatorial]` for small matrices. **One boundary per case** — a 12-column `[TestCase]` row is a builder waiting to happen.

## Test data

- 1–3 fields: inline literals, named via local constants when the value carries meaning (`const string ExpiredCard = "4000000000000069";`).
- **4+ fields: a builder** (`CLAUDE.md`). Fluent, with sane defaults so each test overrides only what it's about — the overridden field *is* the test's subject, and the reader should see it in one line.

```csharp
var order = new OrderBuilder().WithStatus(OrderStatus.Shipped).Build();
```

- Suite-scale test data — ObjectMother, shared fixtures across many projects, DB seeding — is the **peer** `qa-test-data-builder-dotnet`'s lane.

## Async & concurrency

- Test methods return `Task`; never `async void`, never `.Result` / `.Wait()` / `.GetAwaiter().GetResult()` (the production rule applies to tests too).
- `Assert.ThatAsync` / `Assert.MultipleAsync` for async constraint groups; `Assert.ThrowsAsync<T>` for expected failures.
- **Assert on the exception's identity, not its message string** — a message is not a contract.
- **`CancellationToken` propagation is behavior worth a test** on anything long-running: pass a canceled token, assert `OperationCanceledException`.
- **No `Task.Delay` / `Thread.Sleep` in a test.** If a class needs time to pass, that's the `FakeTimeProvider` seam.

## Rules

- One logical assertion per test; group related ones in `Assert.Multiple` so all failures report at once.
- Arrange–Act–Assert, visibly separated. If Arrange needs 20 lines, the design is too coupled — that's a finding, not a fixture problem.
- Tests are independent and order-free: any test runs alone, in any order, in parallel.
- Fake at the boundary you own; the class under test is real and constructed directly (`new`, never resolved from a container).
- Every test the run generates must actually fail if the behavior breaks — verify RED at least once per new behavior (`ep-test-driven-development`).
- No conditional logic, no loops driving assertions, no `try/catch` standing in for `Assert.Throws`.
- No coverage-percentage gate here; whether the assertions are any good is measured by mutation score — **peer** `qa-test-quality-check-dotnet`.

## What NOT to do

- **`UseInMemoryDatabase` to "unit-test a repository"** — the top false-confidence pattern in .NET testing. Integration lane, real engine.
- **`WebApplicationFactory` / `Testcontainers` in this project** — that's the peer's suite; if it appears here, the fence has moved.
- **Substituting `DbContext`, `HttpClient`, `TimeProvider`, or an SDK type** — wrap it.
- **Asserting whole-object equality** on a record with 15 fields when the test is about one — assert the field, or the reader can't tell what broke.
- **`[Ignore]` without a linked issue** — a quarantined test is `qa-flaky-test-quarantine-dotnet`'s process, not a comment.
- **Testing the framework** — that `record` equality works, that FluentValidation validates, that MediatR dispatches.
- **A test per method** instead of per behavior — a 3-branch method needs 3+ tests; a 1-branch method may need 0.
- **Mirroring the implementation** so a behavior-preserving refactor breaks the suite. If it breaks, it was coupled to structure.
- **Reaching for `internal`/reflection** to test a private method — extract the concept into its own class instead.

## Generation steps

1. **Detect** the TFM, the existing test project (if any), its runner and doubles library — **the repo's existing choice wins** over this file's defaults.
2. **Identify the units** from the selection matrix — for each type the `pattern-writer` / `database-code` run just produced, decide test / no-test and say why for the no-tests.
3. **Fix the seams first** — if a unit reads the clock, a GUID, config, or does I/O directly, inject it (that's a `pattern-writer` edit, not a test edit) before writing the test.
4. **Write the failing test** (behavior name, AAA, one logical assertion), watch it fail for the right reason, then make it pass.
5. **Add the boundary cases** as `[TestCase]` rows — nulls, empties, min/max, the rounding boundary, the state that must be refused.
6. **Verify:** `dotnet test` green, `dotnet build` 0 warnings, `dotnet format --verify-no-changes`. Report the counts.
7. **Sweep:** any sibling of the same shape left untested? A strategy family with one tested member is a gap.

## Handoffs

- Contract / integration / E2E tests through the API → **peer** [`qa-api-dotnet`](../../../../qa/dotnet/agents/qa-api-dotnet.md)
- Real-DB verification, Testcontainers → **peer** `qa/dotnet/skills/db-testing/*`
- Do the tests actually catch faults? → **peer** `qa/dotnet/skills/test-quality-check` (Stryker.NET)
- Suite-scale builders / ObjectMother → **peer** `qa/dotnet/skills/test-data-builder`
- Flaky test triage / quarantine → **peer** `qa/reporting/dotnet/skills/flaky-test-quarantine`
- The red-green-refactor loop itself → [`ep-test-driven-development`](../../../../engineering-practices/test-driven-development/SKILL.md)
- The class under test needs a seam / a pattern → [`pattern-writer`](../pattern-writer/SKILL.md)
- Reviewing the tests with the change → [`code-review`](../code-review/SKILL.md)
- Whole-service conformance sweep (incl. §M testability) → [`standards-audit`](../standards-audit/SKILL.md)
- Java equivalent → `backend/java/skills/unit-testing` · TypeScript equivalent → `backend/node/skills/unit-testing`
