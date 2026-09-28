import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.unbind_screen_v3 import screen
from hyperlexical.unbind_screen_v4 import (
    EmptyLexicon,
    ScreenV4Error,
    apply_v4,
    assess,
    measurement_allowed,
    normalize_lexical,
    rule_surface_violations,
)

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
)
V3_PATH = ROOT / "scripts" / "shadow" / "hyperlexical" / "unbind_screen_v3.py"
V4_PATH = ROOT / "scripts" / "shadow" / "hyperlexical" / "unbind_screen_v4.py"


class MapLex:
    def __init__(self, nouns, adjectives=()):
        self._nouns = nouns
        self._adjectives = set(adjectives)

    def noun_lex(self, lemma):
        return self._nouns.get(lemma)

    def has_adjective(self, lemma):
        return lemma in self._adjectives


class BoomLex:
    def noun_lex(self, lemma):
        raise AssertionError(lemma)

    def has_adjective(self, lemma):
        raise AssertionError(lemma)


def test_normalization_folds_hyphen_and_keeps_apostrophe():
    assert normalize_lexical("Seventy-Five") == normalize_lexical("seventy five")
    assert normalize_lexical("one-hundred") == normalize_lexical("one hundred")
    assert "'" in normalize_lexical("one's birthday")


def test_v3_number_grammar_does_not_fold_a_hyphen():
    bucket, _rule, _phase = screen("forty-two fifty", "adj", ["forty-two", "fifty"], "a count")
    assert bucket == "SECONDARY"


def test_v3_spaced_number_still_rejects():
    bucket, rule, _phase = screen("forty two", "adj", ["forty", "two"], "a count")
    assert bucket == "REJECT"
    assert rule == "productive_numeric_expression"


def test_v4_folds_hyphenated_numbers_only_from_secondary():
    moved = apply_v4("SECONDARY", "forty-two fifty", "a count", "adj", EmptyLexicon())
    assert moved["v4_bucket"] == "REJECT"
    assert moved["primary_evidence"] == "productive_number"
    assert moved["inspected"] is True
    held = apply_v4("HIGH_VALUE", "forty-two fifty", "a count", "adj", BoomLex())
    assert held["v4_bucket"] == "HIGH"
    assert held["primary_evidence"] is None
    assert held["inspected"] is False
    rejected = apply_v4("REJECT", "four times", "by a factor of four", "adv", BoomLex())
    assert rejected["v4_bucket"] == "REJECT"
    assert rejected["inspected"] is False


def test_multiplier_is_a_productive_number():
    moved = apply_v4("SECONDARY", "four times", "by a factor of four", "adv", EmptyLexicon())
    assert moved["v4_bucket"] == "REJECT"
    assert moved["primary_evidence"] == "productive_number"
    assert moved["supporting_evidence"] == []


def test_comparative_particle_stays_secondary_and_shifted_particle_promotes():
    stayed = apply_v4("SECONDARY", "better off", "in a more fortunate condition", "adj", EmptyLexicon())
    assert stayed["v4_bucket"] == "SECONDARY"
    assert stayed["primary_evidence"] is None
    promoted = apply_v4("SECONDARY", "zorp up", "having a strong distaste", "adj", EmptyLexicon())
    assert promoted["v4_bucket"] == "HIGH"
    assert promoted["primary_evidence"] == "noncompositional_phrasal_binding"


def test_literal_particle_with_stem_overlap_stays():
    stayed = apply_v4("SECONDARY", "flare out", "become flared and widen", "verb", EmptyLexicon())
    assert stayed["v4_bucket"] == "SECONDARY"


def test_patch_b_frames_are_classes():
    cases = [
        ("strike the ceiling", "get very angry", "verb", "nonliteral_semantic_shift"),
        ("like a flash", "without delay", "adv", "conventionalized_idiom"),
        ("sure as sunrise", "absolutely certain", "adj", "conventionalized_idiom"),
        ("for all practical senses", "in every practical way", "adv", "conventionalized_idiom"),
        ("give it a whirl", "whirl", "verb", "conventionalized_idiom"),
        ("spin on a coin", "have a small turning radius", "verb", "nonliteral_semantic_shift"),
        ("in the civic gaze", "of great interest to the civic world", "adj", "nonliteral_semantic_shift"),
        ("stone cold", "without heat", "adj", "fixed_lexicalized_expression"),
        ("cooked for finished", "destroyed", "adj", "fixed_lexicalized_expression"),
        ("blip a zorp", "show nothing", "verb", "nonliteral_semantic_shift"),
    ]
    for surface, gloss, pos, evidence in cases:
        moved = apply_v4("SECONDARY", surface, gloss, pos, EmptyLexicon())
        assert moved["v4_bucket"] == "HIGH", surface
        assert moved["primary_evidence"] == evidence, surface
        assert moved["primary_evidence"] not in moved["supporting_evidence"]


