using System.Text.RegularExpressions;
using Microsoft.Playwright;

namespace Example.UiTests.Clients;

public sealed record PageHtml(int Status, string CacheControl, string Markup);

public sealed class PageHtmlClient(IAPIRequestContext request)
{
    public async Task<PageHtml> GetAsync(string route)
    {
        var response = await request.GetAsync(route);
        var body = await response.TextAsync();
        var markup = Regex.Replace(body, "<script[\\s\\S]*?</script>", string.Empty, RegexOptions.IgnoreCase);
        return new PageHtml(response.Status, response.Headers.GetValueOrDefault("cache-control", string.Empty), markup);
    }
}
