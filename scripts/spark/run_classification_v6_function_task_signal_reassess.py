"""REASSESS_V6_FUNCTION_TASK_SIGNAL.

Read-only forensic reassessment of FUNCTION learnability / task-signal ceiling.
Replays existing formulations for error consensus; does not design new heads.
"""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

PRIVATE = Path(
    "/home/morpheus/hlx-private/classification-v6-function-task-signal-reassess-20261002"
)
PRIVATE_V3 = Path(
    "/home/morpheus/hlx-private/classification-v6-function-diversity-expand-20261002"
)
PRIVATE_PKG = Path(
    "/home/morpheus/hlx-private/classification-v6-operating-pipeline-harden-20261001"
)
PRIVATE_REDESIGN = Path(
    "/home/morpheus/hlx-private/classification-v6-function-prediction-redesign-20261002"
)
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-FUNCTION-TASK-SIGNAL-REASSESS-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
SEED = 20261005
MAX_LEN = 192
BATCH = 32

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))
sys.path.insert(0, str(REPO / "scripts" / "spark"))

# Lexical cues from settled ontology (explicit cue detection only).
from hyperlexical.classification_v6_human_ontology_settlement import (  # noqa: E402
    FUNCTION_CUES,
)

FUNCTION_SHORT = {
    "function.evaluative_stance": "evaluative_stance",
    "function.relational_intimacy": "relational_intimacy",
    "function.conflictive_force": "conflictive_force",
    "function.memetic_form": "memetic_form",
}


def sudo_read_text(path: Path) -> str:
    if os.access(path, os.R_OK):
        return path.read_text(encoding="utf-8")
    return subprocess.run(
        ["sudo", "-n", "cat", str(path)], check=True, capture_output=True, text=True
    ).stdout


