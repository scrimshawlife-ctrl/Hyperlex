"""REBASE_V6_ON_STRONGER_PRETRAINED_SEMANTIC_ENCODER.

Frozen semantic matching first; lightweight heads; optional embedding adapter.
No QUAL. No ontology edits. MODEL_WIDE_BEST not mutated.
"""

from __future__ import annotations

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
    "/home/morpheus/hlx-private/classification-v6-representation-rebase-20261001"
)
PRIOR_PRIV = Path(
    "/home/morpheus/hlx-private/classification-v6-label-migration-bakeoff-20261001"
)
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-REPRESENTATION-REBASE-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
MAX_LEN = 192
SEED = 20261001
HEAD_EPOCHS = 40
ADAPTER_EPOCHS = 25
LR = 1e-2
ADAPTER_LR = 3e-3

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
    raw_viol = 0
    for i in range(pred.shape[0]):
        if pred[i, ai_idx] == 1 and pred[i, tech_idx] == 0:
            raw_viol += 1
            pred[i, tech_idx] = 1
    return pred, raw_viol / max(1, pred.shape[0])


def pack_axis(gold, pred, vocab, scores=None):
    from hyperlexical.classification_v6_architecture_bakeoff import multilabel_f1
    from hyperlexical.classification_v6_representation_rebase import (
        classify_label_strength,
    )
    import numpy as np

    m = multilabel_f1(gold, pred)
    g = np.asarray(gold)
    p = np.asarray(pred)
    per = {}
    for j, lab in enumerate(vocab):
        tp = int(((g[:, j] == 1) & (p[:, j] == 1)).sum())
        fp = int(((g[:, j] == 0) & (p[:, j] == 1)).sum())
        fn = int(((g[:, j] == 1) & (p[:, j] == 0)).sum())
        prec = tp / max(1, tp + fp)
        rec = tp / max(1, tp + fn)
        f1 = 2 * prec * rec / max(1e-9, prec + rec) if (prec + rec) else 0.0
        supp = int(g[:, j].sum())
        row = {
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "support": supp,
            "strength": classify_label_strength(f1, supp),
        }
        if scores is not None:
            s = np.asarray(scores)[:, j]
            pos, neg = s[g[:, j] == 1], s[g[:, j] == 0]
            row["pos_mean"] = float(pos.mean()) if len(pos) else 0.0
            row["neg_mean"] = float(neg.mean()) if len(neg) else 0.0
            row["margin"] = row["pos_mean"] - row["neg_mean"]
        per[lab] = row
    m["per_label"] = per
    return m


def eval_scores(rows, scores_by_axis, vocabs, thresholds, tech_idx, ai_idx):
    from hyperlexical.classification_v6_architecture_bakeoff import (
        hierarchy_metrics,
        multilabel_f1,
    )

    packed = {"n": len(rows)}
    golds, preds = {}, {}
    raw_viol = None
    for axis, vocab in vocabs.items():
        gold = [multi_hot(r.get(f"{axis}_labels") or [], vocab) for r in rows]
        pred = apply_th(scores_by_axis[axis], thresholds[axis])
        if axis == "domain":
            pred, raw_viol = enforce_hier(pred, tech_idx, ai_idx)
        golds[axis] = gold
        preds[axis] = pred.tolist()
        packed[axis] = pack_axis(gold, preds[axis], vocab, scores_by_axis[axis])
    g_sys = [d + f + m for d, f, m in zip(golds["domain"], golds["function"], golds["mediation"])]
    p_sys = [d + f + m for d, f, m in zip(preds["domain"], preds["function"], preds["mediation"])]
    packed["system"] = multilabel_f1(g_sys, p_sys)
    packed["hierarchy"] = hierarchy_metrics(
        golds["domain"], preds["domain"], tech_idx=tech_idx, ai_idx=ai_idx
    )
    packed["raw_hierarchy_violation"] = raw_viol
    packed["post_constraint_hierarchy_violation"] = packed["hierarchy"][
        "hierarchy_violation_rate"
    ]
    packed["preds"] = preds
    packed["golds"] = golds
    return packed


