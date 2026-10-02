"""REDESIGN_V6_REPRESENTATIVE_VALIDATION_AND_DATA_DIVERSITY.

Build TRAIN/DEV/REP V2 without usable() positive-only filtering, then
replay the frozen hardened V6 package. QUAL-002 is aggregate comparison only.
"""

from __future__ import annotations

import hashlib
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
    "/home/morpheus/hlx-private/classification-v6-representative-validation-redesign-20261001"
)
PRIVATE_FOUND = Path(
    "/home/morpheus/hlx-private/classification-v6-data-foundation-20261001"
)
PRIVATE_MIG = Path(
    "/home/morpheus/hlx-private/classification-v6-label-migration-bakeoff-20261001"
)
PRIVATE_QUAL = Path(
    "/home/morpheus/hlx-private/classification-v6-qualification-surface-002-20261001"
)
PRIVATE_EXEC = Path(
    "/home/morpheus/hlx-private/classification-v6-qualification-execute-002-20261001"
)
PRIVATE_PKG = Path(
    "/home/morpheus/hlx-private/classification-v6-semantic-pipeline-harden-20261001"
)
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-REPRESENTATIVE-VALIDATION-REDESIGN-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
SEED = 20261002
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


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as h:
        for r in rows:
            h.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n")
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


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def text_hash(text: str) -> str:
    return sha256_text((text or "").strip().lower())


def identity_for(text: str, source_url: str | None, source_family: str | None) -> str:
    return sha256_text(
        json.dumps(
            {
                "text": (text or "").strip(),
                "source_url": source_url or "",
                "source_family": source_family or "",
            },
            sort_keys=True,
        )
    )


def n_lab(r: dict) -> int:
    return (
        len(r.get("domain_labels") or [])
        + len(r.get("function_labels") or [])
        + len(r.get("mediation_labels") or [])
    )


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


def length_bucket(n: int) -> str:
    if n < 60:
        return "short"
    if n < 180:
        return "medium"
    return "long"


def map_adjudicated(adj: dict) -> dict[str, Any]:
    from hyperlexical.classification_v6_label_migration import DOMAIN_IDS, FUNCTION_IDS

    domains = []
    for d in adj.get("domains") or []:
        if d in DOMAIN_IDS:
            domains.append(DOMAIN_IDS[d])
        elif d == "ai_discourse":
            domains.append("domain.technology.ai_discourse")
    functions = [
        FUNCTION_IDS[f] for f in (adj.get("functions") or []) if f in FUNCTION_IDS
    ]
    mediation = (
        ["mediation.internet_register"]
        if "internet_register" in (adj.get("mediation") or [])
        else []
    )
    repaired = False
    if (
        "domain.technology.ai_discourse" in domains
        and "domain.technology" not in domains
    ):
        domains.append("domain.technology")
        repaired = True
    return {
        "evidence_label": adj.get("stage_a"),
        "domain_labels": sorted(set(domains)),
        "function_labels": sorted(set(functions)),
        "mediation_labels": sorted(set(mediation)),
        "hierarchy_repaired": repaired,
        "adjudication_status": adj.get("status"),
        "ontology_uncertainty": adj.get("uncertainty"),
    }


def dist_summary(rows: list[dict]) -> dict[str, Any]:
    n = max(1, len(rows))
    ev = Counter(r.get("evidence_label") for r in rows)
    card = Counter(min(n_lab(r), 3) for r in rows)
    comp = Counter(composition(r) for r in rows)
    lens = [len(r.get("text") or "") for r in rows]
    lb = Counter(length_bucket(x) for x in lens)
    src = Counter(r.get("source_family") or "UNKNOWN" for r in rows)
    zero = sum(1 for r in rows if n_lab(r) == 0)
    return {
        "n": len(rows),
        "zero_label_share": zero / n,
        "no_evidence_share": ev.get("NO_EVIDENCE", 0) / n,
        "evidence_present_share": ev.get("EVIDENCE_PRESENT", 0) / n,
        "evidence_label": dict(ev),
        "cardinality": {str(k): v for k, v in sorted(card.items())},
        "composition": dict(comp),
        "length": dict(lb),
        "mean_len": float(sum(lens) / n) if lens else 0.0,
        "n_source_families": len(src),
        "max_source_family_share": (max(src.values()) / n) if src else 0.0,
        "source_family_top": src.most_common(12),
        "n_function_positive": sum(1 for r in rows if r.get("function_labels")),
        "n_domain_positive": sum(1 for r in rows if r.get("domain_labels")),
        "n_mediation_positive": sum(1 for r in rows if r.get("mediation_labels")),
        "n_multi_label": sum(1 for r in rows if n_lab(r) >= 2),
        "n_domain_plus_function": sum(
            1 for r in rows if composition(r) in {"domain+function", "domain+function+mediation"}
        ),
        "observed_share": sum(
            1 for r in rows if (r.get("provenance") or "OBSERVED") == "OBSERVED"
        )
        / n,
        "natural_share": sum(
            1
            for r in rows
            if (r.get("construction_tag") or "NATURAL") == "NATURAL"
        )
        / n,
    }


