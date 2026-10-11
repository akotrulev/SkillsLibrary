# Deep-dive details — `qa-java:mobile-native-features`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## 4. Push notifications and backgrounding — assert state, never sleep through it (idea 4)

**App lifecycle.** Backgrounding and resuming is a real user behavior that breaks fragile apps (lost form state, re-auth loops). Drive it through `NativeFeatures`, then **wait on the restored screen**: a bounded `WebDriverWait` inside the page object, never a `Thread.sleep` guessing how long the OS takes.

```java
@Test
public void Should_PreserveCart_When_AppIsBackgroundedAndResumed() {
    CartPage cart = new CartPage(driver);
    cart.addItem("SKU-42");

    new NativeFeatures(driver).backgroundFor(Duration.ofSeconds(3));

    cart.verifyPageLoaded();
    assertThat(cart.itemCount()).as("cart items after a resume").isEqualTo(1);
}
```

```java
@Test
public void Should_RequireLogin_When_AppIsTerminatedAndRelaunched() {
    String appId = Env.required("APP_ID");
    NativeFeatures os = new NativeFeatures(driver);

    os.terminate(appId);
    assertThat(os.appState(appId)).as("app state after terminate").isEqualTo(ApplicationState.NOT_RUNNING);

    os.activate(appId);
    new LoginPage(driver).verifyPageLoaded();
}
```

`terminateApp` then `activateApp` is also the cold start between tests; the removed `resetApp` and `closeApp` have no replacement beyond it and `mobile: clearApp`.

**Push notifications.** Open the OS notification surface, not your app's UI, assert the notification, then tap it and assert the deep-linked screen (this composes with idea 2's routing assertion).

```java
@Test
public void Should_OpenMessage_When_PushIsTapped() {
    new NativeFeatures(driver).openAndroidNotification("New message from");

    new MessageThreadPage(driver).verifyPageLoaded();
}
```

> **iOS push on the simulator** is simulated with `mobile: pushNotification` (it wraps `simctl push`) carrying an APNs payload: `bundleId` and a `payload` map with an `aps` block. Then open **Notification Center** and tap it. Asserting the *server actually sent* a push is a backend concern (your push provider's sandbox), not Appium's; this skill asserts the **app's reaction**, the same boundary as `qa/java/skills/network-mocking/*` for requests.
