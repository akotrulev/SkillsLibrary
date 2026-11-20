import contextlib
import importlib.util
import io
import shutil
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLEAN_KB = HERE / "fixtures" / "clean-kb"
SPEC = importlib.util.spec_from_file_location("kb_lint", HERE / "kb-lint.py")
kb_lint = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kb_lint)

ENTITY = "entities/booking.md"
DECISION = "decisions/credit-return.md"
FLOW = "flows/book-a-seat.md"
EVENTS = "events.md"
MAP = "interaction-map.md"
CONTEXT = "active-context.md"
INDEX = "INDEX.md"
CONFIRMED_STATE = "| Confirmed | a seat is held for the member | yes | no |"
CANCELLED_STATE = "| Cancelled | the seat is released | no | yes |"
CANCELLED_ROW = "| Cancelled | — | — | ? |"
STATES_HEADER = "| State | Meaning | Initial? | Terminal? | Source |\n|---|---|---|---|---|"
CONF_002 = "## CONF-002 — AREA-002 scheduling × AREA-003 bookings: cancelling a cancelled booking"
AREA_GUIDE = "# Area\n\n<!-- guide · id: AREA-001 · owner: product:doc-business-model · audience: shareable -->\n"
ENTITIES = "(business-model-entities.md)"
DECISIONS = "(business-model-decisions.md)"
CONNECTIONS = "(business-model-connections.md)"
INTERACTIONS = "(business-model-interactions.md)"
CORE = "(business-model.md)"


def without(name, text):
    return (name, text, "")


