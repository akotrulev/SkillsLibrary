# Architecture Conformance Checklist — the 5 sections

The audit's spine. Section letters and check numbers are **permanent**: a finding is `<letter><n>` (`B2`, `D1`) and keeps that ID across every round. Never renumber; append new checks at the end of a section with the next free number.

**How to read a row.** *Check* = the invariant. *Bad sign* = what disqualifies it. *Locate* = a mechanical lead; a hit is never a finding, the code at the hit decides. *Sev* = the default severity; adjust for real impact and say why.

## Locate recipes

Every recipe is read-only shell: `git grep`, `git ls-files`, `git log`, `ls`, `diff` and `sort`, `uniq`, `cut`, `wc`, `cksum`. `git grep` reads the tracked tree, so build output is skipped; add `--untracked` for new files. A clone detector (`jscpd`) or a cycle tool (`madge`) runs only when the user opts in for this audit, and corroborates a read.

`<src>` is a source root from the module map, `<module>` one module's path, `<tests>` the test paths Step 1 found. Set the two patterns from the language lane before the sweep:

```bash
IMPORTS='<imports>'
PUBLIC='<public>'
```

| Language | `<imports>` | `<public>` |
|---|---|---|
| TypeScript, JavaScript | `^(import\|export) .* from \|require\(` | `^export ` |
| C# | `^using ` | `^\s*public ` |
| Java | `^import ` | `^\s*public ` |
| Kotlin | `^import ` | `^\s*(fun\|class\|object\|interface) ` minus the lines holding `internal` or `private` |
| Python | `^(from\|import) ` | `^(def\|class) [A-Za-z]` |
| Rust | `^use ` | `^\s*pub (fn\|struct\|enum\|trait\|type\|const) ` |
| Swift | `^import ` | `^\s*(public\|open) ` |

Test files in a recipe are excluded with the pathspec `':!*[Tt]est*' ':!*[Ss]pec*'`.

---

## A — Module map and dependencies
*Owner: the stack agent; `architecture-review` (`backend/_shared/code-review`) for layering and boundaries, cited and never restated.*

| # | Check | Bad sign | Locate | Sev |
|---|---|---|---|---|
| A1 | Every top-level area has one stated purpose | A `utils`, `common`, `shared` or `helpers` area that unrelated modules import | The map: `git ls-files \| cut -d/ -f1-2 \| sort \| uniq -c \| sort -rn`. Catch-all areas: `git ls-files ':(icase)*/utils/*' ':(icase)*/common/*' ':(icase)*/shared/*' ':(icase)*/helpers/*' \| cut -d/ -f1-3 \| sort -u`. Importing areas per catch-all: `git grep -l -E "$IMPORTS.*<area>" -- <src> \| cut -d/ -f1-2 \| sort -u` | minor |
| A2 | Each module has one entry surface | Callers import files from inside the module, past its index or public types | The surfaces: `git ls-files -- '*/index.*' '*/__init__.py' '*/lib.rs' '*/mod.rs'`. Deep imports from outside: `git grep -n -E "$IMPORTS.*<module>[/.][A-Za-z_]+" -- <src> ':!<module>'` | major |
| A3 | Dependencies between modules have no cycle | Module X imports Y and Y imports X, directly or through a third | Project edges: `git grep -n -e ProjectReference -e 'project(' -e 'path = ' -- '*.csproj' '*.gradle*' '*Cargo.toml'`. Source edges for a pair X, Y: `git grep -l -E "$IMPORTS.*Y" -- X` and the same with X and Y swapped; a hit both ways is a cycle. Longer cycles: follow the edges from X until X returns | major |


---

## B — Module depth
*Owners: the stack agent and `CLAUDE.md` "Simplicity" ("Flat over layered"). An interface with one implementation is `architecture-review`'s row.*

