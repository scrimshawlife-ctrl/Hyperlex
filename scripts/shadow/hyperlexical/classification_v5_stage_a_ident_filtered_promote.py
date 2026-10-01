"""PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE — Stage-A promotion.

Promotes the V1R2 ident-filtered factorized SETTLED_PASS checkpoint to
STAGE_A_BEST. Does not retrain, alter thresholds/V1R2, restore excluded
rows, score spent reserve, mutate MODEL_WIDE_BEST, or retune Stage B.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import (
    BEST_SHA,
    EVIDENCE_LABELS,
    FLAT_RUNTIME_STATUS as STAGE_A_FLAT_RUNTIME_STATUS,
    canonical_json,
    evaluate_decisions,
    sha256_text,
)
from .classification_v5_stage_a_factorized_objective import (
    OBJECTIVE_ID,
    OBJECTIVE_RECEIPT_SHA256_PIN,
    POSSIBLE_EVIDENCE_STATUS as OBJECTIVE_POSSIBLE_EVIDENCE_STATUS,
    decide_stage_a,
)
from .classification_v5_stage_a_gold_identifiability_contract import (
    CONTRACT_ID,
    MODEL_INPUT,
)
from .classification_v5_stage_a_gold_identifiability_filter import (
    CONTRACT_RECEIPT_SHA256_PIN,
    FILTER_RECEIPT_SHA256_PIN,
    SURFACE_ID,
    V1R2_ANNOTATION_SHA256_PIN,
    V1R2_DATASET_SHA256_PIN,
    V1R2_EXCLUSION_MANIFEST_SHA256_PIN,
)
from .classification_v5_stage_a_ident_filtered_authorize import (
    AUTHORIZED_AUTH_RECEIPT_SHA256,
    AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
    AUTHORIZED_TRAINING_CONFIG_SHA256,
    EXPERIMENT_ID,
    EXPLICIT_LIMITATIONS,
    SHORT_ATOM_POSITIVE_GENERALIZATION,
)
from .classification_v5_stage_a_two_stage_generalization import (
    PARENT_STAGE_A_BEST_SHA,
    SPENT_RESERVE,
    SPENT_RESERVE_STATUS,
)

PROMOTE_RULE = "PROMOTE_STAGE_A_IDENT_FILTERED_FACTORIZED_CANDIDATE"
SCHEMA_PROMOTION = (
    "hyperlex.classification.v5.stage_a_ident_filtered_factorized_promotion.v1"
)
SCHEMA_STAGE_A_BEST = "hyperlex.classification.v5.stage_a_best_pointer.v1"
NEXT_ACTION_ON_PASS = (
    "FREEZE_V5_STAGE_A_CANONICAL_AND_UPDATE_DOWNSTREAM_PROVENANCE"
)

STAGE_A_BEST_SHA256 = (
    "8b2de4472dc0ebd65a6b4b7577dc3272d63db2490a1b6f6dbbcc54db50077e41"
)
STAGE_A_BEST_EPOCH = 11
PREVIOUS_STAGE_A_BEST_SHA256 = PARENT_STAGE_A_BEST_SHA  # cd2829c1…
MODEL_WIDE_BEST_SHA256 = BEST_SHA
PARENT_ENCODER_BEST_SHA256 = BEST_SHA
assert PARENT_ENCODER_BEST_SHA256 == MODEL_WIDE_BEST_SHA256

CANONICAL_RELATION_THRESHOLD = 0.60
CANONICAL_RESOLVABILITY_THRESHOLD = 0.75

EXPECTED_RUN_RECEIPT_SHA256 = (
    "4a7d565ca607234c604bcec40acab33e3cbecc4da6e4adc86a0b2b79bb091a4b"
)

EXPECTED_METRICS = {
    "false_evidence_entry_rate_on_none": 0.03356890459363958,
    "EVIDENCE_PRESENT_recall": 0.951310861423221,
    "NO_EVIDENCE_recall": 0.9646643109540636,
    "stage_a_macro_f1": 0.9597164476304262,
}
DISPLAY_METRICS = {
    "false_entry": 0.034,
    "PRESENT_recall": 0.951,
    "NONE_recall": 0.965,
}
METRIC_ABS_TOL = 1e-9

EXPECTED_SHORT_ATOM = {
    "SHORT_ATOM_NONE": {
        "n": 152,
        "relation_false_positive_rate": 0.013157894736842105,
        "NONE_recall": 0.9802631578947368,
    },
    "SHORT_ATOM_PRESENT": {
        "n": 4,
        "relation_recall": 0.75,
        "status": "LOW_SUPPORT",
    },
}

CANONICAL_LOAD_SEQUENCE = (
    "modernbert_trunk",
    "model_wide_BEST_encoder_overlay",
    "STAGE_A_BEST_adapted_layers_20_21",
    "relation_head",
    "resolvability_head",
)

CANONICAL_FORWARD_SCHEMA = (
    "hyperlex.classification.v5.stage_a_factorized_forward.v1"
)
CANONICAL_INFERENCE_POLICY = (
    "if P(RESOLVABLE) < 0.75 -> UNCERTAIN; "
    "else if P(EVIDENCE_RELATION_PRESENT) >= 0.60 -> EVIDENCE_PRESENT; "
    "else NO_EVIDENCE"
)

POSSIBLE_EVIDENCE_STATUS = "DEPRECATED_AS_CANONICAL_STAGE_A_TRAINING_TARGET"
assert OBJECTIVE_POSSIBLE_EVIDENCE_STATUS.startswith("DEPRECATED")

FLAT_RUNTIME_STATUS = STAGE_A_FLAT_RUNTIME_STATUS
TWO_STAGE_RUNTIME_STATUS = "HISTORICAL"
SUPERSEDED_STAGE_A_BEST_STATUS = "SUPERSEDED_STAGE_A_BEST"
FLAT_ALLOWED_USES = (
    "historical_replay",
    "scientific_comparison",
    "compatibility_diagnostics",
)

PROVENANCE_NOTE = (
    "Promotion validates Stage A on the identifiability-filtered text-only "
    "contract. It does not establish performance for context-dependent gold "
    "excluded from V1R2."
)


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def preflight_promotion(
    *,
    train_receipt: Mapping[str, Any],
    selected_checkpoint_sha256: str,
    model_wide_best_sha256: str,
    current_stage_a_best_sha256: str,
    dataset_sha256: str,
    annotation_sha256: str,
    exclusion_manifest_sha256: str,
    v1r2_mutated: bool,
) -> dict[str, Any]:
    gates = train_receipt.get("acceptance_gates") or {}
    thr = train_receipt.get("selected_thresholds") or {}

    def _gate_value(name: str) -> float:
        return float((gates.get(name) or {}).get("value") or -1.0)

    checks = {
        "scientific_settled_pass": train_receipt.get("SCIENTIFIC_RESULT")
        == "SETTLED_PASS",
        "promotion_candidate": train_receipt.get("promotion_candidate") is True,
        "experiment": train_receipt.get("EXPERIMENT_ID") == EXPERIMENT_ID,
        "surface_sha": dataset_sha256 == V1R2_DATASET_SHA256_PIN
        and train_receipt.get("DATASET_SHA256") == V1R2_DATASET_SHA256_PIN,
        "annotation_sha": annotation_sha256 == V1R2_ANNOTATION_SHA256_PIN
        and train_receipt.get("ANNOTATION_SHA256") == V1R2_ANNOTATION_SHA256_PIN,
        "exclusion_manifest_sha": exclusion_manifest_sha256
        == V1R2_EXCLUSION_MANIFEST_SHA256_PIN
        and train_receipt.get("EXCLUSION_MANIFEST_SHA256")
        == V1R2_EXCLUSION_MANIFEST_SHA256_PIN,
        "authorization_receipt": train_receipt.get("AUTHORIZATION_RECEIPT_SHA256")
        == AUTHORIZED_AUTH_RECEIPT_SHA256,
        "training_config_sha": train_receipt.get("TRAINING_CONFIG_SHA256")
        == AUTHORIZED_TRAINING_CONFIG_SHA256,
        "class_weight_artifact_sha": train_receipt.get("CLASS_WEIGHT_ARTIFACT_SHA256")
        == AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
        "selected_checkpoint": selected_checkpoint_sha256 == STAGE_A_BEST_SHA256
        and train_receipt.get("SELECTED_CHECKPOINT_SHA256") == STAGE_A_BEST_SHA256,
        "selected_epoch": int(train_receipt.get("restored_epoch") or -1)
        == STAGE_A_BEST_EPOCH,
        "relation_threshold": float(thr.get("relation_threshold") or -1.0)
        == CANONICAL_RELATION_THRESHOLD,
        "resolvability_threshold": float(thr.get("resolvability_threshold") or -1.0)
        == CANONICAL_RESOLVABILITY_THRESHOLD,
        "false_entry_gate": _gate_value("false_evidence_entry_rate_on_none") <= 0.05
        and bool((gates.get("false_evidence_entry_rate_on_none") or {}).get("pass")),
        "present_recall_gate": _gate_value("EVIDENCE_PRESENT_recall") >= 0.70
        and bool((gates.get("EVIDENCE_PRESENT_recall") or {}).get("pass")),
        "none_recall_gate": _gate_value("NO_EVIDENCE_recall") >= 0.90
        and bool((gates.get("NO_EVIDENCE_recall") or {}).get("pass")),
        "v1r2_unchanged": v1r2_mutated is False
        and train_receipt.get("V1R2_MUTATED") is False,
        "spent_reserve_status": train_receipt.get("RESERVE") == SPENT_RESERVE_STATUS
        or train_receipt.get("SPENT_RESERVE") == SPENT_RESERVE,
        "model_wide_best": model_wide_best_sha256 == MODEL_WIDE_BEST_SHA256,
        "current_stage_a_best": current_stage_a_best_sha256
        == PREVIOUS_STAGE_A_BEST_SHA256,
        "run_receipt": train_receipt.get("RUN_RECEIPT_SHA256")
        == EXPECTED_RUN_RECEIPT_SHA256,
        "objective": train_receipt.get("OBJECTIVE_ID") == OBJECTIVE_ID,
    }
    return {
        "checks": checks,
        "pass": all(checks.values()),
        "result": "PASS" if all(checks.values()) else "PROMOTION_INVALID",
    }


def decide_canonical_stage_a(
    *,
    p_relation: float,
    p_resolvable: float,
) -> str:
    return decide_stage_a(
        p_evidence_relation_present=float(p_relation),
        p_resolvable=float(p_resolvable),
        relation_threshold=CANONICAL_RELATION_THRESHOLD,
        resolvability_threshold=CANONICAL_RESOLVABILITY_THRESHOLD,
    )


def stage_b_entry_from_stage_a(evidence_decision: str) -> dict[str, Any]:
    """Downstream adapter: Stage-B sees semantic labels only."""
    label = str(evidence_decision)
    if label not in EVIDENCE_LABELS:
        raise ValueError(f"unknown_stage_a_decision:{label}")
    if label == "EVIDENCE_PRESENT":
        return {
            "action": "PERMIT_STAGE_B",
            "evidence_decision": label,
            "family_retrieval": "PERMITTED",
            "stage_b_permitted": True,
        }
    if label == "NO_EVIDENCE":
        return {
            "action": "STOP",
            "evidence_decision": label,
            "family_retrieval": "FORBIDDEN",
            "stage_b_permitted": False,
        }
    return {
        "action": "ABSTAIN",
        "evidence_decision": label,
        "family_retrieval": "FORBIDDEN",
        "stage_b_permitted": False,
        "note": "UNCERTAIN stops before family retrieval",
    }


def may_invoke_stage_b(evidence_decision: str) -> bool:
    return bool(stage_b_entry_from_stage_a(evidence_decision)["stage_b_permitted"])


def verify_factorized_architecture(stage_a_tensor_keys: Sequence[str]) -> dict[str, Any]:
    keys = set(str(k) for k in stage_a_tensor_keys)
    checks = {
        "has_relation_head": "relation_head.weight" in keys
        and "relation_head.bias" in keys,
        "has_resolvability_head": "resolvability_head.weight" in keys
        and "resolvability_head.bias" in keys,
        "no_gate1_head": not any(k.startswith("gate1_head.") for k in keys),
        "no_gate2_head": not any(k.startswith("gate2_head.") for k in keys),
        "no_flat_evidence_head": not any(k.startswith("evidence_head.") for k in keys),
        "has_encoder_overlay": any(k.startswith("encoder.") for k in keys),
    }
    return {
        "checks": checks,
        "pass": all(checks.values()),
        "n_keys": len(keys),
        "architecture": (
            "shared ModernBERT + CLS + relation_head(2) + resolvability_head(2); "
            "last 2 encoder layers adapted"
        ),
    }


def verify_canonical_overlay(
    *,
    parent_best_sha256: str,
    stage_a_tensor_keys: Sequence[str],
) -> dict[str, Any]:
    arch = verify_factorized_architecture(stage_a_tensor_keys)
    checks = {
        "parent_best_matches": parent_best_sha256 == PARENT_ENCODER_BEST_SHA256,
        "architecture_identity": bool(arch.get("pass")),
        "no_legacy_possible_evidence_heads": bool(
            (arch.get("checks") or {}).get("no_gate1_head")
        )
        and bool((arch.get("checks") or {}).get("no_gate2_head")),
        "no_flat_evidence_head_canonical": bool(
            (arch.get("checks") or {}).get("no_flat_evidence_head")
        ),
        "has_factorized_heads": bool((arch.get("checks") or {}).get("has_relation_head"))
        and bool((arch.get("checks") or {}).get("has_resolvability_head")),
    }
    return {
        "architecture": arch,
        "checks": checks,
        "pass": all(checks.values()),
    }


def metric_parity(
    observed: Mapping[str, float],
    expected: Mapping[str, float],
    *,
    abs_tol: float = METRIC_ABS_TOL,
) -> dict[str, Any]:
    diffs = {}
    ok = True
    for key, exp in expected.items():
        obs = float(observed[key])
        delta = abs(obs - float(exp))
        diffs[key] = {"expected": float(exp), "observed": obs, "abs_delta": delta}
        if delta > abs_tol:
            ok = False
    return {"diffs": diffs, "pass": ok, "abs_tol": abs_tol}


def short_atom_diagnostics(
    *,
    rows: Sequence[Mapping[str, Any]],
    golds: Sequence[str],
    decisions: Sequence[str],
    p_relation: Sequence[float],
) -> dict[str, Any]:
    sa_none = [
        i
        for i, r in enumerate(rows)
        if r.get("primary_cell") == "SHORT_ATOM/NO_EVIDENCE"
    ]
    sa_pos = [
        i
        for i, r in enumerate(rows)
        if r.get("primary_cell") == "SHORT_ATOM/EVIDENCE_PRESENT"
    ]
    none_metrics = (
        evaluate_decisions(
            [golds[i] for i in sa_none], [decisions[i] for i in sa_none]
        )
        if sa_none
        else None
    )
    out = {
        "SHORT_ATOM_NONE": {
            "n": len(sa_none),
            "support": len(sa_none),
            "relation_false_positive_rate": (
                sum(
                    1
                    for i in sa_none
                    if float(p_relation[i]) >= CANONICAL_RELATION_THRESHOLD
                )
                / len(sa_none)
                if sa_none
                else None
            ),
            "NONE_recall": (
                none_metrics["by_label"]["NO_EVIDENCE"]["recall"]
                if none_metrics
                else None
            ),
        },
        "SHORT_ATOM_PRESENT": {
            "n": len(sa_pos),
            "support": len(sa_pos),
            "relation_recall": (
                sum(
                    1
                    for i in sa_pos
                    if float(p_relation[i]) >= CANONICAL_RELATION_THRESHOLD
                )
                / len(sa_pos)
                if sa_pos
                else None
            ),
            "status": SHORT_ATOM_POSITIVE_GENERALIZATION,
            "low_support_warning": True,
            "stable_subgroup_guarantee": False,
        },
    }
    parity = {
        "SHORT_ATOM_NONE_n": out["SHORT_ATOM_NONE"]["n"]
        == EXPECTED_SHORT_ATOM["SHORT_ATOM_NONE"]["n"],
        "SHORT_ATOM_NONE_fpr": abs(
            float(out["SHORT_ATOM_NONE"]["relation_false_positive_rate"] or -1)
            - EXPECTED_SHORT_ATOM["SHORT_ATOM_NONE"]["relation_false_positive_rate"]
        )
        <= METRIC_ABS_TOL,
        "SHORT_ATOM_NONE_recall": abs(
            float(out["SHORT_ATOM_NONE"]["NONE_recall"] or -1)
            - EXPECTED_SHORT_ATOM["SHORT_ATOM_NONE"]["NONE_recall"]
        )
        <= METRIC_ABS_TOL,
        "SHORT_ATOM_PRESENT_n": out["SHORT_ATOM_PRESENT"]["n"]
        == EXPECTED_SHORT_ATOM["SHORT_ATOM_PRESENT"]["n"],
        "SHORT_ATOM_PRESENT_recall": abs(
            float(out["SHORT_ATOM_PRESENT"]["relation_recall"] or -1)
            - EXPECTED_SHORT_ATOM["SHORT_ATOM_PRESENT"]["relation_recall"]
        )
        <= METRIC_ABS_TOL,
    }
    out["parity_pass"] = all(parity.values())
    out["parity"] = parity
    return out


def post_promotion_replay_check(
    *,
    golds: Sequence[str],
    p_relation: Sequence[float],
    p_resolvable: Sequence[float],
    rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    decisions = [
        decide_canonical_stage_a(p_relation=float(pr), p_resolvable=float(ps))
        for pr, ps in zip(p_relation, p_resolvable)
    ]
    metrics_full = evaluate_decisions(list(golds), decisions)
    observed = {
        "false_evidence_entry_rate_on_none": float(
            metrics_full["false_evidence_entry_rate_on_none"]
        ),
        "EVIDENCE_PRESENT_recall": float(
            metrics_full["by_label"]["EVIDENCE_PRESENT"]["recall"]
        ),
        "NO_EVIDENCE_recall": float(metrics_full["by_label"]["NO_EVIDENCE"]["recall"]),
        "stage_a_macro_f1": float(metrics_full["stage_a_macro_f1"]),
    }
    exact = metric_parity(observed, EXPECTED_METRICS)
    short_atom = None
    if rows is not None:
        short_atom = short_atom_diagnostics(
            rows=rows,
            golds=list(golds),
            decisions=decisions,
            p_relation=list(p_relation),
        )
    replay_body = {
        "metrics": observed,
        "thresholds": {
            "relation_threshold": CANONICAL_RELATION_THRESHOLD,
            "resolvability_threshold": CANONICAL_RESOLVABILITY_THRESHOLD,
        },
        "n": len(golds),
        "short_atom": short_atom,
    }
    replay_hash = sha256_text(canonical_json(replay_body))
    return {
        "display_targets": dict(DISPLAY_METRICS),
        "exact_parity": exact,
        "metrics": observed,
        "metrics_full": {
            "stage_a_macro_f1": metrics_full["stage_a_macro_f1"],
            "false_evidence_entry_rate_on_none": metrics_full[
                "false_evidence_entry_rate_on_none"
            ],
            "by_label": metrics_full["by_label"],
            "acceptance_pass": metrics_full["acceptance_pass"],
        },
        "pass": bool(
            exact["pass"]
            and metrics_full["acceptance_pass"]
            and (short_atom is None or short_atom.get("parity_pass"))
        ),
        "replay_hash": replay_hash,
        "short_atom_diagnostics": short_atom,
        "thresholds_match": True,
        "thresholds": {
            "relation_threshold": CANONICAL_RELATION_THRESHOLD,
            "resolvability_threshold": CANONICAL_RESOLVABILITY_THRESHOLD,
        },
    }


def canonical_load_contract() -> dict[str, Any]:
    return {
        "architecture": OBJECTIVE_ID,
        "fail_closed_if": [
            "parent_BEST_sha_mismatch",
            "stage_a_overlay_name_or_shape_mismatch",
            "missing_relation_or_resolvability_head",
            "gate1_or_gate2_head_loaded_as_canonical",
            "flat_evidence_head_loaded_as_canonical",
        ],
        "forward_schema": CANONICAL_FORWARD_SCHEMA,
        "relation_threshold": CANONICAL_RELATION_THRESHOLD,
        "resolvability_threshold": CANONICAL_RESOLVABILITY_THRESHOLD,
        "parent_encoder_best": PARENT_ENCODER_BEST_SHA256,
        "runtime_threshold_search": False,
        "sequence": list(CANONICAL_LOAD_SEQUENCE),
        "stage_a_best": STAGE_A_BEST_SHA256,
        "stage_a_parent_model_wide_best": PARENT_ENCODER_BEST_SHA256,
    }


def deprecated_path_status() -> dict[str, Any]:
    return {
        "flat_3_class_stage_a": {
            "status": "HISTORICAL",
            "runtime_status": FLAT_RUNTIME_STATUS,
            "allowed_uses": list(FLAT_ALLOWED_USES),
        },
        "two_stage_possible_evidence_architecture": {
            "status": "HISTORICAL",
            "runtime_status": TWO_STAGE_RUNTIME_STATUS,
            "checkpoint": PREVIOUS_STAGE_A_BEST_SHA256,
            "allowed_uses": list(FLAT_ALLOWED_USES),
        },
        "previous_STAGE_A_BEST": {
            "status": SUPERSEDED_STAGE_A_BEST_STATUS,
            "checkpoint_sha256": PREVIOUS_STAGE_A_BEST_SHA256,
            "retained_for": list(FLAT_ALLOWED_USES),
        },
        "POSSIBLE_EVIDENCE": POSSIBLE_EVIDENCE_STATUS,
        "historical_artifacts_deleted": False,
    }


def build_stage_a_best_pointer(
    *,
    weights_path: str,
    previous_stage_a_best: str | None,
    code_revision: str,
    promoted_at: str | None = None,
) -> dict[str, Any]:
    return {
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_A_BEST_EPOCH": STAGE_A_BEST_EPOCH,
        "architecture": OBJECTIVE_ID,
        "auto_relabel": False,
        "checkpoint_sha256": STAGE_A_BEST_SHA256,
        "code_revision": code_revision,
        "component": "STAGE_A",
        "context_dependent_definitive_gold_excluded": True,
        "experiment_id": EXPERIMENT_ID,
        "forward_schema": CANONICAL_FORWARD_SCHEMA,
        "gold_identifiability_contract_id": CONTRACT_ID,
        "gold_identifiability_contract_receipt_sha256": CONTRACT_RECEIPT_SHA256_PIN,
        "identifiability_filter_receipt_sha256": FILTER_RECEIPT_SHA256_PIN,
        "load_sequence": list(CANONICAL_LOAD_SEQUENCE),
        "model_input": list(MODEL_INPUT),
        "model_wide_BEST": MODEL_WIDE_BEST_SHA256,
        "model_wide_BEST_mutated": False,
        "objective_id": OBJECTIVE_ID,
        "objective_receipt_sha256": OBJECTIVE_RECEIPT_SHA256_PIN,
        "parent_encoder_best": PARENT_ENCODER_BEST_SHA256,
        "previous_STAGE_A_BEST": previous_stage_a_best,
        "promoted_at": promoted_at or utc_now_iso(),
        "promotion_rule": PROMOTE_RULE,
        "relation_threshold": CANONICAL_RELATION_THRESHOLD,
        "resolvability_threshold": CANONICAL_RESOLVABILITY_THRESHOLD,
        "schema": SCHEMA_STAGE_A_BEST,
        "semantic_outputs": list(EVIDENCE_LABELS),
        "stage_a_parent_model_wide_best": PARENT_ENCODER_BEST_SHA256,
        "surface_id": SURFACE_ID,
        "surface_dataset_sha256": V1R2_DATASET_SHA256_PIN,
        "weights_path": weights_path,
    }


def choose_promotion_state(
    *,
    preflight_pass: bool,
    overlay_pass: bool,
    post_replay_pass: bool,
) -> dict[str, Any]:
    if not preflight_pass:
        return {
            "STAGE_A_PROMOTION": "PROMOTION_INVALID",
            "PROMOTION_INVALID": True,
            "applied": False,
            "reason": "preflight_failed",
        }
    if not overlay_pass:
        return {
            "STAGE_A_PROMOTION": "PROMOTION_INVALID",
            "PROMOTION_INVALID": True,
            "applied": False,
            "reason": "overlay_verification_failed",
        }
    if not post_replay_pass:
        return {
            "STAGE_A_PROMOTION": "PROMOTION_INVALID",
            "PROMOTION_INVALID": True,
            "applied": False,
            "reason": "post_promotion_replay_mismatch",
            "restore_previous_STAGE_A_BEST": True,
        }
    return {
        "STAGE_A_PROMOTION": "APPLIED",
        "PROMOTION_INVALID": False,
        "applied": True,
        "reason": "ok",
    }


def build_promotion_receipt(
    *,
    preflight: Mapping[str, Any],
    pointer: Mapping[str, Any],
    overlay: Mapping[str, Any],
    post_replay: Mapping[str, Any],
    previous_stage_a_best: str | None,
    code_revision: str,
    promoted_at: str | None = None,
) -> dict[str, Any]:
    state = choose_promotion_state(
        preflight_pass=bool(preflight.get("pass")),
        overlay_pass=bool(overlay.get("pass")),
        post_replay_pass=bool(post_replay.get("pass")),
    )
    payload = {
        "ANNOTATION_SHA256": V1R2_ANNOTATION_SHA256_PIN,
        "AUTHORIZATION_RECEIPT_SHA256": AUTHORIZED_AUTH_RECEIPT_SHA256,
        "BEST_MUTATED": False,
        "CLASS_WEIGHT_ARTIFACT_SHA256": AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
        "CONTRACT_ID": CONTRACT_ID,
        "CONTRACT_RECEIPT_SHA256": CONTRACT_RECEIPT_SHA256_PIN,
        "DATASET_SHA256": V1R2_DATASET_SHA256_PIN,
        "EXCLUSION_MANIFEST_SHA256": V1R2_EXCLUSION_MANIFEST_SHA256_PIN,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "FILTER_RECEIPT_SHA256": FILTER_RECEIPT_SHA256_PIN,
        "MODEL_INPUT": list(MODEL_INPUT),
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "NEXT_ACTION": (
            NEXT_ACTION_ON_PASS
            if state["applied"]
            else "REPAIR_IDENT_FILTERED_FACTORIZED_CHECKPOINT_SERIALIZATION"
        ),
        "OBJECTIVE_ID": OBJECTIVE_ID,
        "OBJECTIVE_RECEIPT_SHA256": OBJECTIVE_RECEIPT_SHA256_PIN,
        "PARENT_ENCODER_BEST": PARENT_ENCODER_BEST_SHA256,
        "POSSIBLE_EVIDENCE": POSSIBLE_EVIDENCE_STATUS,
        "PROMOTION_INVALID": state["PROMOTION_INVALID"],
        "PROMOTE_RULE": PROMOTE_RULE,
        "RESERVE_CONSUMED": False,
        "RUN_RECEIPT_SHA256": EXPECTED_RUN_RECEIPT_SHA256,
        "SELECTED_CHECKPOINT_SHA256": STAGE_A_BEST_SHA256,
        "SELECTED_EPOCH": STAGE_A_BEST_EPOCH,
        "SPENT_RESERVE": SPENT_RESERVE,
        "SPENT_RESERVE_STATUS": SPENT_RESERVE_STATUS,
        "STAGE_A_BEST": (
            STAGE_A_BEST_SHA256 if state["applied"] else previous_stage_a_best
        ),
        "STAGE_A_PROMOTION": state["STAGE_A_PROMOTION"],
        "SURFACE_ID": SURFACE_ID,
        "TRAIN": False,
        "TRAINING_CONFIG_SHA256": AUTHORIZED_TRAINING_CONFIG_SHA256,
        "V1R2_MUTATED": False,
        "auto_relabel": False,
        "canonical_forward_schema": CANONICAL_FORWARD_SCHEMA,
        "canonical_inference_policy": CANONICAL_INFERENCE_POLICY,
        "canonical_load_path": canonical_load_contract(),
        "canonical_thresholds": {
            "relation_threshold": CANONICAL_RELATION_THRESHOLD,
            "resolvability_threshold": CANONICAL_RESOLVABILITY_THRESHOLD,
        },
        "code_revision": code_revision,
        "context_dependent_definitive_gold_excluded": True,
        "deprecated_paths": deprecated_path_status(),
        "explicit_limitations": dict(EXPLICIT_LIMITATIONS),
        "known_limitations": {
            "DOMAIN_IRRELEVANT_GENERALIZATION": "NOT_ESTABLISHED",
            "SHORT_ATOM_POSITIVE_GENERALIZATION": "LOW_SUPPORT",
            "provenance_note": PROVENANCE_NOTE,
        },
        "overlay_verification": dict(overlay),
        "pointer": dict(pointer) if state["applied"] else None,
        "post_promotion_replay": dict(post_replay),
        "preflight": dict(preflight),
        "previous_STAGE_A_BEST": previous_stage_a_best,
        "promoted_at": promoted_at or utc_now_iso(),
        "provenance_note": PROVENANCE_NOTE,
        "runtime_adapter": {
            "decide_canonical_stage_a": (
                "decide_stage_a(p_relation,p_resolvable;"
                "thr=0.60/0.75)"
            ),
            "semantic_outputs": list(EVIDENCE_LABELS),
            "internal_fields": [
                "p_relation",
                "p_resolvable",
                "relation_threshold",
                "resolvability_threshold",
            ],
            "stage_b_entry": {
                "EVIDENCE_PRESENT": "PERMIT_STAGE_B",
                "NO_EVIDENCE": "STOP",
                "UNCERTAIN": "ABSTAIN",
            },
            "stage_b_index_mutated": False,
            "stage_b_score_floor_mutated": False,
            "stage_b_margin_floor_mutated": False,
            "stage_b_family_ontology_mutated": False,
            "stage_b_parent_pin_update": "DEFERRED_TO_DOWNSTREAM_PROVENANCE",
        },
        "schema": SCHEMA_PROMOTION,
        "short_atom_diagnostics": (post_replay or {}).get("short_atom_diagnostics"),
        "stage_a_parent_model_wide_best": PARENT_ENCODER_BEST_SHA256,
        "state": dict(state),
    }
    payload["STAGE_A_PROMOTION_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in payload.items()
                if k != "STAGE_A_PROMOTION_RECEIPT_SHA256"
            }
        )
    )
    return payload
