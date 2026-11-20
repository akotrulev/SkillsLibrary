import importlib.util
import json
import os
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures" / "skill-lint"
SPEC = importlib.util.spec_from_file_location("skill_lint", HERE / "skill-lint.py")
skill_lint = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(skill_lint)

HIDDEN = {"dev": {"secret-skill"}}
GOOD_DESCRIPTION = 'Use when testing. Triggers "lint it". Not for production (front-door).'
AGENT_STEPS = "## Steps\n\n| # | Step | Load | Done when |\n|---|---|---|---|\n| 1 | Build | `x` | built |\n"
AGENT_REPORT = "## Report\n\n```\nMode: BUILD\n```\n"


@pytest.fixture
def tree(tmp_path):
    def write(rel, text):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return str(path)
    return write


def rules_of(findings):
    return sorted(f.rule for f in findings)


def messages_of(findings):
    return sorted(f.message for f in findings)


def rows_of(text):
    lines = text.split("\n")
    return skill_lint.prose(lines, skill_lint.parse_frontmatter(lines)[2])


def skill(name="demo", description=GOOD_DESCRIPTION, hidden=True, body=""):
    flag = "disable-model-invocation: true\n" if hidden else ""
    return "---\nname: %s\ndescription: %s\n%s---\n\n# Demo\n\n%s" % (name, description, flag, body)


# fixtures on disk

def test_should_report_nothing_when_linting_the_clean_fixtures():
    paths = [str(FIXTURES / "clean-skill"), str(FIXTURES / "clean-agent.md")]

    findings = [f for path in paths for f in skill_lint.lint_path(path, HIDDEN)]

    assert findings == []


@pytest.mark.parametrize("fixture, expected", [
    ("r1-missing-name", ["R1"]),
    ("r1-not-kebab", ["R1"]),
    ("r3-bad-description", ["R3", "R3", "R3"]),
    ("r6-hidden-routing", ["R6", "R6"]),
    ("r7-front-door-no-routing", ["R7", "R7"]),
    ("r8-dangling-ref", ["R8", "R8"]),
    ("r9-no-contents", ["R9"]),
    ("r10-placeholder", ["R10", "R10"]),
    ("r11-vocabulary", ["R11", "R11"]),
    ("r12-hidden-invoke", ["R12"]),
    ("r13-agent-shape.md", ["R13", "R13"]),
    ("r13-steps-no-table.md", ["R13", "R13"]),
    ("r14-load-cell.md", ["R14", "R14"]),
])
def test_should_trip_only_its_rule_when_linting_a_breaking_fixture(fixture, expected):
    assert rules_of(skill_lint.lint_path(str(FIXTURES / fixture), HIDDEN)) == expected


def test_should_give_each_rule_its_table_severity_when_reporting():
    findings = skill_lint.lint_path(str(FIXTURES / "r3-bad-description"), HIDDEN)

    assert {f.severity for f in findings} == {"minor"}


# exclusions

@pytest.mark.parametrize("rel, expected", [
    ("communication/x/", True),
    ("tools/fixtures/skill-lint/", True),
    ("auth/cognito-react/x/", True),
    ("qa/vendor/lib/", True),
    ("auth/auth0-react/", False),
    ("engineering-practices/debugging/", False),
])
def test_should_exclude_by_name_when_a_path_is_out_of_scope(rel, expected):
    assert skill_lint.excluded(rel) is expected


def test_should_skip_an_excluded_folder_when_walking_for_skills(tree, tmp_path):
    tree("a/SKILL.md", skill())
    tree("a/vendor/b/SKILL.md", skill())

    assert skill_lint.skill_dirs(str(tmp_path)) == [str(tmp_path / "a")]


# frontmatter

def test_should_return_empty_frontmatter_when_the_file_has_none():
    assert skill_lint.parse_frontmatter(["# Title"]) == ("", {}, 0)


def test_should_join_a_folded_block_scalar_when_the_description_uses_one():
    lines = ["---", "name: x", "description: >-", "  Use when", "  folded.", "tools: Read", "---"]

    keys = skill_lint.parse_frontmatter(lines)[1]

    assert keys["description"] == ("Use when folded.", 3)


def test_should_strip_quotes_when_the_description_is_quoted():
    keys = skill_lint.parse_frontmatter(["---", 'description: "Use \\"a\\" now"', "---"])[1]

    assert keys["description"][0] == 'Use "a" now'


# fences, headings, tables

def test_should_skip_fenced_lines_when_collecting_prose():
    lines = ["one", "~~~~", "hidden", "~~~ not a close", "~~~~", "two"]

    assert skill_lint.prose(lines, 0) == [(1, "one"), (6, "two")]


