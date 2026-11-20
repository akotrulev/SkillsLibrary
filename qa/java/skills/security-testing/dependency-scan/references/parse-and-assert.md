# Parse-and-assert test

SCA is primarily a **build/CI gate** (`./gradlew dependencyCheckAnalyze`). When you want a test-level
assertion independent of the Gradle gate — e.g. a custom threshold, or to surface the count in your test
report — parse the JSON report (TestNG + AssertJ, mirroring `passive-scan`'s parsed-report gate):

```java
// src/test/java/security/DependencyCheckReport.java — a probe over the report
public record DependencyCheckReport(JsonNode root) {
    public static DependencyCheckReport read(Path path) throws IOException {
        return new DependencyCheckReport(new ObjectMapper().readTree(Files.readString(path)));
    }

    public List<String> findingsAtOrAbove(double minimumCvss) {
        List<String> findings = new ArrayList<>();
        for (JsonNode dep : root.path("dependencies")) {
            for (JsonNode vuln : dep.path("vulnerabilities")) {
                double cvss = vuln.path("cvssv3").path("baseScore").asDouble(
                        vuln.path("cvssv2").path("score").asDouble(0.0));
                if (cvss >= minimumCvss) findings.add(vuln.path("name").asText() + " in " + dep.path("fileName").asText());
            }
        }
        return findings;
    }
}

// src/test/java/security/DependencyVulnerabilityTest.java
public class DependencyVulnerabilityTest {
    @Test
    public void Should_have_no_high_severity_cves_When_dependencies_scanned() throws IOException {
        DependencyCheckReport report = DependencyCheckReport.read(Path.of("build", "reports", "dependency-check-report.json"));

        assertThat(report.findingsAtOrAbove(7.0)).as("High+ CVEs (CVSS >= 7.0) in the dependency tree").isEmpty();
    }
}
```

The `.NET`/TS siblings parse their own tool's JSON (`dotnet list package --vulnerable --format json` /
`npm audit --json`) the same way.
