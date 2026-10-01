"""Stage-B V5 integration tests. No GPU / reserve / BEST mutation."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_b import (  # noqa: E402
    EXPERIMENT_ID,
    STAGE_A_BEST_SHA256,
    STAGE_B_RULE,
    WIRE_ACTION,
    compose_end_to_end,
    design_freeze_receipt,
    gold_end_to_end,
    next_action_for_stage_b,
    reserve_authorization,
    stage_b_contract,
)


def test_stage_b_contract_pins_stage_a_best():
    contract = stage_b_contract()
    assert contract["rule"] == STAGE_B_RULE
    assert contract["experiment_id"] == EXPERIMENT_ID
    assert contract["STAGE_A_BEST"] == STAGE_A_BEST_SHA256
    assert STAGE_A_BEST_SHA256.startswith("f2b00c5d")
    assert contract["STAGE_A_CANONICAL"] == "HYPERLEX_V5_STAGE_A_CANONICAL_V1"
    assert contract["retrieval_only_on"] == "EVIDENCE_PRESENT"
    assert contract["train"] is False
    assert contract["v5_reserve"] is None
    assert contract["index_rebuilt"] is False
    assert contract["floors_retuned"] is False
    assert contract["frozen_stage_a"]["relation_threshold"] == 0.60
    assert contract["frozen_stage_a"]["resolvability_threshold"] == 0.75
    assert contract["frozen_stage_a"]["deprecated_gate1_gate2"]["status"] == "HISTORICAL"
    assert contract["entry_invariant"]["UNCERTAIN"] == "ABSTAIN"


def test_retrieval_gated_by_promoted_stage_a():
    none = compose_end_to_end(
        evidence_decision="NO_EVIDENCE",
        ranked_candidates=[{"family": "memetic", "score": 0.99}],
        family_score_min=0.5,
        family_margin_min=0.01,
    )
    assert none["decision_type"] == "NONE"
    assert none["stage_a_entry"]["action"] == "STOP"
    uncertain = compose_end_to_end(
        evidence_decision="UNCERTAIN",
        ranked_candidates=[{"family": "memetic", "score": 0.99}],
        family_score_min=0.5,
        family_margin_min=0.01,
    )
    assert uncertain["decision_type"] == "ABSTAIN"
    assert uncertain["stage_a_entry"]["family_retrieval"] == "FORBIDDEN"
    family = compose_end_to_end(
        evidence_decision="EVIDENCE_PRESENT",
        ranked_candidates=[
            {"family": "memetic", "score": 0.9},
            {"family": "gaming-meta", "score": 0.1},
        ],
        family_score_min=0.5,
        family_margin_min=0.05,
    )
    assert family["decision_type"] == "FAMILY"
    assert family["family"] == "memetic"
    assert family["stage_a_entry"]["action"] == "PERMIT_STAGE_B"


def test_gold_mapping_and_design_freeze():
    assert gold_end_to_end(
        {
            "evidence_subtype": "POSITIVE_EVIDENCE",
            "candidate_families": ["technology-ai"],
        }
    ) == {"decision_type": "FAMILY", "family": "technology-ai"}
    assert gold_end_to_end({"evidence_subtype": "ORDINARY_DOMAIN_NONE"})[
        "decision_type"
    ] == "NONE"
    assert gold_end_to_end({"evidence_subtype": "AMBIGUOUS_EVIDENCE"})[
        "decision_type"
    ] == "ABSTAIN"
    freeze = design_freeze_receipt(code_revision="deadbeef")
    assert freeze["NEXT_ACTION"] == WIRE_ACTION
    assert freeze["STAGE_A_BEST"].startswith("f2b00c5d")
    assert freeze["TRAIN"] is False
    auth_ok = reserve_authorization(
        {"primary_gate_pass": True, "secondary_gate_pass": True}
    )
    assert auth_ok["decision"] == "RESERVE_SEAL_AUTHORIZED"
    assert next_action_for_stage_b(auth_ok).startswith("AUTHORIZE_SEAL_NEW_V5")
    auth_bad = reserve_authorization(
        {"primary_gate_pass": True, "secondary_gate_pass": False}
    )
    assert next_action_for_stage_b(auth_bad) == "DIAGNOSE_V5_STAGE_B_BEFORE_ANY_RESERVE"
