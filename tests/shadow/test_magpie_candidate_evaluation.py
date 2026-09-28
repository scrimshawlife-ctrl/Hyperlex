import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.magpie_candidate_evaluation import (
    ALIGNED_IDIOMATIC,
    ALIGNED_LITERAL,
    AMBIGUOUS,
    CONFLICT,
    EXACT,
    MIXED,
    NONE,
    NORMALIZED,
    UNKNOWN,
    build_index,
    evaluate_row,
    exact_key,
    normalized_key,
    semantic_noncompositional,
)
from hyperlexical.unbind_screen_v4 import rule_surface_violations

MODULE = ROOT / "scripts" / "shadow" / "hyperlexical" / "magpie_candidate_evaluation.py"
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
VERSION = "test-version"
ARTIFACT = "b" * 64


def _instance(identifier, idiom, label="i", variant_type="identical", confidence=1, **extra):
    row = {
        "confidence": confidence,
        "id": identifier,
        "idiom": idiom,
        "label": label,
        "variant_type": variant_type,
    }
    row.update(extra)
    return row


def _row(surface, synset, instances):
    return evaluate_row(surface, synset, build_index(instances), VERSION, ARTIFACT)


def test_module_has_no_phrase_exception_or_probe_surface():
    assert rule_surface_violations(MODULE.read_text(encoding="utf-8"), PROBES) == []


def test_evaluator_does_not_accept_operator_labels_or_gloss():
    names = set(inspect.signature(evaluate_row).parameters)
    assert "operator_bucket" not in names
    assert "gloss" not in names
    assert "operator_reason" not in names


def test_exact_match_is_case_and_separator_only():
    found = _row(
        "At The End",
        "noun:1",
        [_instance(1, "at the end", "i"), _instance(2, "at the end", "l")],
    )
    assert found["surface_match"] == EXACT
    assert found["matched_magpie_expression"] == "at the end"
    assert found["idiomatic_instance_count"] == 1
    assert found["literal_instance_count"] == 1
    assert found["sense_alignment"] == UNKNOWN
    assert found["semantic_noncompositional"] == UNKNOWN
    assert found["primary_evidence_code"] == "magpie_surface_only"
    assert found["source_instance_ids"] == [1, 2]


def test_punctuation_difference_is_normalized_and_not_yes():
    found = _row("end of the day", "noun:1", [_instance(4, "end of the day.")])
    assert exact_key("end of the day") != exact_key("end of the day.")
    assert found["surface_match"] == NORMALIZED
    assert found["semantic_noncompositional"] == UNKNOWN
    assert found["primary_evidence_code"] == "magpie_surface_only"


def test_curly_apostrophe_is_normalized_and_pronouns_are_not_rewritten():
    curly = "flip one\u2019s lid"
    found = _row("flip one's lid", "noun:1", [_instance(5, curly, "i")])
    assert found["surface_match"] == NORMALIZED
    assert found["semantic_noncompositional"] == UNKNOWN
    other = _row("flip his lid", "noun:1", [_instance(6, "flip one's lid", "i")])
    assert other["surface_match"] == NONE
    assert other["primary_evidence_code"] == "magpie_no_match"
    assert normalized_key("someone's chair") != normalized_key("one's chair")


def test_inflection_variant_metadata_does_not_invent_a_match():
    found = _row(
        "threw in the towel",
        "verb:1",
        [_instance(7, "throw in the towel", "i", variant_type="inflection")],
    )
    assert found["surface_match"] == NONE
    assert found["semantic_noncompositional"] == UNKNOWN


def test_colliding_normalized_types_are_ambiguous_and_unattributed():
    found = _row(
        "a b",
        "noun:1",
        [_instance(8, "a-b"), _instance(9, "a b.")],
    )
    assert found["surface_match"] == AMBIGUOUS
    assert found["matched_magpie_expression"] is None
    assert found["literal_instance_count"] is None
    assert found["source_instance_ids"] == []
    assert found["ambiguous_candidates"] == ["a b.", "a-b"]
    assert found["sense_alignment"] == UNKNOWN
    assert found["primary_evidence_code"] == "magpie_surface_only"


