package com.example.uitests.tests;

import com.example.uitests.pages.HomePage;
import com.example.uitests.pages.LoginPage;
import com.example.uitests.pages.LoginPage.Credentials;
import com.example.uitests.support.BaseTest;
import io.qameta.allure.Feature;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import static com.microsoft.playwright.assertions.PlaywrightAssertions.assertThat;

@Feature("Login")
public class LoginTest extends BaseTest {
    private LoginPage loginPage;
    private HomePage homePage;
    private Credentials user;

    @BeforeMethod(alwaysRun = true)
    public void createPages() {
        loginPage = new LoginPage(page);
        homePage = new HomePage(page);
        user = new Credentials(requiredEnv("E2E_USER"), requiredEnv("E2E_PASSWORD"));
    }

    @Test(groups = {"login", "smoke"})
    public void Should_GreetUser_When_CredentialsAreValid() {
        loginPage.signIn(user);

        assertThat(homePage.greeting()).hasText("Welcome, " + user.email());
    }

    @Test(groups = {"login", "regression"})
    public void Should_ShowInvalidCredentialsError_When_PasswordIsWrong() {
        loginPage.signIn(new Credentials(user.email(), user.password() + "-wrong"));

        assertThat(loginPage.error()).hasText("Invalid email or password");
    }
}
