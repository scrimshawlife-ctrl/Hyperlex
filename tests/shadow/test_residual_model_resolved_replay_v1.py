import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.residual_model_resolved_replay_v1 import (
    AMBIGUOUS,
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    EXACT,
    INVERTED,
    NOT_COMPUTABLE,
    NO_SEPARATION,
    RESOLVED,
    SUPPORTED,
    UNRESOLVED,
    abstention_reason,
    analysis_plan,
    bootstrap_intervals,
    direction_result,
    extreme_driven,
    full_distribution,
    integrate_constituent,
    pair_comparison,
    projection_token,
    replay_decision,
    row_projection,
)
from hyperlexical.semantic_compositionality_residual import percentile
from hyperlexical.unbind_screen_v4 import rule_surface_violations

MODULE = ROOT / "scripts" / "shadow" / "hyperlexical" / "residual_model_resolved_replay_v1.py"
REPLAY = ROOT / "scripts" / "shadow" / "hyperlexical" / "residual_model_resolved_replay_v1_replay.py"
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


def _resolver(**overrides):
    row = {
        "candidate_synsets": ["noun:00000001", "noun:00000002"],
        "constituent_index": 0,
        "constituent_pos": "noun",
        "constituent_surface": "alpha",
        "parent_row_id": "row-1",
        "parent_surface": "alpha beta",
        "parent_synset": "noun:00000009",
        "primary_evidence_code": "extended_lesk_tie",
        "resolution_method": "EXTENDED_LESK_V1",
        "resolution_status": AMBIGUOUS,
        "selected_synset": None,
    }
    row.update(overrides)
    return row


def _model(**overrides):
    row = {
        "model_resolution_status": RESOLVED,
        "primary_evidence_code": "model_margin",
        "prior_resolution_status": AMBIGUOUS,
        "selected_sense_key": "alpha%1:00:00::",
        "selected_synset": "noun:00000001",
    }
    row.update(overrides)
    return row


def test_module_hides_labels_and_does_not_encode():
    source = MODULE.read_text(encoding="utf-8")
    replay = REPLAY.read_text(encoding="utf-8")
    assert rule_surface_violations(source, PROBES) == []
    assert "sentence_transformers" not in source
    assert "torch" not in source
    assert "operator_bucket" not in source
    assert "semantic_noncompositional = YES" not in source
    assert "semantic_noncompositional = NO" not in source
    assert "operator_bucket" not in inspect.signature(integrate_constituent).parameters
    plan = analysis_plan()
    assert plan["bootstrap_seed"] == BOOTSTRAP_SEED == 0
    assert plan["bootstrap_resamples"] == BOOTSTRAP_RESAMPLES == 10000
    assert plan["emits_yes_no"] is False
    assert plan["semantic_noncompositionality_threshold"] is None
    assert plan["threshold_eligible"] is False
    assert plan["json_schema_document"] is None
    assert replay.index("write_json(RECEIPT_PATH") < replay.index("buckets = load_operator_buckets()")
    assert "semantic_noncompositional = YES" not in replay
    assert "semantic_noncompositional = NO" not in replay


def test_integration_copies_frozen_tiers_and_refuses_overrides():
    exact = integrate_constituent(
        _resolver(
            primary_evidence_code="structural_exact",
            resolution_method="STRUCTURAL_EXACT",
            resolution_status=EXACT,
            selected_synset="noun:00000003",
        ),
        None,
    )
    assert exact["resolution_tier"] == "TIER1_STRUCTURAL"
    assert exact["resolution_status"] == EXACT
    assert exact["selected_pwn30_synset"] == "noun:00000003"
    assert exact["selected_sense_key_if_available"] is None
    with pytest.raises(RuntimeError):
        integrate_constituent(
            _resolver(resolution_method="UNIQUE_LEMMA", resolution_status=EXACT, selected_synset="noun:1"),
            _model(),
        )
    with pytest.raises(RuntimeError):
        integrate_constituent(
            _resolver(resolution_method="EXTENDED_LESK_V1", resolution_status=RESOLVED, selected_synset="noun:1"),
            _model(),
        )
    copied = integrate_constituent(_resolver(), _model())
    assert copied["resolution_tier"] == "TIER3_GLOSSBERT"
    assert copied["resolution_status"] == RESOLVED
    assert copied["selected_pwn30_synset"] == "noun:00000001"
    assert copied["resolution_provenance"] == "model_margin"
    with pytest.raises(RuntimeError):
        integrate_constituent(_resolver(), _model(selected_synset="noun:99999999"))
    abstained = integrate_constituent(
        _resolver(),
        _model(model_resolution_status=AMBIGUOUS, selected_sense_key=None, selected_synset=None),
    )
    assert abstained["resolution_status"] == AMBIGUOUS
    assert abstained["selected_pwn30_synset"] is None
    unresolved = integrate_constituent(
        _resolver(
            primary_evidence_code="no_candidate",
            resolution_method="NONE",
            resolution_status=UNRESOLVED,
            selected_synset=None,
            candidate_synsets=[],
        ),
        None,
    )
    assert unresolved["resolution_tier"] == UNRESOLVED
    assert projection_token("TIER2_EXTENDED_LESK", RESOLVED) == "LESK_RESOLVED"
    assert projection_token("TIER3_GLOSSBERT", RESOLVED) == "MODEL_RESOLVED"
    assert row_projection(["EXACT"]) == "UNKNOWN"
    assert row_projection(["EXACT", "LESK_RESOLVED", "MODEL_RESOLVED"]) == "RESIDUAL_READY"
    assert abstention_reason(["EXACT"]) == "fewer_than_two_content_constituents"
    assert abstention_reason([AMBIGUOUS, UNRESOLVED]) == "ambiguous_content_constituent"
    assert abstention_reason([EXACT, RESOLVED]) is None


