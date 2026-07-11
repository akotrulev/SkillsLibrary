# SQL Server — Data modeling (schemas, relationships, keys, constraints, temporal)

SQL Server-specific modeling mechanics. Cross-engine *decisions* — id strategy, money as minor units, soft-delete policy, multi-tenancy pattern choice, embed-vs-reference — live in `data/_shared/schema-design`; apply those defaults here, don't re-derive them. Tenant isolation enforcement (RLS) → `references/security.md`.

## Normalization first

- **Normalize to 3NF by default.** Denormalize only with a measured query, its actual execution plan, and evidence the join is the cost.
- Acceptable denormalizations, in preference order: a **covering index** (`INCLUDE`, often removes the lookup, no schema change) → an **indexed view** (`references/caching.md`) → a maintained duplicate column via a trigger or app-side dual-write (last resort, document the invariant).

## Identifiers

- Default surrogate key: **`bigint IDENTITY(1,1)`**. `int IDENTITY` runs out at ~2.1B — start at `bigint` unless the table is provably small and static.
- Need client-generated / unguessable / cross-service ids → GUID, but mind the clustering cost:
  - `uniqueidentifier DEFAULT NEWSEQUENTIALID()` keeps B-tree locality (sequential-ish) — safe to cluster.
  - `NEWID()` is random → catastrophic fragmentation if clustered. If ids must be truly random, keep a **`bigint IDENTITY` clustered surrogate** and put a **non-clustered** unique index on the GUID.
- `SEQUENCE` objects when a key must be shared across tables or pre-fetched in blocks — never mix `IDENTITY` and `SEQUENCE` for the same logical key.
- Natural keys only for stable reference data (currency/country codes).

## The clustered-index decision (SQL Server-specific, do it deliberately)

Every table stores its rows **in** the clustered index (it *is* the table); every non-clustered index carries the clustering key as its row locator. So the clustered key should be **narrow, static, ever-increasing, unique**:

- Usually the PK (`bigint IDENTITY`) — narrow + monotonic + unique, the ideal.
- **Append-mostly / time-series** tables often cluster on the date column instead (range scans by date become sequential) — but then the PK is a *non-clustered* constraint.
- A wide/random clustered key (GUID, multi-column natural key) bloats **every** non-clustered index and fragments on insert. Avoid.
- Heaps (no clustered index) only for transient staging/bulk-load tables.

## Timestamps

- `datetime2(7)` over legacy `datetime` (lower precision, larger, 1753 floor).
- `datetimeoffset(7)` when the zone must be preserved; otherwise store UTC and render in the app.
- `SYSUTCDATETIME()` for defaults.

## Relationship patterns

| Relationship | Shape |
|---|---|
| 1:1 | Same table unless the extension is sparse/optional or has a different security profile → separate table, PK is also the FK: `ProfileId bigint PRIMARY KEY REFERENCES Users(Id) ON DELETE CASCADE` |
| 1:N | FK on the many side, `NOT NULL` unless orphan is a real domain state |
| M:N | Junction table with a **composite PK** `(AId, BId)`; add the reverse-order index `(BId, AId)` for lookups from the other side |
| Self-referencing hierarchy | `ParentId` FK to own PK; query with a recursive CTE, or use the **`hierarchyid`** type for deep path-heavy trees |
| Polymorphic ("belongs to an Order OR an Invoice") | Avoid a `(OwnerType, OwnerId)` pair — no FK integrity. Prefer one nullable FK per target + a `CHECK` that exactly one is set |

## Foreign keys

Unlike Postgres, SQL Server also **does not auto-index FK columns** — index every FK column explicitly. It serves your joins and the referenced table's DELETE/UPDATE (which otherwise scans the child table).

```sql
CustomerId bigint NOT NULL
    CONSTRAINT FK_Orders_Customers REFERENCES dbo.Customers(Id);
CREATE NONCLUSTERED INDEX IX_Orders_CustomerId ON dbo.Orders (CustomerId);
```

### `ON DELETE` / `ON UPDATE` decision matrix — always explicit

| Action | Semantics | Use when |
|---|---|---|
| `NO ACTION` (implicit default) | Delete of parent fails if children exist | Make it visible — write it, or use `RESTRICT`-style intent |
| `CASCADE` | Children deleted with parent | True composition only (Order → OrderLines). **SQL Server forbids multiple cascade paths to the same table** — a diamond of cascades is a hard error; break it with a trigger or app logic |
| `SET NULL` | FK nulled on parent delete | Optional association where orphan is meaningful — column must be nullable |
| `SET DEFAULT` | FK reset to a default row | Rare; "reassign to Unassigned" |

SQL Server has no deferrable constraints (unlike Postgres). For circular refs / reorder-within-transaction, either make one FK nullable and set it in a second statement, or wrap the two writes and disable/re-enable `WITH CHECK` inside the transaction (last resort).

### Composite FK for tenant integrity

When a child must belong to the same tenant as its parent, a composite FK enforces it at the engine (requires a `UNIQUE (TenantId, Id)` on the parent):

```sql
CONSTRAINT FK_OrderLines_Orders
    FOREIGN KEY (TenantId, OrderId) REFERENCES dbo.Orders (TenantId, Id)
```

Cheapest cross-table tenant-integrity guarantee; complements RLS (`references/security.md`).

## Enum strategy — CHECK vs lookup table

