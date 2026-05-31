using OpenQA.Selenium.Appium;
using OpenQA.Selenium.Interactions;

namespace AppiumTests;

/// <summary>
/// Reusable mobile gestures. Prefer the driver-native <c>mobile:</c> commands
/// (the driver computes geometry) and fall back to the W3C Actions API for
/// gestures that have no <c>mobile:</c> equivalent. The deprecated
/// <c>TouchAction</c> / <c>MultiAction</c> API is intentionally not used.
/// </summary>
public static class GestureExtensions
{
    // ── mobile: commands (UiAutomator2 / XCUITest) ───────────────────────────

    /// <summary>Scrolls a container by percent in a direction (Android UiAutomator2).</summary>
    public static void ScrollGesture(this AppiumDriver driver, AppiumElement container,
        string direction = "down", double percent = 3.0)
        => driver.ExecuteScript("mobile: scrollGesture", new Dictionary<string, object>
        {
            ["elementId"] = container.Id,
            ["direction"] = direction,
            ["percent"]   = percent,
        });

    /// <summary>Long-press an element for the given duration (Android UiAutomator2).</summary>
    public static void LongPress(this AppiumDriver driver, AppiumElement element, int durationMs = 1500)
        => driver.ExecuteScript("mobile: longClickGesture", new Dictionary<string, object>
        {
            ["elementId"] = element.Id,
            ["duration"]  = durationMs,
        });

    // ── W3C Actions (cross-platform, coordinate-based) ───────────────────────

    public static void Swipe(this AppiumDriver driver, int startX, int startY, int endX, int endY)
    {
        var finger = new PointerInputDevice(PointerKind.Touch, "finger");
        var seq = new ActionSequence(finger);
        seq.AddAction(finger.CreatePointerMove(CoordinateOrigin.Viewport, startX, startY, TimeSpan.Zero));
        seq.AddAction(finger.CreatePointerDown(MouseButton.Touch));
        seq.AddAction(finger.CreatePause(TimeSpan.FromMilliseconds(200)));
        seq.AddAction(finger.CreatePointerMove(CoordinateOrigin.Viewport, endX, endY, TimeSpan.FromMilliseconds(600)));
        seq.AddAction(finger.CreatePointerUp(MouseButton.Touch));
        driver.PerformActions(new List<ActionSequence> { seq });
    }

    public static void Tap(this AppiumDriver driver, AppiumElement element)
    {
        var cx = element.Location.X + element.Size.Width / 2;
        var cy = element.Location.Y + element.Size.Height / 2;
        var finger = new PointerInputDevice(PointerKind.Touch, "finger");
        var seq = new ActionSequence(finger);
        seq.AddAction(finger.CreatePointerMove(CoordinateOrigin.Viewport, cx, cy, TimeSpan.Zero));
        seq.AddAction(finger.CreatePointerDown(MouseButton.Touch));
        seq.AddAction(finger.CreatePointerUp(MouseButton.Touch));
        driver.PerformActions(new List<ActionSequence> { seq });
    }
}
