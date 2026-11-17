package com.example.apitests.models.health;

import com.fasterxml.jackson.annotation.JsonProperty;

public record HealthDto(
        @JsonProperty("status") String status
) {
}
