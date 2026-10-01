"""SEAL_AND_PACKAGE_HYPERLEX_V5_STAGE_A_B_V1R2_PIPELINE — phase seal.

Freezes the integrated Stage-A/B V1R2 pipeline and produces a local production
package. Does not train, retune floors, rebuild the Stage-B index, score
reserve, or mutate MODEL_WIDE_BEST / STAGE_A_BEST.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .classification_v2 import ACTIVE_FAMILY_VOCABULARY, vocabulary_sha256
from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_b_pipeline import (
    PIPELINE_FLOW,
    PIPELINE_ID,
    PIPELINE_RULE,
    SCHEMA_PIPELINE,
    SCHEMA_PIPELINE_FORWARD,
    V5_STAGE_A_B_PIPELINE_STATE,
    V5_STAGE_B_STATE,
    build_pipeline_forward,
    pipeline_contract,
    runtime_registry,
    verify_entry_gating,
    verify_stage_b_parent_and_floors,
)
from .classification_v5_stage_a_canonical import (
    CANONICAL_ID,
    KNOWN_LIMITATIONS,
    MODEL_WIDE_BEST_SHA256,
    SCHEMA_FORWARD,
    STAGE_A_BEST_SHA256,
    STAGE_A_RESEARCH_LOOP,
    V5_STAGE_A_STATE,
    canonical_inference_policy,
    stage_a_canonical_contract,
)
from .classification_v5_stage_a_factorized_objective import OBJECTIVE_ID
from .classification_v5_stage_a_gold_identifiability_contract import (
    CONTRACT_ID,
    MODEL_INPUT,
)
from .classification_v5_stage_a_gold_identifiability_filter import (
    SURFACE_ID as V1R2_SURFACE_ID,
    V1R2_DATASET_SHA256_PIN,
)
from .classification_v5_stage_a_ident_filtered_promote import (
    CANONICAL_LOAD_SEQUENCE,
    CANONICAL_RELATION_THRESHOLD,
    CANONICAL_RESOLVABILITY_THRESHOLD,
)
from .classification_v5_stage_a_ident_filtered_repro_promote import (
    INCOMPLETE_HISTORICAL_CHECKPOINT_SHA256,
    PREVIOUS_STAGE_A_BEST_SHA256,
)
from .classification_v5_stage_a_two_stage_generalization import (
    SPENT_RESERVE,
    SPENT_RESERVE_STATUS,
)
from .classification_v5_stage_b import (
    EXPERIMENT_ID as STAGE_B_EXPERIMENT_ID,
    FROZEN_INDEX_SHA256,
    FROZEN_MINIMUM_FAMILY_SCORE,
    FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
    HISTORICAL_V1R9_INDEX_SHA256,
    HISTORICAL_V1R9_MINIMUM_FAMILY_SCORE,
    HISTORICAL_V1R9_MINIMUM_TOP1_TOP2_MARGIN,
    STAGE_B_RULE,
    compose_end_to_end,
    stage_b_contract,
)
from .classification_v5_stage_b_v1r2_align import (
    EXPERIMENT_ID as STAGE_B_V1R2_EXPERIMENT_ID,
)
from .save_pretrained import FACTORIZED_HEAD_NAMES

# Re-export pins for package load validators / round-trip subprocesses.
STAGE_A_BEST_SHA256 = STAGE_A_BEST_SHA256
MODEL_WIDE_BEST_SHA256 = MODEL_WIDE_BEST_SHA256
FROZEN_INDEX_SHA256 = FROZEN_INDEX_SHA256
FROZEN_MINIMUM_FAMILY_SCORE = FROZEN_MINIMUM_FAMILY_SCORE
FROZEN_MINIMUM_TOP1_TOP2_MARGIN = FROZEN_MINIMUM_TOP1_TOP2_MARGIN

SEAL_RULE = "SEAL_AND_PACKAGE_HYPERLEX_V5_STAGE_A_B_V1R2_PIPELINE"
PACKAGING_ID = "HYPERLEX_V5_STAGE_A_B_V1R2_PACKAGE_V1"
SCHEMA_SEAL = "hyperlex.classification.v5.stage_a_b_v1r2_seal_package.v1"
SCHEMA_MANIFEST = "hyperlex.classification.v5.pipeline_dependency_manifest.v1"
HUB_STATUS = "NOT_AUTHORIZED"
NEXT_ACTION_CLEAN = "QUALIFY_HYPERLEX_V5_PIPELINE_ON_FRESH_EVALUATION_SURFACE"
NEXT_ACTION_DEFER = "PACKAGE_HYPERLEX_V5_FOR_INTEGRATION_OR_RELEASE"

N_INDEX_RECORDS_PIN = 948
ALIGNMENT_RECEIPT_SHA256_PIN = (
    "9f9c435563921bdc12bb762c363afded6291f63390f0014c7d8407af985ad5b9"
)

# Sealed V1R2 alignment witnesses (validation).
WITNESS_FALSE_ENTRY = 0.03356890459363958
WITNESS_FAMILY_PRECISION = 0.8089887640449438
WITNESS_SELECTIVE_ACCURACY = 0.9362279511533242
TOL_FALSE_ENTRY = 0.002
TOL_FAMILY_PRECISION = 0.02
TOL_SELECTIVE_ACCURACY = 0.02

LOCAL_WEIGHT_LAYOUT = {
    "trunk": "~/.hyperlex/models/trunks/ModernBERT-base",
    "model_wide_best": (
        "~/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
        "model.safetensors"
    ),
    "stage_a_best": "~/.hyperlex/models/STAGE_A_BEST/model.safetensors",
    "stage_b_index": (
        "~/.hyperlex/hlx-private-or-operator-path/"
        "classification-v5-stage-b-v1r2-*/STAGE_B_INDEX.json"
    ),
}

PIPELINE_LIMITATIONS = {
    **KNOWN_LIMITATIONS,
    "STAGE_B_VALIDATION_SCOPE": (
        "Stage-B validation is conditional on canonical Stage-A admission "
        "behavior on V1R2."
    ),
    "RESERVE": "SPENT_NOT_RESCORED",
    "HUB_PUBLISH": HUB_STATUS,
}

HISTORICAL_STATE = {
    "previous_STAGE_A_BEST": {
        "checkpoint_sha256": PREVIOUS_STAGE_A_BEST_SHA256,
        "status": "SUPERSEDED",
    },
    "incomplete_historical_candidate": {
        "checkpoint_sha256": INCOMPLETE_HISTORICAL_CHECKPOINT_SHA256,
        "status": "NON_PROMOTABLE_PACKAGING_ARTIFACT",
    },
    "historical_v1r9_stage_b_index": {
        "index_sha256": HISTORICAL_V1R9_INDEX_SHA256,
        "status": "HISTORICAL",
    },
    "historical_v1r9_stage_b_floors": {
        "minimum_family_score": HISTORICAL_V1R9_MINIMUM_FAMILY_SCORE,
        "minimum_top1_top2_margin": HISTORICAL_V1R9_MINIMUM_TOP1_TOP2_MARGIN,
        "status": "HISTORICAL",
    },
}


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def pipeline_dependency_manifest(*, code_revision: str) -> dict[str, Any]:
    ontology_sha = vocabulary_sha256()
    payload = {
        "pipeline_version": PIPELINE_ID,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "stage_a_architecture_objective_version": OBJECTIVE_ID,
        "stage_a_thresholds": {
            "relation": CANONICAL_RELATION_THRESHOLD,
            "resolvability": CANONICAL_RESOLVABILITY_THRESHOLD,
        },
        "stage_a_input_contract_version": CONTRACT_ID,
        "gold_identifiability_contract_version": CONTRACT_ID,
        "stage_a_surface_id": V1R2_SURFACE_ID,
        "stage_a_surface_dataset_sha256": V1R2_DATASET_SHA256_PIN,
        "stage_b_index_sha256": FROZEN_INDEX_SHA256,
        "stage_b_index_row_count": N_INDEX_RECORDS_PIN,
        "stage_b_score_floor": FROZEN_MINIMUM_FAMILY_SCORE,
        "stage_b_margin_floor": FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
        "stage_b_ontology_version": ontology_sha,
        "stage_b_ontology_size": len(ACTIVE_FAMILY_VOCABULARY),
        "canonical_schema_versions": {
            "stage_a_canonical": stage_a_canonical_contract()["schema"],
            "stage_a_forward": SCHEMA_FORWARD,
            "stage_a_b_pipeline": SCHEMA_PIPELINE,
            "stage_a_b_pipeline_forward": SCHEMA_PIPELINE_FORWARD,
            "stage_b_integration": stage_b_contract()["schema"],
            "seal_package": SCHEMA_SEAL,
            "dependency_manifest": SCHEMA_MANIFEST,
        },
        "factorized_heads": list(FACTORIZED_HEAD_NAMES),
        "load_sequence": list(CANONICAL_LOAD_SEQUENCE),
        "model_input": list(MODEL_INPUT),
        "code_revision": code_revision,
        "schema": SCHEMA_MANIFEST,
    }
    payload["PIPELINE_DEPENDENCY_MANIFEST_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in payload.items()
                if k != "PIPELINE_DEPENDENCY_MANIFEST_SHA256"
            }
        )
    )
    return payload


def package_contract(*, code_revision: str) -> dict[str, Any]:
    manifest = pipeline_dependency_manifest(code_revision=code_revision)
    return {
        "PACKAGING_ID": PACKAGING_ID,
        "SEAL_RULE": SEAL_RULE,
        "HUB_STATUS": HUB_STATUS,
        "PIPELINE_ID": PIPELINE_ID,
        "STAGE_A_CANONICAL": CANONICAL_ID,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "STAGE_B_RULE": STAGE_B_RULE,
        "STAGE_B_EXPERIMENT_ID": STAGE_B_EXPERIMENT_ID,
        "STAGE_B_V1R2_EXPERIMENT_ID": STAGE_B_V1R2_EXPERIMENT_ID,
        "STAGE_B_INDEX_SHA256": FROZEN_INDEX_SHA256,
        "V5_STAGE_A_STATE": V5_STAGE_A_STATE,
        "V5_STAGE_B_STATE": V5_STAGE_B_STATE,
        "V5_STAGE_A_B_PIPELINE_STATE": V5_STAGE_A_B_PIPELINE_STATE,
        "STAGE_A_RESEARCH_LOOP": STAGE_A_RESEARCH_LOOP,
        "artifacts": {
            "runtime_configuration": True,
            "stage_a_artifact_reference": STAGE_A_BEST_SHA256,
            "stage_b_index_reference": FROZEN_INDEX_SHA256,
            "threshold_floor_configuration": True,
            "ontology_schema_versions": True,
            "dependency_manifest": True,
            "load_validator": True,
            "inference_adapter": True,
            "provenance_manifest": True,
            "limitations_manifest": True,
            "historical_experiment_artifacts_bundled": False,
        },
        "dependency_manifest": manifest,
        "PIPELINE_DEPENDENCY_MANIFEST_SHA256": manifest[
            "PIPELINE_DEPENDENCY_MANIFEST_SHA256"
        ],
        "factorized_heads": list(FACTORIZED_HEAD_NAMES),
        "flow": list(PIPELINE_FLOW),
        "inference_policy": canonical_inference_policy(),
        "known_limitations": dict(PIPELINE_LIMITATIONS),
        "historical_state": dict(HISTORICAL_STATE),
        "load_sequence": list(CANONICAL_LOAD_SEQUENCE),
        "local_weight_layout": dict(LOCAL_WEIGHT_LAYOUT),
        "model_input": list(MODEL_INPUT),
        "publish_authorized": False,
        "reserve": SPENT_RESERVE,
        "reserve_status": SPENT_RESERVE_STATUS,
        "runtime_registry": runtime_registry(),
        "schema": SCHEMA_SEAL,
        "stage_b_alignment_receipt_sha256": ALIGNMENT_RECEIPT_SHA256_PIN,
        "weights_in_git": False,
    }


def map_final_decision(decision_type: str) -> str:
    """Map Stage-B compose decision_type onto pipeline forward final_decision."""
    if decision_type == "NONE":
        return "NO_EVIDENCE"
    if decision_type in {"FAMILY", "AMBIGUOUS", "ABSTAIN"}:
        return decision_type
    raise ValueError(f"unknown_decision_type:{decision_type}")


def build_runtime_forward(
    *,
    stage_a_decision: str,
    p_relation: float,
    p_resolvable: float,
    stage_b_result: Mapping[str, Any] | None,
    stage_b_executed: bool,
) -> dict[str, Any]:
    """Canonical end-to-end forward packet for the sealed pipeline package."""
    base = build_pipeline_forward(
        stage_a_decision=stage_a_decision,
        p_relation=p_relation,
        p_resolvable=p_resolvable,
    )
    if not stage_b_executed:
        final = map_final_decision(
            "NONE" if stage_a_decision == "NO_EVIDENCE" else "ABSTAIN"
        )
        return {
            **base,
            "schema": SCHEMA_PIPELINE_FORWARD,
            "stage_b_executed": False,
            "final_decision": final,
            "predicted_family": None,
            "family_score": None,
            "runner_up_family": None,
            "runner_up_score": None,
            "margin": None,
            "stage_a_checkpoint_sha": STAGE_A_BEST_SHA256,
            "stage_b_index_sha": FROZEN_INDEX_SHA256,
            "pipeline_version": PIPELINE_ID,
        }
    result = dict(stage_b_result or {})
    decision_type = str(result.get("decision_type") or "ABSTAIN")
    family_score = result.get("family_score")
    margin = result.get("family_margin")
    return {
        **base,
        "schema": SCHEMA_PIPELINE_FORWARD,
        "stage_b_executed": True,
        "final_decision": map_final_decision(decision_type),
        "predicted_family": result.get("family"),
        "family_score": None if family_score is None else float(family_score),
        "runner_up_family": result.get("runner_up_family"),
        "runner_up_score": (
            None
            if result.get("runner_up_score") is None
            else float(result["runner_up_score"])
        ),
        "margin": None if margin is None else float(margin),
        "stage_a_checkpoint_sha": STAGE_A_BEST_SHA256,
        "stage_b_index_sha": FROZEN_INDEX_SHA256,
        "pipeline_version": PIPELINE_ID,
    }


def compose_runtime_row(
    *,
    stage_a_decision: str,
    p_relation: float,
    p_resolvable: float,
    ranked_candidates: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    from .classification_v5_stage_a_canonical import may_invoke_stage_b

    executed = may_invoke_stage_b(stage_a_decision)
    stage_b_result = None
    if executed:
        stage_b_result = compose_end_to_end(
            evidence_decision=stage_a_decision,
            ranked_candidates=ranked_candidates,
            family_score_min=FROZEN_MINIMUM_FAMILY_SCORE,
            family_margin_min=FROZEN_MINIMUM_TOP1_TOP2_MARGIN,
        )
        # Attach runner-up when available from ranked candidates.
        ordered = sorted(
            list(ranked_candidates or []),
            key=lambda item: (-float(item["score"]), str(item["family"])),
        )
        if len(ordered) > 1:
            stage_b_result = dict(stage_b_result)
            stage_b_result["runner_up_family"] = str(ordered[1]["family"])
            stage_b_result["runner_up_score"] = float(ordered[1]["score"])
    return build_runtime_forward(
        stage_a_decision=stage_a_decision,
        p_relation=p_relation,
        p_resolvable=p_resolvable,
        stage_b_result=stage_b_result,
        stage_b_executed=executed,
    )


def within_tol(observed: float, witness: float, tol: float) -> bool:
    return abs(float(observed) - float(witness)) <= float(tol)


def validate_integration_metrics(metrics: Mapping[str, Any]) -> dict[str, Any]:
    false_entry = float(metrics["false_evidence_entry_rate_on_none"])
    fam_prec = float(metrics["family_emission_precision"])
    selective = float(metrics["selective_accuracy"])
    gating = metrics.get("gating") or {}
    checks = {
        "false_entry_within_tol": within_tol(
            false_entry, WITNESS_FALSE_ENTRY, TOL_FALSE_ENTRY
        ),
        "family_precision_within_tol": within_tol(
            fam_prec, WITNESS_FAMILY_PRECISION, TOL_FAMILY_PRECISION
        ),
        "selective_accuracy_within_tol": within_tol(
            selective, WITNESS_SELECTIVE_ACCURACY, TOL_SELECTIVE_ACCURACY
        ),
        "none_stage_b_zero": int(gating.get("none_entered_stage_b") or 0) == 0,
        "uncertain_stage_b_zero": int(gating.get("uncertain_entered_stage_b") or 0)
        == 0,
        "gating_pass": bool(gating.get("pass")),
        "primary_gate_pass": bool(metrics.get("primary_gate_pass")),
        "secondary_gate_pass": bool(metrics.get("secondary_gate_pass")),
    }
    return {
        "checks": checks,
        "pass": all(checks.values()),
        "observed": {
            "false_evidence_entry_rate_on_none": false_entry,
            "family_emission_precision": fam_prec,
            "selective_accuracy": selective,
            "gating": dict(gating),
        },
        "witnesses": {
            "false_evidence_entry_rate_on_none": WITNESS_FALSE_ENTRY,
            "family_emission_precision": WITNESS_FAMILY_PRECISION,
            "selective_accuracy": WITNESS_SELECTIVE_ACCURACY,
        },
        "tolerances": {
            "false_entry": TOL_FALSE_ENTRY,
            "family_precision": TOL_FAMILY_PRECISION,
            "selective_accuracy": TOL_SELECTIVE_ACCURACY,
        },
    }


def validate_round_trip(mismatches: Mapping[str, int]) -> dict[str, Any]:
    checks = {
        "stage_a_decision_mismatch_count": int(
            mismatches.get("stage_a_decision_mismatch_count") or 0
        )
        == 0,
        "stage_b_execution_mismatch_count": int(
            mismatches.get("stage_b_execution_mismatch_count") or 0
        )
        == 0,
        "family_final_decision_mismatch_count": int(
            mismatches.get("family_final_decision_mismatch_count") or 0
        )
        == 0,
    }
    return {"checks": checks, "pass": all(checks.values()), "mismatches": dict(mismatches)}


def choose_freeze_state(
    *,
    cold_load_pass: bool,
    integration_pass: bool,
    round_trip_pass: bool,
    stale_audit_pass: bool,
    parent_pin_pass: bool,
    entry_gating_pass: bool,
) -> dict[str, Any]:
    ok = all(
        [
            cold_load_pass,
            integration_pass,
            round_trip_pass,
            stale_audit_pass,
            parent_pin_pass,
            entry_gating_pass,
        ]
    )
    return {
        "V5_STAGE_A_STATE": V5_STAGE_A_STATE,
        "V5_STAGE_B_STATE": V5_STAGE_B_STATE if ok else "ALIGNMENT_APPLIED_PENDING_SEAL",
        "V5_STAGE_A_B_PIPELINE_STATE": (
            V5_STAGE_A_B_PIPELINE_STATE if ok else "SEAL_FAILED"
        ),
        "STAGE_A_RESEARCH_LOOP": STAGE_A_RESEARCH_LOOP,
        "sealed": ok,
        "reason": "ok" if ok else "validation_or_packaging_failed",
    }


def hf_card_section() -> str:
    return f"""## V5 Stage-A/B V1R2 pipeline (local; Hub unpublished)

