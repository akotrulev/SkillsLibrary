# Trace Recipes — where business rules actually hide

A rule you do not find is a rule your documentation silently claims does not exist. This file is the checklist of places rules hide, and the search patterns that surface them, per stack and per surface.

Take the stack and version from the orientation pass. Searching for idioms the project's version does not use under-reports, and under-reporting is invisible — nothing tells you the rule was there.

**Contents:**

- Part 1 — The seven hiding places (stack-agnostic)
- Part 2 — The silent-rule catalogue
- Part 3 — Per-stack search patterns
- Part 3a — Where people do things: screens, navigation, labels, forms
- Part 3b — Following a seam (the Edges inventory)
- Part 4 — Cross-stack: the git-archaeology pass
- Part 5 — Cross-stack: reading tasks from journey tests and test-case suites

---

## Part 1 — The seven hiding places (stack-agnostic)

Ordered by how often the rule exists **nowhere else**, which is the same as how badly it hurts to miss:

### 1. Guard clauses and early returns

The most common home of a business rule, and the easiest to read past because it looks like error handling.

```csharp
if (order.PlacedAt < DateTime.UtcNow.AddDays(-30))
    return Result.Fail("REFUND_WINDOW_EXPIRED");
```

That is a 30-day refund policy. Every `throw`, `return Fail`, `raise`, and `res.status(4xx)` on a business condition is a rule. Search the failure vocabulary of the project (its exception types, its error-code constants) rather than the happy path.

### 2. Database constraints, defaults and triggers

A `CHECK`, a `UNIQUE`, a `NOT NULL`, a default value, a cascade rule — each is a business rule the code may never restate. Migrations are the richest source, and they are chronological, so they also carry *when* the rule arrived.

```sql
CHECK (discount_percent BETWEEN 0 AND 40)   -- max discount is 40%, enforced nowhere in the app
```

Read the migration folder end to end for the area's tables. Cascades and `ON DELETE` behavior are business statements about what may outlive what.

### 3. Scheduled jobs

Time-driven rules exist only here: expiry, dunning, reminders, auto-cancellation, retention, reconciliation. Extract the **schedule** as part of the rule — "abandoned carts are cleared after 7 days, checked hourly" is the rule; "there is a cleanup job" is not.

### 4. Event and message handlers

Reactive rules, and the seams between areas. What an area *reacts to* defines its dependencies far more truthfully than its imports do. Note ordering assumptions and idempotency handling — both are business statements about what may happen twice.

### 5. Configuration, feature flags and per-tenant settings

A threshold in config is still a business rule; a rule behind a flag is *conditional* behavior. Record both branches, and which environments or tenants run which. Per-tenant overrides mean the "rule" is actually a default — an important distinction to get right.

### 6. Constants, enums and lookup/seed data

Named constants carry policy (`MaxLoginAttempts = 5`). Enums carry the state vocabulary. Seed data carries the reference model — roles, permissions, categories, statuses — and is often the only place the *complete* list exists.

### 7. Tests

Tests describe intended behavior in something close to business language, and test names frequently state the rule outright (`Should_Reject_Refund_When_Order_Older_Than_30_Days`). They are **evidence of intent, not of behavior** — a test can pass against wrong code, and a skipped or deleted test is a rule that may no longer hold. Cite them for `#inferred`, never for `#observed`.

---

## Part 2 — The silent-rule catalogue

Rules nobody thinks to write down, that surface constantly in real systems and matter enormously to a business reader. Check each explicitly per area; each has a habit of being wrong in a way only a business person can catch:

