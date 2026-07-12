---
name: devops-iac-bicep-terraform
description: Use when the user asks to author Infrastructure as Code with Bicep (Azure) or Terraform (multi-cloud / AWS). Triggers: "write Bicep for X", "Terraform module for Y", "wire up an Azure Container App in Bicep", "Terraform provider for AWS ECS", "should this be Bicep or Terraform", "module structure for our IaC repo". Do NOT use for pipeline YAML (use `devops/{github-actions,gitlab-ci,azure-pipelines}`), app deploys (use `devops/{aws,azure}-deployment`), or app-level config (use `devops/environment-config`).
---

# DevOps — Infrastructure as Code (Bicep & Terraform)

Authors IaC for the cloud resources the library deploys to. **Bicep** when the project is Azure-only and the team values Microsoft-native syntax; **Terraform** when the project is AWS, multi-cloud, or already invested in HCL. The same standards apply to both: modules, environments via stacks/workspaces, state in remote backends, drift detection, and IaC tested before merge.

## When to use

- New project needs its first IaC
- Adding a new resource (Container App, ECS service, Lambda, Cosmos DB, Postgres) to an existing project
- Splitting a monolithic Terraform / Bicep file into modules
- Setting up remote state / state locking
- Migrating from one IaC tool to the other (rare; usually only when the tooling story changes)

## When NOT to use

- Pipeline YAML → `devops/{github-actions,gitlab-ci,azure-pipelines}`
- Cloud-specific app deploy → `devops/{aws,azure}-deployment`
- App-level config / secrets pulled at runtime → `devops/environment-config`

## Inputs needed

1. **Tool**: Bicep or Terraform — pick by team / cloud
2. **Cloud(s)**: AWS / Azure / both
3. **Resources** to provision (list)
4. **Environments**: dev / staging / prod (and their isolation — subscription/account per env preferred)
5. **State backend**: Terraform Cloud, S3 + DynamoDB, Azure Storage with blob lease
6. **Pipeline** that runs `terraform plan` / `bicep build` / `az deployment` per change

## Picking the tool

| Choose Bicep | Choose Terraform |
|---|---|
| Azure-only stack | AWS, or multi-cloud, or any non-Azure provider needed |
| Team prefers Microsoft tooling (VS Code Bicep extension, Azure CLI) | Team prefers HCL + provider ecosystem |
| All resources are AzureRM-supported | Resources include non-Azure services (Auth0, Datadog, GitHub) |
| Closer to ARM, no module registry maturity needed | Need shared modules across teams via a registry |

Either is fine in 2026. **Don't mix them in the same scope** — pick one and stay consistent.

## Repo layout

```
infra/
  modules/
    container-app/
      main.bicep | main.tf
      variables.bicep | variables.tf
      outputs.bicep | outputs.tf
      README.md
    postgres/
    keyvault/
  environments/
    dev/
      main.bicep | main.tf
      backend.tf       (Terraform only)
      env.bicepparam | terraform.tfvars
    staging/
    prod/
  pipelines/
    plan.yml
    apply.yml
```

Per-env folder owns its **stack** (set of resources for that environment). Modules are shared, versioned (Terraform: tagged repo refs; Bicep: registry or relative paths), and have a README naming inputs/outputs.

## State (Terraform)

State **must** be remote and locked. Local state is for prototypes only.

| Backend | Cloud | Locking |
|---|---|---|
| **Terraform Cloud / Enterprise** | Any | Built-in |
| **S3 + DynamoDB** | AWS | DynamoDB for lock |
| **Azure Storage + Blob Lease** | Azure | Native blob lease |

```hcl
# environments/prod/backend.tf
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-tfstate-prod"
    storage_account_name = "tfstateprodyourco"
    container_name       = "tfstate"
    key                  = "orders/prod.tfstate"
    use_oidc             = true                # Workload Identity, no keys
  }
}
```

**Never** commit state to Git. **Always** lock on apply.

## Bicep — example module

