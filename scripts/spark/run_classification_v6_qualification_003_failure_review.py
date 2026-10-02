"""REVIEW_V6_QUALIFICATION_003_FAILURE.

Read-only forensic review of QUAL-003 FAIL focusing on positive/FUNCTION
generalization. Does not retune ANY_LABEL, retrain, change ontology, or
open a new QUAL surface.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

PRIVATE_QUAL = Path(
    "/home/morpheus/hlx-private/classification-v6-qualification-surface-003-20261001"
)
PRIVATE_EXEC = Path(
    "/home/morpheus/hlx-private/classification-v6-qualification-execute-003-20261001"
)
PRIVATE_PKG = Path(
    "/home/morpheus/hlx-private/classification-v6-operating-pipeline-harden-20261001"
)
PRIVATE_V2 = Path(
    "/home/morpheus/hlx-private/classification-v6-representative-validation-redesign-20261001"
)
PRIVATE_REV = Path(
    "/home/morpheus/hlx-private/classification-v6-qualification-003-failure-review-20261001"
)
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-QUALIFICATION-003-FAILURE-REVIEW-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
MAX_LEN = 192
BATCH = 32

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

FUNCTION_VOCAB = [
    "function.relational_intimacy",
    "function.conflictive_force",
    "function.evaluative_stance",
    "function.memetic_form",
]


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


def n_lab(r: dict) -> int:
    return (
        len(r.get("domain_labels") or [])
        + len(r.get("function_labels") or [])
        + len(r.get("mediation_labels") or [])
    )


def length_bucket(n: int) -> str:
    if n < 60:
        return "short"
    if n < 200:
        return "medium"
    return "long"


def source_style(sf: str) -> str:
    s = (sf or "").lower()
    if "wiki_none" in s or "wiki_html_none" in s:
        return "encyclopedic_none_cue"
    if "wikt" in s:
        return "wiktionary_sense"
    if "firecrawl" in s:
        return "firecrawl_observed"
    return "other"


def mean(xs: list[float]) -> float:
    return float(sum(xs) / max(1, len(xs)))


def pct(n: int, d: int) -> float:
    return float(n) / max(1, d)


def l1_dist(a: Counter, b: Counter) -> float:
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    sa, sb = sum(a.values()) or 1, sum(b.values()) or 1
    return 0.5 * sum(abs(a[k] / sa - b[k] / sb) for k in keys)


def embed_model(model_id, texts, device, max_len=MAX_LEN, batch=BATCH, revision=None):
    import torch
    import torch.nn.functional as F
    from transformers import AutoModel, AutoTokenizer

    kw = {}
    if revision:
        kw["revision"] = revision
    tok = AutoTokenizer.from_pretrained(model_id, **kw)
    enc = AutoModel.from_pretrained(model_id, **kw).to(device)
    enc.eval()
    for p in enc.parameters():
        p.requires_grad_(False)

    def mean_pool(last_hidden, attention_mask):
        mask = attention_mask.unsqueeze(-1).float()
        return (last_hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-6)

    vecs = []
    with torch.no_grad():
        for i in range(0, len(texts), batch):
            t = tok(
                texts[i : i + batch],
                padding=True,
                truncation=True,
                max_length=max_len,
                return_tensors="pt",
            ).to(device)
            h = enc(**t).last_hidden_state
            v = F.normalize(mean_pool(h, t["attention_mask"]), dim=-1)
            vecs.append(v.cpu())
    del enc
    torch.cuda.empty_cache()
    return __import__("torch").cat(vecs, dim=0).numpy()


def cosine_centroid_stats(X, labels_idx: list[int], other_idx: list[int]) -> dict:
    import numpy as np

    if not labels_idx:
        return {"n": 0, "mean_sim_to_centroid": None, "mean_sim_to_other": None}
    C = X[labels_idx].mean(axis=0)
    C = C / max(1e-9, float(np.linalg.norm(C)))
    sim_self = (X[labels_idx] @ C).tolist()
    sim_other = (X[other_idx] @ C).tolist() if other_idx else []
    return {
        "n": len(labels_idx),
        "mean_sim_to_centroid": mean(sim_self),
        "p10_sim_to_centroid": float(sorted(sim_self)[max(0, len(sim_self) // 10)]),
        "mean_sim_to_other": mean(sim_other) if sim_other else None,
        "margin_vs_other": (
            mean(sim_self) - mean(sim_other) if sim_other else None
        ),
    }


def analyze_positive_false_reject(rows, preds, fun_idx) -> dict[str, Any]:
    pos = [r for r in rows if n_lab(r) > 0]
    gate_rej = [r for r in pos if preds[r["identity"]]["gate_reject"]]
    final_empty = [
        r
        for r in pos
        if not (
            preds[r["identity"]]["final_domain_labels"]
            or preds[r["identity"]]["final_function_labels"]
            or preds[r["identity"]]["final_mediation_labels"]
        )
    ]
    admitted = [r for r in pos if not preds[r["identity"]]["gate_reject"]]
    empty_after_admit = [
        r
        for r in admitted
        if not (
            preds[r["identity"]]["final_domain_labels"]
            or preds[r["identity"]]["final_function_labels"]
            or preds[r["identity"]]["final_mediation_labels"]
        )
    ]

    def strata(subset, universe):
        out = {}
        # by has function / domain / mediation
        for name, pred in (
            ("has_function", lambda r: bool(r.get("function_labels"))),
            ("has_domain", lambda r: bool(r.get("domain_labels"))),
            ("has_mediation", lambda r: bool(r.get("mediation_labels"))),
            ("single_label", lambda r: n_lab(r) == 1),
            ("multi_label", lambda r: n_lab(r) >= 2),
        ):
            u = [r for r in universe if pred(r)]
            s = [r for r in subset if pred(r)]
            out[name] = {"universe": len(u), "subset": len(s), "rate": pct(len(s), len(u))}
        # length
        for b in ("short", "medium", "long"):
            u = [r for r in universe if length_bucket(len(r.get("text") or "")) == b]
            s = [r for r in subset if length_bucket(len(r.get("text") or "")) == b]
            out[f"length_{b}"] = {
                "universe": len(u),
                "subset": len(s),
                "rate": pct(len(s), len(u)),
            }
        # style
        for st in ("encyclopedic_none_cue", "wiktionary_sense", "firecrawl_observed", "other"):
            u = [r for r in universe if source_style(r.get("source_family") or "") == st]
            s = [r for r in subset if source_style(r.get("source_family") or "") == st]
            out[f"style_{st}"] = {
                "universe": len(u),
                "subset": len(s),
                "rate": pct(len(s), len(u)),
            }
        # gate score margin among rejected positives
        scores = [float(preds[r["identity"]]["gate_score"]) for r in subset]
        out["gate_score"] = {
            "mean": mean(scores) if scores else None,
            "p50": float(sorted(scores)[len(scores) // 2]) if scores else None,
        }
        return out

    # encoder margin proxy: max axis score among rejected positives
    rej_margins = []
    for r in gate_rej:
        p = preds[r["identity"]]
        rej_margins.append(
            max(
                max(p["raw_domain_scores"] or [0]),
                max(p["raw_function_scores"] or [0]),
                max(p["raw_mediation_scores"] or [0]),
            )
        )
    adm_margins = []
    for r in admitted:
        p = preds[r["identity"]]
        adm_margins.append(
            max(
                max(p["raw_domain_scores"] or [0]),
                max(p["raw_function_scores"] or [0]),
                max(p["raw_mediation_scores"] or [0]),
            )
        )

    final_empty_n = len(final_empty)
    post_share = pct(len(empty_after_admit), final_empty_n)
    gate_share_of_empty = pct(len([r for r in final_empty if preds[r["identity"]]["gate_reject"]]), final_empty_n)

    class_ = (
        "POSITIVE_GATE_GENERALIZATION_FAILURE"
        if pct(len(gate_rej), len(pos)) >= 0.45 and post_share < 0.25
        else (
            "MOSTLY_POST_ADMISSION_POSITIVE_ERRORS"
            if post_share >= 0.30
            else "MIXED_GATE_AND_POST_ADMISSION"
        )
    )

    return {
        "n_positive": len(pos),
        "n_gate_reject": len(gate_rej),
        "gate_reject_rate_on_positives": pct(len(gate_rej), len(pos)),
        "n_final_empty": final_empty_n,
        "final_empty_rate_on_positives": pct(final_empty_n, len(pos)),
        "n_admitted": len(admitted),
        "n_empty_after_admit": len(empty_after_admit),
        "post_admission_empty_share_of_final_empty": post_share,
        "gate_share_of_final_empty": gate_share_of_empty,
        "class": class_,
        "gate_reject_strata": strata(gate_rej, pos),
        "final_empty_strata": strata(final_empty, pos),
        "head_score_max_mean_gate_rejected": mean(rej_margins) if rej_margins else None,
        "head_score_max_mean_admitted": mean(adm_margins) if adm_margins else None,
        "note": (
            "PRIMARY_METRICS.false_reject_positive_rate counts final-empty positives; "
            "gate_reject_rate is ANY_LABEL rejects only."
        ),
    }


def analyze_function_failure(rows, preds, rep_rows, fun_idx, per_label_qual) -> dict:
    from hyperlexical.classification_v6_semantic_pipeline_harden import BAKEOFF_THRESHOLDS

    fun_th = list(BAKEOFF_THRESHOLDS["function"])
    qual_fun = [r for r in rows if r.get("function_labels")]
    rep_fun = [r for r in rep_rows if r.get("function_labels")]
    per_label = {}
    admitted_recalls = []
    for j, lab in enumerate(FUNCTION_VOCAB):
        g = [r for r in rows if lab in (r.get("function_labels") or [])]
        rep_g = [r for r in rep_rows if lab in (r.get("function_labels") or [])]
        rej = [r for r in g if preds[r["identity"]]["gate_reject"]]
        adm = [r for r in g if not preds[r["identity"]]["gate_reject"]]
        tp = sum(1 for r in g if lab in preds[r["identity"]]["final_function_labels"])
        # pre-gate head would-fire among admitted
        would = 0
        for r in adm:
            sc = preds[r["identity"]]["raw_function_scores"][j]
            if sc >= fun_th[j]:
                would += 1
        qmetrics = (per_label_qual or {}).get(lab) or {}
        recall_adm = pct(
            sum(1 for r in adm if lab in preds[r["identity"]]["final_function_labels"]),
            len(adm),
        )
        admitted_recalls.append(recall_adm)
        # domains / styles
        dom = Counter(d for r in g for d in (r.get("domain_labels") or []) or ["__NONE__"])
        sty = Counter(source_style(r.get("source_family") or "") for r in g)
        lengths = [len(r.get("text") or "") for r in g]
        rep_lengths = [len(r.get("text") or "") for r in rep_g]
        per_label[lab] = {
            "qual_support": len(g),
            "rep_support": len(rep_g),
            "gate_reject_n": len(rej),
            "gate_reject_rate": pct(len(rej), len(g)),
            "admitted_n": len(adm),
            "final_tp": tp,
            "qual_f1": qmetrics.get("QUAL_f1"),
            "qual_precision": qmetrics.get("precision"),
            "qual_recall": qmetrics.get("recall"),
            "admitted_recall": recall_adm,
            "admitted_head_would_fire_rate": pct(would, len(adm)),
            "domain_mix": dict(dom),
            "style_mix": dict(sty),
            "qual_length_p50": sorted(lengths)[len(lengths) // 2] if lengths else None,
            "rep_length_p50": (
                sorted(rep_lengths)[len(rep_lengths) // 2] if rep_lengths else None
            ),
        }

    wiki_none_fun = sum(
        1
        for r in qual_fun
        if source_style(r.get("source_family") or "") == "encyclopedic_none_cue"
    )
    q_len = [len(r.get("text") or "") for r in qual_fun]
    r_len = [len(r.get("text") or "") for r in rep_fun]
    q_p50 = sorted(q_len)[len(q_len) // 2] if q_len else 0
    r_p50 = sorted(r_len)[len(r_len) // 2] if r_len else 0
    support_ratio = pct(len(qual_fun), len(rep_fun))

    payload = {
        "qual_function_n": len(qual_fun),
        "rep_function_n": len(rep_fun),
        "qual_to_rep_support_ratio": support_ratio,
        "gate_reject_rate_on_function_gold": pct(
            sum(1 for r in qual_fun if preds[r["identity"]]["gate_reject"]),
            len(qual_fun),
        ),
        "admitted_mean_recall": mean(admitted_recalls),
        "qual_function_wiki_none_share": pct(wiki_none_fun, len(qual_fun)),
        "length_shift_severe": (q_p50 >= 2.0 * max(1, r_p50)),
        "qual_function_length_p50": q_p50,
        "rep_function_length_p50": r_p50,
        "per_label": per_label,
        "qual_function_style": dict(
            Counter(source_style(r.get("source_family") or "") for r in qual_fun)
        ),
        "rep_function_style": dict(
            Counter(source_style(r.get("source_family") or "") for r in rep_fun)
        ),
    }
    from hyperlexical.classification_v6_qualification_003_failure_review import (
        classify_function_failure_mode,
    )

    payload["mode"] = classify_function_failure_mode(
        {"function_failure": payload, "positive_false_reject": {}}
    )
    return payload


def analyze_positive_representativeness(rows, rep_rows, train_rows) -> dict:
    q_pos = [r for r in rows if n_lab(r) > 0]
    r_pos = [r for r in rep_rows if n_lab(r) > 0]
    t_pos = [r for r in train_rows if n_lab(r) > 0]

    def dist(rs, keyfn):
        return Counter(keyfn(r) for r in rs)

    style_l1 = l1_dist(
        dist(q_pos, lambda r: source_style(r.get("source_family") or "")),
        dist(r_pos, lambda r: source_style(r.get("source_family") or "")),
    )
    len_l1 = l1_dist(
        dist(q_pos, lambda r: length_bucket(len(r.get("text") or ""))),
        dist(r_pos, lambda r: length_bucket(len(r.get("text") or ""))),
    )
    q_fun_prev = pct(sum(1 for r in q_pos if r.get("function_labels")), len(q_pos))
    r_fun_prev = pct(sum(1 for r in r_pos if r.get("function_labels")), len(r_pos))
    q_df = Counter()
    r_df = Counter()
    for r in q_pos:
        for d in r.get("domain_labels") or ["__NONE__"]:
            for f in r.get("function_labels") or []:
                q_df[(d, f)] += 1
    for r in r_pos:
        for d in r.get("domain_labels") or ["__NONE__"]:
            for f in r.get("function_labels") or []:
                r_df[(d, f)] += 1

    # length stats
    def len_stats(rs):
        L = sorted(len(r.get("text") or "") for r in rs)
        return {
            "n": len(L),
            "p50": L[len(L) // 2] if L else 0,
            "mean": mean([float(x) for x in L]) if L else 0.0,
        }

    severe_length = len_stats(q_pos)["p50"] >= 2.0 * max(1, len_stats(r_pos)["p50"])
    fun_prev_shift = abs(q_fun_prev - r_fun_prev) >= 0.15
    # OVERFIT if REP positives are almost purely short wikt and QUAL positives diverge hard
    rep_wikt_share = pct(
        sum(1 for r in r_pos if source_style(r.get("source_family") or "") == "wiktionary_sense"),
        len(r_pos),
    )
    qual_wikt_share = pct(
        sum(1 for r in q_pos if source_style(r.get("source_family") or "") == "wiktionary_sense"),
        len(q_pos),
    )

    if severe_length and style_l1 >= 0.25 and rep_wikt_share >= 0.85:
        cls = "POSITIVE_REPRESENTATIVENESS_OVERFIT"
    elif severe_length or style_l1 >= 0.20 or fun_prev_shift:
        cls = "POSITIVE_REPRESENTATIVENESS_PARTIAL"
    else:
        cls = "POSITIVE_REPRESENTATIVENESS_VALID"

    return {
        "class": cls,
        "qual_positive_n": len(q_pos),
        "rep_positive_n": len(r_pos),
        "train_positive_n": len(t_pos),
        "style_l1": style_l1,
        "length_bucket_l1": len_l1,
        "qual_length": len_stats(q_pos),
        "rep_length": len_stats(r_pos),
        "qual_function_prevalence_among_positives": q_fun_prev,
        "rep_function_prevalence_among_positives": r_fun_prev,
        "rep_wikt_share_among_positives": rep_wikt_share,
        "qual_wikt_share_among_positives": qual_wikt_share,
        "qual_domain_function_pairs_n": len(q_df),
        "rep_domain_function_pairs_n": len(r_df),
        "qual_style": dict(
            Counter(source_style(r.get("source_family") or "") for r in q_pos)
        ),
        "rep_style": dict(
            Counter(source_style(r.get("source_family") or "") for r in r_pos)
        ),
    }


def analyze_geometry(rows, preds, rep_rows, train_rows) -> dict:
    """Frozen-embedding geometry for function-positive traffic (optional GPU)."""
    try:
        import numpy as np
        import torch
        from hyperlexical.classification_v6_semantic_pipeline_harden import (
            SELECTED_ENCODER_MODEL_ID,
            SELECTED_ENCODER_REVISION,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "class": "INCONCLUSIVE_WITHOUT_GEOMETRY",
            "error": str(exc),
            "note": "geometry skipped",
        }

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    q_fun = [r for r in rows if r.get("function_labels")]
    r_fun = [r for r in rep_rows if r.get("function_labels")]
    t_fun = [r for r in train_rows if r.get("function_labels")]
    # cap for runtime
    import random

    rng = random.Random(20261003)
    r_sample = r_fun if len(r_fun) <= 200 else rng.sample(r_fun, 200)
    t_sample = t_fun if len(t_fun) <= 300 else rng.sample(t_fun, 300)
    q_pos = [r for r in rows if n_lab(r) > 0]
    r_pos = [r for r in rep_rows if n_lab(r) > 0]
    r_pos_s = r_pos if len(r_pos) <= 250 else rng.sample(r_pos, 250)

    texts = (
        [r["text"] for r in q_fun]
        + [r["text"] for r in r_sample]
        + [r["text"] for r in t_sample]
        + [r["text"] for r in q_pos]
        + [r["text"] for r in r_pos_s]
    )
    print(f"geometry_embed n={len(texts)} device={device}", flush=True)
    X = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        texts,
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    i = 0
    Xqf = X[i : i + len(q_fun)]
    i += len(q_fun)
    Xrf = X[i : i + len(r_sample)]
    i += len(r_sample)
    Xtf = X[i : i + len(t_sample)]
    i += len(t_sample)
    Xqp = X[i : i + len(q_pos)]
    i += len(q_pos)
    Xrp = X[i : i + len(r_pos_s)]

    # train function centroid vs QUAL/REP function
    if len(t_sample) == 0 or len(q_fun) == 0:
        return {"class": "INCONCLUSIVE_WITHOUT_GEOMETRY", "note": "empty_function_sets"}

    Ct = Xtf.mean(axis=0)
    Ct = Ct / max(1e-9, float(np.linalg.norm(Ct)))
    q_sim = (Xqf @ Ct).tolist()
    r_sim = (Xrf @ Ct).tolist()
    # admitted vs gate-rejected function golds
    adm_idx = [
        k
        for k, r in enumerate(q_fun)
        if not preds[r["identity"]]["gate_reject"]
    ]
    rej_idx = [
        k for k, r in enumerate(q_fun) if preds[r["identity"]]["gate_reject"]
    ]
    adm_sim = [q_sim[k] for k in adm_idx]
    rej_sim = [q_sim[k] for k in rej_idx]

    # head collapse check: among admitted function golds with intact geometry
    # (sim to train centroid >= REP p20), do heads still miss?
    r_p20 = sorted(r_sim)[max(0, len(r_sim) // 5)] if r_sim else 0.0
    intact_miss = 0
    intact_n = 0
    for k, r in enumerate(q_fun):
        if preds[r["identity"]]["gate_reject"]:
            continue
        if q_sim[k] >= r_p20:
            intact_n += 1
            gold = set(r.get("function_labels") or [])
            pred = set(preds[r["identity"]]["final_function_labels"] or [])
            if not (gold & pred):
                intact_miss += 1

    # positive neighborhood: QUAL pos mean sim to REP pos centroid
    Crp = Xrp.mean(axis=0)
    Crp = Crp / max(1e-9, float(np.linalg.norm(Crp)))
    qp_to_rep = (Xqp @ Crp).tolist()
    rp_to_rep = (Xrp @ Crp).tolist()

    geom_drop = mean(r_sim) - mean(q_sim)
    head_collapse = intact_n > 0 and pct(intact_miss, intact_n) >= 0.70
    rep_collapse = geom_drop >= 0.08 or (
        mean(q_sim) < 0.85 * max(1e-9, mean(r_sim))
    )

    if head_collapse and not rep_collapse:
        cls = "HEAD_GENERALIZATION_FAILURE"
    elif rep_collapse and not head_collapse:
        cls = "REPRESENTATION_GENERALIZATION_FAILURE"
    elif head_collapse and rep_collapse:
        cls = "MIXED_GEOMETRY_AND_HEAD"
    else:
        cls = "MIXED_GEOMETRY_AND_HEAD" if intact_n else "INCONCLUSIVE_WITHOUT_GEOMETRY"

    return {
        "class": cls,
        "device": str(device),
        "qual_function_n": len(q_fun),
        "rep_function_sample_n": len(r_sample),
        "train_function_sample_n": len(t_sample),
        "mean_sim_qual_function_to_train_centroid": mean(q_sim),
        "mean_sim_rep_function_to_train_centroid": mean(r_sim),
        "geometry_drop_qual_vs_rep": geom_drop,
        "admitted_function_mean_sim": mean(adm_sim) if adm_sim else None,
        "gate_rejected_function_mean_sim": mean(rej_sim) if rej_sim else None,
        "intact_geometry_admitted_n": intact_n,
        "intact_geometry_miss_n": intact_miss,
        "intact_geometry_miss_rate": pct(intact_miss, intact_n),
        "qual_pos_mean_sim_to_rep_pos_centroid": mean(qp_to_rep),
        "rep_pos_mean_sim_to_rep_pos_centroid": mean(rp_to_rep),
        "rep_function_sim_p20_threshold": r_p20,
    }


def analyze_learnability(fun_audit: dict, human_agreement: dict | None) -> dict:
    support = int(fun_audit.get("qual_function_n") or 0)
    rep_support = int(fun_audit.get("rep_function_n") or 0)
    wiki_share = float(fun_audit.get("qual_function_wiki_none_share") or 0.0)
    agree = (human_agreement or {}).get("mean_set_jaccard")
    per = fun_audit.get("per_label") or {}
    low_support_labels = sum(
        1 for lab, row in per.items() if int(row.get("qual_support") or 0) < 10
    )
    if support < 40 or (support / max(1, rep_support)) < 0.35:
        cls = "UNDERREPRESENTED"
    elif wiki_share >= 0.30:
        cls = "CONTEXT_DEPENDENT_IN_OPERATING_TEXT"
    elif low_support_labels >= 3:
        cls = "HUMAN_STABLE_BUT_STATISTICALLY_WEAK"
    elif agree is not None and float(agree) >= 0.90:
        cls = "HUMAN_STABLE_MODEL_LEARNABLE"
    else:
        cls = "HUMAN_STABLE_BUT_STATISTICALLY_WEAK"
    return {
        "class": cls,
        "qual_function_n": support,
        "rep_function_n": rep_support,
        "qual_function_wiki_none_share": wiki_share,
        "human_mean_set_jaccard": agree,
        "labels_with_qual_support_lt_10": low_support_labels,
        "note": (
            "Uses QUAL dual-annotation stability + support/style; does not reopen ontology."
        ),
    }


def inner() -> int:
    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text
    from hyperlexical.classification_v6_architecture_reset_bakeoff import AXIS_VOCABS
    from hyperlexical.classification_v6_data_foundation import utc_now_iso
    from hyperlexical.classification_v6_qualification_003_failure_review import (
        EXPECTED_QUAL_RESULT_SHA256,
        REJECTED_MICRO_FIXES,
        REVIEW_RULE,
        build_review_receipt,
        review_contract,
    )
    from hyperlexical.classification_v6_qualification_execute_003 import (
        EXPECTED_N_ROWS,
        EXPECTED_PACKAGE_SHA256,
        EXPECTED_SEAL_SHA256,
        QUALIFICATION_ID,
    )

    PRIVATE_REV.mkdir(mode=0o700, parents=True, exist_ok=True)
    contract = review_contract()
    write_private(PRIVATE_REV / "CONTRACT.json", contract)
    write_repo(REPO_ART / "contract.json", contract)

    print("load_artifacts", flush=True)
    seal = load_json(PRIVATE_QUAL / "QUALIFICATION_SEAL.json")
    receipt = load_json(PRIVATE_EXEC / "RECEIPT.json")
    summary = load_json(PRIVATE_EXEC / "SUMMARY.json")
    gates = load_json(PRIVATE_EXEC / "GATES.json")
    primary = load_json(PRIVATE_EXEC / "PRIMARY_METRICS.json")
    per_label = load_json(PRIVATE_EXEC / "PER_LABEL.json")
    rows = load_jsonl(PRIVATE_QUAL / "QUALIFICATION_ROWS.jsonl")
    preds_list = load_jsonl(PRIVATE_EXEC / "RAW_PREDICTIONS.jsonl")
    preds = {p["identity"]: p for p in preds_list}
    rep_rows = load_jsonl(PRIVATE_V2 / "REPRESENTATIVE_VALIDATION_V2.jsonl")
    train_rows = load_jsonl(PRIVATE_V2 / "TRAIN_V2.jsonl")
    try:
        human = load_json(PRIVATE_QUAL / "HUMAN_AGREEMENT_WITNESS.json")
    except Exception:
        human = None

    issues = []
    if seal.get("QUALIFICATION_STATE") != "EVALUATION_SPENT":
        issues.append(f"seal_state={seal.get('QUALIFICATION_STATE')}")
    if int(seal.get("qualification_model_executions") or 0) != 1:
        issues.append("executions_ne_1")
    if receipt.get("V6_QUALIFICATION_003_RESULT_SHA256") != EXPECTED_QUAL_RESULT_SHA256:
        issues.append("result_sha_mismatch")
    if len(rows) != EXPECTED_N_ROWS:
        issues.append(f"n_rows={len(rows)}")
    if receipt.get("package_sha256") != EXPECTED_PACKAGE_SHA256:
        issues.append("package_sha_mismatch")
    if issues:
        summary_out = {
            "PRIMARY_DIAGNOSIS": "INVALID_REVIEW_INPUT",
            "issues": issues,
            "NEXT_ACTION": "REPAIR_V6_QUALIFICATION_003_EXECUTION",
        }
        write_private(PRIVATE_REV / "SUMMARY.json", summary_out)
        write_repo(REPO_ART / "SUMMARY.json", summary_out)
        print(json.dumps(summary_out, indent=2))
        return 2

    fun_idx = {
        lab: i for i, lab in enumerate(AXIS_VOCABS["function"])
    }

    print("analyze_positive_false_reject", flush=True)
    pos_fr = analyze_positive_false_reject(rows, preds, fun_idx)
    print("analyze_function_failure", flush=True)
    fun = analyze_function_failure(rows, preds, rep_rows, fun_idx, per_label)
    print("analyze_positive_representativeness", flush=True)
    pos_rep = analyze_positive_representativeness(rows, rep_rows, train_rows)
    print("analyze_learnability", flush=True)
    learn = analyze_learnability(fun, human)
    print("analyze_geometry", flush=True)
    geom = analyze_geometry(rows, preds, rep_rows, train_rows)

    none_gate = {
        "operating_gates_pass": bool(
            gates.get("gates", {})
            .get("zero_label_false_positive_rate", {})
            .get("pass")
        )
        and bool(
            gates.get("gates", {})
            .get("zero_label_exact_rejection", {})
            .get("pass")
        ),
        "zero_label_FP": primary.get("zero_label_false_positive_rate"),
        "zero_label_exact": primary.get("zero_label_exact_rejection"),
        "function_gate_reject_rate": fun.get("gate_reject_rate_on_function_gold"),
        "recommendation_default": "NONE_GATE_FROZEN_RETAIN",
        "note": (
            "NONE operating gates passed on QUAL-003; freeze unless function loss "
            "is predominantly gate-induced with intact post-admission recall."
        ),
    }

    audit = {
        "qual_metrics": {
            "system_macro_f1": summary.get("system_macro_f1"),
            "DOMAIN": summary.get("DOMAIN_macro_f1"),
            "FUNCTION": summary.get("FUNCTION_macro_f1"),
            "MEDIATION": summary.get("MEDIATION_macro_f1"),
            "positive_only": summary.get("positive_only_system_macro_f1"),
            "false_reject_positive_rate_final_empty": primary.get(
                "false_reject_positive_rate"
            ),
        },
        "rep_witness": {
            "system": 0.36980892482696165,
            "FUNCTION": 0.22272324177813058,
            "positive_only": 0.415797546133708,
            "zero_fp": 0.08769931662870159,
        },
        "positive_false_reject": pos_fr,
        "function_failure": fun,
        "positive_representativeness": pos_rep,
        "representation_vs_head": geom,
        "function_learnability": learn,
        "none_gate": none_gate,
        "gate_table": gates.get("gates"),
    }

    # refresh function mode with full audit
    from hyperlexical.classification_v6_qualification_003_failure_review import (
        classify_function_failure_mode,
    )

    fun["mode"] = classify_function_failure_mode(audit)
    audit["function_failure"] = fun

    reviewed_at = utc_now_iso()
    receipt_out = build_review_receipt(audit, reviewed_at=reviewed_at)
    write_private(PRIVATE_REV / "AUDIT.json", audit)
    write_private(PRIVATE_REV / "RECEIPT.json", receipt_out)
    write_repo(
        REPO_ART / "audit.json",
        {
            k: v
            for k, v in audit.items()
            if k
            not in {
                # keep public; no row texts embedded
            }
        },
    )
    # public receipt without huge per-row geometry arrays — audit is summary-level
    public = {
        k: v
        for k, v in receipt_out.items()
        if k != "audit"
    }
    public["audit_summary"] = {
        "PRIMARY_DIAGNOSIS": receipt_out["PRIMARY_DIAGNOSIS"],
        "FUNCTION_FAILURE_MODE": receipt_out["FUNCTION_FAILURE_MODE"],
        "POSITIVE_REPRESENTATIVENESS": receipt_out["POSITIVE_REPRESENTATIVENESS"],
        "REPRESENTATION_VS_HEAD": receipt_out["REPRESENTATION_VS_HEAD"],
        "FUNCTION_LEARNABILITY": receipt_out["FUNCTION_LEARNABILITY"],
        "NONE_GATE_STATUS": receipt_out["NONE_GATE_STATUS"],
        "evidence_summary": receipt_out["evidence_summary"],
        "positive_false_reject_class": pos_fr.get("class"),
        "function_support": {
            "qual": fun.get("qual_function_n"),
            "rep": fun.get("rep_function_n"),
            "ratio": fun.get("qual_to_rep_support_ratio"),
        },
    }
    public["SYSTEM_REVIEW_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {k: v for k, v in public.items() if k != "SYSTEM_REVIEW_RECEIPT_SHA256"}
        )
    )
    write_repo(REPO_ART / "receipt.json", public)
    write_repo(REPO_ART / "RECEIPT.json", public)
    write_repo(
        SPEC / "classification-v6-qualification-003-failure-review-receipt-20261001.json",
        public,
    )

    summary_out = {
        "REVIEW_RULE": REVIEW_RULE,
        "PRIMARY_DIAGNOSIS": receipt_out["PRIMARY_DIAGNOSIS"],
        "FUNCTION_FAILURE_MODE": receipt_out["FUNCTION_FAILURE_MODE"],
        "POSITIVE_REPRESENTATIVENESS": receipt_out["POSITIVE_REPRESENTATIVENESS"],
        "REPRESENTATION_VS_HEAD": receipt_out["REPRESENTATION_VS_HEAD"],
        "FUNCTION_LEARNABILITY": receipt_out["FUNCTION_LEARNABILITY"],
        "NONE_GATE_STATUS": receipt_out["NONE_GATE_STATUS"],
        "NEXT_ACTION": receipt_out["NEXT_ACTION"],
        "gate_reject_rate_on_positives": pos_fr["gate_reject_rate_on_positives"],
        "final_empty_rate_on_positives": pos_fr["final_empty_rate_on_positives"],
        "post_admission_empty_share": pos_fr[
            "post_admission_empty_share_of_final_empty"
        ],
        "function_gate_reject_rate": fun["gate_reject_rate_on_function_gold"],
        "function_admitted_mean_recall": fun["admitted_mean_recall"],
        "qual_function_n": fun["qual_function_n"],
        "rep_function_n": fun["rep_function_n"],
        "REJECTED_MICRO_FIXES": dict(REJECTED_MICRO_FIXES),
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "MODEL_WIDE_BEST_MUTATED": False,
        "RECEIPT": public["SYSTEM_REVIEW_RECEIPT_SHA256"],
        "QUAL_RESULT_SHA256": EXPECTED_QUAL_RESULT_SHA256,
        "PACKAGE_SHA256": EXPECTED_PACKAGE_SHA256,
        "QUAL_SEAL_SHA256": EXPECTED_SEAL_SHA256,
    }
    write_private(PRIVATE_REV / "SUMMARY.json", summary_out)
    write_private(PRIVATE_REV / "POINTER.json", {
        "MODEL_WIDE_BEST_MUTATED": False,
        "V6_OPERATING_PIPELINE_CANDIDATE_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
    })
    write_repo(REPO_ART / "SUMMARY.json", summary_out)
    write_repo(REPO_ART / "summary.json", summary_out)
    write_repo(REPO_ART / "pointer.json", {
        "MODEL_WIDE_BEST_MUTATED": False,
        "V6_OPERATING_PIPELINE_CANDIDATE_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
    })

    md = f"""# REVIEW_V6_QUALIFICATION_003_FAILURE

