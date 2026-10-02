"""HARDEN_V6_FULL_OPERATING_PIPELINE_AND_PREPARE_NEW_QUALIFICATION.

Package frozen encoder + ANY_LABEL gate + frozen axis heads + hierarchy.
Cold-load / round-trip / reproduce NONE-rejection REP_V2 witness.
Preregister QUAL-003; do not score QUAL.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(os.environ.get("HLX_REPO") or "/home/morpheus/Hyperlex")
if not (REPO / "scripts" / "shadow" / "hyperlexical").is_dir():
    REPO = Path(__file__).resolve().parents[2]

PRIVATE = Path(
    "/home/morpheus/hlx-private/classification-v6-operating-pipeline-harden-20261001"
)
PRIVATE_NONE = Path(
    "/home/morpheus/hlx-private/classification-v6-none-rejection-harden-20261001"
)
PRIVATE_SURFACES = Path(
    "/home/morpheus/hlx-private/classification-v6-representative-validation-redesign-20261001"
)
PRIVATE_PKG = Path(
    "/home/morpheus/hlx-private/classification-v6-semantic-pipeline-harden-20261001"
)
REPO_ART = (
    REPO
    / "artifacts"
    / "experiments"
    / "HLX-CLASSIFICATION-V6-OPERATING-PIPELINE-HARDEN-001"
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


def sha256_file(path: Path) -> str:
    d = hashlib.sha256()
    with path.open("rb") as h:
        for chunk in iter(lambda: h.read(1 << 20), b""):
            d.update(chunk)
    return d.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


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


def n_lab(r: dict) -> int:
    return (
        len(r.get("domain_labels") or [])
        + len(r.get("function_labels") or [])
        + len(r.get("mediation_labels") or [])
    )


def multi_hot(labels, vocab):
    idx = {v: i for i, v in enumerate(vocab)}
    vec = [0] * len(vocab)
    for lab in labels or []:
        if lab in idx:
            vec[idx[lab]] = 1
    return vec


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
    hsh = hashlib.sha256()
    for k, tns in sorted(enc.state_dict().items()):
        hsh.update(k.encode())
        hsh.update(tns.detach().cpu().numpy().tobytes())
    n_train = sum(p.numel() for p in enc.parameters() if p.requires_grad)
    del enc
    torch.cuda.empty_cache()
    return __import__("torch").cat(vecs, dim=0).numpy(), hsh.hexdigest(), n_train


def build_mlp(hidden: int, n_out: int, device):
    import torch.nn as nn

    return nn.Sequential(
        nn.Linear(hidden, 128), nn.ReLU(), nn.Linear(128, n_out)
    ).to(device)


def load_torch_bundle(path: Path):
    import io
    import torch

    raw = sudo_read_bytes(path)
    try:
        return torch.load(io.BytesIO(raw), map_location="cpu", weights_only=False), raw
    except TypeError:
        return torch.load(io.BytesIO(raw), map_location="cpu"), raw


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


def load_gate(path: Path, device):
    bundle, raw = load_torch_bundle(path)
    m = build_mlp(768, 1, device)
    m.load_state_dict(bundle["state"])
    m.eval()
    for p in m.parameters():
        p.requires_grad_(False)
    return m, bundle, sha256_bytes(raw)


def scores_from_heads(heads, X, device):
    import torch

    out = {}
    with torch.no_grad():
        xt = torch.tensor(X, device=device)
        for axis, model in heads.items():
            out[axis] = torch.sigmoid(model(xt)).cpu().numpy()
    return out


def gate_scores(model, X, device):
    import torch

    with torch.no_grad():
        xt = torch.tensor(X, dtype=torch.float32, device=device)
        return torch.sigmoid(model(xt)).cpu().numpy().reshape(-1)


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
    return float(
        sum(f1_binary(g[:, j], p[:, j]) for j in range(g.shape[1])) / g.shape[1]
    )


def run_operating_pipeline(rows, X, heads, gate, gate_th, vocabs, thresholds, tech_idx, ai_idx, device):
    import numpy as np

    scores = scores_from_heads(heads, X, device)
    gsc = gate_scores(gate, X, device)
    reject = gsc < float(gate_th)
    preds = {}
    preds_raw = {}
    for a in vocabs:
        th = np.asarray(thresholds[a])
        raw = (np.asarray(scores[a]) >= th).astype(np.int32)
        preds_raw[a] = raw
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
    axis_macros = {a: macro_f1(golds[a], preds[a]) for a in vocabs}
    system = float(sum(axis_macros.values()) / len(axis_macros))

    zero_idx = [i for i, r in enumerate(rows) if n_lab(r) == 0]
    pos_idx = [i for i, r in enumerate(rows) if n_lab(r) > 0]
    zero_fp = 0
    zero_exact = 0
    pred_counts = []
    for i in zero_idx:
        npred = int(
            preds["domain"][i].sum()
            + preds["function"][i].sum()
            + preds["mediation"][i].sum()
        )
        pred_counts.append(npred)
        if npred == 0:
            zero_exact += 1
        else:
            zero_fp += 1
    n_zero = max(1, len(zero_idx))
    false_reject = 0
    for i in pos_idx:
        npred = int(
            preds["domain"][i].sum()
            + preds["function"][i].sum()
            + preds["mediation"][i].sum()
        )
        if npred == 0:
            false_reject += 1
    n_pos = max(1, len(pos_idx))

    def slice_macro(idx):
        if not idx:
            return None
        return float(
            sum(macro_f1(golds[a][idx], preds[a][idx]) for a in vocabs) / len(vocabs)
        )

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
        "false_reject_positive_rate": false_reject / n_pos,
        "positive_only_system_macro_f1": slice_macro(pos_idx),
        "single_label_system_macro_f1": slice_macro(
            [i for i, r in enumerate(rows) if n_lab(r) == 1]
        ),
        "multi_label_system_macro_f1": slice_macro(
            [i for i, r in enumerate(rows) if n_lab(r) >= 2]
        ),
        "hierarchy_corrections": hier_corr,
        "hierarchy_violation_rate_post": 0.0,
        "n_gated_zero": int(reject.sum()),
        "preds": {a: preds[a].tolist() for a in vocabs},
        "preds_raw": {a: preds_raw[a].tolist() for a in vocabs},
        "scores_sum": {a: float(np.asarray(scores[a]).sum()) for a in vocabs},
        "gate_score_sum": float(gsc.sum()),
    }


def copy_bundle(src: Path, dst: Path) -> str:
    dst.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    raw = sudo_read_bytes(src)
    dst.write_bytes(raw)
    os.chmod(dst, 0o600)
    return sha256_bytes(raw)


def inner() -> int:
    import numpy as np
    import torch

    from hyperlexical.classification_v5_stage_a import canonical_json, sha256_text
    from hyperlexical.classification_v6_architecture_reset_bakeoff import AXIS_VOCABS
    from hyperlexical.classification_v6_operating_pipeline_harden import (
        PACKAGE_ID,
        PHASE_RULE,
        PIPELINE_CANDIDATE_ID,
        POINTER_ID,
        RUNTIME_SCHEMA,
        WITNESS_GATE_BUNDLE_SHA256,
        WITNESS_GATE_THRESHOLD,
        build_operating_receipt,
        classify_operating_reproduction,
        decide_operating_readiness,
        operating_pipeline_contract,
        qualification_003_preparation,
    )
    from hyperlexical.classification_v6_qualification_execute_002 import (
        EXPECTED_ENCODER_STATE_HASH,
        EXPECTED_PACKAGE_SHA256,
    )
    from hyperlexical.classification_v6_semantic_pipeline_harden import (
        BAKEOFF_THRESHOLDS,
        SELECTED_ENCODER_MODEL_ID,
        SELECTED_ENCODER_REVISION,
        hierarchy_constraints_payload,
        threshold_manifest_payload,
    )

    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    REPO_ART.mkdir(parents=True, exist_ok=True)
    contract = operating_pipeline_contract()
    write_private(PRIVATE / "CONTRACT.json", contract)
    write_repo(REPO_ART / "contract.json", contract)

    parent = load_json(PRIVATE_PKG / "PACKAGE.json")
    if parent.get("PACKAGE_SHA256") != EXPECTED_PACKAGE_SHA256:
        raise SystemExit("parent_package_sha_mismatch")

    none_cand = load_json(PRIVATE_NONE / "CANDIDATE_PACKAGE.json")
    if none_cand.get("mechanism") != "LEARNED_ANY_EVIDENCE_GATE":
        raise SystemExit("none_candidate_mechanism_mismatch")

    train = load_jsonl(PRIVATE_SURFACES / "TRAIN_V2.jsonl")
    dev = load_jsonl(PRIVATE_SURFACES / "DEV_SELECTION_V2.jsonl")
    rep = load_jsonl(PRIVATE_SURFACES / "REPRESENTATIVE_VALIDATION_V2.jsonl")
    if not (len(train) == 2819 and len(dev) == 505 and len(rep) == 1416):
        raise SystemExit("surface_n_mismatch")

    vocabs = {
        "domain": list(AXIS_VOCABS["domain"]),
        "function": list(AXIS_VOCABS["function"]),
        "mediation": list(AXIS_VOCABS["mediation"]),
    }
    thresholds = {a: list(BAKEOFF_THRESHOLDS[a]) for a in vocabs}
    tech_idx = vocabs["domain"].index("domain.technology")
    ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")
    gate_th = float(
        none_cand.get("params", {}).get("gate_threshold", WITNESS_GATE_THRESHOLD)
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device}", flush=True)

    # Prefer emb cache from NONE phase if present.
    emb_path = PRIVATE_NONE / "emb_cache.npz"
    X_dev = X_rep = None
    enc_pre = EXPECTED_ENCODER_STATE_HASH
    try:
        if os.access(emb_path, os.R_OK):
            cache = np.load(emb_path)
            X_dev, X_rep = cache["dev"], cache["rep"]
            print("loaded_emb_cache", flush=True)
        else:
            raw = sudo_read_bytes(emb_path)
            import io

            cache = np.load(io.BytesIO(raw))
            X_dev, X_rep = cache["dev"], cache["rep"]
            print("loaded_emb_cache_sudo", flush=True)
    except Exception as exc:
        print(f"emb_cache_unavailable: {exc}", flush=True)
        X_dev = X_rep = None
    if X_dev is None or X_rep is None:
        print("embed_dev_rep", flush=True)
        X_dev, enc_pre, n_tr = embed_model(
            SELECTED_ENCODER_MODEL_ID,
            [r.get("text") or "" for r in dev],
            device,
            revision=SELECTED_ENCODER_REVISION,
        )
        X_rep, enc_mid, n_tr2 = embed_model(
            SELECTED_ENCODER_MODEL_ID,
            [r.get("text") or "" for r in rep],
            device,
            revision=SELECTED_ENCODER_REVISION,
        )
        if (
            n_tr
            or n_tr2
            or enc_pre != EXPECTED_ENCODER_STATE_HASH
            or enc_mid != EXPECTED_ENCODER_STATE_HASH
        ):
            raise SystemExit("encoder_hash_or_trainable_bad")

    # Package artifact copies
    heads_src = PRIVATE_PKG / "heads" / "axis_nonlinear_heads.pt"
    gate_src = PRIVATE_NONE / "heads" / "any_evidence_gate.pt"
    heads_dst = PRIVATE / "heads" / "axis_nonlinear_heads.pt"
    gate_dst = PRIVATE / "heads" / "any_evidence_gate.pt"
    head_sha = copy_bundle(heads_src, heads_dst)
    gate_sha = copy_bundle(gate_src, gate_dst)
    if gate_sha != WITNESS_GATE_BUNDLE_SHA256:
        raise SystemExit(f"gate_sha_mismatch {gate_sha}")

    heads, head_bundle, head_sha2 = load_heads(heads_dst, vocabs, device)
    gate, gate_bundle, gate_sha2 = load_gate(gate_dst, device)
    if head_sha2 != head_sha or gate_sha2 != gate_sha:
        raise SystemExit("bundle_sha_reload_mismatch")

    print("eval_packaged_pipeline", flush=True)
    dev_m = run_operating_pipeline(
        dev, X_dev, heads, gate, gate_th, vocabs, thresholds, tech_idx, ai_idx, device
    )
    rep_m = run_operating_pipeline(
        rep, X_rep, heads, gate, gate_th, vocabs, thresholds, tech_idx, ai_idx, device
    )
    # strip heavy preds for persisted metrics later
    def slim(m):
        return {k: v for k, v in m.items() if k not in ("preds", "preds_raw")}

    # Cold-load reload
    heads2, _, _ = load_heads(heads_dst, vocabs, device)
    gate2, _, _ = load_gate(gate_dst, device)
    rep_cold = run_operating_pipeline(
        rep, X_rep, heads2, gate2, gate_th, vocabs, thresholds, tech_idx, ai_idx, device
    )
    raw_mismatch = 0
    constr_mismatch = 0
    for a in vocabs:
        raw_mismatch += int(
            np.sum(
                np.asarray(rep_m["preds_raw"][a])
                != np.asarray(rep_cold["preds_raw"][a])
            )
        )
        constr_mismatch += int(
            np.sum(np.asarray(rep_m["preds"][a]) != np.asarray(rep_cold["preds"][a]))
        )
    cold_load_ok = raw_mismatch == 0 and constr_mismatch == 0

    # Clean-process round-trip
    emb_cache = PRIVATE / "emb_cache.npz"
    np.savez_compressed(emb_cache, X_rep=X_rep)
    os.chmod(emb_cache, 0o600)
    rt_script = PRIVATE / "roundtrip_probe.py"
    rt_out = PRIVATE / "roundtrip_out.json"
    write_private(
        rt_script,
        f"""
