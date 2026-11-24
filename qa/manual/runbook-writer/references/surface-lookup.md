# Surface lookup — where each operation lives

Step 2 of `runbook-writer`. For every operation the cases use, find its endpoint, its screen on each UI, its table, and any admin call, simulator or job the cases need, and record how the tester reaches each actor. The result is the runbook's **§1 Access and tools** and **§2 Surface map**.

## What the code is for

The spec and the suite say what **should** happen: every expected result comes from them. The code says what **is**: the route, the field name, the label, the test id, the column. Take addresses from the code and outcomes from the suite.

Where the code disagrees with the suite (the spec says a duplicate SKU is refused with `409`, the controller returns `400`), the test keeps the suite's value and the disagreement goes in the runbook's §14 as a question for the owner. It is also the likeliest place for the run to find a defect.

Where the suite is silent on a value a step must assert (a status code, an error code), take the contract's, else the code's, and list it in §14 as a value the owner confirms.

## Stamps

Every row of the Access table and the Surface map carries one:

| Stamp | Meaning |
|---|---|
| `detected <file:line>` | Read in the codebase this session |
| `stated` | Given by the user, the spec or the contract |
| `observed` | Seen on the running system this session |
| `assumed` | Inferred; listed in §14 until confirmed |

## An OpenAPI document becomes a request catalogue

Where the API has an OpenAPI 3 JSON document, committed or served (`/swagger/v1/swagger.json`, `/openapi/v1.json`, `/v3/api-docs`), generate the catalogue before reading any route by hand:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/qa/manual/runbook-writer/scripts/openapi-to-http.py" <file or URL> \
  --out docs/runbooks/api-requests --env <environment>
