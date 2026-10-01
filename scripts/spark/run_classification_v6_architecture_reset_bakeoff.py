"""CONTINUE_V6_ARCHITECTURE_BAKEOFF — architecture-reset tracks D/E/F.

No A/B/C retuning. No QUAL inspection. No ontology/migration edits.
Label descriptions from settled ontology only.
"""

from __future__ import annotations

import json
import math
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
    "/home/morpheus/hlx-private/classification-v6-architecture-reset-bakeoff-20261001"
)
PRIOR_PRIV = Path(
    "/home/morpheus/hlx-private/classification-v6-label-migration-bakeoff-20261001"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-ARCHITECTURE-RESET-BAKEOFF-001"
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

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    return [
        json.loads(l)
        for l in sudo_read_text(path).splitlines()
        if l.strip()
    ]


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


def load_encoder(encoder_id: str, device):
    import torch
    import torch.nn as nn
    from safetensors.torch import load_file
    from transformers import AutoModel, AutoTokenizer

    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    if encoder_id == "CONTROL":
        if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
            fail("MODEL_WIDE_BEST_mismatch")
        split = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
        apply_encoder_trainable(encoder, split.get("encoder") or {})
    elif encoder_id != "EXTERNAL":
        fail(f"unknown encoder_id {encoder_id}")
    freeze_encoder(encoder, last_trainable=2)
    encoder.to(device)
    return tokenizer, encoder


def mean_pool(last_hidden, attention_mask):
    import torch

    mask = attention_mask.unsqueeze(-1).float()
    summed = (last_hidden * mask).sum(dim=1)
    return summed / mask.sum(dim=1).clamp(min=1e-6)


def enforce_hierarchy(domain_pred, tech_idx: int, ai_idx: int):
    for i in range(domain_pred.shape[0]):
        if domain_pred[i, ai_idx] == 1:
            domain_pred[i, tech_idx] = 1
    return domain_pred


def thresholds_from_dev(scores, gold, grid=None):
    """Per-label thresholds maximizing macro-F1 on DEV (not REP)."""
    import numpy as np

    grid = grid or [round(x, 2) for x in np.linspace(0.05, 0.95, 19)]
    scores = np.asarray(scores, dtype=np.float64)
    gold = np.asarray(gold, dtype=np.int32)
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


def apply_thresholds(scores, thresholds):
    import numpy as np

    scores = np.asarray(scores)
    out = np.zeros_like(scores, dtype=np.int32)
    for j, t in enumerate(thresholds):
        out[:, j] = (scores[:, j] >= t).astype(np.int32)
    return out


def pack_axis_metrics(gold, pred, vocab):
    from hyperlexical.classification_v6_architecture_reset_bakeoff import multilabel_f1
    import numpy as np

    m = multilabel_f1(gold, pred)
    g = np.asarray(gold)
    m["n_positive_labels"] = int(g.sum())
    m["support_positives"] = int((g.sum(axis=0) > 0).sum()) if g.size else 0
    # per-label P/R
    per = {}
    for j, lab in enumerate(vocab):
        tp = int(((g[:, j] == 1) & (np.asarray(pred)[:, j] == 1)).sum())
        fp = int(((g[:, j] == 0) & (np.asarray(pred)[:, j] == 1)).sum())
        fn = int(((g[:, j] == 1) & (np.asarray(pred)[:, j] == 0)).sum())
        prec = tp / max(1, tp + fp)
        rec = tp / max(1, tp + fn)
        per[lab] = {"precision": prec, "recall": rec, "support": int(g[:, j].sum())}
    m["per_label"] = per
    return m


def eval_from_scores(rows, scores_by_axis, vocabs, thresholds_by_axis, tech_idx, ai_idx):
    from hyperlexical.classification_v6_architecture_reset_bakeoff import (
        classify_errors,
        hierarchy_metrics,
        multilabel_f1,
        representation_diagnostics,
    )
    import numpy as np

    out = {"n": len(rows)}
    preds = {}
    golds = {}
    for axis, vocab in vocabs.items():
        gold = [multi_hot(r.get(f"{axis}_labels") or [], vocab) for r in rows]
        pred = apply_thresholds(scores_by_axis[axis], thresholds_by_axis[axis])
        if axis == "domain":
            pred = enforce_hierarchy(pred, tech_idx, ai_idx)
        golds[axis] = gold
        preds[axis] = pred.tolist()
        out[axis] = pack_axis_metrics(gold, preds[axis], vocab)
    g_sys = [
        d + f + m
        for d, f, m in zip(golds["domain"], golds["function"], golds["mediation"])
    ]
    p_sys = [
        d + f + m
        for d, f, m in zip(preds["domain"], preds["function"], preds["mediation"])
    ]
    out["system"] = multilabel_f1(g_sys, p_sys)
    out["hierarchy"] = hierarchy_metrics(
        golds["domain"], preds["domain"], tech_idx=tech_idx, ai_idx=ai_idx
    )
    # error decomposition
    errors = {}
    for axis, vocab in vocabs.items():
        g_labs = [
            [vocab[j] for j, v in enumerate(row) if v == 1] for row in golds[axis]
        ]
        p_labs = [
            [vocab[j] for j, v in enumerate(row) if v == 1] for row in preds[axis]
        ]
        errors[axis] = classify_errors(
            gold_labels=g_labs,
            pred_labels=p_labs,
            axis=axis,
            ontology_uncertainty=[r.get("ontology_uncertainty") for r in rows],
        )
    out["errors"] = errors
    return out, preds, golds


def run_zero_shot(train, dev, rep, encoder_id, device, label_defs, vocabs):
    import numpy as np
    import torch
    import torch.nn.functional as F

    from hyperlexical.classification_v6_architecture_reset_bakeoff import (
        representation_diagnostics,
    )

    tokenizer, encoder = load_encoder(encoder_id, device)
    encoder.eval()
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")

    @torch.no_grad()
    def embed_texts(texts, max_len=MAX_LEN):
        vecs = []
        for i in range(0, len(texts), 32):
            chunk = texts[i : i + 32]
            tok = tokenizer(
                chunk,
                padding=True,
                truncation=True,
                max_length=max_len,
                return_tensors="pt",
            ).to(device)
            h = encoder(**tok).last_hidden_state
            v = F.normalize(mean_pool(h, tok["attention_mask"]), dim=-1)
            vecs.append(v.cpu())
        return torch.cat(vecs, dim=0) if vecs else torch.zeros(0, encoder.config.hidden_size)

    label_vecs = {}
    for axis, vocab in vocabs.items():
        defs = [label_defs[l] for l in vocab]
        label_vecs[axis] = embed_texts(defs, max_len=PAIR_MAX_LEN)

    def score_rows(rows):
        tvec = embed_texts([r["text"] for r in rows])
        scores = {}
        pos_sims, neg_sims = [], []
        for axis, vocab in vocabs.items():
            sim = (tvec @ label_vecs[axis].T).numpy()
            scores[axis] = sim
            for i, r in enumerate(rows):
                gold = set(r.get(f"{axis}_labels") or [])
                for j, lab in enumerate(vocab):
                    if lab in gold:
                        pos_sims.append(float(sim[i, j]))
                    else:
                        neg_sims.append(float(sim[i, j]))
        return scores, representation_diagnostics(pos_sims, neg_sims)

    # thresholds on DEV only
    dev_scores, _ = score_rows(dev)
    thresholds = {}
    for axis, vocab in vocabs.items():
        gold = [multi_hot(r.get(f"{axis}_labels") or [], vocab) for r in dev]
        thresholds[axis] = thresholds_from_dev(dev_scores[axis], gold)

    results = {}
    for name, rows in (("DEV", dev), ("REP", rep)):
        scores, diag = score_rows(rows)
        packed, _, _ = eval_from_scores(
            rows, scores, vocabs, thresholds, tech_idx, ai_idx
        )
        packed["representation"] = diag
        results[name] = packed
    results["encoder"] = encoder_id
    results["n_train"] = 0
    results["trainable"] = False
    del encoder
    return results


def build_pairs(rows, vocabs, label_defs, rng, neg_per_pos=NEG_PER_POS):
    pairs = []
    for r in rows:
        text = r["text"]
        for axis, vocab in vocabs.items():
            pos = set(r.get(f"{axis}_labels") or [])
            neg_pool = [l for l in vocab if l not in pos]
            for lab in pos:
                pairs.append((text, label_defs[lab], 1, axis, lab))
                rng.shuffle(neg_pool)
                for nlab in neg_pool[:neg_per_pos]:
                    pairs.append((text, label_defs[nlab], 0, axis, nlab))
            # if no positives on axis, still sample a few negatives for calibration
            if not pos and neg_pool:
                for nlab in neg_pool[:1]:
                    pairs.append((text, label_defs[nlab], 0, axis, nlab))
    rng.shuffle(pairs)
    return pairs


def run_track_d(train, dev, rep, encoder_id, device, label_defs, vocabs):
    import numpy as np
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    from hyperlexical.classification_v6_architecture_reset_bakeoff import (
        representation_diagnostics,
    )

    tokenizer, encoder = load_encoder(encoder_id, device)
    hidden = encoder.config.hidden_size
    head = nn.Linear(hidden, 1).to(device)
    params = [p for p in encoder.parameters() if p.requires_grad] + list(head.parameters())
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.01)
    bce = nn.BCEWithLogitsLoss()
    rng = random.Random(SEED)
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")

    pairs = build_pairs(train, vocabs, label_defs, rng)
    print(f"D/{encoder_id} pairs={len(pairs)}", flush=True)

    for epoch in range(EPOCHS):
        rng.shuffle(pairs)
        encoder.train()
        head.train()
        total = 0.0
        n = 0
        for i in range(0, len(pairs), PAIR_BATCH):
            chunk = pairs[i : i + PAIR_BATCH]
            texts = [c[0] for c in chunk]
            labs = [c[1] for c in chunk]
            y = torch.tensor([c[2] for c in chunk], dtype=torch.float32, device=device)
            tok = tokenizer(
                texts,
                labs,
                padding=True,
                truncation=True,
                max_length=PAIR_MAX_LEN,
                return_tensors="pt",
            ).to(device)
            opt.zero_grad()
            cls = encoder(**tok).last_hidden_state[:, 0]
            logit = head(cls).squeeze(-1)
            loss = bce(logit, y)
            loss.backward()
            opt.step()
            total += float(loss.item())
            n += 1
        print(f"D/{encoder_id} epoch {epoch+1} loss={total/max(1,n):.4f}", flush=True)

    @torch.no_grad()
    def score_rows(rows):
        encoder.eval()
        head.eval()
        scores = {a: np.zeros((len(rows), len(v)), dtype=np.float64) for a, v in vocabs.items()}
        pos_sims, neg_sims = [], []
        for axis, vocab in vocabs.items():
            for j, lab in enumerate(vocab):
                defs = [label_defs[lab]] * len(rows)
                texts = [r["text"] for r in rows]
                logits = []
                for i in range(0, len(rows), 32):
                    tok = tokenizer(
                        texts[i : i + 32],
                        defs[i : i + 32],
                        padding=True,
                        truncation=True,
                        max_length=PAIR_MAX_LEN,
                        return_tensors="pt",
                    ).to(device)
                    cls = encoder(**tok).last_hidden_state[:, 0]
                    logit = head(cls).squeeze(-1)
                    logits.append(torch.sigmoid(logit).cpu().numpy())
                col = np.concatenate(logits) if logits else np.zeros(len(rows))
                scores[axis][:, j] = col
                for i, r in enumerate(rows):
                    gold = set(r.get(f"{axis}_labels") or [])
                    (pos_sims if lab in gold else neg_sims).append(float(col[i]))
        return scores, representation_diagnostics(pos_sims, neg_sims)

    dev_scores, _ = score_rows(dev)
    thresholds = {
        axis: thresholds_from_dev(
            dev_scores[axis],
            [multi_hot(r.get(f"{axis}_labels") or [], vocab) for r in dev],
        )
        for axis, vocab in vocabs.items()
    }
    out = {"encoder": encoder_id, "n_train": len(train), "track": "D"}
    for name, rows in (("DEV", dev), ("REP", rep)):
        scores, diag = score_rows(rows)
        packed, _, _ = eval_from_scores(
            rows, scores, vocabs, thresholds, tech_idx, ai_idx
        )
        packed["representation"] = diag
        out[name] = packed
    del encoder, head
    return out