def test_should_end_a_table_when_a_row_is_not_contiguous():
    rows = [(1, "| a |"), (2, "|---|"), (3, "| 1 |"), (5, "| 2 |")]

    assert skill_lint.tables(rows) == [(1, ["a"], [(3, ["1"])])]


def test_should_end_a_section_when_a_level_one_heading_follows():
    rows = rows_of("## Steps\ntext\n# Top\nmore")

    assert skill_lint.section_span(rows, 4, "Steps") == (1, 2)


def test_should_return_no_section_when_the_heading_is_absent():
    assert skill_lint.section_span(rows_of("## Other\n"), 2, "Steps") is None


# R1

@pytest.mark.parametrize("text, expected", [
    ("# no frontmatter", ["no frontmatter: add name and description"]),
    ("---\ndescription: d\n---\n", ["frontmatter has no name"]),
    ("---\nname: x\ndescription:\n---\n", ["frontmatter has no description"]),
    ("---\nname: Bad Name\ndescription: d\n---\n", ["name 'Bad Name' is not kebab-case"]),
    ("---\nname: good-name\ndescription: d\n---\n", []),
])
def test_should_check_name_and_description_when_reading_frontmatter(text, expected):
    keys = skill_lint.parse_frontmatter(text.split("\n"))[1]

    assert messages_of(skill_lint.check_r1("x/SKILL.md", keys)) == expected


# R3

@pytest.mark.parametrize("description, expected", [
    (GOOD_DESCRIPTION, []),
    ("", []),
    ('Helps. Triggers "a". Not for b (c).', ["description does not start with 'Use when'"]),
    ("Use when x. Triggers: a. Not for b (c).", ["description writes 'Triggers:'; write Triggers \"a\", \"b\"."]),
    ("Use when x. Not for b (c).", ["description has no Triggers \"a\" clause"]),
    ('Use when x. Triggers "a". Not for b.', ["description does not end 'Not for <case> (<sibling>).'"]),
])
def test_should_check_the_description_shape_when_a_skill_has_one(description, expected):
    keys = {"description": (description, 3)}

    assert messages_of(skill_lint.check_r3("x/SKILL.md", keys)) == expected


# R6, R7

def test_should_flag_a_routing_heading_when_the_skill_is_hidden(tree):
    path = tree("s/SKILL.md", skill(body="## Handoffs\n\n## Rules\n"))

    assert messages_of(skill_lint.lint_skill_file(path, {})) == [
        "hidden skill has a routing heading 'Handoffs'; its agent routes it"]


def test_should_accept_both_fences_when_a_front_door_has_them(tree):
    path = tree("s/SKILL.md", skill(hidden=False, body="## When to use\n\n## When NOT to use\n"))

    assert skill_lint.lint_skill_file(path, {}) == []


# R8

@pytest.mark.parametrize("line", [
    "See [site](https://example.com) and [top](#top) and [abs](/etc/x) and [mail](mailto:a@b.c).",
    "A pattern `references/<topic>.md` and `scripts/{name}.py` and `examples/*.md` and `templates/…`.",
    "The folder `references/` is a name, not a pointer.",
    "Read `references/real.md:12` and `references/real.md#part` and [it](references/real.md#part).",
    "A link inside code `[x](missing.md)` is not a link.",
])
def test_should_not_flag_a_pointer_when_it_resolves_or_is_not_a_path(tree, line):
    path = tree("s/SKILL.md", skill(body=line + "\n"))
    tree("s/references/real.md", "# Real\n")

    assert skill_lint.lint_path(path, {}) == []


def test_should_resolve_a_backticked_path_from_the_skill_root_when_a_reference_names_a_sibling(tree):
    tree("s/SKILL.md", skill())
    tree("s/references/other.md", "# Other\n")
    path = tree("s/references/one.md", "Read `references/other.md` and [this](other.md).\n")

    assert skill_lint.lint_path(path, {}) == []


def test_should_resolve_a_markdown_link_from_the_file_folder_only_when_checking_a_reference(tree):
    tree("s/SKILL.md", skill())
    tree("s/references/other.md", "# Other\n")
    path = tree("s/references/one.md", "Read [this](references/other.md).\n")

    assert messages_of(skill_lint.lint_path(path, {})) == ["pointer 'references/other.md' does not resolve"]


# R9

def long_reference(preamble):
    body = "".join("## %s\n\n%s" % (title, "text\n" * 110) for title in ("Alpha", "Beta", "Gamma"))
    return "# Long\n\n" + preamble + body


