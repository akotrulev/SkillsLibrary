#!/usr/bin/env python3
"""Lint for the mechanical rules of the authoring standard (engineering-practices/writing-for-agents).

Judgment rules (R2, R4, R5, R15-R23) stay with token-audit, plugin-surface-check and review; this
script checks only the ones a regex can decide:

  R1   major  a SKILL.md frontmatter has `name` and `description`; `name` is kebab-case
  R3   minor  a skill description starts `Use when`, has `Triggers "a"`, never `Triggers:`, and ends
              `Not for <case> (<sibling>).`
  R6   minor  a hidden skill has no When to use, When NOT to use, Handoffs or Related heading
  R7   minor  a front door (no `disable-model-invocation: true`) has When to use and When NOT to use
  R8   major  every relative Markdown link, and every backticked path under references/, scripts/,
              templates/ or examples/, exists; a path holding <, {, * or … is a pattern and skipped
  R9   minor  a references/ file over 300 lines lists its ## headings before its first ##
  R10  major  no TODO, TBD, FIXME or XXX outside code, and no @path force-load link
  R11  minor  no Phase, Slice or Milestone in a heading or a table header row
  R12  major  no line tells a model to invoke, call or run a hidden plugin:name, or to use the Skill tool on it
  R13  major  an agent has a ## Steps table with Load and Done when columns, and a ## Report holding Mode:
  R14  minor  an agent's Load cell never says when relevant, if relevant, as needed or if needed

A skill is its SKILL.md plus every other .md beside it (rule files) and under its references/.
Fenced code is skipped by every body rule: Markdown parses no link, code span or heading inside a
fence, and it shows text rather than instructing. R10 also skips inline code spans.

Usage:
  python3 tools/skill-lint.py                  every in-scope skill and every agent in marketplace.json
  python3 tools/skill-lint.py <path> [<path>…] a SKILL.md, a folder of skills, an agent .md, a rule file
  python3 tools/skill-lint.py --json …         a JSON array of {path, line, rule, severity, message}

Output: <path>:<line>: <severity> <rule> <message>, paths relative to the repo root, sorted, then a
count on stderr. Exit 0 clean, 1 on any finding, 2 on a usage error.
"""
import argparse
import json
import os
import re
import sys
from collections import namedtuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

Finding = namedtuple("Finding", "path line severity rule message")

SEVERITY = {
    "R1": "major", "R3": "minor", "R6": "minor", "R7": "minor", "R8": "major", "R9": "minor",
    "R10": "major", "R11": "minor", "R12": "major", "R13": "major", "R14": "minor",
}
EXCLUDED_PREFIXES = ("communication/", "extras/", "meta/skill-creator/", ".skill-template/",
                     "tools/fixtures/", ".git/")
EXCLUDED_PATTERN = re.compile(r"^auth/cognito-[^/]*/|(^|/)(vendor|node_modules)/")
REFERENCE_LINE_LIMIT = 300
PLACEHOLDER_CHARS = ("<", "{", "*", "…")

