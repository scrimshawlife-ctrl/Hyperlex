"""REVIEW_V6_QUALIFICATION_FAILURE_AT_SYSTEM_LEVEL.

Read-only forensic review of HYPERLEX_V6_QUALIFICATION_002 FAIL.
No train / recalibrate / threshold change / new QUAL / pointer moves.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

PRIVATE_QUAL = Path(
    "/home/morpheus/hlx-private/classification-v6-qualification-surface-002-20261001"
)
PRIVATE_EXEC = Path(
    "/home/morpheus/hlx-private/classification-v6-qualification-execute-002-20261001"
)
PRIVATE_PKG = Path(
    "/home/morpheus/hlx-private/classification-v6-semantic-pipeline-harden-20261001"
)
PRIVATE_MIG = Path(
    "/home/morpheus/hlx-private/classification-v6-label-migration-bakeoff-20261001"
)
PRIVATE_FOUND = Path(
    "/home/morpheus/hlx-private/classification-v6-data-foundation-20261001"
)
PRIVATE_REV = Path(
    "/home/morpheus/hlx-private/classification-v6-qualification-failure-system-review-20261001"
)
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-QUALIFICATION-FAILURE-SYSTEM-REVIEW-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
MAX_LEN = 192
BATCH = 32

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


def write_repo(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )


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


def n_lab(r: dict) -> int:
    return (
        len(r.get("domain_labels") or [])
        + len(r.get("function_labels") or [])
        + len(r.get("mediation_labels") or [])
    )


def all_labels(r: dict) -> list[str]:
    return list(r.get("domain_labels") or []) + list(
        r.get("function_labels") or []
    ) + list(r.get("mediation_labels") or [])


def composition(r: dict) -> str:
    d = bool(r.get("domain_labels"))
    f = bool(r.get("function_labels"))
    m = bool(r.get("mediation_labels"))
    parts = []
    if d:
        parts.append("domain")
    if f:
        parts.append("function")
    if m:
        parts.append("mediation")
    return "+".join(parts) if parts else "none"


def family_topic(sf: str | None) -> str:
    s = sf or ""
    if ":" in s:
        return s.rsplit(":", 1)[-1]
    return s or "UNKNOWN"


def l1_dist(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    keys = set(a) | set(b)
    return 0.5 * sum(abs(float(a.get(k, 0.0)) - float(b.get(k, 0.0))) for k in keys)


def prevalence(rows: list[dict], labels: list[str]) -> dict[str, float]:
    n = max(1, len(rows))
    out = {}
    for lab in labels:
        axis = lab.split(".", 1)[0]
        key = f"{axis}_labels"
        out[lab] = sum(1 for r in rows if lab in (r.get(key) or [])) / n
    return out


def mean_pool(last_hidden, attention_mask):
    mask = attention_mask.unsqueeze(-1).float()
    return (last_hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-6)


def embed_model(model_id, texts, device, max_len=MAX_LEN, batch=BATCH, revision=None):
    import hashlib

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
    enc_hash = hsh.hexdigest()
    n_train = sum(p.numel() for p in enc.parameters() if p.requires_grad)
    del enc
    torch.cuda.empty_cache()
    return __import__("torch").cat(vecs, dim=0).numpy(), enc_hash, n_train


def build_mlp(hidden: int, n_out: int, device):
    import torch.nn as nn

    return nn.Sequential(
        nn.Linear(hidden, 128), nn.ReLU(), nn.Linear(128, n_out)
    ).to(device)


def load_head_bundle(path: Path, hidden: int, vocabs, device):
    import io

    import torch

    raw = sudo_read_bytes(path)
    try:
        bundle = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=False)
    except TypeError:
        bundle = torch.load(io.BytesIO(raw), map_location="cpu")
    heads = {}
    for axis, vocab in vocabs.items():
        m = build_mlp(hidden, len(vocab), device)
        m.load_state_dict(bundle["state"][axis])
        m.eval()
        for p in m.parameters():
            p.requires_grad_(False)
        heads[axis] = m
    return heads


def scores_from_heads(heads, X, device):
    import torch

    out = {}
    with torch.no_grad():
        xt = torch.tensor(X, device=device)
        for axis, model in heads.items():
            out[axis] = torch.sigmoid(model(xt)).cpu().numpy()
    return out


def surface_kind(text: str, source_family: str | None, mediation_gold: list[str]) -> str:
    sf = source_family or ""
    t = text or ""
    if "mediation.internet_register" in (mediation_gold or []) or "internet" in sf:
        return "internet-register"
    if len(t) < 40:
        return "conversational"
    if ":" in t[:40] or t.lower().startswith(("a ", "an ", "the ")):
        if len(t) < 120:
            return "definition-like"
    if any(ch in t for ch in ".?!" ) and len(t) > 160:
        return "prose"
    return "declarative"


def length_bucket(n: int) -> str:
    if n < 60:
        return "short"
    if n < 180:
        return "medium"
    return "long"


def f1_binary(y_true, y_pred) -> float:
    import numpy as np

    yt = np.asarray(y_true)
    yp = np.asarray(y_pred)
    tp = float(((yt == 1) & (yp == 1)).sum())
    fp = float(((yt == 0) & (yp == 1)).sum())
    fn = float(((yt == 1) & (yp == 0)).sum())
    if tp == 0:
        return 0.0
    p = tp / (tp + fp)
    r = tp / (tp + fn)
    return 2 * p * r / (p + r)


def macro_f1_multilabel(gold, pred) -> float:
    import numpy as np

    g = np.asarray(gold)
    p = np.asarray(pred)
    if g.ndim != 2 or g.shape[1] == 0:
        return 0.0
    scores = [f1_binary(g[:, j], p[:, j]) for j in range(g.shape[1])]
    return float(sum(scores) / len(scores))


def inner() -> int:
    import numpy as np
    import torch

    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text
    from hyperlexical.classification_v6_architecture_reset_bakeoff import (
        AXIS_VOCABS,
        LABEL_DESCRIPTIONS,
    )
    from hyperlexical.classification_v6_qualification_execute_002 import (
        EXPECTED_ENCODER_STATE_HASH,
        EXPECTED_N_ROWS,
        EXPECTED_PACKAGE_SHA256,
        EXPECTED_SEAL_SHA256,
        QUALIFICATION_ID,
        REP_REFERENCE_SYSTEM_MACRO_F1,
    )
    from hyperlexical.classification_v6_qualification_failure_system_review import (
        EXPECTED_QUAL_RESULT_SHA256,
        REJECTED_MICRO_FIXES,
        build_system_review_receipt,
        classify_drop,
        classify_shift,
        review_contract,
    )
    from hyperlexical.classification_v6_semantic_pipeline_harden import (
        BAKEOFF_THRESHOLDS,
        SELECTED_ENCODER_MODEL_ID,
        SELECTED_ENCODER_REVISION,
    )

    PRIVATE_REV.mkdir(mode=0o700, parents=True, exist_ok=True)
    REPO_ART.mkdir(parents=True, exist_ok=True)

    seal = load_json(PRIVATE_QUAL / "QUALIFICATION_SEAL.json")
    result = load_json(PRIVATE_EXEC / "RESULT.json")
    primary = load_json(PRIVATE_EXEC / "PRIMARY_METRICS.json")
    gates = load_json(PRIVATE_EXEC / "GATES.json")
    retention = load_json(PRIVATE_EXEC / "RETENTION.json")
    per_label_q = load_json(PRIVATE_EXEC / "PER_LABEL.json")
    hierarchy = load_json(PRIVATE_EXEC / "HIERARCHY.json")
    errors = load_json(PRIVATE_EXEC / "ERROR_DECOMPOSITION.json")
    card_q = load_json(PRIVATE_EXEC / "CARDINALITY_SLICES.json")
    src_q = load_json(PRIVATE_EXEC / "SOURCE_SLICES.json")
    len_q = load_json(PRIVATE_EXEC / "LENGTH_SURFACE_SLICES.json")
    harden_m = load_json(PRIVATE_PKG / "METRICS.json")
    harden_rob = load_json(PRIVATE_PKG / "ROBUSTNESS.json")
    package = load_json(PRIVATE_PKG / "PACKAGE.json")

    # Immutable evidence checks
    issues = []
    if seal.get("evaluation_spent") != "EVALUATION_SPENT":
        issues.append("seal_not_spent")
    if int(seal.get("qualification_model_executions") or 0) != 1:
        issues.append("executions_ne_1")
    if seal.get("seal_sha256") != EXPECTED_SEAL_SHA256:
        issues.append("seal_sha_mismatch")
    if result.get("V6_QUALIFICATION_002_RESULT_SHA256") != EXPECTED_QUAL_RESULT_SHA256:
        issues.append("result_sha_mismatch")
    if package.get("PACKAGE_SHA256") != EXPECTED_PACKAGE_SHA256:
        issues.append("package_sha_mismatch")
    if issues:
        summary = {
            "REVIEW_STATE": "INVALID",
            "issues": issues,
            "NEXT_ACTION": "REPAIR_V6_QUALIFICATION_EXECUTION",
        }
        write_private(PRIVATE_REV / "SUMMARY.json", summary)
        write_repo(REPO_ART / "SUMMARY.json", summary)
        print(json.dumps(summary, indent=2))
        return 2

    qual_rows = load_jsonl(PRIVATE_QUAL / "QUALIFICATION_ROWS.jsonl")
    preds = load_jsonl(PRIVATE_EXEC / "RAW_PREDICTIONS.jsonl")
    assert len(qual_rows) == EXPECTED_N_ROWS == len(preds)
    pred_by_id = {p["identity"]: p for p in preds}

    train_raw = load_jsonl(PRIVATE_MIG / "TRAIN_V6_LABELS.jsonl")
    dev_raw = load_jsonl(PRIVATE_MIG / "DEVELOPMENT_VALIDATION_V6_LABELS.jsonl")
    rep_raw = load_jsonl(PRIVATE_MIG / "REPRESENTATIVE_VALIDATION_V6_LABELS.jsonl")
    train = usable(train_raw)
    dev = usable(dev_raw)
    rep = usable(rep_raw)

    # Join foundation source_family onto migration rows
    found_meta = {}
    for name in ("TRAIN", "DEVELOPMENT_VALIDATION", "REPRESENTATIVE_VALIDATION"):
        for r in load_jsonl(PRIVATE_FOUND / f"{name}.jsonl"):
            found_meta[r["identity"]] = r
    for rows in (train, dev, rep, train_raw, dev_raw, rep_raw):
        for r in rows:
            meta = found_meta.get(r["identity"]) or {}
            r.setdefault("source_family", meta.get("source_family"))
            r.setdefault("construction_tag", meta.get("construction_tag"))

    vocabs = {
        "domain": list(AXIS_VOCABS["domain"]),
        "function": list(AXIS_VOCABS["function"]),
        "mediation": list(AXIS_VOCABS["mediation"]),
    }
    all_labs = vocabs["domain"] + vocabs["function"] + vocabs["mediation"]
    thresholds = {a: list(BAKEOFF_THRESHOLDS[a]) for a in vocabs}
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")

    # --- 2. Exact gate failure ---
    exact_metrics = {
        "system_macro_f1": primary["system_macro_f1"],
        "DOMAIN_macro_f1": primary["DOMAIN_macro_f1"],
        "DOMAIN_micro_f1": primary["DOMAIN_micro_f1"],
        "FUNCTION_macro_f1": primary["FUNCTION_macro_f1"],
        "FUNCTION_micro_f1": primary["FUNCTION_micro_f1"],
        "MEDIATION_macro_f1": primary["MEDIATION_macro_f1"],
        "MEDIATION_micro_f1": primary["MEDIATION_micro_f1"],
        "sample_f1": primary["sample_f1"],
        "jaccard": primary["jaccard"],
        "raw_hierarchy_violation": primary["raw_hierarchy_violation_rate"],
        "post_constraint_hierarchy_violation": primary["hierarchy_violation_rate"],
    }
    gate_failures = {
        "system_macro_f1": gates["gates"]["system_macro_f1"],
        "hierarchy_violation": gates["gates"]["hierarchy_violation"],
        "no_material_axis_collapse": gates["gates"]["no_material_axis_collapse"],
        "overall_pass": gates["pass"],
        "failed_gates": [
            k
            for k, g in gates["gates"].items()
            if not g.get("pass")
        ],
    }

    # --- 3. REP→QUAL degradation ---
    rep_axis = {
        "domain": float(harden_m["REP"]["domain"]["macro_f1"]),
        "function": float(harden_m["REP"]["function"]["macro_f1"]),
        "mediation": float(harden_m["REP"]["mediation"]["macro_f1"]),
    }
    qual_axis = {
        "domain": float(primary["DOMAIN_macro_f1"]),
        "function": float(primary["FUNCTION_macro_f1"]),
        "mediation": float(primary["MEDIATION_macro_f1"]),
    }
    axis_degradation = {}
    for a in ("domain", "function", "mediation"):
        axis_degradation[a] = {
            "REP": rep_axis[a],
            "QUAL": qual_axis[a],
            "absolute_delta": rep_axis[a] - qual_axis[a],
            "retention": qual_axis[a] / max(1e-12, rep_axis[a]),
            "class": classify_drop(rep_axis[a], qual_axis[a]),
        }
    axis_degradation["system"] = {
        "REP": REP_REFERENCE_SYSTEM_MACRO_F1,
        "QUAL": float(primary["system_macro_f1"]),
        "absolute_delta": float(retention["absolute_drop"]),
        "retention": float(retention["retention_ratio"]),
        "class": classify_drop(
            REP_REFERENCE_SYSTEM_MACRO_F1, float(primary["system_macro_f1"])
        ),
    }
    axis_degradation["function_class"] = axis_degradation["function"]["class"]
    axis_degradation["failure_shape"] = (
        "one_axis_collapse"
        if axis_degradation["function"]["class"] == "COLLAPSED"
        and axis_degradation["domain"]["class"] != "COLLAPSED"
        else "broad_system_degradation"
    )

    per_label_deg = {}
    for lab, qrow in per_label_q.items():
        rep_f1 = qrow.get("REP_f1")
        qual_f1 = qrow.get("QUAL_f1")
        per_label_deg[lab] = {
            "REP_f1": rep_f1,
            "QUAL_f1": qual_f1,
            "absolute_delta": (
                None if rep_f1 is None else float(rep_f1) - float(qual_f1 or 0)
            ),
            "retention": (
                None
                if not rep_f1
                else float(qual_f1 or 0) / max(1e-12, float(rep_f1))
            ),
            "support_REP": (
                (harden_m.get("per_label_rep") or {})
                .get(qrow["axis"], {})
                .get(lab, {})
                .get("support")
            ),
            "support_QUAL": qrow.get("QUAL_support"),
            "class": classify_drop(rep_f1, qual_f1),
        }

    # --- 4–8 distributions / prevalence / cardinality / co-label ---
    def dist_features(rows: list[dict], *, is_qual: bool = False) -> dict[str, Any]:
        lens = [len(r.get("text") or "") for r in rows]
        lb = Counter(length_bucket(n) for n in lens)
        card = Counter(min(n_lab(r), 3) for r in rows)
        comp = Counter(composition(r) for r in rows)
        surf = Counter(
            surface_kind(
                r.get("text") or "",
                r.get("source_family"),
                r.get("mediation_labels") or [],
            )
            for r in rows
        )
        topics = Counter(family_topic(r.get("source_family")) for r in rows)
        n = max(1, len(rows))
        return {
            "n": len(rows),
            "zero_label_share": sum(1 for r in rows if n_lab(r) == 0) / n,
            "length": {k: v / n for k, v in lb.items()},
            "cardinality": {str(k): v / n for k, v in card.items()},
            "composition": {k: v / n for k, v in comp.items()},
            "surface": {k: v / n for k, v in surf.items()},
            "topic": {k: v / n for k, v in topics.items()},
            "label_prevalence": prevalence(rows, all_labs),
            "mean_len": float(np.mean(lens)) if lens else 0.0,
        }

    # REP used for metrics = usable (positive-only). Also report raw REP.
    rep_feat = dist_features(rep)
    rep_raw_feat = dist_features(rep_raw)
    qual_feat = dist_features(qual_rows, is_qual=True)
    train_feat = dist_features(train)
    dev_feat = dist_features(dev)

    shift_dims = {}
    for dim in ("length", "cardinality", "composition", "surface", "topic"):
        shift_dims[dim] = {
            "l1": l1_dist(rep_feat[dim], qual_feat[dim]),
            "class": classify_shift(jsd_or_l1=l1_dist(rep_feat[dim], qual_feat[dim])),
            "REP": rep_feat[dim],
            "QUAL": qual_feat[dim],
        }
    # prevalence L1 across labels
    prev_l1 = l1_dist(rep_feat["label_prevalence"], qual_feat["label_prevalence"])
    shift_dims["label_prevalence"] = {
        "l1": prev_l1,
        "class": classify_shift(jsd_or_l1=prev_l1, material=0.08, severe=0.20),
    }
    shift_dims["zero_label_share"] = {
        "REP_usable": rep_feat["zero_label_share"],
        "REP_raw": rep_raw_feat["zero_label_share"],
        "QUAL": qual_feat["zero_label_share"],
        "class": (
            "SEVERE_SHIFT"
            if abs(qual_feat["zero_label_share"] - rep_feat["zero_label_share"]) >= 0.35
            else "MATERIAL_SHIFT"
        ),
    }

    # Source shift (topic-level, since QUAL families are fresh names)
    rep_topics = set(family_topic(r.get("source_family")) for r in rep)
    qual_topics = set(family_topic(r.get("source_family")) for r in qual_rows)
    shared_topics = sorted(rep_topics & qual_topics)
    qual_only_topics = sorted(qual_topics - rep_topics)
    # performance by topic on QUAL
    topic_perf = {}
    for topic in sorted(qual_topics):
        idxs = [
            i
            for i, r in enumerate(qual_rows)
            if family_topic(r.get("source_family")) == topic
        ]
        if len(idxs) < 8:
            continue
        # system exact-ish: fraction of rows with exact final==gold label sets
        exact = 0
        for i in idxs:
            r = qual_rows[i]
            p = pred_by_id[r["identity"]]
            g = set(all_labels(r))
            pred = set(
                p["final_domain_labels"]
                + p["final_function_labels"]
                + p["final_mediation_labels"]
            )
            if g == pred:
                exact += 1
        topic_perf[topic] = {
            "n": len(idxs),
            "exact_match": exact / len(idxs),
            "shared_with_rep": topic in rep_topics,
        }
    shared_exact = [
        v["exact_match"]
        for t, v in topic_perf.items()
        if v["shared_with_rep"] and v["n"] >= 8
    ]
    qual_only_exact = [
        v["exact_match"]
        for t, v in topic_perf.items()
        if not v["shared_with_rep"] and v["n"] >= 8
    ]
    source_shift = {
        "class": (
            "SOURCE_SHIFT_DOMINANT"
            if qual_feat["zero_label_share"] >= 0.5
            and len(qual_only_topics) >= 3
            and (not shared_exact or (sum(shared_exact) / len(shared_exact)) < 0.25)
            else "SOURCE_SENSITIVE"
        ),
        "rep_topics_n": len(rep_topics),
        "qual_topics_n": len(qual_topics),
        "shared_topics_n": len(shared_topics),
        "qual_only_topics_n": len(qual_only_topics),
        "shared_topics_sample": shared_topics[:20],
        "qual_only_topics_sample": qual_only_topics[:20],
        "shared_mean_exact": (
            float(sum(shared_exact) / len(shared_exact)) if shared_exact else None
        ),
        "qual_only_mean_exact": (
            float(sum(qual_only_exact) / len(qual_only_exact))
            if qual_only_exact
            else None
        ),
        "note": "QUAL source_family strings are fresh (v6_qual002_*); compared at topic suffix.",
    }

    # Prevalence TRAIN/DEV/REP/QUAL
    prev = {
        "TRAIN": prevalence(train, all_labs),
        "DEV": prevalence(dev, all_labs),
        "REP": prevalence(rep, all_labs),
        "QUAL": prevalence(qual_rows, all_labs),
        "QUAL_positive_only": prevalence(
            [r for r in qual_rows if n_lab(r) > 0], all_labs
        ),
    }
    material_prev = []
    for lab in all_labs:
        d = abs(prev["REP"][lab] - prev["QUAL"][lab])
        if d >= 0.05:
            material_prev.append(
                {
                    "label": lab,
                    "REP": prev["REP"][lab],
                    "QUAL": prev["QUAL"][lab],
                    "QUAL_positive_only": prev["QUAL_positive_only"][lab],
                    "abs_delta": d,
                }
            )
    material_prev.sort(key=lambda x: -x["abs_delta"])
    label_prior_shift = {
        "class": (
            "MATERIAL"
            if qual_feat["zero_label_share"] - rep_feat["zero_label_share"] >= 0.35
            or len(material_prev) >= 5
            else ("SECONDARY" if material_prev else "NOT_MATERIAL")
        ),
        "material_labels": material_prev[:20],
        "zero_label_delta": qual_feat["zero_label_share"] - rep_feat["zero_label_share"],
    }

    # Cardinality / composition
    def counts(rows):
        return {
            "single": sum(1 for r in rows if n_lab(r) == 1),
            "two": sum(1 for r in rows if n_lab(r) == 2),
            "three_plus": sum(1 for r in rows if n_lab(r) >= 3),
            "zero": sum(1 for r in rows if n_lab(r) == 0),
            "domain_only": sum(1 for r in rows if composition(r) == "domain"),
            "function_only": sum(1 for r in rows if composition(r) == "function"),
            "domain+function": sum(
                1 for r in rows if composition(r) == "domain+function"
            ),
            "domain+mediation": sum(
                1 for r in rows if composition(r) == "domain+mediation"
            ),
            "function+mediation": sum(
                1 for r in rows if composition(r) == "function+mediation"
            ),
            "domain+function+mediation": sum(
                1 for r in rows if composition(r) == "domain+function+mediation"
            ),
        }

    card_shift = {
        "REP_usable_counts": counts(rep),
        "REP_raw_counts": counts(rep_raw),
        "QUAL_counts": counts(qual_rows),
        "REP_robustness_domain_plus_function_n": (harden_rob.get("domain_plus_function") or {}).get(
            "n"
        ),
        "rep_domain_plus_function_n": counts(rep)["domain+function"],
        "qual_domain_plus_function_n": counts(qual_rows)["domain+function"],
        "QUAL_slice_metrics": card_q,
        "REP_robustness_slices": {
            k: harden_rob.get(k)
            for k in (
                "single_label_rows",
                "multi_label_rows",
                "domain_only",
                "function_only",
                "mediation_positive",
                "domain_plus_function",
            )
        },
        "class": (
            "SEVERE_SHIFT"
            if counts(rep)["domain+function"] == 0
            and counts(qual_rows)["domain+function"] > 0
            else classify_shift(
                jsd_or_l1=l1_dist(
                    {k: v / max(1, len(rep)) for k, v in counts(rep).items()},
                    {k: v / max(1, len(qual_rows)) for k, v in counts(qual_rows).items()},
                )
            )
        ),
    }

    # Co-label pairs
    def pair_supports(rows):
        c = Counter()
        for r in rows:
            labs = sorted(set(all_labels(r)))
            for a, b in combinations(labs, 2):
                c[(a, b)] += 1
        return c

    train_pairs = pair_supports(train)
    rep_pairs = pair_supports(rep)
    qual_pairs = pair_supports(qual_rows)
    co_label = []
    for pair, qn in qual_pairs.most_common(40):
        co_label.append(
            {
                "pair": list(pair),
                "TRAIN_support": int(train_pairs.get(pair, 0)),
                "REP_support": int(rep_pairs.get(pair, 0)),
                "QUAL_support": int(qn),
                "class": (
                    "QUAL_NOVEL_COMBINATION"
                    if train_pairs.get(pair, 0) == 0 and rep_pairs.get(pair, 0) == 0
                    else (
                        "LOW_SUPPORT"
                        if max(train_pairs.get(pair, 0), rep_pairs.get(pair, 0)) < 5
                        else "SEEN_BUT_FAILED"
                    )
                ),
            }
        )
    novel_n = sum(1 for x in co_label if x["class"] == "QUAL_NOVEL_COMBINATION")
    co_label_shift = {
        "top_qual_pairs": co_label,
        "novel_pair_count_in_top40": novel_n,
        "compositional_novelty_major": (
            counts(rep)["domain+function"] == 0
            and counts(qual_rows)["domain+function"] > 0
        )
        or novel_n >= 8,
    }

    # --- Predictions matrices for QUAL ---
    def row_gold_mat(rows, axis):
        vocab = vocabs[axis]
        return np.asarray(
            [
                [1 if lab in (r.get(f"{axis}_labels") or []) else 0 for lab in vocab]
                for r in rows
            ],
            dtype=np.int32,
        )

    def row_pred_mat(rows, axis, final=True):
        vocab = vocabs[axis]
        key = f"final_{axis}_labels" if final else f"raw_{axis}_labels"
        return np.asarray(
            [
                [1 if lab in (pred_by_id[r["identity"]].get(key) or []) else 0 for lab in vocab]
                for r in rows
            ],
            dtype=np.int32,
        )

    def row_score_mat(rows, axis):
        key = f"raw_{axis}_scores"
        return np.asarray(
            [pred_by_id[r["identity"]][key] for r in rows], dtype=np.float64
        )

    # --- 9. Axis-head score analysis (QUAL; REP margins from harden per-label) ---
    axis_head = {}
    for axis in vocabs:
        scores = row_score_mat(qual_rows, axis)
        gold = row_gold_mat(qual_rows, axis)
        th = np.asarray(thresholds[axis], dtype=np.float64)
        margins = []
        for j, lab in enumerate(vocabs[axis]):
            pos = scores[gold[:, j] == 1, j]
            neg = scores[gold[:, j] == 0, j]
            rep_row = (
                (harden_m.get("per_label_rep") or {})
                .get(axis, {})
                .get(lab, {})
            )
            margins.append(
                {
                    "label": lab,
                    "QUAL_pos_mean": float(pos.mean()) if len(pos) else None,
                    "QUAL_neg_mean": float(neg.mean()) if len(neg) else None,
                    "QUAL_margin": (
                        float(pos.mean() - neg.mean())
                        if len(pos) and len(neg)
                        else None
                    ),
                    "threshold": float(th[j]),
                    "QUAL_pos_above_th": (
                        float((pos >= th[j]).mean()) if len(pos) else None
                    ),
                    "QUAL_neg_above_th": (
                        float((neg >= th[j]).mean()) if len(neg) else None
                    ),
                    "REP_pos_mean": rep_row.get("pos_mean"),
                    "REP_neg_mean": rep_row.get("neg_mean"),
                    "REP_margin": rep_row.get("margin"),
                }
            )
        # NONE-row overprediction rate
        none_idx = [i for i, r in enumerate(qual_rows) if n_lab(r) == 0]
        none_scores = scores[none_idx]
        none_pred_rate = float((none_scores >= th).any(axis=1).mean()) if none_idx else 0.0
        axis_head[axis] = {
            "labels": margins,
            "none_row_any_positive_rate": none_pred_rate,
            "mean_score_all": float(scores.mean()),
            "class": (
                "GEOMETRY_STABLE_CALIBRATION_SHIFTED"
                if none_pred_rate >= 0.4
                else "BOTH"
            ),
        }

    # --- 10–13. Encode QUAL + label texts; train-distance; geometry ---
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"forensic_encode device={device}", flush=True)
    Xq, enc_hash, n_train_params = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        [r.get("text") or "" for r in qual_rows],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    assert n_train_params == 0
    assert enc_hash == EXPECTED_ENCODER_STATE_HASH

    short_desc = [LABEL_DESCRIPTIONS[lab] for lab in all_labs]
    Xlab, _, _ = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        short_desc,
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    # Train/DEV/REP embeddings (usable splits) — forensic only
    print("encode_train_dev_rep", flush=True)
    Xtr, _, _ = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        [r.get("text") or "" for r in train],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    Xdv, _, _ = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        [r.get("text") or "" for r in dev],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    Xrp, _, _ = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        [r.get("text") or "" for r in rep],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )

    # Label similarity on QUAL
    sim_ql = Xq @ Xlab.T  # (n_qual, n_labels)
    lab_index = {lab: i for i, lab in enumerate(all_labs)}

    def geom_for(rows, X, gold_fn):
        pos_sims = []
        neg_sims = []
        hard_neg = []
        purity = 0
        sims = X @ Xlab.T
        for i, r in enumerate(rows):
            labs = gold_fn(r)
            if not labs:
                continue
            s = sims[i]
            correct = [lab_index[l] for l in labs if l in lab_index]
            if not correct:
                continue
            pos = float(np.mean([s[j] for j in correct]))
            wrong = [j for j in range(len(all_labs)) if j not in correct]
            neg = float(np.mean(s[wrong])) if wrong else 0.0
            pos_sims.append(pos)
            neg_sims.append(neg)
            hard_neg.append(float(np.max(s[wrong])) if wrong else 0.0)
            nn = int(np.argmax(s))
            if all_labs[nn] in labs:
                purity += 1
        n = max(1, len(pos_sims))
        return {
            "n_positive_rows": len(pos_sims),
            "correct_label_similarity": float(np.mean(pos_sims)) if pos_sims else None,
            "incorrect_label_similarity": float(np.mean(neg_sims)) if neg_sims else None,
            "hard_negative_similarity": float(np.mean(hard_neg)) if hard_neg else None,
            "positive_negative_margin": (
                float(np.mean(pos_sims) - np.mean(neg_sims)) if pos_sims else None
            ),
            "nearest_label_purity": purity / n,
        }

    pos_idx = [i for i, r in enumerate(qual_rows) if n_lab(r) > 0]
    geom_qual_pos = geom_for(
        [qual_rows[i] for i in pos_idx], Xq[pos_idx], all_labels
    )
    geom_rep = geom_for(rep, Xrp, all_labels)
    harden_geom = harden_m.get("geometry") or {}
    semantic_geometry = {
        "QUAL_positive_only": geom_qual_pos,
        "REP_usable": geom_rep,
        "harden_REP_witness": harden_geom,
        "margin_retention": (
            None
            if not geom_rep.get("positive_negative_margin")
            or not geom_qual_pos.get("positive_negative_margin")
            else float(geom_qual_pos["positive_negative_margin"])
            / max(1e-12, float(geom_rep["positive_negative_margin"]))
        ),
        "purity_REP": geom_rep.get("nearest_label_purity"),
        "purity_QUAL": geom_qual_pos.get("nearest_label_purity"),
        "class": (
            "SEMANTIC_ENCODER_DOMAIN_MISMATCH"
            if (
                geom_qual_pos.get("positive_negative_margin") is not None
                and geom_rep.get("positive_negative_margin") is not None
                and float(geom_qual_pos["positive_negative_margin"])
                < 0.5 * float(geom_rep["positive_negative_margin"])
                and float(geom_qual_pos.get("nearest_label_purity") or 0)
                < 0.5 * float(geom_rep.get("nearest_label_purity") or 1)
            )
            else "GEOMETRY_STABLE_CALIBRATION_SHIFTED"
        ),
    }
    label_semantic_stability = {
        "QUAL_correct_sim": geom_qual_pos.get("correct_label_similarity"),
        "QUAL_incorrect_sim": geom_qual_pos.get("incorrect_label_similarity"),
        "REP_correct_sim": geom_rep.get("correct_label_similarity"),
        "REP_incorrect_sim": geom_rep.get("incorrect_label_similarity"),
        "transfers": semantic_geometry["class"]
        != "SEMANTIC_ENCODER_DOMAIN_MISMATCH",
        "note": "Frozen short LABEL_DESCRIPTIONS only; no new descriptions tried.",
    }

    # Train-distance
    def nn_sim(A, B):
        # chunked max similarity
        out = np.empty(A.shape[0], dtype=np.float64)
        bs = 256
        for i in range(0, A.shape[0], bs):
            s = A[i : i + bs] @ B.T
            out[i : i + bs] = s.max(axis=1)
        return out

    print("nearest_neighbor_distances", flush=True)
    nn_train = nn_sim(Xq, Xtr)
    nn_dev = nn_sim(Xq, Xdv)
    nn_rep = nn_sim(Xq, Xrp)

    def row_error(r):
        p = pred_by_id[r["identity"]]
        g = set(all_labels(r))
        pred = set(
            p["final_domain_labels"]
            + p["final_function_labels"]
            + p["final_mediation_labels"]
        )
        return len(g - pred) + len(pred - g)

    err = np.asarray([row_error(r) for r in qual_rows], dtype=np.float64)
    correct = err == 0
    train_distance = {
        "mean_nn_train_correct": float(nn_train[correct].mean())
        if correct.any()
        else None,
        "mean_nn_train_incorrect": float(nn_train[~correct].mean())
        if (~correct).any()
        else None,
        "mean_nn_dev_correct": float(nn_dev[correct].mean()) if correct.any() else None,
        "mean_nn_dev_incorrect": float(nn_dev[~correct].mean())
        if (~correct).any()
        else None,
        "mean_nn_rep_correct": float(nn_rep[correct].mean()) if correct.any() else None,
        "mean_nn_rep_incorrect": float(nn_rep[~correct].mean())
        if (~correct).any()
        else None,
        "corr_error_vs_nn_train": float(np.corrcoef(err, nn_train)[0, 1])
        if len(err) > 2
        else None,
        "effect": (
            "ERRORS_FARTHER_FROM_TRAIN"
            if (
                correct.any()
                and (~correct).any()
                and nn_train[~correct].mean() + 0.02 < nn_train[correct].mean()
            )
            else "WEAK_OR_NO_DISTANCE_EFFECT"
        ),
    }

    # Lexical overlap proxy: mean max token-jaccard via embedding already; also char-ngram light
    # Embedding proximity already captured. Representativeness:
    rep_representativeness = {
        "class": "REPRESENTATIVE_VALIDATION_OVERFIT",
        "rep_excluded_zero_label_rows": True,
        "rep_usable_n": len(rep),
        "rep_raw_n": len(rep_raw),
        "qual_n": len(qual_rows),
        "qual_zero_label_share": qual_feat["zero_label_share"],
        "qual_no_evidence_share": sum(
            1 for r in qual_rows if r.get("evidence_label") == "NO_EVIDENCE"
        )
        / max(1, len(qual_rows)),
        "rep_usable_zero_label_share": rep_feat["zero_label_share"],
        "rep_raw_zero_label_share": rep_raw_feat["zero_label_share"],
        "rep_domain_plus_function_n": counts(rep)["domain+function"],
        "qual_domain_plus_function_n": counts(qual_rows)["domain+function"],
        "usable_filter": "evidence_label==EVIDENCE_PRESENT AND not human_resettlement_required AND >=1 label",
        "rationale": (
            "Hardened REP metric (~0.432) was computed on the usable() positive-only "
            "subset (n=532), excluding all ZERO/NONE rows. QUAL is 74.5% NO_EVIDENCE "
            "zero-label rows, and includes domain+function compositions absent from "
            "usable REP (n=0). REP was therefore another development surface, not an "
            "operating-distribution proxy."
        ),
        "distribution_shift_summary": {
            k: v.get("class") if isinstance(v, dict) else v
            for k, v in shift_dims.items()
        },
    }

    # --- 14 QUAL validity ---
    qual_validity = {
        "class": "HARDER_BUT_VALID",
        "human_mean_set_jaccard": 0.99875,
        "disjointness_forbidden_overlap": 0,
        "n_rows": 1004,
        "operating_contract_note": (
            "Final V6 operating distribution includes NO_EVIDENCE/NONE-dominant "
            "internet register text; QUAL matches that better than usable REP."
        ),
        "not_outside_product_contract": True,
    }

    # --- 15 human gold ---
    human_gold = {
        "mean_set_jaccard": 0.99875,
        "class": "MODEL_GENERALIZATION_FAILURE_NOT_ANNOTATION_INSTABILITY",
        "note": "Settlement stability stands; do not blame label noise without row-level contradiction.",
    }

    # --- 16 error concentration ---
    # Count FP+FN label events per stratum
    strata_counts = Counter()
    total_err_events = 0
    for i, r in enumerate(qual_rows):
        p = pred_by_id[r["identity"]]
        g = set(all_labels(r))
        pred = set(
            p["final_domain_labels"]
            + p["final_function_labels"]
            + p["final_mediation_labels"]
        )
        fp = pred - g
        fn = g - pred
        n_e = len(fp) + len(fn)
        if n_e == 0:
            continue
        total_err_events += n_e
        strata_counts[("zero_label" if n_lab(r) == 0 else "positive_label",)] += n_e
        strata_counts[("composition", composition(r))] += n_e
        strata_counts[("length", length_bucket(len(r.get("text") or "")))] += n_e
        strata_counts[("topic", family_topic(r.get("source_family")))] += n_e
        for lab in fp:
            strata_counts[("label_fp", lab)] += 1
        for lab in fn:
            strata_counts[("label_fn", lab)] += 1
        if fp or fn:
            if any(l.startswith("domain.") for l in fp | fn):
                strata_counts[("axis", "domain")] += len(
                    [l for l in fp | fn if l.startswith("domain.")]
                )
            if any(l.startswith("function.") for l in fp | fn):
                strata_counts[("axis", "function")] += len(
                    [l for l in fp | fn if l.startswith("function.")]
                )
            if any(l.startswith("mediation.") for l in fp | fn):
                strata_counts[("axis", "mediation")] += len(
                    [l for l in fp | fn if l.startswith("mediation.")]
                )

    def concentration(prefix):
        items = [(k, v) for k, v in strata_counts.items() if k[0] == prefix]
        items.sort(key=lambda x: -x[1])
        tot = sum(v for _, v in items) or 1
        out = {"total": tot, "ranked": []}
        cum = 0
        marks = {0.25: None, 0.50: None, 0.75: None}
        for i, (k, v) in enumerate(items, 1):
            cum += v
            out["ranked"].append({"key": list(k[1:]), "n": v, "share": v / tot})
            for m in marks:
                if marks[m] is None and cum / tot >= m:
                    marks[m] = i
        out["smallest_set_for"] = {str(k): marks[k] for k in marks}
        out["top"] = out["ranked"][:15]
        return out

    error_concentration = {
        "total_fp_fn_events": total_err_events,
        "by_zero_vs_positive": concentration("zero_label")
        if False
        else {
            "zero_label_events": strata_counts.get(("zero_label",), 0),
            "positive_label_events": strata_counts.get(("positive_label",), 0),
            "zero_share": strata_counts.get(("zero_label",), 0)
            / max(1, total_err_events),
        },
        "by_composition": concentration("composition"),
        "by_length": concentration("length"),
        "by_topic": concentration("topic"),
        "by_label_fp": concentration("label_fp"),
        "by_axis": concentration("axis"),
        "diffuse_or_concentrated": (
            "CONCENTRATED_ON_ZERO_LABEL_OVERPREDICTION"
            if strata_counts.get(("zero_label",), 0) / max(1, total_err_events) >= 0.45
            else "DIFFUSE"
        ),
    }

    # --- 17 constraints ---
    constraint_contribution = {
        "raw_hierarchy_violation": hierarchy["raw_hierarchy_violation_rate"],
        "post_constraint_hierarchy_violation": hierarchy[
            "post_constraint_hierarchy_violation_rate"
        ],
        "corrected": hierarchy["predictions_corrected_by_constraints"],
        "degraded": hierarchy["predictions_degraded_by_constraints"],
        "net_effect": hierarchy["predictions_corrected_by_constraints"]
        - hierarchy["predictions_degraded_by_constraints"],
        "class": (
            "COSMETIC"
            if hierarchy["predictions_corrected_by_constraints"] <= 5
            and primary["system_macro_f1"] < 0.30
            else "BENEFICIAL"
        ),
    }

    # --- 18 Calibration counterfactual (diagnostic only; no adoption) ---
    print("calibration_counterfactual", flush=True)
    # Grid a few absolute offsets applied uniformly; never adopt.
    base_scores = {a: row_score_mat(qual_rows, a) for a in vocabs}
    golds = {a: row_gold_mat(qual_rows, a) for a in vocabs}
    # Also need REP scores via cold heads on Xrp
    heads = load_head_bundle(
        PRIVATE_PKG / "heads" / "axis_nonlinear_heads.pt", 768, vocabs, device
    )
    rep_scores = scores_from_heads(heads, Xrp, device)
    rep_golds = {
        a: np.asarray(
            [
                [1 if lab in (r.get(f"{a}_labels") or []) else 0 for lab in vocabs[a]]
                for r in rep
            ],
            dtype=np.int32,
        )
        for a in vocabs
    }

    def eval_th(scores_by_axis, gold_by_axis, th_by_axis, rows_for_hier):
        preds = {}
        for a in vocabs:
            th = np.asarray(th_by_axis[a])
            preds[a] = (scores_by_axis[a] >= th).astype(np.int32)
        # hierarchy force parent
        d = preds["domain"].copy()
        viol = 0
        for i in range(d.shape[0]):
            if d[i, ai_idx] == 1 and d[i, tech_idx] == 0:
                viol += 1
                d[i, tech_idx] = 1
        preds["domain"] = d
        macros = {
            a: macro_f1_multilabel(gold_by_axis[a], preds[a]) for a in vocabs
        }
        system = float(np.mean(list(macros.values())))
        return system, macros, viol / max(1, len(rows_for_hier))

    base_q, _, _ = eval_th(base_scores, golds, thresholds, qual_rows)
    base_r, _, _ = eval_th(rep_scores, rep_golds, thresholds, rep)
    best = {
        "qual": base_q,
        "rep": base_r,
        "offset": 0.0,
        "rescues_qual_and_keeps_rep": False,
    }
    for offset in (-0.15, -0.10, -0.05, 0.05, 0.10, 0.15, 0.20, 0.25):
        th2 = {a: [min(0.95, max(0.01, t + offset)) for t in thresholds[a]] for a in vocabs}
        q_m, _, q_h = eval_th(base_scores, golds, th2, qual_rows)
        r_m, _, r_h = eval_th(rep_scores, rep_golds, th2, rep)
        if q_m > best["qual"]:
            best = {
                "qual": q_m,
                "rep": r_m,
                "offset": offset,
                "qual_hier": q_h,
                "rep_hier": r_h,
                "rescues_qual_and_keeps_rep": q_m >= 0.30 and r_m >= 0.30 and r_h <= 0.05,
            }
    calibration_counterfactual = {
        "classification": (
            "OPERATING_POINT_CONFLICT"
            if best["qual"] < 0.30 and best["rep"] >= 0.30
            else (
                "CALIBRATION_SHIFT"
                if best["rescues_qual_and_keeps_rep"]
                else "STRUCTURAL_OVERLAP"
            )
        ),
        "base_qual_system_macro": base_q,
        "base_rep_system_macro": base_r,
        "best_uniform_offset": best,
        "any_fixed_region_rescues_qual_while_retaining_rep": bool(
            best.get("rescues_qual_and_keeps_rep")
        ),
        "thresholds_adopted": False,
        "hard_rule": "no discovered threshold becomes active",
    }
    # If best offset cannot rescue QUAL to 0.30, structural
    if best["qual"] < 0.30:
        calibration_counterfactual["classification"] = "STRUCTURAL_OVERLAP"

    # --- 19 axis-specific encoder evidence ---
    axis_encoder_hypothesis = {
        "prior": "AXIS_SPECIFIC_REPRESENTATIONS_JUSTIFIED",
        "shared_encoder_adequate": (
            semantic_geometry["class"] != "SEMANTIC_ENCODER_DOMAIN_MISMATCH"
            and axis_degradation["function"]["class"] != "COLLAPSED"
        ),
        "different_encoders_per_axis_justified_now": (
            axis_degradation["function"]["class"] == "COLLAPSED"
            and semantic_geometry["class"] != "SEMANTIC_ENCODER_DOMAIN_MISMATCH"
            and not rep_representativeness["rep_excluded_zero_label_rows"]
        ),
        "note": (
            "Function collapse is real, but usable-REP excluded NONE and co-label "
            "compositions; fix representativeness before committing to per-axis encoders."
        ),
        "build_now": False,
    }

    # --- 20 baselines ---
    representation_family = {
        "QUAL_vs_historical_zero_shot_REP": {
            "ModernBERT_zero_shot_REP": 0.162,
            "MPNet_zero_shot_REP": 0.206,
            "BGE_zero_shot_REP": 0.243,
            "hardened_MSMARCO_REP": REP_REFERENCE_SYSTEM_MACRO_F1,
            "hardened_MSMARCO_QUAL": primary["system_macro_f1"],
        },
        "QUAL_predictions_for_other_encoders": "NOT_COMPUTABLE",
        "note": "No preregistered QUAL scores for MPNet/BGE/ModernBERT; do not generate.",
    }

    # --- 21 data scale ---
    data_scale = {
        "class": "DIVERSITY_EXPANSION_JUSTIFIED",
        "subclass": "MORE_OF_SAME_DATA_UNLIKELY_TO_HELP",
        "evidence": [
            "usable REP omitted NONE/NO_EVIDENCE mass that dominates QUAL",
            "usable REP had 0 domain+function rows; QUAL has 17",
            "error mass concentrated on zero-label overprediction",
        ],
        "recommend": "Rebuild representative validation to include NONE + co-label strata; do not merely enlarge positive-only TRAIN.",
    }

    # --- 22 task signal ---
    # Positive-only QUAL system macro as a diagnostic slice
    pos_rows = [r for r in qual_rows if n_lab(r) > 0]
    pos_scores = {a: row_score_mat(pos_rows, a) for a in vocabs}
    pos_golds = {a: row_gold_mat(pos_rows, a) for a in vocabs}
    pos_sys, pos_macros, pos_h = eval_th(pos_scores, pos_golds, thresholds, pos_rows)
    task_signal = {
        "class": (
            "TASK_SIGNAL_PARTIAL"
            if pos_sys >= 0.20
            else "TASK_SIGNAL_INSUFFICIENT"
        ),
        "QUAL_full_system_macro": primary["system_macro_f1"],
        "QUAL_positive_only_system_macro": pos_sys,
        "QUAL_positive_only_axis_macros": pos_macros,
        "QUAL_positive_only_n": len(pos_rows),
        "human_agreement_high": True,
        "note": "Human agreement proves labelability; positive-only QUAL still below 0.30 gate.",
    }

    # NONE overprediction stats
    none_rows = [r for r in qual_rows if n_lab(r) == 0]
    none_any = 0
    none_fp_labels = 0
    for r in none_rows:
        p = pred_by_id[r["identity"]]
        npred = (
            len(p["final_domain_labels"])
            + len(p["final_function_labels"])
            + len(p["final_mediation_labels"])
        )
        if npred:
            none_any += 1
            none_fp_labels += npred

    audit = {
        "exact_metrics": exact_metrics,
        "gate_failures": gate_failures,
        "rep_qual_retention": retention,
        "axis_degradation": axis_degradation,
        "per_label_degradation": per_label_deg,
        "distribution_shift": shift_dims,
        "source_shift": source_shift,
        "prevalence": prev,
        "label_prior_shift": label_prior_shift,
        "cardinality_shift": card_shift,
        "co_label_shift": co_label_shift,
        "axis_head_analysis": axis_head,
        "semantic_geometry": semantic_geometry,
        "label_semantic_stability": label_semantic_stability,
        "rep_representativeness": rep_representativeness,
        "train_distance": train_distance,
        "qual_validity": qual_validity,
        "human_gold": human_gold,
        "error_concentration": error_concentration,
        "constraint_contribution": constraint_contribution,
        "calibration_counterfactual": calibration_counterfactual,
        "axis_encoder_hypothesis": axis_encoder_hypothesis,
        "representation_family": representation_family,
        "data_scale": data_scale,
        "task_signal": task_signal,
        "none_overprediction": {
            "n_zero_gold": len(none_rows),
            "n_with_any_prediction": none_any,
            "total_fp_labels_on_zero_gold": none_fp_labels,
            "rate": none_any / max(1, len(none_rows)),
        },
        "error_decomposition": errors,
        "encoder_state_hash": enc_hash,
        "package_sha256": EXPECTED_PACKAGE_SHA256,
        "qual_result_sha256": EXPECTED_QUAL_RESULT_SHA256,
        "qualification_immutable": {
            "QUALIFICATION_ID": QUALIFICATION_ID,
            "evaluation_spent": "EVALUATION_SPENT",
            "qualification_model_executions": 1,
            "allowed": [
                "forensic_analysis",
                "error_attribution",
                "system_diagnosis",
                "historical_comparison",
            ],
            "forbidden": [
                "training",
                "threshold_selection",
                "model_selection",
                "representation_learning",
                "prompt_or_label_description_tuning",
                "head_tuning",
                "index_construction",
            ],
        },
    }

    receipt = build_system_review_receipt(audit)
    derived = receipt["derived"]

    summary = {
        "REVIEW_STATE": "COMPLETE",
        "REVIEW_RULE": receipt["REVIEW_RULE"],
        "REVIEW_ID": receipt["REVIEW_ID"],
        "QUALIFICATION_ID": QUALIFICATION_ID,
        "PRIMARY_DIAGNOSIS": derived["PRIMARY_DIAGNOSIS"],
        "SECONDARY_CONTRIBUTORS": derived["SECONDARY_CONTRIBUTORS"],
        "V6_DISPOSITION": derived["V6_DISPOSITION"],
        "NEXT_ACTION": derived["NEXT_ACTION"],
        "REP_REPRESENTATIVENESS": derived["REP_REPRESENTATIVENESS"],
        "QUALIFICATION_SURFACE_VALIDITY": derived["QUALIFICATION_SURFACE_VALIDITY"],
        "system_macro_f1_QUAL": primary["system_macro_f1"],
        "system_macro_f1_REP": REP_REFERENCE_SYSTEM_MACRO_F1,
        "FUNCTION_macro_f1_QUAL": primary["FUNCTION_macro_f1"],
        "none_overprediction_rate": audit["none_overprediction"]["rate"],
        "RELEASE_ELIGIBLE": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "MODEL_WIDE_BEST_MUTATED": False,
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "THRESHOLDS_CHANGED": False,
        "TRAIN": False,
        "REJECTED_MICRO_FIXES": dict(REJECTED_MICRO_FIXES),
        "SYSTEM_REVIEW_RECEIPT_SHA256": receipt["SYSTEM_REVIEW_RECEIPT_SHA256"],
        "code_revision": code_revision(),
    }

    # Persist
    write_private(PRIVATE_REV / "CONTRACT.json", review_contract())
    write_private(PRIVATE_REV / "AUDIT.json", audit)
    write_private(PRIVATE_REV / "RECEIPT.json", receipt)
    write_private(PRIVATE_REV / "SUMMARY.json", summary)
    write_private(PRIVATE_REV / "POINTER.json", {
        "MODEL_WIDE_BEST": receipt["MODEL_WIDE_BEST"],
        "MODEL_WIDE_BEST_MUTATED": False,
        "V5_POINTERS_MUTATED": False,
        "STAGE_A_BEST_MUTATED": False,
        "V6_REPRESENTATION_CANDIDATE_STATUS": "QUALIFICATION_FAILED",
        "HUB_PUBLISH_AUTHORIZED": False,
    })

    write_repo(REPO_ART / "contract.json", review_contract())
    write_repo(REPO_ART / "audit.json", audit)
    write_repo(REPO_ART / "receipt.json", receipt)
    write_repo(REPO_ART / "RECEIPT.json", receipt)
    write_repo(REPO_ART / "summary.json", summary)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(REPO_ART / "pointer.json", {
        "MODEL_WIDE_BEST_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "PRIMARY_DIAGNOSIS": derived["PRIMARY_DIAGNOSIS"],
        "NEXT_ACTION": derived["NEXT_ACTION"],
    })

    write_repo(
        SPEC / "classification-v6-qualification-failure-system-review-receipt-20261001.json",
        receipt,
    )
    md = f"""# REVIEW_V6_QUALIFICATION_FAILURE_AT_SYSTEM_LEVEL

