# Deep-dive details — `qa-dotnet:mobile-native-features`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## 4. Push notifications and backgrounding — assert state, never sleep through it (idea 4)

**App lifecycle.** Backgrounding and resuming is a real user behavior that breaks fragile apps (lost form state, re-auth loops). Drive it through `NativeFeatures`, then **wait on the restored screen**: a bounded `WebDriverWait` inside the page object, never a `Thread.Sleep` guessing how long the OS takes.

```csharp
[Test]
public void Should_PreserveCart_When_AppIsBackgroundedAndResumed()
{
    var cart = new CartPage(Driver);
    cart.AddItem("SKU-42");

    new NativeFeatures(Driver).BackgroundFor(TimeSpan.FromSeconds(3));

    cart.VerifyPageLoaded();
    Assert.That(cart.ItemCount(), Is.EqualTo(1), "cart items after a resume");
}
```

```csharp
[Test]
public void Should_RequireLogin_When_AppIsTerminatedAndRelaunched()
{
    var appId = Env.Required("APP_ID");
    var os = new NativeFeatures(Driver);

    os.Terminate(appId);
    Assert.That(os.StateOf(appId), Is.EqualTo(AppState.NotRunning), "app state after terminate");

    os.Activate(appId);
    new LoginPage(Driver).VerifyPageLoaded();
}
```

`TerminateApp` then `ActivateApp` is also the cold start between tests; the removed `ResetApp` and `CloseApp` have no replacement beyond it and `mobile: clearApp`.

**Push notifications.** Open the OS notification surface, not your app's UI, assert the notification, then tap it and assert the deep-linked screen (this composes with idea 2's routing assertion).

```csharp
[Test]
public void Should_OpenMessage_When_PushIsTapped()
{
    new NativeFeatures(Driver).OpenAndroidNotification("New message from");

    new MessageThreadPage(Driver).VerifyPageLoaded();
}
```

> **iOS push on the simulator** is simulated with `mobile: pushNotification` (it wraps `simctl push`) carrying an APNs payload: `bundleId` and a `payload` map with an `aps` block. Then open **Notification Center** and tap it. Asserting the *server actually sent* a push is a backend concern (your push provider's sandbox), not Appium's; this skill asserts the **app's reaction**, the same boundary as `qa/dotnet/skills/network-mocking/*` for requests.
