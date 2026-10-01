"""APPLY_GOLD_IDENTIFIABILITY_FILTER — apply frozen contract filter.

Creates V1R2 as a membership-only subset of V1R1 under
HYPERLEX_STAGE_A_GOLD_IDENTIFIABILITY_CONTRACT_V1.

Does not train, auto-relabel, mutate V1R1, expand model inputs, alter
Stage B, score spent reserve, or move BEST.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import canonical_json, sha256_text
from .classification_v5_stage_a_factorized_objective import (
    FACTORIZED_ANNOTATION_SHA256_PIN,
    OBJECTIVE_ID,
    OBJECTIVE_RECEIPT_SHA256_PIN,
    derive_factorized_annotation,
    relation_loss_eligible,
    resolvability_loss_eligible,
)
from .classification_v5_stage_a_gold_identifiability_contract import (
    CONTRACT_ID,
    DIAGNOSIS_RECEIPT_SHA256,
    MODEL_INPUT,
    MODEL_WIDE_BEST_SHA256,
    PRIMARY_DIAGNOSIS_PIN,
    classify_row,
    classify_repaired_viability,
)
from .classification_v5_stage_a_two_stage_generalization import (
    AUTHORIZED_DATASET_SHA,
    PARENT_STAGE_A_BEST_SHA,
    SPENT_RESERVE,
    SPENT_RESERVE_OVERLAP,
    SPENT_RESERVE_STATUS,
)

FILTER_RULE = "APPLY_GOLD_IDENTIFIABILITY_FILTER"
FILTER_ID = "HYPERLEX_V5_STAGE_A_GOLD_IDENTIFIABILITY_FILTER_V1"
SURFACE_ID = "HYPERLEX_V5_STAGE_A_IDENTIFIABILITY_FILTERED_SURFACE_V1R2"
DATASET_VERSION = "V1R2"
PARENT_DATASET_VERSION = "V1R1"
PARENT_DATASET_SHA256 = AUTHORIZED_DATASET_SHA
CONTRACT_RECEIPT_SHA256_PIN = (
    "4ce0e5faccef3772bbefdfc42f878446602ffa59f4d7ae9933652b687a41e3e4"
)

TRAIN_AUTHORIZED = False
AUTO_RELABEL = False
V1R1_MUTATED = False
ARCHITECTURE_CHANGE_JUSTIFIED = False
INPUT_CONTRACT_EXPANSION_JUSTIFIED = False

KEEP_DISPOSITIONS = frozenset(
    {
        "KEEP_GOLD",
        "KEEP_FOR_RESOLVABILITY_ONLY",
        "KEEP_GOLD_BUT_MASK_RELATION",
    }
)
EXCLUDE_DISPOSITIONS = frozenset(
    {
        "EXCLUDE_FROM_TEXT_ONLY_STAGE_A",
        "REQUIRES_HUMAN_RESETTLEMENT",
    }
)

# Expected from sealed contract audit (planning witness).
EXPECTED_V1R1_N = 3585
EXPECTED_KEEP_N = 3120
EXPECTED_EXCLUDE_N = 465
EXPECTED_RELATION_ELIGIBLE = 3066
EXPECTED_PRESENT = 1215
EXPECTED_NONE = 1851
EXPECTED_UNCERTAIN = 54

NEXT_ACTION = "AUTHORIZE_STAGE_A_IDENT_FILTERED_FACTORIZED_TRAIN"


def row_sha256(row: Mapping[str, Any]) -> str:
    return sha256_text(canonical_json(row))


def apply_filter_to_rows(
    rows: Sequence[Mapping[str, Any]],
    annotations_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Partition V1R1 rows by contract disposition; copy kept rows unchanged."""
    if len(rows) != EXPECTED_V1R1_N:
        raise ValueError(f"v1r1_count_mismatch:{len(rows)}")

    classifications: list[dict[str, Any]] = []
    kept_rows: list[dict[str, Any]] = []
    kept_anns: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for row in rows:
        identity = str(row["identity"])
        ann = annotations_by_id.get(identity)
        if ann is None:
            raise ValueError(f"missing_annotation:{identity}")
        classified = classify_row(row, ann)
        classifications.append(classified)
        disp = classified["recommended_disposition"]
        if disp in KEEP_DISPOSITIONS:
            # Membership filter only — no gold/text mutation.
            kept_rows.append(dict(row))
            kept_anns.append(dict(ann))
        elif disp in EXCLUDE_DISPOSITIONS:
            excluded.append(
                {
                    "identity": identity,
                    "recommended_disposition": disp,
                    "identifiability_state": classified["identifiability_state"],
                    "current_final_gold": classified["current_final_gold"],
                    "current_subtype": classified["current_subtype"],
                    "cell_family": classified["cell_family"],
                    "identifiability_reason": classified["identifiability_reason"],
                    "split": classified["split"],
                }
            )
        else:
            raise ValueError(f"unknown_disposition:{disp}:{identity}")

    if len(kept_rows) != EXPECTED_KEEP_N:
        raise ValueError(
            f"keep_count_mismatch:{len(kept_rows)}!={EXPECTED_KEEP_N}"
        )
    if len(excluded) != EXPECTED_EXCLUDE_N:
        raise ValueError(
            f"exclude_count_mismatch:{len(excluded)}!={EXPECTED_EXCLUDE_N}"
        )

    # Verify no auto-relabel: kept rows identical to parent identities' gold.
    parent_by_id = {str(r["identity"]): r for r in rows}
    for kr in kept_rows:
        parent = parent_by_id[str(kr["identity"])]
        if kr["evidence_label"] != parent["evidence_label"]:
            raise ValueError(f"auto_relabel_detected:{kr['identity']}")
        if kr["text"] != parent["text"]:
            raise ValueError(f"text_mutation_detected:{kr['identity']}")
        if kr["evidence_subtype"] != parent["evidence_subtype"]:
            raise ValueError(f"subtype_mutation_detected:{kr['identity']}")

    # Re-pin factorized annotations by re-derive (must match copied ann sha).
    for row, ann in zip(kept_rows, kept_anns):
        derived = derive_factorized_annotation(row)
        if derived["annotation_sha256"] != ann["annotation_sha256"]:
            raise ValueError(
                f"annotation_drift:{row['identity']}:"
                f"{derived['annotation_sha256'][:12]}!="
                f"{ann['annotation_sha256'][:12]}"
            )

    gold_counts = Counter(r["evidence_label"] for r in kept_rows)
    split_counts = Counter(r["split"] for r in kept_rows)
    subtype_counts = Counter(r["evidence_subtype"] for r in kept_rows)
    cell_counts = Counter(str(r.get("primary_cell") or "NONE") for r in kept_rows)
    disp_counts = Counter(c["recommended_disposition"] for c in classifications)

    rel_eligible = sum(1 for a in kept_anns if relation_loss_eligible(a))
    res_eligible = sum(1 for a in kept_anns if resolvability_loss_eligible(a))
    if rel_eligible != EXPECTED_RELATION_ELIGIBLE:
        raise ValueError(
            f"relation_eligible_mismatch:{rel_eligible}!={EXPECTED_RELATION_ELIGIBLE}"
        )
    if gold_counts.get("EVIDENCE_PRESENT") != EXPECTED_PRESENT:
        raise ValueError("present_count_mismatch")
    if gold_counts.get("NO_EVIDENCE") != EXPECTED_NONE:
        raise ValueError("none_count_mismatch")
    if gold_counts.get("UNCERTAIN") != EXPECTED_UNCERTAIN:
        raise ValueError("uncertain_count_mismatch")

    sa_present = sum(
        1
        for r in kept_rows
        if str(r.get("primary_cell") or "").startswith("SHORT_ATOM/")
        and r["evidence_label"] == "EVIDENCE_PRESENT"
    )
    sa_none = sum(
        1
        for r in kept_rows
        if str(r.get("primary_cell") or "").startswith("SHORT_ATOM/")
        and r["evidence_label"] == "NO_EVIDENCE"
    )

    balance = {
        "relation_positive": int(gold_counts["EVIDENCE_PRESENT"]),
        "relation_negative": int(gold_counts["NO_EVIDENCE"]),
        "resolvability_positive": rel_eligible,
        "resolvability_negative": int(gold_counts["UNCERTAIN"]),
        "minimum_cell_support": min(
            int(gold_counts["EVIDENCE_PRESENT"]),
            int(gold_counts["NO_EVIDENCE"]),
            rel_eligible,
            max(int(gold_counts["UNCERTAIN"]), 0),
        ),
    }
    viability = classify_repaired_viability(balance)

    return {
        "classifications": classifications,
        "kept_rows": kept_rows,
        "kept_annotations": kept_anns,
        "excluded": excluded,
        "counts": {
            "parent_v1r1": len(rows),
            "kept": len(kept_rows),
            "excluded": len(excluded),
            "by_label": dict(gold_counts),
            "by_split": dict(split_counts),
            "by_subtype": dict(subtype_counts),
            "by_primary_cell": dict(cell_counts),
            "by_disposition": dict(disp_counts),
            "relation_loss_eligible": rel_eligible,
            "resolvability_loss_eligible": res_eligible,
            "SHORT_ATOM_PRESENT": sa_present,
            "SHORT_ATOM_NONE": sa_none,
        },
        "balance": balance,
        "viability": viability,
        "AUTO_RELABEL": AUTO_RELABEL,
        "V1R1_MUTATED": V1R1_MUTATED,
    }


