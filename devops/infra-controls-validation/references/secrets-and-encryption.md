# Secrets management & encryption — present-AND-effective checks

The two control families that fail most often on *effectiveness* rather than *presence*: a secret store is
configured but the app still reads a literal env var; TLS is "enabled" but the plaintext port still serves.
Every check below returns a boolean and cites the exact command, so it drops into the `controls/lib.sh`
harness and reruns after `devops-engineer` remediates. Tags: `[STATIC]` file/config read (safe),
`[LIVE]` needs read access to owned infra (authorization-gated), `[ADMIN]` control-plane/node access.

Tool versions (verified 2026-08-16): External Secrets Operator **v2.6.0** · Secrets Store CSI Driver
**v1.6.0** · gitleaks **v8.30.1** (`detect`/`protect` deprecated since 8.19.0 — use `git`/`dir`) · TruffleHog
**3.96.0**.

## Family 1 — Secrets management

### The core discriminator: a store *reference*, not a literal

The whole control is "the value comes from the store at runtime, and is not a literal sitting in the workload
spec." Each platform makes the distinction visible:

`[LIVE]` **Kubernetes** — an inline `value:` is the finding; `valueFrom.secretKeyRef` is the pass. Whole-Secret
`envFrom` is a blind spot that doesn't appear under `.env`:

```bash
# Finding query — env vars with an inline literal, all namespaces.
kubectl get pods -A -o json | jq -r '
  .items[] | .metadata.namespace as $ns | .metadata.name as $pod
  | (.spec.containers[], (.spec.initContainers // [])[]) | .name as $c
  | (.env // [])[] | select(has("value"))
  | "\($ns)/\($pod)/\($c)\t\(.name)=\(.value)"'

# The envFrom blind spot — whole-Secret injection never shows in .env.
kubectl get pods -A -o json | jq -r '
  .items[] | "\(.metadata.namespace)/\(.metadata.name)" as $p
  | .spec.containers[] | (.envFrom // [])[]
  | "\($p)\tenvFrom \(.secretRef.name // .configMapRef.name)"'
```

`[LIVE]` **ECS** — the task definition splits them for you: `.environment` is plaintext (finding),
`.secrets[].valueFrom` is a store reference (pass). Also check the S3-hosted `.environmentFiles` escape hatch.

```bash
aws ecs describe-task-definition --task-definition FAMILY:REV \
  --query 'taskDefinition.containerDefinitions[].{c:name, plaintext:environment, refs:secrets[].valueFrom, files:environmentFiles}'
```

`[LIVE]` **Azure Container Apps** — `env[].value` is inline (finding), `env[].secretRef` is a reference; the
app secret itself should be a Key Vault ref (`keyVaultUrl`), not a stored literal.

```bash
az containerapp show -n APP -g RG \
  --query "properties.template.containers[].{c:name, inline:env[?value!=null].name, refs:env[?secretRef!=null].name}"
az containerapp secret list -n APP -g RG --query "[].{name:name, kvRef:keyVaultUrl}" -o table
```

`[LIVE]` **Lambda** — `Environment.Variables` are plaintext to anyone with `lambda:GetFunctionConfiguration`;
the pass is a Secrets Manager/Parameter Store fetch at init and a customer-managed KMS key on the env vars.

```bash
aws lambda get-function-configuration --function-name FN --query '{env:Environment.Variables, kms:KMSKeyArn}'
```

### The secret-shaped-value heuristic

`[STATIC]` A hit inside any of the outputs above escalates the finding from "plaintext config" to "plaintext
*secret*." One portable ERE, fed the harness output:

```bash
SECRET_RE='(A(KIA|SIA|IDA|ROA)[0-9A-Z]{16})|(-----BEGIN ([A-Z ]+ )?PRIVATE KEY-----)|(eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})|(gh[pousr]_[A-Za-z0-9]{36,255})|(xox[abposr]-[A-Za-z0-9-]{10,})|(sk-[A-Za-z0-9_-]{20,})|(AIza[0-9A-Za-z_-]{35})|(glpat-[A-Za-z0-9_-]{20,})|((?i)(pwd|password|secret|token|api[_-]?key|client[_-]?secret)\s*[=:]\s*[^ ;"'"'"',]{8,})|((?i)(postgres|postgresql|mysql|mongodb(\+srv)?|amqp|redis)://[^:/@ ]+:[^@ ]{6,}@)'
grep -EnoI "$SECRET_RE"
```

`[STATIC]` The store's own hygiene — no secret committed to the repo/history (the *presence* check that pairs
with `qa-security-secrets-scan`):

```bash
gitleaks git . --redact --report-format sarif --report-path gitleaks.sarif --exit-code 1
trufflehog git file://. --results=verified --fail        # verified = credential still authenticates
```

### K8s Secrets are base64, not encrypted — validate the two real controls

The value in a `Secret` is base64, readable by anyone with `get secrets`. The controls are **who can read**
and **etcd encryption at rest**:

`[LIVE]` Who can read (the RBAC control):

```bash
kubectl auth can-i get secrets --all-namespaces
kubectl get clusterrolebinding,rolebinding -A -o json | jq -r '
  .items[] | select(.roleRef.name | test("admin|edit|cluster-admin"))
  | "\(.kind)\t\(.metadata.namespace // "-")/\(.metadata.name)\t-> \(.roleRef.name)"'
```

