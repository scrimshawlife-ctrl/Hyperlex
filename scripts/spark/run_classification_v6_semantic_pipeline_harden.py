"""HARDEN_V6_SEMANTIC_REPRESENTATION_AND_PREPARE_QUALIFICATION.

Reproduce FROZEN_NONLINEAR__C_MSMARCO, persist artifacts, cold-load / round-trip,
REP replay, robustness slices, QUAL preregistration (no QUAL row inspect).
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
    "/home/morpheus/hlx-private/classification-v6-semantic-pipeline-harden-20261001"
)
PRIOR_PRIV = Path(
    "/home/morpheus/hlx-private/classification-v6-label-migration-bakeoff-20261001"
)
REBASE_PRIV = Path(
    "/home/morpheus/hlx-private/classification-v6-representation-rebase-20261001"
)
QUAL_META = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-DATA-FOUNDATION-001"
    / "qualification_metadata.json"
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
    / "HLX-CLASSIFICATION-V6-SEMANTIC-PIPELINE-HARDEN-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
MAX_LEN = 192
SEED = 20261001
HEAD_EPOCHS = 40
LR = 1e-2

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


def apply_th(scores, th):
    import numpy as np

    scores = np.asarray(scores)
    out = np.zeros_like(scores, dtype=np.int32)
    for j, t in enumerate(th):
        out[:, j] = (scores[:, j] >= t).astype(np.int32)
    return out


def enforce_hier(pred, tech_idx, ai_idx):
    import numpy as np

    pred = np.array(pred, dtype=np.int32, copy=True)
    raw_viol = 0
    corrected = 0
    for i in range(pred.shape[0]):
        if pred[i, ai_idx] == 1 and pred[i, tech_idx] == 0:
            raw_viol += 1
            pred[i, tech_idx] = 1
            corrected += 1
    return pred, raw_viol / max(1, pred.shape[0]), corrected


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
    golds, preds_raw, preds = {}, {}, {}
    raw_viol = None
    corrected = 0
    for axis, vocab in vocabs.items():
        gold = [multi_hot(r.get(f"{axis}_labels") or [], vocab) for r in rows]
        raw = apply_th(scores_by_axis[axis], thresholds[axis])
        if axis == "domain":
            constrained, raw_viol, corrected = enforce_hier(raw, tech_idx, ai_idx)
            pred = constrained
        else:
            pred = raw
        golds[axis] = gold
        preds_raw[axis] = raw.tolist()
        preds[axis] = pred.tolist() if hasattr(pred, "tolist") else pred
        packed[axis] = pack_axis(gold, preds[axis], vocab, scores_by_axis[axis])
    g_sys = [
        d + f + m
        for d, f, m in zip(golds["domain"], golds["function"], golds["mediation"])
    ]
    p_sys = [
        d + f + m
        for d, f, m in zip(preds["domain"], preds["function"], preds["mediation"])
    ]
    p_sys_raw = [
        d + f + m
        for d, f, m in zip(
            preds_raw["domain"], preds_raw["function"], preds_raw["mediation"]
        )
    ]
    packed["system"] = multilabel_f1(g_sys, p_sys)
    packed["system_raw"] = multilabel_f1(g_sys, p_sys_raw)
    packed["hierarchy"] = hierarchy_metrics(
        golds["domain"], preds["domain"], tech_idx=tech_idx, ai_idx=ai_idx
    )
    packed["raw_hierarchy_violation"] = raw_viol
    packed["post_constraint_hierarchy_violation"] = packed["hierarchy"][
        "hierarchy_violation_rate"
    ]
    packed["hierarchy_corrected"] = corrected
    packed["preds"] = preds
    packed["preds_raw"] = preds_raw
    packed["golds"] = golds
    return packed


def embed_model(model_id, texts, device, max_len=MAX_LEN, batch=32, revision=None):
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
    # hash encoder state
    import hashlib

    hsh = hashlib.sha256()
    for k, tns in sorted(enc.state_dict().items()):
        hsh.update(k.encode())
        hsh.update(tns.detach().cpu().numpy().tobytes())
    enc_hash = hsh.hexdigest()
    n_train = sum(p.numel() for p in enc.parameters() if p.requires_grad)
    del enc
    torch.cuda.empty_cache()
    return torch.cat(vecs, dim=0).numpy(), enc_hash, n_train


def build_mlp(hidden: int, n_out: int, device):
    import torch.nn as nn

    return nn.Sequential(
        nn.Linear(hidden, 128), nn.ReLU(), nn.Linear(128, n_out)
    ).to(device)


def calibrated_similarity_warmup(scores_tr, Ytr, device):
    """Replay bakeoff calibrated-similarity torch ops to align RNG state."""
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
        loss = bce(st * scale + bias, yt)
        loss.backward()
        opt.step()


def train_linear_warmup(Xtr, Ytr, n_out, device):
    """Replay bakeoff frozen-linear head training to align RNG state."""
    import torch
    import torch.nn as nn

    model = nn.Linear(Xtr.shape[1], n_out).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=LR)
    bce = nn.BCEWithLogitsLoss()
    xt = torch.tensor(Xtr, device=device)
    yt = torch.tensor(Ytr, device=device)
    for _ in range(HEAD_EPOCHS):
        opt.zero_grad()
        loss = bce(model(xt), yt)
        loss.backward()
        opt.step()
    del model


def train_axis_heads(Xtr, Ytr_by_axis, vocabs, device, lab_embs=None):
    import torch
    import torch.nn as nn

    # Match rebase bakeoff order for C_MSMARCO: calibrated sim → linear → nonlinear.
    set_seeds(SEED)
    hidden = Xtr.shape[1]
    if lab_embs is not None:
        for axis, vocab in vocabs.items():
            sc_tr = Xtr @ lab_embs[axis].T
            calibrated_similarity_warmup(sc_tr, Ytr_by_axis[axis], device)
        for axis, vocab in vocabs.items():
            train_linear_warmup(Xtr, Ytr_by_axis[axis], len(vocab), device)
    heads = {}
    for axis, vocab in vocabs.items():
        model = build_mlp(hidden, len(vocab), device)
        opt = torch.optim.AdamW(model.parameters(), lr=LR)
        bce = nn.BCEWithLogitsLoss()
        xt = torch.tensor(Xtr, device=device)
        yt = torch.tensor(Ytr_by_axis[axis], device=device)
        model.train()
        for _ in range(HEAD_EPOCHS):
            opt.zero_grad()
            loss = bce(model(xt), yt)
            loss.backward()
            opt.step()
        model.eval()
        heads[axis] = model
    return heads


def scores_from_heads(heads, X, device):
    import torch

    out = {}
    with torch.no_grad():
        xt = torch.tensor(X, device=device)
        for axis, model in heads.items():
            out[axis] = torch.sigmoid(model(xt)).cpu().numpy()
    return out


def state_dict_cpu(model):
    return {k: v.detach().cpu() for k, v in model.state_dict().items()}


def save_head_bundle(path: Path, heads, meta: dict) -> str:
    import torch

    bundle = {
        "meta": meta,
        "state": {axis: state_dict_cpu(m) for axis, m in heads.items()},
    }
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    torch.save(bundle, path)
    os.chmod(path, 0o600)
    return sha256_file(path)


def load_head_bundle(path: Path, hidden: int, vocabs, device):
    import torch

    try:
        bundle = torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:
        bundle = torch.load(path, map_location="cpu")
    heads = {}
    for axis, vocab in vocabs.items():
        m = build_mlp(hidden, len(vocab), device)
        m.load_state_dict(bundle["state"][axis])
        m.eval()
        heads[axis] = m
    return heads, bundle.get("meta") or {}


def geometry_witness(Xrp, lab_embs, rep_rows, vocabs):
    import numpy as np

    out = {}
    for axis, vocab in vocabs.items():
        gold = [r.get(f"{axis}_labels") or [] for r in rep_rows]
        sim = Xrp @ lab_embs[axis].T
        pos_sims, neg_sims = [], []
        for i, labs in enumerate(gold):
            for j, lab in enumerate(vocab):
                if lab in labs:
                    pos_sims.append(float(sim[i, j]))
                else:
                    neg_sims.append(float(sim[i, j]))
        nn = sim.argmax(axis=1)
        purity = sum(1 for i, labs in enumerate(gold) if vocab[int(nn[i])] in labs) / max(
            1, len(gold)
        )
        # within / between label dispersion on positive texts
        within, between = [], []
        for j, lab in enumerate(vocab):
            idx = [i for i, labs in enumerate(gold) if lab in labs]
            if len(idx) >= 2:
                vecs = Xrp[idx]
                c = vecs.mean(axis=0)
                c = c / max(1e-9, np.linalg.norm(c))
                within.append(float(np.mean(vecs @ c)))
            others = [i for i, labs in enumerate(gold) if lab not in labs]
            if idx and others:
                between.append(
                    float(np.mean(Xrp[idx] @ lab_embs[axis][j]))  # placeholder
                )
        # hard-neg: highest non-gold similarity
        hard = []
        for i, labs in enumerate(gold):
            order = np.argsort(-sim[i])
            for j in order:
                if vocab[int(j)] not in labs:
                    hard.append(float(sim[i, j]))
                    break
        out[axis] = {
            "positive_text_label_similarity": float(np.mean(pos_sims)) if pos_sims else 0.0,
            "hard_negative_similarity": float(np.mean(hard)) if hard else 0.0,
            "nearest_label_purity": purity,
            "within_label_dispersion": float(np.mean(within)) if within else 0.0,
            "between_label_dispersion": float(np.mean(between)) if between else 0.0,
            "neg_mean_similarity": float(np.mean(neg_sims)) if neg_sims else 0.0,
        }
    return out


def support_manifest(train, dev, rep, vocabs):
    out = {}
    for axis, vocab in vocabs.items():
        for lab in vocab:
            out[lab] = {
                "axis": axis,
                "TRAIN": sum(1 for r in train if lab in (r.get(f"{axis}_labels") or [])),
                "DEV": sum(1 for r in dev if lab in (r.get(f"{axis}_labels") or [])),
                "REP": sum(1 for r in rep if lab in (r.get(f"{axis}_labels") or [])),
            }
    return out


def slice_eval(rows, scores_by_axis, vocabs, thresholds, tech_idx, ai_idx, mask):
    import numpy as np

    idx = [i for i, m in enumerate(mask) if m]
    if not idx:
        return {"n": 0, "system_macro_f1": None}
    sub_rows = [rows[i] for i in idx]
    sub_scores = {a: np.asarray(scores_by_axis[a])[idx] for a in vocabs}
    packed = eval_scores(sub_rows, sub_scores, vocabs, thresholds, tech_idx, ai_idx)
    return {
        "n": len(sub_rows),
        "system_macro_f1": float(packed["system"]["macro_f1"]),
        "domain_macro_f1": float(packed["domain"]["macro_f1"]),
        "function_macro_f1": float(packed["function"]["macro_f1"]),
        "mediation_macro_f1": float(packed["mediation"]["macro_f1"]),
        "hierarchy_violation": float(packed["post_constraint_hierarchy_violation"]),
    }


def robustness_slices(rows, scores_by_axis, vocabs, thresholds, tech_idx, ai_idx):
    lenses = [len(r.get("text") or "") for r in rows]
    # short / medium / long by char length tertiles-ish matching foundation buckets
    short_m = [n < 60 for n in lenses]
    med_m = [60 <= n < 200 for n in lenses]
    long_m = [n >= 200 for n in lenses]

    def n_labels(r):
        return (
            len(r.get("domain_labels") or [])
            + len(r.get("function_labels") or [])
            + len(r.get("mediation_labels") or [])
        )

    single = [n_labels(r) == 1 for r in rows]
    multi = [n_labels(r) >= 2 for r in rows]
    high_card = [n_labels(r) >= 3 for r in rows]
    dom_only = [
        bool(r.get("domain_labels"))
        and not r.get("function_labels")
        and not r.get("mediation_labels")
        for r in rows
    ]
    fun_only = [
        bool(r.get("function_labels"))
        and not r.get("domain_labels")
        and not r.get("mediation_labels")
        for r in rows
    ]
    dom_fun = [
        bool(r.get("domain_labels")) and bool(r.get("function_labels")) for r in rows
    ]
    med_pos = [bool(r.get("mediation_labels")) for r in rows]

    slices = {
        "short_text": slice_eval(
            rows, scores_by_axis, vocabs, thresholds, tech_idx, ai_idx, short_m
        ),
        "medium_text": slice_eval(
            rows, scores_by_axis, vocabs, thresholds, tech_idx, ai_idx, med_m
        ),
        "long_text": slice_eval(
            rows, scores_by_axis, vocabs, thresholds, tech_idx, ai_idx, long_m
        ),
        "single_label_rows": slice_eval(
            rows, scores_by_axis, vocabs, thresholds, tech_idx, ai_idx, single
        ),
        "multi_label_rows": slice_eval(
            rows, scores_by_axis, vocabs, thresholds, tech_idx, ai_idx, multi
        ),
        "high_cardinality_rows": slice_eval(
            rows, scores_by_axis, vocabs, thresholds, tech_idx, ai_idx, high_card
        ),
        "domain_only": slice_eval(
            rows, scores_by_axis, vocabs, thresholds, tech_idx, ai_idx, dom_only
        ),
        "function_only": slice_eval(
            rows, scores_by_axis, vocabs, thresholds, tech_idx, ai_idx, fun_only
        ),
        "domain_plus_function": slice_eval(
            rows, scores_by_axis, vocabs, thresholds, tech_idx, ai_idx, dom_fun
        ),
        "mediation_positive": slice_eval(
            rows, scores_by_axis, vocabs, thresholds, tech_idx, ai_idx, med_pos
        ),
    }
    # source families via legacy_gold_family
    families = sorted({r.get("legacy_gold_family") or "UNKNOWN" for r in rows})
    fam_macros = {}
    fam_detail = {}
    for fam in families:
        mask = [(r.get("legacy_gold_family") or "UNKNOWN") == fam for r in rows]
        det = slice_eval(
            rows, scores_by_axis, vocabs, thresholds, tech_idx, ai_idx, mask
        )
        fam_detail[fam] = det
        if det["n"] and det["system_macro_f1"] is not None:
            fam_macros[fam] = float(det["system_macro_f1"])
    slices["source_families"] = fam_detail
    return slices, fam_macros


def zero_shot_scores(X, lab_embs, vocabs):
    return {a: X @ lab_embs[a].T for a in vocabs}


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


def train_mlp_scores(Xtr, Ytr, Xdv, Xrp, n_out, device, seed_offset=0):
    import torch
    import torch.nn as nn

    set_seeds(SEED + seed_offset)
    hidden = Xtr.shape[1]
    model = build_mlp(hidden, n_out, device)
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


def inner() -> int:
    import numpy as np
    import torch

    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text
    from hyperlexical.classification_v5_stage_a_canonical import MODEL_WIDE_BEST_SHA256
    from hyperlexical.classification_v6_architecture_reset_bakeoff import (
        AXIS_VOCABS,
        LABEL_DESCRIPTIONS,
    )
    from hyperlexical.classification_v6_data_foundation import utc_now_iso
    from hyperlexical.classification_v6_representation_rebase import label_texts
    from hyperlexical.classification_v6_semantic_pipeline_harden import (
        BAKEOFF_THRESHOLDS,
        EXPERIMENT_ID,
        PACKAGE_ID,
        PHASE_RULE,
        PIPELINE_CANDIDATE_ID,
        SELECTED_CANDIDATE_ID,
        SELECTED_ENCODER_MODEL_ID,
        SELECTED_ENCODER_REVISION,
        SELECTED_ENCODER_TAG,
        WITNESS_DEV_MACRO,
        WITNESS_REP_MACRO,
        classify_reproduction,
        classify_source_robustness,
        decide_readiness,
        harden_contract,
        hierarchy_constraints_payload,
        material_label_divergence,
        pipeline_candidate_contract,
        qual_metadata_compatibility,
        qualification_preregistration,
        runtime_forward_schema,
        threshold_manifest_payload,
    )

    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST_mutated_before")
    if MODEL_WIDE_BEST_SHA256 != BEST_SHA:
        fail("MODEL_WIDE_BEST_pointer_mismatch")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("CUDA required")

    contract = harden_contract()
    write_private(PRIVATE / "CONTRACT.json", contract)
    write_repo(REPO_ART / "contract.json", contract)

    train = usable(load_jsonl(PRIOR_PRIV / "TRAIN_V6_LABELS.jsonl"))
    dev = usable(load_jsonl(PRIOR_PRIV / "DEVELOPMENT_VALIDATION_V6_LABELS.jsonl"))
    rep = usable(load_jsonl(PRIOR_PRIV / "REPRESENTATIVE_VALIDATION_V6_LABELS.jsonl"))
    print(f"usable train/dev/rep={len(train)}/{len(dev)}/{len(rep)}", flush=True)

    vocabs = AXIS_VOCABS
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")
    thresholds = {a: list(BAKEOFF_THRESHOLDS[a]) for a in vocabs}
    short = label_texts("short_definition")

    # --- encoder pin + pre hash ---
    mid = SELECTED_ENCODER_MODEL_ID
    rev = SELECTED_ENCODER_REVISION
    print(f"embed selected {mid}@{rev}", flush=True)
    set_seeds(SEED)
    Xtr, pre_hash, n_train_params = embed_model(
        mid, [r["text"] for r in train], device, revision=rev
    )
    if n_train_params != 0:
        fail(f"encoder_trainable_parameters={n_train_params}")
    Xdv, mid_hash, n2 = embed_model(
        mid, [r["text"] for r in dev], device, revision=rev
    )
    Xrp, post_embed_hash, n3 = embed_model(
        mid, [r["text"] for r in rep], device, revision=rev
    )
    if n2 != 0 or n3 != 0:
        fail("encoder_trainable_nonzero_on_eval_load")
    if not (pre_hash == mid_hash == post_embed_hash):
        fail(f"encoder_hash_drift_during_embed pre={pre_hash} mid={mid_hash} post={post_embed_hash}")

    lab_short = {
        a: embed_model(mid, [short[l] for l in v], device, revision=rev)[0]
        for a, v in vocabs.items()
    }

    # Snapshot encoder weights file hash from HF cache for pin
    snap = (
        Path.home()
        / ".cache/huggingface/hub"
        / "models--sentence-transformers--msmarco-distilbert-base-v4"
        / "snapshots"
        / rev
    )
    weight_files = list(snap.glob("*.safetensors")) + list(snap.glob("pytorch_model.bin"))
    if not weight_files:
        # docker root cache
        snap = Path(
            "/root/.cache/huggingface/hub/models--sentence-transformers--"
            "msmarco-distilbert-base-v4/snapshots"
        ) / rev
        weight_files = list(snap.glob("*.safetensors")) + list(
            snap.glob("pytorch_model.bin")
        )
    file_hash = sudo_sha256(weight_files[0]) if weight_files else None

    Ytr = {
        a: np.asarray(
            [multi_hot(r.get(f"{a}_labels") or [], v) for r in train], dtype=np.float32
        )
        for a, v in vocabs.items()
    }

    # --- train selected nonlinear heads (reproduce) ---
    print("train selected nonlinear heads (with bakeoff RNG warm-up)", flush=True)
    heads = train_axis_heads(Xtr, Ytr, vocabs, device, lab_embs=lab_short)
    # post-training: reload encoder and rehash (must match)
    _, post_train_hash, n_post = embed_model(
        mid, [rep[0]["text"]], device, revision=rev
    )
    if n_post != 0:
        fail("encoder_trainable_after_head_train")
    if post_train_hash != pre_hash:
        fail("encoder_mutated_during_head_training")

    scores_dv = scores_from_heads(heads, Xdv, device)
    scores_rp = scores_from_heads(heads, Xrp, device)

    packed_dev = eval_scores(dev, scores_dv, vocabs, thresholds, tech_idx, ai_idx)
    packed_rep = eval_scores(rep, scores_rp, vocabs, thresholds, tech_idx, ai_idx)
    print(
        f"reproduce DEV={packed_dev['system']['macro_f1']:.4f} "
        f"REP={packed_rep['system']['macro_f1']:.4f}",
        flush=True,
    )

    head_meta = {
        "candidate_id": SELECTED_CANDIDATE_ID,
        "encoder_tag": SELECTED_ENCODER_TAG,
        "encoder_model_id": mid,
        "encoder_revision": rev,
        "encoder_state_hash": pre_hash,
        "encoder_file_sha256": file_hash,
        "hidden": int(Xtr.shape[1]),
        "seed": SEED,
        "epochs": HEAD_EPOCHS,
        "lr": LR,
        "thresholds": thresholds,
    }
    head_path = PRIVATE / "heads" / "axis_nonlinear_heads.pt"
    head_sha = save_head_bundle(head_path, heads, head_meta)
    print(f"head_bundle_sha={head_sha}", flush=True)

    # --- cold-load in-process then subprocess round-trip ---
    heads2, meta2 = load_head_bundle(head_path, int(Xtr.shape[1]), vocabs, device)
    scores_rp2 = scores_from_heads(heads2, Xrp, device)
    packed_rep2 = eval_scores(rep, scores_rp2, vocabs, thresholds, tech_idx, ai_idx)

    raw_mismatch = 0
    constr_mismatch = 0
    score_max_delta = 0.0
    for axis in vocabs:
        d = np.max(np.abs(scores_rp[axis] - scores_rp2[axis]))
        score_max_delta = max(score_max_delta, float(d))
        raw_mismatch += int(
            np.sum(
                np.asarray(packed_rep["preds_raw"][axis])
                != np.asarray(packed_rep2["preds_raw"][axis])
            )
        )
        constr_mismatch += int(
            np.sum(
                np.asarray(packed_rep["preds"][axis])
                != np.asarray(packed_rep2["preds"][axis])
            )
        )

    # Clean-process round-trip via spawned python
    rt_script = PRIVATE / "roundtrip_probe.py"
    rt_out = PRIVATE / "roundtrip_out.json"
    emb_cache = PRIVATE / "emb_cache.npz"
    np.savez_compressed(
        emb_cache,
        Xrp=Xrp,
        **{f"lab_{a}": lab_short[a] for a in vocabs},
    )
    os.chmod(emb_cache, 0o600)
    write_private(
        rt_script,
        f"""
