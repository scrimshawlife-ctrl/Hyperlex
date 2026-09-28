"""SELECT-005 source contract and preregistration completion.

Does not train, append the settlement log, or append the identity ledger.
The exhausted settlement universe is not an input. SELECT-004 numeric
floors are not copied. A stale exposure snapshot is not bypassed.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from .select_005_reserve import (
    CLEARED_RIGHTS,
    EXPERIMENT_ID,
    FAILURE_QUOTA,
    PROPOSED_SCHEDULE,
    REQUIRED_SLICES,
    canonical_json,
    census,
    exclusion_reason,
)

TRANSITION = "SELECT_005_SOURCE_AND_PREREGISTRATION_COMPLETION_AUTHORIZATION"
PREREGISTRATION_SEALED = "SELECT_005_PREREGISTRATION_SEALED"
THRESHOLDS_BLOCKED = "BLOCKED_PENDING_OPERATOR_AUTHORIZATION"
THRESHOLD_SCHEMA = "hyperlex.threshold_authorization.v1"
SELECT_ADMISSION_JSON_SCHEMA_EXISTS = False
THRESHOLD_AUTHORIZATION_JSON_SCHEMA_EXISTS = False
TRAINING_AUTHORIZED = False
EXHAUSTED_STREAM_RUN = "hs-20260925T211358Z"
EXHAUSTED_SETTLEMENT_COUNT = 339
BOX_SNAPSHOT_LIMIT_H = 6.0
ADMISSIBLE_SOURCE_TYPES = ("wiktionary_category", "wikipedia_prose")
WARM_START_NAME = "hyperlex-encoder-modernbert-base-seed-morph65"
WARM_START_SHA256 = "96838b9656a84c3fee1773a41fdf2fbbec2f88f3bc948e4acfbe06c194ac5587"
BEST_NAME = "hyperlex-encoder-modernbert-base-seed-select004"
BEST_SHA256 = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
CONTROL_RECIPE_ENV_SHA256 = "edb7163f388de71c258db2d68d03ac4e6d6a011548236666250d5d0f5d05e0f1"
FRESH_BATCH_ID = "HLX-EVAL-RESERVE-SELECT-005-FRESH-001"
LABEL_BLIND_FORBIDDEN = frozenset(
    {
        "attest",
        "class",
        "decision",
        "expected_slice",
        "lineage",
        "model_score",
        "semantic_family",
        "task",
        "unbind_clean",
    }
)
METRIC_NAMES = (
    "classify_macro_f1_nonnone",
    "classification_accuracy",
    "observed_label_accuracy",
    "unbind_clean_exact",
)


def initialization_decision() -> dict[str, Any]:
    """The written proposal warm-starts morph65 while BEST is already select004.

    That sentence is the experiment. The trainer does not choose between them.
    """
    return {
        "best_name": BEST_NAME,
        "best_not_moved": True,
        "best_sha256": BEST_SHA256,
        "decision": "morph65_new_schedule",
        "experiment_id": EXPERIMENT_ID,
        "rejected_alternative": "select004_best_new_schedule",
        "trainer_default_did_not_decide": True,
        "warm_start_name": WARM_START_NAME,
        "warm_start_sha256": WARM_START_SHA256,
    }


def sealed_preregistration() -> dict[str, Any]:
    """Freeze the control-arm recipe. Do not transfer SELECT-004's variable."""
    proposed = json_copy(PROPOSED_SCHEDULE)
    return {
        "experiment_id": EXPERIMENT_ID,
        "held_constant": {
            "batch_size": 8,
            "gradient_accumulation": 1,
            "learning_rate": "2e-5",
            "seed": None,
            "seed_policy": "HLX_SEED_UNSET_FROZEN",
        },
        "held_constant_authority": {
            "batch_size": "Recorded HYPERLEX_TRAIN_BATCH on the morph65 continuation control recipe.",
            "control_recipe_env_sha256": CONTROL_RECIPE_ENV_SHA256,
            "document": "specs/007-hyperlexical-model/evaluation-reserve.md",
            "gradient_accumulation": (
                "The trainer takes one optimizer step per batch and has no "
                "accumulation parameter. 1 freezes that behavior."
            ),
            "inherited_from_select_004": False,
            "learning_rate": "Recorded HYPERLEX_TRAIN_LR on the morph65 continuation control recipe.",
            "same_numeric_optimizer_values_as_select_004_candidate_env": True,
            "seed": "The reconstructed recipe seals HLX_SEED unset. Both arms share that frozen policy.",
            "select_004_scientific_variable_not_transferred": "HLX_SELECT_METRIC",
            "trainer_default_did_not_decide": True,
        },
        "initialization": initialization_decision(),
        "pinned_export_rows": proposed["pinned_export_rows"],
        "pinned_export_sha256": proposed["pinned_export_sha256"],
        "schedule": {
            "baseline": proposed["baseline"],
            "candidate": proposed["candidate"],
            "checkpoint_rule": proposed["checkpoint_rule"],
            "selection_metric": proposed["selection_metric"],
        },
        "schema": "hyperlex.preregistration.v1",
        "scientific_variable": "train_schedule",
        "sealed": True,
        "state": PREREGISTRATION_SEALED,
        "training_authorized": TRAINING_AUTHORIZED,
        "training_launch_authorized": False,
        "unset_fields": [],
    }


