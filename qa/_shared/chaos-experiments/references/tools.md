# Chaos tools — manifests, templates and the abort guard

Every example below targets one service (`payments` in namespace `shop`), affects one replica or a small share,
is time-boxed, and has an abort. Replace names, never the controls. Pin the tool's version where the project
installs it (Helm chart version, Litmus release); this file pins none.

## 1. Chaos Mesh — PodChaos and NetworkChaos

Docs: chaos-mesh.org (2.8 line). Kinds are `chaos-mesh.org/v1alpha1`.

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: payments-one-pod-failure
  namespace: shop
spec:
  action: pod-failure
  mode: one
  duration: '300s'
  selector:
    namespaces: [shop]
    labelSelectors:
      app.kubernetes.io/name: payments
```

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: payments-latency-to-db
  namespace: shop
spec:
  action: delay
  mode: fixed-percent
  value: '30'
  duration: '300s'
  selector:
    namespaces: [shop]
    labelSelectors:
      app.kubernetes.io/name: payments
  delay:
    latency: '200ms'
    jitter: '20ms'
  direction: to
  target:
    mode: all
    selector:
      namespaces: [shop]
      labelSelectors:
        app.kubernetes.io/name: payments-db
```

- `mode` picks targets among the pods the selector matches: `one` (a random pod), `all`, `fixed` (`value` = a
  count), `fixed-percent` (`value` = a percentage), `random-max-percent` (`value` = the upper bound of a random
  percentage).
- `action: pod-failure` makes the pod unavailable for `duration` and restores it; `pod-kill` deletes it and lets
  the controller recreate it.
- **Pause** a running experiment: `kubectl annotate podchaos payments-one-pod-failure -n shop experiment.chaos-mesh.org/pause=true`
  (pausing starts recovery). **Stop** it: `kubectl delete podchaos payments-one-pod-failure -n shop` — the fault is
  restored on deletion.
- **Namespace opt-in**: install with `--set controllerManager.enableFilterNamespace=true`, then
  `kubectl annotate ns shop chaos-mesh.org/inject=enabled`. Chaos Mesh then injects only into annotated namespaces.

### In-tool abort — a Workflow with a StatusCheck

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: Workflow
metadata:
  name: payments-pod-failure-guarded
  namespace: shop
spec:
  entry: entry
  templates:
    - name: entry
      templateType: Parallel
      deadline: 330s
      children: [checkout-health, payments-one-pod-failure]
    - name: checkout-health
      templateType: StatusCheck
      deadline: 330s
      abortWithStatusCheck: true
      statusCheck:
        mode: Continuous
        type: HTTP
        intervalSeconds: 5
        timeoutSeconds: 2
        failureThreshold: 3
        successThreshold: 1
        http:
          url: http://checkout.shop.svc:8080/health/ready
          method: GET
          criteria:
            statusCode: '200'
    - name: payments-one-pod-failure
      templateType: PodChaos
      deadline: 300s
      podChaos:
        action: pod-failure
        mode: one
        selector:
          namespaces: [shop]
          labelSelectors:
            app.kubernetes.io/name: payments
```

The StatusCheck criteria compare a **status code**, not a response body, so it cannot read a Prometheus value. It
guards against "the dependent service is down"; the SLO thresholds need the guard in §5 running beside it.

## 2. LitmusChaos — pod-delete with a Prometheus probe

Docs: litmuschaos.github.io (Litmus 3.x). The probe aborts the run when the PromQL leaves the allowed range.

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: payments-pod-delete
  namespace: shop
spec:
  engineState: active
  appinfo:
    appns: shop
    applabel: app.kubernetes.io/name=payments
    appkind: deployment
  chaosServiceAccount: pod-delete-sa
  experiments:
    - name: pod-delete
      spec:
        components:
          env:
            - name: TOTAL_CHAOS_DURATION
              value: '300'
            - name: CHAOS_INTERVAL
              value: '60'
            - name: PODS_AFFECTED_PERC
              value: '30'
        probe:
          - name: checkout-error-ratio-below-abort
            type: promProbe
            mode: Continuous
            promProbe/inputs:
              endpoint: http://prometheus.monitoring.svc:9090
              query: >-
                sum(rate(http_server_request_duration_seconds_count{service="checkout",http_response_status_code=~"5.."}[1m]))
                / sum(rate(http_server_request_duration_seconds_count{service="checkout"}[1m]))
              comparator:
                criteria: '<'
                value: '0.02'
            runProperties:
              probeTimeout: 5
              interval: 5
              retry: 1
              probePollingInterval: 5
              stopOnFailure: true
```

- Probe `mode`: `SOT` (start of test), `EOT` (end), `Edge` (both), `Continuous` (throughout), `OnChaos` (only
  while the fault is active). The abort is `Continuous` + `stopOnFailure: true`; the steady-state check is a second
  probe in `Edge` mode with the SLO threshold.
- Comparator `criteria`: `>=`, `<=`, `==`, `>`, `<`, `!=`, `oneOf`, `between`.
- `probeTimeout` and `interval` are integers; read the units for your Litmus release before copying the numbers.
- Stop a running engine by patching `spec.engineState` to `stop`.

## 3. AWS FIS — EKS pod latency with a CloudWatch stop condition

