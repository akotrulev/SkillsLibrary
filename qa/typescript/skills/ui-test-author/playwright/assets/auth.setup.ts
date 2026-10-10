import { authFile, expect, test as setup } from './fixtures';

setup('Should_StoreSignedInState_When_TestUserSignsIn', async ({ loginPage, homePage, testUser, context }) => {
  await loginPage.signIn(testUser);
  await expect(homePage.greeting).toBeVisible();
  await context.storageState({ path: authFile });
});
