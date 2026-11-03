---
name: api-models
description: Use when creating a DTO or response model in a .NET API test project (System.Text.Json). Triggers "add an OrderDto". Not for the client class (api-client-writer).
---

# qa-dotnet:api-models

Generator skill. Scaffolds a single DTO file in the Accelerator `ApiTests` project.

## When to use

- A new endpoint needs request/response models for the matching client.
- An existing endpoint added/changed fields and the DTO must be extended.
- A response envelope (pagination, wrapper) is needed.

## When NOT to use

- Java or TypeScript DTOs — use `qa-java:api-models` / `qa-typescript:api-models`.
- Production domain models — DTOs here exist only for the test project.
- Writing the client itself — use `qa-dotnet:api-client-writer`.
- Reacting to a **new version of a swagger/OpenAPI spec** — start at `qa-<stack>:api-spec-assets`: it replaces the stored spec asset in place, derives the changed-DTO work list from `git diff`, and comes back here for only the files that list names. Do not re-generate every DTO because the spec moved.

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

The standards this skill's output must meet are the qa-dotnet rule files, not a list here: `automation.md` and `api.md`. Read the project's copy in `.claude/rules/qa-dotnet/`, or the plugin's in `qa/dotnet/skills/rules/` when the project has not installed them (`/qa-dotnet:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Conventions

### Naming

- `{Resource}Dto` — PascalCase resource noun + `Dto` (e.g. `UserDto`, `OrderDto`).
- `{Resource}InDto` for request bodies, `{Resource}ModDto` for PATCH bodies, `{Resource}ListDto` for envelopes.

### Folder & namespace

- DTOs live in `Models/{Api}/{Resource}Models/`. Namespace: `ApiTests.Models.{Api}.{Resource}Models`.
- Shared within an API group → `Models/{Api}/CommonModels/`, namespace `ApiTests.Models.{Api}.CommonModels`.
- Shared across API groups → `Models/CommonModels/`, namespace `ApiTests.Models.CommonModels`.

### Properties

Type mappings (`[JsonPropertyName]` on every property, defaults over nullable):

  | JSON type        | C# type           | Default          |
  |------------------|-------------------|------------------|
  | string           | `string`          | `string.Empty`   |
  | integer          | `int`             | `0`              |
  | decimal          | `decimal`         | `0`              |
  | boolean          | `bool`            | `false`          |
  | ISO date string  | `DateTimeOffset`  | *(none needed)*  |
  | array of T       | `List<T>`         | `[]`             |
  | nested object    | another DTO       | `null!`          |

### Usage

- Use object initializer in tests: `new {Name}InDto { Prop = value, ... }`.
- Deserialization happens in tests/clients, never inside the DTO.

## Generation steps

0. If an **OpenAPI/Swagger spec** is supplied, derive the answers to steps 1–3 from it (API group from the path/tags, resource from the schema name, properties + types from the schema definition) — do not ask.
1. Ask: which **API group**? (User / Assessment / Legal / Reference / Auth)
2. Ask: resource name and DTO kind (`Dto`, `InDto`, `ModDto`, nested, wrapper).
3. Ask which properties are needed, or inspect a sample API response.
4. Generate at `ApiTests/Models/{Api}/{Resource}Models/{Name}Dto.cs`.
5. Run `dotnet build ApiTests/ApiTests.csproj` — expect 0 errors.
