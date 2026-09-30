"""Stage-A-003 class-weighted focal CE — experiment-scoped objective freeze.

Does not train. Does not modify decide_evidence. Does not alter the canonical
Stage-A-002 recipe globally; focal is allowed only for
HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS.
"""

from __future__ import annotations

import copy
import math
from typing import Any, Mapping, Sequence

import torch
from torch import Tensor
from torch.nn import functional as F

from .classification_v5_stage_a import (
    ACCEPTANCE_GATES,
    AUTHORIZED_DATASET_SHA,
    AUTHORIZED_SURFACE_RULE,
    BEST_SHA,
    CHECKPOINT_SELECTION,
    EVIDENCE_LABELS,
    LABEL_PROVENANCE_RULE,
    PROVENANCE_LOSS_MULTIPLIERS,
    STAGE_A_RULE,
    THRESHOLD_GRID,
    THRESHOLD_SELECTION,
    TRAIN_HYPERPARAMS,
    build_resolved_training_config,
    canonical_json,
    sha256_text,
)

EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS"
PARENT_EXPERIMENT_ID = "HLX-CLASSIFICATION-V5-STAGE-A-002"
PARENT_TRAINING_CONFIG_SHA256 = (
    "2ce1b29bf2be54cc03ac25d66301bf0991226dffd3a1d94bcdaa7a48559d40af"
)
PARENT_ORDINARY_NONE_FALSE_PRESENT = 11
PARENT_PRESENT_TO_NONE = 297
PARENT_PRESENT_RECALL = 0.5274725274725275
PARENT_PRESENT_TO_NONE_MEDIAN_P_NONE = 0.9940457964139012
PARENT_PRESENT_TO_NONE_CONFIDENT_NONE_FRAC = 0.7474747474747475
PARENT_PRESENT_TO_NONE_NEAR_BOUNDARY_FRAC = 0.010101010101010102

FOCAL_GAMMA = 2.0
FOCAL_ALPHA_POLICY = "NONE"
CLASS_WEIGHT_POLICY = "UNCHANGED_FROM_STAGE_A_002"
PROVENANCE_MULTIPLIER_POLICY = "UNCHANGED_FROM_STAGE_A_002"
REDUCTION = "MEAN_OVER_VALID_EXAMPLES"
MASKING_POLICY = "UNCHANGED_FROM_STAGE_A_002"
NUMERICAL_IMPLEMENTATION = "stable_log_softmax"
DECISION_POLICY = "UNCHANGED_decide_evidence_P_PRESENT_only"
OBJECTIVE_NAME = "weighted_focal_cross_entropy"

# Preregistered bound for "ordinary false-PRESENT remains near remediated low".
# Parent 002 remediated count = 11; pre-V1R8 was 60. Cap at 2× remediated.
ORDINARY_FALSE_PRESENT_REMAINS_LOW_MAX = 22

SUPPORT_CRITERION = (
    "One train on unchanged V1R8 with only focal loss: "
    "false_evidence_entry_rate_on_none <= 0.05 AND "
    "PRESENT recall >= 0.70 AND "
    "threshold_grid n_passing >= 1 AND "
    "PRESENT→NONE median P(NONE) < 0.80 AND "
    f"ordinary NONE→PRESENT <= {ORDINARY_FALSE_PRESENT_REMAINS_LOW_MAX} "
    f"(2× Stage-A-002 remediated count {PARENT_ORDINARY_NONE_FALSE_PRESENT}; "
    "pre-V1R8 was 60)."
)

FALSIFICATION_CRITERION = (
    "H1 falsified for this intervention if: PRESENT recall < 0.70 OR "
    "false_evidence_entry_rate_on_none > 0.05 OR "
    f"ordinary NONE→PRESENT > {ORDINARY_FALSE_PRESENT_REMAINS_LOW_MAX} OR "
    "(threshold_grid n_passing = 0 AND PRESENT→NONE median P(NONE) >= 0.80)."
)

