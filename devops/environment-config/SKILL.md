---
name: devops-environment-config
description: Use when the user asks to manage environment configuration, secrets, and per-environment overrides across .NET / Java / Node services — typed config classes, secret stores (Key Vault, AWS Secrets Manager, Vault), config layering, schema validation, hot-reload. Triggers: "set up config for X", "where do secrets go", "validate config at startup". Do NOT use for pipeline authoring (`devops/{github-actions,gitlab-ci,azure-pipelines}`) or cloud deploy (`devops/{aws,azure}-deployment`).
---

# DevOps — Environment Configuration & Secrets

Standardizes how services across the library load configuration and secrets per environment. Defaults baked into code; per-environment values overlayed from a secret-free source; secrets pulled from a secret store at runtime via a Managed Identity / IAM role. Config schema validated at startup — a missing or wrong-shaped value should crash the service immediately, not surface as a 500 in production three days later.

**Version policy:** detect the project's versions (TFM / `engines` / toolchain) and match — never assume. .NET 10 is primary, 8/9 supported (8 LTS ends Nov 2026). Node 20 is EOL (Apr 2026) — 24 is active LTS, 22 maintenance. Java 21 LTS is the default. The config patterns below are version-neutral; only the SDK/package surface differs.

## When to use

- New service needs a config story
- Existing service has `process.env.X` / `IConfiguration["X"]` reads scattered everywhere
- Migrating client secrets to Workload Identity / Managed Identity
- Adding per-environment overrides (dev / staging / prod)
- Setting up Key Vault / Secrets Manager / Vault integration

## When NOT to use

- Pipeline YAML → `devops/{github-actions,gitlab-ci,azure-pipelines}`
- Cloud-specific deploy → `devops/{aws,azure}-deployment`
- Auth0 client secrets in particular → `auth/auth0-{stack}`
- App-level options pattern within code → `backend/{dotnet,java,node}/skills/{reference,generator}`

## The three-layer model

Every service loads config from three layers, in this order, last wins:

1. **In-code defaults** — sensible values for local dev. Compile-time constants.
2. **Per-environment values** from a non-secret source — `appsettings.<env>.json`, `application-<env>.yml`, env vars from a non-secret config map. Checked into the repo.
3. **Secrets** from a secret store at runtime — Azure Key Vault / AWS Secrets Manager / Vault. **Never** in repo, **never** in env vars set by `helm install`, **never** in pipeline variables.

Everything else (timeouts, feature flags, log levels) is non-secret → layer 2.

## Per-stack recipes

### .NET (10 primary) — typed `IOptions<T>` + Key Vault binding

```csharp
// Program.cs
var builder = WebApplication.CreateBuilder(args);

// Layer 1 + 2: appsettings.json + appsettings.<env>.json (already wired)
// Layer 3: Key Vault
if (!builder.Environment.IsDevelopment())
{
    builder.Configuration.AddAzureKeyVault(
        new Uri(builder.Configuration["KeyVault:Uri"]!),
        new DefaultAzureCredential());
}

// Typed config
builder.Services.AddOptions<OrdersOptions>()
    .Bind(builder.Configuration.GetSection("Orders"))
    .ValidateDataAnnotations()
    .ValidateOnStart();
```

```csharp
public sealed class OrdersOptions
{
    [Required] public required string PricingMode { get; init; }
    [Range(1, 1000)] public int MaxLines { get; init; } = 100;
    [Url] public required string DownstreamApiUrl { get; init; }
}
```

`ValidateOnStart()` is non-negotiable — startup fails loud and early.

Layer 2 values in `appsettings.Production.json`; Layer 3 secrets land under the same configuration keys via Key Vault binding (`Orders--ApiKey` in Key Vault → `Configuration["Orders:ApiKey"]`).

### Java 21 + Spring Boot 3 — `@ConfigurationProperties` + Azure / AWS adapter

```yaml
# application.yml — Layer 1 defaults
orders:
  pricing-mode: standard
  max-lines: 100
  downstream-api-url: http://localhost:8081
```

```yaml
# application-prod.yml — Layer 2 per-env
orders:
  downstream-api-url: https://orders.yourco.com
```

```java
@ConfigurationProperties(prefix = "orders")
@Validated
public record OrdersOptions(
    @NotBlank String pricingMode,
    @Min(1) @Max(1000) int maxLines,
    @URL String downstreamApiUrl,
    @NotBlank String apiKey                  // Layer 3, pulled from Key Vault
) {}
```

