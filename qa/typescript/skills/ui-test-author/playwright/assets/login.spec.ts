import { expect, test } from './fixtures';

test.describe('Login', { tag: '@smoke' }, () => {
  test.describe('signed out', () => {
    test.use({ storageState: { cookies: [], origins: [] } });

    test('Should_GreetUser_When_SeededUserSignsIn', async ({ loginPage, homePage, seededUser }) => {
      await loginPage.signIn(seededUser);

      await expect(homePage.greeting, `greeting for ${seededUser.email}`).toHaveText(`Welcome, ${seededUser.email}`);
    });

    test(
      'Should_ShowInvalidCredentialsError_When_PasswordIsWrong',
      { tag: '@regression' },
      async ({ loginPage, seededUser }) => {
        await loginPage.signIn({ email: seededUser.email, password: `${seededUser.password}-wrong` });

        await expect(loginPage.error, `sign-in error for ${seededUser.email}`).toHaveText('Invalid email or password');
      },
    );
  });

  test('Should_GreetUser_When_StoredSessionOpensHome', async ({ homePage, testUser }) => {
    await homePage.goto();

    await expect(homePage.greeting, `greeting for ${testUser.email}`).toHaveText(`Welcome, ${testUser.email}`);
  });
});
