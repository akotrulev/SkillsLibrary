# Deep-dive details — `qa-mobile-native-features-dotnet`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## 4. Push notifications + backgrounding / resume — assert state, never sleep through it (idea #4)

**App lifecycle.** Backgrounding and resuming is a real user behavior that breaks fragile apps (lost form state,
re-auth loops). Drive it with the driver, then **wait on the restored screen** — a bounded `WebDriverWait`, never a
`Thread.Sleep` guessing how long the OS takes.

```csharp
[Test]
public void Should_PreserveCart_When_AppBackgroundedAndResumed()
{
    var cart = new CartPage(Driver);
    cart.AddItem("SKU-42");
    Assert.That(cart.ItemCount(), Is.EqualTo(1));

    var os = new NativeFeatures(Driver);
    os.BackgroundFor(TimeSpan.FromSeconds(3));   // home → wait → return to foreground

    cart.VerifyPageLoaded();                     // explicit wait on the restored screen (no sleep)
    Assert.That(cart.ItemCount(), Is.EqualTo(1));// STATE survived the lifecycle event
}
```

```csharp
// Cold relaunch: terminate then activate; GetAppState confirms the transition deterministically
[Test]
public void Should_RequireLogin_When_AppTerminatedAndRelaunched()
{
    var bundle = Env.AppBundleId;
    var os = new NativeFeatures(Driver);

    os.Terminate(bundle);
    Assert.That(Driver.GetAppState(bundle), Is.EqualTo(AppState.NotRunning));

    os.Activate(bundle);                         // cold start
    var login = new LoginPage(Driver);
    login.VerifyPageLoaded();                    // session did NOT survive a cold start — by design
}
```

**Push notifications.** Open the OS notification surface — *not* your app's UI — assert the notification, then tap
it and assert the deep-linked screen (this composes with idea #2's routing assertion).

```csharp
// Android: open the notification shade via the driver, assert + tap the notification
[Test]
public void Should_OpenMessage_When_PushTapped()
{
    ((AndroidDriver)Driver).OpenNotifications();

    var wait = new WebDriverWait(Driver, TimeSpan.FromSeconds(10));
    var push = wait.Until(d => d.FindElement(AppiumBy.AndroidUIAutomator(
        "new UiSelector().textContains(\"New message from\")")));
    push.Click();

    new MessageThreadPage(Driver).VerifyPageLoaded();     // the push routed into the right screen
}
```

> **iOS push on the simulator** is simulated with `mobile: pushNotification` (wraps `simctl push`) carrying an APNs
> payload; then open **Notification Center** and tap it. Asserting the *server actually sent* a push is a backend
> concern (your push provider's sandbox), not Appium's — this skill asserts the **app's reaction** to a push, the
> same boundary as `qa/dotnet/skills/network-monitoring/*` for requests.

---