Layer 3 wiring options:

- **Azure**: Spring Cloud Azure (`spring-cloud-azure-starter-keyvault-secrets`) binds Key Vault secrets to Spring's `Environment` automatically — `apiKey` set on the Key Vault is available as `orders.api-key` to the app.
- **AWS**: Spring Cloud AWS Parameter Store / Secrets Manager (`spring-cloud-aws-starter-parameter-store`) does the same with SSM Parameter Store or Secrets Manager.
- **Vault**: Spring Cloud Vault.

For both clouds, use a **Managed Identity / IAM Role** for auth — never client secret keys.

### Node 24 + TypeScript — Zod + `dotenv-flow` + cloud SDK

```typescript
// src/shared/config.ts
import { z } from 'zod';
import { SecretsManagerClient, GetSecretValueCommand } from '@aws-sdk/client-secrets-manager';
// or:
// import { SecretClient } from '@azure/keyvault-secrets';
// import { DefaultAzureCredential } from '@azure/identity';

const ConfigSchema = z.object({
  port: z.coerce.number().int().positive(),
  pricingMode: z.enum(['standard', 'b2b']),
  maxLines: z.coerce.number().int().min(1).max(1000).default(100),
  downstreamApiUrl: z.string().url(),
  apiKey: z.string().min(1),                 // Layer 3
});
export type Config = z.infer<typeof ConfigSchema>;

async function getSecrets(): Promise<Record<string, string>> {
  if (process.env.NODE_ENV === 'development') return {};   // local: use .env / shell

  // Pull secrets from AWS Secrets Manager (or Key Vault — pick one per project)
  const client = new SecretsManagerClient({});
  const res = await client.send(new GetSecretValueCommand({ SecretId: process.env.SECRETS_BUNDLE! }));
  return JSON.parse(res.SecretString!) as Record<string, string>;
}

export async function loadConfig(): Promise<Config> {
  const secrets = await getSecrets();
  return ConfigSchema.parse({
    port: process.env.PORT,
    pricingMode: process.env.PRICING_MODE,
    maxLines: process.env.MAX_LINES,
    downstreamApiUrl: process.env.DOWNSTREAM_API_URL,
    apiKey: secrets.apiKey ?? process.env.API_KEY,           // env fallback for local dev
  });
}
```

Local dev uses `dotenv-flow` (`dotenv-flow/config`); prod pulls a single "secrets bundle" from Secrets Manager / Key Vault. The bundle approach keeps secret fetching to one API call at startup.

## Naming conventions

- **Hierarchical keys** — `Orders:PricingMode` (.NET / YAML nesting), `orders.pricing-mode` (Spring), `ORDERS_PRICING_MODE` (env vars)
- **Per-env files / branches**: `Development`, `Staging`, `Production` (.NET); `dev`, `staging`, `prod` (Spring profiles); `development`, `production` (`NODE_ENV`)
- **Secret-bundle** names per env + per service: `secrets/orders/prod`, `secrets/orders/staging`

Pick one convention per project and apply it everywhere.

## Validation at startup

Every stack has a "validate or crash" pattern. **Use it.**

- .NET: `.ValidateDataAnnotations().ValidateOnStart()`
- Java/Spring: `@Validated` + `@NotBlank` / `@Range` / `@URL` on the record
- Node/Zod: `ConfigSchema.parse(...)` — throws on schema violation

A misconfigured service should not start. Failing at startup is dramatically cheaper than discovering at first request.

## Per-environment values — where they actually live

| Layer 2 source | When |
|---|---|
| `appsettings.<env>.json` / `application-<env>.yml` | Committed; small projects |
| Environment variables on the container | Works everywhere; lose hierarchy unless using `__` (.NET) / `_` (Spring) separators |
| Helm `values-<env>.yaml` | Kubernetes |
| Container App environment variables / App Service settings (Azure) | Azure managed services |
| ECS task definition environment / Lambda env vars (AWS) | AWS managed services |
| App Config / Parameter Store **non-secret** | Centralized config across services |

Rule: **non-secret per-env values can sit in `values-<env>.yaml` / Container App settings / ECS env**. Secrets do **not** sit there even when the deploy mechanism would let them.

## Secret stores

