#!/usr/bin/env python3
"""Token-cost audit for the SkillsLibrary plugins.

Reports, per plugin in .claude-plugin/marketplace.json:
  - always-on cost: sum of skill `description` frontmatter + agent `description`
    frontmatter (both are injected into every session)
  - per-invocation cost: SKILL.md body sizes
  - agent-run cost: full agent prompt (whole file) sizes

Flags budget violations (see TOKEN-OPTIMIZATION-PLAN.md):
  skill description > 500 chars · SKILL.md body > 16,000 chars
  agent description > 650 chars · agent file > 14,000 chars

All sizes are decoded-character counts (not bytes), so the multibyte glyphs the
library leans on (· → ≤ ✅) are counted once each, consistently across skills and
agents. Token figures are a rough chars//4 estimate — good for trends and
budgeting, ~±20% against a real tokenizer.

Exits non-zero if any budget is violated, so it doubles as a CI / pre-commit gate.

Usage: python3 tools/token-audit.py [--violations-only]
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESC_BUDGET = 500
BODY_BUDGET = 16_000
AGENT_DESC_BUDGET = 650
AGENT_BUDGET = 14_000


def parse_frontmatter(path):
    """Return (description, body) as decoded strings; ('', whole-text) if no frontmatter."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
    if not m:
        return "", text
    dm = re.search(r"^description:\s*(.*?)(?=^\w[\w-]*:|\Z)", m.group(1), re.S | re.M)
    return (dm.group(1).strip() if dm else ""), m.group(2)


def read_chars(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def tok(chars):
    return chars // 4  # rough chars->tokens


def main():
    violations_only = "--violations-only" in sys.argv
    marketplace = json.load(open(os.path.join(ROOT, ".claude-plugin", "marketplace.json")))
    desc_viol, body_viol, agent_desc_viol, agent_viol = [], [], [], []
    seen = set()

    header = f"{'plugin':<18} {'skills':>6} {'desc(tok)':>10} {'bodies(tok)':>12} {'ag-desc(tok)':>12} {'ag-body(tok)':>12}"
    if not violations_only:
        print(header)
    for plugin in marketplace["plugins"]:
        name = plugin["name"]
        skills = plugin.get("skills") or []
        agents = plugin.get("agents") or []
        n = desc_total = body_total = agent_desc_total = agent_total = 0
        for s in skills:
            rel = s.lstrip("./")
            path = os.path.join(ROOT, rel if rel.endswith(".md") else os.path.join(rel, "SKILL.md"))
            if not os.path.exists(path):
                continue
            desc, body = parse_frontmatter(path)
            n += 1
            desc_total += len(desc)
            body_total += len(body)
            relpath = os.path.relpath(path, ROOT)
            if relpath not in seen:
                seen.add(relpath)
                if "/vendor/" in relpath:
                    continue  # vendored upstream imports are not rewritten
                if len(desc) > DESC_BUDGET:
                    desc_viol.append((len(desc), relpath, name))
                if len(body) > BODY_BUDGET:
                    body_viol.append((len(body), relpath, name))
        for a in agents:
            path = os.path.join(ROOT, a.lstrip("./"))
            if not os.path.exists(path):
                continue
            desc, _ = parse_frontmatter(path)
            size = len(read_chars(path))
            agent_desc_total += len(desc)
            agent_total += size
            relpath = os.path.relpath(path, ROOT)
            if relpath not in seen:
                seen.add(relpath)
                if len(desc) > AGENT_DESC_BUDGET:
                    agent_desc_viol.append((len(desc), relpath, name))
                if size > AGENT_BUDGET:
                    agent_viol.append((size, relpath, name))
        if not violations_only:
            print(f"{name:<18} {n:>6} {tok(desc_total):>10} {tok(body_total):>12} "
                  f"{tok(agent_desc_total):>12} {tok(agent_total):>12}")

    def report(title, items, budget, unit):
        print(f"\n== {title} (> {budget} {unit}): {len(items)} ==")
        for size, path, plugin in sorted(items, reverse=True):
            print(f"{size:>7}  {path}  [{plugin}]")

    report("Skill description budget violations", desc_viol, DESC_BUDGET, "chars")
    report("SKILL.md body budget violations", body_viol, BODY_BUDGET, "chars")
    report("Agent description budget violations", agent_desc_viol, AGENT_DESC_BUDGET, "chars")
    report("Agent file budget violations", agent_viol, AGENT_BUDGET, "chars")

    all_viol = desc_viol + body_viol + agent_desc_viol + agent_viol
    if all_viol:
        by_plugin = {}
        for _, _, plugin in all_viol:
            by_plugin[plugin] = by_plugin.get(plugin, 0) + 1
        print(f"\n== Violations by plugin ({len(all_viol)} total) ==")
        for plugin, count in sorted(by_plugin.items(), key=lambda kv: -kv[1]):
            print(f"{count:>7}  {plugin}")
        sys.exit(1)


if __name__ == "__main__":
    main()
