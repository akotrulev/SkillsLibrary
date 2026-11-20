# Seam examples — a fixed clock, validation without Spring

```java
private static final Instant NOW = Instant.parse("2026-08-09T12:00:00Z");
private final Clock clock = Clock.fixed(NOW, ZoneOffset.UTC);

@Test
void should_ReportExpired_when_ClockPassesExpiry() {
    var service = new SubscriptionService(Clock.offset(clock, Duration.ofDays(31)));
    assertThat(service.isExpired(new Subscription(NOW.plus(Duration.ofDays(30))))).isTrue();
}
```

```java
// Validation without Spring
try (var factory = Validation.buildDefaultValidatorFactory()) {
    var violations = factory.getValidator().validate(new CreateOrderRequest(null, 0));
    assertThat(violations).extracting(v -> v.getPropertyPath().toString())
                          .contains("customerId");
}
```
