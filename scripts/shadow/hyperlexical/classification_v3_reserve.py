"""Fresh Classification v3 reserve seal + disposition contracts.

Seals a new reserve from AVAILABLE ledger identities that are disjoint from the
v3 evidence surface and the spent v2 classify reserve. Does not retune
thresholds, does not reuse the spent v2 reserve, and does not move BEST.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Mapping, Sequence

from .classification_v2 import ACTIVE_FAMILY_VOCABULARY
from .classification_v3_evidence_gate import (
    FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
    FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
    RULE,
)
from .classification_v3_evidence_surface import SURFACE_RULE
from .classification_v3_stage_a import STAGE_A_RULE
from .classification_v3_stage_b import STAGE_B_RULE
from .holdout_guard import normalized_text_sha256

RESERVE_RULE = "HYPERLEX_CLASSIFICATION_V3_RESERVE_EVAL_V1"
FROZEN_THRESHOLDS = {
    "minimum_family_score": 0.96,
    "minimum_top1_top2_margin": 0.01,
    "none_threshold": 0.05,
    "present_threshold": 0.55,
}
STAGE_A_CHECKPOINT_SHA = (
    "0b7dbdac1f39e7b7ede1e51e86b9b938aa68e95692bf4b2f062329d487420ce7"
)
STAGE_B_INDEX_SHA = (
    "42ae85f3ee4e7f13656d2415a2152b11d5c2b14811b20b9c6352a3bb85c40285"
)
SURFACE_DATASET_SHA = (
    "7339c044596a4cc2eb5ae17f3fbab185fface9abffb6151bdb0db69eca0d2d3a"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
SPENT_V2_ROWS_SHA = (
    "8c5276442ce37cf99fff597653a28917b3b4dc69ac87ad01f815fa458416ed36"
)


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def reserve_contract() -> dict[str, Any]:
    return {
        "best": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "false_evidence_entry_rate_on_none_max": FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX,
        "family_emission_precision_min": FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE,
        "frozen_thresholds": dict(FROZEN_THRESHOLDS),
        "parent_rule": RULE,
        "recalibrate": False,
        "rule": RESERVE_RULE,
        "spent_v2_reserve_reuse": False,
        "stage_a_rule": STAGE_A_RULE,
        "stage_b_rule": STAGE_B_RULE,
        "surface_rule": SURFACE_RULE,
        "train": False,
    }


def gold_from_lineage(lineage: str) -> dict[str, Any]:
    if lineage in ACTIVE_FAMILY_VOCABULARY:
        return {
            "evidence_label": "EVIDENCE_PRESENT",
            "evidence_subtype": "POSITIVE_EVIDENCE",
            "gold_decision_type": "FAMILY",
            "gold_family": lineage,
            "candidate_families": [lineage],
        }
    if lineage == "none":
        return {
            "evidence_label": "NO_EVIDENCE",
            "evidence_subtype": "GENERIC_NONE",
            "gold_decision_type": "NONE",
            "gold_family": None,
            "candidate_families": [],
        }
    raise ValueError(f"lineage_not_admissible_for_v3_reserve:{lineage}")


def build_reserve_row(source: Mapping[str, Any]) -> dict[str, Any]:
    text = str(source["text"])
    identity = normalized_text_sha256(text)
    lineage = str(source["lineage"])
    gold = gold_from_lineage(lineage)
    return {
        "candidate_families": gold["candidate_families"],
        "class": source["class"],
        "evidence_label": gold["evidence_label"],
        "evidence_subtype": gold["evidence_subtype"],
        "gold_decision_type": gold["gold_decision_type"],
        "gold_family": gold["gold_family"],
        "identity": identity,
        "lineage": lineage,
        "normalized_text_sha256": identity,
        "provenance": source["class"],
        "source_sha256": sha256_text(text),
        "split": "reserve",
        "text": text,
    }


def collect_available_reserve_rows(
    *,
    ledger: Mapping[str, Any],
    hub_rows: Sequence[Mapping[str, Any]],
    surface_ids: set[str],
    spent_v2_ids: set[str],
) -> dict[str, Any]:
    available = {
        record["normalized_text_sha256"]
        for record in ledger.get("identities") or []
        if record.get("state") == "AVAILABLE"
    }
    chosen: dict[str, dict[str, Any]] = {}
    rejected = Counter()
    for row in hub_rows:
        if row.get("task") not in {"classify", "classify+unbind"}:
            continue
        if row.get("class") not in {"OBSERVED", "INFERRED"}:
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        identity = normalized_text_sha256(text)
        if identity not in available:
            rejected["not_available"] += 1
            continue
        if identity in spent_v2_ids:
            rejected["spent_v2"] += 1
            continue
        if identity in surface_ids:
            rejected["surface_overlap"] += 1
            continue
        lineage = row.get("lineage")
        try:
            built = build_reserve_row(
                {"text": text, "lineage": lineage, "class": row["class"]}
            )
        except ValueError:
            rejected["lineage_inadmissible"] += 1
            continue
        previous = chosen.get(identity)
        if previous is None or (
            previous["provenance"] == "INFERRED" and built["provenance"] == "OBSERVED"
        ):
            chosen[identity] = built
    rows = sorted(chosen.values(), key=lambda item: item["identity"])
    return {
        "n": len(rows),
        "rejected": dict(rejected),
        "rows": rows,
        "lineage_counts": dict(Counter(row["lineage"] for row in rows)),
        "evidence_label_counts": dict(
            Counter(row["evidence_label"] for row in rows)
        ),
    }


def seal_reserve_manifest(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    identities = sorted(row["identity"] for row in rows)
    body_lines = [canonical_json(row) for row in rows]
    body = "\n".join(body_lines) + ("\n" if body_lines else "")
    rows_sha = sha256_text(body)
    identity_list_sha = sha256_text("\n".join(identities) + ("\n" if identities else ""))
    manifest = {
        "BEST": "UNCHANGED",
        "best_sha256": BEST_SHA,
        "evidence_label_counts": dict(
            Counter(row["evidence_label"] for row in rows)
        ),
        "identity_list_sha256": identity_list_sha,
        "lineage_counts": dict(Counter(row["lineage"] for row in rows)),
        "n": len(rows),
        "n_none": sum(1 for row in rows if row["evidence_label"] == "NO_EVIDENCE"),
        "n_present": sum(
            1 for row in rows if row["evidence_label"] == "EVIDENCE_PRESENT"
        ),
        "rows_sha256": rows_sha,
        "rule": RESERVE_RULE,
        "schema": "hyperlex.classification.v3.reserve_manifest.v1",
        "spent_v2_rows_sha256": SPENT_V2_ROWS_SHA,
        "surface_dataset_sha256": SURFACE_DATASET_SHA,
        "surface_rule": SURFACE_RULE,
        "train": False,
    }
    manifest["manifest_sha256"] = sha256_text(
        canonical_json({k: v for k, v in manifest.items() if k != "manifest_sha256"})
    )
    return {"body": body, "identities": identities, "manifest": manifest}


def validate_reserve_disjointness(
    rows: Sequence[Mapping[str, Any]],
    *,
    surface_ids: set[str],
    spent_v2_ids: set[str],
    index_ids: set[str],
) -> list[str]:
    reasons = []
    identities = [row["identity"] for row in rows]
    if len(identities) != len(set(identities)):
        reasons.append("duplicate_reserve_identities")
    overlap_surface = sorted(set(identities) & surface_ids)
    overlap_spent = sorted(set(identities) & spent_v2_ids)
    overlap_index = sorted(set(identities) & index_ids)
    if overlap_surface:
        reasons.append(f"surface_overlap:{len(overlap_surface)}")
    if overlap_spent:
        reasons.append(f"spent_v2_overlap:{len(overlap_spent)}")
    if overlap_index:
        reasons.append(f"stage_b_index_overlap:{len(overlap_index)}")
    if not rows:
        reasons.append("empty_reserve")
    return reasons


def decide_v3_reserve_disposition(
    *,
    invalid_reasons: Sequence[str],
    metrics: Mapping[str, Any],
) -> dict[str, Any]:
    if invalid_reasons:
        return {
            "disposition": "RESERVE_INVALID",
            "primary_gate_pass": False,
            "secondary_gate_pass": False,
            "reasons": list(invalid_reasons),
            "production_promotion_recommended": False,
        }
    primary = bool(metrics.get("primary_gate_pass"))
    secondary = bool(metrics.get("secondary_gate_pass"))
    if primary and secondary:
        return {
            "disposition": "RESERVE_PASS",
            "primary_gate_pass": True,
            "secondary_gate_pass": True,
            "production_promotion_recommended": True,
            "reasons": [
                "false_evidence_entry_rate_on_none_met",
                "family_emission_precision_met",
            ],
            "false_evidence_entry_rate_on_none": metrics.get(
                "false_evidence_entry_rate_on_none"
            ),
            "family_emission_precision": metrics.get("family_emission_precision"),
        }
    reasons = []
    if not primary:
        reasons.append(
            "false_evidence_entry_rate_on_none="
            f"{metrics.get('false_evidence_entry_rate_on_none')} "
            f"> max={FALSE_EVIDENCE_ENTRY_RATE_ON_NONE_MAX}"
        )
    if not secondary:
        reasons.append(
            "family_emission_precision="
            f"{metrics.get('family_emission_precision')} "
            f"< min={FAMILY_EMISSION_PRECISION_MIN_AFTER_GATE}"
        )
    return {
        "disposition": "RESERVE_FAIL",
        "primary_gate_pass": primary,
        "secondary_gate_pass": secondary,
        "production_promotion_recommended": False,
        "reasons": reasons,
        "false_evidence_entry_rate_on_none": metrics.get(
            "false_evidence_entry_rate_on_none"
        ),
        "family_emission_precision": metrics.get("family_emission_precision"),
    }


def next_action_for_v3_disposition(disposition: Mapping[str, Any]) -> str:
    name = disposition.get("disposition")
    if name == "RESERVE_PASS":
        return (
            "V3_EVIDENCE_GATE_PRODUCTION_CANDIDATE — selective contract generalized; "
            "BEST unchanged until a separate explicit promotion authorization."
        )
    if name == "RESERVE_FAIL":
        return (
            "STOP — preserve v3 reserve result; do not retune thresholds against the "
            "reserve; do not move BEST."
        )
    return (
        "RESERVE_INVALID — fix contamination/execution/provenance failure; "
        "do not treat metrics as the failure mode; do not move BEST."
    )


def assemble_reserve_eval_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    receipt = {
        "BEST": "UNCHANGED",
        "audit_state": {
            "authorization": "AUTHORIZE_SEAL_NEW_V3_RESERVE_THEN_ONE_SHOT_SCORE",
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
        "schema": "hyperlex.classification.v3.reserve_eval.v1",
        "stage_a_checkpoint_sha256": STAGE_A_CHECKPOINT_SHA,
        "surface_dataset_sha256": SURFACE_DATASET_SHA,
        "validation_reference": payload.get("validation_reference"),
    }
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )
    return receipt