`[ADMIN]` etcd encryption — the trap is that the **first** provider in the config is the write path; if it is
`identity: {}` nothing is encrypted however many providers follow. The definitive proof is reading etcd for
the `k8s:enc:` prefix:

```bash
grep -- '--encryption-provider-config' /etc/kubernetes/manifests/kube-apiserver.yaml
kubectl create secret generic enc-probe -n default --from-literal=canary=PROVE_XYZ
sudo ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  get /registry/secrets/default/enc-probe | hexdump -C | head
# PASS: payload begins k8s:enc:...  FAIL: the literal PROVE_XYZ is visible
kubectl delete secret enc-probe -n default
```

`[LIVE]` Managed equivalents (no node access needed): EKS `aws eks describe-cluster --query
cluster.encryptionConfig` (non-empty with a `keyArn` = pass); AKS `az aks show --query
securityProfile.azureKeyVaultKms.enabled` (`true` = pass).

### Rotation — prove it happens and the old credential dies

`[LIVE]` The store's rotation metadata is the presence check:

```bash
# AWS Secrets Manager — RotationEnabled + a recent LastRotatedDate.
aws secretsmanager describe-secret --secret-id NAME \
  --query '{rot:RotationEnabled, last:LastRotatedDate, next:NextRotationDate, days:RotationRules.AutomaticallyAfterDays}'
```

> **Azure correction:** `az keyvault secret rotation-policy` does **not** exist — rotation policies are a
> `keys`-only feature. A Key Vault *secret*'s "policy" is validated as **expiry set + an Event Grid
> subscription on `Microsoft.KeyVault.SecretNearExpiry`** wired to a Function/Logic App, not a policy object.

`[LIVE]` The *effectiveness* check most people skip — the app picks up the rotated value **without a restart**,
and the **old credential stops authenticating**:

```bash
# A secret consumed as an env var can NEVER hot-rotate — kubelet resolves it once at container start.
# Assert that first; for an env consumer the correct finding is "requires restart by construction."
kubectl get pod -n NS POD -o json | jq -e '
  [ .spec.containers[] | (.env // [])[] | select(.valueFrom.secretKeyRef != null) ] | length == 0
' || echo 'FINDING: secret consumed as env var — hot rotation is structurally impossible'

# For a volume/CSI-mounted secret: rotate at the provider, wait > refreshInterval, then assert BOTH
# the value changed AND the pod did not restart AND the old credential is now rejected.
```

## Family 2 — Encryption in transit

The control is not "TLS is configured" but "plaintext does not serve and modern TLS is enforced." This lane
validates it is **wired and enforced**; `qa-security-certificate-scan` (sslyze/testssl) owns the cert/cipher
*quality* depth — call it for the grade, validate enforcement here.

`[LIVE]` The plaintext path must redirect, not serve:

```bash
# TLS-02 — HTTP must 301/308 to HTTPS, never return 200 with content.
code=$(curl -s -o /dev/null -w '%{http_code}' -L --max-redirs 0 http://app.myorg.com/)
case "$code" in 30[1287]) echo "PASS redirect";; *) echo "FAIL: http served $code";; esac

# TLS-03 — HSTS present on the HTTPS response.
curl -sI https://app.myorg.com/ | grep -qi '^strict-transport-security:' && echo PASS || echo FAIL
```

`[LIVE]` Internal hops — the "internal network is trusted" gap. Assert service-to-service is TLS/mTLS, not
plaintext between pods:

```bash
# Ingress TLS block present.
kubectl get ingress -A -o json | jq -r '.items[] | select((.spec.tls // []) == []) | "FAIL no-TLS ingress: \(.metadata.namespace)/\(.metadata.name)"'
# Mesh mTLS in STRICT mode (Istio example).
kubectl get peerauthentication -A -o json | jq -r '.items[] | "\(.metadata.namespace)/\(.metadata.name)\tmode=\(.spec.mtls.mode)"'
```

`[LIVE]` Cloud minimum-TLS policy at the load balancer / storage front door:

```bash
# ALB/ELB listener policy, storage account minimum TLS, etc. — assert TLS1.2+ minimum.
az storage account show -n ACCT -g RG --query minimumTlsVersion   # expect TLS1_2
aws elbv2 describe-listeners --load-balancer-arn ARN --query 'Listeners[].SslPolicy'
```

`[LIVE]` At-rest quick checks (the presence half — depth belongs to `cloud-posture`): S3 default encryption,
EBS/managed-disk encryption, RDS/SQL TDE, and the K8s etcd check above.

## Cross-references

- `../SKILL.md` — the harness and the control-family matrix; this reference is Families 1 and 2 in depth.
- `monitoring-and-pipeline.md` — Families 3 and 4.
- `qa-security-secrets-scan` — the *committed-secret* presence scan (gitleaks/TruffleHog); this lane validates
  the runtime *plumbing* is a store reference, not a literal.
- `qa-security-certificate-scan` — sslyze/testssl for TLS cert/cipher **quality**; this lane validates TLS is
  **wired and enforced**.
- `devops-environment-config` — the authoring sibling; a finding routes there for `devops-engineer` to fix,
  then this lane retests.
- `devops-cloud-posture` — broad CSPM benchmark scanning of encryption/IAM; this lane is targeted
  effectiveness validation + retest of specific controls.
