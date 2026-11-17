package com.example.apitests.tests.health;

import com.example.apitests.clients.HealthClient;
import com.example.apitests.models.health.HealthDto;
import com.example.apitests.support.BaseApiTest;
import io.qameta.allure.Feature;
import org.apache.http.HttpStatus;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import static org.assertj.core.api.Assertions.assertThat;

@Feature("Health")
public class HealthTest extends BaseApiTest {
    private HealthClient healthClient;

    @BeforeMethod(alwaysRun = true)
    public void createClient() {
        healthClient = new HealthClient("");
    }

    @Test(groups = "smoke")
    public void Should_ReportUp_When_ServiceIsRunning() {
        HealthDto health = healthClient.get(HttpStatus.SC_OK);

        assertThat(health.status()).as("health status").isEqualTo("UP");
    }
}
