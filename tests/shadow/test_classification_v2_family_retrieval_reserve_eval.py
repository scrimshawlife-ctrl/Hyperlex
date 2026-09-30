"""Frozen family-retrieval reserve eval tests. No train / recalibrate / BEST."""

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
    EMISSION_PRECISION_MIN,
    FROZEN_MINIMUM_FAMILY_SCORE,
    FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
    RETRIEVAL_ARTIFACT_SHA256,
    RETRIEVAL_INDEX_SHA256,
    RULE,
    decide_reserve_disposition,
    reserve_eval_contract,
    selective_contract_generalizes,
    wrong_family_emissions,
)


def test_reserve_contract_is_frozen():
    contract = reserve_eval_contract()
    assert contract["rule"] == RULE
    assert contract["authorization"] == "OPERATOR_AUTHORIZE_RESERVE_EVAL"
    assert contract["recalibrate"] is False
    assert contract["rebuild_index"] is False
    assert contract["train"] is False
    assert contract["moves_best"] is False
    assert contract["minimum_family_score"] == FROZEN_MINIMUM_FAMILY_SCORE == 0.85
    assert contract["minimum_top1_top2_margin"] == FROZEN_MINIMUM_TOP1_TOP2_MARGIN == 0.03
    assert contract["retrieval_artifact_sha256"] == RETRIEVAL_ARTIFACT_SHA256
    assert contract["index_sha256"] == RETRIEVAL_INDEX_SHA256
    assert contract["jev"] == "OFF"


def test_disposition_uses_frozen_precision_only():
    passed = decide_reserve_disposition(
        invalid_reasons=[],
        family_emission_precision=0.808,
    )
    assert passed["disposition"] == "RESERVE_PASS"
    assert passed["production_family_decision_recommended"] is True
    failed = decide_reserve_disposition(
        invalid_reasons=[],
        family_emission_precision=0.79,
    )
    assert failed["disposition"] == "RESERVE_FAIL"
    assert failed["emission_precision_min"] == EMISSION_PRECISION_MIN
    invalid = decide_reserve_disposition(
        invalid_reasons=["overlaps_export:abc"],
        family_emission_precision=0.99,
    )
    assert invalid["disposition"] == "RESERVE_INVALID"


def test_wrong_emissions_and_generalization():
    wrong = wrong_family_emissions(
        [
            {
                "decision": "FAMILY",
                "family": "ai-native",
                "gold_lineage": "gaming-meta",
                "source_identity": "abc",
                "top1_score": 0.9,
                "top2_score": 0.8,
            },
            {
                "decision": "FAMILY",
                "family": "ai-native",
                "gold_lineage": "ai-native",
                "source_identity": "def",
                "top1_score": 0.95,
                "top2_score": 0.1,
            },
            {
                "decision": "ABSTAIN",
                "family": None,
                "gold_lineage": "ai-native",
                "source_identity": "ghi",
                "top1_score": 0.5,
                "top2_score": 0.4,
            },
        ]
    )
    assert len(wrong) == 1
    assert wrong[0]["predicted_family"] == "ai-native"
    assert wrong[0]["margin"] == 0.1
    assert selective_contract_generalizes(
        reserve_precision=0.81, validation_precision=0.808
    )["generalizes"]
    assert not selective_contract_generalizes(
        reserve_precision=0.5, validation_precision=0.808
    )["generalizes"]