def nearest_label_purity(text_emb, label_emb, gold_lists, vocab):
    import numpy as np

    sim = text_emb @ label_emb.T
    nn = sim.argmax(axis=1)
    ok = 0
    for i, labs in enumerate(gold_lists):
        if vocab[int(nn[i])] in labs:
            ok += 1
    return ok / max(1, len(gold_lists))


def embed_model(model_id, texts, device, max_len=MAX_LEN, batch=32):
    import torch
    import torch.nn.functional as F
    from transformers import AutoModel, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_id)
    enc = AutoModel.from_pretrained(model_id).to(device)
    enc.eval()
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
    import torch as T

    T.cuda.empty_cache()
    return T.cat(vecs, dim=0).numpy()


def zero_shot_from_emb(dev, rep, vocabs, text_dev, text_rep, lab_embs):
    import numpy as np

    scores_dev = {a: text_dev @ lab_embs[a].T for a in vocabs}
    scores_rep = {a: text_rep @ lab_embs[a].T for a in vocabs}
    th = {
        a: thresholds_from_dev(
            scores_dev[a],
            [multi_hot(r.get(f"{a}_labels") or [], v) for r in dev],
        )
        for a, v in vocabs.items()
    }
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")
    out = {}
    for name, rows, sc in (("DEV", dev, scores_dev), ("REP", rep, scores_rep)):
        packed = eval_scores(rows, sc, vocabs, th, tech_idx, ai_idx)
        for axis, vocab in vocabs.items():
            golds = [r.get(f"{axis}_labels") or [] for r in rows]
            packed[axis]["nearest_label_purity"] = nearest_label_purity(
                {"DEV": text_dev, "REP": text_rep}[name],
                lab_embs[axis],
                golds,
                vocab,
            )
        out[name] = packed
    out["thresholds"] = th
    return out


def train_linear_or_mlp(Xtr, Ytr, Xdv, Ydv, Xrp, hidden, n_out, kind, device):
    import numpy as np
    import torch
    import torch.nn as nn

    if kind == "linear":
        model = nn.Linear(hidden, n_out).to(device)
    else:
        model = nn.Sequential(
            nn.Linear(hidden, 128), nn.ReLU(), nn.Linear(128, n_out)
        ).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=LR)
    bce = nn.BCEWithLogitsLoss()
    xt = torch.tensor(Xtr, device=device)
    yt = torch.tensor(Ytr, device=device)
    for _ in range(HEAD_EPOCHS):
        opt.zero_grad()
        loss = bce(model(xt), yt)
        loss.backward()
        opt.step()
    with torch.no_grad():
        sdv = torch.sigmoid(model(torch.tensor(Xdv, device=device))).cpu().numpy()
        srp = torch.sigmoid(model(torch.tensor(Xrp, device=device))).cpu().numpy()
    return sdv, srp


def calibrated_similarity(scores_tr, Ytr, scores_dv, scores_rp, device):
    """Per-label affine calibration of cosine scores."""
    import numpy as np
    import torch
    import torch.nn as nn

    n = scores_tr.shape[1]
    scale = nn.Parameter(torch.ones(n, device=device))
    bias = nn.Parameter(torch.zeros(n, device=device))
    opt = torch.optim.Adam([scale, bias], lr=0.05)
    bce = nn.BCEWithLogitsLoss()
    st = torch.tensor(scores_tr, device=device)
    yt = torch.tensor(Ytr, device=device)
    for _ in range(80):
        opt.zero_grad()
        logits = st * scale + bias
        loss = bce(logits, yt)
        loss.backward()
        opt.step()
    with torch.no_grad():
        sdv = torch.sigmoid(
            torch.tensor(scores_dv, device=device) * scale + bias
        ).cpu().numpy()
        srp = torch.sigmoid(
            torch.tensor(scores_rp, device=device) * scale + bias
        ).cpu().numpy()
    return sdv, srp


