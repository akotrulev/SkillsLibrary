import { expect, test } from '../fixtures';

test.describe('Smoke', { tag: '@smoke' }, () => {
  test('Should_GreetUser_When_SignedInUserOpensHome', async ({ homePage, testUser }) => {
    await homePage.goto();

    await expect(homePage.greeting, `greeting for ${testUser.email}`).toHaveText(`Welcome, ${testUser.email}`);
  });
});
