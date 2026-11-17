package com.example.apitests.clients;

import com.example.apitests.models.health.HealthDto;
import com.example.apitests.support.Env;
import io.restassured.response.Response;

import static org.testng.Assert.assertEquals;

public class HealthClient extends BaseApiClient {
    private static final String GET_PATH = "/health";

    public HealthClient(String jwt) {
        super(Env.apiUrl(), jwt);
    }

    public Response get() {
        return execute(spec().get(GET_PATH));
    }

    public HealthDto get(int expectedStatus) {
        Response response = get();
        assertEquals(response.statusCode(), expectedStatus, "GET " + GET_PATH + " returned " + response.asString());
        return deserialize(response, HealthDto.class);
    }
}
