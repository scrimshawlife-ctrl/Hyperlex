"""HYPERLEX_V5_STAGE_A_B_PIPELINE_V1 — frozen Stage-A → Stage-B pipeline.

Read-only contract freeze under canonical Stage-A + V1R2-aligned Stage-B.
Does not train Stage-A, score spent reserve, rebuild Stage-B index, retune
floors, or mutate MODEL_WIDE_BEST.
"""

from __future__ import annotations

from typing import Any, Mapping

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import (
    CANONICAL_ID,
    KNOWN_LIMITATIONS,
    MODEL_WIDE_BEST_SHA256,
    SCHEMA_FORWARD,
    STAGE_A_BEST_SHA256,
    STAGE_A_RESEARCH_LOOP,
    V5_STAGE_A_STATE,
    build_canonical_forward,
    decide_canonical_stage_a,
    may_invoke_stage_b,
    stage_a_canonical_contract,
    stage_b_entry_from_stage_a,
)
from .classification_v5_stage_a_gold_identifiability_filter import (
    SURFACE_ID as V1R2_SURFACE_ID,
    V1R2_DATASET_SHA256_PIN,
)
from .classification_v5_stage_a_ident_filtered_promote import (
    CANONICAL_RELATION_THRESHOLD,
    CANONICAL_RESOLVABILITY_THRESHOLD,
)
from .classification_v5_stage_b import (
    EXPERIMENT_ID as STAGE_B_EXPERIMENT_ID,
    FROZEN_INDEX_SHA256,
    FROZEN_MINIMUM_FAMILY_SCORE,
    FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
    STAGE_B_RULE,
    stage_b_contract,
)

PIPELINE_ID = "HYPERLEX_V5_STAGE_A_B_PIPELINE_V1"
PIPELINE_RULE = "FREEZE_V5_STAGE_A_B_PIPELINE_CONTRACT"
SCHEMA_PIPELINE = "hyperlex.classification.v5.stage_a_b_pipeline.v1"
SCHEMA_PIPELINE_FORWARD = "hyperlex.classification.v5.stage_a_b_pipeline_forward.v1"

V5_STAGE_B_STATE = "CANONICAL_FOR_V1R2_PIPELINE"
V5_STAGE_A_B_PIPELINE_STATE = "CANONICAL_FROZEN"

PIPELINE_FLOW = (
    "text",
    "canonical_stage_a",
    "NO_EVIDENCE->stop",
    "UNCERTAIN->abstain",
    "EVIDENCE_PRESENT->stage_b_retrieval",
    "family_decision_or_abstain_or_ambiguity",
)


def verify_entry_gating() -> dict[str, Any]:
    cases = {
        "NO_EVIDENCE": stage_b_entry_from_stage_a("NO_EVIDENCE"),
        "UNCERTAIN": stage_b_entry_from_stage_a("UNCERTAIN"),
        "EVIDENCE_PRESENT": stage_b_entry_from_stage_a("EVIDENCE_PRESENT"),
    }
    checks = {
        "none_never_enters": cases["NO_EVIDENCE"]["stage_b_permitted"] is False
        and cases["NO_EVIDENCE"]["action"] == "STOP",
        "uncertain_never_enters": cases["UNCERTAIN"]["stage_b_permitted"] is False
        and cases["UNCERTAIN"]["action"] == "ABSTAIN",
        "present_enters": cases["EVIDENCE_PRESENT"]["stage_b_permitted"] is True
        and cases["EVIDENCE_PRESENT"]["action"] == "PERMIT_STAGE_B",
        "may_invoke_present_only": may_invoke_stage_b("EVIDENCE_PRESENT")
        and not may_invoke_stage_b("NO_EVIDENCE")
        and not may_invoke_stage_b("UNCERTAIN"),
    }
    return {"cases": cases, "checks": checks, "pass": all(checks.values())}


