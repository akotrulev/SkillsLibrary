using OpenQA.Selenium.Appium;
using OpenQA.Selenium.Appium.Android;
using OpenQA.Selenium.Appium.Enums;
using OpenQA.Selenium.Appium.iOS;

namespace AppiumTests;

/// <summary>
/// Single place that builds an <see cref="AppiumDriver"/> from a platform name.
/// Capabilities and the server URL come from <c>Env</c> (env vars / -p:Platform=),
/// never hardcoded. Tests and pages never instantiate a driver directly.
/// </summary>
public static class AppiumDriverFactory
{
    public static AppiumDriver Create(string platform)
    {
        var serverUri = new Uri(Env.AppiumServerUrl);
        var startup = TimeSpan.FromSeconds(180);

        return platform.ToLowerInvariant() switch
        {
            "android" => new AndroidDriver(serverUri, AndroidOptions(), startup),
            "ios"     => new IOSDriver(serverUri, IosOptions(), startup),
            _         => throw new ArgumentException($"Unknown platform: {platform}"),
        };
    }

    private static AppiumOptions AndroidOptions()
    {
        var options = new AppiumOptions
        {
            AutomationName = AutomationName.AndroidUIAutomator2,
            PlatformName   = "Android",
            DeviceName     = Env.DeviceName,
        };
        options.AddAdditionalAppiumOption("app", Env.AppPath);
        options.AddAdditionalAppiumOption("noReset", true);
        options.AddAdditionalAppiumOption("newCommandTimeout", 120);
        return options;
    }

    private static AppiumOptions IosOptions()
    {
        var options = new AppiumOptions
        {
            AutomationName = AutomationName.iOSXCUITest,
            PlatformName   = "iOS",
            DeviceName     = Env.DeviceName,
        };
        options.AddAdditionalAppiumOption("app", Env.AppPath);
        options.AddAdditionalAppiumOption("autoAcceptAlerts", true);
        return options;
    }
}
