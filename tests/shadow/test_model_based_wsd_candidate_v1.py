import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.model_based_wsd_candidate_v1 import (
    candidate_gloss_text,
    candidate_policy,
    coverage_gate,
    format_probability,
    gloss_lemma,
    overlay_status,
    project_row_status,
    quoted_context,
    resolve_model_scores,
    summarize_confidence,
)
from hyperlexical.unbind_screen_v4 import rule_surface_violations

MODULE = ROOT / "scripts" / "shadow" / "hyperlexical" / "model_based_wsd_candidate_v1.py"
REPLAY = ROOT / "scripts" / "shadow" / "hyperlexical" / "model_based_wsd_candidate_v1_replay.py"
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
KEYS = {
    "noun:1": ["alpha%1:00:00::"],
    "noun:2": ["beta%1:00:00::"],
}


def test_module_freezes_one_model_and_hides_labels_from_the_decision():
    source = MODULE.read_text(encoding="utf-8")
    replay = REPLAY.read_text(encoding="utf-8")
    assert rule_surface_violations(source, PROBES) == []
    assert "sentence_transformers" not in source
    assert "MiniLM" not in source
    assert "sentence_transformers" not in replay
    assert "MiniLM" not in replay
    names = set(inspect.signature(resolve_model_scores).parameters)
    assert "operator_bucket" not in names
    assert "residual_score" not in names
    policy = candidate_policy()
    assert policy["state_at_freeze"] == "SPEC_FROZEN"
    assert policy["applied_to_hyperlex_at_freeze"] is False
    assert policy["selected_source"] == "none"
    assert policy["runtime_integration"] is False
    assert policy["residual_replay_authorized"] is False
    assert policy["model_name"] == "kanishka/GlossBERT"
    assert policy["model_revision"] == "0cc3b83af5496e27ebcc95ef0cf37ea0a9281a7a"
    assert policy["positive_class_index"] == 1
    assert policy["license"] == "MIT"
    assert "operator_labels" in policy["forbidden_inputs"]
    assert "residual_embeddings" in policy["forbidden_inputs"]
    assert "residual_scores" in policy["forbidden_inputs"]
    assert policy["readiness_gate"]["baseline_high_ready"] == 4
    assert policy["readiness_gate"]["baseline_secondary_ready"] == 4
    assert policy["readiness_gate"]["baseline_total_ready"] == 20
    assert policy["readiness_gate"]["comparison"] == "strictly_greater"
    assert policy["no_gold_constituent_senses"] is True
    assert policy["pwn_mapping"]["cross_version_map"] is False
    assert policy["pwn_mapping"]["manual_migration"] is False


def test_context_quotes_only_the_indexed_content_token():
    assert quoted_context("alpha in beta", 0, "alpha") == '"alpha" in beta'
    assert quoted_context("alpha in beta", 1, "beta") == 'alpha in "beta"'
    assert gloss_lemma(["bank", "other"], "banks", {"banks": {"bank"}, "bank": {"banks"}}) == "bank"
    assert candidate_gloss_text("bank", "sloping land") == "bank: sloping land"
    assert format_probability(0.5) == "0.500000"


def test_abstention_ties_and_invalid_senses_do_not_select():
    resolved = resolve_model_scores(
        ["noun:1", "noun:2"],
        KEYS,
        {"noun:1": "0.800000", "noun:2": "0.200000"},
    )
    assert resolved["model_resolution_status"] == "RESOLVED"
    assert resolved["selected_synset"] == "noun:1"
    assert resolved["selected_sense_key"] == "alpha%1:00:00::"
    assert resolved["primary_evidence_code"] == "model_margin"
    boundary = resolve_model_scores(
        ["noun:1", "noun:2"],
        KEYS,
        {"noun:1": "0.500000", "noun:2": "0.400000"},
    )
    assert boundary["model_resolution_status"] == "RESOLVED"
    assert boundary["model_margin"] == "0.100000"
    near = resolve_model_scores(
        ["noun:1", "noun:2"],
        KEYS,
        {"noun:1": "0.550000", "noun:2": "0.500000"},
    )
    assert near["model_resolution_status"] == "AMBIGUOUS"
    assert near["selected_synset"] is None
    assert near["primary_evidence_code"] == "model_abstention"
    low = resolve_model_scores(
        ["noun:1", "noun:2"],
        KEYS,
        {"noun:1": "0.400000", "noun:2": "0.100000"},
    )
    assert low["model_resolution_status"] == "AMBIGUOUS"
    assert low["selected_synset"] is None
    tie = resolve_model_scores(
        ["noun:2", "noun:1"],
        KEYS,
        {"noun:1": "0.800000", "noun:2": "0.800000"},
    )
    assert tie["model_resolution_status"] == "AMBIGUOUS"
    assert tie["selected_synset"] is None
    assert tie["primary_evidence_code"] == "model_score_tie"
    outsider = resolve_model_scores(
        ["noun:1", "noun:2"],
        KEYS,
        {"noun:1": "0.900000", "noun:9": "0.100000"},
    )
    assert outsider["model_resolution_status"] == "INVALID"
    assert outsider["selected_synset"] is None
    assert outsider["primary_evidence_code"] == "invalid_model_output"
    many_keys = resolve_model_scores(
        ["noun:1", "noun:2"],
        {"noun:1": ["alpha%1:00:00::", "alpha%1:00:01::"], "noun:2": ["beta%1:00:00::"]},
        {"noun:1": "0.900000", "noun:2": "0.100000"},
    )
    assert many_keys["model_resolution_status"] == "AMBIGUOUS"
    assert many_keys["selected_sense_key"] is None
    assert many_keys["selected_synset"] is None
    assert many_keys["primary_evidence_code"] == "pwn30_sense_key_not_unique"
    flooded = resolve_model_scores(
        ["noun:1", "noun:2"],
        KEYS,
        {"noun:1": "0.990000", "noun:2": "0.010000"},
        overflow=True,
    )
    assert flooded["model_resolution_status"] == "AMBIGUOUS"
    assert flooded["selected_synset"] is None
    assert flooded["primary_evidence_code"] == "context_overflow"
    failed = resolve_model_scores(["noun:1", "noun:2"], KEYS, None, error="forward failed")
    assert failed["model_resolution_status"] == "ERROR"
    assert failed["selected_synset"] is None