def adapter_transform(Xtr, Xdv, Xrp, device, rank=16):
    import numpy as np
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    hidden = Xtr.shape[1]
    down = nn.Linear(hidden, rank, bias=False).to(device)
    up = nn.Linear(rank, hidden, bias=False).to(device)
    nn.init.zeros_(up.weight)
    opt = torch.optim.AdamW(list(down.parameters()) + list(up.parameters()), lr=ADAPTER_LR)
    xt = torch.tensor(Xtr, device=device)
    # reconstruct + slight contrast: keep near original
    for _ in range(ADAPTER_EPOCHS):
        opt.zero_grad()
        h = F.normalize(xt + up(torch.relu(down(xt))), dim=-1)
        loss = (1 - (h * F.normalize(xt, dim=-1)).sum(-1)).mean()
        loss.backward()
        opt.step()
    def apply(X):
        with torch.no_grad():
            x = torch.tensor(X, device=device)
            h = F.normalize(x + up(torch.relu(down(x))), dim=-1)
            return h.cpu().numpy()
    return apply(Xtr), apply(Xdv), apply(Xrp), down, up


def error_decomp(gold_sys, pred_a, pred_b, vocabs):
    """Compare zs vs candidate error types on concatenated system vectors."""
    import numpy as np

    ga = np.asarray(gold_sys)
    a = np.asarray(pred_a)
    b = np.asarray(pred_b)
    n_lab = ga.shape[1]
    # split points
    nd, nf = len(vocabs["domain"]), len(vocabs["function"])
    out = {
        "fp_a": int(((a == 1) & (ga == 0)).sum()),
        "fn_a": int(((a == 0) & (ga == 1)).sum()),
        "fp_b": int(((b == 1) & (ga == 0)).sum()),
        "fn_b": int(((b == 0) & (ga == 1)).sum()),
        "fixed_fp": int(((a == 1) & (b == 0) & (ga == 0)).sum()),
        "new_fp": int(((a == 0) & (b == 1) & (ga == 0)).sum()),
        "fixed_fn": int(((a == 0) & (b == 1) & (ga == 1)).sum()),
        "new_fn": int(((a == 1) & (b == 0) & (ga == 1)).sum()),
        "axis_confusion_moved": 0,
    }
    return out


