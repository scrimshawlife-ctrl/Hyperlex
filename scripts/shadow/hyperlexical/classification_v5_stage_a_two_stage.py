"""HYPERLEX_V5_STAGE_A_TWO_STAGE_DECISION_GRAPH_V1 — frozen redesign spec.

Architectural factorization of Stage-A canonical decisions into two binary
gates. Spec/runtime contract only in this module: does not train, does not
mutate V1R9, BEST, or reserve.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .classification_v5_stage_a import (
    ACCEPTANCE_GATES,
    BEST_SHA,
    CLASS_WEIGHT_POLICY,
    EVIDENCE_LABELS,
    LABEL_PROVENANCE_RULE,
    PROVENANCE_LOSS_MULTIPLIERS,
    TRAIN_HYPERPARAMS,
    canonical_json,
    evaluate_decisions,
    false_evidence_entry_rate_on_none,
    prf,
    sha256_text,
    stage_a_macro_f1,
)
from .classification_v5_stage_a_architecture_investigate import (
    DATASET_SHA as V1R9_DATASET_SHA,
    SELECTED_SHA as PARENT_FLAT_SELECTED_SHA,
    SURFACE_RULE as V1R9_SURFACE_RULE,
)
from .classification_v5_stage_a_gold_label_mapping import RULE_ID as GOLD_LABEL_RULE

TWO_STAGE_RULE = "HYPERLEX_V5_STAGE_A_TWO_STAGE_DECISION_GRAPH_V1"
AUTHORIZE_RULE = "AUTHORIZE_V5_STAGE_A_TWO_STAGE_TRAIN_V1"
TRAIN_RULE = "HYPERLEX_V5_STAGE_A_TWO_STAGE_TRAIN_V1"
TRAIN_ONCE_ACTION = "TRAIN_V5_STAGE_A_TWO_STAGE_ONCE"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-001"
# Historical design-freeze experiment id retained for receipt cross-ref only.
DESIGN_EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-STAGE-A-005-TWO-STAGE"
PARENT_EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-STAGE-A-004"
PARENT_PRIMARY_DECISION = "STAGE_A_ARCHITECTURE_REDESIGN_REQUIRED"
FLAT_HEAD_STATUS = "DEPRECATED_FOR_V5_STAGE_A_CANONICAL_DECISION"
FLAT_RUNTIME_STATUS = "DEPRECATED_FOR_CANONICAL_STAGE_A"
ARCHITECTURE_RECEIPT_SHA256 = (
    "631427cc4c1b09bac1e3a2c5e081c7e9fc0947babda26c03cb73895f47754697"
)
CLASS_WEIGHT_RESOLUTION_RULE = "RESOLVE_V5_TWO_STAGE_CLASS_WEIGHTS"
CLASS_WEIGHT_FORMULA_VERSION = "HYPERLEX_V5_TWO_STAGE_CLASS_WEIGHTS_V1"

AUTHORIZED_DATASET_SHA = V1R9_DATASET_SHA
AUTHORIZED_SURFACE_RULE = V1R9_SURFACE_RULE
AUTHORIZED_BEST_SHA = BEST_SHA
PARENT_FLAT_SELECTED_CHECKPOINT_SHA = PARENT_FLAT_SELECTED_SHA

SCHEMA_CONFIG = "hyperlex.classification.v5.stage_a_two_stage_config.v1"
SCHEMA_AUTHORIZATION = "hyperlex.classification.v5.stage_a_two_stage_authorization.v1"
SCHEMA_TRAIN_RECEIPT = "hyperlex.classification.v5.stage_a_two_stage_train_receipt.v1"
SCHEMA_FORWARD = "hyperlex.classification.v5.stage_a_two_stage_forward.v1"
SCHEMA_CLASS_WEIGHTS = "hyperlex.classification.v5.stage_a_two_stage_class_weights.v1"
# Promoted canonical Stage-A forward schema (post STAGE_A_BEST promotion).
CANONICAL_FORWARD_SCHEMA = SCHEMA_FORWARD

# Canonical semantic outputs (unchanged).
CANONICAL_LABELS = EVIDENCE_LABELS

# Gate-1 binary labels (index == logit position).
GATE1_LABELS = ("NO_EVIDENCE", "POSSIBLE_EVIDENCE")
GATE1_INDEX = {label: index for index, label in enumerate(GATE1_LABELS)}
GATE1_INDEX_LABEL = {index: label for label, index in GATE1_INDEX.items()}

# Gate-2 binary labels (index == logit position).
GATE2_LABELS = ("UNCERTAIN", "CONFIRMED_PRESENT")
GATE2_INDEX = {label: index for index, label in enumerate(GATE2_LABELS)}
GATE2_INDEX_LABEL = {index: label for label, index in GATE2_INDEX.items()}

LAMBDA_GATE2 = 1.0
LAST_TRAINABLE_ENCODER_LAYERS = int(TRAIN_HYPERPARAMS["last_trainable"])
POOLING = str(TRAIN_HYPERPARAMS["pooling"])
HEAD_INIT = str(TRAIN_HYPERPARAMS["head_init"])
LOSS_NAME = "binary_weighted_cross_entropy"
FOCAL_FORBIDDEN = True

GATE1_THRESHOLDS = [round(0.50 + 0.05 * i, 2) for i in range(10)]
GATE2_PRESENT_THRESHOLDS = [round(0.50 + 0.05 * i, 2) for i in range(10)]

CHECKPOINT_SELECTION = {
    "formula": "0.50 * Gate1_macro_F1 + 0.50 * Gate2_macro_F1",
    "gate2_scope": "PRESENT_AND_UNCERTAIN_GOLD_ONLY",
    "strict_improvement": True,
    "tie_break": [
        "lower_gate1_false_possible_entry_rate",
        "higher_gate2_CONFIRMED_PRESENT_recall",
        "earlier_epoch",
    ],
}

THRESHOLD_SELECTION = {
    "acceptance_required": [
        "false_evidence_entry_rate_on_none <= 0.05",
        "EVIDENCE_PRESENT_recall >= 0.70",
        "NO_EVIDENCE_recall >= 0.90",
    ],
    "maximize_in_order": [
        "stage_a_macro_f1",
        "EVIDENCE_PRESENT_recall",
        "UNCERTAIN_recall",
        "minimize_false_evidence_entry",
        "higher_gate1_threshold",
        "higher_gate2_present_threshold",
    ],
    "fail_if_no_feasible": "SETTLED_FAIL",
    "n_grid_combinations": 100,
}

NO_DATA = "NO_DATA"
NOT_COMPUTABLE = "NOT_COMPUTABLE"
LABEL_MAPPING_INVALID = "LABEL_MAPPING_INVALID"

DATASET_SPLIT_RULE = "HYPERLEX_V5_STAGE_A_TWO_STAGE_DATASET_SPLIT_V1"
SCHEMA_SPLIT_WITNESS = "hyperlex.classification.v5.stage_a_two_stage_split_witness.v1"

# Frozen V1R9 split identity pins (authoritative; do not regenerate splits).
EXPECTED_TRAIN_ROWS = 4437
EXPECTED_VALIDATION_ROWS = 2051
EXPECTED_GATE1_NO_ROWS = 3554
EXPECTED_GATE1_POSSIBLE_ROWS = 883
EXPECTED_GATE2_UNCERTAIN_ROWS = 280
EXPECTED_GATE2_PRESENT_ROWS = 603
EXPECTED_GATE2_ELIGIBLE_ROWS = 883
EXPECTED_TRAIN_SPLIT_SHA256 = (
    "cee13cbe7412755444a1cd8d831f85ce0607a6e8266fba0e882a4578f3b6db4c"
)
EXPECTED_VALIDATION_SPLIT_SHA256 = (
    "8d56b8c7e72a2fae0582082e9517c29cfa7812ef75cc4f45705c284aefed2678"
)
EXPECTED_TRAIN_IDENTITY_LIST_SHA256 = (
    "c1b22bdfcac3dc3445e2c2f1a8621bea8d44a0e4ce210d07a480a93d7d8ea21f"
)
EXPECTED_VALIDATION_IDENTITY_LIST_SHA256 = (
    "3a24d55056aad96dade8b46da714096472b5f16fc1bd63f2701d87e9adf58c55"
)
EXPECTED_GATE2_ELIGIBLE_IDENTITY_SHA256 = (
    "79bbe523aafdf99d96f92ead776fb41661a932113578033f0f0bd7475d839171"
)

AUTHORIZED_CLASS_WEIGHT_ARTIFACT_SHA256 = (
    "5496015af99ec768d8914a282db465abe75e99f2243fbc864d674bb5cad539d6"
)
AUTHORIZED_TRAINING_CONFIG_SHA256 = (
    "0117faca8e56501e15cea4f69ce9dffd2900b25cfdc7dcabc427651b18d7b0b6"
)
AUTHORIZED_AUTH_RECEIPT_SHA256 = (
    "c9b262de5e3a33abfd52e29cc92715d7809d9470a205226d93d538cd952f0b57"
)
LITERAL_GATE1_WEIGHTS = {
    "NO_EVIDENCE": 0.7182189774877286,
    "POSSIBLE_EVIDENCE": 1.2817810225122714,
}
LITERAL_GATE2_WEIGHTS = {
    "UNCERTAIN": 1.1124229052629504,
    "CONFIRMED_PRESENT": 0.8875770947370494,
}

DROP_LAST = False
SAMPLER = "deterministic_shuffled_full_pass"
REPLACEMENT = False
OVERSAMPLING = False
UNDERSAMPLING = False
CLASS_BALANCED_SAMPLER = False


def identity_list_sha256(identities: Sequence[str]) -> str:
    ordered = sorted(str(identity) for identity in identities)
    return sha256_text("\n".join(ordered) + ("\n" if ordered else ""))


def split_lines_sha256(dataset_path: str, *, split: str) -> str:
    """SHA256 over raw jsonl lines for one split (file order)."""
    import hashlib
    from pathlib import Path

    digest = hashlib.sha256()
    with Path(dataset_path).open("rb") as handle:
        for line in handle:
            if not line.strip():
                continue
            import json

            row = json.loads(line)
            if row.get("split") == split:
                digest.update(line if line.endswith(b"\n") else line + b"\n")
    return digest.hexdigest()


def full_pass_batch_indices(
    n_rows: int,
    *,
    batch_size: int,
    seed: int,
    drop_last: bool = DROP_LAST,
) -> list[list[int]]:
    """Deterministic shuffled full-pass batches; no class rebalancing."""
    import random

    if n_rows <= 0:
        raise ValueError("NO_DATA:empty_train_for_batching")
    if batch_size <= 0:
        raise ValueError("invalid_batch_size")
    order = list(range(n_rows))
    random.Random(int(seed)).shuffle(order)
    batches: list[list[int]] = []
    for start in range(0, n_rows, batch_size):
        chunk = order[start : start + batch_size]
        if drop_last and len(chunk) < batch_size:
            break
        batches.append(chunk)
    return batches


def build_two_stage_split_witness(
    rows: Sequence[Mapping[str, Any]],
    *,
    dataset_sha256: str,
    dataset_path: str,
    code_revision: str,
    disjointness: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Emit HYPERLEX_V5_STAGE_A_TWO_STAGE_DATASET_SPLIT_V1 witness."""
    if dataset_sha256 != AUTHORIZED_DATASET_SHA:
        raise ValueError("INPUT_IDENTITY:dataset_mismatch")
    train_rows = [row for row in rows if row.get("split") == "train"]
    val_rows = [row for row in rows if row.get("split") == "validation"]
    if len(train_rows) != EXPECTED_TRAIN_ROWS:
        raise ValueError(f"INPUT_IDENTITY:train_rows!={EXPECTED_TRAIN_ROWS}")
    if len(val_rows) != EXPECTED_VALIDATION_ROWS:
        raise ValueError(f"INPUT_IDENTITY:val_rows!={EXPECTED_VALIDATION_ROWS}")

    train_ids = [str(row["identity"]) for row in train_rows]
    val_ids = [str(row["identity"]) for row in val_rows]
    train_id_sha = identity_list_sha256(train_ids)
    val_id_sha = identity_list_sha256(val_ids)
    train_split_sha = split_lines_sha256(dataset_path, split="train")
    val_split_sha = split_lines_sha256(dataset_path, split="validation")

    g1_no = [row for row in train_rows if str(row["evidence_label"]) == "NO_EVIDENCE"]
    g1_possible = [
        row
        for row in train_rows
        if str(row["evidence_label"]) in {"EVIDENCE_PRESENT", "UNCERTAIN"}
    ]
    g2_uncertain = [
        row for row in train_rows if str(row["evidence_label"]) == "UNCERTAIN"
    ]
    g2_present = [
        row for row in train_rows if str(row["evidence_label"]) == "EVIDENCE_PRESENT"
    ]
    g2_eligible_ids = sorted(str(row["identity"]) for row in g1_possible)
    g1_possible_ids = sorted(str(row["identity"]) for row in g1_possible)
    if g2_eligible_ids != g1_possible_ids:
        raise ValueError("INPUT_IDENTITY:gate2_eligible_ne_gate1_possible")
    gate2_elig_sha = identity_list_sha256(g2_eligible_ids)

    if len(g1_no) != EXPECTED_GATE1_NO_ROWS:
        raise ValueError("INPUT_IDENTITY:gate1_no_rows")
    if len(g1_possible) != EXPECTED_GATE1_POSSIBLE_ROWS:
        raise ValueError("INPUT_IDENTITY:gate1_possible_rows")
    if len(g1_no) + len(g1_possible) != EXPECTED_TRAIN_ROWS:
        raise ValueError("INPUT_IDENTITY:gate1_cover")
    if len(g2_uncertain) != EXPECTED_GATE2_UNCERTAIN_ROWS:
        raise ValueError("INPUT_IDENTITY:gate2_uncertain_rows")
    if len(g2_present) != EXPECTED_GATE2_PRESENT_ROWS:
        raise ValueError("INPUT_IDENTITY:gate2_present_rows")
    if len(g2_uncertain) + len(g2_present) != EXPECTED_GATE2_ELIGIBLE_ROWS:
        raise ValueError("INPUT_IDENTITY:gate2_eligible_rows")

    if train_split_sha != EXPECTED_TRAIN_SPLIT_SHA256:
        raise ValueError("INPUT_IDENTITY:train_split_sha_mismatch")
    if val_split_sha != EXPECTED_VALIDATION_SPLIT_SHA256:
        raise ValueError("INPUT_IDENTITY:val_split_sha_mismatch")
    if train_id_sha != EXPECTED_TRAIN_IDENTITY_LIST_SHA256:
        raise ValueError("INPUT_IDENTITY:train_identity_list_mismatch")
    if val_id_sha != EXPECTED_VALIDATION_IDENTITY_LIST_SHA256:
        raise ValueError("INPUT_IDENTITY:val_identity_list_mismatch")
    if gate2_elig_sha != EXPECTED_GATE2_ELIGIBLE_IDENTITY_SHA256:
        raise ValueError("INPUT_IDENTITY:gate2_eligible_identity_mismatch")

    id_overlap = len(set(train_ids) & set(val_ids))
    if id_overlap != 0:
        raise ValueError("INPUT_IDENTITY:train_val_identity_overlap")

    lineage_overlap = 0
    if disjointness is not None:
        lineage_overlap = int(
            disjointness.get("parent_lineage_overlap")
            or (disjointness.get("raw") or {})
            .get("metrics", {})
            .get("train_validation_parent_lineage_overlap")
            or 0
        )
        source_overlap = int(disjointness.get("source_hash_overlap") or 0)
        near_dup = int(
            (disjointness.get("raw") or {})
            .get("metrics", {})
            .get("train_validation_near_duplicate_group_overlap")
            or 0
        )
        if (
            int(disjointness.get("identity_overlap") or 0) != 0
            or lineage_overlap != 0
            or source_overlap != 0
            or near_dup != 0
            or disjointness.get("pass") is not True
        ):
            raise ValueError("INPUT_IDENTITY:disjointness_fail")

    batch_size = int(TRAIN_HYPERPARAMS["micro_batch_size"])
    steps = len(
        full_pass_batch_indices(
            EXPECTED_TRAIN_ROWS,
            batch_size=batch_size,
            seed=int(TRAIN_HYPERPARAMS["seed"]),
            drop_last=DROP_LAST,
        )
    )
    witness = {
        "DATASET_SPLIT_RULE": DATASET_SPLIT_RULE,
        "class_balanced_sampler": CLASS_BALANCED_SAMPLER,
        "code_revision": code_revision,
        "dataset_sha256": dataset_sha256,
        "drop_last": DROP_LAST,
        "gate1_no_rows": EXPECTED_GATE1_NO_ROWS,
        "gate1_possible_rows": EXPECTED_GATE1_POSSIBLE_ROWS,
        "gate2_eligible_identity_sha256": gate2_elig_sha,
        "gate2_eligible_rows": EXPECTED_GATE2_ELIGIBLE_ROWS,
        "gate2_present_rows": EXPECTED_GATE2_PRESENT_ROWS,
        "gate2_uncertain_rows": EXPECTED_GATE2_UNCERTAIN_ROWS,
        "optimizer_steps_per_epoch": steps,
        "oversampling": OVERSAMPLING,
        "replacement": REPLACEMENT,
        "sampling": SAMPLER,
        "schema": SCHEMA_SPLIT_WITNESS,
        "shuffle_seed": int(TRAIN_HYPERPARAMS["seed"]),
        "train_dataloader_len": steps,
        "train_identity_list_sha256": train_id_sha,
        "train_rows": EXPECTED_TRAIN_ROWS,
        "train_split_sha256": train_split_sha,
        "train_validation_identity_overlap": id_overlap,
        "train_validation_lineage_overlap": lineage_overlap,
        "undersampling": UNDERSAMPLING,
        "validation_identity_list_sha256": val_id_sha,
        "validation_rows": EXPECTED_VALIDATION_ROWS,
        "validation_split_sha256": val_split_sha,
    }
    witness["TWO_STAGE_SPLIT_WITNESS_SHA256"] = sha256_text(
        canonical_json(
            {k: v for k, v in witness.items() if k != "TWO_STAGE_SPLIT_WITNESS_SHA256"}
        )
    )
    return witness


