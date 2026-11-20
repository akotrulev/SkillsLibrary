#!/usr/bin/env python3
"""Lint for the mechanical rules of a business-model knowledge base. Judgement rules stay with the reviewer.

Usage:
  kb-lint.py [<kb dir>]      default docs/business-model

Output: <file>:<line>: <severity> <rule-id> <message>, one line per finding, severities as the product
rule files tag them (blocker, major, minor, nit), then a count on stderr. Exit 1 when a finding is major or above,
2 when the directory does not exist, 0 otherwise. A rule id's prefix names its rule file: model- business-model.md,
entities- business-model-entities.md, decisions- business-model-decisions.md, connections-
business-model-connections.md, interactions- business-model-interactions.md. Area guides and system-overview.md are
product:doc-business-model's and its doc-lint.py's; here they only take part in id uniqueness and INDEX link resolution.

Rules:
  model-index             major    INDEX.md is missing, an INDEX link does not resolve, or a flow, entity, decision,
                                   connection file, glossary.md, interaction-map.md or active-context.md has no line
  model-id                blocker  a flow, entity or decision title carries no FLOW-/ENT-/DEC-nnn id; a trigger,
                                   reaction or invariant id is not EVT-/RX-/INV-nnn; a flow step is not FLOW-nnn.k
  model-id-unique         blocker  an AREA-/FLOW-/ENT-/DEC-/CONF-/EVT-/RX-/INV- id or flow node defined twice
  model-header            minor    a flow, entity, decision or connection file lacks **Created:** <date> or
                                   **Owned by:** before its first ## heading
  entities-states         minor    the States table has no Initial? or Terminal? column, or a value not yes, no or ?
  entities-cell           major    a blank grid cell, or a state with no grid row
  entities-reachable      major    a state no cell targets and not Initial? yes; a state whose row holds no legal
                                   transition and no ? and is not Terminal? yes
  entities-owner          major    a legal transition naming no owning feature id, or more than one
  entities-event-id       minor    with events.md present, a grid column header carrying no EVT- id
  decisions-hit-policy    major    no **Hit policy** line, or one that is not U, A, F, P, C, C+, C<, C>, C# or [TBD
  decisions-checks        major    no ## Checks section, or one without a Completeness or an Overlap line
  decisions-row           major    a rule row with no owning feature id or no source
  connections-kind        major    a trigger Kind outside command, schedule, timeout, external, event; an event
                                   trigger whose Fired by lists no RX- id
  connections-reaction    major    a reaction with a blank cell
  connections-mode        major    a Mode outside in request, after commit + delivery, scheduled, best effort
  connections-on-failure  major    an On failure outside rolls back, retried <n>× then <dead-letter|alert|drop>,
                                   compensates: <what>, unhandled, ?
  connections-when        major    a reaction's When names no EVT- id, or one that is not a trigger
  connections-consumed    major    an event trigger with no reaction and no "terminal by decision"
  connections-grid-column major    a grid column's EVT- id is not a trigger in events.md
  interactions-heading    blocker  a "## CONF" heading not shaped "## CONF-nnn — <feature> × <feature>: <conflict>"
  interactions-entry      major    an entry without Class (one of the eleven), Severity (blocker, major, minor, nit),
                                   Boundary condition, Pair, Sources or Artifacts updated
  interactions-open       blocker  an entry not #resolved whose id is not under active-context.md's Open questions
"""
import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_KB = Path("docs/business-model")
FAILING = ("blocker", "major")
SEVERITIES = ("blocker", "major", "minor", "nit")
MODEL_FOLDERS = {"flows": "FLOW", "entities": "ENT", "decisions": "DEC"}
CONNECTION_FILES = ("events.md", "shared-data.md", "invariants.md")
INDEXED_FILES = CONNECTION_FILES + ("glossary.md", "interaction-map.md", "active-context.md")
REACTION_COLUMNS = ("When", "Guard", "Owner", "Effects", "Emits", "Mode", "On failure", "Source")
KINDS = ("command", "schedule", "timeout", "external", "event")
CLASSES = (
    "contradictory rules", "trigger overlap", "state interference", "resource contention", "ordering/race",
    "circular dependency", "policy stacking", "permission/authority", "duplication/subsumption",
    "terminology drift", "boundary divergence",
)
ENTRY_FIELDS = ("Class", "Severity", "Boundary condition", "Pair", "Sources", "Artifacts updated")
STATE_FLAGS = ("yes", "no", "?")
NOT_LEGAL = ("—", "?")