Docs: docs.aws.amazon.com/fis. Targets of type `aws:eks:pod` are found by `parameters`, never by ARN or tag;
the minimum EKS version is 1.30 and a Kubernetes service account for FIS is required (the FIS guide's `rbac.yaml`).

```json
{
  "description": "200 ms latency on 1 payments pod for 5 minutes",
  "targets": {
    "paymentsPod": {
      "resourceType": "aws:eks:pod",
      "parameters": {
        "clusterIdentifier": "staging-eks",
        "namespace": "shop",
        "selectorType": "labelSelector",
        "selectorValue": "app.kubernetes.io/name=payments"
      },
      "selectionMode": "COUNT(1)"
    }
  },
  "actions": {
    "paymentsLatency": {
      "actionId": "aws:eks:pod-network-latency",
      "parameters": {
        "kubernetesServiceAccount": "fis-experiments",
        "duration": "PT5M",
        "delayMilliseconds": "200",
        "jitterMilliseconds": "20",
        "sources": "0.0.0.0/0"
      },
      "targets": { "Pods": "paymentsPod" }
    }
  },
  "stopConditions": [
    { "source": "aws:cloudwatch:alarm", "value": "arn:aws:cloudwatch:eu-west-1:111122223333:alarm:checkout-5xx-abort" }
  ],
  "roleArn": "arn:aws:iam::111122223333:role/fis-experiment-role",
  "tags": { "Name": "payments-latency" }
}
```

- `selectionMode`: `ALL`, `COUNT(n)`, `PERCENT(n)` (rounded down; a percentage below one resource selects none and
  the experiment fails).
- A stop condition is a CloudWatch alarm; when it fires FIS stops the experiment and it cannot be resumed. When
  the SLO lives in Prometheus, alarm on the closest CloudWatch signal (the load balancer's 5xx count, the target
  group's response time) **and** run the guard in §5 with `aws fis stop-experiment --id <experiment-id>`.
- `"stopConditions": [{ "source": "none" }]` is a template with no abort: a review blocker.
- The network actions need root in the ephemeral container and do not run on Fargate.

## 4. Azure Chaos Studio — AKS through Chaos Mesh

Docs: learn.microsoft.com/azure/chaos-studio. AKS faults run Chaos Mesh inside the cluster, so Chaos Mesh must be
installed there and the cluster onboarded as a target with the capability enabled.

```json
{
  "name": "branchOne",
  "actions": [
    {
      "type": "continuous",
      "name": "urn:csci:microsoft:azureKubernetesServiceChaosMesh:podChaos/2.2",
      "duration": "PT5M",
      "parameters": [
        {
          "key": "jsonSpec",
          "value": "{\"action\":\"pod-failure\",\"mode\":\"one\",\"selector\":{\"namespaces\":[\"shop\"],\"labelSelectors\":{\"app.kubernetes.io/name\":\"payments\"}}}"
        }
      ],
      "selectorId": "aksStaging"
    }
  ]
}
```

- Other AKS faults use the same shape: `networkChaos/2.2`, `stressChaos/2.2`, `IOChaos/2.2`, `timeChaos/2.2`,
  `httpChaos/2.2`, `dnsChaos/2.2`. VM faults are agent-based (`urn:csci:microsoft:agent:cpuPressure/1.0`); managed
  resources have service-direct faults (`urn:csci:microsoft:cosmosDB:failover/1.0`).
- Chaos Studio **Workspaces** is in public preview and replacing classic experiments; check whether the fault you
  need is available there before starting new work on the classic model.
- Cancel a running experiment: `az rest --method post --url "https://management.azure.com/<experiment-resource-id>/cancel?api-version=<version>"`,
  with the api-version the Chaos Studio REST reference lists. That call is what the guard uses.

## 5. The abort guard — one script for every tool

Where the tool cannot read Prometheus itself, a guard polls the abort queries and stops the experiment through the
tool's own stop command. It runs from the operator's machine or a CI job for exactly the experiment's time box.

```bash
#!/usr/bin/env bash
set -euo pipefail

: "${PROMETHEUS_URL:?}" "${ABORT_QUERY:?}" "${ABORT_ABOVE:?}" "${STOP_COMMAND:?}" "${TIME_BOX_SECONDS:?}"
readonly POLL_SECONDS=10

deadline=$(( $(date +%s) + TIME_BOX_SECONDS ))
while (( $(date +%s) < deadline )); do
  value=$(curl -fsS --get "${PROMETHEUS_URL}/api/v1/query" --data-urlencode "query=${ABORT_QUERY}" \
    | jq -r '.data.result[0].value[1] // "NaN"')
  echo "$(date -u +%FT%TZ) abort-sli=${value} limit=${ABORT_ABOVE}"
  if [[ "${value}" == "NaN" ]] || awk -v v="${value}" -v l="${ABORT_ABOVE}" 'BEGIN { exit !(v > l) }'; then
    echo "ABORT: abort SLI ${value} is past ${ABORT_ABOVE} or unreadable; running: ${STOP_COMMAND}"
    eval "${STOP_COMMAND}"
    exit 2
  fi
  sleep "${POLL_SECONDS}"
done
echo "Time box ended with the abort SLI inside its limit."
```

- `STOP_COMMAND` is the tool's stop: `kubectl delete podchaos payments-one-pod-failure -n shop`,
  `aws fis stop-experiment --id "$EXPERIMENT_ID"`, or the Chaos Studio `az rest ... /cancel` call.
- **An unreadable SLI aborts.** If Prometheus cannot answer, nobody can see the users, so the experiment stops.
- The guard's log is evidence: attach it to the experiment record.
- The fixed poll interval is the guard's sampling rate, the same as a probe's `interval` — not a wait for an
  outcome. Keep it at or below the abort window (`[1m]`) divided by three.
