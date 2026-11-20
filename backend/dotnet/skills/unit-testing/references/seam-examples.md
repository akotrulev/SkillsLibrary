# Seam examples — time and config

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
