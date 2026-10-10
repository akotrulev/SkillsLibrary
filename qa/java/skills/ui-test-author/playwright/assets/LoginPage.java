package com.example.uitests.pages;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.options.AriaRole;

public final class LoginPage {
    private final Page page;
    private final SignInForm signInForm;
    private final Locator error;

    public LoginPage(Page page) {
        this.page = page;
        Locator form = page.getByTestId("Login.Form").describe("Sign-in form");
        this.signInForm = new SignInForm(form);
        this.error = form.locator(page.getByRole(AriaRole.ALERT)).describe("Sign-in error");
    }

    public void goTo() {
        page.navigate("/login");
    }

    public void signIn(Credentials credentials) {
        goTo();
        signInForm.submit(credentials);
    }

    public Locator error() {
        return error;
    }

    public record Credentials(String email, String password) {
    }

    public static final class SignInForm {
        private final Locator email;
        private final Locator password;
        private final Locator submit;

        public SignInForm(Locator root) {
            this.email = root.getByTestId("Login.Email");
            this.password = root.getByTestId("Login.Password");
            this.submit = root.getByTestId("Login.Submit");
        }

        public void submit(Credentials credentials) {
            email.fill(credentials.email());
            password.fill(credentials.password());
            submit.click();
        }
    }
}