def mean_pool(last_hidden, attention_mask):
    mask = attention_mask.unsqueeze(-1).float()
    return (last_hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-6)


def embed_model(model_id, texts, device, max_len=MAX_LEN, batch=BATCH, revision=None):
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
    n_train = sum(p.numel() for p in enc.parameters() if p.requires_grad)
    hsh = hashlib.sha256()
    for k, tns in sorted(enc.state_dict().items()):
        hsh.update(k.encode())
        hsh.update(tns.detach().cpu().numpy().tobytes())
    del enc
    torch.cuda.empty_cache()
    return __import__("torch").cat(vecs, dim=0).numpy(), hsh.hexdigest(), n_train


def build_mlp(hidden: int, n_out: int, device):
    import torch.nn as nn

    return nn.Sequential(
        nn.Linear(hidden, 128), nn.ReLU(), nn.Linear(128, n_out)
    ).to(device)


def load_heads(path: Path, vocabs, device):
    import io
    import torch

    raw = sudo_read_bytes(path)
    try:
        bundle = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=False)
    except TypeError:
        bundle = torch.load(io.BytesIO(raw), map_location="cpu")
    heads = {}
    for axis, vocab in vocabs.items():
        m = build_mlp(768, len(vocab), device)
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


def f1_binary(yt, yp) -> float:
    import numpy as np

    yt = np.asarray(yt)
    yp = np.asarray(yp)
    tp = float(((yt == 1) & (yp == 1)).sum())
    fp = float(((yt == 0) & (yp == 1)).sum())
    fn = float(((yt == 1) & (yp == 0)).sum())
    if tp == 0:
        return 0.0
    p = tp / (tp + fp)
    r = tp / (tp + fn)
    return 2 * p * r / (p + r)


def macro_f1(gold, pred) -> float:
    import numpy as np

    g = np.asarray(gold)
    p = np.asarray(pred)
    if g.size == 0:
        return 0.0
    return float(sum(f1_binary(g[:, j], p[:, j]) for j in range(g.shape[1])) / g.shape[1])


def multi_hot(labels, vocab):
    idx = {v: i for i, v in enumerate(vocab)}
    vec = [0] * len(vocab)
    for lab in labels or []:
        if lab in idx:
            vec[idx[lab]] = 1
    return vec


def evaluate_surface(rows, scores, vocabs, thresholds, tech_idx, ai_idx) -> dict[str, Any]:
    import numpy as np

    golds = {
        a: np.asarray(
            [multi_hot(r.get(f"{a}_labels"), vocabs[a]) for r in rows], dtype=np.int32
        )
        for a in vocabs
    }
    preds = {}
    for a in vocabs:
        th = np.asarray(thresholds[a])
        preds[a] = (np.asarray(scores[a]) >= th).astype(np.int32)
    # hierarchy
    d = preds["domain"].copy()
    for i in range(d.shape[0]):
        if d[i, ai_idx] == 1 and d[i, tech_idx] == 0:
            d[i, tech_idx] = 1
    preds["domain"] = d
    axis_macros = {a: macro_f1(golds[a], preds[a]) for a in vocabs}
    system = float(sum(axis_macros.values()) / len(axis_macros))

    # zero-label metrics
    zero_idx = [i for i, r in enumerate(rows) if n_lab(r) == 0]
    zero_fp = 0
    zero_exact = 0
    pred_counts = []
    for i in zero_idx:
        npred = int(preds["domain"][i].sum() + preds["function"][i].sum() + preds["mediation"][i].sum())
        pred_counts.append(npred)
        if npred == 0:
            zero_exact += 1
        else:
            zero_fp += 1
    n_zero = max(1, len(zero_idx))

    # cardinality slices
    def slice_macro(mask):
        idx = [i for i, m in enumerate(mask) if m]
        if not idx:
            return None
        return float(
            sum(
                macro_f1(golds[a][idx], preds[a][idx]) for a in vocabs
            )
            / len(vocabs)
        )

    single = slice_macro([n_lab(r) == 1 for r in rows])
    multi = slice_macro([n_lab(r) >= 2 for r in rows])
    pos_only = slice_macro([n_lab(r) > 0 for r in rows])
    df_mask = [
        composition(r) in {"domain+function", "domain+function+mediation"} for r in rows
    ]
    df_macro = slice_macro(df_mask)

    # source slices (families with n>=8)
    fam_macros = {}
    for fam in sorted({r.get("source_family") or "UNKNOWN" for r in rows}):
        mask = [(r.get("source_family") or "UNKNOWN") == fam for r in rows]
        if sum(mask) >= 8:
            fam_macros[fam] = slice_macro(mask)

    return {
        "n": len(rows),
        "system_macro_f1": system,
        "DOMAIN_macro_f1": axis_macros["domain"],
        "FUNCTION_macro_f1": axis_macros["function"],
        "MEDIATION_macro_f1": axis_macros["mediation"],
        "axis_macros": axis_macros,
        "zero_label_n": len(zero_idx),
        "zero_label_false_positive_rate": zero_fp / n_zero,
        "zero_label_exact_rejection": zero_exact / n_zero,
        "mean_predicted_labels_on_zero_gold": float(sum(pred_counts) / n_zero),
        "single_label_system_macro_f1": single,
        "multi_label_system_macro_f1": multi,
        "positive_only_system_macro_f1": pos_only,
        "n_domain_plus_function": int(sum(df_mask)),
        "co_label_performance": {
            "domain_plus_function_system_macro": df_macro,
            "n": int(sum(df_mask)),
        },
        "source_slices": fam_macros,
    }


