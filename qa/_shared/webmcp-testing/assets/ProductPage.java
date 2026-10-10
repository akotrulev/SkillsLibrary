package com.example.uitests.pages;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;

import java.util.List;
import java.util.Map;

public final class ProductPage {
    private static final String SETTLED_TOOLS_JS = """
            ({ name, present, timeout }) => new Promise(resolve => {
              const modelContext = document.modelContext;
              if (!modelContext) {
                throw new Error('document.modelContext is missing: launch Chromium with --enable-features=WebMCP');
              }
              const listTools = async () => (await modelContext.getTools())
                .filter(tool => tool.window === window)
                .map(tool => ({
                  name: tool.name,
                  inputSchema: typeof tool.inputSchema === 'string' ? JSON.parse(tool.inputSchema) : tool.inputSchema,
                  annotations: tool.annotations,
                }));
              const settle = async () => {
                const tools = await listTools();
                if (tools.some(tool => tool.name === name) === present) {
                  resolve(tools);
                }
              };
              modelContext.addEventListener('toolchange', settle);
              setTimeout(async () => resolve(await listTools()), timeout);
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

    public List<Map<?, ?>> settledTools(String name, boolean present, int timeoutMs) {
        List<?> tools = (List<?>) page.evaluate(SETTLED_TOOLS_JS, Map.of("name", name, "present", present, "timeout", timeoutMs));
        return tools.stream().<Map<?, ?>>map(tool -> (Map<?, ?>) tool).toList();
    }

    public Object callTool(String name, Map<String, Object> input, int timeoutMs) {
        return page.evaluate(CALL_TOOL_JS, Map.of("name", name, "input", input, "timeout", timeoutMs));
    }
}