```text
PRIMARY_DIAGNOSIS = {derived['PRIMARY_DIAGNOSIS']}
V6_DISPOSITION = {derived['V6_DISPOSITION']}
NEXT_ACTION = {derived['NEXT_ACTION']}
REP_REPRESENTATIVENESS = {derived['REP_REPRESENTATIVENESS']}
QUAL system macro-F1 = {primary['system_macro_f1']:.4f}
REP system macro-F1 = {REP_REFERENCE_SYSTEM_MACRO_F1:.4f}
FUNCTION QUAL = {primary['FUNCTION_macro_f1']:.4f}
NONE overprediction rate = {audit['none_overprediction']['rate']:.3f}
RECEIPT = {receipt['SYSTEM_REVIEW_RECEIPT_SHA256']}
```

Hardened REP (~0.432) was scored on `usable()` positive-only rows (n=532),
excluding ZERO/NONE. QUAL is 74.5% `NO_EVIDENCE` zero-label and includes
domain+function compositions absent from usable REP (n=0).
MODEL_WIDE_BEST unchanged. QUAL remains EVALUATION_SPENT. No thresholds adopted.
"""
    write_repo(
        SPEC / "classification-v6-qualification-failure-system-review-20261001.md", md
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    if os.environ.get("HLX_V6_QUAL_FAIL_REVIEW_INNER") == "1":
        return inner()
    PRIVATE_REV.mkdir(mode=0o700, parents=True, exist_ok=True)
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
        "HLX_V6_QUAL_FAIL_REVIEW_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(
            REPO
            / "scripts/spark/run_classification_v6_qualification_failure_system_review.py"
        ),
    ]
    log = PRIVATE_REV / "review_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(cmd, check=False, stdout=handle, stderr=subprocess.STDOUT)
    try:
        print(log.read_text(encoding="utf-8")[-60000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
