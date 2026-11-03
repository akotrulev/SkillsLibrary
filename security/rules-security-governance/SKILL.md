---
name: rules
description: Use when installing or updating the security artifact standards as path-scoped rules in .claude/rules/security-governance/. Triggers "install the security rules". Not for auditing (standards-audit).
disable-model-invocation: true
---

# Install the security-governance rules

Plugins cannot ship Claude Code rules, so this skill copies them into the project. Each rule file carries `paths:` frontmatter, and Claude Code loads it only once the session reads or edits a matching file, so a session that never touches a WAF config never pays for the WAF rules.

| File (beside this SKILL.md) | Loads when the session touches |
|---|---|
| `security-governance.md`: standards pins, redaction, claims and evidence, comments | `docs/security/`, `detections/`, `sigma/`, `waf/`, `crs/` |
| `detections.md`: Sigma rule anatomy, tests, the detection-as-code pipeline | `detections/`, `sigma/` |
| `hardening.md`: CSP, the secure-headers baseline, CRS / WAF rollout | `docs/security/hardening/`, `waf/`, `crs/`, `crs-setup.conf`, `*modsecurity*.conf`, `coraza*.conf` |
| `runbooks.md`: credential rotation and cloud incident-response runbooks | `docs/security/runbooks/` |
| `compliance.md`: the evidence register and gap list | `docs/security/compliance/` |
| `posture.md`: posture reports, rounds, the risk register | `docs/security/posture/` |

The core file also loads on the pentest and purple-team reports and engagement scope files other plugins write under `docs/security/`: its redaction rules are the one standard that crosses that boundary.

The source folder is `${CLAUDE_SKILL_DIR}`. The target is `<root>/.claude/rules/security-governance/`.

## Procedure

1. **Find the project root**: `git rev-parse --show-toplevel`, or the working directory when it is not a git repo.
2. **Check the source**: all six files exist in `${CLAUDE_SKILL_DIR}`. If one is missing, stop and say so; never write a rule from memory.
3. **Copy each file** that is missing from the target: `mkdir -p <root>/.claude/rules/security-governance` and `cp` it byte for byte.
4. **For each file already present**, `cmp` it with the source.
   - Identical: up to date.
   - Different: the team may have edited it. Show `diff -u <target> <source>` and ask: **replace** with the plugin's copy, **keep** theirs, or **write the plugin's copy beside it** as `<name>.plugin` to merge by hand. Never overwrite without that answer.
5. **Fit the paths to where this project keeps its artifacts.** The defaults follow the layout `security-architect` writes. Find the real ones:
   - Sigma rules: `git grep -l -e '^logsource:' -- '*.yml' '*.yaml'` (a `rules/` folder at the root is common and is deliberately not a default, because the name is generic).
   - WAF config: `git grep -l -e 'SecRuleEngine' -e 'SecRule ' -e 'coreruleset' -- '*.conf' '*.yml' '*.yaml'`.
   - Runbooks, registers and posture reports kept outside `docs/security/`: `git ls-files | grep -i -e runbook -e evidence -e posture`.

   For every folder found that no default glob covers, propose a directory glob (for example `"security/detections/**"`) for the matching file and for the core file, and add it to the installed copies with the user's agreement. Never widen to `**/*.yml` or `**/*.conf`: unrelated config would then load these rules. If a default folder holds something else here (a `waf/` that is a package name), offer to drop that glob.
6. **Check it will be committed**: `git check-ignore -q <root>/.claude/rules/security-governance/security-governance.md`. If it is ignored, say so; the rules then apply on this machine only.
7. **Check for conflicts**: read the project's `CLAUDE.md` (root and `.claude/`) for security rules that contradict these files and list them. A written contradiction is the user's to settle.

## Report

```
security-governance rules: <file>: installed | up to date | replaced | kept | written as .plugin   (one line per file)
Path: <root>/.claude/rules/security-governance/
Artifact paths: default | widened with <globs> | dropped <globs>
Committed: yes | ignored by git
Conflicts with CLAUDE.md: none | <one line each>
```

Then tell the user to commit the folder, and that a rule shows in `/memory` once the session has read a matching file.
