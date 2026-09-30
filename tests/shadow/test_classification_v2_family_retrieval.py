"""Family retrieval decision tests. No train / reserve / BEST / ontology change."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
import hyperlexical.classification_v2 as v2  # noqa: E402

importlib.reload(v2)

from hyperlexical.classification_v2_family_retrieval import (  # noqa: E402
    CANONICAL_FAMILY_DECISION,
    EMISSION_PRECISION_MIN,
    RESIDUAL_HEAD_ROLE,
    RULE,
    TOP_M_CAP,
    build_index_records,
    calibrate_thresholds,
    decide_retrieval,
    evaluate_retrieval_decisions,
    family_scores,
    family_support_m,
    is_admissible_index_row,
    mean_top_m,
    reserve_gate,
    retrieval_contract,
)


def test_contract_preserves_encoder_and_deprecates_residual():
    contract = retrieval_contract()
    assert contract["rule"] == RULE
    assert contract["canonical_family_decision"] == CANONICAL_FAMILY_DECISION
    assert contract["residual_head_role"] == RESIDUAL_HEAD_ROLE
    assert contract["train"] is False
    assert contract["moves_best"] is False
    assert contract["reserve_scored"] is False
    assert contract["uses_family_centroid"] is False
    assert contract["jev"] == "OFF"
    assert contract["emission_precision_min"] == EMISSION_PRECISION_MIN


def test_admissible_rows_exclude_val_reserve_and_m_formula():
    assert is_admissible_index_row(
        {
            "split": "train",
            "task": "classify",
            "lineage": "ai-native",
            "class": "OBSERVED",
            "text": "transformer",
            "jev": "OFF",
        }
    )
    assert not is_admissible_index_row(
        {
            "split": "val",
            "task": "classify",
            "lineage": "ai-native",
            "class": "OBSERVED",
            "text": "transformer",
        }
    )
    assert not is_admissible_index_row(
        {
            "split": "train",
            "task": "classify",
            "lineage": "ai-native",
            "class": "OBSERVED",
            "text": "transformer",
            "evaluation_reserve": True,
        }
    )
    assert family_support_m(1) == 1
    assert family_support_m(2) == 2
    assert family_support_m(10) == TOP_M_CAP
    assert mean_top_m([0.1, 0.9, 0.5, 0.2], 3) == (0.9 + 0.5 + 0.2) / 3


def test_decide_retrieval_branches():
    none = decide_retrieval(
        applicability="NONE",
        top1_family="ai-native",
        top1_score=0.9,
        top2_family="gaming-meta",
        top2_score=0.1,
        minimum_family_score=0.5,
        minimum_top1_top2_margin=0.05,
    )
    assert none["decision"] == "NONE"
    abstain = decide_retrieval(
        applicability="FAMILY_PRESENT",
        top1_family="ai-native",
        top1_score=0.4,
        top2_family="gaming-meta",
        top2_score=0.1,
        minimum_family_score=0.5,
        minimum_top1_top2_margin=0.05,
    )
    assert abstain["decision"] == "ABSTAIN"
    ambiguous = decide_retrieval(
        applicability="FAMILY_PRESENT",
        top1_family="ai-native",
        top1_score=0.9,
        top2_family="gaming-meta",
        top2_score=0.88,
        minimum_family_score=0.5,
        minimum_top1_top2_margin=0.05,
    )
    assert ambiguous["decision"] == "AMBIGUOUS"
    assert ambiguous["ambiguous_pair"] == ["ai-native", "gaming-meta"]
    family = decide_retrieval(
        applicability="FAMILY_PRESENT",
        top1_family="ai-native",
        top1_score=0.9,
        top2_family="gaming-meta",
        top2_score=0.1,
        minimum_family_score=0.5,
        minimum_top1_top2_margin=0.05,
    )
    assert family["decision"] == "FAMILY"
    assert family["family"] == "ai-native"


def test_calibrate_and_reserve_gate():
    labels = list(v2.ACTIVE_FAMILY_VOCABULARY)
    rows = []
    for index, family in enumerate(labels):
        second = labels[(index + 1) % len(labels)]
        rows.append(
            {
                "applicability": "FAMILY_PRESENT",
                "gold_lineage": family,
                "top1_family": family,
                "top1_score": 0.95,
                "top2_family": second,
                "top2_score": 0.10,
            }
        )
    # One wrong high-score emission candidate that thresholds should exclude via margin/score if needed.
    rows.append(
        {
            "applicability": "FAMILY_PRESENT",
            "gold_lineage": labels[0],
            "top1_family": labels[1],
            "top1_score": 0.20,
            "top2_family": labels[2],
            "top2_score": 0.19,
        }
    )
    calibration = calibrate_thresholds(rows)
    assert calibration["feasible"] is True
    assert calibration["precision"] >= EMISSION_PRECISION_MIN
    assert calibration["minimum_family_score"] is not None
    evaluation = evaluate_retrieval_decisions(
        rows,
        minimum_family_score=float(calibration["minimum_family_score"]),
        minimum_top1_top2_margin=float(calibration["minimum_top1_top2_margin"]),
    )
    assert evaluation["family_emission_precision"] >= EMISSION_PRECISION_MIN
    gate = reserve_gate(
        family_emission_precision=evaluation["family_emission_precision"],
        applicability_invariance_pass=True,
    )
    assert gate["decision"] == "RESERVE_EVAL_JUSTIFIED"
    blocked = reserve_gate(
        family_emission_precision=0.5,
        applicability_invariance_pass=True,
    )
    assert blocked["decision"] == "RESERVE_EVAL_NOT_JUSTIFIED"


def test_index_and_family_scores_no_centroid():
    labels = list(v2.ACTIVE_FAMILY_VOCABULARY)
    width = 8
    rows = []
    embeddings = {}
    for index, family in enumerate(labels):
        text = f"exemplar {family}"
        identity_rows = {
            "split": "train",
            "task": "classify",
            "lineage": family,
            "class": "OBSERVED",
            "text": text,
            "jev": "OFF",
        }
        rows.append(identity_rows)
        vector = [0.0] * width
        vector[index % width] = 1.0
        from hyperlexical.holdout_guard import normalized_text_sha256

        embeddings[normalized_text_sha256(text)] = vector
    index = build_index_records(rows, embeddings)
    assert index["n_embeddings"] == 18
    assert index["uses_family_centroid"] is False
    assert all(index["family_support"][name] == 1 for name in labels)
    query = [0.0] * width
    query[0] = 1.0
    scored = family_scores(query, index["records"])
    assert scored["top1"]["family"] == labels[0]
    assert len(scored["candidates"]) == 3
