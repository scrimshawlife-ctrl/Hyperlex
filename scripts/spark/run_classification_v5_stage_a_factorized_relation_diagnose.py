"""DIAGNOSE_STAGE_A_FACTORIZED_RELATION_SETTLED_FAIL — Spark runner.

Read-only SHORT_ATOM geometry / layer / pooling / identifiability diagnosis.
Does not train, relabel, create surfaces, retune, use spent reserve, or move BEST.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-generalization-surface-v1r1-20261001"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "4095036e5af3ad7cfe9f038dd3e1f46e4ef0ea18db4c4b7186fc2b02e96d4274"
ANNOTATIONS = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-factorized-objective-v1-20261001/"
    "FACTORIZED_ANNOTATIONS.jsonl"
)
ANNOTATION_SHA = (
    "4ac884504e4b2fe27e0e5de159847a158c43e2c0d75832ddc5b5c657279778b6"
)
FACTORIZED_AUTH = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-factorized-relation-train-v1-20261001"
)
FACTORIZED_CKPT = (
    FACTORIZED_AUTH
    / "classification-v5-stage-a-factorized-relation-001"
    / "selected"
    / "model.safetensors"
)
FACTORIZED_CKPT_SHA = (
    "8a6981c1f742f127d397770462c345ddcce922895add2f4f52828c49d816d9cd"
)
TWO_STAGE_AUTH = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-two-stage-generalization-train-v1-20261001"
)
TWO_STAGE_CKPT = (
    TWO_STAGE_AUTH
    / "classification-v5-stage-a-two-stage-generalization-001"
    / "selected"
    / "model.safetensors"
)
TWO_STAGE_CKPT_SHA = (
    "26841d5f3a8b9cd4237f79203b80697f2da186e7d4b30ab6c08d528adba56e76"
)
STAGE_A_BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/STAGE_A_BEST/model.safetensors"
)
STAGE_A_BEST_SHA = "cd2829c1b5fb823fc03f18efe66a7387124ef44be2545b9e385a17eb6237bf5c"
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
PRIVATE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-factorized-relation-diagnose-20261001"
)
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
REPO_ARTIFACTS = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-001"
)
SPEC_DIR = REPO / "specs" / "007-hyperlexical-model"

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sudo_sha256(path: Path) -> str:
    try:
        return sha256_file(path)
    except PermissionError:
        completed = subprocess.run(
            ["sudo", "-n", "sha256sum", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.split()[0]


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def write_private(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    os.chmod(path, 0o600)


def write_repo(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def balanced_accuracy(y_true: list[int], y_pred: list[int]) -> float:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    tpr = tp / (tp + fn) if (tp + fn) else 0.0
    tnr = tn / (tn + fp) if (tn + fp) else 0.0
    return 0.5 * (tpr + tnr)


def recall_for(y_true: list[int], y_pred: list[int], label: int) -> float:
    denom = sum(1 for t in y_true if t == label)
    if denom == 0:
        return 0.0
    return sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label) / denom


def fit_logistic(x_train, y_train, x_val, seed: int = 42):
    """Deterministic LBFGS logistic probe (torch; no sklearn)."""
    import torch
    from torch import nn

    torch.manual_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    x_tr = torch.tensor(x_train, dtype=torch.float32, device=device)
    x_va = torch.tensor(x_val, dtype=torch.float32, device=device)
    y_tr = torch.tensor(y_train, dtype=torch.float32, device=device)
    # Class-balanced BCE weights
    n_pos = max(1.0, float(y_tr.sum().item()))
    n_neg = max(1.0, float(len(y_train) - n_pos))
    pos_weight = torch.tensor([n_neg / n_pos], device=device)
    logistic = nn.Linear(x_tr.shape[1], 1).to(device)
    nn.init.zeros_(logistic.weight)
    nn.init.zeros_(logistic.bias)
    opt = torch.optim.LBFGS(
        logistic.parameters(), max_iter=80, line_search_fn="strong_wolfe"
    )

    def closure():
        opt.zero_grad()
        logits = logistic(x_tr).squeeze(-1)
        loss = nn.functional.binary_cross_entropy_with_logits(
            logits, y_tr, pos_weight=pos_weight
        )
        loss.backward()
        return loss

    opt.step(closure)
    with torch.no_grad():
        proba = torch.sigmoid(logistic(x_va).squeeze(-1)).cpu().tolist()
        pred = [1 if p >= 0.5 else 0 for p in proba]
    return pred, proba


def fit_mlp(x_train, y_train, x_val, seed: int = 42):
    """Deterministic small MLP probe (torch; diagnostic only)."""
    import torch
    from torch import nn

    torch.manual_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    x_tr = torch.tensor(x_train, dtype=torch.float32, device=device)
    x_va = torch.tensor(x_val, dtype=torch.float32, device=device)
    y_tr = torch.tensor(y_train, dtype=torch.float32, device=device)
    n_pos = max(1.0, float(y_tr.sum().item()))
    n_neg = max(1.0, float(len(y_train) - n_pos))
    pos_weight = torch.tensor([n_neg / n_pos], device=device)
    mlp = nn.Sequential(
        nn.Linear(x_tr.shape[1], 64),
        nn.ReLU(),
        nn.Linear(64, 1),
    ).to(device)
    nn.init.xavier_uniform_(mlp[0].weight)
    nn.init.zeros_(mlp[0].bias)
    nn.init.xavier_uniform_(mlp[2].weight)
    nn.init.zeros_(mlp[2].bias)
    opt = torch.optim.AdamW(mlp.parameters(), lr=1e-3, weight_decay=0.01)
    mlp.train()
    for _ in range(120):
        opt.zero_grad()
        logits = mlp(x_tr).squeeze(-1)
        loss = nn.functional.binary_cross_entropy_with_logits(
            logits, y_tr, pos_weight=pos_weight
        )
        loss.backward()
        opt.step()
    mlp.eval()
    with torch.no_grad():
        proba = torch.sigmoid(mlp(x_va).squeeze(-1)).cpu().tolist()
        pred = [1 if p >= 0.5 else 0 for p in proba]
    return pred


def geometry_report(embeds: list[list[float]], labels: list[int]) -> dict[str, Any]:
    from hyperlexical.classification_v5_stage_a_generalization_retrain_diagnose import (
        centroid,
        cosine,
    )

    none_e = [e for e, y in zip(embeds, labels) if y == 0]
    pos_e = [e for e, y in zip(embeds, labels) if y == 1]
    if not none_e or not pos_e:
        return {"centroid_cosine": None}
    c0 = centroid(none_e)
    c1 = centroid(pos_e)
    cos = cosine(c0, c1)

    def nearest_stats(query_set, same_set, opp_set):
        same_sims = []
        opp_sims = []
        margins = []
        for q in query_set:
            same = sorted((cosine(q, o) for o in same_set if o is not q), reverse=True)
            opp = sorted((cosine(q, o) for o in opp_set), reverse=True)
            s = same[0] if same else 0.0
            o = opp[0] if opp else 0.0
            same_sims.append(s)
            opp_sims.append(o)
            margins.append(s - o)
        return {
            "nearest_same_mean": sum(same_sims) / len(same_sims) if same_sims else None,
            "nearest_opposite_mean": sum(opp_sims) / len(opp_sims) if opp_sims else None,
            "margin_mean": sum(margins) / len(margins) if margins else None,
        }

    n_stats = nearest_stats(none_e, none_e, pos_e)
    p_stats = nearest_stats(pos_e, pos_e, none_e)
    return {
        "centroid_cosine": cos,
        "NONE": n_stats,
        "PRESENT": p_stats,
        "n_none": len(none_e),
        "n_present": len(pos_e),
    }


def mean_cos_disp(a: list[list[float]], b: list[list[float]]) -> dict[str, float]:
    from hyperlexical.classification_v5_stage_a_generalization_retrain_diagnose import (
        cosine,
    )

    vals = [1.0 - cosine(x, y) for x, y in zip(a, b)]
    if not vals:
        return {"mean": 0.0, "median": 0.0}
    vals_s = sorted(vals)
    m = len(vals_s) // 2
    med = vals_s[m] if len(vals_s) % 2 else 0.5 * (vals_s[m - 1] + vals_s[m])
    return {"mean": sum(vals) / len(vals), "median": med}


def ensure_readable(path: Path, expected_sha: str) -> Path:
    """Return a path loadable by the current process (copy via sudo if needed)."""
    if sudo_sha256(path) != expected_sha:
        fail(f"sha_mismatch:{path}:{expected_sha[:16]}")
    try:
        with path.open("rb") as handle:
            handle.read(1)
        return path
    except PermissionError:
        staging = PRIVATE / "readable_ckpts"
        staging.mkdir(mode=0o700, parents=True, exist_ok=True)
        dest = staging / f"{expected_sha[:16]}_{path.name}"
        if not dest.is_file() or sha256_file(dest) != expected_sha:
            subprocess.run(
                ["sudo", "-n", "cp", "-f", str(path), str(dest)],
                check=True,
            )
            subprocess.run(["sudo", "-n", "chmod", "644", str(dest)], check=True)
            subprocess.run(
                ["sudo", "-n", "chown", f"{os.getuid()}:{os.getgid()}", str(dest)],
                check=True,
            )
        if sha256_file(dest) != expected_sha:
            fail(f"staged_sha_mismatch:{dest}")
        return dest


def pin_inputs() -> dict[str, Path]:
    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset_sha_mismatch")
    paths = {
        "factorized": ensure_readable(FACTORIZED_CKPT, FACTORIZED_CKPT_SHA),
        "two_stage": ensure_readable(TWO_STAGE_CKPT, TWO_STAGE_CKPT_SHA),
        "stage_a_best": ensure_readable(STAGE_A_BEST_WEIGHTS, STAGE_A_BEST_SHA),
        "best": ensure_readable(BEST_WEIGHTS, BEST_SHA),
    }
    return paths


def inner() -> int:
    import numpy as np
    import torch
    import torch.nn.functional as F
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import load_file

    from hyperlexical.classification_v2_surface import word_count
    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text
    from hyperlexical.classification_v5_stage_a_factorized_relation_diagnose import (
        DIAGNOSE_RULE,
        FROZEN_OBSERVED_OUTCOME,
        assemble_diagnosis_receipt,
        classify_adaptation_depth,
        classify_layer_finding,
        classify_pooling,
        classify_token_signal,
        context_sufficiency_class,
        irreducible_overlap_test,
        matched_pair_identifiability,
        normalize_text,
    )
    from hyperlexical.classification_v5_stage_a_generalization_retrain_diagnose import (
        centroid,
        cosine,
        semantic_core_class,
        simple_tokens,
    )
    from hyperlexical.classification_v5_stage_a_two_stage import (
        gate1_probabilities,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    if PRIVATE.exists() and (PRIVATE / "DIAGNOSIS.json").exists():
        fail(f"output_already_exists:{PRIVATE}")
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    ckpt_paths = pin_inputs()

    rows = load_jsonl(DATASET)
    train_rows = [r for r in rows if r.get("split") == "train"]
    val_rows = [r for r in rows if r.get("split") == "validation"]
    if len(train_rows) != 2531 or len(val_rows) != 1054:
        fail("split_counts_mismatch")

    ann_by_id = {}
    if ANNOTATIONS.is_file():
        for a in load_jsonl(ANNOTATIONS):
            ann_by_id[str(a["identity"])] = a

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("diagnose_requires_cuda")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    best_readable = ckpt_paths["best"]

    def load_encoder_from_ckpt(path: Path | None, *, kind: str):
        """kind: best_encoder | two_stage | factorized"""
        encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
        warm = split_weight_tensors(load_file(str(best_readable), device="cpu"))
        apply_encoder_trainable(encoder, warm.get("encoder") or {})
        head = None
        if path is not None:
            split = split_weight_tensors(load_file(str(path), device="cpu"))
            loaded = apply_encoder_trainable(encoder, split.get("encoder") or {})
            if loaded["loaded"] < 12:
                fail(f"encoder_overlay_incomplete:{path}:{loaded['loaded']}")
            if kind == "two_stage":
                head = nn.Linear(HIDDEN, 2)
                with torch.no_grad():
                    head.weight.copy_(split["gate1_head"]["weight"])
                    head.bias.copy_(split["gate1_head"]["bias"])
            elif kind == "factorized":
                head = nn.Linear(HIDDEN, 2)
                with torch.no_grad():
                    head.weight.copy_(split["relation_head"]["weight"])
                    head.bias.copy_(split["relation_head"]["bias"])
        freeze_encoder(encoder, last_trainable=2)
        encoder.to(device).eval()
        if head is not None:
            head.to(device).eval()
        return encoder, head

    models = {
        "MODEL_WIDE_BEST": load_encoder_from_ckpt(None, kind="best_encoder"),
        "STAGE_A_BEST": load_encoder_from_ckpt(
            ckpt_paths["stage_a_best"], kind="two_stage"
        ),
        "TWO_STAGE_FAILED_26841d5f": load_encoder_from_ckpt(
            ckpt_paths["two_stage"], kind="two_stage"
        ),
        "FACTORIZED_FAILED_8a6981c1": load_encoder_from_ckpt(
            ckpt_paths["factorized"], kind="factorized"
        ),
    }

    def encode_rows(encoder, split_rows, *, return_hidden_states=False, pooling="cls"):
        embeds = []
        token_embeds = []
        all_hidden = None
        with torch.no_grad():
            for row in split_rows:
                encoded = tokenizer(
                    [str(row["text"])],
                    padding=True,
                    truncation=True,
                    max_length=int(MAX_LEN),
                    return_tensors="pt",
                )
                encoded = {k: v.to(device) for k, v in encoded.items()}
                out = encoder(
                    **encoded,
                    output_hidden_states=return_hidden_states,
                )
                hs = out.last_hidden_state  # [1,T,H]
                attn = encoded["attention_mask"][0].bool()
                if pooling == "cls":
                    pooled = hs[:, 0]
                elif pooling == "mean":
                    mask = attn.unsqueeze(-1).float()
                    pooled = (hs * mask).sum(1) / mask.sum(1).clamp(min=1.0)
                elif pooling == "max":
                    masked = hs.masked_fill(~attn.unsqueeze(-1), -1e9)
                    pooled = masked.max(1).values
                elif pooling == "first_content":
                    # first non-special content token ≈ index 1 for ModernBERT/BERT
                    idx = 1 if hs.size(1) > 1 else 0
                    pooled = hs[:, idx]
                else:
                    fail(f"unknown_pooling:{pooling}")
                emb = F.normalize(pooled, dim=-1)[0]
                embeds.append(emb.detach().cpu().tolist())
                # content-token mean for token audit
                if hs.size(1) > 2:
                    content = hs[0, 1:-1]
                    content_mask = attn[1:-1]
                    if content_mask.any():
                        tok = F.normalize(
                            content[content_mask].mean(0, keepdim=True), dim=-1
                        )[0]
                    else:
                        tok = emb
                else:
                    tok = emb
                token_embeds.append(tok.detach().cpu().tolist())
                if return_hidden_states:
                    layers = out.hidden_states  # tuple len n_layers+1
                    if all_hidden is None:
                        all_hidden = [[] for _ in range(len(layers))]
                    for li, layer_h in enumerate(layers):
                        # CLS at each layer
                        v = F.normalize(layer_h[:, 0], dim=-1)[0]
                        all_hidden[li].append(v.detach().cpu().tolist())
        return embeds, token_embeds, all_hidden

    def short_atom_subset(split_rows):
        return [
            r
            for r in split_rows
            if str(r.get("primary_cell") or "").startswith("SHORT_ATOM/")
        ]

    def relation_labels(split_rows):
        # 1=PRESENT, 0=NONE; drop UNCERTAIN for binary SHORT_ATOM geometry
        labs = []
        keep = []
        for r in split_rows:
            lab = str(r["evidence_label"])
            if lab == "EVIDENCE_PRESENT":
                labs.append(1)
                keep.append(r)
            elif lab == "NO_EVIDENCE":
                labs.append(0)
                keep.append(r)
        return keep, labs

    sa_train_all = short_atom_subset(train_rows)
    sa_val_all = short_atom_subset(val_rows)
    sa_train, y_train = relation_labels(sa_train_all)
    sa_val, y_val = relation_labels(sa_val_all)

    cross = {}
    embeds_by_model = {}
    for name, (enc, head) in models.items():
        emb_tr, _, _ = encode_rows(enc, sa_train, pooling="cls")
        emb_va, tok_va, _ = encode_rows(enc, sa_val, pooling="cls")
        embeds_by_model[name] = {
            "train": emb_tr,
            "val": emb_va,
            "val_token": tok_va,
            "head": head,
        }
        geom = geometry_report(emb_va, y_val)
        pred, _ = fit_logistic(emb_tr, y_train, emb_va, seed=42)
        nl_pred = fit_mlp(emb_tr, y_train, emb_va, seed=42)
        # Native head scores if present
        native_fpr = None
        native_rec = None
        if head is not None:
            scores = []
            with torch.no_grad():
                for row in sa_val:
                    encoded = tokenizer(
                        [str(row["text"])],
                        padding=True,
                        truncation=True,
                        max_length=int(MAX_LEN),
                        return_tensors="pt",
                    )
                    encoded = {k: v.to(device) for k, v in encoded.items()}
                    pooled = enc(**encoded).last_hidden_state[:, 0]
                    logits = head(pooled)[0].detach().cpu().tolist()
                    if name.startswith("FACTORIZED"):
                        probs = F.softmax(torch.tensor(logits), dim=-1).tolist()
                        scores.append(float(probs[1]))
                    else:
                        g1 = gate1_probabilities(logits)
                        scores.append(float(g1["POSSIBLE_EVIDENCE"]))
            native_pred = [1 if s >= 0.50 else 0 for s in scores]
            native_fpr = 1.0 - recall_for(y_val, native_pred, 0)
            native_rec = recall_for(y_val, native_pred, 1)
        cross[name] = {
            "geometry": geom,
            "linear_probe_BA": balanced_accuracy(y_val, pred),
            "nonlinear_probe_BA": balanced_accuracy(y_val, nl_pred),
            "linear_NONE_recall": recall_for(y_val, pred, 0),
            "linear_PRESENT_recall": recall_for(y_val, pred, 1),
            "NONE_FPR_native": native_fpr,
            "PRESENT_recall_native": native_rec,
            "NONE_FPR_linear": 1.0 - recall_for(y_val, pred, 0),
            "PRESENT_recall_linear": recall_for(y_val, pred, 1),
        }

    # Displacement on SHORT_ATOM val identities (aligned)
    parent = embeds_by_model["MODEL_WIDE_BEST"]["val"]
    two = embeds_by_model["TWO_STAGE_FAILED_26841d5f"]["val"]
    fac = embeds_by_model["FACTORIZED_FAILED_8a6981c1"]["val"]
    by_label_disp = {}
    for lab_name, lab_id in [("NONE", 0), ("PRESENT", 1)]:
        idx = [i for i, y in enumerate(y_val) if y == lab_id]
        by_label_disp[lab_name] = {
            "MODEL_WIDE_BEST->26841d5f": mean_cos_disp(
                [parent[i] for i in idx], [two[i] for i in idx]
            ),
            "MODEL_WIDE_BEST->8a6981c1": mean_cos_disp(
                [parent[i] for i in idx], [fac[i] for i in idx]
            ),
            "26841d5f->8a6981c1": mean_cos_disp(
                [two[i] for i in idx], [fac[i] for i in idx]
            ),
        }
    # UNCERTAIN separately
    sa_unc = [r for r in sa_val_all if r["evidence_label"] == "UNCERTAIN"]
    unc_disp = {}
    if sa_unc:
        p_u, _, _ = encode_rows(models["MODEL_WIDE_BEST"][0], sa_unc)
        t_u, _, _ = encode_rows(models["TWO_STAGE_FAILED_26841d5f"][0], sa_unc)
        f_u, _, _ = encode_rows(models["FACTORIZED_FAILED_8a6981c1"][0], sa_unc)
        unc_disp = {
            "MODEL_WIDE_BEST->26841d5f": mean_cos_disp(p_u, t_u),
            "MODEL_WIDE_BEST->8a6981c1": mean_cos_disp(p_u, f_u),
            "26841d5f->8a6981c1": mean_cos_disp(t_u, f_u),
            "n": len(sa_unc),
        }
    # Separation change: centroid cosine parent vs factorized
    parent_cos = cross["MODEL_WIDE_BEST"]["geometry"]["centroid_cosine"]
    fac_cos = cross["FACTORIZED_FAILED_8a6981c1"]["geometry"]["centroid_cosine"]
    two_cos = cross["TWO_STAGE_FAILED_26841d5f"]["geometry"]["centroid_cosine"]
    mean_disp = by_label_disp["NONE"]["MODEL_WIDE_BEST->8a6981c1"]["mean"]
    if mean_disp < 0.02 and abs((fac_cos or 0) - (parent_cos or 0)) < 0.01:
        displacement_class = "mostly_preserved_parent_geometry"
    elif (fac_cos or 1) > 0.95 and (parent_cos or 1) > 0.95:
        displacement_class = "reshaped_but_not_label_separating"
    else:
        displacement_class = "meaningfully_reshaped_SHORT_ATOM_geometry"

    # Layer-wise on factorized encoder (and parent for reference)
    fac_enc = models["FACTORIZED_FAILED_8a6981c1"][0]
    _, _, train_layers = encode_rows(
        fac_enc, sa_train, return_hidden_states=True, pooling="cls"
    )
    _, _, val_layers = encode_rows(
        fac_enc, sa_val, return_hidden_states=True, pooling="cls"
    )
    layer_table = []
    best_ba = -1.0
    best_layer = 0
    for li, (tr, va) in enumerate(zip(train_layers, val_layers)):
        pred, _ = fit_logistic(tr, y_train, va, seed=42)
        ba = balanced_accuracy(y_val, pred)
        geom = geometry_report(va, y_val)
        row = {
            "layer": li,
            "SHORT_ATOM_BA": ba,
            "NONE_recall": recall_for(y_val, pred, 0),
            "PRESENT_recall": recall_for(y_val, pred, 1),
            "centroid_cosine": geom["centroid_cosine"],
            "nearest_opposite_margin_NONE": geom["NONE"]["margin_mean"],
            "nearest_opposite_margin_PRESENT": geom["PRESENT"]["margin_mean"],
        }
        layer_table.append(row)
        if ba > best_ba:
            best_ba = ba
            best_layer = li
    last_layer = len(layer_table) - 1
    last_ba = layer_table[last_layer]["SHORT_ATOM_BA"]
    any_separates = best_ba >= 0.70
    layer_finding = classify_layer_finding(
        best_layer=best_layer,
        last_layer=last_layer,
        best_ba=best_ba,
        last_ba=last_ba,
        any_separates=any_separates,
    )
    adapt_depth = classify_adaptation_depth(
        layer_finding=layer_finding,
        best_layer=best_layer,
        n_layers=last_layer + 1,  # includes embedding layer 0
        last_trainable=2,
    )
    # For transformers, hidden_states[0]=embeddings, [1]=layer0, ...
    # Trainable last-2 encoder layers correspond to last two transformer blocks
    # ≈ hidden indices [n-2, n-1] if n = len(hidden_states)-1 transformer layers...
    # Use transformer-layer index = li-1 for li>=1; treat best among last 2 blocks.
    n_transformer = last_layer  # if last is final layer output index
    # Recompute adapt with transformer indexing: last two = [n_transformer-1, n_transformer]
    # best_layer is hidden_states index.
    if layer_finding != "NO_LAYER_SEPARATES" and best_layer < max(1, last_layer - 1):
        # earlier than last-two hidden outputs
        if best_layer <= last_layer - 2:
            adapt_depth = "DEEPER_ADAPTATION_JUSTIFIED"
        else:
            adapt_depth = "LAST_TWO_SUFFICIENT"
    if layer_finding == "NO_LAYER_SEPARATES":
        adapt_depth = "DEEPER_ADAPTATION_NOT_SUPPORTED"

    # Pooling audit on factorized encoder
    pooling_results = {}
    for pool in ("cls", "mean", "max", "first_content"):
        tr, _, _ = encode_rows(fac_enc, sa_train, pooling=pool)
        va, _, _ = encode_rows(fac_enc, sa_val, pooling=pool)
        pred, _ = fit_logistic(tr, y_train, va, seed=42)
        pooling_results[pool] = {
            "SHORT_ATOM_BA": balanced_accuracy(y_val, pred),
            "NONE_recall": recall_for(y_val, pred, 0),
            "PRESENT_recall": recall_for(y_val, pred, 1),
            "overall_relation_BA": balanced_accuracy(y_val, pred),
        }
    cls_ba = pooling_results["cls"]["SHORT_ATOM_BA"]
    best_alt_name = max(
        (k for k in pooling_results if k != "cls"),
        key=lambda k: pooling_results[k]["SHORT_ATOM_BA"],
    )
    best_alt_ba = pooling_results[best_alt_name]["SHORT_ATOM_BA"]
    pooling_finding = classify_pooling(
        cls_ba=cls_ba, best_alt_ba=best_alt_ba, best_alt_name=best_alt_name
    )

    # Token-level vs CLS on factorized
    emb_tr_cls, tok_train, _ = encode_rows(fac_enc, sa_train, pooling="cls")
    emb_va_cls, tok_val, _ = encode_rows(fac_enc, sa_val, pooling="cls")
    tok_pred, _ = fit_logistic(tok_train, y_train, tok_val, seed=42)
    cls_pred, _ = fit_logistic(emb_tr_cls, y_train, emb_va_cls, seed=42)
    tok_ba = balanced_accuracy(y_val, tok_pred)
    cls_ba2 = balanced_accuracy(y_val, cls_pred)
    tok_geom = geometry_report(tok_val, y_val)
    cls_geom = geometry_report(emb_va_cls, y_val)
    token_finding = classify_token_signal(
        token_ba=tok_ba,
        cls_ba=cls_ba2,
        token_margin=float(tok_geom["NONE"]["margin_mean"] or 0),
        cls_margin=float(cls_geom["NONE"]["margin_mean"] or 0),
    )

    # Context sufficiency / collisions / identifiability
    ctx_counts = Counter()
    ctx_by_label = defaultdict(Counter)
    id_counts = Counter()
    # Matched-pair: also flag SEMANTICALLY_EQUIVALENT when opposite-label
    # partners share normalized text or identical token multiset.
    pair_groups: dict[str, list[dict]] = defaultdict(list)
    for r in sa_val_all:
        pg = str(r.get("pair_group_id") or "")
        if pg:
            pair_groups[pg].append(r)
    equivalent_ids: set[str] = set()
    for members in pair_groups.values():
        labs = {str(m["evidence_label"]) for m in members}
        if "EVIDENCE_PRESENT" in labs and "NO_EVIDENCE" in labs:
            texts = {normalize_text(m["text"]) for m in members}
            toksets = {tuple(sorted(simple_tokens(str(m["text"])))) for m in members}
            if len(texts) == 1 or len(toksets) == 1:
                for m in members:
                    equivalent_ids.add(str(m["identity"]))

    for r in sa_val_all:
        c = context_sufficiency_class(r)
        ctx_counts[c] += 1
        ctx_by_label[c][str(r["evidence_label"])] += 1
        if str(r["identity"]) in equivalent_ids:
            id_counts["SEMANTICALLY_EQUIVALENT_TEXT_DIFFERENT_GOLD"] += 1
        else:
            id_counts[matched_pair_identifiability(r)] += 1
    # also train for collision search on full V1R1
    text_to_labels = defaultdict(set)
    text_to_rows = defaultdict(list)
    for r in rows:
        nt = normalize_text(r["text"])
        text_to_labels[nt].add(str(r["evidence_label"]))
        text_to_rows[nt].append(r)
    exact_cross = [
        t
        for t, labs in text_to_labels.items()
        if len(labs) > 1 and not labs <= {"UNCERTAIN"}
    ]
    # relation-label collisions: PRESENT vs NONE
    exact_rel_cross = [
        t
        for t, labs in text_to_labels.items()
        if "EVIDENCE_PRESENT" in labs and "NO_EVIDENCE" in labs
    ]
    sa_exact_rel_cross = [
        t
        for t in exact_rel_cross
        if any(
            str(r.get("primary_cell") or "").startswith("SHORT_ATOM/")
            for r in text_to_rows[t]
        )
    ]
    # near collisions: same lexeme token set
    lexeme_map = defaultdict(lambda: defaultdict(set))
    for r in rows:
        toks = tuple(sorted(simple_tokens(str(r["text"]))))
        if not toks:
            continue
        cell = "SHORT_ATOM" if str(r.get("primary_cell") or "").startswith("SHORT_ATOM/") else "OTHER"
        lexeme_map[cell][toks].add(str(r["evidence_label"]))
    near_cross = sum(
        1
        for labs in lexeme_map["OTHER"].values()
        if "EVIDENCE_PRESENT" in labs and "NO_EVIDENCE" in labs
    )
    sa_near_cross = sum(
        1
        for labs in lexeme_map["SHORT_ATOM"].values()
        if "EVIDENCE_PRESENT" in labs and "NO_EVIDENCE" in labs
    )

    # Model-input contract: what fields exist vs what is encoded
    missing_classes = []
    # Heuristic: PRESENT short atoms that are LEXEME_ONLY core or require external context
    sa_present = [r for r in sa_val_all if r["evidence_label"] == "EVIDENCE_PRESENT"]
    n_pres = len(sa_present) or 1
    lexeme_only_present = sum(
        1 for r in sa_present if semantic_core_class(r) == "LEXEME_ONLY"
    )
    req_ext = sum(
        1
        for r in sa_val_all
        if matched_pair_identifiability(r) == "REQUIRES_EXTERNAL_CONTEXT"
    )
    if lexeme_only_present / n_pres >= 0.05:
        missing_classes.append("dictionary_relation_or_definition_context")
    if req_ext / max(1, len(sa_val_all)) >= 0.20:
        missing_classes.append("pair_context_or_provenance")
    # subtype/source not in text
    missing_classes.extend(
        ["subtype_not_in_text", "source_family_not_in_text", "provenance_not_in_text"]
    )
    missing_input_material = (
        lexeme_only_present > 0
        or req_ext / max(1, len(sa_val_all)) >= 0.20
        or len(sa_exact_rel_cross) > 0
    )

    # Metadata diagnostic (read-only)
    def onehot(values, universe):
        idx = {u: i for i, u in enumerate(sorted(universe))}
        mat = np.zeros((len(values), len(idx)), dtype=np.float64)
        for i, v in enumerate(values):
            if v in idx:
                mat[i, idx[v]] = 1.0
        return mat

    base_tr = np.asarray(emb_tr_cls, dtype=np.float64)
    base_va = np.asarray(emb_va_cls, dtype=np.float64)
    src_u = {str(r.get("source_family") or "unk") for r in sa_train + sa_val}
    sub_u = {str(r.get("evidence_subtype") or "unk") for r in sa_train + sa_val}
    dom_u = {str(r.get("topic_domain") or "unk") for r in sa_train + sa_val}
    len_u = {str(word_count(str(r["text"]))) for r in sa_train + sa_val}

    def meta_mat(split_rows, kind):
        if kind == "source":
            return onehot([str(r.get("source_family") or "unk") for r in split_rows], src_u)
        if kind == "subtype":
            return onehot([str(r.get("evidence_subtype") or "unk") for r in split_rows], sub_u)
        if kind == "domain":
            return onehot([str(r.get("topic_domain") or "unk") for r in split_rows], dom_u)
        if kind == "length":
            return onehot([str(word_count(str(r["text"]))) for r in split_rows], len_u)
        fail(kind)

    meta_diag = {}
    configs = {
        "embedding_only": (base_tr, base_va),
        "embedding+source": (
            np.concatenate([base_tr, meta_mat(sa_train, "source")], 1),
            np.concatenate([base_va, meta_mat(sa_val, "source")], 1),
        ),
        "embedding+subtype": (
            np.concatenate([base_tr, meta_mat(sa_train, "subtype")], 1),
            np.concatenate([base_va, meta_mat(sa_val, "subtype")], 1),
        ),
        "embedding+domain": (
            np.concatenate([base_tr, meta_mat(sa_train, "domain")], 1),
            np.concatenate([base_va, meta_mat(sa_val, "domain")], 1),
        ),
        "embedding+all_metadata": (
            np.concatenate(
                [
                    base_tr,
                    meta_mat(sa_train, "source"),
                    meta_mat(sa_train, "subtype"),
                    meta_mat(sa_train, "domain"),
                    meta_mat(sa_train, "length"),
                ],
                1,
            ),
            np.concatenate(
                [
                    base_va,
                    meta_mat(sa_val, "source"),
                    meta_mat(sa_val, "subtype"),
                    meta_mat(sa_val, "domain"),
                    meta_mat(sa_val, "length"),
                ],
                1,
            ),
        ),
    }
    for name, (xt, xv) in configs.items():
        pred, _ = fit_logistic(xt, y_train, xv, seed=42)
        meta_diag[name] = {
            "SHORT_ATOM_BA": balanced_accuracy(y_val, pred),
            "NONE_recall": recall_for(y_val, pred, 0),
            "PRESENT_recall": recall_for(y_val, pred, 1),
        }

    subtype_gain = (
        meta_diag["embedding+subtype"]["SHORT_ATOM_BA"]
        - meta_diag["embedding_only"]["SHORT_ATOM_BA"]
    )

    linear_ba = cross["FACTORIZED_FAILED_8a6981c1"]["linear_probe_BA"]
    nonlinear_ba = cross["FACTORIZED_FAILED_8a6981c1"]["nonlinear_probe_BA"]
    requires_ext_frac = req_ext / max(1, len(sa_val_all))

    irr = irreducible_overlap_test(
        {
            "layer_finding": layer_finding,
            "linear_ba": linear_ba,
            "nonlinear_ba": nonlinear_ba,
            "pooling_finding": pooling_finding,
            "best_pooling_ba": max(v["SHORT_ATOM_BA"] for v in pooling_results.values()),
            "token_finding": token_finding,
            "token_ba": tok_ba,
            "exact_cross_label_collisions": len(exact_rel_cross),
            "short_atom_cross_label_collisions": len(sa_exact_rel_cross),
            "requires_external_context_fraction": requires_ext_frac,
            "missing_input_material": missing_input_material,
        }
    )

    audit = {
        "cross_experiment_geometry": cross,
        "displacement": {
            "by_label": by_label_disp,
            "UNCERTAIN": unc_disp,
            "centroid_cosine": {
                "MODEL_WIDE_BEST": parent_cos,
                "TWO_STAGE_FAILED": two_cos,
                "FACTORIZED_FAILED": fac_cos,
            },
            "displacement_class": displacement_class,
        },
        "layer_wise": {
            "table": layer_table,
            "best_layer": best_layer,
            "last_layer": last_layer,
            "best_BA": best_ba,
            "last_BA": last_ba,
            "best_minus_last_delta": best_ba - last_ba,
            "layer_finding": layer_finding,
        },
        "adaptation_depth": adapt_depth,
        "pooling": {
            "results": pooling_results,
            "finding": pooling_finding,
            "best_alt": best_alt_name,
        },
        "token_level": {
            "token_BA": tok_ba,
            "cls_BA": cls_ba2,
            "token_margin_NONE": tok_geom["NONE"]["margin_mean"],
            "cls_margin_NONE": cls_geom["NONE"]["margin_mean"],
            "finding": token_finding,
        },
        "context_sufficiency": {
            "counts": dict(ctx_counts),
            "by_label": {k: dict(v) for k, v in ctx_by_label.items()},
        },
        "collisions": {
            "exact_cross_label_any": len(exact_cross),
            "exact_cross_label_PRESENT_NONE": len(exact_rel_cross),
            "short_atom_exact_PRESENT_NONE": len(sa_exact_rel_cross),
            "near_cross_label_OTHER": near_cross,
            "short_atom_near_PRESENT_NONE": sa_near_cross,
            "example_short_atom_collisions": sa_exact_rel_cross[:10],
        },
        "matched_pair_identifiability": dict(id_counts),
        "model_input_contract": {
            "encoder_receives": ["text"],
            "not_in_model_input": missing_classes,
            "missing_input_material": missing_input_material,
            "lexeme_only_PRESENT_val": lexeme_only_present,
            "requires_external_context_val": req_ext,
            "requires_external_context_fraction": requires_ext_frac,
        },
        "metadata_diagnostic": {
            **meta_diag,
            "subtype_BA_gain": subtype_gain,
            "interpretation": (
                "subtype/metadata gain indicates gold semantics partly encoded "
                "outside text; do not treat subtype as production model input"
                if subtype_gain >= 0.05
                else "metadata gain small"
            ),
        },
        "irreducible_overlap": irr,
        # flattened keys for decide_primary_diagnosis
        "layer_finding": layer_finding,
        "adaptation_depth": adapt_depth,
        "pooling_finding": pooling_finding,
        "token_finding": token_finding,
        "linear_ba": linear_ba,
        "nonlinear_ba": nonlinear_ba,
        "best_pooling_ba": max(v["SHORT_ATOM_BA"] for v in pooling_results.values()),
        "token_ba": tok_ba,
        "exact_cross_label_collisions": len(exact_rel_cross),
        "short_atom_cross_label_collisions": len(sa_exact_rel_cross) + sa_near_cross,
        "requires_external_context_fraction": requires_ext_frac,
        "missing_input_material": missing_input_material,
        "displacement_class": displacement_class,
        "frozen_observed": FROZEN_OBSERVED_OUTCOME,
        "n_short_atom_train": len(sa_train),
        "n_short_atom_val": len(sa_val),
    }

    receipt = assemble_diagnosis_receipt(audit)
    write_private(PRIVATE / "DIAGNOSIS.json", receipt)
    write_private(PRIVATE / "AUDIT.json", audit)
    write_private(
        PRIVATE / "LAYER_WISE.json",
        audit["layer_wise"],
    )
    write_private(PRIVATE / "POOLING.json", audit["pooling"])
    write_private(PRIVATE / "COLLISIONS.json", audit["collisions"])
    write_private(
        PRIVATE / "METADATA_DIAGNOSTIC.json", audit["metadata_diagnostic"]
    )

    write_repo(REPO_ARTIFACTS / "factorized_relation_diagnose.json", receipt)
    write_repo(
        SPEC_DIR
        / "classification-v5-stage-a-factorized-relation-diagnose-receipt-20261001.json",
        receipt,
    )

    md = f"""# Classification v5 — Diagnose factorized relation SETTLED_FAIL

