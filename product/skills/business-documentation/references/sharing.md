# Sharing a guide — rendering

Loaded by `SKILL.md` when a guide or delivery note is to be sent to a client. A client reads a page, not a markdown file. `render-html.py` turns guides into standalone pages — a table of contents, styled alerts, tables, the screenshots embedded, the diagram drawn — and never writes into the KB.

- **Rendered on demand, never committed.** Markdown and its screenshots stay the only source. Render again after every update and send the new files.
- `--dir` renders every guide whose stamp says `audience: shareable`; a named file is rendered as given. Delivery notes render the same way.
- **One file per guide.** Screenshots are embedded in the page, so it can be sent on its own.
- **The page carries nothing internal:** the About section becomes "Last updated <date>" (the creation date when the guide has not been updated); the stamp comment never reaches the page; a `~~old~~ → new` mark shows only `new`; the *Answer* column of the open questions is shown as it is; links to other guides point to the matching `.html` file, so send a set's pages together.
- **Offline, the reader loses the diagram only.** The only request a page makes is the pinned Mermaid script; without it the diagram shows as "This diagram needs an internet connection" and every arrow is still a task in the text.
