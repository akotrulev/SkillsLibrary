using OpenQA.Selenium.Appium;
using OpenQA.Selenium.Appium.Android;
using OpenQA.Selenium.Appium.iOS;

namespace AppiumTests.Support;

public static class AppiumDriverFactory
{
    private static readonly TimeSpan CommandTimeout = TimeSpan.FromSeconds(180);

    public static AppiumDriver Create()
    {
        var server = new Uri(Env.AppiumUrl);
        var platform = Env.Required("PLATFORM");
        return platform switch
        {
            "android" => new AndroidDriver(server, AndroidOptions(), CommandTimeout),
            "ios" => new IOSDriver(server, IosOptions(), CommandTimeout),
            _ => throw new ArgumentException($"PLATFORM must be android or ios, got {platform}"),
        };
    }

    private static AppiumOptions AndroidOptions()
    {
        var options = new AppiumOptions
        {
            AutomationName = "UiAutomator2",
            PlatformName = "Android",
            DeviceName = Env.Required("DEVICE_NAME"),
            App = Env.Required("APP_PATH"),
        };
        options.AddAdditionalAppiumOption("autoGrantPermissions", true);
        options.AddAdditionalAppiumOption("appium:settings[disableIdLocatorAutocompletion]", true);
        return options;
    }

    private static AppiumOptions IosOptions()
    {
        var options = new AppiumOptions
        {
            AutomationName = "XCUITest",
            PlatformName = "iOS",
            DeviceName = Env.Required("DEVICE_NAME"),
            PlatformVersion = Env.Required("PLATFORM_VERSION"),
            App = Env.Required("APP_PATH"),
        };
        options.AddAdditionalAppiumOption("autoAcceptAlerts", true);
        return options;
    }
}
