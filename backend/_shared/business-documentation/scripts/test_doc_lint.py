import contextlib
import importlib.util
import io
import re
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFERENCES = HERE.parent / "references"
SPEC = importlib.util.spec_from_file_location("doc_lint", HERE / "doc-lint.py")
doc_lint = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doc_lint)


def levels(name="a"):
    return (f"**Levels:** [Guide]({name}.md) · [Behind the scenes]({name}.behind-the-scenes.md) · "
            f"[Technical reference]({name}.technical.md)")


LEVELS = levels()
OBSERVED_ROWS = [
    "| Guide | Booking a seat · steps 1–2 | Priced | see **R1** | `#observed` |",
    "| Behind the scenes | Booking a seat · step 2 | Priced later | see **R1**; Q2 | `#observed` |",
]


def header(audience, sha="abc1234", name="a"):
    return (
        f"**Created:** 2026-08-02\n**Owned by:** `x`\n**Derived from:** code @ `{sha}` on 2026-08-02\n"
        f"**Audience:** {audience}\n{levels(name)}\n"
    )


def document(title, audience, sections, name="a", sha="abc1234"):
    body = "\n\n".join(f"## {heading}\n\n{text}" for heading, text in sections.items())
    return f"# {title}\n\n{header(audience, sha, name)}\n{body}\n"


FLOW = "### Booking a seat\n\n1. A seat is priced.\n2. Credits go down.\n\n**What happens next**\n\n- Credits are spent.\n- Nothing is charged."


def about(audience, sha="abc1234", identifier="**Id:** AREA-001\n"):
    return (
        f"{identifier}**Created:** 2026-08-02\n**Owned by:** `x`\n**Derived from:** code @ `{sha}` on 2026-08-02\n"
        f"**Audience:** {audience}\n"
    )


def guide(audience="shareable", body="Members book sessions.", flow=FLOW, sections=None, identifier="**Id:** AREA-001\n"):
    parts = {
        "Who uses it": "| Who | What they do here |\n|---|---|\n| Members | Book |",
        "For members": flow,
        **(sections or {}),
        "Open questions": "| # | Question | Why |\n|---|---|---|\n| Q1 | Roll over? | Money |",
        "About this document": about(audience, identifier=identifier),
    }
    text = "\n\n".join(f"## {heading}\n\n{content}" for heading, content in parts.items())
    return f"# Area\n\n{body}\n\n{LEVELS}\n\n{text}\n"


def behind(audience="internal", body="The booking service tells the credits service.", questions="| Q2 | When? | Staleness |"):
    return document("Area — Behind the scenes", audience, {
        "At a glance": body, "The parts involved": "| Part | Does |\n|---|---|",
        "What happens behind the scenes": "### Booking a seat\n\n1. Saved.\n2. Priced.",
        "What is remembered, and where": "Bookings.", "Timing and ordering": "In order.",
        "When parts fail or are slow": "Retried.", "If you change this": "Check pricing.",
        "Open questions": f"| # | Question | Why |\n|---|---|---|\n{questions}",
    })


def technical(audience="internal", sha="abc1234", index_rows=None, extra="", tquestions="| T1 | Ordering? |",
              vocabulary="| Credits service | `CreditService` |"):
    sections = {title: "None." for title in doc_lint.REQUIRED_SECTIONS[doc_lint.TECH]}
    sections["How to read this"] = "Tiers: `#observed`, `#inferred`. Never `#confirmed`."
    sections["Rules, validations and decisions"] = "| Id | Rule |\n|---|---|\n| R1 | Cost from tier |" + extra
    sections["Business ↔ code vocabulary"] = f"| Business name | Code |\n|---|---|\n{vocabulary}"
    sections["Technical open questions"] = f"| # | Question |\n|---|---|\n{tquestions}"
    sections["Evidence index"] = index(index_rows or OBSERVED_ROWS)
    return document("Area — Technical reference", audience, sections, sha=sha)


def index(rows):
    return "| Level | Section | Statement | Evidence | Tier |\n|---|---|---|---|---|\n" + "\n".join(rows)