def join_foundation_migration() -> dict[str, list[dict]]:
    out = {}
    for split, fname, mname in (
        ("TRAIN", "TRAIN.jsonl", "TRAIN_V6_LABELS.jsonl"),
        ("DEV", "DEVELOPMENT_VALIDATION.jsonl", "DEVELOPMENT_VALIDATION_V6_LABELS.jsonl"),
        ("REP", "REPRESENTATIVE_VALIDATION.jsonl", "REPRESENTATIVE_VALIDATION_V6_LABELS.jsonl"),
    ):
        found = {
            json.loads(l)["identity"]: json.loads(l)
            for l in sudo_read_text(PRIVATE_FOUND / fname).splitlines()
            if l.strip()
        }
        mig = load_jsonl(PRIVATE_MIG / mname)
        rows = []
        for m in mig:
            f = found.get(m["identity"]) or {}
            rows.append(
                {
                    **f,
                    **{
                        k: m.get(k)
                        for k in (
                            "identity",
                            "text",
                            "evidence_label",
                            "domain_labels",
                            "function_labels",
                            "mediation_labels",
                            "hierarchy_repaired",
                            "ontology_uncertainty",
                            "schema",
                            "split",
                        )
                        if m.get(k) is not None
                    },
                    "source_family": f.get("source_family") or m.get("source_family"),
                    "provenance": f.get("provenance") or "OBSERVED",
                    "construction_tag": f.get("construction_tag") or "NATURAL",
                    "construction_role": f.get("construction_role") or "PRODUCT_EXPECTED",
                    "v2_origin": f"foundation+migration:{split}",
                }
            )
        out[split] = rows
    return out


def blocked_identities() -> set[str]:
    blocked = set()
    for r in load_jsonl(PRIVATE_QUAL / "QUALIFICATION_ROWS.jsonl"):
        blocked.add(r["identity"])
    hold = PRIVATE_FOUND / "qualification_holdout" / "QUALIFICATION_ROWS.jsonl"
    for r in load_jsonl(hold):
        blocked.add(r["identity"])
    return blocked


def unused_none_rows(existing_text_hashes: set[str], blocked: set[str]) -> list[dict]:
    pool = []
    for path in (PRIVATE_FOUND / "RAW_ACQUIRE.jsonl", PRIVATE_FOUND / "RAW_TOPUP.jsonl"):
        for r in load_jsonl(path):
            if r.get("evidence_label") != "NO_EVIDENCE":
                continue
            th = text_hash(r.get("text") or "")
            if th in existing_text_hashes:
                continue
            ident = identity_for(
                r.get("text") or "", r.get("source_url"), r.get("source_family")
            )
            if ident in blocked:
                continue
            pool.append(
                {
                    "identity": ident,
                    "text": r.get("text"),
                    "evidence_label": "NO_EVIDENCE",
                    "domain_labels": [],
                    "function_labels": [],
                    "mediation_labels": [],
                    "source_family": r.get("source_family"),
                    "source_url": r.get("source_url"),
                    "provenance": r.get("provenance") or "OBSERVED",
                    "construction_tag": r.get("construction_tag") or "NATURAL",
                    "construction_role": r.get("construction_role") or "PRODUCT_EXPECTED",
                    "topic_domain": r.get("topic_domain"),
                    "v2_origin": "unused_none_topup",
                    "text_sha256": th,
                }
            )
            existing_text_hashes.add(th)
    return pool