| Silent rule | Where it hides | Why it matters to the business |
|---|---|---|
| **Rounding & precision** | Money math, tax, discounts, currency conversion, percentage splits | Half-up vs banker's rounding is a real financial policy that will surface in a reconciliation dispute |
| **Timezone & date boundaries** | "Today", cutoffs, expiry, reporting windows | "Orders before midnight" — whose midnight? A UTC cutoff for a European business is a policy decision |
| **Default values** | Object initializers, DB defaults, optional parameters | The default *is* the policy for every caller who does not specify one |
| **Ordering & tie-breaks** | Sorts, priority queues, "first match wins" | Which promotion applies when two are eligible is a business decision made by a `.First()` |
| **Pagination limits** | Default and max page size | Caps what a user can ever retrieve or export |
| **Retry & idempotency** | HTTP clients, consumers, job runners | Determines whether an action can happen twice — charge, email, shipment |
| **Soft delete visibility** | Query filters | Whether deleted things still appear in totals, exports, and reports |
| **Tenancy scope** | Query filters, claim reads | Who can see whose data — the highest-stakes silent rule of all |
| **Null/empty semantics** | Nullable fields, empty-collection handling | "No preferences set" vs "all preferences off" are different business states |
| **Numeric bounds** | Validation attributes, DB column types | A `smallint` quantity caps orders at 32,767 whether anyone decided that or not |
| **Concurrency resolution** | Version columns, last-write-wins | Who wins when two people edit at once |
| **Case & whitespace normalization** | Before uniqueness checks | Whether `Bob@x.com` and `bob@x.com` are one customer or two |

---

## Part 3 — Per-stack search patterns

### .NET (10 primary / 8-9 supported)

```bash
# entry points — attribute routing and minimal APIs both, the project may use either or both
grep -rn '\[Http\(Get\|Post\|Put\|Patch\|Delete\)\|\[Route\|MapGet\|MapPost\|MapPut\|MapDelete\|MapGroup' --include='*.cs' src/
# authorization
grep -rn '\[Authorize\|RequireClaim\|RequireRole\|AddPolicy\|IAuthorizationHandler\|\[AllowAnonymous\]' --include='*.cs' src/
# validation
grep -rn 'AbstractValidator\|RuleFor\|\[Required\]\|\[Range\|\[MaxLength\|\[RegularExpression\|ValidationAttribute' --include='*.cs' src/
# business rules — guard clauses and domain failures
grep -rn 'throw new \(Domain\|Business\|Invalid\|Validation\)\|Result\.Fail\|return BadRequest\|return Conflict' --include='*.cs' src/
# scheduled work + consumers
grep -rn 'BackgroundService\|IHostedService\|RecurringJob\|CronSchedule\|IConsumer<\|IHandleMessages' --include='*.cs' src/
# persistence rules
grep -rn 'HasCheckConstraint\|HasIndex\|IsUnique\|HasDefaultValue\|OnDelete\|HasQueryFilter\|IsConcurrencyToken\|IsRowVersion' --include='*.cs' src/
# silent rules
grep -rn 'Math.Round\|MidpointRounding\|DateTime.Now\|DateTime.Today\|TimeZoneInfo\|\.First()\|\.OrderBy' --include='*.cs' src/
# GraphQL + gRPC entry points — only if the survey found these surfaces
grep -rn '\[Query\]\|\[Mutation\]\|\[Subscription\]\|QueryType\|MutationType\|MapGraphQL\|MapGrpcService\|ServerCallContext' --include='*.cs' src/
# client vocabulary — resources, localizers, validation and problem-detail text, enum display names, templates
find src/ -name '*.resx' -o -name '*.cshtml' -o -name '*.liquid' -o -name '*.hbs'
grep -rn 'IStringLocalizer\|IHtmlLocalizer\|WithMessage(\|ErrorMessage =\|ProblemDetails\|Title =\|Detail =\|\[Display(Name\|\[Description(' --include='*.cs' src/
```

`HasQueryFilter` is worth its own pass — it is where soft-delete and tenancy filters live, and it silently changes the meaning of *every* query in the area.

### Java 21 + Spring Boot 3.x