```text
RULE = {DIAGNOSE_RULE}
EXPERIMENT = HLX-CLASSIFICATION-V5-STAGE-A-FACTORIZED-RELATION-001
FAILED_CHECKPOINT = 8a6981c1…
PRIMARY_DIAGNOSIS = {receipt['PRIMARY_DIAGNOSIS']}
NEXT_ACTION = {receipt['NEXT_ACTION']}
DATASET_CONSEQUENCE = {receipt['DATASET_CONSEQUENCE']}
STAGE_A_BEST = cd2829c1… UNCHANGED
MODEL_WIDE_BEST = 9fba0f66… UNCHANGED
TRAIN = false
receipt = {receipt['receipt_sha256'][:16]}…
```

Read-only. No train, relabel, surface, threshold, Stage-B, reserve, or BEST moves.

## Frozen observed outcome

| Metric | Value |
|---|---:|
| threshold pairs passing | 0 / 100 |
| false_entry | 0.180 |
| NONE recall | 0.807 |
| PRESENT recall | 0.888 |
| SHORT_ATOM NONE relation FPR | 0.539 |
| SHORT_ATOM PRESENT relation recall | 0.750 |

## Cross-experiment SHORT_ATOM geometry

| Model | centroid cos | linear BA | nonlinear BA | NONE FPR (native/linear) | PRESENT recall |
|---|---:|---:|---:|---|---:|
"""
    for name in (
        "MODEL_WIDE_BEST",
        "STAGE_A_BEST",
        "TWO_STAGE_FAILED_26841d5f",
        "FACTORIZED_FAILED_8a6981c1",
    ):
        c = cross[name]
        md += (
            f"| {name} | {c['geometry']['centroid_cosine']:.3f} | "
            f"{c['linear_probe_BA']:.3f} | {c['nonlinear_probe_BA']:.3f} | "
            f"{c['NONE_FPR_native']}/{c['NONE_FPR_linear']:.3f} | "
            f"{(c['PRESENT_recall_native'] if c['PRESENT_recall_native'] is not None else c['PRESENT_recall_linear']):} |\n"
        )

    md += f"""
