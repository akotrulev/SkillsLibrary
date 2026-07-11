# Redis — Security

ACL users and rules, TLS, `protected-mode`, command renaming/disabling, network isolation, and secret handling. Redis's threat model is unusual: it's an unauthenticated, fast, scriptable in-memory server that is *catastrophic* if exposed — most Redis breaches are "left open on the internet," not clever exploits.

## The headline: never reachable, never unauthenticated

- **`protected-mode` on** (the default since 3.2) — refuses external connections when no password/bind is configured. Never disable it to "make it work"; fix the bind/auth instead.
- **Bind to private interfaces only** and put Redis in a private subnet / security group that **only the app tier** can reach. A Redis port open to `0.0.0.0` with no auth is game over — attackers use `CONFIG SET dir` + `SAVE` to write files, or `MODULE LOAD` / `SLAVEOF` to run code.
- **Require authentication.** `requirepass` is the minimum; **ACL users are the real answer** (below).

## ACLs — users, not just a shared password

Since Redis 6, ACLs replace the single shared `requirepass` with named users scoped to **commands, key patterns, and channels**. Give each workload its own least-privilege user.

```
# redis.conf / ACL file — an app user that can only touch its namespace, no dangerous commands
user orders-api on >${STRONG_SECRET} \
  ~v1:order:* ~rl:* \
  &invalidate:* \
  +@read +@write +@string +@hash -@dangerous -flushall -flushdb -keys -config

# lock down / disable the default user in production
user default off
```

Rules to apply:

- **One ACL user per workload** (cache app, session app, worker), each restricted to its **key prefix** (`~v1:tenant:*`) and the **command categories** it needs (`+@read +@write` and the specific types), with `-@dangerous` subtracted.
- **Disable or lock the `default` user** (`user default off`) so an unauthenticated connection has zero rights.
- Deny by default; grant the minimum. Never grant `+@all` / `allcommands allkeys` to an app user.
- Manage ACLs as config (an ACL file under version control / the managed-service ACL API), not ad-hoc `ACL SETUSER` in a shell — and reload with `ACL LOAD` (7.4+ no longer disconnects all clients on reload).

> Valkey/managed note: managed tiers (ElastiCache/MemoryDB, Azure) expose ACLs through their own RBAC/user-group APIs — configure there, same principle. Valkey supports the same ACL model.

## Dangerous commands — rename or disable

Some commands are attack primitives or foot-guns in production. Remove them from app users' ACLs, and additionally **rename or disable** them server-wide so even an admin misfire can't fire them:

| Command | Why | Action |
|---|---|---|
| `FLUSHALL` / `FLUSHDB` | Wipes the keyspace | `-flushall -flushdb` in ACLs; rename to an obscure string or disable |
| `KEYS` | O(N), blocks the server | Deny to app users; use `SCAN` |
| `CONFIG` | `CONFIG SET dir` enables file-write RCE | Deny to app users; restrict to admin |
| `DEBUG`, `SHUTDOWN` | Crash / halt | Admin-only or disabled |
| `MODULE` | Loads native code | Disable unless you deliberately load modules |
| `SLAVEOF`/`REPLICAOF`, `SCRIPT` | Replication hijack / arbitrary Lua | Restrict to admin |

Disable via `rename-command KEYS ""` (empty = disabled) or rename to an unguessable token in `redis.conf`.

## TLS in transit

- **TLS on every remote/managed connection** — `rediss://`, or `tls-port` + `--tls-cert-file`/`--tls-key-file`/`--tls-ca-cert-file` self-hosted. Clients: `Ssl = true` (StackExchange), `ssl.enabled: true` (Lettuce), `socket.tls` (node-redis).
- Prefer **mutual TLS** (client certs) for service identities where the platform supports it.
- Don't terminate TLS at a sidecar and run Redis plaintext on a shared network unless that network is genuinely private and attested.

## Secrets

- ACL passwords / connection URIs in **env vars / Key Vault / Secrets Manager**, never in code, `redis.conf` committed to git, or `appsettings.json`.
- Rotate the app user's secret on a schedule; ACLs make rotation per-user without downtime for others.
- On cloud, prefer **IAM/Entra-based auth** where the managed service offers it (ElastiCache IAM auth, Azure Managed Redis Entra auth) over a long-lived password.

## Encryption at rest

RDB/AOF files and backups hold your keyspace in plaintext on disk. Enable **at-rest encryption** on the volume / managed tier, and treat backup snapshots as sensitive (they contain sessions, tokens, cached PII). At-rest + TLS are baseline; Redis has no field-level encryption — don't cache secrets you wouldn't want in a snapshot.

## Rules

- `protected-mode` on; bind private; never reachable from the public internet or an untrusted subnet.
- Per-workload **ACL users**, least-privilege by key prefix + command category; `default` user disabled.
- Rename/disable `FLUSHALL`/`FLUSHDB`/`KEYS`/`CONFIG`/`MODULE`/`DEBUG`; deny them to app users.
- TLS on every remote connection; mTLS/IAM auth where available.
- Secrets in a secret store; rotate; at-rest encryption on data/backup volumes.
- Manage ACLs as versioned config, not shell commands.

## What NOT to do

- No Redis reachable from the internet / a shared network without auth (the #1 breach).
- No disabling `protected-mode` to work around a bind issue.
- No single shared `requirepass` as the whole auth story — use ACL users.
- No app user with `+@all`/`allkeys allcommands`, or with `CONFIG`/`KEYS`/`FLUSH*`/`MODULE`.
- No leaving the `default` user enabled in production.
- No plaintext connections to a managed/remote Redis.
- No secrets in `redis.conf`/config committed to the repo.
- No caching data so sensitive that an unencrypted snapshot would be a breach.

## Handoffs

- Running Redis (persistence/backups whose files this section says to encrypt, replication) → `references/operations.md`
- Why `KEYS` is banned operationally (single-threaded) → `references/data-structures.md` + `references/operations.md`
- Tenant/user identity feeding per-tenant key prefixes → `auth/auth0-{stack}` + `auth/_shared/auth0-concepts`
- Verifying access restrictions → `qa/_shared/security-testing/*` + `qa/<stack>/skills/db-testing/*`