def test_patch_a_uses_gloss_lexfile_not_the_surface_string():
    person = apply_v4(
        "SECONDARY",
        "alice brooke carter",
        "Scottish physiologist and sibling",
        "noun",
        MapLex({"scottish": "noun.person", "physiologist": "noun.person"}, {"scottish"}),
    )
    assert person["primary_evidence"] == "multi_token_person_name"
    role = apply_v4(
        "SECONDARY",
        "sneak thief",
        "a thief who steals",
        "noun",
        MapLex({"thief": "noun.person"}),
    )
    assert role["v4_bucket"] == "SECONDARY"
    species = apply_v4(
        "SECONDARY",
        "ribbon lemur",
        "Indian macaque with a tuft",
        "noun",
        MapLex({"indian": "noun.person", "macaque": "noun.animal"}, {"indian"}),
    )
    assert species["primary_evidence"] == "species_or_common_name_referent"
    organization = apply_v4(
        "SECONDARY",
        "warden of the seal",
        "a small gang of fighters",
        "noun",
        MapLex({"small": "noun.cognition", "gang": "noun.group"}, {"small"}),
    )
    assert organization["primary_evidence"] == "organization_from_gloss"
    medical = apply_v4(
        "SECONDARY",
        "separation of the choroid",
        "visual impairment resulting from the retina becoming separated",
        "noun",
        MapLex(
            {
                "impairment": "noun.event",
                "retina": "noun.body",
                "choroid": "noun.body",
                "eye": "noun.body",
            },
            {"visual"},
        ),
    )
    assert medical["primary_evidence"] == "medical_technical_expression"


def test_scorer_source_has_no_probe_surface_or_phrase_literal():
    for path in (V3_PATH, V4_PATH):
        source = path.read_text(encoding="utf-8")
        assert rule_surface_violations(source, PROBE_SURFACES) == []
        tree = ast.parse(source)
        constants = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        for phrase in PROBE_SURFACES:
            assert phrase not in constants
            assert phrase not in source


def test_gate_passes_only_lawful_secondary_moves():
    rows = [
        _replay("alpha beta", "HIGH", "HIGH", "HIGH"),
        _replay("gamma delta", "REJECT", "REJECT", "REJECT"),
        _replay("epsilon zeta", "SECONDARY", "HIGH", "HIGH", "conventionalized_idiom"),
        _replay("eta theta", "SECONDARY", "REJECT", "REJECT", "productive_number"),
        _replay("iota kappa", "SECONDARY", "SECONDARY", "SECONDARY"),
    ]
    report = assess(rows, phrase_specific_rule_fired=False, expected_rows=5)
    assert report["regression"] == "REGRESSION_VERIFIED"
    assert report["failures"] == []
    assert measurement_allowed(report) is True
    broken = list(rows)
    broken[0] = _replay("alpha beta", "HIGH", "SECONDARY", "HIGH")
    failed = assess(broken, phrase_specific_rule_fired=False, expected_rows=5)
    assert failed["regression"] == "REGRESSION_FAILED"
    assert measurement_allowed(failed) is False
    wrong_patch = list(rows)
    wrong_patch[2] = _replay("epsilon zeta", "SECONDARY", "HIGH", "HIGH", "productive_number")
    assert assess(wrong_patch, phrase_specific_rule_fired=False, expected_rows=5)["regression"] == "REGRESSION_FAILED"
    phrase = assess(rows, phrase_specific_rule_fired=True, expected_rows=5)
    assert phrase["regression"] == "REGRESSION_FAILED"
    assert phrase["phrase_specific_rule_fired"] is True


def test_unknown_bucket_is_refused():
    with pytest.raises(ScreenV4Error):
        apply_v4("MAYBE", "alpha beta", "gloss", "noun", EmptyLexicon())


def _replay(surface, v3, v4, operator, primary=None):
    return {
        "surface": surface,
        "v3_bucket": v3,
        "v4_bucket": v4,
        "operator_bucket": operator,
        "primary_evidence": primary,
        "supporting_evidence": [],
    }
