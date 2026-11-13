#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "markdown-it-py==4.3.0",
#   "mdit-py-plugins==0.7.0",
# ]
# ///
"""Render a documentation guide as one standalone HTML page a client can be sent.

Usage:
  render-html.py --out <dir> <file.md>...   render the named files, whatever their level
  render-html.py --out <dir> --dir <folder> render every file under <folder> whose Audience is shareable
                                            (the Level 1 guides and system-overview.md)

One <name>.html per input, written to --out; nothing is written anywhere else and nothing is committed.
The page carries inline CSS and makes one request: the pinned, integrity-checked Mermaid script, and only
when the guide holds a diagram. Without it the reader sees a one-line notice instead of the diagram.

A client's page carries nothing internal: "## About this document" shrinks to "Last updated <date>", a
reconcile mark "~~old~~ -> new" shows only "new", links to Level 2 and Level 3 files and to anything that is
not a guide show their text, and a file whose Audience is internal says so under its title.
"""

import argparse
import html
import re
import sys
from pathlib import Path
from string import Template

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.anchors import anchors_plugin

MERMAID_VERSION = "11.17.2"
MERMAID_URL = f"https://cdn.jsdelivr.net/npm/mermaid@{MERMAID_VERSION}/dist/mermaid.min.js"
MERMAID_INTEGRITY = "sha384-EOXBFmc3gx5mb+vn0vPvvGqACToJD24hhacX5Yx+8NUUQrHIle/Qi5Bg9o3zKwW2"
NO_DIAGRAM_NOTICE = "This diagram needs an internet connection"

