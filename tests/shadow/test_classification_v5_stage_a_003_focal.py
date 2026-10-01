"""Stage-A-003 focal objective implementation tests. No model training."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import torch

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "shadow"))

from hyperlexical.classification_v5_stage_a import (  # noqa: E402
    EVIDENCE_LABELS,
    PROVENANCE_LOSS_MULTIPLIERS,
    build_resolved_training_config,
)
from hyperlexical.classification_v5_stage_a_003_focal import (  # noqa: E402
    CLASS_WEIGHT_POLICY,
    EXPERIMENT_ID,
    FOCAL_ALPHA_POLICY,
    FOCAL_GAMMA,
    PARENT_EXPERIMENT_ID,
    PROVENANCE_MULTIPLIER_POLICY,
    build_objective_spec,
    build_resolved_training_config_003,
    class_weight_tensor,
    reduce_mean,
    single_factor_diff,
    weighted_cross_entropy_per_example,
    weighted_focal_cross_entropy_per_example,
)

# Frozen Stage-A-002 class weights (V1R8).
CLASS_WEIGHTS = {
    "EVIDENCE_PRESENT": 0.871574519528987,
    "NO_EVIDENCE": 0.5,
    "UNCERTAIN": 1.7466788753540448,
}


def _logits_for_pt(pt: float, target: int = 1, n_class: int = 3) -> torch.Tensor:
    """Construct logits so softmax(target) ≈ pt (other mass uniform)."""
    pt = float(pt)
    if not (0.0 < pt < 1.0):
        raise ValueError("pt_out_of_open_unit_interval")
    other = (1.0 - pt) / (n_class - 1)
    # log-prob targets → logits up to additive constant
    log_probs = [math_log(other)] * n_class
    log_probs[target] = math_log(pt)
    return torch.tensor([log_probs], dtype=torch.float64)


def math_log(x: float) -> float:
    import math

    return math.log(x)


def test_frozen_focal_constants():
    assert EXPERIMENT_ID == "HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS"
    assert PARENT_EXPERIMENT_ID == "HLX-CLASSIFICATION-V5-STAGE-A-002"
    assert FOCAL_GAMMA == 2.0
    assert FOCAL_ALPHA_POLICY == "NONE"
    assert CLASS_WEIGHT_POLICY == "UNCHANGED_FROM_STAGE_A_002"
    assert PROVENANCE_MULTIPLIER_POLICY == "UNCHANGED_FROM_STAGE_A_002"


def test_gamma_zero_equivalence():
    torch.manual_seed(0)
    logits = torch.randn(16, len(EVIDENCE_LABELS), dtype=torch.float64)
    targets = torch.randint(0, len(EVIDENCE_LABELS), (16,))
    prov = torch.tensor(
        [PROVENANCE_LOSS_MULTIPLIERS["OBSERVED"]] * 8
        + [PROVENANCE_LOSS_MULTIPLIERS["INFERRED"]] * 8,
        dtype=torch.float64,
    )
    cw = class_weight_tensor(CLASS_WEIGHTS).to(dtype=torch.float64)
    base = weighted_cross_entropy_per_example(logits, targets, cw, prov)
    focal0 = weighted_focal_cross_entropy_per_example(
        logits, targets, cw, prov, gamma=0.0
    )
    assert torch.allclose(focal0, base, rtol=0.0, atol=1e-12)
    assert torch.allclose(
        reduce_mean(focal0), reduce_mean(base), rtol=0.0, atol=1e-12
    )


def test_easy_example_downweight():
    cw = class_weight_tensor(CLASS_WEIGHTS).to(dtype=torch.float64)
    prov = torch.tensor([1.0], dtype=torch.float64)
    target = 1  # EVIDENCE_PRESENT
    easy_logits = _logits_for_pt(0.95, target=target).to(dtype=torch.float64)
    hard_logits = _logits_for_pt(0.20, target=target).to(dtype=torch.float64)
    easy_pt = torch.softmax(easy_logits, dim=-1)[0, target]
    hard_pt = torch.softmax(hard_logits, dim=-1)[0, target]
    easy_mod = (1.0 - easy_pt).pow(FOCAL_GAMMA)
    hard_mod = (1.0 - hard_pt).pow(FOCAL_GAMMA)
    assert easy_mod < hard_mod
    easy_focal = weighted_focal_cross_entropy_per_example(
        easy_logits, torch.tensor([target]), cw, prov, gamma=FOCAL_GAMMA
    )
    hard_focal = weighted_focal_cross_entropy_per_example(
        hard_logits, torch.tensor([target]), cw, prov, gamma=FOCAL_GAMMA
    )
    easy_base = weighted_cross_entropy_per_example(
        easy_logits, torch.tensor([target]), cw, prov
    )
    hard_base = weighted_cross_entropy_per_example(
        hard_logits, torch.tensor([target]), cw, prov
    )
    assert (easy_focal / easy_base) < (hard_focal / hard_base)


def test_hard_example_emphasis():
    cw = class_weight_tensor(CLASS_WEIGHTS).to(dtype=torch.float64)
    prov = torch.ones(2, dtype=torch.float64)
    # example0 correct/easy PRESENT; example1 wrong/hard (mass on NONE)
    logits = torch.tensor(
        [
            [0.0, 5.0, 0.0],
            [5.0, 0.0, 0.0],
        ],
        dtype=torch.float64,
    )
    targets = torch.tensor([1, 1])  # both gold PRESENT
    base = weighted_cross_entropy_per_example(logits, targets, cw, prov)
    focal = weighted_focal_cross_entropy_per_example(
        logits, targets, cw, prov, gamma=FOCAL_GAMMA
    )
    # Hard/misclassified retains greater share of batch loss under focal than CE.
    base_share_hard = base[1] / base.sum()
    focal_share_hard = focal[1] / focal.sum()
    assert focal_share_hard > base_share_hard
    assert focal[1] > focal[0]


def test_class_weight_preservation():
    logits = torch.zeros(3, 3, dtype=torch.float64)
    targets = torch.tensor([0, 1, 2])
    prov = torch.ones(3, dtype=torch.float64)
    cw = class_weight_tensor(CLASS_WEIGHTS).to(dtype=torch.float64)
    focal = weighted_focal_cross_entropy_per_example(
        logits, targets, cw, prov, gamma=FOCAL_GAMMA
    )
    # Uniform logits → equal p_t; de-weighted focal must be identical across labels.
    deweighted = focal / cw
    assert torch.allclose(deweighted, deweighted[0].expand_as(deweighted), rtol=0, atol=1e-12)
    # Scaling class weight scales loss for that example.
    cw2 = cw.clone()
    cw2[1] = cw2[1] * 2.0
    focal2 = weighted_focal_cross_entropy_per_example(
        logits, targets, cw2, prov, gamma=FOCAL_GAMMA
    )
    assert abs(float(focal2[1] / focal[1]) - 2.0) < 1e-12


def test_provenance_weight_preservation():
    logits = torch.zeros(2, 3, dtype=torch.float64)
    targets = torch.tensor([1, 1])
    cw = class_weight_tensor(CLASS_WEIGHTS).to(dtype=torch.float64)
    prov = torch.tensor(
        [
            PROVENANCE_LOSS_MULTIPLIERS["OBSERVED"],
            PROVENANCE_LOSS_MULTIPLIERS["INFERRED"],
        ],
        dtype=torch.float64,
    )
    focal = weighted_focal_cross_entropy_per_example(
        logits, targets, cw, prov, gamma=FOCAL_GAMMA
    )
    assert abs(float(focal[1] / focal[0]) - 0.5) < 1e-9


def test_finite_extreme_logits():
    cw = class_weight_tensor(CLASS_WEIGHTS).to(dtype=torch.float64)
    prov = torch.tensor([1.0, 0.5], dtype=torch.float64)
    logits = torch.tensor(
        [
            [0.0, 80.0, 0.0],  # extremely confident correct PRESENT
            [80.0, 0.0, 0.0],  # extremely confident incorrect
        ],
        dtype=torch.float64,
    )
    targets = torch.tensor([1, 1])
    focal = weighted_focal_cross_entropy_per_example(
        logits, targets, cw, prov, gamma=FOCAL_GAMMA
    )
    assert torch.isfinite(focal).all()
    assert torch.isfinite(reduce_mean(focal))


def test_objective_spec_hash_stable():
    a = build_objective_spec()
    b = build_objective_spec()
    assert a["FOCAL_GAMMA"] == 2.0
    assert a["FOCAL_ALPHA_POLICY"] == "NONE"
    assert a["FOCAL_LOSS_SPEC_SHA256"] == b["FOCAL_LOSS_SPEC_SHA256"]
    assert len(a["FOCAL_LOSS_SPEC_SHA256"]) == 64


def test_single_factor_diff_pass():
    cw_report = {
        "class_weights": dict(CLASS_WEIGHTS),
        "provenance_multipliers": dict(PROVENANCE_LOSS_MULTIPLIERS),
        "effective_counts": {
            "EVIDENCE_PRESENT": 371.5,
            "NO_EVIDENCE": 1936.5,
            "UNCERTAIN": 92.5,
        },
        "normalized_weights": dict(CLASS_WEIGHTS),
        "policy": {"clip_max": 2.0, "clip_min": 0.5},
        "raw_weights": dict(CLASS_WEIGHTS),
    }
    parent = build_resolved_training_config(
        dataset_sha256="c0fdd82d1734585a7d852318ac5b390cc5e2c50908c0ef9f9eba4b3f7ebedc8b",
        class_weight_report=cw_report,
        code_revision="deadbeef",
        tokenizer_identity="local_files_only:ModernBERT-base",
        surface_rule="HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R8",
    )
    spec = build_objective_spec()
    child = build_resolved_training_config_003(
        dataset_sha256=parent["dataset_sha256"],
        class_weight_report=cw_report,
        code_revision="deadbeef",
        tokenizer_identity="local_files_only:ModernBERT-base",
        focal_loss_spec_sha256=spec["FOCAL_LOSS_SPEC_SHA256"],
    )
    diff = single_factor_diff(parent, child)
    assert diff["SINGLE_FACTOR_DIFF_STATUS"] == "PASS"
    assert diff["checks"]["OBJECTIVE_CHANGED"] is True
    assert diff["checks"]["CLASS_WEIGHTS_CHANGED"] is False
    assert diff["checks"]["DECISION_LOGIC_CHANGED"] is False
    assert child["loss"]["gamma"] == 2.0
    assert child["loss"]["alpha_policy"] == "NONE"
    assert "focal" not in child["loss"]["forbidden"]
    assert "focal" in parent["loss"]["forbidden"]
