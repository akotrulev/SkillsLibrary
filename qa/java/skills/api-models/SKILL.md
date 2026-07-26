---
name: qa-api-models-java
description: Use when the user asks to create a new DTO / model class / response object in a Java test project (Java 21 + Jackson, typically alongside RestAssured). Triggers: "add a {Resource}Dto in Java", "create the InDto / ModDto record", "scaffold the wrapper DTO for paginated {resource} in Java". For end-to-end suite work prefer the phased agent `qa-api-java` / `qa-llm-java` / `qa-performance-java` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# qa-api-models-java

Generator skill. Scaffolds a single DTO file in the Java `apitests` module.

## When to use

- A new endpoint needs request/response models for the matching RestAssured client.
- An existing DTO needs to add fields after an API change.
- A response envelope (pagination, wrapper) is needed.

## When NOT to use

- C# or TypeScript DTOs — use `qa-api-models-dotnet` / `qa-api-models-typescript`.
- Production domain models — these DTOs are test-project-only.
- Writing the client itself — use `qa-api-client-writer` (or the Java equivalent).

## Folder & naming convention

Mirrors the .NET layout, translated to Gradle conventions:

```
apitests/src/test/java/com/{org}/apitests/models/
├── {api}/
│   ├── {resource}/
│   │   └── {Resource}Dto.java
│   └── common/                ← DTOs shared across clients in the same API group
│       └── {Name}Dto.java
└── common/                    ← DTOs shared across API groups
    └── {Name}Dto.java
```

Package follows folder: `com.{org}.apitests.models.{api}.{resource}`.

## Templates

### Primary DTO (response) — Java record

Use a `record` for response DTOs. Records are immutable, terse, and Jackson supports them natively when `jackson-databind` ≥ 2.12.

```java
package com.{org}.apitests.models.{api}.{resource};

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.OffsetDateTime;
import java.util.List;

public record {Name}Dto(
    @JsonProperty("{json_key}") long id,
    @JsonProperty("{json_key}") String {propertyName},
    @JsonProperty("{json_key}") OffsetDateTime {propertyName}
) { }
```

### InDto (request body) — record with a builder for tests

Use a record. For ergonomic construction in tests, expose a static `builder()` only when the DTO has more than three fields; otherwise use the canonical constructor.

```java
package com.{org}.apitests.models.{api}.{resource};

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonInclude;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record {Name}InDto(
    @JsonProperty("{json_key}") String {propertyName},
    @JsonProperty("{json_key}") Integer {propertyName}
) { }
```

### ModDto (PATCH body — all fields nullable)

For PATCH bodies, every field is a boxed reference type and `@JsonInclude(NON_NULL)` skips unset fields when serializing.

```java
package com.{org}.apitests.models.{api}.{resource};

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonInclude;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record {Name}ModDto(
    @JsonProperty("{json_key}") String {propertyName},
    @JsonProperty("{json_key}") Boolean {propertyName}
) { }
```

### Wrapper DTO (envelope / paginated response)

```java
package com.{org}.apitests.models.{api}.{resource};

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record {Resource}ListDto(
    @JsonProperty("data") List<{Resource}Dto> data,
    @JsonProperty("page") int page,
    @JsonProperty("total") int total,
    @JsonProperty("total_pages") int totalPages
) {
    public {Resource}ListDto {
        data = data == null ? List.of() : data;
    }
}
```

## Rules

### Naming

- `{Resource}Dto` — PascalCase noun + `Dto` (e.g. `UserDto`, `OrderDto`).
- `{Resource}InDto` for request bodies, `{Resource}ModDto` for PATCH, `{Resource}ListDto` for envelopes.

### Folder & package

- DTOs live in `apitests/src/test/java/.../models/{api}/{resource}/` — same source set as the clients and tests that use them. Package: `com.{org}.apitests.models.{api}.{resource}`.
- Shared within an API group → `models/{api}/common/`.
- Shared across API groups → `models/common/`.
- One DTO per file; record name matches file name.

### Properties

- `@JsonProperty("json_key")` on **every** record component — explicit mapping, never rely on reflection of Java field names.
- Use boxed types (`Integer`, `Boolean`, `Long`) on `*ModDto` so unset fields stay `null`. On `*Dto` and `*InDto`, prefer primitives.
- Type mappings:

  | JSON type        | Java type          | Notes |
  |------------------|--------------------|-------|
  | string           | `String`           |       |
  | integer          | `int` / `Integer`  | boxed in `ModDto` |
  | decimal          | `BigDecimal`       | never `double` for money |
  | boolean          | `boolean` / `Boolean` | boxed in `ModDto` |
  | ISO date string  | `OffsetDateTime`   | needs `JavaTimeModule` registered on `ObjectMapper` |
  | array of T       | `List<T>`          | use `List.of()` for empty |
  | nested object    | another record DTO |       |

### Class rules

- DTOs are plain data carriers — no behavior, no validation. Records enforce this.
- Construct in tests via the canonical constructor: `new {Name}InDto(value1, value2)`.
- Jackson `ObjectMapper` must register `JavaTimeModule` once at app startup (typically in a `TestConfig` / `RestAssuredConfig` setup).
- Deserialization happens in tests / clients, never inside the DTO.

## Generation steps

0. If an **OpenAPI/Swagger spec** is supplied, derive the answers to steps 1–3 from it (API group from the path/tags, resource from the schema name, properties + types from the schema definition) — do not ask.
1. Ask: which **API group**? (User / Assessment / Legal / Reference / Auth)
2. Ask: resource name and DTO kind (`Dto`, `InDto`, `ModDto`, nested, wrapper).
3. Ask which properties are needed, or inspect a sample API response.
4. Generate at `apitests/src/test/java/com/{org}/apitests/models/{api}/{resource}/{Name}Dto.java`.
5. Run `./gradlew :apitests:compileTestJava` — expect 0 errors.
