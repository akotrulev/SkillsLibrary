# Atomic Red Team — the scalpel (one technique, run-and-clean)

Feeds the host/endpoint row of `../SKILL.md`'s decision matrix. **Atomic Red Team** (Red Canary) is a
library of small, portable tests each mapped to an ATT&CK technique, executed by the
**`invoke-atomicredteam`** PowerShell module. Pin honestly: the **module**
(`redcanaryco/invoke-atomicredteam`) is mature and rarely re-tagged — last tag **v2.3.0** — while the
**`atomics/` technique library** (`redcanaryco/atomic-red-team`) updates continuously and is synced
separately. **For a reproducible run, pin the module version AND the atomics-folder commit** — "we ran
the T1003.001 atomic" is not reproducible unless you record which atomics commit it came from.

```powershell
# Install the module + atomics folder (bootstrap). Do this on the AUTHORIZED lab host, not a workstation.
IEX (IWR 'https://raw.githubusercontent.com/redcanaryco/invoke-atomicredteam/master/install-atomicredteam.ps1' -UseBasicParsing)
Install-AtomicRedTeam -getAtomics                       # pulls the atomics/ library beside the module
Import-Module invoke-atomicredteam -Force

# The disciplined per-technique sequence — check, prereqs, run one test, then always clean up.
Invoke-AtomicTest T1003.001 -ShowDetailsBrief           # what it will do — read before running
Invoke-AtomicTest T1003.001 -CheckPrereqs               # does the host meet the test's prerequisites?
Invoke-AtomicTest T1003.001 -GetPrereqs                 # stage prerequisites (opt-in — it changes the host)
Invoke-AtomicTest T1003.001 -TestNumbers 1              # run exactly one test, not the whole technique blindly
Invoke-AtomicTest T1003.001 -TestNumbers 1 -Cleanup     # clean up — revert what the test planted
```

- **`-TestNumbers`/`-TestGuids` scope the run.** Never `Invoke-AtomicTest T1003.001` with no test selector
  against a live env — that runs *every* atomic under the technique, some of which are more intrusive than
  you intend.
- **`-Cleanup` is not optional.** Many atomics create files, registry keys, users, or services. The
  cleanup command is part of the technique definition; run it and then *verify* the artifact is gone (the
  safety model's cleanup-verification rule — a planted artifact you did not confirm removed is a finding
  against your own run).
- **`-GetPrereqs` changes the host** (downloads tools, creates fixtures). It is an opt-in act under the
  scope file's allowed-techniques list, not a silent default.
- **Run over PowerShell Core** to drive Linux/macOS targets, or the built-in `-Session` to run against a
  remote authorized host; the remote host must be in scope.
