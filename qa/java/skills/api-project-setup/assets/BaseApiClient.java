package com.example.apitests.clients;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.json.JsonMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import io.qameta.allure.Allure;
import io.qameta.allure.AttachmentOptions;
import io.qameta.allure.restassured.AllureRestAssured;
import io.restassured.RestAssured;
import io.restassured.config.ObjectMapperConfig;
import io.restassured.config.RestAssuredConfig;
import io.restassured.response.Response;
import io.restassured.specification.RequestSpecification;

import java.util.List;

public abstract class BaseApiClient {
    private static final ObjectMapper MAPPER = JsonMapper.builder()
            .addModule(new JavaTimeModule())
            .enable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
            .build();
    private static final RestAssuredConfig CONFIG = RestAssuredConfig.config()
            .objectMapperConfig(ObjectMapperConfig.objectMapperConfig().jackson2ObjectMapperFactory((type, charset) -> MAPPER));
    private static final System.Logger LOG = System.getLogger(BaseApiClient.class.getName());

    private final String baseUri;
    private final String token;

    protected BaseApiClient(String baseUri, String token) {
        this.baseUri = baseUri;
        this.token = token;
    }

    protected RequestSpecification spec() {
        RequestSpecification spec = RestAssured.given()
                .config(CONFIG)
                .baseUri(baseUri)
                .filter(new TraceparentFilter())
                .filter(new AllureRestAssured());
        if (token.isBlank()) {
            return spec;
        }
        return spec.header("Authorization", "Bearer " + token);
    }

    protected Response execute(Response response) {
        LOG.log(System.Logger.Level.DEBUG, "{0} {1} in {2} ms", getClass().getSimpleName(), response.statusCode(), response.time());
        return response;
    }

    protected <T> T deserialize(Response response, Class<T> type) {
        String body = response.asString();
        try {
            return MAPPER.readValue(body, type);
        } catch (JsonProcessingException e) {
            throw parseFailure(body, type.getSimpleName(), e);
        }
    }

    protected <T> List<T> deserializeList(Response response, Class<T> type) {
        String body = response.asString();
        try {
            return MAPPER.readValue(body, MAPPER.getTypeFactory().constructCollectionType(List.class, type));
        } catch (JsonProcessingException e) {
            throw parseFailure(body, "List<" + type.getSimpleName() + ">", e);
        }
    }

    private static AssertionError parseFailure(String body, String target, JsonProcessingException e) {
        Allure.attachment("unparsed response", "application/json", body, AttachmentOptions.withFileExtension("json"));
        return new AssertionError("Response does not match " + target + ": " + e.getMessage() + "\nPayload: " + body, e);
    }
}
