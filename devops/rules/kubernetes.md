---
paths:
  - "**/{k8s,kubernetes,manifests,deploy,charts,helm,overlays}/**/*.{yml,yaml}"
  - "**/kustomization.{yml,yaml}"
---

<!-- devops rules v1 (2026-11-03): Kubernetes. Installed by /devops:rules; manifests have no fixed path, so add the folders this project keeps them in. -->

# Kubernetes manifest standards (raw, Helm, Kustomize)

Severity tags as in the core devops rules.

- Every container sets `requests`, and usually `limits`. *major*
- Startup, readiness and liveness probes on every long-running container. *major*
- Pod and container `securityContext`: `runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`, capabilities dropped, `seccompProfile: RuntimeDefault`. *major*
- No privileged container; no `hostNetwork`, `hostPID` or `hostIPC` without a written reason. *blocker*
- Every namespace carries a `pod-security.kubernetes.io/enforce` label; an unlabelled one admits privileged pods. *major*
- `automountServiceAccountToken: false` unless the workload calls the API server. *minor*
- Every namespace has a default-deny NetworkPolicy plus explicit allows. *major*
- Cloud access through Workload Identity or IRSA on the service account; secrets mounted through the CSI driver or External Secrets Operator, never a `Secret` holding cloud credentials. *blocker*
- Production runs at least two replicas with an HPA, a PDB and topology spread across zones; `nodeSelector` is not a spreading tool. *major*
- `terminationGracePeriodSeconds` and a `preStop` sleep for graceful shutdown. *minor*
- `imagePullPolicy: IfNotPresent` for immutable tags. *nit*
- Labels from the `app.kubernetes.io/*` recommended set. *nit*
- Per-environment differences are Helm values files or Kustomize overlays, never copied manifests; chart templates stay flat and close to the resources they render. *minor*