FRONTMATTER = re.compile(r"^---\r?\n(.*?)\r?\n---", re.S)
HIDDEN = re.compile(r"^disable-model-invocation:\s*true\s*$", re.M)
KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
CODE_SPAN = re.compile(r"(`+)(.+?)\1")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
LINK = re.compile(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
BACKTICK_PATH = re.compile(r"`((?:\.{1,2}/)*(?:references|scripts|templates|examples)/[^`\s]+)`")
PLACEHOLDER = re.compile(r"\b(TODO|TBD|FIXME|XXX)\b")
FORCE_LOAD = re.compile(r"(?<![\w@`])@((?:[\w.~-]+/)*[\w-]+\.[A-Za-z]{1,5})\b")
BANNED_WORDS = re.compile(r"\b(phase|slice|milestone)s?\b", re.I)
SKILL_REF = re.compile(r"(?<![\w/:.-])([a-z][a-z0-9-]*):([a-z][a-z0-9-]*)(?![\w-])")
INVOKE = re.compile(r"\bskill tool\b|\b(invoke[sd]?|invoking|call(?:s|ed|ing)?|run(?:s|ning)?|ran)\b", re.I)
VAGUE_LOAD = re.compile(r"\b(when relevant|if relevant|as needed|if needed)\b", re.I)
ROUTING = re.compile(r"^(when (not )?to use|handoffs?|related)\b")
DESCRIPTION_END = re.compile(r"Not for .+\([^()]+\)\.$")
BLOCK_SCALAR = re.compile(r"^[>|][+-]?$")


def relpath(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def excluded(rel):
    return rel.startswith(EXCLUDED_PREFIXES) or EXCLUDED_PATTERN.search(rel) is not None


def finding(path, line, rule, message):
    return Finding(relpath(path), line, SEVERITY[rule], rule, message)


def read_lines(path):
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def parse_frontmatter(lines):
    """Return (block, keys, body_start): keys maps a top-level key to (value, 1-based line)."""
    match = FRONTMATTER.match("\n".join(lines))
    if not match:
        return "", {}, 0
    block = match.group(1)
    block_lines = block.split("\n")
    keys = {}
    for index, line in enumerate(block_lines):
        key = re.match(r"^([A-Za-z][\w-]*):[ \t]*(.*?)[ \t]*$", line)
        if key:
            keys[key.group(1)] = (scalar_value(key.group(2), block_lines[index + 1:]), index + 2)
    return block, keys, len(block_lines) + 2


def scalar_value(value, following):
    if BLOCK_SCALAR.match(value):
        continued = []
        for line in following:
            if not line.startswith((" ", "\t")):
                break
            continued.append(line.strip())
        return " ".join(continued)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1].replace('\\"', '"')
    return value


def prose(lines, start):
    """Return (1-based line, text) for every line from `start` that is outside a fenced code block."""
    rows = []
    fence = None
    for index in range(start, len(lines)):
        line = lines[index]
        opener = FENCE.match(line)
        if fence is None and opener:
            fence = opener.group(1)
        elif fence is not None and opener and opener.group(1).startswith(fence) and not line.strip(fence[0]).strip():
            fence = None
        elif fence is None:
            rows.append((index + 1, line))
    return rows


def without_code_spans(line):
    return CODE_SPAN.sub("", line)


def headings(rows):
    found = []
    for number, line in rows:
        match = HEADING.match(line)
        if match:
            text = match.group(2).replace("*", "").replace("`", "").strip()
            found.append((number, len(match.group(1)), text))
    return found


def cells(line):
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def tables(rows):
    """Return (header line, header cells, [(line, cells)]) for every table in `rows`."""
    found = []
    index = 0
    while index < len(rows) - 1:
        number, line = rows[index]
        below_number, below = rows[index + 1]
        if line.lstrip().startswith("|") and below_number == number + 1 and SEPARATOR.match(below):
            body = []
            index += 2
            while index < len(rows) and rows[index][1].lstrip().startswith("|") \
                    and rows[index][0] == rows[index - 1][0] + 1:
                body.append((rows[index][0], cells(rows[index][1])))
                index += 1
            found.append((number, cells(line), body))
        else:
            index += 1
    return found


def section_span(rows, total, title):
    """Return (heading line, last line) of the `## <title>` section, or None when there is no such heading."""
    top = [(number, level, text) for number, level, text in headings(rows) if level <= 2]
    for position, (number, level, text) in enumerate(top):
        if level == 2 and text == title:
            return number, top[position + 1][0] - 1 if position + 1 < len(top) else total
    return None


def within(rows, span):
    return [(number, line) for number, line in rows if span[0] < number <= span[1]]


def check_r1(path, keys):
    if not keys:
        return [finding(path, 1, "R1", "no frontmatter: add name and description")]
    found = []
    for key in ("name", "description"):
        if not keys.get(key, ("", 0))[0]:
            found.append(finding(path, keys.get(key, ("", 1))[1], "R1", "frontmatter has no " + key))
    name, line = keys.get("name", ("", 1))
    if name and not KEBAB.match(name):
        found.append(finding(path, line, "R1", "name '%s' is not kebab-case" % name))
    return found


def check_r3(path, keys):
    description, line = keys.get("description", ("", 1))
    if not description:
        return []
    found = []
    if not description.startswith("Use when"):
        found.append(finding(path, line, "R3", "description does not start with 'Use when'"))
    if "Triggers:" in description:
        found.append(finding(path, line, "R3", "description writes 'Triggers:'; write Triggers \"a\", \"b\"."))
    elif 'Triggers "' not in description:
        found.append(finding(path, line, "R3", "description has no Triggers \"a\" clause"))
    if not DESCRIPTION_END.search(description):
        found.append(finding(path, line, "R3", "description does not end 'Not for <case> (<sibling>).'"))
    return found


def check_r6(path, rows):
    return [finding(path, number, "R6", "hidden skill has a routing heading '%s'; its agent routes it" % text)
            for number, _, text in headings(rows) if ROUTING.match(text.lower())]


def check_r7(path, rows):
    titles = [text.lower() for _, _, text in headings(rows)]
    return [finding(path, 1, "R7", "front door has no '%s' heading" % wanted)
            for wanted, pattern in (("When to use", r"^when to use\b"), ("When NOT to use", r"^when not to use\b"))
            if not any(re.match(pattern, title) for title in titles)]


def is_pattern(target):
    return any(char in target for char in PLACEHOLDER_CHARS)


def link_targets(line):
    targets = []
    for target in LINK.findall(without_code_spans(line)):
        if "://" in target or target.startswith(("#", "/", "mailto:")):
            continue
        targets.append(target.split("#", 1)[0])
    return targets


def check_r8(path, rows, base_dirs):
    found = []
    for number, line in rows:
        pointers = [(target, (os.path.dirname(path),)) for target in link_targets(line)]
        pointers += [(re.sub(r"(#.*|:\d+(-\d+)?)$", "", target), base_dirs) for target in BACKTICK_PATH.findall(line)]
        for target, bases in pointers:
            if is_pattern(target) or any(os.path.exists(os.path.join(base, target)) for base in bases):
                continue
            found.append(finding(path, number, "R8", "pointer '%s' does not resolve" % target))
    return found


def check_r9(path, lines, rows):
    if len(lines) <= REFERENCE_LINE_LIMIT:
        return []
    sections = [(number, text) for number, level, text in headings(rows) if level == 2]
    if not sections:
        return []
    preamble = "\n".join(line for number, line in rows if number < sections[0][0]).lower()
    missing = [text for _, text in sections if text.lower() not in preamble]
    if not missing:
        return []
    return [finding(path, 1, "R9", "over %d lines; the contents list before the first ## misses: %s"
                    % (REFERENCE_LINE_LIMIT, ", ".join(missing)))]


def check_r10(path, rows):
    found = []
    for number, line in rows:
        text = without_code_spans(line)
        for marker in PLACEHOLDER.findall(text):
            found.append(finding(path, number, "R10", "placeholder '%s'" % marker))
        for target in FORCE_LOAD.findall(text):
            found.append(finding(path, number, "R10", "force-load link '@%s'; point to the file instead" % target))
    return found


def check_r11(path, rows):
    found = []
    for number, _, text in headings(rows):
        for word in BANNED_WORDS.findall(text):
            found.append(finding(path, number, "R11", "heading uses '%s'; a unit of work is a task, its actions steps" % word))
    for number, header, _ in tables(rows):
        for word in BANNED_WORDS.findall(" ".join(header)):
            found.append(finding(path, number, "R11", "table header uses '%s'; a unit of work is a task" % word))
    return found


def check_r12(path, rows, hidden):
    found = []
    for number, line in rows:
        if not INVOKE.search(line):
            continue
        for plugin, name in SKILL_REF.findall(line):
            if name in hidden.get(plugin, ()):
                found.append(finding(path, number, "R12", "tells a model to invoke hidden skill %s:%s; "
                                     "name the path to Read, or the agent" % (plugin, name)))
    return found


def check_r13(path, lines, rows):
    found = []
    steps = section_span(rows, len(lines), "Steps")
    if steps is None:
        found.append(finding(path, 1, "R13", "agent has no '## Steps' section"))
    elif not any("Load" in header and "Done when" in header for _, header, _ in tables(within(rows, steps))):
        found.append(finding(path, steps[0], "R13", "'## Steps' holds no table with Load and Done when columns"))
    report = section_span(rows, len(lines), "Report")
    if report is None:
        found.append(finding(path, 1, "R13", "agent has no '## Report' section"))
    elif not any("Mode:" in line for line in lines[report[0]:report[1]]):
        found.append(finding(path, report[0], "R13", "'## Report' holds no Mode: line"))
    return found


def check_r14(path, lines, rows):
    steps = section_span(rows, len(lines), "Steps")
    step_rows = within(rows, steps) if steps else []
    found = []
    for _, header, body in tables(step_rows):
        if "Load" not in header:
            continue
        column = header.index("Load")
        for number, row in body:
            cell = row[column] if column < len(row) else ""
            for phrase in VAGUE_LOAD.findall(cell):
                found.append(finding(path, number, "R14", "Load cell says '%s'; name the visible condition" % phrase))
    return found


def body_checks(path, rows, base_dirs, hidden):
    return check_r8(path, rows, base_dirs) + check_r10(path, rows) + check_r11(path, rows) + check_r12(path, rows, hidden)


def lint_skill_file(path, hidden):
    lines = read_lines(path)
    block, keys, body_start = parse_frontmatter(lines)
    rows = prose(lines, body_start)
    found = check_r1(path, keys) + check_r3(path, keys)
    found += check_r6(path, rows) if HIDDEN.search(block) else check_r7(path, rows)
    return found + body_checks(path, rows, (os.path.dirname(path),), hidden)


def lint_companion(path, skill_dir, hidden):
    lines = read_lines(path)
    rows = prose(lines, parse_frontmatter(lines)[2])
    found = body_checks(path, rows, (os.path.dirname(path), skill_dir), hidden)
    if "references" in os.path.relpath(path, skill_dir).split(os.sep)[:-1]:
        found += check_r9(path, lines, rows)
    return found


def lint_agent(path, hidden):
    lines = read_lines(path)
    rows = prose(lines, parse_frontmatter(lines)[2])
    found = body_checks(path, rows, (os.path.dirname(path),), hidden)
    return found + check_r13(path, lines, rows) + check_r14(path, lines, rows)


def companions(skill_dir):
    found = [os.path.join(skill_dir, name) for name in sorted(os.listdir(skill_dir))
             if name.endswith(".md") and name != "SKILL.md"]
    for folder, _, files in os.walk(os.path.join(skill_dir, "references")):
        found += [os.path.join(folder, name) for name in sorted(files) if name.endswith(".md")]
    return found


def lint_skill(skill_dir, hidden):
    found = lint_skill_file(os.path.join(skill_dir, "SKILL.md"), hidden)
    for path in companions(skill_dir):
        found += lint_companion(path, skill_dir, hidden)
    return found


def skill_dirs(top):
    found = []
    for folder, dirs, files in os.walk(top):
        dirs[:] = sorted(name for name in dirs
                         if not excluded(os.path.relpath(os.path.join(folder, name), top).replace(os.sep, "/") + "/"))
        if "SKILL.md" in files:
            found.append(folder)
    return found


def owning_skill(path):
    folder = os.path.dirname(path)
    if os.path.isfile(os.path.join(folder, "SKILL.md")):
        return folder
    while "references" in folder.split(os.sep):
        folder = os.path.dirname(folder)
        if os.path.isfile(os.path.join(folder, "SKILL.md")):
            return folder
    return None


def lint_path(path, hidden):
    """Lint one argument: a skill folder (or a folder of skills), a SKILL.md, a rule or reference file, or an agent."""
    if os.path.isdir(path):
        return [found for folder in skill_dirs(path) for found in lint_skill(folder, hidden)]
    if os.path.basename(path) == "SKILL.md":
        return lint_skill(os.path.dirname(path), hidden)
    skill_dir = owning_skill(path)
    if skill_dir:
        return lint_companion(path, skill_dir, hidden)
    return lint_agent(path, hidden)


def load_plugins(root):
    path = os.path.join(root, ".claude-plugin", "marketplace.json")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)["plugins"]


