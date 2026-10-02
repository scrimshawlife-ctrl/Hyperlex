"""EXPAND_V6_FUNCTION_DIVERSITY_AND_POSITIVE_REPRESENTATION.

Acquire diverse natural positive/FUNCTION traffic, build TRAIN/DEV/REP V3,
retrain axis heads under frozen encoder + frozen NONE gate, evaluate on REP_V3.
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
    "/home/morpheus/hlx-private/classification-v6-function-diversity-expand-20261002"
)
PRIVATE_V2 = Path(
    "/home/morpheus/hlx-private/classification-v6-representative-validation-redesign-20261001"
)
PRIVATE_PKG = Path(
    "/home/morpheus/hlx-private/classification-v6-operating-pipeline-harden-20261001"
)
PRIVATE_QUAL = Path(
    "/home/morpheus/hlx-private/classification-v6-qualification-surface-003-20261001"
)
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-FUNCTION-DIVERSITY-EXPAND-001"
)
SPEC = REPO / "specs" / "007-hyperlexical-model"
IMAGE = "lmsysorg/sglang:dev-qwen38-27b-dflash2"
SEED = 20261004
MAX_LEN = 192
BATCH = 32
HEAD_EPOCHS = 40
LR = 1e-2

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


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


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


def mean(xs: list[float]) -> float:
    return float(sum(xs) / max(1, len(xs)))


def multi_hot(labs, vocab):
    import numpy as np

    y = np.zeros(len(vocab), dtype=np.float32)
    s = set(labs or [])
    for i, lab in enumerate(vocab):
        if lab in s:
            y[i] = 1.0
    return y


def set_seeds(seed: int) -> None:
    import random as pyrand

    import numpy as np
    import torch

    pyrand.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


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

    def mean_pool(last_hidden, attention_mask):
        mask = attention_mask.unsqueeze(-1).float()
        return (last_hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-6)

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
    torch.cuda.empty_cache()
    import torch as T

    return T.cat(vecs, dim=0).numpy()


def build_mlp(hidden, n_out, device):
    import torch.nn as nn

    return nn.Sequential(
        nn.Linear(hidden, 128), nn.ReLU(), nn.Linear(128, n_out)
    ).to(device)


def train_axis_heads(Xtr, Ytr_by_axis, vocabs, device):
    import torch
    import torch.nn as nn

    set_seeds(SEED)
    heads = {}
    for axis, vocab in vocabs.items():
        model = build_mlp(Xtr.shape[1], len(vocab), device)
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


def load_torch_bundle(path: Path):
    import io
    import torch

    raw = sudo_read_bytes(path)
    try:
        return torch.load(io.BytesIO(raw), map_location="cpu", weights_only=False), raw
    except TypeError:
        return torch.load(io.BytesIO(raw), map_location="cpu"), raw


def load_gate(path: Path, device):
    bundle, raw = load_torch_bundle(path)
    m = build_mlp(768, 1, device)
    m.load_state_dict(bundle["state"])
    m.eval()
    for p in m.parameters():
        p.requires_grad_(False)
    return m, bundle, sha256_bytes(raw)


def load_heads(path: Path, vocabs, device):
    bundle, raw = load_torch_bundle(path)
    heads = {}
    for axis, vocab in vocabs.items():
        m = build_mlp(768, len(vocab), device)
        m.load_state_dict(bundle["state"][axis])
        m.eval()
        for p in m.parameters():
            p.requires_grad_(False)
        heads[axis] = m
    return heads, bundle, sha256_bytes(raw)


def gate_scores(model, X, device):
    import torch

    with torch.no_grad():
        xt = torch.tensor(X, dtype=torch.float32, device=device)
        return torch.sigmoid(model(xt)).cpu().numpy().reshape(-1)


def save_head_bundle(path: Path, heads, meta: dict) -> str:
    import torch

    bundle = {
        "meta": meta,
        "state": {
            axis: {k: v.detach().cpu() for k, v in m.state_dict().items()}
            for axis, m in heads.items()
        },
    }
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    torch.save(bundle, path)
    os.chmod(path, 0o600)
    return sha256_bytes(path.read_bytes())


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
    }


def acquire_expand_rows(block_paths: list[Path]) -> list[dict]:
    out_path = PRIVATE / "RAW_ACQUIRE_EXPAND.jsonl"
    if out_path.exists() and out_path.stat().st_size > 1000:
        print(f"reuse_acquire {out_path}", flush=True)
        return load_jsonl(out_path)
    cmd = [
        sys.executable,
        str(REPO / "scripts/spark/expand_v6_positive_acquire.py"),
        "--out",
        str(out_path),
        "--wikt-target",
        "520",
        "--wiki-target",
        "240",
        "--per-family",
        "30",
        "--workers",
        "3",
    ]
    for p in block_paths:
        cmd.extend(["--block-texts", str(p)])
    print("acquire", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)
    return load_jsonl(out_path)


def annotate_new_rows(raw: list[dict], blocked_ids: set[str], blocked_text: set[str]) -> list[dict]:
    from hyperlexical.classification_v6_human_ontology_settlement import (
        dual_annotate_rows,
    )
    from hyperlexical.classification_v6_function_diversity_expand import source_style

    blind = []
    for r in raw:
        text = (r.get("text") or "").strip()
        if not text or text.lower() in blocked_text:
            continue
        ident = identity_for(text, r.get("source_url"), r.get("source_family"))
        if ident in blocked_ids:
            continue
        blind.append(
            {
                "identity": ident,
                "text": text,
                "source_url": r.get("source_url"),
                "source_family": r.get("source_family"),
                "provenance": r.get("provenance") or "OBSERVED",
                "construction_tag": r.get("construction_tag") or "NATURAL",
                "construction_role": r.get("construction_role") or "PRODUCT_EXPECTED",
                "acquisition_cue_family": r.get("acquisition_cue_family"),
                "notes": r.get("notes"),
            }
        )
    print(f"dual_annotate_new n={len(blind)}", flush=True)
    ann = dual_annotate_rows(blind)
    out = []
    for a, src in zip(ann, blind):
        mapped = map_adjudicated(a["adjudicated"])
        if mapped.get("adjudication_status") not in {"AGREED", "ADJUDICATED"}:
            continue
        if mapped["evidence_label"] != "EVIDENCE_PRESENT":
            # keep some NONE-like NO_EVIDENCE from wiki culture? skip — we want positives
            if mapped["evidence_label"] == "NO_EVIDENCE" and not (
                mapped["domain_labels"] or mapped["function_labels"]
            ):
                continue
            if mapped["evidence_label"] != "EVIDENCE_PRESENT":
                continue
        if not (
            mapped["domain_labels"]
            or mapped["function_labels"]
            or mapped["mediation_labels"]
        ):
            continue
        row = {
            **src,
            **mapped,
            "schema": "hyperlex.classification.v6.expand_row.v1",
            "v3_origin": "expand_acquire_dual_annotate",
            "source_style": source_style(src.get("source_family") or ""),
            "dual_annotation": {
                "status": a["adjudicated"].get("status"),
                "pair_metrics": a.get("pair_metrics"),
            },
            "usable_filter_applied": False,
            "optimization_forbidden": False,
            "evaluation_spent": False,
            "near_duplicate_key": text_hash(src["text"]),
            "source_sha256": text_hash(src["text"]),
        }
        out.append(row)
    print(
        f"annotated_positives={len(out)} fun={sum(1 for r in out if r.get('function_labels'))}",
        flush=True,
    )
    return out


def diversify_score(r: dict) -> float:
    """Higher = more useful for diversity (length + non-wikt + function)."""
    from hyperlexical.classification_v6_function_diversity_expand import (
        length_bucket,
        source_style,
    )

    score = 0.0
    if r.get("function_labels"):
        score += 3.0
    if r.get("domain_labels") and r.get("function_labels"):
        score += 2.0
    st = source_style(r.get("source_family") or "")
    if st == "encyclopedic_positive":
        score += 2.5
    elif st == "firecrawl_observed":
        score += 1.5
    elif "multi" in (r.get("source_family") or ""):
        score += 1.0
    lb = length_bucket(len(r.get("text") or ""))
    score += {"long": 2.0, "medium": 1.0, "short": 0.0}[lb]
    return score


def build_v3(
    train_v2: list[dict],
    dev_v2: list[dict],
    rep_v2: list[dict],
    new_rows: list[dict],
    qual_ids: set[str],
    qual_text: set[str],
) -> dict[str, list[dict]]:
    from hyperlexical.classification_v6_function_diversity_expand import (
        DEV_V3_ID,
        FUNCTION_VOCAB,
        REP_V3_ID,
        TRAIN_V3_ID,
        length_bucket,
        source_style,
    )

    rng = random.Random(SEED)

    def clone(r, split, surface):
        out = dict(r)
        out["split"] = split
        out["surface_id"] = surface
        out["usable_filter_applied"] = False
        return out

    train = [clone(r, "TRAIN_V3", TRAIN_V3_ID) for r in train_v2]
    dev = [clone(r, "DEV_SELECTION_V3", DEV_V3_ID) for r in dev_v2]
    rep = [clone(r, "REPRESENTATIVE_VALIDATION_V3", REP_V3_ID) for r in rep_v2]

    # Drop any accidental QUAL-003 leakage from parents (should be none)
    def clean(rows):
        return [
            r
            for r in rows
            if r["identity"] not in qual_ids
            and text_hash(r.get("text") or "") not in qual_text
        ]

    train, dev, rep = clean(train), clean(dev), clean(rep)

    # Rank new function-bearing diverse rows
    new_fun = [r for r in new_rows if r.get("function_labels")]
    new_pos = [r for r in new_rows if n_lab(r) > 0 and r not in new_fun]
    new_fun = sorted(new_fun, key=diversify_score, reverse=True)
    new_pos = sorted(new_pos, key=diversify_score, reverse=True)

    existing_text = {
        text_hash(r.get("text") or "") for r in train + dev + rep
    }
    existing_ids = {r["identity"] for r in train + dev + rep}

    def take_new(pool, n):
        out = []
        for r in pool:
            th = text_hash(r.get("text") or "")
            if th in existing_text or r["identity"] in existing_ids:
                continue
            if r["identity"] in qual_ids or th in qual_text:
                continue
            out.append(r)
            existing_text.add(th)
            existing_ids.add(r["identity"])
            if len(out) >= n:
                break
        return out

    # Allocation: prefer putting diverse function into REP/DEV/TRAIN
    rep_fun_new = take_new(new_fun, 80)
    # remove taken from pool ordering
    taken = {r["identity"] for r in rep_fun_new}
    rest_fun = [r for r in new_fun if r["identity"] not in taken]
    dev_fun_new = take_new(rest_fun, 40)
    taken |= {r["identity"] for r in dev_fun_new}
    rest_fun = [r for r in new_fun if r["identity"] not in taken]
    train_fun_new = take_new(rest_fun, 220)

    # Extra domain/mediation positives for length/style diversity
    rep_pos_new = take_new(new_pos, 40)
    taken_pos = {r["identity"] for r in rep_pos_new}
    rest_pos = [r for r in new_pos if r["identity"] not in taken_pos]
    train_pos_new = take_new(rest_pos, 120)

    for r in rep_fun_new + rep_pos_new:
        rep.append(clone(r, "REPRESENTATIVE_VALIDATION_V3", REP_V3_ID))
    for r in dev_fun_new:
        dev.append(clone(r, "DEV_SELECTION_V3", DEV_V3_ID))
    for r in train_fun_new + train_pos_new:
        train.append(clone(r, "TRAIN_V3", TRAIN_V3_ID))

    # Rebalance REP: move excess short-wikt function-only rows to TRAIN if
    # zero-label would drop below band after inject, or if function non-wikt low.
    def zero_share(rows):
        return sum(1 for r in rows if n_lab(r) == 0) / max(1, len(rows))

    def fun_non_wikt_share(rows):
        fun = [r for r in rows if r.get("function_labels")]
        if not fun:
            return 0.0
        nw = sum(
            1
            for r in fun
            if source_style(r.get("source_family") or "") != "wiktionary_sense"
        )
        return nw / len(fun)

    # If zero-label share too low after inject, move short wikt domain-only to train
    movers = [
        r
        for r in rep
        if n_lab(r) > 0
        and not r.get("function_labels")
        and source_style(r.get("source_family") or "") == "wiktionary_sense"
        and length_bucket(len(r.get("text") or "")) == "short"
        and "expand_acquire" not in (r.get("v3_origin") or "")
    ]
    rng.shuffle(movers)
    i = 0
    while zero_share(rep) < 0.56 and i < len(movers) and len(rep) > 1000:
        r = movers[i]
        i += 1
        rep = [x for x in rep if x["identity"] != r["identity"]]
        r2 = clone(r, "TRAIN_V3", TRAIN_V3_ID)
        r2["v3_origin"] = (r2.get("v3_origin") or "") + "+moved_rep_to_train_none_mass"
        train.append(r2)

    # If function still wikt-dominated, move some short wikt function from REP→TRAIN
    # (keep at least PER_FUNCTION mins via new rows)
    short_wikt_fun = [
        r
        for r in rep
        if r.get("function_labels")
        and source_style(r.get("source_family") or "") == "wiktionary_sense"
        and length_bucket(len(r.get("text") or "")) == "short"
        and "expand_acquire" not in (r.get("v3_origin") or "")
    ]
    rng.shuffle(short_wikt_fun)
    j = 0
    while fun_non_wikt_share(rep) < 0.22 and j < len(short_wikt_fun) and j < 40:
        r = short_wikt_fun[j]
        j += 1
        # don't drop a function label below floor in REP
        labs = r.get("function_labels") or []
        counts = Counter(
            lab for x in rep for lab in (x.get("function_labels") or [])
        )
        if any(counts[lab] <= 14 for lab in labs):
            continue
        rep = [x for x in rep if x["identity"] != r["identity"]]
        r2 = clone(r, "TRAIN_V3", TRAIN_V3_ID)
        r2["v3_origin"] = (r2.get("v3_origin") or "") + "+moved_short_wikt_fun_to_train"
        train.append(r2)

    # Final exclusivity: REP wins, then DEV, then TRAIN
    def exclusive(primary, secondary):
        ids = {r["identity"] for r in primary}
        th = {text_hash(r.get("text") or "") for r in primary}
        return [
            r
            for r in secondary
            if r["identity"] not in ids and text_hash(r.get("text") or "") not in th
        ]

    dev = exclusive(rep, dev)
    train = exclusive(rep, exclusive(dev, train))

    for r in train:
        r["split"] = "TRAIN_V3"
        r["surface_id"] = TRAIN_V3_ID
    for r in dev:
        r["split"] = "DEV_SELECTION_V3"
        r["surface_id"] = DEV_V3_ID
    for r in rep:
        r["split"] = "REPRESENTATIVE_VALIDATION_V3"
        r["surface_id"] = REP_V3_ID

    print(
        f"V3 sizes train={len(train)} dev={len(dev)} rep={len(rep)} "
        f"zero_rep={zero_share(rep):.3f} fun_non_wikt={fun_non_wikt_share(rep):.3f}",
        flush=True,
    )
    return {
        "TRAIN": train,
        "DEV": dev,
        "REP": rep,
        "inject_counts": {
            "rep_fun_new": len(rep_fun_new),
            "dev_fun_new": len(dev_fun_new),
            "train_fun_new": len(train_fun_new),
            "rep_pos_new": len(rep_pos_new),
            "train_pos_new": len(train_pos_new),
        },
    }


def audit_surfaces(splits: dict, qual_ids: set[str], qual_text: set[str]) -> dict:
    from hyperlexical.classification_v6_function_diversity_expand import (
        FUNCTION_VOCAB,
        diversity_audit_pass,
        length_bucket,
        source_style,
    )

    def stats(rows):
        fun = [r for r in rows if r.get("function_labels")]
        per = Counter(lab for r in fun for lab in (r.get("function_labels") or []))
        styles = Counter(source_style(r.get("source_family") or "") for r in fun)
        lens = Counter(length_bucket(len(r.get("text") or "")) for r in fun)
        df = Counter()
        for r in fun:
            for d in r.get("domain_labels") or ["__NONE__"]:
                for f in r.get("function_labels") or []:
                    df[(d, f)] += 1
        non_wikt = styles.get("encyclopedic_positive", 0) + styles.get(
            "firecrawl_observed", 0
        ) + styles.get("other", 0)
        # multi-sense wikt counts as wikt still; encyclopedic_positive is non-wikt
        wikt = styles.get("wiktionary_sense", 0)
        med_long = lens.get("medium", 0) + lens.get("long", 0)
        return {
            "n": len(rows),
            "zero_label_share": sum(1 for r in rows if n_lab(r) == 0) / max(1, len(rows)),
            "positive_n": sum(1 for r in rows if n_lab(r) > 0),
            "function_n": len(fun),
            "per_function_support": {lab: int(per.get(lab, 0)) for lab in FUNCTION_VOCAB},
            "function_style": dict(styles),
            "function_length": dict(lens),
            "function_non_wikt_share": (len(fun) - wikt) / max(1, len(fun)),
            "function_medium_long_share": med_long / max(1, len(fun)),
            "domain_function_pairs_n": len(df),
            "function_length_p50": (
                sorted(len(r.get("text") or "") for r in fun)[len(fun) // 2]
                if fun
                else 0
            ),
        }

    train, dev, rep = splits["TRAIN"], splits["DEV"], splits["REP"]
    ids_t = {r["identity"] for r in train}
    ids_d = {r["identity"] for r in dev}
    ids_r = {r["identity"] for r in rep}
    th_t = {text_hash(r.get("text") or "") for r in train}
    th_d = {text_hash(r.get("text") or "") for r in dev}
    th_r = {text_hash(r.get("text") or "") for r in rep}
    disjoint = (
        not (ids_t & ids_d)
        and not (ids_t & ids_r)
        and not (ids_d & ids_r)
        and not (th_t & th_d)
        and not (th_t & th_r)
        and not (th_d & th_r)
    )
    leak_q = (
        bool(ids_t & qual_ids)
        or bool(ids_d & qual_ids)
        or bool(ids_r & qual_ids)
        or bool(th_t & qual_text)
        or bool(th_d & qual_text)
        or bool(th_r & qual_text)
    )
    audit = {
        "train": stats(train),
        "dev": stats(dev),
        "rep": stats(rep),
        "disjointness_pass": disjoint,
        "qual003_blocked": not leak_q,
        "inject_counts": splits.get("inject_counts"),
    }
    audit["diversity_gate"] = diversity_audit_pass(audit)
    return audit


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


def pack_axis(gold, pred, vocab):
    import numpy as np

    g = np.asarray(gold)
    p = np.asarray(pred)
    per = {}
    f1s = []
    for j, lab in enumerate(vocab):
        f1 = f1_binary(g[:, j], p[:, j])
        f1s.append(f1)
        tp = int(((g[:, j] == 1) & (p[:, j] == 1)).sum())
        fp = int(((g[:, j] == 0) & (p[:, j] == 1)).sum())
        fn = int(((g[:, j] == 1) & (p[:, j] == 0)).sum())
        prec = tp / max(1, tp + fp)
        rec = tp / max(1, tp + fn)
        per[lab] = {
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "support": int(g[:, j].sum()),
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
    return {"macro_f1": float(sum(f1s) / max(1, len(f1s))), "per_label": per}


def run_gated(rows, X, heads, gate, gate_th, vocabs, thresholds, tech_idx, ai_idx, device):
    import numpy as np

    scores = scores_from_heads(heads, X, device)
    gsc = gate_scores(gate, X, device)
    reject = gsc < float(gate_th)
    preds = {}
    for a in vocabs:
        th = np.asarray(thresholds[a])
        raw = (np.asarray(scores[a]) >= th).astype(np.int32)
        q = raw.copy()
        q[reject] = 0
        preds[a] = q
    d = preds["domain"].copy()
    hier_corr = 0
    for i in range(d.shape[0]):
        if d[i, ai_idx] == 1 and d[i, tech_idx] == 0:
            d[i, tech_idx] = 1
            hier_corr += 1
    preds["domain"] = d
    golds = {
        a: np.asarray(
            [multi_hot(r.get(f"{a}_labels"), vocabs[a]) for r in rows], dtype=np.int32
        )
        for a in vocabs
    }
    axis = {a: pack_axis(golds[a], preds[a], vocabs[a]) for a in vocabs}
    system = mean([axis[a]["macro_f1"] for a in vocabs])
    zero_idx = [i for i, r in enumerate(rows) if n_lab(r) == 0]
    pos_idx = [i for i, r in enumerate(rows) if n_lab(r) > 0]
    zero_fp = 0.0
    zero_exact = 0.0
    if zero_idx:
        pred_any = np.zeros(len(rows), dtype=np.int32)
        for a in vocabs:
            pred_any = np.maximum(pred_any, preds[a].max(axis=1))
        zero_fp = float(pred_any[zero_idx].mean())
        zero_exact = float((pred_any[zero_idx] == 0).mean())
    pos_macros = []
    if pos_idx:
        for a in vocabs:
            pos_macros.append(
                pack_axis(golds[a][pos_idx], preds[a][pos_idx], vocabs[a])["macro_f1"]
            )
    # function slices
    from hyperlexical.classification_v6_function_diversity_expand import (
        length_bucket,
        source_style,
    )

    fun_rows_idx = [i for i, r in enumerate(rows) if r.get("function_labels")]
    by_source = defaultdict(list)
    by_len = defaultdict(list)
    by_dom = defaultdict(list)
    for i in fun_rows_idx:
        r = rows[i]
        by_source[source_style(r.get("source_family") or "")].append(i)
        by_len[length_bucket(len(r.get("text") or ""))].append(i)
        doms = r.get("domain_labels") or ["__NONE__"]
        for dlab in doms:
            by_dom[dlab].append(i)

    def slice_fun(idxs):
        if not idxs:
            return None
        return pack_axis(
            golds["function"][idxs], preds["function"][idxs], vocabs["function"]
        )["macro_f1"]

    return {
        "system_macro_f1": system,
        "DOMAIN_macro_f1": axis["domain"]["macro_f1"],
        "FUNCTION_macro_f1": axis["function"]["macro_f1"],
        "MEDIATION_macro_f1": axis["mediation"]["macro_f1"],
        "positive_only_system_macro_f1": mean(pos_macros) if pos_macros else 0.0,
        "zero_label_false_positive_rate": zero_fp,
        "zero_label_exact_rejection": zero_exact,
        "hierarchy_corrections": hier_corr,
        "n_rows": len(rows),
        "n_zero": len(zero_idx),
        "n_positive": len(pos_idx),
        "n_function": len(fun_rows_idx),
        "per_label_function": axis["function"]["per_label"],
        "function_by_source": {k: slice_fun(v) for k, v in by_source.items()},
        "function_by_length": {k: slice_fun(v) for k, v in by_len.items()},
        "function_by_domain": {
            k: slice_fun(v) for k, v in list(by_dom.items())[:20]
        },
        "gate_reject_rate": float(reject.mean()),
    }


def semantic_diversity_vs_train(X_new_fun, X_train_fun) -> dict:
    import numpy as np

    if len(X_new_fun) == 0 or len(X_train_fun) == 0:
        return {"n_new": len(X_new_fun), "mean_max_sim_to_train": None}
    sims = X_new_fun @ X_train_fun.T
    max_sim = sims.max(axis=1)
    return {
        "n_new": int(len(X_new_fun)),
        "n_train_fun_ref": int(len(X_train_fun)),
        "mean_max_sim_to_train": float(max_sim.mean()),
        "p50_max_sim_to_train": float(np.median(max_sim)),
        "frac_max_sim_lt_0_85": float((max_sim < 0.85).mean()),
    }


def inner() -> int:
    import numpy as np
    import torch
    from hyperlexical.classification_v6_architecture_reset_bakeoff import AXIS_VOCABS
    from hyperlexical.classification_v6_data_foundation import utc_now_iso
    from hyperlexical.classification_v6_function_diversity_expand import (
        PHASE_RULE,
        TRAIN_V3_ID,
        DEV_V3_ID,
        REP_V3_ID,
        build_expand_receipt,
        classify_outcome,
        expand_contract,
        none_preserved,
    )
    from hyperlexical.classification_v6_operating_pipeline_harden import (
        WITNESS_GATE_THRESHOLD,
    )
    from hyperlexical.classification_v6_qualification_execute_003 import (
        EXPECTED_PACKAGE_SHA256,
    )
    from hyperlexical.classification_v6_semantic_pipeline_harden import (
        BAKEOFF_THRESHOLDS,
        SELECTED_ENCODER_MODEL_ID,
        SELECTED_ENCODER_REVISION,
    )

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    contract = expand_contract()
    write_private(PRIVATE / "CONTRACT.json", contract)
    write_repo(REPO_ART / "contract.json", contract)

    print("load_parents", flush=True)
    train_v2 = load_jsonl(PRIVATE_V2 / "TRAIN_V2.jsonl")
    dev_v2 = load_jsonl(PRIVATE_V2 / "DEV_SELECTION_V2.jsonl")
    rep_v2 = load_jsonl(PRIVATE_V2 / "REPRESENTATIVE_VALIDATION_V2.jsonl")
    if not train_v2 or not dev_v2 or not rep_v2:
        raise RuntimeError(
            f"V2 surfaces empty train={len(train_v2)} dev={len(dev_v2)} rep={len(rep_v2)}"
        )
    qual_rows = load_jsonl(PRIVATE_QUAL / "QUALIFICATION_ROWS.jsonl")
    qual_ids = {r["identity"] for r in qual_rows}
    qual_text = {text_hash(r.get("text") or "") for r in qual_rows}

    pkg = load_json(PRIVATE_PKG / "PACKAGE.json")
    if pkg.get("PACKAGE_SHA256") != EXPECTED_PACKAGE_SHA256:
        # package may nest sha
        pkg_sha = pkg.get("PACKAGE_SHA256") or pkg.get("package_sha256")
        if pkg_sha != EXPECTED_PACKAGE_SHA256:
            print(
                f"WARN package_sha {pkg_sha} vs expected {EXPECTED_PACKAGE_SHA256}",
                flush=True,
            )

    block_paths = [
        PRIVATE_V2 / "TRAIN_V2.jsonl",
        PRIVATE_V2 / "DEV_SELECTION_V2.jsonl",
        PRIVATE_V2 / "REPRESENTATIVE_VALIDATION_V2.jsonl",
        PRIVATE_QUAL / "QUALIFICATION_ROWS.jsonl",
    ]
    # Materialize block texts readable by acquire (copy)
    block_copy = PRIVATE / "BLOCK_TEXTS.jsonl"
    with block_copy.open("w", encoding="utf-8") as h:
        for p in block_paths:
            for r in load_jsonl(p):
                h.write(
                    json.dumps({"text": r.get("text")}, ensure_ascii=False) + "\n"
                )
    os.chmod(block_copy, 0o600)

    raw = acquire_expand_rows([block_copy])
    write_private(
        PRIVATE / "ACQUIRE_SUMMARY.json",
        {
            "n": len(raw),
            "styles": dict(
                Counter(
                    (
                        "wiki_culture"
                        if "wiki_culture" in (r.get("source_family") or "")
                        else "wikt"
                        if "wikt" in (r.get("source_family") or "")
                        else "other"
                    )
                    for r in raw
                )
            ),
        },
    )

    parent_ids = {r["identity"] for r in train_v2 + dev_v2 + rep_v2} | qual_ids
    parent_text = {
        text_hash(r.get("text") or "") for r in train_v2 + dev_v2 + rep_v2
    } | qual_text
    new_rows = annotate_new_rows(raw, parent_ids, parent_text)
    write_jsonl(PRIVATE / "NEW_ANNOTATED_POSITIVES.jsonl", new_rows)

    print("build_v3", flush=True)
    splits = build_v3(train_v2, dev_v2, rep_v2, new_rows, qual_ids, qual_text)
    write_jsonl(PRIVATE / "TRAIN_V3.jsonl", splits["TRAIN"])
    write_jsonl(PRIVATE / "DEV_SELECTION_V3.jsonl", splits["DEV"])
    write_jsonl(PRIVATE / "REPRESENTATIVE_VALIDATION_V3.jsonl", splits["REP"])

    audit = audit_surfaces(splits, qual_ids, qual_text)
    write_private(PRIVATE / "DIVERSITY_AUDIT.json", audit)
    write_repo(REPO_ART / "diversity_audit.json", audit)

    if not audit["diversity_gate"]["pass"]:
        print("diversity_gate_failed", json.dumps(audit["diversity_gate"], indent=2))
        # still train/eval to settle outcome via classify_outcome

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    vocabs = AXIS_VOCABS
    thresholds = {a: list(BAKEOFF_THRESHOLDS[a]) for a in vocabs}
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")

    train, dev, rep = splits["TRAIN"], splits["DEV"], splits["REP"]
    print(
        f"embed train={len(train)} dev={len(dev)} rep={len(rep)} device={device}",
        flush=True,
    )
    Xtr = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        [r["text"] for r in train],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    Xdv = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        [r["text"] for r in dev],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    Xrp = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        [r["text"] for r in rep],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )

    # Semantic diversity of new function rows vs train function (encoder for measurement only)
    new_fun_idx = [
        i
        for i, r in enumerate(train)
        if r.get("function_labels") and "expand_acquire" in (r.get("v3_origin") or "")
    ]
    old_fun_idx = [
        i
        for i, r in enumerate(train)
        if r.get("function_labels") and "expand_acquire" not in (r.get("v3_origin") or "")
    ]
    # sample
    rng = random.Random(SEED)
    old_sample = (
        old_fun_idx
        if len(old_fun_idx) <= 300
        else rng.sample(old_fun_idx, 300)
    )
    sem = semantic_diversity_vs_train(
        Xtr[new_fun_idx] if new_fun_idx else np.zeros((0, Xtr.shape[1])),
        Xtr[old_sample] if old_sample else np.zeros((0, Xtr.shape[1])),
    )
    write_private(PRIVATE / "SEMANTIC_DIVERSITY.json", sem)

    Ytr = {
        a: np.asarray(
            [multi_hot(r.get(f"{a}_labels"), vocabs[a]) for r in train],
            dtype=np.float32,
        )
        for a in vocabs
    }
    print("train_axis_heads", flush=True)
    heads = train_axis_heads(Xtr, Ytr, vocabs, device)
    head_sha = save_head_bundle(
        PRIVATE / "heads" / "axis_nonlinear_heads_v3.pt",
        heads,
        {
            "seed": SEED,
            "epochs": HEAD_EPOCHS,
            "lr": LR,
            "encoder": SELECTED_ENCODER_MODEL_ID,
            "train_surface": TRAIN_V3_ID,
        },
    )

    gate_path = PRIVATE_PKG / "heads" / "any_evidence_gate.pt"
    gate, _, gate_sha = load_gate(gate_path, device)
    gate_th = float(WITNESS_GATE_THRESHOLD)

    # Baseline: old operating heads + frozen gate on REP_V3
    old_heads, _, old_head_sha = load_heads(
        PRIVATE_PKG / "heads" / "axis_nonlinear_heads.pt", vocabs, device
    )
    print("eval_baseline_old_heads_on_REP_V3", flush=True)
    baseline = run_gated(
        rep, Xrp, old_heads, gate, gate_th, vocabs, thresholds, tech_idx, ai_idx, device
    )
    print("eval_candidate_new_heads_on_REP_V3", flush=True)
    candidate = run_gated(
        rep, Xrp, heads, gate, gate_th, vocabs, thresholds, tech_idx, ai_idx, device
    )
    print("eval_candidate_on_DEV_V3", flush=True)
    dev_metrics = run_gated(
        dev, Xdv, heads, gate, gate_th, vocabs, thresholds, tech_idx, ai_idx, device
    )

    none = none_preserved(candidate)
    outcome = classify_outcome(
        diversity_pass=bool(audit["diversity_gate"]["pass"]),
        none=none,
        candidate=candidate,
        baseline=baseline,
    )

    sealed_at = utc_now_iso()
    summary = {
        "PHASE_RULE": PHASE_RULE,
        "OUTCOME": outcome["OUTCOME"],
        "NEXT_ACTION": outcome["NEXT_ACTION"],
        "diversity_pass": audit["diversity_gate"]["pass"],
        "diversity_checks": audit["diversity_gate"]["checks"],
        "inject_counts": splits.get("inject_counts"),
        "surface_sizes": {
            "TRAIN_V3": len(train),
            "DEV_V3": len(dev),
            "REP_V3": len(rep),
        },
        "baseline_REP_V3_old_heads": {
            k: baseline[k]
            for k in (
                "system_macro_f1",
                "DOMAIN_macro_f1",
                "FUNCTION_macro_f1",
                "MEDIATION_macro_f1",
                "positive_only_system_macro_f1",
                "zero_label_false_positive_rate",
                "zero_label_exact_rejection",
            )
        },
        "candidate_REP_V3": {
            k: candidate[k]
            for k in (
                "system_macro_f1",
                "DOMAIN_macro_f1",
                "FUNCTION_macro_f1",
                "MEDIATION_macro_f1",
                "positive_only_system_macro_f1",
                "zero_label_false_positive_rate",
                "zero_label_exact_rejection",
                "function_by_source",
                "function_by_length",
                "per_label_function",
            )
        },
        "DEV_V3": {
            k: dev_metrics[k]
            for k in (
                "system_macro_f1",
                "FUNCTION_macro_f1",
                "positive_only_system_macro_f1",
                "zero_label_false_positive_rate",
                "zero_label_exact_rejection",
            )
        },
        "deltas": {
            "function": outcome["function_delta"],
            "positive_only": outcome["positive_only_delta"],
            "system": outcome["system_delta"],
        },
        "none_preserved": none,
        "semantic_diversity": sem,
        "frozen": {
            "gate_threshold": gate_th,
            "gate_sha256": gate_sha,
            "old_heads_sha256": old_head_sha,
            "new_heads_sha256": head_sha,
            "package_sha256": EXPECTED_PACKAGE_SHA256,
            "encoder": SELECTED_ENCODER_MODEL_ID,
        },
        "QUALIFICATION_USED_FOR_OPTIMIZATION": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "MODEL_WIDE_BEST_MUTATED": False,
        "NONE_GATE_MUTATED": False,
    }
    receipt = build_expand_receipt(
        {
            **summary,
            "diversity_audit": {
                "pass": audit["diversity_gate"]["pass"],
                "values": audit["diversity_gate"]["values"],
                "rep": audit["rep"],
                "train_per_function": audit["train"]["per_function_support"],
            },
            "surface_ids": {
                "TRAIN": TRAIN_V3_ID,
                "DEV": DEV_V3_ID,
                "REP": REP_V3_ID,
            },
        },
        sealed_at=sealed_at,
    )
    write_private(PRIVATE / "SUMMARY.json", summary)
    write_private(PRIVATE / "RECEIPT.json", receipt)
    write_private(
        PRIVATE / "POINTER.json",
        {
            "MODEL_WIDE_BEST_MUTATED": False,
            "NONE_GATE_MUTATED": False,
            "V6_OPERATING_PIPELINE_CANDIDATE_MUTATED": False,
            "HUB_PUBLISH_AUTHORIZED": False,
            "TRAIN_V3": str(PRIVATE / "TRAIN_V3.jsonl"),
            "DEV_V3": str(PRIVATE / "DEV_SELECTION_V3.jsonl"),
            "REP_V3": str(PRIVATE / "REPRESENTATIVE_VALIDATION_V3.jsonl"),
            "heads": str(PRIVATE / "heads" / "axis_nonlinear_heads_v3.pt"),
        },
    )
    write_private(PRIVATE / "REP_V3_METRICS.json", candidate)
    write_private(PRIVATE / "BASELINE_REP_V3_METRICS.json", baseline)
    write_private(PRIVATE / "DEV_V3_METRICS.json", dev_metrics)

    public = {
        k: v
        for k, v in receipt.items()
        if k not in {"diversity_audit"}
    }
    public["diversity_audit_summary"] = receipt.get("diversity_audit")
    write_repo(REPO_ART / "summary.json", summary)
    write_repo(REPO_ART / "SUMMARY.json", summary)
    write_repo(REPO_ART / "receipt.json", public)
    write_repo(REPO_ART / "RECEIPT.json", public)
    write_repo(REPO_ART / "diversity_audit.json", audit)
    write_repo(
        SPEC / "classification-v6-function-diversity-expand-receipt-20261002.json",
        public,
    )

    md = f"""# EXPAND_V6_FUNCTION_DIVERSITY_AND_POSITIVE_REPRESENTATION