def gate1_target(evidence_label: str) -> int:
    """Map canonical gold → Gate-1 target (0=NONE, 1=POSSIBLE_EVIDENCE)."""
    label = str(evidence_label)
    if label == "NO_EVIDENCE":
        return 0
    if label in {"EVIDENCE_PRESENT", "UNCERTAIN"}:
        return 1
    raise ValueError(f"{LABEL_MAPPING_INVALID}:unknown_evidence_label:{label}")


def gate2_eligible(evidence_label: str) -> bool:
    return str(evidence_label) in {"EVIDENCE_PRESENT", "UNCERTAIN"}


def gate2_target(evidence_label: str) -> int:
    """Map PRESENT/UNCERTAIN gold → Gate-2 target (0=UNCERTAIN, 1=CONFIRMED)."""
    label = str(evidence_label)
    if label == "UNCERTAIN":
        return 0
    if label == "EVIDENCE_PRESENT":
        return 1
    raise ValueError(
        f"{LABEL_MAPPING_INVALID}:gate2_ineligible_gold:{label}"
    )


def provenance_multiplier(provenance: str | None) -> float:
    prov = str(provenance or "INFERRED")
    return float(PROVENANCE_LOSS_MULTIPLIERS.get(prov, 0.5))


def _binary_class_weights(
    *,
    effective: Mapping[str, float],
    labels: Sequence[str],
) -> dict[str, Any]:
    counts = [float(effective[label]) for label in labels]
    if not counts or all(c <= 0 for c in counts):
        raise ValueError("NO_DATA:empty_effective_counts")
    median = statistics.median([c if c > 0 else 1.0 for c in counts])
    raw = {}
    for label in labels:
        denom = float(effective[label]) if float(effective[label]) > 0 else 1.0
        raw[label] = math.sqrt(median / denom)
    mean_raw = sum(raw.values()) / len(raw)
    normalized = {label: value / mean_raw for label, value in raw.items()}
    clipped = {
        label: max(
            CLASS_WEIGHT_POLICY["clip_min"],
            min(CLASS_WEIGHT_POLICY["clip_max"], value),
        )
        for label, value in normalized.items()
    }
    return {
        "class_weights": clipped,
        "effective_counts": dict(effective),
        "normalized_weights": normalized,
        "policy": dict(CLASS_WEIGHT_POLICY),
        "provenance_multipliers": dict(PROVENANCE_LOSS_MULTIPLIERS),
        "raw_weights": raw,
    }