HEADING = re.compile(r"^(#+)\s+(.*?)\s*$")
LINK = re.compile(r"\]\(([^)#\s]+)[^)]*\)")
OWNER = re.compile(r"\b(?:E\d+|AREA-\d+)\b")
EVT_ID = re.compile(r"\bEVT-\d+\b")
RX_ID = re.compile(r"\bRX-\d+\b")
CONF_ID = re.compile(r"\bCONF-\d+\b")
AREA_STAMP = re.compile(r"\bid: (AREA-\d+)\b")
CREATED = re.compile(r"^\*\*Created:\*\* \d{4}-\d{2}-\d{2}")
OWNED_BY = re.compile(r"^\*\*Owned by:\*\* \S")
HIT_POLICY_LINE = re.compile(r"^\*\*Hit policy(?::\*\*|\*\*:)\s*(.*)$")
HIT_POLICY = re.compile(r"^(?:\[TBD|(?:U|A|F|P|C[+<>#]?)(?=\s|\(|$))")
MODE = re.compile(r"^(?:in request|scheduled|best effort|after commit, (?:at-least-once|at-most-once|exactly-once|\?))$")
ON_FAILURE = re.compile(
    r"^(?:rolls back(?![\w-])|retried \d+× then (?:dead-letter|alert|drop)(?![\w-])|compensates: \S|unhandled(?![\w-])|\?)"
)
CONF_HEADING = re.compile(r"^## (CONF-\d+) — .+ × .+: .+")


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    severity: str
    rule: str
    message: str

    def __str__(self):
        return f"{self.file}:{self.line}: {self.severity} {self.rule} {self.message}"


def read(path):
    return path.read_text(encoding="utf-8").splitlines()


def heading_line(lines, title):
    return next((n for n, t in enumerate(lines, 1) if HEADING.match(t) and HEADING.match(t).group(2) == title), None)


def section(lines, title):
    """(line number, text) pairs under the first heading named `title`, at any level, up to the next heading."""
    start = heading_line(lines, title)
    if start is None:
        return []
    result = []
    for number in range(start + 1, len(lines) + 1):
        text = lines[number - 1]
        if HEADING.match(text):
            break
        result.append((number, text))
    return result


def header_region(lines):
    """The metadata block: the lines above the first ## heading."""
    end = next((i for i, t in enumerate(lines) if t.startswith("## ")), len(lines))
    return lines[:end]


def table(numbered_lines):
    """(header cells, [(line number, cells)]) of the table rows among the lines; ([], []) when there is no table."""
    rows = [(n, [c.strip() for c in t.strip().strip("|").split("|")]) for n, t in numbered_lines if t.lstrip().startswith("|")]
    if len(rows) < 2:
        return [], []
    return rows[0][1], rows[2:]


def cell(header, cells, name):
    """The row's cell under the column `name`; empty when the table has no such column or the row is short."""
    if name not in header:
        return ""
    index = header.index(name)
    return cells[index] if index < len(cells) else ""


def plain(text):
    return text.replace("*", "").strip()


def artifacts(kb):
    """Relative paths of every file that needs an INDEX.md line."""
    found = [p.relative_to(kb).as_posix() for folder in MODEL_FOLDERS for p in sorted((kb / folder).rglob("*.md"))]
    return found + [name for name in INDEXED_FILES if (kb / name).is_file()]