@pytest.mark.parametrize("text, expected", [
    ("# Short\n\n## Alpha\n", []),
    ("# No sections\n" + "text\n" * 320, []),
    (long_reference("- Alpha\n- Beta\n- Gamma\n\n"), []),
    (long_reference("- Alpha\n\n"), ["over 300 lines; the contents list before the first ## misses: Beta, Gamma"]),
])
def test_should_require_a_contents_list_when_a_reference_is_long(tree, text, expected):
    tree("s/SKILL.md", skill())
    path = tree("s/references/long.md", text)

    assert messages_of(skill_lint.lint_path(path, {})) == expected


def test_should_not_apply_r9_when_a_long_file_is_a_rule_file_beside_skill_md(tree):
    tree("rules/SKILL.md", skill(name="rules"))
    path = tree("rules/core.md", long_reference(""))

    assert skill_lint.lint_path(path, {}) == []


# R10

@pytest.mark.parametrize("line, expected", [
    ("Remove `TODO` markers and `FIXME` notes.", []),
    ("Mail a@docs.md or use the `@types/node` package or @types/node.", []),
    ("FIXME later; XXX and TBD too.", ["placeholder 'FIXME'", "placeholder 'TBD'", "placeholder 'XXX'"]),
    ("Load @~/notes/plan.md now.", ["force-load link '@~/notes/plan.md'; point to the file instead"]),
])
def test_should_flag_a_placeholder_when_it_sits_outside_code(line, expected):
    assert messages_of(skill_lint.check_r10("x.md", [(1, line)])) == expected


# R11

def test_should_flag_banned_vocabulary_only_in_headings_and_table_headers():
    rows = rows_of("## Phases\n\nA slice of bread.\n\n| Step | Owner |\n|---|---|\n| slice | me |\n\n"
                   "| Milestone |\n|---|\n")

    assert [(f.line, f.message.split(";")[0]) for f in skill_lint.check_r11("x.md", rows)] == [
        (1, "heading uses 'Phase'"), (9, "table header uses 'Milestone'")]


# R12

@pytest.mark.parametrize("line, expected", [
    ("Invoke `dev:secret-skill` now.", 1),
    ("Use the Skill tool on dev:secret-skill.", 1),
    ("Read dev:secret-skill by path.", 0),
    ("Run `/dev:secret-skill` yourself.", 0),
    ("Run dev:visible-skill.", 0),
    ("Run other:secret-skill.", 0),
])
def test_should_flag_a_hidden_invocation_when_a_verb_meets_a_hidden_name(line, expected):
    assert len(skill_lint.check_r12("x.md", [(1, line)], HIDDEN)) == expected


# R13, R14

def agent(text):
    return "---\nname: a\ndescription: d\n---\n\n# Agent\n\n" + text


def test_should_accept_the_shape_when_an_agent_has_steps_and_report(tree):
    path = tree("agents/a.md", agent(AGENT_STEPS + "\n" + AGENT_REPORT))

    assert skill_lint.lint_path(path, {}) == []


def test_should_flag_an_empty_steps_section_when_it_holds_no_table(tree):
    path = tree("agents/a.md", agent("## Steps\n## Report\n\nMode: BUILD\n"))

    assert messages_of(skill_lint.lint_path(path, {})) == [
        "'## Steps' holds no table with Load and Done when columns"]


def test_should_read_the_report_to_the_file_end_when_it_is_the_last_section(tree):
    path = tree("agents/a.md", agent(AGENT_STEPS + "\n## Report\n\nChanged files.\n"))

    assert messages_of(skill_lint.lint_path(path, {})) == ["'## Report' holds no Mode: line"]


def test_should_skip_load_checks_when_a_table_has_no_load_column(tree):
    steps = "## Steps\n\n| # | Notes |\n|---|---|\n| 1 | as needed |\n\n" + AGENT_STEPS.replace("## Steps\n", "")
    path = tree("agents/a.md", agent(steps + "\n" + AGENT_REPORT))

    assert skill_lint.lint_path(path, {}) == []


def test_should_treat_a_missing_cell_as_empty_when_a_row_is_short(tree):
    steps = "## Steps\n\n| # | Step | Load | Done when |\n|---|---|---|---|\n| 1 | Build |\n"
    path = tree("agents/a.md", agent(steps + "\n" + AGENT_REPORT))

    assert skill_lint.lint_path(path, {}) == []


def test_should_skip_load_checks_when_an_agent_has_no_steps():
    assert skill_lint.check_r14("a.md", ["# A"], [(1, "# A")]) == []


# path routing

def test_should_lint_the_whole_skill_when_given_its_skill_md(tree):
    path = tree("s/SKILL.md", skill(body="TODO\n"))
    tree("s/references/deep/more.md", "XXX\n")

    assert rules_of(skill_lint.lint_path(path, {})) == ["R10", "R10"]


