# AWS Device Farm — the remote-run orchestrator (Java)

Device Farm is the **remote-run** paradigm: you do not drive a live device. You upload the app and a packaged test suite, schedule a run against a **device-pool ARN**, and poll for the result. Every step that waits for AWS is an **Awaitility condition poll**, never a `Thread.sleep`.

```java
package support.farm;

import software.amazon.awssdk.services.devicefarm.DeviceFarmClient;
import software.amazon.awssdk.services.devicefarm.model.CreateUploadResponse;
import software.amazon.awssdk.services.devicefarm.model.ExecutionResult;
import software.amazon.awssdk.services.devicefarm.model.ExecutionStatus;
import software.amazon.awssdk.services.devicefarm.model.ScheduleRunResponse;
import software.amazon.awssdk.services.devicefarm.model.TestType;
import software.amazon.awssdk.services.devicefarm.model.Upload;
import software.amazon.awssdk.services.devicefarm.model.UploadStatus;
import software.amazon.awssdk.services.devicefarm.model.UploadType;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

import static org.awaitility.Awaitility.await;

public final class DeviceFarmRunner {
    private static final int HTTP_OK = 200;

    private final DeviceFarmClient farm;
    private final HttpClient http;

    public DeviceFarmRunner(DeviceFarmClient farm, HttpClient http) {
        this.farm = farm;
        this.http = http;
    }

    public String uploadAndAwait(String projectArn, String name, UploadType type, byte[] bytes)
            throws IOException, InterruptedException {
        CreateUploadResponse created = farm.createUpload(r -> r.projectArn(projectArn).name(name).type(type));
        Upload upload = created.upload();
        putToPresignedUrl(upload.url(), name, bytes);

        await().atMost(Duration.ofMinutes(5)).pollInterval(Duration.ofSeconds(5)).until(() -> {
            UploadStatus status = farm.getUpload(g -> g.arn(upload.arn())).upload().status();
            if (status == UploadStatus.FAILED) {
                throw new IllegalStateException("Device Farm upload failed: " + name);
            }
            return status == UploadStatus.SUCCEEDED;
        });
        return upload.arn();
    }

    public ExecutionResult scheduleAndAwait(String projectArn, String appArn, String testPackageArn, String devicePoolArn) {
        ScheduleRunResponse scheduled = farm.scheduleRun(r -> r
                .projectArn(projectArn)
                .appArn(appArn)
                .devicePoolArn(devicePoolArn)
                .test(t -> t.type(TestType.APPIUM_JAVA_TESTNG).testPackageArn(testPackageArn)));
        String runArn = scheduled.run().arn();

        await().atMost(Duration.ofMinutes(30)).pollInterval(Duration.ofSeconds(15)).until(() ->
                farm.getRun(g -> g.arn(runArn)).run().status() == ExecutionStatus.COMPLETED);

        return farm.getRun(g -> g.arn(runArn)).run().result();
    }

    private void putToPresignedUrl(String url, String name, byte[] bytes) throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder(URI.create(url))
                .PUT(HttpRequest.BodyPublishers.ofByteArray(bytes))
                .build();
        HttpResponse<Void> response = http.send(request, HttpResponse.BodyHandlers.discarding());
        if (response.statusCode() != HTTP_OK) {
            throw new IllegalStateException("Device Farm upload of " + name + " answered HTTP " + response.statusCode());
        }
    }
}
```

- The upload is a plain HTTP `PUT` of the bytes to the presigned URL; any answer but `200` throws with the file name and status, so a failed upload never shows up later as a five-minute poll timeout.
- `uploadAndAwait` declares `IOException` and `InterruptedException` and catches neither: an interrupt must reach the caller. Awaitility's `ConditionTimeoutException` is the poll's own failure and carries the elapsed time.
- The test package type for a TestNG Appium suite is `APPIUM_JAVA_TESTNG_TEST_PACKAGE`, with an `APPIUM_JAVA_TESTNG_TEST_SPEC` YAML to control the run; the app type is `ANDROID_APP` or `IOS_APP`. The Appium server version a run uses comes from that test spec and the farm's host image, so read both before moving a suite to java-client 11 (see **Does the farm run Appium 3?** in `SKILL.md`).
- A **device pool** is created once (console or `createDevicePool` with a device-selection rule) and referenced by ARN.
- AWS auth is the **default credential provider chain**; in CI prefer **OIDC role assumption** over a long-lived key (`qa/cicd/java/skills/ci-pipelines`). Artifacts (logs, video, screenshots) are fetched per job with `listArtifacts(runArn)` after the run completes.