def run_track_e(train, dev, rep, encoder_id, device, label_defs, vocabs):
    import numpy as np
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    from hyperlexical.classification_v6_architecture_reset_bakeoff import (
        representation_diagnostics,
    )

    tokenizer, encoder = load_encoder(encoder_id, device)
    hidden = encoder.config.hidden_size
    # learned label embeddings initialized from definition encodings
    encoder.eval()
    with torch.no_grad():
        init = {}
        for axis, vocab in vocabs.items():
            defs = [label_defs[l] for l in vocab]
            tok = tokenizer(
                defs, padding=True, truncation=True, max_length=PAIR_MAX_LEN, return_tensors="pt"
            ).to(device)
            h = mean_pool(encoder(**tok).last_hidden_state, tok["attention_mask"])
            init[axis] = F.normalize(h, dim=-1).detach().cpu()

    label_emb = nn.ParameterDict(
        {
            axis: nn.Parameter(init[axis].clone())
            for axis in vocabs
        }
    ).to(device)
    # small proj
    proj = nn.Linear(hidden, hidden, bias=False).to(device)
    params = (
        [p for p in encoder.parameters() if p.requires_grad]
        + list(label_emb.parameters())
        + list(proj.parameters())
    )
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.01)
    bce = nn.BCEWithLogitsLoss()
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")

    def batches(rows, shuffle=False):
        idxs = list(range(len(rows)))
        if shuffle:
            random.Random(SEED).shuffle(idxs)
        for i in range(0, len(idxs), BATCH):
            chunk = [rows[j] for j in idxs[i : i + BATCH]]
            yield chunk

    for epoch in range(EPOCHS):
        encoder.train()
        total = 0.0
        n = 0
        for chunk in batches(train, shuffle=True):
            tok = tokenizer(
                [c["text"] for c in chunk],
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            ).to(device)
            opt.zero_grad()
            h = F.normalize(proj(mean_pool(encoder(**tok).last_hidden_state, tok["attention_mask"])), dim=-1)
            loss = 0.0
            for axis, vocab in vocabs.items():
                y = torch.tensor(
                    [multi_hot(c.get(f"{axis}_labels") or [], vocab) for c in chunk],
                    dtype=torch.float32,
                    device=device,
                )
                le = F.normalize(label_emb[axis], dim=-1)
                logits = (h @ le.T) / 0.07
                loss = loss + bce(logits, y)
                # hierarchy: if AI positive, push tech logit
                if axis == "domain":
                    ai_p = torch.sigmoid(logits[:, ai_idx])
                    tech_p = torch.sigmoid(logits[:, tech_idx])
                    loss = loss + 0.5 * (ai_p * F.relu(0.5 - tech_p)).mean()
            loss.backward()
            opt.step()
            total += float(loss.item())
            n += 1
        print(f"E/{encoder_id} epoch {epoch+1} loss={total/max(1,n):.4f}", flush=True)

    @torch.no_grad()
    def score_rows(rows):
        encoder.eval()
        scores = {}
        pos_sims, neg_sims = [], []
        all_h = []
        for chunk in batches(rows, shuffle=False):
            tok = tokenizer(
                [c["text"] for c in chunk],
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            ).to(device)
            h = F.normalize(proj(mean_pool(encoder(**tok).last_hidden_state, tok["attention_mask"])), dim=-1)
            all_h.append(h.cpu())
        H = torch.cat(all_h, dim=0) if all_h else torch.zeros(0, hidden)
        for axis, vocab in vocabs.items():
            le = F.normalize(label_emb[axis], dim=-1).cpu()
            sim = (H @ le.T).numpy()
            scores[axis] = sim
            for i, r in enumerate(rows):
                gold = set(r.get(f"{axis}_labels") or [])
                for j, lab in enumerate(vocab):
                    (pos_sims if lab in gold else neg_sims).append(float(sim[i, j]))
        return scores, representation_diagnostics(pos_sims, neg_sims)

    dev_scores, _ = score_rows(dev)
    thresholds = {
        axis: thresholds_from_dev(
            dev_scores[axis],
            [multi_hot(r.get(f"{axis}_labels") or [], vocab) for r in dev],
        )
        for axis, vocab in vocabs.items()
    }
    out = {"encoder": encoder_id, "n_train": len(train), "track": "E"}
    for name, rows in (("DEV", dev), ("REP", rep)):
        scores, diag = score_rows(rows)
        packed, _, _ = eval_from_scores(
            rows, scores, vocabs, thresholds, tech_idx, ai_idx
        )
        packed["representation"] = diag
        out[name] = packed
    del encoder
    return out


