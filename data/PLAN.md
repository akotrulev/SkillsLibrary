# PLAN — `data/` domain audit & improvement (2026-07-12)

Audit of the full `data/` domain (38 files, ~5,600 lines): the `data-architect` agent, the 5
router engines (postgresql · sqlserver · mysql · mongodb · redis) + their 24 topic references,
the 3 single-file engines (dynamodb · cosmosdb · elasticsearch), the 4 `_shared` skills, and the
`data` plugin entry in `.claude-plugin/marketplace.json` — checked against the library
`CLAUDE.md` data catalog, `.skill-template/agent.md`, the actual on-disk paths of every
cross-reference, and version currency as of 2026-07.

**Overall verdict: strong.** The scope-fence contract (`_shared` decides / engine executes) is
held consistently in both directions; every engine skill is genuinely version-aware with
fallback tables (PG 18/15–17, SQL Server 2025/2022/2019, MySQL 8.4/9.x/8.0 + MariaDB, Mongo
8.0/7.0, Redis 8.x/7.x + Valkey, ES 9/8 + OpenSearch — all current); the fork-divergence
treatment (Valkey, MariaDB, OpenSearch) is uniform; reference files are dense, not padded
(the 69-line `mysql/references/caching.md` is the *right* length for what MySQL offers); the
agent is brownfield-template-compliant; the marketplace manifest lists all 12 skills + the
agent correctly. The defects are almost entirely **stale or phantom cross-references** written
before the observability domain shipped and pointing at a `devops/` folder that doesn't exist —
plus one broken claim in the agent's Phase 1, and one content gap (pgvector).

## Findings

