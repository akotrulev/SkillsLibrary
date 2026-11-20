# Authenticated scans and Allure reporting

## Authenticated scans

The baseline gate's sweet spot is the **unauthenticated** surface (headers, cookies, public pages). For
behind-login pages, baseline can take a ZAP **context** file (`-n context.context`) or pass auth options
through `-z`; full authenticated flows are really the **full scan's** job. If you do auth, inject any
credentials via **env vars read lazily** (`System.getenv`), never in the committed context file or
`cmd_options` (global rule: no secrets in code).

## Reporting the gate — ZAP report into Allure + CI artifact

`passive-scan.py` writes `report.json`/`.html`/`.xml` to the mounted work dir. Attach to Allure so a
failing run names the alerts without re-scanning (cross-link `qa-java:test-reports`):

```java
// support/ZapReportAttachment.java
import io.qameta.allure.Allure;
import io.qameta.allure.AttachmentOptions;
import java.io.ByteArrayInputStream;
import java.nio.file.Files;
import java.util.stream.Collectors;

public final class ZapReportAttachment {
    private ZapReportAttachment() {}

    public static void attach(ZapBaseline.ZapResult result) throws Exception {
        Allure.attachment("zap-report.html", "text/html",
            new ByteArrayInputStream(Files.readAllBytes(result.reportHtmlPath())),
            AttachmentOptions.withFileExtension("html"));
        String summary = result.alerts().stream()
            .map(a -> "[" + a.riskDesc() + "] " + a.alert() + " (rule " + a.pluginId() + ") x" + a.count())
            .collect(Collectors.joining("\n"));
        Allure.attachment("zap-alerts.txt", summary.isEmpty() ? "no alerts" : summary);
    }
}
```

- **Allure** — attach the HTML + a readable alert summary (rule id, risk, count).
- **CI artifact** — the Action's `artifact_name` upload, or upload the work dir (cross-link
  `qa-java:ci-pipelines`).
- **Tracking issue** — `allow_issue_writing: true` opens/updates a GitHub issue.