FORMULA = (
    "p = softmax(logits); p_t = p[y]; "
    "base_ce = class_weight[y] * provenance_multiplier * (-log p_t); "
    "focal = (1 - p_t)^gamma * base_ce; "
    "batch_loss = mean(focal over examples). "
    "No focal alpha. gamma frozen at 2.0."
)


def class_weight_tensor(
    class_weights: Mapping[str, float], *, device: torch.device | None = None
) -> Tensor:
    values = [float(class_weights[label]) for label in EVIDENCE_LABELS]
    return torch.tensor(values, dtype=torch.float32, device=device)


def weighted_cross_entropy_per_example(
    logits: Tensor,
    targets: Tensor,
    class_weights: Tensor,
    provenance_weights: Tensor,
) -> Tensor:
    """Parent Stage-A-002 per-example loss (reduction=none then × provenance)."""
    if logits.ndim != 2:
        raise ValueError("logits_must_be_2d")
    if targets.ndim != 1 or targets.shape[0] != logits.shape[0]:
        raise ValueError("targets_shape_mismatch")
    if provenance_weights.shape != targets.shape:
        raise ValueError("provenance_shape_mismatch")
    if class_weights.shape[0] != logits.shape[1]:
        raise ValueError("class_weight_dim_mismatch")
    log_probs = F.log_softmax(logits, dim=-1)
    nll = -log_probs.gather(1, targets.unsqueeze(1)).squeeze(1)
    cw = class_weights.gather(0, targets)
    return cw * provenance_weights * nll


def weighted_focal_cross_entropy_per_example(
    logits: Tensor,
    targets: Tensor,
    class_weights: Tensor,
    provenance_weights: Tensor,
    *,
    gamma: float = FOCAL_GAMMA,
) -> Tensor:
    """Class-weighted focal CE; alpha policy NONE (no extra focal alpha)."""
    if float(gamma) < 0.0:
        raise ValueError("gamma_must_be_nonnegative")
    base = weighted_cross_entropy_per_example(
        logits, targets, class_weights, provenance_weights
    )
    log_probs = F.log_softmax(logits, dim=-1)
    log_pt = log_probs.gather(1, targets.unsqueeze(1)).squeeze(1)
    pt = log_pt.exp().clamp(0.0, 1.0)
    modulating = (1.0 - pt).pow(float(gamma))
    return modulating * base


def reduce_mean(per_example: Tensor) -> Tensor:
    if per_example.numel() == 0:
        raise ValueError("empty_loss_batch")
    return per_example.mean()


def build_objective_spec(
    *,
    dataset_sha256: str = AUTHORIZED_DATASET_SHA,
    seed: int = int(TRAIN_HYPERPARAMS["seed"]),
) -> dict[str, Any]:
    spec = {
        "ALLOW_FOCAL_LOSS_FOR": EXPERIMENT_ID,
        "BEST": "UNCHANGED",
        "CLASS_WEIGHT_POLICY": CLASS_WEIGHT_POLICY,
        "DATASET": "V1R8_UNCHANGED",
        "DATASET_SHA256": dataset_sha256,
        "DECISION_POLICY": DECISION_POLICY,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "FALSIFICATION_CRITERION": FALSIFICATION_CRITERION,
        "FOCAL_ALPHA_POLICY": FOCAL_ALPHA_POLICY,
        "FOCAL_GAMMA": FOCAL_GAMMA,
        "FORMULA": FORMULA,
        "MASKING_POLICY": MASKING_POLICY,
        "NUMERICAL_IMPLEMENTATION": NUMERICAL_IMPLEMENTATION,
        "OBJECTIVE_NAME": OBJECTIVE_NAME,
        "ORDINARY_FALSE_PRESENT_REMAINS_LOW_MAX": ORDINARY_FALSE_PRESENT_REMAINS_LOW_MAX,
        "PARENT_EXPERIMENT": PARENT_EXPERIMENT_ID,
        "PARENT_PINS": {
            "ORDINARY_NONE_FALSE_PRESENT": PARENT_ORDINARY_NONE_FALSE_PRESENT,
            "PRESENT_RECALL": PARENT_PRESENT_RECALL,
            "PRESENT_TO_NONE": PARENT_PRESENT_TO_NONE,
            "PRESENT_TO_NONE_CONFIDENT_NONE_FRAC": (
                PARENT_PRESENT_TO_NONE_CONFIDENT_NONE_FRAC
            ),
            "PRESENT_TO_NONE_MEDIAN_P_NONE": PARENT_PRESENT_TO_NONE_MEDIAN_P_NONE,
            "PRESENT_TO_NONE_NEAR_BOUNDARY_FRAC": (
                PARENT_PRESENT_TO_NONE_NEAR_BOUNDARY_FRAC
            ),
            "TRAINING_CONFIG_SHA256": PARENT_TRAINING_CONFIG_SHA256,
        },
        "PROVENANCE_MULTIPLIER_POLICY": PROVENANCE_MULTIPLIER_POLICY,
        "REDUCTION": REDUCTION,
        "RESERVE": "unused",
        "SEED": seed,
        "SUPPORT_CRITERION": SUPPORT_CRITERION,
        "UNCERTAIN_POLICY_INVESTIGATION_PENDING": True,
        "canonical_stage_a_recipe_modified_globally": False,
        "schema": "hyperlex.classification.v5.stage_a_003_focal_objective_spec.v1",
        "surface_rule": AUTHORIZED_SURFACE_RULE,
    }
    spec["FOCAL_LOSS_SPEC_SHA256"] = sha256_text(
        canonical_json({k: v for k, v in spec.items() if k != "FOCAL_LOSS_SPEC_SHA256"})
    )
    return spec