def check_index(kb, files):
    index = kb / "INDEX.md"
    if not index.is_file():
        return [Finding("INDEX.md", 1, "major", "model-index", "INDEX.md is missing (business-model.md)")]
    findings, linked = [], set()
    for number, text in enumerate(read(index), 1):
        for target in LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if (kb / target).is_file():
                linked.add((kb / target).resolve())
            else:
                findings.append(Finding("INDEX.md", number, "major", "model-index", f"link {target} does not resolve (business-model.md)"))
    findings += [
        Finding("INDEX.md", 1, "major", "model-index", f"no line links {name} (business-model.md)")
        for name in files if (kb / name).resolve() not in linked
    ]
    return findings


def check_header(name, lines):
    region = header_region(lines)
    findings = []
    if not any(CREATED.match(t) for t in region):
        findings.append(Finding(name, 1, "minor", "model-header", "no **Created:** <YYYY-MM-DD> line in the metadata block (business-model.md)"))
    if not any(OWNED_BY.match(t) for t in region):
        findings.append(Finding(name, 1, "minor", "model-header", "no **Owned by:** line in the metadata block (business-model.md)"))
    return findings


def title_definition(name, lines, prefix):
    """([(id, file, line)], findings) for the id in a flow, entity or decision title."""
    number = next((n for n, t in enumerate(lines, 1) if t.startswith("# ")), 1)
    match = re.search(rf"\(({prefix}-\d+)\)\s*$", lines[number - 1] if lines else "")
    if not match:
        return [], [Finding(name, number, "blocker", "model-id", f"the title carries no {prefix}-nnn id (business-model.md)")]
    return [(match.group(1), name, number)], []


def table_definitions(name, rows, pattern, what):
    defs, findings = [], []
    for number, cells in rows:
        if re.fullmatch(pattern, cells[0]):
            defs.append((cells[0], name, number))
        else:
            findings.append(Finding(name, number, "blocker", "model-id", f"{what} id '{cells[0]}' is not well-formed (business-model.md)"))
    return defs, findings


def flow_definitions(name, lines):
    defs, findings = title_definition(name, lines, "FLOW")
    if not defs:
        return defs, findings
    number = defs[0][0].split("-")[1]
    _, rows = table(section(lines, "Steps"))
    more, wrong = table_definitions(name, rows, rf"FLOW-{number}\.\d+", "flow node")
    return defs + more, findings + wrong


def definitions(kb, files):
    """([(id, file, line)] of every id the KB defines, findings for the malformed ones)."""
    defs, findings = [], []
    for name in files:
        lines = read(kb / name)
        folder = name.split("/")[0]
        if folder == "flows":
            found, wrong = flow_definitions(name, lines)
        elif folder in MODEL_FOLDERS:
            found, wrong = title_definition(name, lines, MODEL_FOLDERS[folder])
        elif name == "events.md":
            found, wrong = table_definitions(name, table(section(lines, "Triggers"))[1], r"EVT-\d+", "trigger")
            more, worse = table_definitions(name, table(section(lines, "Reactions"))[1], r"RX-\d+", "reaction")
            found, wrong = found + more, wrong + worse
        elif name == "invariants.md":
            found, wrong = table_definitions(name, table(enumerate(lines, 1))[1], r"INV-\d+", "invariant")
        elif name == "interaction-map.md":
            found = [(m.group(1), name, n) for n, t in enumerate(lines, 1) for m in [CONF_HEADING.match(t)] if m]
            wrong = []
        else:
            found, wrong = [], []
        defs += found
        findings += wrong
    for path in sorted((kb / "areas").glob("*.md")):
        name = path.relative_to(kb).as_posix()
        defs += [(m.group(1), name, n) for n, t in enumerate(read(path), 1) for m in [AREA_STAMP.search(t)] if m]
    return defs, findings


