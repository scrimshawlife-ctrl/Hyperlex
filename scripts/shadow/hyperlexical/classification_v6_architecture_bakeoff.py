"""V6 architecture bake-off contracts and metrics (no retrieval-first core).

Tracks:
  A — shared encoder + independent sigmoid heads + hierarchy constraints
  B — A + hierarchy-aware label attention
  C — B + supervised contrastive / text-label alignment term
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v6_label_migration import (
    DOMAIN_VOCAB,
    FUNCTION_VOCAB,
    MEDIATION_VOCAB,
    hierarchy_violation,
)

PHASE_RULE = "REBUILD_V6_LABELS_AND_RUN_ARCHITECTURE_BAKEOFF"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-LABEL-MIGRATION-BAKEOFF-001"
SCHEMA = "hyperlex.classification.v6.architecture_bakeoff.v1"

CONTROL_ENCODER_SHA = MODEL_WIDE_BEST_SHA256

TRACKS = ("A_BASELINE_MULTIHEAD", "B_HIERARCHY_AWARE", "C_REPRESENTATION_AWARE")

PREREGISTERED_METRICS = {
    "DOMAIN": ["micro_f1", "macro_f1", "per_label_precision_recall"],
    "FUNCTION": ["micro_f1", "macro_f1"],
    "MEDIATION": ["per_label_precision_recall"],
    "HIERARCHY": [
        "parent_child_consistency",
        "hierarchical_precision_recall_f1",
        "hierarchy_violation_rate",
    ],
    "SYSTEM": [
        "exact_label_set_match",
        "jaccard",
        "sample_f1",
        "abstention",
        "Stage_A_induced_errors",
        "Stage_B_induced_errors",
        "compound_errors",
    ],
    "GENERALIZATION": ["DEV_metrics", "REP_metrics", "DEV_to_REP_delta"],
}

NON_NEGOTIABLE = {
    "ai_discourse_requires_technology": True,
    "violation_example": "ai_discourse=true && technology=false → structural error",
}

GENERALIZATION_GAP_GATE = {
    "name": "GENERALIZATION_GAP_ACCEPTABLE",
    "rule": (
        "Candidate may not advance on DEV improvement alone. "
        "Material REP degradation vs DEV is a first-class failure."
    ),
    "max_macro_f1_dev_minus_rep": 0.15,
}


def multilabel_f1(
    gold: Sequence[Sequence[int]], pred: Sequence[Sequence[int]]
) -> dict[str, float]:
    import numpy as np

    g = np.asarray(gold, dtype=np.float64)
    p = np.asarray(pred, dtype=np.float64)
    if g.size == 0:
        return {"micro_f1": 0.0, "macro_f1": 0.0, "sample_f1": 0.0, "exact_match": 0.0, "jaccard": 0.0}
    # micro
    tp = (g * p).sum()
    fp = ((1 - g) * p).sum()
    fn = (g * (1 - p)).sum()
    micro = float(2 * tp / max(1e-9, 2 * tp + fp + fn))
    # macro
    f1s = []
    for j in range(g.shape[1]):
        tpj = (g[:, j] * p[:, j]).sum()
        fpj = ((1 - g[:, j]) * p[:, j]).sum()
        fnj = (g[:, j] * (1 - p[:, j])).sum()
        f1s.append(float(2 * tpj / max(1e-9, 2 * tpj + fpj + fnj)))
    macro = float(sum(f1s) / max(1, len(f1s)))
    # sample
    s_f1 = []
    jacs = []
    exact = 0
    for i in range(g.shape[0]):
        gi, pi = g[i], p[i]
        inter = (gi * pi).sum()
        union = ((gi + pi) > 0).sum()
        prec = inter / max(1e-9, pi.sum())
        rec = inter / max(1e-9, gi.sum())
        s_f1.append(float(2 * prec * rec / max(1e-9, prec + rec)) if (prec + rec) > 0 else (1.0 if gi.sum() == 0 and pi.sum() == 0 else 0.0))
        jacs.append(float(inter / max(1e-9, union)) if union > 0 else 1.0)
        if (gi == pi).all():
            exact += 1
    return {
        "micro_f1": micro,
        "macro_f1": macro,
        "sample_f1": float(sum(s_f1) / max(1, len(s_f1))),
        "exact_match": exact / max(1, g.shape[0]),
        "jaccard": float(sum(jacs) / max(1, len(jacs))),
    }


def hierarchy_metrics(
    domain_gold: Sequence[Sequence[int]],
    domain_pred: Sequence[Sequence[int]],
    *,
    tech_idx: int,
    ai_idx: int,
) -> dict[str, float]:
    viol = 0
    n = 0
    for row in domain_pred:
        n += 1
        if row[ai_idx] == 1 and row[tech_idx] == 0:
            viol += 1
    # hierarchical: count AI correct only if parent also predicted when AI gold
    tp = fp = fn = 0
    for g, p in zip(domain_gold, domain_pred):
        # evaluate ai leaf with parent consistency requirement on prediction
        g_ai = g[ai_idx]
        p_ai = 1 if (p[ai_idx] == 1 and p[tech_idx] == 1) else 0
        tp += int(g_ai == 1 and p_ai == 1)
        fp += int(g_ai == 0 and p_ai == 1)
        fn += int(g_ai == 1 and p_ai == 0)
    h_f1 = float(2 * tp / max(1e-9, 2 * tp + fp + fn))
    return {
        "hierarchy_violation_rate": viol / max(1, n),
        "parent_child_consistency": 1.0 - (viol / max(1, n)),
        "hierarchical_f1_ai_discourse": h_f1,
    }


def bakeoff_contract() -> dict[str, Any]:
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "tracks": list(TRACKS),
        "control_encoder_sha256": CONTROL_ENCODER_SHA,
        "control_role": "CONTROL_NOT_ASSUMED_BACKBONE",
        "heads": {
            "domain": DOMAIN_VOCAB,
            "function": FUNCTION_VOCAB,
            "mediation": MEDIATION_VOCAB,
        },
        "constraints": NON_NEGOTIABLE,
        "metrics": PREREGISTERED_METRICS,
        "generalization_gap_gate": GENERALIZATION_GAP_GATE,
        "retrieval_first_core": False,
        "llm_as_gold_ontology_authority": False,
        "identical_budget_note": (
            "Tracks share splits, optimizer family, epoch budget, and thresholding "
            "policy; encoder swaps are controlled separately."
        ),
        "schema": SCHEMA,
    }


def generalization_gap_pass(dev_macro: float, rep_macro: float) -> bool:
    return (dev_macro - rep_macro) <= GENERALIZATION_GAP_GATE["max_macro_f1_dev_minus_rep"]


def select_candidate(results: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Select among tracks using DEV+REP; reject DEV-only winners."""
    ranked = []
    for track, r in results.items():
        dev = float(r.get("DEV", {}).get("system", {}).get("macro_f1") or 0)
        rep = float(r.get("REP", {}).get("system", {}).get("macro_f1") or 0)
        viol = float(r.get("REP", {}).get("hierarchy", {}).get("hierarchy_violation_rate") or 1)
        gap_ok = generalization_gap_pass(dev, rep)
        score = rep - 0.5 * max(0.0, viol) + (0.05 if gap_ok else -0.20)
        ranked.append(
            {
                "track": track,
                "dev_macro_f1": dev,
                "rep_macro_f1": rep,
                "hierarchy_violation_rate_rep": viol,
                "GENERALIZATION_GAP_ACCEPTABLE": gap_ok,
                "selection_score": score,
            }
        )
    ranked.sort(key=lambda x: -x["selection_score"])
    winner = ranked[0] if ranked else None
    return {
        "ranking": ranked,
        "selected": winner["track"] if winner and winner["GENERALIZATION_GAP_ACCEPTABLE"] else None,
        "selection_rule": "maximize REP macro-F1 with hierarchy penalty; require GENERALIZATION_GAP_ACCEPTABLE",
        "advance": bool(winner and winner["GENERALIZATION_GAP_ACCEPTABLE"]),
    }
