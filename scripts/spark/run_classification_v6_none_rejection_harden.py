"""HARDEN_V6_NONE_REJECTION_UNDER_FROZEN_ENCODER.

Train/select NONE-rejection mechanisms on TRAIN_V2/DEV_V2 under the frozen
encoder; evaluate honestly on REP_V2. QUAL-002 is not accessed.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

PRIVATE = Path(
    "/home/morpheus/hlx-private/classification-v6-none-rejection-harden-20261001"
)
PRIVATE_SURFACES = Path(
    "/home/morpheus/hlx-private/classification-v6-representative-validation-redesign-20261001"
)
PRIVATE_PKG = Path(
    "/home/morpheus/hlx-private/classification-v6-semantic-pipeline-harden-20261001"
)
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-NONE-REJECTION-HARDEN-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
SEED = 20261002
MAX_LEN = 192
BATCH = 32
GATE_EPOCHS = 60
HEAD_EPOCHS = 40
LR = 1e-2

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


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


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as h:
        for r in rows:
            h.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
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


def sha256_file(path: Path) -> str:
    d = hashlib.sha256()
    with path.open("rb") as h:
        for chunk in iter(lambda: h.read(1 << 20), b""):
            d.update(chunk)
    return d.hexdigest()


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


def set_seeds(seed: int = SEED) -> None:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def n_lab(r: dict) -> int:
    return (
        len(r.get("domain_labels") or [])
        + len(r.get("function_labels") or [])
        + len(r.get("mediation_labels") or [])
    )


def multi_hot(labels, vocab):
    idx = {v: i for i, v in enumerate(vocab)}
    vec = [0] * len(vocab)
    for lab in labels or []:
        if lab in idx:
            vec[idx[lab]] = 1
    return vec


def mean_pool(last_hidden, attention_mask):
    mask = attention_mask.unsqueeze(-1).float()
    return (last_hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-6)


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
    hsh = hashlib.sha256()
    for k, tns in sorted(enc.state_dict().items()):
        hsh.update(k.encode())
        hsh.update(tns.detach().cpu().numpy().tobytes())
    n_train = sum(p.numel() for p in enc.parameters() if p.requires_grad)
    del enc
    torch.cuda.empty_cache()
    return __import__("torch").cat(vecs, dim=0).numpy(), hsh.hexdigest(), n_train


def build_mlp(hidden: int, n_out: int, device):
    import torch.nn as nn

    return nn.Sequential(
        nn.Linear(hidden, 128), nn.ReLU(), nn.Linear(128, n_out)
    ).to(device)


def load_heads(path: Path, vocabs, device):
    import io
    import torch

    raw = sudo_read_bytes(path)
    try:
        bundle = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=False)
    except TypeError:
        bundle = torch.load(io.BytesIO(raw), map_location="cpu")
    heads = {}
    for axis, vocab in vocabs.items():
        m = build_mlp(768, len(vocab), device)
        m.load_state_dict(bundle["state"][axis])
        m.eval()
        for p in m.parameters():
            p.requires_grad_(False)
        heads[axis] = m
    return heads, bundle


def scores_from_heads(heads, X, device):
    import torch

    out = {}
    with torch.no_grad():
        xt = torch.tensor(X, device=device)
        for axis, model in heads.items():
            out[axis] = torch.sigmoid(model(xt)).cpu().numpy()
    return out


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


def macro_f1(gold, pred) -> float:
    import numpy as np

    g = np.asarray(gold)
    p = np.asarray(pred)
    if g.size == 0:
        return 0.0
    return float(
        sum(f1_binary(g[:, j], p[:, j]) for j in range(g.shape[1])) / g.shape[1]
    )


def apply_thresholds(scores, thresholds):
    import numpy as np

    preds = {}
    for a, sc in scores.items():
        th = np.asarray(thresholds[a])
        preds[a] = (np.asarray(sc) >= th).astype(np.int32)
    return preds


def enforce_hier(preds, tech_idx, ai_idx):
    import numpy as np

    d = np.array(preds["domain"], dtype=np.int32, copy=True)
    for i in range(d.shape[0]):
        if d[i, ai_idx] == 1 and d[i, tech_idx] == 0:
            d[i, tech_idx] = 1
    out = dict(preds)
    out["domain"] = d
    return out


def zero_gate_mask(gate_scores, threshold):
    import numpy as np

    # gate_score = P(ANY_LABEL); reject (ZERO) when score < threshold
    return (np.asarray(gate_scores) < float(threshold))


def apply_zero_gate(preds, reject_mask):
    import numpy as np

    out = {}
    for a, p in preds.items():
        q = np.array(p, dtype=np.int32, copy=True)
        q[reject_mask] = 0
        out[a] = q
    return out


def evaluate_preds(rows, preds, vocabs) -> dict[str, Any]:
    import numpy as np

    golds = {
        a: np.asarray(
            [multi_hot(r.get(f"{a}_labels"), vocabs[a]) for r in rows], dtype=np.int32
        )
        for a in vocabs
    }
    axis_macros = {a: macro_f1(golds[a], preds[a]) for a in vocabs}
    system = float(sum(axis_macros.values()) / len(axis_macros))

    zero_idx = [i for i, r in enumerate(rows) if n_lab(r) == 0]
    pos_idx = [i for i, r in enumerate(rows) if n_lab(r) > 0]
    zero_fp = 0
    zero_exact = 0
    pred_counts = []
    for i in zero_idx:
        npred = int(
            preds["domain"][i].sum()
            + preds["function"][i].sum()
            + preds["mediation"][i].sum()
        )
        pred_counts.append(npred)
        if npred == 0:
            zero_exact += 1
        else:
            zero_fp += 1
    n_zero = max(1, len(zero_idx))

    false_reject = 0
    for i in pos_idx:
        npred = int(
            preds["domain"][i].sum()
            + preds["function"][i].sum()
            + preds["mediation"][i].sum()
        )
        if npred == 0:
            false_reject += 1
    n_pos = max(1, len(pos_idx))

    # label-level FP/FN on positive rows
    pos_fp = 0
    pos_fn = 0
    pos_tp_slots = 0
    for a in vocabs:
        g = golds[a][pos_idx]
        p = preds[a][pos_idx]
        pos_fp += int(((g == 0) & (p == 1)).sum())
        pos_fn += int(((g == 1) & (p == 0)).sum())
        pos_tp_slots += int((g == 1).sum())

    def slice_macro(idx):
        if not idx:
            return None
        return float(
            sum(macro_f1(golds[a][idx], preds[a][idx]) for a in vocabs) / len(vocabs)
        )

    single_idx = [i for i, r in enumerate(rows) if n_lab(r) == 1]
    multi_idx = [i for i, r in enumerate(rows) if n_lab(r) >= 2]
    df_idx = [
        i
        for i, r in enumerate(rows)
        if (r.get("domain_labels") or []) and (r.get("function_labels") or [])
    ]

    diagnostics = {
        "FALSE_ACCEPT_ZERO": zero_fp / n_zero,
        "FALSE_REJECT_POSITIVE": false_reject / n_pos,
        "POSITIVE_LABEL_FP": pos_fp / max(1, len(pos_idx) * sum(len(v) for v in vocabs.values())),
        "POSITIVE_LABEL_FN": pos_fn / max(1, pos_tp_slots),
        "FUNCTION_FAILURE": axis_macros["function"] < 0.15,
        "CO_LABEL_FAILURE": (
            len(df_idx) >= 5 and (slice_macro(df_idx) or 0.0) < 0.15
        ),
        "n_false_accept_zero": zero_fp,
        "n_false_reject_positive": false_reject,
        "n_positive_label_fp": pos_fp,
        "n_positive_label_fn": pos_fn,
    }

    return {
        "n": len(rows),
        "system_macro_f1": system,
        "DOMAIN_macro_f1": axis_macros["domain"],
        "FUNCTION_macro_f1": axis_macros["function"],
        "MEDIATION_macro_f1": axis_macros["mediation"],
        "axis_macros": axis_macros,
        "zero_label_n": len(zero_idx),
        "zero_label_false_positive_rate": zero_fp / n_zero,
        "zero_label_exact_rejection": zero_exact / n_zero,
        "mean_predicted_labels_on_zero_gold": float(sum(pred_counts) / n_zero),
        "false_reject_positive_rate": false_reject / n_pos,
        "single_label_system_macro_f1": slice_macro(single_idx),
        "multi_label_system_macro_f1": slice_macro(multi_idx),
        "positive_only_system_macro_f1": slice_macro(pos_idx),
        "n_domain_plus_function": len(df_idx),
        "co_label_performance": {
            "domain_plus_function_system_macro": slice_macro(df_idx),
            "n": len(df_idx),
        },
        "diagnostics": diagnostics,
    }


def train_gate(Xtr, ytr, device):
    import torch
    import torch.nn as nn

    set_seeds(SEED)
    model = build_mlp(Xtr.shape[1], 1, device)
    opt = torch.optim.AdamW(model.parameters(), lr=LR)
    bce = nn.BCEWithLogitsLoss()
    xt = torch.tensor(Xtr, dtype=torch.float32, device=device)
    yt = torch.tensor(ytr, dtype=torch.float32, device=device).view(-1, 1)
    model.train()
    for _ in range(GATE_EPOCHS):
        opt.zero_grad()
        loss = bce(model(xt), yt)
        loss.backward()
        opt.step()
    model.eval()
    return model


def gate_scores(model, X, device):
    import torch

    with torch.no_grad():
        xt = torch.tensor(X, dtype=torch.float32, device=device)
        return torch.sigmoid(model(xt)).cpu().numpy().reshape(-1)


def train_axis_heads(Xtr, Ytr_by_axis, vocabs, device):
    import torch
    import torch.nn as nn

    set_seeds(SEED + 1)
    heads = {}
    for axis, vocab in vocabs.items():
        model = build_mlp(Xtr.shape[1], len(vocab), device)
        opt = torch.optim.AdamW(model.parameters(), lr=LR)
        bce = nn.BCEWithLogitsLoss()
        xt = torch.tensor(Xtr, dtype=torch.float32, device=device)
        yt = torch.tensor(Ytr_by_axis[axis], dtype=torch.float32, device=device)
        model.train()
        for _ in range(HEAD_EPOCHS):
            opt.zero_grad()
            loss = bce(model(xt), yt)
            loss.backward()
            opt.step()
        model.eval()
        for p in model.parameters():
            p.requires_grad_(False)
        heads[axis] = model
    return heads


def state_dict_cpu(model):
    return {k: v.detach().cpu() for k, v in model.state_dict().items()}


def save_bundle(path: Path, payload: dict) -> str:
    import torch

    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    torch.save(payload, path)
    os.chmod(path, 0o600)
    return sha256_file(path)


def select_threshold(gate_sc, base_preds, rows, vocabs, tech_idx, ai_idx):
    """Pick gate threshold on DEV maximizing zero rejection under preservation."""
    import numpy as np

    from hyperlexical.classification_v6_none_rejection_harden import (
        classify_disposition,
    )

    best = None
    for th in np.linspace(0.05, 0.95, 37):
        reject = zero_gate_mask(gate_sc, th)
        preds = apply_zero_gate(base_preds, reject)
        preds = enforce_hier(preds, tech_idx, ai_idx)
        m = evaluate_preds(rows, preds, vocabs)
        d = classify_disposition(m)
        # DEV selection score: prefer zero improvement + positive + system
        score = (
            m["zero_label_exact_rejection"]
            + m["positive_only_system_macro_f1"]
            + 0.5 * m["system_macro_f1"]
            - m["false_reject_positive_rate"]
        )
        # Prefer candidates that would ADVANCE/PARTIAL on DEV
        rank = (
            2
            if d["DISPOSITION"] == "V6_NONE_REJECTION_ADVANCE"
            else 1
            if d["DISPOSITION"] == "V6_NONE_REJECTION_PARTIAL"
            else 0
        )
        cand = (rank, score, float(th), m, d)
        if best is None or cand[:2] > best[:2]:
            best = cand
    assert best is not None
    return {
        "threshold": best[2],
        "dev_metrics": best[3],
        "dev_disposition": best[4],
        "selection_score": best[1],
    }


def select_maxscore_threshold(scores, base_preds, rows, vocabs, tech_idx, ai_idx):
    import numpy as np

    from hyperlexical.classification_v6_none_rejection_harden import (
        classify_disposition,
    )

    max_sc = np.maximum.reduce(
        [
            np.asarray(scores["domain"]).max(axis=1),
            np.asarray(scores["function"]).max(axis=1),
            np.asarray(scores["mediation"]).max(axis=1),
        ]
    )
    best = None
    for th in np.linspace(0.05, 0.95, 37):
        reject = max_sc < th
        preds = apply_zero_gate(base_preds, reject)
        preds = enforce_hier(preds, tech_idx, ai_idx)
        m = evaluate_preds(rows, preds, vocabs)
        d = classify_disposition(m)
        score = (
            m["zero_label_exact_rejection"]
            + m["positive_only_system_macro_f1"]
            + 0.5 * m["system_macro_f1"]
            - m["false_reject_positive_rate"]
        )
        rank = (
            2
            if d["DISPOSITION"] == "V6_NONE_REJECTION_ADVANCE"
            else 1
            if d["DISPOSITION"] == "V6_NONE_REJECTION_PARTIAL"
            else 0
        )
        cand = (rank, score, float(th), m, d)
        if best is None or cand[:2] > best[:2]:
            best = cand
    assert best is not None
    return {
        "threshold": best[2],
        "dev_metrics": best[3],
        "dev_disposition": best[4],
        "max_scores": max_sc,
        "selection_score": best[1],
    }


def inner() -> int:
    import numpy as np
    import torch

    from hyperlexical.classification_v6_architecture_reset_bakeoff import AXIS_VOCABS
    from hyperlexical.classification_v6_none_rejection_harden import (
        CANDIDATE_PACKAGE_ID,
        PHASE_RULE,
        PIPELINE_POINTER_ID,
        build_none_rejection_receipt,
        classify_disposition,
        decide_next_action,
        none_rejection_contract,
    )
    from hyperlexical.classification_v6_qualification_execute_002 import (
        EXPECTED_ENCODER_STATE_HASH,
        EXPECTED_PACKAGE_SHA256,
    )
    from hyperlexical.classification_v6_semantic_pipeline_harden import (
        BAKEOFF_THRESHOLDS,
        SELECTED_ENCODER_MODEL_ID,
        SELECTED_ENCODER_REVISION,
    )

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    REPO_ART.mkdir(parents=True, exist_ok=True)
    contract = none_rejection_contract()
    write_private(PRIVATE / "CONTRACT.json", contract)
    write_repo(REPO_ART / "contract.json", contract)

    package = load_json(PRIVATE_PKG / "PACKAGE.json")
    if package.get("PACKAGE_SHA256") != EXPECTED_PACKAGE_SHA256:
        raise SystemExit("package_sha_mismatch")

    train = load_jsonl(PRIVATE_SURFACES / "TRAIN_V2.jsonl")
    dev = load_jsonl(PRIVATE_SURFACES / "DEV_SELECTION_V2.jsonl")
    rep = load_jsonl(PRIVATE_SURFACES / "REPRESENTATIVE_VALIDATION_V2.jsonl")
    if not (len(train) == 2819 and len(dev) == 505 and len(rep) == 1416):
        raise SystemExit(
            f"surface_n_mismatch train/dev/rep={len(train)}/{len(dev)}/{len(rep)}"
        )

    vocabs = {
        "domain": list(AXIS_VOCABS["domain"]),
        "function": list(AXIS_VOCABS["function"]),
        "mediation": list(AXIS_VOCABS["mediation"]),
    }
    thresholds = {a: list(BAKEOFF_THRESHOLDS[a]) for a in vocabs}
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device}", flush=True)

    # Encode once; verify immutability hash before training anything new.
    print("embed_all", flush=True)
    X_train, enc_pre, n_tr = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        [r.get("text") or "" for r in train],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    if n_tr != 0:
        raise SystemExit("encoder_trainable_nonzero_pre")
    if enc_pre != EXPECTED_ENCODER_STATE_HASH:
        raise SystemExit(f"encoder_hash_mismatch_pre={enc_pre}")
    X_dev, enc_mid, n_tr2 = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        [r.get("text") or "" for r in dev],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    X_rep, enc_post_embed, n_tr3 = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        [r.get("text") or "" for r in rep],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    if n_tr2 or n_tr3:
        raise SystemExit("encoder_trainable_nonzero_mid")
    if enc_mid != EXPECTED_ENCODER_STATE_HASH or enc_post_embed != EXPECTED_ENCODER_STATE_HASH:
        raise SystemExit("encoder_hash_drift_during_embed")

    np.savez_compressed(
        PRIVATE / "emb_cache.npz",
        train=X_train,
        dev=X_dev,
        rep=X_rep,
        encoder_state_hash=np.asarray([enc_pre]),
    )
    os.chmod(PRIVATE / "emb_cache.npz", 0o600)

    frozen_heads, head_bundle = load_heads(
        PRIVATE_PKG / "heads" / "axis_nonlinear_heads.pt", vocabs, device
    )
    scores_tr = scores_from_heads(frozen_heads, X_train, device)
    scores_dev = scores_from_heads(frozen_heads, X_dev, device)
    scores_rep = scores_from_heads(frozen_heads, X_rep, device)

    def base_preds_from(scores):
        return enforce_hier(apply_thresholds(scores, thresholds), tech_idx, ai_idx)

    base_dev = base_preds_from(scores_dev)
    base_rep = base_preds_from(scores_rep)
    baseline_dev = evaluate_preds(dev, base_dev, vocabs)
    baseline_rep = evaluate_preds(rep, base_rep, vocabs)
    write_private(PRIVATE / "BASELINE_DEV.json", baseline_dev)
    write_private(PRIVATE / "BASELINE_REP.json", baseline_rep)

    # --- Mechanism 1: LEARNED_ANY_EVIDENCE_GATE ---
    print("train_any_evidence_gate", flush=True)
    y_train = np.asarray([1.0 if n_lab(r) > 0 else 0.0 for r in train], dtype=np.float32)
    gate = train_gate(X_train, y_train, device)
    gate_dev = gate_scores(gate, X_dev, device)
    gate_rep = gate_scores(gate, X_rep, device)
    gate_sel = select_threshold(
        gate_dev, base_dev, dev, vocabs, tech_idx, ai_idx
    )
    gate_th = gate_sel["threshold"]
    gate_rep_preds = enforce_hier(
        apply_zero_gate(base_rep, zero_gate_mask(gate_rep, gate_th)),
        tech_idx,
        ai_idx,
    )
    gate_rep_m = evaluate_preds(rep, gate_rep_preds, vocabs)
    gate_bundle_sha = save_bundle(
        PRIVATE / "heads" / "any_evidence_gate.pt",
        {
            "meta": {
                "kind": "ANY_SEMANTIC_EVIDENCE_GATE",
                "threshold": gate_th,
                "seed": SEED,
                "epochs": GATE_EPOCHS,
            },
            "state": state_dict_cpu(gate),
        },
    )

    # --- Mechanism 2: SHARED_MAX_SCORE_REJECT ---
    print("calibrate_max_score_reject", flush=True)
    max_sel = select_maxscore_threshold(
        scores_dev, base_dev, dev, vocabs, tech_idx, ai_idx
    )
    max_th = max_sel["threshold"]
    max_rep = np.maximum.reduce(
        [
            np.asarray(scores_rep["domain"]).max(axis=1),
            np.asarray(scores_rep["function"]).max(axis=1),
            np.asarray(scores_rep["mediation"]).max(axis=1),
        ]
    )
    max_rep_preds = enforce_hier(
        apply_zero_gate(base_rep, max_rep < max_th), tech_idx, ai_idx
    )
    max_rep_m = evaluate_preds(rep, max_rep_preds, vocabs)

    # --- Mechanism 3: NEGATIVE_AWARE_HEAD_RETRAIN ---
    print("train_negative_aware_heads", flush=True)
    Ytr = {
        a: np.asarray(
            [multi_hot(r.get(f"{a}_labels"), vocabs[a]) for r in train],
            dtype=np.float32,
        )
        for a in vocabs
    }
    neg_heads = train_axis_heads(X_train, Ytr, vocabs, device)
    neg_scores_dev = scores_from_heads(neg_heads, X_dev, device)
    neg_scores_rep = scores_from_heads(neg_heads, X_rep, device)
    # calibrate per-axis thresholds lightly on DEV (keep same bakeoff as default;
    # optional shared max-score reject on top selected on DEV)
    neg_base_dev = base_preds_from(neg_scores_dev)
    neg_base_rep = base_preds_from(neg_scores_rep)
    neg_dev_m = evaluate_preds(dev, neg_base_dev, vocabs)
    neg_rep_m = evaluate_preds(rep, neg_base_rep, vocabs)
    neg_heads_sha = save_bundle(
        PRIVATE / "heads" / "negative_aware_axis_heads.pt",
        {
            "meta": {
                "kind": "NEGATIVE_AWARE_AXIS_HEADS",
                "seed": SEED + 1,
                "epochs": HEAD_EPOCHS,
                "includes_zero_label_rows": True,
            },
            "state": {a: state_dict_cpu(m) for a, m in neg_heads.items()},
        },
    )

    # --- Mechanism 4: GATE_PLUS_NEGATIVE_AWARE_HEADS ---
    print("select_gate_plus_neg_heads", flush=True)
    combo_sel = select_threshold(
        gate_dev, neg_base_dev, dev, vocabs, tech_idx, ai_idx
    )
    combo_th = combo_sel["threshold"]
    combo_rep_preds = enforce_hier(
        apply_zero_gate(neg_base_rep, zero_gate_mask(gate_rep, combo_th)),
        tech_idx,
        ai_idx,
    )
    combo_rep_m = evaluate_preds(rep, combo_rep_preds, vocabs)

    # Post-training encoder hash re-check (reload + hash)
    print("encoder_immutability_post", flush=True)
    _, enc_final, n_tr_final = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        ["immutability probe"],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    if n_tr_final != 0 or enc_final != EXPECTED_ENCODER_STATE_HASH:
        raise SystemExit("encoder_mutated_or_trainable")

    mechanisms = {
        "BASELINE_DIRECT_EMISSION": {
            "dev": baseline_dev,
            "rep": baseline_rep,
            "selected_on": "none",
            "params": {},
        },
        "LEARNED_ANY_EVIDENCE_GATE": {
            "dev": gate_sel["dev_metrics"],
            "rep": gate_rep_m,
            "selected_on": "DEV_V2",
            "params": {
                "gate_threshold": gate_th,
                "gate_bundle_sha256": gate_bundle_sha,
                "architecture": "frozen_embedding→ANY_LABEL_gate→frozen_axis_heads→hierarchy",
            },
        },
        "SHARED_MAX_SCORE_REJECT": {
            "dev": max_sel["dev_metrics"],
            "rep": max_rep_m,
            "selected_on": "DEV_V2",
            "params": {
                "max_score_threshold": max_th,
                "architecture": "frozen_embedding→frozen_axis_heads→max_score_reject→hierarchy",
            },
        },
        "NEGATIVE_AWARE_HEAD_RETRAIN": {
            "dev": neg_dev_m,
            "rep": neg_rep_m,
            "selected_on": "DEV_V2_train_only",
            "params": {
                "heads_sha256": neg_heads_sha,
                "architecture": "frozen_embedding→neg_aware_axis_heads→hierarchy",
            },
        },
        "GATE_PLUS_NEGATIVE_AWARE_HEADS": {
            "dev": combo_sel["dev_metrics"],
            "rep": combo_rep_m,
            "selected_on": "DEV_V2",
            "params": {
                "gate_threshold": combo_th,
                "gate_bundle_sha256": gate_bundle_sha,
                "heads_sha256": neg_heads_sha,
                "architecture": "frozen_embedding→ANY_LABEL_gate→neg_aware_heads→hierarchy",
            },
        },
    }

    # Select by DEV disposition rank then score; evaluate that choice on REP.
    def mech_rank(name, blob):
        d = classify_disposition(blob["dev"])
        score = (
            blob["dev"]["zero_label_exact_rejection"]
            + blob["dev"]["positive_only_system_macro_f1"]
            + 0.5 * blob["dev"]["system_macro_f1"]
            - blob["dev"]["false_reject_positive_rate"]
        )
        rank = (
            2
            if d["DISPOSITION"] == "V6_NONE_REJECTION_ADVANCE"
            else 1
            if d["DISPOSITION"] == "V6_NONE_REJECTION_PARTIAL"
            else 0
        )
        # Never select pure baseline as "new" candidate unless all fail.
        baseline_penalty = 0 if name != "BASELINE_DIRECT_EMISSION" else -0.01
        return (rank, score + baseline_penalty, name)

    ranked = sorted(
        (mech_rank(n, b) for n, b in mechanisms.items()), reverse=True
    )
    selected_name = ranked[0][2]
    selected = mechanisms[selected_name]
    rep_metrics = selected["rep"]
    disposition_detail = classify_disposition(rep_metrics)
    disposition = disposition_detail["DISPOSITION"]
    next_action = decide_next_action(disposition, rep_metrics)

    before_after = {
        "zero_label_false_positive_rate": {
            "before": baseline_rep["zero_label_false_positive_rate"],
            "after": rep_metrics["zero_label_false_positive_rate"],
            "delta": rep_metrics["zero_label_false_positive_rate"]
            - baseline_rep["zero_label_false_positive_rate"],
        },
        "zero_label_exact_rejection": {
            "before": baseline_rep["zero_label_exact_rejection"],
            "after": rep_metrics["zero_label_exact_rejection"],
            "delta": rep_metrics["zero_label_exact_rejection"]
            - baseline_rep["zero_label_exact_rejection"],
        },
        "mean_predicted_labels_on_zero_gold": {
            "before": baseline_rep["mean_predicted_labels_on_zero_gold"],
            "after": rep_metrics["mean_predicted_labels_on_zero_gold"],
            "delta": rep_metrics["mean_predicted_labels_on_zero_gold"]
            - baseline_rep["mean_predicted_labels_on_zero_gold"],
        },
        "positive_only_system_macro_f1": {
            "before": baseline_rep["positive_only_system_macro_f1"],
            "after": rep_metrics["positive_only_system_macro_f1"],
            "delta": (rep_metrics["positive_only_system_macro_f1"] or 0.0)
            - (baseline_rep["positive_only_system_macro_f1"] or 0.0),
        },
        "system_macro_f1": {
            "before": baseline_rep["system_macro_f1"],
            "after": rep_metrics["system_macro_f1"],
            "delta": rep_metrics["system_macro_f1"] - baseline_rep["system_macro_f1"],
        },
    }

    selected_candidate = None
    if disposition == "V6_NONE_REJECTION_ADVANCE":
        selected_candidate = {
            "CANDIDATE_PACKAGE_ID": CANDIDATE_PACKAGE_ID,
            "PIPELINE_POINTER_ID": PIPELINE_POINTER_ID,
            "mechanism": selected_name,
            "params": selected["params"],
            "parent_package_sha256": EXPECTED_PACKAGE_SHA256,
            "encoder_state_hash": EXPECTED_ENCODER_STATE_HASH,
            "global_promotion": False,
        }
        write_private(PRIVATE / "CANDIDATE_PACKAGE.json", selected_candidate)
        write_private(
            PRIVATE / "POINTER.json",
            {
                "V6_NONE_REJECTION_CANDIDATE": selected_candidate,
                "MODEL_WIDE_BEST_MUTATED": False,
                "V5_POINTERS_MUTATED": False,
                "HUB_PUBLISH_AUTHORIZED": False,
                "PARENT_PACKAGE_SHA256": EXPECTED_PACKAGE_SHA256,
            },
        )
    else:
        write_private(
            PRIVATE / "POINTER.json",
            {
                "V6_NONE_REJECTION_CANDIDATE": None,
                "MODEL_WIDE_BEST_MUTATED": False,
                "V5_POINTERS_MUTATED": False,
                "HUB_PUBLISH_AUTHORIZED": False,
                "PARENT_PACKAGE_SHA256": EXPECTED_PACKAGE_SHA256,
            },
        )

    mech_report = {
        name: {
            "dev": {
                "system_macro_f1": b["dev"]["system_macro_f1"],
                "positive_only_system_macro_f1": b["dev"][
                    "positive_only_system_macro_f1"
                ],
                "zero_label_false_positive_rate": b["dev"][
                    "zero_label_false_positive_rate"
                ],
                "zero_label_exact_rejection": b["dev"]["zero_label_exact_rejection"],
                "false_reject_positive_rate": b["dev"]["false_reject_positive_rate"],
                "disposition": classify_disposition(b["dev"])["DISPOSITION"],
            },
            "rep": {
                "system_macro_f1": b["rep"]["system_macro_f1"],
                "DOMAIN_macro_f1": b["rep"]["DOMAIN_macro_f1"],
                "FUNCTION_macro_f1": b["rep"]["FUNCTION_macro_f1"],
                "MEDIATION_macro_f1": b["rep"]["MEDIATION_macro_f1"],
                "positive_only_system_macro_f1": b["rep"][
                    "positive_only_system_macro_f1"
                ],
                "zero_label_false_positive_rate": b["rep"][
                    "zero_label_false_positive_rate"
                ],
                "zero_label_exact_rejection": b["rep"]["zero_label_exact_rejection"],
                "mean_predicted_labels_on_zero_gold": b["rep"][
                    "mean_predicted_labels_on_zero_gold"
                ],
                "false_reject_positive_rate": b["rep"]["false_reject_positive_rate"],
                "single_label_system_macro_f1": b["rep"][
                    "single_label_system_macro_f1"
                ],
                "multi_label_system_macro_f1": b["rep"][
                    "multi_label_system_macro_f1"
                ],
                "disposition": classify_disposition(b["rep"])["DISPOSITION"],
            },
            "params": b["params"],
        }
        for name, b in mechanisms.items()
    }
    write_private(PRIVATE / "MECHANISMS.json", mech_report)
    write_repo(REPO_ART / "mechanisms.json", mech_report)
    write_private(PRIVATE / "DEV_V2_SELECTED.json", selected["dev"])
    write_private(PRIVATE / "REP_V2_SELECTED.json", rep_metrics)
    write_repo(REPO_ART / "dev_v2_selected.json", selected["dev"])
    write_repo(REPO_ART / "rep_v2_selected.json", rep_metrics)
    write_private(PRIVATE / "BEFORE_AFTER.json", before_after)
    write_repo(REPO_ART / "before_after.json", before_after)

    receipt = build_none_rejection_receipt(
        {
            "PHASE_RULE": PHASE_RULE,
            "DISPOSITION": disposition,
            "disposition_detail": disposition_detail,
            "NEXT_ACTION": next_action,
            "selected_mechanism": selected_name,
            "selected_candidate": selected_candidate,
            "mechanisms": mech_report,
            "DEV_V2": selected["dev"],
            "REP_V2": rep_metrics,
            "baseline_REP_V2": baseline_rep,
            "before_after": before_after,
            "encoder_immutability": {
                "pre": enc_pre,
                "post": enc_final,
                "expected": EXPECTED_ENCODER_STATE_HASH,
                "equal": enc_pre == enc_final == EXPECTED_ENCODER_STATE_HASH,
                "trainable_parameters": 0,
            },
            "parent_package_sha256": EXPECTED_PACKAGE_SHA256,
            "surfaces": {
                "TRAIN_V2_n": len(train),
                "DEV_V2_n": len(dev),
                "REP_V2_n": len(rep),
                "definitions_frozen": True,
            },
            "code_revision": code_revision(),
        }
    )
    write_private(PRIVATE / "RECEIPT.json", receipt)
    write_repo(REPO_ART / "receipt.json", receipt)
    write_repo(REPO_ART / "RECEIPT.json", receipt)
    write_repo(
        SPEC / "classification-v6-none-rejection-harden-receipt-20261001.json",
        receipt,
    )

    summary = {
        "PHASE_RULE": PHASE_RULE,
        "DISPOSITION": disposition,
        "NEXT_ACTION": next_action,
        "selected_mechanism": selected_name,
        "REP_V2_system_macro_f1": rep_metrics["system_macro_f1"],
        "REP_V2_positive_only": rep_metrics["positive_only_system_macro_f1"],
        "REP_V2_zero_fp": rep_metrics["zero_label_false_positive_rate"],
        "REP_V2_zero_exact": rep_metrics["zero_label_exact_rejection"],
        "REP_V2_mean_pred_zero": rep_metrics["mean_predicted_labels_on_zero_gold"],
        "REP_V2_false_reject_positive": rep_metrics["false_reject_positive_rate"],
        "baseline_zero_fp": baseline_rep["zero_label_false_positive_rate"],
        "baseline_positive_only": baseline_rep["positive_only_system_macro_f1"],
        "zero_label_improved": disposition_detail["zero_label_improved"],
        "positive_preserved": disposition_detail["positive_preserved"],
        "encoder_immutable": True,
        "MODEL_WIDE_BEST_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "selected_candidate": selected_name
        if disposition == "V6_NONE_REJECTION_ADVANCE"
        else None,
        "RECEIPT": receipt["V6_NONE_REJECTION_HARDEN_RECEIPT_SHA256"],
    }
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_repo(REPO_ART / "summary.json", summary)
    write_repo(REPO_ART / "SUMMARY.json", summary)

    md = f"""# HARDEN_V6_NONE_REJECTION_UNDER_FROZEN_ENCODER