def verify_stage_b_parent_and_floors() -> dict[str, Any]:
    contract = stage_b_contract()
    frozen = contract.get("frozen_stage_a") or {}
    checks = {
        "parent_stage_a_best": contract.get("STAGE_A_BEST") == STAGE_A_BEST_SHA256,
        "parent_canonical_id": frozen.get("STAGE_A_CANONICAL") == CANONICAL_ID,
        "model_wide_best": contract.get("MODEL_WIDE_BEST") == MODEL_WIDE_BEST_SHA256
        or frozen.get("model_wide_BEST") == MODEL_WIDE_BEST_SHA256,
        "index_pin_match": contract.get("frozen_index_sha256") == FROZEN_INDEX_SHA256,
        "score_floor_pin_match": contract.get("minimum_family_score")
        == FROZEN_MINIMUM_FAMILY_SCORE,
        "margin_floor_pin_match": contract.get("minimum_top1_top2_margin")
        == FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
        "index_rebuilt": contract.get("index_rebuilt") is True,
        "floors_retuned": contract.get("floors_retuned") is True,
        "entry_invariant_present": (contract.get("entry_invariant") or {}).get(
            "EVIDENCE_PRESENT"
        )
        == "PERMIT_STAGE_B",
        "entry_invariant_none": (contract.get("entry_invariant") or {}).get(
            "NO_EVIDENCE"
        )
        == "STOP",
        "entry_invariant_uncertain": (contract.get("entry_invariant") or {}).get(
            "UNCERTAIN"
        )
        == "ABSTAIN",
    }
    return {
        "checks": checks,
        "pass": all(checks.values()),
        "contract_slice": {
            "STAGE_A_BEST": contract.get("STAGE_A_BEST"),
            "frozen_index_sha256": contract.get("frozen_index_sha256"),
            "minimum_family_score": contract.get("minimum_family_score"),
            "minimum_top1_top2_margin": contract.get("minimum_top1_top2_margin"),
            "STAGE_A_CANONICAL": frozen.get("STAGE_A_CANONICAL"),
        },
    }


def runtime_registry() -> dict[str, Any]:
    """Separate component pointers — never merge into MODEL_WIDE_BEST."""
    return {
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_B_INDEX": FROZEN_INDEX_SHA256,
        "V5_PIPELINE": PIPELINE_ID,
        "STAGE_A_SURFACE": V1R2_SURFACE_ID,
        "STAGE_A_SURFACE_DATASET_SHA256": V1R2_DATASET_SHA256_PIN,
        "merged_into_model_wide_best": False,
    }


def pipeline_contract() -> dict[str, Any]:
    return {
        "PIPELINE_ID": PIPELINE_ID,
        "STAGE_A_CANONICAL": CANONICAL_ID,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "STAGE_B_RULE": STAGE_B_RULE,
        "STAGE_B_EXPERIMENT_ID": STAGE_B_EXPERIMENT_ID,
        "V5_STAGE_A_STATE": V5_STAGE_A_STATE,
        "V5_STAGE_B_STATE": V5_STAGE_B_STATE,
        "V5_STAGE_A_B_PIPELINE_STATE": V5_STAGE_A_B_PIPELINE_STATE,
        "STAGE_A_RESEARCH_LOOP": STAGE_A_RESEARCH_LOOP,
        "flow": list(PIPELINE_FLOW),
        "forward_schema": SCHEMA_PIPELINE_FORWARD,
        "stage_a_forward_schema": SCHEMA_FORWARD,
        "known_limitations": {
            **KNOWN_LIMITATIONS,
            "STAGE_B_VALIDATION_SCOPE": (
                "Stage-B validation is conditional on canonical Stage-A "
                "admission behavior on V1R2."
            ),
        },
        "thresholds": {
            "relation": CANONICAL_RELATION_THRESHOLD,
            "resolvability": CANONICAL_RESOLVABILITY_THRESHOLD,
        },
        "floors": {
            "minimum_family_score": FROZEN_MINIMUM_FAMILY_SCORE,
            "minimum_top1_top2_margin": FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
        },
        "dependencies": {
            "stage_a_checkpoint_sha256": STAGE_A_BEST_SHA256,
            "model_wide_best_sha256": MODEL_WIDE_BEST_SHA256,
            "stage_b_index_sha256": FROZEN_INDEX_SHA256,
            "stage_b_minimum_family_score": FROZEN_MINIMUM_FAMILY_SCORE,
            "stage_b_minimum_top1_top2_margin": FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
            "stage_a_surface_id": V1R2_SURFACE_ID,
            "stage_a_surface_dataset_sha256": V1R2_DATASET_SHA256_PIN,
            "stage_a_contract": stage_a_canonical_contract()["CANONICAL_ID"],
            "stage_b_contract_rule": STAGE_B_RULE,
        },
        "runtime_registry": runtime_registry(),
        "schema": SCHEMA_PIPELINE,
        "train": False,
        "reserve_scored": False,
        "runtime_threshold_search": False,
    }