```bash
# entry points
grep -rn '@RestController\|@RequestMapping\|@GetMapping\|@PostMapping\|@PutMapping\|@PatchMapping\|@DeleteMapping' --include='*.java' src/
# authorization
grep -rn '@PreAuthorize\|@PostAuthorize\|@Secured\|@RolesAllowed\|hasAuthority\|hasRole\|SecurityFilterChain' --include='*.java' src/
# validation
grep -rn '@Valid\|@NotNull\|@NotBlank\|@Size\|@Min\|@Max\|@Pattern\|ConstraintValidator' --include='*.java' src/
# business rules
grep -rn 'throw new \(Business\|Domain\|Invalid\|IllegalState\)\|ResponseStatusException' --include='*.java' src/
# scheduled work + consumers
grep -rn '@Scheduled\|@KafkaListener\|@RabbitListener\|@SqsListener\|@JmsListener\|@EventListener' --include='*.java' src/
# persistence rules
grep -rn '@Column(\|@Table(\|uniqueConstraints\|@Version\|@Where\|@SQLRestriction\|@Filter\|cascade =\|orphanRemoval' --include='*.java' src/
# transaction boundaries — what is atomic is a business statement
grep -rn '@Transactional' --include='*.java' src/
# GraphQL + gRPC entry points — only if the survey found these surfaces
grep -rn '@QueryMapping\|@MutationMapping\|@SchemaMapping\|@SubscriptionMapping\|DataFetcher\|@GrpcService\|extends .*ImplBase' --include='*.java' src/
# client vocabulary — message bundles, constraint messages, problem details, templates
find src/ -name 'messages*.properties' -o -name 'ValidationMessages*.properties' -o -path '*templates*' -name '*.html'
grep -rn 'message = "\|MessageSource\|getMessage(\|ProblemDetail\|setTitle(\|setDetail(\|forStatusAndDetail' --include='*.java' src/
```

`@Where` / `@SQLRestriction` are the Hibernate equivalent of a global query filter — same warning as .NET's.

### Node 24 / 22 + TypeScript

```bash
# entry points — Express/Fastify and Nest both
grep -rn "router\.\(get\|post\|put\|patch\|delete\)\|app\.\(get\|post\|put\|patch\|delete\)\|@Controller\|@Get(\|@Post(\|@Put(\|@Patch(\|@Delete(" --include='*.ts' src/
# authorization
grep -rn '@UseGuards\|@Roles\|CanActivate\|requireAuth\|authorize(\|passport\.' --include='*.ts' src/
# validation — Zod/class-validator/Joi
grep -rn 'z\.object\|z\.string()\.\|@IsNotEmpty\|@IsEmail\|@Min(\|@Max(\|Joi\.\|\.refine(' --include='*.ts' src/
# business rules
grep -rn 'throw new \(Bad\|Conflict\|Forbidden\|Unprocessable\|Domain\|Business\)\|res\.status(4' --include='*.ts' src/
# scheduled work + consumers
grep -rn '@Cron\|node-cron\|schedule(\|@EventPattern\|@MessagePattern\|\.subscribe(\|consumer\.run' --include='*.ts' src/
# persistence rules — Prisma/Drizzle/TypeORM
grep -rn '@@unique\|@unique\|@default\|onDelete\|@relation\|uniqueIndex(\|\.default(\|@Column(' --include='*.ts' prisma/ src/
# silent rules
grep -rn 'toFixed\|Math.round\|new Date()\|Date.now()\|\.sort(\|\[0\]' --include='*.ts' src/
# GraphQL + gRPC entry points — only if the survey found these surfaces
grep -rn '@Resolver\|@Query(\|@Mutation(\|@ResolveField\|@Subscription(\|@GrpcMethod\|@GrpcStreamMethod\|loadPackageDefinition' --include='*.ts' src/
# client vocabulary — i18n/locales JSON, class-validator and Zod messages, exception text, templates
find . -path ./node_modules -prune -o \( -path '*locales*' -o -path '*i18n*' \) -name '*.json' -print
grep -rn "message: ['\"]\|{ message\|i18n\.t(\|\bt(['\"]\|new \w*Exception(['\"]\|\.hbs\|\.mjml" --include='*.ts' src/
```

Prisma's `schema.prisma` is a single high-value read: constraints, defaults, cascades and the full relational model in one file.

### Rust — axum 0.8 (actix-web where the project uses it) + sqlx

`<crates>` is where the workspace keeps its code (`src/`, `crates/`); never `target/`.

