package com.example.mobiletests.support;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

import static org.assertj.core.api.Assertions.assertThat;

public final class OrderSeeder {
    private final HttpClient http;
    private final URI api;
    private final String token;

    public OrderSeeder(HttpClient http, URI api, String token) {
        this.http = http;
        this.api = api;
        this.token = token;
    }

    public URI create(String orderNumber, String title) throws IOException, InterruptedException {
        String body = """
                {"number": "%s", "title": "%s"}""".formatted(orderNumber, title);
        HttpResponse<String> created = http.send(request(api.resolve("/api/orders"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .build(), HttpResponse.BodyHandlers.ofString());
        assertThat(created.statusCode()).as("create order %s: %s", orderNumber, created.body()).isEqualTo(201);
        return api.resolve(created.headers().firstValue("Location").orElseThrow());
    }

    public void delete(URI order) throws IOException, InterruptedException {
        HttpResponse<String> deleted = http.send(request(order).DELETE().build(), HttpResponse.BodyHandlers.ofString());
        assertThat(deleted.statusCode()).as("delete %s: %s", order, deleted.body()).isEqualTo(204);
    }

    private HttpRequest.Builder request(URI uri) {
        return HttpRequest.newBuilder(uri).header("Authorization", "Bearer " + token);
    }
}
