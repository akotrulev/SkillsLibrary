---
name: rules
description: Use when installing or updating the data standards for SQL and migration files as path-scoped rules in .claude/rules/data/. Triggers "install the data rules", "set up this project". Not for schema design (schema-design).
argument-hint: "[replace | keep | beside]"
---

# Install the data rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file. A backend session writing the next migration then gets the data standards without running `data-architect`.

| File (beside this SKILL.md) | Installed | Loads when the session touches |
|---|---|---|
| `data.md`: keys, types, naming, tenancy, queries, grants, comments | always | `*.sql`, `*.prisma`, and the migration folders below |
| `data-migrations.md`: tool, forward-only, expand-contract, online DDL, backfills | always | `db/migration/`, `migrations/`, `Migrations/`, `db/changelog/`, `alembic/versions/`, `drizzle/` |
| `data-postgresql.md` | when the project uses PostgreSQL | same as `data.md` |
| `data-sqlserver.md` | when it uses SQL Server or Azure SQL | same as `data.md` |
| `data-mysql.md` | when it uses MySQL, MariaDB or Aurora MySQL | same as `data.md` |

MongoDB, Redis, DynamoDB, Cosmos DB and Elasticsearch have no rule file: their standards apply to driver code and infrastructure files with no stable path of their own, so they stay in each engine skill's `## Rules`. Migrations for those stores still get `data-migrations.md`.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/data/`.

## Run by a person or by a model

A person types `/data:rules`. A model runs this skill itself, as `data:rules`, when it is asked to set up a project or to install or update the rules, and when it finds this plugin enabled in a project that has no `.claude/rules/data/`. One argument answers the differing-file question below for every file in advance: `replace`, `keep` or `beside`.

Where a step needs the user's answer or agreement and nobody is there to give it (a queued plan task, a subagent, a headless run) and no argument settles it, take the choice that changes nothing of theirs: a differing file gets the plugin's copy beside it as `<name>.plugin`, and a path or any other change to an installed copy is not made. List each one under `Waiting for the user:` in the report. Never guess the answer.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: all five files exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Detect the engines.** Search compose files, manifests and config, not only one of them:
   - PostgreSQL: a `postgres`/`pgvector` image, `Npgsql`, `org.postgresql`, `pg`/`postgres`/`@neondatabase`, `psycopg`/`asyncpg`, `jdbc:postgresql`, Prisma `provider = "postgresql"`, Drizzle `dialect: "postgresql"`.
   - SQL Server: an `mssql`/`azure-sql-edge` image, `Microsoft.EntityFrameworkCore.SqlServer`, `Microsoft.Data.SqlClient`, `mssql-jdbc`, `mssql`/`tedious`, `pyodbc`/`pymssql`, `jdbc:sqlserver`, Prisma `"sqlserver"`.
   - MySQL family: a `mysql`/`mariadb` image, `Pomelo.EntityFrameworkCore.MySql`, `MySqlConnector`, `mysql-connector-j`, `mariadb-java-client`, `mysql2`, `mysqlclient`/`PyMySQL`, `jdbc:mysql`/`jdbc:mariadb`, Prisma `"mysql"`, Drizzle `dialect: "mysql"`.
   - Name any NoSQL engine you find and say it has no rule file. When no SQL engine and no migration tool turns up, stop: there is nothing to install.
   - Ambiguous (a driver with no service, two candidates)? Ask which engines are real.
4. **Detect the migration tool and where it writes**: Flyway (`spring.flyway.locations`, `flyway.locations`, default `db/migration`), Liquibase (`changeLogFile`, `spring.liquibase.change-log`), EF Core (the folder holding `*ModelSnapshot.cs`), Prisma (beside `schema.prisma`), Drizzle (`out` and `schema` in `drizzle.config.*`), Alembic (`script_location` in `alembic.ini`, plus `/versions`), Django (`*/migrations/0*.py`), `node-pg-migrate`/`umzug`/sqlx (`migrations/`), `migrate-mongo` (`migrationsDir`), Mongock (`@ChangeUnit` classes), DbUp (its embedded `.sql` scripts).
5. **Copy each file** that is missing from the target: `data.md`, `data-migrations.md`, and the engine files step 3 found. `mkdir -p <root>/.claude/rules/data` and `cp` byte for byte.
6. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer or a `replace` argument.
   - An engine file installed earlier for an engine step 3 no longer finds: report it, do not delete it.
7. **Fit the paths to this project**, with the user's agreement, in the installed copies:
   - A migration location from step 4 that no default glob matches (a Mongock package, DbUp `Scripts/`, a custom Flyway location): add its glob to `data.md`, `data-migrations.md` and the engine file.
   - A default glob that catches something else (a `migrations/` folder of a frontend state store, a Drizzle `out` that is not `drizzle/`): narrow it.
   - A Drizzle `schema` file: add it to `data.md` and the engine file.
   - Several SQL engines: narrow each engine file's globs to the folders that engine's SQL and migrations live in, so a PostgreSQL migration never loads the SQL Server rules.
8. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/data/data.md`. If it is ignored, say so; the rules then apply on this machine only.
9. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) and any installed backend persistence rules (`.claude/rules/be-*/*persistence*.md`) for rules that contradict these files, and list them. A written contradiction is the user's to settle.

## Report

```
data rules: <file>: installed | up to date | replaced | kept | written as .plugin | not installed (engine absent)   (one line per file)
Path: <root>/.claude/rules/data/
Engines: <SQL engines found> · no rule file: <NoSQL engines found, or none>
Migration tool: <tool at path>   Paths: default | widened with <globs> | narrowed to <globs>
Committed: yes | ignored by git
Conflicts with CLAUDE.md or backend rules: none | <one line each>
Waiting for the user: none | <one line each: the file or path change, and the question>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