## Displacement class

```text
{displacement_class}
```

## Layer-wise finding

```text
best_layer = {best_layer}
last_layer = {last_layer}
best_BA = {best_ba:.3f}
last_BA = {last_ba:.3f}
layer_finding = {layer_finding}
adaptation_depth = {adapt_depth}
```

## Pooling / token

```text
pooling_finding = {pooling_finding}
token_finding = {token_finding}
cls_BA = {cls_ba2:.3f}
token_BA = {tok_ba:.3f}
best_alt_pooling = {best_alt_name} ({best_alt_ba:.3f})
```

## Identifiability / collisions

| Item | n |
|---|---:|
| exact PRESENT/NONE text collisions | {len(exact_rel_cross)} |
| SHORT_ATOM exact PRESENT/NONE | {len(sa_exact_rel_cross)} |
| SHORT_ATOM near PRESENT/NONE | {sa_near_cross} |
| REQUIRES_EXTERNAL_CONTEXT (val SA) | {req_ext} |

Metadata subtype BA gain: **{subtype_gain:.3f}**

## Primary diagnosis / next action

```text
PRIMARY_DIAGNOSIS = {receipt['PRIMARY_DIAGNOSIS']}
DATASET_CONSEQUENCE = {receipt['DATASET_CONSEQUENCE']}
architecture_change_justified = {receipt['architecture_change_justified']}
input_contract_change_justified = {receipt['input_contract_change_justified']}
NEXT_ACTION = {receipt['NEXT_ACTION']}
```