def threshold_authorization_proposal() -> dict[str, Any]:
    """Name the four metrics. Leave every number unset.

    The schedule design supports a strict improvement of the candidate arm
    over the control arm. It does not assign a preservation floor. SELECT-004
    floors do not transfer, and no number is invented here.
    """
    metrics = [
        {
            "authorization_state": THRESHOLDS_BLOCKED,
            "derivation": "OPERATOR_JUDGMENT_ABSENT",
            "metric": name,
            "numeric_threshold": None,
        }
        for name in METRIC_NAMES
    ]
    return {
        "comparison_baseline": "SELECT-005 control arm",
        "decision_thresholds": {},
        "experiment_id": EXPERIMENT_ID,
        "inherited_from_select_004": False,
        "metrics": metrics,
        "not_seed_morph78": True,
        "primary_comparison_supported_by_schedule_design": (
            "candidate classify_macro_f1_nonnone strictly greater than the "
            "control arm; equality does not promote"
        ),
        "reason_unsealed": (
            "No SELECT-005 derivation assigns a number. Predecessor floors "
            "do not transfer. A number was not invented."
        ),
        "schema": THRESHOLD_SCHEMA,
        "sealed": False,
        "state": THRESHOLDS_BLOCKED,
        "threshold_authorization_json_schema_exists": THRESHOLD_AUTHORIZATION_JSON_SCHEMA_EXISTS,
        "training_launch_authorized": False,
    }


def source_contract() -> dict[str, Any]:
    """Rights-cleared ingest rules for a reserve that is not the 339."""
    return {
        "admissible_source_types": list(ADMISSIBLE_SOURCE_TYPES),
        "cleared_rights": CLEARED_RIGHTS,
        "exhausted_settlement_count": EXHAUSTED_SETTLEMENT_COUNT,
        "exhausted_stream_is_a_source": False,
        "exhausted_stream_run": EXHAUSTED_STREAM_RUN,
        "experiment_id": EXPERIMENT_ID,
        "harvest_fence": (
            "hs_run.py refuses when the box exposure snapshot is older than "
            "6 hours. This pass does not bypass that fence and does not fetch."
        ),
        "label_blind": True,
        "required_slices": list(REQUIRED_SLICES),
        "selection_label_blind": True,
        "settlement_slice_gap": (
            "The settlement record emits no task, class, lineage, or "
            "unbind_clean. A decision-only row is SLICE_LABELS_ABSENT. "
            "This pass does not attach those fields beside the contract."
        ),
        "transition": TRANSITION,
        "unbind_clean": (
            "A new campaign must include compositional material that can "
            "satisfy soft_ceiling.clean_surface. Which rows enter the review "
            "surface is chosen before labels. Princeton WordNet is "
            "compositional and is not the census rights token."
        ),
        "wordnet": {
            "admitted_alone": False,
            "census_rights_token": "not CC-BY-SA",
            "license": "Princeton WordNet 3.0",
        },
    }