def overview_set():
    name = "system-overview"
    flow = "### First order\n\n1. Signs up.\n2. Orders."
    return {
        f"{name}.md": document("System", "shareable", {
            "Overview": "A shop.", "The areas": "Orders.", "End-to-end flows": flow, "What is not documented": "Nothing.",
        }, name),
        f"{name}.behind-the-scenes.md": document("System — Behind the scenes", "internal", {
            "At a glance": "Parts.", "What runs when": "Nightly.", "Where information lives": "One store.",
            "How a failure travels": "Retried.", "End-to-end flows": flow,
        }, name),
        f"{name}.technical.md": document("System — Technical reference", "internal", {
            "How to read this": "Tiers.", "Stack and versions": ".NET 8.", "Module structure": "One.",
            "Foundations": "| Id | Rule |\n|---|---|\n| R1 | Auth |", "Coverage ledger": "All.", "Findings": "None.",
            "Evidence index": index([
                "| Guide | First order · step 1 | Signs up | see **R1** | `#observed` |",
                "| Behind the scenes | First order · step 2 | Orders | see **R1** | `#observed` |",
            ]),
        }, name),
    }


def without_section(text, title):
    return re.sub(rf"## {re.escape(title)}\n\n.*?(?=\n## |\Z)", "", text, flags=re.DOTALL)


class DocLintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def write(self, texts):
        for name, text in texts.items():
            (self.folder / name).write_text(text, encoding="utf-8")

    def write_set(self, guide_text=None, behind_text=None, technical_text=None):
        self.write({"a.md": guide_text or guide(), "a.behind-the-scenes.md": behind_text or behind(),
                    "a.technical.md": technical_text or technical()})

    def run_dir(self, folder=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = doc_lint.main(["--dir", str(folder or self.folder)])
        return code, out.getvalue()

    def assert_fires(self, rule, severity="ERROR", folder=None):
        code, out = self.run_dir(folder)
        self.assertRegex(out, rf"(?m)^{severity} \S+ {re.escape(rule)} ", out)
        self.assertEqual(1 if severity == "ERROR" else 0, code, out)

    def assert_clean(self):
        self.assertEqual((0, ""), self.run_dir())

    def test_should_pass_when_set_is_compliant(self):
        self.write_set()
        self.assert_clean()

    def test_should_pass_when_golden_examples_are_linted(self):
        out = io.StringIO()
        files = [str(REFERENCES / n) for n in ("example-area.md", "example-behind-the-scenes.md", "example-technical.md")]
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = doc_lint.main(files)
        self.assertEqual((0, ""), (code, out.getvalue()))

    def test_should_pass_when_system_overview_uses_its_own_sections(self):
        self.write(overview_set())
        self.assert_clean()

    def test_should_report_index_coverage_when_system_overview_flow_uncited(self):
        texts = overview_set()
        texts["system-overview.technical.md"] = texts["system-overview.technical.md"].replace(
            "| Guide | First order · step 1", "| Guide | The areas")
        self.write(texts)
        self.assert_fires("index-coverage")

    def test_should_report_sections_when_system_overview_heading_missing(self):
        texts = overview_set()
        texts["system-overview.behind-the-scenes.md"] = texts["system-overview.behind-the-scenes.md"].replace(
            "## What runs when", "## Schedule")
        self.write(texts)
        self.assert_fires("sections")

    def test_should_report_no_sets_when_dir_missing(self):
        self.assert_fires("no-sets", folder=self.folder / "gone")

    def test_should_report_no_sets_when_dir_holds_no_set(self):
        self.write({"notes.md": "# Notes\n"})
        self.assert_fires("no-sets")

    def test_should_report_set_complete_when_sibling_missing(self):
        self.write({"a.technical.md": technical()})
        self.assert_fires("set-complete")

    def test_should_report_set_complete_when_technical_skipped(self):
        self.write({"a.md": guide(), "a.behind-the-scenes.md": behind()})
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

    def test_should_report_levels_links_when_label_points_at_another_level(self):
        self.write_set(guide_text=guide().replace("(a.technical.md)", "(a.md)"))
        self.assert_fires("levels-links")

    def test_should_report_header_when_guide_about_section_lacks_derived_from(self):
        self.write_set(guide_text=guide().replace("**Derived from:**", "**From:**"))
        self.assert_fires("header")

    def test_should_report_header_when_derived_from_missing_from_behind(self):
        self.write_set(behind_text=behind().replace("**Derived from:**", "**From:**"))
        self.assert_fires("header")

    def test_should_report_header_when_guide_id_missing(self):
        self.write_set(guide_text=guide(identifier=""))
        self.assert_fires("header")

    def test_should_report_header_when_guide_id_not_first_in_about(self):
        self.write_set(guide_text=guide().replace("**Id:** AREA-001\n**Created:** 2026-08-02", "**Created:** 2026-08-02\n**Id:** AREA-001"))
        self.assert_fires("header")

    def test_should_not_require_id_when_guide_is_a_feature_document(self):
        text = guide(identifier="").replace("**Owned by:** `x`\n**Derived from:** code", "**Generated by** feature-documenter")
        self.write_set(guide_text=text)
        self.assert_clean()

    def test_should_read_levels_line_when_it_sits_below_the_title_sentence(self):
        self.write_set(guide_text=guide().replace(LEVELS, "").replace("Members book sessions.", "Members book sessions.\n\n" + LEVELS))
        self.assert_clean()

    def test_should_skip_preamble_when_golden_example_precedes_the_document(self):
        preamble = "# Golden example\n\nSee `Pricing.cs` and the endpoint.\n\n---\n\n"
        self.write_set(guide_text=preamble + guide())
        self.assert_clean()

    def test_should_accept_feature_header_when_generated_by_present(self):
        text = guide().replace("**Owned by:** `x`\n**Derived from:** code", "**Generated by** feature-documenter")
        self.write_set(guide_text=text)
        self.assert_clean()

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

    def test_should_warn_stamp_agree_naming_file_when_sha_absent(self):
        self.write_set(technical_text=technical().replace("@ `abc1234`", ""))
        code, out = self.run_dir()
        self.assertIn("stamp-agree a.technical.md carries no commit sha", out)

    def test_should_report_tier_tags_when_in_guide(self):
        self.write_set(guide_text=guide(body="Members book. #observed"))
        self.assert_fires("tier-tags")

    def test_should_report_confirmed_when_in_guide(self):
        self.write_set(guide_text=guide(body="Members book. #confirmed"))
        self.assert_fires("confirmed")

    def test_should_warn_confirmed_when_human_promoted_level_3_row(self):
        self.write_set(technical_text=technical(extra="\n| R2 | Tagged | `#confirmed` |"))
        self.assert_fires("confirmed", "WARN")

    def test_should_check_topic_siblings_when_level_3_is_split(self):
        text = without_section(technical(), "Telemetry").replace("| R1 | Cost from tier |", "")
        self.write_set(technical_text=text)
        self.write({"a.technical.signals.md": "# Signals\n\n## Telemetry\n\n| Id | Rule |\n|---|---|\n| R1 | Cost |\n"})
        self.assert_clean()

    def test_should_report_sections_when_evidence_index_only_in_topic(self):
        self.write_set(technical_text=without_section(technical(), "Evidence index"))
        self.write({"a.technical.index.md": "# Index\n\n## Evidence index\n\n" + index(OBSERVED_ROWS) + "\n"})
        self.assert_fires("sections")

    def test_should_report_qid_unique_when_t_repeats_in_topic(self):
        self.write_set()
        self.write({"a.technical.more.md": "# More\n\n## Technical open questions\n\n| # | Q |\n|---|---|\n| T1 | Again |\n"})
        self.assert_fires("qid-unique")

    def test_should_report_code_nouns_when_status_code(self):
        self.write_set(behind_text=behind(body="It answers HTTP 409."))
        self.assert_fires("code-nouns")

    def test_should_report_code_nouns_when_reason_phrase(self):
        self.write_set(guide_text=guide(body="Staff get 409 Conflict."))
        self.assert_fires("code-nouns")

    def test_should_report_code_nouns_when_http_verb_and_path(self):
        self.write_set(guide_text=guide(body="Staff call PUT /plans/{id} to change it."))
        self.assert_fires("code-nouns")

    def test_should_warn_code_nouns_when_bare_status_after_response_word(self):
        self.write_set(behind_text=behind(body="The service answers 409."))
        self.assert_fires("code-nouns", "WARN")

    def test_should_warn_code_nouns_when_status_before_error_word(self):
        self.write_set(behind_text=behind(body="Staff see a 409 error."))
        self.assert_fires("code-nouns", "WARN")

    def test_should_pass_when_counts_resemble_status_codes(self):
        self.write_set(guide_text=guide(body="Of 400 accepted bookings, 250 created an overage; it returns 500 credits."))
        self.assert_clean()

    def test_should_pass_when_ratio_resembles_file_line(self):
        self.write_set(guide_text=guide(body="The ratio is 1.5:1."))
        self.assert_clean()

    def test_should_report_code_nouns_when_file_line_alone(self):
        self.write_set(guide_text=guide(body="See notes.txt:12 for it."))
        self.assert_fires("code-nouns")

    def test_should_report_code_nouns_when_source_file(self):
        self.write_set(guide_text=guide(body="See Pricing.cs for it."))
        self.assert_fires("code-nouns")

    def test_should_report_code_nouns_when_inline_code(self):
        self.write_set(guide_text=guide(body="The `credits` value."))
        self.assert_fires("code-nouns")

    def test_should_report_code_nouns_when_inside_fence(self):
        body = "```mermaid\nflowchart LR\n  A[`x.cs:12`] --> B\n```"
        self.write_set(behind_text=behind(body=body))
        self.assert_fires("code-nouns")

    def test_should_warn_code_nouns_when_class_name_in_mermaid_label(self):
        body = "```mermaid\nsequenceDiagram\n  A->>B: PricingEngine prices\n```"
        self.write_set(behind_text=behind(body=body))
        code, out = self.run_dir()
        self.assertEqual((0, 1), (code, out.count("code identifier")), out)

    def test_should_ignore_code_nouns_when_inside_link_target(self):
        self.write_set(behind_text=behind(body="See [the guide](docs/x.json)."))
        self.assert_clean()

    def test_should_warn_code_nouns_when_identifiers_in_any_case_style(self):
        body = "The PricingEngine, creditsUsed, IMessageHandler and membership_plans via PayPal."
        self.write_set(guide_text=guide(body=body))
        code, out = self.run_dir()
        self.assertEqual((0, 4), (code, out.count("code identifier")), out)

    def test_should_pass_when_identifier_declared_in_vocabulary(self):
        self.write_set(guide_text=guide(body="Ask the CreditService."),
                       technical_text=technical(vocabulary="| CreditService | `CreditService` |"))
        self.assert_clean()

    def test_should_report_jargon_when_guide_says_endpoint(self):
        self.write_set(guide_text=guide(body="The Endpoint prices it."))
        self.assert_fires("jargon")

    def test_should_report_jargon_when_plural_in_behind(self):
        self.write_set(behind_text=behind(body="The handlers price it."))
        self.assert_fires("jargon")

    def test_should_pass_when_behind_says_database(self):
        self.write_set(behind_text=behind(body="The booking is kept in the database."))
        self.assert_clean()

    def test_should_report_jargon_when_guide_says_database(self):
        self.write_set(guide_text=guide(body="The booking is kept in the database."))
        self.assert_fires("jargon")

    def test_should_pass_when_jargon_is_client_word_in_vocabulary(self):
        self.write_set(guide_text=guide(body="Partners send a webhook."),
                       technical_text=technical(vocabulary="| Partner webhook | `PartnerCallback` |"))
        self.assert_clean()

    def test_should_warn_defect_words_when_behind_judges(self):
        self.write_set(behind_text=behind(body="Credits are returned twice, which is a bug."))
        self.assert_fires("defect-words", "WARN")

    def test_should_warn_defect_words_when_stem_inflected(self):
        self.write_set(guide_text=guide(body="The total is computed incorrectly."))
        self.assert_fires("defect-words", "WARN")

    def test_should_pass_when_defect_word_is_quoted(self):
        self.write_set(guide_text=guide(body="Staff see “Something went wrong” or \"Wrong plan\"."))
        self.assert_clean()

    def test_should_warn_guarantee_words_when_timing_promised(self):
        self.write_set(behind_text=behind(body="The charge is posted immediately."))
        self.assert_fires("guarantee-words", "WARN")

    def test_should_pass_when_guarantee_word_is_quoted_or_negated(self):
        self.write_set(guide_text=guide(body="Staff see “Saved right away”; delivery is not guaranteed."))
        self.assert_clean()

    def test_should_report_qid_unique_when_q_repeats_across_levels(self):
        self.write_set(behind_text=behind(questions="| Q1 | Again? | Dup |\n| Q2 | When? | Staleness |"))
        self.assert_fires("qid-unique")

    def test_should_report_qid_unique_when_t_repeats(self):
        self.write_set(technical_text=technical(tquestions="| T1 | A? |\n| T1 | B? |"))
        self.assert_fires("qid-unique")

    def test_should_report_ref_resolves_when_bold_id_undefined(self):
        rows = ["| Guide | Booking a seat · step 1 | x | see **R9** | `#observed` |", OBSERVED_ROWS[1]]
        self.write_set(technical_text=technical(index_rows=rows))
        self.assert_fires("ref-resolves")

    def test_should_report_ref_resolves_when_plain_see_id_undefined(self):
        rows = ["| Guide | Booking a seat · step 1 | x | see R99 | `#observed` |", OBSERVED_ROWS[1]]
        self.write_set(technical_text=technical(index_rows=rows))
        self.assert_fires("ref-resolves")

    def test_should_report_ref_resolves_when_q_unknown(self):
        rows = ["| Guide | Booking a seat · step 1 | x | Q7 | `#observed` |", OBSERVED_ROWS[1]]
        self.write_set(technical_text=technical(index_rows=rows))
        self.assert_fires("ref-resolves")

    def test_should_pass_when_q_like_word_in_level_3_prose(self):
        self.write_set(technical_text=technical().replace("## Findings\n\nNone.", "## Findings\n\nQ3 reporting is separate."))
        self.assert_clean()

    def test_should_report_index_level_when_level_cell_unknown(self):
        rows = OBSERVED_ROWS + ["| Technical | Booking a seat | x | see **R1** | `#observed` |"]
        self.write_set(technical_text=technical(index_rows=rows))
        self.assert_fires("index-level")

    def test_should_report_index_evidence_when_inferred_row_names_no_question(self):
        rows = OBSERVED_ROWS + ["| Guide | Overview | x | comment at top | `#inferred` |"]
        self.write_set(technical_text=technical(index_rows=rows))
        self.assert_fires("index-evidence")

    def test_should_report_index_evidence_when_observed_row_has_no_evidence(self):
        rows = OBSERVED_ROWS + ["| Guide | Overview | x | — | `#observed` |"]
        self.write_set(technical_text=technical(index_rows=rows))
        self.assert_fires("index-evidence")

    def test_should_pass_when_inferred_row_names_question(self):
        rows = OBSERVED_ROWS + ["| Guide | Overview | x | comment; Q1 | `#inferred` |"]
        self.write_set(technical_text=technical(index_rows=rows))
        self.assert_clean()

    def test_should_report_index_coverage_when_flow_uncited(self):
        rows = ["| Guide | Overview | x | see **R1** | `#observed` |", OBSERVED_ROWS[1]]
        self.write_set(technical_text=technical(index_rows=rows))
        self.assert_fires("index-coverage")

    def test_should_report_index_coverage_when_only_longer_heading_cited(self):
        rows = ["| Guide | Booking a seat late · step 1 | x | see **R1** | `#observed` |", OBSERVED_ROWS[1]]
        self.write_set(technical_text=technical(index_rows=rows))
        self.assert_fires("index-coverage")

    def test_should_warn_index_steps_when_step_beyond_flow(self):
        rows = ["| Guide | Booking a seat · steps 1–4 | x | see **R1** | `#observed` |", OBSERVED_ROWS[1]]
        self.write_set(technical_text=technical(index_rows=rows))
        self.assert_fires("index-steps", "WARN")

    def test_should_report_sections_when_heading_missing(self):
        self.write_set(technical_text=technical().replace("## Telemetry", "## Signals"))
        self.assert_fires("sections")

    def test_should_report_sections_when_behind_lacks_timing(self):
        self.write_set(behind_text=without_section(behind(), "Timing and ordering"))
        self.assert_fires("sections")

    def test_should_report_sections_when_guide_lacks_who_uses_it(self):
        self.write_set(guide_text=without_section(guide(), "Who uses it"))
        self.assert_fires("sections")

    def test_should_report_sections_when_guide_has_no_for_section(self):
        self.write_set(guide_text=guide().replace("## For members", "## Tasks"))
        self.assert_fires("sections")

    def test_should_report_sections_when_guide_lacks_about_section(self):
        self.write_set(guide_text=without_section(guide(), "About this document"))
        self.assert_fires("sections")

    def test_should_report_index_coverage_when_task_under_second_person_section_uncited(self):
        text = guide(sections={"For staff": "### Setting a rate\n\n1. Open the plan."})
        self.write_set(guide_text=text)
        self.assert_fires("index-coverage")

    def test_should_report_index_coverage_when_automatic_work_uncited(self):
        text = guide(sections={"What happens automatically": "### Monthly posting\n\n**Trigger:** the 1st.\n\n1. Post."})
        self.write_set(guide_text=text)
        self.assert_fires("index-coverage")

    def test_should_not_require_a_row_when_heading_is_outside_the_flow_sections(self):
        self.write_set(guide_text=guide(sections={"Good to know": "### Can I roll credits over?\n\nNo."}))
        self.assert_clean()

    def test_should_pass_when_outcome_cited_within_the_task(self):
        rows = OBSERVED_ROWS + ["| Guide | Booking a seat · outcomes 1–2 | Spent | see **R1** | `#observed` |"]
        self.write_set(technical_text=technical(index_rows=rows))
        self.assert_clean()

    def test_should_warn_index_steps_when_outcome_beyond_task(self):
        rows = OBSERVED_ROWS + ["| Guide | Booking a seat · outcome 3 | Spent | see **R1** | `#observed` |"]
        self.write_set(technical_text=technical(index_rows=rows))
        self.assert_fires("index-steps", "WARN")

    def test_should_count_only_bullets_under_what_happens_next_as_outcomes(self):
        flow = FLOW + "\n\n**Good to know**\n\n- A tip.\n- Another tip."
        rows = OBSERVED_ROWS + ["| Guide | Booking a seat · outcome 3 | Spent | see **R1** | `#observed` |"]
        self.write_set(guide_text=guide(flow=flow), technical_text=technical(index_rows=rows))
        self.assert_fires("index-steps", "WARN")

    def test_should_report_internal_ids_when_area_id_in_body(self):
        self.write_set(guide_text=guide(body="Members book sessions, see AREA-003."))
        self.assert_fires("internal-ids")

    def test_should_report_internal_ids_when_flow_id_in_body(self):
        self.write_set(guide_text=guide(sections={"Related areas": "Priced by FLOW-004."}))
        self.assert_fires("internal-ids")

    def test_should_report_internal_ids_when_question_id_in_body(self):
        self.write_set(guide_text=guide(sections={"Good to know": "Roll-over is Q1."}))
        self.assert_fires("internal-ids")

    def test_should_report_internal_ids_when_question_id_outside_first_cell(self):
        self.write_set(guide_text=guide().replace("| Q1 | Roll over? | Money |", "| Q1 | Roll over? | See Q2 |"))
        self.assert_fires("internal-ids")

    def test_should_pass_internal_ids_when_ids_sit_in_about_and_first_cell(self):
        self.write_set(guide_text=guide().replace("**Audience:** shareable", "**Audience:** shareable\n**Models:** [FLOW-004 pricing]"))
        self.assert_clean()

    def test_should_report_internal_ids_when_id_in_mermaid_label_but_not_in_node_id(self):
        body = "```mermaid\nflowchart LR\n  FLOW-004[\"Priced\"] --> b[\"See ENT-003\"]\n```"
        self.write_set(guide_text=guide(sections={"How it fits together": body}))
        code, out = self.run_dir()
        self.assertEqual((1, 1), (code, out.count("internal-ids")), out)

    def test_should_not_apply_internal_ids_when_set_is_the_overview(self):
        texts = overview_set()
        texts["system-overview.md"] = texts["system-overview.md"].replace("A shop.", "A shop; see AREA-001.")
        self.write(texts)
        self.assert_clean()

    def test_should_report_alerts_when_kind_unknown(self):
        self.write_set(guide_text=guide(sections={"Good to know": "> [!CAUTION]\n> Careful."}))
        self.assert_fires("alerts")

    def test_should_report_alerts_when_kind_is_lowercase(self):
        self.write_set(guide_text=guide(sections={"Good to know": "> [!note]\n> Careful."}))
        self.assert_fires("alerts")

    def test_should_report_alerts_when_behind_uses_unknown_kind(self):
        self.write_set(behind_text=behind(body="> [!DANGER]\n> Careful."))
        self.assert_fires("alerts")

    def test_should_pass_when_every_allowed_alert_kind_is_used(self):
        alerts = "\n\n".join(f"> [!{kind}]\n> Text." for kind in ("NOTE", "TIP", "IMPORTANT", "WARNING"))
        self.write_set(guide_text=guide(sections={"Good to know": alerts}))
        self.assert_clean()

    def test_should_pass_when_mermaid_fence_holds_arrows_and_node_ids(self):
        body = "```mermaid\nstateDiagram-v2\n  [*] --> spent: Book a session\n  PricingEngine --> spent\n```"
        self.write_set(guide_text=guide(sections={"How it fits together": body}))
        self.assert_clean()

    def test_should_warn_code_nouns_when_class_name_in_quoted_mermaid_label(self):
        body = "```mermaid\nflowchart LR\n  a[\"PricingEngine\"] --> b[\"Done\"]\n```"
        self.write_set(guide_text=guide(sections={"How it fits together": body}))
        code, out = self.run_dir()
        self.assertEqual((0, 1), (code, out.count("code identifier")), out)

    def test_should_report_jargon_when_mermaid_label_after_colon_says_endpoint(self):
        body = "```mermaid\nstateDiagram-v2\n  [*] --> spent: Call the endpoint\n```"
        self.write_set(guide_text=guide(sections={"How it fits together": body}))
        self.assert_fires("jargon")

    def test_should_report_jargon_when_quoted_mermaid_label_says_webhook(self):
        body = "```mermaid\nflowchart LR\n  a[\"Webhook\"] --> b[\"Done\"]\n```"
        self.write_set(guide_text=guide(sections={"How it fits together": body}))
        self.assert_fires("jargon")

    def test_should_not_read_other_fences_as_prose_when_checking_jargon(self):
        body = "```text\nthe endpoint\n```"
        self.write_set(guide_text=guide(sections={"Good to know": body}))
        self.assert_clean()

    def test_should_warn_example_when_task_has_formula_and_no_example(self):
        flow = FLOW.replace("**What happens next**", "**What happens next**\n\n- Priced:\n\n  Credit cost = the tier's cost")
        self.write_set(guide_text=guide(flow=flow))
        self.assert_fires("example", "WARN")

    def test_should_pass_example_when_task_holds_an_example(self):
        flow = FLOW.replace("**What happens next**", "**What happens next**\n\n- Priced:\n\n  Credit cost = the tier's cost") + "\n\n**Example**\n\nAna pays 3."
        self.write_set(guide_text=guide(flow=flow))
        self.assert_clean()

    def test_should_pass_example_when_guide_has_a_story_in_numbers(self):
        flow = FLOW.replace("**What happens next**", "**What happens next**\n\n- Priced:\n\n  Credit cost = the tier's cost")
        self.write_set(guide_text=guide(flow=flow, sections={"A month in numbers": "Ana pays 3."}))
        self.assert_clean()

    def test_should_exit_with_usage_when_two_files_given(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            doc_lint.main(["a.md", "b.md"])
        self.assertEqual(2, raised.exception.code)


if __name__ == "__main__":
    unittest.main()
