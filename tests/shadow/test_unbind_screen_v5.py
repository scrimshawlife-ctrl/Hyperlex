import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.unbind_screen_v5 import (
    EmptyLexicon,
    Entry,
    Sense,
    apply_v5,
    assess,
    measurement_allowed,
)
from hyperlexical.unbind_screen_v4 import rule_surface_violations

PROBE_SURFACES = (
    "hit the roof",
    "get it on",
    "like a shot",
    "fed up",
    "taken for granted",
    "turn on a dime",
    "in the public eye",
    "bonnet monkey",
    "john scott haldane",
    "bearer of the sword",
    "detachment of the retina",
    "three times",
    "one hundred seventy-five",
    "on the go",
    "flat out",
    "in the way",
    "to a t",
    "slip of the tongue",
    "run low",
    ".22 caliber",
    "phi correlation",
    "blue-eyed african daisy",
    "monoamine oxidase inhibitor",
    "air force research laboratory",
    "martin luther king jr's birthday",
)
V5_PATH = ROOT / "scripts" / "shadow" / "hyperlexical" / "unbind_screen_v5.py"


class BoomLex:
    def entry(self, surface):
        raise AssertionError(surface)

    def senses(self, token):
        raise AssertionError(token)


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


def test_outer_buckets_pass_through_without_inspection():
    high = apply_v5("HIGH_VALUE", "alpha beta", "gloss", "noun", BoomLex())
    assert high["v5_bucket"] == "HIGH"
    assert high["v4_bucket"] == "HIGH"
    assert high["primary_evidence"] is None
    assert high["inspected"] is False
    rejected = apply_v5("REJECT", "gamma delta", "gloss", "noun", BoomLex())
    assert rejected["v5_bucket"] == "REJECT"
    assert rejected["inspected"] is False
    assert rejected["supporting_evidence"] == []


def test_proper_name_and_pertainym_designate():
    named = MapLex(
        {"north example laboratory": _entry("noun", "North_Example_Laboratory", "noun.artifact", ("North_Example_Laboratory",))},
        {},
    )
    moved = apply_v5("SECONDARY", "north example laboratory", "a workplace", "noun", named)
    assert moved["v5_bucket"] == "REJECT"
    assert moved["primary_evidence"] == "referential_terminological_dominance"
    pert = MapLex(
        {"sample bore": _entry("adj", "sample_bore", "adj.pert", ("sample_bore",))},
        {"sample": (_sense("sample", "noun", "noun.artifact", "an illustrative item"),),
         "bore": (_sense("bore", "noun", "noun.attribute", "a grade of excellence"),)},
    )
    designated = apply_v5("SECONDARY", "sample bore", "of or relating to a measured width", "adj", pert)
    assert designated["v5_bucket"] == "REJECT"
    assert designated["supporting_evidence"] == []


def test_exocentric_life_form_rejects_and_endocentric_life_form_stays():
    exo = MapLex(
        {"sample bloom": _entry("noun", "sample_bloom", "noun.plant", ("sample_bloom",), (("flower",),))},
        {"sample": (_sense("sample", "noun", "noun.artifact", "an illustrative item"),),
         "bloom": (_sense("bloom", "noun", "noun.plant", "a flower of a plant"),)},
    )
    # constituent gloss repeats flower, so this row is recoverable and must not use that overlap
    # to avoid designation. Designation is decided from the synset, before recoverability.
    assert apply_v5("SECONDARY", "sample bloom", "a perennial herb", "noun", exo)["v5_bucket"] == "REJECT"
    endo = MapLex(
        {"sample tree": _entry("noun", "sample_tree", "noun.plant", ("sample_tree",), (("tree",),))},
        {"sample": (_sense("sample", "adj", "adj.all", "illustrative"),),
         "tree": (_sense("tree", "noun", "noun.plant", "a tall woody plant"),)},
    )
    stayed = apply_v5("SECONDARY", "sample tree", "a tall woody plant of the sample kind", "noun", endo)
    assert stayed["v5_bucket"] == "SECONDARY"
    assert stayed["primary_evidence"] is None