def test_decision_gate_and_direction_are_preregistered():
    high = ["0.9000000000", "0.5000000000", "0.2000000000"]
    secondary = ["0.4000000000", "0.4000000000", "0.1000000000"]
    comparison = pair_comparison(high, secondary)
    assert comparison["status"] == "DESCRIPTIVE"
    assert direction_result(comparison) == SUPPORTED
    assert Decimal_gt(comparison["median_difference"])
    assert Decimal_gt(comparison["rank_biserial"])
    assert extreme_driven(high, secondary) is True
    promising = replay_decision(
        readiness_reproduced=True,
        determinism="IDENTICAL",
        direction=SUPPORTED,
        tier3_concentrated=False,
        extremes=False,
        pos_split=False,
    )
    assert promising["candidate_status"] == "CANDIDATE_PROMISING"
    assert promising["threshold_eligible"] is False
    assert promising["next_transition_authorized"] is False
    concentrated = replay_decision(
        readiness_reproduced=True,
        determinism="IDENTICAL",
        direction=SUPPORTED,
        tier3_concentrated=True,
        extremes=False,
        pos_split=False,
    )
    assert concentrated["candidate_status"] == "CANDIDATE_INSUFFICIENT"
    assert replay_decision(
        readiness_reproduced=False,
        determinism="IDENTICAL",
        direction=SUPPORTED,
        tier3_concentrated=False,
        extremes=False,
        pos_split=False,
    )["candidate_status"] == NOT_COMPUTABLE
    assert replay_decision(
        readiness_reproduced=True,
        determinism="DIFFERENT",
        direction=SUPPORTED,
        tier3_concentrated=False,
        extremes=False,
        pos_split=False,
    )["candidate_status"] == "NOT_DETERMINISTIC"
    inverted = pair_comparison(secondary, high)
    assert direction_result(inverted) == INVERTED
    flat = pair_comparison(["0.2000000000", "0.2000000000"], ["0.2000000000"])
    assert direction_result(flat) == NO_SEPARATION
    assert pair_comparison([], ["0.1"])["status"] == NOT_COMPUTABLE


def Decimal_gt(text: str) -> bool:
    from decimal import Decimal

    return Decimal(text) > 0


def test_distribution_matches_residual_percentile_and_bootstrap_is_seeded():
    scores = ["0.1000000000", "0.2000000000", "0.4000000000", "0.8000000000"]
    report = full_distribution(scores)
    assert report["p25"] == percentile(sorted(scores, key=lambda item: __import__("decimal").Decimal(item)), 25)
    assert report["count"] == 4
    assert report["std"] is not None
    first = bootstrap_intervals(["0.2", "0.4", "0.9"], ["0.1", "0.3"], seed=0, resamples=30)
    repeat = bootstrap_intervals(["0.2", "0.4", "0.9"], ["0.1", "0.3"], seed=0, resamples=30)
    other = bootstrap_intervals(["0.2", "0.4", "0.9"], ["0.1", "0.3"], seed=1, resamples=30)
    assert first == repeat
    assert first != other
    assert first["seed"] == 0
    assert first["resamples"] == 30