| Severity | Location | Issue | Suggested fix |
|----------|----------|-------|---------------|
| major | agents/data-architect.md:104; redis/SKILL.md:153; redis/references/operations.md:97; mongodb/SKILL.md:154; mongodb/references/performance.md:94 | **Stale "observability/\* once authored".** The observability domain HAS shipped (6 skills + `observability-engineer-{dotnet,java,node}` agents, bundled into the `be-*` plugins — see recent commits 9de9c6a, 016d731, 852a8de). The agent's line 104 "**No agent yet** (point the human at the skills)" is factually wrong; four skill handoffs still say "once authored". | Agent: replace the line-104 bullet with a real peer entry — "`observability-engineer-{dotnet,java,node}` (bundled in the matching `be-*` plugin) — query-latency telemetry, slow-query dashboards, DB-metric alert rules for the schema this agent designs." Skills: drop "once authored"; point at `observability/*` skills / the `observability-engineer-{stack}` peer. |
| major | _shared/migrations/SKILL.md:184; dynamodb/SKILL.md:331,333; cosmosdb/SKILL.md:334–335; elasticsearch/SKILL.md:396–397; mysql/SKILL.md:165; sqlserver/SKILL.md:160 | **Phantom `devops/*` handoffs.** 8 handoff lines point at `devops/github-actions`, `devops/gitlab-ci`, `devops/azure-pipelines`, `devops/aws-deployment`, `devops/azure-deployment`, `devops/iac-bicep-terraform`, or bare `devops/*` — no `devops/` folder exists anywhere in the library, and the `data` plugin is self-contained, so an installed user follows a dead pointer. | Migrations CI line → the real owner: "`qa-cicd-{java,dotnet,typescript}` (`qa/cicd/<stack>/skills/ci-pipelines`) — the pre-deploy migration step in the pipeline". Deployment/IaC lines → honest phrasing per the agent's own missing-skill rule: "cloud deployment / IaC for the store itself — no skill in this library yet; out of this domain's scope" (or drop the line). |
| major | agents/data-architect.md:91 (Phase 1 row); _shared/schema-design/SKILL.md (whole file) | **Engine-selection framing doesn't exist where the agent says it does.** Phase 1 loads `_shared/schema-design` "for the engine-selection framing", and the agent's triggers include "which database for this workload" — but `schema-design` has no engine-selection section at all (it covers ids/timestamps/money/tenancy/audit/embed-vs-reference). The only guidance is the one-line heuristic in the agent's "When uncertain". | Add an **"Engine selection"** section to `_shared/schema-design` (it's the cross-engine *decision* skill — right home per the scope fence): a workload-shape → engine decision matrix (relational default · document · KV/cache · wide-column known-access-pattern scale · search/relevance · vector), the "don't silently default to Postgres, but know when Postgres genuinely suffices (jsonb, tsvector, SKIP LOCKED queues, pgvector)" rule, and one row per in-catalog engine with its "reach for me when / not when". Update the Phase 1 row to cite the section. |
| major | postgresql/ (no file mentions pgvector) ; elasticsearch/SKILL.md:3,10 | **pgvector gap.** The library treats RAG/LLM features as first-class (`rag-testing`, `llm-app-testing`), Redis and ES both cover vector search, and `elasticsearch` declares itself "the destination for vector search beyond a cache" — but `data/postgresql` never mentions pgvector, the most common way an existing Postgres-backed app adds embeddings. The routing sends everyone to a new ES cluster even when a `vector` column on the table they already own is the right call. | Add a pgvector subsection to `postgresql/references/indexing.md` (HNSW vs IVFFlat, operator classes, filtered ANN caveats) + a modeling note in `references/data-modeling.md` (`vector(n)` column next to the row it embeds, when to normalize out); add a routing-table row in the postgres SKILL. In `elasticsearch/SKILL.md`, qualify the inbound-handoff sentence: pgvector on the existing Postgres first; ES/OpenSearch when you need dedicated relevance/hybrid ranking, independent scaling, or the data isn't in Postgres. |
| minor | elasticsearch/SKILL.md:10,394 | **Broken reference paths** — `data/mongodb/indexing.md` and `data/redis/data-structures.md`; the actual files live under `references/`. | `data/mongodb/references/indexing.md` · `data/redis/references/data-structures.md`. |
| minor | _shared/query-optimization/SKILL.md:117,191 | **Wrong qa path shape** — `qa/api-test-author/reviewer` and `qa/api-test-author/generator/<stack>` don't exist; the shape is stack-first. | `qa/<stack>/skills/api-test-author/reviewer` · `qa/<stack>/skills/api-test-author/generator`. |
| minor | postgresql/SKILL.md:3; sqlserver/SKILL.md:3; mysql/SKILL.md:3; mongodb/SKILL.md:3 | **Frontmatter path shape** — the "Do NOT use for … writing DB tests" pointer says `qa/<stack>/db-testing`; the real path is `qa/<stack>/skills/db-testing`. (The Handoffs sections at the bottom of the same files get it right.) | Align the descriptions with the Handoffs form. |
| minor | redis/SKILL.md:3,152 | **Messaging pointer wrong** — "durable messaging → `qa/_shared` messaging references". `messaging-testing` is a per-stack skill (`qa/<stack>/skills/messaging-testing`), and it's a *testing* skill — there is no messaging *implementation* skill in the library at all. | Point at `qa/<stack>/skills/messaging-testing` for testing brokers, and say plainly that broker selection/implementation has no owning skill yet. |
| minor | dynamodb/SKILL.md:36 | **Internal contradiction** — "When to use" bullet says "SDK setup (.NET v3 / Java v2 / Node v3)" but the skill's own stack default (lines 13, 21–30) is AWS SDK for .NET **v4** with v3 as the tagged down-level fallback. | ".NET v4 (v3 down-level) / Java v2 / Node v3". |
| nit | postgresql/references/security.md:75; mysql/references/security.md:44 | Brace style `qa/{stack}/skills/db-testing/*` vs the routers' `qa/{java,dotnet,typescript}/skills/db-testing/*` — inconsistent placeholder convention. | Standardize on the enumerated form used by the routers. |
| nit | agents/data-architect.md:98–104 | Peer list omits `qa-cicd-{stack}` even though the migrations skill mandates "migrations run from the pipeline" — the wiring has an owner the agent never names. | Add one peer line: "`qa-cicd-{java,dotnet,typescript}` — wires the migration step into the pipeline the migrations skill requires." |

