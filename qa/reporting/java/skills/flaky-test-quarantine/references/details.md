# Deep-dive details — `qa-java:flaky-test-quarantine`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Examples

**End-to-end: a gate test (no retry) next to a known flaky one (quarantined and tracked).**

```java
public class PaymentFlowTests {

    @Test
    public void Should_AuthorizePayment_When_CardIsValid() {
        AuthResult result = gateway.authorize(Cards.valid().withAmount(1999).build());

        assertThat(result.status()).as(result.toString()).isEqualTo(AuthStatus.APPROVED);
    }

    @Test(groups = "flaky")
    @Flaky
    @Issue("PAY-1204")
    public void Should_MarkSettled_When_WebhookArrivesWithinSla() {
        String orderId = gateway.authorize(Cards.valid().build()).orderId();

        Settlement settlement = await().atMost(Duration.ofSeconds(10))
            .until(() -> ledger.settlementFor(orderId), s -> s.state() == SettlementState.SETTLED);

        assertThat(settlement.state()).isEqualTo(SettlementState.SETTLED);
    }
}
```

The first test runs on the gate and gets no retry: if a transient reddens it, Allure history shows it, and a
second occurrence earns it a ticket and the `flaky` group. The second races the gateway's settlement webhook;
it waits on the settlement condition (Awaitility, never a fixed sleep) and lives in quarantine under PAY-1204
until the race is fixed.

CI shape — two jobs, so the quarantine lane can never block the merge (cross-link `qa-java:ci-pipelines` for
the full workflow):

```yaml
gate:
  steps:
    - run: ./gradlew test --no-daemon

quarantine:
  continue-on-error: true
  steps:
    - run: ./gradlew flakyQuarantine --no-daemon
```

Both jobs upload their `build/allure-results/` on every run and, in a UI module, their
`build/playwright-artifacts/` on failure. The gate is green when the non-flaky tests pass; the quarantine lane's result is reported in Allure
(flaky-flagged, history-tracked) but **never** fails the pipeline.