```text
PRIMARY_DIAGNOSIS = {receipt_out['PRIMARY_DIAGNOSIS']}
FUNCTION_FAILURE_MODE = {receipt_out['FUNCTION_FAILURE_MODE']}
POSITIVE_REPRESENTATIVENESS = {receipt_out['POSITIVE_REPRESENTATIVENESS']}
REPRESENTATION_VS_HEAD = {receipt_out['REPRESENTATION_VS_HEAD']}
FUNCTION_LEARNABILITY = {receipt_out['FUNCTION_LEARNABILITY']}
NONE_GATE_STATUS = {receipt_out['NONE_GATE_STATUS']}

gate_reject_on_positives = {pos_fr['gate_reject_rate_on_positives']:.3f}
final_empty_on_positives = {pos_fr['final_empty_rate_on_positives']:.3f}
post_admission_share_of_empty = {pos_fr['post_admission_empty_share_of_final_empty']:.3f}
function_gold n = {fun['qual_function_n']} (REP {fun['rep_function_n']})
function_gate_reject = {fun['gate_reject_rate_on_function_gold']:.3f}
function_admitted_mean_recall = {fun['admitted_mean_recall']:.3f}

NEXT_ACTION = {receipt_out['NEXT_ACTION']}
```

NONE operating gates remain passed; do not retune ANY_LABEL here.
QUAL-003 stays EVALUATION_SPENT / unused for optimization.
MODEL_WIDE_BEST unchanged. HUB_PUBLISH_AUTHORIZED = false.
"""
    write_repo(
        SPEC / "classification-v6-qualification-003-failure-review-20261001.md", md
    )
    print(json.dumps(summary_out, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V6_QUAL_EXEC_INNER") == "1":
        return inner()
    PRIVATE_REV.mkdir(mode=0o700, parents=True, exist_ok=True)
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
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e",
        "HLX_V2_FORWARD_ONTOLOGY=1",
        "-e",
        "HLX_V6_QUAL_EXEC_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(
            REPO
            / "scripts/spark/run_classification_v6_qualification_003_failure_review.py"
        ),
    ]
    log = PRIVATE_REV / "review_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(
            cmd, check=False, stdout=handle, stderr=subprocess.STDOUT
        )
    try:
        print(log.read_text(encoding="utf-8")[-50000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
