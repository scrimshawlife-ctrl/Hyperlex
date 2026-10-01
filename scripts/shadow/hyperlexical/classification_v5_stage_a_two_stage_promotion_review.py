"""REVIEW_V5_STAGE_A_TWO_STAGE_PROMOTION — read-only promotion readiness.

Does not train, score reserve, alter thresholds, or move BEST.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import (
    ACCEPTANCE_GATES,
    BEST_SHA,
    canonical_json,
    evaluate_decisions,
    sha256_text,
)
from .classification_v5_stage_a_two_stage import (
    ARCHITECTURE_RECEIPT_SHA256,
    AUTHORIZED_AUTH_RECEIPT_SHA256,
    AUTHORIZED_BEST_SHA,
    AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
    AUTHORIZED_DATASET_SHA,
    AUTHORIZED_TRAINING_CONFIG_SHA256,
    EXPERIMENT_ID,
    GATE1_THRESHOLDS,
    GATE2_PRESENT_THRESHOLDS,
    TRAIN_ONCE_ACTION,
    TRAIN_RULE,
    TWO_STAGE_RULE,
    decide_two_stage,
)

REVIEW_RULE = "REVIEW_V5_STAGE_A_TWO_STAGE_PROMOTION"
PROMOTE_ACTION = "PROMOTE_V5_STAGE_A_TWO_STAGE_SELECTED"
SCHEMA_REVIEW = "hyperlex.classification.v5.stage_a_two_stage_promotion_review.v1"

EXPECTED_SELECTED_CHECKPOINT_SHA256 = (
    "cd2829c1b5fb823fc03f18efe66a7387124ef44be2545b9e385a17eb6237bf5c"
)
EXPECTED_SELECTED_EPOCH = 11
EXPECTED_GATE1_THRESHOLD = 0.75
EXPECTED_GATE2_PRESENT_THRESHOLD = 0.50
EXPECTED_SPLIT_WITNESS_SHA256 = (
    "ecb88025b1b3355d837a2d81cbd87909d2f961e8800adbef21589c5f3b564fb1"
)
EXPECTED_RUN_RECEIPT_SHA256 = (
    "9c358d2cae25bfe75b4825c30b7334573897eef7ed9615a56f57041db6e444db"
)
EXPECTED_N_GRID = 100
EXPECTED_N_PASSING = 4

# Settled validation metrics (parity targets).
EXPECTED_METRICS = {
    "EVIDENCE_PRESENT_recall": 0.7048665620094191,
    "NO_EVIDENCE_recall": 0.9089456869009584,
    "UNCERTAIN_recall": 0.6790123456790124,
    "false_evidence_entry_rate_on_none": 0.04233226837060703,
    "stage_a_macro_f1": 0.7411485290305739,
}

METRIC_ABS_TOL = 1e-9

CANONICAL_INFERENCE = {
    "gate1_threshold": EXPECTED_GATE1_THRESHOLD,
    "gate2_present_threshold": EXPECTED_GATE2_PRESENT_THRESHOLD,
    "policy": (
        "if P(POSSIBLE_EVIDENCE) < 0.75 -> NO_EVIDENCE; "
        "else if P(CONFIRMED_PRESENT) >= 0.50 -> EVIDENCE_PRESENT; "
        "else UNCERTAIN"
    ),
    "runtime_threshold_search": False,
    "scalar_three_state_forbidden": True,
}

KNOWN_LIMITATIONS = [
    {
        "id": "OBSERVED_PRESENT_RECALL",
        "status": "KNOWN_LIMITATION",
        "value": 0.657,
        "note": "Below aggregate PRESENT gate; no frozen OBSERVED subgroup gate.",
    },
    {
        "id": "OBSERVED_NONE_RECALL",
        "status": "KNOWN_LIMITATION",
        "value": 0.883,
        "note": "Below aggregate NONE gate; no frozen OBSERVED subgroup gate.",
    },
    {
        "id": "OBSERVED_FALSE_ENTRY",
        "status": "KNOWN_LIMITATION",
        "value": 0.054,
        "note": "Above aggregate false-entry gate; no frozen OBSERVED subgroup gate.",
    },
    {
        "id": "ATOM_PRESENT_RECALL",
        "status": "KNOWN_LIMITATION",
        "value": 0.696,
        "note": "Near aggregate PRESENT gate; no frozen ATOM subgroup gate.",
    },
]


def metric_parity(
    actual: Mapping[str, float],
    expected: Mapping[str, float],
    *,
    tol: float = METRIC_ABS_TOL,
) -> dict[str, Any]:
    deltas = {}
    ok = True
    for key, exp in expected.items():
        act = float(actual[key])
        delta = abs(act - float(exp))
        deltas[key] = {"actual": act, "delta": delta, "expected": float(exp)}
        if delta > tol:
            ok = False
    return {"deltas": deltas, "pass": ok, "tolerance_abs": tol}


def verify_settlement_integrity(
    *,
    auth: Mapping[str, Any],
    resolved: Mapping[str, Any],
    weights: Mapping[str, Any],
    witness: Mapping[str, Any],
    receipt: Mapping[str, Any],
    selected_manifest: Mapping[str, Any],
    threshold_grid: Mapping[str, Any],
    selected_checkpoint_sha256: str,
) -> dict[str, Any]:
    checks = {
        "authorization_receipt": auth.get("receipt_sha256")
        == AUTHORIZED_AUTH_RECEIPT_SHA256,
        "dataset_sha": auth.get("DATASET_SHA256") == AUTHORIZED_DATASET_SHA
        and resolved.get("dataset_sha256") == AUTHORIZED_DATASET_SHA,
        "training_config_sha": auth.get("TRAINING_CONFIG_SHA256")
        == AUTHORIZED_TRAINING_CONFIG_SHA256
        and resolved.get("training_config_sha256")
        == AUTHORIZED_TRAINING_CONFIG_SHA256,
        "class_weight_artifact_sha": auth.get("CLASS_WEIGHT_ARTIFACT_SHA256")
        == AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256
        and weights.get("CLASS_WEIGHT_ARTIFACT_SHA256")
        == AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
        "architecture_receipt": auth.get("ARCHITECTURE_RECEIPT_SHA256")
        == ARCHITECTURE_RECEIPT_SHA256,
        "split_witness": witness.get("TWO_STAGE_SPLIT_WITNESS_SHA256")
        == EXPECTED_SPLIT_WITNESS_SHA256,
        "selected_checkpoint_hash": selected_checkpoint_sha256
        == EXPECTED_SELECTED_CHECKPOINT_SHA256
        and receipt.get("SELECTED_CHECKPOINT_SHA256")
        == EXPECTED_SELECTED_CHECKPOINT_SHA256
        and selected_manifest.get("checkpoint_sha256")
        == EXPECTED_SELECTED_CHECKPOINT_SHA256,
        "selected_epoch": int(receipt.get("restored_epoch") or -1)
        == EXPECTED_SELECTED_EPOCH
        and int(selected_manifest.get("restored_epoch") or -1)
        == EXPECTED_SELECTED_EPOCH,
        "threshold_grid_n": int(threshold_grid.get("n_candidates") or 0)
        == EXPECTED_N_GRID
        and len(GATE1_THRESHOLDS) * len(GATE2_PRESENT_THRESHOLDS) == EXPECTED_N_GRID,
        "n_passing": int(threshold_grid.get("n_passing") or -1) == EXPECTED_N_PASSING,
        "selected_thresholds_frozen_rule": (
            float((receipt.get("selected_thresholds") or {}).get("gate1_threshold"))
            == EXPECTED_GATE1_THRESHOLD
            and float(
                (receipt.get("selected_thresholds") or {}).get(
                    "gate2_present_threshold"
                )
            )
            == EXPECTED_GATE2_PRESENT_THRESHOLD
        ),
        "acceptance_gates_pass": bool(
            all(
                (receipt.get("acceptance_gates") or {}).get(name, {}).get("pass")
                for name in (
                    "false_evidence_entry_rate_on_none",
                    "EVIDENCE_PRESENT_recall",
                    "NO_EVIDENCE_recall",
                )
            )
        ),
        "scientific_settled_pass": receipt.get("SCIENTIFIC_RESULT") == "SETTLED_PASS",
        "experiment_id": auth.get("EXPERIMENT_ID") == EXPERIMENT_ID
        and receipt.get("EXPERIMENT_ID") == EXPERIMENT_ID,
        "run_receipt_sha": receipt.get("RUN_RECEIPT_SHA256")
        == EXPECTED_RUN_RECEIPT_SHA256
        or receipt.get("receipt_sha256") == EXPECTED_RUN_RECEIPT_SHA256,
        "current_best_unchanged": AUTHORIZED_BEST_SHA == BEST_SHA,
    }
    return {
        "checks": checks,
        "pass": all(checks.values()),
        "result": "PASS" if all(checks.values()) else "INVALID",
    }


# SELECTED safetensors retain only the last-2-layer ModernBERT overlay (no biases)
# plus Gate1/Gate2 heads — sealed train collect_encoder_trainable contract.
EXPECTED_ENCODER_OVERLAY_TENSORS = 12
EXPECTED_ENCODER_LAYER_PREFIXES = ("encoder.layers.20.", "encoder.layers.21.")


def verify_architecture_identity(tensor_keys: Sequence[str]) -> dict[str, Any]:
    keys = list(tensor_keys)
    prefixes = sorted({k.split(".")[0] for k in keys})
    encoder_n = sum(1 for k in keys if k.startswith("encoder."))
    layer20 = sum(1 for k in keys if k.startswith(EXPECTED_ENCODER_LAYER_PREFIXES[0]))
    layer21 = sum(1 for k in keys if k.startswith(EXPECTED_ENCODER_LAYER_PREFIXES[1]))
    earlier = any(
        k.startswith("encoder.layers.")
        and not k.startswith(EXPECTED_ENCODER_LAYER_PREFIXES[0])
        and not k.startswith(EXPECTED_ENCODER_LAYER_PREFIXES[1])
        for k in keys
    )
    checks = {
        "has_gate1_head": any(k.startswith("gate1_head.") for k in keys),
        "has_gate2_head": any(k.startswith("gate2_head.") for k in keys),
        "no_flat_evidence_head": not any(k.startswith("evidence_head.") for k in keys),
        "has_encoder_tensors": encoder_n > 0,
        # Last-2-layer weight overlay only (ModernBERT layers 20/21, 6 tensors each).
        "encoder_trainable_overlay_count_12": encoder_n
        == EXPECTED_ENCODER_OVERLAY_TENSORS,
        "last_two_layers_adapted": layer20 == 6 and layer21 == 6,
        "earlier_layers_not_in_overlay": not earlier,
        "gate1_weight_shape_hint": "gate1_head.weight" in keys,
        "gate2_weight_shape_hint": "gate2_head.weight" in keys,
        "gate1_2logit_bias": "gate1_head.bias" in keys,
        "gate2_2logit_bias": "gate2_head.bias" in keys,
    }
    return {
        "checks": checks,
        "encoder_tensor_count": encoder_n,
        "last_trainable_layers": 2,
        "pass": all(checks.values()),
        "prefixes": prefixes,
        "shared_encoder": True,
        "flat_3way_canonical": False,
    }


def verify_threshold_selection_rule(
    *,
    threshold_grid: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    chosen = threshold_grid.get("chosen") or {}
    if not chosen:
        # Settled receipt may nest chosen under metrics-bearing object.
        chosen = (threshold_grid.get("chosen") or {}) if threshold_grid.get("feasible") else {}
    selected = receipt.get("selected_thresholds") or {}
    ok = (
        float(selected.get("gate1_threshold")) == EXPECTED_GATE1_THRESHOLD
        and float(selected.get("gate2_present_threshold"))
        == EXPECTED_GATE2_PRESENT_THRESHOLD
        and int(threshold_grid.get("n_passing") or -1) == EXPECTED_N_PASSING
        and int(threshold_grid.get("n_candidates") or -1) == EXPECTED_N_GRID
    )
    return {
        "canonical_thresholds": dict(CANONICAL_INFERENCE),
        "pass": ok,
        "selected_thresholds": dict(selected),
    }


def residual_risk_review() -> dict[str, Any]:
    return {
        "aggregate_acceptance_unaffected": True,
        "frozen_subgroup_gates_exist": False,
        "known_limitations": list(KNOWN_LIMITATIONS),
        "note": (
            "Subgroup diagnostics weaker than aggregate gates remain "
            "KNOWN_LIMITATION; they do not invalidate SETTLED_PASS absent "
            "frozen subgroup acceptance requirements."
        ),
    }


def compatibility_review() -> dict[str, Any]:
    return {
        "api_compatibility": {
            "semantic_outputs_unchanged": [
                "NO_EVIDENCE",
                "EVIDENCE_PRESENT",
                "UNCERTAIN",
            ],
            "breaking_internal_head_interface": True,
            "note": (
                "Callers consuming a single P(PRESENT) scalar / flat 3-logit head "
                "must migrate to decide_two_stage(p_possible, p_confirmed)."
            ),
        },
        "canonical_architecture_change": True,
        "checkpoint_loading_change": True,
        "downstream_stage_b_entry": {
            "impact": "CONTRACT_PRESERVED_AT_SEMANTIC_LAYER",
            "note": (
                "Stage-B / family-retrieval may continue to consume the three "
                "semantic labels; probability channel changes from one scalar to "
                "two gate probabilities."
            ),
        },
        "family_retrieval_integration": {
            "impact": "ADAPTER_REQUIRED_IF_CONSUMING_LOGITS",
            "semantic_label_vocabulary_unchanged": True,
        },
        "migration_map": {
            "from": {
                "architecture": "flat_3_logit_head",
                "decision": "decide_evidence(P_EVIDENCE_PRESENT)",
                "status": "DEPRECATED_FOR_V5_STAGE_A_CANONICAL_DECISION",
            },
            "to": {
                "architecture": "gate1_2logit + gate2_2logit",
                "decision": CANONICAL_INFERENCE["policy"],
                "outputs": ["NO_EVIDENCE", "EVIDENCE_PRESENT", "UNCERTAIN"],
            },
        },
        "runtime_decision_packet_change": True,
        "schemas": {
            "forward_contract": "hyperlex.classification.v5.stage_a_two_stage_forward.v1",
            "historical_flat_retained": True,
        },
    }


def best_semantics_recommendation() -> dict[str, Any]:
    return {
        "current_BEST": AUTHORIZED_BEST_SHA,
        "current_BEST_meaning": (
            "Broader Hyperlex encoder artifact "
            "(hyperlex-encoder-modernbert-base-seed-select004); used as Stage-A "
            "initialization parent, not Stage-A decision head."
        ),
        "overwrite_model_wide_BEST": False,
        "recommendation": "STAGE_A_BEST",
        "reason": (
            "Repository BEST currently denotes the broader encoder seed, not the "
            "Stage-A evidence decision architecture. Prefer component-scoped "
            "STAGE_A_BEST pointing at SELECTED cd2829c1…."
        ),
        "proposed_STAGE_A_BEST": EXPECTED_SELECTED_CHECKPOINT_SHA256,
    }


def reserve_policy_determination() -> dict[str, Any]:
    return {
        "existing_policy_requires_reserve_before_internal_adoption": False,
        "existing_policy_requires_reserve_before_production_promotion": False,
        "fresh_reserve_required_for_internal_canonical_adoption": False,
        "fresh_reserve_required_for_production_promotion": False,
        "note": (
            "Stage-A V5 contracts treat reserve as unused/non-authorizing for "
            "settlement; no frozen Stage-A rule invents a pre-promotion reserve "
            "score for this component. Family-retrieval reserves remain out of scope."
        ),
        "reserve_consumed": False,
        "reserve_scored_in_review": False,
    }


def choose_promotion_decision(
    *,
    integrity_pass: bool,
    replay_pass: bool,
    architecture_pass: bool,
) -> dict[str, Any]:
    if not integrity_pass:
        return {
            "PROMOTION_DECISION": "PROMOTION_REVIEW_INVALID",
            "NEXT_ACTION": "STOP",
            "promote": False,
        }
    if not replay_pass or not architecture_pass:
        return {
            "PROMOTION_DECISION": "PROMOTION_BLOCKED",
            "NEXT_ACTION": "STOP",
            "promote": False,
        }
    return {
        "PROMOTION_DECISION": "PROMOTION_READY",
        "NEXT_ACTION": PROMOTE_ACTION,
        "promote": False,
        "note": "Ready for a separate explicit promotion action; not promoted here.",
    }


def build_promotion_review_receipt(
    *,
    integrity: Mapping[str, Any],
    architecture: Mapping[str, Any],
    replay: Mapping[str, Any],
    threshold_rule: Mapping[str, Any],
    code_revision: str,
) -> dict[str, Any]:
    decision = choose_promotion_decision(
        integrity_pass=bool(integrity.get("pass")),
        replay_pass=bool(replay.get("pass")),
        architecture_pass=bool(architecture.get("pass")),
    )
    payload = {
        "ARCHITECTURE_RECEIPT_SHA256": ARCHITECTURE_RECEIPT_SHA256,
        "AUTHORIZATION_RECEIPT_SHA256": AUTHORIZED_AUTH_RECEIPT_SHA256,
        "BEST": "UNCHANGED",
        "BEST_SHA256": AUTHORIZED_BEST_SHA,
        "CLASS_WEIGHT_ARTIFACT_SHA256": AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
        "CURRENT_BEST": AUTHORIZED_BEST_SHA,
        "DATASET_SHA256": AUTHORIZED_DATASET_SHA,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "NEXT_ACTION": decision["NEXT_ACTION"],
        "PROMOTION_DECISION": decision["PROMOTION_DECISION"],
        "PROMOTION_REVIEW": "VALID" if integrity.get("pass") else "INVALID",
        "RESERVE": "unused",
        "REVIEW_RULE": REVIEW_RULE,
        "RUN_RECEIPT_SHA256": EXPECTED_RUN_RECEIPT_SHA256,
        "SELECTED_CHECKPOINT_SHA256": EXPECTED_SELECTED_CHECKPOINT_SHA256,
        "SELECTED_EPOCH": EXPECTED_SELECTED_EPOCH,
        "TRAIN": False,
        "TRAINING_CONFIG_SHA256": AUTHORIZED_TRAINING_CONFIG_SHA256,
        "TWO_STAGE_SPLIT_WITNESS_SHA256": EXPECTED_SPLIT_WITNESS_SHA256,
        "acceptance_gates": dict(ACCEPTANCE_GATES),
        "architecture_identity": dict(architecture),
        "best_semantics": best_semantics_recommendation(),
        "canonical_inference_contract": dict(CANONICAL_INFERENCE),
        "code_revision": code_revision,
        "compatibility": compatibility_review(),
        "parent_train_rule": TRAIN_RULE,
        "parent_two_stage_rule": TWO_STAGE_RULE,
        "promote": False,
        "replay": dict(replay),
        "reserve_policy": reserve_policy_determination(),
        "residual_risks": residual_risk_review(),
        "schema": SCHEMA_REVIEW,
        "settlement_integrity": dict(integrity),
        "threshold_rule": dict(threshold_rule),
    }
    payload["review_receipt_sha256"] = sha256_text(
        canonical_json(
            {k: v for k, v in payload.items() if k != "review_receipt_sha256"}
        )
    )
    return payload


def replay_decisions(
    *,
    golds: Sequence[str],
    p_possible: Sequence[float],
    p_confirmed: Sequence[float],
    gate1_threshold: float = EXPECTED_GATE1_THRESHOLD,
    gate2_present_threshold: float = EXPECTED_GATE2_PRESENT_THRESHOLD,
) -> dict[str, Any]:
    decisions = [
        decide_two_stage(
            p_possible=float(pp),
            p_confirmed=float(pc),
            gate1_threshold=gate1_threshold,
            gate2_present_threshold=gate2_present_threshold,
        )
        for pp, pc in zip(p_possible, p_confirmed)
    ]
    metrics = evaluate_decisions(golds, decisions)
    compact = {
        "EVIDENCE_PRESENT_recall": metrics["by_label"]["EVIDENCE_PRESENT"]["recall"],
        "NO_EVIDENCE_recall": metrics["by_label"]["NO_EVIDENCE"]["recall"],
        "UNCERTAIN_recall": metrics["by_label"]["UNCERTAIN"]["recall"],
        "false_evidence_entry_rate_on_none": metrics[
            "false_evidence_entry_rate_on_none"
        ],
        "gate1_threshold": gate1_threshold,
        "gate2_present_threshold": gate2_present_threshold,
        "stage_a_macro_f1": metrics["stage_a_macro_f1"],
    }
    parity = metric_parity(
        {
            k: compact[k]
            for k in EXPECTED_METRICS
        },
        EXPECTED_METRICS,
    )
    # Thresholds must match exactly.
    thr_ok = (
        float(compact["gate1_threshold"]) == EXPECTED_GATE1_THRESHOLD
        and float(compact["gate2_present_threshold"])
        == EXPECTED_GATE2_PRESENT_THRESHOLD
    )
    replay_hash = sha256_text(canonical_json(compact))
    return {
        "metrics": compact,
        "parity": parity,
        "pass": bool(parity["pass"] and thr_ok),
        "replay_hash": replay_hash,
        "thresholds_match": thr_ok,
    }
