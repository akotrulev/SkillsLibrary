package com.example.uitests.pages;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;

import java.util.List;
import java.util.Map;

public final class ProductPage {
    private static final String REGISTERED_TOOL_JS = """
            ({ name, timeout }) => new Promise((resolve, reject) => {
              const modelContext = document.modelContext;
              if (!modelContext) {
                throw new Error('document.modelContext is missing: launch Chromium with --enable-features=WebMCP');
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
    private static final String TOOL_NAMES_AFTER_REMOVAL_JS = """
            ({ name, timeout }) => new Promise(resolve => {
              const modelContext = document.modelContext;
              if (!modelContext) {
                throw new Error('document.modelContext is missing: launch Chromium with --enable-features=WebMCP');
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
    private static final String CALL_TOOL_JS = """
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

    private final Page page;
    private final Locator cartBadge;

    public ProductPage(Page page) {
        this.page = page;
        this.cartBadge = page.getByTestId("Cart.Badge").describe("Cart badge");
    }

    public void goTo(String sku) {
        page.navigate("/products/" + sku);
    }

    public Locator cartBadge() {
        return cartBadge;
    }

    public Map<?, ?> registeredTool(String name, int timeoutMs) {
        return (Map<?, ?>) page.evaluate(REGISTERED_TOOL_JS, Map.of("name", name, "timeout", timeoutMs));
    }

    public List<String> toolNamesAfterRemoval(String name, int timeoutMs) {
        List<?> names = (List<?>) page.evaluate(TOOL_NAMES_AFTER_REMOVAL_JS, Map.of("name", name, "timeout", timeoutMs));
        return names.stream().map(String::valueOf).toList();
    }

    public Object callTool(String name, Map<String, Object> input, int timeoutMs) {
        registeredTool(name, timeoutMs);
        return page.evaluate(CALL_TOOL_JS, Map.of("name", name, "input", input, "timeout", timeoutMs));
    }
}