def test_compound_category_rejects_unless_an_ordinary_synonym_is_present():
    term = MapLex(
        {"phi index": _entry(
            "noun", "phi_index", "noun.cognition", ("phi_index",), (("nonparametric_statistic",),)
        )},
        {"phi": (_sense("phi", "noun", "noun.communication", "a letter of an alphabet"),),
         "index": (_sense("index", "noun", "noun.relation", "a numerical scale"),)},
    )
    assert apply_v5("SECONDARY", "phi index", "a statistic of agreement", "noun", term)["primary_evidence"] == "referential_terminological_dominance"
    goods = MapLex(
        {"sample goods": _entry(
            "noun", "sample_goods", "noun.artifact", ("sample_goods", "haberdashery"), (("soft_goods",),)
        )},
        {"sample": (_sense("sample", "noun", "noun.artifact", "an illustrative item"),),
         "goods": (_sense("goods", "noun", "noun.artifact", "articles of commerce"),)},
    )
    stayed = apply_v5("SECONDARY", "sample goods", "articles of commerce", "noun", goods)
    assert stayed["v5_bucket"] == "SECONDARY"


def test_adverb_idiom_promotes_and_recoverable_adverb_stays():
    idiom = MapLex(
        {"blip out": _entry("adv", "blip_out", "adv.all", ("blip_out", "brusquely"))},
        {"blip": (_sense("blip", "noun", "noun.event", "a small mark on a screen"),),
         "out": (_sense("out", "adv", "adv.all", "away from the inside"),)},
    )
    moved = apply_v5("SECONDARY", "blip out", "in a blunt manner", "adv", idiom)
    assert moved["v5_bucket"] == "HIGH"
    assert moved["primary_evidence"] == "lexicalized_noncompositional"
    plain = MapLex(
        {"as common": _entry("adv", "as_common", "adv.all", ("as_common", "commonly"))},
        {"common": (_sense("common", "adj", "adj.all", "occurring in the common manner"),)},
    )
    stayed = apply_v5("SECONDARY", "as common", "in the common manner", "adv", plain)
    assert stayed["v5_bucket"] == "SECONDARY"


def test_orthography_body_and_verb_shift_are_noncompositional():
    ortho = MapLex(
        {"to a q": _entry("adv", "to_a_q", "adv.all", ("to_a_q", "to_the_letter"))},
        {},
    )
    assert apply_v5("SECONDARY", "to a q", "in every respect", "adv", ortho)["v5_bucket"] == "HIGH"
    body = MapLex(
        {"slip of the digit": _entry("noun", "slip_of_the_digit", "noun.communication", ("slip_of_the_digit",))},
        {"slip": (_sense("slip", "noun", "noun.act", "a socially awkward act"),),
         "digit": (_sense("digit", "noun", "noun.body", "a finger or toe"),)},
    )
    assert apply_v5("SECONDARY", "slip of the digit", "an accidental mistake in counting", "noun", body)["v5_bucket"] == "HIGH"
    shifted = MapLex(
        {"dwindle low": _entry("verb", "dwindle_low", "verb.consumption", ("dwindle_low",))},
        {"dwindle": (_sense("dwindle", "verb", "verb.motion", "move fast on foot"),),
         "low": (_sense("low", "adj", "adj.all", "not high"),)},
    )
    assert apply_v5("SECONDARY", "dwindle low", "to be spent or finished", "verb", shifted)["v5_bucket"] == "HIGH"
    same = MapLex(
        {"nudge at": _entry("verb", "nudge_at", "verb.contact", ("nudge_at", "prod"))},
        {"nudge": (_sense("nudge", "verb", "verb.contact", "poke or thrust abruptly"),)},
    )
    assert apply_v5("SECONDARY", "nudge at", "to push against gently", "verb", same)["v5_bucket"] == "SECONDARY"