```bash
# entry points — axum routers (0.8 writes paths `/{id}`; 0.7 and older `/:id`), actix-web attribute macros
grep -rn 'Router::new()\|\.route(\|\.nest(\|\.merge(\|#\[\(get\|post\|put\|patch\|delete\)(' --include='*.rs' <crates>
# authorization — custom extractors, middleware and tower layers
grep -rn 'FromRequestParts\|middleware::from_fn\|route_layer(\|\.layer(\|Claims\|Permission\|Role::' --include='*.rs' <crates>
# validation — validator / garde derives, TryFrom newtypes
grep -rn '#\[validate(\|#\[garde(\|\.validate()\|impl TryFrom<' --include='*.rs' <crates>
# business rules — error enums, early returns, anyhow's bail!/ensure!
grep -rn '#\[error(\|return Err(\|bail!(\|ensure!(\|StatusCode::\(BAD_REQUEST\|CONFLICT\|FORBIDDEN\|UNPROCESSABLE_ENTITY\)' --include='*.rs' <crates>
# scheduled work + consumers
grep -rn 'tokio::spawn\|time::interval(\|JobScheduler\|Job::new_async\|StreamConsumer\|basic_consume\|\.subscribe(\|receive_message()' --include='*.rs' <crates>
# persistence rules — the migrations hold the constraints; the macros hold the SQL a job selects with
grep -rni 'check *(\|unique\|default \|references \|on delete\|create trigger' migrations/
grep -rn 'query!(\|query_as!(\|query_scalar!(\|DeriveEntityModel\|#\[sea_orm(\|diesel::table!' --include='*.rs' <crates>
# silent rules
grep -rn '\.round()\|round_dp(\|Utc::now()\|Local::now()\|OffsetDateTime::now_utc()\|\.first()\|\.sort\|unwrap_or(' --include='*.rs' <crates>
# GraphQL + gRPC entry points — only if the survey found these surfaces
grep -rn '#\[Object\]\|SimpleObject\|async_graphql::\|#\[tonic::async_trait\]\|tonic::transport::Server' --include='*.rs' <crates>
# client vocabulary — Fluent / i18n files, error Display text, templates
find . -path ./target -prune -o \( -name '*.ftl' -o -path '*locales*' -name '*.y*ml' -o -path '*templates*' -name '*.html' \) -print
grep -rn '#\[error("\|t!("\|#\[template(' --include='*.rs' <crates>
```

`migrations/*.sql` is the single high-value read: `CHECK`, `UNIQUE`, defaults and foreign keys in one place. Rounding is a convention to record: `f64::round` rounds half away from zero, `rust_decimal`'s `round_dp` rounds half to even.

### Python 3.12–3.14 — FastAPI, Flask, Django / DRF

`<pkg>` is the project's package root (`src/<pkg>/` or `<pkg>/`); never `.venv/`.

```bash
# entry points — FastAPI and Flask decorators, Django URLconfs and DRF views
grep -rn '@\(app\|router\|bp\|api\)\.\(get\|post\|put\|patch\|delete\|route\)(\|APIRouter(\|urlpatterns\|re_path(\|@api_view\|ViewSet)\|@action(' --include='*.py' <pkg>
# authorization
grep -rn 'Depends(\|Security(\|@login_required\|@permission_required\|permission_classes\|has_permission\|has_object_permission' --include='*.py' <pkg>
# validation — pydantic, DRF serializers, marshmallow
grep -rn 'Field(\|@field_validator\|@model_validator\|Annotated\[\|def validate_\|validate=' --include='*.py' <pkg>
# business rules
grep -rn 'raise \w*\(Error\|Exception\|Denied\)\|raise HTTPException\|abort(4\|status_code=4' --include='*.py' <pkg>
# scheduled work + consumers — Celery, APScheduler, Dramatiq, Kafka / RabbitMQ / SQS clients
grep -rn '@shared_task\|@\w*\.task\|beat_schedule\|crontab(\|add_job(\|scheduled_job\|@dramatiq\.actor\|AIOKafkaConsumer\|basic_consume\|receive_message(' --include='*.py' <pkg>
# persistence rules — SQLAlchemy / Alembic, Django models and migrations
grep -rn 'CheckConstraint\|UniqueConstraint\|unique=True\|server_default\|ondelete=\|on_delete=\|constraints = \[\|create_check_constraint\|create_unique_constraint' --include='*.py' <pkg> migrations/ alembic/ 2>/dev/null
# silent rules
grep -rn 'round(\|quantize(\|ROUND_\|datetime\.now()\|datetime\.utcnow()\|date\.today()\|sorted(\|\[0\]' --include='*.py' <pkg>
# GraphQL + gRPC entry points — only if the survey found these surfaces
grep -rn '@strawberry\.\|graphene\.\|ariadne\|_to_server(\|grpc\.aio\.server' --include='*.py' <pkg>
# client vocabulary — gettext catalogues, model labels and choices, error detail text, templates
find . -path ./.venv -prune -o \( -name '*.po' -o -path '*templates*' -name '*.html' \) -print
grep -rn 'gettext(\|_("\|verbose_name\|choices=\|TextChoices\|detail="\|message="' --include='*.py' <pkg>
```