def exposure_snapshot_refusal(
    ages_hours: Mapping[str, float],
    *,
    limit_h: float = BOX_SNAPSHOT_LIMIT_H,
) -> str | None:
    """Return the harvest refusal, or None when every snapshot is inside the fence."""
    if not ages_hours:
        return "REFUSE: no box exposure snapshot"
    stale = [age for age in ages_hours.values() if float(age) > limit_h]
    if not stale:
        return None
    worst = max(stale)
    return f"REFUSE: box exposure snapshot is {worst:.1f}h old (> {limit_h:g}h)"


def label_blind_surface(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Identity, rights, and provenance only. Labels are a later operator act."""
    surface = []
    for row in rows:
        carried = sorted(LABEL_BLIND_FORBIDDEN.intersection(row))
        if carried:
            raise SystemExit("REFUSE: label-blind surface carries " + ",".join(carried))
        source_type = str(row.get("source_type") or "")
        if source_type not in ADMISSIBLE_SOURCE_TYPES:
            raise SystemExit(
                "REFUSE: source_type is not rights-cleared for this contract: "
                + (source_type or "missing")
            )
        for key in ("row_id", "text_hash", "source_url", "license"):
            if not str(row.get(key) or "").strip():
                raise SystemExit(f"REFUSE: provenance field missing: {key}")
        license_text = str(row["license"])
        compact = license_text.upper().replace(" ", "").replace("-", "")
        if "CCBYSA" not in compact:
            raise SystemExit("REFUSE: license is not CC-BY-SA")
        surface.append(
            {
                "license": license_text,
                "row_id": str(row["row_id"]),
                "source_type": source_type,
                "source_url": str(row["source_url"]),
                "text_hash": str(row["text_hash"]),
            }
        )
    return surface


def fresh_census(
    events: Sequence[Mapping[str, Any]],
    ledger_state: Mapping[str, str],
    export_hashes: set[str],
    *,
    fences: Mapping[str, Mapping[str, set[str]]] | None = None,
) -> dict[str, Any]:
    """Census a new source. The exhausted stream is refused before routing."""
    for event in events:
        run = str(event.get("source_run") or "")
        if run == EXHAUSTED_STREAM_RUN or event.get("exhausted_universe") is True:
            raise SystemExit("REFUSE: exhausted settlement universe is not a SELECT-005 source")
    result = census(
        events,
        ledger_state,
        export_hashes,
        fences=fences,
        batch_id=FRESH_BATCH_ID,
    )
    result["exhausted_universe_consulted"] = False
    result["source"] = "fresh"
    if result.get("failure") is None and result.get("reserve_row_count"):
        result["reserve_status"] = "FROZEN"
    else:
        result["reserve_status"] = FAILURE_QUOTA if result.get("failure") == FAILURE_QUOTA else result.get("failure")
    return result


def completion_report(snapshot_ages: Mapping[str, float]) -> dict[str, Any]:
    """One reconstruction. Live ages are supplied by the caller."""
    refusal = exposure_snapshot_refusal(snapshot_ages)
    body = fresh_census([], {}, set())
    return {
        "acquisition_refusal": refusal,
        "admission_receipt": None,
        "census_failure": body["failure"],
        "exhausted_universe_consulted": False,
        "experiment_id": EXPERIMENT_ID,
        "initialization": initialization_decision(),
        "isolation": "NOT_RUN_NO_ROWS",
        "label_blind_surface_count": 0,
        "preregistration_state": PREREGISTRATION_SEALED,
        "provenance": "NO_ADMITTED_ROWS",
        "reserve_manifest_created": False,
        "reserve_row_count": body["reserve_row_count"],
        "rows_acquired": 0,
        "settlements_appended": 0,
        "snapshot_ages_hours": {key: snapshot_ages[key] for key in sorted(snapshot_ages)},
        "threshold_state": THRESHOLDS_BLOCKED,
        "training_authorized": False,
        "training_launch_authorized": False,
        "transition": TRANSITION,
    }


def json_copy(payload: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(canonical_json(payload))


def decision_only_exclusion(event: Mapping[str, Any]) -> str:
    """Public alias so a settlement-shaped row is judged by the existing census."""
    return exclusion_reason(event, {}, set())
