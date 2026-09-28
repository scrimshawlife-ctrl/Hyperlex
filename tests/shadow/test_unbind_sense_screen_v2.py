import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.unbind_screen_v4 import rule_surface_violations
from hyperlexical.unbind_sense_screen_v2 import Pointer, Synset, classify, parse_data_line

SCORER = ROOT / "scripts" / "shadow" / "hyperlexical" / "unbind_sense_screen_v2.py"
PROBES = (
    "road to damascus",
    "as far as possible",
    "independent state of papua new guinea",
    "full phase of the moon",
    "union jack",
    "atomic number 98",
    "law of definite proportions",
    "round the bend",
    "throw in the towel",
    "flip one's lid",
    "luck through",
    "now and then",
)


def _synset(ss_type, lemmas, pointers=()):
    return Synset("00000000", ss_type, tuple(lemmas), tuple(pointers))


def _pointer(symbol, source=0, target=0, offset="00000011", pos="n"):
    return Pointer(symbol, offset, pos, source, target)


def _class(surface, gloss, synset, exceptions=None, targets=None):
    return classify(surface, gloss, synset, exceptions or {}, targets or {})


def test_instance_hypernym_is_referential_and_wins_over_a_colemma():
    found = _class(
        "alpha beta",
        "a particular named thing",
        _synset("n", ("alpha_beta", "exclude"), (_pointer("@i"),)),
    )
    assert found["referential_state"] == "YES"
    assert found["lexicalized_state"] == "YES"
    assert found["sense_class"] == "REFERENTIAL"
    assert found["bucket"] == "REJECT"
    assert found["primary_evidence_code"] == "referential_designation"
    assert found["evidence_sources"][0] == "synset.instance_hypernym"
    assert "whole_expression_lexicalization" in found["supporting_evidence_codes"]
    assert found["confidence_status"] == "DETERMINATE"


def test_lifespan_is_referential_until_an_instance_pointer_is_also_present():
    life = _class("alpha beta", "a person (1870-1949)", _synset("n", ("alpha_beta",)))
    assert life["evidence_sources"][0] == "synset.gloss.lifespan"
    both = _class(
        "alpha beta",
        "a person (1870-1949)",
        _synset("n", ("alpha_beta",), (_pointer("@i"),)),
    )
    assert both["evidence_sources"][0] == "synset.instance_hypernym"


def test_year_range_without_parentheses_is_not_referential():
    found = _class("alpha beta", "a span from 1870-1949", _synset("n", ("alpha_beta",)))
    assert found["referential_state"] == "UNKNOWN"
    assert found["sense_class"] == "AMBIGUOUS"


def test_allusion_and_capitalization_are_not_referential():
    gloss = "a sudden turning point in a life (similar to a story on the road from one city to another)"
    found = _class("path to example", gloss, _synset("n", ("Path_to_Example",), (_pointer("@", source=0),)))
    assert found["referential_state"] == "UNKNOWN"
    assert found["lexicalized_state"] == "UNKNOWN"
    assert found["compositional_state"] == "UNKNOWN"
    assert found["sense_class"] == "AMBIGUOUS"
    assert found["bucket"] == "QUARANTINE"


def test_technical_gloss_stays_ambiguous():
    found = _class("sample statute", "a law about a measurement of a species", _synset("n", ("sample_statute",)))
    assert found["sense_class"] == "AMBIGUOUS"
    assert found["bucket"] == "QUARANTINE"


def test_colemma_is_lexicalized_yes_and_not_high():
    found = _class("alpha beta", "a stored predicate", _synset("v", ("alpha_beta", "exclude")))
    assert found["lexicalized_state"] == "YES"
    assert found["compositional_state"] == "UNKNOWN"
    assert found["compositional_state"] != "NO"
    assert found["sense_class"] == "AMBIGUOUS"
    assert found["bucket"] == "QUARANTINE"
    assert found["primary_evidence_code"] == "insufficient_record_evidence"
    assert found["supporting_evidence_codes"] == ["whole_expression_lexicalization"]
    assert found["evidence_sources"] == ["synset.lemmas.unrelated_single_word"]
    assert found["confidence_status"] == "INSUFFICIENT"


def test_constituent_and_its_inflection_are_not_an_unrelated_colemma():
    bare = _class("alpha beta", "a predicate", _synset("v", ("alpha_beta", "alpha")))
    inflected = _class(
        "alpha beta",
        "a predicate",
        _synset("v", ("alpha_beta", "alphas")),
        {"alphas": {"alpha"}, "alpha": {"alphas"}},
    )
    assert bare["lexicalized_state"] == "UNKNOWN"
    assert inflected["lexicalized_state"] == "UNKNOWN"


