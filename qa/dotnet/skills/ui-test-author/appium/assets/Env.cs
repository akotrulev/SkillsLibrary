namespace AppiumTests.Support;

public static class Env
{
    private const string DefaultAppiumUrl = "http://127.0.0.1:4723";

    public static string AppiumUrl => Environment.GetEnvironmentVariable("APPIUM_URL") ?? DefaultAppiumUrl;

    public static string Required(string name)
    {
        var value = Environment.GetEnvironmentVariable(name);
        if (string.IsNullOrWhiteSpace(value))
        {
            throw new InvalidOperationException($"Environment variable {name} is not set");
        }
        return value;
    }
}
