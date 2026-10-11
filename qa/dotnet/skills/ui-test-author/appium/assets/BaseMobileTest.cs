using System.Text;
using System.Text.RegularExpressions;
using Allure.Net.Commons;
using Allure.NUnit;
using NUnit.Framework;
using NUnit.Framework.Interfaces;
using OpenQA.Selenium.Appium;
using OpenQA.Selenium.Appium.Android;
using OpenQA.Selenium.Appium.iOS;

namespace AppiumTests.Support;

[AllureNUnit]
[Parallelizable(ParallelScope.Self)]
public abstract class BaseMobileTest
{
    private static readonly TimeSpan RecordingLimit = TimeSpan.FromSeconds(180);
    private const int LogTailLines = 200;

    private readonly bool _recordLocally = Environment.GetEnvironmentVariable("DEVICE_FARM") is null;
    private AppiumDriver? _driver;

    protected AppiumDriver Driver => _driver ?? throw new InvalidOperationException("The driver was not started");

    private static string ArtifactsDirectory =>
        Path.Combine(TestContext.CurrentContext.WorkDirectory, "appium-artifacts");

    [OneTimeSetUp]
    public void StartDriver() => _driver = AppiumDriverFactory.Create();

    [OneTimeTearDown]
    public void QuitDriver() => _driver?.Quit();

    [SetUp]
    public void StartRecording()
    {
        if (_recordLocally)
        {
            BeginRecording();
        }
    }

    [TearDown]
    public void CaptureEvidence()
    {
        if (_driver is null)
        {
            return;
        }
        var recording = _recordLocally ? _driver.StopRecordingScreen() : null;
        if (TestContext.CurrentContext.Result.Outcome.Status != TestStatus.Failed)
        {
            return;
        }
        var name = EvidenceName();
        Keep(name, "screenshot", "png", "image/png", _driver.GetScreenshot().AsByteArray);
        Keep(name, "page-source", "xml", "application/xml", Encoding.UTF8.GetBytes(_driver.PageSource));
        Keep(name, "device-log", "log", "text/plain", Encoding.UTF8.GetBytes(DeviceLogTail()));
        if (recording is not null)
        {
            Keep(name, "screen-recording", "mp4", "video/mp4", Convert.FromBase64String(recording));
        }
    }

    private void BeginRecording()
    {
        switch (Driver)
        {
            case AndroidDriver:
                Driver.StartRecordingScreen(AndroidStartScreenRecordingOptions
                    .GetAndroidStartScreenRecordingOptions()
                    .WithTimeLimit(RecordingLimit)
                    .EnableForcedRestart());
                break;
            case IOSDriver:
                Driver.StartRecordingScreen(IOSStartScreenRecordingOptions
                    .GetIosStartScreenRecordingOptions()
                    .WithTimeLimit(RecordingLimit));
                break;
            default:
                throw new InvalidOperationException($"No recorder for {Driver.GetType().Name}");
        }
    }

    private string DeviceLogTail()
    {
        var logType = Driver is AndroidDriver ? "logcat" : "syslog";
        var entries = Driver.Manage().Logs.GetLog(logType);
        return string.Join('\n', entries.TakeLast(LogTailLines).Select(entry => entry.ToString()));
    }

    private string EvidenceName() =>
        Regex.Replace($"{GetType().Name}.{TestContext.CurrentContext.Test.Name}", "[^A-Za-z0-9._-]", "_");

    private static void Keep(string name, string kind, string extension, string type, byte[] content)
    {
        Directory.CreateDirectory(ArtifactsDirectory);
        var path = Path.Combine(ArtifactsDirectory, $"{name}.{extension}");
        File.WriteAllBytes(path, content);
        TestContext.AddTestAttachment(path, kind);
        AllureApi.AddAttachment(kind, type, content, $".{extension}");
    }
}