```

It writes one `.http` file per tag, with every operation as a named request: path parameters and required query parameters as `{{variables}}`, the header its security scheme needs, a JSON body sampled from the schema, and the documented statuses and optional query parameters as comments. `http-client.env.json` gets the environment's `baseUrl`; pass `--base-url` where the document names no server.

- **A person sends a request from the editor** (Rider, IntelliJ, VS Code's REST Client) after replacing the sampled values, and `ijhttp` sends a whole file. The token is the tester's to supply, in `http-client.private.env.json`, which is git-ignored and never written by the agent.
- **The Surface map's API cells and each request's shape are read from the catalogue**, stamped `stated`.
- **A step copies its request from the catalogue** and gives every field the test's own value. A sampled value (`"string"`, `0`) never stays in a step.
- **The catalogue is regenerated, never edited.** A rerun overwrites the `.http` files and keeps what a person added to the environment file.
- **It is this lane's own output**, so the detection under "How the project makes API calls" leaves `docs/runbooks/api-requests/` out: the runbook's API form stays the project's tool, else `curl`.
- **A Swagger 2.0 or YAML document** makes the script exit `1` and say so. Ask the user for an OpenAPI 3 JSON export, or go on without the catalogue.

## With the codebase

Read the API project first: it names the operations, and the UI is then matched to them.

### The API project

| Fact needed | .NET | Spring | Node (Nest, Express) | Any other stack |
|---|---|---|---|---|
| Routes and verbs | `[HttpGet]`…`[HttpDelete]`, `Map{Get,Post,Put,Patch,Delete}(` | `@GetMapping`…`@DeleteMapping`, `@RequestMapping` | `@Get(`…`@Delete(`, `router.<verb>(` | `Grep` the path segment the spec names |
| Request and response shape | the request and response records | the DTO classes and records | the DTO classes, Zod schemas | the handler's parameter and return types |
| Server-side validation | FluentValidation validators, DataAnnotations | `jakarta.validation` constraints behind `@Valid` | `class-validator` decorators, Zod | the handler's first lines |
| Who may call it | `[Authorize]`, policies, roles | `@PreAuthorize`, the `SecurityFilterChain` | guards, auth middleware | the router's middleware |
| Fields the server sets | entity defaults, `SaveChanges` interceptors | `@CreatedDate`, `@PrePersist` | Prisma `@default(now())`, entity hooks | column defaults in the migrations |
| Tables and columns | EF Core migrations, `OnModelCreating` | Flyway or Liquibase scripts, `@Table`, `@Column` | `schema.prisma`, TypeORM entities, Knex migrations | the migrations folder |
| Derived copies | cache keys, search indexers, read models, outbox and event handlers that react to the entity | the same | the same | the same |

A committed OpenAPI document wins over the code for the request and response shape; where the two differ, that is a §14 row.

A field the server sets and no endpoint accepts is what a data recipe exists for: it is the `Why not the API` line. The derived copies are what DB-write rule 6 needs. The tables and columns also give every DB read its query: the status, amount and history columns an action changes.

### The UI projects

| Fact needed | React, Next.js | Blazor | React Native (Expo) | iOS · Android |
|---|---|---|---|---|
| Screens and routes | `app/**/page.tsx`, the React Router route table | `@page` directives | `app/` (Expo Router) | the navigation graph, `NavigationStack`, `NavHost` |
| Which endpoint a screen calls | the typed client, Server Actions, query hooks | the typed `HttpClient` services | the query hooks | the repository or service layer |
| Labels, headings, messages | JSX text, translation files | markup, `.resx` | `<Text>`, translation files | `Localizable`, `strings.xml` |
| Test ids | `data-testid` | `data-testid` | `testID` | `accessibilityIdentifier` · `testTag` |
| Rules enforced only in the browser or app | Zod schemas, form `rules` | `EditForm` validators | the form schema | the view model |
| What gates a screen | role checks, feature flags | `[Authorize]`, `AuthorizeView` | the same | the same |

Match each screen to the API operation it calls: that pairing is one row of the Surface map. A screen that calls no endpoint of the feature is out of the map.

A fact the checkout should hold and does not (a form component that is imported and absent, a page a link points at) is `assumed`. A screen or control with no trace at all in the code and nobody's word for it is `not found`: its grid cell says where it was looked for, and no test is written on a guess. A row whose facts have different sources gives each fact its own stamp in the Source cell.

### How the project makes API calls

| Found (`Glob`) | The runbook's API form |
|---|---|
| `**/*.http`, `**/*.rest`, `http-client.env.json` | A `.http` file beside the runbook, in the dialect the project's files use |
| `**/*.postman_collection.json`, `*.postman_environment.json` | A Postman collection beside the runbook, reusing the project's environment variable names |
| `bruno.json`, `**/*.bru` | A Bruno folder beside the runbook |
| None of these | `curl` blocks in the runbook |

Record the globs searched when nothing is found. Reuse the project's variable names (`baseUrl`, `token`) so its environment files work unchanged.

### The other actors

| Actor | Where to look |
|---|---|
| Admin | Controllers and routes under an admin or management prefix, and the policies that guard them |
| Sim | A simulator or fake-provider project, a test-mode controller, the provider's sandbox settings in the environment's configuration |
| Job | Scheduler registrations (hosted services, `@Scheduled`, cron tables), and any "run now" endpoint or command for them |
| Doc | The endpoint that returns the document, and the template that fixes its rows |
| Notify | The dispatch table or outbox, the message templates, the environment's mail catcher |
| Helper scripts | A `tools/`, `scripts/` or QA folder with callers, waiters or simulator drivers the project already has: these are used before a new one is written |

## Without the codebase

| Actor | Source, strongest first |
|---|---|
| API | The contract the user gave; the running API's OpenAPI document (`/swagger/v1/swagger.json`, `/v3/api-docs`, `/openapi.json`), turned into the request catalogue above; a question |
| UI | A look-only pass over the screens the cases name, by the driving routes of `qa/manual/app-exploration/references/probes.md`: read labels and routes from the snapshot and write nothing. Stamp `observed` |
| DB | The schema the user gives; on a non-production database, the catalogue read-only (`information_schema.columns`, the collection's sample document); a question |

A table or column nobody stated and no catalogue showed is `assumed`, and every test that depends on it is listed in §14.

## The Access table

One row per actor in scope, for the environment the runbook is written for:

| Actor | Where | How to get in | Source |
|---|---|---|---|
| API | `BASE_URL` = `https://api.staging.example.test` | `POST /auth/token` with `QA_ADMIN_USER` / `QA_ADMIN_PASSWORD`, role `catalogue-admin` | detected `src/Api/Program.cs:41` |
| UI-web | `WEB_URL` = `https://admin.staging.example.test` | Sign in as the same account | stated |
| UI-app | build `2.14.0 (381)` on a Pixel 8 emulator, Android 16 | Sign in as `QA_SHOPPER_USER` | stated |
| DB | PostgreSQL 17, database `catalogue_staging`, `DB_URL` | `psql "$DB_URL"`, a role with DML on schema `catalog` | stated |

Each account is named with its role. Each secret is the name of the variable that holds it. The database row names the database, because the run checks that name before its first statement. The runbook's header repeats the environment, the build and its commit, the device and the accounts, so a reader knows what it was written for before reading a step.
