---
name: devops-aws-deployment
description: Use when the user asks to deploy a service to AWS — ECS Fargate (default for long-running containers), Lambda (event-driven / API Gateway), App Runner (simplest container option), S3 + CloudFront (static frontends / SPAs), or EKS (Kubernetes). Triggers: "deploy this .NET service to ECS", "ship a Lambda from a Node TS handler", "host the React SPA on S3 + CloudFront", "switch this from App Runner to ECS". Do NOT use for Azure (use `devops/azure-deployment`), IaC scripts (use `devops/iac-bicep-terraform`), or pipeline YAML (use `devops/{github-actions,gitlab-ci,azure-pipelines}`).
---

# DevOps — AWS Deployment

Deploys services to AWS using the right primitive for the workload. Default for long-running container services is **ECS Fargate** (serverless containers, no nodes to patch). For event-driven / per-request workloads, **Lambda** behind API Gateway or directly via a Function URL. For SPAs, **S3 + CloudFront with OAC**. EKS only when the team has earned the Kubernetes overhead.

**Version policy:** detect the project's versions (TFM / `engines` / toolchain) and match — never assume. .NET 10 is primary, 8/9 supported (8 LTS ends Nov 2026). Node 20 is EOL (Apr 2026) — 24 is active LTS, 22 maintenance. Java 21 LTS is the default. **Managed runtimes lag the language**: pin to the newest runtime the platform actually offers for the project's major, and never silently up-level the app to reach one.

## Stack

- **AWS**: ECS Fargate, Lambda, App Runner, S3, CloudFront, ECR, IAM, CloudWatch Logs, Secrets Manager / Parameter Store, AWS Certificate Manager
- **Backends**: .NET 10 (8/9 supported) / Java 21 / Node 24 (22 maintenance) — all targets are Linux container images or Lambda runtimes
- **Frontend**: React SPA → S3 + CloudFront; Blazor WASM → same; Blazor Server → ECS Fargate
- IAM via **roles**, not users — services authenticate via IRSA (EKS), Task Role (ECS), or Execution Role (Lambda)
- IaC via Terraform (preferred) or AWS CDK — see `devops/iac-bicep-terraform`
- Pipelines via GitHub Actions / GitLab CI / Azure Pipelines using OIDC (no long-lived keys)

## When to use

- New service needs a deploy target on AWS
- Migrating a workload between targets (Lambda → ECS, App Runner → ECS, EC2 → Fargate)
- Setting up the deploy pipeline's *destination* (the pipeline itself lives in `devops/github-actions` etc.)
- Choosing among AWS primitives for a specific workload

## When NOT to use

- Azure → `devops/azure-deployment`
- IaC syntax → `devops/iac-bicep-terraform`
- Pipeline YAML → `devops/github-actions` / `devops/gitlab-ci` / `devops/azure-pipelines`
- App-level config / secrets injection → `devops/environment-config`

## Picking the right target

| Workload | Default target | Use because |
|---|---|---|
| Long-running web API or background worker | **ECS Fargate** | Containers, no node management, predictable cost, VPC-native |
| Spiky / event-driven API | **Lambda + API Gateway** | Pay-per-request, scales to zero, no idle cost |
| Simplest container demo / internal tool | **App Runner** | Source/repo-to-URL in minutes, but limited networking & scaling controls |
| SPA / static site | **S3 + CloudFront (OAC)** | Cheap, fast, edge-cached |
| Already running Kubernetes elsewhere | **EKS** | Only when k8s expertise + workload complexity justify it |

Rule of thumb: start with **ECS Fargate** for services, **Lambda** for handlers that fit the model (<15 min, stateless, manageable cold start), **S3 + CloudFront** for static UIs.

## ECS Fargate — recipe

### Required resources

- **ECR repository** per service (`yourco/orders-api`)
- **ECS cluster** per env (`yourco-prod`)
- **Task definition** describing one container per service (Linux/X86_64 or ARM64)
- **ECS service** running N tasks behind an **Application Load Balancer** (or **NLB** for non-HTTP)
- **Target group** with health checks pointing at `/health`
- **VPC** with private subnets for tasks, public for the ALB
- **Security groups** — ALB-only ingress to tasks
- **Task role** (what the app can do) + **Execution role** (pulling image, writing logs)

### Task definition essentials

```jsonc
{
  "family": "orders-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecution",
  "taskRoleArn":      "arn:aws:iam::123456789012:role/orders-api-task",
  "containerDefinitions": [
    {
      "name": "app",
      "image": "123456789012.dkr.ecr.eu-west-1.amazonaws.com/orders-api:<sha>",
      "essential": true,
      "portMappings": [{ "containerPort": 8080, "protocol": "tcp" }],
      "environment": [
        { "name": "OTEL_EXPORTER_OTLP_ENDPOINT", "value": "http://otel-collector.observability.svc:4317" }
      ],
      "secrets": [
        { "name": "DB_PASSWORD",   "valueFrom": "arn:aws:secretsmanager:eu-west-1:...:secret:orders/db-password" },
        { "name": "AUTH0_M2M_SECRET","valueFrom": "arn:aws:secretsmanager:eu-west-1:...:secret:orders/auth0-m2m" }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/orders-api",
          "awslogs-region": "eu-west-1",
          "awslogs-stream-prefix": "app"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -fsS http://localhost:8080/health || exit 1"],
        "interval": 30, "timeout": 5, "retries": 3, "startPeriod": 30
      }
    }
  ]
}
```

