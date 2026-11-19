package com.example.uitests.clients;

import com.microsoft.playwright.APIRequestContext;
import com.microsoft.playwright.APIResponse;

public final class PageHtmlClient {
    private final APIRequestContext request;

    public PageHtmlClient(APIRequestContext request) {
        this.request = request;
    }

    public PageHtml get(String route) {
        APIResponse response = request.get(route);
        String markup = response.text().replaceAll("(?is)<script.*?</script>", "");
        return new PageHtml(response.status(), response.headers().getOrDefault("cache-control", ""), markup);
    }

    public record PageHtml(int status, String cacheControl, String markup) {
    }
}
