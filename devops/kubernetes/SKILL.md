---
name: devops-kubernetes
description: Use when the user asks to author Kubernetes manifests, Helm charts, Kustomize overlays, or workload patterns (Deployment, Service, Ingress, HPA, PDB, ServiceAccount + IRSA / Workload Identity) for AKS / EKS / GKE. Triggers: "write a Deployment for service X", "Helm chart for Y", "IRSA for this pod". Do NOT use for non-Kubernetes targets (`devops/{aws,azure}-deployment`), pipelines (`devops/{github-actions,gitlab-ci,azure-pipelines}`), or container build (`devops/docker`).
---

# DevOps — Kubernetes (AKS / EKS / GKE)

Authors Kubernetes manifests, Helm charts, and Kustomize overlays for the library's services on managed Kubernetes (AKS / EKS / GKE). Standardizes on **Helm charts per service** with **Kustomize overlays per environment** when needed, **Workload Identity / IRSA** for cloud access (no static keys), HPA + PDB for resilience, NetworkPolicy for isolation, and probe + resource discipline.

## When to use

- Service needs to run on Kubernetes
- Adding HPA / PDB / NetworkPolicy / ServiceMonitor to an existing workload
- Wiring Workload Identity (Azure) / IRSA (AWS) / Workload Identity (GKE) so pods can access cloud resources without secrets
- Splitting per-env config via Helm values or Kustomize overlays
- Standardizing the team's chart conventions

## When NOT to use

- ECS Fargate / Lambda / Container Apps / Static Web Apps → `devops/{aws,azure}-deployment`
- Container build / Dockerfile → `devops/docker`
- Pipeline YAML → `devops/{github-actions,gitlab-ci,azure-pipelines}`
- IaC for the cluster itself → `devops/infrastructure-as-code`

## Inputs needed

1. **Cluster**: AKS / EKS / GKE; version
2. **Service shape**: stateless HTTP, worker, scheduled job, stateful (rare)
3. **Cloud-resource access** the pod needs (DB, Key Vault / Secrets Manager, S3 / Blob, queue)
4. **Tools**: Helm + Kustomize default; ArgoCD / Flux if GitOps
5. **Ingress**: NGINX Ingress, Application Gateway Ingress Controller (Azure), AWS Load Balancer Controller, Istio gateway
6. **Per-env strategy**: Helm values files vs Kustomize overlays vs both

## The standard manifest set

Every service has the same set, named consistently:

```
charts/orders-api/
  Chart.yaml
  values.yaml
  values-dev.yaml
  values-prod.yaml
  templates/
    deployment.yaml
    service.yaml
    ingress.yaml
    hpa.yaml
    pdb.yaml
    networkpolicy.yaml
    serviceaccount.yaml
    configmap.yaml
    secretproviderclass.yaml      # Key Vault / Secrets Store CSI driver
    servicemonitor.yaml           # if Prometheus Operator
```

## Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orders-api
  labels:
    app.kubernetes.io/name: orders-api
    app.kubernetes.io/instance: orders-api
    app.kubernetes.io/component: api
    app.kubernetes.io/part-of: orders
    app.kubernetes.io/version: "{{ .Chart.AppVersion }}"
spec:
  replicas: {{ .Values.replicaCount }}
  strategy:
    type: RollingUpdate
    rollingUpdate: { maxSurge: 25%, maxUnavailable: 0 }
  revisionHistoryLimit: 5
  selector:
    matchLabels:
      app.kubernetes.io/name: orders-api
  template:
    metadata:
      labels:
        app.kubernetes.io/name: orders-api
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: orders-api
      automountServiceAccountToken: true
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 2000
        seccompProfile: { type: RuntimeDefault }
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels: { app.kubernetes.io/name: orders-api }
      containers:
        - name: app
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8080
              protocol: TCP
          env:
            - name: OTEL_EXPORTER_OTLP_ENDPOINT
              valueFrom:
                configMapKeyRef: { name: orders-api, key: otelEndpoint }
          envFrom:
            - configMapRef: { name: orders-api }
          volumeMounts:
            - name: secrets
              mountPath: /mnt/secrets
              readOnly: true
          resources:
            requests:
              cpu: "200m"
              memory: "256Mi"
            limits:
              cpu: "1"
              memory: "1Gi"
          readinessProbe:
            httpGet: { path: /health/ready, port: http }
            initialDelaySeconds: 10
            periodSeconds: 5
            failureThreshold: 3
          livenessProbe:
            httpGet: { path: /health/live, port: http }
            initialDelaySeconds: 30
            periodSeconds: 15
            failureThreshold: 3
          startupProbe:
            httpGet: { path: /health/ready, port: http }
            failureThreshold: 30
            periodSeconds: 5
          lifecycle:
            preStop:
              exec: { command: ["/bin/sh", "-c", "sleep 5"] }
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: { drop: ["ALL"] }
      volumes:
        - name: secrets
          csi:
            driver: secrets-store.csi.k8s.io
            readOnly: true
            volumeAttributes:
              secretProviderClass: orders-api