def test_unique_exact_wins_over_another_normalized_type():
    found = _row(
        "a b",
        "noun:1",
        [_instance(10, "a b", "l"), _instance(11, "a-b", "i")],
    )
    assert found["surface_match"] == EXACT
    assert found["matched_magpie_expression"] == "a b"
    assert found["literal_instance_count"] == 1
    assert found["idiomatic_instance_count"] == 0


def test_all_idiomatic_labels_without_a_sense_identifier_stay_unknown():
    found = _row(
        "bear fruit",
        "verb:9",
        [_instance(12, "bear fruit", "i"), _instance(13, "bear fruit", "i")],
    )
    assert found["idiomatic_instance_count"] == 2
    assert found["literal_instance_count"] == 0
    assert found["sense_alignment"] == UNKNOWN
    assert found["alignment_basis"] == "no_bound_sense_identifier"
    assert found["semantic_noncompositional"] == UNKNOWN


def test_gloss_text_cannot_change_alignment():
    instances = [_instance(14, "bear fruit", "i")]
    index = build_index(instances)
    first = evaluate_row("bear fruit", "verb:9", index, VERSION, ARTIFACT)
    second = evaluate_row("bear fruit", "verb:9", index, VERSION, ARTIFACT)
    assert first == second
    assert "gloss" not in first


def test_equal_sense_identifier_can_align_without_using_labels_as_rules():
    instances = [
        _instance(15, "bear fruit", "i", synset="verb:9"),
        _instance(16, "bear fruit", "i", synset="verb:9"),
    ]
    found = _row("bear fruit", "verb:9", instances)
    assert found["sense_alignment"] == ALIGNED_IDIOMATIC
    assert found["semantic_noncompositional"] == "YES"
    assert found["primary_evidence_code"] == "magpie_aligned_idiomatic"
    literal = _row(
        "bear fruit",
        "verb:9",
        [_instance(17, "bear fruit", "l", synset="verb:9")],
    )
    assert literal["sense_alignment"] == ALIGNED_LITERAL
    assert literal["semantic_noncompositional"] == "NO"
    mixed = _row(
        "bear fruit",
        "verb:9",
        [
            _instance(18, "bear fruit", "i", synset="verb:9"),
            _instance(19, "bear fruit", "l", synset="verb:9"),
        ],
    )
    assert mixed["sense_alignment"] == MIXED
    assert mixed["semantic_noncompositional"] == UNKNOWN
    assert mixed["primary_evidence_code"] == "magpie_mixed_usage"


def test_a_different_sense_identifier_does_not_transfer():
    found = _row(
        "bear fruit",
        "verb:9",
        [_instance(20, "bear fruit", "i", synset="verb:8")],
    )
    assert found["sense_alignment"] == UNKNOWN
    assert found["alignment_basis"] == "sense_identifier_mismatch"
    assert found["semantic_noncompositional"] == UNKNOWN
    conflict = _row(
        "bear fruit",
        "verb:9",
        [
            _instance(21, "bear fruit", "i", synset="verb:9"),
            _instance(22, "bear fruit", "i", synset="verb:8"),
        ],
    )
    assert conflict["sense_alignment"] == CONFLICT
    assert conflict["semantic_noncompositional"] == UNKNOWN
    assert conflict["primary_evidence_code"] == "magpie_sense_conflict"


def test_other_and_unclear_labels_stay_unresolved():
    found = _row(
        "bear fruit",
        "verb:9",
        [
            _instance(23, "bear fruit", "o"),
            _instance(24, "bear fruit", "?"),
            _instance(25, "bear fruit", "f"),
        ],
    )
    assert found["unresolved_instance_count"] == 3
    assert found["idiomatic_instance_count"] == 0
    assert semantic_noncompositional(UNKNOWN) == UNKNOWN
    assert semantic_noncompositional(ALIGNED_IDIOMATIC) == "YES"
    assert semantic_noncompositional(ALIGNED_LITERAL) == "NO"
    assert semantic_noncompositional(MIXED) == UNKNOWN
    assert semantic_noncompositional(CONFLICT) == UNKNOWN