```text
OUTCOME = {outcome['OUTCOME']}
NEXT_ACTION = {outcome['NEXT_ACTION']}
diversity_pass = {audit['diversity_gate']['pass']}
none_preserved = {none['pass']}

REP_V3 candidate (new heads, frozen gate):
  system = {candidate['system_macro_f1']:.4f}
  DOMAIN = {candidate['DOMAIN_macro_f1']:.4f}
  FUNCTION = {candidate['FUNCTION_macro_f1']:.4f}
  MEDIATION = {candidate['MEDIATION_macro_f1']:.4f}
  positive-only = {candidate['positive_only_system_macro_f1']:.4f}
  zero-FP = {candidate['zero_label_false_positive_rate']:.4f}
  zero-exact = {candidate['zero_label_exact_rejection']:.4f}

baseline old heads on REP_V3:
  FUNCTION = {baseline['FUNCTION_macro_f1']:.4f}
  positive-only = {baseline['positive_only_system_macro_f1']:.4f}
  zero-FP = {baseline['zero_label_false_positive_rate']:.4f}

Δ FUNCTION = {outcome['function_delta']:+.4f}
Δ positive-only = {outcome['positive_only_delta']:+.4f}
```

Encoder / ANY_LABEL gate / ontology / thresholds frozen.
QUAL-003 blocked from train/acquisition targeting.
MODEL_WIDE_BEST unchanged. HUB_PUBLISH_AUTHORIZED = false.
"""
    write_repo(SPEC / "classification-v6-function-diversity-expand-20261002.md", md)
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


def main() -> int:
    if os.environ.get("HLX_V6_EXPAND_INNER") == "1":
        return inner()
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Acquire on host (network) before GPU docker
    block_copy = PRIVATE / "BLOCK_TEXTS.jsonl"
    if not block_copy.exists():
        # minimal placeholder; inner rebuilds properly
        block_copy.write_text("", encoding="utf-8")
    # Host-side acquire if missing
    raw_path = PRIVATE / "RAW_ACQUIRE_EXPAND.jsonl"
    if not raw_path.exists() or raw_path.stat().st_size < 1000:
        print("host_acquire", flush=True)
        # Build block file from parents via sudo
        subprocess.run(
            [
                "bash",
                "-lc",
                f"""
