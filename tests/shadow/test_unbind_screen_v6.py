import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.unbind_screen_v4 import rule_surface_violations
from hyperlexical.unbind_screen_v5 import Entry, Sense
from hyperlexical.unbind_screen_v6 import (
    COMPOSITIONAL_EVIDENCE,
    NONREFERENTIAL_EVIDENCE,
    apply_v6,
    assess,
    measurement_allowed,
)

PROBE_SURFACES = (
    "keep out",
    "on the job",
    "hit the roof",
    "pop the question",
    "all of a sudden",
    ".22 caliber",
)
V6_PATH = ROOT / "scripts" / "shadow" / "hyperlexical" / "unbind_screen_v6.py"


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


def _compositional_lex():
    return MapLex(
        {"fully shut": _entry("verb", "Fully_Shut", "verb.contact", ("fully_shut",))},
        {
            "fully": (_sense("fully", "adv", "adv.all", "completely"),),
            "shut": (_sense("shut", "verb", "verb.contact", "prevent entering"),),
        },
    )


def test_compositional_high_falls_to_secondary_and_stops():
    decision = apply_v6("HIGH", "fully shut", "completely prevent entering", "verb", _compositional_lex())
    assert decision["v6_bucket"] == "SECONDARY"
    assert decision["primary_evidence"] == COMPOSITIONAL_EVIDENCE
    assert decision["supporting_evidence"] == []


def test_idiomatic_mapping_blocks_post_hoc_rationalization():
    lexicon = MapLex(
        {"fully shut": _entry("verb", "fully_shut", "verb.contact", ("fully_shut", "combust"))},
        {
            "fully": (_sense("fully", "adv", "adv.all", "completely"),),
            "shut": (_sense("shut", "verb", "verb.contact", "prevent entering"),),
        },
    )
    decision = apply_v6("HIGH", "fully shut", "completely prevent entering", "verb", lexicon)
    assert decision["v6_bucket"] == "HIGH"
    assert decision["primary_evidence"] is None


def test_single_constituent_gloss_is_not_ordinary_syntax():
    lexicon = MapLex(
        {"quite sudden": _entry("adv", "quite_sudden", "adv.all", ("quite_sudden",))},
        {
            "quite": (_sense("quite", "adv", "adv.all", "to a degree"),),
            "sudden": (_sense("sudden", "adj", "adj.all", "happening without warning"),),
        },
    )
    decision = apply_v6("HIGH", "quite sudden", "without warning", "adv", lexicon)
    assert decision["v6_bucket"] == "HIGH"


def test_state_pertainym_falls_to_secondary():
    lexicon = MapLex(
        {"on duty": _entry("adj", "on_duty", "adj.pert", ("on_duty",))},
        {"duty": (_sense("duty", "noun", "noun.act", "work that is a paid activity"),)},
    )
    decision = apply_v6("REJECT", "on duty", "actively engaged in paid work", "adj", lexicon)
    assert decision["v6_bucket"] == "SECONDARY"
    assert decision["primary_evidence"] == NONREFERENTIAL_EVIDENCE


def test_relational_pertainym_stays_a_designation():
    lexicon = MapLex(
        {"gun bore": _entry("adj", "gun_bore", "adj.pert", ("gun_bore",))},
        {"bore": (_sense("bore", "noun", "noun.attribute", "a degree of excellence"),)},
    )
    decision = apply_v6(
        "REJECT",
        "gun bore",
        "of or relating to the bore of a gun",
        "adj",
        lexicon,
    )
    assert decision["v6_bucket"] == "REJECT"
    assert decision["primary_evidence"] is None


def test_sentence_like_naming_gloss_stays_reject():
    lexicon = MapLex(
        {"alpha force": _entry("noun", "Alpha_Force", "noun.group", ("Alpha_Force",), (("terrorist_group",),))},
        {
            "alpha": (_sense("alpha", "noun", "noun.communication", "the first letter"),),
            "force": (_sense("force", "noun", "noun.group", "a group of people"),),
        },
    )
    decision = apply_v6(
        "REJECT",
        "alpha force",
        "a violent group that seeks a separate state for its members",
        "noun",
        lexicon,
    )
    assert decision["v6_bucket"] == "REJECT"


def test_provisional_secondary_can_still_reject():
    lexicon = MapLex(
        {"alpha force": _entry("noun", "Alpha_Force", "noun.group", ("Alpha_Force",))},
        {"force": (_sense("force", "noun", "noun.group", "a group of people"),)},
    )
    decision = apply_v6("SECONDARY", "alpha force", "a named group", "noun", lexicon)
    assert decision["v6_bucket"] == "REJECT"
    assert decision["primary_evidence"] == "referential_terminological_dominance"


def test_recoverable_secondary_is_not_promoted():
    decision = apply_v6(
        "SECONDARY",
        "fully shut",
        "completely prevent entering",
        "verb",
        MapLex(
            {"fully shut": _entry("verb", "fully_shut", "verb.contact", ("fully_shut",))},
            {
                "fully": (_sense("fully", "adv", "adv.all", "completely"),),
                "shut": (_sense("shut", "verb", "verb.contact", "prevent entering"),),
            },
        ),
    )
    assert decision["v6_bucket"] == "SECONDARY"
    assert decision["primary_evidence"] is None


def test_previously_correct_is_not_bucket_immutability():
    held = assess(
        [
            {
                "surface": "still right",
                "v5_bucket": "HIGH",
                "v6_bucket": "HIGH",
                "operator_bucket": "HIGH",
                "primary_evidence": None,
                "supporting_evidence": [],
            },
            {
                "surface": "corrected",
                "v5_bucket": "REJECT",
                "v6_bucket": "SECONDARY",
                "operator_bucket": "SECONDARY",
                "primary_evidence": NONREFERENTIAL_EVIDENCE,
                "supporting_evidence": [],
            },
        ],
        phrase_specific_rule_fired=False,
        expected_rows=2,
    )
    assert held["previously_correct_lost"] == 0
    assert held["failures"] == []
    broken = assess(
        [
            {
                "surface": "was right",
                "v5_bucket": "HIGH",
                "v6_bucket": "SECONDARY",
                "operator_bucket": "HIGH",
                "primary_evidence": COMPOSITIONAL_EVIDENCE,
                "supporting_evidence": [],
            }
        ],
        phrase_specific_rule_fired=False,
        expected_rows=1,
    )
    assert broken["previously_correct_lost"] == 1
    assert broken["regression"] == "REGRESSION_FAILED"
    assert measurement_allowed(broken) is False


def test_direct_outer_swap_fails_the_gate():
    report = assess(
        [
            {
                "surface": "swapped",
                "v5_bucket": "HIGH",
                "v6_bucket": "REJECT",
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
        apply_v6("MAYBE", "fully shut", "gloss", "verb", _compositional_lex())


def test_probe_surfaces_are_not_rules():
    source = V6_PATH.read_text(encoding="utf-8")
    assert rule_surface_violations(source, PROBE_SURFACES) == []
    tree = ast.parse(source)
    assert any(isinstance(node, ast.FunctionDef) and node.name == "apply_v6" for node in ast.walk(tree))