`secrets` (Secrets Manager / SSM Parameter Store) are injected as env vars at task start by the **execution role** — never bake into the image. `awsvpc` networking gives each task its own ENI; security group ingress from the ALB SG.

### Deploy step (from pipeline)

```bash
# Build & push
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_HOST
docker buildx build --platform linux/amd64 -t $ECR_HOST/orders-api:$SHA --push .

# Update task definition image, register new revision, update service
TASK_DEF=$(aws ecs describe-task-definition --task-definition orders-api --query 'taskDefinition' --output json \
  | jq --arg img "$ECR_HOST/orders-api:$SHA" '.containerDefinitions[0].image = $img
        | del(.taskDefinitionArn,.revision,.status,.requiresAttributes,.compatibilities,.registeredAt,.registeredBy)')

NEW_REV=$(aws ecs register-task-definition --cli-input-json "$TASK_DEF" --query 'taskDefinition.taskDefinitionArn' --output text)
aws ecs update-service --cluster yourco-prod --service orders-api --task-definition "$NEW_REV"
aws ecs wait services-stable --cluster yourco-prod --services orders-api
```

Rolling deploys are the default. For zero-downtime with health gating, use **CodeDeploy** + **blue/green** on the ECS service.

### Autoscaling

Target tracking on **CPU utilization** (50%) or **ALB request count per target**. Schedule scheduled scaling for known-traffic patterns. **Min 2 tasks** in production for AZ failover.

## Lambda — recipe

### When Lambda is right

- Per-request work that finishes in ≤15 min
- Stateless (state lives in DynamoDB / RDS / SQS)
- Bursty / unpredictable traffic
- Cron / event triggers (CloudWatch Events, S3 events, SQS, DynamoDB Streams, EventBridge)

### Function basics

```yaml
# template.yaml (SAM example; Terraform / CDK equivalents apply the same shape)
Resources:
  OrdersFunction:
    Type: AWS::Serverless::Function
    Properties:
      Runtime: nodejs22.x          # newest Lambda-managed runtime for the project's major;
                                   # or dotnet8 / java21 — match the app, never up-level it to fit
      Architectures: [arm64]       # 20% cheaper than x86, slightly faster on ARM-friendly libs
      Handler: dist/handler.handler
      MemorySize: 512
      Timeout: 30
      Environment:
        Variables:
          OTEL_EXPORTER_OTLP_ENDPOINT: !Ref OtelEndpoint
      Tracing: Active              # X-Ray; combine with OTel for trace export
      Policies:
        - DynamoDBReadPolicy: { TableName: !Ref OrdersTable }
      Events:
        Api:
          Type: HttpApi
          Properties:
            Path: /orders/{id}
            Method: GET
```

### Cold start mitigation

- **Provisioned concurrency** for latency-sensitive endpoints (cost trade-off vs warm tasks on ECS)
- **SnapStart** for Java (Lambda restores from a snapshot — dramatic improvement)
- **Native AOT** for .NET Lambda (Linux container image with `dotnet publish -r linux-arm64 -c Release`)
- Avoid heavy initialization in the global scope of Node — but cache DB clients / SDKs there once

### Limits to remember

- 15-minute max execution time → not for batch / long workflows; use Step Functions
- 10 GB max ephemeral storage; payload limits (6 MB sync, 256 KB async)
- Concurrent execution limits per region — request increases before launch

## App Runner — recipe

Simplest container service. Source from ECR or a Git repo; AWS builds and hosts. No VPC control unless you configure VPC connectors. Good for internal tools, prototypes, single-service deploys where ECS feels like overkill. Move to ECS when you need fine-grained networking, sidecars, or > one container per service.

```bash
aws apprunner create-service \
  --service-name orders-api \
  --source-configuration "ImageRepository={ImageIdentifier=$ECR_HOST/orders-api:$SHA,ImageRepositoryType=ECR,ImageConfiguration={Port=8080}}" \
  --instance-configuration "Cpu=1 vCPU,Memory=2 GB,InstanceRoleArn=arn:aws:iam::...:role/orders-app-runner-task"
```

## S3 + CloudFront — SPA hosting

For a React SPA / Blazor WASM build output:

1. **S3 bucket**, block all public access; bucket policy allows **only** CloudFront via **Origin Access Control (OAC)**
2. **CloudFront distribution** with the bucket as the origin, OAC enabled
3. **Custom domain** + **ACM certificate** in `us-east-1` (CloudFront's region)
4. **Default root object**: `index.html`
5. **Custom error responses**: `403`/`404` → `/index.html` with 200 (SPA routing)
6. **Cache policy**: long TTL for static assets (`/static/*`), no-cache for `/index.html`
7. **Invalidation** on each deploy: `aws cloudfront create-invalidation --distribution-id $ID --paths "/*"` (or scope to `/index.html` + `/asset-manifest.json` to save the per-path cost)

The OAC is non-negotiable — never make the bucket public.

## EKS — when (rarely)

Use EKS when:
- The team has existing Kubernetes operational expertise
- Workloads need ecosystem things ECS doesn't have (Argo, KEDA, Istio, custom CRDs)
- You're running > ~20 services and the platform investment pays back

Avoid for: a small number of services, a team new to k8s, or "we might need k8s later" — Fargate scales further than most expect.

## IAM

- **One role per service**, named `<service>-task` (ECS) / `<service>-execution` (Lambda)
- **Least privilege** — grant specific actions on specific resources, never `*` on `*`
- **No IAM users** in services — only roles
- **OIDC-based pipeline auth** — see the pipeline skills for the role trust policies
- **Service Control Policies** at the org level prevent dangerous resources (root user, public buckets without OAC, region restrictions)

## Networking

- **Private subnets** for tasks/functions; **public subnets** only for load balancers + NAT
- **NAT Gateway** for egress (1 per AZ in prod, single NAT in non-prod is fine — cost vs HA)
- **VPC endpoints** for S3, ECR, Secrets Manager, CloudWatch Logs — eliminates NAT egress costs and improves throughput
- **Security groups** are deny-by-default; ingress rules reference other SGs by ID (not CIDR) for service-to-service

## Observability

- **CloudWatch Logs** is the default sink for ECS / Lambda. For Grafana/Loki, deploy the OTel Collector inside the VPC and route logs (stdout JSON) via a sidecar (FireLens) or daemon (Grafana Alloy/Vector).
- **X-Ray** is fine for AWS-native traces; for cross-stack uniformity, prefer OTel via the Collector (see `observability/opentelemetry-{dotnet,java,node}`)
- **CloudWatch Alarms** on ECS service `CPUUtilization`, `MemoryUtilization`, ALB `HTTPCode_Target_5XX_Count`, Lambda `Errors` / `Throttles` / `Duration` p95

## Rules

- Multi-AZ everything in prod — min 2 tasks per service across 2 AZs; ALB across all 3 AZs
- Health checks point at `/health` (or equivalent); separate from `/ready` if needed for k8s-style readiness
- Image tags are immutable (`:sha-abc123`), never `:latest` in production
- Secrets via Secrets Manager / Parameter Store, injected as env vars by the execution role
- All outbound from private subnets goes through NAT (or VPC endpoints) — no public IPs on tasks
- Cost guardrails: AWS Budgets per project; CloudWatch billing alarm at 80% of expected
- Deletion protection on RDS, S3 buckets with content, CloudFront distributions
- One AWS account per environment (Org with prod / staging / dev accounts); cross-account IAM for shared services

## What NOT to do

- No AWS access keys baked into images or env vars — IAM roles only
- No public S3 buckets — OAC + CloudFront
- No `:latest` tags in production deploys
- No IAM policies with `Action: "*"` and `Resource: "*"`
- No `0.0.0.0/0` ingress on a task security group — ALB SG only
- No single-task ECS service in production — min 2, spread across AZs
- No Lambda for long-running batch (> 15 min) — Step Functions / ECS / Batch
- No App Runner for production-critical services that need VPC-private dependencies or multi-container — graduate to ECS
- No CloudFront distribution serving an S3 bucket via origin URL (public access enabled) — always OAC
- No region pinning to `us-east-1` for non-CloudFront resources just because it's "the default" — pick a region near users / compliance boundary

## Generation steps

1. Confirm workload shape and pick the target (ECS / Lambda / App Runner / S3+CF / EKS).
2. Ensure prerequisite infra exists (VPC, ECR repo, ALB, certs, secrets) — hand off to `devops/iac-bicep-terraform` for the Terraform.
3. Produce the deployable artifact: Dockerfile + task definition (ECS), Lambda zip / container image, or `npm run build` output (SPA).
4. Wire the pipeline (`devops/github-actions` / `gitlab-ci` / `azure-pipelines`) with OIDC role assumption + the appropriate deploy step (`ecs update-service` / `lambda update-function-code` / `s3 sync` + invalidation).
5. Smoke: hit `/health` after deploy; verify CloudWatch Logs receive logs; verify metrics arrive in Prometheus via the Collector.

## Handoffs

- IaC (Terraform/CDK) → `devops/iac-bicep-terraform`
- Pipelines → `devops/github-actions` / `devops/gitlab-ci` / `devops/azure-pipelines`
- App-level config & secrets injection → `devops/environment-config`
- Logging → `observability/structured-logging-{dotnet,java,node}`
- Tracing/metrics → `observability/opentelemetry-{dotnet,java,node}`
- Azure equivalent → `devops/azure-deployment`