def test_lexical_pointer_without_a_constituent_relation_stays_ambiguous():
    found = _class(
        "alpha beta",
        "a predicate",
        _synset("v", ("alpha_beta",), (_pointer("!", source=1, target=1),)),
    )
    assert found["lexicalized_state"] == "YES"
    assert found["compositional_state"] == "UNKNOWN"
    assert found["sense_class"] == "AMBIGUOUS"
    assert found["bucket"] == "QUARANTINE"


def test_semantic_pointer_and_a_pointer_on_another_lemma_do_not_lexicalize():
    semantic = _class(
        "alpha beta",
        "a predicate",
        _synset("n", ("alpha_beta",), (_pointer("!", source=0, target=0),)),
    )
    other = _class(
        "alpha beta",
        "a predicate",
        _synset("v", ("alpha_beta", "gamma_delta"), (_pointer("+", source=2, target=1),)),
        targets={("n", "00000011"): ("alpha",)},
    )
    assert semantic["lexicalized_state"] == "UNKNOWN"
    assert other["lexicalized_state"] == "UNKNOWN"
    assert other["compositional_state"] == "UNKNOWN"


def test_constituent_derivation_is_lexicalized_compositional():
    found = _class(
        "alpha beta",
        "a recoverable predicate",
        _synset("v", ("alpha_beta",), (_pointer("+", source=1, target=1, pos="v"),)),
        targets={("v", "00000011"): ("beta",)},
    )
    assert found["lexicalized_state"] == "YES"
    assert found["compositional_state"] == "YES"
    assert found["sense_class"] == "LEXICALIZED_COMPOSITIONAL"
    assert found["bucket"] == "SECONDARY"
    assert found["primary_evidence_code"] == "compositional_semantic_relation"
    assert found["supporting_evidence_codes"] == ["whole_expression_lexicalization"]
    assert found["evidence_sources"][0] == "synset.lexical_pointer.derivation_or_pertainym_to_constituent"


def test_pertainym_to_an_inflected_constituent_is_compositional():
    found = _class(
        "alpha beta",
        "a recoverable predicate",
        _synset("r", ("alpha_beta",), (_pointer("\\", source=1, target=1, pos="a"),)),
        exceptions={"betas": {"beta"}, "beta": {"betas"}},
        targets={("a", "00000011"): ("betas",)},
    )
    assert found["sense_class"] == "LEXICALIZED_COMPOSITIONAL"
    assert found["referential_state"] == "NO"


def test_colemma_plus_constituent_is_secondary_not_high():
    found = _class(
        "alpha beta",
        "a stored predicate",
        _synset("v", ("alpha_beta", "exclude"), (_pointer("+", source=1, target=1, pos="v"),)),
        targets={("v", "00000011"): ("beta",)},
    )
    assert found["lexicalized_state"] == "YES"
    assert found["compositional_state"] == "YES"
    assert found["sense_class"] == "LEXICALIZED_COMPOSITIONAL"
    assert found["bucket"] == "SECONDARY"


def test_colemma_plus_alternation_is_lexicalized_compositional():
    found = _class(
        "as wide as needed",
        "to a feasible extent",
        _synset("r", ("as_wide_as_needed", "as_deep_as_needed", "exclude")),
    )
    assert found["referential_state"] == "NO"
    assert found["lexicalized_state"] == "YES"
    assert found["compositional_state"] == "YES"
    assert found["sense_class"] == "LEXICALIZED_COMPOSITIONAL"
    assert found["primary_evidence_code"] == "productive_grammatical_frame"
    assert "whole_expression_lexicalization" in found["supporting_evidence_codes"]


def test_alternation_alone_is_compositional_yes_and_ambiguous():
    found = _class(
        "as wide as needed",
        "to a feasible extent",
        _synset("r", ("as_wide_as_needed", "as_deep_as_needed")),
    )
    assert found["referential_state"] == "NO"
    assert found["lexicalized_state"] == "UNKNOWN"
    assert found["compositional_state"] == "YES"
    assert found["sense_class"] == "AMBIGUOUS"
    assert found["bucket"] == "QUARANTINE"
    assert found["supporting_evidence_codes"] == ["productive_grammatical_frame"]


def test_alternation_that_excludes_the_surface_does_not_fire():
    found = _class(
        "alpha beta gamma",
        "a predicate",
        _synset("n", ("alpha_beta_gamma", "as_wide_as_needed", "as_deep_as_needed")),
    )
    assert found["compositional_state"] == "UNKNOWN"
    assert found["sense_class"] == "AMBIGUOUS"


