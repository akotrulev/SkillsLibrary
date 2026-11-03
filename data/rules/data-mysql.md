---
paths:
  - "**/*.sql"
  - "**/*.prisma"
  - "**/db/migration/**"
  - "**/migrations/**"
  - "**/Migrations/**"
  - "**/db/changelog/**"
  - "**/alembic/versions/**"
  - "**/drizzle/**"
---

<!-- data rules v1 (2026-11-03): MySQL. Installed by /data:rules when the project uses MySQL, MariaDB or Aurora MySQL; narrow the paths above to this engine's files when the repo has several engines. -->

# MySQL / MariaDB / Aurora MySQL standards (8.4 LTS primary, 9.x supported, 8.0 legacy)

Severity tags as in the core data rules. MariaDB is a fork: check each feature for it rather than assuming MySQL behaviour.

- InnoDB, never MyISAM; `utf8mb4`, never `utf8`; one collation across joined columns. *major*
- An explicit primary key on every table: `BIGINT UNSIGNED AUTO_INCREMENT`, or UUIDv7 as `BINARY(16)`. Never `CHAR(36)`, never a random UUIDv4 as the clustered key. *major*
- `DATETIME(6)` in UTC for events; `TIMESTAMP` only where the 2038 limit and session-zone conversion do not matter. *major*
- No native `ENUM` for a set that will be reordered or pruned; a queried JSON field is promoted to a generated column. *minor*
- Composite indexes put equality columns before the range column. There is no partial or `INCLUDE` index: put the columns in the key. A big index is made `INVISIBLE` before it is dropped. *minor*
- Online DDL: `ALGORITHM=INSTANT` where the version allows, else `ALGORITHM=INPLACE, LOCK=NONE`, else `pt-online-schema-change` or `gh-ost` for a large table, including an FK added to one. *major*
- No FK disabled "for performance" without a plan to re-enable it. *major*
- There is no row-level security: tenant isolation is one tested data-access choke point, never scattered `WHERE`s, with a mandatory cross-tenant leak test. *blocker*
- The runtime account has granular DML on its schema, never `root`, `SUPER`, `ALL PRIVILEGES` or `'app'@'%'`. No `AES_ENCRYPT` key in SQL text. *blocker*
- `max_execution_time` caps runaway `SELECT`s. *minor*
- No `query_cache_size` (removed in 8.0); no `ANALYZE TABLE` or `OPTIMIZE TABLE` on a cron. *minor*
