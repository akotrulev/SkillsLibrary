# Trace Recipes — where business rules actually hide

A rule you do not find is a rule your documentation silently claims does not exist. This file is the checklist of places rules hide, and the search patterns that surface them, per stack and per surface.

Take the stack and version from the orientation pass. Searching for idioms the project's version does not use under-reports, and under-reporting is invisible — nothing tells you the rule was there.

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
grep -rn '\[Http\(Get\|Post\|Put\|Patch\|Delete\)\|\[Route\|MapGet\|MapPost\|MapPut\|MapDelete\|MapGroup' --include=*.cs src/
# authorization
grep -rn '\[Authorize\|RequireClaim\|RequireRole\|AddPolicy\|IAuthorizationHandler\|\[AllowAnonymous\]' --include=*.cs src/
# validation
grep -rn 'AbstractValidator\|RuleFor\|\[Required\]\|\[Range\|\[MaxLength\|\[RegularExpression\|ValidationAttribute' --include=*.cs src/
# business rules — guard clauses and domain failures
grep -rn 'throw new \(Domain\|Business\|Invalid\|Validation\)\|Result\.Fail\|return BadRequest\|return Conflict' --include=*.cs src/
# scheduled work + consumers
grep -rn 'BackgroundService\|IHostedService\|RecurringJob\|CronSchedule\|IConsumer<\|IHandleMessages' --include=*.cs src/
# persistence rules
grep -rn 'HasCheckConstraint\|HasIndex\|IsUnique\|HasDefaultValue\|OnDelete\|HasQueryFilter\|IsConcurrencyToken\|IsRowVersion' --include=*.cs src/
# silent rules
grep -rn 'Math.Round\|MidpointRounding\|DateTime.Now\|DateTime.Today\|TimeZoneInfo\|\.First()\|\.OrderBy' --include=*.cs src/
```

`HasQueryFilter` is worth its own pass — it is where soft-delete and tenancy filters live, and it silently changes the meaning of *every* query in the area.

### Java 21 + Spring Boot 3.x

```bash
# entry points
grep -rn '@RestController\|@RequestMapping\|@GetMapping\|@PostMapping\|@PutMapping\|@PatchMapping\|@DeleteMapping' --include=*.java src/
# authorization
grep -rn '@PreAuthorize\|@PostAuthorize\|@Secured\|@RolesAllowed\|hasAuthority\|hasRole\|SecurityFilterChain' --include=*.java src/
# validation
grep -rn '@Valid\|@NotNull\|@NotBlank\|@Size\|@Min\|@Max\|@Pattern\|ConstraintValidator' --include=*.java src/
# business rules
grep -rn 'throw new \(Business\|Domain\|Invalid\|IllegalState\)\|ResponseStatusException' --include=*.java src/
# scheduled work + consumers
grep -rn '@Scheduled\|@KafkaListener\|@RabbitListener\|@SqsListener\|@JmsListener\|@EventListener' --include=*.java src/
# persistence rules
grep -rn '@Column(\|@Table(\|uniqueConstraints\|@Version\|@Where\|@SQLRestriction\|@Filter\|cascade =\|orphanRemoval' --include=*.java src/
# transaction boundaries — what is atomic is a business statement
grep -rn '@Transactional' --include=*.java src/
```

`@Where` / `@SQLRestriction` are the Hibernate equivalent of a global query filter — same warning as .NET's.

### Node 24 / 22 + TypeScript

```bash
# entry points — Express/Fastify and Nest both
grep -rn "router\.\(get\|post\|put\|patch\|delete\)\|app\.\(get\|post\|put\|patch\|delete\)\|@Controller\|@Get(\|@Post(\|@Put(\|@Patch(\|@Delete(" --include=*.ts src/
# authorization
grep -rn '@UseGuards\|@Roles\|CanActivate\|requireAuth\|authorize(\|passport\.' --include=*.ts src/
# validation — Zod/class-validator/Joi
grep -rn 'z\.object\|z\.string()\.\|@IsNotEmpty\|@IsEmail\|@Min(\|@Max(\|Joi\.\|\.refine(' --include=*.ts src/
# business rules
grep -rn 'throw new \(Bad\|Conflict\|Forbidden\|Unprocessable\|Domain\|Business\)\|res\.status(4' --include=*.ts src/
# scheduled work + consumers
grep -rn '@Cron\|node-cron\|schedule(\|@EventPattern\|@MessagePattern\|\.subscribe(\|consumer\.run' --include=*.ts src/
# persistence rules — Prisma/Drizzle/TypeORM
grep -rn '@@unique\|@unique\|@default\|onDelete\|@relation\|uniqueIndex(\|\.default(\|@Column(' --include=*.ts prisma/ src/
# silent rules
grep -rn 'toFixed\|Math.round\|new Date()\|Date.now()\|\.sort(\|\[0\]' --include=*.ts src/
```

Prisma's `schema.prisma` is a single high-value read: constraints, defaults, cascades and the full relational model in one file.

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
