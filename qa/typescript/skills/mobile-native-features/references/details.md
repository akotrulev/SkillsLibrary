# Deep-dive details — `qa-typescript:mobile-native-features`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## 4. Push notifications and backgrounding — assert state, never sleep through it (idea 4)

**App lifecycle.** Backgrounding and resuming breaks fragile apps (lost form state, re-auth loops). Drive it with the device command, then wait on the restored screen.

```ts
describe('Cart lifecycle', () => {
  it('Should_KeepCartItem_When_AppIsBackgroundedAndResumed', async () => {
    const cart = new CartPage();
    await cart.addItem('SKU-42');
    await new NativeFeatures().backgroundFor(3);

    await cart.verifyPageLoaded();

    await expect(cart.itemCount()).toHaveText('1');
  });

  it('Should_RequireLogin_When_AppIsTerminatedAndRelaunched', async () => {
    const os = new NativeFeatures();
    const appIdentifier = requiredEnv('APP_ID');

    await os.terminate(appIdentifier);
    expect({ appIdentifier, state: await os.appState(appIdentifier) }).toEqual({ appIdentifier, state: 1 });
    await os.activate(appIdentifier);

    await new LoginPage().verifyPageLoaded();
  });
});
```

`mobile: queryAppState` returns `1` for not running, `2` suspended, `3` background and `4` foreground, so the transition is asserted rather than waited out.

**Push notifications.** Open the OS notification surface, assert the notification, tap it, and assert the routed screen.

```ts
describe('Push', () => {
  it('Should_OpenMessageThread_When_PushIsTapped', async () => {
    const shade = new NotificationShade();
    await shade.open();

    await shade.tap('New message from');

    await new MessageThreadPage().verifyPageLoaded();
  });
});
```

```ts
import { $, browser } from '@wdio/globals';

export class NotificationShade {
  async open(): Promise<void> {
    await browser.openNotifications();
  }

  async tap(textFragment: string): Promise<void> {
    const notification = $(`android=new UiSelector().textContains("${textFragment}")`);
    await notification.waitForDisplayed({ timeout: 10_000 });
    await notification.click();
  }
}
```

The notification shade is not your app, so this is one of the few places a `UiSelector` is the practical query; `NotificationShade` keeps it narrow and out of the page objects. On the **iOS simulator**, `mobile: pushNotification { bundleId, payload: { aps: { alert: '…' } } }` delivers the payload, then open Notification Center and tap it. Asserting that the server sent a push is a provider concern, not Appium's; this skill asserts the app's reaction.