def sha256_jsonl_rows(rows: Sequence[Mapping[str, Any]]) -> str:
    """Canonical content hash of JSONL rows (one object per line, sorted keys)."""
    lines = [canonical_json(row) for row in rows]
    # canonical_json already produces compact JSON; join with newlines.
    body = "\n".join(lines) + ("\n" if lines else "")
    return sha256_text(body)


def assemble_filter_receipt(
    *,
    dataset_sha256: str,
    annotation_sha256: str,
    exclusion_manifest_sha256: str,
    filter_result: Mapping[str, Any],
    artifact_hashes: Mapping[str, str],
) -> dict[str, Any]:
    counts = filter_result["counts"]
    receipt = {
        "FILTER_RULE": FILTER_RULE,
        "FILTER_ID": FILTER_ID,
        "SURFACE_ID": SURFACE_ID,
        "DATASET_VERSION": DATASET_VERSION,
        "PARENT_DATASET_VERSION": PARENT_DATASET_VERSION,
        "PARENT_DATASET_SHA256": PARENT_DATASET_SHA256,
        "CONTRACT_ID": CONTRACT_ID,
        "CONTRACT_RECEIPT_SHA256": CONTRACT_RECEIPT_SHA256_PIN,
        "DIAGNOSIS_RECEIPT_SHA256": DIAGNOSIS_RECEIPT_SHA256,
        "PRIMARY_DIAGNOSIS_PIN": PRIMARY_DIAGNOSIS_PIN,
        "OBJECTIVE_ID": OBJECTIVE_ID,
        "OBJECTIVE_RECEIPT_SHA256": OBJECTIVE_RECEIPT_SHA256_PIN,
        "PARENT_FACTORIZED_ANNOTATION_SHA256": FACTORIZED_ANNOTATION_SHA256_PIN,
        "MODEL_INPUT": list(MODEL_INPUT),
        "PRIMARY_REPAIR_APPLIED": "FILTER_CONTEXT_DEPENDENT_GOLD",
        "DATASET_SHA256": dataset_sha256,
        "FACTORIZED_ANNOTATION_SHA256": annotation_sha256,
        "EXCLUSION_MANIFEST_SHA256": exclusion_manifest_sha256,
        "counts": counts,
        "balance": filter_result["balance"],
        "viability": filter_result["viability"],
        "TRAIN_AUTHORIZED": TRAIN_AUTHORIZED,
        "AUTO_RELABEL": AUTO_RELABEL,
        "V1R1_MUTATED": V1R1_MUTATED,
        "V1R2_CREATED": True,
        "ARCHITECTURE_CHANGE_JUSTIFIED": ARCHITECTURE_CHANGE_JUSTIFIED,
        "INPUT_CONTRACT_EXPANSION_JUSTIFIED": INPUT_CONTRACT_EXPANSION_JUSTIFIED,
        "STAGE_A_BEST": PARENT_STAGE_A_BEST_SHA,
        "STAGE_A_BEST_MUTATED": False,
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "SPENT_RESERVE": SPENT_RESERVE,
        "SPENT_RESERVE_OVERLAP": SPENT_RESERVE_OVERLAP,
        "SPENT_RESERVE_STATUS": SPENT_RESERVE_STATUS,
        "STAGE_B_MUTATED": False,
        "THRESHOLDS_MUTATED": False,
        "TRAIN": False,
        "artifact_hashes": dict(artifact_hashes),
        "NEXT_ACTION": NEXT_ACTION,
        "NEXT_ACTION_AUTHORIZED": False,
        "schema": "hyperlex.classification.v5.stage_a_gold_identifiability_filter.v1",
    }
    receipt["receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    )
    return receipt
