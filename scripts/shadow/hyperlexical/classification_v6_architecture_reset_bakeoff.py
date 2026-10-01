"""V6 architecture-reset bake-off (tracks D/E/F) — no A/B/C retuning.

Label descriptions come only from HYPERLEX_V6_FAMILY_ONTOLOGY_V1_FINAL.
QUAL remains sealed. Advancement floors are not lowered.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
from .classification_v6_architecture_bakeoff import (
    GENERALIZATION_GAP_GATE as _PRIOR_GAP,
    _metric,
    generalization_gap_pass,
    hierarchy_metrics,
    multilabel_f1,
)
from .classification_v6_label_migration import (
    DOMAIN_VOCAB,
    FUNCTION_VOCAB,
    MEDIATION_VOCAB,
)

PHASE_RULE = "CONTINUE_V6_ARCHITECTURE_BAKEOFF"
EXPERIMENT_ID = "HLX-CLASSIFICATION-V6-ARCHITECTURE-RESET-BAKEOFF-001"
SCHEMA = "hyperlex.classification.v6.architecture_reset_bakeoff.v1"
PRIOR_RECEIPT = "b936b49bbf0e3925a03f2c1bb6eb46bf7458c7a2f1e215f83cc6536266d2d453"

CONTROL_ENCODER_SHA = MODEL_WIDE_BEST_SHA256
TRACKS = (
    "D_LABEL_DESCRIPTION_NLI",
    "E_LABEL_EMBEDDING_JOINT",
    "F_HIERARCHY_AWARE_CONTRASTIVE",
)

# Frozen natural-language definitions from settled ontology contract only.
LABEL_DESCRIPTIONS: dict[str, str] = {
    "domain.gaming": (
        "DOMAIN gaming: gameplay / gamer-community evidence. "
        "Exclusions: generic 'player' without game sense; sports athletes; AI agents."
    ),
    "domain.gambling": (
        "DOMAIN gambling_betting: actual betting/wagering/casino/bookmaking semantics. "
        "Exclusions: metaphorical 'bet', speculative-market talk without wagering, "
        "ordinary coin minting, storage 'bit' units."
    ),
    "domain.crypto": (
        "DOMAIN crypto_markets: crypto-asset / blockchain / DeFi / NFT market evidence. "
        "Exclusions: ordinary finance, generic 'token' without crypto sense."
    ),
    "domain.sports": (
        "DOMAIN sports: athletic sports evidence. "
        "Exclusions: gaming esports; figurative competition alone."
    ),
    "domain.entertainment": (
        "DOMAIN entertainment_media: music / film / TV entertainment evidence. "
        "Exclusions: generic 'performance' in computing; fashion runway alone."
    ),
    "domain.fashion": (
        "DOMAIN fashion_style: clothing / aesthetic-style evidence. "
        "Exclusions: abstract 'aesthetic' philosophy without style sense."
    ),
    "domain.workplace": (
        "DOMAIN workplace: workplace / career / org evidence. "
        "Exclusions: generic 'service'/'channel' without workplace sense."
    ),
    "domain.politics": (
        "DOMAIN politics_civic: political / civic institutional evidence. "
        "Exclusions: generic conflict/war without civic framing; sports 'left wing'."
    ),
    "domain.spiritual": (
        "DOMAIN spiritual_esoteric: occult / astrology / spiritual practice evidence. "
        "Exclusions: metaphorical 'magic' in tech/gaming without spiritual sense."
    ),
    "domain.technology": (
        "DOMAIN technology: computing / software / systems evidence. "
        "Exclusions: AI-community slang that is specifically model/agent discourse."
    ),
    "domain.technology.ai_discourse": (
        "DOMAIN ai_discourse (child of technology): AI-agent / LLM / prompt community "
        "evidence. Requires technology parent. Exclusions: generic computing without "
        "AI-community evidence."
    ),
    "function.evaluative_stance": (
        "FUNCTION evaluative_stance: praise / insult / pejoration / prestige judgment. "
        "Exclusions: neutral description without stance; pure demonym without evaluation."
    ),
    "function.relational_intimacy": (
        "FUNCTION relational_intimacy: romantic / dating / intimate partnership evidence. "
        "Exclusions: platonic affiliation; workplace 'partner'; evaluative insult alone."
    ),
    "function.conflictive_force": (
        "FUNCTION conflictive_force: hostility / violence / combat framing. "
        "Exclusions: metaphorical 'fight' for sports/competition without hostility sense."
    ),
    "function.memetic_form": (
        "FUNCTION memetic_form: meme format / macro / copypasta / template virality. "
        "Exclusions: any viral topic without memetic form; political content alone."
    ),
    "mediation.internet_register": (
        "MEDIATION internet_register: internet-mediated informal register / netspeak. "
        "Optional co-label; must not be sole exclusive Stage-B decision."
    ),
}

AXIS_VOCABS = {
    "domain": DOMAIN_VOCAB,
    "function": FUNCTION_VOCAB,
    "mediation": MEDIATION_VOCAB,
}

ADVANCEMENT_GATE = {
    "name": "V6_ARCHITECTURE_RESET_ADVANCEMENT",
    "min_rep_system_macro_f1": float(_PRIOR_GAP["min_rep_system_macro_f1"]),
    "max_hierarchy_violation_rate_rep": float(
        _PRIOR_GAP["max_hierarchy_violation_rate_rep"]
    ),
    "max_macro_f1_dev_minus_rep": float(_PRIOR_GAP["max_macro_f1_dev_minus_rep"]),
    "min_axis_macro_f1": 0.10,
    "material_axes": ("domain", "function", "mediation"),
    "floors_locked": True,
    "note": "Do not lower floors after results. QUAL sealed.",
}

ERROR_CLASSES = (
    "ENCODER_SEPARATION_FAILURE",
    "LABEL_DESCRIPTION_CONFUSION",
    "PARENT_CHILD_CONSISTENCY_FAILURE",
    "FALSE_POSITIVE_LABEL",
    "FALSE_NEGATIVE_LABEL",
    "CO_LABEL_FAILURE",
    "AXIS_CONFUSION",
    "ANNOTATION_BOUNDARY_CASE",
)

FAILURE_DIAGNOSES = (
    "ENCODER_REPRESENTATION_FAILURE",
    "ATOMIC_LABEL_HEAD_FAILURE",
    "LABEL_SEMANTICS_MISSING",
    "HIERARCHY_OBJECTIVE_FAILURE",
    "TASK_NOT_LEARNABLE_AT_CURRENT_DATA_SCALE",
    "DATA_SCALE_INSUFFICIENT",
    "LABEL_BOUNDARIES_STILL_NOT_MODEL_LEARNABLE",
    "TEXT_ONLY_SIGNAL_INSUFFICIENT",
    "PRETRAINED_REPRESENTATION_MISMATCH",
    "TASK_REDEFINITION_REQUIRED",
    "LABEL_SEMANTICS_PRIOR_STRONGER_THAN_CURRENT_TRAINED_REPRESENTATION",
)


def frozen_label_descriptions() -> dict[str, str]:
    """Return ontology-contract label descriptions (immutable copy)."""
    missing = [
        lab
        for lab in DOMAIN_VOCAB + FUNCTION_VOCAB + MEDIATION_VOCAB
        if lab not in LABEL_DESCRIPTIONS
    ]
    if missing:
        raise ValueError(f"missing frozen label descriptions: {missing}")
    return dict(LABEL_DESCRIPTIONS)


def bakeoff_contract() -> dict[str, Any]:
    return {
        "PHASE_RULE": PHASE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "schema": SCHEMA,
        "prior_bakeoff_receipt": PRIOR_RECEIPT,
        "prior_state": "V6_BAKEOFF_NO_ADVANCE",
        "tracks": list(TRACKS),
        "track_purposes": {
            "D_LABEL_DESCRIPTION_NLI": (
                "text-label entailment / compatibility using frozen label definitions"
            ),
            "E_LABEL_EMBEDDING_JOINT": (
                "shared space for text and label definitions + multi-label objective"
            ),
            "F_HIERARCHY_AWARE_CONTRASTIVE": (
                "instance/label/hierarchy-structured contrastive representation"
            ),
        },
        "encoder_controls": {
            "CONTROL": {
                "id": "MODEL_WIDE_BEST_CONTROL",
                "sha256": CONTROL_ENCODER_SHA,
                "role": "CONTROL_NOT_ASSUMED_BACKBONE",
            },
            "EXTERNAL_ENCODER_CONTROL": {
                "id": "MODERNBERT_TRUNK_NO_HYPERLEX_ADAPTATION",
                "role": "GENERAL_PRETRAINED_NO_HYPERLEX_FINETUNE",
                "note": "Same ModernBERT trunk weights; no MODEL_WIDE_BEST adaptation.",
            },
        },
        "label_descriptions_source": "HYPERLEX_V6_FAMILY_ONTOLOGY_V1_FINAL",
        "label_descriptions": frozen_label_descriptions(),
        "zero_shot_diagnostic": {
            "name": "TEXT_LABEL_DESCRIPTION_SEMANTIC_MATCHING",
            "trainable": False,
            "purpose": "read-only prior before expensive D/E/F training",
        },
        "advancement_gate": ADVANCEMENT_GATE,
        "error_classes": list(ERROR_CLASSES),
        "failure_diagnoses": list(FAILURE_DIAGNOSES),
        "qual_policy": {
            "HYPERLEX_V6_QUALIFICATION_001": "REMAIN_SEALED_HISTORICAL_SECONDARY",
            "inspected": False,
            "forbidden_uses": [
                "selection",
                "thresholding",
                "early_stopping",
                "architecture_choice",
                "diagnosis",
            ],
        },
        "forbidden": [
            "incremental_ABC_tuning",
            "inspect_QUAL",
            "modify_ontology",
            "alter_migration_gold",
            "tune_REP_row_by_row",
            "lower_advancement_floors",
            "llm_generated_label_reinterpretation",
            "legacy_stage_b_exemplar_index",
        ],
        "retrieval_first_core": False,
        "identical_budget_note": (
            "Tracks share TRAIN/DEV/REP, ontology, label definitions, metric code, "
            "advancement gates, seed policy, and training budget class."
        ),
    }


def axis_floors_pass(rep_axes: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Require each materially supported axis macro-F1 >= floor."""
    floor = ADVANCEMENT_GATE["min_axis_macro_f1"]
    details = {}
    ok = True
    for axis in ADVANCEMENT_GATE["material_axes"]:
        block = rep_axes.get(axis) or {}
        n_pos = int(block.get("n_positive_labels") or block.get("support_positives") or 0)
        macro = float(block.get("macro_f1") or 0.0)
        # Mediation may be sparse; still material if any positives observed.
        material = axis in ("domain", "function") or n_pos > 0 or "macro_f1" in block
        axis_ok = (not material) or (macro >= floor)
        details[axis] = {
            "material": material,
            "macro_f1": macro,
            "floor": floor,
            "ok": axis_ok,
        }
        if material and not axis_ok:
            ok = False
    return {"ok": ok, "axes": details}