**Packaging ID:** `{PACKAGING_ID}`
**Pipeline:** `{PIPELINE_ID}` · Stage-A `{CANONICAL_ID}`
**States:** Stage-A `{V5_STAGE_A_STATE}` · Stage-B `{V5_STAGE_B_STATE}` · Pipeline `{V5_STAGE_A_B_PIPELINE_STATE}`

| Artifact | SHA256 / value |
| --- | --- |
| `STAGE_A_BEST` | `{STAGE_A_BEST_SHA256}` |
| `MODEL_WIDE_BEST` | `{MODEL_WIDE_BEST_SHA256}` |
| Stage-B index | `{FROZEN_INDEX_SHA256}` (n={N_INDEX_RECORDS_PIN}) |
| Stage-B floors | score `{FROZEN_MINIMUM_FAMILY_SCORE}`, margin `{FROZEN_MINIMUM_TOP1_TOP2_MARGIN}` |
| Stage-A thresholds | relation `{CANONICAL_RELATION_THRESHOLD}`, resolvability `{CANONICAL_RESOLVABILITY_THRESHOLD}` |
| Surface | `{V1R2_SURFACE_ID}` / `{V1R2_DATASET_SHA256_PIN}` |

**Flow:** text → Stage-A → (NONE stop | UNCERTAIN abstain | PRESENT → Stage-B → FAMILY|AMBIGUOUS|ABSTAIN).