def dual_relabel_co_labels(rows: list[dict]) -> list[dict]:
    """Dual-annotate positives; return rows where agreed gold has domain+function."""
    from hyperlexical.classification_v6_human_ontology_settlement import (
        dual_annotate_rows,
    )

    cand = [
        r
        for r in rows
        if r.get("evidence_label") == "EVIDENCE_PRESENT"
        and (r.get("domain_labels") or r.get("function_labels"))
    ]
    print(f"dual_annotate candidates={len(cand)}", flush=True)
    ann = dual_annotate_rows(cand)
    out = []
    for a, src in zip(ann, cand):
        mapped = map_adjudicated(a["adjudicated"])
        if not (mapped["domain_labels"] and mapped["function_labels"]):
            continue
        if mapped.get("adjudication_status") not in {"AGREED", "ADJUDICATED"}:
            continue
        # Keep only if dual protocols found both axes (natural cue co-presence)
        row = dict(src)
        row.update(mapped)
        row["v2_origin"] = (row.get("v2_origin") or "") + "+dual_colabel"
        row["dual_annotation"] = {
            "status": a["adjudicated"].get("status"),
            "pair_metrics": a["pair_metrics"],
        }
        out.append(row)
    print(f"dual_colabel_rows={len(out)}", flush=True)
    return out


def build_v2_splits(joined: dict[str, list[dict]], blocked: set[str]) -> dict[str, list[dict]]:
    rng = random.Random(SEED)
    # Drop blocked identities (should be none vs QUAL)
    for k in joined:
        joined[k] = [r for r in joined[k] if r["identity"] not in blocked]

    text_hashes = {text_hash(r.get("text") or "") for rows in joined.values() for r in rows}
    none_pool = unused_none_rows(text_hashes, blocked)
    rng.shuffle(none_pool)

    # Dual-discover co-labels across all foundation positives
    all_pos = joined["TRAIN"] + joined["DEV"] + joined["REP"]
    colabel = dual_relabel_co_labels(all_pos)
    colabel_ids = {r["identity"] for r in colabel}

    # Start from full splits (NO usable filter)
    train = [dict(r) for r in joined["TRAIN"] if r["identity"] not in colabel_ids]
    dev = [dict(r) for r in joined["DEV"] if r["identity"] not in colabel_ids]
    rep = [dict(r) for r in joined["REP"] if r["identity"] not in colabel_ids]

    # Inject co-label rows: prefer REP then DEV then TRAIN
    rng.shuffle(colabel)
    for r in colabel:
        if len([x for x in rep if composition(x).startswith("domain+function")]) < 12:
            r2 = dict(r)
            r2["split"] = "REPRESENTATIVE_VALIDATION_V2"
            rep.append(r2)
        elif len([x for x in dev if composition(x).startswith("domain+function")]) < 6:
            r2 = dict(r)
            r2["split"] = "DEVELOPMENT_VALIDATION_V2"
            dev.append(r2)
        else:
            r2 = dict(r)
            r2["split"] = "TRAIN_V2"
            train.append(r2)

    # Raise REP zero-label share toward [0.55, 0.75] by:
    # 1) adding unused NONE
    # 2) moving excess single-domain positives from REP → TRAIN
    def zero_share(rows):
        return sum(1 for r in rows if n_lab(r) == 0) / max(1, len(rows))

    # Add NONE to REP first
    for r in none_pool:
        if zero_share(rep) >= 0.62 and len(rep) >= 1100:
            # remainder to train
            r2 = dict(r)
            r2["split"] = "TRAIN_V2"
            train.append(r2)
        else:
            r2 = dict(r)
            r2["split"] = "REPRESENTATIVE_VALIDATION_V2"
            rep.append(r2)

    # If still below 0.55, move domain-only positives out of REP
    movers = [
        r
        for r in rep
        if composition(r) == "domain"
        and r.get("v2_origin") != "unused_none_topup"
        and "dual_colabel" not in (r.get("v2_origin") or "")
    ]
    rng.shuffle(movers)
    i = 0
    while zero_share(rep) < 0.58 and i < len(movers) and len(rep) > 950:
        r = movers[i]
        i += 1
        rep = [x for x in rep if x["identity"] != r["identity"]]
        r2 = dict(r)
        r2["split"] = "TRAIN_V2"
        r2["v2_origin"] = (r2.get("v2_origin") or "") + "+moved_rep_to_train_for_none_mass"
        train.append(r2)

    # Ensure DEV keeps substantial NONE (already has ~46% NO_EVIDENCE)
    # Tag splits
    for r in train:
        r["split"] = "TRAIN_V2"
        r["surface_id"] = "HYPERLEX_V6_TRAIN_V2"
        r["usable_filter_applied"] = False
    for r in dev:
        r["split"] = "DEV_SELECTION_V2"
        r["surface_id"] = "HYPERLEX_V6_DEV_SELECTION_V2"
        r["usable_filter_applied"] = False
    for r in rep:
        r["split"] = "REPRESENTATIVE_VALIDATION_V2"
        r["surface_id"] = "HYPERLEX_V6_REPRESENTATIVE_VALIDATION_V2"
        r["usable_filter_applied"] = False

    # Dedup by identity within each split; prefer first
    def dedup(rows):
        seen = set()
        out = []
        for r in rows:
            if r["identity"] in seen:
                continue
            seen.add(r["identity"])
            out.append(r)
        return out

    train, dev, rep = dedup(train), dedup(dev), dedup(rep)

    # Cross-split identity exclusivity: REP wins, then DEV, then TRAIN
    rep_ids = {r["identity"] for r in rep}
    dev = [r for r in dev if r["identity"] not in rep_ids]
    dev_ids = {r["identity"] for r in dev}
    train = [r for r in train if r["identity"] not in rep_ids and r["identity"] not in dev_ids]

    return {"TRAIN_V2": train, "DEV_V2": dev, "REP_V2": rep, "colabel_n": len(colabel)}