def build_resolved_training_config_003(
    *,
    dataset_sha256: str,
    class_weight_report: Mapping[str, Any],
    code_revision: str,
    tokenizer_identity: str,
    surface_rule: str = AUTHORIZED_SURFACE_RULE,
    focal_loss_spec_sha256: str,
) -> dict[str, Any]:
    """Parent 002 config with only the objective block scientifically changed."""
    parent = build_resolved_training_config(
        dataset_sha256=dataset_sha256,
        class_weight_report=class_weight_report,
        code_revision=code_revision,
        tokenizer_identity=tokenizer_identity,
        surface_rule=surface_rule,
    )
    config = copy.deepcopy(parent)
    config["experiment_id"] = EXPERIMENT_ID
    config["parent_experiment_id"] = PARENT_EXPERIMENT_ID
    config["parent_training_config_sha256"] = PARENT_TRAINING_CONFIG_SHA256
    config["loss"] = {
        "ALLOW_FOCAL_LOSS_FOR": EXPERIMENT_ID,
        "alpha_policy": FOCAL_ALPHA_POLICY,
        "forbidden": [
            "contrastive",
            "family",
            "prototype",
            "reserve_derived_weighting",
            "focal_alpha",
            "gamma_sweep",
        ],
        "focal_loss_spec_sha256": focal_loss_spec_sha256,
        "formula": FORMULA,
        "gamma": FOCAL_GAMMA,
        "name": OBJECTIVE_NAME,
        "numerical_implementation": NUMERICAL_IMPLEMENTATION,
        "provenance_multipliers": dict(PROVENANCE_LOSS_MULTIPLIERS),
        "reduction": REDUCTION,
        "scope": "experiment_scoped_exception_to_parent_forbidden_focal",
    }
    config["decision_policy"] = DECISION_POLICY
    config["schema"] = "hyperlex.classification.v5.stage_a_003_resolved_config.v1"
    # Drop parent self-hash then recompute for 003.
    config.pop("training_config_sha256", None)
    config["training_config_sha256"] = sha256_text(canonical_json(config))
    return config


