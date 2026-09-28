import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.unbind_screen_v4 import rule_surface_violations
from hyperlexical.unbind_sense_screen_v1 import Pointer, Synset, classify, parse_data_line

SCORER = ROOT / "scripts" / "shadow" / "hyperlexical" / "unbind_sense_screen_v1.py"
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


def test_instance_hypernym_is_referential():
    found = _class("alpha beta", "a particular named thing", _synset("n", ("alpha_beta",), (_pointer("@i"),)))
    assert found["sense_class"] == "REFERENTIAL"
    assert found["bucket"] == "REJECT"
    assert found["primary_evidence_code"] == "referential_designation"
    assert found["evidence_source"] == "synset.instance_hypernym"
    assert found["confidence_status"] == "DETERMINATE"


def test_lifespan_is_referential_and_instance_wins_when_both_fire():
    life = _class("alpha beta", "a person (1870-1949)", _synset("n", ("alpha_beta",)))
    assert life["evidence_source"] == "synset.gloss.lifespan"
    both = _class("alpha beta", "a person (1870-1949)", _synset("n", ("alpha_beta",), (_pointer("@i"),)))
    assert both["sense_class"] == "REFERENTIAL"
    assert both["evidence_source"] == "synset.instance_hypernym"


def test_year_range_without_parentheses_is_not_a_lifespan():
    found = _class("alpha beta", "a span from 1870-1949", _synset("n", ("alpha_beta",)))
    assert found["sense_class"] == "AMBIGUOUS"


def test_geographic_allusion_and_capitalization_are_not_referential():
    gloss = "a sudden turning point in a life (similar to a story on the road from one city to another)"
    found = _class(
        "path to example",
        gloss,
        _synset("n", ("Path_to_Example",), (_pointer("@", source=0),)),
    )
    assert found["sense_class"] == "AMBIGUOUS"
    assert found["bucket"] == "QUARANTINE"
    assert found["confidence_status"] == "INSUFFICIENT"


def test_technical_gloss_without_a_record_signal_stays_ambiguous():
    found = _class("sample statute", "a law about a measurement of a species", _synset("n", ("sample_statute",)))
    assert found["sense_class"] == "AMBIGUOUS"
    assert found["bucket"] == "QUARANTINE"


def test_unrelated_single_word_colemma_is_noncompositional():
    found = _class("alpha beta", "a stored predicate", _synset("v", ("alpha_beta", "exclude")))
    assert found["sense_class"] == "LEXICALIZED_NONCOMPOSITIONAL"
    assert found["bucket"] == "HIGH"
    assert found["evidence_source"] == "synset.lemmas.unrelated_single_word"


def test_constituent_and_its_exception_form_are_not_unrelated():
    bare = _class("alpha beta", "a predicate", _synset("v", ("alpha_beta", "alpha")))
    assert bare["sense_class"] == "AMBIGUOUS"
    inflected = _class(
        "alpha beta",
        "a predicate",
        _synset("v", ("alpha_beta", "alphas")),
        {"alphas": {"alpha"}, "alpha": {"alphas"}},
    )
    assert inflected["sense_class"] == "AMBIGUOUS"


def test_lexical_pointer_without_a_constituent_relation_is_ambiguous():
    found = _class(
        "alpha beta",
        "a predicate",
        _synset("v", ("alpha_beta",), (_pointer("!", source=1, target=1),)),
    )
    assert found["sense_class"] == "AMBIGUOUS"
    assert found["evidence_source"] == "none"


def test_semantic_pointer_is_not_a_lexical_unit():
    found = _class(
        "alpha beta",
        "a predicate",
        _synset("n", ("alpha_beta",), (_pointer("!", source=0, target=0),)),
    )
    assert found["sense_class"] == "AMBIGUOUS"


def test_pointer_on_the_other_lemma_does_not_count():
    found = _class(
        "alpha beta",
        "a predicate",
        _synset("v", ("alpha_beta", "gamma_delta"), (_pointer("+", source=2, target=1),)),
        targets={("n", "00000011"): ("alpha",)},
    )
    assert found["sense_class"] == "AMBIGUOUS"


def test_derivation_back_to_a_constituent_is_compositional():
    found = _class(
        "alpha beta",
        "a recoverable predicate",
        _synset("v", ("alpha_beta",), (_pointer("+", source=1, target=1, pos="v"),)),
        targets={("v", "00000011"): ("beta",)},
    )
    assert found["sense_class"] == "LEXICALIZED_COMPOSITIONAL"
    assert found["bucket"] == "SECONDARY"
    assert found["evidence_source"] == "synset.lexical_pointer.derivation_or_pertainym_to_constituent"


def test_pertainym_to_an_inflected_constituent_is_compositional():
    found = _class(
        "alpha beta",
        "a recoverable predicate",
        _synset("r", ("alpha_beta",), (_pointer("\\", source=1, target=1, pos="a"),)),
        exceptions={"betas": {"beta"}, "beta": {"betas"}},
        targets={("a", "00000011"): ("betas",)},
    )
    assert found["sense_class"] == "LEXICALIZED_COMPOSITIONAL"
    assert found["confidence_status"] == "DETERMINATE"


