# When the user renamed it too (path B variant)

A user replacing the file by hand often renames it in the same move — dropping in `{service}-openapi-2026-07-29.json` beside the old `…-2026-03-01.json`, or `git mv`-ing then overwriting. The delta is still recoverable; take it against the committed old path rather than the working tree:

```bash
git status --porcelain -- <specs dir>                    # see both sides of the move
git diff -M -- <specs dir>                               # rename-detecting diff (staged move)
# or, explicitly, old committed content vs the new file:
git show HEAD:<old asset path> > "$SCRATCH/spec-before.json"
git diff --no-index "$SCRATCH/spec-before.json" <new asset path>
```

Then continue from step 5. Two rules hold: **the old file must end up deleted** — one asset per service, always, so fix it in this run if the user left both — and **the rename is not evidence**; classify from the diff exactly as on any other path, even when the new name's date makes the change look obvious.
