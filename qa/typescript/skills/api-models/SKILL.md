---
name: api-models
description: Use when the user asks to create a new DTO / model / response interface in a TypeScript test project (Node 24 (22 supported) + TS strict, typically alongside supertest or axios). Triggers: "add a {Resource}Dto in TS", "create the InDto / ModDto types", "scaffold the wrapper DTO for paginated {resource} in TS". Do NOT use for the client module (`qa-typescript:api-client-writer`) or the test specs (`qa-typescript:api-tests`).
---

# qa-typescript:api-models

Generator skill. Scaffolds a single DTO file in the TypeScript `apitests/` package.

## When to use

- A new endpoint needs request/response types for the matching supertest/axios client.
- An existing type needs new fields after an API change.
- A response envelope (pagination, wrapper) is needed.

## When NOT to use

- Reacting to a **new version of a swagger/OpenAPI spec** — start at `qa-<stack>:api-spec-assets`: it replaces the stored spec asset in place, derives the changed-schema work list from `git diff`, and comes back here for only the files that list names. Do not re-generate every schema because the spec moved.

- C# or Java DTOs — use `qa-dotnet:api-models` / `qa-java:api-models`.
- Runtime validation (parsing untrusted JSON, contract verification) — define a Zod/Valibot schema instead and infer the type from it.
- Writing the client itself — use the TS API client skill.

## Folder & naming convention

```
apitests/src/models/
├── {api}/
│   ├── {resource}/
│   │   ├── {resource}.dto.ts
│   │   ├── {resource}-in.dto.ts
│   │   └── {resource}-mod.dto.ts
│   └── common/                ← shared within the API group
│       └── {name}.dto.ts
└── common/                    ← shared across API groups
    └── {name}.dto.ts
```

- File names: `kebab-case.dto.ts`.
- Type names inside the file: `PascalCase` (`UserDto`, `UserInDto`, `UserModDto`, `UserListDto`).

## Decision: `interface` vs `type`

Default to `interface` for object-shaped DTOs (extendable, better error messages). Use `type` when you need a union, intersection, or `Pick`/`Omit` derivation.

## JSON key convention

**The TS field name is the JSON key, verbatim.** If the API returns `snake_case`, the type uses `snake_case`. Do not rename to `camelCase` and rely on a runtime mapping — that drift causes the worst class of test bugs in this codebase. If a project-wide convention forces camelCase, do that remapping in the client layer (with a typed mapper), never silently in the DTO.

## Templates

### Primary DTO (response)

```ts
export interface {Name}Dto {
  id: number;
  {json_key}: string;
  {json_key}: string; // ISO 8601 date-time
}
```

### InDto (request body)

```ts
export interface {Name}InDto {
  {json_key}: string;
  {json_key}: number;
}
```

### ModDto (PATCH body — all optional)

```ts
export interface {Name}ModDto {
  {json_key}?: string;
  {json_key}?: boolean;
}
```

### Wrapper DTO (envelope / paginated response)

```ts
import type { {Resource}Dto } from "./{resource}.dto";

export interface {Resource}ListDto {
  data: {Resource}Dto[];
  page: number;
  total: number;
  total_pages: number;
}
```

### Derivation helpers

When an InDto is "the response shape minus server-managed fields", derive it with `Omit` to avoid drift:

```ts
import type { UserDto } from "./user.dto";

export type UserInDto = Omit<UserDto, "id" | "created_at" | "updated_at">;
```

For ModDto, derive from InDto:

```ts
export type UserModDto = Partial<UserInDto>;
```

Use derivations when the relationship is genuinely "subset of fields, same names". When the wire shape diverges (e.g. server returns nested objects but PATCH takes ids), write the type explicitly.

## Rules

### Naming

- Type name: `{Resource}Dto`, `{Resource}InDto`, `{Resource}ModDto`, `{Resource}ListDto`.
- File name: `kebab-case.dto.ts` matching the type (`user.dto.ts`, `user-in.dto.ts`).

### Folder & imports

- DTOs live in `apitests/src/models/{api}/{resource}/`.
- Shared within an API group → `models/{api}/common/`.
- Shared across API groups → `models/common/`.
- Use `import type { ... }` for type-only imports — keeps the runtime bundle empty.
- One exported DTO per file. Re-export from an `index.ts` per resource if it improves ergonomics.

### Properties

- Field names match the JSON keys verbatim (see decision above).
- Type mappings:

  | JSON type        | TS type        | Notes |
  |------------------|----------------|-------|
  | string           | `string`       |       |
  | integer/decimal  | `number`       | TS has no separate int/decimal — comment if a precision contract matters |
  | boolean          | `boolean`      |       |
  | ISO date string  | `string`       | keep as ISO string; convert at call sites if needed. Add a `// ISO 8601` comment |
  | array of T       | `T[]`          |       |
  | nested object    | another DTO    |       |
  | nullable field   | `T \| null`    | use `null`, not `undefined`, for "field present but empty" |
  | optional field   | `field?: T`    | omitted from the wire when unset (use in `ModDto`) |

- Use `readonly` on response DTO fields when you want the compiler to enforce immutability in tests; skip it on `InDto`/`ModDto` since they're constructed by tests.

### Class rules

- No classes — DTOs are TypeScript types, not classes. No methods, no decorators.
- Construct in tests via object literal: `const body: UserInDto = { name: "x", age: 30 };`.
- Do NOT add `tslib`-style helpers, `class-transformer` decorators, or runtime metadata. If runtime validation is needed, write a Zod schema in a separate `*.schema.ts` file and `z.infer` the type from it.

## Generation steps

0. If an **OpenAPI/Swagger spec** is supplied, derive the answers to steps 1–3 from it (API group from the path/tags, resource from the schema name, properties + types from the schema definition) — do not ask.
1. Ask: which **API group**? (User / Assessment / Legal / Reference / Auth)
2. Ask: resource name and DTO kind (`Dto`, `InDto`, `ModDto`, nested, wrapper).
3. Ask which properties are needed, or inspect a sample API response.
4. Decide: explicit definition or derivation (`Omit` / `Partial`) from an existing DTO.
5. Generate at `apitests/src/models/{api}/{resource}/{name}.dto.ts`.
6. Run the project's own typecheck script with the package manager `packageManager` names — expect 0 errors. Inside a plan task marked `Gate: none`, run none of this and report the files as "written, not run".
