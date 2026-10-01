"""Unit pins for AUTHORIZE_STAGE_A_FACTORIZED_RELATION_TRAIN."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_factorized_authorize import (  # noqa: E402
    AUTHORIZE_RULE,
    AUTHORIZED_AUTH_RECEIPT_SHA256,
    AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
    AUTHORIZED_TRAINING_CONFIG_SHA256,
    EXPERIMENT_ID,
    INITIALIZATION_POLICY,
    LITERAL_RELATION_WEIGHTS,
    LITERAL_RESOLVABILITY_WEIGHTS,
    TRAIN_ONCE_ACTION,
    calibrate_factorized_thresholds,
    checkpoint_selection_score,
    decide_stage_a,
)
from hyperlexical.classification_v5_stage_a_factorized_objective import (  # noqa: E402
    FACTORIZED_ANNOTATION_SHA256_PIN,
)


def test_authorize_pins():
    assert AUTHORIZE_RULE == "AUTHORIZE_STAGE_A_FACTORIZED_RELATION_TRAIN"
    assert EXPERIMENT_ID == "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-001"
    assert TRAIN_ONCE_ACTION == "TRAIN_STAGE_A_FACTORIZED_RELATION_ONCE"
    assert AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256.startswith("47e58773")
    assert AUTHORIZED_TRAINING_CONFIG_SHA256.startswith("618079c7")
    assert AUTHORIZED_AUTH_RECEIPT_SHA256.startswith("133d8dd0")
    assert FACTORIZED_ANNOTATION_SHA256_PIN.startswith("4ac88450")
    assert INITIALIZATION_POLICY["stage_a_best_continuation"] is False
    assert INITIALIZATION_POLICY["base_encoder_source"] == "MODEL_WIDE_BEST"


def test_literal_weights_sealed():
    assert LITERAL_RELATION_WEIGHTS["NO_EVIDENCE_RELATION"] == 0.9538023229441501
    assert LITERAL_RELATION_WEIGHTS["EVIDENCE_RELATION_PRESENT"] == 1.0461976770558497
    assert LITERAL_RESOLVABILITY_WEIGHTS["RESOLVABLE"] == 0.5
    assert LITERAL_RESOLVABILITY_WEIGHTS["UNRESOLVABLE"] == 1.5314299338122987
    for w in list(LITERAL_RELATION_WEIGHTS.values()) + list(
        LITERAL_RESOLVABILITY_WEIGHTS.values()
    ):
        assert 0.50 <= float(w) <= 2.00


def test_decision_and_selection_helpers():
    assert (
        decide_stage_a(
            p_evidence_relation_present=0.9,
            p_resolvable=0.1,
            relation_threshold=0.5,
            resolvability_threshold=0.5,
        )
        == "UNCERTAIN"
    )
    score = checkpoint_selection_score(
        relation_macro_f1=0.8, resolvability_macro_f1=0.6
    )
    assert abs(score - 0.7) < 1e-9


def test_threshold_calibration_fail_closed_on_empty_pass():
    # All UNCERTAIN-like scores → no acceptance pass expected for PRESENT/NONE gates.
    golds = ["NO_EVIDENCE", "EVIDENCE_PRESENT", "UNCERTAIN"]
    p_rel = [0.99, 0.99, 0.99]
    p_res = [0.01, 0.01, 0.01]  # always UNCERTAIN
    cal = calibrate_factorized_thresholds(
        golds=golds, p_relation=p_rel, p_resolvable=p_res
    )
    assert cal["feasible"] is False
    assert cal["disposition"] == "SETTLED_FAIL"
    assert cal["n_candidates"] == 100