def select_reset_candidate(results: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Select among D/E/F (+ optional encoder suffix) using locked floors."""
    ranked: list[dict[str, Any]] = []
    for track, r in results.items():
        if track.startswith("ZERO_SHOT") or track.startswith("DIAGNOSTIC"):
            continue
        dev = _metric(r, "DEV", "system", "macro_f1")
        rep = _metric(r, "REP", "system", "macro_f1")
        viol = _metric(r, "REP", "hierarchy", "hierarchy_violation_rate", default=1.0)
        gap_ok = generalization_gap_pass(dev, rep)
        abs_ok = rep >= ADVANCEMENT_GATE["min_rep_system_macro_f1"]
        hier_ok = viol <= ADVANCEMENT_GATE["max_hierarchy_violation_rate_rep"]
        axis_rep = {
            "domain": r.get("REP", {}).get("domain") or {},
            "function": r.get("REP", {}).get("function") or {},
            "mediation": r.get("REP", {}).get("mediation") or {},
        }
        axis_gate = axis_floors_pass(axis_rep)
        eligible = gap_ok and abs_ok and hier_ok and axis_gate["ok"]
        # Preference order: REP, gap, hierarchy, axis balance, simplicity, cost
        gap = max(0.0, dev - rep)
        axis_macros = [float((axis_rep[a] or {}).get("macro_f1") or 0.0) for a in ("domain", "function", "mediation")]
        axis_balance = 1.0 - (max(axis_macros) - min(axis_macros) if axis_macros else 1.0)
        simplicity = {"D": 0.03, "E": 0.02, "F": 0.01}.get(track[:1], 0.0)
        score = (
            rep
            - 0.25 * gap
            - 0.5 * max(0.0, viol)
            + 0.05 * axis_balance
            + simplicity
            + (0.05 if eligible else -0.25)
        )
        ranked.append(
            {
                "track": track,
                "dev_macro_f1": dev,
                "rep_macro_f1": rep,
                "dev_rep_gap": gap,
                "hierarchy_violation_rate_rep": viol,
                "GENERALIZATION_GAP_ACCEPTABLE": gap_ok,
                "ABS_REP_FLOOR_OK": abs_ok,
                "HIERARCHY_OK": hier_ok,
                "AXIS_FLOOR_OK": axis_gate["ok"],
                "axis_gate": axis_gate,
                "eligible": eligible,
                "selection_score": score,
            }
        )
    ranked.sort(key=lambda x: -x["selection_score"])
    eligible = [x for x in ranked if x["eligible"]]
    winner = eligible[0] if eligible else None
    advance = winner is not None
    return {
        "ranking": ranked,
        "selected": winner["track"] if winner else None,
        "advance": advance,
        "selection_rule": (
            "prefer REP system, then DEV→REP gap, hierarchy, axis balance, "
            "simplicity; require locked floors including axis macro-F1>=0.10"
        ),
        "BAKEOFF_STATE": (
            "V6_ARCHITECTURE_RESET_CANDIDATE_SELECTED"
            if advance
            else "V6_ARCHITECTURE_BAKEOFF_EXHAUSTED"
        ),
        "NEXT_ACTION": (
            "HARDEN_V6_SELECTED_ARCHITECTURE_AND_PREPARE_QUALIFICATION"
            if advance
            else "REASSESS_V6_TASK_SIGNAL_AND_PRETRAINED_REPRESENTATION"
        ),
    }


def diagnose_exhaustion(
    *,
    results: Mapping[str, Mapping[str, Any]],
    zero_shot: Mapping[str, Any] | None,
    abc_best_rep: float = 0.023839137645107797,
) -> dict[str, Any]:
    """Map D/E/F + zero-shot evidence to a primary failure diagnosis."""
    trained = {
        k: v
        for k, v in results.items()
        if not k.startswith("ZERO_SHOT") and not k.startswith("DIAGNOSTIC")
    }
    best_rep = 0.0
    best_track = None
    axis_best = {"domain": 0.0, "function": 0.0, "mediation": 0.0}
    for track, r in trained.items():
        rep = _metric(r, "REP", "system", "macro_f1")
        if rep >= best_rep:
            best_rep = rep
            best_track = track
        for axis in axis_best:
            axis_best[axis] = max(
                axis_best[axis], _metric(r, "REP", axis, "macro_f1")
            )
    zs_rep = float((zero_shot or {}).get("REP", {}).get("system", {}).get("macro_f1") or 0.0)
    zs_stronger = zs_rep > max(abc_best_rep, best_rep) + 0.02
    d_tracks = [k for k in trained if k.startswith("D_")]
    d_best = max((_metric(trained[k], "REP", "system", "macro_f1") for k in d_tracks), default=0.0)

    primary = "TASK_NOT_LEARNABLE_AT_CURRENT_DATA_SCALE"
    evidence: list[str] = []
    if zs_stronger:
        primary = "LABEL_SEMANTICS_PRIOR_STRONGER_THAN_CURRENT_TRAINED_REPRESENTATION"
        evidence.append(
            f"zero-shot REP macro-F1={zs_rep:.4f} > trained/ABC (~{max(abc_best_rep, best_rep):.4f})"
        )
    elif d_best < 0.05 and best_rep < 0.05:
        primary = "TEXT_ONLY_SIGNAL_INSUFFICIENT"
        evidence.append(
            "Track D (explicit label semantics) and other tracks remain near chance on REP"
        )
        if max(axis_best.values()) < 0.05:
            primary = "LABEL_BOUNDARIES_STILL_NOT_MODEL_LEARNABLE"
            evidence.append("all axes remain below 0.05 macro-F1")
    elif axis_best["domain"] < 0.05 and max(axis_best["function"], axis_best["mediation"]) >= 0.10:
        primary = "ATOMIC_LABEL_HEAD_FAILURE"
        evidence.append("domain axis collapsed while other axes show traction")
    elif best_track and best_track.startswith("F_") and d_best + 0.02 < best_rep:
        primary = "HIERARCHY_OBJECTIVE_FAILURE"
        evidence.append("hierarchy-aware contrastive dominated label-semantics track")
    elif best_rep < 0.05:
        primary = "PRETRAINED_REPRESENTATION_MISMATCH"
        evidence.append("no track cleared 0.05 REP system macro-F1 under locked floors")
    if best_rep < ADVANCEMENT_GATE["min_rep_system_macro_f1"]:
        evidence.append(
            f"best REP system macro-F1={best_rep:.4f} < "
            f"{ADVANCEMENT_GATE['min_rep_system_macro_f1']}"
        )
    secondary = []
    if best_rep < 0.08:
        secondary.append("DATA_SCALE_INSUFFICIENT")
    if d_best < 0.05 and not zs_stronger:
        secondary.append("TASK_REDEFINITION_REQUIRED")
    return {
        "primary_failure_diagnosis": primary,
        "secondary": secondary,
        "best_track": best_track,
        "best_rep_system_macro_f1": best_rep,
        "best_axis_macro_f1": axis_best,
        "zero_shot_rep_system_macro_f1": zs_rep,
        "zero_shot_stronger_than_trained": zs_stronger,
        "evidence": evidence,
        "candidate_hypotheses": list(FAILURE_DIAGNOSES),
    }


def classify_errors(
    *,
    gold_labels: Sequence[Sequence[str]],
    pred_labels: Sequence[Sequence[str]],
    texts: Sequence[str] | None = None,
    axis: str,
    ontology_uncertainty: Sequence[str | None] | None = None,
) -> dict[str, Any]:
    """Bucket per-example REP errors into research error classes."""
    counts = {k: 0 for k in ERROR_CLASSES}
    n = len(gold_labels)
    for i in range(n):
        g = set(gold_labels[i])
        p = set(pred_labels[i])
        if g == p:
            continue
        unc = (ontology_uncertainty or [None] * n)[i]
        if unc in {"ONTOLOGY_BOUNDARY_UNCLEAR", "INSUFFICIENT_CONTEXT", "ANNOTATOR_DISAGREEMENT"}:
            counts["ANNOTATION_BOUNDARY_CASE"] += 1
        fp = p - g
        fn = g - p
        if fp:
            counts["FALSE_POSITIVE_LABEL"] += 1
        if fn:
            counts["FALSE_NEGATIVE_LABEL"] += 1
        if axis == "domain":
            if "domain.technology.ai_discourse" in p and "domain.technology" not in p:
                counts["PARENT_CHILD_CONSISTENCY_FAILURE"] += 1
            if fp and fn:
                counts["LABEL_DESCRIPTION_CONFUSION"] += 1
            if len(fp) + len(fn) >= 2:
                counts["CO_LABEL_FAILURE"] += 1
        if fp and not fn:
            counts["ENCODER_SEPARATION_FAILURE"] += 1
        if fn and not g.isdisjoint(p) is False and fn and not fp:
            pass
        # Axis confusion: predicted labels from wrong conceptual family within axis
        # (approximate: any mismatch with both sides nonempty)
        if fp and fn:
            counts["AXIS_CONFUSION"] += 1
    return {"n": n, "counts": counts, "axis": axis}


def representation_diagnostics(
    pos_sims: Sequence[float],
    neg_sims: Sequence[float],
    *,
    nearest_purity: float | None = None,
    within_spread: float | None = None,
    cross_overlap: float | None = None,
    hierarchy_order_ok_rate: float | None = None,
) -> dict[str, Any]:
    def _mean(xs: Sequence[float]) -> float:
        return float(sum(xs) / len(xs)) if xs else 0.0

    pos = _mean(pos_sims)
    neg = _mean(neg_sims)
    return {
        "positive_text_label_similarity": pos,
        "hard_negative_text_label_similarity": neg,
        "positive_negative_margin": pos - neg,
        "nearest_label_purity": nearest_purity,
        "within_label_spread": within_spread,
        "cross_label_overlap": cross_overlap,
        "hierarchy_distance_order_ok_rate": hierarchy_order_ok_rate,
    }


# Re-export metrics helpers for the Spark runner.
__all__ = [
    "ADVANCEMENT_GATE",
    "AXIS_VOCABS",
    "EXPERIMENT_ID",
    "LABEL_DESCRIPTIONS",
    "PHASE_RULE",
    "TRACKS",
    "axis_floors_pass",
    "bakeoff_contract",
    "classify_errors",
    "diagnose_exhaustion",
    "frozen_label_descriptions",
    "hierarchy_metrics",
    "multilabel_f1",
    "representation_diagnostics",
    "select_reset_candidate",
]
