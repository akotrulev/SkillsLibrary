using OpenQA.Selenium.Appium;
using OpenQA.Selenium.Interactions;

namespace AppiumTests.Support;

public static class GestureExtensions
{
    public static bool ScrollGesture(this AppiumDriver driver, AppiumElement container, string direction = "down", double percent = 0.75) =>
        driver.ExecuteScript("mobile: scrollGesture", new Dictionary<string, object>
        {
            ["elementId"] = container.Id,
            ["direction"] = direction,
            ["percent"] = percent,
        }) is true;

    public static void LongPress(this AppiumDriver driver, AppiumElement element, int durationMs = 1500) =>
        driver.ExecuteScript("mobile: longClickGesture", new Dictionary<string, object>
        {
            ["elementId"] = element.Id,
            ["duration"] = durationMs,
        });

    public static void Swipe(this AppiumDriver driver, int startX, int startY, int endX, int endY)
    {
        var finger = new PointerInputDevice(PointerKind.Touch, "finger");
        var swipe = new ActionSequence(finger);
        swipe.AddAction(finger.CreatePointerMove(CoordinateOrigin.Viewport, startX, startY, TimeSpan.Zero));
        swipe.AddAction(finger.CreatePointerDown(MouseButton.Touch));
        swipe.AddAction(finger.CreatePause(TimeSpan.FromMilliseconds(200)));
        swipe.AddAction(finger.CreatePointerMove(CoordinateOrigin.Viewport, endX, endY, TimeSpan.FromMilliseconds(600)));
        swipe.AddAction(finger.CreatePointerUp(MouseButton.Touch));
        driver.PerformActions(new List<ActionSequence> { swipe });
    }

    public static void Tap(this AppiumDriver driver, AppiumElement element)
    {
        var area = element.Rect;
        var finger = new PointerInputDevice(PointerKind.Touch, "finger");
        var tap = new ActionSequence(finger);
        tap.AddAction(finger.CreatePointerMove(CoordinateOrigin.Viewport, area.X + area.Width / 2, area.Y + area.Height / 2, TimeSpan.Zero));
        tap.AddAction(finger.CreatePointerDown(MouseButton.Touch));
        tap.AddAction(finger.CreatePointerUp(MouseButton.Touch));
        driver.PerformActions(new List<ActionSequence> { tap });
    }
}
