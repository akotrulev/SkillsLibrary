---
name: devops-azure-deployment
description: Use when the user asks to deploy a service to Azure — Container Apps (default for long-running containers), Functions (event-driven), App Service (Windows/Linux web apps), Static Web Apps (SPA + Functions), or AKS (Kubernetes). Triggers: "deploy this .NET service to Azure Container Apps", "ship an Azure Function from a Node TS handler", "host the React SPA on Static Web Apps", "switch this from App Service to Container Apps". Do NOT use for AWS (use `devops/aws-deployment`), IaC scripts (use `devops/iac-bicep-terraform`), or pipeline YAML (use `devops/{github-actions,gitlab-ci,azure-pipelines}`).
---

# DevOps — Azure Deployment

Deploys services to Azure using the right primitive for the workload. Default for long-running container services is **Azure Container Apps** (serverless containers on KEDA + Envoy, no AKS to operate). For event-driven / per-request, **Azure Functions**. For SPAs, **Static Web Apps** (or **Storage + Front Door** if SWA's free Functions tier isn't enough). **AKS** only when the team has earned the Kubernetes overhead.

## Stack

- **Azure**: Container Apps, Functions, App Service, Static Web Apps, AKS, Container Registry (ACR), Key Vault, Managed Identity, Application Gateway / Front Door, Log Analytics, Application Insights
- **Backends**: .NET 8 / Java 21 / Node 20 — Linux container images or native Functions runtimes
- **Frontend**: React SPA → Static Web Apps; Blazor WASM → Static Web Apps or App Service; Blazor Server → App Service / Container Apps
- Identity via **Managed Identity** (system-assigned for single-resource, user-assigned for cross-resource) — no service principal secrets in apps
- IaC via Bicep (preferred for Azure-only stacks) or Terraform — see `devops/iac-bicep-terraform`
- Pipelines via Azure Pipelines / GitHub Actions / GitLab CI with **Workload Identity Federation** — no client secrets

## When to use

- New service needs a deploy target on Azure
- Migrating a workload between targets (App Service → Container Apps, VM → Container Apps, AKS → Container Apps for small services)
- Setting up the deploy pipeline's destination
- Choosing among Azure primitives for a specific workload

## When NOT to use

- AWS → `devops/aws-deployment`
- IaC syntax → `devops/iac-bicep-terraform`
- Pipeline YAML → `devops/github-actions` / `devops/gitlab-ci` / `devops/azure-pipelines`
- App-level config / secrets injection → `devops/environment-config` (when authored)

## Picking the right target

| Workload | Default target | Use because |
|---|---|---|
| Long-running web API or background worker | **Container Apps** | Serverless containers, scale-to-zero supported, KEDA scalers, VNet integration |
| Spiky / event-driven API or trigger | **Functions** | Consumption / Flex Consumption plans; rich triggers (HTTP, Queue, Service Bus, Event Grid, Cosmos) |
| Long-standing web app, no container appetite | **App Service** | Code-only deploy, slots, scaling, but more opinionated than Container Apps |
| SPA / static site (+ optional thin API) | **Static Web Apps** | CDN-fronted, free tier for personal/dev, paired Functions |
| Already running Kubernetes | **AKS** | Only when k8s expertise + complexity justify it |

Rule of thumb: start with **Container Apps** for services, **Functions** for event-driven, **Static Web Apps** for SPAs. Choose AKS deliberately.

## Container Apps — recipe

### Required resources