def test_should_lint_as_an_agent_when_no_skill_owns_the_file(tree):
    path = tree("docs/references/x.md", "# Not an agent shape\n")

    assert rules_of(skill_lint.lint_path(path, {})) == ["R13", "R13"]


# marketplace

def marketplace(tree, plugins):
    tree(".claude-plugin/marketplace.json", json.dumps({"plugins": plugins}))


def test_should_find_no_plugins_when_the_marketplace_is_absent(tmp_path):
    assert skill_lint.load_plugins(str(tmp_path)) == []


def test_should_collect_hidden_names_per_plugin_when_reading_the_marketplace(tree, tmp_path):
    tree("a/SKILL.md", skill(name="secret-skill"))
    tree("b/SKILL.md", skill(name="open-skill", hidden=False))
    marketplace(tree, [{"name": "dev", "skills": ["./a", "./b", "./missing"]}, {"name": "qa"}])

    plugins = skill_lint.load_plugins(str(tmp_path))

    assert skill_lint.hidden_names(str(tmp_path), plugins) == {"dev": {"secret-skill"}}


def test_should_lint_every_skill_and_registered_agent_when_sweeping(tree, tmp_path):
    tree("a/SKILL.md", skill(body="TODO\n"))
    tree("agents/x.md", agent(AGENT_STEPS + "\n" + AGENT_REPORT + "TBD\n"))
    plugins = [{"name": "dev", "agents": ["./agents/x.md", "./agents/gone.md"]}]

    findings = skill_lint.sweep(str(tmp_path), plugins, {})

    assert rules_of(findings) == ["R10", "R10"]


# output and main

def test_should_render_sorted_lines_when_output_is_text():
    findings = [skill_lint.Finding("b.md", 2, "minor", "R11", "y"), skill_lint.Finding("a.md", 9, "major", "R10", "x")]

    assert skill_lint.render(findings, False) == "a.md:9: major R10 x\nb.md:2: minor R11 y"


def test_should_render_a_json_array_when_output_is_json():
    findings = [skill_lint.Finding("a.md", 9, "major", "R10", "x")]

    assert json.loads(skill_lint.render(findings, True)) == [
        {"path": "a.md", "line": 9, "rule": "R10", "severity": "major", "message": "x"}]


def test_should_exit_zero_when_the_paths_are_clean(capsys):
    code = skill_lint.main([str(FIXTURES / "clean-skill"), str(FIXTURES / "clean-agent.md")])

    assert (code, capsys.readouterr().err) == (0, "0 findings\n")


def test_should_exit_one_and_print_lines_when_a_path_has_findings(capsys):
    code = skill_lint.main([str(FIXTURES / "r1-not-kebab")])

    out = capsys.readouterr()
    assert (code, out.out, out.err) == (
        1, "tools/fixtures/skill-lint/r1-not-kebab/SKILL.md:2: major R1 name 'Not_Kebab' is not kebab-case\n",
        "1 finding\n")


def test_should_print_an_empty_json_array_when_clean_and_json_is_asked(capsys):
    skill_lint.main(["--json", str(FIXTURES / "clean-agent.md")])

    assert json.loads(capsys.readouterr().out) == []


@pytest.mark.parametrize("argument", ["no/such/path", str(HERE / "skill-lint.py")])
def test_should_exit_two_when_an_argument_is_not_lintable(argument):
    with pytest.raises(SystemExit) as raised:
        skill_lint.main([argument])

    assert raised.value.code == 2


def test_should_exit_two_when_a_folder_holds_no_skill(tmp_path):
    with pytest.raises(SystemExit) as raised:
        skill_lint.main([str(tmp_path)])

    assert raised.value.code == 2


def test_should_sweep_the_root_when_called_without_paths(tree, tmp_path, monkeypatch, capsys):
    tree("a/SKILL.md", skill(name="secret-skill"))
    tree("b/SKILL.md", skill(name="b", body="Invoke dev:secret-skill.\n"))
    marketplace(tree, [{"name": "dev", "skills": ["./a"]}])
    monkeypatch.setattr(skill_lint, "ROOT", str(tmp_path))

    code = skill_lint.main([])

    assert (code, capsys.readouterr().out.split(": ")[1].split(" ")[1]) == (1, "R12")


def test_should_resolve_relative_paths_when_run_from_another_folder(monkeypatch):
    monkeypatch.chdir(HERE)

    assert skill_lint.main([os.path.join("fixtures", "skill-lint", "clean-agent.md")]) == 0