def check_unique(defs):
    first, findings = {}, []
    for identifier, name, number in defs:
        if identifier in first:
            seen = first[identifier]
            findings.append(Finding(name, number, "blocker", "model-id-unique",
                                    f"{identifier} is already defined at {seen[0]}:{seen[1]} (business-model.md)"))
        else:
            first[identifier] = (name, number)
    return findings


def check_states(name, lines):
    """(findings, {state: (initial, terminal)}) from the States table; a flag is None when its column is missing."""
    header, rows = table(section(lines, "States"))
    number = heading_line(lines, "States") or 1
    findings = [
        Finding(name, number, "minor", "entities-states",
                f"the States table has no {column} column; an entity file in the older shape gains it when next edited (business-model-entities.md)")
        for column in ("Initial?", "Terminal?") if header and column not in header
    ]
    states = {}
    for row_number, cells in rows:
        flags = tuple(cell(header, cells, column) if column in header else None for column in ("Initial?", "Terminal?"))
        findings += [
            Finding(name, row_number, "minor", "entities-states", f"{plain(cells[0])}: '{flag}' is not yes, no or ? (business-model-entities.md)")
            for flag in flags if flag is not None and flag not in STATE_FLAGS
        ]
        states[plain(cells[0])] = flags
    return findings, states


def check_cell(name, number, state, event, value):
    """(findings, target state or None) for one grid cell."""
    if not value:
        return [Finding(name, number, "major", "entities-cell", f"{state} × {event} is blank (business-model-entities.md)")], None
    if value in NOT_LEGAL:
        return [], None
    owners = set(OWNER.findall(value))
    target = re.split(r"\s*[(,]", value)[0].strip()
    if not owners:
        return [Finding(name, number, "major", "entities-owner", f"{state} × {event} names no owning feature id (business-model-entities.md)")], target
    if len(owners) > 1:
        return [Finding(name, number, "major", "entities-owner",
                        f"{state} × {event} names {len(owners)} owning features: a double-fire (business-model-entities.md)")], target
    return [], target


def check_columns(name, number, events, triggers):
    findings = []
    for event in events:
        ids = EVT_ID.findall(event)
        if not ids:
            findings.append(Finding(name, number, "minor", "entities-event-id", f"column '{event}' carries no EVT- id (business-model-entities.md)"))
        findings += [
            Finding(name, number, "major", "connections-grid-column", f"{i} is not a trigger in events.md (business-model-connections.md)")
            for i in ids if i not in triggers
        ]
    return findings


def check_reachable(name, number, states, targets, rows):
    findings = []
    for state, (initial, terminal) in states.items():
        if initial is not None and initial != "yes" and state not in targets:
            findings.append(Finding(name, number, "major", "entities-reachable",
                                    f"{state} is targeted by no cell and is not Initial? yes: unreachable (business-model-entities.md)"))
        row = rows.get(state)
        if terminal is not None and terminal != "yes" and row is not None and all(v == "—" for v in row):
            findings.append(Finding(name, number, "major", "entities-reachable",
                                    f"{state} has no legal transition and no ? and is not Terminal? yes: dead (business-model-entities.md)"))
    return findings


def check_entity(name, lines, triggers):
    findings, states = check_states(name, lines)
    header, rows = table(section(lines, "Transition grid"))
    if not header:
        return findings
    number = heading_line(lines, "Transition grid")
    events = header[1:]
    if triggers is not None:
        findings += check_columns(name, number, events, triggers)
    targets, values = set(), {}
    for row_number, cells in rows:
        state = plain(cells[0])
        values[state] = [plain(cells[i + 1]) if i + 1 < len(cells) else "" for i in range(len(events))]
        for event, value in zip(events, values[state]):
            found, target = check_cell(name, row_number, state, event, value)
            findings += found
            targets.add(target)
    findings += [
        Finding(name, number, "major", "entities-cell", f"state {state} has no row in the transition grid (business-model-entities.md)")
        for state in states if state not in values
    ]
    return findings + check_reachable(name, number, states, targets, values)