def test_metalinguistic_reduplication_and_missing_lemma_stay():
    discourse = MapLex(
        {"by the quip": _entry("adv", "by_the_quip", "adv.all", ("by_the_quip", "incidentally"))},
        {"quip": (_sense("quip", "noun", "noun.communication", "a witty remark"),)},
    )
    assert apply_v5("SECONDARY", "by the quip", "introducing a different topic", "adv", discourse)["v5_bucket"] == "SECONDARY"
    repeated = MapLex(
        {"plink by plink": _entry("adv", "plink_by_plink", "adv.all", ("plink_by_plink", "gradually"))},
        {"plink": (_sense("plink", "noun", "noun.event", "a short sound"),)},
    )
    assert apply_v5("SECONDARY", "plink by plink", "in a gradual manner", "adv", repeated)["v5_bucket"] == "SECONDARY"
    loan = MapLex(
        {"al zorp": _entry("adj", "al_zorp", "adj.all", ("al_zorp",))},
        {"al": (_sense("al", "noun", "noun.substance", "a metallic element"),)},
    )
    assert apply_v5("SECONDARY", "al zorp", "of pasta cooked firm", "adj", loan)["v5_bucket"] == "SECONDARY"


def test_unknown_surface_stays_secondary():
    stayed = apply_v5("SECONDARY", "brand new coinage", "a fresh phrase", "noun", EmptyLexicon())
    assert stayed["v5_bucket"] == "SECONDARY"
    assert stayed["primary_evidence"] is None
    assert stayed["inspected"] is True


def test_scorer_source_has_no_probe_surface_or_phrase_literal():
    source = V5_PATH.read_text(encoding="utf-8")
    assert rule_surface_violations(source, PROBE_SURFACES) == []
    tree = ast.parse(source)
    constants = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    for phrase in PROBE_SURFACES:
        assert phrase not in source
        assert phrase not in constants


def test_gate_passes_only_lawful_secondary_moves():
    rows = [
        _replay("alpha beta", "HIGH", "HIGH", "HIGH"),
        _replay("gamma delta", "REJECT", "REJECT", "REJECT"),
        _replay("epsilon zeta", "SECONDARY", "HIGH", "HIGH", "lexicalized_noncompositional"),
        _replay("eta theta", "SECONDARY", "REJECT", "REJECT", "referential_terminological_dominance"),
        _replay("iota kappa", "SECONDARY", "SECONDARY", "SECONDARY"),
    ]
    report = assess(rows, phrase_specific_rule_fired=False, expected_rows=5)
    assert report["regression"] == "REGRESSION_VERIFIED"
    assert report["failures"] == []
    assert report["operator_conflict_on_move"] == 0
    assert measurement_allowed(report) is True
    broken = list(rows)
    broken[0] = _replay("alpha beta", "HIGH", "SECONDARY", "HIGH")
    failed = assess(broken, phrase_specific_rule_fired=False, expected_rows=5)
    assert failed["regression"] == "REGRESSION_FAILED"
    assert measurement_allowed(failed) is False
    conflict = list(rows)
    conflict[2] = _replay("epsilon zeta", "SECONDARY", "HIGH", "SECONDARY", "lexicalized_noncompositional")
    assert assess(conflict, phrase_specific_rule_fired=False, expected_rows=5)["operator_conflict_on_move"] == 1
    phrase = assess(rows, phrase_specific_rule_fired=True, expected_rows=5)
    assert phrase["regression"] == "REGRESSION_FAILED"


def test_unknown_bucket_is_refused():
    with pytest.raises(Exception):
        apply_v5("MAYBE", "alpha beta", "gloss", "noun", EmptyLexicon())


def _replay(surface, prior, nxt, operator, primary=None):
    return {
        "surface": surface,
        "v4_bucket": prior,
        "v5_bucket": nxt,
        "operator_bucket": operator,
        "primary_evidence": primary,
        "supporting_evidence": [],
    }
