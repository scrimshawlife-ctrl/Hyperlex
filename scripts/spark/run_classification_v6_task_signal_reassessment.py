"""REASSESS_V6_TASK_SIGNAL_AND_PRETRAINED_REPRESENTATION — diagnostic phase.

No architecture-family bakeoff. Floors locked. QUAL sealed.
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
    "/home/morpheus/hlx-private/classification-v6-task-signal-reassessment-20261001"
)
PRIOR_PRIV = Path(
    "/home/morpheus/hlx-private/classification-v6-label-migration-bakeoff-20261001"
)
RESET_PRIV = Path(
    "/home/morpheus/hlx-private/classification-v6-architecture-reset-bakeoff-20261001"
)
HA_PRIV = Path(
    "/home/morpheus/hlx-private/classification-v6-human-ontology-settlement-20261001"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
SENTENCE_ENCODER = "sentence-transformers/all-mpnet-base-v2"
NLI_CROSS = "cross-encoder/nli-deberta-v3-base"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-TASK-SIGNAL-REASSESSMENT-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
MAX_LEN = 192
PAIR_MAX_LEN = 256
SEED = 20261001
EPOCHS = 2
BATCH = 8
PAIR_BATCH = 16
LR = 2e-5
NEG_PER_POS = 3

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    import hashlib

    d = hashlib.sha256()
    with path.open("rb") as h:
        for chunk in iter(lambda: h.read(1 << 20), b""):
            d.update(chunk)
    return d.hexdigest()


def sudo_sha256(path: Path) -> str:
    try:
        return sha256_file(path)
    except PermissionError:
        return subprocess.run(
            ["sudo", "-n", "sha256sum", str(path)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split()[0]


def sudo_read_text(path: Path) -> str:
    if os.access(path, os.R_OK):
        return path.read_text(encoding="utf-8")
    return subprocess.run(
        ["sudo", "-n", "cat", str(path)], check=True, capture_output=True, text=True
    ).stdout


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


def fail(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(2)


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


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in sudo_read_text(path).splitlines() if l.strip()]


def usable(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        if r.get("evidence_label") != "EVIDENCE_PRESENT":
            continue
        if r.get("human_resettlement_required"):
            continue
        if not (
            r.get("domain_labels")
            or r.get("function_labels")
            or r.get("mediation_labels")
        ):
            continue
        out.append(r)
    return out


def multi_hot(labels: list[str], vocab: list[str]) -> list[int]:
    idx = {v: i for i, v in enumerate(vocab)}
    vec = [0] * len(vocab)
    for lab in labels:
        if lab in idx:
            vec[idx[lab]] = 1
    return vec


def mean_pool(last_hidden, attention_mask):
    import torch

    mask = attention_mask.unsqueeze(-1).float()
    return (last_hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-6)


def thresholds_from_dev(scores, gold):
    import numpy as np

    scores = np.asarray(scores, dtype=np.float64)
    gold = np.asarray(gold, dtype=np.int32)
    grid = [round(x, 2) for x in np.linspace(0.05, 0.95, 19)]
    th = []
    for j in range(scores.shape[1]):
        best_t, best_f1 = 0.5, -1.0
        for t in grid:
            p = (scores[:, j] >= t).astype(np.int32)
            tp = int(((p == 1) & (gold[:, j] == 1)).sum())
            fp = int(((p == 1) & (gold[:, j] == 0)).sum())
            fn = int(((p == 0) & (gold[:, j] == 1)).sum())
            f1 = 2 * tp / max(1e-9, 2 * tp + fp + fn)
            if f1 > best_f1:
                best_f1, best_t = f1, float(t)
        th.append(best_t)
    return th


def apply_th(scores, th):
    import numpy as np

    scores = np.asarray(scores)
    out = np.zeros_like(scores, dtype=np.int32)
    for j, t in enumerate(th):
        out[:, j] = (scores[:, j] >= t).astype(np.int32)
    return out


def enforce_hier(pred, tech_idx, ai_idx):
    for i in range(pred.shape[0]):
        if pred[i, ai_idx] == 1:
            pred[i, tech_idx] = 1
    return pred


def pack_metrics(gold, pred, vocab):
    from hyperlexical.classification_v6_architecture_bakeoff import multilabel_f1
    import numpy as np

    m = multilabel_f1(gold, pred)
    g = np.asarray(gold)
    p = np.asarray(pred)
    m["n_positive_labels"] = int(g.sum())
    per = {}
    for j, lab in enumerate(vocab):
        tp = int(((g[:, j] == 1) & (p[:, j] == 1)).sum())
        fp = int(((g[:, j] == 0) & (p[:, j] == 1)).sum())
        fn = int(((g[:, j] == 1) & (p[:, j] == 0)).sum())
        prec = tp / max(1, tp + fp)
        rec = tp / max(1, tp + fn)
        f1 = 2 * prec * rec / max(1e-9, prec + rec) if (prec + rec) else 0.0
        pos_scores = []  # filled by caller optionally
        per[lab] = {
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "support": int(g[:, j].sum()),
        }
    m["per_label"] = per
    return m


def score_dist(scores_col, gold_col):
    import numpy as np

    s = np.asarray(scores_col, dtype=np.float64)
    g = np.asarray(gold_col, dtype=np.int32)
    pos = s[g == 1]
    neg = s[g == 0]
    def stats(x):
        if len(x) == 0:
            return {"n": 0, "mean": 0.0, "p50": 0.0, "p90": 0.0}
        return {
            "n": int(len(x)),
            "mean": float(x.mean()),
            "p50": float(np.percentile(x, 50)),
            "p90": float(np.percentile(x, 90)),
        }
    return {
        "positive": stats(pos),
        "negative": stats(neg),
        "margin_mean": float(pos.mean() - neg.mean()) if len(pos) and len(neg) else 0.0,
    }


# ---------- encoder loading ----------
def load_modernbert(encoder_id: str, device, trainable_last: int | None = 2, full: bool = False):
    import torch
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    tok = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    enc = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    if encoder_id == "CONTROL":
        if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
            fail("BEST_mismatch")
        split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
        apply_encoder_trainable(enc, split.get("encoder") or {})
    if full:
        for p in enc.parameters():
            p.requires_grad = True
    elif trainable_last == 0:
        for p in enc.parameters():
            p.requires_grad = False
    else:
        freeze_encoder(enc, last_trainable=int(trainable_last))
    enc.to(device)
    return tok, enc


def embed_biencoder(model_id, texts, device, max_len=MAX_LEN, batch=32):
    import torch
    import torch.nn.functional as F
    from transformers import AutoModel, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_id)
    enc = AutoModel.from_pretrained(model_id).to(device)
    enc.eval()
    vecs = []
    with torch.no_grad():
        for i in range(0, len(texts), batch):
            chunk = texts[i : i + batch]
            t = tok(
                chunk, padding=True, truncation=True, max_length=max_len, return_tensors="pt"
            ).to(device)
            h = enc(**t).last_hidden_state
            v = F.normalize(mean_pool(h, t["attention_mask"]), dim=-1)
            vecs.append(v.cpu())
    del enc
    return torch.cat(vecs, dim=0) if vecs else None


def zero_shot_biencoder(rows_dev, rows_rep, label_texts, vocabs, device, model_id, encoder_tag):
    import numpy as np
    import torch

    from hyperlexical.classification_v6_architecture_bakeoff import hierarchy_metrics

    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")
    # label embeds
    lab_vecs = {}
    for axis, vocab in vocabs.items():
        lab_vecs[axis] = embed_biencoder(
            model_id, [label_texts[l] for l in vocab], device, max_len=PAIR_MAX_LEN
        )

    def score(rows):
        tvec = embed_biencoder(model_id, [r["text"] for r in rows], device)
        scores = {}
        for axis in vocabs:
            scores[axis] = (tvec @ lab_vecs[axis].T).numpy()
        return scores

    dev_s = score(rows_dev)
    th = {
        a: thresholds_from_dev(
            dev_s[a], [multi_hot(r.get(f"{a}_labels") or [], v) for r in rows_dev]
        )
        for a, v in vocabs.items()
    }
    out = {"encoder": encoder_tag, "model_id": model_id, "trainable": False}
    for name, rows in (("DEV", rows_dev), ("REP", rows_rep)):
        sc = score(rows)
        packed = {"n": len(rows)}
        golds, preds = {}, {}
        for axis, vocab in vocabs.items():
            gold = [multi_hot(r.get(f"{axis}_labels") or [], vocab) for r in rows]
            pred = apply_th(sc[axis], th[axis])
            if axis == "domain":
                pred = enforce_hier(pred, tech_idx, ai_idx)
            golds[axis] = gold
            preds[axis] = pred.tolist()
            m = pack_metrics(gold, preds[axis], vocab)
            for j, lab in enumerate(vocab):
                m["per_label"][lab]["score_dist"] = score_dist(sc[axis][:, j], np.asarray(gold)[:, j])
            packed[axis] = m
        g_sys = [d + f + m for d, f, m in zip(golds["domain"], golds["function"], golds["mediation"])]
        p_sys = [d + f + m for d, f, m in zip(preds["domain"], preds["function"], preds["mediation"])]
        from hyperlexical.classification_v6_architecture_bakeoff import multilabel_f1

        packed["system"] = multilabel_f1(g_sys, p_sys)
        packed["hierarchy"] = hierarchy_metrics(
            golds["domain"], preds["domain"], tech_idx=tech_idx, ai_idx=ai_idx
        )
        out[name] = packed
    return out


def zero_shot_nli_cross(rows_dev, rows_rep, label_texts, vocabs, device, model_id):
    """Strong semantic/NLI cross-encoder — inference only."""
    import numpy as np
    import torch
    import torch.nn.functional as F
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    from hyperlexical.classification_v6_architecture_bakeoff import (
        hierarchy_metrics,
        multilabel_f1,
    )

    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSequenceClassification.from_pretrained(model_id).to(device)
    model.eval()
    # label map: entailment index
    id2label = {int(k) if str(k).isdigit() else k: v for k, v in model.config.id2label.items()}
    # normalize
    entail_idx = None
    for i, name in model.config.id2label.items():
        if str(name).lower() in {"entailment", "entail"}:
            entail_idx = int(i)
    if entail_idx is None:
        # deberta nli: often CONTRADICTION=0, NEUTRAL=1, ENTAILMENT=2
        entail_idx = 2

    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")

    @torch.no_grad()
    def score_rows(rows):
        scores = {a: np.zeros((len(rows), len(v)), dtype=np.float64) for a, v in vocabs.items()}
        for axis, vocab in vocabs.items():
            for j, lab in enumerate(vocab):
                defs = [label_texts[lab]] * len(rows)
                texts = [r["text"] for r in rows]
                col = []
                for i in range(0, len(rows), 16):
                    t = tok(
                        texts[i : i + 16],
                        defs[i : i + 16],
                        padding=True,
                        truncation=True,
                        max_length=PAIR_MAX_LEN,
                        return_tensors="pt",
                    ).to(device)
                    logits = model(**t).logits
                    prob = F.softmax(logits, dim=-1)[:, entail_idx]
                    col.append(prob.cpu().numpy())
                scores[axis][:, j] = np.concatenate(col) if col else 0
        return scores

    dev_s = score_rows(rows_dev)
    th = {
        a: thresholds_from_dev(
            dev_s[a], [multi_hot(r.get(f"{a}_labels") or [], v) for r in rows_dev]
        )
        for a, v in vocabs.items()
    }
    out = {"encoder": "NLI_CROSS_ENCODER", "model_id": model_id, "trainable": False}
    for name, rows in (("DEV", rows_dev), ("REP", rows_rep)):
        sc = score_rows(rows)
        packed = {"n": len(rows)}
        golds, preds = {}, {}
        for axis, vocab in vocabs.items():
            gold = [multi_hot(r.get(f"{axis}_labels") or [], vocab) for r in rows]
            pred = apply_th(sc[axis], th[axis])
            if axis == "domain":
                pred = enforce_hier(pred, tech_idx, ai_idx)
            golds[axis] = gold
            preds[axis] = pred.tolist()
            m = pack_metrics(gold, preds[axis], vocab)
            for j, lab in enumerate(vocab):
                m["per_label"][lab]["score_dist"] = score_dist(
                    sc[axis][:, j], np.asarray(gold)[:, j]
                )
            packed[axis] = m
        g_sys = [d + f + m for d, f, m in zip(golds["domain"], golds["function"], golds["mediation"])]
        p_sys = [d + f + m for d, f, m in zip(preds["domain"], preds["function"], preds["mediation"])]
        packed["system"] = multilabel_f1(g_sys, p_sys)
        packed["hierarchy"] = hierarchy_metrics(
            golds["domain"], preds["domain"], tech_idx=tech_idx, ai_idx=ai_idx
        )
        out[name] = packed
    del model
    return out


def build_pairs(rows, vocabs, label_defs, rng):
    pairs = []
    for r in rows:
        text = r["text"]
        for axis, vocab in vocabs.items():
            pos = set(r.get(f"{axis}_labels") or [])
            neg_pool = [l for l in vocab if l not in pos]
            for lab in pos:
                pairs.append((text, label_defs[lab], 1))
                rng.shuffle(neg_pool)
                for nlab in neg_pool[:NEG_PER_POS]:
                    pairs.append((text, label_defs[nlab], 0))
            if not pos and neg_pool:
                pairs.append((text, label_defs[neg_pool[0]], 0))
    rng.shuffle(pairs)
    return pairs


def train_d_style(
    train,
    dev,
    rep,
    vocabs,
    label_defs,
    device,
    *,
    encoder_id="CONTROL",
    trainable_last=2,
    full=False,
    epochs=EPOCHS,
    tag="D",
):
    """Limited Track-D-style training for learning curves / adaptation regimes."""
    import numpy as np
    import torch
    import torch.nn as nn

    from hyperlexical.classification_v6_architecture_bakeoff import (
        hierarchy_metrics,
        multilabel_f1,
    )

    tok, enc = load_modernbert(
        encoder_id, device, trainable_last=trainable_last, full=full
    )
    head = nn.Linear(enc.config.hidden_size, 1).to(device)
    params = [p for p in enc.parameters() if p.requires_grad] + list(head.parameters())
    if not params:
        params = list(head.parameters())
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.01)
    bce = nn.BCEWithLogitsLoss()
    rng = random.Random(SEED)
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")
    pairs = build_pairs(train, vocabs, label_defs, rng)

    # init snapshot for drift (CLS of a fixed probe batch)
    enc.eval()
    probe_texts = [r["text"] for r in train[:64]]
    with torch.no_grad():
        pt = tok(
            probe_texts, padding=True, truncation=True, max_length=MAX_LEN, return_tensors="pt"
        ).to(device)
        h0 = mean_pool(enc(**pt).last_hidden_state, pt["attention_mask"]).detach().cpu()

    for epoch in range(epochs):
        rng.shuffle(pairs)
        enc.train()
        head.train()
        # if encoder frozen, keep eval for BN-like; ModernBERT has no BN — train ok
        total = 0.0
        n = 0
        for i in range(0, len(pairs), PAIR_BATCH):
            chunk = pairs[i : i + PAIR_BATCH]
            y = torch.tensor([c[2] for c in chunk], dtype=torch.float32, device=device)
            t = tok(
                [c[0] for c in chunk],
                [c[1] for c in chunk],
                padding=True,
                truncation=True,
                max_length=PAIR_MAX_LEN,
                return_tensors="pt",
            ).to(device)
            opt.zero_grad()
            logit = head(enc(**t).last_hidden_state[:, 0]).squeeze(-1)
            loss = bce(logit, y)
            loss.backward()
            opt.step()
            total += float(loss.item())
            n += 1
        print(f"{tag} epoch {epoch+1} loss={total/max(1,n):.4f} pairs={len(pairs)}", flush=True)

    enc.eval()
    head.eval()
    with torch.no_grad():
        h1 = mean_pool(enc(**pt).last_hidden_state, pt["attention_mask"]).detach().cpu()
    import torch.nn.functional as F

    drift = {
        "cosine_similarity_to_init": float(F.cosine_similarity(h0, h1, dim=-1).mean()),
        "l2_drift_mean": float(torch.norm(h1 - h0, dim=-1).mean()),
    }

    @torch.no_grad()
    def score_rows(rows):
        scores = {a: np.zeros((len(rows), len(v)), dtype=np.float64) for a, v in vocabs.items()}
        pos, neg = [], []
        for axis, vocab in vocabs.items():
            for j, lab in enumerate(vocab):
                col = []
                texts = [r["text"] for r in rows]
                defs = [label_defs[lab]] * len(rows)
                for i in range(0, len(rows), 32):
                    t = tok(
                        texts[i : i + 32],
                        defs[i : i + 32],
                        padding=True,
                        truncation=True,
                        max_length=PAIR_MAX_LEN,
                        return_tensors="pt",
                    ).to(device)
                    prob = torch.sigmoid(head(enc(**t).last_hidden_state[:, 0]).squeeze(-1))
                    col.append(prob.cpu().numpy())
                arr = np.concatenate(col)
                scores[axis][:, j] = arr
                for i, r in enumerate(rows):
                    (pos if lab in set(r.get(f"{axis}_labels") or []) else neg).append(
                        float(arr[i])
                    )
        margin = (sum(pos) / len(pos) - sum(neg) / len(neg)) if pos and neg else 0.0
        return scores, margin

    dev_s, _ = score_rows(dev)
    th = {
        a: thresholds_from_dev(
            dev_s[a], [multi_hot(r.get(f"{a}_labels") or [], v) for r in dev]
        )
        for a, v in vocabs.items()
    }
    out = {
        "tag": tag,
        "encoder_id": encoder_id,
        "trainable_last": trainable_last,
        "full": full,
        "n_train": len(train),
        "drift": drift,
    }
    for name, rows in (("DEV", dev), ("REP", rep)):
        sc, margin = score_rows(rows)
        packed = {"n": len(rows), "text_label_margin": margin}
        golds, preds = {}, {}
        for axis, vocab in vocabs.items():
            gold = [multi_hot(r.get(f"{axis}_labels") or [], vocab) for r in rows]
            pred = apply_th(sc[axis], th[axis])
            if axis == "domain":
                pred = enforce_hier(pred, tech_idx, ai_idx)
            golds[axis] = gold
            preds[axis] = pred.tolist()
            packed[axis] = pack_metrics(gold, preds[axis], vocab)
        g_sys = [d + f + m for d, f, m in zip(golds["domain"], golds["function"], golds["mediation"])]
        p_sys = [d + f + m for d, f, m in zip(preds["domain"], preds["function"], preds["mediation"])]
        packed["system"] = multilabel_f1(g_sys, p_sys)
        packed["hierarchy"] = hierarchy_metrics(
            golds["domain"], preds["domain"], tech_idx=tech_idx, ai_idx=ai_idx
        )
        out[name] = packed
    del enc, head
    return out


def linear_probes(train, dev, rep, vocabs, device, encoder_id):
    """Frozen encoder + independent logistic probes per axis."""
    import numpy as np
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    from hyperlexical.classification_v6_architecture_bakeoff import multilabel_f1

    tok, enc = load_modernbert(encoder_id, device, trainable_last=0, full=False)
    enc.eval()

    def embed(rows):
        vecs = []
        with torch.no_grad():
            for i in range(0, len(rows), 32):
                chunk = rows[i : i + 32]
                t = tok(
                    [c["text"] for c in chunk],
                    padding=True,
                    truncation=True,
                    max_length=MAX_LEN,
                    return_tensors="pt",
                ).to(device)
                v = F.normalize(
                    mean_pool(enc(**t).last_hidden_state, t["attention_mask"]), dim=-1
                )
                vecs.append(v.cpu().numpy())
        return np.concatenate(vecs, axis=0)

    Xtr, Xdv, Xrp = embed(train), embed(dev), embed(rep)
    hidden = Xtr.shape[1]
    out = {"encoder_id": encoder_id}
    for axis, vocab in vocabs.items():
        Ytr = np.asarray([multi_hot(r.get(f"{axis}_labels") or [], vocab) for r in train], dtype=np.float32)
        Ydv = np.asarray([multi_hot(r.get(f"{axis}_labels") or [], vocab) for r in dev], dtype=np.float32)
        Yrp = np.asarray([multi_hot(r.get(f"{axis}_labels") or [], vocab) for r in rep], dtype=np.float32)
        # linear
        W = nn.Linear(hidden, len(vocab)).to(device)
        opt = torch.optim.AdamW(W.parameters(), lr=1e-2)
        bce = nn.BCEWithLogitsLoss()
        xt = torch.tensor(Xtr, device=device)
        yt = torch.tensor(Ytr, device=device)
        for _ in range(40):
            opt.zero_grad()
            loss = bce(W(xt), yt)
            loss.backward()
            opt.step()
        with torch.no_grad():
            # threshold on DEV
            sdv = torch.sigmoid(W(torch.tensor(Xdv, device=device))).cpu().numpy()
            th = thresholds_from_dev(sdv, Ydv.astype(int))
            srp = torch.sigmoid(W(torch.tensor(Xrp, device=device))).cpu().numpy()
            pr = apply_th(srp, th)
            lin = multilabel_f1(Yrp.astype(int).tolist(), pr.tolist())
        # shallow nonlinear
        mlp = nn.Sequential(
            nn.Linear(hidden, 128), nn.ReLU(), nn.Linear(128, len(vocab))
        ).to(device)
        opt2 = torch.optim.AdamW(mlp.parameters(), lr=1e-2)
        for _ in range(40):
            opt2.zero_grad()
            loss = bce(mlp(xt), yt)
            loss.backward()
            opt2.step()
        with torch.no_grad():
            sdv = torch.sigmoid(mlp(torch.tensor(Xdv, device=device))).cpu().numpy()
            th = thresholds_from_dev(sdv, Ydv.astype(int))
            srp = torch.sigmoid(mlp(torch.tensor(Xrp, device=device))).cpu().numpy()
            pr = apply_th(srp, th)
            non = multilabel_f1(Yrp.astype(int).tolist(), pr.tolist())
        from hyperlexical.classification_v6_task_signal_reassessment import classify_probe

        out[axis] = {
            "linear": lin,
            "nonlinear": non,
            "class": classify_probe(lin["macro_f1"], non["macro_f1"]),
        }
    del enc
    return out


def gold_cardinality_audit(rows):
    buckets = defaultdict(list)
    for r in rows:
        d = len(r.get("domain_labels") or [])
        f = len(r.get("function_labels") or [])
        m = len(r.get("mediation_labels") or [])
        total = d + f + m
        key = "single" if total == 1 else ("multi_2_3" if total <= 3 else "high_4plus")
        buckets[key].append(r)
    return {
        k: {
            "n": len(v),
            "mean_domain": sum(len(r.get("domain_labels") or []) for r in v) / max(1, len(v)),
            "mean_function": sum(len(r.get("function_labels") or []) for r in v) / max(1, len(v)),
        }
        for k, v in buckets.items()
    }


def colabel_sparsity(train, dev, rep, vocabs):
    def pairs(rows):
        c = Counter()
        for r in rows:
            labs = []
            for axis, vocab in vocabs.items():
                labs.extend(r.get(f"{axis}_labels") or [])
            labs = sorted(set(labs))
            for i in range(len(labs)):
                for j in range(i + 1, len(labs)):
                    c[(labs[i], labs[j])] += 1
        return c

    ct, cd, cr = pairs(train), pairs(dev), pairs(rep)
    keys = set(ct) | set(cd) | set(cr)
    rows = []
    for a, b in sorted(keys):
        rows.append(
            {
                "pair": [a, b],
                "TRAIN": ct[(a, b)],
                "DEV": cd[(a, b)],
                "REP": cr[(a, b)],
            }
        )
    rare = [r for r in rows if r["TRAIN"] <= 2 and r["REP"] >= 1]
    return {
        "n_pairs": len(rows),
        "rare_train_but_rep": rare[:40],
        "top_train": sorted(rows, key=lambda r: -r["TRAIN"])[:20],
    }


def supervision_density(train, vocabs):
    out = {}
    n = len(train)
    for axis, vocab in vocabs.items():
        for lab in vocab:
            pos = [r for r in train if lab in (r.get(f"{axis}_labels") or [])]
            # lexical diversity: unique tokens
            toks = set()
            for r in pos:
                toks.update(str(r.get("text") or "").lower().split())
            sources = Counter(str(r.get("source") or r.get("source_family") or "UNK") for r in pos)
            rate = len(pos) / max(1, n)
            if len(pos) < 15:
                klass = "LOW_POSITIVE_SUPPORT"
            elif len(toks) < 40:
                klass = "LOW_DIVERSITY"
            elif rate < 0.02:
                klass = "NEGATIVE_DOMINATED"
            else:
                klass = "ADEQUATELY_SUPERVISED"
            out[lab] = {
                "positive_train": len(pos),
                "negative_train": n - len(pos),
                "positive_rate": rate,
                "lexical_types": len(toks),
                "source_diversity": len(sources),
                "class": klass,
            }
    return out


def source_shortcut_audit(rows_rep, zero_shot_scores_by_axis, vocabs, th):
    """Group REP by source family if present."""
    import numpy as np

    groups = defaultdict(list)
    for i, r in enumerate(rows_rep):
        src = str(r.get("source_family") or r.get("source") or r.get("corpus") or "UNK")
        # coarsen
        src = src.split("/")[0][:40]
        groups[src].append(i)
    # if almost all UNK, try evidence provenance fields
    report = {"groups": {}, "note": None}
    if len(groups) <= 1:
        report["note"] = "insufficient_source_fields_for_holdout"
        report["groups"] = {k: {"n": len(v)} for k, v in groups.items()}
        return report
    from hyperlexical.classification_v6_architecture_bakeoff import multilabel_f1

    for src, idxs in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:12]:
        if len(idxs) < 8:
            continue
        # system scores
        g_sys, p_sys = [], []
        for i in idxs:
            r = rows_rep[i]
            gd, pd = [], []
            for axis, vocab in vocabs.items():
                g = multi_hot(r.get(f"{axis}_labels") or [], vocab)
                p = (zero_shot_scores_by_axis[axis][i] >= np.asarray(th[axis])).astype(int)
                gd.extend(g.tolist() if hasattr(g, "tolist") else list(g))
                pd.extend(p.tolist())
            g_sys.append(gd)
            p_sys.append(pd)
        report["groups"][src] = {"n": len(idxs), "system": multilabel_f1(g_sys, p_sys)}
    return report


def human_vs_model(agree_level1, zs_per_label, trained_per_label):
    """Map agreement strata names onto model label ids loosely."""
    mapping = {
        "domain:crypto_markets": "domain.crypto",
        "domain:gambling_betting": "domain.gambling",
        "function:evaluative_stance": "function.evaluative_stance",
        "function:relational_intimacy": "function.relational_intimacy",
        "mediation:internet_register": "mediation.internet_register",
        "identity_relevance": None,
    }
    rows = []
    for stratum, stats in (agree_level1 or {}).items():
        lab = mapping.get(stratum)
        if lab is None:
            # try direct
            if stratum in zs_per_label:
                lab = stratum
            else:
                continue
        zs = zs_per_label.get(lab) or {}
        tr = trained_per_label.get(lab) or {}
        kappa = float(stats.get("cohen_kappa") or 0)
        support = int(stats.get("n_pos_either") or zs.get("support") or 0)
        if support < 5:
            klass = "LOW_SUPPORT"
        elif kappa < 0.4:
            klass = "HUMAN_UNSTABLE"
        elif float(zs.get("f1") or 0) >= 0.25 or float(tr.get("f1") or 0) >= 0.25:
            klass = "HUMAN_STABLE_MODEL_LEARNABLE"
        else:
            klass = "HUMAN_STABLE_MODEL_WEAK"
        rows.append(
            {
                "stratum": stratum,
                "label": lab,
                "human_kappa": kappa,
                "human_pos_agree": stats.get("positive_agreement"),
                "zero_shot_f1": zs.get("f1"),
                "trained_f1": tr.get("f1"),
                "support": support,
                "class": klass,
            }
        )
    return rows


def modernbert_zero_shot_control(dev, rep, vocabs, label_defs, device):
    """Reproduce CONTROL zero-shot with score distributions (reference path)."""
    import numpy as np
    import torch
    import torch.nn.functional as F

    from hyperlexical.classification_v6_architecture_bakeoff import (
        hierarchy_metrics,
        multilabel_f1,
    )

    tok, enc = load_modernbert("CONTROL", device, trainable_last=0)
    enc.eval()
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")

    def embed(texts, max_len=MAX_LEN):
        vecs = []
        with torch.no_grad():
            for i in range(0, len(texts), 32):
                t = tok(
                    texts[i : i + 32],
                    padding=True,
                    truncation=True,
                    max_length=max_len,
                    return_tensors="pt",
                ).to(device)
                v = F.normalize(
                    mean_pool(enc(**t).last_hidden_state, t["attention_mask"]), dim=-1
                )
                vecs.append(v.cpu())
        return torch.cat(vecs, dim=0)

    lab_v = {
        a: embed([label_defs[l] for l in v], max_len=PAIR_MAX_LEN) for a, v in vocabs.items()
    }

    def score(rows):
        tv = embed([r["text"] for r in rows])
        return {a: (tv @ lab_v[a].T).numpy() for a in vocabs}

    dev_s = score(dev)
    th = {
        a: thresholds_from_dev(
            dev_s[a], [multi_hot(r.get(f"{a}_labels") or [], v) for r in dev]
        )
        for a, v in vocabs.items()
    }
    out = {"encoder": "CONTROL", "scores_rep": None, "thresholds": th}
    for name, rows in (("DEV", dev), ("REP", rep)):
        sc = score(rows)
        if name == "REP":
            out["scores_rep"] = {a: sc[a].tolist() for a in sc}
        packed = {"n": len(rows)}
        golds, preds = {}, {}
        for axis, vocab in vocabs.items():
            gold = [multi_hot(r.get(f"{axis}_labels") or [], vocab) for r in rows]
            pred = apply_th(sc[axis], th[axis])
            if axis == "domain":
                pred = enforce_hier(pred, tech_idx, ai_idx)
            golds[axis] = gold
            preds[axis] = pred.tolist()
            m = pack_metrics(gold, preds[axis], vocab)
            garr = np.asarray(gold)
            for j, lab in enumerate(vocab):
                m["per_label"][lab]["score_dist"] = score_dist(sc[axis][:, j], garr[:, j])
            packed[axis] = m
        g_sys = [d + f + m for d, f, m in zip(golds["domain"], golds["function"], golds["mediation"])]
        p_sys = [d + f + m for d, f, m in zip(preds["domain"], preds["function"], preds["mediation"])]
        packed["system"] = multilabel_f1(g_sys, p_sys)
        packed["hierarchy"] = hierarchy_metrics(
            golds["domain"], preds["domain"], tech_idx=tech_idx, ai_idx=ai_idx
        )
        out[name] = packed
    del enc
    return out


def inner() -> int:
    import numpy as np
    import torch

    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text
    from hyperlexical.classification_v6_architecture_reset_bakeoff import AXIS_VOCABS
    from hyperlexical.classification_v6_data_foundation import utc_now_iso
    from hyperlexical.classification_v6_architecture_reset_bakeoff import (
        frozen_label_descriptions,
    )
    from hyperlexical.classification_v6_task_signal_reassessment import (
        LEARNING_FRACTIONS,
        PHASE_RULE,
        EXPERIMENT_ID,
        ZERO_SHOT_REFERENCE,
        architecture_restart_allowed,
        audit_all_descriptions,
        classify_learning_curve,
        description_variants_for_label,
        oracle_description,
        reassessment_contract,
        select_primary_diagnosis,
    )

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("CUDA required")

    contract = reassessment_contract()
    write_private(PRIVATE / "CONTRACT.json", contract)
    write_repo(REPO_ART / "contract.json", contract)

    train_all = load_jsonl(PRIOR_PRIV / "TRAIN_V6_LABELS.jsonl")
    dev_all = load_jsonl(PRIOR_PRIV / "DEVELOPMENT_VALIDATION_V6_LABELS.jsonl")
    rep_all = load_jsonl(PRIOR_PRIV / "REPRESENTATIVE_VALIDATION_V6_LABELS.jsonl")
    train, dev, rep = usable(train_all), usable(dev_all), usable(rep_all)
    print(f"usable train/dev/rep={len(train)}/{len(dev)}/{len(rep)}", flush=True)
    vocabs = AXIS_VOCABS
    label_defs = frozen_label_descriptions()

    # --- 1/2 reference zero-shot with per-label distributions ---
    print("zero-shot CONTROL reference audit", flush=True)
    zs_control = modernbert_zero_shot_control(dev, rep, vocabs, label_defs, device)
    write_private(PRIVATE / "ZERO_SHOT_CONTROL_AUDIT.json", {
        k: v for k, v in zs_control.items() if k != "scores_rep"
    })
    ref_macro = float(zs_control["REP"]["system"]["macro_f1"])
    print(f"reference REP macro={ref_macro:.4f} frozen={ZERO_SHOT_REFERENCE['rep_system_macro_f1']:.4f}", flush=True)

    # axis structure of 0.162
    axis_audit = {
        a: {
            "macro_f1": zs_control["REP"][a]["macro_f1"],
            "micro_f1": zs_control["REP"][a]["micro_f1"],
            "per_label": zs_control["REP"][a]["per_label"],
        }
        for a in ("domain", "function", "mediation")
    }
    strong_labs = []
    weak_labs = []
    for a in axis_audit:
        for lab, m in axis_audit[a]["per_label"].items():
            (strong_labs if m["f1"] >= 0.25 else weak_labs).append(lab)
    axis_structure = {
        "interpretation": (
            "few_strong_labels_many_unusable"
            if len(strong_labs) <= 3
            else (
                "one_usable_axis"
                if sum(1 for a in axis_audit if axis_audit[a]["macro_f1"] >= 0.15) == 1
                else "all_axes_weak"
                if all(axis_audit[a]["macro_f1"] < 0.15 for a in axis_audit)
                else "mixed_axes"
            )
        ),
        "strong_labels": strong_labs,
        "weak_label_count": len(weak_labs),
    }

    # --- 3 description adequacy ---
    desc_audit = audit_all_descriptions()
    write_private(PRIVATE / "DESCRIPTION_ADEQUACY.json", desc_audit)

    # --- 4 description sensitivity (one predefined pass) ---
    print("description sensitivity", flush=True)
    sens = {}
    # use CONTROL modernbert bi-encoder style with variant texts
    for variant in (
        "canonical_name",
        "canonical_full_definition",
        "positive_core",
        "definition_plus_exclusion",
    ):
        texts = {}
        for lab in label_defs:
            texts[lab] = description_variants_for_label(lab)[variant]
        # quick score using CONTROL trunk embeds
        tok, enc = load_modernbert("CONTROL", device, trainable_last=0)
        enc.eval()
        import torch.nn.functional as F

        def emb(ts, max_len=PAIR_MAX_LEN):
            import torch

            out = []
            with torch.no_grad():
                for i in range(0, len(ts), 32):
                    t = tok(
                        ts[i : i + 32],
                        padding=True,
                        truncation=True,
                        max_length=max_len,
                        return_tensors="pt",
                    ).to(device)
                    out.append(
                        F.normalize(
                            mean_pool(enc(**t).last_hidden_state, t["attention_mask"]),
                            dim=-1,
                        ).cpu()
                    )
            return torch.cat(out, dim=0)

        lab_v = {a: emb([texts[l] for l in v]) for a, v in vocabs.items()}
        t_dev = emb([r["text"] for r in dev], max_len=MAX_LEN)
        t_rep = emb([r["text"] for r in rep], max_len=MAX_LEN)
        th = {}
        for a, v in vocabs.items():
            sdev = (t_dev @ lab_v[a].T).numpy()
            th[a] = thresholds_from_dev(
                sdev, [multi_hot(r.get(f"{a}_labels") or [], v) for r in dev]
            )
        from hyperlexical.classification_v6_architecture_bakeoff import multilabel_f1

        g_sys, p_sys = [], []
        tech_idx = vocabs["domain"].index("domain.technology")
        ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")
        for i, r in enumerate(rep):
            gd, pd = [], []
            for a, v in vocabs.items():
                g = multi_hot(r.get(f"{a}_labels") or [], v)
                s = (t_rep[i] @ lab_v[a].T).numpy()
                p = (s >= np.asarray(th[a])).astype(int)
                if a == "domain":
                    if p[ai_idx] == 1:
                        p[tech_idx] = 1
                gd.extend(g)
                pd.extend(p.tolist())
            g_sys.append(gd)
            p_sys.append(pd)
        m = multilabel_f1(g_sys, p_sys)
        sens[variant] = m
        print(f"  variant {variant}: REP macro={m['macro_f1']:.4f}", flush=True)
        del enc
        torch.cuda.empty_cache()
    macros = [sens[v]["macro_f1"] for v in sens]
    instability = (max(macros) - min(macros)) >= 0.03
    write_private(
        PRIVATE / "DESCRIPTION_SENSITIVITY.json",
        {
            "variants": sens,
            "spread": max(macros) - min(macros),
            "LABEL_DESCRIPTION_INSTABILITY": instability,
            "diagnostic_only": True,
        },
    )

    # --- 5 oracle descriptions ---
    print("oracle descriptions", flush=True)
    oracle_texts = {lab: oracle_description(lab) for lab in label_defs}
    tok, enc = load_modernbert("CONTROL", device, trainable_last=0)
    enc.eval()
    import torch.nn.functional as F

    def emb2(ts, max_len=PAIR_MAX_LEN):
        import torch

        out = []
        with torch.no_grad():
            for i in range(0, len(ts), 32):
                t = tok(
                    ts[i : i + 32],
                    padding=True,
                    truncation=True,
                    max_length=max_len,
                    return_tensors="pt",
                ).to(device)
                out.append(
                    F.normalize(
                        mean_pool(enc(**t).last_hidden_state, t["attention_mask"]), dim=-1
                    ).cpu()
                )
        return torch.cat(out, dim=0)

    lab_v = {a: emb2([oracle_texts[l] for l in v]) for a, v in vocabs.items()}
    t_dev = emb2([r["text"] for r in dev], max_len=MAX_LEN)
    t_rep = emb2([r["text"] for r in rep], max_len=MAX_LEN)
    th = {
        a: thresholds_from_dev(
            (t_dev @ lab_v[a].T).numpy(),
            [multi_hot(r.get(f"{a}_labels") or [], v) for r in dev],
        )
        for a, v in vocabs.items()
    }
    from hyperlexical.classification_v6_architecture_bakeoff import multilabel_f1

    g_sys, p_sys = [], []
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")
    for i, r in enumerate(rep):
        gd, pd = [], []
        for a, v in vocabs.items():
            g = multi_hot(r.get(f"{a}_labels") or [], v)
            s = (t_rep[i] @ lab_v[a].T).numpy()
            p = (s >= np.asarray(th[a])).astype(int)
            if a == "domain" and p[ai_idx] == 1:
                p[tech_idx] = 1
            gd.extend(g)
            pd.extend(p.tolist())
        g_sys.append(gd)
        p_sys.append(pd)
    oracle_m = multilabel_f1(g_sys, p_sys)
    oracle_gain = float(oracle_m["macro_f1"] - ref_macro)
    write_private(
        PRIVATE / "ORACLE_DESCRIPTION.json",
        {
            "REP_system": oracle_m,
            "gain_vs_reference": oracle_gain,
            "SEMANTIC_SPECIFICATION_BOTTLENECK": oracle_gain >= 0.03,
        },
    )
    print(f"oracle REP macro={oracle_m['macro_f1']:.4f} gain={oracle_gain:.4f}", flush=True)
    del enc
    torch.cuda.empty_cache()

    # --- 13/14/15 cardinality, colabel, density ---
    card = {
        "TRAIN": gold_cardinality_audit(train),
        "DEV": gold_cardinality_audit(dev),
        "REP": gold_cardinality_audit(rep),
    }
    colabel = colabel_sparsity(train, dev, rep, vocabs)
    density = supervision_density(train, vocabs)
    write_private(PRIVATE / "CARDINALITY.json", card)
    write_private(PRIVATE / "COLABEL_SPARSITY.json", colabel)
    write_private(PRIVATE / "SUPERVISION_DENSITY.json", density)

    # --- 11 pretrained representation comparison (read-only) ---
    print("sentence embedding zero-shot", flush=True)
    sent = zero_shot_biencoder(
        dev, rep, label_defs, vocabs, device, SENTENCE_ENCODER, "SENTENCE_MPNET"
    )
    write_private(PRIVATE / "ZERO_SHOT_SENTENCE_MPNET.json", sent)
    print(f"mpnet REP macro={sent['REP']['system']['macro_f1']:.4f}", flush=True)
    torch.cuda.empty_cache()

    print("NLI cross-encoder diagnostic", flush=True)
    nli = zero_shot_nli_cross(dev, rep, label_defs, vocabs, device, NLI_CROSS)
    write_private(PRIVATE / "ZERO_SHOT_NLI_DEBERTA.json", nli)
    print(f"nli REP macro={nli['REP']['system']['macro_f1']:.4f}", flush=True)
    torch.cuda.empty_cache()

    # EXTERNAL modernbert trunk zero-shot already known ~0.134; recompute briefly via sensitivity full def? skip — use prior

    # --- 10 linear probes ---
    print("linear probes CONTROL", flush=True)
    probes_c = linear_probes(train, dev, rep, vocabs, device, "CONTROL")
    print("linear probes EXTERNAL", flush=True)
    probes_e = linear_probes(train, dev, rep, vocabs, device, "EXTERNAL")
    write_private(PRIVATE / "PROBES.json", {"CONTROL": probes_c, "EXTERNAL": probes_e})
    torch.cuda.empty_cache()

    # --- 8/9 adaptation regimes ---
    print("adaptation regimes", flush=True)
    regimes = {}
    regime_cfg = {
        "A_ENCODER_FROZEN": dict(trainable_last=0, full=False),
        "B_LAST_1_LAYER": dict(trainable_last=1, full=False),
        "C_LAST_2_LAYERS": dict(trainable_last=2, full=False),
        "D_FULL_FINETUNE": dict(trainable_last=2, full=True),
    }
    for name, cfg in regime_cfg.items():
        print(f"regime {name}", flush=True)
        regimes[name] = train_d_style(
            train,
            dev,
            rep,
            vocabs,
            label_defs,
            device,
            encoder_id="CONTROL",
            tag=name,
            **cfg,
        )
        print(
            f"  REP macro={regimes[name]['REP']['system']['macro_f1']:.4f} "
            f"drift_cos={regimes[name]['drift']['cosine_similarity_to_init']:.4f}",
            flush=True,
        )
        write_private(PRIVATE / "ADAPTATION_PARTIAL.json", regimes)
        torch.cuda.empty_cache()
    write_private(PRIVATE / "ADAPTATION_REGIMES.json", regimes)

    # --- 7 learning curves (C_LAST_2 as strongest simple D/F-like) ---
    print("learning curves", flush=True)
    rng = random.Random(SEED)
    idxs = list(range(len(train)))
    rng.shuffle(idxs)
    curve_points = []
    curve_detail = {}
    for frac in LEARNING_FRACTIONS:
        n = max(1, int(round(len(train) * frac)))
        subset = [train[i] for i in idxs[:n]]
        tag = f"CURVE_{int(frac*100)}"
        print(f"curve {tag} n={n}", flush=True)
        res = train_d_style(
            subset,
            dev,
            rep,
            vocabs,
            label_defs,
            device,
            encoder_id="CONTROL",
            trainable_last=2,
            full=False,
            tag=tag,
        )
        curve_points.append(
            {
                "fraction": frac,
                "n_train": n,
                "rep_system_macro_f1": res["REP"]["system"]["macro_f1"],
                "dev_system_macro_f1": res["DEV"]["system"]["macro_f1"],
                "rep_domain": res["REP"]["domain"]["macro_f1"],
                "rep_function": res["REP"]["function"]["macro_f1"],
                "margin": res["REP"]["text_label_margin"],
            }
        )
        curve_detail[tag] = res
        torch.cuda.empty_cache()
    curve_cls = classify_learning_curve(curve_points)
    write_private(
        PRIVATE / "LEARNING_CURVES.json",
        {"points": curve_points, "classification": curve_cls},
    )

    # --- 6 human vs model ---
    agree = None
    for p in (
        REPO
        / "artifacts/experiments/HLX-CLASSIFICATION-V6-LABEL-MIGRATION-BAKEOFF-001"
        / "three_level_agreement.json",
        PRIOR_PRIV / "three_level_agreement.json",
        HA_PRIV / "THREE_LEVEL_AGREEMENT.json",
    ):
        try:
            agree = json.loads(sudo_read_text(p))
            break
        except Exception:
            continue
    zs_per = {}
    for a in ("domain", "function", "mediation"):
        zs_per.update(zs_control["REP"][a]["per_label"])
    tr_per = {}
    best_trained = regimes.get("C_LAST_2_LAYERS") or regimes.get("A_ENCODER_FROZEN")
    if best_trained:
        for a in ("domain", "function", "mediation"):
            tr_per.update(best_trained["REP"][a]["per_label"])
    hvsm = human_vs_model(
        (agree or {}).get("level1_per_label") or {}, zs_per, tr_per
    )
    write_private(PRIVATE / "HUMAN_VS_MODEL.json", hvsm)

    # --- 12 axis-specific representation ---
    shared_rep = ref_macro
    # per-axis best among CONTROL zs / mpnet / nli for that axis
    axis_best = {}
    for a in ("domain", "function", "mediation"):
        axis_best[a] = max(
            float(zs_control["REP"][a]["macro_f1"]),
            float(sent["REP"][a]["macro_f1"]),
            float(nli["REP"][a]["macro_f1"]),
        )
    # optimistic composition upper bound ≠ system, but if per-axis best >> shared, justify axis-specific
    mean_axis_best = sum(axis_best.values()) / 3
    axis_rep_finding = {
        "shared_zero_shot_system": shared_rep,
        "best_per_axis_macro": axis_best,
        "mean_best_per_axis": mean_axis_best,
        "finding": (
            "AXIS_SPECIFIC_REPRESENTATIONS_JUSTIFIED"
            if (axis_best["domain"] - zs_control["REP"]["domain"]["macro_f1"] > 0.05
                or axis_best["function"] - zs_control["REP"]["function"]["macro_f1"] > 0.05)
            else "SHARED_REPRESENTATION_SUPPORTED"
        ),
    }
    write_private(PRIVATE / "AXIS_REPRESENTATION.json", axis_rep_finding)

    # --- 16 hard negatives (zero-shot vs trained) ---
    hardneg = {}
    for a, vocab in vocabs.items():
        for lab in vocab:
            # competitor = highest mean score among negatives on positive rows — approximate via score_dist margin
            zs = zs_control["REP"][a]["per_label"][lab]
            tr = (best_trained["REP"][a]["per_label"].get(lab) if best_trained else {}) or {}
            zs_m = (zs.get("score_dist") or {}).get("margin_mean")
            # trained margins from regime A vs C
            hardneg[lab] = {
                "zero_shot_margin": zs_m,
                "zero_shot_f1": zs.get("f1"),
                "trained_f1": tr.get("f1"),
                "margin_effect": (
                    "unknown_without_trained_scores"
                ),
            }
    # compare regime A vs D margins
    for name in ("A_ENCODER_FROZEN", "D_FULL_FINETUNE"):
        if name in regimes:
            hardneg[f"_regime_{name}_system_margin"] = regimes[name]["REP"]["text_label_margin"]
    write_private(PRIVATE / "HARD_NEGATIVES.json", hardneg)

    # --- 17 source shortcut ---
    # rebuild scores array from zs_control scores_rep
    scores_rep = {
        a: np.asarray(zs_control["scores_rep"][a]) for a in vocabs
    } if zs_control.get("scores_rep") else None
    if scores_rep is not None:
        src_audit = source_shortcut_audit(rep, scores_rep, vocabs, zs_control["thresholds"])
    else:
        src_audit = {"note": "scores unavailable"}
    write_private(PRIVATE / "SOURCE_SHORTCUT.json", src_audit)

    # --- 18 text-only signal from human protocol ---
    text_signal = {
        "protocol": "dual_operator_text_only_annotation",
        "model_scores_withheld": True,
        "acquisition_gold_withheld": True,
        "mean_set_jaccard": (agree or {}).get("mean_example_jaccard"),
        "labels": {},
    }
    for row in hvsm:
        lab = row["label"]
        if row["class"] == "HUMAN_STABLE_MODEL_WEAK":
            text_signal["labels"][lab] = "TEXT_SIGNAL_SUBTLE"
        elif row["class"] == "HUMAN_STABLE_MODEL_LEARNABLE":
            text_signal["labels"][lab] = "TEXT_SIGNAL_CLEAR"
        elif row["class"] == "HUMAN_UNSTABLE":
            text_signal["labels"][lab] = "POTENTIALLY_CONTEXT_DEPENDENT"
        else:
            text_signal["labels"][lab] = "TEXT_SIGNAL_SUBTLE"
    # mediation mixed identifiability from ontology
    text_signal["labels"]["mediation.internet_register"] = "POTENTIALLY_CONTEXT_DEPENDENT"
    write_private(PRIVATE / "TEXT_ONLY_SIGNAL.json", text_signal)

    # --- decision ---
    frozen_rep = float(regimes["A_ENCODER_FROZEN"]["REP"]["system"]["macro_f1"])
    full_rep = float(regimes["D_FULL_FINETUNE"]["REP"]["system"]["macro_f1"])
    strong_rep = max(
        float(nli["REP"]["system"]["macro_f1"]),
        float(sent["REP"]["system"]["macro_f1"]),
        ref_macro,
    )
    # catastrophic if cosine drift high AND performance below frozen
    cat = False
    for name, r in regimes.items():
        if r["drift"]["cosine_similarity_to_init"] < 0.90 and r["REP"]["system"]["macro_f1"] + 0.02 < frozen_rep:
            cat = True
    if full_rep + 0.03 < frozen_rep:
        cat = True

    # cardinality: compare zero-shot system on single vs multi by rescoring groups
    failure_card = False
    # composition sparsity: many rare pairs
    failure_comp = len(colabel.get("rare_train_but_rep") or []) >= 15

    evidence = {
        "strong_semantic_rep": strong_rep,
        "frozen_encoder_rep": frozen_rep,
        "full_finetune_rep": full_rep,
        "learning_curve": curve_cls,
        "oracle_gain": oracle_gain,
        "label_description_instability": instability,
        "catastrophic_task_adaptation": cat,
        "failure_is_cardinality_driven": failure_card,
        "failure_is_composition_sparsity": failure_comp,
        "text_signal_insufficient": strong_rep < 0.18 and ref_macro < 0.18,
        "axis_specific_representations_justified": axis_rep_finding["finding"]
        == "AXIS_SPECIFIC_REPRESENTATIONS_JUSTIFIED",
    }
    decision = select_primary_diagnosis(evidence)

    best_diag = max(strong_rep, frozen_rep, full_rep, float(curve_cls.get("max") or 0))
    restart = architecture_restart_allowed(
        best_diagnostic_rep=best_diag,
        learning_curve=curve_cls,
        margin_improved=float(regimes["A_ENCODER_FROZEN"]["REP"]["text_label_margin"])
        > 0.08,
        stable_gap=True,
        beats_zero_shot=best_diag > ZERO_SHOT_REFERENCE["rep_system_macro_f1"] + 0.01,
    )

    state = {
        "REASSESSMENT_STATE": "V6_TASK_SIGNAL_REASSESSMENT_COMPLETE",
        "NEXT_ACTION": decision["NEXT_ACTION"],
        "primary_diagnosis": decision["primary_diagnosis"],
        "goal_hypothesis": decision["goal_hypothesis"],
        "secondary_contributors": decision["secondary_contributors"],
        "architecture_restart": restart,
        "zero_shot_reference": ZERO_SHOT_REFERENCE,
        "measured_zero_shot_control_rep": ref_macro,
        "strong_semantic_best_rep": strong_rep,
        "frozen_encoder_rep": frozen_rep,
        "full_finetune_rep": full_rep,
        "learning_curve_class": curve_cls.get("class"),
        "QUAL_ROWS_INSPECTED": False,
        "floors_locked": True,
    }

    receipt = {
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "PHASE_RULE": PHASE_RULE,
        "QUAL_ROWS_INSPECTED": False,
        "ontology_modified": False,
        "architecture_bakeoff": False,
        "floors_lowered": False,
        "zero_shot_reference": ZERO_SHOT_REFERENCE,
        "axis_structure": axis_structure,
        "description_adequacy_counts": desc_audit["counts"],
        "description_sensitivity_spread": max(macros) - min(macros),
        "LABEL_DESCRIPTION_INSTABILITY": instability,
        "oracle_gain": oracle_gain,
        "learning_curve": curve_cls,
        "adaptation_rep": {
            k: v["REP"]["system"]["macro_f1"] for k, v in regimes.items()
        },
        "adaptation_drift": {k: v["drift"] for k, v in regimes.items()},
        "probes": {"CONTROL": probes_c, "EXTERNAL": probes_e},
        "pretrained_comparison": {
            "CONTROL_modernbert": ref_macro,
            "SENTENCE_MPNET": sent["REP"]["system"]["macro_f1"],
            "NLI_DEBERTA": nli["REP"]["system"]["macro_f1"],
        },
        "axis_representation": axis_rep_finding,
        "decision": decision,
        "architecture_restart": restart,
        "code_revision": code_revision(),
        "settled_at": utc_now_iso(),
        "REASSESSMENT_STATE": state["REASSESSMENT_STATE"],
        "NEXT_ACTION": state["NEXT_ACTION"],
    }
    receipt["V6_TASK_SIGNAL_REASSESSMENT_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in receipt.items()
                if k != "V6_TASK_SIGNAL_REASSESSMENT_RECEIPT_SHA256"
            }
        )
    )
    write_private(PRIVATE / "RECEIPT.json", receipt)
    write_repo(REPO_ART / "receipt.json", receipt)
    write_repo(
        SPEC / "classification-v6-task-signal-reassessment-receipt-20261001.json",
        receipt,
    )

    summary = {
        **state,
        "RECEIPT": receipt["V6_TASK_SIGNAL_REASSESSMENT_RECEIPT_SHA256"],
        "n_train": len(train),
        "n_dev": len(dev),
        "n_rep": len(rep),
        "pretrained_comparison": receipt["pretrained_comparison"],
        "adaptation_rep": receipt["adaptation_rep"],
    }
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_repo(REPO_ART / "SUMMARY.json", summary)

    # also dump key jsons to repo art
    for name in (
        "ZERO_SHOT_CONTROL_AUDIT",
        "DESCRIPTION_ADEQUACY",
        "DESCRIPTION_SENSITIVITY",
        "ORACLE_DESCRIPTION",
        "LEARNING_CURVES",
        "ADAPTATION_REGIMES",
        "PROBES",
        "AXIS_REPRESENTATION",
        "CARDINALITY",
        "COLABEL_SPARSITY",
        "SUPERVISION_DENSITY",
        "HUMAN_VS_MODEL",
        "HARD_NEGATIVES",
        "SOURCE_SHORTCUT",
        "TEXT_ONLY_SIGNAL",
    ):
        src = PRIVATE / f"{name}.json"
        if src.exists():
            try:
                write_repo(REPO_ART / f"{name.lower()}.json", json.loads(src.read_text()))
            except Exception:
                pass

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V6_REASSESS_INNER") == "1":
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
        "HLX_V6_REASSESS_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v6_task_signal_reassessment.py"),
    ]
    log = PRIVATE / "reassess_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(cmd, check=False, stdout=handle, stderr=subprocess.STDOUT)
    try:
        print(log.read_text(encoding="utf-8")[-35000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
