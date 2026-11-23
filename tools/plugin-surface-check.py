#!/usr/bin/env python3
"""Plugin-surface check for the SkillsLibrary marketplace.

Over .claude-plugin/marketplace.json, verifies:
  1. every `skills` entry is a folder holding SKILL.md; every `agents` and `commands` entry is a file
  2. skill `name:` values and command file stems are unique within each plugin
  3. no skill name or command stem is a Claude Code built-in (RESERVED, dated 2026-10-11)
  4. no skill name carries a domain/stack prefix or suffix the plugin namespace already says
  5. no skill folder or agent file is registered by plugins of two different categories
  6. every `dependencies` entry names a plugin in this marketplace, and the graph has no cycle
  7. only a front door is listed to the model: a skill named `rules` or one in FRONT_DOORS has no
     `disable-model-invocation`, and every other registered skill sets it to true
  8. no skill `description:` is a plain scalar holding ': ', which is invalid YAML
  9. every command sets `disable-model-invocation: true`: a command is typed, never listed to the model
 10. a skill in HIDDEN sets both `user-invocable: false` and `disable-model-invocation: true`, and a
     front door never sets `user-invocable: false`. Per code.claude.com/docs/en/skills (read
     2026-11-23), `user-invocable: false` hides a skill from the `/` menu; plan 018 D13

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
STACK_CATEGORIES = ("qa", "fe", "be", "mobile", "desktop")

FRONT_DOORS = {
    "engineering": frozenset("""
        debugging verify quality-constraints source-grounding writing-for-agents audit-spec audit-feature audit-architecture untested-code
    """.split()),
    "product": frozenset("plan-feature notebooklm".split()),
    "design": frozenset(("prototype",)),
    "qa":frozenset(("inhouse-framework-conventions", "python-web-testing")),
}

HIDDEN = {
    "product": frozenset("""
        writing-plans plan-session-budget plan-blueprint scoping epics plan-epic-map plan-data-model
        plan-api-surface plan-experience plan-integrations stories story-review
    """.split()),
}


def category(plugin_name):
    prefix = plugin_name.split("-", 1)[0]
    return prefix if prefix in STACK_CATEGORIES else plugin_name


def is_front_door(plugin_name, label):
    return label == "rules" or label in FRONT_DOORS.get(category(plugin_name), ())


def frontmatter(path):
    with open(path, encoding="utf-8") as f:
        m = re.match(r"^---\r?\n(.*?)\r?\n---", f.read(), re.S)
    return m.group(1) if m else ""


def skill_name(block):
    nm = re.search(r"^name:\s*(\S+)\s*$", block, re.M)
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
            block = frontmatter(skill_md)
            label = skill_name(block)
            if not label:
                failures.append(f"{pname}: {rel}/SKILL.md has no name:")
                continue
            claim(label, rel)
            check_name(label, rel)
            if label.startswith(pname + "-") or label.startswith(BANNED_PREFIXES):
                failures.append(f"{pname}: skill name '{label}' carries a prefix the plugin namespace already says ({rel})")
            if label.endswith(BANNED_SUFFIXES):
                failures.append(f"{pname}: skill name '{label}' ends in a stack or -shared token ({rel})")
            hidden = re.search(r"^disable-model-invocation:\s*true\s*$", block, re.M) is not None
            if is_front_door(pname, label) and hidden:
                failures.append(f"{pname}: front-door skill '{label}' sets disable-model-invocation ({rel})")
            if not is_front_door(pname, label) and not hidden:
                failures.append(f"{pname}: skill '{label}' is listed to the model but is not a front door; "
                                f"set disable-model-invocation: true or add it to FRONT_DOORS ({rel})")
            user_hidden = re.search(r"^user-invocable:\s*false\s*$", block, re.M) is not None
            if label in HIDDEN.get(pname, ()) and not (hidden and user_hidden):
                failures.append(f"{pname}: hidden skill '{label}' must set user-invocable: false and "
                                f"disable-model-invocation: true ({rel})")
            if is_front_door(pname, label) and user_hidden:
                failures.append(f"{pname}: front-door skill '{label}' sets user-invocable: false ({rel})")
            if re.search(r"^description:[ \t]*[^\s\"'>|][^\n]*: ", block, re.M):
                failures.append(f"{pname}: description of '{label}' holds an unquoted ': ' ({rel})")

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
            if not re.search(r"^disable-model-invocation:\s*true\s*$", frontmatter(os.path.join(ROOT, rel)), re.M):
                failures.append(f"{pname}: command does not set disable-model-invocation: true ({rel})")
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
