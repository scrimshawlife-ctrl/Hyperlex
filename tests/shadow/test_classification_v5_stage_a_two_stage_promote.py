"""Unit tests for Stage-A two-stage component promotion helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a import (  # noqa: E402
    FLAT_RUNTIME_STATUS,
    decide_evidence,
)
from hyperlexical.classification_v5_stage_a_two_stage_promote import (  # noqa: E402
    CANONICAL_FORWARD_SCHEMA,
    CANONICAL_GATE1_THRESHOLD,
    CANONICAL_GATE2_THRESHOLD,
    CANONICAL_LOAD_SEQUENCE,
    FLAT_RUNTIME_STATUS as PROMOTE_FLAT_STATUS,
    MODEL_WIDE_BEST_SHA256,
    PROMOTE_RULE,
    STAGE_A_BEST_SHA256,
    decide_canonical_stage_a,
    may_invoke_stage_b,
    preflight_promotion,
    stage_b_entry_from_stage_a,
)


def test_promote_constants_and_load_sequence():
    assert PROMOTE_RULE == "PROMOTE_V5_STAGE_A_TWO_STAGE_SELECTED"
    assert STAGE_A_BEST_SHA256.startswith("cd2829c1")
    assert MODEL_WIDE_BEST_SHA256.startswith("9fba0f66")
    assert STAGE_A_BEST_SHA256 != MODEL_WIDE_BEST_SHA256
    assert CANONICAL_GATE1_THRESHOLD == 0.75
    assert CANONICAL_GATE2_THRESHOLD == 0.50
    assert CANONICAL_FORWARD_SCHEMA == (
        "hyperlex.classification.v5.stage_a_two_stage_forward.v1"
    )
    assert CANONICAL_LOAD_SEQUENCE[0] == "modernbert_trunk"
    assert CANONICAL_LOAD_SEQUENCE[-1] == "gate2_head"
    assert PROMOTE_FLAT_STATUS == "DEPRECATED_FOR_CANONICAL_STAGE_A"
    assert FLAT_RUNTIME_STATUS == "DEPRECATED_FOR_CANONICAL_STAGE_A"


def test_canonical_decision_and_stage_b_entry():
    assert decide_canonical_stage_a(p_possible=0.74, p_confirmed=0.99) == "NO_EVIDENCE"
    assert (
        decide_canonical_stage_a(p_possible=0.75, p_confirmed=0.50)
        == "EVIDENCE_PRESENT"
    )
    assert decide_canonical_stage_a(p_possible=0.80, p_confirmed=0.49) == "UNCERTAIN"
    assert may_invoke_stage_b("EVIDENCE_PRESENT") is True
    assert may_invoke_stage_b("NO_EVIDENCE") is False
    assert may_invoke_stage_b("UNCERTAIN") is False
    uncertain = stage_b_entry_from_stage_a("UNCERTAIN")
    assert uncertain["action"] == "ABSTAIN"
    assert uncertain["family_retrieval"] == "FORBIDDEN"
    none = stage_b_entry_from_stage_a("NO_EVIDENCE")
    assert none["action"] == "STOP"
    present = stage_b_entry_from_stage_a("EVIDENCE_PRESENT")
    assert present["action"] == "PERMIT_STAGE_B"


def test_preflight_and_flat_still_callable_for_history():
    # Flat path remains callable for historical replay only.
    assert decide_evidence(0.9, none_threshold=0.05, present_threshold=0.55) == (
        "EVIDENCE_PRESENT"
    )
    review = {
        "PROMOTION_REVIEW": "VALID",
        "PROMOTION_DECISION": "PROMOTION_READY",
        "review_receipt_sha256": (
            "7e09c67d474c91af58dd4f2b4f19121ee81e99d5d472282cf0b4880a638908f2"
        ),
        "SELECTED_CHECKPOINT_SHA256": STAGE_A_BEST_SHA256,
        "SELECTED_EPOCH": 11,
        "NEXT_ACTION": PROMOTE_RULE,
    }
    replay = {
        "pass": True,
        "replay_hash": (
            "fc601e69569594d55eb150ee9b467eb37ce0c1b3015e29d88d54aecb7eda6474"
        ),
    }
    train = {
        "SELECTED_CHECKPOINT_SHA256": STAGE_A_BEST_SHA256,
        "restored_epoch": 11,
        "SCIENTIFIC_RESULT": "SETTLED_PASS",
        "selected_thresholds": {
            "gate1_threshold": 0.75,
            "gate2_present_threshold": 0.50,
        },
    }
    ok = preflight_promotion(
        promotion_review=review,
        validation_replay=replay,
        train_receipt=train,
        selected_checkpoint_sha256=STAGE_A_BEST_SHA256,
        model_wide_best_sha256=MODEL_WIDE_BEST_SHA256,
    )
    assert ok["pass"] is True
    bad = preflight_promotion(
        promotion_review={**review, "PROMOTION_DECISION": "PROMOTION_BLOCKED"},
        validation_replay=replay,
        train_receipt=train,
        selected_checkpoint_sha256=STAGE_A_BEST_SHA256,
        model_wide_best_sha256=MODEL_WIDE_BEST_SHA256,
    )
    assert bad["pass"] is False
