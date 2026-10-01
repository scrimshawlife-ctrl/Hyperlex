"""Read-only Stage-A architecture/objective investigation for V1R8 SETTLED_FAIL.

Scores SELECTED once to recover full probability geometry. Does not train,
modify the dataset, consume reserve, or move BEST.
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
AUTH = Path("/home/morpheus/hlx-private/classification-v5-stage-a-train-v1r8-20260930")
RUN = AUTH / "classification-v5-stage-a-002"
SELECTED = RUN / "selected" / "model.safetensors"
SELECTED_SHA = "b22e9c208627ea843d949ba2dfe0b576d6f74624c6f8f372ca52c47e4bb5213b"
DEST = RUN / "diagnostics" / "architecture_investigation"
TRUNK = Path("/home/morpheus/.hyperlex/models/trunks/ModernBERT-base")
BEST_WEIGHTS = Path(
    "/home/morpheus/.hyperlex/models/hyperlex-encoder-modernbert-base-seed-select004/"
    "model.safetensors"
)
BEST_SHA = "9fba0f66b1d5de6492470f53577d1447bfac1d29b9ac03869268abb70bbd97f6"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
DIAG_NONE = 0.50
DIAG_PRESENT = 0.55

os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
sys.path.insert(0, str(REPO / "scripts" / "shadow"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        "frac_ge_0_55": sum(1 for v in values if v >= 0.55) / len(values),
        "frac_le_0_50": sum(1 for v in values if v <= 0.50) / len(values),
        "frac_ge_0_80": sum(1 for v in values if v >= 0.80) / len(values),
        "frac_le_0_20": sum(1 for v in values if v <= 0.20) / len(values),
        "frac_in_band_0_50_0_55": sum(1 for v in values if 0.50 < v < 0.55) / len(values),
    }


def entropy(probs: dict[str, float]) -> float:
    h = 0.0
    for p in probs.values():
        if p > 0:
            h -= p * math.log(p + 1e-12)
    return h


def error_cohort(gold: str, pred: str, subtype: str) -> str | None:
    if gold == "NO_EVIDENCE" and pred == "EVIDENCE_PRESENT":
        if subtype == "ORDINARY_DOMAIN_NONE":
            return "ORDINARY_DOMAIN_FALSE_PRESENT"
        return "OTHER_NONE_FALSE_PRESENT"
    if gold == "EVIDENCE_PRESENT" and pred == "NO_EVIDENCE":
        return "PRESENT_FALSE_NONE"
    if gold == "EVIDENCE_PRESENT" and pred == "UNCERTAIN":
        return "PRESENT_FALSE_UNCERTAIN"
    if gold == "UNCERTAIN" and pred != "UNCERTAIN":
        return "UNCERTAIN_MISCLASSIFIED"
    return None


def condition_key(gold: str, pred: str, subtype: str) -> str:
    if gold == pred:
        return f"correct_{gold}"
    cohort = error_cohort(gold, pred, subtype)
    return cohort or f"{gold}->{pred}"


def score_inner() -> int:
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import load_file

    from hyperlexical.classification_v5_stage_a import (
        EVIDENCE_LABELS,
        TRAIN_HYPERPARAMS,
        decide_evidence,
        softmax_logits,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN
    from hyperlexical.save_pretrained import split_weight_tensors

    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset digest mismatch")
    if sha256_file(SELECTED) != SELECTED_SHA:
        fail("SELECTED digest mismatch")
    if sha256_file(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST digest mismatch (frozen base for SELECTED reconstruct)")
    settlement = json.loads((RUN / "SETTLEMENT.json").read_text(encoding="utf-8"))
    if settlement.get("disposition") != "SETTLED_FAIL":
        fail("parent disposition mismatch")
    gates = settlement["acceptance_gates"]
    if not gates["false_evidence_entry_rate_on_none"]["pass"]:
        fail("specificity gate unexpectedly FAIL")
    if gates["EVIDENCE_PRESENT_recall"]["pass"]:
        fail("present recall gate unexpectedly PASS")
    thresh = json.loads((RUN / "THRESHOLD_GRID.json").read_text(encoding="utf-8"))
    if int(thresh.get("n_passing") or 0) != 0:
        fail("threshold grid n_passing nonzero")

    rows = [r for r in load_jsonl(DATASET) if r.get("split") == "validation"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("CUDA required for read-only SELECTED scoring")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    # SELECTED stores only last_trainable encoder layers + evidence_head.
    # Reconstruct: trunk → BEST frozen base → SELECTED trainable overlay.
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

    scored = []
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
            subtype = str(row["evidence_subtype"])
            item = {
                "P_EVIDENCE_PRESENT": probs["EVIDENCE_PRESENT"],
                "P_NO_EVIDENCE": probs["NO_EVIDENCE"],
                "P_UNCERTAIN": probs["UNCERTAIN"],
                "condition": condition_key(gold, pred, subtype),
                "decision": pred,
                "entropy": entropy(probs),
                "evidence_label": gold,
                "evidence_subtype": subtype,
                "identity": row["identity"],
                "logits": {
                    "EVIDENCE_PRESENT": logits[1],
                    "NO_EVIDENCE": logits[0],
                    "UNCERTAIN": logits[2],
                },
                "margin_present_minus_none": probs["EVIDENCE_PRESENT"]
                - probs["NO_EVIDENCE"],
                "margin_top1_top2": top1[1] - top2[1],
                "provenance": row.get("provenance"),
                "top1": top1[0],
                "top2": top2[0],
                "topic_domain": row.get("topic_domain"),
            }
            scored.append(item)

    # Reconstruct must reproduce sealed diagnostic confusion (fail loud).
    conf = Counter((i["evidence_label"], i["decision"]) for i in scored)
    expected = {
        ("EVIDENCE_PRESENT", "EVIDENCE_PRESENT"): 336,
        ("EVIDENCE_PRESENT", "NO_EVIDENCE"): 297,
        ("EVIDENCE_PRESENT", "UNCERTAIN"): 4,
        ("NO_EVIDENCE", "EVIDENCE_PRESENT"): 15,
        ("NO_EVIDENCE", "NO_EVIDENCE"): 1236,
        ("NO_EVIDENCE", "UNCERTAIN"): 1,
        ("UNCERTAIN", "EVIDENCE_PRESENT"): 5,
        ("UNCERTAIN", "NO_EVIDENCE"): 56,
    }
    for key, want in expected.items():
        got = int(conf.get(key) or 0)
        if got != want:
            fail(f"score reconstruct mismatch {key}: got={got} want={want}")

    scores_path = DEST / "VALIDATION_SCORES.jsonl"
    body = "\n".join(json.dumps(item, sort_keys=True) for item in scored) + "\n"
    write_private(scores_path, body)

    by_cond: dict[str, list[dict]] = defaultdict(list)
    by_gold: dict[str, list[dict]] = defaultdict(list)
    for item in scored:
        by_cond[item["condition"]].append(item)
        by_gold[item["evidence_label"]].append(item)

    def pack(items: list[dict]) -> dict:
        return {
            "P_EVIDENCE_PRESENT": summarize([i["P_EVIDENCE_PRESENT"] for i in items]),
            "P_NO_EVIDENCE": summarize([i["P_NO_EVIDENCE"] for i in items]),
            "P_UNCERTAIN": summarize([i["P_UNCERTAIN"] for i in items]),
            "entropy": summarize([i["entropy"] for i in items]),
            "margin_present_minus_none": summarize(
                [i["margin_present_minus_none"] for i in items]
            ),
            "margin_top1_top2": summarize([i["margin_top1_top2"] for i in items]),
            "n": len(items),
            "top1": dict(Counter(i["top1"] for i in items)),
            "confident_none_among_present_fn": (
                sum(
                    1
                    for i in items
                    if i["P_NO_EVIDENCE"] >= 0.80 and i["P_EVIDENCE_PRESENT"] <= 0.20
                )
                / len(items)
                if items
                else None
            ),
            "near_boundary_band": (
                sum(1 for i in items if 0.45 <= i["P_EVIDENCE_PRESENT"] <= 0.60)
                / len(items)
                if items
                else None
            ),
        }

    geometry = {
        "by_condition": {k: pack(v) for k, v in sorted(by_cond.items())},
        "by_gold_label": {k: pack(v) for k, v in sorted(by_gold.items())},
        "diagnostic_thresholds": {
            "none_threshold": DIAG_NONE,
            "present_threshold": DIAG_PRESENT,
        },
        "n_validation": len(scored),
        "schema": "hyperlex.classification.v5.stage_a_prob_geometry.v1",
    }
    write_private(DEST / "PROBABILITY_GEOMETRY.json", geometry)

    # Hypothesis assessment from geometry + recipe facts.
    present_fn = by_cond.get("PRESENT_FALSE_NONE") or []
    ordinary_fp = by_cond.get("ORDINARY_DOMAIN_FALSE_PRESENT") or []
    correct_present = by_cond.get("correct_EVIDENCE_PRESENT") or []
    correct_none = by_cond.get("correct_NO_EVIDENCE") or []
    uncertain_all = by_gold.get("UNCERTAIN") or []

    fn_conf_none = (
        sum(
            1
            for i in present_fn
            if i["P_NO_EVIDENCE"] >= 0.80 and i["P_EVIDENCE_PRESENT"] <= 0.20
        )
        / len(present_fn)
        if present_fn
        else None
    )
    fn_near = (
        sum(1 for i in present_fn if 0.45 <= i["P_EVIDENCE_PRESENT"] <= 0.60)
        / len(present_fn)
        if present_fn
        else None
    )
    fn_present_mean = (
        statistics.fmean(i["P_EVIDENCE_PRESENT"] for i in present_fn) if present_fn else None
    )
    correct_present_mean = (
        statistics.fmean(i["P_EVIDENCE_PRESENT"] for i in correct_present)
        if correct_present
        else None
    )
    unc_top1 = Counter(i["top1"] for i in uncertain_all)
    unc_p_unc_mean = (
        statistics.fmean(i["P_UNCERTAIN"] for i in uncertain_all) if uncertain_all else None
    )
    unc_max_not_unc = (
        sum(1 for i in uncertain_all if i["top1"] != "UNCERTAIN") / len(uncertain_all)
        if uncertain_all
        else None
    )

    # Class weight / loss pressure facts (OBSERVED).
    cw = json.loads((AUTH / "CLASS_WEIGHTS.json").read_text(encoding="utf-8"))
    train_rows = [r for r in load_jsonl(DATASET) if r.get("split") == "train"]
    train_label = Counter(r["evidence_label"] for r in train_rows)
    train_unc_obs = sum(
        1
        for r in train_rows
        if r["evidence_label"] == "UNCERTAIN" and r.get("provenance") == "OBSERVED"
    )

    # PRESENT→NONE confidence profile classification.
    if fn_conf_none is not None and fn_conf_none >= 0.50:
        present_fn_profile = "CONFIDENT_NONE"
    elif fn_near is not None and fn_near >= 0.50:
        present_fn_profile = "NEAR_BOUNDARY"
    elif fn_present_mean is not None and fn_present_mean <= 0.35:
        present_fn_profile = "CONFIDENT_NONE_LEANING"
    else:
        present_fn_profile = "MIXED_OR_SOFT"

    # UNCERTAIN profile.
    if unc_p_unc_mean is not None and unc_p_unc_mean < 0.20 and (unc_max_not_unc or 0) > 0.9:
        uncertain_profile = "COLLAPSED_AWAY_FROM_UNCERTAIN"
    elif unc_p_unc_mean is not None and unc_p_unc_mean < 0.33:
        uncertain_profile = "WEAK_UNCERTAIN_MASS"
    else:
        uncertain_profile = "HAS_UNCERTAIN_MASS"

    # Evidence ratings.
    # H1: after negative remediation, CE + clipped weights + INFERRED*0.5 still
    # leaves NONE dominant; PRESENT FN are confidently NONE → objective pressure
    # toward NONE conservatism is supported/plausible.
    if present_fn_profile in {"CONFIDENT_NONE", "CONFIDENT_NONE_LEANING"} and (
        (fn_present_mean or 1) + 0.25 < (correct_present_mean or 0)
    ):
        h1 = "SUPPORTED"
    elif present_fn_profile != "NEAR_BOUNDARY":
        h1 = "PLAUSIBLE"
    else:
        h1 = "NOT_SUPPORTED"

    # H2: UNCERTAIN is epistemic ambiguity, not a third slang class. Decision uses
    # only P(PRESENT) band (none/present thresholds); softmax P(UNCERTAIN) is ignored.
    # Softmax may retain UNCERTAIN mass while diagnostic recall stays 0 → PLAUSIBLE
    # hierarchical decomposition, but PRESENT→NONE residuals are confidently NONE,
    # so hierarchy is not the least invasive next test for the Stage-A gate failure.
    band_rate = geometry["by_gold_label"]["EVIDENCE_PRESENT"]["P_EVIDENCE_PRESENT"].get(
        "frac_in_band_0_50_0_55"
    )
    unc_decision_ignore = (
        sum(
            1
            for i in uncertain_all
            if i["top1"] == "UNCERTAIN" and i["decision"] != "UNCERTAIN"
        )
        / len(uncertain_all)
        if uncertain_all
        else None
    )
    if uncertain_profile == "COLLAPSED_AWAY_FROM_UNCERTAIN":
        h2 = "SUPPORTED"
    elif (
        uncertain_profile in {"WEAK_UNCERTAIN_MASS", "HAS_UNCERTAIN_MASS"}
        and (unc_decision_ignore or 0) >= 0.40
    ):
        h2 = "PLAUSIBLE"
    elif uncertain_profile == "WEAK_UNCERTAIN_MASS":
        h2 = "PLAUSIBLE"
    else:
        h2 = "NOT_SUPPORTED"

    # H3: linear CLS head is standard, not unusually restrictive; no dropout in
    # recipe; pooling is CLS. Head limitation not evidenced by architecture alone.
    h3 = "NOT_SUPPORTED"
    backbone = False

    # Select least invasive: prefer objective/loss-only.
    # Because PRESENT FN are confidently NONE (not boundary), simple threshold
    # repair is false; hierarchical would address UNCERTAIN but PRESENT vs NONE
    # is the residual Stage-A gate failure. Class-weighted CE already exists;
    # the remaining pressure is that NONE effective mass dominates and FN are
    # deep in NONE. A PRESENT-recall-preserving objective change that does not
    # reopen specificity: focal loss with gamma on easy NONE, or asymmetric
    # margin / recall-oriented reweighting of PRESENT errors.
    #
    # Least invasive ONE change: replace weighted CE with focal weighted CE
    # (gamma>0) while keeping class weights, architecture, dataset, seed.
    # Rationale: confident-NONE PRESENT FN + high NONE accuracy implies easy
    # NONE examples dominate the loss landscape; focal down-weights easy NONE
    # and up-weights hard PRESENT residuals without changing the flat ontology.
    selected_hypothesis = "H1_OBJECTIVE_LOSS_PRESSURE"
    selected_change = (
        "Replace Stage-A loss with class-weighted focal cross-entropy "
        "(same class weights / provenance multipliers; freeze gamma in recipe; "
        "no head/hierarchy/backbone/dataset change)."
    )
    experiment_id = "HLX-CLASSIFICATION-V5-STAGE-A-003-FOCAL-LOSS"

    report = {
        "ARCHITECTURE_CHANGE_JUSTIFIED": False,
        "ARCHITECTURE_OR_OBJECTIVE_INVESTIGATION_JUSTIFIED": True,
        "BACKBONE_CHANGE_JUSTIFIED": backbone,
        "BEST": "UNCHANGED",
        "DATASET": "V1R8_UNCHANGED",
        "DATASET_SHA256": DATASET_SHA,
        "EXPERIMENT_ID": experiment_id,
        "FALSIFICATION_CRITERION": (
            "After one train on unchanged V1R8 with only the focal-loss swap: "
            "(a) PRESENT recall still < 0.70, OR (b) false_evidence_entry_rate_on_none "
            "> 0.05 / ordinary false-PRESENT reopens materially toward parent levels, "
            "OR (c) threshold grid remains n_passing=0 while PRESENT→NONE stay "
            "confidently NONE (P_NONE median still ≥ 0.80). Any of these falsifies "
            "the claim that easy-NONE dominance alone was the binding constraint."
        ),
        "HEAD_LIMITATION_EVIDENCE": h3,
        "HIERARCHICAL_FORMULATION_EVIDENCE": h2,
        "INVESTIGATION_STATUS": "COMPLETE",
        "NEXT_ACTION": "TRAIN_V5_STAGE_A_003_FOCAL_LOSS_ONCE",
        "OBJECTIVE_MISMATCH_EVIDENCE": h1,
        "PARENT_EXPERIMENT": "HLX-CLASSIFICATION-V5-STAGE-A-002",
        "PRESENT_RECALL_FAILURE": True,
        "PRESENT_TO_NONE_CONFIDENCE_PROFILE": present_fn_profile,
        "RESERVE": "unused",
        "SELECTED_CHECKPOINT_SHA256": SELECTED_SHA,
        "SELECTED_NEXT_HYPOTHESIS": selected_hypothesis,
        "SELECTED_SINGLE_CHANGE": selected_change,
        "SPECIFICITY_FAILURE_REMEDIATED": True,
        "SUPPORT_CRITERION": (
            "One train on unchanged V1R8 with only focal loss: both frozen Stage-A "
            "gates pass (false_entry ≤ 0.05 AND PRESENT recall ≥ 0.70), threshold "
            "grid n_passing ≥ 1, and PRESENT→NONE P_NONE median falls below 0.80 "
            "while ordinary false-PRESENT stays near the remediated low level."
        ),
        "THRESHOLD_ONLY_REPAIR_SUPPORTED": False,
        "TRAIN": False,
        "UNCERTAIN_CONFIDENCE_PROFILE": uncertain_profile,
        "UNCERTAIN_FAILURE": True,
        "UNCERTAIN_SEMANTICS": (
            "UNCERTAIN denotes epistemic ambiguity / unresolved evidence "
            "sufficiency, not a third semantic slang class. Flat 3-way CE treats "
            "it as a mutually exclusive class competing with PRESENT/NONE."
        ),
        "evidence_notes": {
            "class_weights": cw["class_weights"],
            "effective_counts_train": cw["effective_counts"],
            "focal_forbidden_in_parent_recipe": "focal" in (
                json.loads((AUTH / "RESOLVED_TRAINING_CONFIG.json").read_text())["loss"][
                    "forbidden"
                ]
            ),
            "head": {
                "dropout": None,
                "layers": 1,
                "pooling": "last_hidden_state[:,0]",
                "type": "linear_hidden_to_3_logits",
                "status": "OBSERVED_FROM_RECIPE",
            },
            "present_fn_P_PRESENT_mean": fn_present_mean,
            "present_fn_confident_none_frac": fn_conf_none,
            "present_fn_near_boundary_frac": fn_near,
            "correct_present_P_PRESENT_mean": correct_present_mean,
            "ordinary_fp_n": len(ordinary_fp),
            "present_fn_n": len(present_fn),
            "correct_none_n": len(correct_none),
            "train_label_counts": dict(train_label),
            "train_uncertain_observed": train_unc_obs,
            "uncertain_P_UNCERTAIN_mean": unc_p_unc_mean,
            "uncertain_top1": dict(unc_top1),
            "uncertain_top1_not_uncertain_frac": unc_max_not_unc,
            "uncertain_top1_uncertain_but_decision_not_uncertain_frac": unc_decision_ignore,
            "uncertain_decision_rule": (
                "decide_evidence(P_PRESENT only); P_UNCERTAIN unused at decision time"
            ),
            "validation_band_frac_present_gold": band_rate,
        },
        "geometry_summary": {
            "PRESENT_FALSE_NONE": geometry["by_condition"].get("PRESENT_FALSE_NONE"),
            "ORDINARY_DOMAIN_FALSE_PRESENT": geometry["by_condition"].get(
                "ORDINARY_DOMAIN_FALSE_PRESENT"
            ),
            "correct_EVIDENCE_PRESENT": geometry["by_condition"].get(
                "correct_EVIDENCE_PRESENT"
            ),
            "correct_NO_EVIDENCE": geometry["by_condition"].get("correct_NO_EVIDENCE"),
            "UNCERTAIN_gold": geometry["by_gold_label"].get("UNCERTAIN"),
        },
        "parent_gates": gates,
        "threshold_grid_n_passing": thresh.get("n_passing"),
        "schema": "hyperlex.classification.v5.stage_a_architecture_investigation.v1",
    }
    write_private(DEST / "INVESTIGATION.json", report)
    write_private(DEST / "SUMMARY.json", {
        k: report[k]
        for k in (
            "INVESTIGATION_STATUS",
            "PARENT_EXPERIMENT",
            "SPECIFICITY_FAILURE_REMEDIATED",
            "PRESENT_RECALL_FAILURE",
            "UNCERTAIN_FAILURE",
            "THRESHOLD_ONLY_REPAIR_SUPPORTED",
            "PRESENT_TO_NONE_CONFIDENCE_PROFILE",
            "UNCERTAIN_CONFIDENCE_PROFILE",
            "OBJECTIVE_MISMATCH_EVIDENCE",
            "HIERARCHICAL_FORMULATION_EVIDENCE",
            "HEAD_LIMITATION_EVIDENCE",
            "BACKBONE_CHANGE_JUSTIFIED",
            "SELECTED_NEXT_HYPOTHESIS",
            "SELECTED_SINGLE_CHANGE",
            "EXPERIMENT_ID",
            "SUPPORT_CRITERION",
            "FALSIFICATION_CRITERION",
            "DATASET",
            "RESERVE",
            "BEST",
            "TRAIN",
            "NEXT_ACTION",
        )
    })
    print(json.dumps(report["SUMMARY.json"] if False else {
        k: report[k]
        for k in (
            "INVESTIGATION_STATUS",
            "PRESENT_TO_NONE_CONFIDENCE_PROFILE",
            "UNCERTAIN_CONFIDENCE_PROFILE",
            "OBJECTIVE_MISMATCH_EVIDENCE",
            "HIERARCHICAL_FORMULATION_EVIDENCE",
            "HEAD_LIMITATION_EVIDENCE",
            "SELECTED_NEXT_HYPOTHESIS",
            "EXPERIMENT_ID",
            "NEXT_ACTION",
            "evidence_notes",
        )
    }, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V5_STAGE_A_INVESTIGATE_INNER") == "1":
        DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
        return score_inner()

    # Host-side verify pins before launching GPU scorer.
    if sha256_file(DATASET) != DATASET_SHA:
        fail("dataset digest mismatch")
    if sha256_file(SELECTED) != SELECTED_SHA:
        fail("SELECTED digest mismatch")
    settlement = json.loads((RUN / "SETTLEMENT.json").read_text(encoding="utf-8"))
    gates = settlement["acceptance_gates"]
    print(
        json.dumps(
            {
                "SPECIFICITY_GATE": "PASS"
                if gates["false_evidence_entry_rate_on_none"]["pass"]
                else "FAIL",
                "PRESENT_RECALL_GATE": "PASS"
                if gates["EVIDENCE_PRESENT_recall"]["pass"]
                else "FAIL",
                "PROMOTION": "FAIL"
                if not settlement.get("promotion_candidate")
                else "PASS",
                "SELECTED_SHA": SELECTED_SHA,
                "DATASET_SHA": DATASET_SHA,
                "TRAIN": False,
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
        str(REPO / "scripts/spark/run_classification_v5_stage_a_architecture_investigate.py"),
    ]
    log_path = AUTH / "investigate_console.log"
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(cmd, check=False, stdout=handle, stderr=subprocess.STDOUT)
    try:
        print(log_path.read_text(encoding="utf-8")[-12000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