def check_decision(name, lines):
    findings = []
    policy = next(((n, m.group(1).strip()) for n, t in enumerate(lines, 1) for m in [HIT_POLICY_LINE.match(t)] if m), None)
    if policy is None:
        findings.append(Finding(name, 1, "major", "decisions-hit-policy", "no **Hit policy** line (business-model-decisions.md)"))
    elif not HIT_POLICY.match(policy[1]):
        findings.append(Finding(name, policy[0], "major", "decisions-hit-policy",
                                f"'{policy[1]}' is not U, A, F, P, C, C+, C<, C>, C# or [TBD - needs business decision] (business-model-decisions.md)"))
    checks = heading_line(lines, "Checks")
    if checks is None:
        findings.append(Finding(name, 1, "major", "decisions-checks", "no Checks section (business-model-decisions.md)"))
    else:
        text = " ".join(t for _, t in section(lines, "Checks"))
        findings += [
            Finding(name, checks, "major", "decisions-checks", f"the Checks section records no {check} check (business-model-decisions.md)")
            for check in ("Completeness", "Overlap") if check not in text
        ]
    header, rows = table(section(lines, "Rules"))
    for number, cells in rows:
        if not OWNER.search(cell(header, cells, "Feature")):
            findings.append(Finding(name, number, "major", "decisions-row", f"rule {cells[0]} names no owning feature id (business-model-decisions.md)"))
        if not cell(header, cells, "Source"):
            findings.append(Finding(name, number, "major", "decisions-row", f"rule {cells[0]} names no source (business-model-decisions.md)"))
    return findings


def check_triggers(header, rows):
    findings = []
    for number, cells in rows:
        kind = cell(header, cells, "Kind")
        if kind not in KINDS:
            findings.append(Finding("events.md", number, "major", "connections-kind",
                                    f"{cells[0]}: Kind '{kind}' is not command, schedule, timeout, external or event (business-model-connections.md)"))
        elif kind == "event" and not RX_ID.search(cell(header, cells, "Fired by")):
            findings.append(Finding("events.md", number, "major", "connections-kind",
                                    f"{cells[0]}: an event trigger's Fired by lists no RX- id (business-model-connections.md)"))
    return findings


def check_reaction(header, number, cells, triggers):
    findings = [
        Finding("events.md", number, "major", "connections-reaction", f"{cells[0]}: {column} is blank (business-model-connections.md)")
        for column in REACTION_COLUMNS if not cell(header, cells, column)
    ]
    mode, failure, when = (cell(header, cells, c) for c in ("Mode", "On failure", "When"))
    if mode and not MODE.match(mode):
        findings.append(Finding("events.md", number, "major", "connections-mode", f"{cells[0]}: Mode '{mode}' is outside the vocabulary (business-model-connections.md)"))
    if failure and not ON_FAILURE.match(failure):
        findings.append(Finding("events.md", number, "major", "connections-on-failure",
                                f"{cells[0]}: On failure '{failure}' is outside the vocabulary (business-model-connections.md)"))
    ids = EVT_ID.findall(when)
    if when and not ids:
        findings.append(Finding("events.md", number, "major", "connections-when", f"{cells[0]}: When names no EVT- trigger (business-model-connections.md)"))
    findings += [
        Finding("events.md", number, "major", "connections-when", f"{cells[0]}: When {i} is not a trigger (business-model-connections.md)")
        for i in ids if i not in triggers
    ]
    return findings