| # | Check | Bad sign | Locate | Sev |
|---|---|---|---|---|
| B1 | A module hides more than it exposes | Most public members are one-line forwards or bare data. A caller must know the internals to use it | Surface size: `git grep -c -E "$PUBLIC" -- <module>`. Body size: `git ls-files <module> \| xargs cat \| wc -l`. Read the surface of the five modules with the most public members per body line | major for a module, minor for one type |
| B2 | No forwarding layer | A type whose methods pass the same arguments to one collaborator and return its result | Forward count per file: `git grep -c -E "(return\|=>) +(await +)?(this\.\|_)[A-Za-z]+\.[A-Za-z]+\(" -- <src> ':!*[Tt]est*'`. Open the ten highest and compare the count with the file's method count | major |
| B3 | Internals stay inside | A persistence row type, a mutable collection or a config object in the public surface | `git grep -n -E "$PUBLIC.*(Entity\|Row\|Record\|Model\|Schema\|Document)\b" -- <module>`; `git grep -n -E "$PUBLIC.*(List<\|\[\]\|Dictionary<\|Map<\|Set<\|Vec<\|dict\b)" -- <module>`; `git grep -n -E "$PUBLIC.*(Options\|Config\|Settings)\b" -- <module>` | major |
| B4 | One decision lives in one module | A file format, a protocol detail or a magic value that two modules each encode | Repeated literals: `git grep -h -o -E "\"[A-Za-z0-9_:/.-]{6,}\"" -- <src> ':!*[Tt]est*' \| sort \| uniq -c \| sort -rn \| head -30`. Modules holding one literal: `git grep -l -F "<literal>" -- <src> \| cut -d/ -f1-2 \| sort -u`. Formats and headers: `git grep -n -e 'yyyy-MM' -e toISOString -e Content-Type -e Authorization -e '\.csv' -- <src>` | major |


---

## C — Duplicated logic
*Owners: the stack agent and `CLAUDE.md` "Simplicity". Duplication under the threshold below is never a finding.*

| # | Check | Bad sign | Locate | Sev |
|---|---|---|---|---|
| C1 | No near-identical block in two modules | 20 or more lines, or two whole functions, that match apart from names | Files with one name in two places: `git ls-files \| xargs -n1 basename \| sort \| uniq -d`; for each pair `diff <a> <b> \| wc -l` (a small count is a near-copy). Function names in two modules: `git grep -h -o -E "(function\|def\|fn\|func) +[A-Za-z_]{12,}" -- <src> ':!*[Tt]est*' \| sort \| uniq -d`. Drift: `git log --oneline -3 -- <a> <b>`; one copy edited alone has drifted | major when the copies have drifted, minor when identical |
| C2 | One business rule, one implementation | The same validation, calculation or status rule written in two places | A status or enum value tested in several modules: `git grep -n -w "<Value>" -- <src> ':!*[Tt]est*' \| cut -d: -f1 \| cut -d/ -f1-2 \| sort \| uniq -c`. A threshold written twice: `git grep -h -o -E "(>=\|<=\|>\|<) *[0-9]{2,}" -- <src> ':!*[Tt]est*' \| sort \| uniq -c \| sort -rn \| head -20` then `git grep -n -F "<comparison>" -- <src>`. Rule words: `git grep -n -i -e discount -e vat -e tax -e eligib -e expire -- <src>` | major |
| C3 | No parallel modules | Two modules of the same shape that differ by a noun | Structure per sibling module of one area: `for m in $(ls <area>); do echo "$m $(git ls-files <area>/$m \| sed "s#^<area>/$m/##" \| sort \| cksum)"; done`. Equal checksums on two modules are parallel; then read both for a differing noun only | minor |


---

## D — Tests and the entry surface
*Applies when the scope has tests. Owners: the stack's `unit-testing` skill; `qa-<stack>:test-audit` is the peer for pruning and repairing a suite.*