def single_factor_diff(
    parent_config: Mapping[str, Any], child_config: Mapping[str, Any]
) -> dict[str, Any]:
    """Machine-readable single-factor check vs Stage-A-002."""

    def _get(cfg: Mapping[str, Any], *keys: str) -> Any:
        cur: Any = cfg
        for key in keys:
            cur = cur[key]
        return cur

    checks = {
        "DATASET_CHANGED": _get(parent_config, "dataset_sha256")
        != _get(child_config, "dataset_sha256"),
        "SPLIT_CHANGED": False,  # same V1R8 body; no split rewrite authorized
        "SEED_CHANGED": _get(parent_config, "seed") != _get(child_config, "seed"),
        "BACKBONE_CHANGED": _get(parent_config, "architecture", "encoder")
        != _get(child_config, "architecture", "encoder"),
        "HEAD_CHANGED": _get(parent_config, "architecture", "head")
        != _get(child_config, "architecture", "head"),
        "POOLING_CHANGED": _get(parent_config, "architecture", "pooling")
        != _get(child_config, "architecture", "pooling"),
        "TOKENIZER_CHANGED": _get(parent_config, "tokenization")
        != _get(child_config, "tokenization"),
        "OPTIMIZER_CHANGED": _get(parent_config, "optimization", "optimizer")
        != _get(child_config, "optimization", "optimizer"),
        "LR_CHANGED": _get(parent_config, "optimization", "learning_rate")
        != _get(child_config, "optimization", "learning_rate"),
        "SCHEDULER_CHANGED": (
            _get(parent_config, "optimization", "warmup_ratio")
            != _get(child_config, "optimization", "warmup_ratio")
        ),
        "BATCHING_CHANGED": (
            _get(parent_config, "optimization", "micro_batch_size")
            != _get(child_config, "optimization", "micro_batch_size")
            or _get(parent_config, "optimization", "gradient_accumulation")
            != _get(child_config, "optimization", "gradient_accumulation")
        ),
        "TRAINING_BUDGET_CHANGED": (
            _get(parent_config, "optimization", "max_epochs")
            != _get(child_config, "optimization", "max_epochs")
            or _get(parent_config, "optimization", "minimum_epochs")
            != _get(child_config, "optimization", "minimum_epochs")
            or _get(parent_config, "optimization", "early_stopping_patience")
            != _get(child_config, "optimization", "early_stopping_patience")
        ),
        "CLASS_WEIGHTS_CHANGED": _get(parent_config, "class_weight_report", "class_weights")
        != _get(child_config, "class_weight_report", "class_weights"),
        "PROVENANCE_WEIGHTS_CHANGED": (
            _get(parent_config, "class_weight_report", "provenance_multipliers")
            != _get(child_config, "class_weight_report", "provenance_multipliers")
        ),
        "DECISION_LOGIC_CHANGED": child_config.get("decision_policy")
        not in (None, DECISION_POLICY),
        "THRESHOLDS_CHANGED": (
            _get(parent_config, "threshold_grid") != _get(child_config, "threshold_grid")
            or _get(parent_config, "threshold_selection")
            != _get(child_config, "threshold_selection")
        ),
        "OBJECTIVE_CHANGED": _get(parent_config, "loss", "name")
        != _get(child_config, "loss", "name"),
    }
    expected_true = {"OBJECTIVE_CHANGED"}
    unexpected = {
        key: value
        for key, value in checks.items()
        if (key in expected_true and not value) or (key not in expected_true and value)
    }
    # Parent loss forbids focal; child allows experiment-scoped focal — expected.
    parent_forbidden = set(_get(parent_config, "loss", "forbidden") or [])
    child_forbidden = set(_get(child_config, "loss", "forbidden") or [])
    focal_exception_ok = (
        "focal" in parent_forbidden
        and "focal" not in child_forbidden
        and _get(child_config, "loss", "ALLOW_FOCAL_LOSS_FOR") == EXPERIMENT_ID
        and float(_get(child_config, "loss", "gamma")) == FOCAL_GAMMA
        and _get(child_config, "loss", "alpha_policy") == FOCAL_ALPHA_POLICY
    )
    status = "PASS" if not unexpected and focal_exception_ok else "FAIL"
    return {
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "PARENT_EXPERIMENT": PARENT_EXPERIMENT_ID,
        "SINGLE_FACTOR_DIFF_STATUS": status,
        "checks": checks,
        "expected_true": sorted(expected_true),
        "focal_exception_ok": focal_exception_ok,
        "unexpected": unexpected,
        "schema": "hyperlex.classification.v5.stage_a_003_single_factor_diff.v1",
    }