def run_track_f(train, dev, rep, encoder_id, device, label_defs, vocabs):
    import numpy as np
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    from hyperlexical.classification_v6_architecture_reset_bakeoff import (
        representation_diagnostics,
    )

    tokenizer, encoder = load_encoder(encoder_id, device)
    hidden = encoder.config.hidden_size
    # label prototypes + multi-label heads
    dom_proto = nn.Parameter(torch.randn(len(vocabs["domain"]), hidden) * 0.02)
    fun_proto = nn.Parameter(torch.randn(len(vocabs["function"]), hidden) * 0.02)
    med_proto = nn.Parameter(torch.randn(len(vocabs["mediation"]), hidden) * 0.02)
    domain_head = nn.Linear(hidden, len(vocabs["domain"]))
    function_head = nn.Linear(hidden, len(vocabs["function"]))
    mediation_head = nn.Linear(hidden, len(vocabs["mediation"]))
    modules = nn.ModuleDict(
        {
            "domain_head": domain_head,
            "function_head": function_head,
            "mediation_head": mediation_head,
        }
    ).to(device)
    protos = nn.ParameterList([dom_proto, fun_proto, med_proto]).to(device)
    # init protos from label defs
    with torch.no_grad():
        for proto, vocab in (
            (dom_proto, vocabs["domain"]),
            (fun_proto, vocabs["function"]),
            (med_proto, vocabs["mediation"]),
        ):
            tok = tokenizer(
                [label_defs[l] for l in vocab],
                padding=True,
                truncation=True,
                max_length=PAIR_MAX_LEN,
                return_tensors="pt",
            ).to(device)
            h = mean_pool(encoder(**tok).last_hidden_state, tok["attention_mask"])
            proto.copy_(F.normalize(h, dim=-1))

    params = (
        [p for p in encoder.parameters() if p.requires_grad]
        + list(modules.parameters())
        + list(protos.parameters())
    )
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.01)
    bce = nn.BCEWithLogitsLoss()
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")

    # hierarchy relation matrix among domain labels: 1 same, 0.7 parent-child, 0.4 sibling, 0 unrelated
    n_d = len(vocabs["domain"])
    rel = torch.zeros(n_d, n_d)
    for i in range(n_d):
        rel[i, i] = 1.0
    rel[tech_idx, ai_idx] = rel[ai_idx, tech_idx] = 0.7
    for i in range(n_d):
        for j in range(n_d):
            if i == j:
                continue
            if rel[i, j] == 0 and vocabs["domain"][i].split(".")[0:2] == vocabs["domain"][j].split(".")[0:2]:
                rel[i, j] = 0.4
    rel = rel.to(device)

    def batches(rows, shuffle=False):
        idxs = list(range(len(rows)))
        if shuffle:
            random.Random(SEED).shuffle(idxs)
        for i in range(0, len(idxs), BATCH):
            yield [rows[j] for j in idxs[i : i + BATCH]]

    for epoch in range(EPOCHS):
        encoder.train()
        modules.train()
        total = 0.0
        n = 0
        for chunk in batches(train, shuffle=True):
            tok = tokenizer(
                [c["text"] for c in chunk],
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            ).to(device)
            opt.zero_grad()
            h = F.normalize(mean_pool(encoder(**tok).last_hidden_state, tok["attention_mask"]), dim=-1)
            y_d = torch.tensor(
                [multi_hot(c.get("domain_labels") or [], vocabs["domain"]) for c in chunk],
                dtype=torch.float32,
                device=device,
            )
            y_f = torch.tensor(
                [multi_hot(c.get("function_labels") or [], vocabs["function"]) for c in chunk],
                dtype=torch.float32,
                device=device,
            )
            y_m = torch.tensor(
                [multi_hot(c.get("mediation_labels") or [], vocabs["mediation"]) for c in chunk],
                dtype=torch.float32,
                device=device,
            )
            # label-aware attention
            da = torch.softmax(h @ F.normalize(dom_proto, dim=-1).T / 0.07, dim=-1)
            h_d = h + da @ dom_proto
            fa = torch.softmax(h @ F.normalize(fun_proto, dim=-1).T / 0.07, dim=-1)
            h_f = h + fa @ fun_proto
            ld = modules["domain_head"](h_d)
            lf = modules["function_head"](h_f)
            lm = modules["mediation_head"](h)
            loss = bce(ld, y_d) + bce(lf, y_f) + bce(lm, y_m)
            # instance-instance: pull texts sharing domain labels
            sim = h @ h.T
            share = (y_d @ y_d.T > 0).float()
            share.fill_diagonal_(0)
            if share.sum() > 0:
                loss = loss + 0.1 * F.binary_cross_entropy_with_logits(sim / 0.07, share)
            # label-label: proto similarities should respect hierarchy relation
            lp = F.normalize(dom_proto, dim=-1)
            lsim = lp @ lp.T
            loss = loss + 0.1 * F.mse_loss(lsim, rel)
            # instance-label alignment
            il = h @ lp.T / 0.07
            loss = loss + 0.2 * bce(il, y_d)
            ai_p = torch.sigmoid(ld[:, ai_idx])
            tech_p = torch.sigmoid(ld[:, tech_idx])
            loss = loss + 0.5 * (ai_p * F.relu(0.5 - tech_p)).mean()
            loss.backward()
            opt.step()
            total += float(loss.item())
            n += 1
        print(f"F/{encoder_id} epoch {epoch+1} loss={total/max(1,n):.4f}", flush=True)

    @torch.no_grad()
    def score_rows(rows):
        encoder.eval()
        modules.eval()
        scores = {a: [] for a in vocabs}
        pos_sims, neg_sims = [], []
        order_ok = []
        for chunk in batches(rows, shuffle=False):
            tok = tokenizer(
                [c["text"] for c in chunk],
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            ).to(device)
            h = F.normalize(mean_pool(encoder(**tok).last_hidden_state, tok["attention_mask"]), dim=-1)
            da = torch.softmax(h @ F.normalize(dom_proto, dim=-1).T / 0.07, dim=-1)
            h_d = h + da @ dom_proto
            fa = torch.softmax(h @ F.normalize(fun_proto, dim=-1).T / 0.07, dim=-1)
            h_f = h + fa @ fun_proto
            sd = torch.sigmoid(modules["domain_head"](h_d)).cpu().numpy()
            sf = torch.sigmoid(modules["function_head"](h_f)).cpu().numpy()
            sm = torch.sigmoid(modules["mediation_head"](h)).cpu().numpy()
            scores["domain"].append(sd)
            scores["function"].append(sf)
            scores["mediation"].append(sm)
            il = (h @ F.normalize(dom_proto, dim=-1).T).cpu().numpy()
            for i, c in enumerate(chunk):
                gold = set(c.get("domain_labels") or [])
                for j, lab in enumerate(vocabs["domain"]):
                    (pos_sims if lab in gold else neg_sims).append(float(il[i, j]))
                # hierarchy distance order: sim(parent-child) > sim(unrelated) for gold AI
                if "domain.technology.ai_discourse" in gold:
                    s_pc = float(il[i, tech_idx])
                    # unrelated: pick fashion if not gold
                    uj = vocabs["domain"].index("domain.fashion")
                    s_u = float(il[i, uj])
                    order_ok.append(1.0 if s_pc >= s_u else 0.0)
        stacked = {a: np.concatenate(scores[a], axis=0) if scores[a] else np.zeros((0, len(vocabs[a]))) for a in vocabs}
        diag = representation_diagnostics(
            pos_sims,
            neg_sims,
            hierarchy_order_ok_rate=(sum(order_ok) / len(order_ok)) if order_ok else None,
        )
        return stacked, diag

    # For F heads output probabilities already — still tune thresholds on DEV
    dev_scores, _ = score_rows(dev)
    thresholds = {
        axis: thresholds_from_dev(
            dev_scores[axis],
            [multi_hot(r.get(f"{axis}_labels") or [], vocab) for r in dev],
        )
        for axis, vocab in vocabs.items()
    }
    out = {"encoder": encoder_id, "n_train": len(train), "track": "F"}
    for name, rows in (("DEV", dev), ("REP", rep)):
        scores, diag = score_rows(rows)
        packed, _, _ = eval_from_scores(
            rows, scores, vocabs, thresholds, tech_idx, ai_idx
        )
        packed["representation"] = diag
        out[name] = packed
    del encoder
    return out