class KbLintTests(unittest.TestCase):
    def kb_with(self, *changes):
        """A copy of the clean fixture KB with each change applied: (file, old, new) replaces text, old None writes
        a new file, new None deletes the file."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        kb = Path(folder.name) / "kb"
        shutil.copytree(CLEAN_KB, kb)
        for name, old, new in changes:
            path = kb / name
            if new is None:
                path.unlink()
            elif old is None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(new, encoding="utf-8")
            else:
                text = path.read_text(encoding="utf-8")
                self.assertIn(old, text, f"fixture {name} no longer holds {old!r}")
                path.write_text(text.replace(old, new, 1), encoding="utf-8")
        return kb

    def findings(self, *changes):
        return [str(f) for f in kb_lint.lint(self.kb_with(*changes))]

    def assert_cases(self, cases):
        for label, changes, expected in cases:
            with self.subTest(label):
                self.assertEqual(expected, self.findings(*changes))

    def test_Should_ReportNothing_When_KbIsClean(self):
        self.assertEqual([], self.findings())

    def test_Should_ReportNothing_When_KbVariesWithinTheRules(self):
        self.assert_cases([
            ("external and anchor links", [(INDEX, "- [Glossary](glossary.md)", "- [Glossary](glossary.md#terms) · [wiki](https://example.com/wiki)")], []),
            ("collect hit policy", [(DECISION, "**Hit policy**: U", "**Hit policy:** C+ (sum — BRD §4)")], []),
            ("undecided hit policy", [(DECISION, "**Hit policy**: U", "**Hit policy**: [TBD - needs business decision]")], []),
            ("open vocabulary values", [(EVENTS, "| after commit, at-least-once | retried 3× then dead-letter |", "| best effort | compensates: re-credits |"),
                                        (EVENTS, "| scheduled | ? |", "| after commit, ? | unhandled |")], []),
            ("event terminal by decision", [(EVENTS, "| RX-004 | EVT-004 |", "| RX-004 | EVT-005 |"),
                                            (EVENTS, "| AREA-003 bookings | US4 AC2 |", "| AREA-003 bookings | US4 AC2 · terminal by decision (BRD §3) |")], []),
            ("entity with an empty grid section", [(ENTITY, "## Transition grid\n", "## Transition grid\n\n## Draft grid\n")], []),
            ("class spelt with spaced slash", [(MAP, "state interference (3)", "Ordering / race (5)")], []),
            ("no interaction map", [(MAP, None, None), without(INDEX, "- [Interaction map](interaction-map.md) — 1 resolved conflict, 1 open (CONF-002)\n")], []),
            ("free-text columns before events.md exists", [(EVENTS, None, None), without(INDEX, "- [Events & reactions](events.md) — 5 triggers, 5 reactions\n"),
                                                           (ENTITY, "EVT-003 staff cancels a session", "staff cancels a session")], []),
        ])

    def test_Should_ReportModelIndex_When_IndexMissesOrBreaksALine(self):
        self.assert_cases([
            ("artifact with no line", [without(INDEX, "- [Glossary](glossary.md) — canonical terms\n")],
             [f"INDEX.md:1: major model-index no line links glossary.md {CORE}"]),
            ("link that does not resolve", [(INDEX, "(entities/booking.md)", "(entities/bookings.md)")],
             [f"INDEX.md:1: major model-index no line links entities/booking.md {CORE}",
              f"INDEX.md:6: major model-index link entities/bookings.md does not resolve {CORE}"]),
            ("no INDEX.md", [(INDEX, None, None)], [f"INDEX.md:1: major model-index INDEX.md is missing {CORE}"]),
        ])

    def test_Should_ReportModelId_When_AnIdIsMissingOrMalformed(self):
        self.assert_cases([
            ("entity title", [(ENTITY, " (ENT-001)", "")], [f"{ENTITY}:1: blocker model-id the title carries no ENT-nnn id {CORE}"]),
            ("flow title", [(FLOW, " (FLOW-001)", "")], [f"{FLOW}:1: blocker model-id the title carries no FLOW-nnn id {CORE}"]),
            ("flow node of another flow", [(FLOW, "| FLOW-001.2 |", "| FLOW-002.2 |")],
             [f"{FLOW}:23: blocker model-id flow node id 'FLOW-002.2' is not well-formed {CORE}"]),
            ("reaction", [(EVENTS, "| RX-005 |", "| RX5 |")], [f"events.md:22: blocker model-id reaction id 'RX5' is not well-formed {CORE}"]),
            ("invariant", [("invariants.md", "| INV-001 |", "| INV-01x |")],
             [f"invariants.md:8: blocker model-id invariant id 'INV-01x' is not well-formed {CORE}"]),
        ])

    def test_Should_ReportModelIdUnique_When_AnIdIsDefinedTwice(self):
        self.assert_cases([
            ("trigger", [(EVENTS, "| EVT-005 | Monthly", "| EVT-004 | Monthly"), (EVENTS, "| RX-005 | EVT-005 |", "| RX-005 | EVT-004 |")],
             [f"events.md:13: blocker model-id-unique EVT-004 is already defined at events.md:12 {CORE}"]),
            ("area across guides", [("areas/a.md", None, AREA_GUIDE), ("areas/b.md", None, AREA_GUIDE)],
             [f"areas/b.md:3: blocker model-id-unique AREA-001 is already defined at areas/a.md:3 {CORE}"]),
        ])

    def test_Should_ReportModelHeader_When_AMetadataLineIsMissing(self):
        self.assert_cases([
            ("created", [without(EVENTS, "**Created:** 2026-08-02\n")], [f"events.md:1: minor model-header no **Created:** <YYYY-MM-DD> line in the metadata block {CORE}"]),
            ("owned by", [without(DECISION, "**Owned by:** `product:decision-table`\n")],
             [f"{DECISION}:1: minor model-header no **Owned by:** line in the metadata block {CORE}"]),
        ])

    def test_Should_ReportEntitiesStates_When_AFlagColumnOrValueIsWrong(self):
        self.assert_cases([
            ("older shape without Initial?", [(ENTITY, STATES_HEADER, "| State | Meaning | Terminal? | Source |\n|---|---|---|---|"),
                                              (ENTITY, CONFIRMED_STATE, "| Confirmed | a seat is held for the member | no |"),
                                              (ENTITY, CANCELLED_STATE, "| Cancelled | the seat is released | yes |")],
             [f"{ENTITY}:8: minor entities-states the States table has no Initial? column; an entity file in the older shape gains it when next edited {ENTITIES}"]),
            ("no Terminal?", [(ENTITY, STATES_HEADER, "| State | Meaning | Initial? | Source |\n|---|---|---|---|"),
                              (ENTITY, CONFIRMED_STATE, "| Confirmed | a seat is held for the member | yes |"),
                              (ENTITY, CANCELLED_STATE, "| Cancelled | the seat is released | no |")],
             [f"{ENTITY}:8: minor entities-states the States table has no Terminal? column; an entity file in the older shape gains it when next edited {ENTITIES}"]),
            ("value outside yes, no, ?", [(ENTITY, CONFIRMED_STATE, "| Confirmed | a seat is held for the member | maybe | no |")],
             [f"{ENTITY}:11: minor entities-states Confirmed: 'maybe' is not yes, no or ? {ENTITIES}",
              f"{ENTITY}:14: major entities-reachable Confirmed is targeted by no cell and is not Initial? yes: unreachable {ENTITIES}"]),
        ])

    def test_Should_ReportEntitiesCell_When_AGridCellOrRowIsMissing(self):
        self.assert_cases([
            ("blank cell", [(ENTITY, CANCELLED_ROW, "| Cancelled | — |  | ? |")],
             [f"{ENTITY}:20: major entities-cell Cancelled × EVT-002 member cancels is blank {ENTITIES}"]),
            ("short row", [(ENTITY, CANCELLED_ROW, "| Cancelled | — | — |")],
             [f"{ENTITY}:20: major entities-cell Cancelled × EVT-003 staff cancels a session is blank {ENTITIES}"]),
            ("state with no row", [without(ENTITY, CANCELLED_ROW + "\n")],
             [f"{ENTITY}:14: major entities-cell state Cancelled has no row in the transition grid {ENTITIES}"]),
        ])

    def test_Should_ReportEntitiesReachable_When_AStateCannotBeEnteredOrLeft(self):
        self.assert_cases([
            ("unreachable", [(ENTITY, CONFIRMED_STATE, "| Confirmed | a seat is held for the member | no | no |")],
             [f"{ENTITY}:14: major entities-reachable Confirmed is targeted by no cell and is not Initial? yes: unreachable {ENTITIES}"]),
            ("dead", [(ENTITY, CANCELLED_STATE, "| Cancelled | the seat is released | no | no |"), (ENTITY, CANCELLED_ROW, "| Cancelled | — | — | — |")],
             [f"{ENTITY}:14: major entities-reachable Cancelled has no legal transition and no ? and is not Terminal? yes: dead {ENTITIES}"]),
        ])

    def test_Should_ReportEntitiesOwner_When_ATransitionHasNoneOrTwoOwners(self):
        self.assert_cases([
            ("orphan", [(ENTITY, "Cancelled (AREA-003)", "Cancelled")],
             [f"{ENTITY}:19: major entities-owner Confirmed × EVT-002 member cancels names no owning feature id {ENTITIES}"]),
            ("double-fire", [(ENTITY, "Cancelled (AREA-002)", "Cancelled (AREA-002, E4)")],
             [f"{ENTITY}:19: major entities-owner Confirmed × EVT-003 staff cancels a session names 2 owning features: a double-fire {ENTITIES}"]),
        ])

    def test_Should_ReportGridColumns_When_AHeaderIsNotATriggerOfEventsMd(self):
        self.assert_cases([
            ("free-text header", [(ENTITY, "EVT-003 staff cancels a session", "staff cancels a session")],
             [f"{ENTITY}:14: minor entities-event-id column 'staff cancels a session' carries no EVT- id {ENTITIES}"]),
            ("unknown trigger", [(ENTITY, "EVT-003 staff", "EVT-009 staff")],
             [f"{ENTITY}:14: major connections-grid-column EVT-009 is not a trigger in events.md {CONNECTIONS}"]),
        ])

    def test_Should_ReportDecisionFindings_When_PolicyChecksOrRowsAreIncomplete(self):
        self.assert_cases([
            ("no hit policy", [without(DECISION, "**Hit policy**: U\n")], [f"{DECISION}:1: major decisions-hit-policy no **Hit policy** line {DECISIONS}"]),
            ("unknown hit policy", [(DECISION, "**Hit policy**: U", "**Hit policy**: first match")],
             [f"{DECISION}:7: major decisions-hit-policy 'first match' is not U, A, F, P, C, C+, C<, C>, C# or [TBD - needs business decision] {DECISIONS}"]),
            ("no Checks", [without(DECISION, "## Checks\n- Completeness: ✅ all combinations covered (R1–R3)\n- Overlap: none\n")],
             [f"{DECISION}:1: major decisions-checks no Checks section {DECISIONS}"]),
            ("no Overlap", [without(DECISION, "- Overlap: none\n")], [f"{DECISION}:23: major decisions-checks the Checks section records no Overlap check {DECISIONS}"]),
            ("row without feature id", [(DECISION, "| AREA-004 credits | CONF-001 |", "| credits | CONF-001 |")],
             [f"{DECISION}:21: major decisions-row rule R3 names no owning feature id {DECISIONS}"]),
            ("rules table without a Feature column", [(DECISION, "| → returned | Feature | Source |", "| → returned | Owner | Source |")],
             [f"{DECISION}:19: major decisions-row rule R1 names no owning feature id {DECISIONS}",
              f"{DECISION}:20: major decisions-row rule R2 names no owning feature id {DECISIONS}",
              f"{DECISION}:21: major decisions-row rule R3 names no owning feature id {DECISIONS}"]),
            ("row without source", [(DECISION, "| AREA-004 credits | CONF-001 |", "| AREA-004 credits |  |")],
             [f"{DECISION}:21: major decisions-row rule R3 names no source {DECISIONS}"]),
        ])

    def test_Should_ReportConnectionFindings_When_EventsMdBreaksItsVocabulary(self):
        self.assert_cases([
            ("kind", [(EVENTS, "| command | Staff |", "| api call | Staff |")],
             [f"events.md:11: major connections-kind EVT-003: Kind 'api call' is not command, schedule, timeout, external or event {CONNECTIONS}"]),
            ("event without emitter", [(EVENTS, "| event | RX-002, RX-003 |", "| event | Bookings |")],
             [f"events.md:12: major connections-kind EVT-004: an event trigger's Fired by lists no RX- id {CONNECTIONS}"]),
            ("blank reaction cell", [(EVENTS, "| EVT-003 | — | AREA-002", "| EVT-003 |  | AREA-002")],
             [f"events.md:20: major connections-reaction RX-003: Guard is blank {CONNECTIONS}"]),
            ("mode", [(EVENTS, "| scheduled | ? |", "| nightly | ? |")],
             [f"events.md:22: major connections-mode RX-005: Mode 'nightly' is outside the vocabulary {CONNECTIONS}"]),
            ("on failure", [(EVENTS, "| retried 3× then dead-letter |", "| retried until it works |")],
             [f"events.md:21: major connections-on-failure RX-004: On failure 'retried until it works' is outside the vocabulary {CONNECTIONS}"]),
            ("when without trigger id", [(EVENTS, "| RX-005 | EVT-005 |", "| RX-005 | monthly |")],
             [f"events.md:22: major connections-when RX-005: When names no EVT- trigger {CONNECTIONS}"]),
            ("when fired by nothing", [(EVENTS, "| RX-005 | EVT-005 |", "| RX-005 | EVT-009 |")],
             [f"events.md:22: major connections-when RX-005: When EVT-009 is not a trigger {CONNECTIONS}"]),
            ("unconsumed event", [(EVENTS, "| RX-004 | EVT-004 |", "| RX-004 | EVT-005 |")],
             [f"events.md:12: major connections-consumed EVT-004: no reaction consumes this event and it is not terminal by decision {CONNECTIONS}"]),
        ])

    def test_Should_ReportInteractionFindings_When_AnEntryIsIncompleteOrUnlisted(self):
        self.assert_cases([
            ("heading shape", [(MAP, CONF_002, "## CONF-002 cancelling a cancelled booking")],
             [f"interaction-map.md:9: blocker interactions-heading not shaped '## CONF-nnn — <feature> × <feature>: <the conflict>' {INTERACTIONS}"]),
            ("no sources", [without(MAP, " · **Sources**: US4, US7")], [f"interaction-map.md:9: major interactions-entry no Sources {INTERACTIONS}"]),
            ("unknown class", [(MAP, "state interference (3)", "timing (5)")],
             [f"interaction-map.md:9: major interactions-entry class 'timing (5)' is not one of the eleven {INTERACTIONS}"]),
            ("unknown severity", [(MAP, "**Severity**: minor", "**Severity**: low")],
             [f"interaction-map.md:9: major interactions-entry severity 'low' is not blocker, major, minor or nit {INTERACTIONS}"]),
            ("open entry not listed", [without(CONTEXT, "- CONF-002 — a cancelled booking cancelled again by a session cancellation · owner: PO\n")],
             [f"interaction-map.md:9: blocker interactions-open open CONF-002 is not listed under active-context.md's Open questions {INTERACTIONS}"]),
            ("no active context", [(CONTEXT, None, None), without(INDEX, "- [Active context](active-context.md) — last touched 2026-11-17; 2 open questions\n")],
             [f"interaction-map.md:9: blocker interactions-open open CONF-002 is not listed under active-context.md's Open questions {INTERACTIONS}"]),
        ])

    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = kb_lint.main([str(a) for a in args])
        return code, out.getvalue(), err.getvalue()

    def test_Should_ExitZero_When_KbIsClean(self):
        self.assertEqual((0, "", "kb-lint: 0 blocker, 0 major, 0 minor, 0 nit\n"), self.run_main(self.kb_with()))

    def test_Should_ExitOneAndPrintThePath_When_AFindingIsMajor(self):
        kb = self.kb_with((ENTITY, CANCELLED_ROW, "| Cancelled | — |  | ? |"))
        expected = f"{kb.as_posix()}/{ENTITY}:20: major entities-cell Cancelled × EVT-002 member cancels is blank {ENTITIES}\n"
        self.assertEqual((1, expected, "kb-lint: 0 blocker, 1 major, 0 minor, 0 nit\n"), self.run_main(kb))

    def test_Should_ExitZero_When_FindingsAreMinorOnly(self):
        code, _, err = self.run_main(self.kb_with(without(EVENTS, "**Created:** 2026-08-02\n")))
        self.assertEqual((0, "kb-lint: 0 blocker, 0 major, 1 minor, 0 nit\n"), (code, err))

    def test_Should_ExitTwo_When_DirectoryDoesNotExist(self):
        self.assertEqual(2, self.run_main(CLEAN_KB / "missing")[0])


if __name__ == "__main__":
    unittest.main()