ABOUT_HEADING = re.compile(r"^## About this document\s*$", re.MULTILINE)
NEXT_H2 = re.compile(r"^## ", re.MULTILINE)
LAST_UPDATED = re.compile(r"^\*\*Last updated:\*\*\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE)
CREATED = re.compile(r"^\*\*Created:\*\*\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE)
INTERNAL = re.compile(r"^\*\*Audience:\*\*\s*internal\b", re.MULTILINE)
SHAREABLE = re.compile(r"^\*\*Audience:\*\*\s*shareable\b", re.MULTILINE)
DROPPED_HEADER_LINES = re.compile(r"^\*\*(Levels|Audience):\*\*.*\n?", re.MULTILINE)
RECONCILE_MARK = re.compile(r"~~[^~\n]+~~\s*→\s*")
ALERT = re.compile(r"^\[!(NOTE|TIP|IMPORTANT|WARNING)\][ \t]*\n?")
KEPT_LINK = re.compile(r"^(https?:|mailto:|#)")
INTERNAL_LEVEL = re.compile(r"\.(behind-the-scenes|technical)(\.[^/]*)?\.md$")

CSS = """
:root{--bg:#fff;--fg:#1f2328;--muted:#59636e;--line:#d1d9e0;--soft:#f6f8fa;--link:#0b5fff;
--note:#0969da;--tip:#1a7f37;--important:#8250df;--warning:#9a6700}
@media(prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--muted:#9198a1;--line:#3d444d;
--soft:#151b23;--link:#4493f8;--note:#4493f8;--tip:#3fb950;--important:#ab7df8;--warning:#d29922}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
main{display:grid;grid-template-columns:15rem minmax(0,46rem);gap:3rem;max-width:68rem;margin:0 auto;padding:2rem 1.25rem}
@media(max-width:60rem){main{grid-template-columns:minmax(0,1fr);gap:1rem}}
nav.toc{position:sticky;top:1rem;align-self:start;font-size:.9rem}
@media(max-width:60rem){nav.toc{position:static}}
nav.toc p{margin:0 0 .5rem;font-weight:600;color:var(--muted)}
nav.toc ul{margin:0;padding:0;list-style:none}
nav.toc li{margin:.25rem 0}
a{color:var(--link)}
h1{font-size:2rem;line-height:1.25;margin:0 0 1rem}
h2{margin-top:2.5rem;padding-bottom:.3rem;border-bottom:1px solid var(--line)}
h3{margin-top:2rem}
.header-anchor{margin-left:.4rem;text-decoration:none;color:var(--muted);visibility:hidden}
h2:hover .header-anchor,h3:hover .header-anchor{visibility:visible}
table{border-collapse:collapse;width:100%;margin:1rem 0}
th,td{border:1px solid var(--line);padding:.4rem .7rem;text-align:left;vertical-align:top}
th{background:var(--soft)}
code{background:var(--soft);padding:.1em .3em;border-radius:4px}
.alert{margin:1rem 0;padding:.5rem 1rem;border-left:.3rem solid var(--kind);background:var(--soft);border-radius:0 6px 6px 0}
.alert::before{display:block;font-weight:600;color:var(--kind)}
.alert-note{--kind:var(--note)}.alert-note::before{content:"ℹ  Note"}
.alert-tip{--kind:var(--tip)}.alert-tip::before{content:"✔  Tip"}
.alert-important{--kind:var(--important)}.alert-important::before{content:"❗  Important"}
.alert-warning{--kind:var(--warning)}.alert-warning::before{content:"⚠  Warning"}
.diagram{margin:1.5rem 0;text-align:center}
pre.mermaid{display:none;margin:0}
pre.mermaid[data-processed]{display:block}
pre.mermaid[data-processed]+.diagram-notice{display:none}
.diagram-notice{margin:0;padding:1rem;border:1px dashed var(--line);border-radius:6px;color:var(--muted)}
.internal-banner{display:inline-block;margin:0 0 1rem;padding:.2rem .7rem;border:1px solid var(--warning);
border-radius:6px;color:var(--warning);font-weight:600}
.updated{margin-top:3rem;padding-top:1rem;border-top:1px solid var(--line);color:var(--muted);font-size:.9rem}
@media print{nav.toc{display:none}main{display:block;padding:0}
table,pre.mermaid,.diagram,.alert,tr{break-inside:avoid}}
"""

MERMAID_SCRIPTS = Template("""<script src="$url" integrity="$integrity" crossorigin="anonymous"></script>
<script>if (window.mermaid) { mermaid.initialize({ startOnLoad: true, theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "default" }); }</script>
""")

PAGE = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<style>$css</style>
</head>
<body>
<main>
$toc<article>
$body$updated</article>
</main>
$scripts</body>
</html>
""")


def new_markdown() -> MarkdownIt:
    return (
        MarkdownIt("commonmark", {"html": False})
        .enable(["table", "strikethrough"])
        .use(anchors_plugin, min_level=2, max_level=3, permalink=True)
    )


def cut_about(text: str) -> tuple[str, str | None]:
    """Remove "## About this document" and return the text without it, and its date.

    The date is the Last updated line, else the Created line, else None.
    """
    heading = ABOUT_HEADING.search(text)
    if not heading:
        return text, None
    following = NEXT_H2.search(text, heading.end())
    end = following.start() if following else len(text)
    section = text[heading.start():end]
    found = LAST_UPDATED.search(section) or CREATED.search(section)
    return text[:heading.start()] + text[end:], found.group(1) if found else None


def client_source(text: str) -> tuple[str, str | None]:
    """The markdown a client may see, and the date the page closes with."""
    text, date = cut_about(text)
    text = RECONCILE_MARK.sub("", text)
    return DROPPED_HEADER_LINES.sub("", text), date


def target_of(href: str) -> str | None:
    """Where a link points on the page, or None when only its text may show."""
    if KEPT_LINK.match(href):
        return href
    path, hash_mark, fragment = href.partition("#")
    if not path.endswith(".md") or INTERNAL_LEVEL.search(path):
        return None
    return f"{Path(path).stem}.html{hash_mark}{fragment}"


def rewrite_links(tokens: list[Token]) -> None:
    for token in tokens:
        if token.type != "inline":
            continue
        kept: list[Token] = []
        text_only = False
        for child in token.children:
            if child.type == "link_open":
                target = target_of(child.attrGet("href"))
                text_only = target is None
                if text_only:
                    continue
                child.attrSet("href", target)
            elif child.type == "link_close" and text_only:
                text_only = False
                continue
            kept.append(child)
        token.children = kept


def apply_alerts(md: MarkdownIt, tokens: list[Token]) -> None:
    """Turn a blockquote that opens with [!NOTE], [!TIP], [!IMPORTANT] or [!WARNING] into a styled box.

    Any other first line leaves the blockquote as it is.
    """
    for index, token in enumerate(tokens):
        if token.type != "blockquote_open":
            continue
        first = tokens[index + 1:index + 3]
        if [t.type for t in first] != ["paragraph_open", "inline"]:
            continue
        marker = ALERT.match(first[1].content)
        if not marker:
            continue
        rest = first[1].content[marker.end():]
        first[1].content = rest
        first[1].children = md.parseInline(rest)[0].children
        token.tag = "div"
        token.attrSet("class", f"alert alert-{marker.group(1).lower()}")
        token.attrSet("role", "note")
        closing = next(t for t in tokens[index:] if t.type == "blockquote_close" and t.level == token.level)
        closing.tag = "div"


def apply_diagrams(tokens: list[Token]) -> bool:
    found = False
    for token in tokens:
        if token.type == "fence" and token.info.strip() == "mermaid":
            token.type = "html_block"
            token.content = (
                f'<div class="diagram"><pre class="mermaid">{html.escape(token.content)}</pre>'
                f'<p class="diagram-notice">{NO_DIAGRAM_NOTICE}</p></div>\n'
            )
            found = True
    return found


def add_internal_banner(tokens: list[Token]) -> None:
    after_title = next(
        (i + 1 for i, t in enumerate(tokens) if t.type == "heading_close" and t.tag == "h1"), 0
    )
    banner = Token("html_block", "", 0)
    banner.content = '<p class="internal-banner">Internal — not for sharing</p>\n'
    tokens.insert(after_title, banner)


def headings(tokens: list[Token], tag: str) -> list[tuple[str, str]]:
    return [
        (token.attrGet("id") or "", tokens[i + 1].content)
        for i, token in enumerate(tokens)
        if token.type == "heading_open" and token.tag == tag
    ]


def toc_html(entries: list[tuple[str, str]]) -> str:
    if not entries:
        return ""
    items = "\n".join(
        f'<li><a href="#{html.escape(anchor)}">{html.escape(text)}</a></li>' for anchor, text in entries
    )
    return f'<nav class="toc" aria-label="Contents"><p>Contents</p><ul>\n{items}\n</ul></nav>\n'


def render_page(source: str, fallback_title: str) -> str:
    internal = bool(INTERNAL.search(source))
    markdown, date = client_source(source)
    md = new_markdown()
    tokens = md.parse(markdown)
    rewrite_links(tokens)
    apply_alerts(md, tokens)
    has_diagram = apply_diagrams(tokens)
    titles = headings(tokens, "h1")
    toc = toc_html(headings(tokens, "h2"))
    if internal:
        add_internal_banner(tokens)
    return PAGE.substitute(
        title=html.escape(titles[0][1] if titles else fallback_title),
        css=CSS,
        toc=toc,
        body=md.renderer.render(tokens, md.options, {}),
        updated=f'<p class="updated">Last updated {html.escape(date)}</p>\n' if date else "",
        scripts=MERMAID_SCRIPTS.substitute(url=MERMAID_URL, integrity=MERMAID_INTEGRITY) if has_diagram else "",
    )


def shareable_files(folder: Path) -> list[Path]:
    return [
        path for path in sorted(folder.rglob("*.md"))
        if SHAREABLE.search(path.read_text(encoding="utf-8"))
    ]


def parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render documentation guides as standalone HTML pages.")
    parser.add_argument("--out", type=Path, required=True, help="folder the pages are written to")
    parser.add_argument("--dir", type=Path, help="render every shareable guide under this folder")
    parser.add_argument("files", nargs="*", type=Path, help="markdown files to render as given")
    arguments = parser.parse_args(argv)
    if arguments.dir and not arguments.dir.is_dir():
        parser.error(f"--dir {arguments.dir} is not a folder")
    if not arguments.dir and not arguments.files:
        parser.error("name a file or pass --dir")
    return arguments


def main(argv: list[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    inputs = (shareable_files(arguments.dir) if arguments.dir else []) + arguments.files
    arguments.out.mkdir(parents=True, exist_ok=True)
    for path in inputs:
        target = arguments.out / f"{path.stem}.html"
        target.write_text(render_page(path.read_text(encoding="utf-8"), path.stem), encoding="utf-8")
        print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