def compare_to_abc(results: dict) -> dict:
    prior_path = PRIOR_PRIV / "BAKEOFF_RESULTS.json"
    if not prior_path.exists() and not (PRIOR_PRIV / "bakeoff_results.json").exists():
        return {"available": False}
    raw = sudo_read_text(
        PRIOR_PRIV / "BAKEOFF_RESULTS.json"
        if (PRIOR_PRIV / "BAKEOFF_RESULTS.json").exists()
        else PRIOR_PRIV / "bakeoff_results.json"
    )
    abc = json.loads(raw)
    abc_best = max(
        float(v.get("REP", {}).get("system", {}).get("macro_f1") or 0) for v in abc.values()
    )
    cur_best = max(
        (
            float(v.get("REP", {}).get("system", {}).get("macro_f1") or 0)
            for k, v in results.items()
            if not k.startswith("ZERO_SHOT")
        ),
        default=0.0,
    )
    return {
        "available": True,
        "abc_best_rep_system_macro_f1": abc_best,
        "reset_best_rep_system_macro_f1": cur_best,
        "delta_vs_abc": cur_best - abc_best,
    }


def inner() -> int:
    import torch

    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text
    from hyperlexical.classification_v6_architecture_reset_bakeoff import (
        ADVANCEMENT_GATE,
        AXIS_VOCABS,
        EXPERIMENT_ID,
        PHASE_RULE,
        TRACKS,
        bakeoff_contract,
        diagnose_exhaustion,
        frozen_label_descriptions,
        select_reset_candidate,
    )
    from hyperlexical.classification_v6_data_foundation import utc_now_iso

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("reset bakeoff requires CUDA")

    contract = bakeoff_contract()
    label_defs = frozen_label_descriptions()
    vocabs = AXIS_VOCABS
    write_private(PRIVATE / "CONTRACT.json", contract)
    write_repo(REPO_ART / "contract.json", contract)

    # Prefer already-migrated splits; else re-materialize via frozen migrate_row
    # (no rule changes; migration gold semantics unchanged).
    train_path = PRIOR_PRIV / "TRAIN_V6_LABELS.jsonl"
    dev_path = PRIOR_PRIV / "DEVELOPMENT_VALIDATION_V6_LABELS.jsonl"
    rep_path = PRIOR_PRIV / "REPRESENTATIVE_VALIDATION_V6_LABELS.jsonl"
    have_migrated = False
    try:
        train_all = load_jsonl(train_path)
        dev_all = load_jsonl(dev_path)
        rep_all = load_jsonl(rep_path)
        have_migrated = bool(train_all)
    except Exception as exc:
        print(f"migrated load fallback: {exc}", flush=True)
        have_migrated = False

    if not have_migrated:
        from hyperlexical.classification_v6_label_migration import migrate_row

        FOUNDATION = Path(
            "/home/morpheus/hlx-private/classification-v6-data-foundation-20261001"
        )

        def _load(name: str) -> list[dict]:
            rows = [
                json.loads(l)
                for l in sudo_read_text(FOUNDATION / f"{name}.jsonl").splitlines()
                if l.strip()
            ]
            return [migrate_row(r) for r in rows]

        train_all = _load("TRAIN")
        dev_all = _load("DEVELOPMENT_VALIDATION")
        rep_all = _load("REPRESENTATIVE_VALIDATION")
        write_private(
            PRIVATE / "NOTE.json",
            {"migration": "recomputed_via_frozen_migrate_row_no_rule_change"},
        )

    train = usable(train_all)
    dev = usable(dev_all)
    rep = usable(rep_all)
    print(f"usable train/dev/rep={len(train)}/{len(dev)}/{len(rep)}", flush=True)

    results: dict[str, Any] = {}

    # Zero-shot diagnostic first (EXTERNAL trunk; also CONTROL for comparison)
    for enc in ("EXTERNAL", "CONTROL"):
        key = f"ZERO_SHOT_SEMANTIC_MATCH__{enc}"
        print(f"running {key}", flush=True)
        results[key] = run_zero_shot(train, dev, rep, enc, device, label_defs, vocabs)
        print(
            json.dumps(
                {
                    key: {
                        "REP_system": results[key]["REP"]["system"],
                        "REP_domain": results[key]["REP"]["domain"]["macro_f1"],
                        "REP_function": results[key]["REP"]["function"]["macro_f1"],
                    }
                },
                indent=2,
            )[:1200],
            flush=True,
        )
        write_private(PRIVATE / "BAKEOFF_RESULTS_PARTIAL.json", results)

    # Tracks D (priority), E, F × encoder controls
    runners = {
        "D_LABEL_DESCRIPTION_NLI": run_track_d,
        "E_LABEL_EMBEDDING_JOINT": run_track_e,
        "F_HIERARCHY_AWARE_CONTRASTIVE": run_track_f,
    }
    for track in TRACKS:
        for enc in ("CONTROL", "EXTERNAL"):
            key = f"{track}__{enc}"
            print(f"running {key}", flush=True)
            torch.cuda.empty_cache()
            results[key] = runners[track](
                train, dev, rep, enc, device, label_defs, vocabs
            )
            print(
                json.dumps(
                    {
                        key: {
                            "REP_system_macro_f1": results[key]["REP"]["system"]["macro_f1"],
                            "REP_domain_macro_f1": results[key]["REP"]["domain"]["macro_f1"],
                            "REP_function_macro_f1": results[key]["REP"]["function"]["macro_f1"],
                            "REP_mediation_macro_f1": results[key]["REP"]["mediation"]["macro_f1"],
                            "hierarchy_violation": results[key]["REP"]["hierarchy"][
                                "hierarchy_violation_rate"
                            ],
                        }
                    },
                    indent=2,
                ),
                flush=True,
            )
            write_private(PRIVATE / "BAKEOFF_RESULTS_PARTIAL.json", results)

    selection = select_reset_candidate(results)
    zs_best = max(
        (
            results[k]
            for k in results
            if k.startswith("ZERO_SHOT")
        ),
        key=lambda r: float(r.get("REP", {}).get("system", {}).get("macro_f1") or 0),
        default={},
    )
    abc_cmp = compare_to_abc(results)
    diagnosis = diagnose_exhaustion(
        results=results,
        zero_shot=zs_best,
        abc_best_rep=float(abc_cmp.get("abc_best_rep_system_macro_f1") or 0.0238),
    )
    if selection["advance"]:
        diagnosis["primary_failure_diagnosis"] = None
        diagnosis["note"] = "candidate advanced; failure diagnosis not primary"

    # DEV→REP gaps
    gaps = {}
    for k, r in results.items():
        gaps[k] = {
            "system": float(r.get("DEV", {}).get("system", {}).get("macro_f1") or 0)
            - float(r.get("REP", {}).get("system", {}).get("macro_f1") or 0),
            "domain": float(r.get("DEV", {}).get("domain", {}).get("macro_f1") or 0)
            - float(r.get("REP", {}).get("domain", {}).get("macro_f1") or 0),
            "function": float(r.get("DEV", {}).get("function", {}).get("macro_f1") or 0)
            - float(r.get("REP", {}).get("function", {}).get("macro_f1") or 0),
        }

    write_private(PRIVATE / "BAKEOFF_RESULTS.json", results)
    write_repo(REPO_ART / "bakeoff_results.json", results)
    write_private(PRIVATE / "BAKEOFF_SELECTION.json", selection)
    write_repo(REPO_ART / "bakeoff_selection.json", selection)
    write_private(PRIVATE / "DIAGNOSIS.json", diagnosis)
    write_repo(REPO_ART / "diagnosis.json", diagnosis)
    write_private(PRIVATE / "DEV_REP_GAPS.json", gaps)
    write_repo(REPO_ART / "dev_rep_gaps.json", gaps)
    write_private(PRIVATE / "ABC_COMPARISON.json", abc_cmp)
    write_repo(REPO_ART / "abc_comparison.json", abc_cmp)

    receipt = {
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "PHASE_RULE": PHASE_RULE,
        "TRAIN": True,
        "architecture_reset_bakeoff": True,
        "QUAL_ROWS_INSPECTED": False,
        "ontology_modified": False,
        "migration_gold_altered": False,
        "floors_lowered": False,
        "advancement_gate": ADVANCEMENT_GATE,
        "MODEL_WIDE_BEST_ROLE": "CONTROL",
        "tracks": list(TRACKS),
        "encoder_controls": ["CONTROL", "EXTERNAL"],
        "zero_shot_diagnostic": True,
        "bakeoff_selection": selection,
        "diagnosis": diagnosis,
        "abc_comparison": abc_cmp,
        "best_rep_system_macro_f1": max(
            (
                float(v.get("REP", {}).get("system", {}).get("macro_f1") or 0)
                for k, v in results.items()
                if not k.startswith("ZERO_SHOT")
            ),
            default=0.0,
        ),
        "zero_shot_best_rep_system_macro_f1": float(
            zs_best.get("REP", {}).get("system", {}).get("macro_f1") or 0
        ),
        "code_revision": code_revision(),
        "settled_at": utc_now_iso(),
        "BAKEOFF_STATE": selection["BAKEOFF_STATE"],
        "NEXT_ACTION": selection["NEXT_ACTION"],
        "selected": selection.get("selected"),
    }
    receipt["V6_ARCHITECTURE_RESET_BAKEOFF_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in receipt.items()
                if k != "V6_ARCHITECTURE_RESET_BAKEOFF_RECEIPT_SHA256"
            }
        )
    )
    write_private(PRIVATE / "RECEIPT.json", receipt)
    write_repo(REPO_ART / "receipt.json", receipt)
    write_repo(
        SPEC / "classification-v6-architecture-reset-bakeoff-receipt-20261001.json",
        receipt,
    )

    summary = {
        "BAKEOFF_STATE": receipt["BAKEOFF_STATE"],
        "NEXT_ACTION": receipt["NEXT_ACTION"],
        "RECEIPT": receipt["V6_ARCHITECTURE_RESET_BAKEOFF_RECEIPT_SHA256"],
        "selected": receipt["selected"],
        "advance": selection["advance"],
        "best_rep_system_macro_f1": receipt["best_rep_system_macro_f1"],
        "zero_shot_best_rep_system_macro_f1": receipt[
            "zero_shot_best_rep_system_macro_f1"
        ],
        "primary_failure_diagnosis": diagnosis.get("primary_failure_diagnosis"),
        "abc_best_rep_system_macro_f1": abc_cmp.get("abc_best_rep_system_macro_f1"),
        "QUAL_ROWS_INSPECTED": False,
        "floors_locked": True,
        "n_train": len(train),
        "n_dev": len(dev),
        "n_rep": len(rep),
    }
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(
        SPEC / "classification-v6-architecture-reset-bakeoff-20261001.md",
        f"""# CONTINUE_V6_ARCHITECTURE_BAKEOFF (architecture reset D/E/F)

```text
BAKEOFF_STATE = {summary['BAKEOFF_STATE']}
NEXT_ACTION = {summary['NEXT_ACTION']}
RECEIPT = {summary['RECEIPT']}
selected = {summary['selected']}
advance = {summary['advance']}
best_rep_system_macro_f1 = {summary['best_rep_system_macro_f1']}
zero_shot_best_rep_system_macro_f1 = {summary['zero_shot_best_rep_system_macro_f1']}
primary_failure_diagnosis = {summary['primary_failure_diagnosis']}
```

Tracks D/E/F with CONTROL vs EXTERNAL encoders. Zero-shot semantic matching
diagnostic first. QUAL sealed. Floors locked. No A/B/C retuning.
""",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V6_RESET_INNER") == "1":
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
        "/home/morpheus/.cache/huggingface:/home/morpheus/.cache/huggingface",
        "-w",
        str(REPO),
        "-e",
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e",
        "HLX_V2_FORWARD_ONTOLOGY=1",
        "-e",
        "HLX_V6_RESET_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v6_architecture_reset_bakeoff.py"),
    ]
    log = PRIVATE / "reset_bakeoff_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(cmd, check=False, stdout=handle, stderr=subprocess.STDOUT)
    try:
        print(log.read_text(encoding="utf-8")[-30000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