def disjointness_audit(splits: dict[str, list[dict]], blocked: set[str]) -> dict[str, Any]:
    issues = []
    ids = {}
    texts = {}
    for name, rows in splits.items():
        if name == "colabel_n":
            continue
        ids[name] = {r["identity"] for r in rows}
        texts[name] = {text_hash(r.get("text") or "") for r in rows}
        if any(r.get("usable_filter_applied") for r in rows):
            issues.append(f"{name}_usable_filter_true")
        hit = ids[name] & blocked
        if hit:
            issues.append(f"{name}_blocked_overlap={len(hit)}")
    for a, b in (("TRAIN_V2", "DEV_V2"), ("TRAIN_V2", "REP_V2"), ("DEV_V2", "REP_V2")):
        inter = ids[a] & ids[b]
        if inter:
            issues.append(f"identity_overlap_{a}_{b}={len(inter)}")
        t_inter = texts[a] & texts[b]
        if t_inter:
            issues.append(f"text_overlap_{a}_{b}={len(t_inter)}")
    return {
        "pass": not issues,
        "issues": issues,
        "n_blocked": len(blocked),
        "counts": {k: len(v) for k, v in ids.items()},
    }


def representativeness_audit(rep_rows: list[dict], summary: dict) -> dict[str, Any]:
    from hyperlexical.classification_v6_representative_validation_redesign import (
        REP_V2_MIN_N,
        REP_V2_NO_EVIDENCE_SHARE_RANGE,
        REP_V2_ZERO_LABEL_SHARE_RANGE,
        in_range,
    )

    checks = {
        "no_usable_filter": all(not r.get("usable_filter_applied") for r in rep_rows),
        "includes_zero_label": summary["zero_label_share"] > 0.0,
        "zero_label_in_range": in_range(
            summary["zero_label_share"], *REP_V2_ZERO_LABEL_SHARE_RANGE
        ),
        "no_evidence_in_range": in_range(
            summary["no_evidence_share"], *REP_V2_NO_EVIDENCE_SHARE_RANGE
        ),
        "has_function_labels": summary["n_function_positive"] >= 80,
        "has_positive_traffic": summary["evidence_present_share"] > 0.15,
        "has_multi_label": summary["n_multi_label"] >= 20,
        # Domain+function remains scarce in foundation gold; require multi-label
        # composition coverage and record DF count separately.
        "has_multi_axis_or_df": (
            summary["n_domain_plus_function"] >= 1
            or summary["composition"].get("domain+mediation", 0)
            + summary["composition"].get("function+mediation", 0)
            >= 3
        ),
        "source_diversity": summary["n_source_families"] >= 20,
        "length_diversity": len(summary["length"]) >= 2,
        "observed_majority": summary["observed_share"] >= 0.9,
        "natural_majority": summary["natural_share"] >= 0.9,
        "min_n": summary["n"] >= REP_V2_MIN_N,
        "not_positive_only": summary["zero_label_share"] >= 0.55,
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "summary": summary,
    }


