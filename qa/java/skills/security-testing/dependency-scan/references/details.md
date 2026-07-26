# Deep-dive details — `qa-security-dependency-scan-java`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Examples

**End-to-end: a PR SCA gate that fails on a new High+ CVE, triages a not-yet-fixable transitive one with a
ticketed time-boxed suppression, and forces the fixable one.**

```kotlin
// build.gradle.kts
plugins { java; id("org.owasp.dependencycheck") version "10.0.4" }

dependencyCheck {
    failBuildOnCVSS = 7.0f
    failOnError = true
    suppressionFile = "config/dependency-check/suppressions.xml"
    formats = listOf("HTML", "JSON", "SARIF")
    nvd.apiKey = System.getenv("NVD_API_KEY")
}

dependencies {
    constraints {
        // Real fix: force the patched transitive version (the preferred response).
        implementation("com.fasterxml.jackson.core:jackson-databind:2.17.1") {
            because("CVE-2023-XXXX — force patched transitive jackson (JIRA-4209, fixed)")
        }
    }
}
```

Lifecycle for this gate:
1. A dev bumps a library; it pulls in a transitive `jackson-databind` with a **High** CVE.
2. The PR runs `dependencyCheckAnalyze`; CVSS 8.1 ≥ 7.0 → the task throws → **the build fails**, with the
   CVE in the uploaded HTML report and inline on the PR via SARIF.
3. The dev **forces** the patched `jackson-databind` version via a constraint (the real fix) → the scan
   passes. A *second*, currently-unfixable transitive CVE (upstream fix pending) is `<suppress>`ed with a
   JIRA ticket and `until="2026-09-01Z"` — tracked, time-boxed, not silently muted.
4. Dependabot later raises the parent bump that removes the suppressed CVE; the entry is deleted at its
   next review — the suppression file shrinks, never grows.