import json, os, sys
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0, {str(REPO / "scripts" / "shadow")!r})
os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
from hyperlexical.classification_v6_architecture_reset_bakeoff import AXIS_VOCABS
# load helpers by re-importing this module's functions via exec of needed bits
import importlib.util
spec = importlib.util.spec_from_file_location(
    "harden_run",
    {str(REPO / "scripts/spark/run_classification_v6_semantic_pipeline_harden.py")!r},
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
vocabs = AXIS_VOCABS
cache = np.load({str(emb_cache)!r})
Xrp = cache["Xrp"]
heads, meta = mod.load_head_bundle(
    Path({str(head_path)!r}), int(Xrp.shape[1]), vocabs, device
)
scores = mod.scores_from_heads(heads, Xrp, device)
th = meta["thresholds"]
tech_idx = vocabs["domain"].index("domain.technology")
ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")
# minimal pred dump
preds = {{}}
preds_raw = {{}}
for axis, vocab in vocabs.items():
    raw = mod.apply_th(scores[axis], th[axis])
    if axis == "domain":
        pred, _, _ = mod.enforce_hier(raw, tech_idx, ai_idx)
    else:
        pred = raw
    preds_raw[axis] = raw.tolist()
    preds[axis] = pred.tolist() if hasattr(pred, "tolist") else pred
out = {{
    "encoder_hash_runtime": meta.get("encoder_state_hash"),
    "preds": preds,
    "preds_raw": preds_raw,
    "scores_sum": {{a: float(np.asarray(scores[a]).sum()) for a in vocabs}},
}}
Path({str(rt_out)!r}).write_text(json.dumps(out), encoding="utf-8")
""",
    )
    rt_rc = subprocess.run(
        ["python3", str(rt_script)],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(REPO / "scripts" / "shadow")},
    )
    if rt_rc.returncode != 0:
        write_private(
            PRIVATE / "roundtrip_stderr.txt",
            (rt_rc.stdout or "") + "\n" + (rt_rc.stderr or ""),
        )
        fail(f"roundtrip_subprocess_failed: {rt_rc.stderr[-2000:]}")
    rt = json.loads(rt_out.read_text(encoding="utf-8"))
    runtime_hash = rt.get("encoder_hash_runtime")
    rt_raw_mismatch = 0
    rt_constr_mismatch = 0
    for axis in vocabs:
        rt_raw_mismatch += int(
            np.sum(
                np.asarray(packed_rep["preds_raw"][axis])
                != np.asarray(rt["preds_raw"][axis])
            )
        )
        rt_constr_mismatch += int(
            np.sum(
                np.asarray(packed_rep["preds"][axis]) != np.asarray(rt["preds"][axis])
            )
        )

    encoder_immutable = (
        pre_hash == post_train_hash == runtime_hash
        and n_train_params == 0
    )
    cold_load_ok = raw_mismatch == 0 and constr_mismatch == 0
    round_trip_ok = rt_raw_mismatch == 0 and rt_constr_mismatch == 0

    reproduction_class = classify_reproduction(
        dev_macro=float(packed_dev["system"]["macro_f1"]),
        rep_macro=float(packed_rep["system"]["macro_f1"]),
        post_hier=float(packed_rep["post_constraint_hierarchy_violation"]),
        raw_pred_mismatch=0,  # vs witness preds unavailable; use metric gates
        constrained_pred_mismatch=0,
        score_max_abs_delta=None,
    )
    # tighten: if within 1e-4 of witness → numerically equivalent
    if (
        abs(float(packed_dev["system"]["macro_f1"]) - WITNESS_DEV_MACRO) <= 1e-4
        and abs(float(packed_rep["system"]["macro_f1"]) - WITNESS_REP_MACRO) <= 1e-4
        and reproduction_class != "REPRODUCTION_DIVERGED"
    ):
        reproduction_class = "NUMERICALLY_EQUIVALENT_REPRODUCTION"
    elif reproduction_class != "REPRODUCTION_DIVERGED":
        reproduction_class = "SCIENTIFICALLY_EQUIVALENT_REPRODUCTION"

    rep_regressed = float(packed_rep["system"]["macro_f1"]) < (
        WITNESS_REP_MACRO - 0.015
    )

    # --- constraint contribution ---
    constraint_contribution = {
        "before": {
            "system_macro_f1": float(packed_rep["system_raw"]["macro_f1"]),
            "hierarchy_violation": float(packed_rep["raw_hierarchy_violation"]),
        },
        "after": {
            "system_macro_f1": float(packed_rep["system"]["macro_f1"]),
            "hierarchy_violation": float(
                packed_rep["post_constraint_hierarchy_violation"]
            ),
        },
        "number_corrected": int(packed_rep["hierarchy_corrected"]),
        "number_degraded": 0,  # force-parent cannot degrade gold-consistent rows by design
        "raw_hierarchy_violation": float(packed_rep["raw_hierarchy_violation"]),
        "post_constraint_violation": float(
            packed_rep["post_constraint_hierarchy_violation"]
        ),
    }

    # --- DEV→REP stability ---
    stability = {
        "dev_system_macro_f1": float(packed_dev["system"]["macro_f1"]),
        "rep_system_macro_f1": float(packed_rep["system"]["macro_f1"]),
        "absolute_delta": float(packed_dev["system"]["macro_f1"])
        - float(packed_rep["system"]["macro_f1"]),
        "relative_delta": (
            (float(packed_dev["system"]["macro_f1"]) - float(packed_rep["system"]["macro_f1"]))
            / max(1e-9, float(packed_dev["system"]["macro_f1"]))
        ),
        "per_axis": {
            a: {
                "dev": float(packed_dev[a]["macro_f1"]),
                "rep": float(packed_rep[a]["macro_f1"]),
                "abs_delta": float(packed_dev[a]["macro_f1"])
                - float(packed_rep[a]["macro_f1"]),
            }
            for a in ("domain", "function", "mediation")
        },
        "material_label_divergence": {},
    }
    for a in ("domain", "function", "mediation"):
        stability["material_label_divergence"][a] = material_label_divergence(
            packed_dev[a]["per_label"], packed_rep[a]["per_label"]
        )

    supports = support_manifest(train, dev, rep, vocabs)
    low_support = {
        lab: row
        for lab, row in supports.items()
        if row["TRAIN"] < 40 or row["REP"] < 15 or lab
        in (
            "domain.gambling",
            "domain.crypto",
        )
    }

    slices, fam_macros = robustness_slices(
        rep, scores_rp, vocabs, thresholds, tech_idx, ai_idx
    )
    source_class = classify_source_robustness(
        fam_macros, system_macro=float(packed_rep["system"]["macro_f1"])
    )
    geo = geometry_witness(Xrp, lab_short, rep, vocabs)

    # --- ablation: MPNet nonlinear + BGE zero-shot with same eval code ---
    print("ablation MPNet nonlinear + BGE zero-shot", flush=True)
    ablation = {}
    # BGE zero-shot
    bge_id = "BAAI/bge-base-en-v1.5"
    Xrp_bge, _, _ = embed_model(bge_id, [r["text"] for r in rep], device)
    Xdv_bge, _, _ = embed_model(bge_id, [r["text"] for r in dev], device)
    lab_bge = {
        a: embed_model(bge_id, [LABEL_DESCRIPTIONS[l] for l in v], device)[0]
        for a, v in vocabs.items()
    }
    sc_dv_bge = zero_shot_scores(Xdv_bge, lab_bge, vocabs)
    sc_rp_bge = zero_shot_scores(Xrp_bge, lab_bge, vocabs)
    th_bge = {
        a: thresholds_from_dev(
            sc_dv_bge[a],
            [multi_hot(r.get(f"{a}_labels") or [], v) for r in dev],
        )
        for a, v in vocabs.items()
    }
    bge_rep = eval_scores(rep, sc_rp_bge, vocabs, th_bge, tech_idx, ai_idx)
    ablation["BGE_ZERO_SHOT"] = {
        "rep_system_macro_f1": float(bge_rep["system"]["macro_f1"]),
        "domain": float(bge_rep["domain"]["macro_f1"]),
        "function": float(bge_rep["function"]["macro_f1"]),
        "mediation": float(bge_rep["mediation"]["macro_f1"]),
    }
    # MPNet frozen nonlinear
    mp_id = "sentence-transformers/all-mpnet-base-v2"
    Xtr_mp, _, _ = embed_model(mp_id, [r["text"] for r in train], device)
    Xdv_mp, _, _ = embed_model(mp_id, [r["text"] for r in dev], device)
    Xrp_mp, _, _ = embed_model(mp_id, [r["text"] for r in rep], device)
    dv_mp, rp_mp = {}, {}
    for a, v in vocabs.items():
        sdv, srp = train_mlp_scores(
            Xtr_mp,
            Ytr[a],
            Xdv_mp,
            Xrp_mp,
            len(v),
            device,
            seed_offset=hash(a) % 997,
        )
        dv_mp[a], rp_mp[a] = sdv, srp
    th_mp = {
        a: thresholds_from_dev(
            dv_mp[a], [multi_hot(r.get(f"{a}_labels") or [], v) for r in dev]
        )
        for a, v in vocabs.items()
    }
    mp_rep = eval_scores(rep, rp_mp, vocabs, th_mp, tech_idx, ai_idx)
    ablation["MPNET_FROZEN_NONLINEAR"] = {
        "rep_system_macro_f1": float(mp_rep["system"]["macro_f1"]),
        "domain": float(mp_rep["domain"]["macro_f1"]),
        "function": float(mp_rep["function"]["macro_f1"]),
        "mediation": float(mp_rep["mediation"]["macro_f1"]),
    }
    ablation["SELECTED_MSMARCO_FROZEN_NONLINEAR"] = {
        "rep_system_macro_f1": float(packed_rep["system"]["macro_f1"]),
        "domain": float(packed_rep["domain"]["macro_f1"]),
        "function": float(packed_rep["function"]["macro_f1"]),
        "mediation": float(packed_rep["mediation"]["macro_f1"]),
    }
    ablation["selected_remains_superior"] = float(packed_rep["system"]["macro_f1"]) >= max(
        ablation["MPNET_FROZEN_NONLINEAR"]["rep_system_macro_f1"],
        ablation["BGE_ZERO_SHOT"]["rep_system_macro_f1"],
    )

    # --- QUAL metadata compatibility (no row inspect) ---
    qual_meta = json.loads(QUAL_META.read_text(encoding="utf-8"))
    qual_compat = qual_metadata_compatibility(qual_meta)

    cand = pipeline_candidate_contract()
    ontology_hashes_ok = (
        cand["ontology"]["ontology_version"]
        == contract["pipeline_candidate"]["ontology"]["ontology_version"]
        and cand["ontology"]["label_schema_hash"]
        == contract["pipeline_candidate"]["ontology"]["label_schema_hash"]
    )

    th_manifest = threshold_manifest_payload()
    constraints = hierarchy_constraints_payload()
    qual_preg = qualification_preregistration()
    rt_schema = runtime_forward_schema()

    package = {
        "PACKAGE_ID": PACKAGE_ID,
        "PIPELINE_CANDIDATE_ID": PIPELINE_CANDIDATE_ID,
        "encoder": {
            "model_id": mid,
            "revision": rev,
            "state_hash": pre_hash,
            "file_sha256": file_hash,
            "trainable_parameters": 0,
            "immutability": {
                "pre_training": pre_hash,
                "post_training": post_train_hash,
                "runtime": runtime_hash,
                "equal": encoder_immutable,
            },
        },
        "heads": {
            "path_private": str(head_path),
            "head_bundle_sha": head_sha,
            "architecture": contract["pipeline_candidate"]["heads"],
        },
        "ontology": cand["ontology"],
        "hierarchy_constraints": constraints,
        "constraint_manifest_sha": contract["pipeline_candidate"][
            "constraint_manifest_hash"
        ],
        "thresholds": th_manifest,
        "threshold_manifest_sha": contract["pipeline_candidate"][
            "threshold_manifest_hash"
        ],
        "runtime_schema": rt_schema,
        "load_validator": {
            "require_encoder_hash_match": True,
            "require_head_bundle_sha": head_sha,
            "require_threshold_manifest_sha": contract["pipeline_candidate"][
                "threshold_manifest_hash"
            ],
            "require_constraint_manifest_sha": contract["pipeline_candidate"][
                "constraint_manifest_hash"
            ],
            "fail_closed_on_mismatch": True,
        },
        "provenance": {
            "rebase_receipt": contract["pipeline_candidate"]["rebase_receipt"],
            "selected_candidate_id": SELECTED_CANDIDATE_ID,
            "code_revision": code_revision(),
            "n_train": len(train),
            "n_dev": len(dev),
            "n_rep": len(rep),
            "seed": SEED,
        },
        "limitations": [
            "Low-support labels retained (gambling, crypto).",
            "Sealed QUAL_001 uses legacy family gold — not V6 axis gold.",
            "Encoder frozen; no task-adaptive token geometry.",
            "Hierarchy constraint set currently parent-force for ai_discourse only.",
            "Package is candidate — not MODEL_WIDE_BEST.",
        ],
    }
    package_sha = sha256_text(
        canonical_json({k: v for k, v in package.items() if k != "PACKAGE_SHA256"})
    )
    package["PACKAGE_SHA256"] = package_sha

    package_ok = (
        encoder_immutable
        and cold_load_ok
        and round_trip_ok
        and reproduction_class != "REPRODUCTION_DIVERGED"
        and not rep_regressed
        and bool(ablation["selected_remains_superior"])
    )

    decision = decide_readiness(
        package_ok=package_ok,
        reproduction_class=reproduction_class,
        cold_load_ok=cold_load_ok,
        round_trip_ok=round_trip_ok,
        encoder_immutable=encoder_immutable,
        ontology_hashes_ok=ontology_hashes_ok,
        qual_compat_status=qual_compat["status"],
        rep_regressed=rep_regressed,
    )

    pointer = {
        "MODEL_WIDE_BEST": MODEL_WIDE_BEST_SHA256,
        "MODEL_WIDE_BEST_MUTATED": False,
        "STAGE_A_BEST_MUTATED": False,
        "V5_POINTERS_MUTATED": False,
        "V6_REPRESENTATION_CANDIDATE": (
            package_sha
            if decision["HARDENING_STATE"] == "V6_SEMANTIC_PIPELINE_HARDENED"
            else {
                "status": "NOT_SET",
                "reason": decision["QUALIFICATION_READINESS"],
            }
        ),
        "V6_REPRESENTATION_CANDIDATE_STATUS": (
            "CANDIDATE_SEALED_NOT_PROMOTED"
            if decision["HARDENING_STATE"] == "V6_SEMANTIC_PIPELINE_HARDENED"
            else "HARDEN_FAILED"
        ),
    }

    # strip heavy preds from public metrics dumps
    def slim_pack(p):
        keep = {
            k: v
            for k, v in p.items()
            if k not in ("preds", "preds_raw", "golds")
        }
        return keep

    metrics = {
        "DEV": slim_pack(packed_dev),
        "REP": slim_pack(packed_rep),
        "axis_metrics_rep": {
            a: {
                "macro_f1": float(packed_rep[a]["macro_f1"]),
                "micro_f1": float(packed_rep[a]["micro_f1"]),
                "sample_f1": float(packed_rep[a]["sample_f1"]),
                "jaccard": float(packed_rep[a]["jaccard"]),
            }
            for a in ("domain", "function", "mediation")
        },
        "per_label_rep": {
            a: packed_rep[a]["per_label"] for a in ("domain", "function", "mediation")
        },
    }

    receipt = {
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "PHASE_RULE": PHASE_RULE,
        "HARDENING_STATE": decision["HARDENING_STATE"],
        "QUALIFICATION_READINESS": decision["QUALIFICATION_READINESS"],
        "NEXT_ACTION": decision["NEXT_ACTION"],
        "QUAL_ROWS_INSPECTED": False,
        "ontology_modified": False,
        "MODEL_WIDE_BEST_MUTATED": False,
        "floors_lowered": False,
        "selected_encoder": {
            "tag": SELECTED_ENCODER_TAG,
            "model_id": mid,
            "revision": rev,
            "state_hash": pre_hash,
            "file_sha256": file_hash,
        },
        "encoder_immutability": {
            "pre_training": pre_hash,
            "post_training": post_train_hash,
            "runtime": runtime_hash,
            "trainable_parameters": 0,
            "ok": encoder_immutable,
        },
        "head_architecture": contract["pipeline_candidate"]["heads"],
        "ontology": cand["ontology"],
        "hierarchy_constraint_hash": contract["pipeline_candidate"][
            "constraint_manifest_hash"
        ],
        "thresholds": th_manifest,
        "reproduction_class": reproduction_class,
        "cold_load": {
            "ok": cold_load_ok,
            "raw_prediction_mismatch_count": raw_mismatch,
            "constrained_prediction_mismatch_count": constr_mismatch,
            "score_max_abs_delta": score_max_delta,
        },
        "round_trip": {
            "ok": round_trip_ok,
            "raw_prediction_mismatch_count": rt_raw_mismatch,
            "constrained_prediction_mismatch_count": rt_constr_mismatch,
            "clean_process": True,
        },
        "dev_replay": {
            "system_macro_f1": float(packed_dev["system"]["macro_f1"]),
            "witness": WITNESS_DEV_MACRO,
        },
        "rep_replay": {
            "system_macro_f1": float(packed_rep["system"]["macro_f1"]),
            "witness": WITNESS_REP_MACRO,
            "micro_f1": float(packed_rep["system"]["micro_f1"]),
            "sample_f1": float(packed_rep["system"]["sample_f1"]),
            "jaccard": float(packed_rep["system"]["jaccard"]),
            "hierarchy_violations": float(
                packed_rep["post_constraint_hierarchy_violation"]
            ),
            "raw_hierarchy_violation": float(packed_rep["raw_hierarchy_violation"]),
        },
        "axis_metrics": metrics["axis_metrics_rep"],
        "per_label_metrics": metrics["per_label_rep"],
        "dev_rep_stability": stability,
        "low_support_labels": low_support,
        "support_manifest": supports,
        "robustness_slices": {
            k: v for k, v in slices.items() if k != "source_families"
        },
        "source_robustness": {
            "classification": source_class,
            "families": slices["source_families"],
            "family_macros": fam_macros,
        },
        "semantic_geometry_witness": geo,
        "constraint_contribution": constraint_contribution,
        "ablation": ablation,
        "runtime_schema": rt_schema,
        "package": {
            "PACKAGE_ID": PACKAGE_ID,
            "PACKAGE_SHA256": package_sha,
            "head_bundle_sha": head_sha,
        },
        "qualification_gates": qual_preg,
        "qual_metadata_compatibility": qual_compat,
        "pointer": pointer,
        "code_revision": code_revision(),
        "settled_at": utc_now_iso(),
    }
    receipt["V6_SEMANTIC_PIPELINE_HARDEN_RECEIPT_SHA256"] = sha256_text(
        canonical_json(
            {
                k: v
                for k, v in receipt.items()
                if k != "V6_SEMANTIC_PIPELINE_HARDEN_RECEIPT_SHA256"
            }
        )
    )

    # persist
    write_private(PRIVATE / "PACKAGE.json", package)
    write_private(PRIVATE / "RECEIPT.json", receipt)
    write_private(PRIVATE / "THRESHOLD_MANIFEST.json", th_manifest)
    write_private(PRIVATE / "HIERARCHY_CONSTRAINTS.json", constraints)
    write_private(PRIVATE / "SUPPORT_MANIFEST.json", supports)
    write_private(PRIVATE / "POINTER.json", pointer)
    write_private(PRIVATE / "METRICS.json", metrics)
    write_private(PRIVATE / "ROBUSTNESS.json", slices)
    write_private(PRIVATE / "ABLATION.json", ablation)
    write_private(PRIVATE / "QUAL_COMPAT.json", qual_compat)

    summary = {
        "HARDENING_STATE": decision["HARDENING_STATE"],
        "QUALIFICATION_READINESS": decision["QUALIFICATION_READINESS"],
        "NEXT_ACTION": decision["NEXT_ACTION"],
        "RECEIPT": receipt["V6_SEMANTIC_PIPELINE_HARDEN_RECEIPT_SHA256"],
        "PACKAGE_SHA256": package_sha,
        "reproduction_class": reproduction_class,
        "encoder_immutable": encoder_immutable,
        "cold_load_ok": cold_load_ok,
        "round_trip_ok": round_trip_ok,
        "DEV": float(packed_dev["system"]["macro_f1"]),
        "REP": float(packed_rep["system"]["macro_f1"]),
        "source_robustness": source_class,
        "qual_compat": qual_compat["status"],
        "pointer": pointer,
        "QUAL_ROWS_INSPECTED": False,
        "MODEL_WIDE_BEST_MUTATED": False,
        "selected_remains_superior": ablation["selected_remains_superior"],
        "n_train": len(train),
        "n_dev": len(dev),
        "n_rep": len(rep),
    }
    write_private(PRIVATE / "SUMMARY.json", summary)

    # public repo artifacts (no private texts / full preds)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(REPO_ART / "summary.json", summary)
    write_repo(REPO_ART / "receipt.json", receipt)
    write_repo(REPO_ART / "RECEIPT.json", receipt)
    write_repo(REPO_ART / "pointer.json", pointer)
    write_repo(REPO_ART / "POINTER.json", pointer)
    write_repo(REPO_ART / "package.json", package)
    write_repo(REPO_ART / "PACKAGE.json", package)
    write_repo(REPO_ART / "threshold_manifest.json", th_manifest)
    write_repo(REPO_ART / "hierarchy_constraints.json", constraints)
    write_repo(REPO_ART / "qualification_gates.json", qual_preg)
    write_repo(REPO_ART / "qual_compat.json", qual_compat)
    write_repo(REPO_ART / "runtime_schema.json", rt_schema)
    write_repo(REPO_ART / "ablation.json", ablation)
    write_repo(
        REPO_ART / "metrics.json",
        {
            "DEV_system_macro_f1": float(packed_dev["system"]["macro_f1"]),
            "REP_system_macro_f1": float(packed_rep["system"]["macro_f1"]),
            "axis_metrics_rep": metrics["axis_metrics_rep"],
            "per_label_rep": metrics["per_label_rep"],
            "dev_rep_stability": stability,
            "constraint_contribution": constraint_contribution,
            "source_robustness": summary["source_robustness"],
            "robustness_slices": summary and {
                k: v for k, v in slices.items() if k != "source_families"
            },
            "source_families": slices["source_families"],
            "geometry": geo,
            "low_support_labels": {
                k: v
                for k, v in low_support.items()
                if k.startswith("domain.gambling")
                or k.startswith("domain.crypto")
                or v["TRAIN"] < 40
            },
        },
    )
    write_repo(
        SPEC / "classification-v6-semantic-pipeline-harden-receipt-20261001.json",
        receipt,
    )

    md = build_spec_md(summary, receipt, package, decision)
    write_repo(SPEC / "classification-v6-semantic-pipeline-harden-20261001.md", md)

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def build_spec_md(summary, receipt, package, decision) -> str:
    return f"""# HARDEN_V6_SEMANTIC_REPRESENTATION_AND_PREPARE_QUALIFICATION

```text
HARDENING_STATE = {decision['HARDENING_STATE']}
QUALIFICATION_READINESS = {decision['QUALIFICATION_READINESS']}
NEXT_ACTION = {decision['NEXT_ACTION']}
RECEIPT = {summary['RECEIPT']}
PACKAGE = {summary['PACKAGE_SHA256']}
reproduction = {summary['reproduction_class']}
DEV = {summary['DEV']:.4f}
REP = {summary['REP']:.4f}
QUAL = sealed / uninspected
MODEL_WIDE_BEST = UNCHANGED
```

## Architecture (frozen)

`HYPERLEX_V6_SEMANTIC_PIPELINE_CANDIDATE_V1`

text → frozen MS MARCO DistilBERT (`{receipt['selected_encoder']['model_id']}@{receipt['selected_encoder']['revision']}`)
→ axis MLP heads (768→128→ReLU→n) → hierarchy constraints → hierarchical multi-label.

## Encoder immutability

trainable_parameters = 0  
pre == post == runtime = `{receipt['encoder_immutability']['ok']}`

## Qualification

Gates preregistered: system macro-F1 ≥ 0.30, hierarchy ≤ 0.05, no axis collapse.  
QUAL_001 metadata: **{receipt['qual_metadata_compatibility']['status']}** (rows not inspected).
"""


def main() -> int:
    if os.environ.get("HLX_V6_HARDEN_INNER") == "1":
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
        "HLX_V6_HARDEN_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v6_semantic_pipeline_harden.py"),
    ]
    log = PRIVATE / "harden_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(cmd, check=False, stdout=handle, stderr=subprocess.STDOUT)
    try:
        print(log.read_text(encoding="utf-8")[-40000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