Rounding is a convention to record: `round()` rounds half to even (`round(2.5) == 2`), and `Decimal.quantize` uses the context's rounding unless `rounding=` is passed.

---

## Part 3a — Where people do things: screens, navigation, labels, forms

The Tasks inventory and the guide name the screen and control a person uses (`**Where:** **Your orders** → **Cancel order**`), and a label is evidence: record it in the Tasks row's *Screen › control* and in `Client vocabulary` only from a route or navigation entry you read. A search that finds no screen is recorded as the search, never as a guess. Per UI stack, four questions: where screens and navigation are declared, where labels and messages live, where forms and their validation text live, and which entry point a screen calls. The same searches serve the targeted lookup when an old-shape set is updated in place.

### React — Next.js App Router (Pages Router: `pages/`) and Vite + React Router

```bash
# screens and navigation — Next: a route is a folder holding page.tsx
find app pages -name 'page.*' -o -name 'layout.*' -o -name 'route.*' 2>/dev/null | sort
grep -rn "<Link\|href=\|redirect(\|router\.push\|usePathname" --include='*.tsx' --include='*.ts' app components 2>/dev/null
# screens and navigation — Vite: the route table, then the navigation that points into it
grep -rn "createBrowserRouter\|<Route \|path: ['\"]\|<NavLink\|<Link \|useNavigate" --include='*.tsx' --include='*.ts' src/
# labels and messages — locale files first, then literals beside the control
find . -path ./node_modules -prune -o \( -path '*locales*' -o -path '*messages*' -o -path '*i18n*' \) -name '*.json' -print
grep -rn "useTranslations\|getTranslations\|useTranslation\|\bt(['\"]\|aria-label=\|<button\|<Button\|title=" --include='*.tsx' app/ src/ components/ 2>/dev/null
# forms and validation text — schema messages are the refusal texts
grep -rn "useForm\|zodResolver\|useActionState\|z\.\(string\|number\|object\)\|message: ['\"]" --include='*.tsx' --include='*.ts' app/ src/ components/ lib/ 2>/dev/null
# screen → entry point — server action, route handler, typed client or fetch behind the submit handler
grep -rn "'use server'\|fetch(\|useMutation\|useQuery\|apiClient\.\|client\.\(GET\|POST\|PUT\|PATCH\|DELETE\)" --include='*.tsx' --include='*.ts' app/ src/ components/ lib/ 2>/dev/null
```

### Blazor

```bash
# screens and navigation — @page routes, NavLink menus, programmatic navigation
grep -rn "^@page\|<NavLink\|NavigateTo(" --include='*.razor' .
# labels and messages — resource files and localizers, then literals
find . -name '*.resx' -not -path './bin/*' -not -path './obj/*'
grep -rn "IStringLocalizer\|Localizer\[\|@Loc\[\|<button\|<FluentButton\|<MudButton" --include='*.razor' --include='*.cs' .
# forms and validation text — EditForm, DataAnnotations and FluentValidation messages
grep -rn "<EditForm\|<ValidationMessage\|<ValidationSummary\|DataAnnotationsValidator\|ErrorMessage =\|WithMessage(" --include='*.razor' --include='*.cs' .
# screen → entry point — a typed HttpClient, or an injected application service when the circuit runs server-side
grep -rn "@inject\|\[Inject\]\|GetFromJsonAsync\|PostAsJsonAsync\|HttpClient" --include='*.razor' --include='*.cs' .
```

### React Native — Expo Router