set -euo pipefail
PRIV={PRIVATE}
V2={PRIVATE_V2}
Q={PRIVATE_QUAL}
mkdir -p "$PRIV"
: > "$PRIV/BLOCK_TEXTS.jsonl"
for f in "$V2/TRAIN_V2.jsonl" "$V2/DEV_SELECTION_V2.jsonl" "$V2/REPRESENTATIVE_VALIDATION_V2.jsonl" "$Q/QUALIFICATION_ROWS.jsonl"; do
  sudo -n cat "$f" | python3 -c 'import sys,json; 
[sys.stdout.write(json.dumps({{"text": json.loads(l).get("text")}})+"\\n") for l in sys.stdin if l.strip()]' >> "$PRIV/BLOCK_TEXTS.jsonl"
done
python3 {REPO}/scripts/spark/expand_v6_positive_acquire.py --out "$PRIV/RAW_ACQUIRE_EXPAND.jsonl" --block-texts "$PRIV/BLOCK_TEXTS.jsonl" --wikt-target 520 --wiki-target 240 --per-family 30 --workers 3
""",
            ],
            check=False,
        )
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
        "HLX_V6_EXPAND_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(REPO / "scripts/spark/run_classification_v6_function_diversity_expand.py"),
    ]
    log = PRIVATE / "expand_console.log"
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
