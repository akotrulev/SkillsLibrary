# Apache Caldera — the campaign (a chain of techniques)

Feeds the multi-host row of `../SKILL.md`'s decision matrix. **Apache Caldera** (v5.3.0; **note the
governance move — the repo is now `apache/caldera`, relocated from `mitre/caldera`;** older tutorials
pointing at `mitre/caldera` and pre-5.x plugin layouts are stale) is an autonomous adversary-emulation
platform: a server, lightweight agents (`sandcat`/`manx`) on the in-scope hosts, and **abilities** each
mapped to an ATT&CK technique that chain into an **adversary profile** and run as an **operation**.

- **Abilities ↔ ATT&CK.** Each ability carries its technique id; a profile is an ordered chain (initial
  access → discovery → collection → …) — the multi-technique scenario a single atomic can't express.
- **Planners** (`atomic`, `batch`) decide the order abilities run; **fact sources** feed values (a
  discovered credential) from one ability into the next.
- **The `atomic` plugin imports the Atomic Red Team tests** as abilities, so a Caldera profile can chain
  ART atomics (`atomic-red-team.md`); the **`emu` plugin** ships the Center for Threat-Informed Defense
  (CTID) **adversary-emulation plans** (e.g. an APT profile) as ready ATT&CK-mapped chains.
- **`debrief`** produces the operation report (techniques run, per-step results) — the red-side evidence
  the blue half validates against.
- **Cleanup is first-class:** an operation runs its abilities' cleanup commands in reverse on completion;
  still verify, and remove the agents when the engagement ends.

> **Scope discipline is louder for Caldera than for a single atomic** — an autonomous operation walks a
> chain and can reach further than you expect. Bound it to the in-scope hosts (the agents you deployed),
> cap the operation, and re-read the scope file before starting it. A planner that would pivot to an
> out-of-scope host is a mid-run abort, not a continue.