Explicitly checked and **fine**: marketplace.json `data` entry (all 12 skills + agent, correct
relative paths); agent template compliance (orientation pass, FIX/EXTEND modes, both output
contracts, scope fence, skill-loading protocol incl. `${CLAUDE_PLUGIN_ROOT}` resolution and the
missing-skill rule); scope-fence contract held bidirectionally (spot-checked modeling,
migrations, caching, query-tuning lanes in both `_shared` and engine files); version currency of
all eight engines as of 2026-07 (incl. MySQL 8.0 EOL Apr 2026 flagged, Redis 8 module bundling,
ES/OpenSearch license history); all intra-`data/` reference paths except the two elasticsearch
ones; `auth/auth0-{stack}` + `auth/_shared/auth0-concepts` handshakes (real paths); every
`qa/{java,dotnet,typescript}/skills/db-testing/*` and `security-testing/access-control-testing`
handoff (real paths); Cosmos two-RBAC-planes and creation-time-immutable treatment; DynamoDB
`LeadingKeys` caveats; the six-phase pipeline's exit gates vs the skills they load.

## Plan of action

Four phases, each independently committable. Work on a branch. No new files except the
schema-design section and pgvector reference material go into existing files — the domain's
shape (12 skills, 1 agent) does not change, so `CLAUDE.md` and marketplace.json need no edits.

### Phase 1 — Kill stale & phantom cross-references (mechanical; majors 1–2, minors 5–8, nits)

