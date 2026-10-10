using System.Text.RegularExpressions;
using Allure.Net.Commons;
using Allure.NUnit;
using Microsoft.Playwright;
using Microsoft.Playwright.NUnit;
using NUnit.Framework;
using NUnit.Framework.Interfaces;

namespace Example.UiTests.Support;

[AllureNUnit]
[Parallelizable(ParallelScope.Self)]
public abstract class BaseTest : PageTest
{
    private static string ArtifactsDirectory => Path.Combine(TestContext.CurrentContext.WorkDirectory, "playwright-artifacts");

    private static string RawVideoDirectory => Path.Combine(TestContext.CurrentContext.WorkDirectory, "playwright-videos");

    public static string RequiredEnv(string name)
    {
        var value = Environment.GetEnvironmentVariable(name);
        if (string.IsNullOrWhiteSpace(value))
        {
            throw new InvalidOperationException($"Environment variable {name} is not set");
        }
        return value;
    }

    public override BrowserNewContextOptions ContextOptions()
    {
        var options = base.ContextOptions();
        options.BaseURL = RequiredEnv("BASE_URL");
        options.RecordVideoDir = RawVideoDirectory;
        return options;
    }

    [SetUp]
    public async Task StartTracing()
    {
        await Context.Tracing.StartAsync(new()
        {
            Title = TestContext.CurrentContext.Test.FullName,
            Screenshots = true,
            Snapshots = true,
            Sources = true,
        });
    }

    [TearDown]
    public async Task KeepEvidenceOnFailure()
    {
        var failed = TestContext.CurrentContext.Result.Outcome.Status == TestStatus.Failed;
        var name = EvidenceName();
        var video = Page.Video ?? throw new InvalidOperationException("No video recorded: an override of ContextOptions() must amend base.ContextOptions()");
        if (failed)
        {
            await KeepTraceAsync(name);
            await KeepScreenshotAsync(name);
        }
        else
        {
            await Context.Tracing.StopAsync();
        }
        await Context.CloseAsync();
        if (failed)
        {
            await KeepVideoAsync(video, name);
        }
        await video.DeleteAsync();
    }

    private async Task KeepTraceAsync(string name)
    {
        var path = Artifact(name, "zip");
        await Context.Tracing.StopAsync(new() { Path = path });
        Attach("trace", "application/vnd.allure.playwright-trace", path);
    }

    private async Task KeepScreenshotAsync(string name)
    {
        var path = Artifact(name, "png");
        await Page.ScreenshotAsync(new() { Path = path, FullPage = true });
        Attach("screenshot", "image/png", path);
    }

    private static async Task KeepVideoAsync(IVideo video, string name)
    {
        var path = Artifact(name, "webm");
        await video.SaveAsAsync(path);
        Attach("video", "video/webm", path);
    }

    protected string EvidenceName() =>
        Regex.Replace($"{GetType().Name}.{TestContext.CurrentContext.Test.Name}", "[^A-Za-z0-9._-]", "_");

    protected static string Artifact(string name, string extension) =>
        Path.Combine(ArtifactsDirectory, $"{name}.{extension}");

    protected static void Attach(string name, string contentType, string path)
    {
        TestContext.AddTestAttachment(path, name);
        AllureApi.AddAttachment(name, contentType, path);
    }
}