def authorization_contract_003(
    *,
    dataset_sha256: str,
    training_config_sha256: str,
    focal_loss_spec_sha256: str,
    code_revision: str,
    single_factor_diff_status: str,
    implementation_tests: Mapping[str, str],
) -> dict[str, Any]:
    tests_pass = all(
        value == "PASS"
        for key, value in implementation_tests.items()
        if key
        in {
            "GAMMA_ZERO_EQUIVALENCE",
            "EASY_EXAMPLE_DOWNWEIGHT",
            "HARD_EXAMPLE_EMPHASIS",
            "CLASS_WEIGHT_PRESERVATION",
            "PROVENANCE_WEIGHT_PRESERVATION",
            "FINITE_LOSS_EXTREME_LOGITS",
            "FOCAL_LOSS_IMPLEMENTATION_TEST",
        }
    )
    ready = (
        tests_pass
        and single_factor_diff_status == "PASS"
        and bool(focal_loss_spec_sha256)
        and bool(training_config_sha256)
    )
    return {
        "ACCEPTANCE_GATES": dict(ACCEPTANCE_GATES),
        "ALLOW_FOCAL_LOSS_FOR": EXPERIMENT_ID,
        "BEST": "UNCHANGED",
        "BEST_MUTATED": False,
        "CHECKPOINT_SELECTION": dict(CHECKPOINT_SELECTION),
        "CODE_REVISION": code_revision,
        "CURRENT_BEST": BEST_SHA,
        "DATASET_SHA256": dataset_sha256,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "FOCAL_ALPHA_POLICY": FOCAL_ALPHA_POLICY,
        "FOCAL_GAMMA": FOCAL_GAMMA,
        "FOCAL_LOSS_SPEC_SHA256": focal_loss_spec_sha256,
        "H1_OBJECTIVE_LOSS_PRESSURE": "NOT_TESTED",
        "IMPLEMENTATION_TESTS": dict(implementation_tests),
        "LABEL_PROVENANCE_RULE": LABEL_PROVENANCE_RULE,
        "NEXT_ACTION": (
            "TRAIN_V5_STAGE_A_003_FOCAL_LOSS_ONCE" if ready else "STOP_OBJECTIVE_NOT_READY"
        ),
        "OBJECTIVE_STATE": "FROZEN" if ready else "NOT_READY",
        "PARENT_EXPERIMENT": PARENT_EXPERIMENT_ID,
        "PARENT_TRAINING_CONFIG_SHA256": PARENT_TRAINING_CONFIG_SHA256,
        "RESERVE": "unused",
        "RESERVE_CONSUMED": False,
        "RULE": STAGE_A_RULE,
        "SCIENTIFIC_RESULT": "NOT_COMPUTABLE",
        "SEED": int(TRAIN_HYPERPARAMS["seed"]),
        "SINGLE_FACTOR_DIFF_STATUS": single_factor_diff_status,
        "SURFACE_RULE": AUTHORIZED_SURFACE_RULE,
        "THRESHOLD_GRID": dict(THRESHOLD_GRID),
        "THRESHOLD_SELECTION": dict(THRESHOLD_SELECTION),
        "TRAIN": False,
        "TRAINING_AUTHORIZATION": (
            "AUTHORIZED_V5_STAGE_A_003_FOCAL_LOSS_ONCE" if ready else False
        ),
        "TRAINING_CONFIG_SHA256": training_config_sha256,
        "TRAINING_RUN_LIMIT": 1,
        "TRAINING_STATUS": (
            "AUTHORIZED_NOT_STARTED" if ready else "BLOCKED_OBJECTIVE_NOT_READY"
        ),
        "UNCERTAIN_POLICY_INVESTIGATION_PENDING": True,
        "schema": "hyperlex.classification.v5.stage_a_003_focal_authorization.v1",
    }


def finite_or_raise(values: Sequence[float], *, label: str) -> None:
    for value in values:
        if not math.isfinite(float(value)):
            raise ValueError(f"non_finite_{label}:{value}")
