"""ARCHITECTURE_OR_OBJECTIVE_INVESTIGATION — Stage-A-004 / V1R9 read-only.

Scores SELECTED once for probability + embedding geometry. Does not train,
modify V1R9, consume reserve, or move BEST. Does not authorize a train run.
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
    "classification-v5-stage-a-negative-evidence-surface-v1r9-20260930"
)
DATASET = SURFACE / "EVIDENCE_SURFACE.jsonl"
DATASET_SHA = "8d4be8301b89b191841342fe11ef647c838b32e56e6d133b610c232264c5d00a"
PARENT_SURFACE = Path(
    "/home/morpheus/hlx-private/"
    "classification-v5-stage-a-negative-evidence-surface-v1r8-20260930"
)
PARENT_DATASET_SHA = (
    "c0fdd82d1734585a7d852318ac5b390cc5e2c50908c0ef9f9eba4b3f7ebedc8b"
)
AUTH = Path("/home/morpheus/hlx-private/classification-v5-stage-a-train-v1r9-20260930")
RUN = AUTH / "classification-v5-stage-a-004"
SELECTED = RUN / "selected" / "model.safetensors"
SELECTED_SHA = "82840630a89ea9e9b34fdfc010d455e6bbfce05ecfcb29abe2929505e9e21fdd"
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
FOCAL_FALSIFIED = True  # Stage-A-003 focal SETTLED_FAIL on V1R8
REPO_ARTIFACTS = (
    REPO / "artifacts" / "experiments" / "HLX-CLASSIFICATION-V5-STAGE-A-004"
)
EXPECTED_CONFUSION = {
    ("EVIDENCE_PRESENT", "EVIDENCE_PRESENT"): 374,
    ("EVIDENCE_PRESENT", "NO_EVIDENCE"): 254,
    ("EVIDENCE_PRESENT", "UNCERTAIN"): 9,
    ("NO_EVIDENCE", "EVIDENCE_PRESENT"): 20,
    ("NO_EVIDENCE", "NO_EVIDENCE"): 1231,
    ("NO_EVIDENCE", "UNCERTAIN"): 1,
    ("UNCERTAIN", "EVIDENCE_PRESENT"): 16,
    ("UNCERTAIN", "NO_EVIDENCE"): 146,
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


def write_repo(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def entropy(probs: dict[str, float]) -> float:
    h = 0.0
    for p in probs.values():
        if p > 0:
            h -= p * math.log(p + 1e-12)
    return h


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
        "p90": _quantile(values, 0.90),
        "min": min(values),
        "max": max(values),
        "n": len(values),
        "frac_ge_0_80": sum(1 for v in values if v >= 0.80) / len(values),
        "frac_le_0_20": sum(1 for v in values if v <= 0.20) / len(values),
        "frac_in_band_0_50_0_55": sum(1 for v in values if 0.50 < v < 0.55) / len(values),
    }


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
    return error_cohort(gold, pred, subtype) or f"{gold}->{pred}"


def source_family(row: dict) -> str:
    url = str(row.get("source_url") or "")
    bucket = str(row.get("source_bucket") or "")
    blob = f"{url} {bucket}".lower()
    if "wikipedia" in blob or bucket.startswith("v5_src_wp_"):
        return "wikipedia"
    if "wiktionary" in blob or bucket.startswith("v5_src_wik_"):
        return "wiktionary"
    if "urban" in blob or "hub" in blob:
        return "hub"
    if url:
        return "other_url"
    return "none"


def freeze_baseline() -> dict:
    from hyperlexical.classification_v5_stage_a_gold_label_mapping import (
        RULE_ID as LABEL_MAP_RULE,
        admission_invariants,
        validate_row_gold_mapping,
    )

    if sha256_file(DATASET) != DATASET_SHA:
        fail("V1R9 dataset digest mismatch")
    if PARENT_SURFACE.exists():
        parent_sha = sha256_file(PARENT_SURFACE / "EVIDENCE_SURFACE.jsonl")
        if parent_sha != PARENT_DATASET_SHA:
            fail("V1R8 parent digest mismatch")
    else:
        parent_sha = PARENT_DATASET_SHA
    if sudo_sha256(SELECTED) != SELECTED_SHA:
        fail("SELECTED digest mismatch")
    if sudo_sha256(BEST_WEIGHTS) != BEST_SHA:
        fail("BEST mutated")

    readiness = json.loads((SURFACE / "READINESS.json").read_text(encoding="utf-8"))
    if readiness.get("state") != "READY":
        fail("surface not READY")
    settlement = json.loads((RUN / "SETTLEMENT.json").read_text(encoding="utf-8"))
    if settlement.get("disposition") != "SETTLED_FAIL":
        fail("parent disposition mismatch")
    gates = settlement["acceptance_gates"]
    if not gates["false_evidence_entry_rate_on_none"]["pass"]:
        fail("specificity unexpectedly FAIL")
    if not gates["NO_EVIDENCE_recall"]["pass"]:
        fail("NONE recall unexpectedly FAIL")
    if gates["EVIDENCE_PRESENT_recall"]["pass"]:
        fail("PRESENT recall unexpectedly PASS")
    thresh = json.loads((RUN / "THRESHOLD_GRID.json").read_text(encoding="utf-8"))
    if int(thresh.get("n_passing") or 0) != 0:
        fail("threshold grid n_passing nonzero")

    rows = load_jsonl(DATASET)
    invalid_map = sum(1 for row in rows if validate_row_gold_mapping(row))
    admission = admission_invariants(rows)
    if invalid_map or not admission.get("pass", True):
        fail(
            f"label mapping invalid rows:{invalid_map} "
            f"admission:{admission.get('pass')}"
        )

    prov_stats = json.loads(
        (AUTH / "LABEL_PROVENANCE_STATS.json").read_text(encoding="utf-8")
    )
    if int(prov_stats.get("invalid_provenance_rows", 1)) != 0:
        fail("provenance invalid")

    dist = {
        "all": dict(Counter(r["evidence_label"] for r in rows)),
        "train": dict(
            Counter(r["evidence_label"] for r in rows if r.get("split") == "train")
        ),
        "validation": dict(
            Counter(
                r["evidence_label"] for r in rows if r.get("split") == "validation"
            )
        ),
    }
    return {
        "DATA_INTEGRITY": "PASS",
        "LABEL_MAPPING": "PASS" if admission.get("pass") else "FAIL",
        "SURFACE_READY": "PASS",
        "BEST": "UNCHANGED",
        "BEST_SHA256": BEST_SHA,
        "DATASET_SHA256": DATASET_SHA,
        "PARENT_DATASET_SHA256": parent_sha,
        "SELECTED_CHECKPOINT_SHA256": SELECTED_SHA,
        "label_mapping_rule": LABEL_MAP_RULE,
        "label_mapping_admission": {
            "n_invalid": admission.get("n_invalid"),
            "pass": admission.get("pass"),
            "rule": admission.get("rule"),
        },
        "class_distributions": dist,
        "parent_gates": {
            "SPECIFICITY_GATE": "PASS",
            "PRESENT_RECALL_GATE": "FAIL",
            "NONE_RECALL_GATE": "PASS",
            "THRESHOLD_GRID_PASSING": 0,
            "false_evidence_entry_rate_on_none": gates[
                "false_evidence_entry_rate_on_none"
            ]["value"],
            "EVIDENCE_PRESENT_recall": gates["EVIDENCE_PRESENT_recall"]["value"],
            "NO_EVIDENCE_recall": gates["NO_EVIDENCE_recall"]["value"],
        },
        "provenance_invalid_rows": 0,
        "surface_state": readiness.get("state"),
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
    from hyperlexical.classification_v5_stage_a_architecture_investigate import (
        INVESTIGATE_RULE,
        architecture_alternative_cards,
        choose_primary_decision,
        classify_bottleneck,
        classify_present_fn_mode,
        classify_separability,
        cosine,
        decompose_fn_modes,
        mean_vector,
        smallest_reversible_redesign,
    )
    from hyperlexical.eval_forward import apply_encoder_trainable
    from hyperlexical.layout import HIDDEN
    from hyperlexical.save_pretrained import split_weight_tensors

    if DEST.exists() and (DEST / "INVESTIGATION.json").exists():
        fail(f"investigation already sealed:{DEST}")

    baseline = freeze_baseline()
    rows = [r for r in load_jsonl(DATASET) if r.get("split") == "validation"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        fail("CUDA required")

    tokenizer = AutoTokenizer.from_pretrained(str(TRUNK), local_files_only=True)
    tokenizer.padding_side = "right"
    encoder = AutoModel.from_pretrained(str(TRUNK), local_files_only=True)
    warm = split_weight_tensors(load_file(str(BEST_WEIGHTS), device="cpu"))
    if int(apply_encoder_trainable(encoder, warm.get("encoder") or {}).get("loaded") or 0) <= 0:
        fail("BEST overlay empty")
    evidence_head = nn.Linear(HIDDEN, len(EVIDENCE_LABELS))
    packed = split_weight_tensors(load_file(str(SELECTED), device="cpu"))
    if int(apply_encoder_trainable(encoder, packed.get("encoder") or {}).get("loaded") or 0) <= 0:
        fail("SELECTED overlay empty")
    head = packed.get("evidence_head") or {}
    if "weight" not in head or "bias" not in head:
        fail("SELECTED missing evidence_head")
    with torch.no_grad():
        evidence_head.weight.copy_(head["weight"])
        evidence_head.bias.copy_(head["bias"])
    encoder.to(device)
    evidence_head.to(device)
    encoder.eval()
    evidence_head.eval()

    scored = []
    embeddings_by_label: dict[str, list[list[float]]] = defaultdict(list)
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
            emb = pooled[0].detach().cpu().tolist()
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
            families = row.get("active_family_support") or []
            feature_absence = gold == "EVIDENCE_PRESENT" and not families
            item = {
                "P_EVIDENCE_PRESENT": probs["EVIDENCE_PRESENT"],
                "P_NO_EVIDENCE": probs["NO_EVIDENCE"],
                "P_UNCERTAIN": probs["UNCERTAIN"],
                "atom_prose": surface_form(str(row["text"])),
                "condition": condition_key(gold, pred, subtype),
                "decision": pred,
                "embedding": emb,
                "entropy": entropy(probs),
                "evidence_label": gold,
                "evidence_subtype": subtype,
                "feature_absence": feature_absence,
                "identity": row["identity"],
                "margin_present_minus_none": probs["EVIDENCE_PRESENT"]
                - probs["NO_EVIDENCE"],
                "margin_top1_top2": top1[1] - top2[1],
                "provenance": row.get("provenance"),
                "source_family": source_family(row),
                "top1": top1[0],
                "top2": top2[0],
                "topic_domain": row.get("topic_domain") or "unspecified",
            }
            scored.append(item)
            embeddings_by_label[gold].append(emb)

    conf = Counter((i["evidence_label"], i["decision"]) for i in scored)
    for key, want in EXPECTED_CONFUSION.items():
        got = int(conf.get(key) or 0)
        if got != want:
            fail(f"score reconstruct mismatch {key}: got={got} want={want}")

    # Centroid separability (frozen embeddings; no mutation).
    centroids = {
        label: mean_vector(vecs) for label, vecs in embeddings_by_label.items()
    }
    for item in scored:
        sims = {}
        for label, centroid in centroids.items():
            if centroid is None:
                continue
            sims[label] = cosine(item["embedding"], centroid)
        item["centroid_similarity"] = sims
        item["nearest_centroid"] = (
            max(sims.items(), key=lambda kv: kv[1])[0] if sims else None
        )

    present_fn = [
        i
        for i in scored
        if i["evidence_label"] == "EVIDENCE_PRESENT"
        and i["decision"] != "EVIDENCE_PRESENT"
    ]
    for item in present_fn:
        item["fn_mode"] = classify_present_fn_mode(item)

    fn_decomp = decompose_fn_modes(present_fn)
    # Enrich FN decomposition with slices.
    fn_by_prov = Counter(i.get("provenance") or "UNKNOWN" for i in present_fn)
    fn_by_surface = Counter(i.get("atom_prose") for i in present_fn)
    fn_by_source = Counter(i.get("source_family") for i in present_fn)
    fn_by_domain = Counter(i.get("topic_domain") for i in present_fn)
    fn_decomp["by_provenance"] = dict(fn_by_prov)
    fn_decomp["by_ATOM_PROSE"] = dict(fn_by_surface)
    fn_decomp["by_source_family"] = dict(fn_by_source)
    fn_decomp["by_topic_domain"] = dict(fn_by_domain.most_common(20))
    fn_decomp["mean_probabilities"] = {
        "P_EVIDENCE_PRESENT": summarize([i["P_EVIDENCE_PRESENT"] for i in present_fn]),
        "P_NO_EVIDENCE": summarize([i["P_NO_EVIDENCE"] for i in present_fn]),
        "P_UNCERTAIN": summarize([i["P_UNCERTAIN"] for i in present_fn]),
    }
    fn_decomp["entropy"] = summarize([i["entropy"] for i in present_fn])
    fn_decomp["margin_present_minus_none"] = summarize(
        [i["margin_present_minus_none"] for i in present_fn]
    )
    fn_decomp["margin_top1_top2"] = summarize(
        [i["margin_top1_top2"] for i in present_fn]
    )
    fn_decomp["nearest_centroid"] = dict(
        Counter(i.get("nearest_centroid") for i in present_fn)
    )

    pn = (
        cosine(centroids["EVIDENCE_PRESENT"], centroids["NO_EVIDENCE"])
        if centroids.get("EVIDENCE_PRESENT") and centroids.get("NO_EVIDENCE")
        else None
    )
    pu = (
        cosine(centroids["EVIDENCE_PRESENT"], centroids["UNCERTAIN"])
        if centroids.get("EVIDENCE_PRESENT") and centroids.get("UNCERTAIN")
        else None
    )
    fn_nearest_none = (
        sum(1 for i in present_fn if i.get("nearest_centroid") == "NO_EVIDENCE")
        / len(present_fn)
        if present_fn
        else None
    )
    fn_nearest_present = (
        sum(1 for i in present_fn if i.get("nearest_centroid") == "EVIDENCE_PRESENT")
        / len(present_fn)
        if present_fn
        else None
    )
    separability = classify_separability(
        present_none_centroid_cosine=pn,
        present_uncertain_centroid_cosine=pu,
        present_fn_nearest_none_frac=fn_nearest_none,
        present_fn_nearest_present_frac=fn_nearest_present,
    )
    representation = {
        "PRESENT_vs_NONE_centroid_cosine": pn,
        "PRESENT_vs_UNCERTAIN_centroid_cosine": pu,
        "present_fn_nearest_NONE_frac": fn_nearest_none,
        "present_fn_nearest_PRESENT_frac": fn_nearest_present,
        "separability": separability,
        "n_present_embedded": len(embeddings_by_label.get("EVIDENCE_PRESENT") or []),
        "n_none_embedded": len(embeddings_by_label.get("NO_EVIDENCE") or []),
        "n_uncertain_embedded": len(embeddings_by_label.get("UNCERTAIN") or []),
        "note": "Frozen SELECTED encoder CLS embeddings; not mutated.",
    }

    # Confidence profiles.
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
    if fn_conf_none is not None and fn_conf_none >= 0.50:
        present_fn_profile = "CONFIDENT_NONE"
    elif fn_near is not None and fn_near >= 0.50:
        present_fn_profile = "NEAR_BOUNDARY"
    elif present_fn and statistics.fmean(i["P_EVIDENCE_PRESENT"] for i in present_fn) <= 0.35:
        present_fn_profile = "CONFIDENT_NONE_LEANING"
    else:
        present_fn_profile = "MIXED_OR_SOFT"

    uncertain_all = [i for i in scored if i["evidence_label"] == "UNCERTAIN"]
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
    uncertain_policy_invisible = (
        sum(1 for i in uncertain_all if i["decision"] == "UNCERTAIN") == 0
    )

    bottleneck = classify_bottleneck(
        separability=separability,
        present_fn_profile=present_fn_profile,
        uncertain_decision_ignore_frac=unc_decision_ignore,
        focal_already_falsified=FOCAL_FALSIFIED,
    )

    cw = json.loads((AUTH / "CLASS_WEIGHTS.json").read_text(encoding="utf-8"))
    resolved = json.loads(
        (AUTH / "RESOLVED_TRAINING_CONFIG.json").read_text(encoding="utf-8")
    )
    loss_pressure = {
        "hypothesis": (
            "Weighted CE with NONE clipped at 0.5 and high NONE effective mass "
            "encourages NONE dominance / safe abstention away from PRESENT. "
            "P(PRESENT)-only decide_evidence ignores UNCERTAIN mass, collapsing "
            "epistemic UNCERTAIN into NONE at decision time. Focal (Stage-A-003) "
            "already falsified easy-NONE downweighting alone as sufficient."
        ),
        "class_weights": cw.get("class_weights"),
        "effective_counts_train": cw.get("effective_counts"),
        "provenance_multipliers": resolved.get("loss", {}).get("provenance_multipliers"),
        "loss_name": resolved.get("loss", {}).get("name"),
        "focal_already_falsified": FOCAL_FALSIFIED,
        "none_dominance_signals": {
            "present_fn_confident_none_frac": fn_conf_none,
            "present_fn_profile": present_fn_profile,
            "uncertain_policy_invisible": uncertain_policy_invisible,
            "uncertain_top1_ignored_frac": unc_decision_ignore,
        },
        "gradient_objective_note": (
            "Hypothesis only — no gradient dump / retrain. Softmax CE couples "
            "PRESENT and NONE; raising PRESENT pressure reopens false-entry; "
            "current equilibrium favors NONE conservatism after remediation."
        ),
    }

    decision = choose_primary_decision(
        bottleneck=bottleneck,
        separability=separability,
        present_fn_profile=present_fn_profile,
        focal_already_falsified=FOCAL_FALSIFIED,
        uncertain_policy_invisible=uncertain_policy_invisible,
        dataset_change_justified=False,
    )
    redesign = smallest_reversible_redesign(
        primary=decision["PRIMARY_DECISION"],
        bottleneck=bottleneck,
        uncertain_policy_invisible=uncertain_policy_invisible,
        separability=separability,
    )
    alternatives = architecture_alternative_cards()

    # Strip embeddings from persisted score rows (keep hashes/geometry).
    score_rows = []
    for item in scored:
        slim = {k: v for k, v in item.items() if k != "embedding"}
        score_rows.append(slim)

    DEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DEST, 0o700)
    write_private(
        DEST / "VALIDATION_SCORES.jsonl",
        "\n".join(json.dumps(row, sort_keys=True) for row in score_rows) + "\n",
    )
    write_private(DEST / "BASELINE_AUDIT.json", baseline)
    write_private(DEST / "PRESENT_FN_DECOMPOSITION.json", fn_decomp)
    write_private(DEST / "REPRESENTATION_SEPARABILITY.json", representation)
    write_private(DEST / "LOSS_PRESSURE.json", loss_pressure)
    write_private(
        DEST / "ARCHITECTURE_ALTERNATIVES.json",
        {"alternatives": alternatives, "selected_for_train": None},
    )

    investigation = {
        "INVESTIGATION_STATUS": "COMPLETE",
        "INVESTIGATE_RULE": INVESTIGATE_RULE,
        "PARENT_EXPERIMENT": "HLX-CLASSIFICATION-V5-STAGE-A-002",
        "EXPERIMENT_ID": "HLX-CLASSIFICATION-V5-STAGE-A-004",
        "TRAIN": False,
        "RESERVE": "unused",
        "BEST": "UNCHANGED",
        "BEST_SHA256": BEST_SHA,
        "DATASET": "V1R9_UNCHANGED",
        "DATASET_SHA256": DATASET_SHA,
        "SELECTED_CHECKPOINT_SHA256": SELECTED_SHA,
        "SURFACE_RULE": "HYPERLEX_V5_STAGE_A_NEGATIVE_EVIDENCE_SURFACE_V1R9",
        "PRIMARY_DECISION": decision["PRIMARY_DECISION"],
        "BOTTLENECK": bottleneck,
        "SEPARABILITY": separability,
        "PRESENT_TO_NONE_CONFIDENCE_PROFILE": present_fn_profile,
        "THRESHOLD_ONLY_REPAIR_SUPPORTED": False,
        "FOCAL_ALREADY_FALSIFIED": FOCAL_FALSIFIED,
        "UNCERTAIN_POLICY_INVISIBLE": uncertain_policy_invisible,
        "dataset_change_required": decision["dataset_change_required"],
        "architecture_change_required": decision["architecture_change_required"],
        "new_experiment_required": decision["new_experiment_required"],
        "NEXT_ACTION": decision["NEXT_ACTION"],
        "smallest_reversible_redesign": redesign,
        "architecture_alternatives": alternatives,
        "baseline": baseline,
        "present_fn_decomposition": {
            "n": fn_decomp["n"],
            "counts": fn_decomp["counts"],
            "percentages": fn_decomp["percentages"],
            "by_provenance": fn_decomp["by_provenance"],
            "by_ATOM_PROSE": fn_decomp["by_ATOM_PROSE"],
            "nearest_centroid": fn_decomp["nearest_centroid"],
            "mean_P_PRESENT": fn_decomp["mean_probabilities"]["P_EVIDENCE_PRESENT"].get(
                "mean"
            ),
            "mean_P_NONE": fn_decomp["mean_probabilities"]["P_NO_EVIDENCE"].get("mean"),
            "median_P_NONE": fn_decomp["mean_probabilities"]["P_NO_EVIDENCE"].get(
                "median"
            ),
            "confident_none_frac": fn_conf_none,
            "near_boundary_frac": fn_near,
        },
        "representation": representation,
        "loss_pressure": loss_pressure,
        "head_analysis": {
            "type": "linear_hidden_to_3_logits",
            "pooling": "last_hidden_state[:,0]",
            "decision_rule": "decide_evidence(P_PRESENT only); P_UNCERTAIN unused",
            "bottleneck": bottleneck,
        },
        "schema": "hyperlex.classification.v5.stage_a_architecture_investigation.v1r9",
    }
    # receipt hash without nested huge blobs already slim
    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text

    investigation["receipt_sha256"] = sha256_text(
        canonical_json(
            {k: v for k, v in investigation.items() if k != "receipt_sha256"}
        )
    )
    write_private(DEST / "INVESTIGATION.json", investigation)

    summary = {
        "INVESTIGATION_STATUS": "COMPLETE",
        "PRIMARY_DECISION": decision["PRIMARY_DECISION"],
        "BOTTLENECK": bottleneck,
        "SEPARABILITY": separability,
        "NEXT_ACTION": decision["NEXT_ACTION"],
        "dataset_change_required": decision["dataset_change_required"],
        "architecture_change_required": decision["architecture_change_required"],
        "new_experiment_required": decision["new_experiment_required"],
        "TRAIN": False,
        "BEST": "UNCHANGED",
        "RESERVE": "unused",
        "receipt_sha256": investigation["receipt_sha256"],
        "SELECTED_CHECKPOINT_SHA256": SELECTED_SHA,
        "DATASET_SHA256": DATASET_SHA,
        "smallest_reversible_redesign": redesign["change_id"],
        "private_diag_dir": str(DEST),
    }
    write_private(DEST / "SUMMARY.json", summary)

    # Public mirrors (no row bodies / embeddings).
    write_repo(REPO_ARTIFACTS / "architecture_investigate_summary.json", summary)
    write_repo(
        REPO_ARTIFACTS / "architecture_investigate_receipt.json",
        {
            "PRIMARY_DECISION": decision["PRIMARY_DECISION"],
            "BOTTLENECK": bottleneck,
            "SEPARABILITY": separability,
            "NEXT_ACTION": decision["NEXT_ACTION"],
            "dataset_change_required": decision["dataset_change_required"],
            "architecture_change_required": decision["architecture_change_required"],
            "new_experiment_required": decision["new_experiment_required"],
            "receipt_sha256": investigation["receipt_sha256"],
            "SELECTED_CHECKPOINT_SHA256": SELECTED_SHA,
            "DATASET_SHA256": DATASET_SHA,
            "TRAIN": False,
            "BEST": "UNCHANGED",
            "smallest_reversible_redesign": redesign["change_id"],
        },
    )

    auth = json.loads((AUTH / "AUTHORIZATION.json").read_text(encoding="utf-8"))
    auth["NEXT_ACTION"] = decision["NEXT_ACTION"]
    auth["ARCHITECTURE_PRIMARY_DECISION"] = decision["PRIMARY_DECISION"]
    auth["architecture_investigation_receipt_sha256"] = investigation["receipt_sha256"]
    write_private(AUTH / "AUTHORIZATION.json", auth)

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V5_STAGE_A_ARCH_INNER") == "1":
        return score_inner()
    # Host preflight without torch.
    freeze_baseline()
    if DEST.exists() and (DEST / "INVESTIGATION.json").exists():
        fail(f"investigation already sealed:{DEST}")
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
        "HLX_V5_STAGE_A_ARCH_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={os.environ.get('HLX_V5_STAGE_A_CODE_REVISION', '')}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(
            REPO
            / "scripts/spark/run_classification_v5_stage_a_v1r9_architecture_investigate.py"
        ),
    ]
    print(json.dumps({"launch": cmd[-1], "image": IMAGE}, sort_keys=True), flush=True)
    log_path = AUTH / "architecture_investigate_console.log"
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(
            cmd, check=False, stdout=handle, stderr=subprocess.STDOUT
        )
    try:
        print(log_path.read_text(encoding="utf-8")[-12000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
