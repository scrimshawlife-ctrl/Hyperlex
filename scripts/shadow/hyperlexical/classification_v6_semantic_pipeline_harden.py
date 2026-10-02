"""HARDEN_V6_SEMANTIC_REPRESENTATION_AND_PREPARE_QUALIFICATION — contracts.

Freezes the selected frozen-encoder + nonlinear-head pipeline, packages a
qualification-ready candidate, and preregisters QUAL gates. QUAL rows remain
sealed / uninspected. MODEL_WIDE_BEST and V5 pointers are not mutated.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v6_architecture_reset_bakeoff import AXIS_VOCABS
from .classification_v6_human_ontology_settlement import FINAL_ONTOLOGY_ID
from .classification_v6_label_migration import (
    DOMAIN_VOCAB,
    FUNCTION_VOCAB,
    MEDIATION_VOCAB,
)
from .classification_v6_representation_rebase import (
    ADVANCEMENT as REBASE_ADVANCEMENT,
    ENCODER_FAMILY,
    MPNET_WITNESS,
)

PHASE_RULE = "HARDEN_V6_SEMANTIC_REPRESENTATION_AND_PREPARE_QUALIFICATION"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-SEMANTIC-PIPELINE-HARDEN-001"
PIPELINE_CANDIDATE_ID = "HYPERLEX_V6_SEMANTIC_PIPELINE_CANDIDATE_V1"
PACKAGE_ID = "HYPERLEX_V6_SEMANTIC_PIPELINE_PACKAGE_CANDIDATE_V1"
CONSTRAINT_MANIFEST_ID = "HYPERLEX_V6_HIERARCHY_CONSTRAINTS_V1"
THRESHOLD_MANIFEST_ID = "V6_THRESHOLD_MANIFEST"
RUNTIME_SCHEMA = "hyperlex.classification.v6.semantic_hierarchical_forward.v1"
SCHEMA = "hyperlex.classification.v6.semantic_pipeline_harden.v1"

SELECTED_CANDIDATE_ID = "FROZEN_NONLINEAR__C_MSMARCO"
SELECTED_ENCODER_TAG = "C_MSMARCO"
SELECTED_ENCODER_MODEL_ID = ENCODER_FAMILY[SELECTED_ENCODER_TAG]
# Pinned HF snapshot used in the successful rebase bakeoff (Spark cache).
SELECTED_ENCODER_REVISION = "b2f66c95aba1481a880479165582020c2b9b64d7"

REBASE_RECEIPT_SHA256 = (
    "eb4851e5c854641b97f7cb27d3f331386c4f1b4c30754e7340239de31bdb7c5b"
)
WITNESS_DEV_MACRO = 0.4275164580181028
WITNESS_REP_MACRO = 0.44260197001378715
WITNESS_RAW_HIER_VIOL = 0.0037593984962406013
WITNESS_POST_HIER_VIOL = 0.0

# DEV-selected thresholds from the rebase bakeoff for FROZEN_NONLINEAR__C_MSMARCO.
# Reused exactly — no REP / QUAL involvement.
BAKEOFF_THRESHOLDS = {
    "domain": [0.25, 0.05, 0.1, 0.1, 0.3, 0.45, 0.2, 0.25, 0.3, 0.45, 0.25],
    "function": [0.3, 0.4, 0.2, 0.4],
    "mediation": [0.35],
}

HEAD_ARCH_SHARED = {
    "kind": "axis_specific_mlp",
    "layers": [
        {"type": "Linear", "in": "encoder_hidden", "out": 128, "bias": True},
        {"type": "ReLU"},
        {"type": "Linear", "in": 128, "out": "n_labels", "bias": True},
    ],
    "hidden_dimensions": [128],
    "activation": "ReLU",
    "dropout": 0.0,
    "normalization": None,
    "loss": "BCEWithLogitsLoss",
    "initialization": "torch.nn.Linear default (kaiming_uniform / uniform bias)",
    "optimizer": "AdamW",
    "lr": 1e-2,
    "epochs": 40,
    "seed": 20261001,
}

REPRODUCTION_TOLERANCE = {
    # Exact/numeric bands (same weights + scores).
    "dev_abs": 0.015,
    "rep_abs": 0.015,
    # Clean retrain + locked bakeoff DEV thresholds: allow wider DEV slack;
    # REP must stay near the sealed witness and above the retention region.
    "dev_abs_scientific": 0.10,
    "rep_abs_scientific": 0.04,
    "rep_floor_scientific": 0.40,
    "hierarchy_abs": 1e-9,
    "score_atol": 1e-5,
    "pred_mismatch_max": 0,
}

HARDENING_STATES = (
    "V6_SEMANTIC_PIPELINE_HARDENED",
    "V6_SEMANTIC_PIPELINE_HARDEN_FAILED",
)

QUALIFICATION_READINESS = (
    "V6_QUALIFICATION_READY",
    "V6_QUALIFICATION_BLOCKED_PACKAGE",
    "V6_QUALIFICATION_BLOCKED_ONTOLOGY",
    "V6_QUALIFICATION_BLOCKED_QUAL_SURFACE",
)

REPRODUCTION_CLASSES = (
    "EXACT_REPRODUCTION",
    "NUMERICALLY_EQUIVALENT_REPRODUCTION",
    "SCIENTIFICALLY_EQUIVALENT_REPRODUCTION",
    "REPRODUCTION_DIVERGED",
)

ERROR_TAXONOMY = (
    "DOMAIN_FP",
    "DOMAIN_FN",
    "FUNCTION_FP",
    "FUNCTION_FN",
    "MEDIATION_FP",
    "MEDIATION_FN",
    "PARENT_CHILD_VIOLATION",
    "CO_LABEL_OMISSION",
    "OVERPREDICTION",
    "ONTOLOGY_BOUNDARY_CASE",
)

QUALIFICATION_METRICS = (
    "DOMAIN_macro_f1",
    "DOMAIN_micro_f1",
    "FUNCTION_macro_f1",
    "FUNCTION_micro_f1",
    "MEDIATION_macro_f1",
    "MEDIATION_micro_f1",
    "system_macro_f1",
    "sample_f1",
    "jaccard",
    "hierarchy_violations",
    "per_label_precision_recall_f1",
    "single_label_vs_multi_label",
    "source_slices",
    "cardinality_slices",
)

# Retention floor: REP≈0.443; 0.20 alone is too permissive for fresh QUAL.
QUALIFICATION_GATES = {
    "system_macro_f1_min": 0.30,
    "legacy_floor_system_macro_f1_min": 0.20,
    "hierarchy_violation_max": 0.05,
    "min_axis_macro_f1": 0.10,
    "no_complete_axis_collapse": True,
    "retention_rule": "QUAL_system_macro_f1 >= 0.30 (preregistered from REP≈0.443)",
    "chosen_before_qual_open": True,
}


def _hash_payload(payload: Any) -> str:
    return sha256_text(canonical_json(payload))


def label_schema_payload() -> dict[str, Any]:
    return {
        "structure": "HIERARCHICAL_MULTI_LABEL",
        "ontology_version": FINAL_ONTOLOGY_ID,
        "axes": {
            "domain_labels": list(DOMAIN_VOCAB),
            "function_labels": list(FUNCTION_VOCAB),
            "mediation_labels": list(MEDIATION_VOCAB),
        },
        "axis_vocabs": {
            "domain": list(AXIS_VOCABS["domain"]),
            "function": list(AXIS_VOCABS["function"]),
            "mediation": list(AXIS_VOCABS["mediation"]),
        },
        "semantics": "label_id_stable_no_display_string_lookup",
    }


def hierarchy_constraints_payload() -> dict[str, Any]:
    tech = "domain.technology"
    ai = "domain.technology.ai_discourse"
    return {
        "CONSTRAINT_MANIFEST_ID": CONSTRAINT_MANIFEST_ID,
        "version": 1,
        "apply_stage": "after_raw_head_inference",
        "rules": [
            {
                "id": "ai_discourse_requires_technology",
                "type": "required_parent",
                "child": ai,
                "parent": tech,
                "axis": "domain",
                "action": "force_parent_positive",
                "example": "ai_discourse => technology",
            }
        ],
        "incompatibility_rules": [],
        "report_both": ["raw_predictions", "constrained_predictions"],
    }


def threshold_manifest_payload() -> dict[str, Any]:
    return {
        "THRESHOLD_MANIFEST_ID": THRESHOLD_MANIFEST_ID,
        "status": "FROZEN",
        "selection_surface": "DEV_ONLY",
        "source": "HLX-CLASSIFICATION-V6-REPRESENTATION-REBASE-001",
        "candidate_id": SELECTED_CANDIDATE_ID,
        "thresholds": {
            axis: {
                lab: float(th)
                for lab, th in zip(AXIS_VOCABS[axis], BAKEOFF_THRESHOLDS[axis])
            }
            for axis in ("domain", "function", "mediation")
        },
        "thresholds_ordered": dict(BAKEOFF_THRESHOLDS),
        "rep_touched_during_selection": False,
        "qual_touched_during_selection": False,
    }


def head_architecture_payload() -> dict[str, Any]:
    """Per-axis head shapes (identical MLP topology; different output dims)."""
    hidden = 768  # DistilBERT / MS MARCO base
    out = {
        "shared_topology": HEAD_ARCH_SHARED,
        "encoder_hidden_dim": hidden,
        "axes": {},
    }
    for axis, vocab in (
        ("domain", DOMAIN_VOCAB),
        ("function", FUNCTION_VOCAB),
        ("mediation", MEDIATION_VOCAB),
    ):
        out["axes"][axis] = {
            "input_dimension": hidden,
            "hidden_dimensions": [128],
            "activation": "ReLU",
            "dropout": 0.0,
            "normalization": None,
            "output_dimension": len(vocab),
            "label_ids": list(vocab),
            "loss": "BCEWithLogitsLoss",
            "initialization": HEAD_ARCH_SHARED["initialization"],
        }
    return out


def encoder_identity_payload() -> dict[str, Any]:
    return {
        "tag": SELECTED_ENCODER_TAG,
        "model_id": SELECTED_ENCODER_MODEL_ID,
        "revision": SELECTED_ENCODER_REVISION,
        "trainable_parameters_required": 0,
        "floating_upstream_revision_forbidden": True,
        "immutability": {
            "require": [
                "pre_training_encoder_hash",
                "post_training_encoder_hash",
                "runtime_encoder_hash",
            ],
            "equality": "pre == post == runtime",
            "fail_closed_on_mutation": True,
        },
    }


def pipeline_candidate_contract() -> dict[str, Any]:
    label_schema = label_schema_payload()
    constraints = hierarchy_constraints_payload()
    thresholds = threshold_manifest_payload()
    heads = head_architecture_payload()
    encoder = encoder_identity_payload()
    return {
        "PIPELINE_CANDIDATE_ID": PIPELINE_CANDIDATE_ID,
        "architecture": {
            "flow": [
                "text",
                "frozen_semantic_encoder",
                "frozen_semantic_vector",
                "axis_specific_nonlinear_heads",
                "hierarchy_compatibility_constraints",
                "final_hierarchical_multi_label_output",
            ],
            "axes_prior_to_constraints": "independent",
            "preserve_raw_probabilities": True,
            "external_semantics": [
                "domain_labels[]",
                "function_labels[]",
                "mediation_labels[]",
            ],
            "flat_label_vector_external_semantics": False,
        },
        "selected_candidate_id": SELECTED_CANDIDATE_ID,
        "encoder": encoder,
        "heads": heads,
        "ontology": {
            "ontology_version": FINAL_ONTOLOGY_ID,
            "structure": "HIERARCHICAL_MULTI_LABEL",
            "label_schema_hash": _hash_payload(label_schema),
            "hierarchy_hash": _hash_payload(constraints["rules"]),
            "compatibility_rule_hash": _hash_payload(
                {"rules": constraints["rules"], "incompatibility": []}
            ),
            "label_schema": label_schema,
        },
        "constraints": constraints,
        "constraint_manifest_hash": _hash_payload(constraints),
        "thresholds": thresholds,
        "threshold_manifest_hash": _hash_payload(thresholds),
        "runtime_schema": RUNTIME_SCHEMA,
        "rebase_receipt": REBASE_RECEIPT_SHA256,
        "witness": {
            "dev_system_macro_f1": WITNESS_DEV_MACRO,
            "rep_system_macro_f1": WITNESS_REP_MACRO,
            "raw_hierarchy_violation": WITNESS_RAW_HIER_VIOL,
            "post_constraint_hierarchy_violation": WITNESS_POST_HIER_VIOL,
        },
    }


def runtime_forward_schema() -> dict[str, Any]:
    return {
        "schema": RUNTIME_SCHEMA,
        "required_fields": [
            "domain_scores",
            "function_scores",
            "mediation_scores",
            "raw_domain_labels",
            "raw_function_labels",
            "raw_mediation_labels",
            "final_domain_labels",
            "final_function_labels",
            "final_mediation_labels",
            "hierarchy_adjustments",
            "encoder_id",
            "head_bundle_sha",
            "ontology_version",
            "threshold_manifest_sha",
            "constraint_manifest_sha",
            "pipeline_version",
        ],
        "pipeline_version": PIPELINE_CANDIDATE_ID,
    }


def qualification_preregistration() -> dict[str, Any]:
    return {
        "gates": dict(QUALIFICATION_GATES),
        "metrics": list(QUALIFICATION_METRICS),
        "error_taxonomy": list(ERROR_TAXONOMY),
        "axes_required": ["domain", "function", "mediation"],
        "qual_open": False,
        "chosen_before_qual_inspection": True,
        "note": (
            "Retention floor 0.30 replaces bare 0.20 for informative QUAL; "
            "0.20 remains recorded as legacy floor only."
        ),
    }


def harden_contract() -> dict[str, Any]:
    cand = pipeline_candidate_contract()
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "pipeline_candidate": cand,
        "package_id": PACKAGE_ID,
        "qualification": qualification_preregistration(),
        "runtime_schema": runtime_forward_schema(),
        "reproduction_tolerance": REPRODUCTION_TOLERANCE,
        "historical_control": {
            "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
            "role": "HISTORICAL_CONTROL_REPRESENTATION",
            "do_not_mutate": True,
        },
        "mpnet_witness": MPNET_WITNESS,
        "forbidden": [
            "inspect_QUAL_rows",
            "encoder_bakeoff",
            "fine_tune_encoder",
            "reopen_ontology",
            "lower_gates",
            "mutate_V5_pointers",
            "mutate_MODEL_WIDE_BEST",
            "promote_MODEL_WIDE_BEST",
            "acquire_new_data_unless_support_defect",
            "architecture_search",
            "tune_on_REP",
            "tune_on_QUAL",
        ],
        "pointer_policy": {
            "V6_REPRESENTATION_CANDIDATE": "set_to_package_sha_on_pass",
            "MODEL_WIDE_BEST": "UNCHANGED",
            "STAGE_A_BEST": "UNCHANGED",
            "V5_pointers": "UNCHANGED",
        },
        "rebase_advancement_floors_locked": dict(REBASE_ADVANCEMENT),
    }


def classify_reproduction(
    *,
    dev_macro: float,
    rep_macro: float,
    post_hier: float,
    raw_pred_mismatch: int,
    constrained_pred_mismatch: int,
    score_max_abs_delta: float | None = None,
) -> str:
    """Classify reproduction against the sealed rebase witness."""
    hier_ok = abs(post_hier - WITNESS_POST_HIER_VIOL) <= REPRODUCTION_TOLERANCE[
        "hierarchy_abs"
    ]
    if not hier_ok:
        return "REPRODUCTION_DIVERGED"
    exactish = (
        raw_pred_mismatch == 0
        and constrained_pred_mismatch == 0
        and score_max_abs_delta is not None
        and score_max_abs_delta <= REPRODUCTION_TOLERANCE["score_atol"]
        and abs(dev_macro - WITNESS_DEV_MACRO) < 1e-9
        and abs(rep_macro - WITNESS_REP_MACRO) < 1e-9
    )
    if exactish:
        return "EXACT_REPRODUCTION"
    if (
        raw_pred_mismatch == 0
        and constrained_pred_mismatch == 0
        and abs(dev_macro - WITNESS_DEV_MACRO) <= 1e-4
        and abs(rep_macro - WITNESS_REP_MACRO) <= 1e-4
    ):
        return "NUMERICALLY_EQUIVALENT_REPRODUCTION"
    sci_ok = (
        abs(dev_macro - WITNESS_DEV_MACRO)
        <= REPRODUCTION_TOLERANCE["dev_abs_scientific"]
        and abs(rep_macro - WITNESS_REP_MACRO)
        <= REPRODUCTION_TOLERANCE["rep_abs_scientific"]
        and rep_macro >= REPRODUCTION_TOLERANCE["rep_floor_scientific"]
    )
    if sci_ok:
        return "SCIENTIFICALLY_EQUIVALENT_REPRODUCTION"
    tight_ok = (
        abs(dev_macro - WITNESS_DEV_MACRO) <= REPRODUCTION_TOLERANCE["dev_abs"]
        and abs(rep_macro - WITNESS_REP_MACRO) <= REPRODUCTION_TOLERANCE["rep_abs"]
    )
    if tight_ok:
        return "SCIENTIFICALLY_EQUIVALENT_REPRODUCTION"
    return "REPRODUCTION_DIVERGED"


def classify_source_robustness(
    family_macros: Mapping[str, float],
    *,
    system_macro: float,
    min_family_n: int = 8,
) -> str:
    """SOURCE_STABLE / SOURCE_SENSITIVE / SOURCE_DEPENDENT from family macros."""
    vals = [float(v) for k, v in family_macros.items() if not k.startswith("_")]
    if not vals:
        return "SOURCE_SENSITIVE"
    spread = max(vals) - min(vals)
    weak = sum(1 for v in vals if v < 0.5 * system_macro)
    if spread <= 0.15 and weak == 0:
        return "SOURCE_STABLE"
    if weak >= max(1, len(vals) // 3) or spread > 0.35:
        return "SOURCE_DEPENDENT"
    return "SOURCE_SENSITIVE"


def qual_metadata_compatibility(meta: Mapping[str, Any]) -> dict[str, Any]:
    """Metadata-only QUAL surface check. Never opens row payloads."""
    summary = meta.get("summary") if isinstance(meta.get("summary"), Mapping) else meta
    family_counts = summary.get("family_counts") if isinstance(summary, Mapping) else None
    has_axis_fields = any(
        k in (meta or {})
        for k in ("domain_label_counts", "function_label_counts", "mediation_label_counts")
    )
    # Sealed QUAL_001 was built under pre-settlement family gold (gold_family /
    # family_counts), not hierarchical multi-label axis IDs.
    uses_legacy_families = bool(family_counts) and not has_axis_fields
    expected_axes = {"domain_labels", "function_labels", "mediation_labels"}
    declared_axes = set(meta.get("axes") or meta.get("label_axes") or [])
    ontology_ok = (
        meta.get("ontology_version") == FINAL_ONTOLOGY_ID
        or meta.get("ontology") == FINAL_ONTOLOGY_ID
    )
    if uses_legacy_families or (
        declared_axes and not expected_axes.issubset(declared_axes)
    ):
        return {
            "status": "NEW_QUAL_REQUIRED",
            "compatible": False,
            "reason": (
                "Sealed QUAL metadata uses legacy gold_family / family_counts "
                "without hierarchical domain/function/mediation label axes under "
                f"{FINAL_ONTOLOGY_ID}."
            ),
            "ontology_compatible": False,
            "axes_compatible": False,
            "expected_ontology": FINAL_ONTOLOGY_ID,
            "expected_axes": sorted(expected_axes),
            "observed_family_counts": bool(family_counts),
            "observed_axes": sorted(declared_axes),
            "rows_inspected": False,
        }
    if not ontology_ok:
        return {
            "status": "QUAL_REANNOTATION_REQUIRED",
            "compatible": False,
            "reason": "QUAL metadata ontology version mismatch without axis gold.",
            "ontology_compatible": False,
            "axes_compatible": has_axis_fields,
            "rows_inspected": False,
        }
    return {
        "status": "QUAL_SURFACE_COMPATIBLE",
        "compatible": True,
        "ontology_compatible": True,
        "axes_compatible": True,
        "rows_inspected": False,
    }


def decide_readiness(
    *,
    package_ok: bool,
    reproduction_class: str,
    cold_load_ok: bool,
    round_trip_ok: bool,
    encoder_immutable: bool,
    ontology_hashes_ok: bool,
    qual_compat_status: str,
    rep_regressed: bool,
) -> dict[str, Any]:
    package_pass = (
        package_ok
        and encoder_immutable
        and cold_load_ok
        and round_trip_ok
        and reproduction_class != "REPRODUCTION_DIVERGED"
        and not rep_regressed
    )
    if not ontology_hashes_ok:
        return {
            "HARDENING_STATE": "V6_SEMANTIC_PIPELINE_HARDEN_FAILED",
            "QUALIFICATION_READINESS": "V6_QUALIFICATION_BLOCKED_ONTOLOGY",
            "NEXT_ACTION": "REVIEW_V6_REPRESENTATION_HARDENING_FAILURE",
        }
    if not package_pass:
        return {
            "HARDENING_STATE": "V6_SEMANTIC_PIPELINE_HARDEN_FAILED",
            "QUALIFICATION_READINESS": "V6_QUALIFICATION_BLOCKED_PACKAGE",
            "NEXT_ACTION": "REVIEW_V6_REPRESENTATION_HARDENING_FAILURE",
        }
    if qual_compat_status in ("NEW_QUAL_REQUIRED", "QUAL_REANNOTATION_REQUIRED"):
        return {
            "HARDENING_STATE": "V6_SEMANTIC_PIPELINE_HARDENED",
            "QUALIFICATION_READINESS": "V6_QUALIFICATION_BLOCKED_QUAL_SURFACE",
            "NEXT_ACTION": "BUILD_AND_SEAL_FRESH_V6_QUALIFICATION_SURFACE",
        }
    return {
        "HARDENING_STATE": "V6_SEMANTIC_PIPELINE_HARDENED",
        "QUALIFICATION_READINESS": "V6_QUALIFICATION_READY",
        "NEXT_ACTION": "EXECUTE_V6_FRESH_QUALIFICATION_ONCE",
    }


def encoder_weights_sha256(path_bytes: bytes) -> str:
    return hashlib.sha256(path_bytes).hexdigest()


def material_label_divergence(
    dev_per: Mapping[str, Mapping[str, Any]],
    rep_per: Mapping[str, Mapping[str, Any]],
    *,
    abs_delta: float = 0.25,
) -> list[dict[str, Any]]:
    out = []
    for lab, drow in dev_per.items():
        rrow = rep_per.get(lab) or {}
        df1 = float(drow.get("f1") or 0.0)
        rf1 = float(rrow.get("f1") or 0.0)
        if abs(df1 - rf1) >= abs_delta:
            out.append(
                {
                    "label": lab,
                    "dev_f1": df1,
                    "rep_f1": rf1,
                    "abs_delta": abs(df1 - rf1),
                }
            )
    out.sort(key=lambda r: -r["abs_delta"])
    return out


__all__ = [
    "BAKEOFF_THRESHOLDS",
    "CONSTRAINT_MANIFEST_ID",
    "ERROR_TAXONOMY",
    "EXPERIMENT_ID",
    "PACKAGE_ID",
    "PHASE_RULE",
    "PIPELINE_CANDIDATE_ID",
    "QUALIFICATION_GATES",
    "RUNTIME_SCHEMA",
    "SELECTED_CANDIDATE_ID",
    "SELECTED_ENCODER_MODEL_ID",
    "SELECTED_ENCODER_REVISION",
    "THRESHOLD_MANIFEST_ID",
    "WITNESS_DEV_MACRO",
    "WITNESS_REP_MACRO",
    "classify_reproduction",
    "classify_source_robustness",
    "decide_readiness",
    "harden_contract",
    "head_architecture_payload",
    "hierarchy_constraints_payload",
    "label_schema_payload",
    "material_label_divergence",
    "pipeline_candidate_contract",
    "qual_metadata_compatibility",
    "qualification_preregistration",
    "runtime_forward_schema",
    "threshold_manifest_payload",
]
