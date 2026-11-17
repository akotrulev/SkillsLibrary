import type { Locator, Page } from '@playwright/test';

export type Credentials = {
  readonly email: string;
  readonly password: string;
};

export class SignInForm {
  private readonly email: Locator;
  private readonly password: Locator;
  private readonly submit: Locator;

  constructor(root: Locator) {
    this.email = root.getByTestId('Login.Email');
    this.password = root.getByTestId('Login.Password');
    this.submit = root.getByTestId('Login.Submit');
  }

  async submitCredentials(credentials: Credentials): Promise<void> {
    await this.email.fill(credentials.email);
    await this.password.fill(credentials.password);
    await this.submit.click();
  }
}

export class LoginPage {
  readonly error: Locator;
  private readonly signInForm: SignInForm;

  constructor(private readonly page: Page) {
    const form = page.getByTestId('Login.Form').describe('Sign-in form');
    this.signInForm = new SignInForm(form);
    this.error = page.getByRole('alert').within(form).describe('Sign-in error');
  }

  async goto(): Promise<void> {
    await this.page.goto('/login');
  }

  async signIn(credentials: Credentials): Promise<void> {
    await this.goto();
    await this.signInForm.submitCredentials(credentials);
  }
}