```bash
# screens and navigation — files under app/ are routes; (group) folders and _layout.tsx hold Stack and Tabs
find app -name '*.tsx' | sort
grep -rn "<Stack\.Screen\|<Tabs\.Screen\|<Link\|router\.\(push\|replace\|navigate\)\|href=" --include='*.tsx' --include='*.ts' app/ src/ components/
# labels and messages — locale files, then literals beside the control
find . -path ./node_modules -prune -o \( -path '*locales*' -o -path '*i18n*' -o -path '*translations*' \) -name '*.json' -print
grep -rn "useTranslation\|\bt(['\"]\|accessibilityLabel=\|title=\|<Text>" --include='*.tsx' app/ src/ components/
# forms and validation text
grep -rn "useForm\|zodResolver\|z\.\(string\|number\|object\)\|message: ['\"]\|<TextInput" --include='*.tsx' --include='*.ts' app/ src/ components/
# screen → entry point — query hooks and the API client behind the handler
grep -rn "useMutation\|useQuery\|fetch(\|apiClient\.\|client\.\(GET\|POST\|PUT\|PATCH\|DELETE\)" --include='*.tsx' --include='*.ts' app/ src/
```

### SwiftUI

```bash
# screens and navigation — views, stacks, tabs, destinations and presented sheets
grep -rn ": View {\|NavigationStack\|NavigationSplitView\|NavigationLink\|\.navigationDestination\|TabView\|\.sheet(\|\.fullScreenCover(" --include='*.swift' .
# labels and messages — string catalogs (or legacy .strings), then literals beside the control
find . -name '*.xcstrings' -o -name 'Localizable.strings' -o -name '*.stringsdict'
grep -rn "Text(\"\|Button(\"\|Label(\"\|String(localized:\|LocalizedStringKey\|\.navigationTitle(" --include='*.swift' .
# forms and validation text — Form, TextField, alerts, LocalizedError descriptions
grep -rn "Form {\|TextField(\|\.alert(\|errorDescription\|LocalizedError" --include='*.swift' .
# screen → entry point — the view model or service the button's action awaits, down to the API client
grep -rn "\.task {\|Task {\|URLSession\|APIClient\|@Observable" --include='*.swift' .
```

### Jetpack Compose

```bash
# screens and navigation — the NavHost graph, route definitions, bottom bar
grep -rn "NavHost\|composable(\|composable<\|navigation(\|navigate(\|NavigationBar\|NavigationBarItem" --include='*.kt' .
# labels and messages — strings.xml per locale, then stringResource at the control
find . -path '*/res/values*' -name 'strings.xml' -not -path '*/build/*'
grep -rn "stringResource(\|pluralStringResource(\|R\.string\." --include='*.kt' .
# forms and validation text — fields, their error state and supporting text
grep -rn "OutlinedTextField\|TextField(\|supportingText\|isError" --include='*.kt' .
# screen → entry point — ViewModel → repository → the Retrofit interface or Ktor call
grep -rn "@GET(\|@POST(\|@PUT(\|@PATCH(\|@DELETE(\|httpClient\.\(get\|post\|put\|patch\|delete\)\|collectAsStateWithLifecycle" --include='*.kt' .
```

Read the route to the screen that holds the control and the navigation entry that reaches it; the path is `<menu or screen title> › <control text>`. A control whose text lives in a translation file is cited by the file's value for the project's default language. **Screen to entry point:** follow the control's handler to the client call and match its method and path (or action name) to the backend entry point; that pair is a Tasks row's *Entry points it calls*. When the client app is in another repository, the backend alone shows no screen: record the negative search per task.

### Server-rendered pages — Razor, Thymeleaf, Django / Jinja, askama

```bash
# screens — the page or view, and the route that serves it
find . \( -name '*.cshtml' -o -path '*templates*' -name '*.html' -o -name '*.jinja*' \) -not -path '*/node_modules/*' -not -path './.venv/*' -not -path './target/*'
grep -rn '@page\|return View(\|"redirect:\|render(request\|render_template(\|TemplateResponse(\|#\[template(' .
# labels and forms — the template's literals and form fields, then the server-side validation text
grep -rn '<label\|<button\|<a \|asp-for=\|th:text=\|{% trans\|{{ _(\|{{ form\.' --include='*.cshtml' --include='*.html' --include='*.jinja*' .
```

A server-rendered form posts to the route that rendered it, or to its `action=`: that route is the entry point the Tasks row names.

---

## Part 3b — Following a seam (the Edges inventory)

Stop 9 and the Edges inventory need three answers per emitted event or written field: **who reacts**, **who reads**, and **how the reaction runs**. Take the emitted type's name and its string form (topic, queue, routing key, event name) and search both.

**Reading the mode from the code.** Record only what is visible; everything else is `?`:

