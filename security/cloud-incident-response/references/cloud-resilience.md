# Cloud Resilience — BCDR: RTO/RPO · DR patterns · multi-region failover · restore drills · compliance crosswalk

Business continuity and disaster recovery for cloud, framed as the **RECOVER** half of incident response taken to its limit: recovery from an incident restores from clean state; recovery from a *disaster* (region outage, ransomware, provider concentration failure) is the same discipline under a declared, time-bounded objective. This file is the resilience reference `security/cloud-incident-response` routes to, and the one task **G1** points `compliance-evidence-mapping`'s BCDR crosswalk row at.

> **The BCDR → compliance crosswalk ROW is added by G1** into `security/compliance-evidence-mapping`, not here. This file holds the control-to-cloud-evidence detail that row cites.

## 1. RTO / RPO & the BIA

BCDR is bounded by two objectives **agreed with the business**, not chosen by engineering:

- **RTO — Recovery Time Objective:** max tolerable **downtime** — how long until the system is back. Drives the **DR pattern** (hot vs cold standby).
- **RPO — Recovery Point Objective:** max tolerable **data loss** — how far back the last good recovery point may be. Drives **backup/replication frequency** (nightly snapshot ≈ 24h RPO; continuous/sync replication ≈ near-zero RPO).
- **MTD/MTO** is the ceiling RTO sits under; **WRT** (work-recovery time to validate after restore) is additive: **RTO + WRT ≤ MTD**.
- A **Business Impact Analysis (BIA)** sets RTO/RPO **per service** by quantifying the cost of downtime/data loss — it is the input to tiering, and **ISO 27001:2022 A.5.30 expects one**.

## 2. DR pattern decision table (RTO/RPO ↓ vs cost ↑)

The four AWS-canonical strategies generalize to all clouds, cheapest/slowest → costliest/fastest:

| Pattern | What runs in the recovery region | RTO | RPO | Cost | Use when |
|---|---|---|---|---|---|
| **Backup & restore** | Nothing live; data backed up cross-region, infra provisioned on disaster (IaC) | Hours+ | Hours (last backup) | Lowest | Non-critical; outage tolerable for the restore duration |
| **Pilot light** | Core data replicated + minimal always-on (DB replica, AMIs); app tier off until failover | 10s of min | Minutes (replication) | Low–med | Lower RTO than backup/restore at similar RPO |
| **Warm standby** | Scaled-down but **complete, always-running** copy; scale up on failover | Minutes | Seconds–minutes | Med–high | Fast recovery without a full duplicate |
| **Multi-site active/active** (hot) | Full capacity live in ≥2 regions serving traffic | Near-zero | Near-zero | Highest | Mission-critical; drop the failed site from rotation |

**The rule to author:** pilot light and warm standby share the **same RPO**; they differ on **RTO** (how much is pre-warmed). Start from the BIA's RTO/RPO, then pick the **cheapest pattern that meets both**.

## 3. AZ vs region — availability is not disaster recovery

- **Multi-AZ** = fault tolerance **within one region**. AZs are isolated failure domains a few ms apart → **synchronous** replication, near-zero RPO; protects against datacenter/hardware/AZ failure. This is the **default HA posture**, not DR.
- **Multi-region** = disaster recovery against a **region-wide outage**, and the vehicle for data residency/latency. Regions are far apart → **asynchronous** replication (non-zero RPO) for most stores. Required for the high end of RTO/RPO and for provider-concentration risk.
- **Rule: multi-AZ is availability; multi-region is disaster recovery.** A SOC 2 Availability or ISO A.5.30 posture usually needs **both**.

## 4. Backup strategy

- **3-2-1**: ≥3 copies, ≥2 media types, ≥1 off-site (cross-region/cross-account). Cloud extends this to **3-2-1-1-0**: +1 immutable/offline copy, 0 restore errors (verified).
- **Immutability & isolation** against ransomware and malicious-insider deletion: object-lock / WORM (**S3 Object Lock compliance mode**, **Azure Blob immutability policies**, **GCP bucket retention lock**) and a **separate backup account/subscription/project** so a compromised primary identity cannot reach the backups.
- **Lifecycle & encryption**: tiered retention to colder storage; backups encrypted with keys the **restore path can actually reach** — a KMS key only in the primary region breaks cross-region restore.
- **Snapshot ≠ backup**: a snapshot in the same account/region shares the blast radius. A backup is off-account/off-region and immutable.

## 5. Multi-region failover

- **DNS-level** (Route 53 / Azure Traffic Manager / Cloud DNS + health checks): failover/latency/weighted routing to the healthy region. Simple, bounded by DNS TTL.
- **Data-tier replication**: cross-region read replicas promoted on failover, or active-active multi-writer stores (DynamoDB Global Tables, Cosmos DB multi-region writes, Spanner). **RPO is set here** — the data tier is the hard part.
- **Failover discipline**: prefer **data-plane** operations during failover (control-plane APIs may be impaired in the failing region); automate detection + promotion; and treat **failback** (return to primary once healthy) as an explicit, tested step, not an afterthought.

## 6. Restore / DR drills — the control auditors test for