Do **not** authorize the next action here.
"""
    write_repo(
        SPEC_DIR
        / "classification-v5-stage-a-factorized-relation-diagnose-20261001.md",
        md,
    )
    write_private(PRIVATE / "DIAGNOSIS.md", md)

    print(
        json.dumps(
            {
                "PRIMARY_DIAGNOSIS": receipt["PRIMARY_DIAGNOSIS"],
                "NEXT_ACTION": receipt["NEXT_ACTION"],
                "DATASET_CONSEQUENCE": receipt["DATASET_CONSEQUENCE"],
                "layer_finding": layer_finding,
                "adaptation_depth": adapt_depth,
                "pooling_finding": pooling_finding,
                "token_finding": token_finding,
                "displacement_class": displacement_class,
                "receipt_sha256": receipt["receipt_sha256"],
                "irreducible": irr["IRREDUCIBLE_SEMANTIC_OVERLAP"],
                "subtype_BA_gain": subtype_gain,
                "requires_external_context_fraction": requires_ext_frac,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    if os.environ.get("HLX_V5_STAGE_A_FACTORIZED_DIAGNOSE_INNER") == "1":
        return inner()
    cmd = [
        "docker",
        "run",
        "--rm",
        "--gpus",
        "all",
        "-v",
        f"{REPO}:{REPO}",
        "-v",
        "/home/morpheus/hlx-private:/home/morpheus/hlx-private",
        "-v",
        "/home/morpheus/.hyperlex:/home/morpheus/.hyperlex",
        "-w",
        str(REPO),
        "-e",
        "PYTHONPATH=/home/morpheus/Hyperlex/scripts/shadow",
        "-e",
        "HLX_V2_FORWARD_ONTOLOGY=1",
        "-e",
        "HLX_V5_STAGE_A_FACTORIZED_DIAGNOSE_INNER=1",
        "--entrypoint",
        "python3",
        IMAGE,
        str(
            REPO
            / "scripts/spark/run_classification_v5_stage_a_factorized_relation_diagnose.py"
        ),
    ]
    print(json.dumps({"launch": cmd[-1], "image": IMAGE}, sort_keys=True), flush=True)
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    log_path = PRIVATE / "diagnose_console.log"
    with log_path.open("w", encoding="utf-8") as log_handle:
        completed = subprocess.run(
            cmd, check=False, stdout=log_handle, stderr=subprocess.STDOUT
        )
    try:
        print(log_path.read_text(encoding="utf-8")[-16000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