```bicep
// modules/container-app/main.bicep
@description('Name of the Container App')
param name string

@description('Image to deploy')
param image string

@description('Container App Environment resource id')
param environmentId string

@description('User-assigned managed identity resource id')
param managedIdentityId string

@description('Min replicas')
@minValue(0)
param minReplicas int = 2

@description('Max replicas')
@minValue(1)
param maxReplicas int = 10

@description('Container Registry server')
param registryServer string

@description('Environment variables (non-secret)')
param envVars array = []

@description('Secrets bound from Key Vault')
param secrets array = []

@description('Tags')
param tags object = {}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: resourceGroup().location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${managedIdentityId}': {} }
  }
  properties: {
    environmentId: environmentId
    configuration: {
      ingress: { external: true, targetPort: 8080, transport: 'http' }
      registries: [{ server: registryServer, identity: managedIdentityId }]
      secrets: secrets
    }
    template: {
      containers: [{
        name: 'app'
        image: image
        env: envVars
        resources: { cpu: json('0.5'), memory: '1.0Gi' }
        probes: [{ type: 'Liveness', httpGet: { path: '/health', port: 8080 } }]
      }]
      scale: { minReplicas: minReplicas, maxReplicas: maxReplicas }
    }
  }
}

output fqdn string = app.properties.configuration.ingress.fqdn
output principalId string = managedIdentityId
```

Consumer:

```bicep
// environments/prod/main.bicep
targetScope = 'resourceGroup'

param image string

module ordersApi '../../modules/container-app/main.bicep' = {
  name: 'orders-api'
  params: {
    name: 'orders-api'
    image: image
    environmentId: cae.id
    managedIdentityId: mi.id
    minReplicas: 3
    maxReplicas: 20
    registryServer: '${acr.name}.azurecr.io'
    envVars: [
      { name: 'OTEL_EXPORTER_OTLP_ENDPOINT', value: 'http://otel-collector.internal:4317' }
    ]
    secrets: [
      { name: 'db-password', keyVaultUrl: '${kv.properties.vaultUri}secrets/db-password', identity: mi.id }
    ]
    tags: { env: 'prod', service: 'orders' }
  }
}
```

Bicep files are evaluated client-side and submitted as ARM templates; review diffs in PR as you would code.

## Terraform — example module

```hcl
# modules/container-app/main.tf
variable "name"                  { type = string }
variable "image"                 { type = string }
variable "environment_id"        { type = string }
variable "managed_identity_id"   { type = string }
variable "min_replicas"          { type = number; default = 2 }
variable "max_replicas"          { type = number; default = 10 }
variable "registry_server"       { type = string }
variable "env_vars"              { type = map(string); default = {} }
variable "secrets" {
  type = list(object({
    name         = string
    key_vault_id = string
  }))
  default = []
}
variable "tags" { type = map(string); default = {} }

resource "azurerm_container_app" "this" {
  name                         = var.name
  resource_group_name          = data.azurerm_resource_group.this.name
  container_app_environment_id = var.environment_id
  revision_mode                = "Single"
  tags                         = var.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [var.managed_identity_id]
  }

  registry {
    server   = var.registry_server
    identity = var.managed_identity_id
  }

  dynamic "secret" {
    for_each = var.secrets
    content {
      name                = secret.value.name
      key_vault_secret_id = secret.value.key_vault_id
      identity            = var.managed_identity_id
    }
  }

  template {
    min_replicas = var.min_replicas
    max_replicas = var.max_replicas

    container {
      name   = "app"
      image  = var.image
      cpu    = 0.5
      memory = "1Gi"

      dynamic "env" {
        for_each = var.env_vars
        content { name = env.key; value = env.value }
      }
    }
  }
}

output "fqdn" { value = azurerm_container_app.this.latest_revision_fqdn }
```

Same idea, HCL syntax. Variables typed; defaults explicit; `dynamic` blocks for repeated nested structures.

## Common rules (both tools)

