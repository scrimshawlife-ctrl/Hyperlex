import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.constituent_sense_resolution_v1 import (
    AMBIGUOUS,
    EXACT,
    RESOLVED,
    coverage_decision,
    lesk_tokens,
    overlap_score,
    resolve_constituent_sense,
    resolver_policy,
    row_resolution_status,
    structural_synset_ids,
)
from hyperlexical.unbind_screen_v4 import rule_surface_violations

MODULE = ROOT / "scripts" / "shadow" / "hyperlexical" / "constituent_sense_resolution_v1.py"
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


def test_module_has_no_phrase_exception_embedding_or_label_input():
    source = MODULE.read_text(encoding="utf-8")
    assert rule_surface_violations(source, PROBES) == []
    assert "sentence_transformers" not in source
    assert "SentenceTransformer" not in source
    names = set(inspect.signature(resolve_constituent_sense).parameters)
    assert "operator_bucket" not in names
    assert "residual_score" not in names
    assert "gloss" not in names
    policy = resolver_policy()
    assert policy["state_at_freeze"] == "SPEC_FROZEN"
    assert policy["encoded_at_freeze"] is False
    assert "residual_scores" in policy["forbidden_inputs"]
    assert "operator_labels" in policy["forbidden_inputs"]
    assert policy["extended_lesk"]["minimum_margin"] == 1
    assert policy["extended_lesk"]["stemming"] is False


def test_structural_pointer_outranks_a_higher_lesk_score():
    pointers = [
        ("+", 1, "noun:1", "towel"),
        ("!", 1, "noun:2", "other"),
        ("+", 0, "noun:9", "towel"),
        ("@", 1, "noun:8", "towel"),
    ]
    structural = structural_synset_ids(pointers, "towel", {})
    assert structural == ["noun:1"]
    decision = resolve_constituent_sense(
        structural,
        ["noun:1", "noun:2"],
        [("noun:2", 99), ("noun:1", 0)],
    )
    assert decision["resolution_status"] == EXACT
    assert decision["resolution_method"] == "STRUCTURAL_EXACT"
    assert decision["selected_synset"] == "noun:1"
    assert decision["top_score"] is None
    conflict = structural_synset_ids(
        [("+", 1, "noun:1", "shot"), ("<", 1, "noun:2", "shot")],
        "shots",
        {"shots": {"shot"}, "shot": {"shots"}},
    )
    blocked = resolve_constituent_sense(conflict, ["noun:1", "noun:2"], [("noun:1", 5), ("noun:2", 1)])
    assert blocked["resolution_status"] == AMBIGUOUS
    assert blocked["selected_synset"] is None
    assert blocked["resolution_method"] == "STRUCTURAL_EXACT"


def test_unique_lemma_is_exact_and_absence_stays_unresolved():
    one = resolve_constituent_sense([], ["noun:4"], None)
    assert one["resolution_status"] == EXACT
    assert one["resolution_method"] == "UNIQUE_LEMMA"
    assert one["selected_synset"] == "noun:4"
    missing = resolve_constituent_sense([], [], [("noun:1", 3)])
    assert missing["resolution_status"] == "UNRESOLVED"
    assert missing["resolution_method"] == "NONE"
    assert missing["selected_synset"] is None


def test_extended_lesk_scores_squares_and_ties_abstain():
    assert lesk_tokens("The edible, swollen root!") == ["edible", "swollen", "root"]
    assert overlap_score(["edible", "swollen", "root"], ["swollen", "root"]) == 4
    assert overlap_score(["edible", "root"], ["edible", "root"]) == overlap_score(
        ["edible", "root"], ["edible", "root"]
    )
    resolved = resolve_constituent_sense(
        [],
        ["noun:1", "noun:2"],
        [("noun:2", 1), ("noun:1", 4)],
    )
    assert resolved["resolution_status"] == RESOLVED
    assert resolved["resolution_method"] == "EXTENDED_LESK_V1"
    assert resolved["selected_synset"] == "noun:1"
    assert resolved["top_score"] == 4
    assert resolved["second_score"] == 1
    assert resolved["margin"] == 3
    tie = resolve_constituent_sense([], ["noun:2", "noun:1"], [("noun:1", 4), ("noun:2", 4)])
    assert tie["resolution_status"] == AMBIGUOUS
    assert tie["selected_synset"] is None
    assert tie["primary_evidence_code"] == "extended_lesk_tie"
    assert tie["margin"] == 0
    zeros = resolve_constituent_sense([], ["noun:1", "noun:2"], [("noun:1", 0), ("noun:2", 0)])
    assert zeros["resolution_status"] == AMBIGUOUS
    assert zeros["selected_synset"] is None


def test_row_readiness_keeps_the_two_content_rule():
    assert row_resolution_status(2, [EXACT, RESOLVED]) == "RESIDUAL_READY"
    assert row_resolution_status(2, [EXACT, AMBIGUOUS]) == "UNKNOWN"
    assert row_resolution_status(1, [EXACT]) == "UNKNOWN"
    assert row_resolution_status(0, []) == "UNKNOWN"


def test_coverage_rule_is_fixed_before_any_label_join():
    insufficient = coverage_decision(
        baseline_ambiguous=10,
        baseline_ambiguous_not_resolved=6,
        residual_ready_high=1,
        residual_ready_secondary=1,
    )
    assert insufficient["coverage_finding"] == "CONSTITUENT_WSD_COVERAGE_INSUFFICIENT"
    assert insufficient["candidate_status"] == "COVERAGE_INSUFFICIENT"
    assert insufficient["next_transition_authorized"] is False
    assert insufficient["necessary_condition_met"] is True
    half = coverage_decision(
        baseline_ambiguous=10,
        baseline_ambiguous_not_resolved=5,
        residual_ready_high=1,
        residual_ready_secondary=1,
    )
    assert half["coverage_finding"] is None
    assert half["candidate_status"] == "COVERAGE_NECESSARY_CONDITION_MET"
    unmet = coverage_decision(
        baseline_ambiguous=10,
        baseline_ambiguous_not_resolved=5,
        residual_ready_high=0,
        residual_ready_secondary=4,
    )
    assert unmet["candidate_status"] == "NECESSARY_CONDITION_UNMET"
    assert unmet["necessary_condition_met"] is False