def inner() -> int:
    import numpy as np
    import torch

    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text
    from hyperlexical.classification_v6_architecture_reset_bakeoff import AXIS_VOCABS
    from hyperlexical.classification_v6_data_foundation import utc_now_iso
    from hyperlexical.classification_v6_representation_rebase import (
        ADVANCEMENT,
        ENCODER_FAMILY,
        EXPERIMENT_ID,
        MPNET_WITNESS,
        PHASE_RULE,
        axis_collapse,
        classify_geometry,
        label_texts,
        rebase_contract,
        select_rebase_state,
    )

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated_before")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("CUDA required")

    contract = rebase_contract()
    write_private(PRIVATE / "CONTRACT.json", contract)
    write_repo(REPO_ART / "contract.json", contract)

    train = usable(load_jsonl(PRIOR_PRIV / "TRAIN_V6_LABELS.jsonl"))
    dev = usable(load_jsonl(PRIOR_PRIV / "DEVELOPMENT_VALIDATION_V6_LABELS.jsonl"))
    rep = usable(load_jsonl(PRIOR_PRIV / "REPRESENTATIVE_VALIDATION_V6_LABELS.jsonl"))
    print(f"usable train/dev/rep={len(train)}/{len(dev)}/{len(rep)}", flush=True)
    vocabs = AXIS_VOCABS
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")
    short = label_texts("short_definition")
    full = label_texts("full_boundary_contract")

    # --- read-only encoder family, short defs ---
    zs_results = {}
    embeddings = {}
    for tag, mid in ENCODER_FAMILY.items():
        print(f"embed {tag} {mid}", flush=True)
        texts_tr = [r["text"] for r in train]
        texts_dv = [r["text"] for r in dev]
        texts_rp = [r["text"] for r in rep]
        Xtr = embed_model(mid, texts_tr, device)
        Xdv = embed_model(mid, texts_dv, device)
        Xrp = embed_model(mid, texts_rp, device)
        lab_short = {a: embed_model(mid, [short[l] for l in v], device) for a, v in vocabs.items()}
        zs = zero_shot_from_emb(dev, rep, vocabs, Xdv, Xrp, lab_short)
        zs["model_id"] = mid
        zs["label_variant"] = "short_definition"
        zs_results[f"ZERO_SHOT__{tag}__short"] = zs
        print(
            f"  {tag} short REP macro={zs['REP']['system']['macro_f1']:.4f}",
            flush=True,
        )
        embeddings[tag] = {
            "Xtr": Xtr,
            "Xdv": Xdv,
            "Xrp": Xrp,
            "lab_short": lab_short,
            "model_id": mid,
        }
        write_private(
            PRIVATE / "ZERO_SHOT_PARTIAL.json",
            {
                k: float(v["REP"]["system"]["macro_f1"])
                for k, v in zs_results.items()
            },
        )

    # full boundary contract on encoders that approach witness
    witness = ADVANCEMENT["mpnet_witness"]
    for tag, pack in list(embeddings.items()):
        zs_m = zs_results[f"ZERO_SHOT__{tag}__short"]["REP"]["system"]["macro_f1"]
        if zs_m + 0.03 < witness and tag != "A_MPNET":
            print(f"skip full-contract + train for {tag} (zs {zs_m:.3f} << witness)", flush=True)
            continue
        print(f"full-contract {tag}", flush=True)
        lab_full = {
            a: embed_model(pack["model_id"], [full[l] for l in v], device)
            for a, v in vocabs.items()
        }
        pack["lab_full"] = lab_full
        zs = zero_shot_from_emb(dev, rep, vocabs, pack["Xdv"], pack["Xrp"], lab_full)
        zs["model_id"] = pack["model_id"]
        zs["label_variant"] = "full_boundary_contract"
        zs_results[f"ZERO_SHOT__{tag}__full"] = zs
        print(f"  {tag} full REP macro={zs['REP']['system']['macro_f1']:.4f}", flush=True)

    # Best shared vs axis-specific encoder from zero-shot shorts
    axis_best = {}
    for axis in ("domain", "function", "mediation"):
        best_tag, best_v = None, -1.0
        for tag in embeddings:
            key = f"ZERO_SHOT__{tag}__short"
            if key not in zs_results:
                continue
            v = zs_results[key]["REP"][axis]["macro_f1"]
            if v > best_v:
                best_tag, best_v = tag, v
        axis_best[axis] = {"encoder": best_tag, "macro_f1": best_v}
    uniq = {axis_best[a]["encoder"] for a in axis_best}
    axis_finding = (
        "SHARED_ENCODER_SUPPORTED"
        if len(uniq) == 1
        else "AXIS_SPECIFIC_ENCODERS_SUPPORTED"
    )
    # material gain: if mixing axes would lift mean > 0.03 vs single best shared
    shared_best_tag = max(
        embeddings,
        key=lambda t: zs_results[f"ZERO_SHOT__{t}__short"]["REP"]["system"]["macro_f1"],
    )
    write_private(
        PRIVATE / "AXIS_ENCODER.json",
        {"axis_best": axis_best, "finding": axis_finding, "shared_best": shared_best_tag},
    )

    # Train only on encoders approaching witness
    trainable_tags = [
        t
        for t in embeddings
        if zs_results[f"ZERO_SHOT__{t}__short"]["REP"]["system"]["macro_f1"]
        >= witness - 0.03
        or t == "A_MPNET"
    ]
    print(f"trainable tags: {trainable_tags}", flush=True)

    trained = {}
    for tag in trainable_tags:
        pack = embeddings[tag]
        Xtr, Xdv, Xrp = pack["Xtr"], pack["Xdv"], pack["Xrp"]
        hidden = Xtr.shape[1]
        lab = pack.get("lab_short")
        # cosine scores
        sc_tr = {a: Xtr @ lab[a].T for a in vocabs}
        sc_dv = {a: Xdv @ lab[a].T for a in vocabs}
        sc_rp = {a: Xrp @ lab[a].T for a in vocabs}

        # A. already have zero-shot
        # B. calibrated similarity
        print(f"{tag} calibrated similarity", flush=True)
        cal_dv, cal_rp = {}, {}
        for a, v in vocabs.items():
            Ytr = np.asarray(
                [multi_hot(r.get(f"{a}_labels") or [], v) for r in train], dtype=np.float32
            )
            sdv, srp = calibrated_similarity(sc_tr[a], Ytr, sc_dv[a], sc_rp[a], device)
            cal_dv[a], cal_rp[a] = sdv, srp
        th = {
            a: thresholds_from_dev(
                cal_dv[a],
                [multi_hot(r.get(f"{a}_labels") or [], v) for r in dev],
            )
            for a, v in vocabs.items()
        }
        trained[f"CALIBRATED_SIM__{tag}"] = {
            "DEV": eval_scores(dev, cal_dv, vocabs, th, tech_idx, ai_idx),
            "REP": eval_scores(rep, cal_rp, vocabs, th, tech_idx, ai_idx),
            "thresholds": th,
            "formulation": "learned_calibration_on_similarity",
            "encoder": tag,
        }
        print(
            f"  cal REP={trained[f'CALIBRATED_SIM__{tag}']['REP']['system']['macro_f1']:.4f}",
            flush=True,
        )

        # C. frozen linear / nonlinear heads (shared embedding, axis heads)
        for kind in ("linear", "nonlinear"):
            print(f"{tag} frozen {kind} heads", flush=True)
            dv, rp = {}, {}
            for a, v in vocabs.items():
                Ytr = np.asarray(
                    [multi_hot(r.get(f"{a}_labels") or [], v) for r in train],
                    dtype=np.float32,
                )
                Ydv = np.asarray(
                    [multi_hot(r.get(f"{a}_labels") or [], v) for r in dev],
                    dtype=np.float32,
                )
                sdv, srp = train_linear_or_mlp(
                    Xtr, Ytr, Xdv, Ydv, Xrp, hidden, len(v), kind, device
                )
                dv[a], rp[a] = sdv, srp
            th = {
                a: thresholds_from_dev(
                    dv[a],
                    [multi_hot(r.get(f"{a}_labels") or [], v) for r in dev],
                )
                for a, v in vocabs.items()
            }
            key = f"FROZEN_{kind.upper()}__{tag}"
            trained[key] = {
                "DEV": eval_scores(dev, dv, vocabs, th, tech_idx, ai_idx),
                "REP": eval_scores(rep, rp, vocabs, th, tech_idx, ai_idx),
                "thresholds": th,
                "formulation": f"frozen_embedding_{kind}_heads",
                "encoder": tag,
            }
            print(
                f"  {kind} REP={trained[key]['REP']['system']['macro_f1']:.4f}",
                flush=True,
            )

        # axis-specific projection vs shared (linear proj then linear head)
        print(f"{tag} axis-specific projections", flush=True)
        import torch.nn as nn
        import torch.nn.functional as F

        dv, rp = {}, {}
        for a, v in vocabs.items():
            Ytr = np.asarray(
                [multi_hot(r.get(f"{a}_labels") or [], v) for r in train], dtype=np.float32
            )
            proj = nn.Linear(hidden, hidden, bias=False).to(device)
            head = nn.Linear(hidden, len(v)).to(device)
            opt = torch.optim.AdamW(list(proj.parameters()) + list(head.parameters()), lr=LR)
            bce = nn.BCEWithLogitsLoss()
            xt = torch.tensor(Xtr, device=device)
            yt = torch.tensor(Ytr, device=device)
            for _ in range(HEAD_EPOCHS):
                opt.zero_grad()
                h = F.normalize(proj(xt), dim=-1)
                loss = bce(head(h), yt)
                loss.backward()
                opt.step()
            with torch.no_grad():
                dv[a] = torch.sigmoid(
                    head(F.normalize(proj(torch.tensor(Xdv, device=device)), dim=-1))
                ).cpu().numpy()
                rp[a] = torch.sigmoid(
                    head(F.normalize(proj(torch.tensor(Xrp, device=device)), dim=-1))
                ).cpu().numpy()
        th = {
            a: thresholds_from_dev(
                dv[a], [multi_hot(r.get(f"{a}_labels") or [], v) for r in dev]
            )
            for a, v in vocabs.items()
        }
        trained[f"AXIS_PROJ__{tag}"] = {
            "DEV": eval_scores(dev, dv, vocabs, th, tech_idx, ai_idx),
            "REP": eval_scores(rep, rp, vocabs, th, tech_idx, ai_idx),
            "thresholds": th,
            "formulation": "axis_specific_projections",
            "encoder": tag,
        }
        print(
            f"  axis-proj REP={trained[f'AXIS_PROJ__{tag}']['REP']['system']['macro_f1']:.4f}",
            flush=True,
        )

        # PEFT adapter on frozen embeddings + linear heads
        print(f"{tag} PEFT adapter", flush=True)
        Atr, Adv, Arp, _, _ = adapter_transform(Xtr, Xdv, Xrp, device)
        # geometry vs original
        import torch.nn.functional as TF

        t0 = torch.tensor(Xrp[:64])
        t1 = torch.tensor(Arp[:64])
        cos = float(TF.cosine_similarity(t0, t1, dim=-1).mean())
        # NN retention among 64
        sim0 = (Xrp[:64] @ Xrp[:64].T)
        np.fill_diagonal(sim0, -np.inf)
        sim1 = (Arp[:64] @ Arp[:64].T)
        np.fill_diagonal(sim1, -np.inf)
        nn0, nn1 = sim0.argmax(1), sim1.argmax(1)
        nn_ret = float((nn0 == nn1).mean())
        dv, rp = {}, {}
        for a, v in vocabs.items():
            Ytr = np.asarray(
                [multi_hot(r.get(f"{a}_labels") or [], v) for r in train], dtype=np.float32
            )
            Ydv = np.asarray(
                [multi_hot(r.get(f"{a}_labels") or [], v) for r in dev], dtype=np.float32
            )
            sdv, srp = train_linear_or_mlp(
                Atr, Ytr, Adv, Ydv, Arp, hidden, len(v), "linear", device
            )
            dv[a], rp[a] = sdv, srp
        th = {
            a: thresholds_from_dev(
                dv[a], [multi_hot(r.get(f"{a}_labels") or [], v) for r in dev]
            )
            for a, v in vocabs.items()
        }
        packed_rep = eval_scores(rep, rp, vocabs, th, tech_idx, ai_idx)
        packed_dev = eval_scores(dev, dv, vocabs, th, tech_idx, ai_idx)
        zs_rep = zs_results[f"ZERO_SHOT__{tag}__short"]["REP"]["system"]["macro_f1"]
        # margin change on domain cosine after adapter
        m0 = float(
            np.mean(
                [
                    zs_results[f"ZERO_SHOT__{tag}__short"]["REP"]["domain"]["per_label"][l].get(
                        "margin", 0
                    )
                    for l in vocabs["domain"]
                ]
            )
        )
        # approximate post-adapter cosine margin using adapted text vs original labels
        sc_ad = Xrp  # placeholder unused
        geo = classify_geometry(
            cosine_drift=cos,
            nn_retention=nn_ret,
            margin_delta=0.0,
            rep_delta=packed_rep["system"]["macro_f1"] - zs_rep,
        )
        trained[f"PEFT_ADAPTER__{tag}"] = {
            "DEV": packed_dev,
            "REP": packed_rep,
            "thresholds": th,
            "formulation": "parameter_efficient_adapter",
            "encoder": tag,
            "drift": {
                "cosine_to_pretrained": cos,
                "nn_retention": nn_ret,
                "geometry": geo,
            },
        }
        print(
            f"  peft REP={packed_rep['system']['macro_f1']:.4f} geo={geo} cos={cos:.3f} nn={nn_ret:.3f}",
            flush=True,
        )

    # Build candidate table
    candidates = []
    def add_cand(cid, formulation, encoder, blk, extra=None):
        extra = extra or {}
        rep = blk["REP"]
        devb = blk["DEV"]
        row = {
            "id": cid,
            "formulation": formulation,
            "encoder": encoder,
            "rep_system_macro_f1": float(rep["system"]["macro_f1"]),
            "dev_macro_f1": float(devb["system"]["macro_f1"]),
            "hierarchy_violation_rate_rep": float(
                rep["hierarchy"]["hierarchy_violation_rate"]
            ),
            "raw_hierarchy_violation": rep.get("raw_hierarchy_violation"),
            "axis_collapse": axis_collapse(rep),
            "gap": float(devb["system"]["macro_f1"]) - float(rep["system"]["macro_f1"]),
            "domain_macro": float(rep["domain"]["macro_f1"]),
            "function_macro": float(rep["function"]["macro_f1"]),
            "mediation_macro": float(rep["mediation"]["macro_f1"]),
        }
        row.update(extra)
        candidates.append(row)

    for k, v in zs_results.items():
        add_cand(k, "zero_shot_similarity", k.split("__")[1], v)
    for k, v in trained.items():
        extra = {}
        if "drift" in v:
            extra["geometry"] = v["drift"]["geometry"]
            extra["cosine_to_pretrained"] = v["drift"]["cosine_to_pretrained"]
            extra["nn_retention"] = v["drift"]["nn_retention"]
        add_cand(k, v["formulation"], v["encoder"], v, extra)

    selection = select_rebase_state(candidates)
    print(json.dumps({"selection": selection, "top": candidates[:3]}, indent=2, default=str)[:2000], flush=True)

    # error decomp: MPNet zs vs selected trained if any
    zs_mpnet = zs_results["ZERO_SHOT__A_MPNET__short"]
    err = {}
    g_sys = [
        d + f + m
        for d, f, m in zip(
            zs_mpnet["REP"]["golds"]["domain"],
            zs_mpnet["REP"]["golds"]["function"],
            zs_mpnet["REP"]["golds"]["mediation"],
        )
    ]
    p_zs = [
        d + f + m
        for d, f, m in zip(
            zs_mpnet["REP"]["preds"]["domain"],
            zs_mpnet["REP"]["preds"]["function"],
            zs_mpnet["REP"]["preds"]["mediation"],
        )
    ]
    for k, v in trained.items():
        if v["encoder"] != "A_MPNET":
            continue
        p_b = [
            d + f + m
            for d, f, m in zip(
                v["REP"]["preds"]["domain"],
                v["REP"]["preds"]["function"],
                v["REP"]["preds"]["mediation"],
            )
        ]
        err[k] = error_decomp(g_sys, p_zs, p_b, vocabs)

    # pointer
    pointer = {
        "MODEL_WIDE_BEST": BEST_SHA,
        "MODEL_WIDE_BEST_ROLE": "HISTORICAL_CONTROL_REPRESENTATION",
        "MODEL_WIDE_BEST_MUTATED": False,
        "V6_REPRESENTATION_CANDIDATE": None,
    }
    if selection["REBASE_STATE"] == "V6_REPRESENTATION_REBASE_ADVANCE" and selection["selected"]:
        pointer["V6_REPRESENTATION_CANDIDATE"] = {
            "id": selection["selected"],
            "status": "CANDIDATE_NOT_PROMOTED",
            "encoder": (selection.get("selected_row") or {}).get("encoder"),
            "formulation": (selection.get("selected_row") or {}).get("formulation"),
        }
    elif selection["REBASE_STATE"] == "V6_REPRESENTATION_REBASE_ZERO_SHOT_ONLY":
        pointer["V6_REPRESENTATION_CANDIDATE"] = {
            "id": selection["selected"],
            "status": "ZERO_SHOT_WITNESS_NOT_PROMOTED",
            "encoder": "A_MPNET",
            "formulation": "zero_shot_similarity",
            "model_id": ENCODER_FAMILY["A_MPNET"],
        }

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated_after")

    # strip preds/golds for repo dumps
    def slim_blk(blk):
        if not isinstance(blk, dict):
            return blk
        return {k: v for k, v in blk.items() if k not in {"preds", "golds"}}

    def slim_result(res):
        out = {}
        for k, v in res.items():
            if k in {"DEV", "REP"} and isinstance(v, dict):
                out[k] = slim_blk(v)
            elif k == "thresholds":
                out[k] = v
            else:
                out[k] = v if k not in {"DEV", "REP"} else slim_blk(v)
        return out

    zs_slim = {k: slim_result(v) for k, v in zs_results.items()}
    tr_slim = {k: slim_result(v) for k, v in trained.items()}

    write_private(PRIVATE / "ZERO_SHOT.json", zs_slim)
    write_private(PRIVATE / "TRAINED.json", tr_slim)
    write_private(PRIVATE / "CANDIDATES.json", candidates)
    write_private(PRIVATE / "SELECTION.json", selection)
    write_private(PRIVATE / "ERROR_DECOMP.json", err)
    write_private(PRIVATE / "POINTER.json", pointer)

    receipt = {
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "PHASE_RULE": PHASE_RULE,
        "QUAL_ROWS_INSPECTED": False,
        "ontology_modified": False,
        "MODEL_WIDE_BEST_MUTATED": False,
        "floors_lowered": False,
        "mpnet_witness": MPNET_WITNESS,
        "encoders": ENCODER_FAMILY,
        "zero_shot_rep": {
            k: v["REP"]["system"]["macro_f1"] for k, v in zs_slim.items()
        },
        "trained_rep": {
            k: v["REP"]["system"]["macro_f1"] for k, v in tr_slim.items()
        },
        "axis_encoder": {
            "axis_best": axis_best,
            "finding": axis_finding,
            "shared_best": shared_best_tag,
        },
        "selection": selection,
        "pointer": pointer,
        "candidates": candidates,
        "code_revision": code_revision(),
        "settled_at": utc_now_iso(),
        "REBASE_STATE": selection["REBASE_STATE"],
        "NEXT_ACTION": selection["NEXT_ACTION"],
    }
    receipt["V6_REPRESENTATION_REBASE_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {k: v for k, v in receipt.items() if k != "V6_REPRESENTATION_REBASE_RECEIPT_SHA256"}
        )
    )
    write_private(PRIVATE / "RECEIPT.json", receipt)
    write_repo(REPO_ART / "receipt.json", receipt)
    write_repo(
        SPEC / "classification-v6-representation-rebase-receipt-20261001.json", receipt
    )

    summary = {
        "REBASE_STATE": selection["REBASE_STATE"],
        "NEXT_ACTION": selection["NEXT_ACTION"],
        "RECEIPT": receipt["V6_REPRESENTATION_REBASE_RECEIPT_SHA256"],
        "selected": selection["selected"],
        "MINIMUM_ADVANCE": selection["MINIMUM_ADVANCE"],
        "REPRESENTATION_IMPROVEMENT": selection["REPRESENTATION_IMPROVEMENT"],
        "mpnet_witness": witness,
        "zero_shot_rep": receipt["zero_shot_rep"],
        "trained_rep": receipt["trained_rep"],
        "axis_finding": axis_finding,
        "pointer": pointer,
        "QUAL_ROWS_INSPECTED": False,
        "MODEL_WIDE_BEST_MUTATED": False,
        "n_train": len(train),
        "n_dev": len(dev),
        "n_rep": len(rep),
    }
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(REPO_ART / "zero_shot.json", zs_slim)
    write_repo(REPO_ART / "trained.json", tr_slim)
    write_repo(REPO_ART / "candidates.json", candidates)
    write_repo(REPO_ART / "selection.json", selection)
    write_repo(REPO_ART / "pointer.json", pointer)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V6_REBASE_INNER") == "1":
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
        "HLX_V6_REBASE_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v6_representation_rebase.py"),
    ]
    log = PRIVATE / "rebase_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(cmd, check=False, stdout=handle, stderr=subprocess.STDOUT)
    try:
        print(log.read_text(encoding="utf-8")[-35000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
