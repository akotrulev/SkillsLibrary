#!/usr/bin/env python3
"""Token-cost audit for the SkillsLibrary plugins.

Reports, per plugin in .claude-plugin/marketplace.json:
  - always-on cost: sum of skill `description` frontmatter (injected into every session)
  - per-invocation cost: SKILL.md body sizes
  - agent prompt sizes

Flags budget violations (see TOKEN-OPTIMIZATION-PLAN.md):
  description > 500 chars · SKILL.md body > 16,000 chars · agent file > 14,000 chars

Usage: python3 tools/token-audit.py [--violations-only]
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESC_BUDGET = 500
BODY_BUDGET = 16_000
AGENT_BUDGET = 14_000


def parse_skill(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return "", text
    dm = re.search(r"^description:\s*(.*?)(?=^\w[\w-]*:|\Z)", m.group(1), re.S | re.M)
    return (dm.group(1).strip() if dm else ""), m.group(2)


def tok(chars):
    return chars // 4  # rough chars->tokens


def main():
    violations_only = "--violations-only" in sys.argv
    marketplace = json.load(open(os.path.join(ROOT, ".claude-plugin", "marketplace.json")))
    desc_viol, body_viol, agent_viol = [], [], []
    seen = set()

    print(f"{'plugin':<18} {'skills':>6} {'desc(tok)':>10} {'bodies(tok)':>12} {'agents(tok)':>12}")
    for plugin in marketplace["plugins"]:
        skills = plugin.get("skills") or []
        agents = plugin.get("agents") or []
        n = desc_total = body_total = agent_total = 0
        for s in skills:
            rel = s.lstrip("./")
            path = os.path.join(ROOT, rel if rel.endswith(".md") else os.path.join(rel, "SKILL.md"))
            if not os.path.exists(path):
                continue
            desc, body = parse_skill(path)
            n += 1
            desc_total += len(desc)
            body_total += len(body)
            relpath = os.path.relpath(path, ROOT)
            if relpath not in seen:
                seen.add(relpath)
                if "/vendor/" in relpath:
                    continue  # vendored upstream imports are not rewritten
                if len(desc) > DESC_BUDGET:
                    desc_viol.append((len(desc), relpath))
                if len(body) > BODY_BUDGET:
                    body_viol.append((len(body), relpath))
        for a in agents:
            path = os.path.join(ROOT, a.lstrip("./"))
            if not os.path.exists(path):
                continue
            size = os.path.getsize(path)
            agent_total += size
            relpath = os.path.relpath(path, ROOT)
            if relpath not in seen:
                seen.add(relpath)
                if size > AGENT_BUDGET:
                    agent_viol.append((size, relpath))
        if not violations_only:
            print(f"{plugin['name']:<18} {n:>6} {tok(desc_total):>10} {tok(body_total):>12} {tok(agent_total):>12}")

    def report(title, items, budget, unit):
        print(f"\n== {title} (> {budget} {unit}): {len(items)} ==")
        for size, path in sorted(items, reverse=True):
            print(f"{size:>7}  {path}")

    report("Description budget violations", desc_viol, DESC_BUDGET, "chars")
    report("SKILL.md body budget violations", body_viol, BODY_BUDGET, "chars")
    report("Agent size budget violations", agent_viol, AGENT_BUDGET, "chars")

    if desc_viol or body_viol or agent_viol:
        sys.exit(1)


if __name__ == "__main__":
    main()