def test_operator_gloss_is_ordinary_composition():
    comparative = _class("alpha beta", "used to form the comparative of some words", _synset("r", ("alpha_beta",)))
    superlative = _class("alpha beta", "used to form the superlative of some words", _synset("r", ("alpha_beta",)))
    buried = _class("alpha beta", "a phrase used to form the comparative later", _synset("r", ("alpha_beta",)))
    assert comparative["lexicalized_state"] == "NO"
    assert comparative["compositional_state"] == "YES"
    assert comparative["sense_class"] == "ORDINARY_COMPOSITIONAL"
    assert comparative["bucket"] == "SECONDARY"
    assert comparative["primary_evidence_code"] == "productive_grammatical_frame"
    assert comparative["evidence_sources"][0] == "synset.gloss.grammatical_operator"
    assert superlative["sense_class"] == "ORDINARY_COMPOSITIONAL"
    assert buried["sense_class"] == "AMBIGUOUS"
    assert buried["lexicalized_state"] == "UNKNOWN"


def test_operator_gloss_plus_colemma_conflicts_and_is_not_high():
    found = _class(
        "alpha beta",
        "used to form the comparative of some words",
        _synset("r", ("alpha_beta", "exclude")),
    )
    assert found["lexicalized_state"] == "CONFLICT"
    assert found["sense_class"] == "AMBIGUOUS"
    assert found["bucket"] == "QUARANTINE"
    assert found["primary_evidence_code"] == "conflicting_record_evidence"
    assert found["confidence_status"] == "CONTRADICTORY"


def test_membership_alone_is_not_secondary_or_high():
    noun = _class("alpha beta", "a listed phrase", _synset("n", ("alpha_beta",), (_pointer("@"),)))
    adjective = _class("alpha beta", "a listed modifier", _synset("a", ("alpha_beta",)))
    assert noun["referential_state"] == "UNKNOWN"
    assert noun["sense_class"] == "AMBIGUOUS"
    assert noun["evidence_sources"] == ["none"]
    assert adjective["referential_state"] == "NO"
    assert adjective["sense_class"] == "AMBIGUOUS"


def test_instance_pointer_on_an_alternation_stays_referential():
    found = _class(
        "as wide as needed",
        "a particular (1870-1949)",
        _synset("r", ("as_wide_as_needed", "as_deep_as_needed"), (_pointer("@i"),)),
    )
    assert found["referential_state"] == "YES"
    assert found["compositional_state"] == "YES"
    assert found["sense_class"] == "REFERENTIAL"
    assert found["bucket"] == "REJECT"


def test_hyphen_and_underscore_count_as_the_same_lemma():
    found = _class("full of the moon", "a listed name", _synset("n", ("full-of-the-moon",)))
    assert found["sense_class"] == "AMBIGUOUS"


def test_colemma_rows_are_not_repaired_into_high():
    rows = [
        _class(f"item {index}", "a listed phrase", _synset("n", (f"item_{index}", "exclude")))
        for index in range(5)
    ]
    assert [row["sense_class"] for row in rows] == ["AMBIGUOUS"] * 5
    assert [row["bucket"] for row in rows] == ["QUARANTINE"] * 5
    assert [row["compositional_state"] for row in rows] == ["UNKNOWN"] * 5


def test_decimal_pointer_count_stops_before_frames():
    line = "00013172 29 v 01 bungle 0 003 @ 00010435 v 0000 + 00074790 n 0104 + 09879744 n 0101 01 + 02 00 | spoil by behaving clumsily"
    synset, gloss = parse_data_line(line)
    assert len(synset.pointers) == 3
    wide = (
        "00002137 03 n 02 abstraction 0 abstract_entity 0 010 "
        "@ 00001740 n 0000 + 00692329 v 0101 ~ 00023100 n 0000 ~ 00024264 n 0000 "
        "~ 00031264 n 0000 ~ 00031921 n 0000 ~ 00033020 n 0000 ~ 00033615 n 0000 "
        "~ 05810143 n 0000 ~ 07999699 n 0000 | a general concept"
    )
    parsed, _gloss = parse_data_line(wide)
    assert len(parsed.pointers) == 10
    found = _class("alpha beta", gloss, synset)
    assert found["compositional_state"] == "UNKNOWN"


def test_probe_surfaces_are_not_rules():
    source = SCORER.read_text(encoding="utf-8")
    assert rule_surface_violations(source, PROBES) == []
