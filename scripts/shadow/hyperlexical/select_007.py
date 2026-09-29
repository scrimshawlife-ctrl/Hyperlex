"""SELECT-007 preregistration and acceptance. This module does not train."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

EXPERIMENT_ID = "HLX-EXP-2026-09-29-SELECT-007"
SELECT_006_ID = "HLX-EXP-2026-09-29-SELECT-006"
WARM_START_SHA256 = "96838b9656a84c3fee1773a41fdf2fbbec2f88f3bc948e4acfbe06c194ac5587"
TRAINING_DATA_SHA256 = "64b7d3dede25047cb6dd2e5b663f7fa72946ec82ac1a8816ae34622d1aaac430"
BEST_SHA256 = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
LOADER_WITNESS_SHA256 = "58a3e733087c33c5ffea5909b46098e666337e1b99fb83d87c3744db4aef91b2"
LEDGER_EVENTS_BEFORE = "4471e3339b3708f0f494f7fe60a0d30118609e7312d5d0334b946d2bbc4efbf1"
LEDGER_PROJECTION_BEFORE = "dad556c7f6bba58c7456a6b88b607c72ebe8149e36c176a602e0def2edfdc435"

RULE = "inferred_none_circular_sha256_v1"
CAP = 219
OBSERVED_NONE = 219
INFERRED_NONE = 1935
CLASSIFY_TRAIN_ROWS = 4360

METRICS = (
    "classification_accuracy",
    "classify_macro_f1_nonnone",
    "observed_label_accuracy",
    "predicted_none_rate",
    "unbind_clean_exact",
)

SCHEDULE = {
    "early_stopping": True,
    "early_stopping_patience": 4,
    "improvement": "strict",
    "max_epochs": 12,
    "minimum_epochs": 4,
    "restore_best": True,
    "ties": "keep_earlier",
}


def canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def preregistration_hash(definition: Mapping[str, Any] | None = None) -> str:
    body = definition if definition is not None else preregistration()
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def preregistration() -> dict[str, Any]:
    """Frozen scientific definition. Sampling is the only arm difference."""
    schedule = dict(SCHEDULE)
    return {
        "acceptance_rules": {
            "integrity_failure": "SETTLED_INVALID",
            "missing_metric": "FAIL",
            "no_compensation": True,
            "predicted_none_rate": "candidate < control",
            "preservation": {
                "classification_accuracy": "candidate >= control",
                "observed_label_accuracy": "candidate >= control",
                "unbind_clean_exact": "candidate >= control",
            },
            "primary": "candidate classify_macro_f1_nonnone > control classify_macro_f1_nonnone",
            "predicted_none_rate_role": "mechanistic confirmation, not a promotion gate",
        },
        "candidate_schedule": schedule,
        "control_schedule": dict(schedule),
        "evaluation_design": {
            "cross_experiment_reserve_reuse": "FORBIDDEN",
            "metrics": list(METRICS),
            "predicted_none_rate": (
                "count of classify predictions equal to none divided by "
                "the number of scored classify reserve rows"
            ),
            "reserve": {
                "direct_label_lexicon": "select_006_source_design_v2.DIRECT_LABELS",
                "discovery_per_family": 8,
                "unbind_clean_continuation": (
                    "If the first 8 pages per family yield no incidental "
                    "unbind_clean row, continue the same search order and "
                    "direct labels until one incidental unbind_clean row is "
                    "kept or the scan cap is exhausted. Labels are not widened."
                ),
                "floors": {
                    "classify": 1,
                    "classify_non_none": 1,
                    "classify_observed": 1,
                    "head_mapped_non_none": 1,
                    "unbind_clean": 1,
                },
                "observed_rule": (
                    "ACCEPT OBSERVED only when named_target_family of the "
                    "definition line's own sense-label arguments is one frozen "
                    "target family. INFERRED is not promoted. Unbind rows are "
                    "NONE and stay incidental."
                ),
                "scan_cap_per_query": 240,
                "source": "wiktionary_labeled_sense",
                "surface": "fresh EVAL_RESERVE bound only to this experiment",
            },
            "sampling": {
                "candidate": f"{RULE}:{CAP}",
                "cap_applies_to": "INFERRED none classify rows only",
                "control": "uncapped",
                "control_inferred_none_per_epoch": INFERRED_NONE,
                "candidate_inferred_none_per_epoch": CAP,
                "forbidden_selection_inputs": [
                    "difficulty",
                    "loss",
                    "model_prediction",
                    "reserve_performance",
                ],
                "identity": "normalized_text_sha256(text)",
                "observed_none_preserved": OBSERVED_NONE,
                "order": "original classify train order among kept rows",
                "population": {
                    "classify_train_rows": CLASSIFY_TRAIN_ROWS,
                    "inferred_none": INFERRED_NONE,
                    "observed_none": OBSERVED_NONE,
                },
                "rule": (
                    "Sort INFERRED none rows by (identity, original index). "
                    "For one-based epoch e, start at ((e-1)*219) mod N and "
                    "take 219 rows circularly. N is 1935. Record those "
                    "identity hashes. Do not cap any other class."
                ),
                "rule_id": RULE,
                "seed_policy": "HLX_SEED_UNSET_FROZEN",
                "seed_policy_defines_epoch_sampling": False,
            },
            "select_006_reserve": "NOT_REUSED",
        },
        "experiment_id": EXPERIMENT_ID,
        "hypothesis": (
            "Capping INFERRED none examples per classify epoch at the OBSERVED "
            "none count reduces none overprediction on head-mapped OBSERVED "
            "evaluation data without degrading the existing preservation metrics."
        ),
        "promotion_policy": {
            "pass_promotes_best": False,
            "promotion_applied": False,
            "promotion_eligible": False,
            "separate_from_settlement": True,
        },
        "selection_metric": "classify_macro_f1_nonnone",
        "shared_hyperparameters": {
            "batch_size": 8,
            "filler_filter": "strict",
            "gradient_accumulation": 1,
            "init_expand_vocab": True,
            "last_trainable": 2,
            "learning_rate": 2e-5,
            "loss": "unweighted_cross_entropy",
            "max_length": 64,
            "schedule": schedule,
            "seed": None,
            "trunk": "answerdotai/ModernBERT-base",
            "unbind_curriculum": False,
            "unbind_every_n": 1,
            "unbind_loss_weight": 1.0,
            "unbind_primary": "mixed",
            "warm_start_sha256": WARM_START_SHA256,
            "zero_init_loader_witness_sha256": LOADER_WITNESS_SHA256,
        },
        "training_data_sha256": TRAINING_DATA_SHA256,
        "warm_start_sha256": WARM_START_SHA256,
    }


def _metric(row: Mapping[str, Any], key: str) -> float | None:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def evaluate_acceptance(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    """Strict primary, three preservation gates, and a lower none rate.

    A missing metric is FAIL. This function does not judge integrity.
    """
    gates: dict[str, Any] = {}
    missing = [key for key in METRICS if _metric(control, key) is None or _metric(candidate, key) is None]
    if missing:
        for key in METRICS:
            gates[key] = "MISSING" if key in missing else "NOT_EVALUATED"
        return {
            "acceptance_passed": False,
            "gates": gates,
            "missing": missing,
            "outcome": "FAIL",
            "reason": "missing metric",
        }
    control_f1 = _metric(control, "classify_macro_f1_nonnone")
    candidate_f1 = _metric(candidate, "classify_macro_f1_nonnone")
    assert control_f1 is not None and candidate_f1 is not None
    comparisons = {
        "classify_macro_f1_nonnone": candidate_f1 > control_f1,
        "classification_accuracy": _metric(candidate, "classification_accuracy")
        >= _metric(control, "classification_accuracy"),
        "observed_label_accuracy": _metric(candidate, "observed_label_accuracy")
        >= _metric(control, "observed_label_accuracy"),
        "predicted_none_rate": _metric(candidate, "predicted_none_rate")
        < _metric(control, "predicted_none_rate"),
        "unbind_clean_exact": _metric(candidate, "unbind_clean_exact")
        >= _metric(control, "unbind_clean_exact"),
    }
    for key, passed in comparisons.items():
        gates[key] = "PASS" if passed else "FAIL"
    passed_all = all(comparisons.values())
    return {
        "acceptance_passed": passed_all,
        "classify_macro_f1_nonnone_delta": candidate_f1 - control_f1,
        "gates": gates,
        "missing": [],
        "outcome": "PASS" if passed_all else "FAIL",
        "reason": None if passed_all else "acceptance gate",
    }
