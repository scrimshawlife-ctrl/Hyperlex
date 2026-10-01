"""DIAGNOSE_STAGE_A_FACTORIZED_RELATION_SETTLED_FAIL — read-only contract.

After factorized relation SETTLED_FAIL: determine whether SHORT_ATOM
inseparability is capacity/depth/pooling/input/identifiability.
Does not train, relabel, create surfaces, retune, use reserve, or move BEST.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_factorized_authorize import (
    AUTHORIZED_AUTH_RECEIPT_SHA256,
    AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
    AUTHORIZED_TRAINING_CONFIG_SHA256,
    EXPERIMENT_ID,
)
from .classification_v5_stage_a_factorized_objective import (
    FACTORIZED_ANNOTATION_SHA256_PIN,
    OBJECTIVE_ID,
    OBJECTIVE_RECEIPT_SHA256_PIN,
)
from .classification_v5_stage_a_generalization_retrain_diagnose import (
    centroid,
    cosine,
    semantic_core_class,
    simple_tokens,
)
from .classification_v5_stage_a_two_stage_generalization import (
    AUTHORIZED_DATASET_SHA,
    PARENT_STAGE_A_BEST_SHA,
    SPENT_RESERVE,
    SPENT_RESERVE_OVERLAP,
    SPENT_RESERVE_STATUS,
)

DIAGNOSE_RULE = "DIAGNOSE_STAGE_A_FACTORIZED_RELATION_SETTLED_FAIL"
FAILED_CHECKPOINT_SHA256 = (
    "8a6981c1f742f127d397770462c345ddcce922895add2f4f52828c49d816d9cd"
)
FAILED_RUN_RECEIPT_SHA256 = (
    "76b1d5f594028fae1a76771ae3ebfe9f5e7f833f7edd23f66c2ae64ab5b79b2d"
)
PRIOR_TWO_STAGE_FAILED_SHA256 = (
    "26841d5f3a8b9cd4237f79203b80697f2da186e7d4b30ab6c08d528adba56e76"
)
MODEL_WIDE_BEST_SHA256 = (
    "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
)

FROZEN_OBSERVED_OUTCOME = {
    "SHORT_ATOM_NONE_relation_FPR": 0.5394736842105263,
    "SHORT_ATOM_PRESENT_relation_recall": 0.75,
    "E2E_NONE_recall": 0.8074204946996466,
    "E2E_PRESENT_recall": 0.8883610451306413,
    "E2E_false_entry": 0.18021201413427562,
    "n_threshold_passing": 0,
    "scientific_disposition": "SETTLED_FAIL",
    "selection_score": 0.8756563662884764,
    "restored_epoch": 12,
}

PRIMARY_DIAGNOSES = (
    "ENCODER_ADAPTATION_DEPTH_LIMIT",
    "POOLING_INFORMATION_LOSS",
    "MODEL_INPUT_INFORMATION_DEFICIT",
    "IRREDUCIBLE_SEMANTIC_OVERLAP",
    "REPRESENTATION_OBJECTIVE_LIMIT",
    "MIXED_REPRESENTATION_FAILURE",
)

NEXT_ACTIONS = (
    "DEEPEN_ENCODER_ADAPTATION",
    "CHANGE_POOLING",
    "CHANGE_MODEL_INPUT_CONTRACT",
    "REVISE_GOLD_IDENTIFIABILITY_CONTRACT",
    "CHANGE_BASE_ENCODER",
    "STOP_STAGE_A_RESEARCH",
)

DATASET_CONSEQUENCES = (
    "NO_DATA_CHANGE",
    "ANNOTATION_REPAIR_REQUIRED",
    "GOLD_CONTRACT_REPAIR_REQUIRED",
    "INPUT_ENRICHMENT_REQUIRED",
)


def normalize_text(text: str) -> str:
    t = str(text or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t


def context_sufficiency_class(row: Mapping[str, Any]) -> str:
    """Partition SHORT_ATOM rows using existing gold fields only."""
    core = semantic_core_class(row)
    label = str(row.get("evidence_label") or "")
    subtype = str(row.get("evidence_subtype") or "")
    missing = [str(x) for x in (row.get("missing_required_semantics") or [])]
    text = str(row.get("text") or "")
    tokens = simple_tokens(text)
    notes_l = str(row.get("notes") or "").lower()

    if core in {"LEXEME_ONLY", "CATEGORY_MENTION_ONLY"}:
        return "LEXEME_ONLY"
    if label == "UNCERTAIN" or "evidence_sufficiency_unresolved" in missing:
        return "SEMANTICALLY_UNDERDETERMINED"
    if core in {"LEXEME_PLUS_CONTEXT"}:
        return "CONTEXT_DEPENDENT_RELATION"
    # Bare PRESENT atoms labeled from dictionary/family sense are not
    # self-contained in the model text input.
    if (
        label == "EVIDENCE_PRESENT"
        and len(tokens) <= 3
        and (
            "wikt" in notes_l
            or "atom_present" in notes_l
            or core == "LEXEME_PLUS_RELATION"
        )
    ):
        return "CONTEXT_DEPENDENT_RELATION"
    if core in {"EXPLICIT_EVIDENCE_CORE", "LEXEME_PLUS_RELATION"}:
        if len(tokens) <= 3:
            return "CONTEXT_DEPENDENT_RELATION"
        return "SELF_CONTAINED_RELATION"
    if core == "NEGATED_OR_NONASSERTED":
        return "SELF_CONTAINED_RELATION"
    if subtype.endswith("_NONE") and "active_family_evidence_absent" in missing:
        return "LEXEME_ONLY"
    return "SEMANTICALLY_UNDERDETERMINED"


def matched_pair_identifiability(row: Mapping[str, Any]) -> str:
    """Identifiability from text alone using existing provenance fields."""
    core = semantic_core_class(row)
    label = str(row.get("evidence_label") or "")
    notes = str(row.get("notes") or "")
    missing = [str(x) for x in (row.get("missing_required_semantics") or [])]
    paired = bool(row.get("pair_group_id") or row.get("paired_positive_identity"))
    tokens = simple_tokens(str(row.get("text") or ""))
    notes_l = notes.lower()
    wiktish = "wikt" in notes_l or "wiktionary" in notes_l or "atom_present" in notes_l

    # Bare SHORT_ATOM PRESENT whose gold is dictionary/family sense: the
    # model input is only the lexeme string; relation is external.
    if label == "EVIDENCE_PRESENT" and len(tokens) <= 3:
        if wiktish or paired or core in {"LEXEME_PLUS_RELATION", "LEXEME_ONLY"}:
            return "REQUIRES_EXTERNAL_CONTEXT"

    if core in {"EXPLICIT_EVIDENCE_CORE"} and len(tokens) >= 4:
        return "TEXT_IDENTIFIABLE"
    if core in {"LEXEME_ONLY", "CATEGORY_MENTION_ONLY"} and label == "NO_EVIDENCE":
        # Negative short atom: text alone supports NO_RELATION if lexeme-only.
        return "TEXT_IDENTIFIABLE"
    if "paired_against_positive" in " ".join(missing) or paired:
        if core in {"LEXEME_ONLY", "CATEGORY_MENTION_ONLY"}:
            return "REQUIRES_EXTERNAL_CONTEXT"
    if label == "UNCERTAIN" or "evidence_sufficiency_unresolved" in missing:
        return "INSUFFICIENT_EVIDENCE"
    if core in {"LEXEME_PLUS_CONTEXT"}:
        return "REQUIRES_EXTERNAL_CONTEXT"
    if core in {"EXPLICIT_EVIDENCE_CORE"}:
        return "TEXT_IDENTIFIABLE"
    return "INSUFFICIENT_EVIDENCE"


def classify_layer_finding(
    *,
    best_layer: int,
    last_layer: int,
    best_ba: float,
    last_ba: float,
    any_separates: bool,
) -> str:
    if not any_separates:
        return "NO_LAYER_SEPARATES"
    if best_layer == last_layer or (best_ba - last_ba) <= 0.02:
        return "LAST_LAYER_BEST"
    return "INTERMEDIATE_LAYER_BETTER"


def classify_adaptation_depth(
    *,
    layer_finding: str,
    best_layer: int,
    n_layers: int,
    last_trainable: int = 2,
) -> str:
    """Whether last-two adaptation can reach the separating layer."""
    if layer_finding == "NO_LAYER_SEPARATES":
        return "DEEPER_ADAPTATION_NOT_SUPPORTED"
    # Layers that are trainable under last-2: [n-2, n-1] (0-indexed).
    trainable_start = max(0, n_layers - last_trainable)
    if best_layer >= trainable_start:
        return "LAST_TWO_SUFFICIENT"
    # Intermediate earlier layer better → deeper adaptation may help.
    if layer_finding == "INTERMEDIATE_LAYER_BETTER" and best_layer < trainable_start:
        return "DEEPER_ADAPTATION_JUSTIFIED"
    return "LAST_TWO_SUFFICIENT"


def classify_pooling(
    *,
    cls_ba: float,
    best_alt_ba: float,
    best_alt_name: str,
) -> str:
    if best_alt_ba - cls_ba >= 0.05:
        return "POOLING_INFORMATION_LOSS"
    if cls_ba >= 0.70:
        return "CLS_SUFFICIENT"
    return "POOLING_NOT_PRIMARY"


def classify_token_signal(
    *,
    token_ba: float,
    cls_ba: float,
    token_margin: float,
    cls_margin: float,
) -> str:
    if token_ba - cls_ba >= 0.05 or (
        token_margin - cls_margin >= 0.02 and token_ba >= cls_ba
    ):
        return "TOKEN_SIGNAL_PRESENT_CLS_LOST"
    if token_ba < 0.58 and cls_ba < 0.58:
        return "TOKEN_SIGNAL_ABSENT"
    return "MIXED_TOKEN_SIGNAL"


def irreducible_overlap_test(evidence: Mapping[str, Any]) -> dict[str, Any]:
    checks = {
        "no_encoder_layer_separates": bool(
            evidence.get("layer_finding") == "NO_LAYER_SEPARATES"
        ),
        "nonlinear_probe_no_recovery": bool(
            float(evidence.get("nonlinear_ba", 0.0)) < 0.60
            and float(evidence.get("linear_ba", 0.0)) < 0.60
        ),
        "pooling_no_recovery": bool(
            evidence.get("pooling_finding") in {"POOLING_NOT_PRIMARY", "CLS_SUFFICIENT"}
            and float(evidence.get("best_pooling_ba", 0.0)) < 0.60
        ),
        "token_no_recovery": bool(
            evidence.get("token_finding")
            in {"TOKEN_SIGNAL_ABSENT", "MIXED_TOKEN_SIGNAL"}
            and float(evidence.get("token_ba", 0.0)) < 0.60
        ),
        "substantial_collisions_or_missing_input": bool(
            int(evidence.get("exact_cross_label_collisions", 0)) > 0
            or int(evidence.get("short_atom_cross_label_collisions", 0)) > 0
            or float(evidence.get("requires_external_context_fraction", 0.0)) >= 0.25
            or bool(evidence.get("missing_input_material"))
        ),
    }
    material = all(checks.values())
    return {"checks": checks, "IRREDUCIBLE_SEMANTIC_OVERLAP": material}


def decide_primary_diagnosis(audit: Mapping[str, Any]) -> dict[str, Any]:
    """Choose exactly one primary diagnosis from sealed audit evidence."""
    layer_finding = str(audit.get("layer_finding") or "")
    adapt = str(audit.get("adaptation_depth") or "")
    pooling = str(audit.get("pooling_finding") or "")
    token = str(audit.get("token_finding") or "")
    irr = audit.get("irreducible_overlap") or {}
    missing_input = bool(audit.get("missing_input_material"))
    ext_frac = float(audit.get("requires_external_context_fraction") or 0.0)
    collisions = int(audit.get("short_atom_cross_label_collisions") or 0)
    linear_ba = float(audit.get("linear_ba") or 0.0)
    nonlinear_ba = float(audit.get("nonlinear_ba") or 0.0)
    best_pool_ba = float(audit.get("best_pooling_ba") or 0.0)
    displacement = str(audit.get("displacement_class") or "")

    reasons: list[str] = []

    if irr.get("IRREDUCIBLE_SEMANTIC_OVERLAP"):
        return {
            "primary_diagnosis": "IRREDUCIBLE_SEMANTIC_OVERLAP",
            "reasons": [
                "no layer / probe / pooling / token path recovers SHORT_ATOM separation",
                "collisions or external-context dependence present",
            ],
            "confidence": "high",
        }

    if missing_input or ext_frac >= 0.30 or collisions > 0:
        reasons = [
            f"requires_external_context_fraction={ext_frac:.3f}",
            f"short_atom_cross_label_collisions={collisions}",
            f"missing_input_material={missing_input}",
        ]
        # Prefer input deficit when geometry is also weak.
        if linear_ba < 0.62 and best_pool_ba < 0.62:
            return {
                "primary_diagnosis": "MODEL_INPUT_INFORMATION_DEFICIT",
                "reasons": reasons,
                "confidence": "high",
            }

    if adapt == "DEEPER_ADAPTATION_JUSTIFIED" and layer_finding == (
        "INTERMEDIATE_LAYER_BETTER"
    ):
        return {
            "primary_diagnosis": "ENCODER_ADAPTATION_DEPTH_LIMIT",
            "reasons": [
                f"best_layer earlier than last-2 trainable window",
                f"layer_finding={layer_finding}",
            ],
            "confidence": "medium",
        }

    if pooling == "POOLING_INFORMATION_LOSS" and token == (
        "TOKEN_SIGNAL_PRESENT_CLS_LOST"
    ):
        return {
            "primary_diagnosis": "POOLING_INFORMATION_LOSS",
            "reasons": [
                "alternate pooling recovers BA",
                "token signal present but CLS loses it",
            ],
            "confidence": "medium",
        }

    # Two objectives same failure + geometry mostly preserved → not objective.
    if displacement in {
        "mostly_preserved_parent_geometry",
        "reshaped_but_not_label_separating",
    } and linear_ba < 0.62 and nonlinear_ba < 0.62:
        if missing_input or ext_frac >= 0.20:
            return {
                "primary_diagnosis": "MODEL_INPUT_INFORMATION_DEFICIT",
                "reasons": [
                    "factorized objective failed like prior two-stage on SHORT_ATOM",
                    "probes do not recover separation",
                    "gold often depends on non-text cues",
                ],
                "confidence": "high",
            }
        return {
            "primary_diagnosis": "MIXED_REPRESENTATION_FAILURE",
            "reasons": [
                "objective change did not move SHORT_ATOM geometry",
                "no single recovery path dominates",
            ],
            "confidence": "medium",
        }

    if linear_ba < 0.60 and nonlinear_ba < 0.60 and layer_finding == (
        "NO_LAYER_SEPARATES"
    ):
        return {
            "primary_diagnosis": "REPRESENTATION_OBJECTIVE_LIMIT",
            "reasons": ["no layer separates; probes fail under corrected objective"],
            "confidence": "medium",
        }

    return {
        "primary_diagnosis": "MIXED_REPRESENTATION_FAILURE",
        "reasons": ["multiple weak failure modes without a single dominant cause"],
        "confidence": "low",
    }


def decide_next_action(primary: str) -> str:
    return {
        "ENCODER_ADAPTATION_DEPTH_LIMIT": "DEEPEN_ENCODER_ADAPTATION",
        "POOLING_INFORMATION_LOSS": "CHANGE_POOLING",
        "MODEL_INPUT_INFORMATION_DEFICIT": "REVISE_GOLD_IDENTIFIABILITY_CONTRACT",
        "IRREDUCIBLE_SEMANTIC_OVERLAP": "STOP_STAGE_A_RESEARCH",
        "REPRESENTATION_OBJECTIVE_LIMIT": "CHANGE_BASE_ENCODER",
        "MIXED_REPRESENTATION_FAILURE": "REVISE_GOLD_IDENTIFIABILITY_CONTRACT",
    }.get(primary, "STOP_STAGE_A_RESEARCH")


def dataset_consequence(primary: str, audit: Mapping[str, Any]) -> str:
    if primary == "MODEL_INPUT_INFORMATION_DEFICIT":
        if bool(audit.get("missing_input_material")):
            return "INPUT_ENRICHMENT_REQUIRED"
        return "GOLD_CONTRACT_REPAIR_REQUIRED"
    if primary == "IRREDUCIBLE_SEMANTIC_OVERLAP":
        return "GOLD_CONTRACT_REPAIR_REQUIRED"
    if int(audit.get("exact_cross_label_collisions") or 0) > 0:
        return "ANNOTATION_REPAIR_REQUIRED"
    return "NO_DATA_CHANGE"


def assemble_diagnosis_receipt(audit: Mapping[str, Any]) -> dict[str, Any]:
    primary_payload = decide_primary_diagnosis(audit)
    primary = primary_payload["primary_diagnosis"]
    next_action = decide_next_action(primary)
    consequence = dataset_consequence(primary, audit)
    receipt = {
        "DIAGNOSE_RULE": DIAGNOSE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "FAILED_CHECKPOINT_SHA256": FAILED_CHECKPOINT_SHA256,
        "FAILED_RUN_RECEIPT_SHA256": FAILED_RUN_RECEIPT_SHA256,
        "PRIOR_TWO_STAGE_FAILED_SHA256": PRIOR_TWO_STAGE_FAILED_SHA256,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "STAGE_A_BEST": PARENT_STAGE_A_BEST_SHA,
        "STAGE_A_BEST_MUTATED": False,
        "OBJECTIVE_ID": OBJECTIVE_ID,
        "OBJECTIVE_RECEIPT_SHA256": OBJECTIVE_RECEIPT_SHA256_PIN,
        "FACTORIZED_ANNOTATION_SHA256": FACTORIZED_ANNOTATION_SHA256_PIN,
        "V1R1_DATASET_SHA256": AUTHORIZED_DATASET_SHA,
        "AUTHORIZATION_RECEIPT_SHA256": AUTHORIZED_AUTH_RECEIPT_SHA256,
        "CLASS_WEIGHT_ARTIFACT_SHA256": AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256,
        "TRAINING_CONFIG_SHA256": AUTHORIZED_TRAINING_CONFIG_SHA256,
        "PRIMARY_DIAGNOSIS": primary,
        "PRIMARY_REASONS": primary_payload["reasons"],
        "DIAGNOSIS_CONFIDENCE": primary_payload.get("confidence"),
        "NEXT_ACTION": next_action,
        "NEXT_ACTION_AUTHORIZED": False,
        "DATASET_CONSEQUENCE": consequence,
        "FROZEN_OBSERVED_OUTCOME": FROZEN_OBSERVED_OUTCOME,
        "SPENT_RESERVE": SPENT_RESERVE,
        "SPENT_RESERVE_OVERLAP": SPENT_RESERVE_OVERLAP,
        "SPENT_RESERVE_STATUS": SPENT_RESERVE_STATUS,
        "TRAIN": False,
        "V1R1_MUTATED": False,
        "V1R2_CREATED": False,
        "THRESHOLDS_MUTATED": False,
        "STAGE_B_MUTATED": False,
        "architecture_change_justified": primary
        in {"ENCODER_ADAPTATION_DEPTH_LIMIT", "POOLING_INFORMATION_LOSS", "REPRESENTATION_OBJECTIVE_LIMIT"},
        "input_contract_change_justified": primary
        in {"MODEL_INPUT_INFORMATION_DEFICIT", "IRREDUCIBLE_SEMANTIC_OVERLAP"},
        "audit": audit,
        "schema": "hyperlex.classification.v5.stage_a_factorized_relation_diagnose.v1",
    }
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )
    return receipt
