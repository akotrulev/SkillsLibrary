---
name: qa-api-dto-writer-dotnet
description: Use when creating a new DTO, model class, or response object in a .NET 10 (8-9) / System.Text.Json API test project. Triggers "add a {Resource}Dto", "create the InDto / ModDto for the {resource} endpoint", "scaffold the wrapper DTO for paginated {resource}". Not for the client that calls the endpoint (`api-client-writer`) or the test itself (`api-test-author/generator`).
---

# qa-api-dto-writer-dotnet

Generator skill. Scaffolds a single DTO file in the Accelerator `ApiTests` project.

## When to use

- A new endpoint needs request/response models for the matching client.
- An existing endpoint added/changed fields and the DTO must be extended.
- A response envelope (pagination, wrapper) is needed.

## When NOT to use

- Java or TypeScript DTOs — use `qa-api-dto-writer-java` / `qa-api-dto-writer-typescript`.
- Production domain models — DTOs here exist only for the test project.
- Writing the client itself — use `qa-api-client-writer`.

## Folder & naming convention

```
ApiTests/Models/
├── {Api}/
│   ├── {Resource}Models/
│   │   └── {Resource}Dto.cs
│   └── CommonModels/        ← DTOs shared across clients in the same API group
│       └── {Name}Dto.cs
└── CommonModels/            ← DTOs shared across API groups
    └── {Name}Dto.cs
```

### API group reference

| API Group | Example model folders |
|-----------|------------------------|
| User      | `Models/User/UserModels/`, `Models/User/KycModels/`, `Models/User/AssessmentModels/`, etc. |

## Templates

### Primary DTO (response)

```csharp
using System.Text.Json.Serialization;

namespace ApiTests.Models.{Api}.{Resource}Models;

public class {Name}Dto
{
    [JsonPropertyName("{json_key}")]
    public int Id { get; set; }

    [JsonPropertyName("{json_key}")]
    public string {PropertyName} { get; set; } = string.Empty;

    [JsonPropertyName("{json_key}")]
    public DateTimeOffset {PropertyName} { get; set; }
}
```

### InDto (request body)

```csharp
using System.Text.Json.Serialization;

namespace ApiTests.Models.{Api}.{Resource}Models;

public class {Name}InDto
{
    [JsonPropertyName("{json_key}")]
    public string {PropertyName} { get; set; } = string.Empty;

    [JsonPropertyName("{json_key}")]
    public int {PropertyName} { get; set; }
}
```

### ModDto (patch body — all nullable)

```csharp
using System.Text.Json.Serialization;

namespace ApiTests.Models.{Api}.{Resource}Models;

public class {Name}ModDto
{
    [JsonPropertyName("{json_key}")]
    public string? {PropertyName} { get; set; }

    [JsonPropertyName("{json_key}")]
    public bool? {PropertyName} { get; set; }
}
```

### Wrapper DTO (envelope / paginated response)

```csharp
using System.Text.Json.Serialization;

namespace ApiTests.Models.{Api}.{Resource}Models;

public class {Resource}ListDto
{
    [JsonPropertyName("data")]
    public List<{Resource}Dto> Data { get; set; } = [];

    [JsonPropertyName("page")]
    public int Page { get; set; }

    [JsonPropertyName("total")]
    public int Total { get; set; }

    [JsonPropertyName("total_pages")]
    public int TotalPages { get; set; }

    public {Resource}ListDto(
        List<{Resource}Dto>? data = null,
        int page = 0,
        int total = 0,
        int totalPages = 0)
    {
        Data = data ?? [];
        Page = page;
        Total = total;
        TotalPages = totalPages;
    }
}
```

## Rules

### Naming

- `{Resource}Dto` — PascalCase resource noun + `Dto` (e.g. `UserDto`, `OrderDto`).
- `{Resource}InDto` for request bodies, `{Resource}ModDto` for PATCH bodies, `{Resource}ListDto` for envelopes.

### Folder & namespace

- DTOs live in `Models/{Api}/{Resource}Models/`. Namespace: `ApiTests.Models.{Api}.{Resource}Models`.
- Shared within an API group → `Models/{Api}/CommonModels/`, namespace `ApiTests.Models.{Api}.CommonModels`.
- Shared across API groups → `Models/CommonModels/`, namespace `ApiTests.Models.CommonModels`.
- One DTO per file, one file per class.

### Properties

- `[JsonPropertyName("json_key")]` on **every** property — explicitly map JSON keys.
- Prefer default values over nullable types on response/request DTOs.
- Type mappings:

  | JSON type        | C# type           | Default          |
  |------------------|-------------------|------------------|
  | string           | `string`          | `string.Empty`   |
  | integer          | `int`             | `0`              |
  | decimal          | `decimal`         | `0`              |
  | boolean          | `bool`            | `false`          |
  | ISO date string  | `DateTimeOffset`  | *(none needed)*  |
  | array of T       | `List<T>`         | `[]`             |
  | nested object    | another DTO       | `null!`          |

### Class rules

- DTOs are plain data containers — no validation, no methods.
- Use object initializer in tests: `new {Name}InDto { Prop = value, ... }`.
- `System.Text.Json.Serialization` only — never `Newtonsoft.Json`.
- Deserialization happens in tests/clients, never inside the DTO.

## Generation steps

0. If an **OpenAPI/Swagger spec** is supplied, derive the answers to steps 1–3 from it (API group from the path/tags, resource from the schema name, properties + types from the schema definition) — do not ask.
1. Ask: which **API group**? (User / Assessment / Legal / Reference / Auth)
2. Ask: resource name and DTO kind (`Dto`, `InDto`, `ModDto`, nested, wrapper).
3. Ask which properties are needed, or inspect a sample API response.
4. Generate at `ApiTests/Models/{Api}/{Resource}Models/{Name}Dto.cs`.
5. Run `dotnet build ApiTests/ApiTests.csproj` — expect 0 errors.
