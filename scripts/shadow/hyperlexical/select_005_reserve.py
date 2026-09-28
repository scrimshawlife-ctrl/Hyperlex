"""SELECT-005 fresh-reserve census. Dry run only.

This module does not train, score a candidate, append the identity ledger,
or seal a preregistration. ``admit`` remains the writer. A census that cannot
fill every required slice freezes no reserve rows.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from .identity_ledger import (
    GENERATION,
    PLANNING_TARGETS,
    REQUIRED_SLICES,
    derived_state,
    slices_of,
)

EXPERIMENT_ID = "HLX-EXP-2026-09-27-SELECT-005"
TRANSITION = "SELECT_005_RESERVE_AND_ADMISSION_PREPARATION_AUTHORIZATION"
BATCH_ID = "HLX-EVAL-RESERVE-SELECT-005-CENSUS-001"
ADMISSIBLE_DECISIONS = frozenset({"ACCEPT", "RECLASSIFY", "NONE"})
CLEARED_RIGHTS = "CC-BY-SA"
REQUIRED_PROVENANCE = ("row_id", "text_hash", "rights", "decision", "provenance")
ADMISSION_FLOORS = {key: 1 for key in REQUIRED_SLICES}
FAILURE_QUOTA = "RESERVE_QUOTA_UNFILLED"
FAILURE_ISOLATION = "RESERVE_ISOLATION_FAILURE"
FAILURE_PROVENANCE = "RESERVE_PROVENANCE_FAILURE"
SELECT_ADMISSION_JSON_SCHEMA_EXISTS = False
TRAINING_AUTHORIZED = False

# The written SELECT-005 proposal. Unset trainer fields stay unset.
PROPOSED_SCHEDULE: dict[str, Any] = {
    "baseline": {
        "HYPERLEX_EARLY_STOP": "0",
        "HYPERLEX_EARLY_STOP_MIN_EPOCHS": None,
        "HYPERLEX_EARLY_STOP_PATIENCE": None,
        "HYPERLEX_TRAIN_EPOCHS": "40",
    },
    "candidate": {
        "HYPERLEX_EARLY_STOP": "1",
        "HYPERLEX_EARLY_STOP_MIN_EPOCHS": "4",
        "HYPERLEX_EARLY_STOP_PATIENCE": "4",
        "HYPERLEX_TRAIN_EPOCHS": "12",
    },
    "checkpoint_rule": {
        "restore_best": True,
        "strict_increase": True,
        "ties": "keep_earlier",
    },
    "experiment_id": EXPERIMENT_ID,
    "pinned_export_rows": 9150,
    "pinned_export_sha256": "64b7d3dede25047cb6dd2e5b663f7fa72946ec82ac1a8816ae34622d1aaac430",
    "scientific_variable": "train_schedule",
    "sealed": False,
    "selection_metric": "classify_macro_f1_nonnone",
    "unset_fields": [
        "batch_size",
        "gradient_accumulation",
        "learning_rate",
        "seed",
    ],
    "warm_start_name": "hyperlex-encoder-modernbert-base-seed-morph65",
}


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def schedule_spec_sha256() -> str:
    return sha256_text(canonical_json(PROPOSED_SCHEDULE))


def _order_key(digest: str, batch_id: str = BATCH_ID) -> str:
    return hashlib.sha256(f"{GENERATION}|{batch_id}|{digest}".encode("utf-8")).hexdigest()


def _slices(event: Mapping[str, Any]) -> set[str]:
    """Slice labels only when the row already carries them. Attest is not a class."""
    task = str(event.get("task") or "")
    if not task:
        return set()
    label: dict[str, Any] = {
        "task": task,
        "class": str(event.get("class") or ""),
        "lineage": str(event.get("lineage") or ""),
        "split": str(event.get("split") or ""),
    }
    if task == "unbind":
        label["unbind_clean"] = event.get("unbind_clean") is True
    return slices_of({"labels": [label]})


def exclusion_reason(
    event: Mapping[str, Any],
    ledger_state: Mapping[str, str],
    export_hashes: set[str],
) -> str:
    """One reason. Provenance, then existing consumption, then decision and rights."""
    if any(not str(event.get(key) or "").strip() for key in REQUIRED_PROVENANCE):
        return "PROVENANCE_INCOMPLETE"
    digest = str(event["text_hash"])
    state = ledger_state.get(digest)
    if state:
        return state
    if digest in export_hashes:
        return "PINNED_EXPORT"
    decision = str(event.get("decision") or "")
    if decision == "UNRESOLVED":
        return "DECISION_UNRESOLVED"
    rights = str(event.get("rights") or "")
    if rights != CLEARED_RIGHTS:
        return "RIGHTS_UNRESOLVED" if rights == "RIGHTS_UNRESOLVED" else "RIGHTS_NOT_CLEARED"
    if decision not in ADMISSIBLE_DECISIONS:
        return "DECISION_NOT_ADMISSIBLE"
    if not _slices(event):
        return "SLICE_LABELS_ABSENT"
    return "ELIGIBLE"


def _fence_counts(
    rows: Sequence[Mapping[str, Any]],
    fences: Mapping[str, Mapping[str, set[str]]],
) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for name, fence in fences.items():
        hashes = fence.get("hashes") or set()
        row_ids = fence.get("row_ids") or set()
        synsets = fence.get("synsets") or set()
        sources = fence.get("source_ids") or set()
        hash_hits = 0
        row_hits = 0
        synset_hits = 0
        source_hits = 0
        for row in rows:
            if str(row.get("text_hash") or "") in hashes:
                hash_hits += 1
            if str(row.get("row_id") or "") in row_ids:
                row_hits += 1
            synset = str(row.get("pwn30_synset") or "")
            if synset and synset in synsets:
                synset_hits += 1
            source = str(row.get("source_identity") or "")
            if source and source in sources:
                source_hits += 1
        counts[name] = {
            "normalized_identity": hash_hits,
            "row_id": row_hits,
            "source_identity": source_hits,
            "synset": synset_hits,
        }
    return counts


def census(
    events: Sequence[Mapping[str, Any]],
    ledger_state: Mapping[str, str],
    export_hashes: set[str],
    *,
    fences: Mapping[str, Mapping[str, set[str]]] | None = None,
    batch_id: str = BATCH_ID,
) -> dict[str, Any]:
    """Route a settlement universe twice and freeze a reserve only when it qualifies."""
    first = _once(events, ledger_state, export_hashes, fences or {}, batch_id)
    second = _once(events, ledger_state, export_hashes, fences or {}, batch_id)
    if first != second:
        failed = dict(first)
        failed["determinism"] = "NOT_DETERMINISTIC"
        failed["failure"] = "NOT_DETERMINISTIC"
        failed["reserve_rows"] = []
        failed["reserve_manifest_sha256"] = None
        return failed
    first["determinism"] = "IDENTICAL"
    return first


def _once(
    events: Sequence[Mapping[str, Any]],
    ledger_state: Mapping[str, str],
    export_hashes: set[str],
    fences: Mapping[str, Mapping[str, set[str]]],
    batch_id: str,
) -> dict[str, Any]:
    reasons: Counter[str] = Counter()
    eligible: list[dict[str, Any]] = []
    for event in events:
        reason = exclusion_reason(event, ledger_state, export_hashes)
        reasons[reason] += 1
        if reason != "ELIGIBLE":
            continue
        digest = str(event["text_hash"])
        eligible.append(
            {
                "order_key": _order_key(digest, batch_id),
                "pwn30_synset": str(event.get("pwn30_synset") or ""),
                "rights": str(event.get("rights") or ""),
                "row_id": str(event["row_id"]),
                "slices": sorted(_slices(event)),
                "source_identity": str(event.get("source_identity") or ""),
                "text_hash": digest,
            }
        )
    eligible.sort(key=lambda row: (row["order_key"], row["text_hash"], row["row_id"]))
    counts = {key: 0 for key in REQUIRED_SLICES}
    routed: list[dict[str, Any]] = []
    for row in eligible:
        served = set(row["slices"])
        if any(counts[key] < int(PLANNING_TARGETS[key]) for key in served):
            routed.append(row)
            for key in served:
                counts[key] += 1
    fence_counts = _fence_counts(routed, fences)
    isolation_hit = any(
        value
        for item in fence_counts.values()
        for value in item.values()
    )
    floors_met = all(counts[key] >= ADMISSION_FLOORS[key] for key in REQUIRED_SLICES)
    if isolation_hit:
        failure = FAILURE_ISOLATION
        frozen: list[dict[str, Any]] = []
        frozen_counts = {key: 0 for key in REQUIRED_SLICES}
    elif not floors_met:
        failure = FAILURE_QUOTA
        frozen = []
        frozen_counts = {key: 0 for key in REQUIRED_SLICES}
    else:
        failure = None
        frozen = routed
        frozen_counts = counts
    manifest = None
    if frozen:
        manifest = {
            "batch_id": batch_id,
            "experiment_id": EXPERIMENT_ID,
            "rows": [
                {
                    "rights": row["rights"],
                    "row_id": row["row_id"],
                    "slices": row["slices"],
                    "text_hash": row["text_hash"],
                }
                for row in frozen
            ],
            "schema": "hyperlex.select_reserve_manifest.v1",
        }
    return {
        "admission_floors": dict(ADMISSION_FLOORS),
        "batch_id": batch_id,
        "eligible_count": len(eligible),
        "eligible_order": [row["text_hash"] for row in eligible],
        "exclusion_counts": dict(sorted(reasons.items())),
        "experiment_id": EXPERIMENT_ID,
        "failure": failure,
        "frozen_slice_counts": frozen_counts,
        "isolation": fence_counts,
        "planning_targets": dict(PLANNING_TARGETS),
        "reserve_manifest_sha256": sha256_text(canonical_json(manifest)) if manifest else None,
        "reserve_row_count": len(frozen),
        "reserve_rows": [
            {"row_id": row["row_id"], "slices": row["slices"], "text_hash": row["text_hash"]}
            for row in frozen
        ],
        "routed_before_freeze_gate": len(routed),
        "routed_slice_counts": counts,
        "source_universe_count": len(events),
        "training_authorized": TRAINING_AUTHORIZED,
    }


def spent_reserve_hashes(records: Sequence[Mapping[str, Any]]) -> set[str]:
    """EVAL_SPENT identities that still carry ``evaluation_reserved``.

    SELECT-004's 491 identities moved to EVAL_SPENT without a new binding
    entry. The historical flag is the membership evidence. SELECT-001 and
    SELECT-002 bindings are not this set.
    """
    found: set[str] = set()
    for record in records:
        if derived_state(record) != "EVAL_SPENT" or not record.get("evaluation_reserved"):
            continue
        digest = str(record.get("normalized_text_sha256") or "")
        if digest:
            found.add(digest)
    return found


def ledger_state_index(records: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    index: dict[str, str] = {}
    for record in records:
        digest = str(record.get("normalized_text_sha256") or "")
        if digest:
            index[digest] = derived_state(record)
    return index


def unsettled_screen_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Operator-review packets are not a settlement universe."""
    counts: Counter[str] = Counter()
    for row in rows:
        if str(row.get("operator_decision") or "").strip():
            counts["OPERATOR_DECISION_PRESENT"] += 1
        else:
            counts["OPERATOR_DECISION_ABSENT"] += 1
        bucket = str(row.get("bucket") or "UNBUCKETED")
        counts[f"bucket:{bucket}"] += 1
    counts["rows"] = len(rows)
    return dict(sorted(counts.items()))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                payload = json.loads(line)
                if isinstance(payload, dict):
                    rows.append(payload)
    return rows