- **Container Apps environment** per env (`yourco-prod-env`), VNet-integrated for prod
- **Azure Container Registry (ACR)** with admin user disabled — auth via ACR Pull role on the app's managed identity
- **Container App** per service, with one or more revisions (multiple-revision mode for blue/green)
- **Managed Identity** (user-assigned, reused across the env's apps) with `AcrPull` on ACR + `Key Vault Secrets User` on the env's Key Vault
- **Log Analytics workspace** for container stdout (plus optional OTel Collector for routing elsewhere)

### Bicep / az CLI essentials

```bash
az containerapp create \
  --name orders-api \
  --resource-group rg-yourco-prod \
  --environment yourco-prod-env \
  --image yourco.azurecr.io/orders-api:$SHA \
  --target-port 8080 \
  --ingress external \
  --transport http \
  --user-assigned /subscriptions/.../resourceGroups/.../providers/Microsoft.ManagedIdentity/userAssignedIdentities/orders-mi \
  --registry-server yourco.azurecr.io \
  --registry-identity /subscriptions/.../userAssignedIdentities/orders-mi \
  --min-replicas 2 --max-replicas 10 \
  --cpu 0.5 --memory 1.0Gi \
  --env-vars "OTEL_EXPORTER_OTLP_ENDPOINT=https://otel-collector.internal:4317" \
  --secrets "db-password=keyvaultref:https://kv-orders.vault.azure.net/secrets/db-password,identityref:/subscriptions/.../userAssignedIdentities/orders-mi" \
  --scale-rule-name http \
  --scale-rule-http-concurrency 50
```

`keyvaultref:...,identityref:...` is the Container Apps native Key Vault binding — secret value is pulled by the managed identity at start. No app code reads Key Vault directly.

### Revisions and rollout

Container Apps supports **single-revision** (replace) and **multiple-revision** (blue/green). Multiple-revision splits traffic by weight:

```bash
az containerapp ingress traffic set --name orders-api -g rg-yourco-prod \
  --revision-weight orders-api--abc123=10 orders-api--xyz789=90
```

The pattern: deploy a new revision at 0%, smoke it, ramp to 100%, then deactivate the old.

### Autoscaling

KEDA scalers built in. Common patterns:

- **HTTP concurrency**: scale up when concurrent requests per replica > N
- **CPU**: target 60% utilization
- **Queue depth**: Service Bus / Storage Queue scaler with `messageCount`
- **Cron**: time-of-day scaling for known traffic patterns

**Min 2 replicas** in production for AZ failover (Container Apps spreads across AZs automatically in supported regions). Scale-to-zero is only safe for backgrounds / low-priority endpoints.

## Azure Functions — recipe

### When Functions is right

- Per-request work that finishes within the plan's timeout (5 min Consumption, 10 min default Premium, configurable to 60 min)
- Stateless (state in Cosmos / SQL / Storage / Service Bus)
- Bursty / unpredictable traffic
- Rich triggers (HTTP, Queue, Service Bus, Event Grid, Event Hub, Cosmos Change Feed, Timer)

### Hosting plans

| Plan | When |
|---|---|
| **Consumption** | True scale-to-zero; cold starts in seconds; per-execution billing |
| **Flex Consumption** | Newer; better cold starts, configurable instance memory; VNet support |
| **Premium (EP)** | Pre-warmed instances, no cold start, VNet-integrated, longer timeout — pay for keep-warm |
| **App Service Plan** | When running alongside App Service apps to share compute — rarely the right call |

Prefer **Flex Consumption** for new HTTP triggers needing VNet + low cold start. Premium when you can't tolerate any cold start.

### Function basics (Node 20 + TypeScript example, v4 programming model)

```typescript
import { app, HttpRequest, InvocationContext } from '@azure/functions';

app.http('orders-get', {
  methods: ['GET'],
  authLevel: 'function',
  route: 'orders/{id}',
  handler: async (req: HttpRequest, ctx: InvocationContext) => {
    const id = req.params.id;
    return { jsonBody: await getOrder(id) };
  },
});
```

### Identity & secrets

Managed Identity on the Function App. Reference Key Vault secrets in app settings via the `@Microsoft.KeyVault(SecretUri=https://kv-orders.vault.azure.net/secrets/db-password/)` syntax — no code in the function reads Key Vault directly.

## App Service — recipe

Code-only deploy without managing containers. Two scenarios where it remains the right choice:

- Migrating an existing .NET / Node web app that doesn't need container customization
- Web apps that benefit from App Service's **Deployment Slots** (staging → swap to prod, atomic), **Authentication / Authorization** ("Easy Auth"), and SCM/Kudu

```bash
az webapp create \
  --name orders-api \
  --resource-group rg-yourco-prod \
  --plan asp-yourco-prod \
  --runtime "DOTNETCORE:8.0"
az webapp identity assign --name orders-api --resource-group rg-yourco-prod
az webapp config appsettings set --name orders-api --resource-group rg-yourco-prod \
  --settings DB_PASSWORD='@Microsoft.KeyVault(SecretUri=https://kv-orders.vault.azure.net/secrets/db-password/)'

# Slot-based deploy
az webapp deployment slot create --name orders-api -g rg-yourco-prod --slot staging
az webapp deploy --name orders-api -g rg-yourco-prod --slot staging --src-path ./publish.zip --type zip
az webapp deployment slot swap --name orders-api -g rg-yourco-prod --slot staging --target-slot production
```

Deployment Slots are App Service's killer feature — atomic swap with optional warm-up requests.

## Static Web Apps — SPA hosting

```bash
swa deploy --env production --deployment-token "$SWA_DEPLOYMENT_TOKEN"
```

Or wire `Azure/static-web-apps-deploy@v1` (GitHub Action) — the SWA workflow handles build + upload. Built-in features:

- Free TLS cert + custom domain
- Routing config in `staticwebapp.config.json` (fallback to `index.html` for SPA routes, headers, auth/role gates)
- Paired Azure Functions API (under `/api/`) — handy for thin BFFs
- Preview environments per PR

For frontends that exceed the SWA paired-API limits, use **Storage Static Website** + **Front Door** instead (full CDN, WAF, multi-origin routing).

## AKS — when (rarely)

Same logic as EKS — only when k8s expertise + workload complexity justify it. For most teams Container Apps is the right destination. AKS is right when:

- Argo / Flux / KEDA-as-CRDs / Istio / custom CRDs are in scope
- > 20 services and the platform investment pays back
- Bring-your-own-VNet networking that Container Apps can't satisfy

## Identity & secrets

- **Managed Identity** (system or user-assigned) for every Azure service
- User-assigned MI shared across one logical app's resources (Container App + ACR + Key Vault + Service Bus + Storage)
- **No service principal client secrets** in apps; for pipelines use **Workload Identity Federation** (see `devops/azure-pipelines`, `devops/github-actions`)
- **Key Vault** is the secret store; access via Managed Identity with **Key Vault Secrets User** role
- For per-environment secrets, use separate Key Vaults per env, not one shared

## Networking

- **VNet integration** required for prod Container Apps / Functions / App Service that touch private dependencies (Postgres Flexible Server, internal services)
- **Private Endpoints** for PaaS services (SQL, Storage, Key Vault, Cosmos) — block public traffic
- **NSGs** + **Application Security Groups** for service-to-service rules
- **Azure Firewall** or **NVA** for egress filtering when compliance requires it
- **Front Door** or **Application Gateway** as the public ingress with WAF

## Observability

- **Log Analytics workspace** is the default sink — Container Apps, App Service, Functions, AKS all write here
- **Application Insights** for app-side traces / metrics — Auto-Instrumentation supported for .NET / Java / Node
- For cross-stack OTel uniformity, ship via the **OTel Collector** (deployed as a Container App or AKS workload) to Tempo / Prometheus / Loki — same pattern as on AWS
- **Azure Monitor Alerts** on Container App `Requests`, `RestartCount`; Functions `FunctionErrors`, `FunctionExecutionUnits`; SQL `dtu_used_percent`

## Rules

- One Azure subscription per environment (or at least separate resource groups with strict RBAC); Management Groups at the org level for policy
- **Azure Policy** enforces guardrails — deny public IPs on PaaS, enforce private endpoints on storage, require tags
- All resources tagged: `env`, `service`, `owner`, `cost_center`
- Min 2 replicas in production; multi-AZ where the service tier supports it
- Image tags immutable (`:sha-abc123`); never `:latest`
- Secrets in Key Vault, referenced by Managed Identity; never in app settings as plaintext
- Public ingress is **Application Gateway** or **Front Door** with WAF; internal ingress within the VNet
- Cost guardrails: Cost Management budgets per RG; alerts at 80% of expected; reservation purchases for predictable workloads

## What NOT to do

- No service principal secrets in app config — Managed Identity only
- No public Storage Account / Blob with anonymous read (except deliberate static site origins fronted by Front Door)
- No `:latest` image tags in production
- No `0.0.0.0` rules in NSGs — restrict by source ASG or IP
- No single-replica Container App in production
- No Functions Consumption for endpoints that can't tolerate occasional cold starts (use Premium / Flex)
- No App Service deploy without slot-and-swap once you have prod traffic
- No Static Web Apps with auth gated only by `staticwebapp.config.json` for sensitive content — pair with Auth0 / Entra ID and validate in the API
- No "shared Key Vault across all envs" — separate per env
- No AKS for a 3-service team — Container Apps will scale further than you'd guess

## Generation steps

1. Confirm workload shape and pick the target (Container Apps / Functions / App Service / Static Web Apps / AKS).
2. Ensure prerequisite infra exists (RG, VNet, ACR, Key Vault, Log Analytics) — hand off to `devops/iac-bicep-terraform` for Bicep.
3. Produce the deployable artifact: Dockerfile + image push (Container Apps), Function code (Functions), zip / code (App Service), SPA build output (Static Web Apps).
4. Wire the pipeline (`devops/azure-pipelines` / `devops/github-actions` / `devops/gitlab-ci`) with WIF + the deploy step (`az containerapp update`, `func azure functionapp publish`, `swa deploy`, slot swap).
5. Smoke: hit `/health` after deploy; confirm Log Analytics receives logs; confirm Application Insights or OTel Collector receives traces/metrics.

## Handoffs

- IaC (Bicep / Terraform) → `devops/iac-bicep-terraform`
- Pipelines → `devops/azure-pipelines` / `devops/github-actions` / `devops/gitlab-ci`
- App-level config & secrets injection → `devops/environment-config` (when authored)
- Logging → `observability/structured-logging-{dotnet,java,node}`
- Tracing/metrics → `observability/opentelemetry-{dotnet,java,node}`
- AWS equivalent → `devops/aws-deployment`