- **An untested backup is not a recovery capability — it is a hope.** The drill is the control **SOC 2 A1.3** and **ISO A.5.30** actually test for; backups passing with zero restores is the classic audit exception.
- Drill tiers: **restore test** (recover data, verify integrity) → **failover test** (bring the service up in the recovery region) → **game day / full DR exercise** (declared disaster, measure actual RTO/RPO against target).
- Each drill **records measured RTO/RPO vs objective** and feeds gaps back into the plan. Cadence: at least **annually**, and after material architecture change. Dated evidence (ticket, runbook output, screenshots) is the audit artifact.
- This ties back to the IR close-out: a ransomware incident's recovery is a **verify-before-restore** game day (CSF **RC.RP-03**) into an isolated clean room.

## 7. Cloud-native DR / backup services

| Capability | AWS | Azure | GCP |
|---|---|---|---|
| Managed backup (central) | **AWS Backup** (cross-region/account, Backup Vault Lock) | **Azure Backup** (Recovery Services / Backup vault; immutable vaults) | **Backup and DR Service** (Actifio-derived; GCE/GKE/Cloud SQL) |
| Replication / failover orchestration | **Elastic Disaster Recovery (DRS)** | **Azure Site Recovery (ASR)** | Backup and DR + **persistent-disk async replication** |
| Global data stores | DynamoDB Global Tables; Aurora Global Database; S3 CRR | Cosmos DB multi-region writes; SQL auto-failover groups; GZRS | Spanner; Cloud SQL cross-region replicas; multi/dual-region buckets |
| DNS failover | Route 53 health checks | Traffic Manager / Front Door | Cloud DNS + health checks / global LB |
| Resilience validation | Resilience Hub; Fault Injection Service (FIS) | Chaos Studio | 3rd-party / DIY chaos |

## 8. Compliance crosswalk (the evidence an auditor asks for)

The rows **G1** adds to `security/compliance-evidence-mapping`, with the cloud evidence that satisfies each:

| Framework | Control | What it asks | Cloud evidence |
|---|---|---|---|
| **SOC 2 (Availability)** | **A1.2** | Backup processes and recovery infrastructure are authorized, designed, implemented, operated, maintained | AWS Backup / Azure Backup / GCP Backup-and-DR configs; cross-region replication; multi-AZ architecture; backup immutability + retention policy |
| **SOC 2 (Availability)** | **A1.3** | **Recovery plan procedures are tested** to support recovery objectives | Dated DR/restore **drill records**; measured RTO/RPO vs target; failover test output; game-day reports |
| **SOC 2 (Availability)** | A1.1 | Capacity monitored/forecast to meet availability commitments | Autoscaling, capacity alarms, utilization dashboards (supporting, not BCDR-core) |
| **ISO/IEC 27001:2022** | **A.5.29** | Maintain information security **during disruption** | Continuity plan preserving IAM/encryption/logging in the recovery region; security controls baked into the DR landing zone |
| **ISO/IEC 27001:2022** | **A.5.30** | **ICT readiness for business continuity** — plan/implement/maintain/**test** ICT recovery against a **BIA** with defined RTO/RPO | BIA with per-service RTO/RPO; DR pattern per tier; tested failover; AWS Backup / ASR / GCP DR implementation + drill evidence |
| **NIST CSF 2.0** | **RECOVER (RC)** → **RC.RP** (RC.RP-01…06) + **RC.CO** (RC.CO-03/04) | Execute the recovery plan; prioritize; **verify backup integrity before restore**; verify restored assets; declare recovery complete; communicate progress | DR runbook execution logs; backup-integrity verification step; restored-system validation; stakeholder-comms plan |
| **NIST SP 800-53 Rev 5** | **CP family** (CP-9 backup, CP-10 recovery, CP-7 alt site) | Contingency planning, backup, alternate processing site, recovery/reconstitution | The FedRAMP-side anchor for the same evidence (multi-region alt site = CP-7) |

**Mapping notes:**
- SOC 2 **A1.2 = you built the recovery capability; A1.3 = you proved it works** — keep them as **two rows**; the drill (A1.3) is the one that generates exceptions.
- ISO **A.5.29 vs A.5.30**: 5.29 is *security survives the disruption*; 5.30 is *ICT is ready to recover* (BIA + RTO/RPO + test). **Both are new in the 2022 revision** — no 2013 equivalent.
- CSF 2.0 RECOVER is **two categories, eight subcategories** — do not cite the CSF 1.1 RECOVER structure.
- Cloud-config benchmarks (CIS Foundations), ISO 27017/27018, and CSA CCM v4 extend the existing crosswalk to the cloud-control layer — they belong as **columns** in `compliance-evidence-mapping`, not as a new skill.

> **Audit caveat:** the SOC 2 / ISO / NIST / AICPA control wording above is cross-checked against secondary sources; confirm against the **primary standard text** before use in an audit deliverable. `compliance-evidence-mapping` maps evidence, it does not attest — a human auditor/QSA certifies.

## Handoffs
- **→ `security-governance:compliance-evidence-mapping`** — the BCDR crosswalk row (added by G1) points here for the control-to-cloud-evidence detail.
- **→ `engineering-practices/standards-audit`** — BCDR findings map to the CP / Availability controls; cloud benchmark gap-assessment (CIS Foundations, NIST CSF 2.0) is owned there.
- **↔ `security/cloud-incident-response`** (this skill) — the RECOVER step of the IR runbook escalates into these DR patterns when recovery is from a disaster, not just an incident.
