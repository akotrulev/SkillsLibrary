# Mission Control has moved

Mission Control used to live here at `tools/mission-control`. It is now its own
private repository:

**https://github.com/akotrulev/mission-control**

Its plan documents (`docs/plans/00{1..6}-mission-control-*.md`) moved with it and
live under `docs/plans/` in that repo.

## What this means for SkillsLibrary

Nothing in this library imports Mission Control — the dependency runs the other
way. Mission Control reads this repo as its agent/skill catalog, via
`MISSION_CONTROL_LIBRARY_ROOT` pointing at a checkout of SkillsLibrary
(previously it defaulted to `../..` from inside `tools/mission-control`).

The catalog contract Mission Control depends on is the one in `CLAUDE.md`: agent
definitions under `<domain>/agents/*.md` and skills under `<domain>/**/SKILL.md`,
with `docs/plans/<NNN>-<initiative>/delivery-plan.md` as the ingestion format
that `solution-planner` produces. Changing either of those shapes is a breaking change
for Mission Control.

Moved 2026-08-09. The pre-move history is still in this repo's log under
`tools/mission-control`.