def build_pipeline_forward(
    *,
    stage_a_decision: str,
    p_relation: float,
    p_resolvable: float,
) -> dict[str, Any]:
    """Stage-A slice of the sealed pipeline forward packet."""
    stage_a = build_canonical_forward(
        stage_a_decision=stage_a_decision,
        p_relation=p_relation,
        p_resolvable=p_resolvable,
    )
    entry = stage_b_entry_from_stage_a(stage_a_decision)
    return {
        "stage_a_decision": stage_a["stage_a_decision"],
        "p_relation": stage_a["p_relation"],
        "p_resolvable": stage_a["p_resolvable"],
        "stage_b_permitted": bool(entry["stage_b_permitted"]),
        "stage_a_entry_action": entry["action"],
        "relation_threshold": CANONICAL_RELATION_THRESHOLD,
        "resolvability_threshold": CANONICAL_RESOLVABILITY_THRESHOLD,
        "stage_a_checkpoint_sha": STAGE_A_BEST_SHA256,
        "stage_b_index_sha": FROZEN_INDEX_SHA256,
        "pipeline_version": PIPELINE_ID,
        "schema": SCHEMA_PIPELINE_FORWARD,
    }


def integrate_text_probabilities(
    *,
    p_relation: float,
    p_resolvable: float,
) -> dict[str, Any]:
    """Read-only Stage-A → Stage-B entry integration from probabilities."""
    decision = decide_canonical_stage_a(
        p_relation=p_relation, p_resolvable=p_resolvable
    )
    forward = build_pipeline_forward(
        stage_a_decision=decision,
        p_relation=p_relation,
        p_resolvable=p_resolvable,
    )
    entry = stage_b_entry_from_stage_a(decision)
    return {
        "forward": forward,
        "stage_a_decision": decision,
        "stage_b_entry": entry,
        "invokes_stage_b": bool(entry["stage_b_permitted"]),
    }


def build_pipeline_freeze_receipt(
    *,
    code_revision: str,
    integration: Mapping[str, Any],
    frozen_at: str,
) -> dict[str, Any]:
    payload = {
        "BEST_MUTATED": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "NEXT_ACTION": "SEAL_AND_PACKAGE_HYPERLEX_V5_STAGE_A_B_V1R2_PIPELINE",
        "PIPELINE_ID": PIPELINE_ID,
        "PIPELINE_RULE": PIPELINE_RULE,
        "RESERVE_CONSUMED": False,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_A_CANONICAL": CANONICAL_ID,
        "STAGE_A_RESEARCH_LOOP": STAGE_A_RESEARCH_LOOP,
        "TRAIN": False,
        "V5_STAGE_A_STATE": V5_STAGE_A_STATE,
        "V5_STAGE_B_STATE": V5_STAGE_B_STATE,
        "V5_STAGE_A_B_PIPELINE_STATE": V5_STAGE_A_B_PIPELINE_STATE,
        "code_revision": code_revision,
        "contract": pipeline_contract(),
        "frozen_at": frozen_at,
        "integration": dict(integration),
        "schema": SCHEMA_PIPELINE,
    }
    payload["PIPELINE_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {k: v for k, v in payload.items() if k != "PIPELINE_RECEIPT_SHA256"}
        )
    )
    return payload