def _empty_class_account() -> dict[str, Any]:
    return {
        "OBSERVED_count": 0,
        "INFERRED_count": 0,
        "effective_count": 0.0,
        "final_clipped_weight": None,
        "final_weight": None,
        "normalized_weight": None,
        "raw_row_count": 0,
        "raw_weight": None,
        "rows": 0,
    }


def _account_row(account: dict[str, Any], provenance: str | None) -> None:
    prov = str(provenance or "INFERRED")
    account["raw_row_count"] += 1
    account["rows"] += 1
    if prov == "OBSERVED":
        account["OBSERVED_count"] += 1
    elif prov == "INFERRED":
        account["INFERRED_count"] += 1
    else:
        # Unknown provenance falls back to INFERRED multiplier (0.5) but is counted
        # under INFERRED_count for fail-closed accounting visibility.
        account["INFERRED_count"] += 1
    account["effective_count"] += provenance_multiplier(prov)


def _finalize_binary_accounts(
    accounts: dict[str, dict[str, Any]],
    *,
    labels: Sequence[str],
) -> dict[str, Any]:
    effective = {label: float(accounts[label]["effective_count"]) for label in labels}
    if any(v <= 0 for v in effective.values()):
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:non_positive_effective_count")
    report = _binary_class_weights(effective=effective, labels=labels)
    for label in labels:
        raw = float(report["raw_weights"][label])
        norm = float(report["normalized_weights"][label])
        final = float(report["class_weights"][label])
        if not math.isfinite(raw) or not math.isfinite(norm) or not math.isfinite(final):
            raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:non_finite_weight")
        if not (0.50 <= final <= 2.00):
            raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:clip_bounds")
        accounts[label]["raw_weight"] = raw
        accounts[label]["normalized_weight"] = norm
        accounts[label]["final_clipped_weight"] = final
        accounts[label]["final_weight"] = final
    return {
        "accounts": accounts,
        "class_weights": report["class_weights"],
        "effective_counts": report["effective_counts"],
        "normalized_weights": report["normalized_weights"],
        "policy": report["policy"],
        "provenance_multipliers": report["provenance_multipliers"],
        "raw_weights": report["raw_weights"],
    }


