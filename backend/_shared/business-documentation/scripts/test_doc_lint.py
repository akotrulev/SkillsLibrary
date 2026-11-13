import contextlib
import importlib.util
import io
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


BEHIND_FLOW = "### Booking a seat\n\n1. Saved.\n2. Priced."


def behind(audience="internal", body="The booking service tells the credits service.", questions="| Q2 | When? | Staleness |",
           flow=BEHIND_FLOW, sections=None, sha="abc1234"):
    parts = {
        "At a glance": body, "The parts involved": "| Part | Does |\n|---|---|",
        "For members": flow,
        **(sections or {}),
        "What is remembered, and where": "Bookings.", "Timing and ordering": "In order.",
        "When parts fail or are slow": "Retried.", "If you change this": "Check pricing.",
        "Open questions": f"| # | Question | Why |\n|---|---|---|\n{questions}",
        "About this document": about(audience, sha, identifier="").replace(f"**Audience:** {audience}\n", ""),
    }
    text = "\n\n".join(f"## {heading}\n\n{content}" for heading, content in parts.items())
    return f"# Area — Behind the scenes\n\nHow it works.\n\n{LEVELS}\n**Audience:** {audience}\n\n{text}\n"


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
            "Who uses it": "| Who | What they do | Start here |\n|---|---|---|\n| Shoppers | Order | [Orders](areas/orders.md) |",
            "The journey": "A shop.", "Areas, by who uses them": "### For shoppers\n\nOrders.",
            "End-to-end flows": flow, "What is not documented": "Nothing.", "About this document": "Shop.",
        }, name),
        f"{name}.behind-the-scenes.md": document("System — Behind the scenes", "internal", {
            "At a glance": "Parts.", "What runs when": "Nightly.", "Where information lives": "One store.",
            "How a failure travels": "Retried.", "End-to-end flows": flow, "About this document": "Shop.",
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


def words(count):
    return " ".join(["word"] * count)


def prose(count):
    return " ".join(["Word."] * count)


def sentence(count):
    return "Word " + " ".join(["word"] * (count - 1)) + "."


def task(name):
    return f"### {name}\n\n1. Do it."


def cited(*headings, levels=("Guide", "Behind the scenes")):
    return OBSERVED_ROWS + [f"| {level} | {h} | Done | see **R1** | `#observed` |" for h in headings for level in levels]


def limited_task(steps, outcomes, alerts):
    parts = ["### Booking a seat", *(f"{i}. Step." for i in range(1, steps + 1)), "**What happens next**",
             *(f"- Outcome {i}." for i in range(1, outcomes + 1)),
             *(f"> [!NOTE]\n> Alert {i}." for i in range(1, alerts + 1))]
    return "\n\n".join(parts[:1]) + "\n\n" + "\n".join(parts[1:1 + steps]) + "\n\n" + parts[1 + steps] + "\n\n" + "\n".join(
        parts[2 + steps:2 + steps + outcomes]) + "".join("\n\n" + a for a in parts[2 + steps + outcomes:])


def without_section(text, title):
    return re.sub(rf"## {re.escape(title)}\n\n.*?(?=\n## |\Z)", "", text, flags=re.DOTALL)


INDEX_ENTRY = ("- [Area](areas/a.md) — AREA-001 · members, staff · Book and cancel sessions with credits · "
               "[behind the scenes](areas/a.behind-the-scenes.md) · [technical](areas/a.technical.md) · @ `abc1234`")
OLD_GUIDE = guide().replace("## Who uses it", "## How it works").replace("## For members", "## Flows")


def completed(entry, **replacements):
    for old, new in replacements.items():
        entry = entry.replace(old, new)
    return entry


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
            "| Guide | First order · step 1", "| Guide | The journey")
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

    def test_should_report_sections_when_behind_lacks_about_section(self):
        self.write_set(behind_text=without_section(behind(), "About this document"))
        self.assert_fires("sections")

    def test_should_report_sections_when_behind_has_no_for_section(self):
        self.write_set(behind_text=behind().replace("## For members", "## Flows"))
        self.assert_fires("sections")

    def test_should_report_audience_when_behind_keeps_it_only_in_about(self):
        text = behind().replace("**Audience:** internal\n\n", "\n").replace("**Created:**", "**Audience:** internal\n**Created:**")
        self.write_set(behind_text=text)
        self.assert_fires("audience")

    def test_should_report_header_when_behind_about_lacks_created(self):
        self.write_set(behind_text=behind().replace("**Created:** 2026-08-02\n", ""))
        self.assert_fires("header")

    def test_should_report_internal_ids_when_behind_body_names_a_flow_id(self):
        self.write_set(behind_text=behind(body="Branches are in FLOW-004."))
        self.assert_fires("internal-ids")

    def test_should_report_internal_ids_when_behind_body_names_a_question(self):
        self.write_set(behind_text=behind(body="How soon is not shown (Q2)."))
        self.assert_fires("internal-ids")

    def test_should_pass_internal_ids_when_behind_ids_sit_in_about_and_first_cell(self):
        text = behind().replace("**Derived from:**", "**Models:** [FLOW-004 pricing]\n**Derived from:**")
        self.write_set(behind_text=text)
        self.assert_clean()

    def test_should_pass_flow_mirror_when_behind_leaves_a_guide_task_out(self):
        guide_text = guide(sections={"For staff": task("Cancel a member's booking")})
        self.write_set(guide_text=guide_text, technical_text=technical(index_rows=cited("Cancel a member's booking", levels=("Guide",))))
        self.assert_clean()

    def test_should_report_flow_mirror_when_behind_adds_a_task(self):
        self.write_set(behind_text=behind(sections={"For staff": task("Extra")}),
                       technical_text=technical(index_rows=cited("Extra", levels=("Behind the scenes",))))
        self.assert_fires("flow-mirror")

    def test_should_report_flow_mirror_when_behind_adds_a_section(self):
        self.write_set(behind_text=behind(sections={"What happens automatically": ""}))
        self.assert_fires("flow-mirror")

    def test_should_report_flow_mirror_when_behind_reorders_tasks(self):
        guide_text = guide(flow=FLOW + "\n\n" + task("Cancel a seat"))
        behind_text = behind(flow=task("Cancel a seat") + "\n\n" + BEHIND_FLOW)
        self.write_set(guide_text=guide_text, behind_text=behind_text,
                       technical_text=technical(index_rows=cited("Cancel a seat")))
        self.assert_fires("flow-mirror")

    def test_should_report_flow_mirror_when_behind_moves_a_task_to_another_section(self):
        guide_text = guide(sections={"For staff": task("Cancel a seat")})
        behind_text = behind(flow=BEHIND_FLOW + "\n\n" + task("Cancel a seat"))
        self.write_set(guide_text=guide_text, behind_text=behind_text,
                       technical_text=technical(index_rows=cited("Cancel a seat")))
        self.assert_fires("flow-mirror")

    def test_should_report_task_unique_when_guide_repeats_a_heading(self):
        self.write_set(guide_text=guide(flow=FLOW + "\n\n" + FLOW))
        self.assert_fires("task-unique")

    def test_should_report_task_unique_when_behind_repeats_a_heading(self):
        self.write_set(behind_text=behind(flow=BEHIND_FLOW + "\n\n" + BEHIND_FLOW))
        self.assert_fires("task-unique")

    def test_should_pass_length_when_guide_is_at_the_limit(self):
        self.write_set(guide_text=guide(sections={"Good to know": prose(2400)}))
        self.assert_clean()

    def test_should_report_length_when_guide_is_over_the_limit(self):
        self.write_set(guide_text=guide(sections={"Good to know": words(2500)}))
        self.assert_fires("length")

    def test_should_report_length_when_behind_is_over_the_limit(self):
        self.write_set(behind_text=behind(body=words(3000)))
        self.assert_fires("length")

    def test_should_not_count_about_fences_or_table_pipes_when_measuring_length(self):
        fenced = "```text\n" + words(3000) + "\n```"
        about_words = words(3000)
        text = guide(sections={"Good to know": fenced}).replace("**Audience:**", about_words + "\n**Audience:**")
        self.write_set(guide_text=text)
        self.assert_clean()

    def test_should_count_table_cells_when_measuring_length(self):
        row = "| " + " | ".join(["cell"] * 10) + " |"
        table = "| a | b |\n|---|---|\n" + "\n".join([row] * 250)
        self.write_set(guide_text=guide(sections={"Rules and limits": table}))
        self.assert_fires("length")

    def test_should_report_length_when_level_3_is_over_the_limit(self):
        self.write_set(technical_text=technical(extra="\n\n" + words(4100)))
        self.assert_fires("length")

    def test_should_not_count_the_evidence_index_when_measuring_level_3(self):
        rows = OBSERVED_ROWS + [f"| Guide | Booking a seat | {words(5)} | see **R1** | `#observed` |"] * 800
        self.write_set(technical_text=technical(index_rows=rows))
        self.assert_clean()

    def test_should_measure_each_level_3_topic_sibling_on_its_own(self):
        self.write_set()
        (self.folder / "a.technical.moves.md").write_text(
            f"# Area — Technical reference: moves\n\n{LEVELS}\n\n## Data\n\n{words(4100)}\n", encoding="utf-8")
        self.assert_fires("length")

    def test_should_pass_limits_when_a_task_is_at_every_limit(self):
        flow = limited_task(steps=7, outcomes=5, alerts=1)
        self.write_set(guide_text=guide(flow=flow))
        self.assert_clean()

    def test_should_warn_limits_when_a_task_has_eight_steps(self):
        self.write_set(guide_text=guide(flow=limited_task(steps=8, outcomes=1, alerts=0)))
        self.assert_fires("limits", "WARN")

    def test_should_warn_limits_when_a_task_has_six_outcomes(self):
        self.write_set(guide_text=guide(flow=limited_task(steps=1, outcomes=6, alerts=0)))
        self.assert_fires("limits", "WARN")

    def test_should_warn_limits_when_a_task_has_two_alerts(self):
        self.write_set(guide_text=guide(flow=limited_task(steps=1, outcomes=1, alerts=2)))
        self.assert_fires("limits", "WARN")

    def test_should_warn_limits_when_there_are_seven_key_ideas(self):
        ideas = "\n".join(f"- **Term{chr(97 + i)}** — one line" for i in range(7))
        self.write_set(guide_text=guide(sections={"How it fits together": ideas}))
        self.assert_fires("limits", "WARN")

    def test_should_pass_limits_when_there_are_six_key_ideas_and_entries(self):
        ideas = "\n".join(f"- **Term{chr(97 + i)}** — one line" for i in range(6))
        entries = "\n\n".join(f"### Question {chr(97 + i)}?\n\nYes." for i in range(6))
        self.write_set(guide_text=guide(sections={"How it fits together": ideas, "Good to know": entries}))
        self.assert_clean()

    def test_should_warn_limits_when_there_are_seven_good_to_know_entries(self):
        entries = "\n\n".join(f"### Question {chr(97 + i)}?\n\nYes." for i in range(7))
        self.write_set(guide_text=guide(sections={"Good to know": entries}))
        self.assert_fires("limits", "WARN")

    def test_should_pass_long_sentence_when_a_sentence_has_thirty_words(self):
        self.write_set(guide_text=guide(body=sentence(30)))
        self.assert_clean()

    def test_should_warn_long_sentence_when_a_sentence_has_thirty_one_words(self):
        self.write_set(guide_text=guide(body=sentence(31)))
        self.assert_fires("long-sentence", "WARN")

    def test_should_warn_long_sentence_when_the_sentence_wraps_over_two_lines(self):
        self.write_set(guide_text=guide(body=sentence(16) + "\n" + sentence(16).lower().rstrip(".") + "."))
        self.assert_fires("long-sentence", "WARN")

    def test_should_treat_each_list_item_as_its_own_sentence(self):
        self.write_set(guide_text=guide(sections={"Good to know": f"- {sentence(20)}\n- {sentence(20)}"}))
        self.assert_clean()

    def test_should_split_sentences_when_a_line_holds_two(self):
        self.write_set(guide_text=guide(body=sentence(20) + " " + sentence(20)))
        self.assert_clean()

    def test_should_skip_long_sentence_when_in_a_table_formula_or_fence(self):
        table = f"| a | b |\n|---|---|\n| {sentence(40)} | x |"
        formula = "Credit cost = " + " ".join(["tier"] * 40)
        fence = "```text\n" + sentence(40) + "\n```"
        self.write_set(guide_text=guide(sections={"Rules and limits": table, "Good to know": formula + "\n\n" + fence}))
        code, out = self.run_dir()
        self.assertNotIn("long-sentence", out)

    def test_should_pass_labels_when_where_line_and_steps_use_vocabulary_labels(self):
        flow = "### Cancel an order\n\n**Where:** **Your orders** → **Cancel order**\n\n1. Press **Cancel order**."
        vocabulary = "| Your orders | `x` |\n| Cancel order | `y` |"
        self.write_set(guide_text=guide(flow=flow), behind_text=behind(flow=task("Cancel an order")),
                       technical_text=technical(vocabulary=vocabulary, index_rows=cited("Cancel an order")))
        self.assert_clean()

    def test_should_match_a_label_as_a_phrase_when_it_ends_in_punctuation(self):
        flow = "### Set a rate\n\n1. Set **Overage rate (per credit)**."
        vocabulary = "| Overage rate (per credit) | `x` |"
        self.write_set(guide_text=guide(flow=flow), behind_text=behind(flow=task("Set a rate")),
                       technical_text=technical(vocabulary=vocabulary, index_rows=cited("Set a rate")))
        self.assert_clean()

    def test_should_report_labels_when_where_line_names_an_unknown_label(self):
        flow = "### Cancel an order\n\n**Where:** **Your orders**\n\n1. Open it."
        self.write_set(guide_text=guide(flow=flow), technical_text=technical(index_rows=cited("Cancel an order")))
        self.assert_fires("labels")

    def test_should_report_labels_when_a_step_names_an_unknown_label(self):
        flow = "### Cancel an order\n\n1. Press **Cancel order**."
        self.write_set(guide_text=guide(flow=flow), technical_text=technical(index_rows=cited("Cancel an order")))
        self.assert_fires("labels")

    def test_should_not_read_bold_in_outcomes_or_automatic_work_as_labels(self):
        flow = FLOW.replace("- Credits are spent.", "- You see **Booked**.")
        automatic = "### Monthly posting\n\n**Trigger:** monthly.\n\n1. Post **Charge**.\n\n**Result:** done."
        self.write_set(guide_text=guide(flow=flow, sections={"What happens automatically": automatic}),
                       technical_text=technical(index_rows=cited("Monthly posting", levels=("Guide",))))
        code, out = self.run_dir()
        self.assertNotIn(" labels ", out)

    def test_should_pass_diagram_when_one_quoted_flowchart_is_drawn(self):
        body = "```mermaid\nflowchart LR\n  a[\"Member\"] -- \"books\" --> b[(\"Ledger\")]\n```"
        self.write_set(guide_text=guide(sections={"How it fits together": body}))
        self.assert_clean()

    def test_should_report_diagram_when_two_diagrams_are_drawn(self):
        fence = "```mermaid\nstateDiagram-v2\n  [*] --> a: Book\n```"
        self.write_set(guide_text=guide(sections={"How it fits together": fence + "\n\n" + fence}))
        self.assert_fires("diagram")

    def test_should_report_diagram_when_the_type_is_not_allowed(self):
        body = "```mermaid\nsequenceDiagram\n  a->>b: Book\n```"
        self.write_set(guide_text=guide(sections={"How it fits together": body}))
        self.assert_fires("diagram")

    def test_should_report_diagram_when_a_flowchart_label_is_not_quoted(self):
        body = "```mermaid\nflowchart LR\n  a[Member] --> b[\"Ledger\"]\n```"
        self.write_set(guide_text=guide(sections={"How it fits together": body}))
        self.assert_fires("diagram")

    def test_should_not_limit_behind_to_the_guide_diagram_rules_when_it_draws_a_flowchart_with_bare_labels(self):
        body = "```mermaid\nflowchart LR\n  S[Scheduling] -- \"cancels\" --> B[Booking]\n```"
        self.write_set(behind_text=behind(body=body))
        self.assert_clean()

    def test_should_warn_guarantee_words_when_a_line_starts_not_yet(self):
        self.write_set(guide_text=guide(sections={"Good to know": "Not yet."}))
        self.assert_fires("guarantee-words", "WARN")

    def test_should_warn_guarantee_words_when_a_list_item_starts_not_yet(self):
        self.write_set(guide_text=guide(sections={"Good to know": "- Not yet — planned."}))
        self.assert_fires("guarantee-words", "WARN")

    def test_should_warn_guarantee_words_when_coming_soon(self):
        self.write_set(behind_text=behind(body="Roll-over is coming soon."))
        self.assert_fires("guarantee-words", "WARN")

    def test_should_warn_guarantee_words_when_not_yet_available(self):
        self.write_set(guide_text=guide(body="Roll-over is not yet available."))
        self.assert_fires("guarantee-words", "WARN")

    def test_should_warn_guarantee_words_when_in_a_future_release(self):
        self.write_set(guide_text=guide(body="Roll-over arrives in a future release."))
        self.assert_fires("guarantee-words", "WARN")

    def test_should_pass_guarantee_words_when_not_yet_describes_a_state(self):
        self.write_set(guide_text=guide(body="An order that has not yet shipped can be cancelled."))
        self.assert_clean()

    def write_kb(self, index_lines, guide_text=None, folder="areas"):
        target = self.folder / folder
        target.mkdir(exist_ok=True)
        self.write({f"{folder}/a.md": guide_text or guide(), f"{folder}/a.behind-the-scenes.md": behind(),
                    f"{folder}/a.technical.md": technical()})
        if index_lines is not None:
            (self.folder / "INDEX.md").write_text("# Business Model\n\n## Areas\n" + "\n".join(index_lines) + "\n", encoding="utf-8")

    def test_should_report_sections_when_overview_has_no_journey(self):
        texts = overview_set()
        texts["system-overview.md"] = without_section(texts["system-overview.md"], "The journey")
        self.write(texts)
        self.assert_fires("sections")

    def test_should_report_sections_when_overview_behind_has_no_about(self):
        texts = overview_set()
        texts["system-overview.behind-the-scenes.md"] = without_section(texts["system-overview.behind-the-scenes.md"], "About this document")
        self.write(texts)
        self.assert_fires("sections")

    def test_should_warn_old_shape_once_and_run_no_other_check_when_guide_has_how_it_works(self):
        broken = OLD_GUIDE + "\n#confirmed\n"
        self.write_set(guide_text=broken, technical_text="# Not a technical file\n")
        code, out = self.run_dir()
        self.assertEqual((0, 1), (code, len(out.splitlines())), out)
        self.assertRegex(out, r"^WARN \S+a\.md:\d+ old-shape ")

    def test_should_warn_old_shape_when_the_overview_has_the_areas_table_and_no_who_uses_it(self):
        texts = overview_set()
        texts["system-overview.md"] = texts["system-overview.md"].replace("## Who uses it", "## The areas")
        self.write(texts)
        self.assert_fires("old-shape", "WARN")

    def test_should_not_warn_old_shape_when_the_guide_has_who_uses_it(self):
        self.write_set(guide_text=guide().replace("## For members", "## How it works"))
        code, out = self.run_dir()
        self.assertNotIn("old-shape", out)

    def test_should_pass_index_line_when_the_line_has_the_shape(self):
        self.write_kb([INDEX_ENTRY])
        self.assert_clean()

    def test_should_report_index_line_when_the_set_has_no_line(self):
        self.write_kb(["- [Other](areas/other.md) — AREA-009 · x"])
        self.assert_fires("index-line")

    def test_should_report_index_line_when_the_set_has_two_lines(self):
        self.write_kb([INDEX_ENTRY, INDEX_ENTRY])
        self.assert_fires("index-line")

    def test_should_report_index_line_when_the_line_is_the_old_style(self):
        self.write_kb(["- [Area](areas/a.md) — AREA-001; book sessions; actors: members · derived from code"])
        self.assert_fires("index-line")

    def test_should_pass_index_line_when_the_description_has_twenty_words(self):
        self.write_kb([completed(INDEX_ENTRY, **{"Book and cancel sessions with credits": words(20)})])
        self.assert_clean()

    def test_should_report_index_line_when_the_description_has_twenty_one_words(self):
        self.write_kb([completed(INDEX_ENTRY, **{"Book and cancel sessions with credits": words(21)})])
        self.assert_fires("index-line")

    def test_should_report_index_line_when_a_link_does_not_resolve(self):
        self.write_kb([completed(INDEX_ENTRY, **{"areas/a.technical.md)": "areas/gone.technical.md)"})])
        self.assert_fires("index-line")

    def test_should_not_check_index_line_when_the_set_is_old_shape(self):
        self.write_kb(["- [Area](areas/a.md) — AREA-001; old style line"], guide_text=OLD_GUIDE)
        code, out = self.run_dir()
        self.assertEqual((0, 1), (code, out.count("old-shape")), out)
        self.assertNotIn("index-line", out)

    def test_should_not_check_index_line_when_there_is_no_index(self):
        self.write_kb(None)
        self.assert_clean()

    def test_should_not_check_index_line_when_the_set_is_not_under_areas(self):
        self.write_kb(["- [Other](areas/other.md) — x"], folder="features")
        self.assert_clean()

    def test_should_report_only_set_complete_when_a_set_is_incomplete_and_an_index_exists(self):
        self.write_kb([INDEX_ENTRY])
        (self.folder / "areas" / "a.technical.md").unlink()
        code, out = self.run_dir()
        self.assertNotIn("index-line", out)
        self.assertIn("set-complete", out)

    def test_should_read_a_number_and_a_quoted_message_as_facts(self):
        text = "You pay £6.00 for 24 hours.\nThe screen says “Seat taken” or \"Try later\".\n"
        self.assertEqual(
            [(1, "number", "6.00"), (1, "number", "24"), (2, "message", "Seat taken"), (2, "message", "Try later")],
            doc_lint.fact_lines(text))

    def test_should_not_read_ids_list_numbers_link_targets_or_header_lines_as_facts(self):
        text = ("**Created:** 2026-08-02\n**Id:** AREA-004\n1. See [FLOW-110](flows/f-2.md) and Q12.\n"
                "2. Open the page.\n")
        self.assertEqual([], doc_lint.fact_lines(text))

    def test_should_report_a_lost_number_when_the_new_text_does_not_hold_it(self):
        self.assertEqual([("Guide", 1, "number", "24")], doc_lint.lost_facts([("Guide", "Cut-off is 24 hours.")], "Cut-off is 12 hours."))

    def test_should_keep_a_number_when_a_reconcile_mark_holds_the_old_value(self):
        self.assertEqual([], doc_lint.lost_facts([("Guide", "Cut-off is 24 hours.")], "Cut-off is ~~24~~ → 12 hours."))

    def test_should_keep_a_number_when_it_moved_to_another_level(self):
        self.assertEqual([], doc_lint.lost_facts([("Guide", "Cut-off is 24 hours.")], "Guide.\nThe rule: 24 h."))

    def test_should_not_count_an_id_as_a_fact_when_the_new_text_drops_it(self):
        self.assertEqual([], doc_lint.lost_facts([("Guide", "See AREA-004 and Q7.")], "See the area."))

    def test_should_report_a_lost_message_when_the_new_text_words_it_differently(self):
        old = [("Behind the scenes", "It says “This order was accepted.”")]
        self.assertEqual([("Behind the scenes", 1, "message", "This order was accepted.")], doc_lint.lost_facts(old, "It says “Order accepted.”"))

    def test_should_keep_a_message_when_the_quotes_or_line_breaks_differ(self):
        old = [("Guide", "It says “Seat\ntaken”.")]
        self.assertEqual([], doc_lint.lost_facts(old, "It says \"Seat taken\"."))

    def test_should_report_a_lost_fact_once_when_two_levels_held_it(self):
        old = [("Guide", "Limit 5."), ("Behind the scenes", "Limit 5.")]
        self.assertEqual([("Guide", 1, "number", "5")], doc_lint.lost_facts(old, "Limit is high."))

    def test_should_read_the_old_file_through_git_show_beside_its_path(self):
        done = mock.Mock(returncode=0, stdout="old text")
        with mock.patch.object(doc_lint.subprocess, "run", return_value=done) as run:
            self.assertEqual("old text", doc_lint.git_show("abc123", Path("docs/areas/a.md")))
        self.assertEqual(["git", "-C", "docs/areas", "show", "abc123:./a.md"], run.call_args.args[0])

    def test_should_read_nothing_when_the_revision_has_no_such_file(self):
        with mock.patch.object(doc_lint.subprocess, "run", return_value=mock.Mock(returncode=128, stdout="")):
            self.assertIsNone(doc_lint.git_show("abc123", Path("a.md")))

    def test_should_say_whether_a_revision_exists(self):
        with mock.patch.object(doc_lint.subprocess, "run", return_value=mock.Mock(returncode=0)):
            self.assertTrue(doc_lint.revision_exists("abc123", Path(".")))
        with mock.patch.object(doc_lint.subprocess, "run", return_value=mock.Mock(returncode=1)):
            self.assertFalse(doc_lint.revision_exists("nope", Path(".")))

    def test_should_warn_fact_kept_when_the_old_guide_held_a_number_the_set_lost(self):
        self.write_set()
        old = {"a.md": "Credits expire after 99 days.", "a.behind-the-scenes.md": None}
        with mock.patch.object(doc_lint, "revision_exists", return_value=True), \
                mock.patch.object(doc_lint, "git_show", side_effect=lambda rev, path: old[path.name]):
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                code = doc_lint.main(["--dir", str(self.folder), "--kept-from", "abc123"])
        self.assertEqual(0, code)
        self.assertRegex(out.getvalue(), r"(?m)^WARN \S+a\.md:1 fact-kept number '99' from abc123 ")

    def test_should_print_no_fact_kept_when_the_set_kept_every_fact(self):
        self.write_set()
        with mock.patch.object(doc_lint, "revision_exists", return_value=True), \
                mock.patch.object(doc_lint, "git_show", side_effect=lambda rev, path: path.read_text(encoding="utf-8")):
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                code = doc_lint.main(["--dir", str(self.folder), "--kept-from", "abc123"])
        self.assertEqual((0, ""), (code, out.getvalue()))

    def test_should_check_fact_kept_on_an_explicit_set_when_kept_from_is_given(self):
        self.write_set()
        paths = [str(self.folder / n) for n in ("a.md", "a.behind-the-scenes.md", "a.technical.md")]
        with mock.patch.object(doc_lint, "revision_exists", return_value=True), \
                mock.patch.object(doc_lint, "git_show", return_value="Roll-over after 77 days."):
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                doc_lint.main(paths + ["--kept-from", "abc123"])
        self.assertEqual(1, out.getvalue().count("fact-kept number '77'"), out.getvalue())

    def test_should_exit_with_usage_when_the_kept_from_revision_does_not_exist(self):
        self.write_set()
        with mock.patch.object(doc_lint, "revision_exists", return_value=False), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            doc_lint.main(["--dir", str(self.folder), "--kept-from", "nope"])
        self.assertEqual(2, raised.exception.code)

    def test_should_exit_with_usage_when_two_files_given(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            doc_lint.main(["a.md", "b.md"])
        self.assertEqual(2, raised.exception.code)


if __name__ == "__main__":
    unittest.main()