def inner() -> int:
    import numpy as np
    import torch

    from hyperlexical.classification_v6_architecture_reset_bakeoff import AXIS_VOCABS
    from hyperlexical.classification_v6_qualification_execute_002 import (
        EXPECTED_ENCODER_STATE_HASH,
        EXPECTED_PACKAGE_SHA256,
        REP_REFERENCE_SYSTEM_MACRO_F1,
    )
    from hyperlexical.classification_v6_representative_validation_redesign import (
        DEV_V2_ID,
        PHASE_RULE,
        REP_V2_ID,
        TRAIN_V2_ID,
        build_redesign_receipt,
        classify_remaining_model_failure,
        classify_representativeness_repair,
        decide_next_action,
        redesign_contract,
    )
    from hyperlexical.classification_v6_semantic_pipeline_harden import (
        BAKEOFF_THRESHOLDS,
        SELECTED_ENCODER_MODEL_ID,
        SELECTED_ENCODER_REVISION,
    )

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    REPO_ART.mkdir(parents=True, exist_ok=True)
    contract = redesign_contract()
    write_private(PRIVATE / "CONTRACT.json", contract)
    write_repo(REPO_ART / "contract.json", contract)

    # Integrity: package frozen
    package = load_json(PRIVATE_PKG / "PACKAGE.json")
    if package.get("PACKAGE_SHA256") != EXPECTED_PACKAGE_SHA256:
        raise SystemExit("package_sha_mismatch")

    print("join_foundation_migration", flush=True)
    joined = join_foundation_migration()
    blocked = blocked_identities()
    print(
        f"blocked={len(blocked)} train/dev/rep="
        f"{len(joined['TRAIN'])}/{len(joined['DEV'])}/{len(joined['REP'])}",
        flush=True,
    )

    print("build_v2_splits", flush=True)
    built = build_v2_splits(joined, blocked)
    train, dev, rep = built["TRAIN_V2"], built["DEV_V2"], built["REP_V2"]
    print(
        f"V2 sizes train/dev/rep={len(train)}/{len(dev)}/{len(rep)} colabel={built['colabel_n']}",
        flush=True,
    )

    # Disjointness + audits
    dj = disjointness_audit(
        {"TRAIN_V2": train, "DEV_V2": dev, "REP_V2": rep}, blocked
    )
    train_s, dev_s, rep_s = dist_summary(train), dist_summary(dev), dist_summary(rep)
    rep_audit = representativeness_audit(rep, rep_s)
    write_private(PRIVATE / "DISJOINTNESS_WITNESS.json", dj)
    write_private(
        PRIVATE / "DISTRIBUTIONS.json",
        {"TRAIN_V2": train_s, "DEV_V2": dev_s, "REP_V2": rep_s},
    )
    write_private(PRIVATE / "REPRESENTATIVENESS_AUDIT.json", rep_audit)
    write_repo(REPO_ART / "distributions.json", {"TRAIN_V2": train_s, "DEV_V2": dev_s, "REP_V2": rep_s})
    write_repo(REPO_ART / "representativeness_audit.json", rep_audit)
    write_repo(REPO_ART / "disjointness_witness.json", dj)

    if not dj["pass"]:
        summary = {
            "PHASE_RULE": PHASE_RULE,
            "state": "INTEGRITY_BLOCKED",
            "issues": dj["issues"],
            "NEXT_ACTION": "REPAIR_V6_REPRESENTATIVE_VALIDATION_V2_INTEGRITY",
        }
        write_private(PRIVATE / "SUMMARY.json", summary)
        print(json.dumps(summary, indent=2))
        return 2

    # Persist surfaces
    write_jsonl(PRIVATE / "TRAIN_V2.jsonl", train)
    write_jsonl(PRIVATE / "DEV_SELECTION_V2.jsonl", dev)
    write_jsonl(PRIVATE / "REPRESENTATIVE_VALIDATION_V2.jsonl", rep)
    write_private(
        PRIVATE / "SURFACE_MANIFEST.json",
        {
            "TRAIN_V2_ID": TRAIN_V2_ID,
            "DEV_V2_ID": DEV_V2_ID,
            "REP_V2_ID": REP_V2_ID,
            "n_train": len(train),
            "n_dev": len(dev),
            "n_rep": len(rep),
            "train_sha256": sha256_text(
                "\n".join(json.dumps(r, sort_keys=True) for r in train)
            ),
            "dev_sha256": sha256_text(
                "\n".join(json.dumps(r, sort_keys=True) for r in dev)
            ),
            "rep_sha256": sha256_text(
                "\n".join(json.dumps(r, sort_keys=True) for r in rep)
            ),
            "usable_filter_applied": False,
            "forbidden_filters_absent": True,
        },
    )

    # QUAL aggregate comparison inputs (no row reuse)
    qual_primary = load_json(PRIVATE_EXEC / "PRIMARY_METRICS.json")
    qual_rows = load_jsonl(PRIVATE_QUAL / "QUALIFICATION_ROWS.jsonl")
    qual_preds = {
        p["identity"]: p for p in load_jsonl(PRIVATE_EXEC / "RAW_PREDICTIONS.jsonl")
    }
    q_zero = [r for r in qual_rows if n_lab(r) == 0]
    q_zero_fp = 0
    for r in q_zero:
        p = qual_preds[r["identity"]]
        npred = (
            len(p["final_domain_labels"])
            + len(p["final_function_labels"])
            + len(p["final_mediation_labels"])
        )
        if npred:
            q_zero_fp += 1
    qual_aggregate = {
        "system_macro_f1": qual_primary["system_macro_f1"],
        "DOMAIN_macro_f1": qual_primary["DOMAIN_macro_f1"],
        "FUNCTION_macro_f1": qual_primary["FUNCTION_macro_f1"],
        "MEDIATION_macro_f1": qual_primary["MEDIATION_macro_f1"],
        "zero_label_false_positive_rate": q_zero_fp / max(1, len(q_zero)),
        "zero_label_share": len(q_zero) / max(1, len(qual_rows)),
        "n": len(qual_rows),
        "role": "AGGREGATE_HISTORICAL_COMPARISON_ONLY",
    }

    # Frozen replay
    vocabs = {
        "domain": list(AXIS_VOCABS["domain"]),
        "function": list(AXIS_VOCABS["function"]),
        "mediation": list(AXIS_VOCABS["mediation"]),
    }
    thresholds = {a: list(BAKEOFF_THRESHOLDS[a]) for a in vocabs}
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"frozen_replay device={device}", flush=True)
    heads = load_heads(PRIVATE_PKG / "heads" / "axis_nonlinear_heads.pt", vocabs, device)

    def replay(rows, tag):
        print(f"encode_{tag} n={len(rows)}", flush=True)
        X, enc_hash, n_tr = embed_model(
            SELECTED_ENCODER_MODEL_ID,
            [r.get("text") or "" for r in rows],
            device,
            revision=SELECTED_ENCODER_REVISION,
        )
        if n_tr != 0:
            raise SystemExit("encoder_trainable_nonzero")
        if enc_hash != EXPECTED_ENCODER_STATE_HASH:
            raise SystemExit("encoder_hash_mismatch")
        scores = scores_from_heads(heads, X, device)
        return evaluate_surface(rows, scores, vocabs, thresholds, tech_idx, ai_idx)

    dev_replay = replay(dev, "DEV_V2")
    rep_replay = replay(rep, "REP_V2")
    write_private(PRIVATE / "DEV_V2_REPLAY.json", dev_replay)
    write_private(PRIVATE / "REP_V2_REPLAY.json", rep_replay)
    write_repo(REPO_ART / "dev_v2_replay.json", dev_replay)
    write_repo(REPO_ART / "rep_v2_replay.json", rep_replay)

    repair = classify_representativeness_repair(
        rep_audit_pass=rep_audit["pass"],
        replay=rep_replay,
        qual_aggregate=qual_aggregate,
    )
    remaining = classify_remaining_model_failure(rep_replay)
    next_action = decide_next_action(
        representativeness_repaired=repair["REPRESENTATIVENESS_REPAIRED"],
        remaining_failure=remaining["REMAINING_MODEL_FAILURE"],
    )

    receipt = build_redesign_receipt(
        {
            "PHASE_RULE": PHASE_RULE,
            "TRAIN_V2_ID": TRAIN_V2_ID,
            "DEV_V2_ID": DEV_V2_ID,
            "REP_V2_ID": REP_V2_ID,
            "distributions": {
                "TRAIN_V2": train_s,
                "DEV_V2": dev_s,
                "REP_V2": rep_s,
            },
            "representativeness_audit": rep_audit,
            "disjointness": dj,
            "frozen_model_replay": {
                "DEV_V2": dev_replay,
                "REP_V2": rep_replay,
                "package_sha256": EXPECTED_PACKAGE_SHA256,
                "old_usable_REP_system_macro_f1": REP_REFERENCE_SYSTEM_MACRO_F1,
            },
            "qual_002_aggregate_comparison": qual_aggregate,
            "REPRESENTATIVENESS_REPAIRED": repair["REPRESENTATIVENESS_REPAIRED"],
            "representativeness_repair_detail": repair,
            "REMAINING_MODEL_FAILURE": remaining["REMAINING_MODEL_FAILURE"],
            "remaining_failure_detail": remaining,
            "NEXT_ACTION": next_action,
            "colabel_discovered_n": built["colabel_n"],
            "code_revision": code_revision(),
        }
    )
    write_private(PRIVATE / "RECEIPT.json", receipt)
    write_repo(REPO_ART / "receipt.json", receipt)
    write_repo(REPO_ART / "RECEIPT.json", receipt)
    write_repo(
        SPEC
        / "classification-v6-representative-validation-redesign-receipt-20261001.json",
        receipt,
    )

    summary = {
        "PHASE_RULE": PHASE_RULE,
        "REPRESENTATIVENESS_REPAIRED": repair["REPRESENTATIVENESS_REPAIRED"],
        "REMAINING_MODEL_FAILURE": remaining["REMAINING_MODEL_FAILURE"],
        "NEXT_ACTION": next_action,
        "TRAIN_V2_n": len(train),
        "DEV_V2_n": len(dev),
        "REP_V2_n": len(rep),
        "REP_V2_zero_label_share": rep_s["zero_label_share"],
        "REP_V2_no_evidence_share": rep_s["no_evidence_share"],
        "REP_V2_domain_plus_function_n": rep_s["n_domain_plus_function"],
        "REP_V2_system_macro_f1": rep_replay["system_macro_f1"],
        "REP_V2_FUNCTION_macro_f1": rep_replay["FUNCTION_macro_f1"],
        "REP_V2_zero_fp_rate": rep_replay["zero_label_false_positive_rate"],
        "DEV_V2_system_macro_f1": dev_replay["system_macro_f1"],
        "old_usable_REP_system_macro_f1": REP_REFERENCE_SYSTEM_MACRO_F1,
        "QUAL_system_macro_f1": qual_aggregate["system_macro_f1"],
        "same_failure_shape_as_QUAL": repair["same_broad_failure_shape_as_QUAL_002"],
        "MODEL_WIDE_BEST_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "RECEIPT": receipt["V6_REPRESENTATIVE_VALIDATION_REDESIGN_RECEIPT_SHA256"],
    }
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_repo(REPO_ART / "summary.json", summary)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_private(
        PRIVATE / "POINTER.json",
        {
            "MODEL_WIDE_BEST_MUTATED": False,
            "V5_POINTERS_MUTATED": False,
            "PACKAGE_SHA256": EXPECTED_PACKAGE_SHA256,
            "HUB_PUBLISH_AUTHORIZED": False,
            "V6_REPRESENTATION_CANDIDATE_STATUS": "QUALIFICATION_FAILED",
        },
    )

    md = f"""# REDESIGN_V6_REPRESENTATIVE_VALIDATION_AND_DATA_DIVERSITY

```text
REPRESENTATIVENESS_REPAIRED = {repair['REPRESENTATIVENESS_REPAIRED']}
REMAINING_MODEL_FAILURE = {remaining['REMAINING_MODEL_FAILURE']}
NEXT_ACTION = {next_action}
REP_V2 n = {len(rep)} zero_label_share = {rep_s['zero_label_share']:.3f}
REP_V2 system macro-F1 = {rep_replay['system_macro_f1']:.4f}
REP_V2 FUNCTION macro-F1 = {rep_replay['FUNCTION_macro_f1']:.4f}
REP_V2 zero-label FP rate = {rep_replay['zero_label_false_positive_rate']:.3f}
old usable REP ≈ {REP_REFERENCE_SYSTEM_MACRO_F1:.3f}
QUAL-002 system macro-F1 = {qual_aggregate['system_macro_f1']:.4f}
RECEIPT = {receipt['V6_REPRESENTATIVE_VALIDATION_REDESIGN_RECEIPT_SHA256']}
```

Removed `usable()` positive-only filtering. REP_V2 includes NONE/NO_EVIDENCE
mass and dual-discovered co-labels. Hardened package `{EXPECTED_PACKAGE_SHA256[:12]}…`
replayed unchanged. QUAL-002 rows not used for optimization.
"""
    write_repo(
        SPEC / "classification-v6-representative-validation-redesign-20261001.md", md
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if repair["REPRESENTATIVENESS_REPAIRED"] or rep_audit["pass"] else 2


def main() -> int:
    if os.environ.get("HLX_V6_REP_REDESIGN_INNER") == "1":
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
        "HLX_V6_REP_REDESIGN_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(
            REPO
            / "scripts/spark/run_classification_v6_representative_validation_redesign.py"
        ),
    ]
    log = PRIVATE / "redesign_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(
            cmd, check=False, stdout=handle, stderr=subprocess.STDOUT
        )
    try:
        print(log.read_text(encoding="utf-8")[-60000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
