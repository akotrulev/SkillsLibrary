# Deep-dive details — `qa-mobile-native-features-typescript`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## 4. Push notifications + backgrounding / resume — assert state, never sleep through it (idea #4)

**App lifecycle.** Backgrounding and resuming is a real user behavior that breaks fragile apps (lost form state,
re-auth loops). Drive it with the device command, then **wait on the restored screen** — `waitForDisplayed`, never
`browser.pause` guessing how long the OS takes.

```ts
it("preserves the cart when the app is backgrounded and resumed", async () => {
  const cart = new CartPage();
  await cart.addItem("SKU-42");
  await expect(cart.itemCount()).toHaveText("1");

  const os = new NativeFeatures();
  await os.backgroundFor(3);            // home → wait → return to foreground

  await cart.verifyPageLoaded();        // explicit wait on the restored screen (no pause)
  await expect(cart.itemCount()).toHaveText("1"); // STATE survived the lifecycle event
});
```

```ts
// Cold relaunch: terminate then activate; queryAppState confirms the transition deterministically
it("requires login when the app is terminated and relaunched", async () => {
  const bundle = process.env.APP_BUNDLE_ID!;
  const os = new NativeFeatures();

  await os.terminate(bundle);
  await expect(await driver.queryAppState(bundle)).toBe(1); // 1 = not running

  await os.activate(bundle);            // cold start
  const login = new LoginPage();
  await login.verifyPageLoaded();       // session did NOT survive a cold start — by design
});
```

**Push notifications.** Open the OS notification surface — *not* your app's UI — assert the notification, then tap
it and assert the deep-linked screen (this composes with idea #2's routing assertion).

```ts
// Android: open the notification shade via the driver, assert + tap the notification
it("opens the message thread when the push is tapped", async () => {
  await driver.openNotifications();

  const push = $('android=new UiSelector().textContains("New message from")');
  await push.waitForDisplayed({ timeout: 10_000 });
  await push.click();

  await new MessageThreadPage().verifyPageLoaded(); // the push routed into the right screen
});
```

> **iOS push on the simulator** is simulated with `mobile: pushNotification` (wraps `simctl push`) carrying an APNs
> payload; then open **Notification Center** and tap it. Asserting the *server actually sent* a push is a backend
> concern (your push provider's sandbox), not Appium's — this skill asserts the **app's reaction** to a push, the
> same boundary as `qa/typescript/skills/network-monitoring/*` for requests.

---
