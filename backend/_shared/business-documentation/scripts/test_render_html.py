import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFERENCES = HERE.parent / "references"
SPEC = importlib.util.spec_from_file_location("render_html", HERE / "render-html.py")
render_html = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_html)

MERMAID_FENCE = "```mermaid\nstateDiagram-v2\n  [*] --> a: Book <now>\n```\n"


def page(markdown: str, name: str = "guide") -> str:
    return render_html.render_page(markdown, name)


def run_main(*argv: str) -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = render_html.main(list(argv))
    return code, output.getvalue()


class AlertTests(unittest.TestCase):
    def test_Should_StyleEachKnownKind_When_BlockquoteOpensWithMarker(self):
        for kind in ("note", "tip", "important", "warning"):
            with self.subTest(kind=kind):
                html = page(f"# T\n\n> [!{kind.upper()}]\n> Mind **this**.\n")
                self.assertIn(f'<div class="alert alert-{kind}" role="note">', html)
                self.assertIn("<strong>this</strong>", html)
                self.assertNotIn(f"[!{kind.upper()}]", html)
                self.assertNotIn("<blockquote", html)

    def test_Should_CloseTheBoxWithADiv_When_AlertHasTwoParagraphs(self):
        html = page("# T\n\n> [!NOTE]\n> First.\n>\n> Second.\n\nAfter.\n")
        self.assertIn("<p>Second.</p>\n</div>", html)

    def test_Should_KeepPlainBlockquote_When_KindIsUnknown(self):
        html = page("# T\n\n> [!CAUTION]\n> Careful.\n")
        self.assertIn("<blockquote>", html)
        self.assertNotIn("alert-", html.split("</style>")[1])

    def test_Should_KeepPlainBlockquote_When_ItIsOrdinaryText(self):
        html = page("# T\n\n> Just a quote.\n")
        self.assertIn("<blockquote>", html)

    def test_Should_KeepPlainBlockquote_When_ItIsEmpty(self):
        html = page("# T\n\n>\n")
        self.assertIn("<blockquote>", html)

    def test_Should_KeepPlainBlockquote_When_ItOpensWithAList(self):
        html = page("# T\n\n> - one\n> - two\n")
        self.assertIn("<blockquote>", html)


class DiagramTests(unittest.TestCase):
    def test_Should_WrapFenceInPreMermaid_When_GuideHasADiagram(self):
        html = page(f"# T\n\n{MERMAID_FENCE}")
        self.assertIn('<pre class="mermaid">stateDiagram-v2\n  [*] --&gt; a: Book &lt;now&gt;\n</pre>', html)

    def test_Should_ShowOneLineNoticeBesideTheDiagram_When_GuideHasADiagram(self):
        html = page(f"# T\n\n{MERMAID_FENCE}")
        self.assertIn(f'<p class="diagram-notice">{render_html.NO_DIAGRAM_NOTICE}</p>', html)

    def test_Should_LoadPinnedMermaidWithIntegrity_When_GuideHasADiagram(self):
        html = page(f"# T\n\n{MERMAID_FENCE}")
        self.assertIn(
            f'<script src="https://cdn.jsdelivr.net/npm/mermaid@{render_html.MERMAID_VERSION}/dist/mermaid.min.js" '
            f'integrity="{render_html.MERMAID_INTEGRITY}" crossorigin="anonymous"></script>',
            html,
        )

    def test_Should_MakeNoRequest_When_GuideHasNoDiagram(self):
        html = page("# T\n\nText only.\n")
        self.assertNotIn("<script", html)

    def test_Should_LeaveOtherFencesAlone_When_LanguageIsNotMermaid(self):
        html = page("# T\n\n```text\nplain\n```\n")
        self.assertIn("<pre><code", html)
        self.assertNotIn("<script", html)

    def test_Should_HideUnprocessedDiagramSource_When_MermaidDidNotRun(self):
        self.assertIn("pre.mermaid{display:none", render_html.CSS)


class LinkTests(unittest.TestCase):
    def test_Should_PointToHtml_When_LinkTargetsAGuide(self):
        html = page("# T\n\nSee [Bookings](bookings.md) and [Plans](../areas/plans.md#rules).\n")
        self.assertIn('<a href="bookings.html">Bookings</a>', html)
        self.assertIn('<a href="plans.html#rules">Plans</a>', html)

    def test_Should_ShowOnlyText_When_LinkTargetsLevel2OrLevel3(self):
        for target in ("a.behind-the-scenes.md", "a.technical.md", "a.technical.rules.md#x"):
            with self.subTest(target=target):
                html = page(f"# T\n\nRead [the details]({target}) now.\n")
                self.assertIn("Read the details now.", html)
                self.assertNotIn(target, html)

    def test_Should_ShowOnlyText_When_RelativeLinkIsNotAGuide(self):
        html = page("# T\n\nSee [the diagram](../img/flow.png).\n")
        self.assertIn("See the diagram.", html)
        self.assertNotIn("flow.png", html)

    def test_Should_KeepLink_When_ItIsHttpsOrInPage(self):
        html = page("# T\n\n[Out](https://example.com/x) and [in](#rules) and [mail](mailto:a@b.co).\n")
        self.assertIn('<a href="https://example.com/x">Out</a>', html)
        self.assertIn('<a href="#rules">in</a>', html)
        self.assertIn('<a href="mailto:a@b.co">mail</a>', html)

    def test_Should_RewriteLinksInsideTables_When_CellHoldsALink(self):
        html = page("# T\n\n| A |\n|---|\n| [x](x.md) · [y](y.technical.md) |\n")
        self.assertIn('<td><a href="x.html">x</a> · y</td>', html)


