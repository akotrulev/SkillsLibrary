# Android — Coverage with Kover

*Deep dive for [`mobile-android:unit-testing`](../SKILL.md) *Coverage floor*. Samples have no inline comments (CLAUDE.md § Comments).*

---

## Setup

Once per module, in `app/build.gradle.kts`; the plugin is the `kover` alias in `libs.versions.toml`.

```kotlin
import kotlinx.kover.gradle.plugin.dsl.CoverageUnit
import kotlinx.kover.gradle.plugin.dsl.GroupingEntityType

plugins { alias(libs.plugins.kover) }

kover {
    reports {
        filters { excludes { androidGeneratedClasses() } }
        variant("debug") {
            log {
                groupBy = GroupingEntityType.CLASS
                coverageUnits = CoverageUnit.BRANCH
                format = "<entity> branch coverage: <value>%"
            }
        }
    }
}
```

## Read the number

```bash
./gradlew :app:koverLogDebug | grep -E 'CheckoutViewModel|CartMapper'
```

One line per class is the number; `:app:koverHtmlReportDebug` shows the branches per function. Kover counts Kotlin's inline functions and coroutine state machines more faithfully than raw JaCoCo, which is why it is this lane's tool.
