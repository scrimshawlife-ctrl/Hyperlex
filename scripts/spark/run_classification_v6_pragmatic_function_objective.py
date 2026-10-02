"""REDESIGN_V6_FUNCTION_OBJECTIVE_AROUND_PRAGMATIC_SIGNAL.

Derive pragmatic primitives, audit identifiability, train primitive predictors,
evaluate derived/abstaining FUNCTION objectives. No new direct function head.
"""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

PRIVATE = Path(
    "/home/morpheus/hlx-private/classification-v6-pragmatic-function-objective-20261002"
)
PRIVATE_V3 = Path(
    "/home/morpheus/hlx-private/classification-v6-function-diversity-expand-20261002"
)
PRIVATE_PKG = Path(
    "/home/morpheus/hlx-private/classification-v6-operating-pipeline-harden-20261001"
)
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-PRAGMATIC-FUNCTION-OBJECTIVE-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
SEED = 20261006

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))
sys.path.insert(0, str(REPO / "scripts" / "spark"))


def sudo_read_text(path: Path) -> str:
    if os.access(path, os.R_OK):
        return path.read_text(encoding="utf-8")
    return subprocess.run(
        ["sudo", "-n", "cat", str(path)], check=True, capture_output=True, text=True
    ).stdout


def load_json(path: Path) -> Any:
    return json.loads(sudo_read_text(path))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in sudo_read_text(path).splitlines() if l.strip()]


def write_private(path: Path, payload: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    text = (
        payload
        if isinstance(payload, str)
        else json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    )
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o600)


def write_repo(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )


def code_revision() -> str:
    env = os.environ.get("HLX_V5_STAGE_A_CODE_REVISION")
    if env:
        return env
    return subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def mean(xs: list[float]) -> float:
    return float(sum(xs) / max(1, len(xs)))


def multi_hot(labs, vocab):
    import numpy as np

    y = np.zeros(len(vocab), dtype=np.float32)
    s = set(labs or [])
    for i, lab in enumerate(vocab):
        if lab in s:
            y[i] = 1.0
    return y


def annotate_primitives_protocol(text: str, *, rater: str) -> dict[str, Any]:
    """Independent dual protocols for primitive cue detection (not operator IAA)."""
    from hyperlexical.classification_v6_pragmatic_function_objective import (
        detect_primitive_cues,
    )

    cues = detect_primitive_cues(text)
    prims = sorted(cues)
    # Protocol A: all cue hits; Protocol B: drop weakest single-char-ish / require ≥1 strong
    if rater == "A_PRIMITIVE_ALL_CUES":
        keep = prims
    else:
        # B: require multi-char cue evidence; drop mockery if only "mock" substring weak
        keep = []
        for p in prims:
            hits = cues.get(p) or []
            if any(len(h) >= 4 for h in hits):
                keep.append(p)
        keep = sorted(keep)
    return {"rater": rater, "primitives": keep, "cue_hits": cues}


def function_cue_hit(text: str, *, strong_only: bool = False) -> list[str]:
    from hyperlexical.classification_v6_human_ontology_settlement import (
        FUNCTION_CUES,
        _has_cues,
    )

    short_to_full = {
        "evaluative_stance": "function.evaluative_stance",
        "relational_intimacy": "function.relational_intimacy",
        "conflictive_force": "function.conflictive_force",
        "memetic_form": "function.memetic_form",
    }
    out = []
    for short, cues in FUNCTION_CUES.items():
        hits = _has_cues(text, cues)
        if not hits:
            continue
        if strong_only and not any(len(h) >= 4 for h in hits):
            continue
        out.append(short_to_full[short])
    return out


