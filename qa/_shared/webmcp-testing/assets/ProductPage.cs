using System.Text.Json;
using Microsoft.Playwright;

namespace Example.UiTests.Pages;

public sealed class ProductPage
{
    private const string RegisteredToolJs = """
        ({ name, timeout }) => new Promise((resolve, reject) => {
          const modelContext = document.modelContext;
          if (!modelContext) {
            throw new Error('document.modelContext is missing: run with webmcp.runsettings (--enable-features=WebMCP)');
          }
          const listTools = async () => (await modelContext.getTools()).filter(tool => tool.window === window);
          const settle = async () => {
            const tool = (await listTools()).find(candidate => candidate.name === name);
            if (tool) {
              resolve({
                name: tool.name,
                inputSchema: typeof tool.inputSchema === 'string' ? JSON.parse(tool.inputSchema) : tool.inputSchema,
                annotations: tool.annotations,
              });
            }
          };
          modelContext.addEventListener('toolchange', settle);
          setTimeout(async () => reject(new Error(
            `WebMCP tool "${name}" not registered within ${timeout} ms; tools: ${(await listTools()).map(tool => tool.name).join(', ')}`)), timeout);
          settle();
        })
        """;

    private const string ToolNamesAfterRemovalJs = """
        ({ name, timeout }) => new Promise(resolve => {
          const modelContext = document.modelContext;
          if (!modelContext) {
            throw new Error('document.modelContext is missing: run with webmcp.runsettings (--enable-features=WebMCP)');
          }
          const toolNames = async () => (await modelContext.getTools())
            .filter(tool => tool.window === window)
            .map(tool => tool.name);
          const settle = async () => {
            const names = await toolNames();
            if (!names.includes(name)) {
              resolve(names);
            }
          };
          modelContext.addEventListener('toolchange', settle);
          setTimeout(async () => resolve(await toolNames()), timeout);
          settle();
        })
        """;

    private const string CallToolJs = """
        async ({ name, input, timeout }) => {
          const modelContext = document.modelContext;
          const tools = await modelContext.getTools();
          const tool = tools.find(candidate => candidate.name === name && candidate.window === window);
          if (!tool) {
            throw new Error(`No WebMCP tool named "${name}". Available tools: ${tools.map(candidate => candidate.name).join(', ')}`);
          }
          const execute = async () => {
            try {
              return await modelContext.executeTool(tool, input);
            } catch (error) {
              if (!String(error?.message).includes('Failed to parse input')) {
                throw error;
              }
              return modelContext.executeTool(tool, JSON.stringify(input));
            }
          };
          const expired = new Promise((_, reject) => setTimeout(
            () => reject(new Error(`WebMCP tool "${name}" did not answer within ${timeout} ms`)), timeout));
          const raw = await Promise.race([execute(), expired]);
          return typeof raw === 'string' && raw !== 'undefined' ? JSON.parse(raw) : raw;
        }
        """;

    private readonly IPage _page;

    public ProductPage(IPage page)
    {
        _page = page;
        CartBadge = page.GetByTestId("Cart.Badge").Describe("Cart badge");
    }

    public ILocator CartBadge { get; }

    public async Task GoToAsync(string sku) => await _page.GotoAsync($"/products/{sku}");

    public async Task<JsonElement> RegisteredToolAsync(string name, int timeoutMs) =>
        await _page.EvaluateAsync<JsonElement>(RegisteredToolJs, new { name, timeout = timeoutMs });

    public async Task<string[]> ToolNamesAfterRemovalAsync(string name, int timeoutMs) =>
        await _page.EvaluateAsync<string[]>(ToolNamesAfterRemovalJs, new { name, timeout = timeoutMs });

    public async Task<JsonElement> CallToolAsync(string name, object input, int timeoutMs)
    {
        await RegisteredToolAsync(name, timeoutMs);
        return await _page.EvaluateAsync<JsonElement>(CallToolJs, new { name, input, timeout = timeoutMs });
    }
}