def sudo_read_bytes(path: Path) -> bytes:
    if os.access(path, os.R_OK):
        return path.read_bytes()
    return subprocess.run(
        ["sudo", "-n", "cat", str(path)], check=True, capture_output=True
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


def source_style(sf: str) -> str:
    s = (sf or "").lower()
    if "wiki_culture" in s:
        return "encyclopedic_positive"
    if "wikt" in s:
        return "wiktionary_sense"
    if "firecrawl" in s:
        return "firecrawl_observed"
    return "other"


def length_bucket(n: int) -> str:
    if n < 60:
        return "short"
    if n < 200:
        return "medium"
    return "long"


def has_explicit_cue(text: str, lab: str) -> bool:
    from hyperlexical.classification_v6_human_ontology_settlement import _has_cues

    short = FUNCTION_SHORT[lab]
    cues = FUNCTION_CUES.get(short, ())
    return bool(_has_cues(text, cues))


def classify_cue_type(text: str, lab: str) -> str:
    """Heuristic cue typology for human-vs-model boundary (not gold)."""
    low = (text or "").lower()
    if has_explicit_cue(text, lab):
        return "explicit_lexical_cue"
    # compositional: multiple weak domain/function words
    tokens = set(low.replace("/", " ").split())
    multi = sum(
        1
        for w in (
            "slang",
            "internet",
            "online",
            "dating",
            "meme",
            "insult",
            "military",
            "sexual",
            "romantic",
            "pejorative",
        )
        if w in low
    )
    if multi >= 2:
        return "compositional_cue"
    if any(
        p in low
        for p in (
            "used to",
            "implies",
            "suggests",
            "often",
            "typically",
            "regarded as",
            "considered",
        )
    ):
        return "pragmatic_inference"
    if len(text) > 280 or "wikipedia" in (lab and low) or "culture" in low:
        return "discourse_context_dependence"
    if len(tokens) <= 12:
        return "world_background_knowledge"
    return "pragmatic_inference"


def f1_binary(yt, yp) -> float:
    import numpy as np

    yt = np.asarray(yt)
    yp = np.asarray(yp)
    tp = float(((yt == 1) & (yp == 1)).sum())
    fp = float(((yt == 0) & (yp == 1)).sum())
    fn = float(((yt == 1) & (yp == 0)).sum())
    if tp == 0:
        return 0.0
    p = tp / (tp + fp)
    r = tp / (tp + fn)
    return 2 * p * r / (p + r)


def pack_per_label(gold, pred, vocab):
    import numpy as np

    g = np.asarray(gold)
    p = np.asarray(pred)
    out = {}
    for j, lab in enumerate(vocab):
        out[lab] = {
            "f1": f1_binary(g[:, j], p[:, j]),
            "precision": float(
                ((g[:, j] == 1) & (p[:, j] == 1)).sum()
                / max(1, ((p[:, j] == 1)).sum())
            ),
            "recall": float(
                ((g[:, j] == 1) & (p[:, j] == 1)).sum()
                / max(1, ((g[:, j] == 1)).sum())
            ),
            "support": int(g[:, j].sum()),
            "fn_idx": [i for i in range(len(g)) if g[i, j] == 1 and p[i, j] == 0],
            "fp_idx": [i for i in range(len(g)) if g[i, j] == 0 and p[i, j] == 1],
        }
    return out


def nn_purity_and_margin(X, rows, lab, fun_vocab):
    import numpy as np

    gold = np.asarray([lab in (r.get("function_labels") or []) for r in rows])
    pos = np.where(gold)[0]
    neg = np.where(~gold)[0]
    if len(pos) < 2 or len(neg) < 2:
        return {"nn_purity": None, "pos_neg_margin": None}
    # leave-one-out NN among all rows
    sims = X @ X.T
    np.fill_diagonal(sims, -np.inf)
    nn = sims.argmax(axis=1)
    purity = float(np.mean([gold[nn[i]] == gold[i] for i in pos]))
    # margin: mean sim to other positives - mean sim to hard negatives (other fun / domain)
    hard_neg = []
    for i, r in enumerate(rows):
        if gold[i]:
            continue
        funs = r.get("function_labels") or []
        doms = r.get("domain_labels") or []
        if funs or doms:
            hard_neg.append(i)
    if not hard_neg:
        hard_neg = neg.tolist()
    Cpos = X[pos].mean(axis=0)
    Cpos = Cpos / max(1e-9, float(np.linalg.norm(Cpos)))
    pos_sim = (X[pos] @ Cpos).mean()
    neg_sim = (X[hard_neg] @ Cpos).mean()
    return {
        "nn_purity": purity,
        "pos_neg_margin": float(pos_sim - neg_sim),
        "n_pos": int(len(pos)),
        "n_hard_neg": int(len(hard_neg)),
    }


def adjacent_overlap_rate(rows, lab):
    """Legacy domain-adjacency proxy (diagnostic only; not primary overlap)."""
    pos = [r for r in rows if lab in (r.get("function_labels") or [])]
    other_fun = [
        r
        for r in rows
        if r.get("function_labels") and lab not in (r.get("function_labels") or [])
    ]
    if not pos or not other_fun:
        return 0.0
    pos_doms = Counter(d for r in pos for d in (r.get("domain_labels") or ["__NONE__"]))
    hit = 0
    for r in other_fun:
        doms = r.get("domain_labels") or ["__NONE__"]
        if any(pos_doms[d] > 0 for d in doms):
            hit += 1
    return hit / len(other_fun)


def function_cooccurrence_rate(rows, lab):
    """Share of this label's positives that also carry another function label."""
    pos = [r for r in rows if lab in (r.get("function_labels") or [])]
    if not pos:
        return 0.0
    multi = sum(1 for r in pos if len(r.get("function_labels") or []) >= 2)
    return multi / len(pos)


def inner() -> int:
    import numpy as np
    import torch
    import run_classification_v6_function_prediction_redesign as R
    from hyperlexical.classification_v6_architecture_reset_bakeoff import AXIS_VOCABS
    from hyperlexical.classification_v6_data_foundation import utc_now_iso
    from hyperlexical.classification_v6_function_prediction_redesign import (
        BASELINE_REP_V3,
        FUNCTION_DEFINITIONS,
        FUNCTION_VOCAB,
    )
    from hyperlexical.classification_v6_function_task_signal_reassess import (
        PHASE_RULE,
        REJECTED_MICRO_FIXES,
        build_reassess_receipt,
        classify_axis_structure,
        classify_ceiling,
        classify_function_signal,
        derive_diagnosis,
        reassess_contract,
    )
    from hyperlexical.classification_v6_human_ontology_settlement import (
        dual_annotate_rows,
    )
    from hyperlexical.classification_v6_operating_pipeline_harden import (
        WITNESS_GATE_THRESHOLD,
    )
    from hyperlexical.classification_v6_semantic_pipeline_harden import (
        BAKEOFF_THRESHOLDS,
        SELECTED_ENCODER_MODEL_ID,
        SELECTED_ENCODER_REVISION,
    )

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    contract = reassess_contract()
    write_private(PRIVATE / "CONTRACT.json", contract)
    write_repo(REPO_ART / "contract.json", contract)

    print("load_surfaces", flush=True)
    train = load_jsonl(PRIVATE_V3 / "TRAIN_V3.jsonl")
    dev = load_jsonl(PRIVATE_V3 / "DEV_SELECTION_V3.jsonl")
    rep = load_jsonl(PRIVATE_V3 / "REPRESENTATIVE_VALIDATION_V3.jsonl")
    redesign_summary = load_json(PRIVATE_REDESIGN / "SUMMARY.json")

    vocabs = AXIS_VOCABS
    fun_vocab = list(vocabs["function"])
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
    def_embs = R.embed_model(
        SELECTED_ENCODER_MODEL_ID,
        [FUNCTION_DEFINITIONS[lab] for lab in fun_vocab],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )

    dom_dv = R.scores_from_heads(old_heads, Xdv, device, axes={"domain"})["domain"]
    med_dv = R.scores_from_heads(old_heads, Xdv, device, axes={"mediation"})["mediation"]
    dom_rp = R.scores_from_heads(old_heads, Xrp, device, axes={"domain"})["domain"]
    med_rp = R.scores_from_heads(old_heads, Xrp, device, axes={"mediation"})["mediation"]

    # Score all formulations on REP (and DEV for thresholds)
    print("score_formulations", flush=True)
    old_fun_rp = R.scores_from_heads(old_heads, Xrp, device, axes={"function"})[
        "function"
    ]
    old_fun_dv = R.scores_from_heads(old_heads, Xdv, device, axes={"function"})[
        "function"
    ]

    ind_models, _ = R.train_independent_verifiers(train, Xtr, fun_vocab, device)
    ind_dv = R.score_independent(ind_models, Xdv, fun_vocab, device)
    ind_rp = R.score_independent(ind_models, Xrp, fun_vocab, device)

    cals, _, _ = R.train_semantic_matching(train, Xtr, def_embs, fun_vocab, device)
    sem_dv = R.score_semantic(Xdv, def_embs, cals, fun_vocab)
    sem_rp = R.score_semantic(Xrp, def_embs, cals, fun_vocab)

    hyb_models, _ = R.train_hybrid(train, Xtr, def_embs, fun_vocab, device)
    hyb_dv = R.score_hybrid(hyb_models, Xdv, def_embs, fun_vocab, device)
    hyb_rp = R.score_hybrid(hyb_models, Xrp, def_embs, fun_vocab, device)

    Ydv = np.asarray(
        [multi_hot(r.get("function_labels"), fun_vocab) for r in dev], dtype=np.int32
    )
    Yrp = np.asarray(
        [multi_hot(r.get("function_labels"), fun_vocab) for r in rep], dtype=np.int32
    )

    def th_from(scores):
        return [
            R.threshold_from_dev(scores[:, j], Ydv[:, j]) for j in range(len(fun_vocab))
        ]

    ind_th, sem_th, hyb_th = th_from(ind_dv), th_from(sem_dv), th_from(hyb_dv)

    def pred_fun(scores, ths):
        return (scores >= np.asarray(ths)).astype(np.int32)

    # Apply gate zeroing for operating-consistent errors
    gsc_rp = R.gate_scores(gate, Xrp, device)
    reject_rp = gsc_rp < gate_th

    def gated(pred):
        q = pred.copy()
        q[reject_rp] = 0
        return q

    preds = {
        "OLD_SHARED_HEAD": gated(pred_fun(old_fun_rp, old_fun_th)),
        "INDEPENDENT_BINARY_VERIFIERS": gated(pred_fun(ind_rp, ind_th)),
        "FUNCTION_SEMANTIC_MATCHING": gated(pred_fun(sem_rp, sem_th)),
        "HYBRID_VERIFIER": gated(pred_fun(hyb_rp, hyb_th)),
    }

    per_form = {
        name: pack_per_label(Yrp, pred, fun_vocab) for name, pred in preds.items()
    }
    form_macros = {
        name: float(mean([per_form[name][lab]["f1"] for lab in fun_vocab]))
        for name in preds
    }

    # Dual-annotator gold recovery (cue-protocol raters) — NOT true human IAA.
    # Foundation HUMAN_AGREEMENT remains PROTOCOL_DEFINED_AWAITING_OPERATOR_ANNOTATION.
    print("dual_annotate_rep_function", flush=True)
    fun_rep_idx = [i for i, r in enumerate(rep) if r.get("function_labels")]
    blind = [{"text": rep[i]["text"], "identity": rep[i]["identity"]} for i in fun_rep_idx]
    ann = dual_annotate_rows(blind)
    dual_recovery_by_lab = {}
    dual_ab_agree_by_lab = {}
    for j, lab in enumerate(fun_vocab):
        short = FUNCTION_SHORT[lab]
        recovery = []
        ab_agree = []
        for a, src_i in zip(ann, fun_rep_idx):
            gold = lab in (rep[src_i].get("function_labels") or [])
            a_has = short in (a["rater_a"].get("functions") or [])
            b_has = short in (a["rater_b"].get("functions") or [])
            ab_agree.append(1.0 if a_has == b_has else 0.0)
            if gold:
                recovery.append(
                    1.0 if (a_has and b_has) else (0.5 if (a_has or b_has) else 0.0)
                )
        dual_recovery_by_lab[lab] = mean(recovery) if recovery else None
        dual_ab_agree_by_lab[lab] = mean(ab_agree) if ab_agree else None

    mean_dual_recovery = mean(
        [v for v in dual_recovery_by_lab.values() if v is not None]
    )
    mean_dual_ab = mean([v for v in dual_ab_agree_by_lab.values() if v is not None])
    true_human_iaa_available = False
    mean_human = None  # reserved for operator second-rater kappa when available

    # Error consensus
    print("error_consensus", flush=True)
    consensus = {}
    for j, lab in enumerate(fun_vocab):
        gold_pos = [i for i in range(len(rep)) if Yrp[i, j] == 1]
        fail_sets = {
            name: set(per_form[name][lab]["fn_idx"]) for name in preds
        }
        # rows failed by all / by >=3 / by >=2
        all_fail = set.intersection(*fail_sets.values()) if fail_sets else set()
        ge3 = {
            i
            for i in gold_pos
            if sum(1 for s in fail_sets.values() if i in s) >= 3
        }
        ge2 = {
            i
            for i in gold_pos
            if sum(1 for s in fail_sets.values() if i in s) >= 2
        }
        consensus[lab] = {
            "gold_n": len(gold_pos),
            "fail_all_4": len(all_fail & set(gold_pos)),
            "fail_ge3": len(ge3),
            "fail_ge2": len(ge2),
            "consensus_fail_share_among_gold": len(ge3) / max(1, len(gold_pos)),
            "pairwise_jaccard": {},
        }
        names = list(preds)
        for a in range(len(names)):
            for b in range(a + 1, len(names)):
                A, B = fail_sets[names[a]], fail_sets[names[b]]
                inter = len(A & B)
                union = len(A | B) or 1
                consensus[lab]["pairwise_jaccard"][f"{names[a]}__{names[b]}"] = (
                    inter / union
                )

    mean_consensus = mean(
        [consensus[lab]["consensus_fail_share_among_gold"] for lab in fun_vocab]
    )
    task_signal_limit = mean_consensus >= 0.40

    # Per-function audits
    print("per_function_audits", flush=True)
    per_function = {}
    prag_shares = []
    for j, lab in enumerate(fun_vocab):
        train_pos = [r for r in train if lab in (r.get("function_labels") or [])]
        rep_pos = [r for r in rep if lab in (r.get("function_labels") or [])]
        styles = Counter(source_style(r.get("source_family") or "") for r in train_pos)
        lens = Counter(length_bucket(len(r.get("text") or "")) for r in train_pos)
        doms = Counter(
            d for r in train_pos for d in (r.get("domain_labels") or ["__NONE__"])
        )
        geom = nn_purity_and_margin(Xrp, rep, lab, fun_vocab)
        cues = Counter(classify_cue_type(r["text"], lab) for r in rep_pos)
        prag_share = (
            cues.get("pragmatic_inference", 0)
            + cues.get("discourse_context_dependence", 0)
            + cues.get("world_background_knowledge", 0)
        ) / max(1, len(rep_pos))
        prag_shares.append(prag_share)
        # formulation agreement on gold positives
        agree_old_ind = 0
        n_g = 0
        for i in range(len(rep)):
            if Yrp[i, j] != 1:
                continue
            n_g += 1
            if preds["OLD_SHARED_HEAD"][i, j] == preds["INDEPENDENT_BINARY_VERIFIERS"][i, j]:
                agree_old_ind += 1

        audit = {
            "train_support": len(train_pos),
            "dev_support": sum(
                1 for r in dev if lab in (r.get("function_labels") or [])
            ),
            "rep_support": len(rep_pos),
            "train_styles": dict(styles),
            "train_lengths": dict(lens),
            "train_domains_n": len(doms),
            "train_domain_mix": dict(doms.most_common(8)),
            "old_head_f1": per_form["OLD_SHARED_HEAD"][lab]["f1"],
            "independent_f1": per_form["INDEPENDENT_BINARY_VERIFIERS"][lab]["f1"],
            "hybrid_f1": per_form["HYBRID_VERIFIER"][lab]["f1"],
            "semantic_f1": per_form["FUNCTION_SEMANTIC_MATCHING"][lab]["f1"],
            "nn_purity": geom["nn_purity"],
            "pos_neg_margin": geom["pos_neg_margin"],
            "adjacent_overlap_rate": adjacent_overlap_rate(rep, lab),
            "function_cooccurrence_rate": function_cooccurrence_rate(rep, lab),
            "cue_type_mix": dict(cues),
            "pragmatic_or_context_share": prag_share,
            "explicit_lexical_share": cues.get("explicit_lexical_cue", 0)
            / max(1, len(rep_pos)),
            "consensus_fail_share_among_gold": consensus[lab][
                "consensus_fail_share_among_gold"
            ],
            "old_vs_independent_agree_on_gold": agree_old_ind / max(1, n_g),
            "dual_annotator_gold_recovery": dual_recovery_by_lab[lab],
            "dual_annotator_ab_agree": dual_ab_agree_by_lab[lab],
            "human_function_jaccard": None,
            "error_consensus": consensus[lab],
        }
        audit["signal_class"] = classify_function_signal(audit)
        per_function[lab] = audit

    ceiling_audit = {
        "formulation_function_macros": form_macros,
        "mean_consensus_fail_share": mean_consensus,
        "mean_pragmatic_share": mean(prag_shares),
        "mean_human_function_jaccard": mean_human,
        "true_human_iaa_available": true_human_iaa_available,
        "diversity_adequate": True,  # prior expand phase settled
    }
    ceiling_class = classify_ceiling(ceiling_audit)
    axis_structure = classify_axis_structure(per_function)

    # Failure concentration by cue type among consensus fails
    cue_fail = Counter()
    cue_all = Counter()
    for j, lab in enumerate(fun_vocab):
        for i, r in enumerate(rep):
            if Yrp[i, j] != 1:
                continue
            ct = classify_cue_type(r["text"], lab)
            cue_all[ct] += 1
            if i in set(per_form["OLD_SHARED_HEAD"][lab]["fn_idx"]) and i in set(
                per_form["INDEPENDENT_BINARY_VERIFIERS"][lab]["fn_idx"]
            ):
                cue_fail[ct] += 1
    cue_fail_rate = {
        k: cue_fail[k] / max(1, cue_all[k]) for k in cue_all
    }

    audit = {
        "formulation_function_macros": form_macros,
        "per_formulation_per_label": {
            name: {
                lab: {
                    k: v
                    for k, v in per_form[name][lab].items()
                    if k not in {"fn_idx", "fp_idx"}
                }
                for lab in fun_vocab
            }
            for name in preds
        },
        "per_function": per_function,
        "error_consensus": consensus,
        "task_signal_limit": task_signal_limit,
        "mean_consensus_fail_share": mean_consensus,
        "mean_pragmatic_share": mean(prag_shares),
        "mean_dual_annotator_gold_recovery": mean_dual_recovery,
        "mean_dual_annotator_ab_agree": mean_dual_ab,
        "mean_human_function_jaccard": mean_human,
        "true_human_iaa_available": true_human_iaa_available,
        "ceiling_class": ceiling_class,
        "axis_structure": axis_structure,
        "cue_failure_rates": cue_fail_rate,
        "cue_all_counts": dict(cue_all),
        "parent_redesign": {
            "outcome": redesign_summary.get("OUTCOME"),
            "selected": redesign_summary.get("selected_formulation"),
            "candidate_FUNCTION": redesign_summary.get("candidate_REP_V3", {}).get(
                "FUNCTION_macro_f1"
            ),
        },
        "baseline_REP_V3": dict(BASELINE_REP_V3),
        "diversity_adequate": True,
        "surface_sizes": {
            "TRAIN_V3": len(train),
            "DEV_V3": len(dev),
            "REP_V3": len(rep),
        },
    }

    derived = derive_diagnosis(audit)
    reviewed_at = utc_now_iso()
    receipt = build_reassess_receipt(audit, reviewed_at=reviewed_at)

    summary = {
        "PHASE_RULE": PHASE_RULE,
        "PRIMARY_DIAGNOSIS": derived["PRIMARY_DIAGNOSIS"],
        "CEILING_CLASS": derived["CEILING_CLASS"],
        "AXIS_STRUCTURE": derived["AXIS_STRUCTURE"],
        "NEXT_ACTION": derived["NEXT_ACTION"],
        "task_signal_limit": task_signal_limit,
        "signal_class_counts": derived["signal_class_counts"],
        "per_function_signal": {
            lab: per_function[lab]["signal_class"] for lab in fun_vocab
        },
        "formulation_function_macros": form_macros,
        "mean_consensus_fail_share": mean_consensus,
        "mean_pragmatic_share": mean(prag_shares),
        "mean_dual_annotator_gold_recovery": mean_dual_recovery,
        "mean_dual_annotator_ab_agree": mean_dual_ab,
        "mean_human_function_jaccard": mean_human,
        "true_human_iaa_available": true_human_iaa_available,
        "cue_failure_rates": cue_fail_rate,
        "REJECTED_MICRO_FIXES": dict(REJECTED_MICRO_FIXES),
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "MODEL_WIDE_BEST_MUTATED": False,
        "FUNCTION_HEAD_REDESIGNED": False,
        "RECEIPT": receipt["SYSTEM_TASK_SIGNAL_RECEIPT_SHA256"],
    }

    write_private(PRIVATE / "AUDIT.json", audit)
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_private(PRIVATE / "RECEIPT.json", receipt)
    write_private(
        PRIVATE / "POINTER.json",
        {
            "FUNCTION_HEAD_REDESIGNED": False,
            "DOMAIN_HEAD_MUTATED": False,
            "MEDIATION_HEAD_MUTATED": False,
            "NONE_GATE_MUTATED": False,
            "HUB_PUBLISH_AUTHORIZED": False,
        },
    )

    public = {k: v for k, v in receipt.items() if k != "audit"}
    public["audit_summary"] = {
        "PRIMARY_DIAGNOSIS": derived["PRIMARY_DIAGNOSIS"],
        "CEILING_CLASS": derived["CEILING_CLASS"],
        "AXIS_STRUCTURE": derived["AXIS_STRUCTURE"],
        "NEXT_ACTION": derived["NEXT_ACTION"],
        "per_function_signal": summary["per_function_signal"],
        "formulation_function_macros": form_macros,
        "task_signal_limit": task_signal_limit,
        "mean_consensus_fail_share": mean_consensus,
        "cue_failure_rates": cue_fail_rate,
    }
    write_repo(REPO_ART / "summary.json", summary)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(REPO_ART / "receipt.json", public)
    write_repo(REPO_ART / "RECEIPT.json", public)
    write_repo(REPO_ART / "audit_summary.json", public["audit_summary"])
    write_repo(
        SPEC / "classification-v6-function-task-signal-reassess-receipt-20261002.json",
        public,
    )

    md = f"""# REASSESS_V6_FUNCTION_TASK_SIGNAL

```text
PRIMARY_DIAGNOSIS = {derived['PRIMARY_DIAGNOSIS']}
CEILING_CLASS = {derived['CEILING_CLASS']}
AXIS_STRUCTURE = {derived['AXIS_STRUCTURE']}
TASK_SIGNAL_LIMIT = {task_signal_limit}
NEXT_ACTION = {derived['NEXT_ACTION']}

formulation FUNCTION macros (REP_V3, gated):
  OLD_SHARED_HEAD              = {form_macros['OLD_SHARED_HEAD']:.4f}
  INDEPENDENT_BINARY_VERIFIERS = {form_macros['INDEPENDENT_BINARY_VERIFIERS']:.4f}
  HYBRID_VERIFIER              = {form_macros['HYBRID_VERIFIER']:.4f}
  FUNCTION_SEMANTIC_MATCHING   = {form_macros['FUNCTION_SEMANTIC_MATCHING']:.4f}

mean consensus-fail share among gold = {mean_consensus:.3f}
mean pragmatic/context cue share     = {mean(prag_shares):.3f}
dual_annotator gold recovery         = {mean_dual_recovery:.3f}
dual_annotator A/B agree             = {mean_dual_ab:.3f}
true_human_iaa_available             = {true_human_iaa_available}
"""
    for lab in fun_vocab:
        md += f"\n{lab} = {per_function[lab]['signal_class']}"
    md += """
```

No new function head. Encoder / NONE / DOMAIN / MEDIATION / ontology frozen.
QUAL-003 blocked. MODEL_WIDE_BEST unchanged.
"""
    write_repo(
        SPEC / "classification-v6-function-task-signal-reassess-20261002.md", md
    )
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


def main() -> int:
    if os.environ.get("HLX_V6_FUN_SIGNAL_INNER") == "1":
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
        "HLX_V6_FUN_SIGNAL_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(
            REPO
            / "scripts/spark/run_classification_v6_function_task_signal_reassess.py"
        ),
    ]
    log = PRIVATE / "reassess_console.log"
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
