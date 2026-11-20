# Stratus Red Team (cloud/K8s) & VECTR (the scoreboard)

Feeds the cloud/K8s row and the tracking row of `../SKILL.md`'s decision matrix.

## Stratus Red Team — cloud & Kubernetes atomics

**Stratus Red Team** (Datadog, v2.32.1) is the cloud equivalent of a single atomic — a **self-contained Go
binary** that detonates a granular cloud/K8s attack technique against AWS, Azure, GCP, or Kubernetes,
mapped to the **ATT&CK Cloud/Containers** matrices.

```bash
stratus list                                            # techniques available, with ATT&CK ids
stratus warmup   aws.credential-access.ec2-get-password-data   # prepare prerequisite infra (opt-in)
stratus detonate aws.credential-access.ec2-get-password-data   # run the technique — the CloudTrail event to detect
stratus cleanup  aws.credential-access.ec2-get-password-data   # clean up — tear the technique's resources down
stratus status                                          # what is warm / detonated / to be cleaned
```

- **warmup → detonate → cleanup** is the lifecycle; `cleanup` is mandatory and Stratus tracks state so a
  forgotten `detonate` is visible in `status`.
- The point is the **telemetry it generates** — a detonated technique produces the exact CloudTrail /
  Azure Activity Log / GCP Audit Log event your cloud detection should catch; the blue half then queries
  the log store for it.
- Use Stratus for the cloud/K8s row of the coverage matrix; use Atomic Red Team/Caldera for the
  host/endpoint rows. It runs against **the in-scope cloud account only** — a detonation creates and
  deletes real cloud resources, so a wrong account is both a scope breach and a cost.

## VECTR — the scoreboard (track, benchmark, spot drift)

**VECTR** (Security Risk Advisors; Community Edition **ce-9.14.1**, self-hosted; Enterprise Edition is the
commercial benchmarking/executive-reporting variant) is where purple-team outcomes are *tracked over
time*, not executed. Each test case records the technique (ATT&CK id), the tool that ran it, and the
outcome — **blocked / alerted / logged / no signal** — building the coverage matrix across the ATT&CK map
and, run round over round, the **drift** view. SRA's **Threat Simulation Index 2026** is a ready benchmark
catalogue of techniques worth simulating. VECTR is optional — the purple-team report's detected/not-detected
matrix carries the same data — but it is the natural home when the cadence is continuous and the audience
wants a benchmarked trend.
