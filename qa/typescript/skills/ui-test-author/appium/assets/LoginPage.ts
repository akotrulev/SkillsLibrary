import { expect } from '@wdio/globals';
import { BasePage } from './BasePage.js';
import { OrdersPage } from './OrdersPage.js';

export class LoginPage extends BasePage {
  private static readonly EMAIL_ID = 'Login.Email';
  private static readonly PASSWORD_ID = 'Login.Password';
  private static readonly SUBMIT_ID = 'Login.Submit';

  private get email() {
    return this.byTestId(LoginPage.EMAIL_ID);
  }

  private get password() {
    return this.byTestId(LoginPage.PASSWORD_ID);
  }

  private get submit() {
    return this.byTestId(LoginPage.SUBMIT_ID);
  }

  async verifyPageLoaded(): Promise<void> {
    await expect(this.email).toBeDisplayed({ message: 'Expected LoginPage to be visible but the email field was not found' });
  }

  async signIn(email: string, password: string): Promise<OrdersPage> {
    await this.email.setValue(email);
    await this.password.setValue(password);
    await this.submit.click();
    return new OrdersPage();
  }
}
