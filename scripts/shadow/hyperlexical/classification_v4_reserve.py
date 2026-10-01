"""Classification v4 balanced-reserve seal + one-shot disposition.

Freezes the ACQUIRE_READY Wiktionary pool as the promotion reserve and scores
it once under frozen Stage A/B thresholds. Does not train, retune, reuse spent
v2/v3 reserves, or move BEST.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Mapping, Sequence

from .classification_v3_evidence_gate import (
    FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
    FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
)
from .classification_v3_reserve import (  # noqa: F401 — re-export FROZEN_THRESHOLDS
    BEST_SHA,
    FROZEN_THRESHOLDS,
    STAGE_A_CHECKPOINT_SHA,
    STAGE_B_INDEX_SHA,
    SURFACE_DATASET_SHA,
    SPENT_V2_ROWS_SHA,
    decide_v3_reserve_disposition,
)

# Re-export for spark runner imports.
__all__ = [
    "ACQUIRE_RECEIPT_SHA",
    "ACQUIRE_ROWS_SHA",
    "FROZEN_THRESHOLDS",
    "RESERVE_RULE",
    "assemble_reserve_eval_receipt",
    "decide_v4_reserve_disposition",
    "load_acquire_rows",
    "next_action_for_v4_disposition",
    "reserve_contract",
    "seal_reserve_from_acquire",
    "validate_v4_reserve_disjointness",
]
from .classification_v4_balanced_reserve_acquire import (
    ACQUIRE_RULE,
    SPENT_V3_ROWS_SHA,
    acquire_contract,
    audit_balance,
)

RESERVE_RULE = "HYPERLEX_CLASSIFICATION_V4_BALANCED_RESERVE_EVAL_V1"
ACQUIRE_ROWS_SHA = (
    "dd224047b331cd13b5a6893519907f9998620a482b0d17f29b3444b46794eb82"
)
ACQUIRE_RECEIPT_SHA = (
    "1998f409f5350bb296bd6a84e2be23411c0986177f7b4b1ca53b5b08b1bae9f5"
)


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def reserve_contract() -> dict[str, Any]:
    return {
        "acquire_receipt_sha256": ACQUIRE_RECEIPT_SHA,
        "acquire_rows_sha256": ACQUIRE_ROWS_SHA,
        "acquire_rule": ACQUIRE_RULE,
        "best": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "false_evidence_entry_rate_on_none_max": FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
        "family_emission_precision_min": FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
        "frozen_thresholds": dict(FROZEN_THRESHOLDS),
        "parent_acquire_contract": acquire_contract(),
        "recalibrate": False,
        "rule": RESERVE_RULE,
        "spent_v2_reserve_reuse": False,
        "spent_v3_reserve_reuse": False,
        "spent_v2_rows_sha256": SPENT_V2_ROWS_SHA,
        "spent_v3_rows_sha256": SPENT_V3_ROWS_SHA,
        "stage_a_checkpoint_sha256": STAGE_A_CHECKPOINT_SHA,
        "stage_b_index_sha256": STAGE_B_INDEX_SHA,
        "surface_dataset_sha256": SURFACE_DATASET_SHA,
        "train": False,
    }


def load_acquire_rows(body: str) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in body.splitlines() if line.strip()]
    for row in rows:
        if row.get("split") != "reserve_acquire":
            raise ValueError("acquire_row_split_invalid")
        if "identity" not in row or "text" not in row:
            raise ValueError("acquire_row_incomplete")
    return rows


def seal_reserve_from_acquire(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    balance = audit_balance(rows)
    if not balance.get("balance_pass"):
        raise ValueError(f"acquire_balance_regressed:{balance.get('reasons')}")
    ordered = sorted(rows, key=lambda item: str(item["identity"]))
    identities = [str(row["identity"]) for row in ordered]
    body_lines = [canonical_json(row) for row in ordered]
    body = "\n".join(body_lines) + ("\n" if body_lines else "")
    rows_sha = sha256_text(body)
    identity_list_sha = sha256_text(
        "\n".join(identities) + ("\n" if identities else "")
    )
    manifest = {
        "BEST": "UNCHANGED",
        "acquire_receipt_sha256": ACQUIRE_RECEIPT_SHA,
        "acquire_rows_sha256": ACQUIRE_ROWS_SHA,
        "acquire_rule": ACQUIRE_RULE,
        "balance": balance,
        "best_sha256": BEST_SHA,
        "evidence_label_counts": dict(
            Counter(str(row["evidence_label"]) for row in ordered)
        ),
        "identity_list_sha256": identity_list_sha,
        "lineage_counts": dict(Counter(str(row["lineage"]) for row in ordered)),
        "n": len(ordered),
        "n_none": sum(
            1 for row in ordered if row["evidence_label"] == "NO_EVIDENCE"
        ),
        "n_present": sum(
            1 for row in ordered if row["evidence_label"] == "EVIDENCE_PRESENT"
        ),
        "rows_sha256": rows_sha,
        "rule": RESERVE_RULE,
        "schema": "hyperlex.classification.v4.reserve_manifest.v1",
        "spent_v2_rows_sha256": SPENT_V2_ROWS_SHA,
        "spent_v3_rows_sha256": SPENT_V3_ROWS_SHA,
        "surface_dataset_sha256": SURFACE_DATASET_SHA,
        "train": False,
    }
    manifest["manifest_sha256"] = sha256_text(
        canonical_json({k: v for k, v in manifest.items() if k != "manifest_sha256"})
    )
    return {"body": body, "identities": identities, "manifest": manifest, "rows": ordered}


def validate_v4_reserve_disjointness(
    rows: Sequence[Mapping[str, Any]],
    *,
    surface_ids: set[str],
    spent_v2_ids: set[str],
    spent_v3_ids: set[str],
    index_ids: set[str],
) -> list[str]:
    reasons = []
    identities = [str(row["identity"]) for row in rows]
    if len(identities) != len(set(identities)):
        reasons.append("duplicate_reserve_identities")
    for label, pool in (
        ("surface_overlap", surface_ids),
        ("spent_v2_overlap", spent_v2_ids),
        ("spent_v3_overlap", spent_v3_ids),
        ("stage_b_index_overlap", index_ids),
    ):
        overlap = sorted(set(identities) & pool)
        if overlap:
            reasons.append(f"{label}:{len(overlap)}")
    if not rows:
        reasons.append("empty_reserve")
    balance = audit_balance(rows)
    if not balance.get("balance_pass"):
        reasons.extend(f"balance:{item}" for item in balance.get("reasons") or [])
    return reasons


def decide_v4_reserve_disposition(
    *,
    invalid_reasons: Sequence[str],
    metrics: Mapping[str, Any],
) -> dict[str, Any]:
    # Same product gates as v3; disposition names stay RESERVE_*.
    return decide_v3_reserve_disposition(
        invalid_reasons=invalid_reasons, metrics=metrics
    )


def next_action_for_v4_disposition(disposition: Mapping[str, Any]) -> str:
    name = disposition.get("disposition")
    if name == "RESERVE_PASS":
        return (
            "V4_BALANCED_RESERVE_PRODUCTION_CANDIDATE — selective contract "
            "generalized on the balanced acquire reserve; BEST unchanged until a "
            "separate explicit promotion authorization."
        )
    if name == "RESERVE_FAIL":
        return (
            "STOP — preserve v4 balanced reserve result; do not retune thresholds "
            "against the reserve; do not move BEST."
        )
    return (
        "RESERVE_INVALID — fix contamination/execution/provenance failure; "
        "do not treat metrics as the failure mode; do not move BEST."
    )


def assemble_reserve_eval_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    receipt = {
        "BEST": "UNCHANGED",
        "audit_state": {
            "authorization": "AUTHORIZE_SEAL_V4_BALANCED_RESERVE_THEN_ONE_SHOT_SCORE",
            "best_moved": False,
            "recalibrated": False,
            "reserve_scored_once": True,
            "thresholds_changed": False,
            "train": False,
        },
        "best_sha256": BEST_SHA,
        "contract": reserve_contract(),
        "disposition": payload["disposition"],
        "frozen_thresholds": dict(FROZEN_THRESHOLDS),
        "index_sha256": STAGE_B_INDEX_SHA,
        "metrics": payload["metrics"],
        "next_action": payload["next_action"],
        "reserve_manifest_sha256": payload["reserve_manifest_sha256"],
        "reserve_rows_sha256": payload["reserve_rows_sha256"],
        "rule": RESERVE_RULE,
        "schema": "hyperlex.classification.v4.reserve_eval.v1",
        "stage_a_checkpoint_sha256": STAGE_A_CHECKPOINT_SHA,
        "surface_dataset_sha256": SURFACE_DATASET_SHA,
        "validation_reference": payload.get("validation_reference"),
    }
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )
    return receipt