```

Key points:

- **Resource `requests` are mandatory** — without them HPA / scheduler can't reason about the pod. `limits` recommended but think before setting CPU limits (Linux CFS throttling pitfall).
- **`runAsNonRoot: true` + readOnlyRootFilesystem** — defense in depth at the runtime layer
- **Three probes** — `startupProbe` to give slow-start apps time, `livenessProbe` to recycle hung pods, `readinessProbe` to gate traffic. Distinct endpoints when the meanings differ (live = process alive; ready = ready to take traffic, e.g., warm cache + DB pool up).
- **`preStop` sleep** to give the ingress / kube-proxy time to deregister the pod before SIGTERM — kills 502s during rollout
- **`terminationGracePeriodSeconds`** — give the app time to finish in-flight requests
- **`topologySpreadConstraints`** — spread pods across zones for AZ resilience
- **`revisionHistoryLimit: 5`** — keep rollouts smaller in etcd

## Service & Ingress

```yaml
apiVersion: v1
kind: Service
metadata:
  name: orders-api
spec:
  type: ClusterIP                       # default; ingress fronts the cluster
  ports:
    - name: http
      port: 80
      targetPort: http
  selector:
    app.kubernetes.io/name: orders-api
```

Ingress (NGINX example):

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: orders-api
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: "4m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "30"
spec:
  ingressClassName: nginx
  tls:
    - hosts: [api.yourco.com]
      secretName: api-yourco-com-tls
  rules:
    - host: api.yourco.com
      http:
        paths:
          - path: /orders
            pathType: Prefix
            backend:
              service:
                name: orders-api
                port: { name: http }
```

For AKS: **Application Gateway Ingress Controller** (AGIC) or NGINX. For EKS: **AWS Load Balancer Controller**. The ingress resource itself is mostly portable; the annotations change per controller.

## HPA + PDB

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: { name: orders-api }
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: orders-api }
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 60 } }
    - type: Resource
      resource: { name: memory, target: { type: Utilization, averageUtilization: 75 } }
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies: [{ type: Percent, value: 50, periodSeconds: 60 }]
    scaleUp:
      stabilizationWindowSeconds: 30
      policies: [{ type: Percent, value: 100, periodSeconds: 30 }]
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: { name: orders-api }
spec:
  minAvailable: 2
  selector:
    matchLabels: { app.kubernetes.io/name: orders-api }
```

For request-rate scaling, install **KEDA** and use its `ScaledObject` with the right scaler (HTTP, Service Bus, Kafka, Pub/Sub) — much better than `cpu` alone for asymmetric workloads.

## NetworkPolicy

Default-deny per namespace plus allow rules per service:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: orders-api-allow-ingress }
spec:
  podSelector: { matchLabels: { app.kubernetes.io/name: orders-api } }
  policyTypes: [Ingress]
  ingress:
    - from:
        - namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: ingress-nginx } }
        - podSelector: { matchLabels: { app.kubernetes.io/name: cart-api } }
      ports:
        - port: http
          protocol: TCP
```

Pair with `default-deny` for the namespace to enforce zero-trust between services.

## Identity & secrets

### Azure (AKS) — Workload Identity

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: orders-api
  annotations:
    azure.workload.identity/client-id: "<client-id-of-user-assigned-mi>"
```

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    metadata:
      labels:
        azure.workload.identity/use: "true"
```

The pod receives a federated token; the MI accesses Key Vault, Storage, etc. with **no client secret in the cluster**.

For secret material, mount **Key Vault via the Secrets Store CSI Driver**:

```yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata: { name: orders-api }
spec:
  provider: azure
  parameters:
    clientID: "<mi-client-id>"
    tenantID: "<tenant-id>"
    usePodIdentity: "false"
    useVMManagedIdentity: "false"
    keyvaultName: kv-orders
    objects: |
      array:
        - |
          objectName: db-password
          objectType: secret
```

The secret is materialized as a file under `/mnt/secrets/db-password` (no `Secret` resource needed). For env-var injection there's a `secretObjects` block that creates a paired `Secret`.

### AWS (EKS) — IRSA

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: orders-api
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/orders-api
```

The pod's `AWS_ROLE_ARN` env is automatically set; the AWS SDK exchanges the projected token for credentials. No keys in the cluster.

For secrets, **Secrets Store CSI Driver with AWS provider** or **External Secrets Operator** (pulls from Secrets Manager / Parameter Store into a `Secret`).

### GKE — Workload Identity

Same pattern: `iam.gke.io/gcp-service-account: ...@<project>.iam.gserviceaccount.com` annotation; pod inherits the GSA.

## Observability hooks

- **Prometheus annotations** or `ServiceMonitor` (Prometheus Operator) — wire metrics scrape
- **OTel exporter endpoint** configured via env / ConfigMap
- **Pod labels** kept consistent with the OTel resource attributes — `service.name=<app.kubernetes.io/name>`

## Per-env config

Two viable strategies, sometimes both:

### Helm values per env

```
charts/orders-api/
  values.yaml           # defaults
  values-dev.yaml       # dev overrides
  values-prod.yaml      # prod overrides