def check_events(lines):
    """(findings, the set of trigger ids)."""
    header, rows = table(section(lines, "Triggers"))
    triggers = {cells[0] for _, cells in rows}
    findings = check_triggers(header, rows)
    reaction_header, reactions = table(section(lines, "Reactions"))
    consumed = set()
    for number, cells in reactions:
        findings += check_reaction(reaction_header, number, cells, triggers)
        consumed.update(EVT_ID.findall(cell(reaction_header, cells, "When")))
    findings += [
        Finding("events.md", number, "major", "connections-consumed",
                f"{cells[0]}: no reaction consumes this event and it is not terminal by decision (business-model-connections.md)")
        for number, cells in rows
        if cell(header, cells, "Kind") == "event" and cells[0] not in consumed and "terminal by decision" not in " ".join(cells)
    ]
    return findings, triggers


def check_entry(number, heading, body):
    if not CONF_HEADING.match(heading):
        return [Finding("interaction-map.md", number, "blocker", "interactions-heading",
                        "not shaped '## CONF-nnn — <feature> × <feature>: <the conflict>' (business-model-interactions.md)")]
    findings, text = [], "\n".join(body)
    for field in ENTRY_FIELDS:
        match = re.search(rf"\*\*{field}\*\*:[^\S\n]*([^·\n]*[^·\s])", text)
        value = match.group(1).lower().replace(" / ", "/") if match else ""
        if not match:
            problem = f"no {field}"
        elif field == "Class" and not any(c in value for c in CLASSES):
            problem = f"class '{match.group(1)}' is not one of the eleven"
        elif field == "Severity" and value.split()[0] not in SEVERITIES:
            problem = f"severity '{match.group(1)}' is not blocker, major, minor or nit"
        else:
            continue
        findings.append(Finding("interaction-map.md", number, "major", "interactions-entry", f"{problem} (business-model-interactions.md)"))
    return findings


def check_interactions(lines, listed):
    findings = []
    starts = [n for n, t in enumerate(lines, 1) if t.startswith("## CONF")]
    for number in starts:
        end = next((n for n in range(number + 1, len(lines) + 1) if lines[n - 1].startswith("## ")), len(lines) + 1)
        heading = lines[number - 1]
        findings += check_entry(number, heading, lines[number:end - 1])
        identifier = CONF_ID.search(heading)
        if identifier and "#resolved" not in heading and identifier.group(0) not in listed:
            findings.append(Finding("interaction-map.md", number, "blocker", "interactions-open",
                                    f"open {identifier.group(0)} is not listed under active-context.md's Open questions (business-model-interactions.md)"))
    return findings


def lint(kb):
    files = artifacts(kb)
    defs, findings = definitions(kb, files)
    findings += check_index(kb, files) + check_unique(defs)
    triggers = None
    if (kb / "events.md").is_file():
        found, triggers = check_events(read(kb / "events.md"))
        findings += found
    for name in files:
        lines = read(kb / name)
        folder = name.split("/")[0]
        if folder in MODEL_FOLDERS or name in CONNECTION_FILES:
            findings += check_header(name, lines)
        if folder == "entities":
            findings += check_entity(name, lines, triggers)
        elif folder == "decisions":
            findings += check_decision(name, lines)
    if (kb / "interaction-map.md").is_file():
        context = kb / "active-context.md"
        listed = set(CONF_ID.findall(" ".join(t for _, t in section(read(context), "Open questions")))) if context.is_file() else set()
        findings += check_interactions(read(kb / "interaction-map.md"), listed)
    return sorted(findings, key=lambda f: (f.file, f.line, f.rule, f.message))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kb", nargs="?", type=Path, default=DEFAULT_KB, help="the knowledge-base directory")
    args = parser.parse_args(argv)
    if not args.kb.is_dir():
        print(f"kb-lint: {args.kb} is not a directory", file=sys.stderr)
        return 2
    findings = lint(args.kb)
    for finding in findings:
        print(f"{args.kb.as_posix().rstrip('/')}/{finding}")
    counts = ", ".join(f"{sum(f.severity == s for f in findings)} {s}" for s in SEVERITIES)
    print(f"kb-lint: {counts}", file=sys.stderr)
    return 1 if any(f.severity in FAILING for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