class ClientPageTests(unittest.TestCase):
    ABOUT = (
        "## About this document\n\n**Id:** AREA-004\n**Created:** 2026-08-02\n**Last updated:** 2026-10-15\n"
        "**Derived from:** code by `be-documenter` @ `a3f9c21` on 2026-08-02\n"
        "**Audience:** shareable\n**Models:** [FLOW-004 pricing a booking]\n"
    )

    def test_Should_CloseWithLastUpdatedDate_When_AboutHasLastUpdated(self):
        html = page(f"# T\n\nBody.\n\n{self.ABOUT}")
        self.assertIn('<p class="updated">Last updated 2026-10-15</p>', html)

    def test_Should_FallBackToCreated_When_AboutHasNoLastUpdated(self):
        about = self.ABOUT.replace("**Last updated:** 2026-10-15\n", "")
        html = page(f"# T\n\nBody.\n\n{about}")
        self.assertIn("Last updated 2026-08-02", html)

    def test_Should_CloseWithNoLine_When_AboutHasNoDate(self):
        html = page("# T\n\nBody.\n\n## About this document\n\n**Id:** AREA-004\n")
        self.assertNotIn("Last updated", html.split("</style>")[1])

    def test_Should_RenderNothingInternal_When_AboutHoldsIdShaAndModels(self):
        html = page(f"# T\n\nBody.\n\n{self.ABOUT}")
        for internal in ("AREA-004", "a3f9c21", "FLOW-004", "be-documenter", "About this document"):
            with self.subTest(internal=internal):
                self.assertNotIn(internal, html)

    def test_Should_KeepSectionsAfterAbout_When_AboutIsNotLast(self):
        html = page("# T\n\n## About this document\n\n**Created:** 2026-08-02\n\n## Later\n\nKept.\n")
        self.assertIn("Kept.", html)

    def test_Should_KeepOnlyTheNewValue_When_TextHasAReconcileMark(self):
        html = page("# T\n\nThe cut-off is ~~12 hours~~ → 24 hours before.\n")
        self.assertIn("The cut-off is 24 hours before.", html)
        self.assertNotIn("12 hours", html)

    def test_Should_KeepStrikethrough_When_NoArrowFollows(self):
        html = page("# T\n\nA ~~lone~~ mark.\n")
        self.assertIn("<s>lone</s>", html)

    def test_Should_DropLevelsAndAudienceLines_When_TheyOpenTheFile(self):
        html = page("# T\n\n**Levels:** [Guide](a.md) · [Technical](a.technical.md)\n\n**Audience:** shareable\n\nBody.\n")
        body = html.split("<article>")[1]
        self.assertNotIn("Levels", body)
        self.assertNotIn("Audience", body)

    def test_Should_SayInternalUnderTheTitle_When_AudienceIsInternal(self):
        html = page("# Behind\n\n**Levels:** [Guide](a.md)\n\n**Audience:** internal\n\nBody.\n")
        self.assertIn("</h1>\n<p class=\"internal-banner\">Internal — not for sharing</p>", html)

    def test_Should_NotSayInternal_When_AudienceIsShareable(self):
        html = page("# T\n\n**Audience:** shareable\n\nBody.\n")
        self.assertNotIn('class="internal-banner"', html.split("</style>")[1])

    def test_Should_PutBannerFirst_When_InternalFileHasNoTitle(self):
        html = page("**Audience:** internal\n\nBody.\n")
        self.assertIn('<article>\n<p class="internal-banner">', html)


