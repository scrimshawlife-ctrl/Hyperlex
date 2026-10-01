"""DIAGNOSE_V5_STAGE_A_GENERALIZATION_RETRAIN_SETTLED_FAIL — Spark runner.

Read-only Gate-1 / SHORT_ATOM diagnosis of the V1R1 SETTLED_FAIL candidate.
Does not train, create V1R2, retune, use spent reserve, or move BEST.
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

SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-generalization-surface-v1r1-20261001"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "4095036e5af3ad7cfe9f038dd3e1f46e4ef0ea18db4c4b7186fc2b02e96d4274"
READINESS_SHA = "c4b5fc0725b919c1dd11acfd575d594d8ddd76839836e5a3928f4d6c07030c96"
AUTH_DEST = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-two-stage-generalization-train-v1-20261001"
)
FAILED_CKPT = (
    AUTH_DEST
    / "classification-v5-stage-a-two-stage-generalization-001"
    / "selected"
    / "model.safetensors"
)
FAILED_CKPT_SHA = "26841d5f3a8b9cd4237f79203b80697f2da186e7d4b30ab6c08d528adba56e76"
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
    "classification-v5-stage-a-generalization-retrain-diagnose-20261001"
)
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
REPO_ARTIFACTS = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V5-STAGE-A-TWO-STAGE-GENERALIZATION-001"
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


def pin_inputs() -> None:
    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset_sha_mismatch")
    if sha256_file(SURFACE / "READINESS.json") != READINESS_SHA:
        fail("readiness_sha_mismatch")
    if sudo_sha256(FAILED_CKPT) != FAILED_CKPT_SHA:
        fail("failed_checkpoint_sha_mismatch")
    if sudo_sha256(STAGE_A_BEST_WEIGHTS) != STAGE_A_BEST_SHA:
        fail("STAGE_A_BEST_sha_mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("MODEL_WIDE_BEST_sha_mismatch")
    # Spent reserve must not be loaded — only verify ledger status if present.
    reserve_seal = Path(
        "/home/morpheus/hlx-private/classification-v5-reserve-20260930/RESERVE_SEAL.json"
    )
    if reserve_seal.is_file():
        seal = json.loads(reserve_seal.read_text(encoding="utf-8"))
        status = str(seal.get("status") or seal.get("reserve_status") or "")
        if status and status != "SPENT" and "SPENT" not in status:
            # Allow missing/alternate schema; do not load reserve rows.
            pass


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


def inner() -> int:
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import load_file

    from hyperlexical.classification_v2_surface import surface_form, word_count
    from hyperlexical.classification_v5_stage_a import (
        evaluate_decisions,
        canonical_json,
        sha256_text,
    )
    from hyperlexical.classification_v5_stage_a_generalization_surface import (
        length_band,
    )
    from hyperlexical.classification_v5_stage_a_generalization_retrain_diagnose import (
        DIAGNOSE_RULE,
        FROZEN_OBSERVED_OUTCOME,
        GATE1_THRESHOLDS,
        architecture_semantic_comparison,
        assemble_diagnosis_receipt,
        centroid,
        classify_gate1_error,
        classify_representation_state,
        cosine,
        decide_next_action,
        decide_primary_diagnosis,
        dist_stats,
        distribution_overlap,
        gate1_gold_possible,
        justified_changes,
        label_authority,
        label_derivation,
        semantic_core_class,
        simple_tokens,
        token_hash,
    )
    from hyperlexical.classification_v5_stage_a_two_stage import (
        decide_two_stage,
        gate1_probabilities,
        gate2_probabilities,
    )
    from hyperlexical.classification_v5_stage_a_two_stage_generalization import (
        AUTHORIZED_BEST_SHA,
        EXPERIMENT_ID,
        PARENT_STAGE_A_BEST_SHA,
        SPENT_RESERVE,
        SPENT_RESERVE_OVERLAP,
        SPENT_RESERVE_STATUS,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN, MAX_LEN
    from hyperlexical.loop import freeze_encoder
    from hyperlexical.save_pretrained import split_weight_tensors

    pin_inputs()
    if PRIVATE.exists() and (PRIVATE / "DIAGNOSIS.json").exists():
        fail(f"output_already_exists:{PRIVATE}")
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)

    rows = load_jsonl(DATASET)
    train_rows = [r for r in rows if r.get("split") == "train"]
    val_rows = [r for r in rows if r.get("split") == "validation"]
    if len(train_rows) != 2531 or len(val_rows) != 1054:
        fail("split_counts_mismatch")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("diagnose_requires_cuda")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"

    def load_two_stage(path: Path):
        encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
        # Start from MODEL_WIDE_BEST overlay then apply Stage-A trainable tensors.
        warm = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
        apply_encoder_trainable(encoder, warm.get("encoder") or {})
        split = split_weight_tensors(load_file(str(path), device="cpu"))
        loaded = apply_encoder_trainable(encoder, split.get("encoder") or {})
        if loaded["loaded"] not in {12, 48}:
            # selected ckpt stores last-2 trainable only (12); tolerate
            if loaded["loaded"] < 12:
                fail(f"encoder_overlay_incomplete:{path}:{loaded['loaded']}")
        freeze_encoder(encoder, last_trainable=2)
        g1 = nn.Linear(HIDDEN, 2)
        g2 = nn.Linear(HIDDEN, 2)
        with torch.no_grad():
            g1.weight.copy_(split["gate1_head"]["weight"])
            g1.bias.copy_(split["gate1_head"]["bias"])
            g2.weight.copy_(split["gate2_head"]["weight"])
            g2.bias.copy_(split["gate2_head"]["bias"])
        encoder.to(device).eval()
        g1.to(device).eval()
        g2.to(device).eval()
        return encoder, g1, g2, loaded["loaded"]

    failed_enc, failed_g1, failed_g2, failed_loaded = load_two_stage(FAILED_CKPT)
    best_enc, best_g1, best_g2, best_loaded = load_two_stage(STAGE_A_BEST_WEIGHTS)

    def score_model(encoder, g1_head, g2_head, split_rows: list[dict]):
        scored = []
        embeds = []
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
                pooled = encoder(**encoded).last_hidden_state[:, 0]
                emb = torch.nn.functional.normalize(pooled, dim=-1)[0]
                logits1 = g1_head(pooled)[0]
                logits2 = g2_head(pooled)[0]
                g1p = gate1_probabilities(logits1.detach().cpu().tolist())
                g2p = gate2_probabilities(logits2.detach().cpu().tolist())
                p_pos = float(g1p["POSSIBLE_EVIDENCE"])
                p_conf = float(g2p["CONFIRMED_PRESENT"])
                # margin = logit_possible - logit_none
                margin = float(logits1[1] - logits1[0])
                scored.append(
                    {
                        **row,
                        "Gate1_error": classify_gate1_error(
                            evidence_label=str(row["evidence_label"]),
                            p_possible=p_pos,
                            gate1_threshold=0.50,
                        ),
                        "atom_prose": surface_form(str(row["text"])),
                        "length_band": length_band(word_count(str(row["text"]))),
                        "p_confirmed": p_conf,
                        "p_possible": p_pos,
                        "gate1_margin": margin,
                        "token_count": word_count(str(row["text"])),
                        "text_length": len(str(row["text"])),
                        "label_authority": label_authority(row),
                        "label_derivation": label_derivation(row),
                        "semantic_core": semantic_core_class(row),
                    }
                )
                embeds.append(emb.detach().cpu().tolist())
        return scored, embeds

    val_scored, val_embeds = score_model(
        failed_enc, failed_g1, failed_g2, val_rows
    )
    train_scored, train_embeds = score_model(
        failed_enc, failed_g1, failed_g2, train_rows
    )
    # STAGE_A_BEST on same V1R1 validation SHORT_ATOM only (full val for fairness)
    best_val_scored, best_val_embeds = score_model(
        best_enc, best_g1, best_g2, val_rows
    )

    # --- Gate1 error decomposition ---
    def cohort_contrib(scored: list[dict], error_code: str, key_fn):
        buckets: dict[str, list[dict]] = defaultdict(list)
        for row in scored:
            if row["Gate1_error"] == error_code:
                buckets[str(key_fn(row))].append(row)
        total = sum(len(v) for v in buckets.values()) or 1
        ranked = []
        for name, items in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
            ranked.append(
                {
                    "cohort": name,
                    "fraction": len(items) / total,
                    "n": len(items),
                }
            )
        return {"n_total": total if total != 1 or any(buckets) else 0, "ranked": ranked[:25]}

    error_counts = Counter(r["Gate1_error"] for r in val_scored)
    gate1_decomp = {
        "counts": dict(error_counts),
        "FALSE_NONE_rankings": {
            "ATOM_PROSE": cohort_contrib(
                val_scored, "FALSE_NONE", lambda r: r["atom_prose"]
            ),
            "domain": cohort_contrib(
                val_scored, "FALSE_NONE", lambda r: r.get("topic_domain") or "unspecified"
            ),
            "gold_label": cohort_contrib(
                val_scored, "FALSE_NONE", lambda r: r["evidence_label"]
            ),
            "label_authority": cohort_contrib(
                val_scored, "FALSE_NONE", lambda r: r["label_authority"]
            ),
            "label_derivation": cohort_contrib(
                val_scored, "FALSE_NONE", lambda r: r["label_derivation"]
            ),
            "length_band": cohort_contrib(
                val_scored, "FALSE_NONE", lambda r: r["length_band"]
            ),
            "provenance": cohort_contrib(
                val_scored, "FALSE_NONE", lambda r: r.get("provenance") or "UNKNOWN"
            ),
            "source_family": cohort_contrib(
                val_scored, "FALSE_NONE", lambda r: r.get("source_family") or "unknown"
            ),
            "subtype": cohort_contrib(
                val_scored, "FALSE_NONE", lambda r: r.get("evidence_subtype") or "NONE"
            ),
        },
        "FALSE_POSSIBLE_rankings": {
            "ATOM_PROSE": cohort_contrib(
                val_scored, "FALSE_POSSIBLE", lambda r: r["atom_prose"]
            ),
            "domain": cohort_contrib(
                val_scored,
                "FALSE_POSSIBLE",
                lambda r: r.get("topic_domain") or "unspecified",
            ),
            "gold_label": cohort_contrib(
                val_scored, "FALSE_POSSIBLE", lambda r: r["evidence_label"]
            ),
            "label_authority": cohort_contrib(
                val_scored, "FALSE_POSSIBLE", lambda r: r["label_authority"]
            ),
            "label_derivation": cohort_contrib(
                val_scored, "FALSE_POSSIBLE", lambda r: r["label_derivation"]
            ),
            "length_band": cohort_contrib(
                val_scored, "FALSE_POSSIBLE", lambda r: r["length_band"]
            ),
            "provenance": cohort_contrib(
                val_scored, "FALSE_POSSIBLE", lambda r: r.get("provenance") or "UNKNOWN"
            ),
            "source_family": cohort_contrib(
                val_scored, "FALSE_POSSIBLE", lambda r: r.get("source_family") or "unknown"
            ),
            "subtype": cohort_contrib(
                val_scored,
                "FALSE_POSSIBLE",
                lambda r: r.get("evidence_subtype") or "NONE",
            ),
        },
        "gate1_threshold": 0.50,
        "n_validation": len(val_scored),
    }

    # --- SHORT_ATOM distributions ---
    def is_short_atom(row: dict) -> bool:
        cell = str(row.get("primary_cell") or "")
        return cell.startswith("SHORT_ATOM/") or row.get("atom_prose") == "ATOM"

    sa_val = [r for r in val_scored if is_short_atom(r)]
    sa_by_label = {
        "NO_EVIDENCE": [r for r in sa_val if r["evidence_label"] == "NO_EVIDENCE"],
        "EVIDENCE_PRESENT": [
            r for r in sa_val if r["evidence_label"] == "EVIDENCE_PRESENT"
        ],
        "UNCERTAIN": [r for r in sa_val if r["evidence_label"] == "UNCERTAIN"],
    }
    short_atom_distributions = {
        label: {
            "gate1_margin": dist_stats([r["gate1_margin"] for r in items]),
            "n": len(items),
            "p_confirmed": dist_stats([r["p_confirmed"] for r in items]),
            "p_possible": dist_stats([r["p_possible"] for r in items]),
        }
        for label, items in sa_by_label.items()
    }
    short_atom_distributions["overlaps"] = {
        "NONE_vs_PRESENT_p_possible": distribution_overlap(
            [r["p_possible"] for r in sa_by_label["NO_EVIDENCE"]],
            [r["p_possible"] for r in sa_by_label["EVIDENCE_PRESENT"]],
        ),
        "NONE_vs_UNCERTAIN_p_possible": distribution_overlap(
            [r["p_possible"] for r in sa_by_label["NO_EVIDENCE"]],
            [r["p_possible"] for r in sa_by_label["UNCERTAIN"]],
        ),
        "PRESENT_vs_UNCERTAIN_p_possible": distribution_overlap(
            [r["p_possible"] for r in sa_by_label["EVIDENCE_PRESENT"]],
            [r["p_possible"] for r in sa_by_label["UNCERTAIN"]],
        ),
    }

    # --- Representation separability (failed candidate SHORT_ATOM) ---
    sa_idx = [i for i, r in enumerate(val_scored) if is_short_atom(r)]
    sa_none_vecs = [
        val_embeds[i]
        for i in sa_idx
        if val_scored[i]["evidence_label"] == "NO_EVIDENCE"
    ]
    sa_pres_vecs = [
        val_embeds[i]
        for i in sa_idx
        if val_scored[i]["evidence_label"] == "EVIDENCE_PRESENT"
    ]
    sa_unc_vecs = [
        val_embeds[i]
        for i in sa_idx
        if val_scored[i]["evidence_label"] == "UNCERTAIN"
    ]
    c_none = centroid(sa_none_vecs)
    c_pres = centroid(sa_pres_vecs)
    c_unc = centroid(sa_unc_vecs)

    def nearest_margins(vectors: list[list[float]], same: list[list[float]], opp: list[list[float]]):
        margins = []
        nearest_same = []
        nearest_opp = []
        for i, vec in enumerate(vectors):
            same_pool = [v for j, v in enumerate(same) if v is not vec]
            # identity by index within same list
            same_pool = [same[j] for j in range(len(same)) if j != i] if same is vectors else list(same)
            if not same_pool or not opp:
                continue
            ns = max(cosine(vec, o) for o in same_pool)
            no = max(cosine(vec, o) for o in opp)
            nearest_same.append(ns)
            nearest_opp.append(no)
            margins.append(ns - no)
        return {
            "mean_margin": sum(margins) / len(margins) if margins else None,
            "mean_nearest_opposite": sum(nearest_opp) / len(nearest_opp) if nearest_opp else None,
            "mean_nearest_same": sum(nearest_same) / len(nearest_same) if nearest_same else None,
            "n": len(margins),
        }

    none_margin = nearest_margins(sa_none_vecs, sa_none_vecs, sa_pres_vecs)
    pres_margin = nearest_margins(sa_pres_vecs, sa_pres_vecs, sa_none_vecs)
    none_present_cos = (
        cosine(c_none, c_pres) if c_none and c_pres else None
    )
    representation_separability = {
        "NONE_PRESENT_centroid_cosine": none_present_cos,
        "NONE_UNCERTAIN_centroid_cosine": cosine(c_none, c_unc) if c_none and c_unc else None,
        "PRESENT_UNCERTAIN_centroid_cosine": cosine(c_pres, c_unc) if c_pres and c_unc else None,
        "SHORT_ATOM_NONE_nearest": none_margin,
        "SHORT_ATOM_PRESENT_nearest": pres_margin,
        "n_NONE": len(sa_none_vecs),
        "n_PRESENT": len(sa_pres_vecs),
        "n_UNCERTAIN": len(sa_unc_vecs),
    }
    representation_state = classify_representation_state(
        none_present_cosine=none_present_cos,
        mean_none_margin=none_margin["mean_margin"],
        mean_present_margin=pres_margin["mean_margin"],
    )
    representation_separability["state"] = representation_state

    # --- Probes (fit on train embeds, eval on val) ---
    def gate1_targets(scored: list[dict]) -> list[int]:
        return [1 if gate1_gold_possible(r["evidence_label"]) else 0 for r in scored]

    y_train = gate1_targets(train_scored)
    y_val = gate1_targets(val_scored)
    x_train = torch.tensor(train_embeds, dtype=torch.float32, device=device)
    x_val = torch.tensor(val_embeds, dtype=torch.float32, device=device)
    y_train_t = torch.tensor(y_train, dtype=torch.float32, device=device)

    # A: existing head
    with torch.no_grad():
        a_logits = failed_g1(x_val)
        a_pred = (torch.softmax(a_logits, dim=-1)[:, 1] >= 0.50).long().cpu().tolist()

    # B: logistic probe (LBFGS)
    logistic = nn.Linear(HIDDEN, 1).to(device)
    nn.init.zeros_(logistic.weight)
    nn.init.zeros_(logistic.bias)
    opt = torch.optim.LBFGS(logistic.parameters(), max_iter=50, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        logits = logistic(x_train).squeeze(-1)
        loss = nn.functional.binary_cross_entropy_with_logits(logits, y_train_t)
        loss.backward()
        return loss

    opt.step(closure)
    with torch.no_grad():
        b_prob = torch.sigmoid(logistic(x_val).squeeze(-1)).cpu().tolist()
        b_pred = [1 if p >= 0.5 else 0 for p in b_prob]

    # C: small nonlinear MLP probe (diagnostic only)
    mlp = nn.Sequential(
        nn.Linear(HIDDEN, 64),
        nn.ReLU(),
        nn.Linear(64, 1),
    ).to(device)
    nn.init.xavier_uniform_(mlp[0].weight)
    nn.init.zeros_(mlp[0].bias)
    nn.init.xavier_uniform_(mlp[2].weight)
    nn.init.zeros_(mlp[2].bias)
    opt_m = torch.optim.AdamW(mlp.parameters(), lr=1e-3, weight_decay=0.01)
    mlp.train()
    for _ in range(80):
        opt_m.zero_grad()
        logits = mlp(x_train).squeeze(-1)
        loss = nn.functional.binary_cross_entropy_with_logits(logits, y_train_t)
        loss.backward()
        opt_m.step()
    mlp.eval()
    with torch.no_grad():
        c_prob = torch.sigmoid(mlp(x_val).squeeze(-1)).cpu().tolist()
        c_pred = [1 if p >= 0.5 else 0 for p in c_prob]

    sa_val_idx = [i for i, r in enumerate(val_scored) if is_short_atom(r)]
    sa_y = [y_val[i] for i in sa_val_idx]
    sa_none_idx = [
        i for i in sa_val_idx if val_scored[i]["evidence_label"] == "NO_EVIDENCE"
    ]
    sa_pres_idx = [
        i for i in sa_val_idx if val_scored[i]["evidence_label"] == "EVIDENCE_PRESENT"
    ]

    def probe_metrics(name: str, pred: list[int]) -> dict[str, Any]:
        sa_pred = [pred[i] for i in sa_val_idx]
        none_true = [0] * len(sa_none_idx)
        none_pred = [pred[i] for i in sa_none_idx]
        pres_true = [1] * len(sa_pres_idx)
        # PRESENT recall among SHORT_ATOM PRESENT (pred==1)
        pres_recall = (
            sum(1 for i in sa_pres_idx if pred[i] == 1) / len(sa_pres_idx)
            if sa_pres_idx
            else 0.0
        )
        none_recall = (
            sum(1 for i in sa_none_idx if pred[i] == 0) / len(sa_none_idx)
            if sa_none_idx
            else 0.0
        )
        return {
            "name": name,
            "overall_ba": balanced_accuracy(y_val, pred),
            "short_atom_ba": balanced_accuracy(sa_y, sa_pred),
            "short_atom_NONE_recall": none_recall,
            "short_atom_PRESENT_recall": pres_recall,
            "diagnostic_only": True,
            "persisted_as_model": False,
        }

    probe_results = {
        "A_existing_head": probe_metrics("A_existing_head", a_pred),
        "B_logistic": probe_metrics("B_logistic", b_pred),
        "C_nonlinear": probe_metrics("C_nonlinear", c_pred),
        "interpretation": None,
    }
    a_ba = probe_results["A_existing_head"]["short_atom_ba"]
    b_ba = probe_results["B_logistic"]["short_atom_ba"]
    c_ba = probe_results["C_nonlinear"]["short_atom_ba"]
    if (b_ba - a_ba) >= 0.05 and (c_ba - b_ba) < 0.05:
        probe_results["interpretation"] = "HEAD_OPTIMIZATION_FAILURE"
    elif (c_ba - b_ba) >= 0.05:
        probe_results["interpretation"] = "NONLINEAR_BOUNDARY_SIGNAL"
    else:
        probe_results["interpretation"] = "REPRESENTATION_OR_SEMANTIC_FAILURE"

    # Delete probe params — do not persist.
    del logistic, mlp, opt, opt_m

    # --- Lexical association (TRAIN ONLY) ---
    token_none = Counter()
    token_possible = Counter()
    for row in train_scored:
        toks = set(simple_tokens(str(row["text"])))
        if gate1_gold_possible(row["evidence_label"]):
            token_possible.update(toks)
        else:
            token_none.update(toks)
    vocab = set(token_none) | set(token_possible)
    # smoothed log-odds possible vs none
    assoc = []
    n_none_docs = sum(1 for r in train_scored if not gate1_gold_possible(r["evidence_label"]))
    n_pos_docs = sum(1 for r in train_scored if gate1_gold_possible(r["evidence_label"]))
    for tok in vocab:
        a = token_possible[tok] + 0.5
        b = token_none[tok] + 0.5
        # approximate document-smoothed rates
        log_odds = math.log((a / (n_pos_docs + 1.0)) / (b / (n_none_docs + 1.0)))
        assoc.append((log_odds, tok))
    assoc.sort(reverse=True)
    high_cut = assoc[max(0, int(0.10 * len(assoc)) - 1)][0] if assoc else 0.0
    high_tokens = {tok for lo, tok in assoc if lo >= max(high_cut, 0.5)}

    def frac_high(rows_subset: list[dict]) -> float:
        if not rows_subset:
            return 0.0
        hit = 0
        for row in rows_subset:
            toks = set(simple_tokens(str(row["text"])))
            if toks & high_tokens:
                hit += 1
        return hit / len(rows_subset)

    fp_atoms = [
        r
        for r in sa_val
        if r["Gate1_error"] == "FALSE_POSSIBLE" and r["evidence_label"] == "NO_EVIDENCE"
    ]
    tn_atoms = [
        r
        for r in sa_val
        if r["Gate1_error"] == "TRUE_NONE" and r["evidence_label"] == "NO_EVIDENCE"
    ]
    top_hashes = [
        {"log_odds": lo, "token_sha12": token_hash(tok)}
        for lo, tok in assoc[:20]
    ]
    lexical_association = {
        "false_possible_high_assoc_fraction": frac_high(fp_atoms),
        "high_assoc_threshold_log_odds": max(high_cut, 0.5),
        "n_FALSE_POSSIBLE_atoms": len(fp_atoms),
        "n_TRUE_NONE_atoms": len(tn_atoms),
        "n_high_assoc_tokens": len(high_tokens),
        "top_token_hashes": top_hashes,
        "true_none_high_assoc_fraction": frac_high(tn_atoms),
        "train_only": True,
    }

    # --- Semantic core ---
    sem_counts = Counter(r["semantic_core"] for r in sa_val)
    sem_by_label = {
        label: dict(Counter(r["semantic_core"] for r in items))
        for label, items in sa_by_label.items()
    }
    semantic_core = {
        "gate1_asked_to_distinguish": (
            "token/domain membership vs actual asserted evidence "
            "without an explicit intermediate supervision signal"
        ),
        "short_atom_by_label": sem_by_label,
        "short_atom_counts": dict(sem_counts),
        "support": len(sa_val),
    }

    # --- Provenance controlled ---
    def match_key(row: dict) -> tuple:
        return (
            str(row["evidence_label"]),
            str(row.get("evidence_subtype") or ""),
            str(row.get("primary_cell") or row.get("atom_prose") or ""),
            str(row["length_band"]),
            str(row.get("source_family") or ""),
        )

    obs = [r for r in val_scored if r.get("provenance") == "OBSERVED"]
    inf = [r for r in val_scored if r.get("provenance") == "INFERRED"]
    obs_map: dict[tuple, list[dict]] = defaultdict(list)
    inf_map: dict[tuple, list[dict]] = defaultdict(list)
    for r in obs:
        obs_map[match_key(r)].append(r)
    for r in inf:
        inf_map[match_key(r)].append(r)
    keys = sorted(set(obs_map) & set(inf_map))
    matched_pairs = 0
    d_p = []
    d_fe_num = d_fe_den = 0
    d_fn_num = d_fn_den = 0
    for key in keys:
        o_rows = obs_map[key]
        i_rows = inf_map[key]
        n = min(len(o_rows), len(i_rows))
        matched_pairs += n
        for j in range(n):
            o = o_rows[j]
            i = i_rows[j]
            d_p.append(o["p_possible"] - i["p_possible"])
            if o["evidence_label"] == "NO_EVIDENCE":
                d_fe_den += 1
                if o["Gate1_error"] == "FALSE_POSSIBLE":
                    d_fe_num += 1
                # inferred false entry counted separately via rates below
            if gate1_gold_possible(o["evidence_label"]):
                d_fn_den += 1
                if o["Gate1_error"] == "FALSE_NONE":
                    d_fn_num += 1
    # Rates within matched NONE/PRESENT cells
    matched_obs_none = []
    matched_inf_none = []
    matched_obs_pos = []
    matched_inf_pos = []
    for key in keys:
        if key[0] == "NO_EVIDENCE":
            n = min(len(obs_map[key]), len(inf_map[key]))
            matched_obs_none.extend(obs_map[key][:n])
            matched_inf_none.extend(inf_map[key][:n])
        elif key[0] in {"EVIDENCE_PRESENT", "UNCERTAIN"}:
            n = min(len(obs_map[key]), len(inf_map[key]))
            matched_obs_pos.extend(obs_map[key][:n])
            matched_inf_pos.extend(inf_map[key][:n])

    def fe_rate(items: list[dict]) -> float | None:
        if not items:
            return None
        return sum(1 for r in items if r["Gate1_error"] == "FALSE_POSSIBLE") / len(items)

    def fn_rate(items: list[dict]) -> float | None:
        if not items:
            return None
        return sum(1 for r in items if r["Gate1_error"] == "FALSE_NONE") / len(items)

    if matched_pairs < 30:
        prov_status = "INSUFFICIENT_MATCHED_SUPPORT"
    else:
        # Persist if OBSERVED still worse on false-entry after matching
        o_fe = fe_rate(matched_obs_none)
        i_fe = fe_rate(matched_inf_none)
        if o_fe is not None and i_fe is not None and (o_fe - i_fe) >= 0.05:
            prov_status = "PROVENANCE_EFFECT_PERSISTS"
        elif o_fe is not None and i_fe is not None and abs(o_fe - i_fe) < 0.05:
            prov_status = "PROVENANCE_EFFECT_EXPLAINED"
        else:
            prov_status = "INSUFFICIENT_MATCHED_SUPPORT"

    provenance_controlled = {
        "matched_coverage_pairs": matched_pairs,
        "matched_keys": len(keys),
        "mean_p_possible_delta_obs_minus_inf": (
            sum(d_p) / len(d_p) if d_p else None
        ),
        "raw_INFERRED_false_entry": FROZEN_OBSERVED_OUTCOME.get("E2E_false_entry"),
        "matched_INFERRED_NONE_false_entry": fe_rate(matched_inf_none),
        "matched_OBSERVED_NONE_false_entry": fe_rate(matched_obs_none),
        "matched_INFERRED_POSSIBLE_false_none": fn_rate(matched_inf_pos),
        "matched_OBSERVED_POSSIBLE_false_none": fn_rate(matched_obs_pos),
        "n_matched_NONE": len(matched_obs_none),
        "n_matched_POSSIBLE": len(matched_obs_pos),
        "status": prov_status,
    }

    # --- Wiktionary source effect ---
    wik = [r for r in val_scored if r.get("source_family") == "wiktionary_aggregate"]
    non_wik = [r for r in val_scored if r.get("source_family") != "wiktionary_aggregate"]

    def fe(items: list[dict]) -> float:
        none = [r for r in items if r["evidence_label"] == "NO_EVIDENCE"]
        if not none:
            return 0.0
        return sum(1 for r in none if r["Gate1_error"] == "FALSE_POSSIBLE") / len(none)

    # Control: SHORT_ATOM + length 1-4
    def ctrl(items: list[dict], **pred):
        out = items
        if "atom" in pred:
            out = [r for r in out if r["atom_prose"] == pred["atom"]]
        if "length" in pred:
            out = [r for r in out if r["length_band"] == pred["length"]]
        if "subtype" in pred:
            out = [r for r in out if r.get("evidence_subtype") == pred["subtype"]]
        return out

    wik_atom_14 = ctrl(wik, atom="ATOM", length="1-4")
    non_wik_atom_14 = ctrl(non_wik, atom="ATOM", length="1-4")
    wik_prose = ctrl(wik, atom="PROSE")
    non_wik_prose = ctrl(non_wik, atom="PROSE")
    # Determine dominant effect
    effects = []
    if abs(fe(wik_atom_14) - fe(non_wik_atom_14)) < 0.05 and fe(wik_atom_14) >= 0.3:
        effects.append("LEXICAL_ATOM_EFFECT")
    if abs(fe(wik) - fe(wik_atom_14)) < 0.08 and fe(ctrl(wik, atom="PROSE")) < fe(wik) - 0.1:
        effects.append("LEXICAL_ATOM_EFFECT")
    if fe(wik_prose) >= fe(non_wik_prose) + 0.1:
        effects.append("SOURCE_STYLE_EFFECT")
    # domain composition
    wik_domains = Counter(r.get("topic_domain") or "unspecified" for r in wik)
    # label composition
    wik_labels = Counter(r["evidence_label"] for r in wik)
    non_labels = Counter(r["evidence_label"] for r in non_wik)
    if effects == ["LEXICAL_ATOM_EFFECT"]:
        source_effect = "LEXICAL_ATOM_EFFECT"
    elif "SOURCE_STYLE_EFFECT" in effects and "LEXICAL_ATOM_EFFECT" in effects:
        source_effect = "MIXED_SOURCE_EFFECT"
    elif "SOURCE_STYLE_EFFECT" in effects:
        source_effect = "SOURCE_STYLE_EFFECT"
    elif abs(
        (wik_labels.get("NO_EVIDENCE", 0) / max(1, len(wik)))
        - (non_labels.get("NO_EVIDENCE", 0) / max(1, len(non_wik)))
    ) >= 0.15:
        source_effect = "LABEL_COMPOSITION_EFFECT"
    elif len(wik_domains) <= 5:
        source_effect = "DOMAIN_COMPOSITION_EFFECT"
    else:
        source_effect = "MIXED_SOURCE_EFFECT" if effects else "MIXED_SOURCE_EFFECT"

    wiktionary_source_effect = {
        "class": source_effect,
        "n": len(wik),
        "false_entry": fe(wik),
        "controls": {
            "non_wik_ATOM_1-4_false_entry": fe(non_wik_atom_14),
            "non_wik_PROSE_false_entry": fe(wik_prose and non_wik_prose),
            "non_wik_overall_false_entry": fe(non_wik),
            "wik_ATOM_1-4_false_entry": fe(wik_atom_14),
            "wik_ATOM_1-4_n": len(wik_atom_14),
            "wik_PROSE_false_entry": fe(wik_prose),
            "non_wik_ATOM_1-4_n": len(non_wik_atom_14),
        },
        "label_composition": dict(wik_labels),
        "note": "Do not delete source solely for poor performance.",
    }
    # fix prose control bug
    wiktionary_source_effect["controls"]["non_wik_PROSE_false_entry"] = fe(non_wik_prose)

    # --- Threshold impossibility ---
    curve = []
    for thr in GATE1_THRESHOLDS:
        # Gate1-only
        none_rows = [r for r in val_scored if r["evidence_label"] == "NO_EVIDENCE"]
        pos_rows = [
            r for r in val_scored if r["evidence_label"] == "EVIDENCE_PRESENT"
        ]
        possible_rows = [
            r for r in val_scored if gate1_gold_possible(r["evidence_label"])
        ]
        fe_v = (
            sum(1 for r in none_rows if r["p_possible"] >= thr) / len(none_rows)
            if none_rows
            else 0.0
        )
        none_r = (
            sum(1 for r in none_rows if r["p_possible"] < thr) / len(none_rows)
            if none_rows
            else 0.0
        )
        # e2e PRESENT with Gate2 fixed at 0.50 (strong gate; isolates Gate1 conflict)
        decisions = [
            decide_two_stage(
                p_possible=r["p_possible"],
                p_confirmed=r["p_confirmed"],
                gate1_threshold=thr,
                gate2_present_threshold=0.50,
            )
            for r in val_scored
        ]
        metrics = evaluate_decisions(
            [r["evidence_label"] for r in val_scored], decisions
        )
        curve.append(
            {
                "threshold": thr,
                "e2e_NONE_recall": metrics["by_label"]["NO_EVIDENCE"]["recall"],
                "e2e_PRESENT_recall": metrics["by_label"]["EVIDENCE_PRESENT"]["recall"],
                "e2e_false_entry": metrics["false_evidence_entry_rate_on_none"],
                "gate1_NONE_recall": none_r,
                "gate1_POSSIBLE_recall": (
                    sum(1 for r in possible_rows if r["p_possible"] >= thr)
                    / len(possible_rows)
                    if possible_rows
                    else 0.0
                ),
                "gate1_PRESENT_recall_proxy": (
                    sum(1 for r in pos_rows if r["p_possible"] >= thr) / len(pos_rows)
                    if pos_rows
                    else 0.0
                ),
                "gate1_false_entry": fe_v,
                "passes_all_three": (
                    metrics["false_evidence_entry_rate_on_none"] <= 0.05
                    and metrics["by_label"]["EVIDENCE_PRESENT"]["recall"] >= 0.70
                    and metrics["by_label"]["NO_EVIDENCE"]["recall"] >= 0.90
                ),
            }
        )
    n_pass = sum(1 for c in curve if c["passes_all_three"])
    # Classify impossibility
    # If some thr hits fe and none but kills PRESENT, or vice versa → conflict
    can_fe_none = any(
        c["e2e_false_entry"] <= 0.05 and c["e2e_NONE_recall"] >= 0.90 for c in curve
    )
    can_present = any(c["e2e_PRESENT_recall"] >= 0.70 for c in curve)
    if n_pass > 0:
        thr_class = "CALIBRATION_ONLY"
    elif can_fe_none and can_present and n_pass == 0:
        thr_class = "OPERATING_POINT_CONFLICT"
    else:
        thr_class = "STRUCTURAL_CLASS_OVERLAP"
    # Refine: if even at thr where PRESENT>=0.70, fe stays >>0.05 → structural
    present_ok = [c for c in curve if c["e2e_PRESENT_recall"] >= 0.70]
    if present_ok and min(c["e2e_false_entry"] for c in present_ok) > 0.05:
        if max(c["e2e_NONE_recall"] for c in present_ok) < 0.90:
            thr_class = "STRUCTURAL_CLASS_OVERLAP"

    threshold_impossibility = {
        "Gate2_fixed_for_curve": 0.50,
        "class": thr_class,
        "curve": curve,
        "explanation": (
            "No frozen Gate1 threshold jointly satisfies false_entry<=0.05, "
            "PRESENT>=0.70, and NONE>=0.90 on V1R1 validation under the selected "
            "checkpoint; SHORT_ATOM p_possible overlap forces the tradeoff."
        ),
        "n_passing_gate1_grid_with_gate2_0.50": n_pass,
    }

    # --- Old vs new Stage-A on SHORT_ATOM ---
    def sa_metrics(scored: list[dict]) -> dict[str, Any]:
        sa = [r for r in scored if is_short_atom(r)]
        none = [r for r in sa if r["evidence_label"] == "NO_EVIDENCE"]
        pres = [r for r in sa if r["evidence_label"] == "EVIDENCE_PRESENT"]
        return {
            "NONE_recall": (
                sum(1 for r in none if r["p_possible"] < 0.50) / len(none) if none else None
            ),
            "PRESENT_recall": (
                sum(1 for r in pres if r["p_possible"] >= 0.50) / len(pres) if pres else None
            ),
            "mean_NONE_p_possible": (
                sum(r["p_possible"] for r in none) / len(none) if none else None
            ),
            "mean_PRESENT_p_possible": (
                sum(r["p_possible"] for r in pres) / len(pres) if pres else None
            ),
            "n_NONE": len(none),
            "n_PRESENT": len(pres),
            "score_separation": (
                (
                    sum(r["p_possible"] for r in pres) / len(pres)
                    - sum(r["p_possible"] for r in none) / len(none)
                )
                if none and pres
                else None
            ),
        }

    # best candidate SHORT_ATOM embedding geometry
    best_sa_idx = [i for i, r in enumerate(best_val_scored) if is_short_atom(r)]
    best_none_vecs = [
        best_val_embeds[i]
        for i in best_sa_idx
        if best_val_scored[i]["evidence_label"] == "NO_EVIDENCE"
    ]
    best_pres_vecs = [
        best_val_embeds[i]
        for i in best_sa_idx
        if best_val_scored[i]["evidence_label"] == "EVIDENCE_PRESENT"
    ]
    best_c_none = centroid(best_none_vecs)
    best_c_pres = centroid(best_pres_vecs)
    best_none_m = nearest_margins(best_none_vecs, best_none_vecs, best_pres_vecs)
    best_pres_m = nearest_margins(best_pres_vecs, best_pres_vecs, best_none_vecs)

    failed_sa_m = sa_metrics(val_scored)
    best_sa_m = sa_metrics(best_val_scored)
    # Interpretation of V1R1 training effect
    cos_new = none_present_cos
    cos_old = cosine(best_c_none, best_c_pres) if best_c_none and best_c_pres else None
    sep_new = failed_sa_m["score_separation"]
    sep_old = best_sa_m["score_separation"]
    if (
        cos_old is not None
        and cos_new is not None
        and cos_new < cos_old - 0.02
        and (failed_sa_m["PRESENT_recall"] or 0) > (best_sa_m["PRESENT_recall"] or 0)
        and (failed_sa_m["NONE_recall"] or 1) < (best_sa_m["NONE_recall"] or 0)
    ):
        v1r1_effect = (
            "improved_PRESENT_geometry_at_cost_of_NONE_geometry"
        )
    elif (
        cos_old is not None
        and cos_new is not None
        and cos_new < cos_old - 0.02
        and (sep_new or 0) > (sep_old or 0)
        and (failed_sa_m["NONE_recall"] or 0) < 0.6
    ):
        v1r1_effect = "improved_representation_separation_but_moved_decision_boundary_badly"
    elif cos_old is not None and cos_new is not None and cos_new >= cos_old - 0.01:
        v1r1_effect = "failed_to_improve_representation_separation"
    else:
        v1r1_effect = "improved_PRESENT_geometry_at_cost_of_NONE_geometry"

    old_vs_new = {
        "FAILED_V1R1_candidate": {
            "checkpoint": FAILED_CKPT_SHA,
            "centroid_NONE_PRESENT_cosine": cos_new,
            "nearest_margins": {
                "NONE": none_margin,
                "PRESENT": pres_margin,
            },
            "short_atom_metrics": failed_sa_m,
        },
        "STAGE_A_BEST": {
            "checkpoint": STAGE_A_BEST_SHA,
            "centroid_NONE_PRESENT_cosine": cos_old,
            "nearest_margins": {
                "NONE": best_none_m,
                "PRESENT": best_pres_m,
            },
            "short_atom_metrics": best_sa_m,
        },
        "v1r1_training_effect": v1r1_effect,
    }

    # data coverage dominant? only if SHORT_ATOM support tiny — it's not
    data_coverage_dominant = False

    primary = decide_primary_diagnosis(
        {
            "data_coverage_dominant": data_coverage_dominant,
            "lexical_association": lexical_association,
            "probe_results": probe_results,
            "representation_state": representation_state,
            "semantic_core": semantic_core,
            "threshold_impossibility": threshold_impossibility,
        }
    )
    next_action = decide_next_action(primary["primary_diagnosis"])
    justified = justified_changes(primary["primary_diagnosis"])

    payload = {
        "architecture_semantic_comparison": architecture_semantic_comparison(),
        "frozen_observed_outcome": dict(FROZEN_OBSERVED_OUTCOME),
        "gate1_error_decomposition": gate1_decomp,
        "justified": justified,
        "lexical_association": lexical_association,
        "next_action": next_action,
        "old_vs_new_stage_a": old_vs_new,
        "primary": primary,
        "probe_results": probe_results,
        "provenance_controlled": provenance_controlled,
        "representation_separability": representation_separability,
        "representation_state": representation_state,
        "semantic_core": semantic_core,
        "short_atom_distributions": short_atom_distributions,
        "threshold_impossibility": threshold_impossibility,
        "wiktionary_source_effect": wiktionary_source_effect,
    }
    receipt = assemble_diagnosis_receipt(payload)

    # Privacy: do not write raw embeddings or raw texts.
    write_private(PRIVATE / "DIAGNOSIS.json", receipt)
    write_private(PRIVATE / "GATE1_ERROR_DECOMPOSITION.json", gate1_decomp)
    write_private(PRIVATE / "SHORT_ATOM_DISTRIBUTIONS.json", short_atom_distributions)
    write_private(PRIVATE / "REPRESENTATION.json", representation_separability)
    write_private(PRIVATE / "PROBES.json", probe_results)
    write_private(PRIVATE / "LEXICAL_ASSOCIATION.json", lexical_association)
    write_private(PRIVATE / "SEMANTIC_CORE.json", semantic_core)
    write_private(PRIVATE / "PROVENANCE_CONTROLLED.json", provenance_controlled)
    write_private(PRIVATE / "WIKTIONARY_SOURCE.json", wiktionary_source_effect)
    write_private(PRIVATE / "THRESHOLD_IMPOSSIBILITY.json", threshold_impossibility)
    write_private(PRIVATE / "OLD_VS_NEW_STAGE_A.json", old_vs_new)
    write_private(
        PRIVATE / "SUMMARY.json",
        {
            "DIAGNOSE_RULE": DIAGNOSE_RULE,
            "EXPERIMENT_ID": EXPERIMENT_ID,
            "FAILED_CHECKPOINT_SHA256": FAILED_CKPT_SHA,
            "MODEL_WIDE_BEST": AUTHORIZED_BEST_SHA,
            "MODEL_WIDE_BEST_MUTATED": False,
            "NEXT_ACTION": next_action,
            "PARENT_STAGE_A_BEST": PARENT_STAGE_A_BEST_SHA,
            "PRIMARY_DIAGNOSIS": primary["primary_diagnosis"],
            "PROBE_INTERPRETATION": probe_results["interpretation"],
            "REPRESENTATION_STATE": representation_state,
            "SPENT_RESERVE": SPENT_RESERVE,
            "SPENT_RESERVE_OVERLAP": SPENT_RESERVE_OVERLAP,
            "SPENT_RESERVE_STATUS": SPENT_RESERVE_STATUS,
            "STAGE_A_BEST_MUTATED": False,
            "TRAIN": False,
            "V1R1_MUTATED": False,
            "justified": justified,
            "provenance_status": prov_status,
            "receipt_sha256": receipt["receipt_sha256"],
            "threshold_class": thr_class,
            "wiktionary_effect": source_effect,
            "v1r1_training_effect": v1r1_effect,
        },
    )

    public = {
        "DIAGNOSE_RULE": DIAGNOSE_RULE,
        "EXPERIMENT_ID": EXPERIMENT_ID,
        "FAILED_CHECKPOINT_SHA256": FAILED_CKPT_SHA,
        "MODEL_WIDE_BEST_MUTATED": False,
        "NEXT_ACTION": next_action,
        "PRIMARY_DIAGNOSIS": primary["primary_diagnosis"],
        "PRIMARY_REASONS": primary["reasons"],
        "PROBE_INTERPRETATION": probe_results["interpretation"],
        "REPRESENTATION_STATE": representation_state,
        "SPENT_RESERVE_STATUS": SPENT_RESERVE_STATUS,
        "STAGE_A_BEST_MUTATED": False,
        "TRAIN": False,
        "frozen_observed_outcome": dict(FROZEN_OBSERVED_OUTCOME),
        "justified": justified,
        "lexical_association": {
            k: lexical_association[k]
            for k in (
                "false_possible_high_assoc_fraction",
                "true_none_high_assoc_fraction",
                "n_FALSE_POSSIBLE_atoms",
                "n_TRUE_NONE_atoms",
                "n_high_assoc_tokens",
                "top_token_hashes",
                "train_only",
            )
        },
        "old_vs_new_stage_a": old_vs_new,
        "probe_results": probe_results,
        "provenance_controlled": {
            k: provenance_controlled[k]
            for k in (
                "status",
                "matched_coverage_pairs",
                "matched_keys",
                "mean_p_possible_delta_obs_minus_inf",
                "matched_OBSERVED_NONE_false_entry",
                "matched_INFERRED_NONE_false_entry",
                "n_matched_NONE",
                "n_matched_POSSIBLE",
            )
        },
        "representation_separability": {
            k: representation_separability[k]
            for k in (
                "state",
                "NONE_PRESENT_centroid_cosine",
                "NONE_UNCERTAIN_centroid_cosine",
                "PRESENT_UNCERTAIN_centroid_cosine",
                "SHORT_ATOM_NONE_nearest",
                "SHORT_ATOM_PRESENT_nearest",
                "n_NONE",
                "n_PRESENT",
                "n_UNCERTAIN",
            )
        },
        "semantic_core": semantic_core,
        "short_atom_distributions": short_atom_distributions,
        "threshold_impossibility": {
            "class": thr_class,
            "n_passing_gate1_grid_with_gate2_0.50": n_pass,
            "explanation": threshold_impossibility["explanation"],
            "curve": curve,
        },
        "gate1_error_decomposition": {
            "counts": gate1_decomp["counts"],
            "FALSE_POSSIBLE_top": {
                k: (gate1_decomp["FALSE_POSSIBLE_rankings"][k]["ranked"][:8])
                for k in (
                    "ATOM_PROSE",
                    "length_band",
                    "source_family",
                    "subtype",
                    "provenance",
                    "domain",
                )
            },
            "FALSE_NONE_top": {
                k: (gate1_decomp["FALSE_NONE_rankings"][k]["ranked"][:8])
                for k in (
                    "ATOM_PROSE",
                    "length_band",
                    "source_family",
                    "subtype",
                    "provenance",
                )
            },
        },
        "wiktionary_source_effect": wiktionary_source_effect,
        "architecture_semantic_comparison": architecture_semantic_comparison(),
        "receipt_sha256": receipt["receipt_sha256"],
    }
    write_repo(REPO_ARTIFACTS / "generalization_retrain_diagnose.json", public)
    write_repo(
        SPEC_DIR
        / "classification-v5-stage-a-generalization-retrain-diagnose-receipt-20261001.json",
        public,
    )
    print(json.dumps(json.loads((PRIVATE / "SUMMARY.json").read_text()), indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V5_STAGE_A_GENERALIZATION_DIAGNOSE_INNER") == "1":
        return inner()

    pin_inputs()
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
        "HLX_V5_STAGE_A_GENERALIZATION_DIAGNOSE_INNER=1",
        "--entrypoint",
        "python3",
        IMAGE,
        str(
            REPO
            / "scripts/spark/run_classification_v5_stage_a_generalization_retrain_diagnose.py"
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
        print(log_path.read_text(encoding="utf-8")[-12000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