- [x] 1.1 `agents/data-architect.md:104` — replace the "No agent yet" bullet with the
      `observability-engineer-{dotnet,java,node}` peer entry (bundled in the matching `be-*`
      plugin; query-latency telemetry, DB dashboards/alerts). Add the `qa-cicd-{stack}` peer
      line (nit #2) in the same edit.
- [x] 1.2 Drop "once authored" and point at the shipped observability skills/agent in:
      `redis/SKILL.md:153`, `redis/references/operations.md:97`, `mongodb/SKILL.md:154`,
      `mongodb/references/performance.md:94`.
- [x] 1.3 `_shared/migrations/SKILL.md:184` — CI handoff →
      `qa-cicd-{java,dotnet,typescript}` / `qa/cicd/<stack>/skills/ci-pipelines`.
- [x] 1.4 Replace the deployment/IaC phantom pointers with the honest "no skill in this
      library yet — out of scope" phrasing (or drop the line where it adds nothing):
      `dynamodb/SKILL.md:331,333` · `cosmosdb/SKILL.md:334–335` ·
      `elasticsearch/SKILL.md:396–397` · `mysql/SKILL.md:165` · `sqlserver/SKILL.md:160`.
- [x] 1.5 Fix broken/wrong-shape paths:
      `elasticsearch/SKILL.md:10,394` (`…/references/indexing.md`, `…/references/data-structures.md`);
      `_shared/query-optimization/SKILL.md:117,191` (`qa/<stack>/skills/api-test-author/…`);
      frontmatter `qa/<stack>/db-testing` → `qa/<stack>/skills/db-testing` in
      `postgresql|sqlserver|mysql|mongodb/SKILL.md:3`;
      `redis/SKILL.md:3,152` messaging pointer → `qa/<stack>/skills/messaging-testing` + the
      no-implementation-skill note; brace-style nit in `postgresql|mysql/references/security.md`.
- [x] 1.6 `dynamodb/SKILL.md:36` — align the "When to use" SDK bullet with the v4 default.
- [x] 1.7 Gate: `grep -rn "devops/\|once authored" data/` returns nothing;
      `grep -rn "qa/<stack>/db-testing\`\|api-test-author/reviewer\`" data/` returns nothing.

### Phase 2 — Engine-selection section (major #3)

- [x] 2.1 Add **"Engine selection"** to `_shared/schema-design/SKILL.md` (after "When NOT to
      use", before "Identifiers"): a workload → engine decision matrix covering all 8 catalog
      engines + the "Postgres suffices" row (jsonb / tsvector / SKIP LOCKED / pgvector before
      adding a store), consistency/latency/scale qualifiers, and the rule from the agent —
      justify against the workload, never default silently. Extend the frontmatter description
      + "When to use" with the "which database for this workload" trigger.
- [x] 2.2 Update `agents/data-architect.md` Phase 1 row to cite the new section by name; keep
      the "When uncertain" heuristic as the one-liner it is, referencing the section for depth.
- [x] 2.3 Gate: Phase 1 of the agent is executable as written — every skill/section it names
      exists on disk.

### Phase 3 — pgvector coverage (major #4)

- [x] 3.1 `postgresql/references/indexing.md` — add a pgvector section: `vector(n)` +
      HNSW (default) vs IVFFlat, operator classes (`vector_cosine_ops` etc.), `ef_search`/
      list-count tuning at a rules level, the filtered-ANN caveat (post-filter recall loss →
      partial index / iterative scan), version note (pgvector is an extension — probe with
      `SELECT extversion FROM pg_extension WHERE extname='vector'`; available on
      RDS/Aurora/Azure Flexible).
- [x] 3.2 `postgresql/references/data-modeling.md` — modeling note: embedding column lives
      next to the row it embeds; dimension pinned to the model; re-embedding is a backfill
      (cite `_shared/migrations` batched-backfill rules).
- [x] 3.3 `postgresql/SKILL.md` — routing-table row for vector search pointing at the
      indexing reference; one trigger word ("pgvector", "vector search") in the frontmatter.
- [x] 3.4 `elasticsearch/SKILL.md:3,10` — qualify the vector-destination claim: pgvector on
      the Postgres you already run is the first stop; ES/OpenSearch when relevance/hybrid
      ranking, independent scaling, or non-Postgres data justify a second store. Mirror the
      same one-line qualifier in `redis/references/data-structures.md:113`'s outbound line if
      it claims ES unconditionally.
- [x] 3.5 Gate: the three vector-capable skills (postgresql, redis, elasticsearch) route each
      other consistently — one decision chain, no contradictions.

### Phase 4 — Verify & close

- [x] 4.1 Re-run the full path-validity sweep: extract every `` `data/…` ``/`` `qa/…` ``/
      `` `auth/…` ``/`` `observability/…` `` reference in `data/**/*.md` and check each against
      the filesystem (placeholder forms `<stack>`/`<db>` expanded); zero dead paths.
- [x] 4.2 Re-read the agent end-to-end once against the edited skills — phase table, exit
      gates, peer list all name things that exist.
- [x] 4.3 Commit per phase (or one commit if reviewed together); this PLAN.md's checkboxes
      updated as phases land.

## Deferred backlog (not defects — decide separately)

- **New engine candidates**, in rough priority order if the domain grows: SQLite/libSQL
  (local-first, edge, embedded — genuinely different discipline), ClickHouse (OLAP/analytics —
  the catalog has no analytics store; ES is doing some of this work by proxy), Cassandra/
  ScyllaDB (only if a real project needs it — DynamoDB covers the wide-column *pattern*).
  Dedicated vector DBs (Pinecone/Qdrant/Weaviate) — likely *not* worth adding; pgvector + ES
  + Redis cover the library's stacks, and a one-line "when you'd outgrow these" note in the
  Phase-2 engine-selection matrix is enough.
- **Cloud deployment/IaC ownership** — the Phase-1 fixes remove the phantom `devops/*`
  pointers, but the underlying gap is real: nothing in the library owns provisioning the
  stores. If a `devops/` domain is ever built, these handoff lines are the ready-made seams.
- **`data/HANDOFF.md`** — not needed now (domain is shipped, not mid-build); create only if a
  multi-session extension (new engine) starts, per the established handoff-loop convention.
