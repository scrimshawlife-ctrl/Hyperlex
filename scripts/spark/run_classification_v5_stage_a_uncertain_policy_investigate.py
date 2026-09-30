"""INVESTIGATE_V5_STAGE_A_UNCERTAIN_POLICY — read-only policy geometry.

Scores Stage-A-003 SELECTED once. Does not train, retune weights, change
thresholds, modify labels, consume reserve, or move BEST.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path("/home/morpheus/Hyperlex")
SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-negative-evidence-surface-v1r8-20260930"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "c0fdd82d1734585a7d852318ac5b390cc5e2c50908c0ef9f9eba4b3f7ebedc8b"
AUTH = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-train-v1r8-003-focal-20260930"
)
RUN = AUTH / "classification-v5-stage-a-003"
SELECTED = RUN / "selected" / "model.safetensors"
SELECTED_SHA = "dba6d49103d7c895d7febc46c81491a07ea19acd551f86b3a9fd9f0a1c0782a3"
DEST = RUN / "diagnostics" / "uncertain_policy_investigation"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
DIAG_NONE = 0.50
DIAG_PRESENT = 0.55
THRESHOLD_GRID = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
MARGIN_FLOORS = [0.05, 0.10, 0.15, 0.20]
EXPECTED_CONFUSION = {
    ("EVIDENCE_PRESENT", "EVIDENCE_PRESENT"): 320,
    ("EVIDENCE_PRESENT", "NO_EVIDENCE"): 303,
    ("EVIDENCE_PRESENT", "UNCERTAIN"): 14,
    ("NO_EVIDENCE", "EVIDENCE_PRESENT"): 11,
    ("NO_EVIDENCE", "NO_EVIDENCE"): 1238,
    ("NO_EVIDENCE", "UNCERTAIN"): 3,
    ("UNCERTAIN", "EVIDENCE_PRESENT"): 3,
    ("UNCERTAIN", "NO_EVIDENCE"): 58,
}

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


def write_private(path: Path, payload: dict | str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    os.chmod(path, 0o600)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def _quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = q * (len(ordered) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ordered[lo]
    frac = pos - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def summarize(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    return {
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "p10": _quantile(values, 0.10),
        "p25": _quantile(values, 0.25),
        "p75": _quantile(values, 0.75),
        "p90": _quantile(values, 0.90),
        "min": min(values),
        "max": max(values),
        "n": len(values),
    }


def entropy(probs: dict[str, float]) -> float:
    h = 0.0
    for p in probs.values():
        if p > 0:
            h -= p * math.log(p + 1e-12)
    return h


def source_bucket(row: dict) -> str:
    url = str(row.get("source_url") or "")
    if "wikipedia" in url.lower():
        return "wikipedia"
    if "wiktionary" in url.lower():
        return "wiktionary"
    if url:
        return "other_url"
    return "none"


def vec(item: dict) -> tuple[float, float, float]:
    return (
        float(item["P_NO_EVIDENCE"]),
        float(item["P_EVIDENCE_PRESENT"]),
        float(item["P_UNCERTAIN"]),
    )


def l2(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def classify_present_fn(item: dict) -> str:
    """Taxonomy for gold-PRESENT misses under current scalar policy."""
    p_none = item["P_NO_EVIDENCE"]
    p_pres = item["P_EVIDENCE_PRESENT"]
    p_unc = item["P_UNCERTAIN"]
    margin = item["margin_top1_top2"]
    if p_none >= 0.80 and p_pres <= 0.20:
        return "NONE_DOMINATED"
    if item["top1"] == "UNCERTAIN" or (p_unc >= 0.30 and item["entropy"] >= 0.9):
        return "GENUINELY_UNCERTAIN"
    if margin < 0.10 and max(p_none, p_pres, p_unc) < 0.70:
        return "LOW_MARGIN_PRESENT"
    if 0.20 < p_pres < 0.55 and p_none >= p_pres:
        return "CALIBRATION_SHIFT"
    if p_none >= p_pres:
        return "NONE_DOMINATED"
    return "LOW_MARGIN_PRESENT"


def decide_argmax(item: dict) -> str:
    return item["top1"]


def decide_margin(item: dict, margin_floor: float) -> str:
    if float(item["margin_top1_top2"]) < float(margin_floor):
        return "UNCERTAIN"
    return item["top1"]


def decide_dual(item: dict, present_floor: float, none_floor: float) -> str:
    if float(item["P_EVIDENCE_PRESENT"]) >= float(present_floor):
        return "EVIDENCE_PRESENT"
    if float(item["P_NO_EVIDENCE"]) >= float(none_floor):
        return "NO_EVIDENCE"
    return "UNCERTAIN"


def policy_metrics(golds: list[str], preds: list[str]) -> dict:
    from hyperlexical.classification_v5_stage_a import (
        evaluate_decisions,
        false_evidence_entry_rate_on_none,
        prf,
    )

    evaled = evaluate_decisions(golds, preds)
    false_entry = false_evidence_entry_rate_on_none(golds, preds)
    present_r = prf(golds, preds, "EVIDENCE_PRESENT")["recall"]
    none_r = prf(golds, preds, "NO_EVIDENCE")["recall"]
    unc_r = prf(golds, preds, "UNCERTAIN")["recall"]
    gates = {
        "false_evidence_entry_rate_on_none": {
            "pass": false_entry <= 0.05,
            "value": false_entry,
            "threshold": 0.05,
        },
        "EVIDENCE_PRESENT_recall": {
            "pass": present_r >= 0.70,
            "value": present_r,
            "threshold": 0.70,
        },
        "NO_EVIDENCE_recall": {
            "pass": none_r >= 0.90,
            "value": none_r,
            "threshold": 0.90,
        },
    }
    return {
        "UNCERTAIN_recall": unc_r,
        "decision_counts": dict(Counter(preds)),
        "false_entry_on_none": false_entry,
        "gates_pass": all(g["pass"] for g in gates.values()),
        "gates": gates,
        "macro_F1": evaled["stage_a_macro_f1"],
        "NONE_recall": none_r,
        "PRESENT_recall": present_r,
        "by_label": evaled["by_label"],
        "confusion": evaled["confusion"],
    }


def slice_metrics(scored: list[dict], preds: list[str], mask: list[bool]) -> dict:
    golds = [s["evidence_label"] for s, m in zip(scored, mask) if m]
    sub_preds = [p for p, m in zip(preds, mask) if m]
    if not golds:
        return {"n": 0}
    out = policy_metrics(golds, sub_preds)
    out["n"] = len(golds)
    return out


def pack_geometry(items: list[dict]) -> dict:
    if not items:
        return {"n": 0}
    return {
        "P_EVIDENCE_PRESENT": summarize([i["P_EVIDENCE_PRESENT"] for i in items]),
        "P_NO_EVIDENCE": summarize([i["P_NO_EVIDENCE"] for i in items]),
        "P_UNCERTAIN": summarize([i["P_UNCERTAIN"] for i in items]),
        "entropy": summarize([i["entropy"] for i in items]),
        "margin_top1_top2": summarize([i["margin_top1_top2"] for i in items]),
        "n": len(items),
        "argmax_class": dict(Counter(i["top1"] for i in items)),
    }


def score_inner() -> int:
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import load_file

    from hyperlexical.classification_v2_surface import surface_form
    from hyperlexical.classification_v5_stage_a import (
        EVIDENCE_LABELS,
        TRAIN_HYPERPARAMS,
        decide_evidence,
        softmax_logits,
    )
    from hyperlexical.classification_v5_stage_a_gold_label_mapping import (
        admission_invariants,
        gold_label,
        mapping_contract,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN
    from hyperlexical.save_pretrained import split_weight_tensors

    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset digest mismatch")
    if sha256_file(SELECTED) != SELECTED_SHA:
        fail("SELECTED digest mismatch")
    # Inside docker this is typically root-readable; on host use sudo_sha256.
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST digest mismatch")
    settlement = json.loads((RUN / "SETTLEMENT.json").read_text(encoding="utf-8"))
    if settlement.get("disposition") != "SETTLED_FAIL":
        fail("parent disposition mismatch")
    if settlement.get("selected_checkpoint_sha256") != SELECTED_SHA:
        fail("settlement selected sha mismatch")

    all_rows = load_jsonl(DATASET)
    gold_admit = admission_invariants(all_rows)
    write_private(DEST / "GOLD_LABEL_MAPPING_ADMISSION.json", gold_admit)
    write_private(DEST / "GOLD_LABEL_MAPPING_CONTRACT.json", mapping_contract())
    # Diagnostic only: report admission; do not mutate surface.
    if not gold_admit["pass"]:
        # Soft note — investigation continues on declared labels for policy replay,
        # but records mapping failures for AUDIT path.
        pass

    rows = [r for r in all_rows if r.get("split") == "validation"]
    # Mapping consistency on validation (declared label vs semantic gold).
    mapping_check = {"n": 0, "mismatch": 0, "invalid": 0, "samples": []}
    for row in rows:
        mapping_check["n"] += 1
        try:
            mapped = gold_label(row)
            if mapped != str(row.get("evidence_label")):
                mapping_check["mismatch"] += 1
                if len(mapping_check["samples"]) < 10:
                    mapping_check["samples"].append(
                        {
                            "identity": row.get("identity"),
                            "declared": row.get("evidence_label"),
                            "mapped": mapped,
                            "subtype": row.get("evidence_subtype"),
                        }
                    )
        except Exception as exc:  # noqa: BLE001 — diagnostic capture
            mapping_check["invalid"] += 1
            if len(mapping_check["samples"]) < 10:
                mapping_check["samples"].append(
                    {
                        "identity": row.get("identity"),
                        "error": str(exc),
                        "subtype": row.get("evidence_subtype"),
                    }
                )
    write_private(DEST / "GOLD_LABEL_MAPPING_VALIDATION_CHECK.json", mapping_check)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("CUDA required for read-only SELECTED scoring")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    warm = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    warm_loaded = apply_encoder_trainable(encoder, warm.get("encoder") or {})
    if int(warm_loaded.get("loaded") or 0) <= 0:
        fail("BEST encoder overlay loaded zero tensors")
    evidence_head = nn.Linear(HIDDEN, len(EVIDENCE_LABELS))
    packed = split_weight_tensors(load_file(str(SELECTED), device="cpu"))
    sel_loaded = apply_encoder_trainable(encoder, packed.get("encoder") or {})
    if int(sel_loaded.get("loaded") or 0) <= 0:
        fail("SELECTED encoder overlay loaded zero tensors")
    head = packed.get("evidence_head") or {}
    if "weight" not in head or "bias" not in head:
        fail("SELECTED missing evidence_head tensors")
    with torch.no_grad():
        evidence_head.weight.copy_(head["weight"])
        evidence_head.bias.copy_(head["bias"])
    encoder.to(device)
    evidence_head.to(device)
    encoder.eval()
    evidence_head.eval()

    scored: list[dict] = []
    max_len = int(TRAIN_HYPERPARAMS["max_len"])
    with torch.no_grad():
        for row in rows:
            encoded = tokenizer(
                [str(row["text"])],
                padding=True,
                truncation=True,
                max_length=max_len,
                return_tensors="pt",
            )
            encoded = {k: v.to(device) for k, v in encoded.items()}
            pooled = encoder(**encoded).last_hidden_state[:, 0]
            logits = evidence_head(pooled)[0].detach().cpu().tolist()
            probs = softmax_logits(logits)
            ordered = sorted(probs.items(), key=lambda item: item[1], reverse=True)
            top1, top2 = ordered[0], ordered[1]
            gold = str(row["evidence_label"])
            pred = decide_evidence(
                float(probs["EVIDENCE_PRESENT"]),
                none_threshold=DIAG_NONE,
                present_threshold=DIAG_PRESENT,
            )
            form = surface_form(str(row["text"]))
            item = {
                "P_EVIDENCE_PRESENT": probs["EVIDENCE_PRESENT"],
                "P_NO_EVIDENCE": probs["NO_EVIDENCE"],
                "P_UNCERTAIN": probs["UNCERTAIN"],
                "decision_scalar_0_50_0_55": pred,
                "entropy": entropy(probs),
                "evidence_label": gold,
                "evidence_subtype": str(row["evidence_subtype"]),
                "identity": row["identity"],
                "logits": {
                    "EVIDENCE_PRESENT": logits[1],
                    "NO_EVIDENCE": logits[0],
                    "UNCERTAIN": logits[2],
                },
                "margin_top1_top2": top1[1] - top2[1],
                "provenance": row.get("provenance"),
                "source": source_bucket(row),
                "surface_form": form,
                "top1": top1[0],
                "top2": top2[0],
                "topic_domain": row.get("topic_domain"),
            }
            scored.append(item)

    conf = Counter((i["evidence_label"], i["decision_scalar_0_50_0_55"]) for i in scored)
    for key, want in EXPECTED_CONFUSION.items():
        got = int(conf.get(key) or 0)
        if got != want:
            fail(f"score reconstruct mismatch {key}: got={got} want={want}")
    # UNCERTAIN→UNCERTAIN should be 0 under sealed confusion (61 all missed).
    if int(conf.get(("UNCERTAIN", "UNCERTAIN")) or 0) != 0:
        fail("unexpected UNCERTAIN correct under scalar fail-display")

    write_private(
        DEST / "VALIDATION_SCORES.jsonl",
        "\n".join(json.dumps(item, sort_keys=True) for item in scored) + "\n",
    )

    # 1. Probability geometry by gold label
    by_gold: dict[str, list[dict]] = defaultdict(list)
    for item in scored:
        by_gold[item["evidence_label"]].append(item)
    geometry = {
        "by_gold_label": {k: pack_geometry(v) for k, v in sorted(by_gold.items())},
        "diagnostic_thresholds": {
            "none_threshold": DIAG_NONE,
            "present_threshold": DIAG_PRESENT,
        },
        "n_validation": len(scored),
        "schema": "hyperlex.classification.v5.stage_a_uncertain_policy_geometry.v1",
    }
    write_private(DEST / "PROBABILITY_GEOMETRY.json", geometry)

    # 2. PRESENT FN decomposition
    present_items = by_gold["EVIDENCE_PRESENT"]
    present_parts = {
        "PRESENT_CORRECT": [
            i for i in present_items if i["decision_scalar_0_50_0_55"] == "EVIDENCE_PRESENT"
        ],
        "PRESENT_TO_NONE": [
            i for i in present_items if i["decision_scalar_0_50_0_55"] == "NO_EVIDENCE"
        ],
        "PRESENT_TO_UNCERTAIN": [
            i for i in present_items if i["decision_scalar_0_50_0_55"] == "UNCERTAIN"
        ],
    }

    def present_partition_report(items: list[dict]) -> dict:
        tax = Counter(classify_present_fn(i) for i in items) if items else Counter()
        # For CORRECT, taxonomy is n/a — still report geometry.
        return {
            "count": len(items),
            "provenance": dict(Counter(i.get("provenance") for i in items)),
            "subtype": dict(Counter(i["evidence_subtype"] for i in items)),
            "ATOM_PROSE": dict(Counter(i["surface_form"] for i in items)),
            "source": dict(Counter(i["source"] for i in items)),
            "topic_domain": dict(Counter(str(i.get("topic_domain")) for i in items)),
            "geometry": pack_geometry(items),
            "fn_taxonomy": dict(tax),
        }

    present_decomp = {
        name: present_partition_report(items) for name, items in present_parts.items()
    }
    fn_items = present_parts["PRESENT_TO_NONE"] + present_parts["PRESENT_TO_UNCERTAIN"]
    present_decomp["FN_TAXONOMY_TOTAL"] = dict(
        Counter(classify_present_fn(i) for i in fn_items)
    )
    present_decomp["FN_PRIMARY"] = (
        max(present_decomp["FN_TAXONOMY_TOTAL"], key=present_decomp["FN_TAXONOMY_TOTAL"].get)
        if present_decomp["FN_TAXONOMY_TOTAL"]
        else None
    )
    write_private(DEST / "PRESENT_FN_DECOMPOSITION.json", present_decomp)

    # 3. UNCERTAIN gold audit + head signal
    unc_items = by_gold["UNCERTAIN"]
    present_centroid = (
        (
            statistics.fmean(i["P_NO_EVIDENCE"] for i in present_items),
            statistics.fmean(i["P_EVIDENCE_PRESENT"] for i in present_items),
            statistics.fmean(i["P_UNCERTAIN"] for i in present_items),
        )
        if present_items
        else (0.0, 0.0, 0.0)
    )
    none_items = by_gold["NO_EVIDENCE"]
    none_centroid = (
        (
            statistics.fmean(i["P_NO_EVIDENCE"] for i in none_items),
            statistics.fmean(i["P_EVIDENCE_PRESENT"] for i in none_items),
            statistics.fmean(i["P_UNCERTAIN"] for i in none_items),
        )
        if none_items
        else (0.0, 0.0, 0.0)
    )
    dist_present = [l2(vec(i), present_centroid) for i in unc_items]
    dist_none = [l2(vec(i), none_centroid) for i in unc_items]
    # Independent signal: among gold UNCERTAIN, is P(UNCERTAIN) elevated vs others?
    mean_p_unc_on_unc = (
        statistics.fmean(i["P_UNCERTAIN"] for i in unc_items) if unc_items else 0.0
    )
    mean_p_unc_on_present = (
        statistics.fmean(i["P_UNCERTAIN"] for i in present_items) if present_items else 0.0
    )
    mean_p_unc_on_none = (
        statistics.fmean(i["P_UNCERTAIN"] for i in none_items) if none_items else 0.0
    )
    top1_unc_frac = (
        sum(1 for i in unc_items if i["top1"] == "UNCERTAIN") / len(unc_items)
        if unc_items
        else 0.0
    )
    # Separability: mean distance to NONE centroid should exceed distance to a
    # random NONE row cluster if UNCERTAIN is distinct; also compare P(UNCERTAIN).
    if (
        mean_p_unc_on_unc >= 0.25
        and mean_p_unc_on_unc > mean_p_unc_on_none + 0.10
        and mean_p_unc_on_unc > mean_p_unc_on_present + 0.05
        and top1_unc_frac >= 0.20
    ):
        unc_signal = "UNCERTAIN_HEAD_SIGNAL_PRESENT"
    elif mean_p_unc_on_unc >= 0.10 or top1_unc_frac >= 0.05:
        unc_signal = "UNCERTAIN_HEAD_SIGNAL_WEAK"
    else:
        unc_signal = "UNCERTAIN_HEAD_SIGNAL_ABSENT"

    uncertain_audit = {
        "argmax_distribution": dict(Counter(i["top1"] for i in unc_items)),
        "geometry": pack_geometry(unc_items),
        "distance_to_PRESENT_centroid": summarize(dist_present),
        "distance_to_NONE_centroid": summarize(dist_none),
        "mean_P_UNCERTAIN_on_gold_UNCERTAIN": mean_p_unc_on_unc,
        "mean_P_UNCERTAIN_on_gold_PRESENT": mean_p_unc_on_present,
        "mean_P_UNCERTAIN_on_gold_NONE": mean_p_unc_on_none,
        "top1_UNCERTAIN_frac": top1_unc_frac,
        "UNCERTAIN_HEAD_SIGNAL": unc_signal,
        "n": len(unc_items),
        "note": (
            "Distances are Euclidean in (P_NONE, P_PRESENT, P_UNCERTAIN) space "
            "to gold-label probability centroids. Diagnostic only."
        ),
    }
    write_private(DEST / "UNCERTAIN_GOLD_AUDIT.json", uncertain_audit)

    # 4–5. Policy replay
    golds = [i["evidence_label"] for i in scored]
    policies: dict[str, dict] = {}

    # A. Current scalar — fail-display + full grid scan for gate-clearing
    preds_a = [
        decide_evidence(
            float(i["P_EVIDENCE_PRESENT"]),
            none_threshold=DIAG_NONE,
            present_threshold=DIAG_PRESENT,
        )
        for i in scored
    ]
    policies["A_scalar_fail_display"] = {
        "policy": "CURRENT_SCALAR_P_PRESENT",
        "none_threshold": DIAG_NONE,
        "present_threshold": DIAG_PRESENT,
        **policy_metrics(golds, preds_a),
    }
    scalar_grid = []
    best_scalar = None
    for none_thr in THRESHOLD_GRID:
        for present_thr in THRESHOLD_GRID:
            if not (none_thr < present_thr):
                continue
            preds = [
                decide_evidence(
                    float(i["P_EVIDENCE_PRESENT"]),
                    none_threshold=none_thr,
                    present_threshold=present_thr,
                )
                for i in scored
            ]
            metrics = policy_metrics(golds, preds)
            row = {
                "none_threshold": none_thr,
                "present_threshold": present_thr,
                **{k: metrics[k] for k in (
                    "false_entry_on_none",
                    "PRESENT_recall",
                    "NONE_recall",
                    "UNCERTAIN_recall",
                    "macro_F1",
                    "gates_pass",
                    "decision_counts",
                )},
            }
            scalar_grid.append(row)
            if metrics["gates_pass"] and (
                best_scalar is None or metrics["macro_F1"] > best_scalar["macro_F1"]
            ):
                best_scalar = row
    policies["A_scalar_grid"] = {
        "n_candidates": len(scalar_grid),
        "n_passing": sum(1 for r in scalar_grid if r["gates_pass"]),
        "best_gate_clearing": best_scalar,
        "grid_results": scalar_grid,
    }

    # B. Native argmax
    preds_b = [decide_argmax(i) for i in scored]
    policies["B_native_argmax"] = {
        "policy": "NATIVE_3WAY_ARGMAX",
        **policy_metrics(golds, preds_b),
    }

    # C. Margin-aware
    policies["C_margin_aware"] = {"policy": "MARGIN_AWARE_3WAY", "by_margin_floor": {}}
    best_margin = None
    for floor in MARGIN_FLOORS:
        preds = [decide_margin(i, floor) for i in scored]
        metrics = policy_metrics(golds, preds)
        entry = {"margin_floor": floor, **metrics}
        policies["C_margin_aware"]["by_margin_floor"][str(floor)] = entry
        if metrics["gates_pass"] and (
            best_margin is None or metrics["macro_F1"] > best_margin["macro_F1"]
        ):
            best_margin = {
                "margin_floor": floor,
                "false_entry_on_none": metrics["false_entry_on_none"],
                "PRESENT_recall": metrics["PRESENT_recall"],
                "NONE_recall": metrics["NONE_recall"],
                "UNCERTAIN_recall": metrics["UNCERTAIN_recall"],
                "macro_F1": metrics["macro_F1"],
            }
    policies["C_margin_aware"]["best_gate_clearing"] = best_margin
    policies["C_margin_aware"]["n_passing_floors"] = sum(
        1
        for v in policies["C_margin_aware"]["by_margin_floor"].values()
        if v["gates_pass"]
    )

    # D. Dual-confidence on frozen grid
    dual_grid = []
    best_dual = None
    for present_floor in THRESHOLD_GRID:
        for none_floor in THRESHOLD_GRID:
            preds = [decide_dual(i, present_floor, none_floor) for i in scored]
            metrics = policy_metrics(golds, preds)
            row = {
                "present_floor": present_floor,
                "none_floor": none_floor,
                **{k: metrics[k] for k in (
                    "false_entry_on_none",
                    "PRESENT_recall",
                    "NONE_recall",
                    "UNCERTAIN_recall",
                    "macro_F1",
                    "gates_pass",
                    "decision_counts",
                )},
            }
            dual_grid.append(row)
            if metrics["gates_pass"] and (
                best_dual is None or metrics["macro_F1"] > best_dual["macro_F1"]
            ):
                best_dual = row
    policies["D_dual_confidence"] = {
        "policy": "DUAL_CONFIDENCE",
        "n_candidates": len(dual_grid),
        "n_passing": sum(1 for r in dual_grid if r["gates_pass"]),
        "best_gate_clearing": best_dual,
        # Keep compact summary + top rows by PRESENT recall among false_entry pass
        "top_by_present_recall_false_entry_ok": sorted(
            [r for r in dual_grid if r["false_entry_on_none"] <= 0.05],
            key=lambda r: (r["PRESENT_recall"], r["NONE_recall"], r["macro_F1"]),
            reverse=True,
        )[:15],
        "grid_results": dual_grid,
    }
    write_private(DEST / "POLICY_REPLAY.json", policies)

    # 6. Provenance / surface sensitivity for key policies
    masks = {
        "OBSERVED": [i.get("provenance") == "OBSERVED" for i in scored],
        "INFERRED": [i.get("provenance") == "INFERRED" for i in scored],
        "ATOM": [i.get("surface_form") == "ATOM" for i in scored],
        "PROSE": [i.get("surface_form") == "PROSE" for i in scored],
    }
    sensitivity = {}
    for name, mask in masks.items():
        sensitivity[name] = {
            "A_scalar_fail_display": slice_metrics(scored, preds_a, mask),
            "B_native_argmax": slice_metrics(scored, preds_b, mask),
        }
        # best dual if any, else dual at 0.55/0.55 style diagnostic
        dual_preds = [decide_dual(i, 0.55, 0.55) for i in scored]
        sensitivity[name]["D_dual_0_55_0_55"] = slice_metrics(scored, dual_preds, mask)
        margin_preds = [decide_margin(i, 0.10) for i in scored]
        sensitivity[name]["C_margin_0_10"] = slice_metrics(scored, margin_preds, mask)
    write_private(DEST / "SLICE_SENSITIVITY.json", sensitivity)

    # Observed PRESENT recall specifically
    obs_present_mask = [
        i.get("provenance") == "OBSERVED" and i["evidence_label"] == "EVIDENCE_PRESENT"
        for i in scored
    ]
    obs_present_fix = {
        "n_obs_present": sum(obs_present_mask),
        "A_scalar": slice_metrics(scored, preds_a, obs_present_mask).get("PRESENT_recall"),
        "B_argmax": slice_metrics(scored, preds_b, obs_present_mask).get("PRESENT_recall"),
        "C_margin_0_10": slice_metrics(
            scored, [decide_margin(i, 0.10) for i in scored], obs_present_mask
        ).get("PRESENT_recall"),
        "D_dual_best": None,
    }
    if best_dual:
        dpreds = [
            decide_dual(i, best_dual["present_floor"], best_dual["none_floor"])
            for i in scored
        ]
        obs_present_fix["D_dual_best"] = slice_metrics(
            scored, dpreds, obs_present_mask
        ).get("PRESENT_recall")
        obs_present_fix["D_dual_best_params"] = {
            "present_floor": best_dual["present_floor"],
            "none_floor": best_dual["none_floor"],
        }

    gate_clearing = []
    if best_scalar:
        gate_clearing.append({"policy": "A_scalar", **best_scalar})
    if policies["B_native_argmax"]["gates_pass"]:
        gate_clearing.append(
            {
                "policy": "B_native_argmax",
                "PRESENT_recall": policies["B_native_argmax"]["PRESENT_recall"],
                "NONE_recall": policies["B_native_argmax"]["NONE_recall"],
                "false_entry_on_none": policies["B_native_argmax"]["false_entry_on_none"],
                "macro_F1": policies["B_native_argmax"]["macro_F1"],
            }
        )
    if best_margin:
        gate_clearing.append({"policy": "C_margin_aware", **best_margin})
    if best_dual:
        gate_clearing.append({"policy": "D_dual_confidence", **best_dual})

    # 7. Primary diagnosis
    policy_mis = len(gate_clearing) > 0
    if policy_mis:
        primary = "UNCERTAIN_POLICY_MIS-SPECIFIED"
        next_action = "SPEC_V5_STAGE_A_DECISION_POLICY_V2"
    elif unc_signal == "UNCERTAIN_HEAD_SIGNAL_ABSENT":
        primary = "UNCERTAIN_SUPERVISION_INSUFFICIENT"
        next_action = "AUDIT_V5_UNCERTAIN_LABEL_SURFACE"
    elif unc_signal == "UNCERTAIN_HEAD_SIGNAL_WEAK" and present_decomp["FN_PRIMARY"] == "NONE_DOMINATED":
        # Weak head + confident-NONE PRESENT FNs → mixed or representation
        # If no policy clears gates and FNs are NONE-dominated, representation limit.
        primary = "MIXED_UNCERTAIN_FAILURE"
        next_action = "AUDIT_V5_UNCERTAIN_LABEL_SURFACE"
    elif present_decomp["FN_PRIMARY"] == "NONE_DOMINATED" and unc_signal != "UNCERTAIN_HEAD_SIGNAL_PRESENT":
        primary = "MODEL_REPRESENTATION_LIMIT"
        next_action = "STOP_AND_REDESIGN_STAGE_A_REPRESENTATION"
    elif unc_signal in {"UNCERTAIN_HEAD_SIGNAL_ABSENT", "UNCERTAIN_HEAD_SIGNAL_WEAK"}:
        primary = "UNCERTAIN_SUPERVISION_INSUFFICIENT"
        next_action = "AUDIT_V5_UNCERTAIN_LABEL_SURFACE"
    else:
        # Head has signal but scalar ignores it and no frozen policy clears gates
        # → policy still mis-specified in spirit but not proven by gate-clearing.
        # Spec says MIS-SPECIFIED only if frozen diagnostic clears all three gates.
        primary = "MIXED_UNCERTAIN_FAILURE"
        next_action = "AUDIT_V5_UNCERTAIN_LABEL_SURFACE"

    # Refine: if CURRENT policy is somehow fine (shouldn't be) 
    if (
        policies["A_scalar_fail_display"]["gates_pass"]
        and not policy_mis
    ):
        primary = "CURRENT_POLICY_ADEQUATE"
        next_action = "STOP"

    summary = {
        "INVESTIGATION": "INVESTIGATE_V5_STAGE_A_UNCERTAIN_POLICY",
        "INVESTIGATION_STATE": "COMPLETE",
        "TRAIN": False,
        "BEST": "UNCHANGED",
        "BEST_SHA256": BEST_SHA,
        "RESERVE": "unused",
        "RESERVE_CONSUMED": False,
        "EXPERIMENT_PARENT": "HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS",
        "SELECTED_CHECKPOINT_SHA256": SELECTED_SHA,
        "DATASET_SHA256": DATASET_SHA,
        "GOLD_LABEL_MAPPING_RULE": "HYPERLEX_V5_STAGE_A_GOLD_LABEL_MAPPING_V1",
        "GOLD_LABEL_MAPPING_ADMISSION_PASS": gold_admit["pass"],
        "GOLD_LABEL_MAPPING_VALIDATION": mapping_check,
        "UNCERTAIN_HEAD_SIGNAL": unc_signal,
        "PRESENT_FN_PRIMARY": present_decomp["FN_PRIMARY"],
        "PRESENT_FN_TAXONOMY": present_decomp["FN_TAXONOMY_TOTAL"],
        "POLICY_A_fail_display": {
            k: policies["A_scalar_fail_display"][k]
            for k in (
                "false_entry_on_none",
                "PRESENT_recall",
                "NONE_recall",
                "UNCERTAIN_recall",
                "macro_F1",
                "gates_pass",
                "decision_counts",
            )
        },
        "POLICY_A_grid_n_passing": policies["A_scalar_grid"]["n_passing"],
        "POLICY_B": {
            k: policies["B_native_argmax"][k]
            for k in (
                "false_entry_on_none",
                "PRESENT_recall",
                "NONE_recall",
                "UNCERTAIN_recall",
                "macro_F1",
                "gates_pass",
                "decision_counts",
            )
        },
        "POLICY_C_n_passing_floors": policies["C_margin_aware"]["n_passing_floors"],
        "POLICY_C_by_floor": {
            k: {
                sk: policies["C_margin_aware"]["by_margin_floor"][k][sk]
                for sk in (
                    "false_entry_on_none",
                    "PRESENT_recall",
                    "NONE_recall",
                    "UNCERTAIN_recall",
                    "macro_F1",
                    "gates_pass",
                    "decision_counts",
                )
            }
            for k in policies["C_margin_aware"]["by_margin_floor"]
        },
        "POLICY_D_n_passing": policies["D_dual_confidence"]["n_passing"],
        "POLICY_D_best_gate_clearing": best_dual,
        "GATE_CLEARING_DIAGNOSTIC_POLICIES": gate_clearing,
        "OBSERVED_PRESENT_RECALL_BY_POLICY": obs_present_fix,
        "SLICE_SENSITIVITY_SUMMARY": {
            slice_name: {
                pol: {
                    "PRESENT_recall": sensitivity[slice_name][pol].get("PRESENT_recall"),
                    "NONE_recall": sensitivity[slice_name][pol].get("NONE_recall"),
                    "false_entry_on_none": sensitivity[slice_name][pol].get(
                        "false_entry_on_none"
                    ),
                    "n": sensitivity[slice_name][pol].get("n"),
                }
                for pol in sensitivity[slice_name]
            }
            for slice_name in sensitivity
        },
        "PRIMARY_DIAGNOSIS": primary,
        "NEXT_ACTION": next_action,
        "PROMOTION_AUTHORIZATION": False,
        "note": (
            "Diagnostic policy replay only. Gate-clearing here does not authorize "
            "production thresholds or promotion. Gold UNCERTAIN remains dataset-"
            "semantic under HYPERLEX_V5_STAGE_A_GOLD_LABEL_MAPPING_V1."
        ),
    }
    write_private(DEST / "SUMMARY.json", summary)
    write_private(AUTH / "UNCERTAIN_POLICY_INVESTIGATION_SUMMARY.json", summary)

    # Update auth next-action pointer only (no train / BEST / reserve mutation).
    auth = json.loads((AUTH / "AUTHORIZATION.json").read_text(encoding="utf-8"))
    auth["UNCERTAIN_POLICY_INVESTIGATION"] = "COMPLETE"
    auth["UNCERTAIN_POLICY_PRIMARY_DIAGNOSIS"] = primary
    auth["UNCERTAIN_HEAD_SIGNAL"] = unc_signal
    auth["NEXT_ACTION"] = next_action
    auth["BEST"] = "UNCHANGED"
    auth["RESERVE"] = "unused"
    auth["RESERVE_CONSUMED"] = False
    auth["TRAIN"] = False
    write_private(AUTH / "AUTHORIZATION.json", auth)

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V5_STAGE_A_INVESTIGATE_INNER") == "1":
        DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
        return score_inner()

    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset digest mismatch")
    if sha256_file(SELECTED) != SELECTED_SHA:
        fail("SELECTED digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST digest mismatch")
    settlement = json.loads((RUN / "SETTLEMENT.json").read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "INVESTIGATION": "INVESTIGATE_V5_STAGE_A_UNCERTAIN_POLICY",
                "TRAIN": False,
                "SELECTED_SHA": SELECTED_SHA,
                "DATASET_SHA": DATASET_SHA,
                "BEST_SHA": BEST_SHA,
                "PARENT_DISPOSITION": settlement.get("disposition"),
                "launch": "docker_gpu_readonly_score",
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )
    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
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
        "HLX_V5_STAGE_A_INVESTIGATE_INNER=1",
        "--entrypoint",
        "python3",
        IMAGE,
        str(
            REPO
            / "scripts/spark/run_classification_v5_stage_a_uncertain_policy_investigate.py"
        ),
    ]
    log_path = AUTH / "uncertain_policy_investigate_console.log"
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(
            cmd, check=False, stdout=handle, stderr=subprocess.STDOUT
        )
    try:
        print(log_path.read_text(encoding="utf-8")[-16000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
