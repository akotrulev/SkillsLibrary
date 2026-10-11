# Deep-dive details — `qa-typescript:passive-scan`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Examples

**End-to-end: a passive DAST PR gate that fails on regressed security headers, triages known noise, and
attaches the report.**

```tsv
# .zap/rules.tsv — the ticketed triage gate
10038	FAIL	(CSP header missing — must ship; gate any regression)
10063	FAIL	(Permissions-Policy header missing)
10015	IGNORE	(No Cache-control on public marketing pages — JIRA-3101, accepted)
10096	IGNORE	(Timestamp disclosure false-positive on asset hashes — JIRA-3102)
```

```yaml
# .github/workflows/passive-scan.yml
name: ZAP Baseline DAST
on: [pull_request]
jobs:
  zap_baseline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - run: docker compose up -d --wait        # ready on healthchecks, not a sleep
      - uses: zaproxy/action-baseline@v0.15.0
        with:
          target: 'http://localhost:3000'
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a -j -m 2'             # alpha rules, Ajax spider, 2-min spider for the SPA
          fail_action: false                    # rely on rules→FAIL (exit 1) for the gate
          artifact_name: zap_baseline_report
          token: ${{ secrets.GITHUB_TOKEN }}
```

Lifecycle for this gate:
1. A dev ships a change that drops the `Content-Security-Policy` header on the app shell.
2. The PR runs the baseline scan against the compose-spun app (ready on healthchecks).
3. Rule `10038` is promoted to `FAIL` in `rules.tsv` → ZAP exits **1** → **the job fails**, with the
   alert (rule id, risk, affected URLs) in the uploaded report artifact and the tracking issue.
4. The dev restores the header; the scan exits 0/2; the gate goes green. The two `IGNORE`d rules stay
   tracked by their JIRA tickets, shrinking over time — never grown to silence a real finding.
