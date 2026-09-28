"""SELECT-005 supply review. Does not train, append the ledger, or seal numbers.

Operator decisions are validated against the existing settlement enums.
A stored ``INFERRED`` class is not promoted to ``OBSERVED``.
``eval_settlement.settle`` is the only apply path, and it is not committed
when the held-out stream refuses the row.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .eval_settlement import DECISIONS, settle

EXPERIMENT_ID = "HLX-EXP-2026-09-27-SELECT-005"
TRANSITION = "SELECT_005_RESERVE_SUPPLY_AND_GOVERNANCE_AUTHORIZATION"
READY_BUCKET = "READY_FOR_OPERATOR_REVIEW"
EXCLUDED_BUCKETS = frozenset(
    {"RIGHTS_BLOCKED", "PROVENANCE_BLOCKED", "DUPLICATE_OR_OVERLAP"}
)
PACKET_ID = "HLX-EVAL-REVIEW-2026-09-27-001"
PREREGISTRATION_INCOMPLETE = "SELECT_005_PREREGISTRATION_INCOMPLETE"
THRESHOLDS_BLOCKED = "BLOCKED_PENDING_OPERATOR_AUTHORIZATION"
THRESHOLD_SCHEMA = "hyperlex.threshold_authorization.v1"
SELECT_ADMISSION_JSON_SCHEMA_EXISTS = True
THRESHOLD_AUTHORIZATION_JSON_SCHEMA_EXISTS = True
UNRESOLVED_SCHEDULE_FIELDS = (
    "learning_rate",
    "batch_size",
    "gradient_accumulation",
    "seed",
)
# Named by the unsealed SELECT-005 proposal. Not a sealed preregistration.
RESOLVED_SCHEDULE = {
    "candidate_early_stop": "1",
    "candidate_max_epochs": "12",
    "candidate_min_epochs": "4",
    "candidate_patience": "4",
    "checkpoint_ties": "keep_earlier",
    "control_early_stop": "0",
    "control_max_epochs": "40",
    "restore_best": True,
    "scientific_variable": "train_schedule",
    "selection_metric": "classify_macro_f1_nonnone",
    "strict_increase": True,
    "warm_start_name": "hyperlex-encoder-modernbert-base-seed-morph65",
}


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_review_ready(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Packet order. Blocked, provenance-blocked, and duplicate rows stay out."""
    ready: list[dict[str, Any]] = []
    for row in rows:
        bucket = str(row.get("bucket") or "")
        if bucket in EXCLUDED_BUCKETS:
            continue
        if bucket != READY_BUCKET:
            raise SystemExit(f"REFUSE: unknown review bucket: {bucket}")
        ready.append(dict(row))
    return ready


def manifest_record(
    row: Mapping[str, Any],
    *,
    normalized_identity: str,
    source_class: str,
    source_provenance: str,
    existing_settlement_state: str,
) -> dict[str, Any]:
    """Identity surface only. No slice, quota, expected label, or model output."""
    return {
        "existing_settlement_state": existing_settlement_state,
        "license_rights_state": str(row.get("rights basis") or ""),
        "normalized_identity": normalized_identity,
        "provenance_state": source_provenance,
        "review_row_id": str(row.get("candidate_id") or ""),
        "source": str(row.get("source") or ""),
        "source_class": source_class,
        "source_identity": str(row.get("source locator") or ""),
        "surface": str(row.get("canonical text") or ""),
    }


def manifest_jsonl(records: Sequence[Mapping[str, Any]]) -> str:
    return "".join(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n" for record in records)


def refuse_observed_promotion(source_class: str, attest: str | None) -> None:
    """The stored registry class is not promoted to OBSERVED."""
    if source_class == "INFERRED" and attest == "OBSERVED":
        raise SystemExit("REFUSE: stored INFERRED class is not promoted to OBSERVED")


def validate_operator_decision(record: Mapping[str, Any], *, source_class: str) -> dict[str, Any]:
    decision = str(record.get("decision") or "")
    if decision not in DECISIONS:
        raise SystemExit(f"REFUSE: invalid decision: {decision}")
    attest = record.get("attest")
    if attest is not None and attest not in ("OBSERVED", "INFERRED"):
        raise SystemExit(f"REFUSE: invalid attest: {attest}")
    refuse_observed_promotion(source_class, attest if isinstance(attest, str) else None)
    if decision == "UNRESOLVED" and (record.get("semantic_family") is not None or attest is not None):
        raise SystemExit("REFUSE: UNRESOLVED requires null semantic_family and null attest")
    if decision == "NONE" and record.get("semantic_family") != "none":
        raise SystemExit("REFUSE: NONE requires semantic_family none")
    if decision == "ACCEPT" and not record.get("semantic_family"):
        raise SystemExit("REFUSE: ACCEPT requires an explicit semantic_family")
    rights = str(record.get("rights") or "")
    source_rights = str(record.get("source_rights") or "")
    if source_rights and rights != source_rights:
        raise SystemExit("REFUSE: rights state was changed")
    return dict(record)


def settlement_refusal(
    decisions: Sequence[Mapping[str, Any]],
    stream_rows: Sequence[Mapping[str, Any]],
) -> str:
    """Call the canonical validator. It does not append."""
    try:
        settle(
            stream_rows,
            decisions,
            batch_id="HLX-EVAL-SETTLE-SELECT-005-SUPPLY-001",
            operator="cursor-cloud-agent",
            provenance="SELECT-005 supply review",
            settled_at="2026-09-28T20:39:00Z",
        )
    except SystemExit as exc:
        return str(exc)
    return "APPLIED"


def preregistration_status() -> dict[str, Any]:
    """SELECT-005 never states LR, batch, gradient accumulation, or seed.

    Trainer defaults and the SELECT-004 environment are not an inheritance rule.
    """
    return {
        "experiment_id": EXPERIMENT_ID,
        "inherited_select_004_hyperparameters": False,
        "resolved_schedule": dict(RESOLVED_SCHEDULE),
        "sealed": False,
        "state": PREREGISTRATION_INCOMPLETE,
        "unresolved_fields": list(UNRESOLVED_SCHEDULE_FIELDS),
    }


def threshold_authorization_proposal() -> dict[str, Any]:
    """Metric names from the SELECT decision contract. Numbers stay unset."""
    names = (
        ("classify_macro_f1_nonnone", "primary_selection", "macro_f1", "higher_than_control"),
        ("classification_accuracy", "preservation", "accuracy", "not_below_control_by_more_than_floor"),
        ("observed_label_accuracy", "preservation", "accuracy", "not_below_control_by_more_than_floor"),
        ("unbind_clean_exact", "preservation", "exact_match", "not_below_control_by_more_than_floor"),
    )
    thresholds = [
        {
            "authorization_state": THRESHOLDS_BLOCKED,
            "derivation": "OPERATOR_JUDGMENT_ABSENT",
            "direction": direction,
            "metric": metric,
            "numeric_threshold": None,
            "operator": None,
            "role": role,
            "units": units,
        }
        for metric, role, units, direction in names
    ]
    return {
        "decision_thresholds": {},
        "experiment_id": EXPERIMENT_ID,
        "inherited_from_select_004": False,
        "metrics": thresholds,
        "schema": THRESHOLD_SCHEMA,
        "sealed": False,
        "state": THRESHOLDS_BLOCKED,
        "threshold_authorization_json_schema_exists": THRESHOLD_AUTHORIZATION_JSON_SCHEMA_EXISTS,
        "training_launch_authorized": False,
    }