- **Module per logical resource group** (Container App + its deps, Postgres + firewall + replica, etc.). One thing per module.
- **Inputs typed and described**; outputs documented
- **No magic strings** for resource names — derive from a name prefix variable for predictability
- **Tags everywhere** — `env`, `service`, `owner`, `cost_center` mandatory
- **Identity-based auth** — Managed Identity (Azure), IAM Role + OIDC (AWS); never service principal client secrets or IAM access keys in IaC inputs
- **State remote + locked** (Terraform); Bicep operates on the deployment, but maintain a deployment-history convention
- **Plan-before-apply** in every pipeline; require human approval on apply for prod
- **No `terraform apply` from a developer laptop against prod** — pipeline only
- **Drift detection**: scheduled plan run that fails if real state ≠ code

## Workspaces / stacks per environment

- Terraform: separate **workspaces or state files** per env; never share state across envs
- Bicep: separate `environments/<env>` directories with their own deployment scope

Either way: **one resource per env** — don't try to "deploy the same module twice in one apply for staging and prod".

## Pipeline integration

- `terraform fmt -check` + `terraform validate` + `terraform plan` on every PR
- `bicep build` + `bicep lint` + `az deployment sub what-if` on every PR
- Apply on `main` merge with environment approval (per `devops/{github-actions,gitlab-ci,azure-pipelines}`)
- Use OIDC / Workload Identity for pipeline → cloud auth — no long-lived keys

## Drift & change management

- Plan output saved as a pipeline artifact and surfaced in the PR
- Resources marked with `lifecycle { prevent_destroy = true }` (Terraform) for irreversible things (databases, Key Vaults with content)
- Manual changes in the cloud portal are forbidden — if it happens, the next plan will surface drift; reconcile by codifying or reverting
- Periodic scheduled `terraform plan` job to surface drift before someone clobbers it

## Testing IaC

- `terraform validate` + `tflint` + `tfsec` (or `checkov`) on every PR
- `bicep lint` + `psrule.rules.azure` for Azure
- Module unit tests with Terratest (Go) when modules are complex; for most apps a `plan` review is enough

## Rules

- One IaC tool per project — Bicep or Terraform, not both
- Modules small, single-purpose, versioned
- Tags mandatory on every resource (env, service, owner, cost_center)
- State remote + locked (Terraform); deployment history convention (Bicep)
- Identity-based cloud auth (Managed Identity / IAM Role) — no client secrets / access keys
- Plan-before-apply in pipeline; human approval on prod
- One environment per state / scope
- `prevent_destroy` on irreversible resources
- Drift detected by a scheduled plan
- Pipeline runs `fmt`/`validate`/`lint`/`tfsec` on PRs

## What NOT to do

- No local state in Git
- No `terraform apply` from a laptop against prod
- No mixing Bicep and Terraform on the same resources
- No shared state across environments
- No mutable cloud changes outside IaC — every change goes through a PR
- No IAM access keys / SP secrets as IaC inputs
- No untagged resources
- No `for_each` over a list when it should be a map keyed by stable identifier (causes destroy/recreate on reorder)
- No `count = var.enabled ? 1 : 0` for optional resources without `lifecycle.ignore_changes` planning
- No `null_resource` / `local-exec` doing work IaC should do declaratively
- No hard-coded resource names — use prefixes + variables

## Generation steps

1. Confirm tool (Bicep / Terraform), cloud, target resources, environments, state backend.
2. Lay out `infra/modules/` and `infra/environments/<env>/`.
3. Write **one module per logical resource group**; document inputs/outputs in module README.
4. Wire **state backend** (Terraform); confirm Workload Identity / OIDC for pipeline auth.
5. Author the per-env stack file consuming modules; pass per-env parameters.
6. Add CI to run plan-on-PR; add CD to apply-on-merge with environment approval.
7. Smoke a `plan` locally; verify resources, tags, identities, and outputs match expectations.

## Handoffs

- Pipelines that run plan/apply → `devops/{github-actions,gitlab-ci,azure-pipelines}`
- App deploy specifics built on these resources → `devops/{aws,azure}-deployment`
- App-level secrets binding → `devops/environment-config`
- Cost/budget alerts → `observability/grafana-dashboards` (when authored)