| # | Check | Bad sign | Locate | Sev |
|---|---|---|---|---|
| D1 | Tests enter through the entry surface | A test reaches a non-public member: reflection, widened visibility, a deep import, a suppressed type error | By language, over `<tests>`. C#: `git grep -n -e InternalsVisibleTo -e BindingFlags.NonPublic -e PrivateObject`. Java: `git grep -n -e 'setAccessible(true)' -e ReflectionTestUtils -e getDeclaredMethod -e VisibleForTesting`. TypeScript: `git grep -n -e @ts-expect-error -e @ts-ignore -e 'as any)\.' -- <tests>`, then the A2 deep-import probe over `<tests>`. Python: `git grep -n -E "^(from\|import) [A-Za-z_.]*\._[a-z]" -- <tests>`. Rust and Swift: `git grep -n -B1 -F -e 'pub(crate)' -e '#[cfg(test)]' -- <src>` and `git grep -n -B1 -E "^\s*public " -- <src>`, read for visibility widened only for a test | major |
| D2 | Tests assert outcomes | A call assertion on a collaborator the module owns, where the outcome is observable at the entry surface | Call assertions per test file: `git grep -c -e toHaveBeenCalled -e '.Verify(' -e 'verify(' -e Received -e assert_called -- <tests>`. Read the top files: is the verified collaborator in this repo (owned) or a boundary such as HTTP, mail or a clock? | minor |
| D3 | A module with rules has a test through its surface | Only its internal files are tested | Rule density: `git grep -c -E "\b(if\|switch\|throw\|raise\|match\|when)\b" -- <module> ':!*[Tt]est*'`. Tests through the surface: `git grep -l -E "$IMPORTS.*<module>['\";]?$" -- <tests>`. A module with a high count and no hit has no entry-surface test; tests that import only its inner files (the A2 probe over `<tests>`) are the finding's evidence | major |


---

## E — Code against the glossary
*Applies when `docs/business-model/glossary.md` exists. Owners: `product/skills/domain-modeling/references/glossary-format.md`. E3 belongs to the `business-analyst` agent, which needs `product` enabled.*

The glossary's table has the columns `Term (client)`, `Means`, `Avoid`, `Called in code`. Read it first and take each row's `Avoid` terms and `Called in code` cell as the search lists.

| # | Check | Bad sign | Locate | Sev |
|---|---|---|---|---|
| E1 | Code uses the glossary's term | An identifier, route or UI string that uses a term listed under `Avoid` | Per `Avoid` term: `git grep -n -i -w "<term>" -- <src> ':!docs'`. Routes and UI strings: `git grep -n -i "<term>" -- '*.json' '*.resx' '*.po' '*.properties' '*.strings'`. A comment hit is not a finding | minor |
| E2 | Code names match the glossary | A concept's identifier differs from its `Called in code` cell | Per row: `git grep -n -w "<Called in code>" -- <src>`; with no hit, the nearest name for the concept: `git grep -n -i -E "(class\|type\|interface\|struct\|record\|enum\|def\|fn) +[A-Za-z]*<Concept>[A-Za-z]*" -- <src>`. A `—` cell has nothing to check | minor |
| E3 | One term, one concept | The code uses one glossary term for two things | Types named alike: `git grep -n -E "(class\|type\|interface\|struct\|record) +<Term>\b" -- <src>`. A second hit in another module with different members is the lead; read both definitions and the glossary row for **Drift** | major, a logical conflict owned by `business-analyst` |


---

## Never a finding

- A small module with a small surface. Size is not depth.
- An adapter over code the project does not own. That is a port.
- Duplication under C1's threshold, or in tests, generated code and migrations.
- A consistent project convention. The engine's deviations table holds it.
- An interface with one implementation. That row is `architecture-review`'s; cite it, never restate it.
- A test in Rust's in-file `#[cfg(test)]` module, or Swift's `@testable import`. That is the language's own test access. Visibility widened only for a test is D1.

## Fix directions

A shallow module is merged into its caller or its callee. A forwarding layer is removed. Duplicated logic moves into one module that both callers use, and only when two callers exist today. No fix direction proposes a new layer, a base class or a generic framework.

Evidence is static, per the engine. A finding cites the `file:line` read this round and the search that found it, and the grouped sites of one family are one finding with a count.
