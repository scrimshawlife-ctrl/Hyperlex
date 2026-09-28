import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.unbind_screen_v4 import rule_surface_violations
from hyperlexical.unbind_screen_v5 import Entry, Sense
from hyperlexical.unbind_screen_v6 import COMPOSITIONAL_EVIDENCE, apply_v6
from hyperlexical.unbind_screen_v7 import (
    ORDINARY_EVIDENCE,
    apply_v7,
    assess,
    ordinary_compositional_derivation,
)

PROBE_SURFACES = (
    "keep out",
    "to a lesser extent",
    "to the letter",
    "with child",
    "dressed to the nines",
    "union jack",
    "atomic number 98",
    "law of definite proportions",
)
V7_PATH = ROOT / "scripts" / "shadow" / "hyperlexical" / "unbind_screen_v7.py"


class MapLex:
    def __init__(self, entries, senses):
        self._entries = entries
        self._senses = senses

    def entry(self, surface):
        return self._entries.get(surface.casefold())

    def senses(self, token):
        return tuple(self._senses.get(token, ()))


def _sense(token, pos, lex, gloss):
    return Sense(token, pos, lex, gloss)


def _entry(pos, lemma, lex, lemmas, hypernyms=()):
    return Entry(pos, lemma, lex, tuple(lemmas), tuple(tuple(item) for item in hypernyms))


def _comparative_lex():
    return MapLex(
        {"to a greater degree": _entry("adv", "to_a_greater_degree", "adv.all", ("to_a_greater_degree",))},
        {
            "greater": (_sense("greater", "adj", "adj.all", "of greater size"),),
            "degree": (_sense("degree", "noun", "noun.attribute", "a position on a scale"),),
        },
    )


def _syntactic_lex(lemmas=("fully_shut",)):
    return MapLex(
        {"fully shut": _entry("verb", "fully_shut", "verb.contact", lemmas)},
        {
            "fully": (_sense("fully", "adv", "adv.all", "completely"),),
            "shut": (_sense("shut", "verb", "verb.contact", "prevent entering"),),
        },
    )


def _phrasal_lex():
    return MapLex(
        {"move out": _entry("verb", "move_out", "verb.motion", ("move_out",))},
        {
            "move": (_sense("move", "verb", "verb.motion", "change position"),),
            "out": (_sense("out", "adv", "adv.all", "away outside"),),
        },
    )


def test_ordinary_comparative_composition_may_fire():
    decision = apply_v7(
        "HIGH",
        "to a greater degree",
        "used to form the comparative of some adjectives and adverbs",
        "adv",
        _comparative_lex(),
    )
    assert decision["v7_bucket"] == "SECONDARY"
    assert decision["primary_evidence"] == ORDINARY_EVIDENCE
    assert decision["supporting_evidence"] == []
    assert ordinary_compositional_derivation(
        "to a greater degree",
        "used to form the comparative of some adjectives and adverbs",
        _comparative_lex(),
    )


def test_ordinary_syntactic_composition_may_fire():
    decision = apply_v7("HIGH", "fully shut", "completely prevent entering", "verb", _syntactic_lex())
    assert decision["v7_bucket"] == "SECONDARY"
    assert decision["primary_evidence"] == ORDINARY_EVIDENCE


def test_ordinary_phrasal_composition_may_fire():
    decision = apply_v7("HIGH", "move out", "change position away outside", "verb", _phrasal_lex())
    assert decision["v7_bucket"] == "SECONDARY"
    assert decision["primary_evidence"] == ORDINARY_EVIDENCE


def test_conventionalized_idiom_must_not_fire():
    decision = apply_v7(
        "HIGH",
        "fully shut",
        "completely prevent entering",
        "verb",
        _syntactic_lex(("fully_shut", "combust")),
    )
    assert decision["v7_bucket"] == "HIGH"
    assert decision["primary_evidence"] is None


def test_post_hoc_metaphor_must_not_fire():
    decision = apply_v7(
        "HIGH",
        "fully shut",
        "metaphorically completely prevent entering",
        "verb",
        _syntactic_lex(),
    )
    assert decision["v7_bucket"] == "HIGH"
    assert decision["primary_evidence"] is None


def test_gloss_resemblance_must_not_fire():
    lexicon = MapLex(
        {"fully shut": _entry("verb", "fully_shut", "verb.contact", ("fully_shut",))},
        {
            "fully": (_sense("fully", "adv", "adv.all", "completely done"),),
            "shut": (_sense("shut", "verb", "verb.contact", "prevent entering now"),),
        },
    )
    assert apply_v6("HIGH", "fully shut", "completely prevent", "verb", lexicon)["v6_bucket"] == "SECONDARY"
    assert apply_v6("HIGH", "fully shut", "completely prevent", "verb", lexicon)["primary_evidence"] == COMPOSITIONAL_EVIDENCE
    decision = apply_v7("HIGH", "fully shut", "completely prevent", "verb", lexicon)
    assert decision["v7_bucket"] == "HIGH"
    assert decision["primary_evidence"] is None
    assert decision["primary_evidence"] != COMPOSITIONAL_EVIDENCE


