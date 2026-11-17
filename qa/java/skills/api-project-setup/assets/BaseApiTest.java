package com.example.apitests.support;

import io.qameta.allure.Allure;
import io.qameta.allure.AttachmentOptions;
import org.testng.ITestResult;
import org.testng.annotations.AfterMethod;

public abstract class BaseApiTest {

    @AfterMethod(alwaysRun = true)
    public void linkTelemetryOnFailure(ITestResult result) {
        Object traceId = result.getAttribute(TestTrace.ATTRIBUTE);
        if (traceId == null || result.getStatus() != ITestResult.FAILURE) {
            return;
        }
        TelemetryLinks.uriList((String) traceId).ifPresent(links ->
                Allure.attachment("telemetry", "text/uri-list", links, AttachmentOptions.withFileExtension("uri")));
    }
}
