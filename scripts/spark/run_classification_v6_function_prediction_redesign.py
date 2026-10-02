"""REDESIGN_V6_FUNCTION_PREDICTION.

Train/select FUNCTION-only formulations under frozen encoder + frozen
ANY_LABEL gate. DOMAIN and MEDIATION predictions come from sealed old heads.
"""

from __future__ import annotations

import hashlib
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
    "/home/morpheus/hlx-private/classification-v6-function-prediction-redesign-20261002"
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
    / "HLX-CLASSIFICATION-V6-FUNCTION-PREDICTION-REDESIGN-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
SEED = 20261005
MAX_LEN = 192
BATCH = 32
EPOCHS = 40
LR = 1e-2

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))

# Adjacent function pairs for hard-negative design.
ADJACENT = {
    "function.evaluative_stance": ("function.conflictive_force", "function.memetic_form"),
    "function.conflictive_force": ("function.evaluative_stance", "function.memetic_form"),
    "function.memetic_form": ("function.evaluative_stance", "function.conflictive_force"),
    "function.relational_intimacy": ("function.evaluative_stance",),
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


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def n_lab(r: dict) -> int:
    return (
        len(r.get("domain_labels") or [])
        + len(r.get("function_labels") or [])
        + len(r.get("mediation_labels") or [])
    )


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


def set_seeds(seed: int) -> None:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


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
    import torch as T

    return T.cat(vecs, dim=0).numpy()


def build_mlp(hidden, n_out, device, mid=128):
    import torch.nn as nn

    return nn.Sequential(
        nn.Linear(hidden, mid), nn.ReLU(), nn.Linear(mid, n_out)
    ).to(device)


def load_torch_bundle(path: Path):
    import io
    import torch

    raw = sudo_read_bytes(path)
    try:
        return torch.load(io.BytesIO(raw), map_location="cpu", weights_only=False), raw
    except TypeError:
        return torch.load(io.BytesIO(raw), map_location="cpu"), raw


def load_heads(path: Path, vocabs, device):
    bundle, raw = load_torch_bundle(path)
    heads = {}
    for axis, vocab in vocabs.items():
        m = build_mlp(768, len(vocab), device)
        m.load_state_dict(bundle["state"][axis])
        m.eval()
        for p in m.parameters():
            p.requires_grad_(False)
        heads[axis] = m
    return heads, bundle, sha256_bytes(raw)


def load_gate(path: Path, device):
    bundle, raw = load_torch_bundle(path)
    m = build_mlp(768, 1, device)
    m.load_state_dict(bundle["state"])
    m.eval()
    for p in m.parameters():
        p.requires_grad_(False)
    return m, bundle, sha256_bytes(raw)


def scores_from_heads(heads, X, device, axes=None):
    import torch

    out = {}
    with torch.no_grad():
        xt = torch.tensor(X, device=device)
        for axis, model in heads.items():
            if axes is not None and axis not in axes:
                continue
            out[axis] = torch.sigmoid(model(xt)).cpu().numpy()
    return out


def gate_scores(model, X, device):
    import torch

    with torch.no_grad():
        xt = torch.tensor(X, dtype=torch.float32, device=device)
        return torch.sigmoid(model(xt)).cpu().numpy().reshape(-1)


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


def pack_axis(gold, pred, vocab):
    import numpy as np

    g = np.asarray(gold)
    p = np.asarray(pred)
    per = {}
    f1s = []
    for j, lab in enumerate(vocab):
        f1 = f1_binary(g[:, j], p[:, j])
        f1s.append(f1)
        tp = int(((g[:, j] == 1) & (p[:, j] == 1)).sum())
        fp = int(((g[:, j] == 0) & (p[:, j] == 1)).sum())
        fn = int(((g[:, j] == 1) & (p[:, j] == 0)).sum())
        prec = tp / max(1, tp + fp)
        rec = tp / max(1, tp + fn)
        per[lab] = {
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "support": int(g[:, j].sum()),
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
    return {"macro_f1": float(sum(f1s) / max(1, len(f1s))), "per_label": per}


def length_bucket(n: int) -> str:
    if n < 60:
        return "short"
    if n < 200:
        return "medium"
    return "long"


def source_style(sf: str) -> str:
    s = (sf or "").lower()
    if "wiki_culture" in s or "wiki_html_pos" in s:
        return "encyclopedic_positive"
    if "wikt" in s:
        return "wiktionary_sense"
    if "firecrawl" in s:
        return "firecrawl_observed"
    return "other"


def train_binary_verifier(X, y, device, *, mid=64, epochs=EPOCHS, lr=LR, seed=SEED):
    """Train one binary MLP; y in {0,1}."""
    import numpy as np
    import torch
    import torch.nn as nn

    set_seeds(seed)
    model = build_mlp(X.shape[1], 1, device, mid=mid)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    # Class-balanced BCE
    pos = float((y == 1).sum())
    neg = float((y == 0).sum())
    pos_weight = torch.tensor([neg / max(1.0, pos)], device=device)
    bce = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    xt = torch.tensor(X, device=device)
    yt = torch.tensor(y.reshape(-1, 1), device=device)
    model.train()
    for _ in range(epochs):
        opt.zero_grad()
        loss = bce(model(xt), yt)
        loss.backward()
        opt.step()
    model.eval()
    with torch.no_grad():
        scores = torch.sigmoid(model(xt)).cpu().numpy().reshape(-1)
    return model, scores


def score_binary(model, X, device):
    import torch

    with torch.no_grad():
        xt = torch.tensor(X, device=device)
        return torch.sigmoid(model(xt)).cpu().numpy().reshape(-1)


def build_neg_mask(rows, lab: str, fun_vocab: list[str]):
    """Hard-negative strata masks for one function label."""
    import numpy as np

    n = len(rows)
    y = np.zeros(n, dtype=np.float32)
    strata = {
        "positive": np.zeros(n, dtype=bool),
        "other_function": np.zeros(n, dtype=bool),
        "domain_only": np.zeros(n, dtype=bool),
        "zero_label": np.zeros(n, dtype=bool),
        "adjacent_function": np.zeros(n, dtype=bool),
    }
    adj = set(ADJACENT.get(lab, ()))
    for i, r in enumerate(rows):
        funs = set(r.get("function_labels") or [])
        doms = r.get("domain_labels") or []
        if lab in funs:
            y[i] = 1.0
            strata["positive"][i] = True
        else:
            if funs:
                strata["other_function"][i] = True
                if funs & adj:
                    strata["adjacent_function"][i] = True
            elif doms:
                strata["domain_only"][i] = True
            elif n_lab(r) == 0:
                strata["zero_label"][i] = True
    return y, strata


def sample_training_pairs(y, strata, rng, *, max_neg_per_pos=6):
    """Balanced index sample emphasizing hard negatives."""
    import numpy as np

    pos_idx = np.where(y == 1)[0].tolist()
    if not pos_idx:
        return np.arange(len(y))
    neg_pools = []
    for key in ("adjacent_function", "other_function", "domain_only", "zero_label"):
        idxs = np.where(strata[key])[0].tolist()
        rng.shuffle(idxs)
        neg_pools.append(idxs)
    chosen = list(pos_idx)
    need = len(pos_idx) * max_neg_per_pos
    # Round-robin hard negatives
    cursors = [0] * len(neg_pools)
    while len(chosen) - len(pos_idx) < need:
        progressed = False
        for p, pool in enumerate(neg_pools):
            if cursors[p] < len(pool):
                chosen.append(pool[cursors[p]])
                cursors[p] += 1
                progressed = True
                if len(chosen) - len(pos_idx) >= need:
                    break
        if not progressed:
            break
    rng.shuffle(chosen)
    return np.asarray(sorted(set(chosen)), dtype=np.int64)


def threshold_from_dev(scores, gold) -> float:
    """Pick threshold maximizing F1 on DEV for one binary label."""
    import numpy as np

    best_t, best_f1 = 0.5, -1.0
    for t in np.linspace(0.05, 0.95, 37):
        pred = (scores >= t).astype(np.int32)
        f1 = f1_binary(gold, pred)
        if f1 > best_f1:
            best_f1, best_t = f1, float(t)
    return best_t


def train_independent_verifiers(rows, X, fun_vocab, device):
    import numpy as np

    rng = random.Random(SEED)
    models = {}
    train_scores = np.zeros((len(rows), len(fun_vocab)), dtype=np.float32)
    for j, lab in enumerate(fun_vocab):
        y, strata = build_neg_mask(rows, lab, fun_vocab)
        idx = sample_training_pairs(y, strata, rng)
        model, _ = train_binary_verifier(
            X[idx], y[idx], device, mid=64, seed=SEED + j
        )
        models[lab] = model
        train_scores[:, j] = score_binary(model, X, device)
    return models, train_scores


def score_independent(models, X, fun_vocab, device):
    import numpy as np

    out = np.zeros((len(X), len(fun_vocab)), dtype=np.float32)
    for j, lab in enumerate(fun_vocab):
        out[:, j] = score_binary(models[lab], X, device)
    return out


def train_semantic_matching(rows, X, def_embs, fun_vocab, device):
    """Cosine to frozen definitions + per-label affine calibration a*sim+b."""
    import numpy as np
    import torch
    import torch.nn as nn

    sims = X @ def_embs.T  # (n, 4)
    calibrators = {}
    cal_scores = np.zeros_like(sims)
    for j, lab in enumerate(fun_vocab):
        y, strata = build_neg_mask(rows, lab, fun_vocab)
        rng = random.Random(SEED + 100 + j)
        idx = sample_training_pairs(y, strata, rng)
        set_seeds(SEED + 100 + j)
        # affine: sigmoid(a * sim + b)
        a = nn.Parameter(torch.tensor([2.0], device=device))
        b = nn.Parameter(torch.tensor([-0.5], device=device))
        opt = torch.optim.Adam([a, b], lr=5e-2)
        pos = float((y[idx] == 1).sum())
        neg = float((y[idx] == 0).sum())
        pw = torch.tensor([neg / max(1.0, pos)], device=device)
        bce = nn.BCEWithLogitsLoss(pos_weight=pw)
        s = torch.tensor(sims[idx, j], device=device)
        yt = torch.tensor(y[idx], device=device)
        for _ in range(80):
            opt.zero_grad()
            logits = a * s + b
            loss = bce(logits, yt)
            loss.backward()
            opt.step()
        calibrators[lab] = (float(a.detach().cpu()), float(b.detach().cpu()))
        cal_scores[:, j] = 1.0 / (
            1.0 + np.exp(-(calibrators[lab][0] * sims[:, j] + calibrators[lab][1]))
        )
    return calibrators, cal_scores, sims


def score_semantic(X, def_embs, calibrators, fun_vocab):
    import numpy as np

    sims = X @ def_embs.T
    out = np.zeros_like(sims)
    for j, lab in enumerate(fun_vocab):
        a, b = calibrators[lab]
        out[:, j] = 1.0 / (1.0 + np.exp(-(a * sims[:, j] + b)))
    return out


def train_hybrid(rows, X, def_embs, fun_vocab, device):
    """Per-function binary on [text; def; text*def]."""
    import numpy as np
    import torch
    import torch.nn as nn

    models = {}
    scores = np.zeros((len(rows), len(fun_vocab)), dtype=np.float32)
    for j, lab in enumerate(fun_vocab):
        y, strata = build_neg_mask(rows, lab, fun_vocab)
        rng = random.Random(SEED + 200 + j)
        idx = sample_training_pairs(y, strata, rng)
        d = def_embs[j]
        feats = np.concatenate(
            [X, np.broadcast_to(d, X.shape), X * d], axis=1
        ).astype(np.float32)
        model, _ = train_binary_verifier(
            feats[idx], y[idx], device, mid=96, seed=SEED + 200 + j
        )
        models[lab] = model
        scores[:, j] = score_binary(model, feats, device)
    return models, scores


def score_hybrid(models, X, def_embs, fun_vocab, device):
    import numpy as np

    out = np.zeros((len(X), len(fun_vocab)), dtype=np.float32)
    for j, lab in enumerate(fun_vocab):
        d = def_embs[j]
        feats = np.concatenate(
            [X, np.broadcast_to(d, X.shape), X * d], axis=1
        ).astype(np.float32)
        out[:, j] = score_binary(models[lab], feats, device)
    return out


def run_operating(
    rows,
    X,
    fun_scores,
    fun_thresholds,
    dom_scores,
    med_scores,
    gate,
    gate_th,
    vocabs,
    thresholds_dom_med,
    tech_idx,
    ai_idx,
    device,
):
    """Frozen domain/mediation + candidate function + frozen gate + hierarchy."""
    import numpy as np

    gsc = gate_scores(gate, X, device)
    reject = gsc < float(gate_th)

    fun_pred = (fun_scores >= np.asarray(fun_thresholds)).astype(np.int32)
    dom_pred = (dom_scores >= np.asarray(thresholds_dom_med["domain"])).astype(np.int32)
    med_pred = (med_scores >= np.asarray(thresholds_dom_med["mediation"])).astype(
        np.int32
    )
    fun_pred[reject] = 0
    dom_pred[reject] = 0
    med_pred[reject] = 0

    d = dom_pred.copy()
    hier_corr = 0
    for i in range(d.shape[0]):
        if d[i, ai_idx] == 1 and d[i, tech_idx] == 0:
            d[i, tech_idx] = 1
            hier_corr += 1

    golds = {
        a: np.asarray(
            [multi_hot(r.get(f"{a}_labels"), vocabs[a]) for r in rows], dtype=np.int32
        )
        for a in vocabs
    }
    preds = {"domain": d, "function": fun_pred, "mediation": med_pred}
    axis = {a: pack_axis(golds[a], preds[a], vocabs[a]) for a in vocabs}
    system = mean([axis[a]["macro_f1"] for a in vocabs])

    zero_idx = [i for i, r in enumerate(rows) if n_lab(r) == 0]
    pos_idx = [i for i, r in enumerate(rows) if n_lab(r) > 0]
    pred_any = np.zeros(len(rows), dtype=np.int32)
    for a in vocabs:
        pred_any = np.maximum(pred_any, preds[a].max(axis=1))
    zero_fp = float(pred_any[zero_idx].mean()) if zero_idx else 0.0
    zero_exact = float((pred_any[zero_idx] == 0).mean()) if zero_idx else 0.0
    pos_macros = []
    if pos_idx:
        for a in vocabs:
            pos_macros.append(
                pack_axis(golds[a][pos_idx], preds[a][pos_idx], vocabs[a])["macro_f1"]
            )

    fun_idx = [i for i, r in enumerate(rows) if r.get("function_labels")]
    by_source, by_len, by_dom = defaultdict(list), defaultdict(list), defaultdict(list)
    for i in fun_idx:
        r = rows[i]
        by_source[source_style(r.get("source_family") or "")].append(i)
        by_len[length_bucket(len(r.get("text") or ""))].append(i)
        for dlab in r.get("domain_labels") or ["__NONE__"]:
            by_dom[dlab].append(i)

    def slice_fun(idxs):
        if not idxs:
            return None
        return pack_axis(
            golds["function"][idxs], preds["function"][idxs], vocabs["function"]
        )["macro_f1"]

    return {
        "system_macro_f1": system,
        "DOMAIN_macro_f1": axis["domain"]["macro_f1"],
        "FUNCTION_macro_f1": axis["function"]["macro_f1"],
        "MEDIATION_macro_f1": axis["mediation"]["macro_f1"],
        "positive_only_system_macro_f1": mean(pos_macros) if pos_macros else 0.0,
        "zero_label_false_positive_rate": zero_fp,
        "zero_label_exact_rejection": zero_exact,
        "hierarchy_corrections": hier_corr,
        "gate_reject_rate": float(reject.mean()),
        "n_rows": len(rows),
        "n_zero": len(zero_idx),
        "n_positive": len(pos_idx),
        "n_function": len(fun_idx),
        "per_label_function": axis["function"]["per_label"],
        "function_by_source": {k: slice_fun(v) for k, v in by_source.items()},
        "function_by_length": {k: slice_fun(v) for k, v in by_len.items()},
        "function_by_domain": {k: slice_fun(v) for k, v in list(by_dom.items())[:20]},
        "fun_thresholds": list(map(float, fun_thresholds)),
    }


def save_function_bundle(path: Path, payload: dict) -> str:
    import torch

    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    torch.save(payload, path)
    os.chmod(path, 0o600)
    return sha256_bytes(path.read_bytes())


def inner() -> int:
    import numpy as np
    import torch
    from hyperlexical.classification_v6_architecture_reset_bakeoff import AXIS_VOCABS
    from hyperlexical.classification_v6_data_foundation import utc_now_iso
    from hyperlexical.classification_v6_function_prediction_redesign import (
        BASELINE_REP_V3,
        FUNCTION_DEFINITIONS,
        FUNCTION_VOCAB,
        PHASE_RULE,
        build_redesign_receipt,
        classify_outcome,
        redesign_contract,
        select_best_on_dev,
    )
    from hyperlexical.classification_v6_operating_pipeline_harden import (
        WITNESS_GATE_THRESHOLD,
    )
    from hyperlexical.classification_v6_qualification_execute_003 import (
        EXPECTED_PACKAGE_SHA256,
    )
    from hyperlexical.classification_v6_semantic_pipeline_harden import (
        BAKEOFF_THRESHOLDS,
        SELECTED_ENCODER_MODEL_ID,
        SELECTED_ENCODER_REVISION,
    )

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    contract = redesign_contract()
    write_private(PRIVATE / "CONTRACT.json", contract)
    write_repo(REPO_ART / "contract.json", contract)

    print("load_v3_and_package", flush=True)
    train = load_jsonl(PRIVATE_V3 / "TRAIN_V3.jsonl")
    dev = load_jsonl(PRIVATE_V3 / "DEV_SELECTION_V3.jsonl")
    rep = load_jsonl(PRIVATE_V3 / "REPRESENTATIVE_VALIDATION_V3.jsonl")
    if not train or not dev or not rep:
        raise RuntimeError("V3 surfaces missing")

    vocabs = AXIS_VOCABS
    fun_vocab = list(vocabs["function"])
    assert fun_vocab == list(FUNCTION_VOCAB)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    old_heads, _, old_sha = load_heads(
        PRIVATE_PKG / "heads" / "axis_nonlinear_heads.pt", vocabs, device
    )
    gate, _, gate_sha = load_gate(PRIVATE_PKG / "heads" / "any_evidence_gate.pt", device)
    gate_th = float(WITNESS_GATE_THRESHOLD)
    th_dom_med = {
        "domain": list(BAKEOFF_THRESHOLDS["domain"]),
        "mediation": list(BAKEOFF_THRESHOLDS["mediation"]),
    }
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")

    print(
        f"embed n_train={len(train)} n_dev={len(dev)} n_rep={len(rep)} device={device}",
        flush=True,
    )
    Xtr = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        [r["text"] for r in train],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    Xdv = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        [r["text"] for r in dev],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    Xrp = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        [r["text"] for r in rep],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    def_texts = [FUNCTION_DEFINITIONS[lab] for lab in fun_vocab]
    def_embs = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        def_texts,
        device,
        revision=SELECTED_ENCODER_REVISION,
    )

    # Frozen domain/mediation scores (never trained here)
    print("frozen_domain_mediation_scores", flush=True)
    dom_dv = scores_from_heads(old_heads, Xdv, device, axes={"domain"})["domain"]
    med_dv = scores_from_heads(old_heads, Xdv, device, axes={"mediation"})["mediation"]
    dom_rp = scores_from_heads(old_heads, Xrp, device, axes={"domain"})["domain"]
    med_rp = scores_from_heads(old_heads, Xrp, device, axes={"mediation"})["mediation"]

    # Baseline old function head on DEV/REP for reference
    old_fun_dv_ord = scores_from_heads(old_heads, Xdv, device, axes={"function"})[
        "function"
    ]
    old_fun_rp_ord = scores_from_heads(old_heads, Xrp, device, axes={"function"})[
        "function"
    ]
    old_fun_th = list(BAKEOFF_THRESHOLDS["function"])

    baseline_dev = run_operating(
        dev,
        Xdv,
        old_fun_dv_ord,
        old_fun_th,
        dom_dv,
        med_dv,
        gate,
        gate_th,
        vocabs,
        th_dom_med,
        tech_idx,
        ai_idx,
        device,
    )
    baseline_rep = run_operating(
        rep,
        Xrp,
        old_fun_rp_ord,
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
    print(
        f"baseline_REP FUNCTION={baseline_rep['FUNCTION_macro_f1']:.4f} "
        f"system={baseline_rep['system_macro_f1']:.4f}",
        flush=True,
    )

    # --- Formulation A: independent binary verifiers ---
    print("train_INDEPENDENT_BINARY_VERIFIERS", flush=True)
    ind_models, _ = train_independent_verifiers(train, Xtr, fun_vocab, device)
    ind_dv = score_independent(ind_models, Xdv, fun_vocab, device)
    Ydv_fun = np.asarray(
        [multi_hot(r.get("function_labels"), fun_vocab) for r in dev], dtype=np.int32
    )
    ind_th = [
        threshold_from_dev(ind_dv[:, j], Ydv_fun[:, j]) for j in range(len(fun_vocab))
    ]
    ind_dev = run_operating(
        dev,
        Xdv,
        ind_dv,
        ind_th,
        dom_dv,
        med_dv,
        gate,
        gate_th,
        vocabs,
        th_dom_med,
        tech_idx,
        ai_idx,
        device,
    )
    ind_dev["formulation"] = "INDEPENDENT_BINARY_VERIFIERS"

    # --- Formulation B: semantic matching ---
    print("train_FUNCTION_SEMANTIC_MATCHING", flush=True)
    cals, _, _ = train_semantic_matching(train, Xtr, def_embs, fun_vocab, device)
    sem_dv = score_semantic(Xdv, def_embs, cals, fun_vocab)
    sem_th = [
        threshold_from_dev(sem_dv[:, j], Ydv_fun[:, j]) for j in range(len(fun_vocab))
    ]
    sem_dev = run_operating(
        dev,
        Xdv,
        sem_dv,
        sem_th,
        dom_dv,
        med_dv,
        gate,
        gate_th,
        vocabs,
        th_dom_med,
        tech_idx,
        ai_idx,
        device,
    )
    sem_dev["formulation"] = "FUNCTION_SEMANTIC_MATCHING"

    # --- Formulation C: hybrid ---
    print("train_HYBRID_VERIFIER", flush=True)
    hyb_models, _ = train_hybrid(train, Xtr, def_embs, fun_vocab, device)
    hyb_dv = score_hybrid(hyb_models, Xdv, def_embs, fun_vocab, device)
    hyb_th = [
        threshold_from_dev(hyb_dv[:, j], Ydv_fun[:, j]) for j in range(len(fun_vocab))
    ]
    hyb_dev = run_operating(
        dev,
        Xdv,
        hyb_dv,
        hyb_th,
        dom_dv,
        med_dv,
        gate,
        gate_th,
        vocabs,
        th_dom_med,
        tech_idx,
        ai_idx,
        device,
    )
    hyb_dev["formulation"] = "HYBRID_VERIFIER"

    selection = select_best_on_dev([ind_dev, sem_dev, hyb_dev])
    selected = selection["selected"]
    print(f"selected_on_DEV={selected}", flush=True)

    # Score REP once for selected
    if selected == "INDEPENDENT_BINARY_VERIFIERS":
        fun_rp = score_independent(ind_models, Xrp, fun_vocab, device)
        fun_th = ind_th
        bundle = {
            "formulation": selected,
            "kind": "independent_binary_mlps",
            "state": {
                lab: {k: v.detach().cpu() for k, v in m.state_dict().items()}
                for lab, m in ind_models.items()
            },
            "thresholds": fun_th,
            "fun_vocab": fun_vocab,
        }
    elif selected == "FUNCTION_SEMANTIC_MATCHING":
        fun_rp = score_semantic(Xrp, def_embs, cals, fun_vocab)
        fun_th = sem_th
        bundle = {
            "formulation": selected,
            "kind": "cosine_def_matching_affine",
            "calibrators": cals,
            "thresholds": fun_th,
            "fun_vocab": fun_vocab,
            "definitions": FUNCTION_DEFINITIONS,
        }
    else:
        fun_rp = score_hybrid(hyb_models, Xrp, def_embs, fun_vocab, device)
        fun_th = hyb_th
        bundle = {
            "formulation": selected,
            "kind": "hybrid_text_def_product_mlp",
            "state": {
                lab: {k: v.detach().cpu() for k, v in m.state_dict().items()}
                for lab, m in hyb_models.items()
            },
            "thresholds": fun_th,
            "fun_vocab": fun_vocab,
            "definitions": FUNCTION_DEFINITIONS,
        }

    print("eval_selected_on_REP_V3", flush=True)
    candidate_rep = run_operating(
        rep,
        Xrp,
        fun_rp,
        fun_th,
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
    candidate_rep["formulation"] = selected

    # Also record all three REP scores for transparency (still one selected eval path)
    # Only selected is used for outcome; others are diagnostic DEV already done.
    outcome = classify_outcome(candidate=candidate_rep, baseline=baseline_rep)
    # Prefer sealed expand baseline constants if live replay drifts slightly
    outcome_vs_sealed = classify_outcome(
        candidate=candidate_rep, baseline=BASELINE_REP_V3
    )

    bundle_sha = save_function_bundle(
        PRIVATE / "heads" / "function_redesign_selected.pt", bundle
    )

    sealed_at = utc_now_iso()
    summary = {
        "PHASE_RULE": PHASE_RULE,
        "OUTCOME": outcome_vs_sealed["OUTCOME"],
        "NEXT_ACTION": outcome_vs_sealed["NEXT_ACTION"],
        "selected_formulation": selected,
        "selection": selection,
        "DEV_V3_by_formulation": {
            "INDEPENDENT_BINARY_VERIFIERS": {
                k: ind_dev[k]
                for k in (
                    "FUNCTION_macro_f1",
                    "system_macro_f1",
                    "positive_only_system_macro_f1",
                    "DOMAIN_macro_f1",
                    "MEDIATION_macro_f1",
                    "zero_label_false_positive_rate",
                    "per_label_function",
                    "fun_thresholds",
                )
            },
            "FUNCTION_SEMANTIC_MATCHING": {
                k: sem_dev[k]
                for k in (
                    "FUNCTION_macro_f1",
                    "system_macro_f1",
                    "positive_only_system_macro_f1",
                    "DOMAIN_macro_f1",
                    "MEDIATION_macro_f1",
                    "zero_label_false_positive_rate",
                    "per_label_function",
                    "fun_thresholds",
                )
            },
            "HYBRID_VERIFIER": {
                k: hyb_dev[k]
                for k in (
                    "FUNCTION_macro_f1",
                    "system_macro_f1",
                    "positive_only_system_macro_f1",
                    "DOMAIN_macro_f1",
                    "MEDIATION_macro_f1",
                    "zero_label_false_positive_rate",
                    "per_label_function",
                    "fun_thresholds",
                )
            },
        },
        "baseline_REP_V3_live": {
            k: baseline_rep[k]
            for k in (
                "system_macro_f1",
                "DOMAIN_macro_f1",
                "FUNCTION_macro_f1",
                "MEDIATION_macro_f1",
                "positive_only_system_macro_f1",
                "zero_label_false_positive_rate",
                "zero_label_exact_rejection",
                "per_label_function",
            )
        },
        "baseline_REP_V3_sealed": dict(BASELINE_REP_V3),
        "candidate_REP_V3": {
            k: candidate_rep[k]
            for k in (
                "formulation",
                "system_macro_f1",
                "DOMAIN_macro_f1",
                "FUNCTION_macro_f1",
                "MEDIATION_macro_f1",
                "positive_only_system_macro_f1",
                "zero_label_false_positive_rate",
                "zero_label_exact_rejection",
                "per_label_function",
                "function_by_source",
                "function_by_length",
                "function_by_domain",
                "fun_thresholds",
            )
        },
        "deltas_vs_sealed": {
            "function": outcome_vs_sealed["function_delta"],
            "system": outcome_vs_sealed["system_delta"],
            "positive_only": outcome_vs_sealed["positive_only_delta"],
        },
        "deltas_vs_live_baseline": {
            "function": outcome["function_delta"],
            "system": outcome["system_delta"],
            "positive_only": outcome["positive_only_delta"],
        },
        "none_preserved": outcome_vs_sealed["none_preserved"],
        "any_function_collapsed": outcome_vs_sealed["any_function_collapsed"],
        "frozen": {
            "gate_threshold": gate_th,
            "gate_sha256": gate_sha,
            "old_heads_sha256": old_sha,
            "function_bundle_sha256": bundle_sha,
            "package_sha256": EXPECTED_PACKAGE_SHA256,
            "encoder": SELECTED_ENCODER_MODEL_ID,
            "DOMAIN_HEAD_MUTATED": False,
            "MEDIATION_HEAD_MUTATED": False,
            "NONE_GATE_MUTATED": False,
        },
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "MODEL_WIDE_BEST_MUTATED": False,
    }

    receipt = build_redesign_receipt(summary, sealed_at=sealed_at)
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_private(PRIVATE / "RECEIPT.json", receipt)
    write_private(PRIVATE / "BASELINE_REP_V3.json", baseline_rep)
    write_private(PRIVATE / "CANDIDATE_REP_V3.json", candidate_rep)
    write_private(
        PRIVATE / "DEV_FORMULATIONS.json",
        summary["DEV_V3_by_formulation"],
    )
    write_private(
        PRIVATE / "POINTER.json",
        {
            "DOMAIN_HEAD_MUTATED": False,
            "MEDIATION_HEAD_MUTATED": False,
            "NONE_GATE_MUTATED": False,
            "selected_formulation": selected,
            "function_bundle": str(PRIVATE / "heads" / "function_redesign_selected.pt"),
            "HUB_PUBLISH_AUTHORIZED": False,
        },
    )

    write_repo(REPO_ART / "summary.json", summary)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(REPO_ART / "receipt.json", receipt)
    write_repo(REPO_ART / "RECEIPT.json", receipt)
    write_repo(
        SPEC / "classification-v6-function-prediction-redesign-receipt-20261002.json",
        receipt,
    )

    md = f"""# REDESIGN_V6_FUNCTION_PREDICTION

```text
OUTCOME = {outcome_vs_sealed['OUTCOME']}
NEXT_ACTION = {outcome_vs_sealed['NEXT_ACTION']}
selected = {selected}

DEV_V3 FUNCTION:
  independent = {ind_dev['FUNCTION_macro_f1']:.4f}
  semantic    = {sem_dev['FUNCTION_macro_f1']:.4f}
  hybrid      = {hyb_dev['FUNCTION_macro_f1']:.4f}

REP_V3 candidate ({selected}):
  system = {candidate_rep['system_macro_f1']:.4f}
  DOMAIN = {candidate_rep['DOMAIN_macro_f1']:.4f}
  FUNCTION = {candidate_rep['FUNCTION_macro_f1']:.4f}
  MEDIATION = {candidate_rep['MEDIATION_macro_f1']:.4f}
  positive-only = {candidate_rep['positive_only_system_macro_f1']:.4f}
  zero-FP = {candidate_rep['zero_label_false_positive_rate']:.4f}
  zero-exact = {candidate_rep['zero_label_exact_rejection']:.4f}

sealed baseline REP_V3 old heads:
  FUNCTION = {BASELINE_REP_V3['FUNCTION_macro_f1']:.4f}
  system = {BASELINE_REP_V3['system_macro_f1']:.4f}
  positive-only = {BASELINE_REP_V3['positive_only_system_macro_f1']:.4f}

Δ FUNCTION = {outcome_vs_sealed['function_delta']:+.4f}
Δ system = {outcome_vs_sealed['system_delta']:+.4f}
```

DOMAIN/MEDIATION heads unchanged. Encoder + ANY_LABEL gate frozen.
QUAL-003 blocked. MODEL_WIDE_BEST unchanged.
"""
    write_repo(
        SPEC / "classification-v6-function-prediction-redesign-20261002.md", md
    )
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


def main() -> int:
    if os.environ.get("HLX_V6_FUN_REDESIGN_INNER") == "1":
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
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e",
        "HLX_V2_FORWARD_ONTOLOGY=1",
        "-e",
        "HLX_V6_FUN_REDESIGN_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(
            REPO
            / "scripts/spark/run_classification_v6_function_prediction_redesign.py"
        ),
    ]
    log = PRIVATE / "redesign_console.log"
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
