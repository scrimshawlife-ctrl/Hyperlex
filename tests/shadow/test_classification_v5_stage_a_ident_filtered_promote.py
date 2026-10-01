"""Unit pins for PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a_ident_filtered_promote import (  # noqa: E402
    CANONICAL_LOAD_SEQUENCE,
    CANONICAL_RELATION_THRESHOLD,
    CANONICAL_RESOLVABILITY_THRESHOLD,
    EXPECTED_METRICS,
    MODEL_WIDE_BEST_SHA256,
    NEXT_ACTION_ON_PASS,
    POSSIBLE_EVIDENCE_STATUS,
    PREVIOUS_STAGE_A_BEST_SHA256,
    PROMOTE_RULE,
    STAGE_A_BEST_SHA256,
    decide_canonical_stage_a,
    may_invoke_stage_b,
    metric_parity,
    preflight_promotion,
    stage_b_entry_from_stage_a,
    verify_factorized_architecture,
)


def test_promote_constants():
    assert PROMOTE_RULE == "PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE"
    assert STAGE_A_BEST_SHA256.startswith("8b2de447")
    assert PREVIOUS_STAGE_A_BEST_SHA256.startswith("cd2829c1")
    assert MODEL_WIDE_BEST_SHA256.startswith("9fba0f66")
    assert STAGE_A_BEST_SHA256 != MODEL_WIDE_BEST_SHA256
    assert CANONICAL_RELATION_THRESHOLD == 0.60
    assert CANONICAL_RESOLVABILITY_THRESHOLD == 0.75
    assert CANONICAL_LOAD_SEQUENCE[-1] == "resolvability_head"
    assert CANONICAL_LOAD_SEQUENCE[-2] == "relation_head"
    assert POSSIBLE_EVIDENCE_STATUS == (
        "DEPRECATED_AS_CANONICAL_STAGE_A_TRAINING_TARGET"
    )
    assert NEXT_ACTION_ON_PASS.startswith("FREEZE_V5_STAGE_A_CANONICAL")


def test_canonical_decision_and_stage_b_entry():
    assert decide_canonical_stage_a(p_relation=0.99, p_resolvable=0.74) == "UNCERTAIN"
    assert (
        decide_canonical_stage_a(p_relation=0.60, p_resolvable=0.75)
        == "EVIDENCE_PRESENT"
    )
    assert decide_canonical_stage_a(p_relation=0.59, p_resolvable=0.75) == "NO_EVIDENCE"
    assert may_invoke_stage_b("EVIDENCE_PRESENT") is True
    assert may_invoke_stage_b("NO_EVIDENCE") is False
    assert may_invoke_stage_b("UNCERTAIN") is False
    assert stage_b_entry_from_stage_a("UNCERTAIN")["action"] == "ABSTAIN"
    assert stage_b_entry_from_stage_a("NO_EVIDENCE")["action"] == "STOP"
    assert stage_b_entry_from_stage_a("EVIDENCE_PRESENT")["action"] == "PERMIT_STAGE_B"


def test_architecture_and_preflight():
    arch = verify_factorized_architecture(
        [
            "encoder.layers.20.weight",
            "relation_head.weight",
            "relation_head.bias",
            "resolvability_head.weight",
            "resolvability_head.bias",
        ]
    )
    assert arch["pass"] is True
    bad = verify_factorized_architecture(
        ["gate1_head.weight", "gate2_head.weight", "evidence_head.weight"]
    )
    assert bad["pass"] is False

    train = {
        "SCIENTIFIC_RESULT": "SETTLED_PASS",
        "promotion_candidate": True,
        "EXPERIMENT_ID": (
            "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-IDENT-FILTERED-001"
        ),
        "DATASET_SHA256": (
            "492ed36751c7fdc40fe10bcdfabb69fa8783f8680259c31b3a64ee6903326d73"
        ),
        "ANNOTATION_SHA256": (
            "95d5436555da33ef7aaccf4c32194c29f00caced9a17adf2d2f65f12db7dc1fc"
        ),
        "EXCLUSION_MANIFEST_SHA256": (
            "661c9edb095f7f7dc28a24256b42e0a2796f9ab78fbabc24b23cf9bd57b06d69"
        ),
        "AUTHORIZATION_RECEIPT_SHA256": (
            "6341d0831327bdc3c912b133025b7265c62986badf369819d44dcaf506da42ed"
        ),
        "TRAINING_CONFIG_SHA256": (
            "e252f1ba7beb577f0beb90bc9de294a16a8b808508081bb5b081b530fcaab460"
        ),
        "CLASS_WEIGHT_ARTIFACT_SHA256": (
            "13e8d0ca250839500b71b4b9e23d8238a90488987b9a49cd2c6d2fc336f77fc6"
        ),
        "SELECTED_CHECKPOINT_SHA256": STAGE_A_BEST_SHA256,
        "restored_epoch": 11,
        "selected_thresholds": {
            "relation_threshold": 0.60,
            "resolvability_threshold": 0.75,
        },
        "acceptance_gates": {
            "false_evidence_entry_rate_on_none": {
                "pass": True,
                "value": 0.03356890459363958,
            },
            "EVIDENCE_PRESENT_recall": {"pass": True, "value": 0.951310861423221},
            "NO_EVIDENCE_recall": {"pass": True, "value": 0.9646643109540636},
        },
        "V1R2_MUTATED": False,
        "RESERVE": "SPENT",
        "SPENT_RESERVE": "HYPERLEX_V5_PROMOTION_RESERVE_001",
        "RUN_RECEIPT_SHA256": (
            "4a7d565ca607234c604bcec40acab33e3cbecc4da6e4adc86a0b2b79bb091a4b"
        ),
        "OBJECTIVE_ID": "HYPERLEX_V5_STAGE_A_FACTORIZED_RELATION_OBJECTIVE_V1",
    }
    ok = preflight_promotion(
        train_receipt=train,
        selected_checkpoint_sha256=STAGE_A_BEST_SHA256,
        model_wide_best_sha256=MODEL_WIDE_BEST_SHA256,
        current_stage_a_best_sha256=PREVIOUS_STAGE_A_BEST_SHA256,
        dataset_sha256=train["DATASET_SHA256"],
        annotation_sha256=train["ANNOTATION_SHA256"],
        exclusion_manifest_sha256=train["EXCLUSION_MANIFEST_SHA256"],
        v1r2_mutated=False,
    )
    assert ok["pass"] is True
    assert metric_parity(EXPECTED_METRICS, EXPECTED_METRICS)["pass"] is True