| What the code shows | Mode | Delivery guarantee |
|---|---|---|
| The handler is called by the publisher before the request's save or commit | `in request` | — (it rolls back with the request) |
| An in-process listener bound to the commit (after-commit phase, dispatch after `SaveChanges`) | `after commit` | `?` unless a retry or a persisted queue is visible — a listener with no retry loses the event if the process dies, which is a finding, not a guarantee |
| An outbox table written in the request's transaction, drained by a relay | `after commit` | at-least-once **only** where the relay's retry or redelivery is in the code; the retry count and the dead-letter route are the *On failure* |
| A broker consumer | `after commit` | The broker's name proves nothing. Record at-least-once where a retry policy, a negative acknowledgement or a redelivery setting is visible; record exactly-once never from a library claim alone; otherwise `?` |
| A consumer that checks a processed-id, idempotency key or unique constraint before acting | — | Note the key: it is the invariant's *Enforced* cell |
| A schedule's handler | `scheduled` | Look for a run marker or lock; none found is `?` for a re-run, with the search named |

**Readers of a field.** Search the field's property, column and serialized names; then read the `Where`/`Select` clauses and raw SQL of every scheduled job and report, because a job's selection is a read the rest of the code never shows.

### .NET

```bash
# consumers of an event type — in-process notifications and broker consumers
grep -rn 'INotificationHandler<Event>\|IDomainEventHandler<Event>\|IConsumer<Event>\|IHandleMessages<Event>' --include='*.cs' src/
# publishers and dispatch moment — in request, or after SaveChanges
grep -rn 'Publish(\|PublishAsync(\|DomainEvents\|SaveChangesInterceptor\|AddEntityFrameworkOutbox\|UseBusOutbox\|OutboxMessage' --include='*.cs' src/
# retry and idempotency evidence
grep -rn 'UseMessageRetry\|UseDelayedRedelivery\|Polly\|ProcessedMessage\|IdempotencyKey' --include='*.cs' src/
# readers of a field, including jobs
grep -rn '\.<Field>\b' --include='*.cs' src/ | grep -i 'Where\|Select\|OrderBy\|Job\|Worker'
```

### Java 21 + Spring Boot 3.x

```bash
# consumers
grep -rn '@EventListener\|@TransactionalEventListener\|@KafkaListener\|@RabbitListener\|@SqsListener\|@JmsListener' --include='*.java' src/
# dispatch moment — AFTER_COMMIT is the default phase of @TransactionalEventListener
grep -rn 'publishEvent(\|@TransactionalEventListener\|phase =\|outbox\|Outbox' --include='*.java' src/
# retry and idempotency evidence
grep -rn '@Retryable\|RetryTemplate\|DefaultErrorHandler\|@DltHandler\|DeadLetter\|processed_message\|idempotenc' --include='*.java' src/
# readers of a field, including jobs and repository queries
grep -rn '<field>\|findBy<Field>\|@Query' --include='*.java' src/
```

### Node 24 / 22 + TypeScript

```bash
# consumers
grep -rn "@OnEvent(\|@EventPattern(\|@MessagePattern(\|\.on(['\"]<event>\|consumer\.run\|new Worker(" --include='*.ts' src/
# dispatch moment — emitted inside the request, or from an outbox relay
grep -rn 'emit(\|emitAsync(\|eventEmitter\|outbox\|queue\.add(' --include='*.ts' src/
# retry and idempotency evidence
grep -rn 'attempts:\|backoff\|removeOnFail\|deadLetter\|processedMessage\|idempotencyKey' --include='*.ts' src/
# readers of a field, including jobs
grep -rn '<field>' --include='*.ts' src/
```

A Node `EventEmitter` is synchronous and in-process: its handlers run `in request` unless the emit sits after the commit. A queue's own retry settings (BullMQ `attempts`, `backoff`) are the visible retry; without them the guarantee is `?`.

### Rust

```bash
# consumers — in-process channels and broker consumers
grep -rn 'broadcast::channel\|mpsc::channel\|\.recv()\|StreamConsumer\|basic_consume\|\.subscribe(' --include='*.rs' <crates>
# dispatch moment — sent inside the transaction, after tx.commit(), or by an outbox relay
grep -rn '\.send(\|\.commit()\|\.begin()\|outbox\|FutureProducer\|basic_publish' --include='*.rs' <crates>
# retry and idempotency evidence
grep -rni 'backoff\|retry\|on conflict\|idempotenc\|processed_' --include='*.rs' --include='*.sql' <crates> migrations/
# readers of a field — the column name inside query!/query_as! SQL as well as the struct field
grep -rn '<field>' --include='*.rs' --include='*.sql' <crates> migrations/
```