def _identity_fence(rows: Sequence[Mapping[str, Any]]) -> dict[str, set[str]]:
    return {
        "hashes": {str(row.get("normalized_text_sha256") or "") for row in rows if row.get("normalized_text_sha256")},
        "row_ids": {str(row.get("row_id") or "") for row in rows if row.get("row_id")},
        "source_ids": {str(row.get("source_identity") or "") for row in rows if row.get("source_identity")},
        "synsets": {str(row.get("pwn30_synset") or "") for row in rows if row.get("pwn30_synset")},
    }


def _write_private(path: Path, payload: Mapping[str, Any]) -> str:
    if "hlx-private" not in path.parts:
        raise SystemExit("REFUSE: SELECT-005 census evidence stays under hlx-private")
    text = canonical_json(payload)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return sha256_text(text)


def write_live_census(
    *,
    ledger_dir: Path,
    settlement_events: Path,
    export_path: Path,
    review_candidates: Path,
    calibration_manifest: Path,
    measurement_manifest: Path,
    calibration_v1_manifest: Path,
    destination: Path,
) -> dict[str, str]:
    """Re-census the live settlement stream and freeze the failure. No ledger append."""
    from .holdout_guard import normalized_text_sha256

    ledger_payload = json.loads(ledger_dir.joinpath("ledger.json").read_text(encoding="utf-8"))
    records = ledger_payload["identities"]
    states = ledger_state_index(records)
    state_totals: Counter[str] = Counter(states.values())
    bound_select = {
        str(record.get("normalized_text_sha256") or "")
        for record in records
        if any("SELECT" in str(item) for item in record.get("experiment_bindings") or [])
        and record.get("normalized_text_sha256")
    }
    spent_reserve = spent_reserve_hashes(records)
    export_hashes: set[str] = set()
    export_rows = 0
    for row in _read_jsonl(export_path):
        export_rows += 1
        export_hashes.add(normalized_text_sha256(str(row.get("text") or "")))
    events = _read_jsonl(settlement_events)
    fences = {
        "prior_select_reserve": {
            "hashes": set(spent_reserve),
            "row_ids": set(),
            "source_ids": set(),
            "synsets": set(),
        },
        "select_001_002_bindings": {
            "hashes": set(bound_select),
            "row_ids": set(),
            "source_ids": set(),
            "synsets": set(),
        },
        "threshold_v1_calibration": _identity_fence(_read_jsonl(calibration_v1_manifest)),
        "threshold_v2_calibration": _identity_fence(_read_jsonl(calibration_manifest)),
        "threshold_v2_measurement": _identity_fence(_read_jsonl(measurement_manifest)),
        "train_export": {
            "hashes": set(export_hashes),
            "row_ids": set(),
            "source_ids": set(),
            "synsets": set(),
        },
    }
    report = census(events, states, export_hashes, fences=fences)
    review = unsettled_screen_counts(_read_jsonl(review_candidates))
    # Novel settlements are the rows the quota would have to come from.
    novel = [
        row
        for row in events
        if str(row.get("text_hash") or "") not in states and str(row.get("text_hash") or "") not in export_hashes
    ]
    novel_fences = _fence_counts(novel, fences)
    novel_decision_rights: Counter[str] = Counter(
        f"{row.get('decision')}|{row.get('rights')}" for row in novel
    )
    body = {
        "active_reserve_identities": state_totals.get("EVAL_RESERVE", 0) + state_totals.get("AVAILABLE", 0),
        "batch_id": report["batch_id"],
        "determinism": report["determinism"],
        "eligible_count": report["eligible_count"],
        "exclusion_counts": report["exclusion_counts"],
        "experiment_id": EXPERIMENT_ID,
        "export_rows": export_rows,
        "export_unique_hashes": len(export_hashes),
        "failure": report["failure"],
        "ledger_identity_count": len(states),
        "ledger_state_counts": dict(sorted(state_totals.items())),
        "novel_decision_rights": dict(sorted(novel_decision_rights.items())),
        "novel_settlement_count": len(novel),
        "novel_settlement_fence_overlaps": novel_fences,
        "planning_targets_are_not_the_floor": True,
        "reserve_manifest_sha256": report["reserve_manifest_sha256"],
        "reserve_row_count": report["reserve_row_count"],
        "review_packet_is_not_a_settlement": review,
        "routed_before_freeze_gate": report["routed_before_freeze_gate"],
        "routed_slice_counts": report["routed_slice_counts"],
        "schema": "hyperlex.select_005_reserve_census.v1",
        "select_001_002_bound_identities": len(bound_select),
        "select_004_spent_reserve_identities": len(spent_reserve),
        "source_universe": "settlement/events.jsonl",
        "source_universe_count": report["source_universe_count"],
        "training_authorized": False,
        "transition": TRANSITION,
        "unbind_source_disposition": "WORDNET_NOT_ADMITTED_ALONE",
        "wordnet_rows_admitted": 0,
    }
    isolation = {
        "experiment_id": EXPERIMENT_ID,
        "failure": report["failure"],
        "final_reserve_overlaps": report["isolation"],
        "novel_settlement_fence_overlaps": novel_fences,
        "reserve_row_count": report["reserve_row_count"],
        "schema": "hyperlex.select_005_isolation_report.v1",
        "train_overlap_count": 0,
    }
    provenance = {
        "admitted_rows": 0,
        "experiment_id": EXPERIMENT_ID,
        "required_fields": list(REQUIRED_PROVENANCE),
        "result": "NO_ADMITTED_ROWS",
        "schema": "hyperlex.select_005_provenance_report.v1",
        "source_universe_missing_required_provenance": report["exclusion_counts"].get("PROVENANCE_INCOMPLETE", 0),
    }
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    census_hash = _write_private(destination / "RESERVE_CENSUS.json", body)
    isolation_hash = _write_private(destination / "ISOLATION_REPORT.json", isolation)
    provenance_hash = _write_private(destination / "PROVENANCE_REPORT.json", provenance)
    failure = {
        "admission_receipt_created": False,
        "admission_result": report["failure"],
        "census_sha256": census_hash,
        "decision_threshold_state": "BLOCKED_PENDING_OPERATOR_AUTHORIZATION",
        "experiment_id": EXPERIMENT_ID,
        "failure": report["failure"],
        "isolation_sha256": isolation_hash,
        "next_legal_transition": "NONE",
        "preregistration_sealed": False,
        "provenance_sha256": provenance_hash,
        "reserve_manifest_created": False,
        "schedule_sealed": False,
        "schedule_spec_sha256": schedule_spec_sha256(),
        "schema": "hyperlex.select_005_admission_failure.v1",
        "select_admission_json_schema_exists": SELECT_ADMISSION_JSON_SCHEMA_EXISTS,
        "status": report["failure"],
        "training_authorized": False,
        "training_executed": False,
        "training_launch_authorized": False,
        "transition": TRANSITION,
        "weights_mutated": False,
    }
    failure_hash = _write_private(destination / "ADMISSION_FAILURE.json", failure)
    return {
        "admission_failure_sha256": failure_hash,
        "census_sha256": census_hash,
        "isolation_sha256": isolation_hash,
        "provenance_sha256": provenance_hash,
    }