def compute_gate1_class_weights(
    train_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    accounts = {label: _empty_class_account() for label in GATE1_LABELS}
    for row in train_rows:
        target = gate1_target(str(row["evidence_label"]))
        label = GATE1_INDEX_LABEL[target]
        _account_row(accounts[label], row.get("provenance"))
    finalized = _finalize_binary_accounts(accounts, labels=GATE1_LABELS)
    finalized["gate"] = "gate1"
    finalized["labels"] = list(GATE1_LABELS)
    return finalized


def compute_gate2_class_weights(
    train_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    accounts = {label: _empty_class_account() for label in GATE2_LABELS}
    n_eligible = 0
    for row in train_rows:
        gold = str(row["evidence_label"])
        if not gate2_eligible(gold):
            continue
        n_eligible += 1
        target = gate2_target(gold)
        label = GATE2_INDEX_LABEL[target]
        _account_row(accounts[label], row.get("provenance"))
    if n_eligible == 0:
        raise ValueError("NO_DATA:gate2_zero_eligible_train_rows")
    finalized = _finalize_binary_accounts(accounts, labels=GATE2_LABELS)
    finalized["gate"] = "gate2"
    finalized["labels"] = list(GATE2_LABELS)
    finalized["n_eligible_train"] = n_eligible
    return finalized


def resolve_two_stage_class_weights(
    train_rows: Sequence[Mapping[str, Any]],
    *,
    dataset_sha256: str,
    train_split_sha256: str,
    code_revision: str,
) -> dict[str, Any]:
    """Hard pre-authorization class-weight resolution (train split only)."""
    if not train_rows:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:empty_train")
    if dataset_sha256 != AUTHORIZED_DATASET_SHA:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:dataset_mismatch")

    n_train = len(train_rows)
    n_none = sum(1 for r in train_rows if str(r["evidence_label"]) == "NO_EVIDENCE")
    n_present = sum(
        1 for r in train_rows if str(r["evidence_label"]) == "EVIDENCE_PRESENT"
    )
    n_uncertain = sum(1 for r in train_rows if str(r["evidence_label"]) == "UNCERTAIN")
    if n_none + n_present + n_uncertain != n_train:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:unexpected_gold_labels")

    gate1 = compute_gate1_class_weights(train_rows)
    gate2 = compute_gate2_class_weights(train_rows)

    g1_rows = sum(gate1["accounts"][label]["rows"] for label in GATE1_LABELS)
    if g1_rows != n_train:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:gate1_row_cover")
    if gate1["accounts"]["NO_EVIDENCE"]["rows"] != n_none:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:gate1_none_count")
    if gate1["accounts"]["POSSIBLE_EVIDENCE"]["rows"] != n_present + n_uncertain:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:gate1_possible_count")
    if gate2["n_eligible_train"] != n_present + n_uncertain:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:gate2_eligible_count")
    if gate2["accounts"]["UNCERTAIN"]["rows"] != n_uncertain:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:gate2_uncertain_count")
    if gate2["accounts"]["CONFIRMED_PRESENT"]["rows"] != n_present:
        raise ValueError("CLASS_WEIGHT_RESOLUTION_INVALID:gate2_present_count")

    literal_weights = {
        "gate1": {
            "NO_EVIDENCE": float(gate1["class_weights"]["NO_EVIDENCE"]),
            "POSSIBLE_EVIDENCE": float(gate1["class_weights"]["POSSIBLE_EVIDENCE"]),
        },
        "gate2": {
            "UNCERTAIN": float(gate2["class_weights"]["UNCERTAIN"]),
            "CONFIRMED_PRESENT": float(gate2["class_weights"]["CONFIRMED_PRESENT"]),
        },
    }
    payload = {
        "CLASS_WEIGHT_RESOLUTION_RULE": CLASS_WEIGHT_RESOLUTION_RULE,
        "Gate1": {
            "NO_EVIDENCE": dict(gate1["accounts"]["NO_EVIDENCE"]),
            "POSSIBLE_EVIDENCE": dict(gate1["accounts"]["POSSIBLE_EVIDENCE"]),
            "class_weights": dict(literal_weights["gate1"]),
            "coverage": {
                "n_train": n_train,
                "n_none": n_none,
                "n_possible": n_present + n_uncertain,
            },
        },
        "Gate2": {
            "UNCERTAIN": dict(gate2["accounts"]["UNCERTAIN"]),
            "CONFIRMED_PRESENT": dict(gate2["accounts"]["CONFIRMED_PRESENT"]),
            "class_weights": dict(literal_weights["gate2"]),
            "coverage": {
                "n_eligible": n_present + n_uncertain,
                "n_present": n_present,
                "n_uncertain": n_uncertain,
                "n_none_excluded": n_none,
            },
        },
        "clip_policy": {
            "max": CLASS_WEIGHT_POLICY["clip_max"],
            "min": CLASS_WEIGHT_POLICY["clip_min"],
            "renormalize_after_clip": False,
        },
        "code_revision": code_revision,
        "dataset_sha256": dataset_sha256,
        "literal_weights": literal_weights,
        "provenance_weights": dict(PROVENANCE_LOSS_MULTIPLIERS),
        "resolution_formula_version": CLASS_WEIGHT_FORMULA_VERSION,
        "schema": SCHEMA_CLASS_WEIGHTS,
        "train_split_sha256": train_split_sha256,
        "train_only": True,
    }
    payload["CLASS_WEIGHT_ARTIFACT_SHA256"] = sha256_text(
        canonical_json(
            {k: v for k, v in payload.items() if k != "CLASS_WEIGHT_ARTIFACT_SHA256"}
        )
    )
    return payload


def softmax2(logits: Sequence[float]) -> dict[str, float]:
    if len(logits) != 2:
        raise ValueError(f"{NOT_COMPUTABLE}:expected_2_logits")
    a = float(logits[0])
    b = float(logits[1])
    peak = max(a, b)
    ea = math.exp(a - peak)
    eb = math.exp(b - peak)
    total = ea + eb
    if total <= 0:
        raise ValueError(f"{NOT_COMPUTABLE}:softmax_degenerate")
    return {"0": ea / total, "1": eb / total}


def gate1_probabilities(logits: Sequence[float]) -> dict[str, float]:
    probs = softmax2(logits)
    return {
        "NO_EVIDENCE": probs["0"],
        "POSSIBLE_EVIDENCE": probs["1"],
    }


def gate2_probabilities(logits: Sequence[float]) -> dict[str, float]:
    probs = softmax2(logits)
    return {
        "UNCERTAIN": probs["0"],
        "CONFIRMED_PRESENT": probs["1"],
    }


def decide_two_stage(
    *,
    p_possible: float,
    p_confirmed: float,
    gate1_threshold: float,
    gate2_present_threshold: float,
) -> str:
    """Canonical inference policy (not a single scalar for three states)."""
    if not (0.0 <= float(p_possible) <= 1.0):
        raise ValueError(f"{NOT_COMPUTABLE}:p_possible_out_of_range")
    if not (0.0 <= float(p_confirmed) <= 1.0):
        raise ValueError(f"{NOT_COMPUTABLE}:p_confirmed_out_of_range")
    if not (0.0 <= float(gate1_threshold) <= 1.0):
        raise ValueError("gate1_threshold_out_of_range")
    if not (0.0 <= float(gate2_present_threshold) <= 1.0):
        raise ValueError("gate2_present_threshold_out_of_range")
    if float(p_possible) < float(gate1_threshold):
        return "NO_EVIDENCE"
    if float(p_confirmed) >= float(gate2_present_threshold):
        return "EVIDENCE_PRESENT"
    return "UNCERTAIN"


def forward_contract_schema() -> dict[str, Any]:
    return {
        "fields": [
            "gate1_logits",
            "gate2_logits",
            "gate1_probabilities",
            "gate2_probabilities",
        ],
        "gate1_logits": {"shape": [2], "order": list(GATE1_LABELS)},
        "gate2_logits": {"shape": [2], "order": list(GATE2_LABELS)},
        "note": (
            "Gate-2 logits may be computed for all rows; loss and canonical "
            "decision are masked unless Gate-1 permits entry."
        ),
        "pooling": POOLING,
        "schema": SCHEMA_FORWARD,
    }


def architecture_contract() -> dict[str, Any]:
    return {
        "encoder": "ModernBERT-base",
        "flat_head_status": FLAT_HEAD_STATUS,
        "gate1_head": "linear_hidden_to_2_logits",
        "gate2_head": "linear_hidden_to_2_logits",
        "head_init": HEAD_INIT,
        "last_trainable_encoder_layers": LAST_TRAINABLE_ENCODER_LAYERS,
        "pooling": POOLING,
        "shared_encoder": True,
        "forbidden_additions": [
            "mlp_head",
            "attention_block",
            "prototype",
            "retrieval",
            "family_head",
        ],
        "trainable": {
            "gate1_head": True,
            "gate2_head": True,
            "last_trainable_encoder_layers": LAST_TRAINABLE_ENCODER_LAYERS,
            "mutate_best": False,
        },
    }


def loss_contract() -> dict[str, Any]:
    return {
        "L_total": "L_gate1 + lambda_gate2 * L_gate2",
        "focal_forbidden": FOCAL_FORBIDDEN,
        "gate1": {
            "loss": LOSS_NAME,
            "scope": "all_stage_a_rows",
            "targets": {"NO_EVIDENCE": 0, "POSSIBLE_EVIDENCE": 1},
        },
        "gate2": {
            "loss": LOSS_NAME,
            "scope": "EVIDENCE_PRESENT_and_UNCERTAIN_gold_only",
            "targets": {"UNCERTAIN": 0, "CONFIRMED_PRESENT": 1},
            "none_rows_contribute": False,
        },
        "lambda_gate2": LAMBDA_GATE2,
        "name": "two_stage_weighted_binary_ce",
        "provenance_multipliers": dict(PROVENANCE_LOSS_MULTIPLIERS),
    }


def binary_macro_f1(golds: Sequence[int], preds: Sequence[int]) -> float | str:
    if not golds:
        return NO_DATA
    label_names = ("neg", "pos")
    # Map 0/1 to names for prf reuse via string labels.
    g = [label_names[int(x)] for x in golds]
    p = [label_names[int(x)] for x in preds]
    scores = [prf(g, p, name)["f1"] for name in label_names]
    return sum(scores) / len(scores)


def gate1_false_possible_entry_rate(
    golds: Sequence[str], gate1_preds_possible: Sequence[bool]
) -> float | str:
    none_idx = [i for i, g in enumerate(golds) if g == "NO_EVIDENCE"]
    if not none_idx:
        return NO_DATA
    leaked = sum(1 for i in none_idx if gate1_preds_possible[i])
    return leaked / len(none_idx)


def checkpoint_selection_score(
    *,
    gate1_macro_f1: float,
    gate2_macro_f1: float,
) -> float:
    return 0.50 * float(gate1_macro_f1) + 0.50 * float(gate2_macro_f1)


def select_checkpoint(
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Select best epoch by frozen selection_score + tie-breaks."""
    if not candidates:
        raise ValueError("NO_DATA:empty_checkpoint_candidates")
    ranked = sorted(
        candidates,
        key=lambda row: (
            -float(row["selection_score"]),
            float(row["gate1_false_possible_entry_rate"]),
            -float(row["gate2_confirmed_present_recall"]),
            int(row["epoch"]),
        ),
    )
    best = dict(ranked[0])
    best["rule"] = dict(CHECKPOINT_SELECTION)
    return best


def calibrate_two_stage_thresholds(
    *,
    golds: Sequence[str],
    p_possible: Sequence[float],
    p_confirmed: Sequence[float],
) -> dict[str, Any]:
    if not golds:
        raise ValueError("NO_DATA:empty_validation")
    if len(golds) != len(p_possible) or len(golds) != len(p_confirmed):
        raise ValueError(f"{NOT_COMPUTABLE}:length_mismatch")
    if any(x is None for x in p_possible) or any(x is None for x in p_confirmed):
        raise ValueError(f"{NOT_COMPUTABLE}:missing_probability")

    candidates = []
    for g1 in GATE1_THRESHOLDS:
        for g2 in GATE2_PRESENT_THRESHOLDS:
            decisions = [
                decide_two_stage(
                    p_possible=float(pp),
                    p_confirmed=float(pc),
                    gate1_threshold=g1,
                    gate2_present_threshold=g2,
                )
                for pp, pc in zip(p_possible, p_confirmed)
            ]
            metrics = evaluate_decisions(golds, decisions)
            candidates.append(
                {
                    "acceptance_pass": metrics["acceptance_pass"],
                    "false_evidence_entry_rate_on_none": metrics[
                        "false_evidence_entry_rate_on_none"
                    ],
                    "gate1_threshold": g1,
                    "gate2_present_threshold": g2,
                    "metrics": metrics,
                    "none_recall": metrics["by_label"]["NO_EVIDENCE"]["recall"],
                    "present_recall": metrics["by_label"]["EVIDENCE_PRESENT"]["recall"],
                    "stage_a_macro_f1": metrics["stage_a_macro_f1"],
                    "uncertain_recall": metrics["by_label"]["UNCERTAIN"]["recall"],
                }
            )

    passing = [row for row in candidates if row["acceptance_pass"]]
    if not passing:
        return {
            "chosen": None,
            "disposition": "SETTLED_FAIL",
            "feasible": False,
            "n_candidates": len(candidates),
            "n_passing": 0,
            "selection_rule": dict(THRESHOLD_SELECTION),
            "grid_results": [
                {
                    "acceptance_pass": row["acceptance_pass"],
                    "false_evidence_entry_rate_on_none": row[
                        "false_evidence_entry_rate_on_none"
                    ],
                    "gate1_threshold": row["gate1_threshold"],
                    "gate2_present_threshold": row["gate2_present_threshold"],
                    "none_recall": row["none_recall"],
                    "present_recall": row["present_recall"],
                    "stage_a_macro_f1": row["stage_a_macro_f1"],
                    "uncertain_recall": row["uncertain_recall"],
                }
                for row in candidates
            ],
        }

    ranked = sorted(
        passing,
        key=lambda row: (
            -float(row["stage_a_macro_f1"]),
            -float(row["present_recall"]),
            -float(row["uncertain_recall"]),
            float(row["false_evidence_entry_rate_on_none"]),
            -float(row["gate1_threshold"]),
            -float(row["gate2_present_threshold"]),
        ),
    )
    chosen = ranked[0]
    return {
        "chosen": {
            "gate1_threshold": chosen["gate1_threshold"],
            "gate2_present_threshold": chosen["gate2_present_threshold"],
            "metrics": chosen["metrics"],
        },
        "disposition": "SETTLED_PASS",
        "feasible": True,
        "n_candidates": len(candidates),
        "n_passing": len(passing),
        "selection_rule": dict(THRESHOLD_SELECTION),
    }


def component_gate_metrics(
    *,
    golds: Sequence[str],
    p_possible: Sequence[float],
    p_confirmed: Sequence[float],
    gate1_threshold: float,
    gate2_present_threshold: float,
) -> dict[str, Any]:
    """Diagnostic component metrics (do not replace end-to-end gates)."""
    g1_gold = [gate1_target(g) for g in golds]
    g1_pred = [
        1 if float(pp) >= float(gate1_threshold) else 0 for pp in p_possible
    ]
    g1_macro = binary_macro_f1(g1_gold, g1_pred)
    none_recall = prf(
        ["NONE" if t == 0 else "POSS" for t in g1_gold],
        ["NONE" if t == 0 else "POSS" for t in g1_pred],
        "NONE",
    )["recall"]
    possible_recall = prf(
        ["NONE" if t == 0 else "POSS" for t in g1_gold],
        ["NONE" if t == 0 else "POSS" for t in g1_pred],
        "POSS",
    )["recall"]
    false_possible = gate1_false_possible_entry_rate(
        golds, [bool(p) for p in g1_pred]
    )

    g2_idx = [i for i, g in enumerate(golds) if gate2_eligible(g)]
    if not g2_idx:
        g2_block: dict[str, Any] = {
            "CONFIRMED_PRESENT_recall": NO_DATA,
            "UNCERTAIN_recall": NO_DATA,
            "macro_f1": NO_DATA,
            "n_eligible": 0,
        }
    else:
        g2_gold = [gate2_target(golds[i]) for i in g2_idx]
        # Gate-2 evaluated only when Gate-1 permits; mask for diagnostics:
        # if Gate-1 blocks, treat as not confirmed (pred 0) for component view.
        g2_pred = []
        for i in g2_idx:
            if float(p_possible[i]) < float(gate1_threshold):
                g2_pred.append(0)
            else:
                g2_pred.append(
                    1
                    if float(p_confirmed[i]) >= float(gate2_present_threshold)
                    else 0
                )
        names_g = ["UNC" if t == 0 else "CONF" for t in g2_gold]
        names_p = ["UNC" if t == 0 else "CONF" for t in g2_pred]
        g2_block = {
            "CONFIRMED_PRESENT_recall": prf(names_g, names_p, "CONF")["recall"],
            "UNCERTAIN_recall": prf(names_g, names_p, "UNC")["recall"],
            "macro_f1": binary_macro_f1(g2_gold, g2_pred),
            "n_eligible": len(g2_idx),
        }

    return {
        "gate1": {
            "NO_EVIDENCE_recall": none_recall,
            "POSSIBLE_EVIDENCE_recall": possible_recall,
            "false_possible_entry_rate": false_possible,
            "macro_f1": g1_macro,
        },
        "gate2": g2_block,
        "note": "Component metrics are diagnostic; end-to-end gates remain authoritative.",
    }


def confusion_matrix(
    golds: Sequence[str],
    preds: Sequence[str],
    labels: Sequence[str],
) -> dict[str, Any]:
    """Square confusion matrix; missing labels appear as zero rows/cols."""
    if len(golds) != len(preds):
        raise ValueError(f"{NOT_COMPUTABLE}:confusion_length_mismatch")
    if not golds:
        return {"labels": list(labels), "matrix": NO_DATA, "counts": {}}
    index = {label: i for i, label in enumerate(labels)}
    n = len(labels)
    matrix = [[0 for _ in range(n)] for _ in range(n)]
    counts: dict[str, int] = {}
    for gold, pred in zip(golds, preds):
        if gold not in index or pred not in index:
            raise ValueError(f"{LABEL_MAPPING_INVALID}:confusion_unknown_label")
        matrix[index[gold]][index[pred]] += 1
        counts[f"{gold}->{pred}"] = counts.get(f"{gold}->{pred}", 0) + 1
    return {"counts": counts, "labels": list(labels), "matrix": matrix}


def gate1_confusion_matrix(
    golds: Sequence[str],
    *,
    p_possible: Sequence[float],
    gate1_threshold: float,
) -> dict[str, Any]:
    g_labels = [GATE1_INDEX_LABEL[gate1_target(g)] for g in golds]
    p_labels = [
        "POSSIBLE_EVIDENCE" if float(pp) >= float(gate1_threshold) else "NO_EVIDENCE"
        for pp in p_possible
    ]
    return confusion_matrix(g_labels, p_labels, GATE1_LABELS)


def gate2_confusion_matrix(
    golds: Sequence[str],
    *,
    p_possible: Sequence[float],
    p_confirmed: Sequence[float],
    gate1_threshold: float,
    gate2_present_threshold: float,
) -> dict[str, Any]:
    """Gate-2 confusion over PRESENT/UNCERTAIN gold only (NO_DATA if empty)."""
    eligible = [i for i, g in enumerate(golds) if gate2_eligible(g)]
    if not eligible:
        return {
            "labels": list(GATE2_LABELS),
            "matrix": NO_DATA,
            "counts": {},
            "n_eligible": 0,
        }
    g_labels = []
    p_labels = []
    for i in eligible:
        g_labels.append(GATE2_INDEX_LABEL[gate2_target(golds[i])])
        if float(p_possible[i]) < float(gate1_threshold):
            # Blocked at Gate 1 → not confirmed for component confusion.
            p_labels.append("UNCERTAIN")
        elif float(p_confirmed[i]) >= float(gate2_present_threshold):
            p_labels.append("CONFIRMED_PRESENT")
        else:
            p_labels.append("UNCERTAIN")
    out = confusion_matrix(g_labels, p_labels, GATE2_LABELS)
    out["n_eligible"] = len(eligible)
    return out


def route_diagnostics(
    *,
    golds: Sequence[str],
    p_possible: Sequence[float],
    p_confirmed: Sequence[float],
    gate1_threshold: float,
    gate2_present_threshold: float,
    rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Required PRESENT FN / NONE FP / UNCERTAIN routing diagnostics."""
    decisions = [
        decide_two_stage(
            p_possible=float(pp),
            p_confirmed=float(pc),
            gate1_threshold=gate1_threshold,
            gate2_present_threshold=gate2_present_threshold,
        )
        for pp, pc in zip(p_possible, p_confirmed)
    ]
    g1_enter = [float(pp) >= float(gate1_threshold) for pp in p_possible]

    present_fn_blocked_g1 = 0
    present_fn_rejected_g2 = 0
    none_fp_leaked_g1 = 0
    none_fp_both = 0
    unc_blocked_g1 = 0
    unc_correct = 0
    unc_promoted = 0

    for i, gold in enumerate(golds):
        pred = decisions[i]
        entered = g1_enter[i]
        if gold == "EVIDENCE_PRESENT" and pred != "EVIDENCE_PRESENT":
            if not entered:
                present_fn_blocked_g1 += 1
            else:
                present_fn_rejected_g2 += 1
        if gold == "NO_EVIDENCE" and pred == "EVIDENCE_PRESENT":
            none_fp_both += 1
            if entered:
                none_fp_leaked_g1 += 1
        elif gold == "NO_EVIDENCE" and entered:
            none_fp_leaked_g1 += 1
        if gold == "UNCERTAIN":
            if not entered:
                unc_blocked_g1 += 1
            elif pred == "UNCERTAIN":
                unc_correct += 1
            elif pred == "EVIDENCE_PRESENT":
                unc_promoted += 1

    out: dict[str, Any] = {
        "NONE_FP": {
            "leaked_through_both_gates": none_fp_both,
            "leaked_through_gate1": none_fp_leaked_g1,
        },
        "PRESENT_FN": {
            "blocked_at_gate1": present_fn_blocked_g1,
            "passed_gate1_rejected_at_gate2": present_fn_rejected_g2,
        },
        "UNCERTAIN": {
            "blocked_at_gate1": unc_blocked_g1,
            "correctly_routed": unc_correct,
            "promoted_incorrectly_to_PRESENT": unc_promoted,
        },
        "end_to_end_confusion": dict(
            Counter(f"{g}->{p}" for g, p in zip(golds, decisions))
        ),
    }

    if rows is not None and len(rows) == len(golds):
        strata = defaultdict(Counter)
        for i, row in enumerate(rows):
            key_prov = str(row.get("provenance") or "UNKNOWN")
            strata["by_provenance"][f"{golds[i]}:{decisions[i]}:{key_prov}"] += 1
            form = str(row.get("atom_prose") or row.get("surface_form") or "UNKNOWN")
            strata["by_ATOM_PROSE"][f"{golds[i]}:{decisions[i]}:{form}"] += 1
            src = str(row.get("source_family") or row.get("source_bucket") or "UNKNOWN")
            strata["by_source"][f"{golds[i]}:{decisions[i]}:{src}"] += 1
            domain = str(row.get("topic_domain") or "unspecified")
            strata["by_domain"][f"{golds[i]}:{decisions[i]}:{domain}"] += 1
            reason = str(row.get("ambiguity_reason") or "NONE")
            strata["by_ambiguity_reason"][f"{golds[i]}:{decisions[i]}:{reason}"] += 1
        out["strata"] = {k: dict(v) for k, v in strata.items()}
    return out


def gold_mapping_contract_sha256() -> str:
    from .classification_v5_stage_a_gold_label_mapping import mapping_contract

    return sha256_text(canonical_json(mapping_contract()))


def label_provenance_contract_sha256() -> str:
    return sha256_text(
        canonical_json(
            {
                "provenance_multipliers": dict(PROVENANCE_LOSS_MULTIPLIERS),
                "rule": LABEL_PROVENANCE_RULE,
            }
        )
    )


def two_stage_resolved_config(
    *,
    dataset_sha256: str,
    class_weight_artifact: Mapping[str, Any],
    code_revision: str,
    tokenizer_identity: str,
    architecture_receipt_sha256: str = ARCHITECTURE_RECEIPT_SHA256,
) -> dict[str, Any]:
    if dataset_sha256 != AUTHORIZED_DATASET_SHA:
        raise ValueError("dataset_sha_mismatch")
    if architecture_receipt_sha256 != ARCHITECTURE_RECEIPT_SHA256:
        raise ValueError("architecture_receipt_mismatch")
    literal = class_weight_artifact["literal_weights"]
    config = {
        "acceptance_gates": dict(ACCEPTANCE_GATES),
        "architecture": architecture_contract(),
        "architecture_receipt_sha256": architecture_receipt_sha256,
        "best_encoder_sha256": AUTHORIZED_BEST_SHA,
        "checkpoint_selection": dict(CHECKPOINT_SELECTION),
        "class_weight_artifact_sha256": class_weight_artifact[
            "CLASS_WEIGHT_ARTIFACT_SHA256"
        ],
        "code_revision": code_revision,
        "dataset_sha256": dataset_sha256,
        "experiment_id": EXPERIMENT_ID,
        "flat_head_status": FLAT_HEAD_STATUS,
        "forward": forward_contract_schema(),
        "gate1_class_weights_literal": dict(literal["gate1"]),
        "gate1_gold_mapping": {
            "EVIDENCE_PRESENT": 1,
            "NO_EVIDENCE": 0,
            "UNCERTAIN": 1,
        },
        "gate2_class_weights_literal": dict(literal["gate2"]),
        "gate2_gold_mapping": {
            "EVIDENCE_PRESENT": 1,
            "UNCERTAIN": 0,
        },
        "gate2_mask_rule": "gold_NO_EVIDENCE_excluded_from_gate2_loss",
        "gold_label_rule": GOLD_LABEL_RULE,
        "gold_mapping_sha256": gold_mapping_contract_sha256(),
        "label_provenance_contract_sha256": label_provenance_contract_sha256(),
        "label_provenance_rule": LABEL_PROVENANCE_RULE,
        "loss": loss_contract(),
        "optimization": {
            "early_stopping_patience": TRAIN_HYPERPARAMS["early_stopping_patience"],
            "gradient_accumulation": TRAIN_HYPERPARAMS["gradient_accumulation"],
            "learning_rate": TRAIN_HYPERPARAMS["learning_rate"],
            "max_epochs": TRAIN_HYPERPARAMS["max_epochs"],
            "max_grad_norm": TRAIN_HYPERPARAMS["max_grad_norm"],
            "micro_batch_size": TRAIN_HYPERPARAMS["micro_batch_size"],
            "minimum_epochs": TRAIN_HYPERPARAMS["minimum_epochs"],
            "mixed_precision": TRAIN_HYPERPARAMS["mixed_precision"],
            "optimizer": TRAIN_HYPERPARAMS["optimizer"],
            "warmup_ratio": TRAIN_HYPERPARAMS["warmup_ratio"],
            "weight_decay": TRAIN_HYPERPARAMS["weight_decay"],
        },
        "parent_experiment_id": PARENT_EXPERIMENT_ID,
        "parent_flat_selected_checkpoint_sha256": PARENT_FLAT_SELECTED_CHECKPOINT_SHA,
        "parent_primary_decision": PARENT_PRIMARY_DECISION,
        "provenance_weights": dict(PROVENANCE_LOSS_MULTIPLIERS),
        "rule": TWO_STAGE_RULE,
        "schema": SCHEMA_CONFIG,
        "seed": TRAIN_HYPERPARAMS["seed"],
        "surface_rule": AUTHORIZED_SURFACE_RULE,
        "threshold_grids": {
            "gate1_thresholds": list(GATE1_THRESHOLDS),
            "gate2_present_thresholds": list(GATE2_PRESENT_THRESHOLDS),
            "n_combinations": 100,
        },
        "threshold_selection": dict(THRESHOLD_SELECTION),
        "tokenization": {
            "max_length": TRAIN_HYPERPARAMS["max_len"],
            "padding": TRAIN_HYPERPARAMS["padding"],
            "tokenizer_identity": tokenizer_identity,
            "truncation": TRAIN_HYPERPARAMS["truncation"],
        },
        "train_rule": TRAIN_RULE,
        "train_run_limit": 1,
        "trainable": {
            "gate1_head": True,
            "gate2_head": True,
            "last_trainable_encoder_layers": LAST_TRAINABLE_ENCODER_LAYERS,
            "mutate_best": False,
        },
    }
    config["training_config_sha256"] = sha256_text(
        canonical_json({k: v for k, v in config.items() if k != "training_config_sha256"})
    )
    return config


def authorization_contract(
    *,
    dataset_sha256: str,
    training_config_sha256: str,
    class_weight_artifact_sha256: str,
    code_revision: str,
    architecture_receipt_sha256: str = ARCHITECTURE_RECEIPT_SHA256,
) -> dict[str, Any]:
    if architecture_receipt_sha256 != ARCHITECTURE_RECEIPT_SHA256:
        raise ValueError("architecture_receipt_mismatch")
    if dataset_sha256 != AUTHORIZED_DATASET_SHA:
        raise ValueError("dataset_sha_mismatch")
    return {
        "AUTHORIZE_RULE": AUTHORIZE_RULE,
        "ARCHITECTURE_RECEIPT_SHA256": architecture_receipt_sha256,
        "BEST": "UNCHANGED",
        "BEST_MUTATED": False,
        "CLASS_WEIGHT_ARTIFACT_SHA256": class_weight_artifact_sha256,
        "CURRENT_BEST": AUTHORIZED_BEST_SHA,
        "DATASET_SHA256": dataset_sha256,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "RESERVE_CONSUMED": False,
        "SCIENTIFIC_RESULT": "NOT_COMPUTABLE",
        "TRAINING_CONFIG_SHA256": training_config_sha256,
        "TRAINING_RUN_LIMIT": 1,
        "TRAINING_STATUS": "AUTHORIZED_NOT_STARTED",
        "TRAIN_AUTHORIZED": True,
        "authorized_best_sha256": AUTHORIZED_BEST_SHA,
        "authorized_dataset_sha256": AUTHORIZED_DATASET_SHA,
        "code_revision": code_revision,
        "flat_head_status": FLAT_HEAD_STATUS,
        "parent_experiment_id": PARENT_EXPERIMENT_ID,
        "parent_flat_selected_checkpoint_sha256": PARENT_FLAT_SELECTED_CHECKPOINT_SHA,
        "parent_primary_decision": PARENT_PRIMARY_DECISION,
        "prior_run_count": 0,
        "rule": TRAIN_RULE,
        "schema": SCHEMA_AUTHORIZATION,
        "surface_rule": AUTHORIZED_SURFACE_RULE,
        "train": False,
        "train_authorized": True,
        "two_stage_architecture_rule": TWO_STAGE_RULE,
    }


def runner_authorization_checks(
    *,
    train_authorized: bool,
    experiment_id: str,
    dataset_sha256: str,
    architecture_receipt_sha256: str,
    resolved_config_sha256: str,
    authorized_config_sha256: str,
    best_sha256: str,
    surface_readiness: str,
    label_mapping: str,
    label_provenance_invalid_rows: int,
    prior_run_count: int,
    reserve_consumed: bool,
    class_weight_artifact_sha256: str,
    authorized_class_weight_artifact_sha256: str,
) -> dict[str, Any]:
    checks = {
        "architecture_receipt": architecture_receipt_sha256
        == ARCHITECTURE_RECEIPT_SHA256,
        "best": best_sha256 == AUTHORIZED_BEST_SHA,
        "class_weight_artifact": class_weight_artifact_sha256
        == authorized_class_weight_artifact_sha256,
        "dataset_sha256": dataset_sha256 == AUTHORIZED_DATASET_SHA,
        "experiment_id": experiment_id == EXPERIMENT_ID,
        "label_mapping": label_mapping == "PASS",
        "label_provenance_invalid_rows": label_provenance_invalid_rows == 0,
        "prior_run_count": prior_run_count == 0,
        "reserve_consumed": reserve_consumed is False,
        "resolved_config_sha256": resolved_config_sha256 == authorized_config_sha256,
        "surface_readiness": surface_readiness == "PASS",
        "train_authorized": train_authorized is True,
    }
    checks["pass"] = all(checks.values())
    return checks


def train_receipt_schema() -> dict[str, Any]:
    return {
        "required_fields": [
            "EXPERIMENT_ID",
            "DATASET_SHA256",
            "TRAINING_CONFIG_SHA256",
            "SELECTED_CHECKPOINT_SHA256",
            "RUN_RECEIPT_SHA256",
            "SCIENTIFIC_RESULT",
            "acceptance_gates",
            "gate1_confusion",
            "gate2_confusion",
            "end_to_end_confusion",
            "route_diagnostics",
            "component_metrics",
            "threshold_grid",
            "BEST",
            "RESERVE",
            "TRAIN",
        ],
        "schema": SCHEMA_TRAIN_RECEIPT,
        "scientific_result_values": ["SETTLED_PASS", "SETTLED_FAIL"],
    }


def design_freeze_receipt(*, code_revision: str) -> dict[str, Any]:
    """Public design-state receipt helper (historical; sealed hash is pinned).

    Authorization binds ARCHITECTURE_RECEIPT_SHA256 (631427cc…), not a re-freeze.
    """
    demo_rows = [
        {"evidence_label": "NO_EVIDENCE", "provenance": "OBSERVED"},
        {"evidence_label": "EVIDENCE_PRESENT", "provenance": "OBSERVED"},
        {"evidence_label": "UNCERTAIN", "provenance": "INFERRED"},
        {"evidence_label": "EVIDENCE_PRESENT", "provenance": "INFERRED"},
    ]
    demo_weights = resolve_two_stage_class_weights(
        demo_rows,
        dataset_sha256=AUTHORIZED_DATASET_SHA,
        train_split_sha256="demo_only_not_for_authorization",
        code_revision=code_revision,
    )
    resolved = two_stage_resolved_config(
        dataset_sha256=AUTHORIZED_DATASET_SHA,
        class_weight_artifact=demo_weights,
        code_revision=code_revision,
        tokenizer_identity="local_files_only:ModernBERT-base",
    )
    payload = {
        "AUTHORIZE_RULE_NEXT": AUTHORIZE_RULE,
        "BEST": "UNCHANGED",
        "BEST_SHA256": AUTHORIZED_BEST_SHA,
        "DATASET_SHA256": AUTHORIZED_DATASET_SHA,
        "DESIGN_EXPERIMENT_ID": DESIGN_EXPERIMENT_ID,
        "DESIGN_STATE": "FROZEN",
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "PARENT_EXPERIMENT_ID": PARENT_EXPERIMENT_ID,
        "PARENT_PRIMARY_DECISION": PARENT_PRIMARY_DECISION,
        "RESERVE": "unused",
        "SURFACE_RULE": AUTHORIZED_SURFACE_RULE,
        "TRAIN": False,
        "TRAIN_AUTHORIZED": False,
        "acceptance_gates": dict(ACCEPTANCE_GATES),
        "architecture": architecture_contract(),
        "architecture_receipt_sha256_pin": ARCHITECTURE_RECEIPT_SHA256,
        "checkpoint_selection": dict(CHECKPOINT_SELECTION),
        "code_revision": code_revision,
        "compatibility": {
            "flat_head_status": FLAT_HEAD_STATUS,
            "gold_label_rule": GOLD_LABEL_RULE,
            "historical_flat_artifacts_retained": True,
            "label_provenance_rule": LABEL_PROVENANCE_RULE,
            "v1r9_dataset_unchanged": True,
        },
        "demo_weight_witness_only": {
            "literal_weights": demo_weights["literal_weights"],
            "note": (
                "Witness of formula application on a tiny synthetic set; "
                "authorize must resolve on full V1R9 train split before "
                "TRAIN_AUTHORIZED=true."
            ),
        },
        "forward": forward_contract_schema(),
        "gate1_gold_mapping": {
            "EVIDENCE_PRESENT": 1,
            "NO_EVIDENCE": 0,
            "UNCERTAIN": 1,
        },
        "gate2_gold_mapping": {
            "EVIDENCE_PRESENT": 1,
            "NO_EVIDENCE": "EXCLUDED_FROM_GATE2_LOSS",
            "UNCERTAIN": 0,
        },
        "graph": {
            "canonical_outputs": list(CANONICAL_LABELS),
            "edges": [
                "encoder -> gate1",
                "gate1:NO_EVIDENCE -> NO_EVIDENCE",
                "gate1:POSSIBLE_EVIDENCE -> gate2",
                "gate2:CONFIRMED_PRESENT -> EVIDENCE_PRESENT",
                "gate2:UNCERTAIN -> UNCERTAIN",
            ],
            "factorization": "architectural_only",
        },
        "inference_policy": {
            "gate1": "if P(POSSIBLE_EVIDENCE) < gate1_threshold -> NO_EVIDENCE else Gate2",
            "gate2": (
                "if P(CONFIRMED_PRESENT) >= gate2_present_threshold -> "
                "EVIDENCE_PRESENT else UNCERTAIN"
            ),
            "scalar_three_state_forbidden": True,
        },
        "loss": loss_contract(),
        "no_data_rules": {
            "gate2_zero_eligible": NO_DATA,
            "missing_gold_field": LABEL_MAPPING_INVALID,
            "missing_probability_or_logit": NOT_COMPUTABLE,
            "silent_zero_substitution": False,
        },
        "resolved_config_schema_sha_witness": resolved["training_config_sha256"],
        "rule": TWO_STAGE_RULE,
        "schemas": {
            "authorization": SCHEMA_AUTHORIZATION,
            "class_weights": SCHEMA_CLASS_WEIGHTS,
            "config": SCHEMA_CONFIG,
            "forward": SCHEMA_FORWARD,
            "train_receipt": SCHEMA_TRAIN_RECEIPT,
        },
        "threshold_grids": {
            "gate1_thresholds": list(GATE1_THRESHOLDS),
            "gate2_present_thresholds": list(GATE2_PRESENT_THRESHOLDS),
            "n_combinations": 100,
        },
        "threshold_selection": dict(THRESHOLD_SELECTION),
        "train_receipt_schema": train_receipt_schema(),
    }
    payload["design_receipt_sha256"] = sha256_text(
        canonical_json({k: v for k, v in payload.items() if k != "design_receipt_sha256"})
    )
    return payload