def entry_path(root, entry):
    return os.path.join(root, entry[2:] if entry.startswith("./") else entry)


def hidden_names(root, plugins):
    """Map each plugin to the names of its registered skills that set disable-model-invocation: true."""
    hidden = {}
    for plugin in plugins:
        for entry in plugin.get("skills", []):
            skill_md = os.path.join(entry_path(root, entry), "SKILL.md")
            if not os.path.isfile(skill_md):
                continue
            block, keys, _ = parse_frontmatter(read_lines(skill_md))
            if HIDDEN.search(block) and keys.get("name", ("", 0))[0]:
                hidden.setdefault(plugin["name"], set()).add(keys["name"][0])
    return hidden


def sweep(root, plugins, hidden):
    found = [result for folder in skill_dirs(root) for result in lint_skill(folder, hidden)]
    agents = sorted({entry_path(root, entry) for plugin in plugins for entry in plugin.get("agents", [])})
    for agent in agents:
        if os.path.isfile(agent):
            found += lint_agent(agent, hidden)
    return found


def render(findings, as_json):
    ordered = sorted(set(findings))
    if as_json:
        return json.dumps([{"path": f.path, "line": f.line, "rule": f.rule, "severity": f.severity,
                            "message": f.message} for f in ordered], indent=2)
    return "\n".join("%s:%d: %s %s %s" % (f.path, f.line, f.severity, f.rule, f.message) for f in ordered)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Lint skills, agents and rule files against R1, R3, R6-R14.")
    parser.add_argument("paths", nargs="*", help="a SKILL.md, a skill folder, an agent .md or a rule file")
    parser.add_argument("--json", action="store_true", help="print a JSON array instead of lines")
    args = parser.parse_args(argv)
    for path in args.paths:
        if not os.path.exists(path):
            parser.error("no such path: " + path)
        if os.path.isfile(path) and not path.endswith(".md"):
            parser.error("not a Markdown file: " + path)
        if os.path.isdir(path) and not skill_dirs(os.path.abspath(path)):
            parser.error("no SKILL.md under " + path)
    plugins = load_plugins(ROOT)
    hidden = hidden_names(ROOT, plugins)
    if args.paths:
        findings = [f for path in args.paths for f in lint_path(os.path.abspath(path), hidden)]
    else:
        findings = sweep(ROOT, plugins, hidden)
    output = render(findings, args.json)
    if output:
        print(output)
    count = len(set(findings))
    print("%d finding%s" % (count, "" if count == 1 else "s"), file=sys.stderr)
    return 1 if count else 0


if __name__ == "__main__":
    sys.exit(main())
