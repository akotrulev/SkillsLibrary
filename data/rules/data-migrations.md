---
paths:
  - "**/db/migration/**"
  - "**/migrations/**"
  - "**/Migrations/**"
  - "**/db/changelog/**"
  - "**/alembic/versions/**"
  - "**/drizzle/**"
---

<!-- data rules v1 (2026-11-03): migrations. Installed by /data:rules; edit the paths above to where this project's migration tool keeps its migrations. -->

# Migration standards (any tool, any engine)

Severity tags as in the core data rules. The project's migration tool and its naming win.

- One migration tool per project. Every schema change goes through it, run by the pipeline before deploy: no ad-hoc DDL in production, no migration at app startup. *major*
- An applied migration is never edited. Production is forward-only: a fix is a new migration; down scripts are for local use. *blocker*
- One logical change per migration, named version-then-description. Schema (DDL) and data (backfill) changes are separate files. *major*
- Expand-contract, one phase per release: add the new shape, dual-write, backfill, switch reads, then drop. No in-place rename or type change; no column dropped in the release that stops writing it. *blocker*
- No destructive one-step change on a live table unless it is provably small and the app provably down. *blocker*
- `NOT NULL` on a large table only after a backfill or with a metadata-only constant default; a constraint on a large table is added unvalidated, then validated. *major*
- An index on a hot table uses the engine's online form; nothing locks a hot table for a multi-million-row change. *major; blocker for the lock*
- Idempotent where the tool allows (`IF NOT EXISTS`, `ON CONFLICT DO NOTHING`). *minor*
- A backfill is batched, resumable from a recorded cursor, observable and throttleable. A long one is a job the pipeline triggers, never run from a laptop. *major*
- The migration applies cleanly against a scratch copy before it merges. *major*
- Document stores have no `ALTER`: a new attribute is written and readers tolerate its absence; a rename is dual-write plus a change-feed backfill; a partition-key change is a new container or table, a copier and a cutover; a Mongo validator tightens with `validationAction: "warn"` before `"error"`. *major*
- When several services share the database, the owning service runs the migration and the compatible release range is written down. *minor*