def test_named_phrase_is_irrelevant_to_the_high_challenge():
    lexicon = MapLex(
        {"alpha force": _entry("noun", "Alpha_Force", "noun.group", ("Alpha_Force",))},
        {
            "alpha": (_sense("alpha", "noun", "noun.communication", "the first letter"),),
            "force": (_sense("force", "noun", "noun.group", "a group of people"),),
        },
    )
    assert ordinary_compositional_derivation("alpha force", "a named group", lexicon) is False
    high = apply_v7("HIGH", "alpha force", "a named group", "noun", lexicon)
    assert high["v7_bucket"] == "HIGH"
    assert high["primary_evidence"] is None
    rejected = apply_v7("REJECT", "alpha force", "a named group", "noun", lexicon)
    inherited = apply_v6("REJECT", "alpha force", "a named group", "noun", lexicon)
    assert rejected["v7_bucket"] == inherited["v6_bucket"] == "REJECT"
    assert rejected["primary_evidence"] != ORDINARY_EVIDENCE


def test_demotion_stops_at_secondary():
    lexicon = _comparative_lex()
    gloss = "used to form the comparative of some adjectives and adverbs"
    demoted = apply_v7("HIGH", "to a greater degree", gloss, "adv", lexicon)
    assert demoted["v7_bucket"] == "SECONDARY"
    stopped = apply_v7("SECONDARY", "to a greater degree", gloss, "adv", lexicon)
    assert stopped["v7_bucket"] == "SECONDARY"
    assert stopped["primary_evidence"] is None


def test_reject_behavior_matches_v6_and_secondary_is_not_reopened():
    pertainym = MapLex(
        {"on duty": _entry("adj", "on_duty", "adj.pert", ("on_duty",))},
        {"duty": (_sense("duty", "noun", "noun.act", "work that is a paid activity"),)},
    )
    rejected = apply_v7("REJECT", "on duty", "actively engaged in paid work", "adj", pertainym)
    inherited = apply_v6("REJECT", "on duty", "actively engaged in paid work", "adj", pertainym)
    assert rejected["v7_bucket"] == inherited["v6_bucket"] == "SECONDARY"
    assert rejected["primary_evidence"] == inherited["primary_evidence"] == "nonreferential_lexical_use"
    naming = MapLex(
        {"alpha force": _entry("noun", "Alpha_Force", "noun.group", ("Alpha_Force",))},
        {"force": (_sense("force", "noun", "noun.group", "a group of people"),)},
    )
    assert apply_v6("SECONDARY", "alpha force", "a named group", "noun", naming)["v6_bucket"] == "REJECT"
    held = apply_v7("SECONDARY", "alpha force", "a named group", "noun", naming)
    assert held["v7_bucket"] == "SECONDARY"
    assert held["primary_evidence"] is None


def test_previously_correct_is_not_bucket_immutability():
    allowed = assess(
        [
            {
                "surface": "may retreat",
                "v6_bucket": "HIGH",
                "v7_bucket": "SECONDARY",
                "operator_bucket": "SECONDARY",
                "primary_evidence": ORDINARY_EVIDENCE,
                "supporting_evidence": [],
            }
        ],
        phrase_specific_rule_fired=False,
        expected_rows=1,
    )
    assert allowed["previously_correct_lost"] == 0
    assert allowed["correct_high_lost"] == 0
    assert allowed["regression"] == "REGRESSION_VERIFIED"
    assert allowed["measurement_eligible"] is False
    broken = assess(
        [
            {
                "surface": "was right",
                "v6_bucket": "HIGH",
                "v7_bucket": "SECONDARY",
                "operator_bucket": "HIGH",
                "primary_evidence": ORDINARY_EVIDENCE,
                "supporting_evidence": [],
            }
        ],
        phrase_specific_rule_fired=False,
        expected_rows=1,
    )
    assert broken["previously_correct_lost"] == 1
    assert broken["correct_high_lost"] == 1
    assert broken["regression"] == "REGRESSION_FAILED"


def test_direct_outer_swap_fails_the_gate():
    report = assess(
        [
            {
                "surface": "swapped",
                "v6_bucket": "HIGH",
                "v7_bucket": "REJECT",
                "operator_bucket": "REJECT",
                "primary_evidence": "referential_terminological_dominance",
                "supporting_evidence": [],
            }
        ],
        phrase_specific_rule_fired=False,
        expected_rows=1,
    )
    assert report["direct_swaps"] == 1
    assert "HIGH and REJECT swapped directly" in report["failures"]


def test_unknown_bucket_is_refused():
    with pytest.raises(Exception):
        apply_v7("MAYBE", "move out", "gloss", "verb", _phrasal_lex())


def test_probe_surfaces_are_not_rules():
    source = V7_PATH.read_text(encoding="utf-8")
    assert rule_surface_violations(source, PROBE_SURFACES) == []
    assert "compositional_recoverability" not in source
    tree = ast.parse(source)
    assert any(isinstance(node, ast.FunctionDef) and node.name == "apply_v7" for node in ast.walk(tree))