def inner() -> int:
    import numpy as np
    import torch
    import run_classification_v6_function_prediction_redesign as R
    from hyperlexical.classification_v6_architecture_reset_bakeoff import AXIS_VOCABS
    from hyperlexical.classification_v6_data_foundation import utc_now_iso
    from hyperlexical.classification_v6_function_prediction_redesign import (
        BASELINE_REP_V3,
    )
    from hyperlexical.classification_v6_operating_pipeline_harden import (
        WITNESS_GATE_THRESHOLD,
    )
    from hyperlexical.classification_v6_pragmatic_function_objective import (
        FUNCTION_TO_PRIMARY_PRIMITIVE,
        FUNCTION_VOCAB,
        PHASE_RULE,
        PRIMITIVE_VOCAB,
        REJECTED_MICRO_FIXES,
        build_pragmatic_receipt,
        classify_pragmatic_outcome,
        classify_row_annotation_status,
        derive_functions_from_primitives,
        detect_primitive_cues,
        function_mode_summary,
        pragmatic_contract,
    )
    from hyperlexical.classification_v6_semantic_pipeline_harden import (
        BAKEOFF_THRESHOLDS,
        SELECTED_ENCODER_MODEL_ID,
        SELECTED_ENCODER_REVISION,
    )

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    contract = pragmatic_contract()
    write_private(PRIVATE / "CONTRACT.json", contract)
    write_repo(REPO_ART / "contract.json", contract)

    print("load_surfaces", flush=True)
    train = load_jsonl(PRIVATE_V3 / "TRAIN_V3.jsonl")
    dev = load_jsonl(PRIVATE_V3 / "DEV_SELECTION_V3.jsonl")
    rep = load_jsonl(PRIVATE_V3 / "REPRESENTATIVE_VALIDATION_V3.jsonl")

    vocabs = AXIS_VOCABS
    fun_vocab = list(vocabs["function"])
    prim_vocab = list(PRIMITIVE_VOCAB)
    assert fun_vocab == list(FUNCTION_VOCAB)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    old_heads, _, _ = R.load_heads(
        PRIVATE_PKG / "heads" / "axis_nonlinear_heads.pt", vocabs, device
    )
    gate, _, _ = R.load_gate(PRIVATE_PKG / "heads" / "any_evidence_gate.pt", device)
    gate_th = float(WITNESS_GATE_THRESHOLD)
    th_dom_med = {
        "domain": list(BAKEOFF_THRESHOLDS["domain"]),
        "mediation": list(BAKEOFF_THRESHOLDS["mediation"]),
    }
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")
    old_fun_th = list(BAKEOFF_THRESHOLDS["function"])

    # --- Annotation audit ---
    print("annotation_audit", flush=True)
    audit_rows = []
    status_counts = Counter()
    for split_name, rows in (("TRAIN", train), ("DEV", dev), ("REP", rep)):
        for r in rows:
            st = classify_row_annotation_status(
                r.get("text") or "", r.get("function_labels") or []
            )
            status_counts[f"{split_name}:{st['status']}"] += 1
            status_counts[st["status"]] += 1
            audit_rows.append(
                {
                    "split": split_name,
                    "identity": r.get("identity"),
                    "status": st["status"],
                    "cue_primitives": st["cue_primitives"],
                    "missing_for_gold": st["missing_for_gold"],
                    "gold_functions": list(r.get("function_labels") or []),
                }
            )
    n_all = len(train) + len(dev) + len(rep)
    human_resettle = status_counts.get("HUMAN_RESETTLEMENT_REQUIRED", 0) / max(1, n_all)
    direct = status_counts.get("DIRECTLY_DERIVED", 0) / max(1, n_all)

    # Identifiability: among gold-function rows, share with primary primitive cue
    def ident_rate(rows):
        gold_n = 0
        hit = 0
        fun_cue = 0
        for r in rows:
            g = r.get("function_labels") or []
            if not g:
                continue
            gold_n += 1
            cues = detect_primitive_cues(r.get("text") or "")
            if any(FUNCTION_TO_PRIMARY_PRIMITIVE.get(f) in cues for f in g):
                hit += 1
            if function_cue_hit(r.get("text") or ""):
                fun_cue += 1
        return {
            "n_gold_function_rows": gold_n,
            "primitive_cue_recovery": hit / max(1, gold_n),
            "function_cue_recovery": fun_cue / max(1, gold_n),
        }

    ident_rep = ident_rate(rep)
    ident_train = ident_rate(train)
    ident_lift = (
        ident_rep["primitive_cue_recovery"] - ident_rep["function_cue_recovery"]
    )
    # Also measure: primitive cues recover *some* evidence vs full function cue set
    # Use combined train+rep for lift stability
    ident_all = ident_rate(train + rep)
    ident_lift = (
        ident_all["primitive_cue_recovery"] - ident_all["function_cue_recovery"]
    )

    # Dual protocol agreement
    print("dual_protocol_agreement", flush=True)
    sample = [r for r in rep if r.get("function_labels")][:120]
    if len(sample) < 40:
        sample = rep[:120]
    prim_agree = []
    fun_agree = []
    fun_gold_recovery = []
    for r in sample:
        text = r.get("text") or ""
        a = annotate_primitives_protocol(text, rater="A_PRIMITIVE_ALL_CUES")
        b = annotate_primitives_protocol(text, rater="B_PRIMITIVE_STRONG_CUES")
        sa, sb = set(a["primitives"]), set(b["primitives"])
        union = sa | sb
        prim_agree.append(1.0 if not union else len(sa & sb) / len(union))
        fa, fb = set(function_cue_hit(text)), set(
            function_cue_hit(text, strong_only=True)
        )
        fun_union = fa | fb
        fun_agree.append(1.0 if not fun_union else len(fa & fb) / len(fun_union))
        fg = set(r.get("function_labels") or [])
        if fg:
            fun_gold_recovery.append(len(fa & fg) / len(fg))
    primitive_dual_agreement = mean(prim_agree)
    function_dual_agreement = mean(fun_agree)
    function_gold_cue_recovery = mean(fun_gold_recovery) if fun_gold_recovery else 0.0

    # --- Embed ---
    print(f"embed device={device}", flush=True)
    Xtr = R.embed_model(
        SELECTED_ENCODER_MODEL_ID,
        [r["text"] for r in train],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    Xdv = R.embed_model(
        SELECTED_ENCODER_MODEL_ID,
        [r["text"] for r in dev],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    Xrp = R.embed_model(
        SELECTED_ENCODER_MODEL_ID,
        [r["text"] for r in rep],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )

    dom_dv = R.scores_from_heads(old_heads, Xdv, device, axes={"domain"})["domain"]
    med_dv = R.scores_from_heads(old_heads, Xdv, device, axes={"mediation"})["mediation"]
    dom_rp = R.scores_from_heads(old_heads, Xrp, device, axes={"domain"})["domain"]
    med_rp = R.scores_from_heads(old_heads, Xrp, device, axes={"mediation"})["mediation"]
    old_fun_rp = R.scores_from_heads(old_heads, Xrp, device, axes={"function"})[
        "function"
    ]

    # Baseline old function operating metrics on REP
    print("baseline_old_function", flush=True)
    base_op = R.run_operating(
        rep,
        Xrp,
        old_fun_rp,
        old_fun_th,
        dom_rp,
        med_rp,
        gate,
        gate_th,
        vocabs,
        th_dom_med,
        tech_idx,
        ai_idx,
        device,
    )
    # false function emission: pred function on rows with no gold function
    Yfun_rp = np.asarray(
        [multi_hot(r.get("function_labels"), fun_vocab) for r in rep], dtype=np.int32
    )
    old_fun_pred = (old_fun_rp >= np.asarray(old_fun_th)).astype(np.int32)
    gsc_rp = R.gate_scores(gate, Xrp, device)
    reject_rp = gsc_rp < gate_th
    old_fun_pred[reject_rp] = 0
    no_fun_idx = [i for i, r in enumerate(rep) if not (r.get("function_labels") or [])]
    baseline_false_emission = float(
        old_fun_pred[no_fun_idx].max(axis=1).mean()
    ) if no_fun_idx else 0.0

    # --- Build primitive supervision (cue-derived; + optional rule soft labels) ---
    print("build_primitive_labels", flush=True)

    def cue_primitive_matrix(rows):
        Y = np.zeros((len(rows), len(prim_vocab)), dtype=np.float32)
        for i, r in enumerate(rows):
            cues = detect_primitive_cues(r.get("text") or "")
            for j, p in enumerate(prim_vocab):
                if p in cues:
                    Y[i, j] = 1.0
        return Y

    def rule_primitive_matrix(rows):
        """Cue OR gold-function→primary (deterministic soft projection)."""
        Y = cue_primitive_matrix(rows)
        for i, r in enumerate(rows):
            for f in r.get("function_labels") or []:
                p = FUNCTION_TO_PRIMARY_PRIMITIVE.get(f)
                if p in prim_vocab:
                    Y[i, prim_vocab.index(p)] = 1.0
        return Y

    Ytr_cue = cue_primitive_matrix(train)
    Ydv_cue = cue_primitive_matrix(dev)
    Yrp_cue = cue_primitive_matrix(rep)
    Ytr_rule = rule_primitive_matrix(train)
    Ydv_rule = rule_primitive_matrix(dev)
    Yrp_rule = rule_primitive_matrix(rep)

    def train_primitive_models(X, Y):
        models = {}
        for j, lab in enumerate(prim_vocab):
            y = Y[:, j]
            # keep all rows; class-balanced loss inside trainer
            rng = random.Random(SEED + j)
            pos = np.where(y == 1)[0]
            neg = np.where(y == 0)[0]
            rng.shuffle(neg)
            take_neg = neg[: max(len(pos) * 6, 50)]
            idx = np.asarray(sorted(set(pos.tolist() + take_neg.tolist())), dtype=np.int64)
            if len(pos) == 0:
                # stub always-off
                models[lab] = None
                continue
            model, _ = R.train_binary_verifier(
                X[idx], y[idx], device, mid=64, seed=SEED + j
            )
            models[lab] = model
        return models

    def score_primitive_models(models, X):
        out = np.zeros((len(X), len(prim_vocab)), dtype=np.float32)
        for j, lab in enumerate(prim_vocab):
            m = models[lab]
            if m is None:
                continue
            out[:, j] = R.score_binary(m, X, device)
        return out

    print("train_primitives_cue", flush=True)
    models_cue = train_primitive_models(Xtr, Ytr_cue)
    sc_dv_cue = score_primitive_models(models_cue, Xdv)
    sc_rp_cue = score_primitive_models(models_cue, Xrp)

    print("train_primitives_rule", flush=True)
    models_rule = train_primitive_models(Xtr, Ytr_rule)
    sc_dv_rule = score_primitive_models(models_rule, Xdv)
    sc_rp_rule = score_primitive_models(models_rule, Xrp)

    def th_from(scores, Y):
        return [
            R.threshold_from_dev(scores[:, j], Y[:, j]) for j in range(len(prim_vocab))
        ]

    th_cue = th_from(sc_dv_cue, Ydv_cue)
    th_rule = th_from(sc_dv_rule, Ydv_rule)

    def pred_prim(scores, ths):
        return (scores >= np.asarray(ths)).astype(np.int32)

    # Pick supervision by DEV primitive macro-F1 vs cue gold (identifiable target)
    pack_cue = R.pack_axis(Ydv_cue, pred_prim(sc_dv_cue, th_cue), prim_vocab)
    pack_rule = R.pack_axis(Ydv_cue, pred_prim(sc_dv_rule, th_rule), prim_vocab)
    if pack_rule["macro_f1"] > pack_cue["macro_f1"] + 0.02:
        selected_supervision = "CUE_PLUS_RULE"
        models, sc_rp, th_prim = models_rule, sc_rp_rule, th_rule
        sc_dv = sc_dv_rule
    else:
        selected_supervision = "CUE_ONLY"
        models, sc_rp, th_prim = models_cue, sc_rp_cue, th_cue
        sc_dv = sc_dv_cue

    prim_pred_rp = pred_prim(sc_rp, th_prim)
    prim_pred_rp[reject_rp] = 0
    prim_rep_metrics = R.pack_axis(Yrp_cue, prim_pred_rp, prim_vocab)
    # also vs rule gold for diagnostics
    prim_rep_vs_rule = R.pack_axis(Yrp_rule, prim_pred_rp, prim_vocab)

    # --- Objectives B and C: derive functions ---
    print("derive_functions", flush=True)

    def derived_function_matrix(prim_pred, *, abstain: bool):
        fun = np.zeros((len(prim_pred), len(fun_vocab)), dtype=np.int32)
        unresolved = np.zeros(len(prim_pred), dtype=np.int32)
        unresolved_labels = [[] for _ in range(len(prim_pred))]
        for i in range(len(prim_pred)):
            prims = [prim_vocab[j] for j in range(len(prim_vocab)) if prim_pred[i, j] == 1]
            d = derive_functions_from_primitives(prims, abstain=abstain)
            for lab in d["function_labels"]:
                fun[i, fun_vocab.index(lab)] = 1
            unresolved_labels[i] = list(d["unresolved_functions"])
            if abstain:
                # global unresolved if gold-like evidence incomplete: mockery-only
                # or no primitives on a non-reject row that old head would consider
                if d["FUNCTION_UNRESOLVED"] or (
                    not d["function_labels"] and not prims and not reject_rp[i]
                ):
                    # only mark unresolved when some supportive primitive fired
                    if d["unresolved_functions"]:
                        unresolved[i] = 1
        return fun, unresolved, unresolved_labels

    fun_b, _, _ = derived_function_matrix(prim_pred_rp, abstain=False)
    fun_c, unresolved_c, unresolved_labs = derived_function_matrix(
        prim_pred_rp, abstain=True
    )
    fun_b[reject_rp] = 0
    fun_c[reject_rp] = 0
    unresolved_c[reject_rp] = 0

    def function_error_stats(pred):
        # false emission on no-gold-function rows; omission on gold-function rows
        no_fun = no_fun_idx
        has_fun = [i for i in range(len(rep)) if Yfun_rp[i].sum() > 0]
        false_em = float(pred[no_fun].max(axis=1).mean()) if no_fun else 0.0
        omit = float((pred[has_fun].sum(axis=1) == 0).mean()) if has_fun else 0.0
        return {"false_function_emission": false_em, "function_omission": omit}

    # Operating metrics with derived function replacing function axis
    def operating_with_fun(fun_pred):
        return R.run_operating(
            rep,
            Xrp,
            # pass scores that reproduce fun_pred at threshold 0.5
            fun_pred.astype(np.float32),
            [0.5] * len(fun_vocab),
            dom_rp,
            med_rp,
            gate,
            gate_th,
            vocabs,
            th_dom_med,
            tech_idx,
            ai_idx,
            device,
        )

    op_b = operating_with_fun(fun_b)
    op_c = operating_with_fun(fun_c)
    err_b = function_error_stats(fun_b)
    err_c = function_error_stats(fun_c)

    # Resolved-only precision for C
    resolved_idx = [i for i in range(len(rep)) if unresolved_c[i] == 0]
    if resolved_idx:
        pack_resolved = R.pack_axis(
            Yfun_rp[resolved_idx], fun_c[resolved_idx], fun_vocab
        )
        # precision macro over labels with support
        precs = [
            pack_resolved["per_label"][lab]["precision"]
            for lab in fun_vocab
            if pack_resolved["per_label"][lab]["support"] > 0
            or pack_resolved["per_label"][lab]["tp"]
            + pack_resolved["per_label"][lab]["fp"]
            > 0
        ]
        resolved_precision = mean(precs) if precs else 0.0
    else:
        resolved_precision = 0.0
    unresolved_rate = float(unresolved_c.mean())

    # Objective A metrics = primitive macro-F1
    objective_results = {
        "A_PRIMITIVE_MULTILABEL": {
            "primitive_macro_f1_vs_cue": prim_rep_metrics["macro_f1"],
            "primitive_macro_f1_vs_rule": prim_rep_vs_rule["macro_f1"],
            "primitive_per_label": prim_rep_metrics["per_label"],
            "FUNCTION_macro_f1": None,
            "system_macro_f1": None,
        },
        "B_PRIMITIVE_PLUS_DERIVATION": {
            "FUNCTION_macro_f1": op_b["FUNCTION_macro_f1"],
            "system_macro_f1": op_b["system_macro_f1"],
            "DOMAIN_macro_f1": op_b["DOMAIN_macro_f1"],
            "MEDIATION_macro_f1": op_b["MEDIATION_macro_f1"],
            "positive_only_system_macro_f1": op_b["positive_only_system_macro_f1"],
            "zero_label_false_positive_rate": op_b["zero_label_false_positive_rate"],
            "zero_label_exact_rejection": op_b["zero_label_exact_rejection"],
            "per_label_function": op_b["per_label_function"],
            **err_b,
            "unresolved_rate": 0.0,
        },
        "C_PRIMITIVE_PLUS_ABSTENTION": {
            "FUNCTION_macro_f1": op_c["FUNCTION_macro_f1"],
            "system_macro_f1": op_c["system_macro_f1"],
            "DOMAIN_macro_f1": op_c["DOMAIN_macro_f1"],
            "MEDIATION_macro_f1": op_c["MEDIATION_macro_f1"],
            "positive_only_system_macro_f1": op_c["positive_only_system_macro_f1"],
            "zero_label_false_positive_rate": op_c["zero_label_false_positive_rate"],
            "zero_label_exact_rejection": op_c["zero_label_exact_rejection"],
            "per_label_function": op_c["per_label_function"],
            **err_c,
            "unresolved_rate": unresolved_rate,
            "resolved_function_precision": resolved_precision,
            "resolved_FUNCTION_macro_f1": pack_resolved["macro_f1"]
            if resolved_idx
            else 0.0,
        },
    }

    # Select derived objective by reliability: prefer lower false emission then F1
    cand_b = objective_results["B_PRIMITIVE_PLUS_DERIVATION"]
    cand_c = objective_results["C_PRIMITIVE_PLUS_ABSTENTION"]
    def rank_key(c):
        return (
            -float(c.get("false_function_emission") or 1.0),
            float(c.get("FUNCTION_macro_f1") or 0.0),
            float(c.get("resolved_function_precision") or 0.0),
        )

    if rank_key(cand_c) >= rank_key(cand_b):
        selected_objective = "C_PRIMITIVE_PLUS_ABSTENTION"
        selected_derived = cand_c
    else:
        selected_objective = "B_PRIMITIVE_PLUS_DERIVATION"
        selected_derived = cand_b

    none_ok = (
        float(selected_derived["zero_label_false_positive_rate"]) <= 0.35
        and float(selected_derived["zero_label_exact_rejection"]) >= 0.50
    )
    # DOMAIN/MEDIATION must match baseline (frozen heads)
    domain_ok = abs(
        float(selected_derived["DOMAIN_macro_f1"]) - BASELINE_REP_V3["DOMAIN_macro_f1"]
    ) < 1e-6
    mediation_ok = abs(
        float(selected_derived["MEDIATION_macro_f1"])
        - BASELINE_REP_V3["MEDIATION_macro_f1"]
    ) < 1e-6

    # Cue-positive coverage stats for settlement narrative
    cue_pos_train = int((Ytr_cue.sum(axis=1) > 0).sum())
    cue_pos_rep = int((Yrp_cue.sum(axis=1) > 0).sum())

    audit = {
        "selected_supervision": selected_supervision,
        "selected_objective": selected_objective,
        "function_modes": function_mode_summary(),
        "annotation_status_counts": dict(status_counts),
        "human_resettlement_share": human_resettle,
        "directly_derived_share": direct,
        "identifiability": {
            "train": ident_train,
            "rep": ident_rep,
            "train_rep": ident_all,
            "identifiability_lift": ident_lift,
        },
        "identifiability_lift": ident_lift,
        "primitive_dual_agreement": primitive_dual_agreement,
        "function_dual_agreement": function_dual_agreement,
        "function_gold_cue_recovery": function_gold_cue_recovery,
        "primitive_human_agreement_note": (
            "dual cue-protocol Jaccard; true operator IAA still "
            "PROTOCOL_DEFINED_AWAITING_OPERATOR_ANNOTATION"
        ),
        "cue_positive_rows": {"TRAIN": cue_pos_train, "REP": cue_pos_rep},
        "cue_positive_rep": cue_pos_rep,
        "objective_results": objective_results,
        "baseline_REP_V3": dict(BASELINE_REP_V3),
        "baseline_false_function_emission": baseline_false_emission,
        "baseline_FUNCTION_macro_f1": BASELINE_REP_V3["FUNCTION_macro_f1"],
        "derived_FUNCTION_macro_f1": selected_derived["FUNCTION_macro_f1"],
        "false_function_emission": selected_derived["false_function_emission"],
        "function_omission": selected_derived["function_omission"],
        "unresolved_rate": selected_derived.get("unresolved_rate", 0.0),
        "resolved_function_precision": selected_derived.get(
            "resolved_function_precision"
        ),
        "none_preserved": none_ok,
        "domain_unchanged": domain_ok,
        "mediation_unchanged": mediation_ok,
        "primitive_thresholds": th_prim,
        "dev_primitive_macro_f1_cue_sup": pack_cue["macro_f1"],
        "dev_primitive_macro_f1_rule_sup": pack_rule["macro_f1"],
    }

    decision = classify_pragmatic_outcome(audit)
    # If DOMAIN/MEDIATION drifted somehow, force not supported
    if not (domain_ok and mediation_ok):
        decision = {
            "OUTCOME": "V6_PRAGMATIC_OBJECTIVE_NOT_SUPPORTED",
            "NEXT_ACTION": "REASSESS_V6_FUNCTION_PRODUCT_REQUIREMENT",
            "selected_objective": None,
            "primitives_more_reproducible": decision["primitives_more_reproducible"],
            "reliability_better": False,
            "none_preserved": none_ok,
            "reason": "domain_or_mediation_regressed",
        }

    sealed_at = utc_now_iso()
    receipt = build_pragmatic_receipt(
        {**audit, "selected_objective": decision["selected_objective"]},
        sealed_at=sealed_at,
    )
    # overwrite outcome fields from forced decision if needed
    receipt["OUTCOME"] = decision["OUTCOME"]
    receipt["NEXT_ACTION"] = decision["NEXT_ACTION"]
    receipt["selected_objective"] = decision["selected_objective"]
    receipt["SYSTEM_PRAGMATIC_OBJECTIVE_RECEIPT_SHA256"] = __import__(
        "hyperlexical.classification_v6_pragmatic_function_objective", fromlist=["_hash"]
    )._hash(
        {
            k: v
            for k, v in receipt.items()
            if k != "SYSTEM_PRAGMATIC_OBJECTIVE_RECEIPT_SHA256"
        }
    )

    summary = {
        "PHASE_RULE": PHASE_RULE,
        "OUTCOME": decision["OUTCOME"],
        "NEXT_ACTION": decision["NEXT_ACTION"],
        "selected_objective": decision["selected_objective"],
        "selected_supervision": selected_supervision,
        "function_modes": function_mode_summary(),
        "identifiability_lift": ident_lift,
        "primitive_dual_agreement": primitive_dual_agreement,
        "function_dual_agreement": function_dual_agreement,
        "human_resettlement_share": human_resettle,
        "primitive_macro_f1_vs_cue": prim_rep_metrics["macro_f1"],
        "derived_FUNCTION_macro_f1": selected_derived["FUNCTION_macro_f1"],
        "baseline_FUNCTION_macro_f1": BASELINE_REP_V3["FUNCTION_macro_f1"],
        "false_function_emission": selected_derived["false_function_emission"],
        "baseline_false_function_emission": baseline_false_emission,
        "function_omission": selected_derived["function_omission"],
        "unresolved_rate": selected_derived.get("unresolved_rate", 0.0),
        "resolved_function_precision": selected_derived.get(
            "resolved_function_precision"
        ),
        "system_macro_f1": selected_derived["system_macro_f1"],
        "DOMAIN_macro_f1": selected_derived["DOMAIN_macro_f1"],
        "MEDIATION_macro_f1": selected_derived["MEDIATION_macro_f1"],
        "none_preserved": none_ok,
        "objective_results": {
            k: {
                kk: vv
                for kk, vv in v.items()
                if kk != "per_label_function" and kk != "primitive_per_label"
            }
            for k, v in objective_results.items()
        },
        "REJECTED_MICRO_FIXES": dict(REJECTED_MICRO_FIXES),
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "RECEIPT": receipt["SYSTEM_PRAGMATIC_OBJECTIVE_RECEIPT_SHA256"],
        "reason": decision.get("reason"),
    }

    write_private(PRIVATE / "ANNOTATION_AUDIT.jsonl", "\n".join(
        json.dumps(x, sort_keys=True) for x in audit_rows
    ) + "\n")
    write_private(PRIVATE / "AUDIT.json", audit)
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_private(PRIVATE / "RECEIPT.json", receipt)
    write_private(
        PRIVATE / "POINTER.json",
        {
            "DIRECT_FUNCTION_HEAD_ADDED": False,
            "DOMAIN_HEAD_MUTATED": False,
            "MEDIATION_HEAD_MUTATED": False,
            "NONE_GATE_MUTATED": False,
            "HUB_PUBLISH_AUTHORIZED": False,
        },
    )

    public = {k: v for k, v in receipt.items() if k != "audit"}
    public["audit_summary"] = {
        "OUTCOME": decision["OUTCOME"],
        "NEXT_ACTION": decision["NEXT_ACTION"],
        "selected_objective": decision["selected_objective"],
        "identifiability_lift": ident_lift,
        "primitive_dual_agreement": primitive_dual_agreement,
        "function_dual_agreement": function_dual_agreement,
        "human_resettlement_share": human_resettle,
        "derived_FUNCTION_macro_f1": selected_derived["FUNCTION_macro_f1"],
        "baseline_FUNCTION_macro_f1": BASELINE_REP_V3["FUNCTION_macro_f1"],
        "primitive_macro_f1_vs_cue": prim_rep_metrics["macro_f1"],
        "unresolved_rate": selected_derived.get("unresolved_rate", 0.0),
        "reason": decision.get("reason"),
    }
    write_repo(REPO_ART / "summary.json", summary)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(REPO_ART / "receipt.json", public)
    write_repo(REPO_ART / "RECEIPT.json", public)
    write_repo(REPO_ART / "audit_summary.json", public["audit_summary"])
    write_repo(
        SPEC / "classification-v6-pragmatic-function-objective-receipt-20261002.json",
        public,
    )

    md = f"""# REDESIGN_V6_FUNCTION_OBJECTIVE_AROUND_PRAGMATIC_SIGNAL

```text
OUTCOME = {decision['OUTCOME']}
NEXT_ACTION = {decision['NEXT_ACTION']}
selected_objective = {decision['selected_objective']}
selected_supervision = {selected_supervision}

primitives = {', '.join(prim_vocab)}
identifiability_lift = {ident_lift:.3f}
primitive_dual_agreement = {primitive_dual_agreement:.3f}
function_dual_agreement = {function_dual_agreement:.3f}
human_resettlement_share = {human_resettle:.3f}

primitive_macro_f1_vs_cue (REP) = {prim_rep_metrics['macro_f1']:.4f}
derived FUNCTION (selected)     = {selected_derived['FUNCTION_macro_f1']:.4f}
baseline FUNCTION               = {BASELINE_REP_V3['FUNCTION_macro_f1']:.4f}
false_function_emission         = {selected_derived['false_function_emission']:.4f}
baseline_false_emission         = {baseline_false_emission:.4f}
function_omission               = {selected_derived['function_omission']:.4f}
unresolved_rate                 = {selected_derived.get('unresolved_rate', 0.0):.4f}

DOMAIN/MEDIATION frozen unchanged = {domain_ok and mediation_ok}
NONE preserved = {none_ok}
reason = {decision.get('reason')}
```

No direct four-way function head. Encoder / NONE / DOMAIN / MEDIATION / ontology frozen.
QUAL-003 blocked. MODEL_WIDE_BEST unchanged.
"""
    write_repo(
        SPEC / "classification-v6-pragmatic-function-objective-20261002.md", md
    )
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


def main() -> int:
    if os.environ.get("HLX_V6_PRAG_OBJ_INNER") == "1":
        return inner()
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    revision = code_revision()
    cmd = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "--network",
        "host",
        "-v",
        f"{REPO}:{REPO}",
        "-v",
        "/home/morpheus/hlx-private:/home/morpheus/hlx-private",
        "-v",
        "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
        "-v",
        "/home/morpheus/.cache/huggingface:/root/.cache/huggingface",
        "-w",
        str(REPO),
        "-e",
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow:/home/morpheus/Hyperlex/scripts/spark",
        "-e",
        "HLX_V2_FORWARD_ONTOLOGY=1",
        "-e",
        "HLX_V6_PRAG_OBJ_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(
            REPO
            / "scripts/spark/run_classification_v6_pragmatic_function_objective.py"
        ),
    ]
    log = PRIVATE / "pragmatic_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(
            cmd, check=False, stdout=handle, stderr=subprocess.STDOUT
        )
    try:
        print(log.read_text(encoding="utf-8")[-60000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
