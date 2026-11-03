---
paths:
  - "**/*Entity.java"
  - "**/*Repository.java"
  - "**/*Dao.java"
  - "**/{entity,entities,persistence}/**/*.java"
  - "**/db/migration/**"
---

<!-- be-java rules v1 (2026-11-03): persistence. Installed by /be-java:rules; edit the paths above to where this project keeps its entities and repositories. -->

# Java persistence standards (JPA / Hibernate / Spring Data / Flyway)

Severity tags as in the core Java rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- Flyway or Liquibase owns the schema; a change is a new migration, never an edit to an applied one. *blocker*
- Indexes and constraints come from migrations, not Hibernate annotations; columns are snake_case with explicit names. *minor*
- `@Enumerated(EnumType.STRING)`, always. *major*
- Entities: no Lombok `@Data`; `equals`/`hashCode` not based on a generated id; a protected no-args constructor plus a factory method; collections exposed unmodifiable. *major*
- Associations: no global `FetchType.EAGER`, no `cascade = ALL` on `@ManyToOne`, both sides of a bidirectional association kept in step, `@ManyToMany` with an explicit `@JoinTable`. *major*
- Fetch per query with `@EntityGraph` or a join fetch; use a DTO projection for read-only views; never paginate over a fetch-joined collection. *major*
- `@Version` on an aggregate with concurrent writers; never swallow `OptimisticLockingFailureException`. *major*
- One repository per aggregate. No Spring Data interface or hand-written repository that only mirrors `JpaRepository`. *major*
- A bulk change is a `@Modifying` query or JDBC batch, not a load-every-entity loop. *minor*
- SQL takes bound parameters only, never string concatenation. *blocker*
