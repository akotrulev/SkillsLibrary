import { randomUUID } from 'node:crypto';
import { test as base, expect } from '@playwright/test';
import { HomePage } from './HomePage';
import { type Credentials, LoginPage } from './LoginPage';

export const authFile = 'playwright/.auth/user.json';

export type SeededUser = Credentials & { readonly id: string };

type Fixtures = {
  loginPage: LoginPage;
  homePage: HomePage;
  testUser: Credentials;
  seededUser: SeededUser;
};

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (value === undefined) {
    throw new Error(`Environment variable ${name} is not set`);
  }
  return value;
}

export const test = base.extend<Fixtures>({
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page));
  },
  homePage: async ({ page }, use) => {
    await use(new HomePage(page));
  },
  testUser: async ({}, use) => {
    await use({ email: requiredEnv('E2E_USER'), password: requiredEnv('E2E_PASSWORD') });
  },
  seededUser: async ({ request }, use) => {
    const draft: Credentials = { email: `qa.${randomUUID()}@example.test`, password: randomUUID() };
    const created = await request.post('/api/users', { data: draft });
    expect(created.status(), await created.text()).toBe(201);
    const body: { id: string } = await created.json();

    await use({ ...draft, id: body.id });

    const deleted = await request.delete(`/api/users/${body.id}`);
    expect(deleted.status(), await deleted.text()).toBe(204);
  },
});

export { expect };