A `tokio::spawn` after `commit()` runs `after commit` with no retry: the task dies with the process, so the guarantee is `?` and the possible loss is a finding.

### Python

```bash
# consumers — Django signals, Celery / Dramatiq tasks, broker consumers
grep -rn '@receiver(\|post_save\|pre_save\|@shared_task\|@\w*\.task\|@dramatiq\.actor\|AIOKafkaConsumer\|basic_consume' --include='*.py' <pkg>
# dispatch moment — inside the atomic block, or on commit
grep -rn '\.delay(\|\.apply_async(\|send_task(\|on_commit(\|\.send(\|publish(\|outbox' --include='*.py' <pkg>
# retry and idempotency evidence
grep -rn 'autoretry_for\|retry_backoff\|max_retries\|self\.retry(\|acks_late\|idempotenc\|processed_' --include='*.py' <pkg>
# readers of a field, including tasks and reports
grep -rn '<field>' --include='*.py' <pkg>
```

A Django `post_save` receiver runs `in request`, inside the save's transaction; `transaction.on_commit(...)` is `after commit`. A `.delay()` inside an atomic block can run before the commit and miss the row, which is a finding. Celery acknowledges on receipt unless `acks_late` is set: without it a worker crash loses the task, so the guarantee is `?`.

---

## Part 4 — Cross-stack: the git-archaeology pass

When a rule's purpose is not recoverable from the code, before you give up and file an open question:

```bash
git log -S'<the magic constant>' --oneline          # when did 30 arrive, and in what commit
git log --follow --oneline -- <path/to/file>        # the file's story
git log -1 --format='%an %ad%n%s%n%b' <sha>         # the full message — often names the ticket
git blame -L <start>,<end> <file>                   # who and when, for the exact lines
```

A commit message naming a ticket or stating the reason upgrades an unknown to a solid `#inferred` with a citation. It is still not `#confirmed` — a commit message is one engineer's understanding at one moment, and that is exactly what an open question to the business is for.

---

## Part 5 — Cross-stack: reading tasks from journey tests and test-case suites

When the repository has journey (end-to-end) tests or `docs/test-cases/` suites, they list what people do in nearly the person's own words, and they are the second source for the Tasks inventory (after the UI, before the experience plan).

```bash
# journey tests — Playwright / Cypress specs, Gherkin features, Appium and Maestro flows
find . -path ./node_modules -prune -o \( -name '*.spec.ts' -o -name '*.e2e.*' -o -name '*.feature' -o -path '*e2e*' -o -path '*journeys*' -o -path '*.maestro*' \) -print
grep -rn "Feature:\|Scenario:\|test(\|test.describe(\|\[Test\]\|@Test" <the journey folders>
# page objects — a method name is a person's action
grep -rn "async \w*(\|public \(async \)\?\(Task\|void\) \w*(" <the page-object folders>
# test-case suites — one per story, cases citing the story and criterion
ls docs/test-cases/
grep -n "^## \|^### \|TC-\|US[0-9]\|AC[0-9]" docs/test-cases/*.md
```

- **A task is a goal, not a test.** A scenario or case whose steps run from a screen to a result a person wanted ("a member cancels a booking and sees the credits back") is a task; its boundary and refusal variants are **rules and validations**, not more tasks.
- **Steps give `screen › control`:** the page-object method, the locator's visible name (`getByRole('button', { name: 'Cancel booking' })`), the case's "click …" step. Confirm each against the UI search (Part 3a) — a control the tests name and the UI does not have is a finding.
- **Assertions give example values and refusal text:** the expected message, the number in the expected balance. Cite them as leads for the guide's example; the rule's value still comes from the code.
- **Source** is the test or case `file:line`. A case's `US<n>`/`AC<k>` citation is the stated-purpose source for `Intent notes`, and the story is read at its own file.
- A skipped or deleted test is a lead that the behavior may no longer hold: record it, never silently drop the task.