def test_tier3_cannot_override_an_earlier_tier_and_readiness_needs_two_constituents():
    assert overlay_status("EXACT", "STRUCTURAL_EXACT", None) == "EXACT"
    assert overlay_status("RESOLVED", "EXTENDED_LESK_V1", None) == "LESK_RESOLVED"
    assert overlay_status("UNRESOLVED", "NONE", None) == "UNRESOLVED"
    assert overlay_status("AMBIGUOUS", "EXTENDED_LESK_V1", "RESOLVED") == "MODEL_RESOLVED"
    assert overlay_status("AMBIGUOUS", "EXTENDED_LESK_V1", "AMBIGUOUS") == "AMBIGUOUS"
    assert project_row_status(["EXACT", "MODEL_RESOLVED"]) == "RESIDUAL_READY"
    assert project_row_status(["LESK_RESOLVED", "MODEL_RESOLVED"]) == "RESIDUAL_READY"
    assert project_row_status(["EXACT", "AMBIGUOUS"]) == "UNKNOWN"
    assert project_row_status(["EXACT"]) == "UNKNOWN"
    try:
        overlay_status("EXACT", "STRUCTURAL_EXACT", "RESOLVED")
    except RuntimeError as exc:
        assert "overrode" in str(exc)
    else:
        raise AssertionError("exact override was accepted")


def test_coverage_gate_is_strict_and_equality_is_not_promising():
    promising = coverage_gate(
        high_ready=5,
        secondary_ready=5,
        total_ready=21,
        invalid_output_count=0,
        error_count=0,
        determinism="IDENTICAL",
    )
    assert promising["candidate_status"] == "CANDIDATE_PROMISING"
    assert promising["next_transition_authorized"] is False
    baseline = coverage_gate(
        high_ready=4,
        secondary_ready=4,
        total_ready=20,
        invalid_output_count=0,
        error_count=0,
        determinism="IDENTICAL",
    )
    assert baseline["candidate_status"] == "CANDIDATE_INSUFFICIENT"
    one_sided = coverage_gate(
        high_ready=5,
        secondary_ready=4,
        total_ready=21,
        invalid_output_count=0,
        error_count=0,
        determinism="IDENTICAL",
    )
    assert one_sided["candidate_status"] == "CANDIDATE_INSUFFICIENT"
    rejected = coverage_gate(
        high_ready=10,
        secondary_ready=10,
        total_ready=40,
        invalid_output_count=1,
        error_count=0,
        determinism="IDENTICAL",
    )
    assert rejected["candidate_status"] == "CANDIDATE_REJECTED"
    drifted = coverage_gate(
        high_ready=10,
        secondary_ready=10,
        total_ready=40,
        invalid_output_count=0,
        error_count=0,
        determinism="MISMATCH",
    )
    assert drifted["candidate_status"] == "NOT_DETERMINISTIC"
    summary = summarize_confidence(
        [
            {
                "candidate_pwn30_synsets": ["noun:1", "noun:2"],
                "model_confidence": "0.750000",
                "model_margin": "0.300000",
                "model_resolution_status": "RESOLVED",
            },
            {
                "candidate_pwn30_synsets": ["noun:1", "noun:2", "noun:3"],
                "model_confidence": "0.400000",
                "model_margin": "0.050000",
                "model_resolution_status": "AMBIGUOUS",
            },
        ]
    )
    assert summary["resolved"] == 1
    assert summary["abstained"] == 1
    assert summary["confidence_bins"]["0.70_to_0.80"] == 1
    assert summary["confidence_bins"]["below_0.50"] == 1
    assert summary["margin_bins"]["0.25_to_0.50"] == 1
    assert summary["by_candidate_count"]["2"]["resolved"] == 1
    assert "operator_bucket" not in summary