```

```bash
helm upgrade --install orders-api ./charts/orders-api -f values-prod.yaml --set image.tag=$SHA
```

### Kustomize overlays per env

```
manifests/
  base/
    deployment.yaml
    kustomization.yaml
  overlays/
    dev/
      kustomization.yaml
      replicas-patch.yaml
    prod/
      kustomization.yaml
      replicas-patch.yaml
      resources-patch.yaml
```

```bash
kubectl apply -k manifests/overlays/prod
```

Use **Helm** for chart-as-product reuse (publishing reusable charts); **Kustomize** for env-specific tweaks of a base. The combo (Helm chart + Kustomize overlay) is fine; pick one as the source of truth and use the other for tweaks.

## GitOps

- **ArgoCD** or **Flux** to reconcile cluster state from Git
- One `Application` (Argo) / `Kustomization` (Flux) per service per env
- Image updates via **Argo Image Updater** / **Flux Image Automation** — write back the new tag to Git
- Pipelines push images and bump the tag in Git; the controller does the apply

GitOps replaces `kubectl apply` from CI. Pipelines author the change; the cluster reconciles.

## Rollouts

- **RollingUpdate** is the default (`maxSurge: 25%, maxUnavailable: 0`)
- **Argo Rollouts** for blue/green, canary, traffic-splitting via service mesh; install only when you've earned the complexity
- **`preStop` sleep + `terminationGracePeriodSeconds`** prevent 502s during rolling deploys
- **PDB** prevents drain operations (node upgrades) from taking everything down

## Rules

- Every workload has `requests` and (usually) `limits`
- Every pod has all three probes (startup / readiness / liveness)
- Every pod is non-root with read-only root filesystem
- Every pod has `seccompProfile: RuntimeDefault` + dropped capabilities
- Every workload has an HPA + PDB (PDB even for single-replica when applicable)
- Every service has a NetworkPolicy (default-deny + explicit allow)
- Every workload uses Workload Identity / IRSA — no service principal / IAM keys in `Secret`
- Secrets mounted via CSI driver or External Secrets Operator
- Labels follow `app.kubernetes.io/*` recommended set
- Image tags pinned (immutable `:sha-abc123`); never `:latest`
- Topology spread across zones
- `terminationGracePeriodSeconds` + `preStop` sleep for graceful shutdown

## What NOT to do

- No pods without `requests`
- No `:latest` image tags
- No root user; no privileged containers
- No long-lived `Secret` objects holding cloud credentials
- No `hostNetwork` / `hostPID` / `hostIPC` without a documented reason
- No `imagePullPolicy: Always` for SHA-tagged images — `IfNotPresent` saves pulls
- No services without NetworkPolicy in a zero-trust posture
- No `nodeSelector` for "scheduling fairness" — use topology spread
- No skipping PDBs on multi-replica workloads
- No mixing `kubectl apply` from CI and GitOps reconciliation — pick one
- No giant Helm charts that template everything — keep templates close to the resources; flat is better than clever
- No `subPath` mounts without `subPathExpr` for parameterization
- No `kubectl patch` in CI as a substitute for declarative config

## Generation steps

1. Confirm cluster (AKS / EKS / GKE), workload shape, cloud-resource access, ingress controller, GitOps tool.
2. Pick Helm chart vs raw manifests + Kustomize. Helm for reusable charts; raw + Kustomize for one-off services.
3. Generate the manifest set from the template (Deployment + Service + Ingress + HPA + PDB + NetworkPolicy + SA + CSI SPC).
4. Annotate the ServiceAccount for Workload Identity / IRSA.
5. Wire metrics scrape + OTel endpoint.
6. Add per-env values / overlays.
7. If GitOps is in scope, register the service with Argo / Flux.
8. Smoke against a cluster: `kubectl rollout status`; `kubectl describe pod` for events; check logs via Loki.

## Handoffs

- Container image build → `devops/docker`
- IaC for the cluster itself → `devops/infrastructure-as-code`
- Pipeline that builds + pushes + reconciles → `devops/{github-actions,gitlab-ci,azure-pipelines}`
- Cloud deploy alternatives (Container Apps / ECS / App Service / Static Web Apps) → `devops/{aws,azure}-deployment`
- App-side config / secrets → `devops/environment-config`
- Observability inside pods → `observability/opentelemetry-{stack}` + `observability/structured-logging-{stack}`
