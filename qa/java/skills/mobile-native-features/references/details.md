# Deep-dive details — `qa-mobile-native-features-java`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## 4. Push notifications + backgrounding / resume — assert state, never sleep through it (idea #4)

**App lifecycle.** Backgrounding and resuming is a real user behavior that breaks fragile apps (lost form state,
re-auth loops). Drive it with `InteractsWithApps`, then **wait on the restored screen** — a bounded
`WebDriverWait`, never a `Thread.sleep` guessing how long the OS takes.

```java
@Test
public void Should_preserve_cart_When_app_backgrounded_and_resumed() {
    CartPage cart = new CartPage(driver);
    cart.addItem("SKU-42");
    assertThat(cart.itemCount()).isEqualTo(1);

    NativeFeatures os = new NativeFeatures(driver);
    os.backgroundFor(java.time.Duration.ofSeconds(3));   // home → wait → return to foreground

    cart.verifyPageLoaded();                              // explicit wait on the restored screen (no sleep)
    assertThat(cart.itemCount()).isEqualTo(1);            // STATE survived the lifecycle event
}
```

```java
// Cold relaunch: terminate then activate; queryAppState confirms the transition deterministically
@Test
public void Should_require_login_When_app_terminated_and_relaunched() {
    String bundle = SystemPropertyUtil.getAppBundleId();
    NativeFeatures os = new NativeFeatures(driver);

    os.terminate(bundle);
    assertThat(((io.appium.java_client.InteractsWithApps) driver).queryAppState(bundle))
        .isEqualTo(io.appium.java_client.appmanagement.ApplicationState.NOT_RUNNING);

    os.activate(bundle);                                  // cold start
    LoginPage login = new LoginPage(driver);
    login.verifyPageLoaded();                             // session did NOT survive a cold start — by design
}
```

**Push notifications.** Open the OS notification surface — *not* your app's UI — assert the notification, then tap
it and assert the deep-linked screen (this composes with idea #2's routing assertion).

```java
// Android: open the notification shade via the driver, assert + tap the notification
@Test
public void Should_open_message_When_push_tapped() {
    ((io.appium.java_client.android.AndroidDriver) driver).openNotifications();

    org.openqa.selenium.WebElement push = new org.openqa.selenium.support.ui.WebDriverWait(
            driver, java.time.Duration.ofSeconds(10))
        .until(org.openqa.selenium.support.ui.ExpectedConditions.visibilityOfElementLocated(
            io.appium.java_client.AppiumBy.androidUIAutomator(
                "new UiSelector().textContains(\"New message from\")")));
    push.click();

    new MessageThreadPage(driver).verifyPageLoaded();     // the push routed into the right screen
}
```

> **iOS push on the simulator** is simulated with `mobile: pushNotification` (wraps `simctl push`) carrying an APNs
> payload; then open **Notification Center** and tap it. Asserting the *server actually sent* a push is a backend
> concern (your push provider's sandbox), not Appium's — this skill asserts the **app's reaction** to a push, the
> same boundary as `qa/java/skills/network-monitoring/*` for requests.

---
