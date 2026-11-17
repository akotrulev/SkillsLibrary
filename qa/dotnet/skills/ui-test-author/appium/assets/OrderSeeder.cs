using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using NUnit.Framework;

namespace AppiumTests.Seeders;

public sealed class OrderSeeder : IDisposable
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    private readonly HttpClient _http;

    public OrderSeeder(Uri apiUrl, string token)
    {
        _http = new HttpClient { BaseAddress = apiUrl };
        _http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
    }

    public async Task<SeededOrder> CreateAsync(string title)
    {
        using var response = await _http.PostAsJsonAsync("api/orders", new { title }, JsonOptions);
        var body = await response.Content.ReadAsStringAsync();
        Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.Created), body);
        return JsonSerializer.Deserialize<SeededOrder>(body, JsonOptions)
            ?? throw new InvalidOperationException($"POST api/orders returned no {nameof(SeededOrder)}: {body}");
    }

    public async Task DeleteAsync(SeededOrder order)
    {
        using var response = await _http.DeleteAsync($"api/orders/{order.Id}");
        Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.NoContent), await response.Content.ReadAsStringAsync());
    }

    public void Dispose() => _http.Dispose();
}

public sealed record SeededOrder(string Id, string Number, string Title);