| Store | Cloud | Use when |
|---|---|---|
| **Azure Key Vault** | Azure | Default for Azure stacks; integrate with Managed Identity |
| **AWS Secrets Manager** | AWS | Default for AWS stacks where rotation is a feature requirement |
| **AWS Systems Manager Parameter Store** | AWS | Cheaper; SecureString param for sensitive values; rotation manual |
| **HashiCorp Vault** | Anywhere | Multi-cloud; dynamic secrets (DB credentials minted per request) |
| **Sealed Secrets / SOPS** | Kubernetes | When secrets must live in Git encrypted, decrypted at deploy |

Pick **one per environment** and use it consistently. Mixing creates confusion about which value wins.

### Rotation

Rotation is a property of the store, not the app:

- Key Vault: enable rotation policy on the secret; binding refreshes automatically (default poll ~12 hours, configurable)
- Secrets Manager: rotation Lambda + scheduled rotation; SDK caches with TTL
- Parameter Store: manual rotation, manual restart unless app polls

In the app, **don't cache secrets indefinitely**. Either:

- Refresh on a TTL (5–15 minutes); restart-safe but eventually consistent
- Re-fetch on auth failure (the secret rotated; the new pod will work)
- Subscribe to a store event / event bus when supported

## Hot reload vs restart

- **Restart-on-change** is simpler and the default for most services
- **Hot reload** (`IOptionsMonitor<T>` in .NET, Spring Cloud Config refresh) is right for feature flags + log levels, **wrong** for connection strings / secrets that affect long-lived clients (the client won't pick up the new value without reconstruction)

## Local development

- `appsettings.Development.json` / `application-dev.yml` / `.env.local` committed (no secrets)
- `appsettings.Local.json` / `.env.local` for personal overrides (gitignored)
- Local secret strategy: a `secrets.local.json` in the user's home directory, **never** committed; documented in `README.md` how to obtain test credentials
- `dotnet user-secrets` for ASP.NET Core local secrets

## Rules

- **Three layers, last wins** — defaults → per-env non-secret → secrets
- **Secrets in a secret store**; never in repo, never in CI/CD variables, never in env vars set by `helm install`
- **Managed Identity / IAM Role** for the app to access the secret store
- **Validation at startup**; service crashes early on missing or invalid config
- **Typed config object** consumed throughout the app; **no direct `process.env.X` / `IConfiguration["X"]` reads in business code**
- **Per-env files / values** committed (non-secret)
- **One secret store per environment**, not a mixture
- **Refresh strategy** documented per app (restart-on-change vs `IOptionsMonitor` vs poll)
- **Naming convention** consistent (`Service:Section:Key`)

## What NOT to do

- No secrets in `appsettings.json` / `application.yml` / `.env` checked into Git
- No "encrypted in repo" secrets without a SOPS / Sealed-Secrets pipeline that decrypts at deploy
- No `process.env.X` reads scattered in business code
- No "we'll inject the secret as an env var in the deployment YAML" — that's not a secret store, that's a glorified config map
- No service principal client secrets when Managed Identity / IAM is available
- No `IOptionsSnapshot<T>` consumed by a singleton (lifetime mismatch — won't refresh)
- No long-cached secret with no rotation strategy
- No silent fallbacks (`process.env.API_KEY ?? "demo-key"`) — fail loud
- No `null` / empty-string defaults for required config

## Generation steps

1. Confirm the stack and environment(s) with the user.
2. Choose the secret store (Key Vault / Secrets Manager / Parameter Store / Vault) per the cloud.
3. Define the **typed config schema** (.NET options class, Spring `@ConfigurationProperties` record, Zod schema) — every config value typed and validated.
4. Wire Layer 3 (secret store binding) using Managed Identity / IAM Role — no client secrets.
5. Add `ValidateOnStart` / `@Validated` / `ConfigSchema.parse` so misconfig crashes startup.
6. Document the per-env files / settings and the local-dev fallback path.
7. Smoke locally with the dev config; smoke in staging confirming the secret store binding fires.

## Handoffs

- Pipeline YAML setup → `devops/{github-actions,gitlab-ci,azure-pipelines}`
- Cloud deploy specifics → `devops/{aws,azure}-deployment`
- IaC for the secret store + identity → `devops/infrastructure-as-code`
- App-level Options pattern → `backend/{dotnet,java,node}/skills/generator`
- Auth0 client secrets specifically → `auth/auth0-{stack}`