class PageStructureTests(unittest.TestCase):
    def test_Should_ListEverySecondLevelHeading_When_GuideHasSections(self):
        html = page("# T\n\n## One\n\n### Sub\n\n## Two\n")
        self.assertIn('<nav class="toc"', html)
        self.assertIn('<li><a href="#one">One</a></li>', html)
        self.assertIn('<li><a href="#two">Two</a></li>', html)
        self.assertNotIn('<li><a href="#sub">', html)

    def test_Should_AnchorHeadings_When_GuideHasSections(self):
        html = page("# T\n\n## One\n\n### Sub\n")
        self.assertIn('<h2 id="one">', html)
        self.assertIn('<h3 id="sub">', html)

    def test_Should_OmitContents_When_GuideHasNoSections(self):
        html = page("# T\n\nText.\n")
        self.assertNotIn("<nav", html)

    def test_Should_RenderTables_When_GuideHasAPipeTable(self):
        html = page("# T\n\n| A | B |\n|---|---|\n| 1 | 2 |\n")
        self.assertIn("<th>A</th>", html)
        self.assertIn("<td>2</td>", html)

    def test_Should_TitleThePage_When_GuideHasAnH1(self):
        self.assertIn("<title>Session &amp; credits</title>", page("# Session & credits\n"))

    def test_Should_TitleFromFileName_When_GuideHasNoH1(self):
        self.assertIn("<title>credits</title>", page("Text.\n", "credits"))

    def test_Should_NotPassRawHtmlThrough_When_GuideHoldsAScriptTag(self):
        html = page("# T\n\n<script>alert(1)</script>\n")
        self.assertNotIn("<script>alert", html)

    def test_Should_RenderTheWholeGoldenExample_When_ItIsTheInput(self):
        source = (REFERENCES / "example-area.md").read_text(encoding="utf-8")
        html = page(source, "example-area")
        self.assertIn('class="alert alert-important"', html)
        self.assertIn('class="alert alert-warning"', html)
        self.assertIn('<pre class="mermaid">', html)
        self.assertIn("Last updated 2026-08-02", html)
        for internal in ("AREA-004", "a3f9c21", "FLOW-004", "credits-and-charges.technical.md"):
            with self.subTest(internal=internal):
                self.assertNotIn(internal, html)


class MainTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.source = self.root / "kb"
        (self.source / "areas").mkdir(parents=True)
        self.out = self.root / "out"

    def write(self, relative: str, text: str) -> Path:
        path = self.source / relative
        path.write_text(text, encoding="utf-8")
        return path

    def test_Should_RenderOnlyShareableGuides_When_DirIsGiven(self):
        self.write("areas/credits.md", "# Credits\n\n**Audience:** shareable\n")
        self.write("areas/credits.technical.md", "# Tech\n\n**Audience:** internal\n")
        self.write("INDEX.md", "# Index\n")
        code, printed = run_main("--out", str(self.out), "--dir", str(self.source))
        self.assertEqual(0, code)
        self.assertEqual(["credits.html"], sorted(p.name for p in self.out.iterdir()))
        self.assertEqual(str(self.out / "credits.html"), printed.strip())

    def test_Should_RenderAFileAsGiven_When_ItIsNamedWhateverItsAudience(self):
        level2 = self.write("areas/credits.behind-the-scenes.md", "# Behind\n\n**Audience:** internal\n")
        code, _ = run_main("--out", str(self.out), str(level2))
        self.assertEqual(0, code)
        html = (self.out / "credits.behind-the-scenes.html").read_text(encoding="utf-8")
        self.assertIn("Internal — not for sharing", html)

    def test_Should_RenderDirAndNamedFilesTogether_When_BothAreGiven(self):
        self.write("areas/a.md", "# A\n\n**Audience:** shareable\n")
        named = self.write("areas/b.md", "# B\n")
        run_main("--out", str(self.out), "--dir", str(self.source), str(named))
        self.assertEqual(["a.html", "b.html"], sorted(p.name for p in self.out.iterdir()))

    def test_Should_CreateOutFolder_When_ItDoesNotExist(self):
        named = self.write("a.md", "# A\n")
        nested = self.out / "deeper" / "still"
        run_main("--out", str(nested), str(named))
        self.assertTrue((nested / "a.html").is_file())

    def test_Should_ExitWithUsageError_When_OutIsMissing(self):
        with contextlib.redirect_stderr(io.StringIO()) as errors, self.assertRaises(SystemExit) as raised:
            render_html.main(["--dir", str(self.source)])
        self.assertEqual(2, raised.exception.code)
        self.assertIn("--out", errors.getvalue())

    def test_Should_ExitWithUsageError_When_NothingIsToRender(self):
        with contextlib.redirect_stderr(io.StringIO()) as errors, self.assertRaises(SystemExit) as raised:
            render_html.main(["--out", str(self.out)])
        self.assertEqual(2, raised.exception.code)
        self.assertIn("name a file or pass --dir", errors.getvalue())

    def test_Should_ExitWithUsageError_When_DirIsNotAFolder(self):
        with contextlib.redirect_stderr(io.StringIO()) as errors, self.assertRaises(SystemExit) as raised:
            render_html.main(["--out", str(self.out), "--dir", str(self.root / "missing")])
        self.assertEqual(2, raised.exception.code)
        self.assertIn("is not a folder", errors.getvalue())

    def test_Should_RenderTheFeatureGuideForm_When_OneLevel1FileIsNamed(self):
        feature = self.write("003-booking.md", "# Booking\n\n**Audience:** shareable\n\nSee [Plans](plans.md).\n")
        code, _ = run_main("--out", str(self.out), str(feature))
        self.assertEqual(0, code)
        self.assertIn('<a href="plans.html">Plans</a>', (self.out / "003-booking.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