def test_unrelated_equivalent_overrides_a_constituent_pointer():
    found = _class(
        "alpha beta",
        "a stored predicate",
        _synset("v", ("alpha_beta", "exclude"), (_pointer("+", source=1, target=1, pos="v"),)),
        targets={("v", "00000011"): ("beta",)},
    )
    assert found["sense_class"] == "LEXICALIZED_NONCOMPOSITIONAL"


def test_one_token_alternation_is_ordinary_composition():
    found = _class(
        "as wide as needed",
        "to a feasible extent",
        _synset("r", ("as_wide_as_needed", "as_deep_as_needed")),
    )
    assert found["sense_class"] == "ORDINARY_COMPOSITIONAL"
    assert found["bucket"] == "SECONDARY"
    assert found["evidence_source"] == "synset.lemmas.productive_alternation"


def test_alternation_that_excludes_the_surface_does_not_fire():
    found = _class(
        "alpha beta gamma",
        "a predicate",
        _synset("n", ("alpha_beta_gamma", "as_wide_as_needed", "as_deep_as_needed")),
    )
    assert found["sense_class"] == "AMBIGUOUS"


def test_comparative_and_superlative_formulas_are_ordinary_composition():
    comparative = _class("alpha beta", "used to form the comparative of some words", _synset("r", ("alpha_beta",)))
    superlative = _class("alpha beta", "used to form the superlative of some words", _synset("r", ("alpha_beta",)))
    buried = _class("alpha beta", "a phrase used to form the comparative later", _synset("r", ("alpha_beta",)))
    assert comparative["sense_class"] == "ORDINARY_COMPOSITIONAL"
    assert comparative["evidence_source"] == "synset.gloss.grammatical_operator"
    assert superlative["evidence_source"] == "synset.gloss.grammatical_operator"
    assert buried["sense_class"] == "AMBIGUOUS"


def test_membership_alone_is_not_secondary():
    found = _class("alpha beta", "a listed phrase", _synset("n", ("alpha_beta",), (_pointer("@"),)))
    assert found["sense_class"] == "AMBIGUOUS"
    assert found["bucket"] == "QUARANTINE"


def test_adjective_without_a_unit_signal_is_ambiguous():
    found = _class("alpha beta", "a listed modifier", _synset("a", ("alpha_beta",)))
    assert found["sense_class"] == "AMBIGUOUS"


def test_referential_yes_conflicts_with_a_productive_frame():
    found = _class(
        "as wide as needed",
        "a particular (1870-1949)",
        _synset("r", ("as_wide_as_needed", "as_deep_as_needed"), (_pointer("@i"),)),
    )
    assert found["sense_class"] == "AMBIGUOUS"
    assert found["bucket"] == "QUARANTINE"


def test_unit_yes_and_no_conflict():
    found = _class(
        "as wide as needed",
        "to a feasible extent",
        _synset("r", ("as_wide_as_needed", "as_deep_as_needed", "exclude")),
    )
    assert found["sense_class"] == "AMBIGUOUS"


def test_hyphen_and_underscore_count_as_the_same_lemma():
    found = _class(
        "full of the moon",
        "a listed name",
        _synset("n", ("full-of-the-moon",)),
    )
    assert found["sense_class"] == "AMBIGUOUS"


def test_high_ambiguity_is_left_in_place():
    rows = [
        _class(f"item {index}", "a listed phrase", _synset("n", (f"item_{index}",)))
        for index in range(5)
    ]
    assert [row["sense_class"] for row in rows] == ["AMBIGUOUS"] * 5
    assert [row["bucket"] for row in rows] == ["QUARANTINE"] * 5


def test_data_line_parser_keeps_hex_word_numbers_and_stops_before_frames():
    line = "00013172 29 v 01 bungle 0 003 @ 00010435 v 0000 + 00074790 n 0104 + 09879744 n 0101 01 + 02 00 | spoil by behaving clumsily"
    synset, gloss = parse_data_line(line)
    assert gloss == "spoil by behaving clumsily"
    assert synset.lemmas == ("bungle",)
    assert len(synset.pointers) == 3
    assert synset.pointers[1].symbol == "+"
    assert synset.pointers[1].source == 1
    assert synset.pointers[1].target == 4
    wide = (
        "00002137 03 n 02 abstraction 0 abstract_entity 0 010 "
        "@ 00001740 n 0000 + 00692329 v 0101 ~ 00023100 n 0000 ~ 00024264 n 0000 "
        "~ 00031264 n 0000 ~ 00031921 n 0000 ~ 00033020 n 0000 ~ 00033615 n 0000 "
        "~ 05810143 n 0000 ~ 07999699 n 0000 | a general concept"
    )
    parsed_wide, _gloss = parse_data_line(wide)
    assert len(parsed_wide.pointers) == 10
    assert parsed_wide.pointers[1].symbol == "+"
    assert parsed_wide.pointers[1].source == 1
    assert parsed_wide.pointers[1].target == 1
    lifespan = "00000001 11 n 01 alpha_beta 0 001 @ 00000002 n 0000 | a made example (1900-1910); extra"
    parsed, first = parse_data_line(lifespan)
    found = _class("alpha beta", first, parsed)
    assert found["sense_class"] == "REFERENTIAL"
    assert found["evidence_source"] == "synset.gloss.lifespan"


def test_probe_surfaces_are_not_rules():
    source = SCORER.read_text(encoding="utf-8")
    assert rule_surface_violations(source, PROBES) == []
