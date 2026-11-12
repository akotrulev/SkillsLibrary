import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFERENCES = HERE.parent / "references"
SPEC = importlib.util.spec_from_file_location("doc_lint", HERE / "doc-lint.py")
doc_lint = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doc_lint)

LEVELS = "**Levels:** [Guide](a.md) · [Behind the scenes](a.behind-the-scenes.md) · [Technical reference](a.technical.md)"


def header(audience, sha="abc1234"):
    return (
        f"**Created:** 2026-08-02\n**Owned by:** `x`\n**Derived from:** code @ `{sha}` on 2026-08-02\n"
        f"**Audience:** {audience}\n{LEVELS}\n"
    )


def guide(audience="shareable", body="Members book sessions.", flow_steps="1. A seat is priced.\n2. Credits go down.\n"):
    return (
        f"# Area\n\n{header(audience)}\n## Overview\n\n{body}\n\n## How it works\n\n### Booking a seat\n\n{flow_steps}\n"
        "## Example\n\nAna books.\n\n## Open questions\n\n| # | Question | Why |\n|---|---|---|\n| Q1 | Roll over? | Money |\n\n"
        "## Going deeper\n\nSee the other levels.\n"
    )


def behind(audience="internal", body="The booking service tells the credits service.", questions="| Q2 | When? | Staleness |"):
    return (
        f"# Area — Behind the scenes\n\n{header(audience)}\n## At a glance\n\n{body}\n\n## The parts involved\n\n| Part | Does |\n|---|---|\n\n"
        "## What happens behind the scenes\n\n### Booking a seat\n\n1. Saved.\n2. Priced.\n\n## When parts fail or are slow\n\nRetried.\n\n"
        f"## Open questions\n\n| # | Question | Why |\n|---|---|---|\n{questions}\n"
    )


def technical(audience="internal", sha="abc1234", index_rows=None, extra="", tquestions="| T1 | Ordering? |"):
    rows = index_rows or [
        "| Guide | Booking a seat · steps 1–2 | Priced | see **R1** | `#observed` |",
        "| Behind the scenes | Booking a seat · step 2 | Priced later | see **R1**; Q2 | `#observed` |",
    ]
    sections = {title: "None." for title in doc_lint.REQUIRED_SECTIONS[doc_lint.TECH]}
    sections["How to read this"] = "Tiers: `#observed`, `#inferred`. Never `#confirmed`."
    sections["Rules, validations and decisions"] = "| Id | Rule |\n|---|---|\n| R1 | Cost from tier |" + extra
    sections["Technical open questions"] = f"| # | Question |\n|---|---|\n{tquestions}"
    sections["Evidence index"] = "| Level | Section | Statement | Evidence | Tier |\n|---|---|---|---|---|\n" + "\n".join(rows)
    body = "\n\n".join(f"## {title}\n\n{text}" for title, text in sections.items())
    return f"# Area — Technical reference\n\n{header(audience, sha)}\n{body}\n"


class DocLintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def write_set(self, guide_text=None, behind_text=None, technical_text=None):
        texts = {"a.md": guide_text or guide(), "a.behind-the-scenes.md": behind_text or behind(),
                 "a.technical.md": technical_text or technical()}
        for name, text in texts.items():
            (self.folder / name).write_text(text, encoding="utf-8")

    def run_dir(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = doc_lint.main(["--dir", str(self.folder)])
        return code, out.getvalue()

    def assert_fires(self, rule, severity="ERROR"):
        code, out = self.run_dir()
        self.assertIn(f"{severity} ", out, out)
        self.assertIn(f" {rule} ", out, out)
        self.assertEqual(1 if severity == "ERROR" else 0, code, out)

    def test_should_pass_when_set_is_compliant(self):
        self.write_set()
        self.assertEqual((0, ""), self.run_dir())

    def test_should_pass_when_golden_examples_are_linted(self):
        out = io.StringIO()
        files = [str(REFERENCES / n) for n in ("example-area.md", "example-behind-the-scenes.md", "example-technical.md")]
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = doc_lint.main(files)
        self.assertEqual((0, ""), (code, out.getvalue()))

    def test_should_report_set_complete_when_sibling_missing(self):
        (self.folder / "a.technical.md").write_text(technical(), encoding="utf-8")
        self.assert_fires("set-complete")

    def test_should_report_levels_links_when_target_missing(self):
        self.write_set(technical_text=technical().replace("(a.md)", "(gone.md)"))
        self.assert_fires("levels-links")

    def test_should_report_levels_links_when_label_missing(self):
        self.write_set(guide_text=guide().replace("[Guide]", "[Home]"))
        self.assert_fires("levels-links")

    def test_should_report_levels_links_when_no_levels_line(self):
        self.write_set(guide_text=guide().replace(LEVELS, ""))
        self.assert_fires("levels-links")

    def test_should_report_header_when_derived_from_missing(self):
        self.write_set(guide_text=guide().replace("**Derived from:**", "**From:**"))
        self.assert_fires("header")

    def test_should_accept_feature_header_when_generated_by_present(self):
        text = guide().replace("**Owned by:** `x`\n**Derived from:**", "**Generated by** feature-documenter")
        self.write_set(guide_text=text)
        self.assertEqual((0, ""), self.run_dir())

    def test_should_report_audience_when_missing(self):
        self.write_set(guide_text=guide().replace("**Audience:** shareable\n", ""))
        self.assert_fires("audience")

    def test_should_report_audience_when_value_unknown(self):
        self.write_set(guide_text=guide(audience="public"))
        self.assert_fires("audience")

    def test_should_report_audience_when_guide_internal(self):
        self.write_set(guide_text=guide(audience="internal"))
        self.assert_fires("audience")

    def test_should_report_audience_when_technical_shareable(self):
        self.write_set(technical_text=technical(audience="shareable"))
        self.assert_fires("audience")

    def test_should_warn_audience_when_behind_promoted(self):
        self.write_set(behind_text=behind(audience="shareable"))
        self.assert_fires("audience", "WARN")

    def test_should_warn_stamp_agree_when_shas_differ(self):
        self.write_set(technical_text=technical(sha="def5678"))
        self.assert_fires("stamp-agree", "WARN")

    def test_should_use_commit_line_when_no_header_sha(self):
        text = technical().replace("@ `abc1234`", "").replace("## How to read this", "**Commit:** `abc1234`\n\n## How to read this")
        self.write_set(technical_text=text)
        self.assertEqual((0, ""), self.run_dir())

    def test_should_report_tier_tags_when_in_guide(self):
        self.write_set(guide_text=guide(body="Members book. #observed"))
        self.assert_fires("tier-tags")

    def test_should_report_confirmed_when_outside_legend(self):
        self.write_set(technical_text=technical(extra="\n| R2 | Tagged | `#confirmed` |"))
        self.assert_fires("confirmed")

    def test_should_report_code_nouns_when_status_code(self):
        self.write_set(behind_text=behind(body="It answers HTTP 409."))
        self.assert_fires("code-nouns")

    def test_should_report_code_nouns_when_reason_phrase(self):
        self.write_set(guide_text=guide(body="Staff get 409 Conflict."))
        self.assert_fires("code-nouns")

    def test_should_report_code_nouns_when_source_file(self):
        self.write_set(guide_text=guide(body="See Pricing.cs for it."))
        self.assert_fires("code-nouns")

    def test_should_report_code_nouns_when_inline_code(self):
        self.write_set(guide_text=guide(body="The `credits` value."))
        self.assert_fires("code-nouns")

    def test_should_warn_code_nouns_when_camel_case(self):
        self.write_set(guide_text=guide(body="The CreditService prices it via PayPal."))
        code, out = self.run_dir()
        self.assertEqual((0, 1), (code, out.count("CamelCase")), out)

    def test_should_ignore_code_nouns_when_inside_fence_or_link(self):
        body = "```mermaid\nflowchart LR\n  A[`x.cs:12`] --> B\n```\n\nSee [the guide](docs/x.json)."
        self.write_set(behind_text=behind(body=body))
        self.assertEqual((0, ""), self.run_dir())

    def test_should_report_jargon_when_guide_says_endpoint(self):
        self.write_set(guide_text=guide(body="The Endpoint prices it."))
        self.assert_fires("jargon")

    def test_should_warn_defect_words_when_behind_judges(self):
        self.write_set(behind_text=behind(body="Credits are returned twice, which is a bug."))
        self.assert_fires("defect-words", "WARN")

    def test_should_report_qid_unique_when_q_repeats_across_levels(self):
        self.write_set(behind_text=behind(questions="| Q1 | Again? | Dup |\n| Q2 | When? | Staleness |"))
        self.assert_fires("qid-unique")

    def test_should_report_qid_unique_when_t_repeats(self):
        self.write_set(technical_text=technical(tquestions="| T1 | A? |\n| T1 | B? |"))
        self.assert_fires("qid-unique")

    def test_should_report_ref_resolves_when_bold_id_undefined(self):
        rows = ["| Guide | Booking a seat · step 1 | x | see **R9** | `#observed` |",
                "| Behind the scenes | Booking a seat · step 1 | x | see **R1** | `#observed` |"]
        self.write_set(technical_text=technical(index_rows=rows))
        self.assert_fires("ref-resolves")

    def test_should_report_ref_resolves_when_q_unknown(self):
        rows = ["| Guide | Booking a seat · step 1 | x | Q7 | `#observed` |",
                "| Behind the scenes | Booking a seat · step 1 | x | see **R1** | `#observed` |"]
        self.write_set(technical_text=technical(index_rows=rows))
        self.assert_fires("ref-resolves")

    def test_should_report_index_coverage_when_flow_uncited(self):
        rows = ["| Guide | Overview | x | see **R1** | `#observed` |",
                "| Behind the scenes | Booking a seat · step 1 | x | see **R1** | `#observed` |"]
        self.write_set(technical_text=technical(index_rows=rows))
        self.assert_fires("index-coverage")

    def test_should_warn_index_steps_when_step_beyond_flow(self):
        rows = ["| Guide | Booking a seat · steps 1–4 | x | see **R1** | `#observed` |",
                "| Behind the scenes | Booking a seat · step 2 | x | see **R1** | `#observed` |"]
        self.write_set(technical_text=technical(index_rows=rows))
        self.assert_fires("index-steps", "WARN")

    def test_should_report_sections_when_heading_missing(self):
        self.write_set(technical_text=technical().replace("## Telemetry", "## Signals"))
        self.assert_fires("sections")

    def test_should_exit_with_usage_when_two_files_given(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            doc_lint.main(["a.md", "b.md"])
        self.assertEqual(2, raised.exception.code)


if __name__ == "__main__":
    unittest.main()
