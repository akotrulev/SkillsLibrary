# Deep-dive details — `qa-flaky-test-quarantine-java`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Examples

**End-to-end: a transient on the gate (auto-retried once) vs a known flaky (quarantined + tracked).**

```java
public class PaymentFlowTests {

    // GATE test — normally deterministic. If a true transient (a cold-start 503) reddens it,
    // RetryAnalyzer (cap 1, applied suite-wide by RetryListener) gives it exactly one more shot.
    @Test
    public void shouldAuthorizePaymentWhenCardIsValid() {
        var result = gateway.authorize(Cards.valid().withAmount(1999).build());  // test-data-builder/java
        assertThat(result.status()).isEqualTo(AuthStatus.APPROVED);              // one logical assertion
    }

    // QUARANTINED test — known to race against the gateway's async settlement webhook.
    // Off the gate (group "flaky"), still run in the quarantine lane, flagged in Allure, ticketed.
    @Test(groups = "flaky")
    @Flaky
    @Issue("PAY-1204")
    public void shouldMarkSettledWhenWebhookArrivesWithinSla() {
        gateway.authorize(Cards.valid().build());
        // the de-flake (PAY-1204) is to wait on the settlement condition, not a fixed window — until then,
        // this lives in quarantine so it can't redden a clean PR.
        var settlement = await().atMost(Duration.ofSeconds(10))
            .until(() -> ledger.settlementFor(orderId), s -> s.state() == SettlementState.SETTLED);
        assertThat(settlement.state()).isEqualTo(SettlementState.SETTLED);
    }
}
```

CI shape (two lanes — cross-link `qa-ci-pipelines-java` for the full workflow):

```yaml
- name: Gate suite (blocks merge)
  run: ./gradlew test                       # testng-gate.xml — excludes "flaky", retry cap 1

- name: Quarantine lane (visibility only)
  if: always()
  run: ./gradlew flakyQuarantine            # testng-quarantine.xml — ignoreFailures, never blocks

- name: Upload Allure results               # both lanes write build/allure-results/
  if: always()
  uses: actions/upload-artifact@v4
  with: { name: allure-results, path: '**/build/allure-results/' }
```

The gate is green if the non-flaky tests pass (one retry absorbed any transient); the quarantine lane's
result is reported in Allure (flaky-flagged, history-tracked) but **never** fails the pipeline.