SQL Server has **no native enum type.** Two options:

| | `CHECK (Col IN (...))` | Lookup table + FK |
|---|---|---|
| Add a value | One migration | `INSERT` |
| Payload (display name, sort order) | No | Yes |
| **Verdict** | **Default** for small closed sets | Values that grow or carry attributes |

## JSON

- **2025**: native `json` data type + JSON indexes — use it for genuinely variable-shape payloads; index the paths you filter on.
- **2022 / 2019**: store JSON in `nvarchar(max)` with `CONSTRAINT CHECK (ISJSON(Col) = 1)`; query with `JSON_VALUE`/`OPENJSON`; promote frequently-filtered fields to **computed columns** and index those:

```sql
Metadata      nvarchar(max) NOT NULL CONSTRAINT CK_Orders_Metadata CHECK (ISJSON(Metadata) = 1),
Region        AS JSON_VALUE(Metadata, '$.region') PERSISTED,   -- promote + index
```

- Never use JSON as a substitute for a real column or a junction table.

## Constraint catalog

- `CHECK` for value rules — cheap, always on: `CHECK (TotalMinor >= 0)`, `CHECK (PaidAt IS NULL OR PaidAt >= PlacedAt)`.
- **Filtered unique index** for "unique among the live ones": `CREATE UNIQUE INDEX UX_Users_Email ON dbo.Users (Email) WHERE DeletedAt IS NULL;` (SQL Server treats each NULL as distinct in a plain unique index — a filtered unique index is also the "one active default per user" tool).
- `rowversion` column for optimistic concurrency (EF Core maps it natively; never write to it).
- Name every constraint explicitly (`CK_Orders_TotalNonNeg`, `DF_Orders_PlacedAt`) — auto-generated names make future migrations guesswork and break scripted drops.

## Sample DDL (the house shape)

```sql
CREATE TABLE dbo.Orders (
    Id           bigint       IDENTITY(1,1) NOT NULL,
    TenantId     bigint       NOT NULL,
    CustomerId   bigint       NOT NULL,
    Status       nvarchar(20) NOT NULL CONSTRAINT CK_Orders_Status
                     CHECK (Status IN ('Pending','Paid','Cancelled','Refunded')),
    TotalMinor   bigint       NOT NULL CONSTRAINT CK_Orders_TotalMinor CHECK (TotalMinor >= 0),
    Currency     char(3)      NOT NULL,
    PlacedAt     datetime2(7) NOT NULL CONSTRAINT DF_Orders_PlacedAt DEFAULT SYSUTCDATETIME(),
    PaidAt       datetime2(7)     NULL CONSTRAINT CK_Orders_PaidAt CHECK (PaidAt IS NULL OR PaidAt >= PlacedAt),
    RowVersion   rowversion   NOT NULL,
    CONSTRAINT PK_Orders PRIMARY KEY CLUSTERED (Id),
    CONSTRAINT UQ_Orders_Tenant UNIQUE (TenantId, Id),   -- backs composite tenant FKs
    CONSTRAINT FK_Orders_Customers FOREIGN KEY (CustomerId) REFERENCES dbo.Customers(Id)
);
CREATE NONCLUSTERED INDEX IX_Orders_Tenant_Customer ON dbo.Orders (TenantId, CustomerId);
CREATE NONCLUSTERED INDEX IX_Orders_PlacedAt        ON dbo.Orders (PlacedAt DESC) INCLUDE (Status, CustomerId);
```

Money as `bigint` minor units + `currency char(3)`; `datetime2` everywhere; every FK indexed; every FK's action explicit; clustered index chosen (here the monotonic `Id`).

## Temporal (system-versioned) tables — full queryable history

When "what did this row look like at time X" is a **modeling requirement** (pricing, contracts, config with effective dates) — SQL Server's built-in system-versioning is the house pattern (distinct from a lighter audit *log* of who changed what → `references/security.md`):

```sql
CREATE TABLE dbo.Prices (
    Id          bigint IDENTITY(1,1) PRIMARY KEY,
    ProductId   bigint NOT NULL,
    PriceMinor  bigint NOT NULL,
    ValidFrom   datetime2(7) GENERATED ALWAYS AS ROW START NOT NULL,
    ValidTo     datetime2(7) GENERATED ALWAYS AS ROW END   NOT NULL,
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = dbo.PricesHistory));
```

The engine maintains the history table automatically on every UPDATE/DELETE. Point-in-time query: `SELECT ... FROM dbo.Prices FOR SYSTEM_TIME AS OF '2026-01-01'`. No triggers, no app code. Index the history table (default clustered on `(ValidTo, ValidFrom)`) for your query shape; set a retention policy on the history table so it doesn't grow forever.

## Anti-patterns

- FK column without an index (scans the child table on parent delete).
- Random GUID (`NEWID()`) as the clustered key — fragments the whole table and every non-clustered index.
- Implicit `NO ACTION` because nobody decided the delete behavior.
- Multiple cascade paths to one table (SQL Server rejects it — design around it up front).
- `(OwnerType, OwnerId)` polymorphic pairs with no FK.
- Structured, frequently-queried fields buried in JSON `nvarchar(max)` with no computed-column promotion.
- Unnamed constraints (unscriptable, unguessable in migrations).
- `int IDENTITY` on a table that will exceed 2.1B rows.
- Hand-rolled history triggers where system-versioned temporal tables would do.
