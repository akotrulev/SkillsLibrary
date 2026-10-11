#!/usr/bin/env python3
"""Plugin-surface check for the SkillsLibrary marketplace.

Over .claude-plugin/marketplace.json, verifies:
  1. every `skills` entry is a folder holding SKILL.md; every `agents` and `commands` entry is a file
  2. skill `name:` values and command file stems are unique within each plugin
  3. no skill name or command stem is a Claude Code built-in (RESERVED, dated 2026-10-11)
  4. no skill name carries a domain/stack prefix or suffix the plugin namespace already says
  5. no skill folder or agent file is registered by plugins of two different categories
  6. every `dependencies` entry names a plugin in this marketplace, and the graph has no cycle

Prints OK and exits 0, or one line per failure and exits 1.

Usage: python3 tools/plugin-surface-check.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RESERVED = frozenset("""
add-dir agents artifacts bug clear claude-api code-review compact config context cost dataviz doctor
effort exit export fast feedback fewer-permission-prompts focus help hooks ide init install-github-app
keybindings-help login logout loop mcp memory migrate-installer model output-style permissions plan
plugin plugin-authoring pr-comments privacy-settings release-notes resume review rewind run schedule
security-review simplify status statusline terminal-setup todos update-config upgrade usage vim
workflow-authoring
""".split())

BANNED_PREFIXES = ("be-shared-", "mobile-shared-", "ep-", "ba-", "td-", "tool-", "secgov-",
                   "pentest-", "purpleteam-", "auth-")
BANNED_SUFFIXES = ("-java", "-dotnet", "-typescript", "-node", "-python", "-shared")
STACK_CATEGORIES = ("qa", "fe", "be", "mobile")


def category(plugin_name):
    prefix = plugin_name.split("-", 1)[0]
    return prefix if prefix in STACK_CATEGORIES else plugin_name


def skill_name(skill_md):
    with open(skill_md, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    nm = re.search(r"^name:\s*(\S+)\s*$", m.group(1), re.M) if m else None
    return nm.group(1).strip("\"'") if nm else None


def find_cycle(graph):
    state = {}

    def visit(node, path):
        state[node] = 1
        for dep in graph.get(node, []):
            if state.get(dep) == 1:
                return path + [node, dep]
            if dep not in state:
                found = visit(dep, path + [node])
                if found:
                    return found
        state[node] = 2
        return None

    for node in graph:
        if node not in state:
            found = visit(node, [])
            if found:
                return found
    return None


def main():
    with open(os.path.join(ROOT, ".claude-plugin", "marketplace.json"), encoding="utf-8") as f:
        plugins = json.load(f)["plugins"]
    failures = []
    names = {p["name"] for p in plugins}
    skill_owners, agent_owners = {}, {}

    for plugin in plugins:
        pname = plugin["name"]
        seen = {}

        def claim(label, source):
            if label in seen:
                failures.append(f"{pname}: duplicate name '{label}' ({seen[label]} and {source})")
            else:
                seen[label] = source

        def check_name(label, source):
            if label in RESERVED:
                failures.append(f"{pname}: '{label}' is a reserved name ({source})")

        for entry in plugin.get("skills", []):
            rel = entry[2:] if entry.startswith("./") else entry
            skill_md = os.path.join(ROOT, rel, "SKILL.md")
            if not os.path.isfile(skill_md):
                failures.append(f"{pname}: skill folder has no SKILL.md: {entry}")
                continue
            skill_owners.setdefault(rel, set()).add(pname)
            label = skill_name(skill_md)
            if not label:
                failures.append(f"{pname}: {rel}/SKILL.md has no name:")
                continue
            claim(label, rel)
            check_name(label, rel)
            if label.startswith(pname + "-") or label.startswith(BANNED_PREFIXES):
                failures.append(f"{pname}: skill name '{label}' carries a prefix the plugin namespace already says ({rel})")
            if label.endswith(BANNED_SUFFIXES):
                failures.append(f"{pname}: skill name '{label}' ends in a stack or -shared token ({rel})")

        for entry in plugin.get("agents", []):
            rel = entry[2:] if entry.startswith("./") else entry
            if not os.path.isfile(os.path.join(ROOT, rel)):
                failures.append(f"{pname}: agent file missing: {entry}")
                continue
            agent_owners.setdefault(rel, set()).add(pname)

        for entry in plugin.get("commands", []):
            rel = entry[2:] if entry.startswith("./") else entry
            if not os.path.isfile(os.path.join(ROOT, rel)):
                failures.append(f"{pname}: command file missing: {entry}")
                continue
            stem = os.path.splitext(os.path.basename(rel))[0]
            claim(stem, rel)
            check_name(stem, rel)

    for kind, owners in (("skill", skill_owners), ("agent", agent_owners)):
        for rel, plugin_names in sorted(owners.items()):
            cats = {category(n) for n in plugin_names}
            if len(cats) > 1:
                failures.append(f"{kind} {rel} is registered in categories {sorted(cats)} ({sorted(plugin_names)})")

    graph = {}
    for plugin in plugins:
        graph[plugin["name"]] = plugin.get("dependencies", [])
        for dep in graph[plugin["name"]]:
            if dep not in names:
                failures.append(f"{plugin['name']}: dependency '{dep}' is not a plugin in this marketplace")
    cycle = find_cycle(graph)
    if cycle:
        failures.append("dependency cycle: " + " -> ".join(cycle))

    if failures:
        print("\n".join(failures))
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