**Load:** ModernBERT → MODEL_WIDE_BEST → STAGE_A_BEST (`relation_head` + `resolvability_head`) → Stage-B index `{FROZEN_INDEX_SHA256[:16]}…`.

**Limitations:** DOMAIN_IRRELEVANT=`NOT_ESTABLISHED`; SHORT_ATOM_POSITIVE=`LOW_SUPPORT`; CONTEXT_DEPENDENT_GOLD=`OUTSIDE_CURRENT_TEXT_ONLY_STAGE_A_CONTRACT`; Stage-B validation conditional on Stage-A admission.

**Hub:** `{HUB_STATUS}`. Weights/index stay on operator paths; not in git.
"""


def build_seal_receipt(
    *,
    code_revision: str,
    cold_load: Mapping[str, Any],
    integration: Mapping[str, Any],
    round_trip: Mapping[str, Any],
    stale_audit: Mapping[str, Any],
    sealed_at: str | None = None,
) -> dict[str, Any]:
    parent = verify_stage_b_parent_and_floors()
    entry = verify_entry_gating()
    contract = package_contract(code_revision=code_revision)
    freeze = choose_freeze_state(
        cold_load_pass=bool(cold_load.get("pass")),
        integration_pass=bool(integration.get("pass")),
        round_trip_pass=bool(round_trip.get("pass")),
        stale_audit_pass=bool(stale_audit.get("pass")),
        parent_pin_pass=bool(parent.get("pass")),
        entry_gating_pass=bool(entry.get("pass")),
    )
    payload = {
        "BEST_MUTATED": False,
        "EXPERIMENT_ID": "HLX-CLASSIFICATION-V5-STAGE-A-B-V1R2-SEAL-001",
        "HUB_STATUS": HUB_STATUS,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "NEXT_ACTION": NEXT_ACTION_CLEAN if freeze["sealed"] else "DIAGNOSE_V5_SEAL_FAILURE",
        "PACKAGING_ID": PACKAGING_ID,
        "PIPELINE_ID": PIPELINE_ID,
        "PIPELINE_RULE": PIPELINE_RULE,
        "RESERVE_CONSUMED": False,
        "SEAL_RULE": SEAL_RULE,
        "STAGE_A_BEST": STAGE_A_BEST_SHA256,
        "STAGE_A_CANONICAL": CANONICAL_ID,
        "STAGE_B_INDEX_SHA256": FROZEN_INDEX_SHA256,
        "TRAIN": False,
        "code_revision": code_revision,
        "cold_load": dict(cold_load),
        "contract": contract,
        "entry_gating": entry,
        "freeze_state": freeze,
        "historical_state": dict(HISTORICAL_STATE),
        "integration": dict(integration),
        "known_limitations": dict(PIPELINE_LIMITATIONS),
        "parent_pins": parent,
        "pipeline_contract": pipeline_contract(),
        "round_trip": dict(round_trip),
        "runtime_registry": runtime_registry(),
        "schema": SCHEMA_SEAL,
        "sealed_at": sealed_at or utc_now_iso(),
        "stale_reference_audit": dict(stale_audit),
        "stage_b_alignment_receipt_sha256": ALIGNMENT_RECEIPT_SHA256_PIN,
    }
    payload["PIPELINE_DEPENDENCY_MANIFEST_SHA256"] = contract[
        "PIPELINE_DEPENDENCY_MANIFEST_SHA256"
    ]
    payload["SEAL_PACKAGE_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in payload.items()
                if k != "SEAL_PACKAGE_RECEIPT_SHA256"
            }
        )
    )
    return payload