import json, os, sys
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0, {str(REPO / "scripts/shadow")!r})
os.environ["HLX_V2_FORWARD_ONTOLOGY"] = "1"
import importlib.util
spec = importlib.util.spec_from_file_location(
    "op_run",
    {str(REPO / "scripts/spark/run_classification_v6_operating_pipeline_harden.py")!r},
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
from hyperlexical.classification_v6_architecture_reset_bakeoff import AXIS_VOCABS
from hyperlexical.classification_v6_semantic_pipeline_harden import BAKEOFF_THRESHOLDS
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
vocabs = {{a: list(AXIS_VOCABS[a]) for a in ("domain","function","mediation")}}
thresholds = {{a: list(BAKEOFF_THRESHOLDS[a]) for a in vocabs}}
tech_idx = vocabs["domain"].index("domain.technology")
ai_idx = vocabs["domain"].index("domain.technology.ai_discourse")
X = np.load({str(emb_cache)!r})["X_rep"]
rows = [json.loads(l) for l in open({str(PRIVATE_SURFACES / "REPRESENTATIVE_VALIDATION_V2.jsonl")!r}) if l.strip()]
# private jsonl may need sudo — fallback
if not rows:
    import subprocess
    text = subprocess.run(["sudo","-n","cat",{str(PRIVATE_SURFACES / "REPRESENTATIVE_VALIDATION_V2.jsonl")!r}], check=True, capture_output=True, text=True).stdout
    rows = [json.loads(l) for l in text.splitlines() if l.strip()]
heads, _, _ = mod.load_heads(Path({str(heads_dst)!r}), vocabs, device)
gate, _, _ = mod.load_gate(Path({str(gate_dst)!r}), device)
m = mod.run_operating_pipeline(rows, X, heads, gate, {gate_th!r}, vocabs, thresholds, tech_idx, ai_idx, device)
Path({str(rt_out)!r}).write_text(json.dumps({{
  "system_macro_f1": m["system_macro_f1"],
  "zero_label_false_positive_rate": m["zero_label_false_positive_rate"],
  "positive_only_system_macro_f1": m["positive_only_system_macro_f1"],
  "preds": m["preds"],
  "preds_raw": m["preds_raw"],
  "scores_sum": m["scores_sum"],
  "gate_score_sum": m["gate_score_sum"],
}}), encoding="utf-8")
""",
    )
    # Ensure roundtrip can read surfaces
    try:
        os.chmod(PRIVATE_SURFACES / "REPRESENTATIVE_VALIDATION_V2.jsonl", 0o600)
    except Exception:
        pass
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
        # retry with sudo-readable copy of REP rows
        rep_copy = PRIVATE / "REP_V2_for_roundtrip.jsonl"
        write_private(
            rep_copy,
            "\n".join(json.dumps(r, sort_keys=True) for r in rep) + "\n",
        )
        write_private(
            rt_script,
            rt_script.read_text(encoding="utf-8").replace(
                str(PRIVATE_SURFACES / "REPRESENTATIVE_VALIDATION_V2.jsonl"),
                str(rep_copy),
            ),
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
            raise SystemExit(f"roundtrip_failed: {rt_rc.stderr[-2000:]}")

    rt = json.loads(rt_out.read_text(encoding="utf-8"))
    rt_raw_mismatch = 0
    rt_constr_mismatch = 0
    for a in vocabs:
        rt_raw_mismatch += int(
            np.sum(np.asarray(rep_m["preds_raw"][a]) != np.asarray(rt["preds_raw"][a]))
        )
        rt_constr_mismatch += int(
            np.sum(np.asarray(rep_m["preds"][a]) != np.asarray(rt["preds"][a]))
        )
    round_trip_ok = rt_raw_mismatch == 0 and rt_constr_mismatch == 0

    # Encoder immutability probe
    _, enc_post, n_tr_post = embed_model(
        SELECTED_ENCODER_MODEL_ID,
        ["immutability probe"],
        device,
        revision=SELECTED_ENCODER_REVISION,
    )
    encoder_immutable = (
        enc_pre == enc_post == EXPECTED_ENCODER_STATE_HASH and n_tr_post == 0
    )

    repro = classify_operating_reproduction(rep_m)
    reproduction_ok = repro["reproduction_class"] == "WITNESS_REPRODUCTION"

    th_manifest = threshold_manifest_payload()
    constraints = hierarchy_constraints_payload()
    qual_prep = qualification_003_preparation()

    package = {
        "PACKAGE_ID": PACKAGE_ID,
        "PIPELINE_CANDIDATE_ID": PIPELINE_CANDIDATE_ID,
        "runtime_schema": RUNTIME_SCHEMA,
        "parent_package_sha256": EXPECTED_PACKAGE_SHA256,
        "encoder": {
            "model_id": SELECTED_ENCODER_MODEL_ID,
            "revision": SELECTED_ENCODER_REVISION,
            "state_hash": EXPECTED_ENCODER_STATE_HASH,
            "trainable_parameters": 0,
            "immutability": {
                "pre": enc_pre,
                "post": enc_post,
                "equal": encoder_immutable,
            },
        },
        "gate": {
            "kind": "ANY_SEMANTIC_EVIDENCE_GATE",
            "threshold": gate_th,
            "bundle_sha256": gate_sha,
            "path": "heads/any_evidence_gate.pt",
        },
        "heads": {
            "kind": "axis_nonlinear_heads",
            "bundle_sha256": head_sha,
            "path": "heads/axis_nonlinear_heads.pt",
            "source": "parent_frozen_package",
        },
        "thresholds": thresholds,
        "threshold_manifest_sha": sha256_text(canonical_json(th_manifest)),
        "hierarchy_constraints": constraints,
        "constraint_manifest_sha": sha256_text(canonical_json(constraints)),
        "ontology": contract["ontology"],
        "flow": contract["architecture"]["flow"],
        "load_validator": {
            "require_encoder_state_hash": EXPECTED_ENCODER_STATE_HASH,
            "require_gate_bundle_sha": gate_sha,
            "require_head_bundle_sha": head_sha,
            "fail_closed_on_mismatch": True,
        },
        "witness": contract["witness"],
        "provenance": {
            "none_rejection_candidate": none_cand,
            "code_revision": code_revision(),
            "n_train": len(train),
            "n_dev": len(dev),
            "n_rep": len(rep),
        },
        "limitations": [
            "QUAL-002 EVALUATION_SPENT — new QUAL-003 required before qualification.",
            "Gate adds modest false-reject on positives (+~6pp vs ungated).",
            "Candidate only — not MODEL_WIDE_BEST; no global promotion.",
        ],
        "global_promotion": False,
    }
    package["PACKAGE_SHA256"] = sha256_text(
        canonical_json({k: v for k, v in package.items() if k != "PACKAGE_SHA256"})
    )

    package_ok = (
        encoder_immutable
        and cold_load_ok
        and round_trip_ok
        and reproduction_ok
        and gate_sha == WITNESS_GATE_BUNDLE_SHA256
    )
    decision = decide_operating_readiness(
        package_ok=package_ok,
        cold_load_ok=cold_load_ok,
        round_trip_ok=round_trip_ok,
        encoder_immutable=encoder_immutable,
        reproduction_ok=reproduction_ok,
    )

    pointer = {
        "MODEL_WIDE_BEST_MUTATED": False,
        "V5_POINTERS_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        POINTER_ID: (
            package["PACKAGE_SHA256"]
            if decision["HARDENING_STATE"] == "V6_OPERATING_PIPELINE_HARDENED"
            else None
        ),
        "V6_OPERATING_PIPELINE_CANDIDATE_STATUS": (
            "CANDIDATE_SEALED_NOT_PROMOTED"
            if decision["HARDENING_STATE"] == "V6_OPERATING_PIPELINE_HARDENED"
            else "HARDEN_FAILED"
        ),
        "PARENT_PACKAGE_SHA256": EXPECTED_PACKAGE_SHA256,
        "QUAL_002_STATUS": "EVALUATION_SPENT",
        "QUAL_003_STATUS": "PREPARED_NOT_SEALED",
    }

    write_private(PRIVATE / "PACKAGE.json", package)
    write_private(PRIVATE / "POINTER.json", pointer)
    write_private(PRIVATE / "THRESHOLD_MANIFEST.json", th_manifest)
    write_private(PRIVATE / "HIERARCHY_CONSTRAINTS.json", constraints)
    write_private(PRIVATE / "QUAL_003_PREPARATION.json", qual_prep)
    write_private(PRIVATE / "DEV_V2_REPLAY.json", slim(dev_m))
    write_private(PRIVATE / "REP_V2_REPLAY.json", slim(rep_m))
    write_private(
        PRIVATE / "COLD_LOAD.json",
        {
            "ok": cold_load_ok,
            "raw_mismatch": raw_mismatch,
            "constrained_mismatch": constr_mismatch,
        },
    )
    write_private(
        PRIVATE / "ROUND_TRIP.json",
        {
            "ok": round_trip_ok,
            "raw_mismatch": rt_raw_mismatch,
            "constrained_mismatch": rt_constr_mismatch,
            "rt_system_macro_f1": rt["system_macro_f1"],
        },
    )

    receipt = build_operating_receipt(
        {
            "PHASE_RULE": PHASE_RULE,
            "HARDENING_STATE": decision["HARDENING_STATE"],
            "QUALIFICATION_READINESS": decision["QUALIFICATION_READINESS"],
            "NEXT_ACTION": decision["NEXT_ACTION"],
            "PACKAGE_SHA256": package["PACKAGE_SHA256"],
            "package": {
                "PACKAGE_ID": PACKAGE_ID,
                "PACKAGE_SHA256": package["PACKAGE_SHA256"],
                "gate_bundle_sha256": gate_sha,
                "head_bundle_sha256": head_sha,
                "gate_threshold": gate_th,
            },
            "encoder_immutability": {
                "pre": enc_pre,
                "post": enc_post,
                "expected": EXPECTED_ENCODER_STATE_HASH,
                "ok": encoder_immutable,
                "trainable_parameters": 0,
            },
            "cold_load": {
                "ok": cold_load_ok,
                "raw_mismatch": raw_mismatch,
                "constrained_mismatch": constr_mismatch,
            },
            "round_trip": {
                "ok": round_trip_ok,
                "raw_mismatch": rt_raw_mismatch,
                "constrained_mismatch": rt_constr_mismatch,
            },
            "reproduction": repro,
            "DEV_V2": slim(dev_m),
            "REP_V2": slim(rep_m),
            "qualification_003_preparation": qual_prep,
            "pointer": pointer,
            "code_revision": code_revision(),
        }
    )
    write_private(PRIVATE / "RECEIPT.json", receipt)

    summary = {
        "PHASE_RULE": PHASE_RULE,
        "HARDENING_STATE": decision["HARDENING_STATE"],
        "QUALIFICATION_READINESS": decision["QUALIFICATION_READINESS"],
        "NEXT_ACTION": decision["NEXT_ACTION"],
        "PACKAGE_SHA256": package["PACKAGE_SHA256"],
        "REP_V2_system_macro_f1": rep_m["system_macro_f1"],
        "REP_V2_zero_fp": rep_m["zero_label_false_positive_rate"],
        "REP_V2_positive_only": rep_m["positive_only_system_macro_f1"],
        "DEV_V2_system_macro_f1": dev_m["system_macro_f1"],
        "reproduction_class": repro["reproduction_class"],
        "encoder_immutable": encoder_immutable,
        "cold_load_ok": cold_load_ok,
        "round_trip_ok": round_trip_ok,
        "QUAL_002_STATUS": "EVALUATION_SPENT",
        "QUAL_003_STATUS": "PREPARED_NOT_SEALED",
        "MODEL_WIDE_BEST_MUTATED": False,
        "HUB_PUBLISH_AUTHORIZED": False,
        "RECEIPT": receipt["V6_OPERATING_PIPELINE_HARDEN_RECEIPT_SHA256"],
    }
    write_private(PRIVATE / "SUMMARY.json", summary)

    for name, payload in [
        ("SUMMARY.json", summary),
        ("summary.json", summary),
        ("RECEIPT.json", receipt),
        ("receipt.json", receipt),
        ("PACKAGE.json", package),
        ("package.json", package),
        ("POINTER.json", pointer),
        ("pointer.json", pointer),
        ("contract.json", contract),
        ("qual_003_preparation.json", qual_prep),
        ("qualification_gates.json", qual_prep["gates"]),
        ("dev_v2_replay.json", slim(dev_m)),
        ("rep_v2_replay.json", slim(rep_m)),
        ("threshold_manifest.json", th_manifest),
        ("hierarchy_constraints.json", constraints),
    ]:
        write_repo(REPO_ART / name, payload)

    write_repo(
        SPEC / "classification-v6-operating-pipeline-harden-receipt-20261001.json",
        receipt,
    )
    md = f"""# HARDEN_V6_FULL_OPERATING_PIPELINE_AND_PREPARE_NEW_QUALIFICATION

```text
HARDENING_STATE = {decision['HARDENING_STATE']}
QUALIFICATION_READINESS = {decision['QUALIFICATION_READINESS']}
NEXT_ACTION = {decision['NEXT_ACTION']}
PACKAGE_SHA256 = {package['PACKAGE_SHA256']}
REP_V2 system macro-F1 = {rep_m['system_macro_f1']:.4f}
REP_V2 zero-label FP = {rep_m['zero_label_false_positive_rate']:.3f}
REP_V2 positive-only = {rep_m['positive_only_system_macro_f1']:.4f}
reproduction = {repro['reproduction_class']}
encoder_immutable = {encoder_immutable}
cold_load_ok = {cold_load_ok}
round_trip_ok = {round_trip_ok}
QUAL_002 = EVALUATION_SPENT
QUAL_003 = PREPARED_NOT_SEALED
RECEIPT = {receipt['V6_OPERATING_PIPELINE_HARDEN_RECEIPT_SHA256']}
```

Operating pipeline: frozen embedding → ANY_LABEL gate → frozen axis heads →
hierarchy. QUAL-003 construction plan + operating gates preregistered; no QUAL scoring.
"""
    write_repo(
        SPEC / "classification-v6-operating-pipeline-harden-20261001.md", md
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if decision["HARDENING_STATE"] == "V6_OPERATING_PIPELINE_HARDENED" else 2


def main() -> int:
    if os.environ.get("HLX_V6_OPERATING_PIPELINE_INNER") == "1":
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
        "HLX_V6_OPERATING_PIPELINE_INNER=1",
        "-e",
        f"HLX_V5_STAGE_A_CODE_REVISION={revision}",
        "--entrypoint",
        "python3",
        IMAGE,
        str(
            REPO
            / "scripts/spark/run_classification_v6_operating_pipeline_harden.py"
        ),
    ]
    log = PRIVATE / "operating_pipeline_console.log"
    with log.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(
            cmd, check=False, stdout=handle, stderr=subprocess.STDOUT
        )
    try:
        print(log.read_text(encoding="utf-8")[-80000:])
    except OSError:
        pass
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
