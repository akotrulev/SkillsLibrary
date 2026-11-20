# JaCoCo — measuring branch coverage of the changed classes

```kotlin
// build.gradle.kts — once per project
plugins { jacoco }
tasks.jacocoTestReport {
    dependsOn(tasks.test)
    reports { csv.required = true }
}
```

```bash
./gradlew test jacocoTestReport
grep -E ',(PlaceOrderHandler|PricingStrategyResolver),' build/reports/jacoco/test/jacocoTestReport.csv
```

Branch coverage is `BRANCH_COVERED ÷ (BRANCH_COVERED + BRANCH_MISSED)` — the CSV's 7th and 6th columns — summed over the changed classes; for a method changed in an existing class, the class's page under `build/reports/jacoco/test/html/` shows its branches. On Maven, `jacoco-maven-plugin` (`prepare-agent` + `report`) writes the same CSV to `target/site/jacoco/jacoco.csv`.
