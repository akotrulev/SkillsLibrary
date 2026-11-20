# Exceptions — one id, one ticket, one re-review date

Same model as the Trivy `.trivyignore` and the SCA suppression file; the full discipline is in `qa/_shared/security`. The rules are in `../SKILL.md` Exceptions & triage.

```yaml
checks:
  hostIPCSet: danger
  automountServiceAccountToken: danger   # PLAT-903: ratcheted up from warning once the backlog cleared
  pullPolicyNotAlways: ignore            # PLAT-812: images are SHA-pinned, so Always is a wasted pull
exemptions:
  - namespace: observability
    controllerNames: ["log-collector"]
    rules: ["hostPathSet", "notReadOnlyRootFilesystem"]
    # PLAT-661: the node log agent legitimately needs /var/log; accepted risk, re-review 2026-11-01.
```

Pass it to Polaris with `-c` or `--config`. It grades a check or exempts one named controller.

```bash
kube-bench run --benchmark cis-1.12 --skip 4.2.6 --exit-code 1
kube-score score manifests/*.yaml --ignore-test container-image-pull-policy --exit-one-on-warning
```

The kube-bench skip names one control id; the kube-score ignore names one test. The ticket and reason for each go in the pipeline file beside the flag.