```text
DISPOSITION = {disposition}
NEXT_ACTION = {next_action}
selected_mechanism = {selected_name}
REP_V2 system macro-F1 = {rep_metrics['system_macro_f1']:.4f}
REP_V2 positive-only = {rep_metrics['positive_only_system_macro_f1']:.4f}
REP_V2 zero-label FP = {rep_metrics['zero_label_false_positive_rate']:.3f} (was {baseline_rep['zero_label_false_positive_rate']:.3f})
REP_V2 zero exact reject = {rep_metrics['zero_label_exact_rejection']:.3f}
REP_V2 mean pred on zero = {rep_metrics['mean_predicted_labels_on_zero_gold']:.3f}
false_reject_positive = {rep_metrics['false_reject_positive_rate']:.3f}
encoder_immutable = true
RECEIPT = {receipt['V6_NONE_REJECTION_HARDEN_RECEIPT_SHA256']}
```

Two-stage gate preferred: frozen embedding → ANY_LABEL/ZERO_LABEL gate →
axis heads → hierarchy. Surfaces TRAIN/DEV/REP V2 frozen. QUAL-002 unused.
"""
    write_repo(SPEC / "classification-v6-none-rejection-harden-20261001.md", md)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V6_NONE_REJECTION_INNER") == "1":
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
        "HLX_V6_NONE_REJECTION_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v6_none_rejection_harden.py"),
    ]
    log = PRIVATE / "none_rejection_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(
            cmd, check=False, stdout=handle, stderr=subprocess.STDOUT
        )
    try:
        print(log.read_text(encoding="utf-8")[-80000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
